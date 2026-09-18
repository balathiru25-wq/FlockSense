from typing import List, Dict, Any, Optional
import cv2
import numpy as np

try:
    from .track_state import TrackState
    from .zone_manager import ZoneManager
except ImportError:
    from track_state import TrackState
    from zone_manager import ZoneManager

# Distinct colors for behaviors
BEHAVIOR_COLORS = {
    "feeding": (0, 200, 0),      # Green
    "standing": (255, 180, 0),   # Cyan / Light Blue
    "sitting": (0, 140, 255),    # Orange
    "spreading": (0, 0, 255),    # Red
    "preening": (255, 0, 200),   # Purple
    "resting": (180, 100, 255),  # Violet
    "walking": (255, 255, 0),    # Yellow
    "unknown": (180, 180, 180)   # Gray
}

def get_behavior_color(behavior_name: str):
    return BEHAVIOR_COLORS.get(behavior_name.lower(), (200, 200, 200))

class VisionVisualizer:
    """
    Renders bounding boxes, track IDs, stable behaviors, virtual zones,
    and the global flock behavior statistics overlay.
    """
    def __init__(self, zone_manager: ZoneManager):
        self.zone_manager = zone_manager

    def draw_zones(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        overlay = frame.copy()

        for z in self.zone_manager.get_all_zones():
            pts = []
            for norm_pt in z["polygon"]:
                px = int(norm_pt[0] * w)
                py = int(norm_pt[1] * h)
                pts.append([px, py])
            pts_np = np.array(pts, dtype=np.int32).reshape((-1, 1, 2))

            color = tuple(z.get("color_bgr", [255, 255, 255]))
            cv2.polylines(overlay, [pts_np], isClosed=True, color=color, thickness=2)

            # Zone label at top center of polygon
            lbl_x = int(pts[0][0] + 10)
            lbl_y = int(pts[0][1] + 25)
            cv2.putText(overlay, z["zone_id"], (lbl_x, lbl_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)

        # Subtle alpha blending for zones
        return cv2.addWeighted(overlay, 0.85, frame, 0.15, 0)

    def draw_tracks(self, frame: np.ndarray, tracks: List[TrackState]) -> np.ndarray:
        for t in tracks:
            if t.tracking_status not in ["ACTIVE", "RECOVERED"]:
                continue

            x1, y1, x2, y2 = [int(v) for v in t.bbox]
            color = get_behavior_color(t.stable_behavior)

            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Format label: #<track_id> | <BEHAVIOR> | <ZONE>
            lbl = f"#{t.track_id} | {t.stable_behavior.upper()} | {t.current_zone}"
            if t.behavior_confidence > 0.0:
                lbl += f" ({int(t.behavior_confidence * 100)}%)"

            (lw, lh), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(frame, (x1, max(0, y1 - lh - 8)), (x1 + lw + 6, max(lh + 8, y1)), color, -1)
            cv2.putText(frame, lbl, (x1 + 3, max(lh + 2, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

            # Draw center point
            cx, cy = int(t.center_x), int(t.center_y)
            cv2.circle(frame, (cx, cy), 3, (0, 0, 255), -1)

        return frame

    def draw_global_overlay(
        self,
        frame: np.ndarray,
        tracks: List[TrackState],
        inference_fps: float,
        api_latency: float,
        api_success: bool = True
    ) -> np.ndarray:
        """
        Renders HUD dashboard in top-left corner.
        """
        h, w = frame.shape[:2]
        panel_w = 280
        panel_h = 190
        sub_img = frame[10:10+panel_h, 10:10+panel_w]
        black_rect = np.zeros(sub_img.shape, dtype=np.uint8)
        frame[10:10+panel_h, 10:10+panel_w] = cv2.addWeighted(sub_img, 0.25, black_rect, 0.75, 0)

        # Header
        cv2.putText(frame, "FlockSense Vision Monitor", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2, cv2.LINE_AA)
        
        # Active tracks
        active_cnt = sum(1 for t in tracks if t.tracking_status in ["ACTIVE", "RECOVERED"])
        cv2.putText(frame, f"Active Tracks: {active_cnt}", (20, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        # Behavior distribution
        beh_counts: Dict[str, int] = {}
        for t in tracks:
            if t.tracking_status in ["ACTIVE", "RECOVERED"]:
                beh = t.stable_behavior.capitalize()
                beh_counts[beh] = beh_counts.get(beh, 0) + 1

        beh_str = " | ".join([f"{k}: {v}" for k, v in sorted(beh_counts.items())[:3]]) or "Detecting..."
        cv2.putText(frame, f"Behaviors: {beh_str}", (20, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (200, 255, 200), 1, cv2.LINE_AA)

        # Zone counts
        zone_counts: Dict[str, int] = {}
        for t in tracks:
            if t.tracking_status in ["ACTIVE", "RECOVERED"]:
                z = t.current_zone
                zone_counts[z] = zone_counts.get(z, 0) + 1

        z_str = " | ".join([f"{k}: {v}" for k, v in sorted(zone_counts.items())[:4]]) or "No birds in zones"
        cv2.putText(frame, f"Zones: {z_str}", (20, 96), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (200, 220, 255), 1, cv2.LINE_AA)

        # Inference stats
        status_color = (0, 255, 0) if api_success else (0, 0, 255)
        status_text = "Roboflow API: ONLINE" if api_success else "Roboflow API: OFFLINE/FAIL"
        cv2.putText(frame, status_text, (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.42, status_color, 1, cv2.LINE_AA)
        cv2.putText(frame, f"Model Latency: {int(api_latency*1000)} ms", (20, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (220, 220, 220), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Video Processing: {inference_fps:.1f} FPS", (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (220, 220, 220), 1, cv2.LINE_AA)

        # Notice
        cv2.putText(frame, "Screening only - No disease diagnosis", (20, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (160, 160, 160), 1, cv2.LINE_AA)

        return frame
