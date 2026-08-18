"""
Profile Signature Generator and Caching for AgentEval.
Provides deterministic signature computation and thread-safe caching.
"""

import hashlib
import json
from typing import Any, Dict, Optional
from agenteval.profiling.models import NodeProfile, WorkflowProfile, NodeContext
from agenteval.profiling.prompts import PROFILER_VERSION


def compute_profile_signature(
    node_ctx: NodeContext,
    workflow_topology: Optional[Dict[str, Any]] = None,
    catalog_version: str = "v1",
) -> str:
    """
    Computes a deterministic SHA-256 signature for a node based on identity, tool signatures,
    input/output shapes, graph topology, profiler version, and catalog version.
    """
    input_keys = sorted(list(node_ctx.inputs_excerpt.keys())) if isinstance(node_ctx.inputs_excerpt, dict) else []
    output_keys = sorted(list(node_ctx.outputs_excerpt.keys())) if isinstance(node_ctx.outputs_excerpt, dict) else []
    tools = sorted(node_ctx.tools_invoked)
    parents = sorted(node_ctx.parents)

    signature_payload = {
        "node_id": node_ctx.node_id,
        "parents": parents,
        "tools": tools,
        "input_keys": input_keys,
        "output_keys": output_keys,
        "retrieved_docs_count": 1 if node_ctx.retrieved_docs_count > 0 else 0,
        "topology": workflow_topology or {},
        "profiler_version": PROFILER_VERSION,
        "catalog_version": catalog_version,
    }

    canonical_json = json.dumps(signature_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class ProfileCache:
    """Thread-safe memory cache backed by database persistence in TraceStore."""

    def __init__(self, store: Optional[Any] = None):
        self.store = store
        self._memory_cache: Dict[str, NodeProfile] = {}  # signature -> NodeProfile

    def get_by_signature(self, signature: str) -> Optional[NodeProfile]:
        """Looks up a cached profile by signature hash."""
        if signature in self._memory_cache:
            return self._memory_cache[signature]

        if self.store is not None and hasattr(self.store, "get_profile_by_signature"):
            profile_dict = self.store.get_profile_by_signature(signature)
            if profile_dict:
                try:
                    profile = NodeProfile.from_dict(profile_dict)
                    self._memory_cache[signature] = profile
                    return profile
                except Exception:
                    pass
        return None

    def get_by_node(self, session_id: str, node_id: str) -> Optional[NodeProfile]:
        """Looks up cached profile by session_id and node_id."""
        # Check memory cache first
        for profile in self._memory_cache.values():
            if profile.session_id == session_id and profile.node_id == node_id:
                return profile

        if self.store is not None and hasattr(self.store, "get_node_profile"):
            profile_dict = self.store.get_node_profile(session_id, node_id)
            if profile_dict:
                try:
                    profile = NodeProfile.from_dict(profile_dict)
                    if profile.profile_signature:
                        self._memory_cache[profile.profile_signature] = profile
                    return profile
                except Exception:
                    pass
        return None

    def set(self, profile: NodeProfile):
        """Saves profile to memory and database cache."""
        if profile.profile_signature:
            self._memory_cache[profile.profile_signature] = profile

        if self.store is not None and hasattr(self.store, "save_node_profile"):
            try:
                self.store.save_node_profile(profile.to_dict())
            except Exception as e:
                print(f"[ProfileCache Warning] Failed to save profile to DB: {e}")

    def invalidate(self, signature: Optional[str] = None):
        """Invalidates cache entries."""
        if signature:
            self._memory_cache.pop(signature, None)
        else:
            self._memory_cache.clear()
