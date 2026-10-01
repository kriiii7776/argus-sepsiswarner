import React from 'react';
import { StatCard } from '../components/common/StatCard';
import { PatientRosterTable } from '../components/patients/PatientRosterTable';
import { AlertCard } from '../components/alerts/AlertCard';
import { DataQualityCard } from '../components/data-quality/DataQualityCard';
import { 
  MOCK_PATIENTS, 
  MOCK_CURRENT_VITALS, 
  MOCK_ALERTS, 
  MOCK_DATA_QUALITY 
} from '../mocks/mockData';
import { Users, ShieldAlert, Activity, Heart } from 'lucide-react';

interface Props {
  onSelectPatient: (patient_id: string) => void;
}

export const DashboardPage: React.FC<Props> = ({ onSelectPatient }) => {
  const criticalCount = MOCK_PATIENTS.filter(p => p.risk_level === 'CRITICAL').length;
  const warningCount = MOCK_PATIENTS.filter(p => p.risk_level === 'WARNING').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Stat Cards Row */}
      <div className="grid grid-cols-12">
        <div className="col-span-3">
          <StatCard
            title="Total ICU Bed Roster"
            value={MOCK_PATIENTS.length}
            subtext="All beds monitored continuously"
            icon={<Users size={20} />}
          />
        </div>

        <div className="col-span-3">
          <StatCard
            title="Critical Risk Patients"
            value={criticalCount}
            variant="critical"
            trend="up"
            trendValue="+1 vs 4h ago"
            icon={<ShieldAlert size={20} color="var(--color-critical)" />}
          />
        </div>

        <div className="col-span-3">
          <StatCard
            title="Warning Patients"
            value={warningCount}
            variant="warning"
            trend="neutral"
            trendValue="Sustained monitoring"
            icon={<Activity size={20} color="var(--color-review)" />}
          />

        </div>

        <div className="col-span-3">
          <StatCard
            title="Active Alerts"
            value={MOCK_ALERTS.length}
            variant="critical"
            subtext="3 Requires Action"
            icon={<Heart size={20} color="var(--color-critical)" />}
          />
        </div>
      </div>

      {/* Patient Monitoring Roster & Recent Alerts */}
      <div className="grid grid-cols-12">
        <div className="card col-span-8">
          <div className="card-header">
            <h3 className="card-title">
              <Activity size={18} color="var(--color-info)" /> Real-Time ICU Patient Monitoring Roster
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Auto-refreshed via WebSocket
            </span>
          </div>

          <PatientRosterTable
            patients={MOCK_PATIENTS}
            vitalsMap={MOCK_CURRENT_VITALS}
            activePatientId="P-ICU-001"
            onSelectPatient={onSelectPatient}
          />
        </div>

        <div className="col-span-4" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <ShieldAlert size={18} color="var(--color-critical)" /> Recent Urgent Alerts
              </h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {MOCK_ALERTS.slice(0, 2).map(alert => (
                <AlertCard key={alert.alert_id} alert={alert} onSelectPatient={onSelectPatient} />
              ))}
            </div>
          </div>

          <DataQualityCard dataQuality={MOCK_DATA_QUALITY} />
        </div>
      </div>
    </div>
  );
};
