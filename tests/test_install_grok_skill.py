"""ARS-Grok Build 安装器的单元测试。"""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.install_grok_skill import (
    EXPECTED_AGENTS,
    EXPECTED_COMMANDS,
    HOOK_CONFIG_NAME,
    SOURCE_DIR,
    ValidationError,
    install_skill,
    main,
    validate_package,
)


class InstallGrokSkillTest(unittest.TestCase):
    """验证检查、安装、备份和失败边界。"""

    def test_备份清理不能删除无所有者标记的目录(self):
        from scripts.install_grok_skill import _new_backup_dir, _prune_backups
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            other = root / "backups" / "other-project"
            other.mkdir(parents=True)
            (other / "data.txt").write_text("必须保留", encoding="utf-8")
            own = _new_backup_dir(root)
            _prune_backups(root, 0)
            self.assertFalse(own.exists())
            self.assertEqual((other / "data.txt").read_text(encoding="utf-8"), "必须保留")

    def test_check_only_does_not_write(self) -> None:
        """--check 应验证源包但不创建目标目录。"""

        with tempfile.TemporaryDirectory() as temporary_directory:
            target_root = Path(temporary_directory) / "grok"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(["--check", "--target-root", str(target_root)])

            self.assertEqual(status, 0)
            self.assertFalse(target_root.exists())
            self.assertIn("检查通过", output.getvalue())

    def test_first_install_copies_skill_and_all_commands(self) -> None:
        """首次安装应复制技能文件和 16 个顶层命令。"""

        with tempfile.TemporaryDirectory() as temporary_directory:
            target_root = Path(temporary_directory) / "grok"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(["--target-root", str(target_root)])

            self.assertEqual(status, 0)
            installed_skill = target_root / "skills" / "academic-research-suite"
            self.assertTrue((installed_skill / "VERSION").is_file())
            self.assertTrue((installed_skill / "manifest.json").is_file())
            self.assertTrue((installed_skill / "SKILL.md").is_file())
            self.assertTrue((installed_skill / "ars").is_dir())
            self.assertTrue(
                (installed_skill / "ars" / "deep-research" / "WORKFLOW.md").is_file()
            )
            self.assertEqual(
                sorted(path.name for path in (target_root / "commands").glob("*.md")),
                sorted(EXPECTED_COMMANDS),
            )
            self.assertEqual(
                sorted(path.name for path in (target_root / "agents").glob("*.md")),
                sorted(EXPECTED_AGENTS),
            )
            self.assertFalse((target_root / "hooks" / HOOK_CONFIG_NAME).exists())
            self.assertIn("安装成功", output.getvalue())

    def test_enable_hooks_renders_local_paths_and_no_http(self) -> None:
        """--enable-hooks 应渲染本地脚本路径，并禁止网络 Hook。"""

        with tempfile.TemporaryDirectory() as temporary_directory:
            target_root = Path(temporary_directory) / "grok with spaces"
            self.assertEqual(
                main(["--target-root", str(target_root), "--enable-hooks"]),
                0,
            )
            hook_path = target_root / "hooks" / HOOK_CONFIG_NAME
            self.assertTrue(hook_path.is_file())
            hook_text = hook_path.read_text(encoding="utf-8")
            self.assertNotIn("__ARS_", hook_text)
            self.assertNotIn("http://", hook_text.lower())
            self.assertNotIn("https://", hook_text.lower())
            hook = json.loads(hook_text)
            self.assertEqual(set(hook["hooks"]), {"PreToolUse"})
            self.assertNotIn("SessionStart", hook["hooks"])
            self.assertEqual(
                hook["hooks"]["PreToolUse"][0]["matcher"],
                "^(search_replace|run_terminal_command|run_terminal_cmd)$",
            )
            pre_tool_command = hook["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
            self.assertIn("pre_tool_use.py", pre_tool_command)
            self.assertIn("grok with spaces", pre_tool_command)
            self.assertEqual(
                hook["hooks"]["PreToolUse"][0]["hooks"][0]["type"],
                "command",
            )

    def test_enable_hooks_is_idempotent(self) -> None:
        """相同安装再次显式启用 Hook 不得创建备份。"""

        with tempfile.TemporaryDirectory() as temporary_directory:
            target_root = Path(temporary_directory) / "grok"
            self.assertEqual(main(["--target-root", str(target_root), "--enable-hooks"]), 0)
            self.assertEqual(main(["--target-root", str(target_root), "--enable-hooks"]), 0)
            self.assertFalse((target_root / "backups").exists())

    def test_enable_hooks_backs_up_existing_managed_file(self) -> None:
        """替换同名托管 Hook 前应先保存旧配置。"""

        with tempfile.TemporaryDirectory() as temporary_directory:
            target_root = Path(temporary_directory) / "grok"
            self.assertEqual(main(["--target-root", str(target_root)]), 0)
            hook_path = target_root / "hooks" / HOOK_CONFIG_NAME
            hook_path.parent.mkdir(parents=True, exist_ok=True)
            old_hook = '{"custom":true}\n'
            hook_path.write_text(old_hook, encoding="utf-8")
            self.assertEqual(
                main(["--target-root", str(target_root), "--enable-hooks"]),
                0,
            )
            backups = sorted(
                path for path in (target_root / "backups").iterdir() if path.is_dir()
            )
            self.assertEqual(len(backups), 1)
            self.assertEqual(
                (
                    backups[0] / "hooks" / HOOK_CONFIG_NAME
                ).read_text(encoding="utf-8"),
                old_hook,
            )

    def test_disable_hooks_only_removes_managed_file(self) -> None:
        """--disable-hooks 只移除 ARS 托管文件，其他 Hook 和技能保持不变。"""

        with tempfile.TemporaryDirectory() as temporary_directory:
            target_root = Path(temporary_directory) / "grok"
            self.assertEqual(main(["--target-root", str(target_root), "--enable-hooks"]), 0)
            other_hook = target_root / "hooks" / "other.json"
            other_hook.write_text('{"keep":true}\n', encoding="utf-8")
            skill_version = target_root / "skills" / "academic-research-suite" / "VERSION"
            before = skill_version.read_text(encoding="utf-8")
            self.assertEqual(main(["--target-root", str(target_root), "--disable-hooks"]), 0)
            self.assertFalse((target_root / "hooks" / HOOK_CONFIG_NAME).exists())
            self.assertEqual(other_hook.read_text(encoding="utf-8"), '{"keep":true}\n')
            self.assertEqual(skill_version.read_text(encoding="utf-8"), before)

    def test_enable_and_disable_flags_are_mutually_exclusive(self) -> None:
        """启用和禁用参数不得同时接受。"""

        with tempfile.TemporaryDirectory() as temporary_directory:
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    main(
                        [
                            "--target-root",
                            str(Path(temporary_directory) / "grok"),
                            "--enable-hooks",
                            "--disable-hooks",
                        ]
                    )

    def test_second_install_creates_timestamped_backup(self) -> None:
        """二次安装应先备份旧技能和命令，再替换为新内容。"""

        with tempfile.TemporaryDirectory() as temporary_directory:
            target_root = Path(temporary_directory) / "grok"
            self.assertEqual(main(["--target-root", str(target_root)]), 0)

            old_version = "旧版本测试内容\n"
            installed_version = target_root / "skills" / "academic-research-suite" / "VERSION"
            installed_version.write_text(old_version, encoding="utf-8")
            old_command = target_root / "commands" / EXPECTED_COMMANDS[0]
            old_command.write_text("旧命令测试内容\n", encoding="utf-8")

            self.assertEqual(main(["--target-root", str(target_root)]), 0)

            backup_dirs = sorted(path for path in (target_root / "backups").iterdir() if path.is_dir())
            self.assertEqual(len(backup_dirs), 1)
            backup_skill_version = (
                backup_dirs[0] / "skills" / "academic-research-suite" / "VERSION"
            )
            backup_command = backup_dirs[0] / "commands" / EXPECTED_COMMANDS[0]
            self.assertEqual(backup_skill_version.read_text(encoding="utf-8"), old_version)
            self.assertEqual(backup_command.read_text(encoding="utf-8"), "旧命令测试内容\n")
            self.assertNotEqual(installed_version.read_text(encoding="utf-8"), old_version)

    def test_identical_install_is_noop_without_backup(self) -> None:
        """源包与已安装内容相同时应成功返回且不创建备份。"""

        with tempfile.TemporaryDirectory() as temporary_directory:
            target_root = Path(temporary_directory) / "grok"
            self.assertEqual(main(["--target-root", str(target_root)]), 0)
            installed_version = (
                target_root / "skills" / "academic-research-suite" / "VERSION"
            )
            original_mtime = installed_version.stat().st_mtime_ns

            self.assertEqual(main(["--target-root", str(target_root)]), 0)

            self.assertFalse((target_root / "backups").exists())
            self.assertEqual(installed_version.stat().st_mtime_ns, original_mtime)

    def test_corrupted_vendored_tree_hash_fails_before_install(self) -> None:
        """上游目录摘要损坏时应在写入目标前拒绝安装。"""

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_directory_path = Path(temporary_directory)
            source_copy = temporary_directory_path / "source"
            target_root = temporary_directory_path / "grok"
            shutil.copytree(SOURCE_DIR, source_copy)

            manifest_path = source_copy / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["source_overlay"]["vendored_tree_sha256"] = "0" * 64
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            errors = validate_package(source_copy)
            self.assertTrue(any("vendored_tree_sha256" in error for error in errors))
            with self.assertRaises(ValidationError):
                install_skill(target_root=target_root, source_dir=source_copy)
            self.assertFalse(target_root.exists())

    def test_version_mismatch_fails_before_install(self) -> None:
        """VERSION 与 manifest adapter_version 不一致时应拒绝安装。"""

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_directory_path = Path(temporary_directory)
            source_copy = temporary_directory_path / "source"
            target_root = temporary_directory_path / "grok"
            shutil.copytree(SOURCE_DIR, source_copy)

            manifest_path = source_copy / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["adapter_version"] = "999.0.0"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            errors = validate_package(source_copy)
            self.assertTrue(any("adapter_version" in error for error in errors))
            with self.assertRaises(ValidationError):
                install_skill(target_root=target_root, source_dir=source_copy)
            self.assertFalse(target_root.exists())

    def test_keep_backups_retains_only_latest_count(self) -> None:
        """安装成功后应按参数只保留最新数量的备份。"""

        with tempfile.TemporaryDirectory() as temporary_directory:
            target_root = Path(temporary_directory) / "grok"
            self.assertEqual(main(["--target-root", str(target_root)]), 0)
            installed_version = (
                target_root / "skills" / "academic-research-suite" / "VERSION"
            )

            for index in range(5):
                old_version = f"旧版本-{index}\n"
                installed_version.write_text(old_version, encoding="utf-8")
                self.assertEqual(
                    main(
                        [
                            "--target-root",
                            str(target_root),
                            "--keep-backups",
                            "2",
                        ]
                    ),
                    0,
                )

            backup_dirs = sorted(
                path
                for path in (target_root / "backups").iterdir()
                if path.is_dir()
            )
            self.assertEqual(len(backup_dirs), 2)
            retained_versions = [
                (
                    backup_dir
                    / "skills"
                    / "academic-research-suite"
                    / "VERSION"
                ).read_text(encoding="utf-8")
                for backup_dir in backup_dirs
            ]
            self.assertEqual(retained_versions, ["旧版本-3\n", "旧版本-4\n"])

    def test_missing_key_file_fails_before_install(self) -> None:
        """缺少关键文件时应失败且不写入目标。"""

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_directory_path = Path(temporary_directory)
            source_copy = temporary_directory_path / "source"
            target_root = temporary_directory_path / "grok"
            shutil.copytree(SOURCE_DIR, source_copy)
            (source_copy / "SKILL.md").unlink()

            errors = validate_package(source_copy)
            self.assertTrue(any("SKILL.md" in error for error in errors))
            with self.assertRaises(ValidationError):
                install_skill(target_root=target_root, source_dir=source_copy)
            self.assertFalse(target_root.exists())


if __name__ == "__main__":
    unittest.main()
