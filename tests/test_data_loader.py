"""Tests for src/data_loader.py — pilot CSV reading and validation."""

import os
import sys
import tempfile

SRC = os.path.join(os.path.dirname(__file__), os.pardir, "src")
sys.path.insert(0, os.path.abspath(SRC))

from data_loader import (
    read_pilot_csv,
    generate_sample_csv,
    LoadResult,
    LoadError,
    REQUIRED_COLUMNS,
    OPTIONAL_COLUMNS,
    ALL_COLUMNS,
)


# ── Helpers ──────────────────────────────────

def _write_csv(path: str, lines: list[str]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _make_valid_csv() -> str:
    """Return a minimal valid 3-user × 7-day CSV as a string."""
    header = ",".join(ALL_COLUMNS)
    rows = [header]
    days = ["2026-07-29", "2026-07-30", "2026-07-31", "2026-08-01",
            "2026-08-02", "2026-08-03", "2026-08-04"]
    for uid in ("U01", "U02", "U03"):
        for d in days:
            rows.append(f"{uid},{d},38.0,0.5,normal,2.0,70.0,7.0,calm")
    return "\n".join(rows) + "\n"


# ── Tests ────────────────────────────────────

def test_valid_csv_loads() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(_make_valid_csv())
        path = f.name
    try:
        result = read_pilot_csv(path)
        assert result.ok, f"unexpected errors: {result.errors}"
        assert len(result.data) == 3
        for uid in ("U01", "U02", "U03"):
            assert uid in result.data
            assert len(result.data[uid]) == 7
            assert result.data[uid][0].resting_rmssd == 38.0
            assert result.data[uid][0].recovery_classification == "normal"
    finally:
        os.unlink(path)


def test_json_PilotSample_valid_after_generate() -> None:
    """generate_sample_csv() output should pass validation."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        path = f.name
    try:
        generate_sample_csv(path)
        result = read_pilot_csv(path)
        assert result.ok, f"sample CSV should be valid, got: {result.errors}"
        assert len(result.data) == 3
        for uid in ("U01", "U02", "U03"):
            assert uid in result.data, f"missing {uid}"
            assert len(result.data[uid]) == 7
    finally:
        os.unlink(path)


def test_missing_required_column() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        # Missing "recovery_classification"
        f.write("user_id,date,resting_rmssd,normalized_hrv\n")
        f.write("U01,2026-07-29,38.0,0.5\n")
        path = f.name
    try:
        result = read_pilot_csv(path)
        assert not result.ok
        assert any("recovery_classification" in e.message for e in result.errors)
    finally:
        os.unlink(path)


def test_unknown_column() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("user_id,date,resting_rmssd,normalized_hrv,recovery_classification,extra_column\n")
        f.write("U01,2026-07-29,38.0,0.5,normal,x\n")
        path = f.name
    try:
        result = read_pilot_csv(path)
        assert not result.ok
        assert any("extra_column" in e.message for e in result.errors)
    finally:
        os.unlink(path)


def test_invalid_rmssd_negative() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(",".join(ALL_COLUMNS) + "\n")
        f.write("U01,2026-07-29,-5.0,0.5,normal,2.0,70.0,7.0,calm\n")
        path = f.name
    try:
        result = read_pilot_csv(path)
        assert not result.ok
        assert any("positive" in e.message.lower() for e in result.errors)
    finally:
        os.unlink(path)


def test_invalid_recovery_classification() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(",".join(ALL_COLUMNS) + "\n")
        f.write("U01,2026-07-29,38.0,0.5,unknown,2.0,70.0,7.0,calm\n")
        path = f.name
    try:
        result = read_pilot_csv(path)
        assert not result.ok
        assert any("fast/normal/slow" in e.message for e in result.errors)
    finally:
        os.unlink(path)


def test_invalid_date() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(",".join(ALL_COLUMNS) + "\n")
        f.write("U01,not-a-date,38.0,0.5,normal,2.0,70.0,7.0,calm\n")
        path = f.name
    try:
        result = read_pilot_csv(path)
        assert not result.ok
        assert any("YYYY-MM-DD" in e.message for e in result.errors)
    finally:
        os.unlink(path)


def test_duplicate_user_date() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(",".join(ALL_COLUMNS) + "\n")
        f.write("U01,2026-07-29,38.0,0.5,normal,2.0,70.0,7.0,calm\n")
        f.write("U01,2026-07-29,40.0,0.3,normal,2.5,72.0,6.5,calm\n")
        path = f.name
    try:
        result = read_pilot_csv(path)
        assert not result.ok
        assert any("duplicate" in e.message.lower() for e in result.errors)
    finally:
        os.unlink(path)


def test_invalid_resting_hr_range() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(",".join(ALL_COLUMNS) + "\n")
        # RHR = 10 (below 20) → should fail
        f.write("U01,2026-07-29,38.0,0.5,normal,2.0,10.0,7.0,calm\n")
        path = f.name
    try:
        result = read_pilot_csv(path)
        assert not result.ok
        assert any("resting_hr" in e.message.lower() for e in result.errors)
    finally:
        os.unlink(path)


def test_invalid_sleep_hours() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(",".join(ALL_COLUMNS) + "\n")
        # sleep = 25 (above 24) → should fail
        f.write("U01,2026-07-29,38.0,0.5,normal,2.0,70.0,25.0,calm\n")
        path = f.name
    try:
        result = read_pilot_csv(path)
        assert not result.ok
        assert any("sleep_hours" in e.message.lower() for e in result.errors)
    finally:
        os.unlink(path)


def test_mood_tags_parsed_correctly() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(",".join(ALL_COLUMNS) + "\n")
        f.write("U01,2026-07-29,38.0,0.5,normal,2.0,70.0,7.0,irritable;anxious;exhausted\n")
        path = f.name
    try:
        result = read_pilot_csv(path)
        assert result.ok, f"unexpected errors: {result.errors}"
        feats = result.data["U01"][0]
        assert feats.mood_tags == ["irritable", "anxious", "exhausted"]
    finally:
        os.unlink(path)


def test_empty_mood_tags() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(",".join(ALL_COLUMNS) + "\n")
        f.write("U01,2026-07-29,38.0,0.5,normal,2.0,70.0,7.0,\n")
        path = f.name
    try:
        result = read_pilot_csv(path)
        assert result.ok, f"unexpected errors: {result.errors}"
        assert result.data["U01"][0].mood_tags == []
    finally:
        os.unlink(path)


def test_optional_fields_absent_still_valid() -> None:
    """Missing optional columns should not break loading."""
    header = "user_id,date,resting_rmssd,normalized_hrv,recovery_classification"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(header + "\n")
        f.write("U01,2026-07-29,38.0,0.5,normal\n")
        path = f.name
    try:
        result = read_pilot_csv(path)
        assert result.ok, f"unexpected errors: {result.errors}"
        feats = result.data["U01"][0]
        assert feats.recovery_rate is None
        assert feats.resting_hr is None
        assert feats.sleep_hours is None
        assert feats.mood_tags == []
    finally:
        os.unlink(path)


def test_file_not_found() -> None:
    result = read_pilot_csv("/nonexistent/path.csv")
    assert not result.ok
    assert any("not found" in e.message.lower() for e in result.errors)


def test_utf8_bom_handled() -> None:
    """CSV with UTF-8 BOM should load correctly."""
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as f:
        f.write(b"\xef\xbb\xbf")  # UTF-8 BOM
        header = ",".join(ALL_COLUMNS)
        f.write(f"{header}\n".encode("utf-8"))
        f.write("U01,2026-07-29,38.0,0.5,normal,2.0,70.0,7.0,calm\n".encode("utf-8"))
        path = f.name
    try:
        result = read_pilot_csv(path)
        assert result.ok, f"unexpected errors: {result.errors}"
        assert result.data["U01"][0].resting_rmssd == 38.0
    finally:
        os.unlink(path)
