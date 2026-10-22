from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum

from .errors import DomainError, NotFound, StateConflict


def utc_naive(value: datetime) -> datetime:
    """Legacy SQLite stores naive datetimes; aware inputs are converted to UTC."""
    try:
        return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value
    except OverflowError as exc:
        raise DomainError('La date est hors de la plage représentable en UTC') from exc


def non_blank(value: str, label: str) -> None:
    if not value.strip():
        raise DomainError(f'{label} ne doit pas être vide')


@dataclass(frozen=True)
class TimeSlot:
    start: datetime
    end: datetime

    def __post_init__(self):
        object.__setattr__(self, 'start', utc_naive(self.start))
        object.__setattr__(self, 'end', utc_naive(self.end))
        if self.end <= self.start:
            raise DomainError('La fin doit être strictement postérieure au début')

    def overlaps(self, other: 'TimeSlot') -> bool:
        return self.start < other.end and other.start < self.end

    def contains(self, other: 'TimeSlot') -> bool:
        return self.start <= other.start and other.end <= self.end


@dataclass(frozen=True)
class Equipment:
    items: frozenset[str] = frozenset()

    def __post_init__(self):
        normalized = frozenset(x.strip() for x in self.items)
        if any(not x or ',' in x for x in normalized):
            raise DomainError('Un équipement doit avoir un nom non vide, sans virgule')
        object.__setattr__(self, 'items', normalized)

    def supports(self, required: 'Equipment') -> bool:
        return required.items <= self.items


class PlanningStatus(str, Enum):
    PREPARATION = 'preparation'
    PUBLISHED = 'published'


@dataclass(frozen=True)
class Festival:
    id: int
    name: str
    location: str
    period: TimeSlot
    status: PlanningStatus = PlanningStatus.PREPARATION

    def __post_init__(self):
        non_blank(self.name, 'Le nom')
        non_blank(self.location, 'Le lieu')
        try:
            object.__setattr__(self, 'status', PlanningStatus(self.status))
        except ValueError as exc:
            raise DomainError('État de planning inconnu') from exc

    @property
    def start_date(self):
        return self.period.start

    @property
    def end_date(self):
        return self.period.end

    def require_editable(self):
        if self.status != PlanningStatus.PREPARATION:
            raise StateConflict('Le planning est publié : dépubliez-le explicitement avant modification')

    def publish(self):
        self.require_editable()
        return replace(self, status=PlanningStatus.PUBLISHED)

    def unpublish(self):
        if self.status != PlanningStatus.PUBLISHED:
            raise StateConflict('Seul un planning publié peut être dépublié')
        return replace(self, status=PlanningStatus.PREPARATION)


@dataclass(frozen=True)
class Artist:
    id: int
    name: str
    genre: str
    equipment: Equipment = Equipment()

    def __post_init__(self):
        non_blank(self.name, 'Le nom')
        non_blank(self.genre, 'Le genre')

    @property
    def required_equipment(self):
        return sorted(self.equipment.items)


@dataclass(frozen=True)
class Stage:
    id: int
    festival_id: int
    name: str
    capacity: int
    equipment: Equipment = Equipment()

    def __post_init__(self):
        non_blank(self.name, 'Le nom')
        if self.capacity <= 0:
            raise DomainError('La capacité doit être strictement positive')
        if self.festival_id <= 0:
            raise DomainError('Identifiant du festival invalide')

    @property
    def available_equipment(self):
        return sorted(self.equipment.items)


@dataclass(frozen=True)
class Concert:
    id: int
    festival_id: int
    artist_id: int
    stage_id: int
    slot: TimeSlot
    status: str = 'scheduled'

    def __post_init__(self):
        if min(self.festival_id, self.artist_id, self.stage_id) <= 0:
            raise DomainError('Identifiants du concert invalides')
        if self.status not in ('scheduled', 'cancelled'):
            raise DomainError('État du concert inconnu')

    @property
    def start_time(self):
        return self.slot.start

    @property
    def end_time(self):
        return self.slot.end


@dataclass(frozen=True)
class Incident:
    id: int
    concert_id: int
    description: str
    occurred_at: datetime
    resolved: bool = False

    def __post_init__(self):
        if self.concert_id <= 0:
            raise DomainError('Identifiant du concert invalide')
        non_blank(self.description, "La description de l'incident")
        object.__setattr__(self, 'occurred_at', utc_naive(self.occurred_at))


def validate_programming(concert: Concert, festival: Festival, artist: Artist,
                         stage: Stage, others: list[Concert]) -> None:
    """Single policy for creation, rescheduling and full publication validation."""
    if (concert.festival_id != festival.id or concert.artist_id != artist.id
            or concert.stage_id != stage.id or stage.festival_id != festival.id):
        raise DomainError("La scène, l'artiste et le festival doivent correspondre au concert")
    if not festival.period.contains(concert.slot):
        raise DomainError('Le concert doit se dérouler entièrement pendant le festival')
    if not stage.equipment.supports(artist.equipment):
        raise DomainError('La scène ne dispose pas de tous les équipements requis')
    for other in others:
        if (other.id == concert.id and concert.id != 0) or other.status == 'cancelled':
            continue
        if concert.slot.overlaps(other.slot):
            if other.stage_id == concert.stage_id:
                raise DomainError('Conflit : la scène est déjà occupée')
            if other.artist_id == concert.artist_id:
                raise DomainError("Conflit : l'artiste est déjà programmé")


@dataclass(frozen=True)
class Planning:
    """Aggregate rooted in Festival, with its active Concert children."""
    festival: Festival
    concerts: tuple[Concert, ...]

    def __post_init__(self):
        object.__setattr__(self, 'concerts', tuple(self.concerts))
        ids = [c.id for c in self.concerts if c.id]
        if len(ids) != len(set(ids)):
            raise DomainError('Un concert ne peut figurer deux fois dans le planning')
        if any(c.festival_id != self.festival.id for c in self.concerts):
            raise DomainError("Les concerts du planning doivent appartenir au même festival")

    def _require_member(self, concert: Concert) -> None:
        if concert.festival_id != self.festival.id or not any(
                child.id == concert.id for child in self.concerts):
            raise DomainError("Le concert n'appartient pas à ce planning")

    def program(self, concert: Concert, artist: Artist, stage: Stage,
                global_concerts: list[Concert]) -> Concert:
        self.festival.require_editable()
        if concert.status != 'scheduled':
            raise StateConflict('Un concert annulé ne peut pas être déplacé')
        if concert.id:
            self._require_member(concert)
        validate_programming(concert, self.festival, artist, stage,
                             [*self.concerts, *global_concerts])
        return concert

    def cancel(self, concert: Concert) -> Concert:
        self.festival.require_editable()
        self._require_member(concert)
        return replace(concert, status='cancelled')

    def publish(self, artists: dict[int, Artist], stages: dict[int, Stage],
                global_concerts: list[Concert]) -> Festival:
        self.festival.require_editable()
        for concert in self.concerts:
            if concert.status != 'cancelled':
                artist, stage = artists.get(concert.artist_id), stages.get(concert.stage_id)
                if artist is None or stage is None:
                    raise NotFound('Artiste ou scène introuvable')
                validate_programming(concert, self.festival, artist, stage,
                                     [*self.concerts, *global_concerts])
        return self.festival.publish()
