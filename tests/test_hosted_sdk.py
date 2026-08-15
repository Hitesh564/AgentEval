import os
import tempfile
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from agenteval.eval.metrics import EvaluationEngine, _build_cache_key
from agenteval.root_cause.engine import RootCauseEngine
from agenteval.sdk.client import AgentEvalClient
from agenteval.sdk.storage import TraceStore
from agenteval.server.main import app, _parse_cors_origins


def _setup_local_server_state(db_path: str):
    import agenteval.server.main as main_mod

    store = TraceStore(db_path=db_path)
    store.clear_user_data("alice")
    store.clear_user_data("bob")
    store.create_user("alice", "alice_secret_key_123")
    store.create_user("bob", "bob_secret_key_456")

    orig_db = main_mod.database_url
    orig_store = main_mod.store
    orig_rc_engine = main_mod.rc_engine
    main_mod.database_url = db_path
    main_mod.store = store
    main_mod.rc_engine = RootCauseEngine(db_path=db_path)
    return main_mod, store, orig_db, orig_store, orig_rc_engine


def test_parse_cors_origins_trims_and_defaults():
    assert _parse_cors_origins(None) == ["http://localhost:5173", "http://127.0.0.1:5173"]
    assert _parse_cors_origins(" https://example.com , http://localhost:5173 ") == [
        "https://example.com",
        "http://localhost:5173",
    ]


def test_agent_eval_client_posts_trace_with_api_key(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"status": "accepted"}

    class FakeHttpxClient:
        def __init__(self, *, timeout, headers):
            captured["timeout"] = timeout
            captured["headers"] = headers

        def post(self, url, content):
            captured["url"] = url
            captured["content"] = content
            return FakeResponse()

        def close(self):
            captured["closed"] = True

    monkeypatch.setattr("agenteval.sdk.client.httpx.Client", FakeHttpxClient)
    client = AgentEvalClient("https://api.example.com", "secret-key", retries=0)
    response = client.submit_trace({"session_id": "s1", "node_id": "n1"})
    client.close()

    assert response["status"] == "accepted"
    assert captured["url"] == "https://api.example.com/api/v1/traces"
    assert captured["headers"]["X-API-Key"] == "secret-key"
    assert captured["closed"] is True


def test_agent_eval_client_retries_transient_failure(monkeypatch):
    calls = {"count": 0}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"status": "accepted"}

    class FakeHttpxClient:
        def __init__(self, *, timeout, headers):
            self.timeout = timeout
            self.headers = headers

        def post(self, url, content):
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("transient failure")
            return FakeResponse()

        def close(self):
            return None

    monkeypatch.setattr("agenteval.sdk.client.httpx.Client", FakeHttpxClient)
    client = AgentEvalClient("https://api.example.com", "secret-key", retries=1)
    response = client.submit_trace({"session_id": "s1", "node_id": "n1"})
    client.close()

    assert response["status"] == "accepted"
    assert calls["count"] == 2


def test_trace_ingestion_scopes_authenticated_user_and_rejects_impersonation(monkeypatch):
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    main_mod = None
    store = None
    try:
        main_mod, store, orig_db, orig_store, orig_rc_engine = _setup_local_server_state(db_path)
        client = TestClient(app)

        reject = client.post(
            "/api/v1/traces",
            headers={"X-API-Key": "alice_secret_key_123"},
            json={
                "session_id": "alice_session",
                "node_id": "planner",
                "node_type": "planner",
                "timestamp_start": "2026-08-15T10:00:00Z",
                "timestamp_end": "2026-08-15T10:00:01Z",
                "outputs": {"response": "ok"},
                "user_id": "bob",
            },
        )
        assert reject.status_code == 400

        accepted = client.post(
            "/api/v1/traces",
            headers={"X-API-Key": "alice_secret_key_123"},
            json={
                "session_id": "alice_session",
                "node_id": "planner",
                "node_type": "planner",
                "timestamp_start": "2026-08-15T10:00:00Z",
                "timestamp_end": "2026-08-15T10:00:01Z",
                "outputs": {"response": "ok"},
            },
        )
        assert accepted.status_code == 200
        traces = store.get_session_traces("alice_session", user_id="alice")
        assert len(traces) == 1
        assert traces[0]["user_id"] == "alice"
    finally:
        if main_mod is not None:
            main_mod.database_url = orig_db
            main_mod.store = orig_store
            main_mod.rc_engine = orig_rc_engine
        if store is not None:
            store.close()
        if os.path.exists(db_path):
            os.remove(db_path)


def test_cache_isolation_between_users(monkeypatch):
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = None
    try:
        store = TraceStore(db_path=db_path)
        engine = EvaluationEngine(mode="live", db_path=db_path)
        engine.store = store
        scores = iter(["0.61", "0.22", "0.33", "0.44"])
        call_count = {"count": 0}

        def fake_llm(*_args, **_kwargs):
            call_count["count"] += 1
            return next(scores)

        monkeypatch.setattr("agenteval.eval.metrics.get_llm_response", fake_llm)
        alice_result = engine.evaluate_semantic_response_quality(
            question="What is the status?",
            conversation_history="Context for the request.",
            response="Everything is healthy.",
            user_id="alice",
        )
        assert alice_result["score"] == pytest.approx(0.61)
        assert call_count["count"] == 1

        alice_cached = engine.evaluate_semantic_response_quality(
            question="What is the status?",
            conversation_history="Context for the request.",
            response="Everything is healthy.",
            user_id="alice",
        )
        assert alice_cached["judge_mode"] == "cached_llm"
        assert call_count["count"] == 1

        monkeypatch.setenv("AGENTEVAL_MODEL", "gemini/gemini-2.5-flash")
        alice_model_changed = engine.evaluate_semantic_response_quality(
            question="What is the status?",
            conversation_history="Context for the request.",
            response="Everything is healthy.",
            user_id="alice",
        )
        assert alice_model_changed["score"] == pytest.approx(0.22)
        assert call_count["count"] == 2

        monkeypatch.delenv("AGENTEVAL_MODEL", raising=False)
        alice_prompt_changed = engine.evaluate_semantic_response_quality(
            question="What is the status?",
            conversation_history="A different prior conversation.",
            response="Everything is healthy.",
            user_id="alice",
        )
        assert alice_prompt_changed["score"] == pytest.approx(0.33)
        assert call_count["count"] == 3

        bob_result = engine.evaluate_semantic_response_quality(
            question="What is the status?",
            conversation_history="Context for the request.",
            response="Everything is healthy.",
            user_id="bob",
        )
        assert bob_result["score"] == pytest.approx(0.44)
        assert call_count["count"] == 4

        alice_key = _build_cache_key(
            "semantic_response_quality",
            "v2",
            engine.model_name,
            {
                "question": "What is the status?",
                "conversation_history": "Context for the request.",
                "response": "Everything is healthy.",
            },
            user_id="alice",
        )
        bob_key = _build_cache_key(
            "semantic_response_quality",
            "v2",
            engine.model_name,
            {
                "question": "What is the status?",
                "conversation_history": "Context for the request.",
                "response": "Everything is healthy.",
            },
            user_id="bob",
        )
        assert store.get_cached_result(alice_key, user_id="alice") is not None
        assert store.get_cached_result(alice_key, user_id="bob") is None
        assert store.get_cached_result(bob_key, user_id="alice") is None
        assert store.get_cached_result(bob_key, user_id="bob") is not None
    finally:
        if store is not None:
            store.close()
        if os.path.exists(db_path):
            os.remove(db_path)
