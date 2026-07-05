# Jan6Game Prototype

Unreal prototype assets for a historical public Capitol environment and fictional MetaHuman-style character references.

## MetaHuman Preview

<p align="center">
  <a href="ryan/generated_people_corrected/images/person_050_front.png">
    <img src="ryan/generated_people_corrected/images/person_050_front.png" alt="Fictional MetaHuman-style front portrait reference, person 050" width="360">
  </a>
</p>

## What's Here

- `capitol_unreal_map/` - Unreal 5.8 map package with generated OBJ meshes, 4K procedural textures, metadata, viewer, and import helpers.
- `ryan/generated_people_corrected/` - fictional portrait references, prompts, roster metadata, and distribution notes.
- `ryan/exports/` - early head-proxy and texture experiments.

## Map Scope

The Capitol map targets a Jan 6 / late-2020 public map state. The current generated package uses a historical OpenStreetMap snapshot at `2021-01-06T17:00:00Z`, plus public reference data for visual-only detail.

Interior areas are public-only and schematic: major public rooms, the Rotunda, chambers, galleries, generic offices, and broad seating zones. The package avoids restricted layouts, security-sensitive details, and person-specific assignments.

Detailed map notes are in `capitol_unreal_map/README.md`.

## Setup

Large generated meshes and 4K texture PNGs use Git LFS:

```bash
git lfs install
git lfs pull
```

## View The Map

```bash
cd capitol_unreal_map
python3 -m http.server 8765
```

Open `http://127.0.0.1:8765/viewer.html`.

## Rebuild

```bash
python3 capitol_unreal_map/scripts/fetch_osm_historical_capitol.py
python3 capitol_unreal_map/scripts/generate_material_textures.py
python3 capitol_unreal_map/scripts/build_capitol_unreal_map.py
python3 capitol_unreal_map/scripts/validate_capitol_package.py
```

## Character References

The generated people are fictional references for character creation:

- `ryan/generated_people_corrected/manifest.csv`
- `ryan/generated_people_corrected/distribution_notes.md`
