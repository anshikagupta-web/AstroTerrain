"""Comparison engines for the AstroTerrain ML Engine.

Each module implements one dimension of the multi-criteria similarity:
    - topography: elevation, slope, terrain characteristics.
    - geochemistry: mineralogical composition and spectral analysis.
    - climate: temperature ranges and environmental conditions.
    - similarity: weighted multi-criteria aggregation.
"""

from ml_engine.comparison.topography import compare_topography
from ml_engine.comparison.geochemistry import compare_geochemistry
from ml_engine.comparison.climate import compare_climate
from ml_engine.comparison.similarity import calculate_weighted_similarity

__all__ = [
    "compare_topography",
    "compare_geochemistry",
    "compare_climate",
    "calculate_weighted_similarity",
]
