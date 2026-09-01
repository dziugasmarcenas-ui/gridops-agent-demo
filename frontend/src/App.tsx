import { useState } from "react";

const API_BASE = "http://localhost:8000";

type Priority = {
  score: number;
  label: string;
  reasons: string[];
  missing_inputs: string[];
  disclaimer: string;
};

type Incident = {
  incident_id: string;
  region: string;
  status: string;
  severity: string;
  affected_customers: number;
  confirmed_cause: string | null;
  planned: boolean;
  priority: Priority;
};

type Procedure = {
  document: string;
  section: string;
  text: string;
  version: string;
  synthetic_source: boolean;
};

type ToolCall = {
  tool: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
};

type AgentResponse = {
  answer: string;
  tool_calls: ToolCall[];
  incidents: Incident[];
  procedures: Procedure[];
};

type TicketDraft = {
  id: number;
  incident_id: string;
  summary: string;
  proposed_priority: string;
  requested_action: string;
  supporting_evidence: string;
  status: string;
};

const DEMO_QUESTIONS = [
  { label: "Flow A: Prioritise this morning", question: "Which open network incidents should we prioritise this morning, and why?" },
  { label: "Flow B: Draft escalation for INC-1042", question: "Draft an escalation ticket for INC-1042." },
  { label: "Flow C: What caused INC-1042?", question: "What caused INC-1042?" },
];

export function App() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmedTicketIds, setConfirmedTicketIds] = useState<Set<number>>(new Set());
  const [confirming, setConfirming] = useState<number | null>(null);

  async function ask(q: string) {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await fetch(`${API_BASE}/api/agent/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      if (!response.ok) throw new Error(`Request failed: ${response.status}`);
      setResult(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  async function confirmTicket(ticketId: number) {
    setConfirming(ticketId);
    try {
      const response = await fetch(`${API_BASE}/api/tickets/${ticketId}/confirm`, { method: "POST" });
      if (!response.ok) throw new Error(`Confirm failed: ${response.status}`);
      setConfirmedTicketIds((prev) => new Set(prev).add(ticketId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Confirm failed");
    } finally {
      setConfirming(null);
    }
  }

  const ticketDrafts: TicketDraft[] = (result?.tool_calls ?? [])
    .filter((call) => call.tool === "draft_escalation_ticket" && "id" in call.output)
    .map((call) => call.output as unknown as TicketDraft);

  return (
    <main className="layout">
      <p className="eyebrow">Synthetic utility operations demo — no real data, no real systems</p>
      <h1>GRIDOPS AGENT</h1>

      <div className="demo-buttons">
        {DEMO_QUESTIONS.map((demo) => (
          <button key={demo.label} onClick={() => { setQuestion(demo.question); ask(demo.question); }} disabled={loading}>
            {demo.label}
          </button>
        ))}
      </div>

      <div className="columns">
        <section className="col-main">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (question.trim()) ask(question.trim());
            }}
          >
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask about incidents, e.g. 'What caused INC-1042?'"
              rows={3}
            />
            <button type="submit" disabled={loading || !question.trim()}>
              {loading ? "Thinking…" : "Ask"}
            </button>
          </form>

          {error && <p className="error">{error}</p>}

          {result && (
            <div className="answer-block">
              <h2>Answer</h2>
              <p className="answer-text">{result.answer}</p>
            </div>
          )}

          {result && result.incidents.length > 0 && (
            <div className="priority-block">
              <h2>Priority (demo-only logic)</h2>
              {result.incidents.map((incident) => (
                <div key={incident.incident_id} className="priority-card">
                  <div className="priority-card-header">
                    <strong>{incident.incident_id}</strong>
                    <span className={`badge badge--${incident.priority.label}`}>{incident.priority.label}</span>
                    <span className="score">score {incident.priority.score}</span>
                  </div>
                  <ul>
                    {incident.priority.reasons.map((reason, i) => (
                      <li key={i}>{reason}</li>
                    ))}
                  </ul>
                  {incident.priority.missing_inputs.length > 0 && (
                    <p className="missing">Missing inputs: {incident.priority.missing_inputs.join(", ")}</p>
                  )}
                  <p className="disclaimer">{incident.priority.disclaimer}</p>
                </div>
              ))}
            </div>
          )}

          {ticketDrafts.map((ticket) => (
            <div key={ticket.id} className="ticket-card">
              <p className="ticket-flag">
                {confirmedTicketIds.has(ticket.id) ? "CONFIRMED" : "DRAFT — HUMAN APPROVAL REQUIRED"}
              </p>
              <dl>
                <dt>Incident</dt>
                <dd>{ticket.incident_id}</dd>
                <dt>Summary</dt>
                <dd>{ticket.summary}</dd>
                <dt>Proposed priority</dt>
                <dd>{ticket.proposed_priority}</dd>
                <dt>Requested action</dt>
                <dd>{ticket.requested_action}</dd>
                <dt>Supporting evidence</dt>
                <dd>{ticket.supporting_evidence}</dd>
              </dl>
              {!confirmedTicketIds.has(ticket.id) && (
                <button onClick={() => confirmTicket(ticket.id)} disabled={confirming === ticket.id}>
                  {confirming === ticket.id ? "Confirming…" : "Confirm ticket (human action)"}
                </button>
              )}
            </div>
          ))}
        </section>

        <aside className="col-side">
          {result && (
            <>
              <div className="side-block">
                <h3>Tools used</h3>
                {result.tool_calls.length === 0 && <p className="empty">None</p>}
                <ul>
                  {result.tool_calls.map((call, i) => (
                    <li key={i}>
                      <code>{call.tool}</code>
                      <pre>{JSON.stringify(call.input)}</pre>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="side-block">
                <h3>Structured incident facts</h3>
                {result.incidents.length === 0 && <p className="empty">None retrieved</p>}
                {result.incidents.map((incident) => (
                  <table key={incident.incident_id} className="fact-table">
                    <tbody>
                      <tr><th colSpan={2}>{incident.incident_id}</th></tr>
                      <tr><td>Region</td><td>{incident.region}</td></tr>
                      <tr><td>Status</td><td>{incident.status}</td></tr>
                      <tr><td>Severity</td><td>{incident.severity}</td></tr>
                      <tr><td>Affected customers</td><td>{incident.affected_customers}</td></tr>
                      <tr><td>Planned</td><td>{incident.planned ? "yes" : "no"}</td></tr>
                      <tr>
                        <td>Confirmed cause</td>
                        <td className={incident.confirmed_cause ? "" : "unknown"}>
                          {incident.confirmed_cause ?? "not available in data"}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                ))}
              </div>

              <div className="side-block">
                <h3>Retrieved procedure evidence</h3>
                {result.procedures.length === 0 && <p className="empty">None retrieved</p>}
                {result.procedures.map((p, i) => (
                  <div key={i} className="evidence-card">
                    <p className="evidence-source">
                      {p.document} — {p.section} (v{p.version})
                    </p>
                    <p className="evidence-text">{p.text}</p>
                  </div>
                ))}
              </div>
            </>
          )}
        </aside>
      </div>
    </main>
  );
}
