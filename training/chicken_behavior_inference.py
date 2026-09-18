import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, Union

# Ensure inference_sdk can be imported
try:
    from inference_sdk import InferenceHTTPClient, InferenceConfiguration
except ImportError:
    InferenceHTTPClient = None
    InferenceConfiguration = None

class RoboflowChickenBehaviorDetector:
    """
    Client for running inference using Roboflow's 'chicken-behavior-detection-within-real-time/17'
    object detection model via Serverless Cloud API.
    
    Authentication is sent via HTTP Header ('Authorization: Bearer <API_KEY>'),
    avoiding passing API keys in query parameters.
    """
    MODEL_ID = "chicken-behavior-detection-within-real-time/17"
    API_URL = "https://serverless.roboflow.com"

    def __init__(self, api_key: Optional[str] = None):
        if InferenceHTTPClient is None:
            raise ImportError(
                "inference-sdk is not installed. Please install it using: pip install inference-sdk"
            )
        
        # Load API key from parameter or environment variable
        self.api_key = api_key or os.environ.get("ROBOFLOW_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Roboflow API key is missing! Please provide it via the --api_key parameter "
                "or set the ROBOFLOW_API_KEY environment variable.\n"
                "You can get your API key from https://app.roboflow.com/settings/api"
            )

        # Initialize HTTP client with Header-based authentication transport (v1.5.0+)
        self.client = InferenceHTTPClient(
            api_url=self.API_URL,
            api_key=self.api_key
        ).configure(InferenceConfiguration(
            api_key_transport="header"
        ))

    def detect(self, image_path_or_url: Union[str, Path]) -> Dict[str, Any]:
        """
        Runs object detection and behavior recognition on the given image.
        
        Args:
            image_path_or_url: Local file path or image URL
            
        Returns:
            Dict containing raw prediction results and structured behavior summary.
        """
        image_input = str(image_path_or_url)
        
        # Call Roboflow Serverless Cloud API
        result = self.client.infer(image_input, model_id=self.MODEL_ID)
        
        # Process and summarize behaviors detected in the scene
        summary = self._summarize_predictions(result)
        return {
            "model_id": self.MODEL_ID,
            "image": image_input,
            "summary": summary,
            "raw_result": result
        }

    def _summarize_predictions(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts behavior counts, bounding box counts, and flock activity metrics.
        """
        predictions = result.get("predictions", [])
        behavior_counts = {}
        total_detections = len(predictions)

        for pred in predictions:
            cls = pred.get("class", "unknown")
            behavior_counts[cls] = behavior_counts.get(cls, 0) + 1

        return {
            "total_chickens_detected": total_detections,
            "behavior_distribution": behavior_counts,
            "image_dimensions": {
                "width": result.get("image", {}).get("width"),
                "height": result.get("image", {}).get("height")
            }
        }

    def print_summary(self, detection_output: Dict[str, Any]):
        """
        Formats and prints a clean terminal summary of detected flock behaviors.
        """
        summary = detection_output["summary"]
        raw = detection_output["raw_result"]
        img = detection_output["image"]
        total = summary["total_chickens_detected"]
        dist = summary["behavior_distribution"]

        print("\n" + "=" * 65)
        print(" FLOCKSENSE — ROBOFLOW CHICKEN BEHAVIOR DETECTION (VIDEO AI) ")
        print("=" * 65)
        print(f"Model ID:              {detection_output['model_id']}")
        print(f"Target Image:          {img}")
        print(f"Total Chickens Found:  {total}")
        print("-" * 65)
        print(f"{'Detected Behavior / Class':<35} | {'Count':<10} | {'Percentage':<10}")
        print("-" * 65)
        if not dist:
            print("  No chicken behaviors detected in this frame.")
        else:
            for cls, cnt in sorted(dist.items(), key=lambda x: x[1], reverse=True):
                pct = (cnt / total * 100) if total > 0 else 0
                print(f"{cls:<35} | {cnt:<10} | {pct:<9.1f}%")
        print("-" * 65)
        if "time" in raw:
            print(f"Inference Latency:     {raw['time'] * 1000:.1f} ms" if isinstance(raw['time'], (int, float)) else f"Inference Info: {raw['time']}")
        print("=" * 65 + "\n")


def main():
    parser = argparse.ArgumentParser(description="FlockSense — Roboflow Chicken Behavior Detection")
    parser.add_argument(
        "--image", 
        type=str, 
        default="dataset/video/sample_flock.jpg",
        help="Path to the image or image URL to analyze"
    )
    parser.add_argument(
        "--api_key", 
        type=str, 
        default=None, 
        help="Roboflow API key (or set ROBOFLOW_API_KEY environment variable)"
    )
    parser.add_argument(
        "--json", 
        action="store_true", 
        help="Output raw JSON response"
    )

    args = parser.parse_args()

    # Verify input exists if local file
    img_path = Path(args.image)
    if not args.image.startswith("http://") and not args.image.startswith("https://") and not img_path.exists():
        print(f"Error: Specified image file does not exist: {args.image}")
        sys.exit(1)

    try:
        detector = RoboflowChickenBehaviorDetector(api_key=args.api_key)
        results = detector.detect(args.image)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            detector.print_summary(results)
    except Exception as e:
        print(f"\n[Roboflow Inference Error]: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
