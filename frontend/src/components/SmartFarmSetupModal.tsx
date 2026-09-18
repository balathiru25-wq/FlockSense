import React, { useState, useEffect, useCallback } from 'react';
import { 
  Volume2, 
  Check, 
  ArrowRight, 
  ArrowLeft, 
  RefreshCw, 
  Plus, 
  Minus, 
  AlertCircle, 
  X, 
  MapPin, 
  CheckCircle2, 
  Sliders,
  Radio,
  Eye,
  Camera,
  Mic
} from 'lucide-react';
import { useI18n, LanguageCode } from '../i18n';
import { api } from '../api/flocksense';
import { 
  DeviceResponse, 
  ZoneItem, 
  FlockSetupResponse, 
  SetupStatusResponse 
} from '../types/api';

interface SmartFarmSetupModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSetupComplete: () => void;
  initialFlockSize?: number;
}

export const SmartFarmSetupModal: React.FC<SmartFarmSetupModalProps> = ({
  isOpen,
  onClose,
  onSetupComplete,
  initialFlockSize = 250,
}) => {
  const { t, language, setLanguage, speak, canSpeak } = useI18n();

  // Step state (1: Language, 2: Flock, 3: Recommendation, 4: Zones Created, 5: Connect & Assign, 6: Check, 7: Start)
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [flockSize, setFlockSize] = useState<number>(initialFlockSize);
  const [shedLength, setShedLength] = useState<string>('20');
  const [shedWidth, setShedWidth] = useState<string>('8');
  const [showDimensions, setShowDimensions] = useState<boolean>(true);

  // Recommendations
  const [recData, setRecData] = useState<FlockSetupResponse | null>(null);
  const [customCams, setCustomCams] = useState<number>(4);
  const [customMics, setCustomMics] = useState<number>(2);
  const [customZones, setCustomZones] = useState<number>(4);
  const [isAdjusting, setIsAdjusting] = useState<boolean>(false);

  // Devices & Zones
  const [zones, setZones] = useState<ZoneItem[]>([]);
  const [devices, setDevices] = useState<DeviceResponse[]>([]);
  const [setupStatus, setSetupStatus] = useState<SetupStatusResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Load existing zones & devices
  const refreshSetupData = useCallback(async () => {
    try {
      const [zRes, dRes, sRes] = await Promise.all([
        api.getZones().catch(() => ({ zones: [], count: 0 })),
        api.getDevices().catch(() => []),
        api.getSetupStatus().catch(() => null),
      ]);
      setZones(zRes.zones || []);
      setDevices(dRes || []);
      if (sRes) {
        setSetupStatus(sRes);
        if (sRes.farm_setup?.flock_size) {
          setFlockSize(sRes.farm_setup.flock_size);
        }
      }
    } catch (e) {
      console.error('Failed to load setup data', e);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      refreshSetupData();
    }
  }, [isOpen, refreshSetupData]);

  if (!isOpen) return null;

  // STEP 1: Select Language
  const handleSelectLanguage = (lang: LanguageCode) => {
    setLanguage(lang);
    setCurrentStep(2);
  };

  // STEP 2: Submit Flock size
  const handleFlockSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (flockSize <= 0) return;
    setLoading(true);
    setActionMessage(null);
    try {
      const l = showDimensions && shedLength ? parseFloat(shedLength) : undefined;
      const w = showDimensions && shedWidth ? parseFloat(shedWidth) : undefined;
      const res = await api.submitFlockInfo({
        flock_size: flockSize,
        shed_length_m: l,
        shed_width_m: w,
      });
      setRecData(res);
      setCustomCams(res.recommendation.cameras);
      setCustomMics(res.recommendation.microphones);
      setCustomZones(res.recommendation.zones);
      setCurrentStep(3);

      if (canSpeak) {
        const speakTxt = `${flockSize} ${t.setup.birdsCount.replace('{{count}}', '')}. ${res.recommendation.cameras} ${t.setup.recommendedCameras}, ${res.recommendation.microphones} ${t.setup.recommendedMics}.`;
        speak(speakTxt);
      }
    } catch (err: any) {
      setActionMessage(err.message || 'Failed to submit flock info');
    } finally {
      setLoading(false);
    }
  };

  // STEP 3: Confirm Setup & Generate Zones
  const handleConfirmSetup = async (useManual: boolean = false) => {
    setLoading(true);
    setActionMessage(null);
    try {
      const cams = useManual ? customCams : (recData?.recommendation.cameras || 4);
      const mics = useManual ? customMics : (recData?.recommendation.microphones || 2);
      const zns = useManual ? customZones : (recData?.recommendation.zones || 4);

      const res = await api.confirmSetup({
        cameras: cams,
        microphones: mics,
        zones: zns,
        recreate_zones: true,
      });

      setZones(res.zones || []);
      // Automatically run auto-assign
      await api.autoAssignDevices().catch(() => null);
      await refreshSetupData();
      setCurrentStep(4);
    } catch (err: any) {
      setActionMessage(err.message || 'Failed to confirm setup');
    } finally {
      setLoading(false);
    }
  };

  // Auto assign devices
  const handleAutoAssign = async () => {
    setLoading(true);
    try {
      await api.autoAssignDevices();
      await refreshSetupData();
      setActionMessage('Devices automatically assigned across monitoring zones.');
    } catch (err: any) {
      setActionMessage(err.message || 'Auto assignment failed');
    } finally {
      setLoading(false);
    }
  };

  // Change camera or mic zone
  const handleDeviceZoneChange = async (deviceId: string, newZoneId: string, currentZones: string[], isMulti: boolean = false) => {
    try {
      let updated: string[];
      if (isMulti) {
        if (currentZones.includes(newZoneId)) {
          updated = currentZones.filter(z => z !== newZoneId);
          if (updated.length === 0) updated = [newZoneId];
        } else {
          updated = [...currentZones, newZoneId];
        }
      } else {
        updated = [newZoneId];
      }
      await api.updateDeviceZones(deviceId, updated);
      await refreshSetupData();
    } catch (err: any) {
      console.error(err);
    }
  };

  // Connect All
  const handleConnectAll = async () => {
    setLoading(true);
    try {
      await api.connectAllDevices();
      await refreshSetupData();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Finish Setup & Start Monitoring
  const handleStartMonitoring = async () => {
    setLoading(true);
    try {
      await api.startMonitoringSetup();
      onSetupComplete();
      onClose();
    } catch (err: any) {
      setActionMessage(err.message || 'Failed to start monitoring');
    } finally {
      setLoading(false);
    }
  };

  const cameras = devices.filter(d => d.has_video);
  const microphones = devices.filter(d => d.has_audio);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-950/85 backdrop-blur-md overflow-y-auto">
      <div className="relative w-full max-w-4xl bg-slate-900 border-2 border-emerald-500/50 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        
        {/* Header Bar */}
        <div className="p-5 border-b border-slate-800 bg-slate-950/70 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 p-0.5 shadow-lg">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center text-xl">
                🧑‍🌾
              </div>
            </div>
            <div>
              <h2 className="text-lg sm:text-xl font-black text-white tracking-tight">
                {t.setup.title}
              </h2>
              <p className="text-xs text-slate-400">
                FlockSense Smart Farm Onboarding
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Step Progress Pills */}
        <div className="px-5 py-2.5 bg-slate-950/40 border-b border-slate-800/80 flex items-center space-x-2 overflow-x-auto text-xs font-bold select-none">
          {[
            { step: 1, label: '1. Language' },
            { step: 2, label: '2. Flock' },
            { step: 3, label: '3. Sensors' },
            { step: 4, label: '4. Zones' },
            { step: 5, label: '5. Devices' },
            { step: 6, label: '6. Check' },
          ].map(s => (
            <div
              key={s.step}
              className={`px-3 py-1 rounded-full whitespace-nowrap transition-all ${
                currentStep === s.step
                  ? 'bg-emerald-500 text-slate-950 shadow-md'
                  : currentStep > s.step
                  ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-800/60'
                  : 'bg-slate-800/50 text-slate-500'
              }`}
            >
              {currentStep > s.step ? `✓ ${s.label.split('. ')[1]}` : s.label}
            </div>
          ))}
        </div>

        {/* Action Error / Status Toast */}
        {actionMessage && (
          <div className="px-5 py-2 text-xs bg-amber-500/10 border-b border-amber-500/30 text-amber-300 flex items-center justify-between">
            <span>{actionMessage}</span>
            <button onClick={() => setActionMessage(null)}>
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Modal Body: Active Step */}
        <div className="p-5 sm:p-8 overflow-y-auto flex-1 space-y-6">

          {/* ==================================================== */}
          {/* STEP 1: CHOOSE LANGUAGE                              */}
          {/* ==================================================== */}
          {currentStep === 1 && (
            <div className="max-w-xl mx-auto space-y-6 text-center py-4">
              <div className="text-4xl">🌐</div>
              <h3 className="text-2xl font-black text-white">
                {t.setup.step1Title}
              </h3>
              <p className="text-sm text-slate-400">
                Select your preferred language / மொழியைத் தேர்ந்தெடுக்கவும் / अपनी भाषा चुनें
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4">
                {[
                  { code: 'en', native: 'English', sub: 'Default' },
                  { code: 'ta', native: 'தமிழ்', sub: 'Tamil' },
                  { code: 'hi', native: 'हिंदी', sub: 'Hindi' },
                ].map(l => (
                  <button
                    key={l.code}
                    onClick={() => handleSelectLanguage(l.code as LanguageCode)}
                    className={`p-5 rounded-2xl border-2 text-center transition-all flex flex-col items-center justify-center space-y-2 active:scale-95 ${
                      language === l.code
                        ? 'border-emerald-500 bg-emerald-950/40 text-emerald-300 shadow-xl'
                        : 'border-slate-800 bg-slate-900 text-white hover:border-slate-700'
                    }`}
                  >
                    <span className="text-2xl font-extrabold">{l.native}</span>
                    <span className="text-xs text-slate-400">{l.sub}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* ==================================================== */}
          {/* STEP 2: FLOCK SIZE & OPTIONAL SHED DIMENSIONS        */}
          {/* ==================================================== */}
          {currentStep === 2 && (
            <form onSubmit={handleFlockSubmit} className="max-w-xl mx-auto space-y-6 py-2">
              <div className="text-center space-y-2">
                <div className="text-4xl">🐔</div>
                <h3 className="text-2xl font-black text-white">
                  {t.setup.step2Title}
                </h3>
                <p className="text-base font-semibold text-emerald-400">
                  {t.setup.step2Desc}
                </p>
              </div>

              {/* Large Touch-Friendly Chicken Count Input */}
              <div className="p-6 rounded-3xl bg-slate-950/80 border-2 border-slate-800 space-y-3">
                <label className="block text-sm font-bold text-slate-300">
                  {t.setup.chickensLabel}
                </label>
                <div className="flex items-center space-x-3">
                  <input
                    type="number"
                    min="1"
                    max="100000"
                    required
                    value={flockSize}
                    onChange={(e) => setFlockSize(Math.max(1, parseInt(e.target.value) || 0))}
                    className="w-full px-5 py-4 rounded-2xl bg-slate-900 border-2 border-emerald-500/60 text-white text-3xl font-black text-center focus:border-emerald-400 outline-none"
                    placeholder="250"
                  />
                  <span className="text-xl font-bold text-slate-400 shrink-0">🐔</span>
                </div>
                <div className="flex justify-center space-x-2 pt-2">
                  {[100, 250, 500, 1000].map(cnt => (
                    <button
                      key={cnt}
                      type="button"
                      onClick={() => setFlockSize(cnt)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-colors ${
                        flockSize === cnt
                          ? 'bg-emerald-500 text-slate-950'
                          : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                      }`}
                    >
                      {cnt}
                    </button>
                  ))}
                </div>
              </div>

              {/* Optional Shed Dimensions (Meters) */}
              <div className="p-5 rounded-2xl bg-slate-950/50 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-300">
                    {t.setup.optionalDimensions}
                  </span>
                  <button
                    type="button"
                    onClick={() => setShowDimensions(!showDimensions)}
                    className="text-xs text-emerald-400 hover:underline font-medium"
                  >
                    {showDimensions ? t.setup.skipDimensions : '+ Add dimensions'}
                  </button>
                </div>

                {showDimensions && (
                  <div className="grid grid-cols-2 gap-3 pt-1">
                    <div>
                      <label className="block text-xs text-slate-400 mb-1">{t.setup.shedLength}</label>
                      <input
                        type="number"
                        min="1"
                        value={shedLength}
                        onChange={(e) => setShedLength(e.target.value)}
                        placeholder="20"
                        className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-slate-400 mb-1">{t.setup.shedWidth}</label>
                      <input
                        type="number"
                        min="1"
                        value={shedWidth}
                        onChange={(e) => setShedWidth(e.target.value)}
                        placeholder="8"
                        className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white text-sm"
                      />
                    </div>
                  </div>
                )}
              </div>

              <div className="flex space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setCurrentStep(1)}
                  className="px-6 py-3.5 rounded-2xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-sm"
                >
                  {t.setup.back}
                </button>
                <button
                  type="submit"
                  disabled={loading || flockSize <= 0}
                  className="flex-1 py-3.5 rounded-2xl bg-emerald-600 hover:bg-emerald-500 text-white font-black text-base shadow-lg shadow-emerald-950/50 flex items-center justify-center space-x-2"
                >
                  <span>{t.setup.continue}</span>
                  <ArrowRight className="w-5 h-5" />
                </button>
              </div>
            </form>
          )}

          {/* ==================================================== */}
          {/* STEP 3: FLOCKSENSE SENSOR RECOMMENDATION            */}
          {/* ==================================================== */}
          {currentStep === 3 && recData && (
            <div className="max-w-2xl mx-auto space-y-6 py-2">
              <div className="text-center space-y-1">
                <div className="text-3xl">📡</div>
                <h3 className="text-2xl font-black text-white">
                  {t.setup.suggestedSetupTitle}
                </h3>
                <p className="text-sm font-semibold text-emerald-400">
                  {t.setup.suggestedSetupSub.replace('{{count}}', flockSize.toString())}
                </p>
              </div>

              {/* 3 Giant Visual Cards (Low-Literacy Friendly) */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="p-5 rounded-3xl bg-slate-950/80 border-2 border-emerald-500/40 text-center space-y-2">
                  <span className="text-4xl block">📷</span>
                  <span className="text-4xl font-black text-white block">
                    {isAdjusting ? customCams : recData.recommendation.cameras}
                  </span>
                  <span className="text-xs font-bold text-slate-300 block">
                    {t.setup.recommendedCameras}
                  </span>
                </div>

                <div className="p-5 rounded-3xl bg-slate-950/80 border-2 border-cyan-500/40 text-center space-y-2">
                  <span className="text-4xl block">🎤</span>
                  <span className="text-4xl font-black text-white block">
                    {isAdjusting ? customMics : recData.recommendation.microphones}
                  </span>
                  <span className="text-xs font-bold text-slate-300 block">
                    {t.setup.recommendedMics}
                  </span>
                </div>

                <div className="p-5 rounded-3xl bg-slate-950/80 border-2 border-amber-500/40 text-center space-y-2">
                  <span className="text-4xl block">📍</span>
                  <span className="text-4xl font-black text-white block">
                    {isAdjusting ? customZones : recData.recommendation.zones}
                  </span>
                  <span className="text-xs font-bold text-slate-300 block">
                    {t.setup.recommendedZones}
                  </span>
                </div>
              </div>

              {/* Prototype Disclosure Alert */}
              <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-200 leading-relaxed">
                ℹ️ {t.setup.prototypeDisclaimer}
              </div>

              {/* Manual Adjustment Mode */}
              {isAdjusting && (
                <div className="p-5 rounded-3xl bg-slate-950/90 border border-slate-700 space-y-4">
                  <h4 className="text-sm font-bold text-white">
                    {t.setup.manualAdjustment}
                  </h4>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    {/* Cameras */}
                    <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900 border border-slate-800">
                      <span className="text-xs font-bold text-slate-300">📷 Cams</span>
                      <div className="flex items-center space-x-2">
                        <button
                          type="button"
                          onClick={() => setCustomCams(Math.max(1, customCams - 1))}
                          className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-white"
                        >
                          <Minus className="w-4 h-4" />
                        </button>
                        <span className="font-bold text-white w-6 text-center">{customCams}</span>
                        <button
                          type="button"
                          onClick={() => setCustomCams(customCams + 1)}
                          className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-white"
                        >
                          <Plus className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {/* Microphones */}
                    <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900 border border-slate-800">
                      <span className="text-xs font-bold text-slate-300">🎤 Mics</span>
                      <div className="flex items-center space-x-2">
                        <button
                          type="button"
                          onClick={() => setCustomMics(Math.max(1, customMics - 1))}
                          className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-white"
                        >
                          <Minus className="w-4 h-4" />
                        </button>
                        <span className="font-bold text-white w-6 text-center">{customMics}</span>
                        <button
                          type="button"
                          onClick={() => setCustomMics(customMics + 1)}
                          className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-white"
                        >
                          <Plus className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {/* Zones */}
                    <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900 border border-slate-800">
                      <span className="text-xs font-bold text-slate-300">📍 Zones</span>
                      <div className="flex items-center space-x-2">
                        <button
                          type="button"
                          onClick={() => setCustomZones(Math.max(1, customZones - 1))}
                          className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-white"
                        >
                          <Minus className="w-4 h-4" />
                        </button>
                        <span className="font-bold text-white w-6 text-center">{customZones}</span>
                        <button
                          type="button"
                          onClick={() => setCustomZones(customZones + 1)}
                          className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-white"
                        >
                          <Plus className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAdjusting(!isAdjusting)}
                  className="w-full sm:w-auto px-6 py-3.5 rounded-2xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-bold min-h-[48px]"
                >
                  {isAdjusting ? 'Cancel Adjustments' : t.setup.change}
                </button>

                <button
                  type="button"
                  onClick={() => handleConfirmSetup(isAdjusting)}
                  disabled={loading}
                  className="w-full sm:flex-1 py-3.5 rounded-2xl bg-emerald-600 hover:bg-emerald-500 text-white font-black text-base shadow-xl flex items-center justify-center space-x-2 min-h-[48px]"
                >
                  <Check className="w-5 h-5" />
                  <span>{isAdjusting ? 'Save & Create Zones' : t.setup.useSuggested}</span>
                </button>
              </div>
            </div>
          )}

          {/* ==================================================== */}
          {/* STEP 4: AUTOMATICALLY CREATED ZONES PREVIEW         */}
          {/* ==================================================== */}
          {currentStep === 4 && (
            <div className="max-w-2xl mx-auto space-y-6 py-2">
              <div className="text-center space-y-1">
                <div className="text-3xl">🗺️</div>
                <h3 className="text-2xl font-black text-white">
                  {t.setup.zonesCreatedTitle} ({zones.length})
                </h3>
                <p className="text-xs text-slate-400">
                  {t.setup.zonesCreatedDesc}
                </p>
              </div>

              {/* Visual 2D Shed Map with Device Coverage */}
              <div className="p-4 rounded-3xl bg-slate-950 border-2 border-slate-800">
                <div className={`grid gap-3 ${
                  zones.length <= 2 ? 'grid-cols-2' : zones.length <= 4 ? 'grid-cols-2' : 'grid-cols-3'
                }`}>
                  {zones.map(z => {
                    const zCams = cameras.filter(c => (c.assigned_zone_ids || [c.zone]).includes(z.zone_id));
                    const zMics = microphones.filter(m => (m.assigned_zone_ids || [m.zone]).includes(z.zone_id));

                    return (
                      <div
                        key={z.zone_id}
                        className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 flex flex-col justify-between min-h-[120px]"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-black text-emerald-400">{z.name}</span>
                          <span className="text-[10px] font-mono text-slate-500">{z.zone_id}</span>
                        </div>

                        <div className="space-y-1 pt-2">
                          <div className="text-xs text-slate-300 flex items-center space-x-1">
                            <span>📷</span>
                            <span>{zCams.length > 0 ? zCams.map(c => c.name).join(', ') : 'No camera assigned'}</span>
                          </div>
                          <div className="text-xs text-slate-400 flex items-center space-x-1">
                            <span>🎤</span>
                            <span>{zMics.length > 0 ? zMics.map(m => m.name).join(', ') : 'No mic assigned'}</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="flex space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setCurrentStep(3)}
                  className="px-6 py-3.5 rounded-2xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-sm"
                >
                  {t.setup.back}
                </button>
                <button
                  type="button"
                  onClick={() => setCurrentStep(5)}
                  className="flex-1 py-3.5 rounded-2xl bg-emerald-600 hover:bg-emerald-500 text-white font-black text-base shadow-lg flex items-center justify-center space-x-2"
                >
                  <span>Assign Farm Devices</span>
                  <ArrowRight className="w-5 h-5" />
                </button>
              </div>
            </div>
          )}

          {/* ==================================================== */}
          {/* STEP 5: CONNECT & ASSIGN DEVICES TO ZONES           */}
          {/* ==================================================== */}
          {currentStep === 5 && (
            <div className="space-y-6 py-2">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div>
                  <h3 className="text-xl font-black text-white">
                    {t.setup.connectDevicesTitle}
                  </h3>
                  <p className="text-xs text-slate-400">
                    Each camera monitors an assigned zone; microphones can cover multiple zones.
                  </p>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    type="button"
                    onClick={handleAutoAssign}
                    disabled={loading}
                    className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold flex items-center space-x-1.5 shadow"
                  >
                    <Sliders className="w-3.5 h-3.5" />
                    <span>{t.setup.autoAssign}</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleConnectAll}
                    disabled={loading}
                    className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center space-x-1.5 shadow"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                    <span>{t.devices.connectAll}</span>
                  </button>
                </div>
              </div>

              {/* Devices Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {devices.map(dev => {
                  const isCam = dev.has_video;
                  const activeZones = dev.assigned_zone_ids || [dev.zone];

                  return (
                    <div
                      key={dev.device_id}
                      className="p-4 rounded-2xl bg-slate-950 border border-slate-800 flex flex-col justify-between space-y-3"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center space-x-2.5">
                          <span className="text-2xl">{isCam ? '📷' : '🎤'}</span>
                          <div>
                            <h4 className="text-sm font-extrabold text-white">{dev.name}</h4>
                            <span className="text-[11px] font-mono text-cyan-400">{dev.device_id}</span>
                          </div>
                        </div>

                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                          dev.status === 'ONLINE'
                            ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                            : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                        }`}>
                          {dev.status === 'ONLINE' ? '🟢 Online' : '🟡 Inactive'}
                        </span>
                      </div>

                      {/* Zone Selector Pills */}
                      <div className="space-y-1.5 pt-1">
                        <span className="text-xs font-bold text-slate-400 block">
                          {isCam ? 'Assigned Camera Zone:' : 'Microphone Coverage (Multi-zone):'}
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {zones.map(z => {
                            const isSelected = activeZones.includes(z.zone_id);
                            return (
                              <button
                                key={z.zone_id}
                                type="button"
                                onClick={() => handleDeviceZoneChange(dev.device_id, z.zone_id, activeZones, !isCam)}
                                className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all ${
                                  isSelected
                                    ? 'bg-emerald-500 text-slate-950 shadow'
                                    : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
                                }`}
                              >
                                {z.name}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="flex space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setCurrentStep(4)}
                  className="px-6 py-3.5 rounded-2xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-sm"
                >
                  {t.setup.back}
                </button>
                <button
                  type="button"
                  onClick={() => setCurrentStep(6)}
                  className="flex-1 py-3.5 rounded-2xl bg-emerald-600 hover:bg-emerald-500 text-white font-black text-base shadow-lg flex items-center justify-center space-x-2"
                >
                  <span>Device Readiness Check</span>
                  <ArrowRight className="w-5 h-5" />
                </button>
              </div>
            </div>
          )}

          {/* ==================================================== */}
          {/* STEP 6: DEVICE READINESS & START MONITORING        */}
          {/* ==================================================== */}
          {currentStep === 6 && (
            <div className="max-w-xl mx-auto space-y-6 py-2 text-center">
              <div className="text-4xl">✅</div>
              <h3 className="text-2xl font-black text-white">
                {t.setup.deviceCheckTitle}
              </h3>

              {setupStatus && (
                <div className="p-5 rounded-3xl bg-slate-950 border border-slate-800 text-left space-y-3">
                  <div className="flex items-center justify-between text-sm py-1 border-b border-slate-800/80">
                    <span className="text-slate-400">Flock Size Configured:</span>
                    <strong className="text-emerald-400">{setupStatus.farm_setup.flock_size} birds</strong>
                  </div>
                  <div className="flex items-center justify-between text-sm py-1 border-b border-slate-800/80">
                    <span className="text-slate-400">Monitoring Zones:</span>
                    <strong className="text-emerald-400">{zones.length} zones active</strong>
                  </div>
                  <div className="flex items-center justify-between text-sm py-1 border-b border-slate-800/80">
                    <span className="text-slate-400">Connected Cameras:</span>
                    <strong className="text-white">{cameras.filter(c => c.status === 'ONLINE').length} / {cameras.length} Online</strong>
                  </div>
                  <div className="flex items-center justify-between text-sm py-1">
                    <span className="text-slate-400">Connected Microphones:</span>
                    <strong className="text-white">{microphones.filter(m => m.status === 'ONLINE').length} / {microphones.length} Online</strong>
                  </div>
                </div>
              )}

              {/* Bioacoustics Disclaimer */}
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                {t.setup.audioPlacementDisclaimer}
              </p>

              <div className="flex space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setCurrentStep(5)}
                  className="px-6 py-3.5 rounded-2xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-sm"
                >
                  {t.setup.back}
                </button>
                <button
                  type="button"
                  onClick={handleStartMonitoring}
                  disabled={loading}
                  className="flex-1 py-3.5 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-black text-base shadow-xl flex items-center justify-center space-x-2"
                >
                  <CheckCircle2 className="w-5 h-5" />
                  <span>{t.setup.startMonitoring}</span>
                </button>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};
