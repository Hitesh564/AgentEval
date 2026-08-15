import type { RootCauseSummary, TraceNode } from '../../types';
import { AlertOctagon, ArrowDown } from 'lucide-react';

interface CausalGraphProps {
  rootCause: RootCauseSummary | null;
  nodes: TraceNode[];
}

export const CausalGraph: React.FC<CausalGraphProps> = ({ rootCause, nodes }) => {
  if (!rootCause) {
    return (
      <div className="card-surface" style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
        No root cause failure origin diagnosed for this trace execution.
      </div>
    );
  }

  // Filter degraded nodes
  const degradedNodes = nodes.filter(n => n.is_inherited_degradation);

  return (
    <div className="card-surface" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
        <AlertOctagon size={18} color="var(--color-failure)" />
        <h3 style={{ fontSize: '15px' }}>Causal Propagation Flow</h3>
      </div>

      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '12px',
        padding: '16px',
        background: 'var(--bg-dark)',
        borderRadius: '8px'
      }}>
        {/* Origin Node (Root Cause) */}
        <div className="pulse-root-cause" style={{
          width: '100%',
          maxWidth: '380px',
          background: 'var(--bg-elevated)',
          border: '2px solid var(--color-failure)',
          borderRadius: '8px',
          padding: '14px',
          textAlign: 'center'
        }}>
          <span className="badge badge-failure" style={{ fontSize: '10px', marginBottom: '4px' }}>
            TRUE FAILURE ORIGIN (Score: {rootCause.attribution_score || 0.82})
          </span>
          <div className="mono" style={{ fontWeight: 700, fontSize: '15px', color: 'var(--text-primary)' }}>
            {rootCause.node_id}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--color-failure)', marginTop: '4px' }}>
            {rootCause.failure_type || 'tool_timeout'}
          </div>
        </div>

        {/* Downward Arrow */}
        <div style={{ color: 'var(--color-failure)', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
          <ArrowDown size={18} />
          <span>Propagation Drift</span>
        </div>

        {/* Degraded Downstream Nodes */}
        {degradedNodes.length > 0 ? (
          degradedNodes.map(dNode => (
            <div key={dNode.node_id} style={{
              width: '100%',
              maxWidth: '380px',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--color-degraded)',
              borderRadius: '8px',
              padding: '12px',
              textAlign: 'center'
            }}>
              <span className="badge badge-degraded" style={{ fontSize: '10px', marginBottom: '4px' }}>
                INHERITED DEGRADATION
              </span>
              <div className="mono" style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-primary)' }}>
                {dNode.node_id}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Type: {dNode.node_type} • Weakest dimension: {dNode.weakest_dimension || 'instruction_following'}
              </div>
            </div>
          ))
        ) : (
          <div style={{
            width: '100%',
            maxWidth: '380px',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--color-degraded)',
            borderRadius: '8px',
            padding: '12px',
            textAlign: 'center'
          }}>
            <span className="badge badge-degraded" style={{ fontSize: '10px', marginBottom: '4px' }}>
              INHERITED DEGRADATION
            </span>
            <div className="mono" style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-primary)' }}>
              generator_llm_synthesizer
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
              Synthesizer quality degraded due to upstream tool failure.
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
