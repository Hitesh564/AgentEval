import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { fetchBenchmarkCompare } from '../../services/api';
import type { BenchmarkReport } from '../../types';
import { StatusBadge } from '../../components/common/StatusBadge';
import { RefreshCw } from 'lucide-react';

export const BenchmarksPage: React.FC = () => {
  const { apiKey, isDemoMode } = useApp();
  const [report, setReport] = useState<BenchmarkReport | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadComparison = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchBenchmarkCompare(apiKey, isDemoMode);
      setReport(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load benchmark comparison');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadComparison();
  }, [apiKey, isDemoMode]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: 700 }}>Benchmark & Empirical Validation</h1>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Empirical evaluations across internal controlled benchmarks and external Who&When validation sets.
          </p>
        </div>

        <button onClick={loadComparison} className="obs-btn obs-btn-secondary" style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <RefreshCw size={14} className={loading ? "spin" : ""} /> Run Comparison
        </button>
      </div>

      {/* Top 2 Cards: Internal vs External Who&When */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Card 1: Internal Controlled Benchmark */}
        <div className="card-elevated">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <h3 style={{ fontSize: '16px' }}>Controlled Internal Benchmark</h3>
            <span className="badge badge-success">73.3% Accuracy</span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '16px', lineHeight: '1.5' }}>
            Evaluated on synthetic agent pipelines featuring introduced tool timeouts, vector similarity degradation, and prompt compliance failures.
          </p>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px' }}>
            <span className="mono" style={{ fontSize: '32px', fontWeight: 800, color: 'var(--color-success)' }}>
              73.3%
            </span>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Root Cause Origin Accuracy</span>
          </div>
        </div>

        {/* Card 2: External Who&When Benchmark */}
        <div className="card-elevated">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <h3 style={{ fontSize: '16px' }}>External Who&When Benchmark</h3>
            <span className="badge badge-neutral">184 Test Cases</span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '16px', lineHeight: '1.5' }}>
            Independent external dataset measuring agent-level and step-level root cause accuracy across multi-agent trajectories.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
            <div>
              <div className="mono" style={{ fontSize: '18px', fontWeight: 700 }}>40.8%</div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Agent Accuracy</div>
            </div>
            <div>
              <div className="mono" style={{ fontSize: '18px', fontWeight: 700 }}>14.7%</div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Step Accuracy</div>
            </div>
            <div>
              <div className="mono" style={{ fontSize: '18px', fontWeight: 700 }}>0.353</div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Macro F1</div>
            </div>
            <div>
              <div className="mono" style={{ fontSize: '18px', fontWeight: 700 }}>0.351</div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Balanced Acc</div>
            </div>
          </div>
        </div>
      </div>

      {/* Live Version Comparison Section */}
      <div className="card-surface" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
          <div>
            <h3 style={{ fontSize: '15px' }}>Live Version Comparison Report</h3>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Comparing {report?.version_a || 'v1.0.0-baseline'} vs {report?.version_b || 'v1.0.1-fixed-retrieval'}
            </span>
          </div>
          {report?.overall_verdict && (
            <span className="badge badge-success" style={{ fontSize: '12px', padding: '4px 10px' }}>
              {report.overall_verdict}
            </span>
          )}
        </div>

        {error ? (
          <div style={{ color: 'var(--color-failure)', textAlign: 'center', padding: '16px' }}>
            {error}
          </div>
        ) : report ? (
          <div className="table-container">
            <table className="obs-table">
              <thead>
                <tr>
                  <th>Evaluation Metric</th>
                  <th>Baseline (Version A)</th>
                  <th>Fixed (Version B)</th>
                  <th>Delta Difference</th>
                  <th>Verdict Status</th>
                </tr>
              </thead>
              <tbody>
                {report.metrics.map(m => (
                  <tr key={m.metric}>
                    <td style={{ fontWeight: 600 }}>{m.metric}</td>
                    <td className="mono">{m.val_a}</td>
                    <td className="mono">{m.val_b}</td>
                    <td className="mono" style={{ color: m.status === 'IMPROVED' ? 'var(--color-success)' : m.status === 'DEGRADED' ? 'var(--color-failure)' : 'var(--text-muted)' }}>
                      {m.delta > 0 ? `+${m.delta}` : m.delta}
                    </td>
                    <td>
                      <StatusBadge status={m.status} type={m.status === 'IMPROVED' ? 'passed' : m.status === 'DEGRADED' ? 'failed' : 'warning'} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '24px' }}>
            Click "Run Comparison" to evaluate stored session baseline calibration sets.
          </div>
        )}
      </div>
    </div>
  );
};
