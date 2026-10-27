"""ORM mirrors database/init/001_schema.sql; SQL is the setup source of truth."""

from geoalchemy2 import Geometry
from sqlalchemy import ARRAY, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PlanetaryTarget(Base):
    __tablename__ = "planetary_targets"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    body: Mapped[str] = mapped_column(String(20), nullable=False)
    # This Earth CRS is retained from the provided SQL contract, but lunar/Mars
    # coordinates must not be stored as WGS84 Earth coordinates. Keep NULL for now.
    location = mapped_column(Geometry("POINT", srid=4326, spatial_index=False), nullable=True)
    avg_slope = mapped_column(Numeric, nullable=True)
    regolith_composition = mapped_column(JSONB, nullable=True)
    temp_range_k = mapped_column(ARRAY(Integer), nullable=True)


class EarthAnalogTile(Base):
    __tablename__ = "earth_analog_tiles"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    site_name: Mapped[str] = mapped_column(String(100), nullable=False)
    country = mapped_column(String(50), nullable=True)
    location = mapped_column(Geometry("POINT", srid=4326, spatial_index=False), nullable=True)
    elevation_m = mapped_column(Numeric, nullable=True)
    slope_degrees = mapped_column(Numeric, nullable=True)
    ndvi_index = mapped_column(Numeric, nullable=True)
    spectral_signature = mapped_column(JSONB, nullable=True)
    temperature_min_c = mapped_column(Numeric, nullable=True)
    temperature_max_c = mapped_column(Numeric, nullable=True)
    accessibility_score = mapped_column(String(20), nullable=True)
