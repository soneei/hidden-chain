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

## Legacy format (Excel) — 未实现 / 设计设想

> ⚠️ **以下内容从未实现，仅作为早期设计设想保留，不代表当前代码能力。**
> 本仓库 `src/` 目录**不含任何 `pandas` 引用**，`data_loader.py` 只提供 CSV 加载（`read_pilot_csv` 等），**没有** `hidden_chain_dataset_updated.xlsx` 自动映射路径。请勿依赖此段。

早期设想：兼容上一版 Hidden Chain 的 `hidden_chain_dataset_updated.xlsx`，由 `data_loader.py` 自动映射字段（如 `hrv` → rmssd、`resting_hr` → heart_rate、`menstrual_phase` → cycle_day、`emotional_health` → mood_score）。该 Excel 适配层在当前代码库中不存在。

## Running the engine

```bash
cd src
python hrv_engine.py            # runs with mock data to verify the pipeline
python hidden_chain_score.py    # standalone Hidden Chain Score demo
```

> 注：`data_loader.py` 没有 `if __name__ == "__main__"` 入口，不能通过上述 `python data_loader.py` 直接运行；真实数据请走 `daily_log_template.csv` + `read_pilot_csv`（见上方「Daily log (recommended)」段）。
