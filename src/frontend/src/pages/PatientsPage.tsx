import React, { useState } from 'react';
import { PatientRosterTable } from '../components/patients/PatientRosterTable';
import { MOCK_PATIENTS, MOCK_CURRENT_VITALS } from '../mocks/mockData';
import { Search, Users } from 'lucide-react';


interface Props {
  onSelectPatient: (patient_id: string) => void;
}

export const PatientsPage: React.FC<Props> = ({ onSelectPatient }) => {
  const [filter, setFilter] = useState<'ALL' | 'CRITICAL' | 'WARNING' | 'STABLE'>('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  const filteredPatients = MOCK_PATIENTS.filter(p => {
    const matchesFilter = filter === 'ALL' || p.risk_level === filter;
    const matchesSearch = p.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          p.bed.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          p.patient_id.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Users size={20} color="var(--color-info)" />
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>ICU Patient Roster Directory</h3>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
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
        <PatientRosterTable
          patients={filteredPatients}
          vitalsMap={MOCK_CURRENT_VITALS}
          activePatientId=""
          onSelectPatient={onSelectPatient}
        />
      </div>
    </div>
  );
};
