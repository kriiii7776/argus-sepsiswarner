import React from 'react';
import type { AlertItem } from '../../types';
import { AlertBadge } from '../common/Badge';

import { ShieldAlert, ArrowRight } from 'lucide-react';

interface Props {
  alert: AlertItem;
  onSelectPatient?: (patient_id: string) => void;
}

export const AlertCard: React.FC<Props> = ({ alert, onSelectPatient }) => {
  return (
    <div className="card" style={{ borderLeft: `4px solid ${alert.severity === 'RED_URGENT' ? 'var(--color-critical)' : alert.severity === 'ORANGE_REVIEW' ? 'var(--color-review)' : 'var(--color-watch)'}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <ShieldAlert size={18} style={{ color: alert.severity === 'RED_URGENT' ? 'var(--color-critical)' : 'var(--color-review)' }} />
          <strong style={{ fontSize: '0.95rem' }}>{alert.bed} — {alert.patient_name}</strong>
        </div>
        <AlertBadge severity={alert.severity} />
      </div>

      <p style={{ fontSize: '0.875rem', color: 'var(--text-primary)', margin: '0.6rem 0 0.4rem 0', fontWeight: 500 }}>
        {alert.message}
      </p>

      <div style={{ backgroundColor: 'var(--bg-subtle)', padding: '0.6rem 0.75rem', borderRadius: 'var(--radius-sm)', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
        <strong>Recommended Action:</strong> {alert.recommended_action}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.75rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
        <span>Triggered: {new Date(alert.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
        {onSelectPatient && (
          <button 
            className="btn btn-outline" 
            onClick={() => onSelectPatient(alert.patient_id)}
            style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
          >
            View Patient Focus <ArrowRight size={12} />
          </button>
        )}
      </div>
    </div>
  );
};
