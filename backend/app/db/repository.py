"""Database access layer: parameterized SQL; no scientific scoring here."""

import json
from dataclasses import dataclass
from typing import Any

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session


@dataclass(frozen=True)
class TargetRecord:
    id: str
    name: str
    body: str


class AnalogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_target(self, target_id: str) -> TargetRecord | None:
        result = await self.session.execute(
            text("SELECT id, name, body FROM planetary_targets WHERE id = :id"),
            {"id": target_id},
        )
        row = result.mappings().first()
        return TargetRecord(**row) if row else None

    async def list_targets(self) -> list[dict[str, str]]:
        result = await self.session.execute(
            text("SELECT id, name, body FROM planetary_targets ORDER BY body, name")
        )
        return [dict(row) for row in result.mappings().all()]

    async def has_earth_tiles(self) -> bool:
        result = await self.session.execute(
            text("SELECT EXISTS (SELECT 1 FROM earth_analog_tiles) AS has_tiles")
        )
        return bool(result.scalar_one())

    async def earth_geojson(self, limit: int) -> dict[str, Any]:
        result = await self.session.execute(
            text(
                "SELECT id, site_name, country, ST_AsGeoJSON(location) AS geom "
                "FROM earth_analog_tiles WHERE location IS NOT NULL "
                "ORDER BY id LIMIT :limit"
            ),
            {"limit": limit},
        )
        features = []
        for row in result.mappings().all():
            features.append(
                {
                    "type": "Feature",
                    "id": row["id"],
                    "geometry": json.loads(row["geom"]),
                    "properties": {"site_id": row["id"], "name": row["site_name"], "country": row["country"]},
                }
            )
        return {"type": "FeatureCollection", "features": features}


async def get_repository(session: AsyncSession = Depends(get_session)) -> AnalogRepository:
    return AnalogRepository(session)
