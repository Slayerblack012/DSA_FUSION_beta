"""
DSA AutoGrader - Authentication API.

Features:
- Login with bcrypt + JWT
- Refresh token rotation (single-use)
- Logout with token revocation
- Auth statistics
"""

from fastapi import APIRouter, HTTPException, Depends, Form, Header, Request
from fastapi.responses import JSONResponse
import logging

from app.containers.container import get_container
from app.utils.auth import (
    verify_password,
    create_access_token,
    create_refresh_token,
    refresh_access_token,
    revoke_token,
    verify_token,
    get_token_stats,
)
from app.utils.audit_logger import (
    audit_auth_login,
    audit_auth_logout,
)

logger = logging.getLogger("dsa.auth")
router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    """
    Login endpoint.

    Returns:
    - access_token: JWT token for API calls (expires in 20h)
    - refresh_token: JWT token for refreshing access_token (expires in 7d)
    """
    client_ip = request.client.host if request.client else "unknown"
    logger.info("Login attempt for username: %s", username)

    container = get_container()
    repo = container.get_repository()

    user = repo.get_user_by_username(username)
    if not user:
        audit_auth_login(username, success=False, ip=client_ip, detail="User not found")
        logger.warning("User not found: %s", username)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    password_valid = verify_password(password, user["password_hash"])
    if not password_valid:
        audit_auth_login(username, success=False, ip=client_ip, detail="Invalid password")
        logger.warning("Invalid password for user: %s", username)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Create JWT token pair
    access_token = create_access_token(user["id"], user["username"])
    refresh_token = create_refresh_token(user["id"], user["username"])

    audit_auth_login(username, success=True, ip=client_ip, detail="role=STUDENT")
    logger.info("Login successful for: %s, role: STUDENT", username)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "username": user["username"],
        "full_name": user["full_name"],
        "role": "STUDENT",
        "access_token_expires_in": "20 hours",
        "refresh_token_expires_in": "7 days",
    }


@router.post("/refresh")
async def refresh_access_token(
    request: Request,
    refresh_token_str: str = Form(...),
):
    """
    Refresh access token using a valid refresh token.

    Implements refresh token rotation: old token is blacklisted, new pair issued.
    """
    client_ip = request.client.host if request.client else "unknown"

    result = refresh_access_token(refresh_token_str)
    if not result:
        audit_auth_login("refresh", success=False, ip=client_ip, detail="Invalid/expired refresh token")
        raise HTTPException(status_code=401, detail="Refresh token expired or invalid. Please login again.")

    new_access, new_refresh = result
    audit_auth_login("refresh", success=True, ip=client_ip, detail="Token refreshed")

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "access_token_expires_in": "20 hours",
        "refresh_token_expires_in": "7 days",
    }


@router.post("/logout")
async def logout(request: Request, authorization: str = Header(...)):
    """
    Logout endpoint. Revokes the current access token.
    """
    client_ip = request.client.host if request.client else "unknown"
    token = authorization.replace("Bearer ", "").strip()

    # Try to revoke access token
    revoked = revoke_token(token)

    # Also try to extract user for logging
    try:
        token_data = verify_token(token, token_type="access")
        username = token_data.get("username", "unknown") if token_data else "unknown"
    except Exception:
        username = "unknown"

    audit_auth_logout(username, ip=client_ip)
    logger.info("Logout for user: %s (revoked=%s)", username, revoked)

    return {"message": "Logged out successfully"}


@router.get("/stats")
async def get_auth_stats():
    """Get authentication statistics."""
    return get_token_stats()
