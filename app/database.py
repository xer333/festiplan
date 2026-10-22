from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings


def create_database_engine(url):
    args = {'check_same_thread': False} if url.startswith('sqlite') else {}
    database_engine = create_engine(url, connect_args=args)
    if url.startswith('sqlite'):
        @event.listens_for(database_engine, 'connect')
        def configure_sqlite(connection, record):
            connection.execute('PRAGMA foreign_keys=ON')
    return database_engine


engine = create_database_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    with SessionLocal() as db:
        yield db
