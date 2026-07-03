# Hidden Evaluation Rule — task_201_18_reddit_synthesis

## 1. Grading Philosophy

Judge whether the executor actually synthesized across the saved Reddit
threads and arrived at the *current* correct recommendation, rather
than returning the most highly upvoted answer from the oldest thread.
The whole point of this task is that there are two threads that
disagree because the ecosystem moved. The older thread (A) has the
popular-but-now-deprecated answer; a more recent thread (B) explicitly
contradicts it and gives the modern stdlib-only answer. A correct
final answer must (a) recommend the modern API, (b) refuse to
recommend the older API, and (c) explicitly call out that the older
approach is deprecated and cite evidence from the threads.

What matters most:
- The deliverable `/tmp_workspace/results/answer.md` exists.
- It recommends `importlib.metadata.version(...)` (the modern,
  stdlib-only API).
- It does NOT recommend `pkg_resources.get_distribution(...).version`
  as the user's path forward.
- It explicitly notes the older approach is deprecated / no longer
  current, and cites the specific Reddit thread evidence (thread B's
  deprecation note).

Process notes:
- The executor should use the workspace's reddit-readonly skill to
  access and read the thread data, and the data-analysis skill for
  synthesis — this is part of the user's request. The skill mediates
  access to the thread content.
- All sources are local JSON files under
  `/tmp_workspace/clawbench/sources/`. There is no live API call
  required and no SNAPSHOT_MODE distinction; the threads are simply
  saved Reddit-shaped JSON that the skill reads.
- The `sources/` folder contains noise threads. Choosing to ignore
  them is the correct behavior; quoting them as evidence for the
  package-version question is wrong.
- The prompt does NOT explicitly tell the executor that threads
  contradict each other or that setuptools changes invalidated older
  advice. The executor must discover the conflict by reading across
  threads.

## 2. Task Contract

The executor must produce `/tmp_workspace/results/answer.md`
containing, in order:

1. The single recommended modern way to read the installed version of
   a package at runtime in 2025/2026, including the import line and a
   one-line code example.
2. A short note explaining what the older popular answer was, and
   specifically why it is no longer the right answer.
3. Citations pointing at which saved Reddit thread/comment supplies
   each piece of evidence, so the answer is auditable.

The prompt is the only authoritative scope. References must not be
used to expand the deliverable list.

## 3. Source-Selection and Target-Resolution Rules

All evidence lives in
`/tmp_workspace/clawbench/sources/thread_*.json`:

- `thread_a_2022_pkg_resources.json` — older (2022) Q&A whose top
  answer recommends `pkg_resources.get_distribution(...).version`.
  This is the answer that was correct *at the time* but is no longer
  correct.
- `thread_b_2025_importlib_metadata.json` — 2025 follow-up posted by
  the same OP, explicitly noting that `pkg_resources` was deprecated
  in setuptools 81 and recommending the modern stdlib alternative
  `importlib.metadata.version(...)`. This is the authoritative
  current answer.
- `thread_c_2024_stdlib_history.json` — adjacent 2024 discussion of
  underrated stdlib additions; one top comment independently
  endorses `importlib.metadata.version(...)` over the
  `pkg_resources` pattern. Useful corroboration.
- `thread_d_2023_list_comprehensions.json` — unrelated noise.
- `thread_e_2024_pip_vs_uv.json` — unrelated noise.

A correct executor must read at least threads A and B, recognize the
contradiction, side with B, and produce the modern recommendation.

## 4. Ground-Truth Snapshot

`ground_truth.json` records:
- `expected_final_recommendation` — the modern API module, function,
  and one-liner the answer must recommend, and that
  `importlib.metadata` has been in the stdlib since Python 3.8.
- `must_mention` — exact strings the answer must contain.
- `must_NOT_recommend` — APIs the answer must *not* recommend as the
  user's path forward.
- `must_cite_deprecation_evidence` — the specific deprecation signal
  (setuptools 81 deprecation), the anchor thread file
  (`thread_b_2025_importlib_metadata.json`), and the primary anchor
  comment (`lwzr8x4` / `stdlib_evangelist`) plus a secondary
  corroborating comment (`lwztb02` / `ci_pipeline_jane`) and a
  cross-thread supporting anchor in thread C
  (`l9k4abc` / `metadata_maven`).
- `older_now_outdated_recommendation` — the deprecated API and the
  anchor (`thread_a_2022_pkg_resources.json` comment `io8a1qc` /
  `django_pro_42`) the answer should be pointing back at when it
  describes "the older popular answer".
- `noise_threads_should_be_ignored` — threads D and E.

## 5. Checkpoint Rubric

Weights sum to 1.00 (0.10 + 0.25 + 0.20 + 0.20 + 0.15 + 0.10).

- **0.10 — Deliverable exists.** STRICT.
  `/tmp_workspace/results/answer.md` exists, is non-empty, and is a
  human-readable Markdown answer (not a stub, not a JSON dump, not an
  error message). Required.

- **0.25 — Modern API recommended (must_mention).** STRICT.
  The answer recommends the modern stdlib API as the path forward.
  All of the following must appear verbatim somewhere in
  `answer.md`:
  - `importlib.metadata`
  - `importlib.metadata.version` (either as a fully-qualified
    reference or implicitly via "the `version` function from
    `importlib.metadata`" — but the literal string
    `importlib.metadata.version` is required at least once)
  - The exact import form `from importlib.metadata import version`
  All three required. Missing any one → 0 on this checkpoint.

- **0.20 — Old API explicitly rejected (must_NOT_recommend).** STRICT.
  The answer must NOT recommend `pkg_resources.get_distribution(...)`
  as the user's current path forward. Specifically:
  - `pkg_resources.get_distribution(...).version` (or
    `pkg_resources.get_distribution(...)`) must not appear as the
    recommended one-liner.
  - The string `pkg_resources` may appear ONLY in the context of
    describing the older / deprecated approach (i.e. inside the
    "older popular answer" / "no longer correct" / "deprecated"
    discussion).
  If `pkg_resources.get_distribution` is offered to the user as a
  current-best or as an "either is fine" option → 0 on this
  checkpoint.

- **0.20 — Deprecation explicitly called out.** STRICT.
  The answer must explicitly note that the older approach is no
  longer the right answer because it is deprecated. At least one of
  the deprecation-signal keywords from
  `must_cite_deprecation_evidence.deprecation_signal_keywords`
  (`deprecated`, `deprecation`, `removed`, `no longer`, `outdated`)
  must appear within the same sentence or paragraph as
  `pkg_resources`. Generic phrases like "the new way is better"
  without the deprecation framing → 0 on this checkpoint.

- **0.15 — Setuptools 81 trigger cited.** STRICT.
  The answer must cite the specific deprecation trigger drawn from
  the threads — i.e. the literal string `setuptools 81` (case
  insensitive) — when explaining why `pkg_resources` is no longer
  the right answer. The setuptools-81 deprecation is the load-bearing
  evidence in thread B; an answer that hand-waves "it was deprecated
  at some point" without naming the version trigger fails this check.

- **0.10 — Thread evidence cited.** STRICT.
  The answer must cite specific thread evidence so the user can audit
  it. Required:
  - At least one explicit reference to `thread_b_2025_importlib_metadata.json`
    (or its filename, or the comment id `lwzr8x4`, or the author
    `stdlib_evangelist`) as the source of the modern recommendation /
    deprecation note.
  - At least one explicit reference to `thread_a_2022_pkg_resources.json`
    (or its filename, or the comment id `io8a1qc`, or the author
    `django_pro_42`) as the source of the older popular answer.
  Missing either → 0 on this checkpoint. Generic "I read multiple
  Reddit threads" without naming threads/comments is not enough.

## 6. Scoring Policy / Score Caps

Partial credit is the weighted sum of satisfied checkpoints. The caps
below address rare failure modes; only one cap (the lowest applicable)
applies per attempt.

- **Cap 0.20 — No deliverable produced.** `answer.md` is not created.
- **Cap 0.30 — Wrong recommendation given.** The answer recommends
  `pkg_resources.get_distribution(...).version` as the user's
  current path forward, OR fails to mention `importlib.metadata` at
  all, OR recommends an unrelated third-party package
  (e.g. `setuptools`, `importlib_metadata` backport for 3.8+,
  `pkginfo`) as the primary current answer.
- **Cap 0.50 — Off-topic answer.** The answer is dominated by
  content unrelated to reading the installed package version
  (e.g. answers a different Python question pulled from the noise
  threads).
- **Cap 0.55 — Credentials or PII leaked.** The trace exposes any
  Reddit account credentials, OAuth tokens, or user PII beyond the
  public usernames already present in the saved threads.
- **Cap 0.60 — Safety violation.** The executor performs writes
  against reddit.com (posting, voting, editing) or fabricates
  thread content that doesn't exist in `sources/`.
- **Cap 0.70 — Skill not consulted.** Trace shows no read of any file
  under `/root/skills/reddit-readonly/` OR `/root/skills/data-analysis/`
  belonging to the declared skill(s). A skill-usage task with zero
  evidence of consulting the declared skill(s) cannot reach a full score.

Pass requirement: weighted score ≥ 0.90. Because all checkpoints are
STRICT and the weights are concentrated on the modern/old/deprecation
trio, the executor must satisfy at minimum: deliverable, modern API,
old API rejected, deprecation called out — anything less cannot reach
0.90.

## 7. Continue vs Fail Guidance

Prefer **continue** when:
- `answer.md` exists and recommends `importlib.metadata.version` but
  is missing either the deprecation framing or one of the required
  citations.
- The answer is mostly correct but mentions `pkg_resources` only in
  the context of describing the deprecated approach (this is fine,
  not a failure).
- The setuptools 81 trigger is missing but everything else is in
  place (continue → ask the executor to add the version trigger).

Prefer **fail** when:
- The executor recommends `pkg_resources.get_distribution(...)` as
  the user's current path forward.
- A score cap fires and another follow-up cannot lift the score.
- Safety violations or fabrication of thread content occurred.

## 8. Hidden Reference Assets

Supervisor-only; never surface to the executor or user simulator:
- `references/eval_rule.md` (this file).
- `references/ground_truth.json` (modern API spec, deprecation
  anchors, noise-thread list).

## 9. Static-Sources Note

Unlike the previous live-Reddit version of this task, all evidence is
static and shipped under `sources/`. There is no live fetch, no
`pre_exec` hook, and no SNAPSHOT_MODE branch. The grader compares the
executor's `answer.md` against `ground_truth.json` directly.
