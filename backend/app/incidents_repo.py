"""query_incidents: the ONLY way the agent touches incident data.

The LLM never sees or writes SQL. It calls this function with a small set of
validated parameters (incident_id, status, region, limit); this module is
the only place that builds the actual SQL query. That boundary is what makes
"the model does not get arbitrary SQL access" true rather than a promise.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Incident

VALID_STATUSES = {"open", "resolved"}
MAX_LIMIT = 50


@dataclass(frozen=True)
class IncidentRecord:
    incident_id: str
    region: str
    started_at: datetime
    resolved_at: datetime | None
    status: str
    affected_customers: int
    severity: str
    planned: bool
    confirmed_cause: str | None
    last_update: datetime


def _to_record(row: Incident) -> IncidentRecord:
    return IncidentRecord(
        incident_id=row.incident_id,
        region=row.region,
        started_at=row.started_at,
        resolved_at=row.resolved_at,
        status=row.status,
        affected_customers=row.affected_customers,
        severity=row.severity,
        planned=row.planned,
        confirmed_cause=row.confirmed_cause,
        last_update=row.last_update,
    )


def query_incidents(
    session: Session,
    *,
    incident_id: str | None = None,
    status: str | None = None,
    region: str | None = None,
    limit: int = 20,
) -> list[IncidentRecord]:
    if status is not None and status not in VALID_STATUSES:
        raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}, got {status!r}")
    limit = max(1, min(limit, MAX_LIMIT))

    statement = select(Incident)
    if incident_id is not None:
        statement = statement.where(Incident.incident_id == incident_id)
    if status is not None:
        statement = statement.where(Incident.status == status)
    if region is not None:
        statement = statement.where(Incident.region == region)
    statement = statement.order_by(Incident.affected_customers.desc()).limit(limit)

    return [_to_record(row) for row in session.scalars(statement)]
