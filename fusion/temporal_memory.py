"""
Temporal Memory & Behavioral Persistence Engine for FlockSense.
Tracks multi-window behavioral history per bird, applies exponential smoothing,
measures persistence of elevated deviations, and handles graceful score decay.
"""

from collections import deque
from typing import Dict, List, Any, Optional, Tuple

class TrackTemporalMemory:
    """
    Maintains historical behavioral states and scores for an individual Track ID.
    Enables:
    1. Rejection of isolated one-off transient spikes.
    2. Detection of sustained, persistent behavioral deviation across multiple windows.
    3. Graceful decay back towards baseline when behavior normalizes.
    4. Migration of risk and initial evidence zone as the bird transitions between zones.
    """
    def __init__(
        self,
        track_id: int,
        history_length: int = 6,
        smoothing_alpha: float = 0.35,
        decay_rate: float = 0.25,
        initial_zone: str = "UNKNOWN"
    ):
        self.track_id = int(track_id)
        self.history_length = int(history_length)
        self.smoothing_alpha = float(smoothing_alpha)
        self.decay_rate = float(decay_rate)
        
        # Zone tracking
        self.initial_evidence_zone = initial_zone
        self.current_zone = initial_zone
        self.previous_zone = initial_zone
        self.has_recorded_evidence = False

        # Temporal buffers: deque of tuples (timestamp, raw_dev_score, smoothed_dev_score)
        self.history: deque = deque(maxlen=history_length)
        self.smoothed_score: float = 0.0
        self.consecutive_elevated_windows: int = 0
        self.total_elevated_windows: int = 0
        self.last_update_timestamp: float = 0.0
        self.tracking_status: str = "ACTIVE" # ACTIVE, TEMPORARILY_LOST, TRACK_ENDED

    def add_observation(
        self,
        raw_deviation_score: float,
        current_zone: str,
        timestamp: float,
        camera_status: str = "NORMAL_PATTERN"
    ) -> float:
        """
        Ingests a new temporal window observation for this track.
        Updates zone position while preserving initial evidence zone.
        Computes smoothed score and updates elevated counter.
        """
        self.last_update_timestamp = float(timestamp)
        self.previous_zone = self.current_zone
        self.current_zone = current_zone

        # Track first zone where significant deviation was witnessed
        if not self.has_recorded_evidence and raw_deviation_score >= 45.0:
            self.initial_evidence_zone = current_zone
            self.has_recorded_evidence = True
        elif not self.has_recorded_evidence:
            self.initial_evidence_zone = current_zone

        # Exponential smoothing update
        if not self.history:
            self.smoothed_score = float(raw_deviation_score)
        else:
            self.smoothed_score = round(
                self.smoothing_alpha * float(raw_deviation_score) + 
                (1.0 - self.smoothing_alpha) * self.smoothed_score, 
                1
            )

        # Track persistent elevation (> 45.0 is WATCH or HIGH)
        if raw_deviation_score >= 45.0:
            self.consecutive_elevated_windows += 1
            self.total_elevated_windows += 1
        else:
            # When bird returns to baseline, decay consecutive count
            self.consecutive_elevated_windows = max(0, self.consecutive_elevated_windows - 1)

        self.history.append((timestamp, raw_deviation_score, self.smoothed_score))
        return self.smoothed_score

    def compute_persistence_score(self) -> float:
        """
        Computes a persistence score (0 to 100) indicating the temporal sustained nature
        of abnormal observations.
        - Single isolated spikes produce a low persistence score (< 30).
        - Multiple consecutive or sustained elevated windows produce a high persistence score (> 70).
        """
        if not self.history:
            return 0.0

        recent_scores = [h[1] for h in self.history]
        elevated_count = sum(1 for s in recent_scores if s >= 45.0)
        elevated_ratio = elevated_count / float(len(recent_scores))

        # Weight consecutive duration and historical elevated fraction
        streak_bonus = min(40.0, self.consecutive_elevated_windows * 15.0)
        fraction_component = elevated_ratio * 60.0

        persistence = min(100.0, streak_bonus + fraction_component)
        return round(persistence, 1)

    def apply_decay(self, elapsed_seconds: float, decay_interval: float = 20.0):
        """
        Applies gradual decay to smoothed score when no fresh abnormal observations arrive.
        """
        if elapsed_seconds <= 0:
            return
        decay_factor = max(0.5, 1.0 - (self.decay_rate * (elapsed_seconds / decay_interval)))
        self.smoothed_score = round(self.smoothed_score * decay_factor, 1)


class TemporalMemoryManager:
    """
    Manages track-level temporal memories across all monitored birds in the session.
    """
    def __init__(self, history_length: int = 6, smoothing_alpha: float = 0.35, decay_rate: float = 0.25):
        self.history_length = history_length
        self.smoothing_alpha = smoothing_alpha
        self.decay_rate = decay_rate
        self.track_memories: Dict[int, TrackTemporalMemory] = {}

    def get_or_create(self, track_id: int, initial_zone: str = "UNKNOWN") -> TrackTemporalMemory:
        if track_id not in self.track_memories:
            self.track_memories[track_id] = TrackTemporalMemory(
                track_id=track_id,
                history_length=self.history_length,
                smoothing_alpha=self.smoothing_alpha,
                decay_rate=self.decay_rate,
                initial_zone=initial_zone
            )
        return self.track_memories[track_id]

    def update_track(
        self,
        track_id: int,
        raw_deviation_score: float,
        current_zone: str,
        timestamp: float,
        camera_status: str = "NORMAL_PATTERN"
    ) -> Tuple[float, float]:
        """
        Updates memory for a track and returns (smoothed_deviation_score, persistence_score).
        """
        mem = self.get_or_create(track_id, initial_zone=current_zone)
        smoothed = mem.add_observation(raw_deviation_score, current_zone, timestamp, camera_status)
        persistence = mem.compute_persistence_score()
        return smoothed, persistence

    def mark_lost(self, track_id: int):
        if track_id in self.track_memories:
            self.track_memories[track_id].tracking_status = "TEMPORARILY_LOST"

    def mark_ended(self, track_id: int):
        if track_id in self.track_memories:
            self.track_memories[track_id].tracking_status = "TRACK_ENDED"

    def get_all_active_track_ids(self) -> List[int]:
        return [tid for tid, m in self.track_memories.items() if m.tracking_status != "TRACK_ENDED"]
