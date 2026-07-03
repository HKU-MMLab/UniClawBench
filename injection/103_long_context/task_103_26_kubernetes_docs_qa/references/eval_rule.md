# Hidden Evaluation Rule — task_103_26_kubernetes_docs_qa

Use this file as the primary hidden judging spec. Prefer outcome-oriented checkpoints.

## 1. Grading Philosophy

The supervisor should judge whether the executor read the four injected Kubernetes documentation pages and answered specific field/default/behavior questions correctly, with the right document citation — not from prior memory of Kubernetes. Answers are graded against the values that appear in the injected docs.

## 2. Task Contract

The public task gives four docs in `sources/k8s_docs/` (`deployment.md`, `service.md`, `pod-lifecycle.md`, `configmap.md`) and a list of questions, and asks the executor to answer them in `/tmp_workspace/results/k8s_docs_qa.md`, citing which doc each answer comes from. The questions target specific defaults/fields/limits that must be looked up.

## 3. Source-Selection and Target-Resolution Rules

Answers must be grounded in the injected docs. If the executor answers from memory and a value differs from the injected doc, it is scored as an error (the injected docs are the reference, even if upstream Kubernetes later changed a default).

## 4. Ground-Truth Snapshot

Hidden ground truth (`ground_truth.json`) gives the question set and answers, including:
- RollingUpdate maxUnavailable and maxSurge both default to 25%.
- .spec.replicas defaults to 1; .spec.revisionHistoryLimit defaults to 10; setting it to 0 cleans all history so the Deployment cannot roll back.
- Default Service type is ClusterIP; .spec.clusterIP = "None" creates a headless Service.
- Default Pod termination grace period is 30 seconds.
- restartPolicy values are Always / OnFailure / Never, default Always.
- A ConfigMap cannot exceed 1 MiB.
- Rolling update with 10 replicas, maxSurge=3, maxUnavailable=2: at most 13 Pods total, at least 8 available.

## 5. Checkpoint Rubric

- 0.65 Factual correctness: answers Q1-Q7 with the correct values from the docs. Award proportionally across the seven questions; a correct value with the right doc attribution earns the question's share, a wrong/missing value does not.
- 0.15 Cross-doc reasoning (Q7): correctly computes the rolling-update max-total (13) and min-available (8) from the stated parameters.
- 0.15 Evidence/citation: each answer names which doc (and ideally the field/section) it came from.
- 0.05 Deliverable: `k8s_docs_qa.md` saved at the requested path, organized by question.

## 6. Scoring Policy / Score Caps

The task passes only at score >= 0.90. Award partial credit from satisfied checkpoints but do not mark pass below 0.90.

If the executor answers mostly from memory and gets specific defaults wrong (e.g. grace period != 30s, maxSurge/maxUnavailable default != 25%, ConfigMap limit != 1 MiB), cap at 0.55. If `k8s_docs_qa.md` is missing, cap at 0.40. If answers carry no doc attribution at all, cap at 0.70.

## 7. Continue vs Fail Guidance

Prefer `continue` when some answers are present but others missing/unverified. Prefer `fail` when answers are largely wrong or no answer file is produced.

## 8. Hidden Reference Assets

- `ground_truth.json`: doc identities, question set, answers, anchors, scoring notes.
- `sources/k8s_docs/*.md`: the injected docs (also visible task sources).

## 9. Dynamic Content Note

Kubernetes docs evolve upstream; the injected pages are frozen and authoritative for this task. Judge against the injected docs, not against newer upstream versions.
