"""ARS-Grok Build 可选 Hook 的行为测试。"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


项目根目录 = Path(__file__).resolve().parents[1]
技能目录 = 项目根目录 / "skills" / "academic-research-suite"
Hook目录 = 技能目录 / "grok" / "hooks"
PreToolUse脚本 = Hook目录 / "pre_tool_use.py"


def 运行Hook(脚本: Path, 事件: object, cwd: Path | None = None) -> dict[str, object]:
    """通过 uv 调用 Hook，并确认它输出单个 JSON 对象。"""

    进程 = subprocess.run(
        ["uv", "run", "python", str(脚本)],
        input=json.dumps(事件, ensure_ascii=False),
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        cwd=cwd or 项目根目录,
        check=False,
    )
    if 进程.returncode != 0:
        raise AssertionError(f"Hook 退出失败：{进程.stderr}")
    输出行 = [行 for 行 in 进程.stdout.splitlines() if 行.strip()]
    if len(输出行) != 1:
        raise AssertionError(f"Hook 输出不是单个 JSON：{进程.stdout!r}")
    结果 = json.loads(输出行[0])
    if not isinstance(结果, dict):
        raise AssertionError("Hook 输出不是 JSON 对象")
    return 结果


class GrokHookTest(unittest.TestCase):
    """覆盖允许、拒绝及 fail-open 行为。"""

    def test_pre_tool_use主会话写入允许(self) -> None:
        with tempfile.TemporaryDirectory() as 临时目录:
            工作区 = Path(临时目录)
            结果 = 运行Hook(
                PreToolUse脚本,
                {
                    "hookEventName": "PreToolUse",
                    "toolName": "search_replace",
                    "toolInput": {"filePath": str(工作区 / "notes.md")},
                    "cwd": str(工作区),
                    "workspaceRoot": str(工作区),
                },
            )
        self.assertEqual(结果.get("decision"), "allow")

    def test_pre_tool_use_bucket_a越界写入拒绝(self) -> None:
        with tempfile.TemporaryDirectory() as 临时目录:
            工作区 = Path(临时目录)
            结果 = 运行Hook(
                PreToolUse脚本,
                {
                    "hookEventName": "PreToolUse",
                    "toolName": "search_replace",
                    "toolInput": {"filePath": str(工作区 / "phase2_bad" / "notes.md")},
                    "cwd": str(工作区),
                    "workspaceRoot": str(工作区),
                    "subagentType": "ars-research-architect",
                },
            )
        self.assertEqual(结果.get("decision"), "deny")
        self.assertIsInstance(结果.get("reason"), str)

    def test_pre_tool_use_bucket_a终端调用拒绝(self) -> None:
        """原 guard 对 Bucket A 的 Bash 全部拒绝，映射后仍保持该边界。"""

        结果 = 运行Hook(
            PreToolUse脚本,
            {
                "hookEventName": "PreToolUse",
                "toolName": "run_terminal_command",
                "toolInput": {"command": "读取目录"},
                "subagentType": "ars-research-architect",
            },
        )
        self.assertEqual(结果.get("decision"), "deny")

    def test_pre_tool_use仅处理真实工具名称(self) -> None:
        结果 = 运行Hook(
            PreToolUse脚本,
            {"hookEventName": "PreToolUse", "toolName": "read_file", "toolInput": {}},
        )
        self.assertEqual(结果, {"decision": "allow"})

    def test_pre_tool_use解析失败保持允许(self) -> None:
        进程 = subprocess.run(
            ["uv", "run", "python", str(PreToolUse脚本)],
            input="不是 JSON",
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            cwd=项目根目录,
            check=False,
        )
        self.assertEqual(进程.returncode, 0)
        self.assertEqual(json.loads(进程.stdout), {"decision": "allow"})

    def test_pre_tool_use环境缺失保持允许(self) -> None:
        """缺少随包上游守卫时不得阻塞 Grok 工具调用。"""

        with tempfile.TemporaryDirectory() as 临时目录:
            临时技能 = Path(临时目录) / "skill"
            临时Hook = 临时技能 / "grok" / "hooks"
            临时Hook.mkdir(parents=True)
            临时脚本 = 临时Hook / "pre_tool_use.py"
            shutil.copy2(PreToolUse脚本, 临时脚本)
            结果 = 运行Hook(
                临时脚本,
                {
                    "hookEventName": "PreToolUse",
                    "toolName": "search_replace",
                    "toolInput": {"filePath": "/tmp/private.md"},
                },
                cwd=临时目录,
            )
        self.assertEqual(结果, {"decision": "allow"})

    def test_hook配置只含本地command且matcher精确(self) -> None:
        配置 = json.loads(
            (Hook目录 / "ars-academic-research-suite.json").read_text(encoding="utf-8")
        )
        序列化 = json.dumps(配置, ensure_ascii=False).lower()
        self.assertNotIn("http://", 序列化)
        self.assertNotIn("https://", 序列化)
        self.assertEqual(
            配置["hooks"]["PreToolUse"][0]["matcher"],
            "^(search_replace|run_terminal_command|run_terminal_cmd)$",
        )
        self.assertNotIn("SessionStart", 配置["hooks"])
        self.assertEqual(
            配置["hooks"]["PreToolUse"][0]["hooks"][0]["type"],
            "command",
        )

    def test_工作目录为工作区子目录仍允许本阶段相对写入(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cwd = root / "phase1_blueprint"
            cwd.mkdir()
            result = 运行Hook(PreToolUse脚本, {
                "toolName": "search_replace", "toolInput": {"file_path": "notes.md"},
                "workspaceRoot": str(root), "cwd": str(cwd), "subagentType": "ars-research-architect",
            })
            self.assertEqual(result["decision"], "allow")

    def test_主会话不能改写Grok守卫本体(self):
        result = 运行Hook(PreToolUse脚本, {
            "toolName": "search_replace", "toolInput": {"path": str(PreToolUse脚本)},
            "workspaceRoot": str(项目根目录), "cwd": str(项目根目录),
        })
        self.assertEqual(result["decision"], "deny")

    def test_终端内部别名仍被拒绝(self):
        result = 运行Hook(PreToolUse脚本, {
            "toolName": "run_terminal_cmd", "toolInput": {"command": "printf TEST"},
            "subagentType": "ars-research-architect",
        })
        self.assertEqual(result["decision"], "deny")


if __name__ == "__main__":
    unittest.main()
