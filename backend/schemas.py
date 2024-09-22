from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional
from typing import List, Optional
from datetime import datetime, timedelta, timezone

class Config:
    orm_mode = True
    json_encoders = {
        datetime: lambda v: v.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')
    }

class UserBase(BaseModel):
    name: str

class UserCreate(UserBase):
    name: str
    password: Optional[str] = None  # Make the password optional

class User(BaseModel):
    name: str

    class Config:
        from_attributes = True

class TimeEntry(BaseModel):
    clock_in: datetime | None
    clock_out: datetime | None
    clock_in_note: str | None
    clock_out_note: str | None

    class Config:
        from_attributes = True

class DailyTime(BaseModel):
    date: str
    clock_in: TimeEntry
    clock_out: TimeEntry
    total_time: str  # New field to represent the total time worked that day

class TimeEntryResponse(BaseModel):
    date: str
    clock_in: Optional[datetime]
    clock_out: Optional[datetime]
    total_time: str

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PeriodSummary(BaseModel):
    total_hours: float
    days_worked: int
    entries: List[TimeEntryResponse]

class Message(BaseModel):
    message: str

class EditClockTimes(BaseModel):
    date: str  # Keep as string since we're using it to query
    clock_in_time: Optional[str] = None  # Expect ISO datetime string
    clock_out_time: Optional[str] = None