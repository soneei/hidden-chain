# Hidden Chain — 架构文档 (ARCHITECTURE)

> 代码到架构的权威映射。面向 reviewer / 协作者 / 合规审计。
> 配套文档：`README.md`（用户视角）、`research/013`（TCM 理论）、`research/014`（本体）、`research/015`（知情同意）。

---

## 1. 设计总纲

Hidden Chain 把**穿戴式 HRV** 变成三层可读输出：**Hidden Chain Score（0–100）**、**自主神经年龄**、**中医证候倾向性评估**。核心约束贯穿全栈：

- **可审计优先**：理论（教材）与证据（HRV proxy）严格分离，每个模块可独立审查。
- **合规红线**：输出一律称「基于 HRV 的中医证候倾向性评估」，**非诊断**；HRV 只代理极小子集；标「需面诊」的项必须线下复核。
- **科学核心可测**：覆盖率门槛只卡可审计算法（`hrv_engine` / `hidden_chain_score` / `tcm_*`），显式排除 I/O 适配层（`data_loader` / `device_adapters`）。

---

## 2. 模块职责与数据流

```
数据源 ──(HRVFeatures)──▶ HRV Engine ──┬─▶ Hidden Chain Score / Autonomic Age / Risk
                                       │
              ┌────────────────────────┴────────────────────────┐
              ▼                                                  ▼
        tcm_theory (纯理论)                              tcm_ontology (89 条本体)
              │                                                  │
              │  EvidenceGrade / 5 轴定义                        │ 家族查询
              ▼                                                  │
        tcm_hrv_estimator.estimate_tcm(HRVFeatures) ──┐         │
              │  → TCMAssessment                        │         │
              ▼                                        ◀─────────┘
        tcm_report.build_tcm_report(assessment)
              │  → TCMReport (scored axes + families + must_see_clinic)
              ▼
        tcm_report.render_markdown / tools/run_pilot.py
```

### 2.1 `src/hrv_engine.py` — HRV 引擎（含 TCM 桥接别名）
- 周期阶段归一化、静息–相位双轨、恢复速率、HRV 基线。
- 通过 `from tcm_hrv_estimator import TCMAssessment as TCMMetrics` 保留旧 `TCMMetrics` 别名，**5 主轴分数数值不变**，下游 `DailyRegulationIndex` / `hidden_chain_score` / 旧测试零改动。

### 2.2 `src/hidden_chain_score.py` — 评分 + 自主神经年龄 + 风险
- `HCS = 0.30×HRVbaseline + 0.25×Recovery + 0.25×TCMbalance + 0.20×PhaseAdj`。
- `estimate_autonomic_age(RMSSD)`：人群 HRV 曲线线性插值（Jarczok/Thayer 2019, N=9,550）。
- 风险三级（绿/黄/红）基于 Thayer 队列阈值。

### 2.3 TCM 四件套（审计友好的理论/证据分离）

| 模块 | 关键符号 | 是否依赖 HRV | 职责 |
|---|---|---|---|
| `tcm_theory.py` | `SyndromeId`, `EvidenceGrade`, `SYNDROME_SPECS`, `COMPOSITE_SYNDROMES`, `TCM_DISCLAIMER`, `HRV_PROXY_OVERVIEW` | 否 | 5 单证教材定义（辨证要点/舌脉/八纲/脏腑/鉴别诊断）+ 复合证型识别规则 + 证据等级枚举 + 合规声明 |
| `tcm_ontology.py` | `TCM_SYNDROME_CATALOG`(89), `validate_catalog()`, `hrv_detectable_entries()`, `catalog_by_organ/principle/etiology`, `catalog_stats()` | 否 | 三轴正交本体（八纲/五脏六腑/六淫病因），每条含 `hrv_detectable`/`evidence`/`citations` |
| `tcm_hrv_estimator.py` | `HRVFeatures`, `TCMAssessment`, `estimate_tcm()`, `PRIMARY_MIN_SCORE=50` | 是 | HRV 特征 → 5 轴分数 → 主证/兼证/证据等级/声明 |
| `tcm_report.py` | `build_tcm_report()`, `render_markdown()`, `FamilyCluster`, `FamilyMember`, `TCMReport` | 消费 assessment | 量化轴 + 相关家族 + 必须面诊清单 |

---

## 3. TCM 本体的三轴正交模型

89 条临床常见证型，按临床推理的**三个正交维度**组织：

1. **八纲 (Eight Principles)**：`yin / yang / exterior / interior / cold / heat / deficiency / excess`
2. **五脏六腑 (Zang-Fu)**：心/肝/脾/肺/肾/胃/小肠/大肠/膀胱/胆/三焦（11 脏腑）
3. **病因 (Etiology)**：六淫 / 七情 / 饮食劳逸 / 病理产物（痰饮/瘀血/结石/食滞）/ 其他

大类分布：`zang_fu`(~52) / `qi_blood_fluid`(~17) / `exterior_pathogen`(~17)。

**`SyndromeCatalogEntry` 字段**：`id, name_cn, name_en, category, organ_system, eight_principle, etiology, differentiation_points, tongue_pulse, patho, hrv_detectable, evidence, notes, citations`。

### 3.1 合规关键：`hrv_detectable`
- 仅 **~17 / 89** 条 `hrv_detectable=True`（确有自主神经/迷走证据：肝郁/肝火/肝阳/心系/脾气虚/肺气虚/肾阴阳虚/气虚/气滞/血虚/血瘀/气血两虚/痰证）。
- 其余 `hrv_detectable=False` 仅供审计 + 报告引用，**引擎绝不据 HRV 打分**。
- `validate_catalog()` 强制：`hrv_detectable` 必须配非 `NONE` 证据；`MODERATE/STRONG` 必须有非空 `citations`。

### 3.2 证据等级 `EvidenceGrade`
| 等级 | 含义 |
|---|---|
| STRONG | 多项一致同行评审研究 |
| MODERATE | 1–2 项研究或间接但被支持（**必须带引用**） |
| WEAK | 理论/间接为主，低置信 |
| NONE | 纯理论，HRV 无法代理 |

已核实引用 5 条（`CITE_*` 常量）：焦虑抑郁 HRV、肾虚肝郁 DOR HRV、胸痹心痛 HRV、慢性疲劳 HRV、九种体质 HRV。

---

## 4. 引擎校准要点（2026-07-28 自检结论）

合成数据批判验证后固化的三条规则：

1. **主证阈值 `PRIMARY_MIN_SCORE = 50`**：最高病证轴分数 < 50 时返回 `SyndromeId.BALANCED`（"无明显单证倾向"），避免健康人被误贴主证。
2. **`肝肾阴虚` 移除自动判定**：肾阴虚无独立肾轴 HRV 信号，引擎不得据 HRV 断言；仅保留于本体供报告/面诊参考（合规反例测试保证其不在 `secondary_syndromes`）。
3. **气血分数解饱和**：`_qi_score` 基值 ≥ 70 时不再叠加心率/睡眠奖励，避免恒=100 淹没更具体的肝郁/脾虚轴。

兼证（复合证型）自动识别仅剩三类可 HRV 辨别的：**肝郁脾虚 / 心脾两虚 / 痰气郁结**（阈值 50，痰气郁结 40）。

---

## 5. 报告层：家族聚类与「必须面诊」

`build_tcm_report(assessment, threshold=50)` 逻辑：

- **模块一 量化轴**：输出 4 病证轴分数 + 证据等级；主证/兼证中文名。
- **模块二 相关家族**：对 ≥ 阈值的高倾向轴，按 `SYNDROME_SPECS[sid].zang_fu` 拉同脏腑家族（`catalog_by_organ`）；平衡指数偏低额外拉「虚证家族」（`catalog_by_principle("deficiency")`）。同成员去重。
- **模块三 必须面诊**：所有 `hrv_detectable=False` 的家族成员去重入 `must_see_clinic` 清单，报告第三节按家族归类列出。

`render_markdown()` 输出四节：已量化倾向表 / 相关家族表（含「HRV 可提示 / 需面诊 / 证据等级 / 文献支撑」列）/ ⚠️ 必须面诊 / 合规声明。

---

## 6. 数据管线（pilot）

### 6.1 输入格式
`src/data_loader.py::read_pilot_csv(path)` 读取 CSV，列：

| 列 | 必需 | 约束 |
|---|---|---|
| `user_id` | ✓ | 非空，如 `U01` |
| `date` | ✓ | `YYYY-MM-DD` |
| `resting_rmssd` | ✓ | float > 0 |
| `normalized_hrv` | ✓ | float，有限值 |
| `recovery_classification` | ✓ | `fast`/`normal`/`slow` |
| `recovery_rate` | – | float ≥ 0 |
| `resting_hr` | – | float ∈ (20, 220) |
| `sleep_hours` | – | float ∈ (0, 24] |
| `mood_tags` | – | 分号分隔，如 `irritable;anxious` |

校验：`utf-8-sig`（容 BOM）、缺列/未知列/重复 (user_id,date)/范围越界均报错。`check_pilot_design()` 独立校验每人 7 天（不在 read 内嵌，避免过严破坏单测）。

### 6.2 运行
```bash
# 真实数据：一行命令产出 21 份日报 + 3 份 7 日趋势总结
python tools/run_pilot.py --csv data/pilot/real.csv --out .workbuddy/pilot_reports

# 合成样例（校验管线用）
python tools/run_pilot.py --sample --out .workbuddy/pilot_reports
```
输出结构：`.workbuddy/pilot_reports/{U01,U02,U03}/{day1..day7.md, summary.md}`。

### 6.3 知情同意
`research/015_pilot_consent_template.md`：仅采 HRV、匿名 U01–U03、不采姓名/照片/病历、本地存储不入仓库不上云、可随时退出删除、非诊断声明。

> **隐私**：`data/pilot/` 与 `*.csv` 已在 `.gitignore` 排除，**真实健康数据永不入库/推送**。`data/pilot/real_template.csv` 为本地空白录入模板（无健康数据），便于每日填写。

---

## 7. 质量门禁（CI 四关）

`.github/workflows/ci.yml`，push/PR 到 `main` 触发：

| 关 | Job | 命令 | 失败即阻断 |
|---|---|---|---|
| ① 语法+冒烟 | `quality-gate` (py3.10–3.12) | `py_compile src/*.py tests/*.py` + `python tests/smoke_test.py` | ✓ |
| ② 类型 | `type-check` (py3.12) | `mypy src/`（读 `pyproject.toml`） | ✓ |
| ③ 单测 | `unit-tests` (py3.12) | `pytest tests/ --cov=src` | ✓ |
| ④ 覆盖率 | 同上 (`[tool.coverage.report] fail_under=80`) | 核心算法覆盖率 ≥ 80 % | ✓ |

排除项：`data_loader.py` / `device_adapters.py`（pandas/设备 I/O 适配层）不计入覆盖率，保持门槛对「可审计科学核心」有意义而非凑数。

本地镜像：`python tools/ci_status_report.py`（输出 Markdown 状态报告，写入 `.workbuddy/ci_reports/`，不推送）。

---

## 8. 开发工作流与护栏

每日自动化代理（工作日上午 9 点）消费 `DEV_BACKLOG.md`，**每次只取第一个未完成任务**，做完标记 `[x]`。护栏：
- 仅 `[smoke]` 任务需「smoke + pytest(--cov≥80) + mypy」三关全过才 push；
- `[manual]` 任务 commit 信息以 `[needs-human-verify]` 开头，提示需人工浏览器/凭据验证；
- 禁 `git push --force`、禁 `git add -A`；绝不暂存 `.workbuddy/` / `*.csv` / `*.db` / `data/*.json`；
- push 前 `git pull --ff-only`（分叉即中止）；
- 运行日志写本地 `.workbuddy/daily_dev_log/YYYY-MM-DD.md`（不推送）。

**CD 策略**：CI 必须有（每日自动 push 的兜底）；自动部署到 staging 可选；**生产绝不**由每日 push 自动触发（健康数据红线 + 早期无 SLA/监控/回滚）。

---

## 9. 已知边界与后续

- **待人工**：请执业中医师逐条审校 `tcm_ontology.py` 的 89 条辨证要点/舌脉/病因病机（尤其复合证型与外感传变）。
- **HRV→TCM 证据仍弱**：多数条目为 WEAK/NONE；随真实文献回填可升 MODERATE（须带引用）。
- **Web 表单**：`server.py` 表单部分交互（提交响应/日期选择器/mood tag）待浏览器人工验证修复。
- **部署**：Render.com 公网部署待凭据与 `Procfile` 配置（已存在 `Procfile`）。
