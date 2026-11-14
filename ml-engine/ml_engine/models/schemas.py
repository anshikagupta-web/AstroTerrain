"""Data models for the AstroTerrain ML Engine.

These schemas define the internal data structures used by the ML Engine for
feature validation, comparison results, and explainability outputs.  They are
distinct from the backend's Pydantic models (which belong to Module 3).
"""
from __future__ import annotations

import enum
import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Planet(str, enum.Enum):
    """Supported planetary bodies."""
    EARTH = "earth"
    MOON = "moon"
    MARS = "mars"


class DataQuality(str, enum.Enum):
    """Quality status for a single feature value."""
    VALID = "valid"
    MISSING = "missing"
    INVALID = "invalid"
    OUT_OF_RANGE = "out_of_range"


class DimensionStatus(str, enum.Enum):
    """Whether a comparison dimension could be computed."""
    COMPUTED = "computed"
    UNAVAILABLE = "unavailable"


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

class FeatureReport(BaseModel):
    """Validation report for a single feature."""
    model_config = ConfigDict(extra="forbid")

    feature_name: str
    quality: DataQuality
    raw_value: Any = None
    normalized_value: float | None = None
    message: str = ""


# ---------------------------------------------------------------------------
# Profile schemas
# ---------------------------------------------------------------------------

class PlanetaryTarget(BaseModel):
    """Preprocessed planetary target profile.

    Represents a lunar or Martian site with its measurable features.
    Not all features will be available for every target.
    """
    model_config = ConfigDict(extra="forbid")

    planet: Planet
    site_id: str
    site_name: str
    lat: float | None = None
    lng: float | None = None
    elevation_m: float | None = None
    avg_slope_deg: float | None = None
    regolith_composition: dict[str, float] = Field(default_factory=dict)
    primary_rock: str | None = None
    temp_range_c: tuple[float, float] | None = None
    temp_measurement_type: str = "unknown"
    data_source: str = "unknown"
    feature_reports: list[FeatureReport] = Field(default_factory=list)


class EarthCandidate(BaseModel):
    """Preprocessed Earth analogue candidate profile.

    Represents a terrestrial location being evaluated as a potential
    analogue for a planetary target site.
    """
    model_config = ConfigDict(extra="forbid")

    site_id: str
    site_name: str
    country: str = "Unknown"
    lat: float | None = None
    lng: float | None = None
    elevation_m: float | None = None
    slope_deg: float | None = None
    ndvi: float | None = None
    spectral_signature: dict[str, Any] = Field(default_factory=dict)
    primary_rock: str | None = None
    temp_min_c: float | None = None
    temp_max_c: float | None = None
    temp_measurement_type: str = "unknown"
    accessibility_score: float | None = None
    is_subterranean: bool = False
    data_source: str = "unknown"
    feature_reports: list[FeatureReport] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Comparison result schemas
# ---------------------------------------------------------------------------

class DimensionResult(BaseModel):
    """Result of comparing one dimension (e.g., topography, climate).

    Attributes:
        dimension:  Name of the comparison dimension.
        score:  Similarity score (0-100) if computed, None if unavailable.
        status:  Whether the comparison could be computed.
        weight_requested:  Weight the caller asked for this dimension.
        weight_effective:  Weight actually used after renormalization.
        features_compared:  Features that contributed to this score.
        features_missing:  Features that were unavailable.
        methodology:  Brief description of calculation method.
        warnings:  Data-quality warnings for this dimension.
    """
    model_config = ConfigDict(extra="forbid")

    dimension: str
    score: float | None = None
    status: DimensionStatus = DimensionStatus.UNAVAILABLE
    weight_requested: float = 0.0
    weight_effective: float = 0.0
    features_compared: list[str] = Field(default_factory=list)
    features_missing: list[str] = Field(default_factory=list)
    methodology: str = ""
    warnings: list[str] = Field(default_factory=list)


class SimilarityResult(BaseModel):
    """Complete result of comparing a target against one Earth candidate."""
    model_config = ConfigDict(extra="forbid")

    target_site_id: str
    candidate_site_id: str
    candidate_site_name: str
    candidate_country: str = "Unknown"
    overall_score: float | None = None
    is_complete: bool = False
    dimensions: list[DimensionResult] = Field(default_factory=list)
    dimensions_computed: int = 0
    dimensions_unavailable: int = 0
    warnings: list[str] = Field(default_factory=list)
    methodology_summary: str = ""


class RankedCandidate(BaseModel):
    """A candidate with its rank position in the results."""
    model_config = ConfigDict(extra="forbid")

    rank: int
    similarity_result: SimilarityResult


class RankingResult(BaseModel):
    """Collection of ranked candidates with metadata."""
    model_config = ConfigDict(extra="forbid")

    target_site_id: str
    target_planet: Planet
    total_candidates_evaluated: int = 0
    candidates_above_threshold: int = 0
    threshold_applied: float | None = None
    ranked_candidates: list[RankedCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ComparisonWeights(BaseModel):
    """User-specified or default weights for each comparison dimension.

    Weights are non-negative, finite numbers.  They do not need to sum to 1.0;
    the engine normalises them internally.
    """
    model_config = ConfigDict(extra="forbid")

    topography: float = Field(default=0.40, ge=0.0)
    geochemistry: float = Field(default=0.35, ge=0.0)
    climate: float = Field(default=0.25, ge=0.0)

    @model_validator(mode="after")
    def validate_finite_weights(self) -> ComparisonWeights:
        for name in ("topography", "geochemistry", "climate"):
            val = getattr(self, name)
            if not math.isfinite(val):
                raise ValueError(f"Weight '{name}' must be a finite number.")
        return self

    def total(self) -> float:
        """Sum of all weights."""
        return self.topography + self.geochemistry + self.climate

    def normalized(self) -> dict[str, float]:
        """Return weights normalised to sum to 1.0.

        Raises:
            ValueError: If total is zero or non-positive.
        """
        t = self.total()
        if t <= 0:
            raise ValueError(
                "At least one weight must be greater than zero."
            )
        return {
            "topography": self.topography / t,
            "geochemistry": self.geochemistry / t,
            "climate": self.climate / t,
        }


class ExplanationBlock(BaseModel):
    """Structured explanation of a similarity result.

    Generated from actual calculation outputs, not from an LLM.
    """
    model_config = ConfigDict(extra="forbid")

    overall_summary: str
    overall_score: float | None = None
    is_complete: bool = False
    dimension_explanations: list[str] = Field(default_factory=list)
    strong_matches: list[str] = Field(default_factory=list)
    weak_matches: list[str] = Field(default_factory=list)
    unavailable_dimensions: list[str] = Field(default_factory=list)
    data_quality_warnings: list[str] = Field(default_factory=list)
    effective_weights: dict[str, float] = Field(default_factory=dict)
    methodology_notes: list[str] = Field(default_factory=list)


class SiteReport(BaseModel):
    """Structured site comparison report data."""
    model_config = ConfigDict(extra="forbid")

    report_title: str
    generated_at: str
    target_planet: str
    target_site_id: str
    target_site_name: str
    target_details: dict[str, Any] = Field(default_factory=dict)
    candidate_site_id: str
    candidate_site_name: str
    candidate_country: str = "Unknown"
    candidate_details: dict[str, Any] = Field(default_factory=dict)
    similarity_result: SimilarityResult
    explanation: ExplanationBlock
    scientific_limitations: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
    methodology_description: str = ""
