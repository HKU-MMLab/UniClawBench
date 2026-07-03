# Hidden Evaluation Rule — Exploration v2 · API docs framework selection (builtin vs plugin, conflicting requirements)

## 1. Grading Philosophy

This is a **candidate-selection** task graded by **objective capability-coverage
matching plus the correct optimal pick**.

The pool is six real documentation frameworks shipped offline, each with
capability flags (`builtin` / `plugin` / `no`) normalized from official docs.
The use case needs FIVE capabilities; the obvious "API docs" tool (Redoc) is a
trap because it is an OpenAPI renderer, not a full docs site; the trendiest
options (VitePress, Starlight) lack versioning; the classic option (Sphinx/RTD)
lacks dark mode. Only **docusaurus** and **mkdocs_material** cover all five, and
the tie-break is the structurally hardest requirement: **versioning built in**.

Offline + frozen → deterministic answer key (`ground_truth.json`).

## 2. Task Contract

Pick one framework for a public REST API docs site needing: code blocks, dark
mode, search, doc versioning (v1/v2), and OpenAPI rendering. Capability counts
as satisfied if builtin OR plugin; `no` = fails. Tie-break favors builtin
versioning. Pool at `/tmp_workspace/clawbench/sources/candidates.json`. Save
`framework_choice.json`, `framework_evaluation.json`, `framework_method.json`.
Offline.

## 3. Ground-Truth Reference (answer key)

| framework | code | dark | search | versioning | openapi | hard pass | fails |
| --------- | ---- | ---- | ------ | ---------- | ------- | --------- | ----- |
| **docusaurus** | builtin | builtin | plugin | **builtin** | plugin | **PASS** | — |
| **mkdocs_material** | builtin | builtin | builtin | plugin(mike) | plugin | **PASS** | — |
| redoc | no | plugin | builtin | no | builtin | FAIL | code_blocks + versioning |
| vitepress | builtin | builtin | builtin | **no** | plugin | FAIL | versioning |
| starlight | builtin | builtin | builtin | **no** | plugin | FAIL | versioning |
| sphinx_rtd | builtin | **no** | builtin | builtin | plugin | FAIL | dark_mode |

- **Survivors: docusaurus, mkdocs_material.**
- **Optimal: `docusaurus`** — versioning is built in (vs MkDocs needing external
  `mike`), and versioning is the hardest requirement to retrofit.
- **mkdocs_material** acceptable second-best with explicit tradeoff (cap ~0.85).

Note: embedding Redoc *inside* the chosen docs site (for the OpenAPI reference)
is fine and even sensible — but Redoc *alone* is not a valid answer.

## 4. Expected Artifacts

- `/tmp_workspace/results/framework_choice.json`
- `/tmp_workspace/results/framework_evaluation.json`
- `/tmp_workspace/results/framework_method.json`

## 5. Checkpoint Rubric

| ID  | What matters (objective)                                                                                                                | Weight |
| --- | ------------------------------------------------------------------------------------------------------------------------------------ | ------ |
| CP1 | Final pick is **docusaurus** (optimal), justified by full coverage + versioning builtin. (mkdocs with correct tradeoff → partial.)      | 0.30   |
| CP2 | Hard-pass survivor set correctly identified as **{docusaurus, mkdocs_material}**; no failing framework wrongly included.                 | 0.20   |
| CP3 | The OBVIOUS trap is caught: Redoc rejected as a standalone answer because it lacks guide code-blocks + versioning (not a full docs site).| 0.20   |
| CP4 | The versioning traps are caught: vitepress/starlight rejected for missing first-party versioning; sphinx for missing dark mode.          | 0.15   |
| CP5 | Coverage is evidence-based (builtin/plugin/no per capability cited), and the tie-break reasoning names versioning as the discriminator.  | 0.15   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.45`** if the pick is justified without per-capability coverage
  analysis (e.g. just "it's popular" / "it does OpenAPI").
- **cap at `0.55`** if `framework_choice.json` or `framework_evaluation.json`
  missing.
- **cap at `0.60`** if a framework missing a hard requirement is the final
  standalone pick (redoc, vitepress, starlight, sphinx_rtd).
- **cap at `0.70`** if Redoc is picked as the standalone answer (the central
  obvious-choice trap) — even though it renders OpenAPI, it is not a docs site.
- **cap at `0.85`** if the pick is **mkdocs_material** with a correct tradeoff
  acknowledging its versioning is plugin/external; without acknowledging
  docusaurus's builtin-versioning advantage, cap `0.70`.
- **cap at `0.75`** if the survivor set is wrong even if the single pick is
  docusaurus.
- **cap at `0.30`** if the executor used the network (offline task).

Do **not** cap or fail merely because:

- the executor proposes embedding Redoc/Swagger-UI inside Docusaurus for the
  OpenAPI reference (that's the correct way to satisfy the OpenAPI requirement),
- the executor counts a plugin-backed capability as satisfied (the rules allow
  builtin OR plugin),
- the executor notes extra differences (build speed, ecosystem) as long as the
  hard coverage analysis is correct.

Pass requirements (`score >= 0.90`): CP1 (docusaurus), CP2 (survivors), CP3
(Redoc trap), CP4 (versioning/dark traps), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor has built partial coverage but hasn't
finalized the pick or the tie-break, or rejected Redoc but not yet justified the
survivor tie-break.

Prefer `fail` when, after follow-ups, the standalone pick is a non-covering
framework, or the choice was made with no capability analysis.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — capability coverage + optimal pick.

## 9. Dynamic Content Note

None — frozen offline pool; deterministic. (Frameworks evolve upstream, but the
shipped capability flags are the ground truth for this task.)

## 10. Notes For Rationale

- When scoring CP3, quote the executor's reason for rejecting Redoc as a
  standalone answer (must cite missing guide code-blocks / versioning).
- When scoring CP1, confirm the tie-break names versioning-builtin as the
  decider over mkdocs_material.
- Guidance tags: `capability_coverage_selection`, `obvious_tool_is_a_trap`,
  `builtin_vs_plugin`, `versioning_is_the_discriminator`, `offline_deterministic`.
