"""根级 GitHub Actions 工作流的静态契约测试。"""

from __future__ import annotations

import re
from pathlib import Path
import unittest


仓库根目录 = Path(__file__).resolve().parents[1]
工作流路径 = 仓库根目录 / ".github" / "workflows" / "ci.yml"


class 根级持续集成契约测试(unittest.TestCase):
    """只检查公开 CI 的可审计契约，不启动 Grok 或外网研究流程。"""

    @classmethod
    def setUpClass(cls) -> None:
        if not 工作流路径.is_file():
            raise AssertionError(f"缺少根级 CI 工作流：{工作流路径}")
        cls.工作流 = 工作流路径.read_text(encoding="utf-8")

    def test_工作流同时响应推送和拉取请求(self) -> None:
        self.assertRegex(self.工作流, r"(?m)^on:\s*$")
        self.assertRegex(self.工作流, r"(?m)^  push:\s*$")
        self.assertRegex(self.工作流, r"(?m)^  pull_request:\s*$")

    def test_使用检出和_uv官方动作(self) -> None:
        self.assertIn("uses: actions/checkout@v7", self.工作流)
        self.assertIn("uses: astral-sh/setup-uv@v10.0.1", self.工作流)

    def test_所有显式_python命令都通过_uv(self) -> None:
        self.assertIn("uv run python scripts/validate_skill.py", self.工作流)
        self.assertIn(
            "uv run python -m unittest discover -s tests -p 'test_*.py' -v",
            self.工作流,
        )
        self.assertIn("uv run python - <<'PY'", self.工作流)
        self.assertNotRegex(self.工作流, r"(?m)^\s+python(?:3)?\s+")

    def test_凭证扫描使用只读的_NUL安全路径处理(self) -> None:
        self.assertIn(
            '"git", "ls-tree", "-rz", "--name-only", "HEAD"',
            self.工作流,
        )
        self.assertIn('split(b"\\0")', self.工作流)
        self.assertIn("os.fsdecode", self.工作流)
        self.assertIn("read_bytes()", self.工作流)
        self.assertIn("PRIVATE KEY", self.工作流)
        self.assertIn("github-token", self.工作流)
        self.assertIn("未输出文件内容", self.工作流)
        self.assertNotIn("write_text(", self.工作流)
        self.assertNotIn("open(\"w\"", self.工作流)

    def test_大文件门使用五十_MiB上限(self) -> None:
        self.assertIn("最大文件字节数 = 50 * 1024 * 1024", self.工作流)
        self.assertIn("超过 50 MiB 的已跟踪文件", self.工作流)
        self.assertIn('"git", "ls-tree", "-rz", "--name-only", "HEAD"', self.工作流)
        self.assertRegex(self.工作流, r"(?m)^\s+大文件数量\s*=")

    def test_CI不启动需要登录或外网研究的行为测试(self) -> None:
        for 禁止项 in ("grok inspect", "web_search", "spawn_subagent", "curl ", "wget "):
            with self.subTest(禁止项=禁止项):
                self.assertNotIn(禁止项, self.工作流)


if __name__ == "__main__":
    unittest.main()
