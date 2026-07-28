# Hidden Chain — 每日开发迭代待办 (DEV_BACKLOG)

由每日自动化代理（工作日上午 9 点）消费：**每次只取第一个 `[ ]` 任务执行**，做完标记 `[x]`，并写运行日志到本地 `.workbuddy/daily_dev_log/YYYY-MM-DD.md`（不推送）。

## verify 级别说明
- `[smoke]`：必须 `python3 tests/smoke_test.py` 退出码 0 才允许 commit + push；失败则回退改动并报告。
- `[manual]`：实现后仍以 smoke 为"不破坏引擎"的底线；通过则 commit + push，但 commit 信息以 `[needs-human-verify]` 开头，并在日志标注"需人工在浏览器/凭凭据验证"。

---

## 已完成
- [x] 2026-07-28 建立冒烟自测基线 `tests/smoke_test.py`（import 全引擎 + 校验 ScoreLevel 契约）。

## 待办（按优先级自上而下，自动化自上而下取第一个未完成任务）
- [ ] [smoke] 用 `research/006_TCM-pattern-HRV-quantification.md` 精修 TCM 映射阈值，并以 `research/009_founder_n1_case_study.md` 真实案例回测，断言隐链评分输出与中医辨证一致。验收：在 smoke 中新增 case 回测用例并通过。
- [ ] [smoke] 增强导出/CSV：补齐 `exportCSV` 相关导出路径与 IndexedDB store 名一致性（上次已修 checkins→logs），新增导出单测。验收：smoke 覆盖导出函数。
- [ ] [smoke] 为 `hrv_engine` 周期校准 + `hidden_chain_score` 评分补充 pytest 用例（覆盖 ScoreLevel 边界、周期相位分支）。
- [ ] [manual] 修复 Web 表单"提交无响应"：定位 `server.py` 提供的表单源，修复 submit 处理器/JS 事件，保证写入 IndexedDB。验收：需人工浏览器验证。
- [ ] [manual] 修复日期选择器不收起（date picker 不关闭）。需人工浏览器验证。
- [ ] [manual] 修复心情标签(mood tag)点击不生效。需人工浏览器验证。
- [ ] [manual] 部署到 Render.com 提供公网访问：编写 render 部署配置 + 启动说明，本地可起 `server.py` 自检。需凭据/环境变量，标注阻塞项。

## 阻塞 / 跳过记录（自动化在此追加 `[skip]` 原因）
