# Hidden Evaluation Rule — task_201_32_sysadmin_forensics

## 1. Grading Philosophy

Judge the executor on whether the public request was actually completed and
whether the declared skills under `/root/skills/` were genuinely consulted.
Prefer semantic matching over exact-string matching when the user's prompt
would not pin down a specific key name. Score caps in §6 override rubric
totals when triggered.

## 2. Task Contract

The user supplied a `history.txt` of suspicious shell activity plus
fragments of `auth.log`, `syslog`, and `cron.log`, and requested:

1. `/tmp_workspace/results/forensics.md` — a time-ordered timeline table
   containing every one of the 12 in-scope events, a phased attack
   narrative (entry, privilege_escalation, lateral, persistence,
   anti_forensics, plus background noise where they fit) with MITRE
   ATT&CK technique IDs tagged per phase, and a five-item cleanup /
   hardening list where each item references a specific IOC string.
2. `/tmp_workspace/results/evidence.csv` — exactly 12 time-ordered rows
   (one per event in `ground_truth.expected_timeline_events`) with
   columns `event_id, timestamp, phase, source_file, evidence_text,
   interpretation, recommended_action`. Phase values must normalize to
   `entry / lateral / privilege_escalation / persistence / anti_forensics
   / noise`. Evidence text must be copied verbatim from the source logs.
3. `/tmp_workspace/results/iocs.json` — confirmed indicators grouped into
   `accounts, external_ips, internal_hosts, files_or_paths, persistence,
   stolen_credentials`, plus a separate `likely_noise` list for things
   that look suspicious but are background or normal admin activity.

The public prompt alone is authoritative for in-scope work.

## 3. Source-Selection and Target-Resolution Rules

Sources live under `/tmp_workspace/clawbench/sources/`. The supervisor must
treat the following file list as canonical input; anything outside it is
out of scope:

- `history.txt`
- `auth.log`
- `syslog`
- `cron.log`

Time ordering is taken from each line's own timestamp; when sources
disagree, prefer the timestamp closest to the corroborating event in
another file.

## 4. Ground-Truth Snapshot

The structured expected answer lives at `references/ground_truth.json`
(schema a+b: 12 timeline anchors, per-phase anchors, IOC groups, and
noise list). The supervisor MUST consult `expected_timeline_events`,
`expected_per_phase_anchors`, and `confirmed_iocs` when grading.

Anchored facts the supervisor uses for cross-checking:

- Attacker external IP: `198.51.100.4`.
- Compromised accounts: `user`, `alice`.
- Internal hosts touched: `edge-host`, `db-staging`.
- Attacker-created paths: `/tmp/pwn.sh`, `/tmp/.bash`,
  `/tmp/alice_id_rsa`, `/tmp/notes.log`.
- Stolen credential: `/home/alice/.ssh/id_rsa`.
- Persistence: per-minute crontab beacon `* * * * * /tmp/pwn.sh --beacon`.
- Background / benign signals: failed password attempts from
  `203.0.113.77`; successful internal login `deploy from 10.0.0.45`;
  root backup cron `/usr/local/sbin/backup-staging` predating the
  attack window.

Required attack stages: entry, privilege_escalation, lateral, persistence,
anti_forensics. Total expected timeline events: **12**.

## 5. Checkpoint Rubric

Weights sum to 1.00. All checkpoints are strict — no "≥X/Y" partial
credit unless explicitly stepped.

- **0.11 — Timeline completeness.** `forensics.md` timeline table has
  exactly 12 rows in ascending time order, each row names the source
  file, and **all 12** anchor strings from
  `ground_truth.expected_timeline_events[*].anchor` appear verbatim
  (substring match) in the rendered timeline. Missing any one event
  scores 0 on this checkpoint.
- **0.13 — Phase-anchor coverage.** The phased narrative in
  `forensics.md` must place each anchor from
  `ground_truth.expected_per_phase_anchors` under the correct phase
  heading. Every phase listed in `expected_per_phase_anchors` (entry,
  privilege_escalation, lateral, persistence, anti_forensics, noise)
  must be present and must include all of its expected anchors. Any
  missing phase or any anchor placed under the wrong phase scores 0.
- **0.10 — Verbatim citations.** Reasoning quotes ≥5 distinct command
  or log substrings; each quoted substring appears verbatim
  (case-sensitive) in one of the four source files.
- **0.08 — Five cleanup actions, IOC-anchored.** `forensics.md`
  contains exactly 5 cleanup actions, each backed by a timeline row
  (timeline index referenced in the cleanup item, or cleanup item
  paraphrases a specific timeline-row command). Fewer or more than 5
  scores 0.
- **0.13 — evidence.csv strict.** `evidence.csv` exists with the
  prompt-requested columns, exactly 12 time-ordered rows (one per
  expected event), normalized phase labels, and exact evidence text
  copied verbatim from the source logs. Anchor strings from
  `expected_timeline_events[*].anchor` must each appear as a verbatim
  substring of an `evidence_text` cell. Phase value for each row must
  match the expected phase for that anchor. Missing/extra rows or any
  phase mismatch scores 0.
- **0.15 — iocs.json strict.** `iocs.json` exists and groups confirmed
  accounts, external IPs, internal hosts, files or paths, persistence,
  and stolen credentials. It MUST include every value in
  `ground_truth.confirmed_iocs` (accounts `user` and `alice`;
  external_ip `198.51.100.4`; internal_hosts `edge-host` and
  `db-staging`; files_or_paths `/tmp/pwn.sh`, `/tmp/.bash`,
  `/home/alice/.ssh/id_rsa`, `/tmp/alice_id_rsa`, `/tmp/notes.log`;
  persistence `* * * * * /tmp/pwn.sh --beacon`; stolen_credentials
  `/home/alice/.ssh/id_rsa`). It MUST place `203.0.113.77` and the
  `deploy from 10.0.0.45` event in the `likely_noise` group rather than
  among confirmed indicators. Any missing IOC or noise misclassification
  scores 0.
- **0.10 — No fabricated citations.** Every command or path cited in
  the three deliverables can be grep-found in at least one of
  `history.txt`, `auth.log`, `syslog`, or `cron.log`; any citation
  absent from all four files counts as an invention.
- **0.05 — Cross-deliverable consistency.** The three deliverables
  agree on event ordering, phase labels, and remediation targets;
  minor wording differences are acceptable.
- **0.08 — Cleanup-action IOC reference precision.** Each of the 5
  cleanup actions in `forensics.md` must reference a specific
  path/IOC string from `iocs.json::confirmed_iocs` (verbatim
  substring of an IOC value). All
  `ground_truth.min_cleanups_with_ioc_reference` (= 5) of the 5
  cleanup actions must reference an IOC. Stepped credit:
  - 5/5 → 0.08
  - 4/5 → 0.04
  - ≤3/5 → 0.00.
- **0.07 — MITRE ATT&CK technique tagging.** The phased narrative
  (or evidence.csv) must tag each of at least
  `ground_truth.min_phases_with_mitre_tag` (= 4) of the phases with
  a MITRE ATT&CK technique ID from
  `ground_truth.mitre_acceptable_techniques` (e.g., T1078, T1110).
  Stepped credit:
  - ≥4 phases with MITRE tags → 0.07
  - 3 → 0.03
  - ≤2 → 0.00.

Total: 0.11 + 0.13 + 0.10 + 0.08 + 0.13 + 0.15 + 0.10 + 0.05 + 0.08 + 0.07 = 1.00.

## 6. Scoring Policy / Score Caps

Partial credit comes from satisfied checkpoints. The following caps
override the rubric only on the listed extreme failures:

- **Cap 0.30** — none of the three required output files exist (no
  deliverables produced).
- **Cap 0.30** — any value declared in `.privacy` (credentials,
  secrets) appears in user-visible output.
- **Cap 0.45** — every citation in the deliverables fails to grep in
  any of the four source files (fabricated sources / hallucinated
  evidence).
- **Cap 0.55** — the executor expanded scope beyond the four canonical
  source files (e.g., invented additional logs, hosts, or accounts not
  present anywhere in the inputs) AND those invented entries dominate
  the deliverables.
- **Cap 0.65** — none of the declared skills (`sysadmin-toolbox`,
  `claw-shell`) shows any consultation in the trace (no read of any
  SKILL.md or any file under either skill directory).

Pass requirements: all rubric checkpoints scored, evidence sufficient
for audit, and no cap triggered.

## 7. Continue vs Fail Guidance

Prefer **continue** when:
- Output files exist but one or two checkpoints fall short (e.g., 11
  events out of 12 in the timeline; one phase missing a single
  expected anchor).
- Phase labels are present but slightly off (e.g., `priv_esc` instead
  of `privilege_escalation`) — request normalization.
- `iocs.json` is well-grouped but missed one of the noise items.

Prefer **fail** when:
- No output files were written.
- Citations are largely fabricated (cannot be grep-found in any source).
- Credentials appear in user-visible output.
- The executor refused the task or produced unrelated content.

## 8. Hidden Reference Assets

Supervisor-only — must not be surfaced to the executor or user simulator:

- `references/eval_rule.md` (this file) — grading spec.
- `references/ground_truth.json` — anchored events, IOC groups, and
  noise list used to verify the deliverables.

## 9. Dynamic Content Note

Offline task — no live API calls expected. Source logs are static and
shipped in the injection directory, so timestamps and content do not
drift between the hidden capture and the actual run.
