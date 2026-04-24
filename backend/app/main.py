import logging
import os
import time
import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import router
from app.api.submissions import router as submissions_router
# from app.api.auth import router as auth_router
from app.containers.container import get_container, reset_container
from app.core.config import (CORS_ALLOWED_ORIGINS, ENVIRONMENT, PORT,
                             check_and_log_config, SETTINGS)
from app.services.job_store import start_job_cleanup, stop_job_cleanup
from app.utils.logging_config import setup_logging
from app.utils.sentry import init_sentry
from app.utils.auth import hash_password, cleanup_blacklist
from app.utils.rate_limiter import RateLimitMiddleware
from app.utils.security_hardening import SecurityMiddleware
from app.utils.metrics import generate_metrics

# ---------------------------------------------------------------------------
# Logging & Sentry (module-level, runs once on first import)
# ---------------------------------------------------------------------------
setup_logging(level="INFO", log_format="text")
logger = logging.getLogger("dsa.main")
init_sentry(environment=ENVIRONMENT)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    periodic_cleanup_task = None

    logger.info("=" * 60)
    logger.info("DSA AutoGrader — Starting...")
    logger.info("=" * 60)

    # Validate configuration
    check_and_log_config()

    # Initialise dependency-injection container
    logger.info("Initialising DI container...")
    try:
        container = get_container()
        
        # Connect event bus
        event_bus = container.get_event_bus()
        if event_bus:
            await event_bus.connect()
            
        logger.info("Container ready.")
    except Exception as exc:
        logger.error("Container init failed: %s", exc)
        raise

    # Background cleanup task
    start_job_cleanup()
    logger.info("Background job cleanup started.")

    # Seed demo account
    try:
        repo = container.get_repository()
        if not repo.get_user_by_username("122000001"):
            logger.info("Creating demo account: 122000001 / sv123")
            repo.create_user(
                username="122000001",
                password_hash=hash_password("sv123"),
                full_name="Student Nguyen Van A",
                role="STUDENT"
            )
    except Exception as exc:
        logger.warning("Seed demo account failed: %s", exc)

    # Start periodic auth blacklist cleanup (every 6 hours)
    try:
        async def periodic_blacklist_cleanup():
            while True:
                await asyncio.sleep(6 * 3600)  # Every 6 hours
                try:
                    cleaned = cleanup_blacklist()
                    if cleaned:
                        logger.info("Periodic blacklist cleanup: %d entries removed", cleaned)
                except Exception:
                    logger.exception("Periodic blacklist cleanup failed")
        periodic_cleanup_task = asyncio.create_task(periodic_blacklist_cleanup())
        logger.info("Periodic auth cleanup started (every 6h)")
    except Exception as exc:
        logger.warning("Failed to start periodic cleanup: %s", exc)

    logger.info("=" * 60)
    logger.info("Server is ready!")
    logger.info("  URL:  http://localhost:%s", PORT)
    logger.info("  Docs: http://localhost:%s/docs", PORT)
    logger.info("=" * 60)

    try:
        yield  # ---- application is running ----
    except asyncio.CancelledError:
        # Ctrl+C / reload can cancel lifespan receive loop on shutdown.
        logger.info("Lifespan cancelled during shutdown signal; continuing graceful teardown.")
    finally:
        # Shutdown
        logger.info("Shutting down DSA AutoGrader...")

        if periodic_cleanup_task and not periodic_cleanup_task.done():
            periodic_cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await periodic_cleanup_task

        with suppress(asyncio.CancelledError):
            await stop_job_cleanup()

        cleaned = cleanup_blacklist()
        logger.info("Auth blacklist cleaned: %d entries removed", cleaned)
        if container:
            try:
                container.shutdown()
            except Exception as exc:
                logger.error("Container shutdown error: %s", exc)
        reset_container()
        logger.info("DSA AutoGrader shutdown complete.")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="DSA AutoGrader",
    description="Automatic DSA Assignment Grading System",
    version="Production",
    lifespan=lifespan,
)

# CORS
_cors_origins = (
    CORS_ALLOWED_ORIGINS.split(",") if CORS_ALLOWED_ORIGINS != "*" else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers hardening
app.add_middleware(SecurityMiddleware)

# Rate Limiting (security middleware)
if SETTINGS.security.rate_limit_enabled:
    logger.info(
        "Rate limiting enabled: %d/min, %d/hour",
        SETTINGS.security.rate_limit_per_minute,
        SETTINGS.security.rate_limit_per_hour,
    )
    app.add_middleware(
        RateLimitMiddleware,
        per_minute=SETTINGS.security.rate_limit_per_minute,
        per_hour=SETTINGS.security.rate_limit_per_hour,
    )
else:
    logger.warning("Rate limiting is DISABLED")

# API routers
app.include_router(router, prefix="/api")
app.include_router(submissions_router)
app.include_router(submissions_router, prefix="/api")
# app.include_router(auth_router)


# ---------------------------------------------------------------------------
# Root-level health/ready endpoints (for infrastructure probes)
# ---------------------------------------------------------------------------
@app.get("/health")
async def root_health():
    """Lightweight health check for load balancers and orchestrators."""
    return {
        "status": "healthy",
        "environment": ENVIRONMENT,
        "production": SETTINGS.app.is_production,
        "timestamp": time.time(),
    }


@app.get("/ready")
async def root_ready():
    """
    Readiness check using container health model.

    Returns 503 when any critical component is unhealthy,
    so Kubernetes/orchestrators can stop routing traffic.
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


@app.get("/metrics")
async def root_metrics():
    """Prometheus metrics at root level for scrapers."""
    return PlainTextResponse(generate_metrics())


# Mount Next.js frontend static build
# Mount Next.js frontend static build
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "out"))
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    logger.warning(f"Frontend static 'out' directory not found at {frontend_path}. Make sure to build the Next.js app using 'npm run build'.")
