"""Missing-value detection and handling for the AstroTerrain ML Engine.

The engine does **not** impute missing geoscientific measurements.
Imputation would introduce fabricated data into a scientific comparison.

Design decisions
----------------
* Missing features are detected and reported, never silently filled.
* The comparison engine uses these reports to exclude unavailable
  dimensions and renormalise weights accordingly.
* A clear distinction is maintained between "missing" (no data),
  "invalid" (bad data), and "low score" (valid but dissimilar).
"""
from __future__ import annotations

from ml_engine.models.schemas import DataQuality, FeatureReport


def check_missing_features(
    reports: list[FeatureReport],
    required_features: list[str],
) -> dict[str, DataQuality]:
    """Check which *required_features* are missing or invalid.

    Returns:
        Dict mapping feature name -> ``DataQuality`` for every feature
        that is **not** ``VALID``.
    """
    report_map = {r.feature_name: r for r in reports}
    issues: dict[str, DataQuality] = {}
    for feat in required_features:
        if feat not in report_map:
            issues[feat] = DataQuality.MISSING
        elif report_map[feat].quality != DataQuality.VALID:
            issues[feat] = report_map[feat].quality
    return issues


def imputation_not_supported(feature_name: str) -> str:
    """Return a standard warning explaining why imputation is not used."""
    return (
        f"Feature '{feature_name}' is missing. The AstroTerrain ML Engine "
        f"does not impute missing geoscientific measurements because "
        f"fabricated values would undermine scientific integrity. "
        f"This dimension will be excluded from the similarity calculation "
        f"and the remaining weights will be renormalised."
    )


def summarize_data_quality(
    reports: list[FeatureReport],
) -> dict[str, list[str]]:
    """Summarise feature validation reports by quality category.

    Returns:
        Dict with keys ``valid``, ``missing``, ``invalid``,
        ``out_of_range``, each mapping to a list of feature names.
    """
    summary: dict[str, list[str]] = {
        "valid": [],
        "missing": [],
        "invalid": [],
        "out_of_range": [],
    }
    for report in reports:
        summary[report.quality.value].append(report.feature_name)
    return summary
