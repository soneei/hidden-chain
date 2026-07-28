#!/usr/bin/env python3
"""
Hidden Chain — pytest suite for hrv_engine (gate 3, core algorithm)
====================================================================
Behavioral tests for the HRV analysis engine: recovery metrics, cycle
calibration, TCM mapping, daily regulation index, and the top-level
HRVEngine orchestration. This is the auditable science core, so it is
held to the coverage gate; the pandas/device I/O adapters are excluded
(see pyproject.toml [tool.coverage.run] omit).

Run:  pytest tests/test_hrv_engine.py
"""
import os
import sys

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
sys.path.insert(0, os.path.abspath(SRC))

import pytest

from hrv_engine import (
    HRVRecord,
    RecoveryMetrics,
    CycleCalibrator,
    CyclePhase,
    TCMMetrics,
    DailyRegulationIndex,
    HRVEngine,
)
from hidden_chain_score import ScoreLevel


# ─────────────────────────────────────────────────────────────
# HRVRecord
# ─────────────────────────────────────────────────────────────
def test_hrv_record_lf_hf_ratio():
    rec = HRVRecord(timestamp="t", rmssd=40, sdnn=50, hf=10, lf=20, heart_rate=60)
    assert rec.lf_hf_ratio == 2.0


def test_hrv_record_lf_hf_ratio_zero_hf_is_inf():
    rec = HRVRecord(timestamp="t", rmssd=40, sdnn=50, hf=0, lf=20, heart_rate=60)
    assert rec.lf_hf_ratio == float("inf")


# ─────────────────────────────────────────────────────────────
# RecoveryMetrics.compute
# ─────────────────────────────────────────────────────────────
def test_recovery_fast():
    rm = RecoveryMetrics.compute(pre_hrv=40, post_hrv_values=[39],
                                  baseline_hrv=40, timestamps_min=[2])
    assert rm.classification == "fast"
    assert rm.recovery_time_min == 2
    assert rm.recovery_rate > 0


def test_recovery_normal_no_recovery_found():
    # No post value returns near baseline → falls back to last timestamp.
    rm = RecoveryMetrics.compute(pre_hrv=40, post_hrv_values=[35],
                                  baseline_hrv=40, timestamps_min=[10])
    assert rm.classification == "normal"
    assert rm.recovery_time_min == 10
    assert rm.recovery_rate == 0


def test_recovery_slow():
    rm = RecoveryMetrics.compute(pre_hrv=40, post_hrv_values=[35],
                                  baseline_hrv=40, timestamps_min=[30])
    assert rm.classification == "slow"


def test_recovery_empty_post_list():
    rm = RecoveryMetrics.compute(pre_hrv=40, post_hrv_values=[],
                                  baseline_hrv=40, timestamps_min=[8])
    assert rm.delta_hrv == 0
    assert rm.classification == "normal"  # 8 < 20


# ─────────────────────────────────────────────────────────────
# CycleCalibrator
# ─────────────────────────────────────────────────────────────
def test_cycle_calibrator_fit_and_normalize():
    recs = [HRVRecord(timestamp=f"d{i}", rmssd=40 + i, sdnn=50, hf=10, lf=20, heart_rate=60)
            for i in range(10)]
    days = list(range(1, 11))  # all follicular (days 6-14)
    cal = CycleCalibrator()
    cal.fit(recs, days)
    # A follicular reading of 45 vs mean ~44.5 → small positive z.
    z = cal.normalize(45, CyclePhase.FOLLICULAR)
    assert isinstance(z, float)


def test_cycle_calibrator_normalize_unfitted_returns_zero():
    cal = CycleCalibrator()
    assert cal.normalize(45, CyclePhase.FOLLICULAR) == 0.0


def test_cycle_calibrator_normalize_single_sample_returns_zero():
    rec = HRVRecord(timestamp="x", rmssd=42, sdnn=50, hf=10, lf=20, heart_rate=60)
    cal = CycleCalibrator()
    cal.fit([rec], [7])  # count < 2 → std default 1.0 but count check returns 0.0
    assert cal.normalize(42, CyclePhase.FOLLICULAR) == 0.0


# ─────────────────────────────────────────────────────────────
# TCMMetrics.from_hrv
# ─────────────────────────────────────────────────────────────
def _recovery(classification, rate=2.0) -> RecoveryMetrics:
    return RecoveryMetrics(delta_hrv=0, recovery_time_min=10,
                            recovery_rate=rate, classification=classification)


def test_tcm_high_hrv_no_deficiency():
    # RMSSD 60 → qi_blood_deficiency should floor at 0.
    tcm = TCMMetrics.from_hrv(resting_hrv=60, normalized_hrv=0.0,
                              recovery=_recovery("fast", rate=5.0))
    assert tcm.qi_blood_deficiency == 0.0
    assert 0 <= tcm.yin_yang_balance <= 100


def test_tcm_zero_hrv_high_qi_deficiency():
    tcm = TCMMetrics.from_hrv(resting_hrv=0, normalized_hrv=0.0,
                              recovery=_recovery("slow", rate=0.0))
    assert tcm.qi_blood_deficiency >= 90


def test_tcm_slow_recovery_drives_liver_and_spleen():
    tcm = TCMMetrics.from_hrv(resting_hrv=30, normalized_hrv=0.0,
                              recovery=_recovery("slow", rate=0.0))
    # Slow recovery must push both liver qi stagnation and spleen deficiency up.
    assert tcm.liver_depression >= 65
    assert tcm.spleen_deficiency >= 65


def test_tcm_phlegm_from_normalized_deviation():
    # Large |normalized_hrv| → phlegm turbidity rises.
    tcm = TCMMetrics.from_hrv(resting_hrv=45, normalized_hrv=3.0,
                              recovery=_recovery("normal", rate=3.0))
    assert tcm.phlegm_turbidity > 0


def test_tcm_mood_tags_affect_scores():
    base = TCMMetrics.from_hrv(resting_hrv=35, normalized_hrv=0.2,
                               recovery=_recovery("normal", rate=3.0))
    with_mood = TCMMetrics.from_hrv(resting_hrv=35, normalized_hrv=0.2,
                                    recovery=_recovery("normal", rate=3.0),
                                    mood_tags=["irritable", "anxious", "exhausted", "brain_fog"])
    # Irritable/anxious should lift liver; exhausted/brain_fog lift spleen + phlegm.
    assert with_mood.liver_depression >= base.liver_depression
    assert with_mood.spleen_deficiency >= base.spleen_deficiency


def test_tcm_resting_hr_bonus():
    low = TCMMetrics.from_hrv(resting_hrv=40, normalized_hrv=0.0,
                              recovery=_recovery("fast", rate=5.0))
    high = TCMMetrics.from_hrv(resting_hrv=40, normalized_hrv=0.0,
                               recovery=_recovery("fast", rate=5.0), resting_hr=85)
    assert high.qi_blood_deficiency > low.qi_blood_deficiency


def test_tcm_all_scores_in_range():
    tcm = TCMMetrics.from_hrv(resting_hrv=42.5, normalized_hrv=1.5,
                              recovery=_recovery("normal", rate=2.5),
                              resting_hr=72, sleep_hours=5,
                              mood_tags=["irritable", "exhausted"])
    for v in (tcm.qi_blood_deficiency, tcm.liver_depression,
              tcm.spleen_deficiency, tcm.phlegm_turbidity, tcm.yin_yang_balance):
        assert 0 <= v <= 100


# ─────────────────────────────────────────────────────────────
# DailyRegulationIndex.compute
# ─────────────────────────────────────────────────────────────
def test_dri_high_is_purple():
    tcm = TCMMetrics.from_hrv(resting_hrv=60, normalized_hrv=2.0,
                             recovery=_recovery("fast", rate=6.0))
    rec = _recovery("fast", rate=6.0)
    dri = DailyRegulationIndex.compute(normalized_hrv=3.0, resting_hrv=60,
                                       tcm=tcm, recovery=rec, phase=CyclePhase.FOLLICULAR)
    assert dri.level == "purple"
    assert 0 <= dri.score <= 100


def test_dri_low_is_red():
    tcm = TCMMetrics.from_hrv(resting_hrv=20, normalized_hrv=-3.0,
                             recovery=_recovery("slow", rate=0.0))
    rec = _recovery("slow", rate=0.0)
    dri = DailyRegulationIndex.compute(normalized_hrv=-4.0, resting_hrv=20,
                                       tcm=tcm, recovery=rec, phase=CyclePhase.PREMENSTRUAL)
    assert dri.level == "red"


def test_dri_fitted_flow_returns_index_and_score():
    # End-to-end sanity through the orchestrator.
    engine = HRVEngine()
    rec = HRVRecord(timestamp="2026-07-21T07:00", rmssd=42.5, sdnn=52,
                    hf=10, lf=20, heart_rate=62, is_resting=True)
    idx, hcs = engine.analyze_day(rec, day_of_cycle=8)
    assert isinstance(idx, DailyRegulationIndex)
    assert isinstance(hcs, object)
    assert 0 <= idx.score <= 100
    assert hcs.level in list(ScoreLevel)


# ─────────────────────────────────────────────────────────────
# HRVEngine orchestration
# ─────────────────────────────────────────────────────────────
def test_engine_fit_length_mismatch_raises():
    engine = HRVEngine()
    recs = [HRVRecord(timestamp="t", rmssd=40, sdnn=50, hf=10, lf=20, heart_rate=60)]
    with pytest.raises(ValueError):
        engine.fit_calibrator(recs, [1, 2])


def test_engine_analyze_day_unfitted_normalizes_zero():
    engine = HRVEngine()
    rec = HRVRecord(timestamp="t", rmssd=42.5, sdnn=52, hf=10, lf=20, heart_rate=62)
    idx, hcs = engine.analyze_day(rec, day_of_cycle=8)
    assert engine.score_history == [hcs.score]


def test_engine_analyze_day_with_fit_uses_calibrator():
    engine = HRVEngine()
    recs = [HRVRecord(timestamp=f"d{i}", rmssd=40 + i, sdnn=50, hf=10, lf=20, heart_rate=60)
            for i in range(10)]
    engine.fit_calibrator(recs, list(range(1, 11)))
    assert engine._is_fitted is True
    rec = HRVRecord(timestamp="t", rmssd=45, sdnn=52, hf=10, lf=20, heart_rate=62)
    idx, hcs = engine.analyze_day(rec, day_of_cycle=8)
    assert 0 <= idx.score <= 100


def test_engine_summary_text_contains_phase():
    engine = HRVEngine()
    rec = HRVRecord(timestamp="t", rmssd=42.5, sdnn=52, hf=10, lf=20, heart_rate=62)
    idx, _ = engine.analyze_day(rec, day_of_cycle=8)
    text = engine.summary_text(idx)
    assert "Follicular" in text
    assert "Regulation Index" in text
