from fastapi import APIRouter, Depends
from app.application.service import FestiPlan
from app.composition import get_service
from app.schemas import ArtistCreate, ArtistRead

router = APIRouter(prefix='/artists', tags=['artists'])


@router.get('', response_model=list[ArtistRead])
def list_artists(service: FestiPlan = Depends(get_service)):
    return service.list_artists()


@router.post('', response_model=ArtistRead, status_code=201)
def create_artist(payload: ArtistCreate, service: FestiPlan = Depends(get_service)):
    return service.create_artist(**payload.model_dump())
