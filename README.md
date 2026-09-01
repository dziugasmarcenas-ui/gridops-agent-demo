# GRIDOPS AGENT

A compact applied-AI demo: structured operational data + unstructured
procedure documents + LLM tool use + provenance/citations + explicit missing-
information handling + a write action that requires human approval.

**Everything here is synthetic.** No real utility data, systems, or
procedures are used or implied.

Built as a portfolio piece, not a product — see [`docs/DEMO_CHECKS.md`](docs/DEMO_CHECKS.md)
for hand-checked correctness/safety cases.

## What it proves

| Requirement | Where |
|---|---|
| Structured data in PostgreSQL | `incidents` table, 39 synthetic rows |
| RAG over unstructured docs | 3 synthetic procedure markdown files → heading-aware chunks → pgvector |
| LLM tool use | explicit loop in `backend/app/agent.py`, 3 typed tools |
| Provenance/citations | every retrieved passage carries document + section + exact text |
| Missing-information handling | `INC-1042` has `confirmed_cause = NULL`; agent must say "not available" — enforced by a deterministic code-level guard, not just a prompt |
| Human approval before a write action | tickets start as `draft`; only a separate, explicit `POST /api/tickets/{id}/confirm` call moves them to `confirmed` — nothing in the agent can call that itself |

## Quickstart

Requires Docker Desktop running and an [Anthropic API key](https://console.anthropic.com/).

```bash
cd gridops-agent-demo
echo "GRIDOPS_ANTHROPIC_API_KEY=sk-ant-..." > .env
docker compose up -d --build
docker compose exec backend python -m app.seed              # incidents
docker compose exec backend python -m app.ingest_procedures  # procedure chunks
```

Open http://localhost:5173.

Embeddings work with zero extra configuration (a local deterministic hash
provider). For real semantic search, also set `GRIDOPS_VOYAGE_API_KEY` in
`.env` and re-run `ingest_procedures`.

## 2-minute demo script

Click the three buttons at the top of the page in order:

1. **"Flow A: Prioritise this morning"** — the agent queries all open
   incidents, calculates a transparent DEMO-ONLY priority score for each
   (visible with its reasons in the left panel), retrieves the relevant
   escalation procedure, and explains its recommendation. Point out the
   right panel: exact tool calls, exact database facts, exact procedure
   citation with document + section.

2. **"Flow B: Draft escalation for INC-1042"** — the agent fetches the
   incident, cites the ticket-quality/escalation procedures, and creates a
   ticket. Point out the red **DRAFT — HUMAN APPROVAL REQUIRED** banner and
   click **Confirm ticket** — that's the only thing that can move it to
   `CONFIRMED`. The agent explicitly says it cannot do this itself.

3. **"Flow C: What caused INC-1042?"** — the agent says the confirmed cause
   is not available in the data. It does not guess a cause. This is the one
   flow that must never hallucinate; a code-level check
   (`backend/app/agent.py::_violates_null_cause_rule`) blocks the answer if
   it ever tries.

## Architecture — trace it yourself

```
browser (React) → FastAPI (main.py) → agent loop (agent.py)
  → tool dispatch (tools.py) → Postgres (incidents_repo.py) or
                                pgvector search (retrieval.py)
  → tool result fed back to the LLM (Anthropic API)
  → final answer + full evidence trail → browser
```

- **Why the LLM can't run arbitrary SQL:** it only ever supplies validated
  parameters (`incident_id`, `status`, `region`, `limit`) to
  `query_incidents`; `incidents_repo.py` is the only place that builds a
  SQLAlchemy query, and it's plain Python, not a string the model writes.
- **Why an unknown cause stays unknown:** `confirmed_cause` is `NULL` in the
  database for some incidents (by design — see `seed.py`); the tool returns
  it as JSON `null`, the system prompt says never to guess one, and a
  deterministic keyword check on the final answer (independent of the LLM)
  overrides the answer if it names a cause anyway.
- **Why ticket submission needs a human:** `draft_escalation_ticket` only
  ever inserts a row with `status="draft"`. The only code path that sets
  `status="confirmed"` is the `POST /api/tickets/{id}/confirm` endpoint,
  which nothing in `agent.py` or `tools.py` calls.

## Stack

FastAPI · SQLAlchemy · PostgreSQL + pgvector · Anthropic Claude (tool use) ·
Voyage embeddings (optional; deterministic local fallback by default) ·
React + Vite + TypeScript · Docker Compose.

No Alembic (schema is created once via `Base.metadata.create_all` — simpler
to trace than migrations for a fixed, one-shot schema). No LangChain/agent
framework — the tool loop in `agent.py` is ~100 lines of plain Python,
readable top to bottom.

## Known limitations

- Embeddings default to a local deterministic hash, not real semantic
  similarity, unless `GRIDOPS_VOYAGE_API_KEY` is set — fine for this corpus
  (10 chunks) but not a real retrieval benchmark.
- No auth, no multi-user support, no persistence beyond the Docker volume —
  intentionally out of scope (see the original spec's hard exclusions).
- `docs/DEMO_CHECKS.md` is hand-checked, not an automated eval suite, except
  where noted (the null-cause guard has a real pytest).
