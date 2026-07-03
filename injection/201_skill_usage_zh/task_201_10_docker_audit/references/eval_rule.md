# Hidden Evaluation Rule — task_201_10_docker_audit

## 1. Grading Philosophy

Judge the executor on whether the public request was actually completed and
whether the declared skills under `/root/skills/` were genuinely used. Prefer
semantic matching over exact-string matching when the user's request would not
pin down a specific phrasing. Score caps in §6 override rubric totals when
they apply.

## 2. Task Contract

The user has a small deployment bundle in `/tmp_workspace/clawbench/sources/`:
`Dockerfile`, `requirements.txt`, `server.py`, plus a local advisory feed
`vuln_advisories.json`. The executor must produce three deliverables:

1. `/tmp_workspace/results/audit.md` — a security audit that surfaces the
   most-dangerous risk items in this bundle. Each risk must be presented in
   a way that a reviewer can locate it in the source files (file plus the
   relevant code/line) and understand why it is dangerous and how to fix
   it. The user's prompt does not pin a specific finding format; judge the
   substance, not a fixed heading template.
2. `/tmp_workspace/results/Dockerfile.fixed` — a safer Dockerfile draft.
3. `/tmp_workspace/results/requirements.fixed.txt` — pinned direct
   dependencies that resolve advisory-feed exposures.

The public prompt is authoritative for what counts as in-scope.

## 3. Source-Selection and Target-Resolution Rules

Canonical inputs live under `/tmp_workspace/clawbench/sources/`:

- `Dockerfile`
- `requirements.txt`
- `server.py`
- `vuln_advisories.json` (local advisory feed; the audit's CVE evidence must
  come from this file rather than from model memory)

Anything not listed above is outside the audit's scope. When an advisory in
the feed names a package not present in `requirements.txt`, or describes a
platform/configuration that does not match this bundle, the auditor is
expected to cross-reference against the actual files before listing the CVE
as a finding.

## 4. Ground-Truth Snapshot

Structured expected answer lives at `references/ground_truth.json`
(schema `a`: concept-level critical-risk findings plus CVE crosswalk
checks). Key anchors:

- `must_hit_critical_risks` — exactly 5 concrete most-dangerous risk items
  the audit must surface:
  1. plaintext API_KEY baked into Dockerfile ENV,
  2. `pickle.loads` on attacker-controlled `request.data` in `server.py`,
  3. Flask `debug=True` with `host='0.0.0.0'` (Werkzeug debugger RCE),
  4. container runs as root on `python:latest` with no `USER` directive,
  5. `requests==2.20.0` matching CVE-2018-18074 in the advisory feed.
- `must_hit_match_policy` — strict 5-of-5; each risk is matched
  case-insensitively against the audit's titles + evidence/body via
  per-risk `match_keywords_any`. No partial credit.
- `required_cve_crosswalk` — four packages (flask, requests, pyyaml,
  jinja2) with current requirement, CVE/GHSA, and fixed version.
- `docker_remediation_anchors` — five remediation patterns (pinned base,
  COPY ordering, `--no-cache-dir`, non-root USER, runtime secret
  management).
- `fixed_artifacts` — required substrings / forbidden substrings for
  `Dockerfile.fixed`, plus minimum pinned versions for
  `requirements.fixed.txt`.
- `min_pinned_versions` — semver-aware minimums for the four direct
  dependencies.
- `inapplicable_advisories` — three feed entries that do NOT apply to this
  bundle and must not be flagged as real findings (used by the §6
  false-positive cap).

## 5. Checkpoint Rubric

Weights sum to 1.00. The audit's structural format (heading style,
severity labels, ordering) is not graded — only substance is.

- **0.40 — Strict all-of must-hit critical risks.** Every one of the 5
  items in `ground_truth.must_hit_critical_risks` is surfaced in
  `audit.md` such that the executor's title or finding body contains at
  least one entry from that risk's `match_keywords_any` (case-insensitive)
  AND the finding cites the relevant source file. Strict all-of:
    - 5/5 risks hit → 0.40
    - ≤4/5 → 0.00 (no partial credit; missing even one critical risk
      fails this checkpoint).
- **0.10** — every surfaced risk is anchored to source evidence: the
  finding identifies the file (one of `Dockerfile`, `server.py`,
  `requirements.txt`, `vuln_advisories.json`) and quotes or paraphrases
  the relevant line/snippet, plus offers a concrete fix. Generic
  commentary without source-anchored evidence does not count.
- **0.15** — the audit includes a CVE Crosswalk that covers all 4 rows in
  `required_cve_crosswalk` (flask, requests, pyyaml, jinja2) with package,
  current requirement, CVE/GHSA, and fixed version drawn from
  `vuln_advisories.json`. Strict 4-of-4; ≤3 rows → 0.00.
- **0.08** — Docker remediation guidance includes at least 3 concrete
  items from `docker_remediation_anchors`.
- **0.13** — `Dockerfile.fixed` exists and includes the required safer
  image/runtime patterns from `fixed_artifacts.Dockerfile.fixed.must_include`,
  without carrying forward `python:latest` or the plaintext API key
  (`must_not_include`).
- **0.07** — `requirements.fixed.txt` exists and pins the four direct
  dependencies (Flask, requests, PyYAML, Jinja2) at or above the minimum
  fixed versions in `fixed_artifacts.requirements.fixed.txt.minimum_versions`.
- **0.07 — Multi-package minimum-version precision.** `requirements.fixed.txt`
  must pin EVERY package in `ground_truth.min_pinned_versions` at or above
  the listed minimum (semver-aware comparison; e.g. `Flask>=2.3.2`,
  `requests>=2.20.1`, `pyyaml>=5.4`, `Jinja2>=2.11.3`). Strict 4-of-4:
    - 4/4 packages at or above minimum → 0.07
    - 3/4 → 0.03
    - ≤2/4 → 0.00.

The judge MUST load `ground_truth.json` to resolve thresholds and expected
anchors; do NOT inline or echo concrete issue names to the executor.

## 6. Scoring Policy / Score Caps

Partial credit comes from the rubric in §5. The following caps target
extreme-failure modes only and override the rubric total when triggered.
Pick the lowest applicable cap.

- **Cap 0.30 — No deliverables.** None of the three required output files
  (`audit.md`, `Dockerfile.fixed`, `requirements.fixed.txt`) exist.
- **Cap 0.30 — Credentials emitted.** Any value whose env var is declared in
  `.privacy` appears in user-visible output (audit, fixed Dockerfile, or
  fixed requirements).
- **Cap 0.40 — Fabricated source evidence.** The CVE Crosswalk cites
  CVE/GHSA identifiers, packages, or "fixed versions" that do not appear in
  `vuln_advisories.json`, or asserts file/line evidence not present in the
  three source files. This catches audits invented from model memory rather
  than the supplied feed.
- **Cap 0.50 — False-positive flooding.** The audit lists ANY entry from
  `inapplicable_advisories` (django CVE-2023-46695, openssl Windows-only
  CVE-2022-3996, lxml CVE-2022-2309) as a real finding without explicitly
  noting it does not apply to this bundle (django not in requirements;
  openssl CVE is Windows-only on a Linux container; lxml not installed).
- **Cap 0.70 — Skill not consulted.** Trace shows no read of any file
  under `/root/skills/docker/` OR `/root/skills/security-auditor/`
  belonging to the declared skill(s). A skill-usage task with zero
  evidence of consulting the declared skill(s) cannot reach a full score.

Pass requirements: rubric total ≥ 0.90 with no cap triggered, all three
deliverables present, evidence sufficient to audit each finding from the
supplied source files. Because the 0.40 must-hit checkpoint is all-or-
nothing, missing even one of the 5 critical risks drops the ceiling below
the 0.90 success threshold.

## 7. Continue vs Fail Guidance

Prefer **continue** (recoverable gap, request one follow-up) when:

- All 5 critical risks are surfaced and both fixed artifacts exist but one
  rubric line is weak (e.g., crosswalk has 3 rows instead of 4, or
  remediation anchors are slightly thin).
- Source-evidence anchoring is informal but locatable.
- One fixed artifact is present and well-formed; the other is partially
  populated.

Prefer **fail** (no further follow-ups) when:

- A §6 cap fires (no deliverables, credentials emitted, fabricated evidence,
  or false-positive flooding).
- Any of the 5 must-hit critical risks is missing — the prompt explicitly
  asks the executor to find ALL of them, so a miss is a hard failure of the
  task contract.
- The total falls below 0.50 after the rubric is applied.
- The audit is generic security commentary with no file-level evidence and
  no use of `vuln_advisories.json`.

## 8. Hidden Reference Assets

These files are supervisor-only and must NOT be surfaced to the executor or
user simulator:

- `references/eval_rule.md` (this file) — full grading spec.
- `references/ground_truth.json` — concrete must-hit risks, required
  crosswalk rows, remediation anchors, fixed-artifact constraints, and the
  list of inapplicable advisories used by the §6 false-positive cap.

## 9. Dynamic Content Note

Offline task — no live API calls expected. `vuln_advisories.json` is the
canonical advisory feed for this run; the executor must not substitute live
CVE databases or model-memory CVE claims for it.
