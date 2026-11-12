from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db import repository
from app.db.session import get_db
from app.schemas.search import Planet
from app.schemas.targets import TargetListResponse, TargetSummary

router = APIRouter(prefix="/targets", tags=["targets"])

def _to_target(row: dict) -> TargetSummary:
    return TargetSummary(
        planet=row["planet"], site_id=row["site_id"], site_name=row["site_name"],
        coordinates={"lat": row["lat"], "lng": row["lng"]},
        avg_slope_deg=row.get("avg_slope_deg"), elevation_m=row.get("elevation_m"),
        primary_rock=row.get("primary_rock"), temp_range_c=row.get("temp_range_c"),
        data_source=row.get("data_source") or "unknown",
    )

@router.get("", response_model=TargetListResponse)
def get_targets(planet: Planet | None = Query(default=None), db: Session = Depends(get_db)):
    rows = repository.list_targets(db, planet)
    return TargetListResponse(count=len(rows), targets=[_to_target(row) for row in rows])

@router.get("/{site_id}", response_model=TargetSummary)
def get_target(site_id: str, planet: Planet = Query(...), db: Session = Depends(get_db)):
    row = repository.get_target(db, planet, site_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Target '{site_id}' was not found for planet '{planet}'.")
    return _to_target(row)
