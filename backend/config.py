"""
Backend configuration settings for FlockSense API.
Loads environment variables and application defaults.
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseModel):
    # API metadata
    app_title: str = "FlockSense API"
    app_description: str = (
        "Early-warning poultry monitoring backend combining acoustic abnormality, "
        "tracked behaviour and behavioural deviation. "
        "Disclaimer: FlockSense is an early-warning screening system and does not diagnose poultry disease."
    )
    app_version: str = "1.0.0"
    
    # Environment & mode
    development_mode: bool = Field(default_factory=lambda: os.getenv("FLOCKSENSE_DEV_MODE", "true").lower() == "true")
    
    # CORS
    allowed_origins: list[str] = Field(default_factory=lambda: [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ])
    
    # Model checkpoints and paths
    audio_checkpoint_path: Path = ROOT_DIR / "models" / "audio_model_best.pth"
    camera_anomaly_model_path: Path = ROOT_DIR / "models" / "camera_anomaly_model.pkl"
    fusion_config_path: Path = ROOT_DIR / "config" / "fusion_config.yaml"
    zones_config_path: Path = ROOT_DIR / "config" / "zones.json"
    
    # Max file upload size (e.g. 25 MB for audio files)
    max_audio_upload_bytes: int = 25 * 1024 * 1024
    allowed_audio_extensions: list[str] = [".wav", ".mp3", ".flac", ".ogg", ".m4a"]

settings = Settings()
