"""
Regression tests for the dropped ``sleep_hours`` / ``resting_hr`` inputs.
=========================================================================

Same defect family as the mood-tag bug fixed on 2026-08-05, found while
fixing it. ``TCMAssessment.from_hrv`` has always accepted ``resting_hr``
and ``sleep_hours``:

  * ``_qi_score``     — resting HR > 80 → +20, > 70 → +10; sleep < 6h → +15
                        (both suppressed once qi_raw >= 70, the de-saturation
                        guard added during the 2026-07-28 calibration pass)
  * ``_liver_score``  — sleep < 5h → +10
  * ``_spleen_score`` — rmssd < 35 *and* resting HR > 65 → +15

...but ``HRVEngine.analyze_day()`` called ``from_hrv(rmssd, norm, recovery)``
and forwarded neither, so a user could enter a resting HR of 88 bpm on four
hours of sleep and get output byte-identical to 60 bpm on eight hours.

Two extra wrinkles this locks down, both of which made the bug invisible:

  * ``HRVRecord`` **already carries** ``heart_rate``, and ``run_engine_for_user``
    already filled it from ``daily_log.resting_hr`` — the value was sitting on
    the record the whole time and simply never read. The fallback added with
    the fix must therefore fire without the caller passing anything, but only
    for ``is_resting`` records: an event record's heart rate is a mid-exercise
    reading, not a resting HR.
  * As with the mood tags, the frontend's *offline* path (``computeTCMOffline``
    and the Pyodide branch) passed both values correctly, so the fields only
    broke once the backend was actually reachable.
"""
import os
import sqlite3
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SRC = os.path.join(REPO, "src")
sys.path.insert(0, SRC)
sys.path.insert(0, REPO)

import pytest

from hrv_engine import HRVEngine, HRVRecord
from tcm_hrv_estimator import HRVFeatures, estimate_tcm


def _rec(rmssd: float = 44.0, hr: float = 68.0, resting: bool = True) -> HRVRecord:
    return HRVRecord(
        timestamp="2026-08-10", rmssd=rmssd, sdnn=0, hf=0, lf=0,
        heart_rate=hr, is_resting=resting,
    )


def _run(record: HRVRecord | None = None, **kw):
    _, hcs = HRVEngine().analyze_day(
        record if record is not None else _rec(),
        day_of_cycle=10, baseline_hrv=40.0, **kw
    )
    return hcs


# ──────────────────────────────────────────────
# 1) Engine layer — analyze_day must forward both inputs
# ──────────────────────────────────────────────

def test_analyze_day_accepts_new_kwargs():
    import inspect
    sig = inspect.signature(HRVEngine.analyze_day)
    for p in ("resting_hr", "sleep_hours"):
        assert p in sig.parameters, (
            f"analyze_day() must accept {p}, otherwise the server cannot forward it"
        )


def test_high_resting_hr_raises_qi_blood_axis():
    """THE BUG: 60 bpm and 88 bpm used to score identically."""
    calm = _run(_rec(hr=60))
    fast = _run(_rec(hr=88))
    assert fast.qi_blood > calm.qi_blood


def test_resting_hr_bands_are_ordered():
    """> 80 → +20, > 70 → +10, else +0 — monotonic, not a single on/off flag."""
    low = _run(_rec(hr=65)).qi_blood
    mid = _run(_rec(hr=75)).qi_blood
    high = _run(_rec(hr=85)).qi_blood
    assert low < mid < high


def test_short_sleep_raises_qi_blood_axis():
    rested = _run(sleep_hours=8.0)
    short = _run(sleep_hours=5.5)
    assert short.qi_blood > rested.qi_blood


def test_very_short_sleep_raises_liver_axis():
    """< 5h hits the liver-depression axis on top of the qi-blood penalty."""
    rested = _run(sleep_hours=8.0)
    deprived = _run(sleep_hours=4.0)
    assert deprived.liver_depression > rested.liver_depression


def test_low_hrv_plus_fast_hr_raises_spleen_axis():
    """_spleen_score needs rmssd < 35 *and* resting HR > 65."""
    slow_hr = _run(_rec(rmssd=30.0, hr=60))
    fast_hr = _run(_rec(rmssd=30.0, hr=70))
    assert fast_hr.spleen_deficiency > slow_hr.spleen_deficiency


def test_explicit_resting_hr_overrides_record_heart_rate():
    """An explicit argument wins over the value carried on the record."""
    from_record = _run(_rec(hr=88))
    overridden = _run(_rec(hr=88), resting_hr=60.0)
    assert overridden.qi_blood < from_record.qi_blood


def test_resting_hr_falls_back_to_record_heart_rate():
    """The record already carried heart_rate; not reading it *was* the bug."""
    assert _run(_rec(hr=88)).qi_blood > _run(_rec(hr=60)).qi_blood


def test_non_resting_record_heart_rate_is_ignored():
    """A mid-event heart rate is not a resting HR and must not be adopted."""
    event = _run(_rec(hr=88, resting=False))
    calm = _run(_rec(hr=60, resting=False))
    assert event.qi_blood == calm.qi_blood


def test_zero_heart_rate_placeholder_is_ignored():
    """server.py builds records with 0 placeholders; 0 bpm is not a measurement."""
    assert _run(_rec(hr=0)).qi_blood == _run(_rec(hr=60)).qi_blood


def test_omitting_both_keeps_legacy_behaviour():
    """Back-compat: no kwargs + no usable record HR == the pre-fix numbers."""
    baseline = _run(_rec(hr=0))
    explicit_none = _run(_rec(hr=0), resting_hr=None, sleep_hours=None)
    assert baseline.score == explicit_none.score
    assert baseline.qi_blood == explicit_none.qi_blood


def test_desaturation_guard_still_holds():
    """Severe rmssd (qi_raw >= 70) must not stack HR/sleep bonuses.

    Removing the guard would re-break the 2026-07-28 calibration finding:
    a saturated qi axis drowns out the more specific liver/spleen axes.
    """
    severe = HRVFeatures(resting_rmssd=25.0, normalized_hrv=0.0,
                         recovery_classification="normal")
    severe_loaded = HRVFeatures(resting_rmssd=25.0, normalized_hrv=0.0,
                                recovery_classification="normal",
                                resting_hr=95.0, sleep_hours=3.0)
    assert estimate_tcm(severe).qi_blood_deficiency == \
        estimate_tcm(severe_loaded).qi_blood_deficiency


def test_sleep_and_hr_shift_the_final_score():
    """Not just the axes — the headline number must move too."""
    good = _run(_rec(hr=60), sleep_hours=8.0)
    bad = _run(_rec(hr=88), sleep_hours=4.0)
    assert bad.score != good.score


# ──────────────────────────────────────────────
# 2) Payload parsing — optional numeric fields
# ──────────────────────────────────────────────

def test_parse_optional_float_handles_client_variants():
    server = pytest.importorskip("server")
    p = server.parse_optional_float
    assert p(7.5) == 7.5
    assert p(7) == 7.0
    assert p("6.5") == 6.5
    assert p("  6.5  ") == 6.5
    assert p(None) is None
    assert p("") is None, "an empty string must not become 0.0 hours of sleep"
    assert p("   ") is None
    assert p("abc") is None, "garbage must degrade to None, not raise"
    assert p([]) is None
    assert p(True) is None, "bool is an int subclass — must not sneak through as 1.0"


# ──────────────────────────────────────────────
# 3) Server path — stored value must reach the engine
# ──────────────────────────────────────────────

@pytest.fixture()
def server_app(tmp_path, monkeypatch):
    server = pytest.importorskip("server")
    monkeypatch.setattr(server, "DB_PATH", str(tmp_path / "test.db"))
    server.init_db()
    server.app.config.update(TESTING=True)
    return server


def _post(server_app, user, *, rhr, sleep, date="2026-08-10"):
    client = server_app.app.test_client()
    return client.post("/api/checkin", json={
        "user_id": user, "hrv_rmssd": 44.0, "resting_hr": rhr,
        "cycle_day": 10, "mood_score": 6, "sleep_hours": sleep, "date": date,
    })


def test_checkin_persists_sleep_hours(server_app):
    assert _post(server_app, "u_sleep", rhr=68, sleep=6.5).status_code == 200
    conn = sqlite3.connect(server_app.DB_PATH)
    stored = conn.execute(
        "SELECT sleep_hours FROM daily_log WHERE user_id='u_sleep'"
    ).fetchone()[0]
    conn.close()
    assert stored == 6.5


def test_checkin_blank_sleep_stored_as_null(server_app):
    """An empty string used to land in the column and blow up on read-back."""
    assert _post(server_app, "u_blank", rhr=68, sleep="").status_code == 200
    conn = sqlite3.connect(server_app.DB_PATH)
    stored = conn.execute(
        "SELECT sleep_hours FROM daily_log WHERE user_id='u_blank'"
    ).fetchone()[0]
    conn.close()
    assert stored is None


def test_checkin_sleep_and_hr_change_tcm_output(server_app):
    """END-TO-END: the exact bug, over HTTP. Same HRV → different TCM."""
    rested = _post(server_app, "u_rested", rhr=60, sleep=8.0).get_json()
    strained = _post(server_app, "u_strained", rhr=88, sleep=4.0).get_json()
    assert rested["tcm"] != strained["tcm"], (
        "identical HRV with a very different resting HR and sleep debt must not "
        "produce identical TCM axes — that was the bug"
    )
    assert strained["tcm"]["qi_blood"] > rested["tcm"]["qi_blood"]


LEGACY_SCHEMA = """CREATE TABLE daily_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT,
    hrv_rmssd REAL, resting_hr REAL, cycle_day INTEGER, mood_score INTEGER,
    mood_tags TEXT, sleep_hours REAL, event_label TEXT, hcs_score INTEGER,
    phase TEXT, qi_blood REAL, liver_depression REAL, spleen_deficiency REAL)"""


def test_engine_reads_sleep_from_the_matching_row(tmp_path, monkeypatch):
    """Rows without a cycle_day are skipped when building records.

    The stored sleep_hours has to stay aligned with that *filtered* list, or
    the engine silently scores today using some other day's sleep. Today's
    schema declares ``cycle_day NOT NULL``, so this is only reachable on a
    legacy / hand-edited DB — which is exactly why the defensive ``continue``
    in ``run_engine_for_user`` exists, and why the parallel list has to track it.
    """
    server = pytest.importorskip("server")
    db = tmp_path / "legacy.db"
    conn = sqlite3.connect(db)
    conn.execute(LEGACY_SCHEMA)
    conn.execute(
        "INSERT INTO daily_log (user_id, date, hrv_rmssd, resting_hr, cycle_day, "
        "sleep_hours) VALUES ('u', '2026-08-12', 44.0, 60, 10, 8.0)"
    )
    # Sorts *after* the analysed row, so a naive rows[-1] lookup would grab
    # this row's 3h sleep while records[-1] is still the 08-12 check-in.
    conn.execute(
        "INSERT INTO daily_log (user_id, date, hrv_rmssd, resting_hr, cycle_day, "
        "sleep_hours) VALUES ('u', '2026-08-13', 44.0, 60, NULL, 3.0)"
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(server, "DB_PATH", str(db))

    hcs, _, _, error = server.run_engine_for_user("u")
    assert error is None

    clean = tmp_path / "clean.db"
    conn = sqlite3.connect(clean)
    conn.execute(LEGACY_SCHEMA)
    conn.execute(
        "INSERT INTO daily_log (user_id, date, hrv_rmssd, resting_hr, cycle_day, "
        "sleep_hours) VALUES ('u', '2026-08-12', 44.0, 60, 10, 8.0)"
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(server, "DB_PATH", str(clean))
    expected, _, _, _ = server.run_engine_for_user("u")

    assert hcs.qi_blood == expected.qi_blood, (
        "the cycle_day-less row's 3h sleep leaked into the analysed day"
    )


def test_dashboard_path_also_sees_the_stored_values(server_app):
    """/api/dashboard passes no kwargs — it must still pick both up from SQLite."""
    _post(server_app, "u_dash_bad", rhr=88, sleep=4.0)
    _post(server_app, "u_dash_ok", rhr=60, sleep=8.0)
    client = server_app.app.test_client()
    strained = client.get("/api/dashboard/u_dash_bad").get_json()
    rested = client.get("/api/dashboard/u_dash_ok").get_json()
    assert strained["score"] != rested["score"], (
        "dashboard re-ran the engine without the stored resting HR / sleep hours"
    )
