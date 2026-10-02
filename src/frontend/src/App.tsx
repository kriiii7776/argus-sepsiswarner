import { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { TelemetryProvider } from './contexts/TelemetryContext';
import { AppShell } from './components/layout/AppShell';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/Dashboard';
import { PatientsPage } from './pages/PatientsPage';
import { PatientDetailsPage } from './pages/PatientDetailsPage';
import { AlertsPage } from './pages/AlertsPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { AdminPage } from './pages/AdminPage';
import { SettingsPage } from './pages/SettingsPage';
import { api } from './services/api';
import { useWebSocket } from './hooks/useWebSocket';
import type { ConnectionStatus } from './types';

import { ErrorBoundary } from './components/common/ErrorBoundary';

function MainAppContent() {
  const { user, isAuthenticated } = useAuth();
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [activePatientId, setActivePatientId] = useState<string>(() => {
    try {
      return sessionStorage.getItem('argus_active_patient_id') || 'MIMIC-38197705';
    } catch {
      return 'MIMIC-38197705';
    }
  });

  const { connectionState: wsState } = useWebSocket();

  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    backend_connected: false,
    websocket_connected: false,
    database_status: 'unknown',
    active_model: 'logistic-regression-v1'
  });

  // Role routing enforcement
  useEffect(() => {
    if (user?.role === 'ADMIN') {
      if (currentTab !== 'admin' && currentTab !== 'settings') {
        setCurrentTab('admin');
      }
    } else if (user?.role === 'DOCTOR' || user?.role === 'NURSE') {
      if (currentTab === 'admin') {
        setCurrentTab('dashboard');
      }
    }
  }, [user, currentTab]);

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
    try {
      sessionStorage.setItem('argus_active_patient_id', id);
    } catch {
      // Ignore sessionStorage error if unavailable
    }
    setActivePatientId(id);
    setCurrentTab('patient-details');
  };

  const handleLoginSuccess = (role: 'ADMIN' | 'DOCTOR' | 'NURSE') => {
    if (role === 'ADMIN') {
      setCurrentTab('admin');
    } else {
      setCurrentTab('dashboard');
    }
  };

  if (!isAuthenticated) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  const patientDisplayName = activePatientId.startsWith('MIMIC') ? activePatientId : `Patient ${activePatientId}`;
  const patientBedName = activePatientId.startsWith('MIMIC') ? `ICU-${activePatientId.slice(-4)}` : `Bed ${activePatientId.slice(-3)}`;

  return (
    <AppShell
      currentTab={currentTab}
      onNavigate={setCurrentTab}
      status={connectionStatus}
      wsState={wsState}
      activePatientName={patientDisplayName}
      activeBed={patientBedName}
    >
      {currentTab === 'dashboard' && (
        <DashboardPage onSelectPatient={handleSelectPatient} />
      )}

      {currentTab === 'patients' && (
        <PatientsPage onSelectPatient={handleSelectPatient} />
      )}

      {currentTab === 'patient-details' && (
        <ErrorBoundary fallbackTitle="Patient Focus UI Error" onReset={() => setCurrentTab('patients')}>
          <PatientDetailsPage patientId={activePatientId} />
        </ErrorBoundary>
      )}

      {currentTab === 'alerts' && (
        <AlertsPage onSelectPatient={handleSelectPatient} />
      )}

      {currentTab === 'analytics' && (
        <AnalyticsPage />
      )}

      {currentTab === 'admin' && (
        <AdminPage />
      )}

      {currentTab === 'settings' && (
        <SettingsPage />
      )}
    </AppShell>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <TelemetryProvider>
        <MainAppContent />
      </TelemetryProvider>
    </AuthProvider>
  );
}
