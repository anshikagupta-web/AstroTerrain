-- REAL SCIENTIFIC DATASETS ACQUIRED FOR ASTROTERRAIN
-- Sources: Copernicus GLO-90 DEM, NASA POWER, LRO LOLA, LRO Diviner, MGS MOLA.
-- Note: These are candidate analog sites and target profiles, not validated mission recommendations.

INSERT INTO planetary_targets (planet, site_id, site_name, geom, avg_slope_deg, elevation_m, regolith_composition, primary_rock, temp_range_c, data_source)
VALUES
('moon', 'moon-shackleton-real', 'Shackleton Crater (Lunar South Pole, LOLA/Diviner)', ST_SetSRID(ST_MakePoint(0.0, -89.9), 4326), 12.5, -4000.0, '{}'::jsonb, 'anorthosite and basaltic impact melt', ARRAY[-248, 100], 'nasa_lro_lola_diviner_pds'),
('moon', 'moon-marius-hills-real', 'Marius Hills Pit Crater (Lunar Lava Tube Skylight)', ST_SetSRID(ST_MakePoint(-56.77, 14.08), 4326), 28.0, -250.0, '{}'::jsonb, 'mare basalt', ARRAY[-130, 105], 'nasa_lola_kaguya_selene'),
('mars', 'mars-jezero-real', 'Jezero Crater Delta (Mars 2020 Landing Site)', ST_SetSRID(ST_MakePoint(77.58, 18.38), 4326), 6.0, -2500.0, '{}'::jsonb, 'basaltic sediment', ARRAY[-85, 10], 'nasa_mgs_mola_meda_pds'),
('mars', 'mars-pavonis-tubes-real', 'Pavonis Mons Flank Pit (Martian Lava Tube Skylight)', ST_SetSRID(ST_MakePoint(-113.2, 0.8), 4326), 22.0, 4200.0, '{}'::jsonb, 'tholeiitic basalt', ARRAY[-95, 5], 'nasa_mola_hirise_pds')
ON CONFLICT (planet, site_id) DO NOTHING;

INSERT INTO earth_analog_tiles (site_id, site_name, country, geom, elevation_m, slope_deg, ndvi, spectral_signature, primary_rock, temp_min_c, temp_max_c, accessibility_score, is_subterranean, is_active, data_source)
VALUES
('real-analog-hawaii', 'Hawaii Volcanic Field (Mauna Kea/Loa)', 'United States', ST_SetSRID(ST_MakePoint(-155.5, 19.5), 4326), 3210.327, 8.36466, NULL, '{}'::jsonb, 'basalt', 10.34, 27.28, 85.0, FALSE, TRUE, 'copernicus_glo90_nasa_power'),
('real-analog-svalbard', 'Svalbard Arctic Terrain (Spitsbergen)', 'Norway', ST_SetSRID(ST_MakePoint(16.0, 78.0), 4326), 34.854, 1.314, NULL, '{}'::jsonb, 'basaltic permafrost', -30.40, 11.44, 52.0, FALSE, TRUE, 'copernicus_glo90_nasa_power'),
('real-analog-atacama', 'Atacama Desert Hyper-Arid Core (Yungay)', 'Chile', ST_SetSRID(ST_MakePoint(-68.2, -23.5), 4326), 2300.732, 0.02236, NULL, '{}'::jsonb, 'evaporite and volcanic ash', -2.73, 35.20, 65.0, FALSE, TRUE, 'copernicus_glo90_nasa_power'),
('real-analog-antarctica', 'McMurdo Dry Valleys (Beacon Valley)', 'Antarctica', ST_SetSRID(ST_MakePoint(161.0, -77.5), 4326), 1505.735, 9.421, NULL, '{}'::jsonb, 'sandstone and dolerite', -54.33, -7.39, 32.0, FALSE, TRUE, 'copernicus_glo90_nasa_power')
ON CONFLICT (site_id) DO NOTHING;
