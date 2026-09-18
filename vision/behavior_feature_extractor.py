import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import numpy as np

# Valid behaviors recognized by Roboflow chicken behavior model
RECOGNIZED_BEHAVIORS = ["standing", "feeding", "sitting", "spreading", "preening", "resting", "walking"]

class BehaviorFeatureExtractor:
    """
    Extracts multi-dimensional behavioral, spatial, and social features
    for tracked poultry over rolling temporal windows (e.g., 30s, 60s, 120s).
    
    IMPORTANT: Features represent observable activity only. No disease or medical
    interpretation is inferred.
    """
    def __init__(self, window_duration_seconds: float = 30.0, frame_width: int = 960, frame_height: int = 540):
        self.window_duration_seconds = float(window_duration_seconds)
        self.frame_width = frame_width
        self.frame_height = frame_height
        # Frame diagonal for spatial normalization
        self.frame_diagonal = float(np.hypot(frame_width, frame_height)) if (frame_width > 0 and frame_height > 0) else 1000.0

    def extract_features_from_logs(
        self,
        jsonl_path: str = "outputs/vision/logs/tracking_data.jsonl",
        events_csv_path: str = "outputs/vision/logs/track_events.csv"
    ) -> List[Dict[str, Any]]:
        """
        Parses tracking_data.jsonl and track_events.csv to compute rolling window feature vectors.
        """
        jsonl_file = Path(jsonl_path)
        if not jsonl_file.exists():
            raise FileNotFoundError(f"Tracking log not found: {jsonl_path}")

        # 1. Load frame records: list of {"timestamp": float, "frame": int, "tracks": [...]}
        frames = []
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    frames.append(json.loads(line))

        if not frames:
            return []

        # 2. Group records by time windows
        min_time = frames[0]["timestamp"]
        max_time = frames[-1]["timestamp"]
        duration = max_time - min_time

        # Step size is half the window (50% rolling overlap) or full duration if shorter
        step = max(5.0, self.window_duration_seconds / 2.0)
        
        # If total sequence duration is less than requested window, create at least one window covering all frames
        if duration <= self.window_duration_seconds:
            windows_ranges = [(min_time, max_time)]
        else:
            windows_ranges = []
            cur_start = min_time
            while cur_start + self.window_duration_seconds <= max_time + 1e-4:
                windows_ranges.append((cur_start, cur_start + self.window_duration_seconds))
                cur_start += step
            if not windows_ranges:
                windows_ranges.append((min_time, max_time))

        all_feature_rows = []

        # Load events for transition counting
        events_by_track = defaultdict(list)
        events_csv = Path(events_csv_path)
        if events_csv.exists():
            with open(events_csv, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    tid = int(row["track_id"])
                    events_by_track[tid].append(row)

        for w_start, w_end in windows_ranges:
            # Filter frames within window
            window_frames = [f for f in frames if w_start <= f["timestamp"] <= w_end]
            if not window_frames:
                continue

            # Group frames by track_id inside window
            tracks_in_window = defaultdict(list)
            for f in window_frames:
                ts = f["timestamp"]
                flock_positions = [t["position"] for t in f["tracks"]]
                
                # Compute flock centroid at this frame
                if flock_positions:
                    cx = np.mean([p[0] for p in flock_positions])
                    cy = np.mean([p[1] for p in flock_positions])
                    flock_centroid = (cx, cy)
                else:
                    flock_centroid = (self.frame_width / 2.0, self.frame_height / 2.0)

                for t in f["tracks"]:
                    tid = t["track_id"]
                    t_copy = dict(t)
                    t_copy["timestamp"] = ts
                    t_copy["flock_centroid"] = flock_centroid
                    t_copy["other_positions"] = [p for p in flock_positions if p != t["position"]]
                    tracks_in_window[tid].append(t_copy)

            # Compute flock-wide median movement rate in this window
            all_movement_rates = []
            for tid, samples in tracks_in_window.items():
                all_movement_rates.extend([s.get("movement_rate", 0.0) for s in samples])
            flock_median_movement = float(np.median(all_movement_rates)) if all_movement_rates else 0.0

            # Compute features for each bird in window
            for tid, samples in tracks_in_window.items():
                if len(samples) < 2:
                    continue

                feat = self._compute_bird_window_features(
                    tid=tid,
                    samples=samples,
                    w_start=w_start,
                    w_end=w_end,
                    flock_median_movement=flock_median_movement,
                    events=events_by_track.get(tid, [])
                )
                all_feature_rows.append(feat)

        return all_feature_rows

    def _compute_bird_window_features(
        self,
        tid: int,
        samples: List[Dict[str, Any]],
        w_start: float,
        w_end: float,
        flock_median_movement: float,
        events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculates granular features for one track inside one temporal window."""
        t_start = samples[0]["timestamp"]
        t_end = samples[-1]["timestamp"]
        track_dur = max(0.1, t_end - t_start)

        # 1. Movement features
        speeds = [s.get("movement_rate", 0.0) for s in samples]
        mean_speed = float(np.mean(speeds))
        max_speed = float(np.max(speeds))
        speed_var = float(np.var(speeds))

        # Total distance
        positions = [s["position"] for s in samples]
        total_dist = 0.0
        stationary_count = 0
        burst_count = 0
        for i in range(1, len(positions)):
            disp = np.hypot(positions[i][0] - positions[i-1][0], positions[i][1] - positions[i-1][1])
            total_dist += disp
            if disp < 3.0: # Movement per step threshold
                stationary_count += 1
            elif disp > 25.0: # Burst threshold
                burst_count += 1

        stationary_ratio = float(stationary_count / max(1, len(positions) - 1))
        stationary_duration = stationary_ratio * track_dur

        # 2. Behavior features
        behaviors = [s.get("behavior", "unknown").lower() for s in samples]
        n_beh = len(behaviors)
        beh_counts = defaultdict(int)
        for b in behaviors:
            beh_counts[b] += 1

        # Calculate ratios for all recognized behaviors
        beh_ratios = {}
        for b in RECOGNIZED_BEHAVIORS:
            beh_ratios[f"{b}_ratio"] = round(beh_counts.get(b, 0) / float(n_beh), 3)

        # Behavior transitions within window
        window_events = [e for e in events if w_start <= float(e["timestamp"]) <= w_end]
        beh_trans = [e for e in window_events if e["event"] == "BEHAVIOR_CHANGED"]
        beh_trans_count = len(beh_trans)
        beh_trans_rate = round(beh_trans_count / track_dur, 3)

        # Zone transitions
        zone_trans = [e for e in window_events if e["event"] == "ZONE_TRANSITION"]
        zone_trans_count = len(zone_trans)

        # 3. Isolation & Social Features
        dist_to_nearest_list = []
        dist_to_flock_list = []
        isolation_scores = []

        for s in samples:
            px, py = s["position"]
            fcx, fcy = s["flock_centroid"]
            dist_flock = np.hypot(px - fcx, py - fcy)
            dist_to_flock_list.append(dist_flock)

            others = s.get("other_positions", [])
            if others:
                dists = [np.hypot(px - ox, py - oy) for ox, oy in others]
                nearest = min(dists)
            else:
                nearest = self.frame_diagonal / 2.0
            dist_to_nearest_list.append(nearest)

            # Isolation score: ratio of distance to nearest relative to frame diagonal
            isolation_scores.append(nearest / self.frame_diagonal)

        mean_nearest_bird = float(np.mean(dist_to_nearest_list))
        mean_flock_dist = float(np.mean(dist_to_flock_list))
        relative_isolation_score = float(np.mean(isolation_scores))

        # 4. Relative Activity vs Flock Median
        if flock_median_movement > 1e-3:
            relative_activity = mean_speed / flock_median_movement
        else:
            relative_activity = 1.0 if mean_speed < 1.0 else 2.0

        current_zone = samples[-1].get("zone", "UNKNOWN")
        current_behavior = samples[-1].get("behavior", "unknown")

        row = {
            "timestamp_start": round(w_start, 2),
            "timestamp_end": round(w_end, 2),
            "track_id": tid,
            "current_zone": current_zone,
            "current_behavior": current_behavior,
            "track_duration": round(track_dur, 2),
            "movement_rate": round(mean_speed, 2),
            "maximum_movement_rate": round(max_speed, 2),
            "movement_variance": round(speed_var, 2),
            "distance_travelled_pixels": round(total_dist, 1),
            "stationary_duration": round(stationary_duration, 2),
            "stationary_ratio": round(stationary_ratio, 3),
            "movement_burst_count": burst_count,
            **beh_ratios,
            "behaviour_transition_count": beh_trans_count,
            "behaviour_transition_rate": beh_trans_rate,
            "distance_to_nearest_bird": round(mean_nearest_bird, 1),
            "distance_to_flock_centroid": round(mean_flock_dist, 1),
            "relative_isolation_score": round(relative_isolation_score, 4),
            "relative_activity": round(relative_activity, 3),
            "zone_transition_count": zone_trans_count
        }
        return row

    def save_features_to_csv(self, features: List[Dict[str, Any]], output_csv: str = "outputs/vision/features/bird_behavior_features.csv"):
        out_path = Path(output_csv)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if not features:
            print(f"Warning: No features to save to {output_csv}")
            return

        fieldnames = list(features[0].keys())
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(features)
        print(f"Saved {len(features)} feature window rows to: {out_path}")

if __name__ == "__main__":
    extractor = BehaviorFeatureExtractor(window_duration_seconds=5.0)
    feats = extractor.extract_features_from_logs()
    extractor.save_features_to_csv(feats)
