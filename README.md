# FlockSense React + Tailwind Command Center Dashboard

Modern, real-time web command center for the **FlockSense** early-warning poultry health and behavioral monitoring platform.

This dashboard communicates directly with the **FlockSense FastAPI backend** (`http://127.0.0.1:8000`), visualizing:
- Overall flock early-warning alert state (`NORMAL`, `WATCH`, `ALERT`),
- Global flock bioacoustic deviation meter & direct audio file screening upload,
- 6-Zone virtual shed grid with real-time chicken tracking markers,
- Multimodal Inspection Priority rankings (0–100) indicating which birds farm managers should visually inspect first,
- Detailed individual chicken inspection inspector with zone migration tracking,
- Actionable early-warning alerts feed with farmer recommendations,
- Prototype validation boundaries and technical architecture metadata.

---

## 🛠️ Technology Stack
- **Framework**: React 19 + Vite + TypeScript
- **Styling**: Tailwind CSS v4 (`@tailwindcss/vite`)
- **Icons**: `lucide-react`
- **State & Communication**: Lightweight polling with auto-reconnect and error fallback

---

## 🚀 Running the Frontend

### 1. Ensure the FastAPI Backend is Running
In your main FlockSense workspace terminal:
```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Configure Environment Variables
Verify `frontend/.env`:
```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

### 3. Start the Frontend Development Server
In a separate terminal inside `frontend/`:
```bash
npm run dev
```

Open your browser at:
`http://localhost:5173`

---

## 🖥️ Dashboard Views

1. **Command Center (`dashboard`)**:
   - Executive flock health overview, global acoustic meter, 6-zone virtual shed map, ranked inspection priority list, audio screening uploader, and active alerts.
2. **Track Monitor (`tracks`)**:
   - Searchable, sortable table of all currently tracked birds with locomotor metrics, zone positions, and camera deviation scores. Click any bird to open the deep inspector.
3. **Bioacoustic Analyzer (`audio`)**:
   - Dedicated acoustic screening center for uploading `.wav` or `.mp3` poultry shed recordings to detect respiratory coughs, rales, or acoustic deviations via the trained ResNet18 model.
4. **Alert Log (`alerts`)**:
   - Actionable timeline of early-warning alerts with specific recommendations (e.g. check shed ventilation, inspect bird posture, consult veterinarian).
5. **System & Validation (`system`)**:
   - Transparent technical specification and validation boundaries (synthetic vision prototype, global acoustic scope, provisional weights).

---

## 🧪 Demo Mode                            
Click the **`DEMO MODE: ON/OFF`** toggle in the top-right header to toggle synthetic development test tracks (Track #17 in Zone 2, Track #24 in Zone 3, Track #12 in Zone 1) to showcase the interactive inspection workflow during presentations.
 # FlockSense FastAPI Backend

Production-ready REST API backend for the **FlockSense** early-warning poultry health and behavioral monitoring platform.

This backend connects:
- The trained **Audio Bioacoustics Model** (`models/audio_model_best.pth`, ResNet18 Log-Mel Spectrogram),
- The **Vision Anomaly Model** (`models/camera_anomaly_model.pkl`, Isolation Forest),
- ByteTrack poultry tracking & virtual zones, and
- The **Multimodal Fusion Engine** (`fusion/state_manager.py`),

exposing clean, typed, high-performance REST APIs for the upcoming React dashboard.

---

## ⚠️ Non-Diagnostic Clinical Disclaimer

> **IMPORTANT**: FlockSense is an automated early-warning behavioral and acoustic screening system. It **does NOT diagnose poultry disease** (e.g., Avian Influenza, Infectious Bronchitis, Newcastle Disease).
> 
> "Inspection Priority" indicates which birds farm managers should visually inspect first. It is **not** a disease probability.
> 
> Acoustic abnormalities reflect shed-wide flock acoustics and are **never** attributed to individual birds because microphone-array sound localization is not present.

---

## System Architecture

```
                                [ Audio Upload (.wav) ]
                                          │
                                          ▼
                            [ Audio Inference Pipeline ]
                         (ResNet18 Log-Mel Spectrogram)
                                          │ (Global Flock Context)
                                          ▼
[ ByteTrack Tracking ] ──► [ Camera Anomaly Model ] ──► [ Multimodal Fusion Engine ]
 (Roboflow Behaviors)        (Isolation Forest)             (Temporal Memory & Decay)
                                                                       │
                                                                       ▼
                                                           [ FusionStateManager ]
                                                                       │
                                                                       ▼
                                                             [ FastAPI Backend ]
                                                                       │
                                              ┌────────────────────────┼────────────────────────┐
                                              ▼                        ▼                        ▼
                                      GET /api/flock-status    GET /api/candidates      GET /api/tracks
```

---

## Quickstart & Running Locally

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Development Server
```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

- API Base URL: `http://127.0.0.1:8000`
- Interactive OpenAPI Swagger Docs: `http://127.0.0.1:8000/docs`
- ReDoc Documentation: `http://127.0.0.1:8000/redoc`

---

## Available Endpoints

### 1. System & Health
- `GET /api/health` — Subsystem health, model readiness, and operational status.
- `GET /api/system-info` — Architectural metadata, models, and validation constraints.

### 2. Flock Status & Inspection Candidates
- `GET /api/flock-status` — Overall early-warning alert level, global acoustic score, and active tracking count.
- `GET /api/candidates?limit=5` — Ranked inspection candidates sorted by descending Inspection Priority Score (0–100).

### 3. Track States & Detail
- `GET /api/tracks` — All active and temporarily lost tracked chickens with current zones and behavioral stats.
- `GET /api/tracks/{track_id}` — In-depth view for a specific bird (movement, behavior, isolation, explainability reasons).

### 4. Early Warning Alerts
- `GET /api/alerts?level=ALERT&limit=20` — Actionable inspection alerts with recommended actions.

### 5. Bioacoustic Analysis
- `POST /api/analyze-audio` — Multipart form upload (`file=<audio>`). Runs the ResNet18 model, updates flock acoustic context, and triggers candidate prioritization.

### 6. Development & Sessions
- `POST /api/dev/track-state` — (Active in `development_mode`) Allows vision trackers to push TrackState observations directly.
- `POST /api/session/start` — Starts a monitoring session.
- `POST /api/session/stop` — Ends a monitoring session.
- `GET /api/session/status` — Retrieves monitoring session duration and status.

---

## Example API Requests & Responses

### Health Check
```bash
curl -X GET http://127.0.0.1:8000/api/health
```
```json
{
  "status": "ok",
  "service": "FlockSense API",
  "components": {
    "audio_model": true,
    "camera_anomaly_model": true,
    "fusion_engine": true,
    "roboflow_configured": true
  },
  "validation": {
    "camera_real_world_validated": false,
    "audio_localization_available": false,
    "medical_validation": false,
    "fusion_weights_status": "PROVISIONAL_DEVELOPMENT_WEIGHTS"
  }
}
```

### Bioacoustic Upload
```bash
curl -X POST "http://127.0.0.1:8000/api/analyze-audio" \
  -F "file=@splits/test/unhealthy_sample.wav"
```
```json
{
  "success": true,
  "filename": "unhealthy_sample.wav",
  "audio": {
    "prediction": "ABNORMAL",
    "status": "ALERT",
    "overall_abnormality_probability_pct": 86.4,
    "score": 86.4,
    "scope": "FLOCK",
    "localized": false,
    "duration_seconds": 1.18,
    "windows_analyzed": 1,
    "high_risk_windows": 1,
    "interpretation": "Significant deviation from normal flock acoustic baseline.",
    "recommended_action": "Immediately inspect the poultry flock and shed ventilation."
  },
  "fusion": {
    "flock_status": "ALERT",
    "global_audio_score": 86.4,
    "top_candidate_ids": [17, 24]
  },
  "disclaimer": "Audio abnormality is flock-level and is not attributed to a specific bird."
}
```

---

## Known Prototype Limitations

1. **Audio Localization Unavailable**: Hardware microphone arrays are not present. Audio remains strictly flock-wide context.
2. **Camera Prototype Baseline**: Isolation Forest model was trained on synthetic video features (`PROTOTYPE_ONLY_SYNTHETIC_DATA`).
3. **Provisional Weights**: Fusion parameters are heuristic development settings pending real farm calibration.
