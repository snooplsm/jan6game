"""Import the generated Capitol map package into an Unreal level.

Run from Unreal Editor:
  Tools > Execute Python Script... > select this file

The script imports generated OBJ meshes and places them at their authored
centimeter coordinates. It also spawns labels, generated scene helpers, and
camera viewpoints for the public exterior/interior schematic.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import unreal


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
MESH_DIR = PACKAGE_ROOT / "generated" / "meshes"
METADATA_PATH = PACKAGE_ROOT / "generated" / "data" / "capitol_scene_metadata.json"
UNREAL_IMPORT_REPORT_PATH = PACKAGE_ROOT / "generated" / "data" / "unreal_import_report.json"
MATERIAL_MANIFEST_PATH = PACKAGE_ROOT / "unreal" / "material_realism_manifest.json"
TEXTURE_MANIFEST_PATH = PACKAGE_ROOT / "generated" / "data" / "material_texture_manifest.json"
DESTINATION_PATH = "/Game/CapitolMap/Generated"
MATERIAL_DESTINATION_PATH = "/Game/CapitolMap/Materials"
TEXTURE_DESTINATION_PATH = "/Game/CapitolMap/Textures"
MAP_DESTINATION_PATH = "/Game/CapitolMap/Maps"
MAP_ASSET_PATH = f"{MAP_DESTINATION_PATH}/CapitolMap_Level"
TEXTURE_KIND_SETTINGS = {
    "basecolor": {
        "srgb": True,
        "compression_settings": ["TC_DEFAULT"],
        "texture_group": ["TEXTUREGROUP_WORLD", "TEXTUREGROUP_World"],
        "mip_gen_settings": ["TMGS_FROM_TEXTURE_GROUP"],
        "filter": ["TF_DEFAULT"],
        "sampler_type": ["SAMPLERTYPE_COLOR"],
    },
    "normal": {
        "srgb": False,
        "compression_settings": ["TC_NORMALMAP"],
        "texture_group": ["TEXTUREGROUP_WORLD_NORMAL_MAP", "TEXTUREGROUP_WorldNormalMap", "TEXTUREGROUP_WORLD"],
        "mip_gen_settings": ["TMGS_FROM_TEXTURE_GROUP"],
        "filter": ["TF_DEFAULT"],
        "sampler_type": ["SAMPLERTYPE_NORMAL"],
    },
    "roughness": {
        "srgb": False,
        "compression_settings": ["TC_GRAYSCALE", "TC_MASKS"],
        "texture_group": ["TEXTUREGROUP_WORLD_SPECULAR", "TEXTUREGROUP_WorldSpecular", "TEXTUREGROUP_WORLD"],
        "mip_gen_settings": ["TMGS_FROM_TEXTURE_GROUP"],
        "filter": ["TF_DEFAULT"],
        "sampler_type": ["SAMPLERTYPE_LINEAR_GRAYSCALE", "SAMPLERTYPE_MASKS"],
    },
}
MATERIAL_GRAPH_FEATURES = {
    "basecolor_property": "MP_BASE_COLOR",
    "normal_property": "MP_NORMAL",
    "roughness_property": "MP_ROUGHNESS",
    "metallic_property": "MP_METALLIC",
    "specular_property": "MP_SPECULAR",
    "opacity_property": "MP_OPACITY",
    "clear_coat_property": "MP_CLEAR_COAT",
    "clear_coat_roughness_property": "MP_CLEAR_COAT_ROUGHNESS",
    "supports_clear_coat_shading": True,
    "uses_texture_samples": True,
    "uses_tangent_space_normals": True,
    "two_sided_by_default": True,
    "adds_editor_comment": True,
}
PLAYER_START_LABEL = "CapitolMap_PlayerStart_WestFront"
PLAYER_START_LOCATION_CM = [-9000.0, 0.0, 120.0]
PLAYTEST_PAWN_LABEL = "CapitolMap_Playtest_DefaultPawn"
PLAYTEST_PAWN_LOCATION_CM = [-9600.0, -650.0, 160.0]
PLAYTEST_PAWN_ROTATION_DEG = [0.0, 4.0, 0.0]
NAV_MESH_BOUNDS_LABEL = "CapitolMap_NavMeshBounds_CentralCampus"
NAV_MESH_BOUNDS_LOCATION_CM = [0.0, 0.0, 2500.0]
NAV_MESH_BOUNDS_SCALE = [750.0, 750.0, 45.0]
COLLISION_PROXY_FOLDER = "CapitolMap/Collision"
FIRST_PERSON_COLLISION_PROXY_TAG = "CapitolMap_FirstPersonCollisionProxy"
FIRST_PERSON_COLLISION_PROXIES = [
    {
        "label": "CapitolMap_Collision_WestFrontPlaza",
        "location_cm": [-7600.0, 0.0, 42.0],
        "scale": [48.0, 88.0, 0.22],
        "purpose": "public west-front plaza and entry approach walkable proxy",
    },
    {
        "label": "CapitolMap_Collision_EastFrontPlaza",
        "location_cm": [7600.0, 0.0, 42.0],
        "scale": [48.0, 88.0, 0.22],
        "purpose": "public east-front plaza and entry approach walkable proxy",
    },
    {
        "label": "CapitolMap_Collision_NorthWingApproach",
        "location_cm": [0.0, 10100.0, 48.0],
        "scale": [34.0, 32.0, 0.22],
        "purpose": "public north wing approach walkable proxy",
    },
    {
        "label": "CapitolMap_Collision_SouthWingApproach",
        "location_cm": [0.0, -10100.0, 48.0],
        "scale": [34.0, 32.0, 0.22],
        "purpose": "public south wing approach walkable proxy",
    },
    {
        "label": "CapitolMap_Collision_RotundaPublicFloor",
        "location_cm": [0.0, 0.0, 448.0],
        "scale": [15.5, 15.5, 0.16],
        "purpose": "public Rotunda floor walkable proxy",
    },
    {
        "label": "CapitolMap_Collision_HouseChamberPublicFloor",
        "location_cm": [0.0, -7000.0, 448.0],
        "scale": [48.0, 32.0, 0.16],
        "purpose": "public House chamber schematic floor walkable proxy",
    },
    {
        "label": "CapitolMap_Collision_SenateChamberPublicFloor",
        "location_cm": [0.0, 7000.0, 448.0],
        "scale": [38.0, 30.0, 0.16],
        "purpose": "public Senate chamber schematic floor walkable proxy",
    },
    {
        "label": "CapitolMap_Collision_PublicConnectorSpine",
        "location_cm": [0.0, 0.0, 448.0],
        "scale": [20.0, 92.0, 0.14],
        "purpose": "public schematic connector spine walkable proxy",
    },
]
ENVIRONMENT_IMPORT_SETUP = {
    "directional_light_actor_class": "DirectionalLight",
    "directional_light_label": "CapitolMap_Sun_DirectionalLight",
    "directional_light_location_cm": [-18000.0, -22000.0, 38000.0],
    "directional_light_rotation_deg": [-42.0, -34.0, 0.0],
    "directional_light_intensity": 4.2,
    "sky_light_actor_class": "SkyLight",
    "sky_light_label": "CapitolMap_SkyLight",
    "sky_light_location_cm": [0.0, 0.0, 8000.0],
    "sky_light_intensity": 0.85,
    "sky_atmosphere_actor_class": "SkyAtmosphere",
    "sky_atmosphere_label": "CapitolMap_SkyAtmosphere",
    "exponential_height_fog_actor_class": "ExponentialHeightFog",
    "exponential_height_fog_label": "CapitolMap_AtmosphericFog",
    "reflection_capture_actor_class": "SphereReflectionCapture",
    "reflection_capture_label": "CapitolMap_CampusReflectionCapture",
    "reflection_capture_radius_cm": 42000.0,
    "post_process_actor_class": "PostProcessVolume",
    "post_process_label": "CapitolMap_GlobalPostProcess",
    "post_process_location_cm": [0.0, 0.0, 5000.0],
    "post_process_scale_cm": [620.0, 620.0, 125.0],
    "post_process_exposure_min": 0.65,
    "post_process_exposure_max": 1.25,
}
FIRST_PERSON_IMPORT_SETUP = {
    "static_mesh_lod_group": "LargeProp",
    "auto_generate_collision": True,
    "collision_trace": "CTF_USE_COMPLEX_AS_SIMPLE",
    "actor_collision": "QUERY_AND_PHYSICS",
    "can_affect_navigation": True,
    "nanite_enabled": True,
    "player_start_actor_class": "PlayerStart",
    "player_start_label": PLAYER_START_LABEL,
    "player_start_location_cm": PLAYER_START_LOCATION_CM,
    "playtest_pawn_actor_class": "DefaultPawn",
    "playtest_pawn_label": PLAYTEST_PAWN_LABEL,
    "playtest_pawn_location_cm": PLAYTEST_PAWN_LOCATION_CM,
    "playtest_pawn_rotation_deg": PLAYTEST_PAWN_ROTATION_DEG,
    "playtest_pawn_auto_possess": "PLAYER0",
    "nav_mesh_bounds_actor_class": "NavMeshBoundsVolume",
    "nav_mesh_bounds_label": NAV_MESH_BOUNDS_LABEL,
    "nav_mesh_bounds_location_cm": NAV_MESH_BOUNDS_LOCATION_CM,
    "nav_mesh_bounds_scale_cm": NAV_MESH_BOUNDS_SCALE,
    "collision_proxy_actor_class": "BlockingVolume",
    "collision_proxy_folder": COLLISION_PROXY_FOLDER,
    "collision_proxy_tag": FIRST_PERSON_COLLISION_PROXY_TAG,
    "collision_proxy_count": len(FIRST_PERSON_COLLISION_PROXIES),
}

MESH_FILES = [
    "capitol_exterior_buildings.obj",
    "capitol_exterior_roads_bike_lanes_markers.obj",
    "capitol_landmark_visual_details.obj",
    "capitol_public_interior_schematic.obj",
    "capitol_gameplay_items.obj",
]

INTERIOR_TOPDOWN_INSPECTION = {
    "camera_label": "CapitolMap_Camera_Chambers_TopDown",
    "visible_tag": "CapitolMap_VisibleForInteriorTopDown",
    "hide_tag": "CapitolMap_HideForInteriorTopDown",
    "visible_folder": "CapitolMap/Meshes/InteriorTopDownVisible",
    "hide_folder": "CapitolMap/Meshes/HideForInteriorTopDown",
    "note": "Hide actors tagged CapitolMap_HideForInteriorTopDown to inspect chambers from the top-down camera.",
}

INTERIOR_CUTAWAY_INSPECTION = {
    "camera_label": "CapitolMap_Camera_Interior_Cutaway",
    "visible_tag": "CapitolMap_VisibleForInteriorCutaway",
    "hide_tag": "CapitolMap_HideForInteriorCutaway",
    "visible_folder": INTERIOR_TOPDOWN_INSPECTION["visible_folder"],
    "hide_folder": INTERIOR_TOPDOWN_INSPECTION["hide_folder"],
    "note": "Hide actors tagged CapitolMap_HideForInteriorCutaway to inspect the public interior schematic without exterior, roof, road, or gameplay meshes.",
}

MESH_INSPECTION_VISIBILITY = {
    "capitol_exterior_buildings.obj": {
        "folder": INTERIOR_TOPDOWN_INSPECTION["hide_folder"],
        "tags": [
            "CapitolMap_Mesh",
            "CapitolMap_Exterior",
            INTERIOR_TOPDOWN_INSPECTION["hide_tag"],
            INTERIOR_CUTAWAY_INSPECTION["hide_tag"],
        ],
    },
    "capitol_exterior_roads_bike_lanes_markers.obj": {
        "folder": INTERIOR_TOPDOWN_INSPECTION["hide_folder"],
        "tags": [
            "CapitolMap_Mesh",
            "CapitolMap_Exterior",
            INTERIOR_TOPDOWN_INSPECTION["hide_tag"],
            INTERIOR_CUTAWAY_INSPECTION["hide_tag"],
        ],
    },
    "capitol_landmark_visual_details.obj": {
        "folder": INTERIOR_TOPDOWN_INSPECTION["hide_folder"],
        "tags": [
            "CapitolMap_Mesh",
            "CapitolMap_Landmark",
            INTERIOR_TOPDOWN_INSPECTION["hide_tag"],
            INTERIOR_CUTAWAY_INSPECTION["hide_tag"],
        ],
    },
    "capitol_public_interior_schematic.obj": {
        "folder": INTERIOR_TOPDOWN_INSPECTION["visible_folder"],
        "tags": [
            "CapitolMap_Mesh",
            "CapitolMap_PublicInterior",
            INTERIOR_TOPDOWN_INSPECTION["visible_tag"],
            INTERIOR_CUTAWAY_INSPECTION["visible_tag"],
        ],
    },
    "capitol_gameplay_items.obj": {
        "folder": INTERIOR_TOPDOWN_INSPECTION["hide_folder"],
        "tags": [
            "CapitolMap_Mesh",
            "CapitolMap_GameplayPreview",
            INTERIOR_TOPDOWN_INSPECTION["hide_tag"],
            INTERIOR_CUTAWAY_INSPECTION["hide_tag"],
        ],
    },
}

DEFAULT_VIEWPOINTS = [
    {
        "label": "CapitolMap_Camera_Overview",
        "location_m": [-190.0, -210.0, 120.0],
        "target_m": [0.0, 0.0, 8.0],
        "fov": 45.0,
    },
    {
        "label": "CapitolMap_Camera_WestFront_FirstPerson",
        "location_m": [-105.0, 0.0, 1.8],
        "target_m": [0.0, 0.0, 5.0],
        "fov": 78.0,
    },
    {
        "label": "CapitolMap_Camera_WestGrounds",
        "location_m": [-360.0, -125.0, 42.0],
        "target_m": [-235.0, 0.0, 1.0],
        "fov": 52.0,
    },
    {
        "label": "CapitolMap_Camera_Rotunda",
        "location_m": [-23.0, -24.0, 7.5],
        "target_m": [0.0, 0.0, 5.0],
        "fov": 64.0,
    },
    {
        "label": "CapitolMap_Camera_HouseChamber_JointSession",
        "location_m": [0.0, -108.0, 12.0],
        "target_m": [0.0, -60.0, 5.5],
        "fov": 58.0,
    },
    {
        "label": "CapitolMap_Camera_SenateChamber",
        "location_m": [0.0, 108.0, 11.0],
        "target_m": [0.0, 70.0, 5.5],
        "fov": 58.0,
    },
    {
        "label": "CapitolMap_Camera_Chambers_TopDown",
        "location_m": [0.0, -2.0, 92.0],
        "target_m": [0.0, -2.0, 5.4],
        "fov": 48.0,
    },
    {
        "label": "CapitolMap_Camera_HouseChamber_TopDown",
        "location_m": [0.0, -72.0, 92.0],
        "target_m": [0.0, -72.0, 5.4],
        "fov": 44.0,
    },
    {
        "label": "CapitolMap_Camera_SenateChamber_TopDown",
        "location_m": [0.0, 68.0, 92.0],
        "target_m": [0.0, 68.0, 5.4],
        "fov": 44.0,
    },
    {
        "label": "CapitolMap_Camera_Interior_Cutaway",
        "location_m": [0.0, -8.0, 120.0],
        "target_m": [0.0, 0.0, 5.2],
        "fov": 64.0,
    },
    {
        "label": "CapitolMap_Camera_PublicInterior_TopDown",
        "location_m": [0.0, 0.0, 150.0],
        "target_m": [0.0, 0.0, 5.2],
        "fov": 58.0,
    },
    {
        "label": "CapitolMap_Camera_GameplayItems",
        "location_m": [-145.0, -145.0, 9.0],
        "target_m": [-124.0, -122.0, 1.2],
        "fov": 58.0,
    },
]

LABEL_COLORS = {
    "major_public_space": (250, 245, 230, 255),
    "legislative_chamber": (255, 214, 140, 255),
    "visitor_gallery": (182, 218, 255, 255),
    "generic_office_zone": (175, 230, 205, 255),
    "seating": (246, 224, 153, 255),
    "seating_section": (244, 210, 136, 255),
    "chamber_detail": (214, 184, 112, 255),
    "public_circulation_detail": (170, 220, 235, 255),
    "signage_detail": (185, 225, 170, 255),
    "door_detail": (190, 210, 230, 255),
    "furnishing_detail": (206, 216, 184, 255),
    "joint_session": (255, 190, 120, 255),
    "public_art": (236, 198, 116, 255),
    "lighting": (255, 220, 140, 255),
    "wall_treatment": (224, 196, 152, 255),
    "wall_finish_detail": (218, 202, 170, 255),
    "landmark": (235, 235, 220, 255),
    "street_name": (210, 230, 210, 255),
    "building": (226, 226, 214, 255),
    "gameplay_item": (255, 155, 105, 255),
}


def log(message: str) -> None:
    unreal.log(f"[CapitolMap] {message}")


def set_property(obj: Any, name: str, value: Any) -> bool:
    """Best-effort editor property assignment across UE Python versions."""
    try:
        obj.set_editor_property(name, value)
        return True
    except Exception:
        return False


def get_property(obj: Any, name: str) -> Any:
    try:
        return obj.get_editor_property(name)
    except Exception:
        return None


def set_enum_property(obj: Any, property_name: str, enum_type_name: str, member_names: list[str]) -> str | None:
    enum_type = getattr(unreal, enum_type_name, None)
    if enum_type is None:
        return None
    for member_name in member_names:
        member = getattr(enum_type, member_name, None)
        if member is not None and set_property(obj, property_name, member):
            return member_name
    return None


def set_actor_tags(actor: Any, tags: list[str]) -> None:
    """Best-effort tag assignment across UE Python versions."""
    try:
        unreal_tags = [unreal.Name(tag) for tag in tags] if hasattr(unreal, "Name") else tags
        if set_property(actor, "tags", unreal_tags):
            return
    except Exception:
        pass
    set_property(actor, "tags", tags)


def load_metadata() -> dict[str, Any]:
    return json.loads(METADATA_PATH.read_text(encoding="utf-8"))


def load_material_manifest() -> dict[str, Any]:
    if not MATERIAL_MANIFEST_PATH.exists():
        return {}
    return json.loads(MATERIAL_MANIFEST_PATH.read_text(encoding="utf-8"))


def load_texture_manifest() -> dict[str, Any]:
    if not TEXTURE_MANIFEST_PATH.exists():
        return {}
    return json.loads(TEXTURE_MANIFEST_PATH.read_text(encoding="utf-8"))


def ensure_content_dirs() -> None:
    for path in ["/Game/CapitolMap", DESTINATION_PATH, MATERIAL_DESTINATION_PATH, TEXTURE_DESTINATION_PATH, MAP_DESTINATION_PATH]:
        try:
            unreal.EditorAssetLibrary.make_directory(path)
        except Exception as exc:
            log(f"Could not create content directory {path}: {exc}")


def prepare_level() -> None:
    """Create or open the generated map level when the editor API supports it."""
    ensure_content_dirs()
    try:
        if unreal.EditorAssetLibrary.does_asset_exist(MAP_ASSET_PATH):
            if hasattr(unreal.EditorLevelLibrary, "load_level"):
                unreal.EditorLevelLibrary.load_level(MAP_ASSET_PATH)
                log(f"Loaded existing level {MAP_ASSET_PATH}")
                return
        if hasattr(unreal.EditorLevelLibrary, "new_level"):
            unreal.EditorLevelLibrary.new_level(MAP_ASSET_PATH)
            log(f"Created level {MAP_ASSET_PATH}")
            return
        log("Level creation API unavailable; using the currently open level")
    except Exception as exc:
        log(f"Level preparation skipped; using the currently open level: {exc}")


def make_import_options() -> Any | None:
    """Configure the OBJ/static-mesh import path when the FBX UI wrapper exists."""
    try:
        options = unreal.FbxImportUI()
    except Exception as exc:
        log(f"Using default OBJ import options: {exc}")
        return None

    set_property(options, "import_mesh", True)
    set_property(options, "import_as_skeletal", False)
    set_property(options, "import_materials", True)
    set_property(options, "import_textures", False)
    set_property(options, "automated_import_should_detect_type", False)

    static_mesh_data = get_property(options, "static_mesh_import_data")
    if static_mesh_data:
        set_property(static_mesh_data, "combine_meshes", True)
        set_property(static_mesh_data, "generate_lightmap_u_vs", True)
        set_property(static_mesh_data, "auto_generate_collision", True)
        set_property(static_mesh_data, "import_translation", unreal.Vector(0.0, 0.0, 0.0))
        set_property(static_mesh_data, "import_rotation", unreal.Rotator(0.0, 0.0, 0.0))
        set_property(static_mesh_data, "import_uniform_scale", 1.0)

    return options


def import_meshes() -> list[str]:
    ensure_content_dirs()
    options = make_import_options()
    tasks = []
    for mesh_name in MESH_FILES:
        source_path = MESH_DIR / mesh_name
        if not source_path.exists():
            log(f"WARNING: source mesh missing: {source_path}")
            continue
        task = unreal.AssetImportTask()
        task.filename = str(source_path)
        task.destination_path = DESTINATION_PATH
        task.automated = True
        task.replace_existing = True
        task.save = True
        if options is not None:
            task.options = options
        tasks.append(task)

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    imported = []
    for mesh_name in MESH_FILES:
        asset_path = f"{DESTINATION_PATH}/{Path(mesh_name).stem}"
        if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
            imported.append(asset_path)
            log(f"Imported {asset_path}")
        else:
            log(f"WARNING: expected imported asset missing: {asset_path}")
    return imported


def texture_asset_name(rel_path: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in Path(rel_path).stem).strip("_")
    return f"T_{safe or 'CapitolTexture'}"


def texture_asset_path(rel_path: str) -> str:
    return f"{TEXTURE_DESTINATION_PATH}/{texture_asset_name(rel_path)}"


def configure_texture_asset(asset_path: str, texture_kind: str) -> None:
    texture = unreal.EditorAssetLibrary.load_asset(asset_path)
    if not texture:
        return

    settings = TEXTURE_KIND_SETTINGS.get(texture_kind, {})
    set_property(texture, "srgb", bool(settings.get("srgb", texture_kind == "basecolor")))
    set_enum_property(texture, "compression_settings", "TextureCompressionSettings", settings.get("compression_settings", []))
    set_enum_property(texture, "lod_group", "TextureGroup", settings.get("texture_group", []))
    set_enum_property(texture, "mip_gen_settings", "TextureMipGenSettings", settings.get("mip_gen_settings", []))
    set_enum_property(texture, "filter", "TextureFilter", settings.get("filter", []))

    try:
        unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
    except Exception:
        pass


def import_texture_assets() -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    manifest = load_texture_manifest()
    sets = manifest.get("sets", {})
    material_bindings = manifest.get("materials", {})
    if not sets:
        log("Texture manifest missing or empty; materials will use scalar/color fallback")
        return {}, material_bindings

    ensure_content_dirs()
    tasks = []
    for texture_set in sets.values():
        for texture_kind in ("basecolor", "normal", "roughness"):
            rel_path = texture_set.get(texture_kind)
            if not rel_path:
                continue
            source_path = PACKAGE_ROOT / rel_path
            if not source_path.exists():
                log(f"WARNING: texture source missing: {source_path}")
                continue
            task = unreal.AssetImportTask()
            task.filename = str(source_path)
            task.destination_path = TEXTURE_DESTINATION_PATH
            task.destination_name = texture_asset_name(rel_path)
            task.automated = True
            task.replace_existing = True
            task.save = True
            tasks.append(task)

    if tasks:
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)

    imported: dict[str, dict[str, str]] = {}
    for set_name, texture_set in sets.items():
        imported[set_name] = {}
        for texture_kind in ("basecolor", "normal", "roughness"):
            rel_path = texture_set.get(texture_kind)
            if not rel_path:
                continue
            asset_path = texture_asset_path(rel_path)
            if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
                configure_texture_asset(asset_path, texture_kind)
                imported[set_name][texture_kind] = asset_path
            else:
                log(f"WARNING: expected texture asset missing: {asset_path}")

    log(f"Imported/configured {sum(len(value) for value in imported.values())} texture assets")
    return imported, material_bindings


def configure_static_mesh(asset_path: str) -> None:
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if not asset:
        return

    set_property(asset, "lod_group", "LargeProp")

    body_setup = get_property(asset, "body_setup")
    if body_setup and hasattr(unreal, "CollisionTraceFlag"):
        set_property(
            body_setup,
            "collision_trace_flag",
            unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE,
        )

    nanite_settings = get_property(asset, "nanite_settings")
    if nanite_settings:
        set_property(nanite_settings, "enabled", True)
        set_property(asset, "nanite_settings", nanite_settings)

    try:
        unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
    except Exception as exc:
        log(f"Could not save configured mesh {asset_path}: {exc}")


def asset_name_for_material(material_name: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in material_name).strip("_")
    return f"M_{safe or 'CapitolMaterial'}"


def material_asset_path(material_name: str) -> str:
    return f"{MATERIAL_DESTINATION_PATH}/{asset_name_for_material(material_name)}"


def create_material_constant(material: Any, expression_class: Any, value: Any, x: int, y: int) -> Any | None:
    if not hasattr(unreal, "MaterialEditingLibrary"):
        return None
    try:
        expression = unreal.MaterialEditingLibrary.create_material_expression(material, expression_class, x, y)
        if expression is not None:
            set_property(expression, "constant", value)
            set_property(expression, "default_value", value)
        return expression
    except Exception:
        return None


def create_texture_sample(material: Any, texture_asset_path: str, x: int, y: int, sampler_type_names: list[str] | None = None) -> Any | None:
    if not hasattr(unreal, "MaterialEditingLibrary") or not hasattr(unreal, "MaterialExpressionTextureSample"):
        return None
    texture = unreal.EditorAssetLibrary.load_asset(texture_asset_path)
    if not texture:
        return None
    try:
        expression = unreal.MaterialEditingLibrary.create_material_expression(
            material,
            unreal.MaterialExpressionTextureSample,
            x,
            y,
        )
        if expression is None:
            return None
        set_property(expression, "texture", texture)
        if sampler_type_names:
            set_enum_property(expression, "sampler_type", "MaterialSamplerType", sampler_type_names)
        set_property(expression, "desc", Path(texture_asset_path).name)
        return expression
    except Exception:
        return None


def create_material_comment(material: Any, text: str, x: int, y: int, width: int, height: int) -> Any | None:
    if not hasattr(unreal, "MaterialEditingLibrary") or not hasattr(unreal, "MaterialExpressionComment"):
        return None
    try:
        comment = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionComment, x, y)
        if comment is None:
            return None
        set_property(comment, "text", text)
        set_property(comment, "size_x", width)
        set_property(comment, "size_y", height)
        return comment
    except Exception:
        return None


def connect_material_property(expression: Any, output_name: str, property_name: str) -> None:
    if expression is None or not hasattr(unreal, "MaterialEditingLibrary") or not hasattr(unreal, "MaterialProperty"):
        return
    material_property = getattr(unreal.MaterialProperty, property_name, None)
    if material_property is None:
        return
    try:
        unreal.MaterialEditingLibrary.connect_material_property(expression, output_name, material_property)
    except Exception:
        pass


def configure_unreal_material(material: Any, spec: dict[str, Any], texture_set: dict[str, str] | None = None) -> None:
    color = spec.get("base_color", [0.72, 0.72, 0.72])
    roughness = float(spec.get("roughness", 0.75))
    metallic = float(spec.get("metallic", 0.0))
    specular = float(spec.get("specular", 0.3))
    clear_coat = spec.get("clear_coat")
    clear_coat_roughness = spec.get("clear_coat_roughness")
    texture_set = texture_set or {}
    set_property(material, "two_sided", True)
    set_property(material, "use_material_attributes", False)
    set_property(material, "tangent_space_normal", True)
    if clear_coat is not None and float(clear_coat) > 0.0:
        set_enum_property(material, "shading_model", "MaterialShadingModel", ["MSM_CLEAR_COAT"])

    if hasattr(unreal, "MaterialEditingLibrary"):
        try:
            unreal.MaterialEditingLibrary.delete_all_material_expressions(material)
        except Exception:
            pass
        create_material_comment(
            material,
            "CapitolMap generated PBR setup: basecolor, normal, and roughness maps are imported from generated/textures; scalar parameters remain editable.",
            -900,
            -390,
            760,
            120,
        )

    basecolor_sample = (
        create_texture_sample(
            material,
            texture_set.get("basecolor", ""),
            -760,
            -160,
            TEXTURE_KIND_SETTINGS["basecolor"]["sampler_type"],
        )
        if texture_set.get("basecolor")
        else None
    )
    normal_sample = (
        create_texture_sample(
            material,
            texture_set.get("normal", ""),
            -760,
            60,
            TEXTURE_KIND_SETTINGS["normal"]["sampler_type"],
        )
        if texture_set.get("normal")
        else None
    )
    roughness_sample = (
        create_texture_sample(
            material,
            texture_set.get("roughness", ""),
            -760,
            260,
            TEXTURE_KIND_SETTINGS["roughness"]["sampler_type"],
        )
        if texture_set.get("roughness")
        else None
    )

    if basecolor_sample is not None:
        connect_material_property(basecolor_sample, "RGB", "MP_BASE_COLOR")
    if normal_sample is not None:
        connect_material_property(normal_sample, "RGB", "MP_NORMAL")
    if roughness_sample is not None:
        connect_material_property(roughness_sample, "R", "MP_ROUGHNESS")

    if basecolor_sample is None and hasattr(unreal, "MaterialExpressionConstant3Vector"):
        color_expr = create_material_constant(
            material,
            unreal.MaterialExpressionConstant3Vector,
            unreal.LinearColor(float(color[0]), float(color[1]), float(color[2]), 1.0),
            -520,
            -120,
        )
        connect_material_property(color_expr, "", "MP_BASE_COLOR")

    if hasattr(unreal, "MaterialExpressionScalarParameter"):
        # Parameters make the generated material easier to tune by hand later.
        settings = [
            ("Metallic", metallic, "MP_METALLIC", -260, 80),
            ("Specular", specular, "MP_SPECULAR", -260, 200),
        ]
        if roughness_sample is None:
            settings.insert(0, ("Roughness", roughness, "MP_ROUGHNESS", -260, -40))
        if clear_coat is not None:
            settings.append(("ClearCoat", float(clear_coat), "MP_CLEAR_COAT", -260, 320))
        if clear_coat_roughness is not None:
            settings.append(("ClearCoatRoughness", float(clear_coat_roughness), "MP_CLEAR_COAT_ROUGHNESS", -260, 440))
        for parameter_name, value, property_name, x, y in settings:
            expr = create_material_constant(material, unreal.MaterialExpressionScalarParameter, value, x, y)
            if expr is not None:
                set_property(expr, "parameter_name", parameter_name)
            connect_material_property(expr, "", property_name)
    elif hasattr(unreal, "MaterialExpressionConstant"):
        settings = [
            (metallic, "MP_METALLIC", -260, 80),
            (specular, "MP_SPECULAR", -260, 200),
        ]
        if roughness_sample is None:
            settings.insert(0, (roughness, "MP_ROUGHNESS", -260, -40))
        if clear_coat is not None:
            settings.append((float(clear_coat), "MP_CLEAR_COAT", -260, 320))
        if clear_coat_roughness is not None:
            settings.append((float(clear_coat_roughness), "MP_CLEAR_COAT_ROUGHNESS", -260, 440))
        for value, property_name, x, y in settings:
            expr = create_material_constant(material, unreal.MaterialExpressionConstant, value, x, y)
            connect_material_property(expr, "", property_name)

    opacity = spec.get("opacity")
    if opacity is not None:
        set_property(material, "blend_mode", getattr(unreal.BlendMode, "BLEND_TRANSLUCENT", None))
        if hasattr(unreal, "MaterialExpressionConstant"):
            opacity_expr = create_material_constant(material, unreal.MaterialExpressionConstant, float(opacity), -260, 320)
            connect_material_property(opacity_expr, "", "MP_OPACITY")

    if hasattr(unreal, "MaterialEditingLibrary"):
        try:
            unreal.MaterialEditingLibrary.layout_material_expressions(material)
            unreal.MaterialEditingLibrary.recompile_material(material)
        except Exception:
            pass


def create_or_update_materials(texture_assets: dict[str, dict[str, str]], material_texture_bindings: dict[str, str]) -> dict[str, str]:
    manifest = load_material_manifest()
    if not manifest:
        log("Material realism manifest missing or empty; using imported OBJ materials")
        return {}

    ensure_content_dirs()
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    created: dict[str, str] = {}
    for material_name, spec in manifest.items():
        asset_path = material_asset_path(material_name)
        material = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not material:
            try:
                material = asset_tools.create_asset(
                    asset_name_for_material(material_name),
                    MATERIAL_DESTINATION_PATH,
                    unreal.Material,
                    unreal.MaterialFactoryNew(),
                )
            except Exception as exc:
                log(f"Could not create material {material_name}: {exc}")
                continue
        if material:
            texture_set_name = material_texture_bindings.get(material_name, "")
            configure_unreal_material(material, spec, texture_assets.get(texture_set_name))
            try:
                unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
            except Exception:
                pass
            created[material_name] = asset_path
    log(f"Prepared {len(created)} realism material assets")
    return created


def build_material_texture_features(
    material_texture_bindings: dict[str, str],
    texture_assets: dict[str, dict[str, str]],
) -> dict[str, Any]:
    manifest = load_material_manifest()
    features: dict[str, Any] = {}
    for material_name, spec in manifest.items():
        texture_set_name = material_texture_bindings.get(material_name, "")
        texture_set = texture_assets.get(texture_set_name, {})
        features[material_name] = {
            "texture_set": texture_set_name,
            "basecolor": bool(texture_set.get("basecolor")),
            "normal": bool(texture_set.get("normal")),
            "roughness": bool(texture_set.get("roughness")),
            "opacity": spec.get("opacity"),
            "clear_coat": spec.get("clear_coat"),
            "clear_coat_roughness": spec.get("clear_coat_roughness"),
            "shading_model": "MSM_CLEAR_COAT" if spec.get("clear_coat") else "MSM_DEFAULT_LIT",
            "two_sided": True,
            "tangent_space_normal": True,
        }
    return features


def slot_name(slot: Any) -> str:
    try:
        return str(slot.material_slot_name)
    except Exception:
        try:
            return str(slot.get_editor_property("material_slot_name"))
        except Exception:
            return ""


def apply_realism_materials(asset_path: str, material_assets: dict[str, str]) -> None:
    if not material_assets:
        return
    mesh = unreal.EditorAssetLibrary.load_asset(asset_path)
    if not mesh:
        return
    slots = get_property(mesh, "static_materials") or []
    changed = False
    for index, slot in enumerate(slots):
        name = slot_name(slot)
        realism_path = material_assets.get(name)
        if not realism_path:
            continue
        material = unreal.EditorAssetLibrary.load_asset(realism_path)
        if not material:
            continue
        try:
            mesh.set_material(index, material)
            changed = True
        except Exception as exc:
            log(f"Could not assign {realism_path} to {asset_path} slot {name}: {exc}")
    if changed:
        try:
            unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
        except Exception:
            pass


def actor_folder(actor: Any) -> str:
    try:
        return str(actor.get_folder_path())
    except Exception:
        return ""


def clear_generated_level_actors() -> None:
    """Remove actors spawned by previous runs so the importer is repeatable."""
    try:
        actors = unreal.EditorLevelLibrary.get_all_level_actors()
    except Exception as exc:
        log(f"Could not inspect existing level actors: {exc}")
        return

    removed = 0
    for actor in actors:
        label = actor.get_actor_label()
        folder = actor_folder(actor)
        generated_folder = folder == "CapitolMap" or folder.startswith("CapitolMap/")
        generated_label = label.startswith("CapitolMap_") or (label.startswith("Label_") and generated_folder)
        if generated_folder or generated_label:
            try:
                unreal.EditorLevelLibrary.destroy_actor(actor)
                removed += 1
            except Exception as exc:
                log(f"Could not remove generated actor {label}: {exc}")
    if removed:
        log(f"Removed {removed} previously generated CapitolMap actors")


def configure_static_mesh_component(component: Any) -> None:
    if not component:
        return
    if hasattr(unreal, "CollisionEnabled"):
        set_property(component, "collision_enabled", unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    set_property(component, "can_ever_affect_navigation", True)
    if hasattr(unreal, "ComponentMobility"):
        set_property(component, "mobility", unreal.ComponentMobility.STATIC)


def spawn_mesh_actors(asset_paths: list[str], material_assets: dict[str, str]) -> None:
    for asset_path in asset_paths:
        configure_static_mesh(asset_path)
        apply_realism_materials(asset_path, material_assets)
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not asset:
            continue
        actor = unreal.EditorLevelLibrary.spawn_actor_from_object(asset, unreal.Vector(0, 0, 0))
        if actor:
            mesh_key = f"{Path(asset_path).name}.obj"
            visibility = MESH_INSPECTION_VISIBILITY.get(mesh_key, {"folder": "CapitolMap/Meshes", "tags": ["CapitolMap_Mesh"]})
            actor.set_actor_label(f"CapitolMap_{Path(asset_path).name}")
            actor.set_folder_path(visibility["folder"])
            set_actor_tags(actor, visibility["tags"])
            configure_static_mesh_component(actor.get_component_by_class(unreal.StaticMeshComponent))


def spawn_scene_setup() -> None:
    """Add lighting, environment, and first-person spawn helpers."""
    spawn_environment_setup()

    try:
        player_start = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.PlayerStart,
            unreal.Vector(*PLAYER_START_LOCATION_CM),
            unreal.Rotator(0, 0, 0),
        )
        if player_start:
            player_start.set_actor_label(PLAYER_START_LABEL)
            player_start.set_folder_path("CapitolMap/SceneSetup")
    except Exception as exc:
        log(f"PlayerStart setup skipped: {exc}")

    spawn_playtest_pawn()
    spawn_camera_viewpoints()
    spawn_first_person_collision_proxies()
    spawn_navigation_bounds()
    spawn_metadata_lights()


def spawn_environment_setup() -> None:
    """Place guarded atmosphere, lighting, reflection, and exposure helpers."""
    try:
        directional = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.DirectionalLight,
            unreal.Vector(*ENVIRONMENT_IMPORT_SETUP["directional_light_location_cm"]),
            unreal.Rotator(*ENVIRONMENT_IMPORT_SETUP["directional_light_rotation_deg"]),
        )
        if directional:
            directional.set_actor_label(ENVIRONMENT_IMPORT_SETUP["directional_light_label"])
            directional.set_folder_path("CapitolMap/Environment")
            component = directional.get_component_by_class(unreal.DirectionalLightComponent)
            if component:
                set_property(component, "intensity", ENVIRONMENT_IMPORT_SETUP["directional_light_intensity"])
                set_property(component, "cast_shadows", True)
    except Exception as exc:
        log(f"Lighting setup skipped: {exc}")

    try:
        sky = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.SkyLight,
            unreal.Vector(*ENVIRONMENT_IMPORT_SETUP["sky_light_location_cm"]),
        )
        if sky:
            sky.set_actor_label(ENVIRONMENT_IMPORT_SETUP["sky_light_label"])
            sky.set_folder_path("CapitolMap/Environment")
            component = sky.get_component_by_class(unreal.SkyLightComponent)
            if component:
                set_property(component, "intensity", ENVIRONMENT_IMPORT_SETUP["sky_light_intensity"])
                set_property(component, "real_time_capture", True)
    except Exception as exc:
        log(f"Sky light setup skipped: {exc}")

    spawn_optional_environment_actor(
        ENVIRONMENT_IMPORT_SETUP["sky_atmosphere_actor_class"],
        ENVIRONMENT_IMPORT_SETUP["sky_atmosphere_label"],
        unreal.Vector(0.0, 0.0, 0.0),
        unreal.Rotator(0.0, 0.0, 0.0),
    )

    try:
        fog = spawn_optional_environment_actor(
            ENVIRONMENT_IMPORT_SETUP["exponential_height_fog_actor_class"],
            ENVIRONMENT_IMPORT_SETUP["exponential_height_fog_label"],
            unreal.Vector(0.0, 0.0, 0.0),
            unreal.Rotator(0.0, 0.0, 0.0),
        )
        if fog and hasattr(unreal, "ExponentialHeightFogComponent"):
            component = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
            if component:
                set_property(component, "fog_density", 0.006)
                set_property(component, "fog_height_falloff", 0.18)
    except Exception as exc:
        log(f"Atmospheric fog setup skipped: {exc}")

    try:
        capture = spawn_optional_environment_actor(
            ENVIRONMENT_IMPORT_SETUP["reflection_capture_actor_class"],
            ENVIRONMENT_IMPORT_SETUP["reflection_capture_label"],
            unreal.Vector(0.0, 0.0, 2400.0),
            unreal.Rotator(0.0, 0.0, 0.0),
        )
        if capture and hasattr(unreal, "SphereReflectionCaptureComponent"):
            component = capture.get_component_by_class(unreal.SphereReflectionCaptureComponent)
            if component:
                set_property(component, "influence_radius", ENVIRONMENT_IMPORT_SETUP["reflection_capture_radius_cm"])
    except Exception as exc:
        log(f"Reflection capture setup skipped: {exc}")

    try:
        post = spawn_optional_environment_actor(
            ENVIRONMENT_IMPORT_SETUP["post_process_actor_class"],
            ENVIRONMENT_IMPORT_SETUP["post_process_label"],
            unreal.Vector(*ENVIRONMENT_IMPORT_SETUP["post_process_location_cm"]),
            unreal.Rotator(0.0, 0.0, 0.0),
        )
        if post:
            post.set_actor_scale3d(unreal.Vector(*ENVIRONMENT_IMPORT_SETUP["post_process_scale_cm"]))
            set_property(post, "b_unbound", True)
            component = post.get_component_by_class(unreal.PostProcessComponent) if hasattr(unreal, "PostProcessComponent") else None
            if component:
                set_property(component, "b_unbound", True)
                settings = get_property(component, "settings")
                if settings:
                    set_property(settings, "auto_exposure_method", 1)
                    set_property(settings, "auto_exposure_min_brightness", ENVIRONMENT_IMPORT_SETUP["post_process_exposure_min"])
                    set_property(settings, "auto_exposure_max_brightness", ENVIRONMENT_IMPORT_SETUP["post_process_exposure_max"])
    except Exception as exc:
        log(f"Post process setup skipped: {exc}")


def spawn_optional_environment_actor(class_name: str, label: str, location: unreal.Vector, rotation: unreal.Rotator) -> Any | None:
    actor_class = getattr(unreal, class_name, None)
    if actor_class is None:
        log(f"Environment actor skipped: {class_name} unavailable")
        return None
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(actor_class, location, rotation)
    if actor:
        actor.set_actor_label(label)
        actor.set_folder_path("CapitolMap/Environment")
    return actor


def spawn_playtest_pawn() -> None:
    """Place a default pawn for immediate PIE inspection when available."""
    if not hasattr(unreal, "DefaultPawn"):
        log("Playtest pawn skipped: DefaultPawn unavailable")
        return
    try:
        pawn = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.DefaultPawn,
            unreal.Vector(*PLAYTEST_PAWN_LOCATION_CM),
            unreal.Rotator(*PLAYTEST_PAWN_ROTATION_DEG),
        )
        if not pawn:
            return
        pawn.set_actor_label(PLAYTEST_PAWN_LABEL)
        pawn.set_folder_path("CapitolMap/SceneSetup")
        if hasattr(unreal, "AutoReceiveInput") and hasattr(unreal.AutoReceiveInput, "PLAYER0"):
            set_property(pawn, "auto_possess_player", unreal.AutoReceiveInput.PLAYER0)
            set_property(pawn, "auto_receive_input", unreal.AutoReceiveInput.PLAYER0)
    except Exception as exc:
        log(f"Playtest pawn setup skipped: {exc}")


def to_unreal_vector(location_m: list[float]) -> unreal.Vector:
    x, y, z = location_m
    return unreal.Vector(x * 100.0, y * 100.0, z * 100.0)


def look_at_rotation(location_m: list[float], target_m: list[float]) -> unreal.Rotator:
    dx = target_m[0] - location_m[0]
    dy = target_m[1] - location_m[1]
    dz = target_m[2] - location_m[2]
    horizontal = max(math.hypot(dx, dy), 0.001)
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = math.degrees(math.atan2(dz, horizontal))
    return unreal.Rotator(pitch, yaw, 0.0)


def spawn_camera_viewpoints() -> None:
    try:
        viewpoints = load_metadata().get("viewpoints") or DEFAULT_VIEWPOINTS
    except Exception as exc:
        log(f"Using fallback camera viewpoints: {exc}")
        viewpoints = DEFAULT_VIEWPOINTS

    for viewpoint in viewpoints:
        try:
            camera = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.CameraActor,
                to_unreal_vector(viewpoint["location_m"]),
                look_at_rotation(viewpoint["location_m"], viewpoint["target_m"]),
            )
            if not camera:
                continue
            camera.set_actor_label(viewpoint["label"])
            camera.set_folder_path("CapitolMap/Viewpoints")
            component = camera.get_component_by_class(unreal.CameraComponent)
            if component:
                set_property(component, "field_of_view", viewpoint["fov"])
        except Exception as exc:
            log(f"Camera viewpoint skipped ({viewpoint['label']}): {exc}")


def spawn_navigation_bounds() -> None:
    """Add a broad nav bounds volume for first-person/pawn testing."""
    if not hasattr(unreal, "NavMeshBoundsVolume"):
        log("Navigation bounds skipped: NavMeshBoundsVolume unavailable")
        return
    try:
        volume = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.NavMeshBoundsVolume,
            unreal.Vector(*NAV_MESH_BOUNDS_LOCATION_CM),
            unreal.Rotator(0.0, 0.0, 0.0),
        )
        if not volume:
            return
        volume.set_actor_label(NAV_MESH_BOUNDS_LABEL)
        volume.set_folder_path("CapitolMap/SceneSetup")
        volume.set_actor_scale3d(unreal.Vector(*NAV_MESH_BOUNDS_SCALE))
    except Exception as exc:
        log(f"Navigation bounds setup skipped: {exc}")


def spawn_first_person_collision_proxies() -> None:
    """Add simple walkable blocking volumes for first-person playtest stability."""
    if not hasattr(unreal, "BlockingVolume"):
        log("First-person collision proxies skipped: BlockingVolume unavailable")
        return
    for proxy in FIRST_PERSON_COLLISION_PROXIES:
        try:
            volume = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.BlockingVolume,
                unreal.Vector(*proxy["location_cm"]),
                unreal.Rotator(0.0, 0.0, 0.0),
            )
            if not volume:
                continue
            volume.set_actor_label(proxy["label"])
            volume.set_folder_path(COLLISION_PROXY_FOLDER)
            volume.set_actor_scale3d(unreal.Vector(*proxy["scale"]))
            set_actor_tags(volume, ["CapitolMap_Collision", FIRST_PERSON_COLLISION_PROXY_TAG])
            try:
                volume.set_actor_hidden_in_game(True)
            except Exception:
                set_property(volume, "hidden", True)
            component = volume.get_component_by_class(unreal.BrushComponent) if hasattr(unreal, "BrushComponent") else None
            configure_static_mesh_component(component)
        except Exception as exc:
            log(f"First-person collision proxy skipped ({proxy.get('label', '<unknown>')}): {exc}")


def spawn_metadata_lights() -> None:
    try:
        data = load_metadata()
        fixtures = list(data.get("interior", {}).get("light_fixtures", []))
        exterior_streetlights = [
            prop
            for prop in data.get("exterior", {}).get("streetscape_props", [])
            if prop.get("kind") == "streetlight" and prop.get("light_m")
        ][:120]
        grounds_walk_lamps = [
            detail
            for detail in data.get("exterior", {}).get("grounds_details", [])
            if detail.get("kind") == "public_walk_lamp" and detail.get("light_m")
        ]
        landmark_facade_lights = [
            detail
            for detail in data.get("landmark", {}).get("facade_details", [])
            if detail.get("kind") in {"public_entry_lamp", "facade_uplight"} and detail.get("light_m")
        ]
    except Exception as exc:
        log(f"Lighting metadata skipped: {exc}")
        return
    for prop in exterior_streetlights:
        fixtures.append(
            {
                "name": prop.get("name", "streetlight"),
                "type": "exterior_streetlight",
                "location": "Exterior public streetscape",
                "center_m": prop.get("light_m"),
                "intensity": prop.get("intensity", 420.0),
                "attenuation_radius_m": prop.get("attenuation_radius_m", 9.0),
                "color": prop.get("color", [1.0, 0.82, 0.55]),
            }
        )
    for detail in grounds_walk_lamps:
        fixtures.append(
            {
                "name": detail.get("name", "grounds_walk_lamp"),
                "type": "public_grounds_walk_lamp",
                "location": "Exterior public grounds",
                "center_m": detail.get("light_m"),
                "intensity": detail.get("intensity", 360.0),
                "attenuation_radius_m": detail.get("attenuation_radius_m", 8.0),
                "color": detail.get("color", [1.0, 0.82, 0.55]),
            }
        )
    for detail in landmark_facade_lights:
        fixtures.append(
            {
                "name": detail.get("name", "landmark_facade_light"),
                "type": detail.get("kind", "landmark_facade_light"),
                "location": "Capitol public exterior facade",
                "center_m": detail.get("light_m"),
                "intensity": detail.get("intensity", 430.0),
                "attenuation_radius_m": detail.get("attenuation_radius_m", 8.0),
                "color": detail.get("color", [1.0, 0.80, 0.55]),
            }
        )
    for fixture in fixtures:
        try:
            light = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.PointLight,
                to_unreal_vector(fixture["center_m"]),
            )
            if not light:
                continue
            light.set_actor_label(f"CapitolMap_Light_{fixture['name']}")
            light.set_folder_path("CapitolMap/Lighting")
            component = light.get_component_by_class(unreal.PointLightComponent)
            if component:
                set_property(component, "intensity", float(fixture.get("intensity", 650.0)))
                set_property(component, "attenuation_radius", float(fixture.get("attenuation_radius_m", 7.0)) * 100.0)
                color = fixture.get("color", [1.0, 0.82, 0.52])
                set_property(component, "light_color", unreal.Color(int(color[0] * 255), int(color[1] * 255), int(color[2] * 255), 255))
        except Exception as exc:
            log(f"Light fixture skipped ({fixture.get('name', '<unknown>')}): {exc}")
    if exterior_streetlights or grounds_walk_lamps or landmark_facade_lights:
        log(
            "Spawned metadata lights including "
            f"{len(exterior_streetlights)} capped exterior streetlights and "
            f"{len(grounds_walk_lamps)} public grounds walk lamps and "
            f"{len(landmark_facade_lights)} Capitol facade lights"
        )


def label_color(category: str) -> unreal.Color:
    rgba = LABEL_COLORS.get(category, LABEL_COLORS.get("landmark", (245, 245, 235, 255)))
    return unreal.Color(*rgba)


def label_folder(category: str) -> str:
    if category in {"street_name", "building"}:
        return "CapitolMap/Labels/Exterior"
    if category in {"landmark"}:
        return "CapitolMap/Labels/Landmark"
    if category in {"gameplay_item"}:
        return "CapitolMap/Labels/Gameplay"
    return "CapitolMap/Labels/Interior"


def spawn_text_label(text: str, location_m: list[float], category: str) -> None:
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.TextRenderActor,
        to_unreal_vector(location_m),
        unreal.Rotator(0.0, 0.0, 0.0),
    )
    if not actor:
        return
    safe_label = "".join(ch if ch.isalnum() else "_" for ch in text[:54]).strip("_")
    actor.set_actor_label(f"Label_{safe_label}")
    actor.set_folder_path(label_folder(category))

    component = actor.get_component_by_class(unreal.TextRenderComponent)
    if not component:
        return
    component.set_text(text)
    component.set_world_size(90.0 if category == "major_public_space" else 65.0)
    if hasattr(unreal, "HorizontalTextAligment"):
        component.set_horizontal_alignment(unreal.HorizontalTextAligment.EHTA_CENTER)
    if hasattr(unreal, "VerticalTextAligment"):
        component.set_vertical_alignment(unreal.VerticalTextAligment.EVRTA_TEXT_CENTER)
    component.set_text_render_color(label_color(category))


def spawn_metadata_labels() -> None:
    data = load_metadata()

    # Public interior labels are intentionally sparse and semantic.
    for label in data["interior"]["labels"]:
        spawn_text_label(label["text"], label["location_m"], label["category"])

    for label in data.get("landmark", {}).get("labels", []):
        spawn_text_label(label["text"], label["location_m"], label["category"])

    for label in data.get("gameplay", {}).get("labels", []):
        spawn_text_label(label["text"], label["location_m"], label["category"])

    for label in data.get("exterior", {}).get("street_labels", []):
        location = label["location_m"]
        if abs(location[0]) < 450 and abs(location[1]) < 450:
            spawn_text_label(label["text"], location, "street_name")

    # Add exterior building labels for named nearby buildings only; anonymous
    # building footprints remain unlabeled to avoid clutter.
    for building in data["exterior"]["buildings"]:
        name = building.get("name", "")
        if not name or name.startswith("osm_way_"):
            continue
        center = building["center_m"]
        location = [center[0], center[1], max(center[2] * 2.0 + 3.0, 6.0)]
        spawn_text_label(name, location, "building")


def save_generated_level() -> None:
    """Save the generated level and imported assets when possible."""
    try:
        if hasattr(unreal.EditorLevelLibrary, "save_current_level"):
            unreal.EditorLevelLibrary.save_current_level()
            log("Saved current level")
        elif hasattr(unreal, "EditorLoadingAndSavingUtils"):
            unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
            log("Saved dirty packages")
        else:
            log("Save API unavailable; save the generated level manually")
    except Exception as exc:
        log(f"Could not save generated level automatically: {exc}")


def write_unreal_import_report(
    imported: list[str],
    material_assets: dict[str, str],
    texture_assets: dict[str, dict[str, str]],
    material_texture_bindings: dict[str, str],
) -> None:
    try:
        data = load_metadata()
        report = {
            "ok": True,
            "map_asset_path": MAP_ASSET_PATH,
            "map_destination": MAP_DESTINATION_PATH,
            "import_destination": DESTINATION_PATH,
            "material_destination": MATERIAL_DESTINATION_PATH,
            "texture_destination": TEXTURE_DESTINATION_PATH,
            "imported_assets": imported,
            "material_assets": material_assets,
            "texture_assets": texture_assets,
            "material_texture_bindings": material_texture_bindings,
            "material_texture_features": build_material_texture_features(material_texture_bindings, texture_assets),
            "material_graph_features": MATERIAL_GRAPH_FEATURES,
            "texture_kind_settings": TEXTURE_KIND_SETTINGS,
            "mesh_count": len(imported),
            "material_count": len(material_assets),
            "texture_set_count": len(texture_assets),
            "texture_asset_count": sum(len(value) for value in texture_assets.values()),
            "environment_setup": ENVIRONMENT_IMPORT_SETUP,
            "first_person_setup": FIRST_PERSON_IMPORT_SETUP,
            "collision_proxy_setup": FIRST_PERSON_COLLISION_PROXIES,
            "metadata_counts": {
                "buildings": len(data.get("exterior", {}).get("buildings", [])),
                "roads": len(data.get("exterior", {}).get("roads", [])),
                "bike_lanes": len(data.get("exterior", {}).get("bike_lanes", [])),
                "street_markers": len(data.get("exterior", {}).get("street_markers", [])),
                "grounds_details": len(data.get("exterior", {}).get("grounds_details", [])),
                "grounds_walk_lamps": len(
                    [
                        detail
                        for detail in data.get("exterior", {}).get("grounds_details", [])
                        if detail.get("kind") == "public_walk_lamp"
                    ]
                ),
                "landmark_facade_lights": len(
                    [
                        detail
                        for detail in data.get("landmark", {}).get("facade_details", [])
                        if detail.get("kind") in {"public_entry_lamp", "facade_uplight"} and detail.get("light_m")
                    ]
                ),
                "rooms": len(data.get("interior", {}).get("rooms", [])),
                "seating": len(data.get("interior", {}).get("seating", [])),
                "office_cells": len(data.get("interior", {}).get("office_cells", [])),
                "office_details": len(data.get("interior", {}).get("office_details", [])),
                "circulation_details": len(data.get("interior", {}).get("circulation_details", [])),
                "signage_details": len(data.get("interior", {}).get("signage_details", [])),
                "door_details": len(data.get("interior", {}).get("door_details", [])),
                "furnishing_details": len(data.get("interior", {}).get("furnishing_details", [])),
                "wall_finish_details": len(data.get("interior", {}).get("wall_finish_details", [])),
                "rotunda_details": len(data.get("interior", {}).get("rotunda_details", [])),
                "ceiling_details": len(data.get("interior", {}).get("ceiling_details", [])),
                "floor_details": len(data.get("interior", {}).get("floor_details", [])),
                "joint_session": len(data.get("interior", {}).get("joint_session", [])),
                "gameplay_items": len(data.get("gameplay", {}).get("items", [])),
                "viewpoints": len(data.get("viewpoints", [])),
            },
            "inspection_visibility": INTERIOR_TOPDOWN_INSPECTION,
            "interior_cutaway_inspection": INTERIOR_CUTAWAY_INSPECTION,
            "mesh_inspection_visibility": MESH_INSPECTION_VISIBILITY,
        }
        UNREAL_IMPORT_REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        log(f"Wrote Unreal import report: {UNREAL_IMPORT_REPORT_PATH}")
    except Exception as exc:
        log(f"Could not write Unreal import report: {exc}")


def main() -> None:
    if not METADATA_PATH.exists():
        raise RuntimeError(f"Missing metadata: {METADATA_PATH}")

    log(f"Package root: {PACKAGE_ROOT}")
    prepare_level()
    clear_generated_level_actors()
    imported = import_meshes()
    texture_assets, material_texture_bindings = import_texture_assets()
    material_assets = create_or_update_materials(texture_assets, material_texture_bindings)
    spawn_mesh_actors(imported, material_assets)
    spawn_scene_setup()
    spawn_metadata_labels()
    save_generated_level()
    write_unreal_import_report(imported, material_assets, texture_assets, material_texture_bindings)
    log(f"Done. Check {MAP_ASSET_PATH} and the CapitolMap folders in the World Outliner.")


if __name__ == "__main__":
    main()
