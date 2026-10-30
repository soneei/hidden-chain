#!/usr/bin/env python3
"""
Hidden Chain — synthetic daily series generator (demo + test fixture)
=====================================================================
Generates a 180-day daily CSV in the data/daily_log_template.csv schema so
the masking harness can be exercised end-to-end BEFORE the real Apple
Health export lands. The generator is committed (not just its output) so
anyone can regenerate and audit the fixture.

Ground-truth dynamics planted on purpose (so a correct harness CAN find
them): weekly sleep-debt dips, luteal-phase suppression, post-run dips.
Beating the baselines on synthetic data validates plumbing, NOT science —
the real verdict still waits for the frozen Apple Health export.

Usage:  python tools/gen_synthetic_daily.py --days 180 --seed 42 \
            --out data/synthetic_daily.csv
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import random


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data/synthetic_daily.csv")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    start = dt.date(2026, 4, 1)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "hrv_rmssd", "resting_hr", "cycle_day",
                    "event_label", "mood_score", "sleep_hours", "exercise"])
        for d in range(args.days):
            date = start + dt.timedelta(days=d)
            cycle_day = (d % 28) + 1
            sleep = round(rng.uniform(5.2, 8.6), 1)
            exercise = "run" if rng.random() < 0.2 else ""
            event = "meeting" if rng.random() < 0.1 else ""
            hrv = (
                55.0
                + 6.0 * math.sin(2 * math.pi * d / 28.0)      # cycle rhythm
                - 4.0 * max(0.0, 7.0 - sleep)                 # sleep debt
                - 3.0 * (1 if 15 <= cycle_day <= 28 else 0)   # luteal load
                - 2.0 * (1 if exercise else 0)                # acute dip
                - 1.5 * (1 if event else 0)                   # stress day
                + rng.gauss(0, 4.0)                           # noise
            )
            rhr = round(70 - 0.15 * (hrv - 55) + rng.gauss(0, 2), 0)
            mood = int(max(1, min(10, 7 - (8 - sleep) + rng.randint(-1, 1))))
            w.writerow([date.isoformat(), f"{hrv:.1f}", int(rhr), cycle_day,
                        event, mood, sleep, exercise])
    print(f"wrote {args.out} ({args.days} days, seed={args.seed})")


if __name__ == "__main__":
    main()
