"""Export/CSV consistency tests for the check-in frontend.

Guards against the historical ``checkins -> logs`` IndexedDB store-name
mismatch bug: ``exportCSV()`` used to hardcode the store name while the
rest of the page used the ``ST`` constant, so a rename silently broke the
export path (0 rows exported).

These are static-analysis tests over the tracked HTML frontend:

1. The ``ST`` store-name constant is declared exactly once.
2. ``exportCSV`` exists and is wired to the export button.
3. Every IndexedDB ``transaction(...)`` / ``objectStore(...)`` /
   ``createObjectStore(...)`` call references the ``ST`` constant —
   no hardcoded string store names anywhere.

Note: the Supabase REST path ``/rest/v1/checkins`` is a *remote* table
name, unrelated to the IndexedDB store, and is intentionally allowed.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# The tracked, canonical frontend. Must exist in every checkout (incl. CI).
CANONICAL_FRONTEND = REPO_ROOT / "data" / "web_checkin.html"

# Local build copies kept in sync but not tracked by git; checked only
# when present so CI checkouts (which lack them) still pass.
OPTIONAL_COPIES = [
    REPO_ROOT / "frontend_dist" / "index.html",
    REPO_ROOT / "frontend_ghpages" / "index.html",
]

FRONTENDS = [CANONICAL_FRONTEND] + [p for p in OPTIONAL_COPIES if p.exists()]
FRONTEND_IDS = [str(p.relative_to(REPO_ROOT)) for p in FRONTENDS]


def test_canonical_frontend_exists() -> None:
    assert CANONICAL_FRONTEND.exists(), (
        f"tracked frontend missing: {CANONICAL_FRONTEND}"
    )


@pytest.fixture(params=FRONTENDS, ids=FRONTEND_IDS)
def html(request: pytest.FixtureRequest) -> str:
    return Path(request.param).read_text(encoding="utf-8")


def test_store_constant_declared_once(html: str) -> None:
    decls = re.findall(r"\bST\s*=\s*(['\"])(\w+)\1", html)
    assert len(decls) == 1, f"ST constant must be declared exactly once, found {decls}"
    assert decls[0][1] == "logs", f"ST store name changed unexpectedly: {decls[0][1]!r}"


def test_export_csv_function_present_and_wired(html: str) -> None:
    assert re.search(r"function\s+exportCSV\s*\(", html), "exportCSV() missing"
    assert re.search(r"onclick=\"exportCSV\(\)\"", html), (
        "export button not wired to exportCSV()"
    )


def test_no_hardcoded_indexeddb_store_names(html: str) -> None:
    """All IndexedDB store references must go through the ST constant."""
    offenders: list[str] = []
    for pattern in (
        r"\.transaction\(\s*['\"]\w+['\"]",
        r"\.objectStore\(\s*['\"]\w+['\"]",
        r"createObjectStore\(\s*['\"]\w+['\"]",
    ):
        offenders.extend(re.findall(pattern, html))
    assert not offenders, (
        "hardcoded IndexedDB store name(s) found (use the ST constant): "
        f"{offenders}"
    )


def test_export_csv_body_uses_st_constant(html: str) -> None:
    match = re.search(r"function\s+exportCSV\s*\([^)]*\)\s*\{(.*?)\n\}", html, re.S)
    assert match, "could not extract exportCSV() body"
    body = match.group(1)
    assert re.search(r"\.transaction\(\s*ST\b", body), (
        "exportCSV() must open its transaction via the ST constant"
    )
    assert re.search(r"\.objectStore\(\s*ST\b", body), (
        "exportCSV() must resolve its object store via the ST constant"
    )
