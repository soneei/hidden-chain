# 部署到 Render.com（公网访问）

配置文件：[`render.yaml`](./render.yaml)（Render Blueprint）。本文说明本地自检、部署步骤、
需要人工准备的凭据，以及**上线前必须先解决的阻塞项**。

> ⚠️ **当前状态：配置就绪，但不建议直接上公网。**
> 见下方「阻塞项」P0——API 没有任何鉴权，公网部署等同于把打卡人的 HRV / 经期 /
> 情志标签开放给任何知道 URL 的人。自动化只负责把部署配置和说明写好，**是否真的
> 部署由人来决定**。

---

## 一、本地自检（不需要任何 Render 账号）

```bash
cd /Users/sona/Projects/hidden-chain
pip install -r requirements.txt

# 1) 开发模式（Flask 自带服务器）
python server.py                 # → http://localhost:5000
HC_DEBUG=1 python server.py      # 需要热重载/错误回溯时才开

# 2) 生产模式自检：用与 Render 完全相同的启动命令
PORT=5000 HC_DATA_DIR=./data gunicorn server:app --bind 0.0.0.0:$PORT --workers 1 --timeout 60

# 3) 冒烟：另开一个终端
curl -s localhost:5000/ | head -5
curl -s -X POST localhost:5000/api/checkin \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"selftest","hrv_rmssd":42,"resting_hr":68,"cycle_day":10,"mood_tags":"anxious"}'
```

第 2 步能起来是关键：`gunicorn server:app` 只 import 模块拿 `app`，**不会**执行
`if __name__ == "__main__"` 分支。历史上建表就写在那个分支里，线上第一个请求必然
`no such table: daily_log`；现在 `init_db()` 在 import 时执行（幂等），这条路径才通。

## 二、环境变量

| 变量 | 线上值 | 作用 | 不设会怎样 |
|---|---|---|---|
| `PORT` | Render 自动注入 | gunicorn 绑定端口 | 本地默认 5000 |
| `HC_DATA_DIR` | `/var/data` | SQLite 所在目录，**必须等于 `render.yaml` 的 `disk.mountPath`** | 落到容器临时盘，重启即清零 |
| `HC_DEBUG` | `0` | Werkzeug 调试器开关 | 默认关；`=1` 才开，公网绝不可开 |
| `PYTHON_VERSION` | `3.12.6` | 引擎需 ≥3.10（PEP 604 语法） | Render 默认版本可能过低 |

## 三、部署步骤

1. Render Dashboard → **New → Blueprint** → 授权 GitHub → 选 `soneei/hidden-chain`。
2. Render 读取 `render.yaml`，确认服务名 `hidden-chain`、计划 `starter`、磁盘 1 GB。
3. **Apply** → 首次构建约 2–3 分钟。
4. 访问 `https://hidden-chain-<随机后缀>.onrender.com/` 应看到打卡表单。
5. `autoDeploy: false`，之后每次上线需在 Dashboard 手动点 **Manual Deploy**。

回滚：Dashboard → Deploys → 选上一个成功版本 → **Rollback**。挂载磁盘上的数据不受影响。

## 四、需要人工准备（自动化无法代办）

- Render 账号 + 与 GitHub 的授权（OAuth，需人工点同意）。
- **付费计划**：`starter`（约 $7/月）。free 计划不支持持久磁盘，且 15 分钟无请求即休眠，
  冷启动 30 秒以上——打卡数据会随休眠/部署一起消失，不可用于真实记录。
- 自定义域名 / DNS（可选）。

## 五、阻塞项（上线前必须处理）

**P0 — 无鉴权，任何人可读写任何人的健康数据。**
`/api/dashboard/<user_id>` 只凭路径里的 `user_id` 返回全部历史，`/api/checkin` 也接受
任意 `user_id` 写入。`user_id` 是前端自填的明文字符串，可枚举、可伪造。公网部署前
至少要有：登录态或签名 token、按用户隔离查询、写入限流。**在此之前只应部署在内网或
本机。**

**P1 — SQLite + 单 worker 是临时方案。**
必须 `--workers 1`（多 worker 并发写会 `database is locked`），因此无法水平扩容；
磁盘快照也依赖 Render 的磁盘备份。真要多人用，存储层应换 Postgres（Render 有托管实例），
`server.py` 里的裸 `sqlite3.connect` 需相应抽象。

**P2 — 健康数据合规。**
Render 默认区域在境外（本配置选了 `singapore`）。真实用户的 HRV / 经期 / 情志属于个人
敏感信息，跨境存储需评估合规，并需要有知情同意（模板已有：
`research/015_pilot_consent_template.md`）与数据删除路径（目前**没有**删除接口）。

**P3 — 无备份、无监控。** 磁盘只有 Render 侧快照，仓库里没有导出/恢复脚本；
`healthCheckPath: /` 只能看进程活没活，看不出引擎是否算错。

### 更保守的替代方案

只是想「公网能打开、自己用」，可以走已有的 **GitHub Pages 静态版**（`gh-pages` 分支，
Pyodide 在浏览器内跑引擎，数据存 IndexedDB **不出本机**）。它没有上述 P0/P1/P2 问题，
代价是没有服务端历史与跨设备同步。
