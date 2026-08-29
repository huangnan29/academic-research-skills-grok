"""runtime-core 运行包构建器的契约测试。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from scripts.build_runtime_package import (
    必需工作流,
    _默认输出路径,
    build_runtime_package,
    collect_files,
    directory_summary,
)
from scripts.install_grok_skill import install_skill, validate_package


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
            self.assertFalse(
                any(
                    name.startswith("ars/") and "/tests/" in f"/{name}/"
                    for name in names
                )
            )
            self.assertFalse(
                any(
                    name.startswith("ars/scripts/")
                    and Path(name).name.startswith("test_")
                    and Path(name).suffix == ".py"
                    for name in names
                )
            )
            self.assertFalse(
                any(
                    Path(name).name == "_ci_pytest_manifest.toml"
                    for name in names
                )
            )
            self.assertFalse(any("__pycache__" in name for name in names))
            self.assertFalse(any(name.endswith(".pyc") for name in names))
            self.assertFalse(any(name.endswith("/.DS_Store") for name in names))

            ars_root = 源目录 / "ars"
            excluded_top_level = {
                "CHANGELOG.md",
                "CONTRIBUTING.md",
                "GOVERNANCE.md",
                "POSITIONING.md",
                "QUICKSTART.md",
                "CITATION.cff",
                "package.json",
                "pyproject.toml",
                "requirements-dev.txt",
                "uv.lock",
                ".gitleaks.toml",
                ".gitleaksignore",
                ".command-invariants.toml",
                ".gitattributes",
            }
            excluded_top_level.update(
                path.name
                for path in ars_root.iterdir()
                if path.is_file()
                and path.name.startswith("README")
                and path.suffix == ".md"
            )
            for filename in excluded_top_level:
                self.assertNotIn(f"ars/{filename}", names)

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
            for skill_name in (
                "ars-deep-research",
                "ars-academic-paper",
                "ars-paper-reviewer",
                "ars-academic-pipeline",
            ):
                self.assertIn(f"grok/skills/{skill_name}/SKILL.md", names)
            for agent_name in (
                "ars-research-architect",
                "ars-synthesis",
                "ars-report-compiler",
            ):
                self.assertIn(f"grok/agents/{agent_name}.md", names)
            self.assertIn("grok/hooks/pre_tool_use.py", names)
            self.assertIn("grok/hooks/ars-academic-research-suite.json", names)
            for required in (
                "ars/LICENSE",
                "ars/NOTICE.md",
                "ars/THIRD_PARTY.md",
                "ars/SECURITY.md",
                "ars/requirements-pdf-content-classifier.txt",
            ):
                self.assertIn(required, names)
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
                    and "tests" not in path.relative_to(源目录 / "ars").parts
                    and path.name != "_ci_pytest_manifest.toml"
                    and not (
                        directory_name == "scripts"
                        and path.name.startswith("test_")
                        and path.suffix == ".py"
                    )
                }
                for source_file in source_files:
                    self.assertIn(source_file, names)

            # scripts 中所有非测试运行脚本及其 fixtures 都必须保留。
            scripts_root = 源目录 / "ars" / "scripts"
            for path in scripts_root.rglob("*"):
                if not path.is_file():
                    continue
                relative_to_ars = path.relative_to(源目录 / "ars")
                if (
                    "tests" in relative_to_ars.parts
                    or path.name == "_ci_pytest_manifest.toml"
                    or (
                        path.name.startswith("test_")
                        and path.suffix == ".py"
                    )
                    or path.name == ".DS_Store"
                    or path.suffix == ".pyc"
                    or "__pycache__" in path.parts
                ):
                    continue
                self.assertIn(path.relative_to(源目录).as_posix(), names)

            for script_name in (
                "verify_passport.py",
                "inquiry_branch_ledger.py",
                "research_workflow_profile.py",
            ):
                script_path = scripts_root / script_name
                if script_path.is_file():
                    self.assertIn(script_path.relative_to(源目录).as_posix(), names)

            fixtures_root = scripts_root / "fixtures"
            for path in fixtures_root.rglob("*"):
                if path.is_file():
                    self.assertIn(path.relative_to(源目录).as_posix(), names)

            for required in (
                "ars/hooks/hooks.json",
                "ars/hooks/run_guard.sh",
            ):
                self.assertIn(required, names)
            for directory_name in ("ars/commands", "ars/hooks"):
                source_files = {
                    path.relative_to(源目录).as_posix()
                    for path in (源目录 / directory_name).rglob("*")
                    if path.is_file()
                }
                self.assertTrue(source_files)
                self.assertTrue(source_files.issubset(names))

    def test_包内清单写入轻量变体和最小摘要(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            archive_path = self.构建临时归档(temporary_directory, "runtime.tar.gz")
            _members, contents = 读取归档(archive_path)
            manifest = json.loads(contents["manifest.json"].decode("utf-8"))

            self.assertEqual(
                manifest.get("packaging", {}).get("variant"), "runtime-core"
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
            target = Path(temporary_directory) / "grok"
            install_skill(target_root=target, source_dir=extracted, keep_backups=1)
            self.assertEqual(
                3,
                len(list((target / "agents").glob("ars-*.md"))),
            )
            self.assertFalse(
                (target / "hooks" / "ars-academic-research-suite.json").exists()
            )

    def test_默认输出文件名使用_runtime_core(self) -> None:
        output = _默认输出路径(源目录, "tar.gz")
        self.assertEqual(
            output.name,
            "academic-research-suite-"
            f"{(源目录 / 'VERSION').read_text(encoding='utf-8').strip()}-runtime-core.tar.gz",
        )


if __name__ == "__main__":
    unittest.main()
