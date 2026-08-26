"""ARS-Grok Build 根技能契约测试。"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


仓库根目录 = Path(__file__).resolve().parents[1]
验证器路径 = 仓库根目录 / "scripts" / "validate_skill.py"
模块规格 = importlib.util.spec_from_file_location("validate_skill", 验证器路径)
assert 模块规格 and 模块规格.loader
验证器 = importlib.util.module_from_spec(模块规格)
模块规格.loader.exec_module(验证器)


class 技能契约测试(unittest.TestCase):
    def test_静态契约全部通过(self) -> None:
        self.assertEqual([], 验证器.验证())

    def test_命令数量固定(self) -> None:
        self.assertEqual(16, len(验证器.预期命令))

    def test_工作流入口数量固定(self) -> None:
        self.assertEqual(5, len(验证器.预期工作流))


if __name__ == "__main__":
    unittest.main()
