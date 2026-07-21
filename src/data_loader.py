"""
Hidden Chain — Data Loader
===========================
Reads health data from Excel, CSV, or JSON and converts to engine-compatible format.

支持格式：
  - Excel (.xlsx) — legacy Hidden Chain dataset format
  - CSV — standardized daily log
  - JSON — future API format
"""

import csv
import json
from pathlib import Path
from typing import Optional


def load_from_xlsx(path: str) -> list[dict]:
    """Read legacy Excel dataset (hidden_chain_dataset_updated.xlsx format)"""
    import pandas as pd
    df = pd.read_excel(path)
    records = []
    for _, row in df.iterrows():
        rec = {
            "user_id": str(row.get("user_id", "")),
            "date": str(row.get("date", "")),
            "device": str(row.get("device", "")),
            "hrv": _safe_float(row.get("hrv")),
            "resting_hr": _safe_float(row.get("resting_hr")),
            "spo2": _safe_float(row.get("spo2_avg")),
            "sleep_duration": _safe_float(row.get("sleep_duration")),
            "menstrual_phase": str(row.get("menstrual_phase", "")),
            "lived_exp": str(row.get("lived_exp", "")),
            "intervention": str(row.get("intervention", "")),
            "emotional_health": _safe_float(row.get("emotional_health")),
            "bmi": _safe_float(row.get("bmi")),
            "bp_systolic": _safe_float(row.get("bp_systolic")),
            "bp_diastolic": _safe_float(row.get("bp_diastolic")),
            "body_temp": _safe_float(row.get("body_temp")),
        }
        records.append(rec)
    return records


def load_from_csv(path: str) -> list[dict]:
    """Read standardized daily health log CSV"""
    records = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append({
                "date": row.get("date", ""),
                "hrv_rmssd": _safe_float(row.get("hrv_rmssd")),
                "resting_hr": _safe_float(row.get("resting_hr")),
                "cycle_day": _safe_int(row.get("cycle_day")),
                "event_label": row.get("event_label", ""),
                "mood_score": _safe_int(row.get("mood_score")),
                "sleep_hours": _safe_float(row.get("sleep_hours")),
                "exercise": row.get("exercise", ""),
            })
    return records


def phase_to_day(phase_text: str) -> Optional[int]:
    """Map Chinese menstrual phase text to approximate cycle day.

    这是从旧数据格式到新引擎的适配层。
    旧格式用文字描述阶段，新引擎需要具体天数。
    """
    text = str(phase_text).strip()

    if "月经第" in text or "经期第" in text:
        try:
            return int("".join(c for c in text if c.isdigit()))
        except ValueError:
            pass

    mapping = {
        "月经第3天": 3, "月经第4天": 4, "月经第5天": 5,
        "经期第4天": 4,
        "卵泡期": 10, "卵泡早期": 8, "卵泡中期": 12,
        "排卵期": 16,
        "黄体期": 21, "黄体早期": 19, "黄体中期": 22, "黄体期末": 25,
        "经前期": 26,
    }

    for key, day in mapping.items():
        if key in text:
            return day

    # 无法识别阶段 → 假设卵泡中期（推荐基线窗口）
    return None


def prepare_for_engine(records: list[dict], user_id: str = "U001_Sona",
                       device_filter: str = None) -> tuple[list, list, list]:
    """Convert raw records to engine-ready format.

    Returns:
        (hrv_records, cycle_days, dates)
        where hrv_records is a list matching HRVRecord dataclass fields
    """
    from hrv_engine import HRVRecord

    hrv_records = []
    cycle_days = []
    dates = []

    for r in records:
        if r.get("user_id") and r["user_id"] != user_id:
            continue
        if device_filter and r.get("device") and device_filter not in r["device"]:
            continue
        if r.get("hrv") is None or r.get("resting_hr") is None:
            continue
        if r.get("date") == "nan" or r.get("date") == "":
            continue

        day = phase_to_day(r.get("menstrual_phase", ""))
        if day is None:
            continue

        rec = HRVRecord(
            timestamp=r["date"],
            rmssd=r["hrv"],
            sdnn=0,  # 旧数据没有 SDNN
            hf=0,    # 旧数据没有频域指标
            lf=0,
            heart_rate=r["resting_hr"],
            is_resting=True,
            subjective_mood=_safe_int(r.get("emotional_health")),
        )

        hrv_records.append(rec)
        cycle_days.append(day)
        dates.append(r["date"])

    return hrv_records, cycle_days, dates


def _safe_float(val) -> Optional[float]:
    try:
        v = float(val)
        return v if not (v != v) else None  # skip NaN
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> Optional[int]:
    v = _safe_float(val)
    return int(v) if v is not None else None


# ────────────────────────────────────────────
# CSV template generator
# ────────────────────────────────────────────

CSV_TEMPLATE_HEADERS = [
    "date", "hrv_rmssd", "resting_hr", "cycle_day",
    "event_label", "mood_score", "sleep_hours", "exercise"
]

CSV_TEMPLATE_ROWS = [
    "2026-07-21,45.0,68,12,,7,7.5,",
    "2026-07-22,42.0,70,13,meeting,5,6.0,run",
    "2026-07-23,50.0,65,14,,8,8.0,",
]


def create_template(path: str = None):
    """Generate a daily-log CSV template for new users."""
    if path is None:
        path = str(Path(__file__).parent.parent / "data" / "daily_log_template.csv")

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_TEMPLATE_HEADERS)
        for row in CSV_TEMPLATE_ROWS:
            writer.writerow(row.split(","))

    return path


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))

    # 测试：读取真实数据并送入引擎
    real_data_path = "/Users/sona/WorkBuddy/2026-06-23-10-31-58/hidden_chain_dataset_updated.xlsx"
    records = load_from_xlsx(real_data_path)
    print(f"Loaded {len(records)} records from legacy Excel")

    hrv_records, cycle_days, dates = prepare_for_engine(
        records, user_id="U001_Sona", device_filter="Huawei"
    )
    print(f"Filtered to {len(hrv_records)} valid Huawei records for Sona")

    for i, (rec, day, date) in enumerate(zip(hrv_records, cycle_days, dates)):
        print(f"  {date}: HRV={rec.rmssd}ms, HR={rec.heart_rate}bpm, cycle_day={day}")

    # 送进引擎
    from hrv_engine import HRVEngine

    engine = HRVEngine()

    if len(hrv_records) >= 2:
        engine.fit_calibrator(hrv_records, cycle_days)
        reg_idx, hcs = engine.analyze_day(
            hrv_records[-1], day_of_cycle=cycle_days[-1], baseline_hrv=hrv_records[0].rmssd
        )
        print()
        print(hcs.report())
        print()
        print(f"Regulation index: {reg_idx.score}/100")
