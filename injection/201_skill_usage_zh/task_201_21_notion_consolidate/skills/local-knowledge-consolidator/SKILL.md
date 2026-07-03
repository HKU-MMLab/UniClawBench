---
name: local-knowledge-consolidator
description: Organize project notes into durable decisions, actions, risks, references, and open questions.
metadata:
  clawdbot:
    emoji: "🧠"
---

# Local Knowledge Consolidation Skill

Use this skill to turn a page tree or exported notes into a structured knowledge base. Work from the available notes and exported page data; do not request additional credentials.

## Consolidation Pattern

1. Read every source page or snapshot entry.
2. Normalize facts into meetings, decisions, actions, open questions, risks/dependencies, and references.
3. Preserve source page ids next to every decision, action, risk, and question.
4. Keep unresolved items separate from decided/closed items.
5. Emit tracker files as tables/CSV when requested.

Prefer exact source ids and short excerpts over vague summaries.
