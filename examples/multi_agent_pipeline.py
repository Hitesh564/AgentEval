import os
import sys
import time
import argparse
import yaml
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

# Add workspace to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END

# Import SDK
from agenteval.sdk.callbacks import AgentEvalCallbackHandler

# Define State
class AgentState(Dict[str, Any]):
    query: str
    retrieval_text: Optional[str]
    scoring_text: Optional[str]
    failure_mode: str
    response: Optional[str]
    critic_feedback: Optional[str]
    session_id: str
    node_history: List[str]

# ----------------- AGENT 1: RETRIEVAL AGENT -----------------

def retrieval_planner(state: AgentState) -> AgentState:
    state["node_history"].append("retrieval_planner")
    print("  -> Running Retrieval Planner...")
    state["plan"] = "c. Choose cancel option. d. Check refund eligibility."
    state["response"] = "c. Choose cancel option. d. Check refund eligibility."
    return state

def retrieval_retriever(state: AgentState) -> AgentState:
    state["node_history"].append("retrieval_retriever")
    print("  -> Running Retrieval Retriever...")
    mode = state.get("failure_mode", "none")
    
    # Retrieval failure / co-contribution / borderline
    if mode in ("retrieval_agent", "co_contribution"):
        similarity = 0.30
        docs = "General FAQ: Refund policy is 14 days. Score is rejected."
    elif mode == "co_contribution_borderline":
        similarity = 0.16
        docs = "General FAQ: Refund policy is 14 days. Score is rejected."
    else:
        similarity = 0.95
        docs = "Standard Policy: Refund policy allows 30 days. Score is approved."

    state["retrieved_docs"] = [{"text": docs, "similarity_score": similarity}]
    state["response"] = docs
    return state

def retrieval_generator(state: AgentState) -> AgentState:
    state["node_history"].append("retrieval_generator")
    print("  -> Running Retrieval Generator...")
    return state

def create_retrieval_agent():
    workflow = StateGraph(AgentState)
    workflow.add_node("retrieval_planner", retrieval_planner)
    workflow.add_node("retrieval_retriever", retrieval_retriever)
    workflow.add_node("retrieval_generator", retrieval_generator)
    
    workflow.set_entry_point("retrieval_planner")
    workflow.add_edge("retrieval_planner", "retrieval_retriever")
    workflow.add_edge("retrieval_retriever", "retrieval_generator")
    workflow.add_edge("retrieval_generator", END)
    return workflow.compile()


# ----------------- AGENT 2: SCORING AGENT -----------------

def scoring_retriever(state: AgentState) -> AgentState:
    state["node_history"].append("scoring_retriever")
    print("  -> Running Scoring Retriever...")
    ret_text = state.get("retrieval_text", "")
    
    # Check if retrieval text came from a failed retriever
    if "FAQ" in ret_text:
        # Inherited degradation similarity score
        similarity = 0.30
        if "borderline" in state.get("failure_mode", ""):
            similarity = 0.16
    else:
        similarity = 0.95
        
    state["retrieved_docs"] = [{"text": ret_text, "similarity_score": similarity}]
    return state

def scoring_generator(state: AgentState) -> AgentState:
    state["node_history"].append("scoring_generator")
    print("  -> Running Scoring Generator...")
    mode = state.get("failure_mode", "none")
    
    # Scoring agent fail independently
    if mode in ("scoring_agent", "co_contribution", "co_contribution_borderline"):
        state["response"] = "Refund policy is 14 days. Score: 0.10. 10 is greater than 15."
    else:
        state["response"] = "Refund policy allows 30 days. Score: 0.95. Approved."
        
    return state

def create_scoring_agent():
    workflow = StateGraph(AgentState)
    workflow.add_node("scoring_retriever", scoring_retriever)
    workflow.add_node("scoring_generator", scoring_generator)
    
    workflow.set_entry_point("scoring_retriever")
    workflow.add_edge("scoring_retriever", "scoring_generator")
    workflow.add_edge("scoring_generator", END)
    return workflow.compile()


# ----------------- AGENT 3: CONDUCTOR AGENT -----------------

def conductor_generator(state: AgentState) -> AgentState:
    state["node_history"].append("conductor_generator")
    print("  -> Running Conductor Generator...")
    mode = state.get("failure_mode", "none")
    scoring_text = state.get("scoring_text", "")
    
    if mode == "conductor_agent":
        state["response"] = "Invalid answer. 10 is greater than 15."
    elif "Score: 0.10" in scoring_text:
        state["response"] = "cancellation plan: refund is rejected."
    else:
        state["response"] = "cancellation plan: refund is approved."
        
    return state

def conductor_critic(state: AgentState) -> AgentState:
    state["node_history"].append("conductor_critic")
    print("  -> Running Conductor Critic...")
    mode = state.get("failure_mode", "none")
    response = state.get("response", "")
    
    if mode in ("conductor_agent", "retrieval_agent", "scoring_agent", "co_contribution", "co_contribution_borderline"):
        state["critic_feedback"] = "Fail. Incorrect response."
    else:
        state["critic_feedback"] = "Pass. Response is correct."
        
    return state

def create_conductor_agent():
    workflow = StateGraph(AgentState)
    workflow.add_node("conductor_generator", conductor_generator)
    workflow.add_node("conductor_critic", conductor_critic)
    
    workflow.set_entry_point("conductor_generator")
    workflow.add_edge("conductor_generator", "conductor_critic")
    workflow.add_edge("conductor_critic", END)
    return workflow.compile()


# ----------------- PIPELINE CALIBRATION RUNNER -----------------

def load_fixtures(path: str) -> List[Dict[str, Any]]:
    with open(path, "r") as f:
        return yaml.safe_load(f)

def run_calibration_dataset(db_path: str = "agenteval.db", fixtures_path: str = "examples/fixtures/multi_agent_test_cases.yaml", version: str = "calib", mode: str = "replay", batch: Optional[int] = None):
    fixtures = load_fixtures(fixtures_path)
    if not fixtures:
        print(f"Error: Fixtures file not found at {fixtures_path}")
        return
        
    if batch == 1:
        fixtures = fixtures[:5]
    elif batch == 2:
        fixtures = fixtures[5:]
        
    ret_agent = create_retrieval_agent()
    scr_agent = create_scoring_agent()
    con_agent = create_conductor_agent()
    
    print(f"Starting Multi-Agent Calibration Run for version '{version}' of {len(fixtures)} cases...")
    print(f"Database path: {db_path}\n")
    
    for i, case in enumerate(fixtures):
        case_num = int(case['id'].split('_')[-1])
        suffix = 400 + case_num - 1
        print(f"Running case {i+1}/{len(fixtures)}: ID={case['id']} | Category={case['injected_fault_in']} | Session_base={version}_{suffix}")
        
        session_id_ret = f"session_{version}_ret_{suffix}"
        session_id_scr = f"session_{version}_scr_{suffix}"
        session_id_con = f"session_{version}_con_{suffix}"
        
        query = case["query"]
        fault_in = case["injected_fault_in"]
        
        # In fixed mode, retrieval and scoring faults are resolved/fixed
        runner_category = fault_in
        if version == "fixed":
            if fault_in in ("retrieval_agent", "scoring_agent", "co_contribution", "co_contribution_borderline"):
                runner_category = "none"
                
        # 1. Run Retrieval Agent
        handler_ret = AgentEvalCallbackHandler(session_id=session_id_ret, db_path=db_path)
        state_ret = {
            "query": query,
            "retrieval_text": None,
            "scoring_text": None,
            "failure_mode": runner_category,
            "response": None,
            "critic_feedback": None,
            "session_id": session_id_ret,
            "node_history": []
        }
        res_ret = ret_agent.invoke(state_ret, config={"callbacks": [handler_ret]})
        ret_output = res_ret.get("response") or ""
        
        # 2. Run Scoring Agent
        handler_scr = AgentEvalCallbackHandler(session_id=session_id_scr, db_path=db_path, parent_session_id=session_id_ret)
        state_scr = {
            "query": query,
            "retrieval_text": ret_output,
            "scoring_text": None,
            "failure_mode": runner_category,
            "response": None,
            "critic_feedback": None,
            "session_id": session_id_scr,
            "node_history": []
        }
        res_scr = scr_agent.invoke(state_scr, config={"callbacks": [handler_scr]})
        scr_output = res_scr.get("response") or ""
        
        # 3. Run Conductor Agent
        handler_con = AgentEvalCallbackHandler(session_id=session_id_con, db_path=db_path, parent_session_id=session_id_scr)
        state_con = {
            "query": query,
            "retrieval_text": None,
            "scoring_text": scr_output,
            "failure_mode": runner_category,
            "response": None,
            "critic_feedback": None,
            "session_id": session_id_con,
            "node_history": []
        }
        con_agent.invoke(state_con, config={"callbacks": [handler_con]})
        
        print("-" * 50)
        
    print(f"\nCalibration dataset run completed. Triggering evaluation...")
    from agenteval.benchmark.cli import evaluate_runs
    sessions = [f"session_{version}_con_{400 + int(case['id'].split('_')[-1]) - 1}" for case in fixtures]
    res = evaluate_runs(sessions, db_path, version, mode=mode, fixtures_path=fixtures_path)
    
    if res.get("accuracy") is not None:
         print(f"Evaluation results for '{version}': Chain Pass Rate: {res.get('pass_rate', 0)*100:.1f}%, Causal Accuracy: {res.get('accuracy', 0)*100:.1f}%")
    else:
         print(f"Evaluation results for '{version}': Chain Pass Rate: {res.get('pass_rate', 0)*100:.1f}%, Causal Accuracy: [NO DATA]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Multi-Agent Pipeline Agent")
    parser.add_argument("--calibration", action="store_true")
    parser.add_argument("--fixed", action="store_true")
    parser.add_argument("--db", type=str, default="agenteval.db")
    parser.add_argument("--fixtures", type=str, default="examples/fixtures/multi_agent_test_cases.yaml")
    parser.add_argument("--mode", type=str, choices=["replay", "live"], default="replay")
    parser.add_argument("--batch", type=int, choices=[1, 2], default=None)
    args = parser.parse_args()
    
    version = "fixed" if args.fixed else "calib"
    if args.calibration:
        run_calibration_dataset(db_path=args.db, fixtures_path=args.fixtures, version=version, mode=args.mode, batch=args.batch)
