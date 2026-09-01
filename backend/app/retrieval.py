"""search_procedures: embeds the query, does a plain pgvector nearest-neighbor
search, and returns exact stored rows.

No reranking subsystem. SENTRY's retrieval.py implements hybrid full-text +
vector fusion with a pluggable reranker protocol (~1000 lines) -- that is
explicitly more than this demo needs or should copy. This is the "simple,
stable" version: one embedding call, one SQL query, done.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from .embeddings import get_embedding_provider
from .models import ProcedureChunk


@dataclass(frozen=True)
class ProcedurePassage:
    document: str
    section: str
    text: str
    version: str
    synthetic_source: bool


def search_procedures(session: Session, query: str, *, top_k: int = 3) -> list[ProcedurePassage]:
    provider = get_embedding_provider()
    query_vector = provider.embed_query(query)

    # pgvector's <-> operator is Euclidean distance on the stored vectors;
    # ORDER BY it ascending gives nearest-first without a separate rerank step.
    rows = session.scalars(
        select(ProcedureChunk).order_by(ProcedureChunk.embedding.op("<->")(str(query_vector))).limit(top_k)
    ).all()

    return [
        ProcedurePassage(
            document=row.document,
            section=row.section,
            text=row.text,
            version=row.version,
            synthetic_source=row.synthetic_source,
        )
        for row in rows
    ]
