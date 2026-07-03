"""Clawbench orchestra — distributed task dispatch layer.

This package provides the distributed dispatcher: a single coherent set of
modules that run on a "controller" host (dispatcher / data store / webui) and
push individual tasks out to a configurable pool of worker SSH hosts.

Top-level modules
-----------------

``config``
    Load + validate ``configs/orchestra.local.yaml``.

``stats``
    Walk ``runs/`` to compute the current best status per task and bin
    incomplete tasks into the priority buckets defined in the config.
    Outputs ``runtime/priorities.jsonl``.

``refresh_summary``
    Rebuild each task's ``summary.json`` from its ``p*-*`` attempt subdirs so
    the webui can pick the best attempt without an aggregator step.

``dispatch``
    The main loop: refresh summaries → recompute priorities → walk buckets
    top-down, picking the next runnable task that respects worker capacity,
    global model caps, and inflight locking.

``worker_runner``
    Lightweight CLI invoked by ``dispatch`` over SSH on a worker.  Runs a
    single task via ``scripts/run_eval.py``, rsyncs the resulting attempt
    directory back to the controller, then deletes the local copy.

``top``
    Cursor-positioned terminal monitor that reports per-worker progress,
    cluster-wide model concurrency, recent failures, and node CPU/MEM/disk.

``prepare_node``
    Idempotent worker provisioning: apt packages, Python venv, docker images.
"""

__all__ = [
    "config",
    "stats",
    "refresh_summary",
    "dispatch",
    "worker_runner",
    "top",
    "prepare_node",
]
