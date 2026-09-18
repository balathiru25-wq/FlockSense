from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import supervision as sv

try:
    from .track_state import TrackState
    from .behavior_history import BehaviorHistoryManager
    from .zone_manager import ZoneManager
except ImportError:
    from track_state import TrackState
    from behavior_history import BehaviorHistoryManager
    from zone_manager import ZoneManager

def calculate_iou(boxA: List[float], boxB: List[float]) -> float:
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0.0, xB - xA) * max(0.0, yB - yA)
    boxAArea = max(1e-4, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    boxBArea = max(1e-4, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))

    iou = interArea / float(boxAArea + boxBArea - interArea)
    return iou

class BehaviorTracker:
    """
    Multi-Object Tracker leveraging Supervision ByteTrack.
    
    IMPORTANT TRACKING RULE:
    Detections are mapped to the generic class 'CHICKEN' for tracking.
    Specific behaviors (feeding, standing, sitting, spreading) are NEVER passed
    as separate tracking classes to prevent track ID fragmentation when a bird
    changes its physical behavior.
    """
    def __init__(
        self,
        zone_manager: ZoneManager,
        behavior_history: BehaviorHistoryManager,
        lost_track_buffer: int = 30,
        frame_rate: int = 30,
        minimum_matching_threshold: float = 0.80,
        debounce_frames: int = 3,
        stale_threshold_seconds: float = 4.0
    ):
        self.zone_manager = zone_manager
        self.behavior_history = behavior_history
        self.debounce_frames = debounce_frames
        self.stale_threshold_seconds = stale_threshold_seconds

        # ByteTrack instance from supervision
        self.tracker = sv.ByteTrack(
            track_activation_threshold=0.25,
            lost_track_buffer=lost_track_buffer,
            minimum_matching_threshold=minimum_matching_threshold,
            frame_rate=frame_rate
        )

        # Active tracks: track_id -> TrackState
        self.active_tracks: Dict[int, TrackState] = {}
        # Historical ended tracks for query functions
        self.ended_tracks: Dict[int, TrackState] = {}

        # Tracking events logged during execution
        self.events_log: List[Dict[str, Any]] = []

    def update(
        self,
        roboflow_predictions: Optional[List[Dict[str, Any]]],
        frame_w: int,
        frame_h: int,
        timestamp: float,
        frame_idx: int
    ) -> List[TrackState]:
        """
        Processes a video frame.
        - If roboflow_predictions is provided (inference frame): feeds detections to tracker.
        - If roboflow_predictions is None (skipped frame): updates tracks with empty/cached detections.
        """
        events_this_frame = []

        if roboflow_predictions is not None and len(roboflow_predictions) > 0:
            # 1. Convert all predictions to generic CHICKEN detections for ByteTrack
            xyxy_list = []
            confidence_list = []
            class_id_list = []

            for p in roboflow_predictions:
                bbox = p["bbox"]
                xyxy_list.append(bbox)
                confidence_list.append(float(p["confidence"]))
                class_id_list.append(0) # Generic 0 = CHICKEN

            detections = sv.Detections(
                xyxy=np.array(xyxy_list, dtype=np.float32),
                confidence=np.array(confidence_list, dtype=np.float32),
                class_id=np.array(class_id_list, dtype=int)
            )

            # 2. Run ByteTrack
            tracked_detections = self.tracker.update_with_detections(detections)
            matched_track_ids = set()

            if tracked_detections.tracker_id is not None:
                for i in range(len(tracked_detections.xyxy)):
                    track_id = int(tracked_detections.tracker_id[i])
                    track_box = tracked_detections.xyxy[i].tolist()
                    matched_track_ids.add(track_id)

                    center_pt = ((track_box[0] + track_box[2]) / 2.0, (track_box[1] + track_box[3]) / 2.0)
                    zone_id = self.zone_manager.get_zone_for_point(center_pt, frame_w, frame_h)

                    # Associate with closest/highest-IoU Roboflow prediction for behavior
                    best_pred = None
                    best_iou = 0.20 # Minimum threshold
                    for p in roboflow_predictions:
                        iou = calculate_iou(track_box, p["bbox"])
                        if iou > best_iou:
                            best_iou = iou
                            best_pred = p

                    # Existing track or new track
                    if track_id not in self.active_tracks:
                        # Check if it was previously ended/lost
                        t_state = TrackState(track_id, track_box, zone_id, timestamp)
                        self.active_tracks[track_id] = t_state
                        events_this_frame.append({
                            "timestamp": round(timestamp, 3),
                            "frame": frame_idx,
                            "track_id": track_id,
                            "event": "TRACK_STARTED",
                            "previous_zone": None,
                            "current_zone": zone_id,
                            "behavior": "unknown",
                            "behavior_confidence": 0.0
                        })
                    else:
                        t_state = self.active_tracks[track_id]
                        t_state.update_position(track_box, timestamp)

                    # Update zone with debounce
                    z_event = t_state.update_zone(zone_id, timestamp, debounce_frames=self.debounce_frames)
                    if z_event:
                        events_this_frame.append({
                            "timestamp": round(timestamp, 3),
                            "frame": frame_idx,
                            "track_id": track_id,
                            "event": "ZONE_TRANSITION",
                            "previous_zone": z_event["from_zone"],
                            "current_zone": z_event["to_zone"],
                            "behavior": t_state.stable_behavior,
                            "behavior_confidence": t_state.behavior_confidence
                        })

                    # Update behavior if matched
                    if best_pred:
                        raw_behavior = best_pred["behavior"]
                        conf = best_pred["confidence"]
                        stable_beh = self.behavior_history.add_behavior_observation(
                            track_id, raw_behavior, conf, timestamp
                        )
                        prev_stable = t_state.stable_behavior
                        t_state.update_behavior(raw_behavior, conf, timestamp, stable_beh)

                        if prev_stable != "unknown" and prev_stable != stable_beh:
                            events_this_frame.append({
                                "timestamp": round(timestamp, 3),
                                "frame": frame_idx,
                                "track_id": track_id,
                                "event": "BEHAVIOR_CHANGED",
                                "previous_zone": t_state.previous_zone,
                                "current_zone": t_state.current_zone,
                                "behavior": stable_beh,
                                "behavior_confidence": conf
                            })
                    else:
                        t_state.mark_frame_without_inference()

            # Mark lost tracks
            for tid, t_state in list(self.active_tracks.items()):
                if tid not in matched_track_ids:
                    t_state.mark_lost()
                    if t_state.frames_since_update == 1:
                        events_this_frame.append({
                            "timestamp": round(timestamp, 3),
                            "frame": frame_idx,
                            "track_id": tid,
                            "event": "TRACK_LOST",
                            "previous_zone": t_state.previous_zone,
                            "current_zone": t_state.current_zone,
                            "behavior": t_state.stable_behavior,
                            "behavior_confidence": t_state.behavior_confidence
                        })
                    elif t_state.frames_since_update > 45: # Timeout
                        t_state.mark_ended()
                        self.ended_tracks[tid] = t_state
                        del self.active_tracks[tid]
                        events_this_frame.append({
                            "timestamp": round(timestamp, 3),
                            "frame": frame_idx,
                            "track_id": tid,
                            "event": "TRACK_ENDED",
                            "previous_zone": t_state.previous_zone,
                            "current_zone": t_state.current_zone,
                            "behavior": t_state.stable_behavior,
                            "behavior_confidence": t_state.behavior_confidence
                        })

        else:
            # Skipped frame (no fresh Roboflow inference)
            # Detections empty -> tracker maintains internal positions
            empty_det = sv.Detections.empty()
            tracked_detections = self.tracker.update_with_detections(empty_det)
            matched_track_ids = set()

            if tracked_detections.tracker_id is not None and len(tracked_detections.xyxy) > 0:
                for i in range(len(tracked_detections.xyxy)):
                    track_id = int(tracked_detections.tracker_id[i])
                    track_box = tracked_detections.xyxy[i].tolist()
                    matched_track_ids.add(track_id)

                    if track_id in self.active_tracks:
                        t_state = self.active_tracks[track_id]
                        t_state.update_position(track_box, timestamp)
                        t_state.mark_frame_without_inference()
                        center_pt = ((track_box[0] + track_box[2]) / 2.0, (track_box[1] + track_box[3]) / 2.0)
                        zone_id = self.zone_manager.get_zone_for_point(center_pt, frame_w, frame_h)
                        z_event = t_state.update_zone(zone_id, timestamp, debounce_frames=self.debounce_frames)
                        if z_event:
                            events_this_frame.append({
                                "timestamp": round(timestamp, 3),
                                "frame": frame_idx,
                                "track_id": track_id,
                                "event": "ZONE_TRANSITION",
                                "previous_zone": z_event["from_zone"],
                                "current_zone": z_event["to_zone"],
                                "behavior": t_state.stable_behavior,
                                "behavior_confidence": t_state.behavior_confidence
                            })

            for tid, t_state in list(self.active_tracks.items()):
                if tid not in matched_track_ids:
                    t_state.mark_lost()
                    t_state.mark_frame_without_inference()

        self.events_log.extend(events_this_frame)
        return list(self.active_tracks.values())

    # --- Query API ---
    def get_track_state(self, track_id: int) -> Optional[TrackState]:
        return self.active_tracks.get(track_id) or self.ended_tracks.get(track_id)

    def get_track_history(self, track_id: int) -> List[Tuple[float, float, float]]:
        t_state = self.get_track_state(track_id)
        return list(t_state.position_history) if t_state else []

    def get_behavior_history(self, track_id: int) -> List[Dict[str, Any]]:
        return self.behavior_history.get_behavior_history(track_id)

    def get_zone_history(self, track_id: int) -> List[Dict[str, Any]]:
        t_state = self.get_track_state(track_id)
        return list(t_state.zone_history) if t_state else []

    def get_tracks_in_zone(self, zone_id: str, timestamp: Optional[float] = None) -> List[int]:
        return [
            tid for tid, t in self.active_tracks.items()
            if t.current_zone == zone_id and t.tracking_status in ["ACTIVE", "RECOVERED"]
        ]

    def get_behavior_features(self, track_id: int) -> Dict[str, Any]:
        t_state = self.get_track_state(track_id)
        duration = (t_state.last_seen - t_state.first_seen) if t_state else 0.0
        beh_feat = self.behavior_history.get_behavior_features(track_id, total_duration=duration)
        if t_state:
            beh_feat.update({
                "track_id": track_id,
                "current_zone": t_state.current_zone,
                "time_in_current_zone": round(max(0.0, t_state.last_seen - t_state.zone_entry_time), 1),
                "zone_transition_count": t_state.zone_transition_count,
                "movement_rate": round(t_state.movement_rate_pixels_per_second, 1),
                "stationary_duration": round(t_state.stationary_duration, 1),
                "distance_travelled": round(t_state.distance_travelled_pixels, 1)
            })
        return beh_feat
