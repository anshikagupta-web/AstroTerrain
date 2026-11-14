# AstroTerrain — Scientific Dataset Collection

This directory contains real scientific datasets acquired for the AstroTerrain project.

## Earth

### Copernicus GLO-90
- Location: `earth/copernicus_glo90/`
- Four regional DEM GeoTIFF tiles.
- Used for elevation and terrain context.
- Original GeoTIFF files retained.

### NASA POWER
- Location: `earth/nasa_power/`
- Four regional daily climate CSV files: Hawaii, Svalbard, Atacama and Antarctica.
- Parameters: T2M, T2M_MAX and T2M_MIN.
- Period: 2020-01-01 to 2025-12-31.
- 2,192 daily observations per regional file.
- Missing-value sentinel: -999.

These locations are candidate analogs, not scientifically validated analog matches.

## Moon

### LOLA
- Location: `lunar/lola_875s_20m/`
- Polar elevation raster and original PDS label/XML/catalog metadata.
- 7,584 x 7,584 samples.
- 32-bit floating point.
- 20 m/pixel map scale.
- Polar stereographic projection.

### Diviner
- Location: `lunar/diviner/`
- Maximum and minimum TBOL anomaly point datasets.
- Values are brightness-temperature anomalies, not absolute surface temperatures.

### Moon Mineralogy Mapper (M3)
- Location: `lunar/m3_index/`
- L2 product index and associated label/information files.
- This is an index, not the actual reflectance image products.

## Mars

### MOLA
- Location: `mars/mola/`
- Global elevation raster with original label/header/XML metadata.

### CRISM
- Location: `mars/crism/`
- Product inventories and search-result metadata.
- The `jezero/` directory contains the downloaded CRISM mineral-summary product:
  `t1250_mrrsu_20n078_0327_4`
- Image dimensions: 1,636 lines x 1,538 samples x 60 bands.
- Sample format: PC_REAL, 32-bit.
- Map projection: Equirectangular.
- Label-reported center: 20.0 degrees latitude, 77.5 degrees longitude.
- The IMG download was verified against the expected 603,880,320-byte size.

The product is a mineral-summary product. Verify its footprint and band metadata before making claims about specific Jezero locations or mineral abundances.

### THEMIS
- Location: `mars/themis/`
- Daytime PNG image retained for visual context.
- This PNG is not a calibrated numeric thermal raster.

## Scientific limitations

- Earth analog candidates have not been scientifically validated.
- No NDVI is claimed because aligned red/NIR reflectance rasters are not available.
- No unsupported mineral percentages or compositions have been fabricated.
- Diviner anomaly values must not be interpreted as absolute surface temperatures.
- M3 index files do not substitute for actual M3 reflectance products.
- Original labels, headers, XML files and catalog metadata are retained wherever available.

## Integrity

`SHA256SUMS.txt` contains SHA-256 checksums for the collected data files and this README. Recreate it after modifying or adding datasets.
