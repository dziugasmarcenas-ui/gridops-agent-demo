from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import settings

# One engine per process; SQLAlchemy pools connections internally.
engine = create_engine(settings.database_url, pool_pre_ping=True)

# expire_on_commit=False so objects stay readable after a commit, which is
# convenient for the simple "insert, then read it back" scripts in this demo.
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
