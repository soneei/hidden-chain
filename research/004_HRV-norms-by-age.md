# Track A Direction 1: HRV normative values by age

## Primary source: Shaffer & Ginsberg (2017)

**Title**: An Overview of Heart Rate Variability Metrics and Norms
**Journal**: Frontiers in Public Health
**Year**: 2017 | **Citations**: 7,182
**DOI**: 10.3389/fpubh.2017.00258

### Why this paper matters

The MOST cited paper in all of HRV research. If Hidden Chain needs one paper to justify its age-based baseline values, this is it. Synthesizes data from multiple large-cohort studies totaling tens of thousands of participants.

## Key normative data

### Short-term HRV (5 min, healthy adults ≥ 40 years)
**Nunan et al. (2010) meta-analysis — N=21,438**

| Metric | Mean ± SD | Normal range |
|---|---|---|
| SDNN (ms) | 50 ± 16 | 32–93 |
| RMSSD (ms) | 42 ± 15 | 19–75 |
| LF (ms²) | 519 ± 291 | 193–1,009 |
| HF (ms²) | 657 ± 777 | 83–3,630 |
| LF/HF | 2.8 ± 2.6 | 1.1–11.6 |

### 24h HRV by age (Umetani et al. 1998 — N=260, age 10–99)

| Age decade | SDNN trend | Key note |
|---|---|---|
| 10–19 | Highest | Peak HRV in adolescence |
| 20–29 | Significant drop | **Sharpest decline between decade 2→3** |
| 30–39 | Gradual decline | Night-time HRV drops most |
| 40–49 | Continued decline | |
| 50–59 | Moderate decline | Gender differences disappear after 50 |
| 60–69 | Low | Below mortality risk threshold at 65 |
| 70+ | Lowest | Critical zone |

### Age 25–41 (Aeschbacher et al. 2015 — N=2,079)

| | Male | Female |
|---|---|---|
| SDNN | 160 ± 40 ms | 147 ± 36 ms |
| LF | 1,337 ms² | 884 ms² |
| HF | 289 ms² | 274 ms² |

### Age 40–100 (Almeida-Santos et al. 2016 — N=1,743)

- SDNN, SDANN, SDNNI: **linear decline** with age
- RMSSD and pNN50: **U-shaped** — decline 40-60, rise after 70 (survival bias?)
- All metrics: men > women

## The HRV→age curve (synthesized)

```
Age    Expected RMSSD (ms)   Expected SDNN (ms)
---    -------------------   ------------------
20s    50-60                 55-70
30s    42-50                 48-55
40s    35-42                 40-48
50s    25-35                 30-40
60s+   20-30                 25-35
```

## Relevance to Hidden Chain — Autonomic Age

The formula: if a 34-year-old woman has RMSSD = 45ms, her autonomic age ≈ 33 (normal for 30s). If RMSSD = 25ms, autonomic age ≈ 50+ (premature aging).

**Implementation path**:
1. Fit a decay curve to the normative data (linear or exponential)
2. Map current user's HRV to the curve → estimate autonomic age
3. Track trajectory over months → is autonomic age going up or down?
4. Cross-reference with cycle phase to avoid menstrual bias

## Caveats (from Shaffer & Ginsberg)

- 24h, short-term, and ultra-short-term norms are **NOT interchangeable**
- Measurement context matters: posture (仰卧 vs 坐), breathing (自由呼吸 vs 节律呼吸), device (ECG vs PPG)
- Huawei watch gives PPG-based ultra-short-term RMSSD → need conversion factor
- "Supplement published norms with findings from your own population"

## Next step

Use these baseline values to add a simple `estimated_autonomic_age` field to the Hidden Chain Score. Start conservative — compute from RMSSD, flag when > 1 SD below age norm.

**Journal tier**: Q1 (Frontiers, highly cited, 7,182 citations)
**Last verified**: 2025 (remains the standard reference)
