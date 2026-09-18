import time
from typing import List, Dict, Any, Optional, Tuple
from collections import deque
import numpy as np

class TrackState:
    """
    State representation for an individual chicken track.
    Stores temporary track identity, observable behavior, zone location,
    and movement statistics over time.
    
    IMPORTANT: Track IDs are temporary session identifiers, NOT permanent
    biological identities. No health/disease conclusions are generated.
    """
    def __init__(self, track_id: int, initial_bbox: List[float], initial_zone: str, timestamp: float):
        self.track_id = int(track_id)
        self.first_seen = timestamp
        self.last_seen = timestamp
        
        # Bounding box & position: [x1, y1, x2, y2]
        self.bbox = [float(x) for x in initial_bbox]
        self.center_x = (self.bbox[0] + self.bbox[2]) / 2.0
        self.center_y = (self.bbox[1] + self.bbox[3]) / 2.0
        
        # Behavior attributes
        self.current_behavior = "unknown"
        self.stable_behavior = "unknown"
        self.behavior_confidence = 0.0
        self.last_behavior_timestamp = 0.0
        self.is_behavior_fresh = False # True only on frames where model inference occurred
        
        # Zone tracking
        self.current_zone = initial_zone
        self.previous_zone = initial_zone
        self.candidate_zone = initial_zone
        self.candidate_zone_count = 0
        self.zone_entry_time = timestamp
        self.zone_history: List[Dict[str, Any]] = [
            {"zone": initial_zone, "timestamp": timestamp}
        ]
        self.zone_transition_count = 0

        # Movement tracking
        self.position_history = deque(maxlen=60) # Store (timestamp, cx, cy)
        self.position_history.append((timestamp, self.center_x, self.center_y))
        self.distance_travelled_pixels = 0.0
        self.movement_rate_pixels_per_second = 0.0
        self.stationary_duration = 0.0
        self.last_stationary_check_time = timestamp

        # Tracking status: ACTIVE, TEMPORARILY_LOST, RECOVERED, ENDED
        self.tracking_status = "ACTIVE"
        self.frames_since_update = 0

        # Reserved future fields (kept null per specification)
        self.audio_risk = None
        self.camera_risk = None
        self.overall_risk = None

        # Camera Anomaly / Behavioral Deviation fields
        self.camera_anomaly_score: Optional[float] = None
        self.camera_anomaly_status: str = "NORMAL_PATTERN"
        self.camera_anomaly_reasons: List[str] = []
        self.camera_anomaly_timestamp: Optional[float] = None
        self.camera_anomaly_raw_score: Optional[float] = None
        self.camera_anomaly_validation_status: str = "PROTOTYPE_ONLY_SYNTHETIC_DATA"
        self.anomaly_score_history: deque = deque(maxlen=5) # Rolling window for persistence and smoothing

    def update_camera_anomaly(
        self, 
        deviation_score: float, 
        status: str, 
        reasons: List[str], 
        timestamp: float,
        raw_anomaly_score: Optional[float] = None,
        alpha: float = 0.35
    ):
        """
        Updates camera anomaly fields with exponential rolling score smoothing and decay.
        Avoids abrupt transient spikes and handles gradual normalization if behavior returns to baseline.
        """
        self.anomaly_score_history.append(float(deviation_score))
        
        # Apply smoothing over history
        if self.camera_anomaly_score is None:
            self.camera_anomaly_score = float(deviation_score)
        else:
            # Exponential moving average
            self.camera_anomaly_score = round(alpha * deviation_score + (1.0 - alpha) * self.camera_anomaly_score, 1)

        # Update status according to smoothed score
        if self.camera_anomaly_score >= 70.0:
            self.camera_anomaly_status = "HIGH_DEVIATION"
        elif self.camera_anomaly_score >= 45.0:
            self.camera_anomaly_status = "WATCH_DEVIATION"
        else:
            self.camera_anomaly_status = "NORMAL_PATTERN"

        self.camera_anomaly_reasons = list(reasons)
        self.camera_anomaly_timestamp = float(timestamp)
        self.camera_anomaly_raw_score = float(raw_anomaly_score) if raw_anomaly_score is not None else None
        self.camera_anomaly_validation_status = "PROTOTYPE_ONLY_SYNTHETIC_DATA"

    def update_position(self, bbox: List[float], timestamp: float, stationary_thresh: float = 15.0):
        """Updates spatial position and computes movement dynamics."""
        self.bbox = [float(x) for x in bbox]
        new_cx = (self.bbox[0] + self.bbox[2]) / 2.0
        new_cy = (self.bbox[1] + self.bbox[3]) / 2.0
        
        dt = max(1e-4, timestamp - self.last_seen)
        dx = new_cx - self.center_x
        dy = new_cy - self.center_y
        displacement = float(np.hypot(dx, dy))

        self.distance_travelled_pixels += displacement
        current_speed = displacement / dt

        # Exponential moving average for speed
        if self.movement_rate_pixels_per_second == 0.0:
            self.movement_rate_pixels_per_second = current_speed
        else:
            self.movement_rate_pixels_per_second = 0.7 * self.movement_rate_pixels_per_second + 0.3 * current_speed

        # Stationary tracking
        if displacement < stationary_thresh:
            self.stationary_duration += dt
        else:
            self.stationary_duration = 0.0

        self.center_x = new_cx
        self.center_y = new_cy
        self.last_seen = timestamp
        self.position_history.append((timestamp, new_cx, new_cy))
        self.frames_since_update = 0
        if self.tracking_status == "TEMPORARILY_LOST":
            self.tracking_status = "RECOVERED"
        else:
            self.tracking_status = "ACTIVE"

    def update_zone(self, detected_zone: str, timestamp: float, debounce_frames: int = 3) -> Optional[Dict[str, Any]]:
        """
        Updates zone with debouncing to prevent boundary jitter.
        Returns event dict if a transition is confirmed, otherwise None.
        """
        if detected_zone == self.current_zone:
            self.candidate_zone = detected_zone
            self.candidate_zone_count = 0
            return None

        # Zone candidate logic
        if detected_zone == self.candidate_zone:
            self.candidate_zone_count += 1
        else:
            self.candidate_zone = detected_zone
            self.candidate_zone_count = 1

        if self.candidate_zone_count >= debounce_frames:
            from_z = self.current_zone
            to_z = self.candidate_zone
            self.previous_zone = from_z
            self.current_zone = to_z
            self.zone_entry_time = timestamp
            self.zone_transition_count += 1
            self.candidate_zone_count = 0
            
            event = {
                "event": "ZONE_TRANSITION",
                "track_id": self.track_id,
                "from_zone": from_z,
                "to_zone": to_z,
                "timestamp": round(timestamp, 3)
            }
            self.zone_history.append({"zone": to_z, "timestamp": timestamp})
            return event

        return None

    def update_behavior(self, behavior: str, confidence: float, timestamp: float, stable_behavior: str):
        """Attaches a fresh Roboflow behavior observation."""
        self.current_behavior = behavior
        self.behavior_confidence = float(confidence)
        self.last_behavior_timestamp = timestamp
        self.stable_behavior = stable_behavior
        self.is_behavior_fresh = True

    def mark_frame_without_inference(self):
        """Called on frames where no behavior model inference was executed."""
        self.is_behavior_fresh = False

    def mark_lost(self):
        self.tracking_status = "TEMPORARILY_LOST"
        self.frames_since_update += 1

    def mark_ended(self):
        self.tracking_status = "ENDED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "status": self.tracking_status,
            "bbox": [round(x, 1) for x in self.bbox],
            "position": [round(self.center_x, 1), round(self.center_y, 1)],
            "current_behavior": self.current_behavior,
            "stable_behavior": self.stable_behavior,
            "behavior_confidence": round(self.behavior_confidence, 3),
            "behavior_age_seconds": round(max(0.0, self.last_seen - self.last_behavior_timestamp), 2) if self.last_behavior_timestamp > 0 else None,
            "current_zone": self.current_zone,
            "previous_zone": self.previous_zone,
            "movement_rate_pixels_per_sec": round(self.movement_rate_pixels_per_second, 1),
            "distance_travelled_pixels": round(self.distance_travelled_pixels, 1),
            "stationary_duration_seconds": round(self.stationary_duration, 1),
            "first_seen": round(self.first_seen, 2),
            "last_seen": round(self.last_seen, 2),
            "camera_anomaly_score": self.camera_anomaly_score,
            "camera_anomaly_status": self.camera_anomaly_status,
            "camera_anomaly_reasons": self.camera_anomaly_reasons,
            "camera_anomaly_timestamp": self.camera_anomaly_timestamp,
            "camera_anomaly_validation_status": self.camera_anomaly_validation_status
        }
