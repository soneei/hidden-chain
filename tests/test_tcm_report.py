"""
Tests for the TCM report layer (src/tcm_report.py).

Key compliance assertions:
  - High-tendency axes trigger related syndrome families.
  - Family members are split into HRV-proxyable vs MUST-SEE-CLINIC.
  - The rendered Markdown always carries the non-diagnosis disclaimer
    and an explicit "需面诊" escalation list.
"""

from tcm_theory import SyndromeId, EvidenceGrade
from tcm_hrv_estimator import TCMAssessment
from tcm_report import build_tcm_report, render_markdown, report_to_dict


def _make_assessment(qi, liver, spleen, phlegm, balance,
                     primary, secondary):
    ev = {
        SyndromeId.QI_BLOOD: EvidenceGrade.MODERATE,
        SyndromeId.LIVER_QI: EvidenceGrade.MODERATE,
        SyndromeId.SPLEEN: EvidenceGrade.MODERATE,
        SyndromeId.PHLEGM: EvidenceGrade.MODERATE,
    }
    return TCMAssessment(
        qi_blood_deficiency=qi,
        liver_depression=liver,
        spleen_deficiency=spleen,
        phlegm_turbidity=phlegm,
        yin_yang_balance=balance,
        primary_syndrome=primary,
        secondary_syndromes=list(secondary),
        evidence=ev,
    )


def test_high_tendency_triggers_families():
    a = _make_assessment(
        qi=60.0, liver=72.0, spleen=55.0, phlegm=30.0, balance=40.0,
        primary=SyndromeId.LIVER_QI,
        secondary=[SyndromeId.LIVER_SPLEEN],
    )
    r = build_tcm_report(a)
    labels = [c.label for c in r.family_clusters]
    assert any("肝系" in l for l in labels), f"expected Liver family, got {labels}"
    assert any("脾系" in l for l in labels), f"expected Spleen family, got {labels}"
    # yin_yang below 50 -> deficiency family appears
    assert any("虚证家族" in l for l in labels), f"expected Deficiency family, got {labels}"


def test_must_see_clinic_is_nonempty_and_real_entries():
    a = _make_assessment(
        qi=60.0, liver=72.0, spleen=55.0, phlegm=30.0, balance=40.0,
        primary=SyndromeId.LIVER_QI,
        secondary=[SyndromeId.LIVER_SPLEEN],
    )
    r = build_tcm_report(a)
    assert r.must_see_clinic, "high liver/spleen tendency must produce clinic list"
    # every must-see entry must be an ontology entry HRV cannot proxy
    for m in r.must_see_clinic:
        assert m.hrv_detectable is False
    names = [m.name_cn for m in r.must_see_clinic]
    # Liver family contains hrv_detectable=False members (e.g. 肝血虚)
    assert "肝血虚" in names, f"expected 肝血虚 in clinic list, got {names}"


def test_hrv_proxyable_members_flagged_in_cluster():
    a = _make_assessment(
        qi=60.0, liver=72.0, spleen=55.0, phlegm=30.0, balance=40.0,
        primary=SyndromeId.LIVER_QI,
        secondary=[SyndromeId.LIVER_SPLEEN],
    )
    r = build_tcm_report(a)
    liver_cluster = next(c for c in r.family_clusters if "肝系" in c.label)
    detectable = [m.name_cn for m in liver_cluster.members if m.hrv_detectable]
    # 肝郁气滞 is HRV-proxyable and must appear as a "HRV 可提示" member
    assert "肝郁气滞" in detectable, f"expected 肝郁气滞 proxyable, got {detectable}"


def test_low_scores_no_families_no_clinic():
    a = _make_assessment(
        qi=10.0, liver=5.0, spleen=8.0, phlegm=2.0, balance=95.0,
        primary=SyndromeId.LIVER_QI,
        secondary=[],
    )
    r = build_tcm_report(a)
    assert r.family_clusters == [], "low scores should not trigger families"
    assert r.must_see_clinic == [], "low scores should not require clinic"


def test_markdown_carries_disclaimer_and_clinic_list():
    a = _make_assessment(
        qi=60.0, liver=72.0, spleen=55.0, phlegm=30.0, balance=40.0,
        primary=SyndromeId.LIVER_QI,
        secondary=[SyndromeId.LIVER_SPLEEN],
    )
    md = render_markdown(build_tcm_report(a))
    assert "⚠️" in md, "disclaimer must be present"
    assert "必须面诊" in md, "clinic escalation must be present"
    assert "非中医诊断" in md, "non-diagnosis statement must be present"
    assert "肝系" in md and "脾系" in md, "families must be rendered"


def test_markdown_low_scores_still_compliant():
    a = _make_assessment(
        qi=10.0, liver=5.0, spleen=8.0, phlegm=2.0, balance=95.0,
        primary=SyndromeId.LIVER_QI,
        secondary=[],
    )
    md = render_markdown(build_tcm_report(a))
    assert "⚠️" in md
    assert "非中医诊断" in md


def test_markdown_shows_citation_status():
    """Report should distinguish 'has citations' vs 'theory only'."""
    a = _make_assessment(
        qi=60.0, liver=72.0, spleen=55.0, phlegm=30.0, balance=40.0,
        primary=SyndromeId.LIVER_QI,
        secondary=[SyndromeId.LIVER_SPLEEN],
    )
    md = render_markdown(build_tcm_report(a))
    assert "文献支撑" in md, "citation column header must be present"


def test_report_to_dict_serializes_without_enums():
    """report_to_dict must be json.dumps-able (enums -> values)."""
    import json
    a = _make_assessment(
        qi=60.0, liver=72.0, spleen=55.0, phlegm=30.0, balance=40.0,
        primary=SyndromeId.LIVER_QI,
        secondary=[SyndromeId.LIVER_SPLEEN],
    )
    d = report_to_dict(build_tcm_report(a))
    payload = json.dumps(d)  # must not raise on enums
    assert json.loads(payload) == d
    assert d["primary"] == "肝郁气滞", d["primary"]
    assert d["scored_axes"][0]["evidence"] in ("weak", "moderate", "strong")
    assert all(isinstance(m["evidence"], str) for c in d["family_clusters"] for m in c["members"])
    # must-see entries are HRV-non-proxyable
    assert all(m["hrv_detectable"] is False for m in d["must_see_clinic"])
