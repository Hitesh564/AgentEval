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
    policy_docs: Optional[List[Dict[str, Any]]]
    product_docs: Optional[List[Dict[str, Any]]]
    retrieved_docs: Optional[List[Dict[str, Any]]]
    response: Optional[str]
    critic_feedback: Optional[str]
    session_id: str
    node_history: List[str]

# Mock Document Store
MOCK_DOCS = {
    "general_faq": "Welcome to Customer Support. We help with order tracking, returns, refunds, and cancellations.",
    "refund_policy": "Our standard refund policy allows returns within 14 days of the shipping date.",
    "warranty_policy": "Items are covered by a 1-year limited warranty against manufacturing defects."
}

def load_fixtures(fixtures_path: str = "examples/fixtures/branching_test_cases.yaml") -> List[Dict[str, Any]]:
    """Loads validation fixtures from YAML."""
    if not os.path.exists(fixtures_path):
        return []
    with open(fixtures_path, "r") as f:
        return yaml.safe_load(f)

# Node 1: Planner
def planner_node(state: AgentState) -> AgentState:
    state["node_history"].append("planner")
    print("-> Running Planner Node...")
    state["plan"] = "Step 1: Retrieve policy & product data. Step 2: Synthesize findings."
    state["tool_calls"] = []
    return state

# Node 2A: Policy Retriever
def policy_retriever_node(state: AgentState) -> AgentState:
    mode = state["failure_mode"]
    state["node_history"].append("policy_retriever")
    print("-> Running Policy Retriever Node...")
    
    if mode == "branch_a_failure":
        docs = [{"text": MOCK_DOCS["general_faq"], "similarity_score": 0.35}]
    elif mode == "ambiguous_failure":
        docs = [{"text": MOCK_DOCS["general_faq"], "similarity_score": 0.59}]
    else:
        docs = [{"text": MOCK_DOCS["refund_policy"], "similarity_score": 0.95}]
        
    state["policy_docs"] = docs
    state["retrieved_docs"] = docs
    return state

# Node 2B: Product Retriever
def product_retriever_node(state: AgentState) -> AgentState:
    mode = state["failure_mode"]
    state["node_history"].append("product_retriever")
    print("-> Running Product Retriever Node...")
    
    if mode == "branch_b_failure":
        docs = [{"text": MOCK_DOCS["general_faq"], "similarity_score": 0.35}]
    elif mode == "ambiguous_failure":
        docs = [{"text": MOCK_DOCS["general_faq"], "similarity_score": 0.60}]
    else:
        docs = [{"text": MOCK_DOCS["warranty_policy"], "similarity_score": 0.95}]
        
    state["product_docs"] = docs
    state["retrieved_docs"] = docs
    return state

# Node 3: Synthesizer
def synthesizer_node(state: AgentState) -> AgentState:
    mode = state["failure_mode"]
    state["node_history"].append("synthesizer")
    print("-> Running Synthesizer Node...")
    
    if mode == "synthesizer_failure":
        # Synthesizer reasoning failure: outputs claim supported ratio of 22% (2/9 sentences)
        response = (
            "Welcome to customer support. " # 1. Supported
            "We help with order tracking. " # 2. Supported
            "The refund timeline is completely unlimited. " # 3. Unsupported
            "We offer unlimited warranty on all items. " # 4. Unsupported
            "Free overnight shipping is guaranteed. " # 5. Unsupported
            "We provide 24/7 client phone assistance. " # 6. Unsupported
            "We deliver packages via drones. " # 7. Unsupported
            "Warranty covers water damage and drops. " # 8. Unsupported
            "Return shipping is always free." # 9. Unsupported
        )
    elif mode == "ambiguous_failure":
        # Ambiguous case: synthesizer outputs 44% supported ratio (4/9 sentences)
        response = (
            "Welcome to customer support. " # 1. Supported
            "We help with order tracking. " # 2. Supported
            "We handle refunds. " # 3. Supported
            "We support cancellations. " # 4. Supported
            "We offer unlimited warranty on all items. " # 5. Unsupported
            "Free overnight shipping is guaranteed. " # 6. Unsupported
            "We provide 24/7 client phone assistance. " # 7. Unsupported
            "The refund timeline is completely unlimited. " # 8. Unsupported
            "Warranty covers water damage and drops." # 9. Unsupported
        )
    elif mode in ("branch_a_failure", "branch_b_failure"):
        # Synthesizer is penalized (health ~0.50) due to receiving bad input from one of the retrievers
        response = "The refund timeline policy is unlimited; returns are approved at any time."
    else:
        response = "Standard return policy allows returns within 14 days of shipping date."
        
    state["response"] = response
    return state

# Node 4: Critic
def critic_node(state: AgentState) -> AgentState:
    state["node_history"].append("critic")
    print("-> Running Critic Node...")
    response_text = state.get("response", "")
    if "unlimited" in response_text or "drones" in response_text:
        feedback = "Fail. Response claims unsupported policy rules."
    else:
        feedback = "Pass. Response is correct."
    state["critic_feedback"] = feedback
    return state

# Build LangGraph StateGraph
def create_agent() -> StateGraph:
    workflow = StateGraph(AgentState)
    
    workflow.add_node("planner", planner_node)
    workflow.add_node("policy_retriever", policy_retriever_node)
    workflow.add_node("product_retriever", product_retriever_node)
    workflow.add_node("synthesizer", synthesizer_node)
    workflow.add_node("critic", critic_node)
    
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "policy_retriever")
    workflow.add_edge("policy_retriever", "product_retriever")
    workflow.add_edge("product_retriever", "synthesizer")
    workflow.add_edge("synthesizer", "critic")
    workflow.add_edge("critic", END)
    
    return workflow.compile()

# Run entire branching calibration dataset
def run_calibration_dataset(db_path: str = "agenteval.db", fixtures_path: str = "examples/fixtures/branching_test_cases.yaml", version: str = "calib", mode: str = "replay"):
    from agenteval.sdk.callbacks import AgentEvalCallbackHandler
    
    fixtures = load_fixtures(fixtures_path)
    if not fixtures:
        print(f"Error: Fixtures file not found at {fixtures_path}")
        return
        
    agent = create_agent()
    print(f"Starting Branching Calibration Run for version '{version}' of {len(fixtures)} conversations...")
    print(f"Database path: {db_path}\n")
    
    for i, case in enumerate(fixtures):
        session_id = f"session_{version}_{200 + i}"
        query = case["query"]
        category = case["category"]
        
        # In fixed mode, retriever failures are resolved
        runner_category = category
        if version == "fixed" and category in ("branch_a_failure", "branch_b_failure"):
            runner_category = "none"
            
        handler = AgentEvalCallbackHandler(session_id=session_id, db_path=db_path)
        
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
            "policy_docs": None,
            "product_docs": None,
            "response": None,
            "critic_feedback": None,
            "session_id": session_id,
            "node_history": []
        }
        
        agent.invoke(state_input, config=config)
        
        # Update parallel parent-child relationships and merge retrieved docs in storage
        handler.store.update_branching_topology(session_id)
                
        print("-" * 50)
        
    print(f"\nCalibration dataset run completed. All traces saved to SQLite.")
    print(f"Triggering evaluation runs for version '{version}' (mode: {mode})...")
    from agenteval.benchmark.cli import evaluate_runs
    sessions = [f"session_{version}_{200 + i}" for i in range(len(fixtures))]
    res = evaluate_runs(sessions, db_path, version, mode=mode, fixtures_path=fixtures_path)
    print(f"Evaluation results for '{version}': Pass rate: {res.get('pass_rate', 0)*100:.1f}%, Causal Accuracy: {res.get('accuracy', 0)*100:.1f}%" if res.get('accuracy') is not None else f"Evaluation results for '{version}': Pass rate: {res.get('pass_rate', 0)*100:.1f}%")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Parallel Research Agent")
    parser.add_argument("--calibration", action="store_true", help="Run the entire branching calibration dataset")
    parser.add_argument("--fixed", action="store_true", help="Run in fixed retrieval mode (version 'fixed')")
    parser.add_argument("--db", type=str, default="agenteval.db", help="SQLite database path")
    parser.add_argument("--fixtures", type=str, default="examples/fixtures/branching_test_cases.yaml", help="Path to fixtures YAML")
    parser.add_argument("--mode", type=str, choices=["replay", "live"], default="replay", help="Evaluation mode (replay or live)")
    args = parser.parse_args()
    
    version = "fixed" if args.fixed else "calib"
    
    if args.calibration:
        run_calibration_dataset(db_path=args.db, fixtures_path=args.fixtures, version=version, mode=args.mode)
    else:
        parser.print_help()
