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
        Each recommendation features a description and an expected-impact label (high/medium/low).
        """
        recommendations = []
        
        if failure_type == FailureType.RETRIEVAL_FAILURE:
            sim = evidence.get("retriever_similarity")
            if sim is not None and sim < 0.5:
                recommendations.append({
                    "suggestion": "Cosine similarity of retrieved documents is extremely low. Suggest increasing search top-k, increasing chunk size/overlap, or changing the embedding model.",
                    "impact": "high"
                })
            else:
                recommendations.append({
                    "suggestion": "Retrieval similarity is borderline, but the generator managed to maintain accuracy. Suggest updating the corpus search indexing.",
                    "impact": "medium"
                })
                
        elif failure_type == FailureType.GROUNDING_FAILURE:
            g_ratio = evidence.get("groundedness_ratio")
            if g_ratio is not None and g_ratio < 0.5:
                recommendations.append({
                    "suggestion": "Hallucination detected: generator response contains unsupported claims. Check if retrieved context is missing core facts, or modify the system prompt to explicitly restrict out-of-context answers.",
                    "impact": "high"
                })
            else:
                recommendations.append({
                    "suggestion": "Minor grounding issues detected. Check if prompt instruction guidelines are forcing the generator to make assumptions.",
                    "impact": "medium"
                })
                
        elif failure_type == FailureType.TOOL_SELECTION_FAILURE:
            margin = evidence.get("tool_margin")
            if margin is not None and margin < 0.1:
                recommendations.append({
                    "suggestion": "Tool descriptions are highly ambiguous. Rename similar tools (e.g. check_order_status vs check_order_history) and rewrite their descriptions to be distinct.",
                    "impact": "high"
                })
            else:
                recommendations.append({
                    "suggestion": "Tool selection failed occasionally. Add few-shot dispatch examples to the planner system prompt.",
                    "impact": "medium"
                })
                
        elif failure_type == FailureType.OUTPUT_FORMATTING_FAILURE:
            recommendations.append({
                "suggestion": "Structured output formatting failed (malformed JSON). Enforce JSON parsing schema using structured LLM APIs (e.g. json_object mode) or strict pydantic validators.",
                "impact": "high"
            })
            
        elif failure_type == FailureType.LATENCY_FAILURE:
            latency = evidence.get("latency", 0.0)
            recommendations.append({
                "suggestion": f"Node execution time ({latency:.2f}s) exceeded the 2.0s budget. Optimize internal calls, add caching, or execute sub-tasks in parallel.",
                "impact": "high"
            })
            
        return recommendations
