# Task: Phase 5 — PostgreSQL Migration & Load Testing (COMPLETED)

## Phase 5 PART A — PostgreSQL Migration (COMPLETED)
- [x] Step A1: Add dependencies (`sqlalchemy`, `psycopg2-binary`, `alembic`, `locust`) to `requirements.txt` and `pyproject.toml`.
- [x] Step A2: Initialize Alembic configuration (`alembic.ini`, `alembic/env.py`).
- [x] Step A3: Reflect `agenteval.db` schema via SQLAlchemy to generate `alembic/versions/001_initial_schema.py`.
- [x] Step A4: Refactor `agenteval/sdk/storage.py` (`TraceStore`) to use database-agnostic SQLAlchemy Core with `AGENTEVAL_DATABASE_URL` support.
- [x] Step A5: Run full `pytest` suite against SQLite default backend (21/21 passed).
- [x] Step A6: Remove raw `sqlite3` calls across `server/main.py`, `cli.py`, and `who_when_adapter.py`.
- [x] Step A7: Re-run all 4 calibration datasets against Postgres backend to confirm 100% root-cause accuracy non-regression.
- [x] Step A8: Write `tests/test_postgres_concurrent_writes.py` and run multi-threaded concurrent write verification (200 nodes, 10 threads, 0% loss).

---

## Phase 5 PART B — Load Testing & Latency Optimization (COMPLETED)
- [x] Step B1: Measure zero-concurrency baseline latencies across all 4 target endpoints against PostgreSQL.
- [x] Step B2: Identify performance bottleneck (1,922ms baseline on `/api/sessions`) and implement in-memory response caching in `server/main.py`.
- [x] Step B3: Re-measure zero-concurrency baseline latencies (92x speedup on `/api/sessions` down to 20.69ms p95).
- [x] Step B4: Write `locustfile.py` and `scratch/run_locust_tests.py` load test harness.
- [x] Step B5: Execute Locust load tests at 10, 50, and 100 concurrent user stages against PostgreSQL.
- [x] Step B6: Document final load test findings and optimization results in `README.md` and `walkthrough.md`.
