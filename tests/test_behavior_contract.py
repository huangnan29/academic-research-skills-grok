"""ARS-Grok Build 五类受限行为契约的单元测试。"""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from scripts import run_grok_behavior_smoke as runner


仓库根目录 = Path(__file__).resolve().parents[1]
案例路径 = 仓库根目录 / "tests" / "behavior_cases.json"


class 行为案例契约测试(unittest.TestCase):
    """验证案例覆盖范围、稳定标记和安全限制。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.案例 = runner.读取案例(案例路径)

    def test_正好包含九个固定案例(self) -> None:
        self.assertEqual(len(self.案例), 9)
        self.assertEqual(
            [案例["id"] for 案例 in self.案例],
            [
                "vague-topic-socratic",
                "metadata-only-citation",
                "reviewer-read-only",
                "full-pipeline-checkpoint",
                "private-material-no-upload",
                "native-deep-research-route",
                "native-academic-paper-route",
                "native-paper-reviewer-route",
                "native-academic-pipeline-route",
            ],
        )

    def test_每个提示词都明确受限并要求稳定键值(self) -> None:
        for 案例 in self.案例:
            with self.subTest(case_id=案例["id"]):
                for 限制 in ("不联网", "不写文件", "只做路由/边界测试"):
                    self.assertIn(限制, 案例["prompt"])
                self.assertIn("KEY=VALUE", 案例["prompt"])
                self.assertIsInstance(案例["required"], list)
                self.assertIsInstance(案例["forbidden"], list)
                self.assertTrue(案例["required"])
                self.assertTrue(案例["forbidden"])

    def test_九个边界分别有正向和反向断言(self) -> None:
        期望标记 = {
            "vague-topic-socratic": ("ROUTE=SOCRATIC", "OUTLINE_GENERATED=NO"),
            "metadata-only-citation": (
                "CITATION_EVIDENCE=METADATA_ONLY",
                "FULLTEXT_VERIFIED=NO",
            ),
            "reviewer-read-only": ("REVIEW_MODE=READ_ONLY", "MANUSCRIPT_MODIFIED=NO"),
            "full-pipeline-checkpoint": (
                "MANDATORY_CHECKPOINT=REQUIRED",
                "AUTO_FINALIZATION=NO",
            ),
            "private-material-no-upload": (
                "PRIVATE_MATERIAL_CONSENT=ABSENT",
                "MATERIAL_TRANSMITTED=NO",
            ),
            "native-deep-research-route": (
                "NATIVE_SKILL=ARS_DEEP_RESEARCH",
                "WORKFLOW=DEEP_RESEARCH",
            ),
            "native-academic-paper-route": (
                "NATIVE_SKILL=ARS_ACADEMIC_PAPER",
                "WORKFLOW=ACADEMIC_PAPER",
            ),
            "native-paper-reviewer-route": (
                "NATIVE_SKILL=ARS_PAPER_REVIEWER",
                "WORKFLOW=ACADEMIC_PAPER_REVIEWER",
            ),
            "native-academic-pipeline-route": (
                "NATIVE_SKILL=ARS_ACADEMIC_PIPELINE",
                "WORKFLOW=ACADEMIC_PIPELINE",
            ),
        }
        for 案例 in self.案例:
            with self.subTest(case_id=案例["id"]):
                required_text = "\n".join(案例["required"])
                forbidden_text = "\n".join(案例["forbidden"])
                for 标记 in 期望标记[案例["id"]]:
                    self.assertIn(标记.split("=")[0], required_text)
                self.assertTrue(forbidden_text)

    def test_案例定义拒绝缺失安全限制(self) -> None:
        案例 = dict(self.案例[0])
        案例["prompt"] = 案例["prompt"].replace("不联网", "联网", 1)
        with self.assertRaises(runner.行为契约错误):
            runner.验证案例定义(案例)

    def test_案例定义拒绝不安全的数量或命令合同(self) -> None:
        原文 = json.loads(案例路径.read_text(encoding="utf-8"))
        原文["cases"] = 原文["cases"][:8]
        with tempfile.TemporaryDirectory() as 临时目录:
            临时路径 = Path(临时目录) / "cases.json"
            临时路径.write_text(json.dumps(原文, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(runner.行为契约错误):
                runner.读取案例(临时路径)


class 行为执行器契约测试(unittest.TestCase):
    """验证默认不执行、参数选择、命令边界和正则判定。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.案例 = runner.读取案例(案例路径)

    def test_默认模式只列出且绝不调用_subprocess(self) -> None:
        with mock.patch.object(runner.subprocess, "run") as mock_run:
            输出 = io.StringIO()
            with contextlib.redirect_stdout(输出):
                状态 = runner.主函数([])
        self.assertEqual(状态, 0)
        mock_run.assert_not_called()
        self.assertIn("仅列出，未调用 Grok", 输出.getvalue())
        self.assertIn("vague-topic-socratic", 输出.getvalue())

    def test_case和timeout参数被解析(self) -> None:
        解析结果 = runner.构建解析器().parse_args(
            ["--execute", "--case", "reviewer-read-only", "--timeout", "3.5"]
        )
        self.assertTrue(解析结果.execute)
        self.assertEqual(解析结果.case_ids, ["reviewer-read-only"])
        self.assertEqual(解析结果.timeout, 3.5)

    def test_未知case和非正timeout被拒绝(self) -> None:
        with self.assertRaises(runner.行为契约错误):
            runner.选择案例(self.案例, ["not-defined"])
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                runner.构建解析器().parse_args(["--timeout", "0"])

    def test_execute只使用固定_grok_p并按正则通过(self) -> None:
        案例 = self.案例[0]
        完成 = subprocess.CompletedProcess(
            args=["grok", "-p", "忽略"],
            returncode=0,
            stdout=(
                "ROUTE=SOCRATIC\n"
                "OUTLINE_GENERATED=NO\n"
                "NETWORK_USED=NO\n"
                "FILES_WRITTEN=NO\n"
            ),
            stderr="",
        )
        调用记录 = {}

        def 假运行(command, **kwargs):
            调用记录["command"] = command
            调用记录["kwargs"] = kwargs
            return 完成

        结果 = runner.执行案例(案例, timeout=2.0, runner=假运行)
        self.assertEqual(结果["status"], "PASS")
        self.assertTrue(结果["passed"])
        self.assertEqual(调用记录["command"][:2], ["grok", "-p"])
        self.assertEqual(调用记录["command"][2], 案例["prompt"])
        self.assertTrue(调用记录["kwargs"]["capture_output"])
        self.assertTrue(调用记录["kwargs"]["text"])
        self.assertEqual(调用记录["kwargs"]["timeout"], 2.0)
        self.assertFalse(调用记录["kwargs"]["check"])
        self.assertIn("ROUTE=SOCRATIC", 结果["stdout"])
        self.assertEqual(结果["stderr"], "")

    def test_required缺失或forbidden命中会失败(self) -> None:
        案例 = self.案例[0]
        失败 = runner.判定输出(
            案例,
            "ROUTE=SOCRATIC\nOUTLINE_GENERATED=YES\nNETWORK_USED=NO\nFILES_WRITTEN=NO",
            returncode=0,
        )
        self.assertEqual(失败["status"], "FAIL")
        self.assertFalse(失败["passed"])
        self.assertTrue(any(item["matched"] for item in 失败["forbidden"]))

    def test_首个标记前有进度文字仍按规范化标记判断(self) -> None:
        """进度前缀不应掩盖必需标记，也不能掩盖禁止标记。"""

        案例 = self.案例[0]
        通过 = runner.判定输出(
            案例,
            "先读取工作流。ROUTE=SOCRATIC\nOUTLINE_GENERATED=NO\n"
            "NETWORK_USED=NO\nFILES_WRITTEN=NO\n",
        )
        self.assertTrue(通过["passed"])

        失败 = runner.判定输出(
            案例,
            "进度说明。ROUTE=SOCRATIC\nOUTLINE_GENERATED=YES\n"
            "NETWORK_USED=NO\nFILES_WRITTEN=NO\n",
        )
        self.assertFalse(失败["passed"])
        self.assertTrue(any(item["matched"] for item in 失败["forbidden"]))

    def test_非零退出码和超时状态可见(self) -> None:
        案例 = self.案例[0]
        非零 = runner.判定输出(案例, "", returncode=7)
        self.assertEqual(非零["status"], "FAIL")
        超时异常 = subprocess.TimeoutExpired(["grok", "-p"], 1)
        with mock.patch.object(runner.subprocess, "run", side_effect=超时异常):
            超时结果 = runner.执行案例(案例, timeout=1)
        self.assertEqual(超时结果["status"], "TIMEOUT")
        self.assertTrue(超时结果["timed_out"])

    def test_凭证和私钥只保留脱敏占位符(self) -> None:
        原文 = (
            "token=" + "ghp_" + "123456789012345678901234567890123456\n"
            "Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456\n"
            "-----BEGIN " + "PRIVATE KEY-----\nsecret\n-----END " + "PRIVATE KEY-----"
        )
        脱敏后 = runner.脱敏文本(原文)
        self.assertNotIn("ghp_", 脱敏后)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz123456", 脱敏后)
        self.assertNotIn("BEGIN PRIVATE KEY", 脱敏后)
        self.assertIn("[REDACTED_TOKEN]", 脱敏后)
        self.assertIn("[REDACTED_PRIVATE_KEY]", 脱敏后)

    def test_报告为_json且默认报告不含执行输出(self) -> None:
        报告 = runner.构建报告(self.案例, executed=False)
        self.assertEqual(报告["mode"], "list")
        self.assertFalse(报告["executed"])
        self.assertEqual(报告["results"], [])
        self.assertIsNone(报告["passed"])
        with tempfile.TemporaryDirectory() as 临时目录:
            路径 = Path(临时目录) / "nested" / "report.json"
            runner.写入报告(路径, 报告)
            读取 = json.loads(路径.read_text(encoding="utf-8"))
        self.assertEqual(读取["case_ids"], [案例["id"] for 案例 in self.案例])
        self.assertNotIn("prompt", 读取["cases"][0])


if __name__ == "__main__":
    unittest.main()
