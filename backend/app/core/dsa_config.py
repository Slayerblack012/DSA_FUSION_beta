import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv


def _load_environment_files() -> None:
    """Load environment files with backend-local overrides taking precedence."""
    current_file = Path(__file__).resolve()
    project_root = current_file.parents[3]
    root_env = project_root / ".env"
    backend_env = project_root / "backend" / ".env"

    # Base shared configuration from project root (if present)
    if root_env.exists():
        load_dotenv(dotenv_path=root_env, override=False)

    # Backend-specific secrets/config should win over the shared file.
    if backend_env.exists():
        load_dotenv(dotenv_path=backend_env, override=True)
        return

    # Backward-safe fallback when explicit env files are not present.
    load_dotenv(override=False)


_load_environment_files()

logger = logging.getLogger("dsa.config")


# ---------------------------------------------------------------------------
# Environment parsing helpers
# ---------------------------------------------------------------------------
def _as_str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _as_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid int for %s=%r, using default=%s", name, raw, default)
        return default


def _as_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("Invalid float for %s=%r, using default=%s", name, raw, default)
        return default


def _as_csv(name: str, default: str = "") -> List[str]:
    value = _as_str(name, default)
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _mask_secret(value: str) -> str:
    if not value:
        return "Not set"
    return "Set"


# ---------------------------------------------------------------------------
# Structured settings
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AppSettings:
    environment: str
    is_production: bool
    is_development: bool
    is_testing: bool
    port: int
    auto_reload: bool


@dataclass(frozen=True)
class AISettings:
    provider: str
    model_name: str
    model_temperature: float
    max_output_tokens: int
    max_concurrent_calls: int
    gemini_api_key: str


@dataclass(frozen=True)
class DatabaseSettings:
    sql_server_url: str
    redis_url: str
    db_name: str
    db_file: str
    job_ttl_seconds: int
    max_history_rows: int


@dataclass(frozen=True)
class SecuritySettings:
    my_secret_key: str
    jwt_secret_key: str
    cors_allowed_origins: str
    cors_allowed_origins_list: List[str]
    rate_limit_enabled: bool
    rate_limit_per_minute: int
    rate_limit_per_hour: int


@dataclass(frozen=True)
class SandboxSettings:
    max_memory_mb: int
    max_cpu_time: int
    max_upload_size_mb: int
    dynamic_test_timeout: int


@dataclass(frozen=True)
class FeatureSettings:
    metrics_enabled: bool
    log_level: str
    log_format: str
    plagiarism_threshold: float
    pass_score_threshold: int
    webhook_max_retries: int
    webhook_retry_delay: int


@dataclass(frozen=True)
class IntegrationSettings:
    question_bank_api_url: str
    rubric_api_url: str


@dataclass(frozen=True)
class PathSettings:
    base_dir: str
    data_dir: str
    testcase_root: str
    logs_dir: str


@dataclass(frozen=True)
class DSAConfig:
    app: AppSettings
    ai: AISettings
    database: DatabaseSettings
    security: SecuritySettings
    sandbox: SandboxSettings
    features: FeatureSettings
    integrations: IntegrationSettings
    paths: PathSettings


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------
def _build_paths() -> PathSettings:
    base_dir = Path(__file__).resolve().parents[2]
    data_dir = base_dir / "data"
    testcase_root = data_dir / "testcases"
    logs_dir = base_dir / "logs"

    return PathSettings(
        base_dir=str(base_dir),
        data_dir=str(data_dir),
        testcase_root=str(testcase_root),
        logs_dir=str(logs_dir),
    )


def build_config() -> DSAConfig:
    paths = _build_paths()

    env = _as_str("ENVIRONMENT", "development").lower()
    app = AppSettings(
        environment=env,
        is_production=env == "production",
        is_development=env == "development",
        is_testing=env == "testing",
        port=_as_int("PORT", 8000),
        auto_reload=_as_bool("AUTO_RELOAD", True),
    )

    ai = AISettings(
        provider="gemini",
        model_name=_as_str("AI_MODEL_NAME", "gemini-3-flash-preview"),
        model_temperature=_as_float("AI_MODEL_TEMPERATURE", 0.1),
        max_output_tokens=_as_int("AI_MAX_OUTPUT_TOKENS", 8192),
        max_concurrent_calls=_as_int("MAX_CONCURRENT_AI_CALLS", 5),
        gemini_api_key=_as_str("GEMINI_API_KEY", ""),
    )

    db_name = _as_str("DB_NAME", "database.db")
    database = DatabaseSettings(
        sql_server_url=_as_str("SQL_SERVER_URL", ""),
        redis_url=_as_str("REDIS_URL", ""),
        db_name=db_name,
        db_file=str(Path(paths.data_dir) / db_name),
        job_ttl_seconds=_as_int("JOB_TTL_SECONDS", 3600),
        max_history_rows=_as_int("MAX_HISTORY_ROWS", 2000),
    )

    cors_raw = _as_str("CORS_ALLOWED_ORIGINS", "*")
    # SECURITY: JWT_SECRET_KEY MUST be set in production. No hardcoded default.
    jwt_raw = _as_str("JWT_SECRET_KEY", "")
    if not jwt_raw:
        if _as_str("ENVIRONMENT", "development").lower() == "production":
            raise EnvironmentError(
                "CRITICAL: JWT_SECRET_KEY environment variable is REQUIRED in production.\n"
                "Generate a secure secret with:\n"
                "  python -c 'import secrets; print(secrets.token_urlsafe(64))'\n"
                "Then set it in your .env file or environment:\n"
                "  JWT_SECRET_KEY=<your-secret-here>"
            )
        # Development fallback only (with warning logged later)
        jwt_raw = "dev-secret-change-me-in-production-" + _as_str("MY_SECRET_KEY", "dev")[:20]
    security = SecuritySettings(
        my_secret_key=_as_str("MY_SECRET_KEY", ""),
        jwt_secret_key=jwt_raw,
        cors_allowed_origins=cors_raw,
        cors_allowed_origins_list=["*"] if cors_raw == "*" else _as_csv("CORS_ALLOWED_ORIGINS", ""),
        rate_limit_enabled=_as_bool("RATE_LIMIT_ENABLED", True),
        rate_limit_per_minute=_as_int("RATE_LIMIT_PER_MINUTE", 60),
        rate_limit_per_hour=_as_int("RATE_LIMIT_PER_HOUR", 1000),
    )

    sandbox = SandboxSettings(
        max_memory_mb=_as_int("SANDBOX_MAX_MEMORY_MB", 256),
        max_cpu_time=_as_int("SANDBOX_MAX_CPU_TIME", 5),
        max_upload_size_mb=_as_int("MAX_UPLOAD_SIZE_MB", 10),
        dynamic_test_timeout=_as_int("DYNAMIC_TEST_TIMEOUT", 5),
    )

    features = FeatureSettings(
        metrics_enabled=_as_bool("METRICS_ENABLED", True),
        log_level=_as_str("LOG_LEVEL", "INFO").upper(),
        log_format=_as_str("LOG_FORMAT", "text").lower(),
        plagiarism_threshold=_as_float("PLAGIARISM_THRESHOLD", 0.85),
        pass_score_threshold=_as_int("PASS_SCORE_THRESHOLD", 50),
        webhook_max_retries=_as_int("WEBHOOK_MAX_RETRIES", 3),
        webhook_retry_delay=_as_int("WEBHOOK_RETRY_DELAY", 2),
    )

    integrations = IntegrationSettings(
        question_bank_api_url=_as_str("QUESTION_BANK_API_URL", "https://api-dsa-python.onrender.com"),
        rubric_api_url=_as_str("RUBRIC_API_URL", "https://api-dsa-python.onrender.com/api/rubrics"),
    )

    return DSAConfig(
        app=app,
        ai=ai,
        database=database,
        security=security,
        sandbox=sandbox,
        features=features,
        integrations=integrations,
        paths=paths,
    )


SETTINGS = build_config()


# ---------------------------------------------------------------------------
# Validation and logging
# ---------------------------------------------------------------------------
def _validate(config: DSAConfig) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    if config.app.port <= 0 or config.app.port > 65535:
        errors.append("PORT must be between 1 and 65535")

    if config.features.plagiarism_threshold < 0 or config.features.plagiarism_threshold > 1:
        errors.append("PLAGIARISM_THRESHOLD must be between 0 and 1")

    if config.features.pass_score_threshold < 0 or config.features.pass_score_threshold > 100:
        errors.append("PASS_SCORE_THRESHOLD must be between 0 and 100")

    if config.security.rate_limit_per_minute <= 0:
        errors.append("RATE_LIMIT_PER_MINUTE must be > 0")

    if config.security.rate_limit_per_hour <= 0:
        errors.append("RATE_LIMIT_PER_HOUR must be > 0")

    if config.sandbox.max_memory_mb < 64:
        warnings.append("SANDBOX_MAX_MEMORY_MB is very low; code execution may fail unexpectedly")

    if config.sandbox.max_cpu_time < 1:
        errors.append("SANDBOX_MAX_CPU_TIME must be >= 1")

    if config.app.is_production:
        if config.ai.provider != "gemini":
            errors.append("AI_PROVIDER must be 'gemini'")

        if not config.ai.gemini_api_key:
            errors.append("GEMINI_API_KEY is required in production when AI_PROVIDER=gemini")

        if not config.security.my_secret_key:
            errors.append("MY_SECRET_KEY is required in production")

        # JWT_SECRET_KEY is already enforced at build time, but double-check here
        if not config.security.jwt_secret_key or len(config.security.jwt_secret_key) < 32:
            errors.append("JWT_SECRET_KEY must be set and at least 32 characters in production")

        if config.security.cors_allowed_origins == "*":
            warnings.append("CORS_ALLOWED_ORIGINS='*' in production is unsafe")
    else:
        if not config.ai.gemini_api_key:
            warnings.append("GEMINI_API_KEY not set; using fallback grading mode")

        if config.security.jwt_secret_key.startswith("dev-secret-change-me"):
            warnings.append(
                "JWT_SECRET_KEY is using development default value. "
                "Set a secure value for production!"
            )

    if config.database.redis_url and not config.database.redis_url.startswith("redis://"):
        warnings.append("REDIS_URL should start with redis://")

    return errors, warnings


def validate_config() -> bool:
    errors, warnings = _validate(SETTINGS)

    for message in errors:
        logger.error("CONFIG ERROR: %s", message)

    for message in warnings:
        logger.warning("CONFIG WARNING: %s", message)

    return not errors


def check_and_log_config() -> None:
    logger.info("=" * 60)
    logger.info("DSA AutoGrader Configuration")
    logger.info("=" * 60)
    logger.info("Environment: %s", SETTINGS.app.environment)
    logger.info("Production: %s", SETTINGS.app.is_production)
    logger.info("Port: %s", SETTINGS.app.port)
    logger.info("Rate Limiting: %s", "Enabled" if SETTINGS.security.rate_limit_enabled else "Disabled")
    logger.info("Metrics: %s", "Enabled" if SETTINGS.features.metrics_enabled else "Disabled")
    logger.info("AI Provider/Model: %s / %s", SETTINGS.ai.provider, SETTINGS.ai.model_name)
    logger.info("Database: %s", "SQL Server" if SETTINGS.database.sql_server_url else "SQLite")
    logger.info("Redis: %s", "Enabled" if SETTINGS.database.redis_url else "Disabled (in-memory)")
    logger.info("Base Dir: %s", SETTINGS.paths.base_dir)
    logger.info("Data Dir: %s", SETTINGS.paths.data_dir)
    logger.info("=" * 60)

    if not validate_config():
        logger.error("Configuration validation failed. Exiting...")
        sys.exit(1)

    # Secret status only (masked)
    logger.info("GEMINI_API_KEY: %s", _mask_secret(SETTINGS.ai.gemini_api_key))
    logger.info("MY_SECRET_KEY: %s", _mask_secret(SETTINGS.security.my_secret_key))
    logger.info("JWT_SECRET_KEY: %s", _mask_secret(SETTINGS.security.jwt_secret_key))
    logger.info("=" * 60)


__all__ = [
    "SETTINGS",
    "DSAConfig",
    "check_and_log_config",
    "validate_config",
]
