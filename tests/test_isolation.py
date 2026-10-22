"""Tests must never use a configured working database, even after early imports."""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys


def test_integration_suite_preserves_database_when_application_is_already_imported(tmp_path):
    database = tmp_path / 'working.db'
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE sentinel (value TEXT)')
        connection.execute("INSERT INTO sentinel VALUES ('Keep user data')")
    original = database.read_bytes()
    code = '''from app.main import app
from app.database import engine
import pytest
raise SystemExit(pytest.main(['-q', 'tests/integration/test_regressions.py']))
'''
    run = subprocess.run([sys.executable, '-c', code], capture_output=True, timeout=60,
                         cwd=Path(__file__).resolve().parents[1],
                         env=dict(os.environ, FESTIPLAN_DATABASE_URL=f'sqlite:///{database}',
                                  FESTIPLAN_FAIL_NOTIFICATIONS='false', PYTHONIOENCODING='utf-8'))
    assert run.returncode == 0, (run.stdout + run.stderr).decode('utf-8')
    assert database.read_bytes() == original
