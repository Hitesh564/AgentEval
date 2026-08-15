import type { RankedCandidate } from '../../types';
import { Layers } from 'lucide-react';

interface RankingPanelProps {
  candidates?: RankedCandidate[];
}

export const RankingPanel: React.FC<RankingPanelProps> = ({ candidates }) => {
  const list = candidates && candidates.length > 0 ? candidates : [
    { node_id: "tool_search_internal_db", node_type: "Tool", attribution_score: 0.82, failure_type: "tool_timeout" },
    { node_id: "retriever_vector_store", node_type: "Retriever", attribution_score: 0.54, failure_type: "retrieval_degradation" },
    { node_id: "generator_llm_synthesizer", node_type: "Generator", attribution_score: 0.31, failure_type: "instruction_following" }
  ];

  return (
    <div className="card-surface" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
        <Layers size={18} color="var(--accent-primary)" />
        <h3 style={{ fontSize: '15px' }}>Candidate Node Attribution Ranking</h3>
      </div>

      <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
        Failure attribution is modeled as a candidate node ranking problem over dependency graph trajectories.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {list.map((c, idx) => {
          const isTop = idx === 0;
          return (
            <div 
              key={c.node_id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px',
                background: isTop ? 'rgba(255, 102, 122, 0.08)' : 'var(--bg-dark)',
                border: `1px solid ${isTop ? 'var(--color-failure)' : 'var(--border-color)'}`,
                borderRadius: '6px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span className="mono" style={{ fontWeight: 800, fontSize: '14px', color: isTop ? 'var(--color-failure)' : 'var(--text-muted)' }}>
                  #{idx + 1}
                </span>
                <div>
                  <div className="mono" style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-primary)' }}>
                    {c.node_id}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Type: {c.node_type || 'Agent Step'} • Failure: {c.failure_type || 'N/A'}
                  </div>
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <div className="mono" style={{ fontWeight: 700, fontSize: '15px', color: isTop ? 'var(--color-failure)' : 'var(--accent-primary)' }}>
                  {c.attribution_score.toFixed(2)}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Attribution Score</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
