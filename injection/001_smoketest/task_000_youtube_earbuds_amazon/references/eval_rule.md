# Hidden Evaluation Rule — YouTube Relevance + 4K Best Sleep Earbuds -> Amazon Price

## 1. Grading Philosophy

This task is graded by **outcomes**, not by process.

The supervisor cares about whether the executor:

- ended up with the correct product (`Soundcore Sleep A30`) as the
  `Best Sleep Earbuds` winner,
- opened the matching Amazon product page and captured its current state,
- saved the conclusion and supporting screenshots.

The supervisor does **not** care about how the executor reached the right
answer. Chapters in the video description, timestamp list, affiliate
links in the description block, an external article that names the same
winner, etc., are all acceptable grounding as long as the final product
identification is correct.

Query text, ranking order, and the `4K` filter are still checked because
they define which video is the "primary source", but small procedural
deviations (e.g. the query is typed in a slightly different casing, the
executor scrolled briefly before clicking the first 4K result) are **not**
penalized as long as the right video ends up open.

## 2. Task Contract (for reference)

The public task asks the executor to:

1. Search YouTube for the query `best wireless earbuds 2025 review`
2. With default relevance ordering and the `4K` filter, open the first
   result
3. Identify which earbud wins the video's `Best Sleep Earbuds` category
4. Open a matching Amazon product page for that earbud, and note its
   current state (price if visible, or "currently unavailable" / an
   external price citation if no on-page price is shown)
5. Save the final conclusion, the Amazon link, and supporting screenshots
   under `/tmp_workspace/results/`

## 3. Hidden Snapshot Captured On 2026-04-14

- YouTube query: `best wireless earbuds 2025 review`
- 4K filter search parameter: `sp=EgJwAQ%3D%3D`
- first-ranked 4K result:
  - title: `2025 Earbuds Awards - Unexpected Winners!`
  - channel: `Mike O'Brien`
  - video id: `4F0289jmqQs`
  - URL: `https://www.youtube.com/watch?v=4F0289jmqQs`
- Correct `Best Sleep Earbuds` winner: `Soundcore Sleep A30`
- Amazon product family: `Soundcore Sleep A30 Special by Anker`
  - hidden snapshot ASIN: `B0FYFV2HLM`
  - hidden snapshot URL: `https://www.amazon.com/dp/B0FYFV2HLM/`
  - hidden snapshot price: `$199.99`

Accepted answer variants:

- `Soundcore Sleep A30`
- `Sleep A30`
- `soundcore Sleep A30 by Anker`

Reject these as final answers:

- `Soundcore Sleep A20` (last year's model; the video explicitly mentions
  it as context but this year's winner is A30)
- `Sony WF-1000XM5`, `Bose QuietComfort Ultra`, `AirPods Pro 3`, any
  non-sleep-category winner

## 4. Checkpoint Rubric

| ID | What matters (outcome) | Weight |
| --- | --- | --- |
| CP1 | The primary source that the executor grounds the answer on is the right video (id `4F0289jmqQs`, title `2025 Earbuds Awards - Unexpected Winners!`). The visible evidence can be a screenshot of the video page, the URL in a transcript, or the title echoed in a saved artifact. | 0.20 |
| CP2 | The `Best Sleep Earbuds` winner identified in the saved conclusion is `Soundcore Sleep A30` (any accepted variant above). | 0.30 |
| CP3 | An Amazon product page for the Soundcore Sleep A30 product family is opened. The exact ASIN does not have to match the hidden snapshot; any legitimate A30 product page counts. | 0.15 |
| CP4 | The current state of the Amazon page is captured — an on-page price, **or** a clear page state note such as `Currently unavailable` / `Out of stock`, **or** a defensible price citation from an external source (search snippet, article) tied to the same product. | 0.15 |
| CP5 | Final artifacts are saved coherently under `/tmp_workspace/results/`: a conclusion (text or markdown), an Amazon link or screenshot, and at least one supporting screenshot tying the run together. | 0.20 |

Total full score: `1.00`.

## 5. Scoring Policy

Apply the checkpoint weights above. Caps (only the strong mismatches):

- cap at `0.30` if the executor answers with a winner from a different
  category (e.g. travel / ANC / workout / premium / budget)
- cap at `0.50` if the executor answers with `Sleep A20` instead of
  `Sleep A30`
- cap at `0.60` if the Amazon page is clearly the wrong product family
  (e.g. a Sony / Bose page instead of Soundcore Sleep A30)
- cap at `0.80` if the executor's grounded primary source is the wrong
  video (different channel / different video id) — but partial credit
  still applies when the final product answer is right
- cap at `0.90` if the saved artifacts are missing the conclusion text
  or there is no supporting screenshot at all

Do **not** cap or fail the run merely because:

- the executor inferred the winner from the video description / chapter
  list / affiliate-link block rather than from the video body itself
- the executor used an external article or search snippet alongside the
  video to disambiguate the product name
- the Amazon page shows `Currently unavailable` (Amazon's own state —
  the executor should note it, which still satisfies CP4)
- the executor's Amazon page is A30 but a different ASIN than the hidden
  snapshot

Pass requirements (`score >= 0.95` and `verdict = pass`):

- CP2 is clearly satisfied (Sleep A30 named in the conclusion)
- CP3 and CP4 are both satisfied (right product family Amazon page + a
  page-state capture or defensible external price)
- CP5 is satisfied (conclusion + link + at least one screenshot under
  `results/`)

## 6. Continue vs Fail Guidance

Prefer `continue` when:

- the executor has opened the right video but has not yet written the
  product name into a saved conclusion file
- the executor has identified Sleep A30 but has not yet opened or captured
  the Amazon page
- the Amazon page shows `Currently unavailable` and the executor is still
  looking for an external price to cite (optional — the page state alone
  already satisfies CP4)
- the conclusion file is saved but missing the Amazon link or supporting
  screenshots

Prefer `fail` when:

- the executor answers with `Sleep A20` (this is the disambiguation the
  task specifically tests)
- the executor answers with a winner from a different category
- the executor uses the wrong product family on Amazon (e.g. a Sony or
  Bose earbud page)
- the executor finished with no conclusion file at all, and there are no
  more followups available

Otherwise prefer `continue`.

## 7. Dynamic Content Note

Amazon pricing is dynamic. The hidden `$199.99` snapshot is a grounding
reference only. Judge CP4 against whatever the executor's own visible
Amazon page showed on this run, not against `$199.99` specifically.

## 8. Hidden Reference Assets

The following hidden screenshots are available to the supervisor as
cross-checks:

- `youtube_search_relevance_4k_top_result_2026-04-14.png`
- `youtube_video_page_2025_earbuds_awards_2026-04-14.png`
- `youtube_video_best_sleep_frame_2026-04-14.png`
- `amazon_product_page_soundcore_sleep_a30_2026-04-14.png`

Use them to verify the identity of the primary video and the product
family; they are **not** the only acceptable evidence sources for the
executor.
