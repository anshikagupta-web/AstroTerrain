"""Site comparison report generation.

Provides:
1. Structured ``SiteReport`` data objects for programmatic consumption.
2. Plain-text rendering for display or file export.
3. Optional PDF generation (requires ``reportlab``).

All content is derived deterministically from ML Engine outputs.
No LLM is used.  Scientific limitations are always included.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ml_engine.explainability.explanations import generate_explanation
from ml_engine.models.schemas import (
    ExplanationBlock,
    PlanetaryTarget,
    EarthCandidate,
    SimilarityResult,
    SiteReport,
)

STANDARD_LIMITATIONS: list[str] = [
    "Similarity scores are based on available numerical features and "
    "may not capture all scientifically relevant characteristics.",
    "Geochemical comparison requires validated mineralogical data. "
    "NDVI (vegetation index) is not used as a mineralogy proxy.",
    "Temperature comparisons use reported ranges and may not reflect "
    "microclimatic variations.",
    "This analysis has not been validated against peer-reviewed planetary "
    "analogue studies. Results should be interpreted as preliminary.",
    "Synthetic test data, if present, does not represent actual "
    "scientific measurements.",
]


def generate_site_report(
    target: PlanetaryTarget,
    candidate: EarthCandidate,
    result: SimilarityResult,
    explanation: ExplanationBlock | None = None,
) -> SiteReport:
    """Generate a structured site comparison report."""
    if explanation is None:
        explanation = generate_explanation(result)

    target_details: dict[str, Any] = {
        "planet": target.planet.value,
        "site_id": target.site_id,
        "site_name": target.site_name,
        "coordinates": {"lat": target.lat, "lng": target.lng},
        "elevation_m": target.elevation_m,
        "avg_slope_deg": target.avg_slope_deg,
        "primary_rock": target.primary_rock,
        "data_source": target.data_source,
    }
    if target.temp_range_c is not None:
        target_details["temp_range_c"] = list(target.temp_range_c)

    candidate_details: dict[str, Any] = {
        "site_id": candidate.site_id,
        "site_name": candidate.site_name,
        "country": candidate.country,
        "coordinates": {"lat": candidate.lat, "lng": candidate.lng},
        "elevation_m": candidate.elevation_m,
        "slope_deg": candidate.slope_deg,
        "primary_rock": candidate.primary_rock,
        "temp_range_c": [candidate.temp_min_c, candidate.temp_max_c],
        "data_source": candidate.data_source,
    }

    data_sources: set[str] = set()
    if target.data_source and target.data_source != "unknown":
        data_sources.add(f"Target: {target.data_source}")
    if candidate.data_source and candidate.data_source != "unknown":
        data_sources.add(f"Candidate: {candidate.data_source}")

    methodology = (
        "Multi-criteria weighted similarity analysis using three "
        "comparison dimensions: topography (elevation, slope), "
        "geochemistry (mineral composition, rock type), and climate "
        "(temperature range overlap). Each dimension produces a score "
        "from 0 to 100. Dimensions that cannot be compared due to "
        "missing data are excluded and weights are renormalised."
    )

    return SiteReport(
        report_title=(
            f"AstroTerrain Site Comparison Report: "
            f"{target.site_name} vs {candidate.site_name}"
        ),
        generated_at=datetime.now(timezone.utc).isoformat(),
        target_planet=target.planet.value,
        target_site_id=target.site_id,
        target_site_name=target.site_name,
        target_details=target_details,
        candidate_site_id=candidate.site_id,
        candidate_site_name=candidate.site_name,
        candidate_country=candidate.country,
        candidate_details=candidate_details,
        similarity_result=result,
        explanation=explanation,
        scientific_limitations=STANDARD_LIMITATIONS,
        data_sources=sorted(data_sources),
        methodology_description=methodology,
    )


def render_report_text(report: SiteReport) -> str:
    """Render a ``SiteReport`` as formatted plain text."""
    lines: list[str] = []
    sep = "=" * 72
    thin = "-" * 72

    lines.append(sep)
    lines.append(f"  {report.report_title}")
    lines.append(sep)
    lines.append(f"  Generated: {report.generated_at}")
    lines.append("")

    lines.append(thin)
    lines.append("  PLANETARY TARGET")
    lines.append(thin)
    lines.append(f"  Planet:     {report.target_planet.upper()}")
    lines.append(f"  Site:       {report.target_site_name}")
    lines.append(f"  Site ID:    {report.target_site_id}")
    td = report.target_details
    if td.get("coordinates"):
        lines.append(
            f"  Location:   {td['coordinates'].get('lat')}, "
            f"{td['coordinates'].get('lng')}"
        )
    if td.get("elevation_m") is not None:
        lines.append(f"  Elevation:  {td['elevation_m']} m")
    if td.get("avg_slope_deg") is not None:
        lines.append(f"  Avg Slope:  {td['avg_slope_deg']} deg")
    if td.get("primary_rock"):
        lines.append(f"  Rock Type:  {td['primary_rock']}")
    if td.get("temp_range_c"):
        lines.append(f"  Temp Range: {td['temp_range_c']} deg C")
    lines.append("")

    lines.append(thin)
    lines.append("  EARTH CANDIDATE")
    lines.append(thin)
    lines.append(f"  Site:       {report.candidate_site_name}")
    lines.append(f"  Country:    {report.candidate_country}")
    cd = report.candidate_details
    if cd.get("coordinates"):
        lines.append(
            f"  Location:   {cd['coordinates'].get('lat')}, "
            f"{cd['coordinates'].get('lng')}"
        )
    if cd.get("elevation_m") is not None:
        lines.append(f"  Elevation:  {cd['elevation_m']} m")
    if cd.get("slope_deg") is not None:
        lines.append(f"  Slope:      {cd['slope_deg']} deg")
    if cd.get("primary_rock"):
        lines.append(f"  Rock Type:  {cd['primary_rock']}")
    if cd.get("temp_range_c"):
        lines.append(f"  Temp Range: {cd['temp_range_c']} deg C")
    lines.append("")

    lines.append(thin)
    lines.append("  SIMILARITY RESULTS")
    lines.append(thin)
    expl = report.explanation
    lines.append(f"  {expl.overall_summary}")
    lines.append("")

    if expl.dimension_explanations:
        lines.append("  Dimension Breakdown:")
        for de in expl.dimension_explanations:
            lines.append(f"    * {de}")
        lines.append("")

    if expl.strong_matches:
        lines.append("  Strong Matches:")
        for s in expl.strong_matches:
            lines.append(f"    + {s}")
        lines.append("")

    if expl.weak_matches:
        lines.append("  Weak Matches:")
        for w in expl.weak_matches:
            lines.append(f"    - {w}")
        lines.append("")

    if expl.unavailable_dimensions:
        lines.append("  Unavailable Dimensions:")
        for u in expl.unavailable_dimensions:
            lines.append(f"    ! {u}")
        lines.append("")

    if expl.data_quality_warnings:
        lines.append("  Data Quality Warnings:")
        for w in expl.data_quality_warnings:
            lines.append(f"    ! {w}")
        lines.append("")

    lines.append(thin)
    lines.append("  METHODOLOGY")
    lines.append(thin)
    lines.append(f"  {report.methodology_description}")
    lines.append("")
    if expl.methodology_notes:
        for mn in expl.methodology_notes:
            lines.append(f"    * {mn}")
        lines.append("")

    lines.append(thin)
    lines.append("  SCIENTIFIC LIMITATIONS")
    lines.append(thin)
    for lim in report.scientific_limitations:
        lines.append(f"    * {lim}")
    lines.append("")

    if report.data_sources:
        lines.append(thin)
        lines.append("  DATA SOURCES")
        lines.append(thin)
        for ds in report.data_sources:
            lines.append(f"    * {ds}")
        lines.append("")

    lines.append(sep)
    lines.append("  END OF REPORT")
    lines.append(sep)
    return "\n".join(lines)


def render_report_pdf(report: SiteReport, output_path: str) -> str:
    """Render a ``SiteReport`` as a PDF file.

    Requires the optional ``reportlab`` dependency.

    Raises:
        ImportError: If ``reportlab`` is not installed.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        )
        from reportlab.lib.units import mm
        from reportlab.lib import colors
    except ImportError:
        raise ImportError(
            "PDF report generation requires 'reportlab'. "
            "Install with: pip install reportlab"
        )

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=20 * mm, bottomMargin=20 * mm,
        leftMargin=15 * mm, rightMargin=15 * mm,
    )
    styles = getSampleStyleSheet()
    title_s = ParagraphStyle(
        "RTitle", parent=styles["Title"], fontSize=16, spaceAfter=12,
    )
    heading_s = ParagraphStyle(
        "RHead", parent=styles["Heading2"], fontSize=12,
        spaceAfter=6, spaceBefore=12,
    )
    body_s = styles["BodyText"]
    warn_s = ParagraphStyle(
        "RWarn", parent=body_s, textColor=colors.orangered,
    )

    elems: list = []
    elems.append(Paragraph(report.report_title, title_s))
    elems.append(Paragraph(f"Generated: {report.generated_at}", body_s))
    elems.append(Spacer(1, 6 * mm))

    # Target table
    elems.append(Paragraph("Planetary Target", heading_s))
    tdata = [
        ["Planet", report.target_planet.upper()],
        ["Site", report.target_site_name],
        ["Site ID", report.target_site_id],
    ]
    td = report.target_details
    if td.get("elevation_m") is not None:
        tdata.append(["Elevation", f"{td['elevation_m']} m"])
    if td.get("avg_slope_deg") is not None:
        tdata.append(["Avg Slope", f"{td['avg_slope_deg']} deg"])
    if td.get("primary_rock"):
        tdata.append(["Rock Type", str(td["primary_rock"])])
    t = Table(tdata, colWidths=[40 * mm, 120 * mm])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.Color(0.9, 0.9, 0.95)),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    elems.append(t)
    elems.append(Spacer(1, 4 * mm))

    # Candidate table
    elems.append(Paragraph("Earth Candidate", heading_s))
    cdata = [
        ["Site", report.candidate_site_name],
        ["Country", report.candidate_country],
    ]
    cd = report.candidate_details
    if cd.get("elevation_m") is not None:
        cdata.append(["Elevation", f"{cd['elevation_m']} m"])
    if cd.get("slope_deg") is not None:
        cdata.append(["Slope", f"{cd['slope_deg']} deg"])
    if cd.get("primary_rock"):
        cdata.append(["Rock Type", str(cd["primary_rock"])])
    t2 = Table(cdata, colWidths=[40 * mm, 120 * mm])
    t2.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.Color(0.9, 0.95, 0.9)),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    elems.append(t2)
    elems.append(Spacer(1, 4 * mm))

    # Results
    expl = report.explanation
    elems.append(Paragraph("Similarity Results", heading_s))
    elems.append(Paragraph(expl.overall_summary, body_s))
    elems.append(Spacer(1, 2 * mm))
    for de in expl.dimension_explanations:
        elems.append(Paragraph(f"* {de}", body_s))
    if expl.unavailable_dimensions:
        elems.append(Spacer(1, 2 * mm))
        for ud in expl.unavailable_dimensions:
            elems.append(Paragraph(f"! {ud}", warn_s))
    if expl.data_quality_warnings:
        elems.append(Spacer(1, 2 * mm))
        elems.append(Paragraph("Data Quality Warnings:", heading_s))
        for w in expl.data_quality_warnings:
            elems.append(Paragraph(f"! {w}", warn_s))

    # Limitations
    elems.append(Paragraph("Scientific Limitations", heading_s))
    for lim in report.scientific_limitations:
        elems.append(Paragraph(f"* {lim}", body_s))

    doc.build(elems)
    return output_path
