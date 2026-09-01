"""The explicit agent loop. No framework -- this IS the whole mechanism:

    ask the model -> model requests a tool -> Python runs the tool ->
    feed the result back -> repeat until the model answers in plain text.

Trace it by reading this file top to bottom; there is nothing hidden behind
an abstraction elsewhere.
"""

from __future__ import annotations

import json

import openai
from sqlalchemy.orm import Session

from .config import settings
from .tools import DISPATCH, TOOL_SCHEMAS

# OpenAI's Chat Completions API wants each tool wrapped as {"type": "function",
# "function": {...}}; TOOL_SCHEMAS in tools.py stays provider-neutral
# (name/description/input_schema) so only this file needs to know OpenAI's shape.
_OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": schema["name"],
            "description": schema["description"],
            "parameters": schema["input_schema"],
        },
    }
    for schema in TOOL_SCHEMAS
]

SYSTEM_PROMPT = """You are GRIDOPS AGENT, a demo assistant for a fictional utility's \
network operations team. ALL data you see is synthetic, generated for a portfolio demo \
-- you are not connected to any real utility system.

Rules you must follow exactly:
0. ALWAYS answer in Lithuanian (lietuvių kalba), regardless of what language the \
question is in, using the professional, operational Lithuanian of a utility company's \
internal ops tool: concise, action-oriented, short sentences. Never answer in English. \
Write in short plain sentences, not markdown headers or heavy bullet lists -- a couple \
of short paragraphs, or a plain list at most. Never open with "Remiantis..." or \
"Atsižvelgiant į...". Avoid bureaucratic filler such as "atsižvelgiant į", "vadovaujantis", \
"pažymėtina", or "turimų duomenų pagrindu" -- state facts directly instead. For example, \
prefer "Pirmiausia tvarkyčiau INC-1042. Incidentas paveikė 4 800 klientų ir vis dar yra \
atviras. Pagal eskalavimo procedūros 3.2 skyrių tokį incidentą reikia eskaluoti." over a \
longer, hedged version of the same sentence. Never write an English word in \
parentheses next to its Lithuanian translation (e.g. never "skubus (urgent)") -- use \
only the Lithuanian word.
1. Get every incident fact via the query_incidents tool. Never state an incident's \
region, customer count, severity, or cause from memory or inference.
2. Never invent or guess a confirmed cause. If a tool result shows confirmed_cause as \
null, say plainly and briefly that the confirmed cause is not available in the data \
(e.g. "INC-1042 patvirtinta sutrikimo priežastis duomenyse nenurodyta. Iš turimos \
informacijos jos nustatyti negalima."). Do not speculate about likely or probable \
causes under any circumstances.
3. Priority scores, labels, and reasons come ONLY from query_incidents' "priority" \
field. Never calculate or adjust a score yourself. Every time you state a score, ALWAYS \
attribute it to "demonstracinė prioritizavimo logika" (e.g. "Pagal demonstracinę \
prioritizavimo logiką šis incidentas surinko 95 taškus."). NEVER call it "įmonės veiklos \
logika", "įmonės veiklos politika", or otherwise imply it is a real operating policy -- \
that directly contradicts the disclaimer you must also state and reads as a self- \
contradiction in the same answer.
4. When you cite a procedure, use search_procedures and quote the exact document name \
and section it returns. Never invent a document name or section number.
5. draft_escalation_ticket only ever creates a DRAFT. After calling it, always state \
clearly that a human must review and confirm it before it has any effect, and that you \
cannot approve or send it yourself. Write EVERY field value you pass to this tool \
(summary, proposed_priority, requested_action, supporting_evidence) in Lithuanian too -- \
proposed_priority must be a Lithuanian word (e.g. "žemas", "vidutinis", "aukštas", \
"skubus"), never the English priority label from the tool result.
6. If information needed to answer is missing from tool results, say it's missing \
rather than filling the gap with a plausible guess.
7. MANDATORY: when asked which incidents to prioritise, escalate, or act on -- \
INCLUDING every time you call draft_escalation_ticket -- ALWAYS call search_procedures \
and your final answer text MUST literally contain the exact document title and section \
number it returned, in quotes, as one of the first two sentences -- e.g. "Pagal \
\"Tinklo sutrikimų eskalavimo procedūra\" 3.2 skyrių..." An answer about \
prioritisation/escalation/ticket drafting that does not name a document title and \
section number is INCOMPLETE and WRONG, even if you called the tool. Do not answer \
from incident data alone."""

# Deterministic backstop, not just a prompt: this system's synthetic causes are drawn
# from a small closed vocabulary (see seed.py). If a final answer mentions one of these
# for an incident whose confirmed_cause was null in the tool results, the LLM
# hallucinated -- the prompt failed -- and we override the answer in code rather than
# trust prose alone. This is what "do not rely solely on prompting" means in practice.
#
# Lithuanian stems (substrings, lowercased) catch inflected forms -- e.g. "gedim"
# matches "gedimas"/"gedimo"/"gedimu". English keywords are kept too as a bilingual
# safety net in case the model ever answers in English despite rule 0.
_CAUSE_KEYWORDS = [
    # Lithuanian
    "kabelio gedim", "augalijos sąlyt", "audros pažeidim", "audros sukelt",
    "transformatoriaus perkrov", "transformatoriaus gedim", "iškasimo pažeidim",
    "iškasimo darb", "įrangos susidėvėjim", "įrangos gedim", "relinės apsaugos gedim",
    "relės gedim", "voverės sąlyt", "gyvūno sąlyt", "tikėtina priežas", "tikėtinos priežas",
    "spėjama priežas", "spėjamos priežas", "galima priežas", "oro sąlyg", "dėl orų",
    # English (defense in depth)
    "cable fault", "vegetation contact", "storm damage", "transformer overload",
    "transformer failure", "excavation damage", "equipment aging", "equipment failure",
    "relay misoperation", "squirrel contact", "probable cause", "likely cause",
    "suspected cause", "weather-related", "due to weather",
]


def _violates_null_cause_rule(answer_text: str, null_cause_incident_ids: set[str]) -> bool:
    if not null_cause_incident_ids:
        return False
    lowered = answer_text.lower()
    return any(keyword in lowered for keyword in _CAUSE_KEYWORDS)


def run_agent(session: Session, question: str) -> dict:
    if not settings.openai_api_key:
        return {
            "answer": (
                "GRIDOPS_OPENAI_API_KEY nesukonfigūruotas, todėl agentas negali "
                "iškviesti LLM. Nustatykite jį aplinkoje ir iš naujo paleiskite backend."
            ),
            "tool_calls": [],
            "incidents": [],
            "procedures": [],
        }

    client = openai.OpenAI(api_key=settings.openai_api_key)
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    tool_call_log: list[dict] = []
    incidents_seen: list[dict] = []
    procedures_seen: list[dict] = []
    null_cause_incident_ids: set[str] = set()

    for _ in range(6):  # hard cap so a misbehaving loop can't run forever
        response = client.chat.completions.create(
            model=settings.openai_model,
            max_tokens=1500,
            tools=_OPENAI_TOOLS,
            messages=messages,
        )
        message = response.choices[0].message

        if not message.tool_calls:
            answer_text = message.content or ""
            if _violates_null_cause_rule(answer_text, null_cause_incident_ids):
                ids = ", ".join(sorted(null_cause_incident_ids))
                answer_text = (
                    f"{ids} patvirtinta sutrikimo priežastis duomenyse nenurodyta. "
                    "Iš turimos informacijos jos nustatyti negalima. "
                    "(Modelio atsakymas buvo blokuotas -- jame buvo paminėta konkreti "
                    "priežastis, kurios duomenyse nėra.)"
                )
            return {
                "answer": answer_text,
                "tool_calls": tool_call_log,
                "incidents": incidents_seen,
                "procedures": procedures_seen,
            }

        messages.append(message.model_dump(exclude_unset=True))
        for call in message.tool_calls:
            args = json.loads(call.function.arguments)
            dispatch = DISPATCH[call.function.name]
            result = dispatch(session, args)
            tool_call_log.append({"tool": call.function.name, "input": args, "output": result})

            if call.function.name == "query_incidents":
                for incident in result.get("incidents", []):
                    incidents_seen.append(incident)
                    if incident["confirmed_cause"] is None:
                        null_cause_incident_ids.add(incident["incident_id"])
            if call.function.name == "search_procedures":
                procedures_seen.extend(result.get("passages", []))

            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, default=str)}
            )

    return {
        "answer": "Agentas atliko per daug įrankių iškvietimų ir nepasiekė atsakymo. Pabandykite pateikti konkretesnį klausimą.",
        "tool_calls": tool_call_log,
        "incidents": incidents_seen,
        "procedures": procedures_seen,
    }
