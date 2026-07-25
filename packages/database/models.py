"""Persistent job schema with UUID primary identifiers."""

from sqlalchemy import JSON, Column, DateTime, Float, Integer, MetaData, String, Table, Text, func

metadata = MetaData()
analysis_jobs = Table(
    "analysis_jobs",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("idempotency_key", String(255), nullable=True, unique=True),
    Column("status", String(32), nullable=False),
    Column("object_name", Text, nullable=True),
    Column("original_filename", Text, nullable=True),
    Column("attempt_count", Integer, nullable=False, server_default="0"),
    Column("result", JSON, nullable=True),
    Column("recommendation", JSON, nullable=True),
    Column("mastering_result", JSON, nullable=True),
    Column("output_object_name", Text, nullable=True),
    Column("target_lufs", Float, nullable=False, server_default="-14.0"),
    Column("bit_depth", Integer, nullable=False, server_default="24"),
    Column("error_code", String(64), nullable=True),
    Column("error_message", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
)
