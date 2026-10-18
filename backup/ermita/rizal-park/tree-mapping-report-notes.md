# Rizal Park tree mapping: extracted report facts

**Primary source:** National Parks Development Committee / UPLB student-intern mapping report, *GIS Group Distribution and Thematic Mapping Report*.  
**Source URL:** https://npdc.gov.ph/wp-content/uploads/2025/02/GIS-Group_Distribution-and-Thematic-Mapping-Report.pdf  
**Use:** Factual research notes to guide import of the downloadable inventory tables and maps.

## Coverage described by the report

The report says its mapping work created inventory maps for park areas that were not included in the 2023 inventory, including:
- Gubat sa Syudad
- The Martyrdom of Dr. Jose Rizal
- The Gallery
- Chinese Garden
- Luneta Bark Rangers Headquarters
- Open-Air Auditorium
- NPDC Office at the Old Planetarium
- Chess Plaza
- Japanese Garden

It also includes the Central Promenade and areas to the right of the monument, including Aguinaldo House and the Garden for the Elderly. Areas covered in prior work included Kanlungan ng Sining, Bachelor's Garden, Noli Me Tangere Garden, and the Western Section.

## Fruit-bearing tree map facts

The report describes 16 fruit-bearing-tree maps: 14 maps for different Rizal Park gardens/areas, one map for Rizal Park overall, and one for Paco Park. It notes that Noli Me Tangere Garden and the Luneta Bark Rangers Headquarters were omitted from the fruit-bearing maps because no fruit-bearing trees were recorded in those areas in that analysis.

**Interpretation warning:** “No fruit-bearing trees recorded” is a statement about that report's dataset and classification, not a guarantee that no tree has ever been planted there or that conditions remain unchanged.

## NPDC downloadable datasets to obtain and parse

The NPDC downloads page lists:
- Rizal Park Luneta Tree Inventory 2024
- Bachelor's Garden Tree Inventory
- Kanlungan ng Sining Tree Inventory
- Noli Me Tangere Tree Inventory
- Western Section Tree Inventory
- Distribution maps of exotic trees
- Distribution maps of fruit-bearing trees
- Distribution maps of native trees
- Tree thematic maps
- Tree inventory maps

Download page: https://npdc.gov.ph/downloads/

## Target fields for individual tree rows

Retain the original source columns where present. Expected fields to look for include:
- NPDC/tree inventory identifier
- Common name
- Scientific name
- Family name
- Species/classification group
- Fruit-bearing status
- Diameter at breast height (DBH)
- Height
- Longitude and latitude (including original coordinate format)
- Defects
- Health status
- Structural integrity
- Risk rating
- Remarks
- Garden/section name
- Source workbook/sheet
- Source file URL and version/date

Do not infer missing measurements or convert coordinates without recording the conversion method. Validate any DMS-to-decimal conversion against the source map and expected park extent.

## Count reconciliation

NPDC's web portal currently displays an overall inventory counter of 679 and also shows category counters (e.g. indigenous forest trees, exotic forest trees, Ficus, fruit-bearing trees, and palms). A separate mapped PDF reports 1,084 native trees and palms for western and central sections. These counts are not directly interchangeable because they appear to describe different datasets, category definitions, or coverage. Record each number with its exact source, date, category, and geographic scope; do not sum the website counters or claim the figures conflict until the source tables are reconciled.

Portal: https://npdc.gov.ph/inventory-of-trees/  
Species reference: https://npdc.gov.ph/inventory-of-trees-2/  
Distribution map PDF: https://npdc.gov.ph/wp-content/uploads/2025/02/Inventory-Of-Trees.pdf
