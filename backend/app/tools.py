"""The three tools the agent can call, and nothing else.

Each tool is: a JSON schema (what the LLM sees) + a dispatch function (what
Python actually runs). The LLM only ever supplies the arguments; every
dispatch function below does the real work in plain Python/SQL.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .incidents_repo import query_incidents
from .models import TicketDraft
from .priority import calculate_priority
from .retrieval import search_procedures

TOOL_SCHEMAS = [
    {
        "name": "query_incidents",
        "description": (
            "Look up network incidents from the structured database. Supports both "
            "searching (by status/region) and single-incident lookup (by incident_id). "
            "Each returned incident includes a calculated priority — do not recalculate "
            "or invent a priority yourself, use exactly what this tool returns."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "incident_id": {"type": "string", "description": "Exact incident ID, e.g. INC-1042"},
                "status": {"type": "string", "enum": ["open", "resolved"]},
                "region": {"type": "string"},
                "limit": {"type": "integer", "description": "Max rows to return, default 20"},
            },
        },
    },
    {
        "name": "search_procedures",
        "description": (
            "Search the synthetic operating-procedure documents for passages relevant to a "
            "question. Returns exact text with document name and section — always cite "
            "using exactly the document/section this tool returns, never invent one."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "draft_escalation_ticket",
        "description": (
            "Create a DRAFT escalation ticket for one incident. This never submits, sends, "
            "or approves anything — it only saves a draft row that a human must separately "
            "confirm via the UI. Do not claim the ticket has been sent or approved."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "incident_id": {"type": "string"},
                "summary": {"type": "string"},
                "proposed_priority": {"type": "string"},
                "requested_action": {"type": "string"},
                "supporting_evidence": {"type": "string"},
            },
            "required": ["incident_id", "summary", "proposed_priority", "requested_action", "supporting_evidence"],
        },
    },
]


def _incident_to_dict(record) -> dict:
    priority = calculate_priority(
        affected_customers=record.affected_customers,
        started_at=record.started_at,
        severity=record.severity,
        status=record.status,
        planned=record.planned,
    )
    return {
        "incident_id": record.incident_id,
        "region": record.region,
        "started_at": record.started_at.isoformat(),
        "resolved_at": record.resolved_at.isoformat() if record.resolved_at else None,
        "status": record.status,
        "affected_customers": record.affected_customers,
        "severity": record.severity,
        "planned": record.planned,
        # Deliberately literal None -> null, never a placeholder string, so
        # "no cause on file" and "cause is the string 'unknown'" can never
        # be confused downstream.
        "confirmed_cause": record.confirmed_cause,
        "last_update": record.last_update.isoformat(),
        "priority": {
            "score": priority.score,
            "label": priority.label,
            "reasons": priority.reasons,
            "missing_inputs": priority.missing_inputs,
            "disclaimer": priority.disclaimer,
        },
    }


def dispatch_query_incidents(session: Session, args: dict) -> dict:
    records = query_incidents(
        session,
        incident_id=args.get("incident_id"),
        status=args.get("status"),
        region=args.get("region"),
        limit=args.get("limit", 20),
    )
    return {"incidents": [_incident_to_dict(r) for r in records]}


def dispatch_search_procedures(session: Session, args: dict) -> dict:
    passages = search_procedures(session, args["query"])
    return {
        "passages": [
            {
                "document": p.document,
                "section": p.section,
                "text": p.text,
                "version": p.version,
                "synthetic_source": p.synthetic_source,
            }
            for p in passages
        ]
    }


def dispatch_draft_escalation_ticket(session: Session, args: dict) -> dict:
    incidents = query_incidents(session, incident_id=args["incident_id"], limit=1)
    if not incidents:
        return {"error": f"Incidentas {args['incident_id']!r} nerastas; juodraščio jam parengti negalima."}

    draft = TicketDraft(
        incident_id=args["incident_id"],
        summary=args["summary"],
        proposed_priority=args["proposed_priority"],
        requested_action=args["requested_action"],
        supporting_evidence=args["supporting_evidence"],
        status="draft",
        created_at=datetime.now(timezone.utc),
    )
    session.add(draft)
    session.commit()
    session.refresh(draft)
    return {
        "id": draft.id,
        "incident_id": draft.incident_id,
        "summary": draft.summary,
        "proposed_priority": draft.proposed_priority,
        "requested_action": draft.requested_action,
        "supporting_evidence": draft.supporting_evidence,
        "status": draft.status,
        "created_at": draft.created_at.isoformat(),
        "note": "JUODRAŠTIS — prieš patvirtinant šį įrašą reikalingas žmogaus patvirtinimas. Niekas nebuvo išsiųsta.",
    }


DISPATCH = {
    "query_incidents": dispatch_query_incidents,
    "search_procedures": dispatch_search_procedures,
    "draft_escalation_ticket": dispatch_draft_escalation_ticket,
}
