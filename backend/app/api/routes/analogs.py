from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.repository import AnalogRepository, get_repository
from app.schemas.search import AnalogSearchRequest, AnalogSearchResponse, AnalogSiteResult
from app.services.scoring import ScoringEngine, get_scoring_engine

router = APIRouter(prefix="/api/v1/analogs", tags=["analogs"])


@router.post("/search", response_model=AnalogSearchResponse)
async def search_analogs(
    payload: AnalogSearchRequest,
    repository: Annotated[AnalogRepository, Depends(get_repository)],
    scorer: Annotated[ScoringEngine | None, Depends(get_scoring_engine)],
) -> AnalogSearchResponse:
    target = await repository.get_target(payload.target_site_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Unknown planetary target site")
    if target.body != payload.target_planet:
        raise HTTPException(status_code=400, detail="Target site does not belong to target_planet")

    constraints = payload.constraints
    if constraints and constraints.subterranean_only:
        # The current earth_analog_tiles table has no subsurface annotation.
        # Do not silently ignore a constraint or pretend results satisfy it.
        raise HTTPException(status_code=501, detail="Subterranean filtering is not implemented yet")

    if not await repository.has_earth_tiles():
        return AnalogSearchResponse(
            status="success", target_site_name=target.name, results_count=0, analogs=[]
        )

    if scorer is None:
        raise HTTPException(
            status_code=503,
            detail="Earth tiles exist, but Module 4 scoring is not connected yet",
        )

    raw_analogs = await scorer.score(payload, target, repository)
    analogs = [AnalogSiteResult.model_validate(item) for item in raw_analogs]
    cutoff = constraints.min_similarity if constraints else 50.0
    analogs = sorted(
        [analog for analog in analogs if analog.similarity_score >= cutoff],
        key=lambda analog: analog.similarity_score,
        reverse=True,
    )
    return AnalogSearchResponse(
        status="success",
        target_site_name=target.name,
        results_count=len(analogs),
        analogs=analogs,
    )


@router.get("/geojson")
async def earth_tiles_geojson(
    repository: Annotated[AnalogRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=5000)] = 250,
) -> dict[str, Any]:
    """Earth-only EPSG:4326 point FeatureCollection for the 3D globe."""
    return await repository.earth_geojson(limit)
