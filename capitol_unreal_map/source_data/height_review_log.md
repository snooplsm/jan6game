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

## Review rule

Do not promote these targets to `source_backed_height` based on these sources.
Future promotion requires an explicit total height, measured elevation drawing,
or a clean public rooftop-to-ground elevation match for the target footprint.
