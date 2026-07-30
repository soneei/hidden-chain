#!/usr/bin/env python3
"""
Hidden Chain — cycle calibration & ScoreLevel boundary tests
=============================================================
Backlog item (2026-07-30): supplement pytest cases for
  1. ScoreLevel exact boundaries (80/79, 60/59, 30/29) driven end-to-end
     through HiddenChainScorer.compute (not by constructing HiddenChainScore
     directly, so the int-truncation + clamping path is exercised);
  2. CyclePhase adjustment/label mapping completeness and its propagation
     into both HiddenChainScorer and DailyRegulationIndex;
  3. CycleCalibrator cross-phase independence (same rmssd, different z per
     phase) and z-score sign correctness.

Score formula under test (hidden_chain_score.HiddenChainScorer.compute):
  score = hrv_baseline*0.30 + recovery_index*0.25 + tcm_balance*0.25
          + (50 + phase_adj)*0.20     → int-truncated, clamped [0, 100]

Run:  pytest tests/test_cycle_score_boundaries.py
"""
import os
import sys

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
sys.path.insert(0, os.path.abspath(SRC))

import pytest

from hidden_chain_score import (
    CyclePhase,
    HiddenChainScorer,
    ScoreLevel,
)
from hrv_engine import (
    CycleCalibrator,
    DailyRegulationIndex,
    HRVEngine,
    HRVRecord,
    RecoveryMetrics,
    TCMMetrics,
)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _score(scorer: HiddenChainScorer, *, rmssd: float, recovery: str,
           yy: float, phase: CyclePhase):
    """Compute a HiddenChainScore with all non-boundary knobs neutralised.

    recovery_rate=None → recovery_index stays at the map value (no bonus);
    the TCM axis scores other than yin_yang_balance do not enter the formula.
    """
    return scorer.compute(
        resting_rmssd=rmssd,
        normalized_hrv=0.0,
        recovery_classification=recovery,
        recovery_rate=None,
        qi_blood=0.0,
        liver_depression=0.0,
        spleen_deficiency=0.0,
        phlegm_turbidity=0.0,
        yin_yang_balance=yy,
        phase=phase,
    )


def _record(rmssd: float, hr: float = 68.0) -> HRVRecord:
    return HRVRecord(timestamp="2026-07-30T07:00", rmssd=rmssd, sdnn=50.0,
                     hf=800.0, lf=900.0, heart_rate=hr, is_resting=True)


# ─────────────────────────────────────────────────────────────
# 1. ScoreLevel exact boundaries via HiddenChainScorer.compute
#    (LUTEAL adj=0 → phase term = 10.0, deterministic arithmetic)
# ─────────────────────────────────────────────────────────────

def test_boundary_80_is_purple():
    # 100*0.30 + 85*0.25 + 75*0.25 + 50*0.20 = 30 + 21.25 + 18.75 + 10 = 80.0
    s = _score(HiddenChainScorer(), rmssd=60, recovery="fast", yy=75,
               phase=CyclePhase.LUTEAL)
    assert s.score == 80
    assert s.level is ScoreLevel.PURPLE


def test_boundary_79_is_green():
    # yy=74 → 79.75 → int-truncated to 79 → GREEN
    s = _score(HiddenChainScorer(), rmssd=60, recovery="fast", yy=74,
               phase=CyclePhase.LUTEAL)
    assert s.score == 79
    assert s.level is ScoreLevel.GREEN


def test_boundary_60_is_green():
    # 100*0.30 + 35*0.25 + 45*0.25 + 50*0.20 = 30 + 8.75 + 11.25 + 10 = 60.0
    s = _score(HiddenChainScorer(), rmssd=60, recovery="slow", yy=45,
               phase=CyclePhase.LUTEAL)
    assert s.score == 60
    assert s.level is ScoreLevel.GREEN


def test_boundary_59_is_yellow():
    # yy=44 → 59.75 → 59 → YELLOW
    s = _score(HiddenChainScorer(), rmssd=60, recovery="slow", yy=44,
               phase=CyclePhase.LUTEAL)
    assert s.score == 59
    assert s.level is ScoreLevel.YELLOW


def test_boundary_30_is_yellow():
    # 20*0.30 + 35*0.25 + 25*0.25 + 45*0.20 = 6 + 8.75 + 6.25 + 9 = 30.0
    s = _score(HiddenChainScorer(), rmssd=20, recovery="slow", yy=25,
               phase=CyclePhase.PREMENSTRUAL)
    assert s.score == 30
    assert s.level is ScoreLevel.YELLOW


def test_boundary_29_is_red():
    # yy=21 → 6 + 8.75 + 5.25 + 9 = 29.0 → RED
    s = _score(HiddenChainScorer(), rmssd=20, recovery="slow", yy=21,
               phase=CyclePhase.PREMENSTRUAL)
    assert s.score == 29
    assert s.level is ScoreLevel.RED


def test_scorelevel_labels_and_advice_complete():
    for level in ScoreLevel:
        assert level.label, f"empty label for {level}"
        assert level.advice, f"empty advice for {level}"


# ─────────────────────────────────────────────────────────────
# 2. CyclePhase mapping completeness + propagation into scorer
# ─────────────────────────────────────────────────────────────

EXPECTED_ADJ = {
    CyclePhase.MENSTRUAL: -3,
    CyclePhase.FOLLICULAR: 5,
    CyclePhase.OVULATORY: 3,
    CyclePhase.LUTEAL: 0,
    CyclePhase.PREMENSTRUAL: -5,
}


@pytest.mark.parametrize("phase,adj", list(EXPECTED_ADJ.items()),
                         ids=[p.value for p in EXPECTED_ADJ])
def test_cycle_phase_adjustment_mapping(phase, adj):
    assert phase.adjustment == adj
    assert phase.label_cn  # every phase has a Chinese label


def test_phase_adjustment_propagates_into_score():
    """FOLLICULAR(+5) vs PREMENSTRUAL(-5): 10-point adj gap → exactly
    10*0.20 = 2 score points with all other knobs held fixed."""
    scorer = HiddenChainScorer()
    fol = _score(scorer, rmssd=45, recovery="normal", yy=60,
                 phase=CyclePhase.FOLLICULAR)
    pre = _score(scorer, rmssd=45, recovery="normal", yy=60,
                 phase=CyclePhase.PREMENSTRUAL)
    assert fol.phase_adjustment == 5
    assert pre.phase_adjustment == -5
    assert fol.score - pre.score == 2


def test_analyze_day_phase_branches():
    """HRVEngine.analyze_day routes day_of_cycle → the same CyclePhase on
    both outputs (regulation index and hidden chain score)."""
    engine = HRVEngine()
    day_to_phase = {3: CyclePhase.MENSTRUAL, 10: CyclePhase.FOLLICULAR,
                    16: CyclePhase.OVULATORY, 20: CyclePhase.LUTEAL,
                    27: CyclePhase.PREMENSTRUAL}
    for day, phase in day_to_phase.items():
        index, hcs = engine.analyze_day(_record(42.0), day_of_cycle=day)
        assert index.phase is phase
        assert hcs.phase is phase


def test_dri_phase_adjustment_branch():
    """DailyRegulationIndex applies its own phase table: follicular(+5) vs
    premenstrual(-5) → 10-point spread on otherwise identical inputs."""
    tcm = TCMMetrics.from_hrv(45.0, 0.0, None)
    recovery = RecoveryMetrics(delta_hrv=0.0, recovery_time_min=10.0,
                               recovery_rate=None, classification="normal")
    fol = DailyRegulationIndex.compute(0.0, 45.0, tcm, recovery,
                                       CyclePhase.FOLLICULAR)
    pre = DailyRegulationIndex.compute(0.0, 45.0, tcm, recovery,
                                       CyclePhase.PREMENSTRUAL)
    assert fol.score - pre.score == 10


# ─────────────────────────────────────────────────────────────
# 3. CycleCalibrator — cross-phase independence & z-score sign
# ─────────────────────────────────────────────────────────────

def test_calibrator_phases_are_independent():
    """Same rmssd must normalise differently against different phase
    baselines: menstrual baseline low (30±) vs follicular high (50±)."""
    cal = CycleCalibrator()
    records = [_record(28), _record(32),          # days 2,3  → menstrual
               _record(48), _record(52)]          # days 9,10 → follicular
    cal.fit(records, [2, 3, 9, 10])

    assert set(cal.phase_stats) == {"menstrual", "follicular"}
    z_men = cal.normalize(40.0, CyclePhase.MENSTRUAL)
    z_fol = cal.normalize(40.0, CyclePhase.FOLLICULAR)
    assert z_men > 0    # 40 is above the menstrual mean (30)
    assert z_fol < 0    # 40 is below the follicular mean (50)
    assert z_men != z_fol


def test_calibrator_zscore_sign_and_zero():
    cal = CycleCalibrator()
    cal.fit([_record(38), _record(42)], [9, 10])   # follicular mean=40
    assert cal.normalize(40.0, CyclePhase.FOLLICULAR) == pytest.approx(0.0)
    assert cal.normalize(46.0, CyclePhase.FOLLICULAR) > 0
    assert cal.normalize(34.0, CyclePhase.FOLLICULAR) < 0


def test_engine_fitted_normalization_feeds_score():
    """After fit, an above-baseline rmssd should never score lower than the
    identical engine seeing the same value as its baseline mean."""
    records = [_record(38), _record(42)]
    days = [9, 10]

    eng = HRVEngine()
    eng.fit_calibrator(records, days)
    _, hcs_high = eng.analyze_day(_record(50.0), day_of_cycle=10)

    eng2 = HRVEngine()
    eng2.fit_calibrator(records, days)
    _, hcs_mid = eng2.analyze_day(_record(40.0), day_of_cycle=10)

    assert hcs_high.score >= hcs_mid.score
