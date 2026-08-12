import os
from sqlalchemy import create_engine, select
import pytest

if os.environ.get("AGENTEVAL_RUN_SCRATCH_TESTS") != "1":
    pytest.skip("scratch integration test disabled by default", allow_module_level=True)

from agenteval.sdk.storage import TraceStore

def test_sqlite_engine():
    print("Testing SQLAlchemy Core with SQLite Engine...")
    store = TraceStore(db_path="sqlite:///test_sqlite_core.db")
    user_id = "test_user_sqlite"
    store.create_user(user_id, "secret_key_123")
    resolved = store.resolve_user_id("secret_key_123")
    print(f"  - Resolved User ID: {resolved}")
    assert resolved == user_id
    store.close()
    if os.path.exists("test_sqlite_core.db"):
        os.remove("test_sqlite_core.db")
    print("  [SUCCESS] SQLite SQLAlchemy Core verified.")

if __name__ == "__main__":
    test_sqlite_engine()
