"""AstroTerrain ML Engine -- Module 4.

Spatial Machine Learning Engine for planetary analogue site comparison.
"""

from ml_engine.adapter import (
    score_analog,
    topography_match,
    geochemistry_match,
    climate_match,
    accessibility_rating,
)
from ml_engine.comparison.similarity import calculate_weighted_similarity
from ml_engine.ranking.candidate_ranking import rank_candidates
from ml_engine.explainability.explanations import generate_explanation
from ml_engine.reporting.site_reports import generate_site_report, render_report_text

__version__ = "0.1.0"

__all__ = [
    "score_analog",
    "topography_match",
    "geochemistry_match",
    "climate_match",
    "accessibility_rating",
    "calculate_weighted_similarity",
    "rank_candidates",
    "generate_explanation",
    "generate_site_report",
    "render_report_text",
]
