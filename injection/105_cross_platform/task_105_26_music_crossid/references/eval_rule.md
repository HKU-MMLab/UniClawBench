# Hidden Evaluation Rule — task_105_26_music_crossid

## 1. Grading Philosophy

Grade on whether the executor identified THREE songs from three lyrics
fragments and cross-validated each on NetEase Cloud Music and YouTube.
The user's main goal is "tell me which songs these are AND whether
the metadata across platforms agrees on duration".

Anchor checks against `ground_truth.json` — the three songs (光年之外 /
浮夸 / 倔强) have stable, immutable platform IDs. Five semantic
checkpoints, weights sum 1.0.

## 2. Task Contract

The user wants three songs identified from lyric fragments, then
cross-validated metadata from NetEase + YouTube. There is NO snapshot,
NO mock, NO populate step. Live API calls required.

Expected songs:
- A "缘分让我们相遇乱世以外..." → 光年之外 / G.E.M.邓紫棋
- B "人潮内愈文静愈变得不受理睬" → 浮夸 / 陈奕迅
- C "我和我最後的倔強..." → 倔强 / 五月天

Deliverables under `/tmp_workspace/results/`:
- A JSON file (`song_identification.json` or similar) with the 3 songs
- A markdown report (`report.md` or similar)

Filenames may vary; supervisor uses flexible matching.

## 3. Source-Selection Rules

Live APIs:
- NetEase via ncm-cli:
  `ncm-cli search song --keyword "<query>" --limit <N> --output json`
  (ncm-cli is pre-installed and pre-authenticated by install.sh;
  the executor can also use `ncm-cli song detail` or the public
  `music.163.com/api/search/get` endpoint — any method that returns
  the correct `originalId` / `song_id` is acceptable)
- YouTube via yt-dlp:
  `yt-dlp ytsearch1:<query> --skip-download --print '...'`

NO snapshot file. NO mock service.

## 4. Ground-Truth Anchors

Song 1 — 光年之外 / G.E.M.邓紫棋:
- netease.song_id == 449818741, duration_ms == 235505,
  album == "光年之外"
- youtube.video_id == "T4SimnaiktU", channel == "GEM鄧紫棋",
  duration_seconds == 236, upload_date == "20161230"

Song 2 — 浮夸 / 陈奕迅:
- netease.song_id == 66282, duration_ms == 283520, album == "U87"
- youtube.video_id == "0xFFGzZq75w", channel == "Eason Chan",
  duration_seconds == 284, upload_date == "20190110"

Song 3 — 倔强 / 五月天:
- netease.song_id == 386175, duration_ms == 261618,
  album == "神的孩子都在跳舞"
- youtube.video_id == "R2s-H_crYkc", channel == "滾石唱片 ROCK RECORDS",
  duration_seconds == 263, upload_date == "20120417"

Tightest cross-platform duration diff: 浮夸 (≈ 0.48s).
All three should report `match_status == "match"` (diff < 5s).

## 5. Checkpoint Rubric

Five semantic checkpoints, weights sum 1.0.

- 0.20 — **All 3 songs identified correctly.** Output JSON has 3
  entries with `song_name` (or equivalent field) covering the set
  {光年之外, 浮夸, 倔强}. AND each entry's artist field contains
  (case-insensitive, partial) the canonical artist name or accepted
  alias:
    * 光年之外 → contains any of "G.E.M.", "邓紫棋", "鄧紫棋", "GEM"
    * 浮夸 → contains any of "陈奕迅", "陳奕迅", "Eason"
    * 倔强 → contains any of "五月天", "Mayday"

- 0.25 — **NetEase IDs and metadata correct for all 3.** All three
  NetEase `song_id` values match exactly:
    * 光年之外 → 449818741
    * 浮夸 → 66282
    * 倔强 → 386175
  Partial credit: 0.08 per correct song_id. Bonus 0.01 if all 3
  album fields also match (光年之外 / U87 / 神的孩子都在跳舞).

- 0.25 — **YouTube IDs and metadata correct for all 3.** All three
  YouTube `video_id` values match exactly (T4SimnaiktU, 0xFFGzZq75w,
  R2s-H_crYkc) AND each `duration_seconds` within ±2 of (236, 284, 263).
  Partial credit: 0.08 per correct video_id; remaining 0.01 if all
  upload_dates match (20161230, 20190110, 20120417).

- 0.15 — **Cross-platform duration validation.** For each of the 3
  songs, the output records something like `duration_diff_seconds`
  (or the user can derive it from the netease and youtube duration
  fields), and the recorded match status / verdict reflects "all 3
  match" (each diff < 5s). The check itself must be present — not
  just two duration fields without a comparison.

- 0.15 — **Report exists with the key observation.** A markdown file
  under results/, 250–700 zh chars; mentions all three song names
  (光年之外 / 浮夸 / 倔强); mentions each canonical artist; and
  identifies which song has the tightest cross-platform duration
  match (correct answer is 浮夸 with ≈ 0.48s diff; 光年之外 ≈ 0.5s
  is also accepted because they're within rounding of each other).

## 6. Scoring Policy / Score Caps

Partial credit. Caps:

- No JSON results AND no report → 0.20.
- Output fabricates a different song / artist not derivable from any
  of the three lyrics fragments → 0.40.
- Only 1 of 3 songs has any usable data → 0.50.
- `$NCM_APP_ID`, `$NCM_PRIVATE_KEY`, `$NCM_TOKENS_ENC`, or
  `$NCM_DEVICE_JSON` value emitted to user-visible output → 0.30.
- Trace shows zero ncm-cli / curl / yt-dlp calls (synthetic data
  only) → 0.40.

Pass requires checkpoints 1, 2, 3 (identification + NetEase ID +
YouTube ID) all satisfied.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — executor should stop.
- **Continue** 0.50–0.89 — supervisor may request one follow-up
  (typically a wrong YT video_id from a fan upload).
- **Fail** < 0.50 — no further follow-ups.

## 8. Hidden Reference Assets

Supervisor-only:
- `references/eval_rule.md` (this file)
- `references/ground_truth.json`

## 9. Dynamic Content Note

All anchors immutable — NetEase song_ids 449818741 / 66282 / 386175
have been live with constant metadata for years; YouTube videos
T4SimnaiktU / 0xFFGzZq75w / R2s-H_crYkc have constant
title/channel/duration/upload_date. View counts and like counts are
dynamic and intentionally NOT in ground_truth.

If NetEase API rate-limits or returns 503, supervisor records
`infra_error` and avoids penalising. ncm-cli is pre-installed and
pre-authenticated by install.sh; the executor does NOT need to run
`ncm-cli configure` or `ncm-cli login` themselves.
