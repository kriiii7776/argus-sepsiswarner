import os
import sys
from pathlib import Path

# Ensure workspace root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Force isolated test database for all pytest executions
TEST_DB_PATH = root_dir / ".argus_test_suite.sqlite"
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"

os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["ARGUS_TEST_MODE"] = "true"

# Pre-import store module and initialize test database tables
from src.backend.db import store
store.DATABASE_URL = TEST_DB_URL
store.engine = store.create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
store.Session = store.sessionmaker(bind=store.engine, expire_on_commit=False)
store.Base.metadata.create_all(bind=store.engine)
