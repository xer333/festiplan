from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class FestivalCreate(BaseModel):
    name: str=Field(min_length=2,max_length=120)
    location: str=Field(min_length=2,max_length=120)
    start_date: datetime
    end_date: datetime

class FestivalRead(BaseModel):
    id:int
    name:str
    location:str
    start_date:datetime
    end_date:datetime
    status:str
    model_config=ConfigDict(from_attributes=True)

class ArtistCreate(BaseModel):
    name:str=Field(min_length=2,max_length=120)
    genre:str=Field(min_length=2,max_length=80)
    required_equipment:list[str]=Field(default_factory=list)

class ArtistRead(BaseModel):
    id:int; name:str; genre:str; required_equipment:list[str]
    model_config=ConfigDict(from_attributes=True)

class StageCreate(BaseModel):
    festival_id:int
    name:str=Field(min_length=2,max_length=100)
    capacity:int=Field(gt=0)
    available_equipment:list[str]=Field(default_factory=list)

class StageRead(BaseModel):
    id:int; festival_id:int; name:str; capacity:int; available_equipment:list[str]
    model_config=ConfigDict(from_attributes=True)

class ConcertCreate(BaseModel):
    festival_id:int; artist_id:int; stage_id:int; start_time:datetime; end_time:datetime

class ConcertReschedule(BaseModel):
    start_time:datetime; end_time:datetime

class ConcertRead(BaseModel):
    id:int; festival_id:int; artist_id:int; stage_id:int; start_time:datetime; end_time:datetime; status:str
    model_config=ConfigDict(from_attributes=True)

class IncidentCreate(BaseModel):
    concert_id:int
    description:str=Field(min_length=3,max_length=2000)
    occurred_at:datetime|None=None

class IncidentRead(BaseModel):
    id:int; concert_id:int; description:str; occurred_at:datetime; resolved:bool
    model_config=ConfigDict(from_attributes=True)
