import React from 'react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';

interface VitalPoint {
  time: string;
  hr: number;
  map: number;
  temp: number;
  spo2: number;
  lactate: number;
}

interface Props {
  data: VitalPoint[];
}

export const VitalTrendCharts: React.FC<Props> = ({ data }) => {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
      {/* Heart Rate & MAP Chart */}
      <div className="card">
        <h4 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.75rem', color: 'var(--text-primary)' }}>
          Heart Rate (bpm) & MAP (mmHg) 24h Trend
        </h4>
        <div style={{ height: '200px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 20, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
              <XAxis dataKey="time" stroke="var(--text-secondary)" fontSize={11} />
              <YAxis stroke="var(--text-secondary)" fontSize={11} />
              <Tooltip contentStyle={{ backgroundColor: 'var(--bg-sidebar)', borderRadius: '6px', color: '#fff' }} />
              <Line type="monotone" dataKey="hr" name="Heart Rate (bpm)" stroke="var(--color-critical)" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="map" name="MAP (mmHg)" stroke="var(--color-info)" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Lactate & Temp Chart */}
      <div className="card">
        <h4 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.75rem', color: 'var(--text-primary)' }}>
          Serum Lactate (mmol/L) & Temp (°C) Trend
        </h4>
        <div style={{ height: '200px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 20, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
              <XAxis dataKey="time" stroke="var(--text-secondary)" fontSize={11} />
              <YAxis yAxisId="left" stroke="var(--color-review)" fontSize={11} />
              <YAxis yAxisId="right" orientation="right" stroke="var(--color-watch)" fontSize={11} />
              <Tooltip contentStyle={{ backgroundColor: 'var(--bg-sidebar)', borderRadius: '6px', color: '#fff' }} />
              <Line yAxisId="left" type="monotone" dataKey="lactate" name="Lactate (mmol/L)" stroke="var(--color-review)" strokeWidth={2} dot={{ r: 3 }} />
              <Line yAxisId="right" type="monotone" dataKey="temp" name="Temp (°C)" stroke="var(--color-watch)" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
