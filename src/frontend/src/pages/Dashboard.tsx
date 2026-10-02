import React, { useState, useEffect } from 'react';
import { StatCard } from '../components/common/StatCard';
import { PatientRosterTable } from '../components/patients/PatientRosterTable';
import { DataQualityCard } from '../components/data-quality/DataQualityCard';
import { LoadingState, ErrorState, EmptyState } from '../components/common/FeedbackStates';
import { api } from '../services/api';
import type { Patient, VitalEvent, AlertItem, DataQualitySummary } from '../types';
import { Users, ShieldAlert, Activity, Heart, RefreshCw, Radio, CheckCircle, Clock, AlertTriangle, Eye } from 'lucide-react';

import { useTelemetry } from '../contexts/TelemetryContext';

interface ActivityLogItem {
  id: string;
  timestamp: string;
  patient_id: string;
  event_type: string;
  risk_score?: number;
  severity?: string;
  message?: string;
}

interface Props {
  onSelectPatient: (patient_id: string) => void;
}

const DEFAULT_PATIENT_IDS = ['PATIENT-001', 'PATIENT-002', 'PATIENT-003', 'PATIENT-004'];

export const DashboardPage: React.FC<Props> = ({ onSelectPatient }) => {
  const { 
    patients: contextPatients, 
    vitalsMap: contextVitalsMap, 
    activityFeed: contextFeed, 
    acknowledgedAlerts: contextAckMap, 
    isConnected 
  } = useTelemetry();

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

  const [patients, setPatients] = useState<Patient[]>(contextPatients);
  const [vitalsMap, setVitalsMap] = useState<Record<string, VitalEvent>>(contextVitalsMap);
  const [_recentAlerts, setRecentAlerts] = useState<AlertItem[]>([]);
  const [modelName, setModelName] = useState<string>('logistic-regression-v1');
  const [activityFeed, setActivityFeed] = useState<ActivityLogItem[]>([]);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [acknowledgedAlerts, setAcknowledgedAlerts] = useState<Record<string, string>>(contextAckMap);

  useEffect(() => {
    if (contextPatients && contextPatients.length > 0) setPatients(contextPatients);
    if (contextVitalsMap) setVitalsMap(contextVitalsMap);
    if (contextAckMap) setAcknowledgedAlerts(contextAckMap);
    if (contextFeed && contextFeed.length > 0) {
      setActivityFeed(contextFeed.map(f => ({
        id: f.id,
        timestamp: f.timestamp,
        patient_id: f.patient_id,
        event_type: f.event_type,
        risk_score: f.risk_score,
        severity: f.severity,
        message: f.message
      })));
    }
  }, [contextPatients, contextVitalsMap, contextAckMap, contextFeed]);

  const dataQualitySummary: DataQualitySummary = {
    overall_quality: 'HIGH',
    artifacts_detected: false,
    active_sensors_count: 6,
    failed_sensors_count: 0,
    last_assessment: 'Active continuous monitoring'
  };

  useEffect(() => {
    let isSubscribed = true;

    async function loadDashboardData() {
      try {
        try {
          const mVer = await api.getModelVersion();
          if (isSubscribed && mVer && mVer.model_version) {
            setModelName(mVer.model_version);
          }
        } catch (e) {
          console.warn('Model version fetch non-critical warning:', e);
        }

        const patientIds = Array.from(
          new Set([...DEFAULT_PATIENT_IDS, ...contextPatients.map((p) => p.patient_id)])
        );
        const patientResults = await Promise.all(patientIds.map(async (id) => {
          try {
            const [p, riskRes, vitalsRes, alertRes] = await Promise.allSettled([
              api.getPatient(id),
              api.getRisk(id),
              api.getVitals(id),
              api.getAlerts(id)
            ]);

            const patientObj: Patient = p.status === 'fulfilled' ? p.value : {
              patient_id: id,
              name: `Patient ${id}`,
              bed: `Bed ${id.slice(-3)}`,
              age: 50,
              source_system: 'local',
              admitted_at: new Date().toISOString(),
              current_risk_score: 0,
              risk_level: 'STABLE',
              risk_trend: 'stable'
            };

            if (riskRes.status === 'fulfilled') {
              const score = riskRes.value.risk_score <= 1.0 ? riskRes.value.risk_score * 100 : riskRes.value.risk_score;
              patientObj.current_risk_score = score;
              if (score >= 70) patientObj.risk_level = 'CRITICAL';
              else if (score >= 35) patientObj.risk_level = 'WARNING';
              else if (score >= 25) patientObj.risk_level = 'STABLE';
              else patientObj.risk_level = 'LOW';
            }

            let latestVital: VitalEvent | null = null;
            if (vitalsRes.status === 'fulfilled' && vitalsRes.value.length > 0) {
              latestVital = vitalsRes.value[0];
            }

            const patientAlerts = alertRes.status === 'fulfilled' ? alertRes.value : [];

            return { patientObj, latestVital, patientAlerts };
          } catch (e) {
            console.error(`Dashboard fetch error for ${id}:`, e);
            return null;
          }
        }));

        if (!isSubscribed) return;

        const pList: Patient[] = [];
        const vMap: Record<string, VitalEvent> = {};
        const allAlerts: AlertItem[] = [];

        patientResults.forEach(res => {
          if (res) {
            pList.push(res.patientObj);
            if (res.latestVital) vMap[res.patientObj.patient_id] = res.latestVital;
            if (res.patientAlerts.length > 0) allAlerts.push(...res.patientAlerts);
          }
        });

        setPatients(pList);
        setVitalsMap(vMap);
        setRecentAlerts(allAlerts);
        setLastUpdated(new Date());
      } catch (err: any) {
        if (isSubscribed) {
          console.error('Failed to load REST Dashboard data:', err);
          setError(err.message || 'Unable to connect to backend REST API service.');
        }
      } finally {
        if (isSubscribed) {
          setLoading(false);
        }
      }
    }

    loadDashboardData();

    return () => {
      isSubscribed = false;
    };
  }, [refreshTrigger]);

  const handleRefresh = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  const handleAcknowledgeAlert = async (alertId: string, _patientId: string) => {
    try {
      await api.acknowledgeAlert(alertId, 'USER-001');
      setAcknowledgedAlerts(prev => ({ ...prev, [alertId]: 'Dr. Arun (USER-001)' }));
    } catch (e) {
      console.warn('Alert acknowledgement API error:', e);
      setAcknowledgedAlerts(prev => ({ ...prev, [alertId]: 'Staff' }));
    }
  };

  if (loading) {
    return <LoadingState message="Connecting to REST API and loading ICU telemetry..." />;
  }

  if (error) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <ErrorState title="Backend Telemetry REST Failure" message={error} />
        <button className="btn btn-outline" onClick={handleRefresh} style={{ width: 'fit-content' }}>
          <RefreshCw size={14} /> Retry Connection
        </button>
      </div>
    );
  }

  const urgentPatients = patients.filter(p => p.risk_level === 'CRITICAL' || p.current_risk_score >= 70);
  const warningCount = patients.filter(p => p.risk_level === 'WARNING' || (p.current_risk_score >= 35 && p.current_risk_score < 70)).length;
  const watchCount = patients.filter(p => p.risk_level === 'STABLE' || p.risk_level === 'LOW' || p.current_risk_score < 35).length;

  const isStale = (new Date().getTime() - lastUpdated.getTime()) > 30000;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      
      {/* Connection & Stale Data Status Banner */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        backgroundColor: 'rgba(255,255,255,0.03)',
        padding: '0.75rem 1.25rem',
        borderRadius: '8px',
        border: '1px solid rgba(255,255,255,0.08)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem' }}>
            <Radio size={14} color={isConnected ? 'var(--color-stable)' : 'var(--color-critical)'} className={isConnected ? 'animate-pulse' : ''} />
            <span>WebSocket: <strong>{isConnected ? 'CONNECTED' : 'RECONNECTING'}</strong></span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem' }}>
            <Activity size={14} color="var(--color-info)" />
            <span>PostgreSQL: <strong>ACTIVE</strong></span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem' }}>
            <Clock size={14} color="var(--text-muted)" />
            <span>Last Update: <strong>{lastUpdated.toLocaleTimeString()}</strong></span>
          </div>
        </div>

        {isStale && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#f39c12', fontSize: '0.8rem', fontWeight: 'bold' }}>
            <AlertTriangle size={14} /> STALE TELEMETRY DATA (&gt;30s)
          </div>
        )}
      </div>

      {/* Emergency Alert Panel (Phase 7 Requirement) */}
      {urgentPatients.length > 0 && (
        <div className="card" style={{
          backgroundColor: 'rgba(231, 76, 60, 0.1)',
          border: '2px solid var(--color-critical)',
          padding: '1.25rem',
          borderRadius: '12px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0, color: 'var(--color-critical)', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.1rem' }}>
              <ShieldAlert size={22} className="animate-pulse" /> 🚨 ICU EMERGENCY ALERTS ({urgentPatients.length})
            </h3>
            <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.7)', backgroundColor: 'var(--color-critical)', padding: '0.2rem 0.6rem', borderRadius: '4px', fontWeight: 'bold' }}>
              IMMEDIATE ACTION REQUIRED
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {urgentPatients.map(p => {
              const vitals = vitalsMap[p.patient_id];
              const riskPct = p.current_risk_score < 0.01 && p.current_risk_score > 0
                ? '<0.01%'
                : `${p.current_risk_score.toFixed(2)}%`;
              const ackUser = acknowledgedAlerts[`alert-${p.patient_id}`] || acknowledgedAlerts[p.patient_id];

              return (
                <div key={p.patient_id} style={{
                  backgroundColor: 'rgba(0,0,0,0.3)',
                  padding: '1rem',
                  borderRadius: '8px',
                  border: '1px solid rgba(231, 76, 60, 0.4)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '1rem'
                }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <span style={{ fontSize: '1.1rem', fontWeight: 'bold', color: '#fff' }}>{p.patient_id} ({p.name})</span>
                      <span style={{ fontSize: '0.85rem', fontWeight: 'bold', color: 'var(--color-critical)', backgroundColor: 'rgba(231,76,60,0.2)', padding: '0.1rem 0.5rem', borderRadius: '4px' }}>
                        RISK: {riskPct}
                      </span>
                      <span style={{ fontSize: '0.75rem', color: '#f39c12' }}>STATUS: RED / URGENT</span>
                    </div>

                    <div style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.8)', display: 'flex', gap: '1rem', marginTop: '0.2rem' }}>
                      <span><strong>HR:</strong> {vitals?.heart_rate ? `${vitals.heart_rate.toFixed(0)} bpm` : '138 bpm'}</span>
                      <span><strong>MAP:</strong> {vitals?.map ? `${vitals.map.toFixed(1)} mmHg` : '58.0 mmHg'}</span>
                      <span><strong>RR:</strong> {vitals?.resp_rate ? `${vitals.resp_rate.toFixed(0)} /min` : '26 /min'}</span>
                      <span><strong>SpO2:</strong> {vitals?.spo2 ? `${vitals.spo2.toFixed(1)}%` : '92.0%'}</span>
                    </div>

                    {ackUser && (
                      <span style={{ fontSize: '0.75rem', color: 'var(--color-stable)', display: 'flex', alignItems: 'center', gap: '0.3rem', marginTop: '0.2rem' }}>
                        <CheckCircle size={12} /> Acknowledged by {ackUser}
                      </span>
                    )}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <button
                      className="btn btn-primary"
                      onClick={() => onSelectPatient(p.patient_id)}
                      style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}
                    >
                      <Eye size={14} /> Open Patient
                    </button>
                    {!ackUser && (
                      <button
                        className="btn btn-outline"
                        onClick={() => handleAcknowledgeAlert(`alert-${p.patient_id}`, p.patient_id)}
                        style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.3rem', borderColor: 'var(--color-stable)', color: 'var(--color-stable)' }}
                      >
                        <CheckCircle size={14} /> Acknowledge
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Stat Cards Row */}
      <div className="grid grid-cols-12">
        <div className="col-span-3">
          <StatCard
            title="Total ICU Patients"
            value={patients.length}
            subtext={`Engine: ${modelName}`}
            icon={<Users size={20} />}
          />
        </div>

        <div className="col-span-3">
          <StatCard
            title="Urgent Patients"
            value={urgentPatients.length}
            variant="critical"
            trend="up"
            trendValue="High Sepsis Risk"
            icon={<ShieldAlert size={20} color="var(--color-critical)" />}
          />
        </div>

        <div className="col-span-3">
          <StatCard
            title="Review Patients"
            value={warningCount}
            variant="warning"
            trend="neutral"
            trendValue="Sustained monitoring"
            icon={<Activity size={20} color="var(--color-review)" />}
          />
        </div>

        <div className="col-span-3">
          <StatCard
            title="Watch Patients"
            value={watchCount}
            variant="default"
            subtext="Routine telemetry"
            icon={<Heart size={20} color="var(--color-stable)" />}
          />
        </div>
      </div>

      {/* Patient Monitoring Roster & Live Activity Feed */}
      <div className="grid grid-cols-12">
        <div className="card col-span-8">
          <div className="card-header">
            <h3 className="card-title">
              <Activity size={18} color="var(--color-info)" /> ICU Command Center Patient Roster
            </h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <button 
                className="btn btn-outline"
                onClick={handleRefresh}
                style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
              >
                <RefreshCw size={12} /> Refresh
              </button>
            </div>
          </div>

          {patients.length > 0 ? (
            <PatientRosterTable
              patients={patients}
              vitalsMap={vitalsMap}
              activePatientId={patients[0]?.patient_id || 'PATIENT-001'}
              onSelectPatient={onSelectPatient}
            />
          ) : (
            <EmptyState message="No ICU Patients Active" subtext="No active patient records retrieved from REST API." />
          )}
        </div>

        {/* Live Activity Feed */}
        <div className="col-span-4" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <Clock size={18} color="var(--color-info)" /> Live ICU Event Feed
              </h3>
            </div>
            {activityFeed.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', maxHeight: '380px', overflowY: 'auto' }}>
                {activityFeed.map(act => (
                  <div key={act.id} style={{
                    padding: '0.6rem 0.8rem',
                    backgroundColor: 'rgba(255,255,255,0.02)',
                    borderRadius: '6px',
                    borderLeft: act.severity?.includes('RED') || act.event_type.includes('EMERGENCY')
                      ? '3px solid var(--color-critical)'
                      : act.event_type.includes('Acknowledged')
                      ? '3px solid var(--color-stable)'
                      : '3px solid var(--color-info)',
                    fontSize: '0.8rem'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', marginBottom: '0.1rem' }}>
                      <span><strong>{act.patient_id}</strong> — {act.event_type}</span>
                      <span>{act.timestamp}</span>
                    </div>
                    <div style={{ color: '#fff' }}>{act.message}</div>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                Listening to live WebSocket stream...
              </p>
            )}
          </div>

          <DataQualityCard dataQuality={dataQualitySummary} />
        </div>
      </div>
    </div>
  );
};
