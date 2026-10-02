import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../services/api';
import { Badge } from '../components/common/Badge';
import { LoadingState } from '../components/common/FeedbackStates';
import { User, Bell, Volume2, Smartphone, ShieldCheck, LogOut, Save, CheckCircle } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const { user, logout } = useAuth();
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const [prefs, setPrefs] = useState({
    clinical_notifications: true,
    urgent_alerts: true,
    review_alerts: true,
    watch_alerts: true,
    sound_enabled: true,
    vibration_enabled: true
  });

  useEffect(() => {
    if (!user) return;
    let isSubscribed = true;

    async function loadPrefs() {
      try {
        const fetched = await api.getStaffPreferences(user!.user_id);
        if (isSubscribed && fetched) {
          setPrefs({
            clinical_notifications: fetched.clinical_notifications ?? true,
            urgent_alerts: fetched.urgent_alerts ?? true,
            review_alerts: fetched.review_alerts ?? true,
            watch_alerts: fetched.watch_alerts ?? true,
            sound_enabled: fetched.sound_enabled ?? true,
            vibration_enabled: fetched.vibration_enabled ?? true
          });
        }
      } catch (e) {
        console.warn('Failed to fetch user preferences:', e);
      } finally {
        if (isSubscribed) setLoading(false);
      }
    }

    loadPrefs();
    return () => { isSubscribed = false; };
  }, [user]);

  const handleToggle = (key: keyof typeof prefs) => {
    setPrefs((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSave = async () => {
    if (!user) return;
    setSaving(true);
    setSuccessMsg(null);
    try {
      await api.updateStaffPreferences(user.user_id, prefs);
      setSuccessMsg('Notification preferences saved and synced to ARGUS backend!');
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: any) {
      console.error('Failed to save preferences:', err);
      setSuccessMsg('Saved locally for current session.');
      setTimeout(() => setSuccessMsg(null), 4000);
    } finally {
      setSaving(false);
    }
  };

  if (!user) return null;

  if (loading) {
    return <LoadingState message="Loading staff user settings & notification preferences..." />;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '800px', margin: '0 auto' }}>
      {/* User Identity Card */}
      <div className="card" style={{ borderLeft: '4px solid var(--color-info)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{
              width: '48px',
              height: '48px',
              borderRadius: '50%',
              backgroundColor: 'rgba(52, 152, 219, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--color-info)'
            }}>
              <User size={24} />
            </div>

            <div>
              <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                {user.name}
              </h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
                User ID: <code style={{ fontFamily: 'var(--font-mono)' }}>{user.user_id}</code> | Unit: <strong>{user.assigned_unit}</strong>
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Badge variant={user.role === 'ADMIN' ? 'red' : user.role === 'DOCTOR' ? 'blue' : 'orange'}>
              {user.role}
            </Badge>
            <button className="btn btn-outline" onClick={logout} style={{ fontSize: '0.8rem', color: 'var(--color-critical)' }}>
              <LogOut size={14} /> Sign Out
            </button>
          </div>
        </div>

        {user.assigned_patients.length > 0 && (
          <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            <strong>Assigned Patients:</strong> {user.assigned_patients.join(', ')}
          </div>
        )}
      </div>

      {/* Notification Preferences Section */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <Bell size={18} color="var(--color-info)" /> Personal Mobile & Desktop Notification Preferences
          </h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            User-specific notification controls (Backend AI risk calculation remains 100% active)
          </span>
        </div>

        {successMsg && (
          <div style={{
            padding: '0.75rem 1rem',
            backgroundColor: 'rgba(46, 204, 113, 0.15)',
            border: '1px solid var(--color-stable)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--color-stable)',
            fontSize: '0.85rem',
            margin: '1rem 0 0.5rem 0',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <CheckCircle size={16} />
            <span>{successMsg}</span>
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
          {/* Main Master Switch */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.85rem 1rem', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-md)' }}>
            <div>
              <strong style={{ fontSize: '0.9rem', color: 'var(--text-primary)', display: 'block' }}>
                Clinical Notifications
              </strong>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Master toggle for mobile notification delivery. Turning OFF silences mobile delivery without disabling backend risk calculation.
              </span>
            </div>
            <input
              type="checkbox"
              checked={prefs.clinical_notifications}
              onChange={() => handleToggle('clinical_notifications')}
              style={{ width: '20px', height: '20px', cursor: 'pointer' }}
            />
          </div>

          {/* Urgent RED */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.85rem 1rem', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-md)', opacity: prefs.clinical_notifications ? 1 : 0.5 }}>
            <div>
              <strong style={{ fontSize: '0.9rem', color: 'var(--color-critical)', display: 'block' }}>
                Urgent RED Alerts (&gt;80% Sepsis Risk)
              </strong>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Emergency clinical deterioration alerts requiring immediate review.
              </span>
            </div>
            <input
              type="checkbox"
              disabled={!prefs.clinical_notifications}
              checked={prefs.urgent_alerts}
              onChange={() => handleToggle('urgent_alerts')}
              style={{ width: '20px', height: '20px', cursor: 'pointer' }}
            />
          </div>

          {/* Review ORANGE */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.85rem 1rem', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-md)', opacity: prefs.clinical_notifications ? 1 : 0.5 }}>
            <div>
              <strong style={{ fontSize: '0.9rem', color: 'var(--color-review)', display: 'block' }}>
                Review ORANGE Alerts (Rapid Risk Escalation)
              </strong>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Elevated sepsis risk shifts or significant vital trend deteriorations.
              </span>
            </div>
            <input
              type="checkbox"
              disabled={!prefs.clinical_notifications}
              checked={prefs.review_alerts}
              onChange={() => handleToggle('review_alerts')}
              style={{ width: '20px', height: '20px', cursor: 'pointer' }}
            />
          </div>

          {/* Watch YELLOW */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.85rem 1rem', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-md)', opacity: prefs.clinical_notifications ? 1 : 0.5 }}>
            <div>
              <strong style={{ fontSize: '0.9rem', color: 'var(--color-watch)', display: 'block' }}>
                Watch YELLOW Alerts (SIRS Criteria Met)
              </strong>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Baseline vital sign shifts meeting SIRS / qSOFA monitoring thresholds.
              </span>
            </div>
            <input
              type="checkbox"
              disabled={!prefs.clinical_notifications}
              checked={prefs.watch_alerts}
              onChange={() => handleToggle('watch_alerts')}
              style={{ width: '20px', height: '20px', cursor: 'pointer' }}
            />
          </div>

          {/* Audio Sound Toggle */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.85rem 1rem', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-md)', opacity: prefs.clinical_notifications ? 1 : 0.5 }}>
            <div>
              <strong style={{ fontSize: '0.9rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Volume2 size={16} /> Notification Sound Channel
              </strong>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Play high-priority clinical audio alert on mobile device upon RED notification.
              </span>
            </div>
            <input
              type="checkbox"
              disabled={!prefs.clinical_notifications}
              checked={prefs.sound_enabled}
              onChange={() => handleToggle('sound_enabled')}
              style={{ width: '20px', height: '20px', cursor: 'pointer' }}
            />
          </div>

          {/* Haptic Vibration Toggle */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.85rem 1rem', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-md)', opacity: prefs.clinical_notifications ? 1 : 0.5 }}>
            <div>
              <strong style={{ fontSize: '0.9rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Smartphone size={16} /> Haptic Device Vibration Pattern
              </strong>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Trigger emergency pulse vibration pattern on mobile handset.
              </span>
            </div>
            <input
              type="checkbox"
              disabled={!prefs.clinical_notifications}
              checked={prefs.vibration_enabled}
              onChange={() => handleToggle('vibration_enabled')}
              style={{ width: '20px', height: '20px', cursor: 'pointer' }}
            />
          </div>

          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={saving}
            style={{
              alignSelf: 'flex-end',
              padding: '0.65rem 1.25rem',
              fontWeight: 700,
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              marginTop: '0.5rem'
            }}
          >
            <Save size={16} /> {saving ? 'Saving...' : 'Save Notification Preferences'}
          </button>
        </div>
      </div>

      {/* System Integration Info Card */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <ShieldCheck size={18} color="var(--color-info)" /> System Integration Details
          </h3>
        </div>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.5rem' }}>
          <div>Backend API Base Endpoint: <code style={{ fontFamily: 'var(--font-mono)' }}>{api.getBaseUrl()}</code></div>
          <div>Active Predictive Model: <code style={{ fontFamily: 'var(--font-mono)' }}>logistic-regression-v1</code></div>
          <div>Canonical Feature Pipeline: <strong>31 Temporal Features (1h/4h rolling windows)</strong></div>
          <div>Clinical Decision Support: <strong>Prototype / Demo System Only</strong></div>
        </div>
      </div>
    </div>
  );
};
