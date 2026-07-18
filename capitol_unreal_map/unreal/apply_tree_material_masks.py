import importlib
import json
import pathlib
import sys

import unreal


PROJECT_ROOT = pathlib.Path(r"C:\Users\ryan\Documents\Unreal\Ryan")
UNREAL_SCRIPTS = PROJECT_ROOT / "capitol_unreal_map" / "unreal"
RESULT_PATH = PROJECT_ROOT / "Saved" / "CodexTreeMaskResult.json"

if str(UNREAL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(UNREAL_SCRIPTS))

import import_capitol_map as capitol_map

importlib.reload(capitol_map)
manifest = capitol_map.load_material_manifest()
result = {}

for material_name in ("TreeTrunk", "TreeCanopy"):
    asset_path = capitol_map.material_asset_path(material_name)
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if not asset:
        result[material_name] = False
        unreal.log_error(f"[CapitolMap] Missing material: {asset_path}")
        continue

    capitol_map.configure_unreal_material(asset, manifest[material_name], {})
    result[material_name] = bool(
        unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
    )

RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
RESULT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
unreal.log(f"[CapitolMap] Tree material result: {result}")
