import json
import logging
import time
import uuid
from typing import List, Optional, Tuple

from fastapi import APIRouter, File, Form, Query, UploadFile, HTTPException, Body, Depends
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.concurrency import run_in_threadpool

from app.containers.container import get_container
from app.core.config import ENVIRONMENT, IS_PRODUCTION
from app.services.ast_grader import sanitize_code_input
from app.services.grading_service import GradingService
from app.services.job_store import _job_store, get_job_store
from app.utils.archive_handler import extract_archive, is_archive_file
from app.utils.metrics import generate_metrics

logger = logging.getLogger("dsa.api")
router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
SUPPORTED_ENCODINGS = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]


async def _extract_files_from_upload(uploaded: UploadFile) -> List[Tuple[str, str]]:
    """Extract source code from uploaded file (supports .py and archives)."""
    filename = uploaded.filename or "unknown"
    content = await uploaded.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File {filename} exceeds 10MB limit")

    if is_archive_file(filename):
        try:
            return extract_archive(content, filename)
        except Exception as e:
            logger.error("Archive extraction failed %s: %s", filename, e)
            raise HTTPException(status_code=400, detail=f"Cannot extract {filename}")

    if filename.lower().endswith(".py"):
        try:
            code = _decode_code(content)
            if code:
                return [(filename, sanitize_code_input(code))]
        except ValueError as e:
            logger.warning("Unsafe code in %s: %s", filename, e)
            return []
        except Exception as e:
            logger.error("Python file processing error %s: %s", filename, e)
            return []

    return []


def _decode_code(content: bytes) -> Optional[str]:
    """Decode code with multiple encoding fallbacks."""
    for enc in SUPPORTED_ENCODINGS:
        try:
            return content.decode(enc)
        except UnicodeError:
            continue
    return content.decode("utf-8", errors="replace")


@router.post("/grade", summary="Submit assignment for grading")
async def grade_submission(
    files: List[UploadFile] = File(...),
    topic: Optional[str] = Form(None),
    student_name: str = Form("Anonymous"),
    student_id: Optional[str] = Form(None),
    assignment_code: Optional[str] = Form(None),
):
    """Grade submission endpoint. Supports multiple .py files or archives."""
    container = get_container()
    grading_service: GradingService = container.get_grading_service()

    # Collect files
    all_files_data: List[Tuple[str, str]] = []
    for uploaded in files:
        extracted = await _extract_files_from_upload(uploaded)
        all_files_data.extend(extracted)

    if not all_files_data:
        return JSONResponse(
            {"error": "No valid Python files (.py) found for grading."},
            status_code=400
        )

    # Normalize student info
    final_id, final_name = _normalize_student_info(student_name, student_id)
    final_name = final_name or "Anonymous"

    # Create job
    job_id = str(uuid.uuid4())

    # Use async job store methods
    job_store = get_job_store()
    initial_job_data = {
        "status": "processing",
        "student": final_name,
        "student_id": final_id,
        "created_at": time.time(),
        "progress": {"current": 0, "total": len(all_files_data), "percent": 0}
    }
    await job_store.set(job_id, initial_job_data)

    # Grade files
    try:
        results = await grading_service.grade_submission(
            files=all_files_data,
            topic=topic or "",
            student_name=final_name,
            student_id=final_id,
            assignment_code=assignment_code,
            job_id=job_id,
        )

        # Persist job state
        job_data = await job_store.get(job_id) or {}
        job_data.update({
            "status": "completed",
            "results": results.get("results", []),
            "summary": results.get("summary", {}),
        })
        await job_store.set(job_id, job_data)

        return {
            "job_id": job_id,
            "status": "completed",
            "student_name": final_name,
            "student_id": final_id,
            "results": results.get("results", []),
            "summary": results.get("summary", {}),
        }

    except Exception as exc:
        logger.error("Job %s failed: %s", job_id, exc, exc_info=True)
        return _handle_grading_error(job_id, str(exc))


def _normalize_student_info(student_name: str, student_id: Optional[str]) -> Tuple[Optional[str], str]:
    """Parse student info from name field if ID not provided."""
    final_id = student_id
    final_name = student_name
    
    if " - " in student_name and not final_id:
        parts = student_name.split(" - ", 1)
        final_id, final_name = parts[0].strip(), parts[1].strip()
    
    return final_id, final_name


async def _handle_grading_error(job_id: str, error_detail: str) -> JSONResponse:
    """Handle grading errors with appropriate user message."""
    job_store = get_job_store()
    job_data = await job_store.get(job_id) or {}
    job_data.update({"status": "failed", "error": error_detail})
    await job_store.set(job_id, job_data)

    user_message = (
        "System error during grading. Please try again or contact administrator."
        if IS_PRODUCTION
        else f"System error: {error_detail}"
    )

    return JSONResponse(
        {"job_id": job_id, "status": "failed", "error": user_message},
        status_code=500
    )


# ---------------------------------------------------------------------------
#  Job polling
# ---------------------------------------------------------------------------
@router.get("/api/job/{job_id}", summary="Get job status")
async def get_job_status(job_id: str):
    """Return the current status and results of a grading job."""
    job_store = get_job_store()
    job = await job_store.get(job_id)
    if job is None:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return job


# ---------------------------------------------------------------------------
#  Score queries (with pagination)
# ---------------------------------------------------------------------------
@router.get("/api/scores/student/{student_id}", summary="Get student scores")
async def get_student_scores(
    student_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """Return score history for a student with pagination."""
    container = get_container()
    repo = container.get_repository()
    result = repo.get_student_scores(student_id, page, page_size)
    return result


@router.get("/api/scores/assignment/{assignment_code}", summary="Get assignment scores")
async def get_assignment_scores(
    assignment_code: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
):
    """Return all scores for an assignment with pagination."""
    container = get_container()
    repo = container.get_repository()
    result = repo.get_assignment_scores(assignment_code, page, page_size)
    return result


@router.get("/api/submissions", summary="Get all submissions")
async def get_all_submissions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    student_id: Optional[str] = Query(None, description="Filter by student ID"),
    assignment_code: Optional[str] = Query(None, description="Filter by assignment"),
    status: Optional[str] = Query(None, description="Filter by status"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
):
    """Get all submissions with server-side pagination and filters."""
    container = get_container()
    repo = container.get_repository()
    
    result = repo.get_all_submissions(
        page=page, 
        page_size=page_size,
        student_id=student_id,
        assignment_code=assignment_code,
        topic=topic,
        status=status
    )
    
    return result


@router.get("/api/stats", summary="Get statistics")
async def get_statistics(assignment_code: Optional[str] = Query(None)):
    """Return grading statistics, optionally filtered by assignment."""
    container = get_container()
    repo = container.get_repository()
    return repo.get_stats(assignment_code)


# ---------------------------------------------------------------------------
#  Test Results Detail
# ---------------------------------------------------------------------------
@router.get("/api/submission/{submission_id}/testcases", summary="Get test case results")
async def get_testcase_results(submission_id: int):
    """Return detailed results for each test case of a submission."""
    container = get_container()
    repo = container.get_repository()
    
    # Get submission
    submission = repo.get_result_by_id(submission_id)
    if not submission:
        return JSONResponse({"error": "Submission not found"}, status_code=404)
    
    # Get test results
    test_results = repo.get_test_results_by_submission(submission_id)
    
    # Optimize: single-pass count instead of iterating test_results twice
    passed_count = sum(1 for r in test_results if r["passed"])
    total_count = len(test_results)

    return {
        "submission_id": submission_id,
        "submission": {
            "filename": submission.get("filename"),
            "student_name": submission.get("student_name"),
            "total_score": submission.get("total_score"),
            "status": submission.get("status")
        },
        "test_results": test_results,
        "summary": {
            "passed": passed_count,
            "total": total_count,
            "pass_rate": round(passed_count / total_count * 100, 1) if total_count else 0
        }
    }


# ---------------------------------------------------------------------------
#  Health / readiness / metrics
# ---------------------------------------------------------------------------
@router.get("/health", summary="Health check")
async def health_check():
    """Lightweight health check for load balancers."""
    return {
        "status": "healthy",
        "environment": ENVIRONMENT,
        "production": IS_PRODUCTION,
        "timestamp": time.time(),
    }


@router.get("/ready", summary="Readiness check")
async def readiness_check():
    """
    Check whether the system is ready to serve requests.

    Uses container health model for detailed component status.
    Returns 503 when any critical component is unhealthy.
    """
    container = get_container()
    health = container.get_health()

    response_data = {
        "ready": health.healthy,
        "checks": health.to_dict()["components"],
        "timestamp": time.time(),
    }

    status_code = 200 if health.healthy else 503
    return JSONResponse(content=response_data, status_code=status_code)


@router.get("/metrics", summary="Prometheus metrics")
async def metrics():
    """Return Prometheus-format metrics text."""
    return PlainTextResponse(generate_metrics())


# End of router
