import os
from pathlib import Path
import sqlite3
import subprocess
import sys


def test_seed_is_executable_preserves_existing_data_and_supports_explicit_reset(tmp_path):
    database = tmp_path / 'demo.db'
    env = dict(os.environ, FESTIPLAN_DATABASE_URL=f'sqlite:///{database}', PYTHONIOENCODING='utf-8')
    command = [sys.executable, '-m', 'app.seed']
    cwd = Path(__file__).resolve().parents[2]
    first = subprocess.run(command, cwd=cwd, env=env, capture_output=True)
    assert first.returncode == 0, first.stderr.decode('utf-8')
    with sqlite3.connect(database) as db:
        assert db.execute('select count(*) from concerts').fetchone()[0] == 14
        assert db.execute('select count(*) from artists').fetchone()[0] == 12
        db.execute("update festivals set name='Keep my changes'")
    second = subprocess.run(command, cwd=cwd, env=env, capture_output=True)
    assert second.returncode == 1
    with sqlite3.connect(database) as db:
        assert db.execute('select name from festivals').fetchone()[0] == 'Keep my changes'
    assert subprocess.run(command + ['--reset'], cwd=cwd, env=env, capture_output=True).returncode == 0
    with sqlite3.connect(database) as db:
        assert db.execute('select name from festivals').fetchone()[0] == 'Hellforge Open Air'
