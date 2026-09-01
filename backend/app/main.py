from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .agent import run_agent
from .db import SessionLocal
from .models import TicketDraft
from .schemas import (
    AgentQueryRequest,
    AgentQueryResponse,
    TicketDraftRequest,
    TicketDraftResponse,
)
from .tools import dispatch_draft_escalation_ticket

app = FastAPI(title="GRIDOPS AGENT API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "backend"}


@app.post("/api/agent/query", response_model=AgentQueryResponse)
def agent_query(request: AgentQueryRequest) -> AgentQueryResponse:
    with SessionLocal() as session:
        result = run_agent(session, request.question)
    return AgentQueryResponse(**result)


@app.post("/api/tickets/draft", response_model=TicketDraftResponse)
def create_ticket_draft(request: TicketDraftRequest) -> TicketDraftResponse:
    """Direct draft creation, bypassing the LLM -- same validated path the
    agent's draft_escalation_ticket tool uses under the hood."""
    with SessionLocal() as session:
        result = dispatch_draft_escalation_ticket(session, request.model_dump())
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return TicketDraftResponse(**result)


@app.post("/api/tickets/{ticket_id}/confirm", response_model=TicketDraftResponse)
def confirm_ticket(ticket_id: int) -> TicketDraftResponse:
    """The only way a draft becomes 'confirmed'. This is a separate, explicit
    human action -- nothing in the agent loop or tools.py can call this."""
    with SessionLocal() as session:
        draft = session.get(TicketDraft, ticket_id)
        if draft is None:
            raise HTTPException(status_code=404, detail=f"Nerastas juodraštis su id {ticket_id}")
        if draft.status == "confirmed":
            raise HTTPException(status_code=409, detail="Įrašas jau patvirtintas")
        draft.status = "confirmed"
        draft.confirmed_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(draft)
        return TicketDraftResponse(
            id=draft.id,
            incident_id=draft.incident_id,
            summary=draft.summary,
            proposed_priority=draft.proposed_priority,
            requested_action=draft.requested_action,
            supporting_evidence=draft.supporting_evidence,
            status=draft.status,
            created_at=draft.created_at,
            confirmed_at=draft.confirmed_at,
        )
