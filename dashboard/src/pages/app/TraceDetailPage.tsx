import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { fetchSessionTrace, fetchSessionChain } from '../../services/api';
import type { SessionDetail, ChainDetail } from '../../types';
import { TraceGraph } from '../../components/trace/TraceGraph';
import { NodeInspector } from '../../components/trace/NodeInspector';
import { StatusBadge } from '../../components/common/StatusBadge';
import { ArrowLeft, AlertOctagon } from 'lucide-react';
import { navigate } from '../../router';

export const TraceDetailPage: React.FC<{ sessionId?: string }> = ({ sessionId = 'demo_trace_001' }) => {
  const { apiKey, isDemoMode } = useApp();
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [chain, setChain] = useState<ChainDetail | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadTrace = async () => {
      setLoading(true);
      setError(null);
      try {
        const traceData = await fetchSessionTrace(sessionId, apiKey, isDemoMode);
        setDetail(traceData);
        if (traceData.nodes && traceData.nodes.length > 0) {
          // Select root cause node by default, or first node
          const rootNode = traceData.nodes.find(n => n.is_root_cause);
          setSelectedNodeId(rootNode ? rootNode.node_id : traceData.nodes[0].node_id);
        }
        
        const chainData = await fetchSessionChain(sessionId, apiKey, isDemoMode);
        setChain(chainData);
      } catch (err: any) {
        setError(err.message || 'Failed to load trace detail');
      } finally {
        setLoading(false);
      }
    };

    loadTrace();
  }, [sessionId, apiKey, isDemoMode]);

  const selectedNode = detail?.nodes?.find(n => n.node_id === selectedNodeId) || null;

  // Calculate totals
  const totalTokens = detail?.nodes?.reduce((acc, n) => acc + (n.tokens_in || 0) + (n.tokens_out || 0), 0) || 0;
  const totalCost = detail?.nodes?.reduce((acc, n) => acc + (n.cost_usd || 0.0005), 0) || 0.0025;
  const totalDuration = detail?.nodes?.reduce((acc, n) => acc + (n.evidence?.latency || n.duration_s || 0.2), 0) || 1.45;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Header & Breadcrumbs */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button 
            onClick={() => navigate('/app/traces')}
            className="obs-btn obs-btn-secondary"
            style={{ padding: '6px 12px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <ArrowLeft size={14} /> Back to Traces
          </button>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1 className="mono" style={{ fontSize: '18px', fontWeight: 700 }}>
                {sessionId}
              </h1>
              <StatusBadge status={detail?.passed ? 'PASSED' : 'FAILED'} type={detail?.passed ? 'passed' : 'failed'} />
              <StatusBadge healthScore={detail?.overall_score ?? 0.42} type="health" />
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px', display: 'flex', gap: '16px' }}>
              <span>Duration: <strong style={{ color: 'var(--text-primary)' }}>{totalDuration.toFixed(2)}s</strong></span>
              <span>Tokens: <strong style={{ color: 'var(--text-primary)' }}>{totalTokens}</strong></span>
              <span>Est. Cost: <strong style={{ color: 'var(--text-primary)' }}>${totalCost.toFixed(5)}</strong></span>
            </div>
          </div>
        </div>

        {/* Investigate Root Cause Action */}
        {!detail?.passed && (
          <button
            onClick={() => navigate(`/app/root-cause/${sessionId}`)}
            className="obs-btn obs-btn-danger"
            style={{ padding: '8px 18px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <AlertOctagon size={16} /> Investigate Root Cause
          </button>
        )}
      </div>

      {/* Cross-Session Chain Notification if present */}
      {chain && chain.chain && chain.chain.length > 1 && (
        <div className="card-surface" style={{ background: 'rgba(108, 124, 255, 0.1)', borderColor: 'var(--accent-primary)', padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '12px' }}>
          <div>
            <strong>Multi-Session Chain Detected:</strong> {chain.chain.length} linked sessions in execution chain. Cross-session root cause attributed to session <code>{chain.cross_session_root_cause?.session_id}</code>.
          </div>
        </div>
      )}

      {/* Main Canvas & Inspector Layout */}
      {loading ? (
        <div className="card-surface" style={{ padding: '48px', textAlign: 'center', color: 'var(--text-muted)' }}>
          Loading trace graph execution nodes...
        </div>
      ) : error ? (
        <div className="card-surface" style={{ padding: '24px', color: 'var(--color-failure)', textAlign: 'center' }}>
          {error}
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px', alignItems: 'start' }}>
          {/* Main Execution Canvas */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <TraceGraph 
              nodes={detail?.nodes || []} 
              selectedNodeId={selectedNodeId} 
              onSelectNode={(id) => setSelectedNodeId(id)} 
            />

            {/* Root Cause Banner Card */}
            {detail?.root_cause && (
              <div className="card-surface" style={{ background: 'var(--color-failure-bg)', borderColor: 'rgba(255, 102, 122, 0.3)', padding: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-failure)', fontWeight: 700, fontSize: '14px', marginBottom: '8px' }}>
                  <AlertOctagon size={18} /> Root Cause Attributed to Node: <span className="mono">{detail.root_cause.node_id}</span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-primary)', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                  <div>Failure Type: <strong>{detail.root_cause.failure_type}</strong></div>
                  <div>Attribution Score: <strong>{detail.root_cause.attribution_score}</strong></div>
                  <div>Confidence Tier: <strong>{detail.root_cause.confidence_tier}</strong></div>
                </div>
              </div>
            )}
          </div>

          {/* Right Inspector Drawer */}
          <NodeInspector node={selectedNode} />
        </div>
      )}
    </div>
  );
};
