# Intelligent Interaction Layer — Design Vision

> **⚠️ 设计愿景（roadmap），部分未实现；实际 schema 以 `server.py` 为准。**
> 本文档描述 v0.3 / v0.5 / v1.0 的演进路线图与交互设想：v0.5 的 `device_adapters.py`（多品牌手表导入）当前为**孤儿模块**（无功能调用），v1.0 的 chat bot（钉钉/Telegram/Streamlit）**未实现**。下方「Data architecture」的 `CREATE TABLE` 已与 `server.py:40-58` 的实际建表语句逐项对齐（列名、类型、默认值、索引一致），如需权威定义仍以 `server.py` 代码为准。

## The problem

Users have data from multiple watch brands (Huawei, Apple, OPPO) stored in manual Excel logs. Current flow: export → copy-paste → run script. Nobody will do this daily.

## Evolution roadmap

```
v0.3 (web form)         v0.5 (export import)      v1.0 (chat bot)
     │                       │                       │
30-sec daily form    drag-and-drop export    "How's my body today?"
enter 3 numbers      auto-parses format      engine replies with score
     │                       │                       │
     └───────────────────────┴───────────────────────┘
                         all share unified format
```

## v0.3: Minimal daily web form

**Design principle**: 30 seconds, 3 fields, no friction.

```
┌──────────────────────────────────────┐
│  Hidden Chain — Daily Check-in       │
│                                      │
│  Date: [2026-07-21]                  │
│  HRV (RMSSD): [___]  ms             │
│  Resting HR:   [___]  bpm           │
│  Cycle day:    [___]  (1-35)        │
│  Mood (1-10):  [___]  (optional)    │
│  Notes:        [_______________]    │
│                                      │
│  [Submit]   Today's score appears    │
└──────────────────────────────────────┘
```

- Just 3 required fields: hrv_rmssd, resting_hr, cycle_day
- Each submission immediately returns the Hidden Chain Score
- Data appends to a local SQLite database (no more Excel fragmentation)
- Works offline, single HTML file with vanilla JS

## v0.5: Watch export importer

Multi-brand device adapters (`device_adapters.py`):
- **Huawei Health**: reads JSON export → extracts HRV/RHR/sleep
- **Apple Health**: reads HealthKit XML/CSV export → extracts HRV/RHR
- **OPPO HeyTap**: reads export format → extracts equivalent metrics
- **Generic CSV**: matches column headers heuristically

All outputs normalize to:
```json
{
  "date": "2026-07-21",
  "device": "huawei_band6pro",
  "hrv_rmssd": 45.0,
  "resting_hr": 68,
  "sleep_hours": 7.2,
  "spo2": 97
}
```

## v1.0: Chat-based interaction

Natural language interface. User says:
- "How am I today?" → engine queries latest data → replies with score
- "Compare this week to last week" → trend analysis
- "I feel anxious today" → logs mood + runs engine → replies with TCM insight

Implementation paths:
- **DingTalk bot (钉钉机器人)**: since user already has DingTalk connector connected
- **Telegram bot**: simplest to prototype, works on any device
- **Streamlit web app**: Python-native, no backend needed, deployable on CloudStudio

## Data architecture

All user data stored in `data/hidden_chain.db` (SQLite):

```sql
-- 实际建表语句见 server.py:40-58（AUTOINCREMENT / DEFAULT / 迁移补列 mood_tags 等）。
CREATE TABLE daily_log (
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
);

CREATE UNIQUE INDEX idx_user_date ON daily_log(user_id, date);
```

## Multi-user support

- Each user identified by `user_id`
- Engine runs per-user with independent cycle calibration
- Cross-user comparison disabled (privacy by design)
- Admin view for aggregate trends (future)

## UX principle

> "Your wearables silently collect the data. You check in for 30 seconds a day. Hidden Chain handles everything in between."
