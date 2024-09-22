from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import func
from backend.models import User, TimeEntry
import backend.schemas as schemas
from backend.exceptions import UserNotFoundException, UserAlreadyClockedInException, NoClockInFoundException, UserAlreadyClockedOutException, AdminUserAlreadyExists, UserAlreadyExists
import logging
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone
import bcrypt
logger = logging.getLogger("uvicorn")


def _get_period_summary(time_entries):
    grouped_data = {}
    total_hours = 0
    days_worked = 0

    for entry in time_entries:
        # Ensure clock_in and clock_out are timezone-aware
        clock_in_time = entry.clock_in
        if clock_in_time and clock_in_time.tzinfo is None:
            clock_in_time = clock_in_time.replace(tzinfo=timezone.utc)

        clock_out_time = entry.clock_out
        if clock_out_time and clock_out_time.tzinfo is None:
            clock_out_time = clock_out_time.replace(tzinfo=timezone.utc)

        entry_date = clock_in_time.date().strftime("%Y-%m-%d")

        if entry_date not in grouped_data:
            grouped_data[entry_date] = {
                "clock_in": clock_in_time,
                "clock_out": None
            }

        if clock_out_time:
            grouped_data[entry_date]["clock_out"] = clock_out_time
            # Calculate total time for the day
            total_time = clock_out_time - clock_in_time
            grouped_data[entry_date]["total_time"] = str(total_time)
            total_hours += total_time.total_seconds() / 3600
            days_worked += 1
        else:
            grouped_data[entry_date]["clock_out"] = None
            grouped_data[entry_date]["total_time"] = "N/A"

    # Convert grouped data to list format
    result = []
    for date, data in grouped_data.items():
        result.append({
            "date": date,
            "clock_in": data["clock_in"],
            "clock_out": data["clock_out"],
            "total_time": data.get("total_time", "N/A")
        })

    return {
        "total_hours": total_hours,
        "days_worked": days_worked,
        "entries": result
    }

def get_user_by_name(db: Session, name: str):
    return db.query(User).filter(func.lower(User.name) == name.lower()).first()

def create_user(db: Session, user: schemas.UserCreate, is_admin: bool = False, hashed_password: str = None):
    username_lower = user.name.lower()
    logger.info(f"create_user: A request has been made for {username_lower}")

    # Check if the user already exists
    db_user = get_user_by_name(db, name=username_lower)
    if db_user:
        raise UserAlreadyExists(username_lower)

    # Determine the password to store (hashed password for admin)
    password_to_store = hashed_password if hashed_password else None

    new_user = User(name=username_lower, password=password_to_store, is_admin=is_admin)
    db.add(new_user)

    try:
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        raise UserAlreadyExists(username_lower)

    return new_user

def clock_in(db: Session, user: str, time: datetime = None, note: str = None):
    logger.info(f"clock_in: A request has been made for {user}")
    db_user = get_user_by_name(db, user)
    if not db_user:
        raise UserNotFoundException(user)

    # Use provided time or default to current UTC time
    if time is None:
        time = datetime.now(timezone.utc)
    else:
        # Ensure time is timezone-aware and in UTC
        if time.tzinfo is None:
            time = time.replace(tzinfo=timezone.utc)
        else:
            time = time.astimezone(timezone.utc)

    today = time.date()
    time_entry = db.query(TimeEntry).filter(
        TimeEntry.user_id == db_user.id,
        func.date(TimeEntry.clock_in) == today
    ).first()

    if time_entry:
        if time_entry.clock_out:
            raise UserAlreadyClockedOutException(user.capitalize())
        else:
            raise UserAlreadyClockedInException()

    new_entry = TimeEntry(
        user_id=db_user.id,
        clock_in=time,
        clock_in_note=note
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry

def clock_out(db: Session, user: str, time: datetime = None, note: str = None):
    db_user = get_user_by_name(db, user)
    if not db_user:
        raise UserNotFoundException(user)

    if time is None:
        time = datetime.now(timezone.utc)
    else:
        if time.tzinfo is None:
            time = time.replace(tzinfo=timezone.utc)
        else:
            time = time.astimezone(timezone.utc)

    today = time.date()
    time_entry = db.query(TimeEntry).filter(
        TimeEntry.user_id == db_user.id,
        func.date(TimeEntry.clock_in) == today
    ).first()

    if not time_entry:
        raise NoClockInFoundException()

    time_entry.clock_out = time
    time_entry.clock_out_note = note
    db.commit()
    db.refresh(time_entry)
    return time_entry

def get_time_for_pay_period(db: Session, user: str):
    db_user = get_user_by_name(db, user)
    if not db_user:
        raise UserNotFoundException(user)

    # Define a reference pay period start date (a known payday)
    reference_pay_period_start = datetime(2023, 1, 6, tzinfo=timezone.utc).date()  # Update this date as needed

    today = datetime.now(timezone.utc).date()
    days_since_reference = (today - reference_pay_period_start).days
    pay_periods_since_reference = days_since_reference // 14
    current_pay_period_start = reference_pay_period_start + timedelta(days=pay_periods_since_reference * 14)
    current_pay_period_end = current_pay_period_start + timedelta(days=13)  # 14 days total

    # Adjust for future dates if necessary
    if today < current_pay_period_start:
        current_pay_period_start -= timedelta(days=14)
        current_pay_period_end -= timedelta(days=14)

    time_entries = db.query(TimeEntry).filter(
        TimeEntry.user_id == db_user.id,
        func.date(TimeEntry.clock_in) >= current_pay_period_start,
        func.date(TimeEntry.clock_in) <= current_pay_period_end
    ).all()

    return _get_period_summary(time_entries)

def get_time_for_month(db: Session, user: str):
    db_user = get_user_by_name(db, user)
    if not db_user:
        raise UserNotFoundException(user)

    today = datetime.now(timezone.utc)
    start_date = today.replace(day=1)

    time_entries = db.query(TimeEntry).filter(
        TimeEntry.user_id == db_user.id,
        TimeEntry.clock_in >= start_date
    ).all()

    return _get_period_summary(time_entries)

def get_time_for_current_week(db: Session, user: str):
    db_user = get_user_by_name(db, user)
    if not db_user:
        raise UserNotFoundException(user)

    today = datetime.now()
    start_of_week = today - timedelta(days=(today.weekday() + 1) % 7)
    end_of_week = start_of_week + timedelta(days=6)

    time_entries = db.query(TimeEntry).filter(
        TimeEntry.user_id == db_user.id,
        TimeEntry.clock_in >= start_of_week,
        TimeEntry.clock_in <= end_of_week
    ).all()

    return _get_period_summary(time_entries)

def get_user_status(db: Session, user: str) -> str:
    db_user = get_user_by_name(db, user)
    if not db_user:
        raise UserNotFoundException(user)

    recent_entry = db.query(TimeEntry).filter(TimeEntry.user_id == db_user.id).order_by(
        TimeEntry.clock_in.desc()).first()

    if recent_entry and recent_entry.clock_out is None:
        return "in"
    else:
        return "out"

def delete_today_entry(db: Session, user: str):
    db_user = get_user_by_name(db, user)
    if not db_user:
        raise UserNotFoundException(user)

    today = datetime.now(timezone.utc).date()
    time_entry = db.query(TimeEntry).filter(
        TimeEntry.user_id == db_user.id,
        func.date(TimeEntry.clock_in) == today
    ).first()

    if time_entry:
        db.delete(time_entry)
        db.commit()
        return True  # Indicate that the entry was deleted
    else:
        raise NoClockInFoundException()  # No entry found for today


def is_clocked_in_today(db: Session, user: str):
    db_user = db.query(User).filter(User.name == user).first()
    if not db_user:
        return False

    today = datetime.now(timezone.utc).date()
    time_entry = db.query(TimeEntry).filter(
        TimeEntry.user_id == db_user.id,
        func.date(TimeEntry.clock_in) == today
    ).first()

    return time_entry is not None

def delete_user_by_name(db: Session, username: str):
    db_user = db.query(User).filter(User.name == username).first()
    if db_user:
        db.delete(db_user)
        db.commit()
        return True
    return False

def get_users(db: Session):
    users = db.query(User).all()
    return users