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
    retriever_attempts: int

# Mock Document Store
MOCK_DOCS = {
    "refund_policy": "Our standard refund policy allows returns within 14 days of the shipping date. Returns requested after 14 days are strictly ineligible.",
    "general_faq": "Welcome to Customer Support. We help with order tracking, returns, refunds, and cancellations.",
    "warranty_policy": "Items are covered by a 1-year limited warranty against manufacturing defects."
}

def load_fixtures(fixtures_path: str = "examples/fixtures/retry_test_cases.yaml") -> List[Dict[str, Any]]:
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
    state["node_history"].append("planner")
    print("-> Running Planner Node...")
    state["plan"] = "Step 1: Retrieve refund/warranty documentation. Step 2: Formulate response."
    state["tool_calls"] = []
    return state

# Node 2: Retriever (capable of retrying)
def retriever_node(state: AgentState) -> AgentState:
    mode = state["failure_mode"]
    state["node_history"].append("retriever")
    print("-> Running Retriever Node...")
    
    attempt = state.get("retriever_attempts", 0) + 1
    
    if mode == "retrieval_retry_success":
        if attempt == 1:
            # Low similarity FAQ
            docs = [{"text": MOCK_DOCS["general_faq"], "similarity_score": 0.35}]
        else:
            # High similarity refund policy
            docs = [{"text": MOCK_DOCS["refund_policy"], "similarity_score": 0.95}]
    elif mode == "retrieval_retry_failure":
        # Always fails with low similarity
        docs = [{"text": MOCK_DOCS["general_faq"], "similarity_score": 0.35}]
    else:
        # Default correct retrieval
        docs = [{"text": MOCK_DOCS["refund_policy"], "similarity_score": 0.95}]
        
    state["retrieved_docs"] = docs
    state["retriever_attempts"] = attempt
    return state

def route_retriever(state: AgentState) -> str:
    mode = state.get("failure_mode")
    attempt = state.get("retriever_attempts", 0)
    
    if mode == "retrieval_retry_success":
        if attempt < 2:
            print(f"   [Retrying Retriever] Attempt {attempt} failed similarity threshold. Retrying...")
            return "retriever"
    elif mode == "retrieval_retry_failure":
        if attempt < 3:
            print(f"   [Retrying Retriever] Attempt {attempt} failed similarity threshold. Retrying...")
            return "retriever"
            
    print("   [Passing to Generator] Retrieval complete.")
    return "generator"

# Node 3: Generator
def generator_node(state: AgentState) -> AgentState:
    mode = state["failure_mode"]
    docs = state.get("retrieved_docs", [])
    state["node_history"].append("generator")
    print("-> Running Generator Node...")
    
    if mode == "generator_revision_better":
        # Starts bad, revision will fix it
        response = "AgentEval products are covered under a lifetime unlimited warranty."
    else:
        # Default correct response
        doc_text = docs[0]["text"] if docs else ""
        response = f"Based on our policy: '{doc_text}', you can return items within 14 days."
        
    state["response"] = response
    return state

def route_generator(state: AgentState) -> str:
    mode = state.get("failure_mode")
    if mode in ("generator_revision_worse", "generator_revision_better"):
        return "generator_revision"
    return "critic"

# Node 3.5: Generator Revision (distinct node for reflection step)
def generator_revision_node(state: AgentState) -> AgentState:
    mode = state["failure_mode"]
    state["node_history"].append("generator_revision")
    print("-> Running Generator Revision Node (Self-Correction)...")
    
    if mode == "generator_revision_worse":
        # Original was good, revision makes it worse (hallucination)
        response = "AgentEval products are covered under a lifetime unlimited warranty."
    elif mode == "generator_revision_better":
        # Original was bad, revision makes it correct
        doc_text = state.get("retrieved_docs", [{}])[0].get("text", "")
        response = f"Based on our policy: '{doc_text}', you can return items within 14 days."
    else:
        response = state["response"]
        
    state["response"] = response
    return state

# Node 4: Critic
def critic_node(state: AgentState) -> AgentState:
    state["node_history"].append("critic")
    print("-> Running Critic Node...")
    
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
    
    workflow.add_node("planner", planner_node)
    workflow.add_node("retriever", retriever_node)
    workflow.add_node("generator", generator_node)
    workflow.add_node("generator_revision", generator_revision_node)
    workflow.add_node("critic", critic_node)
    
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "retriever")
    workflow.add_conditional_edges("retriever", route_retriever, {
        "retriever": "retriever",
        "generator": "generator"
    })
    workflow.add_conditional_edges("generator", route_generator, {
        "generator_revision": "generator_revision",
        "critic": "critic"
    })
    workflow.add_edge("generator_revision", "critic")
    workflow.add_edge("critic", END)
    
    return workflow.compile()

# Run entire calibration dataset
def run_calibration_dataset(db_path: str = "agenteval.db", fixtures_path: str = "examples/fixtures/retry_test_cases.yaml", version: str = "calib", mode: str = "replay"):
    from agenteval.sdk.callbacks import AgentEvalCallbackHandler
    
    fixtures = load_fixtures(fixtures_path)
    if not fixtures:
        print(f"Error: Fixtures file not found at {fixtures_path}")
        return
        
    agent = create_agent()
    print(f"Starting Retry/Reflection Calibration Run for version '{version}' of {len(fixtures)} conversations...")
    print(f"Database path: {db_path}\n")
    
    for i, case in enumerate(fixtures):
        session_id = f"session_{version}_{300 + i}"
        query = case["query"]
        category = case["category"]
        
        # In fixed version, retriever retry-failures and generator revision-worse failures are resolved
        runner_category = category
        if version == "fixed" and category in ("retrieval_retry_failure", "generator_revision_worse"):
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
            "retrieved_docs": None,
            "response": None,
            "critic_feedback": None,
            "session_id": session_id,
            "node_history": [],
            "retriever_attempts": 0
        }
        
        agent.invoke(state_input, config=config)
        print("-" * 50)
        
    print(f"\nCalibration dataset run completed. All traces saved to SQLite.")
    print(f"Triggering evaluation runs for version '{version}' (mode: {mode})...")
    from agenteval.benchmark.cli import evaluate_runs
    sessions = [f"session_{version}_{300 + i}" for i in range(len(fixtures))]
    res = evaluate_runs(sessions, db_path, version, mode=mode, fixtures_path=fixtures_path)
    print(f"Evaluation results for '{version}': Pass rate: {res.get('pass_rate', 0)*100:.1f}%, Causal Accuracy: {res.get('accuracy', 0)*100:.1f}%" if res.get('accuracy') is not None else f"Evaluation results for '{version}': Pass rate: {res.get('pass_rate', 0)*100:.1f}%")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Retry RAG Agent")
    parser.add_argument("--calibration", action="store_true", help="Run the retry calibration dataset")
    parser.add_argument("--fixed", action="store_true", help="Run in fixed mode (version 'fixed')")
    parser.add_argument("--db", type=str, default="agenteval.db", help="SQLite database path")
    parser.add_argument("--fixtures", type=str, default="examples/fixtures/retry_test_cases.yaml", help="Path to fixtures YAML")
    parser.add_argument("--mode", type=str, choices=["replay", "live"], default="replay", help="Evaluation mode (replay or live)")
    args = parser.parse_args()
    
    version = "fixed" if args.fixed else "calib"
    
    if args.calibration:
        run_calibration_dataset(db_path=args.db, fixtures_path=args.fixtures, version=version, mode=args.mode)
    else:
        parser.print_help()
