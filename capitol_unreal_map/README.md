# U.S. Capitol Unreal Map Package

This package is a first public-data pass at a U.S. Capitol map for Unreal Engine 5.8, authored at first-person centimeter scale.

## Quick Links

- Local viewer: `http://127.0.0.1:8765/viewer.html`
- Interior-only preview: `http://127.0.0.1:8765/viewer.html#interior-only`
- Full interior plan preview: `http://127.0.0.1:8765/viewer.html#interior-plan`
- Chamber top-down preview: `http://127.0.0.1:8765/viewer.html#chambers-top`
- House Chamber plan preview: `http://127.0.0.1:8765/viewer.html#house-plan`
- Senate Chamber plan preview: `http://127.0.0.1:8765/viewer.html#senate-plan`
- Public chamber role-zone preview: `http://127.0.0.1:8765/viewer.html#role-zones`
- House public gallery preview: `http://127.0.0.1:8765/viewer.html#house-gallery`
- Senate public gallery preview: `http://127.0.0.1:8765/viewer.html#senate-gallery`
- Gameplay item preview: `http://127.0.0.1:8765/viewer.html#gameplay-items`
- Grounds detail preview: `http://127.0.0.1:8765/viewer.html#grounds-details`
- Capitol facade/roof detail preview: `http://127.0.0.1:8765/viewer.html#facade-details`
- Roof detail preview: `http://127.0.0.1:8765/viewer.html#roof-details`
- Office/support detail preview: `http://127.0.0.1:8765/viewer.html#offices`
- Public signage detail preview: `http://127.0.0.1:8765/viewer.html#signage-details`
- Door hardware detail preview: `http://127.0.0.1:8765/viewer.html#door-details`
- Public furnishing detail preview: `http://127.0.0.1:8765/viewer.html#furnishing-details`
- Public art preview: `http://127.0.0.1:8765/viewer.html#public-art`
- Wall finish detail preview: `http://127.0.0.1:8765/viewer.html#wall-finish-details`
- Floor finish detail preview: `http://127.0.0.1:8765/viewer.html#floor-details`
- Surface aging detail preview: `http://127.0.0.1:8765/viewer.html#surface-aging-details`
- Ceiling/crown detail preview: `http://127.0.0.1:8765/viewer.html#ceiling-details`
- First-person whole-map walk preview: `http://127.0.0.1:8765/viewer.html#walk-map`
- First-person walk preview: `http://127.0.0.1:8765/viewer.html#walk`
- Texture preview: `http://127.0.0.1:8765/texture_preview.html`

It contains:

- exterior buildings, roads, bike-lane features, crossings, traffic-signal markers, public DCGIS traffic-sign, fixture, curb, sidewalk, and road-surface props, pedestrian-scale public streetscape props, road-surface repair/crack/grate visuals, public bike racks, public trash/recycling receptacles, bus-stop shelter markers, hydrant markers, and authored public grounds details derived from OpenStreetMap context plus public DCGIS/schematic visual markers
- pedestrian paths, curb edges, sidewalks where side-specific sidewalk tags exist, and lane-edge markings derived from the same public OSM extract
- a public-only Capitol interior schematic with major spaces, generic office/support zones, Rotunda architectural detail records, Rotunda dome interior ribs/coffers/frieze/light-pool markers, public room/galleries/wayfinding signage, public doorway panels and hardware, public benches/display cases/lecterns/receptacles/plant urns, raised wall-finish/wainscot/pilaster trim, picture rails, decorative wall panels, public architraves, public ceiling/coffer/crown-trim/vent-grille records, public floor-finish and room-shape records, layered public surface-aging records for dust shadows, scuffs, contact wear, and tarnish, House Chamber, Senate Chamber, galleries, generic chamber seating, source-backed public-art markers including named Rotunda historical paintings, visible lighting/wall-treatment details, and a joint-session House Chamber visual layout
- public-facing Capitol visual details including an authored Capitol landmark mesh, approximate revolving-door assemblies with glass drums, circular track rings, radial wing panels, perimeter mullions, and side-lites, public plaza paver joints, expansion seams, stone tone patches, and drain-slot visuals, bevelled public massing blocks, layered pavilions, pavilion setback reveal shadows, attic-window bands, cornice shadow reveals, articulated roof/courtyard recesses, recessed facade bays, arcade shadow panels, portico soffit coffers, terrace retaining walls, dormers, skylight strips, pediments, generic pediment relief blocks, stone window surrounds, arched window trim, keystones, window mullions, ashlar stone courses, vertical stone joints, facade weathering stains, limestone discoloration patches, sill runoff stains, base grime bands, roof surface joints, roof capstone blocks, sloped roof skirt panels, parapet corner piers, parapet shadow gaps, generic non-operational roof vent housings, lower terrace stair/riser bands, terrace landing slabs, worn plaza/step patches, public step-edge chip shadows, door surrounds, pilasters, exterior column bases/capitals/fluting, column capital leaf/volute blocks, column base chips, stair treads, approach handrails, dentil/cornice courses, cornice brackets, roof balustrades, dome ribs, dome bands, dome shell panel frames, dome drum trim/spandrels/glass panes, dome shell rain streaks and shadow seams, lantern columns/window glass/balustrade, entry lamps, facade sconces, facade uplights, bollards, and benches
- fictional, non-graphic gameplay item pickup props in a separate preview lane: flagpole with American flag and campaign-style banner variants, nunchucks, bear spray, mace spray, throwable feces, knife, and handgun
- Unreal-friendly OBJ/MTL meshes in centimeter units
- JSON metadata for labels, source provenance, coordinates, rooms, seating records, and gameplay item records
- shared camera/viewpoint metadata for browser and Unreal inspection
- a Unreal material realism manifest for PBR-style roughness, metallic, specular, opacity, clear-coat, and base-color setup
- an Unreal Editor Python import script
- minimal Unreal project config for opening the package directly
- a local WebGL OBJ viewer for checking the generated meshes before Unreal import

## Generated Files

- `CapitolMap.uproject`
- `Config/DefaultEngine.ini`
- `Config/DefaultGame.ini`
- `generated/meshes/capitol_exterior_buildings.obj`
- `generated/meshes/capitol_exterior_roads_bike_lanes_markers.obj`
- `generated/meshes/capitol_landmark_visual_details.obj`
- `generated/meshes/capitol_public_interior_schematic.obj`
- `generated/meshes/capitol_gameplay_items.obj`
- `generated/meshes/capitol_materials.mtl`
- `generated/data/capitol_scene_metadata.json`
- `generated/data/capitol_package_validation.json`
- `generated/data/material_texture_manifest.json`
- `generated/data/unreal_import_report.json` after the Unreal import script is run
- `generated/textures/*_{basecolor,normal,roughness,ambient_occlusion}.png`
- `unreal/material_realism_manifest.json`
- `unreal/import_capitol_map.py`
- `viewer.html`

The OBJ meshes include generated `vt` texture coordinates, so Unreal material texture samples have UVs to read instead of relying on importer-generated defaults.

## Regenerate

From the repository root:

```bash
python3 capitol_unreal_map/scripts/generate_material_textures.py
python3 capitol_unreal_map/scripts/fetch_dcgis_planimetrics.py
python3 capitol_unreal_map/scripts/build_capitol_unreal_map.py
```

Texture generation defaults to production 4096x4096 PNG maps. For a quick local preview run, override the size explicitly:

```bash
CAPITOL_TEXTURE_SIZE=512 python3 capitol_unreal_map/scripts/generate_material_textures.py
CAPITOL_MIN_TEXTURE_SIZE=512 python3 capitol_unreal_map/scripts/validate_capitol_package.py
```

Validate the generated OBJ/MTL/metadata package before Unreal import:

```bash
python3 capitol_unreal_map/scripts/validate_capitol_package.py
```

The validator checks that:

- every metadata mesh exists
- OBJ face indices are valid
- every generated OBJ face has texture-coordinate coverage
- OBJ material references exist in `capitol_materials.mtl`
- every generated MTL material has a valid Unreal realism-material manifest entry
- every generated MTL material has generated basecolor, normal, roughness, and ambient-occlusion texture bindings
- every generated texture file is a valid PNG whose dimensions match `material_texture_manifest.json` and whose minimum production dimension is 4096px
- the expected exterior counts, pedestrian paths, curb records, lane-edge markings, public streetscape props, public grounds details, Capitol facade/furniture details, public interior rooms, generic office cells, House seats, Senate desks, public seating sections, joint-session zones, public Rotunda, signage, door-hardware, furnishing, wall-finish, floor, surface-aging, and ceiling detail layers, fictional gameplay item props, and generated viewpoints are present
- the authored Capitol landmark mesh max Z validates against the public 87.48m height target recorded in metadata
- the Unreal import script still references every generated mesh, expected destination path, import helper, label category, World Outliner folder, first-person setup/collision-proxy marker, photoreal preview marker, and import-report key
- the Unreal project config still enables the scripting plugins, Nanite/navigation settings, generated Capitol map editor/game defaults, and higher-quality preview renderer settings

It writes `generated/data/capitol_package_validation.json`, including an `unreal_importer` contract section. This proves local package consistency; the final editor check is still to run `unreal/import_capitol_map.py` inside Unreal 5.8.

The current validation report counts 1,504,224 vertices, 3,324,456 generated texture coordinates, and 1,784,788 triangles across the five OBJ meshes.

The current texture validation report counts 43 generated texture sets, 19 procedural texture styles, 10 photoreal-readiness feature markers, 172 PNG texture files, 75 material bindings, and a minimum generated texture dimension of 4096px.

The current Unreal importer validation report counts 232 report-key markers, 27 material-setup markers, 58 environment/lighting markers, 24 inspection-workflow markers, 58 Unreal project config markers, and 235 viewer markers, including generated material graph comments, two-sided/tangent-space material flags, clear-coat material support, ambient-occlusion map support, material texture feature reporting, capped public accent-light spawning from visible fixture-detail records, photoreal preview profile reporting, expanded public PlayerStart coverage, explicit Unreal DefaultPawn input mappings, browser photoreal shader/first-person walk HUD/reset/floor-bound markers, public exterior collision proxy coverage, building-height audit labels, and a public schematic inspection workflow contract for browser routes, Unreal cameras, and hide/visible tags.

The current generated build contains:

- 3,631 surrounding building footprints from the Jan 6-era OSM extract; the OSM `United States Capitol` footprint is intentionally skipped and replaced by the authored Capitol landmark mesh to avoid concave-roof triangulation artifacts
- surrounding-building height provenance is tracked in metadata: 25 buildings use explicit OSM/DCGIS height tags, 74 use `building:levels * 3.4m` estimates, 1,324 missing-height footprints use conservative DCGIS Planimetrics 1999 rooftop-to-ground elevation deltas, and 2,208 still use deterministic footprint/type/area estimates because they lack clean matched height data; 1,349 surrounding-building heights are now counted as source-backed, every surrounding building records `height_accuracy_tier`, `height_confidence`, and `height_review_priority`, and `height_model.height_review_targets` lists the 40 largest/highest-priority estimated buildings for the next source-matching pass; the checked-in DCGIS source contains 2,360 rooftop elevation points and 2,307 ground elevation points for the current map bounds; each surrounding building now records footprint area and footprint span for height auditing; the replaced OSM Capitol footprint carries an explicit 87.6m source height, and the authored Capitol visual mesh validates against an 87.48m public-height target
- 8,548 surrounding-building visual detail records, including nearby facade windows, roofline caps, cornice bands, parapet details, entries, rooftop details, facade pilasters, awnings, wall signs, and public-source height audit labels
- 1,432 roads/paths
- 242 bike-lane/cycleway features
- 636 pedestrian path/footway records
- 2,449 curb edge records
- 640 source-backed DCGIS sidewalk polygon records rendered as public sidewalk edge and surface-patch visuals
- 571 lane-edge marking records
- 396 street markers/crossings/traffic signals
- 6,217 public streetscape prop records, including schematic streetlights, 260 streetlight fixture-detail records, street-name signs, 180 street-name sign text-stroke records, traffic-signal heads, 138 traffic-signal mast-arm records, 138 traffic-signal backplate records, 138 pedestrian countdown-face records, 138 push-button plate records, 252 generic public DCGIS traffic-control sign props, 6 generic public DCGIS overhead traffic-sign props, 18 source-backed DCGIS fire hydrant props, 480 sampled DCGIS street-tree props, 220 sampled DCGIS utility-pole props, 240 sampled DCGIS miscellaneous public fixture props, 1,307 source-backed DCGIS curb-line props, 640 DCGIS sidewalk-edge props, 220 DCGIS sidewalk surface-patch props, 220 DCGIS road-edge props, 140 DCGIS road surface-patch props, tree planters, public stop bars, lane arrows, bike symbols, curb-ramp visuals, crosswalk ladder markings, tactile warning surfaces, sidewalk expansion joints, bike-lane delineator posts, pedestrian signal markers, public wayfinding signs, regulatory signs, bike-route signs, crosswalk-ahead signs, curb-paint segments, asphalt repair patches, crack-sealant strips, manhole-cover visuals, storm-drain grates, public utility boxes, public news/vendor boxes, public bike racks, public trash/recycling receptacles, public bus-stop shelter markers, and public hydrant markers; the mesh also includes crosswalk striping and bike-lane marker posts
- 169 authored public grounds detail records, including lawn panels, public walks, reflecting-pool marker, pool coping, formal planting beds, tree allees, 18 Unreal-spawnable public walk lamps, low plaza walls, 12 hedges, 16 path-edge stones, 16 grounds benches, and 24 ornamental planting clusters
- Capitol visual massing details including dome, lantern, porticos, columns, steps, plaza, grounds, public-facing revolving-door visuals with glass drums, track rings, wing panels, mullions, side-lites, public plaza paver joints, expansion seams, stone tone patches, drain-slot visuals, facade windows, recessed window shadow pockets, inner sash frames, pane-highlight strips, attic-window bands, stone window surrounds, arched window trim, facade keystones, window mullions, public ashlar stone courses, vertical stone joints, facade weathering stains, limestone discoloration patches, sill runoff stains, base grime bands, stepped pavilion massing, pavilion setback reveal shadows, facade shadow returns, facade water-table bands, cornice shadow reveals, recessed facade bays, arcade shadow panels, corner quoin blocks, inter-column portico shadows, layered portico entablature bands, frieze panel details, pediment raking-cornice blocks, portico side cornice returns, portico soffit coffers, terrace retaining walls, lower terrace stair/riser bands, terrace landing slabs, roof monitor ridges, roof surface joints, roof capstone blocks, sloped roof skirt panels, parapet corner piers, roof parapet shadow gaps, public roof drain/scupper visuals, generic non-operational roof vent housings, worn plaza/step patches, public step-edge chip shadows, public door surrounds, public facade pilasters, exterior column plinth/base/capital/fluting geometry with individual groove/base-ring/capital-abacus/capital leaf/volute/base-chip details, stair tread records, approach handrails, dentil/cornice courses, individual dentil blocks, cornice brackets, roof balustrades, articulated roof volumes, wing transition blocks, courtyard/recess shadow planes, dormers, skylight strips, dome drum arcade bays, visible dome curved-rib strips, dome shell panel frames, dome drum window trim/spandrel/glass panels, dome shell rain streaks and panel shadow seams, dome lateral bands, lantern columns/window trims/glass panes/balustrade, a public Statue of Freedom crown silhouette, pediment relief panels, generic pediment relief blocks with rosette/garland relief accents, entry lamps, facade sconces, facade uplights, bollards, and benches
- 7,268 Capitol facade/furniture detail records, including close-range public stone relief and wear: 704 staggered masonry joint records, 252 limestone pitting marks, 190 chipped limestone block records, 68 hairline crack records, 54 thin rain-streak records, 48 mortar shadow-groove records, 336 individual exterior column fluting-groove records, 266 facade window mullions, 266 facade window surrounds, 266 facade window recess-shadow records, 266 facade window inner-sash records, 266 facade window pane-highlight records, 232 roof capstone blocks, 224 exterior column capital leaf detail records, 204 facade corner quoin blocks, 192 public step grime-seam records, 138 recessed facade shadow panels, 116 cornice brackets, 116 individual dentil block records, 112 arched window trim records, 112 exterior column base chip detail records, 112 facade window keystone records, 112 sill runoff stain records, 98 limestone discoloration patches, 96 dome shell panel frames, 90 facade weathering stain records, 76 attic-window band records, 72 portico soffit coffers, 70 facade ashlar course records, 68 vertical stone joint records, 62 public plaza paver joints, 56 exterior column capital volute detail records, 56 public roof/drain scupper visuals, 48 dome shell panel shadow seams, 48 revolving-door wing-panel records, 48 revolving-door perimeter mullion records, 32 dome shell rain-streak weathering records, 32 public plaza stone tone-patch records, 24 revolving-door track-ring records, 24 revolving-door side-lite records, 16 dome drum glass-pane records, 14 public plaza drain-slot records, 12 public plaza expansion-seam records, 8 lantern glass-pane records, and other public-facing roof, stair, portico, dome, lantern, plaza, and entry details
- 60 generic public office/support visual cells
- 1,332 public office/support detail records, including 180 generic partition panels, 60 partition top caps, 60 generic door panels, 60 door thresholds, 60 generic public plaques, 60 desk-surface insets, 60 monitors, 60 monitor stands, 60 keyboards, 60 desk cable grommets, 60 cable trays, 60 wall outlet plates, 60 data plates, 60 paper stacks, 60 task lamps, 60 chair backs, 60 chair-arm pairs, 60 chair swivel bases, 60 bookcases, 60 storage cabinets, 8 shared support tables, and 4 public corridor bands
- 448 generic House floor seats
- 100 generic Senate desks
- 16 public seating-section records: 7 regular-session House/Senate chamber sections and 9 joint-session role zones
- 11,290 public chamber detail records for House/Senate rails, dais steps, rostrum desks with front-panel/brass-pull details, generic rostrum seal medallions, public lecterns with reading lamps, work tables with reading lamps, gallery rails, 60 gallery benches with 60 back panels, 180 seat slats, and 120 support brackets, gallery dividers, 64 gallery rail balusters, 4 gallery rail top caps, 32 gallery rail rosettes, 8 gallery edge trims, 36 balcony underside coffers, 43 chamber wall/acoustic panels, 28 chamber wall sconces, 46 chamber wall pilaster strips, 43 upper-wall frieze panels, 43 ceiling cove-molding segments, 28 public chamber light globes, 12 carpet runners, 24 carpet binding strips, 36 carpet weave bands, 24 carpet edge-fringe records, 14 carpet wear paths, 26 row shadow strips, 16 gallery tread-nosing strips, 22 rostrum backdrop trim inlays, 4 carpet medallions, balcony fascia, aisle edge markers, aisle step lights, row-marker plaques, rostrum microphone clusters, public gallery stanchions, 24 gallery support columns, 4 public display boards, 4 public display-board frame details, desk arc markers, desk surface markers, 16 public role-zone floor overlays, 64 public role-zone boundary strips, 16 public role-zone label plaques, 57 public role-zone count ticks, 548 generic desk-surface insets, 548 generic desk edge trims, 548 generic desk wood-grain strip records, 548 generic desk varnish-highlight records, 548 generic desk drawer pulls, 548 generic document stacks, 548 generic desk microphone markers, 548 generic nameplate strips, 548 bevelled chamber furniture records, 548 chair-arm pairs, 548 chair-arm wear records, 548 chair cushions, 548 chair-cushion seams, 548 chair-cushion piping records, 548 chair leather-wear patch records, 548 chair-back insets, 548 chair-back button details, 548 chair-back leather-scuff records, row modesty panels, backdrop panels, and flag standards with cloth/fold/stripe/canton detail
- 417 public circulation detail records for schematic corridor bands, door thresholds, room portal trim, public portal transoms, 8 portal opening-shadow panels, 16 portal jamb-return records, orientation signs, floor inlays, 34 public corridor pilasters, 20 public corridor sconces, 8 public floor medallions, 20 public route floor arrows, 16 public route chevrons, 14 low guide-rail records, 8 public transition arch surrounds, 16 transition reveal panels, 8 transition keystones, 8 transition floor mosaics, 8 threshold marble inserts, 16 threshold brass-edge records, 8 transition light-pool records, 8 lintel-shadow records, 6 public directory boards with 24 line glyphs, 8 wall clocks with hand pairs, 12 generic public safety cabinets with glass panels, 16 generic public emergency light blocks with lens pairs, 28 public wall switch plates, and 28 public wall outlet plates between major public spaces
- 261 public signage detail records for room-identification signs, directional signs, visitor-gallery markers, chamber-role markers, generic office-zone signs, public orientation map kiosks, 196 abstract sign-typography strokes, and 12 map-kiosk route-line glyphs
- 192 public door-hardware detail records: 24 double-door panels, 24 pull bars, 72 hinge plates, 24 kick plates, 12 transom panels, 12 header trims, and 24 side-lite panels at public/schematic doorway transitions
- 536 public furnishing/fixture detail records: 24 benches, 72 bench seat slats, 48 bench arm rests, 24 display cases, 96 display-case edge trims, 24 display-case object silhouettes, 48 display-case light strips, 24 display-case label plaques, 10 information lecterns, 30 lectern text-line glyphs, 16 receptacles, 16 receptacle sorting labels, 20 plant urns, 20 plant urn rims, 20 leaf-cluster records, 24 public queue posts, and 20 rope segments
- 1,758 public wall-finish detail records: 44 baseboards, 44 picture rails, 326 raised wainscot frames, 172 decorative wall panels, 172 upper wall panel frames, 238 wall pilasters, 18 public architrave trims, 44 wall material-variation panels, 498 bevelled wall-trim profile records, 44 baseboard grime decals, 44 wall patina decals, and 114 wainscot rub-mark decals across public rooms, chambers, galleries, and generic office/support zones
- 360 public Rotunda architectural detail records for wall ring, floor trim, center medallion, 16 radial floor inlays, 16 perimeter columns with base/capital blocks plus 64 fluting-groove records, 32 upper coffer panels, 4 public arch portals with 8 spandrel inlays and 4 keystone blocks, upper balustrade ring with 32 posts, oculus trim ring, dome springline/coffer-belt rings, 24 interior dome ribs, 72 dome coffer panels, 32 upper frieze panels, oculus light-pool marker, 7 public statue pedestal bases, and 7 pedestal plaques
- 773 public ceiling detail records: 127 coffer panels, 127 coffer recess shadows, 221 bevelled ceiling trim profiles, 54 ceiling grid beams, 40 crown moldings, 31 medallions, 31 light canopies, 31 light-fixture trim rings, 31 warm glass fixture domes, 40 ceiling vent grilles, and 40 ceiling material-variation panels across the chambers, galleries, public rooms, and generic office/support zones
- 347 public floor-finish/detail records for 72 marble/tile joints, 52 marble vein decals, 52 floor border strips, 24 carpet pile-variation decals, 16 carpet borders, 16 threshold tarnish decals, 8 public threshold slabs, 12 floor medallions, 10 floor-wear bands, 24 floor-wear scuff patches, 7 public room outline inlays, 10 public room axis inlays, and 44 public column footprint markers across public rooms, chamber approaches, galleries, and generic office/support zones
- 191 public surface-aging detail records for baseboard dust shadows, wall-corner grime streaks, threshold dirt tracks, desk edge wear patches, chair leather scuff patches, gallery seat rub shadows, and brass tarnish patches across public rooms, chamber approaches, galleries, and generic office/support zones
- 547 public-art visuals across statues, 35 records each for statue plinth, torso, head, plaque, base-profile, pose-variant, accessory, and surface-detail markers, 8 named Rotunda historical painting panels with title-plaque records, Rotunda frieze panels, hall art, historic chamber art, portrait panels, 56 art-frame inner-bevel records, 56 canvas tone-patch records, and 56 art label-plaque records; 63 Unreal-spawnable public light fixtures; 384 decorative light-fixture detail records including 63 bevelled mounts, 63 glass trim rings, 68 shade-rib records, and 63 finial details; 174 public accent-light candidates, capped to 144 Unreal-spawnable accent lights; and 11 wall-treatment records for public interior visual orientation
- Joint-session House Chamber visual zones: President podium, Speaker chair, Vice President chair, Senators/Senate guests, Cabinet, Supreme Court, diplomatic corps, press/camera pool, and member/guest overflow blocks
- 7 fictional non-graphic gameplay item pickup props: flagpole, nunchucks, bear spray, mace spray, throwable feces, knife, and handgun
- 5 flagpole banner visuals: American flag, two Trump 2024 campaign-style banners, a Save America campaign-style banner, and a Make America Great Again campaign-style banner
- 43 deterministic 4K procedural material texture sets, each with structured basecolor, normal, roughness, and ambient-occlusion PNG maps; high-impact sets include ashlar limestone, weathered ashlar limestone, painted dome panels, marble floor/wall, asphalt aggregate, concrete pitting, fabric/canvas weave, metal brushing, and wood plank styles

## Local Browser Viewer

The viewer is self-contained WebGL and does not require Three.js or a CDN. Because browsers block `fetch()` from `file://` pages, serve the package directory over local HTTP:

```bash
cd capitol_unreal_map
python3 -m http.server 8765
```

Then open:

```text
http://127.0.0.1:8765/viewer.html
```

The viewer reads `generated/data/material_texture_manifest.json` and can preview the generated texture sets with a lightweight PBR-style shader using basecolor, normal, roughness, and ambient-occlusion maps on the OBJ geometry. The default photoreal shader preview adds world-space patina variation, stronger filmic contrast, and atmospheric depth fade for a less-flat browser inspection pass. For browser performance, the full 4096px production maps are downsampled at load time to 1024px basecolor previews and 512px supporting-map previews; Unreal still imports the original 4K basecolor, normal, roughness, and ambient-occlusion maps.

Interior-only quick link:

```text
http://127.0.0.1:8765/viewer.html#interior-only
```

This route hides the exterior, roof/landmark, roads, and gameplay meshes in the browser viewer so the public interior schematic can be inspected without the building shell blocking the camera.

Full interior plan quick link:

```text
http://127.0.0.1:8765/viewer.html#interior-plan
```

This route keeps only the public interior schematic visible and moves the camera to a near-vertical, high plan-review view over the full public interior footprint.

Gameplay item quick link:

```text
http://127.0.0.1:8765/viewer.html#gameplay-items
```

The viewer also accepts `#game-play-items` as an alias for the same preview lane.

Grounds detail quick link:

```text
http://127.0.0.1:8765/viewer.html#grounds-details
```

Capitol facade/roof detail quick link:

```text
http://127.0.0.1:8765/viewer.html#facade-details
```

Roof detail quick link:

```text
http://127.0.0.1:8765/viewer.html#roof-details
```

Office/support detail quick link:

```text
http://127.0.0.1:8765/viewer.html#offices
```

Public signage detail quick link:

```text
http://127.0.0.1:8765/viewer.html#signage-details
```

Door hardware detail quick link:

```text
http://127.0.0.1:8765/viewer.html#door-details
```

Public furnishing detail quick link:

```text
http://127.0.0.1:8765/viewer.html#furnishing-details
```

Public art quick link:

```text
http://127.0.0.1:8765/viewer.html#public-art
```

Wall finish detail quick link:

```text
http://127.0.0.1:8765/viewer.html#wall-finish-details
```

Floor finish detail quick link:

```text
http://127.0.0.1:8765/viewer.html#floor-details
```

Ceiling/crown detail quick link:

```text
http://127.0.0.1:8765/viewer.html#ceiling-details
```

First-person walk quick link:

```text
http://127.0.0.1:8765/viewer.html#walk
```

This route hides the exterior, roof/landmark, roads, and gameplay meshes, starts a human-scale interior camera near the Rotunda, and keeps the public interior schematic visible for walk-through inspection in the browser.

Whole-map first-person walk quick link:

```text
http://127.0.0.1:8765/viewer.html#walk-map
```

This route keeps the public exterior buildings, roads, bike lanes, street markers, grounds, Capitol landmark mesh, and public interior schematic visible, starts at human eye height near the west front, and hides only the gameplay preview mesh.

Surface aging detail quick link:

```text
http://127.0.0.1:8765/viewer.html#surface-aging-details
```

Chamber top-down quick link:

```text
http://127.0.0.1:8765/viewer.html#chambers-top
```

This route hides the exterior, roof/landmark, roads, and gameplay meshes in the browser viewer so the public House and Senate chamber schematic can be inspected from a high plan-review camera.

House Chamber plan quick link:

```text
http://127.0.0.1:8765/viewer.html#house-plan
```

Senate Chamber plan quick link:

```text
http://127.0.0.1:8765/viewer.html#senate-plan
```

Public chamber role-zone quick link:

```text
http://127.0.0.1:8765/viewer.html#role-zones
```

House public gallery quick link:

```text
http://127.0.0.1:8765/viewer.html#house-gallery
```

Senate public gallery quick link:

```text
http://127.0.0.1:8765/viewer.html#senate-gallery
```

These routes keep only the public interior schematic visible, move the camera to a near-vertical plan-review view over the selected chamber or gallery, and filter labels to the selected public chamber/generic role-zone layer. The role-zone route is non-person-specific and uses only generic public seating/role blocks.

The viewer can toggle:

- surrounding buildings
- roads, bike lanes, traffic signals, crossing markers, and streetscape props
- public grounds details
- Capitol visual details, facade details, and public approach furniture
- public interior schematic
- gameplay item props
- PBR texture preview
- photoreal shader preview
- labels

Viewer presets include overview, Capitol exterior, roads, public grounds, public grounds details, Capitol facade/roof details, building-height audit, roof-only detail inspection, public interior, interior-only cutaway, full public-interior plan review, first-person whole-map walk inspection, first-person public-interior walk inspection, Rotunda, House Chamber, Senate Chamber, joint-session House Chamber, all-chambers top-down inspection, House/Senate chamber plan inspection, public chamber role-zone inspection, House/Senate public gallery inspection, public office/support details, public signage details, door hardware details, public furnishing details, public art details, wall finish details, floor finish details, public surface-aging details, ceiling/crown details, and gameplay item preview views. The label search and category filter can focus the camera on matching public spaces, chamber labels, seating labels, chamber detail labels, public chamber role-overlay labels, circulation detail labels, grounds detail labels, facade detail labels, height-audit labels, height-review targets, roof detail labels, office zones, office detail labels, signage detail labels, door detail labels, furnishing detail labels, public art labels, wall finish detail labels, floor detail labels, public surface-aging detail labels, ceiling detail labels, gameplay item labels, streets, or named surrounding buildings.

Controls: orbit mode uses drag, mouse wheel, and shift-drag. Walk modes use click-to-lock mouse look, WASD or arrow-key movement, Shift for faster movement, Q/E for bounded height adjustment, Esc to release the mouse, and a walk HUD with current mode, eye height, speed, position, and reset-to-start control.

## Unreal Import

You can open `CapitolMap.uproject` directly in Unreal 5.8 or run the import script from another Unreal 5.8 project.

1. Open your Unreal 5.8 project.
2. Enable editor scripting/Python support if it is not already enabled.
3. Run `capitol_unreal_map/unreal/import_capitol_map.py` from Unreal Editor with `Tools > Execute Python Script...`.
4. The script creates or opens `/Game/CapitolMap/Maps/CapitolMap_Level`.
5. The script imports meshes into `/Game/CapitolMap/Generated`.
6. The script imports generated texture PNGs into `/Game/CapitolMap/Textures`.
7. The script creates or updates realism materials in `/Game/CapitolMap/Materials` from `unreal/material_realism_manifest.json`, configures imported basecolor/normal/roughness/ambient-occlusion texture assets with kind-specific sRGB, compression, texture-group, mip, filter, and sampler settings, wires generated texture samples from `generated/data/material_texture_manifest.json`, sets two-sided/tangent-space material flags for generated inspection meshes, applies high-precision static-mesh build settings for normals/tangents/lightmap UVs where Unreal exposes them, adds editor comments to generated material graphs, applies the `CapitolMap_PhotoRealPreview` lighting/post-process profile, and applies those materials to matching imported material slots.
8. The script clears previously generated `CapitolMap` actors in that level, then respawns mesh actors with collision/navigation settings, guarded Unreal environment helpers, interior lights, capped public accent lights, a capped set of exterior streetlight actors, labels, nine named public PlayerStart actors, a guarded DefaultPawn playtest helper at the public-interior walk start, camera viewpoints, 54 first-person `BlockingVolume` collision proxies under `CapitolMap/Collision`, and a broad `NavMeshBoundsVolume` for first-person/pawn testing.
9. The script saves the current level when the Unreal editor API allows it.
10. The script writes `generated/data/unreal_import_report.json` with the generated map path, imported asset paths, material asset paths, texture asset paths, material texture bindings/features, material graph features, environment setup, photoreal preview profile, first-person collision/navigation/playtest setup, collision proxy setup/coverage groups, interior-inspection visibility tags, public schematic inspection workflows, and metadata counts.

The OBJ vertices are already authored in centimeters, so import scale should remain `1.0`. OBJ/static mesh import is the primary compatibility path for this package.

## Photorealism Direction

The current package is still a procedural public-data blockout with many detail markers, so it will read boxy from close gameplay views. The Unreal importer now applies a photoreal-readiness pass with generated 4K PBR-style material maps, high-precision UVs/tangents, recomputed/weighted normals, lightmap UV generation, Nanite enablement, guarded lighting/post-process setup, a named `CapitolMap_PhotoRealPreview` profile for sun temperature/source angle, contact shadows, reflection capture brightness, fog, bloom, ambient occlusion, filmic response, and bevelled public chamber desk/chair geometry. Actual photoreal results require replacing the highest-visibility blockout pieces with sculpted modular meshes and licensed or scanned PBR texture sources for limestone, bronze, asphalt, glass, carpet, and wood.

For Unreal full-interior inspection, use `CapitolMap_Camera_Interior_Cutaway` and hide actors tagged `CapitolMap_HideForInteriorCutaway`. The public interior mesh is tagged `CapitolMap_VisibleForInteriorCutaway`, so it remains visible while exterior, roof/landmark, roads, and gameplay preview meshes are hidden.

For Unreal full-interior top-down inspection, use `CapitolMap_Camera_PublicInterior_TopDown` with the same `CapitolMap_HideForInteriorCutaway` hidden actors.

For Unreal first-person whole-map inspection, use `CapitolMap_PlayerStart_WestFront` or `CapitolMap_Camera_WestFront_FirstPerson`. The importer adds public west/east plaza proxies, west/east axial grounds-walk and north/south connector walkable proxies, plus public approach road, sidewalk, and bike-lane inspection surfaces so public exterior routes can be checked at human scale.

For Unreal first-person public-interior inspection, use `CapitolMap_PlayerStart_PublicInteriorWalk`, `CapitolMap_PlayerStart_Rotunda`, `CapitolMap_PlayerStart_HouseChamber`, `CapitolMap_PlayerStart_SenateChamber`, `CapitolMap_PlayerStart_HouseGallery`, `CapitolMap_PlayerStart_SenateGallery`, `CapitolMap_PlayerStart_HouseOfficeWest`, `CapitolMap_PlayerStart_SenateOfficeEast`, the auto-possessed `CapitolMap_Playtest_DefaultPawn`, or the `CapitolMap_Camera_PublicInteriorWalk` camera marker. `Config/DefaultInput.ini` pins DefaultPawn controls for immediate Play-in-Editor inspection: WASD/arrow movement, mouse look, Q/E or LeftControl/SpaceBar vertical movement, and left/right-stick gamepad movement/look. The importer adds public schematic floor proxies for the Rotunda, chambers, galleries, Statuary Hall, Old Senate Chamber, public approach/orientation zones, and generic office/support zones, plus generic public chamber seating, rostrum/dais, gallery bench, pedestal/display, and support-furniture blocker proxies so immediate playtesting has broad walkable coverage without walking through the densest schematic furniture.

For Unreal chamber inspection, use `CapitolMap_Camera_Chambers_TopDown` and hide actors in `CapitolMap/Meshes/HideForInteriorTopDown` or tagged `CapitolMap_HideForInteriorTopDown`. The public interior mesh is foldered under `CapitolMap/Meshes/InteriorTopDownVisible` and tagged `CapitolMap_VisibleForInteriorTopDown`. For generic public seating/role overlays, use `CapitolMap_Camera_ChamberRoleZones_TopDown`; for gallery inspection use `CapitolMap_Camera_HouseGallery_TopDown` or `CapitolMap_Camera_SenateGallery_TopDown`.

The Unreal import report also writes an `inspection_workflows` table that maps the browser inspection routes (`#interior-only`, `#interior-plan`, `#chambers-top`, `#house-plan`, `#senate-plan`, `#role-zones`, `#house-gallery`, and `#senate-gallery`) to the matching Unreal camera labels, visible mesh, label filter, and hide/visible actor tags. These workflows are public schematic and non-person-specific.

`Config/DefaultEngine.ini` points both `EditorStartupMap` and `GameDefaultMap` at `/Game/CapitolMap/Maps/CapitolMap_Level`; run the import script once before relying on those startup-map defaults in a fresh checkout.

## Realism Pass

The current realism pass uses deterministic 4K structured procedural texture maps plus material settings. `scripts/generate_material_textures.py` writes tileable 4096x4096 basecolor, normal, roughness, and ambient-occlusion PNGs under `generated/textures/`, with material-specific rules for ashlar limestone block joints, weathering streaks, marble slab/floor veining, painted dome panel seams, wood plank seams/grain/knots, paver joints, asphalt aggregate/cracks/tar breakup, concrete pitting/trowel variation, textile/canvas fiber breakup, metal brushing/scratches/tarnish variation, micro pores, mineral flecks, stain masks, height-derived roughness, and cavity/contact-darkening ambient occlusion. It also writes `generated/data/material_texture_manifest.json` with photoreal-readiness feature markers. `unreal/material_realism_manifest.json` defines base color fallback, roughness, metallic, specular, opacity, and clear-coat values for all generated MTL materials, including 25 clear-coat material specs for glass, polished wood, leather, brass/gold/bronze trim, light fixtures, traffic lenses, and other close-up reflective surfaces.

The Unreal import script imports those PNGs into `/Game/CapitolMap/Textures`, configures basecolor maps as sRGB and normal/roughness/ambient-occlusion maps as linear texture data with kind-specific compression/sampler settings, creates `M_*` materials under `/Game/CapitolMap/Materials`, wires basecolor/normal/roughness/ambient-occlusion texture samples into the material graph when the editor API supports it, applies optional clear-coat and clear-coat roughness inputs for close-up reflective materials, sets generated materials to two-sided/tangent-space-normal mode for inspection visibility, adds an editor comment describing the generated PBR setup, and assigns the materials to imported static mesh slots when the slot names match the original MTL names. The generated OBJ UVs use a simple planar projection with a 3-meter tile scale so stone, asphalt, carpet, wood, canvas, and metal textures have deterministic coordinates in Unreal. The importer also spawns guarded environment actors for sun, skylight, sky atmosphere, fog, reflection capture, and post-process exposure where the Unreal Python API exposes them, plus metadata-driven interior lights, capped public accent lights derived from chamber/circulation/furnishing fixture-detail records, capped public streetlights, authored public grounds walk lamps, and public Capitol facade entry/uplight fixtures.

`Config/DefaultEngine.ini` enables the real-time rendering features expected for the strongest Unreal preview of this procedural package: Lumen-style dynamic global illumination and reflections, mesh distance fields, Nanite, virtual shadow maps, contact shadows, TSR anti-aliasing, high tonemapper quality, ambient occlusion, stronger reflection capture resolution, 16x anisotropic filtering, texture streaming, and an 8192 MB streaming pool for the 4K material maps. Motion blur and auto exposure stay disabled so geometry/material comparisons remain stable while iterating.

The current mesh-detail pass adds surrounding-building facade windows with sills, lintels, mullions, recess shadows, inner sash frames, pane highlights, floor bands, and facade pilasters driven by explicit, level-derived, DCGIS rooftop/ground-delta, and footprint/type/area-estimated building heights; roofline caps, cornice bands, parapet coping, parapet inner-shadow strips, inset roof surfaces, roof gravel patches, skylight strips, roof penthouses, penthouse louvers, corner piers, public-entry markers, entry frames, entry transoms, entry thresholds, pull bars, center seams, awnings, wall signs, rooftop detail blocks, roof-access hatches, rooftop mechanical units, rooftop louvers, pipe stacks, vent caps, roof conduits, public streetscape props, traffic-signal heads, traffic-signal mast arms/backplates/louver hoods, pedestrian signal markers, public regulatory stop signs, public bike-route signs, public crosswalk-ahead signs, generic public DCGIS traffic-control/overhead sign props, source-backed DCGIS hydrant/tree/utility/miscellaneous fixture props, source-backed DCGIS curb/sidewalk/road edge and surface-patch props, curb-paint segments, road asphalt patches, crack-sealant strips, manhole-cover visuals, storm-drain grates and curb inlets, public utility boxes, public news/vendor boxes, crosswalk striping, crosswalk ladder markings, sidewalk grime strips, sidewalk stain patches, curb gutter-grime strips, bike-lane surface scuffs, crosswalk paint-wear patches, road tire-wear bands, tree planters, public stop bars, lane arrows, bike symbols, curb-ramp visuals, tactile warning surfaces, sidewalk expansion joints, bike-lane delineator posts/base plates, wayfinding signs, streetlight flanged bases/collars/hoods/lens trims, street-name sign text strokes, public bike racks, public trash/recycling receptacles, bus-stop shelter benches/route panels, hydrant markers, authored public grounds details, hedges, path-edge stones, grounds benches, ornamental planting clusters, Capitol facade windows, window recess-shadow geometry, inner sash frames, pane highlights, bevelled public massing blocks, attic-window bands, stone window surrounds, arched window trim, facade window keystones, window mullions, ashlar stone courses, vertical stone joints, close-range mortar shadow grooves, staggered masonry joints, chipped limestone blocks, facade panel bevel strips, facade weathering stains, limestone discoloration patches, sill runoff stains, base grime bands, stepped pavilion massing, pavilion setback reveals, facade shadow returns, facade water-table bands, cornice shadow reveals, recessed facade shadow panels, portico arcade shadow bays, facade corner quoin blocks, portico inter-column shadows, portico architrave/frieze/cornice bands, portico frieze panel details, pediment raking-cornice blocks, portico side cornice returns, portico soffit coffers, terrace retaining walls, lower terrace stair/riser bands, public terrace landing slabs, plaza paver joints, plaza expansion seams, plaza stone tone patches, public plaza drain slots, public door surrounds, revolving-door glass drums, circular tracks, radial wing panels, perimeter mullions, side-lites, public facade pilasters, exterior column plinths, exterior column bases/capitals/fluting, individual column fluting-groove records, base reed-ring details, capital abacus details, generic column capital leaf/volute blocks, column base chip details, public stair treads, public step-edge chip shadows, public step grime seams, worn plaza/step patches, approach handrails, dentil courses, individual dentil blocks, cornice brackets, generic pediment relief blocks, pediment rosette/garland relief accents, roof balustrades, roof articulation volumes, roof monitor ridges, roof surface joints, roof capstone blocks, roof slope-skirt panels, parapet corner piers, roof parapet shadow gaps, public roof drain/scupper visuals, generic non-operational roof vent housings, wing transition blocks, courtyard recess shadow planes, roof dormers, skylight strips, dome balustrade posts, dome vertical ribs, dome shell panel frames, dome drum window trim and glass panes, dome drum spandrel panels, dome shell rain streaks and panel shadow seams, dome lateral bands, lantern windows, lantern glass panes, lantern columns, lantern balustrade, entry lamps, facade sconces, facade uplights, bollards, benches, public Rotunda floor inlays, perimeter column bases/capitals, column fluting-groove overlays, upper coffer panels, arch portals, arch spandrel inlays, arch keystone blocks, balustrade ring/posts, oculus trim ring, public statue pedestal bases/plaques, public statue plinth/torso/head/plaque silhouettes plus base-profile, pose-variant, accessory, and surface-wear markers, public corridor pilasters, public corridor sconces, portal transoms, portal opening-shadow panels, portal jamb returns, public ceiling coffer panels, crown moldings, ceiling grid beams, medallions, light canopies, light-fixture trim rings, warm glass fixture domes, decorative light-fixture chains/armatures/canopies/glass-shade details, ceiling vent grilles, ceiling material-variation panels, public floor tile joints, marble vein decals, floor borders, carpet borders, carpet pile variation decals, threshold slabs, threshold tarnish decals, threshold marble inserts, threshold brass edges, transition light pools, floor medallions, floor-wear bands, floor-wear scuff patches, public room outline inlays, public room axis inlays, public column footprint markers, public room-identification signs, public directional signs, gallery markers, chamber-role signs, map kiosks, sign typography strokes, map-kiosk route-line glyphs, double-door panels, pull bars, hinge plates, kick plates, transoms, side lites, public benches, bench slats, bench arm rests, display cases, display-case edge trims, display-case object silhouettes, display-case light strips, display-case label plaques, information lecterns, lectern text-line glyphs, receptacles, receptacle sorting labels, plant urns, plant urn rims, leaf clusters, queue posts, raised wainscot frames, decorative wall panels, wall material-variation panels, baseboard grime decals, wall patina decals, wainscot rub-mark decals, picture rails, public architrave trims, upper wall panel frames, baseboards, wall pilasters, public office door panels, office thresholds, generic public plaques, shared support tables, generic office partition panels/top caps, desk-surface insets, monitor stands, desk cable grommets, cable trays, wall outlet/data plates, chair backs, chair-arm pairs, bookcases, storage cabinets, public chamber carpet runners, carpet binding strips, carpet weave bands, carpet edge fringe, worn carpet paths, row shadow strips, carpet medallions, gallery tread nosing, rostrum backdrop trim inlays, gallery benches with slats/back panels/support brackets, gallery dividers, gallery rail top caps/rosettes, balcony fascia, public lecterns, lectern reading lamps, work tables, work-table reading lamps, rostrum desks, rostrum desk front panels/brass pulls, generic rostrum seal medallions, chamber flag cloth/fold/stripe/canton markers, aisle step lights, row-marker plaques, rostrum microphone clusters, gallery stanchions, gallery support columns, public display boards, desk surface markers, generic desk-surface insets, generic desk edge trims, desk wood-grain/varnish markers, generic document stacks, generic desk microphone markers, generic nameplate strips, chair-arm pairs, chair arm-wear markers, chair cushions, chair-cushion piping, chair leather-wear patches, chair-back insets/scuffs, row modesty panels, named Rotunda historical painting markers/title plaques, additional public-art panels, art-frame bevels/canvas tone patches/label plaques, visible public light fixtures, and transition exhibit-case/light placement. The `StoneGrimeOverlay` material adds translucent public stone grime, runoff, discoloration, patina, chipped-edge overlays, close-range mortar shadows, approach-step grime seams, roof gravel patches, and column base-chip overlays using the existing weathered-limestone texture set. The height audit now prioritizes Jan 6 / late-2020 target-era sources; present-day or 2024+ 3D-building/lidar data may be used only as clearly marked non-era visual reference, not as a silent geometry replacement. The next visual-fidelity step is to replace procedural texture maps with curated real PBR texture sources where licensing permits, use clearly marked reference-only modern 3D/lidar sources only when they help visual modeling without changing target-era footprints, and add sculpted modular meshes for the closest inspection views.

The public circulation detail pass also adds close-range wall fixtures: public directory boards, abstract directory line glyphs, wall clocks, generic public safety cabinets, emergency light blocks, and wall switch/outlet plates.

The gameplay item pass is fictional and non-graphic. It adds abstract pickup/display props and gameplay metadata only; it does not model historical placement, public-safety guidance, or real-world weapon use or construction. Flagpole banner visuals are simple color-blocked game props, not exact merchandise replicas.

Generated camera viewpoints:

- `CapitolMap_Camera_Overview`
- `CapitolMap_Camera_WestFront_FirstPerson`
- `CapitolMap_Camera_PublicInteriorWalk`
- `CapitolMap_Camera_WestGrounds`
- `CapitolMap_Camera_Rotunda`
- `CapitolMap_Camera_HouseChamber_JointSession`
- `CapitolMap_Camera_SenateChamber`
- `CapitolMap_Camera_Chambers_TopDown`
- `CapitolMap_Camera_HouseChamber_TopDown`
- `CapitolMap_Camera_SenateChamber_TopDown`
- `CapitolMap_Camera_ChamberRoleZones_TopDown`
- `CapitolMap_Camera_HouseGallery_TopDown`
- `CapitolMap_Camera_SenateGallery_TopDown`
- `CapitolMap_Camera_Interior_Cutaway`
- `CapitolMap_Camera_PublicInterior_TopDown`
- `CapitolMap_Camera_GameplayItems`

Those viewpoints are also written into `generated/data/capitol_scene_metadata.json` so downstream tools can reuse the same inspection positions.

## Coordinate System

- Origin: approximate center of the U.S. Capitol, latitude `38.889939`, longitude `-77.009051`
- X: east, in meters before OBJ export
- Y: north, in meters before OBJ export
- Z: up, in meters before OBJ export
- OBJ output: centimeters for Unreal compatibility

## Interior Scope

The interior is intentionally a public schematic, not an exact restricted floor plan.

Included:

- Rotunda, modeled as a 96-foot-diameter public reference circle
- Rotunda wall ring, floor trim, center medallion, radial floor inlays, perimeter columns with fluting-groove overlays, public arch portals with spandrel/keystone ornament, upper coffer panels, upper balustrade ring, and statue pedestal-base details
- Public room-identification signs, directional signs, gallery markers, chamber-role markers, generic office/support zone signs, orientation map kiosks, abstract sign-typography strokes, and map-kiosk route-line glyphs
- Public doorway panels, pull bars, hinges, kick plates, transoms, header trim, and side-lite panels at schematic public transitions
- Public benches with slats/arms, display cases with edge trims/object silhouettes, information lecterns with text-line glyphs, receptacles, plant urns with rim/leaf details, queue posts, and rope segments as generic public fixtures
- Raised public wall-finish details: bevelled baseboards, picture rails, wainscot frames, decorative wall panels, upper wall panel frames, pilasters, and public architrave trims
- Public coffered ceiling, crown molding, medallion, light-canopy, light-fixture trim/glass-dome, and ceiling vent-grille details in major public interior zones
- Public floor borders, marble/tile joints, threshold slabs, carpet borders, floor medallions, floor-wear bands/scuff patches, public room outline inlays, public room axis inlays, and public column footprint markers in major public interior zones
- National Statuary Hall
- Old Senate Chamber
- Crypt marker
- House Chamber and Senate Chamber
- House and Senate galleries
- generic office/support zones
- 60 generic office/support cells with desks, monitors/stands, keyboards, paper stacks, task lamps, chairs, chair backs/arms/swivel bases, bookcases, storage cabinets, partitions/top caps, desk cable grommets, cable trays, wall outlet/data plates, generic door panels, thresholds, public plaques, shared support tables, and public corridor bands
- generic House member seating and Senate desk positions
- aggregate public seating sections for House member floor seating, House gallery, Senate desk blocks, Senate gallery, rostrum/presiding-officer areas, and joint-session role zones
- House Chamber joint-session layout for public ceremonial addresses, including President podium, Speaker and Vice President positions, and public generic seating zones for Senators, Cabinet, Supreme Court, diplomatic corps, press, members, and guests

Not included:

- security posts, secure circulation, evacuation routes, tunnels, or restricted service spaces
- private office-by-person assignments
- current senator-by-desk or representative-by-seat assignments
- nonpublic room numbers or operational details

House floor seating is modeled as 448 generic seats. Senate seating is modeled as 100 generic desks. The `seating_sections` metadata summarizes where major public roles sit without encoding person-by-person assignments, and the chamber mesh includes visible public role-zone overlays, boundaries, labels, and count ticks for top-down inspection. The joint-session layout is a public visual arrangement, not an operational seating chart. Occupant assignments are deliberately not encoded because they change and should be sourced only from approved public references if needed.

## Sources

- Exterior map geometry target: historical OpenStreetMap extract for `2021-01-06T17:00:00Z` using Overpass historical date queries. OSM data is available under the Open Database License.
- Historical source fetch: `python3 scripts/fetch_osm_historical_capitol.py` from this directory writes `source_data/capitol_osm_overpass_2021-01-06.json`. For a strict late-2020 snapshot, run `python3 scripts/fetch_osm_historical_capitol.py --date 2020-12-31T23:59:59Z --output source_data/capitol_osm_overpass_2020-12-31.json`.
- Present-day OSM extracts are fallback/reference inputs only and should not silently replace the Jan 6 / late-2020 target-era geometry.
- Interior schematic: public information about the Capitol's major spaces from Architect of the Capitol and public visitor information, reduced to a non-sensitive schematic.

## Next Fidelity Pass

The current direction is Unreal 5.8, first-person scale, most-compatible static mesh import, and public-only interior/seating detail. The next pass should improve:

- reference-modeled close-range facade modules beyond the current procedural arch trim, keystone, grime, bracket, pilaster, doorway, dentil, column-groove, frieze-panel, and pediment-relief pass
- curated real PBR texture source replacement where licensing permits
- higher-fidelity sculpted modular meshes for stone ornament, gallery surfaces, labels, and worn floor/furniture surfaces
