# Hidden Evaluation Rule — Exploration v2 · Offline monitor shortlist with conflicting traps (objective)

## 1. Grading Philosophy

This is a **candidate-selection / filtering** task graded by **objective set
matching plus correct trap diagnosis**.

It is the offline successor to the v1 live-Amazon monitor task (which scored ~0.59
and depended on flaky live pages). The catalog is shipped and frozen, so the
answer is a deterministic set. Each product has a `listing` summary and an
authoritative `detail` page; several traps are only visible in the detail page,
so a listing-only reader will wrongly accept them. The buyer's requirements are
all objectively checkable, and **exactly three** products qualify.

## 2. Task Contract

Shortlist all monitors matching: ~27" (26-28), true 4K (3840x2160), USB-C VIDEO
(DP Alt Mode, not charging-only), NEW direct purchase, new price ≤ $500, ships
to US, in stock. Detail page is authoritative over the listing. Catalog at
`/tmp_workspace/clawbench/sources/catalog/`. Save `monitor_shortlist.json`,
`monitor_rejections.json`, `monitor_method.json`. Offline.

## 3. Ground-Truth Reference (answer key)

**Qualifying set (exactly): {M01, M04, M08}.**

| id | verdict | reason |
| -- | ------- | ------ |
| M01 | QUALIFY | Dell 27" 4K, USB-C DP Alt Mode, new $449, US, in stock |
| M04 | QUALIFY | LG 27" 4K, USB-C 90W DP Alt Mode, new $479, US, in stock |
| M08 | QUALIFY | ASUS ProArt 27" 4K, USB-C DP Alt Mode, new $399, US, in stock |
| M02 | REJECT | USB-C is charging/data only, NO video (the USB-C trap) |
| M03 | REJECT | 2560x1440 (QHD), not true 4K |
| M05 | REJECT | $429 is a used/like-new price; NEW price $560 > budget; third-party reseller |
| M06 | REJECT | 32", not ~27 |
| M07 | REJECT | ships EU only, not deliverable to US |
| M09 | REJECT | new price $529 > $500 |
| M10 | REJECT | $389 is a renewed price (new $499) AND out of stock |

**Detail-page-only traps:** M02 (usb-c), M03 (resolution), M05 (price type), M10
(renewed/stock) can only be caught by reading the detail page — a listing-only
read wrongly accepts them.

## 4. Expected Artifacts

- `/tmp_workspace/results/monitor_shortlist.json`
- `/tmp_workspace/results/monitor_rejections.json`
- `/tmp_workspace/results/monitor_method.json`

## 5. Checkpoint Rubric

| ID  | What matters (objective)                                                                                                          | Weight |
| --- | ----------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | The shortlist is exactly **{M01, M04, M08}** — all three present, no trap product included.                                      | 0.40   |
| CP2 | Each of the seven rejected products is rejected with the CORRECT specific trap reason (Section 3).                                | 0.30   |
| CP3 | The detail-vs-listing authority rule is applied: the detail-only traps (M02/M03/M05/M10) are caught from the detail page.         | 0.15   |
| CP4 | Each shortlisted item's pass is evidenced field-by-field (resolution, usb-c video, condition, price, US, stock).                  | 0.10   |
| CP5 | Method artifact shows how the requirements + authority rule were applied (reproducible).                                         | 0.05   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.55`** if any trap product is included in the shortlist (the core
  failure). Each wrongly-included trap is a serious error.
- **cap at `0.55`** if `monitor_shortlist.json` is missing.
- **cap at `0.70`** if the shortlist is a strict subset/superset of {M01,M04,M08}
  (e.g. missed M04, or added one extra) — partial correctness.
- **cap at `0.75`** if the shortlist is right but rejections lack specific
  per-product trap reasons (just "doesn't match").
- **cap at `0.80`** if a detail-only trap (M02/M03/M05/M10) was rejected for a
  vague/wrong reason indicating the detail page wasn't actually used.
- **cap at `0.30`** if the executor used the network (offline task).

Do **not** cap or fail merely because:

- the executor orders the shortlist differently or adds extra evidence fields,
- the executor notes that M05/M10 might qualify IF bought new (correct nuance) as
  long as it still rejects them at the given price/condition/stock,
- the executor uses python/jq to filter — any real per-detail evaluation is fine.

Pass requirements (`score >= 0.90`): CP1 (exact set), CP2 (correct trap reasons),
CP3 (detail authority applied), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor has evaluated some products but not all, or
has the shortlist but incomplete rejection reasons.

Prefer `fail` when, after follow-ups, the shortlist includes trap products with
no correction, or the executor judged from listings only and never used detail
pages.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — qualifying set + per-product trap reasons.

## 9. Dynamic Content Note

None — frozen offline catalog; deterministic answer set.

## 10. Notes For Rationale

- When capping at 0.55 for an included trap, name the product and its trap.
- When scoring CP3, confirm M02/M03/M05/M10 were caught via detail-page fields,
  not the listing.
- Guidance tags: `exact_set_selection`, `detail_overrides_listing`,
  `usb_c_video_not_charging`, `price_type_traps`, `offline_deterministic`.
