# Data format for Hidden Chain

## Daily log (recommended)

Use `daily_log_template.csv` as a starting point. Columns:

| Column | Type | Required | Description |
|---|---|---|---|
| date | YYYY-MM-DD | Yes | Date of measurement |
| hrv_rmssd | float (ms) | Yes | RMSSD from wearable |
| resting_hr | int (bpm) | Yes | Resting heart rate |
| cycle_day | int (1-35) | Yes | Day of menstrual cycle |
| event_label | text | No | e.g. "meeting", "exercise", "argument" |
| mood_score | int (1-10) | No | Subjective mood rating |
| sleep_hours | float | No | Hours slept last night |
| exercise | text | No | e.g. "run", "yoga", "rest" |

## Legacy format (Excel)

Works with `hidden_chain_dataset_updated.xlsx` from previous Hidden Chain builds.

Fields mapped automatically by `data_loader.py`:
- `hrv` → rmssd
- `resting_hr` → heart_rate
- `menstrual_phase` → cycle_day (via Chinese text → day mapping)
- `emotional_health` → mood_score

## Running the engine

```bash
cd src
python data_loader.py          # feeds your real Huawei data into the engine
python hrv_engine.py            # runs with mock data to verify the pipeline
python hidden_chain_score.py    # standalone Hidden Chain Score demo
```
