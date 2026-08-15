import { KpiCard } from '../../components/common/KpiCard';
import { StatusBadge } from '../../components/common/StatusBadge';
import { DollarSign } from 'lucide-react';

export const EvaluationsPage: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div>
        <h1 style={{ fontSize: '20px', fontWeight: 700 }}>Evaluation & Quality Dashboard</h1>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
          Trace evaluation scores across instruction following, retrieval quality, tool-calling accuracy, and schema validity.
        </p>
      </div>

      {/* Evaluation Metrics Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
        <KpiCard title="Overall Eval Score" value="88.4%" trend="+4.2%" trendDirection="up" isGoodTrend={true} subtext="Across all evaluated nodes" />
        <KpiCard title="Instruction Following" value="92.1%" trend="+1.5%" trendDirection="up" isGoodTrend={true} subtext="Prompt compliance ratio" />
        <KpiCard title="Retrieval Quality" value="84.5%" trend="-2.1%" trendDirection="down" isGoodTrend={false} subtext="Vector similarity & groundedness" />
        <KpiCard title="Tool Accuracy" value="86.8%" trend="+3.8%" trendDirection="up" isGoodTrend={true} subtext="Schema & execution validity" />
      </div>

      {/* Cost & Token Usage Observability */}
      <div className="card-surface" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <DollarSign size={18} color="var(--color-success)" />
            <h3 style={{ fontSize: '15px' }}>Evaluation Cost & Token Telemetry</h3>
          </div>
          <span className="badge badge-success">Cache Hit Rate: 68.4%</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
          <div className="card-surface" style={{ background: 'var(--bg-dark)' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Total LLM Calls</div>
            <div className="mono" style={{ fontSize: '20px', fontWeight: 700, marginTop: '4px' }}>1,482</div>
          </div>
          <div className="card-surface" style={{ background: 'var(--bg-dark)' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Input Tokens</div>
            <div className="mono" style={{ fontSize: '20px', fontWeight: 700, marginTop: '4px' }}>482,910</div>
          </div>
          <div className="card-surface" style={{ background: 'var(--bg-dark)' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Output Tokens</div>
            <div className="mono" style={{ fontSize: '20px', fontWeight: 700, marginTop: '4px' }}>112,400</div>
          </div>
          <div className="card-surface" style={{ background: 'var(--bg-dark)' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Est. Eval Cost</div>
            <div className="mono" style={{ fontSize: '20px', fontWeight: 700, marginTop: '4px', color: 'var(--color-success)' }}>$0.0142</div>
          </div>
        </div>
      </div>

      {/* Metric Breakdown Table */}
      <div className="table-container">
        <table className="obs-table">
          <thead>
            <tr>
              <th>Evaluation Dimension</th>
              <th>Current Score</th>
              <th>Status</th>
              <th>Evaluated Nodes</th>
              <th>Target Threshold</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Instruction Following</td>
              <td className="mono" style={{ fontWeight: 600 }}>92.1%</td>
              <td><StatusBadge status="PASSED" type="passed" /></td>
              <td>Planner, Generator</td>
              <td>&gt; 85%</td>
            </tr>
            <tr>
              <td>Retrieval Quality</td>
              <td className="mono" style={{ fontWeight: 600 }}>84.5%</td>
              <td><StatusBadge status="PASSED" type="passed" /></td>
              <td>Retriever</td>
              <td>&gt; 80%</td>
            </tr>
            <tr>
              <td>Tool Calling Accuracy</td>
              <td className="mono" style={{ fontWeight: 600 }}>86.8%</td>
              <td><StatusBadge status="PASSED" type="passed" /></td>
              <td>Tool Executor</td>
              <td>&gt; 85%</td>
            </tr>
            <tr>
              <td>JSON / Schema Validity</td>
              <td className="mono" style={{ fontWeight: 600 }}>99.2%</td>
              <td><StatusBadge status="PASSED" type="passed" /></td>
              <td>All Agent Nodes</td>
              <td>&gt; 95%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};
