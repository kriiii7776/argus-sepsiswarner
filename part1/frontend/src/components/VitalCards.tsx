import React from 'react';
import { Heart, Activity, Thermometer, Wind, AlertTriangle, ShieldCheck } from 'lucide-react';
import { VitalUpdateMessage } from '../types';

interface VitalCardsProps {
  latestVitalMsg: VitalUpdateMessage | null;
}

export const VitalCards: React.FC<VitalCardsProps> = ({ latestVitalMsg }) => {
  const vitals = latestVitalMsg?.vitals;
  const quality = latestVitalMsg?.quality_status || 'valid';

  const isSensorFault = ['missing', 'sensor_unavailable', 'disconnected', 'invalid'].includes(quality);

  const getQualityBadge = () => {
    if (quality === 'valid') {
      return (
        <span className="flex items-center gap-1 text-[11px] font-mono font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
          <ShieldCheck className="w-3 h-3" />
          <span>VALID</span>
        </span>
      );
    }
    return (
      <span className="flex items-center gap-1 text-[11px] font-mono font-semibold text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/30 uppercase">
        <AlertTriangle className="w-3 h-3" />
        <span>{quality.replace('_', ' ')}</span>
      </span>
    );
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      
      {/* 1. Heart Rate */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2 shadow-lg">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-1.5 font-medium">
            <Heart className="w-4 h-4 text-rose-500" />
            <span>HEART RATE</span>
          </div>
          <span className="font-mono text-slate-500">bpm</span>
        </div>
        <div className="flex items-baseline justify-between pt-1">
          <div className="text-3xl font-extrabold font-mono tracking-tight text-white">
            {vitals?.heart_rate !== null && vitals?.heart_rate !== undefined ? vitals.heart_rate.toFixed(1) : '--'}
          </div>
          {getQualityBadge()}
        </div>
      </div>

      {/* 2. Blood Pressure (SBP / DBP) */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2 shadow-lg">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-1.5 font-medium">
            <Activity className="w-4 h-4 text-blue-400" />
            <span>BLOOD PRESSURE (SBP/DBP)</span>
          </div>
          <span className="font-mono text-slate-500">mmHg</span>
        </div>
        <div className="flex items-baseline justify-between pt-1">
          <div className="text-3xl font-extrabold font-mono tracking-tight text-white">
            {vitals?.systolic_bp !== null && vitals?.diastolic_bp !== null && vitals?.systolic_bp !== undefined && vitals?.diastolic_bp !== undefined
              ? `${vitals.systolic_bp.toFixed(0)}/${vitals.diastolic_bp.toFixed(0)}`
              : '--/--'}
          </div>
          {getQualityBadge()}
        </div>
      </div>

      {/* 3. SpO2 */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2 shadow-lg">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-1.5 font-medium">
            <Activity className="w-4 h-4 text-cyan-400" />
            <span>OXYGEN SATURATION (SpO₂)</span>
          </div>
          <span className="font-mono text-slate-500">%</span>
        </div>
        <div className="flex items-baseline justify-between pt-1">
          <div className="text-3xl font-extrabold font-mono tracking-tight text-white">
            {vitals?.spo2 !== null && vitals?.spo2 !== undefined ? vitals.spo2.toFixed(1) : '--'}
          </div>
          {getQualityBadge()}
        </div>
      </div>

      {/* 4. Temperature */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2 shadow-lg">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-1.5 font-medium">
            <Thermometer className="w-4 h-4 text-amber-400" />
            <span>TEMPERATURE</span>
          </div>
          <span className="font-mono text-slate-500">°C</span>
        </div>
        <div className="flex items-baseline justify-between pt-1">
          <div className="text-3xl font-extrabold font-mono tracking-tight text-white">
            {vitals?.temperature !== null && vitals?.temperature !== undefined ? vitals.temperature.toFixed(2) : '--'}
          </div>
          {getQualityBadge()}
        </div>
      </div>

      {/* 5. Respiratory Rate */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2 shadow-lg">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-1.5 font-medium">
            <Wind className="w-4 h-4 text-purple-400" />
            <span>RESPIRATORY RATE</span>
          </div>
          <span className="font-mono text-slate-500">breaths/min</span>
        </div>
        <div className="flex items-baseline justify-between pt-1">
          <div className="text-3xl font-extrabold font-mono tracking-tight text-white">
            {vitals?.respiratory_rate !== null && vitals?.respiratory_rate !== undefined ? vitals.respiratory_rate.toFixed(1) : '--'}
          </div>
          {getQualityBadge()}
        </div>
      </div>

    </div>
  );
};
