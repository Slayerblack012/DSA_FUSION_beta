"""Backward-compatible config exports built on top of dsa_config."""

from app.core.dsa_config import SETTINGS, check_and_log_config, validate_config

# Environment
ENVIRONMENT = SETTINGS.app.environment
IS_PRODUCTION = SETTINGS.app.is_production
IS_DEVELOPMENT = SETTINGS.app.is_development
IS_TESTING = SETTINGS.app.is_testing

# AI
AI_PROVIDER = SETTINGS.ai.provider
GEMINI_API_KEY = SETTINGS.ai.gemini_api_key
AI_MODEL_NAME = SETTINGS.ai.model_name
AI_MODEL_TEMPERATURE = SETTINGS.ai.model_temperature
AI_MAX_OUTPUT_TOKENS = SETTINGS.ai.max_output_tokens
MAX_CONCURRENT_AI_CALLS = SETTINGS.ai.max_concurrent_calls

# Security
MY_SECRET_KEY = SETTINGS.security.my_secret_key

QUESTION_BANK_API_URL = SETTINGS.integrations.question_bank_api_url
RUBRIC_API_URL = SETTINGS.integrations.rubric_api_url

# Data stores
SQL_SERVER_URL = SETTINGS.database.sql_server_url
REDIS_URL = SETTINGS.database.redis_url
DB_NAME = SETTINGS.database.db_name
DB_FILE = SETTINGS.database.db_file
MAX_HISTORY_ROWS = SETTINGS.database.max_history_rows
JOB_TTL_SECONDS = SETTINGS.database.job_ttl_seconds

AI_MODEL_NAME = SETTINGS.ai.model_name
AI_MODEL_TEMPERATURE = SETTINGS.ai.model_temperature
AI_MAX_OUTPUT_TOKENS = SETTINGS.ai.max_output_tokens
MAX_CONCURRENT_AI_CALLS = SETTINGS.ai.max_concurrent_calls

# Paths
BASE_DIR = SETTINGS.paths.base_dir
DATA_DIR = SETTINGS.paths.data_dir
TESTCASE_ROOT = SETTINGS.paths.testcase_root
LOGS_DIR = SETTINGS.paths.logs_dir

# Grading thresholds
PLAGIARISM_THRESHOLD = SETTINGS.features.plagiarism_threshold
PASS_SCORE_THRESHOLD = SETTINGS.features.pass_score_threshold

# Server
PORT = SETTINGS.app.port
AUTO_RELOAD = SETTINGS.app.auto_reload

# Security
RATE_LIMIT_ENABLED = SETTINGS.security.rate_limit_enabled
RATE_LIMIT_PER_MINUTE = SETTINGS.security.rate_limit_per_minute
RATE_LIMIT_PER_HOUR = SETTINGS.security.rate_limit_per_hour
JWT_SECRET_KEY = SETTINGS.security.jwt_secret_key
CORS_ALLOWED_ORIGINS = SETTINGS.security.cors_allowed_origins

# Sandbox
SANDBOX_MAX_MEMORY_MB = SETTINGS.sandbox.max_memory_mb
SANDBOX_MAX_CPU_TIME = SETTINGS.sandbox.max_cpu_time
MAX_UPLOAD_SIZE_MB = SETTINGS.sandbox.max_upload_size_mb
DYNAMIC_TEST_TIMEOUT = SETTINGS.sandbox.dynamic_test_timeout

# Logging / monitoring
LOG_LEVEL = SETTINGS.features.log_level
LOG_FORMAT = SETTINGS.features.log_format
METRICS_ENABLED = SETTINGS.features.metrics_enabled

# Webhooks
WEBHOOK_MAX_RETRIES = SETTINGS.features.webhook_max_retries
WEBHOOK_RETRY_DELAY = SETTINGS.features.webhook_retry_delay


__all__ = [
    "SETTINGS",
    "ENVIRONMENT",
    "IS_PRODUCTION",
    "IS_DEVELOPMENT",
    "IS_TESTING",
    "AI_PROVIDER",
    "GEMINI_API_KEY",
    "MY_SECRET_KEY",
    "QUESTION_BANK_API_URL",
    "RUBRIC_API_URL",
    "SQL_SERVER_URL",
    "REDIS_URL",
    "DB_NAME",
    "DB_FILE",
    "MAX_HISTORY_ROWS",
    "JOB_TTL_SECONDS",
    "AI_MODEL_NAME",
    "AI_MODEL_TEMPERATURE",
    "AI_MAX_OUTPUT_TOKENS",
    "MAX_CONCURRENT_AI_CALLS",
    "BASE_DIR",
    "DATA_DIR",
    "TESTCASE_ROOT",
    "LOGS_DIR",
    "PLAGIARISM_THRESHOLD",
    "PASS_SCORE_THRESHOLD",
    "PORT",
    "AUTO_RELOAD",
    "RATE_LIMIT_ENABLED",
    "RATE_LIMIT_PER_MINUTE",
    "RATE_LIMIT_PER_HOUR",
    "JWT_SECRET_KEY",
    "CORS_ALLOWED_ORIGINS",
    "SANDBOX_MAX_MEMORY_MB",
    "SANDBOX_MAX_CPU_TIME",
    "MAX_UPLOAD_SIZE_MB",
    "DYNAMIC_TEST_TIMEOUT",
    "LOG_LEVEL",
    "LOG_FORMAT",
    "METRICS_ENABLED",
    "WEBHOOK_MAX_RETRIES",
    "WEBHOOK_RETRY_DELAY",
    "validate_config",
    "check_and_log_config",
]
