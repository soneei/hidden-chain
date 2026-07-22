"""
Hidden Chain Score — 隐链评分引擎
====================================
业界唯一融合中医辨证的穿戴式 HRV 综合评分系统。

输入：周期校准后的 HRV 指标 + 中医辨证分数
输出：0-100 的隐链评分 + 一句话结论

依赖：无（仅使用 Python 标准库）
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import statistics


class ScoreLevel(Enum):
    PURPLE = "purple"   # 81-100：最佳状态
    GREEN = "green"     # 61-80：状态良好
    YELLOW = "yellow"   # 31-60：需要调节
    RED = "red"         # 0-30：需要关注

    @property
    def label(self) -> str:
        return {
            "purple": "Purple — Peak",
            "green": "Green — Good",
            "yellow": "Yellow — Caution",
            "red": "Red — Rest",
        }[self.value]

    @property
    def advice(self) -> str:
        return {
            "purple": "Qi and blood are full, yin-yang balanced. A day for challenge and creation.",
            "green": "Steady rhythm, vital energy is nourished. Maintain your pace.",
            "yellow": "Liver qi mildly stagnant. Try 3 min deep breathing and a 15-min walk.",
            "red": "Vital energy is low. Prioritize rest. Early sleep + warm foot soak.",
        }[self.value]


class CyclePhase(Enum):
    MENSTRUAL = "menstrual"
    FOLLICULAR = "follicular"
    OVULATORY = "ovulatory"
    LUTEAL = "luteal"
    PREMENSTRUAL = "premenstrual"

    @property
    def label_cn(self) -> str:
        return {
            "menstrual": "月经期",
            "follicular": "卵泡期",
            "ovulatory": "排卵期",
            "luteal": "黄体期",
            "premenstrual": "经前期",
        }[self.value]

    @property
    def adjustment(self) -> float:
        """周期阶段的自然偏移补偿，让评分不因正常生理波动而误判"""
        return {
            "menstrual": -3,
            "follicular": 5,
            "ovulatory": 3,
            "luteal": 0,
            "premenstrual": -5,
        }[self.value]


@dataclass
class HiddenChainScore:
    """隐链评分：把一个复杂身体状态压缩成一个数字"""

    score: int                # 0-100
    level: ScoreLevel
    phase: CyclePhase

    # 四个子维度（追踪问题来源）
    hrv_baseline: int         # 周期校准后的 HRV 基线 0-100
    recovery_index: int       # 恢复速度评分 0-100
    tcm_balance: int          # 中医阴阳平衡 0-100
    phase_adjustment: int     # 周期调节项 ±10

    # 中医明细
    qi_blood: float
    liver_depression: float
    spleen_deficiency: float

    # Autonomic Age (自主神经年龄, v0.3)
    autonomic_age: int | None = None
    autonomic_age_delta: int | None = None
    autonomic_age_text: str = ""

    # Disease Risk Alert (v0.4) — based on Jarczok/Thayer 2019 (N=9,550)
    risk_alert: str = "green"  # "green" | "yellow" | "red"
    risk_alert_text: str = ""

    # Lifecycle stage (v0.4) — based on de Jager 2025
    lifecycle_stage: str = "reproductive"  # "reproductive" | "perimenopausal" | "postmenopausal"

    def one_liner(self) -> str:
        """一句话结论"""
        return self.level.advice

    def report(self) -> str:
        phase_en = self.phase.value
        key_issue = self._identify_key_issue()

        lines = [
            f"=== Hidden Chain Score: {self.score}/100  {self.level.label} ===",
            f"",
            f"Takeaway: {self.one_liner()}",
            f"",
            f"──────────────────────────────",
            f"Cycle phase: {phase_en}",
            f"Autonomic Age: {self.autonomic_age} yrs" + (f" (real age: {self.autonomic_age_delta:+d} yrs)" if self.autonomic_age_delta is not None else ""),
            f"Disease Risk: {self.risk_alert.upper()}" + (f" — {self.risk_alert_text}" if self.risk_alert_text else ""),
            f"──────────────────────────────",
            f"Sub-scores:",
            f"  HRV baseline  {self.hrv_baseline:>3}/100  {'#' * (self.hrv_baseline // 10)}",
            f"  Recovery      {self.recovery_index:>3}/100  {'#' * (self.recovery_index // 10)}",
            f"  TCM balance   {self.tcm_balance:>3}/100  {'#' * (self.tcm_balance // 10)}",
            f"  Phase adj.    {self.phase_adjustment:>+3}",
            f"──────────────────────────────",
            f"TCM diagnostics:",
            f"  Qi-blood deficiency   (气血不足): {self.qi_blood:>5.0f}/100",
            f"  Liver qi stagnation   (肝郁气滞): {self.liver_depression:>5.0f}/100",
            f"  Spleen deficiency     (脾虚):     {self.spleen_deficiency:>5.0f}/100",
            f"──────────────────────────────",
        ]
        if key_issue:
            lines.append(f"Warning — primary concern: {key_issue}")
        return "\n".join(lines)

    def _identify_key_issue(self) -> Optional[str]:
        issues = []
        if self.qi_blood > 60:
            issues.append(f"Qi-blood deficiency ({self.qi_blood:.0f}/100)")
        if self.liver_depression > 50:
            issues.append(f"Liver qi stagnation ({self.liver_depression:.0f}/100)")
        if self.spleen_deficiency > 60:
            issues.append(f"Spleen deficiency ({self.spleen_deficiency:.0f}/100)")
        return " / ".join(issues) if issues else None


# ─────────────────────────────────────────────
# Autonomic Age (自主神经年龄) — based on Shaffer & Ginsberg 2017
# ─────────────────────────────────────────────

# Reference table: expected RMSSD by age decade
# Source: Shaffer & Ginsberg (2017), Nunan et al. (2010) N=21,438
AGE_NORMS = [
    (20, 55),  # age 20 → expected RMSSD ~55ms
    (30, 48),  # age 30 → expected RMSSD ~48ms
    (40, 40),  # age 40 → expected RMSSD ~40ms
    (50, 32),  # age 50 → expected RMSSD ~32ms
    (60, 28),  # age 60 → expected RMSSD ~28ms
    (70, 24),  # age 70 → expected RMSSD ~24ms
]


# ─────────────────────────────────────────────
# Lifecycle calibration — based on de Jager 2025 + von Holzen 2016
# ─────────────────────────────────────────────

def adjust_for_lifecycle(rmssd: float, age: int, stage: str = "reproductive") -> float:
    """Adjust expected RMSSD based on reproductive lifecycle stage.

    Postmenopausal women naturally have 5-10 years "older" HRV due to estrogen loss.
    CHC users have suppressed HRV, especially in late cycle.
    Returns adjusted RMSSD for baseline comparison.
    """
    if stage == "postmenopausal":
        return rmssd / 0.85  # naturally lower → scale up for fair comparison
    elif stage == "perimenopausal":
        return rmssd / 0.92
    elif stage == "chc_user":
        return rmssd + 3  # CHC suppresses RMSSD by ~3ms on average
    return rmssd


def estimate_autonomic_age(rmssd: float, real_age: int | None = None) -> dict:
    """Estimate autonomic age from RMSSD (resting, short-term measurement).

    Returns a dict with:
      - estimated_age: what age your HRV corresponds to
      - delta: difference from real age (negative = younger, positive = older)
      - interpretation: plain-language summary
    """
    if rmssd <= 0:
        return {"estimated_age": None, "delta": None, "interpretation": "No data."}

    # Linear interpolation across age norms
    if rmssd >= AGE_NORMS[0][1]:
        est = max(16, int(AGE_NORMS[0][0] - (rmssd - AGE_NORMS[0][1]) / 1.5))
    elif rmssd <= AGE_NORMS[-1][1]:
        est = min(90, int(AGE_NORMS[-1][0] + (AGE_NORMS[-1][1] - rmssd) / 0.5))
    else:
        for i in range(len(AGE_NORMS) - 1):
            a1, r1 = AGE_NORMS[i]
            a2, r2 = AGE_NORMS[i + 1]
            if r2 <= rmssd <= r1:
                ratio = (r1 - rmssd) / (r1 - r2) if r1 != r2 else 0
                est = int(a1 + ratio * (a2 - a1))
                break
        else:
            est = 40

    delta = (est - real_age) if real_age else None

    if delta is not None:
        if delta <= -5:
            interp = f"Your autonomic nervous system is {abs(delta)} years younger than your real age. Keep doing what you're doing."
        elif delta <= 2:
            interp = f"Your autonomic age matches your real age. Healthy baseline."
        elif delta <= 8:
            interp = f"Your autonomic system shows {delta} years of premature aging. Focus on sleep, exercise, and stress management."
        else:
            interp = f"Your autonomic system is {delta} years older than your real age — a significant gap. Prioritize recovery: deep sleep, moderate aerobic exercise, deep breathing daily."
    else:
        interp = f"Estimated autonomic age: {est}."

    return {"estimated_age": est, "delta": delta, "interpretation": interp}


# ─────────────────────────────────────────────
# Disease Risk Alert — based on Jarczok/Thayer 2019 (N=9,550)
# ─────────────────────────────────────────────

RISK_THRESHOLDS = {
    (16, 29): {"yellow": 45, "red": 25},
    (30, 39): {"yellow": 38, "red": 25},
    (40, 49): {"yellow": 30, "red": 25},
    (50, 99): {"yellow": 25, "red": 20},
}


def compute_risk_alert(rmssd: float, age: int | None = None, history: list = None) -> dict:
    """Three-tier disease risk alert from RMSSD against Jarczok thresholds."""
    if rmssd is None or rmssd <= 0:
        return {"level": "green", "text": ""}

    ag = age or 35
    yellow, red = 25, 20  # defaults
    for (lo, hi), vals in RISK_THRESHOLDS.items():
        if lo <= ag <= hi:
            yellow, red = vals["yellow"], vals["red"]
            break

    level = "green"
    text = ""

    if rmssd < red:
        level = "red"
        text = "Alert: RMSSD below disease-risk threshold (Jarczok 2019). Prioritize rest, avoid high stress, consider consulting a doctor if sustained."
    elif rmssd < yellow:
        level = "yellow"
        text = "Warning: RMSSD below age-expected range. Reduce load, prioritize sleep and recovery."

    # Consecutive-day rule: if last 3 scores all in yellow or red
    if history and len(history) >= 3:
        recent = history[-3:]
        reds = sum(1 for s in recent if s < red)
        yellows = sum(1 for s in recent if s < yellow)
        if reds >= 3:
            level = "red"
            text = "3+ consecutive days in disease-risk zone. Strongly recommend rest and medical consultation."
        elif yellows + reds >= 3:
            level = "yellow"
            text = "Sustained low HRV for 3 days. Accumulated recovery debt. Prioritize rest."

    return {"level": level, "text": text}


# ─────────────────────────────────────────────
# 评分计算引擎
# ─────────────────────────────────────────────

class HiddenChainScorer:
    """隐链评分计算器"""

    def compute(
        self,
        resting_rmssd: float,
        normalized_hrv: float,
        recovery_classification: str,  # "fast" / "normal" / "slow"
        recovery_rate: float,
        qi_blood: float,
        liver_depression: float,
        spleen_deficiency: float,
        phlegm_turbidity: float,
        yin_yang_balance: float,
        phase: CyclePhase,
        lifecycle_stage: str = "reproductive",
    ) -> HiddenChainScore:
        """
        计算隐链评分。

        公式：
          HCS = HRV基线(0.30) + 恢复指数(0.25) + 中医平衡(0.25) + 周期调节(0.20)

        lifecycle_stage: "reproductive" | "perimenopausal" | "postmenopausal" | "chc_user"
        """

        # —— 子维度 1：HRV 基线 (0-100) ——
        # 正常静息 RMSSD 约 30-60ms，映射到 0-100
        if resting_rmssd >= 60:
            hrv_baseline = 100
        elif resting_rmssd <= 20:
            hrv_baseline = 20
        else:
            hrv_baseline = int((resting_rmssd - 20) / 40 * 80 + 20)

        # —— 子维度 2：恢复指数 (0-100) ——
        recovery_map = {"fast": 85, "normal": 60, "slow": 35}
        recovery_index = recovery_map.get(recovery_classification, 50)
        # 恢复速率微调
        if recovery_rate > 0:
            recovery_index = min(100, recovery_index + int(recovery_rate * 2))

        # —— 子维度 3：中医平衡 (0-100) ——
        tcm_balance = max(0, min(100, int(yin_yang_balance)))

        # —— 子维度 4：周期调节 ——
        phase_adj = phase.adjustment

        # —— 综合 ——
        score = (
            hrv_baseline * 0.30
            + recovery_index * 0.25
            + tcm_balance * 0.25
            + (50 + phase_adj) * 0.20  # 周期项以 50 为中位
        )
        score = max(0, min(100, int(score)))

        # —— 等级 ——
        if score >= 80:
            level = ScoreLevel.PURPLE
        elif score >= 60:
            level = ScoreLevel.GREEN
        elif score >= 30:
            level = ScoreLevel.YELLOW
        else:
            level = ScoreLevel.RED

        # 自主神经年龄 (v0.3) — lifecycle-adjusted
        adjusted_rmssd = adjust_for_lifecycle(resting_rmssd, 35, lifecycle_stage)
        aa = estimate_autonomic_age(adjusted_rmssd)

        return HiddenChainScore(
            score=score,
            level=level,
            phase=phase,
            hrv_baseline=hrv_baseline,
            recovery_index=recovery_index,
            tcm_balance=tcm_balance,
            phase_adjustment=phase_adj,
            qi_blood=qi_blood,
            liver_depression=liver_depression,
            spleen_deficiency=spleen_deficiency,
            autonomic_age=aa["estimated_age"],
            autonomic_age_delta=aa["delta"],
            autonomic_age_text=aa["interpretation"],
            risk_alert=compute_risk_alert(resting_rmssd)["level"],
            risk_alert_text=compute_risk_alert(resting_rmssd)["text"],
            lifecycle_stage=lifecycle_stage,
        )


# ─────────────────────────────────────────────
# 时间序列分析
# ─────────────────────────────────────────────

@dataclass
class TrendAnalysis:
    """7天/30天趋势分析"""
    current_score: int
    week_avg: float
    month_avg: float
    week_trend: str   # "improving" / "stable" / "declining"
    month_trend: str

    def report(self) -> str:
        trend_labels = {
            "improving": "↑ Improving",
            "stable": "→ Stable",
            "declining": "↓ Declining",
        }
        return "\n".join([
            "─── Trend ───",
            f"Weekly avg: {self.week_avg:.0f}   Monthly avg: {self.month_avg:.0f}",
            f"Week: {trend_labels[self.week_trend]}",
            f"Month: {trend_labels[self.month_trend]}",
        ])

    @classmethod
    def from_history(cls, scores: list[int]) -> "TrendAnalysis":
        """从历史评分序列计算趋势"""
        if not scores:
            return cls(current_score=0, week_avg=0, month_avg=0,
                       week_trend="stable", month_trend="stable")

        current = scores[-1]
        week_scores = scores[-7:] if len(scores) >= 7 else scores
        month_scores = scores[-30:] if len(scores) >= 30 else scores

        week_avg = statistics.mean(week_scores)
        month_avg = statistics.mean(month_scores)

        def classify_trend(values: list[int]) -> str:
            if len(values) < 3:
                return "stable"
            half = len(values) // 2
            first_half = statistics.mean(values[:half])
            second_half = statistics.mean(values[half:])
            diff = second_half - first_half
            if diff > 5:
                return "improving"
            elif diff < -5:
                return "declining"
            return "stable"

        return cls(
            current_score=current,
            week_avg=week_avg,
            month_avg=month_avg,
            week_trend=classify_trend(week_scores),
            month_trend=classify_trend(month_scores),
        )


# ─────────────────────────────────────────────
# 示例
# ─────────────────────────────────────────────

if __name__ == "__main__":
    scorer = HiddenChainScorer()

    # 模拟一天的数据
    score = scorer.compute(
        resting_rmssd=42.5,
        normalized_hrv=0.3,
        recovery_classification="normal",
        recovery_rate=2.5,
        qi_blood=15.0,
        liver_depression=30.0,
        spleen_deficiency=20.0,
        phlegm_turbidity=10.0,
        yin_yang_balance=78.0,
        phase=CyclePhase.FOLLICULAR,
    )

    print(score.report())
    print()

    # 趋势
    history = [72, 68, 75, 70, 74, 78, 76]
    trend = TrendAnalysis.from_history(history)
    print(trend.report())
