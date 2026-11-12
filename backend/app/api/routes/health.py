from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.db.session import get_db

router = APIRouter(tags=["health"])

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        version = db.execute(text("SELECT PostGIS_Full_Version()")).scalar_one()
        return {"status": "ok", "service": "astroterrain-api", "database": "connected", "postgis_version": version}
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "service": "astroterrain-api", "database": "unavailable"},
        )
