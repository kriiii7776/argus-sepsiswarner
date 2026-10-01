import React from 'react';
import { SignalQualityBadge } from '../common/Badge';
import type { SignalQuality } from '../../types';

interface VitalCardProps {
  label: string;
  value: number | string | null;
  unit: string;
  icon: React.ReactNode;
  statusVariant?: 'normal' | 'warning' | 'critical';
  signalQuality?: SignalQuality;
  subtext?: string;
}

export const VitalCard: React.FC<VitalCardProps> = ({
  label,
  value,
  unit,
  icon,
  statusVariant = 'normal',
  signalQuality = 'HIGH',
  subtext
}) => {
  const getValueColor = () => {
    switch (statusVariant) {
      case 'critical': return 'var(--color-critical)';
      case 'warning': return 'var(--color-review)';
      default: return 'var(--text-primary)';
    }
  };

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-secondary)' }}>
        <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{label}</span>
        {icon}
      </div>

      <div style={{ margin: '0.75rem 0 0.5rem 0' }}>
        <span style={{ fontSize: '2.1rem', fontWeight: 700, color: getValueColor(), letterSpacing: '-0.02em' }}>
          {value !== null && value !== undefined ? value : '--'}
        </span>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginLeft: '0.3rem', fontWeight: 500 }}>
          {unit}
        </span>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 'auto', paddingTop: '0.5rem', borderTop: '1px solid var(--border-light)' }}>
        <SignalQualityBadge quality={signalQuality} />
        {subtext && <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{subtext}</span>}
      </div>
    </div>
  );
};
