# Surrounding-Building Height Review Log

This log records manual reviews of high-priority height targets from
`exterior.height_model.height_review_targets`. A reviewed target remains
estimated unless a source explicitly supports total exterior height or a
defensible roof-to-ground measurement.

## Thurgood Marshall Federal Judiciary Building (OSM way 66418725)

- Current model height: 40.31 m.
- Current source class: deterministic footprint/type/area estimate.
- Reviewed public source: [Architect of the Capitol](https://www.aoc.gov/explore-capitol-campus/buildings-grounds/supreme-court/thurgood-marshall-building).
- Confirmed facts: completed in 1992; approximately one million square feet;
  includes a five-story entrance atrium and a low mechanical-penthouse dome.
- Decision: retain the 40.31 m estimate. The five-story statement describes the
  atrium, not the building's total story count or exterior height.

## Capitol Power Plant (OSM way 48040013)

- Current model height: 27.67 m.
- Current source class: deterministic footprint/type/area estimate.
- Reviewed public source: the 2014 Congressional Directory, Capitol Power Plant
  entry, available through [GovInfo](https://www.govinfo.gov/content/pkg/CDIR-2014-02-18/pdf/CDIR-2014-02-18.pdf).
- Confirmed facts: the original plant was authorized in 1904, completed in
  1910, and measured 244 feet 8 inches by 117 feet in plan.
- Decision: retain the 27.67 m height estimate. The published dimensions support
  footprint-scale review but do not state exterior height.

## Capitol Hill Baptist Church (OSM way 66732540)

- Current model height: 24.58 m from the deterministic footprint/type/area
  heuristic; no reliable total sanctuary or tower height was found.
- Reviewed public sources: [DC Historic Preservation Review Board case
  15-502](https://planning.dc.gov/sites/default/files/dc/sites/op/publication/attachments/Capitol%20Hill%20HD%20525%20A%20Street%20NE%20HPA%2015%20502.pdf)
  and the church's [accessibility page](https://www.capitolhillbaptist.org/visit-us/accessibility/).
- Confirmed facts: the large brick church was designed by Appleton P. Clark,
  Jr. and built around 1911; its rear brick school addition dates to 1927. The
  approved 2015 A Street accessible ramp reaches an entrance six feet above
  sidewalk at a 1:12 slope, occupies a 52-foot-long footprint including flat
  areas, and uses a matching brick base with black iron railing. The church
  confirms an accessible ramp from the smaller A Street parking lot into the
  first floor.
- Decision: retain the unresolved 24.58 m building-height heuristic, but add a
  source-dimensioned ramp assembly with three sloped runs, three landings, six
  rails, and twelve posts. Its switchback fit is explicitly approximate because
  the public staff report does not include fabrication drawings; do not treat it
  as a surveyed layout or infer unsupported sanctuary/tower dimensions.

## Eric E. Hotung International Law Building (OSM way 48040818)

- Current model height: 30.24 m.
- Current source class: deterministic footprint/type/area estimate.
- Target-era footprint evidence: the historical OSM/DCGIS record identifies the
  building at 550 1st Street NW and carries a DCGIS capture date of April 4,
  2005.
- Reviewed public source: [Georgetown Law's Hotung building virtual tour](https://www.law.georgetown.edu/admissions-aid/connect-with-georgetown-law/virtual-tour/the-eric-e-hotung-international-law-center-building/).
- Confirmed facts: completed in August 2004; six stories; therefore present and
  in substantially its current institutional use well before January 6, 2021.
- Decision: retain the 30.24 m estimate. The source confirms story count but not
  total exterior height, roof height, floor-to-floor dimensions, or rooftop
  mechanical height. Applying the generic 3.4 m-per-level rule would produce
  20.4 m and is not defensible for this large institutional building without a
  measured elevation or a building-specific floor-to-floor source.

## Underground Capitol-area structure (OSM way 888787630)

- Previous model height: 42.65 m from a deterministic footprint/type/area
  estimate, making it the highest-priority unresolved height-review target.
- Historical source evidence: the checked-in January 6, 2021 OSM element is
  explicitly tagged `building=yes` and `location=underground`.
- Decision: exclude the footprint from visible above-ground building massing
  rather than estimate a skyline height. Retain an exclusion record with the
  original tags in scene metadata. This corrects a source-interpretation error;
  it does not expose or model subsurface layout.

## House parking garages beneath the green-roof park (OSM ways 888787619 and 888787620)

- Previous model heights: 41.52 m and 41.09 m deterministic
  footprint/type/area estimates.
- Historical OSM evidence: both footprints are tagged `building=parking`,
  `amenity=parking`, and `parking=multi-storey`, but lack an explicit
  `location=underground` tag.
- Reviewed public source: [Architect of the Capitol, "Water Features
  Everywhere"](https://www.aoc.gov/explore-capitol-campus/blog/water-features-everywhere).
- Confirmed fact: the two House Garage fountains sit in the park south of the
  Capitol, and that park is the green roof for the parking garages below.
- Decision: exclude these two ID-specific footprints from visible above-ground
  building massing and retain source-cited metadata records. Do not generalize
  this override to other `parking=multi-storey` features, and do not model or
  expose garage interiors.

## Hart Senate Office Building (OSM way 66733226)

- Previous model height: 13.60 m.
- Reviewed public source: [U.S. Senate, Hart Senate Office Building](https://www.senate.gov/about/historic-buildings-spaces/office-buildings/hart-building.htm).
- Confirmed facts: first occupied in November 1982; nine stories; a 90-foot-high
  central atrium; three additional underground parking levels.
- Decision: replace the footprint/type/area heuristic with a public
  level-count estimate of 30.60 m using the package's conservative 3.4 m per
  above-ground story rule. Keep the result classified as an estimate rather
  than an exact or measured exterior height. The underground parking levels do
  not contribute to the visible extrusion.

## O'Neill House Office Building (OSM way 48037324)

- Current model height: 23.80 m.
- Reviewed public source: [Architect of the Capitol, O'Neill House Office Building](https://www.aoc.gov/explore-capitol-campus/buildings-grounds/house-office-buildings/oneill).
- Confirmed facts: the renovation added a seven-story central atrium and a
  six-story north entrance atrium; the building reopened for federal occupancy
  in 2014 and transferred to House ownership in 2017.
- Decision: retain the existing seven-level, 23.80 m visual estimate and upgrade
  its provenance from an OSM-only level count to an authoritative public
  level-count estimate. Do not treat the atrium statement as an exact exterior
  height.

## Longworth House Office Building (OSM relation 1029365)

- Previous generated state: omitted because the building tags live on a
  multipolygon relation rather than its untagged outer way.
- Reviewed public source: [Architect of the Capitol, Longworth House Office Building](https://www.aoc.gov/explore-capitol-campus/buildings-grounds/house-office-buildings/longworth).
- Confirmed facts: completed in spring 1933; seven stories; the sloped site's
  rusticated base varies from two to four stories.
- Decision: include the historical relation footprint and use a clearly labeled
  seven-level, 23.80 m public level-count estimate. Preserve the inner courtyard
  way ID as provenance for a later courtyard-aware modular replacement.

## Dirksen Senate Office Building (OSM relation 1047027)

- Previous generated state: omitted because the building tags live on a
  multipolygon relation rather than its untagged outer way.
- Reviewed public source: [Architect of the Capitol, Dirksen Senate Office Building](https://www.aoc.gov/explore-capitol-campus/buildings-grounds/senate-office-buildings/dirksen).
- Confirmed facts: the approved design was a seven-story E-shaped building and
  it opened in 1958.
- Decision: include the historical relation footprint and use a clearly labeled
  seven-level, 23.80 m public level-count estimate. Preserve both inner-ring way
  IDs as provenance for later courtyard-aware geometry.

## Rayburn House Office Building (OSM relation 1029369)

- Current model height: 14.51 m from the historical relation's explicit height
  tag.
- Reviewed public source: [Architect of the Capitol, Rayburn House Office Building](https://www.aoc.gov/explore-capitol-campus/buildings-grounds/house-office-buildings/rayburn).
- Confirmed facts: four principal floors, three underground garage levels, a
  basement, a sub-basement, and a rooftop machinery penthouse; fully occupied
  by April 1965 and therefore long-established by January 2021.
- Decision: retain the explicit 14.51 m main-mass height. Underground levels do
  not contribute to visible extrusion. The machinery penthouse and modified-H
  articulation remain required reference-modeled roof details rather than a
  reason to inflate the whole footprint.

## Russell Senate Office Building (OSM relation 1029367)

- Current model height: 13.60 m from the historical relation's four-level tag.
- Reviewed public sources: [Architect of the Capitol, Russell Senate Office Building](https://www.aoc.gov/explore-capitol-campus/buildings-grounds/senate-office-buildings/russell)
  and [U.S. Senate, Russell Senate Office Building](https://www.senate.gov/about/historic-buildings-spaces/office-buildings/russell-building.htm).
- Confirmed facts: the restrained exterior was deliberately limited in height;
  it presents three stories above ground toward Constitution Avenue and five
  stories on the downslope C Street side.
- Decision: retain the four-level, 13.60 m extrusion as a documented average
  blockout. A higher-fidelity replacement must model the grade-dependent
  three-to-five-story exposure and courtyard explicitly rather than applying a
  uniform taller extrusion.

## One Independence Square (OSM way 48037411)

- Previous model state: anonymous `osm_way_48037411` footprint with a 32.83 m
  deterministic footprint/type/area estimate.
- Historical address evidence: the checked-in January 2021 OSM/DCGIS footprint
  is 250 E Street SW, Washington, DC 20024.
- Reviewed public sources: the [One Independence Square property
  sheet](https://images4.loopnet.com/d2/4_nGZbPwun-iQYyXK4QgELjNUZlR5IQt48whGZArEWg/document.pdf)
  and [GSA lease record](https://www.gsa.gov/system/files/Real_Estate_Acquisitions/LDC12661-SLA-2-_Z.pdf).
- Confirmed facts: the property has nine above-grade floors; its first-floor
  slab-to-slab height is 12 ft 6 in and floors 2-9 are each 9 ft 8 in. GSA's
  lease identifies the premises as 250 E Street SW and the lessor as Piedmont -
  Independence Square, LLC.
- Decision: rename the footprint `One Independence Square` and replace the
  heuristic extrusion with the summed 89 ft 10 in (27.3812 m) structural stack.
  This is source-derived main-mass height, not a surveyed roof elevation;
  unmeasured parapets and rooftop equipment remain separate visual details. The
  historical extract also contains tenant-labeled way `535720702`, which shares
  37 nodes, the same address, and the same bounding box with this envelope.
  Exclude that redraw from visible massing and retain an audit record pointing
  back to the more articulated DCGIS footprint, avoiding a false double tower
  and coincident-surface flicker.

## Eric E. Hotung International Law Building (OSM way 48040818)

- Previous model height: 30.24 m from the deterministic footprint/type/area
  heuristic.
- Reviewed public source: [Georgetown Law, Eric E. Hotung International Law
  Center Building virtual tour](https://www.law.georgetown.edu/admissions-aid/connect-with-georgetown-law/virtual-tour/the-eric-e-hotung-international-law-center-building/).
- Confirmed facts: Georgetown Law describes Hotung as a six-story academic
  building completed in August 2004, well before the January 2021 target date.
- Decision: replace the heuristic with a clearly labeled six-level, 20.40 m
  visual estimate using the package's conservative 3.4 m per above-ground story
  rule. Do not treat the story count as an exact parapet, penthouse, or surveyed
  exterior roof height.

## YOTEL Washington DC transition site (OSM way 74035728)

- Current model height: 32.98 m from the deterministic footprint/type/area
  heuristic; historical address is 415 New Jersey Avenue NW.
- Reviewed public sources: YOTEL's [March 2020 transition
  announcement](https://www.yotel.com/ja/node/2851) and [February 1, 2021
  opening announcement](https://www.yotel.com/en/press/yotel-washington-dc-officially-opens).
- Confirmed facts: the former Liaison Washington Capitol Hill underwent a
  year-long full reconstruction and remodel; YOTEL said the property would
  remain open through the transition and officially debuted the completed
  hotel on February 1, 2021.
- Target-date decision: identify the January 6 footprint as `YOTEL Washington
  DC transition site`, record the former Liaison identity, and classify it as
  a pre-opening transition near completion. This is 26 days before the official
  YOTEL debut, so do not silently apply the completed summer 2021 rooftop pool
  state.
- Height decision: retain the 32.98 m heuristic. YOTEL's later `Deck 11`
  branding identifies a rooftop level, while a secondary trade report calls
  the hotel 13 stories; neither is a sufficiently clear total exterior roof
  height for replacing the current extrusion.

## Review rule

Do not promote these targets to `source_backed_height` based on these sources.
Future promotion requires an explicit total height, measured elevation drawing,
or a clean public rooftop-to-ground elevation match for the target footprint.
