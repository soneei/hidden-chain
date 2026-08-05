"""
Regression tests for the "mood tag click does nothing" bug.
===========================================================

Root cause (fixed 2026-08-05) — the tags were dropped in **four** places along
the server path, so on the primary flow (``python server.py`` → localhost) a
user could tick *Anxious* / *Exhausted* and the score, the five TCM axes and
the syndrome report came back byte-identical:

  1. ``HRVEngine.analyze_day()`` called ``TCMMetrics.from_hrv(rmssd, norm,
     recovery)`` and never forwarded ``mood_tags`` — even though
     ``from_hrv``/``estimate_tcm`` have supported the argument all along
     (``_liver_score`` +15 for irritable/anxious, ``_spleen_score`` +20
     exhausted / +15 brain_fog, ``_phlegm_score`` +15 for the combo).
  2. ``server.checkin()`` never read ``mood_tags`` off the JSON payload,
     although the frontend has always sent it (``mood_tags:tags``).
  3. The ``daily_log`` table had no ``mood_tags`` column.
  4. ``run_engine_for_user()`` re-read only hrv/rhr/cycle_day/date from SQLite,
     so nothing subjective could reach the engine anyway.

The frontend's *offline* fallback (``computeTCMOffline`` / the Pyodide path)
did pass the tags — which is why the feature looked like it worked whenever
the backend was unreachable, and only "stopped working" once the server ran.

These tests lock all four layers: engine kwarg forwarding, payload parsing,
SQLite persistence + legacy migration, and an end-to-end HTTP assertion that
identical HRV with different tags produces *different* TCM output.
"""
import os
import re
import sqlite3
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SRC = os.path.join(REPO, "src")
sys.path.insert(0, SRC)
sys.path.insert(0, REPO)

import pytest

from hrv_engine import HRVEngine, HRVRecord

FRONTEND = os.path.join(REPO, "data", "web_checkin.html")


def _rec(rmssd: float = 42.0) -> HRVRecord:
    return HRVRecord(
        timestamp="2026-08-05", rmssd=rmssd, sdnn=0, hf=0, lf=0,
        heart_rate=68, is_resting=True,
    )


def _axes(mood_tags=None):
    """Run one day through a fresh engine and return the three affected axes."""
    _, hcs = HRVEngine().analyze_day(
        _rec(), day_of_cycle=10, baseline_hrv=40.0, mood_tags=mood_tags
    )
    return hcs


# ──────────────────────────────────────────────
# 1) Engine layer — analyze_day must forward mood_tags
# ──────────────────────────────────────────────

def test_analyze_day_accepts_mood_tags_kwarg():
    """The kwarg must exist — its absence was the root cause."""
    import inspect
    sig = inspect.signature(HRVEngine.analyze_day)
    assert "mood_tags" in sig.parameters, \
        "analyze_day() must accept mood_tags, otherwise the server cannot forward them"
    assert sig.parameters["mood_tags"].default is None, \
        "mood_tags must default to None so existing callers keep old behaviour"


def test_no_tags_leaves_liver_spleen_phlegm_untouched():
    """Baseline: with no tags the three tag-driven axes stay at their HRV value."""
    base = _axes(None)
    assert base.liver_depression == 0.0
    assert base.spleen_deficiency == 0.0
    assert base.phlegm_turbidity == 0.0


def test_none_and_empty_list_are_equivalent():
    """Backward compatibility: existing callers passing nothing must not shift."""
    a, b = _axes(None), _axes([])
    assert a.score == b.score
    assert a.liver_depression == b.liver_depression
    assert a.spleen_deficiency == b.spleen_deficiency


@pytest.mark.parametrize("tag", ["irritable", "anxious"])
def test_irritable_or_anxious_raises_liver_depression(tag):
    """情志不遂 → 肝郁气滞 (+15, WEAK evidence per research/013)."""
    base, tagged = _axes(None), _axes([tag])
    assert tagged.liver_depression > base.liver_depression, \
        f"tag {tag!r} must raise the liver-depression axis"
    assert tagged.liver_depression == pytest.approx(base.liver_depression + 15)


def test_exhausted_raises_spleen_deficiency():
    base, tagged = _axes(None), _axes(["exhausted"])
    assert tagged.spleen_deficiency > base.spleen_deficiency
    assert tagged.spleen_deficiency == pytest.approx(base.spleen_deficiency + 20)


def test_brain_fog_raises_spleen_deficiency():
    base, tagged = _axes(None), _axes(["brain_fog"])
    assert tagged.spleen_deficiency == pytest.approx(base.spleen_deficiency + 15)


def test_brain_fog_plus_exhausted_raises_phlegm():
    """脑雾+疲惫同现 → 痰浊蒙蔽清窍 (composite rule)."""
    base = _axes(None)
    combo = _axes(["brain_fog", "exhausted"])
    assert combo.phlegm_turbidity > base.phlegm_turbidity
    # and the spleen bumps stack
    assert combo.spleen_deficiency == pytest.approx(base.spleen_deficiency + 35)


def test_tags_change_the_overall_score():
    """The user-visible symptom: the headline score must actually move."""
    assert _axes(["exhausted", "brain_fog"]).score != _axes(None).score


def test_unknown_tags_are_harmless():
    """Unrecognised tags must not crash or shift the axes."""
    assert _axes(["definitely_not_a_tag"]).score == _axes(None).score


# ──────────────────────────────────────────────
# 2) Payload parsing — server.parse_mood_tags
# ──────────────────────────────────────────────

def _parse():
    import server
    return server.parse_mood_tags


def test_parse_comma_string():
    """The frontend hidden input sends a comma-joined string."""
    assert _parse()("anxious,irritable") == ["anxious", "irritable"]


def test_parse_list_payload():
    assert _parse()(["anxious", "calm"]) == ["anxious", "calm"]


def test_parse_none_and_junk():
    p = _parse()
    assert p(None) == []
    assert p("") == []
    assert p(12345) == []


def test_parse_strips_blanks_and_dedupes_preserving_order():
    p = _parse()
    assert p(" anxious , ,irritable,anxious ") == ["anxious", "irritable"]


# ──────────────────────────────────────────────
# 3) Persistence + legacy migration
# ──────────────────────────────────────────────

@pytest.fixture()
def server_app(tmp_path, monkeypatch):
    """Flask test client bound to a throwaway SQLite file."""
    import server
    monkeypatch.setattr(server, "DB_PATH", str(tmp_path / "test.db"))
    server.init_db()
    server.app.config.update(TESTING=True)
    return server


def test_init_db_creates_mood_tags_column(server_app):
    conn = sqlite3.connect(server_app.DB_PATH)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(daily_log)")}
    conn.close()
    assert "mood_tags" in cols


def test_migration_adds_column_to_legacy_db(tmp_path, monkeypatch):
    """A pre-existing DB written before this fix must be migrated, not broken."""
    import server
    legacy = tmp_path / "legacy.db"
    conn = sqlite3.connect(legacy)
    conn.execute(
        """CREATE TABLE daily_log (
               id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT,
               hrv_rmssd REAL, resting_hr REAL, cycle_day INTEGER,
               mood_score INTEGER, sleep_hours REAL, event_label TEXT)"""
    )
    conn.execute(
        "INSERT INTO daily_log (user_id, date, hrv_rmssd, resting_hr, cycle_day) "
        "VALUES ('u', '2026-01-01', 40.0, 60, 5)"
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(server, "DB_PATH", str(legacy))
    server.init_db()

    conn = sqlite3.connect(legacy)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(daily_log)")}
    kept = conn.execute("SELECT COUNT(*) FROM daily_log").fetchone()[0]
    conn.close()
    assert "mood_tags" in cols, "migration must add the column to an old DB"
    assert kept == 1, "migration must preserve existing rows"


def _post(server_app, user, tags):
    client = server_app.app.test_client()
    return client.post("/api/checkin", json={
        "user_id": user, "hrv_rmssd": 42.0, "resting_hr": 68,
        "cycle_day": 10, "mood_score": 6, "mood_tags": tags,
        "sleep_hours": 7.0, "date": "2026-08-05",
    })


def test_checkin_persists_mood_tags(server_app):
    resp = _post(server_app, "u_persist", "anxious,irritable")
    assert resp.status_code == 200

    conn = sqlite3.connect(server_app.DB_PATH)
    stored = conn.execute(
        "SELECT mood_tags FROM daily_log WHERE user_id='u_persist'"
    ).fetchone()[0]
    conn.close()
    assert stored == "anxious,irritable"


def test_checkin_echoes_mood_tags(server_app):
    body = _post(server_app, "u_echo", "anxious,irritable").get_json()
    assert body["mood_tags"] == ["anxious", "irritable"]


def test_checkin_tags_change_tcm_output(server_app):
    """END-TO-END: the exact bug. Same HRV, different tags → different TCM."""
    plain = _post(server_app, "u_plain", "").get_json()
    tagged = _post(server_app, "u_tagged", "irritable,anxious").get_json()

    assert plain["score"] is not None and tagged["score"] is not None
    assert tagged["tcm"]["liver_depression"] > plain["tcm"]["liver_depression"], \
        "ticking Irritable/Anxious must raise 肝郁气滞 — this regressed before"


def test_checkin_exhausted_changes_spleen(server_app):
    plain = _post(server_app, "u_p2", "").get_json()
    tagged = _post(server_app, "u_t2", "exhausted").get_json()
    assert tagged["tcm"]["spleen_deficiency"] > plain["tcm"]["spleen_deficiency"]


# ──────────────────────────────────────────────
# 4) Frontend contract — the payload must keep carrying the tags
# ──────────────────────────────────────────────

def test_frontend_sends_mood_tags_in_payload():
    html = open(FRONTEND, encoding="utf-8").read()
    assert re.search(r"mood_tags\s*:\s*tags", html), \
        "submitCheckinImpl() must POST mood_tags"


def test_frontend_toggle_writes_hidden_input():
    html = open(FRONTEND, encoding="utf-8").read()
    assert "function toggleTag" in html
    body = re.search(r"function\s+toggleTag\s*\([^)]*\)\s*\{(.*?)\n\}", html, re.S)
    assert body, "could not locate toggleTag() body"
    assert "moodTagsVal" in body.group(1), \
        "toggleTag() must sync the selection into #moodTagsVal"
