"""Shared pytest fixtures for the Spendly test suite.

These fixtures make sure the test suite never reads or writes the real
``spendly.db`` used by local dev: every test runs against its own throwaway
SQLite file.
"""
import os
import tempfile

import pytest

import database.db as db_module

# `app.py` calls `init_db()` / `seed_db()` once at import time (inside
# `with app.app_context():`), against whatever `database.db.DB_PATH` is
# active at that moment. Redirect DB_PATH to a one-off temp file *before*
# importing `app` below, so that import-time call never touches the real
# spendly.db. Individual tests then repoint DB_PATH again (see `db_path`
# below) and re-run `init_db()` against their own temp file, so this
# particular file is never read by any test.
_import_fd, _import_time_db_path = tempfile.mkstemp(suffix=".db")
os.close(_import_fd)
db_module.DB_PATH = _import_time_db_path

from app import app  # noqa: E402  (import must follow the DB_PATH redirect above)


@pytest.fixture
def db_path(monkeypatch):
    """Point database.db.DB_PATH at a fresh temp SQLite file for one test.

    `get_db()` reads the module-level DB_PATH fresh on every call, so
    monkeypatching it here is sufficient to isolate every test's data.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr(db_module, "DB_PATH", path)
    db_module.init_db()
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


@pytest.fixture
def client(db_path):
    """Flask test client wired to the current test's isolated temp database."""
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client
