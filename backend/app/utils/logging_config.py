"""
DSA AutoGrader - Structured Logging Configuration.

Features:
- JSON format for production
- Text format for development
- Context injection (job_id, student_id, etc.)
- Correlation ID support
- Log level filtering
"""

import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """JSON log formatter for production environments."""

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
        self._skip_fields = {
            'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
            'funcName', 'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'message', 'msg', 'name', 'pathname', 'process', 'processName',
            'relativeCreated', 'stack_info', 'thread', 'threadName', 'taskName',
        }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'location': f"{record.filename}:{record.lineno}",
            'function': record.funcName,
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info) if record.exc_info else None,
            }

        # Add custom context fields
        if self.include_extra:
            custom_fields = {
                key: value for key, value in record.__dict__.items()
                if key not in self._skip_fields and not key.startswith('_')
            }
            if custom_fields:
                log_data['context'] = custom_fields

        # Add process info
        log_data['process'] = {
            'pid': record.process,
            'thread': record.thread,
        }

        return json.dumps(log_data, default=str, ensure_ascii=False)


class ContextFormatter(logging.Formatter):
    """Text formatter with context support for development."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with context."""
        # Build base message
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        level = record.levelname
        logger_name = record.name
        message = record.getMessage()

        # Add colors if enabled
        if self.use_colors:
            color = self.COLORS.get(level, '')
            reset = self.RESET
            level = f"{color}{level}{reset}"

        # Build context string
        context_parts = []
        for key, value in record.__dict__.items():
            if not key.startswith('_') and key not in {
                'args', 'asctime', 'created', 'exc_info', 'exc_text',
                'filename', 'funcName', 'levelname', 'levelno', 'lineno',
                'module', 'msecs', 'message', 'msg', 'name', 'pathname',
                'process', 'processName', 'relativeCreated', 'stack_info',
                'thread', 'threadName', 'taskName',
            }:
                if isinstance(value, (str, int, float, bool)):
                    context_parts.append(f"{key}={value}")

        context_str = f" [{' '.join(context_parts)}]" if context_parts else ""

        # Format location
        location = f"{record.filename}:{record.lineno}"

        return f"{timestamp} | {level:<8} | {logger_name:<30} | {location:<30} | {message}{context_str}"


class ContextAdapter(logging.LoggerAdapter):
    """Logger adapter for injecting context into log messages."""

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Add context to log message."""
        if self.extra:
            return msg, {'extra': self.extra, **kwargs}
        return msg, kwargs


def get_context_logger(
    logger_name: str,
    **context: Any
) -> ContextAdapter:
    """
    Get a logger with context injection.
    
    Usage:
        logger = get_context_logger("my_module", job_id="123", student_id="SV001")
        logger.info("Processing job")  # Automatically includes context
    
    Args:
        logger_name: Base logger name
        **context: Context fields to include in all logs
        
    Returns:
        Logger adapter with context
    """
    logger = logging.getLogger(logger_name)
    return ContextAdapter(logger, context)


def setup_logging(
    level: str = "INFO",
    log_format: str = "text",
    log_file: Optional[str] = None,
    use_colors: bool = True,
) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('text' or 'json')
        log_file: Optional file path for log output
        use_colors: Enable colored output (only for text format)
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create console handler with UTF-8 encoding support
    # On Windows, we need to ensure the stream supports UTF-8 to avoid UnicodeEncodeError with emojis
    import io
    stream = sys.stdout
    if sys.platform == "win32":
        # Wrap stdout with a UTF-8 encoder if it's not already
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding='utf-8')
            else:
                import codecs
                stream = codecs.getwriter("utf-8")(sys.stdout.buffer)
        except Exception:
            pass

    console_handler = logging.StreamHandler(stream)
    console_handler.setLevel(getattr(logging, level.upper()))

    # Set formatter based on format type
    if log_format.lower() == 'json':
        formatter = JSONFormatter(include_extra=True)
    else:
        formatter = ContextFormatter(use_colors=use_colors)

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(getattr(logging, level.upper()))
            file_handler.setFormatter(JSONFormatter(include_extra=True))
            root_logger.addHandler(file_handler)
            root_logger.info("Logging to file: %s", log_file)
        except Exception as e:
            root_logger.warning("Failed to setup log file %s: %s", log_file, e)

    # Set levels for noisy third-party loggers
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

    root_logger.info(
        "Logging configured: level=%s, format=%s",
        level,
        log_format
    )


class PerformanceLogger:
    """Context manager for logging performance of code blocks."""

    def __init__(
        self,
        logger_name: str,
        operation: str,
        level: int = logging.INFO,
        **context: Any
    ):
        self.logger = logging.getLogger(logger_name)
        self.operation = operation
        self.level = level
        self.context = context
        self.start_time: Optional[float] = None

    def __enter__(self):
        self.start_time = time.time()
        self.logger.log(
            self.level,
            f"Starting: {self.operation}",
            extra={**self.context, 'operation': self.operation, 'phase': 'start'}
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        if exc_type:
            self.logger.error(
                f"Failed: {self.operation} (took {elapsed:.3f}s) - {exc_val}",
                extra={
                    **self.context,
                    'operation': self.operation,
                    'phase': 'error',
                    'elapsed_seconds': elapsed,
                    'error_type': exc_type.__name__,
                }
            )
        else:
            self.logger.log(
                self.level,
                f"Completed: {self.operation} (took {elapsed:.3f}s)",
                extra={
                    **self.context,
                    'operation': self.operation,
                    'phase': 'complete',
                    'elapsed_seconds': elapsed,
                }
            )
        return False


class LogRequestMiddleware:
    """Middleware for logging HTTP requests with context."""

    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("dsa.http")

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)

        # Extract request info
        method = scope['method']
        path = scope['path']
        
        # Generate correlation ID
        import uuid
        correlation_id = str(uuid.uuid4())
        
        # Create context logger
        ctx_logger = get_context_logger(
            "dsa.http",
            correlation_id=correlation_id,
            method=method,
            path=path
        )

        # Log request
        ctx_logger.info(f"Incoming request: {method} {path}")

        # Track timing
        start_time = time.time()

        # Wrap send to capture response status
        response_status = None

        async def send_wrapper(message):
            nonlocal response_status
            if message['type'] == 'http.response.start':
                response_status = message['status']
            await send(message)

        try:
            # Process request
            await self.app(scope, receive, send_wrapper)

            # Log success
            elapsed = time.time() - start_time
            ctx_logger.info(
                f"Request completed: {response_status}",
                extra={
                    'status_code': response_status,
                    'elapsed_seconds': round(elapsed, 3),
                    'phase': 'complete'
                }
            )

        except Exception as e:
            elapsed = time.time() - start_time
            ctx_logger.error(
                f"Request failed: {str(e)}",
                extra={
                    'status_code': 500,
                    'elapsed_seconds': round(elapsed, 3),
                    'error_type': type(e).__name__,
                    'phase': 'error'
                }
            )
            raise


__all__ = [
    "setup_logging",
    "JSONFormatter",
    "ContextFormatter",
    "ContextAdapter",
    "get_context_logger",
    "PerformanceLogger",
    "LogRequestMiddleware",
]
