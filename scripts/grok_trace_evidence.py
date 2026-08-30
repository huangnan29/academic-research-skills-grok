#!/usr/bin/env python3
"""只读解析 Grok NDJSON 轨迹；模型自述永远不作为工具执行证明。

这里的 PASS 只表示轨迹结构完整、没有已记录错误，不表示研究结论正确。
调用方负责保存原始轨迹及脱敏；本模块保留工具输入与返回内容，不写文件。
"""

from __future__ import annotations

import json
from typing import Any, Iterable


def _reject_constant(value: str) -> None:
    """拒绝 JSON 标准不允许的 NaN 和 Infinity。"""
    raise ValueError(value)


def _tool_names(value: Any) -> list[str] | None:
    """接受工具名列表或带 name 的工具定义，拒绝缺失或不完整的工具表。"""
    if not isinstance(value, list):
        return None
    names = []
    for item in value:
        name = item if isinstance(item, str) else item.get("name") if isinstance(item, dict) else None
        if not isinstance(name, str) or not name.strip():
            return None
        names.append(name)
    if len(set(names)) != len(names):
        return None
    return names


def _valid_result_content(value: Any) -> bool:
    """只接受字符串或结构完整的文本、图片内容块；未知格式不推定有效。"""
    if isinstance(value, str):
        return True
    if not isinstance(value, list):
        return False
    for block in value:
        if not isinstance(block, dict):
            return False
        if block.get("type") == "text":
            if not isinstance(block.get("text"), str):
                return False
        elif block.get("type") == "image":
            source = block.get("source")
            if not isinstance(source, dict):
                return False
            if source.get("type") == "url":
                if not isinstance(source.get("url"), str) or not source["url"]:
                    return False
            elif source.get("type") == "base64":
                if not all(isinstance(source.get(key), str) and source[key] for key in ("data", "media_type")):
                    return False
            else:
                return False
        else:
            return False
    return True


def _has_text_content(value: Any) -> bool:
    """空返回可以是合法工具结果，但不证明已读取实际文本内容。"""
    if isinstance(value, str):
        return bool(value.strip())
    return isinstance(value, list) and any(
        isinstance(block, dict) and block.get("type") == "text"
        and isinstance(block.get("text"), str) and bool(block["text"].strip())
        for block in value
    )


def parse_trace(text: str) -> dict[str, Any]:
    """解析完整 NDJSON，保留机器事件证据并拒绝损坏、截断或多重终止。

空白行允许存在；未知的合法对象事件只作记录。权限断言应调用
permission_evidence，而不是查找 assistant 文本或 result.result 中的 PASS。
"""
    report: dict[str, Any] = {
        "status": "FAIL", "valid_init": False, "init": None,
        "init_tools_present": False, "init_tools_valid": False,
        "tools": None, "skills": None, "tool_calls": [], "tool_results": [],
        "unknown_events": [], "unknown_blocks": [], "errors": [],
        "unverified": [], "unpaired_tool_calls": [],
        "ended_with_result": False, "normal_termination": False,
        "result": None, "is_error": None, "stop_reason": None,
        "event_count": 0,
    }
    errors = report["errors"]
    terminal_seen = False
    init_count = 0
    last_type = None
    call_keys: set[tuple[Any, str]] = set()
    pending_client_calls: set[tuple[Any, str]] = set()
    completed_client_calls: set[tuple[Any, str]] = set()
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        if terminal_seen:
            errors.append(f"第{line_number}行：终止后仍有事件")
        try:
            # 非有限数不是合法 JSON，不能被 Python 默认宽松行为接受。
            event = json.loads(line, parse_constant=_reject_constant)
        except (ValueError, TypeError):
            errors.append(f"第{line_number}行：JSON 损坏")
            last_type = None
            continue
        report["event_count"] += 1
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            errors.append(f"第{line_number}行：事件必须是包含 type 的对象")
            last_type = None
            continue
        event_type = event["type"]
        last_type = event_type
        if event_type == "system" and event.get("subtype") == "init":
            init_count += 1
            if init_count != 1:
                errors.append(f"第{line_number}行：重复 init")
                continue
            if report["event_count"] != 1:
                errors.append(f"第{line_number}行：init 不是首个事件")
            report["init"] = event
            report["valid_init"] = report["event_count"] == 1
            report["init_tools_present"] = "tools" in event
            names = _tool_names(event.get("tools"))
            report["init_tools_valid"] = names is not None
            report["tools"] = names
            report["skills"] = event.get("skills")
            if "tools" in event and names is None:
                errors.append(f"第{line_number}行：init.tools 格式无效")
        elif event_type == "result":
            if terminal_seen:
                errors.append(f"第{line_number}行：重复终止 result")
                continue
            terminal_seen = True
            report["result"] = event
            report["is_error"] = event.get("is_error")
            report["stop_reason"] = event.get("stop_reason")
            if event.get("is_error") is not False:
                errors.append(f"第{line_number}行：result 未明确报告 is_error=false")
            if event.get("subtype") not in (None, "success"):
                errors.append(f"第{line_number}行：result subtype 非成功")
            if event.get("stop_reason") not in ("end_turn", "stop", "stop_sequence"):
                errors.append(f"第{line_number}行：result stop_reason 非正常结束")
        elif event_type in ("assistant", "user"):
            message = event.get("message")
            if not isinstance(message, dict) or not isinstance(message.get("content"), list):
                errors.append(f"第{line_number}行：消息 content 格式无效")
                continue
            parent_id = event.get("parent_tool_use_id")
            if parent_id is not None and not isinstance(parent_id, str):
                errors.append(f"第{line_number}行：parent_tool_use_id 格式无效")
                continue
            for block in message["content"]:
                if not isinstance(block, dict):
                    errors.append(f"第{line_number}行：消息内容块格式无效")
                    continue
                block_type = block.get("type")
                if event_type == "assistant" and block_type in ("tool_use", "server_tool_use"):
                    call = dict(block)
                    call.update(parent_tool_use_id=parent_id, line_number=line_number)
                    report["tool_calls"].append(call)
                    if not isinstance(call.get("id"), str) or not call["id"] or not isinstance(call.get("name"), str) or not call["name"] or not isinstance(call.get("input"), dict):
                        errors.append(f"第{line_number}行：工具调用缺少有效 id/name/input")
                        continue
                    key = (parent_id, call["id"])
                    if key in call_keys:
                        errors.append(f"第{line_number}行：重复工具调用 id")
                        continue
                    call_keys.add(key)
                    if block_type == "tool_use":
                        pending_client_calls.add(key)
                    else:
                        # 服务端工具有独立返回协议；未实现配对时不得冒充成功执行。
                        report["unverified"].append(f"第{line_number}行：server_tool_use 专属结果配对尚未实现")
                elif event_type == "user" and block_type == "tool_result":
                    result = dict(block)
                    result.update(parent_tool_use_id=parent_id, line_number=line_number)
                    result["content_valid"] = _valid_result_content(result.get("content"))
                    result["has_text_content"] = result["content_valid"] and _has_text_content(result.get("content"))
                    report["tool_results"].append(result)
                    if not result["content_valid"]:
                        errors.append(f"第{line_number}行：tool_result content 缺失或格式无效")
                    if not isinstance(result.get("tool_use_id"), str) or not result["tool_use_id"]:
                        errors.append(f"第{line_number}行：工具返回缺少有效 tool_use_id")
                    else:
                        key = (parent_id, result["tool_use_id"])
                        if key in completed_client_calls:
                            errors.append(f"第{line_number}行：重复 tool_result")
                        elif key not in pending_client_calls:
                            errors.append(f"第{line_number}行：孤立 tool_result，找不到同父调用的客户端工具请求")
                        else:
                            pending_client_calls.remove(key)
                            completed_client_calls.add(key)
                    if result.get("is_error", False) is not False:
                        errors.append(f"第{line_number}行：工具返回错误")
                elif block_type not in ("text", "thinking", "redacted_thinking"):
                    report["unknown_blocks"].append({"line_number": line_number, "event_type": event_type, "type": block_type})
        else:
            report["unknown_events"].append({"line_number": line_number, "type": event_type, "subtype": event.get("subtype")})
    if not report["valid_init"] or init_count != 1:
        errors.append("缺少唯一且位于开头的合法 init")
        report["valid_init"] = False
    if not terminal_seen:
        errors.append("缺少终止 result")
    # 同一个调用 ID 在不同父上下文中互不抵消，缺少结果不能证明执行完成。
    for parent_id, call_id in sorted(pending_client_calls, key=lambda key: (key[0] or "", key[1])):
        report["unpaired_tool_calls"].append({"id": call_id, "parent_tool_use_id": parent_id})
    if pending_client_calls:
        errors.append("客户端 tool_use 缺少同父调用的 tool_result")
    report["ended_with_result"] = terminal_seen and last_type == "result" and not any("终止后" in error for error in errors)
    report["normal_termination"] = report["ended_with_result"] and report["is_error"] is False and not errors and not report["unverified"]
    if report["normal_termination"]:
        report["status"] = "PASS"
    elif not errors and report["unverified"]:
        report["status"] = "UNVERIFIED"
    return report


def permission_evidence(report: dict[str, Any], allowed_tools: Iterable[str]) -> dict[str, Any]:
    """比较真实工具表与允许集合；不声称已证明沙箱或所有绕过路径安全。"""
    if isinstance(allowed_tools, (str, bytes)):
        raise ValueError("allowed_tools 必须是工具名集合而不是字符串")
    allowed = list(allowed_tools)
    if any(not isinstance(name, str) or not name for name in allowed):
        raise ValueError("allowed_tools 含无效工具名")
    allowed_set = set(allowed)
    actual = report.get("tools")
    available = report.get("init_tools_present") is True and report.get("init_tools_valid") is True and isinstance(actual, list)
    extra = sorted(set(actual) - allowed_set) if available else []
    missing = sorted(allowed_set - set(actual)) if available else []
    observed = sorted({call["name"] for call in report.get("tool_calls", []) if isinstance(call.get("name"), str)})
    forbidden = sorted(set(observed) - allowed_set)
    complete = report.get("valid_init") is True and report.get("normal_termination") is True and report.get("status") == "PASS"
    surface_match = bool(complete and available and not extra and not missing)
    return {
        "status": "PASS" if surface_match and not forbidden else "FAIL",
        "tool_surface_match": surface_match,
        "tool_surface_available": available,
        "extra_tools": extra, "missing_tools": missing,
        "observed_tools": observed, "forbidden_observed_tools": forbidden,
        "scope": "仅验证 init 工具表及轨迹中的调用，不证明未尝试能力的机械隔离；模型文本自述未参与判定。",
    }
