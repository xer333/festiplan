from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ScheduleConcert:
    festival_id: int
    artist_id: int
    stage_id: int
    start_time: datetime
    end_time: datetime


@dataclass(frozen=True)
class RescheduleConcert:
    concert_id: int
    start_time: datetime
    end_time: datetime
