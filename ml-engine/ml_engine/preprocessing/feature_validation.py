"""Feature validation for planetary targets and Earth candidates.

Validates data types, value ranges, and physical plausibility of
geospatial and environmental features.

Design decisions
----------------
* Each feature is validated independently so that one invalid feature
  does not prevent comparison on other valid features.
* Validation reports are attached to the profile objects so the
  comparison engine can inspect data quality per feature.
* Strict physical measurement validation: out-of-range values are
  flagged as OUT_OF_RANGE and are strictly excluded from entering
  scoring calculations.
* Planet-specific bounds differentiate lunar extreme thermal vacuum
  from Martian atmospheric conditions.
"""
from __future__ import annotations

import math
from typing import Any

from ml_engine.models.schemas import (
    DataQuality,
    EarthCandidate,
    FeatureReport,
    Planet,
    PlanetaryTarget,
)
from ml_engine.preprocessing.normalization import (
    PLANETARY_ELEVATION_BOUNDS,
    PLANETARY_TEMP_BOUNDS,
    normalize_temperature,
)

# ---------------------------------------------------------------------------
# Physical range definitions
# ---------------------------------------------------------------------------

ELEVATION_RANGE_M = PLANETARY_ELEVATION_BOUNDS["earth"]
SLOPE_RANGE_DEG = (0.0, 90.0)
EARTH_TEMP_RANGE_C = PLANETARY_TEMP_BOUNDS["earth"]
NDVI_RANGE = (-1.0, 1.0)
ACCESSIBILITY_RANGE = (0.0, 100.0)
LAT_RANGE = (-90.0, 90.0)
LNG_RANGE = (-180.0, 180.0)

# General planetary bounds
PLANETARY_ELEVATION_RANGE_M = (-30_000.0, 30_000.0)
PLANETARY_TEMP_RANGE_C = (-270.0, 500.0)

# Planet-specific physical bounds (Moon vs Mars)
MOON_TEMP_RANGE_C = PLANETARY_TEMP_BOUNDS["moon"]
MOON_ELEVATION_RANGE_M = PLANETARY_ELEVATION_BOUNDS["moon"]

MARS_TEMP_RANGE_C = PLANETARY_TEMP_BOUNDS["mars"]
MARS_ELEVATION_RANGE_M = PLANETARY_ELEVATION_BOUNDS["mars"]


def _is_finite_number(value: Any) -> bool:
    """Return True if *value* is a finite int or float (not bool)."""
    if value is None or isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return math.isfinite(value)
    return False


def _validate_numeric(
    name: str, value: Any, low: float, high: float,
) -> FeatureReport:
    """Validate a single numeric feature against a range."""
    if value is None:
        return FeatureReport(
            feature_name=name, quality=DataQuality.MISSING,
            message=f"Feature '{name}' is not provided.",
        )
    if not _is_finite_number(value):
        return FeatureReport(
            feature_name=name, quality=DataQuality.INVALID,
            raw_value=value,
            message=f"Feature '{name}' has non-numeric or non-finite value: {value!r}.",
        )
    fval = float(value)
    if fval < low or fval > high:
        return FeatureReport(
            feature_name=name, quality=DataQuality.OUT_OF_RANGE,
            raw_value=fval, normalized_value=None,  # Do not normalize out-of-range value
            message=f"Feature '{name}' value {fval} outside expected range [{low}, {high}].",
        )
    span = high - low
    norm_val = round(max(0.0, min(1.0, (fval - low) / span)), 6) if span > 0 else 0.0
    return FeatureReport(
        feature_name=name, quality=DataQuality.VALID,
        raw_value=fval, normalized_value=norm_val,
    )


def _validate_string(name: str, value: Any) -> FeatureReport:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return FeatureReport(
            feature_name=name, quality=DataQuality.MISSING,
            raw_value=value,
            message=f"Feature '{name}' is not provided.",
        )
    if not isinstance(value, str):
        return FeatureReport(
            feature_name=name, quality=DataQuality.INVALID,
            raw_value=value,
            message=f"Feature '{name}' expected str, got {type(value).__name__}.",
        )
    return FeatureReport(
        feature_name=name, quality=DataQuality.VALID,
        raw_value=value.strip().lower(),
    )


def _validate_dict(name: str, value: Any) -> FeatureReport:
    if value is None:
        return FeatureReport(
            feature_name=name, quality=DataQuality.MISSING,
            message=f"Feature '{name}' is not provided.",
        )
    if not isinstance(value, dict):
        return FeatureReport(
            feature_name=name, quality=DataQuality.INVALID,
            raw_value=value,
            message=f"Feature '{name}' expected dict, got {type(value).__name__}.",
        )
    if len(value) == 0:
        return FeatureReport(
            feature_name=name, quality=DataQuality.MISSING,
            raw_value=value,
            message=f"Feature '{name}' is an empty dictionary.",
        )
    return FeatureReport(
        feature_name=name, quality=DataQuality.VALID, raw_value=value,
    )


# ---------------------------------------------------------------------------
# Helper to extract strictly validated values from reports
# ---------------------------------------------------------------------------

def _get_valid_float(reports: list[FeatureReport], name: str) -> float | None:
    """Extract a float value ONLY if quality is strictly VALID.

    Out-of-range, invalid, or missing values return None to prevent corrupt
    measurements from silently entering similarity scoring.
    """
    for r in reports:
        if r.feature_name == name and r.quality == DataQuality.VALID:
            return float(r.raw_value) if r.raw_value is not None else None
    return None


def _get_valid_string(reports: list[FeatureReport], name: str) -> str | None:
    for r in reports:
        if r.feature_name == name and r.quality == DataQuality.VALID:
            return str(r.raw_value) if r.raw_value is not None else None
    return None


def _get_valid_dict(reports: list[FeatureReport], name: str) -> dict:
    for r in reports:
        if r.feature_name == name and r.quality == DataQuality.VALID:
            return dict(r.raw_value) if isinstance(r.raw_value, dict) else {}
    return {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_target_features(
    raw: dict[str, Any],
    strict: bool = False,
) -> tuple[PlanetaryTarget, list[FeatureReport]]:
    """Validate and build a *PlanetaryTarget* from a raw backend dict.

    Args:
        raw: Target attributes dictionary.
        strict: If True, raise ValueError immediately upon encountering any
            INVALID or OUT_OF_RANGE measurement.

    Returns:
        ``(PlanetaryTarget, list[FeatureReport])``

    Raises:
        ValueError: If required identifiers are missing or invalid, or if
            strict=True and a measurement is out of physical bounds.
    """
    planet_str = raw.get("planet")
    if planet_str is None:
        raise ValueError("Missing 'planet' in target profile.")
    if planet_str not in ("moon", "mars"):
        raise ValueError(
            f"Unsupported or missing planet: {planet_str!r}. "
            "Must be 'moon' or 'mars'."
        )
    site_id = raw.get("site_id")
    if not site_id or not isinstance(site_id, str):
        raise ValueError("Missing or invalid 'site_id'.")
    site_name = raw.get("site_name")
    if not site_name or not isinstance(site_name, str):
        raise ValueError("Missing or invalid 'site_name'.")

    planet = Planet(planet_str)
    reports: list[FeatureReport] = []

    # Planet-specific physical bounds
    elev_range = (
        MOON_ELEVATION_RANGE_M if planet == Planet.MOON else MARS_ELEVATION_RANGE_M
    )
    temp_bound = (
        MOON_TEMP_RANGE_C if planet == Planet.MOON else MARS_TEMP_RANGE_C
    )

    reports.append(_validate_numeric(
        "elevation_m", raw.get("elevation_m"), *elev_range,
    ))
    reports.append(_validate_numeric(
        "avg_slope_deg", raw.get("avg_slope_deg"), *SLOPE_RANGE_DEG,
    ))
    reports.append(_validate_numeric("lat", raw.get("lat"), *LAT_RANGE))
    reports.append(_validate_numeric("lng", raw.get("lng"), *LNG_RANGE))
    reports.append(_validate_string("primary_rock", raw.get("primary_rock")))
    reports.append(_validate_dict(
        "regolith_composition", raw.get("regolith_composition"),
    ))

    # Temperature range -- special handling (list/tuple of two numbers)
    temp_raw = raw.get("temp_range_c")
    temp_tuple: tuple[float, float] | None = None
    if temp_raw is None:
        reports.append(FeatureReport(
            feature_name="temp_range_c", quality=DataQuality.MISSING,
            message="Temperature range is not provided.",
        ))
    elif not isinstance(temp_raw, (list, tuple)) or len(temp_raw) != 2:
        reports.append(FeatureReport(
            feature_name="temp_range_c", quality=DataQuality.INVALID,
            raw_value=temp_raw,
            message=f"Temperature range must be [low, high], got: {temp_raw!r}.",
        ))
    else:
        t_lo, t_hi = temp_raw
        if not _is_finite_number(t_lo) or not _is_finite_number(t_hi):
            reports.append(FeatureReport(
                feature_name="temp_range_c", quality=DataQuality.INVALID,
                raw_value=temp_raw,
                message=f"Temperature values must be finite numbers: {temp_raw!r}.",
            ))
        else:
            lo, hi = float(t_lo), float(t_hi)
            if lo > hi:
                lo, hi = hi, lo
            if lo < temp_bound[0] or hi > temp_bound[1]:
                reports.append(FeatureReport(
                    feature_name="temp_range_c", quality=DataQuality.OUT_OF_RANGE,
                    raw_value=temp_raw,
                    message=(
                        f"Temperature [{lo}, {hi}] partially outside expected "
                        f"{planet.value} bounds [{temp_bound[0]}, {temp_bound[1]}]."
                    ),
                ))
                temp_tuple = None  # Strictly reject out-of-range temperature from entering profile
            else:
                norm_mid = normalize_temperature((lo + hi) / 2.0, planet=planet)
                reports.append(FeatureReport(
                    feature_name="temp_range_c", quality=DataQuality.VALID,
                    raw_value=temp_raw, normalized_value=norm_mid,
                ))
                temp_tuple = (lo, hi)

    if strict:
        for r in reports:
            if r.quality in (DataQuality.INVALID, DataQuality.OUT_OF_RANGE):
                raise ValueError(
                    f"Strict validation failure for target '{site_id}': "
                    f"{r.feature_name} is {r.quality.value} ({r.message})"
                )

    target_meas_type = raw.get("temp_measurement_type")
    if not target_meas_type or target_meas_type == "unknown":
        ds = str(raw.get("data_source", "")).lower()
        if "meda" in ds:
            target_meas_type = "ground_surface"
        elif "diviner" in ds:
            target_meas_type = "spatial_extremes_surface" if planet == Planet.MOON else "ground_surface"
        elif "themis" in ds or "hirise" in ds or "kaguya" in ds:
            target_meas_type = "ground_surface"
        else:
            target_meas_type = "unknown"

    target = PlanetaryTarget(
        planet=planet,
        site_id=site_id,
        site_name=site_name,
        lat=_get_valid_float(reports, "lat"),
        lng=_get_valid_float(reports, "lng"),
        elevation_m=_get_valid_float(reports, "elevation_m"),
        avg_slope_deg=_get_valid_float(reports, "avg_slope_deg"),
        regolith_composition=_get_valid_dict(reports, "regolith_composition"),
        primary_rock=_get_valid_string(reports, "primary_rock"),
        temp_range_c=temp_tuple,
        temp_measurement_type=target_meas_type,
        data_source=raw.get("data_source", "unknown"),
        feature_reports=reports,
    )
    return target, reports


def validate_candidate_features(
    raw: dict[str, Any],
    strict: bool = False,
) -> tuple[EarthCandidate, list[FeatureReport]]:
    """Validate and build an *EarthCandidate* from a raw backend dict.

    Args:
        raw: Candidate attributes dictionary.
        strict: If True, raise ValueError immediately upon encountering any
            INVALID or OUT_OF_RANGE measurement.

    Returns:
        ``(EarthCandidate, list[FeatureReport])``

    Raises:
        ValueError: If required identifiers are missing or invalid, or if
            strict=True and a measurement is out of physical bounds.
    """
    site_id = raw.get("site_id")
    if not site_id or not isinstance(site_id, str):
        raise ValueError("Missing or invalid 'site_id'.")
    site_name = raw.get("site_name")
    if not site_name or not isinstance(site_name, str):
        raise ValueError("Missing or invalid 'site_name'.")

    reports: list[FeatureReport] = []
    reports.append(_validate_numeric(
        "elevation_m", raw.get("elevation_m"), *ELEVATION_RANGE_M,
    ))
    reports.append(_validate_numeric(
        "slope_deg", raw.get("slope_deg"), *SLOPE_RANGE_DEG,
    ))
    reports.append(_validate_numeric("ndvi", raw.get("ndvi"), *NDVI_RANGE))
    reports.append(_validate_numeric(
        "temp_min_c", raw.get("temp_min_c"), *EARTH_TEMP_RANGE_C,
    ))
    reports.append(_validate_numeric(
        "temp_max_c", raw.get("temp_max_c"), *EARTH_TEMP_RANGE_C,
    ))
    reports.append(_validate_numeric(
        "accessibility_score", raw.get("accessibility_score"),
        *ACCESSIBILITY_RANGE,
    ))
    reports.append(_validate_numeric("lat", raw.get("lat"), *LAT_RANGE))
    reports.append(_validate_numeric("lng", raw.get("lng"), *LNG_RANGE))
    reports.append(_validate_string("primary_rock", raw.get("primary_rock")))
    reports.append(_validate_dict(
        "spectral_signature", raw.get("spectral_signature"),
    ))

    if strict:
        for r in reports:
            if r.quality in (DataQuality.INVALID, DataQuality.OUT_OF_RANGE):
                raise ValueError(
                    f"Strict validation failure for candidate '{site_id}': "
                    f"{r.feature_name} is {r.quality.value} ({r.message})"
                )

    tmin = _get_valid_float(reports, "temp_min_c")
    tmax = _get_valid_float(reports, "temp_max_c")
    if tmin is not None and tmax is not None and tmin > tmax:
        tmin, tmax = tmax, tmin

    cand_meas_type = raw.get("temp_measurement_type")
    if not cand_meas_type or cand_meas_type == "unknown":
        ds = str(raw.get("data_source", "")).lower()
        if "nasa_power" in ds:
            cand_meas_type = "air_2m"
        else:
            cand_meas_type = "unknown"

    candidate = EarthCandidate(
        site_id=site_id,
        site_name=site_name,
        country=raw.get("country") or "Unknown",
        lat=_get_valid_float(reports, "lat"),
        lng=_get_valid_float(reports, "lng"),
        elevation_m=_get_valid_float(reports, "elevation_m"),
        slope_deg=_get_valid_float(reports, "slope_deg"),
        ndvi=_get_valid_float(reports, "ndvi"),
        spectral_signature=_get_valid_dict(reports, "spectral_signature"),
        primary_rock=_get_valid_string(reports, "primary_rock"),
        temp_min_c=tmin,
        temp_max_c=tmax,
        temp_measurement_type=cand_meas_type,
        accessibility_score=_get_valid_float(reports, "accessibility_score"),
        is_subterranean=bool(raw.get("is_subterranean", False)),
        data_source=raw.get("data_source", "unknown"),
        feature_reports=reports,
    )
    return candidate, reports
