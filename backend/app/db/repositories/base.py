import logging
from sqlalchemy.orm import Session
from app.db.session import DatabaseManager

class BaseRepository:
    """Base class for all repositories."""
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.logger = logging.getLogger(f"dsa.repository.{self.__class__.__name__.lower()}")

    def get_session(self):
        return self.db.get_session()
