import React from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import type { ConnectionStatus } from '../../types';


import type { ConnectionLifecycleState } from '../../services/websocket';

interface AppShellProps {
  children: React.ReactNode;
  currentTab: string;
  onNavigate: (tab: string) => void;
  status: ConnectionStatus;
  wsState?: ConnectionLifecycleState;
  activePatientName?: string;
  activeBed?: string;
}

export const AppShell: React.FC<AppShellProps> = ({
  children,
  currentTab,
  onNavigate,
  status,
  wsState,
  activePatientName,
  activeBed
}) => {
  const getTabTitle = () => {
    switch (currentTab) {
      case 'dashboard': return 'ICU Overview Dashboard';
      case 'patients': return 'ICU Patient Roster';
      case 'patient-details': return 'Patient Intensive Monitoring & Explainability';
      case 'alerts': return 'Clinical Alert Center';
      case 'analytics': return 'ICU Analytics & Trends';
      case 'settings': return 'System Settings & Integration';
      default: return 'ARGUS SepsisGuard';
    }
  };

  return (
    <div className="app-shell">
      <Sidebar currentTab={currentTab} onNavigate={onNavigate} status={status} wsState={wsState} />
      <main className="app-main">
        <Header 
          title={getTabTitle()} 
          activePatientName={currentTab === 'patient-details' ? activePatientName : undefined}
          activeBed={currentTab === 'patient-details' ? activeBed : undefined}
        />
        <div className="content-container">
          {children}
        </div>
      </main>
    </div>
  );
};
