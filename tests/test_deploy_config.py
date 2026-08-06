"""
Deployment contract tests (Render.com blueprint).
=================================================

These lock the things that silently break a PaaS deploy but look perfectly
fine on a laptop:

  1. **The WSGI path never runs ``__main__``.** Render's start command is
     ``gunicorn server:app`` — gunicorn merely *imports* the module to grab
     ``app``. ``init_db()`` used to live inside ``if __name__ == "__main__"``,
     so a real deploy would have created the table **never** and answered the
     very first request with ``no such table: daily_log``. Locally you'd never
     see it, because ``python server.py`` does enter that branch.
  2. **Config drift between the disk mount and the DB path.** Render wipes the
     container filesystem on every deploy/restart. The DB therefore has to sit
     on the mounted disk, which means ``HC_DATA_DIR`` must equal
     ``disk.mountPath``. Those two values live in different blocks of
     ``render.yaml`` and drift silently — the app keeps working right up until
     a redeploy eats the history.
  3. **SQLite + multiple gunicorn workers** = ``database is locked``.
  4. **Werkzeug debug on a public bind** = arbitrary code execution.

Everything here is static/subprocess-level: no Render account, no network.
"""
import os
import re
import subprocess
import sys

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RENDER_YAML = os.path.join(REPO, "render.yaml")
PROCFILE = os.path.join(REPO, "Procfile")
SERVER_PY = os.path.join(REPO, "server.py")
DEPLOY_DOC = os.path.join(REPO, "DEPLOY_RENDER.md")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# ──────────────────────────────────────────────
# 1) Blueprint exists and starts the app correctly
# ──────────────────────────────────────────────

def test_render_yaml_exists():
    assert os.path.exists(RENDER_YAML), "render.yaml (Render Blueprint) missing"


def test_start_command_uses_gunicorn_and_platform_port():
    """Render injects $PORT; hardcoding 5000 makes the health check fail."""
    cmd = re.search(r"startCommand:\s*(.+)", _read(RENDER_YAML))
    assert cmd, "render.yaml has no startCommand"
    line = cmd.group(1)
    assert "gunicorn server:app" in line, f"unexpected start command: {line}"
    assert "$PORT" in line, "startCommand must bind Render's $PORT, not a fixed port"


def test_single_worker_because_sqlite_has_one_writer():
    line = re.search(r"startCommand:\s*(.+)", _read(RENDER_YAML)).group(1)
    assert "--workers 1" in line, (
        "SQLite allows a single writer; >1 gunicorn worker yields "
        "'database is locked' under concurrent check-ins"
    )


def test_procfile_and_blueprint_agree():
    """Two start definitions that disagree = deploys behave differently per host."""
    proc = _read(PROCFILE)
    render = _read(RENDER_YAML)
    assert "gunicorn server:app" in proc, "Procfile drifted from the blueprint"
    assert "gunicorn server:app" in render


def test_requirements_cover_the_runtime():
    reqs = _read(os.path.join(REPO, "requirements.txt")).lower()
    assert "flask" in reqs, "flask missing from requirements.txt"
    assert "gunicorn" in reqs, "gunicorn missing — the start command would not exist"


def test_python_version_pinned_at_or_above_310():
    """The engine uses PEP 604 (`X | None`); Render's default may be older."""
    m = re.search(r"key:\s*PYTHON_VERSION\s*\n\s*(?:#.*\n\s*)*value:\s*\"?([\d.]+)", _read(RENDER_YAML))
    assert m, "PYTHON_VERSION not pinned in render.yaml"
    major, minor = (int(p) for p in m.group(1).split(".")[:2])
    assert (major, minor) >= (3, 10), f"pinned Python {m.group(1)} < 3.10"


# ──────────────────────────────────────────────
# 2) Persistence wiring — the drift-prone part
# ──────────────────────────────────────────────

def test_data_dir_matches_disk_mount_path():
    """HC_DATA_DIR and disk.mountPath must point at the same place."""
    text = _read(RENDER_YAML)
    data_dir = re.search(
        r"key:\s*HC_DATA_DIR\s*\n\s*(?:#.*\n\s*)*value:\s*(\S+)", text
    )
    mount = re.search(r"mountPath:\s*(\S+)", text)
    assert data_dir and mount, "render.yaml must declare HC_DATA_DIR and a disk mountPath"
    assert data_dir.group(1).strip('"') == mount.group(1).strip('"'), (
        f"HC_DATA_DIR={data_dir.group(1)} but disk mounts at {mount.group(1)} — "
        "the SQLite file would land on the ephemeral filesystem and be wiped "
        "on every redeploy"
    )


def test_server_reads_data_dir_from_env():
    src = _read(SERVER_PY)
    assert "HC_DATA_DIR" in src, "server.py must honour HC_DATA_DIR to use a mounted disk"


def test_init_db_is_called_at_import_scope():
    """Static guard: a bare top-level `init_db()` call must exist."""
    src = _read(SERVER_PY)
    assert re.search(r"(?m)^init_db\(\)\s*$", src), (
        "init_db() is not called at module scope — gunicorn imports the module "
        "without running __main__, so the table would never be created"
    )


def test_import_alone_creates_the_schema(tmp_path):
    """Functional proof: importing server (what gunicorn does) builds the DB.

    Runs in a subprocess so HC_DATA_DIR is read at a fresh import, and so this
    test cannot pollute the repo's data/ directory.
    """
    pytest.importorskip("flask", reason="runtime dep; CI installs it via requirements.txt")
    code = (
        "import server, sqlite3;"
        "cols=[r[1] for r in sqlite3.connect(server.DB_PATH)"
        ".execute('PRAGMA table_info(daily_log)')];"
        "assert cols, 'daily_log table not created on import';"
        "assert 'mood_tags' in cols;"
        "print(server.DB_PATH)"
    )
    env = {**os.environ, "HC_DATA_DIR": str(tmp_path)}
    res = subprocess.run(
        [sys.executable, "-c", code], cwd=REPO, env=env,
        capture_output=True, text=True,
    )
    assert res.returncode == 0, f"import-time bootstrap failed:\n{res.stderr}"
    assert str(tmp_path) in res.stdout, "HC_DATA_DIR was ignored; DB landed elsewhere"


def test_init_db_creates_missing_parent_directory(tmp_path):
    """A freshly mounted Render disk may not have the directory yet."""
    pytest.importorskip("flask", reason="runtime dep; CI installs it via requirements.txt")
    target = tmp_path / "not" / "created" / "yet"
    env = {**os.environ, "HC_DATA_DIR": str(target)}
    res = subprocess.run(
        [sys.executable, "-c", "import server; print(server.DB_PATH)"],
        cwd=REPO, env=env, capture_output=True, text=True,
    )
    assert res.returncode == 0, f"import failed on a non-existent data dir:\n{res.stderr}"
    assert (target / "hidden_chain.db").exists()


# ──────────────────────────────────────────────
# 3) Production safety
# ──────────────────────────────────────────────

def test_debug_is_not_hardcoded_on():
    src = _read(SERVER_PY)
    assert "debug=True" not in src, (
        "the Werkzeug debugger executes arbitrary code from the browser and the "
        "server binds 0.0.0.0 — debug must be opt-in via HC_DEBUG"
    )
    assert "HC_DEBUG" in src, "no HC_DEBUG opt-in switch"


def test_blueprint_disables_debug_and_autodeploy():
    text = _read(RENDER_YAML)
    assert re.search(r"key:\s*HC_DEBUG\s*\n\s*(?:#.*\n\s*)*value:\s*\"?0\"?", text), \
        "HC_DEBUG must be explicitly 0 in the deployed environment"
    assert re.search(r"autoDeploy:\s*false", text), (
        "autoDeploy should be off: a health-data service should not be swapped "
        "out silently on every push to main"
    )


# ──────────────────────────────────────────────
# 4) The docs must carry the blockers, not just the happy path
# ──────────────────────────────────────────────

def test_deploy_doc_exists_and_flags_the_auth_blocker():
    assert os.path.exists(DEPLOY_DOC), "DEPLOY_RENDER.md missing"
    doc = _read(DEPLOY_DOC)
    assert "/api/dashboard/" in doc, "doc must name the unauthenticated endpoint"
    for token in ("P0", "P1", "P2"):
        assert token in doc, f"blocker {token} not documented"


def test_blueprint_warns_before_public_deploy():
    """The config itself must carry the warning — people read yaml, not docs."""
    text = _read(RENDER_YAML)
    assert "DEPLOY_RENDER.md" in text, "render.yaml should point at the deploy notes"


@pytest.mark.parametrize("endpoint", ["/api/checkin", "/api/dashboard/<user_id>"])
def test_no_auth_yet_is_a_known_documented_gap(endpoint):
    """Guard against a false sense of security.

    There is deliberately no auth in this build. If someone later adds one,
    this test should be replaced by real authz tests rather than deleted
    silently — the doc is the single source of truth until then.
    """
    assert endpoint.split("<")[0] in _read(SERVER_PY)
    assert "无鉴权" in _read(DEPLOY_DOC)
