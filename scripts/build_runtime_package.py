#!/usr/bin/env python3
"""确定性构建 ARS-Grok Build 的 runtime-core 运行包。

默认生成 ``dist/academic-research-suite-<VERSION>-runtime-core.tar.gz``。
脚本只使用 Python 标准库，包内的 ``manifest.json`` 会记录轻量 ``ars/``
目录的新文件数和目录摘要。
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tarfile
import tempfile
from typing import Iterable, Mapping


技能名称 = "academic-research-suite"
仓库根目录 = Path(__file__).resolve().parents[1]
默认源目录 = 仓库根目录 / "skills" / 技能名称

# 这些路径属于完整开发/评测材料，不应进入轻量运行包。
排除的_ars_子目录 = {
    "tests",
    "evals",
    "audits",
    ".github",
    "tools",
    "pi",
}
排除的_ars_docs_子目录 = {"design", "migration"}
排除的_ars_顶层文件 = {
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

必需工作流 = (
    "ars/deep-research/WORKFLOW.md",
    "ars/academic-paper/WORKFLOW.md",
    "ars/academic-paper-reviewer/WORKFLOW.md",
    "ars/academic-pipeline/WORKFLOW.md",
    "ars/experiment-agent/WORKFLOW.md",
)
必需根文件 = ("SKILL.md", "VERSION", "manifest.json", "LICENSE")


def 是否排除(relative_path: PurePosixPath) -> bool:
    """判断相对路径是否属于运行包排除项。"""

    parts = relative_path.parts
    if any(part == "__pycache__" for part in parts):
        return True
    if relative_path.name == ".DS_Store" or relative_path.suffix == ".pyc":
        return True

    if len(parts) >= 2 and parts[0] == "ars":
        if parts[1] in 排除的_ars_子目录:
            return True
        # 运行目录不携带任何层级的测试目录及测试清单。
        if "tests" in parts[1:] or relative_path.name == "_ci_pytest_manifest.toml":
            return True
        # ars/scripts 中的 test_*.py 是开发测试，不属于运行时脚本。
        if (
            parts[1] == "scripts"
            and relative_path.name.startswith("test_")
            and relative_path.suffix == ".py"
        ):
            return True
        if (
            len(parts) >= 3
            and parts[1] == "docs"
            and parts[2] in 排除的_ars_docs_子目录
        ):
            return True
        # 仅删除 ars 根目录的项目开发文档和构建元数据，保留运行时资料目录中的同名文件。
        if len(parts) == 2 and (
            relative_path.name in 排除的_ars_顶层文件
            or (
                relative_path.name.startswith("README")
                and relative_path.suffix == ".md"
            )
        ):
            return True
    return False


def 收集文件(source_dir: Path) -> list[tuple[PurePosixPath, Path]]:
    """收集包内文件，并按 POSIX 相对路径排序。"""

    if not source_dir.is_dir():
        raise FileNotFoundError(f"源技能目录不存在：{source_dir}")

    files: list[tuple[PurePosixPath, Path]] = []
    for path in source_dir.rglob("*"):
        relative = PurePosixPath(path.relative_to(source_dir).as_posix())
        if path.is_file() and not path.is_symlink() and not 是否排除(relative):
            files.append((relative, path))
    files.sort(key=lambda item: item[0].as_posix())
    return files


def 计算目录摘要(
    ars_files: Iterable[tuple[PurePosixPath, bytes]],
) -> tuple[int, str]:
    """按相对路径、NUL、文件 SHA-256 digest 和换行计算目录摘要。

    该算法与安装器及完整源包验证器保持一致。传入的路径应当是相对于
    ``ars/`` 的路径，而不是带有 ``ars/`` 前缀的路径。
    """

    total_digest = hashlib.sha256()
    # 必须使用 Path 的组件顺序，与安装器和完整包验证器完全一致。
    # 直接按含斜杠的整串排序会在目录名和连字符相邻时产生不同次序。
    ordered_files = sorted(ars_files, key=lambda item: item[0])
    for relative_path, content in ordered_files:
        file_digest = hashlib.sha256(content).digest()
        total_digest.update(relative_path.as_posix().encode("utf-8"))
        total_digest.update(b"\0")
        total_digest.update(file_digest)
        total_digest.update(b"\n")
    return len(ordered_files), total_digest.hexdigest()


def _读取源元数据(
    source_dir: Path,
    files: list[tuple[PurePosixPath, Path]],
) -> tuple[str, dict[str, object]]:
    """读取版本和源清单，并确认轻量包不能缺少关键入口。"""

    for relative_path in 必需根文件:
        if not (source_dir / relative_path).is_file():
            raise ValueError(f"缺少必需根文件：{relative_path}")

    version = (source_dir / "VERSION").read_text(encoding="utf-8").strip()
    if not version:
        raise ValueError("VERSION 为空")

    try:
        manifest_value = json.loads(
            (source_dir / "manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("manifest.json 无法解析") from error
    if not isinstance(manifest_value, dict):
        raise ValueError("manifest.json 必须是对象")

    included = {relative.as_posix() for relative, _ in files}
    missing_workflows = [
        workflow for workflow in 必需工作流 if workflow not in included
    ]
    if missing_workflows:
        raise ValueError(f"轻量包缺少必需工作流：{', '.join(missing_workflows)}")
    return version, manifest_value


def _准备清单(
    manifest: Mapping[str, object],
    ars_files: Iterable[tuple[PurePosixPath, bytes]],
) -> bytes:
    """生成轻量包专用清单，不修改源目录中的 manifest.json。"""

    package_manifest = json.loads(json.dumps(manifest, ensure_ascii=False))
    if not isinstance(package_manifest, dict):
        raise ValueError("manifest.json 必须是对象")

    packaging = package_manifest.get("packaging")
    if not isinstance(packaging, dict):
        packaging = {}
        package_manifest["packaging"] = packaging
    packaging["variant"] = "runtime-core"

    source_overlay = package_manifest.get("source_overlay")
    if not isinstance(source_overlay, dict):
        source_overlay = {}
        package_manifest["source_overlay"] = source_overlay
    file_count, tree_sha256 = 计算目录摘要(ars_files)
    source_overlay["vendored_file_count"] = file_count
    source_overlay["vendored_tree_sha256"] = tree_sha256

    return (
        json.dumps(package_manifest, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")


def _文件模式(path: Path) -> int:
    """保留是否可执行这一语义，同时固定普通文件模式。"""

    return 0o755 if path.stat().st_mode & stat.S_IXUSR else 0o644


def _条目数据(
    source_dir: Path,
    files: list[tuple[PurePosixPath, Path]],
    manifest_bytes: bytes,
) -> dict[str, tuple[str, bytes | None, int]]:
    """准备目录和文件条目，返回条目类型、内容和模式。"""

    entries: dict[str, tuple[str, bytes | None, int]] = {}
    for relative, path in files:
        name = relative.as_posix()
        content = manifest_bytes if name == "manifest.json" else path.read_bytes()
        entries[name] = ("file", content, _文件模式(path))

        parent = relative.parent
        while str(parent) not in ("", "."):
            parent_name = parent.as_posix()
            entries.setdefault(parent_name, ("directory", None, 0o755))
            parent = parent.parent
    return entries


def _写入确定性归档(
    destination: Path,
    entries: Mapping[str, tuple[str, bytes | None, int]],
) -> None:
    """写入排序且元数据固定的 tar.gz 文件。"""

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as raw_output:
        # gzip 时间戳和文件名都固定，否则同一组内容的归档字节会不同。
        with gzip.GzipFile(
            fileobj=raw_output,
            mode="wb",
            filename="",
            mtime=0,
            compresslevel=9,
        ) as compressed_output:
            with tarfile.open(
                fileobj=compressed_output,
                mode="w",
                format=tarfile.PAX_FORMAT,
            ) as archive:
                for name in sorted(entries):
                    entry_type, content, mode = entries[name]
                    tar_info = tarfile.TarInfo(name=name)
                    tar_info.uid = 0
                    tar_info.gid = 0
                    tar_info.uname = ""
                    tar_info.gname = ""
                    tar_info.mtime = 0
                    tar_info.mode = mode
                    tar_info.pax_headers = {}
                    if entry_type == "directory":
                        tar_info.type = tarfile.DIRTYPE
                        tar_info.size = 0
                        archive.addfile(tar_info)
                    else:
                        if content is None:
                            raise ValueError(f"文件条目缺少内容：{name}")
                        tar_info.type = tarfile.REGTYPE
                        tar_info.size = len(content)
                        archive.addfile(tar_info, io.BytesIO(content))


def _原子写入归档(
    destination: Path,
    entries: Mapping[str, tuple[str, bytes | None, int]],
) -> Path:
    """先写临时文件，再原子替换目标归档。"""

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
        _写入确定性归档(temporary_path, entries)
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return destination


def 构建运行包(
    source_dir: Path | str = 默认源目录,
    output_path: Path | str | None = None,
) -> Path:
    """从源技能目录构建默认的 runtime-core tar.gz。"""

    source = Path(source_dir)
    files = 收集文件(source)
    version, manifest = _读取源元数据(source, files)
    ars_files = [
        (PurePosixPath(*relative.parts[1:]), path.read_bytes())
        for relative, path in files
        if relative.parts and relative.parts[0] == "ars"
    ]
    manifest_bytes = _准备清单(manifest, ars_files)
    entries = _条目数据(source, files, manifest_bytes)
    destination = (
        Path(output_path)
        if output_path is not None
        else 仓库根目录
        / "dist"
        / f"{技能名称}-{version}-runtime-core.tar.gz"
    )
    return _原子写入归档(destination, entries)


def 构建运行目录(
    source_dir: Path | str,
    output_dir: Path | str,
) -> Path:
    """生成同样内容的解压目录，目录元数据也使用固定时间戳。"""

    source = Path(source_dir)
    files = 收集文件(source)
    _version, manifest = _读取源元数据(source, files)
    ars_files = [
        (PurePosixPath(*relative.parts[1:]), path.read_bytes())
        for relative, path in files
        if relative.parts and relative.parts[0] == "ars"
    ]
    manifest_bytes = _准备清单(manifest, ars_files)
    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"输出目录已存在：{destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_dir = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent)
    )
    try:
        entries = _条目数据(source, files, manifest_bytes)
        for name, (entry_type, content, mode) in entries.items():
            path = temporary_dir / Path(name)
            if entry_type == "directory":
                path.mkdir(parents=True, exist_ok=True)
                path.chmod(mode)
                os.utime(path, ns=(0, 0))
                continue
            if content is None:
                raise ValueError(f"文件条目缺少内容：{name}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            path.chmod(mode)
            os.utime(path, ns=(0, 0))
        os.utime(temporary_dir, ns=(0, 0))
        os.replace(temporary_dir, destination)
    except BaseException:
        shutil.rmtree(temporary_dir, ignore_errors=True)
        raise
    return destination


# 使用英文别名便于其他 Python 测试或自动化脚本调用。
build_runtime_package = 构建运行包
build_runtime_directory = 构建运行目录
collect_files = 收集文件
directory_summary = 计算目录摘要


def _默认输出路径(source_dir: Path, output_format: str) -> Path:
    """根据源目录版本生成默认输出路径。"""

    version = (source_dir / "VERSION").read_text(encoding="utf-8").strip()
    suffix = ".tar.gz" if output_format == "tar.gz" else ""
    return (
        仓库根目录
        / "dist"
        / f"{技能名称}-{version}-runtime-core{suffix}"
    )


def main(argv: list[str] | None = None) -> int:
    """解析命令行参数并构建运行包。"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=默认源目录)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--format",
        choices=("tar.gz", "directory"),
        default="tar.gz",
        help="输出 tar.gz 归档或解压目录",
    )
    args = parser.parse_args(argv)

    output = args.output or _默认输出路径(args.source_dir, args.format)
    if args.format == "directory":
        result = 构建运行目录(args.source_dir, output)
    else:
        result = 构建运行包(args.source_dir, output)
    print(f"runtime-core 构建完成：{result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
