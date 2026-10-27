from typing import Annotated

from fastapi import APIRouter, Depends

from app.db.repository import AnalogRepository, get_repository

router = APIRouter(prefix="/api/v1", tags=["targets"])


@router.get("/targets")
async def list_targets(
    repository: Annotated[AnalogRepository, Depends(get_repository)],
) -> list[dict[str, str]]:
    return await repository.list_targets()
