import React from 'react';
import { ShieldCheck, AlertTriangle, AlertOctagon, Volume2 } from 'lucide-react';
import { FlockStatusResponse } from '../types/api';
import { useI18n } from '../i18n';

interface FlockStatusCardProps {
  statusData: FlockStatusResponse | null;
  loading: boolean;
}

export const FlockStatusCard: React.FC<FlockStatusCardProps> = ({ statusData, loading }) => {
  const { t, speak, canSpeak } = useI18n();

  if (loading && !statusData) {
    return (
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 animate-pulse">
        <div className="h-6 w-36 bg-slate-800 rounded mb-4"></div>
        <div className="h-12 w-48 bg-slate-800 rounded mb-6"></div>
        <div className="grid grid-cols-3 gap-4">
          <div className="h-16 bg-slate-800/60 rounded-xl"></div>
          <div className="h-16 bg-slate-800/60 rounded-xl"></div>
          <div className="h-16 bg-slate-800/60 rounded-xl"></div>
        </div>
      </div>
    );
  }

  const flockStatus = statusData?.flock_status || 'NORMAL';
  const activeTracks = statusData?.tracking.active_tracks ?? 0;
  const highDeviation = statusData?.tracking.high_deviation_tracks ?? 0;

  const themeConfig = {
    NORMAL: {
      color: 'text-emerald-400',
      label: t.status.allGood,
      bgGlow: 'from-emerald-950/20 via-slate-900/40 to-slate-900/60',
      borderColor: 'border-emerald-500/30',
      badgeBg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
      icon: <ShieldCheck className="w-8 h-8 text-emerald-400" />,
      subtext: t.status.allGoodDesc,
    },
    WATCH: {
      color: 'text-amber-400',
      label: t.status.keepWatching,
      bgGlow: 'from-amber-950/20 via-slate-900/40 to-slate-900/60',
      borderColor: 'border-amber-500/30',
      badgeBg: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
      icon: <AlertTriangle className="w-8 h-8 text-amber-400" />,
      subtext: t.status.keepWatchingDesc,
    },
    ALERT: {
      color: 'text-rose-400',
      label: t.status.checkNow,
      bgGlow: 'from-rose-950/30 via-slate-900/40 to-slate-900/60',
      borderColor: 'border-rose-500/40',
      badgeBg: 'bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse',
      icon: <AlertOctagon className="w-8 h-8 text-rose-400" />,
      subtext: t.status.checkNowDesc,
    },
  }[flockStatus];

  return (
    <div
      className={`relative overflow-hidden rounded-2xl border ${themeConfig.borderColor} bg-gradient-to-br ${themeConfig.bgGlow} p-5 sm:p-6 shadow-xl backdrop-blur-sm transition-all duration-300`}
    >
      <div className="flex items-start justify-between">
        <div>
          <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
            {t.navigation.commandCenter} • {t.navigation.home}
          </span>
          <div className="flex items-center space-x-3 mt-1">
            <span className={`text-3xl sm:text-4xl font-extrabold tracking-tight ${themeConfig.color}`}>
              {themeConfig.label}
            </span>
            <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${themeConfig.badgeBg}`}>
              {flockStatus}
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-300 mt-1.5 max-w-md">
            {themeConfig.subtext}
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {canSpeak && (
            <button
              type="button"
              onClick={() => speak(`${themeConfig.label}. ${themeConfig.subtext}`)}
              className="p-2.5 rounded-xl bg-slate-950/80 border border-slate-800 text-slate-400 hover:text-emerald-400 min-w-[44px] min-h-[44px] flex items-center justify-center transition-colors"
              title={t.system.listen}
            >
              <Volume2 className="w-5 h-5" />
            </button>
          )}
          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
            {themeConfig.icon}
          </div>
        </div>
      </div>

      {/* Stats counter row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-6">
        <div className="rounded-xl bg-slate-950/60 border border-slate-800/80 p-3">
          <span className="text-[11px] font-medium text-slate-400 block truncate">
            {t.navigation.flock} (Tracked)
          </span>
          <span className="text-xl font-bold font-mono text-white mt-0.5 block">
            {activeTracks}
          </span>
        </div>

        <div className="rounded-xl bg-slate-950/60 border border-slate-800/80 p-3">
          <span className="text-[11px] font-medium text-slate-400 block truncate">
            {t.birds.toCheck}
          </span>
          <span className={`text-xl font-bold font-mono mt-0.5 block ${highDeviation > 0 ? 'text-amber-400' : 'text-slate-200'}`}>
            {highDeviation}
          </span>
        </div>

        <div className="rounded-xl bg-slate-950/60 border border-slate-800/80 p-3 col-span-2 sm:col-span-1">
          <span className="text-[11px] font-medium text-slate-400 block truncate">
            {t.actions.whatShouldIDo}
          </span>
          <span className="text-xs font-semibold text-emerald-400 mt-1 block truncate">
            {flockStatus === 'NORMAL' ? t.actions.continueMonitoring : t.actions.inspectBird}
          </span>
        </div>
      </div>
    </div>
  );
};
