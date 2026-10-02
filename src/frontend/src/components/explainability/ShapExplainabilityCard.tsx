import React, { useState } from 'react';
import { Info, HelpCircle, ChevronDown, ChevronUp } from 'lucide-react';
import type { ShapExplanation } from '../../types';

interface Props {
  explanation: ShapExplanation;
}

export const ShapExplainabilityCard: React.FC<Props> = ({ explanation }) => {
  const [showAll, setShowAll] = useState<boolean>(false);

  if (!explanation.explanation_available || !explanation.feature_attributions || explanation.feature_attributions.length === 0) {
    return (
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <Info size={18} color="var(--color-info)" /> Real SHAP Feature Explainability
          </h3>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
          SHAP feature attributions unavailable for this prediction record.
        </p>
        <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          <HelpCircle size={14} style={{ flexShrink: 0 }} />
          <span>
            <strong>Disclaimer:</strong> SHAP values represent model contribution, not causation.
          </span>
        </div>
      </div>
    );
  }

  const attributions = explanation.feature_attributions;
  const displayItems = showAll ? attributions : attributions.slice(0, 6);
  const maxAbsShap = Math.max(...attributions.map(a => Math.abs(a.shap_value)), 0.1);

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
        Physiological feature attributions driving model risk prediction for this patient ({attributions.length} features analyzed):
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {displayItems.map((attr, idx) => {
          const isPositive = attr.shap_value >= 0;
          const barWidthPercent = Math.min(100, Math.max(8, (Math.abs(attr.shap_value) / maxAbsShap) * 100));

          return (
            <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{attr.description || attr.feature_name}</span>
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

      {attributions.length > 6 && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="btn btn-outline"
          style={{ 
            marginTop: '0.75rem', 
            width: '100%', 
            fontSize: '0.8rem', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            gap: '0.35rem',
            padding: '0.35rem 0.5rem'
          }}
        >
          {showAll ? (
            <>
              Show Top Features <ChevronUp size={14} />
            </>
          ) : (
            <>
              View All {attributions.length} Backend Model Features <ChevronDown size={14} />
            </>
          )}
        </button>
      )}

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
