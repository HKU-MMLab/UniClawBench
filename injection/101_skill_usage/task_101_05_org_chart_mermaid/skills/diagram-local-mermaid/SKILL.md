---
name: diagram-local-mermaid
description: Create Mermaid diagrams and simple local SVG renderings from structured source material without requiring an external MCP server.
metadata:
  clawdbot:
    emoji: "🧭"
    requires:
      bins:
        - python3
---

# Local Mermaid Diagram Skill

Use this skill when the user asks for a Mermaid diagram plus a rendered image
or SVG. Work from the provided source files and keep the diagram auditable.

## Workflow

1. Extract the entities and relationships into a small table before writing
   the diagram.
2. Save Mermaid source as requested, using `graph TD` or `flowchart TD` when
   the user asks for a hierarchy.
3. Use subgraphs for groups such as teams, committees, systems, or phases.
4. Use edge styles consistently. For example, solid arrows for primary
   relationships and dotted arrows for secondary memberships.
5. If a Mermaid renderer is available, render the Mermaid directly. If not,
   create a standalone SVG locally with Python or another available tool that
   preserves the same nodes, labels, groups, and edge meanings.
6. Keep a source matrix when the user asks for auditability: source entity,
   relationship type, target, role, and source quote.

Do not install or configure an MCP server during the task.
