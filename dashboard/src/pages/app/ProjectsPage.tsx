import React from 'react';
import { useApp } from '../../context/AppContext';
import { FolderGit2, Info } from 'lucide-react';

export const ProjectsPage: React.FC = () => {
  const { currentProject, backendInfo } = useApp();

  const projectsList = [
    { name: "Default Project", env: "Development", status: "Active", traces: "5 Traces", db: backendInfo?.database_backend || "SQLite" },
    { name: "Customer Support Agent", env: "Staging", status: "Active", traces: "12 Traces", db: "PostgreSQL" },
    { name: "Research Pipeline", env: "Production", status: "Active", traces: "48 Traces", db: "PostgreSQL" }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '900px' }}>
      <div>
        <h1 style={{ fontSize: '20px', fontWeight: 700 }}>Project & Environment Workspace</h1>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
          Environment configuration status and active workspace project profiles.
        </p>
      </div>

      <div className="card-surface" style={{ background: 'rgba(108, 124, 255, 0.08)', borderColor: 'var(--accent-primary)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-primary)', fontWeight: 600, fontSize: '13px', marginBottom: '4px' }}>
          <Info size={16} /> Server Workspace Note
        </div>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
          Project workspaces are isolated by API keys and environment variables. Full CRUD project management APIs are managed via server configuration.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
        {projectsList.map(p => (
          <div key={p.name} className="card-surface" style={{ border: p.name === currentProject ? '1px solid var(--accent-primary)' : '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <FolderGit2 size={18} color="var(--accent-primary)" />
              <span className="badge badge-success">{p.status}</span>
            </div>
            <h3 style={{ fontSize: '15px', marginBottom: '4px' }}>{p.name}</h3>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Environment: <strong style={{ color: 'var(--text-secondary)' }}>{p.env}</strong>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
              Database: <strong style={{ color: 'var(--text-secondary)' }}>{p.db}</strong>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
