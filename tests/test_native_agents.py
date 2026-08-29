"""Grok 原生 Agent 的静态契约测试。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


仓库根目录 = Path(__file__).resolve().parents[1]
Agent目录 = 仓库根目录 / "skills" / "academic-research-suite" / "grok" / "agents"
上游目录 = 仓库根目录 / "skills" / "academic-research-suite" / "ars" / "agents"

Agent定义 = {
    "ars-research-architect": {
        "上游": "research_architect_agent.md",
        "上游名称": "research_architect_agent",
        "阶段标记": ("Phase Boundary (v3.9.2)", "Phase 1 (Scoping)", "Methodology Blueprint"),
        "同步标记": (
            "Question drives method",
            "Design-Freeze Checkpoint Audit",
            "institutional determination required",
            "submission_readiness",
        ),
    },
    "ars-synthesis": {
        "上游": "synthesis_agent.md",
        "上游名称": "synthesis_agent",
        "阶段标记": ("Phase Boundary (v3.9.2)", "Phase 3 (Analysis)", "Synthesis Report"),
        "同步标记": (
            "Cross-Paper Tension Inventory",
            "cross_paper_tensions",
            "scholar_confirmation: pending",
            "Knowledge Gaps",
        ),
    },
    "ars-report-compiler": {
        "上游": "report_compiler_agent.md",
        "上游名称": "report_compiler_agent",
        "阶段标记": ("Phase 4", "Phase 6", "APA 7.0"),
        "同步标记": (
            "Knowledge Isolation",
            "AI Disclosure Statement (Mandatory)",
            "Standalone-Mode Self-Gate",
            "Claim Intent Manifest Emission",
        ),
    },
}

允许工具 = ["read_file", "search_replace", "grep", "list_dir"]
禁止工具 = {
    "run_terminal_command",
    "web_search",
    "spawn_subagent",
    "mcp",
    "MCP",
    "terminal",
}


def 解析前置元数据(文本: str) -> tuple[dict[str, object], str]:
    """解析无需第三方依赖的 YAML 子集前置元数据。"""
    匹配 = re.match(r"\A---\n(?P<header>.*?)\n---\n(?P<body>.*)\Z", 文本, re.S)
    if not 匹配:
        raise AssertionError("Agent 文件必须以 --- 包围前置元数据")
    头部: dict[str, object] = {}
    for 行 in 匹配.group("header").splitlines():
        if not 行.strip() or 行.startswith("  "):
            continue
        键, 分隔符, 值 = 行.partition(":")
        if not 分隔符:
            raise AssertionError(f"无法解析元数据行：{行}")
        值 = 值.strip()
        if 值 == ">":
            continue
        if 值.startswith("[") and 值.endswith("]"):
            头部[键.strip()] = [项目.strip() for 项目 in 值[1:-1].split(",") if 项目.strip()]
        elif 值.lower() in {"true", "false"}:
            头部[键.strip()] = 值.lower() == "true"
        else:
            头部[键.strip()] = 值.strip('"')
    描述行 = []
    头部行 = 匹配.group("header").splitlines()
    描述中 = False
    for 行 in 头部行:
        if 行 == "description: >":
            描述中 = True
            continue
        if 描述中:
            if 行.startswith("  "):
                描述行.append(行[2:])
            else:
                描述中 = False
    if 描述行:
        头部["description"] = " ".join(描述行).strip()
    return 头部, 匹配.group("body")


class 原生Agent文件测试(unittest.TestCase):
    """验证三个原生 Agent 的发现元数据、权限边界与上游同步。"""

    def test_恰好包含三个目标Agent(self) -> None:
        self.assertTrue(Agent目录.is_dir())
        self.assertEqual(
            sorted(路径.name for 路径 in Agent目录.glob("*.md")),
            sorted(f"{名称}.md" for 名称 in Agent定义),
        )

    def test_前置元数据符合Grok格式(self) -> None:
        for 名称, 配置 in Agent定义.items():
            with self.subTest(名称=名称):
                路径 = Agent目录 / f"{名称}.md"
                头部, 正文 = 解析前置元数据(路径.read_text(encoding="utf-8"))
                self.assertEqual(头部["name"], 名称)
                self.assertTrue(str(头部["description"]).strip())
                self.assertEqual(头部["prompt_mode"], "full")
                self.assertEqual(头部["model"], "inherit")
                self.assertEqual(头部["permission_mode"], "default")
                self.assertIs(头部["agents_md"], True)
                self.assertEqual(头部["mcpInheritance"], "none")
                self.assertEqual(头部["tools"], 允许工具)
                self.assertTrue(正文.strip())

    def test_工具白名单不含禁止能力(self) -> None:
        for 名称 in Agent定义:
            头部, _ = 解析前置元数据((Agent目录 / f"{名称}.md").read_text(encoding="utf-8"))
            工具文本 = " ".join(头部["tools"])
            for 禁止项 in 禁止工具:
                with self.subTest(名称=名称, 禁止项=禁止项):
                    self.assertNotIn(禁止项, 工具文本)

    def test_正文保留上游实质内容和阶段边界(self) -> None:
        for 名称, 配置 in Agent定义.items():
            with self.subTest(名称=名称):
                路径 = Agent目录 / f"{名称}.md"
                上游路径 = 上游目录 / 配置["上游"]
                _, 正文 = 解析前置元数据(路径.read_text(encoding="utf-8"))
                上游头部, 上游正文 = 解析前置元数据(上游路径.read_text(encoding="utf-8"))
                self.assertEqual(上游头部["name"], 配置["上游名称"])
                self.assertIn(上游正文.strip(), 正文)
                for 标记 in 配置["阶段标记"] + 配置["同步标记"]:
                    self.assertIn(标记, 正文)
                self.assertIn("Grok Build Native-Agent Boundary", 正文)

    def test_正文未退化为路径说明(self) -> None:
        for 名称 in Agent定义:
            正文 = 解析前置元数据((Agent目录 / f"{名称}.md").read_text(encoding="utf-8"))[1]
            self.assertGreater(len(正文), 10000, 名称)
            self.assertNotRegex(正文, r"仅需读取 .*\.md")

    def test_文件名与声明名保持作用域前缀(self) -> None:
        for 名称 in Agent定义:
            self.assertRegex(名称, r"\Aars-[a-z0-9-]+\Z")
            头部, _ = 解析前置元数据((Agent目录 / f"{名称}.md").read_text(encoding="utf-8"))
            self.assertTrue(str(头部["description"]).lower().find("phase") >= 0)


if __name__ == "__main__":
    unittest.main()

