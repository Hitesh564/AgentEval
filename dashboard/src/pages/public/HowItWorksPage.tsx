import React from 'react';
import { ArrowLeft } from 'lucide-react';
import { navigate } from '../../router';

export const HowItWorksPage: React.FC = () => {
  return (
    <div style={{ background: '#080B12', color: '#F5F7FB', minHeight: '100vh', padding: '40px' }}>
      <button onClick={() => navigate('/app/overview')} className="obs-btn obs-btn-secondary" style={{ marginBottom: '24px' }}>
        <ArrowLeft size={14} /> Back to Dashboard
      </button>

      <div style={{ maxWidth: '850px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: 800 }}>How AgentEval Failure Attribution Works</h1>
        <p style={{ color: '#9AA4B2', fontSize: '15px' }}>
          Understanding the step-by-step diagnostic propagation pipeline.
        </p>

        <div className="card-surface" style={{ background: '#111827' }}>
          <h3 style={{ fontSize: '16px', marginBottom: '8px' }}>1. Signal Telemetry & Anomaly Extraction</h3>
          <p style={{ color: '#9AA4B2', fontSize: '13px', lineHeight: '1.6' }}>
            When an agent step executes, AgentEval records raw health scores, latency anomalies, retry counts, retriever cosine similarity, and groundedness ratios.
          </p>
        </div>

        <div className="card-surface" style={{ background: '#111827' }}>
          <h3 style={{ fontSize: '16px', marginBottom: '8px' }}>2. Backward Degradation Propagation</h3>
          <p style={{ color: '#9AA4B2', fontSize: '13px', lineHeight: '1.6' }}>
            If downstream steps (e.g. Generator or Critic) fail, AgentEval traces parent dependency links backward to determine whether the failure was caused by upstream quality degradation or an independent anomaly.
          </p>
        </div>

        <div className="card-surface" style={{ background: '#111827' }}>
          <h3 style={{ fontSize: '16px', marginBottom: '8px' }}>3. Root Cause Candidate Ranking</h3>
          <p style={{ color: '#9AA4B2', fontSize: '13px', lineHeight: '1.6' }}>
            Candidates are scored by causal origin scores and candidate separation margins. The candidate with the highest attribution score is isolated as the true failure origin.
          </p>
        </div>
      </div>
    </div>
  );
};
