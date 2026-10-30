"""
Hidden Chain — Retrospective Masking Harness: model M (layer 3)
================================================================
First rung of the frozen upgrade ladder (plan §9.3): ridge regression on
hand-built features, closed form, pure stdlib (no numpy / sklearn).

Design point — "rules as skeleton, data in charge":
  rule_hits are NOT hard-coded adjustments here (that is B3). They enter as
  ONE feature column alongside lags and calendar terms, so the regression
  learns how much each hit is worth from the development segment. The hand
  rules supply direction and structure (inductive bias); the data supplies
  magnitude. This is exactly the "engine demoted to a prior" move from the
  plan: the rules are not thrown away, they are demoted.

Feature list (frozen for v1; all history features read visible days only):
  1  last_y          — most recent visible target before the eval day
  2  mean7_hist      — mean of up to 7 most recent visible targets
  3  mean28_hist     — mean of up to 28 most recent visible targets
  4  trend           — mean7_hist - mean28_hist
  5  cycle_sin       — sin(2π · cycle_day / 28)
  6  cycle_cos       — cos(2π · cycle_day / 28)
  7  weekday         — ISO weekday / 7
  8  sleep_hours     — target-day sleep (missing → column median)
  9  exercise_flag   — 1 if any exercise logged on the target day
  10 event_flag      — 1 if any event logged on the target day
  11 rule_adjust     — Σ frozen rule adjustments (see masking_baselines)
"""

from __future__ import annotations

import math
from typing import Optional

from masking_baselines import last_visible_y, rule_adjust, visible_mean_y
from masking_test import MaskSplit, Row, TARGET

FEATURE_NAMES = [
    "last_y", "mean7_hist", "mean28_hist", "trend",
    "cycle_sin", "cycle_cos", "weekday",
    "sleep_hours", "exercise_flag", "event_flag", "rule_adjust",
]
RIDGE_LAMBDA = 1.0


def _num(v: object) -> Optional[float]:
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def featurize(rows: list[Row], split: MaskSplit, i: int,
              rules_spec: dict, medians: dict) -> Optional[list[float]]:
    """Feature vector for predicting day i. History features read visible
    days strictly before i; covariates (sleep/exercise/event) and calendar
    features come from the target day itself (intervention-path conditioning,
    per the leakage contract)."""
    last_y = last_visible_y(rows, split, i)
    if last_y is None:
        return None
    vals: list[float] = []
    for j in range(i - 1, -1, -1):
        if len(vals) >= 28:
            break
        if split.visible[j] and rows[j].get(TARGET) is not None:
            vals.append(rows[j][TARGET])
    mean7 = sum(vals[:7]) / len(vals[:7]) if vals else last_y
    mean28 = sum(vals) / len(vals) if vals else last_y

    cd = _num(rows[i].get("cycle_day")) or 1.0
    sleep = _num(rows[i].get("sleep_hours"))
    if sleep is None:
        sleep = medians.get("sleep_hours", 7.0)

    lag_row = rows[i - 1] if i >= 1 else None
    return [
        last_y,
        mean7,
        mean28,
        mean7 - mean28,
        math.sin(2 * math.pi * (cd - 1) / 28.0),
        math.cos(2 * math.pi * (cd - 1) / 28.0),
        (_weekday(rows[i]) ) / 7.0,
        sleep,
        1.0 if str(rows[i].get("exercise") or "").strip() else 0.0,
        1.0 if str(rows[i].get("event_label") or "").strip() else 0.0,
        rule_adjust(rows[i], lag_row, rules_spec),
    ]


def _weekday(row: Row) -> int:
    import datetime as _dt
    try:
        return _dt.date.fromisoformat(str(row.get("date"))).isoweekday()
    except ValueError:
        return 1


def column_medians(rows: list[Row]) -> dict:
    """Medians of covariate columns over rows with a known target
    (computed on the FULL series once per split — calendar-level stats,
    not target leakage; frozen here for simplicity and auditability)."""
    meds: dict = {}
    for col in ("sleep_hours",):
        vals = sorted(v for v in (_num(r.get(col)) for r in rows)
                      if v is not None)
        if vals:
            n = len(vals)
            meds[col] = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
    return meds


def ridge_fit(X: list[list[float]], y: list[float],
              lam: float = RIDGE_LAMBDA) -> tuple[list[float], list[float], list[float]]:
    """Closed-form ridge with standardization. Returns (weights, means, stds)
    with the bias folded into weights[-1]. Pure stdlib Gaussian elimination."""
    n, d = len(X), len(X[0])
    means = [sum(col) / n for col in zip(*X)]
    stds = []
    for j in range(d):
        var = sum((row[j] - means[j]) ** 2 for row in X) / n
        stds.append(math.sqrt(var) if var > 1e-12 else 1.0)
    A = [[(row[j] - means[j]) / stds[j] for j in range(d)] + [1.0] for row in X]
    yv = list(y)

    # normal equations: (Z'Z + λI) w = Z'y  (bias row unpenalized)
    p = d + 1
    M = [[sum(A[k][a] * A[k][b] for k in range(n)) for b in range(p)]
         for a in range(p)]
    for a in range(d):
        M[a][a] += lam
    rhs = [sum(A[k][a] * yv[k] for k in range(n)) for a in range(p)]

    # Gaussian elimination with partial pivoting
    for col in range(p):
        piv = max(range(col, p), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-12:
            M[col][col] += 1e-9
            piv = col
        M[col], M[piv] = M[piv], M[col]
        rhs[col], rhs[piv] = rhs[piv], rhs[col]
        for r in range(col + 1, p):
            f = M[r][col] / M[col][col]
            if f == 0.0:
                continue
            for c in range(col, p):
                M[r][c] -= f * M[col][c]
            rhs[r] -= f * rhs[col]
    w = [0.0] * p
    for r in reversed(range(p)):
        s = rhs[r] - sum(M[r][c] * w[c] for c in range(r + 1, p))
        w[r] = s / M[r][r]
    return w, means, stds


def ridge_predict(w: list[float], means: list[float], stds: list[float],
                  x: list[float]) -> float:
    z = [(x[j] - means[j]) / stds[j] for j in range(len(x))]
    return sum(z[j] * w[j] for j in range(len(z))) + w[-1]


def m_ridge(rows: list[Row], split: MaskSplit, rules_spec: dict) -> dict[int, float]:
    """Train on every visible day (warmup ≥ 28), predict each eval day."""
    medians = column_medians(rows)
    train_X: list[list[float]] = []
    train_y: list[float] = []
    for j in range(28, len(rows)):
        if not split.visible[j] or rows[j].get(TARGET) is None:
            continue
        sub = MaskSplit(eval_idx=[j], visible=list(split.visible),
                        strategy=split.strategy, seed=split.seed)
        # training features must also only see days before j that are visible
        fx = featurize(rows, sub, j, rules_spec, medians)
        if fx is not None:
            train_X.append(fx)
            train_y.append(rows[j][TARGET])
    if len(train_X) < len(FEATURE_NAMES) + 5:
        return {}
    w, means, stds = ridge_fit(train_X, train_y)
    out: dict[int, float] = {}
    for i in split.eval_idx:
        fx = featurize(rows, split, i, rules_spec, medians)
        if fx is not None:
            out[i] = ridge_predict(w, means, stds, fx)
    return out
