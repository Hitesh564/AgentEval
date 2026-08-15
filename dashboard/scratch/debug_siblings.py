from agenteval.root_cause.engine import RootCauseEngine

engine = RootCauseEngine()

mock_sibling_traces = [
    {
        "session_id": "session_sib_co",
        "node_id": "planner",
        "node_type": "planner",
        "timestamp_start": "2026-07-10T12:00:00",
        "timestamp_end": "2026-07-10T12:00:00.100",
    },
    {
        "session_id": "session_sib_co",
        "node_id": "policy_retriever",
        "node_type": "retriever",
        "parent_node_ids": ["planner"],
        "timestamp_start": "2026-07-10T12:00:01",
        "timestamp_end": "2026-07-10T12:00:01.100",
        "retrieved_docs": [{"text": "irrelevant", "similarity_score": 0.59}]
    },
    {
        "session_id": "session_sib_co",
        "node_id": "product_retriever",
        "node_type": "retriever",
        "parent_node_ids": ["planner"],
        "timestamp_start": "2026-07-10T12:00:01",
        "timestamp_end": "2026-07-10T12:00:01.100",
        "retrieved_docs": [{"text": "irrelevant", "similarity_score": 0.60}]
    },
    {
        "session_id": "session_sib_co",
        "node_id": "synthesizer",
        "node_type": "generator",
        "parent_node_ids": ["policy_retriever", "product_retriever"],
        "timestamp_start": "2026-07-10T12:00:02",
        "timestamp_end": "2026-07-10T12:00:02.100",
        "outputs": {"response": "Correct return response."}
    }
]

diagnosed = engine.propagate_failures(mock_sibling_traces)
for n in diagnosed:
    print(f"Node: {n['node_id']} ({n['node_type']})")
    print(f"  Raw Health: {n.get('raw_health')}")
    print(f"  Adjusted Health: {n.get('adjusted_health')}")
    print(f"  Is Root Cause: {n.get('is_root_cause')}")
    print(f"  Is Co-originator: {n.get('is_co_originator')}")
