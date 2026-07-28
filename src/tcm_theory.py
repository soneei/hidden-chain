"""
Hidden Chain — TCM Syndrome Theory Layer (research/013)
========================================================
Pure theory. ZERO HRV dependency.

This module is the authoritative source for TCM syndrome
definitions used by the engine. It is grounded in the PRC
standard textbooks 《中医诊断学》(Diagnostics of TCM) and
《中医基础理论》(Basic Theory of TCM), NOT reverse-engineered
from HRV.

Why separate from the estimator (tcm_hrv_estimator.py):
  - Auditability: "what is correct" (theory) is isolated from
    "HRV proxy" (evidence). A reviewer audits each independently.
  - Compliance: HRV only proxies a subset of 四诊 (primarily the
    pulse / spirit / overall qi-dynamics axis). It can never stand
    in for tongue inspection, complexion, or classic pulse diagnosis.
    Engine output MUST be framed as "HRV-based syndrome-tendency
    assessment (基于 HRV 的中医证候倾向性评估)", never a clinical
    TCM diagnosis.

See research/013_tcm_syndrome_theory.md for the full rationale and
the evidence grades behind each HRV→syndrome link.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EvidenceGrade(Enum):
    """Evidence grade for an HRV→syndrome proxy link."""
    STRONG = "strong"      # multiple consistent peer-reviewed studies
    MODERATE = "moderate"  # one or two studies, or indirect but supported
    WEAK = "weak"          # theoretical / indirect only; low confidence


class SyndromeId(Enum):
    """Canonical TCM syndrome identifiers (教材证型)."""
    # ── 单证 (primary syndromes) ──
    QI_BLOOD = "qi_blood_deficiency"        # 气血不足
    LIVER_QI = "liver_depression"           # 肝郁气滞
    SPLEEN = "spleen_deficiency"            # 脾虚
    PHLEGM = "phlegm_turbidity"             # 痰气互结
    YIN_YANG = "yin_yang_balance"           # 阴阳平衡 (composite index, 0-100, higher=better)
    # ── 复合证型 (composite syndromes) ──
    LIVER_SPLEEN = "liver_spleen_deficiency"       # 肝郁脾虚
    HEART_SPLEEN = "heart_spleen_deficiency"       # 心脾两虚
    PHLEGM_QI = "phlegm_qi_stagnation"              # 痰气郁结
    LIVER_KIDNEY_YIN = "liver_kidney_yin_deficiency"  # 肝肾阴虚


@dataclass
class HRVProxy:
    """One HRV feature's ability to proxy a 辨证要点, with evidence grade."""
    feature: str          # e.g. "resting_rmssd", "recovery_rate"
    proxy_for: str        # which differentiation point it stands in for
    grade: EvidenceGrade


@dataclass
class SyndromeSpec:
    """Textbook-grounded definition of a TCM syndrome (单证)."""
    id: SyndromeId
    name_cn: str
    name_en: str
    ba_gang: list[str]                       # 八纲归属 (阴阳/表里/寒热/虚实)
    zang_fu: list[str]                       # 相关脏腑
    differentiation_points: list[str]        # 辨证要点 (教材原汁)
    tongue_pulse: str                        # 舌脉特征
    patho: str                               # 病因病机
    diff_diag: list[str]                     # 鉴别诊断
    hrv_proxy: list[HRVProxy] = field(default_factory=list)  # HRV 能代理哪些要点


@dataclass
class CompositeRule:
    """识别规则：当若干单证分数同时超阈值 → 判定复合证型."""
    id: SyndromeId
    name_cn: str
    name_en: str
    components: tuple[SyndromeId, ...]       # 组成单证
    rule_cn: str                             # 识别规则（自然语言）
    threshold: float                         # 组成单证需共同达到的分数阈值


# ──────────────────────────────────────────────
# 单证定义（权威源：规划教材《中医诊断学》《中医基础理论》）
# ──────────────────────────────────────────────
SYNDROME_SPECS: dict[SyndromeId, SyndromeSpec] = {
    SyndromeId.QI_BLOOD: SyndromeSpec(
        id=SyndromeId.QI_BLOOD,
        name_cn="气血不足",
        name_en="Qi-Blood Deficiency",
        ba_gang=["虚", "里"],
        zang_fu=["脾", "心", "肝"],
        differentiation_points=[
            "面色淡白或萎黄，唇甲色淡",
            "神疲乏力，气短懒言",
            "心悸失眠，头晕目眩",
            "舌淡嫩，脉细弱",
        ],
        tongue_pulse="舌淡嫩，苔薄白；脉细弱",
        patho="气血生化乏源（后天失养或劳倦），气虚推动无力，血虚濡养不足。",
        diff_diag=[
            "与'气滞血瘀'鉴别：后者属实，刺痛固定、舌紫暗有瘀斑，脉涩",
            "与'阳虚'鉴别：阳虚必见畏寒肢冷，气血不足未必恶寒",
        ],
        hrv_proxy=[
            HRVProxy("resting_rmssd", "脉气充盛度（整体气血濡养状态的间接反映）", EvidenceGrade.MODERATE),
            HRVProxy("resting_hr", "心跳偏快→阴虚/血虚倾向", EvidenceGrade.WEAK),
            HRVProxy("sleep_hours", "睡眠不足→气血生化时间不足", EvidenceGrade.WEAK),
        ],
    ),
    SyndromeId.LIVER_QI: SyndromeSpec(
        id=SyndromeId.LIVER_QI,
        name_cn="肝郁气滞",
        name_en="Liver-Qi Stagnation",
        ba_gang=["实", "滞", "气机郁结"],
        zang_fu=["肝"],
        differentiation_points=[
            "情志抑郁，善太息（常舒长气）",
            "胸胁、少腹胀闷窜痛",
            "咽中如有异物梗阻（梅核气）",
            "脉弦",
        ],
        tongue_pulse="苔薄白；脉弦",
        patho="肝失疏泄，气机郁滞。情志不遂、暴怒或郁怒伤肝为常见因。",
        diff_diag=[
            "与'肝火炽盛'鉴别：肝火见面红目赤、急躁易怒、口苦，属实热",
            "与'肝阳上亢'鉴别：兼头胀痛、眩晕耳鸣、面红升火",
        ],
        hrv_proxy=[
            HRVProxy("recovery_classification", "vagal reactivation 速度（肝郁型迷走神经下降最显著，NRICM 2010）", EvidenceGrade.MODERATE),
            HRVProxy("normalized_hrv", "HRV 剧烈波动→气机郁滞不稳", EvidenceGrade.MODERATE),
            HRVProxy("mood_tags", "烦躁/焦虑标签→情志因素直指肝郁", EvidenceGrade.WEAK),
        ],
    ),
    SyndromeId.SPLEEN: SyndromeSpec(
        id=SyndromeId.SPLEEN,
        name_cn="脾虚",
        name_en="Spleen Deficiency",
        ba_gang=["虚", "湿", "里"],
        zang_fu=["脾"],
        differentiation_points=[
            "食少纳呆，腹胀便溏（大便溏薄）",
            "肢体倦怠，神疲乏力",
            "面色萎黄，形体偏瘦或虚胖",
            "舌淡胖，边有齿痕，苔白腻；脉缓弱",
        ],
        tongue_pulse="舌淡胖边有齿痕，苔白腻；脉缓弱",
        patho="脾失健运，气血生化不足，水湿不化。劳倦伤脾、饮食不节为常见因。",
        diff_diag=[
            "与'寒湿困脾'鉴别：寒湿为实，见脘腹冷痛、泄泻清稀，舌苔白腻厚",
            "与'脾阳虚'鉴别：兼畏寒肢冷、腹痛喜温喜按",
        ],
        hrv_proxy=[
            HRVProxy("recovery_rate", "恢复速率慢→脾主运化不足（Olivera-Toro 2019：脾虚 HRV↓）", EvidenceGrade.MODERATE),
            HRVProxy("mood_tags", "疲惫/脑雾标签→脾虚典型表现", EvidenceGrade.WEAK),
        ],
    ),
    SyndromeId.PHLEGM: SyndromeSpec(
        id=SyndromeId.PHLEGM,
        name_cn="痰气互结",
        name_en="Phlegm-Turbidity (Phlegm-Qi Binding)",
        ba_gang=["实", "痰", "郁"],
        zang_fu=["脾", "肝", "肺"],
        differentiation_points=[
            "咽中异物感、咯之不出咽之不下（梅核气）",
            "胸脘痞闷，恶心呕吐，头晕困重",
            "体胖、苔腻、脉滑",
            "情志不遂易诱发或加重",
        ],
        tongue_pulse="舌淡红，苔白腻或黄腻；脉滑",
        patho="肝郁脾虚，津液不布，聚湿生痰，痰气互结于咽膈。",
        diff_diag=[
            "与'痰火扰心'鉴别：痰火见心烦失眠、舌红苔黄腻，属实热",
            "与单纯'脾虚生痰'鉴别：无明确气机郁滞与异物感",
        ],
        hrv_proxy=[
            HRVProxy("normalized_hrv", "周期校准后仍显著偏离 0→非单纯生理周期波动（Yang 2008：肝郁痰阻 vagal 下降最重）", EvidenceGrade.MODERATE),
            HRVProxy("mood_tags", "脑雾+疲惫同现→痰浊蒙蔽清窍", EvidenceGrade.WEAK),
        ],
    ),
    SyndromeId.YIN_YANG: SyndromeSpec(
        id=SyndromeId.YIN_YANG,
        name_cn="阴阳平衡",
        name_en="Yin-Yang Balance (composite index)",
        ba_gang=["总纲"],
        zang_fu=["肾", "全身"],
        differentiation_points=[
            "非独立证型，为气血/肝郁/脾虚/痰浊四维度的加权反向综合指数",
            "指数高=整体气机调和、阴阳相对平衡",
        ],
        tongue_pulse="—（综合指数，无独立舌脉）",
        patho="阴阳互根，气血津液调和则平；任一经纬偏盛偏衰则平衡下降。",
        diff_diag=[],
        hrv_proxy=[
            HRVProxy("aggregate", "四单证分数的加权反向（气血 0.30/肝郁 0.25/脾虚 0.25/痰浊 0.20）", EvidenceGrade.MODERATE),
        ],
    ),
}

# ──────────────────────────────────────────────
# 复合证型识别规则（肝郁脾虚等，引擎据分数自动判定）
# ──────────────────────────────────────────────
COMPOSITE_SYNDROMES: list[CompositeRule] = [
    CompositeRule(
        id=SyndromeId.LIVER_SPLEEN,
        name_cn="肝郁脾虚",
        name_en="Liver-Spleen Deficiency (Wood over Earth)",
        components=(SyndromeId.LIVER_QI, SyndromeId.SPLEEN),
        rule_cn="肝郁气滞 ≥ 阈值 且 脾虚 ≥ 阈值 → 木郁乘土，肝郁脾虚",
        threshold=50.0,
    ),
    CompositeRule(
        id=SyndromeId.HEART_SPLEEN,
        name_cn="心脾两虚",
        name_en="Heart-Spleen Deficiency",
        components=(SyndromeId.QI_BLOOD, SyndromeId.SPLEEN),
        rule_cn="气血不足 ≥ 阈值 且 脾虚 ≥ 阈值 → 气血生化不足、心脾同虚",
        threshold=50.0,
    ),
    CompositeRule(
        id=SyndromeId.PHLEGM_QI,
        name_cn="痰气郁结",
        name_en="Phlegm-Qi Stagnation",
        components=(SyndromeId.PHLEGM, SyndromeId.LIVER_QI),
        rule_cn="痰气互结 ≥ 阈值 且 肝郁气滞 ≥ 阈值 → 气郁痰凝",
        threshold=40.0,
    ),
    CompositeRule(
        id=SyndromeId.LIVER_KIDNEY_YIN,
        name_cn="肝肾阴虚",
        name_en="Liver-Kidney Yin Deficiency",
        components=(SyndromeId.LIVER_QI, SyndromeId.YIN_YANG),
        rule_cn="肝郁气滞 ≥ 阈值 且 阴阳平衡 ≤ (100-阈值) → 肝郁化火伤阴",
        threshold=40.0,
    ),
]

# ──────────────────────────────────────────────
# 合规边界（红线）
# ──────────────────────────────────────────────
TCM_DISCLAIMER = (
    "本输出为【基于 HRV 的中医证候倾向性评估】，非中医诊断/辨证结论。"
    "HRV 仅能代理四诊（望闻问切）中脉/神/整体气机之一小部分，"
    "无法替代舌象、面色、脉象等核心辨证依据。低证据等级项须显式降级，"
    "不得单独作为临床或健康决策依据。"
)

# HRV 代理总体声明（解释引擎的覆盖边界）
HRV_PROXY_OVERVIEW = (
    "HRV features proxy only a subset of TCM differentiation points. "
    "Tongue, complexion, and classic pulse diagnosis are NOT covered and "
    "must be obtained through proper TCM consultation for any clinical use."
)


# ──────────────────────────────────────────────
# 辅助查询
# ──────────────────────────────────────────────
def get_spec(sid: SyndromeId) -> Optional[SyndromeSpec]:
    """Return the textbook spec for a single syndrome id, or None for composites."""
    return SYNDROME_SPECS.get(sid)


def primary_syndrome_ids() -> list[SyndromeId]:
    """The five primary (single) syndrome axes the engine scores."""
    return [
        SyndromeId.QI_BLOOD,
        SyndromeId.LIVER_QI,
        SyndromeId.SPLEEN,
        SyndromeId.PHLEGM,
        SyndromeId.YIN_YANG,
    ]


def composite_rules() -> list[CompositeRule]:
    """All composite-syndrome identification rules."""
    return COMPOSITE_SYNDROMES
