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
