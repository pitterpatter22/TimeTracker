from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import logging
from backend.database import get_db, engine
from backend.models import Base, TimeEntry
import backend.crud as crud
import backend.schemas as schemas
from datetime import datetime, timezone
from backend.exceptions import UserNotFoundException, UserAlreadyClockedInException, NoClockInFoundException, UserAlreadyClockedOutException, UserAlreadyExists
import bcrypt
import os
from sqlalchemy import func
from dateutil.parser import isoparse


# Basic Auth Setup
security = HTTPBasic()

app = FastAPI()
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")
app.mount("/static", StaticFiles(directory="static"), name="static")
Base.metadata.create_all(bind=engine)

# Use Uvicorn's logger
logger = logging.getLogger("uvicorn")

# Retrieve username from environment variables
ENV_USERNAME = os.getenv("ADMIN_USERNAME", "admin")

# Ensure the admin user exists with the hashed password
def ensure_admin_user_exists(db: Session):
    admin_user = crud.get_user_by_name(db, name=ENV_USERNAME)
    if not admin_user:
        # Retrieve password from environment variables
        env_password = os.getenv("ADMIN_PASSWORD")
        
        # Generate a random password if ADMIN_PASSWORD is not set
        if not env_password:
            env_password = secrets.token_urlsafe(16)  # Random secure password
            logger.warning(f"\n\nGenerated admin password: \n{env_password}\n\n")  # Log this for initial use

        # Hash the password
        hashed_env_password = bcrypt.hashpw(env_password.encode('utf-8'), bcrypt.gensalt())
        
        # Create the admin user with the hashed password
        admin_data = schemas.UserCreate(name=ENV_USERNAME)
        crud.create_user(db=db, user=admin_data, is_admin=True, hashed_password=hashed_env_password)

@app.on_event("startup")
def on_startup():
    # Ensure the admin user exists on startup
    db = next(get_db())
    ensure_admin_user_exists(db)

def verify_password(plain_password, hashed_password):
    if not hashed_password:
        return False  # If no password is set, it's an automatic failure
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)

def get_current_username(credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(get_db)):
    user = crud.get_user_by_name(db, name=credentials.username)

    # Check if the user is the admin and verify the password
    if credentials.username == ENV_USERNAME:
        if not user or not verify_password(credentials.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Basic"},
            )
    else:
        # Non-admin users should not have a password
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Basic"},
            )

    return credentials.username


# Custom Exception Handlers

@app.exception_handler(UserAlreadyExists)
async def user_already_exists_exception_handler(request: Request, exc: UserAlreadyExists):
    logger.error(f"UserAlreadyExists: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={"message": f"User '{exc.message}' already exists."},
    )
    
@app.exception_handler(UserAlreadyClockedOutException)
async def user_already_clocked_out_exception_handler(request: Request, exc: UserAlreadyClockedOutException):
    logger.error(f"UserAlreadyClockedOutException: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={"message": exc.message},
    )

@app.exception_handler(UserNotFoundException)
async def user_not_found_exception_handler(request: Request, exc: UserNotFoundException):
    logger.error(f"UserNotFoundException: {exc.message}")
    return JSONResponse(
        status_code=404,
        content={"message": exc.message},
    )

@app.exception_handler(UserAlreadyClockedInException)
async def user_already_clocked_in_exception_handler(request: Request, exc: UserAlreadyClockedInException):
    logger.error(f"UserAlreadyClockedInException: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={"message": exc.message},
    )

@app.exception_handler(NoClockInFoundException)
async def no_clock_in_found_exception_handler(request: Request, exc: NoClockInFoundException):
    logger.error(f"NoClockInFoundException: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={"message": exc.message},
    )

@app.exception_handler(Exception)
async def custom_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error"},
    )

@app.get("/")
def read_root():
    with open("frontend/index.html") as f:
        return HTMLResponse(content=f.read())

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")

@app.post("/user/create", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    username_lower = user.name.lower()
    logger.info(f"create_user: A request has been made for {username_lower}")

    try:
        # Try to create the user
        return crud.create_user(db=db, user=user)
    except UserAlreadyExists as e:
        # Handle the specific exception and provide a user-friendly message
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError:
        # Handle the race condition
        db.rollback()
        raise HTTPException(status_code=400, detail="User already registered")

@app.post("/time/{user}/in")
def clock_in(user: str, time: str = None, note: str = None, db: Session = Depends(get_db)):
    username_lower = user.lower()
    logger.info(f"clock_in: A request has been made for {username_lower}")

    # Parse the time parameter if provided
    if time:
        try:
            parsed_time = datetime.fromisoformat(time)
            if parsed_time.tzinfo is None:
                parsed_time = parsed_time.replace(tzinfo=timezone.utc)
            else:
                parsed_time = parsed_time.astimezone(timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid time format. Use ISO 8601 format.")
    else:
        parsed_time = None  # The CRUD function will handle defaulting to current UTC time

    return crud.clock_in(db=db, user=username_lower, time=parsed_time, note=note)

@app.post("/time/{user}/out")
def clock_out(user: str, time: str = None, note: str = None, db: Session = Depends(get_db)):
    username_lower = user.lower()

    if time:
        try:
            parsed_time = datetime.fromisoformat(time)
            if parsed_time.tzinfo is None:
                parsed_time = parsed_time.replace(tzinfo=timezone.utc)
            else:
                parsed_time = parsed_time.astimezone(timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid time format. Use ISO 8601 format.")
    else:
        parsed_time = None

    return crud.clock_out(db=db, user=username_lower, time=parsed_time, note=note)

@app.get("/time/{user}/recall/payperiod", response_model=schemas.PeriodSummary)
def get_pay_period(user: str, db: Session = Depends(get_db)):
    username_lower = user.lower()
    return crud.get_time_for_pay_period(db=db, user=username_lower)

@app.get("/time/{user}/recall/month", response_model=schemas.PeriodSummary)
def get_time_for_month(user: str, db: Session = Depends(get_db)):
    username_lower = user.lower()
    period_summary = crud.get_time_for_month(db=db, user=username_lower)
    return period_summary

@app.get("/time/{user}/recall/week", response_model=schemas.PeriodSummary)
def get_current_week(user: str, db: Session = Depends(get_db)):
    username_lower = user.lower()
    return crud.get_time_for_current_week(db=db, user=username_lower)

@app.get("/user/status/{user}")
def get_user_status(user: str, db: Session = Depends(get_db)):
    username_lower = user.lower()
    
    try:
        return crud.get_user_status(db=db, user=username_lower)
    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.delete("/time/{user}/today", response_model=schemas.Message)
def delete_today_time_entry(user: str, db: Session = Depends(get_db)):
    try:
        crud.delete_today_entry(db, user.lower())
        return {"message": f"Today's clock-in and clock-out times for {user} have been deleted."}
    except UserNotFoundException as e:
        return {"message": str(e)}
    except NoClockInFoundException:
        return {"message": "No clock-in found for today."}

@app.get("/time/{user}/is_clocked_in_today")
def check_clocked_in_today(user: str, db: Session = Depends(get_db)):
    if not crud.is_clocked_in_today(db, user.lower()):
        return {"clocked_in_today": False}
    return {"clocked_in_today": True}

@app.delete("/user/{username}", response_model=schemas.Message)
def delete_user(username: str, db: Session = Depends(get_db), admin_username: str = Depends(get_current_username)):
    # Only the admin should be able to delete a user
    if admin_username != ENV_USERNAME:
        raise HTTPException(status_code=403, detail="Only the admin can delete users")
    username = username.lower()
    success = crud.delete_user_by_name(db=db, username=username)
    if success:
        return {"message": f"User '{username}' has been deleted."}
    else:
        raise HTTPException(status_code=404, detail="User not found")

@app.get("/edit", response_class=HTMLResponse)
def edit_page():
    with open("frontend/edit.html") as f:
        return HTMLResponse(content=f.read())

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = crud.get_users(db=db)
    return [{"name": user.name} for user in users]

@app.post("/time/{user}/edit")
def edit_clock_times(user: str, data: schemas.EditClockTimes, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_name(db, user)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Parse the date string into a date object
        target_date = datetime.strptime(data.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # Query for the time entry on the specified date
    time_entry = db.query(TimeEntry).filter(
        TimeEntry.user_id == db_user.id,
        func.date(TimeEntry.clock_in) == target_date
    ).first()

    if not time_entry:
        raise HTTPException(status_code=404, detail="No time entry found for this date")

    if data.clock_in_time:
        # Parse the ISO datetime string with timezone information
        time_entry.clock_in = isoparse(data.clock_in_time)
        if time_entry.clock_in.tzinfo is None:
            time_entry.clock_in = time_entry.clock_in.replace(tzinfo=timezone.utc)
        else:
            time_entry.clock_in = time_entry.clock_in.astimezone(timezone.utc)
    if data.clock_out_time:
        time_entry.clock_out = isoparse(data.clock_out_time)
        if time_entry.clock_out.tzinfo is None:
            time_entry.clock_out = time_entry.clock_out.replace(tzinfo=timezone.utc)
        else:
            time_entry.clock_out = time_entry.clock_out.astimezone(timezone.utc)

    db.commit()
    db.refresh(time_entry)

    return {"message": "Clock times updated successfully"}