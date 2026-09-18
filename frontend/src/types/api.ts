/**
 * TypeScript definitions strictly aligned with FlockSense FastAPI schemas.
 */

export interface ComponentStatus {
  audio_model: boolean;
  camera_anomaly_model: boolean;
  fusion_engine: boolean;
  roboflow_configured: boolean;
}

export interface ValidationStatus {
  camera_real_world_validated: boolean;
  audio_localization_available: boolean;
  medical_validation: boolean;
  fusion_weights_status: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  components: ComponentStatus;
  validation: ValidationStatus;
}

export interface SystemInfoResponse {
  audio_model: string;
  behavior_model: string;
  tracker: string;
  camera_anomaly_model: string;
  fusion_mode: string;
  version: string;
  validation: {
    camera: string;
    audio_localization: boolean;
    medical_validation: boolean;
    fusion_weights: string;
  };
  disclaimer: string;
}

export interface GlobalAudioContext {
  score: number;
  status: string;
  active: boolean;
  localized: boolean;
  scope: string;
  last_event_time: number | null;
  interpretation: string;
}

export interface TrackingSummary {
  active_tracks: number;
  high_deviation_tracks: number;
  watch_deviation_tracks: number;
}

export interface FlockStatusResponse {
  flock_status: "NORMAL" | "WATCH" | "ALERT";
  global_audio: GlobalAudioContext;
  tracking: TrackingSummary;
  top_candidate_ids: number[];
  fusion_mode: string;
  timestamp: number;
  recommendation: string;
  disclaimer: string;
}

export interface AudioContextSummary {
  global_audio_active: boolean;
  audio_localized: boolean;
  urgency_boost: number;
}

export interface CandidateItem {
  rank: number;
  track_id: number;
  current_zone: string;
  initial_evidence_zone: string;
  behavior: string;
  camera_deviation_score: number;
  persistence_score: number;
  inspection_priority: number;
  status: "NORMAL" | "WATCH" | "ALERT";
  tracking_status: string;
  reasons: string[];
  audio_context: AudioContextSummary;
  last_seen_timestamp: number;
}

export interface CandidateResponse {
  total_candidates: number;
  candidates: CandidateItem[];
  disclaimer: string;
}

export interface TrackSummaryItem {
  track_id: number;
  tracking_status: string;
  current_zone: string;
  previous_zone: string;
  initial_evidence_zone: string;
  current_behavior: string;
  stable_behavior: string;
  behavior_confidence: number;
  movement_rate: number;
  stationary_duration: number;
  camera_deviation_score: number;
  inspection_priority: number;
  status: "NORMAL" | "WATCH" | "ALERT";
  last_seen: number;
}

export interface TrackListResponse {
  total_tracks: number;
  tracks: TrackSummaryItem[];
}

export interface TrackDetailResponse {
  track_id: number;
  tracking_status: string;
  current_zone: string;
  previous_zone: string;
  initial_evidence_zone: string;
  position: [number, number];
  bbox: [number, number, number, number];
  current_behavior: string;
  stable_behavior: string;
  behavior_confidence: number;
  movement_rate: number;
  distance_travelled_pixels: number;
  stationary_duration: number;
  stationary_ratio: number;
  relative_isolation_score: number;
  relative_activity: number;
  camera_deviation_score: number;
  persistence_score: number;
  inspection_priority: number;
  fusion_status: "NORMAL" | "WATCH" | "ALERT";
  reasons: string[];
  audio_context: AudioContextSummary;
  first_seen: number;
  last_seen: number;
  disclaimer: string;
}

export interface AlertItem {
  alert_id: string;
  timestamp: number;
  level: "NORMAL" | "WATCH" | "ALERT";
  scope: string;
  track_id: number | null;
  current_zone: string | null;
  inspection_priority: number | null;
  message: string;
  recommendation: string;
  audio_localized: boolean;
  disclaimer: string;
}

export interface AlertListResponse {
  total_alerts: number;
  alerts: AlertItem[];
}

export interface AudioInferenceResult {
  prediction: string;
  status: string;
  overall_abnormality_probability_pct: number;
  score: number;
  scope: string;
  localized: boolean;
  duration_seconds: number;
  windows_analyzed: number;
  high_risk_windows: number;
  interpretation: string;
  recommended_action: string;
}

export interface FusionContextUpdate {
  flock_status: string;
  global_audio_score: number;
  top_candidate_ids: number[];
}

export interface AudioAnalysisResponse {
  success: boolean;
  filename: string;
  audio: AudioInferenceResult;
  fusion: FusionContextUpdate;
  disclaimer: string;
}

export interface DeviceResponse {
  device_id: string;
  name: string;
  device_type: "CAMERA" | "MICROPHONE" | "CAMERA_WITH_AUDIO" | "ENVIRONMENT_SENSOR";
  connection_type: string;
  host: string | null;
  sanitized_url: string;
  farm: string;
  shed: string;
  zone: string;
  assigned_zone_ids?: string[];
  enabled: boolean;
  status: "ONLINE" | "DEGRADED" | "RECONNECTING" | "OFFLINE";
  has_video: boolean;
  has_audio: boolean;
  is_demo: boolean;
  last_seen: number | null;
  fps: number;
  latency_ms: number;
  error_message: string | null;
}

export interface DiscoveredDevice {
  device_id: string;
  name: string;
  model: string;
  host: string;
  connection_type: string;
  requires_credentials: boolean;
  suggested_zone: string;
}

export interface DeviceTestResult {
  success: boolean;
  device_id?: string;
  message: string;
  fps: number;
  resolution?: string | null;
  has_audio: boolean;
}

export interface SensorGatewayStatus {
  total_devices: number;
  online_devices: number;
  cameras_online: number;
  total_cameras: number;
  microphones_online: number;
  total_microphones: number;
  gateway_status: string;
  timestamp: number;
}

export interface AddCameraRequest {
  name: string;
  connection_type?: "RTSP" | "ONVIF" | "HTTP_MJPEG" | "LOCAL" | "DEMO";
  host?: string;
  stream_url?: string;
  username?: string;
  password?: string;
  zone?: string;
  farm?: string;
  shed?: string;
  has_audio?: boolean;
}

export interface AddMicrophoneRequest {
  name: string;
  connection_type?: "NETWORK_AUDIO" | "LOCAL_MIC" | "CAMERA_AUDIO" | "DEMO_AUDIO";
  host?: string;
  stream_url?: string;
  zone?: string;
  farm?: string;
  shed?: string;
}

export interface ZoneItem {
  zone_id: string;
  name: string;
  display_name?: string;
  color_bgr: [number, number, number];
  polygon: [number, number][];
  bounds?: {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
  };
}

export interface FarmSetupState {
  farm_name: string;
  shed_id: string;
  shed_name: string;
  flock_size: number;
  shed_dimensions?: {
    length_m: number;
    width_m: number;
  } | null;
  recommended: {
    cameras: number;
    microphones: number;
    zones: number;
    basis?: string;
    reason?: string;
    disclaimer?: string;
  };
  configured: {
    cameras: number;
    microphones: number;
    zones: number;
  };
  is_setup_completed: boolean;
  monitoring_active: boolean;
  step: number;
}

export interface SetupStatusResponse {
  farm_setup: FarmSetupState;
  is_ready: boolean;
  checklist: {
    flock_size_configured: boolean;
    zones_created: boolean;
    num_zones: number;
    cameras_online: number;
    microphones_online: number;
    cameras_assigned: number;
    microphones_assigned: number;
  };
  issues: string[];
  ready_message: string;
}

export interface FlockSetupResponse {
  flock_size: number;
  shed_dimensions?: { length_m: number; width_m: number } | null;
  recommendation: {
    cameras: number;
    microphones: number;
    zones: number;
    basis?: string;
    reason?: string;
    disclaimer?: string;
  };
  comparison: {
    is_first_setup: boolean;
    current_setup: { cameras: number; microphones: number; zones: number };
    new_recommendation: { cameras: number; microphones: number; zones: number };
    camera_diff: number;
    mic_diff: number;
    zone_diff: number;
  };
}

