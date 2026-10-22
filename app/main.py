from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import Base, engine
from app import models  # register ORM mappings
from app.api import festivals, artists, stages, concerts, incidents
from app.domain.errors import DomainError, NotFound, StateConflict


async def business_error(request: Request, exc: DomainError):
    status = 404 if isinstance(exc, NotFound) else 409 if isinstance(exc, StateConflict) else 400
    return JSONResponse(status_code=status, content={'detail': str(exc)})


def health():
    return {'message': 'Bienvenue sur FestiPlan', 'status': 'ok'}


def create_app(database_engine=engine):
    @asynccontextmanager
    async def lifespan(application):
        Base.metadata.create_all(bind=database_engine)
        yield

    application = FastAPI(title=settings.app_name, version='1.0.0', lifespan=lifespan,
                          description='API de gestion de festival, architecture hexagonale et domaine DDD')
    application.add_exception_handler(DomainError, business_error)
    for router in (festivals.router, artists.router, stages.router, concerts.router, incidents.router):
        application.include_router(router)
    application.add_api_route('/', health, methods=['GET'])
    return application


app = create_app()
