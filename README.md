# Hidden Chain

**中医 + 穿戴数据审计的数字健康算法底座**

Hidden Chain 是一套将可穿戴设备（智能手表等）采集的生理信号，与中医辨证理论相结合的算法框架。核心思路是：用现代传感器数据为中医的"气血"、"肝郁"、"脾虚"等概念建立可量化的生物标志物映射。

## 核心理念

```
穿戴设备原始信号 → 西医指标层 → 中医映射层 → 可执行健康建议
     ↓                ↓              ↓               ↓
  HRV/心率/血氧     CVC/CVA        肝郁/脾虚        饮食/作息调节
  睡眠/压力        恢复速率        气血/阴阳        干预建议
```

## 当前模块

### v0.1 — HRV 分析引擎（开发中）

基于三篇权威论文构建的心率变异性分析框架：

- **双轨处理**：静息轨（晨起/睡前基线）+ 事件轨（压力/事件反应）
- **周期校准**：月经周期 5 阶段分层归一化（论文证实 HRV 在经前期比卵泡期低 3-9%）
- **恢复速率**：压力事件后 HRV 恢复速度建模
- **中医映射**：HRV 指标 → 气血/肝郁/脾虚评分

## 论文来源

| # | 论文标题 | 年份 | 核心贡献 |
|---|---|---|---|
| 1 | Cardiac vagal control as a marker of emotion regulation | 2017 | 建立静息 CVC + 相位性 CVC 双轨框架 |
| 2 | CVA changes across the menstrual cycle (meta-analysis) | 2019 | 发现 CVA 从卵泡期到黄体期显著下降 d=-0.39 |
| 3 | Neurovisceral integration model | — | CAN → CVA → 情绪/认知调节的理论框架 |

## 项目结构

```
hidden-chain/
├── README.md              ← 项目简介
├── research/              ← 论文笔记（每天阅读更新）
├── design/                ← 算法设计文档
├── src/                   ← 核心代码
│   └── hrv_engine.py      ← HRV 分析引擎（首个模块）
├── data/                  ← 示例数据（脱敏）
└── .gitignore
```

## 许可

MIT
