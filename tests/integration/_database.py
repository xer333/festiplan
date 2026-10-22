"""An explicit test engine; never reconfigure the application's working engine."""
from pathlib import Path
import tempfile
from sqlalchemy.orm import sessionmaker
from app.database import create_database_engine

directory = tempfile.TemporaryDirectory(prefix='festiplan-tests-')
engine = create_database_engine(f'sqlite:///{Path(directory.name) / "tests.db"}')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
