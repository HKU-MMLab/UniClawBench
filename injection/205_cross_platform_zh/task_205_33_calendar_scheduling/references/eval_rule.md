# Hidden Evaluation Rule — task_205_33_calendar_scheduling

## 1. Grading Philosophy

Grade on whether the executor performed the full cross-platform
"messy text → structured calendar with REAL Zoom meetings → live GUI
calendar" workflow:

1. read the chat-style schedule dump at `~/clawbench-schedule.txt`,
2. parse out each event (title, ISO start datetime, duration in
   minutes) into structured JSON,
3. **self-configure the Zoom CLI from env vars** — `install.sh` wipes
   `~/.cli-anything-zoom/` deliberately; the executor must use
   `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET`, and `ZOOM_REFRESH_TOKEN` to
   re-create `config.json` + `tokens.json`, then verify with
   `zoom auth status` before any `zoom meeting create` call,
4. for each of the 6 events call
   `zoom meeting create --topic <title> --start-time <ISO8601> --duration <min>`
   and embed the returned `join_url` in the matching `VEVENT` (in
   `LOCATION` or `DESCRIPTION`),
5. emit a valid RFC-5545 ICS file with one `VEVENT` per event, each
   carrying the real Zoom join_url,
6. open `gnome-calendar` (preinstalled), get the events visible on
   screen, and capture a `scrot` screenshot of the calendar window,
7. write a narrative `scheduling_report.md` covering all stages.

There is **no Jitsi fallback**: this task is Zoom-only. If `install.sh`
fails to bootstrap Zoom (bad/expired refresh_token), the supervisor
treats the whole run as `infra_error` (no penalty to the executor for
infra failure — see §6).

`install.sh` ALSO resets the test account to zero meetings before the
executor starts, so the executor's 6 newly-created meetings are the
only ones present at eval time. This guarantees every run starts from
a clean slate ("calendar empty before each run" per task design).

Anchor every checkpoint against `ground_truth.json`. Score caps in §6
override rubric totals.

## 2. Task Contract

Required deliverables:

- `/tmp_workspace/results/parsed_events.json` —
  `{events: [{title, start_datetime, duration_minutes}, ...]}`. The
  array MUST have exactly 6 entries (the schedule fixture has 6
  events). Each entry's `start_datetime` is an ISO 8601 timestamp
  (`YYYY-MM-DDTHH:MM:SS`, no timezone suffix). Each entry's
  `duration_minutes` is a positive integer. Each entry's `title` is
  a non-empty string. Top-level `conflict_check` object MUST be
  present (see §5 conflict checkpoint).
- `/tmp_workspace/results/schedule.ics` — RFC-5545 calendar file
  containing `BEGIN:VCALENDAR` ... `END:VCALENDAR` with exactly 6
  `VEVENT` blocks. Each `VEVENT` MUST have `SUMMARY`, `DTSTART`, and
  `DTEND` properties. `DTSTART`/`DTEND` MUST use floating local time
  format `YYYYMMDDTHHMMSS` (no `Z`, no `TZID`). Each `VEVENT` MUST
  contain a Zoom join_url matching
  `https?://(?:[a-z0-9-]+\.)?zoom\.us/(?:j|w|s)/\d+` in either the
  `LOCATION` line, the `DESCRIPTION` line, or both. The 6 numeric
  meeting IDs across the 6 VEVENTs MUST be distinct (one fresh Zoom
  meeting per event).
- `/tmp_workspace/results/calendar_screenshot.png` — `scrot`
  capture of `gnome-calendar`'s main window with at least 1024×600
  px resolution. Supervisor confirms valid PNG header and reads
  width × height with `Image.open(...).size`.
- `/tmp_workspace/results/scheduling_report.md` — narrative report
  with at least 4 distinct Markdown headings (`##` or `###`),
  covering parsing, ICS export, calendar import, and Zoom meeting
  links (per the structure in the user prompt).
- `~/clawbench-schedule.txt` is the input fixture; it MUST exist
  unmodified (executor should not delete the input).
- The executor's trace MUST show evidence of self-configuring Zoom
  auth (e.g. writing `~/.cli-anything-zoom/config.json` and
  `tokens.json`, OR running `zoom auth setup` then setting tokens,
  OR direct file writes via `cat > … <<JSON`) followed by a
  `zoom auth status` invocation.

There is NO snapshot file under `/tmp_workspace/clawbench/`. The
schedule fixture at `~/clawbench-schedule.txt` is created by
`install.sh`, which also installs `gnome-calendar` + Xvfb +
session dbus + `scrot`, installs the `zoom` CLI, performs the
account reset, and then wipes `~/.cli-anything-zoom/`.

## 3. Source-Selection Rules

Canonical sources are LIVE filesystem + GUI + live Zoom REST API:

- Schedule input: `~/clawbench-schedule.txt` (written by
  `install.sh`, anchored content, immutable per run).
- Calendar app: `gnome-calendar` (binary at
  `/usr/bin/gnome-calendar`) talking to Evolution Data Server
  (`evolution-data-server` package). Any other GUI calendar that
  ends up showing the events is also acceptable — the eval only
  checks the screenshot, not the specific app.
- Display: `Xvfb :99` started by `install.sh`.
- Screenshotter: `scrot` (preferred) or `import` from ImageMagick.
- ICS toolchain: `python3 -c "import icalendar"` is available; the
  executor can also hand-write the ICS since RFC-5545 is plain
  text.
- Meeting service: **Zoom REST** via the CLI-Anything `zoom` CLI
  (`pip install -e /opt/cli-anything/zoom/agent-harness`,
  pre-installed by `install.sh`). The executor MUST self-configure
  `~/.cli-anything-zoom/config.json` (with `client_id`,
  `client_secret`, `redirect_uri=http://localhost:4199/callback`)
  and `~/.cli-anything-zoom/tokens.json` (with `refresh_token` from
  env, `access_token` placeholder, `expires_in` and `saved_at`
  fields so the CLI auto-refreshes on next call). After wiring,
  `zoom auth status` MUST succeed before any `zoom meeting create`.

`install.sh` exposes the env vars `ZOOM_CLIENT_ID`,
`ZOOM_CLIENT_SECRET`, `ZOOM_REFRESH_TOKEN` to the executor's process.
There is no Jitsi fallback path.

## 4. Ground-Truth Snapshot

Structured expected answer at `references/ground_truth.json`.
Anchors:

- 6 events with deterministic dates in May 2026 (all weekdays
  verified against ISO calendar).
- Each event has a canonical `title_keywords` list — the executor's
  parsed title need only contain ALL keywords (case-insensitive
  substring match) for that event to count as correctly identified.
  This tolerates cosmetic title differences ("Q2 planning sync"
  vs "Q2 Planning Sync" vs "Q2 planning sync (Alice + Bob)").
- Each event has an exact `start_datetime` and `duration_minutes`.
- ICS file structure: 6 `VEVENT` blocks, each with a Zoom join_url.
- Per-event Zoom verification: each ground-truth event must match at
  least one Zoom meeting on the test account (topic substring +
  start_time within ±5 min).
- Screenshot: PNG ≥ 1024×600.

## 5. Checkpoint Rubric

Weights sum to 1.0. (8 weighted checkpoints.)

- 0.10 — `parsed_events.json` parses; top-level key `events` is a
  6-element array; each element has `title` (non-empty string),
  `start_datetime` (ISO 8601 string parseable by
  `datetime.fromisoformat`), `duration_minutes` (positive int).
- 0.20 — Per-event ground-truth match. For each of the 6 expected
  events (set-equality, order-agnostic):
  * The parsed array contains exactly one entry whose `title`
    contains ALL the `title_keywords` (case-insensitive substring
    match).
  * That entry's `start_datetime` (parsed as a naive datetime)
    equals the ground-truth `start_datetime` to the minute.
  * That entry's `duration_minutes` equals the ground-truth
    `duration_minutes`.
  All 6 events must match. Partial credit: `0.20 * (matched / 6)`
  rounded down to 2 decimals.
- 0.12 — `schedule.ics` exists; first non-blank line is
  `BEGIN:VCALENDAR`; contains exactly 6 `VEVENT` blocks; each
  `VEVENT` has `SUMMARY:`, `DTSTART:` (or `DTSTART;...:`), and
  `DTEND:` (or `DTEND;...:`) lines. ICS validates with
  `python3 -c "from icalendar import Calendar; Calendar.from_ical(open('schedule.ics').read())"`
  without raising.
- 0.12 — Per-event ICS match. Each ground-truth event has at least
  one `VEVENT` whose `SUMMARY` contains ALL `title_keywords`
  (case-insensitive) AND whose `DTSTART` decoded as a floating
  local datetime equals the ground-truth `start_datetime`. All 6
  events must match.
- 0.12 — `calendar_screenshot.png` exists; valid PNG (magic bytes
  `\x89PNG`); `Image.open(...).size` reports width ≥ 1024 AND
  height ≥ 600. Trace must show a `gnome-calendar` invocation OR a
  fallback calendar GUI launch (any of `gnome-calendar`,
  `evolution`, `korganizer`, `thunderbird`) AND a `scrot` (or
  `import`) invocation in the same task transcript.
- 0.08 — `scheduling_report.md` exists; ≥ 4 distinct Markdown
  headings (`##` or `###`); body mentions all 6 event titles
  (case-insensitive substring per `title_keywords`); body mentions
  the screenshot path and the ICS path.
- 0.18 — **Zoom meeting verification.** Two-part check:
  * **(a) ICS-side, 0.06**: At least 6 of the 6 `VEVENT` blocks
    contain a URL matching
    `https?://(?:[a-z0-9-]+\.)?zoom\.us/(?:j|w|s)/\d+` in either
    the `LOCATION` line OR the `DESCRIPTION` line. The set of
    distinct numeric meeting IDs (last `/\d+` segment) across all
    6 VEVENTs has cardinality ≥ 6.
  * **(b) Live Zoom verification, 0.12**: The supervisor runs
    `zoom --json meeting list` against the test account
    post-execution and verifies:
    - The list contains ≥ 6 meetings (since `install.sh` reset the
      account to zero, all listed meetings must be the executor's
      6 fresh creates).
    - For each of the 6 ground-truth events, at least one Zoom
      meeting's `topic` contains ALL `title_keywords`
      (case-insensitive substring) AND `start_time` (parsed as
      datetime) is within ±5 min of the expected `start_datetime`
      (treating the local-floating ICS time as the same wall-clock
      moment as the Zoom UTC start_time when the executor sets it
      with the local-machine timezone, OR matching HH:MM if the
      test env runs UTC).
    Partial credit: `0.12 * (matched / 6)` rounded down to 2
    decimals.
  * **Trace evidence requirement (overrides 0 if missing)**: The
    executor's trace MUST show self-configuration of
    `~/.cli-anything-zoom/{config,tokens}.json` (file writes OR
    `zoom auth setup` invocation OR equivalent) followed by a
    `zoom auth status` check. If no trace evidence of self-config
    appears, this checkpoint scores 0 (means: pre-baked / cheated).
- 0.08 — **Conflict / near-conflict detection is present and
  correct.** The `parsed_events.json` MUST carry a `conflict_check`
  (or equivalently named) object with at least two array fields:
  * `hard_conflicts` (or `events_with_overlap` etc.) — pairs of
    events whose `[start, end)` time windows overlap (start_a <
    end_b AND start_b < end_a).
  * `near_conflicts` (or `near_conflict_pairs` etc.) — pairs of
    events on the SAME calendar date whose consecutive gap (next
    event's start minus previous event's end) is ≥ 0 minutes AND
    < 60 minutes.
  Each entry should identify the two events involved (titles or
  IDs) AND the gap (for near-conflicts). For the schedule fixture
  written by `install.sh`, the EXPECTED values are:
  * `hard_conflicts`: 0 entries (the 6 events fall on 6 distinct
    May 2026 weekdays — Wed 5/13, Fri 5/15, Mon 5/18, Tue 5/19,
    Thu 5/21, Fri 5/22 — so no two windows can overlap).
  * `near_conflicts`: 0 entries (no two events share a calendar
    date in the fixture).
  The `scheduling_report.md` MUST have a section (under any `##` /
  `###` heading containing words like "conflict" / "冲突" /
  "overlap" / "sanity") that surfaces both numbers — when both
  are 0, an explicit "no conflicts" / "no near-conflicts" /
  "零冲突" / "无重叠" statement counts as satisfying. Partial 0.04
  if the JSON object exists with the right shape but the report
  doesn't mention it. Partial 0.04 if the report mentions
  conflict-checking but the JSON object is missing. Score 0 if
  the executor reports a non-zero conflict count for this fixture
  (false positives indicate the conflict logic is broken — the
  fixture is conflict-free by construction).

## 6. Scoring Policy / Score Caps

Partial credit from satisfied checkpoints. Caps:

- `parsed_events.json` missing OR not a 6-element array → cap 0.30.
- `schedule.ics` missing OR not a valid ICS file → cap 0.45.
- Calendar screenshot missing OR no calendar-app invocation in
  trace → cap 0.65.
- Per-event ground-truth match below 4 of 6 → cap 0.55.
- `scheduling_report.md` missing → cap 0.80.
- Trace shows the executor edited or deleted `~/clawbench-schedule.txt`
  (the input fixture) → cap 0.50.
- No trace evidence of executor self-configuring Zoom auth (no file
  write to `~/.cli-anything-zoom/`, no `zoom auth setup`, no `zoom
  auth status` invocation) → cap 0.55 AND zero out checkpoint
  0.18(b). The executor MUST do the wiring themselves; install.sh
  deliberately leaves the auth dir empty. (If the executor DID wire
  the auth and `zoom meeting create` succeeded but `zoom meeting
  list` later returned fewer than 6, see the `infra_error` rule
  below — that is not the executor's fault.)
- All 6 VEVENTs share an identical Zoom meeting ID (one room reused)
  → cap Zoom-meeting checkpoint at 0 (and overall cap 0.85).
- `zoom --json meeting list` post-execution reports fewer than 6
  meetings AND the executor's logs do not show any successful
  `zoom meeting create` invocation → cap Zoom-meeting checkpoint
  at 0 (and overall cap 0.85). If `zoom meeting create` was invoked
  but `meeting list` shows fewer than 6 (e.g. some calls returned
  4xx mid-run), score the (b) sub-checkpoint as
  `0.12 * (created_visible / 6)`.
- **`infra_error`**: If `install.sh` itself failed to bootstrap Zoom
  (bad/missing/expired `ZOOM_REFRESH_TOKEN` — `install.sh` exits 1
  with a clear FATAL line in its log), the supervisor treats the
  ENTIRE run as `infra_error` and reports separately rather than
  scoring against the executor. The executor cannot recover from a
  missing refresh_token — it is a one-time human OAuth bootstrap
  step, documented in `/tmp/clawbench_user_actions.md`. Similarly,
  if `zoom --json meeting list` itself errors at eval time (network
  down, refresh token revoked mid-run), the supervisor drops the
  live Zoom check (b) and grades only the ICS-side URL pattern (a)
  + the executor's own create-call evidence in trace.

Pass requires the parse checkpoint, per-event GT match, ICS
structure, per-event ICS match, screenshot validity checkpoint,
report checkpoint, AND the Zoom-meeting verification checkpoint
(both a + b sub-checkpoints) all satisfied.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — executor should stop.
- **Continue** 0.50–0.89 — supervisor may request one follow-up to
  re-parse a missed event, regenerate the ICS, retake the
  screenshot, retry the Zoom auth wiring, re-create missing
  meetings, or extend the report.
- **Fail** < 0.50 — no further follow-ups.

## 8. Hidden Reference Assets

Supervisor-only:
- `references/eval_rule.md` (this file)
- `references/ground_truth.json`

## 9. Dynamic Content Note

All anchors are immutable: the schedule fixture is re-baked by
`install.sh` on every run with the same 6 events on fixed dates in
May 2026 (weekdays cross-checked). The ICS format is RFC-5545
plain text. `gnome-calendar` is a stable Debian/Ubuntu package and
its on-screen rendering does not affect the eval (we only check
the screenshot is a valid PNG of the right size — not pixel
content).

The Zoom test account is **reset by `install.sh` on every run** (all
pre-existing meetings are listed via `zoom --json meeting list` and
deleted), guaranteeing the 6 meetings the executor creates are the
ONLY ones present at eval time — no cross-run contamination. After
the reset, install.sh wipes `~/.cli-anything-zoom/` so the executor
must self-configure auth from the env vars (`ZOOM_CLIENT_ID`,
`ZOOM_CLIENT_SECRET`, `ZOOM_REFRESH_TOKEN`). The refresh_token in
`.privacy` is long-lived (Zoom server-side TTL); if it is revoked the
supervisor sees `zoom auth status` fail in the install.sh log and
treats the run as `infra_error` per §6.

If `gnome-calendar` fails to launch (e.g., dbus init issue on a
particular base image), the supervisor MUST distinguish "executor
failed" from "infra failure": if the trace shows a clean
`gnome-calendar` exec attempt followed by a non-zero exit and the
executor falls through to a different GUI, the supervisor treats
the screenshot checkpoint as `infra_error` and does not penalise.
