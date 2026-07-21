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
            "purple": "🟣 最佳状态",
            "green": "🟢 状态良好",
            "yellow": "🟡 需要调节",
            "red": "🔴 需要关注",
        }[self.value]

    @property
    def advice(self) -> str:
        """每个等级的一句结论"""
        return {
            "purple": "气血充盈，阴阳调和，今日宜挑战、宜创造",
            "green": "状态在线，正气得养，保持节奏即可",
            "yellow": "肝气微郁，建议疏解：深呼吸 3 分钟、散步 15 分钟",
            "red": "正气不足，今日宜休养、忌硬撑。早睡 + 温热水泡脚",
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

    def one_liner(self) -> str:
        """一句话结论"""
        return self.level.advice

    def report(self) -> str:
        """完整报告"""
        phase_cn = self.phase.label_cn
        key_issue = self._identify_key_issue()

        lines = [
            f"═══ 隐链评分：{self.score}/100  {self.level.label} ═══",
            f"",
            f"一句话：{self.one_liner()}",
            f"",
            f"──────────────────────────────",
            f"当前阶段：{phase_cn}",
            f"子维度：",
            f"  HRV 基线  {self.hrv_baseline:>3}/100  {'█' * (self.hrv_baseline // 10)}",
            f"  恢复速度  {self.recovery_index:>3}/100  {'█' * (self.recovery_index // 10)}",
            f"  中医平衡  {self.tcm_balance:>3}/100  {'█' * (self.tcm_balance // 10)}",
            f"  周期调节  {self.phase_adjustment:>+3}",
            f"──────────────────────────────",
            f"中医辨证：",
            f"  气血不足  {self.qi_blood:>5.0f}/100",
            f"  肝郁气滞  {self.liver_depression:>5.0f}/100",
            f"  脾虚指数  {self.spleen_deficiency:>5.0f}/100",
            f"──────────────────────────────",
        ]
        if key_issue:
            lines.append(f"⚠️ 主要关注：{key_issue}")
        return "\n".join(lines)

    def _identify_key_issue(self) -> Optional[str]:
        """识别最关键的问题"""
        issues = []
        if self.qi_blood > 60:
            issues.append(f"气血不足 ({self.qi_blood:.0f}/100)")
        if self.liver_depression > 50:
            issues.append(f"肝郁气滞 ({self.liver_depression:.0f}/100)")
        if self.spleen_deficiency > 60:
            issues.append(f"脾虚 ({self.spleen_deficiency:.0f}/100)")
        return " / ".join(issues) if issues else None


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
    ) -> HiddenChainScore:
        """
        计算隐链评分。

        公式：
          HCS = HRV基线(0.30) + 恢复指数(0.25) + 中医平衡(0.25) + 周期调节(0.20)
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
            "improving": "↑ 持续改善",
            "stable": "→ 保持稳定",
            "declining": "↓ 需要留意",
        }
        lines = [
            "─── 趋势 ───",
            f"本周均值：{self.week_avg:.0f}  本月均值：{self.month_avg:.0f}",
            f"周趋势：{trend_labels[self.week_trend]}",
            f"月趋势：{trend_labels[self.month_trend]}",
        ]
        return "\n".join(lines)

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
