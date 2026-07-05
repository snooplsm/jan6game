# Jan6Game Prototype

Unreal prototype assets for a public-data Capitol environment and fictional MetaHuman-style character references.

## Preview

Representative fictional MetaHuman reference:

<p align="center">
  <a href="ryan/generated_people_corrected/images/person_050_front.png">
    <img src="ryan/generated_people_corrected/images/person_050_front.png" alt="Fictional MetaHuman-style front portrait reference, person 050" width="380">
  </a>
</p>

## Contents

- `capitol_unreal_map/` - Unreal 5.8 Capitol map package, generated OBJ meshes, 4K procedural textures, metadata, browser viewer, and import script.
- `ryan/generated_people_corrected/` - fictional character reference portraits, prompts, roster metadata, and distribution notes.
- `ryan/exports/` - early head-proxy and texture experiments.

## Capitol Map

The map uses Jan 6-era public exterior context from historical OpenStreetMap data at `2021-01-06T17:00:00Z`. Interior work is public-only and schematic: major public rooms, the Rotunda, chambers, galleries, generic offices, and broad seating zones. It avoids restricted details, security-sensitive layouts, and person-specific assignments.

Detailed package notes live in `capitol_unreal_map/README.md`.

## Setup

Large generated meshes and 4K texture PNGs are tracked with Git LFS:

```bash
git lfs install
git lfs pull
```

## Rebuild

```bash
python3 capitol_unreal_map/scripts/fetch_osm_historical_capitol.py
python3 capitol_unreal_map/scripts/generate_material_textures.py
python3 capitol_unreal_map/scripts/build_capitol_unreal_map.py
python3 capitol_unreal_map/scripts/validate_capitol_package.py
```

## View The Map

```bash
cd capitol_unreal_map
python3 -m http.server 8765
```

Open `http://127.0.0.1:8765/viewer.html`.

## Character References

The generated people are fictional portrait references for character creation. Roster notes and distribution metadata are in:

- `ryan/generated_people_corrected/manifest.csv`
- `ryan/generated_people_corrected/distribution_notes.md`
