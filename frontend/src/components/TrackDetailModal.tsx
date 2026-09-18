import React, { useEffect, useState } from 'react';
import { X, Activity, MapPin, Info, Volume2 } from 'lucide-react';
import { api } from '../api/flocksense';
import { TrackDetailResponse } from '../types/api';
import { useI18n } from '../i18n';

interface TrackDetailModalProps {
  trackId: number | null;
  onClose: () => void;
}

export const TrackDetailModal: React.FC<TrackDetailModalProps> = ({ trackId, onClose }) => {
  const [detail, setDetail] = useState<TrackDetailResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const { t, speak, canSpeak, isSpeaking, stopSpeech } = useI18n();

  useEffect(() => {
    if (!trackId) {
      setDetail(null);
      return;
    }

    setLoading(true);
    setError(null);

    api
      .getTrackDetail(trackId)
      .then((data) => setDetail(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [trackId]);

  if (!trackId) return null;

  const handleSpeakDetails = () => {
    if (isSpeaking) {
      stopSpeech();
      return;
    }
    const zoneNum = detail?.current_zone ? detail.current_zone.replace(/[^0-9]/g, '') : '2';
    const mainMsg = t.birds.listenMessage.replace('{{id}}', trackId.toString()).replace('{{zone}}', zoneNum);
    const actionMsg = `${t.actions.whatShouldIDo}. ${t.actions.step1} ${t.actions.step2}`;
    speak(`${mainMsg} ${actionMsg}`);
  };

  const getTranslatedBehavior = (behavior: string) => {
    const lower = behavior.toLowerCase();
    if (lower.includes('sit')) return t.birds.sittingProlonged;
    if (lower.includes('feed')) return t.birds.feedingNormally;
    if (lower.includes('walk')) return t.birds.activeMoving;
    if (lower.includes('stand')) return t.birds.standingAlert;
    if (lower.includes('rest')) return t.birds.restingIsolated;
    return behavior;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-950/85 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl rounded-3xl border border-slate-800 bg-slate-900 p-5 sm:p-6 shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-slate-800/80 pb-4">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-2xl">
              🐔
            </div>
            <div>
              <div className="flex items-center space-x-2.5">
                <span className="text-xl sm:text-2xl font-black text-white">
                  {t.birds.birdNumber.replace('{{id}}', trackId.toString())}
                </span>
                {detail && (
                  <span
                    className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${
                      detail.fusion_status === 'ALERT'
                        ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                        : detail.fusion_status === 'WATCH'
                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                        : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                    }`}
                  >
                    {detail.fusion_status === 'ALERT' ? t.status.checkNow : detail.fusion_status === 'WATCH' ? t.status.keepWatching : t.status.allGood}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {t.birds.detailsSubtitle}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {canSpeak && (
              <button
                onClick={handleSpeakDetails}
                className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-300 hover:text-emerald-400 min-w-[44px] min-h-[44px] flex items-center justify-center transition-colors"
                title={t.system.listen}
                aria-label={t.system.listen}
              >
                <Volume2 className="w-5 h-5" />
              </button>
            )}

            <button
              onClick={onClose}
              className="p-2.5 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
              aria-label="Close"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="overflow-y-auto py-4 space-y-4 flex-1 pr-1">
          {loading && (
            <div className="py-12 text-center text-xs text-slate-400 animate-pulse">
              Loading...
            </div>
          )}

          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
              {error}
            </div>
          )}

          {detail && !loading && (
            <>
              {/* Primary Farmer Highlights Card */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 flex items-center space-x-3">
                  <MapPin className="w-7 h-7 text-emerald-400 shrink-0" />
                  <div>
                    <span className="text-xs text-slate-400 block font-medium">
                      {t.birds.currentLocation}
                    </span>
                    <span className="text-lg sm:text-xl font-extrabold text-white">
                      {t.birds.zone.replace('{{id}}', detail.current_zone ? detail.current_zone.replace(/[^0-9]/g, '') : '2')}
                    </span>
                    {detail.previous_zone && detail.previous_zone !== detail.current_zone && detail.previous_zone !== 'UNKNOWN' && (
                      <span className="text-[11px] text-slate-400 block mt-0.5">
                        {t.birds.previousLocation}: {t.birds.zone.replace('{{id}}', detail.previous_zone.replace(/[^0-9]/g, ''))}
                      </span>
                    )}
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 flex items-center space-x-3">
                  <Activity className="w-7 h-7 text-cyan-400 shrink-0" />
                  <div>
                    <span className="text-xs text-slate-400 block font-medium">
                      {t.birds.currentActivity}
                    </span>
                    <span className="text-base sm:text-lg font-extrabold text-white block">
                      {getTranslatedBehavior(detail.current_behavior)}
                    </span>
                    <span className="text-[11px] text-amber-300 block mt-0.5">
                      {t.birds.activityChange}: {detail.camera_deviation_score.toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Action Recommendations Box */}
              <div className="p-4 sm:p-5 rounded-2xl bg-emerald-950/20 border border-emerald-500/30 space-y-2.5">
                <span className="text-emerald-300 font-extrabold text-sm flex items-center space-x-2">
                  <span>📋</span>
                  <span>{t.actions.whatToDo}</span>
                </span>
                <ul className="space-y-1.5 text-xs sm:text-sm text-slate-200">
                  <li className="flex items-center space-x-2">
                    <span>🔍</span>
                    <span>{t.actions.step1}</span>
                  </li>
                  <li className="flex items-center space-x-2">
                    <span>🌾</span>
                    <span>{t.actions.step2}</span>
                  </li>
                  <li className="flex items-center space-x-2">
                    <span>👀</span>
                    <span>{t.actions.step3}</span>
                  </li>
                </ul>
              </div>

              {/* Safety / Acoustic Context Note */}
              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-200/90 flex items-start space-x-2">
                <Info className="w-5 h-5 shrink-0 mt-0.5" />
                <div>
                  <strong>{t.audio.safetyDisclaimer}</strong>
                  <p className="text-[11px] text-amber-300/80 mt-0.5">{t.audio.safetyNote}</p>
                </div>
              </div>

              {/* Collapsible Technical Details for Engineers */}
              <details className="text-xs border border-slate-800 rounded-2xl bg-slate-950/60 overflow-hidden">
                <summary className="p-3.5 font-bold text-slate-400 hover:text-white cursor-pointer select-none">
                  {t.system.technicalDetails} (Engineering Metrics)
                </summary>
                <div className="p-4 pt-0 space-y-3 font-mono text-[11px] border-t border-slate-800/80 text-slate-300">
                  <div className="grid grid-cols-2 gap-2">
                    <div>Inspection Priority: <strong className="text-white">{detail.inspection_priority.toFixed(1)}/100</strong></div>
                    <div>Camera Deviation: <strong className="text-rose-400">{detail.camera_deviation_score.toFixed(1)}/100</strong></div>
                    <div>Movement Rate: <strong className="text-white">{detail.movement_rate.toFixed(1)} px/s</strong></div>
                    <div>Stationary Duration: <strong className="text-white">{detail.stationary_duration.toFixed(1)} s</strong></div>
                  </div>
                  <div className="text-[10px] text-slate-500 pt-2 border-t border-slate-800">
                    {detail.disclaimer}
                  </div>
                </div>
              </details>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-slate-800/80 flex justify-end">
          <button
            onClick={onClose}
            className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-sm font-bold text-white transition-colors min-h-[44px]"
          >
            {t.system.close}
          </button>
        </div>
      </div>
    </div>
  );
};
