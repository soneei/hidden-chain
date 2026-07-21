# Intelligent Interaction Layer — Design Vision

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
CREATE TABLE daily_log (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,
    date TEXT NOT NULL,
    device TEXT,
    hrv_rmssd REAL NOT NULL,
    resting_hr REAL NOT NULL,
    cycle_day INTEGER,
    mood_score INTEGER,
    sleep_hours REAL,
    event_label TEXT,
    hcs_score INTEGER,
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
