import React from 'react';
import { 
  Activity, 
  Layers, 
  BarChart2, 
  AlertOctagon, 
  CheckCircle2, 
  Key, 
  FolderGit2, 
  BookOpen, 
  Zap, 
  Compass, 
  Globe,
  Sliders
} from 'lucide-react';
import { useLocation } from '../../router';

export const Sidebar: React.FC = () => {
  const { route, navigate } = useLocation();

  const navItems = [
    { label: 'Overview', path: '/app/overview', icon: <Activity size={18} /> },
    { label: 'Traces', path: '/app/traces', icon: <Layers size={18} /> },
    { label: 'Root Cause', path: '/app/root-cause/demo_trace_001', icon: <AlertOctagon size={18} /> },
    { label: 'Evaluations', path: '/app/evaluations', icon: <CheckCircle2 size={18} /> },
    { label: 'Analytics', path: '/app/analytics', icon: <BarChart2 size={18} /> },
    { label: 'Benchmarks', path: '/app/benchmarks', icon: <Compass size={18} /> },
  ];

  const devItems = [
    { label: 'Integrations', path: '/app/integrations', icon: <Zap size={18} /> },
    { label: 'API Keys', path: '/app/api-keys', icon: <Key size={18} /> },
    { label: 'Projects', path: '/app/projects', icon: <FolderGit2 size={18} /> },
    { label: 'Settings', path: '/app/settings', icon: <Sliders size={18} /> },
    { label: 'Docs', path: '/docs', icon: <BookOpen size={18} /> },
  ];

  const isActive = (itemPath: string) => {
    if (itemPath === '/app/overview' && (route === '/app' || route === '/app/overview')) return true;
    if (itemPath.startsWith('/app/root-cause') && route.startsWith('/app/root-cause')) return true;
    if (itemPath.startsWith('/app/traces') && route.startsWith('/app/traces')) return true;
    return route === itemPath;
  };

  return (
    <aside style={{
      width: 'var(--sidebar-width)',
      height: '100vh',
      background: 'var(--bg-sidebar)',
      borderRight: '1px solid var(--border-color)',
      display: 'flex',
      flexDirection: 'column',
      position: 'fixed',
      left: 0,
      top: 0,
      zIndex: 100,
      userSelect: 'none'
    }}>
      {/* Brand Header */}
      <div style={{
        height: 'var(--topbar-height)',
        padding: '0 20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid var(--border-color)'
      }}>
        <div 
          onClick={() => navigate('/')} 
          style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}
        >
          <div style={{
            width: '28px',
            height: '28px',
            borderRadius: '6px',
            background: 'linear-gradient(135deg, #6C7CFF 0%, #40D9FF 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#FFFFFF',
            fontWeight: 800,
            fontSize: '14px'
          }}>
            AE
          </div>
          <span style={{ fontWeight: 700, fontSize: '15px', color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
            AgentEval
          </span>
        </div>
      </div>

      {/* Main Navigation */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', padding: '0 8px 8px 8px' }}>
            Observability
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {navItems.map(item => {
              const active = isActive(item.path);
              return (
                <button
                  key={item.path}
                  onClick={() => navigate(item.path)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: '6px',
                    border: 'none',
                    background: active ? 'var(--bg-elevated)' : 'transparent',
                    color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                    fontWeight: active ? 600 : 500,
                    fontSize: '13px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    textAlign: 'left'
                  }}
                >
                  <span style={{ color: active ? 'var(--accent-primary)' : 'var(--text-muted)' }}>
                    {item.icon}
                  </span>
                  {item.label}
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', padding: '0 8px 8px 8px' }}>
            Developer & Setup
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {devItems.map(item => {
              const active = isActive(item.path);
              return (
                <button
                  key={item.path}
                  onClick={() => navigate(item.path)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: '6px',
                    border: 'none',
                    background: active ? 'var(--bg-elevated)' : 'transparent',
                    color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                    fontWeight: active ? 600 : 500,
                    fontSize: '13px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    textAlign: 'left'
                  }}
                >
                  <span style={{ color: active ? 'var(--accent-primary)' : 'var(--text-muted)' }}>
                    {item.icon}
                  </span>
                  {item.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Sidebar Footer */}
      <div style={{
        padding: '12px',
        borderTop: '1px solid var(--border-color)',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        background: 'var(--bg-dark)'
      }}>
        <button
          onClick={() => navigate('/')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            width: '100%',
            padding: '6px 10px',
            borderRadius: '6px',
            border: '1px solid var(--border-color)',
            background: 'transparent',
            color: 'var(--text-secondary)',
            fontSize: '12px',
            cursor: 'pointer'
          }}
        >
          <Globe size={14} />
          Public Product Page
        </button>
      </div>
    </aside>
  );
};
