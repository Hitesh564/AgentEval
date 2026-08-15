import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { fetchSessionTrace } from '../../services/api';
import type { SessionDetail } from '../../types';
import { CausalGraph } from '../../components/rootcause/CausalGraph';
import { TimelinePanel } from '../../components/rootcause/TimelinePanel';
import { EvidencePanel } from '../../components/rootcause/EvidencePanel';
import { RankingPanel } from '../../components/rootcause/RankingPanel';
import { RecsPanel } from '../../components/rootcause/RecsPanel';
import { StatusBadge } from '../../components/common/StatusBadge';
import { AlertOctagon, ArrowLeft, RefreshCw, ShieldCheck } from 'lucide-react';
import { navigate } from '../../router';

export const RootCausePage: React.FC<{ sessionId?: string }> = ({ sessionId = 'demo_trace_001' }) => {
  const { apiKey, isDemoMode } = useApp();
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const traceData = await fetchSessionTrace(sessionId, apiKey, isDemoMode);
      setDetail(traceData);
    } catch (err: any) {
      setError(err.message || 'Failed to load root cause diagnosis');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [sessionId, apiKey, isDemoMode]);

  const rootCause = detail?.root_cause || null;
  const rootNode = detail?.nodes?.find(n => n.node_id === rootCause?.node_id || n.is_root_cause) || null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Workspace Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button 
            onClick={() => navigate(`/app/traces/${sessionId}`)}
            className="obs-btn obs-btn-secondary"
            style={{ padding: '6px 12px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <ArrowLeft size={14} /> Back to Execution Graph
          </button>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertOctagon color="var(--color-failure)" size={20} />
              <h1 style={{ fontSize: '18px', fontWeight: 700 }}>Root Cause Analysis Workspace</h1>
              <span className="mono" style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                ({sessionId})
              </span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Attributing failure origins across parent-child dependencies and signal evidence.
            </p>
          </div>
        </div>

        <button onClick={loadData} className="obs-btn obs-btn-secondary" style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <RefreshCw size={14} className={loading ? "spin" : ""} /> Refresh Analysis
        </button>
      </div>

      {/* Top Banner Card for Diagnosed Origin */}
      {error ? (
        <div className="card-surface" style={{ padding: '24px', color: 'var(--color-failure)', textAlign: 'center' }}>
          {error}
        </div>
      ) : rootCause ? (
        <div className="card-elevated" style={{
          background: 'linear-gradient(135deg, rgba(255, 102, 122, 0.12) 0%, rgba(17, 24, 39, 0.9) 100%)',
          borderColor: 'var(--color-failure)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--color-failure)', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '4px' }}>
                PRIMARY DIAGNOSED FAILURE ORIGIN
              </div>
              <h2 className="mono" style={{ fontSize: '22px', color: 'var(--text-primary)', fontWeight: 800 }}>
                {rootCause.node_id}
              </h2>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                Failure Classification: <StatusBadge status={rootCause.failure_type} type="failure_tag" />
              </div>
            </div>

            <div style={{ display: 'flex', gap: '24px', background: 'var(--bg-dark)', padding: '12px 20px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Attribution Score</div>
                <div className="mono" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-failure)' }}>
                  {rootCause.attribution_score || 0.82}
                </div>
              </div>
              <div style={{ borderLeft: '1px solid var(--border-subtle)', paddingLeft: '20px' }}>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Candidate Separation</div>
                <div className="mono" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--accent-secondary)' }}>
                  {rootCause.candidate_separation || 0.28}
                </div>
              </div>
              <div style={{ borderLeft: '1px solid var(--border-subtle)', paddingLeft: '20px' }}>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Confidence Tier</div>
                <div className="mono" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-success)' }}>
                  {rootCause.confidence_tier.toUpperCase()}
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="card-surface" style={{ padding: '24px', textAlign: 'center', color: 'var(--color-success)' }}>
          <ShieldCheck size={32} style={{ margin: '0 auto 8px auto' }} />
          <h3>No failure diagnosed for this trace</h3>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>This trace execution completed successfully with 100% health parameters.</p>
        </div>
      )}

      {/* Grid Layout: Left Column (Causal Graph + Timeline + Evidence), Right Column (Ranking + Recommendations) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Left Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <CausalGraph rootCause={rootCause} nodes={detail?.nodes || []} />
          <TimelinePanel nodes={detail?.nodes || []} />
          <EvidencePanel rootCause={rootCause} node={rootNode} />
        </div>

        {/* Right Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <RankingPanel candidates={rootCause?.ranked_candidates} />
          <RecsPanel recommendations={rootNode?.recommendations} />
        </div>
      </div>
    </div>
  );
};
