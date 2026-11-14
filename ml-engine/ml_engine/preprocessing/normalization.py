"""Feature normalization functions for the AstroTerrain ML Engine.

Each normalization function is designed for a specific feature type and
its physical meaning.  We do **not** blindly apply one method to all
features.

Design decisions
----------------
* **Elevation** — linear scaling against known planetary range bounds.
  This avoids data leakage because bounds are fixed physical constants,
  not fitted from the dataset.
* **Slope** — direct ratio against maximum possible slope (90°).
* **Temperature** — linear scaling against known temperature bounds.

All normalised values are mapped to [0, 1].
"""
from __future__ import annotations

import math


def normalize_elevation(
    value: float | None,
    min_bound: float = -12_000.0,
    max_bound: float = 30_000.0,
) -> float | None:
    """Normalise elevation to [0, 1] using fixed physical bounds.

    Default bounds cover Earth's deepest ocean trench (~−11 000 m)
    to above Mt Everest (~8 849 m), with margin.
    """
    if value is None or not math.isfinite(value):
        return None
    span = max_bound - min_bound
    if span <= 0:
        return None
    return max(0.0, min(1.0, (value - min_bound) / span))


def normalize_slope(
    value: float | None,
    max_slope: float = 90.0,
) -> float | None:
    """Normalise slope angle to [0, 1]."""
    if value is None or not math.isfinite(value):
        return None
    if max_slope <= 0:
        return None
    return max(0.0, min(1.0, value / max_slope))


def normalize_temperature(
    value: float | None,
    min_bound: float = -100.0,
    max_bound: float = 70.0,
) -> float | None:
    """Normalise a temperature value to [0, 1] using fixed physical bounds."""
    if value is None or not math.isfinite(value):
        return None
    span = max_bound - min_bound
    if span <= 0:
        return None
    return max(0.0, min(1.0, (value - min_bound) / span))


def normalize_to_unit_range(
    value: float | None,
    min_bound: float = 0.0,
    max_bound: float = 1.0,
) -> float | None:
    """Generic linear normalisation to [0, 1] with explicit bounds.

    Useful for features like NDVI (already in [−1, 1]) or accessibility
    scores (in [0, 100]).
    """
    if value is None or not math.isfinite(value):
        return None
    span = max_bound - min_bound
    if span <= 0:
        return None
    return max(0.0, min(1.0, (value - min_bound) / span))
