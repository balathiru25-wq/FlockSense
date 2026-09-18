"""
Main FastAPI application entry point for FlockSense.
Exposes REST APIs for the poultry monitoring dashboard.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.flock_service import flock_service
from backend.routes.health import router as health_router
from backend.routes.flock import router as flock_router
from backend.routes.tracks import router as tracks_router
from backend.routes.alerts import router as alerts_router
from backend.routes.audio import router as audio_router
from backend.routes.dev import router as dev_router
from backend.routes.devices import router as devices_router
from backend.routes.setup import router as setup_router, zones_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("flocksense.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager:
    Initializes and loads heavy AI models and Fusion engine ONCE on startup.
    Cleans up resources gracefully on shutdown.
    """
    logger.info("FlockSense backend starting up...")
    flock_service.initialize()
    yield
    logger.info("FlockSense backend shutting down.")

app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler for clean structured errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled Exception at %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while processing the request."
            }
        }
    )

# Register API Routers under /api prefix
app.include_router(health_router, prefix="/api")
app.include_router(flock_router, prefix="/api")
app.include_router(tracks_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(audio_router, prefix="/api")
app.include_router(dev_router, prefix="/api")
app.include_router(devices_router, prefix="/api")
app.include_router(setup_router, prefix="/api")
app.include_router(zones_router, prefix="/api")

@app.get("/", summary="Root Health Ping")
def read_root():
    return {
        "service": settings.app_title,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/health",
        "disclaimer": "FlockSense is an early-warning screening system and does not diagnose poultry disease."
    }
