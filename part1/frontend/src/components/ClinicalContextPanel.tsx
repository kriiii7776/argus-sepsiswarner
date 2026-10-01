import React from 'react';
import { Database, FlaskConical } from 'lucide-react';
import { ClinicalUpdateMessage } from '../types';

const fieldLabels: Array<[keyof ClinicalUpdateMessage['clinical_context'], string]> = [
  ['platelets', 'Platelets'], ['bilirubin', 'Bilirubin'], ['creatinine', 'Creatinine'], ['lactate', 'Lactate'],
  ['pao2_fio2_ratio', 'PaO₂/FiO₂'], ['glasgow_coma_scale', 'GCS'], ['urine_output_6h', 'Urine output'], ['norepinephrine_dose', 'Norepinephrine'],
];

export const ClinicalContextPanel: React.FC<{ clinical: ClinicalUpdateMessage | null }> = ({ clinical }) => (
  <section className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
    <div className="flex items-start justify-between gap-4 border-b border-slate-800 pb-3 mb-4">
      <div className="flex items-center gap-2">
        <Database className="w-4 h-4 text-violet-400" />
        <div>
          <h2 className="text-sm font-semibold text-slate-200">CLINICAL CONTEXT — EHR / LAB REPLAY</h2>
          <p className="text-xs text-slate-500 mt-0.5">Recorded MIMIC-IV observations only. Missing source measurements remain unavailable; no random imputation.</p>
        </div>
      </div>
      <div className="flex items-center gap-1.5 text-[10px] font-mono text-violet-300 bg-violet-500/10 border border-violet-500/30 px-2 py-1 rounded">
        <FlaskConical className="w-3 h-3" /> {clinical?.data_origin || 'awaiting replay'}
      </div>
    </div>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {fieldLabels.map(([field, label]) => {
        const value = clinical?.clinical_context[field];
        const unavailableReason: Partial<Record<keyof ClinicalUpdateMessage['clinical_context'], string>> = {
          pao2_fio2_ratio: 'No matched PaO₂ / FiO₂ record',
          glasgow_coma_scale: 'No concurrent GCS components',
          urine_output_6h: 'No recorded output in window',
          norepinephrine_dose: 'No recorded infusion',
        };
        const noRecordedNorepinephrine = field === 'norepinephrine_dose' && value === null;
        return <div key={field} className="bg-slate-950 border border-slate-800 rounded-lg p-3">
          <div className="text-[11px] text-slate-400">{label}</div>
          <div className={`font-mono ${noRecordedNorepinephrine ? 'text-xs text-amber-300 pt-1.5' : 'text-lg text-slate-100 mt-1'} font-bold`}>
            {noRecordedNorepinephrine ? 'NO RECORDED INFUSION' : value ?? '--'}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">{clinical?.clinical_units[field] || ''}</div>
          <div className="text-[9px] text-slate-600 mt-1">{clinical?.clinical_observation_times[field] ? `Recorded ${new Date(clinical.clinical_observation_times[field]!).toLocaleTimeString()}` : unavailableReason[field] || 'No source record'}</div>
        </div>;
      })}
    </div>
  </section>
);
