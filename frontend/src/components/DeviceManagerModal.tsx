import React, { useState, useEffect, useCallback } from 'react';
import { 
  Radio, 
  Search, 
  Plus, 
  CheckCircle2, 
  AlertCircle, 
  X, 
  Trash2, 
  RefreshCw 
} from 'lucide-react';
import { useI18n } from '../i18n';
import { api } from '../api/flocksense';
import { 
  DeviceResponse, 
  DiscoveredDevice, 
  SensorGatewayStatus,
  AddCameraRequest,
  AddMicrophoneRequest
} from '../types/api';

interface DeviceManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDevicesUpdated?: () => void;
}

export const DeviceManagerModal: React.FC<DeviceManagerModalProps> = ({
  isOpen,
  onClose,
  onDevicesUpdated,
}) => {
  const { t } = useI18n();

  const [activeTab, setActiveTab] = useState<'all' | 'cameras' | 'microphones' | 'add'>('all');
  const [setupMode, setSetupMode] = useState<'simple' | 'advanced'>('simple');
  const [devices, setDevices] = useState<DeviceResponse[]>([]);
  const [gatewayStatus, setGatewayStatus] = useState<SensorGatewayStatus | null>(null);
  const [discoveredDevices, setDiscoveredDevices] = useState<DiscoveredDevice[]>([]);
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [isConnectingAll, setIsConnectingAll] = useState<boolean>(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ id?: string; success: boolean; message: string } | null>(null);

  // New Camera Form State
  const [newCam, setNewCam] = useState<AddCameraRequest>({
    name: '',
    connection_type: 'RTSP',
    host: '',
    stream_url: '',
    username: '',
    password: '',
    zone: 'ZONE_1',
    has_audio: false,
    farm: 'Main Farm',
    shed: 'Broiler Shed A',
  });

  // New Microphone Form State
  const [newMic, setNewMic] = useState<AddMicrophoneRequest>({
    name: '',
    connection_type: 'NETWORK_AUDIO',
    host: '',
    stream_url: '',
    zone: 'ZONE_1',
    farm: 'Main Farm',
    shed: 'Broiler Shed A',
  });

  const loadData = useCallback(async () => {
    try {
      const [devList, status] = await Promise.all([
        api.getDevices().catch(() => []),
        api.getGatewayStatus().catch(() => null),
      ]);
      setDevices(devList);
      if (status) setGatewayStatus(status);
    } catch (err) {
      console.error('Failed to load gateway data', err);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      loadData();
      const interval = setInterval(loadData, 4000);
      return () => clearInterval(interval);
    }
  }, [isOpen, loadData]);

  if (!isOpen) return null;

  const handleScan = async () => {
    setIsScanning(true);
    setTestResult(null);
    try {
      const found = await api.discoverDevices();
      setDiscoveredDevices(found);
    } catch (err: any) {
      setTestResult({ success: false, message: err.message || 'Discovery scan failed' });
    } finally {
      setIsScanning(false);
    }
  };

  const handleConnectAll = async () => {
    setIsConnectingAll(true);
    try {
      await api.connectAllDevices();
      await loadData();
      if (onDevicesUpdated) onDevicesUpdated();
    } catch (err: any) {
      console.error(err);
    } finally {
      setIsConnectingAll(false);
    }
  };

  const handleConnectDevice = async (id: string) => {
    setActionLoading(id);
    try {
      await api.connectDevice(id);
      await loadData();
      if (onDevicesUpdated) onDevicesUpdated();
    } catch (err) {
      console.error(err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDisconnectDevice = async (id: string) => {
    setActionLoading(id);
    try {
      await api.disconnectDevice(id);
      await loadData();
      if (onDevicesUpdated) onDevicesUpdated();
    } catch (err) {
      console.error(err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleTestDevice = async (id: string) => {
    setActionLoading(`test-${id}`);
    setTestResult(null);
    try {
      const res = await api.testDevice(id);
      setTestResult({ id, success: res.success, message: res.message });
    } catch (err: any) {
      setTestResult({ id, success: false, message: err.message || 'Test connection failed' });
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeleteDevice = async (id: string) => {
    if (!window.confirm(`Remove sensor device ${id}?`)) return;
    setActionLoading(`del-${id}`);
    try {
      await api.deleteDevice(id);
      await loadData();
      if (onDevicesUpdated) onDevicesUpdated();
    } catch (err) {
      console.error(err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleAddCameraSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading('add-cam');
    setTestResult(null);
    try {
      const added = await api.addCamera(newCam);
      await loadData();
      if (onDevicesUpdated) onDevicesUpdated();
      setActiveTab('cameras');
      setTestResult({ id: added.device_id, success: true, message: `Camera ${added.name} registered and tested.` });
    } catch (err: any) {
      setTestResult({ success: false, message: err.message || 'Failed to register camera' });
    } finally {
      setActionLoading(null);
    }
  };

  const handleAddMicrophoneSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading('add-mic');
    setTestResult(null);
    try {
      const added = await api.addMicrophone(newMic);
      await loadData();
      if (onDevicesUpdated) onDevicesUpdated();
      setActiveTab('microphones');
      setTestResult({ id: added.device_id, success: true, message: `Microphone ${added.name} registered.` });
    } catch (err: any) {
      setTestResult({ success: false, message: err.message || 'Failed to register microphone' });
    } finally {
      setActionLoading(null);
    }
  };

  const cameras = devices.filter(d => d.device_type === 'CAMERA');
  const microphones = devices.filter(d => d.device_type === 'MICROPHONE');
  const filteredDevices = activeTab === 'cameras' 
    ? cameras 
    : activeTab === 'microphones' 
    ? microphones 
    : devices;

  const onlineCams = cameras.filter(c => c.status === 'ONLINE').length;
  const onlineMics = microphones.filter(m => m.status === 'ONLINE').length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-950/85 backdrop-blur-md overflow-y-auto">
      <div className="relative w-full max-w-5xl bg-slate-900 border-2 border-slate-700/80 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header Bar */}
        <div className="p-5 sm:p-6 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-emerald-600 to-cyan-600 p-0.5 shadow-lg shrink-0">
              <div className="w-full h-full bg-slate-950 rounded-[14px] flex items-center justify-center">
                <Radio className="w-6 h-6 text-emerald-400 animate-pulse" />
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight">
                  {t.devices.title}
                </h2>
                {gatewayStatus && (
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                    gatewayStatus.gateway_status === 'HEALTHY'
                      ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                      : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                  }`}>
                    {gatewayStatus.gateway_status === 'HEALTHY' ? t.devices.gatewayHealthy : t.devices.gatewayPartial}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 font-medium">
                {t.devices.subtitle}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2.5 rounded-2xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Action Controls Bar */}
        <div className="px-5 py-3 border-b border-slate-800/80 bg-slate-950/30 flex flex-wrap items-center justify-between gap-3">
          {/* Tabs */}
          <div className="flex space-x-1.5 overflow-x-auto">
            <button
              onClick={() => setActiveTab('all')}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                activeTab === 'all'
                  ? 'bg-emerald-500 text-slate-950'
                  : 'text-slate-400 hover:text-white bg-slate-800/60'
              }`}
            >
              {t.devices.connected} ({devices.length})
            </button>
            <button
              onClick={() => setActiveTab('cameras')}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold flex items-center space-x-1.5 transition-all ${
                activeTab === 'cameras'
                  ? 'bg-emerald-500 text-slate-950'
                  : 'text-slate-400 hover:text-white bg-slate-800/60'
              }`}
            >
              <span>📷 {t.devices.cameras}</span>
              <span className="text-[10px] opacity-80">({onlineCams}/{cameras.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('microphones')}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold flex items-center space-x-1.5 transition-all ${
                activeTab === 'microphones'
                  ? 'bg-emerald-500 text-slate-950'
                  : 'text-slate-400 hover:text-white bg-slate-800/60'
              }`}
            >
              <span>🎤 {t.devices.microphones}</span>
              <span className="text-[10px] opacity-80">({onlineMics}/{microphones.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('add')}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold flex items-center space-x-1.5 transition-all ${
                activeTab === 'add'
                  ? 'bg-cyan-500 text-slate-950'
                  : 'text-cyan-400 hover:text-white bg-cyan-950/40 border border-cyan-800/60'
              }`}
            >
              <Plus className="w-3.5 h-3.5" />
              <span>{t.devices.addCamera} / {t.devices.addMicrophone}</span>
            </button>
          </div>

          {/* Quick Action Buttons (Connect All / Find Devices) */}
          <div className="flex items-center space-x-2">
            <button
              onClick={handleScan}
              disabled={isScanning}
              className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold flex items-center space-x-2 border border-slate-700 active:scale-95 disabled:opacity-50"
            >
              <Search className={`w-3.5 h-3.5 ${isScanning ? 'animate-spin text-emerald-400' : ''}`} />
              <span>{isScanning ? t.devices.scanning : t.devices.findDevices}</span>
            </button>

            <button
              onClick={handleConnectAll}
              disabled={isConnectingAll}
              className="px-4 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center space-x-2 shadow-md shadow-emerald-950/50 active:scale-95 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isConnectingAll ? 'animate-spin' : ''}`} />
              <span>{t.devices.connectAll}</span>
            </button>
          </div>
        </div>

        {/* Test Result Toast */}
        {testResult && (
          <div className={`px-5 py-2.5 text-xs font-medium flex items-center justify-between ${
            testResult.success 
              ? 'bg-emerald-950/60 text-emerald-300 border-b border-emerald-800/60' 
              : 'bg-rose-950/60 text-rose-300 border-b border-rose-800/60'
          }`}>
            <div className="flex items-center space-x-2">
              {testResult.success ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <AlertCircle className="w-4 h-4 text-rose-400" />}
              <span>{testResult.message}</span>
            </div>
            <button onClick={() => setTestResult(null)} className="opacity-70 hover:opacity-100">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Modal Body Area */}
        <div className="p-5 sm:p-6 overflow-y-auto flex-1 space-y-6">

          {/* Discovered LAN Devices Section */}
          {discoveredDevices.length > 0 && (
            <div className="rounded-2xl border border-cyan-500/40 bg-cyan-950/20 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="text-lg">📡</span>
                  <h3 className="text-sm font-bold text-cyan-300">
                    Discovered Farm LAN Devices ({discoveredDevices.length})
                  </h3>
                </div>
                <button 
                  onClick={() => setDiscoveredDevices([])}
                  className="text-xs text-slate-400 hover:text-white"
                >
                  Clear
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {discoveredDevices.map((d, idx) => (
                  <div key={idx} className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 flex items-center justify-between">
                    <div>
                      <div className="text-xs font-bold text-white flex items-center space-x-1.5">
                        <span>📷</span>
                        <span>{d.name}</span>
                      </div>
                      <div className="text-[11px] font-mono text-cyan-400 mt-0.5">{d.host}</div>
                      <div className="text-[10px] text-slate-400">
                        {d.requires_credentials ? '🔒 Auth Required' : '🔓 Open Access'} • {d.connection_type}
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        setNewCam({
                          ...newCam,
                          name: d.name,
                          host: d.host,
                          stream_url: `rtsp://${d.host}:554/live/ch0`,
                        });
                        setActiveTab('add');
                      }}
                      className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold shrink-0"
                    >
                      Configure
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 1: LIST SENSORS (CAMERAS & MICS) */}
          {activeTab !== 'add' && (
            <div className="space-y-4">
              {filteredDevices.length === 0 ? (
                <div className="text-center py-12 space-y-3">
                  <div className="text-4xl">📡</div>
                  <h3 className="text-lg font-bold text-white">No sensors registered yet</h3>
                  <p className="text-sm text-slate-400 max-w-md mx-auto">
                    Click "Find Devices" to scan your farm Wi-Fi/PoE network, or "Add Camera" to manually enter an RTSP stream.
                  </p>
                  <button
                    onClick={() => setActiveTab('add')}
                    className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold"
                  >
                    + {t.devices.addCamera}
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {filteredDevices.map((dev) => {
                    const isCam = dev.device_type === 'CAMERA';
                    const isOnline = dev.status === 'ONLINE';
                    const isDegraded = dev.status === 'DEGRADED';
                    const isReconnecting = dev.status === 'RECONNECTING';

                    return (
                      <div
                        key={dev.device_id}
                        className={`rounded-2xl border-2 transition-all p-4 bg-slate-950/60 flex flex-col justify-between ${
                          isOnline
                            ? 'border-emerald-500/40 shadow-lg shadow-emerald-950/20'
                            : isReconnecting || isDegraded
                            ? 'border-amber-500/40 bg-amber-950/10'
                            : 'border-slate-800 opacity-90'
                        }`}
                      >
                        {/* Top device header */}
                        <div>
                          <div className="flex items-start justify-between">
                            <div className="flex items-center space-x-2.5">
                              <span className="text-2xl">{isCam ? '📷' : '🎤'}</span>
                              <div>
                                <h4 className="text-base font-extrabold text-white flex items-center space-x-2">
                                  <span>{dev.name}</span>
                                  {dev.is_demo && (
                                    <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                                      {t.devices.demoDevice}
                                    </span>
                                  )}
                                </h4>
                                <div className="flex items-center space-x-2 text-[11px] text-slate-400 mt-0.5">
                                  <span className="font-mono text-cyan-400">{dev.device_id}</span>
                                  <span>•</span>
                                  <span className="text-emerald-300 font-semibold">{dev.zone}</span>
                                  <span>•</span>
                                  <span>{dev.connection_type}</span>
                                </div>
                              </div>
                            </div>

                            {/* Status Pill */}
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border flex items-center space-x-1 ${
                              isOnline
                                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                                : isReconnecting
                                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                                : 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                            }`}>
                              <span>{isOnline ? '🟢' : isReconnecting ? '🟡' : '🔴'}</span>
                              <span>{isOnline ? t.devices.connected : isReconnecting ? t.devices.connecting : t.devices.notConnected}</span>
                            </span>
                          </div>

                          {/* Live Preview Snapshot for Cameras */}
                          {isCam && isOnline && (
                            <div className="mt-3 relative rounded-xl overflow-hidden bg-slate-900 border border-slate-800 aspect-video flex items-center justify-center">
                              <img
                                src={`/api/devices/${dev.device_id}/snapshot.jpg?t=${Date.now()}`}
                                alt={dev.name}
                                className="w-full h-full object-cover"
                                onError={(e) => {
                                  (e.target as HTMLElement).style.display = 'none';
                                }}
                              />
                              <div className="absolute top-2 right-2 bg-slate-950/80 px-2 py-0.5 rounded text-[10px] font-mono text-emerald-400 flex items-center space-x-1">
                                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
                                <span>LIVE GATEWAY</span>
                              </div>
                            </div>
                          )}

                          {/* Audio signal indicator for microphones */}
                          {!isCam && (
                            <div className="mt-3 p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
                              <div className="flex items-center space-x-2">
                                <Radio className={`w-4 h-4 ${isOnline ? 'text-emerald-400 animate-pulse' : 'text-slate-500'}`} />
                                <span className="text-xs text-slate-300 font-medium">
                                  {isOnline ? 'Receiving Flock Bioacoustics' : 'Audio Stream Inactive'}
                                </span>
                              </div>
                              <span className="text-[10px] font-mono text-slate-400">
                                16000 Hz Mono PCM
                              </span>
                            </div>
                          )}

                          {/* Endpoint info (sanitized) */}
                          <div className="mt-2 text-[10px] font-mono text-slate-500 truncate">
                            {dev.host ? `Host: ${dev.host}` : dev.sanitized_url ? `Stream: ${dev.sanitized_url}` : 'Direct Interface'}
                          </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between gap-2">
                          <div className="flex space-x-1.5">
                            {isOnline ? (
                              <button
                                onClick={() => handleDisconnectDevice(dev.device_id)}
                                disabled={actionLoading === dev.device_id}
                                className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
                              >
                                {t.devices.disconnect}
                              </button>
                            ) : (
                              <button
                                onClick={() => handleConnectDevice(dev.device_id)}
                                disabled={actionLoading === dev.device_id}
                                className="px-2.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center space-x-1"
                              >
                                <span>{t.devices.reconnect}</span>
                              </button>
                            )}

                            <button
                              onClick={() => handleTestDevice(dev.device_id)}
                              disabled={actionLoading === `test-${dev.device_id}`}
                              className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
                            >
                              {t.devices.testConnection}
                            </button>
                          </div>

                          <button
                            onClick={() => handleDeleteDevice(dev.device_id)}
                            disabled={actionLoading === `del-${dev.device_id}`}
                            className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 transition-colors"
                            title={t.devices.remove}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: ADD SENSOR FORM */}
          {activeTab === 'add' && (
            <div className="max-w-2xl mx-auto space-y-6">
              {/* Simple vs Advanced Toggle */}
              <div className="flex rounded-2xl bg-slate-950 p-1 border border-slate-800">
                <button
                  type="button"
                  onClick={() => setSetupMode('simple')}
                  className={`flex-1 py-2 rounded-xl text-xs font-bold transition-all ${
                    setupMode === 'simple'
                      ? 'bg-emerald-500 text-slate-950 shadow-md'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {t.devices.simpleSetup}
                </button>
                <button
                  type="button"
                  onClick={() => setSetupMode('advanced')}
                  className={`flex-1 py-2 rounded-xl text-xs font-bold transition-all ${
                    setupMode === 'advanced'
                      ? 'bg-emerald-500 text-slate-950 shadow-md'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {t.devices.advancedSetup}
                </button>
              </div>

              {/* Add Camera Form */}
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5 space-y-4">
                <h3 className="text-base font-bold text-white flex items-center space-x-2">
                  <span>📷</span>
                  <span>{t.devices.addCamera}</span>
                </h3>

                <form onSubmit={handleAddCameraSubmit} className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-bold text-slate-300 mb-1">
                        {t.devices.deviceName} *
                      </label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. Feeding Area Cam"
                        value={newCam.name}
                        onChange={(e) => setNewCam({ ...newCam, name: e.target.value })}
                        className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white text-xs focus:border-emerald-500 outline-none"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-300 mb-1">
                        {t.devices.assignedZone}
                      </label>
                      <select
                        value={newCam.zone}
                        onChange={(e) => setNewCam({ ...newCam, zone: e.target.value })}
                        className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white text-xs focus:border-emerald-500 outline-none"
                      >
                        <option value="ZONE_1">Zone 1 (Feeding line)</option>
                        <option value="ZONE_2">Zone 2 (Drinking/Nipple line)</option>
                        <option value="ZONE_3">Zone 3 (Resting / Brooding area)</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-300 mb-1">
                      {setupMode === 'simple' ? 'Camera IP Address or RTSP URL *' : t.devices.streamUrl}
                    </label>
                    <input
                      type="text"
                      required
                      placeholder={setupMode === 'simple' ? '192.168.1.50 or rtsp://192.168.1.50:554/live' : 'rtsp://user:pass@192.168.1.50:554/h264Preview_01_main'}
                      value={newCam.stream_url || newCam.host}
                      onChange={(e) => {
                        const val = e.target.value;
                        if (val.startsWith('rtsp://') || val.startsWith('http://')) {
                          setNewCam({ ...newCam, stream_url: val });
                        } else {
                          setNewCam({ ...newCam, host: val, stream_url: val ? `rtsp://${val}:554/live` : '' });
                        }
                      }}
                      className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white text-xs font-mono focus:border-emerald-500 outline-none"
                    />
                  </div>

                  {setupMode === 'advanced' && (
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
                      <div>
                        <label className="block text-xs font-bold text-slate-300 mb-1">
                          {t.devices.connectionType}
                        </label>
                        <select
                          value={newCam.connection_type}
                          onChange={(e) => setNewCam({ ...newCam, connection_type: e.target.value as any })}
                          className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white text-xs"
                        >
                          <option value="RTSP">RTSP (IP Camera)</option>
                          <option value="HTTP_MJPEG">HTTP / MJPEG</option>
                          <option value="LOCAL">Local USB Webcam</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-slate-300 mb-1">
                          {t.devices.username}
                        </label>
                        <input
                          type="text"
                          placeholder="admin"
                          value={newCam.username}
                          onChange={(e) => setNewCam({ ...newCam, username: e.target.value })}
                          className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white text-xs"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-slate-300 mb-1">
                          {t.devices.password}
                        </label>
                        <input
                          type="password"
                          placeholder="••••••••"
                          value={newCam.password}
                          onChange={(e) => setNewCam({ ...newCam, password: e.target.value })}
                          className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white text-xs"
                        />
                      </div>
                    </div>
                  )}

                  <div className="flex items-center space-x-2 pt-1">
                    <input
                      type="checkbox"
                      id="cam_has_audio"
                      checked={newCam.has_audio}
                      onChange={(e) => setNewCam({ ...newCam, has_audio: e.target.checked })}
                      className="rounded text-emerald-500 focus:ring-0"
                    />
                    <label htmlFor="cam_has_audio" className="text-xs text-slate-300 select-none cursor-pointer">
                      Camera contains built-in microphone / audio stream
                    </label>
                  </div>

                  <button
                    type="submit"
                    disabled={actionLoading === 'add-cam'}
                    className="w-full min-h-[44px] rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-lg flex items-center justify-center space-x-2 disabled:opacity-50"
                  >
                    <span>{t.devices.save}</span>
                  </button>
                </form>
              </div>

              {/* Add Microphone Form */}
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5 space-y-4">
                <h3 className="text-base font-bold text-white flex items-center space-x-2">
                  <span>🎤</span>
                  <span>{t.devices.addMicrophone}</span>
                </h3>

                <form onSubmit={handleAddMicrophoneSubmit} className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-bold text-slate-300 mb-1">
                        {t.devices.deviceName} *
                      </label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. North Ridge Mic"
                        value={newMic.name}
                        onChange={(e) => setNewMic({ ...newMic, name: e.target.value })}
                        className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white text-xs focus:border-cyan-500 outline-none"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-300 mb-1">
                        {t.devices.assignedZone}
                      </label>
                      <select
                        value={newMic.zone}
                        onChange={(e) => setNewMic({ ...newMic, zone: e.target.value })}
                        className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white text-xs focus:border-cyan-500 outline-none"
                      >
                        <option value="ZONE_1">Zone 1 (Feeding line)</option>
                        <option value="ZONE_2">Zone 2 (Drinking/Nipple line)</option>
                        <option value="ZONE_3">Zone 3 (Resting / Brooding area)</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-300 mb-1">
                      Audio Source IP or URL *
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="192.168.1.60 or http://192.168.1.60:8080/audio.raw"
                      value={newMic.stream_url || newMic.host}
                      onChange={(e) => {
                        const val = e.target.value;
                        if (val.startsWith('http://') || val.startsWith('rtsp://')) {
                          setNewMic({ ...newMic, stream_url: val });
                        } else {
                          setNewMic({ ...newMic, host: val, stream_url: val ? `http://${val}:8000/audio.wav` : '' });
                        }
                      }}
                      className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white text-xs font-mono focus:border-cyan-500 outline-none"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={actionLoading === 'add-mic'}
                    className="w-full min-h-[44px] rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs shadow-lg flex items-center justify-center space-x-2 disabled:opacity-50"
                  >
                    <span>{t.devices.save}</span>
                  </button>
                </form>
              </div>
            </div>
          )}
        </div>

        {/* Footer Disclaimer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/80 text-[11px] text-slate-400 flex flex-col sm:flex-row items-center justify-between gap-2">
          <p className="max-w-2xl">
            {t.devices.disclaimer}
          </p>
          <button
            onClick={onClose}
            className="w-full sm:w-auto px-6 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold"
          >
            {t.system.close}
          </button>
        </div>
      </div>
    </div>
  );
};
