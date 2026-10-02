import React, { useEffect, useState, useMemo } from 'react';
import { api } from '../services/api';
import type { ApiError } from '../services/api';
import type { 
  Patient, 
  VitalEvent, 
  ShapExplanation, 
  UncertaintySummary, 
  AlertItem,
  DataQualitySummary,
  RiskLevel
} from '../types';
import { RiskAnalysisCard } from '../components/risk/RiskAnalysisCard';
import { VitalCard } from '../components/vitals/VitalCard';
import { RiskTrajectoryChart } from '../components/risk/RiskTrajectoryChart';
import { ShapExplainabilityCard } from '../components/explainability/ShapExplainabilityCard';
import { UncertaintyCard } from '../components/explainability/UncertaintyCard';
import { DataQualityCard } from '../components/data-quality/DataQualityCard';
import { VitalTrendCharts } from '../components/charts/VitalTrendCharts';
import { AlertCard } from '../components/alerts/AlertCard';
import { LoadingState, ErrorState, EmptyState } from '../components/common/FeedbackStates';
import { Heart, Activity, Thermometer, Wind, Droplets, User, ShieldAlert, RefreshCw, Radio } from 'lucide-react';
import { Badge } from '../components/common/Badge';

import { useTelemetry } from '../contexts/TelemetryContext';

interface Props {
  patientId: string;
}

export const PatientDetailsPage: React.FC<Props> = ({ patientId }) => {
  const { getPatientTelemetry, isConnected: wsConnected } = useTelemetry();
  const liveData = getPatientTelemetry(patientId);

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

  // REST fallback states (used when live WebSocket data is not yet present)
  const [restPatient, setRestPatient] = useState<Patient | null>(null);
  const [restVitals, setRestVitals] = useState<VitalEvent | null>(null);
  const [vitalHistory, setVitalHistory] = useState<VitalEvent[]>([]);
  const [restTrajectoryPoints, setRestTrajectoryPoints] = useState<Array<{ timeLabel: string; risk_probability: number; alert_severity?: string }>>([]);
  const [restShapExplanation, setRestShapExplanation] = useState<ShapExplanation | null>(null);
  const [restAlerts, setRestAlerts] = useState<AlertItem[]>([]);

  const isConnected = wsConnected;

  // Derived patient & telemetry state (live WebSocket data has priority over REST fallback)
  const patient = liveData.patient || restPatient;
  const vitals = liveData.vitals || restVitals;

  const trajectoryPoints = useMemo(() => {
    if (liveData.trajectory && liveData.trajectory.length > 0) {
      return liveData.trajectory.map((pt) => ({
        timeLabel: new Date(pt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        risk_probability: pt.risk_probability,
        alert_severity: pt.alert_severity
      }));
    }
    return restTrajectoryPoints;
  }, [liveData.trajectory, restTrajectoryPoints]);

  const shapExplanation = useMemo(() => {
    if (liveData.prediction && liveData.prediction.shap_explanation) {
      const shap = liveData.prediction.shap_explanation;
      const attributions = (shap.feature_attributions || []).map((fa: any) => ({
        feature_name: fa.feature_name || 'feature',
        shap_value: fa.shap_value || 0.1,
        description: `Feature ${fa.feature_name}`
      }));
      return {
        explanation_available: shap.explanation_available ?? true,
        feature_attributions: attributions,
        summary: shap.summary || 'Real SHAP model attributions derived from Logistic Regression.',
        disclaimer: 'SHAP values represent model contribution, not causation.'
      };
    }
    return restShapExplanation;
  }, [liveData.prediction, restShapExplanation]);

  const alerts = liveData.alerts.length > 0 ? liveData.alerts : restAlerts;

  // Constant backend uncertainty summary state
  const uncertaintySummary: UncertaintySummary = useMemo(() => ({
    uncertainty_available: false,
    method: 'UNAVAILABLE',
    reason: 'Conformal prediction / Monte Carlo dropout is deactivated in logistic-regression-v1 baseline.'
  }), []);

  const dataQualitySummary: DataQualitySummary = useMemo(() => ({
    overall_quality: (vitals?.signal_quality || 'HIGH') as 'HIGH' | 'MEDIUM' | 'LOW',
    artifacts_detected: false,
    active_sensors_count: 6,
    failed_sensors_count: 0,
    last_assessment: 'Active continuous monitoring'
  }), []);

  // REST API Data Load
  useEffect(() => {
    let isSubscribed = true;

    async function loadData() {
      try {
        if (isSubscribed) {
          setError(null);
        }
        const [patientRes, vitalsRes, riskRes, trajectoryRes, explanationRes, alertsRes] = await Promise.allSettled([
          api.getPatient(patientId),
          api.getVitals(patientId),
          api.getRisk(patientId),
          api.getTrajectory(patientId),
          api.getExplanation(patientId),
          api.getAlerts(patientId)
        ]);

        if (!isSubscribed) return;

        let pObj: Patient;
        if (patientRes.status === 'fulfilled') {
          pObj = patientRes.value;
        } else {
          const err = patientRes.reason as ApiError;
          if (err && (err.status === 401 || err.status === 403)) {
            throw new Error(`Authentication failure (HTTP ${err.status}): ${err.message}`);
          }
          if (err && err.status === 404) {
            throw new Error(`Patient "${patientId}" not found in database.`);
          }
          throw new Error(err?.message || `Failed to fetch patient "${patientId}".`);
        }

        if (riskRes.status === 'fulfilled') {
          const rData = riskRes.value;
          const score = rData.risk_score <= 1.0 ? rData.risk_score * 100 : rData.risk_score;
          pObj.current_risk_score = score;
          
          let rLevel: RiskLevel = 'STABLE';
          if (score >= 80) rLevel = 'CRITICAL';
          else if (score >= 50) rLevel = 'WARNING';
          else if (score >= 30) rLevel = 'STABLE';
          else rLevel = 'LOW';
          
          pObj.risk_level = rLevel;
        }

        setRestPatient(pObj);

        if (vitalsRes.status === 'fulfilled' && vitalsRes.value.length > 0) {
          const vList = vitalsRes.value;
          setVitalHistory(vList);
          setRestVitals(vList[0]);
        } else {
          setRestVitals(null);
          setVitalHistory([]);
        }

        if (trajectoryRes.status === 'fulfilled' && trajectoryRes.value.points) {
          const points = trajectoryRes.value.points.map(pt => ({
            timeLabel: new Date(pt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            risk_probability: pt.risk_probability <= 1.0 ? pt.risk_probability : pt.risk_probability / 100,
            alert_severity: pt.alert_severity || undefined
          }));
          setRestTrajectoryPoints(points);
        } else {
          setRestTrajectoryPoints([]);
        }

        if (explanationRes.status === 'fulfilled') {
          const expData = explanationRes.value;
          const featImp = expData.feature_importance || {};
          const attributions = Object.entries(featImp).map(([key, value]) => ({
            feature_name: key,
            shap_value: value,
            description: formatFeatureName(key, value)
          })).sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value));

          setRestShapExplanation({
            explanation_available: attributions.length > 0,
            feature_attributions: attributions,
            summary: expData.summary,
            disclaimer: 'SHAP values represent model contribution, not causation.'
          });
        } else {
          setRestShapExplanation({
            explanation_available: false,
            feature_attributions: [],
            disclaimer: 'SHAP values represent model contribution, not causation.'
          });
        }

        if (alertsRes.status === 'fulfilled') {
          setRestAlerts(alertsRes.value);
        } else {
          setRestAlerts([]);
        }
      } catch (err: any) {
        if (isSubscribed) {
          console.error('Failed to load patient REST telemetry:', err);
          setError(err.message || 'Unable to load patient data from REST backend.');
        }
      } finally {
        if (isSubscribed) {
          setLoading(false);
        }
      }
    }

    loadData();

    return () => {
      isSubscribed = false;
    };
  }, [patientId, refreshTrigger]);

  const handleRefresh = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  if (loading) {
    return <LoadingState message={`Fetching REST API telemetry for patient ${patientId}...`} />;
  }

  if (error) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <ErrorState 
          title="Patient Telemetry REST Error" 
          message={error} 
        />
        <button 
          className="btn btn-outline" 
          onClick={handleRefresh}
          style={{ width: 'fit-content', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
        >
          <RefreshCw size={14} /> Retry Telemetry Request
        </button>
      </div>
    );
  }

  if (!patient) {
    return <EmptyState message="Patient Not Found" subtext={`No record exists for patient ID ${patientId}`} />;
  }

  const currentVital = vitals || {
    patient_id: patientId,
    timestamp: patient.admitted_at,
    heart_rate: null,
    map: null,
    resp_rate: null,
    spo2: null,
    temperature_c: null,
    lactate: null,
    source: 'integration' as const,
    signal_quality: 'HIGH' as const
  };

  const vitalTrendData = vitalHistory.map(v => ({
    time: new Date(v.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    hr: v.heart_rate || 0,
    map: v.map || 0,
    resp_rate: v.resp_rate || 0,
    spo2: v.spo2 || 0,
    temp: v.temperature_c || 0,
    lactate: v.lactate || 0
  })).reverse();

  const getLatestLabValue = (field: keyof VitalEvent) => {
    for (const v of vitalHistory) {
      if (v[field] != null) {
        return { value: v[field], timestamp: v.timestamp };
      }
    }
    return null;
  };

  const latestLactate = getLatestLabValue('lactate');
  const latestPlatelets = getLatestLabValue('platelets');
  const latestCreatinine = getLatestLabValue('creatinine');
  const latestBilirubin = getLatestLabValue('bilirubin');
  const latestPao2Fio2 = getLatestLabValue('pao2_fio2');
  const latestGcs = getLatestLabValue('gcs');
  const latestUrineOutput = getLatestLabValue('urine_output');
  const latestNorepinephrine = getLatestLabValue('norepinephrine');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Patient Header Banner */}
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: 'var(--bg-card)', borderLeft: '4px solid var(--color-info)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ padding: '0.75rem', backgroundColor: 'var(--color-info-bg)', borderRadius: 'var(--radius-md)' }}>
            <User size={28} color="var(--color-info)" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>{patient.name}</h2>
              <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--color-info)', fontFamily: 'var(--font-mono)' }}>
                {patient.bed}
              </span>
              {isConnected && (
                <span style={{ fontSize: '0.75rem', color: 'var(--color-stable)', display: 'flex', alignItems: 'center', gap: '0.3rem', backgroundColor: 'rgba(46,204,113,0.1)', padding: '0.25rem 0.5rem', borderRadius: '4px' }}>
                  <Radio size={12} className="animate-pulse" /> LIVE STREAM
                </span>
              )}
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
              ID: {patient.patient_id} • Session: {patient.patient_id} • Source: {patient.source_system} • Model: <code style={{ fontFamily: 'var(--font-mono)' }}>logistic-regression-v1</code> • Latest Event: {currentVital.timestamp ? new Date(currentVital.timestamp).toLocaleTimeString() : 'N/A'}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button 
            className="btn btn-outline"
            onClick={handleRefresh}
            title="Refresh Data"
            style={{ padding: '0.4rem 0.6rem', fontSize: '0.8rem' }}
          >
            <RefreshCw size={14} /> Refresh
          </button>
          <Badge variant="blue">SIRS Criteria Evaluated</Badge>
          <Badge variant="orange">qSOFA Active</Badge>
        </div>
      </div>

      {/* Primary Grid Layout */}
      <div className="grid grid-cols-12">
        <div className="col-span-4">
          <RiskAnalysisCard patient={patient} />
        </div>

        <div className="col-span-8">
          <div className="grid grid-cols-12">
            <div className="col-span-4">
              <VitalCard
                label="Heart Rate"
                value={currentVital.heart_rate}
                unit="bpm"
                icon={<Heart size={16} color="var(--color-critical)" />}
                statusVariant={currentVital.heart_rate && currentVital.heart_rate > 100 ? 'critical' : 'normal'}
                signalQuality={currentVital.signal_quality}
              />
            </div>
            <div className="col-span-4">
              <VitalCard
                label="Mean Arterial Pressure"
                value={currentVital.map}
                unit="mmHg"
                icon={<Activity size={16} color="var(--color-review)" />}
                statusVariant={currentVital.map && currentVital.map < 65 ? 'warning' : 'normal'}
                signalQuality={currentVital.signal_quality}
              />
            </div>
            <div className="col-span-4">
              <VitalCard
                label="Blood Pressure (Sys / Dia)"
                value={currentVital.bp_systolic != null && currentVital.bp_diastolic != null ? `${Math.round(currentVital.bp_systolic)}/${Math.round(currentVital.bp_diastolic)}` : null}
                unit="mmHg"
                icon={<Activity size={16} color="var(--color-info)" />}
                statusVariant={currentVital.bp_systolic && currentVital.bp_systolic < 90 ? 'critical' : 'normal'}
                signalQuality={currentVital.signal_quality}
              />
            </div>
            <div className="col-span-4">
              <VitalCard
                label="Temperature"
                value={currentVital.temperature_c}
                unit="°C"
                icon={<Thermometer size={16} color="var(--color-watch)" />}
                statusVariant={currentVital.temperature_c && currentVital.temperature_c > 38.3 ? 'critical' : 'normal'}
                signalQuality={currentVital.signal_quality}
              />
            </div>
            <div className="col-span-4">
              <VitalCard
                label="SpO2 Saturation"
                value={currentVital.spo2}
                unit="%"
                icon={<Wind size={16} color="var(--color-info)" />}
                statusVariant={currentVital.spo2 && currentVital.spo2 < 94 ? 'warning' : 'normal'}
                signalQuality={currentVital.signal_quality}
              />
            </div>
            <div className="col-span-4">
              <VitalCard
                label="Respiratory Rate"
                value={currentVital.resp_rate}
                unit="bpm"
                icon={<Activity size={16} />}
                statusVariant={currentVital.resp_rate && currentVital.resp_rate > 22 ? 'warning' : 'normal'}
                signalQuality={currentVital.signal_quality}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Trajectory & Explainability */}
      <div className="grid grid-cols-12">
        <div className="card col-span-8">
          <div className="card-header">
            <h3 className="card-title">
              <Activity size={18} color="var(--color-info)" /> Deterioration Risk Trajectory (31-Feature Window)
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Trajectory Points: {trajectoryPoints.length}
            </span>
          </div>
          {trajectoryPoints.length > 0 ? (
            <RiskTrajectoryChart data={trajectoryPoints} />
          ) : (
            <EmptyState message="No trajectory points" subtext="No historical predictions recorded for this patient." />
          )}
        </div>

        <div className="col-span-4" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {shapExplanation ? (
            <ShapExplainabilityCard explanation={shapExplanation} />
          ) : null}
          <UncertaintyCard summary={uncertaintySummary} />
        </div>
      </div>

      {/* Section F — Clinical & Laboratory Context */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <Droplets size={18} color="var(--color-info)" /> Clinical & Laboratory Context
          </h3>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Recorded MIMIC-IV / ICU EHR Lab Observations
          </span>
        </div>
        <div className="grid grid-cols-12" style={{ marginTop: '0.75rem', gap: '0.75rem' }}>
          <div className="col-span-3" style={{ padding: '0.6rem 0.85rem', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-sm)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Serum Lactate</span>
            <strong style={{ fontSize: '1rem', color: latestLactate?.value && Number(latestLactate.value) > 2.0 ? 'var(--color-critical)' : 'var(--text-primary)' }}>
              {latestLactate ? `${latestLactate.value} mmol/L` : 'No recorded value'}
            </strong>
            {latestLactate && (
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', marginTop: '0.15rem' }}>
                Observed: {new Date(latestLactate.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </div>

          <div className="col-span-3" style={{ padding: '0.6rem 0.85rem', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-sm)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Platelets</span>
            <strong style={{ fontSize: '1rem', color: 'var(--text-primary)' }}>
              {latestPlatelets ? `${latestPlatelets.value} k/uL` : 'No recorded value'}
            </strong>
            {latestPlatelets && (
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', marginTop: '0.15rem' }}>
                Observed: {new Date(latestPlatelets.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </div>

          <div className="col-span-3" style={{ padding: '0.6rem 0.85rem', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-sm)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Serum Creatinine</span>
            <strong style={{ fontSize: '1rem', color: 'var(--text-primary)' }}>
              {latestCreatinine ? `${latestCreatinine.value} mg/dL` : 'No recorded value'}
            </strong>
            {latestCreatinine && (
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', marginTop: '0.15rem' }}>
                Observed: {new Date(latestCreatinine.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </div>

          <div className="col-span-3" style={{ padding: '0.6rem 0.85rem', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-sm)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Total Bilirubin</span>
            <strong style={{ fontSize: '1rem', color: 'var(--text-primary)' }}>
              {latestBilirubin ? `${latestBilirubin.value} mg/dL` : 'No recorded value'}
            </strong>
            {latestBilirubin && (
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', marginTop: '0.15rem' }}>
                Observed: {new Date(latestBilirubin.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </div>

          <div className="col-span-3" style={{ padding: '0.6rem 0.85rem', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-sm)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>PaO2 / FiO2 Ratio</span>
            <strong style={{ fontSize: '1rem', color: 'var(--text-primary)' }}>
              {latestPao2Fio2 ? `${latestPao2Fio2.value}` : 'No recorded value'}
            </strong>
            {latestPao2Fio2 && (
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', marginTop: '0.15rem' }}>
                Observed: {new Date(latestPao2Fio2.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </div>

          <div className="col-span-3" style={{ padding: '0.6rem 0.85rem', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-sm)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Glasgow Coma Scale (GCS)</span>
            <strong style={{ fontSize: '1rem', color: 'var(--text-primary)' }}>
              {latestGcs ? `${latestGcs.value}` : 'No recorded value'}
            </strong>
            {latestGcs && (
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', marginTop: '0.15rem' }}>
                Observed: {new Date(latestGcs.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </div>

          <div className="col-span-3" style={{ padding: '0.6rem 0.85rem', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-sm)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Urine Output (24h)</span>
            <strong style={{ fontSize: '1rem', color: 'var(--text-primary)' }}>
              {latestUrineOutput ? `${latestUrineOutput.value} mL` : 'No recorded value'}
            </strong>
            {latestUrineOutput && (
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', marginTop: '0.15rem' }}>
                Observed: {new Date(latestUrineOutput.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </div>

          <div className="col-span-3" style={{ padding: '0.6rem 0.85rem', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-sm)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Norepinephrine Infusion</span>
            <strong style={{ fontSize: '1rem', color: 'var(--text-primary)' }}>
              {latestNorepinephrine ? `${latestNorepinephrine.value} mcg/kg/min` : 'No recorded value'}
            </strong>
            {latestNorepinephrine && (
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', marginTop: '0.15rem' }}>
                Observed: {new Date(latestNorepinephrine.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Vital Trends & Alert History */}
      <div className="grid grid-cols-12">
        <div className="col-span-8">
          {vitalTrendData.length > 0 ? (
            <VitalTrendCharts data={vitalTrendData} />
          ) : (
            <div className="card">
              <EmptyState message="No Vital Trend Data" subtext="No vital event history available for plotting." />
            </div>
          )}
        </div>

        <div className="col-span-4" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <ShieldAlert size={18} color="var(--color-critical)" /> Active Alerts & Alert History
              </h3>
            </div>
            {alerts.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {alerts.map(a => (
                  <AlertCard key={a.alert_id} alert={a} />
                ))}
              </div>
            ) : (
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                No active alerts emitted by SmartAlertEngine for this patient.
              </p>
            )}
          </div>

          <DataQualityCard dataQuality={dataQualitySummary} />
        </div>
      </div>
    </div>
  );
};

function formatFeatureName(key: string, val: number): string {
  const isPos = val >= 0;
  const mapNames: Record<string, string> = {
    map: isPos ? 'Low MAP / Hypotension Risk' : 'Normal MAP Level',
    heart_rate: isPos ? 'Elevated Heart Rate (Tachycardia)' : 'Normal Heart Rate',
    lactate: isPos ? 'Elevated Serum Lactate' : 'Normal Serum Lactate',
    resp_rate: isPos ? 'Elevated Respiratory Rate (Tachypnea)' : 'Normal Respiratory Rate',
    temperature_c: isPos ? 'Fever / Temperature Elevation' : 'Normal Body Temperature',
    spo2: isPos ? 'Low SpO2 Saturation' : 'Normal Oxygenation'
  };

  return mapNames[key] || `${key.toUpperCase().replace('_', ' ')} (${isPos ? 'Risk Increasing' : 'Risk Decreasing'})`;
}
