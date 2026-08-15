from typing import List, Dict, Any

class RAGBenchmarkPack:
    """
    RAG Benchmark Pack containing query, expected answer, and expected evidence
    tuples for validating retrieval-augmented generation pipelines.
    """
    def __init__(self):
        self.dataset: List[Dict[str, Any]] = [
            {
                "id": "rag_001",
                "query": "What is AgentEval?",
                "expected_answer": "AgentEval is an open-source SDK and dashboard that performs evidence-based root-cause diagnosis of AI agent failures.",
                "expected_evidence_keywords": ["open-source", "root-cause", "diagnosis", "dashboard"]
            },
            {
                "id": "rag_002",
                "query": "Does AgentEval compete directly with LangSmith or Langfuse?",
                "expected_answer": "No, AgentEval does not compete. It is designed as a causal root-cause reasoning layer that can ingest traces from existing platforms.",
                "expected_evidence_keywords": ["not compete", "causal", "root-cause", "ingest"]
            }
        ]

    def get_dataset(self) -> List[Dict[str, Any]]:
        """Returns the dataset tuples."""
        return self.dataset
