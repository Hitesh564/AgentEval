import secrets
import time
import os
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

from agenteval.sdk.storage import TraceStore
from agenteval.sdk.database import resolve_database_url
from agenteval.root_cause.engine import RootCauseEngine
from agenteval.recommend.engine import RecommendationEngine
from agenteval.benchmark.cli import evaluate_runs

load_dotenv()

app = FastAPI(
    title="AgentEval API Dashboard Server",
    description="Backend server supporting AgentEval's diagnostic dashboard, powered by SQLAlchemy-backed traces."
)

def _parse_cors_origins(value: Optional[str]) -> List[str]:
    raw = (value or "").strip()
    if not raw:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    origins = [origin.strip() for origin in raw.split(",")]
    return [origin for origin in origins if origin]


_cors_origins = _parse_cors_origins(os.environ.get("AGENTEVAL_CORS_ORIGINS"))
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database store and engines
_running_on_railway = bool(
    os.environ.get("RAILWAY_ENVIRONMENT")
    or os.environ.get("RAILWAY_PROJECT_ID")
    or os.environ.get("RAILWAY_SERVICE_ID")
)
database_url = resolve_database_url(allow_sqlite_fallback=not _running_on_railway)
store = TraceStore(database_url=database_url)
rc_engine = RootCauseEngine(db_path=database_url)
rec_engine = RecommendationEngine()

def get_current_user_id(x_api_key: Optional[str] = Header(None)) -> str:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header is missing")
    user_id = store.resolve_user_id(x_api_key)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return user_id

class SessionSummary(BaseModel):
    session_id: str
    score: float
    passed: bool
    failure_tag: Optional[str] = None
    timestamp: str


class TraceNodeIn(BaseModel):
    session_id: str
    node_id: str
    node_type: str
    timestamp_start: str
    timestamp_end: str
    inputs: Optional[Any] = None
    outputs: Optional[Any] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Any] = None
    tool_result: Optional[Any] = None
    retrieved_docs: Optional[Any] = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    parent_node_ids: List[str] = Field(default_factory=list)
    attempt_number: int = 1
    parent_session_id: Optional[str] = None
    user_id: Optional[str] = None

    @field_validator("parent_node_ids", mode="before")
    @classmethod
    def _normalize_parent_node_ids(cls, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        raise ValueError("parent_node_ids must be a list")


class TraceBatchIn(BaseModel):
    traces: List[TraceNodeIn]


class ApiKeyCreateRequest(BaseModel):
    user_id: str


class ApiKeyCreateResponse(BaseModel):
    user_id: str
    api_key: str

# In-memory response cache for expensive aggregate endpoints
RESPONSE_CACHE: Dict[str, Dict[str, Any]] = {
    "sessions": {}, # user_id -> (timestamp, data)
    "compare": {},  # user_id -> (timestamp, data)
}
CACHE_TTL_SECONDS = 300 # 5 minutes TTL

def get_cached_response(cache_type: str, user_id: str) -> Optional[Any]:
    entry = RESPONSE_CACHE.get(cache_type, {}).get(user_id)
    if entry:
        ts, data = entry
        if time.time() - ts < CACHE_TTL_SECONDS:
            return data
    return None

def set_cached_response(cache_type: str, user_id: str, data: Any):
    if cache_type not in RESPONSE_CACHE:
        RESPONSE_CACHE[cache_type] = {}
    RESPONSE_CACHE[cache_type][user_id] = (time.time(), data)

def invalidate_response_cache(user_id: Optional[str] = None):
    if user_id:
        RESPONSE_CACHE["sessions"].pop(user_id, None)
        RESPONSE_CACHE["compare"].pop(user_id, None)
    else:
        RESPONSE_CACHE["sessions"].clear()
        RESPONSE_CACHE["compare"].clear()

@app.get("/api/health")
def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "ok",
        "service": "agenteval-server",
        "database_backend": store.backend_name,
        "database_configured": bool(os.environ.get("AGENTEVAL_DATABASE_URL")),
    }


def _ingest_trace_payload(payload: TraceNodeIn, user_id: str) -> Dict[str, Any]:
    if payload.user_id is not None and payload.user_id != user_id:
        raise HTTPException(status_code=400, detail="Payload user_id does not match authenticated user")

    trace_node = payload.model_dump()
    trace_node["user_id"] = user_id
    store.save_trace_node(trace_node)
    return {
        "status": "accepted",
        "session_id": payload.session_id,
        "node_id": payload.node_id,
        "user_id": user_id,
    }


@app.post("/api/v1/traces")
def ingest_trace(payload: TraceNodeIn, user_id: str = Depends(get_current_user_id)) -> Dict[str, Any]:
    """Ingests a single completed trace node for the authenticated user."""
    return _ingest_trace_payload(payload, user_id)


@app.post("/api/v1/traces/batch")
def ingest_trace_batch(payload: TraceBatchIn, user_id: str = Depends(get_current_user_id)) -> Dict[str, Any]:
    """Ingests a batch of completed trace nodes for the authenticated user."""
    accepted = [_ingest_trace_payload(trace_node, user_id) for trace_node in payload.traces]
    return {"status": "accepted", "count": len(accepted), "traces": accepted}


@app.post("/api/v1/admin/api-keys", response_model=ApiKeyCreateResponse)
def create_api_key(payload: ApiKeyCreateRequest, x_admin_key: Optional[str] = Header(None)) -> ApiKeyCreateResponse:
    """Creates a new API key using a bootstrap admin token."""
    bootstrap_key = os.environ.get("AGENTEVAL_ADMIN_BOOTSTRAP_KEY")
    if not bootstrap_key:
        raise HTTPException(status_code=503, detail="Admin bootstrap key is not configured")
    if x_admin_key != bootstrap_key:
        raise HTTPException(status_code=401, detail="Invalid admin bootstrap key")

    api_key = secrets.token_urlsafe(32)
    store.create_user(payload.user_id, api_key)
    return ApiKeyCreateResponse(user_id=payload.user_id, api_key=api_key)

@app.get("/api/sessions", response_model=List[SessionSummary])
def list_sessions(user_id: str = Depends(get_current_user_id)) -> List[SessionSummary]:
    """
    Returns list of all traced sessions for Screen 1 (Conversation List).
    Queries real session traces and computes actual failure classifications.
    """
    cached = get_cached_response("sessions", user_id)
    if cached is not None:
        return cached

    sessions_info = store.list_session_summaries(user_id=user_id)
    summaries = []
    for info in sessions_info:
        session_id = info["session_id"]
        timestamp = info["start_time"]
        nodes = store.get_session_traces(session_id, user_id=user_id)
        if not nodes:
            continue
            
        diagnosed = rc_engine.propagate_failures(nodes)
        
        # Calculate session score as average of all nodes' raw health
        avg_score = sum(n["raw_health"] for n in diagnosed) / len(diagnosed)
        
        # Check if there is an active root cause or co-originator failure
        root_cause = next((n for n in diagnosed if n["is_root_cause"]), None)
        co_originator = next((n for n in diagnosed if n.get("is_co_originator")), None)
        passed = root_cause is None and co_originator is None
        
        failure_node = root_cause or co_originator
        failure_tag = failure_node["failure_type"].value if failure_node and failure_node["failure_type"] else None
        
        summaries.append(SessionSummary(
            session_id=session_id,
            score=round(avg_score, 2),
            passed=passed,
            failure_tag=failure_tag,
            timestamp=timestamp
        ))
        
    set_cached_response("sessions", user_id, summaries)
    return summaries

@app.get("/api/sessions/{session_id}/trace")
def get_session_trace(session_id: str, user_id: str = Depends(get_current_user_id)) -> Dict[str, Any]:
    """
    Returns full node trace and root cause evaluation for Screen 2 (Trace Detail).
    Integrates evidence extraction and recommendations in real time.
    """
    nodes = store.get_session_traces(session_id, user_id=user_id)
    if not nodes:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
    diagnosed = rc_engine.propagate_failures(nodes)
    
    # Calculate overall session score
    avg_score = sum(n["raw_health"] for n in diagnosed) / len(diagnosed)
    root_cause = next((n for n in diagnosed if n["is_root_cause"]), None)
    passed = root_cause is None and not any(n.get("is_co_originator") for n in diagnosed)
    
    root_cause_summary = None
    if root_cause:
        root_cause_summary = {
            "responsible_agent": root_cause["node_type"],
            "responsible_step": root_cause["node_id"],
            "node_id": root_cause["node_id"],
            "node_type": root_cause["node_type"],
            "failure_type": root_cause["failure_type"].value if root_cause.get("failure_type") else None,
            "raw_health": round(root_cause["raw_health"], 2),
            "overall_health": round(root_cause.get("overall_health", root_cause["raw_health"]), 2),
            "weakest_dimension": root_cause.get("weakest_dimension"),
            "weakest_dimension_score": round(root_cause.get("weakest_dimension_score", 0.0), 2) if root_cause.get("weakest_dimension_score") is not None else None,
            "attribution_score": round(root_cause.get("attribution_score", 0.0), 2),
            "causal_origin_score": round(root_cause.get("causal_origin_score", root_cause.get("attribution_score", 0.0)), 2),
            "candidate_separation": round(root_cause.get("candidate_separation", 0.0), 2),
            "calibrated_probability": round(root_cause.get("calibrated_probability"), 2) if root_cause.get("calibrated_probability") is not None else None,
            "raw_score": round(root_cause.get("raw_score", root_cause.get("candidate_separation", 0.0)), 2),
            "calibration_method": root_cause.get("calibration_method"),
            "calibration_status": root_cause.get("calibration_status"),
            "calibration_version": root_cause.get("calibration_version"),
            "confidence": round(root_cause["confidence"], 2) if root_cause.get("confidence") is not None else None,
            "confidence_calibrated": root_cause.get("confidence_calibrated", False),
            "confidence_tier": root_cause["confidence_tier"],
            "ranked_candidates": root_cause.get("ranked_candidates", []),
        }
        
    co_originators = [
        {"node_id": n["node_id"], "raw_health": round(n["raw_health"], 2)}
        for n in diagnosed if n.get("is_co_originator")
    ]
    if not co_originators:
        co_originators = None
        
    confidence_tier = diagnosed[0]["confidence_tier"] if diagnosed else "high"
    
    output_nodes = []
    for node in diagnosed:
        node_id = node["node_id"]
        
        # Fetch real recommendation recommendations if the node failed (root cause or co-originator)
        node_recs = []
        if (node["is_root_cause"] or node.get("is_co_originator")) and node["failure_type"]:
            node_recs = rec_engine.generate_recommendations(node["failure_type"], node["evidence"])
            
        output_nodes.append({
            "node_id": node_id,
            "node_type": node["node_type"],
            "raw_health": round(node["raw_health"], 2),
            "adjusted_health": round(node["adjusted_health"], 2),
            "overall_health": round(node.get("overall_health", node["raw_health"]), 2),
            "metric_scores": node.get("metric_scores", {}),
            "weakest_dimension": node.get("weakest_dimension"),
            "weakest_dimension_score": node.get("weakest_dimension_score"),
            "failed_dimensions": node.get("failed_dimensions", []),
            "evaluation_status": node.get("evaluation_status", "complete"),
            "is_root_cause": node["is_root_cause"],
            "is_inherited_degradation": node.get("is_inherited_degradation", False),
            "is_co_originator": node.get("is_co_originator", False),
            "inherited_from_node_ids": node.get("inherited_from_node_ids", []),
            "children_node_ids": node.get("children_node_ids", []),
            "parent_node_ids": node["parent_node_ids"],
            "failure_type": node["failure_type"].value if node.get("failure_type") else None,
            "attribution_score": round(node.get("attribution_score", 0.0), 2),
            "causal_origin_score": round(node.get("causal_origin_score", node.get("attribution_score", 0.0)), 2),
            "attribution_evidence": node.get("attribution_evidence", {}),
            "candidate_separation": round(node.get("candidate_separation", 0.0), 2),
            "calibrated_probability": round(node.get("calibrated_probability", 0.0), 2) if node.get("calibrated_probability") is not None else None,
            "raw_score": round(node.get("raw_score", node.get("candidate_separation", 0.0)), 2),
            "calibration_method": node.get("calibration_method"),
            "calibration_status": node.get("calibration_status"),
            "calibration_version": node.get("calibration_version"),
            "evidence": node["evidence"],
            "confidence": round(node["confidence"], 2) if node.get("confidence") is not None else None,
            "confidence_calibrated": node.get("confidence_calibrated", False),
            "confidence_tier": node.get("confidence_tier", "high"),
            "recommendations": node_recs
        })

    return {
        "session_id": session_id,
        "overall_score": round(avg_score, 2),
        "passed": passed,
        "root_cause": root_cause_summary,
        "co_originators": co_originators,
        "confidence_tier": confidence_tier,
        "nodes": output_nodes
    }

@app.get("/api/sessions/{session_id}/profiles")
def get_session_profiles(session_id: str, user_id: str = Depends(get_current_user_id)) -> List[Dict[str, Any]]:
    """
    Returns all semantic node profiles inferred for the given session.
    """
    return store.list_session_profiles(session_id)

@app.get("/api/sessions/{session_id}/chain")
def get_session_chain(session_id: str, user_id: str = Depends(get_current_user_id)) -> Dict[str, Any]:
    """
    Returns full linked chain for a session, each session's own overall health,
    and the cross-session root-cause determination for Screen 4 (Chain Detail).
    """
    from agenteval.root_cause.cross_session import CrossSessionEngine
    engine = CrossSessionEngine(db_path=database_url)
    try:
        return engine.diagnose_chain(session_id, user_id=user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/benchmark/compare")
def compare_versions(user_id: str = Depends(get_current_user_id)) -> Dict[str, Any]:
    """
    Returns benchmark comparison summary for Screen 3 (Benchmark/Regression Report).
    Calculates averages dynamically from the calibration session sets in storage.
    """
    cached = get_cached_response("compare", user_id)
    if cached is not None:
        return cached

    sessions = store.get_distinct_session_ids(user_id=user_id)
    
    # Filter A: 'calib' sessions
    sessions_a = [s for s in sessions if "calib" in s]
    if not sessions_a:
        raise HTTPException(status_code=400, detail="No calibration traces found. Run agent --calibration.")
        
    # Filter B: 'fixed' sessions
    sessions_b = [s for s in sessions if "fixed" in s]
    if not sessions_b:
        raise HTTPException(
            status_code=400, 
            detail="No 'fixed' runs found in database. Run fixed agent calibration (e.g. `python examples/simple_rag_agent.py --calibration --fixed`) to generate runs for comparison."
        )
        
    # Import and run calculation logic
    res_a = evaluate_runs(sessions_a, database_url, "calib", user_id=user_id)
    res_b = evaluate_runs(sessions_b, database_url, "fixed", user_id=user_id)

    
    # Determine dynamic overall verdict
    better = 0
    worse = 0
    for k in ["instruction_following", "retrieval_quality", "tool_accuracy"]:
        if res_b["averages"][k] > res_a["averages"][k] + 0.01:
            better += 1
        elif res_b["averages"][k] < res_a["averages"][k] - 0.01:
            worse += 1
    for k in ["latency", "hallucination_rate"]:
        if res_b["averages"][k] < res_a["averages"][k] - 0.01:
            better += 1
        elif res_b["averages"][k] > res_a["averages"][k] + 0.01:
            worse += 1
            
    # Confidence calculation
    sum_improved = 0.0
    sum_degraded = 0.0
    max_lat = max(0.5, res_a["averages"]["latency"], res_b["averages"]["latency"])
    
    for k in ["instruction_following", "retrieval_quality", "tool_accuracy"]:
        d = res_b["averages"][k] - res_a["averages"][k]
        if d > 0.01:
            sum_improved += d
        elif d < -0.01:
            sum_degraded += abs(d)
            
    for k in ["hallucination_rate"]:
        d = res_a["averages"][k] - res_b["averages"][k]
        if d > 0.01:
            sum_improved += d
        elif d < -0.01:
            sum_degraded += abs(d)
            
    # Latency (lower is better)
    lat_d = (res_a["averages"]["latency"] - res_b["averages"]["latency"]) / max_lat
    if lat_d > 0.01:
        sum_improved += lat_d
    elif lat_d < -0.01:
        sum_degraded += abs(lat_d)
        
    total_diff = sum_improved + sum_degraded
    confidence = 0.0
    if total_diff > 0:
        if better > worse:
            confidence = sum_improved / (total_diff + 0.05)
        elif worse > better:
            confidence = sum_degraded / (total_diff + 0.05)
            
    confidence = max(0.0, min(1.0, confidence))

    if better > worse:
        verdict = "Version B is BETTER"
    elif worse > better:
        verdict = "Version A is BETTER"
    else:
        verdict = "Versions are COMPARABLE"

    metrics_list = []
    for metric_name, key in [
        ("Instruction Following", "instruction_following"),
        ("Hallucination Rate", "hallucination_rate"),
        ("Tool-Calling Accuracy", "tool_accuracy"),
        ("Retrieval Quality", "retrieval_quality"),
        ("Average Latency (s)", "latency")
    ]:
        val_a = res_a["averages"][key]
        val_b = res_b["averages"][key]
        delta = val_b - val_a
        
        # Directional delta status
        if key in ("latency", "hallucination_rate"):
            status = "IMPROVED" if delta < -0.01 else ("DEGRADED" if delta > 0.01 else "UNCHANGED")
        else:
            status = "IMPROVED" if delta > 0.01 else ("DEGRADED" if delta < -0.01 else "UNCHANGED")
            
        metrics_list.append({
            "metric": metric_name,
            "val_a": round(val_a, 2),
            "val_b": round(val_b, 2),
            "delta": round(delta, 2),
            "status": status
        })
        
    comparison_res = {
        "version_a": "v1.0.0-baseline ('calib')",
        "version_b": "v1.0.1-fixed-retrieval ('fixed')",
        "overall_verdict": f"Overall Verdict: {verdict} (confidence: {confidence*100:.1f}%)",
        "metrics": metrics_list,
        "accuracy_a": res_a["accuracy"],
        "accuracy_b": res_b["accuracy"],
        "pass_rate_a": res_a["pass_rate"],
        "pass_rate_b": res_b["pass_rate"],
        "total_runs": res_a["total_runs"]
    }
    set_cached_response("compare", user_id, comparison_res)
    return comparison_res



