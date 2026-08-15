import type { TraceNode } from '../../types';
import { Clock } from 'lucide-react';

interface TimelinePanelProps {
  nodes: TraceNode[];
}

export const TimelinePanel: React.FC<TimelinePanelProps> = () => {
  const events = [
    { time: "14:32:08.100", type: "signal", text: "Planner dispatched execution DAG to Retriever & Tool", status: "info" },
    { time: "14:32:08.350", type: "signal", text: "Tool SQL/SearchInternal execution initiated", status: "info" },
    { time: "14:32:14.550", type: "anomaly", text: "Tool latency exceeded 8.0s timeout limit (8.45s observed)", status: "warning" },
    { time: "14:32:16.800", type: "propagation", text: "Tool retries exhausted (Attempt 3). ETIMEDOUT returned.", status: "error" },
    { time: "14:32:16.810", type: "propagation", text: "Generator received empty tool context -> Instruction following degraded to 0.40", status: "error" },
    { time: "14:32:18.670", type: "diagnosis", text: "Root Cause Engine attributed failure origin to tool_search_internal_db (Attribution Score: 0.82)", status: "success" }
  ];

  return (
    <div className="card-surface" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
        <Clock size={18} color="var(--accent-primary)" />
        <h3 style={{ fontSize: '15px' }}>Diagnostic Investigation Timeline</h3>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', paddingLeft: '8px' }}>
        {events.map((evt, idx) => (
          <div key={idx} style={{ display: 'flex', gap: '12px', alignItems: 'flex-start', position: 'relative' }}>
            <div className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)', width: '85px', flexShrink: 0, paddingTop: '2px' }}>
              {evt.time}
            </div>

            <div style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              background: evt.status === 'error' ? 'var(--color-failure)' : evt.status === 'warning' ? 'var(--color-warning)' : evt.status === 'success' ? 'var(--color-success)' : 'var(--accent-primary)',
              marginTop: '4px',
              flexShrink: 0
            }} />

            <div style={{ flex: 1, fontSize: '12px', color: 'var(--text-primary)', lineHeight: '1.4' }}>
              {evt.text}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
