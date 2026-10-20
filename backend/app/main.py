import base64
import binascii
import hmac
from pathlib import Path

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from .agent import run_agent
from .config import settings
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


if settings.require_demo_auth and not settings.demo_auth_password:
    raise RuntimeError("GRIDOPS_DEMO_AUTH_PASSWORD is required when demo auth is enabled")


class DemoBasicAuthMiddleware:
    """Protect the hosted demo and API with credentials stored in the backend environment."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not settings.require_demo_auth:
            await self.app(scope, receive, send)
            return

        if scope.get("path") == "/health":
            await self.app(scope, receive, send)
            return

        authorization = next(
            (value.decode("latin-1") for key, value in scope.get("headers", []) if key.lower() == b"authorization"),
            "",
        )
        scheme, separator, encoded = authorization.partition(" ")
        authenticated = False
        if separator and scheme.lower() == "basic":
            try:
                decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
                username, password = decoded.split(":", 1)
                expected_password = settings.demo_auth_password or ""
                authenticated = hmac.compare_digest(
                    username.encode("utf-8"), settings.demo_auth_username.encode("utf-8")
                ) and hmac.compare_digest(
                    password.encode("utf-8"), expected_password.encode("utf-8")
                )
            except (binascii.Error, UnicodeDecodeError, ValueError):
                authenticated = False

        if authenticated:
            await self.app(scope, receive, send)
            return

        response = Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="GRIDOPS private demo", charset="UTF-8"'},
        )
        await response(scope, receive, send)


app.add_middleware(DemoBasicAuthMiddleware)


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


# In production the FastAPI service also serves the Vite build. Local
# development keeps using the separate Vite dev server from docker-compose.
frontend_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if frontend_dist.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
