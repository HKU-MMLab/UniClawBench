# Hidden Evaluation Rule — task_101_03_access_log_regex

## 1. Grading Philosophy

Judge the executor on whether the public request was actually completed and
whether the declared `log-analyzer` skill in `/root/skills/` was genuinely
consulted. Prefer semantic matching over exact-string matching when the
user's voice request would not pin down a specific key name. Numeric
tolerances are tight on purpose: a near-right answer that misses the
calibrated bands does not deserve full credit. Score caps in §6 override
rubric totals.

## 2. Task Contract

Restate of the public prompt: the user has ~70K lines of Apache
common-log-format web logs at `/tmp_workspace/clawbench/sources/access.log`
(NASA mirror plus other hosts, blended) and wants a JSON summary at
`/tmp_workspace/results/summary.json` with six keys:

- `total_requests` — parseable request count
- `malformed_line_count` — lines that do not parse as CLF
- `top_urls` — top 50 paths sorted by count desc, then path asc
- `status_distribution` — HTTP status code -> request count
- `error_rate_by_hour` — bucket key `"DD/Mon/YYYY HH"` -> 4xx+5xx rate, using
  the hour string printed in the log line without timezone conversion
- `suspicious_ips` — IPs with >= 10 4xx hits, each `{ip, fourxx_count}`,
  sorted by count desc

Additionally, the companion `report.md` must explicitly cite the exact
hour bucket where the error rate spikes and the exact 4xx+5xx error
count in that bucket, both pinned to values consistent with
`summary.json`.

The public prompt alone defines scope. Nothing in `references/` may be used
by the executor to expand what is in scope.

## 3. Source-Selection and Target-Resolution Rules

The only canonical input is `/tmp_workspace/clawbench/sources/access.log`,
shipped as a deterministic inline asset in this injection directory. Any
other file under `sources/` is out of scope and must not contribute to the
summary. Hour buckets must be derived from the raw timestamp text in each
log line; do not normalize to UTC or any other zone. Sort ties in
`top_urls` are resolved by ascending path string. Sort ties in
`suspicious_ips` are resolved by ascending IP string.

## 4. Ground-Truth Snapshot

The structured expected answer lives at `references/ground_truth.json`.
Anchor every rubric line to that JSON; do not inline expected values
into this rubric. The relevant fields:

- `parseable_count` (= 70949)
- `malformed_line_count` (= 51)
- `status_distribution` — per-code counts, including the postmortem-only
  codes `499` and `503`
- `top_urls` — ordered list of 50 `{path, count}` entries
- `peak_error_hour` (= "01/Jul/1995 04"),
  `peak_error_hour_iso` (= "1995-07-01T04:00:00Z"),
  `peak_error_rate` (= 0.221691)
- `error_rate_by_hour` — full hour-bucket map
- `top_5_suspicious_ips`, `suspicious_ips_top10`, `suspicious_ips_all`
  (now with all IPs at >= 10 4xx hits)
- `anomaly_time_anchor` — `{hour_bucket, hour_bucket_iso, error_count}`
  used by §5.10
- `tolerance_bands` — numeric bands referenced by the rubric below

## 5. Checkpoint Rubric

Weights sum to exactly 1.00 (5 + 16 + 15 + 6 + 11 + 12 + 11 + 12 + 8 + 4).

### 5.1 (5%) Schema and valid JSON
`summary.json` is valid JSON and contains all six required keys listed in
`ground_truth.summary_required_keys`.

### 5.2 (16%) Parseable request count tolerance
Let `d = |executor.total_requests - ground_truth.parseable_count|`.

| `d` | credit | weight portion |
| :-- | :-- | :-- |
| `d <= tolerance_bands.parseable_count_full` (= 3) | full | 16% |
| `d <= tolerance_bands.parseable_count_partial` (= 10) | partial | 10% |
| `d <= tolerance_bands.parseable_count_half` (= 25) | quarter | 5% |
| `d > 25` | none | 0% |

### 5.3 (15%) Malformed line count tolerance
Let `d = |executor.malformed_line_count - ground_truth.malformed_line_count|`.

| `d` | credit | weight portion |
| :-- | :-- | :-- |
| `d <= tolerance_bands.malformed_line_count_full` (= 0) | full | 15% |
| `d <= tolerance_bands.malformed_line_count_partial` (= 2) | partial | 9% |
| `d <= tolerance_bands.malformed_line_count_half` (= 4) | quarter | 4% |
| `d > 4` | none | 0% |

### 5.4 (6%) Top URLs identity and ordering
`top_urls` must be 50 entries sorted by count desc, then path asc, matching
`ground_truth.top_urls`.

- 6% if all 50 entries match path and count in order.
- 4% if the first 30 entries match path and count in order AND every one of
  the 50 expected paths appears somewhere in the executor's list.
- 2% if at least 40 of the 50 expected paths appear, but ordering or counts
  contain minor mistakes.
- 0% if fewer than 40 expected paths appear, or if the executor returns
  fewer than 50 entries.

### 5.5 (11%) Peak error hour formatting and rate
The argmax of `error_rate_by_hour` must match the ground-truth hour, and
the reported peak rate must track `peak_error_rate`.

Hour-string match:
- Full credit if executor reports the hour as either `peak_error_hour`
  ("01/Jul/1995 04") or `peak_error_hour_iso`
  ("1995-07-01T04:00:00Z").
- A timezone-less ISO-ish form like "1995-07-01 04:00" or "1995-07-01 04"
  is accepted only for partial credit; cap this line at 5%.
- Any other hour string -> 0 for this line.

Rate match (applied on top of hour match):
- If `|executor.peak_rate - peak_error_rate| <= peak_error_rate_abs_full`
  (= 0.001) -> no deduction.
- If `|executor.peak_rate - peak_error_rate| > peak_error_rate_abs_penalty`
  (= 0.003) -> deduct 4 percentage points from this line, floor at 0.

### 5.6 (12%) Status-code breakdown with exact counts
Required: `status_distribution` includes both `499` and `503` keys. For
every key that appears in both `executor.status_distribution` and
`ground_truth.status_distribution`, the count must match GT within
`tolerance_bands.status_breakdown_count_pct` (= +/- 2%).

- 12% if `{499, 503}` are both present AND the six highest-volume GT codes
  (`200, 304, 302, 404, 499, 503`) all have per-code counts within +/- 5%
  of GT.
- If 499 is present but 503 missing (or vice versa) -> cap this line at 7%.
- If either 499 or 503 is missing entirely -> cap this line at 0% (and
  trigger the §6 hard cap).
- Additionally, the sum of reported status counts must equal
  `ground_truth.parseable_count` within
  `tolerance_bands.status_distribution_sum_vs_parseable` (= +/- 5);
  otherwise deduct 3 percentage points from this line, floor at 0.
- GT contains zero `508` responses; an invented `508` row with non-zero
  count -> deduct 3 percentage points from this line.

### 5.7 (11%) Suspicious IPs: exact top-5 plus full top-10 match
Let `exec_top10` be the executor's first 10 IPs from `suspicious_ips`
(sorted by count desc), and `exec_top5` the first 5 of those.

- Top-5 ordered match (7%): `exec_top5` equals
  `ground_truth.top_5_suspicious_ips` exactly. Same five IPs in a
  different order -> 4%. Four of five correct in any order -> 2%. Three
  or fewer correct -> 0%.
- Top-10 strict match (4%): the set of `exec_top10` must equal
  `ground_truth.suspicious_ips_top10` exactly (all 10 IPs present, no
  swaps, no missing entries). Anything less -> 0% on this sub-line.
- If the executor returns fewer than 10 IPs, the top-10 sub-line is 0%
  and top-5 still requires 5 entries.
- Additional strict requirement: every IP returned in
  `suspicious_ips` must have `fourxx_count >= 10` (the prompt's stated
  threshold), and the full set of returned IPs (regardless of count)
  must be a subset of `ground_truth.suspicious_ips_all` IPs. Any IP
  whose `fourxx_count` is below 10 or whose entry is not in
  `suspicious_ips_all` -> deduct 2 percentage points from this line per
  spurious entry, floor at 0.

The judge MUST load `references/ground_truth.json` and compare against the
executor's output rather than relying on memorized values.

### 5.8 (12%) Topic dimension coverage in report.md
A companion narrative at `/tmp_workspace/results/report.md` must exist
and discuss the operational picture across multiple analytical lenses.
The judge inspects the file and counts how many of the five hidden
dimensions in `ground_truth.topic_dimensions` are clearly addressed.
Each dimension counts as covered when the report contains a
recognizable discussion of that lens, anchored to numbers or names from
`summary.json` rather than generic boilerplate.

Dimension matching guidance:
- `traffic_volume_trends` — covers how request volume rises and falls
  across the window (overall volume, per-day or per-hour shape, peak/quiet
  periods). Bare repetition of `total_requests` without temporal framing
  is not enough.
- `status_code_distribution` — discusses the mix of HTTP status codes
  beyond just "mostly 200" (highlighting 4xx/5xx share, the 499/503
  postmortem codes, or notable per-code counts).
- `suspicious_ip_behaviors` — describes what the flagged IPs are doing
  (scanner/brute-force/probe pattern, count or rate signature),
  referencing at least one concrete IP from `suspicious_ips`.
- `url_hotspot_patterns` — discusses which URL paths are getting hammered
  hardest, citing concrete entries from `top_urls` or grouping them
  (e.g. images vs. shuttle/countdown content vs. probe paths).
- `anomaly_timeline` — pinpoints when things started looking off, citing
  the peak error hour, the bad-traffic burst window, or a rough "around
  hour X" framing tied to `error_rate_by_hour`.

Scoring tiers:
- 12% if the report covers at least
  `ground_truth.min_dimensions_covered` (= 4) of the five dimensions.
- 7% if exactly 3 dimensions are covered.
- 3% if exactly 2 dimensions are covered.
- 0% if fewer than 2 dimensions are covered, or if `report.md` is
  missing entirely.
- An additional cap applies: if `report.md` exists but consists only of
  raw dump of `summary.json` with no narrative interpretation, score
  this checkpoint at 0% regardless of dimension count.

### 5.9 (8%) Status code precision in report.md
The companion `report.md` is also examined for explicit numeric
references to specific HTTP status codes from the postmortem-grade set
`status_precision_codes` (= `["499", "503", "502", "504", "408"]`),
each tied to its exact count from `ground_truth.status_distribution`
(or, when the code does not appear in GT, an explicit "0" or
equivalent absence statement).

The judge counts how many distinct codes are mentioned with their
correct counts within `tolerance_bands.status_breakdown_count_pct`
(= +/- 2% of GT, or exact zero when GT has none). Each mention must
pair the code (digit form, e.g. `499`) with its count near the same
sentence or table row.

- 8% if at least
  `ground_truth.min_status_codes_cited` (= 4) of the 5 codes are cited
  with correct counts.
- 4% if exactly 3 are cited with correct counts.
- 0% if 2 or fewer are cited with correct counts, or if `report.md`
  is missing.

The five codes' counts in GT are: `499 -> 236`, `503 -> 171`, plus
`502`, `504`, `408` which have no entries in `status_distribution`
(absence-of-row counts as count zero; the executor must explicitly
note "no 502/504/408 observed" or equivalent to claim credit on those
codes). The 6th-highest GT code `400 -> 329` is intentionally
excluded from this list to push the report toward the postmortem-only
codes.

### 5.10 (4%) Anomaly time anchor precision in report.md
The public prompt explicitly demands a precise anomaly anchor: an exact
hour bucket and an exact 4xx+5xx error count, both pulled from
`summary.json`. The judge inspects `report.md` and grades this line
strictly all-or-nothing:

- 4% if AND ONLY IF BOTH of the following are present in `report.md`:
  1. The hour bucket string matches
     `ground_truth.anomaly_time_anchor.hour_bucket`
     (= `"01/Jul/1995 04"`) or its ISO equivalent
     `ground_truth.anomaly_time_anchor.hour_bucket_iso`
     (= `"1995-07-01T04:00:00Z"`). A timezone-less ISO-ish form like
     `"1995-07-01 04:00"` or `"1995-07-01 04"` is also accepted.
  2. The 4xx+5xx error count for that bucket is cited with the exact
     value `ground_truth.anomaly_time_anchor.error_count` (= `417`),
     within `tolerance_bands.anomaly_error_count_abs` (= 2). The count
     must appear within the same paragraph or sentence-block as the
     hour bucket so the two are clearly tied together.
- 0% otherwise. There is no partial credit on this line: missing the
  hour, missing the count, citing only an error rate without the
  raw count, citing the count without the hour, or citing a different
  bucket all score 0%.

If `report.md` is missing entirely, this line scores 0%.

## 6. Scoring Policy / Score Caps

Partial credit comes from the rubric in §5. The following caps target
extreme failure modes only and override rubric totals:

- **Cap 0.30 — no deliverable.** No `summary.json` produced, or the file
  exists but is not valid JSON.
- **Cap 0.30 — credentials emitted.** Any value whose env var is declared
  in `.privacy` appears in the user-visible output. (Not expected for
  this task; retained for policy parity.)
- **Cap 0.30 — fabricated source.** The summary is computed against any
  file other than the canonical `access.log`, or the executor invents
  log content not present in the corpus.
- **Cap 0.50 — total scope blowout.** The summary omits three or more of
  the six required keys, or replaces them with unrelated content.
- **Cap 0.70 — declared skill not consulted.** The trace shows zero reads
  of any file under `/root/skills/log-analyzer/`. A `skill_usage` task
  with no evidence of consulting the declared skill cannot reach high
  scores.
- **Cap 0.70 — postmortem codes silently dropped.** Either `499` or
  `503` (or both) is missing from `status_distribution`. This is the
  hard-cap branch referenced from §5.6.

## 7. Continue vs Fail Guidance

- **Pass** >= 0.85 — executor should stop. Ideal outcome.
- **Continue** 0.60 to 0.84 — supervisor may request one follow-up to fix
  the lowest-scoring rubric line, provided no §6 cap is in effect.
- **Fail** < 0.60 — no further follow-ups; record `finalStatus=failed`.

Prefer `continue` when the deliverable exists and the gap is a numeric
tolerance miss on a single rubric line. Prefer `fail` when a §6 cap is
active, when `summary.json` is absent or unparseable, or when the
executor refused to consult the declared skill.

## 8. Hidden Reference Assets

These files are supervisor-only and must NOT be surfaced to the executor
or the user simulator:

- `references/eval_rule.md` (this file) — the grading spec.
- `references/ground_truth.json` — anchor for every numeric checkpoint
  and tolerance band in §5.

## 9. Dynamic Content Note

Offline task — no live API calls expected. The corpus is deterministic
from a fixed seed; the same `access.log` payload is shipped on every run.
Treat any mismatch between executor counts and `ground_truth.json` as a
real error rather than drift, since there is no live data source to
explain it away.
