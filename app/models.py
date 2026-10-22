from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Festival(Base):
    __tablename__="festivals"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,index=True)
    name: Mapped[str]=mapped_column(String(120),nullable=False)
    location: Mapped[str]=mapped_column(String(120),nullable=False)
    start_date: Mapped[datetime]=mapped_column(DateTime,nullable=False)
    end_date: Mapped[datetime]=mapped_column(DateTime,nullable=False)
    status: Mapped[str]=mapped_column(String(30),default="preparation",nullable=False)
    stages=relationship("Stage",back_populates="festival")
    concerts=relationship("Concert",back_populates="festival")

class Artist(Base):
    __tablename__="artists"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,index=True)
    name: Mapped[str]=mapped_column(String(120),nullable=False,unique=True)
    genre: Mapped[str]=mapped_column(String(80),nullable=False)
    required_equipment: Mapped[str]=mapped_column(Text,default="",nullable=False)

class Stage(Base):
    __tablename__="stages"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,index=True)
    festival_id: Mapped[int]=mapped_column(ForeignKey("festivals.id"),nullable=False)
    name: Mapped[str]=mapped_column(String(100),nullable=False)
    capacity: Mapped[int]=mapped_column(Integer,nullable=False)
    available_equipment: Mapped[str]=mapped_column(Text,default="",nullable=False)
    festival=relationship("Festival",back_populates="stages")
    concerts=relationship("Concert",back_populates="stage")

class Concert(Base):
    __tablename__="concerts"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,index=True)
    festival_id: Mapped[int]=mapped_column(ForeignKey("festivals.id"),nullable=False)
    artist_id: Mapped[int]=mapped_column(ForeignKey("artists.id"),nullable=False)
    stage_id: Mapped[int]=mapped_column(ForeignKey("stages.id"),nullable=False)
    start_time: Mapped[datetime]=mapped_column(DateTime,nullable=False)
    end_time: Mapped[datetime]=mapped_column(DateTime,nullable=False)
    status: Mapped[str]=mapped_column(String(30),default="scheduled",nullable=False)
    festival=relationship("Festival",back_populates="concerts")
    artist=relationship("Artist")
    stage=relationship("Stage",back_populates="concerts")

class Incident(Base):
    __tablename__="incidents"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,index=True)
    concert_id: Mapped[int]=mapped_column(ForeignKey("concerts.id"),nullable=False)
    description: Mapped[str]=mapped_column(Text,nullable=False)
    occurred_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,nullable=False)
    resolved: Mapped[bool]=mapped_column(Boolean,default=False,nullable=False)
