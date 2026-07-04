# U.S. Capitol Unreal Map Package

This package is a first public-data pass at a U.S. Capitol map for Unreal Engine 5.8, authored at first-person centimeter scale.

It contains:

- exterior buildings, roads, bike-lane features, crossings, and traffic-signal markers derived from OpenStreetMap
- pedestrian paths, curb edges, sidewalks where side-specific sidewalk tags exist, and lane-edge markings derived from the same public OSM extract
- a public-only Capitol interior schematic with major spaces, generic office/support zones, Rotunda, House Chamber, Senate Chamber, galleries, generic chamber seating, and a joint-session House Chamber visual layout
- public-facing Capitol visual details including approximate revolving-door assemblies
- Unreal-friendly OBJ/MTL meshes in centimeter units
- JSON metadata for labels, source provenance, coordinates, rooms, and seating records
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
- `generated/meshes/capitol_materials.mtl`
- `generated/data/capitol_scene_metadata.json`
- `generated/data/capitol_package_validation.json`
- `generated/data/unreal_import_report.json` after the Unreal import script is run
- `unreal/material_realism_manifest.json`
- `unreal/import_capitol_map.py`
- `viewer.html`

## Regenerate

From the repository root:

```bash
python3 capitol_unreal_map/scripts/build_capitol_unreal_map.py
```

Validate the generated OBJ/MTL/metadata package before Unreal import:

```bash
python3 capitol_unreal_map/scripts/validate_capitol_package.py
```

The validator checks that:

- every metadata mesh exists
- OBJ face indices are valid
- OBJ material references exist in `capitol_materials.mtl`
- every generated MTL material has a valid Unreal realism-material manifest entry
- the expected exterior counts, pedestrian paths, curb records, lane-edge markings, public interior rooms, generic office cells, House seats, Senate desks, public seating sections, joint-session zones, and generated viewpoints are present

It writes `generated/data/capitol_package_validation.json`. This proves local package consistency; the final editor check is still to run `unreal/import_capitol_map.py` inside Unreal 5.8.

The current generated build contains:

- 2,525 building footprints
- 3,528 roads/paths
- 445 bike-lane/cycleway features
- 2,533 pedestrian path/footway records
- 1,216 curb edge records
- 608 lane-edge marking records
- 880 street markers/crossings/traffic signals
- Capitol visual massing details including dome, lantern, porticos, columns, steps, plaza, grounds, and public-facing revolving-door visuals
- 60 generic public office/support visual cells
- 448 generic House floor seats
- 100 generic Senate desks
- 16 public seating-section records: 7 regular-session House/Senate chamber sections and 9 joint-session role zones
- Joint-session House Chamber visual zones: President podium, Speaker chair, Vice President chair, Senators/Senate guests, Cabinet, Supreme Court, diplomatic corps, press/camera pool, and member/guest overflow blocks

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

The viewer can toggle:

- surrounding buildings
- roads, bike lanes, traffic signals, and crossing markers
- Capitol visual details
- public interior schematic
- labels

Viewer presets include overview, Capitol exterior, roads, public interior, Rotunda, House Chamber, Senate Chamber, and joint-session House Chamber views. The label search and category filter can focus the camera on matching public spaces, chamber labels, seating labels, office zones, streets, or named surrounding buildings.

Controls: drag to orbit, mouse wheel to zoom, shift-drag to pan.

## Unreal Import

You can open `CapitolMap.uproject` directly in Unreal 5.8 or run the import script from another Unreal 5.8 project.

1. Open your Unreal 5.8 project.
2. Enable editor scripting/Python support if it is not already enabled.
3. Run `capitol_unreal_map/unreal/import_capitol_map.py` from Unreal Editor with `Tools > Execute Python Script...`.
4. The script creates or opens `/Game/CapitolMap/Maps/CapitolMap_Level`.
5. The script imports meshes into `/Game/CapitolMap/Generated`.
6. The script creates or updates realism materials in `/Game/CapitolMap/Materials` from `unreal/material_realism_manifest.json` and applies them to matching imported material slots.
7. The script clears previously generated `CapitolMap` actors in that level, then respawns mesh actors, lights, labels, PlayerStart, camera viewpoints, and a broad `NavMeshBoundsVolume` for first-person/pawn testing.
8. The script saves the current level when the Unreal editor API allows it.
9. The script writes `generated/data/unreal_import_report.json` with the generated map path, imported asset paths, material asset paths, and metadata counts.

The OBJ vertices are already authored in centimeters, so import scale should remain `1.0`. OBJ/static mesh import is the primary compatibility path for this package.

## Realism Pass

The current realism pass is material-first. `unreal/material_realism_manifest.json` defines base color, roughness, metallic, specular, and opacity values for all generated MTL materials. The Unreal import script uses that manifest to create `M_*` materials under `/Game/CapitolMap/Materials` and assigns them to imported static mesh material slots when the slot names match the original MTL names.

This is not a texture pass yet. The next visual-fidelity step is to add real PBR texture maps and modular meshes for Capitol facade details, chamber furniture, street signs, traffic lights, trees, lamps, and other public streetscape props.

Generated camera viewpoints:

- `CapitolMap_Camera_Overview`
- `CapitolMap_Camera_WestFront_FirstPerson`
- `CapitolMap_Camera_Rotunda`
- `CapitolMap_Camera_HouseChamber_JointSession`
- `CapitolMap_Camera_SenateChamber`

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
- Rotunda wall ring, floor trim, and perimeter column details
- National Statuary Hall
- Old Senate Chamber
- Crypt marker
- House Chamber and Senate Chamber
- House and Senate galleries
- generic office/support zones
- 60 generic office/support cells with desks, chairs, and partitions
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
- more exterior facade detail on the Capitol wings
- public room shapes where public floor-plan references are available
- current public seating-chart overlays where available and appropriate
- pedestrian-scale signs, curbs, road markings, and bike-lane markings
