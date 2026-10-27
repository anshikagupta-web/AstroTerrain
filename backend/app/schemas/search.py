"""Stable public Module 1/2/4 search contract. Avoid breaking field changes."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SearchWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topography: float = Field(ge=0, le=1)
    geochemistry: float = Field(ge=0, le=1)
    climate: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def require_a_positive_weight(self):
        if self.topography + self.geochemistry + self.climate <= 0:
            raise ValueError("At least one search weight must be positive")
        # Sliders can vary independently; Module 4 can normalize their sum.
        return self


class SearchConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subterranean_only: bool = False
    min_similarity: float = Field(default=50.0, ge=0, le=100)


class AnalogSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_planet: Literal["moon", "mars"]
    target_site_id: str = Field(min_length=1, max_length=50)
    weights: SearchWeights
    constraints: SearchConstraints | None = None


class Coordinates(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class MatchBreakdown(BaseModel):
    topography_match: float = Field(ge=0, le=100)
    geochemistry_match: float = Field(ge=0, le=100)
    climate_match: float = Field(ge=0, le=100)


class SiteMetadata(BaseModel):
    elevation_m: float
    primary_rock: str
    accessibility_rating: str


class AnalogSiteResult(BaseModel):
    site_id: str
    name: str
    country: str
    coordinates: Coordinates
    similarity_score: float = Field(ge=0, le=100)
    breakdown: MatchBreakdown
    metadata: SiteMetadata


class AnalogSearchResponse(BaseModel):
    status: str
    target_site_name: str
    results_count: int = Field(ge=0)
    analogs: list[AnalogSiteResult]
