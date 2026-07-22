# Hidden Chain

> **"我用华为手表的PPG数据跑了一下Hidden Chain——底层是Thayer的神经内脏整合模型，加月经周期校准，再加中医辨证映射。结果出来了：气血不足、肝郁气滞、脾虚。跟我的中医把脉诊断完全对上了。被我自己做的算法惊呆了。"**

**可穿戴设备 → 月经周期校准 → 中医辨证 → 自主神经年龄。一个数字，一句话，看清自己。**

<p align="center">
  <a href="https://599d46bcc932429097eb3443c52f3cfc.app.codebuddy.work">
    <strong>→ Try the live demo ←</strong>
  </a>
  &nbsp;|&nbsp;
  <a href="https://599d46bcc932429097eb3443c52f3cfc.app.codebuddy.work/autonomic-age-guide.html">
    What is Autonomic Age?
  </a>
</p>

---

## What you get with one daily check-in

```
Your smartwatch →  Cycle-calibrated HRV  →  Hidden Chain Score (0-100)
                                + Autonomic Age (自主神经年龄)
                                + TCM diagnosis (气血/肝郁/脾虚)
                                + Disease risk alert (绿/黄/红)
```

You wear a Huawei/Apple/OPPO watch. Enter 3-5 numbers. Hidden Chain reads your heart rate variability, corrects for your menstrual cycle phase, maps the result to TCM diagnostics, and gives you:

- **One score.** How is your body doing today?
- **One age.** How old is your autonomic nervous system?
- **One sentence.** What should you do about it?

No dashboard fatigue. No 20-page report. Just what matters.

## 🔬 Research foundation — 8 papers, 4 Tier 1

| # | Direction | Key paper | Core finding |
|---|---|---|---|
| 1 | HRV age baselines | Shaffer & Ginsberg 2017 (7,182 citations) | RMSSD 20s=55ms → 60s=25ms |
| 2 | Female lifespan | de Jager 2025 (*Sports Med*, IF 13.0) | Postmenopause: pNN50 drops 63% |
| 3 | TCM ↔ HRV | Olivera-Toro 2019 | Spleen def → SDNN↓17%, HF↓14% |
| 4 | HRR aging clock | Cole 1999 (*NEJM*, IF 96.2) | HRR≤12bpm → 4× mortality risk |
| 5 | Disease risk thresholds | Jarczok & Thayer 2019 (N=9,550) | RMSSD<25ms → CVD risk ×1.5-3.5 |

Plus 3 core papers: Holzman & Bridgett 2017, de Jager 2025, Thayer & Lane 2009.

Full notes in [/research](/research).

## 📊 How the score works

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

## 🏃 Quick start

```bash
git clone git@github.com:soneei/hidden-chain.git
cd hidden-chain
pip install -r requirements.txt
python server.py
```

Open http://localhost:5000. Deploy on Render.com (free) for public access — Procfile included.

## 📁 Project structure

```
src/          Core engine (zero-dep Python)
  hrv_engine.py            Cycle calibration + dual-track HRV
  hidden_chain_score.py    Scoring + Autonomic Age + risk alert
  data_loader.py           Legacy Excel → engine bridge
  device_adapters.py       Huawei / Apple / OPPO parsers
research/     8 papers, Tier 1+2 quality standard enforced
design/       Architecture docs (Founder-Market Fit, DTx roadmap)
data/         Web form, consumer education page, daily log template
server.py     Flask API (SQLite, multi-user)
Procfile      One-click deploy (Render, Railway)
```

## License

MIT
