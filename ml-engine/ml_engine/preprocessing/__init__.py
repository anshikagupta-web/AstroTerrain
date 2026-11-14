"""Feature preprocessing pipeline for the AstroTerrain ML Engine.

Handles feature validation, normalization, and missing-value detection
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
    "check_missing_features",
    "imputation_not_supported",
]
