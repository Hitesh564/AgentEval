import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from agenteval.sdk.storage import TraceStore

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:
    # Fallback if langchain-core is not installed
    class BaseCallbackHandler:
        pass

class AgentEvalCallbackHandler(BaseCallbackHandler):
    """
    Real, production-ready LangChain/LangGraph callback handler.
    Automatically logs node transitions, tool calls, and retrieval events
    to the TraceStore (SQLite database) with parent-node relationships.
    """
    def __init__(self, session_id: str, db_path: str = "agenteval.db"):
        self.session_id = session_id
        self.db_path = db_path
        self.store = TraceStore(db_path=db_path)
        # Maps active run_id -> active node trace dict
        self.active_runs: Dict[str, Dict[str, Any]] = {}
        # Lists completed nodes to link parent_node_ids
        self.completed_nodes: List[str] = []
        # Tracks attempt counts for each node_id to populate attempt_number automatically
        self.node_attempts: Dict[str, int] = {}

    def _resolve_node_type(self, node_name: str) -> str:
        """Resolves node names to taxonomy types."""
        name = node_name.lower()
        if "planner" in name:
            return "planner"
        elif "retriever" in name or "search" in name:
            return "retriever"
        elif "generator" in name or "response" in name:
            return "generator"
        elif "critic" in name or "eval" in name:
            return "critic"
        elif "tool" in name:
            return "tool"
        return "custom"

    def _get_latest_active_node(self) -> Optional[Dict[str, Any]]:
        """Returns the currently active LangGraph node trace."""
        if not self.active_runs:
            return None
        # Retrieve the most recently started active node run
        latest_run_id = list(self.active_runs.keys())[-1]
        return self.active_runs[latest_run_id]

    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> Any:
        run_id = str(kwargs.get("run_id"))
        metadata = kwargs.get("metadata", {})
        node_name = metadata.get("langgraph_node")
        
        # Check if this represents a LangGraph node execution step
        if node_name:
            # Ignore nested sub-chains inside the same node
            parent_run_id = str(kwargs.get("parent_run_id"))
            if parent_run_id in self.active_runs and self.active_runs[parent_run_id]["node_id"] == node_name:
                return
                
            # Set parent to the most recently completed node to support causal propagation chains
            parents = [self.completed_nodes[-1]] if self.completed_nodes else []
            
            # Increment and track attempt count for loop nodes
            attempt = self.node_attempts.get(node_name, 0) + 1
            self.node_attempts[node_name] = attempt
            
            self.active_runs[run_id] = {
                "session_id": self.session_id,
                "node_id": node_name,
                "node_type": self._resolve_node_type(node_name),
                "timestamp_start": datetime.now(timezone.utc).isoformat(),
                "inputs": inputs,
                "parent_node_ids": parents,
                "attempt_number": attempt,
                "tool_name": None,
                "tool_args": None,
                "tool_result": None,
                "retrieved_docs": None,
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0
            }

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> Any:
        run_id = str(kwargs.get("run_id"))
        
        if run_id in self.active_runs:
            node_data = self.active_runs[run_id]
            node_data["timestamp_end"] = datetime.now(timezone.utc).isoformat()
            
            # Capture state values from node output dict
            if isinstance(outputs, dict):
                node_data["outputs"] = outputs
                
                # Check for manually injected documents (from RAG node outputs)
                if "retrieved_docs" in outputs and outputs["retrieved_docs"]:
                    node_data["retrieved_docs"] = outputs["retrieved_docs"]
                    
                # Check for tool calls or planning details
                if "tool_calls" in outputs and outputs["tool_calls"]:
                    node_data["tool_calls"] = outputs["tool_calls"]
                    # Store first tool invocation details if present
                    if len(outputs["tool_calls"]) > 0:
                        tc = outputs["tool_calls"][0]
                        node_data["tool_name"] = tc.get("name")
                        node_data["tool_args"] = tc.get("args")
            
            # Save the node details
            self.store.save_trace_node(node_data)
            
            # Update sequence history
            self.completed_nodes.append(node_data["node_id"])
            del self.active_runs[run_id]

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> Any:
        active = self._get_latest_active_node()
        if active:
            active["tool_name"] = serialized.get("name")
            try:
                active["tool_args"] = json.loads(input_str)
            except Exception:
                active["tool_args"] = {"input": input_str}

    def on_tool_end(self, output: Any, **kwargs: Any) -> Any:
        active = self._get_latest_active_node()
        if active:
            # If tool outputs JSON, serialize it nicely
            if isinstance(output, (dict, list)):
                active["tool_result"] = json.dumps(output)
            else:
                active["tool_result"] = str(output)

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> Any:
        # LLM prompt starts
        pass

    def on_llm_end(self, response: Any, **kwargs: Any) -> Any:
        active = self._get_latest_active_node()
        if active and hasattr(response, "llm_output") and response.llm_output:
            usage = response.llm_output.get("token_usage", {})
            if usage:
                active["tokens_in"] += usage.get("prompt_tokens", 0)
                active["tokens_out"] += usage.get("completion_tokens", 0)
                # Apply standard estimated pricing (e.g. Gemini 1.5 Flash: $0.075 / 1M in, $0.30 / 1M out)
                tin = usage.get("prompt_tokens", 0)
                tout = usage.get("completion_tokens", 0)
                active["cost_usd"] += ((tin * 0.075) + (tout * 0.30)) / 1_000_000
