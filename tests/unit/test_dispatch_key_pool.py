"""DispatchState.select_model_key: rate-limit-aware key-pool rotation."""
from __future__ import annotations

import time
import types

from scripts.orchestra import dispatch as dmod
from scripts.orchestra import config as cfg_mod


def _state(cap=900):
    cfg = types.SimpleNamespace(retry_backoff_cap_seconds=cap)
    return dmod.DispatchState(cfg=cfg, workers=[])


def test_no_pool_returns_none(monkeypatch):
    monkeypatch.setattr(cfg_mod, "key_pool_labels", lambda md: [])
    assert _state().select_model_key("m") is None


def test_round_robin_in_pool_order(monkeypatch):
    monkeypatch.setattr(cfg_mod, "key_pool_labels", lambda md: ["primary", "aux1", "aux2"])
    s = _state()
    got = [s.select_model_key("m") for _ in range(7)]
    assert got == ["primary", "aux1", "aux2", "primary", "aux1", "aux2", "primary"]


def test_skips_recently_rate_limited_label(monkeypatch):
    monkeypatch.setattr(cfg_mod, "key_pool_labels", lambda md: ["primary", "aux1", "aux2"])
    s = _state()
    s.key_pool_hot[("m", "aux1")] = time.time()      # aux1 just got a 429
    assert s.select_model_key("m") == "primary"       # cursor 0 -> primary, advance to 1
    assert s.select_model_key("m") == "aux2"          # cursor 1 -> aux1 is hot -> skip to aux2


def test_all_hot_picks_least_recently_hot(monkeypatch):
    monkeypatch.setattr(cfg_mod, "key_pool_labels", lambda md: ["primary", "aux1"])
    s = _state()
    now = time.time()
    s.key_pool_hot[("m", "primary")] = now            # hotter
    s.key_pool_hot[("m", "aux1")] = now - 100          # cooler (older 429)
    assert s.select_model_key("m") == "aux1"           # always make progress on the least-bad key


def test_hot_label_recovers_after_window(monkeypatch):
    monkeypatch.setattr(cfg_mod, "key_pool_labels", lambda md: ["primary", "aux1"])
    s = _state(cap=900)
    s.key_pool_hot[("m", "aux1")] = time.time() - 1000  # older than the 900s window -> cool again
    assert [s.select_model_key("m") for _ in range(2)] == ["primary", "aux1"]
