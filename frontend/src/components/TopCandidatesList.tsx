import React from 'react';
import { Award, Volume2, MapPin, Eye } from 'lucide-react';
import { CandidateItem } from '../types/api';
import { useI18n } from '../i18n';

interface TopCandidatesListProps {
  candidates: CandidateItem[];
  onSelectTrack: (trackId: number) => void;
  selectedTrackId: number | null;
  loading: boolean;
}

export const TopCandidatesList: React.FC<TopCandidatesListProps> = ({
  candidates,
  onSelectTrack,
  selectedTrackId,
  loading,
}) => {
  const { t, speak, canSpeak } = useI18n();

  if (loading && candidates.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-6 shadow-xl animate-pulse">
        <div className="h-6 w-40 bg-slate-800 rounded mb-4"></div>
        <div className="space-y-3">
          <div className="h-16 bg-slate-800/60 rounded-xl"></div>
          <div className="h-16 bg-slate-800/60 rounded-xl"></div>
          <div className="h-16 bg-slate-800/60 rounded-xl"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 sm:p-6 shadow-xl backdrop-blur-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold tracking-wide text-white flex items-center space-x-2">
            <Award className="w-4 h-4 text-amber-400" />
            <span>{t.birds.toCheck}</span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            {t.birds.toCheckSubtitle}
          </p>
        </div>
        <span className="text-[11px] font-mono text-slate-400 px-2.5 py-0.5 rounded-full bg-slate-950 border border-slate-800">
          {candidates.length}
        </span>
      </div>

      {candidates.length === 0 ? (
        <div className="py-8 text-center border border-dashed border-slate-800 rounded-xl bg-slate-950/30">
          <p className="text-xs font-semibold text-slate-300">
            {t.birds.noBirdsNeedAttention}
          </p>
          <p className="text-[11px] text-slate-500 mt-1">
            {t.birds.noBirdsSub}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {candidates.map((cand, idx) => {
            const isAlert = cand.status === 'ALERT';
            const isWatch = cand.status === 'WATCH';
            const isSelected = selectedTrackId === cand.track_id;
            const zoneNum = cand.current_zone ? cand.current_zone.replace(/[^0-9]/g, '') : '1';

            return (
              <div
                key={cand.track_id}
                onClick={() => onSelectTrack(cand.track_id)}
                className={`p-4 rounded-2xl border-2 transition-all cursor-pointer select-none ${
                  isSelected
                    ? 'border-emerald-500 bg-emerald-950/20 shadow-lg shadow-emerald-950/40'
                    : isAlert
                    ? 'border-rose-500/40 bg-rose-950/10 hover:border-rose-500/60'
                    : isWatch
                    ? 'border-amber-500/30 bg-amber-950/10 hover:border-amber-500/50'
                    : 'border-slate-800/80 bg-slate-950/40 hover:border-slate-700'
                }`}
              >
                {/* Header line: Rank, Track ID, Priority & Status */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2.5">
                    <span className="w-6 h-6 rounded-full bg-slate-800 border border-slate-700 text-xs font-bold text-slate-300 flex items-center justify-center">
                      #{idx + 1}
                    </span>
                    <span className="text-base font-extrabold text-white">
                      {t.birds.birdNumber.replace('{{id}}', cand.track_id.toString())}
                    </span>
                  </div>

                  <div className="flex items-center space-x-2">
                    {canSpeak && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          const msg = t.birds.listenMessage
                            .replace('{{id}}', cand.track_id.toString())
                            .replace('{{zone}}', zoneNum);
                          speak(msg);
                        }}
                        className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-emerald-400 min-w-[36px] min-h-[36px] flex items-center justify-center"
                        title={t.system.listen}
                      >
                        <Volume2 className="w-4 h-4" />
                      </button>
                    )}

                    <span
                      className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${
                        isAlert
                          ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                          : isWatch
                          ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                          : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                      }`}
                    >
                      {isAlert ? t.status.checkNow : isWatch ? t.status.keepWatching : t.status.allGood}
                    </span>
                  </div>
                </div>

                {/* Sub details: Zone & Activity */}
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                  <div className="flex items-center space-x-1.5 text-slate-300">
                    <MapPin className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span className="truncate">
                      {t.birds.zone.replace('{{id}}', zoneNum)}
                    </span>
                  </div>
                  <div className="flex items-center space-x-1.5 text-slate-300">
                    <Eye className="w-4 h-4 text-cyan-400 shrink-0" />
                    <span className="truncate">
                      {cand.camera_deviation_score >= 70 ? t.birds.movingLess : t.birds.sittingProlonged}
                    </span>
                  </div>
                </div>

                {/* Bottom button */}
                <button
                  type="button"
                  className="mt-3 w-full py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-white font-bold text-xs transition-colors min-h-[40px] flex items-center justify-center"
                >
                  {t.birds.viewBird}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
