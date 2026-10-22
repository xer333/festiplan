from fastapi import APIRouter, Depends
from app.application.service import FestiPlan
from app.composition import get_service
from app.schemas import StageCreate, StageRead

router = APIRouter(prefix='/stages', tags=['stages'])


@router.get('', response_model=list[StageRead])
def list_stages(festival_id: int, service: FestiPlan = Depends(get_service)):
    return service.list_stages(festival_id)


@router.post('', response_model=StageRead, status_code=201)
def create_stage(payload: StageCreate, service: FestiPlan = Depends(get_service)):
    return service.create_stage(**payload.model_dump())
