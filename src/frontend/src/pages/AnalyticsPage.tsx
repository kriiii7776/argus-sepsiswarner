import React, { useState, useEffect, useMemo } from 'react';
import { useTelemetry } from '../contexts/TelemetryContext';
import { api } from '../services/api';
import { StatCard } from '../components/common/StatCard';
import { Badge } from '../components/common/Badge';
import { BarChart3, Activity, Heart, ShieldAlert, Radio, TrendingUp, Cpu, Filter, Clock } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

export const AnalyticsPage: React.FC = () => {
  const { patients, trajectoriesMap, vitalsMap, isConnected, lastUpdated } = useTelemetry();

  const [selectedPatientId, setSelectedPatientId] = useState<string>('ALL');
  const [timeRange, setTimeRange] = useState<'1h' | '4h' | '6h' | 'ALL'>('ALL');
  const [restTrajectories, setRestTrajectories] = useState<Record<string, Array<{ timestamp: string; risk_probability: number; alert_severity?: string }>>>({});

  // Fetch REST trajectory points for all patients or selected patient if WebSocket stream hasn't populated full history
  useEffect(() => {
    let isSubscribed = true;
    async function loadTrajectories() {
      try {
        const targetIds = selectedPatientId === 'ALL'
          ? patients.map(p => p.patient_id)
          : [selectedPatientId];

        const results = await Promise.allSettled(
          targetIds.map(async (pid) => {
            const traj = await api.getTrajectory(pid);
            return { pid, points: traj.points || [] };
          })
        );

        if (!isSubscribed) return;

        const newMap: Record<string, Array<{ timestamp: string; risk_probability: number; alert_severity?: string }>> = {};
        results.forEach((res) => {
          if (res.status === 'fulfilled' && res.value.points.length > 0) {
            newMap[res.value.pid] = res.value.points.map(pt => ({
              timestamp: pt.timestamp,
              risk_probability: pt.risk_probability <= 1.0 ? pt.risk_probability : pt.risk_probability / 100,
              alert_severity: pt.alert_severity || undefined
            }));
          }
        });

        setRestTrajectories(prev => ({ ...prev, ...newMap }));
      } catch (err) {
        console.warn('REST trajectory load warning in Analytics:', err);
      }
    }

    if (patients.length > 0) {
      loadTrajectories();
    }
    return () => { isSubscribed = false; };
  }, [patients, selectedPatientId]);

  const totalPatients = patients.length;
  const urgentCount = patients.filter((p) => p.risk_level === 'CRITICAL').length;
  const reviewCount = patients.filter((p) => p.risk_level === 'WARNING').length;
  const watchCount = patients.filter((p) => p.risk_level === 'STABLE' || p.risk_level === 'LOW').length;

  // Filter and prepare trajectory data chart
  const trajectoryChartData = useMemo(() => {
    const timeMap: Record<string, Record<string, number>> = {};
    const activeTrajectories = { ...restTrajectories, ...trajectoriesMap };

    const targetPatients = selectedPatientId === 'ALL'
      ? patients
      : patients.filter(p => p.patient_id === selectedPatientId);

    const now = Date.now();
    const cutoffMs = timeRange === '1h' ? 3600 * 1000 : timeRange === '4h' ? 4 * 3600 * 1000 : timeRange === '6h' ? 6 * 3600 * 1000 : Infinity;

    targetPatients.forEach((p) => {
      const pid = p.patient_id;
      const points = activeTrajectories[pid] || [];

      points.forEach((pt) => {
        const ptTime = new Date(pt.timestamp).getTime();
        if (cutoffMs !== Infinity && now - ptTime > cutoffMs) return;

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
    })).slice(-20);
  }, [trajectoriesMap, restTrajectories, patients, selectedPatientId, timeRange]);

  // Selected patient statistics
  const selectedPatientStats = useMemo(() => {
    if (selectedPatientId === 'ALL') return null;
    const p = patients.find(patient => patient.patient_id === selectedPatientId);
    if (!p) return null;

    const points = (trajectoriesMap[selectedPatientId] || restTrajectories[selectedPatientId] || []);
    const riskScores = points.map(pt => pt.risk_probability * 100);
    const peakRisk = riskScores.length > 0 ? Math.max(...riskScores) : p.current_risk_score;
    const latestRisk = p.current_risk_score;

    return {
      patient: p,
      peakRisk: Number(peakRisk.toFixed(1)),
      latestRisk: Number(latestRisk.toFixed(1)),
      trajectoryCount: points.length
    };
  }, [selectedPatientId, patients, trajectoriesMap, restTrajectories]);

  const patientColors = ['#e74c3c', '#f39c12', '#3498db', '#2ecc71', '#9b59b6', '#1abc9c', '#e67e22', '#34495e'];

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

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            {/* Patient Filter Selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', backgroundColor: 'var(--bg-app)', padding: '0.3rem 0.6rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
              <Filter size={14} color="var(--color-info)" />
              <select
                value={selectedPatientId}
                onChange={(e) => setSelectedPatientId(e.target.value)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-primary)', fontSize: '0.8rem', outline: 'none', cursor: 'pointer', fontWeight: 600 }}
              >
                <option value="ALL">All ICU Patients ({totalPatients})</option>
                {patients.map(p => (
                  <option key={p.patient_id} value={p.patient_id}>{p.patient_id} ({p.risk_level})</option>
                ))}
              </select>
            </div>

            {/* Time Range Filter */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', backgroundColor: 'var(--bg-app)', padding: '0.3rem 0.6rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
              <Clock size={14} color="var(--color-info)" />
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value as any)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-primary)', fontSize: '0.8rem', outline: 'none', cursor: 'pointer', fontWeight: 600 }}
              >
                <option value="1h">Last 1 Hour</option>
                <option value="4h">Last 4 Hours</option>
                <option value="6h">Last 6 Hours</option>
                <option value="ALL">All Records</option>
              </select>
            </div>

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

      {/* Patient Specific Metrics Banner when Filtered */}
      {selectedPatientStats && (
        <div className="card" style={{ borderLeft: '4px solid var(--color-critical)', backgroundColor: 'var(--bg-card)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h4 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                Filter Active: Patient {selectedPatientStats.patient.patient_id}
              </h4>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                Source: {selectedPatientStats.patient.source_system} • Total Predictions Evaluated: {selectedPatientStats.trajectoryCount}
              </p>
            </div>

            <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center' }}>
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Current Risk</span>
                <strong style={{ fontSize: '1.1rem', color: selectedPatientStats.latestRisk >= 80 ? 'var(--color-critical)' : 'var(--text-primary)' }}>
                  {selectedPatientStats.latestRisk}%
                </strong>
              </div>
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Peak Trajectory Risk</span>
                <strong style={{ fontSize: '1.1rem', color: selectedPatientStats.peakRisk >= 80 ? 'var(--color-critical)' : 'var(--color-warning)' }}>
                  {selectedPatientStats.peakRisk}%
                </strong>
              </div>
              <Badge variant={selectedPatientStats.patient.risk_level === 'CRITICAL' ? 'red' : 'green'}>
                {selectedPatientStats.patient.risk_level}
              </Badge>
            </div>
          </div>
        </div>
      )}

      {/* Comparative Risk Trajectory Chart */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <TrendingUp size={18} color="var(--color-info)" /> Sepsis Risk Trajectories (%) — {selectedPatientId === 'ALL' ? 'Population View' : `Patient ${selectedPatientId}`}
          </h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Real Temporal History (31 Features Window | {timeRange})
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
                {(selectedPatientId === 'ALL' ? patients : patients.filter(p => p.patient_id === selectedPatientId)).map((p, idx) => (
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
            <Badge variant="orange">No trajectory data in range</Badge>
            <p style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>
              No PredictionRecord events match the selected patient/time filter.
            </p>
          </div>
        )}
      </div>

      {/* Model Specs & Telemetry Table */}
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
              {(selectedPatientId === 'ALL' ? patients : patients.filter(p => p.patient_id === selectedPatientId)).map((p) => {
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
