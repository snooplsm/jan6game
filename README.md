# jan6game

Prototype Unreal project assets for a public-data U.S. Capitol map and fictional MetaHuman-style character references.

<img src="ryan/generated_people_corrected/images/person_050_front.png" alt="Fictional generated MetaHuman-style front portrait" width="320">

## What Is Here

- `capitol_unreal_map/` - Unreal-ready Capitol map package with generated OBJ meshes, 4K procedural textures, metadata, a browser viewer, and an Unreal Editor import script.
- `ryan/generated_people_corrected/` - fictional generated front-face character references and roster metadata.
- `ryan/exports/` - early single-photo head proxy experiments.

## Capitol Map

The map targets a Jan 6-era public exterior source using historical OpenStreetMap data for `2021-01-06T17:00:00Z`. The interior is a public-only schematic: major rooms, Rotunda, generic offices, chambers, galleries, and generic seating zones. It intentionally avoids restricted/security-sensitive details and person-specific assignments.

Useful commands:

```bash
python3 capitol_unreal_map/scripts/fetch_osm_historical_capitol.py
python3 capitol_unreal_map/scripts/generate_material_textures.py
python3 capitol_unreal_map/scripts/build_capitol_unreal_map.py
python3 capitol_unreal_map/scripts/validate_capitol_package.py
```

Local viewer:

```bash
cd capitol_unreal_map
python3 -m http.server 8765
```

Then open `http://127.0.0.1:8765/viewer.html`.

## Character References

The generated people are fictional front-facing portrait references for character creation. Current roster notes and distribution metadata live in:

- `ryan/generated_people_corrected/manifest.csv`
- `ryan/generated_people_corrected/distribution_notes.md`

Detailed Capitol package docs live in `capitol_unreal_map/README.md`.
