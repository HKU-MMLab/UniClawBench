# Hidden Evaluation Rule — task_205_27_sketch_ui_replica

## 1. Grading Philosophy

Grade on whether the executor delivered a real cross-platform UI-replica
pipeline anchored on the live, visually-rich Python homepage
**https://www.python.org/**: (a) chromium-headless screenshot of the
live page, (b) htmlq/curl extraction of the page's actual UI primitives
(title, hero heading, nav link, color), (c) a JSON design spec that
wires those primitives into a sketch-cli–compatible
`pages → artboards → layers` tree, (d) a real `.sketch` artifact
produced by the sketch-cli build command. Difficulty is in the chain —
a screenshot alone, or an empty .sketch shell, fails. python.org's
homepage <title> has been "Welcome to Python.org" for many years, the
top nav contains stable site-internal links (`/downloads/`, `/doc/`,
`/community/`, `/about/`, `/jobs/`, etc.), and the hero carousel
features a small set of long-stable headings (e.g.
"Functions Defined", "Compound Data Types", "Intuitive Interpretation",
"All the Flow You'd Expect"). Anchors are tight on the title and on
the requirement that any of the canonical hero headings appear; the
color value is loose because palette hex codes drift.

## 2. Task Contract

Required deliverables under `/tmp_workspace/results/`:

- `source_screenshot.png` — chromium-headless screenshot of
  https://www.python.org/, valid PNG (magic bytes `\x89PNG`),
  width ≥ 1024 AND height ≥ 600.
- `ui_spec.json` — JSON document with two top-level objects:
    * `extracted` — the four facts pulled out of python.org's HTML:
      `page_title` (must contain `"Python.org"` OR `"Welcome to Python"`,
      case-insensitive — the canonical full title is
      `"Welcome to Python.org"`), `hero_heading` (must contain ANY of
      the canonical hero-carousel slide titles: `"Functions Defined"`,
      `"Compound Data Types"`, `"Intuitive Interpretation"`,
      `"All the Flow You'd Expect"`, `"Quick & Easy to Learn"`, OR any
      `<h1>` text actually present on the page), `nav_link_href` (must
      match an internal path like `/downloads/`, `/doc/`, `/community/`,
      `/about/`, `/jobs/`, `/psf/`, `/success-stories/`, `/blogs/`,
      `/events/` — substring match), `primary_color` (any plausible CSS
      color string, e.g. `#fff`, `#3673a5`, `#004d7a`, `#006dad`, etc).
    * `sketch_spec` — a sketch-cli–compatible design spec: top-level
      `pages` array, each page has `artboards` array, each artboard
      has `layers` array. At least one `text` layer's `value` field
      contains the substring `"Python"` (case-sensitive).
- `replica.sketch` — produced by sketch-cli (`node
  src/cli.js build -i ... -o ...`); the file is a valid ZIP archive
  (PK magic bytes `\x50\x4b`), filesize ≥ 5 KiB, and unzipping it
  yields at least one JSON entry whose decoded text contains
  `"Python"` (so the brand string actually made it through).
- `comparison.md` — Chinese narrative, mentions `python.org`, mentions
  the word `replica` / `复刻` (or `Sketch`), and references at least
  one concrete UI element extracted (heading text / color / layout /
  nav / hero).

## 3. Source-Selection Rules

Canonical sources are LIVE:
- Chromium screenshot: `chromium --headless --disable-gpu --no-sandbox
  --window-size=1280,800 --screenshot=... https://www.python.org/`
- HTML fetch: `curl -sL --compressed https://www.python.org/`
  (python.org serves gzip by default; without `--compressed` curl
  returns binary).
- HTML extraction: `htmlq` (CSS selectors) on the curl output.
- .sketch generation: `node /opt/cli-anything/sketch/agent-harness/src/cli.js
  build --input <spec.json> --output replica.sketch`.

NO snapshot file exists. NO mock service. No API key required —
sketch-cli is a Node.js library, python.org is a public website with
no auth wall.

## 4. Ground-Truth Anchors

python.org's homepage (verified 2026-05-03):
- `<title>` literal → `Welcome to Python.org`
- Hero carousel `<h1>` text (any of, long stable):
  `Intuitive Interpretation`, `Compound Data Types`,
  `All the Flow You'd Expect`, `Functions Defined`,
  `Quick & Easy to Learn`
- Top nav internal hrefs (any of): `/downloads/`, `/doc/`,
  `/community/`, `/about/`, `/jobs/`, `/psf/`, `/success-stories/`,
  `/blogs/`, `/events/`
- Footer: `Copyright ©2001-YYYY.` followed by `Python Software
  Foundation`, `Legal Statements`, `Privacy Notice` link
- Style sheet: `/static/stylesheets/style.<hash>.css` (hash drifts
  per release)
- Color palette includes (drifting): `#fff`, `#3673a5`, `#006dad`,
  `#004d7a`

Structured anchors at `references/ground_truth.json`.

## 5. Checkpoint Rubric

- 0.14 — `source_screenshot.png` exists, valid PNG (magic bytes
  `\x89PNG\r\n\x1a\n`), width ≥ 1024 AND height ≥ 600 (verify via
  Pillow / `file` / ImageMagick).
- 0.20 — `ui_spec.json` parses; `ui_spec.extracted.page_title`
  contains `"Python.org"` OR `"Welcome to Python"` (case-insensitive
  substring); `extracted.hero_heading` contains ANY of the canonical
  hero slide titles listed in §4 (case-sensitive substring) OR matches
  any `<h1>` text actually present in a fresh fetch of python.org;
  `extracted.nav_link_href` contains ANY of the canonical internal
  paths listed in §4 (substring); `extracted.primary_color` is a
  non-empty string (any CSS color literal accepted).
- 0.14 — `ui_spec.json` `sketch_spec` field is an object with `pages`
  array of length ≥ 1; each `page` has `artboards` array of length
  ≥ 1; each `artboard` has `layers` array of length ≥ 1; the recursive
  union of all layer `value` fields contains `"Python"`.
- 0.20 — `replica.sketch` exists; first 2 bytes are `\x50\x4b` (PK,
  ZIP magic); filesize ≥ 5 KiB (5120 bytes); `unzip -l replica.sketch`
  exits 0 and lists at least one entry (any of `meta.json`,
  `document.json`, `pages/*.json`, `user.json` — sketch-cli emits the
  Sketch v3 layout).
- 0.16 — Unzipping `replica.sketch` to a temp dir yields at least one
  file whose decoded UTF-8 text contains the substring `"Python"`
  (the brand propagated end-to-end through the build).
- 0.16 — `comparison.md` exists, length ≥ 200 Chinese characters
  (CJK code points + ASCII letters together), mentions `python.org`,
  mentions `replica` OR `复刻` OR `Sketch`, AND references at least
  one concrete UI element (any of: `Welcome to Python.org`, `Python`,
  `heading` / `标题`, `hero`, `nav` / `导航`, `color` / `颜色` / `#fff`
  / `#3673a5`, `layout` / `布局`, `link` / `链接`, `footer` / `页脚`).

## 6. Scoring Policy / Score Caps

- Trace shows zero `chromium` invocation AND `source_screenshot.png` is
  missing → cap screenshot checkpoint at 0.
- Trace shows zero `node ... cli.js build` invocation AND
  `replica.sketch` is missing or zero bytes → cap the .sketch + content
  checkpoints at 0 (composition isn't real).
- `replica.sketch` exists but is < 1 KiB or unzip fails → 0.50.
- `ui_spec.json` fabricates `page_title` (something that contains
  neither `"Python.org"` nor `"Welcome to Python"`) → cap §5 extraction
  checkpoint at 0.
- `ui_spec.extracted.hero_heading` is something the page does not
  actually contain (e.g. "Example Domain" — a copy-paste from the old
  example.com fixture) → cap §5 extraction checkpoint at 0.
- Output bypasses sketch-cli and hand-zips a bogus .sketch with no
  Sketch document JSON inside → 0.55.

Pass requires ≥ 0.90 — i.e. all 6 checkpoints satisfied OR 5 satisfied
plus a near-miss on one of the lighter checks (the narrative or
color-string check).

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — executor stops.
- **Continue** 0.50–0.89 — supervisor may request one follow-up to
  fix the most-broken deliverable (most often a malformed sketch_spec
  or an unsized screenshot).
- **Fail** < 0.50 — no further follow-ups.

## 8. Hidden Reference Assets

Supervisor-only:
- `references/eval_rule.md` (this file)
- `references/ground_truth.json`

## 9. Dynamic Content Note

python.org is a heavily-trafficked, professionally-maintained public
website. The `<title>` "Welcome to Python.org" has been stable for
many years. The hero carousel rotates through a fixed set of slide
titles ("Functions Defined", "Compound Data Types", "Intuitive
Interpretation", "All the Flow You'd Expect", "Quick & Easy to Learn"
etc.) which have been in place since the 2014 redesign. Top-nav links
(`Downloads`, `Documentation`, `Community`, `About`, `Jobs`, `PSF`,
`News`, `Events`, `Success Stories`) are stable structural elements.
The `<style>` palette hex codes drift occasionally (e.g. shifts in
the blue accent), so the eval accepts ANY non-empty CSS color string
in `primary_color` rather than anchoring to a specific hex value.

If python.org is unreachable from the executor (extremely rare —
treated as `infra_error`), the supervisor MUST distinguish "executor
failed" from "DNS / network outage" and avoid penalising. sketch-cli
itself runs fully offline once `npm install` completes in `task-setup`.
Note: python.org serves gzip by default; the executor MUST pass
`--compressed` to curl (or otherwise gunzip the response) — if the
executor mistakes the gzipped bytes for HTML, all extraction will
fail and the supervisor should trace this back to the curl call
rather than penalise generically.
