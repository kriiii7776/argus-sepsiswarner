import React from 'react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  ReferenceLine 
} from 'recharts';

interface TrajectoryPoint {
  timeLabel: string;
  risk_probability: number; // 0.0 - 1.0
  alert_severity?: string;
}

interface Props {
  data: TrajectoryPoint[];
}

export const RiskTrajectoryChart: React.FC<Props> = ({ data }) => {
  const chartData = data.map(d => ({
    time: d.timeLabel,
    riskPct: Math.round(d.risk_probability * 100)
  }));

  return (
    <div style={{ width: '100%', height: '260px' }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--color-critical)" stopOpacity={0.7}/>
              <stop offset="95%" stopColor="var(--color-critical)" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
          <XAxis dataKey="time" stroke="var(--text-secondary)" fontSize={12} />
          <YAxis stroke="var(--text-secondary)" fontSize={12} domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
          <Tooltip 
            contentStyle={{ backgroundColor: 'var(--bg-sidebar)', borderColor: 'var(--border-sidebar)', borderRadius: '6px', color: '#fff' }}
            formatter={(value: any) => [`${value}%`, 'Sepsis Risk Score']}
          />
          <ReferenceLine y={80} stroke="var(--color-critical)" strokeDasharray="4 4" label={{ position: 'insideTopLeft', value: 'Critical Alert Threshold (80%)', fill: 'var(--color-critical)', fontSize: 11, fontWeight: 600 }} />
          <ReferenceLine y={50} stroke="var(--color-watch)" strokeDasharray="4 4" label={{ position: 'insideTopLeft', value: 'Watch Threshold (50%)', fill: 'var(--color-watch)', fontSize: 11 }} />
          <Area type="monotone" dataKey="riskPct" stroke="var(--color-critical)" strokeWidth={2.5} fillOpacity={1} fill="url(#riskGrad)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
