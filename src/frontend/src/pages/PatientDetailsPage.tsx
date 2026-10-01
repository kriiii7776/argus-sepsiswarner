import React from 'react';
import { 
  MOCK_PATIENTS, 
  MOCK_CURRENT_VITALS, 
  MOCK_TRAJECTORY_DATA, 
  MOCK_VITAL_TRENDS, 
  MOCK_SHAP_EXPLANATION, 
  MOCK_UNCERTAINTY_SUMMARY,
  MOCK_ALERTS,
  MOCK_DATA_QUALITY
} from '../mocks/mockData';
import { RiskAnalysisCard } from '../components/risk/RiskAnalysisCard';
import { VitalCard } from '../components/vitals/VitalCard';
import { RiskTrajectoryChart } from '../components/risk/RiskTrajectoryChart';
import { ShapExplainabilityCard } from '../components/explainability/ShapExplainabilityCard';
import { UncertaintyCard } from '../components/explainability/UncertaintyCard';
import { DataQualityCard } from '../components/data-quality/DataQualityCard';
import { VitalTrendCharts } from '../components/charts/VitalTrendCharts';
import { AlertCard } from '../components/alerts/AlertCard';
import { Heart, Activity, Thermometer, Wind, Droplets, User, ShieldAlert } from 'lucide-react';
import { Badge } from '../components/common/Badge';

interface Props {
  patientId: string;
}

export const PatientDetailsPage: React.FC<Props> = ({ patientId }) => {
  const patient = MOCK_PATIENTS.find(p => p.patient_id === patientId) || MOCK_PATIENTS[0];
  const vitals = MOCK_CURRENT_VITALS[patient.patient_id] || MOCK_CURRENT_VITALS['P-ICU-001'];
  const patientAlerts = MOCK_ALERTS.filter(a => a.patient_id === patient.patient_id);

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
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
              ID: {patient.patient_id} • Age: {patient.age} yrs • Sex: {patient.sex_at_birth} • Source: {patient.source_system} • History: {patient.medical_history?.join(', ')}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Badge variant="blue">SIRS: {patient.sirs_score}/4</Badge>
          <Badge variant="orange">qSOFA: {patient.qsofa_score}/3</Badge>
          <Badge variant="red">NEWS: {patient.news_score} (HIGH)</Badge>
        </div>
      </div>

      {/* Primary Grid Layout */}
      <div className="grid grid-cols-12">
        {/* Risk Analysis Card */}
        <div className="col-span-4">
          <RiskAnalysisCard patient={patient} />
        </div>

        {/* Current Vitals Grid (6 Vitals) */}
        <div className="col-span-8">
          <div className="grid grid-cols-12">
            <div className="col-span-4">
              <VitalCard
                label="Heart Rate"
                value={vitals.heart_rate}
                unit="bpm"
                icon={<Heart size={16} color="var(--color-critical)" />}
                statusVariant={vitals.heart_rate && vitals.heart_rate > 100 ? 'critical' : 'normal'}
                signalQuality={vitals.signal_quality}
              />
            </div>
            <div className="col-span-4">
              <VitalCard
                label="Mean Arterial Pressure"
                value={vitals.map}
                unit="mmHg"
                icon={<Activity size={16} color="var(--color-review)" />}
                statusVariant={vitals.map && vitals.map < 65 ? 'warning' : 'normal'}
                signalQuality={vitals.signal_quality}
              />
            </div>
            <div className="col-span-4">
              <VitalCard
                label="Temperature"
                value={vitals.temperature_c}
                unit="°C"
                icon={<Thermometer size={16} color="var(--color-watch)" />}
                statusVariant={vitals.temperature_c && vitals.temperature_c > 38.3 ? 'critical' : 'normal'}
                signalQuality={vitals.signal_quality}
              />
            </div>
            <div className="col-span-4">
              <VitalCard
                label="SpO2 Saturation"
                value={vitals.spo2}
                unit="%"
                icon={<Wind size={16} color="var(--color-info)" />}
                statusVariant={vitals.spo2 && vitals.spo2 < 94 ? 'warning' : 'normal'}
                signalQuality={vitals.signal_quality}
              />
            </div>
            <div className="col-span-4">
              <VitalCard
                label="Respiratory Rate"
                value={vitals.resp_rate}
                unit="bpm"
                icon={<Activity size={16} />}
                statusVariant={vitals.resp_rate && vitals.resp_rate > 22 ? 'warning' : 'normal'}
                signalQuality={vitals.signal_quality}
              />
            </div>
            <div className="col-span-4">
              <VitalCard
                label="Serum Lactate"
                value={vitals.lactate}
                unit="mmol/L"
                icon={<Droplets size={16} color="var(--color-critical)" />}
                statusVariant={vitals.lactate && vitals.lactate > 2.0 ? 'critical' : 'normal'}
                signalQuality={vitals.signal_quality}
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
              <Activity size={18} color="var(--color-info)" /> 24-Hour Deterioration Risk Trajectory
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Timestamp-Based Windowing Enabled
            </span>
          </div>
          <RiskTrajectoryChart data={MOCK_TRAJECTORY_DATA} />
        </div>

        <div className="col-span-4" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <ShapExplainabilityCard explanation={MOCK_SHAP_EXPLANATION} />
          <UncertaintyCard summary={MOCK_UNCERTAINTY_SUMMARY} />
        </div>
      </div>

      {/* Vital Trends & Alert History */}
      <div className="grid grid-cols-12">
        <div className="col-span-8">
          <VitalTrendCharts data={MOCK_VITAL_TRENDS} />
        </div>

        <div className="col-span-4" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <ShieldAlert size={18} color="var(--color-critical)" /> Patient Active Alerts
              </h3>
            </div>
            {patientAlerts.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {patientAlerts.map(a => (
                  <AlertCard key={a.alert_id} alert={a} />
                ))}
              </div>
            ) : (
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                No active critical alerts for this patient.
              </p>
            )}
          </div>

          <DataQualityCard dataQuality={MOCK_DATA_QUALITY} />
        </div>
      </div>
    </div>
  );
};
