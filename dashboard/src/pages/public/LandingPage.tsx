import React, { useState } from 'react';
import { 
  AlertOctagon, 
  ArrowRight, 
  GitBranch, 
  Sparkles
} from 'lucide-react';
import { navigate } from '../../router';
import { CodeBlock } from '../../components/common/CodeBlock';

export const LandingPage: React.FC = () => {
  const [activeStep, setActiveStep] = useState<number>(3); // 0: Trace, 1: Health, 2: Propagation, 3: Evidence, 4: Root Cause

  return (
    <div style={{ background: '#080B12', color: '#F5F7FB', minHeight: '100vh', fontFamily: 'var(--font-sans)' }}>
      {/* Navbar */}
      <nav style={{
        padding: '20px 40px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid #1E2A3F',
        position: 'sticky',
        top: 0,
        background: 'rgba(8, 11, 18, 0.9)',
        backdropFilter: 'blur(8px)',
        zIndex: 100
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '8px',
            background: 'linear-gradient(135deg, #6C7CFF 0%, #40D9FF 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 800,
            fontSize: '16px'
          }}>
            AE
          </div>
          <span style={{ fontWeight: 700, fontSize: '18px', letterSpacing: '-0.02em' }}>
            AgentEval
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '24px', fontSize: '14px', color: '#9AA4B2' }}>
          <a href="#problem" style={{ color: 'inherit' }}>Problem</a>
          <a href="#workflow" style={{ color: 'inherit' }}>Workflow</a>
          <a href="#benchmarks" style={{ color: 'inherit' }}>Benchmarks</a>
          <a href="#integration" style={{ color: 'inherit' }}>Integration</a>
          <a href="https://github.com/Hitesh564/AgentEval" target="_blank" rel="noreferrer" style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#F5F7FB' }}>
            <GitBranch size={16} /> GitHub
          </a>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button 
            onClick={() => navigate('/demo')}
            className="obs-btn obs-btn-secondary"
            style={{ padding: '8px 16px', fontSize: '13px' }}
          >
            Explore Demo
          </button>
          <button 
            onClick={() => navigate('/app/overview')}
            className="obs-btn obs-btn-primary"
            style={{ padding: '8px 18px', fontSize: '13px' }}
          >
            Start Debugging <ArrowRight size={14} />
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <section style={{
        padding: '90px 20px 70px 20px',
        textAlign: 'center',
        maxWidth: '1100px',
        margin: '0 auto'
      }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          padding: '4px 12px',
          borderRadius: '20px',
          background: 'rgba(108, 124, 255, 0.1)',
          border: '1px solid rgba(108, 124, 255, 0.3)',
          color: '#6C7CFF',
          fontSize: '12px',
          fontWeight: 600,
          marginBottom: '24px'
        }}>
          <Sparkles size={14} /> AI-AGENT OBSERVABILITY & FAILURE ATTRIBUTION
        </div>

        <h1 style={{
          fontSize: '52px',
          fontWeight: 800,
          lineHeight: '1.1',
          letterSpacing: '-0.03em',
          marginBottom: '20px',
          background: 'linear-gradient(180deg, #FFFFFF 0%, #9AA4B2 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent'
        }}>
          Understand why your AI agents fail.
        </h1>

        <p style={{
          fontSize: '18px',
          color: '#9AA4B2',
          maxWidth: '720px',
          margin: '0 auto 36px auto',
          lineHeight: '1.6'
        }}>
          Trace multi-step agent executions, follow failure propagation across tools and LLMs, and identify the exact evidence behind likely root causes.
        </p>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '16px' }}>
          <button 
            onClick={() => navigate('/app/overview')}
            className="obs-btn obs-btn-primary"
            style={{ padding: '12px 28px', fontSize: '15px', fontWeight: 600 }}
          >
            Start Debugging Workflows <ArrowRight size={16} />
          </button>
          <button 
            onClick={() => navigate('/demo')}
            className="obs-btn obs-btn-secondary"
            style={{ padding: '12px 24px', fontSize: '15px' }}
          >
            Launch Live Interactive Demo
          </button>
        </div>

        {/* Hero Interactive Workflow Graph */}
        <div style={{
          marginTop: '60px',
          background: '#111827',
          border: '1px solid #263247',
          borderRadius: '12px',
          padding: '32px',
          textAlign: 'left',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px', borderBottom: '1px solid #263247', paddingBottom: '16px' }}>
            <span style={{ fontSize: '13px', fontWeight: 600, color: '#9AA4B2', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Execution Graph Debugger — Session <span className="mono" style={{ color: '#F5F7FB' }}>demo_trace_001</span>
            </span>
            <div style={{ display: 'flex', gap: '8px' }}>
              {['Trace', 'Node Health', 'Propagation', 'Evidence', 'Root Cause'].map((step, idx) => (
                <button
                  key={step}
                  onClick={() => setActiveStep(idx)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    border: '1px solid',
                    borderColor: activeStep === idx ? '#6C7CFF' : '#263247',
                    background: activeStep === idx ? 'rgba(108, 124, 255, 0.15)' : 'transparent',
                    color: activeStep === idx ? '#6C7CFF' : '#9AA4B2'
                  }}
                >
                  {idx + 1}. {step}
                </button>
              ))}
            </div>
          </div>

          {/* Interactive Graph Node Display */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(5, 1fr)',
            gap: '16px',
            alignItems: 'center',
            position: 'relative'
          }}>
            {/* Node 1: Planner */}
            <div style={{
              background: '#151E2E',
              border: '1px solid #35D39A',
              borderRadius: '8px',
              padding: '16px',
              textAlign: 'center'
            }}>
              <div style={{ fontSize: '11px', color: '#35D39A', fontWeight: 700, marginBottom: '4px' }}>HEALTHY 95%</div>
              <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '4px' }}>Planner</div>
              <div style={{ fontSize: '11px', color: '#9AA4B2' }}>0.24s • 225 tokens</div>
            </div>

            {/* Connector */}
            <div style={{ textAlign: 'center', color: '#64748B' }}>➔</div>

            {/* Node 2: Tool (Root Cause) */}
            <div className={activeStep >= 2 ? "pulse-root-cause" : ""} style={{
              background: '#151E2E',
              border: '2px solid #FF667A',
              borderRadius: '8px',
              padding: '16px',
              textAlign: 'center',
              position: 'relative'
            }}>
              <div style={{
                position: 'absolute',
                top: '-10px',
                right: '10px',
                background: '#FF667A',
                color: '#FFFFFF',
                fontSize: '9px',
                fontWeight: 800,
                padding: '2px 6px',
                borderRadius: '4px'
              }}>
                ROOT CAUSE ORIGIN
              </div>
              <div style={{ fontSize: '11px', color: '#FF667A', fontWeight: 700, marginBottom: '4px' }}>FAILED 20%</div>
              <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '4px' }}>Tool / SQL</div>
              <div style={{ fontSize: '11px', color: '#9AA4B2' }}>8.45s timeout (3 retries)</div>
            </div>

            {/* Connector */}
            <div style={{ textAlign: 'center', color: '#FF667A' }}>➔</div>

            {/* Node 3: Generator (Degraded) */}
            <div style={{
              background: '#151E2E',
              border: '1px solid #A78BFA',
              borderRadius: '8px',
              padding: '16px',
              textAlign: 'center'
            }}>
              <div style={{ fontSize: '11px', color: '#A78BFA', fontWeight: 700, marginBottom: '4px' }}>INHERITED DEGRADATION</div>
              <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '4px' }}>Generator LLM</div>
              <div style={{ fontSize: '11px', color: '#9AA4B2' }}>Partial synthesis</div>
            </div>
          </div>

          {/* Diagnostic Evidence Explanation */}
          <div style={{
            marginTop: '24px',
            padding: '16px',
            background: 'rgba(255, 102, 122, 0.08)',
            border: '1px solid rgba(255, 102, 122, 0.2)',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <AlertOctagon color="#FF667A" size={24} />
              <div>
                <div style={{ fontWeight: 600, fontSize: '13px', color: '#F5F7FB' }}>
                  Root Cause Attributed: <span className="mono" style={{ color: '#FF667A' }}>tool_search_internal_db</span> (Attribution Score: 0.82)
                </div>
                <div style={{ fontSize: '12px', color: '#9AA4B2' }}>
                  Signal: Database query latency exceeded 8.0s timeout limit across 3 retry attempts, causing downstream generator quality degradation.
                </div>
              </div>
            </div>
            <button 
              onClick={() => navigate('/app/root-cause/demo_trace_001')}
              className="obs-btn obs-btn-danger"
              style={{ padding: '6px 14px', fontSize: '12px', whiteSpace: 'nowrap' }}
            >
              Investigate Evidence
            </button>
          </div>
        </div>
      </section>

      {/* Section 1: Light Visual Contrast — The Core Problem */}
      <section id="problem" style={{
        background: '#0B101A',
        borderTop: '1px solid #1C2738',
        borderBottom: '1px solid #1C2738',
        padding: '80px 20px'
      }}>
        <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '48px' }}>
            <h2 style={{ fontSize: '32px', fontWeight: 700, marginBottom: '12px' }}>
              Why traditional tracing fails for agentic workflows
            </h2>
            <p style={{ color: '#9AA4B2', fontSize: '16px', maxWidth: '640px', margin: '0 auto' }}>
              When a complex multi-step AI agent fails, the node that ultimately throws an error or outputs poor response quality is rarely the true origin of failure.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '32px' }}>
            <div className="card-surface" style={{ background: '#111827', border: '1px solid #263247' }}>
              <div style={{ color: '#FF667A', fontWeight: 700, fontSize: '14px', marginBottom: '8px' }}>
                Traditional LLM Observability
              </div>
              <h3 style={{ fontSize: '18px', marginBottom: '12px' }}>Symptom-Level Error Alerting</h3>
              <p style={{ color: '#9AA4B2', fontSize: '13px', lineHeight: '1.6' }}>
                Flags the final Generator or Critic node because its quality score dropped. Engineers spend hours debugging prompts, unaware that the actual cause was a stale vector retrieval 3 steps upstream.
              </p>
            </div>

            <div className="card-surface" style={{ background: '#111827', border: '1px solid #6C7CFF' }}>
              <div style={{ color: '#35D39A', fontWeight: 700, fontSize: '14px', marginBottom: '8px' }}>
                AgentEval Failure Attribution
              </div>
              <h3 style={{ fontSize: '18px', marginBottom: '12px' }}>Causal Propagation & Root Cause Ranking</h3>
              <p style={{ color: '#9AA4B2', fontSize: '13px', lineHeight: '1.6' }}>
                Propagates degradation graph signals backward through execution parents, isolating true failure origins with empirical evidence, retry latency signals, and groundedness metrics.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Section 2: Product Workflow Journey */}
      <section id="workflow" style={{ padding: '80px 20px', maxWidth: '1000px', margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: '48px' }}>
          <h2 style={{ fontSize: '32px', fontWeight: 700, marginBottom: '12px' }}>
            The AgentEval Diagnostic Workflow
          </h2>
          <p style={{ color: '#9AA4B2', fontSize: '16px' }}>
            From raw trace telemetry to automated root cause diagnosis and recommendation.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
          {[
            { step: "01", title: "Trace Ingestion", desc: "Capture multi-step nodes, retries, tool calls, and inputs/outputs via hosted SDK or FastAPI endpoint." },
            { step: "02", title: "Node Evaluation", desc: "Evaluate instruction-following, groundedness ratio, retriever similarity, and schema validity." },
            { step: "03", title: "Failure Propagation", desc: "Calculate raw vs adjusted health scores across parent-child dependencies to trace error drift." },
            { step: "04", title: "Root Cause Ranking", desc: "Rank candidate nodes by causal origin scores and deliver actionable optimization recommendations." }
          ].map((item) => (
            <div key={item.step} className="card-surface" style={{ padding: '20px' }}>
              <div className="mono" style={{ fontSize: '24px', fontWeight: 800, color: '#6C7CFF', marginBottom: '8px' }}>
                {item.step}
              </div>
              <h4 style={{ fontSize: '15px', marginBottom: '8px' }}>{item.title}</h4>
              <p style={{ color: '#9AA4B2', fontSize: '12px', lineHeight: '1.5' }}>{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Section 3: Empirical Benchmarks */}
      <section id="benchmarks" style={{
        background: '#0B101A',
        borderTop: '1px solid #1C2738',
        borderBottom: '1px solid #1C2738',
        padding: '80px 20px'
      }}>
        <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '40px' }}>
            <h2 style={{ fontSize: '32px', fontWeight: 700, marginBottom: '12px' }}>
              Rigorous Empirical Validation
            </h2>
            <p style={{ color: '#9AA4B2', fontSize: '16px' }}>
              Evaluated on controlled benchmarks and independent external datasets.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            <div className="card-surface">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <h3 style={{ fontSize: '16px' }}>Controlled Internal Benchmark</h3>
                <span className="badge badge-success">73.3% Accuracy</span>
              </div>
              <p style={{ color: '#9AA4B2', fontSize: '13px', marginBottom: '16px' }}>
                Evaluated across multi-turn agent pipelines with synthetic tool failures, retrieval degradation, and schema violations.
              </p>
              <div style={{ fontSize: '28px', fontWeight: 700, color: '#35D39A', fontFamily: 'var(--font-mono)' }}>
                73.3%
              </div>
              <div style={{ fontSize: '11px', color: '#9AA4B2' }}>Root-cause origin detection accuracy</div>
            </div>

            <div className="card-surface">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <h3 style={{ fontSize: '16px' }}>External Who&When Benchmark</h3>
                <span className="badge badge-neutral">184 Test Cases</span>
              </div>
              <p style={{ color: '#9AA4B2', fontSize: '13px', marginBottom: '16px' }}>
                Rigorous independent benchmark evaluating step-level and agent-level failure attribution across real multi-agent datasets.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <div style={{ fontSize: '22px', fontWeight: 700, color: '#F5F7FB', fontFamily: 'var(--font-mono)' }}>40.8%</div>
                  <div style={{ fontSize: '11px', color: '#9AA4B2' }}>Agent-Level Accuracy</div>
                </div>
                <div>
                  <div style={{ fontSize: '22px', fontWeight: 700, color: '#F5F7FB', fontFamily: 'var(--font-mono)' }}>14.7%</div>
                  <div style={{ fontSize: '11px', color: '#9AA4B2' }}>Step-Level Exact Match</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section 4: Developer Integration */}
      <section id="integration" style={{ padding: '80px 20px', maxWidth: '1000px', margin: '0 auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '40px', alignItems: 'center' }}>
          <div>
            <span style={{ color: '#6C7CFF', fontWeight: 600, fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Developer First Integration
            </span>
            <h2 style={{ fontSize: '32px', fontWeight: 700, marginTop: '8px', marginBottom: '16px' }}>
              Instrument your LangGraph & Python agents in 3 lines
            </h2>
            <p style={{ color: '#9AA4B2', fontSize: '14px', lineHeight: '1.6', marginBottom: '24px' }}>
              AgentEval provides lightweight callback handlers and a hosted client SDK that seamlessly captures node boundaries, retries, and tool telemetry without slowing down your execution loop.
            </p>
            <button 
              onClick={() => navigate('/app/integrations')}
              className="obs-btn obs-btn-primary"
            >
              View Integration Docs <ArrowRight size={14} />
            </button>
          </div>

          <div>
            <CodeBlock 
              language="python"
              code={`from agenteval.sdk.tracer import AgentEvalTracer

# Initialize tracer with API key
tracer = AgentEvalTracer(
    api_url="http://localhost:8000",
    api_key="ae_live_891f..."
)

# Connect callback handler to LangGraph pipeline
app.compile(checkpointer=memory, callbacks=[tracer])`}
            />
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section style={{
        background: 'linear-gradient(180deg, #0B101A 0%, #080B12 100%)',
        borderTop: '1px solid #1C2738',
        padding: '80px 20px',
        textAlign: 'center'
      }}>
        <h2 style={{ fontSize: '36px', fontWeight: 800, marginBottom: '16px' }}>
          Ready to diagnose your agent failures?
        </h2>
        <p style={{ color: '#9AA4B2', fontSize: '16px', maxWidth: '540px', margin: '0 auto 32px auto' }}>
          Open the observability dashboard or explore the interactive trace debugger in Demo Mode now.
        </p>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '16px' }}>
          <button 
            onClick={() => navigate('/app/overview')}
            className="obs-btn obs-btn-primary"
            style={{ padding: '12px 28px', fontSize: '15px' }}
          >
            Open Dashboard <ArrowRight size={16} />
          </button>
          <button 
            onClick={() => navigate('/demo')}
            className="obs-btn obs-btn-secondary"
            style={{ padding: '12px 24px', fontSize: '15px' }}
          >
            Try Live Demo Mode
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer style={{
        padding: '24px 40px',
        borderTop: '1px solid #1C2738',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: '12px',
        color: '#64748B'
      }}>
        <div>AgentEval AI-Agent Observability & Failure Attribution Platform</div>
        <div style={{ display: 'flex', gap: '16px' }}>
          <a href="https://github.com/Hitesh564/AgentEval" target="_blank" rel="noreferrer" style={{ color: 'inherit' }}>GitHub Repository</a>
          <span>•</span>
          <span style={{ color: '#9AA4B2' }}>v1.0.0 Production</span>
        </div>
      </footer>
    </div>
  );
};
