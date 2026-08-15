import React from 'react';
import { ArrowLeft } from 'lucide-react';
import { navigate } from '../../router';
import { CodeBlock } from '../../components/common/CodeBlock';

export const DocsPage: React.FC = () => {
  return (
    <div style={{ background: '#080B12', color: '#F5F7FB', minHeight: '100vh', padding: '40px' }}>
      <button onClick={() => navigate('/app/overview')} className="obs-btn obs-btn-secondary" style={{ marginBottom: '24px' }}>
        <ArrowLeft size={14} /> Back to Dashboard
      </button>

      <div style={{ maxWidth: '850px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: 800 }}>AgentEval Technical Documentation</h1>
        <p style={{ color: '#9AA4B2', fontSize: '15px' }}>
          Comprehensive architecture reference, failure attribution methodology, and API contract specifications.
        </p>

        <div className="card-surface" style={{ background: '#111827' }}>
          <h2 style={{ fontSize: '18px', marginBottom: '8px' }}>1. What is AgentEval?</h2>
          <p style={{ color: '#9AA4B2', fontSize: '13px', lineHeight: '1.6' }}>
            AgentEval is a focused AI-agent observability and failure-attribution platform. It tracks multi-step agent executions (Planner, Retriever, Tool, Generator, Critic) and identifies the root cause of workflow failures through dependency graph propagation and empirical signal analysis.
          </p>
        </div>

        <div className="card-surface" style={{ background: '#111827' }}>
          <h2 style={{ fontSize: '18px', marginBottom: '8px' }}>2. API Contracts & Telemetry Ingestion</h2>
          <p style={{ color: '#9AA4B2', fontSize: '13px', marginBottom: '12px' }}>
            Telemetry trace nodes are ingested via <code>POST /api/v1/traces</code> or <code>POST /api/v1/traces/batch</code>.
          </p>
          <CodeBlock
            language="bash"
            code={`# Ingest trace node
POST /api/v1/traces
Headers: X-API-Key: ae_live_...
Body:
{
  "session_id": "trace_9912",
  "node_id": "tool_sql_exec",
  "node_type": "Tool",
  "timestamp_start": "2026-08-15T14:00:00Z",
  "timestamp_end": "2026-08-15T14:00:08Z",
  "tokens_in": 120,
  "tokens_out": 40
}`}
          />
        </div>
      </div>
    </div>
  );
};
