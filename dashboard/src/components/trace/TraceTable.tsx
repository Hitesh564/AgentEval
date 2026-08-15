import type { SessionSummary } from '../../types';
import { StatusBadge } from '../common/StatusBadge';
import { Clock, AlertOctagon } from 'lucide-react';
import { navigate } from '../../router';

interface TraceTableProps {
  sessions: SessionSummary[];
  onSelectSession?: (id: string) => void;
}

export const TraceTable: React.FC<TraceTableProps> = ({ sessions, onSelectSession }) => {
  if (!sessions || sessions.length === 0) {
    return (
      <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}>
        No traced sessions found matching criteria.
      </div>
    );
  }

  return (
    <div className="table-container">
      <table className="obs-table">
        <thead>
          <tr>
            <th>Trace Session ID</th>
            <th>Status</th>
            <th>Health Score</th>
            <th>Failure Attribution</th>
            <th>Timestamp</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((s) => {
            const dateStr = new Date(s.timestamp).toLocaleString();
            return (
              <tr 
                key={s.session_id} 
                className="clickable-row"
                onClick={() => onSelectSession ? onSelectSession(s.session_id) : navigate(`/app/traces/${s.session_id}`)}
              >
                <td className="mono" style={{ fontWeight: 600, color: 'var(--accent-primary)' }}>
                  {s.session_id}
                </td>
                <td>
                  <StatusBadge status={s.passed ? 'PASSED' : 'FAILED'} type={s.passed ? 'passed' : 'failed'} />
                </td>
                <td>
                  <StatusBadge healthScore={s.score} type="health" />
                </td>
                <td>
                  {s.failure_tag ? (
                    <StatusBadge status={s.failure_tag} type="failure_tag" />
                  ) : (
                    <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>None (Healthy)</span>
                  )}
                </td>
                <td style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <Clock size={12} /> {dateStr}
                  </span>
                </td>
                <td>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/app/traces/${s.session_id}`);
                      }}
                      className="obs-btn obs-btn-secondary"
                      style={{ padding: '4px 8px', fontSize: '11px' }}
                    >
                      Trace Detail
                    </button>
                    {!s.passed && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/app/root-cause/${s.session_id}`);
                        }}
                        className="obs-btn obs-btn-danger"
                        style={{ padding: '4px 8px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}
                      >
                        <AlertOctagon size={12} /> Root Cause
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
