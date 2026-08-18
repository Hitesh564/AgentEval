"""
Sanitized Node and Workflow Context Builder for AgentEval Profiling.
Extracts compact, privacy-safe execution evidence for LLM-based workflow profiling.
"""

import re
from typing import Any, Dict, List, Optional
from agenteval.profiling.models import NodeContext, WorkflowContext

SENSITIVE_KEY_PATTERNS = [
    r"api[_-]?key",
    r"auth[_-]?token",
    r"secret",
    r"password",
    r"bearer",
    r"credential",
    r"private[_-]?key",
]

MAX_STRING_LEN = 512
MAX_LIST_ITEMS = 5


def _is_sensitive_key(key: str) -> bool:
    key_lower = str(key).lower()
    for pattern in SENSITIVE_KEY_PATTERNS:
        if re.search(pattern, key_lower):
            return True
    return False


def sanitize_value(val: Any, max_str_len: int = MAX_STRING_LEN) -> Any:
    """Recursively sanitizes values, truncating long strings and redacting sensitive keys."""
    if val is None:
        return None
    if isinstance(val, (int, float, bool)):
        return val
    if isinstance(val, str):
        if len(val) > max_str_len:
            return val[:max_str_len] + f"... [truncated, total length {len(val)}]"
        return val
    if isinstance(val, dict):
        sanitized = {}
        for k, v in val.items():
            if _is_sensitive_key(str(k)):
                sanitized[str(k)] = "[REDACTED_SECRET]"
            else:
                sanitized[str(k)] = sanitize_value(v, max_str_len=max_str_len)
        return sanitized
    if isinstance(val, (list, tuple)):
        items = [sanitize_value(item, max_str_len=max_str_len) for item in val[:MAX_LIST_ITEMS]]
        if len(val) > MAX_LIST_ITEMS:
            items.append(f"... [{len(val) - MAX_LIST_ITEMS} more items omitted]")
        return items
    return str(val)[:max_str_len]


class WorkflowContextBuilder:
    """Builds sanitized WorkflowContext from execution traces or callback state."""

    @staticmethod
    def build_node_context(trace_data: Dict[str, Any], execution_order: int = 1) -> NodeContext:
        """Converts a raw trace node dictionary into a compact NodeContext."""
        node_id = str(trace_data.get("node_id", "unknown_node"))
        node_type = str(trace_data.get("node_type", "custom"))
        parents = trace_data.get("parent_node_ids") or []
        if isinstance(parents, str):
            parents = [parents]

        raw_inputs = trace_data.get("inputs") or {}
        raw_outputs = trace_data.get("outputs") or {}

        inputs_excerpt = sanitize_value(raw_inputs) if isinstance(raw_inputs, dict) else {"raw": str(raw_inputs)[:256]}
        outputs_excerpt = sanitize_value(raw_outputs) if isinstance(raw_outputs, dict) else {"raw": str(raw_outputs)[:256]}

        tools_invoked = []
        tool_name = trace_data.get("tool_name")
        if tool_name:
            tools_invoked.append(str(tool_name))

        tool_calls = trace_data.get("tool_calls") or []
        if isinstance(tool_calls, list):
            for tc in tool_calls:
                if isinstance(tc, dict) and tc.get("name"):
                    if tc["name"] not in tools_invoked:
                        tools_invoked.append(tc["name"])

        tool_calls_excerpt = sanitize_value(tool_calls) if isinstance(tool_calls, list) else []

        docs = trace_data.get("retrieved_docs")
        docs_count = len(docs) if isinstance(docs, list) else (1 if docs else 0)

        tokens_in = trace_data.get("tokens_in", 0) or 0
        tokens_out = trace_data.get("tokens_out", 0) or 0
        has_error = bool(trace_data.get("error"))

        metadata = trace_data.get("metadata") or {}
        metadata_excerpt = sanitize_value(metadata) if isinstance(metadata, dict) else {}

        return NodeContext(
            node_id=node_id,
            node_name=node_id,
            parents=parents,
            children=[],
            execution_order=execution_order,
            inputs_excerpt=inputs_excerpt if isinstance(inputs_excerpt, dict) else {"val": str(inputs_excerpt)},
            outputs_excerpt=outputs_excerpt if isinstance(outputs_excerpt, dict) else {"val": str(outputs_excerpt)},
            tools_invoked=tools_invoked,
            tool_calls_excerpt=tool_calls_excerpt if isinstance(tool_calls_excerpt, list) else [],
            retrieved_docs_count=docs_count,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_sec=0.0,
            has_error=has_error,
            metadata_excerpt=metadata_excerpt if isinstance(metadata_excerpt, dict) else {},
        )

    @classmethod
    def build_workflow_context(
        cls,
        session_id: str,
        traces: List[Dict[str, Any]],
        workflow_id: str = "default_workflow",
    ) -> WorkflowContext:
        """Constructs a full WorkflowContext from a list of trace node dicts."""
        node_contexts: List[NodeContext] = []
        execution_graph: Dict[str, List[str]] = {}
        node_ids: List[str] = []

        # Sort traces by order of occurrence if timestamps exist
        sorted_traces = sorted(
            traces,
            key=lambda t: t.get("timestamp_start") or "",
        )

        for idx, trace in enumerate(sorted_traces, start=1):
            nctx = cls.build_node_context(trace, execution_order=idx)
            node_contexts.append(nctx)
            if nctx.node_id not in node_ids:
                node_ids.append(nctx.node_id)

            for parent in nctx.parents:
                if parent not in execution_graph:
                    execution_graph[parent] = []
                if nctx.node_id not in execution_graph[parent]:
                    execution_graph[parent].append(nctx.node_id)

        # Backfill children into node_contexts
        for nctx in node_contexts:
            if nctx.node_id in execution_graph:
                nctx.children = execution_graph[nctx.node_id]

        global_inputs = {}
        if sorted_traces:
            global_inputs = sanitize_value(sorted_traces[0].get("inputs") or {})

        return WorkflowContext(
            session_id=session_id,
            workflow_id=workflow_id,
            total_nodes=len(node_ids),
            node_ids=node_ids,
            execution_graph=execution_graph,
            node_contexts=node_contexts,
            global_inputs_excerpt=global_inputs if isinstance(global_inputs, dict) else {"val": str(global_inputs)},
        )
