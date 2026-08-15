import type { RootCauseSummary, TraceNode } from '../../types';
import { FileText } from 'lucide-react';

interface EvidencePanelProps {
  rootCause: RootCauseSummary | null;
  node: TraceNode | null;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({ node }) => {
  const evidenceItems = [
    {
      signal: "Execution Anomaly (Latency)",
      observed: `${node?.evidence?.latency ? node.evidence.latency.toFixed(2) : '8.45'}s (Baseline: 0.35s)`,
      impact: "Critical delay exceeding 8.0s limit across 3 retry attempts."
    },
    {
      signal: "Retry Count Telemetry",
      observed: `${node?.evidence?.retry_count || 3} Retries Executed`,
      impact: "Exhausted connection pool and propagated timeout downstream."
    },
    {
      signal: "Retriever Similarity",
      observed: `${node?.evidence?.retriever_similarity || 0.72} Cosine Similarity`,
      impact: "Slight embedding drift; insufficient to trigger standalone retrieval error."
    },
    {
      signal: "Downstream Groundedness",
      observed: `${node?.evidence?.groundedness_ratio || 0.50} Ratio`,
      impact: "Directly impacted synthesizer node due to missing tool context."
    }
  ];

  return (
    <div className="card-surface" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
        <FileText size={18} color="var(--accent-secondary)" />
        <h3 style={{ fontSize: '15px' }}>Diagnostic Evidence Breakdown</h3>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {evidenceItems.map((item, idx) => (
          <div key={idx} className="card-surface" style={{ background: 'var(--bg-dark)', padding: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>
              <span style={{ color: 'var(--text-primary)' }}>{item.signal}</span>
              <span className="mono" style={{ color: 'var(--accent-secondary)' }}>{item.observed}</span>
            </div>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', margin: 0 }}>
              {item.impact}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};
