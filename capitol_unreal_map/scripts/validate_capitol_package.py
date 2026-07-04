#!/usr/bin/env python3
"""Validate generated Capitol map assets before Unreal import.

This is a structural package check, not a substitute for opening the level in
Unreal Editor. It verifies that metadata, OBJ meshes, and MTL materials agree
with the public-data map package contract.
"""

from __future__ import annotations

import ast
import json
import math
import os
import struct
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MESH_DIR = ROOT / "generated" / "meshes"
DATA_DIR = ROOT / "generated" / "data"
METADATA_PATH = DATA_DIR / "capitol_scene_metadata.json"
MTL_PATH = MESH_DIR / "capitol_materials.mtl"
REPORT_PATH = DATA_DIR / "capitol_package_validation.json"
MATERIAL_MANIFEST_PATH = ROOT / "unreal" / "material_realism_manifest.json"
TEXTURE_MANIFEST_PATH = DATA_DIR / "material_texture_manifest.json"
UNREAL_IMPORTER_PATH = ROOT / "unreal" / "import_capitol_map.py"
UPROJECT_PATH = ROOT / "CapitolMap.uproject"
DEFAULT_ENGINE_PATH = ROOT / "Config" / "DefaultEngine.ini"
DEFAULT_GAME_PATH = ROOT / "Config" / "DefaultGame.ini"
MIN_TEXTURE_SIZE_PX = int(os.environ.get("CAPITOL_MIN_TEXTURE_SIZE", "4096"))

EXPECTED_MESHES = {
    "generated/meshes/capitol_exterior_buildings.obj",
    "generated/meshes/capitol_exterior_roads_bike_lanes_markers.obj",
    "generated/meshes/capitol_landmark_visual_details.obj",
    "generated/meshes/capitol_public_interior_schematic.obj",
    "generated/meshes/capitol_gameplay_items.obj",
}

EXPECTED_UNREAL_MESH_BASENAMES = {Path(rel).name for rel in EXPECTED_MESHES}

EXPECTED_UNREAL_DESTINATIONS = {
    "/Game/CapitolMap/Generated",
    "/Game/CapitolMap/Materials",
    "/Game/CapitolMap/Textures",
    "/Game/CapitolMap/Maps",
}

REQUIRED_UNREAL_FUNCTIONS = {
    "prepare_level",
    "clear_generated_level_actors",
    "import_meshes",
    "import_texture_assets",
    "create_or_update_materials",
    "spawn_mesh_actors",
    "spawn_scene_setup",
    "spawn_playtest_pawn",
    "spawn_camera_viewpoints",
    "spawn_navigation_bounds",
    "spawn_metadata_lights",
    "spawn_metadata_labels",
    "write_unreal_import_report",
    "main",
}

REQUIRED_UNREAL_CALLS = {
    "prepare_level",
    "clear_generated_level_actors",
    "import_meshes",
    "import_texture_assets",
    "create_or_update_materials",
    "spawn_mesh_actors",
    "spawn_scene_setup",
    "spawn_playtest_pawn",
    "spawn_camera_viewpoints",
    "spawn_navigation_bounds",
    "spawn_metadata_lights",
    "spawn_metadata_labels",
    "save_generated_level",
    "write_unreal_import_report",
}

REQUIRED_UNREAL_REPORT_KEYS = {
    "ok",
    "map_asset_path",
    "map_destination",
    "import_destination",
    "material_destination",
    "texture_destination",
    "imported_assets",
    "material_assets",
    "texture_assets",
    "mesh_count",
    "material_count",
    "texture_set_count",
    "texture_asset_count",
    "first_person_setup",
    "static_mesh_lod_group",
    "auto_generate_collision",
    "collision_trace",
    "actor_collision",
    "can_affect_navigation",
    "nanite_enabled",
    "player_start_actor_class",
    "player_start_label",
    "player_start_location_cm",
    "playtest_pawn_actor_class",
    "playtest_pawn_label",
    "playtest_pawn_location_cm",
    "playtest_pawn_rotation_deg",
    "playtest_pawn_auto_possess",
    "nav_mesh_bounds_actor_class",
    "nav_mesh_bounds_label",
    "nav_mesh_bounds_location_cm",
    "nav_mesh_bounds_scale_cm",
    "metadata_counts",
    "buildings",
    "roads",
    "bike_lanes",
    "street_markers",
    "grounds_details",
    "grounds_walk_lamps",
    "rooms",
    "seating",
    "office_cells",
    "circulation_details",
    "joint_session",
    "gameplay_items",
    "viewpoints",
}

REQUIRED_UNREAL_LABEL_CATEGORIES = {
    "major_public_space",
    "legislative_chamber",
    "visitor_gallery",
    "generic_office_zone",
    "seating",
    "seating_section",
    "chamber_detail",
    "public_circulation_detail",
    "joint_session",
    "public_art",
    "lighting",
    "wall_treatment",
    "landmark",
    "street_name",
    "building",
    "gameplay_item",
}

REQUIRED_UNREAL_OUTLINER_FOLDERS = {
    "CapitolMap/Meshes",
    "CapitolMap/SceneSetup",
    "CapitolMap/Viewpoints",
    "CapitolMap/Lighting",
    "CapitolMap/Labels/Interior",
    "CapitolMap/Labels/Exterior",
    "CapitolMap/Labels/Landmark",
    "CapitolMap/Labels/Gameplay",
}

REQUIRED_UNREAL_FIRST_PERSON_MARKERS = {
    "LargeProp",
    "auto_generate_collision",
    "CTF_USE_COMPLEX_AS_SIMPLE",
    "QUERY_AND_PHYSICS",
    "can_ever_affect_navigation",
    "NavMeshBoundsVolume",
    "PlayerStart",
    "DefaultPawn",
    "PLAYER0",
    "CapitolMap_PlayerStart_WestFront",
    "CapitolMap_Playtest_DefaultPawn",
    "auto_possess_player",
    "auto_receive_input",
    "CapitolMap_NavMeshBounds_CentralCampus",
    "nanite_settings",
}

REQUIRED_UNREAL_PROJECT_CONFIG_MARKERS = {
    "CapitolMap.uproject": {
        '"EngineAssociation": "5.8"',
        '"PythonScriptPlugin"',
        '"EditorScriptingUtilities"',
    },
    "Config/DefaultEngine.ini": {
        "[/Script/EngineSettings.GameMapsSettings]",
        "EditorStartupMap=/Game/CapitolMap/Maps/CapitolMap_Level",
        "GameDefaultMap=/Game/CapitolMap/Maps/CapitolMap_Level",
        "GlobalDefaultGameMode=/Script/Engine.GameModeBase",
        "r.DefaultFeature.AutoExposure=False",
        "r.DefaultFeature.MotionBlur=False",
        "r.GenerateMeshDistanceFields=True",
        "r.Nanite.ProjectEnabled=True",
        "bAutoCreateNavigationData=True",
        "bSpawnNavDataInNavBoundsLevel=True",
    },
    "Config/DefaultGame.ini": {
        "ProjectName=Capitol Unreal Map",
        "Public-data U.S. Capitol exterior and public-interior schematic map package.",
    },
}

REQUIRED_ROOMS = {
    "Rotunda",
    "National Statuary Hall",
    "Old Senate Chamber",
    "House Chamber",
    "Senate Chamber",
    "House galleries",
    "Senate galleries",
}

REQUIRED_JOINT_SESSION = {
    "president_address_podium",
    "speaker_chair_joint_session",
    "vice_president_chair_joint_session",
    "senate_floor_block",
    "cabinet_floor_block",
    "supreme_court_block",
    "diplomatic_corps_block",
    "press_pool_block",
    "members_and_guests_backfill",
}

REQUIRED_SEATING_SECTIONS = {
    "house_representatives_floor_generic",
    "house_rostrum_speaker_clerks_press",
    "house_public_gallery",
    "senate_desks_left_generic_block",
    "senate_desks_right_generic_block",
    "senate_presiding_officer_clerks",
    "senate_public_gallery",
    "joint_session_president_address_podium",
    "joint_session_speaker_chair_joint_session",
    "joint_session_vice_president_chair_joint_session",
    "joint_session_senate_floor_block",
    "joint_session_cabinet_floor_block",
    "joint_session_supreme_court_block",
    "joint_session_diplomatic_corps_block",
    "joint_session_press_pool_block",
    "joint_session_members_and_guests_backfill",
}

REQUIRED_CHAMBER_DETAIL_KINDS = {
    "rostrum_rail",
    "rostrum_desk",
    "dais_step",
    "gallery_rail",
    "gallery_bench",
    "aisle_edge",
    "backdrop_panel",
    "flag_standard",
    "desk_arc_marker",
    "public_lectern",
    "public_work_table",
    "gallery_divider",
    "balcony_fascia",
    "desk_surface_marker",
}

REQUIRED_CIRCULATION_DETAIL_KINDS = {
    "public_corridor_band",
    "door_threshold",
    "room_portal_trim",
    "orientation_sign",
    "floor_inlay",
}

REQUIRED_GROUNDS_DETAIL_KINDS = {
    "lawn_panel",
    "public_walk",
    "reflecting_pool",
    "pool_coping",
    "formal_planting_bed",
    "public_tree_allee",
    "public_walk_lamp",
    "low_plaza_wall",
}

REQUIRED_STREETSCAPE_PROP_KINDS = {
    "streetlight",
    "street_name_sign",
    "traffic_signal_prop",
    "tree_planter",
    "road_stop_bar",
    "lane_direction_arrow",
    "bike_symbol",
    "curb_ramp_visual",
    "public_wayfinding_sign",
}

REQUIRED_BUILDING_DETAIL_KINDS = {
    "surrounding_building_roofline",
    "surrounding_building_facade_window",
    "surrounding_building_public_entry_marker",
    "surrounding_building_rooftop_detail",
}

REQUIRED_VIEWPOINTS = {
    "CapitolMap_Camera_Overview",
    "CapitolMap_Camera_WestFront_FirstPerson",
    "CapitolMap_Camera_WestGrounds",
    "CapitolMap_Camera_Rotunda",
    "CapitolMap_Camera_HouseChamber_JointSession",
    "CapitolMap_Camera_SenateChamber",
    "CapitolMap_Camera_GameplayItems",
}

REQUIRED_GAMEPLAY_ITEMS = {
    "flagpole",
    "nunchucks",
    "bear_spray",
    "mace_spray",
    "feces_throwable",
    "knife",
    "handgun",
}

REQUIRED_FLAGPOLE_BANNERS = {
    "american_flag",
    "trump_2024_red",
    "trump_2024_blue",
    "save_america_red",
    "maga_blue",
}

REQUIRED_FACADE_DETAIL_KINDS = {
    "facade_window",
    "facade_window_surround",
    "facade_window_mullion",
    "facade_dentil_course",
    "facade_cornice_bracket",
    "facade_pilaster",
    "public_stair_tread",
    "public_approach_handrail",
    "public_door_surround",
    "roof_balustrade",
    "dome_balustrade_posts",
    "dome_vertical_rib",
    "dome_drum_window_trim",
    "dome_lateral_band",
    "lantern_window",
    "dome_finial",
    "pediment_relief_panel",
}


def error(errors: list[str], message: str) -> None:
    errors.append(message)


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def is_vec3(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 3 and all(is_number(item) for item in value)


def parse_mtl(path: Path, errors: list[str]) -> set[str]:
    if not path.exists():
        error(errors, f"missing MTL file: {path}")
        return set()

    materials: set[str] = set()
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if parts[0] == "newmtl":
            if len(parts) < 2:
                error(errors, f"{path}:{lineno}: empty material name")
            else:
                materials.add(" ".join(parts[1:]))
        elif parts[0] in {"Kd", "Ka", "Ks"}:
            parsed = parse_floatish(parts[1:])
            if len(parts) != 4 or parsed is None:
                error(errors, f"{path}:{lineno}: malformed {parts[0]} color")
        elif parts[0] == "d":
            parsed = parse_floatish(parts[1:])
            if len(parts) != 2 or parsed is None:
                error(errors, f"{path}:{lineno}: malformed alpha")

    if not materials:
        error(errors, f"no materials defined in {path}")
    return materials


def parse_floatish(values: list[str]) -> list[float] | None:
    try:
        parsed = [float(value) for value in values]
    except ValueError:
        return None
    if not all(math.isfinite(value) for value in parsed):
        return None
    return parsed


def png_dimensions(path: Path) -> tuple[int, int] | None:
    try:
        header = path.read_bytes()[:24]
    except OSError:
        return None
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", header[16:24])
    return int(width), int(height)


def parse_obj(path: Path, materials: set[str], errors: list[str]) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "path": str(path.relative_to(ROOT)),
        "vertices": 0,
        "uvs": 0,
        "faces": 0,
        "faces_with_uvs": 0,
        "triangles": 0,
        "groups": 0,
        "materials": [],
        "mtllibs": [],
        "bbox_cm": None,
    }
    if not path.exists():
        error(errors, f"missing OBJ file: {path}")
        return stats

    material_refs: set[str] = set()
    min_xyz = [math.inf, math.inf, math.inf]
    max_xyz = [-math.inf, -math.inf, -math.inf]

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        kind = parts[0]
        if kind == "v":
            if len(parts) < 4:
                error(errors, f"{path}:{lineno}: malformed vertex")
                continue
            parsed = parse_floatish(parts[1:4])
            if parsed is None:
                error(errors, f"{path}:{lineno}: nonnumeric vertex")
                continue
            stats["vertices"] += 1
            for axis in range(3):
                min_xyz[axis] = min(min_xyz[axis], parsed[axis])
                max_xyz[axis] = max(max_xyz[axis], parsed[axis])
        elif kind == "vt":
            if len(parts) < 3:
                error(errors, f"{path}:{lineno}: malformed texture coordinate")
                continue
            parsed = parse_floatish(parts[1:3])
            if parsed is None:
                error(errors, f"{path}:{lineno}: nonnumeric texture coordinate")
                continue
            stats["uvs"] += 1
        elif kind == "f":
            if len(parts) < 4:
                error(errors, f"{path}:{lineno}: face has fewer than 3 vertices")
                continue
            face_indexes = []
            uv_indexes = []
            for token in parts[1:]:
                token_parts = token.split("/")
                index_token = token_parts[0]
                try:
                    raw_index = int(index_token)
                except ValueError:
                    error(errors, f"{path}:{lineno}: invalid face index {token!r}")
                    continue
                if raw_index == 0:
                    error(errors, f"{path}:{lineno}: OBJ index 0 is invalid")
                    continue
                resolved = raw_index if raw_index > 0 else stats["vertices"] + raw_index + 1
                if resolved < 1 or resolved > stats["vertices"]:
                    error(errors, f"{path}:{lineno}: face index {raw_index} outside 1..{stats['vertices']}")
                    continue
                face_indexes.append(resolved)
                if len(token_parts) > 1 and token_parts[1]:
                    try:
                        raw_uv_index = int(token_parts[1])
                    except ValueError:
                        error(errors, f"{path}:{lineno}: invalid texture coordinate index {token!r}")
                        continue
                    if raw_uv_index == 0:
                        error(errors, f"{path}:{lineno}: OBJ texture coordinate index 0 is invalid")
                        continue
                    resolved_uv = raw_uv_index if raw_uv_index > 0 else stats["uvs"] + raw_uv_index + 1
                    if resolved_uv < 1 or resolved_uv > stats["uvs"]:
                        error(errors, f"{path}:{lineno}: texture coordinate index {raw_uv_index} outside 1..{stats['uvs']}")
                        continue
                    uv_indexes.append(resolved_uv)
            if len(face_indexes) >= 3:
                stats["faces"] += 1
                if len(uv_indexes) == len(face_indexes):
                    stats["faces_with_uvs"] += 1
                stats["triangles"] += len(face_indexes) - 2
        elif kind == "usemtl":
            if len(parts) < 2:
                error(errors, f"{path}:{lineno}: empty usemtl")
                continue
            material_refs.add(" ".join(parts[1:]))
        elif kind == "mtllib":
            stats["mtllibs"].append(" ".join(parts[1:]))
        elif kind == "g":
            stats["groups"] += 1

    missing_materials = sorted(material_refs - materials)
    if missing_materials:
        error(errors, f"{path}: undefined materials: {', '.join(missing_materials)}")
    if stats["vertices"] <= 0:
        error(errors, f"{path}: no vertices")
    if stats["faces"] <= 0:
        error(errors, f"{path}: no faces")
    if stats["uvs"] <= 0:
        error(errors, f"{path}: no texture coordinates")
    if stats["faces"] > 0 and stats["faces_with_uvs"] != stats["faces"]:
        error(errors, f"{path}: {stats['faces'] - stats['faces_with_uvs']} face(s) missing full texture-coordinate coverage")
    if "capitol_materials.mtl" not in stats["mtllibs"]:
        error(errors, f"{path}: missing mtllib capitol_materials.mtl")

    stats["materials"] = sorted(material_refs)
    if all(math.isfinite(value) for value in min_xyz + max_xyz):
        stats["bbox_cm"] = {"min": min_xyz, "max": max_xyz}
    return stats


def validate_metadata(metadata: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    summary: dict[str, Any] = {}

    if metadata.get("package") != "capitol_unreal_map":
        error(errors, "metadata package name is not capitol_unreal_map")

    coordinate_system = metadata.get("coordinate_system", {})
    if coordinate_system.get("obj_units") != "centimeters":
        error(errors, "metadata coordinate_system.obj_units must be centimeters")
    origin = coordinate_system.get("origin", {})
    if not is_number(origin.get("lat")) or not is_number(origin.get("lon")):
        error(errors, "metadata origin lat/lon missing or invalid")

    meshes = set(metadata.get("meshes", []))
    summary["mesh_count"] = len(meshes)
    if meshes != EXPECTED_MESHES:
        error(errors, f"metadata meshes mismatch: expected {sorted(EXPECTED_MESHES)}, got {sorted(meshes)}")
    for rel in meshes:
        if not (ROOT / rel).exists():
            error(errors, f"metadata mesh does not exist: {rel}")

    exterior = metadata.get("exterior", {})
    summary["buildings"] = len(exterior.get("buildings", []))
    summary["roads"] = len(exterior.get("roads", []))
    summary["bike_lanes"] = len(exterior.get("bike_lanes", []))
    summary["pedestrian_paths"] = len(exterior.get("pedestrian_paths", []))
    summary["curbs"] = len(exterior.get("curbs", []))
    summary["lane_edge_markings"] = len(exterior.get("lane_edge_markings", []))
    summary["street_markers"] = len(exterior.get("street_markers", []))
    replaced_buildings = exterior.get("replaced_buildings", [])
    summary["replaced_buildings"] = len(replaced_buildings)
    building_details = exterior.get("building_details", [])
    building_detail_kinds = {detail.get("kind") for detail in building_details}
    summary["building_details"] = len(building_details)
    summary["building_detail_kinds"] = len(building_detail_kinds)
    streetscape_props = exterior.get("streetscape_props", [])
    streetscape_prop_kinds = {prop.get("kind") for prop in streetscape_props}
    summary["streetscape_props"] = len(streetscape_props)
    summary["streetscape_prop_kinds"] = len(streetscape_prop_kinds)
    grounds_details = exterior.get("grounds_details", [])
    grounds_detail_kinds = {detail.get("kind") for detail in grounds_details}
    grounds_walk_lamps = [detail for detail in grounds_details if detail.get("kind") == "public_walk_lamp"]
    summary["grounds_details"] = len(grounds_details)
    summary["grounds_detail_kinds"] = len(grounds_detail_kinds)
    summary["grounds_walk_lamps"] = len(grounds_walk_lamps)
    if summary["buildings"] < 2000:
        error(errors, "expected at least 2000 surrounding building footprints")
    if summary["roads"] < 3000:
        error(errors, "expected at least 3000 roads/paths")
    if summary["bike_lanes"] < 300:
        error(errors, "expected at least 300 bike/cycleway features")
    if summary["pedestrian_paths"] < 2000:
        error(errors, "expected at least 2000 pedestrian paths/footways")
    if summary["curbs"] < 1000:
        error(errors, "expected at least 1000 curb edge records")
    if summary["lane_edge_markings"] < 500:
        error(errors, "expected at least 500 lane edge marking records")
    if summary["street_markers"] < 500:
        error(errors, "expected at least 500 street markers/crossings/signals")
    if not any(item.get("name") == "United States Capitol" for item in replaced_buildings):
        error(errors, "expected OSM United States Capitol footprint to be replaced by authored landmark mesh")
    if any(item.get("name") == "United States Capitol" for item in exterior.get("buildings", [])):
        error(errors, "OSM United States Capitol footprint should not be extruded in exterior buildings mesh")
    if len(building_details) < 520:
        error(errors, f"expected at least 520 surrounding building visual detail records, got {len(building_details)}")
    missing_building_detail_kinds = sorted(REQUIRED_BUILDING_DETAIL_KINDS - building_detail_kinds)
    if missing_building_detail_kinds:
        error(errors, f"missing surrounding building detail kinds: {', '.join(missing_building_detail_kinds)}")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_roofline"]) < 35:
        error(errors, "expected at least 35 surrounding building roofline records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_facade_window"]) < 360:
        error(errors, "expected at least 360 surrounding building facade-window records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_public_entry_marker"]) < 35:
        error(errors, "expected at least 35 surrounding building public-entry marker records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_rooftop_detail"]) < 60:
        error(errors, "expected at least 60 surrounding building rooftop-detail records")
    for detail in building_details[:12]:
        if not is_vec3(detail.get("center_m")):
            error(errors, f"building detail {detail.get('name', '<unknown>')} has invalid center_m")
            break
        if "public" not in detail.get("public_accuracy", ""):
            error(errors, f"building detail {detail.get('name', '<unknown>')} lacks public accuracy boundary")
            break
    if len(streetscape_props) < 870:
        error(errors, f"expected at least 870 public streetscape props, got {len(streetscape_props)}")
    missing_streetscape_kinds = sorted(REQUIRED_STREETSCAPE_PROP_KINDS - streetscape_prop_kinds)
    if missing_streetscape_kinds:
        error(errors, f"missing public streetscape prop kinds: {', '.join(missing_streetscape_kinds)}")
    if len([prop for prop in streetscape_props if prop.get("kind") == "road_stop_bar"]) < 12:
        error(errors, "expected at least 12 public road stop-bar props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "lane_direction_arrow"]) < 12:
        error(errors, "expected at least 12 public lane-direction arrow props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "bike_symbol"]) < 8:
        error(errors, "expected at least 8 public bike-symbol props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "curb_ramp_visual"]) < 16:
        error(errors, "expected at least 16 public curb-ramp visual props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "public_wayfinding_sign"]) < 8:
        error(errors, "expected at least 8 public wayfinding sign props")
    for prop in streetscape_props[:12]:
        if not is_vec3(prop.get("center_m")):
            error(errors, f"streetscape prop {prop.get('name', '<unknown>')} has invalid center_m")
            break
    if len(grounds_details) < 80:
        error(errors, f"expected at least 80 public grounds detail records, got {len(grounds_details)}")
    missing_grounds_kinds = sorted(REQUIRED_GROUNDS_DETAIL_KINDS - grounds_detail_kinds)
    if missing_grounds_kinds:
        error(errors, f"missing public grounds detail kinds: {', '.join(missing_grounds_kinds)}")
    if len(grounds_walk_lamps) < 18:
        error(errors, f"expected at least 18 public grounds walk lamps, got {len(grounds_walk_lamps)}")
    for detail in grounds_details:
        if not is_vec3(detail.get("center_m")):
            error(errors, f"grounds detail {detail.get('name', '<unknown>')} has invalid center_m")
            break
        if "public" not in detail.get("public_accuracy", ""):
            error(errors, f"grounds detail {detail.get('name', '<unknown>')} lacks public accuracy boundary")
            break
        if detail.get("kind") == "public_walk_lamp":
            if not is_vec3(detail.get("light_m")):
                error(errors, f"grounds lamp {detail.get('name', '<unknown>')} has invalid light_m")
                break
            if not is_number(detail.get("intensity")) or not is_number(detail.get("attenuation_radius_m")):
                error(errors, f"grounds lamp {detail.get('name', '<unknown>')} has invalid light properties")
                break

    landmark = metadata.get("landmark", {})
    elements = landmark.get("elements", [])
    facade_details = landmark.get("facade_details", [])
    facade_detail_kinds = {detail.get("kind") for detail in facade_details}
    summary["landmark_elements"] = len(elements)
    summary["facade_details"] = len(facade_details)
    summary["facade_detail_kinds"] = len(facade_detail_kinds)
    revolving = [item for item in elements if "revolving door" in item.get("name", "").lower()]
    summary["revolving_door_visuals"] = len(revolving)
    if len(elements) < 18:
        error(errors, "expected at least 18 Capitol landmark detail elements")
    if len(revolving) < 12:
        error(errors, "expected at least 12 public-facing revolving-door visual elements")
    if len(facade_details) < 1000:
        error(errors, f"expected at least 1000 public facade/furniture visual details, got {len(facade_details)}")
    missing_facade_kinds = sorted(REQUIRED_FACADE_DETAIL_KINDS - facade_detail_kinds)
    if missing_facade_kinds:
        error(errors, f"missing public facade detail kinds: {', '.join(missing_facade_kinds)}")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_window_surround"]) < 240:
        error(errors, "expected at least 240 facade window surround records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_window_mullion"]) < 260:
        error(errors, "expected at least 260 facade window mullion records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_dentil_course"]) < 8:
        error(errors, "expected at least 8 facade dentil course records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_cornice_bracket"]) < 100:
        error(errors, "expected at least 100 facade cornice bracket records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_pilaster"]) < 48:
        error(errors, "expected at least 48 public facade pilaster records")
    if len([detail for detail in facade_details if detail.get("kind") == "public_stair_tread"]) < 18:
        error(errors, "expected at least 18 public stair tread records")
    if len([detail for detail in facade_details if detail.get("kind") == "public_approach_handrail"]) < 8:
        error(errors, "expected at least 8 public approach handrail records")
    if len([detail for detail in facade_details if detail.get("kind") == "public_door_surround"]) < 12:
        error(errors, "expected at least 12 public door surround records")
    if len([detail for detail in facade_details if detail.get("kind") == "roof_balustrade"]) < 6:
        error(errors, "expected at least 6 public roof balustrade records")
    if len([detail for detail in facade_details if detail.get("kind") == "dome_vertical_rib"]) < 24:
        error(errors, "expected at least 24 dome vertical rib records")
    if len([detail for detail in facade_details if detail.get("kind") == "dome_drum_window_trim"]) < 16:
        error(errors, "expected at least 16 dome drum window trim records")
    if len([detail for detail in facade_details if detail.get("kind") == "dome_lateral_band"]) < 4:
        error(errors, "expected at least 4 dome lateral band records")
    for detail in facade_details[:12]:
        if not is_vec3(detail.get("center_m")):
            error(errors, f"facade detail {detail.get('name', '<unknown>')} has invalid center_m")
            break

    interior = metadata.get("interior", {})
    rooms = interior.get("rooms", [])
    room_names = {room.get("name") for room in rooms}
    summary["rooms"] = len(rooms)
    missing_rooms = sorted(REQUIRED_ROOMS - room_names)
    if missing_rooms:
        error(errors, f"missing required public interior rooms: {', '.join(missing_rooms)}")

    seating = interior.get("seating", [])
    house_seats = [seat for seat in seating if seat.get("chamber") == "House Chamber"]
    senate_desks = [seat for seat in seating if seat.get("chamber") == "Senate Chamber"]
    summary["house_seats"] = len(house_seats)
    summary["senate_desks"] = len(senate_desks)
    if len(house_seats) != 448:
        error(errors, f"expected 448 generic House seats, got {len(house_seats)}")
    if len(senate_desks) != 100:
        error(errors, f"expected 100 generic Senate desks, got {len(senate_desks)}")
    for seat in seating:
        if not is_vec3(seat.get("location_m")):
            error(errors, f"seat {seat.get('id', '<unknown>')} has invalid location_m")
            break
        assignment = seat.get("assignment", "").lower()
        if "generic" not in assignment and "unassigned" not in assignment:
            error(errors, f"seat {seat.get('id', '<unknown>')} assignment is not marked generic/unassigned")
            break

    office_cells = interior.get("office_cells", [])
    summary["office_cells"] = len(office_cells)
    if len(office_cells) != 60:
        error(errors, f"expected 60 generic office/support cells, got {len(office_cells)}")

    seating_sections = interior.get("seating_sections", [])
    section_ids = {section.get("id") for section in seating_sections}
    summary["seating_sections"] = len(seating_sections)
    summary["regular_session_seating_sections"] = len(
        [section for section in seating_sections if section.get("mode") == "regular_session"]
    )
    summary["joint_session_seating_sections"] = len(
        [section for section in seating_sections if section.get("mode") == "joint_session"]
    )
    missing_sections = sorted(REQUIRED_SEATING_SECTIONS - section_ids)
    if missing_sections:
        error(errors, f"missing seating sections: {', '.join(missing_sections)}")
    if summary["regular_session_seating_sections"] != 7:
        error(errors, f"expected 7 regular-session seating sections, got {summary['regular_session_seating_sections']}")
    if summary["joint_session_seating_sections"] != 9:
        error(errors, f"expected 9 joint-session seating sections, got {summary['joint_session_seating_sections']}")
    for section in seating_sections:
        if not is_vec3(section.get("center_m")):
            error(errors, f"seating section {section.get('id', '<unknown>')} has invalid center_m")
            break
        assignment = section.get("assignment", "").lower()
        if "generic" not in assignment and "not an operational" not in assignment and "public visual" not in assignment:
            error(errors, f"seating section {section.get('id', '<unknown>')} assignment is not marked generic/public")
            break

    chamber_details = interior.get("chamber_details", [])
    chamber_detail_kinds = {detail.get("kind") for detail in chamber_details}
    chamber_detail_chambers = {detail.get("chamber") for detail in chamber_details}
    summary["chamber_details"] = len(chamber_details)
    summary["chamber_detail_kinds"] = len(chamber_detail_kinds)
    if len(chamber_details) < 140:
        error(errors, f"expected at least 140 public chamber detail records, got {len(chamber_details)}")
    missing_chamber_kinds = sorted(REQUIRED_CHAMBER_DETAIL_KINDS - chamber_detail_kinds)
    if missing_chamber_kinds:
        error(errors, f"missing public chamber detail kinds: {', '.join(missing_chamber_kinds)}")
    for chamber_name in ["House Chamber", "Senate Chamber"]:
        if chamber_name not in chamber_detail_chambers:
            error(errors, f"missing chamber details for {chamber_name}")
    if len([detail for detail in chamber_details if detail.get("kind") == "gallery_bench"]) < 60:
        error(errors, "expected at least 60 public gallery bench records")
    if len([detail for detail in chamber_details if detail.get("kind") == "rostrum_desk"]) < 7:
        error(errors, "expected at least 7 public rostrum desk records")
    if len([detail for detail in chamber_details if detail.get("kind") == "public_lectern"]) < 2:
        error(errors, "expected at least 2 public chamber lectern records")
    if len([detail for detail in chamber_details if detail.get("kind") == "public_work_table"]) < 4:
        error(errors, "expected at least 4 public work table records")
    if len([detail for detail in chamber_details if detail.get("kind") == "gallery_divider"]) < 16:
        error(errors, "expected at least 16 public gallery divider records")
    if len([detail for detail in chamber_details if detail.get("kind") == "balcony_fascia"]) < 4:
        error(errors, "expected at least 4 public balcony fascia records")
    if len([detail for detail in chamber_details if detail.get("kind") == "desk_surface_marker"]) < 10:
        error(errors, "expected at least 10 public desk surface marker records")
    for detail in chamber_details[:12]:
        if not is_vec3(detail.get("center_m")):
            error(errors, f"chamber detail {detail.get('name', '<unknown>')} has invalid center_m")
            break
        assignment = detail.get("assignment", "").lower()
        if "public visual" not in assignment or "operational" not in assignment:
            error(errors, f"chamber detail {detail.get('name', '<unknown>')} lacks public/non-operational boundary")
            break

    circulation_details = interior.get("circulation_details", [])
    circulation_detail_kinds = {detail.get("kind") for detail in circulation_details}
    summary["circulation_details"] = len(circulation_details)
    summary["circulation_detail_kinds"] = len(circulation_detail_kinds)
    if len(circulation_details) < 35:
        error(errors, f"expected at least 35 public circulation detail records, got {len(circulation_details)}")
    missing_circulation_kinds = sorted(REQUIRED_CIRCULATION_DETAIL_KINDS - circulation_detail_kinds)
    if missing_circulation_kinds:
        error(errors, f"missing public circulation detail kinds: {', '.join(missing_circulation_kinds)}")
    for detail in circulation_details:
        if not is_vec3(detail.get("center_m")):
            error(errors, f"circulation detail {detail.get('name', '<unknown>')} has invalid center_m")
            break
        assignment = detail.get("assignment", "").lower()
        if "public orientation" not in assignment or "secure route" not in assignment or "service route" not in assignment:
            error(errors, f"circulation detail {detail.get('name', '<unknown>')} lacks public/non-secure boundary")
            break

    joint_session = interior.get("joint_session", [])
    joint_names = {item.get("name") for item in joint_session}
    summary["joint_session_records"] = len(joint_session)
    missing_joint = sorted(REQUIRED_JOINT_SESSION - joint_names)
    if missing_joint:
        error(errors, f"missing joint-session visual records: {', '.join(missing_joint)}")

    public_art = interior.get("public_art", [])
    light_fixtures = interior.get("light_fixtures", [])
    wall_treatments = interior.get("wall_treatments", [])
    summary["public_art"] = len(public_art)
    summary["light_fixtures"] = len(light_fixtures)
    summary["wall_treatments"] = len(wall_treatments)
    if len(public_art) < 90:
        error(errors, f"expected at least 90 public-art visuals, got {len(public_art)}")
    if len(light_fixtures) < 55:
        error(errors, f"expected at least 55 public light fixtures, got {len(light_fixtures)}")
    if len(wall_treatments) < 10:
        error(errors, f"expected at least 10 wall-treatment records, got {len(wall_treatments)}")
    for record in public_art[:5] + light_fixtures[:5] + wall_treatments[:5]:
        if not is_vec3(record.get("center_m")):
            error(errors, f"interior detail {record.get('name', '<unknown>')} has invalid center_m")
            break

    notice = interior.get("interior_notice", "")
    if "Public schematic only" not in notice or "restricted" not in notice:
        error(errors, "interior_notice must state public schematic and restricted-detail boundary")

    gameplay = metadata.get("gameplay", {})
    gameplay_items = gameplay.get("items", [])
    gameplay_labels = gameplay.get("labels", [])
    flagpole_banners = gameplay.get("flagpole_banners", [])
    summary["gameplay_items"] = len(gameplay_items)
    summary["gameplay_labels"] = len(gameplay_labels)
    summary["flagpole_banners"] = len(flagpole_banners)
    gameplay_ids = {item.get("id") for item in gameplay_items}
    missing_gameplay = sorted(REQUIRED_GAMEPLAY_ITEMS - gameplay_ids)
    if missing_gameplay:
        error(errors, f"missing gameplay item props: {', '.join(missing_gameplay)}")
    if len(gameplay_items) != len(REQUIRED_GAMEPLAY_ITEMS):
        error(errors, f"expected {len(REQUIRED_GAMEPLAY_ITEMS)} gameplay item props, got {len(gameplay_items)}")
    for item in gameplay_items:
        if not is_vec3(item.get("center_m")):
            error(errors, f"gameplay item {item.get('id', '<unknown>')} has invalid center_m")
            break
        if item.get("category") != "gameplay_item" or item.get("non_graphic") is not True:
            error(errors, f"gameplay item {item.get('id', '<unknown>')} must be marked non-graphic gameplay_item")
            break
        if "fictional" not in item.get("public_accuracy", "").lower():
            error(errors, f"gameplay item {item.get('id', '<unknown>')} must be marked fictional")
            break
    gameplay_notice = gameplay.get("notice", "")
    if "Fictional" not in gameplay_notice or "not historical" not in gameplay_notice:
        error(errors, "gameplay notice must state fictional/non-historical boundary")
    banner_ids = {banner.get("id") for banner in flagpole_banners}
    missing_banners = sorted(REQUIRED_FLAGPOLE_BANNERS - banner_ids)
    if missing_banners:
        error(errors, f"missing flagpole banner visuals: {', '.join(missing_banners)}")
    for banner in flagpole_banners:
        if not is_vec3(banner.get("center_m")):
            error(errors, f"flagpole banner {banner.get('id', '<unknown>')} has invalid center_m")
            break
        if "fictional" not in banner.get("public_accuracy", "").lower():
            error(errors, f"flagpole banner {banner.get('id', '<unknown>')} must be marked fictional")
            break

    viewpoints = metadata.get("viewpoints", [])
    viewpoint_labels = {item.get("label") for item in viewpoints}
    summary["viewpoints"] = len(viewpoints)
    missing_viewpoints = sorted(REQUIRED_VIEWPOINTS - viewpoint_labels)
    if missing_viewpoints:
        error(errors, f"missing required viewpoints: {', '.join(missing_viewpoints)}")
    for viewpoint in viewpoints:
        if not is_vec3(viewpoint.get("location_m")) or not is_vec3(viewpoint.get("target_m")):
            error(errors, f"viewpoint {viewpoint.get('label', '<unknown>')} has invalid location/target")
            break
        if not is_number(viewpoint.get("fov")):
            error(errors, f"viewpoint {viewpoint.get('label', '<unknown>')} has invalid fov")
            break

    return summary


def validate_material_manifest(materials: set[str], errors: list[str]) -> dict[str, Any]:
    summary = {"manifest_materials": 0, "missing_manifest_materials": 0, "extra_manifest_materials": 0}
    if not MATERIAL_MANIFEST_PATH.exists():
        error(errors, f"missing Unreal material realism manifest: {MATERIAL_MANIFEST_PATH}")
        return summary

    manifest = json.loads(MATERIAL_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest_materials = set(manifest)
    missing = sorted(materials - manifest_materials)
    extra = sorted(manifest_materials - materials)
    summary["manifest_materials"] = len(manifest_materials)
    summary["missing_manifest_materials"] = len(missing)
    summary["extra_manifest_materials"] = len(extra)
    if missing:
        error(errors, f"material realism manifest missing MTL materials: {', '.join(missing)}")
    if extra:
        error(errors, f"material realism manifest has materials not in MTL: {', '.join(extra)}")

    for name, spec in manifest.items():
        color = spec.get("base_color")
        if not isinstance(color, list) or len(color) != 3 or not all(is_number(item) for item in color):
            error(errors, f"material {name} has invalid base_color")
            break
        for key in ("roughness", "metallic", "specular"):
            value = spec.get(key)
            if not is_number(value) or not (0.0 <= float(value) <= 1.0):
                error(errors, f"material {name} has invalid {key}")
                break
        opacity = spec.get("opacity")
        if opacity is not None and (not is_number(opacity) or not (0.0 <= float(opacity) <= 1.0)):
            error(errors, f"material {name} has invalid opacity")
            break
    return summary


def validate_texture_manifest(materials: set[str], errors: list[str]) -> dict[str, Any]:
    summary = {
        "texture_sets": 0,
        "texture_material_bindings": 0,
        "texture_files": 0,
        "min_texture_size_px": None,
        "expected_min_texture_size_px": MIN_TEXTURE_SIZE_PX,
    }
    if not TEXTURE_MANIFEST_PATH.exists():
        error(errors, f"missing material texture manifest: {TEXTURE_MANIFEST_PATH}")
        return summary
    manifest = json.loads(TEXTURE_MANIFEST_PATH.read_text(encoding="utf-8"))
    sets = manifest.get("sets", {})
    bindings = manifest.get("materials", {})
    summary["texture_sets"] = len(sets)
    summary["texture_material_bindings"] = len(bindings)
    missing_bindings = sorted(materials - set(bindings))
    if missing_bindings:
        error(errors, f"texture manifest missing material bindings: {', '.join(missing_bindings)}")
    unknown_texture_sets = sorted(set(bindings.values()) - set(sets))
    if unknown_texture_sets:
        error(errors, f"texture manifest bindings reference unknown texture sets: {', '.join(unknown_texture_sets)}")
    for set_name, spec in sets.items():
        declared_size = spec.get("size_px")
        if not (
            isinstance(declared_size, list)
            and len(declared_size) == 2
            and all(isinstance(item, int) for item in declared_size)
        ):
            error(errors, f"texture set {set_name} has invalid size_px")
            declared_size = None
        for key in ("basecolor", "normal", "roughness"):
            rel = spec.get(key)
            if not rel:
                error(errors, f"texture set {set_name} missing {key}")
                continue
            path = ROOT / rel
            if not path.exists():
                error(errors, f"texture file missing: {rel}")
            elif path.stat().st_size < 256:
                error(errors, f"texture file too small: {rel}")
            else:
                dimensions = png_dimensions(path)
                if dimensions is None:
                    error(errors, f"texture file is not a valid PNG: {rel}")
                else:
                    width, height = dimensions
                    current_min = min(width, height)
                    if summary["min_texture_size_px"] is None:
                        summary["min_texture_size_px"] = current_min
                    else:
                        summary["min_texture_size_px"] = min(int(summary["min_texture_size_px"]), current_min)
                    if declared_size and [width, height] != declared_size:
                        error(errors, f"texture file {rel} is {width}x{height}, manifest declares {declared_size[0]}x{declared_size[1]}")
                    if width < MIN_TEXTURE_SIZE_PX or height < MIN_TEXTURE_SIZE_PX:
                        error(errors, f"texture file {rel} is below {MIN_TEXTURE_SIZE_PX}px production size: {width}x{height}")
            summary["texture_files"] += 1
    if summary["texture_sets"] < 35:
        error(errors, f"expected at least 35 generated texture sets, got {summary['texture_sets']}")
    return summary


def validate_unreal_importer(errors: list[str]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "path": str(UNREAL_IMPORTER_PATH.relative_to(ROOT)),
        "mesh_files": 0,
        "destination_paths": 0,
        "required_functions": 0,
        "required_calls": 0,
        "report_keys": 0,
        "label_categories": 0,
        "outliner_folders": 0,
        "first_person_markers": 0,
    }
    if not UNREAL_IMPORTER_PATH.exists():
        error(errors, f"missing Unreal import script: {UNREAL_IMPORTER_PATH}")
        return summary

    text = UNREAL_IMPORTER_PATH.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, filename=str(UNREAL_IMPORTER_PATH))
    except SyntaxError as exc:
        error(errors, f"Unreal import script has invalid Python syntax: {exc}")
        return summary

    string_literals = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    functions = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    calls: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            calls.add(node.func.attr)

    missing_meshes = sorted(EXPECTED_UNREAL_MESH_BASENAMES - string_literals)
    missing_destinations = sorted(EXPECTED_UNREAL_DESTINATIONS - string_literals)
    missing_functions = sorted(REQUIRED_UNREAL_FUNCTIONS - functions)
    missing_calls = sorted(REQUIRED_UNREAL_CALLS - calls)
    missing_report_keys = sorted(REQUIRED_UNREAL_REPORT_KEYS - string_literals)
    missing_label_categories = sorted(REQUIRED_UNREAL_LABEL_CATEGORIES - string_literals)
    missing_outliner_folders = sorted(REQUIRED_UNREAL_OUTLINER_FOLDERS - string_literals)
    missing_first_person_markers = sorted(REQUIRED_UNREAL_FIRST_PERSON_MARKERS - string_literals)

    summary["mesh_files"] = len(EXPECTED_UNREAL_MESH_BASENAMES) - len(missing_meshes)
    summary["destination_paths"] = len(EXPECTED_UNREAL_DESTINATIONS) - len(missing_destinations)
    summary["required_functions"] = len(REQUIRED_UNREAL_FUNCTIONS) - len(missing_functions)
    summary["required_calls"] = len(REQUIRED_UNREAL_CALLS) - len(missing_calls)
    summary["report_keys"] = len(REQUIRED_UNREAL_REPORT_KEYS) - len(missing_report_keys)
    summary["label_categories"] = len(REQUIRED_UNREAL_LABEL_CATEGORIES) - len(missing_label_categories)
    summary["outliner_folders"] = len(REQUIRED_UNREAL_OUTLINER_FOLDERS) - len(missing_outliner_folders)
    summary["first_person_markers"] = len(REQUIRED_UNREAL_FIRST_PERSON_MARKERS) - len(missing_first_person_markers)
    summary["missing"] = {
        "mesh_files": missing_meshes,
        "destination_paths": missing_destinations,
        "required_functions": missing_functions,
        "required_calls": missing_calls,
        "report_keys": missing_report_keys,
        "label_categories": missing_label_categories,
        "outliner_folders": missing_outliner_folders,
        "first_person_markers": missing_first_person_markers,
    }

    if missing_meshes:
        error(errors, f"Unreal importer missing generated mesh files: {', '.join(missing_meshes)}")
    if missing_destinations:
        error(errors, f"Unreal importer missing destination paths: {', '.join(missing_destinations)}")
    if missing_functions:
        error(errors, f"Unreal importer missing required functions: {', '.join(missing_functions)}")
    if missing_calls:
        error(errors, f"Unreal importer missing required helper calls: {', '.join(missing_calls)}")
    if missing_report_keys:
        error(errors, f"Unreal import report missing required keys: {', '.join(missing_report_keys)}")
    if missing_label_categories:
        error(errors, f"Unreal importer missing label categories: {', '.join(missing_label_categories)}")
    if missing_outliner_folders:
        error(errors, f"Unreal importer missing outliner folders: {', '.join(missing_outliner_folders)}")
    if missing_first_person_markers:
        error(errors, f"Unreal importer missing first-person setup markers: {', '.join(missing_first_person_markers)}")

    return summary


def validate_unreal_project_config(errors: list[str]) -> dict[str, Any]:
    config_paths = {
        "CapitolMap.uproject": UPROJECT_PATH,
        "Config/DefaultEngine.ini": DEFAULT_ENGINE_PATH,
        "Config/DefaultGame.ini": DEFAULT_GAME_PATH,
    }
    summary: dict[str, Any] = {
        "files": 0,
        "required_markers": 0,
        "missing": {},
    }

    for rel, path in config_paths.items():
        if not path.exists():
            error(errors, f"missing Unreal project config file: {path}")
            summary["missing"][rel] = sorted(REQUIRED_UNREAL_PROJECT_CONFIG_MARKERS.get(rel, set()))
            continue
        summary["files"] += 1
        text = path.read_text(encoding="utf-8")
        missing = sorted(marker for marker in REQUIRED_UNREAL_PROJECT_CONFIG_MARKERS.get(rel, set()) if marker not in text)
        summary["required_markers"] += len(REQUIRED_UNREAL_PROJECT_CONFIG_MARKERS.get(rel, set())) - len(missing)
        if missing:
            summary["missing"][rel] = missing
            error(errors, f"{rel} missing Unreal project config markers: {', '.join(missing)}")

    return summary


def main() -> int:
    errors: list[str] = []
    if not METADATA_PATH.exists():
        error(errors, f"missing metadata: {METADATA_PATH}")
        metadata: dict[str, Any] = {}
    else:
        metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    materials = parse_mtl(MTL_PATH, errors)
    metadata_summary = validate_metadata(metadata, errors)
    material_summary = validate_material_manifest(materials, errors)
    texture_summary = validate_texture_manifest(materials, errors)
    unreal_importer_summary = validate_unreal_importer(errors)
    unreal_project_config_summary = validate_unreal_project_config(errors)
    mesh_stats = [parse_obj(ROOT / rel, materials, errors) for rel in metadata.get("meshes", [])]

    report = {
        "ok": not errors,
        "root": str(ROOT),
        "metadata": metadata_summary,
        "materials": material_summary,
        "textures": texture_summary,
        "unreal_importer": unreal_importer_summary,
        "unreal_project_config": unreal_project_config_summary,
        "meshes": mesh_stats,
        "errors": errors,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if errors:
        print(f"Capitol package validation FAILED with {len(errors)} error(s).")
        for item in errors:
            print(f"- {item}")
        print(f"Wrote report: {REPORT_PATH}")
        return 1

    triangles = sum(int(mesh["triangles"]) for mesh in mesh_stats)
    vertices = sum(int(mesh["vertices"]) for mesh in mesh_stats)
    print("Capitol package validation OK")
    print(f"Meshes: {len(mesh_stats)}")
    print(f"Vertices: {vertices:,}")
    print(f"Texture coordinates: {sum(int(mesh.get('uvs', 0)) for mesh in mesh_stats):,}")
    print(f"Triangles: {triangles:,}")
    print(f"Buildings: {metadata_summary.get('buildings', 0):,}")
    print(f"Roads/paths: {metadata_summary.get('roads', 0):,}")
    print(f"Bike features: {metadata_summary.get('bike_lanes', 0):,}")
    print(f"Pedestrian paths: {metadata_summary.get('pedestrian_paths', 0):,}")
    print(f"Curbs: {metadata_summary.get('curbs', 0):,}")
    print(f"Lane edge markings: {metadata_summary.get('lane_edge_markings', 0):,}")
    print(f"Street markers: {metadata_summary.get('street_markers', 0):,}")
    print(f"Replaced OSM building footprints: {metadata_summary.get('replaced_buildings', 0):,}")
    print(f"Surrounding building details: {metadata_summary.get('building_details', 0):,}")
    print(f"Streetscape props: {metadata_summary.get('streetscape_props', 0):,}")
    print(f"Grounds details: {metadata_summary.get('grounds_details', 0):,}")
    print(f"Grounds walk lamps: {metadata_summary.get('grounds_walk_lamps', 0):,}")
    print(f"Facade/furniture details: {metadata_summary.get('facade_details', 0):,}")
    print(f"House seats: {metadata_summary.get('house_seats', 0):,}")
    print(f"Senate desks: {metadata_summary.get('senate_desks', 0):,}")
    print(f"Seating sections: {metadata_summary.get('seating_sections', 0):,}")
    print(f"Chamber details: {metadata_summary.get('chamber_details', 0):,}")
    print(f"Circulation details: {metadata_summary.get('circulation_details', 0):,}")
    print(f"Public art visuals: {metadata_summary.get('public_art', 0):,}")
    print(f"Light fixtures: {metadata_summary.get('light_fixtures', 0):,}")
    print(f"Wall treatments: {metadata_summary.get('wall_treatments', 0):,}")
    print(f"Gameplay item props: {metadata_summary.get('gameplay_items', 0):,}")
    print(f"Flagpole banner visuals: {metadata_summary.get('flagpole_banners', 0):,}")
    print(f"Realism materials: {material_summary.get('manifest_materials', 0):,}")
    print(f"Texture sets: {texture_summary.get('texture_sets', 0):,}")
    print(f"Viewpoints: {metadata_summary.get('viewpoints', 0):,}")
    print(f"Unreal importer meshes: {unreal_importer_summary.get('mesh_files', 0):,}")
    print(f"Unreal importer report keys: {unreal_importer_summary.get('report_keys', 0):,}")
    print(f"Unreal project config markers: {unreal_project_config_summary.get('required_markers', 0):,}")
    print(f"Wrote report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
