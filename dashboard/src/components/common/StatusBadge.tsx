import React from 'react';

interface StatusBadgeProps {
  status?: string | null;
  type?: 'passed' | 'failed' | 'warning' | 'health' | 'failure_tag';
  healthScore?: number | null;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, type = 'passed', healthScore }) => {
  if (type === 'health' && healthScore !== undefined && healthScore !== null) {
    let healthClass = 'badge-success';
    if (healthScore < 0.5) healthClass = 'badge-failure';
    else if (healthScore < 0.75) healthClass = 'badge-warning';
    
    return (
      <span className={`badge ${healthClass}`}>
        {(healthScore * 100).toFixed(0)}% Health
      </span>
    );
  }

  if (type === 'failure_tag' && status) {
    const formatted = status.replace(/_/g, ' ').toUpperCase();
    return (
      <span className="badge badge-failure">
        {formatted}
      </span>
    );
  }

  if (status === 'PASSED' || status === 'true' || status === 'complete' || status === 'IMPROVED' || type === 'passed') {
    return (
      <span className="badge badge-success">
        {status || 'PASSED'}
      </span>
    );
  }

  if (status === 'DEGRADED' || type === 'warning') {
    return (
      <span className="badge badge-warning">
        {status || 'DEGRADED'}
      </span>
    );
  }

  return (
    <span className="badge badge-failure">
      {status || 'FAILED'}
    </span>
  );
};
