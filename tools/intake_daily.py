#!/usr/bin/env python3
"""
Hidden Chain — device export → daily log intake
================================================
Turns whatever a wearable vendor actually gives you into the one daily table
the masking harness consumes (``data/daily_log_template.csv`` schema), then
tells you honestly whether you have enough data to run anything.

Why this exists
---------------
Vendor exports are the least standardised artefacts in consumer health:
30-day caps, per-metric files, Chinese or English headers, epoch milliseconds,
one row per minute or one row per day, BOM-prefixed UTF-8. Hard-coding one
vendor's layout guarantees the script breaks the month you switch watches.
So this intake **sniffs** the columns instead of assuming them, and prints
exactly what it recognised — you can see the mapping before trusting it.

Usage
-----
  # one export
  python tools/intake_daily.py ~/Downloads/health_export.csv --out data/daily_log.csv

  # several 30-day slices from the same app (Huawei caps a single export at 30 days)
  python tools/intake_daily.py ~/Downloads/exports/*.csv --out data/daily_log.csv

  # fill cycle_day from remembered period start dates (day 1 = first day of bleed)
  python tools/intake_daily.py export.csv --cycle-start 2026-07-01,2026-07-28

Output
------
  1. the daily CSV at --out
  2. a coverage report on stdout, ending in a readiness verdict that matches
     the gate in src/run_masking_test.py

Pure stdlib. No pandas, no numpy — same discipline as the engine.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone

SCHEMA = ["date", "hrv_rmssd", "resting_hr", "cycle_day",
          "event_label", "mood_score", "sleep_hours", "exercise"]

# Candidate header keywords, lower-cased, matched as substrings.
# Order matters: the first matching column wins.
ALIASES: dict[str, list[str]] = {
    "date": ["日期", "时间", "date", "timestamp", "start_time", "starttime",
             "time", "day"],
    "hrv_rmssd": ["心率变异", "hrv", "rmssd", "sdnn"],
    "resting_hr": ["静息心率", "静息", "resting", "rhr", "rest_hr"],
    "sleep_hours": ["睡眠时长", "睡眠", "sleep", "asleep"],
    "mood_score": ["情绪", "心情", "mood"],
}

NUMERIC = ("hrv_rmssd", "resting_hr", "sleep_hours", "mood_score")

_DATE_PATTERNS = [
    "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d",
    "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S", "%d/%m/%Y", "%m/%d/%Y",
]

_CN_DATE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")


def parse_date(raw: str) -> date | None:
    """Vendor date parsing: ISO, slashes, Chinese, epoch seconds/millis."""
    s = (raw or "").strip()
    if not s:
        return None
    m = _CN_DATE.search(s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    # epoch?
    if re.fullmatch(r"\d{10,13}", s):
        v = int(s)
        if v > 10_000_000_000:      # milliseconds
            v //= 1000
        try:
            return datetime.fromtimestamp(v, tz=timezone.utc).date()
        except (ValueError, OSError, OverflowError):
            return None
    head = s.split("T")[0].split(" ")[0]
    for pat in _DATE_PATTERNS:
        try:
            return datetime.strptime(head, pat).date()
        except ValueError:
            continue
    return None


def to_float(raw: str) -> float | None:
    s = (raw or "").strip().replace(",", "")
    if not s:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def sniff(header: list[str]) -> dict[str, int]:
    """Map our schema fields onto the vendor's column indices."""
    cols = [(i, (h or "").strip().lower().lstrip("\ufeff")) for i, h in enumerate(header)]
    mapping: dict[str, int] = {}
    for field, keys in ALIASES.items():
        for key in keys:                      # alias order = priority
            for i, name in cols:
                if i in mapping.values():
                    continue
                if key in name:
                    mapping[field] = i
                    break
            if field in mapping:
                break
    return mapping


def read_csvs(paths: list[str]) -> tuple[dict[date, dict[str, list[float | None]]],
                                         dict[str, int], list[str]]:
    """Aggregate every row of every file into per-day value buckets."""
    days: dict[date, dict[str, list[float | None]]] = {}
    mapping_seen: dict[str, int] = {}
    problems: list[str] = []

    for path in paths:
        try:
            with open(path, newline="", encoding="utf-8-sig") as fh:
                reader = csv.reader(fh)
                try:
                    header = next(reader)
                except StopIteration:
                    problems.append(f"{os.path.basename(path)}: empty file")
                    continue
                if all(to_float(c) is not None for c in header if c.strip()):
                    problems.append(
                        f"{os.path.basename(path)}: no header row detected "
                        f"(first row is all numbers) — skipped")
                    continue
                mapping = sniff(header)
                if "date" not in mapping:
                    problems.append(
                        f"{os.path.basename(path)}: no date column found "
                        f"(headers: {', '.join(h for h in header if h.strip())[:120]})")
                    continue
                for field, idx in mapping.items():
                    mapping_seen.setdefault(field, idx)

                for row in reader:
                    if not row or len(row) < len(header):
                        continue
                    d = parse_date(row[mapping["date"]])
                    if d is None:
                        continue
                    bucket = days.setdefault(
                        d, {f: [] for f in NUMERIC})
                    for field in NUMERIC:
                        idx = mapping.get(field)
                        if idx is None or idx >= len(row):
                            continue
                        v = to_float(row[idx])
                        if v is None:
                            continue
                        # a sleep duration above 24 is seconds or minutes, not hours
                        if field == "sleep_hours" and v > 24:
                            v = v / 3600 if v > 1440 else v / 60
                        bucket[field].append(v)
        except OSError as exc:
            problems.append(f"{os.path.basename(path)}: {exc}")
    return days, mapping_seen, problems


def build_rows(days: dict[date, dict], cycle_starts: list[date]) -> list[dict]:
    """One row per calendar day; intra-day readings collapse to a mean."""
    rows: list[dict] = []
    for d in sorted(days):
        b = days[d]
        row = {k: "" for k in SCHEMA}
        row["date"] = d.isoformat()
        for field in NUMERIC:
            vals = [v for v in b.get(field, []) if v is not None]
            if vals:
                row[field] = f"{sum(vals)/len(vals):.1f}" if field != "mood_score" \
                    else str(int(round(sum(vals)/len(vals))))
        cd = cycle_day_for(d, cycle_starts)
        if cd is not None:
            row["cycle_day"] = str(cd)
        rows.append(row)
    return rows


def cycle_day_for(d: date, starts: list[date]) -> int | None:
    """Day 1 = first day of bleed; counts forward until the next start."""
    prev = None
    for s in sorted(starts):
        if s <= d:
            prev = s
        else:
            break
    if prev is None:
        return None
    return (d - prev).days + 1


def report(rows: list[dict], problems: list[str], mapping: dict[str, int]) -> str:
    n = len(rows)
    out: list[str] = []
    out.append(f"rows (calendar days with data): {n}")
    if n == 0:
        out.append("READINESS: INSUFFICIENT — nothing parsed; check the headers above")
        return "\n".join(out) + "\n"

    first, last = rows[0]["date"], rows[-1]["date"]
    d0 = date.fromisoformat(first)
    d1 = date.fromisoformat(last)
    span = (d1 - d0).days + 1
    present = {date.fromisoformat(r["date"]) for r in rows}
    missing = span - n
    out.append(f"range: {first} .. {last}   (span {span}d, missing {missing}d, "
               f"{n/span:.0%} coverage)")

    # longest gap
    gap = best = 0
    cur = d0
    while cur <= d1:
        if cur not in present:
            gap += 1
            best = max(best, gap)
        else:
            gap = 0
        cur += timedelta(days=1)
    out.append(f"longest consecutive gap: {best}d")

    for field in ("hrv_rmssd", "resting_hr", "sleep_hours", "cycle_day"):
        k = sum(1 for r in rows if str(r.get(field, "")).strip())
        out.append(f"  {field:<12} {k}/{n} ({k/n:.0%})")

    out.append("")

    if n >= 90 and (sum(1 for r in rows if r["hrv_rmssd"]) / n) >= 0.70:
        verdict = ("FULL — S1 point / S2 block(1,3,7) / S3 rolling-7 all runnable. "
                   "This is the world-model grade test.")
    elif n >= 60:
        verdict = ("PARTIAL — S1 + S2 runnable; S3 rolling-7 is underpowered "
                   "(needs >=90d). Verdict from block3 only.")
    elif n >= 30:
        verdict = ("MINIMAL — S1 point masking only. Enough to smoke the harness, "
                   "NOT enough to declare g exists or not.")
    else:
        verdict = ("INSUFFICIENT — below the 60-day hard gate in "
                   "src/run_masking_test.py. Keep accumulating.")
    out.append(f"READINESS: {verdict}")
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="wearable export → daily log")
    ap.add_argument("csvs", nargs="+", help="export CSV file(s)")
    ap.add_argument("--out", default="data/daily_log.csv")
    ap.add_argument("--cycle-start", default="",
                    help="comma-separated period start dates (YYYY-MM-DD)")
    args = ap.parse_args()

    paths: list[str] = []
    for p in args.csvs:
        if os.path.isdir(p):
            paths += [os.path.join(p, f) for f in sorted(os.listdir(p))
                      if f.lower().endswith(".csv")]
        else:
            paths.append(p)
    if not paths:
        raise SystemExit("no CSV files given")

    starts: list[date] = []
    for s in (args.cycle_start.split(",") if args.cycle_start else []):
        s = s.strip()
        if s:
            d = parse_date(s)
            if d:
                starts.append(d)
            else:
                print(f"warning: cannot parse cycle start '{s}'", file=sys.stderr)

    days, mapping, problems = read_csvs(paths)
    rows = build_rows(days, starts)

    print(f"files read: {len(paths)}")
    print("column mapping: " + (", ".join(f"{k}->{v}" for k, v in sorted(mapping.items()))
                                or "NONE (no recognised columns)"))
    if problems:
        print("\n".join("  ! " + p for p in problems))
    print()

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SCHEMA)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {args.out} ({len(rows)} rows)")
    print()
    print(report(rows, problems, mapping))


if __name__ == "__main__":
    sys.exit(main())
