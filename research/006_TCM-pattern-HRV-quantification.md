# Track A Direction 3: TCM pattern differentiation ↔ HRV quantification

> **[archived — primary sources unverifiable, evidence superseded by research/016]**
> Formerly cited as primary sources (now removed as unverifiable): **Olivera-Toro et al. 2019** (J Acupuncture & Meridian Studies), **NRICM Taiwan menopause study 2010**, **Yang et al. 2008** (Medical Research Journal). Directional conclusions below are retained for record only; do **not** cite the three sources. Verified real-person evidence for the 5-axis mapping now lives in `research/016_hrv_tcm_chinese_evidence.md`; the Shaffer 2017 norms anchor is retained in `research/004`.

## Core finding: TCM patterns have measurable HRV signatures

The three previously-cited studies (now unverifiable) claimed that TCM diagnoses (辨证) produce distinct, quantifiable autonomic profiles measurable by HRV. This is the intended bridge between our Thayer NVI model and TCM diagnostics — directional claim retained, sources not.

## 1. Spleen-Qi Deficiency (脾虚)

| Metric | Control | Spleen Def | Change |
|---|---|---|---|
| SDNN (ms) | baseline | 17% lower | ↓ |
| HF power (vagal) | baseline | 14% lower | ↓ |
| LF power | baseline | 16% higher | ↑ |
| LF/HF ratio | baseline | 22% higher | ↑ |
| Heart rate | baseline | 9.6% higher | ↑ |
| Fatigue score | baseline | 21% higher | ↑ |
| Concentration | baseline | 16.2% lower | ↓ |

**Mechanism**: Spleen-Qi deficiency → low vagal tone (迷走神经张力降低) → decreased peristalsis, increased fatigue, reduced attention.

**Hidden Chain link**: Directly supports our spleen_score mapping: low vagal (HF/RMSSD) + high fatigue = spleen deficiency.

## 2. Liver Depression × HRV (肝郁气滞/肝郁化火)

| Pattern | HRV signature |
|---|---|
| Liver depression + fire transformation (肝郁化火) | HF ↓, LF↑, LF/HF ↑, heart rate ↑ |
| Liver depression + phlegm obstruction (肝郁痰阻) | Most severe vagal ↓ of all patterns |
| Liver depression + qi stagnation (肝郁气滞) | Time-domain ↓↓, vagal ↓↓ |

**Key finding**: Liver depression patterns are the MOST disruptive to vagal function — even more than spleen or heart patterns. This matches the TCM theory: 肝主疏泄, when the liver's "free flow" is blocked, autonomic regulation collapses.

## 3. Heart-Blood Deficiency (心血虚)

- Sympathetic ↑, parasympathetic ↓
- Correlates with palpitations (心悸), insomnia
- HRV time-domain (RR) significantly negatively correlated with symptom scores

## 4. Quantitative mapping table for Hidden Chain

| TCM pattern | HRV biomarker | Key threshold | Subjective symptom |
|---|---|---|---|
| Qi-blood deficiency (气血不足) | RMSSD < 35ms | Shaffer 2017, <1SD from age norm | Fatigue, pale tongue |
| Liver depression (肝郁) | Recovery slow > 30min | RMSSD fails to rise after stress | Irritable, PMS |
| Spleen deficiency (脾虚) | SDNN ↓ + LF/HF ↑ | SDNN < age-expected by 17% | Bloating, brain fog |
| Phlegm turbidity (痰气互结) | Cycle-corrected HRV still abnormal | After phase normalization remains >1SD | Unrefreshing sleep |

## Relevance to Hidden Chain

1. **Validation**: The TCM↔HRV mapping direction is supported by multiple studies (sources now unverifiable — see archived note above).
2. **Threshold refinement**: Spleen deficiency → SDNN 17% lower than age norm (per archived source; treat as directional, not calibrated).
3. **Liver depression → recovery slowness**: Maps to our recovery_metrics — "slow" recovery classification has TCM backing.
4. **Phlegm turbidity (痰气互结)**: Only after cycle calibration (排除周期影响), if HRV is still abnormal. Already our design.

> **Superseded**: For verified real-person HRV↔TCM evidence with sample sizes and ethics approval, use `research/016_hrv_tcm_chinese_evidence.md`. The absolute thresholds above remain direction-only until re-calibrated against a health-population norm.
