from enum import Enum

class FailureType(str, Enum):
    """
    Standardized failure taxonomy for AgentEval.
    Used consistently across evaluation, root cause analysis,
    recommendations, and the dashboard.
    """
    RETRIEVAL_FAILURE = "retrieval_failure"
    TOOL_SELECTION_FAILURE = "tool_selection_failure"
    PLANNING_FAILURE = "planning_failure"
    REASONING_FAILURE = "reasoning_failure"
    GROUNDING_FAILURE = "grounding_failure"
    OUTPUT_FORMATTING_FAILURE = "output_formatting_failure"
    LATENCY_FAILURE = "latency_failure"
