"""runtime-minimal 运行包构建器的契约测试。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from scripts.build_runtime_package import (
    必需工作流,
    build_runtime_package,
    collect_files,
    directory_summary,
)
from scripts.install_grok_skill import validate_package


仓库根目录 = Path(__file__).resolve().parents[1]
源目录 = 仓库根目录 / "skills" / "academic-research-suite"


def 读取归档(archive_path: Path) -> tuple[list[tarfile.TarInfo], dict[str, bytes]]:
    """读取归档成员及其文件内容。"""

    with tarfile.open(archive_path, mode="r:gz") as archive:
        members = archive.getmembers()
        contents: dict[str, bytes] = {}
        for member in members:
            if member.isfile():
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise AssertionError(f"无法读取归档文件：{member.name}")
                contents[member.name] = extracted.read()
    return members, contents


class RuntimePackageTest(unittest.TestCase):
    """覆盖排除项、入口文件、清单摘要和确定性构建。"""

    def 构建临时归档(self, temporary_directory: str, name: str) -> Path:
        return build_runtime_package(
            source_dir=源目录,
            output_path=Path(temporary_directory) / name,
        )

    def test_排除开发评测目录和临时文件(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            archive_path = self.构建临时归档(temporary_directory, "runtime.tar.gz")
            _members, contents = 读取归档(archive_path)
            names = set(contents)

            for excluded_prefix in (
                "ars/tests/",
                "ars/evals/",
                "ars/audits/",
                "ars/docs/design/",
                "ars/docs/migration/",
                "ars/.github/",
                "ars/tools/",
                "ars/pi/",
            ):
                self.assertFalse(
                    any(name.startswith(excluded_prefix) for name in names),
                    excluded_prefix,
                )
            self.assertFalse(any("__pycache__" in name for name in names))
            self.assertFalse(any(name.endswith(".pyc") for name in names))
            self.assertFalse(any(name.endswith("/.DS_Store") for name in names))

    def test_保留工作流和运行所需目录(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            archive_path = self.构建临时归档(temporary_directory, "runtime.tar.gz")
            _members, contents = 读取归档(archive_path)
            names = set(contents)

            for required in ("SKILL.md", "VERSION", "manifest.json", "LICENSE"):
                self.assertIn(required, names)
            for required in 必需工作流:
                self.assertIn(required, names)
            self.assertIn("grok/runtime-mapping.md", names)
            self.assertIn("grok/full-runtime-manifest.json", names)
            command_names = {
                name for name in names if name.startswith("grok/commands/")
            }
            source_command_names = {
                path.relative_to(源目录).as_posix()
                for path in (源目录 / "grok" / "commands").glob("*.md")
            }
            self.assertEqual(command_names, source_command_names)

            # 运行时资料目录必须完整保留，排除规则只作用于明确列出的路径。
            for directory_name in ("agents", "references", "templates", "shared", "scripts"):
                source_files = {
                    path.relative_to(源目录).as_posix()
                    for path in (源目录 / "ars").rglob(f"{directory_name}/**/*")
                    if path.is_file()
                    and "__pycache__" not in path.parts
                    and path.suffix != ".pyc"
                    and path.name != ".DS_Store"
                    and not any(
                        part in {
                            "tests",
                            "evals",
                            "audits",
                            "tools",
                            "pi",
                            ".github",
                        }
                        for part in path.relative_to(源目录 / "ars").parts[:2]
                    )
                }
                for source_file in source_files:
                    self.assertIn(source_file, names)

    def test_包内清单写入轻量变体和最小摘要(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            archive_path = self.构建临时归档(temporary_directory, "runtime.tar.gz")
            _members, contents = 读取归档(archive_path)
            manifest = json.loads(contents["manifest.json"].decode("utf-8"))

            self.assertEqual(
                manifest.get("packaging", {}).get("variant"), "runtime-minimal"
            )
            ars_files = [
                (Path(name).relative_to("ars"), content)
                for name, content in contents.items()
                if name.startswith("ars/")
            ]
            expected_count, expected_hash = directory_summary(
                (Path(relative.as_posix()), content)
                for relative, content in ars_files
            )
            source_overlay = manifest["source_overlay"]
            self.assertEqual(source_overlay["vendored_file_count"], expected_count)
            self.assertEqual(source_overlay["vendored_tree_sha256"], expected_hash)

    def test_两次构建归档字节完全一致(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            first = self.构建临时归档(temporary_directory, "first.tar.gz")
            second = self.构建临时归档(temporary_directory, "second.tar.gz")
            first_hash = hashlib.sha256(first.read_bytes()).hexdigest()
            second_hash = hashlib.sha256(second.read_bytes()).hexdigest()
            self.assertEqual(first_hash, second_hash)

            members, _contents = 读取归档(first)
            names = [member.name for member in members]
            self.assertEqual(names, sorted(names))
            for member in members:
                self.assertEqual(member.uid, 0)
                self.assertEqual(member.gid, 0)
                self.assertEqual(member.mtime, 0)

    def test_源目录摘要函数与收集结果可复算(self) -> None:
        files = collect_files(源目录)
        ars_files = [
            (relative.relative_to("ars"), path.read_bytes())
            for relative, path in files
            if relative.parts and relative.parts[0] == "ars"
        ]
        count, digest = directory_summary(ars_files)
        self.assertGreater(count, 0)
        self.assertEqual(len(digest), 64)

    def test_解压目录可被正式安装器验证(self) -> None:
        """轻量包清单摘要必须与正式安装器使用同一排序算法。"""

        with tempfile.TemporaryDirectory() as temporary_directory:
            archive_path = self.构建临时归档(temporary_directory, "runtime.tar.gz")
            extracted = Path(temporary_directory) / "extracted"
            extracted.mkdir()
            with tarfile.open(archive_path, mode="r:gz") as archive:
                archive.extractall(extracted, filter="data")
            self.assertEqual([], validate_package(extracted))


if __name__ == "__main__":
    unittest.main()
