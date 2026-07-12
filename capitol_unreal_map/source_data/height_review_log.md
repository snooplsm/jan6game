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

## Review rule

Do not promote these targets to `source_backed_height` based on these sources.
Future promotion requires an explicit total height, measured elevation drawing,
or a clean public rooftop-to-ground elevation match for the target footprint.
