# Hidden Evaluation Rule — Exploration v2 · Offline kustomize YAML conflict reconciliation (objective ground truth)

## 1. Grading Philosophy

This is an **offline reconciliation / audit** task graded by **objective
ground-truth matching plus mechanism evidence**.

Unlike the v1 k8s-docs task it replaces, this task is **not** graded by a
supervisor eyeballing whether the output "looks clean". The fixture is a fixed,
shipped kustomize repo whose effective state was computed with a real YAML
parser (PyYAML safe_load) + strategic-merge + kustomize image-transformer
semantics. The hidden `ground_truth.json` is the **objective answer key**. The
executor's findings are checked against it.

Two things must hold together:

- the executor **detected the real conflicts** (a fixed set of objectively-true
  conflicts, several of which are invisible unless the YAML is actually parsed),
  and
- the executor **reconciled the correct effective values** per environment.

Because the fixture is fully offline and static, this task **never goes stale**
and has a single deterministic answer key.

## 2. Task Contract

The executor audits the kustomize repo at
`/tmp_workspace/clawbench/sources/k8s_config/` (base + staging/prod overlays)
and produces:

- `yaml_conflicts.json` — every conflict found (id/type/files/object/why +
  effective-vs-shadowed value),
- `yaml_resolved.json` — reconciled effective state per env (effective
  `orders-config` data, effective orders image, effective replica count),
- `yaml_method.json` — how it parsed/reconciled (reproducibility).

No network (the task is offline).

## 3. Ground-Truth Reference (objective answer key)

The hidden `references/ground_truth.json` is authoritative. Summary:

### 3.1 The conflicts (objectively true)

| id | type | what | effective vs shadowed |
| -- | ---- | ---- | --------------------- |
| **C1** | duplicate key | `base/configmap.yaml` defines `data.LOG_LEVEL` twice (`info` then `debug`) | effective **`debug`**, shadowed `info` |
| **C3** | type coercion | `TLS_ENABLED: no` (unquoted) in base Deployment env | parses as **boolean `false`**, not string `"no"`; invalid env value |
| **C4** | transformer vs patch (staging) | staging patch image `:1.4.0` overridden by images-transformer `newTag 1.5.0-rc.1` | effective **`orders:1.5.0-rc.1`** |
| **C5** | transformer vs patch (prod) | prod patch image `:1.4.2` overridden by images-transformer `newTag 1.6.0` | effective **`orders:1.6.0`**, loser `1.4.2` |
| **C6** | replicas under HPA (prod) | prod patch pins `replicas: 5` while prod HPA targets the same Deployment (min4/max10) | replicas **should not be pinned**; HPA (4..10) governs |
| C2 | anchor/alias (nice-to-find) | `metrics-sidecar.resources` is `*default-resources` aliasing the orders container's `&default-resources` | both share identical block |

**Must-find set (for full credit): C1, C3, C4, C5, C6.** C2 is bonus
(nice-to-find), not required.

`minimum_conflicts_for_credit = 4` of the must-find set.

### 3.2 Effective reconciled values (objective)

Effective `orders-config` ConfigMap data:

- **base**: LOG_LEVEL=`debug`, MAX_CONNECTIONS=`100`, FEATURE_CHECKOUT_V2=`false`, REGION=`us-east-1`, CACHE_TTL_SECONDS=`300`
- **staging**: LOG_LEVEL=`warn`, MAX_CONNECTIONS=`150`, FEATURE_CHECKOUT_V2=`true`, REGION=`us-east-1`, CACHE_TTL_SECONDS=`300`
- **prod**: LOG_LEVEL=`error`, MAX_CONNECTIONS=`500`, FEATURE_CHECKOUT_V2=`true`, REGION=`us-west-2`, CACHE_TTL_SECONDS=`300`

Effective orders image: base `1.4.0`, **staging `1.5.0-rc.1`**, **prod `1.6.0`**.

Effective replicas: base `2`, staging `3`, **prod = HPA-governed (4..10), not the
pinned 5**.

### 3.3 Acceptance notes

- Naming/format of the executor's conflict ids is free; match on the **substance**
  (which file/object/key and the effective-vs-shadowed value), not on the literal
  id string.
- The executor may legitimately report extra real conflicts (e.g. noting REGION
  is unset in staging patch so inherits base us-east-1); do not penalize correct
  extras. Penalize only fabricated/incorrect conflicts.

## 4. Expected Artifacts

- `/tmp_workspace/results/yaml_conflicts.json`
- `/tmp_workspace/results/yaml_resolved.json`
- `/tmp_workspace/results/yaml_method.json`

Missing `yaml_conflicts.json` or `yaml_resolved.json` is a serious gap (caps).

## 5. Checkpoint Rubric

| ID  | What matters (objective)                                                                                                                          | Weight |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Conflicts detected: at least the 4-of-5 must-find set (C1, C3, C4, C5, C6), each with correct file/object and a correct effective-vs-shadowed value. Full marks require all 5. | 0.35   |
| CP2 | Effective ConfigMap reconciliation correct for staging AND prod (the per-key effective values in §3.2), including the base `LOG_LEVEL=debug` dup-key result. | 0.25   |
| CP3 | Effective image resolution correct: staging `1.5.0-rc.1` and prod `1.6.0` (i.e. transformer-wins, not the patch's literal tag).                  | 0.20   |
| CP4 | Replicas-under-HPA conflict correctly characterized for prod (static replicas:5 should not be pinned; HPA min4/max10 governs).                    | 0.10   |
| CP5 | `yaml_method.json` shows the YAML was actually parsed (tool/command evidence), making the audit reproducible — not eyeballed.                     | 0.10   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.45`** if the executor only eyeballed/described the files without
  actually parsing them (no parser/tool evidence) AND missed any parse-only
  conflict (C1 dup-key, C3 boolean, or the transformer-override images).
- **cap at `0.55`** if `yaml_conflicts.json` or `yaml_resolved.json` is missing.
- **cap at `0.60`** if fewer than 4 of the 5 must-find conflicts are correctly
  identified.
- **cap at `0.70`** if the image resolution is wrong (reported the patch's
  literal tag `1.4.0`/`1.4.2` as effective instead of the transformer tag) —
  this is the central "written ≠ deployed" trap.
- **cap at `0.75`** if the duplicate-key result is wrong (reported
  `LOG_LEVEL=info` for base instead of the effective `debug`).
- **cap at `0.30`** if the executor used the network / fetched anything (offline
  task) or audited files other than the shipped fixture.

Do **not** cap or fail merely because:

- the executor's conflict ids/labels differ from the ground-truth ids — match on
  substance,
- C2 (anchor/alias) was not reported — it's bonus, not required,
- the executor reported additional correct conflicts beyond the answer key,
- the executor used `python -c "import yaml"`, `yq`, `kustomize build`, or any
  legitimate parser — any real parse is fine (and `kustomize build` is an
  excellent cross-check if available).

Pass requirements (`score >= 0.90`): CP1 (all 5 must-find), CP2, CP3 satisfied,
CP4 satisfied, no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor has parsed the files and found some conflicts
but is still reconciling effective values, or has the conflicts but hasn't
written `yaml_resolved.json`.

Prefer `fail` when, after follow-ups, the executor only narrated the files
without parsing, reported the patch's literal image tags as effective, or
produced a conflict list with major fabricated entries and missing the must-find
set.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — the objective answer key (conflicts +
  effective values). Supervisor-only.

## 9. Dynamic Content Note

None — the fixture is fully offline and static. There is exactly one correct
answer key (`ground_truth.json`), computed with a real parser. No
dynamic-content tolerance applies; do not accept "the files might mean something
else" hand-waving against the objective resolution.

## 10. Notes For Rationale

- When scoring CP1, list which of C1/C3/C4/C5/C6 the executor got right/wrong by
  substance.
- When capping for image resolution (CP3 / cap 0.70), quote the executor's
  reported effective image vs the ground-truth transformer tag.
- When capping for the dup-key (cap 0.75), quote the executor's reported base
  `LOG_LEVEL` vs `debug`.
- Guidance tags: `parse_dont_eyeball`, `objective_ground_truth_match`,
  `kustomize_transformer_wins`, `replicas_under_hpa_conflict`,
  `offline_deterministic`.
