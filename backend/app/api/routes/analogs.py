from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import repository
from app.db.session import get_db
from app.schemas.common import Coordinates
from app.schemas.search import AnalogMetadata, AnalogResult, AnalogSearchRequest, AnalogSearchResponse, SimilarityBreakdown
from app.services.scoring import accessibility_rating, score_analog

router = APIRouter(prefix="/analogs", tags=["analogs"])

@router.post("/search", response_model=AnalogSearchResponse)
def search_analogs(payload: AnalogSearchRequest, db: Session = Depends(get_db)):
    target = repository.get_target(db, payload.target_planet, payload.target_site_id)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Target '{payload.target_site_id}' was not found for planet '{payload.target_planet}'.")
    candidates = repository.list_earth_analogs(db, payload.constraints.subterranean_only)
    weights = payload.weights.model_dump()
    ranked = []
    for candidate in candidates:
        scored = score_analog(target, candidate, weights)
        if scored["similarity_score"] < payload.constraints.min_similarity:
            continue
        result = AnalogResult(
            site_id=candidate["site_id"], name=candidate["site_name"],
            country=candidate.get("country") or "Unknown",
            coordinates=Coordinates(lat=candidate["lat"], lng=candidate["lng"]),
            similarity_score=scored["similarity_score"],
            breakdown=SimilarityBreakdown(**scored["breakdown"]),
            metadata=AnalogMetadata(
                elevation_m=candidate.get("elevation_m"), primary_rock=candidate.get("primary_rock"),
                accessibility_rating=accessibility_rating(candidate.get("accessibility_score")),
            ),
        )
        ranked.append(result)
    ranked.sort(key=lambda item: item.similarity_score, reverse=True)
    results = ranked[:payload.constraints.limit]
    return AnalogSearchResponse(target_site_name=target["site_name"], results_count=len(results), analogs=results)
