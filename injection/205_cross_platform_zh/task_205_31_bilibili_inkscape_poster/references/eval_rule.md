# Hidden Evaluation Rule — task_205_31_bilibili_inkscape_poster

## 1. Grading Philosophy

Grade on whether the executor (a) drove a real **browser** flow against
each Bilibili video page (chromium-headless screenshot + HTML scrape +
htmlq extraction), (b) downloaded the 3 cover thumbnails via plain
`curl` from the URLs extracted from those rendered pages, AND (c)
produced a **single composite Inkscape-renderable SVG poster** that
embeds the 3 thumbnails as real `<image>` elements with title/UP/BV/
duration text overlays around each. Difficulty is in the chain — a
`<text>`-only SVG with no `<image>` elements fails, and any trace of
`yt-dlp` against bilibili.com instead of the browser flow caps the
score (the user explicitly asked for a browser-based pipeline because
opening the page is the most "user-eyes" way to read the metadata).

## 2. Task Contract

Required deliverables under `/tmp_workspace/results/`:

- `poster.svg` — single XML root `<svg>`, viewBox / width / height
  ≥ 800×600, containing:
  * **exactly 3 `<image>` elements** (namespace-agnostic — counted as
    `{http://www.w3.org/2000/svg}image` or plain `image`), each with a
    non-empty `href` or `xlink:href` attribute (relative file path or
    `data:image/...` URI both accepted);
  * for each of the 3 BV IDs, the visible text (concatenated `<text>`
    + `<tspan>` content) contains: BV ID, uploader name, formatted
    duration `Xm Ys`, AND the title (substring match, case-sensitive
    for ASCII / Chinese mix);
  * a "longest"-style highlight marker (any of `最长`, `★`, `LONGEST`,
    `longest`, `MAX`).
- `poster.png` — Inkscape-rendered (or any tool that emits valid PNG)
  output, magic bytes `\x89PNG`, width ≥ 800 px AND height ≥ 600 px.
- `thumbs/` — directory with the 3 raw thumbnails downloaded via
  curl from the Bilibili CDN URLs extracted out of each page's HTML,
  filename `<bv_id>.{jpg,jpeg,png,webp}`. Each must be a valid image
  of ≥ 1 KiB.
- `browser_screenshots/` — directory with 3 PNG screenshots produced
  by chromium-headless against `https://www.bilibili.com/video/<bv>/`,
  filename `<bv_id>.png`. Each must be a valid PNG (`\x89PNG` magic),
  width ≥ 1024 AND height ≥ 600. Captures that the executor really
  drove a browser instead of hitting JSON APIs.

There is NO snapshot file, NO mock, NO populate step. The eval
deliberately drops the JSON-API path — the user wants a browser flow.

## 3. Source-Selection Rules

- **Browser-rendered HTML** (preferred / required):
  * `chromium --headless --disable-gpu --no-sandbox
    --window-size=1280,800 --hide-scrollbars --screenshot=<out.png>
    https://www.bilibili.com/video/<bv>/`
  * `curl -sL --compressed -A "<modern UA>"
    https://www.bilibili.com/video/<bv>/` (Bilibili gzip-encodes the
    response; `--compressed` is required to get readable HTML).
- **HTML extraction**:
  * `htmlq 'meta[itemprop=author]' --attribute content` → uploader
  * `htmlq 'meta[itemprop=image]'  --attribute content` → thumbnail URL
  * `htmlq 'title'`                                       → title
  * grep / jq for `"duration":` in the embedded `__INITIAL_STATE__`
    JSON to recover seconds.
- **Thumbnail download**: plain `curl -sLo thumbs/<bv>.<ext> "<image_url>"`
  (Bilibili thumbnails are public, no auth required).
- **Inkscape (1.x)** for SVG composition + PNG export
  (`inkscape --export-type=png poster.svg`).

NO snapshot under `/tmp_workspace/clawbench/` is used or expected.
Bilibili's CDN currently serves cover thumbnails as `.jpg` for some
videos and `.png` for others. The eval accepts either extension.
The duration value parsed out of the embedded JSON may be 1 second
lower than the API's; both accepted (281/280, 772/771, 297/296).

## 4. Ground-Truth Anchors

For BV1tt411a7Tt: title `"宾利 AGAINST ALL ODDS 逮虾户4分14秒52"`,
uploader `"BLACK-Android"`, duration 281 / 280, formatted `"4m 41s"`.

For BV1Vt411X7sa: title `"使命召唤15-Nate自瞄手枪已上线"`, uploader
`"Prophet47"`, duration 772 / 771, formatted `"12m 52s"`.
**This is the longest video.**

For BV1ev411s7QU: title `"TF2  进阶的练习"` (substring `"TF2"`
sufficient because of internal whitespace ambiguity), uploader
`"最可靠的护盾"`, duration 297 / 296, formatted `"4m 57s"`.

## 5. Checkpoint Rubric

- 0.15 — `browser_screenshots/` directory exists AND for each of the 3
  BV IDs there is a file `<bv_id>.png` of valid PNG magic bytes
  (`\x89PNG`), width ≥ 1024 AND height ≥ 600 (verify via Pillow /
  ImageMagick / `file`). Empty / placeholder PNGs (< 5 KiB) fail.
- 0.15 — `thumbs/` directory exists AND for each of the 3 BV IDs there
  is at least one file matching `<bv_id>.*` (case-insensitive) of
  filesize ≥ 1 KiB AND valid image magic bytes (JPEG `\xff\xd8\xff`,
  PNG `\x89PNG`, or WEBP `RIFF...WEBP`).
- 0.20 — `poster.svg` exists, parses as XML with root `<svg>`, AND
  contains **exactly 3 `<image>` elements** (count via XML parse,
  namespace-agnostic), each with a non-empty `href` / `xlink:href`
  attribute. SVG canvas (root `width`+`height` or `viewBox`) ≥ 800×600.
- 0.25 — `poster.svg` text-content (concatenated `<text>` + `<tspan>`)
  contains, for each of the 3 BV IDs: the BV ID itself, the uploader
  string from ground truth, the formatted duration `Xm Ys`, AND a
  title substring (≥ 3 ASCII chars or ≥ 2 CJK chars from the canonical
  title). Also contains a "longest"-style highlight marker.
- 0.15 — `poster.png` exists, magic bytes `\x89PNG`, width ≥ 800 px
  AND height ≥ 600 px (verify via Pillow / ImageMagick / `file`).
- 0.10 — Identifies the longest video correctly: the SVG explicitly
  flags `BV1Vt411X7sa` with the highlight marker (the marker text is
  near or in the same `<g>` group as the `BV1Vt411X7sa` text, OR there
  is a textual statement like `"最长: BV1Vt411X7sa"` anywhere in the
  SVG concatenated text).

## 6. Scoring Policy / Score Caps

- Trace shows zero `chromium` invocation AND `browser_screenshots/` is
  empty / missing → cap browser-screenshot checkpoint at 0 AND total
  at 0.70 (the user explicitly required the browser flow).
- Trace shows `yt-dlp <bilibili-url>` against bilibili.com (other
  domains are fine) AND the executor never invoked chromium against
  bilibili → 0.55 cap (replaced the requested browser flow).
- `thumbs/` empty even though browser screenshots exist → cap thumb
  checkpoint at 0.
- `poster.svg` contains 0 `<image>` elements → cap §5 image-element
  checkpoint at 0 (composition isn't real).
- Poster is 3 separate SVGs instead of one composite → 0.50.
- Trace shows zero `inkscape` invocation AND `poster.png` was produced
  by another tool but `poster.svg` itself contains the 3 `<image>`
  elements with valid hrefs → no cap (rendering tool is fungible).
- Output fabricates duration / uploader values not derivable from the
  live Bilibili page → 0.40.

Pass requires ≥ 0.90 — i.e. all 6 checkpoints satisfied OR 5 satisfied
plus near-miss on the longest-highlight check.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — executor stops.
- **Continue** 0.50–0.89 — supervisor may request one follow-up to
  add the missing browser screenshot, fix the SVG canvas size, or
  re-render to PNG at the right dimensions.
- **Fail** < 0.50 — no further follow-ups.

## 8. Hidden Reference Assets

Supervisor-only:
- `references/eval_rule.md` (this file)
- `references/ground_truth.json`

## 9. Dynamic Content Note

All anchors are immutable — they reference 3 archived single-part
Bilibili uploads. Play counts, danmaku counts, like / coin / share
counts ARE dynamic and intentionally NOT in ground_truth.

If Bilibili rate-limits the page (returns an HTML challenge or a
geofence interstitial), record `infra_error` and avoid penalising —
the executor is still expected to retry once with a different UA, but
single failures must not zero the score. If a video is removed
(`code: -404` or the page renders an "已失效" banner), record
`infra_drift`, allow degraded scoring on the missing video, but still
require the others. If the served thumbnail format changes (e.g. JPG →
WEBP), accept the new format as long as image magic bytes and
dimensions are valid.

If chromium-headless is genuinely unavailable in the executor
environment (`chromium: command not found`), the supervisor MUST
distinguish "executor failed" from "no browser installed" — record
`infra_error` and do not penalise. The task-setup install.sh must
prove chromium-driver was installed; absence of chromium during eval
is an infrastructure bug, not an agent failure.
