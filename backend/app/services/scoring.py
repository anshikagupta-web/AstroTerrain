from collections.abc import Mapping
from typing import Any

def _num(value: Any) -> float | None:
    if value is None: return None
    try: return float(value)
    except (TypeError, ValueError): return None

def topography_match(target: Mapping[str, Any], analog: Mapping[str, Any]) -> float:
    a, b = _num(target.get("avg_slope_deg")), _num(analog.get("slope_deg"))
    if a is None or b is None: return 50.0
    return round(max(0.0, 100.0 - abs(a - b) * 5.0), 2)

def geochemistry_match(target: Mapping[str, Any], analog: Mapping[str, Any]) -> float:
    left = target.get("regolith_composition") or {}
    right = analog.get("spectral_signature") or {}
    if not isinstance(left, Mapping): left = {}
    if not isinstance(right, Mapping): right = {}
    scores = []
    for key in set(left).intersection(right):
        a, b = _num(left.get(key)), _num(right.get(key))
        if a is not None and b is not None:
            scores.append(max(0.0, 100.0 - abs(a - b)))
    if scores: return round(sum(scores) / len(scores), 2)
    a = (target.get("primary_rock") or "").strip().lower()
    b = (analog.get("primary_rock") or "").strip().lower()
    if a and b: return 100.0 if a == b else 25.0
    return 50.0

def climate_match(target: Mapping[str, Any], analog: Mapping[str, Any]) -> float:
    interval = target.get("temp_range_c")
    low, high = _num(analog.get("temp_min_c")), _num(analog.get("temp_max_c"))
    if not isinstance(interval, (list, tuple)) or len(interval) != 2 or low is None or high is None:
        return 50.0
    t_low, t_high = _num(interval[0]), _num(interval[1])
    if t_low is None or t_high is None: return 50.0
    if t_low > t_high: t_low, t_high = t_high, t_low
    if low > high: low, high = high, low
    overlap = max(0.0, min(t_high, high) - max(t_low, low))
    span = max(t_high, high) - min(t_low, low)
    if span == 0: return 100.0 if t_low == low else 0.0
    return round(overlap / span * 100.0, 2)

def accessibility_rating(score: Any) -> str:
    value = _num(score)
    if value is None: return "Unknown"
    if value >= 75: return "High"
    if value >= 45: return "Moderate"
    return "Low"

def score_analog(target: Mapping[str, Any], analog: Mapping[str, Any], weights: Mapping[str, float]) -> dict[str, Any]:
    breakdown = {
        "topography_match": topography_match(target, analog),
        "geochemistry_match": geochemistry_match(target, analog),
        "climate_match": climate_match(target, analog),
    }
    w = {
        "topography_match": float(weights.get("topography", 0)),
        "geochemistry_match": float(weights.get("geochemistry", 0)),
        "climate_match": float(weights.get("climate", 0)),
    }
    total = sum(w.values())
    if total <= 0: raise ValueError("At least one similarity weight must be greater than zero.")
    final = sum(breakdown[k] * v for k, v in w.items()) / total
    return {"similarity_score": round(final, 2), "breakdown": breakdown}
