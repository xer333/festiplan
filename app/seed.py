"""Demonstration data. No data is erased unless --reset is explicitly passed."""
import argparse
from datetime import datetime
from sqlalchemy import select
from app.database import Base, SessionLocal, engine
from app import models
from app.adapters.persistence import SqlUnitOfWork
from app.domain.model import Artist, Concert, Equipment, Festival, Planning, Stage, TimeSlot

ARTISTS = [('Iron Vow', 'Heavy metal', ['large_rigging', 'special_lighting']),
 ('Crimson Engine', 'Thrash metal', ['special_lighting']),
 ('The Last Citadel', 'Power metal', ['large_rigging']),
 ('Concrete Reign', 'Hardcore', []),
 ('Ashes of Tomorrow', 'Metalcore', ['special_lighting']),
 ('Static Violence', 'Punk', []),
 ('Hollow Mountain', 'Stoner', ['special_lighting']),
 ('Solar Funeral', 'Doom metal', []),
 ('Desert Crown', 'Sludge', []),
 ('Winter Throne', 'Black metal', ['special_lighting']),
 ('Nocturnal Veil', 'Black metal', []),
 ('Pale Kingdom', 'Atmospheric metal', ['special_lighting'])]

STAGES = [('Mainstage', 50000, ['large_rigging', 'special_lighting', 'pyrotechnics']),
 ('Warzone', 15000, ['special_lighting']),
 ('Valley', 8000, ['special_lighting']),
 ('Temple', 10000, ['special_lighting'])]

SHOWS = [('Iron Vow', 'Mainstage', '2027-06-18T18:00:00', '2027-06-18T19:00:00'),
 ('Crimson Engine', 'Mainstage', '2027-06-18T19:30:00', '2027-06-18T20:30:00'),
 ('The Last Citadel', 'Mainstage', '2027-06-18T21:00:00', '2027-06-18T22:00:00'),
 ('Concrete Reign', 'Warzone', '2027-06-18T17:00:00', '2027-06-18T17:45:00'),
 ('Ashes of Tomorrow', 'Warzone', '2027-06-18T18:15:00', '2027-06-18T19:00:00'),
 ('Hollow Mountain', 'Valley', '2027-06-18T19:00:00', '2027-06-18T20:00:00'),
 ('Solar Funeral', 'Valley', '2027-06-18T20:30:00', '2027-06-18T21:30:00'),
 ('Winter Throne', 'Temple', '2027-06-18T20:00:00', '2027-06-18T21:00:00'),
 ('Nocturnal Veil', 'Temple', '2027-06-18T21:30:00', '2027-06-18T22:30:00'),
 ('Static Violence', 'Warzone', '2027-06-19T14:00:00', '2027-06-19T14:45:00'),
 ('Desert Crown', 'Valley', '2027-06-19T15:00:00', '2027-06-19T16:00:00'),
 ('Pale Kingdom', 'Temple', '2027-06-19T16:30:00', '2027-06-19T17:30:00'),
 ('Iron Vow', 'Mainstage', '2027-06-19T21:00:00', '2027-06-19T22:00:00'),
 ('Crimson Engine', 'Mainstage', '2027-06-20T20:00:00', '2027-06-20T21:00:00')]


def seed(reset=False):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        with SqlUnitOfWork(db) as uow:
            populated = any(db.execute(select(table).limit(1)).first() is not None
                            for table in Base.metadata.sorted_tables)
            if populated and not reset:
                raise RuntimeError('La base contient déjà des données. Utilisez --reset pour la réinitialiser.')
            if reset:
                for table in reversed(Base.metadata.sorted_tables):
                    db.execute(table.delete())
            festival = uow.festivals.save(Festival(0, 'Hellforge Open Air', 'Clisson-sur-Rivière',
                TimeSlot(datetime.fromisoformat('2027-06-18T10:00:00'),
                         datetime.fromisoformat('2027-06-20T23:59:00'))))
            artists = {name: uow.artists.save(Artist(0, name, genre, Equipment(frozenset(equipment))))
                       for name, genre, equipment in ARTISTS}
            stages = {name: uow.stages.save(Stage(0, festival.id, name, capacity, Equipment(frozenset(equipment))))
                      for name, capacity, equipment in STAGES}
            concerts = []
            for artist_name, stage_name, start, end in SHOWS:
                artist, stage = artists[artist_name], stages[stage_name]
                concert = Concert(0, festival.id, artist.id, stage.id,
                                  TimeSlot(datetime.fromisoformat(start), datetime.fromisoformat(end)))
                planning = Planning(festival, tuple(concerts))
                concerts.append(uow.concerts.save(planning.program(concert, artist, stage, concerts)))
            uow.commit()
    print('Données chargées : Hellforge Open Air, 4 scènes, 12 artistes, 14 concerts.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reset', action='store_true', help='Effacer les données existantes avant initialisation')
    args = parser.parse_args()
    try:
        seed(reset=args.reset)
    except RuntimeError as exc:
        parser.exit(1, str(exc) + chr(10))
