import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';
import type { Patient, VitalEvent, PredictionResponse, AlertItem, AlertSeverity } from '../types';

export interface ActivityFeedItem {
  id: string;
  timestamp: string;
  patient_id: string;
  event_type: string;
  risk_score?: number;
  severity?: string;
  message: string;
}

interface TelemetryContextType {
  patients: Patient[];
  vitalsMap: Record<string, VitalEvent>;
  predictionsMap: Record<string, PredictionResponse>;
  trajectoriesMap: Record<string, Array<{ timestamp: string; risk_probability: number; alert_severity?: string }>>;
  activeAlerts: AlertItem[];
  activityFeed: ActivityFeedItem[];
  lastUpdated: Date;
  isConnected: boolean;
  acknowledgedAlerts: Record<string, string>;
  acknowledgeAlert: (alertId: string, patientId: string) => Promise<void>;
  getPatientTelemetry: (patientId: string) => {
    patient: Patient | null;
    vitals: VitalEvent | null;
    prediction: PredictionResponse | null;
    trajectory: Array<{ timestamp: string; risk_probability: number; alert_severity?: string }>;
    alerts: AlertItem[];
  };
}

const TelemetryContext = createContext<TelemetryContextType | undefined>(undefined);

export const TelemetryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [patientsMap, setPatientsMap] = useState<Record<string, Patient>>({});
  const [vitalsMap, setVitalsMap] = useState<Record<string, VitalEvent>>({});
  const [predictionsMap, setPredictionsMap] = useState<Record<string, PredictionResponse>>({});
  const [trajectoriesMap, setTrajectoriesMap] = useState<Record<string, Array<{ timestamp: string; risk_probability: number; alert_severity?: string }>>>({});
  const [alertsMap, setAlertsMap] = useState<Record<string, AlertItem>>({});
  const [acknowledgedAlerts, setAcknowledgedAlerts] = useState<Record<string, string>>({});
  const [activityFeed, setActivityFeed] = useState<ActivityFeedItem[]>([]);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const { isConnected, latestEvent } = useWebSocket();

  // Load initial REST state on startup
  useEffect(() => {
    let isSubscribed = true;

    async function loadInitialData() {
      try {
        const fetchedPatients = await api.getPatients().catch(() => []);
        if (!isSubscribed) return;

        const results = await Promise.allSettled(
          fetchedPatients.map(async (pObj) => {
            const pid = pObj.patient_id;
            const [vRes, rRes, tRes, aRes] = await Promise.allSettled([
              api.getVitals(pid),
              api.getRisk(pid),
              api.getTrajectory(pid),
              api.getAlerts(pid)
            ]);

            return {
              pid,
              patient: pObj,
              vitals: vRes.status === 'fulfilled' && vRes.value.length > 0 ? vRes.value[vRes.value.length - 1] : null,
              risk: rRes.status === 'fulfilled' ? rRes.value : null,
              trajectory: tRes.status === 'fulfilled' ? tRes.value.points : [],
              alerts: aRes.status === 'fulfilled' ? aRes.value : []
            };
          })
        );

        if (!isSubscribed) return;

        const newPMap: Record<string, Patient> = {};
        const newVMap: Record<string, VitalEvent> = {};
        const newAMap: Record<string, AlertItem> = {};
        const newTMap: Record<string, Array<{ timestamp: string; risk_probability: number; alert_severity?: string }>> = {};

        results.forEach((res) => {
          if (res.status === 'fulfilled') {
            const d = res.value;
            const pid = d.pid;

            const pObj: Patient = { ...d.patient };

            if (d.risk) {
              pObj.current_risk_score = d.risk.risk_score;
              const s = d.risk.risk_score;
              pObj.risk_level = s >= 0.8 ? 'CRITICAL' : s >= 0.5 ? 'WARNING' : s >= 0.3 ? 'STABLE' : 'LOW';
            }

            newPMap[pid] = pObj;
            if (d.vitals) newVMap[pid] = d.vitals;
            if (d.trajectory && d.trajectory.length > 0) {
              newTMap[pid] = d.trajectory.map((pt) => ({
                timestamp: pt.timestamp,
                risk_probability: pt.risk_probability,
                alert_severity: pt.alert_severity || undefined
              }));
            }
            d.alerts.forEach((alt) => {
              newAMap[alt.alert_id] = alt;
            });
          }
        });

        setPatientsMap((prev) => ({ ...prev, ...newPMap }));
        setVitalsMap((prev) => ({ ...prev, ...newVMap }));
        setAlertsMap((prev) => ({ ...prev, ...newAMap }));
        setTrajectoriesMap((prev) => ({ ...prev, ...newTMap }));
        setLastUpdated(new Date());
      } catch (err) {
        console.warn('Initial telemetry load warning:', err);
      }
    }

    loadInitialData();

    return () => {
      isSubscribed = false;
    };
  }, []);

  // Process live WebSocket stream events
  useEffect(() => {
    if (!latestEvent) return;

    const type = latestEvent.type;
    const payload = latestEvent.payload;
    if (!payload) return;

    const eventPatientId = latestEvent.patient_id || payload.patient_id || 'PATIENT-001';
    const tsStr = latestEvent.occurred_at || new Date().toISOString();

    setLastUpdated(new Date());

    if (type === 'vital_event' || type === 'vital_update') {
      const vObj: VitalEvent = {
        patient_id: eventPatientId,
        timestamp: tsStr,
        heart_rate: payload.heart_rate ?? payload.heartRate ?? null,
        map: payload.map ?? null,
        bp_systolic: payload.bp_systolic ?? null,
        bp_diastolic: payload.bp_diastolic ?? null,
        resp_rate: payload.resp_rate ?? payload.respRate ?? null,
        spo2: payload.spo2 ?? null,
        temperature_c: payload.temperature_c ?? payload.temperature ?? null,
        lactate: payload.lactate ?? null,
        source: 'simulator',
        signal_quality: payload.signal_quality || 'HIGH'
      };
      setVitalsMap((prev) => ({ ...prev, [eventPatientId]: vObj }));
    } else if (type === 'prediction') {
      const rawVal = typeof payload.risk_probability === 'number' 
        ? payload.risk_probability 
        : typeof payload.risk_score === 'number'
          ? payload.risk_score
          : 0;

      const riskProb = rawVal > 1.0 ? rawVal / 100 : rawVal;
      const scorePct = rawVal <= 1.0 ? rawVal * 100 : rawVal;

      const rawSev = (payload.alert_severity || payload.alert?.alert_severity || '').toUpperCase();
      let sev: AlertSeverity = 'NONE';
      if (rawSev.includes('RED') || rawSev.includes('URGENT')) sev = 'RED_URGENT';
      else if (rawSev.includes('ORANGE') || rawSev.includes('REVIEW')) sev = 'ORANGE_REVIEW';
      else if (rawSev.includes('YELLOW') || rawSev.includes('WATCH')) sev = 'YELLOW_WATCH';

      let rLevel: Patient['risk_level'] = 'LOW';
      if (riskProb >= 0.8) rLevel = 'CRITICAL';
      else if (riskProb >= 0.5) rLevel = 'WARNING';
      else if (riskProb >= 0.3) rLevel = 'STABLE';

      setPatientsMap((prev) => ({
        ...prev,
        [eventPatientId]: {
          ...(prev[eventPatientId] || {
            patient_id: eventPatientId,
            name: eventPatientId.startsWith('MIMIC') ? eventPatientId : `Patient ${eventPatientId}`,
            bed: eventPatientId.startsWith('MIMIC') ? `ICU-${eventPatientId.slice(-4)}` : `Bed ${eventPatientId.slice(-3)}`,
            age: 50,
            source_system: eventPatientId.startsWith('MIMIC') ? 'MIMIC-IV' : 'local',
            admitted_at: tsStr,
            risk_trend: 'stable'
          }),
          current_risk_score: scorePct,
          risk_level: rLevel
        }
      }));

      const predObj: PredictionResponse = {
        patient_id: eventPatientId,
        prediction_timestamp: tsStr,
        prediction_horizon_hours: 6,
        risk_probability: riskProb,
        confidence: payload.confidence || 'HIGH',
        signal_quality: payload.signal_quality || 'HIGH',
        alert_severity: payload.alert_severity || null,
        recommended_clinical_review_level: payload.recommended_clinical_review_level || 'Routine monitoring',
        contributing_factors: payload.contributing_factors || [],
        shap_explanation: payload.shap_explanation || null,
        latency_ms: payload.latency_ms || 12,
        model_version: payload.model_version || 'logistic-regression-v1',
        is_demo_model: payload.is_demo_model || false,
        uncertainty_summary: payload.uncertainty_summary || null,
        alert: payload.alert || null
      };

      setPredictionsMap((prev) => ({ ...prev, [eventPatientId]: predObj }));

      setTrajectoriesMap((prev) => {
        const existing = prev[eventPatientId] || [];
        const newPt = { timestamp: tsStr, risk_probability: riskProb, alert_severity: sev !== 'NONE' ? sev : undefined };
        return { ...prev, [eventPatientId]: [...existing.slice(-29), newPt] };
      });

      if (sev !== 'NONE') {
        const episodeKey = payload.alert?.alert_id || `alert-${eventPatientId}`;
        setAlertsMap((prev) => {
          const existing = prev[episodeKey];
          return {
            ...prev,
            [episodeKey]: {
              alert_id: episodeKey,
              patient_id: eventPatientId,
              patient_name: eventPatientId.startsWith('MIMIC') ? eventPatientId : `Patient ${eventPatientId}`,
              bed: eventPatientId.startsWith('MIMIC') ? `ICU-${eventPatientId.slice(-4)}` : `Bed ${eventPatientId.slice(-3)}`,
              severity: sev,
              message: payload.alert?.message || existing?.message || 'Clinical deterioration alert',
              recommended_action: payload.recommended_clinical_review_level || existing?.recommended_action || 'Immediate clinical review',
              timestamp: tsStr,
              status: existing?.status || 'active'
            }
          };
        });
      }

      setActivityFeed((prev) => [
        {
          id: `act-${Date.now()}-${Math.random()}`,
          timestamp: tsStr,
          patient_id: eventPatientId,
          event_type: 'prediction',
          risk_score: scorePct,
          severity: sev,
          message: `Risk score updated to ${scorePct.toFixed(1)}% (${rLevel})`
        },
        ...prev.slice(0, 19)
      ]);
    } else if (type === 'alert_acknowledged') {
      const aid = payload.alert_id;
      const ackUser = payload.user_id || 'Staff';
      if (aid) {
        setAcknowledgedAlerts((prev) => ({ ...prev, [aid]: ackUser }));
        setActivityFeed((prev) => [
          {
            id: `act-ack-${Date.now()}`,
            timestamp: tsStr,
            patient_id: eventPatientId,
            event_type: 'acknowledgement',
            message: `Alert ${aid} acknowledged by ${ackUser}`
          },
          ...prev.slice(0, 19)
        ]);
      }
    }
  }, [latestEvent]);

  const acknowledgeAlert = async (alertId: string, _patientId: string) => {
    try {
      await api.acknowledgeAlert(alertId, 'USER-001');
      setAcknowledgedAlerts((prev) => ({ ...prev, [alertId]: 'Dr. Arun (USER-001)' }));
    } catch (e) {
      console.warn('Alert acknowledgement API error:', e);
      setAcknowledgedAlerts((prev) => ({ ...prev, [alertId]: 'Staff Member' }));
    }
  };

  const getPatientTelemetry = (patientId: string) => {
    const patient = patientsMap[patientId] || null;
    const vitals = vitalsMap[patientId] || null;
    const prediction = predictionsMap[patientId] || null;
    const trajectory = trajectoriesMap[patientId] || [];
    const alerts = Object.values(alertsMap).filter((a) => a.patient_id === patientId);

    return { patient, vitals, prediction, trajectory, alerts };
  };

  const allPatientIds = Array.from(
    new Set([
      ...Object.keys(patientsMap),
      ...Object.keys(vitalsMap),
      ...Object.keys(predictionsMap),
      ...Object.keys(trajectoriesMap)
    ])
  );

  const patientsList: Patient[] = allPatientIds.map((pid) => {
    if (patientsMap[pid]) return patientsMap[pid];
    const risk = predictionsMap[pid]?.risk_probability ?? 0;
    return {
      patient_id: pid,
      name: pid.startsWith('MIMIC') ? pid : `Patient ${pid}`,
      bed: pid.startsWith('MIMIC') ? `ICU-${pid.slice(-4)}` : `Bed ${pid.slice(-3)}`,
      age: 50,
      source_system: pid.startsWith('MIMIC') ? 'MIMIC-IV' : 'local',
      admitted_at: new Date().toISOString(),
      current_risk_score: risk,
      risk_level: risk >= 0.8 ? 'CRITICAL' : risk >= 0.5 ? 'WARNING' : risk >= 0.3 ? 'STABLE' : 'LOW',
      risk_trend: 'stable' as const
    };
  });

  const activeAlertsList = Object.values(alertsMap).filter((a) => !acknowledgedAlerts[a.alert_id]);

  return (
    <TelemetryContext.Provider
      value={{
        patients: patientsList,
        vitalsMap,
        predictionsMap,
        trajectoriesMap,
        activeAlerts: activeAlertsList,
        activityFeed,
        lastUpdated,
        isConnected,
        acknowledgedAlerts,
        acknowledgeAlert,
        getPatientTelemetry
      }}
    >
      {children}
    </TelemetryContext.Provider>
  );
};

export const useTelemetry = () => {
  const context = useContext(TelemetryContext);
  if (!context) {
    throw new Error('useTelemetry must be used within a TelemetryProvider');
  }
  return context;
};
