from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class GradingResult:
    """Standardized grading result structure."""
    filename: str
    total_score: float
    status: str  # AC, WA, FLAG, TLE, RE
    algorithms_detected: List[str]
    feedback: str
    time_used: float
    memory_used: float
    code: Optional[str] = None
    language: str = "python"
    plagiarism_detected: bool = False
    plagiarism_matches: Optional[List[Dict[str, Any]]] = None
    has_rubric: bool = True
    breakdown: Optional[Dict[str, float]] = None
    complexity: Optional[str] = None
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    reasoning: Optional[str] = None
    improvement: Optional[str] = None
    complexity_analysis: Optional[str] = None
    fingerprint: Optional[str] = None
    student_name: Optional[str] = None
    student_id: Optional[str] = None
    test_results: Optional[List[Dict[str, Any]]] = None  # Detailed test case results
    optimized_code: Optional[str] = None  # AI-generated refactored version
    complexity_curve: Optional[List[Dict[str, Any]]] = None  # Big-O visualization points
    agent_trace: Optional[List[Dict[str, Any]]] = None  # Observe/repair/verify/fallback timeline
    score_proof: Optional[Dict[str, Any]] = None  # Auditable weighted-score evidence
    criteria_scores: Optional[List[Dict[str, Any]]] = None  # AI rubric scores per criterion
    rubric_snapshot: Optional[Dict[str, Any]] = None  # Frozen rubric profile used for this submission

@dataclass
class AIResponse:
    """Standardized AI response structure."""
    content: str
    model: str
    usage: Dict[str, int]
    latency_ms: float
    success: bool
    error_message: Optional[str] = None

@dataclass
class GradingRequest:
    """Standardized grading request structure."""
    code: str
    filename: str
    topic: Optional[str]
    student_name: str
    assignment_code: Optional[str]
    test_cases: Optional[List[Dict[str, Any]]] = None

from enum import Enum

class EventType(str, Enum):
    RESULT_SAVED = "result_saved"
    BATCH_RESULTS_SAVED = "batch_results_saved"
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    PLAGIARISM_DETECTED = "plagiarism_detected"

@dataclass
class Event:
    type: EventType
    payload: Dict[str, Any]
    source: str
    timestamp: float = 0.0
