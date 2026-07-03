# Hidden Evaluation Rule — task_205_25_drawio_contributing_flow

## 1. Grading Philosophy

Grade on whether the executor delivered a credible "how to contribute"
diagram for the GitHub CLI repo (cli/cli) anchored to the project's
real `.github/CONTRIBUTING.md` at tag **v2.65.0** (commit
`b3be16e98e1413f5bb0943c06402516cec3fd3b4`). The platform-specific
challenge is fetching real text from GitHub via `gh api`, extracting
≥5 literal step substrings, and producing a structurally valid
mxGraph `.drawio` file (using the `cli-anything-drawio` CLI from
HKUDS/CLI-Anything OR by writing the XML directly). A rendered
PNG/SVG is preferred but not strictly required: a valid `.drawio` is
the irreducible deliverable.

Be lenient on:

- Field names in `flow_steps.json` (semantic equivalents accepted —
  see §2)
- Diagram visual style (any mxGraph-valid layout / palette)
- Image format (.png OR .svg OR .jpg OR .pdf)
- Whether the executor used the drawio CLI vs hand-wrote XML — the
  XML structure is what matters
- Step actor labels (any one of contributor / maintainer / reviewer /
  CI / bot, in any language case)

Be strict on:

- Anchored repo + tag/SHA in the JSON `source` field
- Each step's `action` text MUST literally contain one of the 5
  anchored substrings from the real CONTRIBUTING.md (verified at
  reference time — see §4)
- `.drawio` parses as XML rooted at `<mxfile>`
- Shape/edge counts ≥5 each in the .drawio file
- Diagram and JSON cross-reference: ≥3 step actions appear in some
  mxCell `value` attribute

## 2. Task Contract

Required deliverables:

- `/tmp_workspace/results/flow_steps.json` — JSON with a `source`
  object (any of: `repo`/`source`/`anchor` containing the literal
  string `cli/cli` plus a commit SHA or tag matching the pin) and a
  top-level steps array (any of: `steps`/`flow`/`entries`/bare
  top-level array). Each step object contains the SEMANTIC equivalents
  of: `order`/`index`/`seq`/`step` (1-based int OR position in array
  is acceptable), `actor`/`role`/`who` (string mentioning one of
  contributor / maintainer / reviewer / CI / bot — case-insensitive,
  any language wrapper OK), `action`/`step_text`/`description` (string
  containing at least one of the 5 anchored substrings from §4).
- `/tmp_workspace/results/contributing_flow.drawio` — XML file. The
  supervisor parses with `xml.etree.ElementTree`; root tag MUST be
  `mxfile`. Inside, count `<mxCell>` elements with attribute
  `vertex="1"` (shapes) and `<mxCell>` elements with attribute
  `edge="1"` (connectors).
- ONE OF: `/tmp_workspace/results/contributing_flow.png` |
  `.svg` | `.jpg` | `.pdf` — rendered diagram, non-zero size.
  If absent, the rendering checkpoint scores zero but the rest of the
  rubric still applies (no hard fail).
- `/tmp_workspace/results/contributing_summary.md` — Chinese markdown
  onboarding summary.

## 3. Source-Selection Rules

Canonical source is the LIVE GitHub API at the pinned tag:

```
gh api 'repos/cli/cli/contents/.github/CONTRIBUTING.md?ref=v2.65.0'
```

The `.content` field is base64; executor must decode it. NO snapshot
file. NO mock. `GITHUB_TOKEN` is set in the executor's environment.

Equivalent calls accepted:
- `gh api 'repos/cli/cli/contents/.github/CONTRIBUTING.md?ref=b3be16e98e1413f5bb0943c06402516cec3fd3b4'`
- `curl -H "Authorization: Bearer $GITHUB_TOKEN" https://raw.githubusercontent.com/cli/cli/v2.65.0/.github/CONTRIBUTING.md`

## 4. Ground-Truth Snapshot

Structured expected answer at `references/ground_truth.json`. Key
anchors:

- `pinned_tag = "v2.65.0"`,
  `pinned_commit_sha = "b3be16e98e1413f5bb0943c06402516cec3fd3b4"`
- The 5 expected step anchor substrings (each verified to appear
  literally, case-sensitive, in the file at this tag):
  1. `Check issues to verify that a`
  2. `Open an issue to propose a significant change`
  3. `Create a new branch:`
  4. `Submit a pull request:`
  5. `Make your change, add tests, and ensure tests pass`

Threshold: at least 4 of these 5 substrings must appear (in any
order, in any subset of the executor's `action` fields) for the
anchor checkpoint to pass.

## 5. Checkpoint Rubric

Weights sum to 1.0. Six checkpoints.

- **0.15** — `flow_steps.json` parses; `source` (any acceptable key)
  contains the literal `cli/cli` AND either the literal tag
  `v2.65.0` OR the literal SHA `b3be16e98e1413f5bb0943c06402516cec3fd3b4`
  (full SHA OR a ≥7-char unambiguous prefix). The steps array (under
  any acceptable key — `steps`/`flow`/`entries`/bare top-level array)
  has length ≥5.
- **0.20** — Anchor coverage: at least 4 of the 5 expected step
  anchor substrings (§4) appear as a substring of some step's
  `action`/`step_text`/`description` field. Substring match is
  case-sensitive against the original CONTRIBUTING text. Half credit
  (0.10) if exactly 3 of 5 match; 0 if ≤2.
- **0.20** — `.drawio` exists; `xml.etree.ElementTree.parse` succeeds;
  root tag is `mxfile`; the file contains ≥5 `<mxCell>` elements with
  attribute `vertex="1"` (shapes excluding the always-present
  id="0"/id="1" system cells, which lack `vertex="1"`).
- **0.15** — `.drawio` contains ≥5 `<mxCell>` elements with attribute
  `edge="1"` (connectors).
- **0.15** — Cross-reference: at least 3 of the 5 expected step
  anchor substrings (§4) appear as a substring of some `<mxCell>`
  `value` attribute in the .drawio. Half credit (0.075) if exactly 2.
  AND at least 3 distinct `<mxCell>` shapes carry an actor keyword
  (contributor / maintainer / reviewer / CI / bot — case-insensitive)
  in either the `value` attribute OR the `style` attribute (e.g.
  `shape=mxgraph.basic.person`). Half credit (0.075) if only 2.
- **0.15** — Rendering / summary present. Award 0.07 if any of
  `contributing_flow.{png,svg,jpg,pdf}` exists with non-zero size.
  Award 0.08 if `contributing_summary.md` exists, contains the
  literal `cli/cli`, contains either `v2.65.0` OR the SHA prefix
  `b3be16e9`, contains a markdown image link
  (`![...](contributing_flow.{png|svg|jpg|pdf})`), and includes a
  Chinese narrative ≥150 characters mentioning at least 2 of the
  actor keywords.

## 6. Scoring Policy / Score Caps

Partial credit from satisfied checkpoints. Caps:

- `flow_steps.json` missing OR not parseable → 0.30.
- `contributing_flow.drawio` missing OR root tag not `mxfile` → 0.40.
- Output fabricates step text NOT derivable from the live
  CONTRIBUTING.md (zero of the 5 anchor substrings match) → 0.30.
- `$GITHUB_TOKEN` value emitted to user-visible output → 0.30.
- Trace shows zero gh / curl calls to api.github.com or
  raw.githubusercontent.com (synthetic data only) → 0.40.
- `contributing_summary.md` missing → cap 0.85 (rendering checkpoint
  partial-credit cap).

Pass requires: source/structure checkpoint, anchor-coverage checkpoint,
shape-count checkpoint, edge-count checkpoint, AND cross-reference
checkpoint all satisfied (at least partial credit).

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90.
- **Continue** 0.50–0.89.
- **Fail** < 0.50.

## 8. Hidden Reference Assets

Supervisor-only:
- `references/eval_rule.md` (this file)
- `references/ground_truth.json`

## 9. Dynamic Content Note

The lightweight tag `v2.65.0` on cli/cli points permanently to commit
`b3be16e98e1413f5bb0943c06402516cec3fd3b4`. The contents of
`.github/CONTRIBUTING.md` at that commit are immutable. The 5 anchor
substrings have been verified at task-design time. If the GitHub API
or the cli-anything-drawio package install temporarily fails, the
supervisor MUST distinguish "executor failed" from "infra outage".
A trace showing repeated 5xx responses from api.github.com or a
broken `pip install -e .` because of network failure is an infra
issue — record `infra_error` in summary and avoid penalising.
