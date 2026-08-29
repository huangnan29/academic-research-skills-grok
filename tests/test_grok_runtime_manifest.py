import json
import unittest
from pathlib import Path


class GrokRuntimeManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        项目根目录 = Path(__file__).resolve().parents[1]
        清单路径 = (
            项目根目录
            / "skills"
            / "academic-research-suite"
            / "grok"
            / "full-runtime-manifest.json"
        )
        with 清单路径.open("r", encoding="utf-8") as 文件:
            cls.清单 = json.load(文件)

    def test_json结构完整(self):
        self.assertEqual(self.清单["schema_version"], "1.0")
        self.assertIn("adapter", self.清单)
        self.assertIn("runtime_constraints", self.清单)
        self.assertIn("modes", self.清单)
        self.assertIn("tool_mapping", self.清单)
        self.assertIn("confirmation_gates", self.清单)

    def test完整运行时默认禁用且内联默认启用(self):
        self.assertFalse(self.清单["adapter"]["default_enabled"])
        self.assertEqual(self.清单["runtime_constraints"]["default_mode"], "inline")
        self.assertTrue(self.清单["modes"]["inline"]["enabled_by_default"])
        self.assertFalse(self.清单["modes"]["parallel"]["enabled_by_default"])
        self.assertFalse(self.清单["runtime_constraints"]["automatic_parallel_dispatch"])

    def test运行模式和子agent深度(self):
        self.assertEqual(set(self.清单["modes"]), {"inline", "native-phase", "parallel"})
        self.assertEqual(self.清单["runtime_constraints"]["max_subagent_depth"], 1)
        self.assertEqual(self.清单["subagent_policy"]["max_depth"], 1)
        self.assertEqual(self.清单["modes"]["parallel"]["max_subagent_depth"], 1)
        self.assertTrue(self.清单["runtime_constraints"]["parent_only_spawning"])
        self.assertTrue(self.清单["subagent_policy"]["parent_only_spawning"])

    def test_原生阶段Agent仅用于完整流水线且不并行(self):
        模式 = self.清单["modes"]["native-phase"]
        self.assertEqual(
            模式["enabled_by_default_for"],
            ["ars-full", "ars-academic-pipeline"],
        )
        self.assertFalse(模式["parallel"])
        self.assertEqual(模式["max_subagent_depth"], 1)
        self.assertEqual(
            set(模式["allowed_agent_types"]),
            {
                "ars-research-architect",
                "ars-synthesis",
                "ars-report-compiler",
            },
        )

    def test关键工具映射(self):
        期望映射 = {
            "Read": "read_file",
            "Write": "search_replace",
            "Edit": "search_replace",
            "MultiEdit": "search_replace",
            "Glob": "list_dir",
            "ListDir": "list_dir",
            "Grep": "grep",
            "WebSearch": "web_search",
            "Bash": "run_terminal_command",
            "Agent": "spawn_subagent",
            "Task": "spawn_subagent",
        }
        for 上游工具, Grok工具 in 期望映射.items():
            with self.subTest(上游工具=上游工具):
                self.assertEqual(
                    self.清单["tool_mapping"][上游工具]["grok_tool"],
                    Grok工具,
                )

    def test确认门是显式且默认安全(self):
        确认门 = self.清单["confirmation_gates"]
        必需确认门 = {
            "enable_full_runtime",
            "parallel_subagents",
            "external_network_or_api",
            "cross_model_or_content_upload",
            "write_or_revision",
            "terminal_or_experiment",
            "hook_install_or_enable",
            "destructive_or_irreversible",
        }
        self.assertTrue(必需确认门.issubset(确认门))
        for 门名称 in 必需确认门:
            with self.subTest(门名称=门名称):
                self.assertTrue(确认门[门名称]["required"])
                self.assertIn("trigger", 确认门[门名称])
                self.assertIn("default_without_confirmation", 确认门[门名称])
                self.assertNotEqual(
                    确认门[门名称]["default_without_confirmation"],
                    "allow",
                )

    def test_hook安全边界(self):
        Hook = self.清单["hook_mapping"]
        self.assertTrue(Hook["project_trust_required"])
        self.assertTrue(Hook["global_hooks_always_trusted"])
        self.assertIn("PreToolUse", Hook["blocking_events"])
        self.assertIn("Stop", Hook["blocking_events"])
        self.assertIn("SubagentStop", Hook["blocking_events"])
        self.assertIn("fail-open", Hook["failure_behavior"])
        self.assertIn("integrity_gate_policy", Hook)


if __name__ == "__main__":
    unittest.main()
