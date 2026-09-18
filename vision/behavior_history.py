from collections import defaultdict, deque
from typing import Dict, List, Any, Optional

class BehaviorHistoryManager:
    """
    Maintains per-bird behavior history and computes smoothed stable behaviors.
    
    IMPORTANT: This history is strictly indexed by Track ID, NOT by zone.
    Only genuine model inference events are recorded.
    """
    def __init__(self, smoothing_window: int = 5):
        self.smoothing_window = smoothing_window
        # track_id -> list of raw inference events: [{"timestamp": float, "behavior": str, "confidence": float}]
        self.history_records: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        # track_id -> recent deque for smoothing
        self.recent_predictions: Dict[int, deque] = defaultdict(lambda: deque(maxlen=self.smoothing_window))
        # track_id -> list of confirmed behavior changes: [{"from": str, "to": str, "timestamp": float}]
        self.behavior_transitions: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        self.previous_stable_behavior: Dict[int, str] = {}

    def add_behavior_observation(self, track_id: int, behavior: str, confidence: float, timestamp: float) -> str:
        """
        Records a genuine model prediction for track_id and returns the smoothed stable behavior.
        """
        event = {
            "timestamp": round(timestamp, 3),
            "behavior": behavior.lower(),
            "confidence": float(confidence)
        }
        self.history_records[track_id].append(event)
        self.recent_predictions[track_id].append((behavior.lower(), float(confidence)))

        stable_behavior = self._compute_stable_behavior(track_id)

        # Check for stable behavior transition
        prev_stable = self.previous_stable_behavior.get(track_id)
        if prev_stable is not None and prev_stable != stable_behavior:
            self.behavior_transitions[track_id].append({
                "from": prev_stable,
                "to": stable_behavior,
                "timestamp": round(timestamp, 3)
            })
        self.previous_stable_behavior[track_id] = stable_behavior

        return stable_behavior

    def _compute_stable_behavior(self, track_id: int) -> str:
        """
        Confidence-weighted majority vote across recent model predictions.
        """
        preds = self.recent_predictions[track_id]
        if not preds:
            return "unknown"

        weighted_votes: Dict[str, float] = defaultdict(float)
        for beh, conf in preds:
            weighted_votes[beh] += max(0.1, conf)

        best_behavior = max(weighted_votes.items(), key=lambda x: x[1])[0]
        return best_behavior

    def get_behavior_history(self, track_id: int) -> List[Dict[str, Any]]:
        """Returns chronological list of genuine model behavior predictions for this track."""
        return self.history_records.get(track_id, [])

    def get_behavior_features(self, track_id: int, total_duration: float = 0.0) -> Dict[str, Any]:
        """
        Computes behavior metrics (ratios, transitions) without health interpretation.
        """
        records = self.history_records.get(track_id, [])
        if not records:
            return {
                "total_observations": 0,
                "feeding_ratio": 0.0,
                "standing_ratio": 0.0,
                "sitting_ratio": 0.0,
                "spreading_ratio": 0.0,
                "behavior_transition_rate": 0.0
            }

        counts: Dict[str, int] = defaultdict(int)
        for r in records:
            counts[r["behavior"]] += 1

        n = len(records)
        transitions = self.behavior_transitions.get(track_id, [])
        dt = max(1.0, total_duration)

        return {
            "total_observations": n,
            "feeding_ratio": round(counts.get("feeding", 0) / float(n), 3),
            "standing_ratio": round(counts.get("standing", 0) / float(n), 3),
            "sitting_ratio": round(counts.get("sitting", 0) / float(n), 3),
            "spreading_ratio": round(counts.get("spreading", 0) / float(n), 3),
            "behavior_transitions_count": len(transitions),
            "behavior_transition_rate": round(len(transitions) / dt, 3)
        }
