"""DEMO-ONLY prioritisation logic — not real utility operating policy.

One plain function. No configurable weights, no scoring framework. The LLM
never invents this number — it calls this function (via the query_incidents
tool result) and reports exactly what it returns.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

SEVERITY_POINTS = {"low": 5, "medium": 15, "high": 30, "critical": 45}


@dataclass(frozen=True)
class PriorityResult:
    score: int
    label: str  # 'low' | 'medium' | 'high' | 'urgent'
    reasons: list[str]
    missing_inputs: list[str]
    disclaimer: str = "DEMO-ONLY prioritisation logic — not real utility operating policy."


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
            reasons=["Planned work is not prioritised against unplanned incidents."],
            missing_inputs=[],
        )

    if affected_customers is None:
        missing_inputs.append("affected_customers")
    else:
        customer_points = min(affected_customers // 100, 40)
        score += customer_points
        reasons.append(f"{affected_customers} affected customers (+{customer_points} pts)")

    if severity is None:
        missing_inputs.append("severity")
    else:
        severity_points = SEVERITY_POINTS.get(severity, 0)
        score += severity_points
        reasons.append(f"severity={severity} (+{severity_points} pts)")

    if started_at is None:
        missing_inputs.append("started_at")
    elif status == "open":
        elapsed_hours = (datetime.now(timezone.utc) - started_at).total_seconds() / 3600
        duration_points = min(int(elapsed_hours // 2), 20)
        score += duration_points
        reasons.append(f"open for {elapsed_hours:.1f}h (+{duration_points} pts)")

    if score >= 70:
        label = "urgent"
    elif score >= 45:
        label = "high"
    elif score >= 20:
        label = "medium"
    else:
        label = "low"

    return PriorityResult(score=score, label=label, reasons=reasons, missing_inputs=missing_inputs)
