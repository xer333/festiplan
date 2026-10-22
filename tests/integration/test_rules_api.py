from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import Mock

import pytest

from app import models
from app.config import settings
from ._database import SessionLocal
from app.adapters.persistence import SqlUnitOfWork
from app.application.commands import RescheduleConcert, ScheduleConcert
from app.application.service import FestiPlan
from app.domain.errors import DomainError
from app.domain.errors import NotFound
from .test_regressions import setup_schedule, move


def concert_payload(festival, artist, stage, start='18:00', end='19:00'):
    return dict(festival_id=festival['id'], artist_id=artist['id'], stage_id=stage['id'],
                start_time=f'2027-06-18T{start}:00', end_time=f'2027-06-18T{end}:00')


def test_swagger_and_openapi_expose_existing_and_new_operations(client):
    assert client.get('/docs').status_code == 200
    paths = client.get('/openapi.json').json()['paths']
    assert '/festivals/{festival_id}/unpublish' in paths
    assert '/concerts/{concert_id}/reschedule' in paths
    assert '/incidents' in paths


def test_artist_conflict_different_stages_rejected_on_create_and_move(client):
    festival, artists, stages, concerts = setup_schedule(client)
    assert client.post('/concerts', json=concert_payload(festival, artists[0], stages[1])).status_code == 400
    other = client.post('/concerts', json=concert_payload(festival, artists[0], stages[1], '22:00', '23:00')).json()
    assert move(client, other, '18:15', '19:15').status_code == 400
    assert client.get(f"/concerts/{other['id']}").json() == other


def test_artist_cannot_overlap_in_another_festival(client):
    _, artists, _, _ = setup_schedule(client)
    festival = client.post('/festivals', json=dict(name='Other Festival', location='Nantes',
        start_date='2027-06-18T10:00:00', end_date='2027-06-20T23:00:00')).json()
    stage = client.post('/stages', json=dict(festival_id=festival['id'], name='Other Stage', capacity=100)).json()
    assert client.post('/concerts', json=concert_payload(festival, artists[0], stage)).status_code == 400


def test_adjacent_concert_is_allowed_and_cancelled_slot_is_reusable(client):
    festival, artists, stages, concerts = setup_schedule(client)
    assert client.post('/concerts', json=concert_payload(festival, artists[1], stages[0], '19:00', '20:00')).status_code == 201
    assert client.post(f"/concerts/{concerts[0]['id']}/cancel").status_code == 200
    assert client.post('/concerts', json=concert_payload(festival, artists[1], stages[0])).status_code == 201
    assert concerts[0]['id'] not in [c['id'] for c in client.get(f"/concerts?festival_id={festival['id']}").json()]
    assert move(client, concerts[0], '16:00', '17:00').status_code == 409


def test_wrong_festival_stage_is_rejected(client):
    festival, artists, _, _ = setup_schedule(client)
    other = client.post('/festivals', json=dict(name='Other Festival', location='Nantes',
        start_date='2027-06-18T10:00:00', end_date='2027-06-20T23:00:00')).json()
    stage = client.post('/stages', json=dict(festival_id=other['id'], name='Other Stage', capacity=10)).json()
    assert client.post('/concerts', json=concert_payload(festival, artists[0], stage)).status_code == 400


def test_missing_equipment_rejected(client):
    festival, _, stages, _ = setup_schedule(client)
    artist = client.post('/artists', json=dict(name='Rigging Band', genre='Metal', required_equipment=['rigging'])).json()
    assert client.post('/concerts', json=concert_payload(festival, artist, stages[1], '16:00', '17:00')).status_code == 400


@pytest.mark.parametrize('start,end', [('09:00', '10:30'), ('09:00', '10:00')])
def test_move_outside_festival_rejected_without_change(client, start, end):
    _, _, _, concerts = setup_schedule(client)
    assert move(client, concerts[0], start, end).status_code == 400
    assert client.get(f"/concerts/{concerts[0]['id']}").json() == concerts[0]


def test_published_planning_blocks_all_ordinary_writes_then_can_be_reopened(client):
    festival, artists, stages, concerts = setup_schedule(client)
    path = f"/festivals/{festival['id']}"
    assert client.post(path + '/publish').status_code == 200
    assert client.post(path + '/publish').status_code == 409
    assert client.post(f"/concerts/{concerts[0]['id']}/cancel").status_code == 409
    assert client.post('/concerts', json=concert_payload(festival, artists[0], stages[0], '16:00', '17:00')).status_code == 409
    assert client.post('/stages', json=dict(festival_id=festival['id'], name='New Stage', capacity=10)).status_code == 409
    assert client.post(path + '/unpublish').status_code == 200
    assert client.post(path + '/unpublish').status_code == 409
    assert move(client, concerts[0], '16:00', '17:00').status_code == 200


@pytest.mark.parametrize('corruption', ['overlap', 'equipment', 'duration', 'capacity', 'festival_period'])
def test_publication_rechecks_sql_data_and_preserves_preparation_on_error(client, corruption):
    festival, artists, stages, concerts = setup_schedule(client)
    with SessionLocal() as db:
        if corruption == 'overlap':
            row = db.get(models.Concert, concerts[1]['id'])
            row.start_time = datetime(2027, 6, 18, 18, 30)
        elif corruption == 'equipment':
            db.get(models.Artist, artists[0]['id']).required_equipment = 'unavailable'
        elif corruption == 'duration':
            row = db.get(models.Concert, concerts[0]['id'])
            row.end_time = row.start_time
        elif corruption == 'capacity':
            db.get(models.Stage, stages[0]['id']).capacity = 0
        else:
            db.get(models.Festival, festival['id']).end_date = datetime(2027, 6, 18, 19)
        db.commit()
    assert client.post(f"/festivals/{festival['id']}/publish").status_code == 400
    assert client.get('/festivals').json()[0]['status'] == 'preparation'


def test_publish_notification_failure_is_success_with_explicit_status(client, monkeypatch):
    festival, _, _, _ = setup_schedule(client)
    monkeypatch.setattr(settings, 'fail_notifications', True)
    response = client.post(f"/festivals/{festival['id']}/publish")
    assert response.status_code == 200
    assert response.headers['X-Notification-Status'] == 'failed'
    assert client.get('/festivals').json()[0]['status'] == 'published'


def test_incident_reference_whitespace_and_filtering(client):
    _, _, _, concerts = setup_schedule(client)
    assert client.post('/incidents', json=dict(concert_id=999, description='Power failure')).status_code == 404
    assert client.post('/incidents', json=dict(concert_id=concerts[0]['id'], description='   ')).status_code == 400
    incident = client.post('/incidents', json=dict(concert_id=concerts[0]['id'], description='Power failure'))
    assert incident.status_code == 201
    assert incident.json()['occurred_at']
    assert client.get(f"/incidents?concert_id={concerts[1]['id']}").json() == []
    assert client.get('/incidents').json() == [incident.json()]


def test_duplicate_artist_returns_business_error(client):
    setup_schedule(client)
    assert client.post('/artists', json=dict(name='First Band', genre='Metal')).status_code == 400


def test_unknown_get_move_cancel_and_unpublish_return_404(client):
    assert client.get('/concerts/999').status_code == 404
    assert move(client, {'id': 999}, '16:00', '17:00').status_code == 404
    assert client.post('/concerts/999/cancel').status_code == 404
    assert client.post('/festivals/999/unpublish').status_code == 404


def test_aware_input_is_normalized_before_sql_persistence(client):
    _, _, _, concerts = setup_schedule(client)
    response = client.patch(f"/concerts/{concerts[0]['id']}/reschedule", json=dict(
        start_time='2027-06-18T18:00:00+02:00', end_time='2027-06-18T19:00:00+02:00'))
    assert response.status_code == 200
    assert response.json()['start_time'] == '2027-06-18T16:00:00'


def test_schedule_is_sorted_by_time(client):
    festival, _, _, concerts = setup_schedule(client)
    move(client, concerts[0], '22:00', '23:00')
    response = client.get(f"/concerts/schedule/{festival['id']}")
    assert [c['id'] for c in response.json()] == [concerts[1]['id'], concerts[0]['id']]


def test_sql_commit_failure_rolls_back_and_does_not_notify(client, monkeypatch):
    _, _, _, concerts = setup_schedule(client)
    notifier = Mock()
    with SessionLocal() as db:
        def fail():
            raise RuntimeError('disk unavailable')
        monkeypatch.setattr(db, 'commit', fail)
        service = FestiPlan(SqlUnitOfWork(db), notifier)
        with pytest.raises(RuntimeError, match='disk'):
            service.reschedule(RescheduleConcert(concerts[0]['id'],
                datetime(2027, 6, 18, 16), datetime(2027, 6, 18, 17)))
    notifier.notify.assert_not_called()
    assert client.get(f"/concerts/{concerts[0]['id']}").json() == concerts[0]


def test_sqlite_concurrent_scheduling_cannot_double_book(client):
    festival, artists, stages, _ = setup_schedule(client)
    barrier = Barrier(2)

    def schedule(artist):
        with SessionLocal() as db:
            service = FestiPlan(SqlUnitOfWork(db), Mock())
            barrier.wait(timeout=5)
            try:
                service.schedule(ScheduleConcert(festival['id'], artist['id'], stages[0]['id'],
                    datetime(2027, 6, 18, 22), datetime(2027, 6, 18, 23)))
                return 'created'
            except DomainError:
                return 'refused'

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(schedule, artists))
    assert sorted(results) == ['created', 'refused']


def test_repository_does_not_recreate_an_unknown_entity_with_new_identity(client):
    from dataclasses import replace
    _, _, _, concerts = setup_schedule(client)
    with SessionLocal() as db:
        with SqlUnitOfWork(db) as uow:
            concert = uow.concerts.get(concerts[0]['id'])
            with pytest.raises(NotFound):
                uow.concerts.save(replace(concert, id=999))
            assert len(uow.concerts.list()) == 2


def test_http_read_accepts_festival_created_by_non_http_use_case(client):
    with SessionLocal() as db:
        service = FestiPlan(SqlUnitOfWork(db), Mock())
        service.create_festival('X', 'Y', datetime(2027, 6, 18), datetime(2027, 6, 20))
    response = client.get('/festivals')
    assert response.status_code == 200
    assert response.json()[0]['name'] == 'X'


@pytest.mark.parametrize('start,end', [
    ('0001-01-01T00:00:00+02:00', '0001-01-01T01:00:00+02:00'),
    ('9999-12-31T22:00:00-02:00', '9999-12-31T23:00:00-02:00')])
def test_out_of_range_utc_dates_return_400_without_server_error(client, start, end):
    response = client.post('/festivals', json=dict(
        name='Boundary Festival', location='Clisson', start_date=start, end_date=end))
    assert response.status_code == 400
    assert client.get('/festivals').json() == []
