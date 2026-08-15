"""Minimal LangGraph example that sends traces to a hosted AgentEval backend."""

from __future__ import annotations

import os
from typing import TypedDict

try:
    from langgraph.graph import END, StateGraph
except ImportError as exc:  # pragma: no cover - example script
    raise ImportError("Please install langgraph to run this example.") from exc

from agenteval import AgentEvalCallbackHandler


class AgentState(TypedDict):
    question: str
    answer: str


def planner(state: AgentState) -> AgentState:
    return {"question": state["question"], "answer": f"Plan: answer the question '{state['question']}'."}


def generator(state: AgentState) -> AgentState:
    return {
        "question": state["question"],
        "answer": f"Final answer for '{state['question']}': the workflow completed successfully.",
    }


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner)
    graph.add_node("generator", generator)
    graph.set_entry_point("planner")
    graph.add_edge("planner", "generator")
    graph.add_edge("generator", END)
    return graph


def main() -> None:
    api_url = os.environ["AGENTEVAL_API_URL"]
    api_key = os.environ["AGENTEVAL_API_KEY"]
    handler = AgentEvalCallbackHandler(
        session_id="hosted_langgraph_demo",
        api_url=api_url,
        api_key=api_key,
    )

    graph = build_graph().compile()
    result = graph.invoke(
        {"question": "How does hosted tracing work?", "answer": ""},
        config={"callbacks": [handler]},
    )
    print(result)


if __name__ == "__main__":  # pragma: no cover - example script
    main()

