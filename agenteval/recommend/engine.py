from typing import Dict, Any, List
from agenteval.taxonomy import FailureType

class RecommendationEngine:
    """
    Recommendation Engine that analyzes evidence from diagnosed failure nodes
    and generates concrete, actionable suggestions.
    """
    def generate_recommendations(self, failure_type: FailureType, evidence: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generates evidence-driven recommendations.
        Each recommendation includes a concise problem statement, the evidence used,
        a recommended action, and an expected effect.
        """
        recommendations = []
        priority = "medium"
        confidence = 0.6

        def build_rec(problem: str, evidence_text: str, action: str, effect: str, priority_value: str, confidence_value: float, suggestion: str, impact: str):
            return {
                "problem": problem,
                "evidence": evidence_text,
                "recommended_action": action,
                "expected_effect": effect,
                "priority": priority_value,
                "confidence": confidence_value,
                "suggestion": suggestion,
                "impact": impact,
            }
        
        if failure_type == FailureType.RETRIEVAL_FAILURE:
            retrieval = evidence.get("retrieval_evidence") or {}
            sim = retrieval.get("score", evidence.get("retriever_similarity"))
            if sim is not None and sim < 0.5:
                recommendations.append(build_rec(
                    "Low retrieval quality",
                    f"Retrieval score={sim:.2f}",
                    "Increase top-k and test a stronger embedding or hybrid retriever.",
                    "Better context coverage with a possible latency trade-off.",
                    "high",
                    0.75,
                    "Retrieved context is weak. Increase search top-k, raise chunk overlap, or evaluate a stronger embedding model.",
                    "high"
                ))
            else:
                recommendations.append(build_rec(
                    "Borderline retrieval evidence",
                    f"Retrieval score={sim if sim is not None else 'unavailable'}",
                    "Review corpus indexing and query rewrite quality.",
                    "Slight improvement in retrieval recall and grounding.",
                    "medium",
                    0.55,
                    "Retrieval quality is borderline. Review corpus indexing and query rewrite quality.",
                    "medium"
                ))
                
        elif failure_type == FailureType.GROUNDING_FAILURE:
            grounded = evidence.get("groundedness_evidence") or {}
            g_ratio = grounded.get("score", evidence.get("groundedness_ratio"))
            if g_ratio is not None and g_ratio < 0.5:
                recommendations.append(build_rec(
                    "Unsupported generator claims",
                    f"Groundedness score={g_ratio:.2f}",
                    "Tighten prompt constraints and improve retrieved evidence coverage.",
                    "Lower hallucination rate and stronger citation fidelity.",
                    "high",
                    0.8,
                    "Hallucination detected: generator response contains unsupported claims. Check if retrieved context is missing core facts or tighten the system prompt.",
                    "high"
                ))
            else:
                recommendations.append(build_rec(
                    "Minor grounding drift",
                    f"Groundedness score={g_ratio if g_ratio is not None else 'unavailable'}",
                    "Review prompt wording and evidence retrieval coverage.",
                    "More conservative responses with fewer unsupported claims.",
                    "medium",
                    0.55,
                    "Minor grounding issues detected. Review prompt instruction guidelines and evidence coverage.",
                    "medium"
                ))
                
        elif failure_type == FailureType.TOOL_SELECTION_FAILURE:
            tool = evidence.get("tool_evidence") or {}
            margin = tool.get("margin", evidence.get("tool_margin"))
            if margin is not None and margin < 0.1:
                recommendations.append(build_rec(
                    "Ambiguous tool choice",
                    f"Tool margin={margin:.2f}",
                    "Differentiate tool descriptions and add explicit dispatch examples.",
                    "More reliable tool selection under similar tool names.",
                    "high",
                    0.72,
                    "Tool descriptions are highly ambiguous. Rename similar tools and rewrite their descriptions to be distinct.",
                    "high"
                ))
            else:
                recommendations.append(build_rec(
                    "Tool selection instability",
                    f"Tool margin={margin if margin is not None else 'unavailable'}",
                    "Add few-shot dispatch examples to the planner prompt.",
                    "Lower tool-call error rate.",
                    "medium",
                    0.52,
                    "Tool selection failed occasionally. Add few-shot dispatch examples to the planner system prompt.",
                    "medium"
                ))
                
        elif failure_type == FailureType.OUTPUT_FORMATTING_FAILURE:
            recommendations.append(build_rec(
                "Malformed structured output",
                "JSON parsing validity failed or was malformed.",
                "Enforce schema-constrained output generation and validation.",
                "Higher schema validity and fewer parser failures.",
                "high",
                0.8,
                "Structured output formatting failed (malformed JSON). Enforce JSON parsing schema using structured LLM APIs or strict validators.",
                "high"
            ))
            
        elif failure_type == FailureType.LATENCY_FAILURE:
            latency = evidence.get("latency", 0.0)
            recommendations.append(build_rec(
                "Latency budget exceeded",
                f"Latency={latency:.2f}s",
                "Optimize expensive calls, cache results, or parallelize independent work.",
                "Lower execution time and better SLA compliance.",
                "high",
                0.85,
                f"Node execution time ({latency:.2f}s) exceeded the latency budget. Optimize internal calls, add caching, or execute sub-tasks in parallel.",
                "high"
            ))
            
        return recommendations
