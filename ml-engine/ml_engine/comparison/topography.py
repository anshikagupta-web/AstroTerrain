"""Topographical similarity comparison.

Compares elevation, slope, and terrain characteristics between a
planetary target and an Earth candidate.

Methodology
-----------
Individual feature similarities use **Gaussian (exponential-decay)**
functions calibrated to the physical scale of each feature:

* Maps naturally to [0, 100] without arbitrary cutoffs.
* The decay rate (*sigma*) is set per-feature based on what constitutes
  a "significant" difference in planetary science.
* Handles the full range of possible values gracefully.

Default sigma values:
* **Elevation**: sigma = 2 000 m  (a 2 km difference -> ~60.65% similarity).
* **Slope**: sigma = 5.0 deg  (a 5 deg difference -> ~60.65% similarity).

Scientific Note on Planetary Elevation Datums:
Planetary elevations are defined relative to specific celestial datums:
- Moon: Reference sphere of radius 1,737.4 km (LOLA).
- Mars: Martian areoid / 610.5 Pa equipotential pressure level (MOLA).
- Earth: Mean sea level / WGS84 geoid (EGM96).
Because datum references differ fundamentally, geometric slope angle
serves as the primary universal, transferable topographical metric.
Absolute datum elevation differences are weighted cautiously (default
70% slope / 30% elevation).
"""
from __future__ import annotations

import math

from ml_engine.models.schemas import (
    DimensionResult,
    DimensionStatus,
    EarthCandidate,
    PlanetaryTarget,
)

# Decay parameters -- sigma is the difference at which similarity ~= 60.65%.
ELEVATION_SIGMA_M: float = 2_000.0
SLOPE_SIGMA_DEG: float = 5.0

# Sub-feature weights within topography (emphasize universal slope over arbitrary datum elevation)
DEFAULT_SLOPE_WEIGHT: float = 0.70
DEFAULT_ELEVATION_WEIGHT: float = 0.30


def _gaussian_similarity(a: float, b: float, sigma: float) -> float:
    """Gaussian similarity in [0, 100].

    Returns 100 when identical, ~60.65 when |a - b| == sigma,
    and approaches 0 as the difference grows.
    """
    if sigma <= 0:
        return 100.0 if a == b else 0.0
    return 100.0 * math.exp(-((a - b) ** 2) / (2.0 * sigma ** 2))


def compare_topography(
    target: PlanetaryTarget,
    candidate: EarthCandidate,
    slope_weight: float = DEFAULT_SLOPE_WEIGHT,
    elevation_weight: float = DEFAULT_ELEVATION_WEIGHT,
) -> DimensionResult:
    """Compare topographical features between *target* and *candidate*.

    Args:
        target: Validated planetary target.
        candidate: Validated Earth candidate.
        slope_weight: Weight given to slope similarity (default 0.70).
        elevation_weight: Weight given to elevation similarity (default 0.30).

    Returns:
        ``DimensionResult`` with status ``COMPUTED`` when at least
        one of elevation or slope can be compared, or ``UNAVAILABLE``
        otherwise.
    """
    features_compared: list[str] = []
    features_missing: list[str] = []
    warnings: list[str] = []
    sub_scores: list[tuple[float, float]] = []  # (score, weight)

    # --- Elevation ---
    if target.elevation_m is not None and candidate.elevation_m is not None:
        sim = _gaussian_similarity(
            target.elevation_m, candidate.elevation_m, ELEVATION_SIGMA_M,
        )
        sub_scores.append((sim, elevation_weight))
        features_compared.append("elevation_m")
        warnings.append(
            "Notice: Target and candidate elevations are referenced to distinct "
            "planetary datums (e.g. lunar 1737.4 km sphere vs Earth geoid). "
            "Geometric slope angle is the primary transferable topographic metric."
        )
    else:
        features_missing.append("elevation_m")
        if target.elevation_m is None:
            warnings.append("Target elevation is not available.")
        if candidate.elevation_m is None:
            warnings.append("Candidate elevation is not available.")

    # --- Slope ---
    t_slope = target.avg_slope_deg
    c_slope = candidate.slope_deg

    if t_slope is not None and c_slope is not None:
        sim = _gaussian_similarity(t_slope, c_slope, SLOPE_SIGMA_DEG)
        sub_scores.append((sim, slope_weight))
        features_compared.append("slope_deg")
    else:
        features_missing.append("slope_deg")
        if t_slope is None:
            warnings.append("Target slope is not available.")
        if c_slope is None:
            warnings.append("Candidate slope is not available.")

    # --- Aggregate ---
    if not sub_scores:
        return DimensionResult(
            dimension="topography",
            status=DimensionStatus.UNAVAILABLE,
            features_compared=features_compared,
            features_missing=features_missing,
            methodology="No topographic features available for comparison.",
            warnings=warnings,
        )

    total_w = sum(w for _, w in sub_scores)
    score = round(sum(s * w for s, w in sub_scores) / total_w, 2)

    parts: list[str] = []
    if "slope_deg" in features_compared:
        parts.append(
            f"Slope (Gaussian sigma={SLOPE_SIGMA_DEG} deg, weight={slope_weight:.2f}): "
            f"target={t_slope} deg, candidate={c_slope} deg"
        )
    if "elevation_m" in features_compared:
        parts.append(
            f"Elevation (Gaussian sigma={ELEVATION_SIGMA_M}m, weight={elevation_weight:.2f}): "
            f"target={target.elevation_m}m, candidate={candidate.elevation_m}m"
        )

    return DimensionResult(
        dimension="topography",
        score=score,
        status=DimensionStatus.COMPUTED,
        features_compared=features_compared,
        features_missing=features_missing,
        methodology="Weighted Gaussian similarity. " + "; ".join(parts),
        warnings=warnings,
    )
