# Design notes — task_101_08_receipts_reconcile

Internal-only notes, never injected into executor or supervisor context.

## Skill-usage cap rationale (archived)

Earlier iterations of this task included two score caps tied directly to
trace inspection of the declared skills:

- "If the trace shows no read of `/root/skills/image-ocr/SKILL.md` or any
  file under `/root/skills/image-ocr/` → cap total at 0.89."
- "If the trace shows no read of `/root/skills/xlsx-cn/SKILL.md` or any
  file under `/root/skills/xlsx-cn/` → cap total at 0.89."

These were retired from the active rubric because (a) the cap value (0.89)
sits above the `success_threshold` (0.90) only marginally and is not an
extreme-failure mode, and (b) they re-state outcome checkpoints rather than
guard against catastrophic failure. The §6 caps in the active eval_rule
target only catastrophic edge cases (no deliverables, credentials emitted,
fabricated sources, total scope blowout).

If a future revision needs to re-introduce skill-trace verification, prefer
expressing it as an outcome ("workbook reflects multi-step OCR + spreadsheet
work consistent with the declared toolchain") rather than as a path-read
trace check.

## Continue/Pass band history

- Earlier band: Pass ≥ 0.96 / Continue 0.50–0.95 / Fail < 0.50.
- Active band: Pass ≥ 0.90 (aligned to the task YAML
  `success_threshold: 0.90`) / Continue 0.50–0.89 / Fail < 0.50.

## Review-flags CSV cap rationale

A previous cap of 0.86 was tied to "review_flags.csv missing or fewer than
three rows." This was removed as a separate cap because it duplicates the
0.05-weight rubric checkpoint and would otherwise act as a non-extreme
ceiling. Missing CSV simply forfeits the 0.05 line.

## v8 hardening round 4 (2026-04-29)

Round-3 abstract dimension anchors were too permissive — supervisor gave
partial credit even when the deliverable barely surfaced any concrete
discount / tax / payment / reconciliation tokens. Round 4 replaces the
abstract phrasing with **anchor-keyword detection** so each dimension is
binary-checkable against a concrete word list. Prompt rewritten to embed
five receipt-analysis dimensions naturally (per-line extraction, discount
handling, tax breakdown, payment method, reconciliation check), asking
the executor to drop a trailing notes sheet inside the workbook or a
sidecar `reconcile_notes.md`.

§5 rebalanced: workbook shape 0.15 → 0.10 (-0.05); line-item coverage
0.15 → 0.10 (-0.05); store/date alignment 0.15 → 0.10 (-0.05); new
"Topic dimension coverage" anchor at +0.15. Final weights:
0.10 + 0.10 + 0.15 + 0.10 + 0.15 + 0.10 + 0.10 + 0.05 + 0.15 = 1.00.

Anchor scoring strict: 5/5 → 0.15, 4/5 → 0.05, ≤3/5 → 0.00. Anchor
phrases include German tax tokens (Mwst / USt) and German loyalty / promo
words (rabatt) so the realistic German receipt vocabulary is rewarded.
ground_truth.json gains `topic_dimensions` (5 keyword lists) plus
`min_dimensions_covered: 5`. score caps and success_threshold (0.90)
unchanged.

## Round 8 trim (2026-04-30) — per-receipt MwSt classification CP

Task measured at PASS 1.0 — one strict sub-checkpoint added to drop
ceiling to ~0.95. New 0.05 CP "Per-receipt MwSt rate classification"
requires line items in ≥2 of 3 receipts to be annotated with their
German VAT rate (7% reduced / 19% standard / 0%). Stepped scoring
3/3 → 0.05, 2/3 → 0.025, ≤1/3 → 0.00. To rebalance, Topic dimension
coverage trimmed 0.15 → 0.10 (-0.05) with proportionally tightened
stepped band (5/5 → 0.10, 4/5 → 0.03). Final weights:
0.10 + 0.10 + 0.15 + 0.10 + 0.15 + 0.10 + 0.10 + 0.05 + 0.10 + 0.05
= 1.00. Score caps and success_threshold (0.90) unchanged.

## Review pass (2026-04-30)

Applied global review rules from skill_usage_iter/review_record.md.

### Prompt rewrite (task YAML)

- Skill mention moved up: first paragraph now says "用工作区里的
  image-ocr skill ... 再用 xlsx-cn skill 整理成 Excel 报销表"
  (was: previously the skill mention sat at the bottom of paragraph 2
  "Please use the workspace's OCR and spreadsheet skills").
- All parentheses removed:
  - "(dm, kaisers, penny)" → folded into prose "分别来自 dm、Kaisers
    和 Penny 三家店".
  - "(store, date, source image filename, what it was, qty, unit price,
    line total in euros, and whether the line needs manual review)" →
    rewritten as natural Chinese sentences listing the columns inline.
  - "(rabatt, Kaisers Card / Penny club)" → removed; replaced with
    "会员折扣或者店内促销那种降价情况".
  - "(VAT / Mwst / USt)" → paraphrased as "按德国小票上常见的增值税
    分档".
  - "(cash, card, EC, Visa)" → paraphrased as "现金还是刷卡之类的什么
    方式付的".
  - "(matches / discrepancy / off by / rounding)" → paraphrased as
    "对不上的话写一下差在哪里、像不像是四舍五入造成的".
- Language rewritten in natural Chinese-style user voice (报销 / 月度
  对账 / 一句对账判断 / 两周之后 etc.) per task_require.md realism.
- Rubric anchor keywords no longer enumerated in prose — anchor phrases
  remain only in eval_rule §5 / GT, not surfaced to executor.

### Eval strictness

- "Topic dimension coverage" — was stepped 5/5 → 0.10, 4/5 → 0.03,
  ≤3/5 → 0.00. Tightened to **strict all-or-nothing**: all 5 → 0.10,
  any miss → 0.00. Removes the `≥4/5` partial-credit band.
- "Per-receipt MwSt rate classification" — was stepped 3/3 → 0.05,
  2/3 → 0.025, ≤1/3 → 0.00 with `min = 2`. Tightened to **strict
  all-or-nothing**: all 3 receipts → 0.05, any miss → 0.00. GT
  `min_receipts_with_mwst_classification` lifted 2 → 3 to match.
- All other CPs already strict (exactly 17 line-item rows; exactly 3
  summary / review-flag rows; printed total ±0.02 each; reconciliation
  diff ≤ 0.10 with formula references). No "≥X/Y" anchors remain.

### GT correctness verification

- Line-item counts: dm 5 + kaisers 6 + penny 6 = 17 (matches
  `expected_item_rows`). Verified by re-reading GT § store_summaries.
- Printed totals: dm €11.52, kaisers €12.38, penny €7.13 (unchanged
  from previous iteration; consistent with §4 of eval_rule).
- Three canonical receipts under sources/receipts/, exactly 3 store
  summaries, exactly 3 review-flag rows.
- Score caps (§6) unchanged; success_threshold 0.90 unchanged.

### §5 sum verification

0.10 + 0.10 + 0.15 + 0.10 + 0.15 + 0.10 + 0.10 + 0.05 + 0.10 + 0.05
= 1.00 ✓.
