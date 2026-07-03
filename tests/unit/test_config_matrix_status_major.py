"""matrix (experiment set: backend x model) and priorities (status ordering)
are ORTHOGONAL and coexist.  With a matrix they combine STATUS-MAJOR; priorities
in matrix mode carries status_in only (backend/model is a conflation error).
Also pins the retry-backoff + max_attempts_per_task fields.
"""
from __future__ import annotations

import textwrap

import pytest

from scripts.orchestra import config as cfg_mod

_HEAD = """
controller: {host: controller, data_root: /tmp/cb, webui_port: 9015}
workers:
  - {name: worker1, ssh: worker1, parallel: 16}
supervision:
  supervisor: {provider: provider_primary, model: gpt-5.4}
  user_simulator: {provider: provider_primary, model: gpt-5.4}
suites: [101_skill_usage]
"""


def _write(tmp_path, body: str):
    p = tmp_path / "c.yaml"
    p.write_text(textwrap.dedent(_HEAD) + textwrap.dedent(body), encoding="utf-8")
    return cfg_mod.load(p)


def test_matrix_plus_priorities_combine_status_major(tmp_path):
    cfg = _write(tmp_path, """
        matrix:
          - backend: openclaw
            models: [m1, m2]
          - backends: [nanobot, openclaw_edict]
            models: [m1]
        priorities:
          - {id: missing, status_in: [missing]}
          - {id: running, status_in: [running]}
          - {id: retry,   status_in: [rate_limit, infra_error, pre_exec_failed]}
          - {id: ei,      status_in: [executor_incomplete]}
    """)
    ids = [p.id for p in cfg.priorities]
    assert ids == [
        "missing__openclaw", "missing__nanobot+openclaw_edict",
        "running__openclaw", "running__nanobot+openclaw_edict",
        "retry__openclaw",   "retry__nanobot+openclaw_edict",
        "ei__openclaw",      "ei__nanobot+openclaw_edict",
        "others",
    ]
    # matrix supplies backend x model; the priority tier supplies the status.
    grp = next(p for p in cfg.priorities if p.id == "running__nanobot+openclaw_edict")
    assert grp.backend_in == ("nanobot", "openclaw_edict")
    assert grp.model_in == ("m1",)
    assert grp.status_in == ("running",)
    oc = next(p for p in cfg.priorities if p.id == "missing__openclaw")
    assert oc.model_in == ("m1", "m2")


def test_split_locale_emits_en_before_zh_per_group(tmp_path):
    """A status tier with split_locale:true splits each matrix group's bucket
    into EN-before-ZH sub-buckets (suite ``*_zh`` => ZH).  Only the flagged
    tier splits; other tiers stay locale-agnostic."""
    p = tmp_path / "c.yaml"
    p.write_text(textwrap.dedent("""
        controller: {host: controller, data_root: /tmp/cb, webui_port: 9015}
        workers:
          - {name: worker1, ssh: worker1, parallel: 16}
        supervision:
          supervisor: {provider: provider_primary, model: gpt-5.4}
          user_simulator: {provider: provider_primary, model: gpt-5.4}
        suites: [101_skill_usage, 105_cross_platform, 201_skill_usage_zh, 205_cross_platform_zh]
        matrix:
          - backend: openclaw
            models: [m1, m2]
          - backends: [nanobot, openclaw_edict]
            models: [m1]
        priorities:
          - {id: new,   status_in: [missing, running], split_locale: true}
          - {id: retry, status_in: [rate_limit, infra_error, pre_exec_failed]}
          - {id: ei,    status_in: [executor_incomplete]}
    """), encoding="utf-8")
    cfg = cfg_mod.load(p)
    ids = [pr.id for pr in cfg.priorities]
    # new tier: group-major, EN-before-ZH within each group.  retry/ei stay
    # locale-agnostic (one bucket per group).
    assert ids == [
        "new__openclaw__en", "new__openclaw__zh",
        "new__nanobot+openclaw_edict__en", "new__nanobot+openclaw_edict__zh",
        "retry__openclaw", "retry__nanobot+openclaw_edict",
        "ei__openclaw", "ei__nanobot+openclaw_edict",
        "others",
    ]
    en = next(pr for pr in cfg.priorities if pr.id == "new__openclaw__en")
    zh = next(pr for pr in cfg.priorities if pr.id == "new__openclaw__zh")
    assert en.suite_in == ("101_skill_usage", "105_cross_platform")
    assert zh.suite_in == ("201_skill_usage_zh", "205_cross_platform_zh")
    assert en.status_in == ("missing", "running")
    assert en.backend_in == ("openclaw",) and en.model_in == ("m1", "m2")
    # non-split tier keeps no suite filter
    retry = next(pr for pr in cfg.priorities if pr.id == "retry__openclaw")
    assert retry.suite_in == ()


def test_split_locale_with_only_en_suites_degrades_to_en_bucket(tmp_path):
    """split_locale with no ZH suites emits only the EN sub-bucket (no empty
    zh bucket).  _HEAD declares a single EN suite."""
    cfg = _write(tmp_path, """
        matrix: [{backend: openclaw, models: [m1]}]
        priorities:
          - {id: new, status_in: [missing, running], split_locale: true}
    """)
    ids = [pr.id for pr in cfg.priorities]
    assert ids == ["new__openclaw__en", "others"]
    en = next(pr for pr in cfg.priorities if pr.id == "new__openclaw__en")
    assert en.suite_in == ("101_skill_usage",)


def test_matrix_without_priorities_uses_default_status_order(tmp_path):
    cfg = _write(tmp_path, """
        matrix: [{backend: openclaw, models: [m1]}]
    """)
    ids = [p.id for p in cfg.priorities]
    assert ids == ["missing__openclaw", "running__openclaw",
                   "retry__openclaw", "ei__openclaw", "others"]


def test_priorities_in_matrix_mode_may_not_pin_backend_or_model(tmp_path):
    with pytest.raises(ValueError, match="ORDERING ONLY"):
        _write(tmp_path, """
            matrix: [{backend: openclaw, models: [m1]}]
            priorities:
              - {id: t1, status_in: [missing], match: {backend_in: [openclaw]}}
        """)


def test_legacy_priorities_without_matrix_are_self_contained(tmp_path):
    cfg = _write(tmp_path, """
        priorities:
          - {id: T1, label: oc-missing, match: {backend_in: [openclaw], model_in: [m1], status_in: [missing]}}
    """)
    assert [p.id for p in cfg.priorities] == ["T1"]
    assert cfg.priorities[0].backend_in == ("openclaw",)
    assert cfg.priorities[0].model_in == ("m1",)
    assert cfg.priorities[0].status_in == ("missing",)


def test_matrix_entry_requires_backend_or_backends(tmp_path):
    with pytest.raises(ValueError, match="needs a 'backend' or 'backends'"):
        _write(tmp_path, "matrix:\n  - {models: [m1]}\n")


def test_new_fields_defaults_and_validation(tmp_path):
    cfg = _write(tmp_path, "matrix: [{backend: openclaw, models: [m1]}]\n")
    assert cfg.max_attempts_per_task == 3
    assert cfg.retry_backoff_base_seconds == 0
    assert cfg.retry_backoff_cap_seconds == 900

    cfg2 = _write(tmp_path, """
        matrix: [{backend: openclaw, models: [m1]}]
        max_attempts_per_task: 5
        retry_backoff_base_seconds: 30
        retry_backoff_cap_seconds: 600
    """)
    assert cfg2.max_attempts_per_task == 5
    assert cfg2.retry_backoff_base_seconds == 30
    assert cfg2.retry_backoff_cap_seconds == 600

    with pytest.raises(ValueError, match="max_attempts_per_task"):
        _write(tmp_path, """
            matrix: [{backend: openclaw, models: [m1]}]
            max_attempts_per_task: 0
        """)


def test_controller_data_root_resolves_to_absolute_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = _write(tmp_path, """
        controller: {host: controller, data_root: ./runtime-data, webui_port: 9015}
        matrix: [{backend: openclaw, models: [m1]}]
    """)

    assert cfg.controller.data_root == (tmp_path / "runtime-data").resolve()


def test_worker_repo_and_python_resolution(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(textwrap.dedent("""
        controller: {host: controller, data_root: /tmp/cb, webui_port: 9015}
        worker_repo: /srv/clawbench/shared
        worker_python: /srv/clawbench/venv/bin/python
        workers:
          - {name: worker1, ssh: box1, parallel: 1}
          - {name: worker2, ssh: box2, repo: /custom/repo, python: /custom/python, parallel: 1}
        supervision:
          supervisor: {provider: provider_primary, model: gpt-5.4}
          user_simulator: {provider: provider_primary, model: gpt-5.4}
        matrix: [{backend: openclaw, models: [m1]}]
    """), encoding="utf-8")
    cfg = cfg_mod.load(p)

    assert cfg_mod.worker_repo_for(cfg.workers[0], cfg) == "/srv/clawbench/shared"
    assert cfg_mod.worker_repo_for(cfg.workers[1], cfg) == "/custom/repo"
    assert cfg_mod.worker_python_for(cfg.workers[0], cfg) == "/srv/clawbench/venv/bin/python"
    assert cfg_mod.worker_python_for(cfg.workers[1], cfg) == "/custom/python"


def test_model_full_for_requires_models_registry(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg_mod, "_REGISTRY_CACHE", None)
    monkeypatch.setattr(
        cfg_mod._model_naming,
        "default_models_json_path",
        lambda repo_root: tmp_path / "missing-models.local.json",
    )

    with pytest.raises(FileNotFoundError, match="models.local.json is required"):
        cfg_mod.model_full_for("proxy-example-gpt-5-4")
