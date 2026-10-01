import React from 'react';
import { Search, Bell, Activity } from 'lucide-react';
import { Badge } from '../common/Badge';

interface HeaderProps {
  title: string;
  activePatientName?: string;
  activeBed?: string;
}

export const Header: React.FC<HeaderProps> = ({ title, activePatientName, activeBed }) => {
  return (
    <header className="app-header">
      <div>
        <h2 className="header-title">{title}</h2>
        {activePatientName && (
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            Selected: <strong>{activeBed}</strong> ({activePatientName})
          </span>
        )}
      </div>

      <div className="header-actions">
        <div style={{ position: 'relative', width: '240px' }}>
          <Search size={16} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            type="text"
            placeholder="Search patient, bed, MRN..."
            style={{
              width: '100%',
              padding: '0.4rem 0.75rem 0.4rem 2.2rem',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-color)',
              fontSize: '0.85rem',
              outline: 'none',
              backgroundColor: 'var(--bg-app)'
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Badge variant="blue">
            <Activity size={12} /> MODEL: LOGISTIC-REGRESSION-V1
          </Badge>
          <button className="btn btn-outline" style={{ padding: '0.4rem', borderRadius: '50%' }}>
            <Bell size={18} />
          </button>
        </div>
      </div>
    </header>
  );
};
