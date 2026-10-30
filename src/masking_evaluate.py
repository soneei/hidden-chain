"""
Hidden Chain — Retrospective Masking Harness: evaluation + verdict (layer 4)
============================================================================
Pre-registered scoring (plan §6):

  PRIMARY verdict metric : MAE on the 3-day block mask (S2/block3), averaged
                           over 30 seeds.
  Verdict                : M beats the BEST baseline by >=10% MAE reduction
                           AND direction hit-rate >= 60%  →  "g exists"
                           5–10%                            →  "borderline"
                           < 5% or worse than B1a           →  "g absent"
  Secondary (reported, never verdict-bearing): RMSE, direction accuracy on
                           other strategies, per-seed spread.

Pure stdlib.
"""

from __future__ import annotations

import statistics
from typing import Callable

from masking_baselines import (b1a_persistence, b1b_mean7, b2_phase_mean,
                               b3_rules_prior)
from masking_model import m_ridge
from masking_test import MaskSplit, TARGET, build_splits

METHODS: dict[str, Callable] = {
    "B1a_persistence": b1a_persistence,
    "B1b_mean7": b1b_mean7,
    "B2_phase_mean": b2_phase_mean,
    "B3_rules_prior": None,   # needs the rules spec; bound in run_masking_test
    "M_ridge": None,          # same
}
BASELINE_NAMES = ["B1a_persistence", "B1b_mean7", "B2_phase_mean",
                  "B3_rules_prior"]


def mae(pred: dict[int, float], rows: list[Row]) -> float | None:  # noqa: F821
    errs = [abs(p - rows[i][TARGET]) for i, p in pred.items()
            if rows[i].get(TARGET) is not None]
    return sum(errs) / len(errs) if errs else None


def rmse(pred: dict[int, float], rows) -> float | None:  # noqa: F821
    errs = [(p - rows[i][TARGET]) ** 2 for i, p in pred.items()
            if rows[i].get(TARGET) is not None]
    return (sum(errs) / len(errs)) ** 0.5 if errs else None


def direction_accuracy(pred: dict[int, float], rows) -> float | None:  # noqa: F821
    """Hit-rate on up/down vs the previous REAL day. Uses true y[i-1] for the
    reference only (scoring-time information, not a predictor input)."""
    hits = total = 0
    for i, p in pred.items():
        if i == 0 or rows[i].get(TARGET) is None or rows[i - 1].get(TARGET) is None:
            continue
        actual_dir = rows[i][TARGET] > rows[i - 1][TARGET]
        pred_dir = p > rows[i - 1][TARGET]
        total += 1
        hits += actual_dir == pred_dir
    return hits / total if total else None


def run_all(rows, rules_spec, seeds) -> list[dict]:  # noqa: F821
    """Run every (strategy, seed, method) combination; one row per combo."""
    bound: dict[str, Callable] = {
        "B1a_persistence": b1a_persistence,
        "B1b_mean7": b1b_mean7,
        "B2_phase_mean": lambda r, s: b2_phase_mean(r, s),
        "B3_rules_prior": lambda r, s: b3_rules_prior(r, s, rules_spec),
        "M_ridge": lambda r, s: m_ridge(r, s, rules_spec),
    }
    results: list[dict] = []
    for strategy in ("point", "block1", "block3", "block7", "rolling7"):
        for seed in seeds:
            for split in build_splits(strategy, len(rows), seed):
                for name, fn in bound.items():
                    pred = fn(rows, split)
                    if not pred:
                        continue
                    results.append({
                        "strategy": strategy, "seed": seed, "method": name,
                        "n_eval": len(pred),
                        "mae": mae(pred, rows), "rmse": rmse(pred, rows),
                        "dir_acc": direction_accuracy(pred, rows),
                    })
    return results


PRIMARY_STRATEGY = "block3"
VERDICT_REDuction = (0.10, 0.05)   # >=0.10 exists; 0.05–0.10 borderline
DIR_FLOOR = 0.60


def summarize(results: list[dict]) -> dict:
    """Aggregate over seeds and issue the pre-registered verdict."""
    def cell(strategy: str, method: str, key: str = "mae") -> float | None:  # noqa: F821
        vals = [r[key] for r in results
                if r["strategy"] == strategy and r["method"] == method
                and r[key] is not None]
        return statistics.fmean(vals) if vals else None

    table = {m: {s: cell(s, m) for s in
                 ("point", "block1", "block3", "block7", "rolling7")}
             for m in list(METHODS)}
    best_base = min((table[b][PRIMARY_STRATEGY] for b in BASELINE_NAMES
                     if table[b][PRIMARY_STRATEGY] is not None),
                    default=None)
    m_mae = table["M_ridge"][PRIMARY_STRATEGY]
    m_dir = cell(PRIMARY_STRATEGY, "M_ridge", "dir_acc")

    verdict = {"primary_strategy": PRIMARY_STRATEGY,
               "best_baseline_mae": best_base, "model_mae": m_mae,
               "model_dir_acc": m_dir, "table": table}
    if best_base is None or m_mae is None:
        verdict["verdict"] = "insufficient-data"
        return verdict
    reduction = (best_base - m_mae) / best_base
    verdict["mae_reduction"] = reduction
    if reduction >= VERDICT_REDuction[0] and (m_dir or 0) >= DIR_FLOOR:
        verdict["verdict"] = "g-exists"
    elif reduction >= VERDICT_REDuction[1]:
        verdict["verdict"] = "borderline"
    else:
        verdict["verdict"] = "g-absent"
    return verdict
