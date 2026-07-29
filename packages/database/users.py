"""Persistence adapter for user identities and opaque sessions."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Engine, create_engine, delete, insert, select, update
from sqlalchemy.exc import IntegrityError

from .models import user_sessions, users


class DuplicateUserError(ValueError):
    """Raised when a normalized email address is already registered."""


@dataclass(frozen=True, slots=True)
class UserRecord:
    """Private account record used by the authentication service."""

    id: str
    email: str
    display_name: str
    password_hash: str
    role: str = "user"
    status: str = "pending"
    created_at: datetime | None = None


class UserRepository:
    """Persist accounts and hashed session tokens in short transactions."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @classmethod
    def from_environment(cls) -> UserRepository:
        """Build the production repository from the shared database URL."""
        return cls(create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True))

    def create(
        self,
        *,
        user_id: str,
        email: str,
        display_name: str,
        password_hash: str,
        role: str = "user",
        status: str = "pending",
    ) -> UserRecord:
        """Create one account, rejecting a concurrent duplicate email."""
        try:
            with self._engine.begin() as connection:
                connection.execute(
                    insert(users).values(
                        id=user_id,
                        email=email,
                        display_name=display_name,
                        password_hash=password_hash,
                        role=role,
                        status=status,
                    )
                )
        except IntegrityError as error:
            raise DuplicateUserError("An account already exists for this email") from error
        created = self.get(user_id)
        if created is None:  # pragma: no cover - database invariant
            raise RuntimeError("User disappeared after creation")
        return created

    def get(self, user_id: str) -> UserRecord | None:
        """Return one account by identifier."""
        with self._engine.connect() as connection:
            row = (
                connection.execute(select(users).where(users.c.id == user_id))
                .mappings()
                .one_or_none()
            )
        return _user(row) if row is not None else None

    def get_by_email(self, email: str) -> UserRecord | None:
        """Return one account by its normalized email."""
        with self._engine.connect() as connection:
            row = (
                connection.execute(select(users).where(users.c.email == email))
                .mappings()
                .one_or_none()
            )
        return _user(row) if row is not None else None

    def ensure_admin(
        self,
        *,
        user_id: str,
        email: str,
        display_name: str,
        password_hash: str,
    ) -> UserRecord:
        """Create or promote the configured administrator idempotently."""
        existing = self.get_by_email(email)
        if existing is None:
            try:
                return self.create(
                    user_id=user_id,
                    email=email,
                    display_name=display_name,
                    password_hash=password_hash,
                    role="admin",
                    status="active",
                )
            except DuplicateUserError:
                existing = self.get_by_email(email)
                if existing is None:  # pragma: no cover - defensive race invariant
                    raise
        with self._engine.begin() as connection:
            connection.execute(
                update(users)
                .where(users.c.id == existing.id)
                .values(
                    display_name=display_name,
                    password_hash=password_hash,
                    role="admin",
                    status="active",
                )
            )
        promoted = self.get(existing.id)
        if promoted is None:  # pragma: no cover - database invariant
            raise RuntimeError("Administrator disappeared during bootstrap")
        return promoted

    def list_pending(self, limit: int = 100) -> list[UserRecord]:
        """Return bounded account requests in creation order."""
        with self._engine.connect() as connection:
            rows = (
                connection.execute(
                    select(users)
                    .where(users.c.status == "pending")
                    .order_by(users.c.created_at)
                    .limit(max(1, min(limit, 100)))
                )
                .mappings()
                .all()
            )
        return [_user(row) for row in rows]

    def set_status(self, user_id: str, account_status: str) -> UserRecord | None:
        """Approve or reject one non-admin account request."""
        with self._engine.begin() as connection:
            result = connection.execute(
                update(users)
                .where(
                    users.c.id == user_id,
                    users.c.role != "admin",
                    users.c.status == "pending",
                )
                .values(status=account_status)
            )
        if result.rowcount != 1:
            return None
        return self.get(user_id)

    def create_session(self, *, token_hash: str, user_id: str, expires_at: datetime) -> None:
        """Store only the SHA-256 digest of an opaque browser session."""
        with self._engine.begin() as connection:
            connection.execute(
                insert(user_sessions).values(
                    token_hash=token_hash,
                    user_id=user_id,
                    expires_at=expires_at,
                )
            )

    def user_for_session(self, token_hash: str, now: datetime) -> UserRecord | None:
        """Resolve a non-expired session to its owner."""
        with self._engine.begin() as connection:
            connection.execute(delete(user_sessions).where(user_sessions.c.expires_at <= now))
            row = (
                connection.execute(
                    select(users)
                    .join(user_sessions, user_sessions.c.user_id == users.c.id)
                    .where(
                        user_sessions.c.token_hash == token_hash,
                        user_sessions.c.expires_at > now,
                    )
                )
                .mappings()
                .one_or_none()
            )
        return _user(row) if row is not None else None

    def delete_session(self, token_hash: str) -> None:
        """Revoke one browser session without affecting other devices."""
        with self._engine.begin() as connection:
            connection.execute(
                delete(user_sessions).where(user_sessions.c.token_hash == token_hash)
            )


def _user(row: Any) -> UserRecord:
    return UserRecord(
        id=row["id"],
        email=row["email"],
        display_name=row["display_name"],
        password_hash=row["password_hash"],
        role=row["role"],
        status=row["status"],
        created_at=row["created_at"],
    )
