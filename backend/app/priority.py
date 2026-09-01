"""DEMO-ONLY prioritisation logic — not real utility operating policy.

One plain function. No configurable weights, no scoring framework. The LLM
never invents this number — it calls this function (via the query_incidents
tool result) and reports exactly what it returns.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

SEVERITY_POINTS = {"low": 5, "medium": 15, "high": 30, "critical": 45}

# Display-only Lithuanian labels for the English severity enum stored in the
# database -- the enum value itself (low/medium/high/critical) is untouched,
# this is purely for building readable reason sentences.
SEVERITY_LABELS_LT = {"low": "žemas", "medium": "vidutinis", "high": "aukštas", "critical": "kritinis"}

DISCLAIMER_LT = "DEMONSTRACINĖ prioritizavimo logika — tai nėra reali energetikos įmonės veiklos politika."


@dataclass(frozen=True)
class PriorityResult:
    score: int
    label: str  # 'low' | 'medium' | 'high' | 'urgent'
    reasons: list[str]
    missing_inputs: list[str]
    disclaimer: str = DISCLAIMER_LT


def calculate_priority(
    *,
    affected_customers: int | None,
    started_at: datetime | None,
    severity: str | None,
    status: str,
    planned: bool,
) -> PriorityResult:
    missing_inputs = []
    reasons = []
    score = 0

    if planned:
        return PriorityResult(
            score=0,
            label="low",
            reasons=["Planuoti darbai neprioritetizuojami kartu su neplanuotais incidentais."],
            missing_inputs=[],
        )

    if affected_customers is None:
        missing_inputs.append("affected_customers")
    else:
        customer_points = min(affected_customers // 100, 40)
        score += customer_points
        reasons.append(f"{affected_customers} paveiktų klientų (+{customer_points} tšk.)")

    if severity is None:
        missing_inputs.append("severity")
    else:
        severity_points = SEVERITY_POINTS.get(severity, 0)
        score += severity_points
        severity_lt = SEVERITY_LABELS_LT.get(severity, severity)
        reasons.append(f"svarbumas: {severity_lt} (+{severity_points} tšk.)")

    if started_at is None:
        missing_inputs.append("started_at")
    elif status == "open":
        elapsed_hours = (datetime.now(timezone.utc) - started_at).total_seconds() / 3600
        duration_points = min(int(elapsed_hours // 2), 20)
        score += duration_points
        reasons.append(f"atviras {elapsed_hours:.1f} val. (+{duration_points} tšk.)")

    if score >= 70:
        label = "urgent"
    elif score >= 45:
        label = "high"
    elif score >= 20:
        label = "medium"
    else:
        label = "low"

    return PriorityResult(score=score, label=label, reasons=reasons, missing_inputs=missing_inputs)
