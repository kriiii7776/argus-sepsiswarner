export type ClockState = 'stopped' | 'running' | 'paused';
export type QualityStatus = 'valid' | 'missing' | 'sensor_unavailable' | 'delayed' | 'stale' | 'invalid' | 'disconnected' | 'reconnected';
export type ScenarioState = 'stable' | 'gradual_deterioration' | 'rapid_deterioration' | 'recovery' | 'noisy' | 'sensor_failure' | 'data_quality_problem';
export type ScenarioEngineState = 'STABLE' | 'EARLY_CHANGE' | 'DETERIORATING' | 'CRITICAL' | 'RECOVERY';

export interface VitalSignSet {
  heart_rate: number | null;
  systolic_bp: number | null;
  diastolic_bp: number | null;
  spo2: number | null;
  temperature: number | null;
  respiratory_rate: number | null;
}

export interface VitalUpdateMessage {
  schema_version: string;
  message_type: 'vital_update';
  patient_id: string;
  session_id: string;
  source: string;
  timestamp: string;
  simulation_time: string;
  vitals: VitalSignSet;
  vital_units: {
    heart_rate: string;
    systolic_bp: string;
    diastolic_bp: string;
    spo2: string;
    temperature: string;
    respiratory_rate: string;
  };
  quality_status: QualityStatus;
  scenario_state: ScenarioState;
}

export interface PatientBaseline {
  heart_rate: number;
  systolic_bp: number;
  diastolic_bp: number;
  spo2: number;
  temperature: number;
  respiratory_rate: number;
}

export interface Patient {
  patient_id: string;
  session_id: string;
  age: number;
  sex: 'M' | 'F' | 'OTHER';
  profile_type: string;
  status: 'active' | 'paused' | 'discharged' | 'inactive';
  baseline: PatientBaseline;
  created_at: string;
  updated_at: string;
}

export interface SimulationClockStatus {
  state: ClockState;
  speed_factor: number;
  wall_clock_time: string;
  simulation_time: string;
  elapsed_sim_seconds: number;
  elapsed_wall_seconds: number;
}

export interface SimulationStatusResponse {
  clock_status: SimulationClockStatus;
  active_session_id: string | null;
  active_patient_id: string | null;
  active_scenario_name: ScenarioState;
  active_scenario_state: ScenarioEngineState;
  registered_patients_count: number;
}

export interface ClinicalContext {
  platelets: number | null;
  bilirubin: number | null;
  creatinine: number | null;
  lactate: number | null;
  pao2_fio2_ratio: number | null;
  glasgow_coma_scale: number | null;
  urine_output_6h: number | null;
  norepinephrine_dose: number | null;
}

export interface ClinicalUpdateMessage {
  message_type: 'clinical_update';
  patient_id: string;
  session_id: string;
  simulation_time: string;
  recorded_at: string;
  clinical_context: ClinicalContext;
  clinical_units: Record<keyof ClinicalContext, string>;
  clinical_observation_times: Partial<Record<keyof ClinicalContext, string | null>>;
  data_origin: string;
}
