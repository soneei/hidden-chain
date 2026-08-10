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

# 中医辨证：理论层(tcm_theory) 与 HRV 代理层(tcm_hrv_estimator) 已分离。
# TCMMetrics 现为 TCMAssessment 的别名（向后兼容 5 字段 + 新增主证/兼证/证据）。
# 重构详见 research/013_tcm_syndrome_theory.md。
from tcm_hrv_estimator import TCMAssessment as TCMMetrics

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

        for phase_key, values in phase_values.items():
            self.phase_stats[phase_key] = {
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
    recovery_rate: float | None  # 恢复速率 (ms/min)；无恢复测量时为 None
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
# ──────────────────────────────────────────────
# 第 4 层：中医映射
# ──────────────────────────────────────────────
# TCMMetrics 已迁移至 tcm_hrv_estimator.TCMAssessment（见顶部 import 别名）。
# 理论层（证型定义/辨证要点/舌脉/八纲/复合证型）在 tcm_theory.py，
# 代理层（HRV→证候倾向性）在 tcm_hrv_estimator.py，二者分离便于审计。
# 五主轴分数算法与原实现保持一致（Shaffer 2017 / NRICM 2010 /
# Olivera-Toro 2019 / Yang 2008），新增 primary_syndrome / secondary_syndromes
# （肝郁脾虚等复合证型）/ evidence（证据等级）/ disclaimer（非诊断声明）。

# 第 5 层：调节指数输出
# ──────────────────────────────────────────────

@dataclass
class DailyRegulationIndex:
    """每日调节指数"""
    score: int                # 0-100
    level: str                # red / yellow / green / purple
    tcm: "TCMMetrics"
    recovery: "RecoveryMetrics"
    phase: CyclePhase

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
                    event_records: list[HRVRecord] | None = None,
                    day_of_cycle: int = 1,
                    baseline_hrv: float = 40.0,
                    mood_tags: list[str] | None = None,
                    resting_hr: float | None = None,
                    sleep_hours: float | None = None) -> tuple[DailyRegulationIndex, HiddenChainScore]:
        """分析单日数据，输出完整报告（调节指数 + 隐链评分）

        mood_tags: 情志标签（anxious/irritable/exhausted/brain_fog/...）。
        `TCMAssessment.from_hrv` 一直支持该入参，但此前 analyze_day 从不传递，
        导致走后端引擎时用户勾选的情绪标签对证候分数**完全无影响**
        （前端离线降级路径反而有效）。留空 = 旧行为，向后兼容。

        resting_hr / sleep_hours: 与 mood_tags 同源的缺陷——`from_hrv` 同样一直
        支持这两个入参（静息心率进气血/脾虚轴，睡眠时长进气血/肝郁轴），但
        analyze_day 从不传递，用户在表单里填的静息心率与睡眠时长走后端时
        **一填就丢**。留空 = 旧行为，向后兼容。

        `resting_hr` 未显式给出时，回落到 `resting_record.heart_rate`——记录本身
        就带着这个测量值，此前却被无视（同一条记录 heart_rate=60 与 88 结果完全
        相同）。仅在该记录 `is_resting` 且心率 > 0 时回落：非静息记录的心率是运动/
        事件中的瞬时值，不能当静息心率用；0 是本仓库常见的「未填占位」（server
        构造记录时 sdnn/hf/lf 都填 0），不是真实测量。
        """
        if resting_hr is None and resting_record.is_resting \
                and resting_record.heart_rate > 0:
            resting_hr = resting_record.heart_rate
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
        # 单次每日打卡无恢复事件(未填运动 HRR)时，recovery_rate 原会被算成 0，
        # 而 _spleen_score 把 rr<=0 当最重脾虚(65分)——属误判。置 None 让
        # _spleen_score 跳过恢复惩罚，仅参考情绪标签/HRV，符合「无测量=未知」。
        if not event_records:
            recovery.recovery_rate = None

        # 中医映射（情志标签直接参与肝郁/脾虚/痰浊三轴，静息心率参与气血/脾虚，
        # 睡眠时长参与气血/肝郁，见 tcm_hrv_estimator）
        tcm = TCMMetrics.from_hrv(
            resting_record.rmssd, normalized_hrv, recovery,
            resting_hr=resting_hr, sleep_hours=sleep_hours, mood_tags=mood_tags
        )

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
