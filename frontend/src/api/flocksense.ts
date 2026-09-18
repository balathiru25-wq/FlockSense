/**
 * Centralized API client for communicating with FlockSense FastAPI backend.
 */

import {
  HealthResponse,
  SystemInfoResponse,
  FlockStatusResponse,
  CandidateResponse,
  TrackListResponse,
  TrackDetailResponse,
  AlertListResponse,
  AudioAnalysisResponse
} from '../types/api';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const fullUrl = url.startsWith('http') ? url : `${BASE_URL}${url}`;
  const response = await fetch(fullUrl, {
    ...options,
    headers: {
      'Accept': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.detail?.message) {
        errorDetail = errJson.detail.message;
      } else if (typeof errJson.detail === 'string') {
        errorDetail = errJson.detail;
      }
    } catch {
      // Ignore JSON parse error on non-json error responses
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export const api = {
  getHealth: () => fetchJson<HealthResponse>('/api/health'),
  
  getSystemInfo: () => fetchJson<SystemInfoResponse>('/api/system-info'),
  
  getFlockStatus: () => fetchJson<FlockStatusResponse>('/api/flock-status'),
  
  getCandidates: (limit = 10) => fetchJson<CandidateResponse>(`/api/candidates?limit=${limit}`),
  
  getTracks: () => fetchJson<TrackListResponse>('/api/tracks'),
  
  getTrackDetail: (trackId: number) => fetchJson<TrackDetailResponse>(`/api/tracks/${trackId}`),
  
  getAlerts: (level?: string, limit = 20) => {
    const params = new URLSearchParams();
    if (level && level !== 'ALL') params.set('level', level);
    params.set('limit', String(limit));
    return fetchJson<AlertListResponse>(`/api/alerts?${params.toString()}`);
  },
  
  analyzeAudio: async (file: File): Promise<AudioAnalysisResponse> => {
    const fullUrl = `${BASE_URL}/api/analyze-audio`;
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(fullUrl, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let errorDetail = `Audio Upload Error: ${response.statusText}`;
      try {
        const errJson = await response.json();
        if (errJson.detail?.message) {
          errorDetail = errJson.detail.message;
        } else if (typeof errJson.detail === 'string') {
          errorDetail = errJson.detail;
        }
      } catch {
        // Ignore
      }
      throw new Error(errorDetail);
    }

    return response.json();
  },

  // Development & Judge Demo simulation helpers
  devIngestTrack: (data: Record<string, unknown>) =>
    fetchJson('/api/dev/track-state', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  demoReset: () => fetchJson('/api/dev/demo/reset', { method: 'POST' }),
  demoNormal: () => fetchJson('/api/dev/demo/normal', { method: 'POST' }),
  demoBehaviorDeviation: () => fetchJson('/api/dev/demo/behavior-deviation', { method: 'POST' }),
  demoZoneTransition: () => fetchJson('/api/dev/demo/zone-transition', { method: 'POST' }),
  demoAnalyzeTestAudio: (mode: 'normal' | 'abnormal') =>
    fetchJson(`/api/dev/demo/analyze-test-audio?mode=${mode}`, { method: 'POST' }),
  demoGetStatus: () => fetchJson('/api/dev/demo/status'),

  // Sensor Gateway Methods
  getDevices: () => fetchJson<import('../types/api').DeviceResponse[]>('/api/devices'),
  getCameras: () => fetchJson<import('../types/api').DeviceResponse[]>('/api/devices/cameras'),
  getMicrophones: () => fetchJson<import('../types/api').DeviceResponse[]>('/api/devices/microphones'),
  getGatewayStatus: () => fetchJson<import('../types/api').SensorGatewayStatus>('/api/devices/status'),
  discoverDevices: () => fetchJson<import('../types/api').DiscoveredDevice[]>('/api/devices/discover', { method: 'POST' }),
  connectDevice: (deviceId: string) => fetchJson<import('../types/api').DeviceResponse>(`/api/devices/${deviceId}/connect`, { method: 'POST' }),
  disconnectDevice: (deviceId: string) => fetchJson<import('../types/api').DeviceResponse>(`/api/devices/${deviceId}/disconnect`, { method: 'POST' }),
  connectAllDevices: () => fetchJson<{ success: boolean; message: string; results: Record<string, boolean> }>('/api/devices/connect-all', { method: 'POST' }),
  testDevice: (deviceId: string) => fetchJson<import('../types/api').DeviceTestResult>(`/api/devices/${deviceId}/test`, { method: 'POST' }),
  deleteDevice: (deviceId: string) => fetchJson<{ success: boolean; device_id: string; message: string }>(`/api/devices/${deviceId}`, { method: 'DELETE' }),
  addCamera: (data: import('../types/api').AddCameraRequest | Record<string, unknown>) => fetchJson<import('../types/api').DeviceResponse>('/api/devices/camera', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }),
  addMicrophone: (data: import('../types/api').AddMicrophoneRequest | Record<string, unknown>) => fetchJson<import('../types/api').DeviceResponse>('/api/devices/microphone', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }),

  // Smart Farm Setup & Dynamic Zones
  submitFlockInfo: (data: { flock_size: number; shed_length_m?: number; shed_width_m?: number; farm_name?: string; shed_name?: string }) =>
    fetchJson<import('../types/api').FlockSetupResponse>('/api/setup/flock', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  getSetupStatus: () => fetchJson<import('../types/api').SetupStatusResponse>('/api/setup/status'),
  confirmSetup: (data: { cameras: number; microphones: number; zones: number; recreate_zones?: boolean }) =>
    fetchJson<{ configured: { cameras: number; microphones: number; zones: number }; zones_created: number; zones: import('../types/api').ZoneItem[] }>('/api/setup/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  autoAssignDevices: () => fetchJson<{ success: boolean; assignments: any; message: string }>('/api/setup/auto-assign', { method: 'POST' }),
  startMonitoringSetup: () => fetchJson<{ success: boolean; message: string; state: any }>('/api/setup/start-monitoring', { method: 'POST' }),
  getZones: () => fetchJson<{ zones: import('../types/api').ZoneItem[]; count: number }>('/api/zones'),
  generateZones: (numZones: number, aspectRatio: number = 1.5) =>
    fetchJson<{ zones: import('../types/api').ZoneItem[]; count: number }>('/api/zones/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ num_zones: numZones, aspect_ratio: aspectRatio }),
    }),
  renameZone: (zoneId: string, displayName: string) =>
    fetchJson<{ success: boolean; zone_id: string; display_name: string }>(`/api/zones/${zoneId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ display_name: displayName }),
    }),
  updateDeviceZones: (deviceId: string, assignedZoneIds: string[]) =>
    fetchJson<import('../types/api').DeviceResponse>(`/api/setup/devices/${deviceId}/zones`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ assigned_zone_ids: assignedZoneIds }),
    }),
};

