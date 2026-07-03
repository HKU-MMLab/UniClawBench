---
name: agent-browser-control
description: Drive a headed Chromium via the agent-browser CLI — open/click/type/hover/scroll/screenshot/snapshot/eval/pdf/network-route. Use this for any web interaction; no native browser tool is exposed.
always: true
---
# Agent Browser Control

Use the `agent-browser` CLI for any web interaction. No other browser tool is exposed in this environment.

## Binary

- `agent-browser` (global, on `PATH`)
- Chromium is pre-installed at `/usr/local/bin/chromium`
- A persistent browser daemon is started automatically on the first command and reused across calls

## Typical workflow

1. Open a page:

```bash
agent-browser open https://example.com
```

2. Inspect the page:

```bash
agent-browser snapshot
agent-browser get url
agent-browser get title
```

3. Interact with elements:

```bash
agent-browser click "@e2"
agent-browser fill "@e3" "text value"
agent-browser press Enter
agent-browser wait --load networkidle
```

For form submission flows, do not assume a public demo form is static just because the first click appears unchanged. After clicking the submit button:

```bash
agent-browser wait --load networkidle
agent-browser get url
agent-browser snapshot
```

If needed, try the submit control again or press `Enter`, then re-check the URL and page content before concluding that submission failed.

Before clicking a final action such as a submit button, refresh the page snapshot and use the current ref from that latest snapshot. Do not rely on a stale remembered ref.

4. Save evidence (screenshots go to the path you pass):

```bash
mkdir -p /tmp_workspace/results/screenshots
agent-browser screenshot /tmp_workspace/results/screenshots/page.png
```

`screenshot` defaults to viewport-only PNG at the exact path you provide. Pass `--full` for full-page; pass `--screenshot-format jpeg` for JPEG.

5. Close the browser when done:

```bash
agent-browser close
```

## Notes

- `snapshot` returns refs like `@e2`; use those refs for `click`, `fill`, and `get text`.
- For multi-step flows, `agent-browser batch --json` can run a JSON array of commands in one invocation (daemon persists between commands anyway, so chaining with `&&` is usually enough).
- Always wait for navigation or content changes before taking the next screenshot.
- Save any required output files under `/tmp_workspace/results`; the `screenshot <path>` argument is respected literally, so point it directly at the file you want saved.
- In benchmark tasks, write required JSON/log files incrementally as milestones are reached instead of waiting until the very end.
