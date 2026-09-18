# FlockSense — Expected Judge Questions & Technical Answers

### 1. How do you know which chicken made the sound?
**Answer:**
> We currently do **not** know which individual chicken made the sound. In commercial poultry environments, acoustic reverberation and ambient noise make single-microphone localization impossible. Audio is strictly treated as **flock-level contextual evidence** (shed-wide acoustic abnormality). Our camera tracking provides individual behavioral context. The fusion engine correlates the two: when flock-level acoustic distress is detected, the farmer's attention is directed toward birds exhibiting the strongest individual behavioral deviation. Future deployment of microphone array time-difference-of-arrival (TDOA) sensors will enable spatial acoustic localization.

---

### 2. What happens when the chicken changes zones?
**Answer:**
> Our tracking architecture associates identity and feature histories with the **temporary Track ID**, not with the physical zone. As demonstrated in Demo Step 3 with Track #17 moving from Zone 3 to Zone 2, the bird marker smoothly updates on the shed map, its cumulative behavioral history is preserved, and its inspection priority follows the bird. The previous zone simply records a zone-departure event.

---

### 3. Are you diagnosing disease?
**Answer:**
> **No.** FlockSense is an early-warning screening, anomaly-detection, and inspection-prioritization system, not a veterinary medical diagnostic device. It flags statistically significant behavioral and acoustic deviations from baseline flock norms. All alert notifications clearly state: *Physical inspection recommended. If concerning physical signs persist, consult a veterinarian.*

---

### 4. Why use camera + audio? Why not just one or the other?
**Answer:**
> Neither modality is sufficient in isolation:
> - **Audio alone** can detect respiratory distress, rales, or distress calls early across the entire shed, but a single audio stream cannot tell a farmer which specific chicken or pen area to inspect among 20,000 birds.
> - **Camera alone** can track individual lethargy, reduced feeding, or huddling, but mild early respiratory infections often show acoustic symptoms before severe physical immobility develops.
> Combining both provides sensitivity across both modalities while preserving spatial actionability.

---

### 5. What if chickens look identical? How does tracking work?
**Answer:**
> FlockSense uses **temporary session-level tracking via ByteTrack**, not permanent lifelong biometric re-identification. Because broiler chickens are visually homogeneous, ByteTrack relies on bounding box motion dynamics, high-frame-rate Kalman filtering, and spatial association across consecutive frames. For operational early warning, tracking a bird across several minutes to verify sustained lethargy and identify its current zone is sufficient to alert the farmer.

---

### 6. What happens after occlusion (e.g. bird goes under a feeder)?
**Answer:**
> ByteTrack maintains a track buffer (e.g. 30 frames). If a bird is briefly occluded behind a feeder or another bird and reappears within that window, its track ID is recovered. If the occlusion lasts beyond the buffer threshold, the previous track expires and a new track ID is initialized upon reappearance. The system gracefully resets without crashing.

---

### 7. Why use an Isolation Forest for camera anomaly detection instead of a deep supervised classifier?
**Answer:**
> In poultry farming, obtaining thousands of hours of medically confirmed, per-bird ground-truth labeled sick videos is clinically impractical and prone to dataset bias. An **unsupervised Isolation Forest** learns the multi-dimensional distribution of healthy flock behavior (velocity, stationary duration, zone transition frequency, and nearest-neighbor isolation distance). It detects outliers that deviate from the flock baseline without requiring pre-labeled disease categories.

---

### 8. Is the camera anomaly validation real or synthetic?
**Answer:**
> We disclose this with full technical transparency: in this prototype phase, the camera anomaly baseline was trained on calibrated synthetic behavioral feature distributions because public open-access video datasets of individual tracked broilers with verified ground-truth disease timelines do not exist. In contrast, our **audio model is trained and validated on genuine held-out poultry audio recordings**. Real-world in-barn camera validation is our primary post-hackathon milestone.

---

### 9. Why not use only audio?
**Answer:**
> If an alarm triggers saying *86% acoustic coughing detected in Shed B*, a farmhand entering a 100-meter poultry shed with 30,000 birds still has no idea where to start looking. Without camera tracking, farmers cannot triage or physically inspect the affected birds before disease transmission widens.

---

### 10. Why not use only camera?
**Answer:**
> Chickens naturally rest, sit, and sleep during normal circadian cycles. An isolated camera system could trigger excessive false alarms on a sleeping or resting bird. However, if a resting bird coincides with elevated flock-wide acoustic distress, the posterior probability of illness is substantially higher. Multimodal fusion filters false positives and increases diagnostic confidence.
