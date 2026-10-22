from fastapi import APIRouter, Depends, Response
from app.application.commands import ScheduleConcert, RescheduleConcert
from app.application.service import FestiPlan
from app.composition import get_service
from app.schemas import ConcertCreate, ConcertRead, ConcertReschedule

router = APIRouter(prefix='/concerts', tags=['concerts'])


@router.get('', response_model=list[ConcertRead])
def list_concerts(festival_id: int, service: FestiPlan = Depends(get_service)):
    return service.list_concerts(festival_id)


@router.get('/schedule/{festival_id}', response_model=list[ConcertRead])
def get_schedule(festival_id: int, service: FestiPlan = Depends(get_service)):
    return service.list_concerts(festival_id)


@router.get('/{concert_id}', response_model=ConcertRead)
def get_concert(concert_id: int, service: FestiPlan = Depends(get_service)):
    return service.get_concert(concert_id)


@router.post('', response_model=ConcertRead, status_code=201)
def create_concert(payload: ConcertCreate, service: FestiPlan = Depends(get_service)):
    return service.schedule(ScheduleConcert(**payload.model_dump()))


@router.patch('/{concert_id}/reschedule', response_model=ConcertRead)
def reschedule_concert(concert_id: int, payload: ConcertReschedule, response: Response,
                       service: FestiPlan = Depends(get_service)):
    result = service.reschedule(RescheduleConcert(concert_id, **payload.model_dump()))
    response.headers['X-Notification-Status'] = result.notification_status
    return result.value


@router.post('/{concert_id}/cancel', response_model=ConcertRead)
def cancel_concert(concert_id: int, service: FestiPlan = Depends(get_service)):
    return service.cancel(concert_id)
