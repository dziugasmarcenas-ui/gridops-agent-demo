"""Chunks the three synthetic procedure markdown files and embeds them.

Run manually, same pattern as seed.py:

    docker compose exec backend python -m app.ingest_procedures

Chunking is heading-aware: every "## N.N Title" line starts a new chunk, and
everything until the next "## " heading (or end of file) is that chunk's
exact text. This keeps citations trustworthy -- what's retrieved is exactly
what's in the source file, not a paraphrase or an arbitrary character split.
"""

from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import delete, text

from .db import SessionLocal, engine
from .embeddings import get_embedding_provider
from .models import Base, ProcedureChunk

PROCEDURES_DIR = Path(__file__).parent / "data" / "procedures"

_SECTION_HEADING = re.compile(r"^## (.+)$", re.MULTILINE)
_VERSION_COMMENT = re.compile(r"<!--\s*version:\s*([^\s]+)\s*-->")


def parse_document(markdown_text: str) -> tuple[str, list[tuple[str, str]]]:
    """Returns (version, [(section_heading, section_body_text), ...])."""
    version_match = _VERSION_COMMENT.search(markdown_text)
    version = version_match.group(1) if version_match else "1.0"

    headings = list(_SECTION_HEADING.finditer(markdown_text))
    chunks: list[tuple[str, str]] = []
    for i, match in enumerate(headings):
        section = match.group(1).strip()
        start = match.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(markdown_text)
        body = markdown_text[start:end].strip()
        chunks.append((section, body))
    return version, chunks


def ingest() -> None:
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(engine)

    provider = get_embedding_provider()

    with SessionLocal() as session:
        # Re-ingesting always replaces prior chunks -- procedure text is
        # small and versioned by file, so "delete and re-insert" is simpler
        # and safer than diffing.
        session.execute(delete(ProcedureChunk))

        documents: list[tuple[str, str, str]] = []  # (document_name, section, text)
        doc_versions: dict[str, str] = {}
        for path in sorted(PROCEDURES_DIR.glob("*.md")):
            document_name = path.stem
            version, chunks = parse_document(path.read_text())
            doc_versions[document_name] = version
            for section, body in chunks:
                documents.append((document_name, section, body))

        texts = [body for _, _, body in documents]
        vectors = provider.embed_passages(texts) if texts else []

        for (document_name, section, body), vector in zip(documents, vectors, strict=True):
            session.add(
                ProcedureChunk(
                    document=document_name,
                    section=section,
                    text=body,
                    version=doc_versions[document_name],
                    synthetic_source=True,
                    embedding=vector,
                )
            )
        session.commit()
        print(f"ingest complete: chunks={len(documents)} documents={len(doc_versions)}")


if __name__ == "__main__":
    ingest()
