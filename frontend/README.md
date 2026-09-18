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
