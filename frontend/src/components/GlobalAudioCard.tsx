import React from 'react';
import { Volume2, Info, Radio } from 'lucide-react';
import { GlobalAudioContext } from '../types/api';
import { useI18n } from '../i18n';

interface GlobalAudioCardProps {
  audioContext: GlobalAudioContext | null;
  loading: boolean;
}

export const GlobalAudioCard: React.FC<GlobalAudioCardProps> = ({ audioContext, loading }) => {
  const { t, speak, canSpeak } = useI18n();

  if (loading && !audioContext) {
    return (
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 animate-pulse">
        <div className="h-6 w-36 bg-slate-800 rounded mb-4"></div>
        <div className="h-10 w-24 bg-slate-800 rounded mb-4"></div>
        <div className="h-4 w-full bg-slate-800/60 rounded"></div>
      </div>
    );
  }

  const score = audioContext?.score ?? 0;
  const isActive = audioContext?.active ?? false;
  const isUnusual = score >= 35;

  let badgeColor = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
  let gaugeColor = 'bg-emerald-500';
  if (score >= 70) {
    badgeColor = 'bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse';
    gaugeColor = 'bg-rose-500';
  } else if (score >= 35) {
    badgeColor = 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    gaugeColor = 'bg-amber-500';
  }

  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 sm:p-6 shadow-xl backdrop-blur-sm relative overflow-hidden">
      {/* Top row */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
              {t.audio.title}
            </span>
            {isActive && (
              <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                <Radio className="w-2.5 h-2.5 animate-spin" />
                <span>ACTIVE</span>
              </span>
            )}
          </div>

          <div className="flex items-baseline space-x-3 mt-1">
            <span className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              {score.toFixed(1)}%
            </span>
            <span className="text-xs text-slate-400 font-medium">
              {t.audio.abnormalityLevel}
            </span>
            <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ml-2 ${badgeColor}`}>
              {isUnusual ? t.audio.unusualBadge : t.audio.normalBadge}
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {canSpeak && (
            <button
              type="button"
              onClick={() =>
                speak(
                  isUnusual
                    ? `${t.audio.unusual}. ${score.toFixed(0)} percent.`
                    : `${t.audio.normal}.`
                )
              }
              className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-400 hover:text-emerald-400 min-w-[44px] min-h-[44px] flex items-center justify-center transition-colors"
              title={t.system.listen}
            >
              <Volume2 className="w-5 h-5" />
            </button>
          )}

          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
            {isUnusual ? (
              <Volume2 className="w-6 h-6 text-rose-400 animate-pulse" />
            ) : (
              <Volume2 className="w-6 h-6 text-emerald-400" />
            )}
          </div>
        </div>
      </div>

      {/* Meter Bar */}
      <div className="mt-4">
        <div className="flex justify-between text-[11px] font-medium text-slate-400 mb-1">
          <span>0%</span>
          <span>{isUnusual ? t.audio.unusual : t.audio.normal}</span>
          <span>100%</span>
        </div>
        <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden p-0.5">
          <div
            className={`h-full rounded-full transition-all duration-500 ${gaugeColor}`}
            style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
          ></div>
        </div>
      </div>

      {/* Safety Notice */}
      <div className="mt-4 p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-300 flex items-start space-x-2">
        <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div>
          <strong className="text-amber-300 font-semibold">{t.audio.safetyDisclaimer}</strong>
          <span className="text-slate-400 block mt-0.5 text-[11px]">{t.audio.safetyNote}</span>
        </div>
      </div>
    </div>
  );
};
