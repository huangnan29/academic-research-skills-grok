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
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import sys
import tempfile
from typing import Any, Iterable, Optional, Sequence


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

# 这三个文件是 Grok 适配器提供的独立 Agent。保留 ars- 作用域前缀，避免
# 与用户或 Grok 内置 Agent 同名；文件正文仍绑定到上游的下划线角色名。
EXPECTED_AGENTS = (
    "ars-research-architect.md",
    "ars-synthesis.md",
    "ars-report-compiler.md",
)

HOOK_DIRECTORY = Path("grok") / "hooks"
HOOK_CONFIG_NAME = "ars-academic-research-suite.json"
HOOK_SOURCE_FILES = (
    "pre_tool_use.py",
    HOOK_CONFIG_NAME,
)
HOOK_CONFIG_TARGET = Path("hooks") / HOOK_CONFIG_NAME
HOOK_PRE_TOOL_PLACEHOLDER = "__ARS_PRE_TOOL_USE_HOOK__"


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


def _hook_source_dir(source_dir: Path) -> Path:
    """返回随技能源一起发布的 Grok Hook 目录。"""

    return source_dir / HOOK_DIRECTORY


def _hook_template_errors(source_dir: Path) -> list[str]:
    """验证 Hook 模板只包含本地 command Hook 和精确工具匹配器。"""

    hook_dir = _hook_source_dir(source_dir)
    errors: list[str] = []
    for file_name in HOOK_SOURCE_FILES:
        if not (hook_dir / file_name).is_file():
            errors.append(f"缺少 Hook 源文件：{HOOK_DIRECTORY / file_name}")

    template_path = hook_dir / HOOK_CONFIG_NAME
    if not template_path.is_file():
        return errors
    try:
        template = json.loads(template_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        errors.append("Grok Hook 配置模板无法解析")
        return errors

    if not isinstance(template, dict):
        errors.append("Grok Hook 配置模板必须是对象")
        return errors
    try:
        serialized = json.dumps(template, ensure_ascii=False).lower()
    except (TypeError, ValueError):
        errors.append("Grok Hook 配置模板无法序列化")
        return errors
    if "http://" in serialized or "https://" in serialized:
        errors.append("Grok Hook 配置不得包含 HTTP 地址")

    hooks = template.get("hooks")
    if not isinstance(hooks, dict):
        errors.append("Grok Hook 配置缺少 hooks 对象")
        return errors
    unexpected_events = set(hooks) - {"PreToolUse"}
    if unexpected_events:
        errors.append("Grok Hook 配置只允许 PreToolUse 事件")
    pre_tool_hooks = hooks.get("PreToolUse")
    if not isinstance(pre_tool_hooks, list) or not pre_tool_hooks:
        errors.append("Grok Hook 配置缺少 PreToolUse Hook")

    def validate_command_hook(item: Any, label: str, placeholder: str) -> None:
        if not isinstance(item, dict):
            errors.append(f"{label} Hook 条目必须是对象")
            return
        if item.get("type") != "command":
            errors.append(f"{label} Hook 只能使用 command 类型")
        command = item.get("command")
        if not isinstance(command, str) or not command.strip():
            errors.append(f"{label} Hook 缺少本地 command")
        elif not command.startswith("uv run python ") or placeholder not in command:
            errors.append(f"{label} Hook 必须通过 uv run python 调用随包脚本")

    if isinstance(pre_tool_hooks, list):
        for index, item in enumerate(pre_tool_hooks):
            if not isinstance(item, dict):
                errors.append(f"PreToolUse[{index}] Hook 条目必须是对象")
                continue
            if item.get("matcher") != "^(search_replace|run_terminal_command|run_terminal_cmd)$":
                errors.append("PreToolUse matcher 必须只匹配 search_replace|run_terminal_command|run_terminal_cmd")
            nested = item.get("hooks")
            if not isinstance(nested, list) or not nested:
                errors.append(f"PreToolUse[{index}] 缺少嵌套 Hook")
                continue
            for nested_index, nested_item in enumerate(nested):
                validate_command_hook(
                    nested_item,
                    f"PreToolUse[{index}].hooks[{nested_index}]",
                    HOOK_PRE_TOOL_PLACEHOLDER,
                )
    return errors


def _agent_source_paths(source_dir: Path) -> tuple[Path, ...]:
    """返回三个顶层 Grok Agent 定义的源路径。"""

    return tuple(source_dir / "grok" / "agents" / name for name in EXPECTED_AGENTS)


def _directory_summary(directory: Path) -> tuple[int, str]:
    """按相对路径、NUL 分隔和每个文件的 SHA-256 计算目录摘要。

    这里必须与 ``scripts/validate_skill.py`` 使用完全相同的顺序和拼接规则，
    这样安装器在写入前就能拒绝摘要不匹配的源包。
    """

    total_digest = hashlib.sha256()
    files = sorted(path for path in directory.rglob("*") if path.is_file())
    for path in files:
        relative_path = path.relative_to(directory).as_posix().encode("utf-8")
        file_digest = hashlib.sha256(path.read_bytes()).digest()
        total_digest.update(relative_path)
        total_digest.update(b"\0")
        total_digest.update(file_digest)
        total_digest.update(b"\n")
    return len(files), total_digest.hexdigest()


def _metadata_version(skill_text: str) -> Optional[str]:
    """从 SKILL.md 的 YAML 前置元数据中读取 metadata.version。"""

    front_matter = re.match(r"\A---\n(.*?)\n---\n", skill_text, flags=re.DOTALL)
    if not front_matter:
        return None
    version_match = re.search(
        r"^\s*version:\s*[\"']?([^\"'\s]+)[\"']?\s*$",
        front_matter.group(1),
        flags=re.MULTILINE,
    )
    return version_match.group(1) if version_match else None


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

    version: Optional[str] = None
    version_path = source / "VERSION"
    if version_path.is_file():
        try:
            version = version_path.read_text(encoding="utf-8").strip()
            if not version:
                errors.append("VERSION 为空")
        except (OSError, UnicodeError):
            errors.append("VERSION 无法读取")

    manifest_path = source / "manifest.json"
    manifest: Optional[dict[str, object]] = None
    if manifest_path.is_file():
        try:
            with manifest_path.open("r", encoding="utf-8") as manifest_file:
                parsed_manifest = json.load(manifest_file)
            if not isinstance(parsed_manifest, dict):
                errors.append("manifest.json 不是对象")
            else:
                manifest = parsed_manifest
                if manifest.get("name") != SKILL_NAME:
                    errors.append("manifest.json 的技能名称不匹配")
                if version is not None and manifest.get("adapter_version") != version:
                    errors.append("VERSION 与 manifest.json adapter_version 不一致")
        except (OSError, UnicodeError, json.JSONDecodeError):
            errors.append("manifest.json 无法解析")

    skill_path = source / "SKILL.md"
    if skill_path.is_file():
        try:
            skill_text = skill_path.read_text(encoding="utf-8")
            metadata_version = _metadata_version(skill_text)
            if metadata_version is None:
                errors.append("SKILL.md 缺少有效的 metadata.version")
            elif version is not None and metadata_version != version:
                errors.append("SKILL.md metadata.version 与 VERSION 不一致")
        except (OSError, UnicodeError):
            errors.append("SKILL.md 无法读取")

    ars_dir = source / "ars"
    if not ars_dir.is_dir():
        errors.append("ars 目录缺失")
    else:
        try:
            actual_file_count, actual_tree_sha256 = _directory_summary(ars_dir)
        except (OSError, UnicodeError):
            actual_file_count = None
            actual_tree_sha256 = None
            errors.append("ars/ 目录摘要无法计算")

        source_overlay = manifest.get("source_overlay") if manifest else None
        if not isinstance(source_overlay, dict):
            errors.append("manifest.json 缺少有效的 source_overlay")
        else:
            expected_file_count = source_overlay.get("vendored_file_count")
            if not isinstance(expected_file_count, int) or isinstance(
                expected_file_count, bool
            ):
                errors.append("manifest.json source_overlay.vendored_file_count 无效")
            elif actual_file_count is not None and actual_file_count != expected_file_count:
                errors.append(
                    "manifest.json source_overlay.vendored_file_count 与 ars/ 文件数不一致"
                )

            expected_tree_sha256 = source_overlay.get("vendored_tree_sha256")
            if not isinstance(expected_tree_sha256, str):
                errors.append("manifest.json source_overlay.vendored_tree_sha256 无效")
            elif actual_tree_sha256 is not None and actual_tree_sha256 != expected_tree_sha256:
                errors.append(
                    "manifest.json source_overlay.vendored_tree_sha256 与 ars/ 目录摘要不一致"
                )

    for relative_path in REQUIRED_WORKFLOWS:
        if not (source / relative_path).is_file():
            errors.append(f"缺少关键工作流：{relative_path}")

    command_names = _source_command_names(source)
    expected = set(EXPECTED_COMMANDS)
    actual = set(command_names)
    if len(command_names) != len(EXPECTED_COMMANDS) or actual != expected:
        errors.append("grok/commands 未包含完整的 16 个命令")

    for agent_path in _agent_source_paths(source):
        if not agent_path.is_file():
            errors.append(f"缺少 Grok Agent 定义：{agent_path.relative_to(source)}")

    errors.extend(_hook_template_errors(source))

    return errors


def _raise_if_invalid(source_dir: Path) -> None:
    """在结构检查失败时抛出不含敏感内容的错误。"""

    errors = validate_package(source_dir)
    if errors:
        raise ValidationError("；".join(errors))


def _render_hook_config(source_dir: Path, target_skill_dir: Path) -> bytes:
    """将 Hook 模板中的脚本占位符安全渲染为绝对路径。"""

    template_path = _hook_source_dir(source_dir) / HOOK_CONFIG_NAME
    template = json.loads(template_path.read_text(encoding="utf-8"))

    pre_tool_hook = target_skill_dir / "grok" / "hooks" / "pre_tool_use.py"
    # command 字符串最终由 Grok 的本地 shell 执行，先使用 shell quoting，再交给
    # JSON 序列化处理反斜杠和引号，避免目标根目录中的空格或特殊字符改变命令。
    replacements = {
        HOOK_PRE_TOOL_PLACEHOLDER: shlex.quote(str(pre_tool_hook.resolve())),
    }

    def replace(value: Any) -> Any:
        if isinstance(value, str):
            rendered = value
            for placeholder, replacement in replacements.items():
                rendered = rendered.replace(placeholder, replacement)
            return rendered
        if isinstance(value, list):
            return [replace(item) for item in value]
        if isinstance(value, dict):
            return {key: replace(item) for key, item in value.items()}
        return value

    rendered = replace(template)
    rendered_text = json.dumps(rendered, ensure_ascii=False, indent=2) + "\n"
    if HOOK_PRE_TOOL_PLACEHOLDER in rendered_text:
        raise ValidationError("Grok Hook 配置仍包含未渲染的路径占位符")
    return rendered_text.encode("utf-8")


def _hooks_are_identical(target_root: Path, source_dir: Path) -> bool:
    """判断已托管 Hook 配置是否与当前安装路径下的模板一致。"""

    target = target_root / HOOK_CONFIG_TARGET
    if not target.is_file():
        return False
    try:
        expected = _render_hook_config(
            source_dir,
            target_root / "skills" / SKILL_NAME,
        )
        return target.read_bytes() == expected
    except (OSError, UnicodeError, json.JSONDecodeError, ValidationError):
        return False


def _installed_errors(
    target_root: Path,
    source_dir: Path,
    hooks_enabled: bool = False,
) -> list[str]:
    """检查已安装技能及其顶层命令。"""

    skill_dir = target_root / "skills" / SKILL_NAME
    errors = validate_package(skill_dir)
    if skill_dir.is_dir():
        try:
            if _directory_summary(source_dir) != _directory_summary(skill_dir):
                errors.append("已安装技能内容与源技能不一致")
        except (OSError, UnicodeError):
            errors.append("无法核对已安装技能内容")
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

    agents_dir = target_root / "agents"
    if not agents_dir.is_dir():
        errors.append("Grok Agent 目录缺失")
    else:
        source_agents_dir = source_dir / "grok" / "agents"
        for agent_name in EXPECTED_AGENTS:
            installed = agents_dir / agent_name
            source_agent = source_agents_dir / agent_name
            if not installed.is_file():
                errors.append(f"缺少已安装 Agent：{agent_name}")
                continue
            try:
                if not filecmp.cmp(source_agent, installed, shallow=False):
                    errors.append(f"已安装 Agent 内容不一致：{agent_name}")
            except OSError:
                errors.append(f"无法核对已安装 Agent：{agent_name}")

    if hooks_enabled:
        if not _hooks_are_identical(target_root, source_dir):
            errors.append("已安装 Grok Hook 配置不存在或内容不一致")

    return errors


def _installation_is_identical(
    target_root: Path,
    source_dir: Path,
    hooks_enabled: bool = False,
) -> bool:
    """判断已安装技能、Agent 和 16 个命令是否与源包完全一致。"""

    skill_dir = target_root / "skills" / SKILL_NAME
    if not skill_dir.is_dir():
        return False
    try:
        if _directory_summary(source_dir) != _directory_summary(skill_dir):
            return False
    except (OSError, UnicodeError):
        return False

    command_dir = target_root / "commands"
    if not command_dir.is_dir():
        return False

    source_commands = source_dir / "grok" / "commands"
    for command_name in EXPECTED_COMMANDS:
        source_command = source_commands / command_name
        installed_command = command_dir / command_name
        try:
            if not filecmp.cmp(source_command, installed_command, shallow=False):
                return False
        except OSError:
            return False

    agents_dir = target_root / "agents"
    source_agents_dir = source_dir / "grok" / "agents"
    if not agents_dir.is_dir():
        return False
    for agent_name in EXPECTED_AGENTS:
        try:
            if not filecmp.cmp(
                source_agents_dir / agent_name,
                agents_dir / agent_name,
                shallow=False,
            ):
                return False
        except OSError:
            return False

    if hooks_enabled and not _hooks_are_identical(target_root, source_dir):
        return False
    return True


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
    (candidate / ".ars-grok-backup.json").write_text(
        json.dumps({"owner": SKILL_NAME, "schema_version": 1}) + "\n", encoding="utf-8"
    )
    return candidate


def _owned_backup(path: Path) -> bool:
    """只清理本安装器带明确标记的备份，旧备份和其他项目目录保留。"""
    if path.is_symlink() or not path.is_dir():
        return False
    marker = path / ".ars-grok-backup.json"
    if marker.is_symlink():
        return False
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
        return isinstance(data, dict) and data.get("owner") == SKILL_NAME and data.get("schema_version") == 1
    except (OSError, ValueError):
        return False


def _prune_backups(target_root: Path, keep_backups: int) -> None:
    """安装成功后仅保留按时间戳排序的最新备份。"""

    backups_root = target_root / "backups"
    if not backups_root.is_dir():
        return
    backup_dirs = sorted(
        path
        for path in backups_root.iterdir()
        if _owned_backup(path)
    )
    stale_backups = backup_dirs if keep_backups == 0 else backup_dirs[:-keep_backups]
    for backup_dir in stale_backups:
        _remove_entry(backup_dir)


def _backup_existing(
    target_root: Path,
    skill_dir: Path,
    command_dir: Path,
    agents_dir: Path,
    hook_path: Optional[Path] = None,
) -> tuple[Optional[Path], list[tuple[Path, Path]]]:
    """复制已有安装目标，返回备份目录和需要暂存的目标清单。"""

    existing_skill = _lexists(skill_dir)
    existing_commands = [
        command_dir / command_name
        for command_name in EXPECTED_COMMANDS
        if _lexists(command_dir / command_name)
    ]
    existing_agents = [
        agents_dir / agent_name
        for agent_name in EXPECTED_AGENTS
        if _lexists(agents_dir / agent_name)
    ]
    existing_hook = hook_path is not None and _lexists(hook_path)

    if not existing_skill and not existing_commands and not existing_agents and not existing_hook:
        return None, []

    backup_dir = _new_backup_dir(target_root)
    if existing_skill:
        _copy_entry(skill_dir, backup_dir / "skills" / SKILL_NAME)

    for command_path in existing_commands:
        _copy_entry(command_path, backup_dir / "commands" / command_path.name)

    for agent_path in existing_agents:
        _copy_entry(agent_path, backup_dir / "agents" / agent_path.name)

    if hook_path is not None and existing_hook:
        _copy_entry(hook_path, backup_dir / HOOK_CONFIG_TARGET)

    targets: list[tuple[Path, Path]] = []
    if existing_skill:
        targets.append((skill_dir, Path("skill")))
    targets.extend((path, Path("commands") / path.name) for path in existing_commands)
    targets.extend((path, Path("agents") / path.name) for path in existing_agents)
    if hook_path is not None and existing_hook:
        targets.append((hook_path, HOOK_CONFIG_TARGET))
    return backup_dir, targets


def _backup_existing_hook(
    target_root: Path,
    hook_path: Path,
) -> tuple[Optional[Path], list[tuple[Path, Path]]]:
    """只备份待替换的托管 Hook，不触碰技能、命令或其他 Hook。"""

    if not _lexists(hook_path):
        return None, []
    backup_dir = _new_backup_dir(target_root)
    _copy_entry(hook_path, backup_dir / HOOK_CONFIG_TARGET)
    return backup_dir, [(hook_path, HOOK_CONFIG_TARGET)]


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


def _install_hooks_only(
    target_root: Path,
    source_dir: Path,
    keep_backups: int,
) -> None:
    """在技能已是最新时只原子更新 Hook 配置。"""

    hook_path = target_root / HOOK_CONFIG_TARGET
    rendered_config = _render_hook_config(
        source_dir,
        target_root / "skills" / SKILL_NAME,
    )
    target_root.mkdir(parents=True, exist_ok=True)
    hooks_dir = target_root / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    staging_root = Path(tempfile.mkdtemp(prefix=".ars-grok-hook-stage-", dir=str(target_root)))
    hold_root: Optional[Path] = None
    moved_targets: list[tuple[Path, Path]] = []
    replaced = False
    try:
        staged_config = staging_root / HOOK_CONFIG_NAME
        staged_config.write_bytes(rendered_config)
        _, existing_targets = _backup_existing_hook(target_root, hook_path)
        if existing_targets:
            hold_root, moved_targets = _move_existing_to_hold(target_root, existing_targets)
        os.replace(staged_config, hook_path)
        replaced = True
        if not _hooks_are_identical(target_root, source_dir):
            raise ValidationError("已安装 Grok Hook 配置内容不一致")
        _prune_backups(target_root, keep_backups)
        if hold_root is not None:
            shutil.rmtree(hold_root, ignore_errors=True)
            hold_root = None
    except BaseException:
        if replaced:
            _remove_entry(hook_path)
        if hold_root is not None:
            _restore_held(hold_root, moved_targets)
            hold_root = None
        raise
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)


def disable_hooks(target_root: Path | str | None = None) -> bool:
    """只移除本适配器托管的 Hook 配置文件，保留其他 Hook 和技能文件。"""

    root = Path(target_root).expanduser() if target_root is not None else Path.home() / ".grok"
    root = root.resolve()
    hook_path = root / HOOK_CONFIG_TARGET
    if not _lexists(hook_path):
        return False
    # 目录不是本适配器生成的合法 Hook 文件，避免 --disable-hooks 递归删除用户目录。
    if hook_path.is_dir() and not hook_path.is_symlink():
        raise ValidationError("托管 Hook 路径不是文件，拒绝递归删除")
    hook_path.unlink()
    return True


def install_skill(
    target_root: Path | str | None = None,
    source_dir: Path | str | None = None,
    keep_backups: int = 3,
    enable_hooks: bool = False,
) -> Path:
    """安装技能并返回安装目录；Hook 只有显式启用时才会写入。"""

    if keep_backups < 0:
        raise ValidationError("备份保留数量不能为负数")
    source = _resolve_source_dir(source_dir).resolve()
    _raise_if_invalid(source)

    root = Path(target_root).expanduser() if target_root is not None else Path.home() / ".grok"
    root = root.resolve()
    skill_dir = root / "skills" / SKILL_NAME
    command_dir = root / "commands"
    agents_dir = root / "agents"
    hook_path = root / HOOK_CONFIG_TARGET
    if skill_dir == source:
        raise ValidationError("目标目录不能与源技能目录相同")
    if _installation_is_identical(root, source):
        if not enable_hooks or _hooks_are_identical(root, source):
            return skill_dir
        _install_hooks_only(root, source, keep_backups)
        return skill_dir
    root.mkdir(parents=True, exist_ok=True)
    (root / "skills").mkdir(parents=True, exist_ok=True)
    command_dir.mkdir(parents=True, exist_ok=True)
    agents_dir.mkdir(parents=True, exist_ok=True)
    if enable_hooks:
        (root / "hooks").mkdir(parents=True, exist_ok=True)

    staging_root = Path(tempfile.mkdtemp(prefix=".ars-grok-stage-", dir=str(root)))
    hold_root: Optional[Path] = None
    moved_targets: list[tuple[Path, Path]] = []
    installed_skill = False
    installed_commands: list[Path] = []
    installed_agents: list[Path] = []
    installed_hooks: list[Path] = []
    try:
        staged_skill = staging_root / "skills" / SKILL_NAME
        staged_commands = staging_root / "commands"
        staged_skill.parent.mkdir(parents=True, exist_ok=True)
        staged_commands.mkdir(parents=True, exist_ok=True)
        staged_agents = staging_root / "agents"
        staged_agents.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, staged_skill, symlinks=True)
        for command_name in EXPECTED_COMMANDS:
            shutil.copy2(
                source / "grok" / "commands" / command_name,
                staged_commands / command_name,
            )
        for agent_name in EXPECTED_AGENTS:
            shutil.copy2(
                source / "grok" / "agents" / agent_name,
                staged_agents / agent_name,
            )

        staged_hooks: Optional[Path] = None
        if enable_hooks:
            staged_hooks = staging_root / "hooks"
            staged_hooks.mkdir(parents=True, exist_ok=True)
            (staged_hooks / HOOK_CONFIG_NAME).write_bytes(
                _render_hook_config(source, skill_dir)
            )

        _, existing_targets = _backup_existing(
            root,
            skill_dir,
            command_dir,
            agents_dir,
            hook_path if enable_hooks else None,
        )
        if existing_targets:
            hold_root, moved_targets = _move_existing_to_hold(root, existing_targets)

        os.replace(staged_skill, skill_dir)
        installed_skill = True
        for command_name in EXPECTED_COMMANDS:
            destination = command_dir / command_name
            os.replace(staged_commands / command_name, destination)
            installed_commands.append(destination)

        for agent_name in EXPECTED_AGENTS:
            destination = agents_dir / agent_name
            os.replace(staged_agents / agent_name, destination)
            installed_agents.append(destination)

        if staged_hooks is not None:
            os.replace(staged_hooks / HOOK_CONFIG_NAME, hook_path)
            installed_hooks.append(hook_path)

        errors = _installed_errors(root, source, hooks_enabled=enable_hooks)
        if errors:
            raise ValidationError("；".join(errors))

        _prune_backups(root, keep_backups)
        if hold_root is not None:
            shutil.rmtree(hold_root, ignore_errors=True)
            hold_root = None
        return skill_dir
    except BaseException:
        for installed_hook in reversed(installed_hooks):
            _remove_entry(installed_hook)
        for installed_agent in reversed(installed_agents):
            _remove_entry(installed_agent)
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
    parser.add_argument(
        "--keep-backups",
        type=_non_negative_int,
        default=3,
        metavar="N",
        help="安装成功后保留最新的 N 个备份，默认保留 3 个",
    )
    hooks_group = parser.add_mutually_exclusive_group()
    hooks_group.add_argument(
        "--enable-hooks",
        action="store_true",
        help="显式安装并启用本地 Grok Hook 配置",
    )
    hooks_group.add_argument(
        "--disable-hooks",
        action="store_true",
        help="只移除本适配器托管的 Grok Hook 配置",
    )
    return parser


def _non_negative_int(value: str) -> int:
    """解析非负整数命令行参数。"""

    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("必须是非负整数") from error
    if parsed < 0:
        raise argparse.ArgumentTypeError("必须是非负整数")
    return parsed


def main(argv: Optional[Sequence[str]] = None) -> int:
    """执行命令行入口并返回进程状态码。"""

    args = _build_parser().parse_args(argv)
    if args.check and (args.enable_hooks or args.disable_hooks):
        print("检查失败：--check 不能与 Hook 启用或禁用参数同时使用。")
        return 1
    if args.disable_hooks:
        try:
            disabled = disable_hooks(target_root=args.target_root)
        except (ValidationError, OSError):
            print("禁用失败：托管 Hook 文件未能安全移除。")
            return 1
        if disabled:
            print("已禁用：仅移除 ARS 托管的 Grok Hook 配置。")
        else:
            print("无需禁用：未发现 ARS 托管的 Grok Hook 配置。")
        return 0
    if args.check:
        return 0 if check(target_root=args.target_root) else 1

    try:
        install_skill(
            target_root=args.target_root,
            keep_backups=args.keep_backups,
            enable_hooks=args.enable_hooks,
        )
    except ValidationError as error:
        print(f"安装失败：{error}")
        return 1
    except (OSError, shutil.Error, ValueError):
        # 不打印异常详情，避免把用户路径或其他敏感信息带到终端。
        print("安装失败：文件操作未完成，已有安装如存在应仍保留在备份目录。")
        return 1

    if args.enable_hooks:
        print("安装成功：技能、16 个命令、三个 Agent 和本地 Hook 均已验证。")
    else:
        print("安装成功：技能、16 个命令和三个 Agent 均已验证；Hook 默认未安装。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
