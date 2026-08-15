import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { fetchSessions } from '../../services/api';
import type { SessionSummary } from '../../types';
import { TraceTable } from '../../components/trace/TraceTable';
import { EmptyState } from '../../components/common/EmptyState';
import { Search, RefreshCw } from 'lucide-react';

export const TracesPage: React.FC = () => {
  const { apiKey, isDemoMode } = useApp();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'passed' | 'failed'>('all');
  const [failureFilter, setFailureFilter] = useState<string>('all');

  const loadSessions = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSessions(apiKey, isDemoMode);
      setSessions(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, [apiKey, isDemoMode]);

  // Filtered Sessions
  const filteredSessions = sessions.filter(s => {
    if (statusFilter === 'passed' && !s.passed) return false;
    if (statusFilter === 'failed' && s.passed) return false;
    if (failureFilter !== 'all' && s.failure_tag !== failureFilter) return false;
    if (searchQuery && !s.session_id.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: 700 }}>Trace Explorer</h1>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Search, filter, and inspect multi-step agent trace executions.
          </p>
        </div>

        <button 
          onClick={loadSessions} 
          className="obs-btn obs-btn-secondary"
          style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <RefreshCw size={14} className={loading ? "spin" : ""} /> Refresh Traces
        </button>
      </div>

      {/* Filter Bar */}
      <div className="card-surface" style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
        {/* Search Input */}
        <div style={{ position: 'relative', flex: 1, minWidth: '240px' }}>
          <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            type="text"
            placeholder="Filter by Trace ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="obs-input"
            style={{ width: '100%', paddingLeft: '32px' }}
          />
        </div>

        {/* Status Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as any)}
            className="obs-input"
            style={{ fontSize: '12px' }}
          >
            <option value="all">All Traces</option>
            <option value="passed">Passed Only</option>
            <option value="failed">Failed Only</option>
          </select>
        </div>

        {/* Failure Tag Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Failure Tag:</span>
          <select
            value={failureFilter}
            onChange={(e) => setFailureFilter(e.target.value)}
            className="obs-input"
            style={{ fontSize: '12px' }}
          >
            <option value="all">All Failure Types</option>
            <option value="tool_timeout">Tool Timeout</option>
            <option value="retrieval_degradation">Retrieval Degradation</option>
            <option value="schema_failure">Schema Failure</option>
          </select>
        </div>
      </div>

      {/* Results Count */}
      <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
        Showing {filteredSessions.length} of {sessions.length} trace executions
      </div>

      {/* Trace Table or States */}
      {error ? (
        <div className="card-surface" style={{ padding: '24px', color: 'var(--color-failure)', textAlign: 'center' }}>
          {error}
        </div>
      ) : filteredSessions.length > 0 ? (
        <TraceTable sessions={filteredSessions} />
      ) : (
        <EmptyState 
          title="No traces found"
          description="No trace executions matched your active filters or search criteria."
          actionText="Clear Filters"
          onAction={() => {
            setSearchQuery('');
            setStatusFilter('all');
            setFailureFilter('all');
          }}
        />
      )}
    </div>
  );
};
