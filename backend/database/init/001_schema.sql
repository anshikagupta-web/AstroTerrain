CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS planetary_targets (
    id BIGSERIAL PRIMARY KEY,
    planet VARCHAR(16) NOT NULL CHECK (planet IN ('moon', 'mars')),
    site_id VARCHAR(100) NOT NULL,
    site_name TEXT NOT NULL,
    geom geometry(Point, 4326) NOT NULL,
    avg_slope_deg DOUBLE PRECISION,
    elevation_m DOUBLE PRECISION,
    regolith_composition JSONB NOT NULL DEFAULT '{}'::jsonb,
    primary_rock TEXT,
    temp_range_c INTEGER[],
    data_source TEXT NOT NULL DEFAULT 'unknown',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_planetary_targets_planet_site UNIQUE (planet, site_id)
);

CREATE TABLE IF NOT EXISTS earth_analog_tiles (
    id BIGSERIAL PRIMARY KEY,
    site_id VARCHAR(100) NOT NULL UNIQUE,
    site_name TEXT NOT NULL,
    country TEXT,
    geom geometry(Point, 4326) NOT NULL,
    elevation_m DOUBLE PRECISION,
    slope_deg DOUBLE PRECISION,
    ndvi DOUBLE PRECISION,
    spectral_signature JSONB NOT NULL DEFAULT '{}'::jsonb,
    primary_rock TEXT,
    temp_min_c DOUBLE PRECISION,
    temp_max_c DOUBLE PRECISION,
    accessibility_score DOUBLE PRECISION CHECK (accessibility_score IS NULL OR accessibility_score BETWEEN 0 AND 100),
    is_subterranean BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    data_source TEXT NOT NULL DEFAULT 'unknown',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_earth_analog_temperature CHECK (temp_min_c IS NULL OR temp_max_c IS NULL OR temp_min_c <= temp_max_c)
);

CREATE INDEX IF NOT EXISTS idx_planetary_targets_geom ON planetary_targets USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_earth_analog_tiles_geom ON earth_analog_tiles USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_planetary_targets_planet ON planetary_targets (planet);
CREATE INDEX IF NOT EXISTS idx_earth_analog_tiles_active ON earth_analog_tiles (is_active);
CREATE INDEX IF NOT EXISTS idx_earth_analog_tiles_subterranean ON earth_analog_tiles (is_subterranean);
