# 论文 001：CVC 作为情绪调节标志物

**标题**：Cardiac vagal control as a marker of emotion regulation in healthy adults: A review
**作者**：Balzarotti, Biassoni, Colombo, Ciceri
**期刊**：Biological Psychology, 2017
**覆盖**：135 篇实证研究（1996-2016）

## 核心贡献

建立了 HRV 分析的两条主轨道：

### 轨道 A：静息 CVC（Resting / Vagal Tone）
- **测量场景**：无任务、无刺激的安静基线状态
- **生理含义**：反映个体的特质性调节能力和生理弹性储备
- **高值解读**：更好的负面情绪下调能力、更灵活的情绪反应

### 轨道 B：相位性 CVC（Phasic / Vagal Reactivity）
- **测量场景**：面对情绪/压力刺激时，CVC 相对于基线的变化
- **CVC 下降**：应对压力时的正常生理反应（"准备应对"）
- **CVC 增加**：自我调节努力或压力恢复（注意：不等于调节成功，而是调节过程的生理投入）

## 关键指标映射

| 论文指标 | 穿戴设备对应 | 隐链字段 |
|---|---|---|
| RSA | HRV 时域（RMSSD/SDNN） | hrv_rmssd, hrv_sdnn |
| 静息 CVC | 睡眠/晨起静息 HRV | hrv_resting |
| 相位性 CVC | 事件前后 HRV 变化 | hrv_delta |
| 迷走神经张力 | 高频功率 HF | hrv_hf |

## 对隐链的用法

- 定义"恢复速率"：压力事件后 HRV 恢复到基线水平的时间
- 区分"调节努力" vs "调节成功"：HRV↑ + 消极情绪 = 调节努力，HRV↑ + 积极情绪 = 调节成功
