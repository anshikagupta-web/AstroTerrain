import json
from typing import Any
from sqlalchemy import text
from sqlalchemy.orm import Session

def get_target(db: Session, planet: str, site_id: str) -> dict[str, Any] | None:
    q = text("""
        SELECT planet, site_id, site_name, ST_Y(geom) AS lat, ST_X(geom) AS lng,
               avg_slope_deg, elevation_m, regolith_composition, primary_rock,
               temp_range_c, data_source
        FROM planetary_targets WHERE planet=:planet AND site_id=:site_id LIMIT 1
    """)
    row = db.execute(q, {"planet": planet, "site_id": site_id}).mappings().first()
    return dict(row) if row else None

def list_targets(db: Session, planet: str | None = None) -> list[dict[str, Any]]:
    q = text("""
        SELECT planet, site_id, site_name, ST_Y(geom) AS lat, ST_X(geom) AS lng,
               avg_slope_deg, elevation_m, primary_rock, temp_range_c, data_source
        FROM planetary_targets WHERE (CAST(:planet AS text) IS NULL OR planet=:planet)
        ORDER BY planet, site_name
    """)
    return [dict(row) for row in db.execute(q, {"planet": planet}).mappings().all()]

def list_earth_analogs(db: Session, subterranean_only: bool) -> list[dict[str, Any]]:
    q = text("""
        SELECT site_id, site_name, country, ST_Y(geom) AS lat, ST_X(geom) AS lng,
               elevation_m, slope_deg, spectral_signature, primary_rock,
               temp_min_c, temp_max_c, accessibility_score, is_subterranean, data_source
        FROM earth_analog_tiles
        WHERE is_active=TRUE AND (:subterranean_only=FALSE OR is_subterranean=TRUE)
        ORDER BY site_name
    """)
    return [dict(row) for row in db.execute(q, {"subterranean_only": subterranean_only}).mappings().all()]

def upsert_earth_analog(db: Session, record: dict[str, Any]) -> dict[str, Any]:
    """Insert or update an Earth analog record in PostGIS."""

    query = text("""
        INSERT INTO earth_analog_tiles (
            site_id, site_name, country, geom,
            elevation_m, slope_deg, ndvi, spectral_signature,
            primary_rock, temp_min_c, temp_max_c,
            accessibility_score, is_subterranean, data_source
        )
        VALUES (
            :site_id, :site_name, :country,
            ST_SetSRID(ST_MakePoint(:lng, :lat), 4326),
            :elevation_m, :slope_deg, :ndvi,
            CAST(:spectral_signature AS JSONB),
            :primary_rock, :temp_min_c, :temp_max_c,
            :accessibility_score, :is_subterranean, :data_source
        )
        ON CONFLICT (site_id) DO UPDATE SET
            site_name = EXCLUDED.site_name,
            country = EXCLUDED.country,
            geom = EXCLUDED.geom,
            elevation_m = EXCLUDED.elevation_m,
            slope_deg = EXCLUDED.slope_deg,
            ndvi = EXCLUDED.ndvi,
            spectral_signature = EXCLUDED.spectral_signature,
            primary_rock = EXCLUDED.primary_rock,
            temp_min_c = EXCLUDED.temp_min_c,
            temp_max_c = EXCLUDED.temp_max_c,
            accessibility_score = EXCLUDED.accessibility_score,
            is_subterranean = EXCLUDED.is_subterranean,
            data_source = EXCLUDED.data_source,
            is_active = TRUE,
            updated_at = NOW()
        RETURNING site_id, site_name, ST_Y(geom) AS lat,
                  ST_X(geom) AS lng, data_source
    """)

    params = {
        **record,
        "spectral_signature": json.dumps(
            record.get("spectral_signature") or {}
        ),
    }

    result = db.execute(query, params).mappings().one()
    return dict(result)
