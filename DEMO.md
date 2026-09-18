# FlockSense — Hackathon Demo Guide & Judge Walkthrough

## Before Presentation (Preflight Checklist)

1. **Connect Laptop Charger & Display Output**
   - Ensure the laptop is plugged into AC power to prevent CPU throttling.
   - Set external display / projector to recommended resolution: **1920×1080** or **1366×768** (both tested & responsive).
2. **Confirm Internet Status**
   - If internet is active: Roboflow API can be used for live behavior detection if desired.
   - If internet is unavailable/unstable: **Do not worry**. FlockSense includes an automated offline fallback mode where camera behavior runs from local cached states while audio model inference (PyTorch ResNet18) and multimodal fusion execute 100% locally on-device.
3. **Run Preflight Verification Script**
   `powershell
   python scripts/preflight_check.py
   `
   Confirm that all models, configs, backend, and frontend report [READY] and DEMO READY: YES.
4. **Start Backend and Frontend Services**
   - Option A (One-Click Batch): Double-click start_flocksense_demo.bat.
   - Option B (PowerShell): Run powershell -ExecutionPolicy Bypass -File scripts/start_demo.ps1.
   - Option C (Manual):
     - Terminal 1: python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
     - Terminal 2: cd frontend; npm run dev
5. **Open Dashboard**
   - Open Chrome / Edge to: [http://localhost:5173](http://localhost:5173).
   - Verify the top banner displays: DEMO / SYNTHETIC SCENARIO and the Demo Controller panel is visible on the right.
6. **Reset State**
   - Click **RESET DEMO** in the Demo Controller to initialize a clean slate.

---

## Live Demo Flow (Step-by-Step Clicks)

You can run the entire presentation interactively using the **Demo Controller** buttons or automated via **RUN FULL DEMO**.

### Option A: Interactive Step-by-Step Flow

1. **Click RESET DEMO**:
   - Clears any previous session state, sets flock status to NORMAL, and clears active candidates.
2. **Click Step 1 — Normal Flock**:
   - Ingests healthy birds (Track #12 in Zone 1, Track #17 in Zone 3, Track #24 in Zone 4).
   - Global audio status: NORMAL (0.5% abnormality).
   - Point out to judges: All tracks show low camera deviation (<25%), low inspection priority, green status cards.
3. **Click Step 2 — Deviation**:
   - Simulates gradual behavioral degradation of Track #17 (standing → sitting → prolonged stationary state, isolation increasing).
   - Camera deviation gradually climbs (22% → 38% → 56% → 72% → 82%).
   - Point out to judges: Track #17 transitions to WATCH_DEVIATION / HIGH_DEVIATION. Notice the system does NOT claim disease diagnosis.
4. **Click Step 3 — Zone Move**:
   - Track #17 physically migrates from ZONE 3 to ZONE 2.
   - Point out to judges: **Track ID #17 is retained**. The virtual zone marker moves across the shed map. Its prior behavior and anomaly history follow the bird to Zone 2; nothing remains ghosted in Zone 3.
5. **Click Step 4 — Normal Audio**:
   - Analyzes real held-out audio (
ormal_sample.wav) through the local PyTorch ResNet18 model (models/audio_model_best.pth).
   - Acoustic score returns ~0.50% (NORMAL). Flock acoustic status stays un-triggered.
6. **Click Step 5 — Abnormal Audio**:
   - Analyzes real held-out poultry distress/cough audio (bnormal_sample.wav) through the PyTorch ResNet18 model.
   - Acoustic abnormality score returns ~99.46% (ALERT).
   - Point out to judges: The prominent banner **AUDIO SOURCE NOT LOCALIZED TO THIS BIRD**. Audio informs us of shed-wide respiratory distress, not individual bird identity.
7. **Click Step 6 — Fusion Alert**:
   - Multimodal fusion engine combines global acoustic alert with individual track deviations.
   - Candidate ranking updates deterministically:
     - **#1 Priority:** Track #17 (Zone 2, Priority ~78.3%, ALERT).
     - **#2 Priority:** Track #24 (Zone 4, Priority ~57.7%, WATCH).
     - **#3 Priority:** Track #12 (Zone 1, Priority ~28.0%, NORMAL).
   - Point out to judges: Actionable farmer recommendation appears:
     *Physical visual inspection recommended for Track #17 in ZONE 2. If concerning physical signs persist, consult a veterinarian.*

### Option B: Automated Full Demo
- Click **RUN FULL DEMO**.
- The system automatically triggers the 6 steps sequentially with smooth transitions (~10s per stage), allowing you to talk through the slides and dashboard without touching the mouse.

---

## 2–3 Minute Judge Talk Track

- **[0:00–0:20] Problem**:
  > *Modern commercial poultry houses hold tens of thousands of broilers. Diseases like Newcastle disease or Infectious Bronchitis spread exponentially through flock vocalizations and lethargy before mortality occurs. Farmers cannot manually inspect 30,000 birds one-by-one.*

- **[0:20–0:40] Normal Monitoring**:
  > *FlockSense is a non-invasive multimodal early-warning screening system. On screen right now in Step 1, camera streams track birds across virtual shed zones while an acoustic monitor listens to shed-level vocalizations. Notice all birds have low deviation and flock status is NORMAL.*

- **[0:40–1:00] Individual Tracking & Virtual Zones**:
  > *In Step 2 and 3, our computer vision pipeline tracks individual birds using ByteTrack and extracts spatiotemporal movement features. Watch Track #17: as its activity slows down and isolation increases, its camera behavioral deviation rises. When it migrates from Zone 3 to Zone 2, its unique Track ID and behavioral risk score migrate with it.*

- **[1:00–1:40] Real Acoustic Inference**:
  > *Now listen to the flock. When normal audio is analyzed in Step 4, our custom 1-channel Log-Mel ResNet18 model reports normal baseline activity. In Step 5, we analyze a real held-out abnormal distress audio sample. The neural network computes an acoustic abnormality score of over 99%.*

- **[1:40–2:10] Multimodal Fusion & Honest Boundaries**:
  > *Here is our key engineering honesty: sound propagates through the whole barn. Audio tells us THAT something is wrong in the shed, but microphone-level localization cannot pinpoint which chicken made the sound. That is where our Multimodal Fusion Engine comes in.*

- **[2:10–2:30] Candidate Inspection Ranking**:
  > *The fusion engine combines the global acoustic distress context with individual behavioral deviations. It ranks candidate birds for farmer inspection. Track #17 is surfaced as the #1 inspection priority, located currently in Zone 2. The dashboard advises: 'Inspect Track #17 in Zone 2. If concerning physical signs persist, consult a veterinarian.'*

- **[2:30–3:00] Wrap-up & Technical Disclosures**:
  > *FlockSense never claims medical diagnosis—it is an early-warning screening and triage tool. Our audio model is fully trained and running locally on PyTorch, our fusion engine is deterministic, and our camera anomaly prototype demonstrates how spatial tracking directs farmer labor directly to the birds needing attention.*

---

## Fallback Demo Flow

| Scenario | Impact | Fallback Procedure |
| :--- | :--- | :--- |
| **Internet / WiFi Fails** | Roboflow API cloud calls cannot reach cloud endpoint. | **No action needed.** The Judge Demo Mode automatically uses offline synthetic/cached track states. The ResNet18 audio inference and FusionStateManager run 100% locally. |
| **Frontend Disconnects / Port Conflict** | Browser displays connection refused. | Run stop_flocksense_demo.bat to clear port listeners, then run start_flocksense_demo.bat. Refresh browser at http://localhost:5173. |
| **Audio Model Fails to Load** | Torch CUDA / device error. | Backend automatically maps model weights to cpu (	orch.load(..., map_location='cpu')), ensuring zero dependence on external GPUs or proprietary drivers. |
| **Need Quick Full Reset** | Unintended state left on screen. | Click the red **RESET DEMO** button in the Demo Controller header. |
