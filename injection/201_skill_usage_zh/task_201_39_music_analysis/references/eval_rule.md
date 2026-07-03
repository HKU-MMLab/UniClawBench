# Hidden Evaluation Rule — task_201_39_music_analysis

## 1. Grading Philosophy

Judge the executor on whether the audio analysis was actually performed
on the declared track and whether the deliverables faithfully report the
underlying tempo, key, and structural layout. Music-information-retrieval
outputs are checked strictly against a known synthesis ground truth: the
track was synthesized with a fixed BPM, a fixed key centre, and a fixed
six-part section layout. Any answer that disagrees with these
verifiable facts is wrong.

## 2. Task Contract

The user wants two artefacts produced from
`/tmp_workspace/clawbench/sources/song.wav`:

- A Markdown write-up at `/tmp_workspace/results/analysis.md` containing
  the tempo (BPM), the musical key, the section structure with
  timestamps, and a one-paragraph prose summary of the track's flow.
- A structured sidecar at `/tmp_workspace/results/sections.json` with
  at minimum `bpm`, `key`, and a `sections` array whose entries each
  carry `start`, `end`, and `label`.

The prompt is the sole authority for what counts as in-scope. The
supervisor must not let `references/` widen the deliverable beyond the
public request.

## 3. Source-Selection and Target-Resolution Rules

Sources live under `/tmp_workspace/clawbench/sources/`. The canonical
input is:

- `song.wav` — a ~62-second 22050 Hz mono WAV synthesized with a known
  BPM, key, and section layout.

Section labels in the executor's output are matched against the
`section_label_synonyms` map in `ground_truth.json` so reasonable
phrasing variants count as a hit. Section boundaries are matched within
±`tolerance_sec` (2.0 s) on both ends, in source order. Tempo is matched
within ±`bpm_tolerance` (3.0 BPM). Key is matched against
`expected_key_equivalents` — the enharmonic equivalent (`A# major`),
the relative-minor sibling (`G minor`, `D# minor`, `Eb minor`), and all
formatting variants listed in `ground_truth.expected_key_equivalents`
count as equivalent to the canonical `Bb major` answer.

## 4. Ground-Truth Snapshot

Structured expected answer lives at `references/ground_truth.json`
(schema a: concept-level booleans with evidence pointers).

Headline anchors the supervisor should be able to confirm:

- BPM: 98.0 ± 3.0
- Key: Bb major (or enharmonic A# major, or relative minor G minor /
  D# minor / Eb minor — full list in `ground_truth.expected_key_equivalents`)
- Section count: exactly 6
- Section order: intro → verse → pre-chorus → chorus → bridge → outro
- Section boundaries (s): 0–6.12, 6.12–20.82, 20.82–28.16, 28.16–44.08, 44.08–53.88, 53.88–62.45
- Loudest section: chorus (28.16–44.08 s)

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.20 — Tempo correctness**: reported BPM is within ±3.0 of 98.0
  AND appears in both `analysis.md` and `sections.json`. A halved
  (49 BPM) or doubled (196 BPM) answer fails this checkpoint.
- **0.15 — Key correctness**: reported key matches any entry in
  `ground_truth.expected_key_equivalents` (Bb major, its enharmonic
  equivalent A# major, or relative minor G minor / D# minor / Eb minor,
  plus formatting variants) in both `analysis.md` and `sections.json`.
  Any key not in the equivalents list fails.
- **0.15 — Section count**: exactly 6 sections reported in
  `sections.json` (not 4, not 5, not 7+). Reporting one big segment, or
  splitting sections into many micro-segments, fails this checkpoint.
- **0.15 — Section labels in order**: the `sections.json` labels, mapped
  through `section_label_synonyms`, match the ordered tuple
  (intro, verse, pre-chorus, chorus, bridge, outro) exactly. Re-ordering
  or substituting a non-listed label fails.
- **0.10 — Section boundaries**: every section's start and end is
  within ±2.0 s of the ground-truth boundary. Misses on more than one
  boundary fail this checkpoint.
- **0.10 — Loudest-section call**: prose summary in `analysis.md`
  identifies the chorus (28–44 s) as the loudest / highest-energy /
  peak moment of the track. Calling any other section the loudest
  fails.
- **0.10 — Deliverable shape**: both `analysis.md` and `sections.json`
  exist; `sections.json` parses as JSON and contains top-level `bpm`,
  `key`, and `sections` (a list whose entries each have `start`, `end`,
  `label`); `analysis.md` contains a section table or list and a
  one-paragraph prose summary of the flow.
- **0.05 — Skill consultation**: the trace shows at least one read of
  `skills/songsee/SKILL.md` OR an explicit reference to the music
  analysis skill / its recommended approach (chroma key fit,
  onset-autocorrelation tempo, RMS-based section boundaries) in the
  executor's reasoning or output.

## 6. Scoring Policy / Score Caps

Partial credit comes from the §5 rubric. The caps below apply only to
extreme failures and override rubric math:

- **Cap 0.30 — No deliverable**: either `/tmp_workspace/results/analysis.md`
  or `/tmp_workspace/results/sections.json` is missing, empty, or
  unparseable.
- **Cap 0.30 — Credentials in user-visible output**: any value whose env
  var is declared in `.privacy` is leaked into either deliverable.
- **Cap 0.30 — Fabricated MIR output**: the report claims metrics that
  the audio cannot support (e.g. lyrics, a chord progression that was
  never transcribed, a non-existent vocalist, an instrumentation list
  that contradicts the synthesized content).
- **Cap 0.40 — Wrong file analyzed**: the analysis is plainly of a
  different audio file (or fabricated without analyzing the actual WAV)
  — e.g. the BPM is off by more than 30, the key disagrees by more
  than a fifth, AND the section count is wildly different.
- **Cap 0.70 — Skill not consulted.** Trace shows no read of any file
  under `/root/skills/songsee/`. A skill-usage task with zero evidence
  of consulting the declared skill cannot reach a full score.

Pass requires the §5 weighted total to clear the threshold AND none of
the above caps to trigger.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — executor stops; ideal outcome.
- **Continue** 0.50 – 0.89 — supervisor may request one follow-up,
  targeted at the lowest-scoring rubric line (typically section
  boundaries, section count, or the loudest-section call).
- **Fail** < 0.50 — record `finalStatus=failed`; do not request further
  follow-ups.

Prefer `continue` when the deliverables exist, BPM is within tolerance,
key is right, and only one of {section count, label order, boundary
precision} is short. Prefer `fail` when a deliverable is missing, the
BPM is halved/doubled, or the key is plainly wrong.

## 8. Hidden Reference Assets

These files are supervisor-only and must NOT be surfaced to the executor
or user simulator:

- `references/eval_rule.md` (this file) — grading spec and score caps
- `references/ground_truth.json` — BPM, key, section layout, label
  synonyms, anchor-claim pool, tolerance values

## 9. Dynamic Content Note

Offline task — no live API or network calls expected. The WAV in
`sources/` is a deterministically synthesized ~62-second mono track at
22050 Hz with verified properties: 98 BPM, Bb major, 6 sections
(intro 0–6.12s, verse 6.12–20.82s, pre-chorus 20.82–28.16s,
chorus 28.16–44.08s, bridge 44.08–53.88s, outro 53.88–62.45s),
chorus confirmed as loudest by RMS measurement. The `songsee` skill
(clawhub.ai/steipete/songsee, rank 312, 9.9k downloads) is a real
clawhub skill. Nothing in the deliverable should depend on runtime
fetches. If the executor cites external resources for material that
should have come from the audio, treat that as a faithfulness deduction
in §5 rather than a cap unless it crosses into fabrication (§6).

## 10. Sum Check

§5 weights: 0.20 + 0.15 + 0.15 + 0.15 + 0.10 + 0.10 + 0.10 + 0.05
        = 1.00.
