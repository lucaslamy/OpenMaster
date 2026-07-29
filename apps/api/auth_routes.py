"""HTTP account, session-cookie, and current-user boundary."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel

from packages.auth import (
    AuthenticationError,
    AuthSession,
    AuthUser,
    InvalidAccountError,
    UserAuthService,
)

SESSION_COOKIE = "openmaster_session"
router = APIRouter(prefix="/api/v1/auth", tags=["accounts"])


class RegisterRequest(BaseModel):
    """Fields required to create an account."""

    email: str
    display_name: str
    password: str


class LoginRequest(BaseModel):
    """Credentials accepted by the session endpoint."""

    email: str
    password: str


class UserResponse(BaseModel):
    """Public account identity."""

    id: str
    email: str
    display_name: str
    role: str
    status: str
    created_at: str | None = None


@lru_cache(maxsize=1)
def get_auth_service() -> UserAuthService:
    """Build the production authentication service once per API process."""
    return UserAuthService.from_environment()


def require_user(
    service: Annotated[UserAuthService, Depends(get_auth_service)],
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> AuthUser:
    """Require a valid HttpOnly session cookie."""
    user = service.authenticate(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_admin(user: Annotated[AuthUser, Depends(require_user)]) -> AuthUser:
    """Restrict account-review operations to active administrators."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_202_ACCEPTED)
def register(
    request: RegisterRequest,
    service: Annotated[UserAuthService, Depends(get_auth_service)],
) -> UserResponse:
    """Create a pending account request for administrator review."""
    try:
        user = service.register(
            email=request.email,
            display_name=request.display_name,
            password=request.password,
        )
    except InvalidAccountError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return _response(user)


@router.post("/login", response_model=UserResponse)
def login(
    request: LoginRequest,
    response: Response,
    service: Annotated[UserAuthService, Depends(get_auth_service)],
) -> UserResponse:
    """Authenticate an account and rotate to a fresh session."""
    try:
        session = service.login(email=request.email, password=request.password)
    except AuthenticationError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    _set_session_cookie(response, session)
    return _response(session.user)


@router.get("/me", response_model=UserResponse)
def me(user: Annotated[AuthUser, Depends(require_user)]) -> UserResponse:
    """Return the owner of the active session."""
    return _response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    service: Annotated[UserAuthService, Depends(get_auth_service)],
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> None:
    """Revoke the active session and expire its cookie."""
    service.logout(token)
    response.delete_cookie(SESSION_COOKIE, path="/", samesite="strict")


@router.get("/admin/requests", response_model=list[UserResponse])
def list_account_requests(
    service: Annotated[UserAuthService, Depends(get_auth_service)],
    _admin: Annotated[AuthUser, Depends(require_admin)],
) -> list[UserResponse]:
    """List pending registrations for an administrator."""
    return [_response(user) for user in service.list_pending()]


@router.post("/admin/requests/{user_id}/approve", response_model=UserResponse)
def approve_account_request(
    user_id: str,
    service: Annotated[UserAuthService, Depends(get_auth_service)],
    _admin: Annotated[AuthUser, Depends(require_admin)],
) -> UserResponse:
    """Activate a requested account."""
    user = service.approve(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Account request not found")
    return _response(user)


@router.post("/admin/requests/{user_id}/reject", response_model=UserResponse)
def reject_account_request(
    user_id: str,
    service: Annotated[UserAuthService, Depends(get_auth_service)],
    _admin: Annotated[AuthUser, Depends(require_admin)],
) -> UserResponse:
    """Reject a requested account."""
    user = service.reject(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Account request not found")
    return _response(user)


def _set_session_cookie(response: Response, session: AuthSession) -> None:
    secure = os.environ.get("AUTH_COOKIE_SECURE", "true").strip().lower() not in {
        "0",
        "false",
        "no",
    }
    response.set_cookie(
        SESSION_COOKIE,
        session.token,
        expires=session.expires_at,
        httponly=True,
        secure=secure,
        samesite="strict",
        path="/",
    )


def _response(user: AuthUser) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        status=user.status,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )
