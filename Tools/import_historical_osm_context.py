"""Import only the Jan. 6, 2021 OSM context layers into /Game/Main.

Run from Unreal Editor with Tools > Execute Python Script. This intentionally
does not import or replace the Capitol landmark, public interiors, gameplay
props, generated texture library, cameras, labels, or environment setup.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import unreal


PROJECT_ROOT = Path(unreal.Paths.project_dir()).resolve()
PACKAGE_ROOT = PROJECT_ROOT / "capitol_unreal_map"
BASE_IMPORTER_PATH = PACKAGE_ROOT / "unreal" / "import_capitol_map.py"
REPORT_PATH = PROJECT_ROOT / "Saved" / "HistoricalOSMContextImport.json"

CONTEXT_MESHES = [
    "capitol_exterior_buildings.obj",
    "capitol_exterior_roads_bike_lanes_markers.obj",
]

DESTINATION_PATH = "/Game/HistoricalOSM/Generated"
TARGET_LEVEL = "/Game/Main"
ACTOR_PREFIX = "HistoricalOSM_"
ACTOR_FOLDER = "HistoricalOSM/Context"


def log(message: str) -> None:
    unreal.log(f"[HistoricalOSM] {message}")


def load_base_importer():
    spec = importlib.util.spec_from_file_location("capitol_base_importer", BASE_IMPORTER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load importer: {BASE_IMPORTER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_target_level() -> None:
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not subsystem.load_level(TARGET_LEVEL):
        raise RuntimeError(f"Could not load {TARGET_LEVEL}")


def remove_previous_context() -> int:
    removed = 0
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actor_subsystem.get_all_level_actors():
        if actor.get_actor_label().startswith(ACTOR_PREFIX):
            if actor_subsystem.destroy_actor(actor):
                removed += 1
    return removed


def import_context_assets(base) -> list[str]:
    base.MESH_FILES = list(CONTEXT_MESHES)
    base.DESTINATION_PATH = DESTINATION_PATH
    return base.import_meshes()


def spawn_context_assets(base, asset_paths: list[str]) -> list[str]:
    spawned: list[str] = []
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for asset_path in asset_paths:
        base.configure_static_mesh(asset_path)
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not asset:
            log(f"WARNING: could not load {asset_path}")
            continue
        actor = actor_subsystem.spawn_actor_from_object(asset, unreal.Vector(0.0, 0.0, 0.0))
        if not actor:
            log(f"WARNING: could not spawn {asset_path}")
            continue
        actor.set_actor_label(f"{ACTOR_PREFIX}{Path(asset_path).name}")
        actor.set_folder_path(ACTOR_FOLDER)
        actor.tags = ["HistoricalOSM", "Jan6_2021_Context"]
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        base.configure_static_mesh_component(component)
        spawned.append(actor.get_actor_label())
    return spawned


def save_level() -> None:
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not subsystem.save_current_level():
        raise RuntimeError("Failed to save /Game/Main")


def main() -> None:
    if not BASE_IMPORTER_PATH.exists():
        raise RuntimeError(f"Missing base importer: {BASE_IMPORTER_PATH}")
    load_target_level()
    removed = remove_previous_context()
    base = load_base_importer()
    imported = import_context_assets(base)
    spawned = spawn_context_assets(base, imported)
    save_level()
    report = {
        "target_level": TARGET_LEVEL,
        "source_snapshot": "OpenStreetMap/Overpass 2021-01-06T17:00:00Z",
        "source_meshes": CONTEXT_MESHES,
        "imported_assets": imported,
        "spawned_actors": spawned,
        "removed_previous_actors": removed,
        "excluded": [
            "Capitol landmark replacement",
            "public interior schematic",
            "gameplay props",
            "generated 4K texture library",
            "labels and cameras",
            "environment and lighting overrides",
        ],
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log(f"Done. Imported {len(imported)} assets and spawned {len(spawned)} context actors in {TARGET_LEVEL}.")


if __name__ == "__main__":
    main()
