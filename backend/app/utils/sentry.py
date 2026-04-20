"""
DSA AutoGrader - Sentry Error Tracking.

Optional error tracking integration.
"""

import logging
from typing import Optional

logger = logging.getLogger("dsa.sentry")


def init_sentry(dsn: Optional[str] = None, environment: str = "development"):
    """Initialize Sentry (optional)."""
    dsn = dsn or ""

    if not dsn:
        logger.info("Sentry disabled (no DSN provided)")
        return False

    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            traces_sample_rate=0.1,
        )
        logger.info("Sentry initialized")
        return True
    except ImportError:
        logger.warning("Sentry SDK not installed")
        return False
    except Exception as e:
        logger.error("Sentry init failed: %s", e)
        return False


def capture_exception(exception: Exception, **kwargs):
    """Capture exception."""
    try:
        import sentry_sdk

        sentry_sdk.capture_exception(exception)
    except Exception:
        pass


def capture_message(message: str, level: str = "info"):
    """Capture message."""
    try:
        import sentry_sdk

        sentry_sdk.capture_message(message, level=level)
    except Exception:
        pass


def set_context(name: str, data: dict):
    """Set context."""
    try:
        import sentry_sdk

        sentry_sdk.set_context(name, data)
    except Exception:
        pass
