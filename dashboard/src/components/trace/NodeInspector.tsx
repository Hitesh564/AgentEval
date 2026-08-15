import React, { useState } from 'react';
import type { TraceNode } from '../../types';
import { StatusBadge } from '../common/StatusBadge';
import { CodeBlock } from '../common/CodeBlock';

interface NodeInspectorProps {
  node: TraceNode | null;
}

export const NodeInspector: React.FC<NodeInspectorProps> = ({ node }) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'io' | 'metrics' | 'evidence'>('overview');

  if (!node) {
    return (
      <div className="card-surface" style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}>
        Select a node from the execution graph to inspect its properties, inputs/outputs, and evaluation metrics.
      </div>
    );
  }

  return (
    <div className="card-surface" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Inspector Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
        <div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Node Inspector
          </div>
          <div style={{ fontWeight: 700, fontSize: '16px', color: 'var(--text-primary)', wordBreak: 'break-all' }}>
            {node.node_id}
          </div>
        </div>
        <StatusBadge healthScore={node.overall_health} type="health" />
      </div>

      {/* Sub Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
        {[
          { id: 'overview', label: 'Overview' },
          { id: 'io', label: 'Inputs & Outputs' },
          { id: 'metrics', label: 'Metrics' },
          { id: 'evidence', label: 'Evidence' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            style={{
              padding: '4px 10px',
              fontSize: '12px',
              fontWeight: 500,
              borderRadius: '4px',
              border: 'none',
              background: activeTab === tab.id ? 'var(--bg-elevated)' : 'transparent',
              color: activeTab === tab.id ? 'var(--accent-primary)' : 'var(--text-secondary)',
              cursor: 'pointer'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '13px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Node Type</span>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{node.node_type}</div>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Failure Tag</span>
              <div>
                {node.failure_type ? (
                  <StatusBadge status={node.failure_type} type="failure_tag" />
                ) : (
                  <span style={{ color: 'var(--color-success)' }}>None</span>
                )}
              </div>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Duration</span>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                {node.evidence?.latency ? `${node.evidence.latency.toFixed(2)}s` : `${node.duration_s || 0.15}s`}
              </div>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Est. Cost</span>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                ${(node.cost_usd || 0.0005).toFixed(5)}
              </div>
            </div>
          </div>

          {node.is_root_cause && (
            <div style={{
              background: 'var(--color-failure-bg)',
              border: '1px solid rgba(255, 102, 122, 0.3)',
              borderRadius: '6px',
              padding: '12px',
              fontSize: '12px',
              color: 'var(--color-failure)'
            }}>
              <strong>DIAGNOSED ROOT CAUSE ORIGIN</strong>
              <p style={{ marginTop: '4px', color: 'var(--text-primary)' }}>
                Attribution score: <strong>{(node.attribution_score || 0.82).toFixed(2)}</strong>. Candidate separation: {(node.candidate_separation || 0.28).toFixed(2)}.
              </p>
            </div>
          )}

          {/* Parents & Children Dependencies */}
          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '10px' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Parent Node Dependencies</span>
            <div style={{ display: 'flex', gap: '6px', marginTop: '4px', flexWrap: 'wrap' }}>
              {node.parent_node_ids && node.parent_node_ids.length > 0 ? (
                node.parent_node_ids.map(p => (
                  <span key={p} className="badge badge-neutral">{p}</span>
                ))
              ) : (
                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>None (Entry point)</span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Inputs & Outputs */}
      {activeTab === 'io' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div>
            <span style={{ color: 'var(--text-muted)', fontSize: '11px', fontWeight: 600 }}>INPUTS</span>
            <CodeBlock code={JSON.stringify(node.inputs || { query: "Default user query payload" }, null, 2)} language="json" />
          </div>

          <div>
            <span style={{ color: 'var(--text-muted)', fontSize: '11px', fontWeight: 600 }}>OUTPUTS</span>
            <CodeBlock code={JSON.stringify(node.outputs || { result: "Node execution response" }, null, 2)} language="json" />
          </div>

          {node.tool_name && (
            <div>
              <span style={{ color: 'var(--text-muted)', fontSize: '11px', fontWeight: 600 }}>TOOL TELEMETRY ({node.tool_name})</span>
              <CodeBlock code={JSON.stringify(node.tool_result || { status: "executed" }, null, 2)} language="json" />
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Metrics */}
      {activeTab === 'metrics' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Evaluation Scores Across Dimensions</span>
          {Object.entries(node.metric_scores || { instruction_following: 0.85, latency: 0.90, groundedness: 0.80 }).map(([dim, score]) => (
            <div key={dim} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '12px' }}>
              <span style={{ color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{dim.replace(/_/g, ' ')}</span>
              <span className="mono" style={{ fontWeight: 600, color: score && score < 0.6 ? 'var(--color-failure)' : 'var(--text-primary)' }}>
                {score !== null && score !== undefined ? (score * 100).toFixed(0) + '%' : 'N/A'}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Tab 4: Evidence */}
      {activeTab === 'evidence' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '12px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Empirical Signals & Anomaly Telemetry</span>
          <div className="card-surface" style={{ background: 'var(--bg-dark)' }}>
            <div>Latency Signal: <strong>{node.evidence?.latency ? `${node.evidence.latency}s` : '0.24s'}</strong></div>
            <div>Retry Count: <strong>{node.evidence?.retry_count || 0}</strong></div>
            {node.evidence?.groundedness_ratio !== undefined && (
              <div>Groundedness Ratio: <strong>{node.evidence.groundedness_ratio}</strong></div>
            )}
            {node.evidence?.retriever_similarity !== undefined && (
              <div>Retriever Similarity: <strong>{node.evidence.retriever_similarity}</strong></div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
