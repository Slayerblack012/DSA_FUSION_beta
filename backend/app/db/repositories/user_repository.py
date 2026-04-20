from typing import Optional, Dict
from app.db.repositories.base import BaseRepository
from app.models.models import User

class UserRepository(BaseRepository):
    """Handles user accounts and authentication data."""
    
    def get_by_username(self, username: str) -> Optional[Dict]:
        try:
            with self.get_session() as session:
                user = session.query(User).filter(User.username == username).first()
                if not user:
                    return None
                return {
                    "id": user.id, 
                    "username": user.username, 
                    "password_hash": user.password_hash, 
                    "full_name": user.full_name, 
                    "role": user.role
                }
        except Exception as e:
            self.logger.error("Get user failed: %s", e)
            return None

    def create(self, username: str, password_hash: str, full_name: str, role: str = "STUDENT"):
        try:
            with self.get_session() as session:
                user = User(username=username, password_hash=password_hash, full_name=full_name, role=role)
                session.add(user)
                session.flush()
                return user.id
        except Exception as e:
            self.logger.error("Create user failed: %s", e)
            return None
