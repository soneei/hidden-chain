#!/usr/bin/env python3
"""
Hidden Chain — Pilot Batch Report Runner
=========================================
Reads a pilot CSV (3 users × 7 days) and generates:

  .workbuddy/pilot_reports/
    U01/
      day1.md    day2.md  ...  day7.md
      summary.md          # 7-day trend summary
    U02/...
    U03/...

Usage:
  python tools/run_pilot.py --csv data/pilot/sample.csv --out .workbuddy/pilot_reports

Or use the built-in sample generator:
  python tools/run_pilot.py --sample --out .workbuddy/pilot_reports
"""

import argparse
import os
import sys
from collections import defaultdict
from datetime import date as Date
from pathlib import Path
from typing import Optional

# Project root (for imports when run as script)
_PROJ = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(_PROJ, os.pardir)))
sys.path.insert(0, os.path.abspath(os.path.join(_PROJ, os.pardir, "src")))

from data_loader import read_pilot_csv, generate_sample_csv, check_pilot_design
from tcm_hrv_estimator import HRVFeatures, estimate_tcm, TCMAssessment
from tcm_report import build_tcm_report, render_markdown
from tcm_theory import (
    SyndromeId, EvidenceGrade, SYNDROME_SPECS, COMPOSITE_SYNDROMES, TCM_DISCLAIMER,
)


# ──────────────────────────────────────────────
# Axis metadata for trend tables
# ──────────────────────────────────────────────

AXIS_LABELS = [
    ("qi_blood_deficiency", "气血不足"),
    ("liver_depression", "肝郁气滞"),
    ("spleen_deficiency", "脾虚"),
    ("phlegm_turbidity", "痰浊"),
    ("yin_yang_balance", "阴阳平衡"),
]

LEVEL_EMOJI = {
    "purple": "🟣",
    "green": "🟢",
    "yellow": "🟡",
    "red": "🔴",
}

_EVIDENCE_CN = {
    EvidenceGrade.STRONG: "强",
    EvidenceGrade.MODERATE: "中",
    EvidenceGrade.WEAK: "弱",
    EvidenceGrade.NONE: "无",
}

_CN_NUM = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八"}


def _cn_num(n: int) -> str:
    return _CN_NUM.get(n, str(n))


# Build a name lookup that covers both primary and composite syndromes
_COMPOSITE_NAME: dict[SyndromeId, str] = {
    rule.id: rule.name_cn for rule in COMPOSITE_SYNDROMES
}


def _syndrome_name(sid: SyndromeId) -> str:
    """Return Chinese name for any syndrome id (primary or composite)."""
    if sid == SyndromeId.BALANCED:
        return "无明显倾向"
    spec = SYNDROME_SPECS.get(sid)
    if spec:
        return spec.name_cn
    return _COMPOSITE_NAME.get(sid, sid.name)


# ──────────────────────────────────────────────
# Per-day report
# ──────────────────────────────────────────────

def run_day(uid: str, day_idx: int, feats: HRVFeatures, out_dir: str) -> str:
    """Run engine on one day's data and write the markdown report."""
    assessment = estimate_tcm(feats)
    report = build_tcm_report(assessment)
    md = render_markdown(report)

    day_path = os.path.join(out_dir, f"day{day_idx}.md")
    with open(day_path, "w", encoding="utf-8") as f:
        f.write(md)

    return md


# ──────────────────────────────────────────────
# 7-day summary
# ──────────────────────────────────────────────

def _score_list(assessments: list[TCMAssessment], field: str) -> list[float]:
    return [getattr(a, field) for a in assessments]


def _trend_arrow(values: list[float], field_name: str = "") -> str:
    """Compare first-half vs second-half mean."""
    if len(values) < 4:
        return "—"
    n = len(values)
    first = sum(values[: n // 2]) / (n // 2)
    second = sum(values[n // 2 :]) / (n - n // 2)
    diff = second - first
    if field_name == "yin_yang_balance":
        # For balance, higher = better
        if diff > 5:
            return "↑ 改善"
        elif diff < -5:
            return "↓ 恶化"
        else:
            return "→ 稳定"
    else:
        # For disorder axes, lower = better
        if diff < -5:
            return "↓ 改善"
        elif diff > 5:
            return "↑ 恶化"
        else:
            return "→ 稳定"


def _render_summary(uid: str, assessments: list[TCMAssessment]) -> str:
    """Generate a 7-day trend summary markdown."""
    lines: list[str] = []
    lines.append(f"# {uid} — 7日 HRV-TCM 趋势总结")
    lines.append("")
    lines.append(f"> 基于 7 日穿戴式 HRV 数据的中医证候倾向性评估（非诊断）")
    lines.append("")
    lines.append(f"> ⚠️ {TCM_DISCLAIMER}")
    lines.append("")

    # ── 五轴 7 日趋势表 ──
    lines.append("## 一、5 轴证候倾向分数 (7 日趋势)")
    lines.append("")
    header = "| Day | 气血不足 | 肝郁气滞 | 脾虚 | 痰浊 | 阴阳平衡 | 主证 |"
    lines.append(header)
    lines.append("|" + "---|" * 6 + "---|")
    for i, a in enumerate(assessments, 1):
        qi = f"{a.qi_blood_deficiency:.0f}"
        liver = f"{a.liver_depression:.0f}"
        spleen = f"{a.spleen_deficiency:.0f}"
        phlegm = f"{a.phlegm_turbidity:.0f}"
        balance = f"{a.yin_yang_balance:.0f}"
        spec = SYNDROME_SPECS.get(a.primary_syndrome)
        primary = _syndrome_name(a.primary_syndrome)
        lines.append(f"| Day {i} | {qi} | {liver} | {spleen} | {phlegm} | {balance} | {primary} |")
    lines.append("")

    # ── 趋势分析 ──
    lines.append("## 二、趋势分析")
    lines.append("")
    lines.append("| 证候轴 | 前半周均值 | 后半周均值 | 趋势 |")
    lines.append("|---|---|---|---|")
    for field, label in AXIS_LABELS:
        values = _score_list(assessments, field)
        n = len(values)
        first_mean = sum(values[: n // 2]) / (n // 2)
        second_mean = sum(values[n // 2 :]) / (n - n // 2)
        arrow = _trend_arrow(values, field)
        lines.append(f"| {label} | {first_mean:.1f} | {second_mean:.1f} | {arrow} |")
    lines.append("")

    # ── 主证迁移 ──
    lines.append("## 三、主证迁移")
    lines.append("")
    primary_days: dict[str, list[int]] = {}
    for i, a in enumerate(assessments, 1):
        name = _syndrome_name(a.primary_syndrome)
        primary_days.setdefault(name, []).append(i)
    for name, days in primary_days.items():
        day_str = ", ".join(f"Day {d}" for d in days)
        lines.append(f"- **{name}**：{day_str}（{len(days)}/7 天）")
    lines.append("")

    # ── 兼证出现 ──
    sec_count: dict[str, int] = defaultdict(int)
    for a in assessments:
        for s in a.secondary_syndromes:
            name = _syndrome_name(s)
            sec_count[name] += 1
    if sec_count:
        lines.append("## 四、兼证（复合证型）出现频率")
        lines.append("")
        for name, cnt in sorted(sec_count.items(), key=lambda x: -x[1]):
            lines.append(f"- **{name}**：{cnt}/7 天")
        lines.append("")

    # ── 改善/关注项 ──
    improvements: list[str] = []
    warnings: list[str] = []
    for field, label in AXIS_LABELS:
        values = _score_list(assessments, field)
        arrow = _trend_arrow(values, field)
        if "改善" in arrow:
            improvements.append(f"**{label}** {arrow}")
        elif "恶化" in arrow:
            warnings.append(f"**{label}** {arrow}")

    if improvements:
        lines.append("## 五、✅ 改善项")
        lines.append("")
        for item in improvements:
            lines.append(f"- {item}")
        lines.append("")
    if warnings:
        lines.append("## 六、⚠️ 关注项")
        lines.append("")
        for item in warnings:
            lines.append(f"- {item}")
        lines.append("")
        sec = 7
    else:
        sec = 6

    # ── 合规 ──
    lines.append(f"## {_cn_num(sec)}、合规说明")
    lines.append("")
    lines.append("- 本总结为基于 7 日 **HRV 趋势的中医证候倾向性评估**，非诊断结论。")
    lines.append("- 趋势中「改善/恶化」仅描述 HRV 指标变化方向，不映射临床疗效。")
    lines.append("- 如需辨证诊断或调治，请咨询执业中医师。")
    lines.append("")

    return "\n".join(lines)


# ──────────────────────────────────────────────
# Main runner
# ──────────────────────────────────────────────

def run_pilot(csv_path: str, out_root: str) -> None:
    """Run full pilot batch: per-day reports + 7-day summaries."""
    result = read_pilot_csv(csv_path)
    if not result.ok:
        print("❌ CSV validation failed:")
        for e in result.errors:
            print(f"  L{e.line} [{e.user_id} {e.date}] {e.message}")
        sys.exit(1)

    print(f"✅ CSV valid: {len(result.data)} user(s) loaded")
    for uid, feats_list in result.data.items():
        print(f"  {uid}: {len(feats_list)} days")

    # Pilot design check
    design_issues = check_pilot_design(result.data)
    if design_issues:
        print("⚠️  Pilot design issues:")
        for w in design_issues:
            print(f"  {w}")

    # Per-user processing
    for uid, feats_list in sorted(result.data.items()):
        user_dir = os.path.join(out_root, uid)
        os.makedirs(user_dir, exist_ok=True)

        assessments: list[TCMAssessment] = []
        for i, feats in enumerate(feats_list, 1):
            assessment = estimate_tcm(feats)
            assessments.append(assessment)
            run_day(uid, i, feats, user_dir)

        # 7-day summary
        summary_md = _render_summary(uid, assessments)
        summary_path = os.path.join(user_dir, "summary.md")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary_md)

        n_improved = sum(
            1 for f, _ in AXIS_LABELS
            if "改善" in _trend_arrow(_score_list(assessments, f))
        )
        n_worse = sum(
            1 for f, _ in AXIS_LABELS
            if "恶化" in _trend_arrow(_score_list(assessments, f))
        )
        print(f"  {uid}: day1-day7 done, summary written "
              f"({n_improved} improved, {n_worse} concern)")

    print(f"\n📁 Reports: {os.path.abspath(out_root)}")


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(description="Hidden Chain pilot batch report runner")
    p.add_argument("--csv", help="Path to pilot CSV file")
    p.add_argument("--sample", action="store_true",
                   help="Generate a sample CSV and run on it")
    p.add_argument("--out", default=".workbuddy/pilot_reports",
                   help="Output directory (default: .workbuddy/pilot_reports)")
    p.add_argument("--sample-csv-path", default=".workbuddy/pilot_sample.csv",
                   help="Sample CSV path when using --sample")
    args = p.parse_args()

    if args.sample:
        csv_path = args.sample_csv_path
        generate_sample_csv(csv_path)
        print(f"📝 Sample CSV generated: {csv_path}")
    elif args.csv:
        csv_path = args.csv
    else:
        p.error("Must provide --csv or --sample")

    run_pilot(csv_path, args.out)


if __name__ == "__main__":
    main()
