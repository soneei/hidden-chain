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
from tcm_report import build_tcm_report, report_to_dict

# ── App setup ──
BASE_DIR = Path(__file__).parent
# 数据目录可用 HC_DATA_DIR 覆盖。Render 之类 PaaS 的容器文件系统是**临时的**，
# 每次部署/重启都会重置，所以线上必须把这个变量指到挂载的持久磁盘
# （见 render.yaml 的 disk.mountPath 与 DEPLOY_RENDER.md）。不设则用仓库内
# 的 data/，保持本地开发行为不变。
DATA_DIR = Path(os.environ.get("HC_DATA_DIR") or (BASE_DIR / "data"))
DB_PATH = DATA_DIR / "hidden_chain.db"
app = Flask(__name__, static_folder="data")


def init_db():
    # 新挂载的磁盘 / 全新容器里目录可能还不存在，sqlite3.connect 不会自己建父目录。
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
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
            mood_tags TEXT,
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
    # 迁移：早于 mood_tags 的库没有该列，补上（幂等，保留既有数据）
    cols = {row[1] for row in conn.execute("PRAGMA table_info(daily_log)")}
    if "mood_tags" not in cols:
        conn.execute("ALTER TABLE daily_log ADD COLUMN mood_tags TEXT")
    conn.commit()
    conn.close()


def parse_mood_tags(raw: object) -> list[str]:
    """把前端传来的情志标签规整为干净列表。

    前端 `#moodTagsVal` 发的是逗号串（"anxious,irritable"），但也容忍
    JSON 数组。去空白、去空项、去重且保持顺序。
    """
    if raw is None:
        return []
    if isinstance(raw, str):
        items = raw.split(",")
    elif isinstance(raw, (list, tuple)):
        items = [str(t) for t in raw]
    else:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for t in items:
        t = t.strip()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def parse_optional_float(raw: object) -> float | None:
    """把可选数值字段（睡眠时长等）规整为 float 或 None。

    前端空着不填时 `parseFloat('')||null` 发的是 JSON null，但别的客户端
    （curl / 旧页面 / 表单直传）会发空串 `""`。空串一路写进库后，回读时
    `float("")` 直接抛 ValueError 让整个打卡 500——所以入库前和回读后都过这里。
    """
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def get_history(user_id="default", days=30):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT hcs_score FROM daily_log WHERE user_id=? ORDER BY date DESC LIMIT ?",
        (user_id, days)
    ).fetchall()
    conn.close()
    return [r[0] for r in reversed(rows) if r[0] is not None]


def run_engine_for_user(user_id="default", cycle_day=None, mood_tags=None):
    """Load user's historical data, calibrate, analyze latest.

    mood_tags 属于「当日主观输入」，不从历史行回读，由调用方（本次打卡）直接传入。
    sleep_hours 与 resting_hr 相反：它们是**已落库的当日测量值**，所以从最新一行
    回读即可，`/api/dashboard` 这类不带入参的调用也能因此拿到正确结果。
    """
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT hrv_rmssd, resting_hr, cycle_day, date, sleep_hours "
        "FROM daily_log WHERE user_id=? ORDER BY date",
        (user_id,)
    ).fetchall()
    conn.close()

    if not rows:
        return None, None, None, "No history found."

    records = []
    days = []
    sleeps: list[float | None] = []
    for hrv, rhr, cd, dt, slp in rows:
        if cd is None:
            continue
        records.append(HRVRecord(
            timestamp=dt, rmssd=hrv, sdnn=0, hf=0, lf=0,
            heart_rate=rhr, is_resting=True
        ))
        days.append(int(cd))
        # 与 records 保持同步 append：上面的 `continue` 会跳过无周期日的行，
        # 若按 rows[-1] 取睡眠时长就会张冠李戴地配到另一天的记录上。
        sleeps.append(parse_optional_float(slp))

    if not records:
        return None, None, None, "No valid records with cycle day."

    engine = HRVEngine()
    if len(records) >= 3:
        engine.fit_calibrator(records, days)

    baseline = records[0].rmssd if records else 40.0
    day = cycle_day if cycle_day else days[-1]
    # resting_hr 不必显式传：analyze_day 会从 records[-1].heart_rate 回落，
    # 而该字段正是上面从 daily_log.resting_hr 填进去的。
    reg_idx, hcs = engine.analyze_day(
        records[-1], day_of_cycle=day, baseline_hrv=baseline, mood_tags=mood_tags,
        sleep_hours=sleeps[-1]
    )
    trend = TrendAnalysis.from_history(get_history(user_id, 30))

    return hcs, reg_idx, trend, None


# ── WSGI bootstrap ──
# gunicorn（Render 的 startCommand 是 `gunicorn server:app`）只是 import 本模块拿
# `app`，**永远不会进入下面的 __main__ 分支**。建表与列迁移因此必须在 import 时
# 就执行，否则线上第一个请求就是 "no such table: daily_log"。
# 重复调用无害：CREATE TABLE IF NOT EXISTS 与 PRAGMA 守卫的 ALTER TABLE 都幂等。
init_db()


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
    mood_tags = parse_mood_tags(data.get("mood_tags"))
    sleep_h = parse_optional_float(data.get("sleep_hours"))
    event = data.get("event_label", "")
    date = data.get("date", "")

    if not date:
        from datetime import date as dt
        date = str(dt.today())

    # Save to SQLite
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT OR REPLACE INTO daily_log
           (user_id, date, hrv_rmssd, resting_hr, cycle_day, mood_score, mood_tags,
            sleep_hours, event_label)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, date, hrv, rhr, cycle_day, mood, ",".join(mood_tags), sleep_h, event)
    )
    conn.commit()
    conn.close()

    # Run engine
    hcs, index, trend, error = run_engine_for_user(user_id, cycle_day, mood_tags)

    if error:
        return jsonify({"error": error}), 400

    # 富报告：89 证型 TCM 报告层（家族聚类 + 必须面诊 + 证据等级）
    tcm_report = None
    if index is not None:
        try:
            tcm_report = report_to_dict(build_tcm_report(index.tcm))
        except Exception:
            tcm_report = None

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
            "phlegm_turbidity": round(hcs.phlegm_turbidity, 1),
            "yin_yang_balance": round(hcs.yin_yang_balance, 1),
        },
        "autonomic_age": hcs.autonomic_age,
        "autonomic_age_delta": hcs.autonomic_age_delta,
        "autonomic_age_text": hcs.autonomic_age_text,
        "risk_alert": hcs.risk_alert,
        "risk_alert_text": hcs.risk_alert_text,
        # 回显本次生效的情志标签：让前端/用户能确认标签确实被引擎采纳
        "mood_tags": mood_tags,
        "tcm_report": tcm_report,
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
    hcs, index, trend, error = run_engine_for_user(user_id)
    if error:
        return jsonify({"error": error}), 404

    tcm_report = None
    if index is not None:
        try:
            tcm_report = report_to_dict(build_tcm_report(index.tcm))
        except Exception:
            tcm_report = None

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
        "tcm_report": tcm_report,
        "trend": {
            "week_avg": round(trend.week_avg, 1) if trend else 0,
            "week_trend": trend.week_trend if trend else "stable",
        },
        "history": [{"date": r[0], "score": r[1]} for r in rows],
    })


# ── Startup ──

if __name__ == "__main__":
    # init_db() 已在 import 时跑过（见上方 WSGI bootstrap），这里不必重复。
    port = int(os.environ.get("PORT", 5000))
    # Werkzeug 调试器能在页面上执行任意代码，而这里绑的是 0.0.0.0（局域网可见），
    # 所以默认关闭；本地要热重载/回溯就显式 HC_DEBUG=1 python server.py。
    debug = os.environ.get("HC_DEBUG") == "1"
    print(f"\n  Hidden Chain Server running at http://localhost:{port}")
    print(f"  DB: {DB_PATH}")
    print(f"  Open http://localhost:{port} for the daily check-in form\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
