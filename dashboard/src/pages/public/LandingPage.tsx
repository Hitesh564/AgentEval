import React, { useState, useEffect, useRef } from 'react';
import { navigate } from '../../router';
import '../../landing.css';

/* ============================================================
   AGENTEVAL — PUBLIC LANDING PAGE
   Editorial · Typography-First · Grid-Based · Premium · Minimal
   ============================================================ */

// ── Intersection Observer hook for scroll-reveal ──
function useReveal(): [React.RefObject<HTMLDivElement | null>, boolean] {
  const ref = useRef<HTMLDivElement | null>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setVisible(true); obs.unobserve(el); } },
      { threshold: 0.15 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return [ref, visible];
}

// ── Counter animation hook ──
function useCountUp(target: number, visible: boolean, decimals = 0, duration = 1200): string {
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (!visible) return;
    const start = performance.now();
    const tick = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out
      const eased = 1 - Math.pow(1 - progress, 3);
      setVal(eased * target);
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [visible, target, duration]);
  return val.toFixed(decimals);
}

// ── Small reusable section wrapper with reveal ──
const RevealSection: React.FC<{
  id?: string;
  className?: string;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({ id, className = '', style, children }) => {
  const [ref, visible] = useReveal();
  return (
    <section
      id={id}
      ref={ref}
      className={`l-section l-reveal ${visible ? 'visible' : ''} ${className}`}
      style={style}
    >
      {children}
    </section>
  );
};

export const LandingPage: React.FC = () => {
  const [scrolled, setScrolled] = useState(false);
  const [activeSeq, setActiveSeq] = useState(0);
  const [trustRef, trustVisible] = useReveal();

  // Navbar scroll effect
  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 10);
    window.addEventListener('scroll', handler, { passive: true });
    return () => window.removeEventListener('scroll', handler);
  }, []);

  // Count-up values for trust strip
  const count184 = useCountUp(184, trustVisible);
  const count408 = useCountUp(40.8, trustVisible, 1);
  const count733 = useCountUp(73.3, trustVisible, 1);

  return (
    <div className="landing">
      {/* ════════════════════════════════════════════
          NAVIGATION
          ════════════════════════════════════════════ */}
      <nav className={`l-nav ${scrolled ? 'scrolled' : ''}`}>
        <div className="l-container l-nav-inner">
          <div className="l-nav-brand" onClick={() => navigate('/')}>
            <div className="l-nav-logo">AE</div>
            <span className="l-nav-name">AgentEval</span>
          </div>

          <div className="l-nav-links">
            <a href="#product" className="l-nav-link">Product</a>
            <a href="#how-it-works" className="l-nav-link">How It Works</a>
            <a href="#benchmarks" className="l-nav-link">Benchmarks</a>
            <span className="l-nav-link" onClick={() => navigate('/docs')}>Documentation</span>
            <a href="https://github.com/Hitesh564/AgentEval" target="_blank" rel="noreferrer" className="l-nav-link">GitHub</a>
          </div>

          <div className="l-nav-actions">
            <button className="l-btn l-btn-text" onClick={() => navigate('/app/overview')}>Sign In</button>
            <button className="l-btn l-btn-primary" onClick={() => navigate('/app/overview')}>Get Started</button>
          </div>
        </div>
      </nav>

      {/* ════════════════════════════════════════════
          HERO
          ════════════════════════════════════════════ */}
      <section className="l-hero">
        <div className="l-container l-hero-grid">
          {/* Left: Editorial copy */}
          <div>
            <div className="l-hero-eyebrow">AI Agent Failure Diagnosis</div>
            <h1 className="l-hero-headline">
              Understand why<br />your AI agents <em>fail.</em>
            </h1>
            <p className="l-hero-body">
              Trace execution. Follow failure propagation. Identify the evidence behind likely root causes.
            </p>
            <div className="l-hero-actions">
              <button className="l-btn l-btn-primary" onClick={() => navigate('/app/overview')}>
                Start debugging
              </button>
              <button className="l-btn l-btn-secondary" onClick={() => navigate('/demo')}>
                Explore demo
              </button>
            </div>
          </div>

          {/* Right: Execution visualization */}
          <div className="l-hero-viz">
            <div className="l-hero-viz-header">
              <span>agenteval / trace / demo_trace_001</span>
              <span style={{ color: '#F85149' }}>● FAILURE DETECTED</span>
            </div>
            <div className="l-hero-viz-body">
              {/* Execution graph row */}
              <div className="l-graph-row">
                <div className="l-graph-node healthy">
                  <div className="l-graph-node-status" style={{ color: '#3FB950' }}>HEALTHY</div>
                  <div className="l-graph-node-label">Planner</div>
                  <div className="l-graph-node-meta">0.24s · 225 tok</div>
                </div>
                <div className="l-graph-arrow">→</div>
                <div className="l-graph-node healthy">
                  <div className="l-graph-node-status" style={{ color: '#3FB950' }}>HEALTHY</div>
                  <div className="l-graph-node-label">Retriever</div>
                  <div className="l-graph-node-meta">0.18s · 3 docs</div>
                </div>
                <div className="l-graph-arrow">→</div>
                <div className="l-graph-node failed">
                  <div className="l-graph-node-badge">LIKELY ROOT CAUSE</div>
                  <div className="l-graph-node-status" style={{ color: '#F85149' }}>FAILED</div>
                  <div className="l-graph-node-label">Tool</div>
                  <div className="l-graph-node-meta">8.45s timeout</div>
                </div>
                <div className="l-graph-arrow trace-animate" style={{ color: '#F85149' }}>→</div>
                <div className="l-graph-node degraded">
                  <div className="l-graph-node-status" style={{ color: '#D29922' }}>DEGRADED</div>
                  <div className="l-graph-node-label">Generator</div>
                  <div className="l-graph-node-meta">partial output</div>
                </div>
                <div className="l-graph-arrow trace-animate" style={{ color: '#F85149' }}>→</div>
                <div className="l-graph-node failed">
                  <div className="l-graph-node-status" style={{ color: '#F85149' }}>FAILED</div>
                  <div className="l-graph-node-label">Critic</div>
                  <div className="l-graph-node-meta">quality 0.31</div>
                </div>
              </div>

              {/* Trace-back attribution */}
              <div className="l-graph-trace-back">
                <div>
                  <div className="l-graph-trace-label">
                    Traced backward: Critic failure → Generator degradation → <strong>Tool anomaly</strong>
                  </div>
                  <div className="l-graph-trace-sub">
                    Attribution score: 0.82 — Latency anomaly, retry exhaustion, downstream propagation
                  </div>
                </div>
                <button className="l-btn l-btn-primary" style={{ fontSize: '12px', padding: '6px 14px' }} onClick={() => navigate('/app/root-cause/demo_trace_001')}>
                  Investigate →
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════
          TRUST STRIP
          ════════════════════════════════════════════ */}
      <div className="l-trust" ref={trustRef}>
        <div className="l-container l-trust-inner">
          <div className="l-trust-stat">
            <div className="l-trust-num">{count184}</div>
            <div className="l-trust-label">External benchmark cases</div>
          </div>
          <div className="l-trust-stat">
            <div className="l-trust-num">{count408}%</div>
            <div className="l-trust-label">Agent-level accuracy</div>
          </div>
          <div className="l-trust-stat">
            <div className="l-trust-num">{count733}%</div>
            <div className="l-trust-label">Internal benchmark accuracy</div>
          </div>
        </div>
      </div>

      {/* ════════════════════════════════════════════
          PROBLEM SECTION
          ════════════════════════════════════════════ */}
      <RevealSection id="product">
        <div className="l-container l-asym">
          <div>
            <div className="l-section-eyebrow">The Core Problem</div>
            <h2 className="l-section-headline">
              A failed node<br />isn't necessarily<br />the root cause.
            </h2>
            <p className="l-section-body">
              Agent workflows can fail downstream from the event that actually caused the degradation. Debugging the node that throws an error wastes engineering hours when the true origin is steps upstream.
            </p>
          </div>

          <div className="l-propagation">
            <div className="l-prop-node" style={{ borderColor: 'var(--failure)' }}>
              <div className="l-prop-node-name">Tool</div>
              <div className="l-prop-node-status" style={{ color: 'var(--failure)' }}>8.45s timeout — 3 retries</div>
            </div>
            <div className="l-prop-arrow"></div>
            <div className="l-prop-node" style={{ borderColor: 'var(--degraded)' }}>
              <div className="l-prop-node-name">Generator</div>
              <div className="l-prop-node-status" style={{ color: 'var(--degraded)' }}>Partial synthesis</div>
            </div>
            <div className="l-prop-arrow"></div>
            <div className="l-prop-node" style={{ borderColor: 'var(--failure)' }}>
              <div className="l-prop-node-name">Critic</div>
              <div className="l-prop-node-status" style={{ color: 'var(--failure)' }}>Quality check failed</div>
            </div>
            <div className="l-prop-verdict">
              <div className="l-prop-verdict-item">
                <div className="l-prop-verdict-label">Visible failure</div>
                <div className="l-prop-verdict-value">Critic</div>
              </div>
              <div className="l-prop-verdict-item">
                <div className="l-prop-verdict-label">Likely origin</div>
                <div className="l-prop-verdict-value" style={{ color: 'var(--failure)' }}>Tool</div>
              </div>
            </div>
          </div>
        </div>
      </RevealSection>

      {/* ════════════════════════════════════════════
          INVESTIGATION SEQUENCE
          ════════════════════════════════════════════ */}
      <RevealSection id="how-it-works">
        <div className="l-container">
          <div style={{ marginBottom: '48px' }}>
            <div className="l-section-eyebrow">How It Works</div>
            <h2 className="l-section-headline">From trace to root cause.</h2>
          </div>

          <div className="l-sequence">
            {[
              { num: '01', title: 'Trace', desc: 'Capture multi-step agent execution: nodes, retries, tool calls, LLM inputs and outputs.' },
              { num: '02', title: 'Health', desc: 'Evaluate each node: instruction-following, groundedness, retrieval quality, latency, schema validity.' },
              { num: '03', title: 'Propagation', desc: 'Calculate raw vs. adjusted health scores across parent-child dependencies to trace error drift.' },
              { num: '04', title: 'Evidence', desc: 'Collect signals: latency anomalies, retry counts, quality degradation, schema violations.' },
              { num: '05', title: 'Attribution', desc: 'Rank candidate nodes by causal origin score and deliver actionable optimization recommendations.' },
            ].map((step, idx) => (
              <div
                key={step.num}
                className={`l-seq-step ${activeSeq === idx ? 'active' : ''}`}
                onClick={() => setActiveSeq(idx)}
                onMouseEnter={() => setActiveSeq(idx)}
              >
                <div className="l-seq-num">{step.num}</div>
                <div className="l-seq-title">{step.title}</div>
                <div className="l-seq-desc">{step.desc}</div>
                {idx < 4 && <div className="l-seq-arrow">→</div>}
              </div>
            ))}
          </div>
        </div>
      </RevealSection>

      {/* ════════════════════════════════════════════
          PRODUCT SHOWCASE
          ════════════════════════════════════════════ */}
      <RevealSection>
        <div className="l-container">
          <div style={{ textAlign: 'center', marginBottom: '48px' }}>
            <div className="l-section-eyebrow">The Product</div>
            <h2 className="l-section-headline">A real debugging workspace.</h2>
            <p className="l-section-body" style={{ margin: '0 auto' }}>
              Not a metrics dashboard. A full-stack trace debugger, node health inspector, failure propagation viewer, and root cause attribution engine.
            </p>
          </div>

          <div className="l-showcase">
            <div className="l-showcase-chrome">
              <div className="l-showcase-dot"></div>
              <div className="l-showcase-dot"></div>
              <div className="l-showcase-dot"></div>
              <div className="l-showcase-url">agenteval / trace / demo_trace_001 / root-cause</div>
            </div>
            <div className="l-showcase-body" style={{ padding: '0' }}>
              {/* Simulated product UI */}
              <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr 300px', minHeight: '420px' }}>
                {/* Sidebar */}
                <div style={{ background: '#0D1117', borderRight: '1px solid #2D333B', padding: '16px 0' }}>
                  <div style={{ padding: '12px 16px', fontSize: '10px', fontWeight: 700, color: '#484F58', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Observability</div>
                  {['Overview', 'Traces', 'Root Cause', 'Evaluations', 'Analytics', 'Benchmarks'].map((item, i) => (
                    <div key={item} style={{
                      padding: '8px 16px',
                      fontSize: '13px',
                      color: i === 2 ? '#E6EDF3' : '#8B949E',
                      background: i === 2 ? '#161B22' : 'transparent',
                      fontWeight: i === 2 ? 600 : 400,
                      borderLeft: i === 2 ? '2px solid #5865F2' : '2px solid transparent',
                      cursor: 'pointer'
                    }}>
                      {item}
                    </div>
                  ))}
                  <div style={{ padding: '12px 16px', marginTop: '16px', fontSize: '10px', fontWeight: 700, color: '#484F58', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Developer</div>
                  {['Integrations', 'API Keys', 'Settings'].map(item => (
                    <div key={item} style={{ padding: '8px 16px', fontSize: '13px', color: '#8B949E', cursor: 'pointer' }}>
                      {item}
                    </div>
                  ))}
                </div>

                {/* Main Content - Trace Graph */}
                <div style={{ background: '#0D1117', padding: '24px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
                    <div>
                      <div style={{ fontSize: '16px', fontWeight: 700, color: '#E6EDF3' }}>Root Cause Analysis</div>
                      <div style={{ fontSize: '12px', color: '#8B949E', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>demo_trace_001</div>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <span style={{ padding: '3px 8px', background: 'rgba(248, 81, 73, 0.1)', color: '#F85149', fontSize: '11px', fontWeight: 600, borderRadius: '4px', border: '1px solid rgba(248, 81, 73, 0.2)' }}>FAILURE</span>
                    </div>
                  </div>

                  {/* Mini trace nodes */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '24px', flexWrap: 'wrap' }}>
                    {[
                      { name: 'Planner', health: 95, color: '#3FB950' },
                      { name: 'Retriever', health: 88, color: '#3FB950' },
                      { name: 'Tool', health: 20, color: '#F85149' },
                      { name: 'Generator', health: 55, color: '#D29922' },
                      { name: 'Critic', health: 31, color: '#F85149' }
                    ].map((n, i) => (
                      <React.Fragment key={n.name}>
                        <div style={{
                          padding: '10px 14px',
                          background: '#161B22',
                          border: `1px solid ${n.color}30`,
                          borderRadius: '6px',
                          textAlign: 'center',
                          minWidth: '90px'
                        }}>
                          <div style={{ fontSize: '10px', fontWeight: 700, color: n.color, marginBottom: '2px' }}>{n.health}%</div>
                          <div style={{ fontSize: '12px', fontWeight: 600, color: '#E6EDF3' }}>{n.name}</div>
                        </div>
                        {i < 4 && <span style={{ color: '#484F58', fontSize: '14px' }}>→</span>}
                      </React.Fragment>
                    ))}
                  </div>

                  {/* Timeline */}
                  <div style={{ borderTop: '1px solid #2D333B', paddingTop: '16px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 600, color: '#484F58', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '12px' }}>Diagnostic Timeline</div>
                    {[
                      { time: '14:32:08.100', event: 'Planner dispatched execution DAG', status: '#3FB950' },
                      { time: '14:32:08.350', event: 'Tool SQL execution initiated', status: '#8B949E' },
                      { time: '14:32:16.800', event: 'Tool exceeded 8.0s timeout after 3 retries', status: '#F85149' },
                      { time: '14:32:17.100', event: 'Generator produced partial output from incomplete data', status: '#D29922' },
                      { time: '14:32:17.400', event: 'Critic quality check failed (0.31)', status: '#F85149' },
                    ].map((evt, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'baseline', gap: '12px', padding: '4px 0', fontSize: '12px' }}>
                        <span style={{ fontFamily: 'var(--font-mono)', color: '#484F58', flexShrink: 0, fontSize: '11px' }}>{evt.time}</span>
                        <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: evt.status, flexShrink: 0, marginTop: '4px' }}></span>
                        <span style={{ color: '#8B949E' }}>{evt.event}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Right Panel - Evidence */}
                <div style={{ background: '#161B22', borderLeft: '1px solid #2D333B', padding: '20px' }}>
                  <div style={{ fontSize: '11px', fontWeight: 700, color: '#484F58', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '16px' }}>Root Cause Attribution</div>

                  <div style={{ marginBottom: '20px', padding: '14px', background: 'rgba(248, 81, 73, 0.06)', border: '1px solid rgba(248, 81, 73, 0.15)', borderRadius: '6px' }}>
                    <div style={{ fontSize: '10px', fontWeight: 700, color: '#F85149', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '4px' }}>Likely Root Cause</div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: '#E6EDF3', fontFamily: 'var(--font-mono)' }}>tool_search_internal_db</div>
                    <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'space-between' }}>
                      <div>
                        <div style={{ fontSize: '10px', color: '#484F58' }}>ATTRIBUTION</div>
                        <div style={{ fontSize: '20px', fontWeight: 800, color: '#F85149', fontFamily: 'var(--font-mono)' }}>0.82</div>
                      </div>
                      <div>
                        <div style={{ fontSize: '10px', color: '#484F58' }}>HEALTH</div>
                        <div style={{ fontSize: '20px', fontWeight: 800, color: '#F85149', fontFamily: 'var(--font-mono)' }}>20%</div>
                      </div>
                    </div>
                  </div>

                  <div style={{ fontSize: '11px', fontWeight: 700, color: '#484F58', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '8px' }}>Supporting Evidence</div>
                  {['Latency anomaly: 8.45s (threshold: 2.0s)', 'Retry exhaustion: 3/3 attempts', 'Downstream quality degradation', 'Schema violation in response'].map((e, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'baseline', gap: '8px', padding: '6px 0', fontSize: '12px', color: '#8B949E', borderBottom: '1px solid #2D333B' }}>
                      <span style={{ color: '#484F58', fontSize: '10px' }}>→</span>
                      {e}
                    </div>
                  ))}

                  <div style={{ marginTop: '20px', fontSize: '11px', fontWeight: 700, color: '#484F58', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '8px' }}>Candidate Ranking</div>
                  {[
                    { name: 'Tool', score: '0.82' },
                    { name: 'Retriever', score: '0.54' },
                    { name: 'Generator', score: '0.38' },
                  ].map((c, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', fontSize: '12px', color: i === 0 ? '#F85149' : '#8B949E', fontWeight: i === 0 ? 600 : 400, borderBottom: '1px solid #2D333B' }}>
                      <span>{i + 1}. {c.name}</span>
                      <span style={{ fontFamily: 'var(--font-mono)' }}>{c.score}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </RevealSection>

      {/* ════════════════════════════════════════════
          ROOT CAUSE FEATURE
          ════════════════════════════════════════════ */}
      <RevealSection>
        <div className="l-container l-asym reverse">
          <div className="l-rc-graph">
            <div className="l-rc-chain">
              <div className="l-rc-node origin">
                <div className="l-rc-node-name">Tool</div>
                <div className="l-rc-node-detail">8.45s timeout</div>
              </div>
              <div className="l-rc-connector"></div>
              <div className="l-rc-node degraded">
                <div className="l-rc-node-name">Generator</div>
                <div className="l-rc-node-detail">Partial synthesis</div>
              </div>
              <div className="l-rc-connector"></div>
              <div className="l-rc-node failed">
                <div className="l-rc-node-name">Critic</div>
                <div className="l-rc-node-detail">Quality check failed</div>
              </div>
            </div>

            <div className="l-rc-result">
              <div className="l-rc-result-item">
                <div className="l-rc-result-label">Likely Root Cause</div>
                <div className="l-rc-result-value" style={{ color: 'var(--failure)' }}>Tool</div>
              </div>
              <div className="l-rc-result-item">
                <div className="l-rc-result-label">Attribution</div>
                <div className="l-rc-result-value mono">0.82</div>
              </div>
              <div className="l-rc-result-item">
                <div className="l-rc-result-label">Supporting Evidence</div>
                <ul className="l-rc-evidence-list">
                  <li>Latency anomaly</li>
                  <li>Retry increase</li>
                  <li>Downstream degradation</li>
                </ul>
              </div>
            </div>
          </div>

          <div>
            <div className="l-section-eyebrow">Root Cause Attribution</div>
            <h2 className="l-section-headline">
              Don't stop at<br />the failed node.
            </h2>
            <p className="l-section-body">
              AgentEval traces backward from visible failures through execution dependencies to identify the likely root cause with supporting evidence—so you fix what actually broke, not what merely reported the error.
            </p>
            <button className="l-btn l-btn-secondary" style={{ marginTop: '32px' }} onClick={() => navigate('/app/root-cause/demo_trace_001')}>
              View root cause analysis →
            </button>
          </div>
        </div>
      </RevealSection>

      {/* ════════════════════════════════════════════
          EVALUATION
          ════════════════════════════════════════════ */}
      <RevealSection>
        <div className="l-container l-asym">
          <div>
            <div className="l-section-eyebrow">Node Evaluation</div>
            <h2 className="l-section-headline">
              Measure agent health,<br />not just response time.
            </h2>
            <p className="l-section-body">
              Each node in an agent trace is evaluated across multiple dimensions. Health isn't a single number—it's a composite of instruction adherence, factual grounding, tool reliability, and structural validity.
            </p>
          </div>

          <div className="l-eval-grid">
            {[
              { label: 'Instruction following', value: 92, display: '0.92' },
              { label: 'Groundedness', value: 85, display: '0.85' },
              { label: 'Tool reliability', value: 20, display: '0.20' },
              { label: 'Retrieval quality', value: 78, display: '0.78' },
              { label: 'Latency', value: 65, display: '1.2s' },
              { label: 'Schema validity', value: 95, display: '0.95' },
            ].map(metric => (
              <div key={metric.label} className="l-eval-row">
                <div className="l-eval-label">{metric.label}</div>
                <div className="l-eval-bar-track">
                  <div className="l-eval-bar-fill" style={{
                    width: `${metric.value}%`,
                    background: metric.value < 40 ? 'var(--failure)' : metric.value < 70 ? 'var(--degraded)' : 'var(--text-primary)'
                  }}></div>
                </div>
                <div className="l-eval-value">{metric.display}</div>
              </div>
            ))}
          </div>
        </div>
      </RevealSection>

      {/* ════════════════════════════════════════════
          COST-AWARE EVALUATION
          ════════════════════════════════════════════ */}
      <RevealSection>
        <div className="l-container l-asym reverse">
          <div className="l-pipeline">
            {[
              { step: 'Trace volume', note: 'All incoming traces' },
              { step: 'Deterministic health signals', note: 'Fast, free' },
              { step: 'Suspicious nodes flagged', note: 'Filtered subset' },
              { step: 'Semantic evaluation (LLM)', note: 'Targeted, cached' },
              { step: 'Cached evidence store', note: 'Reusable' },
            ].map((item, idx) => (
              <div key={idx} className="l-pipe-step">
                <div className="l-pipe-num">{idx + 1}</div>
                <div className="l-pipe-text">{item.step}</div>
                <div className="l-pipe-note">{item.note}</div>
              </div>
            ))}
          </div>

          <div>
            <div className="l-section-eyebrow">Cost-Aware Design</div>
            <h2 className="l-section-headline">
              Use semantic<br />reasoning where<br />it matters.
            </h2>
            <p className="l-section-body">
              Deterministic health signals (latency, retries, schema checks) filter trace volume before expensive LLM evaluations run. Semantic reasoning is applied only to suspicious nodes, and results are cached to avoid redundant computation.
            </p>
          </div>
        </div>
      </RevealSection>

      {/* ════════════════════════════════════════════
          EXTERNAL VALIDATION
          ════════════════════════════════════════════ */}
      <RevealSection id="benchmarks">
        <div className="l-container">
          <div style={{ marginBottom: '48px' }}>
            <div className="l-section-eyebrow">Empirical Validation</div>
            <h2 className="l-section-headline">Validated beyond controlled traces.</h2>
          </div>

          <div className="l-bench-grid">
            {/* External Who&When */}
            <div className="l-bench-panel">
              <div className="l-bench-title">Who & When Benchmark</div>
              <div className="l-bench-big">40.8%</div>
              <div className="l-bench-sub">Agent-level accuracy across 184 independent test cases</div>
              <div className="l-bench-stats">
                <div>
                  <div className="l-bench-stat-num">14.7%</div>
                  <div className="l-bench-stat-label">Step accuracy</div>
                </div>
                <div>
                  <div className="l-bench-stat-num">0.353</div>
                  <div className="l-bench-stat-label">Macro-F1</div>
                </div>
                <div>
                  <div className="l-bench-stat-num">0.351</div>
                  <div className="l-bench-stat-label">Balanced accuracy</div>
                </div>
                <div>
                  <div className="l-bench-stat-num">184</div>
                  <div className="l-bench-stat-label">Test cases</div>
                </div>
              </div>
            </div>

            <div className="l-bench-divider"></div>

            {/* Internal Controlled */}
            <div className="l-bench-panel">
              <div className="l-bench-title">Internal Controlled Benchmark</div>
              <div className="l-bench-big">73.3%</div>
              <div className="l-bench-sub">Root-cause origin detection accuracy on synthetic multi-turn agent pipelines</div>
              <p style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6', marginBottom: '24px' }}>
                Evaluated across controlled scenarios with synthetic tool failures, retrieval degradation, and schema violations. Measures the system's ability to correctly identify the originating failure node.
              </p>
              <button className="l-btn l-btn-text" onClick={() => navigate('/how-it-works')}>View methodology →</button>
            </div>
          </div>
        </div>
      </RevealSection>

      {/* ════════════════════════════════════════════
          DEVELOPER INTEGRATION
          ════════════════════════════════════════════ */}
      <RevealSection id="integration">
        <div className="l-container l-asym">
          <div>
            <div className="l-section-eyebrow">Integration</div>
            <h2 className="l-section-headline">
              Connect an agent<br />in minutes.
            </h2>
            <p className="l-section-body" style={{ marginBottom: '32px' }}>
              Install the Python SDK, add the callback handler to your LangGraph pipeline, and start receiving trace data immediately.
            </p>

            {/* Install command */}
            <div className="l-code" style={{ marginBottom: '16px' }}>
              <div className="l-code-header">
                <span>terminal</span>
              </div>
              <pre>$ pip install agenteval</pre>
            </div>

            {/* SDK code */}
            <div className="l-code">
              <div className="l-code-header">
                <span>python</span>
              </div>
              <pre>{`from agenteval.sdk.tracer import AgentEvalTracer

# Initialize tracer with API key
tracer = AgentEvalTracer(
    api_url="https://your-instance.railway.app",
    api_key="ae_live_891f..."
)

# Connect to LangGraph pipeline
app.compile(
    checkpointer=memory,
    callbacks=[tracer]
)`}</pre>
            </div>
          </div>

          <div>
            <div style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '16px' }}>Hosted Architecture</div>
            <div className="l-arch">
              {[
                { label: 'LangGraph Agent', active: true },
                { label: 'AgentEval SDK (Callback)', active: true },
                { label: 'HTTPS Transport', active: false },
                { label: 'Railway (FastAPI Backend)', active: true },
                { label: 'Supabase PostgreSQL', active: true },
                { label: 'AgentEval Dashboard', active: true },
              ].map((step, idx) => (
                <React.Fragment key={idx}>
                  <div className={`l-arch-step ${step.active ? 'active' : ''}`}>
                    <div className="l-arch-icon"></div>
                    {step.label}
                  </div>
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>
      </RevealSection>

      {/* ════════════════════════════════════════════
          FINAL CTA
          ════════════════════════════════════════════ */}
      <RevealSection style={{ borderTop: '1px solid var(--border)' }}>
        <div className="l-container l-cta">
          <h2 className="l-cta-headline">
            Know what broke.<br />Know why.
          </h2>
          <div style={{ display: 'flex', gap: '16px', justifyContent: 'center' }}>
            <button className="l-btn l-btn-primary" onClick={() => navigate('/app/overview')}>Start debugging</button>
            <button className="l-btn l-btn-secondary" onClick={() => navigate('/docs')}>Documentation</button>
          </div>
        </div>
      </RevealSection>

      {/* ════════════════════════════════════════════
          FOOTER
          ════════════════════════════════════════════ */}
      <footer className="l-footer">
        <div className="l-container l-footer-inner">
          <div>AgentEval — AI-Agent Observability & Failure Attribution</div>
          <div className="l-footer-links">
            <a href="https://github.com/Hitesh564/AgentEval" target="_blank" rel="noreferrer">GitHub</a>
            <span onClick={() => navigate('/docs')} style={{ cursor: 'pointer' }}>Docs</span>
            <span onClick={() => navigate('/how-it-works')} style={{ cursor: 'pointer' }}>Methodology</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
