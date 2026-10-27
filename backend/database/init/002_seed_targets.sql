-- Real named reference locations, but NO invented scientific properties.
-- IMPORTANT: 'location' is null for planetary bodies because WGS84/EPSG:4326
-- denotes an Earth-based CRS. A planetary CRS needs its own design.
INSERT INTO planetary_targets (id, name, body)
VALUES
    ('moon_shackleton', 'Shackleton Crater', 'moon'),
    ('mars_jezero', 'Jezero Crater', 'mars')
ON CONFLICT (id) DO NOTHING;
