import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface KpiCardProps {
  title: string;
  value: string | number;
  trend?: string;
  trendDirection?: 'up' | 'down' | 'neutral';
  isGoodTrend?: boolean;
  subtext?: string;
  icon?: React.ReactNode;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  trend,
  trendDirection = 'neutral',
  isGoodTrend = true,
  subtext,
  icon
}) => {
  let trendColor = 'var(--text-muted)';
  if (trendDirection !== 'neutral') {
    trendColor = isGoodTrend ? 'var(--color-success)' : 'var(--color-failure)';
  }

  return (
    <div className="card-surface" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ color: 'var(--text-secondary)', fontSize: '12px', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          {title}
        </span>
        {icon && <span style={{ color: 'var(--accent-primary)', opacity: 0.8 }}>{icon}</span>}
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
        <span style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
          {value}
        </span>
        {trend && (
          <span style={{ fontSize: '12px', fontWeight: 600, color: trendColor, display: 'inline-flex', alignItems: 'center', gap: '2px' }}>
            {trendDirection === 'up' && <TrendingUp size={14} />}
            {trendDirection === 'down' && <TrendingDown size={14} />}
            {trendDirection === 'neutral' && <Minus size={14} />}
            {trend}
          </span>
        )}
      </div>

      {subtext && (
        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
          {subtext}
        </span>
      )}
    </div>
  );
};
