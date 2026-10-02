import React, { useState, useEffect } from 'react';
import { PatientRosterTable } from '../components/patients/PatientRosterTable';
import { api } from '../services/api';
import type { Patient, VitalEvent } from '../types';
import { LoadingState, ErrorState, EmptyState } from '../components/common/FeedbackStates';
import { Search, Users, RefreshCw } from 'lucide-react';

import { useTelemetry } from '../contexts/TelemetryContext';

interface Props {
  onSelectPatient: (patient_id: string) => void;
}

const MONITORED_PATIENT_IDS = ['PATIENT-001', 'PATIENT-002', 'PATIENT-003', 'PATIENT-004'];

export const PatientsPage: React.FC<Props> = ({ onSelectPatient }) => {
  const { patients: contextPatients, vitalsMap: contextVitalsMap } = useTelemetry();
  const [filter, setFilter] = useState<'ALL' | 'CRITICAL' | 'WARNING' | 'STABLE'>('ALL');
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

  const [patients, setPatients] = useState<Patient[]>(contextPatients);
  const [vitalsMap, setVitalsMap] = useState<Record<string, VitalEvent>>(contextVitalsMap);

  useEffect(() => {
    if (contextPatients && contextPatients.length > 0) {
      setPatients(contextPatients);
    }
    if (contextVitalsMap) {
      setVitalsMap(contextVitalsMap);
    }
  }, [contextPatients, contextVitalsMap]);

  useEffect(() => {
    let isSubscribed = true;
    setError(null);

    async function fetchRoster() {
      try {
        const patientIds = Array.from(
          new Set([...MONITORED_PATIENT_IDS, ...contextPatients.map((p) => p.patient_id)])
        );
        const patientPromises = patientIds.map(async (id) => {
          try {
            const [p, riskRes, vitalsRes] = await Promise.allSettled([
              api.getPatient(id),
              api.getRisk(id),
              api.getVitals(id)
            ]);

            const patientObj: Patient = p.status === 'fulfilled' ? p.value : {
              patient_id: id,
              name: `Patient ${id}`,
              bed: `Bed ${id.slice(-3)}`,
              age: 50,
              source_system: 'local',
              admitted_at: new Date().toISOString(),
              current_risk_score: 0,
              risk_level: 'STABLE',
              risk_trend: 'stable'
            };

            if (riskRes.status === 'fulfilled') {
              const score = riskRes.value.risk_score <= 1.0 ? riskRes.value.risk_score * 100 : riskRes.value.risk_score;
              patientObj.current_risk_score = score;
              if (score >= 80) patientObj.risk_level = 'CRITICAL';
              else if (score >= 50) patientObj.risk_level = 'WARNING';
              else if (score >= 30) patientObj.risk_level = 'STABLE';
              else patientObj.risk_level = 'LOW';
            }

            let latestVital: VitalEvent | null = null;
            if (vitalsRes.status === 'fulfilled' && vitalsRes.value.length > 0) {
              latestVital = vitalsRes.value[0];
            }

            return { patientObj, latestVital };
          } catch (e) {
            console.error(`Error fetching patient ${id}:`, e);
            return null;
          }
        });

        const results = await Promise.all(patientPromises);
        if (!isSubscribed) return;

        const validPatients: Patient[] = [];
        const vMap: Record<string, VitalEvent> = {};

        results.forEach(res => {
          if (res) {
            validPatients.push(res.patientObj);
            if (res.latestVital) {
              vMap[res.patientObj.patient_id] = res.latestVital;
            }
          }
        });

        setPatients(validPatients);
        setVitalsMap(vMap);
      } catch (err: any) {
        if (isSubscribed) {
          console.error('Failed to fetch ICU patient roster:', err);
          setError(err.message || 'Failed to communicate with backend REST API.');
        }
      } finally {
        if (isSubscribed) {
          setLoading(false);
        }
      }
    }

    fetchRoster();

    return () => {
      isSubscribed = false;
    };
  }, [refreshTrigger]);

  const handleRefresh = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  const filteredPatients = patients.filter(p => {
    const matchesFilter = filter === 'ALL' || p.risk_level === filter;
    const matchesSearch = p.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          p.bed.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          p.patient_id.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  if (loading) {
    return <LoadingState message="Fetching live ICU patient roster from backend REST API..." />;
  }

  if (error) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <ErrorState title="Patient Directory REST Error" message={error} />
        <button className="btn btn-outline" onClick={handleRefresh} style={{ width: 'fit-content' }}>
          <RefreshCw size={14} /> Retry Request
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Users size={20} color="var(--color-info)" />
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>ICU Patient Roster Directory</h3>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button 
            className="btn btn-outline"
            onClick={handleRefresh}
            style={{ padding: '0.4rem 0.65rem', fontSize: '0.8rem' }}
          >
            <RefreshCw size={14} /> Refresh
          </button>

          {/* Search */}
          <div style={{ position: 'relative', width: '260px' }}>
            <Search size={16} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search by name, bed, ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                width: '100%',
                padding: '0.4rem 0.75rem 0.4rem 2.2rem',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-color)',
                fontSize: '0.85rem',
                outline: 'none'
              }}
            />
          </div>

          {/* Filter buttons */}
          <div style={{ display: 'flex', gap: '0.35rem' }}>
            {(['ALL', 'CRITICAL', 'WARNING', 'STABLE'] as const).map(f => (
              <button
                key={f}
                className={`btn ${filter === f ? 'btn-primary' : 'btn-outline'}`}
                onClick={() => setFilter(f)}
                style={{ padding: '0.35rem 0.7rem', fontSize: '0.8rem' }}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        {filteredPatients.length > 0 ? (
          <PatientRosterTable
            patients={filteredPatients}
            vitalsMap={vitalsMap}
            activePatientId=""
            onSelectPatient={onSelectPatient}
          />
        ) : (
          <EmptyState message="No Matching Patients" subtext="No ICU patient records match the selected filter criteria." />
        )}
      </div>
    </div>
  );
};
