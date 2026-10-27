-- This script runs exactly once for a NEW postgres_data volume.
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS planetary_targets (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    body VARCHAR(20) NOT NULL CHECK (body IN ('moon', 'mars')),
    location GEOMETRY(Point, 4326),
    avg_slope NUMERIC,
    regolith_composition JSONB,
    temp_range_k INT[]
);

CREATE TABLE IF NOT EXISTS earth_analog_tiles (
    id VARCHAR(50) PRIMARY KEY,
    site_name VARCHAR(100) NOT NULL,
    country VARCHAR(50),
    location GEOMETRY(Point, 4326),
    elevation_m NUMERIC,
    slope_degrees NUMERIC,
    ndvi_index NUMERIC,
    spectral_signature JSONB,
    temperature_min_c NUMERIC,
    temperature_max_c NUMERIC,
    accessibility_score VARCHAR(20)
);

CREATE INDEX IF NOT EXISTS idx_earth_tiles_location
    ON earth_analog_tiles USING GIST(location);
