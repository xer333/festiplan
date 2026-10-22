"""The three defects from the assignment, reproduced on the original API."""
from app.config import settings


def setup_schedule(client):
    festival = client.post('/festivals', json=dict(
        name='Regression Fest', location='Clisson',
        start_date='2027-06-18T10:00:00', end_date='2027-06-20T23:00:00')).json()
    artists = [client.post('/artists', json=dict(name=name, genre='Metal')).json()
               for name in ('First Band', 'Second Band')]
    stages = [client.post('/stages', json=dict(
        festival_id=festival['id'], name=name, capacity=100)).json()
        for name in ('Mainstage', 'Temple')]
    concerts = []
    for index in range(2):
        concerts.append(client.post('/concerts', json=dict(
            festival_id=festival['id'], artist_id=artists[index]['id'],
            stage_id=stages[0]['id'], start_time=f'2027-06-18T{18 + index * 2}:00:00',
            end_time=f'2027-06-18T{19 + index * 2}:00:00')).json())
    return festival, artists, stages, concerts


def move(client, concert, start='20:15', end='21:15'):
    return client.patch(f"/concerts/{concert['id']}/reschedule", json=dict(
        start_time=f'2027-06-18T{start}:00', end_time=f'2027-06-18T{end}:00'))


def test_regression_move_onto_occupied_stage_is_refused(client):
    _, _, _, concerts = setup_schedule(client)
    assert move(client, concerts[0]).status_code == 400
    assert client.get(f"/concerts/{concerts[0]['id']}").json() == concerts[0]


def test_regression_notification_failure_keeps_success(client, monkeypatch):
    _, _, _, concerts = setup_schedule(client)
    monkeypatch.setattr(settings, 'fail_notifications', True)
    response = move(client, concerts[0], '16:00', '17:00')
    assert response.status_code == 200
    assert response.headers['X-Notification-Status'] == 'failed'
    assert client.get(f"/concerts/{concerts[0]['id']}").json()['start_time'] == '2027-06-18T16:00:00'


def test_regression_published_schedule_refuses_ordinary_move(client):
    festival, _, _, concerts = setup_schedule(client)
    assert client.post(f"/festivals/{festival['id']}/publish").status_code == 200
    assert move(client, concerts[0], '16:00', '17:00').status_code == 409
    assert client.get(f"/concerts/{concerts[0]['id']}").json() == concerts[0]
