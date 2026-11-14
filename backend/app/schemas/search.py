from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.common import Coordinates

Planet = Literal["moon", "mars"]

class SearchWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topography: float = Field(default=0.40, ge=0, le=1)
    geochemistry: float = Field(default=0.35, ge=0, le=1)
    climate: float = Field(default=0.25, ge=0, le=1)

    @model_validator(mode="after")
    def nonzero_weights(self):
        if self.topography + self.geochemistry + self.climate <= 0:
            raise ValueError("At least one similarity weight must be greater than zero.")
        return self

class SearchConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subterranean_only: bool = False
    min_similarity: float = Field(default=50.0, ge=0, le=100)
    limit: int = Field(default=20, ge=1, le=100)

class AnalogSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_planet: Planet
    target_site_id: str = Field(min_length=1, max_length=100)
    weights: SearchWeights = Field(default_factory=SearchWeights)
    constraints: SearchConstraints = Field(default_factory=SearchConstraints)

class SimilarityBreakdown(BaseModel):
    topography_match: float
    geochemistry_match: float
    climate_match: float

class AnalogMetadata(BaseModel):
    elevation_m: float | None = None
    primary_rock: str | None = None
    accessibility_rating: str
    data_source: str | None = None
    unavailable_dimensions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    is_complete: bool = True

class AnalogResult(BaseModel):
    site_id: str
    name: str
    country: str
    coordinates: Coordinates
    similarity_score: float
    breakdown: SimilarityBreakdown
    metadata: AnalogMetadata
    ml_engine_metadata: dict[str, Any] | None = None

class AnalogSearchResponse(BaseModel):
    status: Literal["success"] = "success"
    target_site_name: str
    results_count: int
    analogs: list[AnalogResult]
