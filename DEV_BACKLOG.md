# Hidden Chain — 每日开发迭代待办 (DEV_BACKLOG)

由每日自动化代理（工作日上午 9 点）消费：**每次只取第一个 `[ ]` 任务执行**，做完标记 `[x]`，并写运行日志到本地 `.workbuddy/daily_dev_log/YYYY-MM-DD.md`（不推送）。

## verify 级别说明
- `[smoke]`：必须**同时**满足三关才允许 commit + push（任一失败则回退改动并报告）：① `python3 tests/smoke_test.py` 退出码 0；② `pytest tests/ --cov=src` 退出码 0 且覆盖率 ≥80%（pyproject `fail_under`）；③ `mypy src/` 退出码 0。
- `[manual]`：实现后仍以 smoke 为"不破坏引擎"的底线；通过则 commit + push，但 commit 信息以 `[needs-human-verify]` 开头，并在日志标注"需人工在浏览器/凭凭据验证"。

---

## 已完成
- [x] 2026-07-28 建立冒烟自测基线 `tests/smoke_test.py`（import 全引擎 + 校验 ScoreLevel 契约）。
- [x] 2026-07-28 接入质量门禁①：`.github/workflows/ci.yml`，push/PR 到 main 时于 py3.10–3.12 矩阵跑 `py_compile` + `smoke_test.py`，不过不许合并。
- [x] 2026-07-28 接入质量门禁②：`type-check` job 跑 `mypy src/`（读 `pyproject.toml` 配置）。修复 27 个类型错误（含 `TCMetrics` 拼写 bug、`from_day` 移入 `CyclePhase` 枚举、Optional 字段收紧、int/float 标注），新增 `pyproject.toml`。
- [x] 2026-07-28 接入质量门禁③：`unit-tests` job 跑 `pytest tests/test_engine.py`（35 passed）。将 `research/009` 创始人 N=1 案例固化为验证 oracle（HRV 43→自主神经年龄 36 精确吻合），覆盖评分等级边界、CyclePhase 边界、风险评估阈值、趋势判定，新增 `tests/test_engine.py`。
- [x] 2026-07-28 补 `tests/test_hrv_engine.py`（核心引擎覆盖，新增 23 用例），并接入**覆盖率门槛**：`pyproject.toml` 配 `[tool.coverage]`（source=src，omit data_loader/device_adapters 两个 pandas/设备 I/O 适配层，`fail_under=80`）；`[tool.pytest.ini_options]` 设 `python_files=test_*.py`（排除 smoke_test.py 走 pytest 收集）。核心引擎覆盖率 85%（hidden_chain_score 80% / hrv_engine 90%），58 passed，达标。CI `unit-tests` job 改跑 `pytest tests/ --cov=src`。
- [x] 2026-07-28 新增 `tools/ci_status_report.py`：本地镜像 CI 四关、`subprocess` 跑 `py_compile`/`smoke_test`/`mypy`/`pytest --cov`，解析通过率与覆盖率，输出可读 Markdown 状态报告。每日自动化步骤 8.5 在跑完迭代后调用它，把报告写入 `.workbuddy/ci_reports/YYYY-MM-DD.md`（本地，不推送），让用户无需登录 GitHub 即可看当日门禁状态。
- [x] 2026-07-28 立 **中医症型理论层** `research/013_tcm_syndrome_theory.md`：以《中医诊断学》《中医基础理论》规划教材为权威源，定义 5 证型（气血不足/肝郁气滞/脾虚/痰气互结/阴阳平衡）的辨证要点+舌脉+病因病机+鉴别诊断，补八纲→脏腑→气血津液→病因框架与复合证型（肝郁脾虚/心脾两虚/痰气郁结/肝肾阴虚），并明确 HRV 仅作 proxy（证据分级 强/中/弱）、输出须称「证候倾向性评估」、非诊断红线。引擎重构的权威源已就位（用户选择：先立理论层文档，暂不改动引擎代码）。
- [x] 2026-07-28 **TCM 引擎重构落地**（消费 013）：拆分 `tcm_theory.py` + `tcm_hrv_estimator.py`，`hrv_engine.TCMMetrics` 改为 `TCMAssessment` 别名，输出升级为主证/兼证/证据等级/非诊断声明，新增 `tests/test_tcm_estimator.py`。详见上方待办首条 `[x]`。
- [x] 2026-07-28 **TCM 证候本体织网（research/014）**：新建 `src/tcm_ontology.py`（纯理论零 HRV），按八纲/五脏六腑/六淫病因三轴正交组织 **89 条临床常见证型**目录（脏腑辨证 ~52 / 气血津液 ~17 / 外感六淫卫气营血六经 ~17），每条含辨证要点+舌脉+病因病机+八纲归属+脏腑归属+病因+HRV可测性。新增 `EvidenceGrade.NONE`、`validate_catalog()`（查重/受控词表/HRV可测→证据一致）、三轴查询 helper、`catalog_stats()`。新增 `tests/test_tcm_ontology.py`（12 用例，含"HRV 可测为极小子集(5–35)"合规断言）。**关键红线**：89 条中仅约 17 条 `hrv_detectable=True`（确有自主神经证据），其余 `hrv_detectable=False` 仅供审计/报告引用，引擎绝不据 HRV 打分。四关全绿、80 passed、覆盖率 89%。
- [x] 2026-07-28 **文献引用落地（citations field）**：给 `SyndromeCatalogEntry` 加 `citations: list[str]` 字段 + `validate_catalog()` 校验「MODERATE 以上必须有真实引用」；新增 5 条已核实文献常量（CITE_ANXIETY_DEPRESSION_HRV / CITE_DOR_HRV / CITE_CHEST_PAIN_HRV / CITE_CHRONIC_FATIGUE_HRV / CITE_CONSTITUTION_HRV）；回填 12 条证型的真实引用（肝郁气滞/痰证/气虚/气滞/气血两虚升 MODERATE，脾气虚降 WEAK）；清掉 notes 中无法核实的假引用（NRICM 2010 / Olivera-Toro 2019 / Yang 2008），同步清理 `tcm_theory.py` HRVProxy 文本。报告层 `tcm_report.py` 新增「文献支撑」列区分有文献 vs 纯理论。新增 3 测试（MODERATE+ 须有 citations / notes 无假引用 / 报告含文献支撑列）。四关全绿、89 passed、覆盖率 91%。
- [x] 2026-07-28 **数据接入管线三件套（pilot ready）**：新增 `src/data_loader.py`（read_pilot_csv: CSV→HRVFeatures, validate 缺失列/非法值/重复/范围, utf-8 BOM, check_pilot_design 独立设计校验, generate_sample_csv 生成3用户×7天样例）；新增 `tools/run_pilot.py`（批量 runner: 读CSV→每人每天estimate_tcm→build_tcm_report→render_markdown→day{N}.md + 7天 summary.md 含5轴趋势/前后周对比/主证迁移/兼证频率/改善关注项/合规说明）；新增 `research/015_pilot_consent_template.md`（知情同意模板:采集什么、匿名 U01-U03、不采集姓名照片病历、可随时退出、非诊断声明）；新增 `tests/test_data_loader.py`（14用例:有效加载/缺列/非法值/日期/重复/范围/mood_tags分号/BOM/可选字段/文件不存在）。四关全绿、104 passed、覆盖率91%。
- [x] 2026-07-28 **校准自检（Calibration self-check）**：用合成数据跑完整管线，批判性发现 3 个引擎缺陷并修复：①**主证无阈值**→健康合成人(U02) 5/7 天被贴主证（分数仅22-58）；加 `SyndromeId.BALANCED` 哨兵 + `PRIMARY_MIN_SCORE=50`，最高病证轴<50 不命名单证，U02 现 5/7 天"无明显倾向"。②**肝肾阴虚误报**（踩红线）→ 原规则"肝郁≥40且平衡≤60"对 U01(肝郁80-95/平衡17-42) 7/7 误触发，但肾阴虚 HRV 无法代理；从 `COMPOSITE_SYNDROMES` 移除该自动判定（保留本体供报告参考），测试改为合规反例（`not in secondary_syndromes`）。③**气血不足恒=100 淹没具体证型**→`_qi_score` 把心率+20/睡眠+15 叠在已90+基值上必封顶；改为基值≥70 不再叠加奖励分，分数降到84-93，U01 主证在肝郁(90-95)>气血不足 的日子正确翻转为肝郁。同步修 `tcm_report.py`/`run_pilot.py` 渲染 BALANCED="无明显倾向"，更新 2 个旧测试 + 加 3 个新测试（阈值→BALANCED / 解饱和<100 / 肝肾阴虚不断言）。四关全绿、106 passed、覆盖率91%。**结论**：合成数据下引擎行为现合理（健康人不误标、肝郁意图浮现、肾阴虚不误报），真数据到来可直接跑。
- [x] 2026-07-28 **架构文档/README 落地（任务③）**：重写 `README.md`（按当前代码真实状态：5 轴引擎 + 89 条三轴本体 + 证据分级 + 数据管线 + 合规红线；修正旧 README「每行列引用论文」「TCM Diagnosis」不实表述与已清理的假引用 NRICM2010/Olivera-Toro2019/Yang2008）+ 新建根目录 `ARCHITECTURE.md`（模块职责/数据流/理论-证据分离理由/三轴本体/证据等级/校准阈值 PRIMARY_MIN_SCORE=50·解饱和/报告家族聚类+must-see-clinic/数据管线 schema + run 命令/CI 四关/每日自动化护栏/合规红线）。另建本地数据录入模板 `data/pilot/real_template.csv`（gitignored，无健康数据）便于每日填写——**用户今日数据尚未输入，管线就绪待录入**。四关全绿、106 passed、覆盖率91%；commit+push `5855754`。**待办②（中医师审校 89 条）仍未做**。

## 待办（按优先级自上而下，自动化自上而下取第一个未完成任务）
- [x] 2026-07-28 **TCM 引擎重构（消费理论层 `research/013`）**：将 `TCMMetrics` 拆为 `tcm_theory.py`（纯理论零 HRV：证型目录/辨证要点/舌脉/八纲/复合证型/证据分级/非诊断声明）与 `tcm_hrv_estimator.py`（HRV proxy + 证据等级 + 非诊断声明）。`hrv_engine` 以 `TCMAssessment` 别名保留 `TCMMetrics`，5 主轴分数算法不变（兼容现有测试），新增 primary_syndrome/secondary_syndromes（肝郁脾虚等复合证型）/evidence/disclaimer。新增 `tests/test_tcm_estimator.py`（9 用例验证结构与合规文案）。CI 四关全绿、67 passed、覆盖率 87%。
- [x] 2026-07-29 [smoke] 增强导出/CSV：`data/web_checkin.html` 的 `exportCSV()` 硬编码 `'logs'` 改为统一走 `ST` 常量（单一数据源，杜绝 checkins→logs 类改名断链复发）；smoke 新增「exportCSV store-name contract」检查（全文件禁止硬编码 IndexedDB store 名）；新增 `tests/test_export_csv.py`（5 用例：ST 唯一声明/导出函数存在且挂接按钮/无硬编码 store 名/exportCSV 体内走 ST；Supabase `/rest/v1/checkins` 为远端表名放行）。两份未跟踪本地副本 frontend_dist/ghpages 同步修复（不入库）。四关全绿、120 passed、覆盖率 91%。
- [x] 2026-07-30 [smoke] 为 `hrv_engine` 周期校准 + `hidden_chain_score` 评分补充 pytest 用例：新增 `tests/test_cycle_score_boundaries.py`（18 用例）——① ScoreLevel 四级**精确分界**首次经 `HiddenChainScorer.compute` 端到端验证（80/79、60/59、30/29，含 int 截断路径）；② CyclePhase 五相位 adjustment/label 全映射 + 相位调节项传导（FOLLICULAR vs PREMENSTRUAL 差恰=2 分）+ `analyze_day` 相位分支双输出一致 + DRI 相位表独立传导（差=10 分）；③ CycleCalibrator 跨相位统计独立性（同 rmssd 不同相位 z 值异号）与 z-score 符号/零点校验、fit 后高于基线不低分。四关全绿、138 passed、覆盖率 91.32%。
- [ ] [manual] 修复 Web 表单"提交无响应"：定位 `server.py` 提供的表单源，修复 submit 处理器/JS 事件，保证写入 IndexedDB。验收：需人工浏览器验证。
- [ ] [manual] 修复日期选择器不收起（date picker 不关闭）。需人工浏览器验证。
- [ ] [manual] 修复心情标签(mood tag)点击不生效。需人工浏览器验证。
- [ ] [manual] 部署到 Render.com 提供公网访问：编写 render 部署配置 + 启动说明，本地可起 `server.py` 自检。需凭据/环境变量，标注阻塞项。

- [ ] [manual] 请执业中医师逐条审校 `tcm_ontology.py` 的 89 条辨证要点/舌脉/病因病机（尤其复合证型与外感传变）。验收：需人工，自动化应 skip。
- [x] 2026-07-28 **报告层落地（消费 research/014 本体）**：新增 `src/tcm_report.py`（纯函数 `build_tcm_report` + `render_markdown`，消费 `TCMAssessment`，按高倾向轴的**脏腑/八纲维度**从 `tcm_ontology` 拉同家族证型，区分「HRV 可提示」vs「必须面诊」，输出 `TCMReport` 含 `must_see_clinic` 清单 + 非诊断声明）；新增 `tests/test_tcm_report.py`（6 用例，含「高倾向触发家族 / 需面诊非空 / 低分无家族 / 合规声明」断言）；新增 `tools/tcm_report_demo.py`（CLI 生成样例 md 到 `.workbuddy/tcm_reports/sample.md`，本地不推送，供 7 天后 3 真人数据套用）。四关全绿、86 passed、覆盖率 91%。
- [x] 2026-07-28 **数据接入管线三件套（pilot ready）**：同上（已完成区第 23 条，覆盖数据格式约定 + CSV 加载器 + 批量 runner + 知情同意模板）。

## 阻塞 / 跳过记录（自动化在此追加 `[skip]` 原因）
- 2026-07-29：无跳过。执行首个 `[ ]`（导出/CSV 一致性）。注：任务提及的 `exportCSV` 位于前端 HTML（JS），仓库内唯一被跟踪前端为 `data/web_checkin.html`，故"导出单测"落地为 Python 静态一致性测试（pytest + smoke），frontend_dist/frontend_ghpages 两份未跟踪副本仅本地同步修复。
- 2026-07-30：无跳过。执行首个 `[ ]`（周期校准+评分边界 pytest 补充）。纯增测试文件，未改动任何引擎代码；工作区预存的 README.md.bak / data/index.html 删除与 research/016、017 草稿为非本任务内容，未触碰未入库。
