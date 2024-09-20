from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import func
from backend.models import User, TimeEntry
import backend.schemas as schemas
from backend.exceptions import UserNotFoundException, UserAlreadyClockedInException, NoClockInFoundException, UserAlreadyClockedOutException, AdminUserAlreadyExists, UserAlreadyExists
import logging
from sqlalchemy.exc import IntegrityError
import bcrypt
logger = logging.getLogger("uvicorn")


def _get_period_summary(time_entries):
    grouped_data = {}
    total_hours = 0
    days_worked = 0

    for entry in time_entries:
        entry_date = entry.clock_in.date().strftime("%Y-%m-%d")
        if entry_date not in grouped_data:
            grouped_data[entry_date] = {
                "clock_in": entry,
                "clock_out": None
            }

        if entry.clock_out:
            grouped_data[entry_date]["clock_out"] = entry
            # Calculate total time for the day
            total_time = entry.clock_out - entry.clock_in
            grouped_data[entry_date]["total_time"] = str(total_time)
            total_hours += total_time.total_seconds() / 3600
            days_worked += 1

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

def clock_in(db: Session, user: str, note: str = None):
    logger.info(f"clock_in: A request has been made for {user}")
    db_user = get_user_by_name(db, user)
    if not db_user:
        raise UserNotFoundException(user)

    today = datetime.now().date()
    time_entry = db.query(TimeEntry).filter(
        TimeEntry.user_id == db_user.id,
        func.date(TimeEntry.clock_in) == today
    ).first()

    # Check if the user has already clocked in and hasn't clocked out yet
    if time_entry:
        if time_entry.clock_out:
            raise UserAlreadyClockedOutException(user.capitalize())  # User has already clocked out for the day
        else:
            raise UserAlreadyClockedInException()  # User is already clocked in without clocking out

    if time_entry:
        raise UserAlreadyClockedInException()

    new_entry = TimeEntry(
        user_id=db_user.id,
        clock_in=datetime.now(),
        clock_in_note=note
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry

def clock_out(db: Session, user: str, note: str = None):
    db_user = get_user_by_name(db, user)
    if not db_user:
        raise UserNotFoundException(user)

    today = datetime.now().date()
    time_entry = db.query(TimeEntry).filter(
        TimeEntry.user_id == db_user.id,
        func.date(TimeEntry.clock_in) == today
    ).first()

    if not time_entry:
        raise NoClockInFoundException()

    time_entry.clock_out = datetime.now()
    time_entry.clock_out_note = note
    db.commit()
    db.refresh(time_entry)
    return time_entry

def get_time_for_pay_period(db: Session, user: str):
    db_user = get_user_by_name(db, user)
    if not db_user:
        raise UserNotFoundException(user)

    today = datetime.now()
    last_friday = today - timedelta(days=(today.weekday() + 3) % 14)
    start_date = last_friday - timedelta(days=13)
    end_date = last_friday

    time_entries = db.query(TimeEntry).filter(
        TimeEntry.user_id == db_user.id,
        TimeEntry.clock_in >= start_date,
        TimeEntry.clock_in <= end_date
    ).all()

    return _get_period_summary(time_entries)

def get_time_for_month(db: Session, user: str):
    db_user = get_user_by_name(db, user)
    if not db_user:
        raise UserNotFoundException(user)

    today = datetime.now()
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

    today = datetime.now().date()
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

    today = datetime.now().date()
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