<div align="center">

<a href="https://599d46bcc932429097eb3443c52f3cfc.app.codebuddy.work">
  <h1><img src="https://raw.githubusercontent.com/soneei/hidden-chain/main/.github/logo.svg" width="36" style="vertical-align:middle"> Hidden Chain</h1>
</a>

**⌚ PPG → 🧠 NVI → 🩺 TCM → 🔮 自主神经年龄**

[![Demo](https://img.shields.io/badge/🔗_Live_Demo-Try_it_now-7c3aed?style=for-the-badge&logoColor=white)](https://599d46bcc932429097eb3443c52f3cfc.app.codebuddy.work)
[![CI](https://github.com/soneei/hidden-chain/actions/workflows/ci.yml/badge.svg)](https://github.com/soneei/hidden-chain/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat)](#license)

<blockquote>
<em>"我用华为手表的PPG数据跑了一下Hidden Chain——底层是Thayer的神经内脏整合模型，加月经周期校准，再加中医辨证映射。结果出来了：气血不足、肝郁气滞、脾虚。跟我的中医把脉诊断完全对上了。被我自己做的算法惊呆了。"</em>
<br>
<sub>— 创始人个人轶事（N=1 单例，<b>不是</b>临床验证，详见下方 <a href="#compliance--red-lines">合规红线</a>）。</sub>
</blockquote>

<br>

```
📱 传感器层              🧬 算法层                📊 输出层
────────────────────────────────────────────────────────────
⌚ Huawei Watch          → HRV 周期校准            → Hidden Chain Score (0–100)
📱 Apple Watch           → Autonomic Age 估算      → 自主神经年龄
💍 Oura / Whoop          → TCM 证候倾向 (5 轴)     → 🟢 气血 🟡 肝郁 🔴 脾虚
📊 CSV 手动输入          → 疾病风险三级预警        → 相关证型家族 + 需面诊清单
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

### 🩺 Five Tendency Axes
*HRV-based TCM tendency*

气血不足 · 肝郁气滞 · 脾虚 · 痰气互结 · 阴阳平衡
（每条带证据等级，非诊断）

</td>
<td width="25%" align="center">

### 🚨 One Alert
*Disease Risk*

Green · Yellow · Red — powered by Thayer's 9,550-person study.

</td>
</tr>
</table>

**Plus the TCM report layer** — given your HRV tendency, it pulls the *related syndrome families* from an 89-pattern ontology and produces an explicit **must-see-clinic** list: the patterns HRV **cannot** tell apart and that require an in-person TCM consultation.

---

## 🧬 How the engine works

The score is a weighted composite of four sub-dimensions:

```
HCS = 0.30 × HRVbaseline  +  0.25 × Recovery  +  0.25 × TCMbalance  +  0.20 × PhaseAdj
```

- **HRV baseline (0.30)** — RMSSD vs. the age-matched norm (Shaffer & Ginsberg 2017, N=21,438).
- **Recovery index (0.25)** — how fast heart rate returns to baseline after stress (Cole 1999, NEJM).
- **TCM balance (0.25)** — five HRV→tendency axes (see below). This is a **proxy**, not a diagnosis.
- **Phase adjustment (0.20)** — menstrual-cycle-phase offset, so a luteal-phase dip is not flagged as "stress".

### Autonomic Age
`estimate_autonomic_age(RMSSD)` interpolates along the population HRV curve (Jarczok/Thayer 2019, N=9,550). Lifecycle-calibrated (postmenopausal / CHC / perimenopausal).

---

## 🩺 The TCM layer — honest by design

The TCM module is split into **four separated, auditable pieces**. This separation is the whole point: *"what a syndrome is"* (textbook) is isolated from *"how HRV proxies it"* (evidence), so a reviewer can audit each independently.

| Module | Role | Depends on HRV? |
|---|---|---|
| `src/tcm_theory.py` | Pure textbook definitions (《中医诊断学》/《中医基础理论》): 5 engine axes, composite rules, `EvidenceGrade`, `TCM_DISCLAIMER` | **No** |
| `src/tcm_ontology.py` | 89 clinical patterns across 3 orthogonal axes (八纲 / 五脏六腑 / 六淫病因); `hrv_detectable` flags; verified `citations` | **No** |
| `src/tcm_hrv_estimator.py` | Maps `HRVFeatures` → `TCMAssessment` (primary/secondary/evidence/disclaimer) | **Yes** |
| `src/tcm_report.py` | `build_tcm_report()` → scored axes + related families + must-see-clinic list | consumes assessment |

**Key facts:**
- The engine scores **5 abstract axes** (qi-blood / liver-qi / spleen / phlegm / yin-yang balance). Of the **89 ontology patterns, only ~17 are `hrv_detectable=True`** — those with a real autonomic/vagal signature. The other ~72 are *theory-only* and used for auditability and report enrichment; **the engine never scores them from HRV.**
- Every HRV→syndrome link carries an `EvidenceGrade` (STRONG / MODERATE / WEAK / NONE). `MODERATE` and above **must** carry a verified citation (enforced by `validate_catalog()`). 5 real studies are referenced (anxiety/depression HRV, DOR HRV, chest-pain HRV, chronic-fatigue HRV, nine-constitution HRV).
- A `PRIMARY_MIN_SCORE = 50` gate prevents over-labeling: if the top disorder axis is below 50, the engine returns `BALANCED` ("无明显单证倾向") instead of naming a syndrome. The qi score is de-saturated so it no longer always maxes out and drowns specific tendencies.
- The composite pattern **肝肾阴虚 (liver-kidney yin deficiency) is deliberately NOT auto-asserted** — kidney-yin has no HRV proxy, so claiming it would cross the compliance line.

---

## 🔬 Built on hard science (honest version)

The **HRV core** cites specific, real studies (see `research/`):
- RMSSD age norms — Shaffer & Ginsberg 2017 (N=21,438)
- Neurovisceral integration model — Thayer & Lane (1,788 cites)
- Recovery / HRR — Cole 1999 (NEJM)
- Disease-risk threshold — Jarczok/Thayer 2019 (N=9,550)

The **HRV→TCM links are proxies with graded evidence**, not textbook diagnoses. The original mapping (qi-blood / liver-qi / spleen / phlegm / balance) is preserved numerically; its supporting HRV→pattern studies are listed per-entry in `tcm_ontology.py` with explicit grades. **We do not claim "every line cites a paper."** What we claim: every module is grounded in either a textbook (TCM) or a verified study, and every HRV→TCM claim is explicitly graded and, where applicable, cited.

**[→ Full research library](/research/)**

---

## 🚀 Try it in 30 seconds

```bash
git clone git@github.com:soneei/hidden-chain.git
cd hidden-chain
pip install -r requirements.txt
python server.py
# → http://localhost:5000
```

Or **[open the live demo](https://599d46bcc932429097eb3443c52f3cfc.app.codebuddy.work)** — enter a few numbers, get your score.

---

## 📥 Data pipeline (pilot / batch reports)

For the 3-person × 7-day pilot, input is a CSV and the engine produces 21 daily reports + 3 trend summaries in one command.

**CSV schema** (column names must match exactly; `*` = optional):

| Column | Type | Notes |
|---|---|---|
| `user_id` | str | anonymised id, e.g. `U01` |
| `date` | str | `YYYY-MM-DD` |
| `resting_rmssd` | float | RMSSD in ms, must be > 0 |
| `normalized_hrv` | float | z-score normalised HRV (finite) |
| `recovery_classification` | str | `fast` / `normal` / `slow` |
| `recovery_rate`* | float | ms/min, ≥ 0 |
| `resting_hr`* | float | bpm, in (20, 220) |
| `sleep_hours`* | float | in (0, 24] |
| `mood_tags`* | str | semicolon-separated, e.g. `irritable;anxious` |

**Run:**
```bash
# on a real CSV (one command → 21 day reports + 3 summaries)
python tools/run_pilot.py --csv data/pilot/real.csv --out .workbuddy/pilot_reports

# or generate a synthetic sample and run it (for testing the pipeline)
python tools/run_pilot.py --sample --out .workbuddy/pilot_reports
```

A fillable template lives at `data/pilot/real_template.csv` (local only, not committed — it holds no health data). See **[ARCHITECTURE.md](/ARCHITECTURE.md)** for the full data-flow and consent template (`research/015_pilot_consent_template.md`).

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Data Sources                                                 │
│  ⌚ Wearable PPG/ECG · 📋 CSV (data/pilot/*.csv) · 🩺 Manual    │
└───────────────────────────────┬──────────────────────────────┘
                                 │  HRVFeatures (normalized)
                                 ▼
┌──────────────────────────────────────────────────────────────┐
│  HRV Engine  (src/hrv_engine.py)                              │
│  • RMSSD / SDNN age-norm baselines  (Shaffer 2017)            │
│  • Cycle-phase calibration          (Sports Medicine 2013)    │
│  • Recovery index                   (Cole 1999)                │
│  • Autonomic Age                    (Jarczok/Thayer 2019)      │
│  • Disease Risk  green/yellow/red                             │
│  • Hidden Chain Score 0–100                                    │
└───────────────────────────────┬──────────────────────────────┘
                                 │
            ┌────────────────────┴────────────────────┐
            ▼                                          ▼
┌───────────────────────────┐        ┌────────────────────────────────┐
│ tcm_theory.py              │        │ tcm_ontology.py                │
│ pure textbook, ZERO HRV   │        │ 89 patterns · 3 orthogonal axes │
│ • 5 engine axes            │        │ • 八纲/五脏六腑/六淫病因         │
│ • composite rules          │        │ • hrv_detectable ⊆ ~17         │
│ • EvidenceGrade           │        │ • verified citations (5)        │
│ • TCM_DISCLAIMER          │        └──────────────┬─────────────────┘
└─────────────┬─────────────┘                       │ family queries
               │                                    │
               ▼                                    │
┌───────────────────────────┐                       │
│ tcm_hrv_estimator.py       │◄──────────────────────┘
│ estimate_tcm() → TCMAssessment                    │
│ (primary / secondary / evidence / disclaimer)     │
└─────────────┬─────────────┘
               │  TCMAssessment
               ▼
┌───────────────────────────┐
│ tcm_report.py              │
│ build_tcm_report →         │
│  • scored axes + evidence  │
│  • related families        │
│  • MUST-SEE-CLINIC list    │
│ render_markdown            │
└─────────────┬─────────────┘
               ▼
┌───────────────────────────┐
│ tools/run_pilot.py         │
│ CSV → 21 day reports +     │
│ 3 × 7-day trend summaries  │
└───────────────────────────┘
```

---

## ⚖️ Compliance & red lines

> **本输出为【基于 HRV 的中医证候倾向性评估】，非中医诊断 / 辨证结论。**
> HRV 仅能代理四诊（望闻问切）中脉 / 神 / 整体气机之一小部分，无法替代舌象、面色、脉象等核心辨证依据。低证据等级项须显式降级，不得单独作为临床或健康决策依据。

Plain English: Hidden Chain is a **tendency-assessment** tool, not a diagnostic device. HRV proxies only a small subset of TCM differentiation points (primarily the pulse / spirit / overall qi-dynamics axis). Tongue, complexion, and classic pulse diagnosis are **not** covered and must come from a proper TCM consultation. Patterns marked "需面诊 / must-see-clinic" in the report must be confirmed in person — never self-diagnosed from HRV.

---

## 🧪 Quality gates (CI)

Every push/PR to `main` must pass four gates (` .github/workflows/ci.yml`):

1. **Syntax + smoke** — `py_compile src/*.py tests/*.py` + `tests/smoke_test.py` (imports all engines, verifies the `ScoreLevel` contract) across py3.10–3.12.
2. **Type check** — `mypy src/` (config in `pyproject.toml`).
3. **Unit tests** — `pytest tests/ --cov=src`, **coverage ≥ 80 %** on the auditable science core.
4. **Coverage gate** — `fail_under = 80` in `pyproject.toml`; `data_loader.py` / `device_adapters.py` are excluded (pandas/device I/O plumbing) so the gate stays meaningful on the algorithm.

Local mirror: `python tools/ci_status_report.py`.

---

## 📁 Project

```
src/
  hrv_engine.py            HRV dual-track + cycle calibration + recovery + risk
  hidden_chain_score.py    Scoring + Autonomic Age + Risk Alert
  tcm_theory.py            TCM theory layer (pure textbook, zero HRV)
  tcm_ontology.py          89-pattern syndrome ontology (3-axis, evidence, citations)
  tcm_hrv_estimator.py     HRV → TCMAssessment (5 axes + evidence + disclaimer)
  tcm_report.py            TCM report layer (families + must-see-clinic)
  data_loader.py           Pilot CSV loader + validator
  device_adapters.py       Huawei / Apple / OPPO parsers
research/                  15+ papers & design notes (Tier-1/2 quality standard)
design/                    Architecture vision & DTx roadmap
tools/                     run_pilot.py, ci_status_report.py, tcm_report_demo.py
tests/                     smoke + pytest suites (106 passed, ~91 % core coverage)
server.py                  Flask API — SQLite, multi-user
ARCHITECTURE.md            Detailed module map & data flow
```

---

## 📚 Research

- `research/001`–`012`: HRV meta-analyses, wearable cycle studies, NVI model, HRV norms, autonomic-age clock, disease-risk thresholds, founder N=1 oracle, vagal-tank theory, composite scores.
- `research/013_tcm_syndrome_theory.md`: TCM syndrome theory (the authority for `tcm_theory.py`).
- `research/014_tcm_syndrome_ontology.md`: the 89-pattern ontology framework (the authority for `tcm_ontology.py`).
- `research/015_pilot_consent_template.md`: pilot informed-consent template.

---

<div align="center">

### Built with ❤️ by [@soneei](https://github.com/soneei) · MIT License

[![Star](https://img.shields.io/github/stars/soneei/hidden-chain?style=social)](https://github.com/soneei/hidden-chain)

</div>
