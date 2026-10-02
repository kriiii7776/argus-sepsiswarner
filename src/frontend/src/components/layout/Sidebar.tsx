import React from 'react';
import { 
  ActivitySquare, 
  LayoutDashboard, 
  Users, 
  ShieldAlert, 
  BarChart3, 
  Settings,
  UserCheck
} from 'lucide-react';
import { ConnectionStatus } from '../common/ConnectionStatus';
import type { ConnectionStatus as ConnectionStatusType } from '../../types';


import type { ConnectionLifecycleState } from '../../services/websocket';

import { useAuth } from '../../contexts/AuthContext';
import { ShieldCheck } from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onNavigate: (tab: string) => void;
  status: ConnectionStatusType;
  wsState?: ConnectionLifecycleState;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onNavigate, status, wsState }) => {
  const { user } = useAuth();
  const role = user?.role || 'DOCTOR';

  const navItems = role === 'ADMIN' ? [
    { id: 'admin', label: 'Admin Console', icon: <ShieldCheck size={18} /> },
    { id: 'settings', label: 'Settings', icon: <Settings size={18} /> },
  ] : [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={18} /> },
    { id: 'patients', label: 'Patients Roster', icon: <Users size={18} /> },
    { id: 'patient-details', label: 'Patient Focus', icon: <UserCheck size={18} /> },
    { id: 'alerts', label: 'Alert Center', icon: <ShieldAlert size={18} /> },
    { id: 'analytics', label: 'Analytics', icon: <BarChart3 size={18} /> },
    { id: 'settings', label: 'Settings', icon: <Settings size={18} /> },
  ];

  return (
    <aside className="app-sidebar">
      <div className="sidebar-header">
        <ActivitySquare size={26} color="var(--color-info)" />
        <div>
          <h1>ARGUS SepsisGuard</h1>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block' }}>AI-Powered ICU Monitoring</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${currentTab === item.id ? 'active' : ''}`}
            onClick={() => onNavigate(item.id)}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div style={{ marginBottom: '0.75rem', fontWeight: 600, textTransform: 'uppercase', fontSize: '0.7rem', letterSpacing: '0.05em' }}>
          System Connection Status
        </div>
        <ConnectionStatus status={status} wsState={wsState} />
      </div>
    </aside>
  );
};
