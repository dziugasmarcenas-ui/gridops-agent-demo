"""The deterministic checks that must hold regardless of what the LLM says.

These don't call a real LLM -- they test the code-level backstops directly,
which is the whole point: correctness here must not depend on the model
behaving.
"""

from app.agent import _violates_null_cause_rule
from app.priority import calculate_priority
from app.seed import INCIDENTS


def test_inc_1042_has_no_confirmed_cause_in_seed_data() -> None:
    row = next(r for r in INCIDENTS if r[0] == "INC-1042")
    confirmed_cause = row[8]
    assert confirmed_cause is None


def test_null_cause_guard_blocks_a_fabricated_cause() -> None:
    hallucinated_answer = "The incident was likely caused by a transformer overload."
    assert _violates_null_cause_rule(hallucinated_answer, {"INC-1042"})


def test_null_cause_guard_allows_a_correct_unknown_answer() -> None:
    honest_answer = "The confirmed cause for INC-1042 is not available in the data."
    assert not _violates_null_cause_rule(honest_answer, {"INC-1042"})


def test_null_cause_guard_is_a_no_op_when_no_incident_has_a_null_cause() -> None:
    # Even if the text happens to contain a cause keyword, there's nothing to
    # guard against if no fetched incident actually had a null cause.
    text_mentioning_a_cause = "INC-1010 was caused by third-party excavation damage."
    assert not _violates_null_cause_rule(text_mentioning_a_cause, set())


def test_null_cause_guard_blocks_a_fabricated_cause_in_lithuanian() -> None:
    hallucinated_answer = "Incidentą greičiausiai sukėlė transformatoriaus gedimas."
    assert _violates_null_cause_rule(hallucinated_answer, {"INC-1042"})


def test_null_cause_guard_allows_a_correct_unknown_answer_in_lithuanian() -> None:
    honest_answer = (
        "Turimuose incidento duomenyse patvirtinta INC-1042 priežastis nenurodyta. "
        "Negaliu pagrįstai nustatyti priežasties iš turimos informacijos."
    )
    assert not _violates_null_cause_rule(honest_answer, {"INC-1042"})


def test_priority_never_invents_missing_inputs() -> None:
    result = calculate_priority(
        affected_customers=None,
        started_at=None,
        severity=None,
        status="open",
        planned=False,
    )
    assert set(result.missing_inputs) == {"affected_customers", "severity", "started_at"}
    assert result.score == 0


def test_priority_flags_planned_work_as_low_without_scoring() -> None:
    from datetime import datetime, timezone

    result = calculate_priority(
        affected_customers=10_000,
        started_at=datetime.now(timezone.utc),
        severity="critical",
        status="open",
        planned=True,
    )
    assert result.label == "low"
    assert result.score == 0
