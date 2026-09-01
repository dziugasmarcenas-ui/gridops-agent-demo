import { useState } from "react";

const API_BASE = "http://localhost:8000";

// Presentation-layer translations only -- the underlying English enum
// values (open/resolved, low/medium/high/critical, etc.) stay as-is in the
// database and API so nothing downstream has to change for localization.
const STATUS_LABELS: Record<string, string> = { open: "Atviras", resolved: "Išspręstas" };
const SEVERITY_LABELS: Record<string, string> = {
  low: "Žemas",
  medium: "Vidutinis",
  high: "Aukštas",
  critical: "Kritinis",
};
const PRIORITY_LABELS: Record<string, string> = {
  low: "Žemas",
  medium: "Vidutinis",
  high: "Aukštas",
  urgent: "Skubus",
};
const TOOL_LABELS: Record<string, string> = {
  query_incidents: "Incidentų paieška",
  search_procedures: "Procedūrų paieška",
  draft_escalation_ticket: "Eskalavimo juodraščio parengimas",
};
const MISSING_INPUT_LABELS: Record<string, string> = {
  affected_customers: "paveiktų klientų skaičius",
  severity: "svarbumas",
  started_at: "pradžios laikas",
};

function translateTool(tool: string): string {
  return TOOL_LABELS[tool] ?? tool;
}

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
  started_at: string;
  last_update: string;
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
  {
    label: "A: Prioritetai šį rytą",
    question: "Kuriuos atvirus incidentus reikėtų tvarkyti pirmiausia?",
  },
  {
    label: "B: Eskalavimo juodraštis INC-1042",
    question: "Parengti INC-1042 eskalavimą",
  },
  {
    label: "C: Kas sukėlė INC-1042?",
    question: "Kokia patvirtinta INC-1042 sutrikimo priežastis?",
  },
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
      if (!response.ok) throw new Error(`Užklausa nepavyko: ${response.status}`);
      setResult(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Užklausa nepavyko");
    } finally {
      setLoading(false);
    }
  }

  async function confirmTicket(ticketId: number) {
    setConfirming(ticketId);
    try {
      const response = await fetch(`${API_BASE}/api/tickets/${ticketId}/confirm`, { method: "POST" });
      if (!response.ok) throw new Error(`Patvirtinimas nepavyko: ${response.status}`);
      setConfirmedTicketIds((prev) => new Set(prev).add(ticketId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Patvirtinimas nepavyko");
    } finally {
      setConfirming(null);
    }
  }

  const ticketDrafts: TicketDraft[] = (result?.tool_calls ?? [])
    .filter((call) => call.tool === "draft_escalation_ticket" && "id" in call.output)
    .map((call) => call.output as unknown as TicketDraft);

  return (
    <main className="layout">
      <p className="eyebrow">Sintetinis tinklų operacijų demonstracinis projektas — jokių realių duomenų, jokių realių sistemų</p>
      <h1>GridOps Agent</h1>
      <p className="subtitle">Incidentų analizė ir eskalavimas</p>

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
              placeholder="Klausk apie incidentus, pvz. 'Kokia yra patvirtinta INC-1042 priežastis?'"
              rows={3}
            />
            <button type="submit" disabled={loading || !question.trim()}>
              {loading ? "Analizuojama…" : "Klausk apie incidentus"}
            </button>
          </form>

          {error && <p className="error">{error}</p>}

          {result && (
            <div className="answer-block">
              <h2>Atsakymas</h2>
              <p className="answer-text">{result.answer}</p>
            </div>
          )}

          {result && result.incidents.length > 0 && (
            <div className="priority-block">
              <h2>Prioritetas</h2>
              {[...result.incidents]
                .sort((a, b) => b.priority.score - a.priority.score)
                .map((incident) => (
                <div key={incident.incident_id} className="priority-card">
                  <div className="priority-card-header">
                    <strong>{incident.incident_id}</strong>
                    <span className={`badge badge--${incident.priority.label}`}>
                      {PRIORITY_LABELS[incident.priority.label] ?? incident.priority.label}
                    </span>
                    <span className="score">Prioriteto balas: {incident.priority.score}</span>
                  </div>
                  <p className="reasons-label">Kodėl:</p>
                  <ul>
                    {incident.priority.reasons.map((reason, i) => (
                      <li key={i}>{reason}</li>
                    ))}
                  </ul>
                  {incident.priority.missing_inputs.length > 0 && (
                    <p className="missing">
                      Ko trūksta:{" "}
                      {incident.priority.missing_inputs
                        .map((field) => MISSING_INPUT_LABELS[field] ?? field)
                        .join(", ")}
                    </p>
                  )}
                  <p className="disclaimer">{incident.priority.disclaimer}</p>
                </div>
              ))}
            </div>
          )}

          {ticketDrafts.map((ticket) => (
            <div key={ticket.id} className="ticket-card">
              <h3 className="ticket-title">Eskalavimo juodraštis</h3>
              <p className="ticket-flag">
                {confirmedTicketIds.has(ticket.id) ? "PATVIRTINTA" : "JUODRAŠTIS — LAUKIA PATVIRTINIMO"}
              </p>
              <dl>
                <dt>Incidento ID</dt>
                <dd>{ticket.incident_id}</dd>
                <dt>Santrauka</dt>
                <dd>{ticket.summary}</dd>
                <dt>Siūlomas prioritetas</dt>
                <dd>{ticket.proposed_priority}</dd>
                <dt>Siūlomas veiksmas</dt>
                <dd>{ticket.requested_action}</dd>
                <dt>Pagrindžiantys šaltiniai</dt>
                <dd>{ticket.supporting_evidence}</dd>
              </dl>
              {!confirmedTicketIds.has(ticket.id) && (
                <button onClick={() => confirmTicket(ticket.id)} disabled={confirming === ticket.id}>
                  {confirming === ticket.id ? "Patvirtinama…" : "Patvirtinti"}
                </button>
              )}
            </div>
          ))}
        </section>

        <aside className="col-side">
          {result && (
            <>
              <div className="side-block">
                <h3>Atlikti veiksmai</h3>
                {result.tool_calls.length === 0 && <p className="empty">Nėra</p>}
                <ul>
                  {result.tool_calls.map((call, i) => (
                    <li key={i}>
                      <span className="tool-name">{translateTool(call.tool)}</span>
                      <code className="tool-fn">{call.tool}</code>
                      <pre>{JSON.stringify(call.input)}</pre>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="side-block">
                <h3>Incidento duomenys</h3>
                {result.incidents.length === 0 && <p className="empty">Nerasta</p>}
                {result.incidents.map((incident) => (
                  <table key={incident.incident_id} className="fact-table">
                    <tbody>
                      <tr><th colSpan={2}>{incident.incident_id}</th></tr>
                      <tr><td>Regionas</td><td>{incident.region}</td></tr>
                      <tr><td>Būsena</td><td>{STATUS_LABELS[incident.status] ?? incident.status}</td></tr>
                      <tr><td>Svarbumas</td><td>{SEVERITY_LABELS[incident.severity] ?? incident.severity}</td></tr>
                      <tr><td>Paveiktų klientų skaičius</td><td>{incident.affected_customers}</td></tr>
                      <tr><td>Planuotas</td><td>{incident.planned ? "taip" : "ne"}</td></tr>
                      <tr><td>Prasidėjo</td><td>{new Date(incident.started_at).toLocaleString("lt-LT")}</td></tr>
                      <tr><td>Paskutinis atnaujinimas</td><td>{new Date(incident.last_update).toLocaleString("lt-LT")}</td></tr>
                      <tr>
                        <td>Patvirtinta priežastis</td>
                        <td className={incident.confirmed_cause ? "" : "unknown"}>
                          {incident.confirmed_cause ?? "Nenurodyta"}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                ))}
              </div>

              <div className="side-block">
                <h3>Šaltiniai</h3>
                {result.procedures.length === 0 && <p className="empty">Nerasta</p>}
                {result.procedures.map((p, i) => (
                  <div key={i} className="evidence-card">
                    <p className="evidence-source">
                      Procedūra: {p.document} · Skyrius: {p.section} (v{p.version})
                    </p>
                    <p className="evidence-text">{p.text}</p>
                  </div>
                ))}
              </div>
            </>
          )}
        </aside>
      </div>

      <footer className="footer-disclaimer">
        Visi šiame demo naudojami incidentų duomenys ir procedūros yra sintetiniai. Sistema
        neturi prieigos prie „Ignitis" vidinių duomenų ar sistemų.
      </footer>
    </main>
  );
}
