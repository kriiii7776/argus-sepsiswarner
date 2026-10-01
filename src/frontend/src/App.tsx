import { useState, useEffect } from 'react';
import { AppShell } from './components/layout/AppShell';
import { DashboardPage } from './pages/Dashboard';
import { PatientsPage } from './pages/PatientsPage';
import { PatientDetailsPage } from './pages/PatientDetailsPage';
import { AlertsPage } from './pages/AlertsPage';
import { api } from './services/api';
import { wsService } from './services/websocket';
import { useWebSocket } from './hooks/useWebSocket';
import type { ConnectionStatus } from './types';

export default function App() {
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [activePatientId, setActivePatientId] = useState<string>('P-ICU-001');

  // Real-Time WebSocket Hook
  const { connectionState: wsState } = useWebSocket();

  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    backend_connected: false,
    websocket_connected: false,
    database_status: 'unknown',
    active_model: 'logistic-regression-v1'
  });

  useEffect(() => {
    let isMounted = true;

    async function checkBackendStatus() {
      try {
        const [healthRes, modelRes] = await Promise.allSettled([
          api.getHealth(),
          api.getModelVersion()
        ]);

        if (!isMounted) return;

        const isBackendUp = healthRes.status === 'fulfilled' && healthRes.value.status === 'healthy';
        const dbStatus = isBackendUp ? 'healthy' : 'unhealthy';
        let modelName = 'logistic-regression-v1';

        if (modelRes.status === 'fulfilled' && modelRes.value.model_version) {
          modelName = modelRes.value.model_version;
        }

        setConnectionStatus({
          backend_connected: isBackendUp,
          websocket_connected: wsState === 'CONNECTED',
          database_status: dbStatus,
          active_model: modelName
        });
      } catch {
        if (isMounted) {
          setConnectionStatus({
            backend_connected: false,
            websocket_connected: wsState === 'CONNECTED',
            database_status: 'unhealthy',
            active_model: 'logistic-regression-v1'
          });
        }
      }
    }

    checkBackendStatus();
    const timer = setInterval(checkBackendStatus, 15000);
    return () => {
      isMounted = false;
      clearInterval(timer);
    };
  }, [wsState]);

  const handleSelectPatient = (id: string) => {
    setActivePatientId(id);
    setCurrentTab('patient-details');
  };

  return (
    <AppShell
      currentTab={currentTab}
      onNavigate={setCurrentTab}
      status={connectionStatus}
      wsState={wsState}
      activePatientName={`Patient ${activePatientId}`}
      activeBed={`Bed ${activePatientId.slice(-3)}`}
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
            Canonical Backend Base URL: <code style={{ fontFamily: 'var(--font-mono)' }}>{api.getBaseUrl()}</code><br />
            WebSocket Stream URL: <code style={{ fontFamily: 'var(--font-mono)' }}>{wsService.getUrl()}</code><br />
            WebSocket Status: <strong style={{ color: wsState === 'CONNECTED' ? 'var(--color-stable)' : 'var(--color-watch)' }}>
              {wsState}
            </strong><br />
            Auth Protocol: <code style={{ fontFamily: 'var(--font-mono)' }}>Bearer Token (fake-super-secret-token)</code><br />
            Active ML Model: <code style={{ fontFamily: 'var(--font-mono)' }}>{connectionStatus.active_model}</code><br />
            Backend API Health: <strong style={{ color: connectionStatus.backend_connected ? 'var(--color-stable)' : 'var(--color-critical)' }}>
              {connectionStatus.backend_connected ? 'Online (HTTP 200)' : 'Offline'}
            </strong>
          </p>
        </div>
      )}
    </AppShell>
  );
}
