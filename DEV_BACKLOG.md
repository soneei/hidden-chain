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

## 待办（按优先级自上而下，自动化自上而下取第一个未完成任务）
- [x] 2026-07-28 **TCM 引擎重构（消费理论层 `research/013`）**：将 `TCMMetrics` 拆为 `tcm_theory.py`（纯理论零 HRV：证型目录/辨证要点/舌脉/八纲/复合证型/证据分级/非诊断声明）与 `tcm_hrv_estimator.py`（HRV proxy + 证据等级 + 非诊断声明）。`hrv_engine` 以 `TCMAssessment` 别名保留 `TCMMetrics`，5 主轴分数算法不变（兼容现有测试），新增 primary_syndrome/secondary_syndromes（肝郁脾虚等复合证型）/evidence/disclaimer。新增 `tests/test_tcm_estimator.py`（9 用例验证结构与合规文案）。CI 四关全绿、67 passed、覆盖率 87%。
- [ ] [smoke] 增强导出/CSV：补齐 `exportCSV` 相关导出路径与 IndexedDB store 名一致性（上次已修 checkins→logs），新增导出单测。验收：smoke 覆盖导出函数。
- [ ] [smoke] 为 `hrv_engine` 周期校准 + `hidden_chain_score` 评分补充 pytest 用例（覆盖 ScoreLevel 边界、周期相位分支）。
- [ ] [manual] 修复 Web 表单"提交无响应"：定位 `server.py` 提供的表单源，修复 submit 处理器/JS 事件，保证写入 IndexedDB。验收：需人工浏览器验证。
- [ ] [manual] 修复日期选择器不收起（date picker 不关闭）。需人工浏览器验证。
- [ ] [manual] 修复心情标签(mood tag)点击不生效。需人工浏览器验证。
- [ ] [manual] 部署到 Render.com 提供公网访问：编写 render 部署配置 + 启动说明，本地可起 `server.py` 自检。需凭据/环境变量，标注阻塞项。

- [ ] [manual] 请执业中医师逐条审校 `tcm_ontology.py` 的 89 条辨证要点/舌脉/病因病机（尤其复合证型与外感传变）。验收：需人工，自动化应 skip。
- [x] 2026-07-28 **报告层落地（消费 research/014 本体）**：新增 `src/tcm_report.py`（纯函数 `build_tcm_report` + `render_markdown`，消费 `TCMAssessment`，按高倾向轴的**脏腑/八纲维度**从 `tcm_ontology` 拉同家族证型，区分「HRV 可提示」vs「必须面诊」，输出 `TCMReport` 含 `must_see_clinic` 清单 + 非诊断声明）；新增 `tests/test_tcm_report.py`（6 用例，含「高倾向触发家族 / 需面诊非空 / 低分无家族 / 合规声明」断言）；新增 `tools/tcm_report_demo.py`（CLI 生成样例 md 到 `.workbuddy/tcm_reports/sample.md`，本地不推送，供 7 天后 3 真人数据套用）。四关全绿、86 passed、覆盖率 91%。
- [ ] [manual] 接入 3 真人 7 天数据：把真实 HRV 采集（设备/CSV）送进 `estimate_tcm` → `build_tcm_report` → `render_markdown`，每人生成一份报告；需先确认数据格式 + 知情同意/匿名 ID。验收：需人工核对数据管线。

## 阻塞 / 跳过记录（自动化在此追加 `[skip]` 原因）
