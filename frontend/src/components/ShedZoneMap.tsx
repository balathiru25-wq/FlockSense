import React from 'react';
import { MapPin, AlertTriangle, Eye, Video } from 'lucide-react';
import { TrackSummaryItem } from '../types/api';

interface ShedZoneMapProps {
  tracks: TrackSummaryItem[];
  onSelectTrack: (trackId: number) => void;
  selectedTrackId: number | null;
}

interface ZoneMeta {
  id: string;
  name: string;
  type: string;
}

const ZONES: ZoneMeta[] = [
  { id: 'ZONE_1', name: 'Zone 1: Feeding A', type: 'Feeders' },
  { id: 'ZONE_2', name: 'Zone 2: Roost Central', type: 'Resting' },
  { id: 'ZONE_3', name: 'Zone 3: Drinkers East', type: 'Drinkers' },
  { id: 'ZONE_4', name: 'Zone 4: Scratching West', type: 'Activity' },
  { id: 'ZONE_5', name: 'Zone 5: Foraging Central', type: 'Open' },
  { id: 'ZONE_6', name: 'Zone 6: Perimeter East', type: 'Perimeter' },
];

export const ShedZoneMap: React.FC<ShedZoneMapProps> = ({
  tracks,
  onSelectTrack,
  selectedTrackId,
}) => {
  // Group tracks by zone
  const tracksByZone: Record<string, TrackSummaryItem[]> = {};
  ZONES.forEach((z) => {
    tracksByZone[z.id] = [];
  });

  tracks.forEach((t) => {
    if (tracksByZone[t.current_zone]) {
      tracksByZone[t.current_zone].push(t);
    } else {
      tracksByZone['ZONE_1']?.push(t);
    }
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ALERT':
        return 'bg-rose-500 text-white border-rose-400 shadow-rose-900/50 animate-pulse';
      case 'WATCH':
        return 'bg-amber-500 text-slate-950 border-amber-300 font-bold';
      default:
        return 'bg-emerald-600/90 text-white border-emerald-400/50';
    }
  };

  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-6 shadow-xl backdrop-blur-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold tracking-wide text-white flex items-center space-x-2">
            <MapPin className="w-4 h-4 text-emerald-400" />
            <span>Virtual Poultry Shed Zone Grid</span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time track spatial assignment across 6 virtual shed zones
          </p>
        </div>

        {/* Video feed indicator */}
        <div className="flex items-center space-x-2 px-2.5 py-1 rounded-md bg-slate-950/80 border border-slate-800 text-[11px] font-mono text-slate-400">
          <Video className="w-3.5 h-3.5 text-cyan-400" />
          <span>RECORDED DEMO OVERLAY</span>
        </div>
      </div>

      {/* 2x3 Zone Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {ZONES.map((zone) => {
          const zoneTracks = tracksByZone[zone.id] || [];
          const alertCount = zoneTracks.filter((t) => t.status === 'ALERT').length;
          const watchCount = zoneTracks.filter((t) => t.status === 'WATCH').length;

          const hasAlert = alertCount > 0;
          const hasWatch = watchCount > 0;

          return (
            <div
              key={zone.id}
              className={`rounded-xl border p-3.5 flex flex-col justify-between min-h-[140px] transition-all bg-slate-950/50 ${
                hasAlert
                  ? 'border-rose-500/40 bg-rose-950/10'
                  : hasWatch
                  ? 'border-amber-500/30 bg-amber-950/10'
                  : 'border-slate-800/80 hover:border-slate-700'
              }`}
            >
              {/* Zone Header */}
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-xs font-bold text-slate-200 block">
                    {zone.id}
                  </span>
                  <span className="text-[11px] text-slate-400 font-medium">
                    {zone.name.split(':')[1] || zone.name}
                  </span>
                </div>

                <div className="flex items-center space-x-1.5 text-[10px] font-mono">
                  {hasAlert && (
                    <span className="px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/40">
                      {alertCount} ALERT
                    </span>
                  )}
                  {hasWatch && (
                    <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                      {watchCount} WATCH
                    </span>
                  )}
                  <span className="text-slate-400 px-1 py-0.5">
                    {zoneTracks.length} birds
                  </span>
                </div>
              </div>

              {/* Chickens inside this zone */}
              <div className="mt-3 flex flex-wrap gap-1.5">
                {zoneTracks.length === 0 ? (
                  <span className="text-[11px] text-slate-600 italic py-2">
                    No active tracks in zone
                  </span>
                ) : (
                  zoneTracks.map((t) => (
                    <button
                      key={t.track_id}
                      onClick={() => onSelectTrack(t.track_id)}
                      className={`px-2 py-1 rounded-md text-[11px] font-mono font-bold border shadow-sm transition-all flex items-center space-x-1 ${getStatusBadge(
                        t.status
                      )} ${
                        selectedTrackId === t.track_id
                          ? 'ring-2 ring-white scale-105'
                          : 'hover:scale-105'
                      }`}
                      title={`Track #${t.track_id} | ${t.current_behavior} | Priority: ${t.inspection_priority.toFixed(
                        1
                      )}`}
                    >
                      <span>🐔</span>
                      <span>#{t.track_id}</span>
                      {t.previous_zone !== t.current_zone && t.previous_zone !== 'UNKNOWN' && (
                        <span className="text-[9px] opacity-80" title={`Moved from ${t.previous_zone}`}>
                          ←{t.previous_zone.replace('ZONE_', 'Z')}
                        </span>
                      )}
                    </button>
                  ))
                )}
              </div>

              {/* Zone Type Footnote */}
              <div className="text-[10px] text-slate-500 pt-2 border-t border-slate-900 flex justify-between">
                <span>Type: {zone.type}</span>
                <span>Track Follows Bird</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
