
"""Connect raster processing with the PostGIS Earth-analog database."""

from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.repository import upsert_earth_analog
from app.services.ingestion import process_dem, process_ndvi


def ingest_raster_analog(
    db: Session,
    dem_path: str | Path,
    red_path: str | Path,
    nir_path: str | Path,
    site_id: str,
    site_name: str,
    country: str,
    primary_rock: str | None = None,
    temp_min_c: float | None = None,
    temp_max_c: float | None = None,
    accessibility_score: float | None = None,
    is_subterranean: bool = False,
    data_source: str = "synthetic_raster_test",
) -> dict[str, Any]:
    """Process DEM and spectral rasters and save their results to PostGIS."""

    try:
        dem = process_dem(dem_path)
        spectral = process_ndvi(red_path, nir_path)

        record = {
            "site_id": site_id,
            "site_name": site_name,
            "country": country,
            "lat": dem["lat"],
            "lng": dem["lng"],
            "elevation_m": dem["elevation_m"],
            "slope_deg": dem["slope_deg"],
            "ndvi": spectral["mean_ndvi"],
            "spectral_signature": {
                "mean_ndvi": spectral["mean_ndvi"],
                "min_ndvi": spectral["min_ndvi"],
                "max_ndvi": spectral["max_ndvi"],
                "valid_pixels": spectral["valid_pixels"],
            },
            "primary_rock": primary_rock,
            "temp_min_c": temp_min_c,
            "temp_max_c": temp_max_c,
            "accessibility_score": accessibility_score,
            "is_subterranean": is_subterranean,
            "data_source": data_source,
        }

        saved = upsert_earth_analog(db, record)
        db.commit()

        return {
            "status": "success",
            "site": saved,
            "dem": dem,
            "spectral": spectral,
        }

    except Exception:
        db.rollback()
        raise
