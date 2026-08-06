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


# 6) Mood-tag end-to-end contract: a ticked mood tag must actually reach the
#    engine. The tags used to be dropped on the server path (analyze_day never
#    forwarded them, checkin() never read them), so clicking a tag changed
#    nothing at all whenever the backend was reachable.
def mood_tag_contract():
    import inspect
    from hrv_engine import HRVEngine, HRVRecord

    sig = inspect.signature(HRVEngine.analyze_day)
    assert "mood_tags" in sig.parameters, "analyze_day() must accept mood_tags"

    rec = HRVRecord(timestamp="2026-01-01", rmssd=42.0, sdnn=0, hf=0, lf=0,
                    heart_rate=68, is_resting=True)
    _, plain = HRVEngine().analyze_day(rec, day_of_cycle=10, baseline_hrv=40.0)
    _, tagged = HRVEngine().analyze_day(rec, day_of_cycle=10, baseline_hrv=40.0,
                                        mood_tags=["irritable", "anxious"])
    assert tagged.liver_depression > plain.liver_depression, \
        "mood tags must move the liver-depression axis (they were being dropped)"

    # the HTTP boundary must read and forward them too
    srv = open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "server.py"),
        encoding="utf-8",
    ).read()
    assert 'data.get("mood_tags")' in srv, "checkin() must read mood_tags from the payload"
    assert "mood_tags" in srv.split("INSERT OR REPLACE")[1][:400], \
        "the check-in INSERT must persist mood_tags"


check("mood tag end-to-end contract", mood_tag_contract)


# 7) Deploy bootstrap contract: Render starts the app with `gunicorn server:app`,
#    which only *imports* the module — it never runs __main__. Schema creation
#    must therefore happen at import scope, and the SQLite file must sit on the
#    mounted disk (HC_DATA_DIR == disk.mountPath) or a redeploy wipes it.
#    Text-only checks, so this stays runnable without flask/pyyaml installed.
def deploy_bootstrap_contract():
    import re
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    srv = open(os.path.join(root, "server.py"), encoding="utf-8").read()
    assert re.search(r"(?m)^init_db\(\)\s*$", srv), \
        "init_db() must run at import scope (gunicorn never executes __main__)"
    assert "HC_DATA_DIR" in srv, "server.py must honour HC_DATA_DIR"
    assert "debug=True" not in srv, "Werkzeug debugger must not be hardcoded on"

    blueprint = os.path.join(root, "render.yaml")
    assert os.path.exists(blueprint), "render.yaml missing"
    y = open(blueprint, encoding="utf-8").read()
    assert "gunicorn server:app" in y, "blueprint start command changed"
    data_dir = re.search(r"key:\s*HC_DATA_DIR\s*\n\s*(?:#.*\n\s*)*value:\s*(\S+)", y)
    mount = re.search(r"mountPath:\s*(\S+)", y)
    assert data_dir and mount, "render.yaml must set HC_DATA_DIR and disk.mountPath"
    assert data_dir.group(1).strip('"') == mount.group(1).strip('"'), \
        "HC_DATA_DIR != disk.mountPath — DB would land on the ephemeral filesystem"


check("deploy bootstrap contract", deploy_bootstrap_contract)


if failed:
    print(f"\nSMOKE TEST FAILED: {len(failed)} check(s)")
    for n, e in failed:
        print(f"  - {n}: {e}")
    sys.exit(1)

print("\nSMOKE TEST PASSED")
sys.exit(0)
