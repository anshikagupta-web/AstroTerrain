-- SYNTHETIC DEMO DATA ONLY. Not validated science or mission recommendations.
INSERT INTO planetary_targets (planet, site_id, site_name, geom, avg_slope_deg, elevation_m, regolith_composition, primary_rock, temp_range_c, data_source)
VALUES
('moon', 'shackleton-crater', 'Shackleton Crater (synthetic demo profile)', ST_SetSRID(ST_MakePoint(0.0, -89.9), 4326), 12.5, -4000, '{"basalt_pct":35,"silica_pct":28,"iron_oxide_pct":12}'::jsonb, 'basalt', ARRAY[-80,20], 'synthetic_demo'),
('mars', 'jezero-crater', 'Jezero Crater (synthetic demo profile)', ST_SetSRID(ST_MakePoint(77.58, 18.38), 4326), 6.0, -2500, '{"basalt_pct":45,"silica_pct":25,"iron_oxide_pct":18}'::jsonb, 'basaltic sediment', ARRAY[-70,10], 'synthetic_demo')
ON CONFLICT (planet, site_id) DO NOTHING;

INSERT INTO earth_analog_tiles (site_id, site_name, country, geom, elevation_m, slope_deg, ndvi, spectral_signature, primary_rock, temp_min_c, temp_max_c, accessibility_score, is_subterranean, is_active, data_source)
VALUES
('demo-analog-a', 'Synthetic Demo Tile A', 'DEMO', ST_SetSRID(ST_MakePoint(-68.2,-23.5),4326), 2300, 11.0, 0.12, '{"basalt_pct":32,"silica_pct":30,"iron_oxide_pct":15}'::jsonb, 'basalt', -15, 35, 68, FALSE, TRUE, 'synthetic_demo'),
('demo-analog-b', 'Synthetic Demo Tile B', 'DEMO', ST_SetSRID(ST_MakePoint(-155.5,19.5),4326), 900, 7.5, 0.28, '{"basalt_pct":48,"silica_pct":24,"iron_oxide_pct":17}'::jsonb, 'basalt', -5, 30, 82, FALSE, TRUE, 'synthetic_demo'),
('demo-analog-c', 'Synthetic Demo Tile C', 'DEMO', ST_SetSRID(ST_MakePoint(16.0,78.0),4326), 120, 18.0, 0.05, '{"basalt_pct":25,"silica_pct":35,"iron_oxide_pct":10}'::jsonb, 'volcanic rock', -25, 12, 55, TRUE, TRUE, 'synthetic_demo'),
('demo-analog-d', 'Synthetic Demo Tile D', 'DEMO', ST_SetSRID(ST_MakePoint(161.0,-77.5),4326), 300, 5.0, 0.18, '{"basalt_pct":40,"silica_pct":22,"iron_oxide_pct":20}'::jsonb, 'basalt', -35, 5, 38, FALSE, TRUE, 'synthetic_demo')
ON CONFLICT (site_id) DO NOTHING;
