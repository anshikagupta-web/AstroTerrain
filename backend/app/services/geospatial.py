"""Small GIS helpers used by the future DEM/spectral ingestion pipeline.

These helpers do not download NASA/ESA data. They read files that the team has
already acquired and validate/standardize them for downstream processing.
"""
from pathlib import Path
from typing import Any


def validate_lon_lat(lon: float, lat: float) -> None:
    if not -180 <= lon <= 180:
        raise ValueError("Longitude must be between -180 and 180 degrees.")
    if not -90 <= lat <= 90:
        raise ValueError("Latitude must be between -90 and 90 degrees.")


def sample_raster_at_lon_lat(raster_path: str | Path, lon: float, lat: float, band: int = 1) -> float | None:
    """Sample one raster band at WGS84 lon/lat; return None for NoData/outside."""
    validate_lon_lat(lon, lat)
    import numpy as np
    import rasterio
    from pyproj import Transformer

    with rasterio.open(raster_path) as dataset:
        if dataset.crs is None:
            raise ValueError("Raster has no CRS; assign/repair its coordinate reference system first.")
        if band < 1 or band > dataset.count:
            raise ValueError(f"Band must be between 1 and {dataset.count}.")
        transformer = Transformer.from_crs("EPSG:4326", dataset.crs, always_xy=True)
        x, y = transformer.transform(lon, lat)
        sample = next(dataset.sample([(x, y)], indexes=band, masked=True))
        value = sample[0]
        if np.ma.is_masked(value):
            return None
        return float(value)


def read_vector_as_geojson(vector_path: str | Path) -> dict[str, Any]:
    """Read a vector dataset and return a GeoJSON FeatureCollection in EPSG:4326."""
    import geopandas as gpd
    import json

    frame = gpd.read_file(vector_path)
    if frame.crs is None:
        raise ValueError("Vector dataset has no CRS; assign/repair it before reprojection.")
    frame = frame.to_crs("EPSG:4326")
    return json.loads(frame.to_json())
