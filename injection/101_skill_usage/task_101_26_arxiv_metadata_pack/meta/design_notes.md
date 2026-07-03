# Design notes — task_101_26_arxiv_metadata_pack

Internal archive only. Not injected into executor or supervisor prompts.

## Source set composition

The `arxiv_papers/` folder ships 7 PDFs total. The user prompt describes
5 of them as the foundational LLM reading list and the other 2 as
unrelated papers a colleague dropped in. The executor must filter
the in-scope 5 from the full set of 7.

In-scope (5): `1706.03762`, `2005.14165`, `2203.02155`, `2303.08774`,
`2307.09288` — Transformer / GPT-3 / InstructGPT / GPT-4 / Llama 2.

Off-theme (2):
- `2401.99001` — COBOL code-generation case study (LoRA modernization).
  Outside the foundational LLM / GPT-family / instruction-tuning theme.
- `2402.88002` — multilingual IR pretraining ablation (encoder-only
  retrieval). Outside the foundational LLM theme.

The two off-theme PDFs were added so that the task tests scope
discrimination, not just PDF parsing throughput. Including either of
them as a `Papers` row, or as one of the 5 in-scope summary bullets,
constitutes a scope-blowout failure.

## Scope-discrimination rubric

The eval rubric awards a stepped 17% for naming both off-theme arxiv
ids in an "Excluded" section of `summary.md` with a one-line reason
each (full credit for 2/2, half for 1/2, none for 0/2). Putting the
off-theme ids in an Excluded section is encouraged and is not a
violation of the §6 scope cap.

## History

Earlier drafts had separate caps for "no skill evidence" at 0.89 and
for "scope blowout" at 0.78. These have been retuned so that score
caps fire only on extreme outcomes (no deliverables, total scope
blowout into both spreadsheet and main summary, fabricated source,
credentials emitted). Partial scope slips and missing skill traces
are now expressed via the rubric and the no-deliverables cap, not
as standalone caps.

## Round 7 hardening (2026-04-30) — pass trim
- Currently pass 1.0; add arxiv id format CP (0.05).
- Shaved 0.05 from scope-discrimination CP (17% → 12%).
- Target: opus 1.0 → ~0.95.

## Round 8 hardening (2026-04-30) — anchor swap (arxiv format → key-contribution)
- R7 arxiv-id format anchor didn't bite (still pass 1.0); replacing with stricter "Per-paper key-contribution statement" CP at same 0.05 weight.
- New requirement: ≥4 of 5 in-scope papers in summary.md need a distinct ≥40-char key-contribution line surfacing main novelty (not title restatement).
- GT swapped: removed arxiv_id_format_required + arxiv_id_format_regex + min_arxiv_ids_correct_format; added min_papers_with_key_contribution: 4 + min_key_contribution_chars: 40.
- §5 sum still 1.00 (pure replacement at same 0.05 weight).
- Target: opus 1.0 → ~0.95 (continues to pass) but biting harder on shallow takeaway lines.

## Review pass (2026-04-30) — full topic redesign

User feedback (review_record.md task 26):
1. 增加数据量 — more papers
2. 不要 "(一篇 COBOL 代码生成，一篇多语 IR pretraining)" 这个 hint，也不要提到具体数值 — implicit checkpoint leak
3. 文档应无序命名，找一些 title 具有迷惑性的（如 2407.05600 实际 image generation but 标题含 LLM-ish keywords）
4. 可能 topic 不要选 LLM — 容易区分

User-confirmed topic: **Robotics / embodied AI** with title-confusing distractors.

### Source-set redesign
- Removed: 7 LLM-themed PDFs (1706.03762, 2005.14165, 2203.02155, 2303.08774, 2307.09288, 2401.99001, 2402.88002).
- Added: 12 robotics-themed placeholder PDFs (ReportLab-rendered) with scrambled filenames `paper_a3f.pdf` ... `paper_m9z.pdf`. Each PDF carries the arxiv id, title, authors, year, abstract, and pad sections so a parser can extract real metadata.
- 7 in-scope robotics papers: ManiSkill3 (2410.00425), RT-2 (2307.15818), Diffusion Policy (2303.04137), Voltron (2302.12766), PaLM-E (2303.03378), Open X-Embodiment (2310.08864), RoboCat (2306.11706).
- 5 off-topic distractors with title-confusing keywords:
  - 2407.05600: latent-diffusion image generation, title says "Compositional Manipulation" → not robotic manipulation.
  - 2401.18000: multi-agent RL for board games (Stratego/Hanabi).
  - 2403.22002: diffusion-based tabular data augmentation, title says "Manipulation" → not robotic.
  - 2402.30050: CV feature-map interpretability, title says "Locomotion-Inspired" → metaphor.
  - 2406.14400: HCI user study on chatbot avatars, title says "Embodiment Effects" → software-only.

### Prompt redesign
- Switched to ENGLISH (was already English; reaffirmed CRITICAL rule).
- Topic: robotics reading group with mis-filed PDFs.
- Removed all explicit counts ("5 in-scope, 2 off-topic", "(one COBOL, one multi IR pretraining)") — no implicit checkpoint hints.
- Mentions skills in the FIRST paragraph ("use the workspace's pymupdf-pdf-parser-clawdbot-skill ... document-pro ... xlsx-cn").
- Tells executor to "read each PDF and decide on content, not on the filename" without revealing how many fall in each bucket.
- No parentheses; the only `[arxiv_id]` is a literal output-format placeholder.

### Eval / GT redesign
- §5 rubric retuned to STRICT in-scope and STRICT off-topic identification (no "≥ N/M" loose matches): missing any in-scope or any off-topic id zeroes that line. Counts checked downstream from the unique-id sets, not from a leaked count.
- New §5 sum (verified 1.00):
  - 0.10 metadata.xlsx Papers shape
  - 0.18 STRICT in-scope identification (all 7 ids exact)
  - 0.15 STRICT off-topic identification (all 5 ids exact)
  - 0.12 per-row title + year (all 7 strict)
  - 0.10 per-row authors (all 7 strict)
  - 0.10 per-row abstract keywords (all 7 strict)
  - 0.07 per-row page count + bibtex (all 7 strict)
  - 0.10 summary.md in-scope bullets (exactly 7)
  - 0.05 stepped key-contribution distinctness (≥6/7 → 0.05; 4-5/7 → 0.025; ≤3 → 0)
  - 0.03 stepped off-topic-reason quality (≥4/5 substantive → 0.03)
  - Total: 1.00.
- §6 caps: kept "no deliverables" (0.30), "scope blowout = any off-topic appears as a row" (0.55), added "off-topic-missed entirely → 0.55", kept "fabricated source / credentials / safety" caps unchanged at 0.55 / 0.30 / 0.30.
- GT json refreshed: `expected_in_scope_papers` (list of 7), `expected_off_topic_papers` (list of 5), per-paper title + accepted authors + abstract keywords + actual_topic + key_contribution_hint + off_topic_reason_template. Filename-to-arxiv_id mapping recorded so supervisor can verify regardless of how the executor recovers ids.
- §9 records actual page counts at packaging time (4-7 pages per PDF) so supervisor can grade `num_pages` correctly.

### Effect
- Difficulty raised: more papers (12 vs 7) + 5 confusing distractors (vs 2 unambiguous) + filename obfuscation. Both LLM and Opus must read each PDF to discriminate.
- No leak surface: prompt has no count, no list of off-topic categories, no distinguishing keyword. Executor must judge on content.
- Strict 7/7 + 5/5 identification lines (33% of total weight) ensure that any miss noticeably hurts the score, matching the user's "暗含全部要求" rule.
