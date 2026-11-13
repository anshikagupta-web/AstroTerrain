"""Tests for the reporting module."""
from __future__ import annotations

from ml_engine.models.schemas import (
    ComparisonWeights,
    EarthCandidate,
    Planet,
    PlanetaryTarget,
)
from ml_engine.comparison.similarity import calculate_weighted_similarity
from ml_engine.explainability.explanations import generate_explanation
from ml_engine.reporting.site_reports import generate_site_report, render_report_text


def _make_target(**kw) -> PlanetaryTarget:
    defaults = dict(
        planet=Planet.MOON, site_id="syn-t", site_name="Syn Target",
        elevation_m=-4000.0, avg_slope_deg=12.5,
        primary_rock="basalt", temp_range_c=(-80.0, 20.0),
        data_source="synthetic_test",
    )
    defaults.update(kw)
    return PlanetaryTarget(**defaults)


def _make_candidate(**kw) -> EarthCandidate:
    defaults = dict(
        site_id="syn-c", site_name="Syn Candidate", country="DEMO",
        elevation_m=2300.0, slope_deg=11.0,
        primary_rock="basalt", temp_min_c=-15.0, temp_max_c=35.0,
        data_source="synthetic_test",
    )
    defaults.update(kw)
    return EarthCandidate(**defaults)


class TestReportGeneration:
    def test_generates_report(self):
        t = _make_target()
        c = _make_candidate()
        result = calculate_weighted_similarity(t, c, ComparisonWeights())
        report = generate_site_report(t, c, result)
        assert report.report_title
        assert report.target_site_id == t.site_id
        assert report.candidate_site_id == c.site_id
        assert len(report.scientific_limitations) > 0

    def test_report_has_methodology(self):
        t = _make_target()
        c = _make_candidate()
        result = calculate_weighted_similarity(t, c, ComparisonWeights())
        report = generate_site_report(t, c, result)
        assert report.methodology_description
        assert "similarity" in report.methodology_description.lower()

    def test_report_with_pregenerated_explanation(self):
        t = _make_target()
        c = _make_candidate()
        result = calculate_weighted_similarity(t, c, ComparisonWeights())
        expl = generate_explanation(result)
        report = generate_site_report(t, c, result, explanation=expl)
        assert report.explanation.overall_summary == expl.overall_summary


class TestTextRendering:
    def test_renders_text(self):
        t = _make_target()
        c = _make_candidate()
        result = calculate_weighted_similarity(t, c, ComparisonWeights())
        report = generate_site_report(t, c, result)
        text = render_report_text(report)
        assert isinstance(text, str)
        assert len(text) > 100
        assert "PLANETARY TARGET" in text
        assert "EARTH CANDIDATE" in text
        assert "SIMILARITY RESULTS" in text
        assert "SCIENTIFIC LIMITATIONS" in text

    def test_contains_scores(self):
        t = _make_target()
        c = _make_candidate()
        result = calculate_weighted_similarity(t, c, ComparisonWeights())
        report = generate_site_report(t, c, result)
        text = render_report_text(report)
        assert "Overall similarity" in text

    def test_unavailable_dims_noted(self):
        t = _make_target(temp_range_c=None)
        c = _make_candidate(temp_min_c=None)
        result = calculate_weighted_similarity(t, c, ComparisonWeights())
        report = generate_site_report(t, c, result)
        text = render_report_text(report)
        assert "Unavailable" in text or "unavailable" in text
