"""
Candidate Ranker and Inspection Prioritizer for FlockSense.
Ranks currently tracked chickens by Inspection Priority Score (0–100)
to support focused farmer physical inspections.
"""

from typing import List, Dict, Any, Optional
from fusion.models import InspectionCandidate, CameraTrackState

class CandidateRanker:
    """
    Ranks tracked chickens for targeted physical inspection.
    Integrates behavioral deviation, persistence, spatial isolation, activity level,
    and flock acoustic context.
    
    IMPORTANT: Inspection Priority is NOT disease probability.
    It indicates: 'Which currently tracked birds should the farmer inspect first?'
    """
    def __init__(self, top_n: int = 5, include_temporarily_lost: bool = True):
        self.top_n = int(top_n)
        self.include_temporarily_lost = bool(include_temporarily_lost)

    def rank_candidates(self, candidates: List[InspectionCandidate]) -> List[InspectionCandidate]:
        """
        Sorts candidates in descending order of inspection priority score.
        Applies rank indices (1, 2, 3...) and returns top N candidates.
        """
        # Filter out ended tracks or lost tracks if configured
        valid = []
        for c in candidates:
            if c.tracking_status == "TRACK_ENDED":
                continue
            if not self.include_temporarily_lost and c.tracking_status == "TEMPORARILY_LOST":
                continue
            valid.append(c)

        # Primary sort: inspection_priority descending; secondary: camera_deviation_score descending
        sorted_candidates = sorted(
            valid,
            key=lambda c: (c.inspection_priority, c.camera_deviation_score, c.persistence_score),
            reverse=True
        )

        # Assign ranks
        ranked = []
        for idx, cand in enumerate(sorted_candidates[:self.top_n]):
            cand.rank = idx + 1
            ranked.append(cand)

        return ranked

    def build_candidate_summary_table(self, ranked: List[InspectionCandidate]) -> str:
        """Helper to format ranked candidates into a terminal or log summary table."""
        header = f"{'Rank':<5} | {'Track ID':<9} | {'Current Zone':<13} | {'Evidence Zone':<14} | {'Priority':<9} | {'Status':<8} | {'Audio Boost':<11} | {'Primary Reason'}"
        sep = "-" * len(header)
        lines = [header, sep]
        for c in ranked:
            reason = c.reasons[0] if c.reasons else "Normal baseline"
            lines.append(
                f"{c.rank:<5} | #{c.track_id:<8} | {c.current_zone:<13} | {c.initial_evidence_zone:<14} | {c.inspection_priority:<9.1f} | {c.status:<8} | {c.audio_urgency_boost:<11.1f} | {reason}"
            )
        return "\n".join(lines)
