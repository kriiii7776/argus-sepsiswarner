import React, { useState, useEffect } from 'react';
import { AlertCard } from '../components/alerts/AlertCard';
import { LoadingState, ErrorState, EmptyState } from '../components/common/FeedbackStates';
import { api } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';
import type { AlertItem, AlertSeverity } from '../types';
import { ShieldAlert, RefreshCw, Radio } from 'lucide-react';

interface Props {
  onSelectPatient: (patient_id: string) => void;
}

const MONITORED_PATIENT_IDS = ['P-ICU-001', 'P-ICU-002', 'P-ICU-003', 'P-ICU-004', 'P-ICU-005'];

export const AlertsPage: React.FC<Props> = ({ onSelectPatient }) => {
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);

  // Global WebSocket Stream Hook
  const { isConnected, latestEvent } = useWebSocket();

  useEffect(() => {
    let isSubscribed = true;

    async function fetchAlerts() {
      try {
        if (isSubscribed) {
          setError(null);
        }
        const alertPromises = MONITORED_PATIENT_IDS.map(id => api.getAlerts(id).catch(err => {
          console.warn(`Failed to fetch alerts for ${id}:`, err);
          return [] as AlertItem[];
        }));

        const results = await Promise.all(alertPromises);
        if (!isSubscribed) return;

        const combined = results.flat();
        setAlerts(combined);
      } catch (err: any) {
        if (isSubscribed) {
          console.error('Failed to fetch REST alerts:', err);
          setError(err.message || 'Failed to fetch alerts from backend service.');
        }
      } finally {
        if (isSubscribed) {
          setLoading(false);
        }
      }
    }

    fetchAlerts();

    return () => {
      isSubscribed = false;
    };
  }, [refreshTrigger]);

  // Handle Real-Time WebSocket Alerts from SmartAlertEngine
  useEffect(() => {
    if (!latestEvent) return;

    const type = latestEvent.type;
    const payload = latestEvent.payload;
    const patientId = latestEvent.patient_id || payload?.patient_id || 'P-UNKNOWN';

    queueMicrotask(() => {
      if (type === 'alert' && payload) {
        let sev: AlertSeverity = 'NONE';
        const rawSev = (payload.severity || payload.alert_severity || '').toUpperCase();
        if (rawSev.includes('RED') || rawSev.includes('URGENT')) sev = 'RED_URGENT';
        else if (rawSev.includes('ORANGE') || rawSev.includes('REVIEW')) sev = 'ORANGE_REVIEW';
        else if (rawSev.includes('YELLOW') || rawSev.includes('WATCH')) sev = 'YELLOW_WATCH';

        const newAlert: AlertItem = {
          alert_id: `ws-alert-${Date.now()}`,
          patient_id: patientId,
          patient_name: `Patient ${patientId}`,
          bed: `Bed ${patientId.slice(-3)}`,
          severity: sev,
          message: payload.message || 'Clinical deterioration alert emitted',
          recommended_action: 'Bedside clinical review',
          timestamp: latestEvent.occurred_at || new Date().toISOString(),
          status: 'active'
        };

        setAlerts(prev => [newAlert, ...prev.filter(a => a.alert_id !== newAlert.alert_id)]);
      } else if (type === 'prediction' && payload && payload.alert && payload.alert.alert_emitted) {
        let sev: AlertSeverity = 'NONE';
        const rawSev = (payload.alert_severity || payload.alert.alert_severity || '').toUpperCase();
        if (rawSev.includes('RED') || rawSev.includes('URGENT')) sev = 'RED_URGENT';
        else if (rawSev.includes('ORANGE') || rawSev.includes('REVIEW')) sev = 'ORANGE_REVIEW';
        else if (rawSev.includes('YELLOW') || rawSev.includes('WATCH')) sev = 'YELLOW_WATCH';

        const newAlert: AlertItem = {
          alert_id: `ws-alert-${Date.now()}`,
          patient_id: patientId,
          patient_name: `Patient ${patientId}`,
          bed: `Bed ${patientId.slice(-3)}`,
          severity: sev,
          message: payload.alert.message || 'Clinical deterioration alert emitted',
          recommended_action: payload.recommended_clinical_review_level || 'Bedside evaluation',
          timestamp: payload.prediction_timestamp || latestEvent.occurred_at || new Date().toISOString(),
          status: 'active'
        };

        setAlerts(prev => [newAlert, ...prev.filter(a => a.alert_id !== newAlert.alert_id)]);
      }
    });
  }, [latestEvent]);

  const handleRefresh = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  if (loading) {
    return <LoadingState message="Fetching clinical alerts from SmartAlertEngine..." />;
  }

  if (error) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <ErrorState title="Alert Center REST Error" message={error} />
        <button className="btn btn-outline" onClick={handleRefresh} style={{ width: 'fit-content' }}>
          <RefreshCw size={14} /> Retry Request
        </button>
      </div>
    );
  }

  const filteredAlerts = alerts.filter(a => {
    if (filterSeverity === 'ALL') return true;
    return a.severity === filterSeverity;
  });

  const urgentCount = alerts.filter(a => a.severity === 'RED_URGENT').length;
  const reviewCount = alerts.filter(a => a.severity === 'ORANGE_REVIEW').length;
  const watchCount = alerts.filter(a => a.severity === 'YELLOW_WATCH').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Alert Level Summary Banner */}
      <div className="grid grid-cols-12">
        <div className="card col-span-4" style={{ borderLeft: '4px solid var(--color-critical)' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>RED URGENT ALERTS</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--color-critical)', marginTop: '0.2rem' }}>
            {urgentCount}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>High Sepsis Risk (&gt;80%) / Refractory Hypotension</span>
        </div>

        <div className="card col-span-4" style={{ borderLeft: '4px solid var(--color-review)' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>ORANGE REVIEW ALERTS</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--color-review)', marginTop: '0.2rem' }}>
            {reviewCount}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Rapid Risk Deterioration (+15%/hr)</span>
        </div>

        <div className="card col-span-4" style={{ borderLeft: '4px solid var(--color-watch)' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>YELLOW WATCH ALERTS</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--color-watch)', marginTop: '0.2rem' }}>
            {watchCount}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>SIRS / qSOFA Criteria Met</span>
        </div>
      </div>

      {/* Filter & List */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <ShieldAlert size={18} color="var(--color-critical)" /> Active ICU Clinical Alert Center
          </h3>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            {isConnected && (
              <span style={{ fontSize: '0.75rem', color: 'var(--color-stable)', display: 'flex', alignItems: 'center', gap: '0.3rem', backgroundColor: 'rgba(46,204,113,0.1)', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>
                <Radio size={12} className="animate-pulse" /> Stream Connected
              </span>
            )}

            <button 
              className="btn btn-outline" 
              onClick={handleRefresh}
              style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
            >
              <RefreshCw size={12} /> Refresh
            </button>

            <div style={{ display: 'flex', gap: '0.35rem' }}>
              {['ALL', 'RED_URGENT', 'ORANGE_REVIEW', 'YELLOW_WATCH'].map(sev => (
                <button
                  key={sev}
                  className={`btn ${filterSeverity === sev ? 'btn-primary' : 'btn-outline'}`}
                  onClick={() => setFilterSeverity(sev)}
                  style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
                >
                  {sev.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>
        </div>

        {filteredAlerts.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
            {filteredAlerts.map(alert => (
              <AlertCard key={alert.alert_id} alert={alert} onSelectPatient={onSelectPatient} />
            ))}
          </div>
        ) : (
          <EmptyState message="No Alerts Active" subtext="No clinical alerts emitted matching the selected filter criteria." />
        )}
      </div>
    </div>
  );
};
