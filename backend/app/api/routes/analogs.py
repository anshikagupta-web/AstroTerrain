import sys
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import repository
from app.db.session import get_db
from app.schemas.common import Coordinates
from app.schemas.search import AnalogMetadata, AnalogResult, AnalogSearchRequest, AnalogSearchResponse, SimilarityBreakdown

# Ensure ml_engine is discoverable from workspace if not pip-installed
_ml_engine_path = Path(__file__).resolve().parents[4] / "ml-engine"
if _ml_engine_path.exists() and str(_ml_engine_path) not in sys.path:
    sys.path.insert(0, str(_ml_engine_path))

try:
    from ml_engine.adapter import accessibility_rating, score_analog
except ImportError:
    # Graceful fallback to legacy scoring if ml_engine package is unavailable
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
        ml_meta = scored.get("ml_engine_metadata") or {}
        result = AnalogResult(
            site_id=candidate["site_id"], name=candidate["site_name"],
            country=candidate.get("country") or "Unknown",
            coordinates=Coordinates(lat=candidate["lat"], lng=candidate["lng"]),
            similarity_score=scored["similarity_score"],
            breakdown=SimilarityBreakdown(**scored["breakdown"]),
            metadata=AnalogMetadata(
                elevation_m=candidate.get("elevation_m"), primary_rock=candidate.get("primary_rock"),
                accessibility_rating=accessibility_rating(candidate.get("accessibility_score")),
                data_source=candidate.get("data_source"),
                unavailable_dimensions=ml_meta.get("unavailable_dimensions", []),
                warnings=ml_meta.get("warnings", []),
                is_complete=ml_meta.get("is_complete", True),
            ),
            ml_engine_metadata=ml_meta if ml_meta else None,
        )
        ranked.append(result)
    # Deterministic ranking: sort by descending similarity_score, then site_id for stable tie-breaking
    ranked.sort(key=lambda item: (-item.similarity_score, item.site_id))
    results = ranked[:payload.constraints.limit]
    return AnalogSearchResponse(target_site_name=target["site_name"], results_count=len(results), analogs=results)
