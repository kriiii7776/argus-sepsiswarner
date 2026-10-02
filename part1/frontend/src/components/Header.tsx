import React, { useEffect, useState } from 'react';
import { Activity, Wifi, WifiOff, Clock, Server, ShieldAlert } from 'lucide-react';
import { SimulationStatusResponse } from '../types';

interface HeaderProps {
  status: SimulationStatusResponse | null;
  wsConnected: boolean;
}

export const Header: React.FC<HeaderProps> = ({ status, wsConnected }) => {
  const [wallClock, setWallClock] = useState<string>(new Date().toISOString());

  useEffect(() => {
    const timer = setInterval(() => {
      setWallClock(new Date().toISOString());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const clockState = status?.clock_status.state || 'stopped';
  const stateColor =
    clockState === 'running'
      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
      : clockState === 'paused'
      ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
      : 'bg-slate-500/10 text-slate-400 border-slate-500/20';

  return (
    <header className="bg-slate-900/90 backdrop-blur border-b border-slate-800 sticky top-0 z-50 px-6 py-4">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        
        {/* Title & Badge */}
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-600/20 text-blue-400 border border-blue-500/30 rounded-lg">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white font-mono">ARGUS</h1>
              <span className="text-xs px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 font-medium border border-blue-500/30">
                v1.0 Data Source & Simulator
              </span>
            </div>
            <p className="text-xs text-slate-400">ICU Synthetic Data Source & Real-Time Telemetry Platform</p>
          </div>
        </div>

        {/* Status Indicators */}
        <div className="flex flex-wrap items-center gap-4 text-xs font-mono">
          
          {/* Simulation State */}
          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border ${stateColor}`}>
            <span className={`w-2 h-2 rounded-full ${clockState === 'running' ? 'bg-emerald-400 animate-pulse' : clockState === 'paused' ? 'bg-amber-400' : 'bg-slate-400'}`}></span>
            <span className="capitalize font-semibold">{clockState}</span>
            <span className="text-slate-500">({status?.clock_status.speed_factor || 1}x)</span>
          </div>

          {/* WebSocket Status */}
          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border ${wsConnected ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20'}`}>
            {wsConnected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
            <span>WS {wsConnected ? 'LIVE STREAM' : 'DISCONNECTED'}</span>
          </div>

          {/* Wall Clock Time */}
          <div className="hidden lg:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 text-slate-300 border border-slate-700">
            <Clock className="w-3.5 h-3.5 text-blue-400" />
            <span>UTC: {wallClock.substring(11, 19)}</span>
          </div>

        </div>

      </div>

      {/* Mandatory Disclaimer */}
      <div className="max-w-7xl mx-auto mt-2 pt-2 border-t border-slate-800/50 flex items-center gap-2 text-[11px] text-amber-400/90 font-medium">
        <ShieldAlert className="w-3.5 h-3.5 shrink-0" />
        <span>SIMULATOR INTERFACE ONLY — Educational/research synthetic ICU data platform. Not for clinical decision-making or patient diagnosis.</span>
      </div>
    </header>
  );
};
