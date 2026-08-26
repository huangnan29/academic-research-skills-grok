#!/usr/bin/env python3
"""验证 ARS-Grok Build 技能包的静态结构和关键契约。"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


仓库根目录 = Path(__file__).resolve().parents[1]
技能目录 = 仓库根目录 / "skills" / "academic-research-suite"
预期命令 = {
    "ars-3w",
    "ars-abstract",
    "ars-cache-invalidate",
    "ars-citation-check",
    "ars-disclosure",
    "ars-format-convert",
    "ars-full",
    "ars-lit-review",
    "ars-mark-read",
    "ars-outline",
    "ars-plan",
    "ars-rebuttal-audit",
    "ars-reviewer",
    "ars-revision",
    "ars-revision-coach",
    "ars-unmark-read",
}
预期工作流 = {
    "deep-research/WORKFLOW.md",
    "academic-paper/WORKFLOW.md",
    "academic-paper-reviewer/WORKFLOW.md",
    "academic-pipeline/WORKFLOW.md",
    "experiment-agent/WORKFLOW.md",
}


def 计算目录摘要(目录: Path) -> str:
    """按相对路径和文件内容计算稳定摘要。"""

    总摘要 = hashlib.sha256()
    for 文件 in sorted(路径 for 路径 in 目录.rglob("*") if 路径.is_file()):
        相对路径 = 文件.relative_to(目录).as_posix().encode("utf-8")
        文件摘要 = hashlib.sha256(文件.read_bytes()).digest()
        总摘要.update(相对路径)
        总摘要.update(b"\0")
        总摘要.update(文件摘要)
        总摘要.update(b"\n")
    return 总摘要.hexdigest()


def 读取前置元数据(文本: str) -> str:
    """提取 SKILL.md 的 YAML 前置元数据文本。"""

    匹配 = re.match(r"\A---\n(.*?)\n---\n", 文本, flags=re.DOTALL)
    if not 匹配:
        raise ValueError("SKILL.md 缺少有效的 YAML 前置元数据")
    return 匹配.group(1)


def 验证() -> list[str]:
    """返回所有验证错误；空列表代表通过。"""

    错误: list[str] = []
    必需文件 = ["SKILL.md", "VERSION", "manifest.json", "LICENSE", "THIRD_PARTY.md"]
    for 名称 in 必需文件:
        if not (技能目录 / 名称).is_file():
            错误.append(f"缺少必需文件：{名称}")

    if 错误:
        return 错误

    版本 = (技能目录 / "VERSION").read_text(encoding="utf-8").strip()
    try:
        清单 = json.loads((技能目录 / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as 异常:
        return [f"manifest.json 无法读取：{异常}"]

    if 清单.get("adapter_version") != 版本:
        错误.append("VERSION 与 manifest.json adapter_version 不一致")
    if 清单.get("generated_for") != "grok-build":
        错误.append("manifest.json generated_for 必须是 grok-build")
    if 清单.get("license") != "CC-BY-NC-4.0":
        错误.append("清单没有保留 CC-BY-NC-4.0 许可证标识")

    技能文本 = (技能目录 / "SKILL.md").read_text(encoding="utf-8")
    try:
        元数据 = 读取前置元数据(技能文本)
    except ValueError as 异常:
        错误.append(str(异常))
        元数据 = ""
    if not re.search(rf'^\s*version:\s*["\']?{re.escape(版本)}["\']?\s*$', 元数据, re.MULTILINE):
        错误.append("SKILL.md metadata.version 与 VERSION 不一致")
    for 工具名 in ("read_file", "web_search", "run_terminal_command", "spawn_subagent"):
        if 工具名 not in 元数据:
            错误.append(f"SKILL.md 前置元数据缺少 Grok 工具：{工具名}")
    if "Codex Runtime Mapping" in 技能文本:
        错误.append("根技能仍包含 Codex Runtime Mapping 标题")

    上游目录 = 技能目录 / "ars"
    实际工作流 = {
        路径.relative_to(上游目录).as_posix() for 路径 in 上游目录.rglob("WORKFLOW.md")
    }
    if 实际工作流 != 预期工作流:
        错误.append(f"上游工作流入口不匹配：{sorted(实际工作流)}")
    嵌套技能 = list(上游目录.rglob("SKILL.md"))
    if 嵌套技能:
        错误.append(f"ars/ 中存在会重复注册的 SKILL.md：{嵌套技能[0]}")

    命令目录 = 技能目录 / "grok" / "commands"
    实际命令 = {路径.stem for 路径 in 命令目录.glob("*.md")}
    if 实际命令 != 预期命令:
        错误.append(f"Grok 命令集合不匹配：{sorted(实际命令)}")
    for 命令文件 in 命令目录.glob("*.md"):
        内容 = 命令文件.read_text(encoding="utf-8")
        if "$ARGUMENTS" not in 内容:
            错误.append(f"命令没有传递参数：{命令文件.name}")
        if "academic-research-suite" not in 内容:
            错误.append(f"命令没有加载根技能：{命令文件.name}")

    运行时清单 = 技能目录 / "grok" / "full-runtime-manifest.json"
    运行时映射 = 技能目录 / "grok" / "runtime-mapping.md"
    if not 运行时清单.is_file():
        错误.append("缺少 Grok 完整运行时清单")
    if not 运行时映射.is_file():
        错误.append("缺少 Grok 运行时映射")

    # 清单中记录的文件数用于发现意外漏拷贝；目录摘要另由安装前测试复核。
    实际文件数 = sum(1 for 路径 in 上游目录.rglob("*") if 路径.is_file())
    预期文件数 = 清单.get("source_overlay", {}).get("vendored_file_count")
    if 实际文件数 != 预期文件数:
        错误.append(f"ars/ 文件数不一致：预期 {预期文件数}，实际 {实际文件数}")
    实际目录摘要 = 计算目录摘要(上游目录)
    预期目录摘要 = 清单.get("source_overlay", {}).get("vendored_tree_sha256")
    if 实际目录摘要 != 预期目录摘要:
        错误.append("ars/ 目录摘要与 manifest.json 不一致")

    return 错误


def 主函数() -> int:
    """运行验证并返回适合自动化使用的退出码。"""

    错误 = 验证()
    if 错误:
        print("ARS-Grok Build 技能验证失败：")
        for 条目 in 错误:
            print(f"- {条目}")
        return 1
    print("ARS-Grok Build 技能静态验证通过。")
    return 0


if __name__ == "__main__":
    sys.exit(主函数())
