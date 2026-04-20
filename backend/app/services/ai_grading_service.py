"""
DSA AutoGrader - AI Grading Service (Optimized with Retry Logic).

Features:
- Exponential backoff retry (3 attempts)
- Circuit breaker pattern
- Response caching
- Graceful fallback
- Token-optimized prompt (60% smaller)
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Optional

from app.core.models import GradingResult

logger = logging.getLogger("dsa.services.ai_grading")

# Maximum code length sent to the AI (characters)
_MAX_CODE_LENGTH = 30_000  # Tăng lên 30,000 để hỗ trợ dự án nhiều files (multi-file projects)
_MAX_FEEDBACK_CODE = 2_000  # Reduced from 3,000 → 2,000

# Retry configuration
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 2.0  # seconds
MAX_RETRY_DELAY = 20.0  # seconds
RETRY_EXPONENT = 2.0  # Exponential backoff factor

# Circuit breaker configuration
CIRCUIT_BREAKER_THRESHOLD = 5  # Failures before opening circuit
CIRCUIT_BREAKER_TIMEOUT = 60  # Seconds to wait before half-open


@dataclass
class CircuitBreakerState:
    """Circuit breaker state."""
    failures: int = 0
    last_failure_time: float = 0.0
    state: str = "closed"  # closed, open, half-open


class AIGradingService:
    """
    AI-powered grading service with retry logic and circuit breaker.

    Dependencies:
    - ``IAIProvider`` (Gemini, OpenAI …)
    - ``IGradingRepository`` (database, for history)
    """

    def __init__(
        self,
        ai_provider: Any,
        repository: Any,
    ) -> None:
        self._ai = ai_provider
        self._repository = repository
        self._prompt = self._build_prompt()
        self._circuit_breaker = CircuitBreakerState()
        self._response_cache: Dict[str, Any] = {}
        self._cache_ttl = 3600  # 1 hour
        self._max_cache_size = 500  # Cap cache size to prevent memory explosion

    # ------------------------------------------------------------------
    #  Circuit Breaker
    # ------------------------------------------------------------------
    def _can_execute(self) -> bool:
        """Check if circuit breaker allows execution."""
        if self._circuit_breaker.state == "closed":
            return True

        if self._circuit_breaker.state == "open":
            # Check if timeout has passed
            if time.time() - self._circuit_breaker.last_failure_time > CIRCUIT_BREAKER_TIMEOUT:
                self._circuit_breaker.state = "half-open"
                logger.info("Circuit breaker half-open, testing...")
                return True
            return False

        # Half-open - allow one test request
        return True

    def _record_success(self) -> None:
        """Record successful execution."""
        self._circuit_breaker.failures = 0
        self._circuit_breaker.state = "closed"

    def _record_failure(self) -> None:
        """Record failed execution."""
        self._circuit_breaker.failures += 1
        self._circuit_breaker.last_failure_time = time.time()

        if self._circuit_breaker.state == "half-open":
            # Half-open test failed → immediately reopen circuit
            self._circuit_breaker.state = "open"
            logger.warning("Circuit breaker RE-OPENED after half-open test failure (total failures: %d)", self._circuit_breaker.failures)
        elif self._circuit_breaker.failures >= CIRCUIT_BREAKER_THRESHOLD:
            self._circuit_breaker.state = "open"
            logger.warning("Circuit breaker OPEN after %d failures", self._circuit_breaker.failures)

    # ------------------------------------------------------------------
    #  Retry Logic with Exponential Backoff
    # ------------------------------------------------------------------
    async def _execute_with_retry(self, func, *args, **kwargs) -> Any:
        """Execute function with retry logic and exponential backoff + jitter."""
        last_exception = None

        for attempt in range(MAX_RETRIES):
            try:
                if not self._can_execute():
                    raise Exception(
                        f"Circuit breaker OPEN — retry after {CIRCUIT_BREAKER_TIMEOUT}s"
                    )

                result = await func(*args, **kwargs)
                self._record_success()
                return result

            except Exception as exc:
                last_exception = exc
                self._record_failure()

                if attempt == MAX_RETRIES - 1:
                    logger.error(
                        "AI grading: all %d attempts exhausted. Last error: %s",
                        MAX_RETRIES, exc,
                    )
                    raise last_exception

                # Exponential backoff with ±10% jitter to avoid thundering herd
                base_delay = min(
                    INITIAL_RETRY_DELAY * (RETRY_EXPONENT ** attempt),
                    MAX_RETRY_DELAY,
                )
                import random
                jitter = base_delay * 0.1 * (random.random() - 0.5) * 2
                total_delay = max(0.1, base_delay + jitter)

                logger.warning(
                    "AI grading attempt %d/%d failed: %s. Retrying in %.2fs...",
                    attempt + 1, MAX_RETRIES, exc, total_delay,
                )
                await asyncio.sleep(total_delay)

        raise last_exception

    # ------------------------------------------------------------------
    #  Prompt template
    # ------------------------------------------------------------------
    @staticmethod
    def _build_prompt() -> str:
        """
        Return optimized grading prompt according to Senior Software Engineer persona.
        """
        return """Bạn là một Kỹ sư Phần mềm Python cấp cao chuyên chấm bài DSA.
Nhiệm vụ: Chấm hệ thống bài nộp (có thể là một hoặc nhiều tệp liên kết được gộp chung) mang tên "{filename}" (chủ đề: {topic}).
Hãy đánh giá toàn diện sự liên kết của mã nguồn và chấm đúng theo rubric_context được cung cấp, không thêm tiêu chí ngoài rubric.

!!! CẢNH BÁO QUAN TRỌNG: 
Hãy chấm điểm tất cả các tiêu chí có trong RUBRIC_CONTEXT.

INPUT_CODE:
```python
{code}
```

AST_REPORT:
{ast_report}

RUBRIC_CONTEXT:
{rubric_context}

QUY TẮC BẮT BUỘC:
1. Xử lý toàn bộ RUBRIC_CONTEXT: Chấm điểm dựa trên mọi tiêu chí được cung cấp.
3. normalized_score_10 = (tổng earned / tổng max) * 10. Tính chính xác, không làm tròn sai.
4. technical_review phải viết như một code review của senior engineer: nêu rõ điểm đúng, điểm rủi ro, edge case, và hướng sửa. Tối thiểu 25 từ.
5. actionable_suggestions (Gợi ý cải thiện): MONG MUỐN BẠN ĐÓNG VAI LÀ MỘT GIÁO SƯ TẬN TÂM, THÂN THIỆN. Hãy đưa ra các lời khuyên chuyên sâu, tích cực để sinh viên học hỏi, cải tiến tư duy thuật toán và tối ưu hoá mã nguồn. Đặc biệt: CHỈ RA ĐIỂM TỐT CỦA EM TRƯỚC VÀ ĐỘNG VIÊN EM CỐ GẮNG. (Tuyệt đối không lặp lại điểm số rubric ở đây). Viết dưới dạng: "Em đã làm rất tốt ở phần..., hãy tiếp tục phát huy!", "Em có thể thử áp dụng...", "Để thuật toán tối ưu hơn, em nên...".
6. Không dùng markdown trong các chuỗi nội dung. Chỉ trả về JSON hợp lệ, không có text ngoài JSON.
7. status: "AC" nếu normalized_score_10 >= 5.0, ngược lại "WA". Dùng "TLE" nếu code có vòng lặp vô hạn rõ ràng.
8. criteria_scores phải bao phủ ĐỦ tất cả tiêu chí trong rubric_context, BẮT BUỘC giữ NGUYÊN tên criterion chính xác từng ký tự như rubric_context cung cấp.
9. Trong mỗi criteria_scores item, feedback phải là nhận xét ngắn, evidence phải là dòng code/hành vi cụ thể chứng minh.
10. TUYỆT ĐỐI KHÔNG chứa các ký tự kỹ thuật sai như "{", "}", "[", "]", "," trong tên criterion. Nếu AI không khớp được tên, hãy bỏ qua hoặc dùng đúng tên từ RUBRIC_CONTEXT.

OUTPUT_JSON (chỉ JSON):
{
"normalized_score_10": <float>,
"status": "AC|WA",
"algorithms_detected": ["<tên thuật toán>"],
"big_o": "O(...)",
"criteria_scores": [
{"criterion": "<tên tiêu chí>", "earned": <float>, "max": <float>, "feedback": "<nhận xét>", "evidence": "<bằng chứng>"}
],
"breakdown": {"correctness": <0-10>, "quality": <0-10>, "efficiency": <0-10>, "structure_robustness": <0-10>, "documentation": <0-10>, "security": <0-10>},
"technical_review": "<nhận xét chuyên nghiệp>",
"evidence_based_issues": ["<lỗi cụ thể>"],
"actionable_suggestions": ["<gợi ý cải thiện cụ thể>"]
}"""

    @staticmethod
    def _looks_placeholder_text(text: Any) -> bool:
        if not isinstance(text, str):
            return True

        normalized = " ".join(text.strip().split()).lower()
        if not normalized:
            return True
        if len(normalized) < 20:
            return True

        placeholder_fragments = [
            "tiếng việt",
            "code đã tối ưu",
            "nếu code ngắn",
            "không có đánh giá",
            "không có phân tích",
            "không có nhận xét",
            "n/a",
            "placeholder",
        ]
        return any(fragment in normalized for fragment in placeholder_fragments)

    @classmethod
    def _is_meaningful_response(cls, response: Dict[str, Any]) -> bool:
        if not isinstance(response, dict):
            return False

        if "error" in response:
            return False

        score = response.get("normalized_score_10", response.get("score"))
        try:
            float(score)
        except (TypeError, ValueError):
            return False

        criteria_scores = response.get("criteria_scores")
        if criteria_scores is not None and not isinstance(criteria_scores, list):
            return False

        status = str(response.get("status", "")).upper()
        if status not in {"AC", "WA", "TLE", "RE", "FLAG"}:
            return False

        technical_review = response.get("technical_review")
        review_text = technical_review.strip() if isinstance(technical_review, str) else ""

        improvement = response.get("actionable_suggestions")
        if isinstance(improvement, list):
            if any(cls._looks_placeholder_text(item) for item in improvement):
                return False

        optimized_code = response.get("improved_code")
        if isinstance(optimized_code, str) and cls._looks_placeholder_text(optimized_code):
            return False

        issues = response.get("evidence_based_issues", [])
        suggestions = response.get("actionable_suggestions", [])
        criteria_scores = response.get("criteria_scores")
        has_criteria = isinstance(criteria_scores, list) and len(criteria_scores) > 0
        has_issues = isinstance(issues, list) and len(issues) > 0
        has_suggestions = isinstance(suggestions, list) and len(suggestions) > 0

        # Accept sparse but still useful responses if at least one key signal exists.
        if not review_text and not has_criteria and not has_issues and not has_suggestions:
            return False

        # Score must be a plausible number (not 0 for non-trivial code)
        score = response.get("normalized_score_10", response.get("score"))
        try:
            score_val = float(score)
            import math
            if math.isnan(score_val) or math.isinf(score_val):
                return False
        except (TypeError, ValueError):
            return False

        # If review exists, avoid obvious placeholder text.
        if review_text and cls._looks_placeholder_text(review_text):
            return False

        return True

    @staticmethod
    def _extract_json_from_raw(raw_text: str) -> Optional[Dict[str, Any]]:
        """Try to recover a JSON object from raw model text."""
        if not raw_text or not isinstance(raw_text, str):
            return None

        cleaned = raw_text.strip()

        # Remove markdown fences if present
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if len(lines) >= 3:
                cleaned = "\n".join(lines[1:-1]).strip()

        # First attempt: parse whole payload
        try:
            data = json.loads(cleaned)
            return data if isinstance(data, dict) else None
        except Exception:
            pass

        # Second attempt: parse the largest JSON-like object
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        candidate = cleaned[start : end + 1]
        try:
            data = json.loads(candidate)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    @classmethod
    def _repair_response_schema(cls, response: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Normalize partial/dirty model responses into expected schema."""
        repaired: Dict[str, Any] = dict(response or {})

        # Score normalization from multiple possible keys
        normalized = repaired.get("normalized_score_10")
        if normalized is None:
            if repaired.get("total_score_60") is not None:
                try:
                    normalized = float(repaired.get("total_score_60")) / 6.0
                except (TypeError, ValueError):
                    normalized = repaired.get("score", 0.0)
            else:
                normalized = repaired.get("score", 0.0)
        repaired["normalized_score_10"] = cls._normalize_score_10(normalized)

        status = str(repaired.get("status", "WA")).upper()
        if status not in {"AC", "WA", "TLE", "RE", "FLAG"}:
            status = "WA"
        repaired["status"] = status

        algorithms = repaired.get("algorithms_detected", [])
        if isinstance(algorithms, str):
            algorithms = [algorithms]
        elif not isinstance(algorithms, list):
            algorithms = []
        repaired["algorithms_detected"] = algorithms

        breakdown = repaired.get("breakdown")
        if not isinstance(breakdown, dict):
            breakdown = {}
        repaired["breakdown"] = {
            "correctness": float(breakdown.get("correctness", 0) or 0),
            "quality": float(breakdown.get("quality", 0) or 0),
            "efficiency": float(breakdown.get("efficiency", 0) or 0),
            "structure_robustness": float(breakdown.get("structure_robustness", 0) or 0),
            "documentation": float(breakdown.get("documentation", 0) or 0),
            "security": float(breakdown.get("security", 0) or 0),
        }

        review = repaired.get("technical_review")
        if not isinstance(review, str) or not review.strip():
            review = repaired.get("analysis") or repaired.get("reasoning") or f"AI review for {filename}."
        repaired["technical_review"] = str(review).strip()

        issues = repaired.get("evidence_based_issues", [])
        if isinstance(issues, str):
            issues = [line.strip("- ").strip() for line in issues.splitlines() if line.strip()]
        elif not isinstance(issues, list):
            issues = []
        repaired["evidence_based_issues"] = [str(item).strip() for item in issues if str(item).strip()]

        suggestions = repaired.get("actionable_suggestions", [])
        if isinstance(suggestions, str):
            suggestions = [line.strip("- ").strip() for line in suggestions.splitlines() if line.strip()]
        elif not isinstance(suggestions, list):
            suggestions = []
        repaired["actionable_suggestions"] = [str(item).strip() for item in suggestions if str(item).strip()]

        if "improved_code" not in repaired:
            repaired["improved_code"] = repaired.get("optimized_code")

        big_o = repaired.get("big_o")
        if not isinstance(big_o, str) or not big_o.strip():
            repaired["big_o"] = "Unknown"

        return repaired

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------
    async def grade_with_ai(
        self,
        code: str,
        filename: str,
        topic: str,
        ast_report: Dict[str, Any],
        rubric_context: Optional[Dict[str, Any]] = None,
    ) -> GradingResult:
        """Grade code using the AI provider with retry logic."""
        logger.info("AI grading: %s (topic: %s)", filename, topic)

        agent_trace: List[Dict[str, Any]] = []

        def trace(stage: str, status: str, detail: str) -> None:
            agent_trace.append({"stage": stage, "status": status, "detail": detail})

        trace("observe", "ok", f"Start grading {filename} (topic={topic})")

        if self._ai is None:
            logger.warning("AI provider is not configured. Falling back to AST for %s", filename)
            trace("fallback", "warn", "AI provider not configured")
            return self._fallback(
                filename,
                code,
                "Gemini API chưa được cấu hình hoặc không khởi tạo được",
                agent_trace=agent_trace,
            )

        # Check cache with stable hash (MD5 of code + rubric context)
        code_hash = hashlib.md5(code.encode("utf-8")).hexdigest()[:12]
        rubric_hash = ""
        if rubric_context:
            rubric_str = json.dumps(rubric_context, sort_keys=True, ensure_ascii=False)
            rubric_hash = ":" + hashlib.md5(rubric_str.encode("utf-8")).hexdigest()[:8]
        cache_key = f"{filename}:{topic}:{code_hash}{rubric_hash}"
        if cache_key in self._response_cache:
            cached_time, cached_result = self._response_cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                logger.debug("Using cached AI grading result for %s", filename)
                trace("observe", "ok", "Cache hit")
                existing_trace = list(cached_result.agent_trace or [])
                return replace(cached_result, agent_trace=existing_trace + agent_trace)

        # Smart truncation: Keep imports (head) and main execution (tail)
        processed_code = code
        if len(code) > _MAX_CODE_LENGTH:
            keep_len = _MAX_CODE_LENGTH // 2
            head = code[:keep_len]
            tail = code[-keep_len:]
            processed_code = f"{head}\n\n# ... [CODE TRUNCATED BY SYSTEM DUE TO LENGTH] ...\n\n{tail}"
            logger.warning("Code truncated for AI: %s", filename)
            trace("observe", "ok", "Code truncated to fit token budget")

        try:
            # Execute with retry logic
            # Use manual replace instead of .format() to avoid KeyError when code contains curly braces
            prompt = self._prompt
            prompt = prompt.replace("{topic}", str(topic))
            prompt = prompt.replace("{filename}", str(filename))
            prompt = prompt.replace("{code}", str(processed_code))
            prompt = prompt.replace("{ast_report}", str(self._format_ast(ast_report)))
            prompt = prompt.replace("{rubric_context}", str(self._format_rubric_context(rubric_context)))
            # Define JSON Schema for Gemini to follow strictly
            grading_schema = {
                "type": "OBJECT",
                "properties": {
                    "normalized_score_10": {"type": "NUMBER"},
                    "status": {"type": "STRING", "enum": ["AC", "WA", "TLE", "RE", "FLAG"]},
                    "algorithms_detected": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "big_o": {"type": "STRING"},
                    "criteria_scores": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "criterion": {"type": "STRING"},
                                "earned": {"type": "NUMBER"},
                                "max": {"type": "NUMBER"},
                                "feedback": {"type": "STRING"},
                                "evidence": {"type": "STRING"}
                            },
                            "required": ["criterion", "earned", "max"]
                        }
                    },
                    "breakdown": {
                        "type": "OBJECT",
                        "properties": {
                            "correctness": {"type": "NUMBER"},
                            "quality": {"type": "NUMBER"},
                            "efficiency": {"type": "NUMBER"},
                            "structure_robustness": {"type": "NUMBER"},
                            "documentation": {"type": "NUMBER"},
                            "security": {"type": "NUMBER"}
                        }
                    },
                    "technical_review": {"type": "STRING"},
                    "evidence_based_issues": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "actionable_suggestions": {"type": "ARRAY", "items": {"type": "STRING"}}
                },
                "required": ["normalized_score_10", "status", "criteria_scores", "technical_review"]
            }

            response = await self._execute_with_retry(
                self._ai.generate_json,
                prompt,
                temperature=0,
                max_tokens=4096,
                response_schema=grading_schema
            )
            trace("observe", "ok", "Provider returned JSON response")

            # Agent-like self-heal: recover JSON object from raw provider output when possible
            if isinstance(response, dict) and "error" in response and response.get("raw"):
                recovered = self._extract_json_from_raw(str(response.get("raw")))
                if recovered:
                    logger.warning("Recovered JSON from raw AI output for %s", filename)
                    response = recovered
                    trace("repair", "ok", "Recovered JSON object from raw model text")
            
            if "error" in response:
                trace("verify", "fail", f"Provider error: {response.get('error')}")
                raise ValueError(f"AI Provider Error: {response['error']}")

            raw_before_repair = dict(response)
            response = self._repair_response_schema(response, filename)
            if response != raw_before_repair:
                trace("repair", "ok", "Normalized response schema")

            if rubric_context and not response.get("criteria_scores"):
                trace("verify", "warn", "Missing criteria_scores, will use server-side rubric scoring fallback")

            if not self._is_meaningful_response(response):
                trace("verify", "fail", "Response failed meaningfulness validation")
                raise ValueError("AI response was not meaningful enough to trust")
            trace("verify", "ok", "Response passed validation")
                
            result = self._parse(response, filename, agent_trace=agent_trace)

            # Cache result
            self._response_cache[cache_key] = (time.time(), result)

            # Clean old cache entries
            self._clean_cache()

            return result

        except Exception as exc:
            logger.error("AI grading failed after retries: %s", exc, exc_info=True)
            trace("fallback", "warn", str(exc))
            return self._fallback(filename, code, str(exc), agent_trace=agent_trace)

    def _clean_cache(self) -> None:
        """Removes expired entries and caps total size using LRU eviction."""
        now = time.time()

        # Remove TTL-expired entries
        expired_keys = [
            key for key, (timestamp, _) in self._response_cache.items()
            if now - timestamp > self._cache_ttl
        ]
        for key in expired_keys:
            del self._response_cache[key]

        # Enforce max cache size — evict oldest-accessed entries first (LRU)
        overflow = len(self._response_cache) - self._max_cache_size
        if overflow > 0:
            sorted_keys = sorted(
                self._response_cache,
                key=lambda k: self._response_cache[k][0]  # sort by insertion/access time
            )
            for key in sorted_keys[:overflow]:
                del self._response_cache[key]
            logger.debug("Cache LRU eviction: removed %d entries, size now %d",
                         overflow, len(self._response_cache))

    @staticmethod
    def _format_rubric_context(rubric_context: Optional[Dict[str, Any]]) -> str:
        """
        Render rubric criteria from DB for AI prompt guidance.

        Optimization: Keep the rubric compact, but include all criteria so the AI
        can score directly against the database rubric.
        """
        if not rubric_context:
            return "No rubric available. Grade by standard DSA criteria."

        criteria = rubric_context.get("criteria", []) or []
        if not criteria:
            return "No rubric criteria. Grade by standard DSA criteria."

        sorted_criteria = sorted(criteria, key=lambda c: c.get("max_score", 0), reverse=True)

        lines = ["BẮT BUỘC: Chỉ chấm điểm theo các tiêu chí dưới đây (giữ nguyên tên tiêu chí):"]
        for idx, item in enumerate(sorted_criteria, start=1):
            name = (item.get("name") or item.get("criteria_name") or "Criterion").strip()
            max_score = item.get("max_score", 0)
            description = (item.get("description") or "").strip()
            if len(description) > 150: # Increased from 60
                description = description[:147] + "..."
            
            lines.append(f"{idx}. TIÊU CHÍ: \"{name}\" | ĐIỂM TỐI ĐA: {max_score}")
            if description:
                lines.append(f"   Mô tả yêu cầu: {description}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    #  Private helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_score_10(raw_score: Any) -> float:
        """Normalize score to 0-10 scale (supports accidental 0-100 responses).
        Guards against NaN and Inf.
        """
        import math
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            return 0.0

        if math.isnan(score) or math.isinf(score):
            return 0.0

        if score > 10.0:
            score = score / 10.0

        return round(max(0.0, min(score, 10.0)), 1)

    @staticmethod
    def _format_ast(report: Dict[str, Any]) -> str:
        """
        Format AST report into concise text for AI prompt.

        Optimization: Only include essential fields to reduce token usage.
        Excludes verbose breakdowns, keeps algorithms + complexity.
        """
        parts = []

        algos = report.get("algorithms", [])
        if algos:
            parts.append(f"Algorithms: {', '.join(algos)}")

        complexity = report.get("complexity", {})
        if complexity:
            if isinstance(complexity, dict):
                big_o = complexity.get("estimated_big_o", complexity.get("time", "N/A"))
            else:
                big_o = str(complexity)
            parts.append(f"Complexity: {big_o}")

        score = report.get("total_score", report.get("score"))
        if score is not None:
            parts.append(f"AST Score: {score}")

        # Include key issues if present
        issues = report.get("issues", report.get("penalties", []))
        if issues:
            parts.append("Issues:")
            for issue in issues[:5]:  # Max 5 issues
                parts.append(f"  - {issue}")

        return "\n".join(parts) if parts else "No AST analysis available"

    @staticmethod
    def _parse(
        response: Dict[str, Any],
        filename: str,
        agent_trace: Optional[List[Dict[str, Any]]] = None,
    ) -> GradingResult:
        """Parse the AI response dict into a ``GradingResult``."""
        # 1. Mandatory Fields
        score = AIGradingService._normalize_score_10(response.get("normalized_score_10", response.get("score", 0.0)))
        status = response.get("status", "WA")
        
        algorithms = response.get("algorithms_detected", [])
        if isinstance(algorithms, str):
            algorithms = [algorithms]
        elif not isinstance(algorithms, list):
            algorithms = []
            
        big_o = response.get("big_o", "Unknown")

        criteria_scores = response.get("criteria_scores", [])
        if not isinstance(criteria_scores, list):
            criteria_scores = []
        normalized_criteria_scores: List[Dict[str, Any]] = []
        for item in criteria_scores:
            if not isinstance(item, dict):
                continue
            criterion = str(item.get("criterion") or item.get("name") or "").strip()
            # Filter out JSON garbage names or very short hallucinated delimiters
            if not criterion or criterion in ['{', '}', '[', ']', ':', ',', '"', '""'] or criterion.startswith('"tieu_chi"') or criterion.startswith('tieu_chi'):
                continue
            try:
                earned = float(item.get("earned", 0) or 0)
            except (TypeError, ValueError):
                earned = 0.0
            try:
                max_score = float(item.get("max", item.get("max_score", 0)) or 0)
            except (TypeError, ValueError):
                max_score = 0.0
            feedback = str(item.get("feedback") or item.get("comment") or "").strip()
            evidence = str(item.get("evidence") or item.get("source_text") or "").strip()
            normalized_criteria_scores.append({
                "criterion": criterion,
                "earned": round(max(0.0, earned), 2),
                "max": round(max(0.0, max_score), 2),
                "feedback": feedback,
                "evidence": evidence,
            })
        
        # Breakdown score
        breakdown = response.get("breakdown", {})
        # Feedback and review
        technical_review = str(response.get("technical_review", "Không có đánh giá chi tiết."))
        
        # 2. Detail lists
        evidence_based_issues = response.get("evidence_based_issues", [])
        if isinstance(evidence_based_issues, str):
            evidence_based_issues = [evidence_based_issues]
        elif not isinstance(evidence_based_issues, list):
            evidence_based_issues = []
            
        actionable_suggestions = response.get("actionable_suggestions", [])
        if isinstance(actionable_suggestions, str):
            actionable_suggestions = [actionable_suggestions]
        elif not isinstance(actionable_suggestions, list):
            actionable_suggestions = []

        if not evidence_based_issues:
            evidence_based_issues = [
                "Chưa trích xuất được lỗi chi tiết từ AI; hệ thống sẽ dựa thêm vào AST/rubric để chấm điểm."
            ]
        if not actionable_suggestions:
            actionable_suggestions = [
                "Bổ sung xử lý biên, tăng độ bao phủ test case và cải thiện tính rõ ràng của thuật toán."
            ]

        optimized_code = response.get("improved_code")

        # 3. Build Combined Feedback for UI
        parts = []
        if technical_review:
            parts.extend(["\n### Phân tích kỹ thuật", technical_review])
        if normalized_criteria_scores:
            parts.append("\n### Điểm theo tiêu chí")
            for item in normalized_criteria_scores:
                line = f"- {item['criterion']}: {item['earned']:.2f}/{item['max']:.2f}"
                if item.get("feedback"):
                    line += f" | {item['feedback']}"
                if item.get("evidence"):
                    line += f" | Evidence: {item['evidence']}"
                parts.append(line)
        if breakdown:
            parts.append("\n### Bảng điểm chi tiết")
            parts.append(f"- Độ chính xác thuật toán: {breakdown.get('correctness', 0)}/10")
            parts.append(f"- Chất lượng Pythonic: {breakdown.get('quality', 0)}/10")
            parts.append(f"- Hiệu năng Big O: {breakdown.get('efficiency', 0)}/10")
            parts.append(f"- Cấu trúc dữ liệu & Xử lý lỗi: {breakdown.get('structure_robustness', 0)}/10")
            parts.append(f"- Tài liệu (Docstring): {breakdown.get('documentation', 0)}/10")
            parts.append(f"- Bảo mật (Security): {breakdown.get('security', 0)}/10")
            parts.append(f"-> Độ phức tạp phát hiện: {big_o}")

        if evidence_based_issues:
            parts.append("\n### Lỗi và vấn đề cần sửa")
            parts.extend(f"- {iss}" for iss in evidence_based_issues)
            
        if actionable_suggestions:
            parts.append("\n### Gợi ý cải thiện")
            parts.extend(f"- {sug}" for sug in actionable_suggestions)

        # 4. Return GradingResult Object
        return GradingResult(
            filename=filename,
            total_score=score,
            status=status,
            algorithms_detected=algorithms,
            feedback="\n".join(parts),
            time_used=0.0,
            memory_used=0.0,
            plagiarism_detected=False,
            breakdown=breakdown,
            complexity=big_o,
            weaknesses="\n".join(f"- {w}" for w in evidence_based_issues) if evidence_based_issues else None,
            improvement="\n".join(f"- {s}" for s in actionable_suggestions) if actionable_suggestions else None,
            reasoning=technical_review,
            optimized_code=optimized_code,
            agent_trace=agent_trace or [],
            criteria_scores=normalized_criteria_scores or None,
        )

    @staticmethod
    def _fallback(
        filename: str,
        code: str,
        error_reason: Optional[str] = None,
        agent_trace: Optional[List[Dict[str, Any]]] = None,
    ) -> GradingResult:
        """Heuristic result when AI is unavailable.
        Score is conservative (max 5.0) to avoid inflating grades when AI is down.
        """
        line_count = max(1, len([line for line in code.split("\n") if line.strip()]))
        # Conservative: cap at 5.0 so students aren't over-rewarded on AI failure
        score = min(5.0, round(2.0 + line_count * 0.05, 1))
        reason_suffix = f" Chi tiết: {error_reason}." if error_reason else ""
        return GradingResult(
            filename=filename,
            total_score=score,
            status="WA",  # Conservative — don't auto-pass on AI failure
            algorithms_detected=[],
            feedback=(
                "Hệ thống chấm AI tạm thời không khả dụng. "
                "Điểm này là ước tính dự phòng, chưa phản ánh chất lượng thực tế của bài nộp."
            ),
            time_used=0.0,
            memory_used=0.0,
            plagiarism_detected=False,
            reasoning=(
                "Dịch vụ AI đang tạm gián đoạn. "
                "Hệ thống đã chuyển sang bộ phân tích dự phòng." + reason_suffix
            ),
            improvement="Vui lòng kiểm tra cấu hình dịch vụ AI và thử nộp lại sau.",
            agent_trace=agent_trace or [],
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get AI service statistics."""
        return {
            "circuit_breaker_state": self._circuit_breaker.state,
            "circuit_breaker_failures": self._circuit_breaker.failures,
            "cache_size": len(self._response_cache),
            "max_retries": MAX_RETRIES,
        }
