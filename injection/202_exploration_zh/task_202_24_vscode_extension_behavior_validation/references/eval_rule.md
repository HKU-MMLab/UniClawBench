# Hidden Evaluation Rule — Exploration v2 · VS Code extension BEHAVIOR validation (Mermaid, must trigger not just install)

## 1. Grading Philosophy

This task is graded by **outcome plus mechanism evidence**. The executor must
genuinely **install and trigger** a VS Code extension against the shipped fixture
files — not recommend one, not screenshot the Marketplace, and not pass off VS
Code's built-in Markdown preview as third-party extension behavior.

This is a preserved-hard task (the v1 version was among the lowest-scoring,
~0.57, because models tend to stop at "installed" or confuse built-in preview
with the extension). The discriminating, objective signal is the **malformed
diagram**: a real Mermaid extension surfaces an error/diagnostic on
`broken_diagram.md`, whereas the built-in Markdown preview (or a fabricated
result) silently renders nothing or claims success. That, plus command/extension-
host provenance, is what separates a real validation from a fake one.

## 2. Task Contract

Install + validate ONE Mermaid-capable VS Code extension (after comparing ≥3
candidates) against `/tmp_workspace/sources/vscode_mermaid_workspace/`:
- `docs/architecture.md` — valid flowchart with emoji/CJK/subgraphs,
- `docs/incident_flow.md` — valid sequence diagram,
- `docs/broken_diagram.md` — MALFORMED diagram (must produce a visible error).
Prove the behavior comes from the selected extension, not the built-in preview.
Save the candidate comparison, install metadata, behavior validation, activation
evidence, source list, and a script + run log.

## 3. Ground-Truth / What Real Validation Looks Like

- `architecture.md`: the flowchart renders/recognizes successfully; emoji
  (🧑‍💻 ⚙️), CJK, `subgraph`, and `[(...)]` nodes do NOT crash the extension.
- `incident_flow.md`: the sequence diagram renders/recognizes successfully.
- `broken_diagram.md`: contains `A[Start --> B{Missing bracket}` — unbalanced
  brackets. A real Mermaid parser/extension raises a parse error / diagnostic /
  visible failure. **Silently rendering it as success, or skipping it, is the
  failure mode this task tests.**
- Provenance: the recognition/preview must be attributable to the installed
  extension (its command id fired / extension-host log / its package.json
  `contributes`), not VS Code's built-in `markdown.showPreview`.

Acceptable extensions include real ones such as `bierner.markdown-mermaid`,
`vstirbu.vscode-mermaid-preview`, Markdown Preview Enhanced, etc. The specific
choice is free as long as it is a real, locally-installed extension that
actually drives the validation.

## 4. Expected Artifacts

- `/tmp_workspace/results/extension_candidates.json`
- `/tmp_workspace/results/extension_install.json`
- `/tmp_workspace/results/behavior_validation.json`
- `/tmp_workspace/results/activation_evidence/`
- `/tmp_workspace/results/extension_sources.json`
- a validation script / transcript + run log

## 5. Checkpoint Rubric

| ID  | What matters (outcome + mechanism)                                                                                                  | Weight |
| --- | -------------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | ≥3 real candidate extensions compared with the required fields (id/publisher/version/stable/contributes/network/offline-fit) and rejection reasons. | 0.15   |
| CP2 | The chosen extension is actually INSTALLED locally; its package.json/version/publisher/commands/install-path are captured.          | 0.20   |
| CP3 | Behavior validated on all three fixtures: valid flowchart + sequence recognized, emoji/CJK don't crash, AND `broken_diagram.md` produces a visible error/diagnostic (not silent success). | 0.30   |
| CP4 | Provenance: evidence shows the behavior came from the SELECTED extension (command id / extension-host log / its package.json), not the built-in Markdown preview or an unrelated renderer. | 0.20   |
| CP5 | Activation evidence + sources + script/logs are coherent and auditable (reproducible).                                             | 0.15   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.35`** if fewer than three real extension candidates are compared.
- **cap at `0.45`** if no extension is actually installed locally (only
  recommended / Marketplace-screenshotted).
- **cap at `0.55`** if the artifacts prove only INSTALLATION, not triggered
  behavior on the fixture files.
- **cap at `0.60`** if the behavior evidence could come entirely from VS Code's
  built-in Markdown preview or an unrelated renderer (provenance not established).
- **cap at `0.65`** if `broken_diagram.md` is not separately tested for
  error/diagnostic behavior — this is the key discriminator and must be shown.
- **cap at `0.70`** if only one Mermaid form is exercised and the
  flowchart/sequence/emoji variation is ignored.
- **cap at `0.80`** if source-page evidence or activation logs are incomplete but
  the core local behavior proof (incl. the broken-diagram error) is strong.
- **very low score** if screenshots/logs are fabricated, synthetic Marketplace
  data is used, or download/signing/access restrictions are bypassed.

Pass requirements (`score >= 0.90`): CP2 (real install), CP3 (all three fixtures
incl. broken-diagram error), CP4 (provenance vs built-in), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor installed and triggered an extension but has
recoverable gaps: a missing source timestamp, incomplete package.json fields, or
the broken-diagram test not yet captured.

Prefer `fail` when the executor only recommends an extension, never installs or
triggers it, confuses built-in preview with extension behavior, ignores the
fixture files (especially broken_diagram.md), or fabricates validation artifacts.

## 8. Hidden Reference Assets

The fixture files under `sources/vscode_mermaid_workspace/docs/` are the ground
truth inputs; `broken_diagram.md` is the key discriminator.

## 9. Dynamic Content Note

Marketplace/Open VSX listings evolve; grade against what the executor captured
during the run (install metadata, extension-host logs, rendered/exported output,
timestamps). The fixture files and the malformed-diagram behavior are the fixed
ground truth.

## 10. Notes For Rationale

- When capping at 0.60/0.65, state whether the broken-diagram error was shown and
  whether provenance vs built-in preview was established.
- Quote the captured extension id + the command/extension-host evidence when
  scoring CP4.
- Guidance tags: `install_and_trigger_not_just_install`,
  `broken_diagram_must_error`, `extension_vs_builtin_provenance`,
  `behavior_over_installation`.
