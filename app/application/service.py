import logging
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Generic, TypeVar

from app.domain.errors import DomainError, NotFound
from app.domain.events import ConcertRescheduled, PlanningPublished, PlanningUnpublished
from app.domain.model import Artist, Concert, Equipment, Festival, Incident, Planning, Stage, TimeSlot
from .commands import RescheduleConcert, ScheduleConcert
from .ports import Notifier, UnitOfWork

logger = logging.getLogger(__name__)
T = TypeVar('T')


@dataclass(frozen=True)
class OperationResult(Generic[T]):
    value: T
    notification_status: str


def required(repo, item_id, label):
    item = repo.get(item_id)
    if item is None:
        raise NotFound(f'{label} introuvable')
    return item


class FestiPlan:
    """Incoming application API. All mutations own one explicit transaction."""

    def __init__(self, uow: UnitOfWork, notifier: Notifier):
        self.uow = uow
        self.notifier = notifier

    def _notify(self, value, event):
        # Called only after successful commit AND closure of the transaction.
        try:
            self.notifier.notify(event)
        except Exception:
            logger.exception('Notification failed after successful commit: %r', event)
            return OperationResult(value, 'failed')
        return OperationResult(value, 'sent')

    def list_festivals(self):
        with self.uow as uow:
            return sorted(uow.festivals.list(), key=lambda f: f.id)

    def create_festival(self, name, location, start_date, end_date):
        festival = Festival(0, name, location, TimeSlot(start_date, end_date))
        with self.uow as uow:
            saved = uow.festivals.save(festival)
            uow.commit()
        return saved

    def list_artists(self):
        with self.uow as uow:
            return sorted(uow.artists.list(), key=lambda a: a.name)

    def create_artist(self, name, genre, required_equipment):
        artist = Artist(0, name, genre, Equipment(frozenset(required_equipment)))
        with self.uow as uow:
            if any(a.name == name for a in uow.artists.list()):
                raise DomainError('Un artiste de ce nom existe déjà')
            saved = uow.artists.save(artist)
            uow.commit()
        return saved

    def list_stages(self, festival_id):
        with self.uow as uow:
            return [s for s in uow.stages.list() if s.festival_id == festival_id]

    def create_stage(self, festival_id, name, capacity, available_equipment):
        stage = Stage(0, festival_id, name, capacity, Equipment(frozenset(available_equipment)))
        with self.uow as uow:
            required(uow.festivals, festival_id, 'Festival').require_editable()
            saved = uow.stages.save(stage)
            uow.commit()
        return saved

    def get_concert(self, concert_id):
        with self.uow as uow:
            return required(uow.concerts, concert_id, 'Concert')

    def list_concerts(self, festival_id):
        with self.uow as uow:
            return sorted((c for c in uow.concerts.list()
                           if c.festival_id == festival_id and c.status != 'cancelled'),
                          key=lambda c: (c.start_time, c.id))

    @staticmethod
    def _planning(uow, festival_id):
        festival = required(uow.festivals, festival_id, 'Festival')
        concerts = uow.concerts.list()
        return Planning(festival, tuple(c for c in concerts if c.festival_id == festival_id)), concerts

    @staticmethod
    def _program(uow, concert):
        planning, concerts = FestiPlan._planning(uow, concert.festival_id)
        artist = required(uow.artists, concert.artist_id, 'Artiste')
        stage = required(uow.stages, concert.stage_id, 'Scène')
        return planning.program(concert, artist, stage, concerts)

    def schedule(self, command: ScheduleConcert):
        concert = Concert(0, command.festival_id, command.artist_id, command.stage_id,
                          TimeSlot(command.start_time, command.end_time))
        with self.uow as uow:
            saved = uow.concerts.save(self._program(uow, concert))
            uow.commit()
        return saved

    def reschedule(self, command: RescheduleConcert):
        slot = TimeSlot(command.start_time, command.end_time)
        with self.uow as uow:
            concert = required(uow.concerts, command.concert_id, 'Concert')
            candidate = replace(concert, slot=slot)
            saved = uow.concerts.save(self._program(uow, candidate))
            uow.commit()
        return self._notify(saved, ConcertRescheduled(saved.id, slot))

    def cancel(self, concert_id):
        with self.uow as uow:
            concert = required(uow.concerts, concert_id, 'Concert')
            planning, _ = self._planning(uow, concert.festival_id)
            saved = uow.concerts.save(planning.cancel(concert))
            uow.commit()
        return saved

    def publish(self, festival_id):
        with self.uow as uow:
            planning, concerts = self._planning(uow, festival_id)
            artists, stages = {}, {}
            for concert in planning.concerts:
                if concert.status != 'cancelled':
                    artists[concert.artist_id] = required(uow.artists, concert.artist_id, 'Artiste')
                    stages[concert.stage_id] = required(uow.stages, concert.stage_id, 'Scène')
            saved = uow.festivals.save(planning.publish(artists, stages, concerts))
            uow.commit()
        return self._notify(saved, PlanningPublished(saved.id))

    def unpublish(self, festival_id):
        with self.uow as uow:
            festival = required(uow.festivals, festival_id, 'Festival')
            saved = uow.festivals.save(festival.unpublish())
            uow.commit()
        return self._notify(saved, PlanningUnpublished(saved.id))

    def report_incident(self, concert_id, description, occurred_at=None):
        incident = Incident(0, concert_id, description,
                            occurred_at or datetime.now(timezone.utc))
        with self.uow as uow:
            required(uow.concerts, concert_id, 'Concert')
            saved = uow.incidents.save(incident)
            uow.commit()
        return saved

    def list_incidents(self, concert_id=None):
        with self.uow as uow:
            return sorted((i for i in uow.incidents.list()
                           if concert_id is None or i.concert_id == concert_id),
                          key=lambda i: i.occurred_at, reverse=True)
