#!/usr/bin/env python3
"""Generate deterministic tileable texture maps for the Capitol Unreal package.

The texture pass is procedural so it can run locally without network access or
third-party image packages. Each texture set writes basecolor, normal, and
roughness PNGs plus a manifest consumed by the Unreal import script.
"""

from __future__ import annotations

import json
import math
import struct
import zlib
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
TEXTURE_DIR = ROOT / "generated" / "textures"
DATA_DIR = ROOT / "generated" / "data"
MANIFEST_PATH = DATA_DIR / "material_texture_manifest.json"
SIZE = 512


TEXTURE_SETS: dict[str, dict[str, Any]] = {
    "limestone": {"base": [0.82, 0.80, 0.72], "roughness": 0.78, "style": "stone", "normal_strength": 3.2},
    "limestone_light": {"base": [0.88, 0.86, 0.79], "roughness": 0.72, "style": "stone", "normal_strength": 2.8},
    "limestone_weathered": {"base": [0.62, 0.61, 0.58], "roughness": 0.86, "style": "stone", "normal_strength": 2.4},
    "dome_painted": {"base": [0.76, 0.76, 0.72], "roughness": 0.58, "style": "painted_metal", "normal_strength": 1.4},
    "step_stone": {"base": [0.50, 0.49, 0.46], "roughness": 0.90, "style": "worn_stone", "normal_strength": 4.0},
    "plaza_stone": {"base": [0.55, 0.53, 0.47], "roughness": 0.88, "style": "pavers", "normal_strength": 3.0},
    "asphalt": {"base": [0.035, 0.037, 0.040], "roughness": 0.94, "style": "asphalt", "normal_strength": 5.0},
    "road_paint_white": {"base": [0.88, 0.88, 0.82], "roughness": 0.76, "style": "worn_paint", "normal_strength": 1.5},
    "road_paint_yellow": {"base": [0.90, 0.68, 0.10], "roughness": 0.74, "style": "worn_paint", "normal_strength": 1.5},
    "concrete": {"base": [0.54, 0.54, 0.50], "roughness": 0.90, "style": "concrete", "normal_strength": 3.0},
    "curb_concrete": {"base": [0.68, 0.68, 0.64], "roughness": 0.88, "style": "concrete", "normal_strength": 2.4},
    "bike_lane_green": {"base": [0.035, 0.28, 0.13], "roughness": 0.78, "style": "worn_paint", "normal_strength": 1.8},
    "grass": {"base": [0.13, 0.26, 0.10], "roughness": 0.96, "style": "grass", "normal_strength": 4.0},
    "polished_wood": {"base": [0.24, 0.12, 0.045], "roughness": 0.46, "style": "wood", "normal_strength": 2.2},
    "dark_wood": {"base": [0.16, 0.075, 0.028], "roughness": 0.42, "style": "wood", "normal_strength": 2.0},
    "leather_dark": {"base": [0.045, 0.038, 0.030], "roughness": 0.44, "style": "leather", "normal_strength": 3.0},
    "brass": {"base": [0.76, 0.56, 0.18], "roughness": 0.34, "style": "brushed_metal", "normal_strength": 1.3},
    "rotunda_floor": {"base": [0.72, 0.62, 0.45], "roughness": 0.62, "style": "marble", "normal_strength": 2.0},
    "rotunda_wall": {"base": [0.84, 0.79, 0.69], "roughness": 0.70, "style": "marble", "normal_strength": 1.8},
    "house_carpet": {"base": [0.045, 0.075, 0.25], "roughness": 0.98, "style": "carpet", "normal_strength": 4.5},
    "senate_carpet": {"base": [0.30, 0.035, 0.035], "roughness": 0.98, "style": "carpet", "normal_strength": 4.5},
    "house_blue_fabric": {"base": [0.08, 0.16, 0.42], "roughness": 0.72, "style": "fabric", "normal_strength": 3.2},
    "senate_dark_fabric": {"base": [0.065, 0.055, 0.045], "roughness": 0.50, "style": "leather", "normal_strength": 2.4},
    "gallery_dark": {"base": [0.20, 0.23, 0.24], "roughness": 0.70, "style": "painted_metal", "normal_strength": 1.6},
    "office_floor": {"base": [0.40, 0.46, 0.54], "roughness": 0.76, "style": "concrete", "normal_strength": 1.8},
    "blue_marker": {"base": [0.075, 0.25, 0.78], "roughness": 0.60, "style": "worn_paint", "normal_strength": 1.2},
    "street_sign_green": {"base": [0.02, 0.18, 0.075], "roughness": 0.42, "style": "painted_metal", "normal_strength": 0.8},
    "glass_blue": {"base": [0.36, 0.58, 0.72], "roughness": 0.08, "style": "glass", "normal_strength": 0.4},
    "black_metal": {"base": [0.14, 0.15, 0.16], "roughness": 0.30, "style": "brushed_metal", "normal_strength": 1.0},
    "joint_zone": {"base": [0.35, 0.30, 0.22], "roughness": 0.76, "style": "fabric", "normal_strength": 2.0},
    "court_black": {"base": [0.13, 0.13, 0.13], "roughness": 0.70, "style": "fabric", "normal_strength": 1.8},
    "cabinet_blue": {"base": [0.055, 0.12, 0.26], "roughness": 0.72, "style": "fabric", "normal_strength": 1.8},
    "diplomatic_purple": {"base": [0.20, 0.12, 0.26], "roughness": 0.72, "style": "fabric", "normal_strength": 1.8},
    "press_green": {"base": [0.12, 0.15, 0.15], "roughness": 0.78, "style": "fabric", "normal_strength": 1.8},
    "statue_marble": {"base": [0.74, 0.70, 0.62], "roughness": 0.68, "style": "marble", "normal_strength": 1.9},
    "statue_bronze": {"base": [0.30, 0.20, 0.10], "roughness": 0.46, "style": "brushed_metal", "normal_strength": 1.4},
    "gilded_frame": {"base": [0.76, 0.54, 0.14], "roughness": 0.32, "style": "brushed_metal", "normal_strength": 1.2},
    "painting_canvas": {"base": [0.38, 0.24, 0.15], "roughness": 0.82, "style": "canvas", "normal_strength": 2.8},
    "portrait_canvas": {"base": [0.22, 0.16, 0.12], "roughness": 0.84, "style": "canvas", "normal_strength": 2.8},
    "warm_light_glass": {"base": [1.0, 0.78, 0.42], "roughness": 0.18, "style": "glass", "normal_strength": 0.3},
    "fixture_dark_metal": {"base": [0.16, 0.13, 0.09], "roughness": 0.36, "style": "brushed_metal", "normal_strength": 1.1},
}

MATERIAL_TEXTURE_BINDINGS = {
    "BuildingGeneric": "limestone_weathered",
    "BuildingCapitol": "limestone",
    "CapitolStone": "limestone",
    "CapitolDome": "dome_painted",
    "ColumnStone": "limestone_light",
    "StepStone": "step_stone",
    "GroundGrass": "grass",
    "PlazaStone": "plaza_stone",
    "RoadAsphalt": "asphalt",
    "LaneMarkingWhite": "road_paint_white",
    "LaneMarkingYellow": "road_paint_yellow",
    "SidewalkConcrete": "concrete",
    "CurbConcrete": "curb_concrete",
    "BikeLaneGreen": "bike_lane_green",
    "BikeLanePost": "road_paint_white",
    "CrosswalkWhite": "road_paint_white",
    "SignalMarker": "road_paint_yellow",
    "InteriorFloor": "rotunda_floor",
    "InteriorWall": "rotunda_wall",
    "InteriorTrim": "dark_wood",
    "HouseCarpet": "house_carpet",
    "SenateCarpet": "senate_carpet",
    "DeskWood": "polished_wood",
    "ChairLeather": "leather_dark",
    "BrassRail": "brass",
    "RotundaFloor": "rotunda_floor",
    "RotundaWall": "rotunda_wall",
    "HouseSeat": "house_blue_fabric",
    "HouseDesk": "polished_wood",
    "SenateDesk": "polished_wood",
    "SenateChair": "senate_dark_fabric",
    "PublicGallery": "gallery_dark",
    "OfficeZone": "office_floor",
    "MarkerBlue": "blue_marker",
    "StreetSignGreen": "street_sign_green",
    "DoorGlass": "glass_blue",
    "DoorMetal": "black_metal",
    "PresidentPodium": "dark_wood",
    "JointSessionZone": "joint_zone",
    "SupremeCourtZone": "court_black",
    "CabinetZone": "cabinet_blue",
    "DiplomaticZone": "diplomatic_purple",
    "PressZone": "press_green",
    "StatueMarble": "statue_marble",
    "StatueBronze": "statue_bronze",
    "ArtFrameGold": "gilded_frame",
    "PaintingCanvas": "painting_canvas",
    "PortraitCanvas": "portrait_canvas",
    "WarmLightGlass": "warm_light_glass",
    "LightFixtureMetal": "fixture_dark_metal",
}


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def write_png(path: Path, rgb: np.ndarray) -> None:
    array = np.clip(rgb, 0, 255).astype(np.uint8)
    height, width, channels = array.shape
    if channels != 3:
        raise ValueError(f"Expected RGB image, got {channels} channels")
    raw = b"".join(b"\x00" + array[row].tobytes() for row in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", header)
        + png_chunk(b"IDAT", zlib.compress(raw, 9))
        + png_chunk(b"IEND", b"")
    )


def tile_noise(size: int, seed: int, octaves: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    coords = np.linspace(0.0, math.tau, size, endpoint=False)
    x, y = np.meshgrid(coords, coords)
    field = np.zeros((size, size), dtype=np.float64)
    amplitude = 1.0
    total = 0.0
    for _ in range(octaves):
        fx = int(rng.integers(1, 11))
        fy = int(rng.integers(1, 11))
        phase_a = float(rng.random() * math.tau)
        phase_b = float(rng.random() * math.tau)
        field += amplitude * np.sin(fx * x + phase_a) * np.cos(fy * y + phase_b)
        field += amplitude * 0.55 * np.cos((fx + fy) * x - fy * y + phase_a * 0.7)
        total += amplitude * 1.55
        amplitude *= 0.55
    field /= max(total, 0.001)
    field = (field - field.min()) / max(float(field.max() - field.min()), 0.001)
    return field


def ridge_noise(size: int, seed: int) -> np.ndarray:
    n = tile_noise(size, seed, 8)
    return 1.0 - np.abs(n * 2.0 - 1.0)


def style_height(style: str, size: int, seed: int) -> np.ndarray:
    x = np.linspace(0.0, math.tau, size, endpoint=False)
    xx, yy = np.meshgrid(x, x)
    base = tile_noise(size, seed, 7)
    fine = tile_noise(size, seed + 17, 10)
    ridges = ridge_noise(size, seed + 31)

    if style == "asphalt":
        aggregate = (fine > 0.58).astype(np.float64) * 0.32
        return np.clip(base * 0.45 + aggregate + ridges * 0.20, 0.0, 1.0)
    if style == "concrete":
        hairline = (ridge_noise(size, seed + 7) > 0.955).astype(np.float64) * 0.38
        return np.clip(base * 0.45 + fine * 0.22 + hairline, 0.0, 1.0)
    if style == "grass":
        blades = (np.sin(xx * 34.0 + tile_noise(size, seed + 2, 3) * 4.0) + 1.0) * 0.16
        return np.clip(base * 0.45 + fine * 0.25 + blades, 0.0, 1.0)
    if style == "wood":
        grain = (np.sin(xx * 18.0 + tile_noise(size, seed + 4, 5) * 8.0) + 1.0) * 0.35
        long_variation = tile_noise(size, seed + 5, 4) * 0.35
        return np.clip(grain + long_variation + fine * 0.18, 0.0, 1.0)
    if style == "carpet":
        weave = (np.sin(xx * 88.0) + np.sin(yy * 82.0)) * 0.06 + 0.5
        return np.clip(weave + fine * 0.38, 0.0, 1.0)
    if style == "fabric":
        weave = (np.sin(xx * 52.0) * np.sin(yy * 52.0)) * 0.12 + 0.5
        return np.clip(weave + fine * 0.30, 0.0, 1.0)
    if style == "leather":
        pores = (fine > 0.72).astype(np.float64) * 0.28
        return np.clip(base * 0.50 + ridges * 0.20 + pores, 0.0, 1.0)
    if style == "brushed_metal":
        brush = (np.sin(xx * 60.0 + fine * 2.0) + 1.0) * 0.12
        return np.clip(base * 0.24 + brush, 0.0, 1.0)
    if style == "painted_metal":
        return np.clip(base * 0.28 + fine * 0.18, 0.0, 1.0)
    if style == "worn_paint":
        wear = (ridges > 0.82).astype(np.float64) * 0.42
        return np.clip(base * 0.22 + fine * 0.18 + wear, 0.0, 1.0)
    if style == "glass":
        return np.clip(base * 0.08 + fine * 0.05, 0.0, 1.0)
    if style == "marble":
        veins = np.sin(xx * 4.0 + yy * 3.0 + tile_noise(size, seed + 9, 5) * 8.0)
        veins = np.clip((veins + 1.0) * 0.5, 0.0, 1.0)
        return np.clip(base * 0.35 + (veins > 0.88).astype(np.float64) * 0.35, 0.0, 1.0)
    if style == "pavers":
        grid_x = (np.abs(np.sin(xx * 8.0)) < 0.045).astype(np.float64)
        grid_y = (np.abs(np.sin(yy * 8.0)) < 0.045).astype(np.float64)
        return np.clip(base * 0.30 + fine * 0.18 + (grid_x + grid_y) * 0.28, 0.0, 1.0)
    if style == "worn_stone":
        chips = (fine > 0.80).astype(np.float64) * 0.30
        return np.clip(base * 0.45 + ridges * 0.20 + chips, 0.0, 1.0)
    if style == "canvas":
        weave = (np.sin(xx * 70.0) + np.sin(yy * 74.0)) * 0.08 + 0.5
        brush = ridge_noise(size, seed + 12) * 0.24
        return np.clip(weave + brush + fine * 0.24, 0.0, 1.0)
    # stone
    flecks = (fine > 0.86).astype(np.float64) * 0.18
    return np.clip(base * 0.38 + ridges * 0.16 + flecks, 0.0, 1.0)


def normal_from_height(height: np.ndarray, strength: float) -> np.ndarray:
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * strength
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * strength
    nx = -dx
    ny = -dy
    nz = np.ones_like(height)
    length = np.sqrt(nx * nx + ny * ny + nz * nz)
    normal = np.stack([nx / length, ny / length, nz / length], axis=2)
    return ((normal * 0.5 + 0.5) * 255.0).astype(np.uint8)


def color_map(base_color: list[float], height: np.ndarray, style: str, seed: int) -> np.ndarray:
    base = np.array(base_color, dtype=np.float64).reshape(1, 1, 3)
    variation = (height - 0.5)[:, :, None]
    tint_noise = tile_noise(height.shape[0], seed + 101, 5)[:, :, None] - 0.5
    color = base * (1.0 + variation * 0.24 + tint_noise * 0.10)

    if style in {"asphalt", "leather", "brushed_metal"}:
        color *= 0.92 + variation * 0.18
    elif style in {"grass"}:
        yellow = np.array([0.08, 0.07, -0.04]).reshape(1, 1, 3)
        color += yellow * np.clip(tint_noise + 0.4, 0.0, 1.0)
    elif style in {"wood"}:
        color += np.array([0.05, 0.018, -0.012]).reshape(1, 1, 3) * np.sin(height[:, :, None] * math.tau * 2.0)
    elif style in {"marble"}:
        color += np.array([0.05, 0.045, 0.02]).reshape(1, 1, 3) * np.clip(height[:, :, None] - 0.62, 0.0, 1.0)

    return (np.clip(color, 0.0, 1.0) * 255.0).astype(np.uint8)


def roughness_map(base_roughness: float, height: np.ndarray, style: str) -> np.ndarray:
    roughness = base_roughness + (height - 0.5) * 0.16
    if style in {"glass", "brushed_metal"}:
        roughness = base_roughness + (height - 0.5) * 0.08
    if style in {"carpet", "grass"}:
        roughness = base_roughness + height * 0.04
    gray = np.clip(roughness, 0.0, 1.0) * 255.0
    return np.repeat(gray[:, :, None], 3, axis=2).astype(np.uint8)


def generate_set(name: str, spec: dict[str, Any]) -> dict[str, str]:
    seed = abs(hash(name)) % 1_000_000
    style = str(spec["style"])
    height = style_height(style, SIZE, seed)
    basecolor = color_map(spec["base"], height, style, seed)
    normal = normal_from_height(height, float(spec["normal_strength"]))
    roughness = roughness_map(float(spec["roughness"]), height, style)

    paths = {
        "basecolor": f"generated/textures/{name}_basecolor.png",
        "normal": f"generated/textures/{name}_normal.png",
        "roughness": f"generated/textures/{name}_roughness.png",
    }
    write_png(ROOT / paths["basecolor"], basecolor)
    write_png(ROOT / paths["normal"], normal)
    write_png(ROOT / paths["roughness"], roughness)
    return paths


def main() -> None:
    TEXTURE_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    sets: dict[str, Any] = {}
    for name, spec in sorted(TEXTURE_SETS.items()):
        texture_paths = generate_set(name, spec)
        sets[name] = {
            "style": spec["style"],
            "size_px": [SIZE, SIZE],
            "tileable": True,
            "basecolor": texture_paths["basecolor"],
            "normal": texture_paths["normal"],
            "roughness": texture_paths["roughness"],
        }

    manifest = {
        "package": "capitol_unreal_map",
        "texture_root": "generated/textures",
        "sets": sets,
        "materials": MATERIAL_TEXTURE_BINDINGS,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {len(sets)} texture sets to {TEXTURE_DIR}")
    print(f"Wrote manifest to {MANIFEST_PATH}")
    print(f"Material texture bindings: {len(MATERIAL_TEXTURE_BINDINGS)}")


if __name__ == "__main__":
    main()
