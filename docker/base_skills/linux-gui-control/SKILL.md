---
name: linux-gui-control
description: Control the Linux desktop GUI using xdotool, wmctrl, dogtail, and scrot. Provides a window list, an accessibility-tree viewer (with coordinates) for finding buttons and text fields, a thin xdotool wrapper for actuating them, and a launcher helper that enables accessibility for Electron/Chromium apps.
---

# Linux GUI Control

Use this skill when you need to automate X11 desktop applications inside
the sandbox.

## Core flow

The flow is deliberately two-stage:

1. **Look** at the accessibility tree to find what widgets exist,
   where they are, and what they're called.
2. **Act** on them via xdotool (click coordinates, type text, press
   keys), using the coordinates from step 1.

This keeps actuation simple (no magic clicking-by-name), and makes it
obvious to everyone reviewing the transcript exactly which button was
targeted.

## Quick start

1. List windows:
   `wmctrl -l`

2. Inspect the accessibility tree of a window. Returns JSON with
   `role / name / x / y / w / h` for every reachable widget:
   `./scripts/gui_action.sh inspect "<window-title-substring>"`
   or directly:
   `python3 ./scripts/inspect_ui.py "<window-title-substring>"`

3. Shortcut for a single widget — prints `"x y w h"` on one line so
   you can xargs it straight into xdotool:
   `./scripts/gui_action.sh find "<window>" "<widget-name>" [--role R]`

4. Activate a window (bring to front, give focus):
   `./scripts/gui_action.sh activate "<window-name>"`

5. Click / type / send a key (coordinate-based, via xdotool):
   `./scripts/gui_action.sh click 500 400`
   `./scripts/gui_action.sh type "hello"`
   `./scripts/gui_action.sh key Return`

6. Launch GUI applications with accessibility enabled (recommended
   for any Electron / Chromium-based app; see the framework matrix
   below for why):
   `./scripts/launch_with_a11y.sh <app> [args...]`

## Important usage rules

- Treat text entry and special keys as separate actions.
- Use `type` only for literal text that should appear on screen.
- Use `key` for keys such as `Return`, `Tab`, `Escape`, `ctrl+l`, or arrow keys.
- Do not put strings like `keyReturn`, `Return`, or `ctrl+l` inside a `type` command unless you really want those characters typed into the UI.
- For browser address bars and search boxes:
  1. activate the window
  2. focus the target field
  3. `type` the URL or search text
  4. send `key Return` as a separate action
  5. wait for the page to load before taking a screenshot

## Typical Save / Open dialog workflow

    # Step A — trigger the dialog inside the app (Ctrl+S / Ctrl+Shift+S
    # / File > Save As menu, whatever the app uses):
    ./scripts/gui_action.sh activate "<main window title>"
    ./scripts/gui_action.sh key ctrl+shift+s
    sleep 1.5   # let the dialog fully open; don't race it

    # Step B — look at the dialog. Get `x y w h` of the Save button
    # and of the filename entry:
    read SAVE_X SAVE_Y SAVE_W SAVE_H < <(./scripts/gui_action.sh find "Save As" "Save" --role "push button")

    # Step C — compute center and click:
    ./scripts/gui_action.sh click $((SAVE_X + SAVE_W/2)) $((SAVE_Y + SAVE_H/2))

Before Step B, consider `gui_action.sh inspect "Save As"` to dump the
whole tree — helpful when widget names are locale-specific or you don't
know the exact role.

## Common browser patterns

- Open a URL in Chromium (launch it with a11y enabled first — see
  below — if you also want `inspect` to work on browser tabs):
  `./scripts/launch_with_a11y.sh chromium &`
  `./scripts/gui_action.sh activate "Chrome"`
  `./scripts/gui_action.sh key ctrl+l`
  `./scripts/gui_action.sh type "https://example.com"`
  `./scripts/gui_action.sh key Return`

- Launch Chromium in a clean disposable profile when first-run pages would be distracting:
  `chromium --no-sandbox --no-first-run --disable-sync --no-default-browser-check --user-data-dir=/tmp/chromium-profile-task &`

- Search from the browser address bar:
  `./scripts/gui_action.sh activate "Chrome"`
  `./scripts/gui_action.sh key ctrl+l`
  `./scripts/gui_action.sh type "your search query"`
  `./scripts/gui_action.sh key Return`

- Move through page focus targets with the keyboard:
  `./scripts/gui_action.sh activate "Chrome"`
  `./scripts/gui_action.sh key Tab`
  `./scripts/gui_action.sh key Tab`
  `./scripts/gui_action.sh key Return`

- Verify the current page URL:
  `./scripts/gui_action.sh activate "Chrome"`
  `./scripts/gui_action.sh key ctrl+l`
  `./scripts/gui_action.sh key ctrl+c`
  `xclip -o -selection clipboard`

- If a page body is blank or still rendering:
  `./scripts/gui_action.sh activate "Chrome"`
  `./scripts/gui_action.sh key ctrl+r`
  `sleep 3`
  Take the screenshot only after visible page text or buttons appear.

## Framework coverage: what `inspect` actually sees

The accessibility tree is populated by the application itself — it
doesn't probe windows from outside. Whether a given app appears in the
tree depends on its UI framework:

| framework              | joins AT-SPI bus automatically? | what you need |
| ---                    | ---                             | --- |
| GTK 2 / 3 / 4          | yes                             | nothing — the image sets `GTK_MODULES=gail:atk-bridge` |
| Qt 5 / 6               | yes                             | nothing — the image sets `QT_ACCESSIBILITY=1` |
| Electron / Chromium    | **no**, off by default          | launch via `launch_with_a11y.sh` (adds `--force-renderer-accessibility`) |
| Java Swing / JavaFX    | no                              | set `JAVA_TOOL_OPTIONS=-Dassistive_technologies=org.GNOME.Accessibility.AtkWrapper` |
| Tcl/Tk / SDL / raw X11 | no                              | no a11y; fall back to `scrot` + coordinate guessing |

Rule of thumb: if `inspect "<window>"` returns only empty-name `panel`
widgets under your frame, the app's renderer is not on the bus. For
Electron / Chromium that means you should have launched it via
`launch_with_a11y.sh`. For other cases you'll need to screenshot and
eyeball coordinates.

Note about Electron's *child* windows: even when the renderer isn't on
the bus, the GTK-native dialogs that Electron pops up (Save As, Open
File, color picker, print) **do** register automatically — they're
separate processes using plain GTK. So `inspect "Save As"` on a
VSCode Save-As dialog works even if you started VSCode without the
a11y flag. The flag is only needed when you want to address widgets
inside the main app window.

## Browser navigation hints

- Prefer keyboard navigation over guessing click coordinates on search result pages.
- On a search results page, it is often more reliable to:
  1. focus Chromium
  2. press `Tab` repeatedly to move through focusable results or page controls
  3. press `Return` on the focused result
- After navigation, verify the URL with `ctrl+l`, `ctrl+c`, and `xclip` before taking a required screenshot.
- If the destination page URL is correct but the body looks blank, reload once and wait for visible content before capturing the screenshot.

## Multi-window and dialog pitfalls

Beyond single-window automation, X11 has two mechanics that break the
naive `xdotool search --class X | head -n1` pattern:

### Selecting the right window when WM_CLASS is not unique

An app may open multiple top-level windows that all share `WM_CLASS`
(e.g. "Welcome", "Untitled-1", and a settings window, all `--class X`).
`| head -n1` is not deterministic about which it returns.

Select by **title substring** — every window has a distinct `WM_NAME`
visible in `wmctrl -l`:

    wmctrl -l
    # 0x00c00004  0 some-app.SomeApp  <host>  Welcome - SomeApp
    # 0x00d00006  0 some-app.SomeApp  <host>  Untitled-1 - SomeApp

    WIN=$(xdotool search --onlyvisible --name "Untitled-" | head -n1)

### Typing into a dialog that just opened

File choosers, Save As dialogs, print dialogs, color pickers in GTK
and Qt are **separate top-level X11 windows**, not children of the app
window that opened them. `xdotool type --window "$MAIN" '<text>'` after
a dialog opens will send keys to `$MAIN`'s focused control, not to the
dialog's text field.

Correct pattern — find the dialog by title and activate it before
typing:

    xdotool key --window "$MAIN" ctrl+shift+s
    sleep 1
    DIALOG=$(xdotool search --onlyvisible --name "Save" | head -n1)
    [ -n "$DIALOG" ] || { wmctrl -l; exit 1; }
    xdotool windowactivate --sync "$DIALOG"
    sleep 0.3
    xdotool key --window "$DIALOG" ctrl+a
    xdotool type --delay 20 --window "$DIALOG" "<text>"
    xdotool key --window "$DIALOG" Return

## Available tools

- `wmctrl` — list / activate windows
- `xdotool` — simulate mouse and keyboard
- `scrot` — take a screenshot
- `python3-dogtail` — accessibility tree (used by `inspect_ui.py` / `a11y.py`)
- `scripts/gui_action.sh` — thin wrapper combining all the above
- `scripts/inspect_ui.py` / `scripts/a11y.py` — accessibility-tree viewer
- `scripts/launch_with_a11y.sh` — launch an app with accessibility on
