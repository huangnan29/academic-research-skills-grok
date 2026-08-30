"""离线验证运行时验收器，只使用合成轨迹，不启动真实 Grok。"""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import unittest
from unittest import mock

from scripts import run_grok_runtime_acceptance as runner
from scripts.grok_trace_evidence import parse_trace


def 生成轨迹(calls=(), tools=(), text="", errors=(), omit_results=()):
    """构造完整机器事件，文本自述与工具事件明确分离。"""
    events = [{"type": "system", "subtype": "init", "tools": list(tools), "skills": []}]
    if text:
        events.append({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})
    for index, (name, arguments) in enumerate(calls):
        call_id = f"call-{index}"
        events.append({"type": "assistant", "parent_tool_use_id": None, "message": {"content": [
            {"type": "tool_use", "id": call_id, "name": name, "input": arguments},
        ]}})
        if index not in omit_results:
            events.append({"type": "user", "parent_tool_use_id": None, "message": {"content": [
                {"type": "tool_result", "tool_use_id": call_id, "content": "合成返回", "is_error": index in errors},
            ]}})
    events.append({"type": "result", "subtype": "success", "is_error": False, "stop_reason": "end_turn", "result": "合成终止"})
    return parse_trace("\n".join(json.dumps(event) for event in events))


class 运行时验收测试(unittest.TestCase):
    def test_默认只列出不执行也不写入(self):
        with mock.patch.object(runner.subprocess, "Popen") as execute, \
             mock.patch.object(runner.tempfile, "mkdtemp") as temporary, \
             mock.patch.object(Path, "mkdir") as mkdir, \
             mock.patch.object(Path, "write_text") as write, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            code = runner.main(["--output-dir", "/不应创建的验收目录"])
        self.assertEqual(code, 0)
        self.assertIn("仅列出，未调用Grok", output.getvalue())
        execute.assert_not_called()
        temporary.assert_not_called()
        mkdir.assert_not_called()
        write.assert_not_called()

    def test_包含八个固定案例(self):
        self.assertEqual(runner.case_names(), [
            "permission:ars-research-architect", "permission:ars-synthesis", "permission:ars-report-compiler",
            "route:research", "route:paper", "route:reviewer", "route:pipeline", "pipeline",
        ])

    def test_自然语言提示词没有预设答案(self):
        for name, (workflow, skill, prompt) in runner.ROUTES.items():
            with self.subTest(route=name):
                command = runner.make_command(f"route:{name}", Path("/tmp/fixture"))
                actual_prompt = command[command.index("-p") + 1]
                self.assertIn(prompt, actual_prompt)
                for forbidden in (skill, "WORKFLOW.md", "SKILL.md", "ROUTE=", "NATIVE_SKILL=", "PASS", "KEY=VALUE"):
                    self.assertNotIn(forbidden, actual_prompt)
                self.assertFalse(prompt.startswith("/"))

    def test_权限案例不使用额外工具过滤伪造隔离(self):
        for agent in runner.AGENTS:
            with self.subTest(agent=agent):
                command = runner.make_command(f"permission:{agent}", Path("/tmp/fixture"))
                self.assertEqual(command[command.index("--agent") + 1], agent)
                for forbidden in ("--tools", "--disallowed-tools", "--disable-web-search", "--no-subagents"):
                    self.assertNotIn(forbidden, command)
                self.assertIn("MCPTool(*)", command)
                self.assertEqual(command[command.index("--permission-mode") + 1], "default")

    def test_成功读取对应技能文件才提供路由证据(self):
        path = "/tmp/skills/ars-academic-paper/SKILL.md"
        trace = 生成轨迹([("read_file", {"target_file": path})], ["read_file"])
        result = runner.assess("route:paper", trace, {}, {}, 0)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["route_file_evidence"], [path])

    def test_成功读取对应工作流也提供路由证据(self):
        path = "/tmp/skills/academic-research-suite/ars/academic-paper/WORKFLOW.md"
        trace = 生成轨迹([("read_file", {"path": path})], ["read_file"])
        result = runner.assess("route:paper", trace, {}, {}, 0)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["route_file_evidence"], [path])

    def test_文字声明读取不能提供路由证据(self):
        trace = 生成轨迹(text="PASS 我已读取 /tmp/ars-academic-paper/SKILL.md")
        result = runner.assess("route:paper", trace, {}, {}, 0)
        self.assertEqual(result["status"], "UNVERIFIED")
        self.assertEqual(result["route_file_evidence"], [])

    def test_失败或缺返回的读取不能提供路由证据(self):
        calls = [("read_file", {"path": "/tmp/ars-academic-paper/SKILL.md"})]
        for options in ({"errors": [0]}, {"omit_results": [0]}):
            with self.subTest(options=options):
                result = runner.assess("route:paper", 生成轨迹(calls, ["read_file"], **options), {}, {}, 0)
                self.assertNotEqual(result["status"], "PASS")
                self.assertEqual(result["route_file_evidence"], [])

    def test_错误工作流读取不能提供目标路由证据(self):
        trace = 生成轨迹([("read_file", {"path": "/tmp/ars-paper-reviewer/SKILL.md"})], ["read_file"])
        result = runner.assess("route:paper", trace, {}, {}, 0)
        self.assertEqual(result["route_file_evidence"], [])
        self.assertNotEqual(result["status"], "PASS")

    def test_空文本回执不能提供读取证据(self):
        trace = 生成轨迹([("read_file", {"path": "/tmp/ars-academic-paper/SKILL.md"})], ["read_file"])
        trace["tool_results"][0]["has_text_content"] = False
        result = runner.assess("route:paper", trace, {}, {}, 0)
        self.assertEqual(result["status"], "UNVERIFIED")
        self.assertEqual(result["route_file_evidence"], [])

    def test_畸形调用与回执不使验收器崩溃(self):
        for field, key in (("tool_calls", "id"), ("tool_results", "tool_use_id")):
            trace = 生成轨迹([("read_file", {"path": "/tmp/ars-academic-paper/SKILL.md"})], ["read_file"])
            del trace[field][0][key]
            trace.update(status="FAIL", normal_termination=False)
            result = runner.assess("route:paper", trace, {}, {}, 0)
            self.assertEqual(result["status"], "UNVERIFIED")
            self.assertEqual(result["route_file_evidence"], [])

    def test_路由意外写文件或非零退出不能通过(self):
        trace = 生成轨迹([("read_file", {"path": "/tmp/ars-academic-paper/SKILL.md"})], ["read_file"])
        for after, exit_code in (({"output.md": "digest"}, 0), ({}, 1)):
            with self.subTest(after=after, exit_code=exit_code):
                self.assertNotEqual(runner.assess("route:paper", trace, {}, after, exit_code)["status"], "PASS")

    def test_流水线缺三次成功调度或文件不能通过(self):
        calls = [("spawn_subagent", {"subagent_type": agent}) for agent in runner.AGENTS]
        files = {"phase1_blueprint/blueprint.md": "a", "phase3_analysis/synthesis.md": "b", "phase4_report/report.md": "c"}
        cases = [
            (生成轨迹(calls[:-1]), files),
            (生成轨迹(calls, errors=[1]), files),
            (生成轨迹(calls), {"phase1_blueprint/blueprint.md": "a"}),
            (生成轨迹(text="三个Agent已成功调度 PASS"), files),
        ]
        for trace, after in cases:
            with self.subTest(after=after, trace_status=trace["status"]):
                result = runner.assess("pipeline", trace, {}, after, 0)
                self.assertEqual(result["status"], "FAIL")

    def test_三次成功调度和文件仍需人工审查(self):
        calls = [("spawn_subagent", {"subagent_type": agent}) for agent in runner.AGENTS]
        files = {"phase1_blueprint/blueprint.md": "a", "phase3_analysis/synthesis.md": "b", "phase4_report/report.md": "c"}
        result = runner.assess("pipeline", 生成轨迹(calls), {}, files, 0)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["successful_dispatches"], list(runner.AGENTS))

    def test_流水线调度顺序错误不能通过(self):
        calls = [("spawn_subagent", {"subagent_type": agent}) for agent in reversed(runner.AGENTS)]
        files = {"phase1_blueprint/blueprint.md": "a", "phase3_analysis/synthesis.md": "b", "phase4_report/report.md": "c"}
        self.assertEqual(runner.assess("pipeline", 生成轨迹(calls), {}, files, 0)["status"], "FAIL")

    def test_权限初始表正确但出现禁用调用仍失败(self):
        trace = 生成轨迹([("run_terminal_command", {"command": "printf ARS_TERMINAL_PROBE"})], runner.ALLOWED_AGENT_TOOLS)
        result = runner.assess("permission:ars-synthesis", trace, {}, {}, 0)
        self.assertEqual(result["permission"]["status"], "FAIL")
        self.assertEqual(result["status"], "FAIL")

    def test_证据流去思考和连接配置但保留工具事件(self):
        tool_call = {"type": "tool_use", "id": "c1", "name": "read_file", "input": {"path": "materials.txt"}}
        tool_result = {"type": "tool_result", "tool_use_id": "c1", "is_error": False, "content": "合成内容"}
        events = [
            {"type": "system", "subtype": "init", "tools": ["read_file"], "mcp_servers": [{"name": "仅测试连接配置"}]},
            {"type": "assistant", "message": {"content": [
                {"type": "thinking", "thinking": "不应保留的思考"},
                {"type": "redacted_thinking", "data": "不应保留的内部签名"},
                {"type": "text", "text": "普通答复"}, tool_call,
            ]}},
            {"type": "user", "message": {"content": [tool_result]}},
        ]
        raw = "\n".join(json.dumps(event, ensure_ascii=False) for event in events)
        cleaned = runner.evidence_text(raw)
        decoded = [json.loads(line) for line in cleaned.splitlines()]
        self.assertNotIn("不应保留", cleaned)
        self.assertNotIn("mcp_servers", decoded[0])
        self.assertEqual(decoded[1]["message"]["content"][-1], tool_call)
        self.assertEqual(decoded[2]["message"]["content"][0], tool_result)
        self.assertEqual(decoded[1]["message"]["content"][0]["text"], "普通答复")


if __name__ == "__main__":
    unittest.main()
