"""
Hidden Chain — TCM Report Layer (research/014 follow-up)
=========================================================
Turns a TCMAssessment (HRV-based tendency) into a human-readable
report that HIGHLIGHTS the syndrome *families* the user's HRV leans
toward, and — critically — marks which family members HRV CANNOT
tell apart and therefore REQUIRE an in-person TCM consultation.

Why this layer exists
---------------------
The engine only scores 5 abstract axes (qi/blood, liver-qi, spleen,
phlegm, yin-yang balance). The 89-entry ontology (tcm_ontology.py)
holds the full TCM "net". This module bridges them: given the user's
high-tendency axes, it pulls the same-organ / same-eight-principle
families from the ontology, and for every family member states whether
HRV can proxy it (hrv_detectable) or not. Members HRV cannot proxy are
collected into a "MUST SEE CLINIC" list — the explicit "需面诊" output
the user asked for.

Design rules (audit-friendly, compliant):
  - Pure function: TCMAssessment -> TCMReport. No I/O, no network.
  - Never invents scores for hrv_detectable=False entries.
  - Always carries TCM_DISCLAIMER and a "non-diagnosis" framing.
  - Same-cluster membership is by 脏腑 (organ) and 八纲 (eight-principle)
    dimensions — both controlled vocabularies already validated in
    tcm_ontology.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from tcm_theory import (
    SyndromeId,
    EvidenceGrade,
    SYNDROME_SPECS,
    TCM_DISCLAIMER,
)
from tcm_hrv_estimator import TCMAssessment
from tcm_ontology import (
    catalog_by_organ,
    catalog_by_principle,
    SyndromeCatalogEntry,
    ZANG_FU_ORGANS,
)


# 八纲中文(来自 tcm_theory.SyndromeSpec.ba_gang) → ontology 英文键
# (tcm_ontology.EIGHT_PRINCIPLES). Only deficiency/excess/cold/heat are
# useful for family clustering; 阴阳/表里 are too broad to be a "family".
BA_GANG_TO_ONTOLOGY = {
    "虚": "deficiency",
    "实": "excess",
    "寒": "cold",
    "热": "heat",
}

# 四个「病证轴」参与"高倾向"判定；YIN_YANG 为平衡指数，单独处理。
DISORDER_AXES = [
    SyndromeId.QI_BLOOD,
    SyndromeId.LIVER_QI,
    SyndromeId.SPLEEN,
    SyndromeId.PHLEGM,
]

# 证据等级中文显示
_EVIDENCE_CN = {
    EvidenceGrade.STRONG: "强",
    EvidenceGrade.MODERATE: "中",
    EvidenceGrade.WEAK: "弱",
    EvidenceGrade.NONE: "无",
}


@dataclass
class FamilyMember:
    """One syndrome in a related family, with its HRV-proxyability flag."""
    id: str
    name_cn: str
    name_en: str
    hrv_detectable: bool
    evidence: EvidenceGrade
    note: str
    has_citations: bool = False  # True if ontology entry has verified literature


@dataclass
class FamilyCluster:
    """A cluster of related syndromes (same organ or same eight-principle)."""
    label: str
    trigger_score: float
    members: list[FamilyMember] = field(default_factory=list)


@dataclass
class TCMReport:
    """Structured HRV-based TCM tendency report with clinic-escalation list."""
    generated_at: str
    scored_axes: list[tuple[str, float, EvidenceGrade]]   # (name_cn, score, grade)
    primary: str
    secondary: list[str]
    family_clusters: list[FamilyCluster]
    must_see_clinic: list[FamilyMember]
    disclaimer: str


def _to_member(entry: SyndromeCatalogEntry) -> FamilyMember:
    """Convert an ontology entry into a family member with a clarity note."""
    if entry.hrv_detectable:
        note = "HRV 可提示（有自主神经相关证据），但引擎未单独量化，仅供参考"
    else:
        note = "需面诊：HRV 无法代理，须中医四诊（舌象/面色/脉象/问诊）鉴别"
    return FamilyMember(
        id=entry.id,
        name_cn=entry.name_cn,
        name_en=entry.name_en,
        hrv_detectable=entry.hrv_detectable,
        evidence=entry.evidence,
        note=note,
        has_citations=bool(entry.citations),
    )


def build_tcm_report(assessment: TCMAssessment,
                     threshold: float = 50.0) -> TCMReport:
    """Build a structured report from an HRV-based TCM assessment.

    Args:
        assessment: output of tcm_hrv_estimator.estimate_tcm().
        threshold: a disorder axis at/above this score (0-100) is treated
            as a "high tendency" that triggers its organ families.

    Returns:
        TCMReport with scored axes, related families, and a must-see-clinic
        escalation list.
    """
    axis_scores = {
        SyndromeId.QI_BLOOD: assessment.qi_blood_deficiency,
        SyndromeId.LIVER_QI: assessment.liver_depression,
        SyndromeId.SPLEEN: assessment.spleen_deficiency,
        SyndromeId.PHLEGM: assessment.phlegm_turbidity,
        SyndromeId.YIN_YANG: assessment.yin_yang_balance,
    }

    # ── 模块一：引擎已量化的病证轴 ──
    scored_axes: list[tuple[str, float, EvidenceGrade]] = []
    for sid in DISORDER_AXES:
        spec = SYNDROME_SPECS.get(sid)
        name = spec.name_cn if spec else sid.name
        grade = assessment.evidence.get(sid, EvidenceGrade.MODERATE)
        scored_axes.append((name, axis_scores[sid], grade))

    primary_name = ""
    spec0 = SYNDROME_SPECS.get(assessment.primary_syndrome)
    if spec0:
        primary_name = spec0.name_cn

    secondary_names: list[str] = []
    for s in assessment.secondary_syndromes:
        sp = SYNDROME_SPECS.get(s)
        if sp:
            secondary_names.append(sp.name_cn)

    # ── 模块二：相关证型家族（脏腑维度 + 八纲维度）──
    clusters: list[FamilyCluster] = []
    seen_member_ids: set[str] = set()
    covered_organs: set[str] = set()
    covered_principles: set[str] = set()

    # 脏腑维度：每个高倾向病证轴 → 其脏腑归属 → 同脏腑家族
    for sid in DISORDER_AXES:
        if axis_scores[sid] < threshold:
            continue
        spec = SYNDROME_SPECS.get(sid)
        if not spec:
            continue
        for organ in spec.zang_fu:
            if organ in covered_organs:
                continue
            covered_organs.add(organ)
            members = _collect_members(
                catalog_by_organ(organ), seen_member_ids
            )
            if members:
                en = ZANG_FU_ORGANS.get(organ, {}).get("en", organ)
                clusters.append(FamilyCluster(
                    label=f"{organ}系 ({en} family)",
                    trigger_score=axis_scores[sid],
                    members=members,
                ))

    # 八纲维度：平衡指数偏低 → 虚证家族（整体失衡视角）
    if axis_scores[SyndromeId.YIN_YANG] < (100.0 - threshold):
        if "deficiency" not in covered_principles:
            covered_principles.add("deficiency")
            members = _collect_members(
                catalog_by_principle("deficiency"), seen_member_ids
            )
            if members:
                clusters.append(FamilyCluster(
                    label="虚证家族 (Deficiency family)",
                    trigger_score=axis_scores[SyndromeId.YIN_YANG],
                    members=members,
                ))

    # ── 模块三：必须面诊清单（所有 hrv_detectable=False 的去重）──
    must_see: list[FamilyMember] = []
    seen_must: set[str] = set()
    for c in clusters:
        for m in c.members:
            if not m.hrv_detectable and m.id not in seen_must:
                seen_must.add(m.id)
                must_see.append(m)

    return TCMReport(
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        scored_axes=scored_axes,
        primary=primary_name,
        secondary=secondary_names,
        family_clusters=clusters,
        must_see_clinic=must_see,
        disclaimer=TCM_DISCLAIMER,
    )


def _collect_members(entries: list[SyndromeCatalogEntry],
                     seen: set[str]) -> list[FamilyMember]:
    """Convert ontology entries to FamilyMembers, skipping already-seen ids."""
    out: list[FamilyMember] = []
    for e in entries:
        if e.id in seen:
            continue
        seen.add(e.id)
        out.append(_to_member(e))
    return out


def render_markdown(report: TCMReport) -> str:
    """Render the report as a clean, compliance-safe Markdown document."""
    lines: list[str] = []
    lines.append("# 中医证候倾向性评估（基于 HRV）")
    lines.append("")
    lines.append(f"> 生成时间：{report.generated_at}")
    lines.append("")
    lines.append(f"> ⚠️ {report.disclaimer}")
    lines.append("")
    lines.append("## 一、HRV 已量化的证候倾向")
    lines.append("")
    lines.append("| 证候轴 | 分数 (0-100) | 证据等级 |")
    lines.append("|---|---|---|")
    for name, score, grade in report.scored_axes:
        lines.append(f"| {name} | {score:.1f} | {_EVIDENCE_CN[grade]} |")
    lines.append("")
    if report.primary:
        lines.append(f"**主证倾向**：{report.primary}")
    if report.secondary:
        lines.append(f"**兼证（复合证型）**：{', '.join(report.secondary)}")
    lines.append("")
    lines.append("## 二、与你 HRV 倾向相关的证型家族")
    lines.append("")
    lines.append("> 同脏腑 / 同八纲的证型构成「家族」。HRV 仅能提示其中一小部分，"
                 "其余必须面诊鉴别。")
    lines.append("")
    if not report.family_clusters:
        lines.append("本次 HRV 倾向未触发明确的证型家族（各轴分数均较低）。")
        lines.append("")
    for c in report.family_clusters:
        lines.append(f"### {c.label}（触发分数 {c.trigger_score:.1f}）")
        lines.append("")
        lines.append("| 证型 | HRV 可提示 | 需面诊 | 证据等级 | 文献支撑 |")
        lines.append("|---|---|---|---|---|")
        for m in c.members:
            hrv = "✅" if m.hrv_detectable else "—"
            clinic = "—" if m.hrv_detectable else "⚠️ 必须"
            cited = "✅" if m.has_citations else "—"
            lines.append(
                f"| {m.name_cn} | {hrv} | {clinic} | {_EVIDENCE_CN[m.evidence]} | {cited} |"
            )
        lines.append("")
    lines.append("## 三、⚠️ 必须面诊鉴别的证型")
    lines.append("")
    if report.must_see_clinic:
        lines.append(
            f"共 **{len(report.must_see_clinic)}** 个证型与你的 HRV 倾向同属一个家族，"
            "但 **HRV 无法区分**，需执业中医师四诊合参（舌象 / 面色 / 脉象 / 问诊）。"
            "以下按家族归类："
        )
        lines.append("")
        grouped: dict[str, list[FamilyMember]] = {}
        for c in report.family_clusters:
            ms = [m for m in c.members if not m.hrv_detectable]
            if ms:
                grouped.setdefault(c.label, []).extend(ms)
        for label, ms in grouped.items():
            names = "、".join(m.name_cn for m in ms)
            lines.append(f"- **{label}**：{names}")
        lines.append("")
        lines.append("> 说明：HRV 仅能代理自主神经 / 迷走张力，无法替代中医四诊；"
                     "上述证型须面诊鉴别，切勿仅凭 HRV 自行判断或处置。")
    else:
        lines.append("本次倾向未触发需面诊的家族证型。")
    lines.append("")
    lines.append("## 四、合规声明与建议")
    lines.append("")
    lines.append("- 本报告为【基于 HRV 的中医证候倾向性评估】，**非中医诊断 / 辨证结论**。")
    lines.append("- HRV 仅能代理四诊中脉 / 神 / 整体气机之一小部分，"
                 "无法替代舌象、面色、脉象。")
    lines.append("- 标「需面诊」的证型，请结合执业中医师面诊，"
                 "切勿仅凭 HRV 自行判断或处置。")
    lines.append("")
    return "\n".join(lines)
