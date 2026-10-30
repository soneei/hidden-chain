"""
Hidden Chain — Retrospective Masking Harness: baselines + rules prior (layer 2)
================================================================================
Four pre-registered baselines the model M must beat (plan §5):

  B1a persistence   — tomorrow = last visible observation
  B1b mean7         — tomorrow = mean of the last 7 visible days
  B2 phase_mean     — tomorrow = historical mean of the same cycle_day
  B3 rules_prior    — mean7 + sum of TCM rule adjustments
                      (the "engine demoted to a prior": the rules no longer
                      issue conclusions, they bias a numeric forecast; their
                      coefficients are frozen in data/rules_prior.json and
                      CAN later be recalibrated by data — see masking_model.py
                      where rule hits enter as features instead of constants.)

Leakage contract: baselines only read y where split.visible is True, and only
at indices strictly before the eval day.
Pure stdlib.
"""

from __future__ import annotations

import json
import math
from typing import Callable, Optional

from masking_test import MaskSplit, TARGET

Row = dict  # daily row: date, hrv_rmssd, cycle_day, sleep_hours, exercise, ...


# ──────────────────────────────────────────────────────────────
# history helpers (leakage-safe by construction)
# ──────────────────────────────────────────────────────────────

def last_visible_y(rows: list[Row], split: MaskSplit, before: int) -> Optional[float]:
    for j in range(min(before, len(rows)) - 1, -1, -1):
        if split.visible[j] and rows[j].get(TARGET) is not None:
            return rows[j][TARGET]
    return None


def visible_mean_y(rows: list[Row], split: MaskSplit, before: int,
                   k: int = 7) -> Optional[float]:
    vals: list[float] = []
    for j in range(min(before, len(rows)) - 1, -1, -1):
        if len(vals) >= k:
            break
        if split.visible[j] and rows[j].get(TARGET) is not None:
            vals.append(rows[j][TARGET])
    return sum(vals) / len(vals) if vals else None


# ──────────────────────────────────────────────────────────────
# B1a / B1b / B2
# ──────────────────────────────────────────────────────────────

def b1a_persistence(rows: list[Row], split: MaskSplit) -> dict[int, float]:
    out: dict[int, float] = {}
    for i in split.eval_idx:
        y = last_visible_y(rows, split, i)
        if y is not None:
            out[i] = y
    return out


def b1b_mean7(rows: list[Row], split: MaskSplit) -> dict[int, float]:
    out: dict[int, float] = {}
    for i in split.eval_idx:
        y = visible_mean_y(rows, split, i, k=7)
        if y is not None:
            out[i] = y
    return out


def b2_phase_mean(rows: list[Row], split: MaskSplit,
                  max_lag_days: int = 180) -> dict[int, float]:
    """Historical mean of y on the same cycle_day, using visible days only.
    Falls back to the global visible mean when a phase has no history."""
    by_phase: dict[int, list[float]] = {}
    global_vals: list[float] = []
    first_i = min(split.eval_idx)
    for j in range(first_i):
        if not split.visible[j]:
            continue
        y = rows[j].get(TARGET)
        cd = rows[j].get("cycle_day")
        if y is not None:
            global_vals.append(y)
            if cd is not None:
                by_phase.setdefault(int(cd), []).append(y)
    global_mean = sum(global_vals) / len(global_vals) if global_vals else None
    out: dict[int, float] = {}
    for i in split.eval_idx:
        cd = rows[i].get("cycle_day")
        vals = by_phase.get(int(cd)) if cd is not None else None
        if vals:
            out[i] = sum(vals) / len(vals)
        elif global_mean is not None:
            out[i] = global_mean
    return out


# ──────────────────────────────────────────────────────────────
# B3 — the TCM rule engine, demoted to a numeric prior
# ──────────────────────────────────────────────────────────────

def load_rules(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        spec = json.load(fh)
    if "rules" not in spec:
        raise ValueError("rules file missing 'rules' key")
    return spec


def _coerce(v: object) -> Optional[float]:
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _eval_when(when: dict, lag_row: Optional[Row], target_row: Row) -> bool:
    """Evaluate a rule's `when` clause. Keys look like `<field>_lt/le/ge/eq`;
    `on_lag` (default 1) picks which day's covariates the comparison uses
    (1 = the day before the target; 0 = the target day itself)."""
    on_lag = int(when.get("on_lag", 1))
    row = lag_row if on_lag == 1 else target_row
    for key, expected in when.items():
        if key == "on_lag":
            continue
        if key.endswith("_lt"):
            v = _coerce((row or {}).get(key[:-3]))
            if v is None or not v < float(expected):
                return False
        elif key.endswith("_le"):
            v = _coerce((row or {}).get(key[:-3]))
            if v is None or not v <= float(expected):
                return False
        elif key.endswith("_ge"):
            v = _coerce((row or {}).get(key[:-3]))
            if v is None or not v >= float(expected):
                return False
        elif key.endswith("_eq"):
            actual = (row or {}).get(key[:-3])
            if str(actual or "").strip() != str(expected).strip():
                return False
        else:
            raise ValueError(f"unsupported condition key: {key}")
    return True


def rule_adjust(row_target: Row, row_lag: Optional[Row],
                rules_spec: dict) -> float:
    total = 0.0
    for rule in rules_spec.get("rules", []):
        if _eval_when(rule.get("when", {}), row_lag, row_target):
            total += float(rule.get("adjust", 0.0))
    return total


def b3_rules_prior(rows: list[Row], split: MaskSplit,
                   rules_spec: dict) -> dict[int, float]:
    """mean7 baseline + sum of rule adjustments (frozen coefficients)."""
    out: dict[int, float] = {}
    for i in split.eval_idx:
        base = visible_mean_y(rows, split, i, k=7)
        if base is None:
            continue
        lag_row = rows[i - 1] if i >= 1 else None
        out[i] = base + rule_adjust(rows[i], lag_row, rules_spec)
    return out


BASELINES: dict[str, Callable] = {}  # populated in masking_evaluate to avoid
                                     # a circular import of the rules spec
