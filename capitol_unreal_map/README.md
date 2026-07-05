# U.S. Capitol Unreal Map Package

This package is a first public-data pass at a U.S. Capitol map for Unreal Engine 5.8, authored at first-person centimeter scale.

## Quick Links

- Local viewer: `http://127.0.0.1:8765/viewer.html`
- Gameplay item preview: `http://127.0.0.1:8765/viewer.html#gameplay-items`
- Grounds detail preview: `http://127.0.0.1:8765/viewer.html#grounds-details`
- Capitol facade/roof detail preview: `http://127.0.0.1:8765/viewer.html#facade-details`
- Office/support detail preview: `http://127.0.0.1:8765/viewer.html#offices`
- Public signage detail preview: `http://127.0.0.1:8765/viewer.html#signage-details`
- Door hardware detail preview: `http://127.0.0.1:8765/viewer.html#door-details`
- Public furnishing detail preview: `http://127.0.0.1:8765/viewer.html#furnishing-details`
- Wall finish detail preview: `http://127.0.0.1:8765/viewer.html#wall-finish-details`
- Floor finish detail preview: `http://127.0.0.1:8765/viewer.html#floor-details`
- Ceiling/crown detail preview: `http://127.0.0.1:8765/viewer.html#ceiling-details`
- Chamber top-down preview: `http://127.0.0.1:8765/viewer.html#chambers-top`
- Texture preview: `http://127.0.0.1:8765/texture_preview.html`

It contains:

- exterior buildings, roads, bike-lane features, crossings, traffic-signal markers, public streetscape props, public bike racks, public trash/recycling receptacles, bus-stop shelter markers, hydrant markers, and authored public grounds details derived from OpenStreetMap context plus schematic visual markers
- pedestrian paths, curb edges, sidewalks where side-specific sidewalk tags exist, and lane-edge markings derived from the same public OSM extract
- a public-only Capitol interior schematic with major spaces, generic office/support zones, Rotunda architectural detail records, public room/galleries/wayfinding signage, public doorway panels and hardware, public benches/display cases/lecterns/receptacles/plant urns, raised wall-finish/wainscot/pilaster trim, public ceiling/coffer/crown-trim records, public floor-finish records, House Chamber, Senate Chamber, galleries, generic chamber seating, public-art markers, visible lighting/wall-treatment details, and a joint-session House Chamber visual layout
- public-facing Capitol visual details including an authored Capitol landmark mesh, approximate revolving-door assemblies, layered pavilions, articulated roof/courtyard recesses, dormers, skylight strips, pediments, stone window surrounds, window mullions, ashlar stone courses, vertical stone joints, facade weathering stains, roof surface joints, worn plaza/step patches, door surrounds, pilasters, stair treads, approach handrails, dentil/cornice courses, cornice brackets, roof balustrades, dome ribs, dome bands, dome shell panel frames, dome drum trim/spandrels, lantern columns/balustrade, entry lamps, facade uplights, bollards, and benches
- fictional, non-graphic gameplay item pickup props in a separate preview lane: flagpole with American flag and campaign-style banner variants, nunchucks, bear spray, mace spray, throwable feces, knife, and handgun
- Unreal-friendly OBJ/MTL meshes in centimeter units
- JSON metadata for labels, source provenance, coordinates, rooms, seating records, and gameplay item records
- shared camera/viewpoint metadata for browser and Unreal inspection
- a Unreal material realism manifest for PBR-style roughness, metallic, specular, opacity, and base-color setup
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
- `generated/textures/*_{basecolor,normal,roughness}.png`
- `unreal/material_realism_manifest.json`
- `unreal/import_capitol_map.py`
- `viewer.html`

The OBJ meshes include generated `vt` texture coordinates, so Unreal material texture samples have UVs to read instead of relying on importer-generated defaults.

## Regenerate

From the repository root:

```bash
python3 capitol_unreal_map/scripts/generate_material_textures.py
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
- every generated MTL material has generated basecolor, normal, and roughness texture bindings
- every generated texture file is a valid PNG whose dimensions match `material_texture_manifest.json` and whose minimum production dimension is 4096px
- the expected exterior counts, pedestrian paths, curb records, lane-edge markings, public streetscape props, public grounds details, Capitol facade/furniture details, public interior rooms, generic office cells, House seats, Senate desks, public seating sections, joint-session zones, public Rotunda, signage, door-hardware, furnishing, wall-finish, floor, and ceiling detail layers, fictional gameplay item props, and generated viewpoints are present
- the Unreal import script still references every generated mesh, expected destination path, import helper, label category, World Outliner folder, first-person setup marker, and import-report key
- the Unreal project config still enables the scripting plugins, Nanite/navigation settings, and generated Capitol map editor/game defaults

It writes `generated/data/capitol_package_validation.json`, including an `unreal_importer` contract section. This proves local package consistency; the final editor check is still to run `unreal/import_capitol_map.py` inside Unreal 5.8.

The current validation report counts 1,052,342 generated texture coordinates across the five OBJ meshes.

The current texture validation report counts 43 generated texture sets, 129 PNG texture files, and a minimum generated texture dimension of 4096px.

The current generated build contains:

- 2,524 surrounding building footprints; the OSM `United States Capitol` footprint is intentionally skipped and replaced by the authored Capitol landmark mesh to avoid concave-roof triangulation artifacts
- 1,182 surrounding-building visual detail records, including nearby facade windows, roofline caps, cornice bands, public-entry markers, awnings, wall signs, rooftop detail blocks, and rooftop mechanical units
- 3,528 roads/paths
- 445 bike-lane/cycleway features
- 2,533 pedestrian path/footway records
- 1,216 curb edge records
- 608 lane-edge marking records
- 880 street markers/crossings/traffic signals
- 926 public streetscape prop records, including schematic streetlights, street-name signs, traffic-signal heads, tree planters, public stop bars, lane arrows, bike symbols, curb-ramp visuals, wayfinding signs, 12 public bike racks, 16 public trash/recycling receptacles, 8 public bus-stop shelter markers, and 16 public hydrant markers; the mesh also includes crosswalk striping and bike-lane marker posts
- 169 authored public grounds detail records, including lawn panels, public walks, reflecting-pool marker, pool coping, formal planting beds, tree allees, 18 Unreal-spawnable public walk lamps, low plaza walls, 12 hedges, 16 path-edge stones, 16 grounds benches, and 24 ornamental planting clusters
- Capitol visual massing details including dome, lantern, porticos, columns, steps, plaza, grounds, public-facing revolving-door visuals, facade windows, stone window surrounds, window mullions, public ashlar stone courses, vertical stone joints, facade weathering stains, roof surface joints, worn plaza/step patches, public door surrounds, public facade pilasters, stair tread records, approach handrails, dentil/cornice courses, cornice brackets, roof balustrades, articulated roof volumes, wing transition blocks, courtyard/recess shadow planes, dormers, skylight strips, dome ribs, dome shell panel frames, dome drum window trim/spandrel panels, dome lateral bands, lantern columns/balustrade, pediment relief panels, entry lamps, facade uplights, bollards, and benches
- 1,710 Capitol facade/furniture detail records, including 266 facade window mullions, 116 cornice brackets, 96 dome shell panel frames, 90 facade weathering stain records, 70 facade ashlar course records, 68 vertical stone joint records, 55 roof surface joint records, 32 worn plaza/step patch records, 32 public roof dormers, 24 facade uplights, 16 public entry lamps, 16 dome drum spandrel panels, 16 lantern columns, 10 roof articulation volumes, 8 wing transition blocks, 8 courtyard/recess shadows, 8 skylight strips, 12 public door surrounds, and 8 public approach handrails
- 60 generic public office/support visual cells
- 492 public office/support detail records, including 60 generic door panels, 60 door thresholds, 60 generic public plaques, 60 desk-surface insets, 60 chair backs, 60 chair-arm pairs, 60 bookcases, 60 storage cabinets, 8 shared support tables, and 4 public corridor bands
- 448 generic House floor seats
- 100 generic Senate desks
- 16 public seating-section records: 7 regular-session House/Senate chamber sections and 9 joint-session role zones
- 1,366 public chamber detail records for House/Senate rails, dais steps, rostrum desks, public lecterns, work tables, gallery rails, gallery benches, gallery dividers, balcony fascia, aisle edge markers, aisle step lights, row-marker plaques, rostrum microphone clusters, public gallery stanchions, desk arc markers, desk surface markers, generic desk-surface insets, chair-arm pairs, row modesty panels, backdrop panels, and flag standards
- 35 public circulation detail records for schematic corridor bands, door thresholds, room portal trim, orientation signs, and floor inlays between major public spaces
- 53 public signage detail records for room-identification signs, directional signs, visitor-gallery markers, chamber-role markers, generic office-zone signs, and public orientation map kiosks
- 192 public door-hardware detail records: 24 double-door panels, 24 pull bars, 72 hinge plates, 24 kick plates, 12 transom panels, 12 header trims, and 24 side-lite panels at public/schematic doorway transitions
- 130 public furnishing/fixture detail records: 24 benches, 16 display cases, 10 information lecterns, 16 receptacles, 20 plant urns, 24 public queue posts, and 20 rope segments
- 780 public wall-finish detail records: 44 baseboards, 326 raised wainscot frames, 172 upper wall panel frames, and 238 wall pilasters across public rooms, chambers, galleries, and generic office/support zones
- 151 public Rotunda architectural detail records for wall ring, floor trim, center medallion, 16 radial floor inlays, 16 perimeter columns with base/capital blocks, 32 upper coffer panels, 4 public arch portals, upper balustrade ring with 32 posts, oculus trim ring, 7 public statue pedestal bases, and 7 pedestal plaques
- 283 public ceiling detail records for coffer panels, ceiling grid beams, crown molding, medallions, and light canopies across the chambers, galleries, public rooms, and generic office/support zones
- 160 public floor-finish detail records for marble/tile joints, floor border strips, carpet borders, public threshold slabs, and medallions across public rooms, chamber approaches, galleries, and generic office/support zones
- 91 public-art visuals across statues, Rotunda painting/frieze panels, hall art, historic chamber art, and portrait panels; 55 public light fixtures; and 11 wall-treatment records for public interior visual orientation
- Joint-session House Chamber visual zones: President podium, Speaker chair, Vice President chair, Senators/Senate guests, Cabinet, Supreme Court, diplomatic corps, press/camera pool, and member/guest overflow blocks
- 7 fictional non-graphic gameplay item pickup props: flagpole, nunchucks, bear spray, mace spray, throwable feces, knife, and handgun
- 5 flagpole banner visuals: American flag, two Trump 2024 campaign-style banners, a Save America campaign-style banner, and a Make America Great Again campaign-style banner
- 43 deterministic 4K procedural material texture sets, each with basecolor, normal, and roughness PNG maps

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

Chamber top-down quick link:

```text
http://127.0.0.1:8765/viewer.html#chambers-top
```

This route hides the exterior, roof/landmark, roads, and gameplay meshes in the browser viewer so the public House and Senate chamber schematic can be inspected from above.

The viewer can toggle:

- surrounding buildings
- roads, bike lanes, traffic signals, crossing markers, and streetscape props
- public grounds details
- Capitol visual details, facade details, and public approach furniture
- public interior schematic
- gameplay item props
- labels

Viewer presets include overview, Capitol exterior, roads, public grounds, public grounds details, Capitol facade/roof details, public interior, Rotunda, House Chamber, Senate Chamber, joint-session House Chamber, top-down chamber inspection, public office/support details, public signage details, door hardware details, public furnishing details, wall finish details, floor finish details, ceiling/crown details, and gameplay item preview views. The label search and category filter can focus the camera on matching public spaces, chamber labels, seating labels, chamber detail labels, circulation detail labels, grounds detail labels, facade detail labels, office zones, office detail labels, signage detail labels, door detail labels, furnishing detail labels, wall finish detail labels, floor detail labels, ceiling detail labels, gameplay item labels, streets, or named surrounding buildings.

Controls: drag to orbit, mouse wheel to zoom, shift-drag to pan.

## Unreal Import

You can open `CapitolMap.uproject` directly in Unreal 5.8 or run the import script from another Unreal 5.8 project.

1. Open your Unreal 5.8 project.
2. Enable editor scripting/Python support if it is not already enabled.
3. Run `capitol_unreal_map/unreal/import_capitol_map.py` from Unreal Editor with `Tools > Execute Python Script...`.
4. The script creates or opens `/Game/CapitolMap/Maps/CapitolMap_Level`.
5. The script imports meshes into `/Game/CapitolMap/Generated`.
6. The script imports generated texture PNGs into `/Game/CapitolMap/Textures`.
7. The script creates or updates realism materials in `/Game/CapitolMap/Materials` from `unreal/material_realism_manifest.json`, wires generated basecolor/normal/roughness texture samples from `generated/data/material_texture_manifest.json`, and applies those materials to matching imported material slots.
8. The script clears previously generated `CapitolMap` actors in that level, then respawns mesh actors with collision/navigation settings, guarded Unreal environment helpers, interior lights, a capped set of exterior streetlight actors, labels, PlayerStart, a guarded DefaultPawn playtest helper, camera viewpoints, and a broad `NavMeshBoundsVolume` for first-person/pawn testing.
9. The script saves the current level when the Unreal editor API allows it.
10. The script writes `generated/data/unreal_import_report.json` with the generated map path, imported asset paths, material asset paths, texture asset paths, environment setup, first-person collision/navigation/playtest setup, and metadata counts.

The OBJ vertices are already authored in centimeters, so import scale should remain `1.0`. OBJ/static mesh import is the primary compatibility path for this package.

`Config/DefaultEngine.ini` points both `EditorStartupMap` and `GameDefaultMap` at `/Game/CapitolMap/Maps/CapitolMap_Level`; run the import script once before relying on those startup-map defaults in a fresh checkout.

## Realism Pass

The current realism pass uses deterministic 4K procedural texture maps plus material settings. `scripts/generate_material_textures.py` writes tileable 4096x4096 basecolor, normal, and roughness PNGs under `generated/textures/` and writes `generated/data/material_texture_manifest.json`. `unreal/material_realism_manifest.json` defines base color fallback, roughness, metallic, specular, and opacity values for all generated MTL materials.

The Unreal import script imports those PNGs into `/Game/CapitolMap/Textures`, creates `M_*` materials under `/Game/CapitolMap/Materials`, wires basecolor/normal/roughness texture samples into the material graph when the editor API supports it, and assigns the materials to imported static mesh slots when the slot names match the original MTL names. The generated OBJ UVs use a simple planar projection with a 3-meter tile scale so stone, asphalt, carpet, wood, canvas, and metal textures have deterministic coordinates in Unreal. The importer also spawns guarded environment actors for sun, skylight, sky atmosphere, fog, reflection capture, and post-process exposure where the Unreal Python API exposes them, plus metadata-driven interior lights, capped public streetlights, authored public grounds walk lamps, and public Capitol facade entry/uplight fixtures.

The current mesh-detail pass adds surrounding-building facade windows, roofline caps, cornice bands, public-entry markers, awnings, wall signs, rooftop detail blocks, rooftop mechanical units, public streetscape props, traffic-signal heads, crosswalk striping, tree planters, public stop bars, lane arrows, bike symbols, curb-ramp visuals, wayfinding signs, public bike racks, public trash/recycling receptacles, bus-stop shelter markers, hydrant markers, authored public grounds details, hedges, path-edge stones, grounds benches, ornamental planting clusters, Capitol facade windows, stone window surrounds, window mullions, ashlar stone courses, vertical stone joints, facade weathering stains, public door surrounds, public facade pilasters, public stair treads, worn plaza/step patches, approach handrails, dentil courses, cornice brackets, roof balustrades, roof articulation volumes, roof surface joints, wing transition blocks, courtyard recess shadow planes, roof dormers, skylight strips, dome balustrade posts, dome vertical ribs, dome shell panel frames, dome drum window trim, dome drum spandrel panels, dome lateral bands, lantern windows, lantern columns, lantern balustrade, entry lamps, facade uplights, bollards, benches, public Rotunda floor inlays, perimeter column bases/capitals, upper coffer panels, arch portals, balustrade ring/posts, oculus trim ring, public statue pedestal bases/plaques, public ceiling coffer panels, crown moldings, ceiling grid beams, medallions, light canopies, public floor tile joints, floor borders, carpet borders, threshold slabs, floor medallions, public room-identification signs, public directional signs, gallery markers, chamber-role signs, map kiosks, double-door panels, pull bars, hinge plates, kick plates, transoms, side lites, public benches, display cases, information lecterns, receptacles, plant urns, queue posts, raised wainscot frames, upper wall panel frames, baseboards, wall pilasters, public office door panels, office thresholds, generic public plaques, shared support tables, generic office desk-surface insets, chair backs, chair-arm pairs, bookcases, storage cabinets, public chamber gallery benches, gallery dividers, balcony fascia, public lecterns, work tables, rostrum desks, aisle step lights, row-marker plaques, rostrum microphone clusters, gallery stanchions, desk surface markers, generic desk-surface insets, chair-arm pairs, row modesty panels, additional public-art panels, and visible public light fixtures. The next visual-fidelity step is to replace procedural texture maps with curated real PBR texture sources where licensing permits and to add higher-fidelity modular meshes for public streetscape fixtures, facade ornament, and chamber furniture.

The gameplay item pass is fictional and non-graphic. It adds abstract pickup/display props and gameplay metadata only; it does not model historical placement, public-safety guidance, or real-world weapon use or construction. Flagpole banner visuals are simple color-blocked game props, not exact merchandise replicas.

Generated camera viewpoints:

- `CapitolMap_Camera_Overview`
- `CapitolMap_Camera_WestFront_FirstPerson`
- `CapitolMap_Camera_WestGrounds`
- `CapitolMap_Camera_Rotunda`
- `CapitolMap_Camera_HouseChamber_JointSession`
- `CapitolMap_Camera_SenateChamber`
- `CapitolMap_Camera_Chambers_TopDown`
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
- Rotunda wall ring, floor trim, center medallion, radial floor inlays, perimeter columns, public arch portals, upper coffer panels, upper balustrade ring, and statue pedestal-base details
- Public room-identification signs, directional signs, gallery markers, chamber-role markers, generic office/support zone signs, and orientation map kiosks
- Public doorway panels, pull bars, hinges, kick plates, transoms, header trim, and side-lite panels at schematic public transitions
- Public benches, display cases, information lecterns, receptacles, plant urns, queue posts, and rope segments as generic public fixtures
- Raised public wall-finish details: baseboards, wainscot frames, upper wall panel frames, and pilasters
- Public coffered ceiling, crown molding, medallion, and light-canopy details in major public interior zones
- Public floor borders, marble/tile joints, threshold slabs, carpet borders, and floor medallions in major public interior zones
- National Statuary Hall
- Old Senate Chamber
- Crypt marker
- House Chamber and Senate Chamber
- House and Senate galleries
- generic office/support zones
- 60 generic office/support cells with desks, chairs, chair backs/arms, bookcases, storage cabinets, partitions, generic door panels, thresholds, public plaques, shared support tables, and public corridor bands
- generic House member seating and Senate desk positions
- aggregate public seating sections for House member floor seating, House gallery, Senate desk blocks, Senate gallery, rostrum/presiding-officer areas, and joint-session role zones
- House Chamber joint-session layout for public ceremonial addresses, including President podium, Speaker and Vice President positions, and public generic seating zones for Senators, Cabinet, Supreme Court, diplomatic corps, press, members, and guests

Not included:

- security posts, secure circulation, evacuation routes, tunnels, or restricted service spaces
- private office-by-person assignments
- current senator-by-desk or representative-by-seat assignments
- nonpublic room numbers or operational details

House floor seating is modeled as 448 generic seats. Senate seating is modeled as 100 generic desks. The `seating_sections` metadata summarizes where major public roles sit without encoding person-by-person assignments. The joint-session layout is a public visual arrangement, not an operational seating chart. Occupant assignments are deliberately not encoded because they change and should be sourced only from approved public references if needed.

## Sources

- Exterior map geometry: OpenStreetMap extract downloaded from Overpass API on 2026-07-04. OSM data is available under the Open Database License.
- Interior schematic: public information about the Capitol's major spaces from Architect of the Capitol and public visitor information, reduced to a non-sensitive schematic.

## Next Fidelity Pass

The current direction is Unreal 5.8, first-person scale, most-compatible static mesh import, and public-only interior/seating detail. The next pass should improve:

- more recognizable chamber furniture and gallery shapes
- higher-fidelity facade ornament beyond the current public mullion, bracket, pilaster, and doorway pass
- public room shapes where public floor-plan references are available
- current public seating-chart overlays where available and appropriate
- pedestrian-scale signs, curbs, road markings, and bike-lane markings
