
from pathlib import Path
from math import hypot
from typing import Any

import numpy as np
import rasterio
from pyproj import CRS, Transformer


def process_dem(dem_path: str | Path) -> dict[str, Any]:
    """
    Process a DEM GeoTIFF and calculate elevation and terrain slope
    statistics. Coordinates are returned in WGS84.
    """

    with rasterio.open(dem_path) as dataset:
        if dataset.crs is None:
            raise ValueError("DEM must have a valid CRS.")

        if dataset.width < 2 or dataset.height < 2:
            raise ValueError("DEM must contain at least 2 rows and columns.")

        dem = dataset.read(1, masked=True).astype("float64")
        valid = dem.compressed()

        if valid.size == 0:
            raise ValueError("DEM contains no valid elevation values.")

        crs = CRS.from_user_input(dataset.crs)

        # Calculate the physical pixel spacing in metres.
        row = dataset.height / 2
        col = dataset.width / 2

        x0, y0 = dataset.transform * (col, row)
        x1, y1 = dataset.transform * (col + 1, row)
        x2, y2 = dataset.transform * (col, row + 1)


        if crs.is_geographic:
            geod = crs.get_geod()
            dx = abs(geod.inv(x0, y0, x1, y1)[2])
            dy = abs(geod.inv(x0, y0, x2, y2)[2])
        else:
            factor = crs.axis_info[0].unit_conversion_factor
            dx = hypot(x1 - x0, y1 - y0) * factor
            dy = hypot(x2 - x0, y2 - y0) * factor

        if dx <= 0 or dy <= 0:
            raise ValueError("Invalid DEM pixel dimensions.")


        # Calculate slope in degrees.
        values = dem.filled(np.nan)
        gradient_y, gradient_x = np.gradient(values, dy, dx)
        slope = np.degrees(
            np.arctan(np.hypot(gradient_x, gradient_y))
        )

        valid_slope = slope[np.isfinite(slope)]

        if valid_slope.size == 0:
            raise ValueError("Could not calculate terrain slope.")

        # Calculate raster centre coordinates.
        center_x, center_y = dataset.transform * (
            dataset.width / 2,
            dataset.height / 2,
        )

        transformer = Transformer.from_crs(
            crs, "EPSG:4326", always_xy=True
        )
        longitude, latitude = transformer.transform(center_x, center_y)

        return {
            "lat": float(latitude),
            "lng": float(longitude),
            "elevation_m": float(np.mean(valid)),
            "min_elevation_m": float(np.min(valid)),
            "max_elevation_m": float(np.max(valid)),
            "slope_deg": float(np.mean(valid_slope)),
            "valid_pixels": int(valid.size),
            "crs": str(crs),
            "source_file": Path(dem_path).name,
        }

def process_ndvi(
    red_path: str | Path,
    nir_path: str | Path,
) -> dict[str, Any]:
    """
    Calculate NDVI from aligned red and near-infrared GeoTIFF bands.

    Input bands should contain compatible reflectance values.
    """
    with rasterio.open(red_path) as red_ds, rasterio.open(nir_path) as nir_ds:

        if red_ds.crs is None or nir_ds.crs is None:
            raise ValueError("Both bands must have a valid CRS.")

        if (
            red_ds.crs != nir_ds.crs
            or red_ds.transform != nir_ds.transform
            or red_ds.width != nir_ds.width
            or red_ds.height != nir_ds.height
        ):
            raise ValueError(
                "Red and NIR bands must be aligned to the same grid."
            )

        red = red_ds.read(1, masked=True).astype("float64")
        nir = nir_ds.read(1, masked=True).astype("float64")

        red_data = np.asarray(red.filled(np.nan))
        nir_data = np.asarray(nir.filled(np.nan))

        denominator = nir_data + red_data

        valid = (
            ~np.ma.getmaskarray(red)
            & ~np.ma.getmaskarray(nir)
            & np.isfinite(red_data)
            & np.isfinite(nir_data)
            & (denominator != 0)
        )

        if not np.any(valid):
            raise ValueError("No valid pixels available for NDVI.")

        ndvi = np.full(red_data.shape, np.nan, dtype="float64")
        ndvi[valid] = (
            nir_data[valid] - red_data[valid]
        ) / denominator[valid]

        valid_ndvi = ndvi[valid]

        return {
            "mean_ndvi": float(np.mean(valid_ndvi)),
            "min_ndvi": float(np.min(valid_ndvi)),
            "max_ndvi": float(np.max(valid_ndvi)),
            "valid_pixels": int(valid.sum()),
            "source_red": Path(red_path).name,
            "source_nir": Path(nir_path).name,
        }
