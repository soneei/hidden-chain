"""
CI configuration contract tests.
================================

These lock the one failure mode the other 190-odd tests structurally cannot
catch: **the CI environment differing from the developer's environment.**

The bug this file exists to prevent already happened. On 2026-08-05 commit
``35be3ef`` added ``tests/test_mood_tags.py``, which does a bare ``import
server`` (Flask) in five places. The ``unit-tests`` job installed only
``pytest pytest-cov``, so on GitHub it died with ``ModuleNotFoundError: No
module named 'flask'`` — 5 failed, 5 errors — while every local run stayed
green, because a developer machine has flask installed. Nobody noticed for two
days, and two further commits were pushed on top of a red pipeline.

The asymmetry is the whole point: a test suite validates the code against the
environment it happens to run in. It says nothing about whether *another*
environment can even import the modules. So the check has to be made against
the workflow file itself.

Deliberately **not** fixed by wrapping those tests in ``pytest.importorskip``:
that would turn a loud red job into silent green while quietly deleting the
mood-tag end-to-end assertions from CI — the exact regression net that the
08-05 bug proved we needed. Install the runtime deps instead.

Static text checks only: no yaml parser (CI installs none at this step), no
network, no GitHub API.
"""
import os
import re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
WORKFLOW = os.path.join(REPO, ".github", "workflows", "ci.yml")
REQUIREMENTS = os.path.join(REPO, "requirements.txt")
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _unit_tests_job() -> str:
    """The ``unit-tests:`` job block (it is the last job in the file)."""
    wf = _read(WORKFLOW)
    assert "unit-tests:" in wf, "unit-tests job missing from CI workflow"
    return wf.split("unit-tests:", 1)[1]


def _tests_importing_server() -> list[str]:
    """Collected test modules that import the Flask app without a skip guard."""
    offenders = []
    for fn in sorted(os.listdir(TESTS_DIR)):
        if not (fn.startswith("test_") and fn.endswith(".py")):
            continue
        body = _read(os.path.join(TESTS_DIR, fn))
        if re.search(r"^\s*import server\b", body, re.M) and "importorskip" not in body:
            offenders.append(fn)
    return offenders


# ──────────────────────────────────────────────
# 1) The workflow installs what the tests actually import
# ──────────────────────────────────────────────

def test_workflow_exists():
    assert os.path.exists(WORKFLOW), "CI workflow (.github/workflows/ci.yml) missing"


def test_unit_tests_job_installs_runtime_requirements():
    """The regression itself: pytest-only env cannot import server.py."""
    offenders = _tests_importing_server()
    if not offenders:
        return  # nothing needs the runtime deps; nothing to enforce
    assert "-r requirements.txt" in _unit_tests_job(), (
        "unit-tests job must `pip install -r requirements.txt` — "
        f"{', '.join(offenders)} import server.py (Flask) without importorskip"
    )


def test_requirements_declares_flask():
    """server.py is unimportable without it, so it must be a declared dep."""
    assert "flask" in _read(REQUIREMENTS).lower(), "requirements.txt must declare flask"


def test_every_unguarded_server_import_is_covered_by_requirements():
    """Cross-check: the deps those tests need are declared, not just installed ad hoc."""
    if not _tests_importing_server():
        return
    server_src = _read(os.path.join(REPO, "server.py"))
    reqs = _read(REQUIREMENTS).lower()
    for mod in re.findall(r"^\s*(?:from|import)\s+(flask\w*)", server_src, re.M):
        assert mod.split(".")[0].lower() in reqs, (
            f"server.py imports {mod} but requirements.txt does not declare it"
        )


# ──────────────────────────────────────────────
# 2) The gate keeps its teeth
# ──────────────────────────────────────────────

def test_unit_tests_job_still_installs_test_tooling():
    job = _unit_tests_job()
    assert "pytest" in job, "unit-tests job must install pytest"
    assert "pytest-cov" in job, "unit-tests job must install pytest-cov"


def test_coverage_gate_not_dropped_from_pytest_command():
    """Losing --cov=src would keep the job green while retiring the 80% gate."""
    job = _unit_tests_job()
    assert "--cov=src" in job, "coverage gate (--cov=src) dropped from the pytest command"
    assert "pytest tests/" in job, "unit-tests job must run the whole tests/ suite"


def test_all_three_gates_still_wired():
    """Silently deleting a job is a plausible 'fix' for a red pipeline."""
    wf = _read(WORKFLOW)
    for job in ("quality-gate:", "type-check:", "unit-tests:"):
        assert job in wf, f"CI job {job} disappeared from the workflow"
    assert "smoke_test.py" in wf, "smoke gate must stay wired into CI"
    assert "mypy src/" in wf, "mypy gate must stay wired into CI"
