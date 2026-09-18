import React, { useState } from 'react';
import { Search, ArrowUpDown, MapPin, Activity, Clock, ShieldCheck, AlertTriangle } from 'lucide-react';
import { TrackSummaryItem } from '../types/api';

interface TracksViewProps {
  tracks: TrackSummaryItem[];
  onSelectTrack: (trackId: number) => void;
  loading: boolean;
}

export const TracksView: React.FC<TracksViewProps> = ({ tracks, onSelectTrack, loading }) => {
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [sortBy, setSortBy] = useState<'priority' | 'deviation' | 'id' | 'zone'>('priority');

  const filteredTracks = tracks.filter((t) => {
    const term = searchTerm.toLowerCase();
    return (
      String(t.track_id).includes(term) ||
      t.current_zone.toLowerCase().includes(term) ||
      t.current_behavior.toLowerCase().includes(term) ||
      t.status.toLowerCase().includes(term)
    );
  });

  const sortedTracks = [...filteredTracks].sort((a, b) => {
    switch (sortBy) {
      case 'priority':
        return b.inspection_priority - a.inspection_priority;
      case 'deviation':
        return b.camera_deviation_score - a.camera_deviation_score;
      case 'id':
        return a.track_id - b.track_id;
      case 'zone':
        return a.current_zone.localeCompare(b.current_zone);
      default:
        return 0;
    }
  });

  return (
    <div className="space-y-4">
      {/* Controls Header */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-900/60 p-4 rounded-2xl border border-slate-800">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by Track ID, zone, or behavior..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
          />
        </div>

        <div className="flex items-center space-x-2 text-xs">
          <span className="text-slate-400 font-medium flex items-center space-x-1">
            <ArrowUpDown className="w-3.5 h-3.5 text-cyan-400" />
            <span>Sort By:</span>
          </span>
          {[
            { id: 'priority', label: 'Inspection Priority' },
            { id: 'deviation', label: 'Camera Deviation' },
            { id: 'id', label: 'Track ID' },
            { id: 'zone', label: 'Zone' },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => setSortBy(item.id as typeof sortBy)}
              className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-colors ${
                sortBy === item.id
                  ? 'bg-slate-800 text-white border border-slate-700'
                  : 'text-slate-400 hover:text-slate-200 bg-slate-950 border border-slate-900'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tracks Table */}
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800 font-mono">
              <tr>
                <th className="py-3 px-4">Track ID</th>
                <th className="py-3 px-4">Current Zone</th>
                <th className="py-3 px-4">Observed Behavior</th>
                <th className="py-3 px-4">Movement Rate</th>
                <th className="py-3 px-4">Camera Deviation</th>
                <th className="py-3 px-4">Inspection Priority</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {sortedTracks.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500 font-sans italic">
                    {loading ? 'Loading tracked flock birds...' : 'No active tracks match your query.'}
                  </td>
                </tr>
              ) : (
                sortedTracks.map((t) => {
                  const isAlert = t.status === 'ALERT';
                  const isWatch = t.status === 'WATCH';

                  return (
                    <tr
                      key={t.track_id}
                      onClick={() => onSelectTrack(t.track_id)}
                      className="hover:bg-slate-800/40 cursor-pointer transition-colors"
                    >
                      <td className="py-3 px-4 font-bold text-white">
                        #{t.track_id}
                      </td>
                      <td className="py-3 px-4 text-slate-300 flex items-center space-x-1">
                        <MapPin className="w-3 h-3 text-cyan-400" />
                        <span>{t.current_zone}</span>
                        {t.previous_zone !== t.current_zone && t.previous_zone !== 'UNKNOWN' && (
                          <span className="text-[10px] text-slate-500">
                            (was {t.previous_zone})
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 capitalize font-sans text-slate-200">
                        {t.current_behavior}
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {t.movement_rate.toFixed(1)} px/s
                      </td>
                      <td className="py-3 px-4 font-bold text-rose-300">
                        {t.camera_deviation_score.toFixed(1)}
                      </td>
                      <td className="py-3 px-4 font-extrabold text-white text-sm">
                        {t.inspection_priority.toFixed(1)}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                            isAlert
                              ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse'
                              : isWatch
                              ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                              : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                          }`}
                        >
                          {t.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectTrack(t.track_id);
                          }}
                          className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-sans font-medium transition-colors"
                        >
                          Inspect
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
