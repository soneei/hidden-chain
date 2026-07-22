# Paper 002: Wearable HRV across the menstrual cycle

**Title**: Wearable-Derived Heart Rate Variability Across the Menstrual Cycle, Hormonal Contraceptive Use, and Reproductive Life Stages in Females: A Living Systematic Review
**Authors**: Eline de Jager, Brian Caulfield, Evgenia Angelidi, Brian MacNamee, Sinead Holden
**Journal**: Sports Medicine (IF ~13.0)
**Year**: 2025 (published Jan 2026) | **DOI**: 10.1007/s40279-025-02388-y

## Why this paper matters

**The most relevant paper for Hidden Chain.** It's the first systematic review that exclusively looks at HRV measured by **wearable devices** (not lab ECG). 16 studies, N=19,322 women. Published in a Q1 journal with an IF of 13 — this is the paper we cite when anyone questions whether consumer wearables can detect cycle-related HRV changes.

## Key findings

### HRV naturally drops across the cycle — loud and clear

| Phase comparison | HRV difference | Measurement |
|---|---|---|
| Cycle start vs end | **3-9% lower RMSSD (时域指标)** | Consistent across 8/10 studies |
| Day 5 peak vs Day 21 trough | **+3.6ms → -3.2ms from mean** | Jasinski et al. |
| Early cycle vs late cycle | **-5.96ms RMSSD drop** | Alzueta et al. |
| Follicular (卵泡期) vs luteal (黄体期) | Significantly lower in luteal (p<0.001) | Pearson et al. |

### Hormonal contraceptive effects

- CHC (combined hormonal contraceptive, 复方激素避孕药) users have consistently **lower HRV** than naturally cycling women
- The drop is most pronounced in the **late cycle** (late luteal phase)

### Across the lifespan

- HRV declines after menopause (绝经后), accelerating with age
- Middle-aged women (42-56) have significantly lower RMSSD than young women (18-35)

### Estrogen (雌激素) & progesterone (孕酮) → HRV pathway

- Blood estrogen: **negatively correlated** with RMSSD (β=-0.05, p<0.001) during follicular phase
- Progesterone: significantly correlated with HF power (β=1.03, p≤0.011)

## Method quality notes

- Only 7/15 studies used biochemical verification (激素检测) of cycle phase — the rest relied on calendar counting
- HRV measurement protocols are wildly inconsistent across studies (duration, timing, posture, device type)
- The heterogeneity is so large that a formal meta-analysis **was not possible** — this is both a limitation and an opportunity for Hidden Chain to standardize

## Relevance to Hidden Chain

1. **Cycle calibration is mandatory.** The 3-9% RMSSD drop is a **physiological signal, not noise.** If we don't calibrate for cycle phase, we will flag normal luteal-phase HRV dips as "stress."
2. **Our CyclePhase 5-stage model is validated.** The peak-to-trough pattern (Day 5 highest, Day 21 lowest) maps directly to our FOLLICULAR → PREMENSTRUAL calibration.
3. **Contraceptive users need a separate calibration.** Hidden Chain v1.0 should have a flag: `contraceptive=yes/no` with different baseline expectations.
4. **We need to log which device.** Huawei Band 6 Pro was one of the validated devices in this review — our data source checks out.

**Last verified**: 2026-01 (this is a *living* review, updating monthly)
**Journal tier**: Q1 (IF 13.0, top 3% in sports medicine)

---

## 中文全文摘要 (Chinese Full-Text Summary)

### 背景
心率变异性（HRV）反映自主神经系统功能，现可通过可穿戴技术在现实环境中持续监测。但卵巢激素对HRV的影响仍不清楚。

### 研究设计
实时系统综述（Living systematic review）。检索PubMed、Web of Science、IEEE Xplore、SPORTDiscus、Embase，从建库至2025年12月。纳入16项研究，总计**19,322名女性参与者**。

### 核心发现

**1. 自然月经女性：HRV在周期中波动3–9%**
- 卵泡期（周期前半段）：HRV较高（副交感神经优势）
- 黄体期（周期后半段）：HRV降低3–9%
- Jasinski (2024)：第5天RMSSD最高（+3.6ms），第21天最低（−3.2ms）
- Sims (2021)：RMSSD从~70ms（周期前1/4）降至~64ms以下（周期后1/4）

**2. 口服避孕药使用者：HRV模式完全不同**
- CHC（联合激素避孕药）使用者的RMSSD振幅显著低于自然月经女性：**-0.51ms vs +4.65ms**（p < 0.001）
- 在活性药丸服用期间HRV下降，撤退性出血期间回升

**3. 绝经后：HRV显著下降**
- pNN50：绝经前 **4.3** → 早期绝经后 **1.6** → 晚期绝经后 **2.4**（p = 0.001，降幅63%）
- 中年女性（42–56岁）RMSSD显著低于年轻女性（18–35岁）：p < 0.01

### 对Hidden Chain的意义
1. 周期校准必须做——不能把黄体期的正常HRV下降误判为"压力"
2. 口服避孕药用户需要单独的校准曲线
3. 绝经后女性的HRV基线需要上调（天然HRV更低不代表"不健康"）
4. 我们的Huawei手表数据通道在论文中得到验证——这篇证明可穿戴设备测HRV可行

## Key data tables (from full text)

### RMSSD across menstrual cycle (natural menstruating)
| Study | Finding | Magnitude |
|---|---|---|
| Jasinski et al. 2024 | Day 5 peak, Day 21 trough | +3.6 / −3.2 ms |
| Sims et al. 2021 | Q1 → Q4 decline | ~70 → <64 ms |
| Alzueta et al. 2022 | Late cycle lower | −5.96 ms |
| **Overall** | **Follicular → Luteal** | **3–9% decline** |

### Postmenopause: pNN50 collapse
| Group | pNN50 |
|---|---|
| Premenopausal | 4.3 ± 6.2 |
| Early postmenopause (<5yr) | 1.6 ± 1.7 |
| Late postmenopause (>5yr) | 2.4 ± 2.5 |
**p = 0.001 (63% drop from pre- to postmenopause)**
