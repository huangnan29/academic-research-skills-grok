"""ARS-Grok Build 安装器的单元测试。"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.install_grok_skill import (
    EXPECTED_COMMANDS,
    SOURCE_DIR,
    ValidationError,
    install_skill,
    main,
    validate_package,
)


class InstallGrokSkillTest(unittest.TestCase):
    """验证检查、安装、备份和失败边界。"""

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
            self.assertIn("安装成功", output.getvalue())

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
