"""Planet-aware feature normalization functions for the AstroTerrain ML Engine.

Each normalization function is designed for a specific feature type and its
planetary context. We do **not** apply Earth-specific bounds blindly to
extraterrestrial targets.

Scientific Reference Ranges & Justifications
---------------------------------------------
1. **Elevation Datums & Envelopes:**
   * **Earth (WGS84/EGM96 Geoid):**
     - Lowest natural point: Mariana Trench (Challenger Deep), ~-10,928 m.
     - Highest natural point: Mount Everest, ~+8,849 m.
     - Terrestrial GIS reference envelope: [-12,000 m, +30,000 m].
       Default Earth range preserves backward compatibility with standard GIS bounds.
   * **Moon (LRO LOLA 1,737.4 km Reference Sphere):**
     - Lowest topographical point: Floor of Antoniadi crater (South Pole-Aitken basin), ~-9,150 m.
     - Highest topographical point: Selenean summit on Engel'gardt crater rim, ~+10,786 m.
     - Reference envelope: [-12,000 m, +15,000 m] (total relief ~27,000 m).
       Encompasses all lunar surface relief without artificial clipping.
   * **Mars (MGS MOLA 610.5 Pa Areoid):**
     - Lowest topographical point: Hellas Planitia impact basin floor, ~-8,200 m.
     - Highest topographical point: Olympus Mons caldera rim/peak, ~+21,229 m.
     - Reference envelope: [-10,000 m, +25,000 m] (total relief ~35,000 m).
       Encompasses Hellas basin to the summit of Olympus Mons without clipping.

2. **Surface Temperatures:**
   * **Earth:**
     - Surface extremes: -89.2 deg C (Vostok Station, Antarctica; satellite skin ~-98 deg C)
       to +56.7 deg C (Death Valley; satellite skin ~+70.7 deg C in Lut Desert).
     - Operational reference envelope: [-100.0 deg C, +70.0 deg C].
   * **Moon:**
     - Vacuum thermal regime with no atmospheric moderation.
     - Permanently Shadowed Regions (PSRs, e.g. Shackleton crater floor) reach 25 K to 40 K
       (-248 deg C to -233 deg C), measured by LRO Diviner.
     - Subsolar point at equatorial noon reaches ~390 K to 400 K (+117 deg C to +127 deg C).
     - Operational reference envelope: [-250.0 deg C, +150.0 deg C].
       Ensures cryogenic polar cold traps and superheated lunar noon surface conditions
       map into [0, 1] without clipping distortion.
   * **Mars:**
     - Thin CO2 atmosphere (~6 hPa).
     - Polar winter CO2 condensation reaches ~140 K (-133 deg C; ground down to ~-143 deg C).
     - Equatorial summer midday surface ground temperatures reach +20 deg C to +35 deg C.
     - Operational reference envelope: [-150.0 deg C, +40.0 deg C].
       Ensures Martian polar winter dry-ice frost and equatorial summer midday conditions
       are mapped continuously into [0, 1] without clipping.
"""
from __future__ import annotations

import math
from typing import Any

from ml_engine.models.schemas import Planet

# ---------------------------------------------------------------------------
# Authoritative Planetary Reference Ranges
# ---------------------------------------------------------------------------

PLANETARY_ELEVATION_BOUNDS: dict[str, tuple[float, float]] = {
    "earth": (-12_000.0, 30_000.0),
    "moon": (-12_000.0, 15_000.0),
    "mars": (-10_000.0, 25_000.0),
}

PLANETARY_TEMP_BOUNDS: dict[str, tuple[float, float]] = {
    "earth": (-100.0, 70.0),
    "moon": (-250.0, 150.0),
    "mars": (-150.0, 40.0),
}


def _resolve_planet_key(planet: Planet | str | None) -> str:
    """Normalize a planet identifier to a lowercase string ('earth', 'moon', 'mars')."""
    if planet is None:
        return "earth"
    if isinstance(planet, Planet):
        return planet.value.lower()
    if isinstance(planet, str):
        key = planet.strip().lower()
        if key in ("earth", "moon", "mars"):
            return key
        raise ValueError(
            f"Unsupported planet: {planet!r}. Must be 'earth', 'moon', or 'mars'."
        )
    raise ValueError(
        f"Invalid planet type: {type(planet).__name__}. Expected Planet enum or str."
    )


def get_planetary_elevation_bounds(planet: Planet | str = "earth") -> tuple[float, float]:
    """Return the scientific elevation reference range (min_m, max_m) for *planet*."""
    key = _resolve_planet_key(planet)
    return PLANETARY_ELEVATION_BOUNDS[key]


def get_planetary_temperature_bounds(planet: Planet | str = "earth") -> tuple[float, float]:
    """Return the scientific temperature reference range (min_c, max_c) for *planet*."""
    key = _resolve_planet_key(planet)
    return PLANETARY_TEMP_BOUNDS[key]


# ---------------------------------------------------------------------------
# Normalization Functions
# ---------------------------------------------------------------------------

def normalize_elevation(
    value: float | None,
    planet: Planet | str | None = None,
    min_bound: float | None = None,
    max_bound: float | None = None,
    *,
    clip: bool = True,
) -> float | None:
    """Normalise an elevation value to [0, 1] using planet-aware bounds.

    Parameters:
        value: Elevation in meters (relative to body datum).
        planet: Planetary body ('earth', 'moon', 'mars', or Planet enum).
            Defaults to 'earth' if omitted.
        min_bound: Optional explicit lower bound in meters. Overrides planetary defaults.
        max_bound: Optional explicit upper bound in meters. Overrides planetary defaults.
        clip: If True (default), clamp normalized value to [0.0, 1.0].
            If False, return unclipped linear scale.

    Backward-compatibility:
        If *planet* is passed positionally as a numeric float/int, it is treated
        as legacy *min_bound*, preserving signatures like
        ``normalize_elevation(val, -12000.0, 30000.0)``.
    """
    if value is None or not math.isfinite(value):
        return None

    # Handle legacy positional signature: normalize_elevation(val, min_b, max_b)
    if isinstance(planet, (int, float)):
        max_bound = min_bound if max_bound is None else max_bound
        min_bound = float(planet)
        planet = "earth"

    if min_bound is not None and max_bound is not None:
        low, high = float(min_bound), float(max_bound)
    else:
        key = _resolve_planet_key(planet)
        p_low, p_high = PLANETARY_ELEVATION_BOUNDS[key]
        low = p_low if min_bound is None else float(min_bound)
        high = p_high if max_bound is None else float(max_bound)

    span = high - low
    if span <= 0:
        return None

    norm = (float(value) - low) / span
    if clip:
        norm = max(0.0, min(1.0, norm))
    return round(norm, 6)


def normalize_temperature(
    value: float | None,
    planet: Planet | str | None = None,
    min_bound: float | None = None,
    max_bound: float | None = None,
    *,
    clip: bool = True,
) -> float | None:
    """Normalise a temperature value (in deg C) to [0, 1] using planet-aware bounds.

    Parameters:
        value: Temperature in degrees Celsius.
        planet: Planetary body ('earth', 'moon', 'mars', or Planet enum).
            Defaults to 'earth' if omitted.
        min_bound: Optional explicit lower bound in deg C. Overrides planetary defaults.
        max_bound: Optional explicit upper bound in deg C. Overrides planetary defaults.
        clip: If True (default), clamp normalized value to [0.0, 1.0].
            If False, return unclipped linear scale.

    Backward-compatibility:
        If *planet* is passed positionally as a numeric float/int, it is treated
        as legacy *min_bound*, preserving signatures like
        ``normalize_temperature(val, -100.0, 70.0)``.
    """
    if value is None or not math.isfinite(value):
        return None

    # Handle legacy positional signature: normalize_temperature(val, min_b, max_b)
    if isinstance(planet, (int, float)):
        max_bound = min_bound if max_bound is None else max_bound
        min_bound = float(planet)
        planet = "earth"

    if min_bound is not None and max_bound is not None:
        low, high = float(min_bound), float(max_bound)
    else:
        key = _resolve_planet_key(planet)
        p_low, p_high = PLANETARY_TEMP_BOUNDS[key]
        low = p_low if min_bound is None else float(min_bound)
        high = p_high if max_bound is None else float(max_bound)

    span = high - low
    if span <= 0:
        return None

    norm = (float(value) - low) / span
    if clip:
        norm = max(0.0, min(1.0, norm))
    return round(norm, 6)


def normalize_temperature_range(
    temp_range: tuple[float, float] | list[float] | None,
    planet: Planet | str | None = None,
    min_bound: float | None = None,
    max_bound: float | None = None,
    *,
    clip: bool = True,
) -> tuple[float, float] | None:
    """Normalise a temperature interval [low_c, high_c] to unit interval [0, 1].

    Returns ``(norm_low, norm_high)`` where both values are in [0, 1],
    or ``None`` if invalid or non-finite.
    """
    if temp_range is None or len(temp_range) != 2:
        return None
    t0, t1 = temp_range[0], temp_range[1]
    if t0 is None or t1 is None:
        return None
    try:
        f0, f1 = float(t0), float(t1)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f0) or not math.isfinite(f1):
        return None

    n0 = normalize_temperature(
        f0, planet=planet, min_bound=min_bound, max_bound=max_bound, clip=clip,
    )
    n1 = normalize_temperature(
        f1, planet=planet, min_bound=min_bound, max_bound=max_bound, clip=clip,
    )
    if n0 is None or n1 is None:
        return None
    return (min(n0, n1), max(n0, n1))


def normalize_slope(
    value: float | None,
    max_slope: float = 90.0,
    *,
    clip: bool = True,
) -> float | None:
    """Normalise slope angle in degrees to [0, 1].

    Parameters:
        value: Slope angle in degrees (0 to 90).
        max_slope: Maximum possible slope angle (default 90.0).
        clip: If True, clamp to [0.0, 1.0].
    """
    if value is None or not math.isfinite(value):
        return None
    if max_slope <= 0:
        return None
    norm = float(value) / max_slope
    if clip:
        norm = max(0.0, min(1.0, norm))
    return round(norm, 6)


def normalize_to_unit_range(
    value: float | None,
    min_bound: float = 0.0,
    max_bound: float = 1.0,
    *,
    clip: bool = True,
) -> float | None:
    """Generic linear normalisation to [0, 1] with explicit bounds.

    Useful for features like NDVI (in [-1, 1]) or accessibility scores (in [0, 100]).
    """
    if value is None or not math.isfinite(value):
        return None
    span = max_bound - min_bound
    if span <= 0:
        return None
    norm = (float(value) - min_bound) / span
    if clip:
        norm = max(0.0, min(1.0, norm))
    return round(norm, 6)
