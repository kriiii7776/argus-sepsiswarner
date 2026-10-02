import React from 'react';
import type { Patient, VitalEvent } from '../../types';
import { RiskBadge, AlertBadge, SignalQualityBadge } from '../common/Badge';


interface Props {
  patients: Patient[];
  vitalsMap: Record<string, VitalEvent>;
  activePatientId: string;
  onSelectPatient: (id: string) => void;
}

export const PatientRosterTable: React.FC<Props> = ({
  patients,
  vitalsMap,
  activePatientId,
  onSelectPatient
}) => {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem', textAlign: 'left' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)', fontSize: '0.75rem', textTransform: 'uppercase' }}>
            <th style={{ padding: '0.75rem 1rem' }}>Bed / Patient</th>
            <th style={{ padding: '0.75rem 1rem' }}>Age / Sex</th>
            <th style={{ padding: '0.75rem 1rem' }}>Sepsis Risk</th>
            <th style={{ padding: '0.75rem 1rem' }}>Vitals Summary</th>
            <th style={{ padding: '0.75rem 1rem' }}>Scores (SIRS/qSOFA/NEWS)</th>
            <th style={{ padding: '0.75rem 1rem' }}>Alert State</th>
            <th style={{ padding: '0.75rem 1rem' }}>Signal</th>
            <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>Action</th>
          </tr>
        </thead>
        <tbody>
          {patients.map((p) => {
            const v = vitalsMap[p.patient_id];
            const isSelected = p.patient_id === activePatientId;

            return (
              <tr
                key={p.patient_id}
                onClick={() => onSelectPatient(p.patient_id)}
                style={{
                  borderBottom: '1px solid var(--border-color)',
                  backgroundColor: isSelected ? 'var(--bg-info-bg)' : 'transparent',
                  cursor: 'pointer',
                  transition: 'background-color 0.15s ease'
                }}
              >
                <td style={{ padding: '0.85rem 1rem' }}>
                  <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{p.bed} — {p.name}</div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{p.patient_id}</span>
                </td>

                <td style={{ padding: '0.85rem 1rem', color: 'var(--text-secondary)' }}>
                  {p.age} yrs • {p.sex_at_birth || 'Unspecified'}
                </td>

                <td style={{ padding: '0.85rem 1rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontWeight: 800, fontSize: '1rem', color: p.current_risk_score >= 80 ? 'var(--color-critical)' : p.current_risk_score >= 50 ? 'var(--color-review)' : 'var(--color-stable)' }}>
                      {p.current_risk_score.toFixed(1)}%
                    </span>
                    <RiskBadge level={p.risk_level} />
                  </div>
                </td>

                <td style={{ padding: '0.85rem 1rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  {v ? (
                    <div>
                      HR <strong>{v.heart_rate}</strong> • MAP <strong>{v.map}</strong> • SpO2 <strong>{v.spo2}%</strong>
                    </div>
                  ) : (
                    <span>Telemetry Pending</span>
                  )}
                </td>

                <td style={{ padding: '0.85rem 1rem', fontSize: '0.8rem' }}>
                  <span style={{ fontFamily: 'var(--font-mono)' }}>SIRS:{p.sirs_score} | qSOFA:{p.qsofa_score} | NEWS:{p.news_score}</span>
                </td>

                <td style={{ padding: '0.85rem 1rem' }}>
                  <AlertBadge severity={p.alert_severity} />
                </td>

                <td style={{ padding: '0.85rem 1rem' }}>
                  <SignalQualityBadge quality={v?.signal_quality} />
                </td>

                <td style={{ padding: '0.85rem 1rem', textAlign: 'right' }}>
                  <button className="btn btn-outline" style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem' }}>
                    View Focus
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
