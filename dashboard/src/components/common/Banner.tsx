import React from 'react';
import { Info, WifiOff } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export const Banner: React.FC = () => {
  const { isDemoMode, setIsDemoMode, backendConnected, refreshHealth } = useApp();

  if (isDemoMode) {
    return (
      <div style={{
        background: 'rgba(108, 124, 255, 0.12)',
        borderBottom: '1px solid rgba(108, 124, 255, 0.3)',
        padding: '8px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: '12px',
        color: '#E0E7FF'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Info size={16} color="var(--accent-primary)" />
          <span>
            <strong>DEMO MODE ACTIVE</strong> — Displaying representative sample trace data (`demo_trace_001`).
          </span>
        </div>
        <button
          onClick={() => setIsDemoMode(false)}
          className="obs-btn obs-btn-secondary"
          style={{ padding: '2px 10px', fontSize: '11px' }}
        >
          Exit Demo Mode
        </button>
      </div>
    );
  }

  if (backendConnected === false) {
    return (
      <div style={{
        background: 'var(--color-failure-bg)',
        borderBottom: '1px solid rgba(255, 102, 122, 0.3)',
        padding: '8px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: '12px',
        color: 'var(--color-failure)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <WifiOff size={16} />
          <span>
            <strong>Unable to connect to AgentEval backend</strong> (http://localhost:8000). Ensure backend server is running.
          </span>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => refreshHealth()}
            className="obs-btn obs-btn-danger"
            style={{ padding: '2px 10px', fontSize: '11px' }}
          >
            Retry Connection
          </button>
          <button
            onClick={() => setIsDemoMode(true)}
            className="obs-btn obs-btn-secondary"
            style={{ padding: '2px 10px', fontSize: '11px' }}
          >
            Explore Demo Mode
          </button>
        </div>
      </div>
    );
  }

  return null;
};
