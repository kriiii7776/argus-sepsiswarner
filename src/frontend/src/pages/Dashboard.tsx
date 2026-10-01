import React, { useState, useEffect } from 'react';
import { StatCard } from '../components/common/StatCard';
import { PatientRosterTable } from '../components/patients/PatientRosterTable';
import { AlertCard } from '../components/alerts/AlertCard';
import { DataQualityCard } from '../components/data-quality/DataQualityCard';
import { LoadingState, ErrorState, EmptyState } from '../components/common/FeedbackStates';
import { api } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';
import type { Patient, VitalEvent, AlertItem, DataQualitySummary, RiskLevel, AlertSeverity } from '../types';
import { Users, ShieldAlert, Activity, Heart, RefreshCw, Radio } from 'lucide-react';

interface Props {
  onSelectPatient: (patient_id: string) => void;
}

const MONITORED_PATIENT_IDS = ['P-ICU-001', 'P-ICU-002', 'P-ICU-003', 'P-ICU-004', 'P-ICU-005'];

export const DashboardPage: React.FC<Props> = ({ onSelectPatient }) => {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

  const [patients, setPatients] = useState<Patient[]>([]);
  const [vitalsMap, setVitalsMap] = useState<Record<string, VitalEvent>>({});
  const [recentAlerts, setRecentAlerts] = useState<AlertItem[]>([]);
  const [modelName, setModelName] = useState<string>('logistic-regression-v1');

  // Global WebSocket Stream Hook
  const { isConnected, latestEvent } = useWebSocket();

  const dataQualitySummary: DataQualitySummary = {
    overall_quality: 'HIGH',
    artifacts_detected: false,
    active_sensors_count: 6,
    failed_sensors_count: 0,
    last_assessment: 'Active continuous monitoring'
  };

  useEffect(() => {
    let isSubscribed = true;
    // setError reset moved to initialization, no need to call here

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

        const patientResults = await Promise.all(MONITORED_PATIENT_IDS.map(async (id) => {
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
              if (score >= 80) patientObj.risk_level = 'CRITICAL';
              else if (score >= 50) patientObj.risk_level = 'WARNING';
              else if (score >= 30) patientObj.risk_level = 'STABLE';
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

  // Real-Time WebSocket Event Listener for Dashboard Roster Updates
  useEffect(() => {
    if (!latestEvent) return;

    const eventPatientId = latestEvent.patient_id || latestEvent.payload?.patient_id;
    if (!eventPatientId) return;

    const type = latestEvent.type;
    const payload = latestEvent.payload;

    queueMicrotask(() => {
      if (type === 'prediction' && payload) {
        const prob = payload.risk_probability ?? 0;
        const scorePct = prob <= 1.0 ? prob * 100 : prob;

        setPatients(prevList => prevList.map(p => {
          if (p.patient_id === eventPatientId) {
            let rLevel: RiskLevel = 'STABLE';
            if (scorePct >= 80) rLevel = 'CRITICAL';
            else if (scorePct >= 50) rLevel = 'WARNING';
            else if (scorePct >= 30) rLevel = 'STABLE';
            else rLevel = 'LOW';

            return {
              ...p,
              current_risk_score: scorePct,
              risk_level: rLevel,
              risk_trend: scorePct > p.current_risk_score ? 'up' : scorePct < p.current_risk_score ? 'down' : 'stable'
            };
          }
          return p;
        }));

        // Update recent alert if emitted
        if (payload.alert && payload.alert.alert_emitted) {
          const rawSev = (payload.alert_severity || payload.alert.alert_severity || '').toUpperCase();
          let sev: AlertSeverity = 'NONE';
          if (rawSev.includes('RED') || rawSev.includes('URGENT')) sev = 'RED_URGENT';
          else if (rawSev.includes('ORANGE') || rawSev.includes('REVIEW')) sev = 'ORANGE_REVIEW';
          else if (rawSev.includes('YELLOW') || rawSev.includes('WATCH')) sev = 'YELLOW_WATCH';

          const newAlert: AlertItem = {
            alert_id: `ws-alert-${Date.now()}`,
            patient_id: eventPatientId,
            patient_name: `Patient ${eventPatientId}`,
            bed: `Bed ${eventPatientId.slice(-3)}`,
            severity: sev,
            message: payload.alert.message || 'Clinical deterioration alert',
            recommended_action: payload.recommended_clinical_review_level || 'Review telemetry',
            timestamp: payload.prediction_timestamp || latestEvent.occurred_at || new Date().toISOString(),
            status: 'active'
          };

          setRecentAlerts(prev => [newAlert, ...prev.filter(a => a.alert_id !== newAlert.alert_id)]);
        }
      } else if (type === 'alert' && payload) {
        let sev: AlertSeverity = 'NONE';
        const rawSev = (payload.severity || payload.alert_severity || '').toUpperCase();
        if (rawSev.includes('RED') || rawSev.includes('URGENT')) sev = 'RED_URGENT';
        else if (rawSev.includes('ORANGE') || rawSev.includes('REVIEW')) sev = 'ORANGE_REVIEW';
        else if (rawSev.includes('YELLOW') || rawSev.includes('WATCH')) sev = 'YELLOW_WATCH';

        const newAlert: AlertItem = {
          alert_id: `ws-alert-${Date.now()}`,
          patient_id: eventPatientId,
          patient_name: `Patient ${eventPatientId}`,
          bed: `Bed ${eventPatientId.slice(-3)}`,
          severity: sev,
          message: payload.message || 'Clinical deterioration alert',
          recommended_action: 'Bedside evaluation',
          timestamp: latestEvent.occurred_at || new Date().toISOString(),
          status: 'active'
        };

        setRecentAlerts(prev => [newAlert, ...prev]);
      }
    });
  }, [latestEvent]);

  const handleRefresh = () => {
    setRefreshTrigger(prev => prev + 1);
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

  const criticalCount = patients.filter(p => p.risk_level === 'CRITICAL').length;
  const warningCount = patients.filter(p => p.risk_level === 'WARNING').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Stat Cards Row */}
      <div className="grid grid-cols-12">
        <div className="col-span-3">
          <StatCard
            title="Total ICU Bed Roster"
            value={patients.length}
            subtext={`Engine: ${modelName}`}
            icon={<Users size={20} />}
          />
        </div>

        <div className="col-span-3">
          <StatCard
            title="Critical Risk Patients"
            value={criticalCount}
            variant="critical"
            trend="up"
            trendValue="High Sepsis Deterioration"
            icon={<ShieldAlert size={20} color="var(--color-critical)" />}
          />
        </div>

        <div className="col-span-3">
          <StatCard
            title="Warning Patients"
            value={warningCount}
            variant="warning"
            trend="neutral"
            trendValue="Sustained monitoring"
            icon={<Activity size={20} color="var(--color-review)" />}
          />
        </div>

        <div className="col-span-3">
          <StatCard
            title="Active Alerts"
            value={recentAlerts.length}
            variant="critical"
            subtext="Engine: SmartAlertEngine"
            icon={<Heart size={20} color="var(--color-critical)" />}
          />
        </div>
      </div>

      {/* Patient Monitoring Roster & Recent Alerts */}
      <div className="grid grid-cols-12">
        <div className="card col-span-8">
          <div className="card-header">
            <h3 className="card-title">
              <Activity size={18} color="var(--color-info)" /> Real-Time ICU Patient Monitoring Roster
            </h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              {isConnected && (
                <span style={{ fontSize: '0.75rem', color: 'var(--color-stable)', display: 'flex', alignItems: 'center', gap: '0.3rem', backgroundColor: 'rgba(46,204,113,0.1)', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>
                  <Radio size={12} className="animate-pulse" /> WebSocket Live
                </span>
              )}
              <button 
                className="btn btn-outline"
                onClick={handleRefresh}
                style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
              >
                <RefreshCw size={12} /> Refresh REST
              </button>
            </div>
          </div>

          {patients.length > 0 ? (
            <PatientRosterTable
              patients={patients}
              vitalsMap={vitalsMap}
              activePatientId={patients[0]?.patient_id || 'P-ICU-001'}
              onSelectPatient={onSelectPatient}
            />
          ) : (
            <EmptyState message="No ICU Patients Active" subtext="No active patient records retrieved from REST API." />
          )}
        </div>

        <div className="col-span-4" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <ShieldAlert size={18} color="var(--color-critical)" /> Recent Urgent Alerts
              </h3>
            </div>
            {recentAlerts.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {recentAlerts.slice(0, 3).map(alert => (
                  <AlertCard key={alert.alert_id} alert={alert} onSelectPatient={onSelectPatient} />
                ))}
              </div>
            ) : (
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                No active alerts emitted by SmartAlertEngine.
              </p>
            )}
          </div>

          <DataQualityCard dataQuality={dataQualitySummary} />
        </div>
      </div>
    </div>
  );
};
