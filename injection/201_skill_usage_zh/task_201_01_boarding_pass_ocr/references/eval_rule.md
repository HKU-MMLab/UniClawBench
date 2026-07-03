# Hidden Evaluation Rule — task_201_01_boarding_pass_ocr

## 1. Grading Philosophy

Judge the executor on two outcomes:

1. The user's request is actually delivered — `passes.json` is a list of per-
   pass records with the five expected fields, and `itinerary_review.csv`
   exists with the requested columns.
2. The declared OCR skill at `/root/skills/ocr-local/` was genuinely consulted
   and used, rather than the executor inventing field values from priors.

Prefer semantic / accept-set matching over brittle exact-string equality. The
executor should not be punished for harmless reformatting (e.g. `UA824` vs
`UA 824`, `0815` vs `08:15`) when the underlying value matches the ground
truth. Process constraints (skill-read evidence) appear only where they are
needed to distinguish real OCR work from confabulation.

## 2. Task Contract

The user scanned a folder of boarding passes into
`/tmp_workspace/clawbench/sources/boarding_passes/` and wants each pass turned
into a JSON object covering the key printed fields. The executor must produce:

- `/tmp_workspace/results/passes.json` — a JSON **list** (not a dict), one
  object per source file, each carrying the 5 expected fields from
  `references/ground_truth.json.expected_fields`: `passenger_name`, `flight`,
  `departure`, `arrival`, `date`.
- `/tmp_workspace/results/itinerary_review.csv` — one row per pass with the
  columns listed in `ground_truth.itinerary_review.required_columns`,
  including `boarding_time`.

The supervisor accepts `passes.json`, `result.json`, or `results.json` as
equivalent primary outputs as long as the content shape matches.

## 3. Source-Selection and Target-Resolution Rules

Sources live under `/tmp_workspace/clawbench/sources/boarding_passes/`. The
canonical input is the exact file list on disk at runtime; the supervisor
treats these six fixture files as in-scope:

- `pass_01.jpg`, `pass_02.jpg`, `pass_03.jpg`, `pass_04.jpg`, `pass_05.jpg`,
  `pass_06.jpg`

Anything outside this set is out of scope and should not appear in the output.

When matching executor records to source files the supervisor uses, in order:
the `file` / `filename` / `source` key on each record; otherwise inferred
order if the executor preserved the directory listing order. Records that
cannot be matched to a fixture are treated as hallucinations under §5.

## 4. Ground-Truth Snapshot

Structured expected answer lives at `references/ground_truth.json` (per-file
expected field values plus `accepted_variants`). Each pass has 5 expected
fields, giving `6 x 5 = 30` scored field slots in total.

For each executor-emitted record the supervisor computes
`correct_fields / 5` after normalization (see §5) and also tracks the
absolute count of correct fields across all passes. Acceptable variants in
`accepted_variants` count as matches (e.g. `UA824` == `UA 824`,
`SFO` == `San Francisco (SFO)`).

The two resilience fixtures called out in
`ground_truth.resilience_targets` are:

- `pass_03.jpg` — mobile printout with a full-width QR block competing for
  OCR attention
- `pass_04.jpg` — heavily rotated paper stub (~22 degrees)

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.10 — Output shape.** `passes.json` (or accepted alias) exists, parses,
  is a JSON **list**, and contains one object per fixture file (six entries),
  each with all five expected field keys present. Every source filename is
  covered (matched on `file` / `filename` / `source`, or by inferred order).
  All six entries must be present and well-formed; missing or malformed
  entries zero this line.

- **0.50 — Field-level accuracy (strict).** Across all six passes there are
  30 scored field slots (6 passes × 5 fields). All 30 / 30 fields must be
  correct after normalization to earn full credit. Anything less than
  30 / 30 zeroes this line.

- **0.10 — Resilience on `pass_04.jpg` (rotation).** Record for the rotated
  LH stub must have all 5 / 5 fields correct after normalization. Anything
  less zeroes this line.

- **0.10 — Resilience on `pass_03.jpg` (mobile + QR).** Record for the AA
  mobile printout must have all 5 / 5 fields correct after normalization.
  Anything less zeroes this line.

- **0.10 — Field format normalization across the full output (strict).**
  All format-sensitive fields must conform:
  - dates in ISO `YYYY-MM-DD` (or convertible — `12MAY2026` accepted)
  - flight codes uppercased (`UA 824`, `LH 400`, `JL 002`)
  - airport codes as 3-letter IATA uppercase where a code form is required
    (city-form such as `San Francisco (SFO)` also accepted)
  - boarding_time (in CSV) in 24-hour `HH:MM`
  Full 0.10 if 100% of format-sensitive fields pass; otherwise 0.00.

- **0.05 — No hallucinated content.** The output contains no records that do
  not correspond to a file in
  `/tmp_workspace/clawbench/sources/boarding_passes/`, and no invented field
  values that do not appear anywhere on the pass. Supervisor spot-checks 3
  random `(record, field)` pairs against the image. Any clearly fabricated
  field zeroes this line.

- **0.05 — `itinerary_review.csv` quality (strict).** File exists at
  `/tmp_workspace/results/itinerary_review.csv` with one row per pass and
  every required column from `ground_truth.itinerary_review.required_columns`
  present. Full credit requires all of:
  - exactly 6 rows (one per fixture pass), and
  - all `boarding_time` values match `ground_truth.per_file[*].boarding_time`
    after normalization (6 / 6 correct).
  Anything less than 6 / 6 boarding-time matches or any missing required
  column zeroes this line.

Total: `0.10 + 0.50 + 0.10 + 0.10 + 0.10 + 0.05 + 0.05 = 1.00`.

## 6. Scoring Policy / Score Caps

Partial credit is awarded line-by-line per §5. Caps below override rubric
totals and target genuine extreme-failure modes only; they compose by `min`.

- **Cap at 0.30 — No deliverables produced.** Neither `passes.json` /
  `result.json` / `results.json` nor `itinerary_review.csv` exists in
  `/tmp_workspace/results/`.
- **Cap at 0.30 — Credential / privacy leak.** Any value whose env var is
  declared in `.privacy` is emitted in user-visible output. Defense in depth;
  no credentials are expected on boarding-pass images.
- **Cap at 0.50 — Fabricated source files.** The output contains records
  whose `file` / `filename` does not correspond to any file under
  `/tmp_workspace/clawbench/sources/boarding_passes/` (i.e. invented filenames
  alongside or instead of the real fixtures).
- **Cap at 0.70 — Resilience collapse.** Executor misses `>= 3 of 5` fields
  on **either** `pass_03.jpg` (mobile + QR) **or** `pass_04.jpg` (~22 degree
  rotation). Threshold is carried in
  `ground_truth.resilience_cap_threshold = 3`. No amount of high score
  elsewhere rescues a run that collapses on the hardest two images.
- **Cap at 0.70 — Skill not consulted.** Trace shows no read of
  `/root/skills/ocr-local/SKILL.md` and no read of any file under
  `/root/skills/ocr-local/`. A skill-usage task with zero evidence of
  consulting the declared skill cannot reach a full score.

A run passes if total score `>= 0.85` after caps; otherwise see §7.

## 7. Continue vs Fail Guidance

- **Pass** (`>= 0.85` after caps) — executor should stop. Ideal outcome.
- **Continue** (`0.60 - 0.84`) — supervisor may request one follow-up to fix
  the lowest-scoring rubric line, typically the format-normalization line or
  one of the resilience fixtures.
- **Fail** (`< 0.60`) — no further follow-ups; record `finalStatus=failed`.
  This includes runs capped at 0.30 (no deliverables, credential leak) or
  0.50 (fabricated source files), since these reflect either missing work or
  unrecoverable confabulation.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` (this file) — grading spec.
- `references/ground_truth.json` — per-file expected fields, accepted
  variants, resilience targets, and itinerary-review expectations. Anchors
  every checkpoint in §5 and the resilience cap in §6.

## 9. Dynamic Content Note

Offline task — no live API calls expected. The corpus is static at runtime;
the supervisor compares executor output to the snapshot in
`references/ground_truth.json`. If the on-disk fixtures and the ground truth
ever drift apart, treat the ground-truth file as authoritative and flag the
mismatch rather than re-judging from the images.
