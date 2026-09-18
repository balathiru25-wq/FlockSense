import React from 'react';
import { ShieldCheck, Cpu, HardDrive, AlertOctagon, Info, CheckCircle2 } from 'lucide-react';
import { SystemInfoResponse, HealthResponse } from '../types/api';

interface SystemStatusPanelProps {
  systemInfo: SystemInfoResponse | null;
  health: HealthResponse | null;
}

export const SystemStatusPanel: React.FC<SystemStatusPanelProps> = ({ systemInfo, health }) => {
  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-6 shadow-xl backdrop-blur-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold tracking-wide text-white flex items-center space-x-2">
            <Cpu className="w-4 h-4 text-emerald-400" />
            <span>AI Architecture & Sensor Pipeline Status</span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Operational pipeline readiness and prototype validation boundaries
          </p>
        </div>
      </div>

      {/* Component Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="font-semibold">Bioacoustics AI</span>
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
          </div>
          <span className="text-white font-bold block truncate">
            {systemInfo?.audio_model.split('(')[0] || 'ResNet18 Log-Mel'}
          </span>
          <span className="text-[10px] text-slate-500 block mt-0.5">
            1-Channel Log-Mel Spectrogram (16kHz)
          </span>
        </div>

        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="font-semibold">Vision Behaviors</span>
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
          </div>
          <span className="text-white font-bold block truncate">Roboflow Model 17</span>
          <span className="text-[10px] text-slate-500 block mt-0.5">
            7 Observable Poultry Postures
          </span>
        </div>

        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="font-semibold">Tracking Engine</span>
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
          </div>
          <span className="text-white font-bold block truncate">ByteTrack Supervision</span>
          <span className="text-[10px] text-slate-500 block mt-0.5">
            Generic CHICKEN Class (ID Persistence)
          </span>
        </div>

        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="font-semibold">Camera Anomaly</span>
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
          </div>
          <span className="text-white font-bold block truncate">Isolation Forest</span>
          <span className="text-[10px] text-slate-500 block mt-0.5">
            18 Behavioral & Locomotor Features
          </span>
        </div>
      </div>

      {/* Validation Badges Section */}
      <div className="mt-5 pt-4 border-t border-slate-800/80">
        <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase block mb-2.5">
          Prototype Validation Status & Boundaries
        </span>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono">
          <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80">
            <span className="text-slate-500 block text-[10px]">CAMERA ANOMALY MODEL:</span>
            <span className="text-amber-300 font-bold">SYNTHETIC BASELINE</span>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80">
            <span className="text-slate-500 block text-[10px]">SOUND LOCALIZATION:</span>
            <span className="text-amber-300 font-bold">NOT AVAILABLE (FLOCK)</span>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80">
            <span className="text-slate-500 block text-[10px]">MEDICAL / DISEASE CLAIMS:</span>
            <span className="text-cyan-300 font-bold">NONE (SCREENING ONLY)</span>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80">
            <span className="text-slate-500 block text-[10px]">FUSION WEIGHTS:</span>
            <span className="text-slate-300 font-bold">PROVISIONAL DEV</span>
          </div>
        </div>
      </div>

      {/* Non-Diagnostic Disclaimer Footer */}
      <div className="mt-4 p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/60 text-[11px] text-slate-500 flex items-center space-x-2">
        <Info className="w-4 h-4 text-slate-400 shrink-0" />
        <span>
          FlockSense provides automated early-warning screening based on acoustic and behavioral deviations.
          It does not provide veterinary diagnosis or prescription.
        </span>
      </div>
    </div>
  );
};
