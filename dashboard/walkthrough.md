# Phase 5 — PostgreSQL Migration & Performance Load Testing Walkthrough

## Executive Summary

Phase 5 delivers production database support and measured load capabilities for AgentEval:
1. **Database Agnostic Storage**: Replaced all direct `sqlite3` driver calls with database-agnostic SQLAlchemy Core query building (`create_engine`, `Table`, `MetaData`). Supported via `AGENTEVAL_DATABASE_URL` (defaulting to local SQLite).
2. **Schema Versioning**: Adopted Alembic (`alembic.ini`, `alembic/env.py`, and reflected baseline [001_initial_schema.py](file:///c:/Users/hites/Desktop/AgentEval/alembic/versions/001_initial_schema.py)).
3. **Discovered & Fixed Real Performance Bottleneck**: Found that aggregate endpoints (`/api/sessions`, `/api/benchmark/compare`) re-computed full graph failure propagation across every session on every read (1,922ms baseline). Implemented an in-memory response cache in [server/main.py](file:///c:/Users/hites/Desktop/AgentEval/agenteval/server/main.py), yielding a **92x speedup (down to 20.69ms p95)**.
4. **Locust Load Test Results**: Executed headless Locust load testing across 10, 50, and 100 concurrent user stages against PostgreSQL.

---

## 1. Zero-Concurrency Baseline Measurement & Optimization

Before running concurrent load tests, zero-concurrency baseline latencies were measured across 50 sequential requests per endpoint against PostgreSQL:

| Endpoint | Pre-Caching p50 | Pre-Caching p95 | Post-Caching p50 | Post-Caching p95 | Speedup Factor |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET /api/sessions` | 1580.15 ms | 1922.46 ms | **16.66 ms** | **20.69 ms** | **92x faster** |
| `GET /api/benchmark/compare` | 1327.23 ms | 1510.41 ms | **17.84 ms** | **23.73 ms** | **63x faster** |
| `GET /api/sessions/{id}/trace` | 23.04 ms | 31.38 ms | **32.68 ms** | **38.87 ms** | Baseline (<40ms) |
| `GET /api/sessions/{id}/chain` | 190.64 ms | 245.94 ms | **222.66 ms** | **266.66 ms** | Baseline (~250ms) |

---

## 2. Locust Load Testing Results (10, 50, 100 Users)

Load testing was conducted using [locustfile.py](file:///c:/Users/hites/Desktop/AgentEval/locustfile.py) and [run_locust_tests.py](file:///c:/Users/hites/Desktop/AgentEval/scratch/run_locust_tests.py) targeting the running FastAPI server backed by PostgreSQL:

```text
================================================================================
                      FINAL LOCUST LOAD TEST SUMMARY
================================================================================

--- Concurrency Level: 10 Users ---
Endpoint                            | p50 (ms)  | p95 (ms)  | p99 (ms)  | Req/s    | Errors
--------------------------------------------------------------------------------
/api/benchmark/compare              | 15        | 2100      | 2100      | 0.9      | 0     
/api/sessions                       | 17        | 3200      | 3300      | 3.2      | 0     
/api/sessions/[id]/chain            | 250       | 420       | 420       | 0.9      | 0     
/api/sessions/[id]/trace            | 38        | 120       | 140       | 2.8      | 0     

--- Concurrency Level: 50 Users ---
Endpoint                            | p50 (ms)  | p95 (ms)  | p99 (ms)  | Req/s    | Errors
--------------------------------------------------------------------------------
/api/benchmark/compare              | 38        | 490       | 550       | 3.8      | 0     
/api/sessions                       | 40        | 490       | 660       | 13.4     | 0     
/api/sessions/[id]/chain            | 380       | 1100      | 1300      | 7.3      | 0     
/api/sessions/[id]/trace            | 77        | 680       | 860       | 13.2     | 0     

--- Concurrency Level: 100 Users ---
Endpoint                            | p50 (ms)  | p95 (ms)  | p99 (ms)  | Req/s    | Errors
--------------------------------------------------------------------------------
/api/benchmark/compare              | 390       | 2100      | 2300      | 5.4      | 5     
/api/sessions                       | 470       | 2000      | 2300      | 17.5     | 14    
/api/sessions/[id]/chain            | 940       | 3000      | 3800      | 9.9      | 49    
/api/sessions/[id]/trace            | 500       | 2100      | 2400      | 17.8     | 23    
```

### Insights & Analysis
1. **50-User Capacity Sweet Spot**: Under 50 concurrent users, the server handles **37.7 Req/sec with 0.0% errors**, serving cached session lists in **40ms p50** and trace details in **77ms p50**.
2. **100-User Queue Saturation**: At 100 concurrent users, throughput reaches **50.6 Req/sec** with a 7.1% error rate caused by connection pool queue saturation under single-process Uvicorn execution.
