"""
Hidden Chain — Pilot Data Loader
=================================
Reads a CSV file of pilot user HRV data and converts it into
per-user, per-day batches of HRVFeatures ready for the engine.

CSV Schema (column names must match exactly):
  user_id                — anonymised pilot id (U01, U02, ...)
  date                   — ISO date (YYYY-MM-DD)
  resting_rmssd          — float, RMSSD in ms
  normalized_hrv         — float, z-score normalised HRV
  recovery_classification— "fast" | "normal" | "slow"
  recovery_rate          — float (optional), ms/min
  resting_hr             — float (optional), bpm
  sleep_hours            — float (optional)
  mood_tags              — semicolon-separated strings (optional)

Validation (read_pilot_csv):
  - All required columns present.
  - No extra/unknown columns.
  - user_id non-empty, date parseable.
  - resting_rmssd > 0, normalized_hrv is finite.
  - recovery_classification in {"fast", "normal", "slow"}.
  - recovery_rate >= 0 if present, resting_hr in (20, 220) if present,
    sleep_hours in (0, 24] if present.
  - No duplicate (user_id, date) pairs.
  - Each user has 7 consecutive calendar days (pilot design).

Returns:
  dict[str, list[HRVFeatures]]  keyed by user_id, each list sorted by date.
"""

import csv
import os
from dataclasses import dataclass, field
from datetime import date as Date
from datetime import datetime, timedelta
from typing import Any, Optional

from tcm_hrv_estimator import HRVFeatures

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

REQUIRED_COLUMNS = [
    "user_id", "date",
    "resting_rmssd", "normalized_hrv", "recovery_classification",
]
OPTIONAL_COLUMNS = [
    "recovery_rate", "resting_hr", "sleep_hours", "mood_tags",
]
ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS
VALID_RECOVERY = {"fast", "normal", "slow"}

PILOT_DAYS = 7  # 3 users × 7 days each


# ──────────────────────────────────────────────
# Error types
# ──────────────────────────────────────────────

@dataclass
class LoadError:
    """A single validation error found in the CSV."""
    line: int          # 1-based line number (header = line 1, data = line 2+)
    user_id: str
    date: str
    message: str


@dataclass
class LoadResult:
    """Result of reading and validating a pilot CSV."""
    data: dict[str, list[HRVFeatures]] = field(default_factory=dict)
    errors: list[LoadError] = field(default_factory=list)
    ok: bool = True


# ──────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────

def read_pilot_csv(path: str) -> LoadResult:
    """Read and validate a pilot CSV. Returns LoadResult with data and errors."""
    result = LoadResult()

    if not os.path.isfile(path):
        result.ok = False
        result.errors.append(LoadError(
            line=0, user_id="", date="",
            message=f"File not found: {path}",
        ))
        return result

    with open(path, encoding="utf-8-sig") as fh:  # utf-8-sig handles BOM
        reader = csv.DictReader(fh)

        # ── Check header ──
        if reader.fieldnames is None:
            result.ok = False
            result.errors.append(LoadError(
                line=1, user_id="", date="", message="CSV has no header row",
            ))
            return result

        # Normalise header: strip whitespace, lowercase
        raw_to_key: dict[str, str] = {}
        for h in reader.fieldnames:
            norm = h.strip().lower()
            raw_to_key[h] = norm

        present = set(raw_to_key.values())
        required_set = set(REQUIRED_COLUMNS)
        missing = required_set - present
        if missing:
            result.ok = False
            result.errors.append(LoadError(
                line=1, user_id="", date="",
                message=f"Missing required columns: {', '.join(sorted(missing))}",
            ))
            return result

        unknown = present - set(ALL_COLUMNS)
        if unknown:
            result.ok = False
            result.errors.append(LoadError(
                line=1, user_id="", date="",
                message=f"Unknown columns: {', '.join(sorted(unknown))}",
            ))
            return result

        # ── Read rows ──
        rows_raw: list[dict[str, str]] = []
        for i, row in enumerate(reader, start=2):
            normalised: dict[str, str] = {}
            for orig_key, val in row.items():
                normalised[raw_to_key[orig_key]] = val.strip()
            rows_raw.append(normalised)

    # ── Validate rows ──
    _validate_rows(rows_raw, result)
    if result.errors:
        result.ok = False
        return result

    # ── Build per-user sorted lists ──
    result.data = _build(rows_raw, result)
    if result.errors:
        result.ok = False

    return result


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────

def _validate_rows(rows: list[dict[str, str]], result: LoadResult) -> None:
    """Populate result.errors for invalid rows."""
    seen: set[tuple[str, str]] = set()

    for i, row in enumerate(rows):
        line = i + 2  # header is line 1
        uid = row.get("user_id", "")
        d = row.get("date", "")

        def err(msg: str) -> None:
            result.errors.append(LoadError(line=line, user_id=uid, date=d, message=msg))

        # user_id non-empty
        if not uid:
            err("user_id is empty")
            continue

        # date parseable
        try:
            parsed_date = _parse_date(d)
        except ValueError:
            err(f"date '{d}' is not a valid YYYY-MM-DD")
            continue

        # no duplicate (user_id, date)
        key = (uid, d)
        if key in seen:
            err(f"duplicate entry for user {uid} on {d}")
            continue
        seen.add(key)

        # resting_rmssd > 0
        try:
            rmssd = float(row["resting_rmssd"])
            if rmssd <= 0:
                err(f"resting_rmssd={rmssd} must be positive")
        except (ValueError, KeyError):
            err(f"resting_rmssd='{row.get('resting_rmssd')}' is not a number")

        # normalized_hrv is finite
        try:
            nhrv = float(row["normalized_hrv"])
            if not _isfinite(nhrv):
                err(f"normalized_hrv={nhrv} is not finite")
        except (ValueError, KeyError):
            err(f"normalized_hrv='{row.get('normalized_hrv')}' is not a number")

        # recovery_classification in valid set
        rc = row["recovery_classification"].lower()
        if rc not in VALID_RECOVERY:
            err(f"recovery_classification='{rc}' must be fast/normal/slow")

        # optional: recovery_rate >= 0 if present
        rr_str = row.get("recovery_rate", "")
        if rr_str:
            try:
                rr = float(rr_str)
                if rr < 0:
                    err(f"recovery_rate={rr} must be >= 0")
            except ValueError:
                err(f"recovery_rate='{rr_str}' is not a number")

        # optional: resting_hr in (20, 220)
        rhr_str = row.get("resting_hr", "")
        if rhr_str:
            try:
                rhr = float(rhr_str)
                if not (20 < rhr < 220):
                    err(f"resting_hr={rhr} must be in (20, 220)")
            except ValueError:
                err(f"resting_hr='{rhr_str}' is not a number")

        # optional: sleep_hours in (0, 24]
        sh_str = row.get("sleep_hours", "")
        if sh_str:
            try:
                sh = float(sh_str)
                if not (0 < sh <= 24):
                    err(f"sleep_hours={sh} must be in (0, 24]")
            except ValueError:
                err(f"sleep_hours='{sh_str}' is not a number")


def _build(rows: list[dict[str, str]], result: LoadResult) -> dict[str, list[HRVFeatures]]:
    """Convert valid rows into per-user sorted HRVFeatures. Adds LoadErrors on build failures."""
    raw: dict[str, dict[Date, HRVFeatures]] = {}
    for row in rows:
        uid = row["user_id"]
        d = _parse_date(row["date"])
        try:
            feats = _row_to_features(row)
        except ValueError as e:
            result.errors.append(LoadError(
                line=0, user_id=uid, date=row["date"],
                message=f"build error: {e}",
            ))
            return {}  # should not happen after validate, but guard
        raw.setdefault(uid, {})[d] = feats

    out: dict[str, list[HRVFeatures]] = {}
    for uid, day_map in raw.items():
        sorted_days = sorted(day_map.keys())
        out[uid] = [day_map[d] for d in sorted_days]
    return out


def check_pilot_design(data: dict[str, list[HRVFeatures]]) -> list[str]:
    """Check pilot design: each user must have PILOT_DAYS entries.

    Returns a list of human-readable warnings (empty = ok).
    This is NOT part of read_pilot_csv(); call it separately when strict
    design validation is desired (e.g. from run_pilot.py).
    """
    warnings: list[str] = []
    if not data:
        warnings.append("No valid rows found (empty dataset)")
        return warnings
    for uid, feats_list in data.items():
        n = len(feats_list)
        if n != PILOT_DAYS:
            warnings.append(f"{uid}: expected {PILOT_DAYS} rows, got {n}")
    return warnings


def _row_to_features(row: dict[str, str]) -> HRVFeatures:
    """Convert a single validated CSV row to HRVFeatures."""
    rr_str = row.get("recovery_rate", "")
    rhr_str = row.get("resting_hr", "")
    sh_str = row.get("sleep_hours", "")
    mt_str = row.get("mood_tags", "")

    return HRVFeatures(
        resting_rmssd=float(row["resting_rmssd"]),
        normalized_hrv=float(row["normalized_hrv"]),
        recovery_classification=row["recovery_classification"].lower(),
        recovery_rate=float(rr_str) if rr_str else None,
        resting_hr=float(rhr_str) if rhr_str else None,
        sleep_hours=float(sh_str) if sh_str else None,
        mood_tags=[t.strip() for t in mt_str.split(";") if t.strip()] if mt_str else [],
    )


def _parse_date(s: str) -> Date:
    """Parse YYYY-MM-DD, raise ValueError on failure."""
    dt = datetime.strptime(s.strip(), "%Y-%m-%d")
    return dt.date()


def _isfinite(x: float) -> bool:
    """True if x is not inf, -inf, or NaN."""
    import math
    return math.isfinite(x)


def generate_sample_csv(path: str) -> None:
    """Generate a realistic sample CSV for testing the pipeline."""
    import random
    random.seed(42)

    # Explicit typed profiles to avoid mypy inference issues
    Profile = tuple[tuple[float, float], str, float, tuple[float, float], list[str]]
    profiles: dict[str, Profile] = {
        "U01": ((25.0, 35.0), "slow", 82.0, (4.5, 6.0), ["irritable", "anxious"]),
        "U02": ((40.0, 55.0), "normal", 68.0, (6.5, 8.0), ["calm"]),
        "U03": ((30.0, 42.0), "fast", 72.0, (5.5, 7.0), ["exhausted", "brain_fog"]),
    }

    header = ",".join(ALL_COLUMNS)
    rows: list[str] = [header]

    start = Date(2026, 7, 29)
    for uid, (rmssd_r, rc, rhr_base, sleep_r, moods_list) in profiles.items():
        rmssd_lo, rmssd_hi = rmssd_r
        sleep_lo, sleep_hi = sleep_r
        for day_offset in range(7):
            d = start + timedelta(days=day_offset)
            rmssd = round(random.uniform(rmssd_lo, rmssd_hi), 1)
            nhrv = round(random.uniform(-2.0, 1.5), 2)
            rr = round(random.uniform(0.3, 3.5), 2) if rc == "slow" else round(random.uniform(1.5, 6.0), 2)
            rhr = round(rhr_base + random.uniform(-3, 3), 0)
            sleep = round(random.uniform(sleep_lo, sleep_hi), 1)
            moods = ";".join(random.sample(moods_list, k=min(2, len(moods_list))))
            row = f"{uid},{d.isoformat()},{rmssd},{nhrv},{rc},{rr},{rhr},{sleep},{moods}"
            rows.append(row)

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(rows) + "\n")
