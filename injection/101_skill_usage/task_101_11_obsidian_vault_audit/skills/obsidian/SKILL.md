---
name: obsidian
description: Work with Obsidian vaults as plain Markdown folders for offline note graph audits.
homepage: https://help.obsidian.md
metadata: {"clawdbot":{"emoji":"💎"}}
---

# Obsidian

Obsidian vault = a normal folder on disk.

Vault structure (typical)
- Notes: `*.md` (plain text Markdown; edit with any editor)
- Config: `.obsidian/` (workspace + plugin settings; usually don’t touch from scripts)
- Canvases: `*.canvas` (JSON)
- Attachments: whatever folder you chose in Obsidian settings (images/PDFs/etc.)

## Offline vault audit

When the user gives a vault path, treat it as the source of truth. Read the
Markdown files directly; do not install or launch Obsidian desktop tooling.

Useful checks:
- Enumerate notes with `find <vault> -name '*.md'`.
- Extract wikilinks with a regex for `[[target]]` and compare them against
  note paths / stems.
- Check Markdown links like `[text](relative/path.md)` against files on disk.
- Build a small graph from note -> linked note to find orphan notes, broken
  links, stale references, overused tags, and tag spelling drift.
- Preserve vault-relative paths in reports so the user can act on them.

## Wikilink resolution semantics (Obsidian-specific)

Vanilla Obsidian resolves `[[target]]` with these rules in order:
1. **Case-insensitive**: `[[Projects/Alpha]]` resolves to `projects/alpha.md` if it exists.
2. **Relative `../`**: `[[../daily-2026-04-01]]` resolves against the note's parent directory (i.e. flattens the `..` against the link source's location).
3. **Shortest-path / stem-only**: bare `[[stem]]` matches any note with that filename stem anywhere in the vault.

When auditing for broken links, apply ALL three rules before deciding a link is broken. A link that only differs in case, or uses `../`, may still resolve cleanly.
