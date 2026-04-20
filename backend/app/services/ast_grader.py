"""
DSA AutoGrader — AST-based Grading Service (backward-compat shim).

The grading logic has been split into focused modules under
``app.services.grading``. This file re-exports everything so that
existing imports (e.g. ``from app.services.ast_grader import ...``)
continue to work without modification.

Security Note:
    This module now includes input validation and sanitization helpers
    for secure code grading.
"""

import logging
import re
from typing import Any, Dict, List, Optional

# Re-export everything from the grading sub-package
from app.services.grading.constants import SCORING_CONSTANTS
from app.services.grading.constants import \
    ASTGradingResult as GradingResult  # noqa: F401
from app.services.grading.constants import CodeFeatures
from app.services.grading.extractor import ASTFeatureExtractor  # noqa: F401
from app.services.grading.grader import (DSALightningGrader,  # noqa: F401
                                         generate_fingerprint,
                                         lightning_grader)
from app.services.grading.pep8_checker import (  # noqa: F401
    apply_spaghetti_penalties, check_pep8)
from app.services.grading.scorer import (DSAScorer,  # noqa: F401
                                         score_complexity)
from app.services.grading.test_runner import (run_dynamic_tests,  # noqa: F401
                                              score_static_tests)

# Module logger
logger = logging.getLogger("dsa.ast_grader")


def sanitize_code_input(code: str) -> str:
    """
    Sanitize code input before grading.
    
    Security: Removes potentially dangerous patterns that could bypass
    the safety checker through encoding tricks.
    
    Args:
        code: Raw code string from user upload
        
    Returns:
        Sanitized code string
        
    Raises:
        ValueError: If code contains unfixable dangerous patterns
    """
    if not code or not isinstance(code, str):
        raise ValueError("Code must be a non-empty string")
    
    # Remove null bytes and other control characters (except newlines/tabs)
    code = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', code)
    
    # Normalize line endings to Unix style
    code = code.replace('\r\n', '\n').replace('\r', '\n')
    
    # Check for obfuscation attempts (base64 encoded exec/eval)
    obfuscation_patterns = [
        r'__import__\s*\(\s*["\']base64["\']\s*\)',
        r'exec\s*\(\s*base64\.',
        r'eval\s*\(\s*base64\.',
        r'compile\s*\(\s*base64\.',
        r'getattr\s*\(\s*__builtins__',
        r'globals\s*\(\s*\)\s*\[',
    ]
    
    for pattern in obfuscation_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            logger.warning("Obfuscation attempt detected in code")
            raise ValueError("Code contains obfuscated dangerous patterns")
    
    # Limit code length to prevent DoS (50KB max)
    MAX_CODE_LENGTH = 50 * 1024  # 50KB
    if len(code) > MAX_CODE_LENGTH:
        logger.warning("Code exceeds maximum length: %d bytes", len(code))
        code = code[:MAX_CODE_LENGTH]
    
    return code


def validate_student_info(
    student_name: Optional[str],
    student_id: Optional[str],
) -> tuple[str, str]:
    """
    Validate and sanitize student information.
    """
    # Nếu không có tên, gán mặc định thay vì báo lỗi
    final_name = student_name.strip() if student_name and isinstance(student_name, str) else "Sinh viên"
    
    if len(final_name) > 100:
        raise ValueError("Tên sinh viên quá dài (tối đa 100 ký tự)")

    # Check for HTML/script injection
    if re.search(r'<[^>]*>', final_name):
        raise ValueError("Tên sinh viên chứa ký tự không hợp lệ")

    # Validate student ID
    sanitized_id = ""
    if student_id:
        sanitized_id = str(student_id).strip()
        
        if len(sanitized_id) > 50:
            raise ValueError("Student ID must not exceed 50 characters")
        
        # Allow alphanumeric, hyphens, underscores only
        if sanitized_id and not re.match(r'^[a-zA-Z0-9_-]+$', sanitized_id):
            raise ValueError("Student ID contains invalid characters")
    
    return final_name, sanitized_id


def safe_grade_code(
    code: str,
    filename: str = "submission.py",
    topic: Optional[str] = None,
    student_name: Optional[str] = None,
    student_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Safely grade code with input validation and error handling.
    
    This is the main entry point for secure code grading.
    
    Args:
        code: Python code to grade
        filename: Name of the file being graded
        topic: Optional topic/algorithm category
        student_name: Optional student name for logging
        student_id: Optional student ID for logging
        
    Returns:
        Grading result dictionary
        
    Raises:
        ValueError: If input validation fails
        RuntimeError: If grading process fails
    """
    # Log grading request (without sensitive data)
    logger.info(
        "Grading request: file=%s, topic=%s, student=%s",
        filename,
        topic or "auto",
        student_id or "anonymous"
    )
    
    try:
        # Step 1: Sanitize code input
        sanitized_code = sanitize_code_input(code)
        
        # Step 2: Validate optional student info
        if student_name or student_id:
            student_name, student_id = validate_student_info(
                student_name, student_id
            )
        
        # Step 3: Grade the code using lightning grader
        result = lightning_grader.grade_file_ultra_fast(
            code=sanitized_code,
            filename=filename,
            topic=topic or ""
        )
        
        # Step 4: Add metadata to result
        result["student_name"] = student_name
        result["student_id"] = student_id
        result["filename"] = filename
        
        logger.info(
            "Grading completed: file=%s, score=%.1f, status=%s",
            filename,
            result.get("total_score", 0),
            result.get("status", "UNKNOWN")
        )
        
        return result
        
    except ValueError as e:
        # Input validation errors
        logger.warning("Validation failed for %s: %s", filename, e)
        raise
    except Exception as e:
        # Unexpected errors
        logger.error("Grading failed for %s: %s", filename, e, exc_info=True)
        raise RuntimeError(f"Grading process failed: {str(e)}") from e


__all__ = [
    "SCORING_CONSTANTS",
    "CodeFeatures",
    "GradingResult",
    "ASTFeatureExtractor",
    "DSAScorer",
    "DSALightningGrader",
    "check_pep8",
    "apply_spaghetti_penalties",
    "score_complexity",
    "score_static_tests",
    "run_dynamic_tests",
    "generate_fingerprint",
    "lightning_grader",
    # New security functions
    "sanitize_code_input",
    "validate_student_info",
    "safe_grade_code",
]
