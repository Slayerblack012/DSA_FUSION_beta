"""
DSA AutoGrader - Database Facade.
Provides a clean interface to models and repository.
"""

from app.models.models import Base, User, GradingHistory, RunResult, Rubric, ManualGrade
from app.services.repository import GradingRepository

__all__ = [
    "Base", 
    "User", 
    "GradingHistory", 
    "RunResult", 
    "Rubric", 
    "ManualGrade", 
    "GradingRepository"
]
