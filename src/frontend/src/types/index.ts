// ---------------------------------------------------------------------------
// Canonical Frontend Type Definitions (Phase 7A)
// Aligned with Phase 6D Backend REST & WebSocket Schemas
// ---------------------------------------------------------------------------

export type RiskLevel = 'CRITICAL' | 'WARNING' | 'STABLE' | 'LOW';
export type AlertSeverity = 'RED_URGENT' | 'ORANGE_REVIEW' | 'YELLOW_WATCH' | 'NONE';
export type SignalQuality = 'HIGH' | 'MEDIUM' | 'LOW';
export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export interface Patient {
  patient_id: string;
  name: string;
  bed: string;
  age: number;
  sex_at_birth?: string;
  birth_year?: number;
  source_system: string;
  medical_history?: string[];
  admitted_at: string;
  sirs_score?: number;
  qsofa_score?: number;
  news_score?: number;
  current_risk_score: number;
  risk_level: RiskLevel;
  risk_trend: 'up' | 'down' | 'stable';
  alert_severity?: AlertSeverity;
}

export interface VitalEvent {
  patient_id: string;
  timestamp: string;
  heart_rate: number | null;
  map: number | null;
  bp_systolic?: number | null;
  bp_diastolic?: number | null;
  resp_rate: number | null;
  spo2: number | null;
  temperature_c: number | null;
  lactate: number | null;
  wbc?: number | null;
  platelets?: number | null;
  creatinine?: number | null;
  bilirubin?: number | null;
  pao2_fio2?: number | null;
  gcs?: number | null;
  urine_output?: number | null;
  norepinephrine?: number | null;
  source: 'simulator' | 'integration';
  signal_quality?: SignalQuality;
}

export interface ShapAttribution {
  feature_name: string;
  feature_value?: number;
  shap_value: number;
  direction?: 'positive' | 'negative';
  magnitude?: number;
  description?: string;
}

export interface ShapExplanation {
  explanation_available: boolean;
  base_value?: number;
  feature_attributions: ShapAttribution[];
  summary?: string;
  disclaimer?: string;
}

export interface UncertaintySummary {
  uncertainty_available: boolean;
  method: 'UNAVAILABLE' | 'CONFORMAL' | string;
  reason: string;
  interval_lower?: number | null;
  interval_upper?: number | null;
}

export interface SmartAlertPayload {
  alert_emitted: boolean;
  alert_severity?: AlertSeverity | string;
  recommended_clinical_review_level?: string;
  message?: string;
  reason?: string;
}

export interface PredictionResponse {
  patient_id: string;
  prediction_timestamp: string;
  prediction_horizon_hours: number;
  risk_probability: number;
  uncertainty_interval?: [number, number] | null;
  uncertainty_summary: UncertaintySummary;
  confidence: ConfidenceLevel;
  signal_quality: SignalQuality;
  alert_severity: AlertSeverity | string | null;
  recommended_clinical_review_level: string;
  contributing_factors: string[];
  shap_explanation: ShapExplanation | null;
  alert: SmartAlertPayload | null;
  latency_ms: number;
  model_version: string; // 'logistic-regression-v1'
  is_demo_model: boolean; // false
}

export interface AlertItem {
  alert_id: string;
  patient_id: string;
  patient_name: string;
  bed: string;
  severity: AlertSeverity;
  message: string;
  recommended_action: string;
  timestamp: string;
  status: 'active' | 'closed' | 'suppressed';
}

export interface DataQualitySummary {
  overall_quality: SignalQuality;
  artifacts_detected: boolean;
  active_sensors_count: number;
  failed_sensors_count: number;
  last_assessment: string;
}

export interface WebSocketUpdate {
  type: 'prediction' | 'alert' | 'pong' | 'error';
  occurred_at: string;
  patient_id?: string;
  payload: PredictionResponse | SmartAlertPayload | Record<string, any>;
}

export interface ConnectionStatus {
  backend_connected: boolean;
  websocket_connected: boolean;
  database_status: 'healthy' | 'unhealthy' | 'unknown';
  active_model: string;
}
