from dataclasses import replace
from datetime import datetime, timedelta, timezone
import pytest

from app.domain.errors import DomainError, StateConflict
from app.domain.model import (Artist, Concert, Equipment, Festival, Incident, Planning,
                              PlanningStatus, Stage, TimeSlot, validate_programming)

D = datetime(2027, 6, 18, 18)


def fixture():
    festival = Festival(1, 'Hellforge', 'Clisson', TimeSlot(D - timedelta(hours=8), D + timedelta(days=2)))
    artist = Artist(1, 'Iron Vow', 'Metal', Equipment(frozenset({'lights'})))
    stage = Stage(1, 1, 'Mainstage', 100, Equipment(frozenset({'lights', 'rigging'})))
    concert = Concert(1, 1, 1, 1, TimeSlot(D, D + timedelta(hours=1)))
    return festival, artist, stage, concert


@pytest.mark.parametrize('offset', [0, -1])
def test_r1_strictly_positive_duration(offset):
    with pytest.raises(DomainError):
        TimeSlot(D, D + timedelta(hours=offset))


def test_time_slot_is_immutable_and_adjacent_intervals_do_not_overlap():
    slot = TimeSlot(D, D + timedelta(hours=1))
    assert not slot.overlaps(TimeSlot(slot.end, slot.end + timedelta(hours=1)))
    assert slot.overlaps(TimeSlot(D + timedelta(minutes=59), D + timedelta(hours=2)))
    with pytest.raises(AttributeError):
        slot.start = D


def test_aware_input_normalizes_to_utc_and_compares_to_naive_legacy_data():
    local = D.replace(tzinfo=timezone(timedelta(hours=2)))
    assert TimeSlot(local, local + timedelta(hours=1)) == TimeSlot(D - timedelta(hours=2), D - timedelta(hours=1))


@pytest.mark.parametrize('other_stage, other_artist', [(1, 2), (2, 1)])
def test_r2_r3_conflicts_on_stage_or_artist(other_stage, other_artist):
    festival, artist, stage, concert = fixture()
    other = Concert(2, 1, other_artist, other_stage, concert.slot)
    with pytest.raises(DomainError, match='Conflit'):
        validate_programming(concert, festival, artist, stage, [other])


def test_global_artist_conflict_applies_across_festivals():
    festival, artist, stage, concert = fixture()
    other = Concert(2, 2, 1, 2, concert.slot)
    with pytest.raises(DomainError, match='artiste'):
        validate_programming(concert, festival, artist, stage, [other])


def test_cancelled_concert_and_current_concert_do_not_conflict():
    festival, artist, stage, concert = fixture()
    cancelled = replace(concert, id=2, status='cancelled')
    validate_programming(concert, festival, artist, stage, [concert, cancelled])


def test_r4_stage_must_belong_to_festival():
    festival, artist, stage, concert = fixture()
    with pytest.raises(DomainError):
        validate_programming(concert, festival, artist, replace(stage, festival_id=2), [])


def test_r5_equipment_is_checked_in_domain():
    festival, artist, stage, concert = fixture()
    with pytest.raises(DomainError, match='équipements'):
        validate_programming(concert, festival, artist, replace(stage, equipment=Equipment()), [])


@pytest.mark.parametrize('offset', [-9, 48])
def test_r6_entire_concert_inside_festival(offset):
    festival, artist, stage, concert = fixture()
    invalid = replace(concert, slot=TimeSlot(D + timedelta(hours=offset), D + timedelta(hours=offset+1)))
    with pytest.raises(DomainError, match='festival'):
        validate_programming(invalid, festival, artist, stage, [])


def test_festival_boundaries_are_inclusive():
    festival, artist, stage, concert = fixture()
    validate_programming(replace(concert, slot=festival.period), festival, artist, stage, [])


def test_r7_published_planning_blocks_programming_and_cancellation():
    festival, artist, stage, concert = fixture()
    planning = Planning(festival.publish(), (concert,))
    with pytest.raises(StateConflict):
        planning.program(concert, artist, stage, [])
    with pytest.raises(StateConflict):
        planning.cancel(concert)


def test_state_transitions_are_explicit():
    festival, _, _, _ = fixture()
    with pytest.raises(StateConflict):
        festival.unpublish()
    published = festival.publish()
    assert published.status == PlanningStatus.PUBLISHED
    with pytest.raises(StateConflict):
        published.publish()
    assert published.unpublish().status == PlanningStatus.PREPARATION


def test_r8_publication_revalidates_every_concert():
    festival, artist, stage, concert = fixture()
    conflict = replace(concert, id=2)
    planning = Planning(festival, (concert, conflict))
    with pytest.raises(DomainError, match='Conflit'):
        planning.publish({1: artist}, {1: stage}, [concert, conflict])


@pytest.mark.parametrize('capacity', [0, -1])
def test_r9_capacity_validated_without_http(capacity):
    with pytest.raises(DomainError, match='capacité'):
        Stage(0, 1, 'Temple', capacity)


@pytest.mark.parametrize('description', ['', '   ', '\n\t'])
def test_r10_incident_description_not_blank(description):
    with pytest.raises(DomainError, match='description'):
        Incident(0, 1, description, D)


def test_equipment_normalizes_duplicates_and_spaces():
    assert Equipment(frozenset({' lights ', 'lights'})).items == frozenset({'lights'})


@pytest.mark.parametrize('name', ['', '  ', 'lights,rigging'])
def test_invalid_equipment_name(name):
    with pytest.raises(DomainError):
        Equipment(frozenset({name}))


def test_cancelled_concert_cannot_be_rescheduled():
    festival, artist, stage, concert = fixture()
    with pytest.raises(StateConflict):
        Planning(festival, ()).program(replace(concert, status='cancelled'), artist, stage, [])


def test_aggregate_checks_own_concerts_when_external_snapshot_is_empty():
    festival, artist, stage, concert = fixture()
    candidate = replace(concert, id=0)
    with pytest.raises(DomainError, match='Conflit'):
        Planning(festival, (concert,)).program(candidate, artist, stage, [])


def test_aggregate_publication_checks_own_concerts_without_external_snapshot():
    festival, artist, stage, concert = fixture()
    conflict = replace(concert, id=2)
    with pytest.raises(DomainError, match='Conflit'):
        Planning(festival, (concert, conflict)).publish({1: artist}, {1: stage}, [])


@pytest.mark.parametrize('operation', ['program', 'cancel'])
def test_aggregate_cannot_modify_an_entity_it_does_not_contain(operation):
    festival, artist, stage, concert = fixture()
    planning = Planning(festival, ())
    with pytest.raises(DomainError):
        if operation == 'program':
            planning.program(concert, artist, stage, [])
        else:
            planning.cancel(concert)


def test_utc_conversion_outside_datetime_range_is_a_business_error():
    low = datetime.min.replace(tzinfo=timezone(timedelta(hours=2)))
    with pytest.raises(DomainError):
        TimeSlot(low, low + timedelta(hours=1))


@pytest.mark.parametrize('missing', ['artist', 'stage'])
def test_aggregate_reports_missing_publication_reference_as_business_error(missing):
    festival, artist, stage, concert = fixture()
    with pytest.raises(DomainError, match='introuvable'):
        Planning(festival, (concert,)).publish(
            {} if missing == 'artist' else {artist.id: artist},
            {} if missing == 'stage' else {stage.id: stage}, [])


@pytest.mark.parametrize('invalid', ['duplicate', 'wrong_festival'])
def test_aggregate_rejects_ambiguous_or_foreign_children(invalid):
    festival, _, _, concert = fixture()
    children = [concert, concert] if invalid == 'duplicate' else [replace(concert, festival_id=2)]
    with pytest.raises(DomainError):
        Planning(festival, children)


def test_aggregate_copies_a_mutable_collection_of_children():
    festival, _, _, concert = fixture()
    children = [concert]
    planning = Planning(festival, children)
    children.clear()
    assert planning.concerts == (concert,)
