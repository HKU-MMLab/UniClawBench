"""Load + validate orchestra YAML config.

The config file describes:
  - the controller host location
  - the pool of worker SSH hosts and their per-host parallelism
  - a list of priority buckets used to decide which incomplete tasks to run
    next
  - global per-model concurrency caps

See ``configs/orchestra.example.yaml`` for the shape; ``orchestra.local.yaml``
is the user's instance and is gitignored.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

LOG = logging.getLogger("orchestra.config")
DEFAULT_WORKER_REPO = "/opt/clawbench/Clawbench"
DEFAULT_WORKER_PYTHON = "/opt/clawbench-venv/bin/python"

# One-shot deprecation tracker — keys are strings like "max_retries"; we
# warn once per process per dead field so noisy configs don't flood the
# log every reload.
_DEPRECATION_WARNED: set[str] = set()


def _warn_dead_field(field_name: str, note: str) -> None:
    """Emit a one-shot ``LOG.warning`` for a config field that is parsed
    for backward compatibility but no longer enforced.  Future cleanups
    of dead config fields should reuse this helper so we get a uniform
    log shape and easy ``grep``-ability."""
    if field_name in _DEPRECATION_WARNED:
        return
    _DEPRECATION_WARNED.add(field_name)
    LOG.warning(
        "orchestra config: %r field is no longer enforced — %s",
        field_name, note,
    )


@dataclass(frozen=True)
class ControllerCfg:
    host: str
    data_root: Path
    webui_port: int


@dataclass(frozen=True)
class WorkerCfg:
    name: str
    ssh: str
    parallel: int
    skip: bool = False
    # Optional per-worker repo path override.  Empty -> fall back to the global
    # ``worker_repo``. Lets a heterogeneous worker with a different checkout
    # path run from its own clone while the rest share the default.
    repo: str = ""
    # Python interpreter used on the worker for worker_runner and helper
    # commands. Empty -> global ``worker_python`` -> prepared venv default.
    python: str = ""
    # Optional per-worker lightweight result sync. When true, worker_runner
    # transfers ONLY summary/score/transcript (~88K) per cell instead of the full
    # ~176MB attempt dir, so a flaky/high-latency link cannot strand the result
    # and phantom-lock the slot. Full artifact stays in the worker's local
    # runs/ for a later batch-sync.
    lightweight_sync: bool = False
    # Run worker_runner via `sudo` on this worker. Use this for non-root worker
    # accounts whose executor/codex containers write root-owned files that the
    # worker account cannot later remove or sync. Requires NOPASSWD sudo and
    # SSH access back to the controller from the elevated account.
    run_as_root: bool = False
    # The runtime tag this worker stamps onto its done-history rows (the
    # ``host_tag`` field in done_history/*.jsonl). Defaults to ``name.lower()``
    # which is usually enough. A worker whose runtime identity differs from
    # its config name should declare it here so ``top`` / stats can map its
    # results back to the worker. Machine-specific mappings belong in the
    # local config, never hardcoded in source.
    host_tag: str = ""

    @property
    def effective_host_tag(self) -> str:
        """The done-history ``host_tag`` key for this worker."""
        return self.host_tag or self.name.lower()


@dataclass(frozen=True)
class PriorityCfg:
    """One priority bucket.

    ``backend_in`` / ``model_in`` / ``suite_in`` / ``status_in`` are list-only
    filters.  Empty list (or missing field) means no filter on that axis.  All
    four filters are AND-combined: a task qualifies if it matches every
    non-empty filter list.  ``suite_in`` is the locale axis — EN suites
    (``101-105``) vs ZH suites (``*_zh``, ``201-205``) — used to split a status
    tier into EN-before-ZH sub-buckets (see ``split_locale`` on a tier).

    Retry-budget history: per-bucket retry budgets (the old ``max_retries``
    field) were removed in Round 12.  Round 16 went further and made
    P100/P200 fully session-only — both buckets are driven by the
    dispatcher's in-memory ``DispatchState.session_attempts`` (see
    ``stats.GLOBAL_MAX_ATTEMPTS`` and ``stats.SESSION_P200_THRESHOLD``).
    Restart releases both buckets automatically; no on-disk
    ``attempts_resets.jsonl`` ledger participates in routing.
    ``stats.LIFETIME_MAX_ATTEMPTS`` and ``release_p200.py`` are retained
    only for the legacy lifetime display used by pre-Round-16 reporting
    tools.  Old YAML configs that still carry ``max_retries:`` lines are
    silently accepted but emit a one-shot deprecation warning at load
    time (see ``_warn_dead_field``).
    """

    id: str
    label: str
    backend_in: tuple[str, ...] = ()
    model_in: tuple[str, ...] = ()
    suite_in: tuple[str, ...] = ()
    status_in: tuple[str, ...] = ()

    def matches(self, backend: str, model_dir: str, suite: str, status: str) -> bool:
        if self.backend_in and backend not in self.backend_in:
            return False
        if self.model_in and model_dir not in self.model_in:
            return False
        if self.suite_in and suite not in self.suite_in:
            return False
        if self.status_in and status not in self.status_in:
            return False
        return True


# Model-dir ↔ provider/model translation lives in lib.util.model_naming.
# The canonical model registry is configs/models.local.json — adding a
# new model = adding it there.  ``model_full_for`` is a convenience
# wrapper that caches the registry per-process.

import sys

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib.util import model_naming as _model_naming  # noqa: E402

_REGISTRY_CACHE: tuple[str, ...] | None = None


def _load_registry() -> tuple[str, ...]:
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is not None:
        return _REGISTRY_CACHE
    path = _model_naming.default_models_json_path(_REPO_ROOT)
    try:
        rows = _model_naming.load_registry(path)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"{path} is required for orchestra dispatch. Copy "
            "configs/models.example.json to configs/models.local.json and "
            "declare every matrix model there; refusing to guess provider/model "
            "from the encoded run directory."
        ) from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in model registry {path}: {exc}") from exc
    except OSError as exc:
        raise OSError(f"cannot read model registry {path}: {exc}") from exc
    _REGISTRY_CACHE = tuple(rows)
    return _REGISTRY_CACHE


def model_full_for(model_dir: str) -> str:
    """Resolve a runs-tree ``model_dir`` to the ``provider/model`` id.

    Uses ``configs/models.local.json`` as the source of truth.  Raises when
    the registry is missing/invalid or when the dir is unknown / ambiguous;
    dispatch must not guess because encoded model dirs are not reversible
    without the registry (dots and dashes collapse to the same slug).
    """
    registry = _load_registry()
    return _model_naming.decode_model_full(model_dir, registry)


_KEY_POOLS_CACHE: dict[str, list[str]] | None = None


def key_pool_labels(model_dir: str) -> list[str]:
    """Ordered executor key-pool labels for a ``model_dir`` (primary first), or
    [] if it has no pool.  The dispatcher rotates across these labels
    (rate-limit-aware); the worker resolves the chosen label to a real key.
    See ``lib/runner/key_pool.py``.

    Called on every ``reserve()`` (the dispatch hot path), so the keyPools block
    is parsed once and cached — models.local.json is static during a run.
    """
    global _KEY_POOLS_CACHE
    if _KEY_POOLS_CACHE is None:
        try:
            path = _model_naming.default_models_json_path(_REPO_ROOT)
            data = json.loads(Path(str(path)).read_text(encoding="utf-8"))
            pools = data.get("keyPools") or {}
            _KEY_POOLS_CACHE = {
                md: list(p.keys()) for md, p in pools.items() if isinstance(p, dict)
            }
        except Exception:  # noqa: BLE001 — never raise into the dispatch loop
            _KEY_POOLS_CACHE = {}
    return list(_KEY_POOLS_CACHE.get(model_dir, []))


@dataclass(frozen=True)
class CodexRoleCfg:
    """One Codex grading role: which provider + model to invoke."""

    provider: str
    model: str


@dataclass(frozen=True)
class SupervisionCfg:
    """Provider/model bindings for the two Codex grading roles.

    Lives in ``orchestra.local.yaml`` under the ``supervision:`` block
    so changing the grader model is a YAML edit, not a code change.
    ``worker_runner.py`` reads these via CLI flags the dispatcher
    threads through.
    """

    supervisor: CodexRoleCfg
    user_simulator: CodexRoleCfg


@dataclass(frozen=True)
class OrchestraConfig:
    controller: ControllerCfg
    workers: tuple[WorkerCfg, ...]
    priorities: tuple[PriorityCfg, ...]
    model_caps: dict[str, int]
    default_model_cap: int | None
    images: tuple[str, ...]
    supervision: SupervisionCfg
    # Allowlist of suite directory names to dispatch, e.g.
    # ["101_skill_usage", "201_skill_usage_zh"].  Empty = every suite under
    # tasks/ EXCEPT the 000_template / 001_smoketest scaffolding (which are
    # always excluded regardless of this list).
    suites: tuple[str, ...] = ()
    # Hard ceiling on a single SSH worker invocation (subprocess.run timeout).
    # If a worker hangs (network partition, OS freeze, stuck container) the
    # dispatcher will SIGKILL the ssh subprocess after this many seconds and
    # release the inflight slot.  Default = 24h, well above any realistic
    # single-task runtime; tasks have their own per-turn and global budgets.
    worker_timeout_seconds: int = 86400
    # Inflight rows older than this are auto-expunged from inflight.jsonl on
    # the next stats.recompute_priorities pass.  Catches the rare case where
    # a worker crashed AFTER reserving but BEFORE the SSH connection failure
    # propagated to the dispatcher (e.g. dispatcher itself crashed in the
    # window).  Default = worker_timeout_seconds + 10 min grace.
    max_inflight_age_seconds: int = 86400 + 600
    # Round-15 / P1 fix.  When True (the default), the dispatcher tracks a
    # ``dispatched_this_round`` set: any task reserved in the current wave
    # cannot be re-reserved until every task in that wave has finished
    # (drained out of inflight).  This stops the rate_limit / infra_error
    # retry-storm pattern observed in Round 14: a fast-failing task used to
    # be re-dispatched within ~5s as soon as the drain thread released it,
    # consuming a model_cap slot 3 times in 25 seconds.  Now retries are
    # naturally spaced by wave duration (typically 10–30 min on long-context
    # suites), giving rate-limited APIs time to recover.
    #
    # Set to False to revert to the pre-Round-15 behaviour for emergency
    # rollback or A/B comparison.  Should normally stay True in production.
    wave_isolation: bool = True
    # Per-CELL retry backoff (supersedes per-priority wave_isolation when > 0).
    # Instead of blocking a whole priority's wave until its slowest member
    # drains (which idles the cluster behind one slow cell), each cell is
    # paced individually: after an attempt drains, that cell cannot re-dispatch
    # until ``min(base * 2**(attempts-1), cap)`` seconds have passed.  A
    # fast-failing rate_limited cell is throttled per-cell (no retry storm);
    # unrelated cells are never blocked (no idle tail).  Fresh (never-attempted)
    # cells are never delayed.  0 disables it and falls back to wave_isolation.
    retry_backoff_base_seconds: int = 0
    retry_backoff_cap_seconds: int = 900
    # Per-task experiment retention.  After a task's attempt directory is
    # collected, prune its ``runs/<backend>/<model_dir>/<suite>/<task>/`` dir to
    # the newest N attempt subdirs (by mtime); older ones are deleted.  Keeps
    # the canonical runs/ tree from growing without bound on heavily-retried
    # tasks.  Must be >= 1.
    max_attempts_per_task: int = 3
    # Stuck-worker stall detector (see dispatch.detect_stuck_workers).  A worker
    # holding an inflight cell older than this — while it has produced no DONE in
    # the same window — is flagged (loud STUCK log) so the watchdog/operator can
    # skip+restart it.  This is DISTINCT from worker_timeout_seconds (the 24h SSH
    # ceiling) and max_inflight_age_seconds (the 24h inflight TTL): both are
    # sized to the SSH call, far too long to catch a per-cell freeze.  Size this
    # to the task executor budget + margin: max_total_seconds (1800) + 900s grace
    # = 2700s.  Detection only (no auto-release).  0 disables.
    stuck_cell_age_seconds: int = 2700
    raw: dict = field(default_factory=dict)


def _coerce_tuple(val: Any) -> tuple[str, ...]:
    if val is None:
        return ()
    if isinstance(val, (list, tuple)):
        return tuple(str(x) for x in val)
    raise ValueError(f"expected list, got {type(val).__name__}: {val!r}")


# Default STATUS ordering used when a ``matrix:`` is given without an explicit
# ``priorities:`` list.  Each entry is ``(tier_id, status_in, split_locale)``.
# The dispatcher drains tier N (across ALL matrix groups) before tier N+1: all
# groups' fresh "missing" work before any "running", before any recoverable
# retry, before executor_incomplete.  Fresh first, retries last; backends never
# coupled.  ``split_locale=False`` for every default tier — locale (EN/ZH)
# splitting is opt-in per tier via ``split_locale: true`` in the YAML.
_DEFAULT_STATUS_TIERS: tuple[tuple[str, tuple[str, ...], bool], ...] = (
    ("missing", ("missing",), False),
    ("running", ("running",), False),
    ("retry",   ("rate_limit", "infra_error", "pre_exec_failed"), False),
    ("ei",      ("executor_incomplete",), False),
)


def _matrix_groups(matrix_raw: Any) -> list[tuple[tuple[str, ...], tuple[str, ...]]]:
    """Parse a ``matrix:`` block into ``[(backends, models), ...]`` groups."""
    groups: list[tuple[tuple[str, ...], tuple[str, ...]]] = []
    if isinstance(matrix_raw, dict):
        # Cross-product mapping: every backend x every model.
        backends = _coerce_tuple(matrix_raw.get("backends"))
        models = _coerce_tuple(matrix_raw.get("models"))
        if not backends or not models:
            raise ValueError("config: matrix mapping needs non-empty 'backends' and 'models'")
        groups.append((backends, models))
    elif isinstance(matrix_raw, list):
        for i, entry in enumerate(matrix_raw):
            if not isinstance(entry, dict):
                raise ValueError(f"config: matrix[{i}] must be a mapping")
            # Accept ``backend`` (one) or ``backends`` (several sharing a model
            # set, e.g. nanobot + openclaw_edict both on the same 4 models).
            if "backends" in entry:
                backends = _coerce_tuple(entry.get("backends"))
            elif "backend" in entry:
                backends = (str(entry["backend"]),)
            else:
                raise ValueError(
                    f"config: matrix[{i}] needs a 'backend' or 'backends' key"
                )
            if not backends:
                raise ValueError(f"config: matrix[{i}] has an empty backend list")
            models = _coerce_tuple(entry.get("models"))
            if not models:
                raise ValueError(
                    f"config: matrix[{i}] (backend {backends!r}) needs a non-empty 'models' list"
                )
            groups.append((backends, models))
    else:
        raise ValueError(
            "config: 'matrix' must be a list of {backend|backends, models} "
            "entries or a {backends, models} mapping"
        )
    return groups


def _status_tiers_from_priorities(prios_raw: Any) -> tuple[tuple[str, tuple[str, ...], bool], ...]:
    """Parse a ``priorities:`` list as STATUS tiers (matrix mode).

    ``matrix:`` and ``priorities:`` are ORTHOGONAL: matrix declares the
    experiment set (backend x model), priorities declares the ORDERING ONLY.
    So in matrix mode each priorities entry is a status tier — ``{id,
    status_in, split_locale?}`` — and carries NO backend/model (declaring one is
    a conflation error).  An empty/absent priorities list falls back to the
    default order.  ``split_locale: true`` on a tier splits its per-group bucket
    into EN-before-ZH sub-buckets (suite ``*_zh`` => ZH); locale is NOT a
    backend/model conflation, so it is allowed here.
    """
    if not prios_raw:
        return _DEFAULT_STATUS_TIERS
    tiers: list[tuple[str, tuple[str, ...], bool]] = []
    for i, p in enumerate(prios_raw):
        match = p.get("match") or {}
        if match.get("backend_in") or match.get("model_in") or p.get("backend_in") or p.get("model_in"):
            raise ValueError(
                f"config: priorities[{i}] declares backend_in/model_in, but with "
                "'matrix:' present the priorities list configures ORDERING ONLY. "
                "Put the backend x model test set in 'matrix:'; leave only "
                "'status_in' (and an optional 'id'/'split_locale') in priorities."
            )
        status_in = _coerce_tuple(p.get("status_in") or match.get("status_in"))
        if not status_in:
            raise ValueError(f"config: priorities[{i}] needs a non-empty 'status_in'")
        split_locale = bool(p.get("split_locale", False))
        tiers.append((str(p.get("id", f"tier{i}")), status_in, split_locale))
    return tuple(tiers)


def _combine_matrix_and_tiers(
    groups: list[tuple[tuple[str, ...], tuple[str, ...]]],
    tiers: tuple[tuple[str, tuple[str, ...], bool], ...],
    en_suites: tuple[str, ...] = (),
    zh_suites: tuple[str, ...] = (),
) -> tuple[PriorityCfg, ...]:
    """Combine matrix groups (what) with status tiers (order) STATUS-MAJOR.

    For each status tier, emit one bucket per matrix group, then a wildcard
    catch-all.  So two groups [openclaw, nanobot+edict] under the default tiers
    yield: openclaw-missing, nanobot/edict-missing, openclaw-running,
    nanobot/edict-running, openclaw-retry, ... — fresh first, retries last,
    backends interleaved within each tier.

    When a tier has ``split_locale=True`` AND the config declares EN/ZH suites,
    each group's bucket is further split into EN-before-ZH sub-buckets — so the
    ``new`` tier with two groups yields, in order:
    ``new__openclaw__en, new__openclaw__zh,
    new__nanobot+openclaw_edict__en, new__nanobot+openclaw_edict__zh`` —
    group-major, EN-before-ZH within each group.  A split tier with no suites
    of a locale skips that locale; with no suites at all it degrades to the
    plain (locale-agnostic) bucket.
    """
    prios: list[PriorityCfg] = []
    for tier_id, statuses, split_locale in tiers:
        for backends, models in groups:
            tag = backends[0] if len(backends) == 1 else "+".join(backends)
            if split_locale and (en_suites or zh_suites):
                for loc_tag, loc_suites in (("en", en_suites), ("zh", zh_suites)):
                    if not loc_suites:
                        continue
                    prios.append(PriorityCfg(
                        id=f"{tier_id}__{tag}__{loc_tag}",
                        label=f"{tier_id}: {tag} [{loc_tag}]",
                        backend_in=backends, model_in=models,
                        suite_in=loc_suites, status_in=statuses,
                    ))
            else:
                prios.append(PriorityCfg(
                    id=f"{tier_id}__{tag}",
                    label=f"{tier_id}: {tag}",
                    backend_in=backends, model_in=models, status_in=statuses,
                ))
    # Wildcard safety net last: catches any non-terminal status not covered by
    # the explicit tiers. ``global_timeout`` is terminal; it is retried only
    # when the config declares an explicit status_in=[global_timeout] tier.
    prios.append(PriorityCfg(id="others", label="catch-all (other non-terminal)"))
    return tuple(prios)


def load(path: str | Path) -> OrchestraConfig:
    """Load and validate an orchestra config YAML."""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"orchestra config not found: {p}")

    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}

    controller_block = raw.get("controller") or {}
    if not controller_block.get("host") or not controller_block.get("data_root"):
        raise ValueError("config: 'controller.host' and 'controller.data_root' are required")
    data_root = Path(controller_block["data_root"]).expanduser()
    if not data_root.is_absolute():
        data_root = (Path.cwd() / data_root).resolve()
    controller = ControllerCfg(
        host=str(controller_block["host"]),
        data_root=data_root,
        webui_port=int(controller_block.get("webui_port", 9005)),
    )

    workers_raw = raw.get("workers") or []
    if not workers_raw:
        raise ValueError("config: 'workers' must be a non-empty list")
    workers = tuple(
        WorkerCfg(
            name=str(w["name"]),
            ssh=str(w.get("ssh", w["name"])),
            parallel=int(w.get("parallel", 1)),
            skip=bool(w.get("skip", False)),
            repo=str(w.get("repo", "")),
            python=str(w.get("python", "")),
            lightweight_sync=bool(w.get("lightweight_sync", False)),
            run_as_root=bool(w.get("run_as_root", False)),
            host_tag=str(w.get("host_tag", "")),
        )
        for w in workers_raw
    )

    prios_raw = raw.get("priorities") or []
    # Round-12 cleanup: ``max_retries`` is no longer enforced.  Emit a
    # one-shot warning if an old YAML still carries it, but never fail
    # to load (silent ignore preserves backward compatibility).
    for p in prios_raw:
        if "max_retries" in p:
            _warn_dead_field(
                "max_retries",
                "Round 16+ uses a session-only in-memory attempts ceiling "
                "(GLOBAL_MAX_ATTEMPTS for P100, SESSION_P200_THRESHOLD for "
                "P200) — both bucketed in DispatchState.session_attempts and "
                "released on dispatcher restart.  Please remove the field "
                "from your priority blocks.",
            )
            break
    # ``matrix:`` and ``priorities:`` are ORTHOGONAL and may coexist:
    #   * matrix      — the experiment set (backend x model groups): WHAT to run.
    #   * priorities  — the status-tier ORDERING: in WHAT ORDER.
    # When matrix is present they are combined STATUS-MAJOR (matrix supplies
    # backend x model, priorities supplies the status order; an absent
    # priorities list uses the default order).  With NO matrix, priorities are
    # legacy self-contained buckets that pin their own backend/model/status.
    # ``suites`` parsed here (ahead of the matrix combine) so its EN/ZH split
    # can feed locale-split priority tiers.  ZH suites are the ``*_zh`` dirs
    # (201-205); everything else is EN (101-105).
    suites = _coerce_tuple(raw.get("suites"))
    zh_suites = tuple(s for s in suites if s.endswith("_zh"))
    en_suites = tuple(s for s in suites if not s.endswith("_zh"))

    matrix_raw = raw.get("matrix")
    if matrix_raw:
        groups = _matrix_groups(matrix_raw)
        tiers = _status_tiers_from_priorities(prios_raw)
        priorities = _combine_matrix_and_tiers(groups, tiers, en_suites, zh_suites)
        # Optional operational override: lift selected backend/model cells above
        # the status-major schedule without dropping the rest of the matrix.
        # This is useful when a partially completed long run needs a specific
        # model/backend block drained first. It remains purely additive: all
        # normal matrix priorities still run after these front buckets.
        front_raw = raw.get("priority_front") or []
        if front_raw:
            tier_statuses = tuple(
                dict.fromkeys(status for _tier, statuses, _slice in tiers for status in statuses)
            )
            front: list[PriorityCfg] = []
            for i, fr in enumerate(front_raw):
                backends = _coerce_tuple(fr.get("backend_in"))
                models = _coerce_tuple(fr.get("model_in"))
                if not backends or not models:
                    raise ValueError(
                        f"config: priority_front[{i}] needs both backend_in and model_in"
                    )
                tag = "+".join(backends) + "__" + "+".join(models)
                front.append(PriorityCfg(
                    id=f"front__{tag}",
                    label=f"FRONT (jump queue): {tag}",
                    backend_in=backends,
                    model_in=models,
                    status_in=tier_statuses,
                ))
            priorities = tuple(front) + priorities
    elif prios_raw:
        priorities = tuple(
            PriorityCfg(
                id=str(p["id"]),
                label=str(p.get("label", p["id"])),
                backend_in=_coerce_tuple((p.get("match") or {}).get("backend_in")),
                model_in=_coerce_tuple((p.get("match") or {}).get("model_in")),
                status_in=_coerce_tuple((p.get("match") or {}).get("status_in")),
            )
            for p in prios_raw
        )
    else:
        priorities = ()

    caps_raw = raw.get("model_caps") or {}
    model_caps = {str(k): int(v) for k, v in caps_raw.items()}
    default_cap = raw.get("default_model_cap")
    default_model_cap = int(default_cap) if default_cap is not None else None

    images = _coerce_tuple(raw.get("images"))

    supervision_raw = raw.get("supervision") or {}
    if not isinstance(supervision_raw, dict):
        raise ValueError("config: 'supervision' must be a mapping")
    supervisor_raw = supervision_raw.get("supervisor") or {}
    user_sim_raw = supervision_raw.get("user_simulator") or {}
    for label, block in (("supervisor", supervisor_raw), ("user_simulator", user_sim_raw)):
        if not isinstance(block, dict):
            raise ValueError(f"config: 'supervision.{label}' must be a mapping")
        if not block.get("provider") or not block.get("model"):
            raise ValueError(
                f"config: 'supervision.{label}.provider' and "
                f"'supervision.{label}.model' are required"
            )
    supervision = SupervisionCfg(
        supervisor=CodexRoleCfg(
            provider=str(supervisor_raw["provider"]),
            model=str(supervisor_raw["model"]),
        ),
        user_simulator=CodexRoleCfg(
            provider=str(user_sim_raw["provider"]),
            model=str(user_sim_raw["model"]),
        ),
    )

    worker_timeout_seconds = int(raw.get("worker_timeout_seconds", 86400))
    max_inflight_age_seconds = int(
        raw.get("max_inflight_age_seconds", worker_timeout_seconds + 600)
    )
    wave_isolation = bool(raw.get("wave_isolation", True))
    retry_backoff_base_seconds = int(raw.get("retry_backoff_base_seconds", 0))
    retry_backoff_cap_seconds = int(raw.get("retry_backoff_cap_seconds", 900))
    max_attempts_per_task = int(raw.get("max_attempts_per_task", 3))
    if max_attempts_per_task < 1:
        raise ValueError("config: 'max_attempts_per_task' must be >= 1")
    stuck_cell_age_seconds = int(raw.get("stuck_cell_age_seconds", 2700))

    return OrchestraConfig(
        controller=controller,
        workers=workers,
        priorities=priorities,
        model_caps=model_caps,
        default_model_cap=default_model_cap,
        images=images,
        supervision=supervision,
        suites=suites,
        worker_timeout_seconds=worker_timeout_seconds,
        max_inflight_age_seconds=max_inflight_age_seconds,
        wave_isolation=wave_isolation,
        retry_backoff_base_seconds=retry_backoff_base_seconds,
        retry_backoff_cap_seconds=retry_backoff_cap_seconds,
        max_attempts_per_task=max_attempts_per_task,
        stuck_cell_age_seconds=stuck_cell_age_seconds,
        raw=raw,
    )


def runs_root(cfg: OrchestraConfig) -> Path:
    return cfg.controller.data_root / "runs"


def worker_repo_for(worker: WorkerCfg, cfg: OrchestraConfig, *, override: str | None = None) -> str:
    if override:
        return override
    if worker.repo:
        return worker.repo
    return str(cfg.raw.get("worker_repo") or DEFAULT_WORKER_REPO)


def worker_python_for(worker: WorkerCfg, cfg: OrchestraConfig) -> str:
    if worker.python:
        return worker.python
    return str(cfg.raw.get("worker_python") or DEFAULT_WORKER_PYTHON)


def shell_quote(value: str | Path) -> str:
    s = str(value)
    if any(c in s for c in " \t'\"$`\\"):
        return "'" + s.replace("'", "'\"'\"'") + "'"
    return s


def worker_python_cmd(worker: WorkerCfg, cfg: OrchestraConfig) -> str:
    py = shell_quote(worker_python_for(worker, cfg))
    return f"sudo -n {py}" if worker.run_as_root else py


def runtime_dir() -> Path:
    """Return the in-tree runtime/ dir (where priorities/inflight live)."""
    return Path(__file__).resolve().parent / "runtime"
