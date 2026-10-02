import { useAuth } from '../../contexts/AuthContext';
import { User, LogOut, Activity } from 'lucide-react';
import { Badge } from '../common/Badge';

interface HeaderProps {
  title: string;
  activePatientName?: string;
  activeBed?: string;
}

export const Header: React.FC<HeaderProps> = ({ title, activePatientName, activeBed }) => {
  const { user, logout } = useAuth();

  return (
    <header className="app-header">
      <div>
        <h2 className="header-title">{title}</h2>
        {activePatientName && (
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            Selected: <strong>{activeBed}</strong> ({activePatientName})
          </span>
        )}
      </div>

      <div className="header-actions">
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Badge variant={user.role === 'ADMIN' ? 'red' : user.role === 'DOCTOR' ? 'blue' : 'orange'}>
              <User size={12} /> {user.name} ({user.role})
            </Badge>

            <button
              className="btn btn-outline"
              onClick={logout}
              title="Sign Out"
              style={{ padding: '0.35rem 0.6rem', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}
            >
              <LogOut size={14} /> Exit
            </button>
          </div>
        )}

        <Badge variant="blue">
          <Activity size={12} /> MODEL: LOGISTIC-REGRESSION-V1
        </Badge>
      </div>
    </header>
  );
};
