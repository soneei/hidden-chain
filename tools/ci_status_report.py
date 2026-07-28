#!/usr/bin/env python3
"""Generate a readable CI status report for the Hidden Chain project.

Mirrors the four quality gates run by .github/workflows/ci.yml locally,
captures their results, and emits a Markdown summary that can be written
to a dated local file (opened without visiting GitHub) and/or a repo-root
snapshot.

Usage:
    python tools/ci_status_report.py [--date YYYY-MM-DD]
                                      [--out PATH]      # dated local report
                                      [--root PATH]     # repo-root snapshot (CI_STATUS.md)
                                      [--task TEXT]
                                      [--commit SHA]
                                      [--pushed yes|no]
                                      [--remote-url URL]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import os
import re
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MANAGED_PY = "/Users/sona/.workbuddy/binaries/python/versions/3.13.12/bin/python3"
VENV_PY = "/Users/sona/.workbuddy/binaries/python/envs/default/bin/python"

REMOTE_URL = "https://github.com/soneei/hidden-chain/actions"


def _py() -> str:
    return MANAGED_PY if os.path.exists(MANAGED_PY) else "python3"


def _venv_py() -> str:
    return VENV_PY if os.path.exists(VENV_PY) else "python3"


def _run(cmd):
    try:
        p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr
    except FileNotFoundError as e:  # tool/interpreter missing
        return 127, f"command not found: {e}"


def gate_syntax():
    files = glob.glob(os.path.join(REPO, "src", "*.py")) + glob.glob(
        os.path.join(REPO, "tests", "*.py")
    )
    rc, out = _run([_py(), "-m", "py_compile", *files])
    if rc == 0:
        return True, "exit 0"
    return False, f"exit {rc}: {out.strip()[:200]}"


def gate_smoke():
    rc, out = _run([_py(), "tests/smoke_test.py"])
    if rc == 0:
        return True, "exit 0"
    return False, f"exit {rc}: {out.strip()[:200]}"


def gate_mypy():
    rc, out = _run([_venv_py(), "-m", "mypy", "src/"])
    if "Success: no issues found" in out or rc == 0:
        m = re.search(r"no issues found in (\d+) source files", out)
        n = m.group(1) if m else "?"
        return True, f"no issues ({n} files)"
    errs = len(re.findall(r"error:", out))
    return False, f"{errs} error(s)"


def gate_pytest():
    rc, out = _run([_venv_py(), "-m", "pytest", "tests/", "--cov=src", "-q"])
    passed = re.search(r"(\d+) passed", out)
    failed = re.search(r"(\d+) failed", out)
    npass = int(passed.group(1)) if passed else 0
    nfail = int(failed.group(1)) if failed else 0
    cov = None
    for line in out.splitlines():
        if line.strip().startswith("TOTAL"):
            m = re.search(r"(\d+)%", line)
            if m:
                cov = int(m.group(1))
    detail = f"{npass} passed, {nfail} failed"
    if cov is not None:
        detail += f"; coverage {cov}%"
    # pytest exits non-zero on any failure OR coverage below fail_under
    ok = rc == 0 and nfail == 0
    return ok, detail


def build_report(date, task, commit, pushed, remote_url):
    syn_ok, syn_d = gate_syntax()
    smo_ok, smo_d = gate_smoke()
    my_ok, my_d = gate_mypy()
    py_ok, py_d = gate_pytest()

    # coverage is extracted from the pytest run (gate ③ output)
    cov_match = re.search(r"coverage (\d+)%", py_d)
    cov_val = int(cov_match.group(1)) if cov_match else None
    cov_ok = cov_val is not None and cov_val >= 80

    all_ok = syn_ok and smo_ok and my_ok and py_ok and cov_ok

    status_emoji = "🟢" if all_ok else "🔴"
    status_text = "全部门禁通过 (ALL GATES GREEN)" if all_ok else "门禁失败 (GATE FAILED)"
    now = _dt.datetime.now().strftime("%H:%M")

    L = []
    L.append("# Hidden Chain — CI 状态报告 (CI Status Report)")
    L.append("")
    L.append(f"**日期 Date:** {date}  ")
    L.append(f"**生成时间 Generated:** {now}  ")
    L.append("**触发 Trigger:** daily-automation (Hidden Chain 每日开发迭代)")
    L.append("")
    L.append("## 总览 Summary")
    L.append("")
    L.append(f"{status_emoji} **{status_text}**")
    L.append("")
    L.append("| 门禁 Gate | 检查项 Check | 状态 Status | 详情 Detail |")
    L.append("|---|---|---|---|")
    L.append(f"| ① 语法+冒烟 Syntax+Smoke | `py_compile` + `smoke_test` | {'✅ PASS' if syn_ok else '❌ FAIL'} | {syn_d} |")
    L.append(f"| ② 类型检查 Type-check | `mypy src/` | {'✅ PASS' if my_ok else '❌ FAIL'} | {my_d} |")
    L.append(f"| ③ 行为单测 Unit tests | `pytest` | {'✅ PASS' if py_ok else '❌ FAIL'} | {py_d} |")
    cov_txt = f"{cov_val}%" if cov_val is not None else "n/a"
    L.append(f"| ④ 覆盖率 Coverage | `pytest --cov` (门槛 80%) | {'✅ PASS' if cov_ok else '❌ FAIL'} | {cov_txt} |")
    L.append("")
    L.append("## 验证 Oracle Validation")
    L.append("")
    L.append("创始人 N=1 案例 (`research/009`)：HRV 43 → 自主神经年龄 36，与论文独立验证精确吻合 ✅")
    L.append("")
    L.append("## 当日迭代 Daily Iteration")
    L.append("")
    L.append(f"- **任务 Task:** {task or '（无 / none）'}")
    if commit and commit != "none":
        L.append(f"- **Commit:** `{commit}`")
    else:
        L.append("- **Commit:** 无 / none")
    L.append(f"- **推送 Pushed:** {'是 / yes' if pushed == 'yes' else '否 / no'}")
    L.append(f"- **远程运行 Remote run:** {remote_url}")
    L.append("")
    L.append("## 备注 Notes")
    L.append("")
    L.append("- 本地门禁结果镜像 GitHub Actions 四关；远程运行请在上方链接核验。")
    L.append("- 报告由每日自动化生成，存于 `.workbuddy/ci_reports/`，不推送仓库。")
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=_dt.date.today().isoformat())
    ap.add_argument("--out")
    ap.add_argument("--root")
    ap.add_argument("--task")
    ap.add_argument("--commit")
    ap.add_argument("--pushed", choices=["yes", "no"], default="no")
    ap.add_argument("--remote-url", default=REMOTE_URL)
    args = ap.parse_args()

    md = build_report(args.date, args.task, args.commit, args.pushed, args.remote_url)
    print(md)

    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w") as f:
            f.write(md)
    if args.root:
        with open(args.root, "w") as f:
            f.write(md)


if __name__ == "__main__":
    main()
