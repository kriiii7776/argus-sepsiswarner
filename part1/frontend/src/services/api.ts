import { ClinicalUpdateMessage, Patient, SimulationStatusResponse } from '../types';

const API_BASE = '/api/v1';

export async function fetchSimulationStatus(): Promise<SimulationStatusResponse> {
  const res = await fetch(`${API_BASE}/simulation/status`);
  if (!res.ok) throw new Error('Failed to fetch simulation status');
  return res.json();
}

export async function fetchPatients(): Promise<Patient[]> {
  const res = await fetch(`${API_BASE}/patients`);
  if (!res.ok) throw new Error('Failed to fetch patients list');
  return res.json();
}

export async function createPatient(profile_type = 'standard', seed?: number): Promise<Patient> {
  const res = await fetch(`${API_BASE}/patients`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile_type, seed }),
  });
  if (!res.ok) throw new Error('Failed to create patient baseline');
  return res.json();
}

export async function startSimulation(patient_id?: string, speed_factor = 1.0): Promise<SimulationStatusResponse> {
  const res = await fetch(`${API_BASE}/simulation/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ patient_id, speed_factor }),
  });
  if (!res.ok) throw new Error('Failed to start simulation');
  return res.json();
}

export async function pauseSimulation(): Promise<SimulationStatusResponse> {
  const res = await fetch(`${API_BASE}/simulation/pause`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to pause simulation');
  return res.json();
}

export async function resumeSimulation(): Promise<SimulationStatusResponse> {
  const res = await fetch(`${API_BASE}/simulation/resume`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to resume simulation');
  return res.json();
}

export async function stopSimulation(): Promise<SimulationStatusResponse> {
  const res = await fetch(`${API_BASE}/simulation/stop`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to stop simulation');
  return res.json();
}

export async function setSimulationSpeed(speed_factor: number): Promise<SimulationStatusResponse> {
  const res = await fetch(`${API_BASE}/simulation/speed`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ speed_factor }),
  });
  if (!res.ok) throw new Error('Failed to update speed');
  return res.json();
}

export async function setPatientScenario(patient_id: string, scenario_name: string): Promise<SimulationStatusResponse> {
  const res = await fetch(`${API_BASE}/patients/${patient_id}/scenario`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_name }),
  });
  if (!res.ok) throw new Error('Failed to update scenario');
  return res.json();
}

export async function fetchClinicalContext(patient_id: string): Promise<ClinicalUpdateMessage> {
  const res = await fetch(`${API_BASE}/patients/${patient_id}/clinical-context`);
  if (!res.ok) throw new Error('Failed to fetch clinical context');
  return res.json();
}
