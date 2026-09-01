from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .vector import Vector


class Base(DeclarativeBase):
    pass


class Incident(Base):
    """One synthetic network incident.

    confirmed_cause is nullable ON PURPOSE: some incidents genuinely have no
    confirmed cause yet. The agent must say "unknown" for these, never guess
    one — see INC-1042 in seed.py, which is the demo case for this.
    """

    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # 'open' | 'resolved'
    affected_customers: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)  # 'low'|'medium'|'high'|'critical'
    planned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confirmed_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_update: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProcedureChunk(Base):
    """One heading-aware section of a synthetic procedure document.

    document/section/text/version/synthetic_source together are the
    provenance record: whatever the agent cites must trace back to exactly
    one row here, word for word. The agent never invents a section name.
    """

    __tablename__ = "procedure_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document: Mapped[str] = mapped_column(String(128), nullable=False)  # e.g. "outage_escalation"
    section: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "3.2 Escalation conditions"
    text: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(16), nullable=False, default="1.0")
    synthetic_source: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    embedding: Mapped[list[float]] = mapped_column(Vector, nullable=False)


class TicketDraft(Base):
    """A draft escalation ticket. Never sent anywhere; exists only in this table.

    status starts at "draft" and can only move to "confirmed" via the
    explicit /api/tickets/{id}/confirm endpoint -- a separate human action,
    never something the agent or LLM can trigger itself.
    """

    __tablename__ = "ticket_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_priority: Mapped[str] = mapped_column(String(16), nullable=False)
    requested_action: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_evidence: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")  # 'draft' | 'confirmed'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
