"""
Hidden Chain — Retrospective Masking Harness: strategies (layer 1)
==================================================================
Implements the three masking strategies of the pre-registered
retrospective masking test (design/masking-test-plan-v1.md):

  S1  point_mask      — hide a random 10% of days
  S2  block_mask      — hide one contiguous 1/3/7-day window
  S3  rolling_forecast— walk forward: fit on [0..T], predict T+1..T+h

Leakage contract (hard rule, enforced by construction here):
  Within a MaskSplit, every eval day's `hrv_rmssd` is hidden from ALL
  predictors via `visible`. Non-y channels (cycle_day, sleep_hours,
  exercise, event_label) stay visible — the dynamics are conditioned on
  the intervention path a, i.e. P(s_t | s_<t, a), exactly as pre-registered.

Pure stdlib. No numpy, no third-party deps (repo science-core rule).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

TARGET = "hrv_rmssd"          # the single pre-registered primary target
WARMUP = 28                   # days of history required before any eval day
DEFAULT_SEEDS = list(range(1, 31))   # seeds 1..30, frozen in the plan


@dataclass(frozen=True)
class MaskSplit:
    """One masking draw: which days must be predicted, which are visible."""
    eval_idx: list[int]       # days whose y is hidden and must be predicted
    visible: list[bool]       # len == n_days; False where y is hidden
    strategy: str = ""        # "point" | "block1" | "block3" | "block7" | "rolling7"
    seed: int = 0

    @property
    def n_visible(self) -> int:
        return sum(self.visible)


def _check(n: int, block: int) -> None:
    if n < WARMUP + block + 1:
        raise ValueError(
            f"need n >= {WARMUP + block + 1} days for block={block}, got n={n}"
        )


def point_mask(n: int, ratio: float = 0.10, seed: int = 0) -> list[MaskSplit]:
    """S1: hide a random `ratio` of days (at least 1)."""
    _check(n, 1)
    rng = random.Random(seed)
    k = max(1, int(round(n * ratio)))
    idx = sorted(rng.sample(range(WARMUP, n), min(k, n - WARMUP)))
    visible = [True] * n
    for i in idx:
        visible[i] = False
    return [MaskSplit(eval_idx=idx, visible=visible,
                      strategy="point", seed=seed)]


def block_mask(n: int, block: int, seed: int = 0) -> list[MaskSplit]:
    """S2: hide one contiguous `block`-day window at a random start."""
    _check(n, block)
    rng = random.Random(seed)
    start = rng.randint(WARMUP, n - block - 1)
    idx = list(range(start, start + block))
    visible = [True] * n
    for i in idx:
        visible[i] = False
    name = f"block{block}"
    return [MaskSplit(eval_idx=idx, visible=visible,
                      strategy=name, seed=seed)]


def rolling_forecast(n: int, horizon: int = 7, frac: float = 0.6,
                     seed: int = 0) -> list[MaskSplit]:
    """S3: pick a random subset of origins T (frac of all origins);
    each origin yields one split fitting on [0..T] and predicting
    T+1..T+horizon. Seeds control which origins are sampled, giving the
    30-seed spread required by the plan."""
    _check(n, horizon)
    rng = random.Random(seed)
    origins = list(range(WARMUP, n - horizon))
    rng.shuffle(origins)
    keep = sorted(origins[: max(1, int(len(origins) * frac))])
    splits: list[MaskSplit] = []
    for t in keep:
        idx = list(range(t + 1, t + 1 + horizon))
        visible = [True] * n
        for i in idx:
            visible[i] = False
        splits.append(MaskSplit(eval_idx=idx, visible=visible,
                                strategy="rolling7", seed=seed))
    return splits


def build_splits(strategy: str, n: int, seed: int) -> list[MaskSplit]:
    """Dispatch by pre-registered strategy name."""
    if strategy == "point":
        return point_mask(n, seed=seed)
    if strategy in ("block1", "block3", "block7"):
        return block_mask(n, block=int(strategy[-1]), seed=seed)
    if strategy == "rolling7":
        return rolling_forecast(n, seed=seed)
    raise ValueError(f"unknown strategy: {strategy}")


STRATEGIES = ["point", "block1", "block3", "block7", "rolling7"]
