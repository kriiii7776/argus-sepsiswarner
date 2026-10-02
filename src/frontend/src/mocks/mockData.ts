// PHASE 7A UI MOCK DATA - Will be replaced by backend integration in Phase 7B/7C.
// Aligned with Phase 6D backend contracts and canonical model logistic-regression-v1.

import type { 
  Patient, 
  VitalEvent, 
  ShapExplanation, 
  UncertaintySummary, 
  AlertItem, 
  ConnectionStatus,
  DataQualitySummary
} from '../types';


export const MOCK_PATIENTS: Patient[] = [
  {
    patient_id: 'P-ICU-001',
    name: 'Eleanor Vance',
    bed: 'ICU-01',
    age: 67,
    sex_at_birth: 'Female',
    birth_year: 1959,
    source_system: 'EHR-MIMIC-IV',
    medical_history: ['Hypertension', 'Type 2 Diabetes', 'Previous Pneumonia'],
    admitted_at: '2026-09-29T14:30:00Z',
    sirs_score: 3,
    qsofa_score: 2,
    news_score: 8,
    current_risk_score: 87.4,
    risk_level: 'CRITICAL',
    risk_trend: 'up',
    alert_severity: 'RED_URGENT'
  },
  {
    patient_id: 'P-ICU-002',
    name: 'Marcus Brody',
    bed: 'ICU-02',
    age: 72,
    sex_at_birth: 'Male',
    birth_year: 1954,
    source_system: 'EHR-MIMIC-IV',
    medical_history: ['COPD', 'Coronary Artery Disease'],
    admitted_at: '2026-09-30T08:15:00Z',
    sirs_score: 2,
    qsofa_score: 1,
    news_score: 5,
    current_risk_score: 64.2,
    risk_level: 'WARNING',
    risk_trend: 'up',
    alert_severity: 'ORANGE_REVIEW'
  },
  {
    patient_id: 'P-ICU-003',
    name: 'Arthur Pendelton',
    bed: 'ICU-03',
    age: 54,
    sex_at_birth: 'Male',
    birth_year: 1972,
    source_system: 'EHR-MIMIC-IV',
    medical_history: ['Post-Op Appendectomy'],
    admitted_at: '2026-10-01T02:00:00Z',
    sirs_score: 1,
    qsofa_score: 0,
    news_score: 2,
    current_risk_score: 12.1,
    risk_level: 'STABLE',
    risk_trend: 'down',
    alert_severity: 'NONE'
  },
  {
    patient_id: 'P-ICU-004',
    name: 'Sophia Castillo',
    bed: 'ICU-04',
    age: 61,
    sex_at_birth: 'Female',
    birth_year: 1965,
    source_system: 'EHR-MIMIC-IV',
    medical_history: ['Acute Pancreatitis', 'Asthma'],
    admitted_at: '2026-09-30T19:45:00Z',
    sirs_score: 2,
    qsofa_score: 1,
    news_score: 6,
    current_risk_score: 53.8,
    risk_level: 'WARNING',
    risk_trend: 'stable',
    alert_severity: 'YELLOW_WATCH'
  }
];

export const MOCK_CURRENT_VITALS: Record<string, VitalEvent> = {
  'P-ICU-001': {
    patient_id: 'P-ICU-001',
    timestamp: '2026-10-01T22:00:00Z',
    heart_rate: 118.0,
    map: 61.3,
    bp_systolic: 92.0,
    bp_diastolic: 46.0,
    resp_rate: 26.0,
    spo2: 93.0,
    temperature_c: 39.2,
    lactate: 4.2,
    wbc: 18.5,
    source: 'integration',
    signal_quality: 'HIGH'
  },
  'P-ICU-002': {
    patient_id: 'P-ICU-002',
    timestamp: '2026-10-01T22:00:00Z',
    heart_rate: 102.0,
    map: 68.0,
    bp_systolic: 104.0,
    bp_diastolic: 50.0,
    resp_rate: 22.0,
    spo2: 95.0,
    temperature_c: 38.4,
    lactate: 2.6,
    wbc: 14.2,
    source: 'integration',
    signal_quality: 'HIGH'
  },
  'P-ICU-003': {
    patient_id: 'P-ICU-003',
    timestamp: '2026-10-01T22:00:00Z',
    heart_rate: 74.0,
    map: 86.0,
    bp_systolic: 122.0,
    bp_diastolic: 68.0,
    resp_rate: 15.0,
    spo2: 99.0,
    temperature_c: 36.8,
    lactate: 1.1,
    wbc: 7.8,
    source: 'integration',
    signal_quality: 'HIGH'
  },
  'P-ICU-004': {
    patient_id: 'P-ICU-004',
    timestamp: '2026-10-01T22:00:00Z',
    heart_rate: 96.0,
    map: 72.0,
    bp_systolic: 110.0,
    bp_diastolic: 53.0,
    resp_rate: 20.0,
    spo2: 96.0,
    temperature_c: 37.9,
    lactate: 2.1,
    wbc: 12.0,
    source: 'integration',
    signal_quality: 'MEDIUM'
  }
};

export const MOCK_TRAJECTORY_DATA = [
  { timestamp: '00:00', timeLabel: '00:00', risk_probability: 0.18, alert_severity: 'NONE' },
  { timestamp: '04:00', timeLabel: '04:00', risk_probability: 0.24, alert_severity: 'NONE' },
  { timestamp: '08:00', timeLabel: '08:00', risk_probability: 0.38, alert_severity: 'YELLOW_WATCH' },
  { timestamp: '12:00', timeLabel: '12:00', risk_probability: 0.52, alert_severity: 'ORANGE_REVIEW' },
  { timestamp: '16:00', timeLabel: '16:00', risk_probability: 0.69, alert_severity: 'ORANGE_REVIEW' },
  { timestamp: '20:00', timeLabel: '20:00', risk_probability: 0.874, alert_severity: 'RED_URGENT' }
];

export const MOCK_VITAL_TRENDS = [
  { time: '00:00', hr: 82, map: 85, temp: 37.1, spo2: 98, resp: 16, lactate: 1.2 },
  { time: '04:00', hr: 88, map: 80, temp: 37.4, spo2: 97, resp: 18, lactate: 1.5 },
  { time: '08:00', hr: 96, map: 74, temp: 38.0, spo2: 96, resp: 20, lactate: 2.1 },
  { time: '12:00', hr: 104, map: 69, temp: 38.6, spo2: 95, resp: 22, lactate: 2.8 },
  { time: '16:00', hr: 112, map: 64, temp: 39.0, spo2: 94, resp: 24, lactate: 3.5 },
  { time: '20:00', hr: 118, map: 61, temp: 39.2, spo2: 93, resp: 26, lactate: 4.2 }
];

export const MOCK_SHAP_EXPLANATION: ShapExplanation = {
  explanation_available: true,
  base_value: -2.845,
  feature_attributions: [
    { feature_name: 'lactate_curr', feature_value: 4.2, shap_value: 1.452, description: 'Elevated Serum Lactate (4.2 mmol/L)' },
    { feature_name: 'map_min_4h', feature_value: 58.0, shap_value: 1.120, description: 'Hypotension (4h Minimum MAP < 65 mmHg)' },
    { feature_name: 'hr_slope_4h', feature_value: 8.5, shap_value: 0.865, description: 'Tachycardia Acceleration (+8.5 bpm/hr)' },
    { feature_name: 'temp_max_4h', feature_value: 39.2, shap_value: 0.742, description: 'Hyperthermia / Fever (39.2 °C)' },
    { feature_name: 'rr_curr', feature_value: 26.0, shap_value: 0.618, description: 'Tachypnea (26 breaths/min)' },
    { feature_name: 'spo2_curr', feature_value: 93.0, shap_value: 0.431, description: 'Desaturation (93% SpO2)' },
    { feature_name: 'wbc_curr', feature_value: 18.5, shap_value: 0.380, description: 'Leukocytosis (WBC 18.5 x10^9/L)' },
    { feature_name: 'hr_curr', feature_value: 118.0, shap_value: 0.354, description: 'Elevated Heart Rate (118 bpm)' },
    { feature_name: 'shock_index_curr', feature_value: 1.28, shap_value: 0.295, description: 'High Shock Index (HR/SBP = 1.28)' },
    { feature_name: 'sbp_curr', feature_value: 92.0, shap_value: 0.210, description: 'Systolic Blood Pressure Drop (92 mmHg)' }
  ]
};

export const MOCK_UNCERTAINTY_SUMMARY: UncertaintySummary = {
  uncertainty_available: false,
  method: 'UNAVAILABLE',
  reason: 'Conformal prediction runtime not configured for baseline model (logistic-regression-v1)'
};

export const MOCK_ALERTS: AlertItem[] = [
  {
    alert_id: 'ALT-1001',
    patient_id: 'P-ICU-001',
    patient_name: 'Eleanor Vance',
    bed: 'ICU-01',
    severity: 'RED_URGENT',
    message: 'High Sepsis Risk (>80%) sustained for >1 hour. Refractory hypotension detected.',
    recommended_action: 'Immediate Senior Clinician Review. Prepare IV Fluid Resuscitation & Blood Cultures.',
    timestamp: '2026-10-01T21:45:00Z',
    status: 'active'
  },
  {
    alert_id: 'ALT-1002',
    patient_id: 'P-ICU-002',
    patient_name: 'Marcus Brody',
    bed: 'ICU-02',
    severity: 'ORANGE_REVIEW',
    message: 'Deteriorating Trajectory (+18%/hr). MAP < 65 mmHg & rising lactate.',
    recommended_action: 'Perform Clinical Review. Order Repeat Lactate & Arterial Blood Gas.',
    timestamp: '2026-10-01T21:15:00Z',
    status: 'active'
  },
  {
    alert_id: 'ALT-1003',
    patient_id: 'P-ICU-004',
    patient_name: 'Sophia Castillo',
    bed: 'ICU-04',
    severity: 'YELLOW_WATCH',
    message: 'SIRS criteria met (Temp 37.9°C, HR 96 bpm). Risk score 53.8%.',
    recommended_action: 'Increase Vitals Monitoring Frequency to q15m.',
    timestamp: '2026-10-01T20:30:00Z',
    status: 'active'
  }
];

export const MOCK_SYSTEM_STATUS: ConnectionStatus = {
  backend_connected: true,
  websocket_connected: true,
  database_status: 'healthy',
  active_model: 'logistic-regression-v1'
};

export const MOCK_DATA_QUALITY: DataQualitySummary = {
  overall_quality: 'HIGH',
  artifacts_detected: false,
  active_sensors_count: 6,
  failed_sensors_count: 0,
  last_assessment: '2026-10-01T22:00:00Z'
};
