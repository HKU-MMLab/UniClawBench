# Reference Video Selection

Hidden benchmark snapshot target:

- creator: `kate elisabeth`
- selected video: `YQOhJE2pA9E`
- title: `How much I Spend £ in a Week as a 25 year-old Living in London 🇬🇧`
- published date: `2025-09-21`

Older but relevant candidate:

- `Nk4ZeczQGwk`
- `What I Spend £ in a Week as a 25 year old Living and Working in London 🇬🇧 (bills, transport, food)`
- published `2025-07-06`

Reference output expectation:

- select the `YQOhJE2pA9E` video as the snapshot-latest matching upload
- recover the 18 canonical itemized spend rows where possible; a passing-level
  output should match at least 16 with accepted GBP amounts
- report the GBP 520.68 itemized total, the GBP 542.94 creator-stated grand
  total, and reconcile the GBP 22.26 difference as unitemized or unconfirmed
- produce the required CSV, markdown, pie chart, and one saved evidence frame per
  CSV spend row
- keep the category pie chart consistent with the CSV and do not invent named
  purchases for the unitemized remainder
- ground rows in video playback evidence; visual-overlay rows need readable
  screenshots/keyframes rather than transcript-only support

This task still requires runtime extraction from playback; this hidden file is
mainly a selection-grounding reference.
