"""
Regression tests for the "date picker does not collapse" bug.
=============================================================

Root cause (fixed 2026-08-01) — three independent reasons the native
``<input type="date">`` popup / iOS wheel tray stayed open:

  * **No event to close on.** The only dismissal path was a ``change``
    listener, but a native date input fires ``change`` *only when the value
    actually changes*. Re-opening the picker and tapping the date that is
    already selected (a very common "let me double-check" gesture) fires
    nothing at all, so the tray stayed up indefinitely.
  * **Swallowed synchronous blur.** ``blur()`` was called synchronously inside
    the ``change`` handler, i.e. while the browser was still committing the
    picker selection. In that window the blur is dropped, and on iOS it can
    leave the tray up with the input already unfocused (a zombie overlay).
  * **No escape hatch.** There was no Escape-key and no outside-tap handler
    anywhere in the file, so once the popup was stuck the user had no way out.

A secondary defect fixed at the same time: the phase hint was driven purely by
``change``, but mobile wheel pickers emit ``input`` on every tick and only emit
``change`` on dismissal — so the hint lagged behind the visible selection.

These are static contract tests over ``data/web_checkin.html`` (the frontend is
plain inline JS and this repo has no JS test runner — same approach as
``tests/test_export_csv.py`` and ``tests/test_checkin_submit.py``).
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


def _close_body(html: str) -> str:
    body = re.search(r"function\s+closeDatePicker\s*\([^)]*\)\s*\{(.*?)\n\}", html, re.S)
    assert body, "could not locate closeDatePicker() body"
    return body.group(1)


def test_close_helper_exists(html: str) -> None:
    """Dismissal must live in one named helper, not be inlined per listener."""
    assert "function closeDatePicker" in html, "closeDatePicker() missing"
    assert _close_body(html).strip(), "closeDatePicker() body is empty"


def test_blur_is_deferred_one_macrotask(html: str) -> None:
    """A blur fired synchronously inside `change` is swallowed by the browser."""
    body = _close_body(html)
    assert "setTimeout(" in body, \
        "closeDatePicker() must defer the blur (setTimeout) so it is not swallowed"
    assert ".blur()" in body, "closeDatePicker() must actually blur the input"


def test_no_synchronous_blur_in_change_handler(html: str) -> None:
    """Guard against reintroducing the original blur-inside-change anti-pattern."""
    assert not re.search(
        r"addEventListener\(\s*'change'\s*,\s*\(\)\s*=>\s*\{[^}]*\.blur\(\)", html
    ), "blur() must not be called synchronously inside a change handler"


def test_escape_key_fallback(html: str) -> None:
    """Escape must close the picker even when `change` never fires."""
    assert re.search(r"addEventListener\(\s*'keydown'", html), \
        "no keydown listener on the date input"
    assert "'Escape'" in html, "Escape key does not dismiss the date picker"
    assert re.search(r"'Escape'[^\n]*closeDatePicker\(\)", html), \
        "Escape branch must call closeDatePicker()"


def test_outside_tap_fallback(html: str) -> None:
    """Tapping elsewhere must close a picker that `change` never dismissed."""
    handler = re.search(
        r"document\.addEventListener\(\s*'pointerdown'\s*,([^\n]*)", html
    )
    assert handler, "no document-level pointerdown fallback"
    src = handler.group(1)
    assert "closeDatePicker()" in src, "pointerdown fallback must close the picker"
    assert "activeElement" in src, \
        "pointerdown fallback must only fire while the date input holds focus"
    assert "!==" in src, \
        "pointerdown fallback must ignore taps on the date input itself"


def test_hint_also_tracks_input_event(html: str) -> None:
    """Mobile wheels emit `input` per tick; `change` only fires on dismissal."""
    assert re.search(
        r"periodStartEl\.addEventListener\(\s*'input'\s*,\s*updatePhaseHint\s*\)", html
    ), "phase hint must update on `input`, not only on `change`"


def test_change_handler_still_persists_and_closes(html: str) -> None:
    """Consolidating the duplicate listeners must not drop localStorage writes."""
    handler = re.search(
        r"periodStartEl\.addEventListener\(\s*'change'\s*,([^\n]*)", html
    )
    assert handler, "date input has no change listener"
    src = handler.group(1)
    for call in ("updatePhaseHint()", "savePeriodToLocal()", "closeDatePicker()"):
        assert call in src, f"change handler must call {call}"


def test_no_duplicate_change_listeners_on_date_input(html: str) -> None:
    """Two listeners with overlapping duties are how the close path drifted."""
    listeners = re.findall(
        r"(?:periodStartEl|getElementById\('periodStart'\))"
        r"\.addEventListener\(\s*'change'",
        html,
    )
    assert len(listeners) == 1, \
        f"expected exactly one change listener on the date input, found {len(listeners)}"
