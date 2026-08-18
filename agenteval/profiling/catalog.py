"""
Executable Metric Catalog for AgentEval.
Discovers and returns the real executable evaluation metrics supported by AgentEval's EvaluationEngine.
"""

from typing import Dict, List
from agenteval.profiling.models import ExecutableMetricSpec

EXECUTABLE_METRICS: Dict[str, ExecutableMetricSpec] = {
    "instruction_following": ExecutableMetricSpec(
        name="instruction_following",
        description="Assesses how well the agent output follows system instructions, prompt constraints, and guidelines.",
        required_inputs=["system_prompt", "response"],
        output_range=[0.0, 1.0],
        evaluator_type="llm_judge",
        is_executable=True,
    ),
    "semantic_response_quality": ExecutableMetricSpec(
        name="semantic_response_quality",
        description="Assesses semantic relevance, helpfulness, and quality of the response given the prompt/conversation context.",
        required_inputs=["question", "response"],
        output_range=[0.0, 1.0],
        evaluator_type="llm_judge",
        is_executable=True,
    ),
    "tool_selection": ExecutableMetricSpec(
        name="tool_selection",
        description="Evaluates tool selection accuracy and semantic ranking margin against candidate tools or expected tools.",
        required_inputs=["chosen_tool"],
        output_range=[0.0, 1.0],
        evaluator_type="deterministic",
        is_executable=True,
    ),
    "retrieval_evidence": ExecutableMetricSpec(
        name="retrieval_evidence",
        description="Calculates document retrieval relevance, mean similarity, top-k precision/recall, and MRR.",
        required_inputs=["query", "retrieved_docs"],
        output_range=[0.0, 1.0],
        evaluator_type="deterministic",
        is_executable=True,
    ),
    "groundedness": ExecutableMetricSpec(
        name="groundedness",
        description="Decomposes response into factual claims and verifies claim support against retrieved documents/context.",
        required_inputs=["response", "retrieved_docs"],
        output_range=[0.0, 1.0],
        evaluator_type="llm_judge",
        is_executable=True,
    ),
    "json_validity": ExecutableMetricSpec(
        name="json_validity",
        description="Deterministic syntax check verifying if output response is valid parseable JSON.",
        required_inputs=["response_text"],
        output_range=[0.0, 1.0],
        evaluator_type="deterministic",
        is_executable=True,
    ),
    "latency": ExecutableMetricSpec(
        name="latency",
        description="Measures node execution time difference in seconds against latency budget.",
        required_inputs=["timestamp_start", "timestamp_end"],
        output_range=[0.0, 1.0],
        evaluator_type="deterministic",
        is_executable=True,
    ),
    "cost_and_tokens": ExecutableMetricSpec(
        name="cost_and_tokens",
        description="Tracks token consumption (input/output) and estimated USD pricing for LLM calls.",
        required_inputs=["tokens_in", "tokens_out", "cost_usd"],
        output_range=[0.0, 1.0],
        evaluator_type="deterministic",
        is_executable=True,
    ),
}


def get_executable_metric_catalog() -> Dict[str, ExecutableMetricSpec]:
    """Returns the dictionary of executable metric specifications."""
    return EXECUTABLE_METRICS


def get_supported_metric_names() -> List[str]:
    """Returns list of valid executable metric names."""
    return list(EXECUTABLE_METRICS.keys())
