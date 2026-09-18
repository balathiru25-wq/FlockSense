import React, { useEffect, useState, useCallback } from 'react';
import { Header } from './components/Header';
import { FlockStatusCard } from './components/FlockStatusCard';
import { GlobalAudioCard } from './components/GlobalAudioCard';
import { AudioUploadWidget } from './components/AudioUploadWidget';
import { ShedZoneMap } from './components/ShedZoneMap';
import { TopCandidatesList } from './components/TopCandidatesList';
import { TrackDetailModal } from './components/TrackDetailModal';
import { AlertsFeed } from './components/AlertsFeed';
import { SystemStatusPanel } from './components/SystemStatusPanel';
import { TracksView } from './components/TracksView';
import { DemoController } from './components/DemoController';
import { FarmerDashboardView } from './components/FarmerDashboardView';
import { LanguageSelectionModal } from './components/LanguageSelectionModal';
import { DeviceManagerModal } from './components/DeviceManagerModal';
import { SmartFarmSetupModal } from './components/SmartFarmSetupModal';

import { useI18n } from './i18n';
import { api } from './api/flocksense';
import {
  FlockStatusResponse,
  CandidateItem,
  TrackSummaryItem,
  AlertItem,
  SystemInfoResponse,
  HealthResponse,
  AudioAnalysisResponse,
} from './types/api';

export function App() {
  const { t, isFirstLaunch, openLanguageModal, language } = useI18n();

  const [online, setOnline] = useState<boolean>(true);
  const [demoMode, setDemoMode] = useState<boolean>(true);
  const [isPresentationMode, setIsPresentationMode] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [viewMode, setViewMode] = useState<'farmer' | 'technical'>('farmer'); // Default FARMER VIEW
  const [isLanguageModalOpen, setIsLanguageModalOpen] = useState<boolean>(false);
  const [isDeviceModalOpen, setIsDeviceModalOpen] = useState<boolean>(false);
  const [isSetupModalOpen, setIsSetupModalOpen] = useState<boolean>(false);

  // Backend state
  const [flockStatus, setFlockStatus] = useState<FlockStatusResponse | null>(null);
  const [candidates, setCandidates] = useState<CandidateItem[]>([]);
  const [tracks, setTracks] = useState<TrackSummaryItem[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [systemInfo, setSystemInfo] = useState<SystemInfoResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [selectedTrackId, setSelectedTrackId] = useState<number | null>(null);

  // Data fetching poll
  const refreshData = useCallback(async () => {
    try {
      const [hRes, sRes, fRes, cRes, tRes, aRes] = await Promise.all([
        api.getHealth().catch(() => null),
        api.getSystemInfo().catch(() => null),
        api.getFlockStatus().catch(() => null),
        api.getCandidates(10).catch(() => null),
        api.getTracks().catch(() => null),
        api.getAlerts('ALL', 20).catch(() => null),
      ]);

      if (hRes) {
        setOnline(true);
        setHealth(hRes);
      } else {
        setOnline(false);
      }

      if (sRes) setSystemInfo(sRes);
      if (fRes) setFlockStatus(fRes);
      setCandidates(cRes?.candidates || []);
      setTracks(tRes?.tracks || []);
      if (aRes) setAlerts(aRes.alerts || []);
    } catch {
      setOnline(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshData();
    const interval = setInterval(refreshData, 3000);
    return () => clearInterval(interval);
  }, [refreshData]);

  const handleAudioAnalysisComplete = (_data: AudioAnalysisResponse) => {
    refreshData();
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* First-Launch & On-Demand Language Picker Modal */}
      <LanguageSelectionModal
        isOpen={isFirstLaunch || isLanguageModalOpen}
        onClose={() => setIsLanguageModalOpen(false)}
        forceMandatory={isFirstLaunch}
      />

      {/* Header */}
      <Header
        online={online}
        fusionMode={systemInfo?.fusion_mode}
        flockStatus={flockStatus?.flock_status || 'NORMAL'}
        demoMode={demoMode}
        setDemoMode={setDemoMode}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        viewMode={viewMode}
        setViewMode={setViewMode}
        onOpenLanguage={() => setIsLanguageModalOpen(true)}
        onOpenDevices={() => setIsDeviceModalOpen(true)}
      />

      {/* Demo Banner */}
      {demoMode && (
        <div className="bg-amber-500/10 border-b border-amber-500/30 text-amber-300 px-4 py-1.5 text-center text-xs font-mono font-medium flex items-center justify-center space-x-2">
          <span>⚠️</span>
          <span>{t.system.demoScenario}: {t.system.demoNotice}</span>
        </div>
      )}

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-3 sm:px-6 lg:px-8 py-4 sm:py-6 space-y-6">
        {/* Offline Warning banner if backend is unreachable */}
        {!online && (
          <div className="rounded-2xl bg-rose-950/40 border border-rose-800/80 p-4 text-rose-200 text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-lg">
            <div>
              <strong className="font-bold block text-rose-300">{t.system.offline}</strong>
              <span>{t.system.offlineDesc}</span>
            </div>
            <button
              onClick={refreshData}
              className="px-4 py-2 rounded-xl bg-rose-700 hover:bg-rose-600 text-white font-bold transition-colors shrink-0 min-h-[44px]"            >
              {t.system.tryAgain}
            </button>
          </div>
        )}

        {/* Demo Controller always accessible for hackathon verification */}
        {demoMode && (
          <DemoController
            onStateChanged={refreshData}
            isPresentationMode={isPresentationMode}
            setIsPresentationMode={setIsPresentationMode}
          />
        )}

        {/* VIEW MODE 1: FARMER VIEW (DEFAULT - MULTILINGUAL & LOW LITERACY ACCESSIBLE) */}
        {viewMode === 'farmer' && (
          <FarmerDashboardView
            flockStatus={flockStatus}
            candidates={candidates}
            alerts={alerts}
            onSelectTrack={(id) => setSelectedTrackId(id)}
            onRefresh={refreshData}
            online={online}
            onOpenDeviceManager={() => setIsDeviceModalOpen(true)}
            onOpenSetupModal={() => setIsSetupModalOpen(true)}
          />
        )}

        {/* VIEW MODE 2: TECHNICAL / COMMAND CENTER VIEW */}
        {viewMode === 'technical' && (
          <>
            {activeTab === 'dashboard' && (
              <div className="space-y-6">
                {/* Top Cards Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <FlockStatusCard statusData={flockStatus} loading={loading} />
                  <GlobalAudioCard audioContext={flockStatus?.global_audio || null} loading={loading} />
                </div>

                {/* Middle Monitoring Grid: Shed Map & Top Candidates */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div className="lg:col-span-2 space-y-6">
                    <ShedZoneMap
                      tracks={tracks}
                      onSelectTrack={(id) => setSelectedTrackId(id)}
                      selectedTrackId={selectedTrackId}
                    />
                    <AudioUploadWidget onAnalysisComplete={handleAudioAnalysisComplete} />
                  </div>

                  <div className="space-y-6">
                    <TopCandidatesList
                      candidates={candidates}
                      onSelectTrack={(id) => setSelectedTrackId(id)}
                      selectedTrackId={selectedTrackId}
                      loading={loading}
                    />
                  </div>
                </div>

                {/* Bottom Section: Alerts & System Panel */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <AlertsFeed alerts={alerts} loading={loading} />
                  <SystemStatusPanel systemInfo={systemInfo} health={health} />
                </div>
              </div>
            )}

            {activeTab === 'tracks' && (
              <div className="space-y-6">
                <TracksView
                  tracks={tracks}
                  onSelectTrack={(id) => setSelectedTrackId(id)}
                  loading={loading}
                />
              </div>
            )}

            {activeTab === 'audio' && (
              <div className="space-y-6 max-w-3xl mx-auto">
                <GlobalAudioCard audioContext={flockStatus?.global_audio || null} loading={loading} />
                <AudioUploadWidget onAnalysisComplete={handleAudioAnalysisComplete} />
              </div>
            )}

            {activeTab === 'alerts' && (
              <div className="space-y-6 max-w-4xl mx-auto">
                <AlertsFeed alerts={alerts} loading={loading} />
              </div>
            )}

            {activeTab === 'system' && (
              <div className="space-y-6 max-w-4xl mx-auto">
                <SystemStatusPanel systemInfo={systemInfo} health={health} />
              </div>
            )}
          </>
        )}
      </main>

      {/* Individual Track Detail Modal */}
      <TrackDetailModal
        trackId={selectedTrackId}
        onClose={() => setSelectedTrackId(null)}
      />

      {/* Sensor Gateway Device Management Modal */}
      <DeviceManagerModal
        isOpen={isDeviceModalOpen}
        onClose={() => setIsDeviceModalOpen(false)}
        onDevicesUpdated={refreshData}
      />

      {/* Smart Farm Setup Modal (First-time & New Flock Onboarding) */}
      <SmartFarmSetupModal
        isOpen={isSetupModalOpen}
        onClose={() => setIsSetupModalOpen(false)}
        onSetupComplete={refreshData}
      />

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>
            FlockSense © 2026 — AI-Powered Poultry Early-Warning Monitoring
          </span>
          <span className="text-[11px] text-slate-600 max-w-xl text-center sm:text-right">
            {t.actions.disclaimer}
          </span>
        </div>
      </footer>
    </div>
  );
}

export default App;
