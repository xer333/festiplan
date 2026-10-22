"""Map legacy SQL tables to domain objects; ORM rows never leave this adapter."""
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from app import models as orm
from app.domain import model as domain
from app.domain.errors import DomainError, NotFound


def equipment(value):
    return domain.Equipment(frozenset(x for x in value.split(',') if x))


def decode(row):
    if isinstance(row, orm.Festival):
        return domain.Festival(row.id, row.name, row.location,
                               domain.TimeSlot(row.start_date, row.end_date), row.status)
    if isinstance(row, orm.Artist):
        return domain.Artist(row.id, row.name, row.genre, equipment(row.required_equipment))
    if isinstance(row, orm.Stage):
        return domain.Stage(row.id, row.festival_id, row.name, row.capacity, equipment(row.available_equipment))
    if isinstance(row, orm.Concert):
        return domain.Concert(row.id, row.festival_id, row.artist_id, row.stage_id,
                              domain.TimeSlot(row.start_time, row.end_time), row.status)
    if isinstance(row, orm.Incident):
        return domain.Incident(row.id, row.concert_id, row.description, row.occurred_at, row.resolved)
    raise TypeError(f'Unsupported ORM object: {type(row)}')


def encode(item):
    if isinstance(item, domain.Festival):
        return dict(name=item.name, location=item.location, start_date=item.start_date,
                    end_date=item.end_date, status=item.status.value)
    if isinstance(item, domain.Artist):
        return dict(name=item.name, genre=item.genre, required_equipment=','.join(item.required_equipment))
    if isinstance(item, domain.Stage):
        return dict(festival_id=item.festival_id, name=item.name, capacity=item.capacity,
                    available_equipment=','.join(item.available_equipment))
    if isinstance(item, domain.Concert):
        return dict(festival_id=item.festival_id, artist_id=item.artist_id, stage_id=item.stage_id,
                    start_time=item.start_time, end_time=item.end_time, status=item.status)
    if isinstance(item, domain.Incident):
        return dict(concert_id=item.concert_id, description=item.description,
                    occurred_at=item.occurred_at, resolved=item.resolved)
    raise TypeError(f'Unsupported domain object: {type(item)}')


class SqlRepository:
    def __init__(self, session, model):
        self.session = session
        self.model = model

    def get(self, item_id):
        row = self.session.get(self.model, item_id)
        return decode(row) if row is not None else None

    def list(self):
        return [decode(row) for row in self.session.scalars(select(self.model).order_by(self.model.id))]

    def save(self, item):
        row = self.session.get(self.model, item.id) if item.id else None
        if item.id and row is None:
            raise NotFound('Objet à modifier introuvable')
        if row is None:
            row = self.model(**encode(item))
            self.session.add(row)
        else:
            for name, value in encode(item).items():
                setattr(row, name, value)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise DomainError('Contrainte de persistance : référence invalide ou valeur déjà utilisée') from exc
        return decode(row)


class SqlUnitOfWork:
    def __init__(self, session):
        self.session = session
        for name, model in [('festivals', orm.Festival), ('artists', orm.Artist),
                            ('stages', orm.Stage), ('concerts', orm.Concert), ('incidents', orm.Incident)]:
            setattr(self, name, SqlRepository(session, model))

    def __enter__(self):
        # Serialize SQLite read-check-write, including cross-festival conflicts.
        if self.session.get_bind().dialect.name == 'sqlite':
            self.session.execute(text('BEGIN IMMEDIATE'))
        return self

    def commit(self):
        self.session.commit()

    def __exit__(self, exc_type, exc_value, traceback):
        self.session.rollback()
