"""Minimal SQLAlchemy type for a pgvector column.

Adapted from SENTRY (../ChatGPT/SENTRY/sentry/vector.py) — copied because it
is small, generic, and has zero dependency on any embedding provider's SDK.
Postgres just needs the pgvector extension; this class only teaches
SQLAlchemy how to read/write that column type as a plain Python list.
"""

from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kw):
        return "vector"

    def bind_processor(self, dialect):
        def process(value):
            if value is None or isinstance(value, str):
                return value
            return "[" + ",".join(str(item) for item in value) + "]"

        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            if value is None or not isinstance(value, str):
                return value
            return [float(item) for item in value.strip("[]").split(",")] if value.strip("[]") else []

        return process
