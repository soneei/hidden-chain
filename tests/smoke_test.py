#!/usr/bin/env python3
"""
Hidden Chain — minimal smoke test (no external deps required)
=============================================================
Safety net for the daily dev-iteration automation.

What it checks:
  1. All core engine modules import cleanly (catches syntax / broken-import
     regressions from any edit).
  2. The HiddenChainScore tier contract holds (ScoreLevel enum values).

Run:  python3 tests/smoke_test.py
Exit: 0 = pass, 1 = fail
"""
import sys
import os
import traceback

# Make src/ importable (modules use bare imports, e.g. `from hidden_chain_score import ...`)
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
sys.path.insert(0, os.path.abspath(SRC))

failed = []


def check(name, fn):
    try:
        fn()
        print(f"  OK   {name}")
    except Exception as e:
        print(f"  FAIL {name}: {e}")
        failed.append((name, repr(e)))


# 1) Import all core modules (must not raise)
check("import hrv_engine", lambda: __import__("hrv_engine"))
check("import hidden_chain_score", lambda: __import__("hidden_chain_score"))
check("import data_loader", lambda: __import__("data_loader"))
check("import device_adapters", lambda: __import__("device_adapters"))


# 2) Functional contract: scoring tier mapping must stay stable
def functional_contract():
    from hidden_chain_score import ScoreLevel
    assert ScoreLevel.PURPLE.value == "purple", "PURPLE tier changed"
    assert ScoreLevel.GREEN.value == "green", "GREEN tier changed"
    assert ScoreLevel.YELLOW.value == "yellow", "YELLOW tier changed"
    assert ScoreLevel.RED.value == "red", "RED tier changed"
    # label property must exist and be non-empty
    for lvl in ScoreLevel:
        assert getattr(lvl, "label", ""), f"{lvl.name} missing label"


check("HiddenChainScore tier contract", functional_contract)


# 3) Export path contract: the check-in frontend's exportCSV() must use the
#    ST store-name constant (guards the historical checkins->logs mismatch).
def export_csv_contract():
    import re
    frontend = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "data", "web_checkin.html"
    )
    html = open(frontend, encoding="utf-8").read()
    assert re.search(r"function\s+exportCSV\s*\(", html), "exportCSV() missing"
    hardcoded = []
    for pat in (
        r"\.transaction\(\s*['\"]\w+['\"]",
        r"\.objectStore\(\s*['\"]\w+['\"]",
        r"createObjectStore\(\s*['\"]\w+['\"]",
    ):
        hardcoded += re.findall(pat, html)
    assert not hardcoded, f"hardcoded IndexedDB store name(s): {hardcoded}"


check("exportCSV store-name contract", export_csv_contract)


if failed:
    print(f"\nSMOKE TEST FAILED: {len(failed)} check(s)")
    for n, e in failed:
        print(f"  - {n}: {e}")
    sys.exit(1)

print("\nSMOKE TEST PASSED")
sys.exit(0)
