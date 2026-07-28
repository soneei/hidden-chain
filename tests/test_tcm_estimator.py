#!/usr/bin/env python3
"""
Hidden Chain — pytest suite for the TCM estimator (research/013)
================================================================
Verifies the theory/estimator separation:
  - five primary scores preserved (back-compat)
  - primary_syndrome / secondary_syndromes (composite patterns)
  - per-syndrome evidence grade
  - mandatory non-diagnostic disclaimer
"""
import os
import sys

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
sys.path.insert(0, os.path.abspath(SRC))

from tcm_hrv_estimator import HRVFeatures, TCMAssessment, estimate_tcm
from tcm_theory import SyndromeId, EvidenceGrade


def _feat(rmssd=40.0, norm=0.0, cls="normal", rate=2.0, hr=None, sleep=None, tags=None):
    return HRVFeatures(
        resting_rmssd=rmssd,
        normalized_hrv=norm,
        recovery_classification=cls,
        recovery_rate=rate,
        resting_hr=hr,
        sleep_hours=sleep,
        mood_tags=list(tags) if tags else [],
    )


def test_five_scores_in_range():
    a = estimate_tcm(_feat(rmssd=35, norm=1.5, cls="normal", rate=2.5, hr=72, sleep=5,
                            tags=["irritable", "exhausted"]))
    for v in (a.qi_blood_deficiency, a.liver_depression, a.spleen_deficiency,
              a.phlegm_turbidity, a.yin_yang_balance):
        assert 0 <= v <= 100


def test_primary_is_a_disorder_axis_not_balance():
    a = estimate_tcm(_feat())  # all low → primary picks first max axis
    assert a.primary_syndrome in (
        SyndromeId.QI_BLOOD, SyndromeId.LIVER_QI,
        SyndromeId.SPLEEN, SyndromeId.PHLEGM,
    )
    assert a.primary_syndrome != SyndromeId.YIN_YANG


def test_composite_liver_spleen_deficiency():
    # slow recovery + low HRV drives both liver & spleen ≥ 50
    a = estimate_tcm(_feat(rmssd=30, norm=0.0, cls="slow", rate=0.0))
    assert a.liver_depression >= 50
    assert a.spleen_deficiency >= 50
    assert SyndromeId.LIVER_SPLEEN in a.secondary_syndromes


def test_composite_heart_spleen_deficiency():
    # zero HRV → qi high; rate 0 → spleen high
    a = estimate_tcm(_feat(rmssd=0, norm=0.0, cls="slow", rate=0.0))
    assert a.qi_blood_deficiency >= 50
    assert a.spleen_deficiency >= 50
    assert SyndromeId.HEART_SPLEEN in a.secondary_syndromes


def test_composite_phlegm_qi_stagnation():
    # high normalized deviation + irritable → phlegm & liver both ≥ 40
    a = estimate_tcm(_feat(rmssd=45, norm=3.0, cls="normal", rate=3.0,
                            tags=["irritable"]))
    assert a.phlegm_turbidity >= 40
    assert a.liver_depression >= 40
    assert SyndromeId.PHLEGM_QI in a.secondary_syndromes


def test_composite_liver_kidney_yin_deficiency():
    # all axes high → balance drops, liver high → 肝肾阴虚
    a = estimate_tcm(_feat(rmssd=0, norm=3.0, cls="slow", rate=0.0))
    assert a.liver_depression >= 40
    assert a.yin_yang_balance <= 60
    assert SyndromeId.LIVER_KIDNEY_YIN in a.secondary_syndromes


def test_evidence_grades_present():
    a = estimate_tcm(_feat())
    for sid in (SyndromeId.QI_BLOOD, SyndromeId.LIVER_QI,
                SyndromeId.SPLEEN, SyndromeId.PHLEGM, SyndromeId.YIN_YANG):
        assert sid in a.evidence
        assert isinstance(a.evidence[sid], EvidenceGrade)


def test_disclaimer_is_non_diagnostic():
    a = estimate_tcm(_feat())
    assert isinstance(a.disclaimer, str)
    assert "倾向性评估" in a.disclaimer
    # Compliance: must NOT frame itself as a clinical diagnosis.
    assert "非中医诊断" in a.disclaimer or "非诊断" in a.disclaimer


def test_backcompat_from_hrv_alias():
    # hrv_engine aliases TCMMetrics = TCMAssessment; from_hrv must still work.
    from hrv_engine import TCMMetrics
    tcm = TCMMetrics.from_hrv(resting_hrv=42.5, normalized_hrv=1.5,
                              recovery=None, resting_hr=72, sleep_hours=5,
                              mood_tags=["irritable", "exhausted"])
    assert 0 <= tcm.qi_blood_deficiency <= 100
    assert isinstance(tcm.primary_syndrome, SyndromeId)
