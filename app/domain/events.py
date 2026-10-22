from dataclasses import dataclass
from .model import TimeSlot


@dataclass(frozen=True)
class ConcertRescheduled:
    concert_id: int
    slot: TimeSlot


@dataclass(frozen=True)
class PlanningPublished:
    festival_id: int


@dataclass(frozen=True)
class PlanningUnpublished:
    festival_id: int


DomainEvent = ConcertRescheduled | PlanningPublished | PlanningUnpublished
