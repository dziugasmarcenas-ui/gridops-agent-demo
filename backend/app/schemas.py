from datetime import datetime

from pydantic import BaseModel


class AgentQueryRequest(BaseModel):
    question: str


class AgentQueryResponse(BaseModel):
    answer: str
    tool_calls: list[dict]
    incidents: list[dict]
    procedures: list[dict]
    guard_triggered: bool = False
    priority_mismatch: bool = False


class TicketDraftRequest(BaseModel):
    incident_id: str
    summary: str
    proposed_priority: str
    requested_action: str
    supporting_evidence: str


class TicketDraftResponse(BaseModel):
    id: int
    incident_id: str
    summary: str
    proposed_priority: str
    requested_action: str
    supporting_evidence: str
    status: str
    created_at: datetime
    confirmed_at: datetime | None = None
