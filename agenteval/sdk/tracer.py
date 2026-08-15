import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from agenteval.sdk.storage import TraceStore
from agenteval.sdk.client import AgentEvalClient

class trace:
    """
    Context manager for manual tracing of agent runs / custom node executions.
    
    Usage:
        with trace(session_id="session_123", node_id="node_a", node_type="generator") as t:
            # perform LLM call or computation
            t.inputs = {"query": "hello"}
            t.outputs = {"response": "hi"}
    """
    def __init__(
        self,
        session_id: str,
        node_id: str,
        node_type: str,
        db_path: Optional[str] = None,
        *,
        database_url: Optional[str] = None,
        api_url: Optional[str] = None,
        parent_session_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.session_id = session_id
        self.node_id = node_id
        self.node_type = node_type
        self.db_path = database_url or db_path or "agenteval.db"
        self.parent_session_id = parent_session_id
        self.api_url = api_url
        self.api_key = api_key
        self.store = None if api_url else TraceStore(db_path=self.db_path)
        self.client = AgentEvalClient(api_url, api_key) if api_url else None
        self.inputs = None
        self.outputs = None
        self.parent_node_ids = []
        self.retrieved_docs = None
        self.tool_name = None
        self.tool_args = None
        self.tool_result = None
        self.tokens_in = 0
        self.tokens_out = 0
        self.cost_usd = 0.0

        self.user_id = None
        if api_key and self.store is not None:
            self.user_id = self.store.resolve_user_id(api_key)

        if parent_session_id and self.store is not None:
            self.store.save_session_link(session_id, parent_session_id, link_reason="Handoff", user_id=self.user_id)

    def __enter__(self):
        self.timestamp_start = datetime.now(timezone.utc).isoformat()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.timestamp_end = datetime.now(timezone.utc).isoformat()

        if exc_type:
            # log error details in outputs if execution failed
            self.outputs = {"error": str(exc_val)}
        
        trace_data = {
            "session_id": self.session_id,
            "node_id": self.node_id,
            "node_type": self.node_type,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "tool_result": self.tool_result,
            "retrieved_docs": self.retrieved_docs,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_usd": self.cost_usd,
            "parent_node_ids": self.parent_node_ids,
            "parent_session_id": self.parent_session_id,
            "user_id": self.user_id
        }
        if self.client is not None:
            self.client.submit_trace(trace_data)
        else:
            self.store.save_trace_node(trace_data)
        # Propagate exceptions if any
        return False
