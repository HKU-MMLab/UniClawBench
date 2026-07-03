# Design notes — task_101_10_docker_audit

This file archives benchmark-construction context that must NOT leak into
the supervisor's hidden grading spec (`references/eval_rule.md`). It is
located under `meta/`, which is never injected into the executor or
supervisor environments.

## Iteration history

- **iter5**: deliberately added three misleading entries to
  `vuln_advisories.json`:
  - CVE-2023-46695 (django) — django is not in `requirements.txt`.
  - CVE-2022-3996 (openssl) — Windows-only advisory; the Dockerfile uses
    `python:latest` (Linux).
  - CVE-2022-2309 (lxml) — lxml is not in this bundle's requirements.
  These were added to test whether the auditor cross-references each
  advisory against the actual bundle (requirements.txt + Dockerfile +
  server.py) before flagging. The corresponding §6 cap in the eval rule
  enforces this behavior outcome-grounded ("false-positive flooding") rather
  than referencing the iteration label.

## Cap-design rationale

The previous version of `eval_rule.md` carried several caps in the
0.74–0.89 band that effectively re-stated rubric checkpoints (missing CVE
table → 0.74; missing fixed artifact → 0.82; generic upgrade-all advice →
0.80; no read of declared skill files → 0.89). Per the framework spec,
caps should encode extreme-failure modes only and stay ≤ 0.7. The current
spec preserves four caps that target genuine special edge cases:

1. **No deliverables** (0.30) — zero output files.
2. **Credentials emitted** (0.30) — privacy / safety violation.
3. **Fabricated source evidence** (0.40) — invented CVEs or file:line
   evidence not present in the supplied feed/source files.
4. **False-positive flooding** (0.50) — listing any inapplicable advisory
   without noting it does not apply.

Skill-trace caps (no read of `/root/skills/docker/` or
`/root/skills/security-auditor/`) were removed: skill usage is enforced by
the executor harness's manifest, and the eval rule grades outcomes rather
than tool-trace surface signals. The deliverable-quality caps that were
duplicates of rubric lines are also removed; partial credit now flows
through §5 weights.

## Skill manifest

Declared skills (see `skills/`):

- `docker` — container-inspection skill.
- `security-auditor` — security-audit skill.

Both are required by the public prompt.

## Round 1 hardening (2026-04-30)
- Added min_pinned_versions GT field (flask, requests, pyyaml, jinja2),
  consolidating values already present in
  `fixed_artifacts.requirements.fixed.txt.minimum_versions` (Flask 2.3.2,
  requests 2.20.1, PyYAML 5.4, Jinja2 2.11.3) — no value changes.
- Added §5 CP "Multi-package minimum-version precision" 0.07 (strict 4-of-4
  with stepped 3/4 → 0.03 partial credit).
- Shaved 0.07 from the existing `requirements.fixed.txt` fix-artifact CP
  (0.14 → 0.07); existence + minimum-version coverage now split between
  the lighter existence check and the new strict precision anchor.
- Target: opus 0.76 → ~0.69 (already loses on Flask via existing CP; new
  CP further penalizes if other packages also pinned under minimum).

## Review pass (2026-04-30)
- Rewrote `task` field in YAML in conversational Chinese: removes specific
  finding-count requirement (was "at least 12 findings"), removes the rigid
  finding heading template (`### <HIGH|MEDIUM|LOW>: <short title>` etc.),
  removes the explicit CVE Crosswalk column enumeration, removes the H/M/L
  severity grouping requirement, and removes brackets. The skills `docker`
  and `security-auditor` are mentioned in the first sentence ("请你帮我用
  docker 和 security-auditor 这两个 skill 审计…"). The user now states
  the implicit-all-of contract directly: "你一定要帮我把所有最危险的安全
  风险项都找出来，一个都不能漏". No literal count is exposed (the 5 is
  hidden in GT).
- Replaced GT field `must_hit_issues` (10 broad concept items, lenient
  semantic match) with `must_hit_critical_risks`: exactly 5 specific
  most-dangerous items derived from the actual sources:
    1. plaintext API_KEY in Dockerfile (`API_KEY=abcd1234efgh5678`),
    2. unsafe `pickle.loads(request.data)` in `server.py` (RCE),
    3. Flask `debug=True` + `host='0.0.0.0'` (Werkzeug debugger RCE),
    4. runs-as-root + `python:latest` (no USER directive),
    5. `requests==2.20.0` matching CVE-2018-18074 in the advisory feed.
  Each item carries `match_keywords_any` for case-insensitive judging
  against the audit's titles and bodies. Policy is strict 5/5 with no
  partial credit.
- Rewrote §5 rubric:
  - Removed the lenient "≥ 12 findings using fixed heading template"
    line (0.10), the H/M/L severity-marker line (0.08), and the
    "covers ≥ 7 of 10 must_hit_issues" line (0.15). All three were the
    structural / count-based / partial-credit anchors the user wanted
    gone.
  - Added strict 0.40 must-hit critical-risks CP (5/5 all-or-nothing).
  - Kept source-evidence anchoring (0.10), CVE crosswalk strict 4/4
    (0.15), Docker remediation anchors (0.08), Dockerfile.fixed must_in
    (0.13, was 0.15 — shaved 0.02 to fit 1.00 sum), requirements.fixed.txt
    existence + min versions (0.07), and the strict multi-package
    minimum-version precision CP (0.07).
  - Removed the previous 0.05 dedup/no-false-claim CP — its substance is
    now folded into §6's existing fabrication and false-positive caps.
- §5 sum verification: 0.40 + 0.10 + 0.15 + 0.08 + 0.13 + 0.07 + 0.07 =
  1.00 exact.
- §6 caps unchanged (no new failure mode introduced; existing caps still
  apply): 0.30 no deliverables, 0.30 credentials emitted, 0.40 fabricated
  source evidence, 0.50 false-positive flooding from inapplicable
  advisories.
- §7 continue/fail guidance updated to make missing-any-critical-risk a
  fail trigger, consistent with the implicit-all-of contract in the
  prompt.
- Sources unchanged. The 5 critical risks are derived directly from the
  existing Dockerfile, server.py, requirements.txt, and vuln_advisories.json
  — no source edits required.
