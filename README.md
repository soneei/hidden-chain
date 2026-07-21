# Hidden Chain

**可穿戴设备 → 月经周期校准 → 中医辨证评分。一个数字，一句话，看清自己。**

Wearable-to-TCM (Traditional Chinese Medicine) health scoring engine. A single daily number built on peer-reviewed autonomic neuroscience, calibrated for the menstrual cycle (月经周期), and mapped to TCM diagnostics (中医辨证).

<p align="center">
  <a href="https://599d46bcc932429097eb3443c52f3cfc.app.codebuddy.work">
    <strong>→ Try the live demo ←</strong>
  </a>
</p>

## What it does

```
Your smartwatch data  →  Cycle-calibrated HRV analysis  →  Hidden Chain Score (0-100) + TCM insight
```

You wear a Huawei/Apple/OPPO watch. Hidden Chain reads your heart rate variability (HRV, 心率变异性), corrects for where you are in your menstrual cycle (so normal luteal-phase dips don't get flagged as "stress"), then maps the result to TCM concepts: qi-blood deficiency (气血不足), liver qi stagnation (肝郁气滞), spleen deficiency (脾虚).

**One number. One sentence. No dashboard fatigue.**

## Quick links

**[Live demo →](https://599d46bcc932429097eb3443c52f3cfc.app.codebuddy.work)** — Same page as above. 30-second daily check-in, stores your history.

## Try it

```bash
git clone git@github.com:soneei/hidden-chain.git
cd hidden-chain
pip install -r requirements.txt
python server.py
```

Open http://localhost:5000 — enter HRV, resting heart rate, and cycle day. Get your score.

## Research foundation

Built directly on three Tier 1 papers (Q1 journals, meta-analyses):

| # | Paper | Journal | Core contribution |
|---|---|---|---|
| 1 | HRV as a biomarker for self-regulation (Holzman & Bridgett, 2017) | *Neuroscience & Biobehavioral Reviews* (IF 9.0) | 123-study meta-analysis: HRV → self-regulation confirmed |
| 2 | Wearable HRV across the menstrual cycle (de Jager et al., 2025) | *Sports Medicine* (IF 13.0) | Living systematic review: 3-9% RMSSD drop across cycle phases |
| 3 | Neurovisceral integration model (Thayer & Lane, 2009) | *Neuroscience & Biobehavioral Reviews* (IF 9.0) | 1,788 citations: CAN → vagus → heart → health |

Full notes and quality standards in `/research`.

## How the score works

```
Hidden Chain Score = baseline HRV (0.30)
                   + recovery rate (0.25)
                   + TCM balance (0.25)
                   + cycle adjustment (0.20)
```

| Score | Level | Meaning |
|---|---|---|
| 81-100 | Purple | Peak — qi and blood are full. Challenge yourself. |
| 61-80 | Green | Good — steady rhythm, maintain your pace. |
| 31-60 | Yellow | Caution — liver qi mildly stagnant. Breathe, walk. |
| 0-30 | Red | Rest — vital energy low. Prioritize recovery. |

## Project structure

```
src/          Core engine (zero-dep Python)
  hrv_engine.py             Cycle calibration + dual-track HRV processing
  hidden_chain_score.py     Scoring engine + trend analysis
  data_loader.py            Legacy Excel → engine bridge
  device_adapters.py        Huawei / Apple / OPPO export parsers
research/     Paper notes (Tier 1 only, quality standard enforced)
design/       Architecture docs (Founder-Market Fit, 3-layer model, DTx roadmap)
data/         Web form, daily log template
server.py     Flask API (SQLite backend, ready for deployment)
```

## Roadmap

- **v0.3** (now): Web check-in + device adapters
- **v0.5**: Drag-and-drop watch export import + SQLite multi-user persistence
- **v1.0**: Chat-based interaction (DingTalk bot / Telegram)

## License

MIT
