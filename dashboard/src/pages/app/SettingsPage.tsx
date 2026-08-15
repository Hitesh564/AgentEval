import React from 'react';
import { useApp } from '../../context/AppContext';
import { Info } from 'lucide-react';
import { CodeBlock } from '../../components/common/CodeBlock';

export const SettingsPage: React.FC = () => {
  const { backendInfo } = useApp();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '850px' }}>
      <div>
        <h1 style={{ fontSize: '20px', fontWeight: 700 }}>System Configuration & Settings</h1>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
          Read-only environment variables, evaluation thresholds, and backend database parameters.
        </p>
      </div>

      <div className="card-surface" style={{ background: 'rgba(108, 124, 255, 0.08)', borderColor: 'var(--accent-primary)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-primary)', fontWeight: 600, fontSize: '13px', marginBottom: '4px' }}>
          <Info size={16} /> Environment Configuration Reference
        </div>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
          Server settings are configured via environment variables (`.env`). Backend mutation is disabled from the dashboard UI for security.
        </p>
      </div>

      <div className="card-surface" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <h3 style={{ fontSize: '15px' }}>Active Backend Parameters</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', fontSize: '13px' }}>
          <div>
            <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Database Backend</span>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{backendInfo?.database_backend || 'SQLite'}</div>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>CORS Allowed Origins</span>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>http://localhost:5173</div>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Semantic Gating</span>
            <div style={{ fontWeight: 600, color: 'var(--color-success)' }}>ENABLED (0.75 Threshold)</div>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Cache TTL</span>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>300 seconds (5 min)</div>
          </div>
        </div>
      </div>

      <div className="card-surface">
        <h3 style={{ fontSize: '15px', marginBottom: '12px' }}>Environment Variables Example</h3>
        <CodeBlock 
          language="bash"
          code={`# Backend Environment Configuration (.env)
AGENTEVAL_DATABASE_URL=sqlite:///./agenteval.db
PORT=8000
HOST=127.0.0.1
AGENTEVAL_CORS_ORIGINS=http://localhost:5173
AGENTEVAL_ADMIN_BOOTSTRAP_KEY=ae_admin_sec_9941`}
        />
      </div>
    </div>
  );
};
