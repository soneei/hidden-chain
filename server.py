"""
Hidden Chain — Flask API Server
=================================
Accepts daily check-in data, runs the full HRV engine,
returns Hidden Chain Score with TCM diagnostics.

Deploy: python server.py  →  http://localhost:5000
"""

import sqlite3
import json
import os
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory

# Engine imports — add src/ to path
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from hrv_engine import HRVEngine, HRVRecord, CyclePhase
from hidden_chain_score import HiddenChainScorer, TrendAnalysis

# ── App setup ──
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "hidden_chain.db"
app = Flask(__name__, static_folder="data")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT DEFAULT 'default',
            date TEXT NOT NULL,
            device TEXT DEFAULT 'manual',
            hrv_rmssd REAL NOT NULL,
            resting_hr REAL NOT NULL,
            cycle_day INTEGER NOT NULL,
            mood_score INTEGER,
            sleep_hours REAL,
            event_label TEXT,
            hcs_score INTEGER,
            phase TEXT,
            qi_blood REAL,
            liver_depression REAL,
            spleen_deficiency REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_user_date
        ON daily_log(user_id, date)
    """)
    conn.commit()
    conn.close()


def get_history(user_id="default", days=30):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT hcs_score FROM daily_log WHERE user_id=? ORDER BY date DESC LIMIT ?",
        (user_id, days)
    ).fetchall()
    conn.close()
    return [r[0] for r in reversed(rows) if r[0] is not None]


def run_engine_for_user(user_id="default", cycle_day=None):
    """Load user's historical data, calibrate, analyze latest."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT hrv_rmssd, resting_hr, cycle_day, date "
        "FROM daily_log WHERE user_id=? ORDER BY date",
        (user_id,)
    ).fetchall()
    conn.close()

    if not rows:
        return None, None, "No history found."

    records = []
    days = []
    for hrv, rhr, cd, dt in rows:
        if cd is None:
            continue
        records.append(HRVRecord(
            timestamp=dt, rmssd=hrv, sdnn=0, hf=0, lf=0,
            heart_rate=rhr, is_resting=True
        ))
        days.append(int(cd))

    if not records:
        return None, None, "No valid records with cycle day."

    engine = HRVEngine()
    if len(records) >= 3:
        engine.fit_calibrator(records, days)

    baseline = records[0].rmssd if records else 40.0
    day = cycle_day if cycle_day else days[-1]
    reg_idx, hcs = engine.analyze_day(records[-1], day_of_cycle=day, baseline_hrv=baseline)
    trend = TrendAnalysis.from_history(get_history(user_id, 30))

    return hcs, trend, None


# ── Routes ──

@app.route("/")
def index():
    return send_from_directory("data", "web_checkin.html")


@app.route("/api/checkin", methods=["POST"])
def checkin():
    data = request.get_json(force=True)
    user_id = data.get("user_id", "default")
    hrv = float(data["hrv_rmssd"])
    rhr = float(data["resting_hr"])
    cycle_day = int(data["cycle_day"])
    mood = data.get("mood_score")
    sleep_h = data.get("sleep_hours")
    event = data.get("event_label", "")
    date = data.get("date", "")

    if not date:
        from datetime import date as dt
        date = str(dt.today())

    # Save to SQLite
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT OR REPLACE INTO daily_log
           (user_id, date, hrv_rmssd, resting_hr, cycle_day, mood_score, sleep_hours, event_label)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, date, hrv, rhr, cycle_day, mood, sleep_h, event)
    )
    conn.commit()
    conn.close()

    # Run engine
    hcs, trend, error = run_engine_for_user(user_id, cycle_day)

    if error:
        return jsonify({"error": error}), 400

    # Update score back to DB
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE daily_log SET hcs_score=?, phase=?, qi_blood=?, liver_depression=?, spleen_deficiency=? WHERE user_id=? AND date=?",
        (hcs.score, hcs.phase.value, hcs.qi_blood, hcs.liver_depression, hcs.spleen_deficiency, user_id, date)
    )
    conn.commit()
    conn.close()

    return jsonify({
        "score": hcs.score,
        "level": hcs.level.value,
        "label": hcs.level.label,
        "takeaway": hcs.one_liner(),
        "phase": hcs.phase.value,
        "sub_scores": {
            "hrv_baseline": hcs.hrv_baseline,
            "recovery": hcs.recovery_index,
            "tcm_balance": hcs.tcm_balance,
            "phase_adjustment": hcs.phase_adjustment,
        },
        "tcm": {
            "qi_blood": round(hcs.qi_blood, 1),
            "liver_depression": round(hcs.liver_depression, 1),
            "spleen_deficiency": round(hcs.spleen_deficiency, 1),
        },
        "autonomic_age": hcs.autonomic_age,
        "autonomic_age_delta": hcs.autonomic_age_delta,
        "autonomic_age_text": hcs.autonomic_age_text,
        "trend": {
            "week_avg": round(trend.week_avg, 1),
            "month_avg": round(trend.month_avg, 1),
            "week_trend": trend.week_trend,
            "month_trend": trend.month_trend,
        } if trend else None,
    })


@app.route("/api/dashboard/<user_id>")
def dashboard(user_id):
    """Return user's history and latest score."""
    hcs, trend, error = run_engine_for_user(user_id)
    if error:
        return jsonify({"error": error}), 404

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT date, hcs_score FROM daily_log WHERE user_id=? AND hcs_score IS NOT NULL ORDER BY date",
        (user_id,)
    ).fetchall()
    conn.close()

    return jsonify({
        "score": hcs.score,
        "level": hcs.level.value,
        "takeaway": hcs.one_liner(),
        "phase": hcs.phase.value,
        "trend": {
            "week_avg": round(trend.week_avg, 1) if trend else 0,
            "week_trend": trend.week_trend if trend else "stable",
        },
        "history": [{"date": r[0], "score": r[1]} for r in rows],
    })


# ── Startup ──

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  Hidden Chain Server running at http://localhost:{port}")
    print(f"  Open http://localhost:{port} for the daily check-in form\n")
    app.run(host="0.0.0.0", port=port, debug=True)
