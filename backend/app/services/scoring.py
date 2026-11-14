from collections.abc import Mapping
from typing import Any


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def topography_match(target: Mapping[str, Any], analog: Mapping[str, Any]) -> float | None:
    target_slope = _num(target.get("avg_slope_deg"))
    analog_slope = _num(analog.get("slope_deg"))

    if target_slope is None or analog_slope is None:
        return None

    return round(max(0.0, 100.0 - abs(target_slope - analog_slope) * 5.0), 2)


def geochemistry_match(target: Mapping[str, Any], analog: Mapping[str, Any]) -> float | None:
    left = target.get("regolith_composition") or {}
    right = analog.get("spectral_signature") or {}

    if not isinstance(left, Mapping):
        left = {}
    if not isinstance(right, Mapping):
        right = {}

    scores = []
    for key in set(left).intersection(right):
        a = _num(left.get(key))
        b = _num(right.get(key))
        if a is not None and b is not None:
            scores.append(max(0.0, 100.0 - abs(a - b)))

    if scores:
        return round(sum(scores) / len(scores), 2)

    target_rock = (target.get("primary_rock") or "").strip().lower()
    analog_rock = (analog.get("primary_rock") or "").strip().lower()

    if target_rock and analog_rock:
        return 100.0 if target_rock == analog_rock else 25.0

    return None


def climate_match(target: Mapping[str, Any], analog: Mapping[str, Any]) -> float | None:
    # Temperature values are comparable only when their measurement types match.
    target_measurement = target.get("temperature_measurement")
    analog_measurement = analog.get("temperature_measurement")

    if not target_measurement or target_measurement != analog_measurement:
        return None

    interval = target.get("temp_range_c")
    low = _num(analog.get("temp_min_c"))
    high = _num(analog.get("temp_max_c"))

    if not isinstance(interval, (list, tuple)) or len(interval) != 2:
        return None
    if low is None or high is None:
        return None

    target_low = _num(interval[0])
    target_high = _num(interval[1])

    if target_low is None or target_high is None:
        return None

    if target_low > target_high:
        target_low, target_high = target_high, target_low
    if low > high:
        low, high = high, low

    overlap = max(0.0, min(target_high, high) - max(target_low, low))
    span = max(target_high, high) - min(target_low, low)

    if span == 0:
        return 100.0 if target_low == low else 0.0

    return round(overlap / span * 100.0, 2)


def accessibility_rating(score: Any) -> str:
    value = _num(score)
    if value is None:
        return "Unknown"
    if value >= 75:
        return "High"
    if value >= 45:
        return "Moderate"
    return "Low"


def score_analog(
    target: Mapping[str, Any],
    analog: Mapping[str, Any],
    weights: Mapping[str, float],
) -> dict[str, Any]:
    breakdown = {
        "topography_match": topography_match(target, analog),
        "geochemistry_match": geochemistry_match(target, analog),
        "climate_match": climate_match(target, analog),
    }

    configured_weights = {
        "topography_match": float(weights.get("topography", 0)),
        "geochemistry_match": float(weights.get("geochemistry", 0)),
        "climate_match": float(weights.get("climate", 0)),
    }

    total_configured_weight = sum(
        weight for weight in configured_weights.values() if weight > 0
    )
    if total_configured_weight <= 0:
        raise ValueError("At least one similarity weight must be greater than zero.")

    available = [
        key for key, score in breakdown.items()
        if score is not None and configured_weights[key] > 0
    ]

    available_weight = sum(configured_weights[key] for key in available)

    if not available:
        return {
            "similarity_score": None,
            "breakdown": breakdown,
            "available_features": [],
            "feature_coverage": 0.0,
        }

    final_score = sum(
        breakdown[key] * configured_weights[key] for key in available
    ) / available_weight

    return {
        "similarity_score": round(final_score, 2),
        "breakdown": breakdown,
        "available_features": available,
        "feature_coverage": round(available_weight / total_configured_weight, 3),
    }
