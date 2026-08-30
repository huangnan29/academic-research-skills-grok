"""验证 Grok 轨迹解析器不把模型自述误认成工具和权限证据。"""

import json
import unittest

from scripts.grok_trace_evidence import parse_trace, permission_evidence


def 轨迹(*events):
    return "\n".join(json.dumps(event) for event in events)


def 初始(tools=None):
    return {"type": "system", "subtype": "init", "tools": [] if tools is None else tools, "skills": ["ars-academic-paper"]}


def 结束(**kwargs):
    return {"type": "result", "subtype": "success", "is_error": False, "stop_reason": "end_turn", **kwargs}


def 消息(role, blocks, parent=None):
    return {"type": role, "message": {"content": blocks}, "parent_tool_use_id": parent}


class 轨迹证据测试(unittest.TestCase):
    def test_合法最小案例(self):
        report = parse_trace(轨迹(初始(), 结束()))
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(permission_evidence(report, [])["tool_surface_match"])

    def test_纯PASS文本不能通过(self):
        self.assertEqual(parse_trace("PASS")["status"], "FAIL")
        report = parse_trace(轨迹(结束(result="PASS 全部权限通过")))
        self.assertFalse(permission_evidence(report, [])["tool_surface_match"])

    def test_文本工具自述不计入调用(self):
        report = parse_trace(轨迹(初始(), 消息("assistant", [{"type": "text", "text": "已执行 read_file，权限检查PASS"}]), 结束(result="执行成功")))
        self.assertEqual(report["tool_calls"], [])
        self.assertEqual(permission_evidence(report, [])["observed_tools"], [])

    def test_禁用工具实际出现(self):
        report = parse_trace(轨迹(初始(["read_file"]), 消息("assistant", [{"type": "tool_use", "id": "c1", "name": "run_terminal_command", "input": {"command": "true"}}]), 结束()))
        evidence = permission_evidence(report, ["read_file"])
        self.assertEqual(evidence["status"], "FAIL")
        self.assertEqual(evidence["forbidden_observed_tools"], ["run_terminal_command"])

    def test_额外工具表不通过(self):
        evidence = permission_evidence(parse_trace(轨迹(初始(["read_file", "web_search"]), 结束())), ["read_file"])
        self.assertEqual(evidence["extra_tools"], ["web_search"])
        self.assertFalse(evidence["tool_surface_match"])

    def test_缺少init不能通过(self):
        report = parse_trace(轨迹(结束()))
        self.assertFalse(report["valid_init"])
        self.assertEqual(report["status"], "FAIL")

    def test_缺tools不能当空集合(self):
        report = parse_trace(轨迹({"type": "system", "subtype": "init"}, 结束()))
        evidence = permission_evidence(report, [])
        self.assertFalse(evidence["tool_surface_available"])
        self.assertFalse(evidence["tool_surface_match"])

    def test_错误工具返回不通过(self):
        report = parse_trace(轨迹(初始(), 消息("user", [{"type": "tool_result", "tool_use_id": "c1", "content": "拒绝访问", "is_error": True}]), 结束()))
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(report["tool_results"][0]["is_error"])

    def test_终止后事件不通过(self):
        report = parse_trace(轨迹(初始(), 结束(), {"type": "custom"}))
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["ended_with_result"])

    def test_重复终止不通过(self):
        self.assertEqual(parse_trace(轨迹(初始(), 结束(), 结束()))["status"], "FAIL")

    def test_缺少终止不通过(self):
        self.assertEqual(parse_trace(轨迹(初始()))["status"], "FAIL")

    def test_损坏JSON不能被正常尾事件覆盖(self):
        self.assertEqual(parse_trace(轨迹(初始()) + "\n{损坏\n" + 轨迹(结束()))["status"], "FAIL")

    def test_未知事件只记录(self):
        report = parse_trace(轨迹(初始(), {"type": "heartbeat", "result": "PASS"}, 结束()))
        self.assertEqual(report["unknown_events"][0]["type"], "heartbeat")
        self.assertEqual(report["tool_calls"], [])

    def test_保留调用输入结果内容和父调用(self):
        report = parse_trace(轨迹(初始([{"name": "read_file"}]), 消息("assistant", [{"type": "server_tool_use", "id": "c1", "name": "read_file", "input": {"path": "input.md"}}], "parent1"), 消息("user", [{"type": "tool_result", "tool_use_id": "c1", "is_error": False, "content": [{"type": "text", "text": "原始内容"}]}], "parent1"), 结束()))
        self.assertEqual(report["tool_calls"][0]["input"], {"path": "input.md"})
        self.assertEqual(report["tool_calls"][0]["parent_tool_use_id"], "parent1")
        self.assertEqual(report["tool_results"][0]["content"][0]["text"], "原始内容")
        self.assertEqual(report["skills"], ["ars-academic-paper"])

    def test_异常停止和错误终止不通过(self):
        for result in (结束(stop_reason="max_tokens"), 结束(is_error=True), 结束(subtype="error_max_turns")):
            with self.subTest(result=result):
                self.assertEqual(parse_trace(轨迹(初始(), result))["status"], "FAIL")

    def test_重复init不能通过(self):
        self.assertEqual(parse_trace(轨迹(初始(), 初始(), 结束()))["status"], "FAIL")

    def test_格式错误工具列表不能通过(self):
        for tools in ("read_file", [{}], ["read_file", "read_file"]):
            with self.subTest(tools=tools):
                self.assertFalse(permission_evidence(parse_trace(轨迹(初始(tools), 结束())), [])["tool_surface_match"])

    def test_缺少明确is_error不能通过(self):
        report = parse_trace(轨迹(初始(), {"type": "result", "result": "PASS"}))
        self.assertEqual(report["status"], "FAIL")

    def test_MCP元工具必须算额外权限(self):
        allowed = ["read_file", "search_replace", "list_dir", "grep"]
        report = parse_trace(轨迹(初始(allowed + ["search_tool", "use_tool"]), 结束()))
        evidence = permission_evidence(report, allowed)
        self.assertFalse(evidence["tool_surface_match"])
        self.assertEqual(evidence["extra_tools"], ["search_tool", "use_tool"])

    def test_缺少允许工具不视为精确匹配(self):
        evidence = permission_evidence(parse_trace(轨迹(初始(), 结束())), ["read_file"])
        self.assertEqual(evidence["missing_tools"], ["read_file"])
        self.assertFalse(evidence["tool_surface_match"])

    def test_重复调用ID不通过(self):
        call = {"type": "tool_use", "id": "c1", "name": "read_file", "input": {}}
        report = parse_trace(轨迹(初始(), 消息("assistant", [call, call]), 结束()))
        self.assertEqual(report["status"], "FAIL")

    def test_非有限数字不是合法JSON(self):
        report = parse_trace(轨迹(初始()) + '\n{"type":"custom","value":NaN}\n' + 轨迹(结束()))
        self.assertEqual(report["status"], "FAIL")

    def test_缺少stop_reason不能正常完成(self):
        terminal = 结束()
        del terminal["stop_reason"]
        report = parse_trace(轨迹(初始(), terminal))
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["normal_termination"])

    def test_客户端调用缺少结果不能正常完成(self):
        call = {"type": "tool_use", "id": "c1", "name": "read_file", "input": {}}
        report = parse_trace(轨迹(初始(["read_file"]), 消息("assistant", [call]), 结束()))
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["unpaired_tool_calls"], [{"id": "c1", "parent_tool_use_id": None}])

    def test_孤立工具结果拒绝(self):
        result = {"type": "tool_result", "tool_use_id": "c1", "content": "完成", "is_error": False}
        report = parse_trace(轨迹(初始(), 消息("user", [result]), 结束()))
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("孤立 tool_result" in error for error in report["errors"]))

    def test_重复工具结果拒绝(self):
        call = {"type": "tool_use", "id": "c1", "name": "read_file", "input": {}}
        result = {"type": "tool_result", "tool_use_id": "c1", "content": "完成", "is_error": False}
        report = parse_trace(轨迹(初始(), 消息("assistant", [call]), 消息("user", [result, result]), 结束()))
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("重复 tool_result" in error for error in report["errors"]))

    def test_不同父上下文不能配对(self):
        call = {"type": "tool_use", "id": "c1", "name": "read_file", "input": {}}
        result = {"type": "tool_result", "tool_use_id": "c1", "content": "完成"}
        report = parse_trace(轨迹(初始(), 消息("assistant", [call], "parent1"), 消息("user", [result], "parent2"), 结束()))
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["unpaired_tool_calls"][0]["parent_tool_use_id"], "parent1")

    def test_合法客户端配对通过(self):
        call = {"type": "tool_use", "id": "c1", "name": "read_file", "input": {}}
        result = {"type": "tool_result", "tool_use_id": "c1", "content": "完成", "is_error": False}
        report = parse_trace(轨迹(初始(["read_file"]), 消息("assistant", [call], "parent1"), 消息("user", [result], "parent1"), 结束()))
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["unpaired_tool_calls"], [])

    def test_服务端调用专属结果未配对则未验证(self):
        call = {"type": "server_tool_use", "id": "s1", "name": "web_search", "input": {}}
        report = parse_trace(轨迹(初始(["web_search"]), 消息("assistant", [call]), 结束()))
        self.assertEqual(report["status"], "UNVERIFIED")
        self.assertFalse(report["normal_termination"])
        self.assertFalse(permission_evidence(report, ["web_search"])["tool_surface_match"])

    def test_缺少工具返回content不能通过(self):
        call = {"type": "tool_use", "id": "c1", "name": "read_file", "input": {}}
        result = {"type": "tool_result", "tool_use_id": "c1", "is_error": False}
        report = parse_trace(轨迹(初始(), 消息("assistant", [call]), 消息("user", [result]), 结束()))
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["tool_results"][0]["content_valid"])

    def test_null工具返回content不能通过(self):
        call = {"type": "tool_use", "id": "c1", "name": "read_file", "input": {}}
        result = {"type": "tool_result", "tool_use_id": "c1", "content": None, "is_error": False}
        report = parse_trace(轨迹(初始(), 消息("assistant", [call]), 消息("user", [result]), 结束()))
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["tool_results"][0]["has_text_content"])

    def test_空字符串合法但不能证明实际文本读取(self):
        call = {"type": "tool_use", "id": "c1", "name": "read_file", "input": {}}
        for content in ("", "  ", [], [{"type": "text", "text": ""}]):
            with self.subTest(content=content):
                result = {"type": "tool_result", "tool_use_id": "c1", "content": content}
                report = parse_trace(轨迹(初始(), 消息("assistant", [call]), 消息("user", [result]), 结束()))
                self.assertEqual(report["status"], "PASS")
                self.assertTrue(report["tool_results"][0]["content_valid"])
                self.assertFalse(report["tool_results"][0]["has_text_content"])

    def test_内容块缺字段或错误类型不通过(self):
        call = {"type": "tool_use", "id": "c1", "name": "read_file", "input": {}}
        for content in (42, {}, [{}], ["text"], [{"type": "text"}], [{"type": "text", "text": None}], [{"type": "image"}]):
            with self.subTest(content=content):
                result = {"type": "tool_result", "tool_use_id": "c1", "content": content}
                report = parse_trace(轨迹(初始(), 消息("assistant", [call]), 消息("user", [result]), 结束()))
                self.assertEqual(report["status"], "FAIL")

    def test_完整文本内容块可作为文本读取证据(self):
        call = {"type": "tool_use", "id": "c1", "name": "read_file", "input": {}}
        result = {"type": "tool_result", "tool_use_id": "c1", "content": [{"type": "text", "text": "真实返回文本"}]}
        report = parse_trace(轨迹(初始(), 消息("assistant", [call]), 消息("user", [result]), 结束()))
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["tool_results"][0]["has_text_content"])


if __name__ == "__main__":
    unittest.main()
