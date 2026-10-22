import pytest
from fastapi.testclient import TestClient
from app.config import settings
from app.database import Base, get_db
from app.main import create_app
from ._database import directory, engine, SessionLocal


@pytest.fixture(scope='session', autouse=True)
def prepare():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    directory.cleanup()


@pytest.fixture(autouse=True)
def notification_defaults(monkeypatch):
    monkeypatch.setattr(settings, 'fail_notifications', False)


@pytest.fixture
def client():
    with SessionLocal() as db:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()

    application = create_app(database_engine=engine)

    def test_db():
        with SessionLocal() as db:
            yield db

    application.dependency_overrides[get_db] = test_db
    with TestClient(application) as test_client:
        yield test_client
