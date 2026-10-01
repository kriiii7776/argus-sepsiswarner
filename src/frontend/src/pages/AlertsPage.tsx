import React, { useState } from 'react';
import { AlertCard } from '../components/alerts/AlertCard';
import { MOCK_ALERTS } from '../mocks/mockData';
import { ShieldAlert } from 'lucide-react';


interface Props {
  onSelectPatient: (patient_id: string) => void;
}

export const AlertsPage: React.FC<Props> = ({ onSelectPatient }) => {
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');

  const filteredAlerts = MOCK_ALERTS.filter(a => {
    if (filterSeverity === 'ALL') return true;
    return a.severity === filterSeverity;
  });

  const urgentCount = MOCK_ALERTS.filter(a => a.severity === 'RED_URGENT').length;
  const reviewCount = MOCK_ALERTS.filter(a => a.severity === 'ORANGE_REVIEW').length;
  const watchCount = MOCK_ALERTS.filter(a => a.severity === 'YELLOW_WATCH').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Alert Level Summary Banner */}
      <div className="grid grid-cols-12">
        <div className="card col-span-4" style={{ borderLeft: '4px solid var(--color-critical)' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>RED URGENT ALERTS</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--color-critical)', marginTop: '0.2rem' }}>
            {urgentCount}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>High Sepsis Risk (&gt;80%) / Refractory Hypotension</span>

        </div>

        <div className="card col-span-4" style={{ borderLeft: '4px solid var(--color-review)' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>ORANGE REVIEW ALERTS</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--color-review)', marginTop: '0.2rem' }}>
            {reviewCount}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Rapid Risk Deterioration (+15%/hr)</span>
        </div>

        <div className="card col-span-4" style={{ borderLeft: '4px solid var(--color-watch)' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>YELLOW WATCH ALERTS</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--color-watch)', marginTop: '0.2rem' }}>
            {watchCount}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>SIRS / qSOFA Criteria Met</span>
        </div>
      </div>

      {/* Filter & List */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <ShieldAlert size={18} color="var(--color-critical)" /> Active ICU Clinical Alert Center
          </h3>

          <div style={{ display: 'flex', gap: '0.35rem' }}>
            {['ALL', 'RED_URGENT', 'ORANGE_REVIEW', 'YELLOW_WATCH'].map(sev => (
              <button
                key={sev}
                className={`btn ${filterSeverity === sev ? 'btn-primary' : 'btn-outline'}`}
                onClick={() => setFilterSeverity(sev)}
                style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
              >
                {sev.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
          {filteredAlerts.map(alert => (
            <AlertCard key={alert.alert_id} alert={alert} onSelectPatient={onSelectPatient} />
          ))}
        </div>
      </div>
    </div>
  );
};
