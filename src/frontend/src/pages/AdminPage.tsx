import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { StatCard } from '../components/common/StatCard';
import { LoadingState, ErrorState } from '../components/common/FeedbackStates';
import { Badge } from '../components/common/Badge';
import { ShieldCheck, Users, Smartphone, HeartPulse, RefreshCw, Activity, CheckCircle } from 'lucide-react';

export const AdminPage: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<any | null>(null);

  const fetchAdminData = async () => {
    setLoading(true);
    setError(null);
    try {
      const overview = await api.getAdminOverview();
      setData(overview);
    } catch (err: any) {
      console.error('Failed to fetch admin overview:', err);
      setError(err.message || 'Failed to load system administrative data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAdminData();
  }, []);

  if (loading) {
    return <LoadingState message="Fetching ARGUS System Administrative Telemetry..." />;
  }

  if (error || !data) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <ErrorState title="Admin Telemetry Error" message={error || 'System data unavailable'} />
        <button className="btn btn-outline" onClick={fetchAdminData} style={{ width: 'fit-content' }}>
          <RefreshCw size={14} /> Retry Telemetry Fetch
        </button>
      </div>
    );
  }

  const { system_health, metrics, staff_list, patient_assignments, registered_devices } = data;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* System Health Top Banner */}
      <div className="card" style={{ borderLeft: '4px solid var(--color-info)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ShieldCheck size={20} color="var(--color-info)" /> System Administrative & Clinical Infrastructure Overview
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
              Active Model: <code style={{ fontFamily: 'var(--font-mono)' }}>{system_health.active_model}</code> | Platform Environment: <strong>Development / Prototype Validation</strong>
            </p>
          </div>

          <button className="btn btn-outline" onClick={fetchAdminData} style={{ fontSize: '0.75rem', padding: '0.4rem 0.75rem' }}>
            <RefreshCw size={12} /> Refresh Infrastructure State
          </button>
        </div>
      </div>

      {/* System Metrics */}
      <div className="grid grid-cols-12">
        <div className="col-span-3">
          <StatCard
            title="ACTIVE STAFF MEMBERS"
            value={metrics.active_staff_count}
            subtitle="Doctors & Nurses"
            icon={<Users size={20} />}
            variant="blue"
          />
        </div>
        <div className="col-span-3">
          <StatCard
            title="REGISTERED DEVICES"
            value={metrics.registered_devices_count}
            subtitle="Mobile & Desktop Terminals"
            icon={<Smartphone size={20} />}
            variant="green"
          />
        </div>
        <div className="col-span-3">
          <StatCard
            title="MONITORED PATIENTS"
            value={metrics.monitored_patients_count}
            subtitle="Care Teams Assigned"
            icon={<HeartPulse size={20} />}
            variant="orange"
          />
        </div>
        <div className="col-span-3">
          <StatCard
            title="TOTAL AI PREDICTIONS"
            value={metrics.total_predictions_generated.toLocaleString()}
            subtitle="Canonical 31-Feature Pipeline"
            icon={<Activity size={20} />}
            variant="purple"
          />
        </div>
      </div>

      {/* Staff Roster Management */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <Users size={18} color="var(--color-info)" /> Clinical Staff Identity & Role Management
          </h3>
        </div>
        <table className="roster-table">
          <thead>
            <tr>
              <th>USER ID</th>
              <th>NAME</th>
              <th>CLINICAL ROLE</th>
              <th>ASSIGNED UNIT</th>
              <th>STATUS</th>
            </tr>
          </thead>
          <tbody>
            {staff_list.map((st: any) => (
              <tr key={st.user_id}>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{st.user_id}</td>
                <td style={{ fontWeight: 600 }}>{st.name}</td>
                <td>
                  <Badge variant={st.role === 'ADMIN' ? 'red' : st.role === 'DOCTOR' ? 'blue' : 'orange'}>
                    {st.role}
                  </Badge>
                </td>
                <td>{st.assigned_unit}</td>
                <td>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', color: st.active ? 'var(--color-stable)' : 'var(--text-muted)', fontSize: '0.8rem', fontWeight: 600 }}>
                    <CheckCircle size={14} /> {st.active ? 'Active' : 'Inactive'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Patient Care-Team Assignments */}
      <div className="grid grid-cols-12">
        <div className="card col-span-6">
          <div className="card-header">
            <h3 className="card-title">
              <HeartPulse size={18} color="var(--color-orange)" /> Patient Care-Team Topology
            </h3>
          </div>
          <table className="roster-table">
            <thead>
              <tr>
                <th>PATIENT ID</th>
                <th>ASSIGNED CLINICAL STAFF</th>
              </tr>
            </thead>
            <tbody>
              {patient_assignments.map((pa: any) => (
                <tr key={pa.patient_id}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{pa.patient_id}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                      {pa.assigned_staff.map((uid: string) => (
                        <Badge key={uid} variant="blue">{uid}</Badge>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Device Registrations */}
        <div className="card col-span-6">
          <div className="card-header">
            <h3 className="card-title">
              <Smartphone size={18} color="var(--color-stable)" /> Registered Mobile & Desktop Terminals
            </h3>
          </div>
          <table className="roster-table">
            <thead>
              <tr>
                <th>DEVICE ID</th>
                <th>STAFF USER</th>
                <th>PLATFORM</th>
                <th>LAST SEEN</th>
              </tr>
            </thead>
            <tbody>
              {registered_devices.map((d: any) => (
                <tr key={d.device_id}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{d.device_id}</td>
                  <td><Badge variant="blue">{d.user_id}</Badge></td>
                  <td style={{ textTransform: 'capitalize' }}>{d.platform}</td>
                  <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {d.last_seen ? new Date(d.last_seen).toLocaleTimeString() : 'N/A'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
