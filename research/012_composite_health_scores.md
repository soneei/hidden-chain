# Research Note: HRV 综合健康评分的权重分配

**问题：** 谁已经做过"把 HRV 基线、恢复速度、自主神经平衡、周期影响四块合并成一个分"这件事？

**答案：** **没有。** 整个可穿戴行业跟你一样——没人公开过权重。

---

## 行业现状

**Doherty et al. 2025**（BME Front.，系统综述）分析了 **14 个可穿戴品牌的 Composite Health Score (CHS)**：

| 品牌 | 评分名称 | 权重公开？ | 核心输入 |
|---|---|---|---|
| Oura | Readiness Score | ❌ | HRV, RHR, Sleep, Activity, Temp |
| WHOOP | Recovery | ❌ | HRV, RHR, Sleep, RR |
| Garmin | Training Readiness | ❌ | HRV, Sleep, Activity, Stress |
| Fitbit | Daily Readiness | ❌ | HRV, RHR, Sleep, Activity |
| Polar | Nightly Recharge | ❌ | HRV, Sleep (28-day baseline) |
| Samsung | Energy Score | ❌ | HRV, Sleep, Activity |
| Apple | — | ❌ | No composite score yet |
| Ultrahuman | Dynamic Recovery | ❌ | HRV, Sleep, Activity |

**关键发现：**
- 86% 的 CHS 用了 HRV（RMSSD），79% 用了 RHR
- **没有一个品牌公开了权重公式**
- **没有一个 CHS 被临床验证过**

---

## 唯一接近的公开权重

### NeuroScore™（SoliVana Research Institute）

| 维度 | 权重 | 来源 |
|---|---|---|
| HRV Trend | 40% | 个人 30 天基线 |
| Sleep | 25% | 睡眠质量 + 时长 |
| Breathwork | 15% | 每周呼吸训练频率 |
| Spa 频率 | 12% | 距离上次治疗的天数 |
| Recovery | 8% | 运动后的恢复标记 |

**问题：** 来自商业实验室，不是学术论文。没有公布验证数据。但权重分配有参考价值——**HRV 占最大权重是所有系统的共同选择。**

### RDTI（Recovery Index，Bulgaria 2025）

| 参数 | 权重 | 用途 |
|---|---|---|
| SDNN 恢复比 | 0.20 | 总变异性 |
| RMSSD 恢复比 | 0.20 | 迷走神经反应 |
| nHF 恢复比 | 0.15 | 副交感优势 |
| SD1 恢复比 | 0.15 | 短期变异 |
| SampEn | 0.15 | 节律复杂性 |
| 1/DFAα2 | 0.15 | 分形灵活性 |

**限制：** 只为运动恢复设计，不是健康评分。只有 6 个运动员。

---

## 有学术支撑的方法

### Principal Components Analysis (PCA)

**Johns Hopkins 2009** — 276 名老年女性，2 小时动态心电图：

- 把 6 个 HRV 指标（SDNN, RMSSD, pNN50, LF, HF, VLF）输入 PCA
- 前两个主成分解释 90% 的方差 → PC1 = HRV 平均水平，PC2 = 交感/副交感平衡
- **PC2 比单用任何指标，更好地预测 5 年死亡率（β = -0.60, P < 10⁻⁶）**

**为什么 PCA 对 Hidden Chain 有用：**
- PCA 不需要预设权重——数据的内部结构自己决定最优权重
- **如果你的 30 人纵向数据累积完成后，我们可以做一次 PCA，得出 Hidden Chain 自己的权重**

---

## 对 Hidden Chain 的建议

| 当前做法 | 建议替代 |
|---|---|
| 手工权重 0.30/0.25/0.25/0.20 | **标注"待验证权重"**，等 30 人数据到位后跑 PCA |
| 优先级排序 | 先验证自主神经年龄和疾病风险（这两个有独立论文支撑） |
| HCS 总分 | **暂时不要向外部用户展示 HCS 总分**——先展示自主神经年龄、疾病风险、TCM 五症型这三个独立模块 |
| 权重最终解 | 攒够 30 人数据后运行 PCA |
