import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { createAdminApiKey } from '../../services/api';
import { Modal } from '../../components/common/Modal';
import { CodeBlock } from '../../components/common/CodeBlock';
import { AlertTriangle } from 'lucide-react';

export const ApiKeysPage: React.FC = () => {
  const { apiKey, setApiKey } = useApp();
  const [bootstrapKey, setBootstrapKey] = useState<string>('');
  const [userId, setUserId] = useState<string>('default_user');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  // Generated key modal
  const [newApiKey, setNewApiKey] = useState<string | null>(null);
  const [showModal, setShowModal] = useState<boolean>(false);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bootstrapKey.trim()) {
      setError("Admin bootstrap key is required to generate new integration keys");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await createAdminApiKey(bootstrapKey.trim(), userId.trim());
      setNewApiKey(res.api_key);
      setApiKey(res.api_key); // Save locally
      setShowModal(true);
    } catch (err: any) {
      setError(err.message || "Failed to generate API Key");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '800px' }}>
      {/* Header */}
      <div>
        <h1 style={{ fontSize: '20px', fontWeight: 700 }}>API Key & Integration Setup</h1>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
          Manage authenticated API keys for hosted trace ingestion and telemetry callbacks.
        </p>
      </div>

      {/* Active API Key Card */}
      <div className="card-surface">
        <h3 style={{ fontSize: '14px', marginBottom: '8px' }}>Active Local API Key</h3>
        {apiKey ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--bg-dark)', padding: '12px 16px', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
            <span className="mono" style={{ fontSize: '13px', color: 'var(--color-success)' }}>
              {apiKey.substring(0, 8)}************************
            </span>
            <button 
              onClick={() => setApiKey(null)}
              className="obs-btn obs-btn-secondary"
              style={{ fontSize: '11px', padding: '4px 10px' }}
            >
              Clear Saved Key
            </button>
          </div>
        ) : (
          <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
            No active API key set in dashboard local storage. Enter your admin key below to generate one.
          </div>
        )}
      </div>

      {/* API Key Generation Form */}
      <div className="card-surface">
        <h3 style={{ fontSize: '14px', marginBottom: '4px' }}>Generate New Integration Key</h3>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
          Uses backend bootstrap admin endpoint <code>POST /api/v1/admin/api-keys</code> with <code>X-Admin-Key</code> authorization.
        </p>

        {error && (
          <div style={{ background: 'var(--color-failure-bg)', border: '1px solid rgba(255, 102, 122, 0.3)', color: 'var(--color-failure)', padding: '10px 14px', borderRadius: '6px', fontSize: '12px', marginBottom: '16px' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleGenerate} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
              User / Tenant ID
            </label>
            <input
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              className="obs-input"
              style={{ width: '100%' }}
              required
            />
          </div>

          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
              Admin Bootstrap Token (<code>AGENTEVAL_ADMIN_BOOTSTRAP_KEY</code>)
            </label>
            <input
              type="password"
              placeholder="Enter AGENTEVAL_ADMIN_BOOTSTRAP_KEY..."
              value={bootstrapKey}
              onChange={(e) => setBootstrapKey(e.target.value)}
              className="obs-input"
              style={{ width: '100%' }}
              required
            />
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="obs-btn obs-btn-primary"
            style={{ width: 'fit-content' }}
          >
            {loading ? 'Generating Key...' : 'Generate API Key'}
          </button>
        </form>
      </div>

      {/* Security Guidance */}
      <div className="card-surface" style={{ background: 'rgba(245, 185, 76, 0.08)', borderColor: 'rgba(245, 185, 76, 0.3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-warning)', fontWeight: 600, fontSize: '13px', marginBottom: '4px' }}>
          <AlertTriangle size={16} /> Security Best Practices
        </div>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
          Never commit API keys or admin bootstrap tokens to public source control. Store keys securely using environment variables (`AGENTEVAL_API_KEY`).
        </p>
      </div>

      {/* One-Time Display Modal */}
      <Modal isOpen={showModal} onClose={() => setShowModal(false)} title="API Key Successfully Created">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ background: 'var(--color-warning-bg)', border: '1px solid rgba(245, 185, 76, 0.3)', padding: '12px', borderRadius: '6px', fontSize: '12px', color: 'var(--color-warning)' }}>
            <strong>Copy this key now. It will only be shown once!</strong>
          </div>

          <div>
            <label style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Generated Plaintext Key</label>
            <CodeBlock code={newApiKey || ''} language="text" />
          </div>

          <button 
            onClick={() => setShowModal(false)}
            className="obs-btn obs-btn-primary"
            style={{ width: '100%' }}
          >
            Done & Save Key to Dashboard
          </button>
        </div>
      </Modal>
    </div>
  );
};
