"""
DSA AutoGrader - Utilities Package.
"""

from app.utils.logging_config import setup_logging
from app.utils.metrics import (MetricsMiddleware, generate_metrics,
                               record_ai_call, record_job_complete,
                               record_job_start, record_plagiarism_check)
from app.utils.rate_limiter import RateLimitMiddleware
from app.utils.sandbox import run_python_sandbox
from app.utils.security import (calculate_jaccard_similarity,
                                check_python_safety, generate_code_fingerprint)
from app.utils.security_hardening import (InputValidator, SecurityAuditLogger,
                                          SecurityHeaders, SecurityMiddleware)
from app.utils.sentry import capture_exception, capture_message, init_sentry

__all__ = [
    # Security
    "check_python_safety",
    "generate_code_fingerprint",
    "calculate_jaccard_similarity",
    # Sandbox
    "run_python_sandbox",
    # Logging
    "setup_logging",
    # Rate Limiting
    "RateLimitMiddleware",
    # Metrics
    "generate_metrics",
    "MetricsMiddleware",
    "record_job_start",
    "record_job_complete",
    "record_ai_call",
    "record_plagiarism_check",
    # Sentry
    "init_sentry",
    "capture_exception",
    "capture_message",
    # Security Hardening
    "InputValidator",
    "SecurityAuditLogger",
    "SecurityHeaders",
    "SecurityMiddleware",
]
