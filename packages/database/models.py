"""Persistent job schema with UUID primary identifiers."""

from sqlalchemy import Column, DateTime, MetaData, String, Table, func

metadata = MetaData()
analysis_jobs = Table(
    "analysis_jobs",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("status", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
