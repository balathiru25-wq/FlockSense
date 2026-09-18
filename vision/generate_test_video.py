import cv2
import numpy as np
from pathlib import Path

def create_sample_poultry_video(output_path="dataset/video/sample_chickens.mp4", duration_sec=5.0, fps=30):
    """
    Creates a realistic test video based on the poultry shed frame.
    Simulates:
    1. Bird A: Sitting in Zone 3 (top right), stands up, and walks into Zone 2 (top center).
    2. Bird B: Feeding in Zone 5 (bottom center).
    3. Bird C: Standing in Zone 1 (top left).
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    base_img_path = Path("dataset/video/sample_flock.jpg")
    if base_img_path.exists():
        base_frame = cv2.imread(str(base_img_path))
        base_frame = cv2.resize(base_frame, (960, 540))
    else:
        base_frame = np.ones((540, 960, 3), dtype=np.uint8) * 180

    h, w = base_frame.shape[:2]
    total_frames = int(duration_sec * fps)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_file), fourcc, float(fps), (w, h))

    for f_idx in range(total_frames):
        t_norm = f_idx / float(total_frames)
        frame = base_frame.copy()

        # Slight camera movement / subtle noise
        noise = np.random.normal(0, 1.5, frame.shape).astype(np.int16)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # Draw moving Bird A (White broiler chicken circle with head marker)
        # Trajectory: Zone 3 (x=720, y=140) -> Zone 2 (x=460, y=140)
        b1_x = int(720 - 260 * t_norm)
        b1_y = int(140 + 5 * np.sin(t_norm * np.pi * 4))
        cv2.ellipse(frame, (b1_x, b1_y), (35, 25), 0, 0, 360, (245, 245, 245), -1)
        cv2.circle(frame, (b1_x - 18, b1_y - 8), 12, (230, 230, 230), -1)
        cv2.circle(frame, (b1_x - 22, b1_y - 12), 4, (0, 0, 255), -1) # comb

        # Bird B (Feeding in Zone 5: x=480, y=380)
        b2_x = 480
        b2_y = int(380 + 3 * np.cos(t_norm * np.pi * 6))
        cv2.ellipse(frame, (b2_x, b2_y), (38, 28), 0, 0, 360, (250, 250, 250), -1)
        cv2.circle(frame, (b2_x + 20, b2_y + 10), 12, (235, 235, 235), -1)

        # Bird C (Zone 1: x=190, y=150)
        b3_x = int(190 + 6 * np.sin(t_norm * np.pi * 2))
        b3_y = 150
        cv2.ellipse(frame, (b3_x, b3_y), (32, 24), 0, 0, 360, (240, 240, 240), -1)

        writer.write(frame)

    writer.release()
    print(f"Sample test video generated: {out_file} ({total_frames} frames, {w}x{h}, {fps} FPS)")

if __name__ == "__main__":
    create_sample_poultry_video()
