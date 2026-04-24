import asyncio
import hashlib
import logging
import time
import uuid
from typing import List, Optional, Tuple

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.containers.container import get_container
from app.services.grading_service import GradingService
from app.services.testcase_loader import get_all_topics
from app.utils.archive_handler import extract_archive, is_archive_file

# Initialize Logger
logger = logging.getLogger("dsa.api.submissions")
router = APIRouter(prefix="/submissions", tags=["Submissions"])

_IDEMPOTENCY_TTL_SECONDS = 600
_idempotency_cache: dict = {}
_idempotency_lock = asyncio.Lock()


def _cleanup_idempotency_cache() -> None:
    now = time.time()
    expired = [
        key for key, value in _idempotency_cache.items()
        if now - float(value.get("timestamp", 0)) > _IDEMPOTENCY_TTL_SECONDS
    ]
    for key in expired:
        _idempotency_cache.pop(key, None)


def _build_idempotency_cache_key(
    student_id: str,
    student_name: str,
    topic: Optional[str],
    assignment_code: Optional[str],
    file_names: List[str],
    raw_key: str,
) -> str:
    payload = {
        "student_id": student_id,
        "student_name": student_name,
        "topic": topic or "",
        "assignment_code": assignment_code or "",
        "files": sorted(file_names),
        "key": raw_key.strip(),
    }
    digest = hashlib.sha256(str(payload).encode("utf-8")).hexdigest()
    return f"submission:{digest}"

# ---------------------------------------------------------------------------
#  Topic Inference & Response Mapping Helpers
# ---------------------------------------------------------------------------

def _infer_topic(name: str, code: str, available_topics: List[str]) -> str:
    """
    Infer the Data Structure / Algorithm topic from the filename or code content.
    Supports English and Vietnamese keywords.
    """
    # 1. Direct match from filename
    name_lower = name.lower()
    for t in available_topics:
        if t.lower() in name_lower:
            return t

    # 2. Heuristic match from code content keywords
    code_lower = code.lower()
    keyword_map = {
        "search": ["search", "tìm kiếm", "binary_search"],
        "sort": ["sort", "sắp xếp", "bubble", "quick", "merge"],
        "linkedlist": ["linkedlist", "danh sách liên kết", "node", "prev"],
        "queue": ["queue", "hàng đợi"],
        "stack": ["stack", "ngăn xếp"],
        "tree": ["tree", "cây", "bst"],
        "graph": ["graph", "đồ thị", "bfs", "dfs"],
        "greedy": ["greedy", "tham lam"],
        "knapsack": ["dp", "dynamic programming", "quy hoạch động"],
        "recursion": ["recursion", "đệ quy"],
        "factorial": ["factorial", "giai thừa"],
        "fibonacci": ["fibonacci"],
    }

    for topic, keywords in keyword_map.items():
        if any(k in code_lower for k in keywords):
            return topic

    return ""


def _map_to_frontend_format(results: dict, student_id: str) -> dict:
    """
    Map GradingService business results to the specific JSON format 
    expected by the Legacy Next.js frontend.
    """
    grading_results = results.get("results", [])
    summary = results.get("summary", {})
    
    file_evaluations = []
    total_time_ms = 0.0
    
    for r in grading_results:
        # Build individual file feedback from AI grading output and optional testcase data
        feedbacks = []
        test_results = r.get("test_results", [])
        full_feedback = r.get("feedback") or r.get("reasoning") or "Mã nguồn hợp lệ"
        
        if test_results:
            feedbacks.append({
                "testcase": "AI Review",
                "status": r.get("status", "AC"),
                "message": full_feedback,
                "hint": "",
                "points": r.get("total_score", 0),
            })

            for tr in test_results:
                feedbacks.append({
                    "testcase": tr.get("testcase", "Test Case"),
                    "status": "AC" if tr.get("passed") else "WA",
                    "message": tr.get("message", "N/A"),
                    "hint": tr.get("hint"),
                    "points": tr.get("points", 0)
                })

            # Add rubric criteria summary (if available) so frontend can show DB-based scoring details.
            rubric_marker = "### Chấm theo tiêu chí từ cơ sở dữ liệu"
            if rubric_marker in full_feedback:
                rubric_text = full_feedback.split(rubric_marker, 1)[1].strip()
                feedbacks.append({
                    "testcase": "Tiêu chí SQL",
                    "status": r.get("status", "AC"),
                    "message": rubric_text,
                    "hint": "Điểm bên dưới được chuẩn hóa về thang 10 theo trọng số rubric.",
                    "points": r.get("total_score", 0),
                })
        else:
            # AI-only summary when no testcase breakdown is attached
            feedbacks.append({
                "testcase": "AI Review",
                "status": r.get("status", "AC"),
                "message": full_feedback,
                "hint": "",
                "points": r.get("total_score", 0)
            })

        # Calculate time in milliseconds
        time_ms = float(r.get("time_used", 0) or 0) * 1000
        total_time_ms += time_ms

        file_evaluations.append({
            "file_name": r.get("filename", "submission.py"),
            "score": r.get("total_score", 0.0),
            "status": r.get("status", "AC"),
            "time_ms": time_ms,
            "feedbacks": feedbacks,
            "ai_advice": r.get("feedback") or r.get("reasoning") or r.get("improvement") or "",
            "improvement": r.get("improvement") or "",
            "optimized_code": r.get("optimized_code"),
            "complexity_curve": r.get("complexity_curve", []),
            "agent_trace": r.get("agent_trace", []),
            "score_proof": r.get("score_proof"),
            "criteria_scores": r.get("criteria_scores") or [],
            "breakdown": r.get("breakdown"),
            "complexity": r.get("complexity"),
        })

    # Return structured response matching Frontend's ResultRecord type
    avg_score = summary.get("avg_score", 0.0) if summary else 0.0
    if avg_score is None:
        avg_score = 0.0

    return {
        "submission_id": str(uuid.uuid4()),
        "student_id": student_id,
        "student_name": (grading_results[0].get("student_name") if grading_results else "") or "Sinh viên",
        "total_score": avg_score,
        "total_time_ms": total_time_ms,
        "status": "AC" if avg_score >= 5 else "WA",
        "file_evaluations": file_evaluations,
        "overall_ai_summary": results.get("ai_summary", "Hệ thống đã hoàn tất chấm điểm bài làm của bạn.") or "Hệ thống đã hoàn tất chấm điểm bài làm của bạn."
    }


# ---------------------------------------------------------------------------
#  Primary Submission Endpoint
# ---------------------------------------------------------------------------

@router.post("/", summary="Submit assignment for grading")
async def submit_multi_file(
    request: Request,
    files: List[UploadFile] = File(...),
    student_id: str = Form(...),
    student_name: str = Form("Sinh viên"),
    topic: Optional[str] = Form(None),
    assignment_code: Optional[str] = Form(None),
    idempotency_key: Optional[str] = Form(None),
):
    """
    Submission entry point for students. 
    Handles file upload, archive extraction, topic auto-detection, 
    and orchestrates the grading pipeline via GradingService.
    """
    # Initialize Core Service via Container
    container = get_container()
    grading_service: GradingService = container.get_grading_service()

    incoming_key = (request.headers.get("Idempotency-Key") or idempotency_key or "").strip()
    file_names = [f.filename or "unknown.py" for f in files]
    cache_key: Optional[str] = None

    if incoming_key:
        cache_key = _build_idempotency_cache_key(
            student_id=student_id,
            student_name=student_name,
            topic=topic,
            assignment_code=assignment_code,
            file_names=file_names,
            raw_key=incoming_key,
        )
        async with _idempotency_lock:
            _cleanup_idempotency_cache()
            cached = _idempotency_cache.get(cache_key)
            if cached and isinstance(cached.get("response"), dict):
                logger.info("Returning cached submission response via idempotency key for student %s", student_id)
                return cached["response"]
    
    py_files_to_grade: List[Tuple[str, str]] = []

    # Step 1: Extract and Sanitize Source Files
    try:
        for uploaded_file in files:
            content = await uploaded_file.read()
            name = uploaded_file.filename or "unknown.py"
            
            if is_archive_file(name):
                # Handle ZIP/RAR archives
                extracted = extract_archive(content, name)
                py_files_to_grade.extend(extracted)
            elif name.lower().endswith(".py"):
                # Handle direct Python files with encoding fallback
                code = None
                for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
                    try:
                        code = content.decode(enc)
                        break
                    except UnicodeDecodeError:
                        continue
                
                if code:
                    py_files_to_grade.append((name, code))
    except Exception as exc:
        logger.error(f"Failed to process uploaded files: {exc}")
        raise HTTPException(status_code=400, detail=f"Lỗi xử lý tệp: {str(exc)}")

    if not py_files_to_grade:
        raise HTTPException(status_code=400, detail="Không tìm thấy mã nguồn Python (.py) hợp lệ.")

    # ------ CẢI TIẾN: GỘP NHIỀU FILE ------
    original_files = list(py_files_to_grade)
    # Gộp tất cả các file thành một project hoàn chỉnh để AI có thể chấm toàn bộ cấu trúc dự án
    # và tránh bị chặn vì Rate Limit (quá nhiều request AI cùng lúc).
    if len(py_files_to_grade) > 1:
        combined_code = "\n\n".join([f"# {'='*20}\n# TẬP TIN: {name}\n# {'='*20}\n{code}" for name, code in py_files_to_grade])
        # Tóm tắt tên file nếu quá dài để hiển thị trên UI đẹp hơn
        display_name = " | ".join([name for name, _ in py_files_to_grade])
        if len(display_name) > 60:
            display_name = f"Dự án gồm {len(py_files_to_grade)} file"
        py_files_to_grade = [(display_name, combined_code)]

    # Step 2: Topic selection (prefer explicit form input, then infer)
    batch_topic = (topic or "").strip().lower()
    if not batch_topic:
        available_topics = get_all_topics()
        inferred_topics = [_infer_topic(fn, fc, available_topics) for fn, fc in py_files_to_grade]
        batch_topic = next((t for t in inferred_topics if t), "")

    final_assignment_code = (assignment_code or "").strip() or None
    logger.info("Batch submission detected for student %s | Topic: %s", student_id, batch_topic or "Auto")

    # Step 3: Execute Grading Pipeline
    try:
        # The orchestrator handles AI-only grading, plagiarism checks, and DB persistence
        grading_results = await grading_service.grade_submission(
            files=py_files_to_grade,
            topic=batch_topic,
            student_name=student_name,
            student_id=student_id,
            assignment_code=final_assignment_code,
        )

        result_rows = grading_results.get("results", []) or []
        if result_rows and all((row.get("status") == "RE") for row in result_rows):
            detail = next(
                (
                    row.get("feedback")
                    or row.get("reasoning")
                    or "Dịch vụ AI chưa sẵn sàng để chấm bài."
                )
                for row in result_rows
            )
            raise HTTPException(status_code=503, detail=detail)
        
        # Manually run intra-job plagiarism check on original separate files
        if len(original_files) > 1:
            try:
                plagiarism_service = container.get_plagiarism_service()
                from app.core.models import GradingResult
                dummy_results = [
                    GradingResult(
                        filename=fn,
                        total_score=0.0,
                        status="AC",
                        algorithms_detected=[],
                        feedback="",
                        time_used=0.0,
                        memory_used=0.0,
                        code=fc,
                        fingerprint=plagiarism_service.generate_fingerprint(fc)
                    ) for fn, fc in original_files
                ]
                intra_alerts = await plagiarism_service.check_intra_job_plagiarism(dummy_results)
                if intra_alerts:
                    current_alerts = grading_results.get("plagiarism_alerts", [])
                    current_alerts.extend(intra_alerts)
                    grading_results["plagiarism_alerts"] = current_alerts
            except Exception as e:
                logger.warning("Original files plagiarism check failed: %s", e)

        # Step 4: Format and Return results to Frontend
        mapped = _map_to_frontend_format(grading_results, student_id)

        if cache_key:
            async with _idempotency_lock:
                _cleanup_idempotency_cache()
                _idempotency_cache[cache_key] = {
                    "timestamp": time.time(),
                    "response": mapped,
                }

        return mapped

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Grading orchestration service failure: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Dịch vụ AI chấm bài đang gặp lỗi. Vui lòng kiểm tra cấu hình Gemini hoặc thử lại sau.")
    
@router.get("/assignments/codes")
async def get_assignment_codes():
    container = get_container()
    db_repo = container.get_repository()
    return db_repo.get_ctdl_assignment_codes()


@router.get("/assignments/{code}")
async def get_assignment_detail(code: str):
    container = get_container()
    repo = container.get_repository()
    # Find specific assignment detail
    exercises = repo.get_baitap_exercises("CTDL")
    for ex in exercises:
        if ex["assignment_code"] == code:
            return ex
    raise HTTPException(status_code=404, detail="Không tìm thấy bài tập.")
