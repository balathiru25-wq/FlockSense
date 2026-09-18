"""
FlockSense Backend Package.
"""

from backend.main import app
from backend.flock_service import flock_service

__all__ = ["app", "flock_service"]
