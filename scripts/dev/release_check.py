#!/usr/bin/env python3
"""Release hygiene checks for a public UniClawBench source drop.

By default this script checks files that would enter a git archive
(`git ls-files`).  Use --strict-working-tree when auditing an ad-hoc copied
directory before publishing; that mode also fails if ignored local-only
directories such as .claude/ or runs/ are present.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path


FORBIDDEN_RELEASE_PATTERNS = (
    ".claude",
    ".claude/*",
    "AGENTS.md",
    "runs",
    "runs/*",
    "logs",
    "logs/*",
    "static-site",
    "static-site/*",
    "scripts/orchestra/runtime/*",
    "configs/*.local.*",
    ".env",
    ".env.*",
)

ALLOWED_RELEASE_PATHS = {
    "scripts/orchestra/runtime/.gitkeep",
}

SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "downloads",
    "node_modules",
    "runs",
    "static-site",
}

BINARY_SUFFIXES = {
    ".7z",
    ".avi",
    ".db",
    ".doc",
    ".docx",
    ".gif",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".m4a",
    ".mov",
    ".mp3",
    ".mp4",
    ".ods",
    ".odt",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".sqlite",
    ".tar",
    ".tgz",
    ".webm",
    ".webp",
    ".xlsx",
    ".zip",
}

TEXT_MAX_BYTES = 2_000_000

PRIVATE_TEXT_PATTERNS = (
    re.compile(r"/Users/azily\b"),
    re.compile(r"/Volumes/Attach\b"),
    re.compile(r"\b100\.116\.9\.115\b"),
    re.compile(r"\b172\.22\.\d{1,3}\.\d{1,3}\b"),
    re.compile(r"\broot@[A-Za-z0-9_.-]+"),
    re.compile(r"/root/clawbench(?:_[A-Za-z0-9_.-]+)?\b"),
)

SECRET_VALUE_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:api[_-]?key|token|secret)\s*[:=]\s*['\"][A-Za-z0-9_./+=-]{24,}['\"]", re.IGNORECASE),
)

FIXTURE_PREFIXES = (
    "injection/",
    "tests/",
)

SANITIZER_IMPLEMENTATION_FILES = {
    "scripts/dev/release_check.py",
    "webui/server.py",
}


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    return any(path == pattern or fnmatch.fnmatch(path, pattern) for pattern in patterns)


def _git_files(root: Path) -> list[Path] | None:
    try:
        raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
    except (OSError, subprocess.CalledProcessError):
        return None
    return [root / item.decode("utf-8", "surrogateescape") for item in raw.split(b"\0") if item]


def _walk_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        dirnames[:] = [
            name for name in dirnames
            if name not in SKIP_DIRS and not _matches_any((rel_dir / name).as_posix(), FORBIDDEN_RELEASE_PATTERNS)
        ]
        for filename in filenames:
            out.append(Path(dirpath) / filename)
    return out


def _looks_binary(path: Path) -> bool:
    if path.suffix.lower() in BINARY_SUFFIXES:
        return True
    try:
        sample = path.read_bytes()[:4096]
    except OSError:
        return True
    return b"\0" in sample


def _scan_text(path: Path, rel: str) -> list[str]:
    try:
        if path.stat().st_size > TEXT_MAX_BYTES or _looks_binary(path):
            return []
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    if rel.startswith(FIXTURE_PREFIXES):
        return []
    hits: list[str] = []
    patterns = list(PRIVATE_TEXT_PATTERNS)
    patterns.extend(SECRET_VALUE_PATTERNS)
    if rel in SANITIZER_IMPLEMENTATION_FILES:
        private_patterns = {p.pattern for p in PRIVATE_TEXT_PATTERNS}
        patterns = [p for p in patterns if p.pattern not in private_patterns]
    for pattern in patterns:
        if pattern.search(text):
            hits.append(pattern.pattern)
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository or release tree root")
    parser.add_argument(
        "--strict-working-tree",
        action="store_true",
        help="fail if forbidden local-only paths exist anywhere under root",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    files = _git_files(root)
    source = "git-tracked"
    if files is None:
        files = _walk_files(root)
        source = "filesystem"

    errors: list[str] = []
    warnings: list[str] = []

    for path in files:
        rel = _rel(path, root)
        if rel not in ALLOWED_RELEASE_PATHS and _matches_any(rel, FORBIDDEN_RELEASE_PATTERNS):
            errors.append(f"forbidden release path is tracked: {rel}")
            continue
        hits = _scan_text(path, rel)
        if hits:
            errors.append(f"private-looking text in {rel}: {', '.join(hits)}")

    if args.strict_working_tree:
        for pattern in FORBIDDEN_RELEASE_PATTERNS:
            for path in root.glob(pattern):
                rel = _rel(path, root)
                if path.exists() and rel not in ALLOWED_RELEASE_PATHS:
                    errors.append(f"forbidden local path present: {rel}")
    else:
        for pattern in (".claude", "AGENTS.md", "runs", "configs/*.local.*", ".env", ".env.*"):
            if any(root.glob(pattern)):
                warnings.append(f"local-only path exists but is not checked in default mode: {pattern}")

    demo_media = sorted((root / "assets" / "demo").glob("**/*"))
    demo_media = [p for p in demo_media if p.suffix.lower() in {".mp4", ".jpg", ".jpeg", ".png", ".webp"}]
    if demo_media:
        warnings.append(f"manual visual review required for {len(demo_media)} demo media files under assets/demo/")

    print(f"release-check source={source} root={root}")
    for warning in warnings:
        print(f"WARN: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: no blocking release hygiene issues found in checked files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
