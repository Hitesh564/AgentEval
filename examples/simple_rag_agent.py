import os
import time
import json
import argparse
import yaml
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check if litellm is available
try:
    import litellm
except ImportError:
    litellm = None

# Check for LangGraph
try:
    from langgraph.graph import StateGraph, END
except ImportError:
    raise ImportError("Please ensure 'langgraph' is installed in your python environment.")

# Define Agent State matching LangGraph spec
class AgentState(TypedDict):
    query: str
    failure_mode: Optional[str]
    plan: Optional[str]
    tool_calls: Optional[List[Dict[str, Any]]]
    tool_result: Optional[str]
    retrieved_docs: Optional[List[Dict[str, Any]]]
    response: Optional[str]
    critic_feedback: Optional[str]
    session_id: str
    node_history: List[str]

# Mock Document Store
MOCK_DOCS = {
    "refund_policy": "Our standard refund policy allows returns within 14 days of the shipping date. Returns requested after 14 days are strictly ineligible.",
    "general_faq": "Welcome to Customer Support. We help with order tracking, returns, refunds, and cancellations.",
    "warranty_policy": "Items are covered by a 1-year limited warranty against manufacturing defects."
}

def load_fixtures(fixtures_path: str = "examples/fixtures/test_cases.yaml") -> List[Dict[str, Any]]:
    """Loads validation fixtures from YAML."""
    if not os.path.exists(fixtures_path):
        return []
    with open(fixtures_path, "r") as f:
        return yaml.safe_load(f)

def match_query_to_fixture(query: str, fixtures: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Matches an incoming query text to a fixture case."""
    query_clean = query.strip().lower()
    for case in fixtures:
        if case["query"].strip().lower() in query_clean or query_clean in case["query"].strip().lower():
            return case
    return None

# Node 1: Planner
def planner_node(state: AgentState) -> AgentState:
    query = state["query"]
    mode = state["failure_mode"]
    state["node_history"].append("planner")
    
    print("-> Running Planner Node...")
    
    # 1. Tool Selection Failure: Ambiguous top-2 tools
    if mode == "tool_selection_failure":
        # Planner mistakenly calls check_order_history instead of check_order_status
        # because of near-identical description similarity
        plan = "Step 1: Inspect order status history."
        tool_calls = [{"name": "check_order_history", "args": {"order_id": "12345"}}]
        
    # 2. Planning Failure: Incomplete plan for a multi-step query
    elif mode == "planning_failure":
        # Multi-step query requires cancellation AND refund eligibility.
        # Planner prompt constraint restricts it to canceling only.
        plan = "Step 1: Cancel the order."
        tool_calls = [{"name": "cancel_order", "args": {"order_id": "12345"}}]
        
    else:
        # Default correct behavior
        plan = "Step 1: Retrieve refund/warranty documentation. Step 2: Formulate response."
        tool_calls = []

    state["plan"] = plan
    state["tool_calls"] = tool_calls
    return state

# Node 2: Retriever
def retriever_node(state: AgentState) -> AgentState:
    query = state["query"]
    mode = state["failure_mode"]
    state["node_history"].append("retriever")
    
    print("-> Running Retriever Node...")
    
    # 1. Latency Failure: Sleeps past 2s budget
    if mode == "latency_failure":
        print("   [Latency Injected] Sleeping for 3.1 seconds...")
        time.sleep(3.1)

    # 2. Retrieval Failure: Low cosine similarity docs returned
    if mode == "retrieval_failure":
        # Returns general FAQ with low similarity score (0.35) instead of actual policy
        docs = [{"text": MOCK_DOCS["general_faq"], "similarity_score": 0.35}]
        
    # 3. Grounding Failure: drops critical documentation
    elif mode == "grounding_failure":
        # Drops the warranty doc, forcing generator to hallucinate
        docs = [{"text": MOCK_DOCS["general_faq"], "similarity_score": 0.88}]
        
    # 4. Compounding Failure (Chain A): retriever fails (low similarity FAQ)
    elif mode == "compounding_retrieval_hallucination":
        docs = [{"text": MOCK_DOCS["general_faq"], "similarity_score": 0.32} ]
        
    # 5. Ambiguous Failure: retriever fails with similarity 0.59
    elif mode == "ambiguous_failure":
        docs = [{"text": MOCK_DOCS["general_faq"], "similarity_score": 0.59}]
        
    else:
        # Default correct retrieval
        docs = [{"text": MOCK_DOCS["refund_policy"], "similarity_score": 0.95}]

    state["retrieved_docs"] = docs
    return state

# Node 3: Generator
def generator_node(state: AgentState) -> AgentState:
    query = state["query"]
    mode = state["failure_mode"]
    docs = state.get("retrieved_docs", [])
    state["node_history"].append("generator")
    
    print("-> Running Generator Node...")
    
    # 1. Reasoning Failure: Ineligible claim due to reasoning error
    if mode == "reasoning_failure":
        response = (
            "The order shipped 10 days ago. The policy allows returns within 14 days. "
            "Therefore, the item is not returnable because 10 is greater than 15."
        )
        
    # 2. Grounding Failure: Hallucinates because context was dropped
    elif mode == "grounding_failure":
        response = "AgentEval products are covered under a lifetime unlimited warranty."
        
    # 3. Output Formatting Failure: Outputs malformed JSON
    elif mode == "output_formatting_failure":
        response = "{eligible: true, reason: 'Returns are allowed' -- missing closing quotes"
        
    # 4. Compounding Failure (Chain A): generator hallucinates from bad documents
    elif mode == "compounding_retrieval_hallucination":
        response = "The refund timeline policy is unlimited; returns are approved at any time."
        
    # 5. Ambiguous Failure: generator fails with 44% groundedness score
    elif mode == "ambiguous_failure":
        response = (
            "Welcome to customer support. "
            "We help with order tracking. "
            "We handle refunds. "
            "We support cancellations. "
            "We offer unlimited warranty on all items. "
            "Free overnight shipping is guaranteed. "
            "We provide 24/7 client phone assistance. "
            "The refund timeline is completely unlimited. "
            "Warranty covers water damage and drops."
        )
        
    else:
        # Default correct response
        doc_text = docs[0]["text"] if docs else ""
        response = f"Based on our policy: '{doc_text}', you can return items within 14 days."

    state["response"] = response
    return state

# Node 4: Critic
def critic_node(state: AgentState) -> AgentState:
    mode = state["failure_mode"]
    state["node_history"].append("critic")
    
    print("-> Running Critic Node...")
    
    # 1. Compounding Failure (Chain A): critic fails to catch generator's hallucination
    if mode == "compounding_retrieval_hallucination":
        feedback = "Pass. The response is accurate."
    else:
        # Default correct critic behavior
        response_text = state.get("response", "")
        if "lifetime unlimited warranty" in response_text or "unlimited" in response_text:
            feedback = "Fail. Response claims unsupported warranty rules."
        else:
            feedback = "Pass. Response is correct."

    state["critic_feedback"] = feedback
    return state

# Build LangGraph StateGraph
def create_agent() -> StateGraph:
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("retriever", retriever_node)
    workflow.add_node("generator", generator_node)
    workflow.add_node("critic", critic_node)
    
    # Add edges
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "retriever")
    workflow.add_edge("retriever", "generator")
    workflow.add_edge("generator", "critic")
    workflow.add_edge("critic", END)
    
    return workflow.compile()

# Run entire 43-case calibration dataset
def run_calibration_dataset(db_path: str = "agenteval.db", fixtures_path: str = "examples/fixtures/test_cases.yaml", version: str = "calib", mode: str = "replay"):
    from agenteval.sdk.callbacks import AgentEvalCallbackHandler
    
    fixtures = load_fixtures(fixtures_path)
    if not fixtures:
        print(f"Error: Fixtures file not found at {fixtures_path}")
        return
        
    agent = create_agent()
    print(f"Starting Calibration Run for version '{version}' of {len(fixtures)} conversations...")
    print(f"Database path: {db_path}\n")
    
    for i, case in enumerate(fixtures):
        session_id = f"session_{version}_{100 + i}"
        query = case["query"]
        category = case["category"]
        
        # In fixed mode, retrieval failures and compounding retrieval-hallucination cases are resolved
        runner_category = category
        if version == "fixed" and category in ("retrieval_failure", "compounding_retrieval_hallucination"):
            runner_category = "none"
            
        # Wire Callback Handler
        handler = AgentEvalCallbackHandler(session_id=session_id, db_path=db_path)
        
        # Configure callback in config
        config = {
            "callbacks": [handler],
            "configurable": {"session_id": session_id}
        }
        
        print(f"Running case {i+1}/{len(fixtures)}: ID={case['id']} | Category={category} (running as {runner_category}) | Session={session_id}")
        
        state_input: AgentState = {
            "query": query,
            "failure_mode": runner_category,
            "plan": None,
            "tool_calls": None,
            "tool_result": None,
            "retrieved_docs": None,
            "response": None,
            "critic_feedback": None,
            "session_id": session_id,
            "node_history": []
        }
        
        agent.invoke(state_input, config=config)
        
        # Clear parent relationship of generator to simulate parallel failures
        if runner_category == "ambiguous_failure":
            import sqlite3
            conn = sqlite3.connect(db_path)
            try:
                with conn:
                    conn.execute("UPDATE traces SET parent_node_ids = '[]' WHERE session_id = ? AND node_id = 'generator'", (session_id,))
            finally:
                conn.close()
                
        print("-" * 50)
        
    print(f"\nCalibration dataset run for version '{version}' completed. All traces saved to SQLite.")
    print(f"Triggering evaluation runs for version '{version}' (mode: {mode})...")
    from agenteval.benchmark.cli import evaluate_runs
    sessions = [f"session_{version}_{100 + i}" for i in range(len(fixtures))]
    res = evaluate_runs(sessions, db_path, version, mode=mode)
    print(f"Evaluation results for '{version}': Pass rate: {res.get('pass_rate', 0)*100:.1f}%, Causal Accuracy: {res.get('accuracy', 0)*100:.1f}%" if res.get('accuracy') is not None else f"Evaluation results for '{version}': Pass rate: {res.get('pass_rate', 0)*100:.1f}%")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Simple RAG Agent")
    parser.add_argument("--query", type=str, help="Single query to run")
    parser.add_argument("--calibration", action="store_true", help="Run the entire 43-case calibration dataset")
    parser.add_argument("--fixed", action="store_true", help="Run in fixed retrieval mode (version 'fixed')")
    parser.add_argument("--db", type=str, default="agenteval.db", help="SQLite database path")
    parser.add_argument("--fixtures", type=str, default="examples/fixtures/test_cases.yaml", help="Path to fixtures YAML")
    parser.add_argument("--mode", type=str, choices=["replay", "live"], default="replay", help="Evaluation mode (replay or live)")
    args = parser.parse_args()
    
    version = "fixed" if args.fixed else "calib"
    
    if args.calibration:
        run_calibration_dataset(db_path=args.db, fixtures_path=args.fixtures, version=version, mode=args.mode)
    elif args.query:
        fixtures = load_fixtures(args.fixtures)
        matched = match_query_to_fixture(args.query, fixtures)
        category = matched["category"] if matched else None
        
        runner_category = category
        if version == "fixed" and category in ("retrieval_failure", "compounding_retrieval_hallucination"):
            runner_category = "none"
            
        agent = create_agent()
        from agenteval.sdk.callbacks import AgentEvalCallbackHandler
        session_id = f"session_manual_{version}_{int(time.time())}"
        handler = AgentEvalCallbackHandler(session_id=session_id, db_path=args.db)
        
        res = agent.invoke({
            "query": args.query,
            "failure_mode": runner_category,
            "plan": None,
            "tool_calls": None,
            "tool_result": None,
            "retrieved_docs": None,
            "response": None,
            "critic_feedback": None,
            "session_id": session_id,
            "node_history": []
        }, config={"callbacks": [handler]})
        
        print("\nFinal Agent Response:")
        print(json.dumps(res, indent=2))
    else:
        parser.print_help()

