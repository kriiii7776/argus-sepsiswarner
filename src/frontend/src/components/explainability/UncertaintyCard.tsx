import React from 'react';
import { AlertTriangle } from 'lucide-react';
import type { UncertaintySummary } from '../../types';


interface Props {
  summary: UncertaintySummary;
}

export const UncertaintyCard: React.FC<Props> = ({ summary }) => {
  return (
    <div className="card" style={{ borderLeft: '4px solid var(--text-muted)' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
        <AlertTriangle size={18} style={{ color: 'var(--text-muted)', marginTop: '2px', flexShrink: 0 }} />
        <div>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            Predictive Uncertainty Status: <span style={{ fontFamily: 'var(--font-mono)' }}>{summary.method}</span>
          </h4>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            {summary.reason}
          </p>
          <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Uncertainty Available: <strong style={{ color: summary.uncertainty_available ? 'var(--color-stable)' : 'var(--text-secondary)' }}>{summary.uncertainty_available ? 'True' : 'False'}</strong>
          </div>
        </div>
      </div>
    </div>
  );
};
