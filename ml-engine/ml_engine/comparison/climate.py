"""Climate similarity comparison.

Compares temperature ranges between a planetary target and an Earth
candidate using interval-overlap analysis.

Methodology
-----------
1. Both intervals [T_min, T_max] are compared.
2. Overlapping ranges -> mapped continuously to [35.0, 100.0]:
   score = 35.0 + 65.0 * (overlap / union)
3. Non-overlapping ranges -> exponential decay on the gap mapped to [0.0, 35.0]:
   score = 35.0 * exp(-gap^2 / (2 * sigma^2))
   This ensures a smooth, continuous transition at touchpoint (gap=0, overlap=0 -> 35.0)
   and guarantees that overlapping ranges always rank >= 35.0 while disjoint ranges rank < 35.0.

Temperature-gap decay sigma = 30.0 deg C.
"""
from __future__ import annotations

import math

from ml_engine.models.schemas import (
    DimensionResult,
    DimensionStatus,
    EarthCandidate,
    PlanetaryTarget,
)

TEMP_GAP_SIGMA_C: float = 30.0


def _interval_similarity(
    t_lo: float, t_hi: float,
    c_lo: float, c_hi: float,
    gap_sigma: float = TEMP_GAP_SIGMA_C,
) -> float:
    """Similarity between two temperature intervals, in [0, 100].

    Guarantees:
    - 100.0 for identical intervals
    - Continuous at the boundary: when intervals touch (overlap=0, gap=0), score is 35.0
    - Strictly monotonic: overlap/union > 0 gives score in [35.0, 100.0]
    - Strictly monotonic: gap > 0 gives score in [0.0, 35.0)
    """
    if t_lo > t_hi:
        t_lo, t_hi = t_hi, t_lo
    if c_lo > c_hi:
        c_lo, c_hi = c_hi, c_lo

    overlap_lo = max(t_lo, c_lo)
    overlap_hi = min(t_hi, c_hi)
    overlap = max(0.0, overlap_hi - overlap_lo)

    union_lo = min(t_lo, c_lo)
    union_hi = max(t_hi, c_hi)
    union = union_hi - union_lo

    if union == 0:
        return 100.0 if t_lo == c_lo else 0.0

    if overlap > 0:
        ratio = overlap / union
        score = 35.0 + 65.0 * ratio
        return round(min(100.0, max(0.0, score)), 2)

    gap = overlap_lo - overlap_hi  # positive when no overlap
    if gap_sigma <= 0:
        return 0.0
    decay = math.exp(-(gap ** 2) / (2.0 * gap_sigma ** 2))
    return round(min(35.0, max(0.0, 35.0 * decay)), 2)


def compare_climate(
    target: PlanetaryTarget,
    candidate: EarthCandidate,
) -> DimensionResult:
    """Compare climate features between *target* and *candidate*.

    Currently compares temperature ranges.  Future versions may add
    aridity indices, pressure, and radiation when data is available.
    """
    features_compared: list[str] = []
    features_missing: list[str] = []
    warnings: list[str] = []

    has_target = target.temp_range_c is not None
    has_cand = (
        candidate.temp_min_c is not None and candidate.temp_max_c is not None
    )

    if has_target and has_cand:
        assert target.temp_range_c is not None
        t_lo, t_hi = target.temp_range_c
        c_lo = candidate.temp_min_c
        c_hi = candidate.temp_max_c
        assert c_lo is not None and c_hi is not None

        score = _interval_similarity(t_lo, t_hi, c_lo, c_hi)
        features_compared.append("temperature_range")

        return DimensionResult(
            dimension="climate",
            score=score,
            status=DimensionStatus.COMPUTED,
            features_compared=features_compared,
            features_missing=features_missing,
            methodology=(
                f"Temperature interval overlap. "
                f"Target: [{t_lo} deg C, {t_hi} deg C], "
                f"Candidate: [{c_lo} deg C, {c_hi} deg C]. "
                f"Gap decay sigma={TEMP_GAP_SIGMA_C} deg C."
            ),
            warnings=warnings,
        )

    if not has_target:
        features_missing.append("target_temp_range_c")
        warnings.append("Target temperature range is not available.")
    if not has_cand:
        if candidate.temp_min_c is None:
            features_missing.append("candidate_temp_min_c")
        if candidate.temp_max_c is None:
            features_missing.append("candidate_temp_max_c")
        warnings.append("Candidate temperature data is incomplete.")

    return DimensionResult(
        dimension="climate",
        status=DimensionStatus.UNAVAILABLE,
        features_compared=features_compared,
        features_missing=features_missing,
        methodology="No compatible temperature data available.",
        warnings=warnings,
    )
