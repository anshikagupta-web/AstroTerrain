"""Topographical similarity comparison.

Compares terrain characteristics between a planetary target and an Earth
candidate using datum-invariant geometric slope analysis.

Scientific Foundation: Geodetic Datum Independence
---------------------------------------------------
Planetary elevations are defined relative to fundamentally distinct geodetic datums:
* **Moon (LRO LOLA):** Arbitrary geometric reference sphere of radius 1,737.4 km.
* **Mars (MGS MOLA):** Martian Areoid (610.5 Pa equipotential pressure level).
* **Earth (WGS84/EGM2008):** Mean sea level geoid.

Because these reference zeroes represent completely distinct physical quantities
(geometric radius vs atmospheric pressure vs gravitational equipotential),
direct numerical comparison of absolute elevation (|z_t - z_c|) across celestial
bodies is scientifically invalid:
- A Martian crater basin at -2,500 m (e.g. Jezero) would suffer a heavy artificial
  penalty against any dry terrestrial analogue, while falsely matching an abyssal
  ocean trench on Earth.
- A lunar crater floor at -3,500 m (e.g. Shackleton) would be similarly distorted.

In contrast, **geometric slope angle** (theta = arctan(||grad z||)) is the spatial
derivative of elevation over horizontal distance. Any constant vertical datum offset
strictly cancels out (grad(z + C) = grad z). Slope is 100% universal and transferable,
directly governing rover trafficability, geotechnical stability, and solar illumination.

Scoring Methodology & Calibration Parameter
----------------------------------------------
Topography similarity is evaluated strictly on datum-invariant geometric slope
using a configurable Gaussian (exponential-decay) function:

    S_slope = 100 * exp(-((target_slope - candidate_slope)^2) / (2 * sigma_slope^2))

**Calibration Notice:**
The default decay scale ``SLOPE_SIGMA_DEG = 5.0 deg`` (where a 5.0 deg slope difference
yields ~60.65% similarity) is an **initial configurable calibration parameter**
derived from planetary rover mobility heuristics (e.g., MSL Curiosity and Mars 2020
Perseverance traverse constraints, where 5 deg represents a significant shift in wheel slip
and trafficability). **It is NOT a scientifically validated universal threshold for all
planetary bodies and landforms.** It can be configured or tuned per investigation via the
``slope_sigma_deg`` parameter to suit specific mission criteria (e.g. strict rover
trafficability vs broader geomorphic terrain classification).

Absolute elevation is **excluded** from cross-planetary similarity scoring (weight = 0.0),
but remains fully tracked and validated for metadata, diagnostic reporting, and
environmental profiling. Local relief and roughness are reserved as future extensions
requiring 2D DEM raster ingestion.
"""
from __future__ import annotations

import math

from ml_engine.models.schemas import (
    DimensionResult,
    DimensionStatus,
    EarthCandidate,
    PlanetaryTarget,
)

# Initial configurable calibration parameter for geometric slope (NOT a universal threshold)
SLOPE_SIGMA_DEG: float = 5.0

# Reference dispersion for elevation (retained for backward compatibility / single-body use)
ELEVATION_SIGMA_M: float = 2_000.0

# Sub-feature weights: slope is the universal active metric; elevation is 0.0 to prevent datum distortion
DEFAULT_SLOPE_WEIGHT: float = 1.00
DEFAULT_ELEVATION_WEIGHT: float = 0.00


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
    slope_sigma_deg: float = SLOPE_SIGMA_DEG,
) -> DimensionResult:
    """Compare topographical features between *target* and *candidate*.

    Evaluates datum-invariant geometric slope angle. Absolute elevation is
    tracked in metadata and reports, but excluded from cross-planetary scoring
    (elevation_weight=0.0) to avoid datum distortion.

    Args:
        target: Validated planetary target.
        candidate: Validated Earth candidate.
        slope_weight: Weight given to slope similarity (default 1.00).
        elevation_weight: Weight given to elevation similarity (default 0.00).
        slope_sigma_deg: Configurable Gaussian dispersion parameter in degrees
            (default 5.0 deg). Configurable heuristic parameter, not a universal threshold.

    Returns:
        ``DimensionResult`` with status ``COMPUTED`` when slope is available,
        or ``UNAVAILABLE`` if slope data is missing on either profile.
    """
    features_compared: list[str] = []
    features_missing: list[str] = []
    warnings: list[str] = []
    sub_scores: list[tuple[float, float]] = []  # (score, weight)

    # --- Elevation (Validation & Informative Metadata Tracking) ---
    t_elev = target.elevation_m
    c_elev = candidate.elevation_m

    if t_elev is None or c_elev is None:
        features_missing.append("elevation_m")
        if t_elev is None:
            warnings.append("Target elevation is not available.")
        if c_elev is None:
            warnings.append("Candidate elevation is not available.")
    else:
        # Elevation is available on both profiles.
        if elevation_weight > 0.0:
            # Explicit non-default override: caller requested elevation scoring
            sim_elev = _gaussian_similarity(t_elev, c_elev, ELEVATION_SIGMA_M)
            sub_scores.append((sim_elev, elevation_weight))
            features_compared.append("elevation_m")
            warnings.append(
                "Notice: Target and candidate elevations are referenced to distinct "
                "planetary datums. Elevation difference contributed to score per caller override."
            )
        else:
            # Default cross-planetary policy: track elevation in metadata, exclude from scoring
            warnings.append(
                "Notice: Target and candidate elevations are referenced to distinct "
                "planetary datums (e.g. lunar 1737.4 km sphere / Martian areoid vs Earth geoid). "
                "Absolute elevation is excluded from cross-planetary scoring to prevent geodetic datum mismatch distortion."
            )

    # --- Geometric Slope (Universal Datum-Invariant Metric) ---
    t_slope = target.avg_slope_deg
    c_slope = candidate.slope_deg

    if t_slope is not None and c_slope is not None:
        sim_slope = _gaussian_similarity(t_slope, c_slope, slope_sigma_deg)
        if slope_weight > 0.0:
            sub_scores.append((sim_slope, slope_weight))
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
            methodology="No valid datum-independent topographic features (slope) available for comparison.",
            warnings=warnings,
        )

    total_w = sum(w for _, w in sub_scores)
    if total_w <= 0:
        return DimensionResult(
            dimension="topography",
            status=DimensionStatus.UNAVAILABLE,
            features_compared=features_compared,
            features_missing=features_missing,
            methodology="All available topographic feature weights sum to zero.",
            warnings=warnings,
        )

    score = round(sum(s * w for s, w in sub_scores) / total_w, 2)

    parts: list[str] = []
    if "slope_deg" in features_compared:
        parts.append(
            f"Slope (Gaussian sigma={slope_sigma_deg} deg, weight={slope_weight:.2f}): "
            f"target={t_slope} deg, candidate={c_slope} deg"
        )
    if "elevation_m" in features_compared and elevation_weight > 0.0:
        parts.append(
            f"Elevation (Gaussian sigma={ELEVATION_SIGMA_M}m, weight={elevation_weight:.2f}): "
            f"target={t_elev}m, candidate={c_elev}m"
        )
    elif t_elev is not None and c_elev is not None:
        parts.append(
            f"Elevation tracked as metadata (weight=0.00): target={t_elev}m, candidate={c_elev}m"
        )

    return DimensionResult(
        dimension="topography",
        score=score,
        status=DimensionStatus.COMPUTED,
        features_compared=features_compared,
        features_missing=features_missing,
        methodology="Datum-invariant Gaussian slope similarity. " + "; ".join(parts),
        warnings=warnings,
    )
