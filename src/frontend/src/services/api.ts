// ---------------------------------------------------------------------------
// ARGUS Canonical REST API Client (Phase 7B)
// Connected to src/backend FastAPI REST Service
// ---------------------------------------------------------------------------

import type {
  Patient,
  VitalEvent,
  PredictionResponse,
  AlertItem,
  AlertSeverity
} from '../types';

// Environment variable with fallback to canonical Phase 6D backend default
const getInitialBaseUrl = (): string => {
  try {
    if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) {
      return import.meta.env.VITE_API_BASE_URL;
    }
  } catch {
    // Ignore in non-vite test environments
  }
  return 'http://127.0.0.1:8000/api/v1';
};

const API_BASE_URL = getInitialBaseUrl();
const DEFAULT_AUTH_TOKEN = 'argus-auth-admin-001-session-token';

const getInitialToken = (): string => {
  try {
    if (typeof localStorage !== 'undefined') {
      const stored = localStorage.getItem('argus_user_session');
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed && parsed.access_token) {
          return parsed.access_token;
        }
      }
    }
  } catch {
    // Fallback if localStorage unavailable
  }
  return DEFAULT_AUTH_TOKEN;
};

export interface ApiError {
  status: number;
  message: string;
  isAuthError: boolean;
  detail?: any;
}

export class RestApiClient {
  private baseUrl: string;
  private token: string;

  constructor(baseUrl: string = API_BASE_URL, token: string = getInitialToken()) {
    // Strip trailing slash if present
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this.token = token;
  }

  public setToken(token: string): void {
    this.token = token;
  }

  public getBaseUrl(): string {
    return this.baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    requiresAuth: boolean = true
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
    
    const headers: Record<string, string> = {
      'Accept': 'application/json',
      ...(options.headers as Record<string, string> || {})
    };

    if (requiresAuth && this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    if (options.body && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers
      });

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        let errorDetail: any = null;

        try {
          const errorJson = await response.json();
          errorDetail = errorJson;
          if (errorJson.detail) {
            errorMessage = typeof errorJson.detail === 'string' 
              ? errorJson.detail 
              : JSON.stringify(errorJson.detail);
          }
        } catch {
          // If response body is not JSON, use HTTP status text
        }

        const isAuthError = response.status === 401 || response.status === 403;
        
        const apiErr: ApiError = {
          status: response.status,
          message: errorMessage,
          isAuthError,
          detail: errorDetail
        };

        throw apiErr;
      }

      // 204 No Content handling
      if (response.status === 204) {
        return {} as T;
      }

      return await response.json() as T;
    } catch (err: any) {
      // Re-throw if already formatted ApiError
      if (err && typeof err.status === 'number' && typeof err.isAuthError === 'boolean') {
        throw err;
      }

      // Handle network / offline errors
      const networkError: ApiError = {
        status: 0,
        message: err.message || 'Network error: Backend server is unreachable.',
        isAuthError: false
      };
      throw networkError;
    }
  }

  // ---------------------------------------------------------------------------
  // Health & Model Metadata Endpoints
  // ---------------------------------------------------------------------------

  public async getHealth(): Promise<{ status: string }> {
    return this.request<{ status: string }>('/health', { method: 'GET' }, false);
  }

  public async getModelVersion(): Promise<{
    model_version: string;
    is_demo_model: boolean;
    prediction_horizon_hours: number;
  }> {
    return this.request<{
      model_version: string;
      is_demo_model: boolean;
      prediction_horizon_hours: number;
    }>('/model-version', { method: 'GET' }, false);
  }

  // ---------------------------------------------------------------------------
  // Event Ingestion Endpoint
  // ---------------------------------------------------------------------------

  public async ingestVitals(event: Partial<VitalEvent> & { patient_id: string }): Promise<PredictionResponse> {
    const payload = {
      timestamp: new Date().toISOString(),
      source: 'integration',
      ...event
    };
    return this.request<PredictionResponse>('/events/vitals', {
      method: 'POST',
      body: JSON.stringify(payload)
    }, false);
  }

  // ---------------------------------------------------------------------------
  // Patient Endpoints
  // ---------------------------------------------------------------------------

  public async createPatient(payload: {
    patient_id?: string;
    name?: string;
    age?: number;
    medical_history?: string[];
    source_system?: string;
  }): Promise<Patient> {
    const raw = await this.request<any>('/patients', {
      method: 'POST',
      body: JSON.stringify(payload)
    }, true);

    return this.formatPatientResponse(raw);
  }

  public async getPatients(): Promise<Patient[]> {
    const raw = await this.request<any[]>('/patients', {
      method: 'GET'
    }, true);

    return (Array.isArray(raw) ? raw : []).map(p => this.formatPatientResponse(p));
  }

  public async getPatient(patientId: string): Promise<Patient> {
    const raw = await this.request<any>(`/patients/${encodeURIComponent(patientId)}`, {
      method: 'GET'
    }, true);

    return this.formatPatientResponse(raw);
  }

  public async getVitals(patientId: string): Promise<VitalEvent[]> {
    const raw = await this.request<any[]>(`/patients/${encodeURIComponent(patientId)}/vitals`, {
      method: 'GET'
    }, true);

    return raw.map(v => ({
      patient_id: patientId,
      timestamp: v.timestamp || new Date().toISOString(),
      heart_rate: v.heart_rate ?? null,
      map: v.map ?? null,
      bp_systolic: v.bp_systolic ?? null,
      bp_diastolic: v.bp_diastolic ?? null,
      resp_rate: v.resp_rate ?? null,
      spo2: v.spo2 ?? null,
      temperature_c: v.temperature_c ?? v.temperature ?? null,
      lactate: v.lactate ?? null,
      wbc: v.wbc ?? null,
      platelets: v.platelets ?? null,
      creatinine: v.creatinine ?? null,
      bilirubin: v.bilirubin ?? null,
      pao2_fio2: v.pao2_fio2 ?? null,
      gcs: v.gcs ?? null,
      urine_output: v.urine_output ?? null,
      norepinephrine: v.norepinephrine ?? null,
      source: v.source || 'integration',
      signal_quality: v.signal_quality || 'HIGH'
    }));
  }

  public async getTrajectory(patientId: string): Promise<{
    patient_id: string;
    points: Array<{
      timestamp: string;
      risk_probability: number;
      alert_severity: string | null;
    }>;
  }> {
    return this.request<{
      patient_id: string;
      points: Array<{
        timestamp: string;
        risk_probability: number;
        alert_severity: string | null;
      }>;
    }>(`/patients/${encodeURIComponent(patientId)}/trajectory`, {
      method: 'GET'
    }, true);
  }

  public async getRisk(patientId: string): Promise<{
    patient_id: string;
    risk_score: number;
    risk_level: string;
    factors: string[];
  }> {
    return this.request<{
      patient_id: string;
      risk_score: number;
      risk_level: string;
      factors: string[];
    }>(`/patients/${encodeURIComponent(patientId)}/risk`, {
      method: 'GET'
    }, true);
  }

  public async getExplanation(patientId: string): Promise<{
    patient_id: string;
    feature_importance: Record<string, number>;
    summary: string;
  }> {
    return this.request<{
      patient_id: string;
      feature_importance: Record<string, number>;
      summary: string;
    }>(`/patients/${encodeURIComponent(patientId)}/explanation`, {
      method: 'GET'
    }, true);
  }

  public async getAlerts(patientId: string): Promise<AlertItem[]> {
    const raw = await this.request<any[]>(`/patients/${encodeURIComponent(patientId)}/alerts`, {
      method: 'GET'
    }, true);

    return raw.map((a, idx) => {
      let mappedSeverity: AlertSeverity = 'NONE';
      const sev = (a.severity || '').toUpperCase().replace(/\s+/g, '_');
      if (sev.includes('RED') || sev.includes('URGENT')) mappedSeverity = 'RED_URGENT';
      else if (sev.includes('ORANGE') || sev.includes('REVIEW')) mappedSeverity = 'ORANGE_REVIEW';
      else if (sev.includes('YELLOW') || sev.includes('WATCH')) mappedSeverity = 'YELLOW_WATCH';

      return {
        alert_id: a.alert_id || `alert-${idx}`,
        patient_id: patientId,
        patient_name: `Patient ${patientId}`,
        bed: `Bed ${patientId.slice(-3)}`,
        severity: mappedSeverity,
        message: a.message || 'Clinical deterioration alert',
        recommended_action: a.recommended_action || 'Review vital trajectory and clinical status',
        timestamp: a.timestamp || new Date().toISOString(),
        status: 'active'
      };
    });
  }

  // ---------------------------------------------------------------------------
  // Track B Endpoints & Auth/Preferences
  // ---------------------------------------------------------------------------

  public async login(username: string, password?: string): Promise<{
    access_token: string;
    token_type: string;
    user_id: string;
    name: string;
    role: string;
    assigned_unit: string;
    assigned_patients: string[];
  }> {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    }, false);
  }

  public async getAdminOverview(): Promise<{
    system_health: any;
    metrics: any;
    staff_list: any[];
    patient_assignments: any[];
    registered_devices: any[];
  }> {
    return this.request('/admin/overview', { method: 'GET' }, false);
  }

  public async getStaffPreferences(userId: string): Promise<any> {
    return this.request(`/staff/${encodeURIComponent(userId)}/preferences`, { method: 'GET' }, false);
  }

  public async updateStaffPreferences(userId: string, prefs: any): Promise<any> {
    return this.request(`/staff/${encodeURIComponent(userId)}/preferences`, {
      method: 'POST',
      body: JSON.stringify(prefs)
    }, false);
  }

  public async getIcuOverview(): Promise<{
    total_patients: number;
    active_patients: number;
    watch_count: number;
    review_count: number;
    urgent_count: number;
    recent_emergency_alerts: Array<any>;
  }> {
    return this.request('/icu/overview', { method: 'GET' }, false);
  }

  public async acknowledgeAlert(alertId: string, userId: string = 'USER-001'): Promise<any> {
    return this.request(`/alerts/${encodeURIComponent(alertId)}/acknowledge`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId })
    }, false);
  }

  public async getStaff(): Promise<Array<{ user_id: string; name: string; role: string; assigned_unit: string; active: boolean }>> {
    return this.request('/staff', { method: 'GET' }, false);
  }

  // ---------------------------------------------------------------------------
  // Helper Formatter
  // ---------------------------------------------------------------------------

  private formatPatientResponse(raw: any): Patient {
    const id = raw.id || raw.patient_id || 'P-UNKNOWN';
    const name = raw.name || `Patient ${id}`;
    const age = typeof raw.age === 'number' ? raw.age : 50;
    const history = Array.isArray(raw.medical_history) ? raw.medical_history : [];
    
    // Default risk score to 0 until risk endpoint is fetched
    let riskLevel: Patient['risk_level'] = 'STABLE';
    const score = raw.current_risk_score ?? 0;
    if (score >= 0.8) riskLevel = 'CRITICAL';
    else if (score >= 0.5) riskLevel = 'WARNING';
    else if (score >= 0.3) riskLevel = 'STABLE';
    else riskLevel = 'LOW';

    return {
      patient_id: id,
      name,
      bed: raw.bed || `Bed ${id.slice(-3)}`,
      age,
      sex_at_birth: raw.sex_at_birth || 'Unspecified',
      birth_year: raw.birth_year,
      source_system: raw.source_system || 'local',
      medical_history: history,
      admitted_at: raw.created_at || raw.admitted_at || new Date().toISOString(),
      current_risk_score: score,
      risk_level: riskLevel,
      risk_trend: 'stable'
    };
  }
}

export const api = new RestApiClient();
