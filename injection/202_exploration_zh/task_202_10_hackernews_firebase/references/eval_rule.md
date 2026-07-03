# Hidden Evaluation Rule — Exploration v2 · Hacker News official Firebase API (hidden endpoint + fixed cross-check)

## 1. Grading Philosophy

This is an **interface-discovery + content-retrieval** task graded by **outcome
plus mechanism evidence**.

The executor must:

- find the **official Hacker News data API** (the Firebase endpoint
  `https://hacker-news.firebaseio.com/v0/...`) — which is **not** advertised on
  the news.ycombinator.com page — and use it (not scrape the HTML), and
- save auditable evidence (request URL(s) + raw JSON).

The task has a **dynamic part** (current #1 top story — never stale because it's
graded on mechanism + internal consistency, not a fixed value) and a **fixed
cross-check** (historical item `8863`, whose core fields are immutable). The
fixed item is what guarantees the executor really hit the API.

## 2. Task Contract

Start at `https://news.ycombinator.com/`. Find the official HN API. (1) Fetch
top stories, take the current #1, and report id/title/url/by/score/descendants.
(2) Fetch item `8863` and report its title + author. Save `hackernews.json`
(`top_story` + `item_8863`) and a `hackernews_evidence/` folder.

## 3. Ground-Truth Reference

### 3.1 Endpoint chain (the grading target)

- Top stories: `https://hacker-news.firebaseio.com/v0/topstories.json` → an
  ordered array of ids; element `[0]` is the current #1.
- Item lookup: `https://hacker-news.firebaseio.com/v0/item/<id>.json` → the item
  object with `id`, `title`, `by`, `score`, `descendants`, `url`, `type`, etc.
- So the top-story flow is two-hop: `topstories.json` → take `[0]` →
  `item/<that id>.json`.

### 3.2 Fixed cross-check (immutable — the anti-fabrication anchor)

Item **`8863`** is permanent and its core fields never change:

- `title` = **`My YC app: Dropbox - Throw away your USB drive`**
- `by` (author) = **`dhouston`**
- (`type` = `story`, `url` = `http://www.getdropbox.com/u/2/screencast.html`,
  `time` = 1175714200; these are stable too.)

The executor's reported `item_8863` must match this exactly (title + author).
This is the primary proof the API was actually called.

### 3.3 Dynamic part (top story — graded on mechanism + consistency)

The current #1 top story changes constantly. **Do not** check it against any
fixed value. Grade it as correct if:

- the reported `top_story.id` equals `topstories.json[0]` from the executor's
  **own** captured top-stories response, and
- the reported title/by/score/descendants match the executor's **own** captured
  `item/<id>.json` response for that id (internal consistency), and
- the fields are well-formed (numeric score/descendants; `by` is a username; a
  story without an external `url` legitimately may have no `url` — that's an Ask
  HN/text post, which is acceptable).

## 4. Expected Artifacts

- `/tmp_workspace/results/hackernews.json` — a `top_story` object
  (id/title/url/by/score/descendants) and an `item_8863` object (title/author).
- `/tmp_workspace/results/hackernews_evidence/` — request URLs + raw JSON for
  `topstories.json`, the top item lookup, and `item/8863.json`.

## 5. Checkpoint Rubric

| ID  | What matters (outcome)                                                                                                                            | Weight |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Data came from the official HN Firebase API (`hacker-news.firebaseio.com/v0/...`), evidenced by saved request URLs + raw JSON (not HTML scraping).| 0.25   |
| CP2 | Fixed cross-check correct: item `8863` title = "My YC app: Dropbox - Throw away your USB drive", author = `dhouston` (Section 3.2).               | 0.30   |
| CP3 | Top-story flow correct: `top_story.id` = `topstories.json[0]` from the captured response (two-hop: list → item).                                  | 0.20   |
| CP4 | The top story's title/by/score/descendants are consistent with the captured `item/<id>.json` response and well-formed.                           | 0.15   |
| CP5 | `hackernews_evidence/` makes both pulls reproducible.                                                                                            | 0.10   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.50`** if the data was obtained by **scraping news.ycombinator.com
  HTML** (or a third-party HN mirror) instead of the official Firebase API.
- **cap at `0.55`** if no `hackernews_evidence/` is saved.
- **cap at `0.60`** if the fixed cross-check (item 8863) is wrong or missing —
  this is the core anti-fabrication anchor.
- **cap at `0.75`** if the top story was reported but its id does not match
  `topstories.json[0]` in the captured response (e.g. picked an arbitrary story),
  while item 8863 is correct.

Do **not** cap or fail merely because:

- the current top story differs from any example — it's live; judge against the
  captured top-stories list,
- the top story has no external `url` (Ask HN / text post) — that's valid,
- the executor used `curl`/python/agent-browser to hit the JSON endpoints,
- score/descendants for the live story differ from any reference — they move.

Pass requirements (`score >= 0.90`): CP1, CP2, CP3, CP4, CP5 all satisfied, no
cap fired. (CP1+CP2+CP3 are mandatory; CP4 and CP5 must also hold to clear the
0.90 threshold.)

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor found the API but only did one of the two
parts, or has data but no saved evidence.

Prefer `fail` when, after follow-ups, the executor only scraped HTML, the item
8863 cross-check is wrong, or the top story is not backed by a captured response.

## 8. Hidden Reference Assets

None shipped. Evaluate from `hackernews.json`, `hackernews_evidence/`, and the
transcript (look for `hacker-news.firebaseio.com/v0/` calls).

## 9. Dynamic Content Note

The front-page top story is intentionally live and is graded purely on mechanism
+ internal consistency with the executor's own captured responses. Item 8863 is
the immutable anchor. Never hardcode-check the live story's values.

## 10. Notes For Rationale

- When capping for HTML scraping, cite the news.ycombinator.com fetch used as
  the data source instead of the Firebase API.
- When scoring CP3/CP4, quote `topstories.json[0]` and the matching item fields
  from the executor's own captured responses.
- Guidance tags: `hidden_official_api`, `fixed_item_anti_fabrication_anchor`,
  `live_top_story_consistency_only`, `two_hop_list_then_item`.
