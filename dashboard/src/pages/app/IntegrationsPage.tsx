import React from 'react';
import { CodeBlock } from '../../components/common/CodeBlock';
import { navigate } from '../../router';

export const IntegrationsPage: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '900px' }}>
      {/* Header */}
      <div>
        <h1 style={{ fontSize: '20px', fontWeight: 700 }}>Developer Setup & Integrations</h1>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
          Connect your LangGraph pipelines, LangChain agents, or Python workflows to AgentEval in 6 simple steps.
        </p>
      </div>

      {/* Step 1 */}
      <div className="card-surface">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
          <div className="mono" style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'var(--accent-glow)', color: 'var(--accent-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '12px' }}>
            1
          </div>
          <h3 style={{ fontSize: '15px' }}>Install Python SDK Package</h3>
        </div>
        <CodeBlock language="bash" code="pip install agenteval" />
      </div>

      {/* Step 2 */}
      <div className="card-surface">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
          <div className="mono" style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'var(--accent-glow)', color: 'var(--accent-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '12px' }}>
            2
          </div>
          <h3 style={{ fontSize: '15px' }}>Generate API Key</h3>
        </div>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
          Generate a tenant integration key using the bootstrap key endpoint or the API Keys setup page.
        </p>
        <button onClick={() => navigate('/app/api-keys')} className="obs-btn obs-btn-primary" style={{ fontSize: '12px' }}>
          Generate API Key Now
        </button>
      </div>

      {/* Step 3 */}
      <div className="card-surface">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
          <div className="mono" style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'var(--accent-glow)', color: 'var(--accent-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '12px' }}>
            3
          </div>
          <h3 style={{ fontSize: '15px' }}>Configure Environment Variables</h3>
        </div>
        <CodeBlock 
          language="bash" 
          code={`export AGENTEVAL_API_URL="http://localhost:8000"
export AGENTEVAL_API_KEY="your_generated_api_key"`} 
        />
      </div>

      {/* Step 4 */}
      <div className="card-surface">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
          <div className="mono" style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'var(--accent-glow)', color: 'var(--accent-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '12px' }}>
            4
          </div>
          <h3 style={{ fontSize: '15px' }}>Attach AgentEval Callback to LangGraph</h3>
        </div>
        <CodeBlock 
          language="python" 
          code={`from agenteval.sdk.tracer import AgentEvalTracer

# Instantiate callback tracer
tracer = AgentEvalTracer(
    api_url="http://localhost:8000",
    api_key="your_generated_api_key"
)

# Attach to LangGraph pipeline
app = workflow.compile(checkpointer=memory, callbacks=[tracer])

# Execute agent run
inputs = {"messages": [("user", "Find Q3 security audit report")]}
output = app.invoke(inputs)`} 
        />
      </div>

      {/* Step 5 */}
      <div className="card-surface">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
          <div className="mono" style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'var(--accent-glow)', color: 'var(--accent-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '12px' }}>
            5
          </div>
          <h3 style={{ fontSize: '15px' }}>Inspect Failures in Dashboard</h3>
        </div>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
          Once your agent finishes running, trace telemetry will automatically stream into the Trace Explorer and Root Cause Analysis workspace.
        </p>
      </div>
    </div>
  );
};
