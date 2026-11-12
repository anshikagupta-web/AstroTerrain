from pydantic import BaseModel
from app.schemas.common import Coordinates
from app.schemas.search import Planet

class TargetSummary(BaseModel):
    planet: Planet
    site_id: str
    site_name: str
    coordinates: Coordinates
    avg_slope_deg: float | None = None
    elevation_m: float | None = None
    primary_rock: str | None = None
    temp_range_c: list[int] | None = None
    data_source: str

class TargetListResponse(BaseModel):
    count: int
    targets: list[TargetSummary]
