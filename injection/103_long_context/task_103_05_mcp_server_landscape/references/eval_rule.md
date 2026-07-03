# Hidden Evaluation Rule — task_103_05_mcp_server_landscape

Use this file as the primary hidden judging spec. Prefer outcome-oriented checkpoints.

## 1. Grading Philosophy

The supervisor should judge whether the executor performed real enumeration research and produced a verified inventory of genuine MCP (Model Context Protocol) servers, with correct exclusion of look-alikes (awesome-lists, clients, inspectors). Because this is live research over a fast-changing ecosystem, judge methodology, correct identification, verification quality, and enumeration discipline — not exact star counts.

## 2. Task Contract

The public task asks the executor to research and enumerate at least 12 real MCP servers, recording for each: repo/link, purpose, language, popularity signal, official-vs-community, and transport where determinable; to exclude or clearly flag non-servers (awesome-lists, client libraries, inspectors); and to save the inventory to `/tmp_workspace/results/mcp_server_landscape.md`.

## 3. Source-Selection and Target-Resolution Rules

An MCP server exposes tools/resources/prompts to MCP clients over the protocol (stdio or HTTP/SSE). Awesome-lists (e.g. `awesome-mcp-servers`), client libraries (e.g. `mcp-use`), and inspector/debug tools (e.g. `modelcontextprotocol/inspector`) are NOT servers and must not be counted as such. The official `modelcontextprotocol/servers` reference collection is a primary anchor and should appear. Verification means actually checking what each repo is (reading its README/description), not just pattern-matching the name "mcp".

## 4. Ground-Truth Snapshot

Hidden ground truth (`ground_truth.json`) lists real server anchors (e.g. `microsoft/playwright-mcp`, `github/github-mcp-server`, `googleapis/mcp-toolbox`, `GLips/Figma-Context-MCP`, `awslabs/mcp`, the official `modelcontextprotocol/servers`) and distractors to exclude (`punkpeye/awesome-mcp-servers`, `modelcontextprotocol/inspector`, `mcp-use/mcp-use`). Star counts are a 2026-06-20 snapshot and need not match exactly.

## 5. Checkpoint Rubric

- 0.30 Enumeration: lists at least 12 genuine MCP servers with real, resolvable repos/links.
- 0.25 Verification: for each server, records what it actually does and the requested fields (language, popularity, official/community, transport where determinable), based on reading the repo — not name-guessing.
- 0.20 Enumeration discipline: awesome-lists, client libraries, and inspectors are excluded or clearly flagged as not-a-server; reward finding the official `modelcontextprotocol/servers` collection.
- 0.15 No fabrication: repos/links are real and the descriptions match the actual projects (no invented servers, no wrong descriptions).
- 0.10 Deliverable: `mcp_server_landscape.md` saved at the requested path, organized and readable.

## 6. Scoring Policy / Score Caps

The task passes only at score >= 0.90. Award partial credit from satisfied checkpoints but do not mark pass below 0.90.

If fewer than 12 genuine servers are identified, cap at 0.70. If awesome-lists or clients are counted as servers without flagging, cap at 0.70. If the list contains fabricated repos or descriptions that do not match the real projects, cap at 0.55. If `mcp_server_landscape.md` is missing, cap at 0.40. If entries are unverified name-matches with no description of function, cap at 0.65.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor has a partial list or unverified entries. Prefer `fail` when the inventory is mostly fabricated, miscategorizes look-alikes as servers throughout, or produces no output file.

## 8. Hidden Reference Assets

- `ground_truth.json`: definition, real-server anchors, distractors, expected fields, scoring notes.

## 9. Dynamic Content Note

GitHub stars and the MCP ecosystem change continuously. Judge live findings on correctness, verification, and enumeration discipline, not on matching the snapshot exactly.
