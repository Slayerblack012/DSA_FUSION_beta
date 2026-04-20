"""
DSA AutoGrader - Security Hardening.

Enhanced security features.
"""

import logging
import re
from typing import Dict

logger = logging.getLogger("dsa.security")


class InputValidator:
    """Input validation for security."""

    @classmethod
    def validate_filename(cls, filename: str) -> bool:
        """Validate filename."""
        if not filename or len(filename) > 255:
            return False
        if ".." in filename or "/" in filename or "\\" in filename:
            return False
        allowed_extensions = (".py", ".zip", ".rar")
        if not filename.lower().endswith(allowed_extensions):
            return False
        return True

    @classmethod
    def validate_student_name(cls, name: str) -> bool:
        """Validate student name."""
        if not name or len(name) > 100:
            return False
        return True

    @classmethod
    def validate_assignment_code(cls, code: str) -> bool:
        """Validate assignment code."""
        if not code or len(code) > 50:
            return False
        if not re.match(r"^[a-zA-Z0-9_-]+$", code):
            return False
        return True


class SecurityAuditLogger:
    """Security audit logging."""

    def __init__(self, log_file: str = "logs/security_audit.log"):
        self.log_file = log_file
        try:
            import os

            os.makedirs("logs", exist_ok=True)
            self.audit_logger = logging.getLogger("dsa.security.audit")
            handler = logging.FileHandler(log_file)
            handler.setFormatter(
                logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
            )
            self.audit_logger.addHandler(handler)
            self.audit_logger.setLevel(logging.INFO)
        except Exception as e:
            logger.warning("Security audit logger setup failed: %s", e)

    def log_event(
        self, event_type: str, source_ip: str, endpoint: str, action: str, result: str
    ):
        """Log security event."""
        try:
            self.audit_logger.info(
                "type=%s | ip=%s | endpoint=%s | action=%s | result=%s",
                event_type,
                source_ip,
                endpoint,
                action,
                result,
            )
        except Exception:
            pass

    def log_violation(
        self, source_ip: str, endpoint: str, violation_type: str, details: str
    ):
        """Log security violation."""
        self.log_event("violation", source_ip, endpoint, violation_type, "blocked")


class SecurityHeaders:
    """Security headers for HTTP responses."""

    HEADERS = {
        "X-XSS-Protection": "1; mode=block",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }

    @classmethod
    def get_headers(cls) -> Dict[str, str]:
        return cls.HEADERS.copy()


class SecurityMiddleware:
    """Security middleware for FastAPI."""

    def __init__(self, app):
        self.app = app
        self.validator = InputValidator()

    async def __call__(self, scope, receive, send):
        """Process request."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Add security headers to response
        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                for header, value in SecurityHeaders.get_headers().items():
                    headers.append((header.lower().encode(), value.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)
