#!/usr/bin/env python3
"""
Hidden Chain — TCM Report Demo / Sample generator
==================================================
Runs the full pipeline  HRV features -> TCMAssessment -> TCMReport
and renders a Markdown report. Used to:

  - preview the report the 3 real users will get in 7 days,
  - generate a sample .md (default: .workbuddy/tcm_reports/sample.md,
    NOT committed) for design review.

Usage:
  # built-in high-liver / high-spleen sample
  python tools/tcm_report_demo.py

  # custom HRV inputs
  python tools/tcm_report_demo.py --rmssd 28 --normalized 1.5 \
      --recovery slow --hr 80 --sleep 5.5 \
      --mood irritable,anxious,exhausted,brain_fog \
      --out .workbuddy/tcm_reports/sample.md
"""

import argparse
import os
import sys

# make src/ importable when run as a script from the repo root
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))

from tcm_hrv_estimator import HRVFeatures, estimate_tcm  # noqa: E402
from tcm_report import build_tcm_report, render_markdown  # noqa: E402


def _builtin_sample() -> HRVFeatures:
    """A realistic profile: liver-qi stagnation high, spleen moderate.

    Intentionally NOT maxed-out on every axis — real 7-day data will
    have one or two dominant tendencies, not all-max. Keeps the sample
    report readable and signal-rich rather than a wall of 67 items.
    """
    return HRVFeatures(
        resting_rmssd=30.0,
        normalized_hrv=1.2,
        recovery_classification="slow",
        recovery_rate=1.1,
        resting_hr=76.0,
        sleep_hours=5.5,
        mood_tags=["irritable", "anxious"],
    )


def main() -> int:
    p = argparse.ArgumentParser(description="Generate a TCM HRV report sample.")
    p.add_argument("--rmssd", type=float, help="resting RMSSD (ms)")
    p.add_argument("--normalized", type=float, default=0.0,
                   help="normalized HRV (cycle-adjusted z-score)")
    p.add_argument("--recovery", type=str, default="normal",
                   choices=["fast", "normal", "slow"],
                   help="recovery classification")
    p.add_argument("--hr", type=float, default=None, help="resting HR (bpm)")
    p.add_argument("--sleep", type=float, default=None, help="sleep hours")
    p.add_argument("--mood", type=str, default="",
                   help="comma-separated mood tags")
    p.add_argument("--out", type=str,
                   default=os.path.join(_REPO_ROOT, ".workbuddy",
                                         "tcm_reports", "sample.md"),
                   help="output markdown path")
    args = p.parse_args()

    if args.rmssd is not None:
        mood = [m.strip() for m in args.mood.split(",") if m.strip()]
        feats = HRVFeatures(
            resting_rmssd=args.rmssd,
            normalized_hrv=args.normalized,
            recovery_classification=args.recovery,
            resting_hr=args.hr,
            sleep_hours=args.sleep,
            mood_tags=mood,
        )
    else:
        feats = _builtin_sample()

    assessment = estimate_tcm(feats)
    report = build_tcm_report(assessment)
    md = render_markdown(report)

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(md)

    print(f"[ok] report written to {args.out}")
    print(f"     primary tendency : {report.primary}")
    print(f"     families         : {len(report.family_clusters)}")
    print(f"     must-see-clinic  : {len(report.must_see_clinic)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
