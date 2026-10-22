from fastapi import APIRouter, Depends
from app.application.service import FestiPlan
from app.composition import get_service
from app.schemas import IncidentCreate, IncidentRead

router = APIRouter(prefix='/incidents', tags=['incidents'])


@router.post('', response_model=IncidentRead, status_code=201)
def create_incident(payload: IncidentCreate, service: FestiPlan = Depends(get_service)):
    return service.report_incident(**payload.model_dump())


@router.get('', response_model=list[IncidentRead])
def list_incidents(concert_id: int | None = None, service: FestiPlan = Depends(get_service)):
    return service.list_incidents(concert_id)
