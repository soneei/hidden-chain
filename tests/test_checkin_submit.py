"""
Regression tests for the check-in form "submit does nothing" bug.
=================================================================

Root cause (fixed 2026-07-31):
  * ``idb()`` opened IndexedDB asynchronously at page load, but ``save()``
    read the bare ``db`` global and did ``if(!db) return;`` — a submit fired
    before the open resolved (or when IndexedDB is unavailable, e.g. Safari
    private mode) was **silently discarded**: no error, no stored row.
  * ``save()`` attached no error handler to the add request or transaction,
    so quota / InvalidStateError failures were invisible too.
  * ``submitCheckin()`` had no try/catch, so any synchronous throw killed the
    click with zero UI feedback.

These are static contract tests over ``data/web_checkin.html`` (the frontend
is plain inline JS with no JS test runner in this repo — same approach as
``tests/test_export_csv.py``).
"""
import os
import re

import pytest

FRONTEND = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "web_checkin.html"
)


@pytest.fixture(scope="module")
def html() -> str:
    with open(FRONTEND, encoding="utf-8") as f:
        return f.read()


def test_save_is_async_and_awaits_db_open(html: str) -> None:
    """save() must lazily open the DB instead of bailing out when it is not ready."""
    assert re.search(r"async\s+function\s+save\s*\(", html), "save() must be async"
    body = re.search(r"async\s+function\s+save\s*\([^)]*\)\s*\{(.*?)\n\}", html, re.S)
    assert body, "could not locate save() body"
    assert "await idb()" in body.group(1), "save() must await idb()"
    assert not re.search(r"if\s*\(\s*!db\s*\)\s*return\s*;", body.group(1)), \
        "save() must not silently return when db is not ready"


def test_save_rejects_on_write_failure(html: str) -> None:
    """A failed IndexedDB write must reject so the caller can warn the user."""
    body = re.search(r"async\s+function\s+save\s*\([^)]*\)\s*\{(.*?)\n\}", html, re.S)
    assert body
    src = body.group(1)
    for handler in ("onerror", "onabort", "oncomplete"):
        assert handler in src, f"save() missing {handler} handler"
    assert "throw new Error" in src, "save() must throw when storage is unavailable"


def test_idb_is_cached_and_idempotent(html: str) -> None:
    """idb() must reuse one open promise so concurrent callers share the handle."""
    assert "dbPromise" in html, "idb() must cache its open promise"
    assert re.search(r"if\s*\(\s*db\s*\)\s*return\s+Promise\.resolve\(db\)", html), \
        "idb() must short-circuit when the DB is already open"


def test_submit_wraps_body_in_try_catch(html: str) -> None:
    """A synchronous throw must surface as an inline error, not a dead click."""
    assert re.search(r"function\s+submitCheckin\s*\([^)]*\)\s*\{\s*try", html), \
        "submitCheckin() must wrap submitCheckinImpl() in try/catch"
    assert "function submitCheckinImpl" in html, "submitCheckinImpl() missing"
    wrapper = re.search(
        r"function\s+submitCheckin\s*\([^)]*\)\s*\{(.*?)\n\}", html, re.S
    )
    assert wrapper and "showInlineError" in wrapper.group(1), \
        "submitCheckin() catch block must call showInlineError()"


def test_all_call_sites_use_save_or_warn(html: str) -> None:
    """Both the online and offline paths must persist through saveOrWarn()."""
    assert "async function saveOrWarn" in html, "saveOrWarn() missing"
    assert not re.search(r"(?<!OrWarn)\bsave\(\{", html), \
        "found a bare fire-and-forget save({...}) call"
    assert len(re.findall(r"await\s+saveOrWarn\(", html)) >= 2, \
        "expected saveOrWarn() awaited on both the server and offline paths"


def test_all_reader_also_opens_db_lazily(html: str) -> None:
    """History rendering must not return [] just because the open is in flight."""
    body = re.search(r"async\s+function\s+all\s*\([^)]*\)\s*\{(.*?)\n\}", html, re.S)
    assert body, "all() must be async"
    assert "await idb()" in body.group(1), "all() must await idb()"
