# Track A Direction 5: Disease risk thresholds — quantifying the "red zone"

## Primary sources

**Jarczok, Koenig, Thayer et al. (2019)** — *J Clin Med*. N=9,550 working adults.
**Goldenberg et al. (2019)** — *J Am Heart Assoc*. HRV-DETECT study, N=1,043.
**MESA Study (2016)** — *J Electrocardiol*. N=1,175 CVD-free participants.
**Framingham Heart Study (Tsuji et al.)** — 2,501 participants, 4-year follow-up.

## The core question

At what HRV threshold does a "bad day" become a "disease risk signal"? This is what Hidden Chain needs for its red alert system.

## Jarczok 2019: The answer we're looking for

**N=9,550** working adults, **19 study sites**, co-authored by **Thayer** (NVI model creator).

> Daytime RMSSD < **25 ± 4 ms** → elevated risk across ALL major cardiovascular risk factors
> Nighttime RMSSD < **29 ± 4 ms** → elevated risk

| Risk factor | OR at RMSSD < 25ms (daytime) |
|---|---|
| Inflammation (hsCRP elevated) | 1.5 |
| Hyperglycemia | 2.2 |
| Hyperlipidemia | 1.8 |
| Hypertension | 3.5 |
| Any 2+ risk factors | 2.8 |

**This is THAYER's own research.** The same person who created the NVI model (our Paper 003) co-authored this threshold paper. The cut point of RMSSD < 25ms for disease risk is as authoritative as it gets.

## MESA study — borderline abnormal thresholds (age 45+)

| | SDNN (ms) | RMSSD (ms) |
|---|---|---|
| Borderline abnormal (<5th percentile) | ~12 | ~8 |
| Abnormal (<2nd percentile) | ~8 | ~5 |

Note: These are 10-second ECG values, much lower than 5-min or overnight averages. Not directly comparable to Jarczok.

## Framingham — SDNN risk

- **1 SD below mean SDNN** → HR 1.38 for all-cause mortality (p=0.019)
- Lowest LF tertile → HR 1.70 (p=0.001) — strongest single predictor
- Lower SDNN → Higher rate of heart disease (12.40 vs 2.06 events)

## HRV-DETECT (Goldenberg 2019)

- N=1,043, prospective international
- Low HRV → **2x likelihood of myocardial ischemia** (OR 2.00, p=0.01)
- Adding HRV to traditional risk factors improved prediction significantly

## Hidden Chain → Implementation

### Three-tier alert system

| Zone | RMSSD (daytime) vs age norm | Meaning | Action |
|---|---|---|---|
| Green | ≥ age-expected range | Normal | Continue tracking |
| Yellow | 1 SD below age norm | Warning | Suggest lifestyle check |
| Red | < 25ms (Jarczok threshold) OR 2+ consecutive days below yellow | Disease risk elevated | Recommend rest, check-in with doctor |

### Specific thresholds for Hidden Chain Score

| User type | Green | Yellow | Red |
|---|---|---|---|
| 20s | RMSSD > 45 | 25-45 | < 25 |
| 30s | RMSSD > 38 | 25-38 | < 25 |
| 40s | RMSSD > 30 | 25-30 | < 25 |
| 50s+ | RMSSD > 25 | 20-25 | < 20 |

### Consecutive-day rule (proposed)

> If a user's RMSSD stays in Yellow zone for **3+ consecutive days**: raise to Red-level recommendation ("sustained low recovery — consider reducing load")
>
> If a user's RMSSD stays below 25ms (Jarczok threshold) for **5+ days in a 7-day window**: flag for medical consultation

## Summary: Hidden Chain's disease risk layer

1. **Daily RMSSD** → compare to age norm → green/yellow/red
2. **Consecutive bad days** → sustained low signal → medical flag
3. **Combined with TCM warning** → qi-blood deficiency + spleen deficiency + HRV in red zone → strongest possible flag

**This is what makes Hidden Chain preventive, not just descriptive.**

**Journal tier**: Jarczok = Q2 (JCM). But co-authored by Thayer — quality > journal.
MESA = Q2. HRV-DETECT = Q1 (JAHA).
**Last verified**: 2019 (Jarczok), 2019 (Goldenberg)
