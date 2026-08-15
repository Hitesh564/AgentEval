import type { 
  SessionSummary, 
  SessionDetail, 
  ChainDetail, 
  BenchmarkReport, 
  ApiHealthResponse 
} from '../types';
import { DEMO_SESSIONS, DEMO_SESSION_DETAILS, DEMO_BENCHMARK_REPORT } from '../data/demoData';

export const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function fetchHealth(): Promise<ApiHealthResponse> {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) throw new ApiError(`Health check failed (${res.status})`, res.status);
    return await res.json();
  } catch (err: any) {
    throw new ApiError(err.message || "Unable to connect to AgentEval backend server");
  }
}

export async function fetchSessions(apiKey: string | null, isDemo: boolean = false): Promise<SessionSummary[]> {
  if (isDemo) {
    return DEMO_SESSIONS;
  }
  if (!apiKey) {
    throw new ApiError("API Key is required to fetch session traces", 401);
  }

  const res = await fetch(`${API_BASE}/api/sessions`, {
    headers: { "X-API-Key": apiKey }
  });

  if (!res.ok) {
    const text = await res.text();
    let msg = `Failed to load sessions (${res.status})`;
    try {
      const data = JSON.parse(text);
      if (data.detail) msg = data.detail;
    } catch (_) {}
    throw new ApiError(msg, res.status);
  }

  return await res.json();
}

export async function fetchSessionTrace(sessionId: string, apiKey: string | null, isDemo: boolean = false): Promise<SessionDetail> {
  if (isDemo || sessionId.startsWith("demo_")) {
    const detail = DEMO_SESSION_DETAILS[sessionId] || DEMO_SESSION_DETAILS["demo_trace_001"];
    return detail;
  }
  if (!apiKey) {
    throw new ApiError("API Key is required to fetch trace details", 401);
  }

  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/trace`, {
    headers: { "X-API-Key": apiKey }
  });

  if (!res.ok) {
    const text = await res.text();
    let msg = `Failed to load trace details (${res.status})`;
    try {
      const data = JSON.parse(text);
      if (data.detail) msg = data.detail;
    } catch (_) {}
    throw new ApiError(msg, res.status);
  }

  return await res.json();
}

export async function fetchSessionChain(sessionId: string, apiKey: string | null, isDemo: boolean = false): Promise<ChainDetail | null> {
  if (isDemo || sessionId.startsWith("demo_")) {
    return {
      chain_id: `chain_${sessionId}`,
      chain: [
        { session_id: sessionId, overall_health: 0.42, passed: false, root_cause_node_id: "tool_search_internal_db" }
      ],
      cross_session_root_cause: {
        session_id: sessionId,
        node_id: "tool_search_internal_db",
        node_type: "Tool",
        failure_type: "tool_timeout"
      }
    };
  }
  if (!apiKey) return null;

  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/chain`, {
      headers: { "X-API-Key": apiKey }
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (_) {
    return null;
  }
}

export async function fetchBenchmarkCompare(apiKey: string | null, isDemo: boolean = false): Promise<BenchmarkReport> {
  if (isDemo) {
    return DEMO_BENCHMARK_REPORT;
  }
  if (!apiKey) {
    throw new ApiError("API Key is required to run benchmark comparison", 401);
  }

  const res = await fetch(`${API_BASE}/api/benchmark/compare`, {
    headers: { "X-API-Key": apiKey }
  });

  if (!res.ok) {
    const text = await res.text();
    let msg = "Failed to run benchmark comparison";
    try {
      const data = JSON.parse(text);
      if (data.detail) msg = data.detail;
    } catch (_) {}
    throw new ApiError(msg, res.status);
  }

  return await res.json();
}

export async function createAdminApiKey(adminBootstrapKey: string, userId: string): Promise<{ user_id: string; api_key: string }> {
  const res = await fetch(`${API_BASE}/api/v1/admin/api-keys`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Key": adminBootstrapKey
    },
    body: JSON.stringify({ user_id: userId })
  });

  if (!res.ok) {
    const text = await res.text();
    let msg = `API Key creation failed (${res.status})`;
    try {
      const data = JSON.parse(text);
      if (data.detail) msg = data.detail;
    } catch (_) {}
    throw new ApiError(msg, res.status);
  }

  return await res.json();
}
