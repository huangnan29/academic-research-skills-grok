#!/usr/bin/env python3
"""安装并验证 ARS-Grok Build 技能包。

本脚本只使用 Python 标准库。默认把技能安装到用户的
``~/.grok/skills/academic-research-suite``，并把 Grok 命令包装文件安装到
``~/.grok/commands``。
"""

from __future__ import annotations

import argparse
import datetime as _datetime
import filecmp
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Iterable, Optional, Sequence


SKILL_NAME = "academic-research-suite"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = REPOSITORY_ROOT / "skills" / SKILL_NAME

REQUIRED_FILES = ("VERSION", "manifest.json", "SKILL.md")
REQUIRED_WORKFLOWS = (
    "ars/deep-research/WORKFLOW.md",
    "ars/academic-paper/WORKFLOW.md",
    "ars/academic-paper-reviewer/WORKFLOW.md",
    "ars/academic-pipeline/WORKFLOW.md",
    "ars/experiment-agent/WORKFLOW.md",
)

# 命令名称固定在适配器清单中，避免源目录意外增加文件后被静默安装。
EXPECTED_COMMANDS = (
    "ars-3w.md",
    "ars-abstract.md",
    "ars-cache-invalidate.md",
    "ars-citation-check.md",
    "ars-disclosure.md",
    "ars-format-convert.md",
    "ars-full.md",
    "ars-lit-review.md",
    "ars-mark-read.md",
    "ars-outline.md",
    "ars-plan.md",
    "ars-rebuttal-audit.md",
    "ars-reviewer.md",
    "ars-revision-coach.md",
    "ars-revision.md",
    "ars-unmark-read.md",
)


class ValidationError(Exception):
    """技能包结构不符合安装契约。"""


def _lexists(path: Path) -> bool:
    """判断路径是否存在，包括悬空符号链接。"""

    return os.path.lexists(path)


def _remove_entry(path: Path) -> None:
    """删除文件、目录或符号链接，不输出其内容。"""

    if not _lexists(path):
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _copy_entry(source: Path, destination: Path) -> None:
    """复制一个文件、目录或符号链接，用于生成可恢复备份。"""

    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        destination.symlink_to(os.readlink(source), target_is_directory=source.is_dir())
    elif source.is_dir():
        shutil.copytree(source, destination, symlinks=True)
    else:
        shutil.copy2(source, destination)


def _source_command_names(source_dir: Path) -> tuple[str, ...]:
    """读取源命令文件名，不读取命令正文。"""

    command_dir = source_dir / "grok" / "commands"
    if not command_dir.is_dir():
        return ()
    return tuple(sorted(path.name for path in command_dir.glob("*.md") if path.is_file()))


def _resolve_source_dir(source_dir: Path | str | None) -> Path:
    """解析源目录；命令行始终使用仓库内固定源目录。"""

    return SOURCE_DIR if source_dir is None else Path(source_dir)


def validate_package(source_dir: Path | str | None = None) -> list[str]:
    """返回源技能包的结构错误；空列表表示通过。"""

    source = _resolve_source_dir(source_dir)
    errors: list[str] = []

    if not source.is_dir():
        return ["源技能目录缺失"]

    for relative_path in REQUIRED_FILES:
        if not (source / relative_path).is_file():
            errors.append(f"缺少关键文件：{relative_path}")

    manifest_path = source / "manifest.json"
    if manifest_path.is_file():
        try:
            with manifest_path.open("r", encoding="utf-8") as manifest_file:
                manifest = json.load(manifest_file)
            if not isinstance(manifest, dict):
                errors.append("manifest.json 不是对象")
            elif manifest.get("name") != SKILL_NAME:
                errors.append("manifest.json 的技能名称不匹配")
        except (OSError, UnicodeError, json.JSONDecodeError):
            errors.append("manifest.json 无法解析")

    ars_dir = source / "ars"
    if not ars_dir.is_dir():
        errors.append("ars 目录缺失")

    for relative_path in REQUIRED_WORKFLOWS:
        if not (source / relative_path).is_file():
            errors.append(f"缺少关键工作流：{relative_path}")

    command_names = _source_command_names(source)
    expected = set(EXPECTED_COMMANDS)
    actual = set(command_names)
    if len(command_names) != len(EXPECTED_COMMANDS) or actual != expected:
        errors.append("grok/commands 未包含完整的 16 个命令")

    return errors


def _raise_if_invalid(source_dir: Path) -> None:
    """在结构检查失败时抛出不含敏感内容的错误。"""

    errors = validate_package(source_dir)
    if errors:
        raise ValidationError("；".join(errors))


def _installed_errors(target_root: Path, source_dir: Path) -> list[str]:
    """检查已安装技能及其顶层命令。"""

    skill_dir = target_root / "skills" / SKILL_NAME
    errors = validate_package(skill_dir)
    command_dir = target_root / "commands"
    source_commands = source_dir / "grok" / "commands"

    if not command_dir.is_dir():
        errors.append("Grok 命令目录缺失")
    else:
        for command_name in EXPECTED_COMMANDS:
            installed = command_dir / command_name
            if not installed.is_file():
                errors.append(f"缺少已安装命令：{command_name}")
                continue
            source_command = source_commands / command_name
            try:
                if not filecmp.cmp(source_command, installed, shallow=False):
                    errors.append(f"已安装命令内容不一致：{command_name}")
            except OSError:
                errors.append(f"无法核对已安装命令：{command_name}")

    return errors


def _backup_name() -> str:
    """生成带微秒的本地时间戳，避免连续安装覆盖同一备份目录。"""

    return _datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")


def _new_backup_dir(target_root: Path) -> Path:
    """创建唯一备份目录。"""

    backups_root = target_root / "backups"
    backups_root.mkdir(parents=True, exist_ok=True)
    candidate = backups_root / _backup_name()
    suffix = 1
    while _lexists(candidate):
        candidate = backups_root / f"{_backup_name()}-{suffix}"
        suffix += 1
    candidate.mkdir()
    return candidate


def _backup_existing(
    target_root: Path,
    skill_dir: Path,
    command_dir: Path,
) -> tuple[Optional[Path], list[tuple[Path, Path]]]:
    """复制已有安装目标，返回备份目录和需要暂存的目标清单。"""

    existing_skill = _lexists(skill_dir)
    existing_commands = [
        command_dir / command_name
        for command_name in EXPECTED_COMMANDS
        if _lexists(command_dir / command_name)
    ]

    if not existing_skill and not existing_commands:
        return None, []

    backup_dir = _new_backup_dir(target_root)
    if existing_skill:
        _copy_entry(skill_dir, backup_dir / "skills" / SKILL_NAME)

    for command_path in existing_commands:
        _copy_entry(command_path, backup_dir / "commands" / command_path.name)

    targets: list[tuple[Path, Path]] = []
    if existing_skill:
        targets.append((skill_dir, Path("skill")))
    targets.extend((path, Path("commands") / path.name) for path in existing_commands)
    return backup_dir, targets


def _move_existing_to_hold(
    target_root: Path,
    existing_targets: Iterable[tuple[Path, Path]],
) -> tuple[Path, list[tuple[Path, Path]]]:
    """把已备份目标移到同一文件系统的暂存目录，准备原子替换。"""

    hold_root = Path(tempfile.mkdtemp(prefix=".ars-grok-old-", dir=str(target_root)))
    moved: list[tuple[Path, Path]] = []
    try:
        for original, relative_hold_path in existing_targets:
            hold_path = hold_root / relative_hold_path
            hold_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(original, hold_path)
            moved.append((original, hold_path))
    except BaseException:
        for original, hold_path in reversed(moved):
            if _lexists(hold_path):
                original.parent.mkdir(parents=True, exist_ok=True)
                os.replace(hold_path, original)
        shutil.rmtree(hold_root, ignore_errors=True)
        raise
    return hold_root, moved


def _restore_held(hold_root: Path, moved: Iterable[tuple[Path, Path]]) -> None:
    """回滚暂存目标。"""

    for original, hold_path in reversed(list(moved)):
        if _lexists(original):
            _remove_entry(original)
        if _lexists(hold_path):
            original.parent.mkdir(parents=True, exist_ok=True)
            os.replace(hold_path, original)
    shutil.rmtree(hold_root, ignore_errors=True)


def install_skill(
    target_root: Path | str | None = None,
    source_dir: Path | str | None = None,
) -> Path:
    """安装技能并返回安装目录；失败时不输出文件内容。"""

    source = _resolve_source_dir(source_dir).resolve()
    _raise_if_invalid(source)

    root = Path(target_root).expanduser() if target_root is not None else Path.home() / ".grok"
    root = root.resolve()
    skill_dir = root / "skills" / SKILL_NAME
    command_dir = root / "commands"
    if skill_dir == source:
        raise ValidationError("目标目录不能与源技能目录相同")
    root.mkdir(parents=True, exist_ok=True)
    (root / "skills").mkdir(parents=True, exist_ok=True)
    command_dir.mkdir(parents=True, exist_ok=True)

    staging_root = Path(tempfile.mkdtemp(prefix=".ars-grok-stage-", dir=str(root)))
    hold_root: Optional[Path] = None
    moved_targets: list[tuple[Path, Path]] = []
    installed_skill = False
    installed_commands: list[Path] = []
    try:
        staged_skill = staging_root / "skills" / SKILL_NAME
        staged_commands = staging_root / "commands"
        staged_skill.parent.mkdir(parents=True, exist_ok=True)
        staged_commands.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, staged_skill, symlinks=True)
        for command_name in EXPECTED_COMMANDS:
            shutil.copy2(
                source / "grok" / "commands" / command_name,
                staged_commands / command_name,
            )

        backup_dir, existing_targets = _backup_existing(root, skill_dir, command_dir)
        del backup_dir  # 备份目录已经落盘，安装过程不需要再次读取它。
        if existing_targets:
            hold_root, moved_targets = _move_existing_to_hold(root, existing_targets)

        os.replace(staged_skill, skill_dir)
        installed_skill = True
        for command_name in EXPECTED_COMMANDS:
            destination = command_dir / command_name
            os.replace(staged_commands / command_name, destination)
            installed_commands.append(destination)

        errors = _installed_errors(root, source)
        if errors:
            raise ValidationError("；".join(errors))

        if hold_root is not None:
            shutil.rmtree(hold_root, ignore_errors=True)
            hold_root = None
        return skill_dir
    except BaseException:
        for installed_command in reversed(installed_commands):
            _remove_entry(installed_command)
        if installed_skill:
            _remove_entry(skill_dir)
        if hold_root is not None:
            _restore_held(hold_root, moved_targets)
            hold_root = None
        raise
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)


def check(
    source_dir: Path | str | None = None,
    target_root: Path | str | None = None,
) -> bool:
    """只检查源技能包及已有目标，不创建或修改任何目录。"""

    errors = validate_package(source_dir)
    source = _resolve_source_dir(source_dir).resolve()
    if not errors and target_root is not None:
        root = Path(target_root).expanduser().resolve()
        skill_dir = root / "skills" / SKILL_NAME
        command_dir = root / "commands"
        has_install_target = _lexists(skill_dir) or any(
            _lexists(command_dir / command_name) for command_name in EXPECTED_COMMANDS
        )
        if has_install_target:
            errors.extend(_installed_errors(root, source))
    if errors:
        print("检查失败：" + "；".join(errors))
        return False
    print("检查通过：源技能包结构完整，未写入安装目录。")
    return True


def _build_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器。"""

    parser = argparse.ArgumentParser(description="安装并验证 ARS-Grok Build 技能包")
    parser.add_argument(
        "--check",
        action="store_true",
        help="只检查源技能包，不写入 Grok 目录",
    )
    parser.add_argument(
        "--target-root",
        type=Path,
        help="指定 Grok 根目录，主要用于隔离测试",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """执行命令行入口并返回进程状态码。"""

    args = _build_parser().parse_args(argv)
    if args.check:
        return 0 if check(target_root=args.target_root) else 1

    try:
        install_skill(target_root=args.target_root)
    except ValidationError as error:
        print(f"安装失败：{error}")
        return 1
    except (OSError, shutil.Error, ValueError):
        # 不打印异常详情，避免把用户路径或其他敏感信息带到终端。
        print("安装失败：文件操作未完成，已有安装如存在应仍保留在备份目录。")
        return 1

    print("安装成功：技能、16 个命令和关键工作流均已验证。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
