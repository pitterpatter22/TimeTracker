import logging
logger = logging.getLogger("uvicorn")

class UserNotFoundException(Exception):
    def __init__(self, username: str):
        self.message = f"User '{username}' not found"
        super().__init__(self.message)
        logger.error(self.message)


class UserAlreadyClockedInException(Exception):
    def __init__(self, message: str = "User already clocked in today"):
        self.message = message
        super().__init__(self.message)
        logger.error(self.message)


class NoClockInFoundException(Exception):
    def __init__(self, message: str = "No clock-in found for today"):
        self.message = message
        super().__init__(self.message)
        logger.error(self.message)


class UserAlreadyClockedOutException(Exception):
    def __init__(self, user: str):
        self.message = f"{user} has already clocked out for the day."
        super().__init__(self.message)
        
class AdminUserAlreadyExists(Exception):
    def __init__(self, user: str):
        self.message = f"Admin user has already been created, {user} has not been created."
        super().__init__(self.message)
        
class UserAlreadyExists(Exception):
    def __init__(self, user: str):
        self.message = f"{user} already exists"
        super().__init__(self.message)