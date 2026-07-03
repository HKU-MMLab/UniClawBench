# Hidden Evaluation Rule — task_205_18_3dcv_web_review

Use this file as the primary hidden judging spec for the task. Judge whether the executor performed a realistic pure-web paper and repository reproduction-readiness review in the requested domain.

## 1. Grading Philosophy

The goal is not to summarize a paper only; it is to decide whether a recent paper in the specified domain is worth attempting to reproduce in one week. Papers, repositories, issues, model/data links, and README instructions change over time. Current web evidence or clearly documented absence is required; invented repository metrics or dependencies should be penalized.

## 2. Task Contract

Domain: 3D Gaussian Splatting / NeRF accelerated rendering / 3D scene reconstruction. Minimum publication year: 2026. Final artifact: /tmp_workspace/results/gaussian_splatting_reproduction_web_review.md. Required sections: paper, repo activity, model/data dependencies, reproduction risk, 1-week verdict (yes/no/maybe). Required repository checks: official or author-provided GitHub repository when available, stars or equivalent activity, open issues or issue status, recent update time, README/setup guidance, model/data/project page dependencies when referenced. Verdict requirement: yes / no / maybe with practical reproduction-risk rationale.

The executor should use only browser/web information, choose a paper that is clearly in scope and year-qualified, find the official or author-provided repository when available, inspect repository activity and reproduction guidance, check model/data/project-page dependencies when referenced, and write a practical yes/no/maybe one-week verdict.

## 3. Source and Scope Rules

The selected paper must be from 2026 or later and clearly relevant to 3D Gaussian Splatting / NeRF accelerated rendering / 3D scene reconstruction. A generic adjacent paper is acceptable only if the connection to the requested domain is explicit and supported by the source. Repository links should be official, author-provided, or clearly associated with the paper; random unofficial reimplementations should not be treated as official unless labeled as such.

If no official repository exists, the executor may still finish by clearly stating that absence and basing the verdict on available sources, but it should not invent repository metrics. If model/data dependencies are absent, say so explicitly.

## 4. Ground-Truth Snapshot

Hidden ground truth fixes the domain, minimum year, required output path, required sections, and repository/dependency checks. There may be no process_evidence screenshots for this task. Do not require exact paper choice or exact metrics; judge whether the chosen sources satisfy the task scope and whether claims are auditable.

## 5. Checkpoint Rubric

- 0.25 Paper selection: paper is from the required year or later and clearly relevant to the target domain.
- 0.20 Source traceability: includes paper title, paper link, venue/year, and source URLs sufficient to audit the choice.
- 0.20 Repository review: identifies official/author repository when available and records activity metrics such as stars, issues, recent update, and README/setup guidance.
- 0.15 Dependency/reproduction-risk analysis: checks model/data/project-page dependencies when referenced and discusses practical risks such as setup, compute, data, training time, or maintenance.
- 0.10 Verdict quality: gives a clear yes/no/maybe one-week verdict with concise reasoning.
- 0.10 Final artifact structure: Markdown exists at required path and includes all required sections.

## 6. Score Caps

Pass threshold is 0.90. If the final artifact is missing, cap at 0.40. If the chosen paper is outside the target domain or older than the required year, cap at 0.60. If repository metrics or dependency claims are fabricated, cap at 0.65. If no repository is found and the executor fails to clearly explain that absence, cap at 0.75. If the output is only a summary or link list without reproduction-readiness judgment, cap at 0.70.

## 7. Continue vs Fail Guidance

Prefer continue when the paper is not clearly in scope, repository/dependency checks are incomplete, the verdict is missing, or the final Markdown is missing. Prefer fail when the executor finishes with fabricated metrics, wrong domain/year, no auditable sources, or no final artifact.
