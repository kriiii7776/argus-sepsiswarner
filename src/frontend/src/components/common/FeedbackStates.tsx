import React from 'react';
import { AlertCircle, Inbox, Loader2 } from 'lucide-react';

export const EmptyState: React.FC<{ message?: string; subtext?: string }> = ({ 
  message = 'No data available', 
  subtext = 'There are no active records for this selection.' 
}) => (
  <div style={{ padding: '3rem 1.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
    <Inbox size={40} style={{ marginBottom: '0.75rem', opacity: 0.5 }} />
    <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-secondary)' }}>{message}</h3>
    <p style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>{subtext}</p>
  </div>
);

export const LoadingState: React.FC<{ message?: string }> = ({ message = 'Loading patient monitoring telemetry...' }) => (
  <div style={{ padding: '3rem 1.5rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
    <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', marginBottom: '0.75rem', color: 'var(--color-info)' }} />
    <p style={{ fontSize: '0.9rem', fontWeight: 500 }}>{message}</p>
  </div>
);

export const ErrorState: React.FC<{ title?: string; message?: string }> = ({ 
  title = 'Unable to Load Data', 
  message = 'Failed to fetch telemetry payload from backend service.' 
}) => (
  <div className="card" style={{ borderLeft: '4px solid var(--color-critical)', backgroundColor: 'var(--color-critical-bg)' }}>
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
      <AlertCircle size={20} color="var(--color-critical)" style={{ flexShrink: 0, marginTop: '2px' }} />
      <div>
        <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--color-critical)' }}>{title}</h4>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>{message}</p>
      </div>
    </div>
  </div>
);
