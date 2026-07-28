"""
Hidden Chain — TCM HRV Estimator (research/013, layer 2)
========================================================
Bridges HRV features to TCM syndrome tendencies.

Design (audit-friendly separation from tcm_theory.py):
  - tcm_theory.py  : WHAT a syndrome IS (textbook-grounded, zero HRV)
  - tcm_hrv_estimator.py : how HRV PROXIES it, with EVIDENCE GRADES and a
    NON-DIAGNOSTIC disclaimer.

The five primary scores (qi_blood_deficiency / liver_depression /
spleen_deficiency / phlegm_turbidity / yin_yang_balance) preserve the
original HRV→score mapping (grounded in Shaffer 2017, NRICM 2010,
Olivera-Toro 2019, Yang 2008) so existing behavioral tests stay valid.
On top of that we now EMIT:
  - primary_syndrome  : argmax of the five axes
  - secondary_syndromes : composite patterns (肝郁脾虚 etc.) via tcm_theory rules
  - evidence          : per-syndrome EvidenceGrade from tcm_theory
  - disclaimer        : mandatory compliance text

IMPORTANT: output is a tendency assessment, never a diagnosis.
"""

from dataclasses import dataclass, field
from typing import Optional

from tcm_theory import (
    SyndromeId, EvidenceGrade, HRVProxy,
    SYNDROME_SPECS, COMPOSITE_SYNDROMES,
    TCM_DISCLAIMER, primary_syndrome_ids,
)


@dataclass
class HRVFeatures:
    """Normalized HRV inputs for the estimator (adapter layer flattens raw data)."""
    resting_rmssd: float
    normalized_hrv: float
    recovery_classification: str                 # "fast" / "normal" / "slow"
    recovery_rate: Optional[float] = None
    resting_hr: Optional[float] = None
    sleep_hours: Optional[float] = None
    mood_tags: list[str] = field(default_factory=list)


@dataclass
class TCMAssessment:
    """HRV-based TCM syndrome-tendency assessment.

    向后兼容 (back-compat): the five *_score-like fields keep the original
    field names so DailyRegulationIndex / hidden_chain_score / tests work
    unchanged. New fields add the theory-grounded structure.
    """
    # ── 向后兼容的五个主轴分数 (0-100) ──
    qi_blood_deficiency: float
    liver_depression: float
    spleen_deficiency: float
    phlegm_turbidity: float
    yin_yang_balance: float
    # ── 理论层新增 (research/013) ──
    primary_syndrome: SyndromeId
    secondary_syndromes: list[SyndromeId] = field(default_factory=list)
    evidence: dict[SyndromeId, EvidenceGrade] = field(default_factory=dict)
    disclaimer: str = TCM_DISCLAIMER

    # ──────────────────────────────────────────
    # 兼容旧 from_hrv 签名（hrv_engine 通过别名 TCMMetrics 调用）
    # ──────────────────────────────────────────
    @classmethod
    def from_hrv(cls, resting_hrv: float, normalized_hrv: float,
                 recovery: object, resting_hr: float | None = None,
                 sleep_hours: float | None = None,
                 mood_tags: list[str] | None = None) -> "TCMAssessment":
        """Back-compat entry: accepts the legacy RecoveryMetrics object."""
        feats = HRVFeatures(
            resting_rmssd=resting_hrv,
            normalized_hrv=normalized_hrv if normalized_hrv is not None else 0.0,
            recovery_classification=getattr(recovery, "classification", "normal"),
            recovery_rate=getattr(recovery, "recovery_rate", None),
            resting_hr=resting_hr,
            sleep_hours=sleep_hours,
            mood_tags=list(mood_tags) if mood_tags else [],
        )
        return estimate_tcm(feats)


# ──────────────────────────────────────────────
# 五个主轴分数（保留原算法，数值稳定）
# ──────────────────────────────────────────────
def _qi_score(f: HRVFeatures) -> float:
    qi_raw: float = 0.0
    rh = f.resting_rmssd
    if rh <= 0:
        qi_raw = 90
    elif rh >= 55:
        qi_raw = 0
    elif rh >= 48:
        qi_raw = (55 - rh) / 7 * 40
    elif rh >= 40:
        qi_raw = 40 + (48 - rh) / 8 * 30
    elif rh >= 28:
        qi_raw = 70 + (40 - rh) / 12 * 20
    else:
        qi_raw = 90 + (28 - rh) / 8 * 10

    rhr_bonus = 0
    # 解饱和：rmssd 已提示重度不足(qi_raw>=70)时，心率/睡眠奖励不再叠加——
    # 否则必封顶 100，永远压过更具体的肝郁/脾虚轴，掩盖真实倾向。
    if qi_raw < 70 and f.resting_hr is not None:
        if f.resting_hr > 80:
            rhr_bonus = 20
        elif f.resting_hr > 70:
            rhr_bonus = 10

    sleep_bonus = 0
    if qi_raw < 70 and f.sleep_hours is not None and f.sleep_hours > 0 and f.sleep_hours < 6:
        sleep_bonus = 15

    return min(100.0, qi_raw + rhr_bonus + sleep_bonus)


def _liver_score(f: HRVFeatures) -> float:
    s = 0.0
    if f.recovery_classification == "slow":
        s += 65
    elif f.recovery_classification == "normal" and abs(f.normalized_hrv) > 0.5:
        s += 35

    rr = f.recovery_rate
    if rr is not None:
        if rr < 1:
            s += 25
        elif rr < 2:
            s += 15

    if f.mood_tags and ("irritable" in f.mood_tags or "anxious" in f.mood_tags):
        s += 15
    if f.sleep_hours is not None and f.sleep_hours > 0 and f.sleep_hours < 5:
        s += 10
    return min(100.0, s)


def _spleen_score(f: HRVFeatures) -> float:
    raw: float = 0.0
    rr = f.recovery_rate
    if rr is not None:
        if rr <= 0:
            raw = 65
        elif rr < 2:
            raw = 55
        elif rr < 4:
            raw = 40 - (rr - 2) * 15
        elif rr < 6:
            raw = 25 - (rr - 4) * 10
        else:
            raw = 0

    if f.mood_tags:
        if "exhausted" in f.mood_tags:
            raw += 20
        if "brain_fog" in f.mood_tags:
            raw += 15
    if f.resting_rmssd < 35 and f.resting_hr is not None and f.resting_hr > 65:
        raw += 15
    return min(100.0, raw)


def _phlegm_score(f: HRVFeatures) -> float:
    nh = f.normalized_hrv
    if abs(nh) <= 1:
        s = 0.0
    elif abs(nh) <= 2:
        s = abs(nh) * 30
    elif abs(nh) <= 4:
        s = 60 + (abs(nh) - 2) * 15
    else:
        s = min(100.0, 90 + (abs(nh) - 4) * 5)

    if f.mood_tags and "brain_fog" in f.mood_tags and "exhausted" in f.mood_tags:
        s = min(100.0, s + 15)
    return s


def _balance_score(qi: float, liver: float, spleen: float, phlegm: float) -> float:
    imbalance = qi * 0.30 + liver * 0.25 + spleen * 0.25 + phlegm * 0.20
    return max(0.0, min(100.0, 100 - imbalance))


# ──────────────────────────────────────────────
# 主入口：HRV features → TCMAssessment
# ──────────────────────────────────────────────
# 主证命名阈值：最高病证轴分数低于此值时不命名任何单证（返回 BALANCED）。
# 校准依据（2026-07-28 合成数据自检）："健康"画像各轴在 22-58 区间波动，
# 若无阈值，健康人 5/7 天会被贴上主证标签；50 作为"确有 HRV 可提示的
# 明确病证倾向"切点，低于它视为 HRV 未显示明确倾向。
PRIMARY_MIN_SCORE = 50.0


def estimate_tcm(f: HRVFeatures) -> TCMAssessment:
    qi = round(_qi_score(f), 1)
    liver = round(_liver_score(f), 1)
    spleen = round(_spleen_score(f), 1)
    phlegm = round(_phlegm_score(f), 1)
    balance = round(_balance_score(qi, liver, spleen, phlegm), 1)

    # 主轴分数表（用于 argmax 与证据标注）
    axis_scores = {
        SyndromeId.QI_BLOOD: qi,
        SyndromeId.LIVER_QI: liver,
        SyndromeId.SPLEEN: spleen,
        SyndromeId.PHLEGM: phlegm,
        SyndromeId.YIN_YANG: balance,
    }

    # 主证 = 四个病证轴里分数最高者（YIN_YANG 为平衡指数，不参与"证"排名，
    # 仅作平衡参考）。低于 PRIMARY_MIN_SCORE 则不命名任何单证。
    disorder_axes = [SyndromeId.QI_BLOOD, SyndromeId.LIVER_QI,
                    SyndromeId.SPLEEN, SyndromeId.PHLEGM]
    top_axis = max(disorder_axes, key=lambda sid: axis_scores[sid])
    primary = top_axis if axis_scores[top_axis] >= PRIMARY_MIN_SCORE \
        else SyndromeId.BALANCED

    # 兼证（复合证型）识别，依据 tcm_theory.COMPOSITE_SYNDROMES
    # 注：肝肾阴虚已移出自动判定（HRV 无法代理肾阴虚），故循环内仅剩
    # 肝郁脾虚 / 心脾两虚 / 痰气郁结 三类可 HRV 辨别的复合证型。
    secondary: list[SyndromeId] = []
    for rule in COMPOSITE_SYNDROMES:
        comp_scores = [axis_scores.get(c, 0.0) for c in rule.components]
        if all(s >= rule.threshold for s in comp_scores):
            secondary.append(rule.id)

    # 证据等级：取该证 type 的代理里的最低等级（短板原则）
    evidence: dict[SyndromeId, EvidenceGrade] = {}
    for sid in primary_syndrome_ids():
        spec = SYNDROME_SPECS.get(sid)
        if spec and spec.hrv_proxy:
            evidence[sid] = min(
                (p.grade for p in spec.hrv_proxy),
                key=lambda g: {"weak": 0, "moderate": 1, "strong": 2}[g.value],
            )
        else:
            evidence[sid] = EvidenceGrade.MODERATE

    return TCMAssessment(
        qi_blood_deficiency=qi,
        liver_depression=liver,
        spleen_deficiency=spleen,
        phlegm_turbidity=phlegm,
        yin_yang_balance=balance,
        primary_syndrome=primary,
        secondary_syndromes=secondary,
        evidence=evidence,
        disclaimer=TCM_DISCLAIMER,
    )
