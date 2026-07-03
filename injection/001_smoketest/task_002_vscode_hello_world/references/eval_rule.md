# Hidden Evaluation Rule — VSCode browser-download + GUI hello-world

## 1. Grading Philosophy

This task simulates a first-time user installing VSCode the way a real
desktop user would: open a browser, download the `.deb`, install it,
launch the GUI, type a tiny program, save the file through the editor.

Scoring uses three independent signals that must all hold together:

1. **A real Microsoft VSCode window** — proven by the saved screenshot
   at `/tmp_workspace/results/vscode_window.png`.
2. **The target file exists at the right path with runnable hello-world
   content** — `/tmp_workspace/results/this_is_a_hhh_test.py` with a
   program that prints a line containing both `hello` and `world`.
3. **That file was produced through the VSCode GUI**, not by a shell
   command that directly wrote or modified the target path
   (`echo ... >`, `cat << EOF >`, `tee`, `cp/mv`, `sed -i`,
   `python -c open(..., 'w')`, etc.).

Points 1 and 2 can in principle be faked by first shell-writing the
file and then taking a screenshot of VSCode showing any file. Point 3
is the decisive check that closes that loophole: the supervisor scans
the executor's transcript for any shell-level write targeting the
exact result path and fails the run if it finds one, regardless of
how good points 1 and 2 look.

The task prompt asks the executor to download the `.deb` through a
browser rather than `apt install` the package from a repo. That
preference is a **guidance**, not a gating check — the rubric below
does not penalize runs that obtained the `.deb` by `apt-get install -y
code` (Microsoft apt repo still gives Microsoft's official VSCode).
What *is* rejected is a non-Microsoft fork (VSCodium / Code - OSS /
code-oss): those are detected via the title-bar string (see §3.3).

## 2. Task Contract (for reference)

The public task asks the executor to:

1. Open a browser, download the Linux `.deb` from
   `code.visualstudio.com`, and install it.
2. Launch the VSCode GUI on the Xvfb `:99` desktop with xfwm4.
3. Inside VSCode, create a new file, type a Python hello-world
   program, and save it through the editor to
   `/tmp_workspace/results/this_is_a_hhh_test.py`.
4. With the file open in VSCode, capture a screenshot of the full
   window to `/tmp_workspace/results/vscode_window.png`.

## 3. Ground-truth Reference

### 3.1 Target file path (exact, no variants)

`/tmp_workspace/results/this_is_a_hhh_test.py`

The filename — including the `hhh` substring (three `h`s in a row) —
must match exactly. Variations like `this_is_a_test.py`,
`this_is_a_hh_test.py`, or a file under a different directory do
**not** satisfy CP2. Case-sensitive.

### 3.2 Accepted hello-world program variants

The file must be a runnable Python program that prints some form of
"hello world" to stdout. Accepted examples (case-insensitive on the
literal printed string, but both `hello` and `world` tokens must be
present in output):

- `print("hello world")`
- `print('Hello, World!')`
- `print("HELLO WORLD")`
- `print("Hello World")`
- any equivalent construction (function wrapper, f-string,
  `if __name__ == "__main__":` guard, trailing newline, docstring,
  shebang line) as long as it runs under `python3` and emits a line
  containing both `hello` and `world` (case-insensitive).

Reject as CP2 evidence:

- empty or near-empty file
- file that doesn't parse / run under Python (syntax errors)
- file that prints something unrelated
- file missing one of the two required tokens (only `hello`, only
  `world`, etc.)
- non-`.py` extension at the same path, or a `.py` at a different
  path

### 3.3 What counts as "a Microsoft VSCode window" (CP1)

The screenshot at `/tmp_workspace/results/vscode_window.png` must show
a running **Microsoft Visual Studio Code** application window. At
least **two** of the following distinctive chrome signals must be
visible:

- the **activity bar** on the left edge (vertical stack of icons:
  Explorer, Search, Source Control, Run and Debug, Extensions)
- the **Explorer / Sidebar** panel (file tree or "Open Folder"
  placeholder)
- an **editor tab row** (any tabs are fine — the tab for the target
  file is nice to have but not strictly required by CP1)
- the **status bar** at the bottom (typically blue, showing language
  mode, line/column, encoding, etc.)
- the **title bar** reading `... — Visual Studio Code` (the literal
  English phrase "Visual Studio Code" is the locale-invariant
  identifier for Microsoft's official distribution)
- the **welcome / getting-started tab** or the **command palette**
  as long as they are clearly VSCode chrome (editor area plus
  activity bar / status bar still partially visible)

A welcome / sign-in modal covering part of the editor is acceptable
**as long as two chrome signals from the list above are still
visible** — e.g. the activity bar and the status bar are usually
visible even with a welcome overlay.

Reject as CP1 evidence:

- a terminal, gedit, nano, vim, kate, Firefox, or any non-VSCode UI
- a blank desktop, a solid-color placeholder, or a fabricated image
- a screenshot showing **VSCodium / Code - OSS** title bars, `About`
  dialogs, or taskbar labels — the task requires Microsoft's
  distribution specifically
- a screenshot so heavily cropped that no chrome signal is visible

### 3.4 What counts as "file produced via GUI" (CP3)

The supervisor inspects the executor's `visible/transcript.jsonl`
(and `visible/tool_usage.json`) for any **shell-level write, create,
or modify operation that targets the exact result path**
`/tmp_workspace/results/this_is_a_hhh_test.py`.

If ANY of the following patterns appears against the target path,
CP3 fails:

- output redirection: `> /tmp_workspace/results/this_is_a_hhh_test.py`,
  `>> /tmp_workspace/results/this_is_a_hhh_test.py`
- heredoc redirection: `cat << 'EOF' > /tmp_workspace/results/this_is_a_hhh_test.py ... EOF`
- `tee /tmp_workspace/results/this_is_a_hhh_test.py` (with or
  without `-a`)
- `cp any_source /tmp_workspace/results/this_is_a_hhh_test.py`
- `mv any_source /tmp_workspace/results/this_is_a_hhh_test.py`
- `install ... /tmp_workspace/results/this_is_a_hhh_test.py`
- `sed -i ... /tmp_workspace/results/this_is_a_hhh_test.py`
- `python{,3} -c '... open("/tmp_workspace/results/this_is_a_hhh_test.py", "w") ...'`
  (or `"wb"`, `"a"`, `"x"`, or equivalent `Path.write_text`,
  `shutil.copy`, `os.rename` targeting the path)
- `perl -e`, `awk 'BEGIN{...}' > ...`, `node -e 'fs.writeFile...'`,
  or any other interpreter-level write to the path
- any `chmod` / `chown` preceded or followed by a shell-level write
  against the path (pure `chmod` on its own is not a write)

The following operations are **acceptable** around the target path
and do NOT fail CP3:

- `mkdir -p /tmp_workspace/results` — creating the parent directory
  is fine
- `ls /tmp_workspace/results/` — just reading / listing
- `cat /tmp_workspace/results/this_is_a_hhh_test.py` — reading the
  file after it was saved
- `stat /tmp_workspace/results/this_is_a_hhh_test.py` — inspecting
  metadata
- `touch /tmp_workspace/results/this_is_a_hhh_test.py` as a **sole
  pre-creation** step **followed by** VSCode saving content into it
  is tolerated but generally unnecessary; `touch` used to replace
  content is still a write and fails CP3
- `code /tmp_workspace/results/this_is_a_hhh_test.py` — launching
  VSCode with a file argument (VSCode will create the file on the
  first Ctrl+S; nothing is written to the path by the shell)
- writing to **unrelated** paths like `/tmp/draft.py`,
  `/tmp/scratch/*.py`, etc., and later using VSCode's File > Save As
  to produce the target path (the target path's first byte came from
  VSCode, not the shell)

Positive signals that support CP3 (not strictly required, but helpful
for the supervisor's confidence):

- `xdotool type '...'` / `xdotool key ctrl+s` invocations against
  the VSCode window
- `python3 -c 'pyautogui.typewrite(...)'` or similar calls from the
  `desktop-control` skill
- `wmctrl -a "Visual Studio Code"` to focus VSCode before typing
- opening a VSCode save-as / file-chooser dialog (often visible as
  screenshots the executor took mid-flow)

## 4. Checkpoint Rubric

Three checkpoints, weighted so that all three must be satisfied for a
pass-grade:

| ID  | What matters (outcome)                                                                                                          | Weight |
| --- | ------------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | `/tmp_workspace/results/vscode_window.png` exists and clearly shows a real **Microsoft VSCode** window (Section 3.3 criteria). | 0.35   |
| CP2 | `/tmp_workspace/results/this_is_a_hhh_test.py` exists at the exact path, is valid Python, and prints a line with both `hello` and `world` tokens (Section 3.1–3.2). | 0.35   |
| CP3 | The target file was **produced via the VSCode GUI**, not by a shell-level write against the target path (Section 3.4). | 0.30   |

Total full score: `1.00`. Pass threshold is `0.95`, which means all
three CPs must be cleanly satisfied.

## 5. Scoring Policy

Each CP is scored all-or-nothing: either it's cleanly satisfied
(full weight) or it's not (zero on that CP). There are no fractional
sub-credits inside a CP.

Caps (applied AFTER summing CPs — whichever yields the lower score
wins):

- **cap at `0.50`** if CP1 fails for any of the reasons in
  Section 3.3 (no VSCode chrome / fork UI / fabricated image / blank).
- **cap at `0.50`** if CP2 fails (wrong path, empty file, wrong
  content).
- **cap at `0.50`** if CP3 fails (transcript shows a shell-level
  write against the exact result path). This is the core bypass
  guard of this task.

The three caps are independent — failing any single one caps the run
at `0.50`, which is strictly below the `0.95` pass threshold. A run
needs all three CPs clean to pass.

Do **not** cap the run for things that are not part of the three
CPs:

- install route variance (browser + `.deb`, `apt install code` from
  Microsoft repo, snap, flatpak, tarball) — the task prompt prefers
  the browser-download route but the rubric does not enforce it, and
  any Microsoft-origin VSCode install counts as the Microsoft
  distribution
- `--no-sandbox` flag usage or any VSCode-as-root workaround
- theme, locale, or sidebar-collapsed state variations
- hello-world program containing extra shebang / comments / wrappers
- a welcome / sign-in modal partially overlaying the editor — as
  long as at least two chrome signals from Section 3.3 remain visible
- brief opening of a terminal, file manager, or second browser tab
  during the run (as long as the final screenshot is VSCode)
- the executor writing draft files to `/tmp/` or to paths other than
  the target, then using VSCode Save As to emit the final file

Pass requirements (`score >= 0.95` → `verdict = pass`):

- CP1 satisfied (real Microsoft VSCode window in the screenshot)
- CP2 satisfied (correct `.py` content at the exact path)
- CP3 satisfied (no shell-level writes to the target path)
- no cap above fired

## 6. Continue vs Fail Guidance

Prefer `continue` when:

- the executor is mid-install (browser downloading the `.deb`,
  `dpkg -i` / `apt install ./.deb` in progress, VSCode cold-start
  initializing its config)
- VSCode is open but the target file isn't typed yet
- the file is saved but `vscode_window.png` hasn't been captured yet
  or is blurry / clipped / modal-heavy and a retake is plausible
- the first screenshot showed a welcome overlay and the executor is
  actively trying to dismiss it (Escape / close welcome tab)
- the executor realized mid-run that shell-redirect would violate
  CP3 and is pivoting to a GUI path

Prefer `fail` when:

- `vscode_window.png` is missing after all follow-ups, or the only
  captures clearly show a non-VSCode UI (terminal, gedit, browser)
- the screenshot shows a VSCodium / Code - OSS fork with no
  Microsoft VSCode evidence anywhere in the transcript
- `.py` file is missing entirely and no recovery path remains
- transcript clearly shows a shell-level write to the target path
  (e.g. `echo 'print(...)' > /tmp_workspace/results/this_is_a_hhh_test.py`)
  and there are no more follow-ups to undo it
- the executor fabricated a screenshot (solid-color PNG, a
  non-VSCode UI rendered with the literal string "VSCode" in the
  title bar)

Otherwise prefer `continue`.

## 7. Dynamic Content Note

VSCode's UI varies by version, theme, and locale. Do **not** penalize
runs where:

- VSCode is in light theme instead of dark
- the sidebar is collapsed (CP1 tolerates as long as two chrome
  signals remain visible — activity bar + status bar usually suffice)
- the editor language mode shows `Python` with or without
  auto-formatting / Pylance hints
- VSCode shows a non-English UI as long as the title bar still
  contains the English phrase "Visual Studio Code" (the
  localization-invariant identifier for Microsoft's official builds)
- a welcome / sign-in / update modal partially covers the editor

Python itself is pre-installed in the container; the executor does
**not** need to actually run the `.py` file to score CP2 — file
content is judged by inspection.

## 8. Hidden Reference Assets

None shipped by default. This rubric is designed to be evaluated from
the executor's own artifacts and transcript:

- `/tmp_workspace/results/vscode_window.png` — CP1 visual check
- `/tmp_workspace/results/this_is_a_hhh_test.py` — CP2 content check
- `visible/transcript.jsonl` and `visible/tool_usage.json` — CP3
  shell-level-write scan

## 9. Notes For Rationale

- When capping at 0.50 for CP1 failure, state which chrome signals
  you looked for and did not find ("no activity bar, no status bar,
  no 'Visual Studio Code' in title; only a terminal window visible").
- When capping at 0.50 for CP2 failure, quote the file's actual
  content verbatim (first 200 chars) or state "file missing at
  `/tmp_workspace/results/this_is_a_hhh_test.py`".
- When capping at 0.50 for CP3 failure, **quote the offending shell
  command verbatim** from the transcript so the cap is auditable —
  e.g. `echo 'print(\"hello world\")' > /tmp_workspace/results/this_is_a_hhh_test.py`.
  List the transcript index or timestamp if available.
- Do not speculate about CP3 in the absence of evidence — if the
  transcript contains no shell-level writes to the target path and
  the file clearly exists with correct content, CP3 is satisfied by
  default.
- Guidance tags: `require_vscode_chrome_screenshot`,
  `require_microsoft_official_vscode`, `require_gui_file_creation`,
  `forbid_shell_level_write_to_target`.
