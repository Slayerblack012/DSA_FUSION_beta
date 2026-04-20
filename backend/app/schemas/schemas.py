from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# User Schemas
class UserBase(BaseModel):
    username: str
    full_name: str
    role: str = "STUDENT"

class UserCreate(UserBase):
    password: str

class UserSchema(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Submission & Grading Schemas
class TestResultSchema(BaseModel):
    testcase_id: str
    actual_output: Optional[str] = None
    error: Optional[str] = None
    time_ms: float = 0.0
    memory_kb: float = 0.0
    passed: bool
    error_message: Optional[str] = None
    error_type: Optional[str] = None

class SubmissionSchema(BaseModel):
    id: int
    job_id: str
    student_id: Optional[str]
    student_name: str
    assignment_code: Optional[str]
    filename: Optional[str]
    topic: Optional[str]
    total_score: float
    final_score: float
    status: str
    submitted_at: datetime
    plagiarism_detected: bool = False
    needs_review: bool = False
    language: str = "python"
    
    class Config:
        from_attributes = True

class SubmissionPagination(BaseModel):
    submissions: List[SubmissionSchema]
    total: int
    page: int
    page_size: int
    total_pages: int

class SubmissionDetailSchema(SubmissionSchema):
    code: Optional[str]
    feedback: List[str] = []
    test_results: List[TestResultSchema] = []
    plagiarism_matches: List[Dict[str, Any]] = []

# Statistics Schemas
class ScoreDistribution(BaseModel):
    range_0_2: int = Field(alias="0-2")
    range_2_4: int = Field(alias="2-4")
    range_4_6: int = Field(alias="4-6")
    range_6_8: int = Field(alias="6-8")
    range_8_10: int = Field(alias="8-10")

class RecentActivity(BaseModel):
    student_name: str
    action: str
    timestamp: str

class DashboardStats(BaseModel):
    total_submissions: int
    total_students: int
    active_students: int
    avg_score: float
    max_score: float
    min_score: float
    pass_rate: float
    plagiarism_count: int
    score_distribution: Dict[str, int]
    recent_activity: List[RecentActivity]

# Rubric Schemas
class RubricBase(BaseModel):
    assignment_code: str
    topic: str
    criteria_name: str
    max_score: float
    description: Optional[str]
    file_path: Optional[str]

class RubricCreate(RubricBase):
    pass

class RubricSchema(RubricBase):
    id: int
    created_by: str
    created_at: datetime
    
    class Config:
        from_attributes = True
