"""Composition root: wires concrete dependencies outside the core."""
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.adapters.persistence import SqlUnitOfWork
from app.adapters.notifications import EmailNotifier
from app.application.service import FestiPlan


def get_service(db: Session = Depends(get_db)) -> FestiPlan:
    return FestiPlan(SqlUnitOfWork(db), EmailNotifier())
