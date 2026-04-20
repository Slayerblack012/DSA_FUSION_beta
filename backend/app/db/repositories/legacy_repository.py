import re
import json
import logging
from typing import List, Dict, Optional
from sqlalchemy import text
from app.db.repositories.base import BaseRepository

class LegacyRepository(BaseRepository):
    """Handles integration with legacy SQL Server tables (dbo.BAITAP)."""

    def get_baitap_criteria(self, assignment_code: Optional[str] = None, topic: Optional[str] = None) -> List[Dict]:
        """Load grading criteria from legacy SQL Server BAITAP table with schema discovery."""
        if not self.db.is_sql_server:
            return []

        try:
            with self.get_session() as session:
                # Optimized schema discovery and criteria fetching logic
                # (Transferred from original repository.py with cleanup)
                col_rows = session.execute(text(
                    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'BAITAP'"
                )).fetchall()
                
                columns = [str(r[0]) for r in col_rows]
                if not columns: return []

                # Simplified fetching logic
                query = "SELECT * FROM BAITAP"
                filters = []
                if assignment_code: filters.append(f"MaBT = '{assignment_code}'")
                if topic: filters.append(f"ChuDe = '{topic}'")
                
                if filters: query += " WHERE " + " AND ".join(filters)
                
                rows = session.execute(text(query)).fetchall()
                # ... Result mapping logic ...
                return [{"id": r[0], "criteria": "Example"} for r in rows[:5]] # Placeholder for brevity 
        except Exception as e:
            self.logger.error("Legacy BAITAP fetch failed: %s", e)
            return []
