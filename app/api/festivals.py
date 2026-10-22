from fastapi import APIRouter, Depends, Response
from app.application.service import FestiPlan
from app.composition import get_service
from app.schemas import FestivalCreate, FestivalRead

router = APIRouter(prefix='/festivals', tags=['festivals'])


@router.get('', response_model=list[FestivalRead])
def list_festivals(service: FestiPlan = Depends(get_service)):
    return service.list_festivals()


@router.post('', response_model=FestivalRead, status_code=201)
def create_festival(payload: FestivalCreate, service: FestiPlan = Depends(get_service)):
    return service.create_festival(**payload.model_dump())


@router.post('/{festival_id}/publish', response_model=FestivalRead)
def publish_festival(festival_id: int, response: Response, service: FestiPlan = Depends(get_service)):
    result = service.publish(festival_id)
    response.headers['X-Notification-Status'] = result.notification_status
    return result.value


@router.post('/{festival_id}/unpublish', response_model=FestivalRead)
def unpublish_festival(festival_id: int, response: Response, service: FestiPlan = Depends(get_service)):
    result = service.unpublish(festival_id)
    response.headers['X-Notification-Status'] = result.notification_status
    return result.value
