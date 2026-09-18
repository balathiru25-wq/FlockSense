# FlockSense — Real Tracking Validation Report

**Project**: FlockSense — AI-Powered Poultry Farm Early-Warning System  
**Pipeline**: Video Behavior Detection & Multi-Object Tracking  
**Status**: **UNVALIDATED ON REAL POULTRY FOOTAGE** (Pending Real Video Acquisition)  
**Date**: September 2026  

---

## 1. Real Video Search Results

A recursive scan of the entire FlockSense workspace was conducted across all video and data directories:
* `dataset/video/`
* `dataset/`
* `data/`
* `videos/`
* `samples/`

### Video Artifacts Discovered:
1. `dataset/video/sample_chickens.mp4` (Size: 2.51 MB) — **GENERATED / SYNTHETIC**. Created via programmatic script (`vision/generate_test_video.py`) using animated elliptical shapes over a static backdrop image.
2. `outputs/vision/videos/flocksense_behavior_tracking.mp4` (Size: 3.23 MB) — **PROCESSED OUTPUT** generated from the synthetic sequence above.

### Conclusion:
**No real poultry video footage exists in the repository.**

In accordance with strict scientific guardrails:
> **"Real poultry footage is required for tracking validation."**  
> Synthetic test results (e.g., 100% ID stability on 3 simulated chickens) must **never** be reported as real-world performance. Real-world validation is therefore halted and marked **UNVALIDATED** until real flock footage is provided.

---

## 2. Real-World Tracking Challenges (Pre-Identified Test Criteria)

When real multi-chicken footage is supplied, the tracking pipeline will be evaluated against the following difficult edge cases:

1. **Path Crossover & ID Switching**: When two chickens walk in intersecting paths, IoU association in ByteTrack can swap IDs if detection bounding boxes merge.
2. **Dense Occlusion & Clustering**: Chickens huddling around feeders or resting together create severe bounding-box overlap. ByteTrack's 30-frame buffer must be benchmarked on how well it recovers IDs after occlusion breaks.
3. **Flock Boundary Transitions**: Chickens entering and leaving camera field-of-view must trigger honest track termination (`TRACK_ENDED`) without leaking historical IDs to newly arriving birds.
4. **Behavior Transition Stability**: Verifying that posture changes (*standing* $\rightarrow$ *sitting* $\rightarrow$ *feeding*) do not trigger false new track generation.
5. **Zone Boundary Dithering**: Verifying that birds pecking along virtual zone boundaries do not produce rapid flickering transitions due to the 3-frame debounce filter.

---

## 3. Comparison Summary

| Metric / Scenario | Synthetic Test Sequence | Real Poultry Footage (Expected) |
|---|---|---|
| **Footage Source** | `vision/generate_test_video.py` | Real shed CCTV / IP Camera |
| **Simultaneous Birds** | 3 simulated birds | 20–100+ birds in commercial shed |
| **Observed ID Switching** | 0% (Controlled paths) | Expected non-zero (occlusions/crossovers) |
| **Validation Status** | **SYNTHETIC ONLY** | **PENDING FOOTAGE** |
