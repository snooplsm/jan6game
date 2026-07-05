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
from collections import Counter
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
VIEWER_PATH = ROOT / "viewer.html"
MIN_TEXTURE_SIZE_PX = int(os.environ.get("CAPITOL_MIN_TEXTURE_SIZE", "4096"))
CAPITOL_PUBLIC_HEIGHT_TARGET_M = 87.78
LANDMARK_HEIGHT_TOLERANCE_M = 0.35
LANDMARK_MESH_REL = "generated/meshes/capitol_landmark_visual_details.obj"

REQUIRED_PHOTOREAL_TEXTURE_FEATURES = {
    "tileable_4k_basecolor_normal_roughness_ao",
    "material_micro_pores_and_pinholes",
    "stone_mineral_flecks_and_joint_grime",
    "asphalt_aggregate_tar_and_crack_breakup",
    "concrete_pitting_trowel_and_edge_wear",
    "fabric_canvas_fiber_weave_breakup",
    "wood_open_grain_knots_and_plank_seams",
    "metal_brushing_scratches_and_tarnish_variation",
    "height_derived_normal_maps",
    "height_and_cavity_driven_roughness_ao",
}

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
    "spawn_environment_setup",
    "spawn_optional_environment_actor",
    "apply_photoreal_post_process_settings",
    "spawn_playtest_pawn",
    "spawn_player_starts",
    "spawn_camera_viewpoints",
    "spawn_first_person_collision_proxies",
    "spawn_navigation_bounds",
    "build_public_accent_light_specs",
    "spawn_metadata_lights",
    "spawn_metadata_labels",
    "write_unreal_import_report",
    "is_vector3",
    "to_unreal_color",
    "set_enum_property",
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
    "spawn_environment_setup",
    "spawn_optional_environment_actor",
    "apply_photoreal_post_process_settings",
    "spawn_playtest_pawn",
    "spawn_player_starts",
    "spawn_camera_viewpoints",
    "spawn_first_person_collision_proxies",
    "spawn_navigation_bounds",
    "build_public_accent_light_specs",
    "spawn_metadata_lights",
    "spawn_metadata_labels",
    "to_unreal_color",
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
    "material_texture_bindings",
    "material_texture_features",
    "material_graph_features",
    "texture_kind_settings",
    "static_mesh_realism_build_settings",
    "use_full_precision_uvs",
    "use_full_precision_u_vs",
    "use_high_precision_tangent_basis",
    "recompute_normals",
    "recompute_tangents",
    "compute_weighted_normals",
    "remove_degenerates",
    "generate_lightmap_uvs",
    "generate_lightmap_u_vs",
    "min_lightmap_resolution",
    "light_map_resolution",
    "lightmap_resolution",
    "normal_import_method",
    "normal_generation_method",
    "MikkTSpace",
    "srgb",
    "compression_settings",
    "texture_group",
    "mip_gen_settings",
    "filter",
    "sampler_type",
    "mesh_count",
    "material_count",
    "texture_set_count",
    "texture_asset_count",
    "basecolor_property",
    "normal_property",
    "roughness_property",
    "ambient_occlusion_property",
    "metallic_property",
    "specular_property",
    "opacity_property",
    "uses_texture_samples",
    "uses_ambient_occlusion_maps",
    "uses_tangent_space_normals",
    "two_sided_by_default",
    "adds_editor_comment",
    "environment_setup",
    "photoreal_preview_profile",
    "profile_name",
    "renderer_features",
    "lumen_dynamic_global_illumination",
    "lumen_reflections",
    "nanite_static_meshes",
    "virtual_shadow_maps",
    "screen_space_ambient_occlusion",
    "contact_shadows",
    "reflection_capture",
    "filmic_post_process",
    "directional_light_use_temperature",
    "directional_light_temperature",
    "directional_light_source_angle",
    "directional_light_contact_shadow_length",
    "sky_light_indirect_lighting_intensity",
    "reflection_capture_brightness",
    "post_process_settings",
    "bloom_intensity",
    "bloom_threshold",
    "ambient_occlusion_intensity",
    "ambient_occlusion_radius",
    "ambient_occlusion_power",
    "vignette_intensity",
    "film_slope",
    "film_toe",
    "film_shoulder",
    "film_black_clip",
    "film_white_clip",
    "motion_blur_amount",
    "public_accent_light_setup",
    "public_accent_light_kind_settings",
    "scene_setup_stats",
    "metadata_light_fixture_count",
    "exterior_streetlight_actor_count",
    "grounds_walk_lamp_actor_count",
    "landmark_facade_light_actor_count",
    "public_accent_light_candidate_count",
    "public_accent_light_actor_count",
    "public_accent_light_kinds",
    "spawned_light_type_counts",
    "public_accent_light_actor_class",
    "public_accent_light_folder",
    "public_accent_light_tag",
    "public_accent_light_limit",
    "public_accent_light_cast_shadows",
    "public_accent_light_metadata_sources",
    "priority",
    "max_count",
    "source_radius_cm",
    "soft_source_radius_cm",
    "source_length_cm",
    "z_offset_m",
    "directional_light_actor_class",
    "directional_light_label",
    "directional_light_location_cm",
    "directional_light_rotation_deg",
    "directional_light_intensity",
    "sky_light_actor_class",
    "sky_light_label",
    "sky_light_location_cm",
    "sky_light_intensity",
    "sky_atmosphere_actor_class",
    "sky_atmosphere_label",
    "exponential_height_fog_actor_class",
    "exponential_height_fog_label",
    "reflection_capture_actor_class",
    "reflection_capture_label",
    "reflection_capture_radius_cm",
    "post_process_actor_class",
    "post_process_label",
    "post_process_location_cm",
    "post_process_scale_cm",
    "post_process_exposure_min",
    "post_process_exposure_max",
    "first_person_setup",
    "collision_proxy_setup",
    "static_mesh_lod_group",
    "auto_generate_collision",
    "collision_trace",
    "actor_collision",
    "can_affect_navigation",
    "nanite_enabled",
    "player_start_actor_class",
    "player_start_label",
    "player_start_location_cm",
    "player_start_points",
    "public_interior_walk_start_label",
    "public_interior_walk_start_location_cm",
    "playtest_pawn_actor_class",
    "playtest_pawn_label",
    "playtest_pawn_location_cm",
    "playtest_pawn_rotation_deg",
    "playtest_pawn_auto_possess",
    "nav_mesh_bounds_actor_class",
    "nav_mesh_bounds_label",
    "nav_mesh_bounds_location_cm",
    "nav_mesh_bounds_scale_cm",
    "collision_proxy_actor_class",
    "collision_proxy_folder",
    "collision_proxy_tag",
    "collision_proxy_count",
    "collision_proxy_coverage",
    "collision_proxy_groups",
    "public_exterior_surface_proxy_count",
    "public_interior_surface_proxy_count",
    "public_exterior_surface_total",
    "public_interior_surface_total",
    "group",
    "rotation_deg",
    "public_exterior_road_surface",
    "public_exterior_sidewalk_surface",
    "public_bike_lane_surface",
    "public_exterior_walk_surface",
    "public_interior_surface",
    "label",
    "location_cm",
    "scale",
    "purpose",
    "metadata_counts",
    "inspection_visibility",
    "interior_cutaway_inspection",
    "inspection_workflows",
    "inspection_workflow_count",
    "inspection_workflow_camera_labels",
    "mesh_inspection_visibility",
    "browser_route",
    "camera_label",
    "hide_tag",
    "visible_tag",
    "visible_mesh",
    "label_filter",
    "public_accuracy",
    "person_specific",
    "buildings",
    "roads",
    "bike_lanes",
    "street_markers",
    "grounds_details",
    "grounds_walk_lamps",
    "landmark_facade_lights",
    "rooms",
    "seating",
    "office_cells",
    "office_details",
    "circulation_details",
    "signage_details",
    "door_details",
    "furnishing_details",
    "public_accent_light_candidates",
    "public_accent_lights",
    "wall_finish_details",
    "rotunda_details",
    "ceiling_details",
    "floor_details",
    "surface_aging_details",
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
    "signage_detail",
    "door_detail",
    "furnishing_detail",
    "joint_session",
    "public_art",
    "lighting",
    "wall_treatment",
    "wall_finish_detail",
    "surface_aging_detail",
    "landmark",
    "street_name",
    "building",
    "gameplay_item",
}

REQUIRED_UNREAL_OUTLINER_FOLDERS = {
    "CapitolMap/Meshes",
    "CapitolMap/Meshes/InteriorTopDownVisible",
    "CapitolMap/Meshes/HideForInteriorTopDown",
    "CapitolMap/SceneSetup",
    "CapitolMap/Collision",
    "CapitolMap/Environment",
    "CapitolMap/Viewpoints",
    "CapitolMap/Lighting",
    "CapitolMap/Lighting/PublicAccent",
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
    "CapitolMap_PlayerStart_PublicInteriorWalk",
    "CapitolMap_PlayerStart",
    "CapitolMap_FirstPersonInspection",
    "CapitolMap_Playtest_DefaultPawn",
    "auto_possess_player",
    "auto_receive_input",
    "CapitolMap_NavMeshBounds_CentralCampus",
    "BlockingVolume",
    "CapitolMap_Collision",
    "CapitolMap_FirstPersonCollisionProxy",
    "CapitolMap_Collision_WestFrontPlaza",
    "CapitolMap_Collision_EastFrontPlaza",
    "CapitolMap_Collision_WestAxialPublicWalk",
    "CapitolMap_Collision_EastAxialPublicWalk",
    "CapitolMap_Collision_NorthPublicGroundsWalk",
    "CapitolMap_Collision_SouthPublicGroundsWalk",
    "CapitolMap_Collision_RotundaPublicFloor",
    "CapitolMap_Collision_PublicInteriorFootprint",
    "CapitolMap_Collision_NationalStatuaryHallPublicFloor",
    "CapitolMap_Collision_OldSenatePublicFloor",
    "CapitolMap_Collision_HouseGalleryPublicFloor",
    "CapitolMap_Collision_SenateGalleryPublicFloor",
    "CapitolMap_Collision_PublicEastWestConnector",
    "CapitolMap_Collision_HouseChamberPublicFloor",
    "CapitolMap_Collision_SenateChamberPublicFloor",
    "CapitolMap_Collision_WestApproachRoadSurface",
    "CapitolMap_Collision_EastApproachRoadSurface",
    "CapitolMap_Collision_NorthApproachRoadSurface",
    "CapitolMap_Collision_SouthApproachRoadSurface",
    "CapitolMap_Collision_WestApproachNorthSidewalk",
    "CapitolMap_Collision_WestApproachSouthSidewalk",
    "CapitolMap_Collision_EastApproachNorthSidewalk",
    "CapitolMap_Collision_EastApproachSouthSidewalk",
    "CapitolMap_Collision_WestBikeLaneNorthSurface",
    "CapitolMap_Collision_WestBikeLaneSouthSurface",
    "CapitolMap_Collision_EastBikeLaneSouthSurface",
    "public_exterior_road_surface",
    "public_exterior_sidewalk_surface",
    "public_bike_lane_surface",
    "nanite_settings",
}

MIN_UNREAL_COLLISION_PROXY_SPECS = 40
REQUIRED_UNREAL_COLLISION_PROXY_GROUPS = {
    "public_exterior_road_surface",
    "public_exterior_sidewalk_surface",
    "public_bike_lane_surface",
    "public_exterior_walk_surface",
    "public_interior_surface",
}

REQUIRED_UNREAL_MATERIAL_MARKERS = {
    "MATERIAL_GRAPH_FEATURES",
    "MaterialExpressionTextureSample",
    "MaterialExpressionComment",
    "MP_BASE_COLOR",
    "MP_NORMAL",
    "MP_ROUGHNESS",
    "MP_AMBIENT_OCCLUSION",
    "MP_METALLIC",
    "MP_SPECULAR",
    "MP_OPACITY",
    "MP_CLEAR_COAT",
    "MP_CLEAR_COAT_ROUGHNESS",
    "MaterialShadingModel",
    "MSM_CLEAR_COAT",
    "clear_coat_property",
    "clear_coat_roughness_property",
    "ambient_occlusion_property",
    "supports_clear_coat_shading",
    "uses_ambient_occlusion_maps",
    "two_sided",
    "tangent_space_normal",
    "use_material_attributes",
    "material_texture_bindings",
    "material_texture_features",
    "material_graph_features",
    "build_material_texture_features",
    "CapitolMap generated PBR setup: basecolor, normal, roughness, and ambient-occlusion maps are imported from generated/textures; scalar parameters remain editable.",
}

REQUIRED_UNREAL_ENVIRONMENT_MARKERS = {
    "DirectionalLight",
    "SkyLight",
    "SkyAtmosphere",
    "ExponentialHeightFog",
    "SphereReflectionCapture",
    "PostProcessVolume",
    "PointLight",
    "DirectionalLightComponent",
    "SkyLightComponent",
    "ExponentialHeightFogComponent",
    "SphereReflectionCaptureComponent",
    "PostProcessComponent",
    "PointLightComponent",
    "CapitolMap_Sun_DirectionalLight",
    "CapitolMap_SkyLight",
    "CapitolMap_SkyAtmosphere",
    "CapitolMap_AtmosphericFog",
    "CapitolMap_CampusReflectionCapture",
    "CapitolMap_GlobalPostProcess",
    "CapitolMap_PhotoRealPreview",
    "CapitolMap_PublicAccentLight",
    "CapitolMap/Lighting/PublicAccent",
    "CapitolMap_AccentLight",
    "CapitolMap_AccentKind_",
    "public_accent_light",
    "public_accent_light_metadata_sources",
    "source_radius",
    "soft_source_radius",
    "source_length",
    "cast_shadows",
    "use_temperature",
    "temperature",
    "source_angle",
    "contact_shadow_length",
    "light_color",
    "attenuation_radius",
    "real_time_capture",
    "indirect_lighting_intensity",
    "fog_density",
    "fog_height_falloff",
    "influence_radius",
    "brightness",
    "b_unbound",
    "b_override_",
    "bloom_intensity",
    "bloom_threshold",
    "ambient_occlusion_intensity",
    "ambient_occlusion_radius",
    "ambient_occlusion_power",
    "vignette_intensity",
    "film_slope",
    "film_toe",
    "film_shoulder",
    "film_black_clip",
    "film_white_clip",
    "motion_blur_amount",
    "auto_exposure_min_brightness",
    "auto_exposure_max_brightness",
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
        "r.DefaultFeature.AmbientOcclusion=True",
        "r.DefaultFeature.Bloom=True",
        "r.DefaultFeature.MotionBlur=False",
        "r.DynamicGlobalIlluminationMethod=1",
        "r.GenerateMeshDistanceFields=True",
        "r.ReflectionMethod=1",
        "r.Nanite.ProjectEnabled=True",
        "r.Shadow.Virtual.Enable=1",
        "r.AntiAliasingMethod=4",
        "r.TemporalAA.Upsampling=True",
        "r.Tonemapper.Quality=5",
        "r.SSR.Quality=4",
        "r.SSR.Temporal=True",
        "r.ReflectionCaptureResolution=1024",
        "r.ContactShadows=True",
        "r.AmbientOcclusionLevels=3",
        "r.AmbientOcclusionRadiusScale=1.150000",
        "r.MaxAnisotropy=16",
        "r.Shadow.Virtual.ResolutionLodBiasDirectional=-1",
        "r.Shadow.Virtual.SMRT.RayCountDirectional=8",
        "r.Lumen.Reflections.MaxRoughnessToTrace=0.800000",
        "r.Lumen.ScreenProbeGather.Temporal=1",
        "r.Streaming.PoolSize=8192",
        "r.Streaming.MaxTempMemoryAllowed=512",
        "r.TextureStreaming=True",
        "bAutoCreateNavigationData=True",
        "bSpawnNavDataInNavBoundsLevel=True",
    },
    "Config/DefaultGame.ini": {
        "ProjectName=Capitol Unreal Map",
        "Public-data U.S. Capitol exterior and public-interior schematic map package.",
    },
}

REQUIRED_VIEWER_MARKERS = {
    'id="quickGroundsDetails"',
    'id="quickFacadeDetails"',
    'id="quickRoofDetails"',
    'id="quickOffices"',
    'id="quickSignageDetails"',
    'id="quickDoorDetails"',
    'id="quickFurnishingDetails"',
    'id="quickPublicArt"',
    'id="quickWallFinishDetails"',
    'id="quickFloorDetails"',
    'id="quickSurfaceAgingDetails"',
    'id="quickCeilingDetails"',
    'id="quickWalkMap"',
    'id="quickWalkInterior"',
    'id="quickInteriorOnly"',
    'id="quickInteriorPlan"',
    'id="quickChambersTop"',
    'id="quickHousePlan"',
    'id="quickSenatePlan"',
    'id="quickRoleZones"',
    'id="quickHouseGallery"',
    'id="quickSenateGallery"',
    'id="quickGameplayItems"',
    'id="texturesToggle"',
    'id="photoRealToggle"',
    'href="#grounds-details"',
    'href="#facade-details"',
    'href="#roof-details"',
    'href="#offices"',
    'href="#signage-details"',
    'href="#door-details"',
    'href="#furnishing-details"',
    'href="#public-art"',
    'href="#wall-finish-details"',
    'href="#floor-details"',
    'href="#surface-aging-details"',
    'href="#ceiling-details"',
    'href="#walk-map"',
    'href="#walk"',
    'href="#interior-only"',
    'href="#interior-plan"',
    'href="#chambers-top"',
    'href="#house-plan"',
    'href="#senate-plan"',
    'href="#role-zones"',
    'href="#house-gallery"',
    'href="#senate-gallery"',
    'href="#gameplay-items"',
    'id="presetGroundsDetails"',
    'id="presetFacadeDetails"',
    'id="presetRoofDetails"',
    'id="presetOffices"',
    'id="presetSignageDetails"',
    'id="presetDoorDetails"',
    'id="presetFurnishingDetails"',
    'id="presetPublicArt"',
    'id="presetWallFinishDetails"',
    'id="presetFloorDetails"',
    'id="presetSurfaceAgingDetails"',
    'id="presetCeilingDetails"',
    'id="presetWalkMap"',
    'id="presetWalkInterior"',
    'id="presetInteriorOnly"',
    'id="presetInteriorPlan"',
    'id="presetChambersTop"',
    'id="presetHousePlan"',
    'id="presetSenatePlan"',
    'id="presetRoleZones"',
    'id="presetHouseGallery"',
    'id="presetSenateGallery"',
    'id="presetGameplay"',
    'value="grounds_detail"',
    'value="facade_detail"',
    'value="office_detail"',
    'value="signage_detail"',
    'value="door_detail"',
    'value="furnishing_detail"',
    'value="public_art"',
    'value="wall_finish_detail"',
    'value="floor_detail"',
    'value="surface_aging_detail"',
    'value="ceiling_detail"',
    'value="interior_plan"',
    'value="chamber_role_overlay"',
    'value="gameplay_item"',
    "metadata.exterior?.grounds_details",
    "metadata.landmark?.facade_details",
    "focusRoofDetailsRoute",
    "focusRoofDetails",
    "roof-inspection",
    "capstones, scuppers, parapet gaps, vents, dormers, skylights, and dome trim",
    "metadata.interior?.office_details",
    "metadata.interior?.signage_details",
    "metadata.interior?.door_details",
    "metadata.interior?.furnishing_details",
    "metadata.interior?.public_art",
    "metadata.interior?.wall_finish_details",
    "metadata.interior?.floor_details",
    "metadata.interior?.surface_aging_details",
    "metadata.interior?.ceiling_details",
    "metadata.interior?.chamber_details",
    "metadata.gameplay?.labels",
    "generated/data/material_texture_manifest.json",
    "loadViewerTextures",
    "createViewerTexture",
    "photoRealEnabled",
    "uPhotoRealStrength",
    "worldSpacePatina",
    "filmicContrast",
    "atmosphericDepthFade",
    "Photoreal shader preview",
    "viewerTextureDimension",
    "VIEWER_TEXTURE_MAX_SIZE",
    "VIEWER_SECONDARY_TEXTURE_MAX_SIZE",
    "PBR texture preview",
    "uBaseColorTexture",
    "uNormalTexture",
    "uRoughnessTexture",
    "uAoTexture",
    "uUseNormalTexture",
    "ambient_occlusion",
    "hiddenByDefaultLabelCategories",
    "publicInteriorPlanLabelCategories",
    "focusGroundsDetails",
    "focusGroundsDetailsRoute",
    "focusFacadeDetails",
    "focusFacadeDetailsRoute",
    "focusOffices",
    "focusOfficesRoute",
    "focusSignageDetails",
    "focusSignageDetailsRoute",
    "focusDoorDetails",
    "focusDoorDetailsRoute",
    "focusFurnishingDetails",
    "focusFurnishingDetailsRoute",
    "focusPublicArt",
    "focusPublicArtRoute",
    "focusWallFinishDetails",
    "focusWallFinishDetailsRoute",
    "focusFloorDetails",
    "focusFloorDetailsRoute",
    "focusSurfaceAgingDetails",
    "focusSurfaceAgingDetailsRoute",
    "focusCeilingDetails",
    "focusCeilingDetailsRoute",
    "focusWalkMap",
    "focusWalkMapRoute",
    "focusWalkInterior",
    "focusWalkInteriorRoute",
    "walkHud",
    "resetWalk",
    "walkPresetConfigs",
    "activeWalkConfig",
    "resetWalkCamera",
    "updateWalkHud",
    "minEyeZ",
    "maxEyeZ",
    "cameraMode",
    "requestPointerLock",
    "updateWalkCamera",
    "focusInteriorOnly",
    "focusInteriorOnlyRoute",
    "focusInteriorPlan",
    "focusInteriorPlanRoute",
    "focusChambersTop",
    "focusChambersTopRoute",
    "focusHousePlan",
    "focusHousePlanRoute",
    "focusSenatePlan",
    "focusSenatePlanRoute",
    "focusRoleZones",
    "focusRoleZonesRoute",
    "focusHouseGallery",
    "focusHouseGalleryRoute",
    "focusSenateGallery",
    "focusSenateGalleryRoute",
    "focusGameplayItems",
    "focusGameplayItemsRoute",
    "humanizeId",
    "grounds-details",
    "facade-details",
    "office-details",
    "signage-details",
    "door-details",
    "furnishing-details",
    "public-art",
    "statues-paintings",
    "wall-finish-details",
    "floor-details",
    "surface-aging-details",
    "surface-aging",
    "surface-wear",
    "ceiling-details",
    "walk-map",
    "map-walk",
    "walk-exterior",
    "first-person-map",
    "walk",
    "walk-interior",
    "first-person",
    "walkthrough",
    "interior-only",
    "interior-cutaway",
    "interior-plan",
    "public-interior-plan",
    "top-interior",
    "cutaway",
    "chambers-top",
    "chamber-top",
    "top-chambers",
    "house-plan",
    "house-chamber-plan",
    "house-top",
    "senate-plan",
    "senate-chamber-plan",
    "senate-top",
    "role-zones",
    "chamber-role-zones",
    "where-everyone-sits",
    "house-gallery",
    "house-public-gallery",
    "senate-gallery",
    "senate-public-gallery",
    "gameplay-items",
    "game-play-items",
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
    "public_lectern_reading_lamp",
    "public_work_table",
    "public_work_table_lamp",
    "gallery_divider",
    "balcony_fascia",
    "desk_surface_marker",
    "aisle_step_light",
    "row_marker_plaque",
    "rostrum_microphone_cluster",
    "rostrum_desk_front_panel_detail",
    "rostrum_desk_brass_pull_detail",
    "generic_rostrum_seal_medallion",
    "gallery_stanchion",
    "gallery_support_column",
    "public_display_board",
    "generic_desk_surface_inset",
    "generic_desk_edge_trim",
    "generic_document_stack",
    "generic_desk_microphone_marker",
    "generic_nameplate_strip",
    "generic_chair_arm_pair",
    "generic_chair_cushion",
    "generic_chair_back_inset",
    "generic_chair_cushion_seam",
    "generic_chair_cushion_piping",
    "generic_chair_leather_wear_patch",
    "generic_chair_arm_wear",
    "generic_chair_back_button",
    "generic_chair_back_leather_scuff",
    "generic_desk_drawer_pull",
    "generic_desk_wood_grain_strip",
    "generic_desk_varnish_highlight",
    "generic_row_modesty_panel",
    "generic_beveled_chamber_furniture",
    "public_role_zone_floor_overlay",
    "public_role_zone_boundary",
    "public_role_zone_label_plaque",
    "gallery_rail_baluster",
    "chamber_wall_acoustic_panel",
    "chamber_wall_sconce_fixture",
    "chamber_wall_pilaster_strip",
    "gallery_edge_trim",
    "gallery_rail_top_cap",
    "gallery_rail_rosette",
    "public_display_board_frame_detail",
    "chamber_upper_wall_frieze_panel",
    "chamber_ceiling_cove_molding",
    "balcony_underside_coffer",
    "chamber_public_light_globe",
    "chamber_carpet_aisle_runner",
    "chamber_carpet_binding_strip",
    "chamber_carpet_weave_band",
    "chamber_carpet_edge_fringe",
    "chamber_carpet_wear_path",
    "chamber_row_shadow_strip",
    "gallery_tread_nosing",
    "rostrum_backdrop_trim_inlay",
    "chamber_carpet_medallion",
    "chamber_flag_cloth_panel",
    "chamber_flag_fold_strip",
    "chamber_flag_stripe_detail",
    "chamber_flag_canton_marker",
}

REQUIRED_OFFICE_DETAIL_KINDS = {
    "public_office_corridor_band",
    "shared_support_table",
    "office_door_threshold",
    "generic_office_door_panel",
    "generic_office_plaque",
    "generic_office_desk_surface_inset",
    "generic_office_chair_back",
    "generic_office_chair_arm_pair",
    "generic_office_bookcase",
    "generic_office_storage_cabinet",
}

REQUIRED_CIRCULATION_DETAIL_KINDS = {
    "public_corridor_band",
    "door_threshold",
    "room_portal_trim",
    "public_portal_transom",
    "public_portal_opening_shadow",
    "public_portal_jamb_return",
    "orientation_sign",
    "floor_inlay",
    "public_corridor_pilaster",
    "public_corridor_sconce",
    "public_floor_medallion",
    "public_transition_arch_surround",
    "public_transition_reveal_panel",
    "public_transition_keystone",
    "public_transition_floor_mosaic",
    "public_transition_lintel_shadow",
    "public_threshold_marble_insert",
    "public_threshold_brass_edge",
    "public_transition_light_pool",
}

REQUIRED_SIGNAGE_DETAIL_KINDS = {
    "public_room_identification_sign",
    "public_directional_sign",
    "visitor_gallery_sign",
    "chamber_role_sign",
    "generic_office_zone_sign",
    "public_map_kiosk",
    "sign_typography_stroke",
    "map_kiosk_route_line",
}

REQUIRED_DOOR_DETAIL_KINDS = {
    "public_double_door_panel",
    "door_pull_bar",
    "hinge_plate",
    "door_kick_plate",
    "transom_panel",
    "door_header_trim",
    "side_lite_panel",
}

REQUIRED_FURNISHING_DETAIL_KINDS = {
    "public_bench",
    "bench_seat_slat",
    "bench_arm_rest",
    "display_case",
    "display_case_edge_trim",
    "display_case_object_silhouette",
    "display_case_light_strip",
    "display_case_label_plaque",
    "information_lectern",
    "lectern_text_line",
    "waste_receptacle",
    "receptacle_sorting_label",
    "plant_urn",
    "plant_urn_rim",
    "plant_leaf_cluster",
    "public_queue_post",
    "queue_rope_segment",
}

REQUIRED_WALL_FINISH_DETAIL_KINDS = {
    "baseboard",
    "picture_rail",
    "raised_wainscot_frame",
    "decorative_wall_panel",
    "upper_wall_panel_frame",
    "wall_pilaster",
    "public_architrave_trim",
    "wall_material_variation_panel",
    "beveled_wall_trim_profile",
    "baseboard_grime_decal",
    "wall_patina_decal",
    "wainscot_rub_mark",
}

REQUIRED_ROTUNDA_DETAIL_KINDS = {
    "wall_ring",
    "floor_trim_ring",
    "center_floor_medallion",
    "floor_radial_inlay",
    "perimeter_column",
    "perimeter_column_base",
    "perimeter_column_capital",
    "column_fluting_groove",
    "upper_coffer_panel",
    "public_arch_portal",
    "arch_spandrel_inlay",
    "arch_keystone_block",
    "upper_balustrade",
    "upper_balustrade_post",
    "oculus_trim_ring",
    "dome_springline_molding",
    "dome_coffer_belt_ring",
    "interior_dome_rib",
    "interior_dome_coffer_panel",
    "interior_frieze_panel",
    "oculus_light_pool",
    "statue_pedestal_base",
    "statue_pedestal_plaque",
}

REQUIRED_PUBLIC_ART_TYPES = {
    "statue",
    "statue_plinth_detail",
    "statue_torso_silhouette",
    "statue_head_silhouette",
    "statue_public_plaque",
    "historical_painting_panel",
    "historical_painting_title_plaque",
    "rotunda_frieze_relief_panel",
    "public_hall_art_panel",
    "historic_chamber_art_panel",
    "portrait_panel",
    "art_frame_inner_bevel",
    "art_canvas_tone_patch",
    "art_label_plaque",
}

EXPECTED_ROTUNDA_HISTORICAL_PAINTINGS = {
    "Declaration of Independence",
    "Surrender of General Burgoyne",
    "Surrender of Lord Cornwallis",
    "General George Washington Resigning His Commission",
    "Landing of Columbus",
    "Discovery of the Mississippi by De Soto",
    "Baptism of Pocahontas",
    "Embarkation of the Pilgrims",
}

REQUIRED_LIGHT_FIXTURE_DETAIL_KINDS = {
    "chandelier_chain",
    "chandelier_armature",
    "chandelier_glass_bulb_cluster",
    "pendant_canopy_detail",
    "pendant_glass_shade_detail",
    "sconce_backplate_detail",
    "sconce_glass_shade_detail",
    "fixture_beveled_mount",
    "fixture_glass_trim_ring",
    "fixture_glass_shade_rib",
    "fixture_finial_detail",
}

REQUIRED_CEILING_DETAIL_KINDS = {
    "crown_molding",
    "ceiling_grid_beam",
    "coffer_panel",
    "ceiling_medallion",
    "light_canopy",
    "light_fixture_trim_ring",
    "light_fixture_glass_dome",
    "ceiling_vent_grille",
    "ceiling_material_variation_panel",
    "beveled_ceiling_trim_profile",
    "coffer_recess_shadow",
}

REQUIRED_FLOOR_DETAIL_KINDS = {
    "floor_border_strip",
    "marble_tile_joint",
    "marble_vein_decal",
    "carpet_border_strip",
    "carpet_pile_variation_decal",
    "public_threshold_slab",
    "threshold_tarnish_decal",
    "floor_medallion",
    "floor_wear_band",
    "floor_wear_scuff_patch",
    "public_room_outline_inlay",
    "public_room_axis_inlay",
    "public_column_footprint_marker",
}

REQUIRED_SURFACE_AGING_DETAIL_KINDS = {
    "baseboard_dust_shadow",
    "wall_corner_grime_streak",
    "threshold_dirt_track",
    "desk_edge_wear_patch",
    "chair_leather_scuff_patch",
    "gallery_seat_rub_shadow",
    "brass_tarnish_patch",
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
    "public_hedge",
    "path_edge_stone",
    "grounds_bench",
    "ornamental_planting_cluster",
}

REQUIRED_STREETSCAPE_PROP_KINDS = {
    "streetlight",
    "streetlight_fixture_detail",
    "street_name_sign",
    "street_name_sign_text_strokes",
    "traffic_signal_prop",
    "traffic_signal_mast_arm",
    "traffic_signal_backplate",
    "tree_planter",
    "road_stop_bar",
    "lane_direction_arrow",
    "bike_symbol",
    "curb_ramp_visual",
    "public_wayfinding_sign",
    "public_bike_rack",
    "public_trash_receptacle",
    "public_bus_stop_shelter",
    "public_hydrant_marker",
    "crosswalk_ladder_marking",
    "tactile_warning_surface",
    "sidewalk_expansion_joint",
    "bike_lane_delineator_post",
    "bike_lane_delineator_base_plate",
    "pedestrian_signal_marker",
    "regulatory_stop_sign",
    "bike_route_sign",
    "crosswalk_ahead_sign",
    "curb_paint_segment",
    "road_asphalt_patch",
    "road_crack_line",
    "sidewalk_grime_strip",
    "sidewalk_stain_patch",
    "curb_gutter_grime_strip",
    "bike_lane_surface_scuff",
    "crosswalk_paint_wear_patch",
    "road_tire_wear_band",
    "public_manhole_cover",
    "storm_drain_grate",
    "storm_drain_curb_inlet",
    "public_utility_box",
    "public_news_box",
    "bus_stop_shelter_bench",
    "bus_stop_route_panel",
}

REQUIRED_BUILDING_DETAIL_KINDS = {
    "surrounding_building_roofline",
    "surrounding_building_cornice_band",
    "surrounding_building_parapet_coping",
    "surrounding_building_corner_pier",
    "surrounding_building_floor_band",
    "surrounding_building_facade_pilaster",
    "surrounding_building_facade_window",
    "surrounding_building_window_sill",
    "surrounding_building_window_lintel",
    "surrounding_building_window_mullion",
    "surrounding_building_window_recess_shadow",
    "surrounding_building_window_inner_sash",
    "surrounding_building_window_pane_highlight",
    "surrounding_building_public_entry_marker",
    "surrounding_building_entry_frame",
    "surrounding_building_entry_transom",
    "surrounding_building_entry_threshold",
    "surrounding_building_entry_pull_bar",
    "surrounding_building_entry_center_seam",
    "surrounding_building_awning",
    "surrounding_building_wall_sign",
    "surrounding_building_rooftop_detail",
    "surrounding_building_roof_access_hatch",
    "surrounding_building_rooftop_mechanical",
    "surrounding_building_rooftop_louver",
    "surrounding_building_roof_pipe_stack",
    "surrounding_building_roof_vent_cap",
    "surrounding_building_roof_conduit",
}

REQUIRED_VIEWPOINTS = {
    "CapitolMap_Camera_Overview",
    "CapitolMap_Camera_WestFront_FirstPerson",
    "CapitolMap_Camera_PublicInteriorWalk",
    "CapitolMap_Camera_WestGrounds",
    "CapitolMap_Camera_Rotunda",
    "CapitolMap_Camera_HouseChamber_JointSession",
    "CapitolMap_Camera_SenateChamber",
    "CapitolMap_Camera_Chambers_TopDown",
    "CapitolMap_Camera_HouseChamber_TopDown",
    "CapitolMap_Camera_SenateChamber_TopDown",
    "CapitolMap_Camera_ChamberRoleZones_TopDown",
    "CapitolMap_Camera_HouseGallery_TopDown",
    "CapitolMap_Camera_SenateGallery_TopDown",
    "CapitolMap_Camera_Interior_Cutaway",
    "CapitolMap_Camera_PublicInterior_TopDown",
    "CapitolMap_Camera_GameplayItems",
}

REQUIRED_UNREAL_INSPECTION_MARKERS = {
    "INTERIOR_TOPDOWN_INSPECTION",
    "INTERIOR_CUTAWAY_INSPECTION",
    "UNREAL_INSPECTION_WORKFLOWS",
    "MESH_INSPECTION_VISIBILITY",
    "CapitolMap_VisibleForInteriorTopDown",
    "CapitolMap_HideForInteriorTopDown",
    "CapitolMap_Camera_Interior_Cutaway",
    "CapitolMap_Camera_PublicInterior_TopDown",
    "CapitolMap_Camera_ChamberRoleZones_TopDown",
    "CapitolMap_Camera_HouseGallery_TopDown",
    "CapitolMap_Camera_SenateGallery_TopDown",
    "CapitolMap_VisibleForInteriorCutaway",
    "CapitolMap_HideForInteriorCutaway",
    "interior_cutaway_inspection",
    "inspection_workflows",
    "#role-zones",
    "#house-gallery",
    "#senate-gallery",
    "chamber_role_overlay",
    "public_schematic_non_operational",
    "person_specific",
    "CapitolMap/Meshes/InteriorTopDownVisible",
    "CapitolMap/Meshes/HideForInteriorTopDown",
    "set_actor_tags",
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
    "facade_window_recess_shadow",
    "facade_window_inner_sash",
    "facade_window_pane_highlight",
    "facade_dentil_course",
    "facade_dentil_block_detail",
    "facade_cornice_bracket",
    "facade_pilaster",
    "facade_ashlar_course",
    "facade_vertical_stone_joint",
    "facade_weathering_stain",
    "facade_limestone_discoloration_patch",
    "facade_sill_runoff_stain",
    "facade_base_grime_band",
    "facade_mortar_shadow_groove",
    "facade_staggered_masonry_joint",
    "facade_chipped_limestone_block",
    "facade_panel_bevel_strip",
    "facade_beveled_massing",
    "facade_recess_shadow_panel",
    "facade_arcade_shadow_bay",
    "facade_corner_quoin_block",
    "attic_window_band",
    "cornice_shadow_reveal",
    "stepped_pavilion_massing",
    "pavilion_setback_reveal",
    "facade_shadow_return",
    "facade_water_table",
    "exterior_column_base",
    "exterior_column_capital",
    "exterior_column_fluting",
    "exterior_column_fluting_groove",
    "exterior_column_base_ring_detail",
    "exterior_column_capital_abacus_detail",
    "portico_soffit_coffer",
    "portico_intercolumn_shadow",
    "portico_architrave_band",
    "portico_frieze_band",
    "portico_frieze_panel_detail",
    "portico_cornice_band",
    "pediment_raking_cornice_block",
    "portico_side_cornice_return",
    "terrace_retaining_wall",
    "public_stair_tread",
    "public_step_edge_chip_shadow",
    "public_step_grime_seam",
    "terrace_stair_riser_band",
    "public_terrace_landing_slab",
    "public_approach_handrail",
    "public_door_surround",
    "public_entry_lamp",
    "public_facade_sconce",
    "facade_uplight",
    "plaza_wear_patch",
    "facade_arch_window_trim",
    "facade_window_keystone",
    "pediment_sculptural_relief_block",
    "pediment_rosette_relief_detail",
    "pediment_garland_relief_detail",
    "roof_balustrade",
    "roof_articulation_volume",
    "roof_slope_skirt_panel",
    "roof_surface_joint",
    "roof_monitor_ridge",
    "roof_capstone_block",
    "parapet_corner_pier",
    "roof_parapet_shadow_gap",
    "roof_drain_scupper",
    "generic_roof_vent_housing",
    "wing_transition_block",
    "courtyard_notch_shadow",
    "roof_dormer",
    "roof_skylight_strip",
    "dome_balustrade_posts",
    "dome_vertical_rib",
    "dome_curved_rib",
    "dome_drum_arcade_bay",
    "dome_shell_panel_frame",
    "dome_drum_window_trim",
    "dome_drum_spandrel_panel",
    "dome_lateral_band",
    "lantern_window",
    "lantern_window_trim",
    "lantern_column",
    "lantern_balustrade",
    "dome_finial",
    "statue_of_freedom_silhouette",
    "pediment_relief_panel",
}

REQUIRED_TEXTURE_STYLES = {
    "ashlar_limestone",
    "weathered_ashlar_limestone",
    "painted_dome_panels",
    "wood_planks",
    "marble_floor",
    "marble_wall",
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
    buildings = exterior.get("buildings", [])
    summary["buildings"] = len(buildings)
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
    building_height_sources = Counter(building.get("height_source", "missing") for building in buildings)
    summary["building_height_sources"] = dict(sorted(building_height_sources.items()))
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
    if any(not is_number(building.get("height_m")) for building in buildings):
        error(errors, "expected every surrounding building to include numeric height_m")
    if "missing" in building_height_sources:
        error(errors, "expected every surrounding building to include height_source provenance")
    if building_height_sources.get("explicit_height_tag", 0) < 20:
        error(errors, "expected at least 20 surrounding buildings with explicit height tags")
    if building_height_sources.get("building_levels_estimate", 0) < 100:
        error(errors, "expected at least 100 surrounding buildings with building-level height estimates")
    if building_height_sources.get("default_11m_no_height_tag", 0) < 2000:
        error(errors, "expected at least 2000 surrounding buildings marked as default-height estimates")
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
    if len(building_details) < 7300:
        error(errors, f"expected at least 7300 surrounding building visual detail records, got {len(building_details)}")
    missing_building_detail_kinds = sorted(REQUIRED_BUILDING_DETAIL_KINDS - building_detail_kinds)
    if missing_building_detail_kinds:
        error(errors, f"missing surrounding building detail kinds: {', '.join(missing_building_detail_kinds)}")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_roofline"]) < 35:
        error(errors, "expected at least 35 surrounding building roofline records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_cornice_band"]) < 35:
        error(errors, "expected at least 35 surrounding building cornice-band records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_parapet_coping"]) < 35:
        error(errors, "expected at least 35 surrounding building parapet-coping records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_corner_pier"]) < 150:
        error(errors, "expected at least 150 surrounding building corner-pier records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_floor_band"]) < 180:
        error(errors, "expected at least 180 surrounding building floor-band records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_facade_pilaster"]) < 500:
        error(errors, "expected at least 500 surrounding building facade-pilaster records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_facade_window"]) < 360:
        error(errors, "expected at least 360 surrounding building facade-window records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_window_sill"]) < 800:
        error(errors, "expected at least 800 surrounding building window-sill records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_window_lintel"]) < 800:
        error(errors, "expected at least 800 surrounding building window-lintel records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_window_mullion"]) < 800:
        error(errors, "expected at least 800 surrounding building window-mullion records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_window_recess_shadow"]) < 800:
        error(errors, "expected at least 800 surrounding building window recess-shadow records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_window_inner_sash"]) < 800:
        error(errors, "expected at least 800 surrounding building window inner-sash records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_window_pane_highlight"]) < 800:
        error(errors, "expected at least 800 surrounding building window pane-highlight records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_public_entry_marker"]) < 35:
        error(errors, "expected at least 35 surrounding building public-entry marker records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_entry_frame"]) < 35:
        error(errors, "expected at least 35 surrounding building entry-frame records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_entry_transom"]) < 35:
        error(errors, "expected at least 35 surrounding building entry-transom records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_entry_threshold"]) < 35:
        error(errors, "expected at least 35 surrounding building entry-threshold records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_entry_pull_bar"]) < 35:
        error(errors, "expected at least 35 surrounding building entry pull-bar records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_entry_center_seam"]) < 35:
        error(errors, "expected at least 35 surrounding building entry center-seam records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_awning"]) < 35:
        error(errors, "expected at least 35 surrounding building awning records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_wall_sign"]) < 35:
        error(errors, "expected at least 35 surrounding building wall-sign records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_rooftop_detail"]) < 60:
        error(errors, "expected at least 60 surrounding building rooftop-detail records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_roof_access_hatch"]) < 70:
        error(errors, "expected at least 70 surrounding building roof-access hatch records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_rooftop_mechanical"]) < 70:
        error(errors, "expected at least 70 surrounding building rooftop-mechanical records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_rooftop_louver"]) < 70:
        error(errors, "expected at least 70 surrounding building rooftop-louver records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_roof_pipe_stack"]) < 70:
        error(errors, "expected at least 70 surrounding building roof pipe-stack records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_roof_vent_cap"]) < 70:
        error(errors, "expected at least 70 surrounding building roof vent-cap records")
    if len([detail for detail in building_details if detail.get("kind") == "surrounding_building_roof_conduit"]) < 70:
        error(errors, "expected at least 70 surrounding building roof-conduit records")
    for detail in building_details[:12]:
        if not is_vec3(detail.get("center_m")):
            error(errors, f"building detail {detail.get('name', '<unknown>')} has invalid center_m")
            break
        if "public" not in detail.get("public_accuracy", ""):
            error(errors, f"building detail {detail.get('name', '<unknown>')} lacks public accuracy boundary")
            break
    if len(streetscape_props) < 2250:
        error(errors, f"expected at least 2250 public streetscape props, got {len(streetscape_props)}")
    missing_streetscape_kinds = sorted(REQUIRED_STREETSCAPE_PROP_KINDS - streetscape_prop_kinds)
    if missing_streetscape_kinds:
        error(errors, f"missing public streetscape prop kinds: {', '.join(missing_streetscape_kinds)}")
    if len([prop for prop in streetscape_props if prop.get("kind") == "road_stop_bar"]) < 12:
        error(errors, "expected at least 12 public road stop-bar props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "streetlight_fixture_detail"]) < 250:
        error(errors, "expected at least 250 public streetlight fixture-detail props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "street_name_sign_text_strokes"]) < 170:
        error(errors, "expected at least 170 public street-name sign text-stroke props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "traffic_signal_mast_arm"]) < 150:
        error(errors, "expected at least 150 public traffic-signal mast-arm props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "traffic_signal_backplate"]) < 150:
        error(errors, "expected at least 150 public traffic-signal backplate props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "lane_direction_arrow"]) < 12:
        error(errors, "expected at least 12 public lane-direction arrow props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "bike_symbol"]) < 8:
        error(errors, "expected at least 8 public bike-symbol props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "curb_ramp_visual"]) < 16:
        error(errors, "expected at least 16 public curb-ramp visual props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "public_wayfinding_sign"]) < 8:
        error(errors, "expected at least 8 public wayfinding sign props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "public_bike_rack"]) < 12:
        error(errors, "expected at least 12 public bike-rack props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "public_trash_receptacle"]) < 16:
        error(errors, "expected at least 16 public trash/recycling receptacle props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "public_bus_stop_shelter"]) < 8:
        error(errors, "expected at least 8 public bus-stop shelter props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "public_hydrant_marker"]) < 16:
        error(errors, "expected at least 16 public hydrant-marker props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "crosswalk_ladder_marking"]) < 12:
        error(errors, "expected at least 12 public crosswalk ladder-marking props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "tactile_warning_surface"]) < 16:
        error(errors, "expected at least 16 public tactile warning-surface props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "sidewalk_expansion_joint"]) < 32:
        error(errors, "expected at least 32 public sidewalk expansion-joint props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "bike_lane_delineator_post"]) < 64:
        error(errors, "expected at least 64 public bike-lane delineator posts")
    if len([prop for prop in streetscape_props if prop.get("kind") == "bike_lane_delineator_base_plate"]) < 64:
        error(errors, "expected at least 64 public bike-lane delineator base-plate props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "pedestrian_signal_marker"]) < 16:
        error(errors, "expected at least 16 public pedestrian signal-marker props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "regulatory_stop_sign"]) < 12:
        error(errors, "expected at least 12 public regulatory stop-sign props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "bike_route_sign"]) < 12:
        error(errors, "expected at least 12 public bike-route sign props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "crosswalk_ahead_sign"]) < 12:
        error(errors, "expected at least 12 public crosswalk-ahead sign props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "curb_paint_segment"]) < 16:
        error(errors, "expected at least 16 public curb-paint segment props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "road_asphalt_patch"]) < 24:
        error(errors, "expected at least 24 public road asphalt patch props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "road_crack_line"]) < 32:
        error(errors, "expected at least 32 public road crack-line props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "sidewalk_grime_strip"]) < 36:
        error(errors, "expected at least 36 public sidewalk grime-strip props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "sidewalk_stain_patch"]) < 32:
        error(errors, "expected at least 32 public sidewalk stain-patch props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "curb_gutter_grime_strip"]) < 32:
        error(errors, "expected at least 32 public curb gutter-grime strip props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "bike_lane_surface_scuff"]) < 20:
        error(errors, "expected at least 20 public bike-lane surface-scuff props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "crosswalk_paint_wear_patch"]) < 24:
        error(errors, "expected at least 24 public crosswalk paint-wear patch props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "road_tire_wear_band"]) < 16:
        error(errors, "expected at least 16 public road tire-wear band props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "public_manhole_cover"]) < 12:
        error(errors, "expected at least 12 public manhole-cover props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "storm_drain_grate"]) < 16:
        error(errors, "expected at least 16 public storm-drain grate props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "storm_drain_curb_inlet"]) < 16:
        error(errors, "expected at least 16 public storm-drain curb-inlet props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "public_utility_box"]) < 12:
        error(errors, "expected at least 12 public utility-box props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "public_news_box"]) < 12:
        error(errors, "expected at least 12 public news-box props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "bus_stop_shelter_bench"]) < 8:
        error(errors, "expected at least 8 public bus-stop shelter bench-detail props")
    if len([prop for prop in streetscape_props if prop.get("kind") == "bus_stop_route_panel"]) < 8:
        error(errors, "expected at least 8 public bus-stop route-panel props")
    for prop in streetscape_props[:12]:
        if not is_vec3(prop.get("center_m")):
            error(errors, f"streetscape prop {prop.get('name', '<unknown>')} has invalid center_m")
            break
    if len(grounds_details) < 165:
        error(errors, f"expected at least 165 public grounds detail records, got {len(grounds_details)}")
    missing_grounds_kinds = sorted(REQUIRED_GROUNDS_DETAIL_KINDS - grounds_detail_kinds)
    if missing_grounds_kinds:
        error(errors, f"missing public grounds detail kinds: {', '.join(missing_grounds_kinds)}")
    if len(grounds_walk_lamps) < 18:
        error(errors, f"expected at least 18 public grounds walk lamps, got {len(grounds_walk_lamps)}")
    if len([detail for detail in grounds_details if detail.get("kind") == "public_hedge"]) < 12:
        error(errors, "expected at least 12 public hedge records")
    if len([detail for detail in grounds_details if detail.get("kind") == "path_edge_stone"]) < 16:
        error(errors, "expected at least 16 public path edge stone records")
    if len([detail for detail in grounds_details if detail.get("kind") == "grounds_bench"]) < 16:
        error(errors, "expected at least 16 public grounds bench records")
    if len([detail for detail in grounds_details if detail.get("kind") == "ornamental_planting_cluster"]) < 24:
        error(errors, "expected at least 24 ornamental planting cluster records")
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
    if len(facade_details) < 4050:
        error(errors, f"expected at least 4050 public facade/furniture visual details, got {len(facade_details)}")
    missing_facade_kinds = sorted(REQUIRED_FACADE_DETAIL_KINDS - facade_detail_kinds)
    if missing_facade_kinds:
        error(errors, f"missing public facade detail kinds: {', '.join(missing_facade_kinds)}")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_window_surround"]) < 240:
        error(errors, "expected at least 240 facade window surround records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_window_mullion"]) < 260:
        error(errors, "expected at least 260 facade window mullion records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_window_recess_shadow"]) < 260:
        error(errors, "expected at least 260 facade window recess-shadow records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_window_inner_sash"]) < 260:
        error(errors, "expected at least 260 facade window inner-sash records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_window_pane_highlight"]) < 260:
        error(errors, "expected at least 260 facade window pane-highlight records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_dentil_course"]) < 8:
        error(errors, "expected at least 8 facade dentil course records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_dentil_block_detail"]) < 116:
        error(errors, "expected at least 116 individual public facade dentil block records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_cornice_bracket"]) < 100:
        error(errors, "expected at least 100 facade cornice bracket records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_pilaster"]) < 48:
        error(errors, "expected at least 48 public facade pilaster records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_ashlar_course"]) < 70:
        error(errors, "expected at least 70 public facade ashlar course records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_vertical_stone_joint"]) < 68:
        error(errors, "expected at least 68 public facade vertical stone joint records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_weathering_stain"]) < 90:
        error(errors, "expected at least 90 public facade weathering stain records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_limestone_discoloration_patch"]) < 96:
        error(errors, "expected at least 96 public facade limestone discoloration patch records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_sill_runoff_stain"]) < 112:
        error(errors, "expected at least 112 public facade sill runoff stain records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_base_grime_band"]) < 10:
        error(errors, "expected at least 10 public facade base grime band records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_mortar_shadow_groove"]) < 48:
        error(errors, "expected at least 48 close-range facade mortar shadow-groove records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_staggered_masonry_joint"]) < 600:
        error(errors, "expected at least 600 close-range staggered masonry joint records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_chipped_limestone_block"]) < 160:
        error(errors, "expected at least 160 close-range chipped limestone block records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_panel_bevel_strip"]) < 16:
        error(errors, "expected at least 16 close-range facade panel bevel-strip records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_beveled_massing"]) < 32:
        error(errors, "expected at least 32 beveled public facade massing records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_recess_shadow_panel"]) < 130:
        error(errors, "expected at least 130 public facade recess shadow panel records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_arcade_shadow_bay"]) < 24:
        error(errors, "expected at least 24 public facade arcade shadow bay records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_corner_quoin_block"]) < 200:
        error(errors, "expected at least 200 public facade corner quoin block records")
    if len([detail for detail in facade_details if detail.get("kind") == "attic_window_band"]) < 76:
        error(errors, "expected at least 76 public attic-window band records")
    if len([detail for detail in facade_details if detail.get("kind") == "cornice_shadow_reveal"]) < 10:
        error(errors, "expected at least 10 public cornice shadow-reveal records")
    if len([detail for detail in facade_details if detail.get("kind") == "stepped_pavilion_massing"]) < 12:
        error(errors, "expected at least 12 public stepped pavilion massing records")
    if len([detail for detail in facade_details if detail.get("kind") == "pavilion_setback_reveal"]) < 12:
        error(errors, "expected at least 12 public pavilion setback-reveal records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_shadow_return"]) < 12:
        error(errors, "expected at least 12 public facade shadow-return records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_water_table"]) < 10:
        error(errors, "expected at least 10 public facade water-table records")
    if len([detail for detail in facade_details if detail.get("kind") == "exterior_column_base"]) < 28:
        error(errors, "expected at least 28 public exterior column base records")
    if len([detail for detail in facade_details if detail.get("kind") == "exterior_column_capital"]) < 28:
        error(errors, "expected at least 28 public exterior column capital records")
    if len([detail for detail in facade_details if detail.get("kind") == "exterior_column_fluting"]) < 28:
        error(errors, "expected at least 28 public exterior column fluting records")
    if len([detail for detail in facade_details if detail.get("kind") == "exterior_column_fluting_groove"]) < 336:
        error(errors, "expected at least 336 public exterior column fluting groove records")
    if len([detail for detail in facade_details if detail.get("kind") == "exterior_column_base_ring_detail"]) < 28:
        error(errors, "expected at least 28 public exterior column base ring detail records")
    if len([detail for detail in facade_details if detail.get("kind") == "exterior_column_capital_abacus_detail"]) < 28:
        error(errors, "expected at least 28 public exterior column capital abacus detail records")
    if len([detail for detail in facade_details if detail.get("kind") == "portico_soffit_coffer"]) < 70:
        error(errors, "expected at least 70 public portico soffit coffer records")
    if len([detail for detail in facade_details if detail.get("kind") == "portico_intercolumn_shadow"]) < 24:
        error(errors, "expected at least 24 public portico intercolumn shadow records")
    if len([detail for detail in facade_details if detail.get("kind") == "portico_architrave_band"]) < 4:
        error(errors, "expected at least 4 public portico architrave band records")
    if len([detail for detail in facade_details if detail.get("kind") == "portico_frieze_band"]) < 4:
        error(errors, "expected at least 4 public portico frieze band records")
    if len([detail for detail in facade_details if detail.get("kind") == "portico_frieze_panel_detail"]) < 36:
        error(errors, "expected at least 36 public portico frieze panel detail records")
    if len([detail for detail in facade_details if detail.get("kind") == "portico_cornice_band"]) < 4:
        error(errors, "expected at least 4 public portico cornice band records")
    if len([detail for detail in facade_details if detail.get("kind") == "pediment_raking_cornice_block"]) < 40:
        error(errors, "expected at least 40 public pediment raking-cornice block records")
    if len([detail for detail in facade_details if detail.get("kind") == "portico_side_cornice_return"]) < 8:
        error(errors, "expected at least 8 public portico side cornice-return records")
    if len([detail for detail in facade_details if detail.get("kind") == "terrace_retaining_wall"]) < 8:
        error(errors, "expected at least 8 public terrace retaining wall records")
    if len([detail for detail in facade_details if detail.get("kind") == "public_stair_tread"]) < 18:
        error(errors, "expected at least 18 public stair tread records")
    if len([detail for detail in facade_details if detail.get("kind") == "public_step_edge_chip_shadow"]) < 36:
        error(errors, "expected at least 36 public step-edge chip shadow records")
    if len([detail for detail in facade_details if detail.get("kind") == "public_step_grime_seam"]) < 160:
        error(errors, "expected at least 160 public step grime-seam records")
    if len([detail for detail in facade_details if detail.get("kind") == "terrace_stair_riser_band"]) < 22:
        error(errors, "expected at least 22 public lower terrace stair/riser band records")
    if len([detail for detail in facade_details if detail.get("kind") == "public_terrace_landing_slab"]) < 4:
        error(errors, "expected at least 4 public lower terrace landing slab records")
    if len([detail for detail in facade_details if detail.get("kind") == "public_approach_handrail"]) < 8:
        error(errors, "expected at least 8 public approach handrail records")
    if len([detail for detail in facade_details if detail.get("kind") == "public_door_surround"]) < 12:
        error(errors, "expected at least 12 public door surround records")
    if len([detail for detail in facade_details if detail.get("kind") == "public_entry_lamp"]) < 16:
        error(errors, "expected at least 16 public entry lamp records")
    if len([detail for detail in facade_details if detail.get("kind") == "public_facade_sconce"]) < 16:
        error(errors, "expected at least 16 public facade sconce records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_uplight"]) < 24:
        error(errors, "expected at least 24 public facade uplight records")
    if len([detail for detail in facade_details if detail.get("kind") == "plaza_wear_patch"]) < 30:
        error(errors, "expected at least 30 public plaza wear patch records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_arch_window_trim"]) < 112:
        error(errors, "expected at least 112 public facade arched window trim records")
    if len([detail for detail in facade_details if detail.get("kind") == "facade_window_keystone"]) < 112:
        error(errors, "expected at least 112 public facade window keystone records")
    if len([detail for detail in facade_details if detail.get("kind") == "pediment_sculptural_relief_block"]) < 32:
        error(errors, "expected at least 32 generic public pediment relief block records")
    if len([detail for detail in facade_details if detail.get("kind") == "pediment_rosette_relief_detail"]) < 32:
        error(errors, "expected at least 32 generic public pediment rosette relief records")
    if len([detail for detail in facade_details if detail.get("kind") == "pediment_garland_relief_detail"]) < 32:
        error(errors, "expected at least 32 generic public pediment garland relief records")
    if len([detail for detail in facade_details if detail.get("kind") == "roof_balustrade"]) < 6:
        error(errors, "expected at least 6 public roof balustrade records")
    if len([detail for detail in facade_details if detail.get("kind") == "roof_articulation_volume"]) < 10:
        error(errors, "expected at least 10 public roof articulation volume records")
    if len([detail for detail in facade_details if detail.get("kind") == "roof_slope_skirt_panel"]) < 28:
        error(errors, "expected at least 28 public roof slope-skirt panel records")
    if len([detail for detail in facade_details if detail.get("kind") == "roof_surface_joint"]) < 55:
        error(errors, "expected at least 55 public roof surface joint records")
    if len([detail for detail in facade_details if detail.get("kind") == "roof_monitor_ridge"]) < 8:
        error(errors, "expected at least 8 public roof monitor/ridge records")
    if len([detail for detail in facade_details if detail.get("kind") == "roof_capstone_block"]) < 220:
        error(errors, "expected at least 220 public roof capstone block records")
    if len([detail for detail in facade_details if detail.get("kind") == "parapet_corner_pier"]) < 28:
        error(errors, "expected at least 28 public parapet corner-pier records")
    if len([detail for detail in facade_details if detail.get("kind") == "roof_parapet_shadow_gap"]) < 28:
        error(errors, "expected at least 28 public roof parapet shadow gap records")
    if len([detail for detail in facade_details if detail.get("kind") == "roof_drain_scupper"]) < 56:
        error(errors, "expected at least 56 public roof drain/scupper visual records")
    if len([detail for detail in facade_details if detail.get("kind") == "generic_roof_vent_housing"]) < 18:
        error(errors, "expected at least 18 generic non-operational roof vent housing records")
    if len([detail for detail in facade_details if detail.get("kind") == "wing_transition_block"]) < 8:
        error(errors, "expected at least 8 public wing transition block records")
    if len([detail for detail in facade_details if detail.get("kind") == "courtyard_notch_shadow"]) < 8:
        error(errors, "expected at least 8 public courtyard/recess shadow records")
    if len([detail for detail in facade_details if detail.get("kind") == "roof_dormer"]) < 32:
        error(errors, "expected at least 32 public roof dormer records")
    if len([detail for detail in facade_details if detail.get("kind") == "roof_skylight_strip"]) < 8:
        error(errors, "expected at least 8 public roof skylight strip records")
    if len([detail for detail in facade_details if detail.get("kind") == "dome_vertical_rib"]) < 24:
        error(errors, "expected at least 24 dome vertical rib records")
    if len([detail for detail in facade_details if detail.get("kind") == "dome_curved_rib"]) < 24:
        error(errors, "expected at least 24 visible dome curved rib records")
    if len([detail for detail in facade_details if detail.get("kind") == "dome_drum_arcade_bay"]) < 32:
        error(errors, "expected at least 32 dome drum arcade bay records")
    if len([detail for detail in facade_details if detail.get("kind") == "dome_shell_panel_frame"]) < 96:
        error(errors, "expected at least 96 dome shell panel frame records")
    if len([detail for detail in facade_details if detail.get("kind") == "dome_drum_window_trim"]) < 16:
        error(errors, "expected at least 16 dome drum window trim records")
    if len([detail for detail in facade_details if detail.get("kind") == "dome_drum_spandrel_panel"]) < 16:
        error(errors, "expected at least 16 dome drum spandrel panel records")
    if len([detail for detail in facade_details if detail.get("kind") == "dome_lateral_band"]) < 4:
        error(errors, "expected at least 4 dome lateral band records")
    if len([detail for detail in facade_details if detail.get("kind") == "lantern_column"]) < 16:
        error(errors, "expected at least 16 lantern column records")
    if len([detail for detail in facade_details if detail.get("kind") == "lantern_window_trim"]) < 8:
        error(errors, "expected at least 8 lantern window trim records")
    if len([detail for detail in facade_details if detail.get("kind") == "lantern_balustrade"]) < 1:
        error(errors, "expected public lantern balustrade record")
    if len([detail for detail in facade_details if detail.get("kind") == "statue_of_freedom_silhouette"]) < 1:
        error(errors, "expected public Statue of Freedom silhouette record")
    for detail in [item for item in facade_details if item.get("kind") in {"public_entry_lamp", "public_facade_sconce", "facade_uplight"}]:
        if not is_vec3(detail.get("light_m")):
            error(errors, f"facade light {detail.get('name', '<unknown>')} has invalid light_m")
            break
        if not is_number(detail.get("intensity")) or not is_number(detail.get("attenuation_radius_m")):
            error(errors, f"facade light {detail.get('name', '<unknown>')} has invalid light properties")
            break
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

    office_details = interior.get("office_details", [])
    office_detail_kinds = {detail.get("kind") for detail in office_details}
    summary["office_details"] = len(office_details)
    summary["office_detail_kinds"] = len(office_detail_kinds)
    if len(office_details) < 490:
        error(errors, f"expected at least 490 public office detail records, got {len(office_details)}")
    missing_office_kinds = sorted(REQUIRED_OFFICE_DETAIL_KINDS - office_detail_kinds)
    if missing_office_kinds:
        error(errors, f"missing public office detail kinds: {', '.join(missing_office_kinds)}")
    if len([detail for detail in office_details if detail.get("kind") == "office_door_threshold"]) < 60:
        error(errors, "expected at least 60 public office door threshold records")
    if len([detail for detail in office_details if detail.get("kind") == "generic_office_door_panel"]) < 60:
        error(errors, "expected at least 60 generic office door panel records")
    if len([detail for detail in office_details if detail.get("kind") == "generic_office_plaque"]) < 60:
        error(errors, "expected at least 60 generic office plaque records")
    if len([detail for detail in office_details if detail.get("kind") == "public_office_corridor_band"]) < 4:
        error(errors, "expected at least 4 public office corridor band records")
    if len([detail for detail in office_details if detail.get("kind") == "shared_support_table"]) < 8:
        error(errors, "expected at least 8 shared support table records")
    if len([detail for detail in office_details if detail.get("kind") == "generic_office_desk_surface_inset"]) < 60:
        error(errors, "expected at least 60 generic office desk-surface inset records")
    if len([detail for detail in office_details if detail.get("kind") == "generic_office_chair_back"]) < 60:
        error(errors, "expected at least 60 generic office chair-back records")
    if len([detail for detail in office_details if detail.get("kind") == "generic_office_chair_arm_pair"]) < 60:
        error(errors, "expected at least 60 generic office chair-arm pair records")
    if len([detail for detail in office_details if detail.get("kind") == "generic_office_bookcase"]) < 60:
        error(errors, "expected at least 60 generic office bookcase records")
    if len([detail for detail in office_details if detail.get("kind") == "generic_office_storage_cabinet"]) < 60:
        error(errors, "expected at least 60 generic office storage-cabinet records")
    for detail in office_details[:12]:
        if not is_vec3(detail.get("center_m")):
            error(errors, f"office detail {detail.get('name', '<unknown>')} has invalid center_m")
            break
        assignment = detail.get("assignment", "").lower()
        if "generic public visual" not in assignment or "not an actual office assignment" not in assignment:
            error(errors, f"office detail {detail.get('name', '<unknown>')} lacks public/generic office boundary")
            break

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
    if len(chamber_details) < 10320:
        error(errors, f"expected at least 10320 public chamber detail records, got {len(chamber_details)}")
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
    if len([detail for detail in chamber_details if detail.get("kind") == "public_lectern_reading_lamp"]) < 2:
        error(errors, "expected at least 2 public lectern reading-lamp records")
    if len([detail for detail in chamber_details if detail.get("kind") == "public_work_table"]) < 4:
        error(errors, "expected at least 4 public work table records")
    if len([detail for detail in chamber_details if detail.get("kind") == "public_work_table_lamp"]) < 4:
        error(errors, "expected at least 4 public work-table lamp records")
    if len([detail for detail in chamber_details if detail.get("kind") == "gallery_divider"]) < 16:
        error(errors, "expected at least 16 public gallery divider records")
    if len([detail for detail in chamber_details if detail.get("kind") == "balcony_fascia"]) < 4:
        error(errors, "expected at least 4 public balcony fascia records")
    if len([detail for detail in chamber_details if detail.get("kind") == "desk_surface_marker"]) < 10:
        error(errors, "expected at least 10 public desk surface marker records")
    if len([detail for detail in chamber_details if detail.get("kind") == "aisle_step_light"]) < 36:
        error(errors, "expected at least 36 public chamber aisle step-light records")
    if len([detail for detail in chamber_details if detail.get("kind") == "row_marker_plaque"]) < 24:
        error(errors, "expected at least 24 public chamber row-marker plaque records")
    if len([detail for detail in chamber_details if detail.get("kind") == "rostrum_microphone_cluster"]) < 7:
        error(errors, "expected at least 7 public rostrum microphone-cluster records")
    if len([detail for detail in chamber_details if detail.get("kind") == "rostrum_desk_front_panel_detail"]) < 7:
        error(errors, "expected at least 7 public rostrum desk front-panel detail records")
    if len([detail for detail in chamber_details if detail.get("kind") == "rostrum_desk_brass_pull_detail"]) < 7:
        error(errors, "expected at least 7 public rostrum desk brass-pull detail records")
    if len([detail for detail in chamber_details if detail.get("kind") == "generic_rostrum_seal_medallion"]) < 2:
        error(errors, "expected at least 2 generic public rostrum seal medallion records")
    if len([detail for detail in chamber_details if detail.get("kind") == "gallery_stanchion"]) < 32:
        error(errors, "expected at least 32 public gallery stanchion records")
    if len([detail for detail in chamber_details if detail.get("kind") == "gallery_support_column"]) < 24:
        error(errors, "expected at least 24 public gallery support-column records")
    if len([detail for detail in chamber_details if detail.get("kind") == "public_display_board"]) < 4:
        error(errors, "expected at least 4 public chamber display-board records")
    if len([detail for detail in chamber_details if detail.get("kind") == "generic_desk_surface_inset"]) < 548:
        error(errors, "expected at least 548 generic chamber desk-surface inset records")
    if len([detail for detail in chamber_details if detail.get("kind") == "generic_desk_edge_trim"]) < 548:
        error(errors, "expected at least 548 generic chamber desk-edge trim records")
    if len([detail for detail in chamber_details if detail.get("kind") == "generic_document_stack"]) < 548:
        error(errors, "expected at least 548 generic chamber document-stack records")
    if len([detail for detail in chamber_details if detail.get("kind") == "generic_desk_microphone_marker"]) < 548:
        error(errors, "expected at least 548 generic chamber desk microphone-marker records")
    if len([detail for detail in chamber_details if detail.get("kind") == "generic_nameplate_strip"]) < 548:
        error(errors, "expected at least 548 generic chamber nameplate-strip records")
    if len([detail for detail in chamber_details if detail.get("kind") == "generic_chair_arm_pair"]) < 548:
        error(errors, "expected at least 548 generic chamber chair-arm pair records")
    if len([detail for detail in chamber_details if detail.get("kind") == "generic_chair_cushion"]) < 548:
        error(errors, "expected at least 548 generic chamber chair-cushion records")
    if len([detail for detail in chamber_details if detail.get("kind") == "generic_chair_back_inset"]) < 548:
        error(errors, "expected at least 548 generic chamber chair-back inset records")
    if len([detail for detail in chamber_details if detail.get("kind") == "generic_chair_cushion_seam"]) < 548:
        error(errors, "expected at least 548 generic chamber chair-cushion seam records")
    if len([detail for detail in chamber_details if detail.get("kind") == "generic_chair_cushion_piping"]) < 548:
        error(errors, "expected at least 548 generic chamber chair-cushion piping records")
    if len([detail for detail in chamber_details if detail.get("kind") == "generic_chair_leather_wear_patch"]) < 548:
        error(errors, "expected at least 548 generic chamber chair leather-wear patch records")
    if len([detail for detail in chamber_details if detail.get("kind") == "generic_chair_arm_wear"]) < 548:
        error(errors, "expected at least 548 generic chamber chair arm-wear records")
    if len([detail for detail in chamber_details if detail.get("kind") == "generic_chair_back_button"]) < 548:
        error(errors, "expected at least 548 generic chamber chair-back button records")
    if len([detail for detail in chamber_details if detail.get("kind") == "generic_chair_back_leather_scuff"]) < 548:
        error(errors, "expected at least 548 generic chamber chair-back leather-scuff records")
    if len([detail for detail in chamber_details if detail.get("kind") == "generic_desk_drawer_pull"]) < 548:
        error(errors, "expected at least 548 generic chamber desk drawer-pull records")
    if len([detail for detail in chamber_details if detail.get("kind") == "generic_desk_wood_grain_strip"]) < 548:
        error(errors, "expected at least 548 generic chamber desk wood-grain strip records")
    if len([detail for detail in chamber_details if detail.get("kind") == "generic_desk_varnish_highlight"]) < 548:
        error(errors, "expected at least 548 generic chamber desk varnish-highlight records")
    if len([detail for detail in chamber_details if detail.get("kind") == "generic_row_modesty_panel"]) < 26:
        error(errors, "expected at least 26 generic chamber row modesty-panel records")
    if len([detail for detail in chamber_details if detail.get("kind") == "generic_beveled_chamber_furniture"]) < 548:
        error(errors, "expected at least 548 generic beveled chamber furniture records")
    if len([detail for detail in chamber_details if detail.get("kind") == "public_role_zone_floor_overlay"]) < 16:
        error(errors, "expected at least 16 public chamber role-zone floor overlay records")
    if len([detail for detail in chamber_details if detail.get("kind") == "public_role_zone_boundary"]) < 64:
        error(errors, "expected at least 64 public chamber role-zone boundary records")
    if len([detail for detail in chamber_details if detail.get("kind") == "public_role_zone_label_plaque"]) < 16:
        error(errors, "expected at least 16 public chamber role-zone label plaque records")
    if len([detail for detail in chamber_details if detail.get("kind") == "gallery_rail_baluster"]) < 64:
        error(errors, "expected at least 64 public chamber gallery rail baluster records")
    if len([detail for detail in chamber_details if detail.get("kind") == "chamber_wall_acoustic_panel"]) < 40:
        error(errors, "expected at least 40 public chamber wall acoustic-panel records")
    if len([detail for detail in chamber_details if detail.get("kind") == "chamber_wall_sconce_fixture"]) < 28:
        error(errors, "expected at least 28 public chamber wall sconce fixture records")
    if len([detail for detail in chamber_details if detail.get("kind") == "chamber_wall_pilaster_strip"]) < 44:
        error(errors, "expected at least 44 public chamber wall pilaster-strip records")
    if len([detail for detail in chamber_details if detail.get("kind") == "gallery_edge_trim"]) < 8:
        error(errors, "expected at least 8 public chamber gallery edge-trim records")
    if len([detail for detail in chamber_details if detail.get("kind") == "gallery_rail_top_cap"]) < 4:
        error(errors, "expected at least 4 public chamber gallery rail top-cap records")
    if len([detail for detail in chamber_details if detail.get("kind") == "gallery_rail_rosette"]) < 32:
        error(errors, "expected at least 32 public chamber gallery rail rosette records")
    if len([detail for detail in chamber_details if detail.get("kind") == "public_display_board_frame_detail"]) < 4:
        error(errors, "expected at least 4 public chamber display-board frame detail records")
    if len([detail for detail in chamber_details if detail.get("kind") == "chamber_upper_wall_frieze_panel"]) < 40:
        error(errors, "expected at least 40 public chamber upper-wall frieze panel records")
    if len([detail for detail in chamber_details if detail.get("kind") == "chamber_ceiling_cove_molding"]) < 40:
        error(errors, "expected at least 40 public chamber ceiling cove-molding records")
    if len([detail for detail in chamber_details if detail.get("kind") == "balcony_underside_coffer"]) < 32:
        error(errors, "expected at least 32 public chamber balcony underside coffer records")
    if len([detail for detail in chamber_details if detail.get("kind") == "chamber_public_light_globe"]) < 28:
        error(errors, "expected at least 28 public chamber light-globe records")
    if len([detail for detail in chamber_details if detail.get("kind") == "chamber_carpet_aisle_runner"]) < 12:
        error(errors, "expected at least 12 public chamber carpet aisle-runner records")
    if len([detail for detail in chamber_details if detail.get("kind") == "chamber_carpet_binding_strip"]) < 24:
        error(errors, "expected at least 24 public chamber carpet binding-strip records")
    if len([detail for detail in chamber_details if detail.get("kind") == "chamber_carpet_weave_band"]) < 36:
        error(errors, "expected at least 36 public chamber carpet weave-band records")
    if len([detail for detail in chamber_details if detail.get("kind") == "chamber_carpet_edge_fringe"]) < 24:
        error(errors, "expected at least 24 public chamber carpet edge-fringe records")
    if len([detail for detail in chamber_details if detail.get("kind") == "chamber_carpet_wear_path"]) < 14:
        error(errors, "expected at least 14 public chamber carpet wear-path records")
    if len([detail for detail in chamber_details if detail.get("kind") == "chamber_row_shadow_strip"]) < 26:
        error(errors, "expected at least 26 public chamber row shadow-strip records")
    if len([detail for detail in chamber_details if detail.get("kind") == "gallery_tread_nosing"]) < 16:
        error(errors, "expected at least 16 public chamber gallery tread-nosing records")
    if len([detail for detail in chamber_details if detail.get("kind") == "rostrum_backdrop_trim_inlay"]) < 22:
        error(errors, "expected at least 22 public chamber rostrum backdrop trim-inlay records")
    if len([detail for detail in chamber_details if detail.get("kind") == "chamber_carpet_medallion"]) < 4:
        error(errors, "expected at least 4 public chamber carpet medallion records")
    if len([detail for detail in chamber_details if detail.get("kind") == "chamber_flag_cloth_panel"]) < 4:
        error(errors, "expected at least 4 public chamber flag cloth-panel records")
    if len([detail for detail in chamber_details if detail.get("kind") == "chamber_flag_fold_strip"]) < 12:
        error(errors, "expected at least 12 public chamber flag fold-strip records")
    if len([detail for detail in chamber_details if detail.get("kind") == "chamber_flag_stripe_detail"]) < 16:
        error(errors, "expected at least 16 public chamber flag stripe-detail records")
    if len([detail for detail in chamber_details if detail.get("kind") == "chamber_flag_canton_marker"]) < 4:
        error(errors, "expected at least 4 public chamber flag canton-marker records")
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
    if len(circulation_details) < 209:
        error(errors, f"expected at least 209 public circulation detail records, got {len(circulation_details)}")
    missing_circulation_kinds = sorted(REQUIRED_CIRCULATION_DETAIL_KINDS - circulation_detail_kinds)
    if missing_circulation_kinds:
        error(errors, f"missing public circulation detail kinds: {', '.join(missing_circulation_kinds)}")
    if len([detail for detail in circulation_details if detail.get("kind") == "public_portal_transom"]) < 8:
        error(errors, "expected at least 8 public portal transom records")
    if len([detail for detail in circulation_details if detail.get("kind") == "public_portal_opening_shadow"]) < 8:
        error(errors, "expected at least 8 public portal opening-shadow records")
    if len([detail for detail in circulation_details if detail.get("kind") == "public_portal_jamb_return"]) < 16:
        error(errors, "expected at least 16 public portal jamb-return records")
    if len([detail for detail in circulation_details if detail.get("kind") == "public_corridor_pilaster"]) < 30:
        error(errors, "expected at least 30 public corridor pilaster records")
    if len([detail for detail in circulation_details if detail.get("kind") == "public_corridor_sconce"]) < 20:
        error(errors, "expected at least 20 public corridor sconce records")
    if len([detail for detail in circulation_details if detail.get("kind") == "public_floor_medallion"]) < 8:
        error(errors, "expected at least 8 public floor medallion records")
    if len([detail for detail in circulation_details if detail.get("kind") == "public_transition_arch_surround"]) < 8:
        error(errors, "expected at least 8 public transition arch-surround records")
    if len([detail for detail in circulation_details if detail.get("kind") == "public_transition_reveal_panel"]) < 16:
        error(errors, "expected at least 16 public transition reveal-panel records")
    if len([detail for detail in circulation_details if detail.get("kind") == "public_transition_keystone"]) < 8:
        error(errors, "expected at least 8 public transition keystone records")
    if len([detail for detail in circulation_details if detail.get("kind") == "public_transition_floor_mosaic"]) < 8:
        error(errors, "expected at least 8 public transition floor-mosaic records")
    if len([detail for detail in circulation_details if detail.get("kind") == "public_transition_lintel_shadow"]) < 8:
        error(errors, "expected at least 8 public transition lintel-shadow records")
    if len([detail for detail in circulation_details if detail.get("kind") == "public_threshold_marble_insert"]) < 8:
        error(errors, "expected at least 8 public threshold marble-insert records")
    if len([detail for detail in circulation_details if detail.get("kind") == "public_threshold_brass_edge"]) < 16:
        error(errors, "expected at least 16 public threshold brass-edge records")
    if len([detail for detail in circulation_details if detail.get("kind") == "public_transition_light_pool"]) < 8:
        error(errors, "expected at least 8 public transition light-pool records")
    for detail in circulation_details:
        if not is_vec3(detail.get("center_m")):
            error(errors, f"circulation detail {detail.get('name', '<unknown>')} has invalid center_m")
            break
        assignment = detail.get("assignment", "").lower()
        if "public orientation" not in assignment or "secure route" not in assignment or "service route" not in assignment:
            error(errors, f"circulation detail {detail.get('name', '<unknown>')} lacks public/non-secure boundary")
            break

    signage_details = interior.get("signage_details", [])
    signage_detail_kinds = {detail.get("kind") for detail in signage_details}
    summary["signage_details"] = len(signage_details)
    summary["signage_detail_kinds"] = len(signage_detail_kinds)
    if len(signage_details) < 260:
        error(errors, f"expected at least 260 public signage detail records, got {len(signage_details)}")
    missing_signage_kinds = sorted(REQUIRED_SIGNAGE_DETAIL_KINDS - signage_detail_kinds)
    if missing_signage_kinds:
        error(errors, f"missing public signage detail kinds: {', '.join(missing_signage_kinds)}")
    if len([detail for detail in signage_details if detail.get("kind") == "public_room_identification_sign"]) < 9:
        error(errors, "expected at least 9 public room-identification sign records")
    if len([detail for detail in signage_details if detail.get("kind") == "public_directional_sign"]) < 16:
        error(errors, "expected at least 16 public directional sign records")
    if len([detail for detail in signage_details if detail.get("kind") == "visitor_gallery_sign"]) < 8:
        error(errors, "expected at least 8 visitor gallery sign records")
    if len([detail for detail in signage_details if detail.get("kind") == "chamber_role_sign"]) < 10:
        error(errors, "expected at least 10 chamber role sign records")
    if len([detail for detail in signage_details if detail.get("kind") == "generic_office_zone_sign"]) < 6:
        error(errors, "expected at least 6 generic office-zone sign records")
    if len([detail for detail in signage_details if detail.get("kind") == "public_map_kiosk"]) < 4:
        error(errors, "expected at least 4 public map kiosk records")
    if len([detail for detail in signage_details if detail.get("kind") == "sign_typography_stroke"]) < 196:
        error(errors, "expected at least 196 public sign typography-stroke records")
    if len([detail for detail in signage_details if detail.get("kind") == "map_kiosk_route_line"]) < 12:
        error(errors, "expected at least 12 public map kiosk route-line records")
    for detail in signage_details:
        if not detail.get("area"):
            error(errors, f"signage detail {detail.get('name', '<unknown>')} is missing area")
            break
        if not is_vec3(detail.get("center_m")):
            error(errors, f"signage detail {detail.get('name', '<unknown>')} has invalid center_m")
            break
        public_accuracy = detail.get("public_accuracy", "").lower()
        assignment = detail.get("assignment", "").lower()
        if (
            "public" not in public_accuracy
            or "public visual" not in assignment
            or "restricted route" not in assignment
            or "security feature" not in assignment
            or "operational" not in assignment
        ):
            error(errors, f"signage detail {detail.get('name', '<unknown>')} lacks public/non-operational boundary")
            break

    door_details = interior.get("door_details", [])
    door_detail_kinds = {detail.get("kind") for detail in door_details}
    summary["door_details"] = len(door_details)
    summary["door_detail_kinds"] = len(door_detail_kinds)
    if len(door_details) < 180:
        error(errors, f"expected at least 180 public door detail records, got {len(door_details)}")
    missing_door_kinds = sorted(REQUIRED_DOOR_DETAIL_KINDS - door_detail_kinds)
    if missing_door_kinds:
        error(errors, f"missing public door detail kinds: {', '.join(missing_door_kinds)}")
    if len([detail for detail in door_details if detail.get("kind") == "public_double_door_panel"]) < 24:
        error(errors, "expected at least 24 public double-door panel records")
    if len([detail for detail in door_details if detail.get("kind") == "door_pull_bar"]) < 24:
        error(errors, "expected at least 24 public door pull bar records")
    if len([detail for detail in door_details if detail.get("kind") == "hinge_plate"]) < 72:
        error(errors, "expected at least 72 public hinge plate records")
    if len([detail for detail in door_details if detail.get("kind") == "door_kick_plate"]) < 24:
        error(errors, "expected at least 24 public kick plate records")
    if len([detail for detail in door_details if detail.get("kind") == "transom_panel"]) < 12:
        error(errors, "expected at least 12 public transom panel records")
    if len([detail for detail in door_details if detail.get("kind") == "door_header_trim"]) < 12:
        error(errors, "expected at least 12 public door header trim records")
    if len([detail for detail in door_details if detail.get("kind") == "side_lite_panel"]) < 24:
        error(errors, "expected at least 24 public side-lite panel records")
    for detail in door_details:
        if not detail.get("area"):
            error(errors, f"door detail {detail.get('name', '<unknown>')} is missing area")
            break
        if not is_vec3(detail.get("center_m")):
            error(errors, f"door detail {detail.get('name', '<unknown>')} has invalid center_m")
            break
        public_accuracy = detail.get("public_accuracy", "").lower()
        assignment = detail.get("assignment", "").lower()
        if (
            "public" not in public_accuracy
            or "public visual" not in assignment
            or "restricted access" not in assignment
            or "security feature" not in assignment
            or "operational" not in assignment
        ):
            error(errors, f"door detail {detail.get('name', '<unknown>')} lacks public/non-operational boundary")
            break

    furnishing_details = interior.get("furnishing_details", [])
    furnishing_detail_kinds = {detail.get("kind") for detail in furnishing_details}
    summary["furnishing_details"] = len(furnishing_details)
    summary["furnishing_detail_kinds"] = len(furnishing_detail_kinds)
    if len(furnishing_details) < 530:
        error(errors, f"expected at least 530 public furnishing detail records, got {len(furnishing_details)}")
    missing_furnishing_kinds = sorted(REQUIRED_FURNISHING_DETAIL_KINDS - furnishing_detail_kinds)
    if missing_furnishing_kinds:
        error(errors, f"missing public furnishing detail kinds: {', '.join(missing_furnishing_kinds)}")
    if len([detail for detail in furnishing_details if detail.get("kind") == "public_bench"]) < 24:
        error(errors, "expected at least 24 public interior bench records")
    if len([detail for detail in furnishing_details if detail.get("kind") == "bench_seat_slat"]) < 72:
        error(errors, "expected at least 72 public bench seat-slat records")
    if len([detail for detail in furnishing_details if detail.get("kind") == "bench_arm_rest"]) < 48:
        error(errors, "expected at least 48 public bench arm-rest records")
    if len([detail for detail in furnishing_details if detail.get("kind") == "display_case"]) < 24:
        error(errors, "expected at least 24 public display case records")
    if len([detail for detail in furnishing_details if detail.get("kind") == "display_case_edge_trim"]) < 96:
        error(errors, "expected at least 96 public display case edge-trim records")
    if len([detail for detail in furnishing_details if detail.get("kind") == "display_case_object_silhouette"]) < 24:
        error(errors, "expected at least 24 public display case object-silhouette records")
    if len([detail for detail in furnishing_details if detail.get("kind") == "display_case_light_strip"]) < 48:
        error(errors, "expected at least 48 public display case light-strip records")
    if len([detail for detail in furnishing_details if detail.get("kind") == "display_case_label_plaque"]) < 24:
        error(errors, "expected at least 24 public display case label-plaque records")
    if len([detail for detail in furnishing_details if detail.get("kind") == "information_lectern"]) < 10:
        error(errors, "expected at least 10 public information lectern records")
    if len([detail for detail in furnishing_details if detail.get("kind") == "lectern_text_line"]) < 30:
        error(errors, "expected at least 30 public lectern text-line records")
    if len([detail for detail in furnishing_details if detail.get("kind") == "waste_receptacle"]) < 16:
        error(errors, "expected at least 16 public receptacle records")
    if len([detail for detail in furnishing_details if detail.get("kind") == "receptacle_sorting_label"]) < 16:
        error(errors, "expected at least 16 public receptacle sorting-label records")
    if len([detail for detail in furnishing_details if detail.get("kind") == "plant_urn"]) < 20:
        error(errors, "expected at least 20 public plant urn records")
    if len([detail for detail in furnishing_details if detail.get("kind") == "plant_urn_rim"]) < 20:
        error(errors, "expected at least 20 public plant urn rim records")
    if len([detail for detail in furnishing_details if detail.get("kind") == "plant_leaf_cluster"]) < 20:
        error(errors, "expected at least 20 public plant leaf-cluster records")
    if len([detail for detail in furnishing_details if detail.get("kind") == "public_queue_post"]) < 24:
        error(errors, "expected at least 24 public queue post records")
    if len([detail for detail in furnishing_details if detail.get("kind") == "queue_rope_segment"]) < 20:
        error(errors, "expected at least 20 public queue rope segment records")
    for detail in furnishing_details:
        if not detail.get("area"):
            error(errors, f"furnishing detail {detail.get('name', '<unknown>')} is missing area")
            break
        if not is_vec3(detail.get("center_m")):
            error(errors, f"furnishing detail {detail.get('name', '<unknown>')} has invalid center_m")
            break
        public_accuracy = detail.get("public_accuracy", "").lower()
        assignment = detail.get("assignment", "").lower()
        if (
            "public" not in public_accuracy
            or "public visual" not in assignment
            or "restricted route" not in assignment
            or "security feature" not in assignment
            or "operational" not in assignment
        ):
            error(errors, f"furnishing detail {detail.get('name', '<unknown>')} lacks public/non-operational boundary")
            break

    wall_finish_details = interior.get("wall_finish_details", [])
    wall_finish_detail_kinds = {detail.get("kind") for detail in wall_finish_details}
    wall_finish_rooms = {detail.get("room") for detail in wall_finish_details}
    summary["wall_finish_details"] = len(wall_finish_details)
    summary["wall_finish_detail_kinds"] = len(wall_finish_detail_kinds)
    if len(wall_finish_details) < 1750:
        error(errors, f"expected at least 1750 public wall-finish detail records, got {len(wall_finish_details)}")
    missing_wall_finish_kinds = sorted(REQUIRED_WALL_FINISH_DETAIL_KINDS - wall_finish_detail_kinds)
    if missing_wall_finish_kinds:
        error(errors, f"missing public wall-finish detail kinds: {', '.join(missing_wall_finish_kinds)}")
    for room in [
        "Rotunda",
        "House Chamber",
        "Senate Chamber",
        "National Statuary Hall",
        "Old Senate Chamber",
        "House galleries",
        "Senate galleries",
    ]:
        if room not in wall_finish_rooms:
            error(errors, f"missing wall-finish details for {room}")
    if len([detail for detail in wall_finish_details if detail.get("kind") == "baseboard"]) < 40:
        error(errors, "expected at least 40 public baseboard detail records")
    if len([detail for detail in wall_finish_details if detail.get("kind") == "picture_rail"]) < 44:
        error(errors, "expected at least 44 public picture rail detail records")
    if len([detail for detail in wall_finish_details if detail.get("kind") == "raised_wainscot_frame"]) < 300:
        error(errors, "expected at least 300 public raised wainscot frame records")
    if len([detail for detail in wall_finish_details if detail.get("kind") == "decorative_wall_panel"]) < 170:
        error(errors, "expected at least 170 public decorative wall panel records")
    if len([detail for detail in wall_finish_details if detail.get("kind") == "upper_wall_panel_frame"]) < 170:
        error(errors, "expected at least 170 public upper wall panel frame records")
    if len([detail for detail in wall_finish_details if detail.get("kind") == "wall_pilaster"]) < 230:
        error(errors, "expected at least 230 public wall pilaster records")
    if len([detail for detail in wall_finish_details if detail.get("kind") == "public_architrave_trim"]) < 18:
        error(errors, "expected at least 18 public architrave trim records")
    if len([detail for detail in wall_finish_details if detail.get("kind") == "wall_material_variation_panel"]) < 44:
        error(errors, "expected at least 44 public wall material-variation panel records")
    if len([detail for detail in wall_finish_details if detail.get("kind") == "beveled_wall_trim_profile"]) < 498:
        error(errors, "expected at least 498 public beveled wall-trim profile records")
    if len([detail for detail in wall_finish_details if detail.get("kind") == "baseboard_grime_decal"]) < 44:
        error(errors, "expected at least 44 public baseboard grime decal records")
    if len([detail for detail in wall_finish_details if detail.get("kind") == "wall_patina_decal"]) < 44:
        error(errors, "expected at least 44 public wall patina decal records")
    if len([detail for detail in wall_finish_details if detail.get("kind") == "wainscot_rub_mark"]) < 114:
        error(errors, "expected at least 114 public wainscot rub-mark records")
    for detail in wall_finish_details:
        if not detail.get("room"):
            error(errors, f"wall-finish detail {detail.get('name', '<unknown>')} is missing room")
            break
        if not is_vec3(detail.get("center_m")):
            error(errors, f"wall-finish detail {detail.get('name', '<unknown>')} has invalid center_m")
            break
        public_accuracy = detail.get("public_accuracy", "").lower()
        assignment = detail.get("assignment", "").lower()
        if (
            "public" not in public_accuracy
            or "public visual" not in assignment
            or "restricted room" not in assignment
            or "security feature" not in assignment
            or "operational" not in assignment
        ):
            error(errors, f"wall-finish detail {detail.get('name', '<unknown>')} lacks public/non-operational boundary")
            break

    rotunda_details = interior.get("rotunda_details", [])
    rotunda_detail_kinds = {detail.get("kind") for detail in rotunda_details}
    summary["rotunda_details"] = len(rotunda_details)
    summary["rotunda_detail_kinds"] = len(rotunda_detail_kinds)
    if len(rotunda_details) < 360:
        error(errors, f"expected at least 360 public Rotunda detail records, got {len(rotunda_details)}")
    missing_rotunda_kinds = sorted(REQUIRED_ROTUNDA_DETAIL_KINDS - rotunda_detail_kinds)
    if missing_rotunda_kinds:
        error(errors, f"missing public Rotunda detail kinds: {', '.join(missing_rotunda_kinds)}")
    if len([detail for detail in rotunda_details if detail.get("kind") == "floor_radial_inlay"]) < 16:
        error(errors, "expected at least 16 public Rotunda floor radial inlay records")
    if len([detail for detail in rotunda_details if detail.get("kind") == "perimeter_column"]) < 16:
        error(errors, "expected at least 16 public Rotunda perimeter column records")
    if len([detail for detail in rotunda_details if detail.get("kind") == "perimeter_column_base"]) < 16:
        error(errors, "expected at least 16 public Rotunda column-base records")
    if len([detail for detail in rotunda_details if detail.get("kind") == "perimeter_column_capital"]) < 16:
        error(errors, "expected at least 16 public Rotunda column-capital records")
    if len([detail for detail in rotunda_details if detail.get("kind") == "column_fluting_groove"]) < 64:
        error(errors, "expected at least 64 public Rotunda column fluting groove records")
    if len([detail for detail in rotunda_details if detail.get("kind") == "upper_coffer_panel"]) < 32:
        error(errors, "expected at least 32 public Rotunda upper coffer panel records")
    if len([detail for detail in rotunda_details if detail.get("kind") == "public_arch_portal"]) < 4:
        error(errors, "expected at least 4 public Rotunda arch portal records")
    if len([detail for detail in rotunda_details if detail.get("kind") == "arch_spandrel_inlay"]) < 8:
        error(errors, "expected at least 8 public Rotunda arch spandrel inlay records")
    if len([detail for detail in rotunda_details if detail.get("kind") == "arch_keystone_block"]) < 4:
        error(errors, "expected at least 4 public Rotunda arch keystone block records")
    if len([detail for detail in rotunda_details if detail.get("kind") == "upper_balustrade_post"]) < 32:
        error(errors, "expected at least 32 public Rotunda upper balustrade post records")
    if len([detail for detail in rotunda_details if detail.get("kind") == "oculus_trim_ring"]) < 1:
        error(errors, "expected public Rotunda oculus trim ring record")
    if len([detail for detail in rotunda_details if detail.get("kind") == "dome_springline_molding"]) < 1:
        error(errors, "expected public Rotunda dome springline molding record")
    if len([detail for detail in rotunda_details if detail.get("kind") == "dome_coffer_belt_ring"]) < 3:
        error(errors, "expected at least 3 public Rotunda dome coffer-belt ring records")
    if len([detail for detail in rotunda_details if detail.get("kind") == "interior_dome_rib"]) < 24:
        error(errors, "expected at least 24 public Rotunda interior dome rib records")
    if len([detail for detail in rotunda_details if detail.get("kind") == "interior_dome_coffer_panel"]) < 72:
        error(errors, "expected at least 72 public Rotunda interior dome coffer panel records")
    if len([detail for detail in rotunda_details if detail.get("kind") == "interior_frieze_panel"]) < 32:
        error(errors, "expected at least 32 public Rotunda interior frieze panel records")
    if len([detail for detail in rotunda_details if detail.get("kind") == "oculus_light_pool"]) < 1:
        error(errors, "expected public Rotunda oculus light-pool record")
    if len([detail for detail in rotunda_details if detail.get("kind") == "statue_pedestal_base"]) < 7:
        error(errors, "expected at least 7 public Rotunda statue pedestal records")
    if len([detail for detail in rotunda_details if detail.get("kind") == "statue_pedestal_plaque"]) < 7:
        error(errors, "expected at least 7 public Rotunda statue pedestal plaque records")
    for detail in rotunda_details:
        if detail.get("location") != "Rotunda":
            error(errors, f"Rotunda detail {detail.get('name', '<unknown>')} has invalid location")
            break
        if not is_vec3(detail.get("center_m")):
            error(errors, f"Rotunda detail {detail.get('name', '<unknown>')} has invalid center_m")
            break
        public_accuracy = detail.get("public_accuracy", "").lower()
        assignment = detail.get("assignment", "").lower()
        if "public" not in public_accuracy or "public visual" not in assignment or "security feature" not in assignment:
            error(errors, f"Rotunda detail {detail.get('name', '<unknown>')} lacks public/non-operational boundary")
            break

    ceiling_details = interior.get("ceiling_details", [])
    ceiling_detail_kinds = {detail.get("kind") for detail in ceiling_details}
    summary["ceiling_details"] = len(ceiling_details)
    summary["ceiling_detail_kinds"] = len(ceiling_detail_kinds)
    if len(ceiling_details) < 770:
        error(errors, f"expected at least 770 public ceiling detail records, got {len(ceiling_details)}")
    missing_ceiling_kinds = sorted(REQUIRED_CEILING_DETAIL_KINDS - ceiling_detail_kinds)
    if missing_ceiling_kinds:
        error(errors, f"missing public ceiling detail kinds: {', '.join(missing_ceiling_kinds)}")
    if len([detail for detail in ceiling_details if detail.get("kind") == "coffer_panel"]) < 120:
        error(errors, "expected at least 120 public coffer-panel records")
    if len([detail for detail in ceiling_details if detail.get("kind") == "crown_molding"]) < 40:
        error(errors, "expected at least 40 public crown-molding records")
    if len([detail for detail in ceiling_details if detail.get("kind") == "ceiling_grid_beam"]) < 50:
        error(errors, "expected at least 50 public ceiling grid beam records")
    if len([detail for detail in ceiling_details if detail.get("kind") == "ceiling_medallion"]) < 30:
        error(errors, "expected at least 30 public ceiling medallion records")
    if len([detail for detail in ceiling_details if detail.get("kind") == "light_canopy"]) < 30:
        error(errors, "expected at least 30 public light canopy records")
    if len([detail for detail in ceiling_details if detail.get("kind") == "light_fixture_trim_ring"]) < 30:
        error(errors, "expected at least 30 public light fixture trim ring records")
    if len([detail for detail in ceiling_details if detail.get("kind") == "light_fixture_glass_dome"]) < 30:
        error(errors, "expected at least 30 public light fixture glass dome records")
    if len([detail for detail in ceiling_details if detail.get("kind") == "ceiling_vent_grille"]) < 40:
        error(errors, "expected at least 40 public ceiling vent grille records")
    if len([detail for detail in ceiling_details if detail.get("kind") == "ceiling_material_variation_panel"]) < 40:
        error(errors, "expected at least 40 public ceiling material-variation panel records")
    if len([detail for detail in ceiling_details if detail.get("kind") == "beveled_ceiling_trim_profile"]) < 220:
        error(errors, "expected at least 220 public beveled ceiling trim-profile records")
    if len([detail for detail in ceiling_details if detail.get("kind") == "coffer_recess_shadow"]) < 120:
        error(errors, "expected at least 120 public coffer recess-shadow records")
    for detail in ceiling_details:
        if not detail.get("room"):
            error(errors, f"ceiling detail {detail.get('name', '<unknown>')} is missing room")
            break
        if not is_vec3(detail.get("center_m")):
            error(errors, f"ceiling detail {detail.get('name', '<unknown>')} has invalid center_m")
            break
        public_accuracy = detail.get("public_accuracy", "").lower()
        assignment = detail.get("assignment", "").lower()
        if "public" not in public_accuracy or "public visual" not in assignment or "security feature" not in assignment:
            error(errors, f"ceiling detail {detail.get('name', '<unknown>')} lacks public/non-operational boundary")
            break

    floor_details = interior.get("floor_details", [])
    floor_detail_kinds = {detail.get("kind") for detail in floor_details}
    summary["floor_details"] = len(floor_details)
    summary["floor_detail_kinds"] = len(floor_detail_kinds)
    if len(floor_details) < 347:
        error(errors, f"expected at least 347 public floor detail records, got {len(floor_details)}")
    missing_floor_kinds = sorted(REQUIRED_FLOOR_DETAIL_KINDS - floor_detail_kinds)
    if missing_floor_kinds:
        error(errors, f"missing public floor detail kinds: {', '.join(missing_floor_kinds)}")
    if len([detail for detail in floor_details if detail.get("kind") == "floor_border_strip"]) < 28:
        error(errors, "expected at least 28 public floor border records")
    if len([detail for detail in floor_details if detail.get("kind") == "marble_tile_joint"]) < 70:
        error(errors, "expected at least 70 public marble tile joint records")
    if len([detail for detail in floor_details if detail.get("kind") == "marble_vein_decal"]) < 52:
        error(errors, "expected at least 52 public marble vein decal records")
    if len([detail for detail in floor_details if detail.get("kind") == "carpet_border_strip"]) < 16:
        error(errors, "expected at least 16 public carpet border records")
    if len([detail for detail in floor_details if detail.get("kind") == "carpet_pile_variation_decal"]) < 24:
        error(errors, "expected at least 24 public carpet pile-variation decal records")
    if len([detail for detail in floor_details if detail.get("kind") == "public_threshold_slab"]) < 8:
        error(errors, "expected at least 8 public threshold slab records")
    if len([detail for detail in floor_details if detail.get("kind") == "threshold_tarnish_decal"]) < 16:
        error(errors, "expected at least 16 public threshold tarnish decal records")
    if len([detail for detail in floor_details if detail.get("kind") == "floor_medallion"]) < 10:
        error(errors, "expected at least 10 public floor medallion records")
    if len([detail for detail in floor_details if detail.get("kind") == "floor_wear_band"]) < 10:
        error(errors, "expected at least 10 public floor wear band records")
    if len([detail for detail in floor_details if detail.get("kind") == "floor_wear_scuff_patch"]) < 24:
        error(errors, "expected at least 24 public floor wear scuff patch records")
    if len([detail for detail in floor_details if detail.get("kind") == "public_room_outline_inlay"]) < 7:
        error(errors, "expected at least 7 public room outline inlay records")
    if len([detail for detail in floor_details if detail.get("kind") == "public_room_axis_inlay"]) < 10:
        error(errors, "expected at least 10 public room axis inlay records")
    if len([detail for detail in floor_details if detail.get("kind") == "public_column_footprint_marker"]) < 44:
        error(errors, "expected at least 44 public column footprint marker records")
    for detail in floor_details:
        if not detail.get("area"):
            error(errors, f"floor detail {detail.get('name', '<unknown>')} is missing area")
            break
        if not is_vec3(detail.get("center_m")):
            error(errors, f"floor detail {detail.get('name', '<unknown>')} has invalid center_m")
            break
        public_accuracy = detail.get("public_accuracy", "").lower()
        assignment = detail.get("assignment", "").lower()
        if "public" not in public_accuracy or "public visual" not in assignment or "security feature" not in assignment:
            error(errors, f"floor detail {detail.get('name', '<unknown>')} lacks public/non-operational boundary")
            break

    surface_aging_details = interior.get("surface_aging_details", [])
    surface_aging_detail_kinds = {detail.get("kind") for detail in surface_aging_details}
    summary["surface_aging_details"] = len(surface_aging_details)
    summary["surface_aging_detail_kinds"] = len(surface_aging_detail_kinds)
    if len(surface_aging_details) < 190:
        error(errors, f"expected at least 190 public surface-aging detail records, got {len(surface_aging_details)}")
    missing_surface_aging_kinds = sorted(REQUIRED_SURFACE_AGING_DETAIL_KINDS - surface_aging_detail_kinds)
    if missing_surface_aging_kinds:
        error(errors, f"missing public surface-aging detail kinds: {', '.join(missing_surface_aging_kinds)}")
    if len([detail for detail in surface_aging_details if detail.get("kind") == "baseboard_dust_shadow"]) < 40:
        error(errors, "expected at least 40 public baseboard dust-shadow records")
    if len([detail for detail in surface_aging_details if detail.get("kind") == "wall_corner_grime_streak"]) < 40:
        error(errors, "expected at least 40 public wall corner grime-streak records")
    if len([detail for detail in surface_aging_details if detail.get("kind") == "threshold_dirt_track"]) < 16:
        error(errors, "expected at least 16 public threshold dirt-track records")
    if len([detail for detail in surface_aging_details if detail.get("kind") == "desk_edge_wear_patch"]) < 25:
        error(errors, "expected at least 25 public desk edge wear-patch records")
    if len([detail for detail in surface_aging_details if detail.get("kind") == "chair_leather_scuff_patch"]) < 25:
        error(errors, "expected at least 25 public chair leather scuff-patch records")
    if len([detail for detail in surface_aging_details if detail.get("kind") == "gallery_seat_rub_shadow"]) < 20:
        error(errors, "expected at least 20 public gallery seat rub-shadow records")
    if len([detail for detail in surface_aging_details if detail.get("kind") == "brass_tarnish_patch"]) < 7:
        error(errors, "expected at least 7 public brass tarnish-patch records")
    for detail in surface_aging_details:
        if not detail.get("area"):
            error(errors, f"surface-aging detail {detail.get('name', '<unknown>')} is missing area")
            break
        if not is_vec3(detail.get("center_m")):
            error(errors, f"surface-aging detail {detail.get('name', '<unknown>')} has invalid center_m")
            break
        public_accuracy = detail.get("public_accuracy", "").lower()
        assignment = detail.get("assignment", "").lower()
        if (
            "public" not in public_accuracy
            or "public visual" not in assignment
            or "security feature" not in assignment
            or "operational" not in assignment
        ):
            error(errors, f"surface-aging detail {detail.get('name', '<unknown>')} lacks public/non-operational boundary")
            break

    joint_session = interior.get("joint_session", [])
    joint_names = {item.get("name") for item in joint_session}
    summary["joint_session_records"] = len(joint_session)
    missing_joint = sorted(REQUIRED_JOINT_SESSION - joint_names)
    if missing_joint:
        error(errors, f"missing joint-session visual records: {', '.join(missing_joint)}")

    public_art = interior.get("public_art", [])
    public_art_types = {record.get("type") for record in public_art}
    light_fixtures = interior.get("light_fixtures", [])
    light_fixture_details = interior.get("light_fixture_details", [])
    light_fixture_detail_kinds = {record.get("kind") for record in light_fixture_details}
    wall_treatments = interior.get("wall_treatments", [])
    summary["public_art"] = len(public_art)
    summary["public_art_types"] = len(public_art_types)
    summary["light_fixtures"] = len(light_fixtures)
    summary["light_fixture_details"] = len(light_fixture_details)
    summary["light_fixture_detail_kinds"] = len(light_fixture_detail_kinds)
    summary["wall_treatments"] = len(wall_treatments)
    if len(public_art) < 403:
        error(errors, f"expected at least 403 public-art visuals, got {len(public_art)}")
    missing_art_types = sorted(REQUIRED_PUBLIC_ART_TYPES - public_art_types)
    if missing_art_types:
        error(errors, f"missing public-art visual types: {', '.join(missing_art_types)}")
    if len([record for record in public_art if record.get("type") == "statue"]) < 35:
        error(errors, "expected at least 35 public statue visual records")
    if len([record for record in public_art if record.get("type") == "statue_plinth_detail"]) < 35:
        error(errors, "expected at least 35 public statue plinth-detail records")
    if len([record for record in public_art if record.get("type") == "statue_torso_silhouette"]) < 35:
        error(errors, "expected at least 35 public statue torso-silhouette records")
    if len([record for record in public_art if record.get("type") == "statue_head_silhouette"]) < 35:
        error(errors, "expected at least 35 public statue head-silhouette records")
    if len([record for record in public_art if record.get("type") == "statue_public_plaque"]) < 35:
        error(errors, "expected at least 35 public statue plaque records")
    if len([record for record in public_art if record.get("type") == "historical_painting_panel"]) < 8:
        error(errors, "expected at least 8 Rotunda historical painting panel records")
    if len([record for record in public_art if record.get("type") == "historical_painting_title_plaque"]) < 8:
        error(errors, "expected at least 8 Rotunda historical painting title-plaque records")
    rotunda_painting_titles = {
        record.get("title")
        for record in public_art
        if record.get("type") == "historical_painting_panel" and record.get("location") == "Rotunda"
    }
    missing_rotunda_paintings = sorted(EXPECTED_ROTUNDA_HISTORICAL_PAINTINGS - rotunda_painting_titles)
    if missing_rotunda_paintings:
        error(errors, f"missing named Rotunda historical paintings: {', '.join(missing_rotunda_paintings)}")
    if len([record for record in public_art if record.get("type") == "rotunda_frieze_relief_panel"]) < 16:
        error(errors, "expected at least 16 Rotunda frieze relief panel records")
    if len([record for record in public_art if record.get("type") == "portrait_panel"]) < 18:
        error(errors, "expected at least 18 public portrait panel records")
    if len([record for record in public_art if record.get("type") == "art_frame_inner_bevel"]) < 56:
        error(errors, "expected at least 56 public art inner-frame bevel records")
    if len([record for record in public_art if record.get("type") == "art_canvas_tone_patch"]) < 56:
        error(errors, "expected at least 56 public art canvas tone-patch records")
    if len([record for record in public_art if record.get("type") == "art_label_plaque"]) < 56:
        error(errors, "expected at least 56 public art label-plaque records")
    if len(light_fixtures) < 63:
        error(errors, f"expected at least 63 public light fixtures, got {len(light_fixtures)}")
    if len(light_fixture_details) < 380:
        error(errors, f"expected at least 380 public light fixture detail records, got {len(light_fixture_details)}")
    missing_light_fixture_detail_kinds = sorted(REQUIRED_LIGHT_FIXTURE_DETAIL_KINDS - light_fixture_detail_kinds)
    if missing_light_fixture_detail_kinds:
        error(errors, f"missing public light fixture detail kinds: {', '.join(missing_light_fixture_detail_kinds)}")
    if len([record for record in light_fixture_details if record.get("kind") == "pendant_canopy_detail"]) < 28:
        error(errors, "expected at least 28 public pendant canopy detail records")
    if len([record for record in light_fixture_details if record.get("kind") == "pendant_glass_shade_detail"]) < 28:
        error(errors, "expected at least 28 public pendant glass-shade detail records")
    if len([record for record in light_fixture_details if record.get("kind") == "sconce_backplate_detail"]) < 34:
        error(errors, "expected at least 34 public sconce backplate detail records")
    if len([record for record in light_fixture_details if record.get("kind") == "sconce_glass_shade_detail"]) < 34:
        error(errors, "expected at least 34 public sconce glass-shade detail records")
    if len([record for record in light_fixture_details if record.get("kind") == "fixture_beveled_mount"]) < 63:
        error(errors, "expected at least 63 public fixture beveled-mount records")
    if len([record for record in light_fixture_details if record.get("kind") == "fixture_glass_trim_ring"]) < 63:
        error(errors, "expected at least 63 public fixture glass trim-ring records")
    if len([record for record in light_fixture_details if record.get("kind") == "fixture_glass_shade_rib"]) < 68:
        error(errors, "expected at least 68 public fixture glass shade-rib records")
    if len([record for record in light_fixture_details if record.get("kind") == "fixture_finial_detail"]) < 63:
        error(errors, "expected at least 63 public fixture finial-detail records")
    if len(wall_treatments) < 10:
        error(errors, f"expected at least 10 wall-treatment records, got {len(wall_treatments)}")
    for record in public_art[:5] + light_fixtures[:5] + light_fixture_details[:5] + wall_treatments[:5]:
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
    summary = {
        "manifest_materials": 0,
        "missing_manifest_materials": 0,
        "extra_manifest_materials": 0,
        "clear_coat_materials": 0,
    }
    if not MATERIAL_MANIFEST_PATH.exists():
        error(errors, f"missing Unreal material realism manifest: {MATERIAL_MANIFEST_PATH}")
        return summary

    manifest = json.loads(MATERIAL_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest_materials = set(manifest)
    missing = sorted(materials - manifest_materials)
    extra = sorted(manifest_materials - materials)
    clear_coat_materials = [name for name, spec in manifest.items() if spec.get("clear_coat") is not None]
    summary["manifest_materials"] = len(manifest_materials)
    summary["missing_manifest_materials"] = len(missing)
    summary["extra_manifest_materials"] = len(extra)
    summary["clear_coat_materials"] = len(clear_coat_materials)
    if missing:
        error(errors, f"material realism manifest missing MTL materials: {', '.join(missing)}")
    if extra:
        error(errors, f"material realism manifest has materials not in MTL: {', '.join(extra)}")
    if len(clear_coat_materials) < 20:
        error(errors, f"expected at least 20 clear-coat material specs, got {len(clear_coat_materials)}")

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
        clear_coat = spec.get("clear_coat")
        if clear_coat is not None and (not is_number(clear_coat) or not (0.0 <= float(clear_coat) <= 1.0)):
            error(errors, f"material {name} has invalid clear_coat")
            break
        clear_coat_roughness = spec.get("clear_coat_roughness")
        if clear_coat_roughness is not None and (
            not is_number(clear_coat_roughness) or not (0.0 <= float(clear_coat_roughness) <= 1.0)
        ):
            error(errors, f"material {name} has invalid clear_coat_roughness")
            break
    return summary


def validate_texture_manifest(materials: set[str], errors: list[str]) -> dict[str, Any]:
    summary = {
        "texture_sets": 0,
        "texture_material_bindings": 0,
        "texture_files": 0,
        "texture_styles": 0,
        "photoreal_texture_features": 0,
        "min_texture_size_px": None,
        "expected_min_texture_size_px": MIN_TEXTURE_SIZE_PX,
    }
    if not TEXTURE_MANIFEST_PATH.exists():
        error(errors, f"missing material texture manifest: {TEXTURE_MANIFEST_PATH}")
        return summary
    manifest = json.loads(TEXTURE_MANIFEST_PATH.read_text(encoding="utf-8"))
    sets = manifest.get("sets", {})
    bindings = manifest.get("materials", {})
    styles = {spec.get("style") for spec in sets.values() if isinstance(spec, dict)}
    photoreal_features_raw = manifest.get("photoreal_readiness_features", [])
    photoreal_features = set(photoreal_features_raw if isinstance(photoreal_features_raw, list) else [])
    summary["texture_sets"] = len(sets)
    summary["texture_material_bindings"] = len(bindings)
    summary["texture_styles"] = len(styles)
    summary["photoreal_texture_features"] = len(photoreal_features)
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
        for key in ("basecolor", "normal", "roughness", "ambient_occlusion"):
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
    missing_styles = sorted(REQUIRED_TEXTURE_STYLES - styles)
    if missing_styles:
        error(errors, f"texture manifest missing required realism styles: {', '.join(missing_styles)}")
    missing_photoreal_features = sorted(REQUIRED_PHOTOREAL_TEXTURE_FEATURES - photoreal_features)
    if missing_photoreal_features:
        error(errors, f"texture manifest missing photoreal-readiness features: {', '.join(missing_photoreal_features)}")
    return summary


def infer_unreal_collision_proxy_group(proxy: dict[str, Any]) -> str:
    explicit_group = proxy.get("group")
    if explicit_group:
        return str(explicit_group)
    label = str(proxy.get("label", "")).lower()
    purpose = str(proxy.get("purpose", "")).lower()
    if "road" in label or "road" in purpose:
        return "public_exterior_road_surface"
    if "sidewalk" in label or "sidewalk" in purpose:
        return "public_exterior_sidewalk_surface"
    if "bike" in label or "bike" in purpose:
        return "public_bike_lane_surface"
    if any(token in label for token in ["plaza", "approach", "grounds", "axial", "walk"]):
        return "public_exterior_walk_surface"
    if any(token in label for token in ["rotunda", "chamber", "gallery", "office", "support", "connector", "crypt", "statuary", "senate", "house"]):
        return "public_interior_surface"
    return "public_first_person_surface"


def literal_assignment(tree: ast.AST, name: str) -> Any:
    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            try:
                return ast.literal_eval(node.value)
            except Exception:
                return None
    return None


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
        "material_markers": 0,
        "environment_markers": 0,
        "inspection_markers": 0,
        "collision_proxy_specs": 0,
        "collision_proxy_groups": 0,
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
    attribute_names = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    name_tokens = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    marker_tokens = string_literals | attribute_names
    functions = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    collision_proxy_specs_raw = literal_assignment(tree, "FIRST_PERSON_COLLISION_PROXIES")
    collision_proxy_specs = collision_proxy_specs_raw if isinstance(collision_proxy_specs_raw, list) else []
    collision_proxy_groups = {
        infer_unreal_collision_proxy_group(proxy)
        for proxy in collision_proxy_specs
        if isinstance(proxy, dict)
    }
    calls: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            calls.add(node.func.attr)
    inspection_tokens = marker_tokens | name_tokens | functions | calls

    missing_meshes = sorted(EXPECTED_UNREAL_MESH_BASENAMES - string_literals)
    missing_destinations = sorted(EXPECTED_UNREAL_DESTINATIONS - string_literals)
    missing_functions = sorted(REQUIRED_UNREAL_FUNCTIONS - functions)
    missing_calls = sorted(REQUIRED_UNREAL_CALLS - calls)
    missing_report_keys = sorted(REQUIRED_UNREAL_REPORT_KEYS - string_literals)
    missing_label_categories = sorted(REQUIRED_UNREAL_LABEL_CATEGORIES - string_literals)
    missing_outliner_folders = sorted(REQUIRED_UNREAL_OUTLINER_FOLDERS - string_literals)
    missing_first_person_markers = sorted(REQUIRED_UNREAL_FIRST_PERSON_MARKERS - string_literals)
    missing_collision_proxy_groups = sorted(REQUIRED_UNREAL_COLLISION_PROXY_GROUPS - collision_proxy_groups)
    missing_material_markers = sorted(REQUIRED_UNREAL_MATERIAL_MARKERS - inspection_tokens)
    missing_environment_markers = sorted(REQUIRED_UNREAL_ENVIRONMENT_MARKERS - marker_tokens)
    missing_inspection_markers = sorted(REQUIRED_UNREAL_INSPECTION_MARKERS - inspection_tokens)

    summary["mesh_files"] = len(EXPECTED_UNREAL_MESH_BASENAMES) - len(missing_meshes)
    summary["destination_paths"] = len(EXPECTED_UNREAL_DESTINATIONS) - len(missing_destinations)
    summary["required_functions"] = len(REQUIRED_UNREAL_FUNCTIONS) - len(missing_functions)
    summary["required_calls"] = len(REQUIRED_UNREAL_CALLS) - len(missing_calls)
    summary["report_keys"] = len(REQUIRED_UNREAL_REPORT_KEYS) - len(missing_report_keys)
    summary["label_categories"] = len(REQUIRED_UNREAL_LABEL_CATEGORIES) - len(missing_label_categories)
    summary["outliner_folders"] = len(REQUIRED_UNREAL_OUTLINER_FOLDERS) - len(missing_outliner_folders)
    summary["first_person_markers"] = len(REQUIRED_UNREAL_FIRST_PERSON_MARKERS) - len(missing_first_person_markers)
    summary["collision_proxy_specs"] = len(collision_proxy_specs)
    summary["collision_proxy_groups"] = len(collision_proxy_groups)
    summary["material_markers"] = len(REQUIRED_UNREAL_MATERIAL_MARKERS) - len(missing_material_markers)
    summary["environment_markers"] = len(REQUIRED_UNREAL_ENVIRONMENT_MARKERS) - len(missing_environment_markers)
    summary["inspection_markers"] = len(REQUIRED_UNREAL_INSPECTION_MARKERS) - len(missing_inspection_markers)
    summary["missing"] = {
        "mesh_files": missing_meshes,
        "destination_paths": missing_destinations,
        "required_functions": missing_functions,
        "required_calls": missing_calls,
        "report_keys": missing_report_keys,
        "label_categories": missing_label_categories,
        "outliner_folders": missing_outliner_folders,
        "first_person_markers": missing_first_person_markers,
        "collision_proxy_groups": missing_collision_proxy_groups,
        "material_markers": missing_material_markers,
        "environment_markers": missing_environment_markers,
        "inspection_markers": missing_inspection_markers,
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
    if len(collision_proxy_specs) < MIN_UNREAL_COLLISION_PROXY_SPECS:
        error(errors, f"Unreal importer expected at least {MIN_UNREAL_COLLISION_PROXY_SPECS} first-person collision proxy specs, got {len(collision_proxy_specs)}")
    if missing_collision_proxy_groups:
        error(errors, f"Unreal importer missing first-person collision proxy groups: {', '.join(missing_collision_proxy_groups)}")
    if missing_material_markers:
        error(errors, f"Unreal importer missing material setup markers: {', '.join(missing_material_markers)}")
    if missing_environment_markers:
        error(errors, f"Unreal importer missing environment setup markers: {', '.join(missing_environment_markers)}")
    if missing_inspection_markers:
        error(errors, f"Unreal importer missing interior inspection markers: {', '.join(missing_inspection_markers)}")

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


def validate_viewer_contract(errors: list[str]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "path": "viewer.html",
        "required_markers": 0,
        "missing": [],
    }
    if not VIEWER_PATH.exists():
        error(errors, f"missing local OBJ viewer: {VIEWER_PATH}")
        summary["missing"] = sorted(REQUIRED_VIEWER_MARKERS)
        return summary

    text = VIEWER_PATH.read_text(encoding="utf-8")
    missing = sorted(marker for marker in REQUIRED_VIEWER_MARKERS if marker not in text)
    summary["required_markers"] = len(REQUIRED_VIEWER_MARKERS) - len(missing)
    summary["missing"] = missing
    if missing:
        error(errors, f"viewer missing office-detail inspection markers: {', '.join(missing)}")
    return summary


def validate_landmark_height_contract(metadata: dict[str, Any], mesh_stats: list[dict[str, Any]], errors: list[str]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "mesh": LANDMARK_MESH_REL,
        "public_height_target_m": CAPITOL_PUBLIC_HEIGHT_TARGET_M,
        "max_z_m": None,
        "tolerance_m": LANDMARK_HEIGHT_TOLERANCE_M,
    }
    profile = metadata.get("landmark", {}).get("height_profile", {})
    declared_target = profile.get("public_height_target_m")
    if not is_number(declared_target):
        error(errors, "landmark.height_profile.public_height_target_m is missing or non-numeric")
    elif abs(float(declared_target) - CAPITOL_PUBLIC_HEIGHT_TARGET_M) > 0.05:
        error(
            errors,
            f"landmark public height target expected {CAPITOL_PUBLIC_HEIGHT_TARGET_M:.2f}m, got {float(declared_target):.2f}m",
        )
    summary["public_height_target_m"] = round(float(declared_target), 2) if is_number(declared_target) else CAPITOL_PUBLIC_HEIGHT_TARGET_M

    landmark_mesh = next((mesh for mesh in mesh_stats if mesh.get("path") == LANDMARK_MESH_REL), None)
    if landmark_mesh is None:
        error(errors, f"missing landmark mesh stats for {LANDMARK_MESH_REL}")
        return summary

    bbox = landmark_mesh.get("bbox_cm")
    if not isinstance(bbox, dict) or not isinstance(bbox.get("max"), list) or len(bbox["max"]) < 3:
        error(errors, f"{LANDMARK_MESH_REL} missing bounding-box stats")
        return summary

    max_z_m = float(bbox["max"][2]) / 100.0
    summary["max_z_m"] = round(max_z_m, 3)
    target = float(summary["public_height_target_m"])
    if abs(max_z_m - target) > LANDMARK_HEIGHT_TOLERANCE_M:
        error(errors, f"{LANDMARK_MESH_REL} max Z {max_z_m:.2f}m does not match public target {target:.2f}m")
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
    viewer_summary = validate_viewer_contract(errors)
    mesh_stats = [parse_obj(ROOT / rel, materials, errors) for rel in metadata.get("meshes", [])]
    landmark_height_summary = validate_landmark_height_contract(metadata, mesh_stats, errors)

    report = {
        "ok": not errors,
        "root": str(ROOT),
        "metadata": metadata_summary,
        "materials": material_summary,
        "textures": texture_summary,
        "unreal_importer": unreal_importer_summary,
        "unreal_project_config": unreal_project_config_summary,
        "viewer": viewer_summary,
        "landmark_height": landmark_height_summary,
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
    print(f"Office details: {metadata_summary.get('office_details', 0):,}")
    print(f"Chamber details: {metadata_summary.get('chamber_details', 0):,}")
    print(f"Circulation details: {metadata_summary.get('circulation_details', 0):,}")
    print(f"Signage details: {metadata_summary.get('signage_details', 0):,}")
    print(f"Door details: {metadata_summary.get('door_details', 0):,}")
    print(f"Furnishing details: {metadata_summary.get('furnishing_details', 0):,}")
    print(f"Rotunda details: {metadata_summary.get('rotunda_details', 0):,}")
    print(f"Ceiling details: {metadata_summary.get('ceiling_details', 0):,}")
    print(f"Floor details: {metadata_summary.get('floor_details', 0):,}")
    print(f"Surface aging details: {metadata_summary.get('surface_aging_details', 0):,}")
    print(f"Public art visuals: {metadata_summary.get('public_art', 0):,}")
    print(f"Light fixtures: {metadata_summary.get('light_fixtures', 0):,}")
    print(f"Light fixture details: {metadata_summary.get('light_fixture_details', 0):,}")
    print(f"Wall treatments: {metadata_summary.get('wall_treatments', 0):,}")
    print(f"Wall-finish details: {metadata_summary.get('wall_finish_details', 0):,}")
    print(f"Gameplay item props: {metadata_summary.get('gameplay_items', 0):,}")
    print(f"Flagpole banner visuals: {metadata_summary.get('flagpole_banners', 0):,}")
    print(f"Realism materials: {material_summary.get('manifest_materials', 0):,}")
    print(f"Texture sets: {texture_summary.get('texture_sets', 0):,}")
    print(f"Texture styles: {texture_summary.get('texture_styles', 0):,}")
    print(f"Photoreal texture features: {texture_summary.get('photoreal_texture_features', 0):,}")
    print(f"Viewpoints: {metadata_summary.get('viewpoints', 0):,}")
    print(f"Unreal importer meshes: {unreal_importer_summary.get('mesh_files', 0):,}")
    print(f"Unreal importer report keys: {unreal_importer_summary.get('report_keys', 0):,}")
    print(f"Unreal importer material markers: {unreal_importer_summary.get('material_markers', 0):,}")
    print(f"Unreal importer environment markers: {unreal_importer_summary.get('environment_markers', 0):,}")
    print(f"Unreal importer inspection markers: {unreal_importer_summary.get('inspection_markers', 0):,}")
    print(f"Unreal project config markers: {unreal_project_config_summary.get('required_markers', 0):,}")
    print(f"Viewer markers: {viewer_summary.get('required_markers', 0):,}")
    print(f"Landmark public height target: {landmark_height_summary.get('max_z_m')}m / {landmark_height_summary.get('public_height_target_m')}m")
    print(f"Wrote report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
