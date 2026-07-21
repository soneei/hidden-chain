"""
Hidden Chain — Device Adapters
================================
Reads export files from multiple smartwatch brands and normalizes
to a unified data format that the HRV engine can consume.

Supported:
  - Huawei Health JSON export
  - Apple Health XML/CSV export
  - OPPO HeyTap Health export
  - Generic CSV (column matching heuristic)
  - Hidden Chain daily log CSV
"""

from dataclasses import dataclass, asdict
from pathlib import Path
import csv
import json
import xml.etree.ElementTree as ET
from typing import Optional


@dataclass
class NormalizedRecord:
    """Unified format — all device data lands here before entering the engine."""
    date: str
    device: str
    hrv_rmssd: Optional[float] = None
    resting_hr: Optional[float] = None
    sleep_hours: Optional[float] = None
    spo2: Optional[float] = None
    steps: Optional[int] = None
    raw_source: str = ""  # original file path for traceability

    def is_valid(self) -> bool:
        return self.hrv_rmssd is not None and self.resting_hr is not None


# ──────────────────────────────────────────────────
# Huawei Health JSON
# ──────────────────────────────────────────────────

def parse_huawei_json(path: str) -> list[NormalizedRecord]:
    """Parse Huawei Health JSON export.

    Expected structure:
    {
      "data": [{
        "date": "2026-07-21",
        "heartRate": {"resting": 68, "min": 55, "max": 120},
        "hrv": {"rmssd": 45.2, "sdnn": 52.0},
        "sleep": {"duration": 450},
        "spo2": {"avg": 97}
      }]
    }
    """
    with open(path) as f:
        raw = json.load(f)

    records = []
    entries = raw.get("data", []) if isinstance(raw, dict) else raw

    for entry in entries:
        rec = NormalizedRecord(
            date=entry.get("date", ""),
            device="huawei",
            raw_source=path,
        )
        if "heartRate" in entry:
            rec.resting_hr = float(entry["heartRate"].get("resting", 0))
        if "hrv" in entry:
            rec.hrv_rmssd = float(entry["hrv"].get("rmssd", 0))
        if "sleep" in entry:
            dur = entry["sleep"].get("duration", 0)
            rec.sleep_hours = round(dur / 60, 1) if dur else None
        if "spo2" in entry:
            rec.spo2 = float(entry["spo2"].get("avg", 0))
        records.append(rec)

    return [r for r in records if r.is_valid()]


# ──────────────────────────────────────────────────
# Apple Health Export (XML)
# ──────────────────────────────────────────────────

def parse_apple_health_xml(path: str) -> list[NormalizedRecord]:
    """Parse Apple Health Export XML.

    Extracts:
      - HKQuantityTypeIdentifierHeartRateVariabilitySDNN → hrv_rmssd
      - HKQuantityTypeIdentifierRestingHeartRate → resting_hr
      - HKCategoryTypeIdentifierSleepAnalysis → sleep_hours
    """
    tree = ET.parse(path)
    root = tree.getroot()

    # Collect records by date
    from collections import defaultdict
    daily = defaultdict(dict)

    for record in root.findall(".//Record"):
        rtype = record.get("type", "")
        date = (record.get("startDate") or "")[:10]
        value = record.get("value")

        if not value:
            continue

        if "HeartRateVariabilitySDNN" in rtype:
            daily[date]["hrv_rmssd"] = float(value) * 1000  # seconds → ms
        elif "RestingHeartRate" in rtype:
            daily[date]["resting_hr"] = float(value)
        elif "SleepAnalysis" in rtype:
            dur = float(value)
            daily[date]["sleep_hours"] = round(daily[date].get("sleep_hours", 0) + dur / 3600, 1)

    records = []
    for date, vals in sorted(daily.items()):
        rec = NormalizedRecord(date=date, device="apple_watch", raw_source=path, **vals)
        if rec.is_valid():
            records.append(rec)

    return records


# ──────────────────────────────────────────────────
# OPPO HeyTap Health
# ──────────────────────────────────────────────────

OPPO_COLUMN_MAP = {
    "date": ["date", "日期", "time", "时间"],
    "hrv_rmssd": ["hrv", "rmssd", "心率变异性", "heart_rate_variability"],
    "resting_hr": ["resting_hr", "rhr", "静息心率", "resting_heart_rate", "heart_rate_rest"],
    "sleep_hours": ["sleep", "duration", "睡眠时长", "sleep_duration", "sleep_hours"],
    "spo2": ["spo2", "血氧", "oxygen", "血氧饱和度"],
}


def parse_generic_csv(path: str, device: str = "generic") -> list[NormalizedRecord]:
    """Parse any CSV by heuristically matching column headers.

    Works with OPPO exports and any CSV that has recognizable column names.
    """
    with open(path) as f:
        reader = csv.DictReader(f)
        headers = [h.lower().strip() for h in (reader.fieldnames or [])]
        rows = list(reader)

    # Build column index map
    col_idx = {}
    for field, aliases in OPPO_COLUMN_MAP.items():
        for alias in aliases:
            for i, h in enumerate(headers):
                if alias in h:
                    col_idx[field] = i
                    break
            if field in col_idx:
                break

    def _val(row, field):
        if field not in col_idx:
            return None
        try:
            return float(list(row.values())[col_idx[field]])
        except (ValueError, TypeError, IndexError):
            return None

    records = []
    for row in rows:
        rec = NormalizedRecord(
            date=str(list(row.values())[0]) if row else "",
            device=device,
            hrv_rmssd=_val(row, "hrv_rmssd"),
            resting_hr=_val(row, "resting_hr"),
            sleep_hours=_val(row, "sleep_hours"),
            spo2=_val(row, "spo2"),
            raw_source=path,
        )
        if rec.is_valid():
            records.append(rec)

    return records


# ──────────────────────────────────────────────────
# Auto-detection entry point
# ──────────────────────────────────────────────────

def auto_parse(path: str, device: str = "auto") -> list[NormalizedRecord]:
    """Auto-detect format and parse.

    Usage:
      records = auto_parse("data/sona_huawei_export.json")
      records = auto_parse("data/rongrong_apple_export.xml", device="apple_watch")
    """
    ext = Path(path).suffix.lower()

    if ext == ".json":
        return parse_huawei_json(path)
    elif ext == ".xml":
        return parse_apple_health_xml(path)
    elif ext == ".csv":
        brand = device.split("_")[0] if "_" in device else device
        return parse_generic_csv(path, device=brand)

    raise ValueError(f"Unsupported format: {ext}")


# ──────────────────────────────────────────────────
# Hidden Chain daily log CSV → engine records
# ──────────────────────────────────────────────────

def daily_log_to_records(path: str) -> list[dict]:
    """Read the standardized daily_log CSV format and return engine-ready dicts."""
    records = []
    with open(path) as f:
        for row in csv.DictReader(f):
            try:
                records.append({
                    "date": row.get("date", ""),
                    "hrv_rmssd": float(row.get("hrv_rmssd", 0)),
                    "resting_hr": float(row.get("resting_hr", 0)),
                    "cycle_day": int(row.get("cycle_day", 0)),
                    "mood_score": int(row.get("mood_score", 0)) if row.get("mood_score") else None,
                    "sleep_hours": float(row.get("sleep_hours", 0)) if row.get("sleep_hours") else None,
                    "event_label": row.get("event_label", ""),
                    "exercise": row.get("exercise", ""),
                })
            except (ValueError, TypeError):
                continue
    return records


# ──────────────────────────────────────────────────
# Quick test
# ──────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))

    # Test generic CSV parsing with the daily log template
    template = str(Path(__file__).parent.parent / "data" / "daily_log_template.csv")
    if Path(template).exists():
        records = parse_generic_csv(template, device="huawei_band6pro")
        print(f"Parsed {len(records)} records from template:")
        for r in records:
            print(f"  {r.date}: HRV={r.hrv_rmssd}ms, RHR={r.resting_hr}bpm, Sleep={r.sleep_hours}h")

    print("\nDevice adapters ready. Usage:")
    print("  auto_parse('export.json')          → Huawei JSON")
    print("  auto_parse('export.xml')           → Apple Health XML")
    print("  auto_parse('export.csv', 'oppo')   → OPPO CSV")
    print("  daily_log_to_records('mylog.csv')  → Daily log")
