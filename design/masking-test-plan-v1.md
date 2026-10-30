# Retrospective Masking Test — Pre-registration v1

> **This document is the pre-registration.** Thresholds, seeds and the primary
> strategy are frozen here *before* real data lands. Changing any of them
> requires a v2 that states the v1 result and why it was abandoned.
> That constraint is the product — it is what separates "the model predicted"
> from "I explained it afterwards".

**Question under test:** does a generative direction `g` exist in this system —
i.e. can the latent autonomic state *generate* observations that were never
shown to it?

Formal framing: the world-model triple is `z_{t+1} = f(z_t, a)`, `ô = g(z)`,
`z ← q(z, a, o)`. This test isolates **`g`**. Note that `g` is a *function*, not
a data product: its absence is an architecture gap, independent of how many
users exist. N=1 with dense longitudinal sampling is a legitimate design here
(the constraint on an intra-individual dynamical model is time-points, not
people).

---

## 1. Primary outcome (exactly one)

| | |
|---|---|
| Target | `hrv_rmssd` — nightly HRV (RMSSD), daily mean |
| Primary strategy | **block3** (3-day contiguous block masked) |
| Primary metric | **MAE** over all masked days × 30 seeds |
| Secondary | direction-of-change hit rate (sign of day-over-day delta) |

HRV is chosen because it is the densest channel, is measured rather than
self-reported, and is the engine's own autonomic proxy. One target only —
a second target would let a bad result be quietly replaced by a good one.

## 2. Data gates

| Gate | Threshold | Rationale |
|---|---|---|
| Minimum days | **60** (hard, enforced in `run_masking_test.py`) | below this, block strategies have no room |
| Target coverage | **≥70%** of days non-null | MNAR bias becomes dominant otherwise |
| Full protocol | ≥90 days | only then is S3 rolling-7 powered |

## 3. Masking strategies

| ID | Strategy | What it actually tests |
|---|---|---|
| S1 | point masking (scattered single days) | interpolation |
| S2 | block masking, k ∈ {1, 3, 7} | interpolation under contiguous absence |
| S3 | **rolling 7-day lookahead** | **prediction — the only true world-model test** |

Seeds 1–30 are hard-coded (`DEFAULT_SEEDS`). Mask positions are a deterministic
function of (strategy, k, seed).

## 4. Baselines the model must beat

| ID | Baseline | Description |
|---|---|---|
| B1a | persistence | tomorrow = last visible value |
| B1b | mean7 | mean of last 7 visible days |
| B2 | phase_mean | historical mean at the same cycle day |
| B3 | rules_prior | mean7 **+ TCM rule adjustments** (frozen coefficients in `data/rules_prior.json`) |
| M | ridge | lag + phase + rule-hit features, L2 |

**B3 is not a strawman.** It is the existing rule engine *demoted to a prior*:
the rules stop issuing conclusions and instead bias a numeric forecast, with
their coefficients frozen in JSON. In M, rule hits enter as *features*, so data
sets the magnitude while the rules supply the structure. That is the concrete
meaning of "the engine is demoted to a prior".

If B3 wins, the finding is not a failure — it is *"the hand-written rules are
already this good; the learned layer adds nothing"*, which is a valuable and
independently publishable result.

## 5. Verdict rule (frozen)

On the primary strategy (block3):

| Condition | Verdict |
|---|---|
| MAE reduction vs **best** baseline ≥ **10%** AND direction accuracy ≥ **60%** | **g-exists** |
| MAE reduction < 10%, or direction accuracy < 60% | **g-not-established** |
| M fails to beat **B1a** (persistence) | **g-absent** — no generative signal at all |

Beating the *best* baseline, not a chosen one, is deliberate: it removes the
freedom to pick a weak comparator.

## 6. Anti-self-deception protocol

1. **Data freeze** — hash the daily CSV; any re-export invalidates the run.
2. **Holdout** — the final 20% of days is untouchable until the verdict is written.
3. **No target switching** — `hrv_rmssd` cannot be changed after the fact.
4. **No threshold editing** — a new threshold means v2, which must quote v1's result.
5. **Model escalation ladder** (only upward, only on failure, each step logged):
   1. ridge / lagged linear (readable coefficients)
   2. gradient-boosted trees with lag + phase + intervention dummies
   3. small linear state-space / Neural ODE (<100k params, CPU-trainable)
   4. time-series foundation model (Chronos-class), zero-shot or adapter
   — *only permitted if 1–3 all fail to beat B3*.
   Escalate when and only when tier N's 3-day block MAE reduction is <10%.
   No skipping tiers. No tuning on the holdout.

## 7. Cost discipline (why no foundation model, and where LoRA actually belongs)

Training a base model is not on the table. Neither is LoRA *for `g`*:

- `g` is low-dimensional numeric sequence prediction — thousands to ~100k
  parameters, no pretrained base to adapt. LoRA has nothing to attach to.
- An LLM regressing numeric series typically loses to lagged linear/tree models
  on this class of task.
- It would violate the project's own architectural rule: *the LLM is the
  detective that proposes suspects, not the judge that sentences.* A numeric
  forecast emitted by an LLM cannot be audited by the causal layer, and cannot
  be run counterfactually.

LoRA belongs on the **language/expression layer** only (terminology, report
voice), not on the dynamics layer.

## 8. Precision declaration (must ship with any result)

- Device HRV is a **vendor estimate** (RMSSD/SDNN), not raw R–R intervals.
  Cross-device and cross-firmware comparability is not guaranteed.
- Missingness is **not random** — unworn days skew toward bad days (MNAR), which
  biases the model optimistic. Every report states the missing rate next to MAE.
- **N=1**: results are valid for this individual's intra-individual dynamics.
  The claim is "this architecture predicts", *not* "a general physiological law
  was discovered".

## 9. Status

Harness is implemented and green on synthetic data (16 unit tests;
end-to-end CLI reports `g-exists` on planted dynamics, which is the expected
result and validates the plumbing, **not** the hypothesis). Real-data run
pending device export — see `docs/n1-data-intake.md`.
