import React from 'react';
import { ShieldCheck } from 'lucide-react';
import type { DataQualitySummary } from '../../types';
import { Badge } from '../common/Badge';


interface Props {
  dataQuality: DataQualitySummary;
}

export const DataQualityCard: React.FC<Props> = ({ dataQuality }) => {
  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">
          <ShieldCheck size={18} color="var(--color-stable)" /> Telemetry Signal Quality
        </h3>
        <Badge variant={dataQuality.overall_quality === 'HIGH' ? 'green' : 'orange'}>
          {dataQuality.overall_quality} QUALITY
        </Badge>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', margin: '0.5rem 0' }}>
        <div style={{ backgroundColor: 'var(--bg-subtle)', padding: '0.6rem 0.8rem', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Active Telemetry Sensors</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            {dataQuality.active_sensors_count} Sensors
          </div>
        </div>

        <div style={{ backgroundColor: 'var(--bg-subtle)', padding: '0.6rem 0.8rem', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Signal Artifact Status</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: dataQuality.artifacts_detected ? 'var(--color-review)' : 'var(--color-stable)' }}>
            {dataQuality.artifacts_detected ? 'Artifact Flagged' : 'Clean Signal'}
          </div>
        </div>
      </div>
    </div>
  );
};
