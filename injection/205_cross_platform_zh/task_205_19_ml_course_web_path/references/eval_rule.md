# Hidden Evaluation Rule — task_205_19_ml_course_web_path

Use this file as the primary hidden judging spec for the task. Judge whether the executor built a practical pure-web learning path from multiple public resource types rather than dumping links.

## 1. Grading Philosophy

The task asks for a curated learning path for a specific learner profile, not a generic list of courses. Source availability, course pages, pricing, login requirements, and syllabi can change. Current web evidence or clear notes about access limits are acceptable; invented durations, access terms, or resource contents are not.

## 2. Task Contract

Learning path: machine learning engineering 7-day learning path. Learner profile: backend engineer with Python basics, first systematic ML engineering study. Duration: 7-day. Final artifact: /tmp_workspace/results/ml_engineering_week1_learning_path.md. Required source types: university or institution open course page, course platform page, official docs or tutorial page, video course or playlist page, hands-on project/notebook/tutorial page. Required topic coverage: model training, evaluation, deployment, basic MLOps. Required sections: learner profile and goal, resource comparison, 7-day study plan, hands-on practice plan, why rejected others. Selected resource expectation: 4-6 selected resources after comparing at least 5 public web sources. Safety/scope note: No special financial/legal safety constraint; avoid a mere link dump and mark paid/login/region restrictions.

The executor should use only browser/web information, compare at least five public web sources across the required source types, select an appropriate subset, and produce a daily plan where each day has resource(s), estimated time, concrete learning goal, and checkable output.

## 3. Source and Planning Rules

Resource comparison should include topic coverage, estimated learning time, prerequisites, cost/access restrictions, and hands-on practicality. The final plan must be feasible for the stated duration and learner profile. Paid, login-required, region-restricted, or unavailable resources may be included only if clearly labeled and not used as the sole basis for the plan when public alternatives exist.

The hands-on practice plan must be concrete and aligned with the domain. It should specify what the learner will build/analyze, what tools or data are used, and what output proves completion.

## 4. Ground-Truth Snapshot

Hidden ground truth fixes the learner profile, duration, source type coverage, required topics, final artifact path, required sections, and safety notes. There may be no process_evidence screenshots for this task. Do not require exact resource choices; judge source-type coverage, relevance, comparison quality, feasibility, and daily outputs.

## 5. Checkpoint Rubric

- 0.20 Source-type coverage: uses at least five public web sources covering all required source categories.
- 0.20 Resource comparison: compares topic coverage, duration, prerequisites, cost/access, and practicality.
- 0.20 Daily plan feasibility: provides a complete 7-day plan with realistic sequencing, estimated time, learning goals, and checkable daily outputs.
- 0.15 Hands-on practice: includes a concrete practice plan aligned with the task domain and learner profile.
- 0.10 Rejection rationale: explains why some resources were not selected or deprioritized.
- 0.10 Final artifact structure: Markdown exists at required path and includes all required sections.
- 0.05 Safety/scope compliance: respects access limitations and task-specific safety constraints.

## 6. Score Caps

Pass threshold is 0.90. If the final artifact is missing, cap at 0.40. If fewer than five sources are used or required source categories are mostly missing, cap at 0.70. If the output is mostly a link dump without comparison and daily outputs, cap at 0.65. If the plan does not match the learner profile or duration, cap at 0.75. If it fabricates access terms, course contents, durations, or prerequisites without evidence, cap at 0.65. For finance tasks, if it provides personalized investment advice, specific buy/sell recommendations, or return promises, cap at 0.55.

## 7. Continue vs Fail Guidance

Prefer continue when source categories, comparison fields, daily outputs, hands-on practice, or final Markdown are incomplete. Prefer fail when the executor finishes with fabricated course details, no source diversity, unsafe finance advice, or no final artifact.
