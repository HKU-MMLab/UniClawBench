# Design notes — task_101_36_youtube_synthesis_qa

Internal archive only. Not injected into supervisor or executor context.

## Scope-discrimination construction

The sources directory contains seven PDFs but the public prompt explicitly
limits the literature review to five in-scope LLM-foundation papers. The
remaining two are intentionally out-of-domain:

- `paper_6.pdf` — biomedical microscopy cell segmentation using a fully
  convolutional U-Net. Subfield: computer vision / biomedical image
  segmentation. No transformer or language-model component.
- `paper_7.pdf` — contextual-bandit re-ranking with calibrated click models
  for e-commerce search result lists. Subfield: information retrieval /
  recommender systems. No transformer or language-model component.

Both off-topic papers were deliberately chosen from clearly distinct ML
subfields so that any minimally careful PDF skim resolves them as off-scope.
Their alias and expected marker keywords live in
`references/ground_truth.json` under `out_of_scope_papers`.

## Iteration history

- Earlier revisions used near-domain off-topic papers (other transformer
  variants) which proved too easy to misclassify as in-scope. The current
  swap to CV-segmentation and IR-bandit makes the discrimination signal
  unambiguous in the abstracts.
- Threshold parameters tuned across iterations:
  `min_body_citations=8`, `min_cross_paper_comparisons=6`,
  evidence matrix exact row count = 5.

## Why a dedicated scope-discrimination checkpoint exists

The 18% rubric line for explicit subfield naming is not redundant with the
"5 rows in CSV" check. The CSV check verifies the executor did not silently
include off-topic papers; the discussion-section check verifies the executor
*understood* why they were off-topic and can articulate the actual subfield.
Both signals must align for full credit.

## v8 hardening round 2 (2026-04-29)

Round 1 of opus-4.6 testing showed this task at capped=1.0 pass — the
six-section structure plus per-paper contribution / constraint plus
six cross-paper comparisons plus four off-topic exclusions was reliably
satisfied. Hardening direction: introduce an implicit cohort-level
synthesis requirement so the executor must read the five papers as a
cohort instead of as isolated cards. Prompt rewritten in natural voice
asking for method comparison, dataset/scale comparison, recurring
limitation patterns, future-work gaps, and cross-paper synthesis
(relations / contradictions / builds-on). Eval rule §5 adds a 0.12
"Dimension coverage" anchor checkpoint requiring ≥4 of 5 lit-review
angles surfaced with concrete, non-generic substance. To rebalance to
1.00, References completeness cut 0.08→0.05 (-0.03), Section structure
cut 0.08→0.05 (-0.03), Body citations cut 0.12→0.09 (-0.03), Method
category alignment cut 0.08→0.05 (-0.03). Ground truth gains
`topic_dimensions` array and `min_dimensions_covered=4`. Score cap numbers
and success_threshold unchanged.

## v8 hardening round 5 (2026-04-29)

Round-2 dimension anchor (0.12, ≥4-of-5) was insufficient on its own —
opus-class executors hit cap 0.95 by satisfying every non-anchor
checkpoint plus a partial dimension match. This round adds a second §5
anchor "Arxiv id precision" at weight 0.08 that requires the
deliverable package to reference, by exact arxiv id OR by alias label,
≥4 of 5 specific in-scope paper anchors: `1810.04805` (BERT),
`2106.09685` (LoRA), `2005.11401` (RAG), `2106.04554` (A Survey of
Transformers), `2302.13971` (LLaMA). Stepped credit: ≥4/5 → 0.08,
exactly 3/5 → 0.04, ≤2/5 → 0.00. To rebalance to 1.00, the two
heaviest non-anchor checkpoints lose 0.04 each: Off-topic
discrimination 0.18 → 0.14 (-0.04) and Evidence matrix shape 0.17 →
0.13 (-0.04). First anchor (Dimension coverage at 0.12) and all other
weights unchanged. Ground truth gains `arxiv_id` field on each entry
of the `papers` array. Score caps and success_threshold unchanged.
Final weights: 0.05 + 0.05 + 0.09 + 0.12 + 0.12 + 0.13 + 0.05 + 0.14 +
0.05 + 0.12 + 0.08 = 1.00.

## v8 hardening round 9 (2026-04-30)

Round-8 measurements showed this task at PASS = 1.0. Round 9 adds a
small auxiliary CP "Section ordering precision" at weight 0.05. The
six H2 sections (Abstract → Introduction → Related Work → Discussion
→ Conclusion → References) must appear in `review.md` in canonical
order; ≥5 of 6 sections must be in correct relative order. Stepped:
6/6 → 0.05, 5/6 → 0.025, ≤4/6 → 0.00. Rebalance: Off-topic
discrimination 0.14 → 0.09 (-0.05) funds the new line; tier credits
scaled accordingly (full → 0.09, ≥50% recall → 0.05). Final §5 sum:
0.05+0.05+0.09+0.12+0.12+0.13+0.05+0.09+0.05+0.05+0.12+0.08 = 1.00.
GT gains `required_section_order` (6 names) and
`min_sections_in_canonical_order: 5`. Score caps and
success_threshold unchanged.

## Review pass (2026-04-30) — full redesign as YouTube multi-video synthesis

User feedback flagged the original "literature pack" design as too
overlapping with task_26. Per the user-confirmed redesign list in
`/tmp/clawbench_modify_instructions.md`, this task is wholly redesigned
as a YouTube multi-video synthesis using the `youtube-watcher` skill
from `skills_top1000_downloads.jsonl` (rank 38, 43.6k downloads,
michaelgathara). Topic chosen: "How to fix Python virtualenv conflicts
on macOS Sonoma in 2024" — picked because it has a clean 2022 / 2023 /
2024 lineage with a real OS-version caveat, so the synthesis is not
just "pick the newest video" but requires recognising why pyenv+Poetry
was right in 2023 yet broken on Sonoma.

### Sources changed
- Removed nine PDFs under `sources/papers/`.
- Added five JSON transcripts under `sources/transcripts/`:
  - `video_1.json` — 2022 venv-only advice (kJ8nqM3pYwA)
  - `video_2.json` — 2023 pyenv+Poetry advice that explicitly labels venv-only as outdated (Lp4xR9zT2mE)
  - `video_3.json` — 2023 Sonoma compatibility warning for pyenv+Poetry (Qs7vN4uWxKj)
  - `video_4.json` — 2024 uv-from-Astral as the new best, addresses Sonoma directly (Wm5tH7yJqRb)
  - `video_5.json` — Tangential history of Python packaging 2008–2024 (Bv2zX8aLpFh)
- Each transcript is structured with `video_id`, `published_at`,
  segment-level `transcript[]` array, and `key_points` summary so the
  executor can synthesise without inventing details.

### Skill changed
- Removed `pymupdf-pdf-parser-clawdbot-skill`, `literature-review`,
  `academic-writing` from `skills/`.
- Added `youtube-watcher/SKILL.md` based on the slug summary in
  `skills_top1000_downloads.jsonl`. SKILL.md describes when to use it,
  how transcripts are structured (json or txt), how to handle multiple
  videos that disagree, and the expected output shape (commit to one
  answer, surface outdated and caveats).
- YAML `skills:` field updated to a single skill: `youtube-watcher`.

### Prompt changed
- Now in ENGLISH (per critical rule 3a). First paragraph names the
  workspace's youtube-watcher skill explicitly. No brackets. Asks for
  a single committed recommendation (not a hedged summary), explicit
  outdated callouts with reasons, an explicit Sonoma caveat, video
  citations, and a Caveats section. Output: `/tmp_workspace/results/answer.md`.

### Eval changes
- Schema renamed to `youtube-multi-video-synthesis`. All 12
  checkpoints in §5 are STRICT — no "n out of m" wording is used
  except where anchored in GT (`min_videos_cited`, stepped citation
  precision, stepped internal consistency, all explicitly tied to
  required floors).
- Final answer must (a) commit to uv as the current best, (b) name
  install + setup keywords, (c) state rationale, (d) mark plain venv
  outdated with a stated reason, (e) mark pyenv+Poetry outdated with
  a Sonoma-specific reason, (f) add a separate Sonoma caveat
  callout, (g) cite ≥4 of 5 videos, (h) use ≥3 verbatim video_ids,
  (i) surface ≥1 uv-specific limitation in Caveats, (j) be
  internally consistent across sections, (k) not fabricate.
- Score caps include a 0.40 wrong-recommendation cap and a 0.40
  refused-to-commit cap to make the contract bite when an executor
  hedges or picks the wrong tool.
- §5 sum verified: 0.05 + 0.12 + 0.10 + 0.08 + 0.10 + 0.12 + 0.10 +
  0.10 + 0.08 + 0.06 + 0.05 + 0.04 = 1.00 (12 checkpoints).

### Ground truth changes
Replaced literature-review schema with a multi-video synthesis schema:
- `expected_final_recommendation` (uv from Astral, with alias / install
  / setup / rationale keyword families and minimum-keyword floors)
- `must_explicitly_note_outdated[]` — venv-only and pyenv+Poetry, each
  with matching keywords and reason-keyword floor
- `must_explicitly_note_caveat` — Sonoma compatibility, with symptom
  keyword family (dylib / segfault / linker / openssl / libffi) and
  floor
- `must_cite_videos[]` — five entries with `video_id`, `title`,
  `alias_keywords`, plus `min_videos_cited = 4`
- `expected_caveats_about_recommendation_uv[]` and
  `min_uv_caveats_required = 1` to keep the executor honest about
  the recommended tool's downsides
- `required_sections[]` and `deliverable_path` for the §5 shape check.

