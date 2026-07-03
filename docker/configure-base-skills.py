#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from pathlib import Path


MANIFEST = Path(__file__).resolve().parents[1] / "configs" / "base_skills.json"


def keep_skills() -> list[str]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return [str(item).strip() for item in (payload.get("skills") or []) if str(item).strip()]


def copy_base_skills() -> None:
    src_root = Path("/opt/clawbench/base_skills")
    dst_root = Path("/root/skills")
    dst_root.mkdir(parents=True, exist_ok=True)
    keep = set(keep_skills())
    for child in list(dst_root.iterdir()):
        if child.name in keep:
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()
    for name in keep_skills():
        src = src_root / name
        if not src.exists():
            continue
        dst = dst_root / name
        if dst.exists():
            if dst.is_dir() and not dst.is_symlink():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        shutil.copytree(src, dst)


def remove_agent_browser_embedded_skills() -> None:
    candidate_roots = (
        Path("/usr/local/lib/node_modules/agent-browser/skills"),
        Path("/usr/local/lib/nodejs/node-v22.22.1-linux-x64/lib/node_modules/agent-browser/skills"),
    )
    for root in candidate_roots:
        if not root.exists():
            continue
        for child in root.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()


def main() -> None:
    copy_base_skills()
    remove_agent_browser_embedded_skills()


if __name__ == "__main__":
    main()
