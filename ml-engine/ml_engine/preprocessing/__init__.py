"""Feature preprocessing pipeline for the AstroTerrain ML Engine.

Handles feature validation, planet-aware normalization, and missing-value detection
for both planetary targets and Earth candidate profiles.
"""

from ml_engine.preprocessing.feature_validation import (
    validate_target_features,
    validate_candidate_features,
)
from ml_engine.preprocessing.normalization import (
    normalize_elevation,
    normalize_slope,
    normalize_temperature,
    normalize_temperature_range,
    normalize_to_unit_range,
    get_planetary_elevation_bounds,
    get_planetary_temperature_bounds,
    PLANETARY_ELEVATION_BOUNDS,
    PLANETARY_TEMP_BOUNDS,
)
from ml_engine.preprocessing.missing_values import (
    check_missing_features,
    imputation_not_supported,
)

__all__ = [
    "validate_target_features",
    "validate_candidate_features",
    "normalize_elevation",
    "normalize_slope",
    "normalize_temperature",
    "normalize_temperature_range",
    "normalize_to_unit_range",
    "get_planetary_elevation_bounds",
    "get_planetary_temperature_bounds",
    "PLANETARY_ELEVATION_BOUNDS",
    "PLANETARY_TEMP_BOUNDS",
    "check_missing_features",
    "imputation_not_supported",
]
