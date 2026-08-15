import argparse
import json
import os
from typing import Any, Dict, List


def export_calibration_dataset(
    *,
    db_path: str,
    fixtures_path: str,
    output_path: str,
    mode: str = "replay",
    prefix: str = "",
    seed: int = 0,
) -> Dict[str, Any]:
    from agenteval.benchmark.cli import load_fixtures
    from agenteval.root_cause.engine import RootCauseEngine
    from agenteval.sdk.storage import TraceStore

    store = TraceStore(db_path=db_path)
    sessions = store.get_distinct_session_ids(user_id=None)
    if prefix:
        sessions = [s for s in sessions if prefix in s]
    fixtures = load_fixtures(fixtures_path)
    engine = RootCauseEngine(db_path=db_path, mode=mode)

    examples: List[Dict[str, Any]] = []
    try:
        for session_id in sessions:
            suffix = None
            try:
                import re
                match = re.search(r"(\d+)$", session_id)
                suffix = int(match.group(1)) if match else None
            except Exception:
                suffix = None
            if suffix is None:
                continue
            if "retry" in fixtures_path:
                idx = suffix - 300
            elif "branching" in fixtures_path:
                idx = suffix - 200
            else:
                idx = suffix - 100
            if not (0 <= idx < len(fixtures)):
                continue
            fixture = fixtures[idx]
            traces = store.get_session_traces(session_id)
            if not traces:
                continue
            diagnosed = engine.propagate_failures(traces)
            if not diagnosed:
                continue
            session_health = sum(node.get("raw_health", 0.0) for node in diagnosed) / len(diagnosed)
            examples.append(
                {
                    "case_id": fixture["id"],
                    "health": float(session_health),
                    "failure_label": 0 if fixture.get("expected_root_cause") == "none" else 1,
                }
            )
    finally:
        engine.store.close()
        store.close()

    payload = {
        "dataset": {
            "source": "benchmark_traces",
            "fixtures": fixtures_path,
            "mode": mode,
            "seed": seed,
            "record_count": len(sessions),
            "calibration_example_count": len(examples),
        },
        "examples": examples,
    }
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a benchmark-derived calibration dataset.")
    parser.add_argument("--db", default="agenteval.db", help="Path to SQLite database")
    parser.add_argument("--fixtures", default="examples/fixtures/test_cases.yaml", help="Path to benchmark fixtures")
    parser.add_argument("--output", default="artifacts/benchmark_calibration_dataset.json", help="Path to write the calibration dataset")
    parser.add_argument("--mode", default="replay", choices=["replay", "live"], help="Evaluation mode")
    parser.add_argument("--prefix", default="", help="Optional session prefix filter")
    parser.add_argument("--seed", type=int, default=0, help="Deterministic seed")
    args = parser.parse_args()

    result = export_calibration_dataset(
        db_path=args.db,
        fixtures_path=args.fixtures,
        output_path=args.output,
        mode=args.mode,
        prefix=args.prefix,
        seed=args.seed,
    )
    print(json.dumps(result["dataset"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
