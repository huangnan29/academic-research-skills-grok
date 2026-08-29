"""ARS-Grok 原生 Skill 入口和命令推理分层的静态契约测试。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


仓库根目录 = Path(__file__).resolve().parents[1]
技能目录 = (
    仓库根目录
    / "skills"
    / "academic-research-suite"
    / "grok"
    / "skills"
)
命令目录 = (
    仓库根目录
    / "skills"
    / "academic-research-suite"
    / "grok"
    / "commands"
)

预期技能 = {
    "ars-deep-research": {
        "路径": "../../../ars/deep-research/WORKFLOW.md",
        "触发词": ("ARS", "深度研究", "文献综述", "/deep-research"),
        "工具": {
            "read_file",
            "list_dir",
            "grep",
            "web_search",
            "run_terminal_command",
            "search_replace",
        },
    },
    "ars-academic-paper": {
        "路径": "../../../ars/academic-paper/WORKFLOW.md",
        "触发词": ("ARS", "论文", "引用核验"),
        "工具": {
            "read_file",
            "list_dir",
            "grep",
            "web_search",
            "run_terminal_command",
            "search_replace",
        },
    },
    "ars-paper-reviewer": {
        "路径": "../../../ars/academic-paper-reviewer/WORKFLOW.md",
        "触发词": ("ARS", "同行评审", "只读"),
        "工具": {"read_file", "list_dir", "grep", "web_search"},
    },
    "ars-academic-pipeline": {
        "路径": "../../../ars/academic-pipeline/WORKFLOW.md",
        "触发词": ("ARS", "端到端", "Material Passport"),
        "工具": {
            "read_file",
            "list_dir",
            "grep",
            "web_search",
            "run_terminal_command",
            "search_replace",
            "spawn_subagent",
        },
    },
}

轻任务命令 = {
    "ars-3w",
    "ars-abstract",
    "ars-cache-invalidate",
    "ars-citation-check",
    "ars-disclosure",
    "ars-format-convert",
    "ars-lit-review",
    "ars-mark-read",
    "ars-outline",
    "ars-plan",
    "ars-rebuttal-audit",
    "ars-revision",
    "ars-unmark-read",
}
继承命令 = {"ars-full", "ars-reviewer", "ars-revision-coach"}


def 读取前置元数据(文本: str) -> dict[str, str | list[str]]:
    """读取本项目入口和命令使用的有限 YAML 前置元数据。"""
    匹配 = re.match(r"\A---\n(?P<头部>.*?)\n---\n", 文本, re.DOTALL)
    if not 匹配:
        raise AssertionError("文件缺少列一的 YAML 前置元数据")
    头部 = 匹配.group("头部")
    元数据: dict[str, str | list[str]] = {}
    当前列表键: str | None = None
    for 行 in 头部.splitlines():
        if 行.startswith("  - ") and 当前列表键:
            元数据.setdefault(当前列表键, [])
            值 = 元数据[当前列表键]
            assert isinstance(值, list)
            值.append(行[4:].strip())
            continue
        键值 = re.match(r"^(?P<键>[A-Za-z][\w-]*):\s*(?P<值>.*)$", 行)
        if not 键值:
            当前列表键 = None
            continue
        键 = 键值.group("键")
        值 = 键值.group("值").strip()
        if 值:
            元数据[键] = 值.strip('"\'')
            当前列表键 = None
        else:
            元数据[键] = []
            当前列表键 = 键
    return 元数据


class 原生技能入口测试(unittest.TestCase):
    def test_四个技能名称和目录精确匹配(self) -> None:
        实际 = {
            路径.parent.name
            for 路径 in 技能目录.glob("*/SKILL.md")
        }
        self.assertEqual(set(预期技能), 实际)

    def test_路由描述和自动显式调用契约(self) -> None:
        for 名称, 期望 in 预期技能.items():
            with self.subTest(名称=名称):
                文本 = (技能目录 / 名称 / "SKILL.md").read_text(encoding="utf-8")
                元数据 = 读取前置元数据(文本)
                self.assertEqual(名称, 元数据.get("name"))
                描述 = str(元数据.get("description", ""))
                for 触发词 in 期望["触发词"]:
                    self.assertIn(触发词, 描述 + 文本)
                self.assertEqual("true", 元数据.get("user-invocable"))
                self.assertEqual("false", 元数据.get("disable-model-invocation"))
                self.assertIn(期望["路径"], 文本)
                self.assertTrue((技能目录 / 名称 / 期望["路径"]).resolve().is_file())
                self.assertEqual(期望["工具"], set(元数据.get("allowed-tools", [])))

    def test_入口简短且没有复制工作流正文(self) -> None:
        for 名称 in 预期技能:
            with self.subTest(名称=名称):
                文本 = (技能目录 / 名称 / "SKILL.md").read_text(encoding="utf-8")
                正文 = 文本.split("---\n", 2)[-1]
                self.assertLess(len(正文), 1800)
                self.assertNotIn("## Agent Team", 正文)
                self.assertNotIn("## Orchestration Workflow", 正文)
                self.assertNotIn("## Pipeline Stages", 正文)


class 命令推理分层测试(unittest.TestCase):
    def test_轻任务和继承命令集合精确匹配(self) -> None:
        实际 = {路径.stem for 路径 in 命令目录.glob("*.md")}
        self.assertEqual(轻任务命令 | 继承命令, 实际)
        self.assertEqual(13, len(轻任务命令))
        self.assertEqual(3, len(继承命令))

    def test_轻任务使用中等推理强度(self) -> None:
        for 名称 in 轻任务命令:
            with self.subTest(名称=名称):
                文本 = (命令目录 / f"{名称}.md").read_text(encoding="utf-8")
                元数据 = 读取前置元数据(文本)
                self.assertEqual("medium", 元数据.get("effort"))

    def test_重任务保持当前模型和推理强度继承(self) -> None:
        for 名称 in 继承命令:
            with self.subTest(名称=名称):
                文本 = (命令目录 / f"{名称}.md").read_text(encoding="utf-8")
                元数据 = 读取前置元数据(文本)
                self.assertNotIn("model", 元数据)
                self.assertNotIn("effort", 元数据)

    def test_命令不硬编码模型(self) -> None:
        for 路径 in 命令目录.glob("*.md"):
            with self.subTest(命令=路径.stem):
                文本 = 路径.read_text(encoding="utf-8")
                self.assertNotRegex(文本, r"(?m)^model\s*:")


if __name__ == "__main__":
    unittest.main()
