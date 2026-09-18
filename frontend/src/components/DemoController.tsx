import React, { useState } from 'react';
import { Play, RotateCcw, FastForward, CheckCircle2, AlertCircle, ArrowRight, ShieldCheck, Volume2, MapPin } from 'lucide-react';
import { api } from '../api/flocksense';

interface DemoControllerProps {
  onStateChanged: () => void;
  isPresentationMode: boolean;
  setIsPresentationMode: (val: boolean) => void;
}

export const DemoController: React.FC<DemoControllerProps> = ({
  onStateChanged,
  isPresentationMode,
  setIsPresentationMode,
}) => {
  const [activeStep, setActiveStep] = useState<number>(0);
  const [isRunningFull, setIsRunningFull] = useState<boolean>(false);
  const [statusMsg, setStatusMsg] = useState<string>('Ready for demonstration.');

  const handleReset = async () => {
    try {
      await api.demoReset();
      setActiveStep(0);
      setStatusMsg('State reset to clean zero-state baseline.');
      onStateChanged();
    } catch (err: unknown) {
      setStatusMsg(`Reset error: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handleStep1 = async () => {
    try {
      await api.demoNormal();
      setActiveStep(1);
      setStatusMsg('Step 1: Normal flock initialized (Tracks #12, #17, #24 all healthy).');
      onStateChanged();
    } catch (err: unknown) {
      setStatusMsg(`Step 1 error: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handleStep2 = async () => {
    try {
      await api.demoBehaviorDeviation();
      setActiveStep(2);
      setStatusMsg('Step 2: Track #17 behavioral deviation established (lethargy, isolation).');
      onStateChanged();
    } catch (err: unknown) {
      setStatusMsg(`Step 2 error: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handleStep3 = async () => {
    try {
      await api.demoZoneTransition();
      setActiveStep(3);
      setStatusMsg('Step 3: Track #17 migrated Zone 3 -> Zone 2 (Risk followed Track ID).');
      onStateChanged();
    } catch (err: unknown) {
      setStatusMsg(`Step 3 error: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handleStep4 = async () => {
    try {
      const res = (await api.demoAnalyzeTestAudio('normal')) as { predicted_state: string; overall_abnormality_pct: number };
      setActiveStep(4);
      setStatusMsg(`Step 4: Normal test audio analyzed (${res.predicted_state}, ${res.overall_abnormality_pct}% dev). Baseline preserved.`);
      onStateChanged();
    } catch (err: unknown) {
      setStatusMsg(`Step 4 error: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handleStep5 = async () => {
    try {
      const res = (await api.demoAnalyzeTestAudio('abnormal')) as { predicted_state: string; overall_abnormality_pct: number };
      setActiveStep(5);
      setStatusMsg(`Step 5: Abnormal audio analyzed (${res.predicted_state}, ${res.overall_abnormality_pct}%). Global acoustic alert triggered.`);
      onStateChanged();
    } catch (err: unknown) {
      setStatusMsg(`Step 5 error: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handleRunFull = async () => {
    setIsRunningFull(true);
    try {
      // Step 1: Reset and normal
      await api.demoReset();
      await api.demoNormal();
      setActiveStep(1);
      setStatusMsg('Automated Demo: Step 1 Normal monitoring...');
      onStateChanged();
      await new Promise((r) => setTimeout(r, 2500));

      // Step 2: Behavior deviation
      await api.demoBehaviorDeviation();
      setActiveStep(2);
      setStatusMsg('Automated Demo: Step 2 Track #17 behavioral deviation elevated...');
      onStateChanged();
      await new Promise((r) => setTimeout(r, 2500));

      // Step 3: Zone transition
      await api.demoZoneTransition();
      setActiveStep(3);
      setStatusMsg('Automated Demo: Step 3 Track #17 moves Zone 3 -> Zone 2...');
      onStateChanged();
      await new Promise((r) => setTimeout(r, 2500));

      // Step 4: Abnormal audio
      await api.demoAnalyzeTestAudio('abnormal');
      setActiveStep(5);
      setStatusMsg('Automated Demo: Step 4/5 Global acoustic alert & multimodal fusion complete!');
      onStateChanged();
    } catch (err: unknown) {
      setStatusMsg(`Auto demo error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsRunningFull(false);
    }
  };

  return (
    <div className="rounded-2xl border-2 border-amber-500/40 bg-slate-900/90 p-4 shadow-2xl backdrop-blur-md">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 rounded-full bg-amber-400 animate-ping"></div>
          <div>
            <h4 className="text-xs font-bold text-amber-300 font-mono tracking-wider uppercase">
              Judge Demonstration Controller
            </h4>
            <p className="text-[11px] text-slate-400">
              Deterministic scenario sequence showing normal monitoring to early-warning alert
            </p>
          </div>
        </div>

        {/* Presentation mode toggle & Full run */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setIsPresentationMode(!isPresentationMode)}
            className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-all border ${
              isPresentationMode
                ? 'bg-cyan-500 text-slate-950 border-cyan-400 font-bold'
                : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
            }`}
          >
            {isPresentationMode ? 'PROJECTOR MODE: ON' : 'PROJECTOR MODE: OFF'}
          </button>

          <button
            onClick={handleRunFull}
            disabled={isRunningFull}
            className="px-3 py-1 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold shadow-md transition-all disabled:opacity-50 flex items-center space-x-1.5"
          >
            <Play className="w-3.5 h-3.5" />
            <span>{isRunningFull ? 'Running Demo...' : 'RUN FULL DEMO'}</span>
          </button>

          <button
            onClick={handleReset}
            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 flex items-center space-x-1"
          >
            <RotateCcw className="w-3 h-3" />
            <span>RESET</span>
          </button>
        </div>
      </div>

      {/* Step Buttons */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mt-3 text-xs font-mono">
        <button
          onClick={handleStep1}
          className={`p-2 rounded-lg border text-left transition-all ${
            activeStep === 1
              ? 'border-emerald-400 bg-emerald-950/40 text-emerald-200'
              : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:bg-slate-800/60'
          }`}
        >
          <span className="text-[10px] text-slate-500 block">STEP 1</span>
          <span className="font-bold block text-slate-200">Normal Flock</span>
          <span className="text-[9px] text-slate-400">Baseline PEACETIME</span>
        </button>

        <button
          onClick={handleStep2}
          className={`p-2 rounded-lg border text-left transition-all ${
            activeStep === 2
              ? 'border-amber-400 bg-amber-950/40 text-amber-200'
              : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:bg-slate-800/60'
          }`}
        >
          <span className="text-[10px] text-slate-500 block">STEP 2</span>
          <span className="font-bold block text-slate-200">#17 Deviation</span>
          <span className="text-[9px] text-slate-400">Stationary lethargy</span>
        </button>

        <button
          onClick={handleStep3}
          className={`p-2 rounded-lg border text-left transition-all ${
            activeStep === 3
              ? 'border-cyan-400 bg-cyan-950/40 text-cyan-200'
              : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:bg-slate-800/60'
          }`}
        >
          <span className="text-[10px] text-slate-500 block">STEP 3</span>
          <span className="font-bold block text-slate-200">Zone 3 → Zone 2</span>
          <span className="text-[9px] text-slate-400">Risk follows Track ID</span>
        </button>

        <button
          onClick={handleStep4}
          className={`p-2 rounded-lg border text-left transition-all ${
            activeStep === 4
              ? 'border-emerald-400 bg-emerald-950/40 text-emerald-200'
              : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:bg-slate-800/60'
          }`}
        >
          <span className="text-[10px] text-slate-500 block">STEP 4</span>
          <span className="font-bold block text-slate-200">Normal Audio</span>
          <span className="text-[9px] text-slate-400">Real ResNet18 check</span>
        </button>

        <button
          onClick={handleStep5}
          className={`p-2 rounded-lg border text-left transition-all ${
            activeStep === 5
              ? 'border-rose-400 bg-rose-950/40 text-rose-200'
              : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:bg-slate-800/60'
          }`}
        >
          <span className="text-[10px] text-slate-500 block">STEP 5/6</span>
          <span className="font-bold block text-rose-300">Abnormal Audio</span>
          <span className="text-[9px] text-slate-400">Fusion alert & ranking</span>
        </button>
      </div>

      {/* Live Status Message & Attribution Disclaimer */}
      <div className="mt-2.5 pt-2 border-t border-slate-800/80 flex flex-col sm:flex-row items-start sm:items-center justify-between text-[11px] gap-2">
        <div className="text-slate-300 font-mono flex items-center space-x-1.5">
          <span className="text-cyan-400 font-bold">STATUS:</span>
          <span>{statusMsg}</span>
        </div>
        <div className="text-[10px] text-amber-300/90 font-mono">
          SOUND LOCALIZATION: NOT AVAILABLE (FLOCK CONTEXT)
        </div>
      </div>
    </div>
  );
};
