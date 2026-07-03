# Hidden Evaluation Rule — services-injected jq + JSON ground-truth query

## 1. Grading Philosophy

This task is graded by **outcome plus mechanism evidence**.

Two things must hold together:

- the executor writes the correct answer to the designated results
  file, and
- the answer was obtained by **actually using the `jq` binary that was
  installed via the `services:` injection channel**.

The task prompt deliberately does not mention `jq` or the path it was
installed to — the executor is expected to probe the environment
(`which jq`, `command -v jq`, `ls /usr/local/bin`, reading common PATH
entries, etc.) and discover the tool on its own. Supervisors should
therefore credit runs that demonstrably exercised the shipped tool and
partially credit runs that solved the puzzle with alternative parsers
while penalizing bypass routes that install a competing copy of `jq`
from the network.

## 2. Task Contract (for reference)

The public task asks the executor to:

1. Read a JSON catalog at `/tmp_workspace/clawbench/sources/data.json`
   (each entry has `sku`, `name`, `price`, `stock`).
2. Find the **single most expensive** entry.
3. Write just that entry's `sku` code to
   `/tmp_workspace/results/answer.txt`.

The prompt hints that "whatever tooling is already available" may help
and suggests "a quick check of what's on PATH" — this is the only
pointer the executor gets toward the services-injected `jq`.

## 3. Ground-truth Reference

### 3.1 The catalog

```json
{
  "catalog": [
    {"sku": "A-101", "name": "Screwdriver",    "price":  5.49, "stock": 120},
    {"sku": "A-102", "name": "Hammer",         "price": 12.99, "stock":  45},
    {"sku": "A-103", "name": "Cordless Drill", "price": 89.00, "stock":   8},
    {"sku": "A-104", "name": "Tape Measure",   "price":  7.25, "stock": 200},
    {"sku": "A-105", "name": "Pipe Wrench",    "price": 34.50, "stock":  17}
  ]
}
```

### 3.2 Correct answer

**`A-103`** — the "Cordless Drill" at `$89.00`, which is strictly the
highest price in the catalog (next is `A-105` at `$34.50`).

### 3.3 Output format

`/tmp_workspace/results/answer.txt` must contain the literal string
`A-103`. Accepted forms after stripping leading/trailing whitespace:

- `A-103`
- `A-103\n` (with trailing newline)
- `A-103\r\n` (CRLF tolerated)

**Rejected** as "correct answer":

- `A103` (missing dash)
- `a-103` / `A_103` / `A 103` (case or separator changes)
- `"A-103"` (quoted)
- `{"sku":"A-103"}` or any JSON-wrapped form
- `A-103 Cordless Drill $89.00` (any extra tokens beyond the SKU)
- `A-105`, `A-102`, etc. (wrong row)

### 3.4 What counts as "using the services-installed jq"

The supervisor inspects the executor's transcript (exec-tool
invocations / shell commands / agent-browser calls) for at least one
call that exercises `jq`. All of the following are acceptable:

- a direct invocation: `jq '.catalog | max_by(.price) | .sku' /tmp_workspace/clawbench/sources/data.json`
- piped: `cat /tmp_workspace/clawbench/sources/data.json | jq -r '.catalog | max_by(.price).sku'`
- multi-step: `jq '.catalog' data.json | jq 'max_by(.price)' | jq -r '.sku'`
- even a probe like `which jq` or `jq --version` followed by any real
  `jq` query of `data.json` in the same turn

Signals that do **not** count as "using jq":

- the executor parses the JSON with `python3 -c 'import json ...'`
- the executor uses `grep` / `awk` / `sed` / `cut` on the raw file
- the executor hand-computes the answer by reading the file and
  eyeballing prices
- the executor uses agent-browser or an HTTP call to parse JSON

## 4. Checkpoint Rubric

| ID  | What matters (outcome)                                                                                                                                                                                                                                                                          | Weight |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | `/tmp_workspace/results/answer.txt` exists at exactly that path and is non-empty.                                                                                                                                                                                                                | 0.20   |
| CP2 | The file's content, stripped of leading/trailing whitespace, is exactly the literal `A-103` (Section 3.3 — case-sensitive, dash included).                                                                                                                                                       | 0.40   |
| CP3 | The executor's transcript shows at least one real invocation of `jq` that reads the catalog (Section 3.4). This is the primary signal that the services-injected tool was actually used.                                                                                                         | 0.25   |
| CP4 | `answer.txt` is "clean" — just the SKU (with optional trailing newline), no explanatory text, no JSON blob, no quoting, no extra lines. See Section 3.3 rejected forms.                                                                                                                            | 0.10   |
| CP5 | The executor did not substitute a competing `jq` by running `apt-get install -y jq`, `snap install jq`, `curl .../jq`, `wget .../jq`, `pip install pyjq`, etc. — the shipped `/usr/local/bin/jq` from `services/jq-installer/` is the only `jq` that should be involved.                           | 0.05   |

Total full score: `1.00`.

## 5. Scoring Policy

Apply the checkpoint weights above. Caps:

- **fail to 0.0** if `/tmp_workspace/results/answer.txt` does not
  exist. There is no partial credit path that bypasses CP1.
- **cap at `0.50`** if CP2 fails (the answer string is not `A-103`).
  Even a run that used `jq` beautifully but produced the wrong SKU
  does not meaningfully pass the smoketest.
- **cap at `0.80`** if CP2 passes but CP3 fails — i.e. the answer is
  right but the executor never actually invoked `jq` on the catalog.
  (This is the "I just used Python" case. The task is technically
  solved, but the services-injection demo is not exercised.)
- **cap at `0.90`** if the file content is correct but unclean — e.g.
  `A-103 (Cordless Drill)` or a multi-line explanation around the SKU.
  The data is there but CP4 isn't.
- **cap at `0.95`** if the executor re-installed `jq` from the network
  (apt, snap, curl of an unrelated release) instead of using the one
  the services channel shipped. The goal was to test the injection
  path; a network reinstall silently bypasses it.

Do **not** cap or fail the run merely because:

- the executor ran `which jq`, `command -v jq`, `jq --version`, or
  `ls /usr/local/bin/jq` before its real query — exploration is
  encouraged
- the executor used complex jq expressions (`max_by`, `sort_by`,
  `group_by`, `map`, etc.) — any query that produces `A-103` is fine
- the executor piped through `tr -d '\n'` or similar to strip
  whitespace from the output before saving
- the executor copied `data.json` to another path first (e.g.
  `/tmp/catalog.json`) and ran `jq` there — the source of truth is
  what was read, not the working copy

Pass requirements (`score >= 0.95` → `verdict = pass`):

- CP1 satisfied (answer.txt exists)
- CP2 satisfied (content is exactly `A-103`)
- CP3 satisfied (at least one real `jq` query in the transcript)
- CP4 satisfied (content is clean — just the SKU + optional newline)
- no cap fired (in particular, no network-based jq reinstall)

## 6. Continue vs Fail Guidance

Prefer `continue` when:

- the executor is still probing the environment (running `which`,
  `ls`, `env`) and hasn't yet found `jq`
- the executor has found `jq` but hasn't run a query yet
- the executor has run a `jq` query but hasn't written the answer
  file yet, or wrote a draft with extra text that needs cleaning
- the executor's first answer is wrong (e.g. read `stock` instead of
  `price`) and follow-ups remain

Prefer `fail` when:

- `answer.txt` is missing and no recovery path remains
- the executor claims a wrong SKU with high confidence after all
  follow-ups are exhausted
- the executor openly ignored the "check what's on PATH" hint and
  solved the problem with network-installed tools, with no chance
  of re-running

Otherwise prefer `continue`.

## 7. Dynamic Content Note

The catalog is static and shipped with the task — there is no external
state to reconcile. The answer is unconditional: `A-103`. No timezone,
locale, or network variability applies.

`jq`'s output format does not matter as long as the final answer.txt
is `A-103`. `jq -r` (raw string) produces `A-103` without quotes;
default `jq` produces `"A-103"` (quoted), which the executor should
strip. Either path is fine as long as the file on disk is clean.

## 8. Hidden Reference Assets

None shipped by default. The rubric is designed to be evaluated from
the saved artifacts plus the transcript:

- `/tmp_workspace/results/answer.txt` — inspect content
- Executor transcript — look for `jq` invocations that hit the
  catalog file

## 9. Notes For Rationale

- When capping at 0.80 for missing `jq` usage, name the actual parser
  the executor used (`python3`, `grep | awk`, etc.) so the cap is
  auditable.
- When capping at 0.95 for network reinstall, cite the specific
  command in the transcript (`apt-get install -y jq` / `curl ... jq
  > ...`). Do **not** conflate `which jq` / `command -v jq` /
  `jq --version` checks with network reinstalls — probing the
  pre-installed binary is desired behaviour.
- When CP2 passes but the content is unclean (CP4 fails), quote the
  actual first 80 chars of `answer.txt` verbatim in the rationale so
  the cleanup expectation is concrete.
- Guidance tags: `require_tool_discovery`, `ground_truth_string_match`,
  `artifact_cleanliness`, `prefer_shipped_tool_over_apt`.
