"""Creates the incidents table and inserts synthetic demo data.

Run manually (not on every app boot) so the demo owner can see exactly when
and how the database gets populated:

    docker compose exec backend python -m app.seed

Safe to re-run: it skips rows whose incident_id already exists.

ALL DATA HERE IS SYNTHETIC. Timestamps are relative to "now" (hours ago) so
the demo always looks like "this morning's incidents" whenever it's run --
the incident content itself (region, causes, customer counts) is a fixed,
hand-written table below, not randomly generated.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from .db import SessionLocal, engine
from .models import Base, Incident

# (incident_id, region, hours_ago_started, duration_hours_if_resolved,
#  status, affected_customers, severity, planned, confirmed_cause)
#
# duration_hours_if_resolved is None for open incidents (resolved_at stays
# NULL regardless of what's written there for open rows).
INCIDENTS: list[tuple] = [
    ("INC-1000", "Vilnius", 2, None, "open", 6400, "critical", False, None),
    ("INC-1001", "Kaunas", 5, None, "open", 850, "medium", False, None),
    ("INC-1002", "Klaipeda", 1, None, "open", 120, "low", False, None),
    ("INC-1003", "Siauliai", 30, 4, "resolved", 300, "medium", False, "Underground cable fault"),
    ("INC-1004", "Panevezys", 48, 2, "resolved", 90, "low", False, "Vegetation contact with overhead line"),
    ("INC-1005", "Vilnius", 12, None, "open", 3100, "high", False, None),
    ("INC-1006", "Alytus", 72, 6, "resolved", 1800, "high", False, "Storm damage to overhead line"),
    ("INC-1007", "Marijampole", 96, 1, "resolved", 45, "low", True, None),
    ("INC-1008", "Utena", 3, None, "open", 2200, "high", False, None),
    ("INC-1009", "Kaunas", 150, 3, "resolved", 610, "medium", False, "Transformer overload"),
    ("INC-1010", "Vilnius", 200, 8, "resolved", 4300, "critical", False, "Third-party excavation damage"),
    ("INC-1011", "Klaipeda", 10, None, "open", 40, "low", True, None),
    ("INC-1012", "Siauliai", 220, 2, "resolved", 150, "low", False, "Equipment aging failure"),
    ("INC-1013", "Panevezys", 6, None, "open", 980, "medium", False, None),
    ("INC-1014", "Alytus", 300, 5, "resolved", 720, "medium", False, "Protection relay misoperation"),
    ("INC-1015", "Vilnius", 400, 12, "resolved", 9200, "critical", False, "Storm damage to overhead line"),
    ("INC-1016", "Marijampole", 8, None, "open", 60, "low", False, None),
    ("INC-1017", "Utena", 260, 3, "resolved", 340, "medium", False, None),
    ("INC-1018", "Kaunas", 15, None, "open", 1500, "high", False, None),
    ("INC-1019", "Klaipeda", 330, 1, "resolved", 25, "low", True, None),
    ("INC-1020", "Vilnius", 4, None, "open", 210, "low", False, None),
    ("INC-1021", "Siauliai", 500, 4, "resolved", 480, "medium", False, "Underground cable fault"),
    ("INC-1022", "Panevezys", 18, None, "open", 5100, "critical", False, None),
    ("INC-1023", "Alytus", 600, 2, "resolved", 95, "low", False, "Squirrel contact with equipment"),
    ("INC-1024", "Vilnius", 700, 10, "resolved", 6800, "critical", False, "Transformer overload"),
    ("INC-1025", "Marijampole", 20, None, "open", 380, "medium", True, None),
    ("INC-1026", "Utena", 800, 3, "resolved", 210, "low", False, "Equipment aging failure"),
    ("INC-1027", "Kaunas", 24, None, "open", 70, "low", False, None),
    ("INC-1028", "Klaipeda", 900, 6, "resolved", 1450, "high", False, "Storm damage to overhead line"),
    ("INC-1029", "Vilnius", 36, None, "open", 2600, "high", False, None),
    ("INC-1030", "Siauliai", 1000, 2, "resolved", 130, "low", False, None),
    ("INC-1031", "Panevezys", 40, None, "open", 45, "low", True, None),
    ("INC-1032", "Alytus", 1100, 5, "resolved", 890, "medium", False, "Third-party excavation damage"),
    ("INC-1033", "Vilnius", 44, None, "open", 7200, "critical", False, None),
    ("INC-1034", "Marijampole", 1200, 1, "resolved", 55, "low", False, "Vegetation contact with overhead line"),
    ("INC-1035", "Utena", 50, None, "open", 320, "medium", False, None),
    ("INC-1036", "Kaunas", 1300, 7, "resolved", 2900, "high", False, "Protection relay misoperation"),
    ("INC-1037", "Klaipeda", 60, None, "open", 90, "low", False, None),
    # Demo incident: open, high impact, cause genuinely not yet confirmed.
    # Do NOT give this one a confirmed_cause anywhere -- it is the fixture
    # for the "missing information" refusal flow (Flow C).
    ("INC-1042", "Vilnius", 7, None, "open", 4800, "high", False, None),
]


def seed() -> None:
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)

    with SessionLocal() as session:
        existing_ids = set(session.scalars(select(Incident.incident_id)))
        inserted = 0
        for (
            incident_id,
            region,
            hours_ago_started,
            duration_hours,
            status,
            affected_customers,
            severity,
            planned,
            confirmed_cause,
        ) in INCIDENTS:
            if incident_id in existing_ids:
                continue
            started_at = now - timedelta(hours=hours_ago_started)
            resolved_at = (
                started_at + timedelta(hours=duration_hours)
                if status == "resolved" and duration_hours is not None
                else None
            )
            last_update = resolved_at or now
            session.add(
                Incident(
                    incident_id=incident_id,
                    region=region,
                    started_at=started_at,
                    resolved_at=resolved_at,
                    status=status,
                    affected_customers=affected_customers,
                    severity=severity,
                    planned=planned,
                    confirmed_cause=confirmed_cause,
                    last_update=last_update,
                )
            )
            inserted += 1
        session.commit()
        print(f"seed complete: inserted={inserted} skipped_existing={len(existing_ids)}")


if __name__ == "__main__":
    seed()
