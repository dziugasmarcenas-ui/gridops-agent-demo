#!/bin/sh
set -eu

# Ingestion creates the pgvector extension before SQLAlchemy creates tables
# that contain vector columns. Both commands are safe to rerun for this
# synthetic, single-instance demo.
python -m app.ingest_procedures
python -m app.seed

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-10000}"
