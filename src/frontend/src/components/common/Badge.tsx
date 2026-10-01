import React from 'react';
import type { AlertSeverity, RiskLevel, SignalQuality } from '../../types';


interface BadgeProps {
  children: React.ReactNode;
  variant?: 'red' | 'orange' | 'yellow' | 'green' | 'blue' | 'gray';
  size?: 'sm' | 'md';
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'gray', size = 'sm' }) => {
  const getVariantClass = () => {
    switch (variant) {
      case 'red': return 'badge-red';
      case 'orange': return 'badge-orange';
      case 'yellow': return 'badge-yellow';
      case 'green': return 'badge-green';
      case 'blue': return 'badge-blue';
      default: return 'badge-gray';
    }
  };

  return (
    <span className={`badge ${getVariantClass()}`} style={{ fontSize: size === 'md' ? '0.85rem' : '0.75rem' }}>
      {children}
    </span>
  );
};

export const AlertBadge: React.FC<{ severity?: AlertSeverity | string | null }> = ({ severity }) => {
  switch (severity) {
    case 'RED_URGENT':
      return <Badge variant="red">RED URGENT</Badge>;
    case 'ORANGE_REVIEW':
      return <Badge variant="orange">ORANGE REVIEW</Badge>;
    case 'YELLOW_WATCH':
      return <Badge variant="yellow">YELLOW WATCH</Badge>;
    default:
      return <Badge variant="green">NO ALERT</Badge>;
  }
};

export const RiskBadge: React.FC<{ level: RiskLevel }> = ({ level }) => {
  switch (level) {
    case 'CRITICAL':
      return <Badge variant="red">CRITICAL RISK</Badge>;
    case 'WARNING':
      return <Badge variant="orange">HIGH WARNING</Badge>;
    case 'STABLE':
    case 'LOW':
      return <Badge variant="green">STABLE</Badge>;
    default:
      return <Badge variant="blue">{level}</Badge>;
  }
};

export const SignalQualityBadge: React.FC<{ quality?: SignalQuality }> = ({ quality = 'HIGH' }) => {
  switch (quality) {
    case 'HIGH':
      return <span style={{ color: 'var(--color-stable)', fontSize: '0.75rem', fontWeight: 600 }}>● Good Signal</span>;
    case 'MEDIUM':
      return <span style={{ color: 'var(--color-watch)', fontSize: '0.75rem', fontWeight: 600 }}>● Medium Signal</span>;
    case 'LOW':
      return <span style={{ color: 'var(--color-critical)', fontSize: '0.75rem', fontWeight: 600 }}>● Artifact Detected</span>;
  }
};
