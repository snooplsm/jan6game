#!/usr/bin/env python3
"""Generate deterministic tileable texture maps for the Capitol Unreal package.

The texture pass is procedural so it can run locally without network access or
third-party image packages. Each texture set writes basecolor, normal,
roughness, and ambient-occlusion PNGs plus a manifest consumed by the Unreal
import script.
"""

from __future__ import annotations

import json
import hashlib
import math
import os
import struct
import zlib
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
TEXTURE_DIR = ROOT / "generated" / "textures"
DATA_DIR = ROOT / "generated" / "data"
MANIFEST_PATH = DATA_DIR / "material_texture_manifest.json"
SIZE = int(os.environ.get("CAPITOL_TEXTURE_SIZE", "4096"))
PNG_COMPRESSION_LEVEL = int(os.environ.get("CAPITOL_TEXTURE_COMPRESSION", "6"))


TEXTURE_SETS: dict[str, dict[str, Any]] = {
    "limestone": {"base": [0.82, 0.80, 0.72], "roughness": 0.78, "style": "ashlar_limestone", "normal_strength": 3.4},
    "limestone_light": {"base": [0.88, 0.86, 0.79], "roughness": 0.72, "style": "ashlar_limestone", "normal_strength": 3.0},
    "limestone_weathered": {"base": [0.62, 0.61, 0.58], "roughness": 0.86, "style": "weathered_ashlar_limestone", "normal_strength": 3.0},
    "dome_painted": {"base": [0.76, 0.76, 0.72], "roughness": 0.58, "style": "painted_dome_panels", "normal_strength": 1.8},
    "step_stone": {"base": [0.50, 0.49, 0.46], "roughness": 0.90, "style": "worn_stone", "normal_strength": 4.0},
    "plaza_stone": {"base": [0.55, 0.53, 0.47], "roughness": 0.88, "style": "pavers", "normal_strength": 3.0},
    "asphalt": {"base": [0.035, 0.037, 0.040], "roughness": 0.94, "style": "asphalt", "normal_strength": 5.0},
    "road_paint_white": {"base": [0.88, 0.88, 0.82], "roughness": 0.76, "style": "worn_paint", "normal_strength": 1.5},
    "road_paint_yellow": {"base": [0.90, 0.68, 0.10], "roughness": 0.74, "style": "worn_paint", "normal_strength": 1.5},
    "concrete": {"base": [0.54, 0.54, 0.50], "roughness": 0.90, "style": "concrete", "normal_strength": 3.0},
    "curb_concrete": {"base": [0.68, 0.68, 0.64], "roughness": 0.88, "style": "concrete", "normal_strength": 2.4},
    "bike_lane_green": {"base": [0.035, 0.28, 0.13], "roughness": 0.78, "style": "worn_paint", "normal_strength": 1.8},
    "grass": {"base": [0.13, 0.26, 0.10], "roughness": 0.96, "style": "grass", "normal_strength": 4.0},
    "polished_wood": {"base": [0.24, 0.12, 0.045], "roughness": 0.46, "style": "wood_planks", "normal_strength": 2.5},
    "dark_wood": {"base": [0.16, 0.075, 0.028], "roughness": 0.42, "style": "wood_planks", "normal_strength": 2.4},
    "leather_dark": {"base": [0.045, 0.038, 0.030], "roughness": 0.44, "style": "leather", "normal_strength": 3.0},
    "brass": {"base": [0.76, 0.56, 0.18], "roughness": 0.34, "style": "brushed_metal", "normal_strength": 1.3},
    "rotunda_floor": {"base": [0.72, 0.62, 0.45], "roughness": 0.58, "style": "marble_floor", "normal_strength": 2.4},
    "rotunda_wall": {"base": [0.84, 0.79, 0.69], "roughness": 0.66, "style": "marble_wall", "normal_strength": 2.0},
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
    "statue_marble": {"base": [0.74, 0.70, 0.62], "roughness": 0.68, "style": "marble_wall", "normal_strength": 1.9},
    "statue_bronze": {"base": [0.30, 0.20, 0.10], "roughness": 0.46, "style": "brushed_metal", "normal_strength": 1.4},
    "gilded_frame": {"base": [0.76, 0.54, 0.14], "roughness": 0.32, "style": "brushed_metal", "normal_strength": 1.2},
    "painting_canvas": {"base": [0.38, 0.24, 0.15], "roughness": 0.82, "style": "canvas", "normal_strength": 2.8},
    "portrait_canvas": {"base": [0.22, 0.16, 0.12], "roughness": 0.84, "style": "canvas", "normal_strength": 2.8},
    "warm_light_glass": {"base": [1.0, 0.78, 0.42], "roughness": 0.18, "style": "glass", "normal_strength": 0.3},
    "fixture_dark_metal": {"base": [0.16, 0.13, 0.09], "roughness": 0.36, "style": "brushed_metal", "normal_strength": 1.1},
    "brushed_steel": {"base": [0.70, 0.70, 0.66], "roughness": 0.34, "style": "brushed_metal", "normal_strength": 1.1},
    "cloth_red": {"base": [0.72, 0.06, 0.04], "roughness": 0.82, "style": "fabric", "normal_strength": 2.6},
}

MATERIAL_TEXTURE_BINDINGS = {
    "BuildingGeneric": "limestone_weathered",
    "BuildingCapitol": "limestone",
    "CapitolStone": "limestone",
    "CapitolDome": "dome_painted",
    "ColumnStone": "limestone_light",
    "StepStone": "step_stone",
    "StoneGrimeOverlay": "limestone_weathered",
    "GroundGrass": "grass",
    "PlazaStone": "plaza_stone",
    "RoadAsphalt": "asphalt",
    "RoadPatchAsphalt": "asphalt",
    "RoadCrackSealant": "asphalt",
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
    "FloorWear": "step_stone",
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
    "FacadeWindow": "glass_blue",
    "StreetLightPole": "black_metal",
    "StreetLightGlass": "warm_light_glass",
    "TrafficSignalHousing": "black_metal",
    "TrafficSignalRed": "warm_light_glass",
    "TrafficSignalYellow": "warm_light_glass",
    "TrafficSignalGreen": "warm_light_glass",
    "TreeTrunk": "dark_wood",
    "TreeCanopy": "grass",
    "PlanterStone": "plaza_stone",
    "BenchWood": "polished_wood",
    "BollardMetal": "black_metal",
    "GameplayPickupPad": "gallery_dark",
    "ItemWood": "polished_wood",
    "ItemMetal": "black_metal",
    "ItemGrip": "leather_dark",
    "ItemSprayCan": "road_paint_yellow",
    "ItemWarningOrange": "road_paint_yellow",
    "ItemOrganicBrown": "dark_wood",
    "ItemBlade": "brushed_steel",
    "ItemCloth": "cloth_red",
}

PHOTOREAL_TEXTURE_FEATURES = [
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
]


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
        + png_chunk(b"IDAT", zlib.compress(raw, PNG_COMPRESSION_LEVEL))
        + png_chunk(b"IEND", b"")
    )


def tile_noise(size: int, seed: int, octaves: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    coords = np.linspace(0.0, math.tau, size, endpoint=False, dtype=np.float32)
    x = coords.reshape(1, size)
    y = coords.reshape(size, 1)
    field = np.zeros((size, size), dtype=np.float32)
    amplitude = np.float32(1.0)
    total = np.float32(0.0)
    for _ in range(octaves):
        fx = int(rng.integers(1, 11))
        fy = int(rng.integers(1, 11))
        phase_a = np.float32(rng.random() * math.tau)
        phase_b = np.float32(rng.random() * math.tau)
        field += amplitude * np.sin(fx * x + phase_a) * np.cos(fy * y + phase_b)
        field += amplitude * np.float32(0.55) * np.cos((fx + fy) * x - fy * y + phase_a * np.float32(0.7))
        total += amplitude * np.float32(1.55)
        amplitude *= np.float32(0.55)
    field /= max(float(total), 0.001)
    field = (field - field.min()) / max(float(field.max() - field.min()), 0.001)
    return field.astype(np.float32, copy=False)


def ridge_noise(size: int, seed: int) -> np.ndarray:
    n = tile_noise(size, seed, 8)
    return 1.0 - np.abs(n * 2.0 - 1.0)


def band_mask(signal: np.ndarray, width: float) -> np.ndarray:
    return np.clip((width - np.abs(np.sin(signal))) / width, 0.0, 1.0).astype(np.float32, copy=False)


def threshold_soft(field: np.ndarray, threshold: float, softness: float) -> np.ndarray:
    return np.clip((field - threshold) / softness, 0.0, 1.0).astype(np.float32, copy=False)


def periodic_knot_field(xx: np.ndarray, yy: np.ndarray, seed: int) -> np.ndarray:
    phase_a = np.float32((seed % 19) / 19.0 * math.tau)
    phase_b = np.float32((seed % 31) / 31.0 * math.tau)
    dx = np.sin(xx * 2.0 + phase_a)
    dy = np.sin(yy * 3.0 + phase_b)
    return np.exp(-((dx * dx) / 0.035 + (dy * dy) / 0.055)).astype(np.float32, copy=False)


def photoreal_height_detail(height: np.ndarray, style: str, seed: int) -> np.ndarray:
    """Layer small-scale physical surface detail over the broad material pattern."""
    size = height.shape[0]
    x = np.linspace(0.0, math.tau, size, endpoint=False, dtype=np.float32)
    xx = x.reshape(1, size)
    yy = x.reshape(size, 1)
    micro = tile_noise(size, seed + 211, 11)
    speckle = tile_noise(size, seed + 229, 9)
    pinholes = threshold_soft(speckle, 0.82, 0.14)
    pores = threshold_soft(micro, 0.68, 0.22)
    scratch = band_mask(xx * 21.0 + yy * 4.0 + micro * 2.8, 0.018)
    hairline = band_mask(xx * 13.0 - yy * 9.0 + speckle * 4.0, 0.014)

    if style in {"ashlar_limestone", "weathered_ashlar_limestone", "worn_stone", "marble_wall", "marble_floor", "pavers"}:
        mineral_flecks = threshold_soft(micro, 0.88, 0.10)
        detail = (micro - 0.5) * 0.045 - pores * 0.055 - pinholes * 0.035 + mineral_flecks * 0.030
        if style == "weathered_ashlar_limestone":
            rain_channels = band_mask(xx * 18.0 + tile_noise(size, seed + 241, 4) * 2.2, 0.020)
            detail += rain_channels * threshold_soft(speckle, 0.45, 0.35) * 0.045
        return np.clip(height + detail, 0.0, 1.0)

    if style == "asphalt":
        exposed_aggregate = threshold_soft(micro, 0.44, 0.30)
        loose_stone = threshold_soft(speckle, 0.86, 0.11)
        alligator_cracks = band_mask(xx * 16.0 + yy * 11.0 + speckle * 6.0, 0.016)
        return np.clip(height + exposed_aggregate * 0.070 + loose_stone * 0.045 + alligator_cracks * 0.055 - pores * 0.025, 0.0, 1.0)

    if style == "concrete":
        aggregate = threshold_soft(micro, 0.78, 0.18)
        trowel_swirls = band_mask(xx * 19.0 + np.sin(yy * 7.0 + micro * 2.0), 0.028) * 0.035
        return np.clip(height + (micro - 0.5) * 0.040 + aggregate * 0.040 + trowel_swirls - pinholes * 0.045, 0.0, 1.0)

    if style in {"fabric", "carpet", "canvas"}:
        lint = threshold_soft(speckle, 0.84, 0.12) * 0.035
        cross_threads = (np.sin(xx * 166.0 + micro) + np.sin(yy * 154.0 + speckle)) * 0.018
        return np.clip(height + cross_threads + lint, 0.0, 1.0)

    if style in {"wood_planks", "leather"}:
        open_grain = band_mask(xx * 44.0 + micro * 4.0, 0.034) * 0.045
        pores_low = pores * 0.035
        return np.clip(height + open_grain - pores_low + (speckle - 0.5) * 0.025, 0.0, 1.0)

    if style in {"brushed_metal", "painted_metal", "painted_dome_panels"}:
        oxidation = threshold_soft(micro, 0.78, 0.16) * 0.030
        return np.clip(height + scratch * 0.040 + hairline * 0.024 + oxidation + (speckle - 0.5) * 0.018, 0.0, 1.0)

    if style == "worn_paint":
        paint_lift = threshold_soft(micro, 0.74, 0.18) * 0.045
        undercoat_chips = pinholes * 0.040
        return np.clip(height + paint_lift - undercoat_chips + scratch * 0.026, 0.0, 1.0)

    if style == "grass":
        clumps = threshold_soft(micro, 0.66, 0.24) * 0.045
        dry_low_spots = threshold_soft(0.42 - speckle, 0.00, 0.18) * 0.035
        return np.clip(height + clumps - dry_low_spots, 0.0, 1.0)

    if style == "glass":
        return np.clip(height + scratch * 0.012 + (micro - 0.5) * 0.006, 0.0, 1.0)

    return np.clip(height + (micro - 0.5) * 0.024 + pinholes * 0.018, 0.0, 1.0)


def style_height(style: str, size: int, seed: int) -> np.ndarray:
    x = np.linspace(0.0, math.tau, size, endpoint=False, dtype=np.float32)
    xx = x.reshape(1, size)
    yy = x.reshape(size, 1)
    base = tile_noise(size, seed, 7)
    fine = tile_noise(size, seed + 17, 10)
    ridges = ridge_noise(size, seed + 31)

    if style == "asphalt":
        aggregate = threshold_soft(fine, 0.50, 0.28) * np.float32(0.38)
        cracks = band_mask(xx * 3.0 + yy * 2.0 + tile_noise(size, seed + 71, 4) * 6.0, 0.022)
        tar_patch = band_mask(xx * 5.0 - yy * 2.0 + tile_noise(size, seed + 72, 4) * 3.0, 0.035) * threshold_soft(ridges, 0.62, 0.22)
        return np.clip(base * 0.32 + aggregate + ridges * 0.16 + cracks * 0.36 + tar_patch * 0.18, 0.0, 1.0)
    if style == "concrete":
        hairline = band_mask(xx * 4.0 - yy * 3.0 + tile_noise(size, seed + 7, 5) * 5.0, 0.018)
        trowel = band_mask(xx * 10.0 + tile_noise(size, seed + 8, 3) * 1.6, 0.075) * 0.08
        return np.clip(base * 0.36 + fine * 0.22 + hairline * 0.34 + trowel, 0.0, 1.0)
    if style == "grass":
        blades = (np.sin(xx * 34.0 + tile_noise(size, seed + 2, 3) * 4.0) + 1.0) * 0.16
        return np.clip(base * 0.45 + fine * 0.25 + blades, 0.0, 1.0)
    if style == "wood":
        flow = tile_noise(size, seed + 4, 5) * 7.0
        grain = (np.sin(xx * 22.0 + flow) + 1.0) * 0.30
        tight_grain = (np.sin(xx * 74.0 + flow * 1.7) + 1.0) * 0.065
        knots = periodic_knot_field(xx, yy, seed) * 0.36
        long_variation = tile_noise(size, seed + 5, 4) * 0.28
        return np.clip(grain + tight_grain + knots + long_variation + fine * 0.13, 0.0, 1.0)
    if style == "wood_planks":
        flow = tile_noise(size, seed + 4, 5) * 7.4
        grain = (np.sin(xx * 24.0 + flow) + 1.0) * 0.27
        tight_grain = (np.sin(xx * 86.0 + flow * 1.6) + 1.0) * 0.07
        plank_seams = band_mask(yy * 6.0 + tile_noise(size, seed + 21, 3) * 0.28, 0.040)
        end_checks = band_mask(xx * 3.0 + np.sin(yy * 3.0) * 0.65, 0.028) * threshold_soft(plank_seams, 0.25, 0.42)
        knots = periodic_knot_field(xx, yy, seed) * 0.34
        plank_tone = (np.sin(yy * 6.0 + seed * 0.001) + 1.0) * 0.08
        return np.clip(0.18 + grain + tight_grain + knots + plank_tone + fine * 0.10 - plank_seams * 0.34 - end_checks * 0.18, 0.0, 1.0)
    if style == "carpet":
        warp = np.sin(xx * 112.0 + tile_noise(size, seed + 18, 3) * 0.8) * 0.055
        weft = np.sin(yy * 104.0 + tile_noise(size, seed + 19, 3) * 0.8) * 0.055
        pile = threshold_soft(fine, 0.42, 0.36) * 0.35
        wear_lanes = band_mask(xx * 4.0 + yy * 1.0, 0.18) * 0.08
        return np.clip(0.42 + warp + weft + pile + wear_lanes, 0.0, 1.0)
    if style == "fabric":
        weave = (np.sin(xx * 58.0) * np.sin(yy * 54.0)) * 0.12 + 0.48
        thread = (np.sin(xx * 116.0 + yy * 3.0) + np.sin(yy * 112.0)) * 0.035
        return np.clip(weave + thread + fine * 0.25, 0.0, 1.0)
    if style == "leather":
        pores = threshold_soft(fine, 0.68, 0.20) * np.float32(0.28)
        crease = band_mask(xx * 5.0 + yy * 4.0 + tile_noise(size, seed + 35, 4) * 5.0, 0.030)
        return np.clip(base * 0.44 + ridges * 0.20 + pores + crease * 0.22, 0.0, 1.0)
    if style == "brushed_metal":
        brush = (np.sin(xx * 92.0 + fine * 2.0) + 1.0) * 0.10
        hair_scratches = band_mask(xx * 38.0 + tile_noise(size, seed + 44, 4) * 2.0, 0.030) * 0.14
        return np.clip(base * 0.20 + brush + hair_scratches, 0.0, 1.0)
    if style == "painted_metal":
        seam = band_mask(xx * 9.0 + tile_noise(size, seed + 45, 3) * 1.2, 0.035) * 0.10
        oxidized = threshold_soft(ridges, 0.72, 0.18) * 0.14
        return np.clip(base * 0.26 + fine * 0.17 + seam + oxidized, 0.0, 1.0)
    if style == "painted_dome_panels":
        vertical_seams = band_mask(xx * 10.0 + tile_noise(size, seed + 45, 3) * 0.80, 0.030)
        lateral_bands = band_mask(yy * 4.0 + tile_noise(size, seed + 46, 3) * 0.42, 0.045)
        oxidized = threshold_soft(ridges, 0.62, 0.26) * 0.16
        runoff = band_mask(xx * 13.0 + tile_noise(size, seed + 47, 4) * 2.2, 0.036) * threshold_soft(yy, 2.0, 2.6) * 0.15
        subtle_panels = (np.sin(xx * 10.0 + 0.5) + 1.0) * 0.035
        return np.clip(base * 0.22 + fine * 0.12 + subtle_panels + oxidized + runoff - vertical_seams * 0.18 - lateral_bands * 0.10, 0.0, 1.0)
    if style == "worn_paint":
        wear = threshold_soft(ridges, 0.72, 0.18) * np.float32(0.42)
        chipped_edges = band_mask(xx * 12.0 + yy * 4.0 + tile_noise(size, seed + 48, 4) * 4.0, 0.032) * 0.18
        return np.clip(base * 0.20 + fine * 0.17 + wear + chipped_edges, 0.0, 1.0)
    if style == "glass":
        return np.clip(base * 0.08 + fine * 0.05, 0.0, 1.0)
    if style == "marble":
        vein_signal = xx * 4.0 + yy * 3.0 + tile_noise(size, seed + 9, 5) * 8.0
        veins = band_mask(vein_signal, 0.060)
        secondary = band_mask(xx * 7.0 - yy * 2.0 + tile_noise(size, seed + 10, 4) * 5.0, 0.035)
        return np.clip(base * 0.30 + veins * 0.42 + secondary * 0.20 + fine * 0.10, 0.0, 1.0)
    if style == "marble_floor":
        vein_signal = xx * 3.8 + yy * 2.7 + tile_noise(size, seed + 9, 5) * 8.5
        veins = band_mask(vein_signal, 0.052)
        secondary = band_mask(xx * 7.4 - yy * 1.8 + tile_noise(size, seed + 10, 4) * 4.8, 0.030)
        tile_joints = band_mask(xx * 4.0, 0.038) + band_mask(yy * 4.0, 0.038)
        polish_waves = (np.sin(xx * 2.0 + yy * 1.2 + tile_noise(size, seed + 11, 3) * 1.5) + 1.0) * 0.045
        return np.clip(base * 0.24 + veins * 0.38 + secondary * 0.18 + polish_waves + fine * 0.08 - tile_joints * 0.28, 0.0, 1.0)
    if style == "marble_wall":
        vertical_veins = band_mask(xx * 3.2 + yy * 1.1 + tile_noise(size, seed + 9, 5) * 7.0, 0.050)
        hairline_veins = band_mask(xx * 8.5 - yy * 1.4 + tile_noise(size, seed + 10, 4) * 4.0, 0.025)
        slab_joints = band_mask(xx * 4.0, 0.030) * 0.70 + band_mask(yy * 2.0, 0.026) * 0.42
        cloudy = tile_noise(size, seed + 11, 6) * 0.12
        return np.clip(base * 0.26 + vertical_veins * 0.36 + hairline_veins * 0.16 + cloudy + fine * 0.07 - slab_joints * 0.22, 0.0, 1.0)
    if style == "pavers":
        grid_x = band_mask(xx * 8.0, 0.050)
        grid_y = band_mask(yy * 8.0 + np.sin(xx * 4.0) * 0.35, 0.050)
        chipped_edges = threshold_soft(ridges, 0.78, 0.18) * (grid_x + grid_y) * 0.20
        return np.clip(base * 0.27 + fine * 0.16 + (grid_x + grid_y) * 0.30 + chipped_edges, 0.0, 1.0)
    if style == "worn_stone":
        chips = threshold_soft(fine, 0.74, 0.20) * np.float32(0.30)
        erosion = band_mask(xx * 5.0 - yy * 3.0 + tile_noise(size, seed + 56, 5) * 5.5, 0.050) * 0.18
        return np.clip(base * 0.38 + ridges * 0.18 + chips + erosion, 0.0, 1.0)
    if style == "canvas":
        weave = (np.sin(xx * 76.0) + np.sin(yy * 80.0)) * 0.075 + 0.48
        brush = ridge_noise(size, seed + 12) * 0.22
        brush_direction = band_mask(xx * 10.0 + yy * 2.0 + tile_noise(size, seed + 13, 4) * 3.5, 0.12) * 0.08
        return np.clip(weave + brush + brush_direction + fine * 0.20, 0.0, 1.0)
    if style == "weathered_stone":
        bedding = band_mask(yy * 7.0 + tile_noise(size, seed + 61, 4) * 0.9, 0.070) * 0.12
        pits = threshold_soft(fine, 0.76, 0.18) * 0.22
        rain_streaks = band_mask(xx * 11.0 + tile_noise(size, seed + 62, 4) * 2.0, 0.045) * threshold_soft(ridges, 0.48, 0.35) * 0.24
        mineral_veins = band_mask(xx * 4.0 + yy * 2.0 + tile_noise(size, seed + 63, 5) * 4.0, 0.034) * 0.14
        return np.clip(base * 0.32 + ridges * 0.14 + bedding + pits + rain_streaks + mineral_veins, 0.0, 1.0)
    if style in {"ashlar_limestone", "weathered_ashlar_limestone"}:
        course_shift = np.where(np.sin(yy * 4.0) > 0.0, math.pi * 0.46, 0.0)
        horizontal_joints = band_mask(yy * 8.0 + tile_noise(size, seed + 61, 4) * 0.32, 0.050)
        vertical_joints = band_mask(xx * 5.0 + course_shift + tile_noise(size, seed + 62, 3) * 0.24, 0.038)
        block_joints = np.clip(horizontal_joints + vertical_joints, 0.0, 1.0)
        bedding = band_mask(yy * 18.0 + tile_noise(size, seed + 63, 4) * 0.70, 0.055) * 0.09
        pits = threshold_soft(fine, 0.76, 0.18) * 0.18
        mineral_veins = band_mask(xx * 3.2 + yy * 5.1 + tile_noise(size, seed + 64, 5) * 4.0, 0.028) * 0.13
        weathering = 0.0
        if style == "weathered_ashlar_limestone":
            weathering = (
                band_mask(xx * 10.0 + tile_noise(size, seed + 65, 4) * 2.0, 0.043)
                * threshold_soft(ridges, 0.42, 0.34)
                * 0.24
            )
        block_variation = (np.sin(xx * 2.5 + seed * 0.001) + np.cos(yy * 3.0 - seed * 0.001)) * 0.035
        return np.clip(0.42 + base * 0.16 + fine * 0.11 + bedding + pits + mineral_veins + weathering + block_variation - block_joints * 0.36, 0.0, 1.0)
    # stone
    bedding = band_mask(yy * 7.0 + tile_noise(size, seed + 61, 4) * 0.9, 0.065) * 0.10
    mineral_veins = band_mask(xx * 3.0 + yy * 5.0 + tile_noise(size, seed + 63, 5) * 4.0, 0.030) * 0.14
    flecks = threshold_soft(fine, 0.82, 0.16) * np.float32(0.18)
    return np.clip(base * 0.34 + ridges * 0.14 + bedding + mineral_veins + flecks, 0.0, 1.0)


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
    base = np.array(base_color, dtype=np.float32).reshape(1, 1, 3)
    variation = (height - 0.5)[:, :, None]
    tint_noise = tile_noise(height.shape[0], seed + 101, 5)[:, :, None] - 0.5
    detail_noise = tile_noise(height.shape[0], seed + 121, 7)[:, :, None] - 0.5
    color = base * (1.0 + variation * 0.24 + tint_noise * 0.10 + detail_noise * 0.04)

    if style in {"asphalt", "leather", "brushed_metal"}:
        color *= 0.92 + variation * 0.18
    elif style in {"painted_dome_panels"}:
        seam_shadow = np.clip(0.44 - height[:, :, None], 0.0, 1.0)
        oxidized = np.clip(height[:, :, None] - 0.56, 0.0, 1.0)
        cool = np.array([-0.025, -0.018, 0.010], dtype=np.float32).reshape(1, 1, 3)
        grime = np.array([-0.070, -0.065, -0.055], dtype=np.float32).reshape(1, 1, 3)
        color += cool * oxidized
        color += grime * seam_shadow
    elif style in {"stone"}:
        warm = np.array([0.035, 0.028, 0.006], dtype=np.float32).reshape(1, 1, 3)
        cool = np.array([-0.018, -0.014, 0.018], dtype=np.float32).reshape(1, 1, 3)
        color += warm * np.clip(height[:, :, None] - 0.56, 0.0, 1.0)
        color += cool * np.clip(0.44 - height[:, :, None], 0.0, 1.0)
    elif style in {"ashlar_limestone", "weathered_ashlar_limestone"}:
        warm = np.array([0.040, 0.033, 0.010], dtype=np.float32).reshape(1, 1, 3)
        cool = np.array([-0.028, -0.025, -0.012], dtype=np.float32).reshape(1, 1, 3)
        joint_grime = np.array([-0.095, -0.090, -0.078], dtype=np.float32).reshape(1, 1, 3)
        color += warm * np.clip(height[:, :, None] - 0.58, 0.0, 1.0)
        color += cool * np.clip(0.50 - height[:, :, None], 0.0, 1.0)
        color += joint_grime * np.clip(0.34 - height[:, :, None], 0.0, 1.0)
        if style == "weathered_ashlar_limestone":
            stain = np.array([-0.080, -0.078, -0.070], dtype=np.float32).reshape(1, 1, 3)
            color += stain * np.clip(height[:, :, None] - 0.55, 0.0, 1.0)
    elif style in {"weathered_stone"}:
        grime = np.array([-0.12, -0.11, -0.095], dtype=np.float32).reshape(1, 1, 3)
        mineral = np.array([0.055, 0.048, 0.020], dtype=np.float32).reshape(1, 1, 3)
        color += grime * np.clip(height[:, :, None] - 0.52, 0.0, 1.0)
        color += mineral * np.clip(0.45 - height[:, :, None], 0.0, 1.0)
    elif style in {"worn_stone", "concrete", "pavers"}:
        dust = np.array([0.030, 0.027, 0.018], dtype=np.float32).reshape(1, 1, 3)
        shadow = np.array([-0.045, -0.043, -0.040], dtype=np.float32).reshape(1, 1, 3)
        color += dust * np.clip(height[:, :, None] - 0.55, 0.0, 1.0)
        color += shadow * np.clip(0.40 - height[:, :, None], 0.0, 1.0)
    elif style == "worn_paint":
        exposed = np.array([-0.18, -0.17, -0.15], dtype=np.float32).reshape(1, 1, 3)
        chalk = np.array([0.08, 0.08, 0.07], dtype=np.float32).reshape(1, 1, 3)
        color += exposed * np.clip(height[:, :, None] - 0.64, 0.0, 1.0)
        color += chalk * np.clip(0.52 - height[:, :, None], 0.0, 1.0)
    elif style in {"grass"}:
        yellow = np.array([0.08, 0.07, -0.04], dtype=np.float32).reshape(1, 1, 3)
        color += yellow * np.clip(tint_noise + 0.4, 0.0, 1.0)
    elif style in {"wood"}:
        color += np.array([0.06, 0.024, -0.016], dtype=np.float32).reshape(1, 1, 3) * np.sin(height[:, :, None] * math.tau * 2.0)
        color *= 0.92 + np.clip(height[:, :, None], 0.0, 1.0) * 0.18
    elif style in {"wood_planks"}:
        color += np.array([0.060, 0.024, -0.016], dtype=np.float32).reshape(1, 1, 3) * np.sin(height[:, :, None] * math.tau * 2.0)
        color *= 0.90 + np.clip(height[:, :, None], 0.0, 1.0) * 0.20
        seam_shadow = np.array([-0.080, -0.045, -0.020], dtype=np.float32).reshape(1, 1, 3)
        color += seam_shadow * np.clip(0.34 - height[:, :, None], 0.0, 1.0)
    elif style in {"carpet", "fabric", "canvas"}:
        fiber_highlight = np.array([0.035, 0.033, 0.030], dtype=np.float32).reshape(1, 1, 3)
        color += fiber_highlight * np.clip(height[:, :, None] - 0.54, 0.0, 1.0)
    elif style in {"marble"}:
        color += np.array([0.05, 0.045, 0.02], dtype=np.float32).reshape(1, 1, 3) * np.clip(height[:, :, None] - 0.62, 0.0, 1.0)
    elif style in {"marble_floor", "marble_wall"}:
        vein_tint = np.array([0.050, 0.045, 0.025], dtype=np.float32).reshape(1, 1, 3)
        cool_shadow = np.array([-0.045, -0.040, -0.030], dtype=np.float32).reshape(1, 1, 3)
        polish = np.array([0.025, 0.022, 0.014], dtype=np.float32).reshape(1, 1, 3)
        color += vein_tint * np.clip(height[:, :, None] - 0.60, 0.0, 1.0)
        color += cool_shadow * np.clip(0.36 - height[:, :, None], 0.0, 1.0)
        color += polish * np.clip(height[:, :, None] - 0.48, 0.0, 1.0)

    cavity = np.clip(0.42 - height[:, :, None], 0.0, 1.0)
    raised = np.clip(height[:, :, None] - 0.62, 0.0, 1.0)
    fleck = np.clip(detail_noise + 0.18, 0.0, 1.0)
    stain = np.clip(tint_noise + 0.32, 0.0, 1.0)
    if style in {"ashlar_limestone", "weathered_ashlar_limestone", "worn_stone", "marble_floor", "marble_wall", "pavers"}:
        color += np.array([-0.070, -0.066, -0.056], dtype=np.float32).reshape(1, 1, 3) * cavity
        color += np.array([0.034, 0.028, 0.010], dtype=np.float32).reshape(1, 1, 3) * fleck * raised
        if style == "weathered_ashlar_limestone":
            color += np.array([-0.090, -0.086, -0.074], dtype=np.float32).reshape(1, 1, 3) * stain * np.clip(height[:, :, None] - 0.52, 0.0, 1.0)
    elif style == "asphalt":
        color += np.array([0.085, 0.083, 0.078], dtype=np.float32).reshape(1, 1, 3) * fleck * raised
        color += np.array([-0.040, -0.038, -0.036], dtype=np.float32).reshape(1, 1, 3) * cavity
    elif style in {"concrete", "pavers"}:
        color += np.array([0.045, 0.042, 0.034], dtype=np.float32).reshape(1, 1, 3) * fleck * raised
        color += np.array([-0.060, -0.058, -0.052], dtype=np.float32).reshape(1, 1, 3) * stain * cavity
    elif style in {"fabric", "carpet", "canvas"}:
        color *= 1.0 + (detail_noise * 0.055)
        color += np.array([0.026, 0.024, 0.022], dtype=np.float32).reshape(1, 1, 3) * fleck * 0.35
    elif style in {"wood_planks", "leather"}:
        color += np.array([-0.052, -0.030, -0.016], dtype=np.float32).reshape(1, 1, 3) * cavity
        color += np.array([0.036, 0.018, 0.002], dtype=np.float32).reshape(1, 1, 3) * raised
    elif style in {"brushed_metal", "painted_metal", "painted_dome_panels"}:
        color += np.array([0.038, 0.036, 0.032], dtype=np.float32).reshape(1, 1, 3) * fleck * 0.25
        color += np.array([-0.040, -0.038, -0.034], dtype=np.float32).reshape(1, 1, 3) * cavity
    elif style == "glass":
        color += np.array([0.018, 0.024, 0.030], dtype=np.float32).reshape(1, 1, 3) * fleck * 0.18

    return (np.clip(color, 0.0, 1.0) * 255.0).astype(np.uint8)


def roughness_map(base_roughness: float, height: np.ndarray, style: str) -> np.ndarray:
    roughness = base_roughness + (height - 0.5) * 0.16
    if style in {"glass", "brushed_metal"}:
        roughness = base_roughness + (height - 0.5) * 0.08
    if style in {"painted_dome_panels"}:
        roughness = base_roughness + height * 0.10 + np.clip(0.42 - height, 0.0, 1.0) * 0.08
    if style in {"weathered_stone", "worn_stone", "concrete", "pavers", "asphalt"}:
        roughness = base_roughness + height * 0.10 - 0.03
    if style in {"ashlar_limestone", "weathered_ashlar_limestone"}:
        roughness = base_roughness + height * 0.08 + np.clip(0.36 - height, 0.0, 1.0) * 0.12 - 0.02
    if style in {"marble_floor"}:
        roughness = base_roughness + np.clip(0.42 - height, 0.0, 1.0) * 0.16 - np.clip(height - 0.62, 0.0, 1.0) * 0.08
    if style in {"marble_wall"}:
        roughness = base_roughness + np.clip(0.42 - height, 0.0, 1.0) * 0.12
    if style in {"carpet", "grass"}:
        roughness = base_roughness + height * 0.04
    if style in {"wood", "leather"}:
        roughness = base_roughness + (height - 0.5) * 0.10
    if style in {"wood_planks"}:
        roughness = base_roughness + (height - 0.5) * 0.10 + np.clip(0.34 - height, 0.0, 1.0) * 0.10
    if style in {"worn_paint"}:
        roughness = base_roughness + np.clip(height - 0.45, 0.0, 1.0) * 0.18
    neighbor_mean = (
        np.roll(height, -1, axis=0)
        + np.roll(height, 1, axis=0)
        + np.roll(height, -1, axis=1)
        + np.roll(height, 1, axis=1)
    ) * np.float32(0.25)
    micro_breakup = np.clip(np.abs(height - neighbor_mean) * 3.5, 0.0, 1.0)
    if style in {"glass"}:
        roughness += micro_breakup * 0.025
    elif style in {"brushed_metal", "painted_metal"}:
        roughness += micro_breakup * 0.055
    else:
        roughness += micro_breakup * 0.085
    gray = np.clip(roughness, 0.0, 1.0) * 255.0
    return np.repeat(gray[:, :, None], 3, axis=2).astype(np.uint8)


def ambient_occlusion_map(height: np.ndarray, style: str) -> np.ndarray:
    neighbor_mean = (
        np.roll(height, -1, axis=0)
        + np.roll(height, 1, axis=0)
        + np.roll(height, -1, axis=1)
        + np.roll(height, 1, axis=1)
    ) * np.float32(0.25)
    local_cavity = np.clip((neighbor_mean - height) * 5.0, 0.0, 1.0)
    low_crevices = np.clip((0.48 - height) * 2.4, 0.0, 1.0)
    style_strength = {
        "ashlar_limestone": 0.52,
        "weathered_ashlar_limestone": 0.62,
        "worn_stone": 0.58,
        "weathered_stone": 0.62,
        "pavers": 0.58,
        "asphalt": 0.50,
        "concrete": 0.42,
        "wood_planks": 0.46,
        "marble_floor": 0.36,
        "marble_wall": 0.34,
        "carpet": 0.30,
        "fabric": 0.28,
        "leather": 0.38,
        "canvas": 0.32,
        "brushed_metal": 0.26,
        "painted_metal": 0.28,
        "painted_dome_panels": 0.34,
        "worn_paint": 0.36,
        "glass": 0.14,
        "grass": 0.32,
    }.get(style, 0.38)
    cavity = np.clip(local_cavity * 0.72 + low_crevices * 0.48, 0.0, 1.0)
    occlusion = 1.0 - cavity * np.float32(style_strength)
    gray = np.clip(occlusion, 0.0, 1.0) * 255.0
    return np.repeat(gray[:, :, None], 3, axis=2).astype(np.uint8)


def generate_set(name: str, spec: dict[str, Any]) -> dict[str, str]:
    seed = int.from_bytes(hashlib.sha256(name.encode("utf-8")).digest()[:8], "big") % 1_000_000
    style = str(spec["style"])
    height = photoreal_height_detail(style_height(style, SIZE, seed), style, seed)
    basecolor = color_map(spec["base"], height, style, seed)
    normal = normal_from_height(height, float(spec["normal_strength"]))
    roughness = roughness_map(float(spec["roughness"]), height, style)
    ambient_occlusion = ambient_occlusion_map(height, style)

    paths = {
        "basecolor": f"generated/textures/{name}_basecolor.png",
        "normal": f"generated/textures/{name}_normal.png",
        "roughness": f"generated/textures/{name}_roughness.png",
        "ambient_occlusion": f"generated/textures/{name}_ambient_occlusion.png",
    }
    write_png(ROOT / paths["basecolor"], basecolor)
    write_png(ROOT / paths["normal"], normal)
    write_png(ROOT / paths["roughness"], roughness)
    write_png(ROOT / paths["ambient_occlusion"], ambient_occlusion)
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
            "ambient_occlusion": texture_paths["ambient_occlusion"],
        }

    manifest = {
        "package": "capitol_unreal_map",
        "texture_root": "generated/textures",
        "source_type": "deterministic_procedural_local",
        "external_texture_sources": [],
        "photoreal_readiness_features": PHOTOREAL_TEXTURE_FEATURES,
        "realism_note": "Generated locally from structured procedural material rules: ashlar limestone block joints, weathering streaks, marble slab/floor veining, dome panel seams, wood plank seams/grain/knots, paver joints, asphalt aggregate/cracks/tar breakup, concrete pitting/trowel variation, textile/canvas fiber breakup, metal brushing/scratches/tarnish variation, micro pores, mineral flecks, stain masks, and height-derived normal/roughness/ambient-occlusion maps. These are 4K PBR-style placeholder maps, not scanned or photogrammetry material textures.",
        "target_size_px": [SIZE, SIZE],
        "png_compression_level": PNG_COMPRESSION_LEVEL,
        "sets": sets,
        "materials": MATERIAL_TEXTURE_BINDINGS,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {len(sets)} texture sets to {TEXTURE_DIR}")
    print(f"Wrote manifest to {MANIFEST_PATH}")
    print(f"Material texture bindings: {len(MATERIAL_TEXTURE_BINDINGS)}")


if __name__ == "__main__":
    main()
