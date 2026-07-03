# Design notes — task_101_39_music_analysis

Internal-only archive. Not injected into executor or supervisor at runtime.

## Skill-trace caps (archived from earlier eval_rule revisions)

Earlier revisions of this task's eval_rule included per-skill trace caps at
0.89 for each declared skill (`pdf-reading-local`, `humanizer-zh`,
`content-writer`), triggered when no read of the skill's `SKILL.md` or any
file under that skill directory appeared in the trace.

These caps were removed from the runtime eval_rule because:

1. The `0.89` value did not target an extreme-failure edge case; it was a
   process-shaped cap that overlapped with normal §5 rubric judgement.
2. Trace-based "skill consultation" is hard to verify reliably from
   supervisor-visible signals when the executor uses internal reasoning to
   apply a skill's guidance without a literal file read.
3. The task design intentionally lets §5 (anchor coverage, formula
   preservation, term-style, scope honesty) carry the weight of judging
   whether the declared skills were genuinely applied.

If a future revision wants to reintroduce a skill-trace signal, prefer:

- A single low cap (≤ 0.50) gated on **all three** declared skills having
  zero trace evidence AND the §5 score being implausibly high, OR
- A §5 sub-checkpoint that scores observable artefacts of skill use
  (e.g., `English(中文)` term style for `humanizer-zh`, structured
  section-by-section coverage for `content-writer`, formula preservation
  for `pdf-reading-local`).

## Anchor-claim pool rationale

The anchor pool in `ground_truth.json` mixes conceptual anchors
(self-attention, multi-head attention, positional encoding) with
quantitative anchors (28.4 BLEU, 41.8 BLEU, 3.5 days, 8 GPUs) so that the
0.20 anchor-coverage checkpoint cannot be satisfied by a purely conceptual
summary that drops all metrics, nor by a metrics-only paragraph that skips
the architectural ideas.

`min_anchor_claims_hit = 6` out of 10 leaves room for natural translator
choices (e.g., omitting one BLEU number or one of the three attention
concepts) without forcing a checklist-style output.

## Heading-order requirement

`min_heading_hits = 5` out of 8 source headings, with order preserved,
captures the prompt's "preserve the section structure for the selected
parts" requirement. Five hits is the smallest count that still pins the
output to the paper's actual flow (Abstract → Introduction → Background
→ Model Architecture → … → Conclusion) rather than allowing arbitrary
re-ordering.

## Review pass (2026-04-30) — full redesign to music analysis

The original task asked the executor to produce a Chinese-language study
pack from a real public English deep-learning PDF. User feedback flagged
that the task family was over-skewed toward Chinese-document tooling and
that the skill set (`pdf-reading-local`, `humanizer-zh`,
`content-writer`) overlapped heavily with other tasks in the same shard.
The task was therefore retargeted to **music / audio analysis** with the
clawhub `songsee` skill (rank 312, ~9.9k downloads, 1 version,
`steipete/songsee`). `songsee` was previously unused in
`tasks/101_skill_usage/`, satisfying the cross-family-coverage rule.

### Skill rationale

- `songsee` is a music-information-retrieval (MIR) skill explicitly
  scoped to audio analysis: spectrograms and feature panels.
- Other audio-adjacent skills in the top 1000 are TTS-only
  (`edge-tts`, `openai-tts`, `kokoro-tts`, `mac-tts`, `elevenlabs`),
  STT-only (`openai-whisper-api`, `voice-transcribe`, `elevenlabs-stt`),
  generation-only (`audio-cog`, `vap-media`), or non-MIR utilities
  (`spotify-player`, `ffmpeg-cli`). None of those fit "analyze a song's
  BPM + key + sections" cleanly.
- `task_103_04_audio_transcript` already occupies the speech-to-text
  niche with `openai-whisper-api`, so a music-analysis task with
  `songsee` adds a genuinely new audio sub-family rather than
  duplicating coverage.

### Source rationale

`song.wav` is synthesized rather than borrowed from a public track so
that BPM, key, and section layout are deterministic and reproducible
inside the benchmark, and so the supervisor can ship a
ground-truth-anchored eval that does not depend on external librosa
analysis.

Synthesis recipe (replayable from numpy + scipy alone):

- 22050 Hz mono, 16-bit PCM, total duration 32.0 s.
- Tempo: 120 BPM, 4-on-the-floor synth kick on every beat (except in the
  bridge).
- Key: C major. The harmonic content uses C major triads (C–E–G) on the
  pad, C and G bass alternating per beat, and a C-major scale melody.
  The bridge swaps to an F major (IV) chord with a melody that stays in
  the C major scale.
- Sections (5 in source order):
  - intro  0.0 –  4.0 s (8 beats: pad + kick only)
  - verse  4.0 – 12.0 s (16 beats: pad + bass + simple melody + kick)
  - chorus 12.0 – 20.0 s (16 beats: full arrangement, octave-up bright
    melody, heaviest kick — the loudest moment of the track)
  - bridge 20.0 – 24.0 s (8 beats: kick drops out, soft pad + slow
    melody on F major; deliberate energy dip)
  - outro 24.0 – 32.0 s (16 beats: kick returns and decays in amplitude,
    held C chord with 2-second tail fade)

### Verification (run inside this design pass)

- Tempo via onset-strength autocorrelation: estimated 120.0 BPM
  (autocorrelation peak at lag 0.5 s, exactly one beat).
- Key via Krumhansl–Schmuckler chroma profile fit: top result
  C major (corr=0.906); next G major (0.677), then E minor (0.622).
  C major is unambiguous; A minor (relative minor) is intentionally
  accepted as equivalent in the eval.
- Section RMS profile (0.5 s buckets) recovers the 5-segment layout
  cleanly: 0.07–0.08 (intro) → 0.12–0.13 (verse) → 0.15–0.21 (chorus,
  the global maximum) → 0.07–0.10 (bridge dip) → 0.09–0.16 with a
  decaying tail (outro).

### Eval rubric (§5 sum = 1.00)

Eight checkpoints with strict music-domain checks:

- 0.20 — tempo within ±2 BPM of 120, present in both deliverables
- 0.15 — key matches `C major` or its relative minor `A minor`
- 0.15 — exactly 5 sections in `sections.json`
- 0.15 — section labels in source order
  (intro, verse, chorus, bridge, outro)
- 0.10 — every section boundary within ±1.5 s of ground truth
- 0.10 — prose summary names the chorus as the loudest section
- 0.10 — both deliverables exist and parse; `sections.json` carries
  `bpm`, `key`, and a list of `{start, end, label}` entries
- 0.05 — skill consultation: trace reads `skills/songsee/SKILL.md`
  or applies its named recipes (chroma key fit, onset-autocorrelation
  tempo, RMS section boundaries)

Sum: 0.20 + 0.15 + 0.15 + 0.15 + 0.10 + 0.10 + 0.10 + 0.05 = 1.00.

### Caps (§6)

- 0.30 — no deliverable (analysis.md or sections.json missing/empty/
  unparseable)
- 0.30 — credentials leaked into a deliverable
- 0.30 — fabricated MIR output (lyrics, chord progression, instrumentation
  not in the synthesized track)
- 0.40 — wrong file analyzed (BPM off by >30, key off by >a fifth,
  section count wildly off — consistent with hallucinated analysis)

### Files updated in this redesign

- `tasks/101_skill_usage/task_101_39_music_analysis.yaml` — English prompt
  rewritten end-to-end; sources list `song.wav`; skills list `songsee`;
  output paths `analysis.md` + `sections.json`; skill mention is in the
  first sentence of the first paragraph; no parentheses/brackets in the
  user-facing text.
- `injection/.../sources/song.wav` — newly synthesized
- `injection/.../sources/deep_paper.pdf` — removed
- `injection/.../skills/songsee/SKILL.md` — new MIR skill brief
- `injection/.../skills/songsee/_meta.json` — new
- `injection/.../skills/{pdf-reading-local,humanizer-zh,content-writer}` —
  removed
- `injection/.../references/eval_rule.md` — rewritten for strict
  music-domain checks
- `injection/.../references/ground_truth.json` — rewritten with
  expected_bpm, expected_key (+ equivalents), expected_sections list,
  loudest_section, label synonyms, and a 9-item anchor pool
- `injection/.../meta/source_manifest.json` — updated for `song.wav`
- `injection/.../meta/skill_fork_manifest.json` — updated to reflect the
  songsee fork (numpy/scipy fallback added because the CLI is not
  shipped in the benchmark image)

### What was kept from the old task

Nothing in the runtime artefacts. The "Skill-trace caps" archival note
and the older anchor-claim/heading rationale at the top of this file
are retained as historical record only — they describe the prior
PDF-translation incarnation of this task and do not bind the new
music-analysis design.
