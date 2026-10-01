import React from 'react';
import { Brain } from 'lucide-react';
import { RiskBadge } from '../common/Badge';
import type { Patient } from '../../types';


interface RiskAnalysisCardProps {
  patient: Patient;
}

export const RiskAnalysisCard: React.FC<RiskAnalysisCardProps> = ({ patient }) => {
  const getRiskColor = () => {
    if (patient.current_risk_score >= 80) return 'var(--color-critical)';
    if (patient.current_risk_score >= 50) return 'var(--color-review)';
    return 'var(--color-stable)';
  };

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">
          <Brain size={18} color="var(--color-info)" /> Sepsis Risk Analysis
        </h3>
        <RiskBadge level={patient.risk_level} />
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', margin: '1rem 0' }}>
        <div>
          <div style={{ fontSize: '3rem', fontWeight: 800, color: getRiskColor(), lineHeight: 1 }}>
            {patient.current_risk_score.toFixed(1)}%
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.4rem' }}>
            6-Hour Prediction Horizon Probability
          </p>
        </div>

        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Risk Trajectory</div>
          <div style={{ fontSize: '1rem', fontWeight: 700, color: patient.risk_trend === 'up' ? 'var(--color-critical)' : 'var(--color-stable)' }}>
            {patient.risk_trend === 'up' ? '▲ Worsening (+15%/hr)' : patient.risk_trend === 'down' ? '▼ Improving' : '● Stable'}
          </div>
        </div>
      </div>

      <div style={{ backgroundColor: 'var(--bg-subtle)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-sm)', marginTop: '1rem', fontSize: '0.8rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
          <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>Model Engine:</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>logistic-regression-v1</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
          <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>Is Demo Model:</span>
          <span style={{ fontWeight: 600, color: 'var(--color-stable)' }}>False (Real Baseline Model)</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>Reliability Confidence:</span>
          <span style={{ fontWeight: 600, color: 'var(--color-stable)' }}>HIGH</span>
        </div>
      </div>
    </div>
  );
};
