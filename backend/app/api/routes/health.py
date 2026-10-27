from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def live() -> dict[str, str]:
    """Liveness: confirms the HTTP server responds, not database connectivity."""
    return {"status": "ok"}


@router.get("/health/db")
async def database_health(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    try:
        result = await session.execute(text("SELECT PostGIS_Version()"))
        version = str(result.scalar_one())
    except Exception as exc:
        # Do not leak DB credentials or internal exception text to callers.
        raise HTTPException(status_code=503, detail="Database/PostGIS not ready") from exc
    return {"status": "ok", "postgis_version": version}
