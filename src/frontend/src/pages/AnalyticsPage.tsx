import React from 'react';
import { useTelemetry } from '../contexts/TelemetryContext';
import { StatCard } from '../components/common/StatCard';
import { Badge } from '../components/common/Badge';
import { BarChart3, Activity, Heart, ShieldAlert, Radio, TrendingUp, Cpu } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

export const AnalyticsPage: React.FC = () => {
  const { patients, trajectoriesMap, vitalsMap, isConnected, lastUpdated } = useTelemetry();

  const totalPatients = patients.length;
  const urgentCount = patients.filter((p) => p.risk_level === 'CRITICAL').length;
  const reviewCount = patients.filter((p) => p.risk_level === 'WARNING').length;
  const watchCount = patients.filter((p) => p.risk_level === 'STABLE' || p.risk_level === 'LOW').length;

  // Prepare combined trajectory data chart
  const trajectoryChartData = React.useMemo(() => {
    const timeMap: Record<string, Record<string, number>> = {};

    Object.entries(trajectoriesMap).forEach(([pid, points]) => {
      points.forEach((pt) => {
        const timeLabel = new Date(pt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        if (!timeMap[timeLabel]) {
          timeMap[timeLabel] = {};
        }
        timeMap[timeLabel][pid] = Number((pt.risk_probability * 100).toFixed(1));
      });
    });

    return Object.entries(timeMap).map(([time, pData]) => ({
      time,
      ...pData
    })).slice(-15);
  }, [trajectoriesMap]);

  const patientColors = ['#e74c3c', '#f39c12', '#3498db', '#2ecc71'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Analytics Top Header */}
      <div className="card" style={{ borderLeft: '4px solid var(--color-info)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <BarChart3 size={20} color="var(--color-info)" /> ICU Population Health & Predictive Analytics
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
              Active AI Model: <code style={{ fontFamily: 'var(--font-mono)' }}>logistic-regression-v1</code> | Real-Time Telemetry Stream: {isConnected ? 'Active' : 'Reconnecting'}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Badge variant={isConnected ? 'green' : 'orange'}>
              <Radio size={12} className={isConnected ? 'animate-pulse' : ''} /> {isConnected ? 'STREAM CONNECTED' : 'DISCONNECTED'}
            </Badge>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          </div>
        </div>
      </div>

      {/* Population Risk Cards */}
      <div className="grid grid-cols-12">
        <div className="col-span-3">
          <StatCard
            title="TOTAL PATIENTS"
            value={totalPatients}
            subtitle="Monitored in ICU"
            icon={<Heart size={20} />}
            variant="blue"
          />
        </div>
        <div className="col-span-3">
          <StatCard
            title="URGENT / CRITICAL"
            value={urgentCount}
            subtitle="Sepsis Risk >80%"
            icon={<ShieldAlert size={20} />}
            variant="red"
          />
        </div>
        <div className="col-span-3">
          <StatCard
            title="REVIEW / WARNING"
            value={reviewCount}
            subtitle="Rapid Risk Escalation"
            icon={<TrendingUp size={20} />}
            variant="orange"
          />
        </div>
        <div className="col-span-3">
          <StatCard
            title="WATCH / STABLE"
            value={watchCount}
            subtitle="Within Baseline Thresholds"
            icon={<Activity size={20} />}
            variant="green"
          />
        </div>
      </div>

      {/* Comparative Risk Trajectory Chart */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <TrendingUp size={18} color="var(--color-info)" /> Comparative ICU Patient Sepsis Risk Trajectories (%)
          </h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Real-Time Horizon (31 Temporal Features Pipeline)
          </span>
        </div>

        {trajectoryChartData.length > 0 ? (
          <div style={{ height: '320px', width: '100%', marginTop: '1rem' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trajectoryChartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                <XAxis dataKey="time" stroke="var(--text-muted)" fontSize={12} />
                <YAxis domain={[0, 100]} stroke="var(--text-muted)" fontSize={12} unit="%" />
                <Tooltip
                  contentStyle={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)', borderRadius: 'var(--radius-md)' }}
                  formatter={(val: any) => [`${val}%`, 'Risk Probability']}
                />
                <Legend />
                {patients.map((p, idx) => (
                  <Line
                    key={p.patient_id}
                    type="monotone"
                    dataKey={p.patient_id}
                    name={`${p.patient_id} (${p.risk_level})`}
                    stroke={patientColors[idx % patientColors.length]}
                    strokeWidth={2}
                    dot={{ r: 3 }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Badge variant="orange">Insufficient live data</Badge>
            <p style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>
              Waiting for live simulator telemetry stream to populate trajectory history.
            </p>
          </div>
        )}
      </div>

      {/* Model & Data Quality Summary */}
      <div className="grid grid-cols-12">
        {/* Active Model Specs */}
        <div className="card col-span-6">
          <div className="card-header">
            <h3 className="card-title">
              <Cpu size={18} color="var(--color-info)" /> Active ML Model Provenance & Pipeline Specs
            </h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem', marginTop: '0.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-sm)' }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Active Runtime Model:</span>
              <strong style={{ fontSize: '0.85rem', fontFamily: 'var(--font-mono)' }}>logistic-regression-v1</strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-sm)' }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Technically Validated Candidate:</span>
              <strong style={{ fontSize: '0.85rem', fontFamily: 'var(--font-mono)' }}>xgboost-tabular-v1</strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-sm)' }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Canonical Feature Extraction:</span>
              <strong style={{ fontSize: '0.85rem', color: 'var(--color-stable)' }}>31 Temporal Features</strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-sm)' }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Calibration Method:</span>
              <strong style={{ fontSize: '0.85rem', color: 'var(--color-info)' }}>Platt Scaling / Isotonic</strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-sm)' }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Explainability Engine:</span>
              <strong style={{ fontSize: '0.85rem', color: 'var(--color-review)' }}>Tree / Kernel SHAP</strong>
            </div>
          </div>
        </div>

        {/* Live Patient Roster Telemetry Breakdown */}
        <div className="card col-span-6">
          <div className="card-header">
            <h3 className="card-title">
              <Activity size={18} color="var(--color-stable)" /> Live Telemetry Vital Signs Overview
            </h3>
          </div>
          <table className="roster-table">
            <thead>
              <tr>
                <th>PATIENT</th>
                <th>HR (bpm)</th>
                <th>MAP (mmHg)</th>
                <th>SpO2 (%)</th>
                <th>RISK %</th>
              </tr>
            </thead>
            <tbody>
              {patients.map((p) => {
                const v = vitalsMap[p.patient_id];
                const riskPct = (p.current_risk_score * 100).toFixed(1);
                return (
                  <tr key={p.patient_id}>
                    <td style={{ fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{p.patient_id}</td>
                    <td>{v && v.heart_rate != null ? Math.round(v.heart_rate) : <span style={{ color: 'var(--text-muted)' }}>N/A</span>}</td>
                    <td>{v && v.map != null ? Math.round(v.map) : <span style={{ color: 'var(--text-muted)' }}>N/A</span>}</td>
                    <td>{v && v.spo2 != null ? `${Math.round(v.spo2)}%` : <span style={{ color: 'var(--text-muted)' }}>N/A</span>}</td>
                    <td>
                      <Badge variant={p.risk_level === 'CRITICAL' ? 'red' : p.risk_level === 'WARNING' ? 'orange' : 'green'}>
                        {riskPct}% ({p.risk_level})
                      </Badge>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
