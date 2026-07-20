"""
Hidden Chain — HRV Analysis Engine v0.1
========================================
中医 + 穿戴数据审计的 HRV 分析核心引擎

输入：华为手表/PPG设备的 HRV 时序数据
输出：周期校准后的调节指数 + 中医映射评分

依赖：无（仅使用 Python 标准库）
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import statistics
from collections import defaultdict

# ──────────────────────────────────────────────
# 第 2 层：周期阶段定义
# ──────────────────────────────────────────────

class CyclePhase(Enum):
    MENSTRUAL = "menstrual"       # 第 1-5 天
    FOLLICULAR = "follicular"     # 第 6-14 天（基线推荐窗口）
    OVULATORY = "ovulatory"       # 第 15-17 天
    LUTEAL = "luteal"             # 第 18-24 天
    PREMENSTRUAL = "premenstrual" # 第 25-28 天

    @classmethod
    def from_day(cls, day: int, cycle_length: int = 28) -> "CyclePhase":
        """根据周期第几天返回阶段"""
        if day < 1 or day > cycle_length:
            raise ValueError(f"day must be between 1 and {cycle_length}")

        # 按比例缩放
        if cycle_length != 28:
            day = int(day * 28 / cycle_length)

        if 1 <= day <= 5:
            return cls.MENSTRUAL
        elif 6 <= day <= 14:
            return cls.FOLLICULAR
        elif 15 <= day <= 17:
            return cls.OVULATORY
        elif 18 <= day <= 24:
            return cls.LUTEAL
        else:
            return cls.PREMENSTRUAL

    @property
    def expected_cva_level(self) -> str:
        """该阶段的预期 CVA 水平"""
        levels = {
            "menstrual": "low",
            "follicular": "high",        # CVA 最高
            "ovulatory": "high",
            "luteal": "moderate",
            "premenstrual": "low",       # CVA 最低
        }
        return levels[self.value]


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
                 recovery: RecoveryMetrics) -> "TCMetrics":
        """从 HRV 指标映射到中医评分

        映射逻辑（基于论文 001+002+003 的理论框架）：
        - 静息 HRV 持续偏低 → 气血不足
        - 事件后恢复慢 + HRV 剧烈波动 → 肝郁
        - 恢复慢 → 脾主运化能力不足
        - 排除周期影响后仍异常 → 痰气互结
        """
        # 气血不足：静息 HRV 越低，评分越高
        # 正常静息 RMSSD 大约 30-60ms，低于 25 提示不足
        qi_score = max(0, 100 - (resting_hrv / 30) * 100) if resting_hrv < 40 else 0

        # 肝郁气滞：恢复慢 + HRV 波动大
        liver_score = 0
        if recovery.classification == "slow":
            liver_score += 50
        if abs(recovery.delta_hrv) > 20:
            liver_score += 30
        liver_score = min(100, liver_score)

        # 脾虚：恢复速率慢
        spleen_score = max(0, 100 - (recovery.recovery_rate * 5)) if recovery.recovery_rate > 0 else 50

        # 痰气互结：周期校准后仍异常（normalized_hrv 偏离 0 越多越异常）
        phlegm_score = min(100, abs(normalized_hrv) * 30) if abs(normalized_hrv) > 1 else 0

        # 阴阳平衡：综合指数，越高越平衡
        balance = max(0, 100 - (qi_score * 0.3 + liver_score * 0.25 +
                                spleen_score * 0.25 + phlegm_score * 0.2))

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
        self._is_fitted = False

    def fit_calibrator(self, records: list[HRVRecord], cycle_days: list[int]):
        """训练周期校准器"""
        if len(records) != len(cycle_days):
            raise ValueError("records and cycle_days must have the same length")
        self.calibrator.fit(records, cycle_days)
        self._is_fitted = True

    def analyze_day(self, resting_record: HRVRecord,
                    event_records: list[HRVRecord] = None,
                    day_of_cycle: int = 1,
                    baseline_hrv: float = 40.0) -> DailyRegulationIndex:
        """分析单日数据，输出完整报告"""
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

        return index

    def summary_text(self, index: DailyRegulationIndex) -> str:
        """生成一句话总结"""
        phase_map = {
            "menstrual": "月经期", "follicular": "卵泡期",
            "ovulatory": "排卵期", "luteal": "黄体期", "premenstrual": "经前期",
        }
        level_map = {
            "purple": "🟣 最佳状态", "green": "🟢 状态良好",
            "yellow": "🟡 需要调节", "red": "🔴 需要关注",
        }

        lines = [
            f"【每日调节指数】{index.score}/100  {level_map.get(index.level, '')}",
            f"当前阶段：{phase_map.get(index.phase.value, '未知')}",
            f"恢复速率：{index.recovery.classification} "
            f"({index.recovery.recovery_time_min:.0f} 分钟恢复)",
            "",
            "中医评估：",
            f"  气血不足：{index.tcm.qi_blood_deficiency:.0f}/100",
            f"  肝郁气滞：{index.tcm.liver_depression:.0f}/100",
            f"  脾虚指数：{index.tcm.spleen_deficiency:.0f}/100",
            f"  阴阳平衡：{index.tcm.yin_yang_balance:.0f}/100",
        ]
        return "\n".join(lines)


# ──────────────────────────────────────────────
# 使用示例
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("═══ Hidden Chain HRV Engine v0.1 ═══")
    print("中医 + 穿戴数据审计的 HRV 分析引擎\n")

    # 模拟数据
    records = [
        HRVRecord(timestamp="2026-07-20T07:00", rmssd=32.5, sdnn=45.2,
                  hf=650, lf=1200, heart_rate=72, is_resting=True),
        HRVRecord(timestamp="2026-07-20T12:30", rmssd=28.1, sdnn=38.5,
                  hf=520, lf=1400, heart_rate=78, event_label="meeting"),
        HRVRecord(timestamp="2026-07-20T22:00", rmssd=35.8, sdnn=48.1,
                  hf=720, lf=1100, heart_rate=68, is_resting=True),
    ]
    cycle_days = [3, 3, 3]  # 月经期第 3 天

    # 运行
    engine = HRVEngine()
    engine.fit_calibrator(records, cycle_days)
    result = engine.analyze_day(
        records[0],
        event_records=records[1:2],
        day_of_cycle=3,
        baseline_hrv=35.0,
    )

    print(engine.summary_text(result))
    print("\n═══ 分析完成 ═══")
