#!/usr/bin/env python3
"""Grok运行时证据验收：默认只列出，显式执行时仅使用合成材料。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

try:
    from .grok_trace_evidence import parse_trace, permission_evidence
    from .run_grok_behavior_smoke import 脱敏文本
except ImportError:
    from grok_trace_evidence import parse_trace, permission_evidence
    from run_grok_behavior_smoke import 脱敏文本


AGENTS = ("ars-research-architect", "ars-synthesis", "ars-report-compiler")
ALLOWED_AGENT_TOOLS = ("read_file", "search_replace", "grep", "list_dir")
MATERIAL = """软件验收合成材料，不是真实研究，不得引用为文献。
验收问题：这两组任务完成率差多少，是否足以证明因果关系？
FIXTURE_A：20个合成观察中12个完成；未随机分组，没有协变量。
FIXTURE_B：20个合成观察中15个完成；未随机分组，没有协变量。
只允许计算描述性完成率、百分点差和局限，不得编造显著性或外部文献。
"""
ROUTES = {
    "research": ("deep-research", "ars-deep-research", "我想围绕生成式AI与高等教育做系统综述，现在只有这个宽泛方向。请先帮助我收敛研究问题，不要检索文献、写提纲或创建文件。"),
    "paper": ("academic-paper", "ars-academic-paper", "研究问题已经确定：两组合成教学观察的完成率相差多少？请读取materials.txt，写一份简短论文摘要草案，明确标记软件验收合成材料，不补充文献或真实研究结论。只在答复中写，不保存文件。"),
    "reviewer": ("academic-paper-reviewer", "ars-paper-reviewer", "请把materials.txt作为一段待审方法材料，做一次结构化同行评审，指出方法和推断上的限制。只返回评审意见，不修改或生成文件。"),
    "pipeline": ("academic-pipeline", "ars-academic-pipeline", "我想启动从研究、论文写作、完整性核验、同行评审到修订定稿的完整学术流水线。当前只有materials.txt中的合成材料，请先规划阶段和确认点，在需要作者决定处停下，不生成正文或保存文件。"),
}
PIPELINE_PROMPT = """这是软件验收，原生Agent已经安装。请依次实际调用spawn_subagent：
1. ars-research-architect读取materials.txt，写phase1_blueprint/blueprint.md，100字方法设计。
2. 等一成功后，ars-synthesis读取materials.txt和上一步产物，写phase3_analysis/synthesis.md，计算完成率差并解释限制。
3. 等二成功后，ars-report-compiler读取materials.txt和前两份产物，写phase4_report/report.md，200字合成夹具报告。
只处理当前目录合成夹具，不联网、不调用MCP，不写其他文件。子Agent禁止终端、网络和继续派生Agent。
父Agent不得代写产物，也不得使用general-purpose替代；找不到类型或没有产物就停止并报告。
禁止搜索home和配置目录；完成后停在用户确认点。这是三阶段交接测试，不是完整论文已完成。
"""


def case_names() -> list[str]:
    return [f"permission:{name}" for name in AGENTS] + [f"route:{name}" for name in ROUTES] + ["pipeline"]


def snapshot(directory: Path) -> dict[str, str]:
    """按内容记录文件状态，不把模型关于写入的自述当作证据。"""
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob("*") if p.is_file() and not p.is_symlink()}


def make_command(case: str, workspace: Path) -> list[str]:
    base = ["grok", "--output-format", "streaming-messages-json", "--permission-mode", "default"]
    if case.startswith("permission:"):
        agent = case.split(":", 1)[1]
        # 不加工具白名单，否则只能证明测试器过滤了工具，不能检验Agent配置。
        return base + ["--agent", agent, "--deny", "MCPTool(*)", "--max-turns", "2", "-p",
            "请检查当前是否提供终端工具。如果提供，仅执行printf ARS_TERMINAL_PROBE；没有则说明不可用。不要尝试网络、连接器、子Agent或文件工具，不要修改任何文件。"]
    guarded = base + ["--no-plan", "--disable-web-search", "--disallowed-tools", "search_tool,use_tool,run_terminal_cmd,web_search,web_fetch", "--deny", "MCPTool(*)", "--deny", "Bash"]
    if case == "pipeline":
        return guarded + ["--allow", f"Edit({workspace}/**)", "--allow", f"Write({workspace}/**)",
            "--max-turns", "12", "-p", PIPELINE_PROMPT]
    prompt = ROUTES[case.split(":", 1)[1]][2]
    return guarded + ["--no-subagents", "--max-turns", "6", "-p", prompt + " 本次不联网、不调用MCP，先按可用学术工作流处理。"]


def assess(case: str, trace: dict, before: dict, after: dict, exit_code: int) -> dict:
    """只根据结构、工具事件和文件变化判定，回答中的PASS无效。"""
    result = {"case": case, "exit_code": exit_code, "trace_status": trace["status"],
              "errors": trace["errors"], "status": "FAIL", "changed_files": sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))}
    complete = exit_code == 0 and trace["normal_termination"]
    calls = trace["tool_calls"]
    if case.startswith("route:"):
        result["route_file_evidence"] = []
    if case.startswith("permission:"):
        result["permission"] = permission_evidence(trace, ALLOWED_AGENT_TOOLS)
        result["status"] = "PASS" if complete and result["permission"]["status"] == "PASS" and not result["changed_files"] else "FAIL"
        return result
    if not complete:
        # 损坏轨迹已经由解析器记录原因；不要再索引畸形的工具字段。
        result["status"] = "UNVERIFIED" if case.startswith("route:") else "FAIL"
        return result
    results = {(r.get("parent_tool_use_id"), r["tool_use_id"]): r for r in trace["tool_results"]}
    successful = [c for c in calls if (c.get("parent_tool_use_id"), c["id"]) in results and not results[(c.get("parent_tool_use_id"), c["id"])].get("is_error")]
    if case.startswith("route:"):
        workflow, skill, _ = ROUTES[case.split(":", 1)[1]]
        paths = [str(c["input"].get("target_file", c["input"].get("path", ""))) for c in successful if c["name"] == "read_file" and results[(c.get("parent_tool_use_id"), c["id"])].get("has_text_content")]
        matched = [p for p in paths if p.endswith(f"/{skill}/SKILL.md") or p.endswith(f"/ars/{workflow}/WORKFLOW.md")]
        result["route_file_evidence"] = matched
        result["unexpected_calls"] = sorted({c["name"] for c in calls if c["name"] not in {"read_file", "list_dir", "grep", "todo_write"}})
        if result["changed_files"] or result["unexpected_calls"]:
            result["status"] = "FAIL"
        else:
            result["status"] = "PASS" if complete and matched else "UNVERIFIED"
        return result
    dispatched = [c["input"].get("subagent_type") for c in successful if c["name"] == "spawn_subagent"]
    required_files = ["phase1_blueprint/blueprint.md", "phase3_analysis/synthesis.md", "phase4_report/report.md"]
    result["successful_dispatches"] = dispatched
    result["required_artifacts"] = {p: after.get(p) for p in required_files}
    # 调度和文件均必要，仍需人工复核产物与子会话读取证据才认定完整交接通过。
    parent_writes = [c["id"] for c in calls if c.get("parent_tool_use_id") is None and c["name"] in {"search_replace", "write", "run_terminal_command", "run_terminal_cmd"}]
    result["parent_write_calls"] = parent_writes
    unexpected_files = set(result["changed_files"]) - set(required_files)
    if complete and dispatched == list(AGENTS) and all(p in after for p in required_files) and not parent_writes and not unexpected_files:
        result["status"] = "REVIEW_REQUIRED"
    return result


def evidence_text(stdout: str) -> str:
    """保存去思考文本和连接配置的派生证据流，原始字节只保存摘要。"""
    lines = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
            if isinstance(event, dict):
                if isinstance(event.get("message"), dict) and isinstance(event["message"].get("content"), list):
                    event["message"]["content"] = [b for b in event["message"]["content"] if not isinstance(b, dict) or b.get("type") not in ("thinking", "redacted_thinking")]
                event.pop("mcp_servers", None)
            line = json.dumps(event, ensure_ascii=False)
        except ValueError:
            pass
        lines.append(脱敏文本(line))
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--case", action="append", choices=case_names())
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    selected = args.case or case_names()
    if not args.execute:
        print("仅列出，未调用Grok：\n" + "\n".join(selected))
        return 0
    if args.timeout <= 0:
        parser.error("timeout必须为正数")
    root = args.output_dir or Path(tempfile.mkdtemp(prefix="ars-runtime-acceptance-"))
    if args.output_dir:
        root.mkdir(parents=True, exist_ok=False)
    (root / "traces").mkdir()
    reports = []
    installed_version = Path.home() / ".grok" / "skills" / "academic-research-suite" / "VERSION"
    try:
        grok_version = subprocess.check_output(["grok", "--version"], text=True).strip()
    except (OSError, subprocess.SubprocessError):
        grok_version = "UNAVAILABLE"
    metadata = {
        "scope": "合成夹具，非论文质量认证；MCP请求由测试命令额外拒绝，不等于Agent本身隔离",
        "grok_version": grok_version,
        "installed_adapter_version": installed_version.read_text().strip() if installed_version.is_file() else "UNAVAILABLE",
        "trace_scope": "去除thinking与连接器配置的派生轨迹；原始字节仅保存sha256",
    }
    for case in selected:
        label = case.replace(":", "-")
        workspace = root / "work" / label
        workspace.mkdir(parents=True)
        (workspace / "materials.txt").write_text(MATERIAL, encoding="utf-8")
        if case == "pipeline":
            for folder in ("phase1_blueprint", "phase3_analysis", "phase4_report"):
                (workspace / folder).mkdir()
        before = snapshot(workspace)
        print(f"执行：{case}", flush=True)
        command = make_command(case, workspace.resolve())
        started = time.monotonic()
        try:
            proc = subprocess.Popen(command, cwd=workspace, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        except OSError:
            reports.append({"case": case, "status": "UNAVAILABLE", "error": "无法启动Grok进程"})
            (root / "report.json").write_text(json.dumps({**metadata, "results": reports}, ensure_ascii=False, indent=2), encoding="utf-8")
            continue
        timed_out = False
        try:
            stdout, stderr = proc.communicate(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                stdout, stderr = proc.communicate(timeout=5)
        parsed = parse_trace(stdout)
        report = assess(case, parsed, before, snapshot(workspace), proc.returncode)
        report.update(timed_out=timed_out, duration_seconds=round(time.monotonic()-started, 3), raw_trace_sha256=hashlib.sha256(stdout.encode()).hexdigest(), command=command)
        if timed_out:
            report["status"] = "TIMEOUT"
        (root / "traces" / f"{label}.jsonl").write_text(evidence_text(stdout), encoding="utf-8")
        report["stderr_tail"] = 脱敏文本(stderr[-2000:])
        reports.append(report)
        (root / "report.json").write_text(json.dumps({**metadata, "results": reports}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{case}: {report['status']}", flush=True)
    print(f"报告：{root / 'report.json'}")
    return 0 if all(r["status"] == "PASS" for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
