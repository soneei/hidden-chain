<div align="center">

<a href="https://599d46bcc932429097eb3443c52f3cfc.app.codebuddy.work">
  <h1><img src="https://raw.githubusercontent.com/soneei/hidden-chain/main/.github/logo.svg" width="36" style="vertical-align:middle"> Hidden Chain</h1>
</a>

**⌚ PPG → 🧠 NVI → 🩺 TCM → 🔮 自主神经年龄**

[![Demo](https://img.shields.io/badge/🔗_Live_Demo-Try_it_now-7c3aed?style=for-the-badge&logoColor=white)](https://599d46bcc932429097eb3443c52f3cfc.app.codebuddy.work)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat)](#license)
[![Research](https://img.shields.io/badge/papers-8-orange?style=flat)](research/)

<blockquote>
<em>"我用华为手表的PPG数据跑了一下Hidden Chain——底层是Thayer的神经内脏整合模型，加月经周期校准，再加中医辨证映射。结果出来了：气血不足、肝郁气滞、脾虚。跟我的中医把脉诊断完全对上了。被我自己做的算法惊呆了。"</em>
</blockquote>

<br>

```
📱 传感器层              🧬 算法层                📊 输出层
────────────────────────────────────────────────────────────
⌚ Huawei Watch          → HRV 周期校准            → Hidden Chain Score (0–100)
📱 Apple Watch           → Autonomic Age 估算      → 自主神经年龄 (26 yrs)
💍 Oura / Whoop          → TCM 辨证 (5个症型)     → 🟢 气血 🟡 肝郁 🔴 脾虚
📊 CSV 手动输入          → 疾病风险三级预警 (绿/黄/红) → 一句话建议
```

</div>

---

## ✨ What you get

<table>
<tr>
<td width="25%" align="center">

### 🔮 One Score
*0–100 Hidden Chain Score*

Your body's daily status — cycle-calibrated, TCM-mapped, one number.

</td>
<td width="25%" align="center">

### 🧬 One Age
*Autonomic Age*

How old is your nervous system? 34 going on 26, or 34 going on 52?

</td>
<td width="25%" align="center">

### 🩺 Five Patterns
*TCM Diagnosis*

气血不足 · 肝郁气滞 · 脾虚 · 痰气互结 · 阴阳平衡

</td>
<td width="25%" align="center">

### 🚨 One Alert
*Disease Risk*

Green · Yellow · Red — powered by Thayer's 9,550-person study.

</td>
</tr>
</table>

---

## 🔬 Built on hard science

Every line of our engine cites a specific paper. Not marketing. Not vibes.

| # | Title | Journal | IF | N | Key finding | Our code |
|---|---|---|---|---|---|---|
| ① | An overview of HRV metrics and norms | *Front. Public Health* | 5.0 | 21,438 | RMSSD drops from 55→25ms (age 20→60) | `estimate_autonomic_age()` |
| ② | Wearable HRV across menstrual cycle | *Sports Medicine* | 13.0 | 16 studies | 3–9% HRV drop across cycle phases | `calibrate_cycle()` |
| ③ | Neurovisceral integration model | *Neurosc. Biobehav. Rev.* | 9.0 | 1,788 cites | Brain→vagus→heart→health pathway | `TCMMetrics.from_hrv()` |
| ④ | HRV for TCM pattern differentiation | *J Acupunct. Meridian Stud.* | – | 104 | Spleen def → SDNN↓17%, HF↓14% | `spleen_deficiency` |
| ⑤ | HRR as predictor of mortality | *NEJM* | 96.2 | 2,428 | HRR≤12bpm → 4× death risk | `compute_risk_alert()` |

**[→ Full research library (8 papers)](/research/)**

---

## 🎯 Why this exists

There are two worlds that rarely talk to each other:

**Western autonomic neuroscience** knows that HRV is a window into brain health. The neurovisceral integration model (Thayer & Lane, 1,788 citations) proved that your prefrontal cortex, amygdala, and vagus nerve form a continuous feedback loop — and HRV is its most accessible signal.

**Traditional Chinese Medicine** has been diagnosing qi-blood deficiency (气血不足), liver qi stagnation (肝郁气滞), and spleen deficiency (脾虚) for 2,000 years. But no one has put a number on it.

Hidden Chain bridges them. We don't replace TCM diagnosis — we give it a quantified signal from your wrist. The reason our algorithm matched the founder's in-person TCM diagnosis is not magic. It's because three independent research groups (Mexico, Taiwan, mainland China) all found the same thing: **TCM patterns produce measurable, reproducible HRV signatures.**

## 🔍 How the engine works (technical)

The score is a weighted composite of four sub-dimensions:

```
HCS = 0.30 × HRVbaseline  +  0.25 × Recovery  +  0.25 × TCMbalance  +  0.20 × PhaseAdj
```

**HRV baseline (0.30)** — Your RMSSD compared to the age-matched norm from Shaffer & Ginsberg 2017 (N=21,438). A 34-year-old with RMSSD 43ms scores neutral; RMSSD 55ms scores near-ceiling.

**Recovery index (0.25)** — Based on Cole 1999 (NEJM): how fast your heart rate returns to baseline after stress. Fast recovery → high vagal tone.

**TCM balance (0.25)** — Five-pattern syndrome differentiation scored from HRV features:
- **气血不足**: Low resting RMSSD relative to age norm
- **肝郁气滞**: Slow recovery + large HRV swings (NRICM 2010)
- **脾虚**: SDNN-depressed profile, elevated LF/HF (Olivera-Toro 2019)
- **痰气互结**: Abnormal HRV after removing cycle-phase effects
- **阴阳平衡**: Composite wellness index from the above four

**Phase adjustment (0.20)** — Cycle-phase offset. Luteal phase gets +0 (normal dip expected). Follicular gets +5 (higher baseline expected). This prevents false positives — a woman in her luteal phase is NOT "stressed"; she's physiologically normal.

## 🧠 Autonomic Age: your body's real clock

Your chronological age is on your ID. Your autonomic age is in your vagus nerve.

The calculation: `estimate_autonomic_age(RMSSD)` → linear interpolation across the population HRV curve.

| RMSSD | Autonomic Age | What it means |
|---|---|---|
| 55+ ms | ~20 | Elite — your nervous system is a decade younger than your body |
| 45 ms | ~33 | Average for 30s |
| 35 ms | ~46 | Premature autonomic aging — your body acts ~10 years older |
| 25 ms | ~67 | Disease-risk threshold (Jarczok/Thayer 2019, N=9,550) |

Autononomic Age adjusts for lifecycle stage:
- **Postmenopausal women**: RMSSD divided by 0.85 — same RMSSD means a younger autonomic age (estrogen loss naturally lowers HRV)
- **CHC users**: RMSSD + 3ms — hormonal contraceptives artificially suppress HRV (de Jager 2025)
- **Perimenopausal**: RMSSD divided by 0.92

---

## 🚀 Try it in 30 seconds

```bash
git clone git@github.com:soneei/hidden-chain.git
cd hidden-chain
pip install -r requirements.txt
python server.py
# → http://localhost:5000
```

Or **[open the live demo](https://599d46bcc932429097eb3443c52f3cfc.app.codebuddy.work)** — enter 3 numbers, get your score.

---

## 🧭 Architecture

```
┌──────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│ Data Sources │ →  │ HRV Engine (Track B) │ →  │ Hidden Chain     │
│              │    │                      │    │ Score + Report   │
│ ⌚ PPG/ECG   │    │ ・Cycle calibration  │    │                  │
│ 📋 CSV input │    │ ・Dual-track HRV     │    │ 0–100 Score      │
│ 🩺 Manual    │    │ ・TCM mapping        │    │ Autonomic Age    │
│              │    │ ・Recovery metrics   │    │ 5 TCM Patterns   │
│              │    │                      │    │ Risk Alert       │
└──────────────┘    └─────────────────────┘    └──────────────────┘
                              ↑
                     ┌────────┴─────────┐
                     │ Research Layer   │
                     │ (Track A, 8 papers)│
                     │ ・Age baselines   │
                     │ ・Lifecycle calib.│
                     │ ・TCM↔HRV mapping │
                     │ ・HRR aging clock │
                     │ ・Disease risk    │
                     └──────────────────┘
```

---

## 📁 Project

```
src/         Core engine (zero external dependencies)
  hrv_engine.py            HRV dual-track + TCM mapping
  hidden_chain_score.py    Scoring + Autonomic Age + Risk Alert
  data_loader.py           Excel/CSV bridge
  device_adapters.py       Huawei / Apple / OPPO parsers
research/    8 papers, Tier 1+2 quality standard
design/      Architecture & DTx roadmap
data/        Web form (HTML), consumer education, daily log
server.py    Flask API — SQLite, multi-user
```

---

<div align="center">

### Built with ❤️ by [@soneei](https://github.com/soneei) · MIT License

[![Star](https://img.shields.io/github/stars/soneei/hidden-chain?style=social)](https://github.com/soneei/hidden-chain)

</div>
