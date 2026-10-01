import { useState } from 'react';
import { AppShell } from './components/layout/AppShell';
import { DashboardPage } from './pages/Dashboard';
import { PatientsPage } from './pages/PatientsPage';
import { PatientDetailsPage } from './pages/PatientDetailsPage';
import { AlertsPage } from './pages/AlertsPage';
import { MOCK_PATIENTS, MOCK_SYSTEM_STATUS } from './mocks/mockData';

export default function App() {
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [activePatientId, setActivePatientId] = useState<string>('P-ICU-001');

  const activePatient = MOCK_PATIENTS.find(p => p.patient_id === activePatientId) || MOCK_PATIENTS[0];

  const handleSelectPatient = (id: string) => {
    setActivePatientId(id);
    setCurrentTab('patient-details');
  };

  return (
    <AppShell
      currentTab={currentTab}
      onNavigate={setCurrentTab}
      status={MOCK_SYSTEM_STATUS}
      activePatientName={activePatient.name}
      activeBed={activePatient.bed}
    >
      {currentTab === 'dashboard' && (
        <DashboardPage onSelectPatient={handleSelectPatient} />
      )}

      {currentTab === 'patients' && (
        <PatientsPage onSelectPatient={handleSelectPatient} />
      )}

      {currentTab === 'patient-details' && (
        <PatientDetailsPage patientId={activePatientId} />
      )}

      {currentTab === 'alerts' && (
        <AlertsPage onSelectPatient={handleSelectPatient} />
      )}

      {currentTab === 'analytics' && (
        <div className="card" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>ICU Analytics & Population Health</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
            Population-level sepsis incidence, mean time-to-antibiotics, and alert sensitivity metrics.
          </p>
        </div>
      )}

      {currentTab === 'settings' && (
        <div className="card" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>ARGUS Integration & System Settings</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
            Canonical Backend Endpoint: <code style={{ fontFamily: 'var(--font-mono)' }}>http://localhost:8000/api/v1</code><br />
            WebSocket Stream: <code style={{ fontFamily: 'var(--font-mono)' }}>ws://localhost:8000/api/v1/ws/stream</code><br />
            Baseline Model: <code style={{ fontFamily: 'var(--font-mono)' }}>logistic-regression-v1</code>
          </p>
        </div>
      )}
    </AppShell>
  );
}
