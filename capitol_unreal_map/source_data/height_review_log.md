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

## Review rule

Do not promote either target to `source_backed_height` based on these sources.
Future promotion requires an explicit total height, measured elevation drawing,
or a clean public rooftop-to-ground elevation match for the target footprint.
