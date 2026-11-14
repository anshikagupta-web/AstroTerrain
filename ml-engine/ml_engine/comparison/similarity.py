"""Weighted multi-criteria similarity engine.

Aggregates dimension scores into an overall similarity using configurable
weights.

Missing-data policy (critical)
-------------------------------
1. **NEVER** silently assign 0, 50, or 100 to an unavailable dimension.
2. Exclude unavailable dimensions from aggregation.
3. Renormalise remaining valid weights to sum to 1.0.
4. Report which dimensions were unavailable.
5. Report the effective weights used.
6. Mark incomplete comparisons explicitly.
7. Return ``overall_score=None`` if **no** positively-weighted dimensions
   can be compared.

Formula:  ``S = Sum(w_i * S_i) / Sum(w_i)``  for available dimensions.
"""
from __future__ import annotations

from ml_engine.comparison.topography import compare_topography
from ml_engine.comparison.geochemistry import compare_geochemistry
from ml_engine.comparison.climate import compare_climate
from ml_engine.models.schemas import (
    ComparisonWeights,
    DimensionResult,
    DimensionStatus,
    EarthCandidate,
    PlanetaryTarget,
    SimilarityResult,
)


def calculate_weighted_similarity(
    target: PlanetaryTarget,
    candidate: EarthCandidate,
    weights: ComparisonWeights,
) -> SimilarityResult:
    """Calculate weighted multi-criteria similarity.

    This is the **main entry point** for the similarity engine.  It:

    1. Runs all three comparison dimensions.
    2. Applies the missing-data policy.
    3. Aggregates available scores using renormalised weights.
    4. Produces a fully explainable ``SimilarityResult``.
    """
    topo = compare_topography(target, candidate)
    geo = compare_geochemistry(target, candidate)
    clim = compare_climate(target, candidate)

    weight_map = {
        "topography": weights.topography,
        "geochemistry": weights.geochemistry,
        "climate": weights.climate,
    }

    dims: list[DimensionResult] = [topo, geo, clim]
    for d in dims:
        d.weight_requested = weight_map.get(d.dimension, 0.0)

    available: list[DimensionResult] = []
    unavailable: list[DimensionResult] = []

    for d in dims:
        if (
            d.status == DimensionStatus.COMPUTED
            and d.score is not None
            and d.weight_requested > 0
        ):
            available.append(d)
        else:
            if d.status != DimensionStatus.COMPUTED or d.score is None:
                unavailable.append(d)
            d.weight_effective = 0.0

    all_warnings: list[str] = []
    for d in dims:
        all_warnings.extend(d.warnings)

    n_computed = len(available)
    n_unavailable = len(unavailable)

    if not available:
        all_warnings.append(
            "No positively-weighted comparison dimensions could be "
            "computed. Overall similarity score cannot be determined."
        )
        return SimilarityResult(
            target_site_id=target.site_id,
            candidate_site_id=candidate.site_id,
            candidate_site_name=candidate.site_name,
            candidate_country=candidate.country,
            overall_score=None,
            is_complete=False,
            dimensions=dims,
            dimensions_computed=n_computed,
            dimensions_unavailable=n_unavailable,
            warnings=all_warnings,
            methodology_summary="No dimensions available for comparison.",
        )

    total_w = sum(d.weight_requested for d in available)
    if total_w <= 0:
        return SimilarityResult(
            target_site_id=target.site_id,
            candidate_site_id=candidate.site_id,
            candidate_site_name=candidate.site_name,
            candidate_country=candidate.country,
            overall_score=None,
            is_complete=False,
            dimensions=dims,
            dimensions_computed=n_computed,
            dimensions_unavailable=n_unavailable,
            warnings=all_warnings + ["Total available weight is zero."],
            methodology_summary="Cannot compute: zero total weight.",
        )

    for d in available:
        d.weight_effective = round(d.weight_requested / total_w, 6)

    overall = round(
        sum(d.score * d.weight_effective for d in available),  # type: ignore[operator]
        2,
    )

    is_complete = n_unavailable == 0 and all(
        d.weight_requested > 0 for d in dims
    )

    if not is_complete and unavailable:
        names = [
            d.dimension for d in unavailable if d.weight_requested > 0
        ]
        if names:
            all_warnings.append(
                f"Comparison is incomplete. Unavailable dimensions with "
                f"positive weight: {', '.join(names)}. "
                f"Weights were renormalised over {n_computed} available "
                f"dimension(s)."
            )

    desc_parts = []
    for d in available:
        desc_parts.append(
            f"{d.dimension}: score={d.score}, "
            f"w_eff={d.weight_effective:.4f} "
            f"(requested={d.weight_requested})"
        )
    methodology = (
        f"Weighted average of {n_computed} dimension(s). "
        + "; ".join(desc_parts)
        + f". Overall = {overall}."
    )

    return SimilarityResult(
        target_site_id=target.site_id,
        candidate_site_id=candidate.site_id,
        candidate_site_name=candidate.site_name,
        candidate_country=candidate.country,
        overall_score=overall,
        is_complete=is_complete,
        dimensions=dims,
        dimensions_computed=n_computed,
        dimensions_unavailable=n_unavailable,
        warnings=all_warnings,
        methodology_summary=methodology,
    )
