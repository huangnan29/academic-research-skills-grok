#!/usr/bin/env python3
"""Grok PreToolUse 写入范围 Hook。

Grok 的事件字段使用 camelCase。本适配层只把已声明的
``search_replace`` 与 ``run_terminal_command`` 映射为上游 guard 理解的
``Write`` 与 ``Bash``，然后复用上游确定性决策函数；没有改变原 guard 的
范围、基础设施保护或 Bucket A Bash 拒绝策略。导入、解析和环境异常均
输出允许继续的 pass-through JSON，以符合可选 Hook 的 fail-open 约定。
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

# Hook 运行时会按路径加载随包的上游脚本；禁止在 vendored ars/ 下生成
# __pycache__，否则后续安装器的确定性目录摘要会被运行时副产物污染。
sys.dont_write_bytecode = True


技能根目录 = Path(__file__).resolve().parents[2]
原生工具映射 = {
    "search_replace": "Write",
    "run_terminal_command": "Bash",
}
# Grok 顶层 Agent 使用作用域前缀；上游守卫的 manifest 绑定的是原始
# 下划线名称。只做固定的一对一别名转换，未知名称不会被猜测或升级权限。
Agent名称映射 = {
    "ars-research-architect": "research_architect_agent",
    "ars-synthesis": "synthesis_agent",
    "ars-report-compiler": "report_compiler_agent",
}
路径字段 = ("filePath", "file_path", "path")


def _输出(内容: dict[str, Any]) -> None:
    """输出单个 Grok 可解析的 JSON 对象。"""

    sys.stdout.write(json.dumps(内容, ensure_ascii=False, separators=(",", ":")))
    sys.stdout.write("\n")


def _pass_through() -> None:
    """允许 Grok 继续走正常权限流程。"""

    _输出({"decision": "allow"})


def _读取事件() -> dict[str, Any]:
    """严格读取一个 JSON 对象，异常交给 fail-open 主流程。"""

    原始 = sys.stdin.read()
    事件 = json.loads(原始)
    if not isinstance(事件, dict):
        raise ValueError("Hook 事件必须是对象")
    return 事件


def _加载上游守卫() -> ModuleType:
    """从随包的上游脚本加载纯决策函数，不执行其命令行入口。"""

    脚本路径 = 技能根目录 / "ars" / "scripts" / "ars_write_scope_guard.py"
    规格 = importlib.util.spec_from_file_location("ars_grok_upstream_guard", 脚本路径)
    if 规格 is None or 规格.loader is None:
        raise ImportError("无法加载范围守卫")
    模块 = importlib.util.module_from_spec(规格)
    规格.loader.exec_module(模块)
    return 模块


def _取字符串(对象: dict[str, Any], 字段: tuple[str, ...]) -> str | None:
    """读取第一个非空字符串字段；冲突路径不猜测。"""

    值列表 = [对象.get(名称) for 名称 in 字段 if isinstance(对象.get(名称), str)]
    值列表 = [值 for 值 in 值列表 if 值]
    if not 值列表:
        return None
    if any(值 != 值列表[0] for 值 in 值列表[1:]):
        return None
    return 值列表[0]


def _适配工具输入(原生工具名: str, 原生输入: Any) -> dict[str, Any]:
    """把 Grok camelCase 输入收敛为上游 guard 的最小输入形状。"""

    if not isinstance(原生输入, dict):
        return {}
    if 原生工具名 == "search_replace":
        文件路径 = _取字符串(原生输入, 路径字段)
        if 文件路径 is None:
            return {}
        结果: dict[str, Any] = {"file_path": 文件路径}
        # 这些字段只是为了保留上游 Write 输入形状；guard 不读取正文。
        if isinstance(原生输入.get("content"), str):
            结果["content"] = 原生输入["content"]
        return 结果
    命令 = _取字符串(原生输入, ("command", "commandText"))
    return {"command": 命令} if 命令 is not None else {}


def _适配事件(事件: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """转换工具、输入、agent 和工作区字段，并返回工作区路径。"""

    原生工具名 = 事件.get("toolName")
    if not isinstance(原生工具名, str) or 原生工具名 not in 原生工具映射:
        raise ValueError("事件工具不在 Hook matcher 范围内")
    工作区 = _取字符串(事件, ("workspaceRoot", "projectRoot", "cwd"))
    工作区路径 = 工作区 or os.getcwd()
    适配事件 = dict(事件)
    适配事件["tool_name"] = 原生工具映射[原生工具名]
    适配事件["tool_input"] = _适配工具输入(
        原生工具名, 事件.get("toolInput")
    )
    适配事件["cwd"] = 事件.get("cwd") or 工作区路径
    代理类型 = _取字符串(事件, ("subagentType", "agentType", "agent_type"))
    if 代理类型 is not None:
        适配事件["agent_type"] = Agent名称映射.get(代理类型, 代理类型)
    return 适配事件, 工作区路径


def _决策(事件: dict[str, Any]) -> dict[str, Any]:
    """调用上游纯决策函数，并只接受其明确 deny。"""

    守卫 = _加载上游守卫()
    适配事件, 工作区 = _适配事件(事件)
    清单 = 守卫._load_manifest()
    决定 = 守卫.evaluate_decision(
        适配事件,
        清单,
        工作区,
        str(技能根目录),
    )
    if not isinstance(决定, dict) or 决定.get("decision") != "deny":
        return {"decision": "allow"}
    原因 = 决定.get("reason")
    return {
        "decision": "deny",
        "reason": 原因 if isinstance(原因, str) else "ARS 写入范围守卫拒绝了该工具调用。",
    }


def main() -> int:
    """处理一次事件；任何守卫异常都保持 fail-open。"""

    try:
        事件 = _读取事件()
        工具名 = 事件.get("toolName")
        if 工具名 not in 原生工具映射:
            _pass_through()
        else:
            _输出(_决策(事件))
    except Exception:
        _pass_through()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
