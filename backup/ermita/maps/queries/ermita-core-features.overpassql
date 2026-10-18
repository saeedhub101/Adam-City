/*
Ermita, Manila — first-pass core feature extraction
Boundary relation reference: https://www.openstreetmap.org/relation/103706
Output is raw Overpass JSON with full geometry. Export via https://overpass-turbo.eu/
and choose Export -> GeoJSON if a converted GeoJSON file is needed.

This query collects mapped roads/paths, buildings, businesses, health facilities,
amenities, tourism/historic features and tagged street/traffic signs.
Review output and license before committing any exports.
*/
[out:json][timeout:180];
rel(103706);
map_to_area -> .ermitaArea;
(
  way(area.ermitaArea)["highway"];
  way(area.ermitaArea)["building"];
  nwr(area.ermitaArea)["shop"];
  nwr(area.ermitaArea)["amenity"];
  nwr(area.ermitaArea)["healthcare"];
  nwr(area.ermitaArea)["tourism"];
  nwr(area.ermitaArea)["historic"];
  nwr(area.ermitaArea)["office"];
  nwr(area.ermitaArea)["craft"];
  nwr(area.ermitaArea)["public_transport"];
  nwr(area.ermitaArea)["traffic_sign"];
  nwr(area.ermitaArea)["man_made"="street_cabinet"];
);
out geom;
