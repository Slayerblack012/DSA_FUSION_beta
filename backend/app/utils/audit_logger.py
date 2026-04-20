"""
DSA AutoGrader - Security Audit Logger.

Structured audit logging for security-relevant events.
Logs are written to a separate file for compliance and analysis.

Features:
- Structured log format (pipe-delimited for easy parsing)
- Separate audit log file
- Event categorization (AUTH, API, ADMIN, SECURITY)
- IP address tracking
- Success/failure tracking
- Log rotation support
"""

import logging
import os
from typing import Optional


# ---------------------------------------------------------------------------
# Audit Logger Setup
# ---------------------------------------------------------------------------
_AUDIT_LOGGER_NAME = "dsa.audit"
_audit_logger: Optional[logging.Logger] = None


def init_audit_logger(
    logs_dir: str = None,
    log_file: str = "audit.log",
    level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    Initialize the audit logger.

    Args:
        logs_dir: Directory for audit log files
        log_file: Audit log filename
        level: Logging level
        max_bytes: Max log file size before rotation
        backup_count: Number of rotated backup files

    Returns:
        Configured audit logger instance
    """
    global _audit_logger

    if _audit_logger is not None:
        return _audit_logger

    # Determine log directory
    if logs_dir is None:
        logs_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
    logs_dir = os.path.abspath(logs_dir)
    os.makedirs(logs_dir, exist_ok=True)

    log_path = os.path.join(logs_dir, log_file)

    # Create logger
    _audit_logger = logging.getLogger(_AUDIT_LOGGER_NAME)
    _audit_logger.setLevel(level)
    _audit_logger.propagate = False  # Don't propagate to root logger

    # Remove existing handlers
    _audit_logger.handlers.clear()

    # File handler with rotation
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)

    # Structured format: TIMESTAMP | EVENT_TYPE | CATEGORY | USER | IP | RESULT | DETAIL
    formatter = logging.Formatter(
        "%(asctime)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    _audit_logger.addHandler(file_handler)

    _audit_logger.info("AUDIT_LOGGER | initialized | log_file=%s", log_path)
    return _audit_logger


def get_audit_logger() -> logging.Logger:
    """Get the audit logger instance (auto-initializes if needed)."""
    if _audit_logger is None:
        return init_audit_logger()
    return _audit_logger


# ---------------------------------------------------------------------------
# Audit Event Helpers
# ---------------------------------------------------------------------------
def _format_audit_log(
    event_type: str,
    category: str,
    user: str,
    ip: str,
    result: str,
    detail: str = "",
) -> str:
    """
    Format audit log entry in structured pipe-delimited format.

    Format:
    TYPE | CATEGORY | USER | IP | RESULT | DETAIL
    """
    parts = [
        event_type.upper(),
        category.upper(),
        user or "anonymous",
        ip or "unknown",
        result.upper(),
        detail or "",
    ]
    return " | ".join(p.strip() for p in parts)


def audit_log(
    event_type: str,
    category: str,
    user: str = "",
    ip: str = "",
    success: bool = True,
    detail: str = "",
) -> None:
    """
    Write an audit log entry.

    Args:
        event_type: Event type (LOGIN, LOGOUT, API_CALL, ADMIN_ACTION, etc.)
        category: Category (AUTH, API, ADMIN, SECURITY, FILE_UPLOAD, etc.)
        user: Username or identifier
        ip: Client IP address
        success: Whether the event was successful
        detail: Additional context
    """
    result = "SUCCESS" if success else "FAILURE"
    message = _format_audit_log(event_type, category, user, ip, result, detail)
    get_audit_logger().info(message)


# ---------------------------------------------------------------------------
# Convenience Functions for Common Events
# ---------------------------------------------------------------------------
def audit_auth_login(username: str, success: bool, ip: str = "", detail: str = ""):
    """Log authentication login attempt."""
    audit_log(
        event_type="LOGIN",
        category="AUTH",
        user=username,
        ip=ip,
        success=success,
        detail=detail or ("Login successful" if success else "Login failed"),
    )


def audit_auth_logout(username: str, ip: str = ""):
    """Log user logout."""
    audit_log(
        event_type="LOGOUT",
        category="AUTH",
        user=username,
        ip=ip,
        success=True,
        detail="User logged out",
    )


def audit_api_access(
    endpoint: str,
    user: str = "",
    ip: str = "",
    method: str = "GET",
    success: bool = True,
    detail: str = "",
):
    """Log API endpoint access."""
    audit_log(
        event_type="API_CALL",
        category="API",
        user=user,
        ip=ip,
        success=success,
        detail=f"{method} {endpoint} - {detail}",
    )


def audit_security_violation(
    violation_type: str,
    user: str = "",
    ip: str = "",
    detail: str = "",
):
    """Log security violation (sandbox escape, dangerous code, etc.)."""
    audit_log(
        event_type="SECURITY_VIOLATION",
        category="SECURITY",
        user=user,
        ip=ip,
        success=False,
        detail=f"{violation_type}: {detail}",
    )


def audit_file_upload(
    filename: str,
    user: str = "",
    ip: str = "",
    success: bool = True,
    detail: str = "",
):
    """Log file upload event."""
    audit_log(
        event_type="FILE_UPLOAD",
        category="FILE",
        user=user,
        ip=ip,
        success=success,
        detail=f"File: {filename} - {detail}",
    )


def audit_admin_action(
    action: str,
    user: str = "",
    ip: str = "",
    target: str = "",
    detail: str = "",
):
    """Log administrative action."""
    audit_log(
        event_type="ADMIN_ACTION",
        category="ADMIN",
        user=user,
        ip=ip,
        success=True,
        detail=f"Action: {action}, Target: {target} - {detail}",
    )


def audit_rate_limit_exceeded(ip: str, endpoint: str = ""):
    """Log rate limit exceeded event."""
    audit_log(
        event_type="RATE_LIMIT",
        category="SECURITY",
        ip=ip,
        success=False,
        detail=f"Rate limit exceeded on {endpoint}",
    )


def audit_sandbox_violation(
    code_hash: str,
    violation: str,
    user: str = "",
    ip: str = "",
):
    """Log sandbox escape attempt or dangerous code detection."""
    audit_log(
        event_type="SANDBOX_VIOLATION",
        category="SECURITY",
        user=user,
        ip=ip,
        success=False,
        detail=f"Code hash: {code_hash[:16]}..., Violation: {violation}",
    )


# ---------------------------------------------------------------------------
# Audit Log Analysis Helpers
# ---------------------------------------------------------------------------
def get_audit_log_path() -> str:
    """Get the path to the current audit log file."""
    logger = get_audit_logger()
    if logger.handlers:
        handler = logger.handlers[0]
        if hasattr(handler, "baseFilename"):
            return handler.baseFilename
    return "unknown"


def get_audit_log_stats() -> dict:
    """
    Get basic audit log statistics.

    Returns:
        Dict with log file info and event counts
    """
    log_path = get_audit_log_path()

    stats = {
        "log_file": log_path,
        "file_exists": os.path.exists(log_path),
        "file_size_bytes": 0,
        "total_events": 0,
        "event_counts": {},
    }

    if stats["file_exists"]:
        stats["file_size_bytes"] = os.path.getsize(log_path)

        # Count events by type
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    stats["total_events"] += 1
                    parts = line.split(" | ")
                    if len(parts) >= 2:
                        event_type = parts[1].strip()
                        stats["event_counts"][event_type] = (
                            stats["event_counts"].get(event_type, 0) + 1
                        )
        except Exception:
            pass

    return stats


__all__ = [
    "init_audit_logger",
    "get_audit_logger",
    "audit_log",
    "audit_auth_login",
    "audit_auth_logout",
    "audit_api_access",
    "audit_security_violation",
    "audit_file_upload",
    "audit_admin_action",
    "audit_rate_limit_exceeded",
    "audit_sandbox_violation",
    "get_audit_log_path",
    "get_audit_log_stats",
]
