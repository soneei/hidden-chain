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

## 待办（按优先级自上而下，自动化自上而下取第一个未完成任务）
- [ ] [smoke] **TCM 引擎重构（消费理论层 `research/013`）**：把 `src/hrv_engine.py::TCMMetrics.from_hrv` 拆为 `tcm_theory`（纯理论、零 HRV，消费 013 第 3/4 节证型目录 + 辨证要点 + 复合证型）与 `tcm_hrv_estimator`（消费 research/006、011，HRV 特征作 proxy、带证据等级 + 非诊断声明「证候倾向性评估」）。输出由 5 独立分数改为「主证 + 兼证 + 证据等级 + 覆盖缺失声明」。验收：新增 test 断言 estimator 输出结构与非诊断文案；过 CI 四关（py_compile / smoke / pytest-cov≥80% / mypy）。
- [ ] [smoke] 增强导出/CSV：补齐 `exportCSV` 相关导出路径与 IndexedDB store 名一致性（上次已修 checkins→logs），新增导出单测。验收：smoke 覆盖导出函数。
- [ ] [smoke] 为 `hrv_engine` 周期校准 + `hidden_chain_score` 评分补充 pytest 用例（覆盖 ScoreLevel 边界、周期相位分支）。
- [ ] [manual] 修复 Web 表单"提交无响应"：定位 `server.py` 提供的表单源，修复 submit 处理器/JS 事件，保证写入 IndexedDB。验收：需人工浏览器验证。
- [ ] [manual] 修复日期选择器不收起（date picker 不关闭）。需人工浏览器验证。
- [ ] [manual] 修复心情标签(mood tag)点击不生效。需人工浏览器验证。
- [ ] [manual] 部署到 Render.com 提供公网访问：编写 render 部署配置 + 启动说明，本地可起 `server.py` 自检。需凭据/环境变量，标注阻塞项。

## 阻塞 / 跳过记录（自动化在此追加 `[skip]` 原因）
