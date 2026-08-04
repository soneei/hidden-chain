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


# 4) Check-in persistence contract: submitCheckin() must never silently drop a
#    check-in. save() has to await the DB open and reject on failure, and both
#    call sites must go through saveOrWarn() so the user sees an error.
def checkin_persistence_contract():
    import re
    frontend = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "data", "web_checkin.html"
    )
    html = open(frontend, encoding="utf-8").read()
    assert re.search(r"async\s+function\s+save\s*\(", html), "save() must be async"
    assert re.search(
        r"async\s+function\s+save\s*\([^)]*\)\s*\{[^}]*await\s+idb\(\)", html
    ), "save() must await idb() instead of bailing on a not-yet-open db"
    assert "function saveOrWarn" in html, "saveOrWarn() missing"
    assert not re.search(
        r"(?<!OrWarn)\bsave\(\{", html
    ), "check-in write must go through saveOrWarn(), not a bare fire-and-forget save()"
    assert re.search(r"function\s+submitCheckin\s*\([^)]*\)\s*\{\s*try", html), \
        "submitCheckin() must wrap its body in try/catch so sync errors surface"


check("check-in persistence contract", checkin_persistence_contract)


# 5) Date picker dismissal contract: the native <input type="date"> popup must
#    be closable even when `change` never fires (re-picking the same date), and
#    the blur must be deferred so the browser does not swallow it.
def date_picker_dismissal_contract():
    import re
    frontend = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "data", "web_checkin.html"
    )
    html = open(frontend, encoding="utf-8").read()
    assert "function closeDatePicker" in html, "closeDatePicker() missing"
    body = re.search(r"function\s+closeDatePicker\s*\([^)]*\)\s*\{(.*?)\n\}", html, re.S)
    assert body, "could not locate closeDatePicker() body"
    assert re.search(r"setTimeout\(", body.group(1)), \
        "closeDatePicker() must defer blur() one macrotask, not blur synchronously"
    assert re.search(r"\.blur\(\)", body.group(1)), "closeDatePicker() must blur the input"
    assert not re.search(
        r"addEventListener\(\s*'change'\s*,\s*\(\)\s*=>\s*\{[^}]*\.blur\(\)", html
    ), "blur() must not be called synchronously inside a change handler"
    assert "'Escape'" in html, "no Escape-key fallback to dismiss the date picker"
    assert re.search(r"addEventListener\(\s*'pointerdown'", html), \
        "no outside-tap fallback to dismiss the date picker"


check("date picker dismissal contract", date_picker_dismissal_contract)


if failed:
    print(f"\nSMOKE TEST FAILED: {len(failed)} check(s)")
    for n, e in failed:
        print(f"  - {n}: {e}")
    sys.exit(1)

print("\nSMOKE TEST PASSED")
sys.exit(0)
