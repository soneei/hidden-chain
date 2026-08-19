#!/usr/bin/env python3
"""
Hidden Chain × DeepSeek Harness 接入示例
==========================================
展示「评分引擎 + AI 自然语言解读」的完整链路：
  1. 用 Hidden Chain 的 HRVEngine / HiddenChainScorer 算出分数与 TCM 报告；
  2. 把引擎输出（结构化数据）交给 DeepSeek Harness 生成用户可读的健康解读；
  3. 输出 JSON 结构化结果，前端可直接渲染。

设计边界：
- harness 是纯工具，本示例是「业务提示词」——两者分离，互不污染。
- 本示例只演示调用方式；是否接入生产 server.py 由产品决策决定。

用法：
    export DEEPSEEK_API_KEY=sk-xxx
    python3 hc_ai_interpreter_demo.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# 让脚本能 import harness 与 hidden-chain 的 src
ROOT = Path(__file__).resolve().parent.parent  # hidden-chain/
sys.path.insert(0, str(ROOT / "tools"))              # deepseek_harness
sys.path.insert(0, str(ROOT / "src"))                # hrv_engine 等

from deepseek_harness import DeepSeekHarness, DeepSeekError  # noqa: E402
from hidden_chain_score import HiddenChainScorer, CyclePhase  # noqa: E402


def build_engine_snapshot() -> dict:
    """构造一份引擎输出快照（真实项目里这是 run_engine_for_user() 的产物）。

    这里用确定性示例数据，保证示例可复现；生产环境直接传引擎返回值即可。
    """
    # 模拟一次完整评分：HRV 偏低、恢复偏慢、中医偏肝郁脾虚、经期第 6 天
    scorer = HiddenChainScorer()
    result = scorer.compute(
        resting_rmssd=32.0,          # 静息 RMSSD 偏低（30-60 为常见区间）
        normalized_hrv=45.0,         # 归一化 HRV
        recovery_classification="slow",  # 恢复偏慢
        recovery_rate=0.5,
        qi_blood=62.0,
        liver_depression=58.0,       # 肝郁偏高
        spleen_deficiency=60.0,      # 脾虚偏高
        phlegm_turbidity=45.0,
        yin_yang_balance=55.0,
        phase=CyclePhase.from_day(6, 28),  # 经期第 6 天
        lifecycle_stage="reproductive",
    )
    return {
        "score": getattr(result, "score", None),
        "level": str(getattr(result, "level", None)),  # 枚举转字符串以便 JSON 序列化
        "one_liner": getattr(result, "one_liner", lambda: "")() if hasattr(result, "one_liner") else "",
        "key_issue": getattr(result, "key_issue", None),
        "report": getattr(result, "report", lambda: "")()[:200] if hasattr(result, "report") else "",
        "raw": {
            "resting_rmssd": 32.0,
            "recovery": "slow",
            "cycle_day": 6,
            "mood_tags": ["疲惫", "压力"],
        },
    }


SYSTEM_PROMPT = """你是「隐链健康」(Hidden Chain) 的用户健康解读助手。
你的任务：把引擎算出的客观指标（分数、等级、关键问题）翻译成普通用户能读懂、
愿意执行的自然语言建议。

要求：
1. 语气温和、专业、不说教、不制造焦虑；
2. 结论必须严格基于给定的数据，禁止编造指标；
3. 建议要具体可执行（1-3 条），不要泛泛而谈；
4. 只输出 JSON，不要多余文字。"""


def main() -> None:
    snapshot = build_engine_snapshot()

    try:
        h = DeepSeekHarness()
    except DeepSeekError as e:
        print(f"[✗] {e}")
        print("提示：export DEEPSEEK_API_KEY=sk-xxx 后再运行。")
        sys.exit(1)

    prompt = (
        "请根据以下健康引擎输出，生成一份面向用户的健康解读。\n"
        f"引擎数据：\n{json.dumps(snapshot, ensure_ascii=False, indent=2)}\n\n"
        "输出 JSON 结构：\n"
        '{"summary": "一段 80 字以内的总结", '
        '"highlights": ["亮点1", "亮点2"], '
        '"concerns": ["需注意1"], '
        '"actionable_advice": ["可执行建议1", "可执行建议2", "可执行建议3"]}'
    )

    schema_hint = (
        '{"summary": str, "highlights": [str], '
        '"concerns": [str], "actionable_advice": [str]}'
    )

    print("① 引擎快照（喂给 AI 的输入）:")
    print(json.dumps(snapshot, ensure_ascii=False, indent=2)[:400])
    print("\n② 调用 DeepSeek harness 生成解读……")

    try:
        result = h.chat_json(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            schema_hint=schema_hint,
            temperature=0.3,
            max_tokens=1200,
        )
    except DeepSeekError as e:
        print(f"[✗] 调用失败：{e}")
        sys.exit(1)

    print("\n③ AI 健康解读（JSON 结构化）:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 落盘演示
    out = ROOT / "data" / "ai_interpretation_demo.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"engine": snapshot, "ai_interpretation": result},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[✓] 已保存到 {out}")


if __name__ == "__main__":
    main()
