import React, { useState } from 'react';
import { Check, Copy } from 'lucide-react';

interface CodeBlockProps {
  code: string;
  language?: string;
}

export const CodeBlock: React.FC<CodeBlockProps> = ({ code, language = 'bash' }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{
      position: 'relative',
      background: 'var(--bg-dark)',
      border: '1px solid var(--border-color)',
      borderRadius: '6px',
      overflow: 'hidden',
      margin: '8px 0'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '6px 12px',
        background: 'var(--bg-elevated)',
        borderBottom: '1px solid var(--border-color)',
        fontSize: '11px',
        color: 'var(--text-muted)',
        fontFamily: 'var(--font-mono)'
      }}>
        <span>{language}</span>
        <button
          onClick={handleCopy}
          style={{
            background: 'none',
            border: 'none',
            color: copied ? 'var(--color-success)' : 'var(--text-secondary)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '11px'
          }}
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre style={{
        padding: '12px',
        margin: 0,
        fontFamily: 'var(--font-mono)',
        fontSize: '12px',
        color: 'var(--text-primary)',
        overflowX: 'auto',
        lineHeight: '1.5'
      }}>
        <code>{code}</code>
      </pre>
    </div>
  );
};
