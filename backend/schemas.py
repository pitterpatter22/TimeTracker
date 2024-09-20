from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional

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

class PeriodSummary(BaseModel):
    total_hours: float  # Total hours worked in the period
    days_worked: int  # Number of days worked in the period
    entries: list[DailyTime]  # List of daily time entries

class Message(BaseModel):
    message: str

class EditClockTimes(BaseModel):
    date: datetime  # Keep the full datetime for editing purposes
    clock_in_time: Optional[datetime]
    clock_out_time: Optional[datetime]