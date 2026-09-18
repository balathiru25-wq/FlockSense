import React from 'react';
import { Activity, Globe, Wifi, WifiOff, Sliders } from 'lucide-react';
import { useI18n, LanguageCode } from '../i18n';

interface HeaderProps {
  online: boolean;
  fusionMode?: string;
  flockStatus?: 'NORMAL' | 'WATCH' | 'ALERT';
  demoMode: boolean;
  setDemoMode: (val: boolean) => void;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  viewMode: 'farmer' | 'technical';
  setViewMode: (mode: 'farmer' | 'technical') => void;
  onOpenLanguage: () => void;
  onOpenDevices?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  online,
  flockStatus = 'NORMAL',
  demoMode,
  setDemoMode,
  activeTab,
  setActiveTab,
  viewMode,
  setViewMode,
  onOpenLanguage,
  onOpenDevices,
}) => {
  const { t, language } = useI18n();

  const statusColors = {
    NORMAL: 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10',
    WATCH: 'text-amber-400 border-amber-500/40 bg-amber-500/10',
    ALERT: 'text-rose-400 border-rose-500/40 bg-rose-500/10 animate-pulse',
  };

  const languageLabels: Record<LanguageCode, string> = {
    en: 'English',
    ta: 'தமிழ்',
    hi: 'हिंदी',
  };

  const navItems = [
    { id: 'dashboard', label: t.navigation.commandCenter },
    { id: 'tracks', label: t.navigation.trackMonitor },
    { id: 'audio', label: t.navigation.bioacoustics },
    { id: 'alerts', label: t.navigation.alerts },
    { id: 'system', label: t.navigation.systemValidation },
  ];

  return (
    <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand & Subtitle */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 via-teal-500 to-cyan-500 p-0.5 shadow-lg shadow-emerald-950/50 shrink-0">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Activity className="w-5 h-5 text-emerald-400" />
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                  FlockSense
                </span>
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${statusColors[flockStatus]}`}>
                  {flockStatus === 'NORMAL' ? t.status.normal : flockStatus === 'WATCH' ? t.status.watch : t.status.alert}
                </span>
              </div>
              <p className="text-xs text-slate-400 font-medium">
                {language === 'ta'
                  ? 'AI கோழிப்பண்ணை ஆரம்ப எச்சரிக்கை'
                  : language === 'hi'
                  ? 'AI पोल्ट्री प्रारंभिक चेतावनी प्रणाली'
                  : 'AI Poultry Early-Warning System'}
              </p>
            </div>
          </div>

          {/* Navigation Tabs (Only in Technical View) */}
          {viewMode === 'technical' && (
            <nav className="hidden lg:flex space-x-1">
              {navItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`px-3 py-2 rounded-lg text-xs font-semibold transition-all ${
                    activeTab === item.id
                      ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </nav>
          )}

          {/* Right Status & Controls */}
          <div className="flex items-center space-x-2 sm:space-x-3">
            {/* View Mode Toggle: Farmer View <-> Technical View */}
            <button
              onClick={() => setViewMode(viewMode === 'farmer' ? 'technical' : 'farmer')}
              className={`px-2.5 sm:px-3 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center space-x-1.5 border min-h-[44px] sm:min-h-0 ${
                viewMode === 'farmer'
                  ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                  : 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
              }`}
              title="Switch between Farmer View and Technical Engineering View"
            >
              {viewMode === 'farmer' ? (
                <>
                  <span>🧑‍🌾</span>
                  <span className="hidden sm:inline">{t.system.farmerView}</span>
                </>
              ) : (
                <>
                  <Sliders className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="hidden sm:inline">{t.navigation.technical}</span>
                </>
              )}
            </button>

            {/* Devices & Gateway Button */}
            {onOpenDevices && (
              <button
                onClick={onOpenDevices}
                className="px-2.5 sm:px-3 py-1.5 rounded-xl text-xs font-bold transition-all bg-slate-900 text-slate-200 border border-slate-700/80 hover:border-emerald-500 flex items-center space-x-1.5 min-h-[44px] sm:min-h-0"
                title={t.devices.title}
              >
                <span>📡</span>
                <span className="hidden sm:inline">{t.devices.title}</span>
              </button>
            )}

            {/* Language Selector Button with Native Name */}
            <button
              onClick={onOpenLanguage}
              className="px-2.5 sm:px-3 py-1.5 rounded-xl text-xs font-bold transition-all bg-slate-900 text-slate-200 border border-slate-700/80 hover:border-emerald-500 flex items-center space-x-1.5 min-h-[44px] sm:min-h-0"
              title="Change Language / மொழியை மாற்றவும் / भाषा बदलें"
            >
              <Globe className="w-3.5 h-3.5 text-emerald-400" />
              <span>{languageLabels[language]}</span>
            </button>

            {/* Demo Toggle */}
            <button
              onClick={() => setDemoMode(!demoMode)}
              className={`hidden sm:inline-flex px-2.5 py-1.5 rounded-md text-[11px] font-semibold transition-colors border ${
                demoMode
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                  : 'bg-slate-900 text-slate-400 border-slate-800'
              }`}
              title="Toggle synthetic development demo data"
            >
              DEMO: {demoMode ? 'ON' : 'OFF'}
            </button>

            {/* Server Online/Offline status */}
            <div
              className={`flex items-center space-x-1.5 px-2.5 py-1.5 rounded-md border text-[11px] font-medium ${
                online
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                  : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
              }`}
            >
              {online ? (
                <>
                  <Wifi className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="hidden sm:inline">ONLINE</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-3.5 h-3.5 text-rose-400" />
                  <span className="hidden sm:inline">{t.system.offline}</span>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
