# Hidden Evaluation Rule — Exploration v2 · Hardened zshrc refactor (objective per-scenario prompt assertions)

## 1. Grading Philosophy

This is a **config-refactor / conflict-resolution** task graded by **objective
assertion matching plus mechanism evidence**.

This is the hardened successor to the v1 zshrc task. The v1 version was too easy
because the supervisor accepted the executor's **prose description** of what the
prompt "would" look like and eyeballed self-written render files. Here, the
hidden `expected_prompts.json` defines **machine-checkable assertions** on the
FINAL rendered prompt for each scenario (must-contain / must-not-contain
regexes, stdout-must-be-empty). The executor must actually load zsh and render
the prompt; the grader checks the rendered output against the assertions, not
the narrative.

Two things must hold together:

- the **audit** correctly identifies the entangled legacy conflicts and which
  write currently wins (several writes are dead code shadowed by a later line),
  and
- the **final config** is verified by real rendered output that satisfies the
  per-scenario assertions, while preserving the required behaviors.

The legacy config is shipped and offline, so the answer key is deterministic and
**never goes stale**.

## 2. Task Contract

Refactor `/tmp_workspace/sources/existing_zshrc` into a clean, low-noise,
verifiable zsh config that PRESERVES: aliases (`ll`,`gs`,`k`,`gp`), oh-my-zsh
plugins (`git`,`docker`,`kubectl`,`python`,`npm`) — oh-my-zsh must still load —
conda hook, nvm sourcing, PATH prepends. The prompt must show path + git status
but must NOT show username/hostname/time/runtime-version/Nerd-Font glyphs/full
deep path by default; RPROMPT removed. Validate by rendering all eight scenarios
(real output saved) including a silent non-interactive `zsh -ic true`. Save
`zshrc_final`, `zsh_prompt_audit.json`, `zsh_prompt_patch_notes.json`, eight
render files, `zsh_prompt_verification.log`, `startup_time.txt`. Offline.

## 3. Ground-Truth Reference (objective answer key)

The hidden `references/expected_prompts.json` is authoritative.

### 3.1 Legacy conflicts (audit must identify which write wins)

| id | conflict | resolution |
| -- | -------- | ---------- |
| **L1** | THREE competing `PROMPT=` assignments (before omz / after omz w/ python version / last). The **last** wins; the other two are dead code. | audit must list all three and that the last wins |
| **L2** | `ZSH_THEME=agnoster` needs a Nerd Font → conflicts with "no Nerd-Font glyphs". | drop/replace agnoster but STILL source oh-my-zsh so plugins load |
| **L3** | raw `precmd(){ vcs_info }` REPLACES oh-my-zsh's precmd (doesn't append to `precmd_functions`). | use `precmd_functions+=`/`add-zsh-hook` so omz hooks survive |
| **L5** | unguarded `echo "[motd]..."` dumps to stdout on every startup, corrupting stdout-capturing tooling (`zsh -ic 'cmd'`). | remove the echo or guard to login-only (`[[ -o login ]]`); a plain interactive guard does NOT fix it |
| L4 | `$HOME/.local/bin` prepended twice (duplicate PATH). | dedup |
| L6 | RPROMPT shows time+user@host. | remove by default |
| L7 | a PROMPT attempt injects `python --version` (runtime spam). | must not reappear |
| L8 | conda hook + nvm sourcing must be retained. | preserve both |

**Must-identify set (for full credit): L1, L2, L3, L5.** Minimum 3 of these for
partial credit. L4/L6/L7/L8 are nice-to-find.

### 3.2 Per-scenario assertions on the FINAL rendered prompt

For each scenario the rendered output must satisfy (see `expected_prompts.json`
for exact regexes):

- **plain_shell**: shows path; NO `@`, NO `HH:MM`, NO runtime version.
- **git_clean**: shows path + branch (e.g. `main`); no `@`/time.
- **git_dirty**: shows path + branch + a dirty indicator; must visibly differ
  from git_clean.
- **detached_head**: shows path + a detached indicator or short SHA (not a branch
  name); no `@`/time.
- **rebase_or_merge_state**: shows path + (ideally) rebase/merge indicator;
  doesn't crash; no time.
- **deep_path**: path compressed/truncated, not the raw full-width absolute path;
  no `@`/time.
- **python_venv_active**: may show venv NAME; must NOT show a python VERSION
  number (`\d+\.\d+\.\d+`).
- **non_interactive**: `zsh -ic true` → **stdout must be empty**; the `[motd]
  welcome back` line must NOT appear (note: an interactive guard does not fix
  this since `zsh -ic` is interactive — the echo must be removed or login-gated).

**Critical assertions (the discriminators the easy task lacked):**
`non_interactive`, `python_venv_active`, `git_dirty`, `detached_head`.

### 3.3 Preservation requirements

oh-my-zsh still sourced; aliases `ll/gs/k/gp` present; plugins load; conda hook +
nvm sourcing retained; PATH prepends present (deduped).

## 4. Expected Artifacts

`zshrc_final`, `zsh_prompt_audit.json`, `zsh_prompt_patch_notes.json`, eight
render files (real rendered output), `zsh_prompt_verification.log`,
`startup_time.txt`. Render files must contain ACTUAL rendered prompt output (e.g.
via `print -P` or a real zsh load), not prose.

## 5. Checkpoint Rubric

| ID  | What matters (objective)                                                                                                                            | Weight |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Audit identifies the must-find conflicts (L1, L2, L3, L5) and states which write wins for the competing PROMPTs. Full marks = all 4; ≥3 partial.   | 0.25   |
| CP2 | Final prompt satisfies the four critical scenario assertions (non_interactive silent, no python version in venv, git_dirty≠clean, detached head). | 0.30   |
| CP3 | Remaining scenario assertions satisfied (plain/git_clean/deep_path/rebase) with real rendered output.                                              | 0.15   |
| CP4 | Preservation intact: oh-my-zsh still loads, aliases + plugins + conda hook + nvm sourcing retained; agnoster/Nerd-Font dependency removed.          | 0.20   |
| CP5 | Render files contain ACTUAL rendered output (mechanism evidence the config was loaded), and `startup_time.txt` shows no major regression.          | 0.10   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.45`** if the prompt appearance is only described in prose / the
  render files are self-written mock text with no evidence zsh was actually
  loaded (this is the exact loophole being closed).
- **cap at `0.50`** if the solution discards the legacy config and writes an
  unrelated minimal zshrc (preservation requirements unmet — e.g. oh-my-zsh no
  longer sourced, plugins/aliases dropped).
- **cap at `0.55`** if `zsh -ic true` still leaks the `[motd]` line to stdout
  (stdout not empty) — L5 unresolved.
- **cap at `0.60`** if any critical scenario assertion fails (python version
  still in venv prompt, git_dirty indistinguishable from git_clean, user@host or
  time still present, or detached head shows a branch name).
- **cap at `0.70`** if fewer than 3 of the must-find conflicts (L1/L2/L3/L5) are
  correctly identified in the audit.
- **cap at `0.30`** if the executor used the network (offline task).

Do **not** cap or fail merely because:

- the exact prompt styling differs (colors, separator chars) — only the
  assertions matter, not aesthetics,
- the executor surfaced extra correct conflicts beyond the answer key,
- the rebase/merge scenario shows only path+branch (acceptable minimum) rather
  than a full rebase indicator,
- the deep-path compression style differs (truncate vs `~`-collapse vs tail) as
  long as it is not the raw full absolute path.

Pass requirements (`score >= 0.90`): CP1 (all 4 must-find), CP2 (all four
critical assertions), CP4 satisfied, no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor has audited and written a final config but
some scenario renders are missing or one assertion fails (recoverable), or render
files exist but lack evidence of a real zsh load.

Prefer `fail` when, after follow-ups, the render files are prose mockups with no
real load, the non-interactive leak persists, oh-my-zsh/plugins were dropped, or
the audit missed the must-find conflicts.

## 8. Hidden Reference Assets

- `references/expected_prompts.json` — objective answer key (legacy conflicts +
  per-scenario assertions). Supervisor-only.

## 9. Dynamic Content Note

None — the legacy config is shipped and offline; the answer key is deterministic.
No dynamic-content tolerance. Grade rendered output against the fixed assertions.

## 10. Notes For Rationale

- When scoring CP1, list which of L1/L2/L3/L5 the audit got, and whether it
  correctly stated the last PROMPT wins.
- When scoring CP2, quote the relevant rendered line and the assertion it
  passed/failed (e.g. non_interactive stdout contents; venv prompt containing a
  version number).
- When capping at 0.45 for prose-only renders, note the absence of any real
  `print -P`/zsh-load evidence in the transcript or render files.
- Guidance tags: `render_dont_describe`, `objective_scenario_assertions`,
  `noninteractive_must_be_silent`, `omz_must_survive_theme_swap`,
  `last_write_wins_audit`.
