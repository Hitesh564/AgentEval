from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ExecutableMetricSpec(BaseModel):
    """Specification of an executable metric supported by AgentEval."""
    name: str = Field(..., description="Unique name of the executable metric")
    description: str = Field(..., description="Description of what this metric measures")
    required_inputs: List[str] = Field(default_factory=list, description="Input fields required by this evaluator")
    output_range: List[float] = Field(default=[0.0, 1.0], description="Expected min and max score range")
    evaluator_type: str = Field(default="deterministic", description="Type: deterministic, llm_judge, heuristic")
    is_executable: bool = Field(default=True, description="Whether AgentEval can execute this metric")


class EvaluationDimension(BaseModel):
    """Conceptual evaluation dimension inferred by the LLM."""
    dimension_name: str = Field(..., description="Name of conceptual dimension (e.g., adaptiveness)")
    description: str = Field(..., description="Description of why this dimension matters for the node")
    mapped_executable_metrics: List[str] = Field(
        default_factory=list,
        description="List of executable metric names mapped to this conceptual dimension"
    )
    is_executable: bool = Field(
        default=True,
        description="True if mapped to at least one valid executable metric in AgentEval"
    )


class NodeProfile(BaseModel):
    """Structured semantic profile for a single agent node."""
    profile_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = Field(default=None, description="Associated session or workflow instance ID")
    workflow_id: Optional[str] = Field(default=None, description="Associated workflow ID or signature")
    node_id: str = Field(..., description="Unique node identifier in the graph")
    profile_signature: str = Field(default="", description="Deterministic hash of node config and evidence")
    profile_version: str = Field(default="1.0", description="Profile schema / model version")
    
    inferred_role: str = Field(
        ...,
        description="Free-form descriptive role (e.g., adaptive_interview_agent, sql_execution_agent)"
    )
    purpose: str = Field(..., description="Summary of the node's primary purpose and objective")
    responsibilities: List[str] = Field(
        default_factory=list,
        description="List of specific functional responsibilities"
    )
    inputs_summary: List[str] = Field(
        default_factory=list,
        description="Summary of inputs consumed by this node"
    )
    outputs_summary: List[str] = Field(
        default_factory=list,
        description="Summary of outputs produced by this node"
    )
    tools_used: List[str] = Field(
        default_factory=list,
        description="Names of tools invoked by this node"
    )
    
    evaluation_dimensions: List[EvaluationDimension] = Field(
        default_factory=list,
        description="Conceptual evaluation dimensions applicable to this node"
    )
    executable_metrics: List[str] = Field(
        default_factory=list,
        description="List of validated executable metric names supported by EvaluationEngine"
    )
    metric_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="Optional metric weights for health scoring normalized between 0.0 and 1.0"
    )
    
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0 to 1.0) of the inferred profile"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        """Helper to convert Pydantic model to dictionary."""
        if hasattr(self, "model_dump"):
            return self.model_dump()
        return self.dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NodeProfile":
        """Helper to create model from dictionary."""
        if hasattr(cls, "model_validate"):
            return cls.model_validate(data)
        return cls.parse_obj(data)


class WorkflowProfile(BaseModel):
    """Workflow-level profile encompassing all node profiles created in a single LLM operation."""
    workflow_id: str = Field(default="default_workflow")
    purpose: str = Field(default="", description="Overall objective of the workflow")
    node_profiles: List[NodeProfile] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        if hasattr(self, "model_dump"):
            return self.model_dump()
        return self.dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowProfile":
        if hasattr(cls, "model_validate"):
            return cls.model_validate(data)
        return cls.parse_obj(data)


class NodeContext(BaseModel):
    """Sanitized compact context representing execution evidence for a single node."""
    node_id: str
    node_name: str
    parents: List[str] = Field(default_factory=list)
    children: List[str] = Field(default_factory=list)
    execution_order: int = 1
    inputs_excerpt: Dict[str, Any] = Field(default_factory=dict)
    outputs_excerpt: Dict[str, Any] = Field(default_factory=dict)
    tools_invoked: List[str] = Field(default_factory=list)
    tool_calls_excerpt: List[Dict[str, Any]] = Field(default_factory=list)
    retrieved_docs_count: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    latency_sec: float = 0.0
    has_error: bool = False
    metadata_excerpt: Dict[str, Any] = Field(default_factory=dict)


class WorkflowContext(BaseModel):
    """Compact context of the full agent workflow for LLM profiling."""
    session_id: str
    workflow_id: str = "default_workflow"
    total_nodes: int = 0
    node_ids: List[str] = Field(default_factory=list)
    execution_graph: Dict[str, List[str]] = Field(default_factory=dict)  # parent -> children
    node_contexts: List[NodeContext] = Field(default_factory=list)
    global_inputs_excerpt: Dict[str, Any] = Field(default_factory=dict)


class ProfilingMeta(BaseModel):
    """Observability metadata for the profiler operation itself."""
    operation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    nodes_profiled_count: int = 0
    model: str = "gemini/gemini-3.5-flash"
    latency_sec: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    cache_hit: bool = False
    success: bool = True
    error_message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
