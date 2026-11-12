from app.services.scoring import accessibility_rating, climate_match, geochemistry_match, score_analog, topography_match

def test_topography_exact_match_is_100():
    assert topography_match({"avg_slope_deg": 10}, {"slope_deg": 10}) == 100.0

def test_geochemistry_similarity():
    a = {"regolith_composition": {"basalt_pct": 40, "silica_pct": 20}}
    b = {"spectral_signature": {"basalt_pct": 40, "silica_pct": 30}}
    assert geochemistry_match(a, b) == 95.0

def test_climate_exact_range_is_100():
    assert climate_match({"temp_range_c": [-10, 20]}, {"temp_min_c": -10, "temp_max_c": 20}) == 100.0

def test_weighted_score_is_100_for_exact_features():
    target = {"avg_slope_deg": 10, "regolith_composition": {"basalt_pct": 40}, "temp_range_c": [-10, 20]}
    analog = {"slope_deg": 10, "spectral_signature": {"basalt_pct": 40}, "temp_min_c": -10, "temp_max_c": 20}
    result = score_analog(target, analog, {"topography": .4, "geochemistry": .35, "climate": .25})
    assert result["similarity_score"] == 100.0

def test_accessibility_bands():
    assert accessibility_rating(80) == "High"
    assert accessibility_rating(60) == "Moderate"
    assert accessibility_rating(20) == "Low"
    assert accessibility_rating(None) == "Unknown"
