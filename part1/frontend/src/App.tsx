import React, { useEffect, useState } from 'react';
import { Header } from './components/Header';
import { ControlPanel } from './components/ControlPanel';
import { VitalCards } from './components/VitalCards';
import { VitalCharts } from './components/VitalCharts';
import { ClinicalContextPanel } from './components/ClinicalContextPanel';
import { useWebSocket } from './hooks/useWebSocket';
import {
  fetchSimulationStatus,
  fetchPatients,
  startSimulation,
  pauseSimulation,
  resumeSimulation,
  stopSimulation,
  setSimulationSpeed,
  setPatientScenario,
  fetchClinicalContext,
} from './services/api';
import { ClinicalUpdateMessage, Patient, SimulationStatusResponse } from './types';

export function App() {
  const [status, setStatus] = useState<SimulationStatusResponse | null>(null);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string | null>(null);
  const [clinicalContext, setClinicalContext] = useState<ClinicalUpdateMessage | null>(null);

  const activeSessionId = status?.active_session_id || null;
  const { isConnected, latestVitalMsg, history } = useWebSocket(activeSessionId);

  // Poll status & patients every 2 seconds
  const refreshStatus = async () => {
    try {
      const st = await fetchSimulationStatus();
      setStatus(st);
      const pList = await fetchPatients();
      setPatients(pList);
      if (st.active_patient_id) {
        setSelectedPatientId(st.active_patient_id);
      } else if (pList.length > 0 && !selectedPatientId) {
        setSelectedPatientId(pList[0].patient_id);
      }
    } catch (err) {
      console.error('Error refreshing status:', err);
    }
  };

  useEffect(() => {
    refreshStatus();
    const timer = setInterval(refreshStatus, 2000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!selectedPatientId) return;
    const refreshClinical = () => fetchClinicalContext(selectedPatientId).then(setClinicalContext).catch(console.error);
    refreshClinical();
    const timer = setInterval(refreshClinical, 2000);
    return () => clearInterval(timer);
  }, [selectedPatientId]);

  const handleStart = async () => {
    const st = await startSimulation(selectedPatientId || undefined, status?.clock_status.speed_factor || 1.0);
    setStatus(st);
  };

  const handlePause = async () => {
    const st = await pauseSimulation();
    setStatus(st);
  };

  const handleResume = async () => {
    const st = await resumeSimulation();
    setStatus(st);
  };

  const handleStop = async () => {
    const st = await stopSimulation();
    setStatus(st);
  };

  const handleSpeedChange = async (speed: number) => {
    const st = await setSimulationSpeed(speed);
    setStatus(st);
  };

  const handleScenarioChange = async (scenario: string) => {
    if (selectedPatientId) {
      const st = await setPatientScenario(selectedPatientId, scenario);
      setStatus(st);
    }
  };

  const handleSelectPatient = (patientId: string) => {
    setSelectedPatientId(patientId);
  };

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col space-y-6 pb-12">
      <Header status={status} wsConnected={isConnected} />

      <main className="max-w-7xl mx-auto px-6 w-full space-y-6">
        {/* Operator Controls */}
        <ControlPanel
          status={status}
          patients={patients}
          selectedPatientId={selectedPatientId}
          onSelectPatient={handleSelectPatient}
          onStart={handleStart}
          onPause={handlePause}
          onResume={handleResume}
          onStop={handleStop}
          onSpeedChange={handleSpeedChange}
          onScenarioChange={handleScenarioChange}
        />

        {/* Vital Cards Grid */}
        <VitalCards latestVitalMsg={latestVitalMsg} />

        <ClinicalContextPanel clinical={clinicalContext} />

        {/* Real-Time Trajectory Charts */}
        <VitalCharts history={history} />
      </main>
    </div>
  );
}

export default App;
