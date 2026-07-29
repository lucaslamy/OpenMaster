"""Account hashing, session, and project-isolation tests."""

from __future__ import annotations

from io import BytesIO
from typing import Any, cast

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from apps.api.auth_routes import require_admin
from packages.analysis_jobs import AnalysisJobService
from packages.auth import AuthenticationError, AuthUser, InvalidAccountError, UserAuthService
from packages.database import AnalysisJobRepository, UserRepository, metadata
from packages.database.models import user_sessions
from packages.storage import MinioObjectStore


class FakeObjectStore:
    """Minimal immutable store used to exercise owned submissions."""

    def upload(
        self,
        object_name: str,
        stream: Any,
        *,
        length: int,
        content_type: str,
    ) -> None:
        del object_name, content_type
        stream.read(length)


def _engine() -> Any:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata.create_all(engine)
    return engine


def test_registration_hashes_password_and_stores_only_session_digest() -> None:
    engine = _engine()
    users = UserRepository(engine)
    service = UserAuthService(users)

    requested = service.register(
        email=" Artist@Example.com ",
        display_name="  Studio   Artist ",
        password="a sufficiently long password",
    )

    stored = users.get(requested.id)
    assert stored is not None
    assert stored.email == "artist@example.com"
    assert stored.display_name == "Studio Artist"
    assert stored.status == "pending"
    assert stored.password_hash.startswith("pbkdf2_sha256$600000$")
    assert "sufficiently" not in stored.password_hash
    assert service.approve(requested.id) is not None
    session = service.login(
        email="artist@example.com",
        password="a sufficiently long password",
    )
    with engine.connect() as connection:
        session_hash = connection.execute(select(user_sessions.c.token_hash)).scalar_one()
    assert session.token not in session_hash
    assert service.authenticate(session.token) == session.user


def test_login_failure_is_generic_and_duplicate_registration_is_rejected() -> None:
    service = UserAuthService(UserRepository(_engine()))
    service.register(
        email="artist@example.com",
        display_name="Artist",
        password="a sufficiently long password",
    )

    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        service.login(email="artist@example.com", password="wrong-password")
    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        service.login(email="unknown@example.com", password="wrong-password")
    with pytest.raises(AuthenticationError, match="awaiting administrator approval"):
        service.login(
            email="artist@example.com",
            password="a sufficiently long password",
        )
    with pytest.raises(InvalidAccountError, match="already exists"):
        service.register(
            email="ARTIST@example.com",
            display_name="Another",
            password="another long password",
        )


def test_admin_bootstrap_promotes_configured_identity_and_reviews_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = UserAuthService(UserRepository(_engine()))
    monkeypatch.setenv("OPENMASTER_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("OPENMASTER_ADMIN_PASSWORD", "an administrator password")
    monkeypatch.setenv("OPENMASTER_ADMIN_DISPLAY_NAME", "Chief Engineer")

    admin = service.bootstrap_admin_from_environment()
    request = service.register(
        email="new@example.com",
        display_name="New User",
        password="a pending password",
    )

    assert admin.role == "admin"
    assert admin.status == "active"
    assert (
        service.login(
            email="admin@example.com",
            password="an administrator password",
        ).user
        == admin
    )
    assert service.list_pending() == [request]
    approved = service.approve(request.id)
    assert approved is not None
    assert approved.status == "active"
    assert service.list_pending() == []

    monkeypatch.setenv("OPENMASTER_ADMIN_PASSWORD", "a rotated administrator password")
    assert service.bootstrap_admin_from_environment().id == admin.id
    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        service.login(
            email="admin@example.com",
            password="an administrator password",
        )
    assert (
        service.login(
            email="admin@example.com",
            password="a rotated administrator password",
        ).user.id
        == admin.id
    )


def test_admin_dependency_rejects_a_standard_active_user() -> None:
    with pytest.raises(HTTPException) as forbidden:
        require_admin(
            AuthUser(
                id="user-1",
                email="user@example.com",
                display_name="User",
                role="user",
                status="active",
            )
        )
    assert forbidden.value.status_code == 403


def test_projects_are_visible_only_to_their_owner() -> None:
    engine = _engine()
    users = UserAuthService(UserRepository(engine))
    first = users.register(
        email="one@example.com",
        display_name="One",
        password="first long password",
    )
    second = users.register(
        email="two@example.com",
        display_name="Two",
        password="second long password",
    )
    repository = AnalysisJobRepository(engine)
    service = AnalysisJobService(
        repository,
        cast(MinioObjectStore, FakeObjectStore()),
        lambda _job_id, _object_name: None,
        maximum_upload_bytes=1024,
    )

    project = service.submit(
        filename="private.wav",
        content_type="audio/wav",
        stream=BytesIO(b"audio"),
        length=5,
        idempotency_key="owner-one",
        user_id=first.id,
    )

    assert service.get_for_user(project.id, first.id) == project
    assert service.get_for_user(project.id, second.id) is None
    assert service.list_recent(user_id=first.id) == [project]
    assert service.list_recent(user_id=second.id) == []
    assert service.rename_project(project.id, "Stolen", user_id=second.id) is None
