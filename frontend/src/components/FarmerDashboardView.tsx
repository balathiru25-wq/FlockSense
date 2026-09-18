import React, { useState } from 'react';
import { 
  Volume2, 
  MapPin, 
  Info, 
  Eye
} from 'lucide-react';
import { useI18n } from '../i18n';
import { CandidateItem, FlockStatusResponse, AlertItem } from '../types/api';
import { AudioUploadWidget } from './AudioUploadWidget';

interface FarmerDashboardViewProps {
  flockStatus: FlockStatusResponse | null;
  candidates: CandidateItem[];
  alerts: AlertItem[];
  onSelectTrack: (trackId: number) => void;
  onRefresh: () => void;
  online: boolean;
  onOpenDeviceManager?: () => void;
  onOpenSetupModal?: () => void;
}

export const FarmerDashboardView: React.FC<FarmerDashboardViewProps> = ({
  flockStatus,
  candidates,
  alerts,
  onSelectTrack,
  onOpenDeviceManager,
  onOpenSetupModal,
}) => {
  const { t, speak, canSpeak, isSpeaking, stopSpeech } = useI18n();
  const [activeFarmerTab, setActiveFarmerTab] = useState<'home' | 'flock' | 'audio' | 'alerts' | 'help'>('home');

  const status = flockStatus?.flock_status || 'NORMAL';
  const audioContext = flockStatus?.global_audio || null;
  const audioScore = audioContext?.score ?? 0;
  const isAudioUnusual = audioScore >= 35;

  // Status visual mapping
  const statusConfig = {
    NORMAL: {
      label: t.status.allGood,
      desc: t.status.allGoodDesc,
      sub: t.status.allGoodSub,
      bg: 'from-emerald-950/40 to-slate-900',
      border: 'border-emerald-500/40',
      text: 'text-emerald-400',
      badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
      icon: '🟢',
      speechText: `${t.status.allGood}. ${t.status.allGoodDesc}`,
    },
    WATCH: {
      label: t.status.keepWatching,
      desc: t.status.keepWatchingDesc,
      sub: t.status.keepWatchingSub,
      bg: 'from-amber-950/40 to-slate-900',
      border: 'border-amber-500/40',
      text: 'text-amber-400',
      badge: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
      icon: '🟡',
      speechText: `${t.status.keepWatching}. ${t.status.keepWatchingDesc}`,
    },
    ALERT: {
      label: t.status.checkNow,
      desc: t.status.checkNowDesc,
      sub: t.status.checkNowSub,
      bg: 'from-rose-950/50 to-slate-900',
      border: 'border-rose-500/50',
      text: 'text-rose-400',
      badge: 'bg-rose-500/20 text-rose-200 border-rose-500/50 animate-pulse',
      icon: '🔴',
      speechText: `${t.status.checkNow}. ${t.status.checkNowDesc}`,
    },
  }[status];

  // Primary top bird if available
  const topBird = candidates.length > 0 ? candidates[0] : null;

  const handleSpeakStatus = () => {
    if (isSpeaking) {
      stopSpeech();
      return;
    }
    let fullSpoken = statusConfig.speechText;
    if (topBird && status !== 'NORMAL') {
      const birdZoneNum = topBird.current_zone ? topBird.current_zone.replace(/[^0-9]/g, '') : '2';
      const birdSpeech = t.birds.listenMessage
        .replace('{{id}}', topBird.track_id.toString())
        .replace('{{zone}}', birdZoneNum);
      fullSpoken += ` ${birdSpeech}`;
    }
    speak(fullSpoken);
  };

  const handleSpeakBird = (cand: CandidateItem) => {
    const birdZoneNum = cand.current_zone ? cand.current_zone.replace(/[^0-9]/g, '') : '1';
    const msg = t.birds.listenMessage
      .replace('{{id}}', cand.track_id.toString())
      .replace('{{zone}}', birdZoneNum);
    speak(msg);
  };

  return (
    <div className="space-y-6">
      {/* Farmer Sub-navigation bar (Touch-friendly 48px targets) */}
      <div className="grid grid-cols-5 gap-2 p-1.5 bg-slate-900/90 rounded-2xl border border-slate-800 shadow-md">
        {[
          { id: 'home', label: t.navigation.home, icon: '🏠' },
          { id: 'flock', label: t.navigation.flock, icon: '🐔' },
          { id: 'audio', label: t.navigation.audio, icon: '🎤' },
          { id: 'alerts', label: t.navigation.alerts, icon: '🔔' },
          { id: 'help', label: t.actions.whatToDo, icon: '📋' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveFarmerTab(tab.id as any)}
            className={`min-h-[48px] py-2 px-1 rounded-xl text-xs sm:text-sm font-bold flex flex-col sm:flex-row items-center justify-center space-y-1 sm:space-y-0 sm:space-x-2 transition-all select-none ${
              activeFarmerTab === tab.id
                ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-950/40'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <span className="text-base sm:text-lg">{tab.icon}</span>
            <span className="truncate">{tab.label}</span>
          </button>
        ))}
      </div>

      {/* VIEW: HOME */}
      {activeFarmerTab === 'home' && (
        <div className="space-y-6">
          {/* Main Giant Status Card (Low-Literacy Friendly) */}
          <div
            className={`rounded-3xl border-2 ${statusConfig.border} bg-gradient-to-b ${statusConfig.bg} p-6 sm:p-8 shadow-2xl relative overflow-hidden transition-all`}
          >
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="space-y-2">
                <div className="flex items-center space-x-3">
                  <span className="text-3xl sm:text-4xl">{statusConfig.icon}</span>
                  <span className={`text-2xl sm:text-4xl font-black tracking-tight ${statusConfig.text}`}>
                    {statusConfig.label}
                  </span>
                </div>
                <p className="text-lg sm:text-xl font-semibold text-white">
                  {statusConfig.desc}
                </p>
                <p className="text-sm text-slate-300">
                  {statusConfig.sub}
                </p>
              </div>

              {/* Big Touch-Friendly Listen Button */}
              {canSpeak && (
                <button
                  onClick={handleSpeakStatus}
                  className="w-full sm:w-auto min-h-[52px] px-6 py-3 rounded-2xl bg-slate-900 border-2 border-slate-700 hover:border-emerald-500 text-white font-bold text-base flex items-center justify-center space-x-3 shadow-xl active:scale-95 transition-all shrink-0"
                >
                  <Volume2 className={`w-6 h-6 text-emerald-400 ${isSpeaking ? 'animate-bounce' : ''}`} />
                  <span>{isSpeaking ? t.system.close : t.system.listen}</span>
                </button>
              )}
            </div>
          </div>

          {/* Quick Bird Priority Card */}
          {topBird && status !== 'NORMAL' && (
            <div className="rounded-3xl border-2 border-rose-500/40 bg-slate-900/90 p-6 shadow-xl space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <span className="text-3xl">🐔</span>
                  <div>
                    <h3 className="text-xl sm:text-2xl font-extrabold text-white">
                      {t.birds.birdNumber.replace('{{id}}', topBird.track_id.toString())}
                    </h3>
                    <span className="inline-block text-xs font-bold px-2.5 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/40 mt-1">
                      {t.status.checkNow}
                    </span>
                  </div>
                </div>

                {canSpeak && (
                  <button
                    onClick={() => handleSpeakBird(topBird)}
                    className="p-3 rounded-2xl bg-slate-950 border border-slate-800 text-slate-300 hover:text-emerald-400 min-w-[48px] min-h-[48px] flex items-center justify-center"
                    title={t.system.listen}
                  >
                    <Volume2 className="w-6 h-6" />
                  </button>
                )}
              </div>

              {/* Key Simple Information */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 flex items-center space-x-3">
                  <MapPin className="w-6 h-6 text-emerald-400 shrink-0" />
                  <div>
                    <span className="text-xs text-slate-400 block">{t.birds.currentLocation}</span>
                    <span className="text-lg font-bold text-white">
                      {t.birds.zone.replace('{{id}}', topBird.current_zone ? topBird.current_zone.replace(/[^0-9]/g, '') : '2')}
                    </span>
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 flex items-center space-x-3">
                  <Eye className="w-6 h-6 text-cyan-400 shrink-0" />
                  <div>
                    <span className="text-xs text-slate-400 block">{t.birds.currentActivity}</span>
                    <span className="text-sm sm:text-base font-bold text-white">
                      {topBird.camera_deviation_score >= 70 ? t.birds.movingLess : t.birds.sittingProlonged}
                    </span>
                  </div>
                </div>
              </div>

              <button
                onClick={() => onSelectTrack(topBird.track_id)}
                className="w-full min-h-[52px] rounded-2xl bg-emerald-600 hover:bg-emerald-500 text-white font-extrabold text-base flex items-center justify-center space-x-2 shadow-lg transition-all"
              >
                <span>{t.birds.viewBird}</span>
              </button>
            </div>
          )}

          {/* YOUR SHED Summary Card with Birds, Zones, and Online Status */}
          <div className="rounded-3xl border-2 border-emerald-500/40 bg-slate-900/95 p-5 sm:p-6 shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div className="flex items-center space-x-3">
                <span className="text-3xl">🏠</span>
                <div>
                  <h4 className="text-lg sm:text-xl font-black text-white">
                    {t.setup.yourShed}
                  </h4>
                  <div className="flex items-center space-x-3 text-xs sm:text-sm text-slate-300 mt-0.5">
                    <span className="text-emerald-400 font-bold">250 birds</span>
                    <span>•</span>
                    <span className="text-cyan-400 font-bold">4 zones</span>
                    <span>•</span>
                    <span className="text-slate-400">Broiler Shed A</span>
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap gap-2 w-full sm:w-auto">
                {onOpenSetupModal && (
                  <button
                    onClick={onOpenSetupModal}
                    className="flex-1 sm:flex-none px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold border border-slate-700 flex items-center justify-center space-x-1.5 min-h-[40px]"
                  >
                    <span>🔄 {t.setup.startNewFlock}</span>
                  </button>
                )}
                {onOpenDeviceManager && (
                  <button
                    onClick={onOpenDeviceManager}
                    className="flex-1 sm:flex-none px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold shadow-md min-h-[40px] flex items-center justify-center space-x-1.5"
                  >
                    <span>⚙️ {t.setup.viewShed}</span>
                  </button>
                )}
              </div>
            </div>

            {/* Live Camera and Microphone Status Pills */}
            <div className="grid grid-cols-2 gap-3 pt-1 text-xs">
              <div className="p-3 rounded-2xl bg-slate-950/80 border border-slate-800 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span>📷</span>
                  <span className="text-slate-300 font-semibold">{t.devices.cameras}</span>
                </div>
                <span className="font-mono text-emerald-400 font-bold">4 / 4 Online</span>
              </div>
              <div className="p-3 rounded-2xl bg-slate-950/80 border border-slate-800 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span>🎤</span>
                  <span className="text-slate-300 font-semibold">{t.devices.microphones}</span>
                </div>
                <span className="font-mono text-emerald-400 font-bold">2 / 2 Online</span>
              </div>
            </div>
          </div>

          {/* Quick Sound Context Preview */}
          <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center space-x-4">
              <span className="text-3xl">🎤</span>
              <div>
                <h4 className="text-base sm:text-lg font-bold text-white">{t.audio.title}</h4>
                <p className={`text-sm sm:text-base font-semibold ${isAudioUnusual ? 'text-rose-400' : 'text-emerald-400'}`}>
                  {isAudioUnusual ? t.audio.unusual : t.audio.normal}
                </p>
                <p className="text-xs text-slate-400 mt-1 max-w-lg">
                  {t.audio.safetyDisclaimer}
                </p>
              </div>
            </div>
            <button
              onClick={() => setActiveFarmerTab('audio')}
              className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs sm:text-sm font-bold shrink-0 min-h-[44px]"
            >
              {t.audio.checkRecording}
            </button>
          </div>

          {/* 5 Farmer Action Steps Checklist */}
          <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-lg font-bold text-white flex items-center space-x-2">
                <span>📋</span>
                <span>{t.actions.whatShouldIDo}</span>
              </h4>
              {canSpeak && (
                <button
                  onClick={() =>
                    speak(
                      `${t.actions.whatShouldIDo}. ${t.actions.step1} ${t.actions.step2} ${t.actions.step3} ${t.actions.step4} ${t.actions.step5}`
                    )
                  }
                  className="px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-300 hover:text-emerald-400 text-xs font-semibold flex items-center space-x-1.5"
                >
                  <Volume2 className="w-4 h-4" />
                  <span>{t.system.listen}</span>
                </button>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                { icon: '🔍', text: t.actions.step1 },
                { icon: '🌾', text: t.actions.step2 },
                { icon: '👀', text: t.actions.step3 },
                { icon: '📊', text: t.actions.step4 },
                { icon: '🩺', text: t.actions.step5 },
              ].map((step, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-2xl bg-slate-950/60 border border-slate-800/80 flex items-center space-x-3 text-sm text-slate-200"
                >
                  <span className="text-xl">{step.icon}</span>
                  <span className="font-medium">{step.text}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* VIEW: FLOCK (All Birds to Check) */}
      {activeFarmerTab === 'flock' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-extrabold text-white flex items-center space-x-2">
                <span>🐔</span>
                <span>{t.birds.toCheck}</span>
              </h3>
              <p className="text-xs text-slate-400 mt-1">{t.birds.toCheckSubtitle}</p>
            </div>
            <span className="px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs font-mono text-slate-300">
              {candidates.length}
            </span>
          </div>

          {candidates.length === 0 ? (
            <div className="p-8 text-center rounded-3xl border border-dashed border-slate-800 bg-slate-900/40 space-y-2">
              <span className="text-4xl">🟢</span>
              <h4 className="text-lg font-bold text-white">{t.birds.noBirdsNeedAttention}</h4>
              <p className="text-xs text-slate-400">{t.birds.noBirdsSub}</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {candidates.map((cand) => {
                const isAlert = cand.status === 'ALERT';
                const zoneNum = cand.current_zone ? cand.current_zone.replace(/[^0-9]/g, '') : '1';
                return (
                  <div
                    key={cand.track_id}
                    className={`rounded-3xl border-2 p-5 space-y-4 bg-slate-900/90 transition-all ${
                      isAlert ? 'border-rose-500/50 bg-rose-950/10' : 'border-amber-500/40 bg-amber-950/10'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <span className="text-2xl">🐔</span>
                        <div>
                          <h4 className="text-lg font-extrabold text-white">
                            {t.birds.birdNumber.replace('{{id}}', cand.track_id.toString())}
                          </h4>
                          <span
                            className={`inline-block text-xs font-bold px-2 py-0.5 rounded-full ${
                              isAlert ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                            }`}
                          >
                            {isAlert ? t.status.checkNow : t.status.keepWatching}
                          </span>
                        </div>
                      </div>

                      {canSpeak && (
                        <button
                          onClick={() => handleSpeakBird(cand)}
                          className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-300 hover:text-emerald-400 min-w-[44px] min-h-[44px] flex items-center justify-center"
                          title={t.system.listen}
                        >
                          <Volume2 className="w-5 h-5" />
                        </button>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                        <span className="text-slate-400 block">{t.birds.currentLocation}</span>
                        <span className="text-sm font-bold text-white">
                          {t.birds.zone.replace('{{id}}', zoneNum)}
                        </span>
                      </div>
                      <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                        <span className="text-slate-400 block">{t.birds.currentActivity}</span>
                        <span className="text-sm font-bold text-white">
                          {cand.camera_deviation_score >= 70 ? t.birds.movingLess : t.birds.sittingProlonged}
                        </span>
                      </div>
                    </div>

                    <button
                      onClick={() => onSelectTrack(cand.track_id)}
                      className="w-full min-h-[46px] rounded-xl bg-slate-800 hover:bg-emerald-600 text-white text-xs sm:text-sm font-bold transition-colors flex items-center justify-center"
                    >
                      {t.birds.viewBird}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* VIEW: AUDIO */}
      {activeFarmerTab === 'audio' && (
        <div className="space-y-6 max-w-2xl mx-auto">
          <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-6 space-y-4">
            <div className="flex items-center space-x-3">
              <span className="text-3xl">🎤</span>
              <div>
                <h3 className="text-xl font-extrabold text-white">{t.audio.title}</h3>
                <p className="text-xs text-slate-400">{t.audio.subtitle}</p>
              </div>
            </div>

            <div
              className={`p-5 rounded-2xl border ${
                isAudioUnusual ? 'border-rose-500/40 bg-rose-950/20 text-rose-300' : 'border-emerald-500/40 bg-emerald-950/20 text-emerald-300'
              } flex items-center justify-between`}
            >
              <div className="space-y-1">
                <span className="text-sm sm:text-base font-bold block">
                  {isAudioUnusual ? t.audio.unusual : t.audio.normal}
                </span>
                <span className="text-xs text-slate-400">
                  {isAudioUnusual ? t.audio.elevatedSummary : t.audio.statusSummary}
                </span>
              </div>
              {canSpeak && (
                <button
                  onClick={() =>
                    speak(
                      isAudioUnusual
                        ? `${t.audio.unusual}. ${t.audio.elevatedSummary}`
                        : `${t.audio.normal}. ${t.audio.statusSummary}`
                    )
                  }
                  className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-300 hover:text-emerald-400 shrink-0"
                >
                  <Volume2 className="w-5 h-5" />
                </button>
              )}
            </div>

            {/* Disclaimer reminder */}
            <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start space-x-2">
              <Info className="w-5 h-5 shrink-0 mt-0.5" />
              <span>{t.audio.safetyDisclaimer} {t.audio.safetyNote}</span>
            </div>
          </div>

          {/* Audio Upload Widget */}
          <AudioUploadWidget />
        </div>
      )}

      {/* VIEW: ALERTS */}
      {activeFarmerTab === 'alerts' && (
        <div className="space-y-4 max-w-2xl mx-auto">
          <div className="flex items-center space-x-3">
            <span className="text-3xl">🔔</span>
            <div>
              <h3 className="text-xl font-extrabold text-white">{t.alerts.title}</h3>
              <p className="text-xs text-slate-400">{t.alerts.subtitle}</p>
            </div>
          </div>

          {alerts.length === 0 ? (
            <div className="p-8 text-center rounded-3xl border border-dashed border-slate-800 bg-slate-900/40 space-y-2">
              <span className="text-4xl">🟢</span>
              <h4 className="text-lg font-bold text-white">{t.alerts.noActiveAlerts}</h4>
              <p className="text-xs text-slate-400">{t.alerts.noAlertsSub}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {alerts.map((alert) => (
                <div
                  key={alert.alert_id}
                  className="p-4 rounded-2xl border border-slate-800 bg-slate-900/80 flex items-start justify-between gap-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="text-lg">
                        {alert.level === 'ALERT' ? '🔴' : '🟡'}
                      </span>
                      <span className="text-sm font-bold text-white">
                        {alert.level === 'ALERT' ? t.status.checkNow : t.status.keepWatching}
                      </span>
                      {alert.track_id && (
                        <span className="text-xs text-cyan-300 font-mono">
                          {t.birds.birdNumber.replace('{{id}}', alert.track_id.toString())}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-300">{alert.message}</p>
                    <p className="text-[11px] text-emerald-400 font-medium">{alert.recommendation}</p>
                  </div>
                  {canSpeak && (
                    <button
                      onClick={() => speak(`${alert.message}. ${alert.recommendation}`)}
                      className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-400 hover:text-emerald-400 shrink-0"
                    >
                      <Volume2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* VIEW: HELP / WHAT TO DO */}
      {activeFarmerTab === 'help' && (
        <div className="space-y-4 max-w-2xl mx-auto">
          <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-6 space-y-4">
            <h3 className="text-xl font-extrabold text-white flex items-center space-x-2">
              <span>📋</span>
              <span>{t.actions.whatShouldIDo}</span>
            </h3>

            <div className="space-y-3 pt-2">
              {[
                { title: t.actions.step1, desc: t.birds.toCheckSubtitle, icon: '🐔' },
                { title: t.actions.step2, desc: 'Ensure water nipples and feed pans are flowing clean.', icon: '💧' },
                { title: t.actions.step3, desc: 'Watch for head drooping, heavy panting, or wing sagging.', icon: '👀' },
                { title: t.actions.step4, desc: 'Check back in 15–30 minutes to see if movement returns.', icon: '⏱️' },
                { title: t.actions.step5, desc: 'Early consultation prevents flock-wide transmission.', icon: '🩺' },
              ].map((item, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 flex items-start space-x-3.5"
                >
                  <span className="text-2xl mt-0.5">{item.icon}</span>
                  <div>
                    <h4 className="text-base font-bold text-white">{item.title}</h4>
                    <p className="text-xs text-slate-400 mt-0.5">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="pt-4 border-t border-slate-800 text-center">
              <p className="text-xs text-slate-400">{t.actions.disclaimer}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
