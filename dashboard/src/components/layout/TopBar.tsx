import { Search, ShieldCheck, ShieldAlert, Sparkles, Key } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import type { AppEnvironment } from '../../types';
import { navigate } from '../../router';

export const TopBar: React.FC = () => {
  const { 
    environment, 
    setEnvironment, 
    currentProject, 
    setCurrentProject,
    backendConnected,
    isDemoMode,
    setIsDemoMode,
    apiKey
  } = useApp();

  return (
    <header style={{
      height: 'var(--topbar-height)',
      background: 'var(--bg-sidebar)',
      borderBottom: '1px solid var(--border-color)',
      padding: '0 24px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      position: 'sticky',
      top: 0,
      zIndex: 90
    }}>
      {/* Left section: Project & Environment Selectors */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* Project Selector */}
        <select
          value={currentProject}
          onChange={(e) => setCurrentProject(e.target.value)}
          className="obs-input"
          style={{ padding: '4px 10px', fontWeight: 600, fontSize: '13px' }}
        >
          <option value="Default Project">Default Project</option>
          <option value="Customer Support Agent">Customer Support Agent</option>
          <option value="Research Pipeline">Research Pipeline</option>
        </select>

        {/* Environment Selector */}
        <select
          value={environment}
          onChange={(e) => setEnvironment(e.target.value as AppEnvironment)}
          className="obs-input"
          style={{ padding: '4px 10px', fontSize: '12px', color: 'var(--text-secondary)' }}
        >
          <option value="development">Dev (Development)</option>
          <option value="staging">Staging</option>
          <option value="production">Production</option>
        </select>
      </div>

      {/* Center: Search */}
      <div style={{ position: 'relative', width: '320px' }}>
        <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
        <input
          type="text"
          placeholder="Search trace ID, session, agent, root cause..."
          className="obs-input"
          style={{ width: '100%', paddingLeft: '32px', fontSize: '12px' }}
        />
      </div>

      {/* Right section: Demo Mode Toggle, Connection Status & Auth */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '12px' }}>
        {/* Demo Mode Button */}
        <button
          onClick={() => setIsDemoMode(!isDemoMode)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: '6px',
            border: isDemoMode ? '1px solid var(--accent-primary)' : '1px solid var(--border-color)',
            background: isDemoMode ? 'var(--accent-glow)' : 'transparent',
            color: isDemoMode ? 'var(--accent-primary)' : 'var(--text-secondary)',
            fontSize: '12px',
            fontWeight: 500,
            cursor: 'pointer'
          }}
        >
          <Sparkles size={14} />
          {isDemoMode ? 'Demo Mode On' : 'Demo Mode Off'}
        </button>

        {/* Backend Status Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
          {isDemoMode ? (
            <span className="badge badge-neutral">DEMO DATA</span>
          ) : backendConnected === true ? (
            <span className="badge badge-success" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              <ShieldCheck size={12} /> BACKEND ONLINE
            </span>
          ) : (
            <span className="badge badge-failure" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              <ShieldAlert size={12} /> DISCONNECTED
            </span>
          )}
        </div>

        {/* API Key Status */}
        <button
          onClick={() => navigate('/app/api-keys')}
          className="obs-btn obs-btn-secondary"
          style={{ padding: '4px 10px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <Key size={13} />
          {apiKey ? 'API Key Set' : 'Set API Key'}
        </button>
      </div>
    </header>
  );
};
