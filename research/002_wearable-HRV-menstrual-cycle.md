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
