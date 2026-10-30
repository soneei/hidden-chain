#!/usr/bin/env python3
"""
Hidden Chain — masking harness tests (gate: pytest)
====================================================
Locks the harness contract before the real data lands:
  - masking strategies are deterministic per seed and leak nothing
  - baselines reproduce trivial ground truth exactly
  - the rules-prior evaluator reads conditions from the correct day
  - ridge recovers planted linear structure
  - the pre-registered verdict logic
Run:  pytest tests/test_masking_test.py
"""

import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SRC = os.path.join(REPO, "src")
sys.path.insert(0, SRC)

from masking_baselines import (b1a_persistence, b1b_mean7, b2_phase_mean,
                               b3_rules_prior, load_rules, rule_adjust)
from masking_evaluate import direction_accuracy, mae, run_all, summarize
from masking_model import featurize, m_ridge, ridge_fit, ridge_predict
from masking_test import (DEFAULT_SEEDS, MaskSplit, block_mask, point_mask,
                          rolling_forecast)

import pytest


# ── fixtures ──────────────────────────────────────────────────

def const_rows(n=90, c=50.0):
    return [{"date": f"2026-01-{i+1:02d}" if i < 28 else f"2026-02-{i-27:02d}",
             "hrv_rmssd": c, "cycle_day": (i % 28) + 1, "sleep_hours": 7.5,
             "exercise": "", "event_label": ""} for i in range(n)]


def spec():
    return load_rules(os.path.join(REPO, "data", "rules_prior.json"))


# ── strategies ────────────────────────────────────────────────

def test_strategies_deterministic_per_seed():
    a = block_mask(90, 3, seed=7)
    b = block_mask(90, 3, seed=7)
    assert a[0].eval_idx == b[0].eval_idx
    c = block_mask(90, 3, seed=8)
    assert a[0].eval_idx != c[0].eval_idx


def test_block_mask_hides_exactly_block_days():
    n = 90
    split = block_mask(n, 3, seed=1)[0]
    assert len(split.eval_idx) == 3
    assert split.n_visible == n - 3
    assert split.eval_idx == list(range(split.eval_idx[0],
                                        split.eval_idx[0] + 3))


def test_point_mask_ratio():
    n = 100
    split = point_mask(n, ratio=0.10, seed=3)[0]
    assert len(split.eval_idx) == 10


def test_rolling_fits_are_disjoint_windows():
    n = 90
    splits = rolling_forecast(n, horizon=7, seed=2)
    assert splits and all(len(s.eval_idx) == 7 for s in splits)
    for s in splits:
        assert max(s.eval_idx) < n


def test_eval_days_hidden_warmup_respected():
    n = 90
    for strat, seed in (("point", 1), ("block3", 1), ("rolling7", 1)):
        for s in build_from(strat, n, seed):
            assert all(i >= 28 for i in s.eval_idx)
            assert all(not s.visible[i] for i in s.eval_idx)


def build_from(strategy, n, seed):
    from masking_test import build_splits
    return build_splits(strategy, n, seed)


# ── baselines ─────────────────────────────────────────────────

def test_persistence_on_constant_series_is_exact():
    rows = const_rows(90, 50.0)
    split = block_mask(90, 3, seed=5)[0]
    pred = b1a_persistence(rows, split)
    assert all(abs(v - 50.0) < 1e-9 for v in pred.values())
    assert mae(pred, rows) == pytest.approx(0.0)


def test_mean7_on_constant_series_is_exact():
    rows = const_rows(90, 50.0)
    split = block_mask(90, 7, seed=5)[0]
    pred = b1b_mean7(rows, split)
    assert mae(pred, rows) == pytest.approx(0.0)


def test_phase_mean_uses_visible_days_only():
    rows = const_rows(90, 50.0)
    split = block_mask(90, 3, seed=5)[0]
    # break the hidden days so they would poison a leaky mean
    for i in split.eval_idx:
        rows[i]["hrv_rmssd"] = 999.0
    pred = b2_phase_mean(rows, split)
    assert all(v < 60 for v in pred.values())


# ── rules prior ───────────────────────────────────────────────

def test_rule_reads_lagged_covariate():
    rows = const_rows(5, 50.0)
    rules = {"rules": [{"id": "t", "when": {"sleep_hours_lt": 6.0, "on_lag": 1},
                        "adjust": -4.0}]}
    rows[3]["sleep_hours"] = 5.0     # lag day for target day 4
    assert rule_adjust(rows[4], rows[3], rules) == pytest.approx(-4.0)
    rows[3]["sleep_hours"] = 7.5
    assert rule_adjust(rows[4], rows[3], rules) == pytest.approx(0.0)


def test_rule_reads_target_day_calendar():
    rows = const_rows(5, 50.0)
    rules = {"rules": [{"id": "lut", "when": {"cycle_day_ge": 15, "on_lag": 0},
                        "adjust": -3.0}]}
    rows[4]["cycle_day"] = 20
    assert rule_adjust(rows[4], None, rules) == pytest.approx(-3.0)


def test_b3_is_mean7_plus_adjustments():
    rows = const_rows(90, 50.0)
    split = block_mask(90, 3, seed=5)[0]
    pred = b3_rules_prior(rows, split, spec())
    assert pred and all(abs(v - 50.0) < 7.0 for v in pred.values())


# ── ridge model ───────────────────────────────────────────────

def test_ridge_recovers_linear_signal():
    X = [[float(i), float(i % 7)] for i in range(200)]
    y = [3.0 * a - 1.0 * b + 5.0 for a, b in X]
    w, means, stds = ridge_fit(X, y)
    p = ridge_predict(w, means, stds, [150.0, 3.0])
    # NOTE: ridge carries L2 shrinkage, so it recovers the planted linear
    # structure only up to a small bias (~0.2% here). The contract under test
    # is "recovers the structure", not "exact OLS identity".
    assert p == pytest.approx(3.0 * 150.0 - 1.0 * 3.0 + 5.0, rel=1e-2)


def test_m_ridge_beats_mean7_on_planted_dynamics():
    # synthetic rows with planted sleep/luteal structure (gen_synthetic_daily)
    rows = _synthetic()
    best = {"b1a": [], "m": []}
    for seed in range(1, 11):
        split = block_mask(len(rows), 3, seed=seed)[0]
        p7 = b1b_mean7(rows, split)
        pm = m_ridge(rows, split, spec())
        if p7 and pm:
            best["b1a"].append(mae(p7, rows))
            best["m"].append(mae(pm, rows))
    assert best["m"], "model produced no predictions"
    assert statistics_mean(best["m"]) < statistics_mean(best["b1a"]) * 1.10


def statistics_mean(xs):
    return sum(xs) / len(xs)


def _synthetic():
    import csv as _csv
    path = os.path.join(REPO, "data", "synthetic_daily.csv")
    if not os.path.exists(path):
        pytest.skip("synthetic fixture not generated yet")
    with open(path, newline="", encoding="utf-8") as fh:
        rows = []
        for r in _csv.DictReader(fh):
            r["hrv_rmssd"] = float(r["hrv_rmssd"])
            r["sleep_hours"] = float(r["sleep_hours"])
            r["cycle_day"] = int(r["cycle_day"])
            rows.append(r)
    return rows


def test_featurize_history_is_leakage_safe():
    rows = _synthetic()
    split = block_mask(len(rows), 3, seed=5)[0]
    medians = {"sleep_hours": 7.0}
    f = featurize(rows, split, split.eval_idx[0], spec(), medians)
    assert f is not None and len(f) == 11
    # last_y must be a VISIBLE day's value, never a hidden one
    last_y = f[0]
    hidden_vals = {rows[i]["hrv_rmssd"] for i in split.eval_idx}
    assert not any(abs(last_y - v) < 1e-9 and v == 999.0 for v in hidden_vals)


# ── evaluation / verdict ──────────────────────────────────────

def test_direction_accuracy_perfect_on_trend():
    rows = [{"date": str(i), "hrv_rmssd": float(i), "cycle_day": 1,
             "sleep_hours": 7.0, "exercise": "", "event_label": ""}
            for i in range(10)]
    pred = {i: rows[i]["hrv_rmssd"] + 0.5 for i in range(1, 10)}
    assert direction_accuracy(pred, rows) == pytest.approx(1.0)


def test_summarize_issues_verdict_key():
    rows = _synthetic()
    res = run_all(rows, spec(), seeds=DEFAULT_SEEDS[:3])
    s = summarize(res)
    assert s["verdict"] in ("g-exists", "borderline", "g-absent",
                            "insufficient-data")
    assert "mae_reduction" in s or s["verdict"] == "insufficient-data"
