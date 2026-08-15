import React from 'react';
import { Layers } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  actionText,
  onAction,
  icon
}) => {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '48px 24px',
      textAlign: 'center',
      background: 'var(--bg-surface)',
      border: '1px border-dashed var(--border-color)',
      borderRadius: '8px',
      gap: '12px'
    }}>
      <div style={{
        width: '48px',
        height: '48px',
        borderRadius: '50%',
        background: 'var(--bg-elevated)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--text-muted)'
      }}>
        {icon || <Layers size={24} />}
      </div>
      <h3 style={{ fontSize: '16px', color: 'var(--text-primary)' }}>{title}</h3>
      <p style={{ fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '400px' }}>{description}</p>
      {actionText && onAction && (
        <button
          onClick={onAction}
          className="obs-btn obs-btn-primary"
          style={{ marginTop: '8px' }}
        >
          {actionText}
        </button>
      )}
    </div>
  );
};
