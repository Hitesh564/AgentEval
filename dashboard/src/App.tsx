import { useState, useEffect } from 'react';
import { 
  Activity, 
  CheckCircle2, 
  XCircle, 
  ArrowLeft, 
  BarChart2, 
  AlertOctagon, 
  Layers, 
  Clock, 
  Info,
  ChevronRight
} from 'lucide-react';

const API_BASE = "http://localhost:8000";

interface Session {
  session_id: string;
  score: number;
  passed: boolean;
  failure_tag: string | null;
  timestamp: string;
}


interface NodeRecommendation {
  suggestion: string;
  impact: string;
}

interface TraceNode {
  node_id: string;
  node_type: string;
  raw_health: number;
  adjusted_health: number;
  is_root_cause: boolean;
  is_inherited_degradation: boolean;
  is_co_originator: boolean;
  parent_node_ids: string[];
  evidence: {
    retriever_similarity: number | null;
    groundedness_ratio: number | null;
    tool_margin: number | null;
    latency: number;
    json_valid: number;
    instruction_following: number;
    judge_mode: string;
    retry_count?: number;
  };
  confidence: number;
  confidence_tier: string;
  recommendations: NodeRecommendation[];
}

interface SessionDetail {
  session_id: string;
  overall_score: number;
  passed: boolean;
  root_cause: {
    node_id: string;
    confidence: number;
    confidence_tier: string;
  } | null;
  co_originators: {
    node_id: string;
    raw_health: number;
  }[] | null;
  confidence_tier: string;
  nodes: TraceNode[];
}

interface BenchmarkMetric {
  metric: string;
  val_a: number;
  val_b: number;
  delta: number;
  status: string;
}

interface BenchmarkReport {
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

function App() {
  const [activeTab, setActiveTab] = useState<'sessions' | 'benchmark'>('sessions');
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [sessionDetail, setSessionDetail] = useState<SessionDetail | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkReport | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load conversation list
  useEffect(() => {
    if (activeTab === 'sessions' && !selectedSession) {
      setLoading(true);
      setError(null);
      fetch(`${API_BASE}/api/sessions`)
        .then(res => {
          if (!res.ok) throw new Error("Failed to load sessions");
          return res.json();
        })
        .then(data => {
          setSessions(data);
          setLoading(false);
        })
        .catch(err => {
          setError(err.message);
          setLoading(false);
        });
    }
  }, [activeTab, selectedSession]);

  // Load session trace detail
  useEffect(() => {
    if (selectedSession) {
      setLoading(true);
      setError(null);
      fetch(`${API_BASE}/api/sessions/${selectedSession}/trace`)
        .then(res => {
          if (!res.ok) throw new Error("Failed to load trace details");
          return res.json();
        })
        .then(data => {
          setSessionDetail(data);
          setLoading(false);
        })
        .catch(err => {
          setError(err.message);
          setLoading(false);
        });
    } else {
      setSessionDetail(null);
    }
  }, [selectedSession]);

  // Load benchmark comparison report
  useEffect(() => {
    if (activeTab === 'benchmark') {
      setLoading(true);
      setError(null);
      fetch(`${API_BASE}/api/benchmark/compare`)
        .then(res => {
          if (!res.ok) {
            return res.json().then(data => {
              throw new Error(data.detail || "Failed to compare versions");
            });
          }
          return res.json();
        })
        .then(data => {
          setBenchmark(data);
          setLoading(false);
        })
        .catch(err => {
          setError(err.message);
          setLoading(false);
        });
    }
  }, [activeTab]);

  const formatDate = (isoStr: string) => {
    try {
      const date = new Date(isoStr);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' ' + date.toLocaleDateString();
    } catch {
      return isoStr;
    }
  };

  const getFailureLabel = (tag: string | null) => {
    if (!tag) return "None";
    return tag.replace(/_/g, ' ');
  };

  return (
    <div className="app-container">
      {/* Top Header & Nav bar */}
      <header className="app-header">
        <div className="logo-section">
          <Activity className="logo-icon" size={32} />
          <div>
            <h1 className="app-title">AgentEval</h1>
            <p className="app-subtitle">Causal Diagnosis Observability Infrastructure</p>
          </div>
        </div>
        <nav className="nav-tabs">
          <button 
            className={`nav-tab ${activeTab === 'sessions' ? 'active' : ''}`}
            onClick={() => { setActiveTab('sessions'); setSelectedSession(null); }}
          >
            <Layers size={16} /> Sessions
          </button>
          <button 
            className={`nav-tab ${activeTab === 'benchmark' ? 'active' : ''}`}
            onClick={() => { setActiveTab('benchmark'); setSelectedSession(null); }}
          >
            <BarChart2 size={16} /> Regression Report
          </button>
        </nav>
      </header>

      {/* Loading state indicator */}
      {loading && (
        <div className="empty-state">
          <Activity className="logo-icon" size={40} style={{ animation: 'spin 2s linear infinite' }} />
          <p style={{ marginTop: '1rem' }}>Processing diagnostic traces...</p>
        </div>
      )}

      {/* Error state alert */}
      {error && !loading && (
        <div className="glass-card" style={{ borderColor: 'var(--color-danger)', borderLeftWidth: '4px', marginBottom: '2rem' }}>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <AlertOctagon color="var(--color-danger)" size={24} />
            <h3 style={{ margin: 0, color: 'var(--color-danger)' }}>Error Encountered</h3>
          </div>
          <p style={{ marginTop: '0.75rem', color: 'var(--text-primary)' }}>{error}</p>
          <p style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>
            Ensure your FastAPI backend is running (`python -m uvicorn agenteval.server.main:app`) and the calibration SQLite file exists.
          </p>
        </div>
      )}

      {/* Screen 1: Conversation Session List */}
      {activeTab === 'sessions' && !selectedSession && !loading && !error && (
        <div className="glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h2>Traced Agent Conversations</h2>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Showing {sessions.length} sessions
            </span>
          </div>
          {sessions.length === 0 ? (
            <div className="empty-state">
              <p>No traces detected in sqlite store. Execute simple_rag_agent to populate runs.</p>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="session-table">
                <thead>
                  <tr>
                    <th>Session ID</th>
                    <th>Diag Score</th>
                    <th>Status</th>
                    <th>Root Cause Taxonomy</th>
                    <th>Timestamp</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.map(s => (
                    <tr 
                      key={s.session_id} 
                      className="session-row"
                      onClick={() => setSelectedSession(s.session_id)}
                    >
                      <td style={{ fontWeight: 600 }}>{s.session_id}</td>
                      <td>
                        <span style={{ fontWeight: 700, color: s.passed ? 'var(--color-success)' : 'var(--color-warning)' }}>
                          {s.score.toFixed(2)}
                        </span>
                      </td>
                      <td>
                        <span className={`score-badge ${s.passed ? 'passed' : 'failed'}`}>
                          {s.passed ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
                          {s.passed ? 'Passed' : 'Failed'}
                        </span>
                      </td>
                      <td>
                        {s.failure_tag ? (
                          <span className={`taxo-badge ${s.failure_tag}`}>
                            {getFailureLabel(s.failure_tag)}
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>—</span>
                        )}
                      </td>
                      <td style={{ color: 'var(--text-secondary)' }}>{formatDate(s.timestamp)}</td>
                      <td><ChevronRight size={16} color="var(--text-muted)" /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Screen 2: Detailed Trace View & Causal Chain Graph */}
      {activeTab === 'sessions' && selectedSession && sessionDetail && !loading && !error && (
        <div className="flex-column">
          <div>
            <button className="btn-back" onClick={() => setSelectedSession(null)}>
              <ArrowLeft size={16} /> Back to Conversations
            </button>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
              <div>
                <h2 style={{ marginBottom: '0.25rem' }}>Session Trace Analysis</h2>
                <code style={{ fontSize: '0.9rem', color: 'var(--color-primary)' }}>ID: {sessionDetail.session_id}</code>
              </div>
              <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                <span className={`score-badge ${sessionDetail.passed ? 'passed' : 'failed'}`} style={{ padding: '0.6rem 1rem', fontSize: '1rem' }}>
                  {sessionDetail.passed ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
                  {sessionDetail.passed ? 'Healthy Run' : 'Failure Diagnosed'}
                </span>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>OVERALL SCORE</div>
                  <div style={{ fontSize: '1.75rem', fontWeight: 800, color: sessionDetail.passed ? 'var(--color-success)' : 'var(--color-warning)' }}>
                    {sessionDetail.overall_score.toFixed(2)}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="grid-2">
            {/* Visual Causal Chain Flow */}
            <div className="glass-card">
              <h3 style={{ marginBottom: '1.5rem' }}>Causal Attribution Graph</h3>
              <div className="causal-graph">
                {(() => {
                  const isBranching = sessionDetail.nodes.some(n => n.parent_node_ids.length > 1);
                  if (!isBranching) {
                    return sessionDetail.nodes.map(node => {
                      let borderClass = 'healthy';
                      if (node.is_root_cause) {
                        borderClass = 'root-cause';
                      } else if (node.is_co_originator) {
                        borderClass = 'co-originator';
                      } else if (node.is_inherited_degradation) {
                        borderClass = 'inherited-degradation';
                      }

                      return (
                        <div 
                          key={node.node_id} 
                          className={`causal-node-card ${borderClass}`}
                        >
                          <div className="node-info">
                            <div className="node-meta">
                              <span className="node-title">{node.node_id}</span>
                              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                                ({node.node_type})
                              </span>
                              {node.is_root_cause && (
                                <span className="badge-pill root-cause" style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                                  <AlertOctagon size={12} /> Root Cause
                                </span>
                              )}
                              {node.is_co_originator && (
                                <span className="badge-pill co-originator" style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                                  <AlertOctagon size={12} /> Ambiguous Cause
                                </span>
                              )}
                              {node.is_inherited_degradation && (
                                <span className="badge-pill inherited" style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                                  <Info size={12} /> Inherited Degradation
                                </span>
                              )}
                              {node.evidence.retry_count !== undefined && node.evidence.retry_count > 0 && (
                                <span className="badge-pill retried" style={{ display: 'flex', alignItems: 'center', gap: '0.2rem', backgroundColor: 'rgba(245, 158, 11, 0.1)', color: 'var(--color-warning)', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                                  Retried {node.evidence.retry_count}x
                                </span>
                              )}
                            </div>
                            {node.parent_node_ids.length > 0 && (
                              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                                Inbound link from: {node.parent_node_ids.join(', ')}
                              </div>
                            )}
                          </div>

                          <div className="node-stats">
                            <div className="stat-group">
                              <span className="stat-label">Raw Health</span>
                              <span className="stat-value" style={{ color: node.raw_health < 0.70 ? 'var(--color-danger)' : (node.raw_health < 1.00 ? 'var(--color-warning)' : 'var(--color-success)') }}>
                                {node.raw_health.toFixed(2)}
                              </span>
                            </div>
                            <div className="stat-group">
                              <span className="stat-label">Adjusted Health</span>
                              <span className="stat-value" style={{ color: node.adjusted_health < 0.70 ? 'var(--color-danger)' : (node.adjusted_health < 1.00 ? 'var(--color-warning)' : 'var(--color-success)') }}>
                                {node.adjusted_health.toFixed(2)}
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    });
                  }

                  // Topological Sort for Branching Layout
                  const levels: Record<string, number> = {};
                  sessionDetail.nodes.forEach(n => {
                    if (n.parent_node_ids.length === 0) {
                      levels[n.node_id] = 0;
                    }
                  });

                  let changed = true;
                  let iterations = 0;
                  while (changed && iterations < 100) {
                    changed = false;
                    iterations++;
                    sessionDetail.nodes.forEach(n => {
                      if (levels[n.node_id] === undefined) {
                        const parentLevels = n.parent_node_ids.map(p => levels[p]);
                        if (parentLevels.every(l => l !== undefined)) {
                          levels[n.node_id] = Math.max(...parentLevels) + 1;
                          changed = true;
                        }
                      }
                    });
                  }

                  const grouped: Record<number, any[]> = {};
                  sessionDetail.nodes.forEach(n => {
                    const lvl = levels[n.node_id] !== undefined ? levels[n.node_id] : 0;
                    if (!grouped[lvl]) grouped[lvl] = [];
                    grouped[lvl].push(n);
                  });

                  const rows: any[][] = [];
                  const maxLvl = Math.max(...Object.keys(grouped).map(Number), 0);
                  for (let i = 0; i <= maxLvl; i++) {
                    if (grouped[i]) {
                      rows.push(grouped[i]);
                    }
                  }

                  return (
                    <div className="causal-graph-branching" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%', alignItems: 'center' }}>
                      {rows.map((rowNodes, lvlIdx) => (
                        <div key={lvlIdx} className="graph-level-row-wrapper" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%' }}>
                          {/* Render connector from previous level to this level */}
                          {lvlIdx > 0 && (
                            <div className="level-connector-wrapper" style={{ width: '100%', height: '40px', display: 'flex', justifyContent: 'center', margin: '0.25rem 0' }}>
                              {rows[lvlIdx - 1].length === 1 && rowNodes.length === 2 && (
                                <svg width="100%" height="40" style={{ maxWidth: '400px' }}>
                                  <line x1="50%" y1="0" x2="50%" y2="20" stroke="var(--border-card)" strokeWidth="2" />
                                  <line x1="25%" y1="20" x2="75%" y2="20" stroke="var(--border-card)" strokeWidth="2" />
                                  <line x1="25%" y1="20" x2="25%" y2="40" stroke="var(--border-card)" strokeWidth="2" />
                                  <line x1="75%" y1="20" x2="75%" y2="40" stroke="var(--border-card)" strokeWidth="2" />
                                </svg>
                              )}
                              {rows[lvlIdx - 1].length === 2 && rowNodes.length === 1 && (
                                <svg width="100%" height="40" style={{ maxWidth: '400px' }}>
                                  <line x1="25%" y1="0" x2="25%" y2="20" stroke={rows[lvlIdx - 1][0].raw_health < 0.70 ? "var(--color-danger)" : "var(--border-card)"} strokeWidth="2" />
                                  <line x1="75%" y1="0" x2="75%" y2="20" stroke={rows[lvlIdx - 1][1].raw_health < 0.70 ? "var(--color-danger)" : "var(--border-card)"} strokeWidth="2" />
                                  <line x1="25%" y1="20" x2="75%" y2="20" stroke="var(--border-card)" strokeWidth="2" />
                                  <line x1="50%" y1="20" x2="50%" y2="40" stroke="var(--border-card)" strokeWidth="2" />
                                </svg>
                              )}
                              {(rows[lvlIdx - 1].length === 1 && rowNodes.length === 1) && (
                                <svg width="100%" height="40" style={{ maxWidth: '400px' }}>
                                  <line x1="50%" y1="0" x2="50%" y2="40" stroke="var(--border-card)" strokeWidth="2" />
                                </svg>
                              )}
                            </div>
                          )}
                          
                          <div className="graph-level-row" style={{ display: 'flex', justifyContent: 'center', gap: '2rem', width: '100%' }}>
                            {rowNodes.map(node => {
                              let borderClass = 'healthy';
                              if (node.is_root_cause) {
                                borderClass = 'root-cause';
                              } else if (node.is_co_originator) {
                                borderClass = 'co-originator';
                              } else if (node.is_inherited_degradation) {
                                borderClass = 'inherited-degradation';
                              }

                              const inheritedFrom = node.inherited_from_node_ids || [];
                              
                              return (
                                <div 
                                  key={node.node_id} 
                                  className={`causal-node-card ${borderClass}`}
                                  style={{ flex: 1, maxWidth: rowNodes.length === 1 ? '500px' : '350px' }}
                                >
                                  <div className="node-info">
                                    <div className="node-meta">
                                      <span className="node-title">{node.node_id}</span>
                                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                                        ({node.node_type})
                                      </span>
                                      {node.is_root_cause && (
                                        <span className="badge-pill root-cause" style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                                          <AlertOctagon size={12} /> Root Cause
                                        </span>
                                      )}
                                      {node.is_co_originator && (
                                        <span className="badge-pill co-originator" style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                                          <AlertOctagon size={12} /> Ambiguous Cause
                                        </span>
                                      )}
                                      {node.is_inherited_degradation && (
                                        <span className="badge-pill inherited" style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                                          <Info size={12} /> Inherited Degradation
                                        </span>
                                      )}
                                      {node.evidence.retry_count !== undefined && node.evidence.retry_count > 0 && (
                                        <span className="badge-pill retried" style={{ display: 'flex', alignItems: 'center', gap: '0.2rem', backgroundColor: 'rgba(245, 158, 11, 0.1)', color: 'var(--color-warning)', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                                          Retried {node.evidence.retry_count}x
                                        </span>
                                      )}
                                    </div>
                                    
                                    {inheritedFrom.length > 0 && (
                                      <div style={{ fontSize: '0.8rem', color: 'var(--color-warning)', marginTop: '0.25rem' }}>
                                        Degradation inherited from: {inheritedFrom.join(', ')}
                                      </div>
                                    )}
                                    {node.parent_node_ids.length > 0 && inheritedFrom.length === 0 && (
                                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                                        Inbound link from: {node.parent_node_ids.join(', ')}
                                      </div>
                                    )}
                                  </div>

                                  <div className="node-stats">
                                    <div className="stat-group">
                                      <span className="stat-label">Raw Health</span>
                                      <span className="stat-value" style={{ color: node.raw_health < 0.70 ? 'var(--color-danger)' : (node.raw_health < 1.00 ? 'var(--color-warning)' : 'var(--color-success)') }}>
                                        {node.raw_health.toFixed(2)}
                                      </span>
                                    </div>
                                    <div className="stat-group">
                                      <span className="stat-label">Adjusted Health</span>
                                      <span className="stat-value" style={{ color: node.adjusted_health < 0.70 ? 'var(--color-danger)' : (node.adjusted_health < 1.00 ? 'var(--color-warning)' : 'var(--color-success)') }}>
                                        {node.adjusted_health.toFixed(2)}
                                      </span>
                                    </div>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </div>
            </div>

            {/* Evidence details & recommendations sidebar */}
            <div className="flex-column">
              {/* Identified Root Cause Details */}
              {sessionDetail.nodes.find(n => n.is_root_cause) && (
                (() => {
                  const rootNode = sessionDetail.nodes.find(n => n.is_root_cause)!;
                  return (
                    <div className="glass-card" style={{ borderColor: 'var(--color-danger)' }}>
                      <h3 style={{ color: 'var(--color-danger)', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        <AlertOctagon size={18} /> Root Cause Detected
                      </h3>
                      <p style={{ fontSize: '0.9rem', marginBottom: '1rem' }}>
                        The Root Cause Engine identified <strong>{rootNode.node_id}</strong> as the origin of the failure with <strong title={`${(rootNode.confidence * 100).toFixed(1)}% raw confidence`} style={{ borderBottom: '1px dotted rgba(255,255,255,0.4)', cursor: 'help' }}>{rootNode.confidence_tier} confidence</strong>.
                      </p>
                      
                      <div className="stat-group" style={{ alignItems: 'flex-start', borderTop: '1px solid var(--border-card)', paddingTop: '0.75rem', marginBottom: '1rem' }}>
                        <span className="stat-label">Measurable Evidence</span>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', width: '100%', marginTop: '0.5rem', fontSize: '0.85rem' }}>
                          {rootNode.evidence.retriever_similarity !== null && (
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                              <span>Retriever Doc Cosine Similarity:</span>
                              <strong style={{ color: rootNode.evidence.retriever_similarity < 0.50 ? 'var(--color-danger)' : 'var(--text-primary)' }}>
                                {rootNode.evidence.retriever_similarity.toFixed(3)}
                              </strong>
                            </div>
                          )}
                          {rootNode.evidence.groundedness_ratio !== null && (
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                              <span>Groundedness support ratio:</span>
                              <strong style={{ color: rootNode.evidence.groundedness_ratio < 1.0 ? 'var(--color-danger)' : 'var(--text-primary)' }}>
                                {(rootNode.evidence.groundedness_ratio * 100).toFixed(0)}%
                              </strong>
                            </div>
                          )}
                          {rootNode.evidence.tool_margin !== null && (
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                              <span>Tool Selection Margin:</span>
                              <strong style={{ color: rootNode.evidence.tool_margin < 0.15 ? 'var(--color-danger)' : 'var(--text-primary)' }}>
                                {rootNode.evidence.tool_margin.toFixed(2)}
                              </strong>
                            </div>
                          )}
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span>Node Latency Duration:</span>
                            <strong style={{ color: rootNode.evidence.latency > 2.0 ? 'var(--color-danger)' : 'var(--text-primary)' }}>
                              {rootNode.evidence.latency.toFixed(3)}s
                            </strong>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span>JSON parsing validity:</span>
                            <strong style={{ color: rootNode.evidence.json_valid === 0 ? 'var(--color-danger)' : 'var(--text-primary)' }}>
                              {rootNode.evidence.json_valid === 1.0 ? 'VALID' : 'MALFORMED'}
                            </strong>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span>Judge evaluation mode:</span>
                            <strong style={{ textTransform: 'uppercase', color: rootNode.evidence.judge_mode === 'llm' ? 'var(--color-primary)' : 'var(--text-muted)' }}>
                              {rootNode.evidence.judge_mode}
                            </strong>
                          </div>
                        </div>
                      </div>

                      {/* Evidence Recommendations */}
                      {rootNode.recommendations.length > 0 && (
                        <div className="rec-box">
                          <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.95rem' }}>
                            <Clock size={14} /> Actionable Fixes
                          </h4>
                          {rootNode.recommendations.map((rec, idx) => (
                            <div key={idx} className="rec-item">
                              <span className={`rec-impact-badge ${rec.impact.toLowerCase()}`}>
                                {rec.impact}
                              </span>
                              <p style={{ fontSize: '0.8rem', color: 'var(--text-primary)' }}>{rec.suggestion}</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })()
              )}

              {/* Co-Originators Details (Ambiguous Case) */}
              {sessionDetail.co_originators && sessionDetail.co_originators.length > 0 && (
                <div className="glass-card" style={{ borderColor: 'var(--color-warning)' }}>
                  <h3 style={{ color: 'var(--color-warning)', display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <AlertOctagon size={18} /> Ambiguous Causal Origin
                  </h3>
                  <p style={{ fontSize: '0.9rem', marginBottom: '1rem' }}>
                    The Root Cause Engine detected an ambiguous failure. The following nodes are likely co-originators of the degradation:
                  </p>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                    {sessionDetail.co_originators.map((co: any) => {
                      const coNode = sessionDetail.nodes.find(n => n.node_id === co.node_id);
                      if (!coNode) return null;
                      return (
                        <div key={co.node_id} style={{ borderLeft: '3px solid var(--color-warning)', paddingLeft: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <strong style={{ fontSize: '0.95rem', color: 'var(--color-warning)' }}>{co.node_id}</strong>
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                              Raw Health: {co.raw_health.toFixed(2)}
                            </span>
                          </div>
                          
                          {/* Evidence list for this co-originator */}
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                            {coNode.evidence.retriever_similarity !== null && (
                              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <span>Retriever Similarity:</span>
                                <strong>{coNode.evidence.retriever_similarity.toFixed(3)}</strong>
                              </div>
                            )}
                            {coNode.evidence.groundedness_ratio !== null && (
                              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <span>Groundedness support:</span>
                                <strong>{(coNode.evidence.groundedness_ratio * 100).toFixed(0)}%</strong>
                              </div>
                            )}
                            {coNode.evidence.tool_margin !== null && (
                              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <span>Tool Margin:</span>
                                <strong>{coNode.evidence.tool_margin.toFixed(2)}</strong>
                              </div>
                            )}
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                              <span>Latency:</span>
                              <strong>{coNode.evidence.latency.toFixed(3)}s</strong>
                            </div>
                          </div>
                          
                          {/* Recommendations for this co-originator */}
                          {coNode.recommendations && coNode.recommendations.length > 0 && (
                            <div className="rec-box" style={{ marginTop: '0.25rem', padding: '0.5rem', background: 'rgba(255,255,255,0.02)' }}>
                              <div style={{ fontSize: '0.75rem', fontWeight: 600, marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                <Clock size={12} /> Suggested Fixes:
                              </div>
                              {coNode.recommendations.map((rec: any, idx: number) => (
                                <div key={idx} className="rec-item" style={{ marginBottom: '0.2rem', paddingBottom: 0, border: 'none' }}>
                                  <span className={`rec-impact-badge ${rec.impact.toLowerCase()}`} style={{ fontSize: '0.65rem', padding: '0.1rem 0.3rem' }}>
                                    {rec.impact}
                                  </span>
                                  <span style={{ fontSize: '0.75rem', marginLeft: '0.4rem', color: 'var(--text-primary)' }}>{rec.suggestion}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* General trace execution details */}
              <div className="glass-card">
                <h3>Execution Metadata</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1rem', fontSize: '0.85rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-card)', paddingBottom: '0.5rem' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Evaluator Mode</span>
                    <strong>{sessionDetail.nodes[0]?.evidence.judge_mode.toUpperCase() || 'UNKNOWN'}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-card)', paddingBottom: '0.5rem' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Total Chain Latency</span>
                    <strong>
                      {sessionDetail.nodes.reduce((sum, n) => sum + n.evidence.latency, 0).toFixed(3)}s
                    </strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Calibration Holdout</span>
                    <strong style={{ color: 'var(--color-success)' }}>Ground Truth Labeled</strong>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Screen 3: Benchmark Compare View */}
      {activeTab === 'benchmark' && benchmark && !loading && !error && (
        <div className="flex-column">
          <div className="glass-card">
            <h2>Benchmark Comparison</h2>
            <p style={{ marginBottom: '1.5rem' }}>
              Showing real, parsed regression deltas between baseline runs and optimized configurations.
            </p>
            
            <div className="comparison-grid">
              <div className="glass-card" style={{ padding: '1rem', textAlign: 'center' }}>
                <span className="stat-label">Version A (Baseline)</span>
                <h3 style={{ fontSize: '1.25rem', marginTop: '0.5rem', marginBottom: 0 }}>{benchmark.version_a}</h3>
              </div>
              <div className="glass-card" style={{ padding: '1rem', textAlign: 'center' }}>
                <span className="stat-label">Version B (Fixed)</span>
                <h3 style={{ fontSize: '1.25rem', marginTop: '0.5rem', marginBottom: 0 }}>{benchmark.version_b}</h3>
              </div>
            </div>

            <div className="comparison-grid" style={{ marginTop: '1.5rem', marginBottom: '1.5rem' }}>
              <div className="glass-card" style={{ padding: '1.25rem' }}>
                <span className="stat-label" style={{ fontWeight: 600, color: 'var(--color-primary)' }}>Causal Diagnostic Accuracy</span>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.75rem' }}>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>VERSION A (BASELINE)</div>
                    <div style={{ fontSize: '1.4rem', fontWeight: 700 }}>
                      {benchmark.accuracy_a !== null ? `${(benchmark.accuracy_a * 100).toFixed(1)}%` : '—'}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>VERSION B (FIXED)</div>
                    <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--color-success)' }}>
                      {benchmark.accuracy_b !== null ? `${(benchmark.accuracy_b * 100).toFixed(1)}%` : '—'}
                    </div>
                  </div>
                </div>
              </div>

              <div className="glass-card" style={{ padding: '1.25rem' }}>
                <span className="stat-label" style={{ fontWeight: 600, color: 'var(--color-primary)' }}>Regression Run Pass Rate</span>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.75rem' }}>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>VERSION A (BASELINE)</div>
                    <div style={{ fontSize: '1.4rem', fontWeight: 700 }}>
                      {`${(benchmark.pass_rate_a * 100).toFixed(1)}%`}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>VERSION B (FIXED)</div>
                    <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--color-success)' }}>
                      {`${(benchmark.pass_rate_b * 100).toFixed(1)}%`}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div style={{ overflowX: 'auto', marginBottom: '2rem' }}>
              <table className="session-table">
                <thead>
                  <tr>
                    <th>Target Evaluation Metric</th>
                    <th>vA (Baseline)</th>
                    <th>vB (Fixed)</th>
                    <th>Observed Delta</th>
                  </tr>
                </thead>
                <tbody>
                  {benchmark.metrics.map((m, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: 600 }}>{m.metric}</td>
                      <td>{m.val_a.toFixed(2)}</td>
                      <td>{m.val_b.toFixed(2)}</td>
                      <td>
                        <span className={`delta-pill ${m.status.toLowerCase()}`}>
                          {m.delta > 0 ? `+${m.delta.toFixed(2)}` : m.delta.toFixed(2)} ({m.status})
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Verdict calibration block */}
            <div className="glass-card" style={{ borderColor: 'var(--color-primary)', background: 'var(--bg-secondary)', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <h3 style={{ color: 'var(--color-primary)', margin: 0 }}>Attribution Regression Verification</h3>
              <p style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                {benchmark.overall_verdict}
              </p>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                The comparative verdict checks directional improvements across instruction following, hallucination rate, tool accuracy, retrieval cosine similarity, and node executions to verify B is a healthy regression improvement over A.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
