import os
import shutil
import sqlite3
import pytest

# Force DATABASE_URL environment variable to use an isolated test database BEFORE app imports
os.environ["DATABASE_URL"] = "sqlite:///./fpl_engine_test.db"

# Copy production fpl_engine.db to fpl_engine_test.db BEFORE SQLAlchemy engine initializes
if os.path.exists("fpl_engine.db"):
    if os.path.exists("fpl_engine_test.db"):
        try:
            os.remove("fpl_engine_test.db")
        except Exception:
            pass
    shutil.copyfile("fpl_engine.db", "fpl_engine_test.db")
    conn = sqlite3.connect("fpl_engine_test.db")
    conn.execute("DELETE FROM user_picks;")
    conn.execute("DELETE FROM user_squads;")
    conn.execute("INSERT INTO user_squads (id, name, bank, free_transfers, active_chip) VALUES (1, 'My FPL Team', 0, 1, NULL);")
    conn.commit()
    conn.close()

from backend.database import Base, engine
import backend.models  # Register all models with Base.metadata

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Ensure tests run on an isolated test database and NEVER touch production fpl_engine.db."""
    Base.metadata.create_all(bind=engine)
    yield

    if os.path.exists("fpl_engine_test.db"):
        try:
            os.remove("fpl_engine_test.db")
        except Exception:
            pass
