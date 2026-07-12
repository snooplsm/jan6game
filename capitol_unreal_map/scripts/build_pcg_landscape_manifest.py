#!/usr/bin/env python3
"""Build a deterministic Unreal PCG/Water handoff from scene metadata."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METADATA_PATH = ROOT / "generated" / "data" / "capitol_scene_metadata.json"
OUTPUT_PATH = ROOT / "generated" / "data" / "pcg_landscape_manifest.json"

GRASS_KINDS = {"lawn_panel", "public_lawn_slope_panel", "formal_planting_bed"}
HARDSCAPE_KINDS = {
    "public_walk",
    "plaza",
    "reflecting_pool",
    "reflecting_pool_edge",
    "low_plaza_wall",
    "path_edge_stone",
}


def compact_record(record: dict) -> dict:
    return {
        key: record[key]
        for key in (
            "name",
            "kind",
            "center_m",
            "size_m",
            "min_z_m",
            "max_z_m",
            "public_accuracy",
        )
        if key in record
    }


def main() -> None:
    data = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    exterior = data["exterior"]
    grounds = exterior.get("grounds_details", [])

    grass_surfaces = [compact_record(item) for item in grounds if item.get("kind") in GRASS_KINDS]
    hardscape = [compact_record(item) for item in grounds if item.get("kind") in HARDSCAPE_KINDS]
    pools = [item for item in hardscape if item.get("kind") == "reflecting_pool"]

    manifest = {
        "schema_version": 1,
        "target_date_local": "2021-01-06T11:50:00-05:00",
        "coordinate_system": {
            "units": "meters",
            "unreal_units_per_meter": 100,
            "origin_note": "Matches generated Capitol OBJ/metadata origin.",
        },
        "source_provenance": {
            "map_snapshot": "OpenStreetMap/Overpass 2021-01-06T17:00:00Z",
            "ground_surfaces": "DC GIS Planimetrics 1999 source where available; otherwise documented public schematic grounds geometry",
            "metadata": str(METADATA_PATH.relative_to(ROOT)),
        },
        "unreal_dependencies": {
            "plugins": ["PCG", "Water"],
            "local_fab_content": ["/Game/PN_GrassLibrary", "/Game/Maxtree"],
            "preferred_grass_meshes": [
                "/Game/PN_GrassLibrary/Meshes/grassMesh/grass_01_01_mesh",
                "/Game/PN_GrassLibrary/Meshes/grassMesh/grass_02_01_mesh",
                "/Game/PN_GrassLibrary/Meshes/grassMesh/lowGrass_04_01_mesh",
            ],
        },
        "seasonal_profile": {
            "season": "mid_atlantic_winter",
            "date": "2021-01-06",
            "grass_density_multiplier": 1.0,
            "grass_height_scale_range": [0.72, 0.94],
            "grass_color_tint_linear": [0.42, 0.48, 0.28, 1.0],
            "dry_blade_fraction": 0.28,
            "flower_density_multiplier": 0.0,
            "mowing_pattern_strength": 0.18,
            "wind_strength": 0.22,
            "note": "Dense dormant/cool-season maintained turf; avoid saturated summer green. The current generated grounds are static meshes, so the live Unreal map uses PCG-spawned HISM turf rather than Landscape Grass Type until a future landscape conversion.",
        },
        "pcg": {
            "graph_asset": "/Game/HistoricalOSM/PCG/PCG_CapitolWinterLawns",
            "surface_tag": "CapitolGrassSurface",
            "exclusion_tags": [
                "HistoricalOSM_Building",
                "HistoricalOSM_Road",
                "HistoricalOSM_BikeLane",
                "HistoricalOSM_Sidewalk",
                "CapitolHardscape",
                "CapitolReflectingPool",
            ],
            "grass_surfaces": grass_surfaces,
            "sampling": {
                "points_per_square_meter": 33.33,
                "volume_sampler_spacing_cm": 17.32,
                "looseness": 0.82,
                "random_yaw": True,
                "scale_min": 0.72,
                "scale_max": 0.94,
                "collision": "none",
                "instance_type": "HISM",
                "cull_start_cm": 12000,
                "cull_end_cm": 26000,
            },
        },
        "hardscape_exclusions": hardscape,
        "transport_exclusions": {
            "roads": [{"id": item.get("id"), "name": item.get("name"), "width_m": item.get("width_m")} for item in exterior.get("roads", [])],
            "bike_lanes": [{"id": item.get("id"), "name": item.get("name"), "type": item.get("type")} for item in exterior.get("bike_lanes", [])],
            "building_count": len(exterior.get("buildings", [])),
        },
        "water": {
            "plugin": "Water",
            "body_type": "custom_shallow_reflecting_pool",
            "surface_material_intent": "low-wave winter reflecting water",
            "depth_m": 0.35,
            "wave_amplitude_m": 0.006,
            "wave_length_m": 5.5,
            "flow_speed_mps": 0.0,
            "roughness": 0.08,
            "opacity": 0.72,
            "reflection_method": "Lumen plus planar reflection for hero views",
            "pool_records": pools,
            "security_note": "Public landscape feature only; no restricted infrastructure detail.",
        },
        "validation": {
            "grass_surface_count": len(grass_surfaces),
            "hardscape_exclusion_count": len(hardscape),
            "road_exclusion_count": len(exterior.get("roads", [])),
            "bike_lane_exclusion_count": len(exterior.get("bike_lanes", [])),
            "reflecting_pool_count": len(pools),
        },
    }

    OUTPUT_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["validation"], indent=2))


if __name__ == "__main__":
    main()
