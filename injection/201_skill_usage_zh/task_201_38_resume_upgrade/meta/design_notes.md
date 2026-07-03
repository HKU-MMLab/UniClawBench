# Design notes — task_101_38_resume_upgrade

Internal archive only. Not injected into executor or supervisor view.

## Round 1 hardening (2026-04-30)
- Added jd_must_be_supported_keywords GT field (postgresql, kubernetes, reliability).
- Added §5 CP "Tech-stack JD label correctness" 0.06 (strict 3-of-3).
- Shaved 0.06 from "Evidence workbook auditable" (0.20→0.14).
- Target: opus 0.88 → ~0.82 (loses 0.06 if any of postgresql/kubernetes/reliability still partial).
- Combined with already-failing quantified-bullet CP (opus has 4 < 5 → 0), opus's effective ceiling drops further.

## Round 2 hardening (2026-04-30) — second anchor
- R1 added JD tech-stack label CP (0.06). Score dropped 0.88→0.70.
- Added §5 CP "Resume-evidence quote precision per must-have row" 0.07.
- Added GT fields must_have_evidence_quote_min_chars + must_have_evidence_quote_min_rows.
- Shaved 0.07 from "Coverage matrix complete" (0.14→0.07).
- Target: opus 0.70 → ~0.55 (loses 0.07 if evidence column has summary/paraphrase rather than verbatim quotes).

## Review pass (2026-04-30) — embedded factual errors

User-confirmed direction: resume-editing realism requires fixing factual
problems, not just polishing. Embedded 3 mixed-class defects in
sources/resume_2023.docx; executor MUST fix all 3.

### Embedded defects (verbatim source anchors)

- **A. Date inversion** — Para [11] heading rewritten:
  `Software Engineer II — Bluebird Logistics (2019–2022)` →
  `Software Engineer II — Bluebird Logistics (2019-06 – 2018-12)`.
  End-month precedes start-month; impossible.
- **B. Internal contradiction (customer count)** — Para [7] keeps
  "billing platform serving 12k customers" (Meridian); para [9]
  rewritten to also say "served 8,000 customers across the billing
  platform". Same role, same period, two different counts.
- **C. Impossible Kubernetes tenure** — Para [4] Professional Summary
  rewritten to claim "4 years of hands-on Kubernetes experience".
  Kubernetes appears only in Meridian (2022–2023) stack, so at most
  ~1–2 years.

### Prompt rewrite (English, skill in first paragraph, no brackets)
- Tells user to fix "factual errors and internal contradictions".
- Skill mention upfront: resume-assistant + word-docx + copywriting.
- Removed all `()` parentheses from instructions (kept paragraph-numbered
  deliverable list and backticks for paths/sheet/column names — those
  are not natural-language brackets).

### Eval rule changes
- Added §5 CP "Factual errors fixed (strict 3/3)" weight 0.12,
  all-or-nothing (3/3 → 0.12, 2/3 → 0.04, ≤1/3 → 0.00).
- Re-balanced: Coverage matrix 0.07→0.05, No fabricated experience
  0.10→0.07, Feedback note compliant 0.10→0.07, Evidence workbook
  0.14→0.10. Freed 0.12 for the new CP.
- §5 sum = 1.00 verified by regex extraction.

### GT additions
- `factual_errors[]` — 3 records each with `id`, `location`,
  `original_text_anchor(s)`, `defect`, `expected_fix`,
  `verification_rule` (regex anchors that supervisor can run on
  resume_v2.docx text).
- `factual_errors_strict_all_or_nothing: true` flag.

### Verification regex (supervisor runs against rewritten resume text)
- A: `2019-?0?6.*2018-?12` — MUST NOT match.
- B: count `\b(12[,\s]?000|12k)\b` and `\b(8[,\s]?000|8k)\b` in
  Meridian bullets — at most one pattern non-zero.
- C: `\b(3|4|5|6|7|8|9|\d{2,})\+?\s*(years?|yrs?)\s+(of\s+)?(hands-on\s+)?Kubernetes`
  — MUST NOT match.

### Failure-mode prediction
- gpt-4.1: likely catches A (visually obvious) and possibly B if it
  reads bullets carefully; C is subtle (tenure-vs-stack inference) so
  partial 2/3 → 0.04. Combined with prior caps the score should land
  ~0.50–0.65.
- Stronger executor: needs careful chronology cross-check across
  summary + experience + skills sections to catch C.
