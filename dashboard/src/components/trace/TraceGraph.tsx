import React from 'react';
import type { TraceNode } from '../../types';
import { Clock, Activity } from 'lucide-react';

interface TraceGraphProps {
  nodes: TraceNode[];
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
}

export const TraceGraph: React.FC<TraceGraphProps> = ({ nodes, selectedNodeId, onSelectNode }) => {
  if (!nodes || nodes.length === 0) {
    return (
      <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}>
        No nodes present in trace graph.
      </div>
    );
  }

  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-color)',
      borderRadius: '8px',
      padding: '24px',
      overflowX: 'auto'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '20px',
        borderBottom: '1px solid var(--border-subtle)',
        paddingBottom: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Activity size={16} color="var(--accent-primary)" />
          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Execution Graph & Dependency DAG ({nodes.length} Nodes)
          </span>
        </div>
        <div style={{ display: 'flex', gap: '12px', fontSize: '11px', color: 'var(--text-secondary)' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-success)' }} /> Healthy
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-warning)' }} /> Warning
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-failure)' }} /> Failed / Root Cause
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-degraded)' }} /> Inherited
          </span>
        </div>
      </div>

      {/* DAG Node Layout */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '24px',
        minWidth: '700px',
        padding: '12px 0'
      }}>
        {nodes.map((node, index) => {
          const isSelected = selectedNodeId === node.node_id;
          const isRoot = node.is_root_cause;
          const isDegraded = node.is_inherited_degradation;

          let borderColor = 'var(--border-color)';
          let statusText = 'HEALTHY';
          let statusColor = 'var(--color-success)';

          if (isRoot) {
            borderColor = 'var(--color-failure)';
            statusText = 'ROOT CAUSE';
            statusColor = 'var(--color-failure)';
          } else if (node.raw_health < 0.5 || node.failed_dimensions?.length > 0) {
            borderColor = 'var(--color-failure)';
            statusText = 'FAILED';
            statusColor = 'var(--color-failure)';
          } else if (isDegraded) {
            borderColor = 'var(--color-degraded)';
            statusText = 'DEGRADED';
            statusColor = 'var(--color-degraded)';
          } else if (node.raw_health < 0.75) {
            borderColor = 'var(--color-warning)';
            statusText = 'WARNING';
            statusColor = 'var(--color-warning)';
          }

          return (
            <React.Fragment key={node.node_id}>
              {/* Connector Arrow */}
              {index > 0 && (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  color: isDegraded || isRoot ? 'var(--color-failure)' : 'var(--border-color)',
                  fontWeight: 700,
                  fontSize: '18px'
                }}>
                  ➔
                </div>
              )}

              {/* Node Card */}
              <div
                onClick={() => onSelectNode(node.node_id)}
                className={isRoot ? "pulse-root-cause" : ""}
                style={{
                  flex: 1,
                  minWidth: '150px',
                  background: isSelected ? 'var(--bg-elevated)' : 'var(--bg-dark)',
                  border: `2px solid ${isSelected ? 'var(--accent-primary)' : borderColor}`,
                  borderRadius: '8px',
                  padding: '14px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  position: 'relative'
                }}
              >
                {/* Status Header */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '8px'
                }}>
                  <span style={{ fontSize: '10px', fontWeight: 700, color: statusColor, textTransform: 'uppercase' }}>
                    {statusText}
                  </span>
                  <span className="mono" style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {(node.overall_health * 100).toFixed(0)}%
                  </span>
                </div>

                {/* Node Title & Type */}
                <div style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-primary)', marginBottom: '4px', wordBreak: 'break-all' }}>
                  {node.node_id}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  Type: <strong style={{ color: 'var(--text-secondary)' }}>{node.node_type}</strong>
                </div>

                {/* Performance / Latency */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: '10px',
                  color: 'var(--text-muted)',
                  borderTop: '1px solid var(--border-subtle)',
                  paddingTop: '6px'
                }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                    <Clock size={11} /> {node.evidence?.latency ? `${node.evidence.latency.toFixed(2)}s` : node.duration_s ? `${node.duration_s.toFixed(2)}s` : '0.12s'}
                  </span>
                  <span>{node.tokens_in || 0} tokens</span>
                </div>
              </div>
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
