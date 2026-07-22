"""
Hidden Chain — HRV Analysis Engine v0.2
========================================
中医 + 穿戴数据审计的 HRV 分析核心引擎

v0.2 新增：隐链评分 (Hidden Chain Score)
  — 业界唯一融合中医辨证的穿戴式 HRV 综合评分

输入：华为手表/PPG设备的 HRV 时序数据
输出：隐链评分 + 周期校准后的调节指数 + 中医映射评分

依赖：无（仅使用 Python 标准库）
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import statistics
from collections import defaultdict

# 从评分引擎导入
from hidden_chain_score import (
    HiddenChainScore, HiddenChainScorer, ScoreLevel,
    CyclePhase, TrendAnalysis,
)

# ──────────────────────────────────────────────
# 第 2 层：扩展 CyclePhase（添加 from_day）
# ──────────────────────────────────────────────

# 给 imported CyclePhase 添加 from_day 方法
def _cycle_phase_from_day(day: int, cycle_length: int = 28) -> CyclePhase:
    if day < 1 or day > cycle_length:
        raise ValueError(f"day must be between 1 and {cycle_length}")
    if cycle_length != 28:
        day = int(day * 28 / cycle_length)
    if 1 <= day <= 5:
        return CyclePhase.MENSTRUAL
    elif 6 <= day <= 14:
        return CyclePhase.FOLLICULAR
    elif 15 <= day <= 17:
        return CyclePhase.OVULATORY
    elif 18 <= day <= 24:
        return CyclePhase.LUTEAL
    else:
        return CyclePhase.PREMENSTRUAL

CyclePhase.from_day = staticmethod(_cycle_phase_from_day)


# ──────────────────────────────────────────────
# 第 1 层 & 第 2 层：HRV 数据记录
# ──────────────────────────────────────────────

@dataclass
class HRVRecord:
    """单条 HRV 测量数据"""
    timestamp: str             # ISO 格式时间戳
    rmssd: float               # 相邻 RR 间期差值的均方根 (ms)
    sdnn: float                # NN 间期标准差 (ms)
    hf: float                  # 高频功率 (ms²)
    lf: float                  # 低频功率 (ms²)
    heart_rate: float          # 心率 (bpm)
    is_resting: bool = False   # 是否为静息测量
    event_label: Optional[str] = None  # 事件标签，如 "meeting", "stress", "exercise"
    subjective_mood: Optional[int] = None  # 主观情绪评分 1-10

    @property
    def lf_hf_ratio(self) -> float:
        """LF/HF 比值 — 交感/副交感平衡"""
        if self.hf == 0:
            return float("inf")
        return self.lf / self.hf


@dataclass
class CycleCalibrator:
    """周期校准器 — 第 2 层核心"""
    phase_stats: dict = field(default_factory=dict)
    """每个周期的统计信息: {phase: {"mean": float, "std": float, "count": int}}"""

    def fit(self, records: list[HRVRecord], cycle_days: list[int]):
        """计算各周期的均值和标准差"""
        phase_values = defaultdict(list)

        for record, day in zip(records, cycle_days):
            phase = CyclePhase.from_day(day)
            phase_values[phase.value].append(record.rmssd)

        for phase, values in phase_values.items():
            self.phase_stats[phase] = {
                "mean": statistics.mean(values),
                "std": statistics.stdev(values) if len(values) > 1 else 1.0,
                "count": len(values),
            }

    def normalize(self, rmssd: float, phase: CyclePhase) -> float:
        """z-score 归一化"""
        stats = self.phase_stats.get(phase.value)
        if stats is None or stats["count"] < 2:
            return 0.0
        return (rmssd - stats["mean"]) / stats["std"]


# ──────────────────────────────────────────────
# 第 1 层：恢复速率计算
# ──────────────────────────────────────────────

@dataclass
class RecoveryMetrics:
    """压力事件后的恢复指标"""
    delta_hrv: float           # 事件前后的 HRV 变化量 (ms)
    recovery_time_min: float   # 恢复到基线所需时间 (分钟)
    recovery_rate: float       # 恢复速率 (ms/min)
    classification: str        # 恢复等级: fast / normal / slow

    @classmethod
    def compute(cls, pre_hrv: float, post_hrv_values: list,
                baseline_hrv: float, timestamps_min: list) -> "RecoveryMetrics":
        """计算恢复指标"""
        delta = pre_hrv - post_hrv_values[0] if post_hrv_values else 0

        # 找到恢复到基线的时间
        recovery_time = float("inf")
        for i, val in enumerate(post_hrv_values):
            if i < len(timestamps_min) and abs(val - baseline_hrv) < baseline_hrv * 0.05:
                recovery_time = timestamps_min[i]
                break

        if recovery_time == float("inf"):
            recovery_time = timestamps_min[-1] if timestamps_min else 30.0
            recovery_rate = 0
        else:
            recovery_rate = abs(delta) / recovery_time if recovery_time > 0 else 0

        # 分类
        if recovery_time < 5:
            cls_name = "fast"
        elif recovery_time < 20:
            cls_name = "normal"
        else:
            cls_name = "slow"

        return cls(
            delta_hrv=round(delta, 2),
            recovery_time_min=round(recovery_time, 1),
            recovery_rate=round(recovery_rate, 2),
            classification=cls_name,
        )


# ──────────────────────────────────────────────
# 第 4 层：中医映射
# ──────────────────────────────────────────────

@dataclass
class TCMMetrics:
    """中医证型评分"""
    qi_blood_deficiency: float    # 气血不足评分 0-100
    liver_depression: float       # 肝郁气滞评分 0-100
    spleen_deficiency: float      # 脾虚评分 0-100
    phlegm_turbidity: float       # 痰气互结评分 0-100
    yin_yang_balance: float       # 阴阳平衡指数 0-100

    @classmethod
    def from_hrv(cls, resting_hrv: float, normalized_hrv: float,
                 recovery: RecoveryMetrics, resting_hr: float | None = None,
                 sleep_hours: float | None = None,
                 mood_tags: list[str] | None = None) -> "TCMetrics":
        """从多维度数据映射到中医证型评分。

        ------------------------------------------------
        映射逻辑（五篇论文支撑）：
        ------------------------------------------------
        ① 气血不足 — Shaffer 2017 (N=21,438): RMSSD 低于同龄正常值 = 气血基础薄弱。
           辅助：静息心率偏高（心跳偏快→阴虚/血虚倾向）、睡眠不足→气血生成时间不够。
        ② 肝郁气滞 — NRICM 2010: 肝的疏泄功能反映在 vagal reactivation 速度上。
           肝郁型患者 vagal 下降是所有证型中最严重的。恢复慢或 HRV 剧烈波动 =
           肝主疏泄受阻。辅助：烦躁标签→情志因素直指肝郁。
        ③ 脾虚 — Olivera-Toro 2019 (n=104): 脾虚→SDNN↓17%, HF↓14%, LF/HF↑22%,
           疲劳↑21%, 注意力↓16%。恢复速率慢 + 疲惫标签→脾主运化不足。
        ④ 痰气互结 — Yang 2008: 肝郁痰阻型 vagal 下降最严重。
           周期校准后仍异常（normalized_hrv 偏离 0）→ 不是单纯的生理周期波动。
        ⑤ 阴阳平衡 — 综合评分。前四项越高，平衡越差。
        ------------------------------------------------
        """

        # ── ① 气血不足 (Qi-Blood Deficiency) ──
        # 主信号：RMSSD 低于年龄-正常基线
        # 正常基线参考 Shaffer 2017: 20s=55ms, 30s=48ms, 40s=40ms, 50s=32ms, 60s=28ms
        if resting_hrv <= 0:
            qi_raw = 90
        elif resting_hrv >= 55:
            qi_raw = 0
        elif resting_hrv >= 48:
            qi_raw = (55 - resting_hrv) / 7 * 40       # 48→0, 4:
        elif resting_hrv >= 40:
            qi_raw = 40 + (48 - resting_hrv) / 8 * 30  # 40→40, 48→40
        elif resting_hrv >= 28:
            qi_raw = 70 + (40 - resting_hrv) / 12 * 20 # 28→70, 40→70
        else:
            qi_raw = 90 + (28 - resting_hrv) / 8 * 10  # <28→90+

        # 辅助信号：静息心率偏高（心跳快→阴虚/血虚倾向）
        rhr_bonus = 0
        if resting_hr is not None:
            if resting_hr > 80:
                rhr_bonus = 20
            elif resting_hr > 70:
                rhr_bonus = 10

        # 辅助信号：睡眠不足→气血生成时间不够
        sleep_bonus = 0
        if sleep_hours is not None and sleep_hours > 0 and sleep_hours < 6:
            sleep_bonus = 15

        qi_score = min(100, qi_raw + rhr_bonus + sleep_bonus)

        # ── ② 肝郁气滞 (Liver Qi Stagnation) ──
        # 主信号：恢复速度慢（NRICM 2010: 肝郁型 vagal 下降最严重）
        liver_score = 0
        if recovery.classification == "slow":
            liver_score += 65
        elif recovery.classification == "normal":
            # Normal recovery but HRV is still unstable → mild liver involvement
            if normalized_hrv is not None and abs(normalized_hrv) > 0.5:
                liver_score += 35

        # 辅助信号：恢复速率
        if recovery.recovery_rate is not None:
            if recovery.recovery_rate < 1:
                liver_score += 25  # Very slow recovery
            elif recovery.recovery_rate < 2:
                liver_score += 15  # Below average recovery

        # 辅助信号：烦躁/暴躁标签→情志因素直指肝郁（NRICM 2010 肝郁化火型）
        if mood_tags and ("irritable" in mood_tags or "anxious" in mood_tags):
            liver_score += 15

        # 辅助信号：睡眠不足→加重肝郁（肝藏魂，不寐则魂不安）
        if sleep_hours is not None and sleep_hours > 0 and sleep_hours < 5:
            liver_score += 10

        liver_score = min(100, liver_score)

        # ── ③ 脾虚 (Spleen Deficiency) ──
        # 主信号：恢复速率慢→脾主运化不足（Olivera-Toro 2019: 脾虚→HRV↓17%）
        spleen_raw = 0
        if recovery.recovery_rate is not None:
            if recovery.recovery_rate <= 0:
                spleen_raw = 65
            elif recovery.recovery_rate < 2:
                spleen_raw = 55
            elif recovery.recovery_rate < 4:
                spleen_raw = 40 - (recovery.recovery_rate - 2) * 15
            elif recovery.recovery_rate < 6:
                spleen_raw = 25 - (recovery.recovery_rate - 4) * 10
            else:
                spleen_raw = 0

        # 辅助信号：疲惫/脑雾标签→脾虚的典型表现（Olivera-Toro: 疲劳↑21%, 注意力↓16%）
        if mood_tags:
            if "exhausted" in mood_tags:
                spleen_raw += 20
            if "brain_fog" in mood_tags:
                spleen_raw += 15

        # 辅助信号：HRV 偏低 + RHR 偏高 同时出现 → 脾虚（气血生化之源不足）
        if resting_hrv < 35 and resting_hr is not None and resting_hr > 65:
            spleen_raw += 15

        spleen_score = min(100, spleen_raw)

        # ── ④ 痰气互结 (Phlegm Turbidity) ──
        # 定义：周期校准后仍异常（normalized HRV 偏离 0 较多）
        # Yang 2008: 肝郁痰阻型 vagal 下降是所有证型中最严重的
        nh = normalized_hrv if normalized_hrv is not None else 0
        if abs(nh) <= 1:
            phlegm_score = 0
        elif abs(nh) <= 2:
            phlegm_score = abs(nh) * 30  # 1→30, 2→60
        elif abs(nh) <= 4:
            phlegm_score = 60 + (abs(nh) - 2) * 15  # 2→60, 4→90
        else:
            phlegm_score = min(100, 90 + (abs(nh) - 4) * 5)

        # 辅助信号：脑雾+疲惫同时出现→痰浊蒙蔽清窍
        if mood_tags and "brain_fog" in mood_tags and "exhausted" in mood_tags:
            phlegm_score = min(100, phlegm_score + 15)

        # ── ⑤ 阴阳平衡 (Yin-Yang Balance) ──
        # 四个维度的加权反向——哪个维度高，平衡就低
        from_imbalance = (
            qi_score * 0.30  +   # 气血是基础
            liver_score * 0.25 +  # 肝郁直接影响全身气机
            spleen_score * 0.25 + # 脾是后天之本
            phlegm_score * 0.20   # 痰浊是病理产物
        )
        balance = max(0, min(100, 100 - from_imbalance))

        return cls(
            qi_blood_deficiency=round(qi_score, 1),
            liver_depression=round(liver_score, 1),
            spleen_deficiency=round(spleen_score, 1),
            phlegm_turbidity=round(phlegm_score, 1),
            yin_yang_balance=round(balance, 1),
        )


# ──────────────────────────────────────────────
# 第 5 层：调节指数输出
# ──────────────────────────────────────────────

@dataclass
class DailyRegulationIndex:
    """每日调节指数"""
    score: int                # 0-100
    level: str                # red / yellow / green / purple
    tcm: Optional["TCMMetrics"] = None
    recovery: Optional["RecoveryMetrics"] = None
    phase: Optional[CyclePhase] = None

    @classmethod
    def compute(cls, normalized_hrv: float, resting_hrv: float,
                tcm: "TCMMetrics", recovery: "RecoveryMetrics",
                phase: CyclePhase) -> "DailyRegulationIndex":
        """综合计算每日调节指数"""
        # 基础分来自归一化 HRV（越高越好）
        base = min(50, max(0, 50 + normalized_hrv * 10))

        # 恢复能力加成
        recovery_bonus = {
            "fast": 20, "normal": 10, "slow": -10,
        }.get(recovery.classification, 0)

        # 中医评分加成
        tcm_bonus = (100 - tcm.qi_blood_deficiency) * 0.1
        tcm_bonus += (100 - tcm.liver_depression) * 0.1

        # 周期阶段调整
        phase_adjustment = {
            "menstrual": 0, "follicular": 5, "ovulatory": 3,
            "luteal": 0, "premenstrual": -5,
        }

        total = base + recovery_bonus + tcm_bonus + phase_adjustment.get(phase.value, 0)
        total = max(0, min(100, int(total)))

        if total >= 80:
            level = "purple"
        elif total >= 60:
            level = "green"
        elif total >= 30:
            level = "yellow"
        else:
            level = "red"

        return cls(score=total, level=level, tcm=tcm,
                   recovery=recovery, phase=phase)


# ──────────────────────────────────────────────
# 主引擎
# ──────────────────────────────────────────────

class HRVEngine:
    """Hidden Chain HRV 分析引擎主入口"""

    def __init__(self):
        self.calibrator = CycleCalibrator()
        self.scorer = HiddenChainScorer()
        self._is_fitted = False
        self.score_history: list[int] = []

    def fit_calibrator(self, records: list[HRVRecord], cycle_days: list[int]):
        """训练周期校准器"""
        if len(records) != len(cycle_days):
            raise ValueError("records and cycle_days must have the same length")
        self.calibrator.fit(records, cycle_days)
        self._is_fitted = True

    def analyze_day(self, resting_record: HRVRecord,
                    event_records: list[HRVRecord] = None,
                    day_of_cycle: int = 1,
                    baseline_hrv: float = 40.0) -> tuple[DailyRegulationIndex, HiddenChainScore]:
        """分析单日数据，输出完整报告（调节指数 + 隐链评分）"""
        phase = CyclePhase.from_day(day_of_cycle)

        # 归一化
        if self._is_fitted:
            normalized_hrv = self.calibrator.normalize(resting_record.rmssd, phase)
        else:
            normalized_hrv = 0.0

        # 恢复指标
        recovery = RecoveryMetrics.compute(
            pre_hrv=resting_record.rmssd,
            post_hrv_values=[r.rmssd for r in (event_records or [])],
            baseline_hrv=baseline_hrv,
            timestamps_min=[0],  # 简化处理
        )

        # 中医映射
        tcm = TCMMetrics.from_hrv(resting_record.rmssd, normalized_hrv, recovery)

        # 调节指数
        index = DailyRegulationIndex.compute(
            normalized_hrv, resting_record.rmssd, tcm, recovery, phase
        )

        # 隐链评分（v0.2 新增）
        hcs = self.scorer.compute(
            resting_rmssd=resting_record.rmssd,
            normalized_hrv=normalized_hrv,
            recovery_classification=recovery.classification,
            recovery_rate=recovery.recovery_rate,
            qi_blood=tcm.qi_blood_deficiency,
            liver_depression=tcm.liver_depression,
            spleen_deficiency=tcm.spleen_deficiency,
            phlegm_turbidity=tcm.phlegm_turbidity,
            yin_yang_balance=tcm.yin_yang_balance,
            phase=phase,
        )
        self.score_history.append(hcs.score)

        return index, hcs

    def summary_text(self, index: DailyRegulationIndex) -> str:
        phase_map = {
            "menstrual": "Menstrual (月经期)", "follicular": "Follicular (卵泡期)",
            "ovulatory": "Ovulatory (排卵期)", "luteal": "Luteal (黄体期)", "premenstrual": "Premenstrual (经前期)",
        }
        level_map = {
            "purple": "Purple — Peak", "green": "Green — Good",
            "yellow": "Yellow — Caution", "red": "Red — Rest",
        }

        lines = [
            f"[Regulation Index] {index.score}/100  {level_map.get(index.level, '')}",
            f"Phase: {phase_map.get(index.phase.value, 'unknown')}",
            f"Recovery: {index.recovery.classification} "
            f"({index.recovery.recovery_time_min:.0f}min)",
            "",
            "TCM assessment:",
            f"  Qi-blood def.  (气血不足): {index.tcm.qi_blood_deficiency:.0f}/100",
            f"  Liver stasis   (肝郁气滞): {index.tcm.liver_depression:.0f}/100",
            f"  Spleen def.    (脾虚):     {index.tcm.spleen_deficiency:.0f}/100",
            f"  Yin-yang bal.  (阴阳平衡): {index.tcm.yin_yang_balance:.0f}/100",
        ]
        return "\n".join(lines)


# ──────────────────────────────────────────────
# 使用示例
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Hidden Chain HRV Engine v0.2 ===")
    print("Wearable HRV + Cycle Calibration + TCM Scoring\n")

    records = [
        HRVRecord(timestamp="2026-07-21T07:00", rmssd=42.5, sdnn=52.0,
                  hf=780, lf=1050, heart_rate=68, is_resting=True),
        HRVRecord(timestamp="2026-07-21T12:30", rmssd=35.2, sdnn=44.1,
                  hf=550, lf=1350, heart_rate=74, event_label="meeting"),
        HRVRecord(timestamp="2026-07-21T22:00", rmssd=46.0, sdnn=55.5,
                  hf=820, lf=980, heart_rate=65, is_resting=True),
    ]
    cycle_days = [10, 10, 10]

    engine = HRVEngine()
    engine.fit_calibrator(records, cycle_days)
    reg_idx, hcs = engine.analyze_day(
        records[0], event_records=records[1:2], day_of_cycle=10, baseline_hrv=42.0
    )

    print(hcs.report())
    print()

    history = [72, 68, 75, 70, 74, 78, 76]
    trend = TrendAnalysis.from_history(history)
    print(trend.report())
    print("\n=== Analysis complete ===")
