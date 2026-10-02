import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import { VitalUpdateMessage } from '../types';

interface VitalChartsProps {
  history: VitalUpdateMessage[];
}

export const VitalCharts: React.FC<VitalChartsProps> = ({ history }) => {
  const chartData = history.map((msg) => {
    const timeStr = msg.simulation_time.substring(11, 19);
    return {
      time: timeStr,
      heart_rate: msg.vitals.heart_rate,
      systolic_bp: msg.vitals.systolic_bp,
      diastolic_bp: msg.vitals.diastolic_bp,
      spo2: msg.vitals.spo2,
      temperature: msg.vitals.temperature,
      respiratory_rate: msg.vitals.respiratory_rate,
    };
  });

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      
      {/* 1. Heart Rate Trajectory */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3 shadow-xl">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold font-mono text-slate-300 tracking-wider">HEART RATE TRAJECTORY (bpm)</h3>
          <span className="text-[10px] font-mono text-slate-500">Live 60s Window</span>
        </div>
        <div className="h-48 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
              <YAxis domain={[30, 200]} stroke="#64748b" tick={{ fontSize: 10 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '12px' }}
                labelStyle={{ color: '#94a3b8' }}
              />
              <Line
                type="monotone"
                dataKey="heart_rate"
                stroke="#f43f5e"
                strokeWidth={2}
                dot={false}
                connectNulls={false}
                name="Heart Rate (bpm)"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 2. Blood Pressure Trajectory (SBP & DBP) */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3 shadow-xl">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold font-mono text-slate-300 tracking-wider">BLOOD PRESSURE TRAJECTORY (mmHg)</h3>
          <span className="text-[10px] font-mono text-slate-500">SBP (Blue) / DBP (Cyan)</span>
        </div>
        <div className="h-48 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
              <YAxis domain={[30, 220]} stroke="#64748b" tick={{ fontSize: 10 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '12px' }}
                labelStyle={{ color: '#94a3b8' }}
              />
              <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '4px' }} />
              <Line
                type="monotone"
                dataKey="systolic_bp"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
                connectNulls={false}
                name="Systolic BP"
              />
              <Line
                type="monotone"
                dataKey="diastolic_bp"
                stroke="#06b6d4"
                strokeWidth={2}
                dot={false}
                connectNulls={false}
                name="Diastolic BP"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 3. SpO2 & Temperature Trajectories */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3 shadow-xl">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold font-mono text-slate-300 tracking-wider">OXYGEN SATURATION SpO₂ (%)</h3>
          <span className="text-[10px] font-mono text-slate-500">SpO2 (Teal)</span>
        </div>
        <div className="h-48 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
              <YAxis domain={[70, 100]} stroke="#64748b" tick={{ fontSize: 10 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '12px' }}
                labelStyle={{ color: '#94a3b8' }}
              />
              <Line
                type="monotone"
                dataKey="spo2"
                stroke="#14b8a6"
                strokeWidth={2}
                dot={false}
                connectNulls={false}
                name="SpO2 (%)"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 4. Respiratory Rate & Temperature Trajectories */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3 shadow-xl">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold font-mono text-slate-300 tracking-wider">RESPIRATORY RATE (breaths/min)</h3>
          <span className="text-[10px] font-mono text-slate-500">RR (Purple)</span>
        </div>
        <div className="h-48 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
              <YAxis domain={[5, 45]} stroke="#64748b" tick={{ fontSize: 10 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '12px' }}
                labelStyle={{ color: '#94a3b8' }}
              />
              <Line
                type="monotone"
                dataKey="respiratory_rate"
                stroke="#a855f7"
                strokeWidth={2}
                dot={false}
                connectNulls={false}
                name="Respiratory Rate"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

    </div>
  );
};
