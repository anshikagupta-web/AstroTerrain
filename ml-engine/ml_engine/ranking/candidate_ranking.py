"""Candidate ranking system for the AstroTerrain ML Engine.

Design decisions
----------------
* Sorted by ``overall_score`` descending.
* Ties broken deterministically by ``candidate_site_id`` ascending.
* Candidates with ``overall_score=None`` (unscored due to missing features)
  are placed at the end, sorted by ``candidate_site_id``.
* Configurable minimum threshold and result limit.
* When ``min_score`` is specified, unscored candidates and candidates below
  the threshold are excluded.
* When ``min_score`` is None, all candidates are returned with scored ones first.
* Empty candidate lists return an empty result (not an error).
"""
from __future__ import annotations

from ml_engine.models.schemas import (
    ComparisonWeights,
    EarthCandidate,
    PlanetaryTarget,
    RankedCandidate,
    RankingResult,
    SimilarityResult,
)
from ml_engine.comparison.similarity import calculate_weighted_similarity


def rank_candidates(
    target: PlanetaryTarget,
    candidates: list[EarthCandidate],
    weights: ComparisonWeights,
    min_score: float | None = None,
    limit: int | None = None,
) -> RankingResult:
    """Rank Earth candidates by similarity to a planetary target.

    Args:
        target: Validated planetary target profile.
        candidates: Validated Earth candidate profiles.
        weights: Comparison dimension weights.
        min_score: Minimum overall score to include (``None`` -> no filter).
            Candidates with ``score=None`` are always excluded when set.
        limit: Maximum number of results (``None`` -> no limit).

    Returns:
        ``RankingResult`` with ranked candidates and metadata.
    """
    warnings: list[str] = []

    if not candidates:
        return RankingResult(
            target_site_id=target.site_id,
            target_planet=target.planet,
            total_candidates_evaluated=0,
            candidates_above_threshold=0,
            threshold_applied=min_score,
            ranked_candidates=[],
            warnings=["No candidates provided for ranking."],
        )

    # Score all candidates
    results: list[SimilarityResult] = [
        calculate_weighted_similarity(target, c, weights) for c in candidates
    ]

    scored = [r for r in results if r.overall_score is not None]
    unscored = [r for r in results if r.overall_score is None]

    if unscored:
        warnings.append(
            f"{len(unscored)} candidate(s) could not be scored "
            f"(no computable dimensions)."
        )

    # Sort scored candidates: score descending, then candidate_site_id ascending
    scored.sort(
        key=lambda r: (
            -(r.overall_score if r.overall_score is not None else 0.0),
            r.candidate_site_id,
        ),
    )

    # Apply minimum threshold if provided
    if min_score is not None:
        above = [
            r for r in scored
            if r.overall_score is not None and r.overall_score >= min_score
        ]
        below = len(scored) - len(above)
        if below > 0:
            warnings.append(
                f"{below} candidate(s) scored below the "
                f"minimum threshold of {min_score}."
            )
        candidates_to_rank = above
        total_above = len(above)
    else:
        # No threshold: scored first (descending score), then unscored at the end
        unscored.sort(key=lambda r: r.candidate_site_id)
        candidates_to_rank = scored + unscored
        total_above = len(scored)

    # Apply limit if requested
    if limit is not None and limit > 0:
        candidates_to_rank = candidates_to_rank[:limit]

    ranked = [
        RankedCandidate(rank=i, similarity_result=r)
        for i, r in enumerate(candidates_to_rank, start=1)
    ]

    return RankingResult(
        target_site_id=target.site_id,
        target_planet=target.planet,
        total_candidates_evaluated=len(candidates),
        candidates_above_threshold=total_above,
        threshold_applied=min_score,
        ranked_candidates=ranked,
        warnings=warnings,
    )
