import { useState } from 'react';
import { 
  Activity,
  Heart, 
  Thermometer, 
  Wind, 
  Droplets,
  ActivitySquare,
  ShieldAlert,
  Brain,
  Info
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  ReferenceLine
} from 'recharts';

// Mock Data
const MOCK_PATIENTS = [
  { id: '1', name: 'John Doe', bed: 'ICU-01', age: 65, status: 'critical', riskScore: 87, riskTrend: 'up' },
  { id: '2', name: 'Jane Smith', bed: 'ICU-02', age: 72, status: 'warning', riskScore: 65, riskTrend: 'stable' },
  { id: '3', name: 'Robert Johnson', bed: 'ICU-03', age: 54, status: 'stable', riskScore: 12, riskTrend: 'down' },
  { id: '4', name: 'Maria Garcia', bed: 'ICU-04', age: 68, status: 'warning', riskScore: 55, riskTrend: 'up' },
];

const TRAJECTORY_DATA = [
  { time: '00:00', risk: 20 },
  { time: '04:00', risk: 25 },
  { time: '08:00', risk: 35 },
  { time: '12:00', risk: 45 },
  { time: '16:00', risk: 60 },
  { time: '20:00', risk: 87 },
];

const LAB_TRENDS_DATA = [
  { time: 'Day 1', lactate: 1.2, wbc: 11, crp: 15 },
  { time: 'Day 2', lactate: 1.8, wbc: 14, crp: 45 },
  { time: 'Day 3', lactate: 2.5, wbc: 18, crp: 85 },
  { time: 'Day 4', lactate: 4.1, wbc: 22, crp: 120 },
];

export default function App() {
  const [activePatientId, setActivePatientId] = useState('1');

  const activePatient = MOCK_PATIENTS.find(p => p.id === activePatientId) || MOCK_PATIENTS[0];

  return (
    <div className="dashboard-container">
      {/* Sidebar: Patient List & ICU Overview */}
      <div className="sidebar">
        <div className="sidebar-header">
          <ActivitySquare size={24} color="var(--color-info)" />
          <h1>SepsisGuard AI</h1>
        </div>
        <div className="patient-list">
          <h2 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', textTransform: 'uppercase', paddingLeft: '0.5rem' }}>ICU Patient Roster</h2>
          {MOCK_PATIENTS.map(patient => (
            <div 
              key={patient.id} 
              className={`patient-card ${patient.status} ${activePatientId === patient.id ? 'active' : ''}`}
              onClick={() => setActivePatientId(patient.id)}
            >
              <div className="patient-info">
                <h3>{patient.bed} - {patient.name}</h3>
                <p>Age: {patient.age} | Risk: {patient.riskScore}%</p>
              </div>
              <div className="status-indicator"></div>
            </div>
          ))}
        </div>
      </div>

      {/* Main Content: Patient Detail View */}
      <div className="main-content">
        <div className="header-panel">
          <div>
            <h1 style={{ fontSize: '1.75rem', marginBottom: '0.25rem' }}>{activePatient.name}</h1>
            <p style={{ color: 'var(--text-secondary)' }}>Bed {activePatient.bed} • Age {activePatient.age} • Admitted: 2 days ago</p>
          </div>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <div className="badge badge-outline">SIRS: 3/4</div>
            <div className="badge badge-outline">qSOFA: 2/3</div>
            <div className="badge badge-outline">NEWS: 7 (High)</div>
          </div>
        </div>

        <div className="grid-layout">
          
          {/* Risk Score & AI Confidence */}
          <div className="card col-span-3">
            <h2><Brain size={18} /> Sepsis Risk Score</h2>
            <div className="risk-score-display">
              <div className={`risk-value risk-${activePatient.status}`}>
                {activePatient.riskScore}%
              </div>
              <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
                Trajectory: {activePatient.riskTrend === 'up' ? 'Worsening' : 'Improving'}
              </p>
            </div>
            <div style={{ marginTop: '2rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span>AI Confidence</span>
                <span>92%</span>
              </div>
              <div className="confidence-bar">
                <div className="confidence-fill" style={{ width: '92%' }}></div>
              </div>
            </div>
          </div>

          {/* Current Vitals */}
          <div className="card col-span-5">
            <h2><Activity size={18} /> Current Vitals (Continuous)</h2>
            <div className="vital-grid">
              <div className="vital-item">
                <div className="vital-label">
                  <span>Heart Rate</span>
                  <Heart size={14} color="var(--color-critical)" />
                </div>
                <div className="vital-value" style={{ color: 'var(--color-critical)' }}>
                  115<span className="vital-unit">bpm</span>
                </div>
                <div className="signal-quality signal-good mt-1">● Good Signal</div>
              </div>
              <div className="vital-item">
                <div className="vital-label">
                  <span>MAP</span>
                  <Activity size={14} />
                </div>
                <div className="vital-value" style={{ color: 'var(--color-warning)' }}>
                  62<span className="vital-unit">mmHg</span>
                </div>
                <div className="signal-quality signal-good mt-1">● Good Signal</div>
              </div>
              <div className="vital-item">
                <div className="vital-label">
                  <span>Temperature</span>
                  <Thermometer size={14} />
                </div>
                <div className="vital-value" style={{ color: 'var(--color-critical)' }}>
                  39.1<span className="vital-unit">°C</span>
                </div>
              </div>
              <div className="vital-item">
                <div className="vital-label">
                  <span>SpO2</span>
                  <Wind size={14} />
                </div>
                <div className="vital-value">
                  94<span className="vital-unit">%</span>
                </div>
                <div className="signal-quality signal-poor mt-1">● Artifact Detected</div>
              </div>
            </div>
          </div>

          {/* Alert Panel */}
          <div className="card col-span-4" style={{ overflowY: 'auto', maxHeight: '300px' }}>
            <h2><ShieldAlert size={18} /> Active Alerts</h2>
            {activePatient.status === 'critical' ? (
              <>
                <div className="alert-item alert-critical">
                  <strong>CRITICAL: High Sepsis Risk</strong>
                  <p style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>Risk exceeded threshold 2 hours ago. Lactate pending.</p>
                </div>
                <div className="alert-item alert-warning">
                  <strong>WARNING: Hypotension trend</strong>
                  <p style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>MAP &lt; 65 mmHg for last 45 mins.</p>
                </div>
              </>
            ) : (
              <p style={{ color: 'var(--text-secondary)' }}>No active critical alerts.</p>
            )}
          </div>

          {/* Deterioration Trajectory */}
          <div className="card col-span-8">
            <h2><Activity size={18} /> Deterioration Trajectory (24h)</h2>
            <div className="chart-container">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={TRAJECTORY_DATA} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorRisk" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-critical)" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="var(--color-critical)" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
                  <XAxis dataKey="time" stroke="var(--text-secondary)" fontSize={12} />
                  <YAxis stroke="var(--text-secondary)" fontSize={12} domain={[0, 100]} />
                  <Tooltip contentStyle={{ backgroundColor: 'var(--bg-tertiary)', border: 'none', borderRadius: '4px' }} />
                  <ReferenceLine y={80} stroke="var(--color-critical)" strokeDasharray="3 3" label={{ position: 'insideTopLeft', value: 'Critical Threshold', fill: 'var(--color-critical)', fontSize: 12 }} />
                  <Area type="monotone" dataKey="risk" stroke="var(--color-critical)" fillOpacity={1} fill="url(#colorRisk)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* AI Explanation */}
          <div className="card col-span-4">
            <h2><Info size={18} /> AI Explanation</h2>
            <p style={{ fontSize: '0.9rem', marginBottom: '1rem', color: 'var(--text-secondary)' }}>
              Top factors contributing to the current risk score:
            </p>
            <ul className="explanation-list">
              <li>
                <span>Serum Lactate (Rising)</span>
                <span style={{ color: 'var(--color-critical)' }}>+32%</span>
              </li>
              <li>
                <span>Heart Rate Variability (Low)</span>
                <span style={{ color: 'var(--color-warning)' }}>+18%</span>
              </li>
              <li>
                <span>Systolic BP (Trending Down)</span>
                <span style={{ color: 'var(--color-warning)' }}>+15%</span>
              </li>
              <li>
                <span>WBC Count</span>
                <span style={{ color: 'var(--color-info)' }}>+12%</span>
              </li>
            </ul>
          </div>

          {/* Laboratory Trends */}
          <div className="card col-span-12">
            <h2><Droplets size={18} /> Laboratory Trends</h2>
            <div className="chart-container">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={LAB_TRENDS_DATA} margin={{ top: 10, right: 30, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
                  <XAxis dataKey="time" stroke="var(--text-secondary)" fontSize={12} />
                  <YAxis yAxisId="left" stroke="var(--color-critical)" fontSize={12} />
                  <YAxis yAxisId="right" orientation="right" stroke="var(--color-warning)" fontSize={12} />
                  <Tooltip contentStyle={{ backgroundColor: 'var(--bg-tertiary)', border: 'none', borderRadius: '4px' }} />
                  <Line yAxisId="left" type="monotone" dataKey="lactate" name="Lactate (mmol/L)" stroke="var(--color-critical)" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                  <Line yAxisId="right" type="monotone" dataKey="wbc" name="WBC (x10^9/L)" stroke="var(--color-warning)" strokeWidth={2} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
