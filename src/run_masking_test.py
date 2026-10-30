#!/usr/bin/env python3
"""
Hidden Chain — Retrospective Masking Test, one-shot CLI
=======================================================
Pre-registered entry point (design/masking-test-plan-v1.md). Runs all
strategies × seeds × methods on a daily CSV and writes results.csv plus a
verdict summary.

Usage:
  python src/run_masking_test.py data/synthetic_daily.csv \
      --rules data/rules_prior.json --seeds 30 --out results.csv

Exit code 0 always (the verdict is data, not a test outcome).
"""

from __future__ import annotations

import argparse
import csv
import sys

from masking_baselines import load_rules
from masking_evaluate import run_all, summarize
from masking_test import DEFAULT_SEEDS, TARGET


def load_daily_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    parsed: list[dict] = []
    for r in rows:
        q = dict(r)
        for col in (TARGET, "sleep_hours"):
            v = (q.get(col) or "").strip()
            q[col] = float(v) if v else None
        cd = (q.get("cycle_day") or "").strip()
        q["cycle_day"] = int(cd) if cd else None
        parsed.append(q)
    parsed.sort(key=lambda r: r["date"])
    n = len(parsed)
    if n < 60:
        raise SystemExit(f"need >= 60 days, got {n} — run the data export first")
    known = sum(1 for r in parsed if r[TARGET] is not None)
    if known / n < 0.70:
        raise SystemExit(
            f"primary-target coverage {known/n:.0%} < 70% — plan §2.1 gate")
    return parsed


def main() -> None:
    ap = argparse.ArgumentParser(description="Hidden Chain masking test")
    ap.add_argument("data", help="daily CSV (data/daily_log_template.csv schema)")
    ap.add_argument("--rules", default="data/rules_prior.json")
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--out", default="results.csv")
    args = ap.parse_args()

    rows = load_daily_csv(args.data)
    rules_spec = load_rules(args.rules)
    print(f"days={len(rows)}  target={TARGET}  seeds=1..{args.seeds}")

    results = run_all(rows, rules_spec, DEFAULT_SEEDS[: args.seeds])

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(results[0]))
        w.writeheader()
        w.writerows(results)
    print(f"wrote {args.out} ({len(results)} rows)")

    s = summarize(results)
    print("\n=== MAE by strategy (mean over seeds) ===")
    for strat in ("point", "block1", "block3", "block7", "rolling7"):
        line = "  ".join(
            f"{m.split('_')[0]}={s['table'][m][strat]:.2f}"
            for m in s["table"] if s["table"][m][strat] is not None)
        print(f"{strat:>9}: {line}")
    print(f"\nprimary strategy: {s['primary_strategy']}")
    print(f"best baseline MAE: {s['best_baseline_mae']:.2f}")
    print(f"model MAE:         {s['model_mae']:.2f}")
    print(f"MAE reduction:     {s.get('mae_reduction', float('nan')):.1%}")
    print(f"model dir acc:     {(s['model_dir_acc'] or 0):.1%}")
    print(f"\nVERDICT (pre-registered, plan §6.2): {s['verdict']}")


if __name__ == "__main__":
    sys.exit(main())
