import re
from typing import List, Dict, Optional
from sqlalchemy import text
from app.db.repositories.base import BaseRepository

class LegacyRepository(BaseRepository):
    """Handles integration with legacy SQL Server tables (dbo.BAITAP)."""

    def _clean_criterion_name(self, name: str) -> str:
        if not name:
            return ""
        # Remove JSON artifacts and specific keys
        clean = name.replace('{', '').replace('}', '').replace('[', '').replace(']', '')
        clean = clean.replace('"tieu_chi":', '').replace('"criteria":', '').replace('"items":', '')
        clean = clean.replace('tieu_chi:', '').replace('criteria:', '')
        # Remove quotes
        clean = clean.replace('"', '').replace("'", "")
        # Remove leading/trailing symbols commonly found in JSON or bad splits
        clean = re.sub(r'^[,\s:•*-]+', '', clean)
        clean = re.sub(r'[,\s:•*-]+$', '', clean)
        return clean.strip()

    def get_baitap_criteria(self, assignment_code: Optional[str] = None, topic: Optional[str] = None, 
                           include_from_assignment: bool = False, split_packed_criteria: bool = False) -> List[Dict]:
        """Load grading criteria from legacy SQL Server BAITAP table."""
        if not self.db.is_sql_server:
            return []

        try:
            with self.get_session() as session:
                query = "SELECT MaBaiTap, TenBaiTap, TieuChiChamDiem FROM BAITAP WHERE MaBaiTap LIKE 'CTDL%' AND (IsDeleted = 0 OR IsDeleted IS NULL)"
                params = {}
                
                if assignment_code:
                    if include_from_assignment:
                        query += " AND MaBaiTap >= :code"
                    else:
                        query += " AND MaBaiTap = :code"
                    params["code"] = assignment_code
                
                rows = session.execute(text(query), params).fetchall()
                
                results = []
                for r in rows:
                    raw_criteria = str(r[2]) if r[2] else ""
                    if split_packed_criteria and raw_criteria:
                        parts = re.split(r'[;\n]+', raw_criteria)
                        for p in parts:
                            p_clean = self._clean_criterion_name(p)
                            if not p_clean or len(p_clean) < 3: continue
                            
                            score_match = re.search(r'\((\d+\.?\d*)\s*[đd]\)', p, re.I)
                            results.append({
                                "assignment_code": str(r[0]),
                                "criteria_name": p_clean,
                                "max_score": float(score_match.group(1)) if score_match else 2.0,
                                "description": p_clean
                            })
                    else:
                        results.append({
                            "assignment_code": str(r[0]),
                            "title": str(r[1]),
                            "criteria_name": "Tiêu chí tổng quát",
                            "max_score": 10.0,
                            "description": raw_criteria
                        })
                return results
        except Exception as e:
            self.logger.error("Legacy BAITAP fetch failed: %s", e)
            return []

    def get_ctdl_assignment_codes(self) -> List[str]:
        """Fetch distinct assignment codes using MaBaiTap column."""
        if not self.db.is_sql_server:
            return []
        try:
            with self.get_session() as session:
                result = session.execute(text("SELECT DISTINCT MaBaiTap FROM BAITAP WHERE MaBaiTap LIKE 'CTDL%' AND (IsDeleted = 0 OR IsDeleted IS NULL)")).fetchall()
                return [str(row[0]) for row in result]
        except Exception as e:
            self.logger.error("Failed to fetch assignment codes: %s", e)
            return []

    def get_baitap_exercises(self, min_code: str = "CTDL_D1_01") -> List[Dict]:
        """Fetch full exercise data using MaBaiTap column."""
        if not self.db.is_sql_server:
            return []
        try:
            with self.get_session() as session:
                query = "SELECT MaBaiTap, TenBaiTap, TieuChiChamDiem, MoTa FROM BAITAP WHERE MaBaiTap LIKE 'CTDL%' AND MaBaiTap >= :min_code AND (IsDeleted = 0 OR IsDeleted IS NULL)"
                rows = session.execute(text(query), {"min_code": min_code}).fetchall()
                
                exercises = []
                for r in rows:
                    raw_criteria = str(r[2]) if r[2] else ""
                    criteria_list = []
                    if raw_criteria:
                        parts = re.split(r'[;\n]+', raw_criteria)
                        for p in parts:
                            p_clean = self._clean_criterion_name(p)
                            if not p_clean or len(p_clean) < 3: continue
                            
                            score_match = re.search(r'\((\d+\.?\d*)\s*[đd]\)', p, re.I)
                            criteria_list.append({
                                "name": p_clean,
                                "max_score": float(score_match.group(1)) if score_match else 2.0,
                                "description": p_clean
                            })
                    
                    exercises.append({
                        "assignment_code": str(r[0]),
                        "title": str(r[1]),
                        "criteria": criteria_list,
                        "criteria_raw": raw_criteria,
                        "description": str(r[3]) if r[3] else ""
                    })
                return exercises
        except Exception as e:
            self.logger.error("Failed to fetch baitap exercises: %s", e)
            return []
