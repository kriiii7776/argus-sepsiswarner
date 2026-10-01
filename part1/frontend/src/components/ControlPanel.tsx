import React from 'react';
import { Play, Pause, Square, Zap, Sliders, Activity } from 'lucide-react';
import { Patient, SimulationStatusResponse } from '../types';

interface ControlPanelProps {
  status: SimulationStatusResponse | null;
  patients: Patient[];
  selectedPatientId: string | null;
  onSelectPatient: (patientId: string) => void;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  onSpeedChange: (speed: number) => void;
  onScenarioChange: (scenario: string) => void;
}

const SPEED_OPTIONS = [1.0, 5.0, 10.0, 30.0, 60.0];
const SCENARIO_OPTIONS = [
  { id: 'stable', label: '1. Stable Equilibrium' },
  { id: 'gradual_deterioration', label: '2. Gradual Deterioration (Primary Demo)' },
  { id: 'rapid_deterioration', label: '3. Rapid Acute Decompensation' },
  { id: 'recovery', label: '4. Recovery Trajectory' },
  { id: 'noisy', label: '5. High Noise Injection' },
  { id: 'sensor_failure', label: '6. Sensor Failure (Lead Disconnect)' },
  { id: 'data_quality_problem', label: '7. Data Quality Intermittent Loss' },
];

const PROFILE_OPTIONS = [
  { id: 'standard', label: 'Standard Baseline' },
  { id: 'athletic', label: 'Athletic Baseline' },
  { id: 'geriatric', label: 'Geriatric Baseline' },
  { id: 'hypertensive', label: 'Hypertensive Baseline' },
  { id: 'icu_baseline', label: 'ICU Critically Ill Baseline' },
];

export const ControlPanel: React.FC<ControlPanelProps> = ({
  status,
  patients,
  selectedPatientId,
  onSelectPatient,
  onStart,
  onPause,
  onResume,
  onStop,
  onSpeedChange,
  onScenarioChange,
}) => {
  const clockState = status?.clock_status.state || 'stopped';
  const currentSpeed = status?.clock_status.speed_factor || 1.0;
  const currentScenario = status?.active_scenario_name || 'stable';
  const enginePhase = status?.active_scenario_state || 'STABLE';

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-6 shadow-xl">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2 text-slate-200 font-semibold text-sm">
          <Sliders className="w-4 h-4 text-blue-400" />
          <span>SIMULATION OPERATOR CONTROLS</span>
        </div>
        <div className="text-xs font-mono text-slate-400">
          Session: <span className="text-blue-400 font-semibold">{status?.active_session_id || 'N/A'}</span>
        </div>
      </div>

      {/* Primary Action Buttons */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <button
          onClick={onStart}
          disabled={clockState === 'running'}
          className={`flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg font-medium text-sm transition-all ${
            clockState === 'running'
              ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700/50'
              : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-900/30'
          }`}
        >
          <Play className="w-4 h-4 fill-current" />
          <span>Start Clock</span>
        </button>

        {clockState === 'running' ? (
          <button
            onClick={onPause}
            className="flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg font-medium text-sm bg-amber-600 hover:bg-amber-500 text-white shadow-lg shadow-amber-900/30 transition-all"
          >
            <Pause className="w-4 h-4 fill-current" />
            <span>Pause Clock</span>
          </button>
        ) : (
          <button
            onClick={onResume}
            disabled={clockState === 'stopped'}
            className={`flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg font-medium text-sm transition-all ${
              clockState === 'stopped'
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700/50'
                : 'bg-amber-600 hover:bg-amber-500 text-white shadow-lg shadow-amber-900/30'
            }`}
          >
            <Play className="w-4 h-4 fill-current" />
            <span>Resume</span>
          </button>
        )}

        <button
          onClick={onStop}
          disabled={clockState === 'stopped'}
          className={`flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg font-medium text-sm transition-all ${
            clockState === 'stopped'
              ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700/50'
              : 'bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-900/30'
          }`}
        >
          <Square className="w-4 h-4 fill-current" />
          <span>Stop</span>
        </button>

        {/* Speed Selector Buttons */}
        <div className="flex items-center justify-between bg-slate-950 p-1 rounded-lg border border-slate-800">
          <div className="flex items-center gap-1 pl-2 text-xs font-mono text-slate-400">
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            <span>Speed:</span>
          </div>
          <div className="flex gap-1">
            {SPEED_OPTIONS.map((speed) => (
              <button
                key={speed}
                onClick={() => onSpeedChange(speed)}
                className={`px-2 py-1 text-xs font-mono rounded font-medium transition-all ${
                  currentSpeed === speed
                    ? 'bg-blue-600 text-white shadow'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {speed}x
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Patient & Scenario Selection */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
        
        {/* Historical MIMIC replay selection */}
        <div className="bg-slate-950 p-4 rounded-lg border border-slate-800/80 space-y-3">
          <div className="flex items-center justify-between text-xs font-medium text-slate-300">
            <span>RECORDED MIMIC-IV ICU STAY</span>
            <span className="text-slate-500 font-mono">({patients.length} Replays)</span>
          </div>
          <div className="flex gap-2">
            <select
              value={selectedPatientId || ''}
              onChange={(e) => onSelectPatient(e.target.value)}
              className="flex-1 bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:outline-none font-mono"
            >
              {patients.map((p) => (
                <option key={p.patient_id} value={p.patient_id}>
                  {p.patient_id} — {p.profile_type.toUpperCase()} ({p.age}y {p.sex})
                </option>
              ))}
            </select>
            
          </div>
        </div>

        {/* Recorded replay intentionally has no synthetic deterioration injection. */}
        <div className="bg-slate-950 p-4 rounded-lg border border-slate-800/80 space-y-3">
          <div className="flex items-center justify-between text-xs font-medium text-slate-300">
            <span>HISTORICAL REPLAY MODE</span>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
              enginePhase === 'CRITICAL'
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                : enginePhase === 'DETERIORATING'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                : 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
            }`}>
              RECORDED MIMIC-IV DEMO
            </span>
          </div>
          <div className="w-full bg-slate-900 border border-slate-700 text-slate-300 text-xs rounded-lg p-2.5 font-mono">
            Original recorded observations only — no generated deterioration.
          </div>
        </div>

      </div>
    </div>
  );
};
