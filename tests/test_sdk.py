import os
import tempfile
import pytest
from agenteval.sdk.storage import TraceStore
from agenteval.sdk.tracer import trace

def test_trace_store_initialization():
    """Validates trace store databases initialize tables correctly."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        store = TraceStore(db_path=db_path)
        assert os.path.exists(db_path)
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

def test_manual_trace_capture():
    """Validates that using the trace context manager records and saves variables."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        session_id = "test_session_123"
        node_id = "generator_node"
        
        with trace(session_id=session_id, node_id=node_id, node_type="generator", db_path=db_path) as t:
            t.inputs = {"prompt": "Translate 'hello' to French"}
            t.outputs = {"response": "Bonjour"}
            t.parent_node_ids = ["input_node"]
            t.tokens_in = 15
            t.tokens_out = 5
            t.cost_usd = 0.0003
            
        store = TraceStore(db_path=db_path)
        traces = store.get_session_traces(session_id)
        
        assert len(traces) == 1
        recorded = traces[0]
        assert recorded["node_id"] == node_id
        assert recorded["node_type"] == "generator"
        assert recorded["inputs"] == {"prompt": "Translate 'hello' to French"}
        assert recorded["outputs"] == {"response": "Bonjour"}
        assert recorded["parent_node_ids"] == ["input_node"]
        assert recorded["tokens_in"] == 15
        assert recorded["tokens_out"] == 5
        assert recorded["cost_usd"] == 0.0003
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
