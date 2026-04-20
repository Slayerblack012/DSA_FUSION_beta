# DSA Fusion Backend

Backend service for automated DSA grading.

## Core Capabilities

- File and archive submission handling
- AST-based static grading
- Optional AI-assisted grading
- Sandboxed dynamic test execution
- Plagiarism checking
- Grading history and analytics APIs

## Tech Stack

- FastAPI
- SQLAlchemy
- Redis (optional but recommended)
- Uvicorn

## Setup

From backend folder:

    python -m pip install -r requirements.txt -r requirements-dev.txt

## Run

    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

Health endpoints:

- /health
- /ready
- /metrics

## Security and Runtime Hardening

- Security headers middleware enabled
- Rate limiter with Redis-backed mode and in-memory fallback
- Safe archive extraction with traversal and resource limits
- Sandboxed execution with timeout and memory enforcement
- Dynamic SQL identifier safety validation for schema-driven queries

## Testing

Run targeted hardening regressions:

    python -m pytest tests/test_archive_safety.py tests/test_sandbox_execution.py -q

Run full backend tests:

    python -m pytest -q tests

## Quality Gates

Local pre-commit:

    pre-commit install
    pre-commit run --all-files

CI:

- .github/workflows/ci.yml
- .github/workflows/security.yml

## Configuration

Backend uses environment variables loaded from project-level .env.
Important production variables include JWT secret and AI provider keys.
