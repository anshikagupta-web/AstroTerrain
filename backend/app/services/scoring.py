"""Module 4 integration boundary. No placeholder scores are exposed as science."""

from typing import Protocol

from app.db.repository import AnalogRepository, TargetRecord
from app.schemas.search import AnalogSearchRequest, AnalogSiteResult


class ScoringEngine(Protocol):
    async def score(
        self,
        request: AnalogSearchRequest,
        target: TargetRecord,
        repository: AnalogRepository,
    ) -> list[AnalogSiteResult]:
        """Module 4 must return validated, evidence-based analog matches."""
        ...


def get_scoring_engine() -> ScoringEngine | None:
    # Module 4 supplies an implementation later. Tests override this dependency.
    return None
