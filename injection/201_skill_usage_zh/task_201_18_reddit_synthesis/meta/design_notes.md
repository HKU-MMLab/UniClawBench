# Design notes — task_101_18_reddit_synthesis

Internal-only archive of revision history and design choices. Not
injected into the executor or user simulator.

## Lineage

- Hard-tier task, schema b. Live Reddit metadata plus top-comment
  anchors and topic-cluster anchors.
- Iteration history (paraphrased from earlier eval_rule headers):
  - Initial draft: rewarded only `post.json` keys; allowed paraphrased
    comment bodies; no snapshot fallback.
  - Mid revision: split top-comment matching from comment-score drift;
    introduced topic-cluster coverage requirement.
  - Hard-v8 revision (pre-rewrite): added an explicit dual-path
    (live JSON vs local snapshot) source-selection rule, hardened the
    "no HTML scraping" cap, and added a "comment bodies preserved
    verbatim" checkpoint to discourage executors from summarizing
    comments inline.
- Current rewrite normalizes to the 9-section template, removes
  benchmark-construction language and version markers, and reshapes
  score caps so they target rare extreme-failure modes rather than
  restating per-checkpoint requirements.

## Cap-design rationale

Caps were re-aimed at edge cases the rubric cannot otherwise express:
- No deliverables (0.20): nothing to grade.
- Fabricated thread content (0.30): the executor invented a thread
  rather than fetching anything.
- Total scope blowout (0.50): the deliverable describes a different
  thread entirely.
- Credentials / PII leaked (0.55): the trace must not leak Reddit
  credentials, OAuth tokens, or commenter PII beyond public usernames.
- Safety violation (0.60): writes against reddit.com, ban-inviting
  rate-limit evasion, or attempts to deanonymize commenters.

Removed from caps (now expressed via rubric weighting only):
- "HTML-only fetch" penalty (was a 0.70 cap): the rubric already
  rewards structured fetches via the deliverables and the metadata
  checkpoints; HTML-scraped output that happens to land on the right
  fields can still earn partial credit.
- "Fewer than three top comments verbatim" (was a 0.65 cap):
  subsumed by the new "comment bodies preserved verbatim" checkpoint
  and the top-comment coverage checkpoint.
- "No declared skill consulted" (was a 0.89 cap): supervisor cannot
  reliably verify skill consultation; this is now reflected only in
  the rubric (skill use is part of the user's request but not a
  grading anchor).

## Ground-truth maintenance

`ops/populate.py` regenerates `references/ground_truth.json` and
`sources/reddit_snapshot.json` from the same Reddit JSON pull at
pre-exec. Drift tolerances live inside `ground_truth.tolerance` so the
supervisor and the populate script stay in lockstep. If Reddit changes
its top-window heuristic, only the tolerances and `min_topic_clusters`
should need adjusting; the rubric structure is agnostic to those
numbers.

## v8 hardening round 2 (2026-04-29)

- Round-1 measurements showed opus-4.6 capping at 1.00 on this task. The
  fix targets implicit multi-part output: the task prompt now also asks
  for a multi-lens narrative in `thread_report.md` ("what the room is
  arguing about, who's nodding along, who's pushing back, which tools
  keep getting name-dropped, what an engineering lead could take away,
  how the participants are showing up"). The five dimensions are
  intentionally not enumerated — they have to be inferred from the
  casual user voice.
- New §5 anchor at weight 0.10 → bumped to 0.12 to track the round-1
  recipe. The five dimension keys live in
  `ground_truth.topic_dimensions` (`major_themes`,
  `top_supporting_dissenting_opinions`, `tech_stack_mentioned`,
  `actionable_takeaways`, `participation_profile`) with
  `min_topic_dimensions_covered=4`.
- Rebalance to keep weights = 1.00: Deliverables 0.15→0.12 (-0.03), Top
  comments coverage 0.20→0.18 (-0.02), Topic clusters 0.15→0.12
  (-0.03), Verbatim bodies 0.10→0.06 (-0.04). Total -0.12. New 5.8 =
  +0.12. Final total: 0.12+0.15+0.18+0.15+0.12+0.10+0.06+0.12 = 1.00.
- Score cap numbers in §6 untouched; success_threshold in YAML
  untouched.
- Both prompt variants (`task` and `task_snapshot`) updated in lockstep
  so live-fetch and snapshot paths converge on the same multi-lens
  narrative requirement.

## v8 hardening round 5 (2026-04-29)

Round-2 dimension anchor (0.12, ≥4-of-5) was insufficient on its own —
opus-class executors hit cap 0.94 by satisfying every non-anchor
checkpoint plus a partial dimension match. This round adds a second §5
anchor "Comment / cluster anchor precision" at weight 0.08 that requires
the deliverable package to reference, by exact comment id, exact author
handle, or supporting cluster keyword, ≥4 of 5 specific anchors:
`nma5ikp` / `rangoric` (premature-optimization), `nma84cw` / `pdpi`
(three-stage scale economics), `nma58so` / `kane49` (pushback),
`nma603k` / `Radstrom` (scale magnifies savings), `nma7qlm` /
`Farados55` (linkedin-slop meta-complaint). Stepped credit: ≥4/5 →
0.08, exactly 3/5 → 0.04, ≤2/5 → 0.00. To rebalance to 1.00, the two
heaviest non-anchor checkpoints lose 0.04 each: Top comments coverage
0.18 → 0.14 (-0.04) and Post metadata fidelity 0.15 → 0.11 (-0.04).
First anchor (Topic dimension coverage at 0.12) and all other weights
unchanged. Score caps and success_threshold unchanged. Final weights:
0.12 + 0.11 + 0.14 + 0.15 + 0.12 + 0.10 + 0.06 + 0.12 + 0.08 = 1.00.

## Review pass (2026-04-30)

Per-task user feedback (review_record.md task 18) drove a full
redesign. The previous version was a live-Reddit comment-summarization
exercise: the executor either fetched `<permalink>.json` or read a
local `reddit_snapshot.json`, then produced two deliverables
(`post.json` + `thread_report.md`) summarizing the discussion. User
feedback:

1. The skill being used (`reddit-readonly`) reads public JSON and
   doesn't actually need API credentials, so the SNAPSHOT_MODE
   distinction was extra ceremony. Snapshot-only is fine — just put
   the data in `sources/` and don't gate on a mode flag.
2. The previous task was too easy: summarizing a single thread is the
   one thing modern LLMs are very good at. To make it actually require
   skill-aware multi-source reasoning, the task now spans multiple
   threads where one thread directly contradicts another, and the
   correct final answer must reject the older popular answer.

### Redesign

- **Sources** (5 threads under `sources/`):
  - `thread_a_2022_pkg_resources.json` — older r/learnpython Q&A from
    2022. Top answer: use `pkg_resources.get_distribution("pkg").version`.
  - `thread_b_2025_importlib_metadata.json` — same OP, 2025 follow-up
    explicitly noting that `pkg_resources` was deprecated in
    setuptools 81 and recommending `importlib.metadata.version(...)`
    as the modern stdlib answer.
  - `thread_c_2024_stdlib_history.json` — adjacent r/Python thread on
    underrated stdlib additions; one top comment independently
    endorses `importlib.metadata.version(...)` over `pkg_resources`.
  - `thread_d_2023_list_comprehensions.json` — noise (unrelated
    Python style question).
  - `thread_e_2024_pip_vs_uv.json` — noise (unrelated tooling
    discussion).
- **No SNAPSHOT_MODE.** Removed `pre_exec: ops/populate.py`, deleted
  the `ops/` directory and its `populate.py`, removed
  `pre_exec_parallel_safe`. All sources are now static, ship in the
  repo, and are listed under `sources:` in the YAML.
- **Topic chosen** is a real, well-known Python deprecation
  (`pkg_resources` → `importlib.metadata`, triggered by setuptools
  81). It has the structural property the task needs: the older
  highly-upvoted answer was correct at the time and is concretely
  wrong now, with a specific, namable deprecation trigger.

### Prompt rewrite (English, ENGLISH)

The two prompt variants (`task` and `task_snapshot`) were collapsed
into one `task` prompt, in English. First paragraph mentions the
skills naturally ("use the Reddit-reading and light data-analysis
skills in the workspace"). The user voice is casual and goal-oriented
(asking for the right modern way to read package version at runtime),
not a checklist. The single deliverable is now
`/tmp_workspace/results/answer.md` with three implicit parts (modern
recommendation + why-old-is-wrong + thread citations). No brackets
in the prompt. Skill checkpoint coverage is preserved through the
required citations and the use of multiple sources.

### Eval / GT / §5

- §5 fully rewritten to 6 STRICT checkpoints with weights:
  0.10 + 0.25 + 0.20 + 0.20 + 0.15 + 0.10 = 1.00.
  - 0.10 — Deliverable exists.
  - 0.25 — Modern API recommended (`importlib.metadata`,
    `importlib.metadata.version`, `from importlib.metadata import version`).
  - 0.20 — Old API explicitly rejected (no
    `pkg_resources.get_distribution(...)` recommendation as path
    forward).
  - 0.20 — Deprecation explicitly called out (deprecation-signal
    keyword in the same context as `pkg_resources`).
  - 0.15 — Setuptools 81 trigger cited.
  - 0.10 — Thread evidence cited (thread A and thread B both
    referenced).
- §6 score caps re-aimed at the new failure modes: no deliverable
  (0.20), wrong recommendation (0.30), off-topic (0.50), credentials
  leaked (0.55), safety / fabrication (0.60). Numbers within the
  existing cap floors — no cap loosened.
- `ground_truth.json` rewritten with `expected_final_recommendation`,
  `must_mention`, `must_NOT_recommend`, `must_cite_deprecation_evidence`
  (with anchor thread file, anchor comment ids, and the
  `setuptools 81` deprecation trigger), and
  `older_now_outdated_recommendation` pointing at thread A.
- All previous live-Reddit fields (`top_comment_anchors`,
  `topic_clusters`, drift tolerances, `topic_dimensions`) are
  removed — they no longer apply.

### Sanity check

§5 weights: 0.10 + 0.25 + 0.20 + 0.20 + 0.15 + 0.10 = 1.00. Pass.
All checkpoints STRICT (no "≥ n/m" looseness). The hardest single
checkpoint (Modern API recommended, 0.25) demands all three exact
strings; failing it cannot be compensated by other CPs to reach 0.90.
The success_threshold (0.9) is still reachable when the executor
follows the threads correctly.
