import os
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any, Union, List
import cv2
import numpy as np

# Ensure inference_sdk can be imported
try:
    from inference_sdk import InferenceHTTPClient, InferenceConfiguration
except ImportError:
    InferenceHTTPClient = None
    InferenceConfiguration = None

class RoboflowBehaviorDetector:
    """
    Client for running inference using Roboflow's 'chicken-behavior-detection-within-real-time/17'
    object detection model via Serverless Cloud API.
    
    Includes API error handling, bandwidth-reduction resizing/JPEG compression,
    and structured output conversion.
    """
    MODEL_ID = "chicken-behavior-detection-within-real-time/17"
    API_URL = "https://serverless.roboflow.com"

    def __init__(self, api_key: Optional[str] = None, max_width: int = 960, jpeg_quality: int = 75, confidence_threshold: float = 0.25):
        self.api_key = api_key or os.environ.get("ROBOFLOW_API_KEY")
        self.max_width = max_width
        self.jpeg_quality = jpeg_quality
        self.confidence_threshold = confidence_threshold
        
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_latency_seconds = 0.0

        if InferenceHTTPClient is not None and self.api_key:
            # Initialize HTTP client with Header-based authentication transport (v1.5.0+)
            self.client = InferenceHTTPClient(
                api_url=self.API_URL,
                api_key=self.api_key
            ).configure(InferenceConfiguration(
                api_key_transport="header"
            ))
        else:
            self.client = None

    def is_configured(self) -> bool:
        return self.client is not None and bool(self.api_key)

    def prepare_frame_for_inference(self, frame: np.ndarray) -> np.ndarray:
        """
        Resize and compress frame to reduce bandwidth while preserving behavior recognition detail.
        """
        h, w = frame.shape[:2]
        if w > self.max_width:
            scale = self.max_width / float(w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            resized = frame.copy()

        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
        _, encimg = cv2.imencode(".jpg", resized, encode_param)
        decompressed = cv2.imdecode(encimg, 1)
        return decompressed

    def infer_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Runs behavior detection on a BGR numpy frame.
        Handles API errors gracefully without crashing.
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "ROBOFLOW_API_KEY not configured",
                "predictions": [],
                "latency_seconds": 0.0
            }

        self.total_requests += 1
        t0 = time.time()

        try:
            proc_frame = self.prepare_frame_for_inference(frame)
            result = self.client.infer(proc_frame, model_id=self.MODEL_ID)
            latency = time.time() - t0
            self.total_latency_seconds += latency
            self.successful_requests += 1

            orig_h, orig_w = frame.shape[:2]
            proc_h, proc_w = proc_frame.shape[:2]
            scale_x = orig_w / float(proc_w)
            scale_y = orig_h / float(proc_h)

            raw_preds = result.get("predictions", [])
            parsed_preds = []

            for p in raw_preds:
                conf = float(p.get("confidence", 0.0))
                if conf < self.confidence_threshold:
                    continue

                cx = float(p.get("x", 0.0)) * scale_x
                cy = float(p.get("y", 0.0)) * scale_y
                bw = float(p.get("width", 0.0)) * scale_x
                bh = float(p.get("height", 0.0)) * scale_y

                x1 = max(0, cx - bw / 2.0)
                y1 = max(0, cy - bh / 2.0)
                x2 = min(orig_w, cx + bw / 2.0)
                y2 = min(orig_h, cy + bh / 2.0)

                behavior = str(p.get("class", "unknown")).lower()

                parsed_preds.append({
                    "bbox": [x1, y1, x2, y2],
                    "center": (cx, cy),
                    "behavior": behavior,
                    "confidence": conf
                })

            return {
                "success": True,
                "error": None,
                "predictions": parsed_preds,
                "latency_seconds": latency
            }

        except Exception as e:
            latency = time.time() - t0
            self.total_latency_seconds += latency
            self.failed_requests += 1
            return {
                "success": False,
                "error": str(e),
                "predictions": [],
                "latency_seconds": latency
            }

    def get_statistics(self) -> Dict[str, Any]:
        avg_latency = (
            (self.total_latency_seconds / self.total_requests)
            if self.total_requests > 0
            else 0.0
        )
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "average_latency_seconds": round(avg_latency, 3)
        }
