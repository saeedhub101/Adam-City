# Maps and geographic layers

This folder stores map-oriented datasets and indexes for Ermita, Manila, with detailed focus on Rizal Park.

## Planned layers
- ermita_boundary — project boundary used for clipping; record its source and date.
- street_network — road and path geometry, including named and unnamed ways.
- building_footprints — individual building polygons where openly available.
- places — point features such as stores, restaurants, hospitals and public facilities.
- street_signs — observed or sourced sign locations and text.
- official_reference_maps — metadata and links for NAMRIA/Geoportal maps; only store files when their reuse terms permit.

## Preferred formats
GeoJSON for interoperable vector exports; GeoPackage for larger GIS datasets; CSV for tabular indexes; keep source ZIP/SHP files intact in a separate raw-data location when redistribution is permitted.

## Current status
No new map geometry is claimed as imported by this folder setup. The source index at [Geoportal Philippines](https://geoportal.gov.ph/) lists road layers and built-up-area layers, but each layer's coverage and download restriction must be checked before reuse. See the [Geoportal data inventory](https://www.geoportal.gov.ph/gpresources/GP_DataInventory.pdf).

## Attribution and licensing
For OpenStreetMap-derived data, include OpenStreetMap attribution and comply with the ODbL: https://www.openstreetmap.org/copyright. Do not copy map tiles or imagery from a provider unless its terms explicitly permit that use.
