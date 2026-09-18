import React, { useState } from 'react';
import { AlertCircle, Volume2 } from 'lucide-react';
import { AlertItem } from '../types/api';
import { useI18n } from '../i18n';

interface AlertsFeedProps {
  alerts: AlertItem[];
  loading: boolean;
  onFilterChange?: (level: string) => void;
}

export const AlertsFeed: React.FC<AlertsFeedProps> = ({ alerts, onFilterChange }) => {
  const [filter, setFilter] = useState<string>('ALL');
  const { t, speak, canSpeak } = useI18n();

  const handleFilterClick = (lvl: string) => {
    setFilter(lvl);
    if (onFilterChange) {
      onFilterChange(lvl);
    }
  };

  const filteredAlerts = alerts.filter((a) => {
    if (filter === 'ALL') return true;
    return a.level.toUpperCase() === filter;
  });

  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 sm:p-6 shadow-xl backdrop-blur-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold tracking-wide text-white flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-rose-400" />
            <span>{t.alerts.title}</span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            {t.alerts.subtitle}
          </p>
        </div>

        {/* Filter Badges */}
        <div className="flex items-center space-x-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800">
          {[
            { id: 'ALL', label: t.alerts.all },
            { id: 'ALERT', label: t.alerts.highPriority },
            { id: 'WATCH', label: t.alerts.moderate },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => handleFilterClick(item.id)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-bold transition-colors min-h-[32px] ${
                filter === item.id
                  ? 'bg-emerald-500 text-slate-950 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* Feed list */}
      {filteredAlerts.length === 0 ? (
        <div className="py-8 text-center border border-dashed border-slate-800 rounded-xl bg-slate-950/30 space-y-1">
          <p className="text-xs font-semibold text-slate-300">
            {t.alerts.noActiveAlerts}
          </p>
          <p className="text-[11px] text-slate-500">
            {t.alerts.noAlertsSub}
          </p>
        </div>
      ) : (
        <div className="space-y-2.5 max-h-[360px] overflow-y-auto pr-1">
          {filteredAlerts.map((alert) => {
            const isAlert = alert.level === 'ALERT';
            return (
              <div
                key={alert.alert_id}
                className={`p-3.5 rounded-xl border text-xs transition-all ${
                  isAlert
                    ? 'border-rose-500/40 bg-rose-950/20 text-slate-200'
                    : 'border-amber-500/30 bg-amber-950/15 text-slate-200'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span
                      className={`font-bold px-2 py-0.5 rounded-full text-[10px] uppercase border ${
                        isAlert
                          ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                          : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                      }`}
                    >
                      {isAlert ? t.status.checkNow : t.status.keepWatching}
                    </span>
                    {alert.track_id && (
                      <span className="font-mono text-cyan-300 font-bold">
                        {t.birds.birdNumber.replace('{{id}}', alert.track_id.toString())}
                      </span>
                    )}
                    {alert.current_zone && (
                      <span className="text-slate-400">
                        • {t.birds.zone.replace('{{id}}', alert.current_zone.replace(/[^0-9]/g, ''))}
                      </span>
                    )}
                  </div>

                  {canSpeak && (
                    <button
                      type="button"
                      onClick={() => speak(`${alert.message}. ${alert.recommendation}`)}
                      className="p-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-emerald-400 min-w-[32px] min-h-[32px] flex items-center justify-center shrink-0"
                      title={t.system.listen}
                    >
                      <Volume2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                <p className="text-slate-200 mt-2 font-medium leading-relaxed">
                  {alert.message}
                </p>

                <p className="text-[11px] text-emerald-400 font-semibold mt-1.5 flex items-center space-x-1">
                  <span>↳</span>
                  <span>{alert.recommendation}</span>
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
