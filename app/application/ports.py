from typing import Protocol, TypeVar
from app.domain.model import Artist, Concert, Festival, Incident, Stage
from app.domain.events import DomainEvent

T = TypeVar('T')


class Repository(Protocol[T]):
    def get(self, item_id: int) -> T | None: ...
    def list(self) -> list[T]: ...
    def save(self, item: T) -> T: ...


class UnitOfWork(Protocol):
    festivals: Repository[Festival]
    artists: Repository[Artist]
    stages: Repository[Stage]
    concerts: Repository[Concert]
    incidents: Repository[Incident]

    def __enter__(self) -> 'UnitOfWork': ...
    def __exit__(self, exc_type, exc_value, traceback) -> None: ...
    def commit(self) -> None: ...


class Notifier(Protocol):
    def notify(self, event: DomainEvent) -> None: ...
