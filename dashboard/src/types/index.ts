export interface SessionSummary {
  session_id: string;
  score: number;
  passed: boolean;
  failure_tag: string | null;
  timestamp: string;
}

export interface TraceEvidence {
  retriever_similarity?: number | null;
  groundedness_ratio?: number | null;
  tool_margin?: number | null;
  latency?: number;
  json_valid?: number;
  instruction_following?: number;
  judge_mode?: string;
  retry_count?: number;
  first_attempt_health?: number;
  final_attempt_health?: number;
  retry_latency_cost?: number;
}

export interface NodeRecommendation {
  problem: string;
  evidence: string;
  recommended_action: string;
  expected_effect: string;
  priority: string; // "high" | "medium" | "low"
  confidence: number;
  suggestion?: string;
  impact?: string;
}

export interface RankedCandidate {
  node_id: string;
  node_type?: string;
  attribution_score: number;
  causal_origin_score?: number;
  failure_type?: string | null;
  calibrated_probability?: number | null;
}

export interface TraceNode {
  node_id: string;
  node_type: string;
  raw_health: number;
  adjusted_health?: number;
  overall_health: number;
  metric_scores: Record<string, number | null>;
  weakest_dimension: string | null;
  weakest_dimension_score: number | null;
  failed_dimensions: string[];
  evaluation_status: string;
  is_root_cause: boolean;
  is_inherited_degradation: boolean;
  is_co_originator: boolean;
  inherited_from_node_ids?: string[];
  children_node_ids?: string[];
  parent_node_ids: string[];
  failure_type: string | null;
  attribution_score?: number;
  causal_origin_score?: number;
  attribution_evidence?: Record<string, number>;
  candidate_separation?: number;
  calibrated_probability?: number | null;
  raw_score?: number;
  calibration_method?: string | null;
  calibration_status?: string | null;
  calibration_version?: string | null;
  evidence: TraceEvidence;
  confidence: number | null;
  confidence_calibrated?: boolean;
  confidence_tier: string;
  recommendations: NodeRecommendation[];
  // Raw node properties
  inputs?: any;
  outputs?: any;
  tool_name?: string | null;
  tool_args?: any;
  tool_result?: any;
  retrieved_docs?: any;
  tokens_in?: number;
  tokens_out?: number;
  cost_usd?: number;
  duration_s?: number;
  attempt_number?: number;
  timestamp_start?: string;
  timestamp_end?: string;
}

export interface RootCauseSummary {
  responsible_agent?: string;
  responsible_step?: string;
  node_id: string;
  node_type?: string;
  failure_type?: string | null;
  raw_health?: number;
  overall_health?: number;
  weakest_dimension?: string | null;
  weakest_dimension_score?: number | null;
  attribution_score?: number;
  causal_origin_score?: number;
  candidate_separation?: number;
  calibrated_probability?: number | null;
  raw_score?: number;
  calibration_method?: string | null;
  calibration_status?: string | null;
  calibration_version?: string | null;
  confidence: number | null;
  confidence_calibrated?: boolean;
  confidence_tier: string;
  ranked_candidates?: RankedCandidate[];
}

export interface CoOriginator {
  node_id: string;
  raw_health: number;
}

export interface SessionDetail {
  session_id: string;
  overall_score: number;
  passed: boolean;
  root_cause: RootCauseSummary | null;
  co_originators: CoOriginator[] | null;
  confidence_tier: string;
  nodes: TraceNode[];
}

export interface ChainSession {
  session_id: string;
  overall_health: number;
  passed: boolean;
  parent_session_id?: string | null;
  root_cause_node_id?: string | null;
}

export interface ChainDetail {
  chain_id: string;
  chain: ChainSession[];
  cross_session_root_cause: {
    session_id: string;
    node_id: string;
    node_type: string;
    failure_type: string | null;
  } | null;
}

export interface BenchmarkMetric {
  metric: string;
  val_a: number;
  val_b: number;
  delta: number;
  status: "IMPROVED" | "DEGRADED" | "UNCHANGED";
}

export interface BenchmarkReport {
  version_a: string;
  version_b: string;
  overall_verdict: string;
  metrics: BenchmarkMetric[];
  accuracy_a: number | null;
  accuracy_b: number | null;
  pass_rate_a: number;
  pass_rate_b: number;
  total_runs: number;
}

export interface ApiHealthResponse {
  status: string;
  service: string;
  database_backend: string;
  database_configured: boolean;
}

export type AppEnvironment = "development" | "staging" | "production";
