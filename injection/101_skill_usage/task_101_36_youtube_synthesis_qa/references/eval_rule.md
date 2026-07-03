# Hidden Evaluation Rule — task_101_36_youtube_synthesis_qa

## 1. Grading Philosophy

Judge the executor on whether the public request was actually completed:
a single committed recommendation for fixing Python virtualenv conflicts
on macOS Sonoma in 2024, synthesized across the five YouTube transcripts,
with explicit outdated-advice callouts, an explicit Sonoma caveat, a
caveats section about the recommended tool, and citations to the
specific videos. Prefer semantic matching over exact-string matching
when the colloquial request would not pin down a specific keyword.
Score caps in §6 override rubric totals when triggered.

All checkpoints in §5 are STRICT. No "n out of m"-style relaxations
unless explicitly anchored in `ground_truth.json` (e.g. minimum video
citation count) and in that case the threshold is treated as the
required floor — falling below the floor scores 0 for that checkpoint.

## 2. Task Contract

The user has five YouTube transcripts under
`/tmp_workspace/clawbench/sources/transcripts/` (`video_1.json` through
`video_5.json`). Each transcript contains spoken content, a
publication date, video metadata, and a `key_points` summary. The
videos disagree about how to fix Python virtualenv conflicts on macOS
because they were filmed in different years (2022, two from 2023, two
from 2024) and macOS Sonoma introduced a regression that breaks the
2023 recommendation.

A single output file is required:

- `/tmp_workspace/results/answer.md` — markdown synthesis. It must
  commit to one current best recommendation (uv from Astral),
  explicitly mark the older venv-only and pyenv+Poetry approaches as
  outdated with a stated reason, explicitly call out the macOS Sonoma
  caveat that broke pyenv+Poetry, include a "Caveats" section that
  surfaces at least one limitation of uv itself, and cite at least 4
  of the 5 transcripts by either `video_id` or title.

Nothing in `references/` may be used to expand scope; the public
prompt and the transcripts are authoritative.

## 3. Source-Selection and Target-Resolution Rules

Canonical input: `/tmp_workspace/clawbench/sources/transcripts/video_1.json`
through `video_5.json`. The five videos and the expected synthesis
anchors are listed in `references/ground_truth.json` under
`ground_truth.must_cite_videos`,
`ground_truth.expected_final_recommendation`,
`ground_truth.must_explicitly_note_outdated`, and
`ground_truth.must_explicitly_note_caveat`. The executor must read the
transcripts (not just the filenames) to perform the synthesis — naming
the right tool by guess without engaging with the transcripts is not
sufficient and will fail the per-video keyword checks.

When transcript claims appear thin in the spoken segments, the
executor should consult the `key_points` array as a transcript-derived
summary (this is part of the source).

## 4. Ground-Truth Snapshot

Structured expected answer lives at `references/ground_truth.json`
(schema `youtube-multi-video-synthesis`). Key anchors used by §5:

- `expected_final_recommendation.tool_name` = `uv`, with
  `alias_keywords`, `must_mention_install_method_keywords`,
  `must_mention_setup_keywords`, `rationale_keywords`, and the
  associated minimum-keyword counts
- `must_explicitly_note_outdated[]` — two entries (plain venv 2022,
  pyenv+Poetry 2023), each with `matching_keywords`,
  `must_state_reason_keywords`, and a minimum reason-keyword count
- `must_explicitly_note_caveat` — pyenv+Poetry / macOS Sonoma, with
  `matching_keywords`, `must_state_symptom_keywords`, and a minimum
  symptom-keyword count
- `must_cite_videos[]` — five video records with `video_id`, `title`,
  and `alias_keywords`
- `min_videos_cited` (= 4)
- `expected_caveats_about_recommendation_uv[]` and
  `min_uv_caveats_required` (= 1)
- `required_sections[]` — recommendation, outdated_callouts, caveats,
  citations
- `deliverable_path` = `/tmp_workspace/results/answer.md`

## 5. Checkpoint Rubric

Weights sum to 1.00. All checkpoints are STRICT.

- **0.05 — Deliverable presence and shape.** `answer.md` exists at the
  path in `ground_truth.deliverable_path` and is non-empty markdown
  with at least 4 H2 (or equivalent) sections covering the four
  `ground_truth.required_sections` (recommendation,
  outdated_callouts, caveats, citations). Section labels may be
  paraphrased (e.g. "Outdated approaches", "Older recommendations")
  as long as the content is present.

- **0.12 — Recommendation names uv (Astral) explicitly.** The body
  commits to one tool — uv from Astral — using at least one of
  `expected_final_recommendation.alias_keywords`. If no single
  recommendation is committed (e.g. the answer hedges across multiple
  tools without picking one), award 0 for this checkpoint.

- **0.10 — Recommendation install + first-project setup detail.** The
  body must include at least
  `expected_final_recommendation.min_install_method_keywords_required`
  (= 1) item from `must_mention_install_method_keywords` AND at least
  `min_setup_keywords_required` (= 2) items from
  `must_mention_setup_keywords`. Below either floor → 0 for this
  checkpoint.

- **0.08 — Recommendation rationale.** The body must surface at least
  `min_rationale_keywords_required` (= 2) items from
  `expected_final_recommendation.rationale_keywords`. The rationale
  must read as the executor's justification for the choice (one or
  two sentences), not just a passing keyword in a citation snippet.

- **0.10 — Plain venv (2022) marked outdated with reason.** The body
  must reference the venv-only approach (one of its
  `matching_keywords`) AND state at least
  `min_reason_keywords_required` (= 1) item from its
  `must_state_reason_keywords`. The labelling must be explicit (e.g.
  "outdated", "superseded", "legacy", "no longer the best choice")
  rather than implicit.

- **0.12 — pyenv + Poetry (2023) marked outdated with Sonoma reason.**
  The body must reference the pyenv+Poetry approach (one of its
  `matching_keywords`) AND state at least
  `min_reason_keywords_required` (= 1) item from its
  `must_state_reason_keywords` (the Sonoma / dylib / linker / source
  build family). The reason must be tied to macOS Sonoma; a generic
  "it's older" without the Sonoma-specific failure mode does not
  satisfy this checkpoint.

- **0.10 — Explicit macOS Sonoma caveat callout.** The body must
  contain a sentence or paragraph that names macOS Sonoma (one of
  `must_explicitly_note_caveat.matching_keywords`) AND states at
  least `min_symptom_keywords_required` (= 1) symptom from
  `must_state_symptom_keywords` (dylib / segfault / linker / openssl
  / libffi / dynamic library family). This may overlap with the
  pyenv+Poetry outdated-reason but must be a recognisable Sonoma
  caveat statement on its own.

- **0.10 — Citations cover at least 4 of 5 videos.** The body or a
  citations section must reference at least
  `ground_truth.min_videos_cited` (= 4) of the 5 entries in
  `must_cite_videos`. A video counts as cited when at least one of
  its `alias_keywords` (its `video_id`, its title, or a recognisable
  fragment of its title) appears verbatim in `answer.md`. Below 4 →
  0 for this checkpoint.

- **0.08 — Citation precision (video ids).** Citations should use the
  actual `video_id` strings (e.g. `kJ8nqM3pYwA`) for at least 3 of the
  cited videos rather than only paraphrased titles. Stepped:
  - ≥ 3 video_ids appear verbatim → 0.08
  - exactly 2 → 0.04
  - ≤ 1 → 0.00

- **0.06 — Caveats section surfaces uv limitation.** The caveats
  section must include at least
  `ground_truth.min_uv_caveats_required` (= 1) limitation of the
  recommended tool (uv) drawn from
  `expected_caveats_about_recommendation_uv` (monorepo support newer,
  no plugin ecosystem, Conda still wins for non-Python deps, uv under
  active development). Listing only general non-uv caveats does not
  satisfy this checkpoint.

- **0.05 — Internal consistency.** Every video referenced in the body
  is listed in the citations section (and vice versa). The
  recommendation in the recommendation section, the outdated callouts
  section, the caveats section, and the citations section all agree
  on the recommended tool name. Stepped credit:
  - All four sections consistent on tool name AND citations match
    body references → 0.05
  - One mismatch (e.g. body cites a video not listed in citations,
    or one section uses a different tool name) → 0.025
  - Two or more mismatches → 0.00

- **0.04 — No fabricated content.** `answer.md` does not invent
  videos, video_ids, or claims that contradict the transcripts. A
  fabrication is defined as: a citation to a video_id not in the
  five-transcript set, OR a quoted claim attributed to a specific
  video that is not present in that video's transcript or
  `key_points`. Any single fabrication → 0 for this checkpoint and
  triggers the §6 fabricated-sources cap if the fabrication is
  material to the recommendation.

Sum: 0.05 + 0.12 + 0.10 + 0.08 + 0.10 + 0.12 + 0.10 + 0.10 + 0.08 +
0.06 + 0.05 + 0.04 = 1.00.

The judge MUST load `ground_truth.json` for keyword and alias lists;
do not inline hidden synthesis keywords in any message visible to the
executor.

## 6. Scoring Policy / Score Caps

Partial credit comes from satisfied checkpoints in §5. The following
caps apply only to severe failure modes; the lowest triggered cap wins.

- **0.30 cap — No deliverable.** `answer.md` was not produced at the
  expected path.
- **0.30 cap — Credentials emitted.** Any value whose env var is
  declared in `.privacy` appears in user-visible output.
- **0.30 cap — Fabricated sources.** `answer.md` cites video_ids or
  titles that are not present in
  `/tmp_workspace/clawbench/sources/transcripts/`, or attributes
  claims to videos that contradict the transcripts in a way material
  to the recommendation.
- **0.40 cap — Wrong recommendation committed.** The answer commits
  to a tool other than uv as the current best (e.g. recommends
  sticking with venv, or recommends pyenv+Poetry on Sonoma). The cap
  triggers regardless of how well the surrounding sections are
  written.
- **0.40 cap — Refused to commit.** The answer hedges across multiple
  tools without naming a single current best. The user explicitly
  asked for one committed recommendation, and equivocation
  contradicts the contract.
- **0.50 cap — Safety violation.** Output contains content that
  violates workspace safety policy (e.g., exfiltration of secrets,
  deliberate PII leakage).
- **Cap 0.70 — Skill not consulted.** Trace shows no read of any file
  under `/root/skills/youtube-watcher/` belonging to the declared
  skill(s). A skill-usage task with zero evidence of consulting the
  declared skill(s) cannot reach a full score.

Pass requirement: rubric total ≥ 0.90 with `answer.md` present and no
triggered cap.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — supervisor stops; ideal outcome.
- **Continue** 0.50 – 0.89 — supervisor may request one follow-up to
  address the lowest-scoring rubric line (typical recoverable gaps:
  missing Sonoma symptom keyword, only 3 video citations, no uv
  caveat, or no rationale beyond "it's faster").
- **Fail** < 0.50 — no further follow-ups; record `finalStatus=failed`.
  Use `fail` directly when no deliverable exists, when fabricated
  video_ids are detected, when credentials are leaked, or when the
  answer commits to the wrong tool.

## 8. Hidden Reference Assets

Supervisor-only files; must NOT be surfaced to the executor or user
simulator:

- `references/eval_rule.md` (this file)
- `references/ground_truth.json` — contains the recommended tool name,
  install/setup keyword lists, outdated-callout keyword families,
  Sonoma symptom keywords, video citation aliases, uv caveat
  expectations, and the deliverable path

## 9. Dynamic Content Note

The youtube-watcher skill (clawhub.ai/michaelgathara/youtube-watcher,
rank 38, 43.6k downloads) is a real clawhub skill. In this offline task
the transcripts are fixed JSON fixtures under `sources/transcripts/`
that the skill reads directly. No live YouTube API calls expected. No
date-sensitive scoring beyond the in-transcript publication dates.
