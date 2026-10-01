import React from 'react';
import { Info, HelpCircle } from 'lucide-react';
import type { ShapExplanation } from '../../types';


interface Props {
  explanation: ShapExplanation;
}

export const ShapExplainabilityCard: React.FC<Props> = ({ explanation }) => {
  if (!explanation.explanation_available || !explanation.feature_attributions) {
    return (
      <div className="card">
        <h3 className="card-title"><Info size={18} /> Real SHAP Explainability</h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
          SHAP feature attributions unavailable for this prediction record.
        </p>
      </div>
    );
  }

  const maxAbsShap = Math.max(...explanation.feature_attributions.map(a => Math.abs(a.shap_value)), 0.1);

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">
          <Info size={18} color="var(--color-info)" /> Real SHAP Feature Explainability
        </h3>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          Output Space: Log-Odds
        </span>
      </div>

      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        Top physiological feature attributions driving model risk prediction for this patient:
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {explanation.feature_attributions.slice(0, 7).map((attr, idx) => {
          const isPositive = attr.shap_value >= 0;
          const barWidthPercent = Math.min(100, Math.max(8, (Math.abs(attr.shap_value) / maxAbsShap) * 100));

          return (
            <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{attr.description}</span>
                <span style={{ fontWeight: 700, color: isPositive ? 'var(--color-critical)' : 'var(--color-stable)', fontFamily: 'var(--font-mono)' }}>
                  {isPositive ? '+' : ''}{attr.shap_value.toFixed(3)}
                </span>
              </div>

              <div style={{ height: '8px', width: '100%', backgroundColor: 'var(--bg-subtle)', borderRadius: '4px', overflow: 'hidden' }}>
                <div 
                  style={{ 
                    height: '100%', 
                    width: `${barWidthPercent}%`, 
                    backgroundColor: isPositive ? 'var(--color-critical)' : 'var(--color-stable)',
                    borderRadius: '4px'
                  }} 
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Mandatory Clinical Disclaimer */}
      <div style={{ marginTop: '1.25rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
        <HelpCircle size={14} style={{ flexShrink: 0 }} />
        <span>
          <strong>Disclaimer:</strong> SHAP values represent model contribution, not causation.
        </span>
      </div>
    </div>
  );
};
