"""
Tests for the TCM syndrome ontology (research/014, src/tcm_ontology.py).

The ontology is PURE theory (zero HRV). These tests guard:
  - the net is big enough (>= 80 common clinical syndromes)
  - it is internally consistent (controlled vocab, no dup ids,
    hrv_detectable implies a real evidence grade)
  - the query helpers return correct slices
"""
import pytest

from tcm_ontology import (
    TCM_SYNDROME_CATALOG,
    EIGHT_PRINCIPLES,
    ZANG_FU_ORGANS,
    ETIOLOGY_ALL,
    CATEGORY_ZANGFU,
    CATEGORY_QI_BLOOD,
    CATEGORY_EXTERIOR,
    validate_catalog,
    catalog_stats,
    catalog_by_organ,
    catalog_by_principle,
    catalog_by_etiology,
    catalog_by_category,
    hrv_detectable_entries,
    get_entry,
    SyndromeCatalogEntry,
)
from tcm_theory import EvidenceGrade


def test_catalog_size_at_least_80():
    # 用户要求织一张 80-100 证型的网；不低于下限
    assert len(TCM_SYNDROME_CATALOG) >= 80
    # 且控制在合理上限（避免无意义膨胀）
    assert len(TCM_SYNDROME_CATALOG) <= 120


def test_catalog_is_consistent():
    errors = validate_catalog()
    assert errors == [], f"ontology consistency errors:\n" + "\n".join(errors)


def test_no_duplicate_ids():
    ids = [e.id for e in TCM_SYNDROME_CATALOG.values()]
    assert len(ids) == len(set(ids))


def test_controlled_vocab_respected():
    valid_organs = set(ZANG_FU_ORGANS.keys())
    for sid, e in TCM_SYNDROME_CATALOG.items():
        for o in e.organ_system:
            assert o in valid_organs, f"{sid}: bad organ {o}"
        for p in e.eight_principle:
            assert p in EIGHT_PRINCIPLES, f"{sid}: bad principle {p}"
        for f in e.etiology:
            assert f in ETIOLOGY_ALL, f"{sid}: bad etiology {f}"


def test_hrv_detectable_implies_evidence():
    # 引擎只能打 hrv_detectable 的证型；它们必须有真实证据等级
    for e in hrv_detectable_entries():
        assert e.evidence in (EvidenceGrade.STRONG, EvidenceGrade.MODERATE, EvidenceGrade.WEAK)
        assert e.evidence != EvidenceGrade.NONE


def test_hrv_detectable_is_small_subset():
    # 合规红线：HRV 只能代理极小子集（自主神经相关），不得声称能覆盖全网
    detectable = hrv_detectable_entries()
    assert 5 <= len(detectable) <= 35
    # 绝大多数证型 HRV 不可测
    assert len(detectable) < len(TCM_SYNDROME_CATALOG) * 0.5


def test_category_buckets_sum_to_total():
    zf = len(catalog_by_category(CATEGORY_ZANGFU))
    qb = len(catalog_by_category(CATEGORY_QI_BLOOD))
    ex = len(catalog_by_category(CATEGORY_EXTERIOR))
    assert zf + qb + ex == len(TCM_SYNDROME_CATALOG)


def test_query_by_organ_liver():
    liver = catalog_by_organ("肝")
    names = {e.id for e in liver}
    assert "liver_qi_stagnation" in names
    assert "liver_yang_rising" in names
    # 肝胃不和也累及肝
    assert "liver_stomach_disharmony" in names


def test_query_by_principle_deficiency():
    deficiency = catalog_by_principle("deficiency")
    # 脾虚必在虚证集合
    assert any(e.id == "spleen_qi_deficiency" for e in deficiency)
    # 肝郁气滞是实证，不应在虚证集合
    assert all(e.id != "liver_qi_stagnation" for e in deficiency)


def test_query_by_etiology_anger():
    anger = catalog_by_etiology("怒")
    ids = {e.id for e in anger}
    assert "liver_qi_stagnation" in ids
    assert "liver_fire_hyperactivity" in ids


def test_get_entry_and_missing():
    assert isinstance(get_entry("spleen_qi_deficiency"), SyndromeCatalogEntry)
    assert get_entry("does_not_exist") is None


def test_stats_counts_match():
    stats = catalog_stats()
    assert stats["total"] == len(TCM_SYNDROME_CATALOG)
    assert stats["hrv_detectable"] == len(hrv_detectable_entries())
    assert stats["zang_fu"] == len(catalog_by_category(CATEGORY_ZANGFU))
    assert stats["qi_blood_fluid"] == len(catalog_by_category(CATEGORY_QI_BLOOD))
    assert stats["exterior_pathogen"] == len(catalog_by_category(CATEGORY_EXTERIOR))


def test_every_entry_has_differentiation_points():
    for e in TCM_SYNDROME_CATALOG.values():
        assert e.differentiation_points, f"{e.id}: empty differentiation_points"
        assert e.tongue_pulse, f"{e.id}: empty tongue_pulse"
        assert e.patho, f"{e.id}: empty patho"


def test_moderate_or_above_has_citations():
    """MODERATE/STRONG evidence must carry verified citations."""
    for e in TCM_SYNDROME_CATALOG.values():
        if e.evidence in (EvidenceGrade.STRONG, EvidenceGrade.MODERATE):
            assert e.citations, (
                f"{e.id}: evidence={e.evidence.value} requires non-empty citations"
            )


def test_no_unverified_citation_references():
    """Notes must not contain unverified citation names."""
    forbidden = ["NRICM", "Olivera-Toro", "Yang 2008"]
    for e in TCM_SYNDROME_CATALOG.values():
        for f in forbidden:
            assert f not in e.notes, f"{e.id}: notes still reference '{f}'"
