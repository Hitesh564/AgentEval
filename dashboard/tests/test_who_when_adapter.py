from agenteval.adapters.who_when_adapter import (
    aggregate_records,
    evaluate_case,
    WhoWhenEvaluationRecord,
)


class FakeStore:
    def __init__(self):
        self.traces = []
        self.links = []
        self.deleted = []

    def save_trace_node(self, trace_node):
        self.traces.append(trace_node)

    def save_session_link(self, session_id, previous_session, link_reason=None, user_id=None):
        self.links.append((session_id, previous_session))

    def delete_case_traces(self, user_id, q_id):
        self.deleted.append((user_id, q_id))


class FakeCrossEngine:
    def diagnose_chain(self, session_id, user_id=None):
        return {
            "chain": [
                {"session_id": "session_1_step1_assistant", "status": "healthy", "root_cause_node": None},
                {"session_id": session_id, "status": "root-cause", "root_cause_node": "step_3"},
            ],
            "root_cause_session": session_id,
            "co_contributing_sessions": [],
            "verdict": "failed",
        }


def test_who_when_case_reports_agent_and_step():
    item = {
        "question_ID": "1",
        "question": "Question?",
        "mistake_agent": "assistant",
        "mistake_step": "3",
        "history": [
            {"role": "human", "content": "Hi"},
            {"role": "assistant", "content": "First answer"},
            {"role": "human", "content": "More"},
            {"role": "assistant", "content": "Wrong answer"},
        ],
    }
    store = FakeStore()
    engine = FakeCrossEngine()

    record = evaluate_case(item, store=store, cross_engine=engine, user_id="u")
    assert record.case_id == "1"
    assert record.agent_correct is True
    assert record.step_correct is True
    assert record.exact_match is True
    assert record.predicted_step == "step_3"
    assert store.links


def test_who_when_aggregate_records_includes_step_metrics():
    records = [
        WhoWhenEvaluationRecord(
            case_id="1",
            expected_agent="assistant",
            predicted_agent="assistant",
            expected_step="assistant",
            predicted_step="assistant",
            agent_correct=True,
            step_correct=True,
            exact_match=True,
            top_k_agents=["assistant"],
        ),
        WhoWhenEvaluationRecord(
            case_id="2",
            expected_agent="orchestrator",
            predicted_agent="assistant",
            expected_step="step_2",
            predicted_step="step_4",
            agent_correct=False,
            step_correct=False,
            exact_match=False,
            top_k_agents=["assistant", "orchestrator"],
        ),
    ]

    summary = aggregate_records(records)
    assert summary["count"] == 2
    assert summary["agent_accuracy"] == 0.5
    assert summary["step_accuracy"] == 0.5
    assert summary["exact_match"] == 0.5
    assert summary["top_k_agent_accuracy"] == 1.0
    assert summary["assumptions"]


def test_who_when_prediction_is_invariant_to_ground_truth_label_changes():
    base_item = {
        "question_ID": "1",
        "question": "Question?",
        "mistake_agent": "assistant",
        "mistake_step": "assistant",
        "history": [
            {"role": "human", "content": "Hi"},
            {"role": "assistant", "content": "First answer"},
            {"role": "human", "content": "More"},
            {"role": "assistant", "content": "Wrong answer"},
        ],
    }
    changed_labels = dict(base_item)
    changed_labels["mistake_agent"] = "orchestrator"
    changed_labels["mistake_step"] = "step_99"

    base_record = evaluate_case(base_item, store=FakeStore(), cross_engine=FakeCrossEngine(), user_id="u")
    changed_record = evaluate_case(changed_labels, store=FakeStore(), cross_engine=FakeCrossEngine(), user_id="u")

    assert base_record.predicted_agent == changed_record.predicted_agent
    assert base_record.predicted_step == changed_record.predicted_step
    assert base_record.agent_correct != changed_record.agent_correct
