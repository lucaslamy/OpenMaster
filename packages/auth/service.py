"""Password hashing and opaque-session business logic."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from packages.database import DuplicateUserError, UserRecord, UserRepository

PBKDF2_ITERATIONS = 600_000
SESSION_DAYS_ENV = "AUTH_SESSION_DAYS"
DEFAULT_SESSION_DAYS = 30
ADMIN_EMAIL_ENV = "OPENMASTER_ADMIN_EMAIL"
ADMIN_PASSWORD_ENV = "OPENMASTER_ADMIN_PASSWORD"
ADMIN_NAME_ENV = "OPENMASTER_ADMIN_DISPLAY_NAME"
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class InvalidAccountError(ValueError):
    """Raised when registration data is unsafe or already used."""


class AuthenticationError(ValueError):
    """Raised for invalid credentials without revealing which field failed."""


@dataclass(frozen=True, slots=True)
class AuthUser:
    """Public account identity safe to expose through the API."""

    id: str
    email: str
    display_name: str
    role: str = "user"
    status: str = "pending"
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class AuthSession:
    """New opaque token and its authenticated owner."""

    token: str
    expires_at: datetime
    user: AuthUser


class UserAuthService:
    """Register accounts and issue revocable database-backed sessions."""

    def __init__(self, repository: UserRepository, *, session_days: int = DEFAULT_SESSION_DAYS):
        if not 1 <= session_days <= 365:
            raise ValueError("session_days must be between 1 and 365")
        self._repository = repository
        self._session_days = session_days

    @classmethod
    def from_environment(cls) -> UserAuthService:
        """Build the production service from environment configuration."""
        try:
            session_days = int(os.environ.get(SESSION_DAYS_ENV, str(DEFAULT_SESSION_DAYS)))
        except ValueError as error:
            raise RuntimeError("AUTH_SESSION_DAYS must be an integer") from error
        return cls(UserRepository.from_environment(), session_days=session_days)

    def register(self, *, email: str, display_name: str, password: str) -> AuthUser:
        """Create a pending account request without opening a session."""
        normalized_email = _normalize_email(email)
        normalized_name = " ".join(display_name.split())
        _validate_password(password)
        if not 2 <= len(normalized_name) <= 80:
            raise InvalidAccountError("Display name must contain between 2 and 80 characters")
        try:
            user = self._repository.create(
                user_id=str(uuid4()),
                email=normalized_email,
                display_name=normalized_name,
                password_hash=_hash_password(password),
                role="user",
                status="pending",
            )
        except DuplicateUserError as error:
            raise InvalidAccountError(str(error)) from error
        return _public_user(user)

    def login(self, *, email: str, password: str) -> AuthSession:
        """Authenticate with a generic failure path to avoid account discovery."""
        user = self._repository.get_by_email(email.strip().casefold())
        encoded = user.password_hash if user is not None else _hash_password("invalid-login")
        valid = _verify_password(password, encoded)
        if user is None or not valid:
            raise AuthenticationError("Invalid email or password")
        if user.status == "pending":
            raise AuthenticationError("Account is awaiting administrator approval")
        if user.status != "active":
            raise AuthenticationError("Account request was rejected")
        return self._new_session(user)

    def authenticate(self, token: str | None) -> AuthUser | None:
        """Resolve an opaque cookie without persisting its clear value."""
        if not token:
            return None
        user = self._repository.user_for_session(_token_hash(token), datetime.now(UTC))
        return _public_user(user) if user is not None and user.status == "active" else None

    def logout(self, token: str | None) -> None:
        """Revoke the supplied session if it exists."""
        if token:
            self._repository.delete_session(_token_hash(token))

    def bootstrap_admin_from_environment(self) -> AuthUser:
        """Create or rotate the single configured deployment administrator."""
        email = os.environ.get(ADMIN_EMAIL_ENV, "")
        password = os.environ.get(ADMIN_PASSWORD_ENV, "")
        display_name = os.environ.get(ADMIN_NAME_ENV, "OpenMaster Admin")
        if not email or not password:
            raise RuntimeError("OPENMASTER_ADMIN_EMAIL and OPENMASTER_ADMIN_PASSWORD are required")
        normalized_email = _normalize_email(email)
        normalized_name = " ".join(display_name.split())
        _validate_password(password)
        if not 2 <= len(normalized_name) <= 80:
            raise RuntimeError(
                "OPENMASTER_ADMIN_DISPLAY_NAME must contain between 2 and 80 characters"
            )
        admin = self._repository.ensure_admin(
            user_id=str(uuid4()),
            email=normalized_email,
            display_name=normalized_name,
            password_hash=_hash_password(password),
        )
        return _public_user(admin)

    def list_pending(self) -> list[AuthUser]:
        """Return pending registration requests for administrator review."""
        return [_public_user(user) for user in self._repository.list_pending()]

    def approve(self, user_id: str) -> AuthUser | None:
        """Activate one pending non-admin account."""
        user = self._repository.set_status(user_id, "active")
        return _public_user(user) if user is not None else None

    def reject(self, user_id: str) -> AuthUser | None:
        """Reject one non-admin account and revoke all of its sessions."""
        user = self._repository.set_status(user_id, "rejected")
        return _public_user(user) if user is not None else None

    def _new_session(self, user: UserRecord) -> AuthSession:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(days=self._session_days)
        self._repository.create_session(
            token_hash=_token_hash(token),
            user_id=user.id,
            expires_at=expires_at,
        )
        return AuthSession(token=token, expires_at=expires_at, user=_public_user(user))


def _normalize_email(email: str) -> str:
    normalized = email.strip().casefold()
    if len(normalized) > 320 or not EMAIL_PATTERN.fullmatch(normalized):
        raise InvalidAccountError("Enter a valid email address")
    return normalized


def _validate_password(password: str) -> None:
    if not 10 <= len(password) <= 128:
        raise InvalidAccountError("Password must contain between 10 and 128 characters")


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return (
        f"pbkdf2_sha256${PBKDF2_ITERATIONS}$"
        f"{urlsafe_b64encode(salt).decode()}${urlsafe_b64encode(digest).decode()}"
    )


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            urlsafe_b64decode(salt),
            int(iterations),
        )
        return hmac.compare_digest(candidate, urlsafe_b64decode(expected))
    except (ValueError, TypeError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _public_user(user: UserRecord) -> AuthUser:
    return AuthUser(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        status=user.status,
        created_at=user.created_at,
    )
