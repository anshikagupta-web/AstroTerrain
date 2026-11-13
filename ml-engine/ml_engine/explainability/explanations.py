"""Explanation generation for similarity results.

Generates structured, human-readable explanations from actual ML Engine
outputs.  These are **deterministic descriptions** -- no LLM is used.

Thresholds:
    * Strong match: >= 70.0
    * Moderate match: 40.0 - 70.0
    * Weak match: < 40.0
"""
from __future__ import annotations

from ml_engine.models.schemas import (
    DimensionStatus,
    ExplanationBlock,
    SimilarityResult,
)

STRONG_THRESHOLD = 70.0
MODERATE_THRESHOLD = 40.0


def generate_explanation(result: SimilarityResult) -> ExplanationBlock:
    """Generate a structured explanation for a ``SimilarityResult``.

    Built entirely from the calculation data -- no external API calls.
    """
    strong: list[str] = []
    weak: list[str] = []
    dim_explanations: list[str] = []
    unavailable: list[str] = []
    eff_weights: dict[str, float] = {}
    method_notes: list[str] = []

    for d in result.dimensions:
        if d.status == DimensionStatus.COMPUTED and d.score is not None:
            eff_weights[d.dimension] = d.weight_effective

            if d.score >= STRONG_THRESHOLD:
                quality = "strong"
                strong.append(
                    f"{d.dimension.capitalize()} similarity is strong "
                    f"({d.score:.1f}/100)."
                )
            elif d.score >= MODERATE_THRESHOLD:
                quality = "moderate"
            else:
                quality = "weak"
                weak.append(
                    f"{d.dimension.capitalize()} similarity is weak "
                    f"({d.score:.1f}/100)."
                )

            explanation = (
                f"{d.dimension.capitalize()}: {d.score:.1f}/100 ({quality}). "
                f"Weight: {d.weight_effective:.2%} "
                f"(requested: {d.weight_requested:.2f})."
            )
            if d.features_compared:
                explanation += (
                    f" Features compared: {', '.join(d.features_compared)}."
                )
            if d.features_missing:
                explanation += (
                    f" Features unavailable: "
                    f"{', '.join(d.features_missing)}."
                )
            dim_explanations.append(explanation)

            if d.methodology:
                method_notes.append(
                    f"{d.dimension.capitalize()}: {d.methodology}"
                )

        elif d.status == DimensionStatus.UNAVAILABLE:
            msg = f"{d.dimension.capitalize()} comparison was unavailable"
            msg += f": {d.methodology}" if d.methodology else "."
            unavailable.append(msg)
            if d.methodology:
                method_notes.append(
                    f"{d.dimension.capitalize()} (unavailable): "
                    f"{d.methodology}"
                )

    # Overall summary
    if result.overall_score is not None:
        comp = "complete" if result.is_complete else "partial"
        total = result.dimensions_computed + result.dimensions_unavailable
        summary = (
            f"Overall similarity: {result.overall_score:.1f}/100 "
            f"({comp} comparison, "
            f"{result.dimensions_computed} of {total} dimensions computed)."
        )
    else:
        summary = (
            "Overall similarity could not be determined because no "
            "comparison dimensions were available."
        )

    return ExplanationBlock(
        overall_summary=summary,
        overall_score=result.overall_score,
        is_complete=result.is_complete,
        dimension_explanations=dim_explanations,
        strong_matches=strong,
        weak_matches=weak,
        unavailable_dimensions=unavailable,
        data_quality_warnings=result.warnings,
        effective_weights=eff_weights,
        methodology_notes=method_notes,
    )
