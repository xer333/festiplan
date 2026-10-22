from dataclasses import replace
from datetime import datetime, timedelta
import pytest

from app.application.commands import RescheduleConcert, ScheduleConcert
from app.application.service import FestiPlan
from app.domain.errors import DomainError, NotFound, StateConflict
from app.domain.events import ConcertRescheduled
from app.domain.model import Equipment, TimeSlot
from .fakes import MemoryUnitOfWork, RecordingNotifier

D = datetime(2027, 6, 18, 18)


@pytest.fixture
def context():
    uow = MemoryUnitOfWork()
    notifier = RecordingNotifier(uow)
    service = FestiPlan(uow, notifier)
    festival = service.create_festival('Hellforge', 'Clisson', D - timedelta(hours=8), D + timedelta(days=2))
    artist = service.create_artist('Iron Vow', 'Metal', ['lights'])
    stage = service.create_stage(festival.id, 'Mainstage', 100, ['lights'])
    concert = service.schedule(ScheduleConcert(festival.id, artist.id, stage.id, D, D + timedelta(hours=1)))
    return service, uow, notifier, festival, artist, stage, concert


def test_valid_move_persists_before_notification(context):
    service, uow, notifier, _, _, _, concert = context
    start = D + timedelta(hours=2)
    result = service.reschedule(RescheduleConcert(concert.id, start, start + timedelta(hours=1)))
    assert result.notification_status == 'sent'
    assert uow.concerts.get(concert.id).start_time == start
    assert notifier.events == [ConcertRescheduled(concert.id, result.value.slot)]


def test_notification_failure_is_reported_without_undoing_move(context):
    service, uow, notifier, _, _, _, concert = context
    notifier.fail = True
    result = service.reschedule(RescheduleConcert(concert.id, D + timedelta(hours=2), D + timedelta(hours=3)))
    assert result.notification_status == 'failed'
    assert uow.concerts.get(concert.id) == result.value


def test_commit_failure_rolls_back_and_does_not_notify(context):
    service, uow, notifier, _, _, _, concert = context
    uow.fail_commit = True
    with pytest.raises(RuntimeError, match='Storage'):
        service.reschedule(RescheduleConcert(concert.id, D + timedelta(hours=2), D + timedelta(hours=3)))
    assert uow.concerts.get(concert.id) == concert
    assert notifier.events == []


@pytest.mark.parametrize('same_artist', [False, True])
def test_conflicting_move_has_no_write_or_notification(context, same_artist):
    service, uow, notifier, festival, artist, stage, concert = context
    if same_artist:
        stage = service.create_stage(festival.id, 'Temple', 100, ['lights'])
    else:
        artist = service.create_artist('Crimson Engine', 'Metal', [])
    service.schedule(ScheduleConcert(festival.id, artist.id, stage.id, D + timedelta(hours=2), D + timedelta(hours=3)))
    commits = uow.commits
    with pytest.raises(DomainError, match='Conflit'):
        service.reschedule(RescheduleConcert(concert.id, D + timedelta(hours=2), D + timedelta(hours=3)))
    assert uow.concerts.get(concert.id) == concert
    assert uow.commits == commits
    assert notifier.events == []


def test_published_then_explicitly_unpublished_schedule_can_be_changed(context):
    service, _, _, festival, _, _, concert = context
    service.publish(festival.id)
    with pytest.raises(StateConflict):
        service.reschedule(RescheduleConcert(concert.id, D, D + timedelta(hours=1)))
    service.unpublish(festival.id)
    assert service.reschedule(RescheduleConcert(concert.id, D, D + timedelta(hours=1))).value == concert


@pytest.mark.parametrize('corruption', ['stage', 'artist', 'equipment', 'period', 'conflict'])
def test_publication_refuses_inconsistent_imported_data(context, corruption):
    service, uow, notifier, festival, artist, stage, concert = context
    if corruption == 'stage':
        del uow.stages.rows[stage.id]
    elif corruption == 'artist':
        del uow.artists.rows[artist.id]
    elif corruption == 'equipment':
        uow.stages.rows[stage.id] = replace(stage, equipment=Equipment())
    elif corruption == 'period':
        uow.concerts.rows[concert.id] = replace(concert, slot=TimeSlot(D - timedelta(days=1), D))
    else:
        uow.concerts.save(replace(concert, id=0))
    with pytest.raises(DomainError):
        service.publish(festival.id)
    assert uow.festivals.get(festival.id).status == 'preparation'
    assert notifier.events == []


def test_publication_notification_failure_preserves_published_state(context):
    service, uow, notifier, festival, _, _, _ = context
    notifier.fail = True
    assert service.publish(festival.id).notification_status == 'failed'
    assert uow.festivals.get(festival.id).status == 'published'


def test_incident_requires_existing_concert_without_http(context):
    service, _, _, _, _, _, _ = context
    with pytest.raises(NotFound):
        service.report_incident(999, 'Power failure')


def test_incident_can_be_reported_after_publication(context):
    service, _, _, festival, _, _, concert = context
    service.publish(festival.id)
    incident = service.report_incident(concert.id, 'Power failure')
    assert service.list_incidents(concert.id) == [incident]


@pytest.mark.parametrize('reference', ['festival_id', 'artist_id', 'stage_id'])
def test_creation_checks_all_references(context, reference):
    service, _, _, festival, artist, stage, _ = context
    values = dict(festival_id=festival.id, artist_id=artist.id, stage_id=stage.id,
                  start_time=D + timedelta(hours=4), end_time=D + timedelta(hours=5))
    values[reference] = 999
    with pytest.raises(NotFound):
        service.schedule(ScheduleConcert(**values))
