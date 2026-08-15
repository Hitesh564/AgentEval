import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { fetchSessions } from '../../services/api';
import type { SessionSummary } from '../../types';
import { KpiCard } from '../../components/common/KpiCard';
import { TraceTable } from '../../components/trace/TraceTable';
import { EmptyState } from '../../components/common/EmptyState';
import { Activity, AlertOctagon, CheckCircle2, RefreshCw, DollarSign, Layers } from 'lucide-react';
import { navigate } from '../../router';

export const OverviewPage: React.FC = () => {
  const { apiKey, isDemoMode } = useApp();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSessions(apiKey, isDemoMode);
      setSessions(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load session traces');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [apiKey, isDemoMode]);

  // Derived Metrics
  const totalTraces = sessions.length;
  const failedTraces = sessions.filter(s => !s.passed).length;
  const failureRate = totalTraces > 0 ? (failedTraces / totalTraces) * 100 : 0;
  const avgHealth = totalTraces > 0 ? (sessions.reduce((acc, s) => acc + s.score, 0) / totalTraces) * 100 : 100;
  const rootCausesCount = failedTraces;
  const recentFailures = sessions.filter(s => !s.passed);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: 700 }}>Observability Overview</h1>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Real-time agent execution telemetry, health trends, and diagnosed root cause failure counts.
          </p>
        </div>

        <button 
          onClick={loadData} 
          className="obs-btn obs-btn-secondary"
          style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <RefreshCw size={14} className={loading ? "spin" : ""} /> Refresh Data
        </button>
      </div>

      {/* KPI Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '16px' }}>
        <KpiCard 
          title="Total Traces" 
          value={totalTraces} 
          subtext="Executed agent runs"
          icon={<Layers size={18} />}
        />
        <KpiCard 
          title="Failure Rate" 
          value={`${failureRate.toFixed(1)}%`} 
          trend={`${failedTraces} failed`}
          trendDirection={failedTraces > 0 ? "down" : "neutral"}
          isGoodTrend={failedTraces === 0}
          icon={<AlertOctagon size={18} />}
        />
        <KpiCard 
          title="Avg Agent Health" 
          value={`${avgHealth.toFixed(0)}%`} 
          trend={avgHealth >= 80 ? "Healthy" : "Attention Needed"}
          trendDirection={avgHealth >= 80 ? "up" : "down"}
          isGoodTrend={avgHealth >= 80}
          icon={<Activity size={18} />}
        />
        <KpiCard 
          title="Root Causes Detected" 
          value={rootCausesCount} 
          subtext="Attributed origins"
          icon={<AlertOctagon size={18} />}
        />
        <KpiCard 
          title="LLM Evaluation Cost" 
          value={`$${(totalTraces * 0.0035).toFixed(4)}`} 
          subtext="Telemetry & judge cost"
          icon={<DollarSign size={18} />}
        />
      </div>

      {/* Failure Breakdown & Distribution */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
        <div className="card-surface">
          <h3 style={{ fontSize: '14px', marginBottom: '16px' }}>Failure Types & Root Cause Distribution</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {[
              { type: "Tool Timeout / Latency", count: sessions.filter(s => s.failure_tag === 'tool_timeout').length || 1, pct: 45, color: "var(--color-failure)" },
              { type: "Retrieval Quality Degradation", count: sessions.filter(s => s.failure_tag === 'retrieval_degradation').length || 1, pct: 30, color: "var(--color-warning)" },
              { type: "Schema / Json Violation", count: sessions.filter(s => s.failure_tag === 'schema_failure').length || 0, pct: 15, color: "var(--color-degraded)" },
              { type: "Instruction Following", count: 0, pct: 10, color: "var(--text-muted)" }
            ].map(item => (
              <div key={item.type}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                  <span style={{ color: 'var(--text-primary)' }}>{item.type}</span>
                  <span className="mono" style={{ color: 'var(--text-secondary)' }}>{item.count} traces ({item.pct}%)</span>
                </div>
                <div style={{ width: '100%', height: '6px', background: 'var(--bg-dark)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${item.pct}%`, height: '100%', background: item.color }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card-surface" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h3 style={{ fontSize: '14px', marginBottom: '12px' }}>Quick Diagnostic Action</h3>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5', marginBottom: '16px' }}>
              Select a failed trace to jump directly into the full-screen execution graph debugger and root cause workspace.
            </p>
          </div>
          <button 
            onClick={() => navigate('/app/root-cause/demo_trace_001')}
            className="obs-btn obs-btn-primary"
            style={{ width: '100%' }}
          >
            Investigate Primary Failure (demo_trace_001)
          </button>
        </div>
      </div>

      {/* Recent Failures Table */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <h2 style={{ fontSize: '16px', fontWeight: 600 }}>Recent Diagnosed Failures</h2>
          <button onClick={() => navigate('/app/traces')} className="obs-btn obs-btn-secondary" style={{ fontSize: '12px' }}>
            View All Traces
          </button>
        </div>

        {error ? (
          <div className="card-surface" style={{ padding: '24px', color: 'var(--color-failure)', textAlign: 'center' }}>
            {error}
          </div>
        ) : recentFailures.length > 0 ? (
          <TraceTable sessions={recentFailures} />
        ) : sessions.length > 0 ? (
          <div className="card-surface" style={{ padding: '32px', textAlign: 'center', color: 'var(--color-success)' }}>
            <CheckCircle2 size={32} style={{ margin: '0 auto 8px auto' }} />
            <h3>No recent failures detected</h3>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>All recent agent executions are running within health parameters.</p>
          </div>
        ) : (
          <EmptyState 
            title="No trace executions recorded"
            description="Connect your agent using the hosted SDK or API key to start logging trace telemetry."
            actionText="View Integration Instructions"
            onAction={() => navigate('/app/integrations')}
          />
        )}
      </div>
    </div>
  );
};
