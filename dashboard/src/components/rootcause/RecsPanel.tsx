import type { NodeRecommendation } from '../../types';
import { CheckCircle2 } from 'lucide-react';

interface RecsPanelProps {
  recommendations?: NodeRecommendation[];
}

export const RecsPanel: React.FC<RecsPanelProps> = ({ recommendations }) => {
  const recs = recommendations && recommendations.length > 0 ? recommendations : [
    {
      problem: "Database query execution exceeded 8.0s timeout limit across 3 retry attempts.",
      evidence: "Latency spike to 8.45s (baseline 0.35s). 3 retries occurred, causing cascading timeout in downstream generator.",
      recommended_action: "Increase database indexing on `audit_records` table and add connection pool circuit breaker.",
      expected_effect: "Reduces tool latency by ~85% and prevents downstream timeout propagation.",
      priority: "high",
      confidence: 0.94
    }
  ];

  return (
    <div className="card-surface" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
        <CheckCircle2 size={18} color="var(--color-success)" />
        <h3 style={{ fontSize: '15px' }}>Actionable Fix Recommendations</h3>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {recs.map((rec, idx) => (
          <div key={idx} className="card-surface" style={{ background: 'var(--bg-dark)', border: '1px solid var(--border-color)', padding: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span className={`badge ${rec.priority === 'high' ? 'badge-failure' : 'badge-warning'}`}>
                {rec.priority} Priority
              </span>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Confidence: <strong style={{ color: 'var(--color-success)' }}>{(rec.confidence * 100).toFixed(0)}%</strong>
              </span>
            </div>

            <h4 style={{ fontSize: '14px', marginBottom: '6px', color: 'var(--text-primary)' }}>
              {rec.problem}
            </h4>

            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px', lineHeight: '1.5' }}>
              <strong>Evidence:</strong> {rec.evidence}
            </p>

            <div style={{
              background: 'var(--bg-elevated)',
              borderLeft: '3px solid var(--color-success)',
              padding: '10px 12px',
              borderRadius: '0 4px 4px 0',
              fontSize: '12px'
            }}>
              <div style={{ color: 'var(--color-success)', fontWeight: 600, marginBottom: '2px' }}>
                Recommended Action:
              </div>
              <div style={{ color: 'var(--text-primary)' }}>
                {rec.recommended_action}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                <strong>Expected Impact:</strong> {rec.expected_effect}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
