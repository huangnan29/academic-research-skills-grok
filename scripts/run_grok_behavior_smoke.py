#!/usr/bin/env python3
"""运行 ARS-Grok Build 的受限行为契约冒烟测试。

默认模式只列出案例，不启动 Grok。只有显式传入 ``--execute`` 时，才会
逐案调用本机 ``grok -p``。案例提示词本身禁止联网、写文件和研究执行；
执行器还会对捕获内容做凭证脱敏，避免把令牌或私钥写入终端和 JSON 报告。
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


仓库根目录 = Path(__file__).resolve().parents[1]
默认案例路径 = 仓库根目录 / "tests" / "behavior_cases.json"
默认超时秒数 = 60.0
案例数量 = 5


class 行为契约错误(ValueError):
    """行为案例或命令行参数不符合安全契约。"""


def _文字化(value: object) -> str:
    """把 subprocess 返回的文本或字节安全转换为字符串。"""

    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


_脱敏规则 = (
    re.compile(
        r"(?is)-----BEGIN [^-\r\n]*PRIVATE KEY-----.*?-----END [^-\r\n]*PRIVATE KEY-----"
    ),
    re.compile(
        r"(?i)\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
        r"sk-[A-Za-z0-9_-]{20,}|xai-[A-Za-z0-9_-]{20,})\b"
    ),
    re.compile(r"(?i)(\b(?:bearer|token)\s+)[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(
        r"(?i)(\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|secret)\s*[:=]\s*)"
        r"([^\s,;]+)"
    ),
)


def 脱敏文本(text: object) -> str:
    """脱敏常见令牌、授权头、密码和私钥；不改变普通行为标记。"""

    脱敏后 = _文字化(text)
    脱敏后 = _脱敏规则[0].sub("[REDACTED_PRIVATE_KEY]", 脱敏后)
    脱敏后 = _脱敏规则[1].sub("[REDACTED_TOKEN]", 脱敏后)
    脱敏后 = _脱敏规则[2].sub(r"\1[REDACTED_TOKEN]", 脱敏后)
    脱敏后 = _脱敏规则[3].sub(r"\1[REDACTED_SECRET]", 脱敏后)
    return 脱敏后


def _正则文本(pattern: object) -> str:
    """读取 required/forbidden 条目的正则文本。"""

    if isinstance(pattern, str) and pattern:
        return pattern
    if isinstance(pattern, Mapping) and isinstance(pattern.get("pattern"), str):
        if pattern["pattern"]:
            return pattern["pattern"]
    raise 行为契约错误("required/forbidden 必须是非空正则字符串或带 pattern 的对象")


def _案例标识(case: Mapping[str, Any]) -> str:
    """返回用于错误信息的案例标识，不回显提示词。"""

    value = case.get("id")
    return value if isinstance(value, str) else "<unknown-case>"


def 验证案例定义(case: Mapping[str, Any]) -> None:
    """验证一个案例的结构和受限提示词边界。"""

    case_id = _案例标识(case)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", case_id):
        raise 行为契约错误(f"案例标识无效：{case_id}")
    if not isinstance(case.get("name"), str) or not case["name"].strip():
        raise 行为契约错误(f"案例缺少名称：{case_id}")
    prompt = case.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise 行为契约错误(f"案例缺少提示词：{case_id}")
    for restriction in ("不联网", "不写文件", "只做路由/边界测试"):
        if restriction not in prompt:
            raise 行为契约错误(f"案例提示词缺少安全限制：{case_id}")
    required = case.get("required")
    forbidden = case.get("forbidden")
    if not isinstance(required, list) or not required:
        raise 行为契约错误(f"案例缺少 required 正则：{case_id}")
    if not isinstance(forbidden, list) or not forbidden:
        raise 行为契约错误(f"案例缺少 forbidden 正则：{case_id}")
    for pattern in (*required, *forbidden):
        re.compile(_正则文本(pattern))


def 读取案例(path: Path | str = 默认案例路径) -> list[dict[str, Any]]:
    """读取并验证五个行为案例，不读取任何用户研究材料。"""

    案例文件 = Path(path)
    try:
        原始 = json.loads(案例文件.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise 行为契约错误("无法读取行为案例定义") from error
    if not isinstance(原始, dict) or 原始.get("schema_version") != "1.0":
        raise 行为契约错误("行为案例 schema_version 无效")
    合同 = 原始.get("runner_contract")
    if not isinstance(合同, dict):
        raise 行为契约错误("缺少 runner_contract")
    if 合同.get("default_mode") != "list_only":
        raise 行为契约错误("默认模式必须是 list_only")
    if 合同.get("execute_flag") != "--execute":
        raise 行为契约错误("执行开关必须是 --execute")
    if 合同.get("command") != ["grok", "-p"]:
        raise 行为契约错误("Grok 命令契约必须是 grok -p")
    限制 = 合同.get("prompt_constraints")
    if not isinstance(限制, list) or set(限制) != {"不联网", "不写文件", "只做路由/边界测试"}:
        raise 行为契约错误("runner_contract 的提示词限制不完整")
    案例 = 原始.get("cases")
    if not isinstance(案例, list) or len(案例) != 案例数量:
        raise 行为契约错误(f"行为案例数量必须为 {案例数量}")
    结果: list[dict[str, Any]] = []
    已见标识: set[str] = set()
    for item in 案例:
        if not isinstance(item, dict):
            raise 行为契约错误("行为案例必须是对象")
        验证案例定义(item)
        case_id = _案例标识(item)
        if case_id in 已见标识:
            raise 行为契约错误(f"行为案例标识重复：{case_id}")
        已见标识.add(case_id)
        结果.append(item)
    return 结果


def 选择案例(
    cases: Sequence[Mapping[str, Any]], case_ids: Iterable[str] | None = None
) -> list[Mapping[str, Any]]:
    """按 ``--case`` 选择案例，未指定时保持 JSON 中的固定顺序。"""

    请求 = list(case_ids or [])
    if not 请求:
        return list(cases)
    索引 = {str(case["id"]): case for case in cases}
    if any(case_id not in 索引 for case_id in 请求):
        raise 行为契约错误("存在未定义的行为案例")
    return [索引[case_id] for case_id in 请求]


def _匹配结果(case: Mapping[str, Any], output: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """按案例中的 required/forbidden 正则计算逐项匹配结果。"""

    # Grok 可能在第一个标记前输出一小段进度文字。只抽取稳定的大写
    # KEY=VALUE 标记并逐行规范化，保留原有行首锚点和禁止项检查强度。
    contract_output = "\n".join(
        re.findall(r"\b[A-Z][A-Z0-9_]*=[A-Z0-9_]+\b", output)
    )
    required_results = []
    for raw_pattern in case["required"]:
        pattern = _正则文本(raw_pattern)
        required_results.append(
            {
                "pattern": 脱敏文本(pattern),
                "matched": re.search(pattern, contract_output) is not None,
            }
        )
    forbidden_results = []
    for raw_pattern in case["forbidden"]:
        pattern = _正则文本(raw_pattern)
        forbidden_results.append(
            {
                "pattern": 脱敏文本(pattern),
                "matched": re.search(pattern, contract_output) is not None,
            }
        )
    return required_results, forbidden_results


def 判定输出(
    case: Mapping[str, Any],
    output: object,
    returncode: int | None = 0,
    timed_out: bool = False,
    error: object | None = None,
) -> dict[str, Any]:
    """根据脱敏后的输出和进程状态返回可序列化的行为判定。"""

    文本 = 脱敏文本(output)
    required_results, forbidden_results = _匹配结果(case, 文本)
    required_passed = all(item["matched"] for item in required_results)
    forbidden_passed = not any(item["matched"] for item in forbidden_results)
    if timed_out:
        status = "TIMEOUT"
    elif error:
        status = "ERROR"
    elif returncode != 0 or not required_passed or not forbidden_passed:
        status = "FAIL"
    else:
        status = "PASS"
    return {
        "id": _案例标识(case),
        "name": case.get("name", ""),
        "returncode": returncode,
        "timed_out": bool(timed_out),
        "status": status,
        "passed": status == "PASS",
        "required": required_results,
        "forbidden": forbidden_results,
        "output": 文本,
        "stdout": 文本,
        "stderr": "",
        "error": 脱敏文本(error) if error else None,
    }


evaluate_output = 判定输出
evaluate_case = 判定输出


def 执行案例(
    case: Mapping[str, Any],
    timeout: float = 默认超时秒数,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    """执行一个案例；只调用固定的本机 ``grok -p`` 命令。"""

    if not math.isfinite(timeout) or timeout <= 0:
        raise 行为契约错误("超时必须是正数")
    prompt = case["prompt"]
    try:
        completed = runner(
            ["grok", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        partial = _文字化(getattr(error, "output", ""))
        partial_error = _文字化(getattr(error, "stderr", ""))
        结果 = 判定输出(
            case,
            partial + ("\n" + partial_error if partial_error else ""),
            returncode=None,
            timed_out=True,
            error="Grok 调用超时",
        )
        结果["stdout"] = 脱敏文本(partial)
        结果["stderr"] = 脱敏文本(partial_error)
        return 结果
    except FileNotFoundError:
        return 判定输出(case, "", returncode=None, error="找不到本机 grok 命令")
    except OSError:
        return 判定输出(case, "", returncode=None, error="本机 Grok 调用失败")
    stdout = _文字化(getattr(completed, "stdout", ""))
    stderr = _文字化(getattr(completed, "stderr", ""))
    output = stdout + ("\n" + stderr if stderr else "")
    结果 = 判定输出(case, output, returncode=getattr(completed, "returncode", None))
    结果["stdout"] = 脱敏文本(stdout)
    结果["stderr"] = 脱敏文本(stderr)
    return 结果


run_grok_case = 执行案例


def _摘要案例(case: Mapping[str, Any]) -> dict[str, str]:
    """生成不含提示词和执行输出的案例摘要。"""

    return {"id": _案例标识(case), "name": str(case.get("name", ""))}


def 构建报告(
    cases: Sequence[Mapping[str, Any]],
    results: Sequence[Mapping[str, Any]] | None = None,
    executed: bool = False,
) -> dict[str, Any]:
    """构造不包含凭证和用户材料的 JSON 报告。"""

    报告结果 = list(results or [])
    return {
        "schema_version": "1.0",
        "runner": "run_grok_behavior_smoke.py",
        "mode": "execute" if executed else "list",
        "executed": bool(executed),
        "case_ids": [_案例标识(case) for case in cases],
        "cases": [_摘要案例(case) for case in cases],
        "results": 报告结果,
        "passed": all(bool(result.get("passed")) for result in 报告结果) if executed else None,
    }


def 写入报告(path: Path | str, report: Mapping[str, Any]) -> None:
    """以 UTF-8 JSON 写报告；报告内容已经在判定阶段脱敏。"""

    报告路径 = Path(path).expanduser()
    try:
        报告路径.parent.mkdir(parents=True, exist_ok=True)
        报告路径.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, UnicodeError, TypeError) as error:
        raise 行为契约错误("无法写入 JSON 报告") from error


def _正数(value: str) -> float:
    """解析正的有限超时秒数。"""

    try:
        parsed = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("超时必须是正数") from error
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("超时必须是正数")
    return parsed


def 构建解析器() -> argparse.ArgumentParser:
    """创建命令行解析器。"""

    parser = argparse.ArgumentParser(description="ARS-Grok Build 受限行为契约冒烟测试")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="显式逐案调用本机 grok -p；默认只列出案例",
    )
    parser.add_argument(
        "--case",
        dest="case_ids",
        action="append",
        metavar="CASE_ID",
        help="只选择一个案例；可重复传入以选择多个案例",
    )
    parser.add_argument(
        "--timeout",
        type=_正数,
        default=默认超时秒数,
        metavar="SECONDS",
        help=f"每个案例的超时秒数，默认 {默认超时秒数:g}",
    )
    parser.add_argument(
        "--report",
        type=Path,
        metavar="PATH",
        help="把脱敏后的列表或执行结果写入 JSON 文件",
    )
    return parser


def _打印列表(cases: Sequence[Mapping[str, Any]]) -> None:
    """打印默认的案例列表，不打印提示词或执行输出。"""

    print("ARS-Grok 行为案例（仅列出，未调用 Grok）：")
    for index, case in enumerate(cases, start=1):
        print(f"{index}. {_案例标识(case)} - {case.get('name', '')}")
    print("使用 --execute 才会逐案调用本机 grok -p。")


def 主函数(argv: Sequence[str] | None = None) -> int:
    """执行命令行入口；返回 0 表示列表成功或全部案例通过。"""

    parser = 构建解析器()
    args = parser.parse_args(argv)
    try:
        cases = 读取案例()
        selected = 选择案例(cases, args.case_ids)
    except 行为契约错误 as error:
        print(f"行为测试参数或案例无效：{脱敏文本(error)}", file=sys.stderr)
        return 2

    if not args.execute:
        _打印列表(selected)
        if args.report:
            try:
                写入报告(args.report, 构建报告(selected, executed=False))
            except 行为契约错误 as error:
                print(f"行为测试报告失败：{脱敏文本(error)}", file=sys.stderr)
                return 2
        return 0

    results = []
    for case in selected:
        result = 执行案例(case, timeout=args.timeout)
        results.append(result)
        print(f"{result['id']}: {result['status']}")
    report = 构建报告(selected, results=results, executed=True)
    if args.report:
        try:
            写入报告(args.report, report)
        except 行为契约错误 as error:
            print(f"行为测试报告失败：{脱敏文本(error)}", file=sys.stderr)
            return 2
    return 0 if report["passed"] else 1


main = 主函数
load_behavior_cases = 读取案例
select_cases = 选择案例
redact_sensitive = 脱敏文本
build_parser = 构建解析器


if __name__ == "__main__":
    raise SystemExit(主函数())
