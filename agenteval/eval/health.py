from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass(frozen=True)
class HealthConfig:
    node_type: str
    metric_weights: Dict[str, float]
    threshold_policy: Dict[str, float] = field(default_factory=dict)


DEFAULT_HEALTH_CONFIGS: Dict[str, HealthConfig] = {
    "retriever": HealthConfig(
        node_type="retriever",
        metric_weights={
            "retrieval_relevance": 0.40,
            "retrieval_recall": 0.25,
            "retrieval_coverage": 0.15,
            "latency": 0.20,
        },
        threshold_policy={
            "overall": 0.70,
            "retrieval_relevance": 0.70,
            "retrieval_recall": 0.70,
            "retrieval_coverage": 0.70,
            "latency": 0.70,
        },
    ),
    "planner": HealthConfig(
        node_type="planner",
        metric_weights={
            "tool_selection": 0.35,
            "tool_arguments": 0.25,
            "instruction_following": 0.25,
            "latency": 0.15,
        },
        threshold_policy={
            "overall": 0.70,
            "tool_selection": 0.70,
            "tool_arguments": 0.70,
            "instruction_following": 0.70,
            "latency": 0.70,
        },
    ),
    "generator": HealthConfig(
        node_type="generator",
        metric_weights={
            "groundedness": 0.35,
            "instruction_following": 0.25,
            "schema_validity": 0.20,
            "latency": 0.20,
        },
        threshold_policy={
            "overall": 0.70,
            "groundedness": 0.70,
            "instruction_following": 0.70,
            "schema_validity": 0.70,
            "latency": 0.70,
        },
    ),
    "critic": HealthConfig(
        node_type="critic",
        metric_weights={
            "critic_correctness": 0.60,
            "instruction_following": 0.20,
            "latency": 0.20,
        },
        threshold_policy={
            "overall": 0.70,
            "critic_correctness": 0.70,
            "instruction_following": 0.70,
            "latency": 0.70,
        },
    ),
    "custom": HealthConfig(
        node_type="custom",
        metric_weights={
            "instruction_following": 0.40,
            "latency": 0.30,
        },
        threshold_policy={
            "overall": 0.70,
            "instruction_following": 0.70,
            "latency": 0.70,
        },
    ),
}


def get_health_config(node_type: str) -> HealthConfig:
    return DEFAULT_HEALTH_CONFIGS.get(node_type, DEFAULT_HEALTH_CONFIGS["custom"])


def weighted_health(
    metric_scores: Dict[str, Optional[float]],
    config: HealthConfig,
) -> Dict[str, Any]:
    present_metrics: Dict[str, float] = {}
    for key, value in metric_scores.items():
        if value is None:
            continue
        try:
            present_metrics[key] = max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            continue

    if not present_metrics:
        return {
            "overall_health": None,
            "metric_scores": {},
            "weakest_dimension": None,
            "weakest_dimension_score": None,
            "failed_dimensions": [],
            "legacy_min_health": None,
            "evaluation_status": "unavailable",
        }

    weighted_total = 0.0
    weight_sum = 0.0
    for metric_name, score in present_metrics.items():
        weight = config.metric_weights.get(metric_name)
        if weight is None:
            continue
        weighted_total += weight * score
        weight_sum += weight

    if weight_sum > 0:
        overall_health = weighted_total / weight_sum
    else:
        overall_health = sum(present_metrics.values()) / len(present_metrics)

    weakest_dimension = min(present_metrics, key=present_metrics.get)
    weakest_dimension_score = present_metrics[weakest_dimension]
    threshold_policy = config.threshold_policy or {}
    default_threshold = 0.70
    failed_dimensions = [
        metric_name
        for metric_name, score in present_metrics.items()
        if score < threshold_policy.get(metric_name, default_threshold)
    ]

    return {
        "overall_health": overall_health,
        "metric_scores": present_metrics,
        "weakest_dimension": weakest_dimension,
        "weakest_dimension_score": weakest_dimension_score,
        "failed_dimensions": failed_dimensions,
        "legacy_min_health": min(present_metrics.values()),
        "evaluation_status": "complete",
    }
