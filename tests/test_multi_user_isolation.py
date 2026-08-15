import os
import sqlite3
import pytest
from fastapi.testclient import TestClient

from agenteval.sdk.storage import TraceStore
from agenteval.sdk.tracer import trace
from agenteval.root_cause.engine import RootCauseEngine
from agenteval.server.main import app

TEST_DB = "test_multi_user_isolation.db"

@pytest.fixture(autouse=True)
def setup_db():
    # Clean database before and after test
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        
    store = TraceStore(db_path=TEST_DB)
    store.clear_user_data("alice")
    store.clear_user_data("bob")
    
    # Register Alice and Bob
    store.create_user("alice", "alice_secret_key_123")
    store.create_user("bob", "bob_secret_key_456")
    
    # Temporarily override main.py database config
    import agenteval.server.main as main_mod
    orig_db = main_mod.database_url
    orig_store = main_mod.store
    orig_rc_engine = main_mod.rc_engine
    
    main_mod.database_url = TEST_DB
    main_mod.store = store
    main_mod.rc_engine = RootCauseEngine(db_path=TEST_DB)
    
    yield
    
    # Restore original config
    store.clear_user_data("alice")
    store.clear_user_data("bob")
    store.close()
    main_mod.database_url = orig_db
    main_mod.store = orig_store
    main_mod.rc_engine = orig_rc_engine
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_multi_user_data_isolation():
    # 1. Write traces for Alice
    with trace(session_id="alice_session_calib_1", node_id="planner", node_type="planner", db_path=TEST_DB, api_key="alice_secret_key_123") as t:
        t.inputs = {"q": "Alice Query"}
        t.outputs = {"response": "Alice Response"}
        
    # Write traces for Bob
    with trace(session_id="bob_session_calib_1", node_id="generator", node_type="generator", db_path=TEST_DB, api_key="bob_secret_key_456") as t:
        t.inputs = {"q": "Bob Query"}
        t.outputs = {"response": "Bob Response"}

    client = TestClient(app)
    
    # 2. Test unauthenticated request
    r = client.get("/api/sessions")
    assert r.status_code == 401
    assert "missing" in r.json()["detail"].lower()
    
    # 3. Test invalid API key
    r = client.get("/api/sessions", headers={"X-API-Key": "wrong_key"})
    assert r.status_code == 401
    assert "invalid" in r.json()["detail"].lower()
    
    # 4. Query as Alice
    r = client.get("/api/sessions", headers={"X-API-Key": "alice_secret_key_123"})
    assert r.status_code == 200
    sessions_alice = r.json()
    assert len(sessions_alice) == 1
    assert sessions_alice[0]["session_id"] == "alice_session_calib_1"
    
    # 5. Query as Bob
    r = client.get("/api/sessions", headers={"X-API-Key": "bob_secret_key_456"})
    assert r.status_code == 200
    sessions_bob = r.json()
    assert len(sessions_bob) == 1
    assert sessions_bob[0]["session_id"] == "bob_session_calib_1"
    
    # 6. Alice tries to read Bob's session trace (should be 404/not found)
    r = client.get("/api/sessions/bob_session_calib_1/trace", headers={"X-API-Key": "alice_secret_key_123"})
    assert r.status_code == 404
    
    # Bob reads his own trace (should be 200)
    r = client.get("/api/sessions/bob_session_calib_1/trace", headers={"X-API-Key": "bob_secret_key_456"})
    assert r.status_code == 200
    assert r.json()["session_id"] == "bob_session_calib_1"

    # 7. Alice tries to query Bob's session chain (should return empty chain/verdict healthy)
    r = client.get("/api/sessions/bob_session_calib_1/chain", headers={"X-API-Key": "alice_secret_key_123"})
    assert r.status_code == 200
    assert len(r.json()["chain"]) == 0
    
    # Bob queries his own chain
    r = client.get("/api/sessions/bob_session_calib_1/chain", headers={"X-API-Key": "bob_secret_key_456"})
    assert r.status_code == 200
    assert len(r.json()["chain"]) == 1
