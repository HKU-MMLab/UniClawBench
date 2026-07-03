#!/usr/bin/env python3
"""Validate task resource references for a public UniClawBench clone."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
import json
from pathlib import Path
import sys

import yaml


LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"


def _as_path_values(value: object) -> Iterable[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict):
                for key in ("path", "file", "dir"):
                    nested = item.get(key)
                    if isinstance(nested, str):
                        out.append(nested)
        return out
    if isinstance(value, dict):
        out: list[str] = []
        for key in ("path", "file", "dir"):
            nested = value.get(key)
            if isinstance(nested, str):
                out.append(nested)
        return out
    return []


def _task_root(root: Path, data: dict[str, object]) -> Path:
    category = data.get("category")
    task_id = data.get("task_id")
    if not isinstance(category, str) or not isinstance(task_id, str):
        raise ValueError("task YAML must contain string category and task_id")
    return root / "injection" / category / task_id


def _resolve_reference(task_root: Path, rel: str, default_subdir: str) -> Path:
    rel_path = Path(rel)
    if rel_path.is_absolute() or ".." in rel_path.parts:
        raise ValueError(f"unsafe resource path: {rel}")
    direct = task_root / rel_path
    if direct.exists():
        return direct
    return task_root / default_subdir / rel_path


def _resource_paths(task_root: Path, data: dict[str, object]) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []

    references = list(_as_path_values(data.get("references")))
    for rel in references:
        out.append(("reference", _resolve_reference(task_root, rel, "references")))

    sources = list(_as_path_values(data.get("sources")))
    if sources:
        for rel in sources:
            out.append(("source", _resolve_reference(task_root, rel, "sources")))
    else:
        source_dir = task_root / "sources"
        if source_dir.exists():
            out.append(("source", source_dir))

    skills = list(_as_path_values(data.get("skills")))
    base_skills = _base_skills(task_root.parents[2])
    for rel in skills:
        if rel in base_skills or rel in {"linux-gui-control", "desktop-control"}:
            continue
        out.append(("skill", _resolve_reference(task_root, rel, "skills")))

    services = data.get("services")
    if isinstance(services, list):
        for service in services:
            if not isinstance(service, dict):
                continue
            rel = service.get("path")
            if isinstance(rel, str):
                out.append(("service", _resolve_reference(task_root, rel, "services")))

    for rel in _as_path_values(data.get("pre_exec")):
        out.append(("pre_exec", _resolve_reference(task_root, rel, "ops")))

    return out


def _base_skills(root: Path) -> set[str]:
    manifest = root / "configs" / "base_skills.json"
    names: set[str] = set()
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except OSError:
        return names
    for key in ("skills", "fallback_skills"):
        values = payload.get(key)
        if isinstance(values, list):
            names.update(str(item).strip() for item in values if str(item).strip())
    return names


def _iter_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
    elif path.is_dir():
        yield from (p for p in path.rglob("*") if p.is_file())


def _is_lfs_pointer(path: Path) -> bool:
    try:
        return path.read_bytes()[: len(LFS_POINTER_PREFIX)] == LFS_POINTER_PREFIX
    except OSError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    task_files = sorted((root / "tasks").glob("*/*.yaml"))
    errors: list[str] = []
    checked_resources = 0
    checked_files = 0

    for task_file in task_files:
        try:
            data = yaml.safe_load(task_file.read_text(encoding="utf-8")) or {}
            if not isinstance(data, dict):
                raise ValueError("task YAML must parse to a mapping")
            task_root = _task_root(root, data)
            if not task_root.exists():
                errors.append(f"{task_file.relative_to(root)}: missing injection root {task_root.relative_to(root)}")
                continue
            resources = _resource_paths(task_root, data)
        except Exception as exc:  # noqa: BLE001 - release check should keep scanning.
            errors.append(f"{task_file.relative_to(root)}: {exc}")
            continue

        for kind, path in resources:
            checked_resources += 1
            if not path.exists():
                errors.append(
                    f"{task_file.relative_to(root)}: missing {kind} {path.relative_to(root)}"
                )
                continue
            for file_path in _iter_files(path):
                checked_files += 1
                if _is_lfs_pointer(file_path):
                    errors.append(
                        f"{task_file.relative_to(root)}: unresolved LFS pointer {file_path.relative_to(root)}"
                    )

    print(f"asset-check root={root}")
    print(f"tasks={len(task_files)} resources={checked_resources} files={checked_files}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print("Hint: run `git lfs pull` after cloning, then retry this check.")
        return 1
    print("OK: all task resource references exist and are materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
