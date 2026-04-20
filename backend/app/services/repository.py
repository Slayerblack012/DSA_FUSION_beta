import logging
from typing import Dict, List, Optional
from app.db.session import DatabaseManager
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.submission_repository import SubmissionRepository
from app.db.repositories.rubric_repository import RubricRepository
from app.db.repositories.legacy_repository import LegacyRepository

logger = logging.getLogger("dsa.repository")

class GradingRepository:
    """
    Refactored Facade for database operations.
    Delegates work to specialized repositories for better maintainability.
    """
    def __init__(self, sql_server_url: str = None, sqlite_file: str = None):
        # Use centralized session manager
        self.db_manager = DatabaseManager(sql_server_url=sql_server_url)
        
        # Initialize sub-repositories
        self.users = UserRepository(self.db_manager)
        self.submissions = SubmissionRepository(self.db_manager)
        self.rubrics = RubricRepository(self.db_manager)
        self.legacy = LegacyRepository(self.db_manager)
        
        logger.info("GradingRepository (Facade) initialized and delegated.")

    def initialize(self):
        """Compatibility method for Container initialization."""
        logger.info("GradingRepository initialized.")
        return True

    # --- Backward Compatibility Wrappers ---
    
    def save_result(self, result: Dict) -> int:
        return self.submissions.save_result(result)

    def get_summary_stats(self) -> Dict:
        return self.submissions.get_summary_stats()

    def find_similar_submissions(self, fingerprint: str, threshold: float = 0.8, topic: str = None) -> List[Dict]:
        return self.submissions.find_similar(fingerprint, threshold, topic)

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        return self.users.get_by_username(username)

    def create_user(self, username: str, password_hash: str, full_name: str, role: str = "STUDENT"):
        return self.users.create(username, password_hash, full_name, role)

    def get_all_submissions(self, *args, **kwargs):
        return self.submissions.get_all_submissions(*args, **kwargs)

    def delete_submission(self, submission_id: int):
        return self.submissions.delete_submission(submission_id)

    def get_result_by_id(self, result_id: int):
        return self.submissions.get_by_id(result_id)

    def create_rubric(self, *args, **kwargs):
        return self.rubrics.create_rubric(*args, **kwargs)

    def get_rubrics_by_assignment(self, assignment_code: str):
        return self.rubrics.get_by_assignment(assignment_code)

    def create_manual_grade(self, *args, **kwargs):
        return self.rubrics.create_manual_grade(*args, **kwargs)

    def get_baitap_criteria(self, *args, **kwargs):
        return self.legacy.get_baitap_criteria(*args, **kwargs)

    def get_baitap_exercises(self, *args, **kwargs):
        return self.legacy.get_baitap_exercises(*args, **kwargs)

    def save_runs(self, *args, **kwargs):
        return self.submissions.save_runs(*args, **kwargs)

    def save_batch_results(self, *args, **kwargs):
        return self.submissions.save_batch_results(*args, **kwargs)

    def get_ctdl_assignment_codes(self):
        return self.legacy.get_ctdl_assignment_codes()

    def close(self):
        self.db_manager.close()

    def __del__(self):
        try:
            self.close()
        except: pass

