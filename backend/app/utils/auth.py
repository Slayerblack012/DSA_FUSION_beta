"""
DSA AutoGrader - Authentication & Authorization.

Features:
- bcrypt password hashing (cost factor 12)
- JWT signed tokens (HS256) with expiration
- Refresh token mechanism with blacklist
- Audit logging for security events
"""

import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

import bcrypt
import jwt

from app.core.config import JWT_SECRET_KEY, IS_PRODUCTION

logger = logging.getLogger("dsa.auth")

# ── JWT Configuration ──────────────────────────────────────────────────────
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRY_HOURS = 20
REFRESH_TOKEN_EXPIRY_DAYS = 7

# ── Token blacklist (in-memory, production should use Redis) ───────────────
_token_blacklist: Dict[str, float] = {}


# ── Password Hashing (bcrypt) ─────────────────────────────────────────────
def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with cost factor 12.

    bcrypt generates a random salt internally, so no need for manual salt.
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash."""
    try:
        password_bytes = password.encode("utf-8")
        hash_bytes = password_hash.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except (ValueError, Exception) as exc:
        logger.error("Password verification failed: %s", exc)
        return False


# ── JWT Token Management ──────────────────────────────────────────────────
def _get_jwt_secret() -> str:
    """
    Get JWT secret key. In production, this MUST be set via environment variable.
    Falls back to a hash of JWT_SECRET_KEY for backward compatibility.
    """
    if not JWT_SECRET_KEY or JWT_SECRET_KEY.startswith("5a1ToRxZ"):
        if IS_PRODUCTION:
            raise RuntimeError(
                "CRITICAL: JWT_SECRET_KEY must be set in production environment. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
            )
        logger.warning(
            "Using default JWT_SECRET_KEY. This is INSECURE for production!"
        )
    return JWT_SECRET_KEY


def create_access_token(
    user_id: int,
    username: str,
    expiry_hours: int = ACCESS_TOKEN_EXPIRY_HOURS,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        user_id: User database ID
        username: Username for display
        expiry_hours: Token validity in hours

    Returns:
        Signed JWT token string
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": "STUDENT",
        "type": "access",
        "iat": now,
        "exp": now + timedelta(hours=expiry_hours),
        "jti": str(uuid.uuid4()),  # Unique token ID
    }
    secret = _get_jwt_secret()
    token = jwt.encode(payload, secret, algorithm=ALGORITHM)
    logger.debug("Created access token for user: %s (jti=%s)", username, payload["jti"])
    return token


def create_refresh_token(user_id: int, username: str) -> str:
    """
    Create a signed JWT refresh token with longer expiry (7 days).

    Refresh tokens can only be used to get new access tokens, not for API access.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": "STUDENT",
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS),
        "jti": str(uuid.uuid4()),
    }
    secret = _get_jwt_secret()
    token = jwt.encode(payload, secret, algorithm=ALGORITHM)
    return token


def verify_token(token: str, token_type: str = "access") -> Optional[Dict]:
    """
    Verify a JWT token and return payload data.

    Args:
        token: JWT token string
        token_type: Expected token type ("access" or "refresh")

    Returns:
        Dict with user info or None if invalid
    """
    try:
        secret = _get_jwt_secret()
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])

        # Check token type
        if payload.get("type") != token_type:
            logger.warning("Token type mismatch: expected=%s, got=%s", token_type, payload.get("type"))
            return None

        # Check blacklist
        jti = payload.get("jti")
        if jti and jti in _token_blacklist:
            logger.warning("Token blacklisted: jti=%s", jti)
            return None

        return {
            "user_id": int(payload["sub"]),
            "username": payload["username"],
            "role": "STUDENT",
            "jti": payload.get("jti"),
            "expires": payload["exp"],
        }

    except jwt.ExpiredSignatureError:
        logger.debug("Token expired")
        return None
    except jwt.InvalidTokenError as exc:
        logger.warning("Invalid token: %s", exc)
        return None


def refresh_access_token(refresh_token_str: str) -> Optional[Tuple[str, str]]:
    """
    Refresh an access token using a valid refresh token.

    Returns:
        (new_access_token, new_refresh_token) or None if refresh token invalid
    """
    data = verify_token(refresh_token_str, token_type="refresh")
    if not data:
        return None

    # Blacklist old refresh token (single-use policy)
    old_jti = data.get("jti")
    if old_jti:
        _token_blacklist[old_jti] = time.time()

    # Issue new token pair
    new_access = create_access_token(data["user_id"], data["username"])
    new_refresh = create_refresh_token(data["user_id"], data["username"])
    return new_access, new_refresh


def revoke_token(token: str) -> bool:
    """
    Revoke a token by adding it to the blacklist.

    Useful for logout functionality.
    """
    try:
        secret = _get_jwt_secret()
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        if jti:
            _token_blacklist[jti] = time.time()
            logger.info("Token revoked: jti=%s", jti)
            return True
    except jwt.InvalidTokenError:
        pass
    return False


def cleanup_blacklist() -> int:
    """
    Remove expired entries from the token blacklist.
    Call periodically to prevent memory growth.
    """
    now = time.time()
    # Remove entries older than refresh token expiry + buffer
    max_age = (REFRESH_TOKEN_EXPIRY_DAYS + 1) * 86400
    old_keys = [k for k, v in _token_blacklist.items() if now - v > max_age]
    for k in old_keys:
        del _token_blacklist[k]
    if old_keys:
        logger.info("Cleaned %d expired blacklist entries", len(old_keys))
    return len(old_keys)


def get_current_user(authorization_header: str) -> Optional[Dict]:
    """
    Extract and verify user from Authorization header.

    Usage: user = get_current_user(request.headers.get("Authorization", ""))
    """
    if not authorization_header or not authorization_header.startswith("Bearer "):
        return None

    token = authorization_header[7:].strip()
    return verify_token(token, token_type="access")


def get_token_stats() -> Dict:
    """Get authentication statistics."""
    now = time.time()
    active = sum(1 for v in _token_blacklist.values() if now - v < 86400 * REFRESH_TOKEN_EXPIRY_DAYS)
    return {
        "blacklisted_tokens": len(_token_blacklist),
        "active_blacklist_entries": active,
        "access_token_expiry_hours": ACCESS_TOKEN_EXPIRY_HOURS,
        "refresh_token_expiry_days": REFRESH_TOKEN_EXPIRY_DAYS,
        "algorithm": ALGORITHM,
    }
