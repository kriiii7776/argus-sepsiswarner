import React from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtext?: string;
  icon?: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  badge?: React.ReactNode;
  variant?: 'default' | 'critical' | 'warning' | 'stable';
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtext,
  icon,
  trend,
  trendValue,
  badge,
  variant = 'default'
}) => {
  const getBorderColor = () => {
    switch (variant) {
      case 'critical': return 'var(--color-critical)';
      case 'warning': return 'var(--color-review)';
      case 'stable': return 'var(--color-stable)';
      default: return 'var(--border-color)';
    }
  };

  return (
    <div className="card" style={{ borderTop: `3px solid ${getBorderColor()}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.02em' }}>
          {title}
        </span>
        {icon && <div style={{ color: 'var(--text-secondary)' }}>{icon}</div>}
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem' }}>
        <span style={{ fontSize: '2rem', fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
          {value}
        </span>
        {badge}
      </div>

      {(subtext || trendValue) && (
        <div style={{ marginTop: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          {trend && (
            <span style={{ color: trend === 'up' ? 'var(--color-critical)' : trend === 'down' ? 'var(--color-stable)' : 'var(--text-muted)', fontWeight: 600 }}>
              {trend === 'up' ? '▲' : trend === 'down' ? '▼' : '●'} {trendValue}
            </span>
          )}
          {subtext && <span>{subtext}</span>}
        </div>
      )}
    </div>
  );
};
