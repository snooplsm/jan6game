#!/usr/bin/env python3
"""Build a public-data U.S. Capitol map package for Unreal Engine.

The exterior is derived from OpenStreetMap geometry. The interior is a
public-only schematic based on public descriptions of major Capitol spaces; it
does not model restricted office assignments, service routes, or security
features.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET_MAP_ERA = "Jan 6, 2021 / late-2020 public map state"
TARGET_OSM_DATE_UTC = "2021-01-06T17:00:00Z"
HISTORICAL_OSM_SOURCE = ROOT / "source_data" / "capitol_osm_overpass_2021-01-06.json"
STRICT_2020_OSM_SOURCE = ROOT / "source_data" / "capitol_osm_overpass_2020-12-31.json"
PRESENT_DAY_OSM_SOURCE = ROOT / "source_data" / "capitol_osm_overpass_2026-07-04.json"
SOURCE = next(
    path
    for path in (HISTORICAL_OSM_SOURCE, STRICT_2020_OSM_SOURCE, PRESENT_DAY_OSM_SOURCE)
    if path.exists()
)
DCGIS_ELEVATION_SOURCE = ROOT / "source_data" / "dc_planimetrics_1999_capitol_elevation_points.json"
DCGIS_TRAFFIC_SIGN_SOURCE = ROOT / "source_data" / "dc_planimetrics_1999_capitol_traffic_signs.json"
DCGIS_FIXTURE_SOURCE = ROOT / "source_data" / "dc_planimetrics_1999_capitol_public_fixtures.json"
DCGIS_GROUND_SURFACE_SOURCE = ROOT / "source_data" / "dc_planimetrics_1999_capitol_ground_surfaces.json"
GENERATED = ROOT / "generated"
MESH_DIR = GENERATED / "meshes"
DATA_DIR = GENERATED / "data"

LAT0 = 38.889939
LON0 = -77.009051
EARTH_M_PER_DEG_LAT = 111_320.0
EARTH_M_PER_DEG_LON = 111_320.0 * math.cos(math.radians(LAT0))
OBJ_UNIT_SCALE = 100.0  # meters to Unreal centimeters
UV_TILE_METERS = 3.0


def relative_to_package(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


@dataclass(frozen=True)
class ElevationPoint:
    x: float
    y: float
    elevation_m: float
    object_id: int


@dataclass(frozen=True)
class DcgisTrafficSignPoint:
    x: float
    y: float
    object_id: int
    sign_code: int
    sign_id: int
    description: str
    dxf_layer: str


@dataclass(frozen=True)
class DcgisOverheadTrafficSign:
    points: tuple[tuple[float, float], ...]
    object_id: int
    sign_code: int
    sign_id: int
    description: str
    dxf_layer: str


@dataclass(frozen=True)
class DcgisFixturePoint:
    x: float
    y: float
    object_id: int
    feature_id: int
    feature_code: int
    angle_degrees: float
    description: str
    dxf_layer: str
    source_layer: str
    source_label: str


@dataclass(frozen=True)
class DcgisPolylineFeature:
    points: tuple[tuple[float, float], ...]
    object_id: int
    feature_id: int
    feature_code: int
    description: str
    dxf_layer: str
    source_layer: str
    source_label: str


@dataclass(frozen=True)
class DcgisPolygonFeature:
    rings: tuple[tuple[tuple[float, float], ...], ...]
    object_id: int
    feature_id: int
    feature_code: int
    description: str
    dxf_layer: str
    source_layer: str
    source_label: str


MATERIALS = {
    "BuildingGeneric": (0.72, 0.72, 0.70, 1.0),
    "BuildingCapitol": (0.90, 0.88, 0.82, 1.0),
    "CapitolStone": (0.86, 0.84, 0.78, 1.0),
    "CapitolDome": (0.82, 0.82, 0.78, 1.0),
    "ColumnStone": (0.90, 0.88, 0.82, 1.0),
    "StepStone": (0.62, 0.60, 0.56, 1.0),
    "StoneGrimeOverlay": (0.24, 0.23, 0.20, 0.46),
    "GroundGrass": (0.16, 0.32, 0.12, 1.0),
    "PlazaStone": (0.58, 0.56, 0.50, 1.0),
    "RoadAsphalt": (0.045, 0.048, 0.052, 1.0),
    "RoadPatchAsphalt": (0.030, 0.032, 0.034, 1.0),
    "RoadCrackSealant": (0.010, 0.011, 0.012, 1.0),
    "LaneMarkingWhite": (0.96, 0.96, 0.90, 1.0),
    "LaneMarkingYellow": (0.95, 0.78, 0.14, 1.0),
    "SidewalkConcrete": (0.56, 0.56, 0.53, 1.0),
    "CurbConcrete": (0.74, 0.74, 0.70, 1.0),
    "BikeLaneGreen": (0.04, 0.34, 0.16, 1.0),
    "BikeLanePost": (0.90, 0.90, 0.82, 1.0),
    "CrosswalkWhite": (0.92, 0.92, 0.88, 1.0),
    "SignalMarker": (0.95, 0.75, 0.10, 1.0),
    "InteriorFloor": (0.62, 0.56, 0.48, 1.0),
    "InteriorWall": (0.82, 0.78, 0.69, 1.0),
    "InteriorTrim": (0.55, 0.43, 0.28, 1.0),
    "HouseCarpet": (0.08, 0.13, 0.35, 1.0),
    "SenateCarpet": (0.36, 0.06, 0.06, 1.0),
    "DeskWood": (0.30, 0.16, 0.07, 1.0),
    "ChairLeather": (0.08, 0.07, 0.055, 1.0),
    "BrassRail": (0.82, 0.63, 0.24, 1.0),
    "RotundaFloor": (0.78, 0.68, 0.50, 1.0),
    "RotundaWall": (0.88, 0.84, 0.74, 1.0),
    "FloorWear": (0.36, 0.34, 0.30, 0.42),
    "HouseSeat": (0.12, 0.23, 0.55, 1.0),
    "HouseDesk": (0.28, 0.18, 0.10, 1.0),
    "SenateDesk": (0.34, 0.18, 0.08, 1.0),
    "SenateChair": (0.12, 0.11, 0.10, 1.0),
    "PublicGallery": (0.24, 0.28, 0.30, 1.0),
    "OfficeZone": (0.46, 0.53, 0.62, 1.0),
    "MarkerBlue": (0.10, 0.35, 0.95, 1.0),
    "StreetSignGreen": (0.03, 0.24, 0.10, 1.0),
    "DoorGlass": (0.48, 0.72, 0.88, 0.55),
    "DoorMetal": (0.18, 0.20, 0.21, 1.0),
    "PresidentPodium": (0.18, 0.09, 0.035, 1.0),
    "JointSessionZone": (0.42, 0.36, 0.26, 1.0),
    "SupremeCourtZone": (0.18, 0.18, 0.18, 1.0),
    "CabinetZone": (0.08, 0.16, 0.32, 1.0),
    "DiplomaticZone": (0.24, 0.16, 0.30, 1.0),
    "PressZone": (0.16, 0.20, 0.20, 1.0),
    "StatueMarble": (0.78, 0.74, 0.66, 1.0),
    "StatueBronze": (0.36, 0.24, 0.12, 1.0),
    "ArtFrameGold": (0.78, 0.56, 0.16, 1.0),
    "PaintingCanvas": (0.42, 0.28, 0.18, 1.0),
    "PortraitCanvas": (0.24, 0.18, 0.14, 1.0),
    "WarmLightGlass": (1.0, 0.82, 0.48, 0.72),
    "LightFixtureMetal": (0.18, 0.15, 0.11, 1.0),
    "FacadeWindow": (0.08, 0.13, 0.16, 0.72),
    "StreetLightPole": (0.11, 0.11, 0.10, 1.0),
    "StreetLightGlass": (1.0, 0.86, 0.54, 0.70),
    "TrafficSignalHousing": (0.045, 0.052, 0.045, 1.0),
    "TrafficSignalRed": (0.85, 0.06, 0.035, 1.0),
    "TrafficSignalYellow": (0.95, 0.68, 0.05, 1.0),
    "TrafficSignalGreen": (0.04, 0.50, 0.16, 1.0),
    "TreeTrunk": (0.25, 0.13, 0.055, 1.0),
    "TreeCanopy": (0.075, 0.28, 0.10, 1.0),
    "PlanterStone": (0.52, 0.50, 0.45, 1.0),
    "BenchWood": (0.28, 0.14, 0.055, 1.0),
    "BollardMetal": (0.12, 0.12, 0.115, 1.0),
    "GameplayPickupPad": (0.12, 0.18, 0.24, 1.0),
    "ItemWood": (0.30, 0.15, 0.06, 1.0),
    "ItemMetal": (0.16, 0.16, 0.15, 1.0),
    "ItemGrip": (0.055, 0.055, 0.052, 1.0),
    "ItemSprayCan": (0.88, 0.30, 0.08, 1.0),
    "ItemWarningOrange": (0.95, 0.38, 0.04, 1.0),
    "ItemOrganicBrown": (0.22, 0.11, 0.045, 1.0),
    "ItemBlade": (0.70, 0.70, 0.66, 1.0),
    "ItemCloth": (0.72, 0.06, 0.04, 1.0),
}

VIEWPOINTS = [
    {
        "label": "CapitolMap_Camera_Overview",
        "location_m": [-190.0, -210.0, 120.0],
        "target_m": [0.0, 0.0, 8.0],
        "fov": 45.0,
        "category": "overview",
    },
    {
        "label": "CapitolMap_Camera_WestFront_FirstPerson",
        "location_m": [-105.0, 0.0, 1.8],
        "target_m": [0.0, 0.0, 5.0],
        "fov": 78.0,
        "category": "first_person",
    },
    {
        "label": "CapitolMap_Camera_PublicInteriorWalk",
        "location_m": [0.0, -14.0, 5.7],
        "target_m": [0.0, 0.0, 5.2],
        "fov": 78.0,
        "category": "first_person_public_interior",
        "viewer_note": "Human-scale public-interior walk inspection start; hide exterior/landmark/roads/gameplay meshes for browser parity.",
    },
    {
        "label": "CapitolMap_Camera_WestGrounds",
        "location_m": [-360.0, -125.0, 42.0],
        "target_m": [-235.0, 0.0, 1.0],
        "fov": 52.0,
        "category": "public_exterior",
    },
    {
        "label": "CapitolMap_Camera_Rotunda",
        "location_m": [-23.0, -24.0, 7.5],
        "target_m": [0.0, 0.0, 5.0],
        "fov": 64.0,
        "category": "public_interior",
    },
    {
        "label": "CapitolMap_Camera_HouseChamber_JointSession",
        "location_m": [0.0, -108.0, 12.0],
        "target_m": [0.0, -60.0, 5.5],
        "fov": 58.0,
        "category": "public_interior",
    },
    {
        "label": "CapitolMap_Camera_SenateChamber",
        "location_m": [0.0, 108.0, 11.0],
        "target_m": [0.0, 70.0, 5.5],
        "fov": 58.0,
        "category": "public_interior",
    },
    {
        "label": "CapitolMap_Camera_Chambers_TopDown",
        "location_m": [0.0, -2.0, 92.0],
        "target_m": [0.0, -2.0, 5.4],
        "fov": 48.0,
        "category": "public_interior_topdown",
        "viewer_note": "Hide exterior/landmark meshes for unobstructed chamber inspection.",
    },
    {
        "label": "CapitolMap_Camera_HouseChamber_TopDown",
        "location_m": [0.0, -72.0, 92.0],
        "target_m": [0.0, -72.0, 5.4],
        "fov": 44.0,
        "category": "public_interior_topdown",
        "viewer_note": "Hide exterior/landmark meshes for public House Chamber plan inspection.",
    },
    {
        "label": "CapitolMap_Camera_SenateChamber_TopDown",
        "location_m": [0.0, 68.0, 92.0],
        "target_m": [0.0, 68.0, 5.4],
        "fov": 44.0,
        "category": "public_interior_topdown",
        "viewer_note": "Hide exterior/landmark meshes for public Senate Chamber plan inspection.",
    },
    {
        "label": "CapitolMap_Camera_ChamberRoleZones_TopDown",
        "location_m": [0.0, -6.0, 118.0],
        "target_m": [0.0, -6.0, 5.25],
        "fov": 42.0,
        "category": "public_interior_topdown",
        "viewer_note": "Hide exterior/landmark meshes and filter chamber role overlays for public, non-person-specific seating inspection.",
    },
    {
        "label": "CapitolMap_Camera_HouseGallery_TopDown",
        "location_m": [0.0, -101.0, 68.0],
        "target_m": [0.0, -101.0, 5.4],
        "fov": 38.0,
        "category": "public_interior_topdown",
        "viewer_note": "Hide exterior/landmark meshes for public House gallery inspection.",
    },
    {
        "label": "CapitolMap_Camera_SenateGallery_TopDown",
        "location_m": [0.0, 97.0, 68.0],
        "target_m": [0.0, 97.0, 5.4],
        "fov": 38.0,
        "category": "public_interior_topdown",
        "viewer_note": "Hide exterior/landmark meshes for public Senate gallery inspection.",
    },
    {
        "label": "CapitolMap_Camera_Interior_Cutaway",
        "location_m": [0.0, -8.0, 120.0],
        "target_m": [0.0, 0.0, 5.2],
        "fov": 64.0,
        "category": "public_interior_cutaway",
        "viewer_note": "Hide exterior/landmark/roads/gameplay meshes for unobstructed public interior inspection.",
    },
    {
        "label": "CapitolMap_Camera_PublicInterior_TopDown",
        "location_m": [0.0, 0.0, 150.0],
        "target_m": [0.0, 0.0, 5.2],
        "fov": 58.0,
        "category": "public_interior_topdown",
        "viewer_note": "Hide exterior/landmark/roads/gameplay meshes for a roof-off public interior plan review.",
    },
    {
        "label": "CapitolMap_Camera_GameplayItems",
        "location_m": [-145.0, -145.0, 9.0],
        "target_m": [-124.0, -122.0, 1.2],
        "fov": 58.0,
        "category": "gameplay_preview",
    },
]


@dataclass
class ObjWriter:
    name: str
    vertices: list[tuple[float, float, float]] = field(default_factory=list)
    texture_vertices: list[tuple[float, float]] = field(default_factory=list)
    faces: list[str] = field(default_factory=list)

    def add_vertex(self, x: float, y: float, z: float) -> int:
        self.vertices.append((x * OBJ_UNIT_SCALE, y * OBJ_UNIT_SCALE, z * OBJ_UNIT_SCALE))
        return len(self.vertices)

    def add_texture_vertex(self, u: float, v: float) -> int:
        self.texture_vertices.append((u, v))
        return len(self.texture_vertices)

    def projected_uvs(self, indexes: list[int]) -> list[tuple[float, float]]:
        points = [self.vertices[index - 1] for index in indexes]
        if len(points) < 3:
            return [(0.0, 0.0) for _ in indexes]

        ax = points[1][0] - points[0][0]
        ay = points[1][1] - points[0][1]
        az = points[1][2] - points[0][2]
        bx = points[2][0] - points[0][0]
        by = points[2][1] - points[0][1]
        bz = points[2][2] - points[0][2]
        normal = (
            ay * bz - az * by,
            az * bx - ax * bz,
            ax * by - ay * bx,
        )
        dominant_axis = max(range(3), key=lambda axis: abs(normal[axis]))
        tile_cm = UV_TILE_METERS * OBJ_UNIT_SCALE
        uvs: list[tuple[float, float]] = []
        for x, y, z in points:
            if dominant_axis == 0:
                u, v = y / tile_cm, z / tile_cm
            elif dominant_axis == 1:
                u, v = x / tile_cm, z / tile_cm
            else:
                u, v = x / tile_cm, y / tile_cm
            uvs.append((u, v))
        return uvs

    def add_face(self, indexes: list[int]) -> None:
        if len(indexes) >= 3:
            texture_indexes = [self.add_texture_vertex(u, v) for u, v in self.projected_uvs(indexes)]
            tokens = [f"{vertex_index}/{texture_index}" for vertex_index, texture_index in zip(indexes, texture_indexes)]
            self.faces.append("f " + " ".join(tokens))

    def add_group(self, name: str, material: str) -> None:
        safe = re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_") or "group"
        self.faces.append(f"g {safe}")
        self.faces.append(f"usemtl {material}")

    def add_box(
        self,
        center: tuple[float, float],
        size: tuple[float, float],
        height: float,
        z: float,
        name: str,
        material: str,
    ) -> None:
        cx, cy = center
        sx, sy = size[0] / 2.0, size[1] / 2.0
        corners = [
            (cx - sx, cy - sy),
            (cx + sx, cy - sy),
            (cx + sx, cy + sy),
            (cx - sx, cy + sy),
        ]
        self.add_extruded_polygon(corners, z, height, name, material)

    def add_beveled_box(
        self,
        center: tuple[float, float],
        size: tuple[float, float],
        height: float,
        z: float,
        name: str,
        material: str,
        bevel: float,
    ) -> None:
        cx, cy = center
        sx, sy = size[0] / 2.0, size[1] / 2.0
        inset = min(abs(bevel), sx * 0.42, sy * 0.42)
        if inset <= 0.01:
            self.add_box(center, size, height, z, name, material)
            return
        corners = [
            (cx - sx + inset, cy - sy),
            (cx + sx - inset, cy - sy),
            (cx + sx, cy - sy + inset),
            (cx + sx, cy + sy - inset),
            (cx + sx - inset, cy + sy),
            (cx - sx + inset, cy + sy),
            (cx - sx, cy + sy - inset),
            (cx - sx, cy - sy + inset),
        ]
        self.add_extruded_polygon(corners, z, height, name, material)

    def add_oriented_box(
        self,
        center: tuple[float, float],
        size: tuple[float, float],
        height: float,
        z: float,
        angle_rad: float,
        name: str,
        material: str,
    ) -> None:
        cx, cy = center
        sx, sy = size[0] / 2.0, size[1] / 2.0
        ca = math.cos(angle_rad)
        sa = math.sin(angle_rad)
        corners = []
        for lx, ly in [(-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy)]:
            corners.append((cx + lx * ca - ly * sa, cy + lx * sa + ly * ca))
        self.add_extruded_polygon(corners, z, height, name, material)

    def add_extruded_polygon(
        self,
        points: list[tuple[float, float]],
        z: float,
        height: float,
        name: str,
        material: str,
    ) -> None:
        if len(points) < 3:
            return
        if points[0] == points[-1]:
            points = points[:-1]
        if len(points) < 3:
            return

        self.add_group(name, material)
        bottom = [self.add_vertex(x, y, z) for x, y in points]
        top = [self.add_vertex(x, y, z + height) for x, y in points]
        n = len(points)
        for i in range(n):
            j = (i + 1) % n
            self.add_face([bottom[i], bottom[j], top[j], top[i]])
        self.add_face(top)
        self.add_face(list(reversed(bottom)))

    def add_flat_polygon(
        self,
        points: list[tuple[float, float]],
        z: float,
        name: str,
        material: str,
    ) -> None:
        if len(points) < 3:
            return
        if points[0] == points[-1]:
            points = points[:-1]
        self.add_group(name, material)
        verts = [self.add_vertex(x, y, z) for x, y in points]
        self.add_face(verts)

    def add_polyline_strip(
        self,
        points: list[tuple[float, float]],
        width: float,
        z: float,
        name: str,
        material: str,
    ) -> None:
        if len(points) < 2:
            return
        self.add_group(name, material)
        for index, (p0, p1) in enumerate(zip(points, points[1:])):
            x0, y0 = p0
            x1, y1 = p1
            dx = x1 - x0
            dy = y1 - y0
            length = math.hypot(dx, dy)
            if length < 0.05:
                continue
            nx = -dy / length * width / 2.0
            ny = dx / length * width / 2.0
            quad = [
                self.add_vertex(x0 + nx, y0 + ny, z),
                self.add_vertex(x1 + nx, y1 + ny, z),
                self.add_vertex(x1 - nx, y1 - ny, z),
                self.add_vertex(x0 - nx, y0 - ny, z),
            ]
            self.add_face(quad)

    def add_disk(
        self,
        center: tuple[float, float],
        radius: float,
        z: float,
        name: str,
        material: str,
        segments: int = 64,
    ) -> None:
        self.add_group(name, material)
        cx, cy = center
        center_idx = self.add_vertex(cx, cy, z)
        ring = []
        for i in range(segments):
            angle = math.tau * i / segments
            ring.append(self.add_vertex(cx + radius * math.cos(angle), cy + radius * math.sin(angle), z))
        for i in range(segments):
            self.add_face([center_idx, ring[i], ring[(i + 1) % segments]])

    def add_cylinder(
        self,
        center: tuple[float, float],
        radius: float,
        z: float,
        height: float,
        name: str,
        material: str,
        segments: int = 64,
    ) -> None:
        self.add_group(name, material)
        cx, cy = center
        bottom: list[int] = []
        top: list[int] = []
        for i in range(segments):
            angle = math.tau * i / segments
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            bottom.append(self.add_vertex(x, y, z))
            top.append(self.add_vertex(x, y, z + height))
        for i in range(segments):
            j = (i + 1) % segments
            self.add_face([bottom[i], bottom[j], top[j], top[i]])
        self.add_face(top)
        self.add_face(list(reversed(bottom)))

    def add_ring(
        self,
        center: tuple[float, float],
        outer_radius: float,
        inner_radius: float,
        z: float,
        height: float,
        name: str,
        material: str,
        segments: int = 72,
    ) -> None:
        self.add_group(name, material)
        cx, cy = center
        outer_bottom: list[int] = []
        outer_top: list[int] = []
        inner_bottom: list[int] = []
        inner_top: list[int] = []
        for i in range(segments):
            angle = math.tau * i / segments
            co = math.cos(angle)
            si = math.sin(angle)
            outer_bottom.append(self.add_vertex(cx + outer_radius * co, cy + outer_radius * si, z))
            outer_top.append(self.add_vertex(cx + outer_radius * co, cy + outer_radius * si, z + height))
            inner_bottom.append(self.add_vertex(cx + inner_radius * co, cy + inner_radius * si, z))
            inner_top.append(self.add_vertex(cx + inner_radius * co, cy + inner_radius * si, z + height))
        for i in range(segments):
            j = (i + 1) % segments
            self.add_face([outer_bottom[i], outer_bottom[j], outer_top[j], outer_top[i]])
            self.add_face([inner_bottom[j], inner_bottom[i], inner_top[i], inner_top[j]])
            self.add_face([outer_top[i], outer_top[j], inner_top[j], inner_top[i]])
            self.add_face([outer_bottom[j], outer_bottom[i], inner_bottom[i], inner_bottom[j]])

    def add_pediment(
        self,
        center: tuple[float, float],
        width: float,
        depth: float,
        z: float,
        height: float,
        name: str,
        material: str,
        orientation: str,
    ) -> None:
        """Add a simple triangular classical pediment prism.

        orientation east_west creates a triangular face across Y, extruded in X.
        orientation north_south creates a triangular face across X, extruded in Y.
        """
        self.add_group(name, material)
        cx, cy = center
        if orientation == "east_west":
            x0, x1 = cx - depth / 2.0, cx + depth / 2.0
            y0, y1 = cy - width / 2.0, cy + width / 2.0
            front = [self.add_vertex(x1, y0, z), self.add_vertex(x1, y1, z), self.add_vertex(x1, cy, z + height)]
            back = [self.add_vertex(x0, y0, z), self.add_vertex(x0, y1, z), self.add_vertex(x0, cy, z + height)]
        else:
            y0, y1 = cy - depth / 2.0, cy + depth / 2.0
            x0, x1 = cx - width / 2.0, cx + width / 2.0
            front = [self.add_vertex(x0, y1, z), self.add_vertex(x1, y1, z), self.add_vertex(cx, y1, z + height)]
            back = [self.add_vertex(x0, y0, z), self.add_vertex(x1, y0, z), self.add_vertex(cx, y0, z + height)]
        self.add_face(front)
        self.add_face(list(reversed(back)))
        self.add_face([front[0], back[0], back[1], front[1]])
        self.add_face([front[1], back[1], back[2], front[2]])
        self.add_face([front[2], back[2], back[0], front[0]])

    def add_dome(
        self,
        center: tuple[float, float],
        radius: float,
        z: float,
        height: float,
        name: str,
        material: str,
        segments: int = 72,
        rings: int = 10,
    ) -> None:
        self.add_group(name, material)
        cx, cy = center
        ring_indexes: list[list[int]] = []
        for ring in range(rings + 1):
            t = ring / rings
            theta = t * math.pi / 2.0
            rr = radius * math.cos(theta)
            zz = z + height * math.sin(theta)
            current: list[int] = []
            if ring == rings:
                current = [self.add_vertex(cx, cy, z + height)]
            else:
                for i in range(segments):
                    angle = math.tau * i / segments
                    current.append(self.add_vertex(cx + rr * math.cos(angle), cy + rr * math.sin(angle), zz))
            ring_indexes.append(current)

        for ring in range(rings):
            lower = ring_indexes[ring]
            upper = ring_indexes[ring + 1]
            for i in range(segments):
                j = (i + 1) % segments
                if ring == rings - 1:
                    self.add_face([lower[i], lower[j], upper[0]])
                else:
                    self.add_face([lower[i], lower[j], upper[j], upper[i]])

    def write(self, path: Path, mtl_name: str) -> None:
        lines = [f"mtllib {mtl_name}", f"o {self.name}"]
        for x, y, z in self.vertices:
            lines.append(f"v {x:.4f} {y:.4f} {z:.4f}")
        for u, v in self.texture_vertices:
            lines.append(f"vt {u:.6f} {v:.6f}")
        lines.extend(self.faces)
        lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")


def local_xy(lat: float, lon: float) -> tuple[float, float]:
    return ((lon - LON0) * EARTH_M_PER_DEG_LON, (lat - LAT0) * EARTH_M_PER_DEG_LAT)


def write_mtl(path: Path) -> None:
    lines: list[str] = []
    for name, color in MATERIALS.items():
        r, g, b, alpha = color
        lines.extend(
            [
                f"newmtl {name}",
                f"Kd {r:.3f} {g:.3f} {b:.3f}",
                "Ka 0.000 0.000 0.000",
                "Ks 0.050 0.050 0.050",
                f"d {alpha:.3f}",
                "illum 2",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def stable_unit_interval(*parts: object) -> float:
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.sha1(payload).digest()
    return int.from_bytes(digest[:4], "big") / 0xFFFFFFFF


def parse_numeric_tag(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", value)
    if not match:
        return None
    return float(match.group(1))


def polygon_area_m2(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    total = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1]):
        total += x0 * y1 - x1 * y0
    return abs(total) / 2.0


def point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    x, y = point
    inside = False
    for (x1, y1), (x2, y2) in zip(polygon, polygon[1:] + polygon[:1]):
        if (y1 > y) == (y2 > y):
            continue
        crossing_x = (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1
        if x < crossing_x:
            inside = not inside
    return inside


def median(values: list[float]) -> float:
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2.0


def footprint_span_m(points: list[tuple[float, float]]) -> float:
    if not points:
        return 0.0
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return max(max(xs) - min(xs), max(ys) - min(ys))


def parse_dcgis_elevation_layer(features: list[dict[str, Any]]) -> list[ElevationPoint]:
    points: list[ElevationPoint] = []
    for feature in features:
        geometry = feature.get("geometry") or {}
        attributes = feature.get("attributes") or {}
        if not all(key in geometry for key in ("x", "y")):
            continue
        elevation = attributes.get("ELEVATION")
        object_id = attributes.get("OBJECTID")
        if not isinstance(elevation, (int, float)) or not isinstance(object_id, int):
            continue
        x, y = local_xy(float(geometry["y"]), float(geometry["x"]))
        points.append(ElevationPoint(x=x, y=y, elevation_m=float(elevation), object_id=object_id))
    return points


def load_dcgis_elevation_points() -> dict[str, Any]:
    if not DCGIS_ELEVATION_SOURCE.exists():
        return {
            "available": False,
            "source_file": str(DCGIS_ELEVATION_SOURCE.relative_to(ROOT)),
            "rooftop_points": [],
            "ground_points": [],
        }
    data = json.loads(DCGIS_ELEVATION_SOURCE.read_text(encoding="utf-8"))
    layers = data.get("layers", {})
    rooftop_features = layers.get("rooftop_elevations_1999", {}).get("features", [])
    ground_features = layers.get("ground_elevation_points_1999", {}).get("features", [])
    rooftop_points = parse_dcgis_elevation_layer(rooftop_features)
    ground_points = parse_dcgis_elevation_layer(ground_features)
    return {
        "available": True,
        "source_file": str(DCGIS_ELEVATION_SOURCE.relative_to(ROOT)),
        "service_url": data.get("service_url"),
        "bbox_lonlat": data.get("bbox_lonlat"),
        "retrieved_utc": data.get("retrieved_utc"),
        "rooftop_points": rooftop_points,
        "ground_points": ground_points,
        "rooftop_point_count": len(rooftop_points),
        "ground_point_count": len(ground_points),
    }


def dcgis_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    return 0


def parse_dcgis_traffic_sign_points(features: list[dict[str, Any]]) -> list[DcgisTrafficSignPoint]:
    signs: list[DcgisTrafficSignPoint] = []
    for feature in features:
        geometry = feature.get("geometry") or {}
        attributes = feature.get("attributes") or {}
        if not all(key in geometry for key in ("x", "y")):
            continue
        x, y = local_xy(float(geometry["y"]), float(geometry["x"]))
        signs.append(
            DcgisTrafficSignPoint(
                x=x,
                y=y,
                object_id=dcgis_int(attributes.get("OBJECTID")),
                sign_code=dcgis_int(attributes.get("TRF_CODE")),
                sign_id=dcgis_int(attributes.get("TRF_ID")),
                description=str(attributes.get("DESC_") or "Other Traffic Control Sign"),
                dxf_layer=str(attributes.get("DXF_LAYER") or ""),
            )
        )
    return signs


def parse_dcgis_overhead_traffic_signs(features: list[dict[str, Any]]) -> list[DcgisOverheadTrafficSign]:
    signs: list[DcgisOverheadTrafficSign] = []
    for feature in features:
        geometry = feature.get("geometry") or {}
        attributes = feature.get("attributes") or {}
        raw_paths = geometry.get("paths") or []
        if not raw_paths:
            continue
        path_points: list[tuple[float, float]] = []
        for raw_point in raw_paths[0]:
            if len(raw_point) < 2:
                continue
            path_points.append(local_xy(float(raw_point[1]), float(raw_point[0])))
        if len(path_points) < 2:
            continue
        signs.append(
            DcgisOverheadTrafficSign(
                points=tuple(path_points),
                object_id=dcgis_int(attributes.get("OBJECTID")),
                sign_code=dcgis_int(attributes.get("OTS_CODE")),
                sign_id=dcgis_int(attributes.get("OTS_ID")),
                description=str(attributes.get("DESC_") or "Overhead Traffic Sign"),
                dxf_layer=str(attributes.get("DXF_LAYER") or ""),
            )
        )
    return signs


def load_dcgis_traffic_signs() -> dict[str, Any]:
    if not DCGIS_TRAFFIC_SIGN_SOURCE.exists():
        return {
            "available": False,
            "source_file": str(DCGIS_TRAFFIC_SIGN_SOURCE.relative_to(ROOT)),
            "traffic_sign_points": [],
            "overhead_signs": [],
        }
    data = json.loads(DCGIS_TRAFFIC_SIGN_SOURCE.read_text(encoding="utf-8"))
    layers = data.get("layers", {})
    traffic_sign_features = layers.get("other_traffic_signs_1999", {}).get("features", [])
    overhead_sign_features = layers.get("overhead_traffic_signs_1999", {}).get("features", [])
    traffic_sign_points = parse_dcgis_traffic_sign_points(traffic_sign_features)
    overhead_signs = parse_dcgis_overhead_traffic_signs(overhead_sign_features)
    return {
        "available": True,
        "source_file": str(DCGIS_TRAFFIC_SIGN_SOURCE.relative_to(ROOT)),
        "service_url": data.get("service_url"),
        "bbox_lonlat": data.get("bbox_lonlat"),
        "retrieved_utc": data.get("retrieved_utc"),
        "traffic_sign_points": traffic_sign_points,
        "overhead_signs": overhead_signs,
        "traffic_sign_point_count": len(traffic_sign_points),
        "overhead_sign_count": len(overhead_signs),
    }


def parse_dcgis_fixture_points(
    features: list[dict[str, Any]],
    source_layer: str,
    source_label: str,
    id_field: str,
    code_field: str,
    angle_field: str | None = None,
) -> list[DcgisFixturePoint]:
    fixtures: list[DcgisFixturePoint] = []
    for feature in features:
        geometry = feature.get("geometry") or {}
        attributes = feature.get("attributes") or {}
        if not all(key in geometry for key in ("x", "y")):
            continue
        x, y = local_xy(float(geometry["y"]), float(geometry["x"]))
        fixtures.append(
            DcgisFixturePoint(
                x=x,
                y=y,
                object_id=dcgis_int(attributes.get("OBJECTID")),
                feature_id=dcgis_int(attributes.get(id_field)),
                feature_code=dcgis_int(attributes.get(code_field)),
                angle_degrees=float(attributes.get(angle_field) or 0.0) if angle_field else 0.0,
                description=str(attributes.get("DESC_") or source_label),
                dxf_layer=str(attributes.get("DXF_LAYER") or ""),
                source_layer=source_layer,
                source_label=source_label,
            )
        )
    return fixtures


def load_dcgis_public_fixtures() -> dict[str, Any]:
    if not DCGIS_FIXTURE_SOURCE.exists():
        return {
            "available": False,
            "source_file": str(DCGIS_FIXTURE_SOURCE.relative_to(ROOT)),
            "fire_hydrants": [],
            "miscellaneous_points": [],
            "street_trees": [],
            "utility_poles": [],
        }
    data = json.loads(DCGIS_FIXTURE_SOURCE.read_text(encoding="utf-8"))
    layers = data.get("layers", {})
    fire_hydrants = parse_dcgis_fixture_points(
        layers.get("fire_hydrants_1999", {}).get("features", []),
        "fire_hydrants_1999",
        "Fire Hydrants - 1999",
        "WTL_ID",
        "WTL_CODE",
    )
    miscellaneous_points = parse_dcgis_fixture_points(
        layers.get("miscellaneous_points_1999", {}).get("features", []),
        "miscellaneous_points_1999",
        "Miscellaneous Points - 1999",
        "CTN_ID",
        "CTN_CODE",
        "CTN_ANGL",
    )
    street_trees = parse_dcgis_fixture_points(
        layers.get("street_trees_1999", {}).get("features", []),
        "street_trees_1999",
        "Street Trees - 1999",
        "TRE_ID",
        "TRE_CODE",
    )
    utility_poles = parse_dcgis_fixture_points(
        layers.get("utility_poles_1999", {}).get("features", []),
        "utility_poles_1999",
        "Utility Poles - 1999",
        "ELT_ID",
        "ELT_CODE",
        "ELT_ANGL",
    )
    return {
        "available": True,
        "source_file": str(DCGIS_FIXTURE_SOURCE.relative_to(ROOT)),
        "service_url": data.get("service_url"),
        "bbox_lonlat": data.get("bbox_lonlat"),
        "retrieved_utc": data.get("retrieved_utc"),
        "fire_hydrants": fire_hydrants,
        "miscellaneous_points": miscellaneous_points,
        "street_trees": street_trees,
        "utility_poles": utility_poles,
        "fire_hydrant_count": len(fire_hydrants),
        "miscellaneous_point_count": len(miscellaneous_points),
        "street_tree_count": len(street_trees),
        "utility_pole_count": len(utility_poles),
    }


def select_spaced_dcgis_points(
    points: list[DcgisFixturePoint],
    limit: int,
    min_distance_m: float,
) -> list[DcgisFixturePoint]:
    selected: list[DcgisFixturePoint] = []
    for point in sorted(points, key=lambda item: (round(item.y / 40.0), round(item.x / 40.0), item.object_id)):
        if len(selected) >= limit:
            break
        if all(math.hypot(point.x - chosen.x, point.y - chosen.y) >= min_distance_m for chosen in selected):
            selected.append(point)
    if len(selected) >= limit:
        return selected
    selected_ids = {point.object_id for point in selected}
    for point in sorted(points, key=lambda item: item.object_id):
        if len(selected) >= limit:
            break
        if point.object_id not in selected_ids:
            selected.append(point)
            selected_ids.add(point.object_id)
    return selected


def parse_dcgis_polyline_features(
    features: list[dict[str, Any]],
    source_layer: str,
    source_label: str,
    id_field: str,
    code_field: str,
) -> list[DcgisPolylineFeature]:
    parsed: list[DcgisPolylineFeature] = []
    for feature in features:
        geometry = feature.get("geometry") or {}
        attributes = feature.get("attributes") or {}
        raw_paths = geometry.get("paths") or []
        if not raw_paths:
            continue
        points: list[tuple[float, float]] = []
        for raw_point in raw_paths[0]:
            if len(raw_point) < 2:
                continue
            points.append(local_xy(float(raw_point[1]), float(raw_point[0])))
        if len(points) < 2:
            continue
        parsed.append(
            DcgisPolylineFeature(
                points=tuple(points),
                object_id=dcgis_int(attributes.get("OBJECTID")),
                feature_id=dcgis_int(attributes.get(id_field)),
                feature_code=dcgis_int(attributes.get(code_field)),
                description=str(attributes.get("SNAPS_TO") or attributes.get("DESC_") or source_label),
                dxf_layer=str(attributes.get("DXF_LAYER") or ""),
                source_layer=source_layer,
                source_label=source_label,
            )
        )
    return parsed


def parse_dcgis_polygon_features(
    features: list[dict[str, Any]],
    source_layer: str,
    source_label: str,
    id_field: str,
    code_field: str,
) -> list[DcgisPolygonFeature]:
    parsed: list[DcgisPolygonFeature] = []
    for feature in features:
        geometry = feature.get("geometry") or {}
        attributes = feature.get("attributes") or {}
        rings: list[tuple[tuple[float, float], ...]] = []
        for raw_ring in geometry.get("rings") or []:
            points: list[tuple[float, float]] = []
            for raw_point in raw_ring:
                if len(raw_point) < 2:
                    continue
                points.append(local_xy(float(raw_point[1]), float(raw_point[0])))
            if len(points) >= 3:
                rings.append(tuple(points))
        if not rings:
            continue
        parsed.append(
            DcgisPolygonFeature(
                rings=tuple(rings),
                object_id=dcgis_int(attributes.get("OBJECTID")),
                feature_id=dcgis_int(attributes.get(id_field)),
                feature_code=dcgis_int(attributes.get(code_field)),
                description=str(attributes.get("DESC_") or source_label),
                dxf_layer=str(attributes.get("DXF_LAYER") or ""),
                source_layer=source_layer,
                source_label=source_label,
            )
        )
    return parsed


def load_dcgis_ground_surfaces() -> dict[str, Any]:
    if not DCGIS_GROUND_SURFACE_SOURCE.exists():
        return {
            "available": False,
            "source_file": str(DCGIS_GROUND_SURFACE_SOURCE.relative_to(ROOT)),
            "curbs": [],
            "roads": [],
            "sidewalks": [],
        }
    data = json.loads(DCGIS_GROUND_SURFACE_SOURCE.read_text(encoding="utf-8"))
    layers = data.get("layers", {})
    curbs = parse_dcgis_polyline_features(
        layers.get("curbs_1999", {}).get("features", []),
        "curbs_1999",
        "Curbs - 1999",
        "CRBLNC_ID",
        "CRB_CODE",
    )
    roads = parse_dcgis_polygon_features(
        layers.get("roads_1999", {}).get("features", []),
        "roads_1999",
        "Roads - 1999",
        "RDS_ID",
        "RDS_CODE",
    )
    sidewalks = parse_dcgis_polygon_features(
        layers.get("sidewalks_1999", {}).get("features", []),
        "sidewalks_1999",
        "Sidewalks - 1999",
        "SDW_ID",
        "SDW_CODE",
    )
    return {
        "available": True,
        "source_file": str(DCGIS_GROUND_SURFACE_SOURCE.relative_to(ROOT)),
        "service_url": data.get("service_url"),
        "bbox_lonlat": data.get("bbox_lonlat"),
        "retrieved_utc": data.get("retrieved_utc"),
        "curbs": curbs,
        "roads": roads,
        "sidewalks": sidewalks,
        "curb_count": len(curbs),
        "road_polygon_count": len(roads),
        "sidewalk_polygon_count": len(sidewalks),
    }


def polyline_length(points: tuple[tuple[float, float], ...] | list[tuple[float, float]]) -> float:
    return sum(math.hypot(x1 - x0, y1 - y0) for (x0, y0), (x1, y1) in zip(points, points[1:]))


def polygon_feature_center(feature: DcgisPolygonFeature) -> tuple[float, float]:
    ring = feature.rings[0]
    return (sum(point[0] for point in ring) / len(ring), sum(point[1] for point in ring) / len(ring))


def polygon_feature_bounds(feature: DcgisPolygonFeature) -> tuple[float, float, float, float]:
    points = [point for ring in feature.rings for point in ring]
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return (min(xs), min(ys), max(xs), max(ys))


def select_polygon_features(
    polygons: list[DcgisPolygonFeature],
    limit: int,
    min_area_m2: float,
) -> list[DcgisPolygonFeature]:
    ranked = sorted(
        polygons,
        key=lambda feature: polygon_area_m2(list(feature.rings[0])),
        reverse=True,
    )
    return [feature for feature in ranked if polygon_area_m2(list(feature.rings[0])) >= min_area_m2][:limit]


def dcgis_height_estimate(
    footprint: list[tuple[float, float]],
    current_height: float,
    rooftop_points: list[ElevationPoint],
    ground_points: list[ElevationPoint],
) -> dict[str, Any] | None:
    if not rooftop_points or not ground_points or len(footprint) < 3:
        return None
    roof_inside = [point for point in rooftop_points if point_in_polygon((point.x, point.y), footprint)]
    if not roof_inside:
        return None

    cx = sum(point[0] for point in footprint) / len(footprint)
    cy = sum(point[1] for point in footprint) / len(footprint)
    nearby_ground = [
        point
        for point in ground_points
        if math.hypot(point.x - cx, point.y - cy) <= 120.0
    ]
    if len(nearby_ground) < 4:
        nearby_ground = sorted(ground_points, key=lambda point: math.hypot(point.x - cx, point.y - cy))[:8]
    if len(nearby_ground) < 4:
        return None

    roof_elevations = [point.elevation_m for point in roof_inside]
    ground_elevations = [point.elevation_m for point in nearby_ground]
    roof_median = median(roof_elevations)
    ground_median = median(ground_elevations)
    low_ground_count = max(3, min(6, len(ground_elevations) // 2))
    low_ground_median = median(sorted(ground_elevations)[:low_ground_count])

    for method, ground_elevation in (
        ("median_ground_delta", ground_median),
        ("low_ground_delta", low_ground_median),
    ):
        candidate_height = roof_median - ground_elevation
        if not 3.0 <= candidate_height <= 70.0:
            continue
        ratio = candidate_height / current_height if current_height > 0.1 else 0.0
        if not 0.45 <= ratio <= 2.0:
            continue
        return {
            "height_m": candidate_height,
            "method": method,
            "roof_point_count": len(roof_inside),
            "ground_point_count": len(nearby_ground),
            "roof_elevation_m": roof_median,
            "ground_elevation_m": ground_elevation,
            "nearest_ground_distance_m": round(
                min(math.hypot(point.x - cx, point.y - cy) for point in nearby_ground),
                3,
            ),
            "roof_object_ids": [point.object_id for point in roof_inside[:5]],
            "ground_object_ids": [point.object_id for point in nearby_ground[:8]],
        }
    return None


def estimate_missing_building_height(
    tags: dict[str, str],
    way_id: int,
    name: str,
    footprint_area: float,
    footprint_span: float,
    is_capitol: bool,
) -> tuple[float, str]:
    if is_capitol:
        return 28.0, "capitol_osm_placeholder_replaced"

    building = tags.get("building", "").lower()
    amenity = tags.get("amenity", "").lower()
    office = tags.get("office", "").lower()
    tourism = tags.get("tourism", "").lower()
    government = tags.get("government", "").lower()
    roof_levels = parse_numeric_tag(tags.get("roof:levels")) or 0.0
    roof_extra = min(max(roof_levels, 0.0), 3.0) * 2.6
    variation = stable_unit_interval(way_id, name, building, round(footprint_area, 1))

    low_auxiliary = {"garage", "garages", "guardhouse", "service", "shed", "roof", "carport"}
    rowhouse = {"house", "residential", "semidetached_house", "terrace", "detached"}
    institutional = (
        building in {"office", "commercial", "government", "hotel", "university", "school", "retail", "public"}
        or bool(office)
        or government in {"administrative", "government"}
        or tourism in {"hotel", "museum", "attraction"}
        or amenity in {"school", "university", "college", "courthouse", "townhall", "hospital", "place_of_worship"}
    )

    if building in low_auxiliary:
        height = 3.2 + variation * 2.4 + roof_extra
        return min(max(height, 3.0), 7.5), "footprint_type_area_estimate"

    if building in rowhouse:
        area_boost = 0.55 if footprint_area < 80.0 else 0.95 if footprint_area < 180.0 else 1.25
        stories = 1.75 + area_boost + variation * 0.65
        height = stories * 3.15 + roof_extra
        return min(max(height, 6.0), 14.5), "footprint_type_area_estimate"

    if building == "apartments":
        area_boost = min(math.log2(max(footprint_area, 120.0) / 120.0) * 0.75, 3.0)
        stories = 3.0 + area_boost + variation * 1.1
        height = stories * 3.25 + roof_extra
        return min(max(height, 10.0), 24.0), "footprint_type_area_estimate"

    if institutional:
        area_boost = min(math.log2(max(footprint_area, 120.0) / 120.0) * 0.85, 5.7)
        span_boost = min(max(footprint_span - 35.0, 0.0) / 45.0, 1.6)
        use_bonus = 1.9 if tourism == "hotel" or building == "hotel" else 1.4 if office or government else 0.9
        stories = 2.2 + area_boost + span_boost + use_bonus + variation * 1.0
        height = stories * 3.55 + roof_extra
        return min(max(height, 11.0), 54.0), "footprint_type_area_estimate"

    if amenity == "place_of_worship" or building == "church":
        area_boost = min(math.log2(max(footprint_area, 160.0) / 160.0) * 0.55, 2.0)
        height = (2.8 + area_boost + variation * 0.7) * 4.0 + roof_extra
        return min(max(height, 9.0), 24.0), "footprint_type_area_estimate"

    if footprint_area < 60.0:
        height = 4.2 + variation * 2.2 + roof_extra
    elif footprint_area < 140.0:
        height = 7.1 + variation * 3.4 + roof_extra
    elif footprint_area < 400.0:
        height = 9.2 + variation * 5.2 + roof_extra
    elif footprint_area < 900.0:
        height = 11.5 + variation * 8.5 + roof_extra
    elif footprint_area < 1800.0:
        height = 15.0 + variation * 10.5 + roof_extra
    elif footprint_area < 4000.0:
        height = 19.0 + variation * 14.0 + roof_extra
    else:
        height = 25.0 + variation * 18.0 + roof_extra
    return min(max(height, 3.0), 50.0), "footprint_type_area_estimate"


def parse_height(
    tags: dict[str, str],
    is_capitol: bool,
    way_id: int,
    name: str,
    footprint_area: float,
    footprint_span: float,
) -> tuple[float, str]:
    height = tags.get("height") or tags.get("building:height")
    if height:
        value = parse_numeric_tag(height)
        if value is not None:
            if "ft" in height.lower() or "'" in height:
                value *= 0.3048
            max_height = 120.0 if is_capitol else 70.0
            return min(max(value, 3.0), max_height), "explicit_height_tag"
    levels = parse_numeric_tag(tags.get("building:levels"))
    if levels is not None:
        return min(max(levels * 3.4, 3.0), 70.0), "building_levels_estimate"
    return estimate_missing_building_height(tags, way_id, name, footprint_area, footprint_span, is_capitol)


def building_height_accuracy_record(
    height_source: str,
    height_m: float,
    footprint_area_m2: float,
    footprint_span_m: float,
    tags: dict[str, str],
    has_height_provenance: bool,
) -> dict[str, Any]:
    """Classify height evidence so first-person visual audits can target weak estimates."""
    source_records: dict[str, dict[str, Any]] = {
        "explicit_height_tag": {
            "height_accuracy_tier": "source_tag",
            "height_confidence": 0.95,
            "height_accuracy_note": "Explicit OSM/DCGIS height tag used directly after unit parsing and sanity clamping.",
        },
        "dcgis_rooftop_ground_delta_estimate": {
            "height_accuracy_tier": "public_elevation_delta",
            "height_confidence": 0.82,
            "height_accuracy_note": (
                "Public DCGIS rooftop and ground elevation points matched the footprint; treated as a "
                "source-backed visual height estimate."
            ),
        },
        "building_levels_estimate": {
            "height_accuracy_tier": "level_count_estimate",
            "height_confidence": 0.62,
            "height_accuracy_note": "OSM building:levels converted with a conservative 3.4m-per-level visual estimate.",
        },
        "footprint_type_area_estimate": {
            "height_accuracy_tier": "heuristic_visual_estimate",
            "height_confidence": 0.38,
            "height_accuracy_note": (
                "No clean explicit, level-count, or DCGIS elevation match is available; height is a deterministic "
                "footprint/type/area visual estimate."
            ),
        },
        "capitol_osm_placeholder_replaced": {
            "height_accuracy_tier": "replaced_by_authored_landmark",
            "height_confidence": 0.1,
            "height_accuracy_note": "Original OSM footprint is not extruded; the authored Capitol landmark mesh carries the public height target.",
        },
    }
    record = dict(
        source_records.get(
            height_source,
            {
                "height_accuracy_tier": "unknown",
                "height_confidence": 0.2,
                "height_accuracy_note": "Unrecognized height source; inspect before using for realism-critical comparisons.",
            },
        )
    )
    review_priority = 0
    review_reasons: list[str] = []
    if height_source == "footprint_type_area_estimate":
        review_priority += 3
        review_reasons.append("heuristic_height")
    elif height_source == "building_levels_estimate":
        review_priority += 1
        review_reasons.append("level_count_height")
    if footprint_area_m2 >= 900.0:
        review_priority += 2
        review_reasons.append("large_footprint")
    if footprint_span_m >= 70.0:
        review_priority += 1
        review_reasons.append("large_span")
    if height_m >= 24.0 and height_source not in {"explicit_height_tag", "dcgis_rooftop_ground_delta_estimate"}:
        review_priority += 1
        review_reasons.append("tall_estimate")
    if tags.get("name") or tags.get("official_name"):
        review_priority += 1
        review_reasons.append("named_building")
    if has_height_provenance:
        review_reasons.append("source_feature_ids_recorded")
    record["height_review_priority"] = review_priority
    record["height_review_reasons"] = review_reasons
    return record


def road_width(tags: dict[str, str]) -> float:
    highway = tags.get("highway", "")
    widths = {
        "motorway": 18.0,
        "trunk": 16.0,
        "primary": 13.0,
        "secondary": 11.0,
        "tertiary": 9.0,
        "residential": 6.5,
        "service": 4.5,
        "unclassified": 6.0,
        "pedestrian": 5.0,
        "footway": 2.2,
        "cycleway": 2.4,
        "path": 2.0,
        "steps": 1.8,
    }
    return widths.get(highway, 5.0)


def is_bike_feature(tags: dict[str, str]) -> bool:
    if tags.get("highway") == "cycleway":
        return True
    for key in ("cycleway", "cycleway:left", "cycleway:right", "cycleway:both", "bicycle"):
        value = tags.get(key, "")
        if value and value not in ("no", "dismount"):
            return True
    return False


def sidewalk_sides(tags: dict[str, str]) -> list[str]:
    highway = tags.get("highway", "")
    if highway in {"footway", "path", "steps", "cycleway", "pedestrian"}:
        return []

    sidewalk = tags.get("sidewalk", "")
    if sidewalk in {"both", "yes"}:
        return ["left", "right"]
    if sidewalk in {"left", "right"}:
        return [sidewalk]
    if sidewalk in {"no", "none", "separate"}:
        return []

    sides = []
    for side in ("left", "right"):
        value = tags.get(f"sidewalk:{side}", "")
        if value and value not in {"no", "none", "separate"}:
            sides.append(side)
    return sides


def offset_polyline(points: list[tuple[float, float]], offset: float) -> list[tuple[float, float]]:
    if len(points) < 2:
        return points[:]

    normals: list[tuple[float, float]] = []
    for p0, p1 in zip(points, points[1:]):
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        length = math.hypot(dx, dy)
        if length <= 0.01:
            normals.append((0.0, 0.0))
        else:
            normals.append((-dy / length, dx / length))

    shifted: list[tuple[float, float]] = []
    for index, (x, y) in enumerate(points):
        if index == 0:
            nx, ny = normals[0]
        elif index == len(points) - 1:
            nx, ny = normals[-1]
        else:
            n0 = normals[index - 1]
            n1 = normals[index]
            nx = n0[0] + n1[0]
            ny = n0[1] + n1[1]
            length = math.hypot(nx, ny)
            if length <= 0.01:
                nx, ny = n1
            else:
                nx /= length
                ny /= length
        shifted.append((x + nx * offset, y + ny * offset))
    return shifted


def load_osm() -> tuple[dict[int, tuple[float, float]], list[dict[str, Any]], dict[str, Any]]:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    nodes: dict[int, tuple[float, float]] = {}
    ways: list[dict[str, Any]] = []
    for element in data.get("elements", []):
        if element.get("type") == "node" and "lat" in element and "lon" in element:
            nodes[int(element["id"])] = local_xy(float(element["lat"]), float(element["lon"]))
        elif element.get("type") == "way":
            ways.append(element)
    return nodes, ways, data


def way_points(way: dict[str, Any], nodes: dict[int, tuple[float, float]]) -> list[tuple[float, float]]:
    return [nodes[nid] for nid in way.get("nodes", []) if nid in nodes]


def polyline_midpoint(points: list[tuple[float, float]]) -> tuple[float, float]:
    if not points:
        return (0.0, 0.0)
    if len(points) == 1:
        return points[0]
    lengths: list[float] = []
    total = 0.0
    for p0, p1 in zip(points, points[1:]):
        length = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        lengths.append(length)
        total += length
    target = total / 2.0
    walked = 0.0
    for (p0, p1), length in zip(zip(points, points[1:]), lengths):
        if walked + length >= target and length > 0:
            t = (target - walked) / length
            return (p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t)
        walked += length
    return points[-1]


def sample_polyline(points: list[tuple[float, float]], spacing: float) -> list[tuple[float, float]]:
    samples: list[tuple[float, float]] = []
    carry = 0.0
    for p0, p1 in zip(points, points[1:]):
        x0, y0 = p0
        x1, y1 = p1
        dx = x1 - x0
        dy = y1 - y0
        length = math.hypot(dx, dy)
        if length <= 0.01:
            continue
        distance = spacing - carry if carry else spacing
        while distance < length:
            t = distance / length
            samples.append((x0 + dx * t, y0 + dy * t))
            distance += spacing
        carry = length - (distance - spacing)
    return samples


def build_exterior(nodes: dict[int, tuple[float, float]], ways: list[dict[str, Any]]) -> dict[str, Any]:
    buildings = ObjWriter("capitol_exterior_buildings")
    roads = ObjWriter("capitol_exterior_roads_bike_lanes_markers")
    dcgis_elevation_model = load_dcgis_elevation_points()
    dcgis_rooftop_points = dcgis_elevation_model.get("rooftop_points", [])
    dcgis_ground_points = dcgis_elevation_model.get("ground_points", [])
    dcgis_traffic_sign_model = load_dcgis_traffic_signs()
    dcgis_traffic_sign_points = dcgis_traffic_sign_model.get("traffic_sign_points", [])
    dcgis_overhead_signs = dcgis_traffic_sign_model.get("overhead_signs", [])
    dcgis_fixture_model = load_dcgis_public_fixtures()
    dcgis_fire_hydrants = dcgis_fixture_model.get("fire_hydrants", [])
    dcgis_miscellaneous_points = dcgis_fixture_model.get("miscellaneous_points", [])
    dcgis_street_trees = dcgis_fixture_model.get("street_trees", [])
    dcgis_utility_poles = dcgis_fixture_model.get("utility_poles", [])
    dcgis_ground_surface_model = load_dcgis_ground_surfaces()
    dcgis_curb_lines = dcgis_ground_surface_model.get("curbs", [])
    dcgis_road_polygons = dcgis_ground_surface_model.get("roads", [])
    dcgis_sidewalk_polygons = dcgis_ground_surface_model.get("sidewalks", [])
    dcgis_height_match_count = 0
    metadata: dict[str, Any] = {
        "buildings": [],
        "roads": [],
        "bike_lanes": [],
        "pedestrian_paths": [],
        "sidewalks": [],
        "curbs": [],
        "lane_edge_markings": [],
        "street_markers": [],
        "street_labels": [],
        "streetscape_props": [],
        "building_details": [],
        "grounds_details": [],
        "replaced_buildings": [],
        "height_model": {
            "primary_sources": [
                "explicit OSM/DCGIS height tags",
                "OSM building:levels estimates",
                "DCGIS Planimetrics 1999 rooftop-to-ground elevation deltas for matched missing-height footprints",
                "deterministic footprint/type/area fallback estimates",
            ],
            "dcgis_source_file": dcgis_elevation_model.get("source_file"),
            "dcgis_service_url": dcgis_elevation_model.get("service_url"),
            "dcgis_retrieved_utc": dcgis_elevation_model.get("retrieved_utc"),
            "dcgis_bbox_lonlat": dcgis_elevation_model.get("bbox_lonlat"),
            "dcgis_rooftop_points": dcgis_elevation_model.get("rooftop_point_count", 0),
            "dcgis_ground_points": dcgis_elevation_model.get("ground_point_count", 0),
            "dcgis_matched_buildings": 0,
            "source_backed_buildings": 0,
            "level_count_estimated_buildings": 0,
            "heuristic_estimated_buildings": 0,
            "height_accuracy_tiers": {},
            "height_review_targets": [],
            "target_era_height_policy": {
                "target_map_era": TARGET_MAP_ERA,
                "target_osm_date_utc": TARGET_OSM_DATE_UTC,
                "preferred_sources": [
                    "historical OSM attic extract selected by the target date",
                    "public 2019/2020-era municipal or federal datasets when licensing and coverage permit",
                    "older public DCGIS Planimetrics 1999 data as conservative supplemental evidence",
                ],
                "modern_reference_policy": (
                    "Present-day or 2024+ sources may be used only as clearly marked non-era references "
                    "for visual modeling; they should not silently replace target-era geometry."
                ),
                "note": (
                    "Height corrections should prioritize sources close to the Jan 6 / late-2020 target era. "
                    "Modern lidar-derived building datasets can be useful for comparison, but they must be "
                    "tagged as non-era references before use."
                ),
            },
            "dcgis_note": (
                "DCGIS elevation points are public 1999 planimetrics. They are used conservatively only "
                "when rooftop points fall inside the current OSM footprint and nearby ground points produce "
                "a plausible building-height delta; explicit height and level tags remain authoritative."
            ),
        },
        "traffic_sign_model": {
            "source_file": dcgis_traffic_sign_model.get("source_file"),
            "service_url": dcgis_traffic_sign_model.get("service_url"),
            "retrieved_utc": dcgis_traffic_sign_model.get("retrieved_utc"),
            "bbox_lonlat": dcgis_traffic_sign_model.get("bbox_lonlat"),
            "dcgis_traffic_sign_points": dcgis_traffic_sign_model.get("traffic_sign_point_count", 0),
            "dcgis_overhead_signs": dcgis_traffic_sign_model.get("overhead_sign_count", 0),
            "generated_public_traffic_sign_props": 0,
            "generated_public_overhead_sign_props": 0,
            "dcgis_note": (
                "Public DCGIS 1999 planimetric sign points and overhead sign lines are rendered as generic "
                "traffic-control sign props. They are public streetscape markers, not current operational guidance."
            ),
        },
        "public_fixture_model": {
            "source_file": dcgis_fixture_model.get("source_file"),
            "service_url": dcgis_fixture_model.get("service_url"),
            "retrieved_utc": dcgis_fixture_model.get("retrieved_utc"),
            "bbox_lonlat": dcgis_fixture_model.get("bbox_lonlat"),
            "dcgis_fire_hydrants": dcgis_fixture_model.get("fire_hydrant_count", 0),
            "dcgis_miscellaneous_points": dcgis_fixture_model.get("miscellaneous_point_count", 0),
            "dcgis_street_trees": dcgis_fixture_model.get("street_tree_count", 0),
            "dcgis_utility_poles": dcgis_fixture_model.get("utility_pole_count", 0),
            "generated_fire_hydrant_props": 0,
            "generated_misc_fixture_props": 0,
            "generated_street_tree_props": 0,
            "generated_utility_pole_props": 0,
            "dcgis_note": (
                "Public DCGIS 1999 planimetric hydrant, miscellaneous point, tree, and utility-pole features "
                "are rendered as generic public streetscape fixtures. Dense layers are spatially sampled for "
                "performance while retaining source counts and feature IDs in metadata."
            ),
        },
        "ground_surface_model": {
            "source_file": dcgis_ground_surface_model.get("source_file"),
            "service_url": dcgis_ground_surface_model.get("service_url"),
            "retrieved_utc": dcgis_ground_surface_model.get("retrieved_utc"),
            "bbox_lonlat": dcgis_ground_surface_model.get("bbox_lonlat"),
            "dcgis_curb_lines": dcgis_ground_surface_model.get("curb_count", 0),
            "dcgis_road_polygons": dcgis_ground_surface_model.get("road_polygon_count", 0),
            "dcgis_sidewalk_polygons": dcgis_ground_surface_model.get("sidewalk_polygon_count", 0),
            "generated_curb_line_props": 0,
            "generated_sidewalk_edge_props": 0,
            "generated_sidewalk_surface_patches": 0,
            "generated_road_edge_props": 0,
            "generated_road_surface_patches": 0,
            "dcgis_note": (
                "Public DCGIS 1999 curb polylines and road/sidewalk polygons are rendered as curb strips, "
                "edge strips, and bounded surface patches instead of full arbitrary polygon triangulation."
            ),
        },
    }
    streetlight_count = 0
    tree_count = 0
    street_sign_count = 0
    traffic_signal_count = 0

    def on_central_campus(point: tuple[float, float]) -> bool:
        x, y = point
        return -650.0 <= x <= 650.0 and -650.0 <= y <= 650.0

    def add_streetscape_record(
        name: str,
        kind: str,
        center: tuple[float, float, float],
        public_accuracy: str = "approximate_public_visual",
        extra: dict[str, Any] | None = None,
    ) -> None:
        record: dict[str, Any] = {
            "name": name,
            "kind": kind,
            "center_m": [round(center[0], 3), round(center[1], 3), round(center[2], 3)],
            "public_accuracy": public_accuracy,
        }
        if extra:
            record.update(extra)
        metadata["streetscape_props"].append(record)

    def add_building_detail_record(
        name: str,
        kind: str,
        building_id: int,
        building_name: str,
        center: tuple[float, float, float],
        extra: dict[str, Any] | None = None,
    ) -> None:
        record: dict[str, Any] = {
            "name": name,
            "kind": kind,
            "building_id": building_id,
            "building_name": building_name,
            "center_m": [round(center[0], 3), round(center[1], 3), round(center[2], 3)],
            "public_accuracy": "approximate_public_surrounding_building_visual",
        }
        if extra:
            record.update(extra)
        metadata["building_details"].append(record)

    def building_detail_building_count(kind: str) -> int:
        return len({detail.get("building_id") for detail in metadata["building_details"] if detail.get("kind") == kind})

    def add_surrounding_building_visuals(
        way_id: int,
        name: str,
        points: list[tuple[float, float]],
        height: float,
        center: tuple[float, float],
    ) -> None:
        if building_detail_building_count("surrounding_building_roofline") >= 40:
            return
        cx, cy = center
        if math.hypot(cx, cy) > 780.0:
            return
        min_x = min(point[0] for point in points)
        max_x = max(point[0] for point in points)
        min_y = min(point[1] for point in points)
        max_y = max(point[1] for point in points)
        width = max_x - min_x
        depth = max_y - min_y
        if height < 5.5 or width < 4.0 or depth < 4.0:
            return

        safe_prefix = f"surrounding_building_{way_id}"
        roof_z = height + 0.08
        buildings.add_box(((min_x + max_x) / 2.0, max_y), (width, 0.20), 0.18, roof_z, f"{safe_prefix}_north_roofline", "StepStone")
        buildings.add_box(((min_x + max_x) / 2.0, min_y), (width, 0.20), 0.18, roof_z, f"{safe_prefix}_south_roofline", "StepStone")
        buildings.add_box((max_x, (min_y + max_y) / 2.0), (0.20, depth), 0.18, roof_z, f"{safe_prefix}_east_roofline", "StepStone")
        buildings.add_box((min_x, (min_y + max_y) / 2.0), (0.20, depth), 0.18, roof_z, f"{safe_prefix}_west_roofline", "StepStone")
        add_building_detail_record(
            f"{safe_prefix}_roofline",
            "surrounding_building_roofline",
            way_id,
            name,
            (cx, cy, roof_z + 0.09),
            {"size_m": [round(width, 3), round(depth, 3)]},
        )

        cornice_z = max(2.4, height - 0.44)
        buildings.add_box(((min_x + max_x) / 2.0, max_y + 0.035), (width, 0.14), 0.16, cornice_z, f"{safe_prefix}_north_cornice_band", "StepStone")
        buildings.add_box(((min_x + max_x) / 2.0, min_y - 0.035), (width, 0.14), 0.16, cornice_z, f"{safe_prefix}_south_cornice_band", "StepStone")
        buildings.add_box((max_x + 0.035, (min_y + max_y) / 2.0), (0.14, depth), 0.16, cornice_z, f"{safe_prefix}_east_cornice_band", "StepStone")
        buildings.add_box((min_x - 0.035, (min_y + max_y) / 2.0), (0.14, depth), 0.16, cornice_z, f"{safe_prefix}_west_cornice_band", "StepStone")
        add_building_detail_record(
            f"{safe_prefix}_cornice_band",
            "surrounding_building_cornice_band",
            way_id,
            name,
            (cx, cy, cornice_z + 0.08),
            {"size_m": [round(width, 3), round(depth, 3)]},
        )

        coping_z = height + 0.32
        buildings.add_box(((min_x + max_x) / 2.0, max_y + 0.04), (width + 0.16, 0.16), 0.10, coping_z, f"{safe_prefix}_north_parapet_coping", "StepStone")
        buildings.add_box(((min_x + max_x) / 2.0, min_y - 0.04), (width + 0.16, 0.16), 0.10, coping_z, f"{safe_prefix}_south_parapet_coping", "StepStone")
        buildings.add_box((max_x + 0.04, (min_y + max_y) / 2.0), (0.16, depth + 0.16), 0.10, coping_z, f"{safe_prefix}_east_parapet_coping", "StepStone")
        buildings.add_box((min_x - 0.04, (min_y + max_y) / 2.0), (0.16, depth + 0.16), 0.10, coping_z, f"{safe_prefix}_west_parapet_coping", "StepStone")
        add_building_detail_record(
            f"{safe_prefix}_parapet_coping",
            "surrounding_building_parapet_coping",
            way_id,
            name,
            (cx, cy, coping_z + 0.05),
            {"size_m": [round(width, 3), round(depth, 3)]},
        )

        roof_inset = max(0.35, min(width, depth) * 0.06)
        roof_surface_size = (max(0.8, width - roof_inset * 2.0), max(0.8, depth - roof_inset * 2.0))
        roof_surface_z = height + 0.105
        roof_surface_name = f"{safe_prefix}_inset_roof_surface"
        buildings.add_box((cx, cy), roof_surface_size, 0.045, roof_surface_z, roof_surface_name, "RoadPatchAsphalt")
        add_building_detail_record(
            roof_surface_name,
            "surrounding_building_roof_setback_surface",
            way_id,
            name,
            (cx, cy, roof_surface_z + 0.022),
            {"size_m": [round(roof_surface_size[0], 3), round(roof_surface_size[1], 3)]},
        )

        shadow_z = height + 0.145
        inner_shadow_specs = [
            ("north", (cx, max_y - roof_inset * 0.55), (roof_surface_size[0], 0.045)),
            ("south", (cx, min_y + roof_inset * 0.55), (roof_surface_size[0], 0.045)),
            ("east", (max_x - roof_inset * 0.55, cy), (0.045, roof_surface_size[1])),
            ("west", (min_x + roof_inset * 0.55, cy), (0.045, roof_surface_size[1])),
        ]
        for shadow_face, shadow_center, shadow_size in inner_shadow_specs:
            shadow_name = f"{safe_prefix}_{shadow_face}_parapet_inner_shadow"
            buildings.add_box(shadow_center, shadow_size, 0.028, shadow_z, shadow_name, "RoadCrackSealant")
        add_building_detail_record(
            f"{safe_prefix}_parapet_inner_shadow",
            "surrounding_building_parapet_inner_shadow",
            way_id,
            name,
            (cx, cy, shadow_z + 0.014),
            {"count": len(inner_shadow_specs)},
        )

        gravel_specs = [
            ((cx - width * 0.18, cy + depth * 0.18), (max(0.9, min(width * 0.22, 4.2)), max(0.55, min(depth * 0.11, 2.0)))),
            ((cx + width * 0.20, cy - depth * 0.15), (max(0.8, min(width * 0.18, 3.6)), max(0.50, min(depth * 0.10, 1.8)))),
        ]
        for patch_index, (patch_center, patch_size) in enumerate(gravel_specs, start=1):
            patch_name = f"{safe_prefix}_roof_gravel_patch_{patch_index}"
            buildings.add_box(patch_center, patch_size, 0.026, height + 0.168, patch_name, "StoneGrimeOverlay")
            add_building_detail_record(
                patch_name,
                "surrounding_building_roof_gravel_patch",
                way_id,
                name,
                (patch_center[0], patch_center[1], height + 0.181),
                {"size_m": [round(patch_size[0], 3), round(patch_size[1], 3)]},
            )

        skylight_specs = [
            ((cx, cy + depth * 0.08), (max(1.0, min(width * 0.36, 7.8)), 0.34), "east_west"),
            ((cx - width * 0.14, cy - depth * 0.08), (0.34, max(1.0, min(depth * 0.34, 6.8))), "north_south"),
        ]
        for skylight_index, (skylight_center, skylight_size, orientation) in enumerate(skylight_specs, start=1):
            skylight_name = f"{safe_prefix}_roof_skylight_strip_{skylight_index}"
            buildings.add_box(skylight_center, skylight_size, 0.12, height + 0.20, skylight_name, "DoorGlass")
            buildings.add_box(skylight_center, (skylight_size[0] + 0.10, skylight_size[1] + 0.10), 0.045, height + 0.18, f"{skylight_name}_metal_frame", "DoorMetal")
            add_building_detail_record(
                skylight_name,
                "surrounding_building_skylight_strip",
                way_id,
                name,
                (skylight_center[0], skylight_center[1], height + 0.26),
                {"orientation": orientation, "size_m": [round(skylight_size[0], 3), round(skylight_size[1], 3)]},
            )

        penthouse_size = (max(1.4, min(width * 0.28, 6.2)), max(1.0, min(depth * 0.22, 4.8)))
        penthouse_center = (cx + width * 0.12, cy - depth * 0.22)
        penthouse_name = f"{safe_prefix}_roof_penthouse"
        buildings.add_box(penthouse_center, penthouse_size, 1.05, height + 0.25, penthouse_name, "BuildingGeneric")
        buildings.add_box((penthouse_center[0], penthouse_center[1] - penthouse_size[1] * 0.52), (penthouse_size[0] * 0.74, 0.06), 0.12, height + 0.84, f"{penthouse_name}_louver_mid", "RoadCrackSealant")
        buildings.add_box((penthouse_center[0], penthouse_center[1] - penthouse_size[1] * 0.52), (penthouse_size[0] * 0.74, 0.06), 0.12, height + 1.08, f"{penthouse_name}_louver_high", "RoadCrackSealant")
        buildings.add_box((penthouse_center[0] + penthouse_size[0] * 0.42, penthouse_center[1]), (0.08, penthouse_size[1] * 0.62), 0.64, height + 0.44, f"{penthouse_name}_access_panel", "DoorMetal")
        add_building_detail_record(
            penthouse_name,
            "surrounding_building_roof_penthouse",
            way_id,
            name,
            (penthouse_center[0], penthouse_center[1], height + 0.775),
            {"size_m": [round(penthouse_size[0], 3), round(penthouse_size[1], 3)]},
        )
        add_building_detail_record(
            f"{penthouse_name}_louvers",
            "surrounding_building_roof_penthouse_louver",
            way_id,
            name,
            (penthouse_center[0], penthouse_center[1] - penthouse_size[1] * 0.52, height + 0.96),
            {"count": 2},
        )

        corner_specs = [
            ("northwest", min_x - 0.03, max_y + 0.03, (0.22, 0.22)),
            ("northeast", max_x + 0.03, max_y + 0.03, (0.22, 0.22)),
            ("southwest", min_x - 0.03, min_y - 0.03, (0.22, 0.22)),
            ("southeast", max_x + 0.03, min_y - 0.03, (0.22, 0.22)),
        ]
        pilaster_height = max(2.2, height - 0.82)
        for corner_name, corner_x, corner_y, corner_size in corner_specs:
            pier_name = f"{safe_prefix}_{corner_name}_corner_pier"
            buildings.add_box((corner_x, corner_y), corner_size, pilaster_height, 0.20, pier_name, "StepStone")
            add_building_detail_record(
                pier_name,
                "surrounding_building_corner_pier",
                way_id,
                name,
                (corner_x, corner_y, 0.20 + pilaster_height / 2.0),
                {"corner": corner_name},
            )

        rows = max(1, min(3, int(height // 4.0)))
        cols_x = max(2, min(5, int(width // 7.0)))
        cols_y = max(2, min(5, int(depth // 7.0)))

        def add_surrounding_window_depth_details(
            window_name: str,
            center_xy: tuple[float, float],
            window_z: float,
            face_name: str,
        ) -> None:
            wx, wy = center_xy
            if face_name in {"north", "south"}:
                face_sign = 1.0 if face_name == "north" else -1.0
                face_y = wy + face_sign * 0.035
                shadow_specs = [
                    ((wx - 0.60, face_y), (0.055, 0.060), 0.98, window_z - 0.045),
                    ((wx + 0.60, face_y), (0.055, 0.060), 0.98, window_z - 0.045),
                    ((wx, face_y), (1.20, 0.060), 0.035, window_z - 0.050),
                    ((wx, face_y), (1.20, 0.060), 0.040, window_z + 0.91),
                ]
                sash_specs = [
                    ((wx - 0.30, face_y + face_sign * 0.012), (0.050, 0.052), 0.72, window_z + 0.08),
                    ((wx + 0.30, face_y + face_sign * 0.012), (0.050, 0.052), 0.72, window_z + 0.08),
                    ((wx, face_y + face_sign * 0.012), (0.88, 0.052), 0.034, window_z + 0.32),
                    ((wx, face_y + face_sign * 0.012), (0.88, 0.052), 0.034, window_z + 0.64),
                ]
                highlight_specs = [
                    ((wx - 0.22, face_y + face_sign * 0.020), (0.22, 0.038), 0.18, window_z + 0.58),
                    ((wx + 0.18, face_y + face_sign * 0.020), (0.18, 0.038), 0.14, window_z + 0.70),
                ]
            else:
                face_sign = 1.0 if face_name == "east" else -1.0
                face_x = wx + face_sign * 0.035
                shadow_specs = [
                    ((face_x, wy - 0.60), (0.060, 0.055), 0.98, window_z - 0.045),
                    ((face_x, wy + 0.60), (0.060, 0.055), 0.98, window_z - 0.045),
                    ((face_x, wy), (0.060, 1.20), 0.035, window_z - 0.050),
                    ((face_x, wy), (0.060, 1.20), 0.040, window_z + 0.91),
                ]
                sash_specs = [
                    ((face_x + face_sign * 0.012, wy - 0.30), (0.052, 0.050), 0.72, window_z + 0.08),
                    ((face_x + face_sign * 0.012, wy + 0.30), (0.052, 0.050), 0.72, window_z + 0.08),
                    ((face_x + face_sign * 0.012, wy), (0.052, 0.88), 0.034, window_z + 0.32),
                    ((face_x + face_sign * 0.012, wy), (0.052, 0.88), 0.034, window_z + 0.64),
                ]
                highlight_specs = [
                    ((face_x + face_sign * 0.020, wy - 0.22), (0.038, 0.22), 0.18, window_z + 0.58),
                    ((face_x + face_sign * 0.020, wy + 0.18), (0.038, 0.18), 0.14, window_z + 0.70),
                ]

            for detail_index, (detail_center, detail_size, detail_height, detail_z) in enumerate(shadow_specs, start=1):
                buildings.add_box(detail_center, detail_size, detail_height, detail_z, f"{window_name}_recess_shadow_{detail_index}", "RoadCrackSealant")
            for detail_index, (detail_center, detail_size, detail_height, detail_z) in enumerate(sash_specs, start=1):
                buildings.add_box(detail_center, detail_size, detail_height, detail_z, f"{window_name}_inner_sash_{detail_index}", "DoorMetal")
            for detail_index, (detail_center, detail_size, detail_height, detail_z) in enumerate(highlight_specs, start=1):
                buildings.add_box(detail_center, detail_size, detail_height, detail_z, f"{window_name}_pane_highlight_{detail_index}", "DoorGlass")

            add_building_detail_record(
                f"{window_name}_recess_shadow",
                "surrounding_building_window_recess_shadow",
                way_id,
                name,
                (wx, wy, window_z + 0.46),
                {"face": face_name, "count": len(shadow_specs)},
            )
            add_building_detail_record(
                f"{window_name}_inner_sash",
                "surrounding_building_window_inner_sash",
                way_id,
                name,
                (wx, wy, window_z + 0.46),
                {"face": face_name, "count": len(sash_specs)},
            )
            add_building_detail_record(
                f"{window_name}_pane_highlight",
                "surrounding_building_window_pane_highlight",
                way_id,
                name,
                (wx, wy, window_z + 0.70),
                {"face": face_name, "count": len(highlight_specs)},
            )

        def add_surrounding_facade_rhythm() -> None:
            floor_band_zs = [1.58 + level_index * 3.1 for level_index in range(rows + 1) if 1.58 + level_index * 3.1 < height - 0.55]
            for band_index, band_z in enumerate(floor_band_zs, start=1):
                band_specs = [
                    ("north", ((min_x + max_x) / 2.0, max_y + 0.078), (width, 0.070)),
                    ("south", ((min_x + max_x) / 2.0, min_y - 0.078), (width, 0.070)),
                    ("east", (max_x + 0.078, (min_y + max_y) / 2.0), (0.070, depth)),
                    ("west", (min_x - 0.078, (min_y + max_y) / 2.0), (0.070, depth)),
                ]
                for face_name, band_center, band_size in band_specs:
                    band_name = f"{safe_prefix}_{face_name}_floor_band_{band_index:02d}"
                    buildings.add_box(band_center, band_size, 0.055, band_z, band_name, "StepStone")
                    add_building_detail_record(
                        band_name,
                        "surrounding_building_floor_band",
                        way_id,
                        name,
                        (band_center[0], band_center[1], band_z + 0.028),
                        {"face": face_name, "level": band_index},
                    )

            pilaster_z = 0.28
            pilaster_height = max(1.8, height - 0.90)
            for col in range(cols_x + 1):
                x = min_x + width * col / cols_x
                for face_name, y_face in (("north", max_y + 0.092), ("south", min_y - 0.092)):
                    pilaster_name = f"{safe_prefix}_{face_name}_facade_pilaster_{col:02d}"
                    buildings.add_box((x, y_face), (0.095, 0.105), pilaster_height, pilaster_z, pilaster_name, "StepStone")
                    add_building_detail_record(
                        pilaster_name,
                        "surrounding_building_facade_pilaster",
                        way_id,
                        name,
                        (x, y_face, pilaster_z + pilaster_height / 2.0),
                        {"face": face_name, "sequence": col},
                    )
            for col in range(cols_y + 1):
                y = min_y + depth * col / cols_y
                for face_name, x_face in (("east", max_x + 0.092), ("west", min_x - 0.092)):
                    pilaster_name = f"{safe_prefix}_{face_name}_facade_pilaster_{col:02d}"
                    buildings.add_box((x_face, y), (0.105, 0.095), pilaster_height, pilaster_z, pilaster_name, "StepStone")
                    add_building_detail_record(
                        pilaster_name,
                        "surrounding_building_facade_pilaster",
                        way_id,
                        name,
                        (x_face, y, pilaster_z + pilaster_height / 2.0),
                        {"face": face_name, "sequence": col},
                    )

        add_surrounding_facade_rhythm()

        for row in range(rows):
            z = min(height - 1.45, 2.1 + row * 3.1)
            if z <= 1.2:
                continue
            for col in range(cols_x):
                x = min_x + width * (col + 0.5) / cols_x
                for face_name, y_face in (("north", max_y + 0.05), ("south", min_y - 0.05)):
                    window_name = f"{safe_prefix}_{face_name}_window_r{row+1:02d}_c{col+1:02d}"
                    buildings.add_box((x, y_face), (1.12, 0.08), 0.92, z, window_name, "FacadeWindow")
                    add_building_detail_record(window_name, "surrounding_building_facade_window", way_id, name, (x, y_face, z + 0.46), {"face": face_name})
                    sill_name = f"{window_name}_sill"
                    lintel_name = f"{window_name}_lintel"
                    mullion_name = f"{window_name}_mullion"
                    buildings.add_box((x, y_face), (1.34, 0.11), 0.07, z - 0.13, sill_name, "StepStone")
                    buildings.add_box((x, y_face), (1.34, 0.11), 0.08, z + 0.94, lintel_name, "StepStone")
                    buildings.add_box((x, y_face), (0.055, 0.10), 0.78, z + 0.07, mullion_name, "DoorMetal")
                    add_building_detail_record(sill_name, "surrounding_building_window_sill", way_id, name, (x, y_face, z - 0.095), {"face": face_name})
                    add_building_detail_record(lintel_name, "surrounding_building_window_lintel", way_id, name, (x, y_face, z + 0.98), {"face": face_name})
                    add_building_detail_record(mullion_name, "surrounding_building_window_mullion", way_id, name, (x, y_face, z + 0.46), {"face": face_name})
                    add_surrounding_window_depth_details(window_name, (x, y_face), z, face_name)
            for col in range(cols_y):
                y = min_y + depth * (col + 0.5) / cols_y
                for face_name, x_face in (("east", max_x + 0.05), ("west", min_x - 0.05)):
                    window_name = f"{safe_prefix}_{face_name}_window_r{row+1:02d}_c{col+1:02d}"
                    buildings.add_box((x_face, y), (0.08, 1.12), 0.92, z, window_name, "FacadeWindow")
                    add_building_detail_record(window_name, "surrounding_building_facade_window", way_id, name, (x_face, y, z + 0.46), {"face": face_name})
                    sill_name = f"{window_name}_sill"
                    lintel_name = f"{window_name}_lintel"
                    mullion_name = f"{window_name}_mullion"
                    buildings.add_box((x_face, y), (0.11, 1.34), 0.07, z - 0.13, sill_name, "StepStone")
                    buildings.add_box((x_face, y), (0.11, 1.34), 0.08, z + 0.94, lintel_name, "StepStone")
                    buildings.add_box((x_face, y), (0.10, 0.055), 0.78, z + 0.07, mullion_name, "DoorMetal")
                    add_building_detail_record(sill_name, "surrounding_building_window_sill", way_id, name, (x_face, y, z - 0.095), {"face": face_name})
                    add_building_detail_record(lintel_name, "surrounding_building_window_lintel", way_id, name, (x_face, y, z + 0.98), {"face": face_name})
                    add_building_detail_record(mullion_name, "surrounding_building_window_mullion", way_id, name, (x_face, y, z + 0.46), {"face": face_name})
                    add_surrounding_window_depth_details(window_name, (x_face, y), z, face_name)

        if abs(cx) >= abs(cy):
            x_face = min_x - 0.06 if cx > 0 else max_x + 0.06
            y = cy
            entry_size = (0.10, min(2.2, depth * 0.32))
            face = "west" if cx > 0 else "east"
        else:
            y = min_y - 0.06 if cy > 0 else max_y + 0.06
            x_face = cx
            entry_size = (min(2.2, width * 0.32), 0.10)
            face = "south" if cy > 0 else "north"
        entry_name = f"{safe_prefix}_public_entry_marker"
        buildings.add_box((x_face, y), entry_size, 1.85, 0.12, entry_name, "DoorGlass")
        add_building_detail_record(entry_name, "surrounding_building_public_entry_marker", way_id, name, (x_face, y, 1.05), {"face": face})

        frame_name = f"{safe_prefix}_public_entry_frame"
        transom_name = f"{safe_prefix}_public_entry_transom"
        threshold_name = f"{safe_prefix}_public_entry_threshold_step"
        pull_name = f"{safe_prefix}_public_entry_pull_bar"
        seam_name = f"{safe_prefix}_public_entry_center_seam"
        if face in {"east", "west"}:
            header_size = (0.16, entry_size[1] + 0.46)
            jamb_size = (0.16, 0.12)
            transom_size = (0.12, entry_size[1] * 0.84)
            threshold_size = (0.74, entry_size[1] + 0.62)
            pull_size = (0.08, 0.12)
            seam_size = (0.08, 0.035)
            side_offsets = [(0.0, -entry_size[1] / 2.0 - 0.17), (0.0, entry_size[1] / 2.0 + 0.17)]
            sill_center = (x_face, y)
        else:
            header_size = (entry_size[0] + 0.46, 0.16)
            jamb_size = (0.12, 0.16)
            transom_size = (entry_size[0] * 0.84, 0.12)
            threshold_size = (entry_size[0] + 0.62, 0.74)
            pull_size = (0.12, 0.08)
            seam_size = (0.035, 0.08)
            side_offsets = [(-entry_size[0] / 2.0 - 0.17, 0.0), (entry_size[0] / 2.0 + 0.17, 0.0)]
            sill_center = (x_face, y)
        buildings.add_box(sill_center, header_size, 0.16, 1.98, f"{frame_name}_header", "StepStone")
        for side_index, (dx, dy) in enumerate(side_offsets, start=1):
            buildings.add_box((x_face + dx, y + dy), jamb_size, 1.98, 0.10, f"{frame_name}_side_{side_index}", "StepStone")
        buildings.add_box((x_face, y), transom_size, 0.34, 1.72, transom_name, "DoorGlass")
        buildings.add_box((x_face, y), threshold_size, 0.10, 0.04, threshold_name, "StepStone")
        buildings.add_box((x_face, y), seam_size, 1.48, 0.28, seam_name, "DoorMetal")
        for pull_index, pull_offset in enumerate([-0.28, 0.28], start=1):
            if face in {"east", "west"}:
                pull_center = (x_face, y + pull_offset)
            else:
                pull_center = (x_face + pull_offset, y)
            buildings.add_box(pull_center, pull_size, 0.82, 0.62, f"{pull_name}_{pull_index}", "BrassRail")
        add_building_detail_record(frame_name, "surrounding_building_entry_frame", way_id, name, (x_face, y, 1.12), {"face": face})
        add_building_detail_record(transom_name, "surrounding_building_entry_transom", way_id, name, (x_face, y, 1.89), {"face": face})
        add_building_detail_record(threshold_name, "surrounding_building_entry_threshold", way_id, name, (x_face, y, 0.09), {"face": face})
        add_building_detail_record(pull_name, "surrounding_building_entry_pull_bar", way_id, name, (x_face, y, 1.03), {"face": face, "count": 2})
        add_building_detail_record(seam_name, "surrounding_building_entry_center_seam", way_id, name, (x_face, y, 1.02), {"face": face})

        awning_name = f"{safe_prefix}_public_entry_awning"
        sign_name = f"{safe_prefix}_wall_sign"
        sign_material = "StreetSignGreen" if way_id % 2 else "MarkerBlue"
        if face in {"east", "west"}:
            awning_size = (0.44, max(1.4, min(3.0, entry_size[1] * 1.22)))
            sign_size = (0.08, max(0.95, min(2.2, entry_size[1] * 0.88)))
        else:
            awning_size = (max(1.4, min(3.0, entry_size[0] * 1.22)), 0.44)
            sign_size = (max(0.95, min(2.2, entry_size[0] * 0.88)), 0.08)
        buildings.add_box((x_face, y), awning_size, 0.18, 2.05, awning_name, "DoorMetal")
        buildings.add_box((x_face, y), sign_size, 0.38, 2.42, sign_name, sign_material)
        add_building_detail_record(
            awning_name,
            "surrounding_building_awning",
            way_id,
            name,
            (x_face, y, 2.14),
            {"face": face},
        )
        add_building_detail_record(
            sign_name,
            "surrounding_building_wall_sign",
            way_id,
            name,
            (x_face, y, 2.61),
            {"face": face, "material": sign_material},
        )

        front_span = depth if face in {"east", "west"} else width
        entry_lateral_span = entry_size[1] if face in {"east", "west"} else entry_size[0]

        def face_point(lateral_offset: float, outward_offset: float = 0.0) -> tuple[float, float]:
            if face == "west":
                return (x_face - outward_offset, y + lateral_offset)
            if face == "east":
                return (x_face + outward_offset, y + lateral_offset)
            if face == "south":
                return (x_face + lateral_offset, y - outward_offset)
            return (x_face + lateral_offset, y + outward_offset)

        def face_size(lateral_length: float, wall_depth: float) -> tuple[float, float]:
            if face in {"east", "west"}:
                return (wall_depth, lateral_length)
            return (lateral_length, wall_depth)

        def add_face_detail_box(
            detail_name: str,
            lateral_offset: float,
            outward_offset: float,
            lateral_length: float,
            wall_depth: float,
            box_height: float,
            z: float,
            material: str,
        ) -> tuple[float, float]:
            detail_center = face_point(lateral_offset, outward_offset)
            buildings.add_box(detail_center, face_size(lateral_length, wall_depth), box_height, z, detail_name, material)
            return detail_center

        stoop_lateral = min(max(entry_lateral_span + 0.86, 1.55), max(1.55, front_span * 0.54))
        stoop_center = add_face_detail_box(
            f"{safe_prefix}_entry_stoop_slab",
            0.0,
            0.50,
            stoop_lateral,
            0.92,
            0.075,
            0.015,
            "StepStone",
        )
        add_face_detail_box(f"{safe_prefix}_entry_stoop_front_lip", 0.0, 0.98, stoop_lateral * 0.94, 0.16, 0.055, 0.012, "StoneGrimeOverlay")
        add_building_detail_record(
            f"{safe_prefix}_entry_stoop_slab",
            "surrounding_building_entry_stoop_slab",
            way_id,
            name,
            (stoop_center[0], stoop_center[1], 0.052),
            {"face": face, "size_m": [round(stoop_lateral, 3), 0.92]},
        )

        window_offset = min(front_span * 0.28, max(1.15, entry_lateral_span * 0.66 + 0.72))
        window_lateral = min(1.35, max(0.82, front_span * 0.16))
        ground_floor_offsets = [-window_offset, window_offset]
        for panel_index, lateral_offset in enumerate(ground_floor_offsets, start=1):
            panel_name = f"{safe_prefix}_ground_floor_window_panel_{panel_index}"
            panel_center = add_face_detail_box(panel_name, lateral_offset, 0.066, window_lateral, 0.070, 1.18, 0.54, "FacadeWindow")
            add_building_detail_record(
                panel_name,
                "surrounding_building_ground_floor_window_panel",
                way_id,
                name,
                (panel_center[0], panel_center[1], 1.13),
                {"face": face, "sequence": panel_index},
            )
            for slat_index in range(5):
                slat_z = 0.74 + slat_index * 0.18
                add_face_detail_box(
                    f"{panel_name}_blind_slat_{slat_index+1:02d}",
                    lateral_offset,
                    0.096,
                    window_lateral * 0.78,
                    0.044,
                    0.026,
                    slat_z,
                    "LaneMarkingWhite",
                )
            add_building_detail_record(
                f"{panel_name}_blind_slats",
                "surrounding_building_ground_floor_blind",
                way_id,
                name,
                (panel_center[0], panel_center[1], 1.11),
                {"face": face, "sequence": panel_index, "slat_count": 5},
            )
            sill_center = add_face_detail_box(
                f"{panel_name}_stone_sill",
                lateral_offset,
                0.082,
                window_lateral + 0.22,
                0.105,
                0.070,
                0.42,
                "StepStone",
            )
            add_building_detail_record(
                f"{panel_name}_stone_sill",
                "surrounding_building_ground_floor_sill",
                way_id,
                name,
                (sill_center[0], sill_center[1], 0.455),
                {"face": face, "sequence": panel_index},
            )

        for grime_index, lateral_offset in enumerate([-front_span * 0.31, front_span * 0.31], start=1):
            patch_length = min(2.35, max(0.90, front_span * (0.12 + 0.015 * grime_index)))
            patch_center = add_face_detail_box(
                f"{safe_prefix}_street_level_wall_grime_patch_{grime_index}",
                lateral_offset,
                0.101,
                patch_length,
                0.048,
                0.58 + 0.10 * grime_index,
                0.08,
                "StoneGrimeOverlay",
            )
            add_building_detail_record(
                f"{safe_prefix}_street_level_wall_grime_patch_{grime_index}",
                "surrounding_building_wall_grime_patch",
                way_id,
                name,
                (patch_center[0], patch_center[1], 0.38 + 0.05 * grime_index),
                {"face": face, "sequence": grime_index},
            )

        for vent_index, lateral_offset in enumerate([-front_span * 0.40, front_span * 0.40], start=1):
            vent_center = face_point(lateral_offset, 0.104)
            for slat_index in range(4):
                add_face_detail_box(
                    f"{safe_prefix}_facade_vent_grille_{vent_index}_slat_{slat_index+1}",
                    lateral_offset,
                    0.104,
                    0.72,
                    0.042,
                    0.026,
                    0.36 + slat_index * 0.085,
                    "RoadCrackSealant",
                )
            add_building_detail_record(
                f"{safe_prefix}_facade_vent_grille_{vent_index}",
                "surrounding_building_facade_vent_grille",
                way_id,
                name,
                (vent_center[0], vent_center[1], 0.50),
                {"face": face, "sequence": vent_index, "slat_count": 4},
            )

        meter_offset = -min(front_span * 0.44, max(1.60, window_offset + 0.58))
        meter_backer_center = add_face_detail_box(
            f"{safe_prefix}_utility_meter_backer",
            meter_offset,
            0.110,
            0.92,
            0.070,
            0.72,
            0.54,
            "DoorMetal",
        )
        for meter_index, meter_lateral_delta in enumerate([-0.27, 0.0, 0.27], start=1):
            meter_center = add_face_detail_box(
                f"{safe_prefix}_utility_meter_{meter_index}",
                meter_offset + meter_lateral_delta,
                0.142,
                0.16,
                0.082,
                0.20,
                0.80,
                "FacadeWindow",
            )
            add_face_detail_box(
                f"{safe_prefix}_utility_meter_{meter_index}_conduit",
                meter_offset + meter_lateral_delta,
                0.132,
                0.045,
                0.052,
                0.74,
                0.16,
                "DoorMetal",
            )
        add_building_detail_record(
            f"{safe_prefix}_utility_meter_bank",
            "surrounding_building_utility_meter_bank",
            way_id,
            name,
            (meter_backer_center[0], meter_backer_center[1], 0.90),
            {"face": face, "meter_count": 3},
        )

        service_offset = min(front_span * 0.43, max(1.55, window_offset + 0.52))
        service_center = add_face_detail_box(
            f"{safe_prefix}_street_level_service_panel",
            service_offset,
            0.116,
            0.62,
            0.072,
            0.98,
            0.58,
            "DoorMetal",
        )
        add_face_detail_box(f"{safe_prefix}_street_level_service_panel_handle", service_offset + 0.22, 0.152, 0.055, 0.045, 0.18, 1.00, "BrassRail")
        add_building_detail_record(
            f"{safe_prefix}_street_level_service_panel",
            "surrounding_building_service_panel",
            way_id,
            name,
            (service_center[0], service_center[1], 1.07),
            {"face": face},
        )

        plaque_lateral = min(entry_lateral_span * 0.62 + 0.44, front_span * 0.30)
        plaque_center = add_face_detail_box(
            f"{safe_prefix}_address_plaque",
            plaque_lateral,
            0.126,
            0.52,
            0.048,
            0.24,
            2.18,
            "BrassRail",
        )
        for bar_index, bar_z in enumerate([2.25, 2.32], start=1):
            add_face_detail_box(
                f"{safe_prefix}_address_plaque_mark_{bar_index}",
                plaque_lateral,
                0.154,
                0.34 - 0.06 * (bar_index - 1),
                0.034,
                0.020,
                bar_z,
                "RoadCrackSealant",
            )
        add_building_detail_record(
            f"{safe_prefix}_address_plaque",
            "surrounding_building_address_plaque",
            way_id,
            name,
            (plaque_center[0], plaque_center[1], 2.30),
            {"face": face},
        )

        downspout_limit = max(0.45, front_span / 2.0 - 0.28)
        downspout_offsets = [-downspout_limit, downspout_limit]
        downspout_height = max(2.1, min(height - 0.65, 5.20))
        for pipe_index, lateral_offset in enumerate(downspout_offsets, start=1):
            pipe_center = add_face_detail_box(
                f"{safe_prefix}_downspout_pipe_{pipe_index}",
                lateral_offset,
                0.116,
                0.075,
                0.075,
                downspout_height,
                0.18,
                "DoorMetal",
            )
            add_face_detail_box(
                f"{safe_prefix}_downspout_elbow_{pipe_index}",
                lateral_offset,
                0.28,
                0.26,
                0.070,
                0.080,
                0.20,
                "DoorMetal",
            )
            add_building_detail_record(
                f"{safe_prefix}_downspout_pipe_{pipe_index}",
                "surrounding_building_downspout_pipe",
                way_id,
                name,
                (pipe_center[0], pipe_center[1], 0.18 + downspout_height / 2.0),
                {"face": face, "sequence": pipe_index},
            )

        for unit_index, (ox, oy) in enumerate([(-0.18, -0.12), (0.20, 0.16)], start=1):
            unit_center = (cx + width * ox, cy + depth * oy)
            unit_size = (max(0.8, min(3.8, width * 0.22)), max(0.65, min(2.4, depth * 0.18)))
            unit_name = f"{safe_prefix}_rooftop_detail_{unit_index}"
            buildings.add_box(unit_center, unit_size, 0.55, height + 0.18, unit_name, "BuildingGeneric")
            hatch_name = f"{unit_name}_access_hatch_lid"
            buildings.add_box((unit_center[0] + unit_size[0] * 0.18, unit_center[1] - unit_size[1] * 0.18), (unit_size[0] * 0.44, unit_size[1] * 0.36), 0.045, height + 0.77, hatch_name, "DoorMetal")
            add_building_detail_record(unit_name, "surrounding_building_rooftop_detail", way_id, name, (unit_center[0], unit_center[1], height + 0.46))
            add_building_detail_record(
                hatch_name,
                "surrounding_building_roof_access_hatch",
                way_id,
                name,
                (unit_center[0] + unit_size[0] * 0.18, unit_center[1] - unit_size[1] * 0.18, height + 0.79),
            )

        for unit_index, (ox, oy) in enumerate([(0.10, -0.28), (-0.28, 0.22)], start=1):
            unit_center = (cx + width * ox, cy + depth * oy)
            unit_size = (max(0.72, min(2.7, width * 0.16)), max(0.58, min(1.85, depth * 0.14)))
            unit_name = f"{safe_prefix}_rooftop_mechanical_{unit_index}"
            buildings.add_box(unit_center, unit_size, 0.42, height + 0.76, unit_name, "DoorMetal")
            buildings.add_cylinder(unit_center, max(0.18, min(unit_size) * 0.24), height + 1.20, 0.055, f"{unit_name}_fan_cap", "FacadeWindow", segments=12)
            for louver_index, louver_z in enumerate([height + 0.90, height + 1.02, height + 1.14], start=1):
                buildings.add_box((unit_center[0], unit_center[1] - unit_size[1] * 0.52), (unit_size[0] * 0.72, 0.055), 0.032, louver_z, f"{unit_name}_louver_{louver_index}", "RoadCrackSealant")
            pipe_center = (unit_center[0] + unit_size[0] * 0.45, unit_center[1] + unit_size[1] * 0.42)
            stack_name = f"{unit_name}_pipe_stack"
            vent_cap_name = f"{unit_name}_gooseneck_vent_cap"
            buildings.add_cylinder(pipe_center, 0.09, height + 0.76, 0.78, stack_name, "DoorMetal", segments=10)
            buildings.add_box((pipe_center[0], pipe_center[1] + 0.09), (0.28, 0.11), 0.10, height + 1.47, vent_cap_name, "DoorMetal")
            add_building_detail_record(
                unit_name,
                "surrounding_building_rooftop_mechanical",
                way_id,
                name,
                (unit_center[0], unit_center[1], height + 0.97),
            )
            add_building_detail_record(
                f"{unit_name}_louvers",
                "surrounding_building_rooftop_louver",
                way_id,
                name,
                (unit_center[0], unit_center[1] - unit_size[1] * 0.52, height + 1.02),
                {"count": 3},
            )
            add_building_detail_record(stack_name, "surrounding_building_roof_pipe_stack", way_id, name, (pipe_center[0], pipe_center[1], height + 1.15))
            add_building_detail_record(vent_cap_name, "surrounding_building_roof_vent_cap", way_id, name, (pipe_center[0], pipe_center[1] + 0.09, height + 1.52))

        conduit_specs = [
            ("north_south", (cx - width * 0.22, cy), (0.08, max(1.4, min(depth * 0.46, 5.2)))),
            ("east_west", (cx, cy + depth * 0.24), (max(1.4, min(width * 0.46, 5.2)), 0.08)),
        ]
        for conduit_index, (orientation, conduit_center, conduit_size) in enumerate(conduit_specs, start=1):
            conduit_name = f"{safe_prefix}_roof_conduit_run_{conduit_index}"
            buildings.add_box(conduit_center, conduit_size, 0.045, height + 0.96, conduit_name, "DoorMetal")
            add_building_detail_record(
                conduit_name,
                "surrounding_building_roof_conduit",
                way_id,
                name,
                (conduit_center[0], conduit_center[1], height + 0.985),
                {"orientation": orientation, "size_m": [round(conduit_size[0], 3), round(conduit_size[1], 3)]},
            )

    def add_streetlight(name: str, point: tuple[float, float], side_sign: float) -> None:
        x, y = point
        lamp_x = x + side_sign * 0.62
        roads.add_cylinder((x, y), 0.075, 0.10, 5.1, f"{name}_pole", "StreetLightPole", segments=10)
        roads.add_cylinder((x, y), 0.18, 0.08, 0.08, f"{name}_flanged_base", "BollardMetal", segments=12)
        roads.add_cylinder((x, y), 0.095, 4.36, 0.12, f"{name}_upper_collar", "BrassRail", segments=10)
        roads.add_box((x + side_sign * 0.30, y), (0.62, 0.10), 0.08, 5.05, f"{name}_arm", "StreetLightPole")
        roads.add_box((x + side_sign * 0.52, y), (0.30, 0.18), 0.10, 4.88, f"{name}_lamp_hood", "LightFixtureMetal")
        roads.add_cylinder((lamp_x, y), 0.18, 4.62, 0.34, f"{name}_warm_glass", "StreetLightGlass", segments=12)
        roads.add_cylinder((lamp_x, y), 0.20, 4.56, 0.045, f"{name}_lower_lens_trim", "BrassRail", segments=12)
        add_streetscape_record(
            name,
            "streetlight",
            (x, y, 2.7),
            extra={
                "light_m": [round(lamp_x, 3), round(y, 3), 4.78],
                "intensity": 420.0,
                "attenuation_radius_m": 9.0,
                "color": [1.0, 0.82, 0.55],
            },
        )
        add_streetscape_record(
            f"{name}_fixture_detail",
            "streetlight_fixture_detail",
            (x + side_sign * 0.42, y, 4.78),
            extra={"side_sign": side_sign, "fixture_parts": ["flanged_base", "upper_collar", "lamp_hood", "lens_trim"]},
        )

    def add_tree(name: str, point: tuple[float, float]) -> None:
        x, y = point
        roads.add_cylinder((x, y), 0.16, 0.08, 1.9, f"{name}_trunk", "TreeTrunk", segments=10)
        roads.add_cylinder((x, y), 1.05, 1.55, 1.0, f"{name}_lower_canopy", "TreeCanopy", segments=18)
        roads.add_cylinder((x, y), 0.82, 2.18, 0.9, f"{name}_upper_canopy", "TreeCanopy", segments=18)
        roads.add_cylinder((x, y), 1.18, 0.06, 0.18, f"{name}_planter_ring", "PlanterStone", segments=18)
        add_streetscape_record(name, "tree_planter", (x, y, 1.75))

    def add_street_sign(name: str, point: tuple[float, float], text: str) -> None:
        x, y = point
        roads.add_cylinder((x, y), 0.045, 0.10, 2.15, f"{name}_post", "StreetLightPole", segments=8)
        roads.add_box((x, y), (1.55, 0.12), 0.44, 1.92, f"{name}_blade", "StreetSignGreen")
        for stroke_index, (offset, width) in enumerate([(-0.42, 0.34), (-0.12, 0.24), (0.18, 0.30), (0.46, 0.18)], start=1):
            roads.add_box((x + offset, y - 0.075), (width, 0.026), 0.035, 2.13, f"{name}_abstract_text_stroke_{stroke_index}", "LaneMarkingWhite")
        add_streetscape_record(name, "street_name_sign", (x, y, 1.45), extra={"label": text[:80]})
        add_streetscape_record(
            f"{name}_text_strokes",
            "street_name_sign_text_strokes",
            (x, y - 0.075, 2.15),
            extra={"stroke_count": 4, "label_source": text[:80]},
        )

    def add_traffic_signal(name: str, point: tuple[float, float]) -> None:
        x, y = point
        arm_sign = 1.0 if x < 0.0 else -1.0
        roads.add_cylinder((x, y), 0.07, 0.08, 4.05, f"{name}_pole", "StreetLightPole", segments=10)
        roads.add_cylinder((x, y), 0.17, 0.08, 0.08, f"{name}_base_flange", "BollardMetal", segments=12)
        roads.add_box((x + arm_sign * 0.72, y), (1.44, 0.09), 0.09, 4.02, f"{name}_mast_arm", "StreetLightPole")
        roads.add_box((x + arm_sign * 1.36, y), (0.16, 0.44), 0.10, 3.86, f"{name}_hanging_bracket", "StreetLightPole")
        roads.add_box((x, y + 0.075), (0.55, 0.08), 1.42, 2.98, f"{name}_signal_backplate", "TrafficSignalHousing")
        roads.add_box((x, y), (0.44, 0.28), 1.24, 3.05, f"{name}_signal_head", "TrafficSignalHousing")
        roads.add_box((x, y - 0.15), (0.20, 0.055), 0.18, 3.95, f"{name}_red_lens", "TrafficSignalRed")
        roads.add_box((x, y - 0.15), (0.20, 0.055), 0.18, 3.58, f"{name}_yellow_lens", "TrafficSignalYellow")
        roads.add_box((x, y - 0.15), (0.20, 0.055), 0.18, 3.21, f"{name}_green_lens", "TrafficSignalGreen")
        for hood_index, z in enumerate([3.95, 3.58, 3.21], start=1):
            roads.add_box((x, y - 0.205), (0.26, 0.08), 0.055, z + 0.10, f"{name}_signal_louver_hood_{hood_index}", "TrafficSignalHousing")
        roads.add_box((x - arm_sign * 0.18, y - 0.13), (0.34, 0.075), 0.48, 2.28, f"{name}_ped_countdown_housing", "TrafficSignalHousing")
        roads.add_box((x - arm_sign * 0.18, y - 0.18), (0.20, 0.040), 0.12, 2.54, f"{name}_walk_icon_face", "LaneMarkingWhite")
        roads.add_box((x - arm_sign * 0.18, y - 0.185), (0.18, 0.035), 0.08, 2.36, f"{name}_countdown_digit_bar_top", "TrafficSignalYellow")
        roads.add_box((x - arm_sign * 0.18, y - 0.185), (0.12, 0.035), 0.08, 2.23, f"{name}_countdown_digit_bar_bottom", "TrafficSignalYellow")
        roads.add_box((x + arm_sign * 0.16, y + 0.11), (0.20, 0.075), 0.28, 1.05, f"{name}_pushbutton_plate", "TrafficSignalHousing")
        roads.add_cylinder((x + arm_sign * 0.16, y + 0.155), 0.040, 1.19, 0.025, f"{name}_pushbutton_marker", "SignalMarker", segments=8)
        add_streetscape_record(name, "traffic_signal_prop", (x, y, 2.5))
        add_streetscape_record(
            f"{name}_mast_arm_detail",
            "traffic_signal_mast_arm",
            (x + arm_sign * 0.72, y, 4.06),
            extra={"arm_sign": arm_sign},
        )
        add_streetscape_record(
            f"{name}_backplate_detail",
            "traffic_signal_backplate",
            (x, y + 0.075, 3.70),
            extra={"louver_hoods": 3},
        )
        add_streetscape_record(
            f"{name}_ped_countdown_detail",
            "traffic_signal_pedestrian_countdown",
            (x - arm_sign * 0.18, y - 0.13, 2.52),
            extra={"generic_face": "walk_icon_and_countdown_bars", "arm_sign": arm_sign},
        )
        add_streetscape_record(
            f"{name}_pushbutton_detail",
            "traffic_signal_pushbutton_plate",
            (x + arm_sign * 0.16, y + 0.12, 1.19),
            extra={"generic_button_marker": True, "arm_sign": arm_sign},
        )

    def add_crosswalk_stripes(name: str, point: tuple[float, float]) -> None:
        x, y = point
        for stripe in range(4):
            sx = x + (stripe - 1.5) * 0.46
            roads.add_box((sx, y), (0.24, 2.35), 0.035, 0.14, f"{name}_stripe_{stripe+1}", "CrosswalkWhite")

    def add_stop_bar(name: str, center: tuple[float, float], orientation: str) -> None:
        size = (9.6, 0.44) if orientation == "east_west" else (0.44, 9.6)
        roads.add_box(center, size, 0.035, 0.18, name, "LaneMarkingWhite")
        add_streetscape_record(name, "road_stop_bar", (center[0], center[1], 0.22), extra={"orientation": orientation})

    def add_lane_arrow(name: str, center: tuple[float, float], direction: str) -> None:
        x, y = center
        if direction in {"north", "south"}:
            sign = 1.0 if direction == "north" else -1.0
            roads.add_box((x, y - sign * 0.62), (0.36, 1.35), 0.035, 0.185, f"{name}_stem", "LaneMarkingWhite")
            head = [(x, y + sign * 1.08), (x - 0.70, y + sign * 0.12), (x + 0.70, y + sign * 0.12)]
        else:
            sign = 1.0 if direction == "east" else -1.0
            roads.add_box((x - sign * 0.62, y), (1.35, 0.36), 0.035, 0.185, f"{name}_stem", "LaneMarkingWhite")
            head = [(x + sign * 1.08, y), (x + sign * 0.12, y - 0.70), (x + sign * 0.12, y + 0.70)]
        roads.add_extruded_polygon(head, 0.185, 0.035, f"{name}_arrow_head", "LaneMarkingWhite")
        add_streetscape_record(name, "lane_direction_arrow", (x, y, 0.22), extra={"direction": direction})

    def add_bike_symbol(name: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        if orientation == "north_south":
            wheel_a = (x, y - 0.72)
            wheel_b = (x, y + 0.72)
            roads.add_box((x, y), (0.14, 1.25), 0.032, 0.19, f"{name}_frame_bar", "LaneMarkingWhite")
            roads.add_box((x, y + 1.18), (0.78, 0.12), 0.032, 0.19, f"{name}_handlebar", "LaneMarkingWhite")
        else:
            wheel_a = (x - 0.72, y)
            wheel_b = (x + 0.72, y)
            roads.add_box((x, y), (1.25, 0.14), 0.032, 0.19, f"{name}_frame_bar", "LaneMarkingWhite")
            roads.add_box((x + 1.18, y), (0.12, 0.78), 0.032, 0.19, f"{name}_handlebar", "LaneMarkingWhite")
        roads.add_ring(wheel_a, 0.34, 0.25, 0.19, 0.03, f"{name}_wheel_a", "LaneMarkingWhite", segments=18)
        roads.add_ring(wheel_b, 0.34, 0.25, 0.19, 0.03, f"{name}_wheel_b", "LaneMarkingWhite", segments=18)
        add_streetscape_record(name, "bike_symbol", (x, y, 0.22), extra={"orientation": orientation})

    def add_curb_ramp_visual(name: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        size = (2.2, 1.3) if orientation == "east_west" else (1.3, 2.2)
        roads.add_box(center, size, 0.045, 0.105, f"{name}_concrete_slope", "SidewalkConcrete")
        roads.add_box(center, (size[0] * 0.62, size[1] * 0.36), 0.026, 0.155, f"{name}_tactile_panel", "LaneMarkingYellow")
        add_streetscape_record(name, "curb_ramp_visual", (x, y, 0.16), extra={"orientation": orientation})

    def add_public_wayfinding_sign(name: str, center: tuple[float, float], label: str, orientation: str) -> None:
        x, y = center
        roads.add_cylinder((x, y), 0.055, 0.10, 2.45, f"{name}_post", "StreetLightPole", segments=8)
        panel_size = (2.2, 0.14) if orientation == "east_west" else (0.14, 2.2)
        roads.add_box((x, y), panel_size, 0.78, 2.05, f"{name}_green_panel", "StreetSignGreen")
        roads.add_box((x, y), (panel_size[0] * 0.72, panel_size[1] * 0.72), 0.12, 2.23, f"{name}_white_arrow_marker", "LaneMarkingWhite")
        add_streetscape_record(name, "public_wayfinding_sign", (x, y, 1.55), extra={"label": label, "orientation": orientation})

    def add_public_bike_rack(name: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        if orientation == "east_west":
            roads.add_box((x, y), (2.35, 0.10), 0.10, 0.18, f"{name}_ground_rail", "BollardMetal")
            for idx, offset in enumerate([-0.78, 0.0, 0.78], start=1):
                roads.add_box((x + offset, y), (0.10, 0.52), 0.74, 0.22, f"{name}_u_loop_{idx:02d}", "BollardMetal")
        else:
            roads.add_box((x, y), (0.10, 2.35), 0.10, 0.18, f"{name}_ground_rail", "BollardMetal")
            for idx, offset in enumerate([-0.78, 0.0, 0.78], start=1):
                roads.add_box((x, y + offset), (0.52, 0.10), 0.74, 0.22, f"{name}_u_loop_{idx:02d}", "BollardMetal")
        add_streetscape_record(name, "public_bike_rack", (x, y, 0.58), extra={"orientation": orientation})

    def add_public_trash_receptacle(name: str, center: tuple[float, float]) -> None:
        x, y = center
        roads.add_cylinder((x, y), 0.30, 0.10, 0.78, f"{name}_dark_body", "TrafficSignalHousing", segments=14)
        roads.add_cylinder((x, y), 0.32, 0.88, 0.08, f"{name}_metal_lid", "DoorMetal", segments=14)
        roads.add_box((x, y), (0.30, 0.055), 0.04, 0.95, f"{name}_slot_marker", "LaneMarkingWhite")
        add_streetscape_record(name, "public_trash_receptacle", (x, y, 0.52))

    def add_bus_stop_shelter(name: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        if orientation == "east_west":
            panel_size = (3.2, 0.10)
            roof_size = (3.6, 1.2)
            post_offsets = [(-1.45, -0.42), (1.45, -0.42), (-1.45, 0.42), (1.45, 0.42)]
            bench_size = (2.45, 0.28)
            bench_center = (x, y + 0.32)
            ad_size = (0.70, 0.08)
            ad_center = (x - 1.05, y - 0.07)
        else:
            panel_size = (0.10, 3.2)
            roof_size = (1.2, 3.6)
            post_offsets = [(-0.42, -1.45), (-0.42, 1.45), (0.42, -1.45), (0.42, 1.45)]
            bench_size = (0.28, 2.45)
            bench_center = (x + 0.32, y)
            ad_size = (0.08, 0.70)
            ad_center = (x - 0.07, y - 1.05)
        for idx, (dx, dy) in enumerate(post_offsets, start=1):
            roads.add_cylinder((x + dx, y + dy), 0.055, 0.10, 2.15, f"{name}_post_{idx:02d}", "StreetLightPole", segments=8)
        roads.add_box((x, y), panel_size, 1.28, 0.42, f"{name}_glass_back_panel", "DoorGlass")
        roads.add_box((x, y), roof_size, 0.10, 2.24, f"{name}_flat_roof", "DoorMetal")
        roads.add_box(bench_center, bench_size, 0.14, 0.48, f"{name}_bench_seat", "BenchWood")
        roads.add_box(bench_center, (bench_size[0] * 0.94, bench_size[1] * 0.94), 0.08, 0.62, f"{name}_bench_back", "BenchWood")
        roads.add_box(ad_center, ad_size, 0.72, 1.04, f"{name}_route_ad_panel", "MarkerBlue")
        roads.add_box(ad_center, (ad_size[0] * 0.70, ad_size[1] * 0.70), 0.05, 1.58, f"{name}_route_ad_text_marker", "LaneMarkingWhite")
        add_streetscape_record(name, "public_bus_stop_shelter", (x, y, 1.35), extra={"orientation": orientation})
        add_streetscape_record(
            f"{name}_bench_detail",
            "bus_stop_shelter_bench",
            (bench_center[0], bench_center[1], 0.64),
            extra={"orientation": orientation},
        )
        add_streetscape_record(
            f"{name}_route_panel_detail",
            "bus_stop_route_panel",
            (ad_center[0], ad_center[1], 1.40),
            extra={"orientation": orientation},
        )

    def add_public_hydrant(name: str, center: tuple[float, float]) -> None:
        x, y = center
        roads.add_cylinder((x, y), 0.18, 0.10, 0.62, f"{name}_barrel", "TrafficSignalRed", segments=12)
        roads.add_cylinder((x, y), 0.20, 0.72, 0.12, f"{name}_cap", "TrafficSignalYellow", segments=12)
        roads.add_box((x, y), (0.64, 0.12), 0.12, 0.46, f"{name}_side_nozzles", "TrafficSignalYellow")
        add_streetscape_record(name, "public_hydrant_marker", (x, y, 0.48))

    def add_crosswalk_ladder_marking(name: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        if orientation == "east_west":
            roads.add_box((x, y - 1.54), (7.8, 0.16), 0.032, 0.205, f"{name}_near_edge", "CrosswalkWhite")
            roads.add_box((x, y + 1.54), (7.8, 0.16), 0.032, 0.205, f"{name}_far_edge", "CrosswalkWhite")
            for stripe_index, offset in enumerate([-2.55, -1.53, -0.51, 0.51, 1.53, 2.55], start=1):
                roads.add_box((x + offset, y), (0.28, 2.62), 0.032, 0.205, f"{name}_ladder_stripe_{stripe_index:02d}", "CrosswalkWhite")
            size = (7.8, 3.25)
        else:
            roads.add_box((x - 1.54, y), (0.16, 7.8), 0.032, 0.205, f"{name}_near_edge", "CrosswalkWhite")
            roads.add_box((x + 1.54, y), (0.16, 7.8), 0.032, 0.205, f"{name}_far_edge", "CrosswalkWhite")
            for stripe_index, offset in enumerate([-2.55, -1.53, -0.51, 0.51, 1.53, 2.55], start=1):
                roads.add_box((x, y + offset), (2.62, 0.28), 0.032, 0.205, f"{name}_ladder_stripe_{stripe_index:02d}", "CrosswalkWhite")
            size = (3.25, 7.8)
        add_streetscape_record(name, "crosswalk_ladder_marking", (x, y, 0.225), extra={"orientation": orientation, "size_m": size})

    def add_tactile_warning_surface(name: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        panel_size = (1.25, 0.78) if orientation == "east_west" else (0.78, 1.25)
        roads.add_box(center, panel_size, 0.022, 0.182, f"{name}_yellow_panel", "LaneMarkingYellow")
        x_offsets = [-0.42, -0.14, 0.14, 0.42] if orientation == "east_west" else [-0.22, 0.0, 0.22]
        y_offsets = [-0.22, 0.0, 0.22] if orientation == "east_west" else [-0.42, -0.14, 0.14, 0.42]
        dot_index = 1
        for dx in x_offsets:
            for dy in y_offsets:
                roads.add_cylinder((x + dx, y + dy), 0.035, 0.205, 0.025, f"{name}_raised_dot_{dot_index:02d}", "SignalMarker", segments=8)
                dot_index += 1
        add_streetscape_record(name, "tactile_warning_surface", (x, y, 0.215), extra={"orientation": orientation, "dot_count": dot_index - 1})

    def add_sidewalk_expansion_joint(name: str, center: tuple[float, float], length: float, orientation: str) -> None:
        x, y = center
        size = (0.045, length) if orientation == "north_south" else (length, 0.045)
        roads.add_box(center, size, 0.018, 0.185, name, "StepStone")
        add_streetscape_record(name, "sidewalk_expansion_joint", (x, y, 0.195), extra={"orientation": orientation, "length_m": round(length, 3)})

    def add_sidewalk_grime_strip(name: str, center: tuple[float, float], length: float, orientation: str) -> None:
        x, y = center
        size = (length, 0.18) if orientation == "east_west" else (0.18, length)
        roads.add_box(center, size, 0.012, 0.206, name, "RoadCrackSealant")
        add_streetscape_record(name, "sidewalk_grime_strip", (x, y, 0.218), extra={"orientation": orientation, "length_m": round(length, 3)})

    def add_sidewalk_stain_patch(
        name: str,
        center: tuple[float, float],
        size: tuple[float, float],
        angle_degrees: float,
    ) -> None:
        roads.add_oriented_box(center, size, 0.010, 0.209, math.radians(angle_degrees), name, "FloorWear")
        add_streetscape_record(
            name,
            "sidewalk_stain_patch",
            (center[0], center[1], 0.220),
            extra={"size_m": [round(size[0], 3), round(size[1], 3)], "angle_degrees": round(angle_degrees, 2)},
        )

    def add_curb_gutter_grime_strip(name: str, center: tuple[float, float], length: float, orientation: str) -> None:
        x, y = center
        size = (length, 0.22) if orientation == "east_west" else (0.22, length)
        roads.add_box(center, size, 0.014, 0.225, name, "RoadCrackSealant")
        add_streetscape_record(name, "curb_gutter_grime_strip", (x, y, 0.239), extra={"orientation": orientation, "length_m": round(length, 3)})

    def add_bike_lane_surface_scuff(
        name: str,
        center: tuple[float, float],
        size: tuple[float, float],
        angle_degrees: float,
    ) -> None:
        roads.add_oriented_box(center, size, 0.012, 0.236, math.radians(angle_degrees), name, "RoadPatchAsphalt")
        add_streetscape_record(
            name,
            "bike_lane_surface_scuff",
            (center[0], center[1], 0.249),
            extra={"size_m": [round(size[0], 3), round(size[1], 3)], "angle_degrees": round(angle_degrees, 2)},
        )

    def add_crosswalk_paint_wear_patch(
        name: str,
        center: tuple[float, float],
        size: tuple[float, float],
        angle_degrees: float,
    ) -> None:
        roads.add_oriented_box(center, size, 0.012, 0.240, math.radians(angle_degrees), name, "RoadPatchAsphalt")
        add_streetscape_record(
            name,
            "crosswalk_paint_wear_patch",
            (center[0], center[1], 0.253),
            extra={"size_m": [round(size[0], 3), round(size[1], 3)], "angle_degrees": round(angle_degrees, 2)},
        )

    def add_road_tire_wear_band(
        name: str,
        center: tuple[float, float],
        size: tuple[float, float],
        angle_degrees: float,
    ) -> None:
        roads.add_oriented_box(center, size, 0.010, 0.239, math.radians(angle_degrees), name, "RoadPatchAsphalt")
        add_streetscape_record(
            name,
            "road_tire_wear_band",
            (center[0], center[1], 0.250),
            extra={"size_m": [round(size[0], 3), round(size[1], 3)], "angle_degrees": round(angle_degrees, 2)},
        )

    def add_road_oil_stain(
        name: str,
        center: tuple[float, float],
        size: tuple[float, float],
        angle_degrees: float,
    ) -> None:
        angle = math.radians(angle_degrees)
        roads.add_oriented_box(center, size, 0.009, 0.248, angle, f"{name}_soft_edge", "RoadCrackSealant")
        roads.add_oriented_box(
            (center[0] + size[0] * 0.07, center[1] - size[1] * 0.05),
            (size[0] * 0.58, size[1] * 0.52),
            0.010,
            0.252,
            angle + math.radians(7.0),
            f"{name}_dark_core",
            "RoadPatchAsphalt",
        )
        add_streetscape_record(
            name,
            "road_oil_stain",
            (center[0], center[1], 0.260),
            extra={"size_m": [round(size[0], 3), round(size[1], 3)], "angle_degrees": round(angle_degrees, 2)},
        )

    def add_sidewalk_gum_mark(name: str, center: tuple[float, float], radius: float) -> None:
        roads.add_cylinder(center, radius, 0.214, 0.006, f"{name}_flattened_disc", "FloorWear", segments=10)
        add_streetscape_record(name, "sidewalk_gum_mark", (center[0], center[1], 0.222), extra={"radius_m": round(radius, 3)})

    def add_sidewalk_leaf_litter_cluster(name: str, center: tuple[float, float], radius: float) -> None:
        leaf_materials = ["TreeCanopy", "BenchWood", "TreeTrunk", "FloorWear"]
        leaf_count = 5
        for leaf_index in range(leaf_count):
            spread = radius * (0.18 + stable_unit_interval(name, leaf_index, "spread") * 0.82)
            theta = math.tau * stable_unit_interval(name, leaf_index, "theta")
            leaf_center = (center[0] + math.cos(theta) * spread, center[1] + math.sin(theta) * spread)
            leaf_size = (
                0.18 + stable_unit_interval(name, leaf_index, "size_x") * 0.16,
                0.045 + stable_unit_interval(name, leaf_index, "size_y") * 0.035,
            )
            leaf_angle = math.tau * stable_unit_interval(name, leaf_index, "angle")
            material = leaf_materials[leaf_index % len(leaf_materials)]
            roads.add_oriented_box(leaf_center, leaf_size, 0.006, 0.216 + leaf_index * 0.001, leaf_angle, f"{name}_leaf_{leaf_index+1:02d}", material)
        add_streetscape_record(name, "sidewalk_leaf_litter_cluster", (center[0], center[1], 0.226), extra={"radius_m": round(radius, 3), "leaf_count": leaf_count})

    def add_curb_grime_patch(
        name: str,
        center: tuple[float, float],
        size: tuple[float, float],
        angle_degrees: float,
    ) -> None:
        roads.add_oriented_box(center, size, 0.012, 0.242, math.radians(angle_degrees), name, "StoneGrimeOverlay")
        add_streetscape_record(
            name,
            "curb_grime_patch",
            (center[0], center[1], 0.256),
            extra={"size_m": [round(size[0], 3), round(size[1], 3)], "angle_degrees": round(angle_degrees, 2)},
        )

    def add_bike_lane_delineator_post(name: str, center: tuple[float, float]) -> None:
        x, y = center
        roads.add_cylinder((x, y), 0.18, 0.10, 0.05, f"{name}_rubber_base", "TrafficSignalHousing", segments=12)
        for bolt_index, (dx, dy) in enumerate([(-0.08, -0.08), (-0.08, 0.08), (0.08, -0.08), (0.08, 0.08)], start=1):
            roads.add_cylinder((x + dx, y + dy), 0.022, 0.155, 0.018, f"{name}_base_bolt_{bolt_index}", "DoorMetal", segments=8)
        roads.add_cylinder((x, y), 0.055, 0.14, 0.86, f"{name}_flex_post", "BikeLanePost", segments=10)
        roads.add_box((x, y), (0.18, 0.035), 0.045, 0.58, f"{name}_reflective_band_low", "LaneMarkingWhite")
        roads.add_box((x, y), (0.18, 0.035), 0.045, 0.86, f"{name}_reflective_band_high", "LaneMarkingWhite")
        add_streetscape_record(name, "bike_lane_delineator_post", (x, y, 0.58))
        add_streetscape_record(
            f"{name}_base_plate_detail",
            "bike_lane_delineator_base_plate",
            (x, y, 0.16),
            extra={"bolt_count": 4},
        )

    def add_pedestrian_signal_marker(name: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        roads.add_cylinder((x, y), 0.055, 0.10, 2.85, f"{name}_pushbutton_pole", "StreetLightPole", segments=8)
        if orientation == "east_west":
            signal_size = (0.42, 0.14)
            button_size = (0.24, 0.10)
            offset = (0.0, 0.11)
        else:
            signal_size = (0.14, 0.42)
            button_size = (0.10, 0.24)
            offset = (0.11, 0.0)
        roads.add_box((x, y), signal_size, 0.52, 2.62, f"{name}_walk_signal_housing", "TrafficSignalHousing")
        roads.add_box((x + offset[0], y + offset[1]), (signal_size[0] * 0.55, signal_size[1] * 0.55), 0.045, 2.85, f"{name}_walk_icon_marker", "LaneMarkingWhite")
        roads.add_box((x, y), button_size, 0.18, 1.22, f"{name}_push_button_box", "TrafficSignalHousing")
        roads.add_cylinder((x + offset[0], y + offset[1]), 0.045, 1.40, 0.025, f"{name}_button_marker", "SignalMarker", segments=8)
        add_streetscape_record(name, "pedestrian_signal_marker", (x, y, 1.75), extra={"orientation": orientation})

    def add_regulatory_stop_sign(name: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        panel_size = (0.86, 0.10) if orientation == "east_west" else (0.10, 0.86)
        word_bar_size = (0.48, 0.035) if orientation == "east_west" else (0.035, 0.48)
        roads.add_cylinder((x, y), 0.045, 0.10, 2.35, f"{name}_post", "StreetLightPole", segments=8)
        roads.add_box((x, y), panel_size, 0.72, 1.82, f"{name}_red_panel", "TrafficSignalRed")
        roads.add_box((x, y), word_bar_size, 0.06, 2.10, f"{name}_white_word_marker", "LaneMarkingWhite")
        add_streetscape_record(name, "regulatory_stop_sign", (x, y, 1.78), extra={"label": "STOP", "orientation": orientation})

    def add_bike_route_sign(name: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        panel_size = (1.05, 0.12) if orientation == "east_west" else (0.12, 1.05)
        marker_size = (0.62, 0.045) if orientation == "east_west" else (0.045, 0.62)
        roads.add_cylinder((x, y), 0.045, 0.10, 2.15, f"{name}_post", "StreetLightPole", segments=8)
        roads.add_box((x, y), panel_size, 0.62, 1.82, f"{name}_green_panel", "StreetSignGreen")
        roads.add_box((x, y), marker_size, 0.055, 2.05, f"{name}_white_bike_route_marker", "LaneMarkingWhite")
        add_streetscape_record(name, "bike_route_sign", (x, y, 1.62), extra={"label": "Bike Route", "orientation": orientation})

    def add_crosswalk_ahead_sign(name: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        panel_size = (0.94, 0.12) if orientation == "east_west" else (0.12, 0.94)
        icon_size = (0.42, 0.045) if orientation == "east_west" else (0.045, 0.42)
        roads.add_cylinder((x, y), 0.045, 0.10, 2.22, f"{name}_post", "StreetLightPole", segments=8)
        roads.add_box((x, y), panel_size, 0.68, 1.88, f"{name}_yellow_panel", "LaneMarkingYellow")
        roads.add_box((x, y), icon_size, 0.055, 2.12, f"{name}_crossing_icon_marker", "TrafficSignalHousing")
        add_streetscape_record(name, "crosswalk_ahead_sign", (x, y, 1.70), extra={"label": "Crosswalk", "orientation": orientation})

    def add_dcgis_traffic_control_sign(name: str, sign: DcgisTrafficSignPoint, stack_index: int) -> None:
        offset_angle = stack_index * math.tau / 5.0
        offset_radius = 0.18 * min(stack_index, 4)
        x = sign.x + math.cos(offset_angle) * offset_radius
        y = sign.y + math.sin(offset_angle) * offset_radius
        orientation = "east_west" if stack_index % 2 else "north_south"
        panel_size = (0.76, 0.10) if orientation == "east_west" else (0.10, 0.76)
        trim_size = (0.88, 0.12) if orientation == "east_west" else (0.12, 0.88)
        symbol_size = (0.42, 0.036) if orientation == "east_west" else (0.036, 0.42)
        panel_material = "LaneMarkingWhite" if sign.object_id % 3 else "LaneMarkingYellow"
        roads.add_cylinder((x, y), 0.042, 0.10, 2.26, f"{name}_post", "StreetLightPole", segments=8)
        roads.add_box((x, y), trim_size, 0.66, 1.83, f"{name}_dark_backplate", "TrafficSignalHousing")
        roads.add_box((x, y), panel_size, 0.56, 1.88, f"{name}_sign_face", panel_material)
        roads.add_box((x, y), symbol_size, 0.052, 2.08, f"{name}_abstract_symbol_bar", "TrafficSignalHousing")
        add_streetscape_record(
            name,
            "dcgis_traffic_control_sign",
            (x, y, 1.68),
            public_accuracy="public_1999_planimetric_sign_point_generic_visual",
            extra={
                "source": "DCGIS Planimetrics 1999 Other Traffic Signs",
                "dcgis_object_id": sign.object_id,
                "dcgis_sign_id": sign.sign_id,
                "dcgis_sign_code": sign.sign_code,
                "description": sign.description,
                "dxf_layer": sign.dxf_layer,
                "orientation": orientation,
                "stack_index": stack_index,
            },
        )

    def add_dcgis_overhead_traffic_sign(name: str, sign: DcgisOverheadTrafficSign) -> None:
        x0, y0 = sign.points[0]
        x1, y1 = sign.points[-1]
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0
        dx = x1 - x0
        dy = y1 - y0
        length = max(math.hypot(dx, dy), 1.2)
        angle = math.atan2(dy, dx) if length > 0.01 else 0.0
        ux = math.cos(angle)
        uy = math.sin(angle)
        support_a = (cx - ux * length / 2.0, cy - uy * length / 2.0)
        support_b = (cx + ux * length / 2.0, cy + uy * length / 2.0)
        roads.add_cylinder(support_a, 0.055, 0.10, 4.28, f"{name}_support_a", "StreetLightPole", segments=8)
        roads.add_cylinder(support_b, 0.055, 0.10, 4.28, f"{name}_support_b", "StreetLightPole", segments=8)
        roads.add_oriented_box((cx, cy), (length + 0.34, 0.10), 0.10, 4.22, angle, f"{name}_overhead_bar", "StreetLightPole")
        roads.add_oriented_box((cx, cy), (max(1.02, length * 0.90), 0.16), 0.52, 3.82, angle, f"{name}_green_panel", "StreetSignGreen")
        roads.add_oriented_box((cx, cy), (max(0.52, length * 0.46), 0.035), 0.052, 4.04, angle, f"{name}_white_text_marker", "LaneMarkingWhite")
        add_streetscape_record(
            name,
            "dcgis_overhead_traffic_sign",
            (cx, cy, 3.72),
            public_accuracy="public_1999_planimetric_overhead_sign_generic_visual",
            extra={
                "source": "DCGIS Planimetrics 1999 Overhead Traffic Signs",
                "dcgis_object_id": sign.object_id,
                "dcgis_sign_id": sign.sign_id,
                "dcgis_sign_code": sign.sign_code,
                "description": sign.description,
                "dxf_layer": sign.dxf_layer,
                "span_m": round(length, 3),
                "angle_degrees": round(math.degrees(angle), 2),
            },
        )

    def dcgis_fixture_extra(point: DcgisFixturePoint) -> dict[str, Any]:
        return {
            "source": f"DCGIS Planimetrics 1999 {point.source_label}",
            "dcgis_object_id": point.object_id,
            "dcgis_feature_id": point.feature_id,
            "dcgis_feature_code": point.feature_code,
            "description": point.description,
            "dxf_layer": point.dxf_layer,
        }

    def add_dcgis_fire_hydrant(name: str, point: DcgisFixturePoint) -> None:
        x, y = point.x, point.y
        roads.add_cylinder((x, y), 0.18, 0.08, 0.66, f"{name}_barrel", "TrafficSignalRed", segments=12)
        roads.add_cylinder((x, y), 0.20, 0.74, 0.11, f"{name}_bonnet", "TrafficSignalYellow", segments=12)
        roads.add_box((x, y), (0.62, 0.12), 0.12, 0.44, f"{name}_side_nozzles", "TrafficSignalYellow")
        roads.add_box((x, y), (0.14, 0.46), 0.08, 0.58, f"{name}_front_nozzle", "TrafficSignalYellow")
        extra = dcgis_fixture_extra(point)
        add_streetscape_record(
            name,
            "dcgis_fire_hydrant",
            (x, y, 0.48),
            public_accuracy="public_1999_planimetric_hydrant_generic_visual",
            extra=extra,
        )

    def add_dcgis_street_tree(name: str, point: DcgisFixturePoint) -> None:
        x, y = point.x, point.y
        scale = 0.86 + stable_unit_interval(point.object_id, point.feature_id) * 0.34
        roads.add_cylinder((x, y), 0.12 * scale, 0.08, 1.58 * scale, f"{name}_trunk", "TreeTrunk", segments=8)
        roads.add_cylinder((x, y), 0.72 * scale, 1.18 * scale, 0.74 * scale, f"{name}_lower_canopy", "TreeCanopy", segments=14)
        roads.add_cylinder((x, y), 0.56 * scale, 1.66 * scale, 0.62 * scale, f"{name}_upper_canopy", "TreeCanopy", segments=14)
        roads.add_cylinder((x, y), 0.58 * scale, 0.055, 0.10, f"{name}_tree_pit_ring", "PlanterStone", segments=12)
        extra = dcgis_fixture_extra(point)
        extra["scale"] = round(scale, 3)
        add_streetscape_record(
            name,
            "dcgis_street_tree",
            (x, y, 1.45 * scale),
            public_accuracy="public_1999_planimetric_tree_generic_visual",
            extra=extra,
        )

    def add_dcgis_utility_pole(name: str, point: DcgisFixturePoint) -> None:
        x, y = point.x, point.y
        angle = math.radians(point.angle_degrees)
        if point.angle_degrees == 0.0:
            angle = stable_unit_interval(point.object_id, "utility_pole_angle") * math.pi
        roads.add_cylinder((x, y), 0.060, 0.08, 4.18, f"{name}_pole", "StreetLightPole", segments=8)
        roads.add_oriented_box((x, y), (1.22, 0.08), 0.08, 3.72, angle, f"{name}_crossarm", "BollardMetal")
        roads.add_cylinder((x, y), 0.12, 0.06, 0.055, f"{name}_base_plate", "BollardMetal", segments=10)
        roads.add_box((x, y), (0.24, 0.14), 0.22, 2.10, f"{name}_utility_box_marker", "DoorMetal")
        extra = dcgis_fixture_extra(point)
        extra["angle_degrees"] = round(math.degrees(angle), 2)
        add_streetscape_record(
            name,
            "dcgis_utility_pole",
            (x, y, 2.18),
            public_accuracy="public_1999_planimetric_utility_pole_generic_visual",
            extra=extra,
        )

    def add_dcgis_misc_public_fixture(name: str, point: DcgisFixturePoint) -> None:
        x, y = point.x, point.y
        variant = point.object_id % 4
        if variant == 0:
            roads.add_cylinder((x, y), 0.16, 0.08, 0.72, f"{name}_bollard_body", "BollardMetal", segments=10)
            roads.add_cylinder((x, y), 0.18, 0.80, 0.06, f"{name}_bollard_cap", "BrassRail", segments=10)
            visual = "bollard"
            center_z = 0.48
        elif variant == 1:
            angle = math.radians(point.angle_degrees or stable_unit_interval(point.object_id, "bench") * 180.0)
            roads.add_oriented_box((x, y), (1.62, 0.34), 0.12, 0.42, angle, f"{name}_bench_seat", "BenchWood")
            roads.add_oriented_box((x, y), (1.70, 0.12), 0.42, 0.52, angle, f"{name}_bench_back", "BenchWood")
            visual = "bench"
            center_z = 0.62
        elif variant == 2:
            roads.add_cylinder((x, y), 0.38, 0.06, 0.34, f"{name}_planter_bowl", "PlanterStone", segments=14)
            roads.add_cylinder((x, y), 0.44, 0.38, 0.08, f"{name}_planter_rim", "PlanterStone", segments=14)
            roads.add_cylinder((x, y), 0.34, 0.42, 0.42, f"{name}_planting_mass", "TreeCanopy", segments=12)
            visual = "planter"
            center_z = 0.50
        else:
            roads.add_cylinder((x, y), 0.24, 0.08, 0.54, f"{name}_marker_post", "StreetLightPole", segments=8)
            roads.add_box((x, y), (0.58, 0.10), 0.20, 0.62, f"{name}_small_public_marker", "MarkerBlue")
            visual = "small_marker"
            center_z = 0.56
        extra = dcgis_fixture_extra(point)
        extra["visual_variant"] = visual
        add_streetscape_record(
            name,
            "dcgis_misc_public_fixture",
            (x, y, center_z),
            public_accuracy="public_1999_planimetric_misc_point_generic_visual",
            extra=extra,
        )

    def dcgis_surface_extra(feature: DcgisPolylineFeature | DcgisPolygonFeature) -> dict[str, Any]:
        return {
            "source": f"DCGIS Planimetrics 1999 {feature.source_label}",
            "dcgis_object_id": feature.object_id,
            "dcgis_feature_id": feature.feature_id,
            "dcgis_feature_code": feature.feature_code,
            "description": feature.description,
            "dxf_layer": feature.dxf_layer,
        }

    def add_dcgis_curb_line(name: str, feature: DcgisPolylineFeature) -> None:
        roads.add_polyline_strip(list(feature.points), 0.18, 0.218, name, "CurbConcrete")
        midpoint = feature.points[len(feature.points) // 2]
        extra = dcgis_surface_extra(feature)
        extra["length_m"] = round(polyline_length(feature.points), 3)
        add_streetscape_record(
            name,
            "dcgis_curb_line",
            (midpoint[0], midpoint[1], 0.245),
            public_accuracy="public_1999_planimetric_curb_line",
            extra=extra,
        )
        metadata["curbs"].append(
            {
                "id": feature.object_id,
                "name": name,
                "side": "dcgis_planimetric",
                "offset_m": 0.0,
                "source": "DCGIS Planimetrics 1999 Curbs",
                "dcgis_feature_id": feature.feature_id,
                "length_m": round(polyline_length(feature.points), 3),
            }
        )

    def add_dcgis_polygon_edges(
        name: str,
        feature: DcgisPolygonFeature,
        kind: str,
        material: str,
        width: float,
        z: float,
    ) -> int:
        count = 0
        for ring_index, ring in enumerate(feature.rings[:2], start=1):
            if len(ring) < 2:
                continue
            roads.add_polyline_strip(list(ring), width, z, f"{name}_edge_{ring_index}", material)
            count += 1
        center = polygon_feature_center(feature)
        extra = dcgis_surface_extra(feature)
        extra["edge_ring_count"] = count
        add_streetscape_record(
            name,
            kind,
            (center[0], center[1], z + 0.025),
            public_accuracy="public_1999_planimetric_polygon_edge_visual",
            extra=extra,
        )
        return 1 if count else 0

    def add_dcgis_surface_patch(
        name: str,
        feature: DcgisPolygonFeature,
        kind: str,
        material: str,
        z: float,
        max_size: tuple[float, float],
    ) -> None:
        min_x, min_y, max_x, max_y = polygon_feature_bounds(feature)
        center = polygon_feature_center(feature)
        size = (min(max_x - min_x, max_size[0]), min(max_y - min_y, max_size[1]))
        if size[0] < 0.8 or size[1] < 0.8:
            return
        roads.add_box(center, size, 0.018, z, name, material)
        extra = dcgis_surface_extra(feature)
        extra["patch_size_m"] = [round(size[0], 3), round(size[1], 3)]
        extra["source_area_m2"] = round(polygon_area_m2(list(feature.rings[0])), 3)
        add_streetscape_record(
            name,
            kind,
            (center[0], center[1], z + 0.020),
            public_accuracy="public_1999_planimetric_polygon_bounded_patch",
            extra=extra,
        )

    def add_curb_paint_segment(name: str, center: tuple[float, float], length: float, orientation: str, material: str) -> None:
        x, y = center
        size = (length, 0.16) if orientation == "east_west" else (0.16, length)
        roads.add_box(center, size, 0.024, 0.205, name, material)
        add_streetscape_record(name, "curb_paint_segment", (x, y, 0.218), extra={"orientation": orientation, "length_m": round(length, 3), "material": material})

    def add_asphalt_patch(
        name: str,
        center: tuple[float, float],
        size: tuple[float, float],
        angle_degrees: float,
    ) -> None:
        roads.add_oriented_box(center, size, 0.026, 0.214, math.radians(angle_degrees), name, "RoadPatchAsphalt")
        add_streetscape_record(
            name,
            "road_asphalt_patch",
            (center[0], center[1], 0.227),
            extra={"size_m": [round(size[0], 3), round(size[1], 3)], "angle_degrees": round(angle_degrees, 2)},
        )

    def add_road_crack_line(name: str, points: list[tuple[float, float]], width: float = 0.07) -> None:
        roads.add_polyline_strip(points, width, 0.232, name, "RoadCrackSealant")
        cx = sum(point[0] for point in points) / len(points)
        cy = sum(point[1] for point in points) / len(points)
        length = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:]))
        add_streetscape_record(name, "road_crack_line", (cx, cy, 0.234), extra={"length_m": round(length, 3), "width_m": round(width, 3)})

    def add_manhole_cover(name: str, center: tuple[float, float]) -> None:
        x, y = center
        roads.add_cylinder((x, y), 0.44, 0.216, 0.034, f"{name}_cover", "RoadCrackSealant", segments=24)
        roads.add_ring((x, y), 0.36, 0.29, 0.252, 0.020, f"{name}_raised_ring", "RoadPatchAsphalt", segments=24)
        add_streetscape_record(name, "public_manhole_cover", (x, y, 0.245), extra={"radius_m": 0.44})

    def add_storm_drain_grate(name: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        grate_size = (1.20, 0.36) if orientation == "east_west" else (0.36, 1.20)
        roads.add_box(center, grate_size, 0.038, 0.212, f"{name}_dark_recess", "RoadCrackSealant")
        inlet_size = (1.32, 0.12) if orientation == "east_west" else (0.12, 1.32)
        inlet_center = (x, y + 0.28) if orientation == "east_west" else (x + 0.28, y)
        roads.add_box(inlet_center, inlet_size, 0.12, 0.185, f"{name}_curb_inlet_throat", "RoadCrackSealant")
        roads.add_box(inlet_center, (inlet_size[0] * 1.10, inlet_size[1] * 1.10), 0.035, 0.315, f"{name}_curb_inlet_stone_lip", "CurbConcrete")
        for slat_index, offset in enumerate([-0.36, -0.12, 0.12, 0.36], start=1):
            if orientation == "east_west":
                slat_center = (x + offset, y)
                slat_size = (0.040, 0.30)
            else:
                slat_center = (x, y + offset)
                slat_size = (0.30, 0.040)
            roads.add_box(slat_center, slat_size, 0.022, 0.252, f"{name}_slat_{slat_index:02d}", "DoorMetal")
        add_streetscape_record(name, "storm_drain_grate", (x, y, 0.246), extra={"orientation": orientation, "size_m": grate_size})
        add_streetscape_record(
            f"{name}_curb_inlet",
            "storm_drain_curb_inlet",
            (inlet_center[0], inlet_center[1], 0.275),
            extra={"orientation": orientation, "size_m": inlet_size},
        )

    def add_public_utility_box(name: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        body_size = (0.72, 0.42) if orientation == "east_west" else (0.42, 0.72)
        roads.add_box(center, body_size, 1.08, 0.14, f"{name}_body", "TrafficSignalHousing")
        roads.add_box((x, y), (body_size[0] * 0.72, body_size[1] * 0.18), 0.045, 0.86, f"{name}_service_label", "LaneMarkingWhite")
        for vent_index, z in enumerate([0.38, 0.52, 0.66], start=1):
            roads.add_box((x, y), (body_size[0] * 0.62, body_size[1] * 0.10), 0.026, z, f"{name}_louver_{vent_index:02d}", "RoadCrackSealant")
        add_streetscape_record(name, "public_utility_box", (x, y, 0.68), extra={"orientation": orientation, "size_m": body_size})

    def add_public_news_box(name: str, center: tuple[float, float], material: str) -> None:
        x, y = center
        roads.add_box(center, (0.54, 0.42), 0.92, 0.12, f"{name}_box_body", material)
        roads.add_box((x, y - 0.045), (0.40, 0.050), 0.36, 0.48, f"{name}_front_window", "DoorGlass")
        roads.add_box((x, y), (0.38, 0.042), 0.050, 0.92, f"{name}_headline_bar", "LaneMarkingWhite")
        add_streetscape_record(name, "public_news_box", (x, y, 0.58), extra={"material": material})

    def add_public_roadway_visual_details() -> None:
        # Authored public-facing road markings for visual realism. These are
        # schematic surface props, not traffic-control engineering plans.
        for name, center, orientation in [
            ("west_approach_stop_bar_north", (-222.0, 34.0), "east_west"),
            ("west_approach_stop_bar_south", (-222.0, -34.0), "east_west"),
            ("east_approach_stop_bar_north", (142.0, 34.0), "east_west"),
            ("east_approach_stop_bar_south", (142.0, -34.0), "east_west"),
            ("north_approach_stop_bar_west", (-54.0, 138.0), "north_south"),
            ("north_approach_stop_bar_east", (54.0, 138.0), "north_south"),
            ("south_approach_stop_bar_west", (-54.0, -138.0), "north_south"),
            ("south_approach_stop_bar_east", (54.0, -138.0), "north_south"),
            ("west_pool_stop_bar", (-336.0, 0.0), "north_south"),
            ("east_plaza_stop_bar", (210.0, 0.0), "north_south"),
            ("northwest_public_stop_bar", (-148.0, 112.0), "east_west"),
            ("southwest_public_stop_bar", (-148.0, -112.0), "east_west"),
        ]:
            add_stop_bar(name, center, orientation)

        for name, center, direction in [
            ("west_approach_arrow_east_01", (-300.0, -8.0), "east"),
            ("west_approach_arrow_east_02", (-240.0, -8.0), "east"),
            ("west_approach_arrow_west_01", (-220.0, 8.0), "west"),
            ("west_approach_arrow_west_02", (-280.0, 8.0), "west"),
            ("east_approach_arrow_west_01", (130.0, 8.0), "west"),
            ("east_approach_arrow_east_01", (172.0, -8.0), "east"),
            ("north_approach_arrow_south_01", (-40.0, 168.0), "south"),
            ("north_approach_arrow_south_02", (40.0, 168.0), "south"),
            ("south_approach_arrow_north_01", (-40.0, -168.0), "north"),
            ("south_approach_arrow_north_02", (40.0, -168.0), "north"),
            ("northwest_curve_arrow_east", (-170.0, 92.0), "east"),
            ("southwest_curve_arrow_east", (-170.0, -92.0), "east"),
        ]:
            add_lane_arrow(name, center, direction)

        for name, center, orientation in [
            ("west_bike_symbol_01", (-318.0, 18.0), "east_west"),
            ("west_bike_symbol_02", (-278.0, 18.0), "east_west"),
            ("west_bike_symbol_03", (-238.0, 18.0), "east_west"),
            ("west_bike_symbol_04", (-198.0, 18.0), "east_west"),
            ("east_bike_symbol_01", (124.0, -18.0), "east_west"),
            ("east_bike_symbol_02", (164.0, -18.0), "east_west"),
            ("north_bike_symbol_01", (-68.0, 150.0), "north_south"),
            ("south_bike_symbol_01", (68.0, -150.0), "north_south"),
        ]:
            add_bike_symbol(name, center, orientation)

        ramp_index = 1
        for x, y, orientation in [
            (-70.0, 119.0, "east_west"), (-34.0, 122.0, "east_west"), (34.0, 122.0, "east_west"), (70.0, 119.0, "east_west"),
            (-70.0, -119.0, "east_west"), (-34.0, -122.0, "east_west"), (34.0, -122.0, "east_west"), (70.0, -119.0, "east_west"),
            (-94.0, 48.0, "north_south"), (-160.0, 96.0, "north_south"), (-94.0, -48.0, "north_south"), (-160.0, -96.0, "north_south"),
            (94.0, 48.0, "north_south"), (132.0, 88.0, "north_south"), (94.0, -48.0, "north_south"), (132.0, -88.0, "north_south"),
        ]:
            add_curb_ramp_visual(f"public_curb_ramp_{ramp_index:02d}", (x, y), orientation)
            ramp_index += 1

        for idx, (x, y, orientation) in enumerate(
            [
                (-70.0, 114.8, "east_west"), (-34.0, 117.8, "east_west"), (34.0, 117.8, "east_west"), (70.0, 114.8, "east_west"),
                (-70.0, -114.8, "east_west"), (-34.0, -117.8, "east_west"), (34.0, -117.8, "east_west"), (70.0, -114.8, "east_west"),
                (-89.8, 48.0, "north_south"), (-155.8, 96.0, "north_south"), (-89.8, -48.0, "north_south"), (-155.8, -96.0, "north_south"),
                (89.8, 48.0, "north_south"), (127.8, 88.0, "north_south"), (89.8, -48.0, "north_south"), (127.8, -88.0, "north_south"),
            ],
            start=1,
        ):
            add_tactile_warning_surface(f"public_tactile_warning_surface_{idx:02d}", (x, y), orientation)

        for idx, (x, y, orientation) in enumerate(
            [
                (-222.0, 41.0, "east_west"), (-222.0, -41.0, "east_west"), (142.0, 41.0, "east_west"), (142.0, -41.0, "east_west"),
                (-54.0, 145.0, "north_south"), (54.0, 145.0, "north_south"), (-54.0, -145.0, "north_south"), (54.0, -145.0, "north_south"),
                (-148.0, 119.0, "east_west"), (-148.0, -119.0, "east_west"), (-336.0, 7.0, "north_south"), (210.0, 7.0, "north_south"),
            ],
            start=1,
        ):
            add_crosswalk_ladder_marking(f"public_crosswalk_ladder_marking_{idx:02d}", (x, y), orientation)

        joint_specs = [
            ("west_approach_north_sidewalk", [(-336.0, 31.6), (-300.0, 31.6), (-264.0, 31.6), (-228.0, 31.6), (-192.0, 31.6), (-156.0, 31.6)], "north_south", 2.20),
            ("west_approach_south_sidewalk", [(-336.0, -31.6), (-300.0, -31.6), (-264.0, -31.6), (-228.0, -31.6), (-192.0, -31.6), (-156.0, -31.6)], "north_south", 2.20),
            ("east_approach_north_sidewalk", [(116.0, 31.6), (148.0, 31.6), (180.0, 31.6), (212.0, 31.6)], "north_south", 2.20),
            ("east_approach_south_sidewalk", [(116.0, -31.6), (148.0, -31.6), (180.0, -31.6), (212.0, -31.6)], "north_south", 2.20),
            ("north_approach_west_sidewalk", [(-62.0, 112.0), (-62.0, 142.0), (-62.0, 172.0), (-62.0, 202.0)], "east_west", 2.20),
            ("north_approach_east_sidewalk", [(62.0, 112.0), (62.0, 142.0), (62.0, 172.0), (62.0, 202.0)], "east_west", 2.20),
            ("south_approach_west_sidewalk", [(-62.0, -112.0), (-62.0, -142.0), (-62.0, -172.0), (-62.0, -202.0)], "east_west", 2.20),
            ("south_approach_east_sidewalk", [(62.0, -112.0), (62.0, -142.0), (62.0, -172.0), (62.0, -202.0)], "east_west", 2.20),
        ]
        joint_index = 1
        for prefix, centers, orientation, length in joint_specs:
            for center in centers:
                add_sidewalk_expansion_joint(f"{prefix}_expansion_joint_{joint_index:02d}", center, length, orientation)
                joint_index += 1

        delineator_centers = (
            [(-340.0 + step * 12.0, 20.9) for step in range(18)]
            + [(-340.0 + step * 12.0, -20.9) for step in range(18)]
            + [(110.0 + step * 12.0, 20.9) for step in range(10)]
            + [(110.0 + step * 12.0, -20.9) for step in range(10)]
            + [(-74.0, 112.0 + step * 12.0) for step in range(8)]
            + [(74.0, -196.0 + step * 12.0) for step in range(8)]
        )
        for idx, center in enumerate(delineator_centers, start=1):
            add_bike_lane_delineator_post(f"public_bike_lane_delineator_{idx:03d}", center)

        for idx, (x, y, orientation) in enumerate(
            [
                (-226.0, 41.0, "east_west"), (-226.0, -41.0, "east_west"), (146.0, 41.0, "east_west"), (146.0, -41.0, "east_west"),
                (-58.0, 142.0, "north_south"), (58.0, 142.0, "north_south"), (-58.0, -142.0, "north_south"), (58.0, -142.0, "north_south"),
                (-152.0, 116.0, "east_west"), (-152.0, -116.0, "east_west"), (-332.0, 6.0, "north_south"), (214.0, 6.0, "north_south"),
                (-94.0, 52.0, "north_south"), (94.0, 52.0, "north_south"), (-94.0, -52.0, "north_south"), (94.0, -52.0, "north_south"),
            ],
            start=1,
        ):
            add_pedestrian_signal_marker(f"public_pedestrian_signal_marker_{idx:02d}", (x, y), orientation)

        for idx, (x, y, orientation) in enumerate(
            [
                (-230.0, 36.0, "east_west"), (-230.0, -36.0, "east_west"), (150.0, 36.0, "east_west"), (150.0, -36.0, "east_west"),
                (-62.0, 146.0, "north_south"), (62.0, 146.0, "north_south"), (-62.0, -146.0, "north_south"), (62.0, -146.0, "north_south"),
                (-156.0, 120.0, "east_west"), (-156.0, -120.0, "east_west"), (-332.0, 10.0, "north_south"), (214.0, 10.0, "north_south"),
            ],
            start=1,
        ):
            add_regulatory_stop_sign(f"public_regulatory_stop_sign_{idx:02d}", (x, y), orientation)

        for idx, (x, y, orientation) in enumerate(
            [
                (-318.0, 24.0, "east_west"), (-276.0, 24.0, "east_west"), (-234.0, 24.0, "east_west"), (-192.0, 24.0, "east_west"),
                (124.0, -24.0, "east_west"), (166.0, -24.0, "east_west"), (208.0, -24.0, "east_west"),
                (-78.0, 150.0, "north_south"), (78.0, -150.0, "north_south"),
                (-180.0, 116.0, "east_west"), (-180.0, -116.0, "east_west"), (204.0, -34.0, "east_west"),
            ],
            start=1,
        ):
            add_bike_route_sign(f"public_bike_route_sign_{idx:02d}", (x, y), orientation)

        for idx, (x, y, orientation) in enumerate(
            [
                (-238.0, 45.5, "east_west"), (-238.0, -45.5, "east_west"), (154.0, 45.5, "east_west"), (154.0, -45.5, "east_west"),
                (-66.0, 152.0, "north_south"), (66.0, 152.0, "north_south"), (-66.0, -152.0, "north_south"), (66.0, -152.0, "north_south"),
                (-160.0, 124.0, "east_west"), (-160.0, -124.0, "east_west"), (-340.0, 12.0, "north_south"), (218.0, 12.0, "north_south"),
            ],
            start=1,
        ):
            add_crosswalk_ahead_sign(f"public_crosswalk_ahead_sign_{idx:02d}", (x, y), orientation)

        curb_paint_specs = [
            ("west_approach_north_yellow", (-286.0, 31.0), 54.0, "east_west", "LaneMarkingYellow"),
            ("west_approach_south_yellow", (-286.0, -31.0), 54.0, "east_west", "LaneMarkingYellow"),
            ("west_approach_north_white", (-186.0, 31.0), 46.0, "east_west", "LaneMarkingWhite"),
            ("west_approach_south_white", (-186.0, -31.0), 46.0, "east_west", "LaneMarkingWhite"),
            ("east_approach_north_yellow", (156.0, 31.0), 44.0, "east_west", "LaneMarkingYellow"),
            ("east_approach_south_yellow", (156.0, -31.0), 44.0, "east_west", "LaneMarkingYellow"),
            ("north_approach_west_yellow", (-62.0, 158.0), 52.0, "north_south", "LaneMarkingYellow"),
            ("north_approach_east_yellow", (62.0, 158.0), 52.0, "north_south", "LaneMarkingYellow"),
            ("south_approach_west_yellow", (-62.0, -158.0), 52.0, "north_south", "LaneMarkingYellow"),
            ("south_approach_east_yellow", (62.0, -158.0), 52.0, "north_south", "LaneMarkingYellow"),
            ("northwest_curve_white", (-150.0, 114.0), 42.0, "east_west", "LaneMarkingWhite"),
            ("southwest_curve_white", (-150.0, -114.0), 42.0, "east_west", "LaneMarkingWhite"),
            ("east_plaza_white", (204.0, 30.0), 34.0, "north_south", "LaneMarkingWhite"),
            ("east_plaza_yellow", (204.0, -30.0), 34.0, "north_south", "LaneMarkingYellow"),
            ("west_pool_white", (-340.0, 28.0), 34.0, "north_south", "LaneMarkingWhite"),
            ("west_pool_yellow", (-340.0, -28.0), 34.0, "north_south", "LaneMarkingYellow"),
        ]
        for name, center, length, orientation, material in curb_paint_specs:
            add_curb_paint_segment(f"public_curb_paint_segment_{name}", center, length, orientation, material)

        patch_specs = [
            ("west_approach_patch_01", (-318.0, -6.0), (8.2, 2.6), 1.0),
            ("west_approach_patch_02", (-292.0, 7.4), (6.4, 2.1), -2.0),
            ("west_approach_patch_03", (-266.0, -7.2), (7.0, 2.4), 2.5),
            ("west_approach_patch_04", (-240.0, 6.6), (5.6, 1.9), -1.5),
            ("west_approach_patch_05", (-214.0, -6.8), (6.0, 2.2), 2.0),
            ("west_approach_patch_06", (-188.0, 6.8), (7.4, 2.2), -1.0),
            ("east_approach_patch_01", (122.0, 7.0), (5.8, 1.9), 1.0),
            ("east_approach_patch_02", (148.0, -7.0), (6.6, 2.2), -1.0),
            ("east_approach_patch_03", (176.0, 6.6), (5.2, 1.8), 2.0),
            ("east_approach_patch_04", (204.0, -7.0), (6.2, 2.1), -2.0),
            ("north_approach_patch_01", (-42.0, 132.0), (2.0, 6.2), 0.0),
            ("north_approach_patch_02", (42.0, 158.0), (2.0, 6.8), 0.0),
            ("north_approach_patch_03", (-42.0, 184.0), (2.1, 5.8), 0.0),
            ("south_approach_patch_01", (42.0, -132.0), (2.0, 6.2), 0.0),
            ("south_approach_patch_02", (-42.0, -158.0), (2.0, 6.8), 0.0),
            ("south_approach_patch_03", (42.0, -184.0), (2.1, 5.8), 0.0),
            ("northwest_curve_patch_01", (-164.0, 96.0), (6.0, 2.0), 12.0),
            ("northwest_curve_patch_02", (-132.0, 116.0), (5.2, 1.8), -8.0),
            ("southwest_curve_patch_01", (-164.0, -96.0), (6.0, 2.0), -12.0),
            ("southwest_curve_patch_02", (-132.0, -116.0), (5.2, 1.8), 8.0),
            ("east_plaza_patch_01", (204.0, 42.0), (2.0, 5.4), 0.0),
            ("east_plaza_patch_02", (204.0, -42.0), (2.0, 5.4), 0.0),
            ("west_pool_patch_01", (-340.0, 42.0), (2.0, 5.2), 0.0),
            ("west_pool_patch_02", (-340.0, -42.0), (2.0, 5.2), 0.0),
        ]
        for name, center, size, angle_degrees in patch_specs:
            add_asphalt_patch(f"public_{name}", center, size, angle_degrees)

        crack_specs = [
            ("west_crack_01", [(-334.0, -8.5), (-322.0, -7.0), (-310.0, -8.2)]),
            ("west_crack_02", [(-316.0, 8.5), (-304.0, 7.6), (-292.0, 8.3)]),
            ("west_crack_03", [(-286.0, -8.6), (-274.0, -7.4), (-260.0, -8.0)]),
            ("west_crack_04", [(-252.0, 8.3), (-240.0, 7.5), (-226.0, 8.4)]),
            ("west_crack_05", [(-220.0, -8.0), (-208.0, -7.1), (-196.0, -8.1)]),
            ("west_crack_06", [(-190.0, 8.2), (-176.0, 7.7), (-162.0, 8.5)]),
            ("east_crack_01", [(116.0, 8.2), (128.0, 7.3), (140.0, 8.0)]),
            ("east_crack_02", [(146.0, -8.3), (158.0, -7.2), (172.0, -8.0)]),
            ("east_crack_03", [(178.0, 8.1), (190.0, 7.2), (202.0, 8.2)]),
            ("east_crack_04", [(202.0, -8.2), (214.0, -7.4), (226.0, -8.0)]),
            ("north_crack_01", [(-48.0, 124.0), (-47.0, 138.0), (-48.4, 152.0)]),
            ("north_crack_02", [(48.0, 136.0), (47.0, 150.0), (48.2, 164.0)]),
            ("north_crack_03", [(-48.0, 166.0), (-46.8, 180.0), (-48.4, 194.0)]),
            ("south_crack_01", [(48.0, -124.0), (47.0, -138.0), (48.4, -152.0)]),
            ("south_crack_02", [(-48.0, -136.0), (-47.0, -150.0), (-48.2, -164.0)]),
            ("south_crack_03", [(48.0, -166.0), (46.8, -180.0), (48.4, -194.0)]),
            ("nw_curve_crack_01", [(-178.0, 92.0), (-164.0, 98.0), (-150.0, 104.0)]),
            ("nw_curve_crack_02", [(-150.0, 118.0), (-136.0, 112.0), (-122.0, 116.0)]),
            ("sw_curve_crack_01", [(-178.0, -92.0), (-164.0, -98.0), (-150.0, -104.0)]),
            ("sw_curve_crack_02", [(-150.0, -118.0), (-136.0, -112.0), (-122.0, -116.0)]),
            ("east_plaza_crack_01", [(198.0, 28.0), (204.0, 38.0), (198.0, 50.0)]),
            ("east_plaza_crack_02", [(210.0, -28.0), (204.0, -38.0), (210.0, -50.0)]),
            ("west_pool_crack_01", [(-346.0, 28.0), (-340.0, 38.0), (-346.0, 50.0)]),
            ("west_pool_crack_02", [(-334.0, -28.0), (-340.0, -38.0), (-334.0, -50.0)]),
            ("road_joint_crack_01", [(-88.0, 52.0), (-96.0, 56.0), (-104.0, 54.0)]),
            ("road_joint_crack_02", [(88.0, -52.0), (96.0, -56.0), (104.0, -54.0)]),
            ("road_joint_crack_03", [(-88.0, -52.0), (-96.0, -56.0), (-104.0, -54.0)]),
            ("road_joint_crack_04", [(88.0, 52.0), (96.0, 56.0), (104.0, 54.0)]),
            ("plaza_lane_crack_01", [(180.0, 30.0), (190.0, 32.0), (200.0, 31.0)]),
            ("plaza_lane_crack_02", [(-218.0, 30.0), (-228.0, 32.0), (-238.0, 31.0)]),
            ("plaza_lane_crack_03", [(180.0, -30.0), (190.0, -32.0), (200.0, -31.0)]),
            ("plaza_lane_crack_04", [(-218.0, -30.0), (-228.0, -32.0), (-238.0, -31.0)]),
        ]
        for name, points in crack_specs:
            add_road_crack_line(f"public_{name}", points)

        for idx, center in enumerate(
            [
                (-318.0, 0.0), (-286.0, 0.0), (-254.0, 0.0), (-222.0, 0.0),
                (-190.0, 0.0), (124.0, 0.0), (156.0, 0.0), (188.0, 0.0),
                (-52.0, 132.0), (52.0, 132.0), (-52.0, -132.0), (52.0, -132.0),
            ],
            start=1,
        ):
            add_manhole_cover(f"public_manhole_cover_{idx:02d}", center)

        for idx, (center, orientation) in enumerate(
            [
                ((-330.0, 29.6), "east_west"), ((-294.0, -29.6), "east_west"), ((-258.0, 29.6), "east_west"), ((-222.0, -29.6), "east_west"),
                ((-186.0, 29.6), "east_west"), ((118.0, -29.6), "east_west"), ((154.0, 29.6), "east_west"), ((190.0, -29.6), "east_west"),
                ((-70.2, 126.0), "north_south"), ((70.2, 154.0), "north_south"), ((-70.2, -126.0), "north_south"), ((70.2, -154.0), "north_south"),
                ((-152.0, 110.5), "east_west"), ((-152.0, -110.5), "east_west"), ((206.0, 88.0), "north_south"), ((206.0, -88.0), "north_south"),
            ],
            start=1,
        ):
            add_storm_drain_grate(f"public_storm_drain_grate_{idx:02d}", center, orientation)

        sidewalk_grime_specs = [
            ("west_north_edge_01", (-318.0, 32.85), 24.0, "east_west"),
            ("west_north_edge_02", (-286.0, 32.85), 24.0, "east_west"),
            ("west_north_edge_03", (-254.0, 32.85), 24.0, "east_west"),
            ("west_north_edge_04", (-222.0, 32.85), 24.0, "east_west"),
            ("west_north_edge_05", (-190.0, 32.85), 24.0, "east_west"),
            ("west_south_edge_01", (-318.0, -32.85), 24.0, "east_west"),
            ("west_south_edge_02", (-286.0, -32.85), 24.0, "east_west"),
            ("west_south_edge_03", (-254.0, -32.85), 24.0, "east_west"),
            ("west_south_edge_04", (-222.0, -32.85), 24.0, "east_west"),
            ("west_south_edge_05", (-190.0, -32.85), 24.0, "east_west"),
            ("east_north_edge_01", (124.0, 32.85), 20.0, "east_west"),
            ("east_north_edge_02", (156.0, 32.85), 20.0, "east_west"),
            ("east_north_edge_03", (188.0, 32.85), 20.0, "east_west"),
            ("east_south_edge_01", (124.0, -32.85), 20.0, "east_west"),
            ("east_south_edge_02", (156.0, -32.85), 20.0, "east_west"),
            ("east_south_edge_03", (188.0, -32.85), 20.0, "east_west"),
            ("north_west_edge_01", (-63.2, 128.0), 24.0, "north_south"),
            ("north_west_edge_02", (-63.2, 160.0), 24.0, "north_south"),
            ("north_west_edge_03", (-63.2, 192.0), 24.0, "north_south"),
            ("north_east_edge_01", (63.2, 128.0), 24.0, "north_south"),
            ("north_east_edge_02", (63.2, 160.0), 24.0, "north_south"),
            ("north_east_edge_03", (63.2, 192.0), 24.0, "north_south"),
            ("south_west_edge_01", (-63.2, -128.0), 24.0, "north_south"),
            ("south_west_edge_02", (-63.2, -160.0), 24.0, "north_south"),
            ("south_west_edge_03", (-63.2, -192.0), 24.0, "north_south"),
            ("south_east_edge_01", (63.2, -128.0), 24.0, "north_south"),
            ("south_east_edge_02", (63.2, -160.0), 24.0, "north_south"),
            ("south_east_edge_03", (63.2, -192.0), 24.0, "north_south"),
            ("northwest_walk_edge_01", (-178.0, 118.9), 28.0, "east_west"),
            ("northwest_walk_edge_02", (-146.0, 118.9), 28.0, "east_west"),
            ("southwest_walk_edge_01", (-178.0, -118.9), 28.0, "east_west"),
            ("southwest_walk_edge_02", (-146.0, -118.9), 28.0, "east_west"),
            ("east_plaza_edge_01", (204.0, 68.0), 28.0, "north_south"),
            ("east_plaza_edge_02", (204.0, -68.0), 28.0, "north_south"),
            ("west_pool_edge_01", (-340.0, 68.0), 28.0, "north_south"),
            ("west_pool_edge_02", (-340.0, -68.0), 28.0, "north_south"),
        ]
        for name, center, length, orientation in sidewalk_grime_specs:
            add_sidewalk_grime_strip(f"public_sidewalk_grime_strip_{name}", center, length, orientation)

        sidewalk_stain_specs = [
            ("west_north_stain_01", (-330.0, 31.8), (2.8, 0.62), 4.0),
            ("west_north_stain_02", (-300.0, 31.7), (2.0, 0.54), -6.0),
            ("west_north_stain_03", (-264.0, 31.9), (2.6, 0.58), 8.0),
            ("west_north_stain_04", (-228.0, 31.6), (2.1, 0.50), -5.0),
            ("west_south_stain_01", (-330.0, -31.8), (2.8, 0.62), -4.0),
            ("west_south_stain_02", (-300.0, -31.7), (2.0, 0.54), 6.0),
            ("west_south_stain_03", (-264.0, -31.9), (2.6, 0.58), -8.0),
            ("west_south_stain_04", (-228.0, -31.6), (2.1, 0.50), 5.0),
            ("east_north_stain_01", (122.0, 31.9), (2.2, 0.54), 5.0),
            ("east_north_stain_02", (154.0, 31.7), (2.5, 0.58), -7.0),
            ("east_north_stain_03", (186.0, 31.8), (1.8, 0.46), 3.0),
            ("east_south_stain_01", (122.0, -31.9), (2.2, 0.54), -5.0),
            ("east_south_stain_02", (154.0, -31.7), (2.5, 0.58), 7.0),
            ("east_south_stain_03", (186.0, -31.8), (1.8, 0.46), -3.0),
            ("north_west_stain_01", (-62.2, 126.0), (0.56, 2.4), 3.0),
            ("north_west_stain_02", (-62.0, 158.0), (0.48, 2.0), -4.0),
            ("north_west_stain_03", (-62.3, 190.0), (0.52, 2.2), 6.0),
            ("north_east_stain_01", (62.2, 126.0), (0.56, 2.4), -3.0),
            ("north_east_stain_02", (62.0, 158.0), (0.48, 2.0), 4.0),
            ("north_east_stain_03", (62.3, 190.0), (0.52, 2.2), -6.0),
            ("south_west_stain_01", (-62.2, -126.0), (0.56, 2.4), -3.0),
            ("south_west_stain_02", (-62.0, -158.0), (0.48, 2.0), 4.0),
            ("south_west_stain_03", (-62.3, -190.0), (0.52, 2.2), -6.0),
            ("south_east_stain_01", (62.2, -126.0), (0.56, 2.4), 3.0),
            ("south_east_stain_02", (62.0, -158.0), (0.48, 2.0), -4.0),
            ("south_east_stain_03", (62.3, -190.0), (0.52, 2.2), 6.0),
            ("northwest_walk_stain_01", (-176.0, 118.0), (2.1, 0.50), 6.0),
            ("northwest_walk_stain_02", (-140.0, 118.0), (2.4, 0.54), -5.0),
            ("southwest_walk_stain_01", (-176.0, -118.0), (2.1, 0.50), -6.0),
            ("southwest_walk_stain_02", (-140.0, -118.0), (2.4, 0.54), 5.0),
            ("east_plaza_walk_stain", (204.0, 74.0), (0.54, 2.6), -4.0),
            ("west_pool_walk_stain", (-340.0, -74.0), (0.54, 2.6), 4.0),
        ]
        for name, center, size, angle_degrees in sidewalk_stain_specs:
            add_sidewalk_stain_patch(f"public_sidewalk_stain_patch_{name}", center, size, angle_degrees)

        curb_gutter_specs = [
            ("west_north_gutter_01", (-318.0, 29.65), 28.0, "east_west"),
            ("west_north_gutter_02", (-282.0, 29.65), 28.0, "east_west"),
            ("west_north_gutter_03", (-246.0, 29.65), 28.0, "east_west"),
            ("west_north_gutter_04", (-210.0, 29.65), 28.0, "east_west"),
            ("west_south_gutter_01", (-318.0, -29.65), 28.0, "east_west"),
            ("west_south_gutter_02", (-282.0, -29.65), 28.0, "east_west"),
            ("west_south_gutter_03", (-246.0, -29.65), 28.0, "east_west"),
            ("west_south_gutter_04", (-210.0, -29.65), 28.0, "east_west"),
            ("east_north_gutter_01", (124.0, 29.65), 24.0, "east_west"),
            ("east_north_gutter_02", (158.0, 29.65), 24.0, "east_west"),
            ("east_north_gutter_03", (192.0, 29.65), 24.0, "east_west"),
            ("east_south_gutter_01", (124.0, -29.65), 24.0, "east_west"),
            ("east_south_gutter_02", (158.0, -29.65), 24.0, "east_west"),
            ("east_south_gutter_03", (192.0, -29.65), 24.0, "east_west"),
            ("north_west_gutter_01", (-70.2, 128.0), 28.0, "north_south"),
            ("north_west_gutter_02", (-70.2, 164.0), 28.0, "north_south"),
            ("north_west_gutter_03", (-70.2, 196.0), 24.0, "north_south"),
            ("north_east_gutter_01", (70.2, 128.0), 28.0, "north_south"),
            ("north_east_gutter_02", (70.2, 164.0), 28.0, "north_south"),
            ("north_east_gutter_03", (70.2, 196.0), 24.0, "north_south"),
            ("south_west_gutter_01", (-70.2, -128.0), 28.0, "north_south"),
            ("south_west_gutter_02", (-70.2, -164.0), 28.0, "north_south"),
            ("south_west_gutter_03", (-70.2, -196.0), 24.0, "north_south"),
            ("south_east_gutter_01", (70.2, -128.0), 28.0, "north_south"),
            ("south_east_gutter_02", (70.2, -164.0), 28.0, "north_south"),
            ("south_east_gutter_03", (70.2, -196.0), 24.0, "north_south"),
            ("northwest_gutter_01", (-178.0, 110.7), 32.0, "east_west"),
            ("northwest_gutter_02", (-142.0, 110.7), 28.0, "east_west"),
            ("southwest_gutter_01", (-178.0, -110.7), 32.0, "east_west"),
            ("southwest_gutter_02", (-142.0, -110.7), 28.0, "east_west"),
            ("east_plaza_gutter", (206.4, 74.0), 32.0, "north_south"),
            ("west_pool_gutter", (-337.6, -74.0), 32.0, "north_south"),
        ]
        for name, center, length, orientation in curb_gutter_specs:
            add_curb_gutter_grime_strip(f"public_curb_gutter_grime_strip_{name}", center, length, orientation)

        bike_scuff_specs = [
            ("west_bike_scuff_01", (-326.0, 18.0), (5.2, 0.36), 1.5),
            ("west_bike_scuff_02", (-302.0, 18.0), (4.6, 0.30), -2.5),
            ("west_bike_scuff_03", (-278.0, 18.0), (5.0, 0.34), 2.0),
            ("west_bike_scuff_04", (-254.0, 18.0), (4.2, 0.28), -1.0),
            ("west_bike_scuff_05", (-230.0, 18.0), (5.4, 0.32), 1.0),
            ("west_bike_scuff_06", (-206.0, 18.0), (4.8, 0.30), -2.0),
            ("west_bike_scuff_07", (-326.0, -18.0), (5.0, 0.34), -1.5),
            ("west_bike_scuff_08", (-278.0, -18.0), (4.4, 0.28), 2.5),
            ("west_bike_scuff_09", (-230.0, -18.0), (5.2, 0.32), -2.0),
            ("east_bike_scuff_01", (124.0, -18.0), (4.2, 0.30), 2.0),
            ("east_bike_scuff_02", (148.0, -18.0), (4.8, 0.34), -2.0),
            ("east_bike_scuff_03", (172.0, -18.0), (4.0, 0.28), 1.5),
            ("east_bike_scuff_04", (196.0, -18.0), (4.6, 0.32), -1.5),
            ("north_bike_scuff_01", (-68.0, 132.0), (0.32, 4.8), -1.0),
            ("north_bike_scuff_02", (-68.0, 168.0), (0.30, 4.2), 1.5),
            ("north_bike_scuff_03", (-68.0, 198.0), (0.34, 4.6), -2.0),
            ("south_bike_scuff_01", (68.0, -132.0), (0.32, 4.8), 1.0),
            ("south_bike_scuff_02", (68.0, -168.0), (0.30, 4.2), -1.5),
            ("south_bike_scuff_03", (68.0, -198.0), (0.34, 4.6), 2.0),
            ("east_plaza_bike_scuff", (206.0, -42.0), (0.30, 4.0), 1.0),
        ]
        for name, center, size, angle_degrees in bike_scuff_specs:
            add_bike_lane_surface_scuff(f"public_bike_lane_surface_scuff_{name}", center, size, angle_degrees)

        crosswalk_wear_specs = [
            ("west_north_crosswalk_wear_01", (-225.4, 41.0), (1.45, 0.28), 0.0),
            ("west_north_crosswalk_wear_02", (-218.6, 41.0), (1.20, 0.24), 0.0),
            ("west_south_crosswalk_wear_01", (-225.4, -41.0), (1.45, 0.28), 0.0),
            ("west_south_crosswalk_wear_02", (-218.6, -41.0), (1.20, 0.24), 0.0),
            ("east_north_crosswalk_wear_01", (138.6, 41.0), (1.25, 0.24), 0.0),
            ("east_north_crosswalk_wear_02", (145.4, 41.0), (1.45, 0.28), 0.0),
            ("east_south_crosswalk_wear_01", (138.6, -41.0), (1.25, 0.24), 0.0),
            ("east_south_crosswalk_wear_02", (145.4, -41.0), (1.45, 0.28), 0.0),
            ("north_west_crosswalk_wear_01", (-54.0, 141.6), (0.28, 1.45), 0.0),
            ("north_west_crosswalk_wear_02", (-54.0, 148.4), (0.24, 1.20), 0.0),
            ("north_east_crosswalk_wear_01", (54.0, 141.6), (0.28, 1.45), 0.0),
            ("north_east_crosswalk_wear_02", (54.0, 148.4), (0.24, 1.20), 0.0),
            ("south_west_crosswalk_wear_01", (-54.0, -141.6), (0.28, 1.45), 0.0),
            ("south_west_crosswalk_wear_02", (-54.0, -148.4), (0.24, 1.20), 0.0),
            ("south_east_crosswalk_wear_01", (54.0, -141.6), (0.28, 1.45), 0.0),
            ("south_east_crosswalk_wear_02", (54.0, -148.4), (0.24, 1.20), 0.0),
            ("northwest_crosswalk_wear_01", (-151.5, 119.0), (1.35, 0.26), 0.0),
            ("northwest_crosswalk_wear_02", (-144.5, 119.0), (1.10, 0.22), 0.0),
            ("southwest_crosswalk_wear_01", (-151.5, -119.0), (1.35, 0.26), 0.0),
            ("southwest_crosswalk_wear_02", (-144.5, -119.0), (1.10, 0.22), 0.0),
            ("west_pool_crosswalk_wear_01", (-336.0, 3.6), (0.26, 1.35), 0.0),
            ("west_pool_crosswalk_wear_02", (-336.0, 10.4), (0.22, 1.10), 0.0),
            ("east_plaza_crosswalk_wear_01", (210.0, 3.6), (0.26, 1.35), 0.0),
            ("east_plaza_crosswalk_wear_02", (210.0, 10.4), (0.22, 1.10), 0.0),
        ]
        for name, center, size, angle_degrees in crosswalk_wear_specs:
            add_crosswalk_paint_wear_patch(f"public_crosswalk_paint_wear_patch_{name}", center, size, angle_degrees)

        tire_wear_specs = [
            ("west_lane_wear_01", (-318.0, -8.4), (28.0, 0.30), 0.0),
            ("west_lane_wear_02", (-318.0, 8.4), (28.0, 0.28), 0.0),
            ("west_lane_wear_03", (-266.0, -8.4), (28.0, 0.30), 0.0),
            ("west_lane_wear_04", (-266.0, 8.4), (28.0, 0.28), 0.0),
            ("west_lane_wear_05", (-214.0, -8.4), (28.0, 0.30), 0.0),
            ("west_lane_wear_06", (-214.0, 8.4), (28.0, 0.28), 0.0),
            ("east_lane_wear_01", (134.0, -8.4), (24.0, 0.28), 0.0),
            ("east_lane_wear_02", (134.0, 8.4), (24.0, 0.26), 0.0),
            ("east_lane_wear_03", (184.0, -8.4), (24.0, 0.28), 0.0),
            ("east_lane_wear_04", (184.0, 8.4), (24.0, 0.26), 0.0),
            ("north_lane_wear_01", (-42.0, 136.0), (0.28, 26.0), 0.0),
            ("north_lane_wear_02", (42.0, 164.0), (0.28, 26.0), 0.0),
            ("north_lane_wear_03", (-42.0, 192.0), (0.26, 24.0), 0.0),
            ("south_lane_wear_01", (42.0, -136.0), (0.28, 26.0), 0.0),
            ("south_lane_wear_02", (-42.0, -164.0), (0.28, 26.0), 0.0),
            ("south_lane_wear_03", (42.0, -192.0), (0.26, 24.0), 0.0),
        ]
        for name, center, size, angle_degrees in tire_wear_specs:
            add_road_tire_wear_band(f"public_road_tire_wear_band_{name}", center, size, angle_degrees)

        oil_stain_specs = [
            ("west_lane_oil_01", (-326.0, -5.2), (1.55, 0.54), -3.0),
            ("west_lane_oil_02", (-302.0, 6.4), (1.20, 0.46), 4.0),
            ("west_lane_oil_03", (-274.0, -7.6), (1.46, 0.50), -5.0),
            ("west_lane_oil_04", (-246.0, 7.2), (1.28, 0.44), 6.0),
            ("west_lane_oil_05", (-218.0, -6.0), (1.34, 0.48), -4.0),
            ("east_lane_oil_01", (128.0, 5.8), (1.20, 0.44), 3.0),
            ("east_lane_oil_02", (152.0, -6.8), (1.50, 0.52), -5.0),
            ("east_lane_oil_03", (178.0, 6.2), (1.18, 0.42), 5.0),
            ("east_lane_oil_04", (202.0, -7.4), (1.44, 0.50), -2.0),
            ("north_lane_oil_01", (-36.0, 132.0), (0.48, 1.36), 2.0),
            ("north_lane_oil_02", (36.0, 158.0), (0.52, 1.46), -3.0),
            ("north_lane_oil_03", (-36.0, 188.0), (0.44, 1.18), 4.0),
            ("south_lane_oil_01", (36.0, -132.0), (0.48, 1.36), -2.0),
            ("south_lane_oil_02", (-36.0, -158.0), (0.52, 1.46), 3.0),
            ("south_lane_oil_03", (36.0, -188.0), (0.44, 1.18), -4.0),
            ("west_pool_oil_01", (-340.0, 16.0), (0.48, 1.20), 2.0),
            ("east_plaza_oil_01", (210.0, -16.0), (0.46, 1.18), -2.0),
            ("northwest_curve_oil", (-160.0, 104.0), (1.10, 0.42), 14.0),
            ("southwest_curve_oil", (-160.0, -104.0), (1.10, 0.42), -14.0),
            ("east_service_oil", (206.0, 92.0), (0.48, 1.12), 3.0),
        ]
        for name, center, size, angle_degrees in oil_stain_specs:
            add_road_oil_stain(f"public_road_oil_stain_{name}", center, size, angle_degrees)

        gum_mark_centers = [
            (-326.0, 34.1), (-314.0, 33.8), (-302.0, 34.2), (-290.0, 33.9), (-278.0, 34.0), (-266.0, 34.2),
            (-254.0, -34.1), (-242.0, -33.8), (-230.0, -34.2), (-218.0, -33.9), (-206.0, -34.0), (-194.0, -34.2),
            (122.0, 34.1), (134.0, 33.8), (146.0, 34.2), (158.0, 33.9), (170.0, -34.1), (182.0, -33.8),
            (194.0, -34.2), (206.0, -33.9), (-63.8, 128.0), (-63.9, 142.0), (-64.1, 156.0), (-63.8, 170.0),
            (63.8, 128.0), (63.9, 142.0), (64.1, 156.0), (63.8, 170.0), (-63.8, -128.0), (-63.9, -142.0),
            (-64.1, -156.0), (-63.8, -170.0), (63.8, -128.0), (63.9, -142.0), (64.1, -156.0), (63.8, -170.0),
            (-178.0, 119.4), (-166.0, 119.2), (-154.0, 119.5), (-142.0, 119.3), (-178.0, -119.4), (-166.0, -119.2),
            (-154.0, -119.5), (-142.0, -119.3), (204.5, 74.0), (204.6, 62.0), (-340.5, 74.0), (-340.6, -62.0),
        ]
        for idx, center in enumerate(gum_mark_centers, start=1):
            radius = 0.055 + stable_unit_interval("public_sidewalk_gum_mark", idx) * 0.035
            add_sidewalk_gum_mark(f"public_sidewalk_gum_mark_{idx:02d}", center, radius)

        leaf_cluster_centers = [
            (-330.0, 35.0), (-306.0, 35.2), (-282.0, 35.0), (-258.0, 35.1), (-234.0, -35.0), (-210.0, -35.2),
            (126.0, 35.0), (150.0, 35.2), (174.0, -35.0), (198.0, -35.2), (-66.0, 132.0), (-66.2, 156.0),
            (66.0, 132.0), (66.2, 156.0), (-66.0, -132.0), (-66.2, -156.0), (66.0, -132.0), (66.2, -156.0),
            (-182.0, 121.0), (-158.0, 121.2), (-134.0, 121.0), (-182.0, -121.0), (-158.0, -121.2), (-134.0, -121.0),
            (206.0, 72.0), (206.0, -72.0), (-338.0, 72.0), (-338.0, -72.0),
        ]
        for idx, center in enumerate(leaf_cluster_centers, start=1):
            radius = 0.46 + stable_unit_interval("public_sidewalk_leaf_litter", idx) * 0.18
            add_sidewalk_leaf_litter_cluster(f"public_sidewalk_leaf_litter_cluster_{idx:02d}", center, radius)

        curb_grime_patch_specs = [
            ("west_north_curb_patch_01", (-326.0, 30.3), (2.4, 0.32), 0.0),
            ("west_north_curb_patch_02", (-294.0, 30.3), (2.0, 0.28), 0.0),
            ("west_north_curb_patch_03", (-262.0, 30.3), (2.6, 0.34), 0.0),
            ("west_north_curb_patch_04", (-230.0, 30.3), (2.1, 0.30), 0.0),
            ("west_south_curb_patch_01", (-326.0, -30.3), (2.4, 0.32), 0.0),
            ("west_south_curb_patch_02", (-294.0, -30.3), (2.0, 0.28), 0.0),
            ("west_south_curb_patch_03", (-262.0, -30.3), (2.6, 0.34), 0.0),
            ("west_south_curb_patch_04", (-230.0, -30.3), (2.1, 0.30), 0.0),
            ("east_north_curb_patch_01", (126.0, 30.3), (2.2, 0.30), 0.0),
            ("east_north_curb_patch_02", (158.0, 30.3), (2.6, 0.34), 0.0),
            ("east_south_curb_patch_01", (126.0, -30.3), (2.2, 0.30), 0.0),
            ("east_south_curb_patch_02", (158.0, -30.3), (2.6, 0.34), 0.0),
            ("north_west_curb_patch_01", (-70.8, 132.0), (0.32, 2.2), 0.0),
            ("north_west_curb_patch_02", (-70.8, 164.0), (0.34, 2.6), 0.0),
            ("north_east_curb_patch_01", (70.8, 132.0), (0.32, 2.2), 0.0),
            ("north_east_curb_patch_02", (70.8, 164.0), (0.34, 2.6), 0.0),
            ("south_west_curb_patch_01", (-70.8, -132.0), (0.32, 2.2), 0.0),
            ("south_west_curb_patch_02", (-70.8, -164.0), (0.34, 2.6), 0.0),
            ("south_east_curb_patch_01", (70.8, -132.0), (0.32, 2.2), 0.0),
            ("south_east_curb_patch_02", (70.8, -164.0), (0.34, 2.6), 0.0),
            ("northwest_curb_patch_01", (-178.0, 111.3), (2.4, 0.32), 0.0),
            ("northwest_curb_patch_02", (-146.0, 111.3), (2.0, 0.28), 0.0),
            ("southwest_curb_patch_01", (-178.0, -111.3), (2.4, 0.32), 0.0),
            ("southwest_curb_patch_02", (-146.0, -111.3), (2.0, 0.28), 0.0),
        ]
        for name, center, size, angle_degrees in curb_grime_patch_specs:
            add_curb_grime_patch(f"public_curb_grime_patch_{name}", center, size, angle_degrees)

        for idx, (center, orientation) in enumerate(
            [
                ((-238.0, 34.5), "east_west"), ((-202.0, -34.5), "east_west"), ((-166.0, 34.5), "east_west"),
                ((126.0, -34.5), "east_west"), ((166.0, 34.5), "east_west"), ((206.0, -34.5), "east_west"),
                ((-82.0, 136.0), "north_south"), ((82.0, 136.0), "north_south"), ((-82.0, -136.0), "north_south"), ((82.0, -136.0), "north_south"),
                ((-188.0, 126.0), "east_west"), ((-188.0, -126.0), "east_west"),
            ],
            start=1,
        ):
            add_public_utility_box(f"public_utility_box_{idx:02d}", center, orientation)

        for idx, (center, material) in enumerate(
            [
                ((-246.0, 34.5), "MarkerBlue"), ((-210.0, -34.5), "StreetSignGreen"), ((-174.0, 34.5), "MarkerBlue"),
                ((134.0, -34.5), "StreetSignGreen"), ((174.0, 34.5), "MarkerBlue"), ((214.0, -34.5), "StreetSignGreen"),
                ((-90.0, 136.0), "MarkerBlue"), ((90.0, -136.0), "StreetSignGreen"),
                ((-196.0, 126.0), "MarkerBlue"), ((-196.0, -126.0), "StreetSignGreen"),
                ((198.0, 116.0), "MarkerBlue"), ((198.0, -116.0), "StreetSignGreen"),
            ],
            start=1,
        ):
            add_public_news_box(f"public_news_box_{idx:02d}", center, material)

        for name, center, label, orientation in [
            ("west_public_wayfinding_pool", (-245.0, -26.0), "Reflecting Pool / West Front", "east_west"),
            ("west_public_wayfinding_capitol", (-138.0, 26.0), "Capitol / Visitor Orientation", "east_west"),
            ("east_public_wayfinding_plaza", (156.0, 28.0), "East Plaza / Capitol", "east_west"),
            ("north_public_wayfinding", (-74.0, 132.0), "North Public Walk", "east_west"),
            ("south_public_wayfinding", (74.0, -132.0), "South Public Walk", "east_west"),
            ("northwest_public_wayfinding", (-186.0, 118.0), "Public Walk / Streets", "east_west"),
            ("southwest_public_wayfinding", (-186.0, -118.0), "Public Walk / Streets", "east_west"),
            ("east_public_wayfinding_bike", (196.0, -28.0), "Bike Lane / Public Walk", "east_west"),
        ]:
            add_public_wayfinding_sign(name, center, label, orientation)

        for idx, (x, y, orientation) in enumerate(
            [
                (-226.0, -36.0, "east_west"),
                (-196.0, -36.0, "east_west"),
                (-166.0, -36.0, "east_west"),
                (-136.0, -36.0, "east_west"),
                (124.0, 36.0, "east_west"),
                (154.0, 36.0, "east_west"),
                (184.0, 36.0, "east_west"),
                (-72.0, 134.0, "north_south"),
                (72.0, 134.0, "north_south"),
                (-72.0, -134.0, "north_south"),
                (72.0, -134.0, "north_south"),
                (214.0, -34.0, "east_west"),
            ],
            start=1,
        ):
            add_public_bike_rack(f"public_bike_rack_{idx:02d}", (x, y), orientation)

        for idx, (x, y) in enumerate(
            [
                (-252.0, 28.0),
                (-228.0, -28.0),
                (-188.0, 28.0),
                (-148.0, -28.0),
                (-108.0, 30.0),
                (112.0, -30.0),
                (146.0, 30.0),
                (180.0, -30.0),
                (-84.0, 118.0),
                (84.0, 118.0),
                (-84.0, -118.0),
                (84.0, -118.0),
                (-182.0, 118.0),
                (-182.0, -118.0),
                (202.0, 116.0),
                (202.0, -116.0),
            ],
            start=1,
        ):
            add_public_trash_receptacle(f"public_trash_receptacle_{idx:02d}", (x, y))

        for idx, (x, y, orientation) in enumerate(
            [
                (-318.0, 42.0, "east_west"),
                (-270.0, -42.0, "east_west"),
                (-198.0, 42.0, "east_west"),
                (-126.0, -42.0, "east_west"),
                (126.0, 42.0, "east_west"),
                (184.0, -42.0, "east_west"),
                (-96.0, 152.0, "north_south"),
                (96.0, -152.0, "north_south"),
            ],
            start=1,
        ):
            add_bus_stop_shelter(f"public_bus_stop_shelter_{idx:02d}", (x, y), orientation)

        for idx, (x, y) in enumerate(
            [
                (-338.0, 32.0),
                (-302.0, -32.0),
                (-266.0, 32.0),
                (-230.0, -32.0),
                (-194.0, 32.0),
                (-158.0, -32.0),
                (-122.0, 32.0),
                (116.0, -32.0),
                (148.0, 32.0),
                (180.0, -32.0),
                (212.0, 32.0),
                (-96.0, 126.0),
                (96.0, 126.0),
                (-96.0, -126.0),
                (96.0, -126.0),
                (208.0, -92.0),
            ],
            start=1,
        ):
            add_public_hydrant(f"public_hydrant_marker_{idx:02d}", (x, y))

    def add_grounds_record(
        name: str,
        kind: str,
        center: tuple[float, float, float],
        size: tuple[float, float] | None = None,
        public_accuracy: str = "approximate_public_grounds_visual",
        extra: dict[str, Any] | None = None,
    ) -> None:
        record: dict[str, Any] = {
            "name": name,
            "kind": kind,
            "center_m": [round(center[0], 3), round(center[1], 3), round(center[2], 3)],
            "public_accuracy": public_accuracy,
        }
        if size is not None:
            record["size_m"] = [round(size[0], 3), round(size[1], 3)]
        if extra:
            record.update(extra)
        metadata["grounds_details"].append(record)

    def add_grounds_box(
        name: str,
        kind: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
        height: float,
        material: str,
    ) -> None:
        roads.add_box(center, size, height, z, name, material)
        add_grounds_record(name, kind, (center[0], center[1], z + height / 2.0), size)

    def add_grounds_path(name: str, points: list[tuple[float, float]], width: float, material: str = "PlazaStone") -> None:
        roads.add_polyline_strip(points, width, 0.165, name, material)
        center = polyline_midpoint(points)
        length = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:]))
        add_grounds_record(name, "public_walk", (center[0], center[1], 0.18), (length, width))

    def add_grounds_tree(name: str, center: tuple[float, float]) -> None:
        x, y = center
        roads.add_cylinder((x, y), 0.16, 0.09, 1.85, f"{name}_trunk", "TreeTrunk", segments=10)
        roads.add_cylinder((x, y), 0.92, 1.45, 0.90, f"{name}_lower_canopy", "TreeCanopy", segments=16)
        roads.add_cylinder((x, y), 0.70, 2.05, 0.80, f"{name}_upper_canopy", "TreeCanopy", segments=16)
        roads.add_cylinder((x, y), 1.02, 0.07, 0.16, f"{name}_planter_ring", "PlanterStone", segments=16)
        add_grounds_record(name, "public_tree_allee", (x, y, 1.55), (2.1, 2.1))

    def add_grounds_lamp(name: str, center: tuple[float, float]) -> None:
        x, y = center
        roads.add_cylinder((x, y), 0.055, 0.10, 3.25, f"{name}_pole", "StreetLightPole", segments=10)
        roads.add_cylinder((x, y), 0.16, 3.08, 0.32, f"{name}_glass", "StreetLightGlass", segments=12)
        add_grounds_record(
            name,
            "public_walk_lamp",
            (x, y, 1.75),
            (0.36, 0.36),
            public_accuracy="schematic_public_grounds_lighting",
            extra={
                "light_m": [round(x, 3), round(y, 3), 3.22],
                "intensity": 360.0,
                "attenuation_radius_m": 8.0,
                "color": [1.0, 0.82, 0.55],
            },
        )

    def add_grounds_hedge(name: str, center: tuple[float, float], size: tuple[float, float]) -> None:
        roads.add_box(center, size, 0.42, 0.12, name, "TreeCanopy")
        add_grounds_record(name, "public_hedge", (center[0], center[1], 0.33), size)

    def add_path_edge_stone(name: str, center: tuple[float, float], size: tuple[float, float]) -> None:
        roads.add_box(center, size, 0.08, 0.16, name, "StepStone")
        add_grounds_record(name, "path_edge_stone", (center[0], center[1], 0.20), size)

    def add_grounds_bench(name: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        if orientation == "north_south":
            roads.add_box((x, y), (0.42, 2.15), 0.16, 0.46, f"{name}_seat", "BenchWood")
            roads.add_box((x + 0.24, y), (0.12, 2.15), 0.62, 0.54, f"{name}_back", "BenchWood")
            for leg_index, ly in enumerate([-0.78, 0.78], start=1):
                roads.add_box((x, y + ly), (0.32, 0.12), 0.42, 0.08, f"{name}_leg_{leg_index}", "BollardMetal")
            size = (0.62, 2.15)
        else:
            roads.add_box((x, y), (2.15, 0.42), 0.16, 0.46, f"{name}_seat", "BenchWood")
            roads.add_box((x, y + 0.24), (2.15, 0.12), 0.62, 0.54, f"{name}_back", "BenchWood")
            for leg_index, lx in enumerate([-0.78, 0.78], start=1):
                roads.add_box((x + lx, y), (0.12, 0.32), 0.42, 0.08, f"{name}_leg_{leg_index}", "BollardMetal")
            size = (2.15, 0.62)
        add_grounds_record(name, "grounds_bench", (x, y, 0.72), size)

    def add_ornamental_planting_cluster(name: str, center: tuple[float, float]) -> None:
        x, y = center
        roads.add_cylinder((x, y), 0.62, 0.09, 0.12, f"{name}_stone_ring", "PlanterStone", segments=14)
        for index, (dx, dy, radius) in enumerate([(-0.22, -0.12, 0.22), (0.18, -0.10, 0.18), (0.02, 0.20, 0.20)], start=1):
            roads.add_cylinder((x + dx, y + dy), radius, 0.15, 0.34, f"{name}_shrub_{index}", "TreeCanopy", segments=10)
        add_grounds_record(name, "ornamental_planting_cluster", (x, y, 0.32), (1.35, 1.35))

    def add_capitol_grounds_details() -> None:
        # Broad public landscape shapes around the Capitol, authored as
        # approximate visual context rather than survey-grade grounds design.
        for name, center, size in [
            ("west_north_lawn_panel", (-188.0, 58.0), (150.0, 74.0)),
            ("west_south_lawn_panel", (-188.0, -58.0), (150.0, 74.0)),
            ("east_north_lawn_panel", (145.0, 58.0), (112.0, 70.0)),
            ("east_south_lawn_panel", (145.0, -58.0), (112.0, 70.0)),
            ("north_public_lawn_panel", (0.0, 148.0), (156.0, 62.0)),
            ("south_public_lawn_panel", (0.0, -148.0), (156.0, 62.0)),
        ]:
            add_grounds_box(name, "lawn_panel", center, size, 0.022, 0.026, "GroundGrass")

        for name, points, width in [
            ("west_axial_public_walk", [(-93.0, 0.0), (-174.0, 0.0), (-260.0, 0.0), (-352.0, 0.0)], 8.5),
            ("east_axial_public_walk", [(93.0, 0.0), (145.0, 0.0), (205.0, 0.0)], 7.0),
            ("north_public_crosswalk_path", [(-68.0, 119.0), (0.0, 124.0), (68.0, 119.0)], 4.4),
            ("south_public_crosswalk_path", [(-68.0, -119.0), (0.0, -124.0), (68.0, -119.0)], 4.4),
            ("northwest_diagonal_public_walk", [(-84.0, 48.0), (-156.0, 96.0), (-248.0, 126.0)], 4.0),
            ("southwest_diagonal_public_walk", [(-84.0, -48.0), (-156.0, -96.0), (-248.0, -126.0)], 4.0),
            ("northeast_diagonal_public_walk", [(84.0, 48.0), (130.0, 88.0), (184.0, 118.0)], 3.8),
            ("southeast_diagonal_public_walk", [(84.0, -48.0), (130.0, -88.0), (184.0, -118.0)], 3.8),
        ]:
            add_grounds_path(name, points, width)

        add_grounds_box("west_reflecting_pool_public_marker", "reflecting_pool", (-286.0, 0.0), (82.0, 30.0), 0.135, 0.04, "MarkerBlue")
        for name, center, size in [
            ("west_reflecting_pool_north_edge", (-286.0, 15.45), (84.0, 0.55)),
            ("west_reflecting_pool_south_edge", (-286.0, -15.45), (84.0, 0.55)),
            ("west_reflecting_pool_east_edge", (-244.75, 0.0), (0.55, 31.0)),
            ("west_reflecting_pool_west_edge", (-327.25, 0.0), (0.55, 31.0)),
        ]:
            add_grounds_box(name, "pool_coping", center, size, 0.14, 0.10, "StepStone")

        for idx, (x, y) in enumerate(
            [(-112.0, 76.0), (-112.0, -76.0), (-150.0, 76.0), (-150.0, -76.0), (105.0, 72.0), (105.0, -72.0), (146.0, 72.0), (146.0, -72.0)],
            start=1,
        ):
            add_grounds_box(f"formal_planting_bed_{idx:02d}_stone_edge", "formal_planting_bed", (x, y), (18.0, 5.2), 0.08, 0.16, "PlanterStone")
            add_grounds_box(f"formal_planting_bed_{idx:02d}_grass_inset", "formal_planting_bed", (x, y), (16.6, 3.8), 0.18, 0.03, "GroundGrass")

        tree_index = 1
        for y in (-23.0, 23.0):
            for x in [-338.0, -318.0, -298.0, -278.0, -258.0, -238.0, -218.0, -198.0, -178.0, -158.0, -138.0]:
                add_grounds_tree(f"west_public_tree_allee_{tree_index:02d}", (x, y))
                tree_index += 1
        for y in (-26.0, 26.0):
            for x in [112.0, 132.0, 152.0, 172.0, 192.0]:
                add_grounds_tree(f"east_public_tree_allee_{tree_index:02d}", (x, y))
                tree_index += 1
        for x in (-72.0, 72.0):
            for y in [-170.0, -150.0, -130.0, 130.0, 150.0, 170.0]:
                add_grounds_tree(f"north_south_public_tree_allee_{tree_index:02d}", (x, y))
                tree_index += 1

        lamp_index = 1
        for y in (-11.0, 11.0):
            for x in [-340.0, -300.0, -260.0, -220.0, -180.0, -140.0]:
                add_grounds_lamp(f"west_public_walk_lamp_{lamp_index:02d}", (x, y))
                lamp_index += 1
        for y in (-10.0, 10.0):
            for x in [116.0, 156.0, 196.0]:
                add_grounds_lamp(f"east_public_walk_lamp_{lamp_index:02d}", (x, y))
                lamp_index += 1

        for name, center, size in [
            ("west_plaza_low_wall_north", (-84.0, 86.0), (52.0, 0.45)),
            ("west_plaza_low_wall_south", (-84.0, -86.0), (52.0, 0.45)),
            ("east_plaza_low_wall_north", (84.0, 86.0), (52.0, 0.45)),
            ("east_plaza_low_wall_south", (84.0, -86.0), (52.0, 0.45)),
        ]:
            add_grounds_box(name, "low_plaza_wall", center, size, 0.12, 0.46, "StepStone")

        for name, center, size in [
            ("west_north_lawn_inner_hedge", (-140.0, 21.0), (82.0, 0.72)),
            ("west_south_lawn_inner_hedge", (-140.0, -21.0), (82.0, 0.72)),
            ("west_outer_north_hedge", (-225.0, 96.0), (74.0, 0.70)),
            ("west_outer_south_hedge", (-225.0, -96.0), (74.0, 0.70)),
            ("east_north_lawn_inner_hedge", (132.0, 23.0), (64.0, 0.70)),
            ("east_south_lawn_inner_hedge", (132.0, -23.0), (64.0, 0.70)),
            ("east_outer_north_hedge", (170.0, 94.0), (46.0, 0.68)),
            ("east_outer_south_hedge", (170.0, -94.0), (46.0, 0.68)),
            ("north_lawn_west_hedge", (-58.0, 126.0), (0.70, 42.0)),
            ("north_lawn_east_hedge", (58.0, 126.0), (0.70, 42.0)),
            ("south_lawn_west_hedge", (-58.0, -126.0), (0.70, 42.0)),
            ("south_lawn_east_hedge", (58.0, -126.0), (0.70, 42.0)),
        ]:
            add_grounds_hedge(name, center, size)

        for name, center, size in [
            ("west_axial_walk_north_edge_01", (-154.0, 4.58), (110.0, 0.22)),
            ("west_axial_walk_south_edge_01", (-154.0, -4.58), (110.0, 0.22)),
            ("west_axial_walk_north_edge_02", (-286.0, 4.58), (126.0, 0.22)),
            ("west_axial_walk_south_edge_02", (-286.0, -4.58), (126.0, 0.22)),
            ("east_axial_walk_north_edge", (151.0, 3.85), (112.0, 0.20)),
            ("east_axial_walk_south_edge", (151.0, -3.85), (112.0, 0.20)),
            ("north_crosswalk_path_edge_west", (-34.0, 121.9), (48.0, 0.18)),
            ("north_crosswalk_path_edge_east", (34.0, 121.9), (48.0, 0.18)),
            ("south_crosswalk_path_edge_west", (-34.0, -121.9), (48.0, 0.18)),
            ("south_crosswalk_path_edge_east", (34.0, -121.9), (48.0, 0.18)),
            ("northwest_diagonal_path_edge", (-170.0, 100.0), (52.0, 0.18)),
            ("southwest_diagonal_path_edge", (-170.0, -100.0), (52.0, 0.18)),
            ("northeast_diagonal_path_edge", (135.0, 90.0), (38.0, 0.18)),
            ("southeast_diagonal_path_edge", (135.0, -90.0), (38.0, 0.18)),
            ("west_pool_north_walk_edge", (-286.0, 19.8), (86.0, 0.18)),
            ("west_pool_south_walk_edge", (-286.0, -19.8), (86.0, 0.18)),
        ]:
            add_path_edge_stone(name, center, size)

        for idx, (center, orientation) in enumerate(
            [
                ((-212.0, 12.5), "east_west"), ((-212.0, -12.5), "east_west"),
                ((-272.0, 20.8), "east_west"), ((-272.0, -20.8), "east_west"),
                ((-336.0, 20.8), "east_west"), ((-336.0, -20.8), "east_west"),
                ((122.0, 12.0), "east_west"), ((122.0, -12.0), "east_west"),
                ((174.0, 12.0), "east_west"), ((174.0, -12.0), "east_west"),
                ((-78.0, 124.0), "north_south"), ((78.0, 124.0), "north_south"),
                ((-78.0, -124.0), "north_south"), ((78.0, -124.0), "north_south"),
                ((-112.0, 88.0), "east_west"), ((112.0, -88.0), "east_west"),
            ],
            start=1,
        ):
            add_grounds_bench(f"public_grounds_bench_{idx:02d}", center, orientation)

        cluster_centers = [
            (-112.0, 68.0), (-112.0, -68.0), (-150.0, 68.0), (-150.0, -68.0),
            (105.0, 64.0), (105.0, -64.0), (146.0, 64.0), (146.0, -64.0),
            (-102.0, 84.0), (-102.0, -84.0), (-160.0, 84.0), (-160.0, -84.0),
            (96.0, 80.0), (96.0, -80.0), (156.0, 80.0), (156.0, -80.0),
            (-92.0, 36.0), (-92.0, -36.0), (92.0, 36.0), (92.0, -36.0),
            (-64.0, 116.0), (64.0, 116.0), (-64.0, -116.0), (64.0, -116.0),
        ]
        for idx, center in enumerate(cluster_centers, start=1):
            add_ornamental_planting_cluster(f"ornamental_public_planting_cluster_{idx:02d}", center)

    for way in ways:
        tags = way.get("tags", {})
        points = way_points(way, nodes)
        if len(points) < 2:
            continue
        name = tags.get("name") or tags.get("official_name") or f"osm_way_{way['id']}"
        is_capitol = "capitol" in name.lower() and tags.get("building")
        is_us_capitol = tags.get("wikidata") == "Q54109" or name == "United States Capitol"

        if tags.get("building") and len(points) >= 3:
            cx = sum(p[0] for p in points) / len(points)
            cy = sum(p[1] for p in points) / len(points)
            footprint_area = polygon_area_m2(points)
            footprint_span = footprint_span_m(points)
            height, height_source = parse_height(
                tags,
                is_us_capitol,
                int(way["id"]),
                name,
                footprint_area,
                footprint_span,
            )
            height_provenance: dict[str, Any] | None = None
            if height_source == "footprint_type_area_estimate":
                dcgis_height = dcgis_height_estimate(points, height, dcgis_rooftop_points, dcgis_ground_points)
                if dcgis_height:
                    height = float(dcgis_height["height_m"])
                    height_source = "dcgis_rooftop_ground_delta_estimate"
                    dcgis_height_match_count += 1
                    height_provenance = {
                        "source": "DCGIS Planimetrics 1999 rooftop and ground elevation points",
                        "source_file": dcgis_elevation_model.get("source_file"),
                        "method": dcgis_height["method"],
                        "roof_point_count": dcgis_height["roof_point_count"],
                        "ground_point_count": dcgis_height["ground_point_count"],
                        "roof_elevation_m": round(float(dcgis_height["roof_elevation_m"]), 3),
                        "ground_elevation_m": round(float(dcgis_height["ground_elevation_m"]), 3),
                        "nearest_ground_distance_m": dcgis_height["nearest_ground_distance_m"],
                        "roof_object_ids": dcgis_height["roof_object_ids"],
                        "ground_object_ids": dcgis_height["ground_object_ids"],
                    }
            if is_us_capitol:
                metadata["replaced_buildings"].append(
                    {
                        "id": way["id"],
                        "name": name,
                        "center_m": [round(cx, 3), round(cy, 3), round(height / 2.0, 3)],
                        "height_m": round(height, 2),
                        "height_source": height_source,
                        "footprint_area_m2": round(footprint_area, 2),
                        "footprint_span_m": round(footprint_span, 2),
                        "reason": "Skipped concave OSM extrusion; replaced by authored Capitol landmark visual mesh.",
                        "tags": tags,
                    }
                )
            else:
                material = "BuildingCapitol" if is_capitol else "BuildingGeneric"
                buildings.add_extruded_polygon(points, 0.0, height, f"building_{name}_{way['id']}", material)
                add_surrounding_building_visuals(way["id"], name, points, height, (cx, cy))
                height_accuracy = building_height_accuracy_record(
                    height_source,
                    height,
                    footprint_area,
                    footprint_span,
                    tags,
                    bool(height_provenance),
                )
                building_record = {
                    "id": way["id"],
                    "name": name,
                    "height_m": round(height, 2),
                    "height_source": height_source,
                    "footprint_area_m2": round(footprint_area, 2),
                    "footprint_span_m": round(footprint_span, 2),
                    "center_m": [round(cx, 3), round(cy, 3), round(height / 2.0, 3)],
                    "tags": tags,
                }
                building_record.update(height_accuracy)
                if height_provenance:
                    building_record["height_provenance"] = height_provenance
                metadata["buildings"].append(building_record)

        if tags.get("highway"):
            width = road_width(tags)
            highway = tags.get("highway")
            if highway == "cycleway":
                material = "BikeLaneGreen"
            elif highway in {"footway", "path", "steps", "pedestrian"}:
                material = "SidewalkConcrete"
            else:
                material = "RoadAsphalt"
            z = 0.08 if material == "BikeLaneGreen" else 0.03
            roads.add_polyline_strip(points, width, z, f"road_{name}_{way['id']}", material)
            if highway in {"footway", "path", "steps", "pedestrian"}:
                metadata["pedestrian_paths"].append(
                    {
                        "id": way["id"],
                        "name": name,
                        "highway": highway,
                        "width_m": width,
                        "tags": tags,
                    }
                )
            if tags.get("highway") not in {"footway", "path", "steps", "cycleway"} and width >= 5.0:
                roads.add_polyline_strip(points, 0.18, 0.14, f"lane_marking_{name}_{way['id']}", "LaneMarkingYellow")
                left_edge = offset_polyline(points, width / 2.0 - 0.35)
                right_edge = offset_polyline(points, -(width / 2.0 - 0.35))
                roads.add_polyline_strip(left_edge, 0.12, 0.145, f"left_edge_line_{name}_{way['id']}", "LaneMarkingWhite")
                roads.add_polyline_strip(right_edge, 0.12, 0.145, f"right_edge_line_{name}_{way['id']}", "LaneMarkingWhite")
                metadata["lane_edge_markings"].append(
                    {
                        "id": way["id"],
                        "name": name,
                        "kind": "white_edge_lines",
                        "sides": ["left", "right"],
                    }
                )

                for side in ("left", "right"):
                    side_sign = 1.0 if side == "left" else -1.0
                    curb_line = offset_polyline(points, side_sign * (width / 2.0 + 0.12))
                    roads.add_polyline_strip(curb_line, 0.22, 0.18, f"{side}_curb_{name}_{way['id']}", "CurbConcrete")
                    metadata["curbs"].append(
                        {
                            "id": way["id"],
                            "name": name,
                            "side": side,
                            "offset_m": round(side_sign * (width / 2.0 + 0.12), 3),
                        }
                    )

                for side in sidewalk_sides(tags):
                    side_sign = 1.0 if side == "left" else -1.0
                    sidewalk_line = offset_polyline(points, side_sign * (width / 2.0 + 1.55))
                    roads.add_polyline_strip(sidewalk_line, 2.4, 0.10, f"{side}_sidewalk_{name}_{way['id']}", "SidewalkConcrete")
                    metadata["sidewalks"].append(
                        {
                            "id": way["id"],
                            "name": name,
                            "side": side,
                            "width_m": 2.4,
                            "source_tag": tags.get("sidewalk") or tags.get(f"sidewalk:{side}") or "sidewalk",
                        }
                    )
                if streetlight_count < 260:
                    for side in ("left", "right"):
                        side_sign = 1.0 if side == "left" else -1.0
                        lamp_line = offset_polyline(points, side_sign * (width / 2.0 + 2.25))
                        for px, py in sample_polyline(lamp_line, spacing=85.0)[:3]:
                            if streetlight_count >= 260:
                                break
                            if not on_central_campus((px, py)):
                                continue
                            streetlight_count += 1
                            add_streetlight(f"streetlight_{way['id']}_{streetlight_count:03d}", (px, py), side_sign)
                if street_sign_count < 180 and name and not name.startswith("osm_way_"):
                    mx, my = polyline_midpoint(points)
                    if on_central_campus((mx, my)):
                        street_sign_count += 1
                        add_street_sign(f"street_name_sign_{way['id']}", (mx, my), name)
            if name and not name.startswith("osm_way_") and tags.get("highway") not in {"footway", "path", "steps"}:
                mx, my = polyline_midpoint(points)
                metadata["street_labels"].append(
                    {
                        "text": name,
                        "location_m": [round(mx, 3), round(my, 3), 2.0],
                        "category": "street_name",
                        "highway": tags.get("highway"),
                    }
                )
            metadata["roads"].append(
                {
                    "id": way["id"],
                    "name": name,
                    "highway": tags.get("highway"),
                    "width_m": width,
                    "tags": tags,
                }
            )

            if is_bike_feature(tags):
                bike_width = 2.0 if tags.get("highway") != "cycleway" else 2.6
                roads.add_polyline_strip(points, bike_width, 0.12, f"bike_lane_{name}_{way['id']}", "BikeLaneGreen")
                for post_index, (px, py) in enumerate(sample_polyline(points, spacing=24.0)[:12], start=1):
                    roads.add_box((px, py), (0.32, 0.32), 1.0, 0.05, f"bike_lane_marker_{way['id']}_{post_index}", "BikeLanePost")
                metadata["bike_lanes"].append(
                    {
                        "id": way["id"],
                        "name": name,
                        "type": tags.get("cycleway") or tags.get("highway") or "bike_lane",
                        "tags": tags,
                    }
                )
            if tree_count < 220 and highway in {"footway", "path", "pedestrian"}:
                tree_line = offset_polyline(points, 2.4)
                for px, py in sample_polyline(tree_line, spacing=42.0)[:4]:
                    if tree_count >= 220:
                        break
                    if not on_central_campus((px, py)):
                        continue
                    tree_count += 1
                    add_tree(f"campus_tree_planter_{way['id']}_{tree_count:03d}", (px, py))

    # Node street markers are in the OSM element list, so read them directly.
    source_data = json.loads(SOURCE.read_text(encoding="utf-8"))
    for element in source_data.get("elements", []):
        if element.get("type") != "node" or "lat" not in element or "lon" not in element:
            continue
        tags = element.get("tags", {})
        if not (tags.get("highway") == "traffic_signals" or tags.get("crossing")):
            continue
        x, y = local_xy(float(element["lat"]), float(element["lon"]))
        is_signal = tags.get("highway") == "traffic_signals"
        material = "SignalMarker" if is_signal else "CrosswalkWhite"
        size = (1.2, 1.2) if material == "SignalMarker" else (1.8, 1.8)
        marker_height = 0.08 if is_signal else 0.035
        roads.add_box((x, y), size, marker_height, 0.16, f"street_marker_{element['id']}", material)
        if is_signal:
            traffic_signal_count += 1
            add_traffic_signal(f"traffic_signal_{element['id']}", (x, y))
        else:
            add_crosswalk_stripes(f"crosswalk_{element['id']}", (x, y))
        metadata["street_markers"].append(
            {
                "id": element["id"],
                "kind": "traffic_signal" if material == "SignalMarker" else "crossing",
                "center_m": [round(x, 3), round(y, 3), 0.9],
                "tags": tags,
            }
        )

    sign_stack_counts: dict[tuple[int, int], int] = {}
    generated_dcgis_signs = 0
    for sign in sorted(dcgis_traffic_sign_points, key=lambda item: item.object_id):
        key = (round(sign.x * 2.0), round(sign.y * 2.0))
        sign_stack_counts[key] = sign_stack_counts.get(key, 0) + 1
        generated_dcgis_signs += 1
        add_dcgis_traffic_control_sign(
            f"dcgis_traffic_control_sign_{sign.object_id}",
            sign,
            sign_stack_counts[key],
        )

    generated_dcgis_overhead_signs = 0
    for sign in sorted(dcgis_overhead_signs, key=lambda item: item.object_id):
        generated_dcgis_overhead_signs += 1
        add_dcgis_overhead_traffic_sign(f"dcgis_overhead_traffic_sign_{sign.object_id}", sign)

    metadata["traffic_sign_model"]["generated_public_traffic_sign_props"] = generated_dcgis_signs
    metadata["traffic_sign_model"]["generated_public_overhead_sign_props"] = generated_dcgis_overhead_signs

    hydrant_stack_counts: dict[tuple[int, int], int] = {}
    generated_dcgis_hydrants = 0
    for fixture in sorted(dcgis_fire_hydrants, key=lambda item: item.object_id):
        key = (round(fixture.x * 4.0), round(fixture.y * 4.0))
        hydrant_stack_counts[key] = hydrant_stack_counts.get(key, 0) + 1
        stack_index = hydrant_stack_counts[key]
        if stack_index > 1:
            angle = stack_index * math.tau / 5.0
            fixture = DcgisFixturePoint(
                x=fixture.x + math.cos(angle) * 0.22,
                y=fixture.y + math.sin(angle) * 0.22,
                object_id=fixture.object_id,
                feature_id=fixture.feature_id,
                feature_code=fixture.feature_code,
                angle_degrees=fixture.angle_degrees,
                description=fixture.description,
                dxf_layer=fixture.dxf_layer,
                source_layer=fixture.source_layer,
                source_label=fixture.source_label,
            )
        generated_dcgis_hydrants += 1
        add_dcgis_fire_hydrant(f"dcgis_fire_hydrant_{fixture.object_id}", fixture)

    selected_trees = select_spaced_dcgis_points(dcgis_street_trees, 480, 11.5)
    for fixture in selected_trees:
        add_dcgis_street_tree(f"dcgis_street_tree_{fixture.object_id}", fixture)

    selected_misc = select_spaced_dcgis_points(dcgis_miscellaneous_points, 240, 8.5)
    for fixture in selected_misc:
        add_dcgis_misc_public_fixture(f"dcgis_misc_public_fixture_{fixture.object_id}", fixture)

    selected_utility_poles = select_spaced_dcgis_points(dcgis_utility_poles, 220, 10.0)
    for fixture in selected_utility_poles:
        add_dcgis_utility_pole(f"dcgis_utility_pole_{fixture.object_id}", fixture)

    metadata["public_fixture_model"]["generated_fire_hydrant_props"] = generated_dcgis_hydrants
    metadata["public_fixture_model"]["generated_misc_fixture_props"] = len(selected_misc)
    metadata["public_fixture_model"]["generated_street_tree_props"] = len(selected_trees)
    metadata["public_fixture_model"]["generated_utility_pole_props"] = len(selected_utility_poles)

    generated_curb_line_props = 0
    for feature in sorted(dcgis_curb_lines, key=lambda item: item.object_id):
        add_dcgis_curb_line(f"dcgis_curb_line_{feature.object_id}", feature)
        generated_curb_line_props += 1

    generated_sidewalk_edge_props = 0
    for feature in sorted(dcgis_sidewalk_polygons, key=lambda item: item.object_id):
        generated_sidewalk_edge_props += add_dcgis_polygon_edges(
            f"dcgis_sidewalk_polygon_{feature.object_id}",
            feature,
            "dcgis_sidewalk_edge",
            "SidewalkConcrete",
            0.16,
            0.212,
        )
        center = polygon_feature_center(feature)
        metadata["sidewalks"].append(
            {
                "id": feature.object_id,
                "name": f"dcgis_sidewalk_polygon_{feature.object_id}",
                "side": "dcgis_planimetric_polygon",
                "width_m": None,
                "source_tag": "DCGIS Planimetrics 1999 Sidewalks",
                "center_m": [round(center[0], 3), round(center[1], 3), 0.22],
                "dcgis_feature_id": feature.feature_id,
                "area_m2": round(polygon_area_m2(list(feature.rings[0])), 3),
            }
        )

    selected_sidewalk_patches = select_polygon_features(dcgis_sidewalk_polygons, 220, 8.0)
    for feature in selected_sidewalk_patches:
        add_dcgis_surface_patch(
            f"dcgis_sidewalk_surface_patch_{feature.object_id}",
            feature,
            "dcgis_sidewalk_surface_patch",
            "SidewalkConcrete",
            0.186,
            (7.5, 7.5),
        )

    selected_road_edges = select_polygon_features(dcgis_road_polygons, 220, 18.0)
    generated_road_edge_props = 0
    for feature in selected_road_edges:
        generated_road_edge_props += add_dcgis_polygon_edges(
            f"dcgis_road_polygon_{feature.object_id}",
            feature,
            "dcgis_road_edge",
            "RoadPatchAsphalt",
            0.14,
            0.203,
        )

    selected_road_patches = select_polygon_features(dcgis_road_polygons, 140, 30.0)
    for feature in selected_road_patches:
        add_dcgis_surface_patch(
            f"dcgis_road_surface_patch_{feature.object_id}",
            feature,
            "dcgis_road_surface_patch",
            "RoadPatchAsphalt",
            0.176,
            (10.0, 10.0),
        )

    metadata["ground_surface_model"]["generated_curb_line_props"] = generated_curb_line_props
    metadata["ground_surface_model"]["generated_sidewalk_edge_props"] = generated_sidewalk_edge_props
    metadata["ground_surface_model"]["generated_sidewalk_surface_patches"] = len(selected_sidewalk_patches)
    metadata["ground_surface_model"]["generated_road_edge_props"] = generated_road_edge_props
    metadata["ground_surface_model"]["generated_road_surface_patches"] = len(selected_road_patches)

    add_public_roadway_visual_details()
    add_capitol_grounds_details()
    metadata["height_model"]["dcgis_matched_buildings"] = dcgis_height_match_count
    height_source_counts: dict[str, int] = {}
    height_accuracy_tiers: dict[str, int] = {}
    for building in metadata["buildings"]:
        height_source = building.get("height_source", "missing")
        height_source_counts[height_source] = height_source_counts.get(height_source, 0) + 1
        tier = building.get("height_accuracy_tier", "missing")
        height_accuracy_tiers[tier] = height_accuracy_tiers.get(tier, 0) + 1
    metadata["height_model"]["height_source_counts"] = dict(sorted(height_source_counts.items()))
    metadata["height_model"]["height_accuracy_tiers"] = dict(sorted(height_accuracy_tiers.items()))
    metadata["height_model"]["source_backed_buildings"] = (
        height_source_counts.get("explicit_height_tag", 0)
        + height_source_counts.get("dcgis_rooftop_ground_delta_estimate", 0)
    )
    metadata["height_model"]["level_count_estimated_buildings"] = height_source_counts.get("building_levels_estimate", 0)
    metadata["height_model"]["heuristic_estimated_buildings"] = height_source_counts.get("footprint_type_area_estimate", 0)
    review_candidates = [
        building
        for building in metadata["buildings"]
        if building.get("height_review_priority", 0) >= 4
        and building.get("height_source") in {"footprint_type_area_estimate", "building_levels_estimate"}
    ]
    review_candidates.sort(
        key=lambda building: (
            building.get("height_review_priority", 0),
            building.get("footprint_area_m2", 0.0),
            building.get("footprint_span_m", 0.0),
            building.get("height_m", 0.0),
        ),
        reverse=True,
    )
    metadata["height_model"]["height_review_targets"] = [
        {
            "id": building.get("id"),
            "name": building.get("name"),
            "height_m": building.get("height_m"),
            "height_source": building.get("height_source"),
            "height_accuracy_tier": building.get("height_accuracy_tier"),
            "height_confidence": building.get("height_confidence"),
            "height_review_priority": building.get("height_review_priority"),
            "height_review_reasons": building.get("height_review_reasons", []),
            "footprint_area_m2": building.get("footprint_area_m2"),
            "footprint_span_m": building.get("footprint_span_m"),
            "center_m": building.get("center_m"),
        }
        for building in review_candidates[:40]
    ]

    buildings.write(MESH_DIR / "capitol_exterior_buildings.obj", "capitol_materials.mtl")
    roads.write(MESH_DIR / "capitol_exterior_roads_bike_lanes_markers.obj", "capitol_materials.mtl")
    return metadata


def build_capitol_landmark_details() -> dict[str, Any]:
    obj = ObjWriter("capitol_landmark_visual_details")
    labels: list[dict[str, Any]] = []
    elements: list[dict[str, Any]] = []
    facade_details: list[dict[str, Any]] = []
    capitol_public_height_m = 87.48
    statue_of_freedom_height_m = 5.94
    dome_remap_base_z = 17.90
    dome_stack_source_top_z = 66.10
    statue_base_z = capitol_public_height_m - statue_of_freedom_height_m
    dome_z_scale = (statue_base_z - dome_remap_base_z) / (dome_stack_source_top_z - dome_remap_base_z)

    def dome_z(source_z: float) -> float:
        return dome_remap_base_z + (source_z - dome_remap_base_z) * dome_z_scale

    def dome_height(source_height: float) -> float:
        return source_height * dome_z_scale

    def add_dome_cylinder(
        center: tuple[float, float],
        radius: float,
        z: float,
        height: float,
        name: str,
        material: str,
        segments: int = 64,
    ) -> None:
        obj.add_cylinder(center, radius, dome_z(z), dome_height(height), name, material, segments=segments)

    def add_dome_ring(
        center: tuple[float, float],
        outer_radius: float,
        inner_radius: float,
        z: float,
        height: float,
        name: str,
        material: str,
        segments: int = 72,
    ) -> None:
        obj.add_ring(center, outer_radius, inner_radius, dome_z(z), dome_height(height), name, material, segments=segments)

    def add_dome_shell(
        center: tuple[float, float],
        radius: float,
        z: float,
        height: float,
        name: str,
        material: str,
        segments: int = 72,
        rings: int = 10,
    ) -> None:
        obj.add_dome(center, radius, dome_z(z), dome_height(height), name, material, segments=segments, rings=rings)

    def add_element(name: str, category: str, center: tuple[float, float, float]) -> None:
        elements.append(
            {
                "name": name,
                "category": category,
                "center_m": [round(center[0], 3), round(center[1], 3), round(center[2], 3)],
                "public_accuracy": "approximate_visual_massing",
            }
        )
        add_label(labels, name, center[0], center[1], center[2] + 2.0, category)

    def add_facade_detail(name: str, kind: str, center: tuple[float, float, float], extra: dict[str, Any] | None = None) -> None:
        record: dict[str, Any] = {
            "name": name,
            "kind": kind,
            "center_m": [round(center[0], 3), round(center[1], 3), round(center[2], 3)],
            "public_accuracy": "approximate_public_visual_detail",
        }
        if extra:
            record.update(extra)
        facade_details.append(record)

    def add_window_surround(
        name: str,
        center: tuple[float, float],
        z: float,
        orientation: str,
        width: float,
        height: float,
    ) -> None:
        x, y = center
        trim = 0.14
        depth = 0.20
        if orientation == "east_west":
            face_x = x + (0.08 if x >= 0.0 else -0.08)
            obj.add_box((face_x, y - width / 2.0 - trim / 2.0), (depth, trim), height + 0.42, z - 0.2, f"{name}_left_stone_jamb", "ColumnStone")
            obj.add_box((face_x, y + width / 2.0 + trim / 2.0), (depth, trim), height + 0.42, z - 0.2, f"{name}_right_stone_jamb", "ColumnStone")
            obj.add_box((face_x, y), (depth, width + 0.46), 0.18, z + height + 0.10, f"{name}_stone_lintel", "ColumnStone")
            obj.add_box((face_x, y), (depth, width + 0.38), 0.14, z - 0.30, f"{name}_projecting_sill", "ColumnStone")
        else:
            face_y = y + (0.08 if y >= 0.0 else -0.08)
            obj.add_box((x - width / 2.0 - trim / 2.0, face_y), (trim, depth), height + 0.42, z - 0.2, f"{name}_left_stone_jamb", "ColumnStone")
            obj.add_box((x + width / 2.0 + trim / 2.0, face_y), (trim, depth), height + 0.42, z - 0.2, f"{name}_right_stone_jamb", "ColumnStone")
            obj.add_box((x, face_y), (width + 0.46, depth), 0.18, z + height + 0.10, f"{name}_stone_lintel", "ColumnStone")
            obj.add_box((x, face_y), (width + 0.38, depth), 0.14, z - 0.30, f"{name}_projecting_sill", "ColumnStone")
        add_facade_detail(
            f"{name}_stone_surround",
            "facade_window_surround",
            (x, y, z + height / 2.0),
            {"orientation": orientation},
        )

    def add_window_panel(name: str, center: tuple[float, float], z: float, orientation: str) -> None:
        x, y = center
        if orientation == "east_west":
            obj.add_box((x, y), (0.12, 1.34), 1.28, z, name, "FacadeWindow")
        else:
            obj.add_box((x, y), (1.34, 0.12), 1.28, z, name, "FacadeWindow")
        add_facade_detail(name, "facade_window", (x, y, z + 0.64), {"orientation": orientation})
        add_window_mullions(f"{name}_mullions", center, z, orientation, 1.34, 1.28)
        add_window_surround(name, center, z, orientation, 1.34, 1.28)
        add_window_depth_details(name, center, z, orientation, 1.34, 1.28)

    def add_window_mullions(
        name: str,
        center: tuple[float, float],
        z: float,
        orientation: str,
        width: float,
        height: float,
    ) -> None:
        x, y = center
        if orientation == "east_west":
            face_x = x + (0.16 if x >= 0.0 else -0.16)
            obj.add_box((face_x, y), (0.12, 0.055), height, z, f"{name}_vertical_bar", "DoorMetal")
            obj.add_box((face_x, y), (0.12, width), 0.06, z + height * 0.52, f"{name}_horizontal_bar", "DoorMetal")
        else:
            face_y = y + (0.16 if y >= 0.0 else -0.16)
            obj.add_box((x, face_y), (0.055, 0.12), height, z, f"{name}_vertical_bar", "DoorMetal")
            obj.add_box((x, face_y), (width, 0.12), 0.06, z + height * 0.52, f"{name}_horizontal_bar", "DoorMetal")
        add_facade_detail(
            name,
            "facade_window_mullion",
            (x, y, z + height / 2.0),
            {"orientation": orientation},
        )

    def add_window_depth_details(
        name: str,
        center: tuple[float, float],
        z: float,
        orientation: str,
        width: float,
        height: float,
    ) -> None:
        x, y = center
        if orientation == "east_west":
            face_x = x + (0.22 if x >= 0.0 else -0.22)
            shadow_size_major = (0.065, width + 0.18)
            shadow_size_minor = (0.065, 0.08)
            sash_size_major = (0.075, width * 0.86)
            sash_size_minor = (0.075, 0.055)
            highlight_size = (0.055, width * 0.18)
            shadow_centers = [
                ((face_x, y - width / 2.0 - 0.045), shadow_size_minor, height + 0.16, z - 0.07),
                ((face_x, y + width / 2.0 + 0.045), shadow_size_minor, height + 0.16, z - 0.07),
                ((face_x, y), shadow_size_major, 0.055, z - 0.08),
                ((face_x, y), shadow_size_major, 0.065, z + height + 0.02),
            ]
            sash_centers = [
                ((face_x, y - width * 0.34), sash_size_minor, height * 0.90, z + height * 0.05),
                ((face_x, y + width * 0.34), sash_size_minor, height * 0.90, z + height * 0.05),
                ((face_x, y), sash_size_major, 0.045, z + height * 0.18),
                ((face_x, y), sash_size_major, 0.045, z + height * 0.82),
            ]
            highlight_centers = [
                ((face_x + (0.015 if x >= 0.0 else -0.015), y - width * 0.22), highlight_size, height * 0.24, z + height * 0.62),
                ((face_x + (0.015 if x >= 0.0 else -0.015), y + width * 0.18), highlight_size, height * 0.16, z + height * 0.72),
            ]
        else:
            face_y = y + (0.22 if y >= 0.0 else -0.22)
            shadow_size_major = (width + 0.18, 0.065)
            shadow_size_minor = (0.08, 0.065)
            sash_size_major = (width * 0.86, 0.075)
            sash_size_minor = (0.055, 0.075)
            highlight_size = (width * 0.18, 0.055)
            shadow_centers = [
                ((x - width / 2.0 - 0.045, face_y), shadow_size_minor, height + 0.16, z - 0.07),
                ((x + width / 2.0 + 0.045, face_y), shadow_size_minor, height + 0.16, z - 0.07),
                ((x, face_y), shadow_size_major, 0.055, z - 0.08),
                ((x, face_y), shadow_size_major, 0.065, z + height + 0.02),
            ]
            sash_centers = [
                ((x - width * 0.34, face_y), sash_size_minor, height * 0.90, z + height * 0.05),
                ((x + width * 0.34, face_y), sash_size_minor, height * 0.90, z + height * 0.05),
                ((x, face_y), sash_size_major, 0.045, z + height * 0.18),
                ((x, face_y), sash_size_major, 0.045, z + height * 0.82),
            ]
            highlight_centers = [
                ((x - width * 0.22, face_y + (0.015 if y >= 0.0 else -0.015)), highlight_size, height * 0.24, z + height * 0.62),
                ((x + width * 0.18, face_y + (0.015 if y >= 0.0 else -0.015)), highlight_size, height * 0.16, z + height * 0.72),
            ]

        for index, (detail_center, detail_size, detail_height, detail_z) in enumerate(shadow_centers, start=1):
            obj.add_box(detail_center, detail_size, detail_height, detail_z, f"{name}_recess_shadow_{index:02d}", "RoadCrackSealant")
        for index, (detail_center, detail_size, detail_height, detail_z) in enumerate(sash_centers, start=1):
            obj.add_box(detail_center, detail_size, detail_height, detail_z, f"{name}_inner_sash_{index:02d}", "DoorMetal")
        for index, (detail_center, detail_size, detail_height, detail_z) in enumerate(highlight_centers, start=1):
            obj.add_box(detail_center, detail_size, detail_height, detail_z, f"{name}_pane_highlight_{index:02d}", "DoorGlass")

        add_facade_detail(
            f"{name}_recess_shadow",
            "facade_window_recess_shadow",
            (x, y, z + height / 2.0),
            {"orientation": orientation, "count": len(shadow_centers)},
        )
        add_facade_detail(
            f"{name}_inner_sash",
            "facade_window_inner_sash",
            (x, y, z + height / 2.0),
            {"orientation": orientation, "count": len(sash_centers)},
        )
        add_facade_detail(
            f"{name}_pane_highlight",
            "facade_window_pane_highlight",
            (x, y, z + height * 0.74),
            {"orientation": orientation, "count": len(highlight_centers)},
        )

    def add_arch_window_trim(
        name: str,
        center: tuple[float, float],
        z: float,
        orientation: str,
        width: float,
        height: float,
    ) -> None:
        x, y = center
        arch_height = width * 0.32
        fractions = [-0.86, -0.58, -0.30, 0.0, 0.30, 0.58, 0.86]
        for stone_index, fraction in enumerate(fractions, start=1):
            lateral_offset = fraction * width / 2.0
            lift = arch_height * math.sqrt(max(0.0, 1.0 - fraction * fraction))
            stone_z = z + height + lift - 0.08
            stone_height = 0.18 if abs(fraction) > 0.65 else 0.22
            if orientation == "east_west":
                face_x = x + (0.36 if x >= 0.0 else -0.36)
                stone_center = (face_x, y + lateral_offset)
                stone_size = (0.20, max(0.20, width * 0.13))
            else:
                face_y = y + (0.36 if y >= 0.0 else -0.36)
                stone_center = (x + lateral_offset, face_y)
                stone_size = (max(0.20, width * 0.13), 0.20)
            obj.add_box(stone_center, stone_size, stone_height, stone_z, f"{name}_arch_voussoir_{stone_index:02d}", "ColumnStone")

        if orientation == "east_west":
            face_x = x + (0.43 if x >= 0.0 else -0.43)
            keystone_center = (face_x, y)
            keystone_size = (0.24, 0.28)
        else:
            face_y = y + (0.43 if y >= 0.0 else -0.43)
            keystone_center = (x, face_y)
            keystone_size = (0.28, 0.24)
        obj.add_box(keystone_center, keystone_size, 0.44, z + height + arch_height * 0.78, f"{name}_center_keystone", "ColumnStone")
        add_facade_detail(
            name,
            "facade_arch_window_trim",
            (x, y, z + height + arch_height / 2.0),
            {"orientation": orientation, "voussoir_count": len(fractions)},
        )
        add_facade_detail(
            f"{name}_center_keystone",
            "facade_window_keystone",
            (x, y, z + height + arch_height),
            {"orientation": orientation},
        )

    def add_arch_window_trim_grid(
        prefix: str,
        orientation: str,
        fixed: float,
        span_values: list[float],
        z_levels: list[float],
        width: float,
        height: float,
    ) -> None:
        for level_index, z_level in enumerate(z_levels, start=1):
            for span_index, value in enumerate(span_values, start=1):
                center = (fixed, value) if orientation == "east_west" else (value, fixed)
                add_arch_window_trim(f"{prefix}_arch_l{level_index:02d}_{span_index:02d}", center, z_level, orientation, width, height)

    def add_facade_window_grid(
        prefix: str,
        orientation: str,
        fixed: float,
        span_values: list[float],
        z_levels: list[float],
    ) -> None:
        for level_index, z in enumerate(z_levels, start=1):
            for span_index, value in enumerate(span_values, start=1):
                if orientation == "east_west":
                    center = (fixed, value)
                else:
                    center = (value, fixed)
                add_window_panel(f"{prefix}_window_l{level_index:02d}_{span_index:02d}", center, z, orientation)

    def add_plaza_bollard(name: str, center: tuple[float, float]) -> None:
        x, y = center
        obj.add_cylinder((x, y), 0.16, 0.08, 0.84, f"{name}_post", "BollardMetal", segments=12)
        obj.add_cylinder((x, y), 0.18, 0.92, 0.12, f"{name}_cap", "BollardMetal", segments=12)
        add_facade_detail(name, "plaza_bollard", (x, y, 0.55))

    def add_bench(name: str, center: tuple[float, float]) -> None:
        x, y = center
        obj.add_box((x, y), (2.2, 0.45), 0.16, 0.52, f"{name}_seat", "BenchWood")
        obj.add_box((x, y + 0.22), (2.2, 0.12), 0.72, 0.58, f"{name}_back", "BenchWood")
        for leg_index, lx in enumerate([-0.82, 0.82], start=1):
            obj.add_box((x + lx, y), (0.12, 0.34), 0.48, 0.08, f"{name}_leg_{leg_index}", "BollardMetal")
        add_facade_detail(name, "public_bench", (x, y, 0.75))

    def add_public_entry_lamp(name: str, center: tuple[float, float]) -> None:
        x, y = center
        obj.add_cylinder((x, y), 0.08, 0.12, 3.4, f"{name}_pole", "StreetLightPole", segments=10)
        obj.add_cylinder((x, y), 0.24, 3.34, 0.42, f"{name}_lantern_glass", "StreetLightGlass", segments=12)
        add_facade_detail(
            name,
            "public_entry_lamp",
            (x, y, 2.0),
            {"light_m": [round(x, 3), round(y, 3), 3.55], "intensity": 520.0, "attenuation_radius_m": 8.0},
        )

    def add_public_facade_sconce(name: str, center: tuple[float, float], facade: str) -> None:
        x, y = center
        if facade in {"east", "west"}:
            face_x = x + (0.48 if x >= 0.0 else -0.48)
            obj.add_box((face_x, y), (0.18, 0.22), 0.34, 2.22, f"{name}_wall_plate", "LightFixtureMetal")
            obj.add_box((face_x, y), (0.34, 0.13), 0.10, 2.52, f"{name}_bracket_arm", "LightFixtureMetal")
            obj.add_cylinder((face_x, y), 0.16, 2.58, 0.34, f"{name}_warm_glass_bowl", "WarmLightGlass", segments=12)
            light_location = (face_x, y, 2.92)
        else:
            face_y = y + (0.48 if y >= 0.0 else -0.48)
            obj.add_box((x, face_y), (0.22, 0.18), 0.34, 2.22, f"{name}_wall_plate", "LightFixtureMetal")
            obj.add_box((x, face_y), (0.13, 0.34), 0.10, 2.52, f"{name}_bracket_arm", "LightFixtureMetal")
            obj.add_cylinder((x, face_y), 0.16, 2.58, 0.34, f"{name}_warm_glass_bowl", "WarmLightGlass", segments=12)
            light_location = (x, face_y, 2.92)
        add_facade_detail(
            name,
            "public_facade_sconce",
            (light_location[0], light_location[1], 2.56),
            {
                "facade": facade,
                "light_m": [round(light_location[0], 3), round(light_location[1], 3), round(light_location[2], 3)],
                "intensity": 260.0,
                "attenuation_radius_m": 5.5,
                "color": [1.0, 0.78, 0.48],
            },
        )

    def add_facade_uplight(name: str, center: tuple[float, float], aimed_at: tuple[float, float, float]) -> None:
        x, y = center
        obj.add_cylinder((x, y), 0.18, 0.12, 0.08, f"{name}_round_base", "LightFixtureMetal", segments=14)
        obj.add_cylinder((x, y), 0.12, 0.20, 0.16, f"{name}_warm_lens", "WarmLightGlass", segments=14)
        obj.add_box((x, y), (0.34, 0.12), 0.08, 0.26, f"{name}_metal_yoke", "LightFixtureMetal")
        add_facade_detail(
            name,
            "facade_uplight",
            (x, y, 0.34),
            {
                "light_m": [round(x, 3), round(y, 3), 0.82],
                "aimed_at_m": [round(aimed_at[0], 3), round(aimed_at[1], 3), round(aimed_at[2], 3)],
                "intensity": 430.0,
                "attenuation_radius_m": 8.5,
                "color": [1.0, 0.80, 0.55],
            },
        )

    def add_roof_slope_skirt_panels(name: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        cx, cy = center
        sx, sy = size
        inset = max(0.85, min(2.35, min(sx, sy) * 0.075))
        outer_z = z + 0.73
        inner_z = z + 1.02
        panel_specs = [
            (
                "north",
                [
                    (cx - sx / 2.0, cy + sy / 2.0, outer_z),
                    (cx + sx / 2.0, cy + sy / 2.0, outer_z),
                    (cx + sx / 2.0 - inset, cy + sy / 2.0 - inset, inner_z),
                    (cx - sx / 2.0 + inset, cy + sy / 2.0 - inset, inner_z),
                ],
            ),
            (
                "south",
                [
                    (cx + sx / 2.0, cy - sy / 2.0, outer_z),
                    (cx - sx / 2.0, cy - sy / 2.0, outer_z),
                    (cx - sx / 2.0 + inset, cy - sy / 2.0 + inset, inner_z),
                    (cx + sx / 2.0 - inset, cy - sy / 2.0 + inset, inner_z),
                ],
            ),
            (
                "east",
                [
                    (cx + sx / 2.0, cy + sy / 2.0, outer_z),
                    (cx + sx / 2.0, cy - sy / 2.0, outer_z),
                    (cx + sx / 2.0 - inset, cy - sy / 2.0 + inset, inner_z),
                    (cx + sx / 2.0 - inset, cy + sy / 2.0 - inset, inner_z),
                ],
            ),
            (
                "west",
                [
                    (cx - sx / 2.0, cy - sy / 2.0, outer_z),
                    (cx - sx / 2.0, cy + sy / 2.0, outer_z),
                    (cx - sx / 2.0 + inset, cy + sy / 2.0 - inset, inner_z),
                    (cx - sx / 2.0 + inset, cy - sy / 2.0 + inset, inner_z),
                ],
            ),
        ]
        for edge, points in panel_specs:
            group_name = f"{name}_{edge}_sloped_roof_skirt_panel"
            obj.add_group(group_name, "CapitolDome")
            vertices = [obj.add_vertex(x, y, point_z) for x, y, point_z in points]
            obj.add_face(vertices)
            obj.add_face(list(reversed(vertices)))
            center_x = sum(point[0] for point in points) / len(points)
            center_y = sum(point[1] for point in points) / len(points)
            center_z = sum(point[2] for point in points) / len(points)
            add_facade_detail(
                group_name,
                "roof_slope_skirt_panel",
                (center_x, center_y, center_z),
                {"edge": edge, "inset_m": round(inset, 3), "public_accuracy": "schematic_public_roof_silhouette"},
            )

    def add_parapet_corner_piers(name: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        cx, cy = center
        sx, sy = size
        pier_size = (0.84, 0.84)
        for corner, x_sign, y_sign in [
            ("northeast", 1.0, 1.0),
            ("northwest", -1.0, 1.0),
            ("southeast", 1.0, -1.0),
            ("southwest", -1.0, -1.0),
        ]:
            pier_center = (cx + x_sign * (sx / 2.0 - 0.62), cy + y_sign * (sy / 2.0 - 0.62))
            pier_name = f"{name}_{corner}_parapet_corner_pier"
            obj.add_box(pier_center, pier_size, 0.54, z + 0.50, pier_name, "ColumnStone")
            add_facade_detail(
                pier_name,
                "parapet_corner_pier",
                (pier_center[0], pier_center[1], z + 0.77),
                {"corner": corner, "public_accuracy": "schematic_public_roof_silhouette"},
            )

    def add_roof_cap(name: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        obj.add_box(center, size, 0.48, z, f"{name}_parapet_cap", "ColumnStone")
        obj.add_box(center, (size[0] * 0.92, size[1] * 0.92), 0.22, z + 0.48, f"{name}_slightly_recessed_roof", "CapitolDome")
        add_facade_detail(name, "roof_parapet_and_recessed_roof", (center[0], center[1], z + 0.48))
        add_roof_slope_skirt_panels(name, center, size, z)
        add_parapet_corner_piers(name, center, size, z)

    def add_beveled_massing(
        name: str,
        center: tuple[float, float],
        size: tuple[float, float],
        height: float,
        z: float,
        material: str,
        bevel: float = 0.46,
    ) -> None:
        obj.add_beveled_box(center, size, height, z, name, material, bevel)
        add_facade_detail(
            f"{name}_beveled_public_massing",
            "facade_beveled_massing",
            (center[0], center[1], z + height / 2.0),
            {
                "size_m": [round(size[0], 3), round(size[1], 3)],
                "height_m": round(height, 3),
                "bevel_m": round(bevel, 3),
                "public_accuracy": "schematic_beveled_public_massing",
            },
        )

    def add_roof_articulation_volume(
        name: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
        height: float,
        kind: str = "roof_articulation_volume",
    ) -> None:
        obj.add_box(center, size, height, z, name, "CapitolStone")
        obj.add_box(center, (size[0] * 0.92, size[1] * 0.88), 0.16, z + height, f"{name}_cap", "ColumnStone")
        add_facade_detail(name, kind, (center[0], center[1], z + height / 2.0), {"size_m": [round(size[0], 3), round(size[1], 3)]})

    def add_stepped_pavilion_massing(
        name: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
        height: float,
    ) -> None:
        x, y = center
        sx, sy = size
        add_beveled_massing(f"{name}_primary_step", center, size, height, z, "CapitolStone", bevel=0.28)
        add_beveled_massing(f"{name}_upper_setback", center, (sx * 0.86, sy * 0.86), height * 0.32, z + height, "CapitolStone", bevel=0.22)
        obj.add_box(center, (sx + 0.62, sy + 0.62), 0.18, z + height + height * 0.32, f"{name}_cap_course", "ColumnStone")
        reveal_z = z + height + 0.03
        reveal_specs = [
            ((x, y + sy * 0.43), (sx * 0.86, 0.08), "north"),
            ((x, y - sy * 0.43), (sx * 0.86, 0.08), "south"),
            ((x + sx * 0.43, y), (0.08, sy * 0.86), "east"),
            ((x - sx * 0.43, y), (0.08, sy * 0.86), "west"),
        ]
        for reveal_center, reveal_size, edge in reveal_specs:
            obj.add_box(reveal_center, reveal_size, 0.10, reveal_z, f"{name}_{edge}_upper_setback_shadow_reveal", "DoorMetal")
        add_facade_detail(name, "stepped_pavilion_massing", (x, y, z + height * 0.66), {"size_m": [round(sx, 3), round(sy, 3)]})
        add_facade_detail(
            f"{name}_upper_setback_shadow_reveal",
            "pavilion_setback_reveal",
            (x, y, reveal_z + 0.05),
            {"size_m": [round(sx * 0.86, 3), round(sy * 0.86, 3)], "public_accuracy": "schematic_public_roof_silhouette"},
        )

    def add_facade_shadow_return(
        name: str,
        orientation: str,
        fixed: float,
        span_center: float,
        span_length: float,
        z: float,
        height: float,
    ) -> None:
        if orientation == "east_west":
            center = (fixed, span_center)
            size = (0.16, span_length)
        else:
            center = (span_center, fixed)
            size = (span_length, 0.16)
        obj.add_box(center, size, height, z, name, "DoorMetal")
        add_facade_detail(name, "facade_shadow_return", (center[0], center[1], z + height / 2.0), {"orientation": orientation})

    def add_facade_water_table(
        name: str,
        orientation: str,
        fixed: float,
        span_center: float,
        span_length: float,
        z: float = 1.36,
    ) -> None:
        if orientation == "east_west":
            center = (fixed, span_center)
            size = (0.34, span_length)
        else:
            center = (span_center, fixed)
            size = (span_length, 0.34)
        obj.add_box(center, size, 0.26, z, name, "ColumnStone")
        add_facade_detail(name, "facade_water_table", (center[0], center[1], z + 0.13), {"orientation": orientation})

    def add_cornice_shadow_reveal(
        name: str,
        orientation: str,
        fixed: float,
        span_center: float,
        span_length: float,
        z: float,
    ) -> None:
        face_offset = 0.42 if fixed >= 0.0 else -0.42
        if orientation == "east_west":
            center = (fixed + face_offset, span_center)
            size = (0.075, span_length)
        else:
            center = (span_center, fixed + face_offset)
            size = (span_length, 0.075)
        obj.add_box(center, size, 0.12, z, name, "DoorMetal")
        add_facade_detail(
            name,
            "cornice_shadow_reveal",
            (center[0], center[1], z + 0.06),
            {"orientation": orientation, "length_m": round(span_length, 3), "public_accuracy": "schematic_public_roof_silhouette"},
        )

    def add_attic_window_band(
        prefix: str,
        orientation: str,
        fixed: float,
        values: list[float],
        z: float,
        width: float = 0.78,
        height: float = 0.46,
    ) -> None:
        face_offset = 0.38 if fixed >= 0.0 else -0.38
        for idx, value in enumerate(values, start=1):
            if orientation == "east_west":
                center = (fixed + face_offset, value)
                window_size = (0.075, width)
                sill_center = (fixed + face_offset * 1.04, value)
                sill_size = (0.095, width + 0.28)
            else:
                center = (value, fixed + face_offset)
                window_size = (width, 0.075)
                sill_center = (value, fixed + face_offset * 1.04)
                sill_size = (width + 0.28, 0.095)
            name = f"{prefix}_attic_window_{idx:02d}"
            obj.add_box(center, window_size, height, z, name, "FacadeWindow")
            obj.add_box(sill_center, sill_size, 0.075, z - 0.08, f"{name}_stone_sill", "ColumnStone")
            obj.add_box(sill_center, sill_size, 0.075, z + height + 0.02, f"{name}_stone_lintel", "ColumnStone")
            add_facade_detail(
                name,
                "attic_window_band",
                (center[0], center[1], z + height / 2.0),
                {"orientation": orientation, "sequence": idx, "public_accuracy": "schematic_public_facade_rhythm"},
            )

    def add_roof_monitor_ridge(
        name: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
        orientation: str,
    ) -> None:
        x, y = center
        sx, sy = size
        obj.add_box(center, size, 0.32, z, f"{name}_stone_base", "ColumnStone")
        obj.add_box(center, (sx * 0.78, sy * 0.78), 0.28, z + 0.32, f"{name}_raised_roof", "CapitolDome")
        if orientation == "east_west":
            obj.add_box((x, y - sy * 0.39), (sx * 0.66, 0.10), 0.18, z + 0.44, f"{name}_south_dark_louver", "FacadeWindow")
            obj.add_box((x, y + sy * 0.39), (sx * 0.66, 0.10), 0.18, z + 0.44, f"{name}_north_dark_louver", "FacadeWindow")
        else:
            obj.add_box((x - sx * 0.39, y), (0.10, sy * 0.66), 0.18, z + 0.44, f"{name}_west_dark_louver", "FacadeWindow")
            obj.add_box((x + sx * 0.39, y), (0.10, sy * 0.66), 0.18, z + 0.44, f"{name}_east_dark_louver", "FacadeWindow")
        add_facade_detail(name, "roof_monitor_ridge", (x, y, z + 0.32), {"orientation": orientation, "size_m": [round(sx, 3), round(sy, 3)]})

    def add_courtyard_notch_shadow(name: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        x, y = center
        sx, sy = size
        obj.add_box(center, size, 0.10, z, name, "DoorMetal")
        obj.add_box((x, y + sy / 2.0), (sx + 0.42, 0.18), 0.18, z + 0.08, f"{name}_north_lip", "ColumnStone")
        obj.add_box((x, y - sy / 2.0), (sx + 0.42, 0.18), 0.18, z + 0.08, f"{name}_south_lip", "ColumnStone")
        add_facade_detail(name, "courtyard_notch_shadow", (center[0], center[1], z + 0.05), {"size_m": [round(size[0], 3), round(size[1], 3)]})

    def add_roof_dormer(name: str, center: tuple[float, float], z: float, orientation: str) -> None:
        x, y = center
        if orientation == "east_west":
            obj.add_box((x, y), (0.82, 1.18), 0.82, z, f"{name}_stone_body", "ColumnStone")
            obj.add_box((x + (0.12 if x >= 0.0 else -0.12), y), (0.12, 0.72), 0.46, z + 0.18, f"{name}_dark_window", "FacadeWindow")
            obj.add_pediment((x + (0.08 if x >= 0.0 else -0.08), y), 1.18, 0.74, z + 0.78, 0.34, f"{name}_little_pediment", "ColumnStone", "east_west")
        else:
            obj.add_box((x, y), (1.18, 0.82), 0.82, z, f"{name}_stone_body", "ColumnStone")
            obj.add_box((x, y + (0.12 if y >= 0.0 else -0.12)), (0.72, 0.12), 0.46, z + 0.18, f"{name}_dark_window", "FacadeWindow")
            obj.add_pediment((x, y + (0.08 if y >= 0.0 else -0.08)), 1.18, 0.74, z + 0.78, 0.34, f"{name}_little_pediment", "ColumnStone", "north_south")
        add_facade_detail(name, "roof_dormer", (x, y, z + 0.5), {"orientation": orientation})

    def add_roof_skylight_strip(name: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        x, y = center
        sx, sy = size
        obj.add_box(center, size, 0.08, z, f"{name}_glass", "DoorGlass")
        obj.add_box((x, y + sy / 2.0), (sx + 0.18, 0.10), 0.10, z + 0.04, f"{name}_north_frame", "DoorMetal")
        obj.add_box((x, y - sy / 2.0), (sx + 0.18, 0.10), 0.10, z + 0.04, f"{name}_south_frame", "DoorMetal")
        add_facade_detail(name, "roof_skylight_strip", (center[0], center[1], z + 0.04), {"size_m": [round(size[0], 3), round(size[1], 3)]})

    def add_facade_ashlar_courses(
        prefix: str,
        orientation: str,
        fixed: float,
        span_center: float,
        span_length: float,
        z_levels: list[float],
    ) -> None:
        face_offset = 0.24 if fixed >= 0.0 else -0.24
        for idx, z_level in enumerate(z_levels, start=1):
            if orientation == "east_west":
                center = (fixed + face_offset, span_center)
                size = (0.075, span_length)
            else:
                center = (span_center, fixed + face_offset)
                size = (span_length, 0.075)
            name = f"{prefix}_ashlar_course_{idx:02d}"
            obj.add_box(center, size, 0.055, z_level, name, "ColumnStone")
            add_facade_detail(
                name,
                "facade_ashlar_course",
                (center[0], center[1], z_level + 0.028),
                {"orientation": orientation, "length_m": round(span_length, 3)},
            )

    def add_facade_vertical_stone_joints(
        prefix: str,
        orientation: str,
        fixed: float,
        positions: list[float],
        z_base: float,
        height: float,
    ) -> None:
        face_offset = 0.25 if fixed >= 0.0 else -0.25
        for idx, value in enumerate(positions, start=1):
            if orientation == "east_west":
                center = (fixed + face_offset, value)
                size = (0.080, 0.055)
            else:
                center = (value, fixed + face_offset)
                size = (0.055, 0.080)
            name = f"{prefix}_vertical_stone_joint_{idx:02d}"
            obj.add_box(center, size, height, z_base, name, "ColumnStone")
            add_facade_detail(
                name,
                "facade_vertical_stone_joint",
                (center[0], center[1], z_base + height / 2.0),
                {"orientation": orientation, "height_m": round(height, 3)},
            )

    def add_roof_surface_joint_grid(
        prefix: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
        x_lines: int,
        y_lines: int,
    ) -> None:
        cx, cy = center
        sx, sy = size
        for idx in range(1, x_lines + 1):
            x = cx - sx / 2.0 + sx * idx / (x_lines + 1)
            name = f"{prefix}_roof_joint_x_{idx:02d}"
            obj.add_box((x, cy), (0.08, sy * 0.84), 0.035, z, name, "StepStone")
            add_facade_detail(name, "roof_surface_joint", (x, cy, z + 0.018), {"axis": "x", "length_m": round(sy * 0.84, 3)})
        for idx in range(1, y_lines + 1):
            y = cy - sy / 2.0 + sy * idx / (y_lines + 1)
            name = f"{prefix}_roof_joint_y_{idx:02d}"
            obj.add_box((cx, y), (sx * 0.84, 0.08), 0.035, z, name, "StepStone")
            add_facade_detail(name, "roof_surface_joint", (cx, y, z + 0.018), {"axis": "y", "length_m": round(sx * 0.84, 3)})

    def add_roof_edge_realism_details(
        prefix: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
        x_blocks: int,
        y_blocks: int,
    ) -> None:
        cx, cy = center
        sx, sy = size

        def capstone(name: str, block_center: tuple[float, float], block_size: tuple[float, float], edge: str) -> None:
            obj.add_box(block_center, block_size, 0.13, z, name, "ColumnStone")
            add_facade_detail(
                name,
                "roof_capstone_block",
                (block_center[0], block_center[1], z + 0.065),
                {"edge": edge, "size_m": [round(block_size[0], 3), round(block_size[1], 3)]},
            )

        for index in range(x_blocks):
            x = cx - sx / 2.0 + sx * (index + 0.5) / x_blocks
            block_width = sx / x_blocks * 0.72
            capstone(f"{prefix}_north_capstone_block_{index+1:02d}", (x, cy + sy / 2.0 + 0.08), (block_width, 0.30), "north")
            capstone(f"{prefix}_south_capstone_block_{index+1:02d}", (x, cy - sy / 2.0 - 0.08), (block_width, 0.30), "south")
        for index in range(y_blocks):
            y = cy - sy / 2.0 + sy * (index + 0.5) / y_blocks
            block_depth = sy / y_blocks * 0.72
            capstone(f"{prefix}_east_capstone_block_{index+1:02d}", (cx + sx / 2.0 + 0.08, y), (0.30, block_depth), "east")
            capstone(f"{prefix}_west_capstone_block_{index+1:02d}", (cx - sx / 2.0 - 0.08, y), (0.30, block_depth), "west")

        shadow_specs = [
            ("north", (cx, cy + sy / 2.0 - 0.18), (sx * 0.92, 0.08)),
            ("south", (cx, cy - sy / 2.0 + 0.18), (sx * 0.92, 0.08)),
            ("east", (cx + sx / 2.0 - 0.18, cy), (0.08, sy * 0.92)),
            ("west", (cx - sx / 2.0 + 0.18, cy), (0.08, sy * 0.92)),
        ]
        for edge, shadow_center, shadow_size in shadow_specs:
            name = f"{prefix}_{edge}_parapet_shadow_gap"
            obj.add_box(shadow_center, shadow_size, 0.035, z + 0.012, name, "DoorMetal")
            add_facade_detail(
                name,
                "roof_parapet_shadow_gap",
                (shadow_center[0], shadow_center[1], z + 0.030),
                {"edge": edge, "length_m": round(max(shadow_size), 3)},
            )

        scupper_specs = [
            ("north", (cx - sx * 0.30, cy + sy / 2.0 + 0.12), (0.48, 0.12)),
            ("north", (cx + sx * 0.30, cy + sy / 2.0 + 0.12), (0.48, 0.12)),
            ("south", (cx - sx * 0.30, cy - sy / 2.0 - 0.12), (0.48, 0.12)),
            ("south", (cx + sx * 0.30, cy - sy / 2.0 - 0.12), (0.48, 0.12)),
            ("east", (cx + sx / 2.0 + 0.12, cy - sy * 0.30), (0.12, 0.48)),
            ("east", (cx + sx / 2.0 + 0.12, cy + sy * 0.30), (0.12, 0.48)),
            ("west", (cx - sx / 2.0 - 0.12, cy - sy * 0.30), (0.12, 0.48)),
            ("west", (cx - sx / 2.0 - 0.12, cy + sy * 0.30), (0.12, 0.48)),
        ]
        for index, (edge, scupper_center, scupper_size) in enumerate(scupper_specs, start=1):
            name = f"{prefix}_{edge}_roof_scupper_{index:02d}"
            obj.add_box(scupper_center, scupper_size, 0.08, z + 0.02, name, "DoorMetal")
            add_facade_detail(
                name,
                "roof_drain_scupper",
                (scupper_center[0], scupper_center[1], z + 0.06),
                {"edge": edge, "public_accuracy": "generic_non_operational_roof_detail"},
            )

    def add_generic_roof_vent_housing(
        name: str,
        center: tuple[float, float],
        z: float,
        size: tuple[float, float] = (1.25, 0.92),
    ) -> None:
        x, y = center
        obj.add_box((x, y), size, 0.42, z, f"{name}_low_stone_curb", "StepStone")
        obj.add_box((x, y), (size[0] * 0.72, size[1] * 0.62), 0.34, z + 0.42, f"{name}_metal_louvered_housing", "LightFixtureMetal")
        obj.add_box((x, y), (size[0] * 0.82, 0.08), 0.06, z + 0.62, f"{name}_louver_slats_a", "DoorMetal")
        obj.add_box((x, y), (size[0] * 0.82, 0.08), 0.06, z + 0.76, f"{name}_louver_slats_b", "DoorMetal")
        obj.add_cylinder((x + size[0] * 0.18, y - size[1] * 0.16), 0.11, z + 0.78, 0.44, f"{name}_short_vent_pipe", "LightFixtureMetal", segments=10)
        add_facade_detail(
            name,
            "generic_roof_vent_housing",
            (x, y, z + 0.55),
            {"size_m": [round(size[0], 3), round(size[1], 3)], "public_accuracy": "generic_non_operational_roof_detail"},
        )

    def add_facade_weathering_stains(
        prefix: str,
        orientation: str,
        fixed: float,
        positions: list[float],
        z_levels: list[float],
        base_height: float,
        base_width: float,
    ) -> None:
        face_offset = 0.32 if fixed >= 0.0 else -0.32
        for level_index, z_level in enumerate(z_levels, start=1):
            for idx, value in enumerate(positions, start=1):
                height = base_height * (0.78 + ((idx + level_index) % 3) * 0.16)
                width = base_width * (0.86 + ((idx + level_index) % 2) * 0.22)
                if orientation == "east_west":
                    center = (fixed + face_offset, value)
                    size = (0.045, width)
                else:
                    center = (value, fixed + face_offset)
                    size = (width, 0.045)
                name = f"{prefix}_weathering_stain_l{level_index:02d}_{idx:02d}"
                obj.add_box(center, size, height, z_level, name, "BuildingGeneric")
                add_facade_detail(
                    name,
                    "facade_weathering_stain",
                    (center[0], center[1], z_level + height / 2.0),
                    {"orientation": orientation, "height_m": round(height, 3), "width_m": round(width, 3)},
                )

    def add_facade_discoloration_patches(
        prefix: str,
        orientation: str,
        fixed: float,
        positions: list[float],
        z_levels: list[float],
        base_height: float,
        base_width: float,
    ) -> None:
        face_offset = 0.46 if fixed >= 0.0 else -0.46
        for level_index, z_level in enumerate(z_levels, start=1):
            for idx, value in enumerate(positions, start=1):
                width = base_width * (0.82 + ((idx + level_index) % 4) * 0.10)
                height = base_height * (0.72 + ((idx * 2 + level_index) % 5) * 0.09)
                if orientation == "east_west":
                    center = (fixed + face_offset, value)
                    size = (0.035, width)
                else:
                    center = (value, fixed + face_offset)
                    size = (width, 0.035)
                name = f"{prefix}_limestone_discoloration_patch_l{level_index:02d}_{idx:02d}"
                obj.add_box(center, size, height, z_level, name, "StoneGrimeOverlay")
                add_facade_detail(
                    name,
                    "facade_limestone_discoloration_patch",
                    (center[0], center[1], z_level + height / 2.0),
                    {"orientation": orientation, "height_m": round(height, 3), "width_m": round(width, 3)},
                )

    def add_facade_sill_runoff_stains(
        prefix: str,
        orientation: str,
        fixed: float,
        positions: list[float],
        z_levels: list[float],
    ) -> None:
        face_offset = 0.52 if fixed >= 0.0 else -0.52
        for level_index, z_level in enumerate(z_levels, start=1):
            for idx, value in enumerate(positions, start=1):
                height = 0.92 + ((idx + level_index) % 4) * 0.17
                width = 0.18 + (idx % 3) * 0.045
                if orientation == "east_west":
                    center = (fixed + face_offset, value - 0.26 + (idx % 2) * 0.52)
                    size = (0.030, width)
                else:
                    center = (value - 0.26 + (idx % 2) * 0.52, fixed + face_offset)
                    size = (width, 0.030)
                stain_z = z_level - height * 0.72
                name = f"{prefix}_sill_runoff_stain_l{level_index:02d}_{idx:02d}"
                obj.add_box(center, size, height, stain_z, name, "StoneGrimeOverlay")
                add_facade_detail(
                    name,
                    "facade_sill_runoff_stain",
                    (center[0], center[1], stain_z + height / 2.0),
                    {"orientation": orientation, "height_m": round(height, 3), "width_m": round(width, 3)},
                )

    def add_facade_base_grime_band(
        name: str,
        orientation: str,
        fixed: float,
        span_center: float,
        span_length: float,
        z: float = 1.34,
    ) -> None:
        face_offset = 0.54 if fixed >= 0.0 else -0.54
        if orientation == "east_west":
            center = (fixed + face_offset, span_center)
            size = (0.040, span_length)
        else:
            center = (span_center, fixed + face_offset)
            size = (span_length, 0.040)
        obj.add_box(center, size, 0.42, z, name, "StoneGrimeOverlay")
        add_facade_detail(
            name,
            "facade_base_grime_band",
            (center[0], center[1], z + 0.21),
            {"orientation": orientation, "length_m": round(span_length, 3)},
        )

    def add_close_range_masonry_relief(
        prefix: str,
        orientation: str,
        fixed: float,
        span_center: float,
        span_length: float,
        z_base: float,
        z_top: float,
        columns: int,
        rows: int,
    ) -> None:
        face_offset = 0.58 if fixed >= 0.0 else -0.58
        face = fixed + face_offset
        row_height = (z_top - z_base) / rows
        column_width = span_length / columns
        min_span = span_center - span_length / 2.0

        for row_index in range(1, rows):
            z = z_base + row_height * row_index
            if orientation == "east_west":
                center = (face, span_center)
                size = (0.035, span_length * 0.94)
            else:
                center = (span_center, face)
                size = (span_length * 0.94, 0.035)
            name = f"{prefix}_mortar_shadow_groove_{row_index:02d}"
            obj.add_box(center, size, 0.038, z, name, "StoneGrimeOverlay")
            add_facade_detail(
                name,
                "facade_mortar_shadow_groove",
                (center[0], center[1], z + 0.019),
                {"orientation": orientation, "span_m": round(span_length, 3), "public_accuracy": "generic_public_masonry_relief"},
            )

        for row_index in range(rows):
            row_z = z_base + row_height * row_index + row_height * 0.14
            stagger = 0.5 if row_index % 2 else 0.0
            for column_index in range(1, columns):
                span_value = min_span + (column_index + stagger) * column_width
                if span_value > min_span + span_length - column_width * 0.18:
                    continue
                if orientation == "east_west":
                    center = (face, span_value)
                    size = (0.042, 0.055)
                else:
                    center = (span_value, face)
                    size = (0.055, 0.042)
                name = f"{prefix}_staggered_masonry_joint_r{row_index+1:02d}_c{column_index:02d}"
                obj.add_box(center, size, row_height * 0.68, row_z, name, "StoneGrimeOverlay")
                add_facade_detail(
                    name,
                    "facade_staggered_masonry_joint",
                    (center[0], center[1], row_z + row_height * 0.34),
                    {
                        "orientation": orientation,
                        "row": row_index + 1,
                        "column": column_index,
                        "public_accuracy": "generic_public_masonry_relief",
                    },
                )

        for row_index in range(rows):
            for column_index in range(columns):
                if (row_index * 3 + column_index * 5 + len(prefix)) % 4 != 0:
                    continue
                span_value = min_span + column_width * (column_index + 0.5)
                z = z_base + row_height * row_index + row_height * (0.42 + 0.08 * ((row_index + column_index) % 2))
                chip_span = min(column_width * 0.34, 0.42)
                chip_height = min(row_height * 0.24, 0.24)
                if orientation == "east_west":
                    center = (face + (0.018 if fixed >= 0.0 else -0.018), span_value + column_width * 0.18 * ((column_index % 2) - 0.5))
                    size = (0.030, chip_span)
                else:
                    center = (span_value + column_width * 0.18 * ((column_index % 2) - 0.5), face + (0.018 if fixed >= 0.0 else -0.018))
                    size = (chip_span, 0.030)
                name = f"{prefix}_chipped_limestone_block_r{row_index+1:02d}_c{column_index+1:02d}"
                obj.add_box(center, size, chip_height, z, name, "StepStone")
                add_facade_detail(
                    name,
                    "facade_chipped_limestone_block",
                    (center[0], center[1], z + chip_height / 2.0),
                    {
                        "orientation": orientation,
                        "row": row_index + 1,
                        "column": column_index + 1,
                        "public_accuracy": "generic_public_masonry_relief",
                    },
                )

        bevel_specs = [
            ("lower", z_base, 0.060),
            ("upper", z_top, 0.065),
        ]
        for label, z, height in bevel_specs:
            if orientation == "east_west":
                center = (face + (0.018 if fixed >= 0.0 else -0.018), span_center)
                size = (0.050, span_length * 0.96)
            else:
                center = (span_center, face + (0.018 if fixed >= 0.0 else -0.018))
                size = (span_length * 0.96, 0.050)
            name = f"{prefix}_{label}_panel_bevel_strip"
            obj.add_box(center, size, height, z, name, "ColumnStone")
            add_facade_detail(
                name,
                "facade_panel_bevel_strip",
                (center[0], center[1], z + height / 2.0),
                {"orientation": orientation, "edge": label, "public_accuracy": "generic_public_masonry_relief"},
            )

    def add_close_range_stone_surface_wear(
        prefix: str,
        orientation: str,
        fixed: float,
        span_center: float,
        span_length: float,
        z_base: float,
        z_top: float,
        columns: int,
        rows: int,
    ) -> None:
        face_offset = 0.625 if fixed >= 0.0 else -0.625
        face = fixed + face_offset
        row_height = (z_top - z_base) / rows
        column_width = span_length / columns
        min_span = span_center - span_length / 2.0

        for row_index in range(rows):
            row_z = z_base + row_height * row_index
            for column_index in range(columns):
                if (row_index * 5 + column_index * 7 + len(prefix)) % 3 != 0:
                    continue
                span_value = min_span + column_width * (column_index + 0.5)
                spot_z = row_z + row_height * (0.30 + 0.11 * ((row_index + column_index) % 4))
                pit_span = min(0.18 + 0.035 * ((row_index + column_index) % 3), column_width * 0.30)
                pit_height = min(0.055 + 0.018 * ((row_index + column_index) % 2), row_height * 0.13)
                if orientation == "east_west":
                    center = (face, span_value + column_width * 0.16 * (((row_index + column_index) % 2) - 0.5))
                    size = (0.020, pit_span)
                else:
                    center = (span_value + column_width * 0.16 * (((row_index + column_index) % 2) - 0.5), face)
                    size = (pit_span, 0.020)
                name = f"{prefix}_limestone_pitting_r{row_index+1:02d}_c{column_index+1:02d}"
                obj.add_box(center, size, pit_height, spot_z, name, "StoneGrimeOverlay")
                add_facade_detail(
                    name,
                    "facade_limestone_pitting_mark",
                    (center[0], center[1], spot_z + pit_height / 2.0),
                    {
                        "orientation": orientation,
                        "row": row_index + 1,
                        "column": column_index + 1,
                        "public_accuracy": "generic_public_surface_wear",
                    },
                )

        crack_count = max(3, columns // 3)
        for crack_index in range(crack_count):
            span_value = min_span + span_length * (crack_index + 0.7) / (crack_count + 0.4)
            crack_z = z_base + (z_top - z_base) * (0.22 + 0.13 * ((crack_index + len(prefix)) % 5))
            segment_height = min(0.52, (z_top - z_base) * 0.09)
            lateral_shift = column_width * 0.08
            for segment_index, shift_sign in enumerate((-1.0, 1.0), start=1):
                if orientation == "east_west":
                    center = (face, span_value + shift_sign * lateral_shift)
                    size = (0.018, 0.075)
                else:
                    center = (span_value + shift_sign * lateral_shift, face)
                    size = (0.075, 0.018)
                z = crack_z + (segment_index - 1) * segment_height * 0.82
                name = f"{prefix}_hairline_crack_{crack_index+1:02d}_{segment_index:02d}"
                obj.add_box(center, size, segment_height, z, name, "StoneGrimeOverlay")
                add_facade_detail(
                    name,
                    "facade_hairline_crack",
                    (center[0], center[1], z + segment_height / 2.0),
                    {
                        "orientation": orientation,
                        "segment": segment_index,
                        "public_accuracy": "generic_public_surface_wear",
                    },
                )

        rain_count = max(6, columns // 2)
        for streak_index in range(rain_count):
            span_value = min_span + span_length * (streak_index + 0.5) / rain_count
            streak_height = 0.64 + 0.16 * ((streak_index + len(prefix)) % 4)
            streak_z = z_base + (z_top - z_base) * (0.46 + 0.07 * (streak_index % 3))
            streak_width = 0.055 + 0.012 * (streak_index % 3)
            if orientation == "east_west":
                center = (face, span_value)
                size = (0.018, streak_width)
            else:
                center = (span_value, face)
                size = (streak_width, 0.018)
            name = f"{prefix}_thin_rain_streak_{streak_index+1:02d}"
            obj.add_box(center, size, streak_height, streak_z, name, "StoneGrimeOverlay")
            add_facade_detail(
                name,
                "facade_thin_rain_streak",
                (center[0], center[1], streak_z + streak_height / 2.0),
                {
                    "orientation": orientation,
                    "height_m": round(streak_height, 3),
                    "public_accuracy": "generic_public_surface_wear",
                },
            )

    def add_public_step_grime_seams(
        prefix: str,
        orientation: str,
        center: tuple[float, float],
        span: float,
        count: int,
        z: float,
    ) -> None:
        cx, cy = center
        for index in range(count):
            offset = -span / 2.0 + span * (index + 0.5) / count
            if orientation == "east_west":
                seam_center = (cx, cy + offset)
                seam_size = (0.040, span / count * 0.48)
            else:
                seam_center = (cx + offset, cy)
                seam_size = (span / count * 0.48, 0.040)
            name = f"{prefix}_step_grime_seam_{index+1:02d}"
            obj.add_box(seam_center, seam_size, 0.026, z, name, "StoneGrimeOverlay")
            add_facade_detail(
                name,
                "public_step_grime_seam",
                (seam_center[0], seam_center[1], z + 0.013),
                {"orientation": orientation, "public_accuracy": "generic_public_approach_wear"},
            )

    def add_plaza_wear_patch(name: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        obj.add_box(center, size, 0.026, z, name, "StepStone")
        add_facade_detail(
            name,
            "plaza_wear_patch",
            (center[0], center[1], z + 0.013),
            {"size_m": [round(size[0], 3), round(size[1], 3)]},
        )

    def add_public_plaza_surface_details() -> None:
        def plaza_detail(
            name: str,
            kind: str,
            center: tuple[float, float],
            size: tuple[float, float],
            z: float,
            material: str,
            extra: dict[str, Any] | None = None,
        ) -> None:
            obj.add_box(center, size, 0.018, z, name, material)
            metadata = {
                "size_m": [round(size[0], 3), round(size[1], 3)],
                "public_accuracy": "schematic_public_plaza_surface_detail",
            }
            if extra:
                metadata.update(extra)
            add_facade_detail(name, kind, (center[0], center[1], z + 0.009), metadata)

        def paver_grid(prefix: str, center: tuple[float, float], size: tuple[float, float], columns: int, rows: int) -> None:
            cx, cy = center
            sx, sy = size
            for col in range(1, columns):
                x = cx - sx / 2.0 + sx * col / columns
                plaza_detail(
                    f"{prefix}_vertical_paver_joint_{col:02d}",
                    "public_plaza_paver_joint",
                    (x, cy),
                    (0.040, sy),
                    0.112,
                    "RoadCrackSealant",
                    {"orientation": "north_south", "panel": prefix},
                )
            for row in range(1, rows):
                y = cy - sy / 2.0 + sy * row / rows
                plaza_detail(
                    f"{prefix}_horizontal_paver_joint_{row:02d}",
                    "public_plaza_paver_joint",
                    (cx, y),
                    (sx, 0.040),
                    0.112,
                    "RoadCrackSealant",
                    {"orientation": "east_west", "panel": prefix},
                )

        plaza_panels = [
            ("west_front_public_plaza", (-70.0, 0.0), (30.0, 154.0), 4, 14),
            ("east_front_public_plaza", (70.0, 0.0), (30.0, 154.0), 4, 14),
            ("north_public_plaza", (0.0, 86.0), (154.0, 24.0), 14, 3),
            ("south_public_plaza", (0.0, -86.0), (154.0, 24.0), 14, 3),
        ]
        for prefix, center, size, columns, rows in plaza_panels:
            paver_grid(prefix, center, size, columns, rows)

        expansion_specs = [
            ("west_front_plaza_expansion_seam_north", (-70.0, 38.5), (30.0, 0.085), "east_west"),
            ("west_front_plaza_expansion_seam_center", (-70.0, 0.0), (30.0, 0.085), "east_west"),
            ("west_front_plaza_expansion_seam_south", (-70.0, -38.5), (30.0, 0.085), "east_west"),
            ("east_front_plaza_expansion_seam_north", (70.0, 38.5), (30.0, 0.085), "east_west"),
            ("east_front_plaza_expansion_seam_center", (70.0, 0.0), (30.0, 0.085), "east_west"),
            ("east_front_plaza_expansion_seam_south", (70.0, -38.5), (30.0, 0.085), "east_west"),
            ("north_plaza_expansion_seam_west", (-38.5, 86.0), (0.085, 24.0), "north_south"),
            ("north_plaza_expansion_seam_center", (0.0, 86.0), (0.085, 24.0), "north_south"),
            ("north_plaza_expansion_seam_east", (38.5, 86.0), (0.085, 24.0), "north_south"),
            ("south_plaza_expansion_seam_west", (-38.5, -86.0), (0.085, 24.0), "north_south"),
            ("south_plaza_expansion_seam_center", (0.0, -86.0), (0.085, 24.0), "north_south"),
            ("south_plaza_expansion_seam_east", (38.5, -86.0), (0.085, 24.0), "north_south"),
        ]
        for name, center, size, orientation in expansion_specs:
            plaza_detail(name, "public_plaza_expansion_seam", center, size, 0.126, "RoadCrackSealant", {"orientation": orientation})

        for panel_index, (prefix, center, size, _columns, _rows) in enumerate(plaza_panels, start=1):
            cx, cy = center
            sx, sy = size
            for patch_index in range(8):
                x_offset = ((patch_index % 4) - 1.5) * sx * 0.18
                y_offset = ((patch_index // 4) - 0.5) * sy * 0.32
                patch_center = (cx + x_offset, cy + y_offset)
                patch_size = (min(3.2, sx * 0.18), min(1.6, sy * 0.11))
                plaza_detail(
                    f"{prefix}_stone_tone_variation_patch_{patch_index+1:02d}",
                    "public_plaza_stone_tone_patch",
                    patch_center,
                    patch_size,
                    0.118 + panel_index * 0.001,
                    "StoneGrimeOverlay",
                    {"panel": prefix, "variation_index": patch_index + 1},
                )

        drain_specs = []
        for index, y in enumerate([-54.0, -18.0, 18.0, 54.0], start=1):
            drain_specs.append((f"west_front_plaza_linear_drain_slot_{index:02d}", (-86.0, y), (0.10, 2.8), "north_south"))
            drain_specs.append((f"east_front_plaza_linear_drain_slot_{index:02d}", (86.0, y), (0.10, 2.8), "north_south"))
        for index, x in enumerate([-44.0, 0.0, 44.0], start=1):
            drain_specs.append((f"north_plaza_linear_drain_slot_{index:02d}", (x, 105.6), (2.8, 0.10), "east_west"))
            drain_specs.append((f"south_plaza_linear_drain_slot_{index:02d}", (x, -105.6), (2.8, 0.10), "east_west"))
        for name, center, size, orientation in drain_specs:
            plaza_detail(name, "public_plaza_linear_drain_slot", center, size, 0.132, "RoadCrackSealant", {"orientation": orientation})

    def add_step_edge_chip_shadow(
        name: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
        orientation: str,
    ) -> None:
        obj.add_box(center, size, 0.018, z, name, "StoneGrimeOverlay")
        add_facade_detail(
            name,
            "public_step_edge_chip_shadow",
            (center[0], center[1], z + 0.009),
            {"orientation": orientation, "size_m": [round(size[0], 3), round(size[1], 3)]},
        )

    def add_exterior_column_ornament(
        prefix: str,
        center: tuple[float, float],
        radius: float,
        z_base: float,
        height: float,
        orientation: str,
    ) -> None:
        obj.add_cylinder(center, radius * 1.34, z_base - 0.12, 0.16, f"{prefix}_round_plinth", "ColumnStone", segments=24)
        obj.add_ring(center, radius * 1.24, radius * 0.92, z_base + 0.08, 0.20, f"{prefix}_base_torus", "ColumnStone", segments=24)
        obj.add_ring(center, radius * 1.16, radius * 0.98, z_base + 0.34, 0.075, f"{prefix}_base_reed_ring", "ColumnStone", segments=24)
        obj.add_ring(center, radius * 1.18, radius * 0.90, z_base + height - 0.32, 0.22, f"{prefix}_capital_torus", "ColumnStone", segments=24)
        obj.add_box(center, (radius * 2.65, radius * 2.65), 0.18, z_base + height - 0.02, f"{prefix}_square_abacus", "ColumnStone")
        obj.add_box(center, (radius * 2.28, radius * 2.28), 0.075, z_base + height + 0.17, f"{prefix}_abacus_top_bevel", "ColumnStone")

        for leaf_index in range(8):
            angle = math.tau * leaf_index / 8.0
            leaf_center = (
                center[0] + radius * 1.06 * math.cos(angle),
                center[1] + radius * 1.06 * math.sin(angle),
            )
            leaf_name = f"{prefix}_capital_leaf_detail_{leaf_index + 1:02d}"
            obj.add_oriented_box(
                leaf_center,
                (0.10, radius * 0.34),
                0.34,
                z_base + height - 0.70,
                angle + math.pi / 2.0,
                leaf_name,
                "ColumnStone",
            )
            add_facade_detail(
                leaf_name,
                "exterior_column_capital_leaf_detail",
                (leaf_center[0], leaf_center[1], z_base + height - 0.53),
                {"orientation": orientation, "angle_degrees": round(math.degrees(angle), 2)},
            )

        face_sign = 1.0 if (center[0] if orientation == "east_west" else center[1]) >= 0.0 else -1.0
        for volute_index, tangent_offset in enumerate((-radius * 0.58, radius * 0.58), start=1):
            if orientation == "east_west":
                volute_center = (center[0] + face_sign * radius * 1.22, center[1] + tangent_offset)
                volute_size = (0.11, radius * 0.34)
            else:
                volute_center = (center[0] + tangent_offset, center[1] + face_sign * radius * 1.22)
                volute_size = (radius * 0.34, 0.11)
            volute_name = f"{prefix}_capital_volute_detail_{volute_index:02d}"
            obj.add_box(volute_center, volute_size, 0.30, z_base + height - 0.43, volute_name, "ColumnStone")
            add_facade_detail(
                volute_name,
                "exterior_column_capital_volute_detail",
                (volute_center[0], volute_center[1], z_base + height - 0.28),
                {"orientation": orientation, "face_sign": face_sign},
            )

        for chip_index, angle in enumerate((0.0, math.pi / 2.0, math.pi, math.pi * 1.5), start=1):
            chip_center = (
                center[0] + radius * 1.36 * math.cos(angle),
                center[1] + radius * 1.36 * math.sin(angle),
            )
            chip_name = f"{prefix}_base_chip_detail_{chip_index:02d}"
            obj.add_oriented_box(
                chip_center,
                (0.08, radius * 0.38),
                0.08,
                z_base + 0.06,
                angle + math.pi / 2.0,
                chip_name,
                "StoneGrimeOverlay",
            )
            add_facade_detail(
                chip_name,
                "exterior_column_base_chip_detail",
                (chip_center[0], chip_center[1], z_base + 0.10),
                {"orientation": orientation, "angle_degrees": round(math.degrees(angle), 2)},
            )

        flute_count = 12
        flute_height = max(0.5, height - 1.24)
        for flute_index in range(flute_count):
            angle = math.tau * flute_index / flute_count
            flute_center = (
                center[0] + (radius + 0.035) * math.cos(angle),
                center[1] + (radius + 0.035) * math.sin(angle),
            )
            obj.add_oriented_box(
                flute_center,
                (0.050, radius * 0.30),
                flute_height,
                z_base + 0.58,
                angle + math.pi / 2.0,
                f"{prefix}_flute_shadow_{flute_index + 1:02d}",
                "StepStone",
            )
            add_facade_detail(
                f"{prefix}_flute_groove_{flute_index + 1:02d}",
                "exterior_column_fluting_groove",
                (flute_center[0], flute_center[1], z_base + 0.58 + flute_height / 2.0),
                {
                    "orientation": orientation,
                    "angle_degrees": round(math.degrees(angle), 2),
                    "public_accuracy": "generic_public_column_flute_shadow",
                },
            )

        add_facade_detail(
            f"{prefix}_column_base",
            "exterior_column_base",
            (center[0], center[1], z_base + 0.10),
            {"orientation": orientation, "radius_m": round(radius, 3)},
        )
        add_facade_detail(
            f"{prefix}_column_capital",
            "exterior_column_capital",
            (center[0], center[1], z_base + height - 0.12),
            {"orientation": orientation, "radius_m": round(radius, 3)},
        )
        add_facade_detail(
            f"{prefix}_column_base_ring_detail",
            "exterior_column_base_ring_detail",
            (center[0], center[1], z_base + 0.38),
            {"orientation": orientation, "radius_m": round(radius, 3)},
        )
        add_facade_detail(
            f"{prefix}_column_capital_abacus_detail",
            "exterior_column_capital_abacus_detail",
            (center[0], center[1], z_base + height + 0.21),
            {"orientation": orientation, "radius_m": round(radius, 3)},
        )
        add_facade_detail(
            f"{prefix}_column_fluting",
            "exterior_column_fluting",
            (center[0], center[1], z_base + height / 2.0),
            {"orientation": orientation, "flute_count": flute_count},
        )

    def add_column_row(prefix: str, orientation: str, fixed: float, values: list[float], z_base: float, height: float) -> None:
        for idx, value in enumerate(values, start=1):
            center = (fixed, value) if orientation == "east_west" else (value, fixed)
            name = f"{prefix}_column_{idx:02d}"
            obj.add_cylinder(center, 0.46, z_base, height, name, "ColumnStone", segments=18)
            add_exterior_column_ornament(name, center, 0.46, z_base, height, orientation)
            add_facade_detail(name, "exterior_column", (center[0], center[1], z_base + height / 2.0))

    def add_dentil_row(prefix: str, orientation: str, fixed: float, values: list[float], z: float) -> None:
        for idx, value in enumerate(values, start=1):
            if orientation == "east_west":
                x = fixed + (0.18 if fixed >= 0.0 else -0.18)
                center = (x, value)
                size = (0.34, 0.42)
            else:
                y = fixed + (0.18 if fixed >= 0.0 else -0.18)
                center = (value, y)
                size = (0.42, 0.34)
            obj.add_box(center, size, 0.34, z, f"{prefix}_dentil_{idx:02d}", "ColumnStone")
            add_facade_detail(
                f"{prefix}_dentil_block_{idx:02d}",
                "facade_dentil_block_detail",
                (center[0], center[1], z + 0.17),
                {"orientation": orientation, "sequence": idx},
            )
        if values:
            center = (fixed, sum(values) / len(values), z + 0.17) if orientation == "east_west" else (sum(values) / len(values), fixed, z + 0.17)
            add_facade_detail(f"{prefix}_dentil_course", "facade_dentil_course", center, {"orientation": orientation, "count": len(values)})

    def add_facade_pilaster_line(
        prefix: str,
        orientation: str,
        fixed: float,
        values: list[float],
        z_base: float,
        height: float,
    ) -> None:
        for idx, value in enumerate(values, start=1):
            if orientation == "east_west":
                x = fixed + (0.20 if fixed >= 0.0 else -0.20)
                center = (x, value)
                size = (0.44, 0.34)
            else:
                y = fixed + (0.20 if fixed >= 0.0 else -0.20)
                center = (value, y)
                size = (0.34, 0.44)
            obj.add_box(center, size, height, z_base, f"{prefix}_pilaster_{idx:02d}", "ColumnStone")
            obj.add_box(center, (size[0] * 1.45, size[1] * 1.45), 0.22, z_base, f"{prefix}_pilaster_{idx:02d}_base", "ColumnStone")
            obj.add_box(center, (size[0] * 1.35, size[1] * 1.35), 0.24, z_base + height, f"{prefix}_pilaster_{idx:02d}_capital", "ColumnStone")
            add_facade_detail(
                f"{prefix}_pilaster_{idx:02d}",
                "facade_pilaster",
                (center[0], center[1], z_base + height / 2.0),
                {"orientation": orientation},
            )

    def add_balustrade_line(prefix: str, orientation: str, fixed: float, values: list[float], z: float) -> None:
        if not values:
            return
        span = max(values) - min(values) + 2.0
        if orientation == "east_west":
            x = fixed + (0.16 if fixed >= 0.0 else -0.16)
            for idx, value in enumerate(values, start=1):
                obj.add_cylinder((x, value), 0.13, z, 0.86, f"{prefix}_baluster_{idx:02d}", "ColumnStone", segments=8)
            obj.add_box((x, (min(values) + max(values)) / 2.0), (0.22, span), 0.16, z + 0.86, f"{prefix}_top_rail", "ColumnStone")
            center = (x, (min(values) + max(values)) / 2.0, z + 0.52)
        else:
            y = fixed + (0.16 if fixed >= 0.0 else -0.16)
            for idx, value in enumerate(values, start=1):
                obj.add_cylinder((value, y), 0.13, z, 0.86, f"{prefix}_baluster_{idx:02d}", "ColumnStone", segments=8)
            obj.add_box(((min(values) + max(values)) / 2.0, y), (span, 0.22), 0.16, z + 0.86, f"{prefix}_top_rail", "ColumnStone")
            center = ((min(values) + max(values)) / 2.0, y, z + 0.52)
        add_facade_detail(f"{prefix}_roof_balustrade", "roof_balustrade", center, {"orientation": orientation, "count": len(values)})

    def add_window_grid_on_face(
        prefix: str,
        orientation: str,
        fixed: float,
        values: list[float],
        z_levels: list[float],
        width: float = 0.92,
        height: float = 1.06,
    ) -> None:
        for level_index, z_level in enumerate(z_levels, start=1):
            for value_index, value in enumerate(values, start=1):
                x, y = (fixed, value) if orientation == "east_west" else (value, fixed)
                if orientation == "east_west":
                    obj.add_box((x, y), (0.10, width), height, z_level, f"{prefix}_window_{level_index:02d}_{value_index:02d}", "FacadeWindow")
                else:
                    obj.add_box((x, y), (width, 0.10), height, z_level, f"{prefix}_window_{level_index:02d}_{value_index:02d}", "FacadeWindow")
                add_facade_detail(
                    f"{prefix}_window_{level_index:02d}_{value_index:02d}",
                    "facade_window",
                    (x, y, z_level + height / 2.0),
                    {"orientation": orientation},
                )
                add_window_mullions(
                    f"{prefix}_window_{level_index:02d}_{value_index:02d}_mullions",
                    (x, y),
                    z_level,
                    orientation,
                    width,
                    height,
                )
                add_window_surround(
                    f"{prefix}_window_{level_index:02d}_{value_index:02d}",
                    (x, y),
                    z_level,
                    orientation,
                    width,
                    height,
                )
                add_window_depth_details(
                    f"{prefix}_window_{level_index:02d}_{value_index:02d}",
                    (x, y),
                    z_level,
                    orientation,
                    width,
                    height,
                )

    def add_stair_tread_detail(
        name: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
        height: float,
        orientation: str,
    ) -> None:
        obj.add_box(center, size, height, z, name, "StepStone")
        add_facade_detail(
            name,
            "public_stair_tread",
            (center[0], center[1], z + height / 2.0),
            {"orientation": orientation, "width_m": round(max(size), 3)},
        )

    def add_radial_trim_bar(
        name: str,
        angle: float,
        radius: float,
        tangent_offset: float,
        z: float,
        height: float,
        width: float,
        depth: float,
        material: str = "ColumnStone",
    ) -> None:
        radial = (math.cos(angle), math.sin(angle))
        tangent = (-math.sin(angle), math.cos(angle))
        cx = radius * radial[0] + tangent_offset * tangent[0]
        cy = radius * radial[1] + tangent_offset * tangent[1]
        points = [
            (cx - tangent[0] * width / 2.0 - radial[0] * depth / 2.0, cy - tangent[1] * width / 2.0 - radial[1] * depth / 2.0),
            (cx + tangent[0] * width / 2.0 - radial[0] * depth / 2.0, cy + tangent[1] * width / 2.0 - radial[1] * depth / 2.0),
            (cx + tangent[0] * width / 2.0 + radial[0] * depth / 2.0, cy + tangent[1] * width / 2.0 + radial[1] * depth / 2.0),
            (cx - tangent[0] * width / 2.0 + radial[0] * depth / 2.0, cy - tangent[1] * width / 2.0 + radial[1] * depth / 2.0),
        ]
        obj.add_extruded_polygon(points, dome_z(z), dome_height(height), name, material)

    def add_dome_window_trim(index: int, angle: float, radius: float) -> None:
        add_radial_trim_bar(f"dome_drum_window_glass_pane_{index:02d}", angle, radius - 0.18, 0.0, 22.70, 1.26, 0.76, 0.09, "DoorGlass")
        add_radial_trim_bar(f"dome_drum_window_trim_{index:02d}_left_jamb", angle, radius, -0.45, 22.55, 1.62, 0.12, 0.28)
        add_radial_trim_bar(f"dome_drum_window_trim_{index:02d}_right_jamb", angle, radius, 0.45, 22.55, 1.62, 0.12, 0.28)
        add_radial_trim_bar(f"dome_drum_window_trim_{index:02d}_lintel", angle, radius, 0.0, 24.08, 0.14, 1.04, 0.30)
        add_radial_trim_bar(f"dome_drum_window_trim_{index:02d}_sill", angle, radius, 0.0, 22.40, 0.14, 0.98, 0.30)
        add_facade_detail(
            f"dome_drum_window_glass_pane_{index:02d}",
            "dome_drum_window_glass_pane",
            ((radius - 0.18) * math.cos(angle), (radius - 0.18) * math.sin(angle), dome_z(23.33)),
            {"radial_index": index},
        )
        add_facade_detail(
            f"dome_drum_window_trim_{index:02d}",
            "dome_drum_window_trim",
            (radius * math.cos(angle), radius * math.sin(angle), dome_z(23.35)),
            {"radial_index": index},
        )

    def dome_shell_radius(z: float) -> float:
        t = max(0.0, min(1.0, (z - 34.0) / 22.0))
        return 18.0 * math.sqrt(max(0.0, 1.0 - t * t))

    def add_dome_shell_panel_frame(
        name: str,
        angle: float,
        z: float,
        panel_height: float,
        panel_width: float,
    ) -> None:
        radius = dome_shell_radius(z + panel_height / 2.0) + 0.22
        add_radial_trim_bar(f"{name}_left_stile", angle, radius, -panel_width / 2.0, z, panel_height, 0.055, 0.22)
        add_radial_trim_bar(f"{name}_right_stile", angle, radius, panel_width / 2.0, z, panel_height, 0.055, 0.22)
        add_radial_trim_bar(f"{name}_bottom_rail", angle, radius, 0.0, z, 0.065, panel_width, 0.22)
        add_radial_trim_bar(f"{name}_top_rail", angle, radius, 0.0, z + panel_height, 0.065, panel_width, 0.22)
        add_facade_detail(
            name,
            "dome_shell_panel_frame",
            (radius * math.cos(angle), radius * math.sin(angle), dome_z(z + panel_height / 2.0)),
            {"angle_degrees": round(math.degrees(angle), 2), "size_m": [round(panel_width, 3), round(panel_height, 3)]},
        )

    def add_dome_drum_spandrel_panel(name: str, angle: float, z: float) -> None:
        radius = 18.18
        add_radial_trim_bar(f"{name}_stone_panel", angle, radius, 0.0, z, 0.34, 1.18, 0.24)
        add_facade_detail(
            name,
            "dome_drum_spandrel_panel",
            (radius * math.cos(angle), radius * math.sin(angle), dome_z(z + 0.17)),
            {"angle_degrees": round(math.degrees(angle), 2)},
        )

    def add_dome_drum_arcade_bay(index: int, angle: float) -> None:
        radius = 18.42
        add_radial_trim_bar(f"dome_drum_arcade_bay_{index:02d}_left_pier", angle, radius, -0.74, 20.85, 4.05, 0.16, 0.34)
        add_radial_trim_bar(f"dome_drum_arcade_bay_{index:02d}_right_pier", angle, radius, 0.74, 20.85, 4.05, 0.16, 0.34)
        add_radial_trim_bar(f"dome_drum_arcade_bay_{index:02d}_impost_band", angle, radius, 0.0, 24.58, 0.16, 1.78, 0.36)
        add_radial_trim_bar(f"dome_drum_arcade_bay_{index:02d}_arch_lintel", angle, radius, 0.0, 25.02, 0.24, 1.34, 0.40)
        add_radial_trim_bar(f"dome_drum_arcade_bay_{index:02d}_keystone", angle, radius, 0.0, 25.10, 0.62, 0.20, 0.48)
        add_facade_detail(
            f"dome_drum_arcade_bay_{index:02d}",
            "dome_drum_arcade_bay",
            (radius * math.cos(angle), radius * math.sin(angle), dome_z(23.25)),
            {"angle_degrees": round(math.degrees(angle), 2)},
        )

    def add_dome_curved_rib(index: int, angle: float) -> None:
        segments_spec = [
            (34.35, 1.18),
            (36.05, 1.28),
            (37.95, 1.34),
            (40.10, 1.28),
            (42.35, 1.22),
            (44.70, 1.14),
            (47.05, 1.02),
            (49.30, 0.92),
            (51.35, 0.78),
            (53.05, 0.56),
        ]
        for segment_index, (z, height) in enumerate(segments_spec, start=1):
            radius = dome_shell_radius(z + height / 2.0) + 0.36
            add_radial_trim_bar(
                f"dome_curved_rib_{index:02d}_segment_{segment_index:02d}",
                angle,
                radius,
                0.0,
                z,
                height,
                0.14,
                0.34,
            )
        mid_radius = dome_shell_radius(43.8) + 0.36
        add_facade_detail(
            f"dome_curved_rib_{index:02d}",
            "dome_curved_rib",
            (mid_radius * math.cos(angle), mid_radius * math.sin(angle), dome_z(43.8)),
            {"radial_index": index, "segments": len(segments_spec)},
        )

    def add_dome_shell_weathering_details() -> None:
        for index in range(32):
            angle = math.tau * (index + 0.18) / 32.0
            z = 36.35 + (index % 4) * 2.9
            height = 1.65 + (index % 5) * 0.28
            radius = dome_shell_radius(z + height / 2.0) + 0.43
            name = f"dome_shell_rain_streak_{index+1:02d}"
            add_radial_trim_bar(name, angle, radius, 0.0, z, height, 0.055, 0.085, "StoneGrimeOverlay")
            add_facade_detail(
                name,
                "dome_shell_rain_streak",
                (radius * math.cos(angle), radius * math.sin(angle), dome_z(z + height / 2.0)),
                {"angle_degrees": round(math.degrees(angle), 2), "public_accuracy": "generic_public_dome_weathering"},
            )
        for index in range(24):
            angle = math.tau * (index + 0.5) / 24.0
            for seam_index, (z, height, width) in enumerate([(35.95, 1.10, 0.040), (44.75, 0.92, 0.036)], start=1):
                radius = dome_shell_radius(z + height / 2.0) + 0.39
                name = f"dome_shell_panel_shadow_seam_{index+1:02d}_{seam_index:02d}"
                add_radial_trim_bar(name, angle, radius, 0.0, z, height, width, 0.070, "RoadCrackSealant")
                add_facade_detail(
                    name,
                    "dome_shell_panel_shadow_seam",
                    (radius * math.cos(angle), radius * math.sin(angle), dome_z(z + height / 2.0)),
                    {"angle_degrees": round(math.degrees(angle), 2), "public_accuracy": "generic_public_dome_panel_relief"},
                )

    def add_lantern_window_trim(index: int, angle: float) -> None:
        radius = 4.78
        add_radial_trim_bar(f"dome_lantern_window_glass_pane_{index:02d}", angle, radius - 0.16, 0.0, 56.10, 1.86, 0.58, 0.07, "DoorGlass")
        add_radial_trim_bar(f"dome_lantern_window_trim_{index:02d}_left_jamb", angle, radius, -0.36, 56.02, 2.05, 0.075, 0.20)
        add_radial_trim_bar(f"dome_lantern_window_trim_{index:02d}_right_jamb", angle, radius, 0.36, 56.02, 2.05, 0.075, 0.20)
        add_radial_trim_bar(f"dome_lantern_window_trim_{index:02d}_lintel", angle, radius, 0.0, 58.10, 0.11, 0.82, 0.22)
        add_radial_trim_bar(f"dome_lantern_window_trim_{index:02d}_sill", angle, radius, 0.0, 55.86, 0.11, 0.78, 0.22)
        add_facade_detail(
            f"dome_lantern_window_glass_pane_{index:02d}",
            "lantern_window_glass_pane",
            ((radius - 0.16) * math.cos(angle), (radius - 0.16) * math.sin(angle), dome_z(57.03)),
            {"radial_index": index},
        )
        add_facade_detail(
            f"dome_lantern_window_trim_{index:02d}",
            "lantern_window_trim",
            (radius * math.cos(angle), radius * math.sin(angle), dome_z(57.08)),
            {"radial_index": index},
        )

    def add_statue_of_freedom_silhouette() -> None:
        base_z = statue_base_z
        obj.add_cylinder((0.0, 0.0), 0.56, base_z - 0.28, 0.28, "statue_of_freedom_round_base", "StatueBronze", segments=16)
        obj.add_cylinder((0.0, 0.0), 0.38, base_z, 0.42, "statue_of_freedom_pedestal_silhouette", "StatueBronze", segments=14)
        obj.add_cylinder((0.0, 0.0), 0.30, base_z + 0.36, 3.90, "statue_of_freedom_body_silhouette", "StatueBronze", segments=12)
        obj.add_cylinder((0.0, 0.0), 0.20, base_z + 4.23, 0.48, "statue_of_freedom_head_silhouette", "StatueBronze", segments=12)
        obj.add_box((0.0, 0.0), (1.68, 0.13), 0.18, base_z + 3.18, "statue_of_freedom_arm_silhouette", "StatueBronze")
        obj.add_box((-0.44, 0.0), (0.16, 0.12), 3.06, base_z + 1.18, "statue_of_freedom_left_drape_silhouette", "StatueBronze")
        obj.add_box((0.44, 0.0), (0.16, 0.12), 3.06, base_z + 1.18, "statue_of_freedom_right_drape_silhouette", "StatueBronze")
        obj.add_cylinder((0.0, 0.0), 0.10, capitol_public_height_m - 0.52, 0.52, "statue_of_freedom_plume_silhouette", "StatueBronze", segments=10)
        add_facade_detail(
            "statue_of_freedom_silhouette",
            "statue_of_freedom_silhouette",
            (0.0, 0.0, base_z + statue_of_freedom_height_m / 2.0),
            {"public_height_target_m": round(capitol_public_height_m, 2)},
        )

    def add_revolving_door(name: str, center: tuple[float, float], facade: str) -> None:
        x, y = center
        obj.add_cylinder((x, y), 1.18, 0.14, 2.65, f"{name}_glass_drum", "DoorGlass", segments=28)
        add_facade_detail(
            f"{name}_glass_drum",
            "public_revolving_door_glass_drum",
            (x, y, 1.465),
            {"facade": facade, "public_accuracy": "approximate_public_entrance_visual"},
        )
        for track_name, track_z in [("floor_track_ring", 0.10), ("ceiling_track_ring", 2.82)]:
            obj.add_ring((x, y), 1.25, 1.05, track_z, 0.075, f"{name}_{track_name}", "DoorMetal", segments=32)
            add_facade_detail(
                f"{name}_{track_name}",
                "public_revolving_door_track_ring",
                (x, y, track_z + 0.038),
                {"facade": facade, "position": track_name, "public_accuracy": "approximate_public_entrance_visual"},
            )
        obj.add_cylinder((x, y), 0.10, 0.12, 2.85, f"{name}_center_post", "DoorMetal", segments=12)
        add_facade_detail(
            f"{name}_center_post",
            "public_revolving_door_center_post",
            (x, y, 1.545),
            {"facade": facade, "public_accuracy": "approximate_public_entrance_visual"},
        )
        for wing_index, angle in enumerate([math.radians(18.0), math.radians(108.0), math.radians(198.0), math.radians(288.0)], start=1):
            wing_center = (x + math.cos(angle) * 0.56, y + math.sin(angle) * 0.56)
            obj.add_oriented_box(
                wing_center,
                (1.12, 0.055),
                2.38,
                0.28,
                angle,
                f"{name}_radial_glass_wing_{wing_index:02d}",
                "DoorGlass",
            )
            add_facade_detail(
                f"{name}_radial_glass_wing_{wing_index:02d}",
                "public_revolving_door_wing_panel",
                (wing_center[0], wing_center[1], 1.47),
                {
                    "facade": facade,
                    "radial_index": wing_index,
                    "angle_degrees": round(math.degrees(angle), 1),
                    "public_accuracy": "approximate_public_entrance_visual",
                },
            )
        for mullion_index, angle in enumerate([math.radians(45.0), math.radians(135.0), math.radians(225.0), math.radians(315.0)], start=1):
            mullion_center = (x + math.cos(angle) * 1.18, y + math.sin(angle) * 1.18)
            obj.add_oriented_box(
                mullion_center,
                (0.055, 0.22),
                2.52,
                0.20,
                angle + math.pi / 2.0,
                f"{name}_curved_drum_mullion_{mullion_index:02d}",
                "DoorMetal",
            )
            add_facade_detail(
                f"{name}_curved_drum_mullion_{mullion_index:02d}",
                "public_revolving_door_perimeter_mullion",
                (mullion_center[0], mullion_center[1], 1.46),
                {
                    "facade": facade,
                    "radial_index": mullion_index,
                    "angle_degrees": round(math.degrees(angle), 1),
                    "public_accuracy": "approximate_public_entrance_visual",
                },
            )
        obj.add_box((x, y), (2.8, 2.8), 0.10, 0.08, f"{name}_threshold_plate", "DoorMetal")
        add_facade_detail(
            f"{name}_threshold_plate",
            "public_revolving_door_threshold_plate",
            (x, y, 0.13),
            {"facade": facade, "public_accuracy": "approximate_public_entrance_visual"},
        )
        if facade in {"east", "west"}:
            obj.add_box((x, y), (0.42, 3.45), 3.05, 0.10, f"{name}_dark_recess", "DoorMetal")
            for lite_index, y_offset in enumerate([-1.52, 1.52], start=1):
                lite_center = (x, y + y_offset)
                obj.add_box(lite_center, (0.14, 0.58), 2.36, 0.36, f"{name}_side_lite_{lite_index:02d}", "DoorGlass")
                add_facade_detail(
                    f"{name}_side_lite_{lite_index:02d}",
                    "public_revolving_door_side_lite",
                    (lite_center[0], lite_center[1], 1.54),
                    {"facade": facade, "side_index": lite_index, "public_accuracy": "approximate_public_entrance_visual"},
                )
        else:
            obj.add_box((x, y), (3.45, 0.42), 3.05, 0.10, f"{name}_dark_recess", "DoorMetal")
            for lite_index, x_offset in enumerate([-1.52, 1.52], start=1):
                lite_center = (x + x_offset, y)
                obj.add_box(lite_center, (0.58, 0.14), 2.36, 0.36, f"{name}_side_lite_{lite_index:02d}", "DoorGlass")
                add_facade_detail(
                    f"{name}_side_lite_{lite_index:02d}",
                    "public_revolving_door_side_lite",
                    (lite_center[0], lite_center[1], 1.54),
                    {"facade": facade, "side_index": lite_index, "public_accuracy": "approximate_public_entrance_visual"},
                )
        add_facade_detail(
            f"{name}_dark_recess",
            "public_revolving_door_dark_recess",
            (x, y, 1.625),
            {"facade": facade, "public_accuracy": "approximate_public_entrance_visual"},
        )
        add_public_door_surround(f"{name}_stone_surround", center, facade)
        add_element(f"{name.replace('_', ' ').title()} revolving door visual", "public_entrance_visual", (x, y, 1.5))

    def add_public_door_surround(name: str, center: tuple[float, float], facade: str) -> None:
        x, y = center
        if facade in {"east", "west"}:
            face_x = x + (0.24 if x >= 0.0 else -0.24)
            obj.add_box((face_x, y - 1.86), (0.44, 0.34), 3.55, 0.12, f"{name}_left_pier", "ColumnStone")
            obj.add_box((face_x, y + 1.86), (0.44, 0.34), 3.55, 0.12, f"{name}_right_pier", "ColumnStone")
            obj.add_box((face_x, y), (0.48, 4.22), 0.34, 3.32, f"{name}_flat_lintel", "ColumnStone")
            obj.add_box((face_x, y), (0.30, 3.05), 0.32, 3.78, f"{name}_transom_glass", "DoorGlass")
        else:
            face_y = y + (0.24 if y >= 0.0 else -0.24)
            obj.add_box((x - 1.86, face_y), (0.34, 0.44), 3.55, 0.12, f"{name}_left_pier", "ColumnStone")
            obj.add_box((x + 1.86, face_y), (0.34, 0.44), 3.55, 0.12, f"{name}_right_pier", "ColumnStone")
            obj.add_box((x, face_y), (4.22, 0.48), 0.34, 3.32, f"{name}_flat_lintel", "ColumnStone")
            obj.add_box((x, face_y), (3.05, 0.30), 0.32, 3.78, f"{name}_transom_glass", "DoorGlass")
        add_facade_detail(name, "public_door_surround", (x, y, 1.95), {"facade": facade})

    def add_cornice_bracket_row(prefix: str, orientation: str, fixed: float, values: list[float], z: float) -> None:
        for idx, value in enumerate(values, start=1):
            if orientation == "east_west":
                x = fixed + (0.32 if fixed >= 0.0 else -0.32)
                center = (x, value)
                size = (0.38, 0.48)
            else:
                y = fixed + (0.32 if fixed >= 0.0 else -0.32)
                center = (value, y)
                size = (0.48, 0.38)
            obj.add_box(center, size, 0.72, z, f"{prefix}_cornice_bracket_{idx:02d}", "ColumnStone")
            add_facade_detail(
                f"{prefix}_cornice_bracket_{idx:02d}",
                "facade_cornice_bracket",
                (center[0], center[1], z + 0.36),
                {"orientation": orientation},
            )

    def add_approach_handrails(name: str, orientation: str, center: tuple[float, float], span: float, offsets: tuple[float, float]) -> None:
        x, y = center
        for side_index, offset in enumerate(offsets, start=1):
            if orientation == "east_west":
                rail_center = (x, y + offset)
                rail_size = (span, 0.13)
                post_offsets = [-span * 0.42, 0.0, span * 0.42]
                for post_index, post_offset in enumerate(post_offsets, start=1):
                    obj.add_box((x + post_offset, y + offset), (0.13, 0.13), 0.92, 0.28, f"{name}_{side_index}_post_{post_index}", "DoorMetal")
            else:
                rail_center = (x + offset, y)
                rail_size = (0.13, span)
                post_offsets = [-span * 0.42, 0.0, span * 0.42]
                for post_index, post_offset in enumerate(post_offsets, start=1):
                    obj.add_box((x + offset, y + post_offset), (0.13, 0.13), 0.92, 0.28, f"{name}_{side_index}_post_{post_index}", "DoorMetal")
            obj.add_box(rail_center, rail_size, 0.12, 1.20, f"{name}_{side_index}_top_rail", "BrassRail")
            add_facade_detail(
                f"{name}_{side_index}",
                "public_approach_handrail",
                (rail_center[0], rail_center[1], 1.26),
                {"orientation": orientation},
            )

    def add_facade_recess_panel(
        prefix: str,
        orientation: str,
        fixed: float,
        values: list[float],
        z_levels: list[float],
        width: float,
        height: float,
    ) -> None:
        face_offset = 0.34 if fixed >= 0.0 else -0.34
        for level_index, z in enumerate(z_levels, start=1):
            for value_index, value in enumerate(values, start=1):
                if orientation == "east_west":
                    center = (fixed + face_offset, value)
                    panel_size = (0.055, width)
                    trim_size_vertical = (0.08, 0.070)
                    trim_size_horizontal = (0.08, width + 0.32)
                    left_center = (center[0], value - width / 2.0)
                    right_center = (center[0], value + width / 2.0)
                    top_center = (center[0], value)
                    bottom_center = (center[0], value)
                else:
                    center = (value, fixed + face_offset)
                    panel_size = (width, 0.055)
                    trim_size_vertical = (0.070, 0.08)
                    trim_size_horizontal = (width + 0.32, 0.08)
                    left_center = (value - width / 2.0, center[1])
                    right_center = (value + width / 2.0, center[1])
                    top_center = (value, center[1])
                    bottom_center = (value, center[1])
                name = f"{prefix}_facade_recess_l{level_index:02d}_{value_index:02d}"
                obj.add_box(center, panel_size, height, z, f"{name}_dark_backing", "DoorMetal")
                obj.add_box(left_center, trim_size_vertical, height + 0.30, z - 0.12, f"{name}_left_return", "ColumnStone")
                obj.add_box(right_center, trim_size_vertical, height + 0.30, z - 0.12, f"{name}_right_return", "ColumnStone")
                obj.add_box(top_center, trim_size_horizontal, 0.12, z + height + 0.05, f"{name}_top_lintel", "ColumnStone")
                obj.add_box(bottom_center, trim_size_horizontal, 0.10, z - 0.12, f"{name}_sill", "ColumnStone")
                add_facade_detail(
                    name,
                    "facade_recess_shadow_panel",
                    (center[0], center[1], z + height / 2.0),
                    {"orientation": orientation, "width_m": round(width, 3), "height_m": round(height, 3)},
                )

    def add_arcade_shadow_bays(
        prefix: str,
        orientation: str,
        fixed: float,
        values: list[float],
        z_base: float,
        height: float,
        width: float,
    ) -> None:
        face_offset = 0.42 if fixed >= 0.0 else -0.42
        for idx, value in enumerate(values, start=1):
            if orientation == "east_west":
                center = (fixed + face_offset, value)
                panel_size = (0.08, width)
                impost_size = (0.11, width + 0.34)
                keystone_center = (center[0], value)
                keystone_size = (0.16, 0.26)
            else:
                center = (value, fixed + face_offset)
                panel_size = (width, 0.08)
                impost_size = (width + 0.34, 0.11)
                keystone_center = (value, center[1])
                keystone_size = (0.26, 0.16)
            name = f"{prefix}_arcade_shadow_bay_{idx:02d}"
            obj.add_box(center, panel_size, height, z_base, f"{name}_dark_recess", "DoorMetal")
            obj.add_box(center, impost_size, 0.18, z_base + height * 0.82, f"{name}_impost_band", "ColumnStone")
            obj.add_box(keystone_center, keystone_size, 0.42, z_base + height * 0.82, f"{name}_keystone", "ColumnStone")
            add_facade_detail(
                name,
                "facade_arcade_shadow_bay",
                (center[0], center[1], z_base + height / 2.0),
                {"orientation": orientation, "width_m": round(width, 3), "height_m": round(height, 3)},
            )

    def add_portico_soffit_coffers(
        prefix: str,
        orientation: str,
        center: tuple[float, float],
        span_values: list[float],
        depth_values: list[float],
        z: float,
    ) -> None:
        cx, cy = center
        for row_index, depth_offset in enumerate(depth_values, start=1):
            for col_index, span_offset in enumerate(span_values, start=1):
                if orientation == "east_west":
                    coffer_center = (cx + depth_offset, cy + span_offset)
                    panel_size = (0.95, 2.6)
                else:
                    coffer_center = (cx + span_offset, cy + depth_offset)
                    panel_size = (2.6, 0.95)
                name = f"{prefix}_soffit_coffer_r{row_index:02d}_c{col_index:02d}"
                obj.add_box(coffer_center, panel_size, 0.055, z, f"{name}_recessed_panel", "RotundaWall")
                obj.add_box(coffer_center, (panel_size[0] * 0.76, panel_size[1] * 0.76), 0.040, z - 0.018, f"{name}_inner_shadow", "StepStone")
                add_facade_detail(
                    name,
                    "portico_soffit_coffer",
                    (coffer_center[0], coffer_center[1], z + 0.028),
                    {"orientation": orientation, "size_m": [round(panel_size[0], 3), round(panel_size[1], 3)]},
                )

    def add_terrace_retaining_wall(
        name: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
        height: float,
        orientation: str,
    ) -> None:
        obj.add_box(center, size, height, z, name, "StepStone")
        cap_size = (size[0] + 0.18, size[1] + 0.18)
        obj.add_box(center, cap_size, 0.10, z + height, f"{name}_stone_cap", "ColumnStone")
        add_facade_detail(
            name,
            "terrace_retaining_wall",
            (center[0], center[1], z + height / 2.0),
            {"orientation": orientation, "size_m": [round(size[0], 3), round(size[1], 3)]},
        )

    def add_terrace_stair_riser_band(
        name: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
        height: float,
        orientation: str,
    ) -> None:
        obj.add_box(center, size, height, z, name, "StepStone")
        add_facade_detail(
            name,
            "terrace_stair_riser_band",
            (center[0], center[1], z + height / 2.0),
            {"orientation": orientation, "width_m": round(max(size), 3)},
        )

    def add_public_terrace_landing_slab(
        name: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
        orientation: str,
    ) -> None:
        obj.add_box(center, size, 0.10, z, name, "PlazaStone")
        obj.add_box(center, (size[0] * 0.96, size[1] * 0.96), 0.035, z + 0.10, f"{name}_edge_shadow_reveal", "StepStone")
        add_facade_detail(
            name,
            "public_terrace_landing_slab",
            (center[0], center[1], z + 0.05),
            {"orientation": orientation, "size_m": [round(size[0], 3), round(size[1], 3)]},
        )

    def add_pediment_relief_cluster(
        prefix: str,
        orientation: str,
        center: tuple[float, float],
        width: float,
        z: float,
        count: int,
    ) -> None:
        cx, cy = center
        denominator = max(1.0, (count - 1) / 2.0)
        for idx in range(count):
            normalized = (idx - (count - 1) / 2.0) / denominator
            lift = (1.0 - abs(normalized)) * 0.36
            relief_height = 0.24 + (idx % 3) * 0.055
            if orientation == "east_west":
                detail_center = (cx, cy + normalized * width * 0.31)
                detail_size = (0.16, 0.42)
            else:
                detail_center = (cx + normalized * width * 0.31, cy)
                detail_size = (0.42, 0.16)
            name = f"{prefix}_pediment_relief_block_{idx+1:02d}"
            obj.add_box(detail_center, detail_size, relief_height, z + lift, name, "ColumnStone")
            rosette_size = (0.115, 0.115) if orientation == "east_west" else (0.115, 0.115)
            garland_offset = 0.22 if normalized <= 0.0 else -0.22
            garland_center = (
                (detail_center[0], detail_center[1] + garland_offset)
                if orientation == "east_west"
                else (detail_center[0] + garland_offset, detail_center[1])
            )
            garland_size = (0.075, 0.34) if orientation == "east_west" else (0.34, 0.075)
            obj.add_box(detail_center, rosette_size, 0.050, z + lift + relief_height + 0.020, f"{name}_rosette", "ColumnStone")
            obj.add_box(garland_center, garland_size, 0.044, z + lift + relief_height * 0.56, f"{name}_garland", "ColumnStone")
            add_facade_detail(
                name,
                "pediment_sculptural_relief_block",
                (detail_center[0], detail_center[1], z + lift + relief_height / 2.0),
                {"orientation": orientation, "public_accuracy": "generic_public_visual_relief"},
            )
            add_facade_detail(
                f"{name}_rosette",
                "pediment_rosette_relief_detail",
                (detail_center[0], detail_center[1], z + lift + relief_height + 0.045),
                {"orientation": orientation, "public_accuracy": "generic_public_visual_relief"},
            )
            add_facade_detail(
                f"{name}_garland",
                "pediment_garland_relief_detail",
                (garland_center[0], garland_center[1], z + lift + relief_height * 0.56 + 0.022),
                {"orientation": orientation, "public_accuracy": "generic_public_visual_relief"},
            )

    def add_facade_corner_quoin_stack(
        prefix: str,
        corners: list[tuple[float, float]],
        z_base: float,
        z_top: float,
        block_size: float,
        block_count: int,
    ) -> None:
        spacing = (z_top - z_base) / block_count
        block_height = min(0.58, spacing * 0.46)
        for corner_index, (x, y) in enumerate(corners, start=1):
            for block_index in range(block_count):
                z = z_base + block_index * spacing + spacing * 0.18
                offset = 0.08 if block_index % 2 == 0 else -0.08
                center = (x + math.copysign(offset, x or 1.0), y + math.copysign(offset, y or 1.0))
                name = f"{prefix}_corner_{corner_index:02d}_quoin_{block_index+1:02d}"
                obj.add_box(center, (block_size, block_size), block_height, z, name, "ColumnStone")
                add_facade_detail(
                    name,
                    "facade_corner_quoin_block",
                    (center[0], center[1], z + block_height / 2.0),
                    {"block_size_m": round(block_size, 3), "public_accuracy": "generic_public_facade_depth"},
                )

    def add_portico_entablature_layers(
        prefix: str,
        orientation: str,
        center: tuple[float, float],
        span: float,
        z: float,
    ) -> None:
        cx, cy = center
        layer_specs = [
            ("architrave", "portico_architrave_band", 0.00, 0.24, 0.46, span * 0.98),
            ("frieze", "portico_frieze_band", 0.36, 0.34, 0.38, span * 0.92),
            ("projecting_cornice", "portico_cornice_band", 0.86, 0.24, 0.70, span + 1.4),
        ]
        for label, kind, z_offset, height, depth, layer_span in layer_specs:
            if orientation == "east_west":
                size = (depth, layer_span)
            else:
                size = (layer_span, depth)
            name = f"{prefix}_{label}"
            obj.add_box(center, size, height, z + z_offset, name, "ColumnStone")
            add_facade_detail(
                name,
                kind,
                (cx, cy, z + z_offset + height / 2.0),
                {"orientation": orientation, "span_m": round(layer_span, 3)},
            )

        panel_count = 10 if span >= 55.0 else 8
        panel_spacing = span * 0.82 / max(1, panel_count - 1)
        for panel_index in range(panel_count):
            offset = -span * 0.41 + panel_index * panel_spacing
            if orientation == "east_west":
                panel_center = (cx, cy + offset)
                panel_size = (0.10, max(1.28, span / panel_count * 0.34))
            else:
                panel_center = (cx + offset, cy)
                panel_size = (max(1.28, span / panel_count * 0.34), 0.10)
            name = f"{prefix}_frieze_panel_detail_{panel_index + 1:02d}"
            obj.add_box(panel_center, panel_size, 0.13, z + 0.48, name, "StepStone")
            add_facade_detail(
                name,
                "portico_frieze_panel_detail",
                (panel_center[0], panel_center[1], z + 0.545),
                {"orientation": orientation, "public_accuracy": "generic_public_frieze_paneling"},
            )

    def add_portico_intercolumn_shadows(
        prefix: str,
        orientation: str,
        fixed: float,
        values: list[float],
        z: float,
        height: float,
    ) -> None:
        for bay_index, (a, b) in enumerate(zip(values, values[1:]), start=1):
            bay_width = abs(b - a)
            value = (a + b) / 2.0
            if orientation == "east_west":
                center = (fixed, value)
                size = (0.08, bay_width * 0.62)
            else:
                center = (value, fixed)
                size = (bay_width * 0.62, 0.08)
            name = f"{prefix}_intercolumn_shadow_{bay_index:02d}"
            obj.add_box(center, size, height, z, name, "DoorMetal")
            add_facade_detail(
                name,
                "portico_intercolumn_shadow",
                (center[0], center[1], z + height / 2.0),
                {"orientation": orientation, "bay_width_m": round(bay_width, 3)},
            )

    def add_pediment_raking_cornice(
        prefix: str,
        orientation: str,
        center: tuple[float, float],
        width: float,
        z: float,
        height: float,
    ) -> None:
        cx, cy = center
        segments = 5
        segment_span = width / (segments * 2.25)
        for side_sign in (-1.0, 1.0):
            for segment_index in range(segments):
                t = (segment_index + 0.5) / segments
                lateral = side_sign * (width / 2.0) * t
                block_z = z + height * (1.0 - t) + 0.08
                if orientation == "east_west":
                    block_center = (cx, cy + lateral)
                    size = (0.55, segment_span)
                else:
                    block_center = (cx + lateral, cy)
                    size = (segment_span, 0.55)
                name = f"{prefix}_raking_cornice_{'left' if side_sign < 0 else 'right'}_{segment_index+1:02d}"
                obj.add_box(block_center, size, 0.16, block_z, name, "ColumnStone")
                add_facade_detail(
                    name,
                    "pediment_raking_cornice_block",
                    (block_center[0], block_center[1], block_z + 0.08),
                    {"orientation": orientation, "stepped_visual": True},
                )

    def add_portico_side_cornice_returns(
        prefix: str,
        orientation: str,
        center: tuple[float, float],
        half_span: float,
        return_depth: float,
        z: float,
    ) -> None:
        cx, cy = center
        for side_index, side_sign in enumerate((-1.0, 1.0), start=1):
            if orientation == "east_west":
                return_center = (cx, cy + side_sign * half_span)
                size = (return_depth, 0.34)
            else:
                return_center = (cx + side_sign * half_span, cy)
                size = (0.34, return_depth)
            name = f"{prefix}_side_cornice_return_{side_index}"
            obj.add_box(return_center, size, 0.28, z, name, "ColumnStone")
            add_facade_detail(
                name,
                "portico_side_cornice_return",
                (return_center[0], return_center[1], z + 0.14),
                {"orientation": orientation, "return_depth_m": round(return_depth, 3)},
            )

    obj.add_box((0.0, 0.0), (430.0, 360.0), 0.08, -0.06, "capitol_campus_ground_plane", "GroundGrass")
    obj.add_box((0.0, 0.0), (185.0, 165.0), 0.10, 0.0, "capitol_plaza_walkable_stone_plane", "PlazaStone")
    add_public_plaza_surface_details()

    # Public visual massing: layered wings, pavilions, porticos, roof caps,
    # columns, dome, and lantern. Dimensions are approximate for visual
    # orientation rather than survey-grade modeling.
    add_beveled_massing("capitol_continuous_raised_plinth", (0.0, 0.0), (154.0, 188.0), 1.05, 0.08, "StepStone", bevel=1.10)
    add_beveled_massing("capitol_central_body_lower", (0.0, 0.0), (78.0, 58.0), 12.4, 1.13, "CapitolStone", bevel=0.82)
    add_beveled_massing("capitol_central_body_upper_setback", (0.0, 0.0), (62.0, 44.0), 4.2, 13.53, "CapitolStone", bevel=0.64)
    add_roof_cap("central_body_roof", (0.0, 0.0), (82.0, 62.0), 17.73)

    for args in [
        ("west_front_upper_terrace_retaining_wall", (-87.2, 0.0), (0.58, 154.0), 0.18, 1.08, "north_south"),
        ("east_front_upper_terrace_retaining_wall", (87.2, 0.0), (0.58, 154.0), 0.18, 1.08, "north_south"),
        ("north_terrace_retaining_wall", (0.0, 109.2), (154.0, 0.58), 0.18, 1.08, "east_west"),
        ("south_terrace_retaining_wall", (0.0, -109.2), (154.0, 0.58), 0.18, 1.08, "east_west"),
        ("central_north_plinth_retaining_wall", (0.0, 31.8), (82.0, 0.42), 1.06, 0.62, "east_west"),
        ("central_south_plinth_retaining_wall", (0.0, -31.8), (82.0, 0.42), 1.06, 0.62, "east_west"),
        ("central_east_plinth_retaining_wall", (41.8, 0.0), (0.42, 62.0), 1.06, 0.62, "north_south"),
        ("central_west_plinth_retaining_wall", (-41.8, 0.0), (0.42, 62.0), 1.06, 0.62, "north_south"),
    ]:
        add_terrace_retaining_wall(*args)

    for wing_name, y, width, depth in (("senate_north_wing", 68.0, 82.0, 58.0), ("house_south_wing", -68.0, 90.0, 62.0)):
        add_beveled_massing(f"{wing_name}_main_block", (0.0, y), (width, depth), 10.9, 1.13, "CapitolStone", bevel=0.72)
        add_beveled_massing(f"{wing_name}_west_end_pavilion", (-34.0, y), (16.0, depth + 4.0), 13.2, 1.13, "CapitolStone", bevel=0.46)
        add_beveled_massing(f"{wing_name}_east_end_pavilion", (34.0, y), (16.0, depth + 4.0), 13.2, 1.13, "CapitolStone", bevel=0.46)
        add_beveled_massing(f"{wing_name}_center_pavilion", (0.0, y), (26.0, depth + 8.0), 12.4, 1.13, "CapitolStone", bevel=0.54)
        add_roof_cap(f"{wing_name}_main_roof", (0.0, y), (width + 2.0, depth + 2.0), 12.05)
        add_roof_cap(f"{wing_name}_center_pavilion_roof", (0.0, y), (28.0, depth + 10.0), 13.55)
        add_facade_detail(f"{wing_name}_articulated_pavilions", "wing_pavilion_massing", (0.0, y, 7.2))

    add_facade_corner_quoin_stack(
        "central_lower_body",
        [(-39.4, -29.4), (-39.4, 29.4), (39.4, -29.4), (39.4, 29.4)],
        1.25,
        13.15,
        0.86,
        8,
    )
    add_facade_corner_quoin_stack(
        "central_upper_setback",
        [(-31.4, -22.4), (-31.4, 22.4), (31.4, -22.4), (31.4, 22.4)],
        13.70,
        17.55,
        0.72,
        3,
    )
    for wing_name, y, width, depth in (("senate_north_wing", 68.0, 82.0, 58.0), ("house_south_wing", -68.0, 90.0, 62.0)):
        half_width = width / 2.0
        half_depth = depth / 2.0
        add_facade_corner_quoin_stack(
            wing_name,
            [(-half_width, y - half_depth), (-half_width, y + half_depth), (half_width, y - half_depth), (half_width, y + half_depth)],
            1.25,
            12.0,
            0.78,
            7,
        )

    stepped_pavilion_specs = [
        ("central_northeast_hyphen_stepped_pavilion", (34.5, 36.5), (14.5, 12.0), 1.13, 11.4),
        ("central_northwest_hyphen_stepped_pavilion", (-34.5, 36.5), (14.5, 12.0), 1.13, 11.4),
        ("central_southeast_hyphen_stepped_pavilion", (34.5, -36.5), (14.5, 12.0), 1.13, 11.4),
        ("central_southwest_hyphen_stepped_pavilion", (-34.5, -36.5), (14.5, 12.0), 1.13, 11.4),
        ("senate_northeast_corner_stepped_pavilion", (41.8, 92.5), (11.5, 12.0), 1.13, 10.6),
        ("senate_northwest_corner_stepped_pavilion", (-41.8, 92.5), (11.5, 12.0), 1.13, 10.6),
        ("senate_southeast_inner_stepped_pavilion", (41.8, 43.5), (11.5, 10.0), 1.13, 10.2),
        ("senate_southwest_inner_stepped_pavilion", (-41.8, 43.5), (11.5, 10.0), 1.13, 10.2),
        ("house_southeast_corner_stepped_pavilion", (44.8, -93.5), (12.0, 12.0), 1.13, 10.6),
        ("house_southwest_corner_stepped_pavilion", (-44.8, -93.5), (12.0, 12.0), 1.13, 10.6),
        ("house_northeast_inner_stepped_pavilion", (44.8, -42.5), (12.0, 10.0), 1.13, 10.2),
        ("house_northwest_inner_stepped_pavilion", (-44.8, -42.5), (12.0, 10.0), 1.13, 10.2),
    ]
    for name, center, size, z, height in stepped_pavilion_specs:
        add_stepped_pavilion_massing(name, center, size, z, height)

    shadow_return_specs = [
        ("central_east_north_recess_shadow_return", "east_west", 42.4, 35.5, 13.5, 1.55, 10.0),
        ("central_west_north_recess_shadow_return", "east_west", -42.4, 35.5, 13.5, 1.55, 10.0),
        ("central_east_south_recess_shadow_return", "east_west", 42.4, -35.5, 13.5, 1.55, 10.0),
        ("central_west_south_recess_shadow_return", "east_west", -42.4, -35.5, 13.5, 1.55, 10.0),
        ("senate_northwest_court_shadow_return", "north_south", 98.7, -31.0, 14.5, 1.42, 8.6),
        ("senate_northeast_court_shadow_return", "north_south", 98.7, 31.0, 14.5, 1.42, 8.6),
        ("senate_southwest_court_shadow_return", "north_south", 39.2, -31.0, 14.5, 1.42, 8.6),
        ("senate_southeast_court_shadow_return", "north_south", 39.2, 31.0, 14.5, 1.42, 8.6),
        ("house_southwest_court_shadow_return", "north_south", -99.7, -33.5, 15.5, 1.42, 8.6),
        ("house_southeast_court_shadow_return", "north_south", -99.7, 33.5, 15.5, 1.42, 8.6),
        ("house_northwest_court_shadow_return", "north_south", -38.2, -33.5, 15.5, 1.42, 8.6),
        ("house_northeast_court_shadow_return", "north_south", -38.2, 33.5, 15.5, 1.42, 8.6),
    ]
    for args in shadow_return_specs:
        add_facade_shadow_return(*args)

    water_table_specs = [
        ("central_east_water_table", "east_west", 39.4, 0.0, 58.0),
        ("central_west_water_table", "east_west", -39.4, 0.0, 58.0),
        ("central_north_water_table", "north_south", 29.8, 0.0, 78.0),
        ("central_south_water_table", "north_south", -29.8, 0.0, 78.0),
        ("east_front_portico_water_table", "east_west", 67.5, 0.0, 68.0),
        ("west_front_portico_water_table", "east_west", -67.5, 0.0, 68.0),
        ("senate_north_front_water_table", "north_south", 102.2, 0.0, 84.0),
        ("house_south_front_water_table", "north_south", -102.2, 0.0, 88.0),
        ("senate_inner_south_water_table", "north_south", 38.6, 0.0, 70.0),
        ("house_inner_north_water_table", "north_south", -37.6, 0.0, 74.0),
    ]
    for args in water_table_specs:
        add_facade_water_table(*args)

    cornice_shadow_specs = [
        ("central_east_cornice_shadow_reveal", "east_west", 39.45, 0.0, 58.0, 15.38),
        ("central_west_cornice_shadow_reveal", "east_west", -39.45, 0.0, 58.0, 15.38),
        ("central_north_cornice_shadow_reveal", "north_south", 29.95, 0.0, 78.0, 15.38),
        ("central_south_cornice_shadow_reveal", "north_south", -29.95, 0.0, 78.0, 15.38),
        ("east_front_portico_cornice_shadow_reveal", "east_west", 67.72, 0.0, 68.0, 13.86),
        ("west_front_portico_cornice_shadow_reveal", "east_west", -67.72, 0.0, 68.0, 13.86),
        ("senate_north_front_cornice_shadow_reveal", "north_south", 102.28, 0.0, 84.0, 12.44),
        ("house_south_front_cornice_shadow_reveal", "north_south", -102.28, 0.0, 88.0, 12.44),
        ("senate_inner_south_cornice_shadow_reveal", "north_south", 38.72, 0.0, 70.0, 12.12),
        ("house_inner_north_cornice_shadow_reveal", "north_south", -37.72, 0.0, 74.0, 12.12),
    ]
    for args in cornice_shadow_specs:
        add_cornice_shadow_reveal(*args)

    attic_window_specs = [
        ("central_east", "east_west", 39.30, [-24.0, -16.0, -8.0, 0.0, 8.0, 16.0, 24.0], 16.13),
        ("central_west", "east_west", -39.30, [-24.0, -16.0, -8.0, 0.0, 8.0, 16.0, 24.0], 16.13),
        ("central_north", "north_south", 29.80, [-30.0, -20.0, -10.0, 0.0, 10.0, 20.0, 30.0], 16.13),
        ("central_south", "north_south", -29.80, [-30.0, -20.0, -10.0, 0.0, 10.0, 20.0, 30.0], 16.13),
        ("east_front_portico", "east_west", 67.35, [-28.0, -20.0, -12.0, -4.0, 4.0, 12.0, 20.0, 28.0], 12.68),
        ("west_front_portico", "east_west", -67.35, [-28.0, -20.0, -12.0, -4.0, 4.0, 12.0, 20.0, 28.0], 12.68),
        ("senate_north_front", "north_south", 101.85, [-36.0, -27.0, -18.0, -9.0, 0.0, 9.0, 18.0, 27.0, 36.0], 11.30),
        ("house_south_front", "north_south", -101.85, [-36.0, -27.0, -18.0, -9.0, 0.0, 9.0, 18.0, 27.0, 36.0], 11.30),
        ("senate_inner_south", "north_south", 38.70, [-30.0, -20.0, -10.0, 0.0, 10.0, 20.0, 30.0], 11.05),
        ("house_inner_north", "north_south", -37.70, [-30.0, -20.0, -10.0, 0.0, 10.0, 20.0, 30.0], 11.05),
    ]
    for prefix, orientation, fixed, values, z in attic_window_specs:
        add_attic_window_band(f"{prefix}_upper_attic", orientation, fixed, values, z)

    roof_articulation_specs = [
        ("central_roof_north_pavilion_riser", (0.0, 24.0), (48.0, 8.5), 18.06, 0.72),
        ("central_roof_south_pavilion_riser", (0.0, -24.0), (48.0, 8.5), 18.06, 0.72),
        ("central_roof_east_gallery_riser", (31.0, 0.0), (8.5, 48.0), 18.02, 0.66),
        ("central_roof_west_gallery_riser", (-31.0, 0.0), (8.5, 48.0), 18.02, 0.66),
        ("senate_roof_north_bar", (0.0, 88.8), (58.0, 6.4), 13.18, 0.58),
        ("senate_roof_south_inner_bar", (0.0, 47.2), (58.0, 5.6), 12.76, 0.50),
        ("house_roof_south_bar", (0.0, -90.0), (62.0, 6.4), 13.18, 0.58),
        ("house_roof_north_inner_bar", (0.0, -47.0), (62.0, 5.6), 12.76, 0.50),
        ("east_front_roof_layered_return", (57.2, 0.0), (7.8, 58.0), 14.52, 0.58),
        ("west_front_roof_layered_return", (-57.2, 0.0), (7.8, 58.0), 14.52, 0.58),
    ]
    for name, center, size, z, height in roof_articulation_specs:
        add_roof_articulation_volume(name, center, size, z, height)

    wing_transition_specs = [
        ("northwest_central_wing_transition_block", (-31.0, 40.5), (15.0, 13.5), 12.92, 1.15),
        ("northeast_central_wing_transition_block", (31.0, 40.5), (15.0, 13.5), 12.92, 1.15),
        ("southwest_central_wing_transition_block", (-31.0, -40.5), (15.0, 13.5), 12.92, 1.15),
        ("southeast_central_wing_transition_block", (31.0, -40.5), (15.0, 13.5), 12.92, 1.15),
        ("north_east_front_transition_block", (48.0, 40.0), (9.5, 16.0), 13.65, 0.95),
        ("south_east_front_transition_block", (48.0, -40.0), (9.5, 16.0), 13.65, 0.95),
        ("north_west_front_transition_block", (-48.0, 40.0), (9.5, 16.0), 13.65, 0.95),
        ("south_west_front_transition_block", (-48.0, -40.0), (9.5, 16.0), 13.65, 0.95),
    ]
    for name, center, size, z, height in wing_transition_specs:
        add_roof_articulation_volume(name, center, size, z, height, kind="wing_transition_block")

    courtyard_shadow_specs = [
        ("northwest_inner_courtyard_shadow", (-47.0, 43.0), (11.0, 15.0), 12.34),
        ("northeast_inner_courtyard_shadow", (47.0, 43.0), (11.0, 15.0), 12.34),
        ("southwest_inner_courtyard_shadow", (-47.0, -43.0), (11.0, 15.0), 12.34),
        ("southeast_inner_courtyard_shadow", (47.0, -43.0), (11.0, 15.0), 12.34),
        ("senate_west_roof_recess_shadow", (-24.0, 68.0), (11.5, 24.0), 13.18),
        ("senate_east_roof_recess_shadow", (24.0, 68.0), (11.5, 24.0), 13.18),
        ("house_west_roof_recess_shadow", (-26.0, -68.0), (12.0, 26.0), 13.18),
        ("house_east_roof_recess_shadow", (26.0, -68.0), (12.0, 26.0), 13.18),
    ]
    for name, center, size, z in courtyard_shadow_specs:
        add_courtyard_notch_shadow(name, center, size, z)

    for side, x in (("east", 42.0), ("west", -42.0)):
        for idx, y in enumerate([-27.0, -19.0, -11.0, -3.0, 5.0, 13.0, 21.0, 29.0], start=1):
            add_roof_dormer(f"{side}_central_roof_dormer_{idx:02d}", (x, y), 18.52, "east_west")
    for side, y in (("north", 83.8), ("south", -83.8)):
        for idx, x in enumerate([-35.0, -25.0, -15.0, -5.0, 5.0, 15.0, 25.0, 35.0], start=1):
            add_roof_dormer(f"{side}_wing_roof_dormer_{idx:02d}", (x, y), 13.68, "north_south")

    skylight_specs = [
        ("central_north_roof_skylight_strip", (0.0, 18.2), (24.0, 1.05), 18.94),
        ("central_south_roof_skylight_strip", (0.0, -18.2), (24.0, 1.05), 18.94),
        ("senate_west_roof_skylight_strip", (-25.0, 78.0), (14.0, 1.0), 14.02),
        ("senate_east_roof_skylight_strip", (25.0, 78.0), (14.0, 1.0), 14.02),
        ("house_west_roof_skylight_strip", (-27.0, -78.0), (14.0, 1.0), 14.02),
        ("house_east_roof_skylight_strip", (27.0, -78.0), (14.0, 1.0), 14.02),
        ("east_front_roof_skylight_strip", (56.0, 18.0), (1.0, 18.0), 15.18),
        ("west_front_roof_skylight_strip", (-56.0, -18.0), (1.0, 18.0), 15.18),
    ]
    for name, center, size, z in skylight_specs:
        add_roof_skylight_strip(name, center, size, z)

    roof_monitor_specs = [
        ("central_north_roof_monitor_ridge", (0.0, 24.4), (32.0, 2.1), 18.98, "east_west"),
        ("central_south_roof_monitor_ridge", (0.0, -24.4), (32.0, 2.1), 18.98, "east_west"),
        ("central_east_roof_monitor_ridge", (31.5, 0.0), (2.1, 32.0), 18.95, "north_south"),
        ("central_west_roof_monitor_ridge", (-31.5, 0.0), (2.1, 32.0), 18.95, "north_south"),
        ("senate_center_pavilion_roof_monitor_ridge", (0.0, 68.0), (18.5, 2.0), 14.58, "east_west"),
        ("house_center_pavilion_roof_monitor_ridge", (0.0, -68.0), (19.5, 2.0), 14.58, "east_west"),
        ("east_front_portico_roof_monitor_ridge", (58.5, 0.0), (2.0, 42.0), 15.30, "north_south"),
        ("west_front_portico_roof_monitor_ridge", (-58.5, 0.0), (2.0, 42.0), 15.30, "north_south"),
    ]
    for name, center, size, z, orientation in roof_monitor_specs:
        add_roof_monitor_ridge(name, center, size, z, orientation)

    add_element("Articulated public roof silhouette and courtyard recesses", "landmark", (0.0, 0.0, 18.5))

    for side, x in (("east", 58.5), ("west", -58.5)):
        face_sign = 1.0 if x > 0.0 else -1.0
        add_beveled_massing(f"{side}_front_projecting_portico_block", (x, 0.0), (17.0, 68.0), 13.7, 1.13, "CapitolStone", bevel=0.42)
        add_beveled_massing(f"{side}_front_entablature", (x, 0.0), (20.0, 72.0), 0.55, 14.83, "ColumnStone", bevel=0.36)
        add_facade_corner_quoin_stack(
            f"{side}_front_portico",
            [(x - 8.5, -34.0), (x - 8.5, 34.0), (x + 8.5, -34.0), (x + 8.5, 34.0)],
            1.25,
            14.30,
            0.76,
            7,
        )
        add_portico_entablature_layers(f"{side}_front_portico", "east_west", (x + face_sign * 4.75, 0.0), 58.0, 13.35)
        obj.add_pediment((x + (2.2 if x > 0 else -2.2), 0.0), 56.0, 4.4, 15.38, 4.2, f"{side}_front_triangular_pediment", "ColumnStone", "east_west")
        add_pediment_raking_cornice(f"{side}_front_pediment", "east_west", (x + face_sign * 4.55, 0.0), 56.0, 15.38, 4.2)
        add_portico_side_cornice_returns(f"{side}_front_portico", "east_west", (x, 0.0), 36.0, 18.0, 14.72)
        obj.add_box((x + (2.7 if x > 0 else -2.7), 0.0), (0.18, 12.0), 0.42, 16.25, f"{side}_front_pediment_public_relief_panel", "ColumnStone")
        add_pediment_relief_cluster(f"{side}_front", "east_west", (x + face_sign * 4.55, 0.0), 56.0, 15.95, 9)
        add_roof_cap(f"{side}_front_portico_roof", (x, 0.0), (20.5, 70.0), 13.95)
        add_portico_soffit_coffers(
            f"{side}_front_portico",
            "east_west",
            (x, 0.0),
            [-24.0, -16.0, -8.0, 0.0, 8.0, 16.0, 24.0],
            [-4.2, 0.0, 4.2],
            13.62,
        )
        add_facade_detail(f"{side}_front_triangular_pediment", "classical_pediment", (x, 0.0, 17.1))
        add_facade_detail(f"{side}_front_pediment_public_relief_panel", "pediment_relief_panel", (x, 0.0, 16.46))

    for side, y in (("north", 99.0), ("south", -99.0)):
        face_sign = 1.0 if y > 0.0 else -1.0
        add_beveled_massing(f"{side}_wing_public_portico_block", (0.0, y), (50.0, 13.0), 11.8, 1.13, "CapitolStone", bevel=0.38)
        add_beveled_massing(f"{side}_wing_entablature", (0.0, y), (54.0, 15.5), 0.48, 13.15, "ColumnStone", bevel=0.32)
        add_facade_corner_quoin_stack(
            f"{side}_wing_portico",
            [(-25.0, y - 6.5), (-25.0, y + 6.5), (25.0, y - 6.5), (25.0, y + 6.5)],
            1.25,
            12.70,
            0.74,
            6,
        )
        add_portico_entablature_layers(f"{side}_wing_portico", "north_south", (0.0, y + face_sign * 4.05), 46.0, 12.60)
        obj.add_pediment((0.0, y + (2.0 if y > 0 else -2.0)), 44.0, 4.0, 13.63, 3.3, f"{side}_wing_triangular_pediment", "ColumnStone", "north_south")
        add_pediment_raking_cornice(f"{side}_wing_pediment", "north_south", (0.0, y + face_sign * 4.15), 44.0, 13.63, 3.3)
        add_portico_side_cornice_returns(f"{side}_wing_portico", "north_south", (0.0, y), 27.0, 13.5, 13.08)
        obj.add_box((0.0, y + (2.4 if y > 0 else -2.4)), (10.0, 0.18), 0.38, 14.52, f"{side}_wing_pediment_public_relief_panel", "ColumnStone")
        add_pediment_relief_cluster(f"{side}_wing", "north_south", (0.0, y + face_sign * 4.15), 44.0, 14.10, 7)
        add_portico_soffit_coffers(
            f"{side}_wing_portico",
            "north_south",
            (0.0, y),
            [-18.0, -9.0, 0.0, 9.0, 18.0],
            [-3.0, 0.0, 3.0],
            12.92,
        )
        add_facade_detail(f"{side}_wing_triangular_pediment", "classical_pediment", (0.0, y, 15.1))
        add_facade_detail(f"{side}_wing_pediment_public_relief_panel", "pediment_relief_panel", (0.0, y, 14.71))

    roof_joint_specs = [
        ("central_body", (0.0, 0.0), (75.0, 55.0), 18.47, 5, 4),
        ("senate_main", (0.0, 68.0), (78.0, 54.0), 12.79, 5, 4),
        ("house_main", (0.0, -68.0), (86.0, 58.0), 12.79, 5, 4),
        ("senate_center_pavilion", (0.0, 68.0), (24.0, 62.0), 14.29, 2, 5),
        ("house_center_pavilion", (0.0, -68.0), (24.0, 66.0), 14.29, 2, 5),
        ("east_front_portico", (58.5, 0.0), (18.0, 66.0), 14.70, 2, 5),
        ("west_front_portico", (-58.5, 0.0), (18.0, 66.0), 14.70, 2, 5),
    ]
    for name, center, size, z, x_lines, y_lines in roof_joint_specs:
        add_roof_surface_joint_grid(name, center, size, z, x_lines, y_lines)

    roof_edge_detail_specs = [
        ("central_body", (0.0, 0.0), (82.0, 62.0), 18.52, 12, 10),
        ("senate_main_roof", (0.0, 68.0), (84.0, 60.0), 12.98, 12, 8),
        ("house_main_roof", (0.0, -68.0), (92.0, 64.0), 12.98, 12, 8),
        ("senate_center_pavilion_roof", (0.0, 68.0), (28.0, 68.0), 14.42, 5, 9),
        ("house_center_pavilion_roof", (0.0, -68.0), (28.0, 72.0), 14.42, 5, 9),
        ("east_front_portico_roof", (58.5, 0.0), (20.5, 70.0), 14.86, 4, 9),
        ("west_front_portico_roof", (-58.5, 0.0), (20.5, 70.0), 14.86, 4, 9),
    ]
    for name, center, size, z, x_blocks, y_blocks in roof_edge_detail_specs:
        add_roof_edge_realism_details(name, center, size, z, x_blocks, y_blocks)

    roof_vent_specs = [
        ("central_roof_generic_vent_01", (-22.0, -18.0), 18.72),
        ("central_roof_generic_vent_02", (-22.0, 18.0), 18.72),
        ("central_roof_generic_vent_03", (22.0, -18.0), 18.72),
        ("central_roof_generic_vent_04", (22.0, 18.0), 18.72),
        ("senate_main_generic_vent_01", (-31.0, 55.0), 13.18),
        ("senate_main_generic_vent_02", (31.0, 55.0), 13.18),
        ("senate_main_generic_vent_03", (-31.0, 81.0), 13.18),
        ("senate_main_generic_vent_04", (31.0, 81.0), 13.18),
        ("house_main_generic_vent_01", (-34.0, -55.0), 13.18),
        ("house_main_generic_vent_02", (34.0, -55.0), 13.18),
        ("house_main_generic_vent_03", (-34.0, -81.0), 13.18),
        ("house_main_generic_vent_04", (34.0, -81.0), 13.18),
        ("east_front_portico_generic_vent_01", (58.5, -26.0), 15.05),
        ("east_front_portico_generic_vent_02", (58.5, 26.0), 15.05),
        ("west_front_portico_generic_vent_01", (-58.5, -26.0), 15.05),
        ("west_front_portico_generic_vent_02", (-58.5, 26.0), 15.05),
        ("senate_center_pavilion_generic_vent", (0.0, 82.0), 14.62),
        ("house_center_pavilion_generic_vent", (0.0, -82.0), 14.62),
    ]
    for name, center, z in roof_vent_specs:
        add_generic_roof_vent_housing(name, center, z)
    add_element("Generic roof capstones, scuppers, and non-operational vent housings", "landmark", (0.0, 0.0, 19.2))

    # Facade rhythm: public visual windows, belt courses, and cornice bands.
    y_window_positions = [value * 5.0 for value in range(-6, 7)]
    wing_x_window_positions = [value * 5.6 for value in range(-7, 8)]
    add_facade_window_grid("east_front", "east_west", 63.2, y_window_positions, [3.8, 7.2, 10.6, 14.0])
    add_facade_window_grid("west_front", "east_west", -63.2, y_window_positions, [3.8, 7.2, 10.6, 14.0])
    add_facade_window_grid("senate_north_wing", "north_south", 97.2, wing_x_window_positions, [3.7, 7.1, 10.5])
    add_facade_window_grid("house_south_wing", "north_south", -97.2, wing_x_window_positions, [3.7, 7.1, 10.5])
    add_arch_window_trim_grid("east_front_public", "east_west", 63.2, y_window_positions, [3.8, 7.2], 1.34, 1.28)
    add_arch_window_trim_grid("west_front_public", "east_west", -63.2, y_window_positions, [3.8, 7.2], 1.34, 1.28)
    add_arch_window_trim_grid("senate_north_wing_public", "north_south", 97.2, wing_x_window_positions, [3.7, 7.1], 1.34, 1.28)
    add_arch_window_trim_grid("house_south_wing_public", "north_south", -97.2, wing_x_window_positions, [3.7, 7.1], 1.34, 1.28)
    add_window_grid_on_face("east_front_deep_shadow", "east_west", 67.3, [-27, -18, -9, 9, 18, 27], [5.1, 8.5, 11.9], width=1.05)
    add_window_grid_on_face("west_front_deep_shadow", "east_west", -67.3, [-27, -18, -9, 9, 18, 27], [5.1, 8.5, 11.9], width=1.05)
    add_window_grid_on_face("north_portico_shadow", "north_south", 101.8, [-20, -12, -4, 4, 12, 20], [4.9, 8.3, 11.2], width=0.9)
    add_window_grid_on_face("south_portico_shadow", "north_south", -101.8, [-20, -12, -4, 4, 12, 20], [4.9, 8.3, 11.2], width=0.9)
    add_facade_recess_panel("east_front_public_depth", "east_west", 67.45, [-30.0, -22.0, -14.0, -6.0, 6.0, 14.0, 22.0, 30.0], [2.85, 6.20, 9.55], 2.15, 1.95)
    add_facade_recess_panel("west_front_public_depth", "east_west", -67.45, [-30.0, -22.0, -14.0, -6.0, 6.0, 14.0, 22.0, 30.0], [2.85, 6.20, 9.55], 2.15, 1.95)
    add_facade_recess_panel("central_east_public_depth", "east_west", 39.10, [-24.0, -16.0, -8.0, 0.0, 8.0, 16.0, 24.0], [3.10, 6.55, 10.00], 1.75, 1.75)
    add_facade_recess_panel("central_west_public_depth", "east_west", -39.10, [-24.0, -16.0, -8.0, 0.0, 8.0, 16.0, 24.0], [3.10, 6.55, 10.00], 1.75, 1.75)
    add_facade_recess_panel("north_wing_public_depth", "north_south", 101.95, [-36.0, -27.0, -18.0, -9.0, 9.0, 18.0, 27.0, 36.0], [3.05, 6.35, 9.65], 2.05, 1.82)
    add_facade_recess_panel("south_wing_public_depth", "north_south", -101.95, [-36.0, -27.0, -18.0, -9.0, 9.0, 18.0, 27.0, 36.0], [3.05, 6.35, 9.65], 2.05, 1.82)

    ashlar_z_levels = [2.35, 3.55, 4.75, 5.95, 7.15, 8.35, 9.55, 10.75, 11.95]
    front_ashlar_z_levels = [2.25, 3.48, 4.71, 5.94, 7.17, 8.40, 9.63, 10.86, 12.09]
    wing_ashlar_z_levels = [2.20, 3.40, 4.60, 5.80, 7.00, 8.20, 9.40, 10.60]
    add_facade_ashlar_courses("central_east", "east_west", 39.0, 0.0, 57.0, ashlar_z_levels)
    add_facade_ashlar_courses("central_west", "east_west", -39.0, 0.0, 57.0, ashlar_z_levels)
    add_facade_ashlar_courses("central_north", "north_south", 29.4, 0.0, 76.0, ashlar_z_levels)
    add_facade_ashlar_courses("central_south", "north_south", -29.4, 0.0, 76.0, ashlar_z_levels)
    add_facade_ashlar_courses("east_front_portico", "east_west", 67.2, 0.0, 66.0, front_ashlar_z_levels)
    add_facade_ashlar_courses("west_front_portico", "east_west", -67.2, 0.0, 66.0, front_ashlar_z_levels)
    add_facade_ashlar_courses("senate_north_front", "north_south", 101.8, 0.0, 82.0, wing_ashlar_z_levels)
    add_facade_ashlar_courses("house_south_front", "north_south", -101.8, 0.0, 86.0, wing_ashlar_z_levels)

    add_facade_vertical_stone_joints("central_east", "east_west", 39.0, [-24.0, -16.0, -8.0, 0.0, 8.0, 16.0, 24.0], 2.0, 10.9)
    add_facade_vertical_stone_joints("central_west", "east_west", -39.0, [-24.0, -16.0, -8.0, 0.0, 8.0, 16.0, 24.0], 2.0, 10.9)
    add_facade_vertical_stone_joints("central_north", "north_south", 29.4, [-32.0, -24.0, -16.0, -8.0, 0.0, 8.0, 16.0, 24.0, 32.0], 2.0, 10.9)
    add_facade_vertical_stone_joints("central_south", "north_south", -29.4, [-32.0, -24.0, -16.0, -8.0, 0.0, 8.0, 16.0, 24.0, 32.0], 2.0, 10.9)
    add_facade_vertical_stone_joints("east_front_portico", "east_west", 67.2, [-28.0, -20.0, -12.0, -4.0, 4.0, 12.0, 20.0, 28.0], 2.0, 11.8)
    add_facade_vertical_stone_joints("west_front_portico", "east_west", -67.2, [-28.0, -20.0, -12.0, -4.0, 4.0, 12.0, 20.0, 28.0], 2.0, 11.8)
    add_facade_vertical_stone_joints("senate_north_front", "north_south", 101.8, [-36.0, -28.0, -20.0, -12.0, -4.0, 4.0, 12.0, 20.0, 28.0, 36.0], 2.0, 9.7)
    add_facade_vertical_stone_joints("house_south_front", "north_south", -101.8, [-36.0, -28.0, -20.0, -12.0, -4.0, 4.0, 12.0, 20.0, 28.0, 36.0], 2.0, 9.7)

    add_facade_weathering_stains("east_front", "east_west", 67.35, [-27.0, -18.0, -9.0, 0.0, 9.0, 18.0, 27.0], [5.0, 8.4, 11.8], 0.92, 0.86)
    add_facade_weathering_stains("west_front", "east_west", -67.35, [-27.0, -18.0, -9.0, 0.0, 9.0, 18.0, 27.0], [5.0, 8.4, 11.8], 0.92, 0.86)
    add_facade_weathering_stains("senate_north", "north_south", 101.95, [-33.0, -24.0, -15.0, -6.0, 6.0, 15.0, 24.0, 33.0], [4.8, 8.15, 10.95], 0.84, 0.78)
    add_facade_weathering_stains("house_south", "north_south", -101.95, [-33.0, -24.0, -15.0, -6.0, 6.0, 15.0, 24.0, 33.0], [4.8, 8.15, 10.95], 0.84, 0.78)
    add_facade_discoloration_patches("east_front", "east_west", 67.55, [-30.0, -20.0, -10.0, 0.0, 10.0, 20.0, 30.0], [2.70, 5.90, 9.10, 12.30], 1.05, 1.32)
    add_facade_discoloration_patches("west_front", "east_west", -67.55, [-30.0, -20.0, -10.0, 0.0, 10.0, 20.0, 30.0], [2.70, 5.90, 9.10, 12.30], 1.05, 1.32)
    add_facade_discoloration_patches("senate_north", "north_south", 102.05, [-36.0, -24.0, -12.0, 0.0, 12.0, 24.0, 36.0], [2.60, 5.80, 9.00], 0.94, 1.20)
    add_facade_discoloration_patches("house_south", "north_south", -102.05, [-36.0, -24.0, -12.0, 0.0, 12.0, 24.0, 36.0], [2.60, 5.80, 9.00], 0.94, 1.20)
    add_facade_sill_runoff_stains("east_front", "east_west", 63.45, y_window_positions, [3.8, 7.2])
    add_facade_sill_runoff_stains("west_front", "east_west", -63.45, y_window_positions, [3.8, 7.2])
    add_facade_sill_runoff_stains("senate_north_wing", "north_south", 97.45, wing_x_window_positions, [3.7, 7.1])
    add_facade_sill_runoff_stains("house_south_wing", "north_south", -97.45, wing_x_window_positions, [3.7, 7.1])

    base_grime_specs = [
        ("central_east_base_grime", "east_west", 39.72, 0.0, 58.0),
        ("central_west_base_grime", "east_west", -39.72, 0.0, 58.0),
        ("central_north_base_grime", "north_south", 30.12, 0.0, 78.0),
        ("central_south_base_grime", "north_south", -30.12, 0.0, 78.0),
        ("east_front_portico_base_grime", "east_west", 67.82, 0.0, 68.0),
        ("west_front_portico_base_grime", "east_west", -67.82, 0.0, 68.0),
        ("senate_north_front_base_grime", "north_south", 102.55, 0.0, 84.0),
        ("house_south_front_base_grime", "north_south", -102.55, 0.0, 88.0),
        ("senate_inner_south_base_grime", "north_south", 38.92, 0.0, 70.0),
        ("house_inner_north_base_grime", "north_south", -37.92, 0.0, 74.0),
    ]
    for args in base_grime_specs:
        add_facade_base_grime_band(*args)

    close_range_masonry_specs = [
        ("central_east_close_masonry", "east_west", 39.78, 0.0, 57.0, 1.72, 12.55, 12, 7),
        ("central_west_close_masonry", "east_west", -39.78, 0.0, 57.0, 1.72, 12.55, 12, 7),
        ("east_front_portico_close_masonry", "east_west", 67.92, 0.0, 66.0, 1.64, 13.25, 14, 8),
        ("west_front_portico_close_masonry", "east_west", -67.92, 0.0, 66.0, 1.64, 13.25, 14, 8),
        ("senate_north_close_masonry", "north_south", 102.62, 0.0, 82.0, 1.58, 11.65, 16, 7),
        ("house_south_close_masonry", "north_south", -102.62, 0.0, 86.0, 1.58, 11.65, 16, 7),
        ("senate_inner_south_close_masonry", "north_south", 39.02, 0.0, 70.0, 1.56, 10.95, 12, 6),
        ("house_inner_north_close_masonry", "north_south", -38.02, 0.0, 74.0, 1.56, 10.95, 12, 6),
    ]
    for args in close_range_masonry_specs:
        add_close_range_masonry_relief(*args)
        add_close_range_stone_surface_wear(*args)

    front_pilaster_values = [value * 5.0 for value in range(-7, 8)]
    wing_pilaster_values = [value * 5.6 for value in range(-8, 9)]
    add_facade_pilaster_line("east_front_public_rhythm", "east_west", 64.1, front_pilaster_values, 1.2, 12.6)
    add_facade_pilaster_line("west_front_public_rhythm", "east_west", -64.1, front_pilaster_values, 1.2, 12.6)
    add_facade_pilaster_line("senate_north_public_rhythm", "north_south", 98.0, wing_pilaster_values, 1.2, 10.9)
    add_facade_pilaster_line("house_south_public_rhythm", "north_south", -98.0, wing_pilaster_values, 1.2, 10.9)

    front_dentil_values = [value * 4.0 for value in range(-8, 9)]
    wing_dentil_values = [value * 4.0 for value in range(-10, 11)]
    add_dentil_row("east_front_entablature", "east_west", 67.1, front_dentil_values, 14.18)
    add_dentil_row("west_front_entablature", "east_west", -67.1, front_dentil_values, 14.18)
    add_dentil_row("north_wing_entablature", "north_south", 101.6, wing_dentil_values, 12.72)
    add_dentil_row("south_wing_entablature", "north_south", -101.6, wing_dentil_values, 12.72)
    add_dentil_row("central_east_cornice", "east_west", 39.1, [-24, -18, -12, -6, 0, 6, 12, 18, 24], 15.92)
    add_dentil_row("central_west_cornice", "east_west", -39.1, [-24, -18, -12, -6, 0, 6, 12, 18, 24], 15.92)
    add_dentil_row("central_north_cornice", "north_south", 29.8, [-30, -24, -18, -12, -6, 0, 6, 12, 18, 24, 30], 15.92)
    add_dentil_row("central_south_cornice", "north_south", -29.8, [-30, -24, -18, -12, -6, 0, 6, 12, 18, 24, 30], 15.92)
    add_cornice_bracket_row("east_front_entablature", "east_west", 67.1, front_dentil_values, 13.32)
    add_cornice_bracket_row("west_front_entablature", "east_west", -67.1, front_dentil_values, 13.32)
    add_cornice_bracket_row("north_wing_entablature", "north_south", 101.6, wing_dentil_values, 11.86)
    add_cornice_bracket_row("south_wing_entablature", "north_south", -101.6, wing_dentil_values, 11.86)
    add_cornice_bracket_row("central_east_cornice", "east_west", 39.1, [-24, -18, -12, -6, 0, 6, 12, 18, 24], 15.08)
    add_cornice_bracket_row("central_west_cornice", "east_west", -39.1, [-24, -18, -12, -6, 0, 6, 12, 18, 24], 15.08)
    add_cornice_bracket_row("central_north_cornice", "north_south", 29.8, [-30, -24, -18, -12, -6, 0, 6, 12, 18, 24, 30], 15.08)
    add_cornice_bracket_row("central_south_cornice", "north_south", -29.8, [-30, -24, -18, -12, -6, 0, 6, 12, 18, 24, 30], 15.08)

    add_balustrade_line("east_front_roof", "east_west", 68.3, [value * 5.0 for value in range(-7, 8)], 14.38)
    add_balustrade_line("west_front_roof", "east_west", -68.3, [value * 5.0 for value in range(-7, 8)], 14.38)
    add_balustrade_line("central_east_roof", "east_west", 41.6, [value * 5.0 for value in range(-6, 7)], 18.05)
    add_balustrade_line("central_west_roof", "east_west", -41.6, [value * 5.0 for value in range(-6, 7)], 18.05)
    add_balustrade_line("senate_north_roof", "north_south", 100.2, [value * 5.6 for value in range(-8, 9)], 13.12)
    add_balustrade_line("house_south_roof", "north_south", -100.2, [value * 5.6 for value in range(-8, 9)], 13.12)

    for band_index, (z, height) in enumerate([(5.7, 0.18), (9.1, 0.18), (15.55, 0.48)], start=1):
        obj.add_box((0.0, 29.4), (77.0, 0.28), height, z, f"central_north_belt_course_{band_index}", "ColumnStone")
        obj.add_box((0.0, -29.4), (77.0, 0.28), height, z, f"central_south_belt_course_{band_index}", "ColumnStone")
        obj.add_box((38.4, 0.0), (0.28, 58.0), height, z, f"central_east_belt_course_{band_index}", "ColumnStone")
        obj.add_box((-38.4, 0.0), (0.28, 58.0), height, z, f"central_west_belt_course_{band_index}", "ColumnStone")
        add_facade_detail(f"central_belt_course_{band_index}", "facade_belt_course", (0.0, 0.0, z + height / 2.0))

    for y in (68.0, -68.0):
        name = "senate" if y > 0 else "house"
        for band_index, z_level in enumerate([4.8, 8.2, 12.9], start=1):
            obj.add_box((0.0, y + 30.4), (84.0, 0.22), 0.18, z_level, f"{name}_north_edge_belt_course_{band_index}", "ColumnStone")
            obj.add_box((0.0, y - 30.4), (84.0, 0.22), 0.18, z_level, f"{name}_south_edge_belt_course_{band_index}", "ColumnStone")
            obj.add_box((-42.0, y), (0.22, 61.0), 0.18, z_level, f"{name}_west_edge_belt_course_{band_index}", "ColumnStone")
            obj.add_box((42.0, y), (0.22, 61.0), 0.18, z_level, f"{name}_east_edge_belt_course_{band_index}", "ColumnStone")
            add_facade_detail(f"{name}_wing_belt_course_{band_index}", "facade_belt_course", (0.0, y, z_level))

    add_element("Central Rotunda exterior massing", "landmark", (0.0, 0.0, 12.0))
    add_element("Senate wing exterior massing", "landmark", (0.0, 68.0, 8.0))
    add_element("House wing exterior massing", "landmark", (0.0, -68.0, 8.0))

    for side, x in (("east", 67.0), ("west", -67.0)):
        front_sign = 1.0 if x > 0.0 else -1.0
        for step_index in range(5):
            width = 72.0 + step_index * 5.0
            depth = 4.0
            sx = x + (step_index * 2.2 if x > 0 else -step_index * 2.2)
            add_stair_tread_detail(
                f"{side}_front_stair_tread_{step_index+1}",
                (sx, 0.0),
                (depth, width),
                0.08 + step_index * 0.22,
                0.22 + step_index * 0.05,
                "east_west",
            )
        for riser_index in range(6):
            riser_x = x + front_sign * (11.8 + riser_index * 2.05)
            add_terrace_stair_riser_band(
                f"{side}_front_lower_terrace_riser_band_{riser_index+1:02d}",
                (riser_x, 0.0),
                (1.35, 82.0 + riser_index * 3.2),
                0.05 + riser_index * 0.055,
                0.10,
                "east_west",
            )
        add_public_terrace_landing_slab(
            f"{side}_front_lower_approach_landing",
            (x + front_sign * 25.0, 0.0),
            (8.5, 101.0),
            0.06,
            "east_west",
        )
        for chip_index, y in enumerate([-36.0, -28.0, -20.0, -12.0, -4.0, 4.0, 12.0, 20.0, 28.0, 36.0], start=1):
            add_step_edge_chip_shadow(
                f"{side}_front_step_edge_chip_shadow_{chip_index:02d}",
                (x + front_sign * 7.4, y),
                (0.56, 0.95),
                0.72,
                "east_west",
            )
        for seam_row, seam_x in enumerate([x + front_sign * 4.4, x + front_sign * 7.2, x + front_sign * 10.0], start=1):
            add_public_step_grime_seams(
                f"{side}_front_approach_row_{seam_row:02d}",
                "east_west",
                (seam_x, 0.0),
                78.0,
                18,
                0.44 + seam_row * 0.11,
            )
        for idx, y in enumerate([-24.0, -16.0, -8.0, 0.0, 8.0, 16.0, 24.0], start=1):
            column_center = (x * 0.92, y)
            column_name = f"{side}_portico_column_{idx}"
            obj.add_cylinder(column_center, 0.62, 0.2, 13.5, column_name, "ColumnStone", segments=20)
            add_exterior_column_ornament(column_name, column_center, 0.62, 0.2, 13.5, "east_west")
            add_facade_detail(column_name, "exterior_column", (column_center[0], column_center[1], 6.95))
        add_portico_intercolumn_shadows(
            f"{side}_front_portico",
            "east_west",
            x * 0.91,
            [-24.0, -16.0, -8.0, 0.0, 8.0, 16.0, 24.0],
            2.05,
            9.8,
        )
        add_arcade_shadow_bays(
            f"{side}_front_portico",
            "east_west",
            x * 0.91,
            [-20.0, -12.0, -4.0, 4.0, 12.0, 20.0],
            2.15,
            9.8,
            4.3,
        )
        add_element(f"{side.title()} front steps and colonnade", "landmark", (x, 0.0, 3.0))
        for door_index, y in enumerate([-9.0, 0.0, 9.0], start=1):
            add_revolving_door(f"{side}_front_{door_index}", (x * 0.86, y), side)
        for lamp_index, y in enumerate([-18.0, -6.0, 6.0, 18.0], start=1):
            add_public_entry_lamp(f"{side}_front_lamp_{lamp_index}", (x * 0.92, y))
        for sconce_index, y in enumerate([-13.5, -4.5, 4.5, 13.5], start=1):
            add_public_facade_sconce(f"{side}_front_public_sconce_{sconce_index:02d}", (x * 0.86, y), side)
        add_approach_handrails(f"{side}_front_approach_handrail", "east_west", (x * 0.98, 0.0), 12.5, (-35.5, 35.5))

    for side, y in (("north", 99.0), ("south", -99.0)):
        wing_sign = 1.0 if y > 0.0 else -1.0
        add_column_row(f"{side}_wing_portico", "north_south", y * 0.98, [-19.0, -12.5, -6.0, 0.0, 6.0, 12.5, 19.0], 1.3, 10.9)
        add_portico_intercolumn_shadows(
            f"{side}_wing_portico",
            "north_south",
            y * 0.97,
            [-19.0, -12.5, -6.0, 0.0, 6.0, 12.5, 19.0],
            2.05,
            8.3,
        )
        add_arcade_shadow_bays(
            f"{side}_wing_portico",
            "north_south",
            y * 0.97,
            [-15.5, -9.25, -3.0, 3.0, 9.25, 15.5],
            2.05,
            8.3,
            3.6,
        )
        for step_index in range(4):
            width = 45.0 + step_index * 4.0
            depth = 3.4
            sy = y + (step_index * 1.85 if y > 0 else -step_index * 1.85)
            add_stair_tread_detail(
                f"{side}_wing_stair_tread_{step_index+1}",
                (0.0, sy),
                (width, depth),
                0.08 + step_index * 0.20,
                0.20 + step_index * 0.05,
                "north_south",
            )
        for riser_index in range(5):
            riser_y = y + wing_sign * (8.6 + riser_index * 1.85)
            add_terrace_stair_riser_band(
                f"{side}_wing_lower_terrace_riser_band_{riser_index+1:02d}",
                (0.0, riser_y),
                (56.0 + riser_index * 3.5, 1.20),
                0.05 + riser_index * 0.052,
                0.095,
                "north_south",
            )
        add_public_terrace_landing_slab(
            f"{side}_wing_lower_approach_landing",
            (0.0, y + wing_sign * 19.5),
            (73.0, 7.5),
            0.06,
            "north_south",
        )
        for chip_index, x in enumerate([-28.0, -20.0, -12.0, -4.0, 4.0, 12.0, 20.0, 28.0], start=1):
            add_step_edge_chip_shadow(
                f"{side}_wing_step_edge_chip_shadow_{chip_index:02d}",
                (x, y + wing_sign * 6.9),
                (0.92, 0.52),
                0.60,
                "north_south",
            )
        for seam_row, seam_y in enumerate([y + wing_sign * 3.6, y + wing_sign * 5.9, y + wing_sign * 8.2], start=1):
            add_public_step_grime_seams(
                f"{side}_wing_approach_row_{seam_row:02d}",
                "north_south",
                (0.0, seam_y),
                54.0,
                14,
                0.38 + seam_row * 0.10,
            )
        for door_index, x in enumerate([-8.0, 0.0, 8.0], start=1):
            add_revolving_door(f"{side}_wing_{door_index}", (x, y), side)
        for lamp_index, x in enumerate([-18.0, -6.0, 6.0, 18.0], start=1):
            add_public_entry_lamp(f"{side}_wing_lamp_{lamp_index}", (x, y * 0.95))
        for sconce_index, x in enumerate([-13.5, -4.5, 4.5, 13.5], start=1):
            add_public_facade_sconce(f"{side}_wing_public_sconce_{sconce_index:02d}", (x, y), side)
        add_approach_handrails(f"{side}_wing_approach_handrail", "north_south", (0.0, y * 0.985), 10.0, (-24.5, 24.5))

    for side, x in (("east", 70.0), ("west", -70.0)):
        for light_index, y in enumerate([-30.0, -20.0, -10.0, 10.0, 20.0, 30.0], start=1):
            add_facade_uplight(
                f"{side}_front_facade_uplight_{light_index:02d}",
                (x, y),
                (x * 0.88, y, 7.5),
            )
    for side, y in (("north", 104.0), ("south", -104.0)):
        for light_index, x in enumerate([-26.0, -16.0, -6.0, 6.0, 16.0, 26.0], start=1):
            add_facade_uplight(
                f"{side}_wing_facade_uplight_{light_index:02d}",
                (x, y),
                (x, y * 0.92, 7.0),
            )

    for side, x in (("east", 76.0), ("west", -76.0)):
        for patch_index, y in enumerate([-24.0, -16.0, -8.0, 0.0, 8.0, 16.0, 24.0], start=1):
            add_plaza_wear_patch(f"{side}_front_step_wear_patch_{patch_index:02d}", (x, y), (2.8, 1.15), 0.62)
    for side, y in (("north", 105.0), ("south", -105.0)):
        for patch_index, x in enumerate([-18.0, -9.0, 0.0, 9.0, 18.0], start=1):
            add_plaza_wear_patch(f"{side}_wing_step_wear_patch_{patch_index:02d}", (x, y), (2.2, 1.05), 0.52)
    for patch_index, (x, y, sx, sy) in enumerate(
        [
            (-42.0, -18.0, 5.0, 2.0),
            (-42.0, 18.0, 5.0, 2.0),
            (42.0, -18.0, 5.0, 2.0),
            (42.0, 18.0, 5.0, 2.0),
            (-18.0, -42.0, 2.0, 5.0),
            (18.0, -42.0, 2.0, 5.0),
            (-18.0, 42.0, 2.0, 5.0),
            (18.0, 42.0, 2.0, 5.0),
        ],
        start=1,
    ):
        add_plaza_wear_patch(f"public_plaza_wear_patch_{patch_index:02d}", (x, y), (sx, sy), 0.13)

    for idx, y in enumerate([value * 8.0 for value in range(-7, 8)], start=1):
        add_plaza_bollard(f"east_plaza_bollard_{idx:02d}", (78.0, y))
        add_plaza_bollard(f"west_plaza_bollard_{idx:02d}", (-78.0, y))
    for idx, x in enumerate([-46.0, -30.0, -14.0, 14.0, 30.0, 46.0], start=1):
        add_bench(f"east_public_bench_{idx:02d}", (86.0, x * 0.55))
        add_bench(f"west_public_bench_{idx:02d}", (-86.0, x * 0.55))

    add_dome_cylinder((0.0, 0.0), 20.5, 17.9, 1.2, "dome_base_octagonal_plinth", "ColumnStone", segments=32)
    add_dome_cylinder((0.0, 0.0), 18.0, 18.0, 16.0, "dome_drum_cylinder", "CapitolDome", segments=96)
    add_dome_ring((0.0, 0.0), 18.4, 17.8, 20.6, 0.55, "dome_lower_balustrade_ring", "ColumnStone", segments=96)
    add_dome_ring((0.0, 0.0), 16.2, 15.7, 30.8, 0.45, "dome_upper_balustrade_ring", "ColumnStone", segments=96)
    for idx in range(48):
        angle = math.tau * idx / 48.0
        add_dome_cylinder((18.1 * math.cos(angle), 18.1 * math.sin(angle)), 0.11, 20.72, 0.78, f"dome_lower_balustrade_post_{idx+1:02d}", "ColumnStone", segments=8)
        add_dome_cylinder((15.95 * math.cos(angle), 15.95 * math.sin(angle)), 0.09, 30.92, 0.64, f"dome_upper_balustrade_post_{idx+1:02d}", "ColumnStone", segments=8)
    add_facade_detail("dome_lower_balustrade_posts", "dome_balustrade_posts", (0.0, 0.0, dome_z(21.1)), {"count": 48})
    add_facade_detail("dome_upper_balustrade_posts", "dome_balustrade_posts", (0.0, 0.0, dome_z(31.24)), {"count": 48})
    for idx in range(32):
        angle = math.tau * idx / 32.0
        px = 18.1 * math.cos(angle)
        py = 18.1 * math.sin(angle)
        add_dome_cylinder((px, py), 0.18, 19.0, 10.4, f"dome_drum_pilaster_{idx+1:02d}", "ColumnStone", segments=10)
        add_dome_drum_arcade_bay(idx + 1, angle)
        if idx % 2 == 0:
            wx = 17.85 * math.cos(angle)
            wy = 17.85 * math.sin(angle)
            add_dome_window_trim(idx // 2 + 1, angle, 18.02)
            add_dome_cylinder((wx, wy), 0.30, 22.8, 1.25, f"dome_drum_dark_window_{idx//2+1:02d}", "FacadeWindow", segments=10)
            add_dome_drum_spandrel_panel(f"dome_drum_spandrel_panel_{idx//2+1:02d}", angle, 25.25)
    for idx in range(24):
        angle = math.tau * idx / 24.0
        px = 12.2 * math.cos(angle)
        py = 12.2 * math.sin(angle)
        add_dome_cylinder((px, py), 0.10, 34.5, 16.5, f"dome_vertical_rib_{idx+1:02d}", "ColumnStone", segments=8)
        add_dome_curved_rib(idx + 1, angle)
        add_facade_detail(
            f"dome_vertical_rib_{idx+1:02d}",
            "dome_vertical_rib",
            (px, py, dome_z(42.75)),
            {"radial_index": idx + 1},
        )
    for band_index, (outer_radius, inner_radius, z) in enumerate(
        [(18.0, 17.70, 37.8), (16.9, 16.55, 42.6), (14.55, 14.20, 47.4), (11.50, 11.18, 51.2)],
        start=1,
    ):
        add_dome_ring((0.0, 0.0), outer_radius, inner_radius, z, 0.16, f"dome_lateral_stone_band_{band_index}", "ColumnStone", segments=96)
        add_facade_detail(
            f"dome_lateral_stone_band_{band_index}",
            "dome_lateral_band",
            (0.0, 0.0, dome_z(z + 0.08)),
            {"band_index": band_index},
        )
    for row_index, (z, panel_height, panel_width) in enumerate(
        [(36.2, 1.04, 1.05), (40.6, 1.00, 0.98), (45.0, 0.88, 0.86), (49.1, 0.72, 0.72)],
        start=1,
    ):
        for idx in range(24):
            angle = math.tau * (idx + 0.5) / 24.0
            add_dome_shell_panel_frame(
                f"dome_shell_panel_frame_r{row_index:02d}_{idx+1:02d}",
                angle,
                z,
                panel_height,
                panel_width,
            )
    add_dome_shell((0.0, 0.0), 18.0, 34.0, 22.0, "capitol_dome_approximate_shell", "CapitolDome", segments=72, rings=10)
    add_dome_shell_weathering_details()
    add_dome_cylinder((0.0, 0.0), 4.2, 55.5, 5.2, "dome_lantern_cylinder", "ColumnStone", segments=32)
    for idx in range(16):
        angle = math.tau * idx / 16.0
        add_dome_cylinder((4.45 * math.cos(angle), 4.45 * math.sin(angle)), 0.10, 55.55, 4.48, f"dome_lantern_column_{idx+1:02d}", "ColumnStone", segments=10)
        add_dome_cylinder((4.58 * math.cos(angle), 4.58 * math.sin(angle)), 0.055, 59.88, 0.70, f"dome_lantern_balustrade_post_{idx+1:02d}", "ColumnStone", segments=8)
        add_facade_detail(
            f"dome_lantern_column_{idx+1:02d}",
            "lantern_column",
            (4.45 * math.cos(angle), 4.45 * math.sin(angle), dome_z(57.79)),
            {"radial_index": idx + 1},
        )
    add_dome_ring((0.0, 0.0), 4.72, 4.44, 60.45, 0.16, "dome_lantern_balustrade_ring", "ColumnStone", segments=64)
    add_facade_detail("dome_lantern_balustrade", "lantern_balustrade", (0.0, 0.0, dome_z(60.28)), {"count": 16})
    for idx in range(8):
        angle = math.tau * idx / 8.0
        add_dome_cylinder((4.28 * math.cos(angle), 4.28 * math.sin(angle)), 0.16, 56.25, 1.7, f"dome_lantern_dark_window_{idx+1:02d}", "FacadeWindow", segments=8)
        add_lantern_window_trim(idx + 1, angle)
    add_facade_detail("dome_lantern_dark_window_ring", "lantern_window", (0.0, 0.0, dome_z(57.1)), {"count": 8})
    add_dome_shell((0.0, 0.0), 4.2, 60.2, 4.0, "dome_lantern_cap", "CapitolDome", segments=32, rings=5)
    add_dome_cylinder((0.0, 0.0), 0.18, 64.0, 2.1, "dome_lantern_finial", "ColumnStone", segments=12)
    add_statue_of_freedom_silhouette()
    add_facade_detail("dome_lantern_finial", "dome_finial", (0.0, 0.0, dome_z(65.05)))
    add_element("Capitol Dome / lantern visual massing", "landmark", (0.0, 0.0, dome_z(49.0)))

    obj.write(MESH_DIR / "capitol_landmark_visual_details.obj", "capitol_materials.mtl")
    return {
        "elements": elements,
        "labels": labels,
        "facade_details": facade_details,
        "height_profile": {
            "public_height_target_m": round(capitol_public_height_m, 2),
            "target_source": "public Architect of the Capitol 287 ft height fact converted to meters",
            "dome_remap_base_m": round(dome_remap_base_z, 2),
            "dome_vertical_scale": round(dome_z_scale, 5),
            "statue_of_freedom_height_m": round(statue_of_freedom_height_m, 2),
        },
    }


def add_label(labels: list[dict[str, Any]], name: str, x: float, y: float, z: float, category: str) -> None:
    labels.append({"text": name, "location_m": [round(x, 3), round(y, 3), round(z, 3)], "category": category})


def add_room(
    obj: ObjWriter,
    rooms: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    name: str,
    center: tuple[float, float],
    size: tuple[float, float],
    material: str,
    category: str,
    z: float = 4.0,
    height: float = 0.35,
    with_walls: bool = True,
) -> None:
    obj.add_box(center, size, height, z, f"interior_{name}", material)
    if with_walls:
        cx, cy = center
        sx, sy = size
        wall_thickness = 0.42
        wall_height = 3.1
        wall_z = z + height
        obj.add_box((cx, cy + sy / 2.0), (sx, wall_thickness), wall_height, wall_z, f"wall_north_{name}", "InteriorWall")
        obj.add_box((cx, cy - sy / 2.0), (sx, wall_thickness), wall_height, wall_z, f"wall_south_{name}", "InteriorWall")
        obj.add_box((cx + sx / 2.0, cy), (wall_thickness, sy), wall_height, wall_z, f"wall_east_{name}", "InteriorWall")
        obj.add_box((cx - sx / 2.0, cy), (wall_thickness, sy), wall_height, wall_z, f"wall_west_{name}", "InteriorWall")
    rooms.append(
        {
            "name": name,
            "category": category,
            "center_m": [round(center[0], 3), round(center[1], 3), round(z, 3)],
            "size_m": [round(size[0], 3), round(size[1], 3)],
            "public_accuracy": "schematic_public_reference",
        }
    )
    add_label(labels, name, center[0], center[1], z + 0.7, category)


def add_gallery_risers(
    obj: ObjWriter,
    prefix: str,
    center: tuple[float, float],
    width: float,
    depth: float,
    rows: int,
    z: float,
    material: str = "PublicGallery",
) -> None:
    cx, cy = center
    for row in range(rows):
        y = cy + (row - (rows - 1) / 2.0) * (depth / rows)
        obj.add_box(
            (cx, y),
            (width, depth / rows * 0.82),
            0.28 + row * 0.18,
            z + row * 0.18,
            f"{prefix}_gallery_riser_{row+1}",
            material,
        )
        for rail_index, x in enumerate([-width / 2.0 + 1.0, width / 2.0 - 1.0], start=1):
            obj.add_box(
                (cx + x, y),
                (0.18, depth / rows * 0.72),
                0.9,
                z + row * 0.18 + 0.25,
                f"{prefix}_gallery_side_rail_{row+1}_{rail_index}",
                "BrassRail",
            )


def add_public_office_grid(
    obj: ObjWriter,
    labels: list[dict[str, Any]],
    prefix: str,
    center: tuple[float, float],
    size: tuple[float, float],
    columns: int,
    rows: int,
    office_details: list[dict[str, Any]] | None = None,
    z: float = 4.45,
) -> list[dict[str, Any]]:
    cx, cy = center
    sx, sy = size
    cell_w = sx / columns
    cell_h = sy / rows
    records: list[dict[str, Any]] = []

    def add_office_detail(name: str, kind: str, center_m: tuple[float, float, float], size_m: tuple[float, float] | None = None) -> None:
        if office_details is None:
            return
        record: dict[str, Any] = {
            "name": name,
            "kind": kind,
            "zone": prefix,
            "center_m": [round(center_m[0], 3), round(center_m[1], 3), round(center_m[2], 3)],
            "public_accuracy": "schematic_public_office_visual_detail",
            "assignment": "Generic public visual detail only; not an actual office assignment, staff location, or room number.",
        }
        if size_m is not None:
            record["size_m"] = [round(size_m[0], 3), round(size_m[1], 3)]
        office_details.append(record)

    obj.add_box((cx, cy), (cell_w * 0.48, sy * 0.94), 0.05, z + 0.012, f"{prefix}_public_office_corridor_band", "InteriorFloor")
    add_office_detail(f"{prefix}_public_office_corridor_band", "public_office_corridor_band", (cx, cy, z + 0.04), (cell_w * 0.48, sy * 0.94))

    for shared_index, y_offset in enumerate([-sy * 0.39, sy * 0.39], start=1):
        table_name = f"{prefix}_shared_support_table_{shared_index}"
        table_center = (cx, cy + y_offset)
        obj.add_box(table_center, (cell_w * 0.62, 0.92), 0.32, z + 0.20, f"{table_name}_top", "DeskWood")
        obj.add_box((table_center[0], table_center[1] - 0.50), (cell_w * 0.50, 0.08), 0.38, z + 0.46, f"{table_name}_rear_lip", "InteriorTrim")
        obj.add_box((table_center[0] - cell_w * 0.16, table_center[1] + 0.16), (0.42, 0.30), 0.045, z + 0.535, f"{table_name}_document_tray_lower", "DoorMetal")
        obj.add_box((table_center[0] - cell_w * 0.16, table_center[1] + 0.16), (0.38, 0.26), 0.026, z + 0.592, f"{table_name}_document_tray_papers", "LaneMarkingWhite")
        obj.add_box((table_center[0] + cell_w * 0.16, table_center[1] - 0.08), (0.36, 0.26), 0.18, z + 0.535, f"{table_name}_supply_bin", "InteriorTrim")
        obj.add_box((table_center[0] + cell_w * 0.16, table_center[1] - 0.08), (0.28, 0.18), 0.035, z + 0.735, f"{table_name}_supply_bin_contents", "DoorMetal")
        add_office_detail(table_name, "shared_support_table", (table_center[0], table_center[1], z + 0.36), (cell_w * 0.62, 0.92))
        add_office_detail(f"{table_name}_document_tray", "shared_support_document_tray", (table_center[0] - cell_w * 0.16, table_center[1] + 0.16, z + 0.59), (0.42, 0.30))
        add_office_detail(f"{table_name}_supply_bin", "shared_support_supply_bin", (table_center[0] + cell_w * 0.16, table_center[1] - 0.08, z + 0.64), (0.36, 0.26))

    for row in range(rows):
        for col in range(columns):
            ox = cx - sx / 2.0 + cell_w * (col + 0.5)
            oy = cy - sy / 2.0 + cell_h * (row + 0.5)
            room_id = f"{prefix}_generic_office_{row+1}_{col+1}"
            obj.add_box((ox, oy), (cell_w * 0.82, cell_h * 0.72), 0.16, z, room_id + "_floor", "OfficeZone")
            obj.add_box((ox, oy + cell_h * 0.36), (cell_w * 0.80, 0.18), 2.2, z + 0.16, room_id + "_back_partition", "InteriorTrim")
            obj.add_box((ox - cell_w * 0.40, oy), (0.18, cell_h * 0.68), 2.2, z + 0.16, room_id + "_left_partition", "InteriorTrim")
            obj.add_box((ox + cell_w * 0.40, oy), (0.18, cell_h * 0.68), 2.2, z + 0.16, room_id + "_right_partition", "InteriorTrim")
            obj.add_box((ox, oy + cell_h * 0.36), (cell_w * 0.80, 0.22), 0.055, z + 2.36, room_id + "_partition_top_cap", "InteriorTrim")
            obj.add_box((ox, oy - cell_h * 0.10), (cell_w * 0.40, 0.70), 0.78, z + 0.18, room_id + "_desk", "DeskWood")
            obj.add_box((ox, oy - cell_h * 0.10), (cell_w * 0.28, 0.46), 0.030, z + 0.97, room_id + "_desk_surface_inset", "InteriorTrim")
            monitor_y = oy + cell_h * 0.03
            keyboard_y = oy - cell_h * 0.20
            obj.add_box((ox, monitor_y), (0.18, 0.12), 0.035, z + 1.005, room_id + "_monitor_base", "DoorMetal")
            obj.add_cylinder((ox, monitor_y), 0.035, z + 1.035, 0.22, room_id + "_monitor_stem", "DoorMetal", segments=8)
            obj.add_box((ox, monitor_y + 0.035), (0.68, 0.055), 0.44, z + 1.22, room_id + "_monitor_screen", "MarkerBlue")
            obj.add_box((ox, keyboard_y), (0.54, 0.16), 0.026, z + 1.008, room_id + "_keyboard", "DoorMetal")
            grommet_center = (ox + cell_w * 0.10, oy - cell_h * 0.05)
            obj.add_box(grommet_center, (0.16, 0.060), 0.018, z + 1.022, room_id + "_desk_cable_grommet", "DoorMetal")
            obj.add_polyline_strip(
                [(ox + 0.07, monitor_y - 0.02), (ox + cell_w * 0.08, oy - cell_h * 0.02), grommet_center],
                0.026,
                z + 1.041,
                room_id + "_loose_monitor_cable_loop",
                "RoadCrackSealant",
            )
            cable_tray_center = (ox, oy + cell_h * 0.34)
            obj.add_box(cable_tray_center, (cell_w * 0.58, 0.045), 0.075, z + 0.62, room_id + "_back_partition_cable_tray", "DoorMetal")
            outlet_center = (ox + cell_w * 0.24, oy + cell_h * 0.345)
            data_plate_center = (ox + cell_w * 0.32, oy + cell_h * 0.345)
            obj.add_box(outlet_center, (0.16, 0.026), 0.12, z + 0.66, room_id + "_wall_outlet_plate", "LaneMarkingWhite")
            obj.add_box(data_plate_center, (0.14, 0.026), 0.10, z + 0.83, room_id + "_data_plate", "MarkerBlue")
            obj.add_box((ox - cell_w * 0.12, oy - cell_h * 0.02), (0.42, 0.28), 0.014, z + 1.012, room_id + "_paper_stack_1", "LaneMarkingWhite")
            obj.add_box((ox - cell_w * 0.12 + 0.025, oy - cell_h * 0.02 - 0.018), (0.39, 0.26), 0.014, z + 1.030, room_id + "_paper_stack_2", "LaneMarkingWhite")
            inbox_center = (ox + cell_w * 0.14, oy - cell_h * 0.19)
            obj.add_box(inbox_center, (0.38, 0.26), 0.020, z + 1.040, room_id + "_inbox_tray_bottom", "DoorMetal")
            obj.add_box(inbox_center, (0.34, 0.22), 0.014, z + 1.068, room_id + "_inbox_tray_papers", "LaneMarkingWhite")
            obj.add_box((inbox_center[0], inbox_center[1] + 0.015), (0.38, 0.26), 0.018, z + 1.090, room_id + "_inbox_tray_top", "DoorMetal")
            lamp_x = ox + cell_w * 0.15
            lamp_y = oy + cell_h * 0.04
            obj.add_cylinder((lamp_x, lamp_y), 0.07, z + 1.000, 0.05, room_id + "_desk_lamp_base", "LightFixtureMetal", segments=10)
            obj.add_cylinder((lamp_x, lamp_y), 0.025, z + 1.040, 0.36, room_id + "_desk_lamp_stem", "LightFixtureMetal", segments=8)
            obj.add_cylinder((lamp_x, lamp_y), 0.12, z + 1.390, 0.11, room_id + "_desk_lamp_warm_shade", "WarmLightGlass", segments=12)
            obj.add_box((ox, oy - cell_h * 0.28), (0.70, 0.55), 0.55, z + 0.18, room_id + "_chair", "ChairLeather")
            obj.add_box((ox, oy - cell_h * 0.36), (0.74, 0.10), 0.72, z + 0.52, room_id + "_chair_back", "ChairLeather")
            obj.add_box((ox - 0.44, oy - cell_h * 0.28), (0.055, 0.42), 0.18, z + 0.54, room_id + "_chair_left_arm", "ChairLeather")
            obj.add_box((ox + 0.44, oy - cell_h * 0.28), (0.055, 0.42), 0.18, z + 0.54, room_id + "_chair_right_arm", "ChairLeather")
            obj.add_cylinder((ox, oy - cell_h * 0.28), 0.22, z + 0.16, 0.055, room_id + "_chair_swivel_base", "DoorMetal", segments=12)
            for caster_index, caster_angle in enumerate([math.radians(value) for value in (18, 90, 162, 234, 306)], start=1):
                caster_center = (
                    ox + math.cos(caster_angle) * 0.32,
                    oy - cell_h * 0.28 + math.sin(caster_angle) * 0.32,
                )
                obj.add_oriented_box(
                    caster_center,
                    (0.20, 0.045),
                    0.035,
                    z + 0.135,
                    caster_angle,
                    f"{room_id}_chair_caster_{caster_index}",
                    "DoorMetal",
                )
            bookcase_x = ox - cell_w * 0.27
            obj.add_box((bookcase_x, oy + cell_h * 0.22), (0.58, 1.55), 1.35, z + 0.20, room_id + "_bookcase_body", "DeskWood")
            for shelf_index, shelf_y in enumerate([-0.46, 0.0, 0.46], start=1):
                obj.add_box((bookcase_x, oy + cell_h * 0.22 + shelf_y), (0.62, 0.045), 0.055, z + 0.76 + shelf_index * 0.25, f"{room_id}_bookcase_shelf_{shelf_index}", "InteriorTrim")
            binder_materials = ["MarkerBlue", "StreetSignGreen", "DiplomaticZone", "InteriorTrim"]
            binder_y = oy + cell_h * 0.22 - 0.46
            for binder_index in range(4):
                binder_x = bookcase_x - 0.19 + binder_index * 0.12
                binder_height = 0.30 + 0.035 * (binder_index % 2)
                obj.add_box(
                    (binder_x, binder_y),
                    (0.085, 0.16),
                    binder_height,
                    z + 0.84,
                    f"{room_id}_bookcase_binder_spine_{binder_index+1}",
                    binder_materials[binder_index % len(binder_materials)],
                )
            cabinet_x = ox + cell_w * 0.27
            obj.add_box((cabinet_x, oy + cell_h * 0.18), (0.72, 1.10), 0.78, z + 0.18, room_id + "_storage_cabinet", "InteriorTrim")
            obj.add_box((cabinet_x, oy + cell_h * 0.18), (0.78, 0.055), 0.08, z + 0.98, room_id + "_storage_cabinet_top", "DeskWood")
            obj.add_box((cabinet_x, oy + cell_h * 0.18 - 0.47), (0.46, 0.035), 0.034, z + 0.64, room_id + "_storage_cabinet_label_low", "DoorMetal")
            obj.add_box((cabinet_x, oy + cell_h * 0.18 - 0.47), (0.36, 0.026), 0.018, z + 0.68, room_id + "_storage_cabinet_label_insert", "LaneMarkingWhite")
            pinboard_center = (ox + cell_w * 0.16, oy + cell_h * 0.345)
            obj.add_box(pinboard_center, (0.58, 0.035), 0.40, z + 1.44, room_id + "_pinboard_panel", "PaintingCanvas")
            for note_index, note_x in enumerate([-0.16, 0.0, 0.15], start=1):
                obj.add_box(
                    (pinboard_center[0] + note_x, pinboard_center[1] - 0.002),
                    (0.13, 0.020),
                    0.10,
                    z + 1.54 + 0.06 * (note_index % 2),
                    f"{room_id}_pinboard_note_{note_index}",
                    "LaneMarkingWhite" if note_index != 2 else "MarkerBlue",
                )
            door_y = oy - cell_h * 0.36
            obj.add_box((ox, door_y), (cell_w * 0.36, 0.08), 0.06, z + 0.03, room_id + "_public_door_threshold", "StepStone")
            obj.add_box((ox, door_y + 0.05), (cell_w * 0.26, 0.10), 1.62, z + 0.22, room_id + "_generic_door_panel", "DoorGlass")
            plaque_x = ox - cell_w * 0.24
            obj.add_box((plaque_x, door_y + 0.10), (0.34, 0.055), 0.22, z + 1.38, room_id + "_generic_public_plaque", "MarkerBlue")
            add_office_detail(room_id + "_back_partition", "generic_office_partition_panel", (ox, oy + cell_h * 0.36, z + 1.26), (cell_w * 0.80, 0.18))
            add_office_detail(room_id + "_left_partition", "generic_office_partition_panel", (ox - cell_w * 0.40, oy, z + 1.26), (0.18, cell_h * 0.68))
            add_office_detail(room_id + "_right_partition", "generic_office_partition_panel", (ox + cell_w * 0.40, oy, z + 1.26), (0.18, cell_h * 0.68))
            add_office_detail(room_id + "_partition_top_cap", "generic_office_partition_top_cap", (ox, oy + cell_h * 0.36, z + 2.388), (cell_w * 0.80, 0.22))
            add_office_detail(room_id + "_desk_surface_inset", "generic_office_desk_surface_inset", (ox, oy - cell_h * 0.10, z + 0.985), (cell_w * 0.28, 0.46))
            add_office_detail(room_id + "_monitor_screen", "generic_office_monitor", (ox, monitor_y + 0.035, z + 1.44), (0.68, 0.055))
            add_office_detail(room_id + "_monitor_stand", "generic_office_monitor_stand", (ox, monitor_y, z + 1.13), (0.18, 0.12))
            add_office_detail(room_id + "_keyboard", "generic_office_keyboard", (ox, keyboard_y, z + 1.021), (0.54, 0.16))
            add_office_detail(room_id + "_desk_cable_grommet", "generic_office_desk_cable_grommet", (grommet_center[0], grommet_center[1], z + 1.031), (0.16, 0.060))
            add_office_detail(room_id + "_back_partition_cable_tray", "generic_office_cable_tray", (cable_tray_center[0], cable_tray_center[1], z + 0.658), (cell_w * 0.58, 0.045))
            add_office_detail(room_id + "_wall_outlet_plate", "generic_office_wall_outlet_plate", (outlet_center[0], outlet_center[1], z + 0.72), (0.16, 0.026))
            add_office_detail(room_id + "_data_plate", "generic_office_data_plate", (data_plate_center[0], data_plate_center[1], z + 0.88), (0.14, 0.026))
            add_office_detail(room_id + "_paper_stack", "generic_office_paper_stack", (ox - cell_w * 0.12 + 0.012, oy - cell_h * 0.02 - 0.009, z + 1.033), (0.42, 0.28))
            add_office_detail(room_id + "_inbox_tray", "generic_office_inbox_tray", (inbox_center[0], inbox_center[1], z + 1.072), (0.38, 0.26))
            add_office_detail(room_id + "_loose_monitor_cable_loop", "generic_office_loose_cable_loop", (ox + cell_w * 0.06, oy - cell_h * 0.035, z + 1.042), (0.42, 0.16))
            add_office_detail(room_id + "_desk_lamp", "generic_office_task_lamp", (lamp_x, lamp_y, z + 1.25), (0.24, 0.24))
            add_office_detail(room_id + "_chair_back", "generic_office_chair_back", (ox, oy - cell_h * 0.36, z + 0.88), (0.74, 0.10))
            add_office_detail(room_id + "_chair_arm_pair", "generic_office_chair_arm_pair", (ox, oy - cell_h * 0.28, z + 0.63), (0.94, 0.42))
            add_office_detail(room_id + "_chair_swivel_base", "generic_office_chair_swivel_base", (ox, oy - cell_h * 0.28, z + 0.19), (0.64, 0.64))
            add_office_detail(room_id + "_bookcase", "generic_office_bookcase", (bookcase_x, oy + cell_h * 0.22, z + 0.875), (0.62, 1.55))
            add_office_detail(room_id + "_book_spine_row", "generic_office_book_spine_row", (bookcase_x, binder_y, z + 1.01), (0.52, 0.16))
            add_office_detail(room_id + "_storage_cabinet", "generic_office_storage_cabinet", (cabinet_x, oy + cell_h * 0.18, z + 0.57), (0.78, 1.10))
            add_office_detail(room_id + "_storage_cabinet_label_plate", "generic_office_cabinet_label_plate", (cabinet_x, oy + cell_h * 0.18 - 0.47, z + 0.67), (0.46, 0.035))
            add_office_detail(room_id + "_pinboard_panel", "generic_office_pinboard_panel", (pinboard_center[0], pinboard_center[1], z + 1.66), (0.58, 0.035))
            add_office_detail(room_id + "_public_door_threshold", "office_door_threshold", (ox, door_y, z + 0.06), (cell_w * 0.36, 0.08))
            add_office_detail(room_id + "_generic_door_panel", "generic_office_door_panel", (ox, door_y + 0.05, z + 1.03), (cell_w * 0.26, 0.10))
            add_office_detail(room_id + "_generic_public_plaque", "generic_office_plaque", (plaque_x, door_y + 0.10, z + 1.49), (0.34, 0.055))
            records.append(
                {
                    "name": room_id,
                    "category": "generic_public_office_visual_cell",
                    "center_m": [round(ox, 3), round(oy, 3), round(z, 3)],
                    "note": "Visual-only generic office cell; not an actual office assignment or room number.",
                }
            )
    add_label(labels, f"{prefix.replace('_', ' ').title()} generic office cells", cx, cy, z + 2.8, "generic_office_zone")
    return records


def add_rotunda_visual_details(
    obj: ObjWriter,
    labels: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> None:
    def add_rotunda_detail(
        name: str,
        kind: str,
        center_m: tuple[float, float, float],
        size_m: tuple[float, float] | None = None,
    ) -> None:
        record: dict[str, Any] = {
            "name": name,
            "kind": kind,
            "location": "Rotunda",
            "center_m": [round(center_m[0], 3), round(center_m[1], 3), round(center_m[2], 3)],
            "public_accuracy": "schematic_public_rotunda_visual_detail",
            "assignment": (
                "Public visual architectural detail only; not a restricted route, "
                "security feature, or operational placement."
            ),
        }
        if size_m is not None:
            record["size_m"] = [round(size_m[0], 3), round(size_m[1], 3)]
        records.append(record)

    obj.add_ring((0.0, 0.0), 15.05, 14.45, 4.35, 4.9, "rotunda_public_wall_ring", "RotundaWall", segments=96)
    add_rotunda_detail("rotunda_public_wall_ring", "wall_ring", (0.0, 0.0, 6.8), (30.1, 30.1))
    obj.add_ring((0.0, 0.0), 10.8, 10.55, 4.42, 0.18, "rotunda_inner_floor_trim_ring", "BrassRail", segments=96)
    add_rotunda_detail("rotunda_inner_floor_trim_ring", "floor_trim_ring", (0.0, 0.0, 4.51), (21.6, 21.6))
    obj.add_cylinder((0.0, 0.0), 3.2, 4.46, 0.18, "rotunda_center_floor_medallion", "BrassRail", segments=64)
    add_rotunda_detail("rotunda_center_floor_medallion", "center_floor_medallion", (0.0, 0.0, 4.55), (6.4, 6.4))

    for idx in range(16):
        angle = math.tau * idx / 16.0
        start = (3.95 * math.cos(angle), 3.95 * math.sin(angle))
        end = (10.25 * math.cos(angle), 10.25 * math.sin(angle))
        name = f"rotunda_floor_radial_inlay_{idx+1:02d}"
        obj.add_polyline_strip([start, end], 0.16, 4.49, name, "BrassRail")
        mid_radius = 7.10
        add_rotunda_detail(
            name,
            "floor_radial_inlay",
            (mid_radius * math.cos(angle), mid_radius * math.sin(angle), 4.5),
            (6.3, 0.16),
        )

    for idx in range(16):
        angle = math.tau * idx / 16.0
        x = 13.55 * math.cos(angle)
        y = 13.55 * math.sin(angle)
        name = f"rotunda_perimeter_column_{idx+1:02d}"
        obj.add_cylinder((x, y), 0.28, 4.42, 4.25, name, "ColumnStone", segments=16)
        obj.add_cylinder((x, y), 0.42, 4.38, 0.16, f"{name}_base_ring", "StepStone", segments=16)
        obj.add_cylinder((x, y), 0.38, 8.52, 0.18, f"{name}_capital_block", "InteriorTrim", segments=16)
        add_rotunda_detail(name, "perimeter_column", (x, y, 6.545), (0.56, 0.56))
        add_rotunda_detail(f"{name}_base_ring", "perimeter_column_base", (x, y, 4.46), (0.84, 0.84))
        add_rotunda_detail(f"{name}_capital_block", "perimeter_column_capital", (x, y, 8.61), (0.76, 0.76))
        for groove_idx, groove_offset in enumerate([-0.42, -0.14, 0.14, 0.42], start=1):
            groove_angle = angle + groove_offset
            groove_x = x + 0.285 * math.cos(groove_angle)
            groove_y = y + 0.285 * math.sin(groove_angle)
            groove_name = f"{name}_fluting_groove_{groove_idx:02d}"
            obj.add_oriented_box(
                (groove_x, groove_y),
                (0.035, 0.135),
                3.52,
                4.82,
                groove_angle,
                groove_name,
                "StepStone",
            )
            add_rotunda_detail(groove_name, "column_fluting_groove", (groove_x, groove_y, 6.58), (0.035, 0.135))

    for idx in range(32):
        angle = math.tau * idx / 32.0 + math.pi / 32.0
        x = 14.72 * math.cos(angle)
        y = 14.72 * math.sin(angle)
        name = f"rotunda_upper_coffer_panel_{idx+1:02d}"
        obj.add_cylinder((x, y), 0.24, 7.55, 0.10, name, "ArtFrameGold", segments=12)
        add_rotunda_detail(name, "upper_coffer_panel", (x, y, 7.6), (0.48, 0.48))

    dome_ring_specs = [
        ("rotunda_dome_springline_molding", "dome_springline_molding", 13.65, 13.36, 9.24, 0.16, "ArtFrameGold"),
        ("rotunda_dome_lower_coffer_belt_ring", "dome_coffer_belt_ring", 12.15, 11.92, 10.58, 0.12, "InteriorTrim"),
        ("rotunda_dome_middle_coffer_belt_ring", "dome_coffer_belt_ring", 9.60, 9.40, 12.12, 0.11, "InteriorTrim"),
        ("rotunda_dome_upper_coffer_belt_ring", "dome_coffer_belt_ring", 6.90, 6.72, 13.52, 0.10, "InteriorTrim"),
    ]
    for name, kind, outer_radius, inner_radius, z, height, material in dome_ring_specs:
        obj.add_ring((0.0, 0.0), outer_radius, inner_radius, z, height, name, material, segments=96)
        add_rotunda_detail(name, kind, (0.0, 0.0, z + height / 2.0), (outer_radius * 2.0, outer_radius * 2.0))

    for idx in range(24):
        angle = math.tau * idx / 24.0
        inner_radius = 4.95
        outer_radius = 12.75
        start = (inner_radius * math.cos(angle), inner_radius * math.sin(angle))
        end = (outer_radius * math.cos(angle), outer_radius * math.sin(angle))
        name = f"rotunda_dome_interior_rib_{idx+1:02d}"
        obj.add_polyline_strip([start, end], 0.12, 11.40, name, "ArtFrameGold")
        mid_radius = (inner_radius + outer_radius) / 2.0
        add_rotunda_detail(name, "interior_dome_rib", (mid_radius * math.cos(angle), mid_radius * math.sin(angle), 11.42), (outer_radius - inner_radius, 0.12))

    for band_index, (radius, z, panel_width, panel_depth, panel_count) in enumerate(
        [
            (12.10, 10.76, 0.78, 0.20, 24),
            (9.55, 12.30, 0.68, 0.18, 24),
            (6.85, 13.72, 0.54, 0.16, 24),
        ],
        start=1,
    ):
        for idx in range(panel_count):
            angle = math.tau * (idx + 0.5) / panel_count
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            name = f"rotunda_dome_interior_coffer_b{band_index:02d}_{idx+1:02d}"
            obj.add_oriented_box((x, y), (panel_width, panel_depth), 0.07, z, angle + math.pi / 2.0, name, "RotundaWall")
            add_rotunda_detail(name, "interior_dome_coffer_panel", (x, y, z + 0.035), (panel_width, panel_depth))

    for idx in range(32):
        angle = math.tau * (idx + 0.5) / 32.0
        radius = 14.57
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        name = f"rotunda_upper_frieze_panel_{idx+1:02d}"
        obj.add_oriented_box((x, y), (0.86, 0.095), 0.30, 8.76, angle + math.pi / 2.0, name, "PaintingCanvas")
        add_rotunda_detail(name, "interior_frieze_panel", (x, y, 8.91), (0.86, 0.095))

    obj.add_disk((0.0, 0.0), 4.20, 4.515, "rotunda_oculus_soft_light_pool", "WarmLightGlass", segments=72)
    add_rotunda_detail("rotunda_oculus_soft_light_pool", "oculus_light_pool", (0.0, 0.0, 4.516), (8.4, 8.4))

    portal_specs = [
        ("north", (0.0, 14.42), "y", 1.0),
        ("south", (0.0, -14.42), "y", -1.0),
        ("east", (14.42, 0.0), "x", 1.0),
        ("west", (-14.42, 0.0), "x", -1.0),
    ]
    for name_part, (cx, cy), axis, sign in portal_specs:
        name = f"rotunda_public_arch_{name_part}_portal"
        if axis == "y":
            obj.add_box((cx - 3.15, cy), (0.46, 0.72), 3.35, 4.48, f"{name}_left_post", "InteriorTrim")
            obj.add_box((cx + 3.15, cy), (0.46, 0.72), 3.35, 4.48, f"{name}_right_post", "InteriorTrim")
            obj.add_box((cx, cy), (6.75, 0.72), 0.55, 7.62, f"{name}_lintel", "InteriorTrim")
            obj.add_box((cx, cy - sign * 0.18), (5.65, 0.16), 0.42, 7.12, f"{name}_inner_shadow_line", "BrassRail")
            for side_label, x_offset in [("left", -2.08), ("right", 2.08)]:
                inlay_name = f"{name}_{side_label}_spandrel_inlay"
                obj.add_box((cx + x_offset, cy - sign * 0.28), (1.12, 0.105), 0.42, 7.04, inlay_name, "ArtFrameGold")
                add_rotunda_detail(inlay_name, "arch_spandrel_inlay", (cx + x_offset, cy - sign * 0.28, 7.25), (1.12, 0.105))
            keystone_name = f"{name}_keystone_block"
            obj.add_box((cx, cy - sign * 0.32), (0.54, 0.14), 0.72, 7.38, keystone_name, "ColumnStone")
            add_rotunda_detail(keystone_name, "arch_keystone_block", (cx, cy - sign * 0.32, 7.74), (0.54, 0.14))
            size = (6.75, 0.72)
        else:
            obj.add_box((cx, cy - 3.15), (0.72, 0.46), 3.35, 4.48, f"{name}_left_post", "InteriorTrim")
            obj.add_box((cx, cy + 3.15), (0.72, 0.46), 3.35, 4.48, f"{name}_right_post", "InteriorTrim")
            obj.add_box((cx, cy), (0.72, 6.75), 0.55, 7.62, f"{name}_lintel", "InteriorTrim")
            obj.add_box((cx - sign * 0.18, cy), (0.16, 5.65), 0.42, 7.12, f"{name}_inner_shadow_line", "BrassRail")
            for side_label, y_offset in [("left", -2.08), ("right", 2.08)]:
                inlay_name = f"{name}_{side_label}_spandrel_inlay"
                obj.add_box((cx - sign * 0.28, cy + y_offset), (0.105, 1.12), 0.42, 7.04, inlay_name, "ArtFrameGold")
                add_rotunda_detail(inlay_name, "arch_spandrel_inlay", (cx - sign * 0.28, cy + y_offset, 7.25), (0.105, 1.12))
            keystone_name = f"{name}_keystone_block"
            obj.add_box((cx - sign * 0.32, cy), (0.14, 0.54), 0.72, 7.38, keystone_name, "ColumnStone")
            add_rotunda_detail(keystone_name, "arch_keystone_block", (cx - sign * 0.32, cy, 7.74), (0.14, 0.54))
            size = (0.72, 6.75)
        add_rotunda_detail(name, "public_arch_portal", (cx, cy, 6.1), size)

    obj.add_ring((0.0, 0.0), 13.05, 12.72, 8.72, 0.32, "rotunda_upper_balustrade_ring", "BrassRail", segments=96)
    add_rotunda_detail("rotunda_upper_balustrade_ring", "upper_balustrade", (0.0, 0.0, 8.88), (26.1, 26.1))
    obj.add_ring((0.0, 0.0), 4.85, 4.55, 9.22, 0.16, "rotunda_oculus_trim_ring", "ArtFrameGold", segments=96)
    add_rotunda_detail("rotunda_oculus_trim_ring", "oculus_trim_ring", (0.0, 0.0, 9.3), (9.7, 9.7))
    for idx in range(32):
        angle = math.tau * idx / 32.0
        x = 12.88 * math.cos(angle)
        y = 12.88 * math.sin(angle)
        name = f"rotunda_upper_balustrade_post_{idx+1:02d}"
        obj.add_cylinder((x, y), 0.075, 8.76, 0.62, name, "BrassRail", segments=10)
        add_rotunda_detail(name, "upper_balustrade_post", (x, y, 9.07), (0.15, 0.15))

    rotunda_statue_pedestals = [
        ("washington", 0.0),
        ("jackson", 60.0),
        ("garfield", 120.0),
        ("eisenhower", 180.0),
        ("reagan", 240.0),
        ("ford", 300.0),
        ("truman", 330.0),
    ]
    for label, degrees in rotunda_statue_pedestals:
        angle = math.radians(degrees)
        x = 11.2 * math.cos(angle)
        y = 11.2 * math.sin(angle)
        name = f"rotunda_{label}_statue_public_pedestal_base"
        obj.add_cylinder((x, y), 0.86, 4.41, 0.18, name, "StepStone", segments=20)
        plaque_center = (10.55 * math.cos(angle), 10.55 * math.sin(angle))
        plaque_size = (0.44, 0.08) if abs(math.sin(angle)) > abs(math.cos(angle)) else (0.08, 0.44)
        obj.add_box(plaque_center, plaque_size, 0.16, 4.63, f"rotunda_{label}_statue_public_pedestal_plaque", "BrassRail")
        add_rotunda_detail(name, "statue_pedestal_base", (x, y, 4.5), (1.72, 1.72))
        add_rotunda_detail(
            f"rotunda_{label}_statue_public_pedestal_plaque",
            "statue_pedestal_plaque",
            (plaque_center[0], plaque_center[1], 4.71),
            plaque_size,
        )

    add_label(labels, "Rotunda architectural details - public schematic", 0.0, 11.0, 7.2, "major_public_space")
    add_label(labels, "Rotunda dome interior ribs, coffers, frieze, and oculus light - schematic", 0.0, 7.0, 11.2, "major_public_space")


def add_statue_visual(
    obj: ObjWriter,
    records: list[dict[str, Any]],
    name: str,
    collection: str,
    location: str,
    center: tuple[float, float],
    material: str,
    public_accuracy: str = "schematic_public_art_marker",
    z: float = 4.45,
) -> None:
    x, y = center
    pose_variants = ("draped_robe", "book_slab", "scroll_marker", "raised_arm")
    pose_variant = pose_variants[int(stable_unit_interval(name, "pose_variant") * len(pose_variants)) % len(pose_variants)]
    surface_offset = stable_unit_interval(name, "surface_offset") - 0.5
    surface_material = "StoneGrimeOverlay" if material == "StatueMarble" else "FloorWear"
    obj.add_cylinder((x, y), 0.62, z, 0.34, f"{name}_plinth", "StepStone", segments=18)
    obj.add_cylinder((x, y), 0.34, z + 0.34, 1.28, f"{name}_body", material, segments=18)
    obj.add_cylinder((x, y), 0.20, z + 1.62, 0.28, f"{name}_head", material, segments=18)
    obj.add_cylinder((x, y), 0.72, z - 0.08, 0.10, f"{name}_plinth_base_step", "StepStone", segments=18)
    obj.add_cylinder((x, y), 0.54, z + 0.31, 0.12, f"{name}_plinth_cap", "StepStone", segments=18)
    obj.add_cylinder((x, y), 0.78, z - 0.16, 0.045, f"{name}_plinth_lower_shadow_bevel", "StoneGrimeOverlay", segments=18)
    obj.add_cylinder((x, y), 0.46, z + 0.44, 0.060, f"{name}_plinth_upper_profile_ring", "StepStone", segments=18)
    obj.add_box((x, y - 0.51), (0.72, 0.08), 0.18, z + 0.12, f"{name}_plinth_public_plaque", "BrassRail")
    obj.add_box((x, y - 0.57), (0.62, 0.05), 0.055, z + 0.33, f"{name}_plinth_inscription_bar", "BrassRail")
    obj.add_box((x, y), (0.82, 0.18), 0.18, z + 1.12, f"{name}_shoulder_silhouette", material)
    obj.add_box((x - 0.34, y), (0.12, 0.12), 0.72, z + 0.70, f"{name}_left_drape_fold", material)
    obj.add_box((x + 0.34, y), (0.12, 0.12), 0.72, z + 0.70, f"{name}_right_drape_fold", material)
    obj.add_cylinder((x, y), 0.23, z + 1.89, 0.035, f"{name}_head_top_highlight", material, segments=18)
    for fold_index, dx in enumerate([-0.18, 0.0, 0.18], start=1):
        obj.add_box((x + dx, y - 0.105), (0.046, 0.075), 0.82, z + 0.55, f"{name}_robe_fold_relief_{fold_index}", material)
    if pose_variant == "book_slab":
        obj.add_box((x + 0.31, y - 0.25), (0.34, 0.10), 0.22, z + 1.04, f"{name}_book_slab_marker", "StepStone")
        obj.add_box((x + 0.31, y - 0.31), (0.30, 0.036), 0.028, z + 1.24, f"{name}_book_page_groove", "BrassRail")
        accessory_hint = "book_slab"
    elif pose_variant == "scroll_marker":
        obj.add_cylinder((x - 0.28, y - 0.23), 0.055, z + 1.02, 0.34, f"{name}_scroll_cylinder_marker", material, segments=10)
        obj.add_box((x - 0.28, y - 0.30), (0.24, 0.045), 0.030, z + 1.18, f"{name}_scroll_edge_marker", "BrassRail")
        accessory_hint = "scroll_marker"
    elif pose_variant == "raised_arm":
        obj.add_box((x - 0.42, y - 0.02), (0.10, 0.12), 0.94, z + 0.98, f"{name}_raised_arm_silhouette", material)
        obj.add_box((x - 0.48, y - 0.02), (0.18, 0.12), 0.12, z + 1.86, f"{name}_raised_hand_marker", material)
        accessory_hint = "raised_arm"
    else:
        obj.add_box((x, y - 0.18), (0.56, 0.07), 0.56, z + 0.82, f"{name}_front_drape_panel", material)
        obj.add_box((x - 0.02, y - 0.235), (0.46, 0.040), 0.055, z + 1.30, f"{name}_drape_clasp_marker", "BrassRail")
        accessory_hint = "draped_robe"
    obj.add_box(
        (x - 0.10 + surface_offset * 0.18, y - 0.33),
        (0.14, 0.055),
        0.42,
        z + 0.72,
        f"{name}_surface_patina_patch",
        surface_material,
    )
    records.append(
        {
            "name": name,
            "type": "statue",
            "collection": collection,
            "location": location,
            "center_m": [round(x, 3), round(y, 3), round(z + 0.9, 3)],
            "material_hint": "bronze" if material == "StatueBronze" else "marble/stone",
            "public_accuracy": public_accuracy,
            "assignment": "Public-art visual marker. Not an exact current statue-by-statue placement unless explicitly named.",
        }
    )
    detail_specs = [
        ("plinth_detail", "statue_plinth_detail", (x, y, z + 0.18), "base_step/cap/plaque"),
        ("torso_silhouette", "statue_torso_silhouette", (x, y, z + 1.08), "shoulders/drape"),
        ("head_silhouette", "statue_head_silhouette", (x, y, z + 1.78), "head/highlight"),
        ("public_plaque", "statue_public_plaque", (x, y - 0.51, z + 0.21), "generic_public_label"),
        ("base_profile_detail", "statue_base_profile_detail", (x, y, z + 0.38), "stepped_plinth_profile"),
        ("pose_variant_marker", "statue_pose_variant_marker", (x, y - 0.18, z + 1.22), pose_variant),
        ("accessory_silhouette", "statue_accessory_silhouette", (x, y - 0.26, z + 1.18), accessory_hint),
        ("surface_detail", "statue_surface_detail", (x - 0.10 + surface_offset * 0.18, y - 0.33, z + 0.93), "patina_or_stone_wear_patch"),
    ]
    for suffix, art_type, detail_center, detail_hint in detail_specs:
        records.append(
            {
                "name": f"{name}_{suffix}",
                "type": art_type,
                "collection": collection,
                "location": location,
                "center_m": [round(detail_center[0], 3), round(detail_center[1], 3), round(detail_center[2], 3)],
                "material_hint": "bronze" if material == "StatueBronze" else "marble/stone",
                "public_accuracy": "schematic_public_art_detail",
                "detail_hint": detail_hint,
                "pose_variant": pose_variant,
                "assignment": "Generic sculptural-detail silhouette for public visual realism; not an exact artwork reconstruction.",
            }
        )


def add_wall_art_visual(
    obj: ObjWriter,
    records: list[dict[str, Any]],
    name: str,
    art_type: str,
    location: str,
    center: tuple[float, float],
    size: tuple[float, float],
    facing_axis: str,
    material: str,
    z: float = 5.85,
    public_accuracy: str = "schematic_public_art_marker",
    metadata: dict[str, Any] | None = None,
) -> None:
    x, y = center
    width, height = size
    if facing_axis == "x":
        obj.add_box((x, y), (0.16, width + 0.34), height + 0.34, z - height / 2.0, f"{name}_frame", "ArtFrameGold")
        obj.add_box((x, y), (0.18, width), height, z - height / 2.0 + 0.08, f"{name}_canvas", material)
        obj.add_box((x, y), (0.19, width + 0.16), 0.10, z + height / 2.0 + 0.04, f"{name}_top_inner_bevel", "ArtFrameGold")
        obj.add_box((x, y), (0.19, width + 0.16), 0.10, z - height / 2.0 - 0.08, f"{name}_bottom_inner_bevel", "ArtFrameGold")
        obj.add_box((x, y - width * 0.22), (0.20, width * 0.34), height * 0.16, z + height * 0.10, f"{name}_canvas_mid_tone_patch", "PaintingCanvas")
        obj.add_box((x, y + width * 0.26), (0.20, width * 0.22), height * 0.10, z - height * 0.18, f"{name}_canvas_dark_tone_patch", "PortraitCanvas")
        obj.add_box((x, y), (0.20, min(width * 0.55, 1.1)), 0.08, z - height / 2.0 - 0.38, f"{name}_small_label_plaque", "BrassRail")
    else:
        obj.add_box((x, y), (width + 0.34, 0.16), height + 0.34, z - height / 2.0, f"{name}_frame", "ArtFrameGold")
        obj.add_box((x, y), (width, 0.18), height, z - height / 2.0 + 0.08, f"{name}_canvas", material)
        obj.add_box((x, y), (width + 0.16, 0.19), 0.10, z + height / 2.0 + 0.04, f"{name}_top_inner_bevel", "ArtFrameGold")
        obj.add_box((x, y), (width + 0.16, 0.19), 0.10, z - height / 2.0 - 0.08, f"{name}_bottom_inner_bevel", "ArtFrameGold")
        obj.add_box((x - width * 0.22, y), (width * 0.34, 0.20), height * 0.16, z + height * 0.10, f"{name}_canvas_mid_tone_patch", "PaintingCanvas")
        obj.add_box((x + width * 0.26, y), (width * 0.22, 0.20), height * 0.10, z - height * 0.18, f"{name}_canvas_dark_tone_patch", "PortraitCanvas")
        obj.add_box((x, y), (min(width * 0.55, 1.1), 0.20), 0.08, z - height / 2.0 - 0.38, f"{name}_small_label_plaque", "BrassRail")
    art_record: dict[str, Any] = {
        "name": name,
        "type": art_type,
        "location": location,
        "center_m": [round(x, 3), round(y, 3), round(z, 3)],
        "size_m": [round(width, 3), round(height, 3)],
        "public_accuracy": public_accuracy,
        "assignment": "Schematic public-art panel, not an exact artwork inventory record.",
    }
    if metadata:
        art_record.update(metadata)
    records.append(art_record)
    detail_specs = [
        ("inner_bevel", "art_frame_inner_bevel", (x, y, z), {"facing_axis": facing_axis}),
        ("canvas_tone_patches", "art_canvas_tone_patch", (x, y, z), {"patch_count": 2, "facing_axis": facing_axis}),
        ("label_plaque", "art_label_plaque", (x, y, z - height / 2.0 - 0.34), {"facing_axis": facing_axis}),
    ]
    for suffix, detail_type, detail_center, extra in detail_specs:
        record: dict[str, Any] = {
            "name": f"{name}_{suffix}",
            "type": detail_type,
            "location": location,
            "center_m": [round(detail_center[0], 3), round(detail_center[1], 3), round(detail_center[2], 3)],
            "size_m": [round(width, 3), round(height, 3)],
            "public_accuracy": "schematic_public_art_detail",
            "assignment": "Generic frame/canvas detail for public visual realism; not an exact artwork reconstruction.",
        }
        record.update(extra)
        if metadata and metadata.get("title"):
            record["source_title"] = metadata["title"]
        records.append(record)
    if metadata and metadata.get("title"):
        records.append(
            {
                "name": f"{name}_named_title_plaque",
                "type": "historical_painting_title_plaque",
                "location": location,
                "center_m": [round(x, 3), round(y, 3), round(z - height / 2.0 - 0.34, 3)],
                "size_m": [round(min(width * 0.55, 1.1), 3), 0.2],
                "title": metadata["title"],
                "artist": metadata.get("artist", ""),
                "public_accuracy": "named_public_rotunda_painting_schematic_marker",
                "assignment": "Public title-plaque marker for an AOC-listed Rotunda painting; schematic placement only.",
            }
        )


def add_light_fixture_detail_record(
    records: list[dict[str, Any]],
    name: str,
    kind: str,
    fixture_name: str,
    fixture_type: str,
    location: str,
    center: tuple[float, float, float],
    extra: dict[str, Any] | None = None,
) -> None:
    record: dict[str, Any] = {
        "name": name,
        "kind": kind,
        "fixture_name": fixture_name,
        "fixture_type": fixture_type,
        "location": location,
        "center_m": [round(center[0], 3), round(center[1], 3), round(center[2], 3)],
        "public_accuracy": "schematic_public_light_fixture_detail",
        "assignment": "Decorative visible fixture geometry only; spawned light metadata remains in light_fixtures.",
    }
    if extra:
        record.update(extra)
    records.append(record)


def add_light_fixture(
    obj: ObjWriter,
    fixtures: list[dict[str, Any]],
    fixture_details: list[dict[str, Any]],
    name: str,
    fixture_type: str,
    location: str,
    center: tuple[float, float],
    z: float,
    intensity: float,
    radius: float,
) -> None:
    x, y = center
    if fixture_type == "chandelier":
        obj.add_cylinder((x, y), 0.10, z + 0.18, 0.45, f"{name}_ceiling_chain", "LightFixtureMetal", segments=10)
        obj.add_cylinder((x, y), 0.28, z + 0.61, 0.045, f"{name}_stepped_ceiling_canopy_outer", "LightFixtureMetal", segments=20)
        obj.add_cylinder((x, y), 0.22, z + 0.58, 0.06, f"{name}_ceiling_canopy", "LightFixtureMetal", segments=16)
        obj.add_cylinder((x, y), 0.13, z + 0.50, 0.045, f"{name}_ceiling_canopy_inner_ring", "BrassRail", segments=16)
        obj.add_cylinder((x, y), 0.48, z - 0.16, 0.18, f"{name}_metal_ring", "LightFixtureMetal", segments=24)
        obj.add_cylinder((x, y), 0.54, z - 0.04, 0.040, f"{name}_upper_trim_ring", "BrassRail", segments=24)
        obj.add_cylinder((x, y), 0.12, z - 0.78, 0.12, f"{name}_center_finial", "BrassRail", segments=14)
        for idx in range(6):
            angle = math.tau * idx / 6.0
            px = x + 0.42 * math.cos(angle)
            py = y + 0.42 * math.sin(angle)
            obj.add_oriented_box((x + 0.21 * math.cos(angle), y + 0.21 * math.sin(angle)), (0.42, 0.045), 0.045, z - 0.20, angle, f"{name}_radial_arm_{idx+1}", "LightFixtureMetal")
            obj.add_oriented_box((x + 0.36 * math.cos(angle), y + 0.36 * math.sin(angle)), (0.18, 0.026), 0.030, z - 0.34, angle, f"{name}_glass_shade_rib_{idx+1}", "BrassRail")
            obj.add_cylinder((px, py), 0.13, z - 0.26, 0.040, f"{name}_glass_cup_trim_{idx+1}", "BrassRail", segments=12)
            obj.add_cylinder((px, py), 0.10, z - 0.55, 0.32, f"{name}_glass_bulb_{idx+1}", "WarmLightGlass", segments=12)
        add_light_fixture_detail_record(fixture_details, f"{name}_ceiling_chain_detail", "chandelier_chain", name, fixture_type, location, (x, y, z + 0.40))
        add_light_fixture_detail_record(fixture_details, f"{name}_armature_detail", "chandelier_armature", name, fixture_type, location, (x, y, z - 0.16), {"arm_count": 6})
        add_light_fixture_detail_record(fixture_details, f"{name}_glass_bulb_detail", "chandelier_glass_bulb_cluster", name, fixture_type, location, (x, y, z - 0.40), {"bulb_count": 6})
        add_light_fixture_detail_record(fixture_details, f"{name}_beveled_mount_detail", "fixture_beveled_mount", name, fixture_type, location, (x, y, z + 0.58))
        add_light_fixture_detail_record(fixture_details, f"{name}_trim_ring_detail", "fixture_glass_trim_ring", name, fixture_type, location, (x, y, z - 0.04))
        add_light_fixture_detail_record(fixture_details, f"{name}_finial_detail", "fixture_finial_detail", name, fixture_type, location, (x, y, z - 0.72))
        for idx in range(6):
            angle = math.tau * idx / 6.0
            add_light_fixture_detail_record(
                fixture_details,
                f"{name}_glass_shade_rib_detail_{idx+1}",
                "fixture_glass_shade_rib",
                name,
                fixture_type,
                location,
                (x + 0.36 * math.cos(angle), y + 0.36 * math.sin(angle), z - 0.32),
            )
    elif fixture_type == "sconce":
        obj.add_beveled_box((x, y), (0.35, 0.12), 0.55, z - 0.28, f"{name}_sconce_backplate", "LightFixtureMetal", 0.018)
        obj.add_beveled_box((x, y), (0.44, 0.15), 0.08, z + 0.24, f"{name}_sconce_top_cap", "BrassRail", 0.014)
        obj.add_beveled_box((x, y), (0.44, 0.15), 0.08, z - 0.40, f"{name}_sconce_bottom_cap", "BrassRail", 0.014)
        obj.add_cylinder((x, y), 0.15, z + 0.19, 0.035, f"{name}_sconce_glass_top_trim", "BrassRail", segments=12)
        obj.add_cylinder((x, y), 0.15, z - 0.39, 0.035, f"{name}_sconce_glass_bottom_trim", "BrassRail", segments=12)
        obj.add_cylinder((x, y), 0.13, z - 0.12, 0.32, f"{name}_sconce_glass", "WarmLightGlass", segments=12)
        obj.add_oriented_box((x - 0.11, y), (0.14, 0.022), 0.030, z - 0.03, 0.0, f"{name}_sconce_glass_left_rib", "BrassRail")
        obj.add_oriented_box((x + 0.11, y), (0.14, 0.022), 0.030, z - 0.03, 0.0, f"{name}_sconce_glass_right_rib", "BrassRail")
        obj.add_cylinder((x, y), 0.07, z - 0.52, 0.08, f"{name}_sconce_lower_finial", "BrassRail", segments=10)
        add_light_fixture_detail_record(fixture_details, f"{name}_backplate_detail", "sconce_backplate_detail", name, fixture_type, location, (x, y, z - 0.02))
        add_light_fixture_detail_record(fixture_details, f"{name}_glass_shade_detail", "sconce_glass_shade_detail", name, fixture_type, location, (x, y, z + 0.04))
        add_light_fixture_detail_record(fixture_details, f"{name}_beveled_mount_detail", "fixture_beveled_mount", name, fixture_type, location, (x, y, z - 0.02))
        add_light_fixture_detail_record(fixture_details, f"{name}_trim_ring_detail", "fixture_glass_trim_ring", name, fixture_type, location, (x, y, z - 0.10))
        add_light_fixture_detail_record(fixture_details, f"{name}_glass_rib_detail", "fixture_glass_shade_rib", name, fixture_type, location, (x, y, z - 0.03), {"rib_count": 2})
        add_light_fixture_detail_record(fixture_details, f"{name}_finial_detail", "fixture_finial_detail", name, fixture_type, location, (x, y, z - 0.48))
    else:
        obj.add_cylinder((x, y), 0.26, z + 0.55, 0.040, f"{name}_pendant_canopy_outer_step", "LightFixtureMetal", segments=20)
        obj.add_cylinder((x, y), 0.21, z + 0.50, 0.065, f"{name}_pendant_ceiling_canopy", "LightFixtureMetal", segments=16)
        obj.add_cylinder((x, y), 0.13, z + 0.43, 0.035, f"{name}_pendant_canopy_inner_ring", "BrassRail", segments=16)
        obj.add_cylinder((x, y), 0.30, z + 0.02, 0.040, f"{name}_pendant_upper_trim", "BrassRail", segments=16)
        obj.add_cylinder((x, y), 0.30, z - 0.28, 0.055, f"{name}_pendant_lower_trim", "BrassRail", segments=16)
        obj.add_cylinder((x, y), 0.26, z - 0.22, 0.32, f"{name}_pendant_glass", "WarmLightGlass", segments=16)
        obj.add_cylinder((x, y), 0.07, z + 0.10, 0.42, f"{name}_pendant_stem", "LightFixtureMetal", segments=10)
        for idx in range(4):
            angle = math.tau * idx / 4.0
            obj.add_oriented_box((x + 0.20 * math.cos(angle), y + 0.20 * math.sin(angle)), (0.15, 0.026), 0.030, z - 0.08, angle, f"{name}_pendant_shade_rib_{idx+1}", "BrassRail")
        obj.add_cylinder((x, y), 0.08, z - 0.42, 0.085, f"{name}_pendant_bottom_finial", "BrassRail", segments=12)
        add_light_fixture_detail_record(fixture_details, f"{name}_canopy_detail", "pendant_canopy_detail", name, fixture_type, location, (x, y, z + 0.53))
        add_light_fixture_detail_record(fixture_details, f"{name}_glass_shade_detail", "pendant_glass_shade_detail", name, fixture_type, location, (x, y, z - 0.06))
        add_light_fixture_detail_record(fixture_details, f"{name}_beveled_mount_detail", "fixture_beveled_mount", name, fixture_type, location, (x, y, z + 0.50))
        add_light_fixture_detail_record(fixture_details, f"{name}_trim_ring_detail", "fixture_glass_trim_ring", name, fixture_type, location, (x, y, z - 0.13))
        add_light_fixture_detail_record(fixture_details, f"{name}_glass_rib_detail", "fixture_glass_shade_rib", name, fixture_type, location, (x, y, z - 0.08), {"rib_count": 4})
        add_light_fixture_detail_record(fixture_details, f"{name}_finial_detail", "fixture_finial_detail", name, fixture_type, location, (x, y, z - 0.38))
    fixtures.append(
        {
            "name": name,
            "type": fixture_type,
            "location": location,
            "center_m": [round(x, 3), round(y, 3), round(z, 3)],
            "intensity": intensity,
            "attenuation_radius_m": radius,
            "color": [1.0, 0.82, 0.52],
            "public_accuracy": "schematic_public_lighting",
        }
    )


def add_public_art_and_lighting(
    obj: ObjWriter,
    labels: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    art: list[dict[str, Any]] = []
    lights: list[dict[str, Any]] = []
    light_details: list[dict[str, Any]] = []

    # Named Rotunda presidential statues are public AOC-listed objects. Their
    # exact in-room positions are schematic here.
    rotunda_statues = [
        ("rotunda_washington_statue", "George Washington statue", "StatueMarble", 0.0),
        ("rotunda_jackson_statue", "Andrew Jackson statue", "StatueBronze", 60.0),
        ("rotunda_garfield_statue", "James A. Garfield statue", "StatueMarble", 120.0),
        ("rotunda_eisenhower_statue", "Dwight D. Eisenhower statue", "StatueBronze", 180.0),
        ("rotunda_reagan_statue", "Ronald Reagan statue", "StatueBronze", 240.0),
        ("rotunda_ford_statue", "Gerald Ford statue", "StatueBronze", 300.0),
        ("rotunda_truman_statue", "Harry S. Truman statue", "StatueBronze", 330.0),
    ]
    for name, label, material, degrees in rotunda_statues:
        angle = math.radians(degrees)
        add_statue_visual(
            obj,
            art,
            name,
            "Rotunda public statuary",
            "Rotunda",
            (11.2 * math.cos(angle), 11.2 * math.sin(angle)),
            material,
            public_accuracy="named_public_rotunda_statue_schematic_position",
        )
    add_label(labels, "Rotunda presidential statues - schematic public markers", 0.0, -11.2, 7.4, "public_art")

    # Rotunda historical paintings are public AOC-listed works. Positions are
    # schematic public markers, not exact artwork conservation records.
    rotunda_paintings = [
        ("Declaration of Independence", "John Trumbull"),
        ("Surrender of General Burgoyne", "John Trumbull"),
        ("Surrender of Lord Cornwallis", "John Trumbull"),
        ("General George Washington Resigning His Commission", "John Trumbull"),
        ("Landing of Columbus", "John Vanderlyn"),
        ("Discovery of the Mississippi by De Soto", "William Henry Powell"),
        ("Baptism of Pocahontas", "John Gadsby Chapman"),
        ("Embarkation of the Pilgrims", "Robert Walter Weir"),
    ]
    for idx, (title, artist) in enumerate(rotunda_paintings):
        angle = math.tau * idx / 8.0 + math.pi / 8.0
        x = 14.95 * math.cos(angle)
        y = 14.95 * math.sin(angle)
        facing_axis = "x" if abs(math.cos(angle)) > abs(math.sin(angle)) else "y"
        add_wall_art_visual(
            obj,
            art,
            f"rotunda_historical_painting_panel_{idx+1}",
            "historical_painting_panel",
            "Rotunda",
            (x, y),
            (3.2, 2.1),
            facing_axis,
            "PaintingCanvas",
            z=6.75,
            public_accuracy="named_public_rotunda_painting_schematic_marker",
            metadata={
                "title": title,
                "artist": artist,
                "collection": "U.S. Capitol Rotunda historical paintings",
                "source": "Architect of the Capitol public Rotunda materials",
            },
        )
    add_label(labels, "Rotunda historical painting panels - schematic", 0.0, 14.0, 7.7, "public_art")

    for idx in range(16):
        angle = math.tau * idx / 16.0
        x = 14.88 * math.cos(angle)
        y = 14.88 * math.sin(angle)
        facing_axis = "x" if abs(math.cos(angle)) > abs(math.sin(angle)) else "y"
        add_wall_art_visual(
            obj,
            art,
            f"rotunda_frieze_relief_panel_{idx+1:02d}",
            "rotunda_frieze_relief_panel",
            "Rotunda",
            (x, y),
            (1.75, 0.72),
            facing_axis,
            "PaintingCanvas",
            z=8.65,
            public_accuracy="schematic_public_rotunda_frieze_marker",
        )

    # National Statuary Hall and nearby public statuary zones.
    for idx in range(18):
        row = idx // 6
        col = idx % 6
        x = 17.5 + col * 4.2
        y = -37.0 + row * 7.0
        add_statue_visual(
            obj,
            art,
            f"national_statuary_hall_marker_{idx+1:02d}",
            "National Statuary Hall Collection",
            "National Statuary Hall",
            (x, y),
            "StatueMarble" if idx % 3 else "StatueBronze",
        )
    add_label(labels, "National Statuary Hall collection markers - schematic", 28.0, -22.0, 7.1, "public_art")

    for idx, x in enumerate([17.5, 20.5, 23.5, 26.5, 29.5, 32.5, 35.5, 38.5], start=1):
        add_wall_art_visual(
            obj,
            art,
            f"statuary_hall_wall_art_panel_{idx:02d}",
            "public_hall_art_panel",
            "National Statuary Hall",
            (x, -20.2 if idx % 2 else -39.8),
            (1.35, 1.85),
            "y",
            "PortraitCanvas",
            z=6.05,
        )

    for idx in range(10):
        angle = math.tau * idx / 10.0
        add_statue_visual(
            obj,
            art,
            f"crypt_statuary_marker_{idx+1:02d}",
            "National Statuary Hall Collection",
            "Crypt / public statuary marker",
            (9.0 * math.cos(angle), -24.0 + 4.0 * math.sin(angle)),
            "StatueMarble" if idx % 2 else "StatueBronze",
        )

    for idx, x in enumerate([-58.5, -55.0, -51.5, 51.5, 55.0, 58.5], start=1):
        add_wall_art_visual(
            obj,
            art,
            f"public_corridor_portrait_panel_{idx:02d}",
            "portrait_panel",
            "Public circulation / schematic corridor",
            (x, -18.0 if idx <= 3 else 18.0),
            (1.5, 2.1),
            "x",
            "PortraitCanvas",
            z=6.15,
        )

    for idx, x in enumerate([18.5, 22.5, 26.5, 30.5, 34.5, 38.5], start=1):
        add_wall_art_visual(
            obj,
            art,
            f"old_senate_chamber_wall_art_panel_{idx:02d}",
            "historic_chamber_art_panel",
            "Old Senate Chamber",
            (x, 21.2 if idx % 2 else 38.8),
            (1.25, 1.75),
            "y",
            "PortraitCanvas",
            z=6.0,
        )

    for idx, x in enumerate([-24.0, -16.0, -8.0, 8.0, 16.0, 24.0], start=1):
        add_wall_art_visual(
            obj,
            art,
            f"house_chamber_portrait_panel_{idx:02d}",
            "portrait_panel",
            "House Chamber public wall visual",
            (x, -51.4),
            (1.4, 1.9),
            "y",
            "PortraitCanvas",
            z=6.25,
        )
        add_wall_art_visual(
            obj,
            art,
            f"senate_chamber_portrait_panel_{idx:02d}",
            "portrait_panel",
            "Senate Chamber public wall visual",
            (x, 85.6),
            (1.4, 1.9),
            "y",
            "PortraitCanvas",
            z=6.25,
        )

    # Warm public lighting. Unreal importer can spawn actual lights from this
    # metadata; mesh geometry keeps them visible in OBJ/browser preview.
    add_light_fixture(obj, lights, light_details, "rotunda_center_chandelier", "chandelier", "Rotunda", (0.0, 0.0), 9.1, 2600.0, 16.0)
    for idx in range(8):
        angle = math.tau * idx / 8.0
        add_light_fixture(
            obj,
            lights,
            light_details,
            f"rotunda_perimeter_sconce_{idx+1:02d}",
            "sconce",
            "Rotunda",
            (13.2 * math.cos(angle), 13.2 * math.sin(angle)),
            7.4,
            650.0,
            7.0,
        )

    for idx, x in enumerate([-20.0, -10.0, 0.0, 10.0, 20.0], start=1):
        add_light_fixture(obj, lights, light_details, f"house_chamber_pendant_{idx:02d}", "pendant", "House Chamber", (x, -72.0), 8.2, 900.0, 9.0)
        add_light_fixture(obj, lights, light_details, f"senate_chamber_pendant_{idx:02d}", "pendant", "Senate Chamber", (x * 0.75, 68.0), 8.2, 850.0, 8.0)

    for idx, y in enumerate([-87.0, -80.5, -74.0, -67.5, -61.0], start=1):
        add_light_fixture(obj, lights, light_details, f"house_west_wall_sconce_{idx:02d}", "sconce", "House Chamber", (-30.2, y), 7.0, 560.0, 6.8)
        add_light_fixture(obj, lights, light_details, f"house_east_wall_sconce_{idx:02d}", "sconce", "House Chamber", (30.2, y), 7.0, 560.0, 6.8)

    for idx, y in enumerate([58.0, 64.5, 71.0, 77.5], start=1):
        add_light_fixture(obj, lights, light_details, f"senate_west_wall_sconce_{idx:02d}", "sconce", "Senate Chamber", (-23.2, y), 7.0, 540.0, 6.4)
        add_light_fixture(obj, lights, light_details, f"senate_east_wall_sconce_{idx:02d}", "sconce", "Senate Chamber", (23.2, y), 7.0, 540.0, 6.4)

    for idx, x in enumerate([-24.0, -8.0, 8.0, 24.0], start=1):
        add_light_fixture(obj, lights, light_details, f"house_gallery_sconce_{idx:02d}", "sconce", "House galleries", (x, -100.9), 6.85, 440.0, 5.4)
        add_light_fixture(obj, lights, light_details, f"senate_gallery_sconce_{idx:02d}", "sconce", "Senate galleries", (x * 0.78, 98.8), 6.85, 420.0, 5.2)

    transition_light_specs = [
        ("west_public_approach_transition_light", "West terrace public orientation marker", (-55.0, 0.0), 6.92, 520.0, 5.8),
        ("east_public_approach_transition_light", "East public approach / visitor circulation", (55.0, 0.0), 6.92, 520.0, 5.8),
        ("statuary_transition_light", "Rotunda / National Statuary Hall", (16.2, -15.8), 6.96, 460.0, 5.2),
        ("old_senate_transition_light", "Rotunda / Old Senate Chamber", (16.2, 15.8), 6.96, 460.0, 5.2),
        ("house_transition_light", "Rotunda / House Chamber orientation", (0.0, -51.0), 7.00, 560.0, 6.0),
        ("senate_transition_light", "Rotunda / Senate Chamber orientation", (0.0, 51.0), 7.00, 540.0, 5.8),
        ("house_gallery_transition_light", "House Chamber / public gallery", (0.0, -91.0), 6.92, 430.0, 5.0),
        ("senate_gallery_transition_light", "Senate Chamber / public gallery", (0.0, 89.0), 6.92, 420.0, 5.0),
    ]
    for name, location, center, z, intensity, radius in transition_light_specs:
        add_light_fixture(obj, lights, light_details, name, "pendant", location, center, z, intensity, radius)

    for idx, x in enumerate([20.0, 28.0, 36.0], start=1):
        add_light_fixture(obj, lights, light_details, f"statuary_hall_pendant_{idx:02d}", "pendant", "National Statuary Hall", (x, -30.0), 7.8, 720.0, 7.0)
        add_light_fixture(obj, lights, light_details, f"old_senate_chamber_pendant_{idx:02d}", "pendant", "Old Senate Chamber", (x, 30.0), 7.8, 680.0, 6.5)

    for idx, (x, y) in enumerate([(-53.0, -55.0), (53.0, -55.0), (-52.0, 55.0), (52.0, 55.0)], start=1):
        add_light_fixture(obj, lights, light_details, f"generic_office_zone_light_{idx:02d}", "pendant", "Generic office/support zone", (x, y), 7.2, 550.0, 6.0)

    add_label(labels, "Warm public lighting fixtures - schematic", 0.0, 6.5, 9.7, "lighting")
    return art, lights, light_details


def add_wall_treatment(
    obj: ObjWriter,
    records: list[dict[str, Any]],
    name: str,
    room: str,
    center: tuple[float, float],
    size: tuple[float, float],
    panel_count_long: int,
    panel_count_short: int,
    z: float = 4.55,
) -> None:
    cx, cy = center
    sx, sy = size
    rail_z = z + 1.45
    picture_rail_z = z + 2.55
    lower_panel_z = z + 0.46

    # Rails on all four walls.
    obj.add_box((cx, cy + sy / 2.0 - 0.08), (sx * 0.96, 0.10), 0.12, rail_z, f"{name}_north_chair_rail", "InteriorTrim")
    obj.add_box((cx, cy - sy / 2.0 + 0.08), (sx * 0.96, 0.10), 0.12, rail_z, f"{name}_south_chair_rail", "InteriorTrim")
    obj.add_box((cx + sx / 2.0 - 0.08, cy), (0.10, sy * 0.96), 0.12, rail_z, f"{name}_east_chair_rail", "InteriorTrim")
    obj.add_box((cx - sx / 2.0 + 0.08, cy), (0.10, sy * 0.96), 0.12, rail_z, f"{name}_west_chair_rail", "InteriorTrim")
    obj.add_box((cx, cy + sy / 2.0 - 0.10), (sx * 0.94, 0.08), 0.10, picture_rail_z, f"{name}_north_picture_rail", "ArtFrameGold")
    obj.add_box((cx, cy - sy / 2.0 + 0.10), (sx * 0.94, 0.08), 0.10, picture_rail_z, f"{name}_south_picture_rail", "ArtFrameGold")
    obj.add_box((cx + sx / 2.0 - 0.10, cy), (0.08, sy * 0.94), 0.10, picture_rail_z, f"{name}_east_picture_rail", "ArtFrameGold")
    obj.add_box((cx - sx / 2.0 + 0.10, cy), (0.08, sy * 0.94), 0.10, picture_rail_z, f"{name}_west_picture_rail", "ArtFrameGold")

    for index in range(panel_count_long):
        x = cx - sx / 2.0 + sx * (index + 0.5) / panel_count_long
        panel_w = sx / panel_count_long * 0.58
        obj.add_box((x, cy + sy / 2.0 - 0.16), (panel_w, 0.10), 0.82, lower_panel_z, f"{name}_north_wainscot_panel_{index+1}", "InteriorTrim")
        obj.add_box((x, cy - sy / 2.0 + 0.16), (panel_w, 0.10), 0.82, lower_panel_z, f"{name}_south_wainscot_panel_{index+1}", "InteriorTrim")
    for index in range(panel_count_short):
        y = cy - sy / 2.0 + sy * (index + 0.5) / panel_count_short
        panel_w = sy / panel_count_short * 0.58
        obj.add_box((cx + sx / 2.0 - 0.16, y), (0.10, panel_w), 0.82, lower_panel_z, f"{name}_east_wainscot_panel_{index+1}", "InteriorTrim")
        obj.add_box((cx - sx / 2.0 + 0.16, y), (0.10, panel_w), 0.82, lower_panel_z, f"{name}_west_wainscot_panel_{index+1}", "InteriorTrim")

    records.append(
        {
            "name": name,
            "room": room,
            "type": "wainscot_and_picture_rail",
            "center_m": [round(cx, 3), round(cy, 3), round(z, 3)],
            "size_m": [round(sx, 3), round(sy, 3)],
            "panel_count": panel_count_long * 2 + panel_count_short * 2,
            "public_accuracy": "schematic_interior_finish",
        }
    )


def add_wall_finish_detail_record(
    records: list[dict[str, Any]],
    name: str,
    kind: str,
    room: str,
    center: tuple[float, float, float],
    size: tuple[float, float] | None = None,
) -> None:
    record: dict[str, Any] = {
        "name": name,
        "kind": kind,
        "room": room,
        "center_m": [round(center[0], 3), round(center[1], 3), round(center[2], 3)],
        "public_accuracy": "schematic_public_interior_wall_finish_detail",
        "assignment": (
            "Public visual wall/trim finish detail only; not a restricted room, "
            "security feature, staff location, or operational access map."
        ),
    }
    if size is not None:
        record["size_m"] = [round(size[0], 3), round(size[1], 3)]
    records.append(record)


def add_public_interior_wall_finish_details(
    obj: ObjWriter,
    labels: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> None:
    panel_bottom_z = 4.58
    panel_height = 0.86
    baseboard_z = 4.42
    pilaster_z = 4.50
    upper_z = 6.34
    picture_rail_z = 7.20
    decorative_panel_z = 6.46
    decorative_panel_height = 0.44
    architrave_z = 4.50
    architrave_height = 2.28

    def add_baseboard(name: str, room: str, center: tuple[float, float], size: tuple[float, float]) -> None:
        obj.add_beveled_box(center, size, 0.18, baseboard_z, f"{name}_baseboard", "InteriorTrim", 0.014)
        add_wall_finish_detail_record(records, name, "baseboard", room, (center[0], center[1], baseboard_z + 0.09), size)

    def add_pilaster(name: str, room: str, center: tuple[float, float], size: tuple[float, float]) -> None:
        obj.add_beveled_box(center, (size[0] * 1.55, size[1] * 1.55), 0.16, pilaster_z - 0.02, f"{name}_base", "ArtFrameGold", 0.012)
        obj.add_beveled_box(center, size, 2.35, pilaster_z, f"{name}_shaft", "InteriorTrim", 0.014)
        obj.add_beveled_box(center, (size[0] * 1.45, size[1] * 1.45), 0.18, pilaster_z + 2.32, f"{name}_cap", "ArtFrameGold", 0.012)
        add_wall_finish_detail_record(records, name, "wall_pilaster", room, (center[0], center[1], pilaster_z + 1.18), size)

    def add_frame(
        name: str,
        room: str,
        center: tuple[float, float],
        width: float,
        orientation: str,
        kind: str,
        bottom_z: float,
        height: float,
        material: str,
    ) -> None:
        x, y = center
        thickness = 0.055
        wall_depth = 0.11
        if orientation == "east_west":
            top_size = (width, wall_depth)
            side_size = (thickness, wall_depth)
            obj.add_beveled_box((x, y), top_size, 0.065, bottom_z, f"{name}_bottom_rail", material, 0.012)
            obj.add_beveled_box((x, y), top_size, 0.065, bottom_z + height, f"{name}_top_rail", material, 0.012)
            obj.add_beveled_box((x - width / 2.0, y), side_size, height, bottom_z, f"{name}_left_stile", material, 0.010)
            obj.add_beveled_box((x + width / 2.0, y), side_size, height, bottom_z, f"{name}_right_stile", material, 0.010)
            size = (width, wall_depth)
        else:
            top_size = (wall_depth, width)
            side_size = (wall_depth, thickness)
            obj.add_beveled_box((x, y), top_size, 0.065, bottom_z, f"{name}_bottom_rail", material, 0.012)
            obj.add_beveled_box((x, y), top_size, 0.065, bottom_z + height, f"{name}_top_rail", material, 0.012)
            obj.add_beveled_box((x, y - width / 2.0), side_size, height, bottom_z, f"{name}_left_stile", material, 0.010)
            obj.add_beveled_box((x, y + width / 2.0), side_size, height, bottom_z, f"{name}_right_stile", material, 0.010)
            size = (wall_depth, width)
        add_wall_finish_detail_record(records, name, kind, room, (x, y, bottom_z + height / 2.0), size)
        add_wall_finish_detail_record(
            records,
            f"{name}_beveled_trim_profile",
            "beveled_wall_trim_profile",
            room,
            (x, y, bottom_z + height / 2.0),
            size,
        )

    def add_picture_rail(name: str, room: str, center: tuple[float, float], size: tuple[float, float]) -> None:
        obj.add_beveled_box(center, size, 0.11, picture_rail_z, name, "ArtFrameGold", 0.012)
        add_wall_finish_detail_record(
            records,
            name,
            "picture_rail",
            room,
            (center[0], center[1], picture_rail_z + 0.055),
            size,
        )

    def add_decorative_panel(
        name: str,
        room: str,
        center: tuple[float, float],
        width: float,
        orientation: str,
    ) -> None:
        x, y = center
        if orientation == "east_west":
            size = (width, 0.064)
        else:
            size = (0.064, width)
        obj.add_beveled_box((x, y), size, decorative_panel_height, decorative_panel_z, name, "RotundaWall", 0.010)
        add_wall_finish_detail_record(
            records,
            name,
            "decorative_wall_panel",
            room,
            (x, y, decorative_panel_z + decorative_panel_height / 2.0),
            size,
        )

    def add_material_variation_panel(
        name: str,
        room: str,
        center: tuple[float, float],
        width: float,
        orientation: str,
        material: str,
    ) -> None:
        x, y = center
        if orientation == "east_west":
            size = (width, 0.050)
        else:
            size = (0.050, width)
        obj.add_box((x, y), size, 0.34, 5.72, name, material)
        obj.add_box((x, y), (size[0] * 1.06, size[1] * 1.06), 0.035, 5.69, f"{name}_lower_reveal", "DoorMetal")
        add_wall_finish_detail_record(
            records,
            name,
            "wall_material_variation_panel",
            room,
            (x, y, 5.89),
            size,
        )

    def add_wall_surface_decal(
        name: str,
        room: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
        height: float,
        kind: str,
        material: str = "StoneGrimeOverlay",
    ) -> None:
        obj.add_box(center, size, height, z, name, material)
        add_wall_finish_detail_record(records, name, kind, room, (center[0], center[1], z + height / 2.0), size)

    def add_architrave(
        name: str,
        room: str,
        center: tuple[float, float],
        opening_width: float,
        orientation: str,
    ) -> None:
        x, y = center
        stile = 0.16
        depth = 0.15
        header_height = 0.18
        if orientation == "east_west":
            obj.add_beveled_box((x - opening_width / 2.0, y), (stile, depth), architrave_height, architrave_z, f"{name}_left_stile", "InteriorTrim", 0.014)
            obj.add_beveled_box((x + opening_width / 2.0, y), (stile, depth), architrave_height, architrave_z, f"{name}_right_stile", "InteriorTrim", 0.014)
            obj.add_beveled_box((x, y), (opening_width + stile * 2.0, depth), header_height, architrave_z + architrave_height, f"{name}_header", "ArtFrameGold", 0.016)
            size = (opening_width + stile * 2.0, depth)
        else:
            obj.add_beveled_box((x, y - opening_width / 2.0), (depth, stile), architrave_height, architrave_z, f"{name}_left_stile", "InteriorTrim", 0.014)
            obj.add_beveled_box((x, y + opening_width / 2.0), (depth, stile), architrave_height, architrave_z, f"{name}_right_stile", "InteriorTrim", 0.014)
            obj.add_beveled_box((x, y), (depth, opening_width + stile * 2.0), header_height, architrave_z + architrave_height, f"{name}_header", "ArtFrameGold", 0.016)
            size = (depth, opening_width + stile * 2.0)
        add_wall_finish_detail_record(
            records,
            name,
            "public_architrave_trim",
            room,
            (x, y, architrave_z + architrave_height / 2.0),
            size,
        )

    def wall_fixture_size(width: float, depth: float, orientation: str) -> tuple[float, float]:
        if orientation == "east_west":
            return (width, depth)
        return (depth, width)

    def wall_fixture_center(center: tuple[float, float], along_offset: float, orientation: str) -> tuple[float, float]:
        x, y = center
        if orientation == "east_west":
            return (x + along_offset, y)
        return (x, y + along_offset)

    def add_public_wall_glazing_assembly(
        name: str,
        room: str,
        center: tuple[float, float],
        width: float,
        orientation: str,
    ) -> None:
        x, y = center
        glass_size = wall_fixture_size(width, 0.058, orientation)
        obj.add_box(center, glass_size, 0.82, 5.72, f"{name}_public_glazing_panel", "DoorGlass")
        add_wall_finish_detail_record(records, f"{name}_public_glazing_panel", "public_wall_glazing_panel", room, (x, y, 6.13), glass_size)

        rail_size = wall_fixture_size(width + 0.18, 0.070, orientation)
        for rail_name, rail_z in [("bottom", 5.66), ("top", 6.52)]:
            obj.add_box(center, rail_size, 0.055, rail_z, f"{name}_{rail_name}_glazing_rail", "InteriorTrim")
            add_wall_finish_detail_record(
                records,
                f"{name}_{rail_name}_glazing_rail",
                "public_wall_glazing_mullion",
                room,
                (x, y, rail_z + 0.028),
                rail_size,
            )

        mullion_size = wall_fixture_size(0.055, 0.084, orientation)
        for mullion_index, along_offset in enumerate([-width / 2.0, 0.0, width / 2.0], start=1):
            mullion_center = wall_fixture_center(center, along_offset, orientation)
            obj.add_box(mullion_center, mullion_size, 0.86, 5.68, f"{name}_vertical_mullion_{mullion_index:02d}", "InteriorTrim")
            add_wall_finish_detail_record(
                records,
                f"{name}_vertical_mullion_{mullion_index:02d}",
                "public_wall_glazing_mullion",
                room,
                (mullion_center[0], mullion_center[1], 6.11),
                mullion_size,
            )

        drape_size = wall_fixture_size(0.20, 0.090, orientation)
        for side, along_offset in [("left", -width / 2.0 - 0.22), ("right", width / 2.0 + 0.22)]:
            drape_center = wall_fixture_center(center, along_offset, orientation)
            obj.add_box(drape_center, drape_size, 1.02, 5.58, f"{name}_{side}_drapery_panel", "PublicGallery")
            add_wall_finish_detail_record(
                records,
                f"{name}_{side}_drapery_panel",
                "public_drapery_panel",
                room,
                (drape_center[0], drape_center[1], 6.09),
                drape_size,
            )

        sill_size = wall_fixture_size(width + 0.42, 0.155, orientation)
        obj.add_box(center, sill_size, 0.070, 5.44, f"{name}_projecting_window_sill", "InteriorTrim")
        add_wall_finish_detail_record(records, f"{name}_projecting_window_sill", "public_window_sill", room, (x, y, 5.475), sill_size)

        radiator_size = wall_fixture_size(width * 0.86, 0.125, orientation)
        obj.add_box(center, radiator_size, 0.32, 4.74, f"{name}_low_wall_radiator_cover", "DoorMetal")
        add_wall_finish_detail_record(records, f"{name}_low_wall_radiator_cover", "public_low_wall_radiator_cover", room, (x, y, 4.90), radiator_size)
        for slat_index, slat_z in enumerate([4.84, 4.94, 5.04], start=1):
            slat_size = wall_fixture_size(width * 0.72, 0.032, orientation)
            obj.add_box(center, slat_size, 0.030, slat_z, f"{name}_radiator_grille_slat_{slat_index:02d}", "BrassRail")
            add_wall_finish_detail_record(
                records,
                f"{name}_radiator_grille_slat_{slat_index:02d}",
                "public_radiator_grille_slat",
                room,
                (x, y, slat_z + 0.015),
                slat_size,
            )

    def add_room_finish(
        name: str,
        room: str,
        center: tuple[float, float],
        size: tuple[float, float],
        panel_count_long: int,
        panel_count_short: int,
    ) -> None:
        cx, cy = center
        sx, sy = size
        north_y = cy + sy / 2.0 - 0.22
        south_y = cy - sy / 2.0 + 0.22
        east_x = cx + sx / 2.0 - 0.22
        west_x = cx - sx / 2.0 + 0.22

        add_baseboard(f"{name}_north", room, (cx, north_y), (sx * 0.96, 0.12))
        add_baseboard(f"{name}_south", room, (cx, south_y), (sx * 0.96, 0.12))
        add_baseboard(f"{name}_east", room, (east_x, cy), (0.12, sy * 0.96))
        add_baseboard(f"{name}_west", room, (west_x, cy), (0.12, sy * 0.96))
        add_picture_rail(f"{name}_north_picture_rail", room, (cx, north_y), (sx * 0.94, 0.09))
        add_picture_rail(f"{name}_south_picture_rail", room, (cx, south_y), (sx * 0.94, 0.09))
        add_picture_rail(f"{name}_east_picture_rail", room, (east_x, cy), (0.09, sy * 0.94))
        add_picture_rail(f"{name}_west_picture_rail", room, (west_x, cy), (0.09, sy * 0.94))
        add_wall_surface_decal(f"{name}_north_baseboard_grime_decal", room, (cx, north_y - 0.018), (sx * 0.86, 0.046), baseboard_z + 0.18, 0.072, "baseboard_grime_decal")
        add_wall_surface_decal(f"{name}_south_baseboard_grime_decal", room, (cx, south_y + 0.018), (sx * 0.86, 0.046), baseboard_z + 0.18, 0.072, "baseboard_grime_decal")
        add_wall_surface_decal(f"{name}_east_baseboard_grime_decal", room, (east_x - 0.018, cy), (0.046, sy * 0.86), baseboard_z + 0.18, 0.072, "baseboard_grime_decal")
        add_wall_surface_decal(f"{name}_west_baseboard_grime_decal", room, (west_x + 0.018, cy), (0.046, sy * 0.86), baseboard_z + 0.18, 0.072, "baseboard_grime_decal")
        add_wall_surface_decal(f"{name}_north_wall_patina_decal", room, (cx - sx * 0.20, north_y - 0.022), (sx * 0.22, 0.040), 5.34, 0.42, "wall_patina_decal")
        add_wall_surface_decal(f"{name}_south_wall_patina_decal", room, (cx + sx * 0.20, south_y + 0.022), (sx * 0.22, 0.040), 5.28, 0.38, "wall_patina_decal")
        add_wall_surface_decal(f"{name}_east_wall_patina_decal", room, (east_x - 0.022, cy + sy * 0.20), (0.040, sy * 0.22), 5.32, 0.40, "wall_patina_decal")
        add_wall_surface_decal(f"{name}_west_wall_patina_decal", room, (west_x + 0.022, cy - sy * 0.20), (0.040, sy * 0.22), 5.30, 0.38, "wall_patina_decal")

        for index in range(panel_count_long):
            x = cx - sx / 2.0 + sx * (index + 0.5) / panel_count_long
            width = sx / panel_count_long * 0.64
            add_frame(f"{name}_north_wainscot_frame_{index+1:02d}", room, (x, north_y), width, "east_west", "raised_wainscot_frame", panel_bottom_z, panel_height, "InteriorTrim")
            add_frame(f"{name}_south_wainscot_frame_{index+1:02d}", room, (x, south_y), width, "east_west", "raised_wainscot_frame", panel_bottom_z, panel_height, "InteriorTrim")
            if index % 3 == 1:
                rub_size = (width * 0.36, 0.044)
                add_wall_surface_decal(f"{name}_north_wainscot_rub_mark_{index+1:02d}", room, (x - width * 0.12, north_y - 0.030), rub_size, panel_bottom_z + 0.30, 0.055, "wainscot_rub_mark", "FloorWear")
                add_wall_surface_decal(f"{name}_south_wainscot_rub_mark_{index+1:02d}", room, (x + width * 0.10, south_y + 0.030), rub_size, panel_bottom_z + 0.24, 0.055, "wainscot_rub_mark", "FloorWear")
            if index % 2 == 0:
                upper_width = sx / panel_count_long * 0.72
                add_frame(f"{name}_north_upper_wall_frame_{index+1:02d}", room, (x, north_y), upper_width, "east_west", "upper_wall_panel_frame", upper_z, 0.72, "ArtFrameGold")
                add_frame(f"{name}_south_upper_wall_frame_{index+1:02d}", room, (x, south_y), upper_width, "east_west", "upper_wall_panel_frame", upper_z, 0.72, "ArtFrameGold")
                add_decorative_panel(f"{name}_north_decorative_wall_panel_{index+1:02d}", room, (x, north_y), upper_width * 0.70, "east_west")
                add_decorative_panel(f"{name}_south_decorative_wall_panel_{index+1:02d}", room, (x, south_y), upper_width * 0.70, "east_west")
        for index in range(panel_count_short):
            y = cy - sy / 2.0 + sy * (index + 0.5) / panel_count_short
            width = sy / panel_count_short * 0.64
            add_frame(f"{name}_east_wainscot_frame_{index+1:02d}", room, (east_x, y), width, "north_south", "raised_wainscot_frame", panel_bottom_z, panel_height, "InteriorTrim")
            add_frame(f"{name}_west_wainscot_frame_{index+1:02d}", room, (west_x, y), width, "north_south", "raised_wainscot_frame", panel_bottom_z, panel_height, "InteriorTrim")
            if index % 3 == 1:
                rub_size = (0.044, width * 0.36)
                add_wall_surface_decal(f"{name}_east_wainscot_rub_mark_{index+1:02d}", room, (east_x - 0.030, y + width * 0.10), rub_size, panel_bottom_z + 0.28, 0.055, "wainscot_rub_mark", "FloorWear")
                add_wall_surface_decal(f"{name}_west_wainscot_rub_mark_{index+1:02d}", room, (west_x + 0.030, y - width * 0.12), rub_size, panel_bottom_z + 0.26, 0.055, "wainscot_rub_mark", "FloorWear")
            if index % 2 == 0:
                upper_width = sy / panel_count_short * 0.70
                add_frame(f"{name}_east_upper_wall_frame_{index+1:02d}", room, (east_x, y), upper_width, "north_south", "upper_wall_panel_frame", upper_z, 0.68, "ArtFrameGold")
                add_frame(f"{name}_west_upper_wall_frame_{index+1:02d}", room, (west_x, y), upper_width, "north_south", "upper_wall_panel_frame", upper_z, 0.68, "ArtFrameGold")
                add_decorative_panel(f"{name}_east_decorative_wall_panel_{index+1:02d}", room, (east_x, y), upper_width * 0.70, "north_south")
                add_decorative_panel(f"{name}_west_decorative_wall_panel_{index+1:02d}", room, (west_x, y), upper_width * 0.70, "north_south")

        pilaster_long_step = max(1, panel_count_long // 4)
        for index in range(0, panel_count_long + 1, pilaster_long_step):
            x = cx - sx / 2.0 + sx * index / panel_count_long
            add_pilaster(f"{name}_north_pilaster_{index+1:02d}", room, (x, north_y), (0.13, 0.16))
            add_pilaster(f"{name}_south_pilaster_{index+1:02d}", room, (x, south_y), (0.13, 0.16))
        pilaster_short_step = max(1, panel_count_short // 3)
        for index in range(0, panel_count_short + 1, pilaster_short_step):
            y = cy - sy / 2.0 + sy * index / panel_count_short
            add_pilaster(f"{name}_east_pilaster_{index+1:02d}", room, (east_x, y), (0.16, 0.13))
            add_pilaster(f"{name}_west_pilaster_{index+1:02d}", room, (west_x, y), (0.16, 0.13))

        glazing_width = min(max(sx * 0.14, 1.65), 3.40)
        add_public_wall_glazing_assembly(f"{name}_north_public_wall_glazing", room, (cx - sx * 0.22, north_y - 0.018), glazing_width, "east_west")
        add_public_wall_glazing_assembly(f"{name}_south_public_wall_glazing", room, (cx + sx * 0.22, south_y + 0.018), glazing_width, "east_west")

    for args in [
        ("rotunda_wall_finish_detail", "Rotunda", (0.0, 0.0), (29.5, 29.5), 10, 10),
        ("house_chamber_wall_finish_detail", "House Chamber", (0.0, -72.0), (62.0, 42.0), 12, 8),
        ("senate_chamber_wall_finish_detail", "Senate Chamber", (0.0, 68.0), (48.0, 38.0), 10, 8),
        ("national_statuary_hall_wall_finish_detail", "National Statuary Hall", (28.0, -30.0), (30.0, 20.0), 8, 5),
        ("old_senate_chamber_wall_finish_detail", "Old Senate Chamber", (28.0, 30.0), (26.0, 18.0), 7, 5),
        ("house_gallery_wall_finish_detail", "House galleries", (0.0, -96.0), (68.0, 10.0), 12, 3),
        ("senate_gallery_wall_finish_detail", "Senate galleries", (0.0, 94.0), (54.0, 10.0), 10, 3),
        ("house_west_office_wall_finish_detail", "House leadership/support offices - schematic zone", (-53.0, -55.0), (22.0, 46.0), 5, 8),
        ("house_east_office_wall_finish_detail", "House committee/support rooms - schematic zone", (53.0, -55.0), (22.0, 46.0), 5, 8),
        ("senate_west_office_wall_finish_detail", "Senate leadership/support offices - schematic zone", (-52.0, 55.0), (22.0, 46.0), 5, 8),
        ("senate_east_office_wall_finish_detail", "Senate committee/support rooms - schematic zone", (52.0, 55.0), (22.0, 46.0), 5, 8),
    ]:
        add_room_finish(*args)

    for name, room, center, size, material in [
        ("rotunda_wall_material_variation", "Rotunda", (0.0, 0.0), (29.5, 29.5), "RotundaWall"),
        ("house_chamber_wall_material_variation", "House Chamber", (0.0, -72.0), (62.0, 42.0), "InteriorWall"),
        ("senate_chamber_wall_material_variation", "Senate Chamber", (0.0, 68.0), (48.0, 38.0), "InteriorWall"),
        ("national_statuary_hall_wall_material_variation", "National Statuary Hall", (28.0, -30.0), (30.0, 20.0), "ColumnStone"),
        ("old_senate_chamber_wall_material_variation", "Old Senate Chamber", (28.0, 30.0), (26.0, 18.0), "RotundaWall"),
        ("house_gallery_wall_material_variation", "House galleries", (0.0, -96.0), (68.0, 10.0), "PublicGallery"),
        ("senate_gallery_wall_material_variation", "Senate galleries", (0.0, 94.0), (54.0, 10.0), "PublicGallery"),
        ("house_west_office_wall_material_variation", "House leadership/support offices - schematic zone", (-53.0, -55.0), (22.0, 46.0), "InteriorWall"),
        ("house_east_office_wall_material_variation", "House committee/support rooms - schematic zone", (53.0, -55.0), (22.0, 46.0), "InteriorWall"),
        ("senate_west_office_wall_material_variation", "Senate leadership/support offices - schematic zone", (-52.0, 55.0), (22.0, 46.0), "InteriorWall"),
        ("senate_east_office_wall_material_variation", "Senate committee/support rooms - schematic zone", (52.0, 55.0), (22.0, 46.0), "InteriorWall"),
    ]:
        cx, cy = center
        sx, sy = size
        north_y = cy + sy / 2.0 - 0.24
        south_y = cy - sy / 2.0 + 0.24
        east_x = cx + sx / 2.0 - 0.24
        west_x = cx - sx / 2.0 + 0.24
        add_material_variation_panel(f"{name}_north_panel", room, (cx - sx * 0.18, north_y), sx * 0.18, "east_west", material)
        add_material_variation_panel(f"{name}_south_panel", room, (cx + sx * 0.18, south_y), sx * 0.18, "east_west", material)
        add_material_variation_panel(f"{name}_east_panel", room, (east_x, cy + sy * 0.18), sy * 0.18, "north_south", material)
        add_material_variation_panel(f"{name}_west_panel", room, (west_x, cy - sy * 0.18), sy * 0.18, "north_south", material)

    for args in [
        ("rotunda_north_public_architrave", "Rotunda", (0.0, 14.53), 4.8, "east_west"),
        ("rotunda_south_public_architrave", "Rotunda", (0.0, -14.53), 4.8, "east_west"),
        ("rotunda_east_public_architrave", "Rotunda", (14.53, 0.0), 4.8, "north_south"),
        ("rotunda_west_public_architrave", "Rotunda", (-14.53, 0.0), 4.8, "north_south"),
        ("house_north_public_architrave", "House Chamber", (0.0, -51.22), 5.8, "east_west"),
        ("house_south_gallery_public_architrave", "House Chamber", (0.0, -92.78), 5.2, "east_west"),
        ("senate_south_public_architrave", "Senate Chamber", (0.0, 49.22), 5.0, "east_west"),
        ("senate_north_gallery_public_architrave", "Senate Chamber", (0.0, 86.78), 4.8, "east_west"),
        ("statuary_north_public_architrave", "National Statuary Hall", (28.0, -20.22), 4.2, "east_west"),
        ("statuary_south_public_architrave", "National Statuary Hall", (28.0, -39.78), 4.2, "east_west"),
        ("statuary_west_public_architrave", "National Statuary Hall", (13.22, -30.0), 3.8, "north_south"),
        ("statuary_east_public_architrave", "National Statuary Hall", (42.78, -30.0), 3.8, "north_south"),
        ("old_senate_north_public_architrave", "Old Senate Chamber", (28.0, 38.78), 3.8, "east_west"),
        ("old_senate_south_public_architrave", "Old Senate Chamber", (28.0, 21.22), 3.8, "east_west"),
        ("old_senate_west_public_architrave", "Old Senate Chamber", (15.22, 30.0), 3.4, "north_south"),
        ("old_senate_east_public_architrave", "Old Senate Chamber", (40.78, 30.0), 3.4, "north_south"),
        ("west_public_spine_architrave", "West terrace public orientation marker", (-56.22, 0.0), 4.2, "north_south"),
        ("east_public_spine_architrave", "East public approach / visitor circulation", (56.22, 0.0), 4.2, "north_south"),
    ]:
        add_architrave(*args)

    add_label(labels, "Raised wall panels, picture rails, pilasters, architraves, glazing panels, drapery, and low wall grilles - schematic", -23.0, -7.5, 7.7, "wall_finish_detail")


def add_interior_ceiling_detail_record(
    records: list[dict[str, Any]],
    name: str,
    kind: str,
    room: str,
    center: tuple[float, float, float],
    size: tuple[float, float] | None = None,
) -> None:
    record: dict[str, Any] = {
        "name": name,
        "kind": kind,
        "room": room,
        "center_m": [round(center[0], 3), round(center[1], 3), round(center[2], 3)],
        "public_accuracy": "schematic_public_interior_ceiling_detail",
        "assignment": (
            "Public visual ceiling/trim detail only; not a restricted route, "
            "security feature, or operational placement."
        ),
    }
    if size is not None:
        record["size_m"] = [round(size[0], 3), round(size[1], 3)]
    records.append(record)


def add_coffered_ceiling(
    obj: ObjWriter,
    records: list[dict[str, Any]],
    name: str,
    room: str,
    center: tuple[float, float],
    size: tuple[float, float],
    columns: int,
    rows: int,
    medallion_offsets: list[tuple[float, float]],
    z: float,
) -> None:
    cx, cy = center
    sx, sy = size
    beam_width = 0.16
    beam_height = 0.12
    crown_height = 0.18

    crown_specs = [
        ("north", (cx, cy + sy / 2.0 - 0.12), (sx * 0.98, 0.18)),
        ("south", (cx, cy - sy / 2.0 + 0.12), (sx * 0.98, 0.18)),
        ("east", (cx + sx / 2.0 - 0.12, cy), (0.18, sy * 0.98)),
        ("west", (cx - sx / 2.0 + 0.12, cy), (0.18, sy * 0.98)),
    ]
    for side, detail_center, detail_size in crown_specs:
        detail_name = f"{name}_{side}_crown_molding"
        obj.add_beveled_box(detail_center, detail_size, crown_height, z, detail_name, "ArtFrameGold", 0.018)
        add_interior_ceiling_detail_record(
            records,
            detail_name,
            "crown_molding",
            room,
            (detail_center[0], detail_center[1], z + crown_height / 2.0),
            detail_size,
        )
        add_interior_ceiling_detail_record(
            records,
            f"{detail_name}_beveled_profile",
            "beveled_ceiling_trim_profile",
            room,
            (detail_center[0], detail_center[1], z + crown_height / 2.0),
            detail_size,
        )

    for col in range(1, columns):
        x = cx - sx / 2.0 + sx * col / columns
        detail_name = f"{name}_vertical_ceiling_beam_{col:02d}"
        detail_size = (beam_width, sy * 0.94)
        obj.add_beveled_box((x, cy), detail_size, beam_height, z + 0.02, detail_name, "InteriorTrim", 0.012)
        add_interior_ceiling_detail_record(records, detail_name, "ceiling_grid_beam", room, (x, cy, z + 0.08), detail_size)
        add_interior_ceiling_detail_record(records, f"{detail_name}_beveled_profile", "beveled_ceiling_trim_profile", room, (x, cy, z + 0.08), detail_size)
    for row in range(1, rows):
        y = cy - sy / 2.0 + sy * row / rows
        detail_name = f"{name}_horizontal_ceiling_beam_{row:02d}"
        detail_size = (sx * 0.94, beam_width)
        obj.add_beveled_box((cx, y), detail_size, beam_height, z + 0.02, detail_name, "InteriorTrim", 0.012)
        add_interior_ceiling_detail_record(records, detail_name, "ceiling_grid_beam", room, (cx, y, z + 0.08), detail_size)
        add_interior_ceiling_detail_record(records, f"{detail_name}_beveled_profile", "beveled_ceiling_trim_profile", room, (cx, y, z + 0.08), detail_size)

    cell_w = sx / columns
    cell_h = sy / rows
    for row in range(rows):
        for col in range(columns):
            px = cx - sx / 2.0 + cell_w * (col + 0.5)
            py = cy - sy / 2.0 + cell_h * (row + 0.5)
            detail_name = f"{name}_coffer_panel_r{row+1:02d}_c{col+1:02d}"
            panel_size = (cell_w * 0.70, cell_h * 0.66)
            obj.add_beveled_box((px, py), panel_size, 0.035, z + 0.10, detail_name, "RotundaWall", 0.022)
            shadow_name = f"{detail_name}_recess_shadow"
            shadow_size = (panel_size[0] * 0.84, panel_size[1] * 0.80)
            obj.add_beveled_box((px, py), shadow_size, 0.016, z + 0.084, shadow_name, "DoorMetal", 0.016)
            add_interior_ceiling_detail_record(records, detail_name, "coffer_panel", room, (px, py, z + 0.118), panel_size)
            add_interior_ceiling_detail_record(records, f"{detail_name}_beveled_profile", "beveled_ceiling_trim_profile", room, (px, py, z + 0.118), panel_size)
            add_interior_ceiling_detail_record(records, shadow_name, "coffer_recess_shadow", room, (px, py, z + 0.092), shadow_size)

    variation_material = "PublicGallery" if "galler" in room.lower() else ("RotundaWall" if "Statuary" in room or "Old Senate" in room else "InteriorWall")
    for index, (ox, oy) in enumerate([(-0.28, -0.24), (0.28, -0.24), (-0.28, 0.24), (0.28, 0.24)], start=1):
        x = cx + sx * ox
        y = cy + sy * oy
        detail_name = f"{name}_ceiling_material_variation_panel_{index:02d}"
        panel_size = (cell_w * 0.52, cell_h * 0.42)
        obj.add_box((x, y), panel_size, 0.026, z + 0.145, detail_name, variation_material)
        obj.add_box((x, y), (panel_size[0] * 1.06, panel_size[1] * 1.06), 0.020, z + 0.132, f"{detail_name}_shadow_reveal", "DoorMetal")
        add_interior_ceiling_detail_record(records, detail_name, "ceiling_material_variation_panel", room, (x, y, z + 0.158), panel_size)

    for index, (ox, oy) in enumerate(medallion_offsets, start=1):
        x = cx + sx * ox
        y = cy + sy * oy
        medallion_name = f"{name}_ceiling_medallion_{index:02d}"
        canopy_name = f"{name}_light_canopy_{index:02d}"
        obj.add_cylinder((x, y), 0.52, z + 0.16, 0.06, medallion_name, "ArtFrameGold", segments=24)
        obj.add_cylinder((x, y), 0.22, z + 0.22, 0.08, canopy_name, "LightFixtureMetal", segments=18)
        trim_name = f"{canopy_name}_trim_ring"
        glass_name = f"{canopy_name}_glass_dome"
        obj.add_ring((x, y), 0.31, 0.235, z + 0.255, 0.032, trim_name, "BrassRail", segments=18)
        obj.add_cylinder((x, y), 0.155, z + 0.298, 0.105, glass_name, "WarmLightGlass", segments=16)
        add_interior_ceiling_detail_record(records, medallion_name, "ceiling_medallion", room, (x, y, z + 0.19), (1.04, 1.04))
        add_interior_ceiling_detail_record(records, canopy_name, "light_canopy", room, (x, y, z + 0.26), (0.44, 0.44))
        add_interior_ceiling_detail_record(records, trim_name, "light_fixture_trim_ring", room, (x, y, z + 0.271), (0.62, 0.62))
        add_interior_ceiling_detail_record(records, glass_name, "light_fixture_glass_dome", room, (x, y, z + 0.35), (0.31, 0.31))

    vent_offsets = [(-0.34, -0.34), (0.34, -0.34), (-0.34, 0.34), (0.34, 0.34)]
    for index, (ox, oy) in enumerate(vent_offsets, start=1):
        x = cx + sx * ox
        y = cy + sy * oy
        vent_name = f"{name}_ceiling_vent_grille_{index:02d}"
        vent_size = (0.82, 0.34)
        obj.add_box((x, y), vent_size, 0.028, z + 0.18, vent_name, "LightFixtureMetal")
        for slat in range(3):
            slat_y = y - 0.10 + slat * 0.10
            obj.add_box((x, slat_y), (0.70, 0.028), 0.032, z + 0.215, f"{vent_name}_slat_{slat+1}", "BrassRail")
        add_interior_ceiling_detail_record(records, vent_name, "ceiling_vent_grille", room, (x, y, z + 0.197), vent_size)

    utility_offsets = [(-0.18, -0.34), (0.18, -0.34), (-0.18, 0.34), (0.18, 0.34)]
    for index, (ox, oy) in enumerate(utility_offsets, start=1):
        x = cx + sx * ox
        y = cy + sy * oy
        sprinkler_name = f"{name}_generic_sprinkler_head_{index:02d}"
        obj.add_cylinder((x, y), 0.075, z + 0.235, 0.032, sprinkler_name, "BrassRail", segments=12)
        obj.add_cylinder((x, y), 0.035, z + 0.270, 0.035, f"{sprinkler_name}_center_pin", "DoorMetal", segments=8)
        add_interior_ceiling_detail_record(records, sprinkler_name, "generic_ceiling_sprinkler_head", room, (x, y, z + 0.251), (0.15, 0.15))

    detector_offsets = [(-0.36, 0.0), (0.36, 0.0)]
    for index, (ox, oy) in enumerate(detector_offsets, start=1):
        x = cx + sx * ox
        y = cy + sy * oy
        detector_name = f"{name}_generic_smoke_detector_disc_{index:02d}"
        obj.add_cylinder((x, y), 0.18, z + 0.230, 0.045, detector_name, "LaneMarkingWhite", segments=20)
        obj.add_ring((x, y), 0.135, 0.115, z + 0.278, 0.020, f"{detector_name}_inner_ring", "DoorMetal", segments=16)
        add_interior_ceiling_detail_record(records, detector_name, "generic_ceiling_smoke_detector_disc", room, (x, y, z + 0.253), (0.36, 0.36))

    diffuser_offsets = [(0.0, -0.36), (0.0, 0.36)]
    for index, (ox, oy) in enumerate(diffuser_offsets, start=1):
        x = cx + sx * ox
        y = cy + sy * oy
        diffuser_name = f"{name}_square_air_diffuser_{index:02d}"
        diffuser_size = (0.58, 0.58)
        obj.add_box((x, y), diffuser_size, 0.028, z + 0.226, diffuser_name, "LightFixtureMetal")
        for ring_index, scale in enumerate([0.72, 0.48], start=1):
            obj.add_box((x, y), (diffuser_size[0] * scale, 0.030), 0.034, z + 0.258 + ring_index * 0.006, f"{diffuser_name}_horizontal_bar_{ring_index}", "BrassRail")
            obj.add_box((x, y), (0.030, diffuser_size[1] * scale), 0.034, z + 0.258 + ring_index * 0.006, f"{diffuser_name}_vertical_bar_{ring_index}", "BrassRail")
        add_interior_ceiling_detail_record(records, diffuser_name, "generic_ceiling_air_diffuser", room, (x, y, z + 0.240), diffuser_size)

    access_panel_offsets = [(-0.42, 0.22), (0.42, -0.22)]
    for index, (ox, oy) in enumerate(access_panel_offsets, start=1):
        x = cx + sx * ox
        y = cy + sy * oy
        panel_name = f"{name}_generic_access_panel_{index:02d}"
        panel_size = (0.72, 0.46)
        obj.add_box((x, y), panel_size, 0.020, z + 0.218, panel_name, "InteriorTrim")
        obj.add_box((x, y), (panel_size[0] * 0.90, 0.030), 0.026, z + 0.247, f"{panel_name}_hinge_line", "DoorMetal")
        obj.add_box((x + panel_size[0] * 0.32, y), (0.050, 0.050), 0.030, z + 0.252, f"{panel_name}_pull_dot", "BrassRail")
        add_interior_ceiling_detail_record(records, panel_name, "generic_ceiling_access_panel", room, (x, y, z + 0.228), panel_size)


def add_public_interior_ceiling_details(
    obj: ObjWriter,
    labels: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> None:
    ceiling_specs = [
        ("house_chamber_ceiling", "House Chamber", (0.0, -72.0), (62.0, 42.0), 6, 4, [(-0.28, -0.18), (0.0, -0.18), (0.28, -0.18), (-0.14, 0.18), (0.14, 0.18)], 8.15),
        ("senate_chamber_ceiling", "Senate Chamber", (0.0, 68.0), (48.0, 38.0), 5, 4, [(-0.24, -0.16), (0.0, -0.16), (0.24, -0.16), (0.0, 0.18)], 8.05),
        ("national_statuary_hall_ceiling", "National Statuary Hall", (28.0, -30.0), (30.0, 20.0), 4, 3, [(-0.22, 0.0), (0.0, 0.0), (0.22, 0.0)], 7.95),
        ("old_senate_chamber_ceiling", "Old Senate Chamber", (28.0, 30.0), (26.0, 18.0), 4, 3, [(-0.22, 0.0), (0.0, 0.0), (0.22, 0.0)], 7.9),
        ("house_gallery_ceiling", "House galleries", (0.0, -96.0), (68.0, 10.0), 6, 1, [(-0.34, 0.0), (-0.12, 0.0), (0.12, 0.0), (0.34, 0.0)], 7.65),
        ("senate_gallery_ceiling", "Senate galleries", (0.0, 94.0), (54.0, 10.0), 5, 1, [(-0.32, 0.0), (-0.10, 0.0), (0.10, 0.0), (0.32, 0.0)], 7.65),
        ("house_west_office_ceiling", "House leadership/support offices - schematic zone", (-53.0, -55.0), (22.0, 46.0), 3, 4, [(-0.18, -0.18), (0.18, 0.18)], 7.35),
        ("house_east_office_ceiling", "House committee/support rooms - schematic zone", (53.0, -55.0), (22.0, 46.0), 3, 4, [(-0.18, -0.18), (0.18, 0.18)], 7.35),
        ("senate_west_office_ceiling", "Senate leadership/support offices - schematic zone", (-52.0, 55.0), (22.0, 46.0), 3, 4, [(-0.18, -0.18), (0.18, 0.18)], 7.35),
        ("senate_east_office_ceiling", "Senate committee/support rooms - schematic zone", (52.0, 55.0), (22.0, 46.0), 3, 4, [(-0.18, -0.18), (0.18, 0.18)], 7.35),
    ]
    for spec in ceiling_specs:
        add_coffered_ceiling(obj, records, *spec)
    add_label(labels, "Coffered ceilings and crown trim - schematic", 0.0, 0.0, 8.9, "wall_treatment")


def add_public_floor_detail_record(
    records: list[dict[str, Any]],
    name: str,
    kind: str,
    area: str,
    center: tuple[float, float, float],
    size: tuple[float, float] | None = None,
) -> None:
    record: dict[str, Any] = {
        "name": name,
        "kind": kind,
        "area": area,
        "center_m": [round(center[0], 3), round(center[1], 3), round(center[2], 3)],
        "public_accuracy": "schematic_public_interior_floor_finish",
        "assignment": (
            "Public visual floor-finish detail only; not a restricted route, "
            "security feature, or operational placement."
        ),
    }
    if size is not None:
        record["size_m"] = [round(size[0], 3), round(size[1], 3)]
    records.append(record)


def add_floor_border(
    obj: ObjWriter,
    records: list[dict[str, Any]],
    name: str,
    area: str,
    center: tuple[float, float],
    size: tuple[float, float],
    z: float,
    kind: str,
    material: str,
    thickness: float = 0.16,
) -> None:
    cx, cy = center
    sx, sy = size
    border_specs = [
        ("north", (cx, cy + sy / 2.0 - thickness / 2.0), (sx, thickness)),
        ("south", (cx, cy - sy / 2.0 + thickness / 2.0), (sx, thickness)),
        ("east", (cx + sx / 2.0 - thickness / 2.0, cy), (thickness, sy)),
        ("west", (cx - sx / 2.0 + thickness / 2.0, cy), (thickness, sy)),
    ]
    for side, detail_center, detail_size in border_specs:
        detail_name = f"{name}_{side}"
        obj.add_box(detail_center, detail_size, 0.035, z, detail_name, material)
        add_public_floor_detail_record(records, detail_name, kind, area, (detail_center[0], detail_center[1], z + 0.018), detail_size)


def add_floor_tile_grid(
    obj: ObjWriter,
    records: list[dict[str, Any]],
    name: str,
    area: str,
    center: tuple[float, float],
    size: tuple[float, float],
    columns: int,
    rows: int,
    z: float,
) -> None:
    cx, cy = center
    sx, sy = size
    for col in range(1, columns):
        x = cx - sx / 2.0 + sx * col / columns
        detail_name = f"{name}_vertical_joint_{col:02d}"
        detail_size = (0.075, sy * 0.94)
        obj.add_box((x, cy), detail_size, 0.026, z, detail_name, "StepStone")
        add_public_floor_detail_record(records, detail_name, "marble_tile_joint", area, (x, cy, z + 0.013), detail_size)
    for row in range(1, rows):
        y = cy - sy / 2.0 + sy * row / rows
        detail_name = f"{name}_horizontal_joint_{row:02d}"
        detail_size = (sx * 0.94, 0.075)
        obj.add_box((cx, y), detail_size, 0.026, z, detail_name, "StepStone")
        add_public_floor_detail_record(records, detail_name, "marble_tile_joint", area, (cx, y, z + 0.013), detail_size)


def add_floor_medallion(
    obj: ObjWriter,
    records: list[dict[str, Any]],
    name: str,
    area: str,
    center: tuple[float, float],
    radius: float,
    z: float,
) -> None:
    obj.add_cylinder(center, radius, z, 0.035, name, "BrassRail", segments=28)
    add_public_floor_detail_record(records, name, "floor_medallion", area, (center[0], center[1], z + 0.018), (radius * 2.0, radius * 2.0))


def add_public_room_shape_details(
    obj: ObjWriter,
    labels: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> None:
    def ellipse_points(
        center: tuple[float, float],
        radius_x: float,
        radius_y: float,
        segments: int = 72,
    ) -> list[tuple[float, float]]:
        cx, cy = center
        return [
            (cx + radius_x * math.cos(math.tau * idx / segments), cy + radius_y * math.sin(math.tau * idx / segments))
            for idx in range(segments + 1)
        ]

    def outline(
        name: str,
        area: str,
        center: tuple[float, float],
        radii: tuple[float, float],
        z: float,
        width: float = 0.16,
    ) -> None:
        points = ellipse_points(center, radii[0], radii[1])
        obj.add_polyline_strip(points, width, z, name, "BrassRail")
        add_public_floor_detail_record(
            records,
            name,
            "public_room_outline_inlay",
            area,
            (center[0], center[1], z),
            (radii[0] * 2.0, radii[1] * 2.0),
        )

    def axis_inlay(
        name: str,
        area: str,
        start: tuple[float, float],
        end: tuple[float, float],
        z: float,
        width: float = 0.12,
    ) -> None:
        obj.add_polyline_strip([start, end], width, z, name, "ArtFrameGold")
        center = ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)
        length = math.hypot(end[0] - start[0], end[1] - start[1])
        add_public_floor_detail_record(records, name, "public_room_axis_inlay", area, (center[0], center[1], z), (length, width))

    def column_marker(name: str, area: str, center: tuple[float, float], z: float, radius: float = 0.34) -> None:
        obj.add_ring(center, radius, radius * 0.66, z, 0.030, name, "ColumnStone", segments=18)
        add_public_floor_detail_record(
            records,
            name,
            "public_column_footprint_marker",
            area,
            (center[0], center[1], z + 0.015),
            (radius * 2.0, radius * 2.0),
        )

    outline("rotunda_public_room_outer_outline", "Rotunda", (0.0, 0.0), (14.35, 14.35), 4.635, width=0.18)
    outline("rotunda_public_room_inner_outline", "Rotunda", (0.0, 0.0), (9.25, 9.25), 4.655, width=0.12)
    outline("statuary_hall_public_room_oval_outline", "National Statuary Hall", (28.0, -30.0), (14.0, 8.8), 4.665)
    outline("statuary_hall_public_inner_oval_outline", "National Statuary Hall", (28.0, -30.0), (9.8, 5.9), 4.685, width=0.11)
    outline("old_senate_public_room_oval_outline", "Old Senate Chamber", (28.0, 30.0), (12.0, 7.7), 4.665)
    outline("old_senate_public_inner_oval_outline", "Old Senate Chamber", (28.0, 30.0), (8.2, 5.0), 4.685, width=0.11)
    outline("crypt_marker_public_room_outline", "Crypt below Rotunda marker", (0.0, -24.0), (10.7, 5.2), 4.645, width=0.14)

    for name, area, center, starts_ends in [
        (
            "rotunda_public_axis",
            "Rotunda",
            (0.0, 0.0),
            [((-12.7, 0.0), (12.7, 0.0)), ((0.0, -12.7), (0.0, 12.7)), ((-8.9, -8.9), (8.9, 8.9)), ((-8.9, 8.9), (8.9, -8.9))],
        ),
        (
            "statuary_public_axis",
            "National Statuary Hall",
            (28.0, -30.0),
            [((16.2, -30.0), (39.8, -30.0)), ((28.0, -37.2), (28.0, -22.8))],
        ),
        (
            "old_senate_public_axis",
            "Old Senate Chamber",
            (28.0, 30.0),
            [((17.4, 30.0), (38.6, 30.0)), ((28.0, 23.8), (28.0, 36.2))],
        ),
        (
            "crypt_marker_public_axis",
            "Crypt below Rotunda marker",
            (0.0, -24.0),
            [((-8.9, -24.0), (8.9, -24.0)), ((0.0, -28.4), (0.0, -19.6))],
        ),
    ]:
        for index, (start, end) in enumerate(starts_ends, start=1):
            axis_inlay(f"{name}_{index:02d}", area, start, end, 4.705, width=0.10)

    for idx in range(16):
        angle = math.tau * idx / 16.0
        column_marker(
            f"rotunda_public_column_footprint_{idx+1:02d}",
            "Rotunda",
            (11.45 * math.cos(angle), 11.45 * math.sin(angle)),
            4.705,
            radius=0.30,
        )
    for idx, (x, y) in enumerate(
        [(18.0, -37.2), (23.0, -38.4), (28.0, -38.8), (33.0, -38.4), (38.0, -37.2), (17.2, -30.0), (38.8, -30.0), (18.0, -22.8), (23.0, -21.6), (28.0, -21.2), (33.0, -21.6), (38.0, -22.8)],
        start=1,
    ):
        column_marker(f"statuary_hall_public_column_footprint_{idx:02d}", "National Statuary Hall", (x, y), 4.705)
    for idx, (x, y) in enumerate(
        [(19.0, 23.7), (25.0, 22.7), (31.0, 22.7), (37.0, 23.7), (19.0, 36.3), (25.0, 37.3), (31.0, 37.3), (37.0, 36.3)],
        start=1,
    ):
        column_marker(f"old_senate_public_column_footprint_{idx:02d}", "Old Senate Chamber", (x, y), 4.705, radius=0.30)
    for idx in range(8):
        angle = math.tau * idx / 8.0
        column_marker(
            f"crypt_marker_public_column_footprint_{idx+1:02d}",
            "Crypt below Rotunda marker",
            (7.4 * math.cos(angle), -24.0 + 3.6 * math.sin(angle)),
            4.685,
            radius=0.28,
        )

    add_label(labels, "Public room-shape floor outlines and column footprints - schematic", -21.0, -24.0, 5.35, "floor_detail")


def add_public_interior_floor_details(
    obj: ObjWriter,
    labels: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> None:
    def add_marble_vein_decal(
        name: str,
        area: str,
        start: tuple[float, float],
        end: tuple[float, float],
        z: float,
        width: float = 0.038,
    ) -> None:
        obj.add_polyline_strip([start, end], width, z, name, "StepStone")
        center = ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)
        length = math.hypot(end[0] - start[0], end[1] - start[1])
        add_public_floor_detail_record(records, name, "marble_vein_decal", area, (center[0], center[1], z), (length, width))

    def add_carpet_pile_variation_decal(
        name: str,
        area: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
        angle_degrees: float,
    ) -> None:
        obj.add_oriented_box(center, size, 0.010, z, math.radians(angle_degrees), name, "FloorWear")
        add_public_floor_detail_record(records, name, "carpet_pile_variation_decal", area, (center[0], center[1], z + 0.005), size)

    def add_threshold_tarnish_decal(
        name: str,
        area: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
    ) -> None:
        obj.add_box(center, size, 0.012, z, name, "FloorWear")
        add_public_floor_detail_record(records, name, "threshold_tarnish_decal", area, (center[0], center[1], z + 0.006), size)

    public_floor_specs = [
        ("national_statuary_hall_floor", "National Statuary Hall", (28.0, -30.0), (28.0, 18.0), 4, 3, 4.47),
        ("old_senate_chamber_floor", "Old Senate Chamber", (28.0, 30.0), (24.0, 16.0), 4, 3, 4.47),
        ("crypt_marker_floor", "Crypt below Rotunda marker", (0.0, -24.0), (22.0, 10.0), 3, 2, 4.47),
        ("house_well_floor", "House Chamber public well", (0.0, -54.0), (18.0, 8.0), 5, 2, 4.58),
        ("senate_presiding_floor", "Senate presiding-officer public well", (0.0, 83.0), (14.0, 7.0), 4, 2, 4.58),
        ("north_public_spine_floor", "Rotunda / Senate public spine", (0.0, 35.0), (16.0, 26.0), 2, 5, 4.47),
        ("south_public_spine_floor", "Rotunda / House public spine", (0.0, -35.0), (16.0, 26.0), 2, 5, 4.47),
        ("east_public_circulation_floor", "East public approach / visitor circulation", (62.0, 0.0), (11.5, 66.0), 2, 8, 4.47),
        ("west_public_circulation_floor", "West terrace public orientation marker", (-62.0, 0.0), (11.5, 66.0), 2, 8, 4.47),
        ("house_west_office_floor", "House leadership/support offices - schematic zone", (-53.0, -55.0), (19.0, 42.0), 3, 5, 4.62),
        ("house_east_office_floor", "House committee/support rooms - schematic zone", (53.0, -55.0), (19.0, 42.0), 3, 5, 4.62),
        ("senate_west_office_floor", "Senate leadership/support offices - schematic zone", (-52.0, 55.0), (19.0, 42.0), 3, 5, 4.62),
        ("senate_east_office_floor", "Senate committee/support rooms - schematic zone", (52.0, 55.0), (19.0, 42.0), 3, 5, 4.62),
    ]
    for name, area, center, size, columns, rows, z in public_floor_specs:
        add_floor_border(obj, records, f"{name}_stone_border", area, center, size, z, "floor_border_strip", "BrassRail")
        add_floor_tile_grid(obj, records, f"{name}_tile_grid", area, center, size, columns, rows, z + 0.04)
        cx, cy = center
        sx, sy = size
        vein_length = min(sx, sy) * 0.28
        for vein_index in range(4):
            x = cx - sx * 0.30 + sx * 0.20 * vein_index
            y = cy - sy * 0.24 + sy * 0.13 * ((vein_index * 2) % 5)
            start = (x - vein_length * 0.50, y - vein_length * 0.16)
            end = (x + vein_length * 0.50, y + vein_length * 0.16)
            add_marble_vein_decal(f"{name}_marble_vein_decal_{vein_index+1:02d}", area, start, end, z + 0.076, width=0.030 + 0.004 * (vein_index % 2))

    carpet_specs = [
        ("house_chamber_carpet_border", "House Chamber", (0.0, -80.0), (55.5, 30.5), 4.57, "HouseCarpet"),
        ("senate_chamber_carpet_border", "Senate Chamber", (0.0, 73.0), (42.5, 26.5), 4.57, "SenateCarpet"),
        ("house_gallery_carpet_border", "House galleries", (0.0, -100.0), (66.5, 7.6), 4.92, "HouseCarpet"),
        ("senate_gallery_carpet_border", "Senate galleries", (0.0, 97.5), (52.5, 6.8), 4.92, "SenateCarpet"),
    ]
    for name, area, center, size, z, material in carpet_specs:
        add_floor_border(obj, records, name, area, center, size, z, "carpet_border_strip", material, thickness=0.22)
        cx, cy = center
        sx, sy = size
        for pile_index in range(6):
            x = cx - sx * 0.32 + sx * 0.128 * pile_index
            y = cy + sy * (0.16 if pile_index % 2 == 0 else -0.14)
            pile_size = (sx * 0.12, 0.085 if sy > 10.0 else 0.060)
            add_carpet_pile_variation_decal(
                f"{name}_pile_variation_decal_{pile_index+1:02d}",
                area,
                (x, y),
                pile_size,
                z + 0.054,
                -4.0 + pile_index * 1.7,
            )

    threshold_specs = [
        ("west_public_approach_floor_slab", "West terrace public orientation marker", (-55.0, 0.0), (0.90, 8.2), 4.52),
        ("east_public_approach_floor_slab", "East public approach / visitor circulation", (55.0, 0.0), (0.90, 8.2), 4.52),
        ("rotunda_statuary_hall_floor_slab", "Rotunda / National Statuary Hall", (16.2, -15.8), (5.2, 0.90), 4.52),
        ("rotunda_old_senate_floor_slab", "Rotunda / Old Senate Chamber", (16.2, 15.8), (5.0, 0.90), 4.52),
        ("rotunda_house_floor_slab", "Rotunda / House Chamber orientation", (0.0, -51.0), (6.6, 0.95), 4.56),
        ("rotunda_senate_floor_slab", "Rotunda / Senate Chamber orientation", (0.0, 51.0), (6.4, 0.95), 4.56),
        ("house_gallery_floor_slab", "House Chamber / public gallery", (0.0, -91.0), (8.4, 0.90), 4.76),
        ("senate_gallery_floor_slab", "Senate Chamber / public gallery", (0.0, 89.0), (7.4, 0.90), 4.76),
    ]
    for name, area, center, size, z in threshold_specs:
        obj.add_box(center, size, 0.035, z, name, "StepStone")
        add_public_floor_detail_record(records, name, "public_threshold_slab", area, (center[0], center[1], z + 0.018), size)
        cx, cy = center
        sx, sy = size
        if sx >= sy:
            tarnish_specs = [
                ((cx, cy - sy * 0.32), (sx * 0.72, 0.050)),
                ((cx, cy + sy * 0.32), (sx * 0.64, 0.044)),
            ]
        else:
            tarnish_specs = [
                ((cx - sx * 0.32, cy), (0.050, sy * 0.72)),
                ((cx + sx * 0.32, cy), (0.044, sy * 0.64)),
            ]
        for tarnish_index, (tarnish_center, tarnish_size) in enumerate(tarnish_specs, start=1):
            add_threshold_tarnish_decal(
                f"{name}_threshold_tarnish_decal_{tarnish_index:02d}",
                area,
                tarnish_center,
                tarnish_size,
                z + 0.043,
            )

    medallion_specs = [
        ("statuary_hall_center_floor_medallion", "National Statuary Hall", (28.0, -30.0), 1.25, 4.53),
        ("old_senate_center_floor_medallion", "Old Senate Chamber", (28.0, 30.0), 1.05, 4.53),
        ("east_circulation_floor_medallion_north", "East public approach / visitor circulation", (62.0, 18.0), 0.72, 4.53),
        ("east_circulation_floor_medallion_south", "East public approach / visitor circulation", (62.0, -18.0), 0.72, 4.53),
        ("west_circulation_floor_medallion_north", "West terrace public orientation marker", (-62.0, 18.0), 0.72, 4.53),
        ("west_circulation_floor_medallion_south", "West terrace public orientation marker", (-62.0, -18.0), 0.72, 4.53),
        ("house_floor_centerline_medallion", "House Chamber", (0.0, -65.0), 0.62, 4.61),
        ("senate_floor_centerline_medallion", "Senate Chamber", (0.0, 70.0), 0.62, 4.61),
        ("house_gallery_floor_medallion", "House galleries", (0.0, -100.0), 0.58, 4.98),
        ("senate_gallery_floor_medallion", "Senate galleries", (0.0, 97.5), 0.58, 4.98),
        ("house_west_office_floor_medallion", "House leadership/support offices - schematic zone", (-53.0, -55.0), 0.56, 4.68),
        ("senate_east_office_floor_medallion", "Senate committee/support rooms - schematic zone", (52.0, 55.0), 0.56, 4.68),
    ]
    for name, area, center, radius, z in medallion_specs:
        add_floor_medallion(obj, records, name, area, center, radius, z)

    wear_band_specs = [
        ("rotunda_floor_wear_band_north_south", "Rotunda", [(0.0, -11.8), (0.0, 11.8)], 0.92, 4.735),
        ("rotunda_floor_wear_band_east_west", "Rotunda", [(-11.8, 0.0), (11.8, 0.0)], 0.82, 4.735),
        ("south_public_spine_floor_wear_band", "Rotunda / House Chamber orientation", [(0.0, -48.0), (0.0, -18.0)], 0.78, 4.615),
        ("north_public_spine_floor_wear_band", "Rotunda / Senate public spine", [(0.0, 18.0), (0.0, 48.0)], 0.78, 4.615),
        ("statuary_hall_floor_wear_band", "National Statuary Hall", [(17.0, -30.0), (39.0, -30.0)], 0.70, 4.565),
        ("old_senate_floor_wear_band", "Old Senate Chamber", [(18.0, 30.0), (38.0, 30.0)], 0.64, 4.565),
        ("house_chamber_public_well_floor_wear_band", "House Chamber public well", [(-8.0, -56.0), (8.0, -56.0)], 0.62, 4.635),
        ("senate_presiding_floor_wear_band", "Senate presiding-officer public well", [(-6.5, 83.0), (6.5, 83.0)], 0.58, 4.635),
        ("house_gallery_floor_wear_band", "House galleries", [(-25.0, -100.0), (25.0, -100.0)], 0.54, 4.985),
        ("senate_gallery_floor_wear_band", "Senate galleries", [(-20.0, 97.5), (20.0, 97.5)], 0.50, 4.985),
    ]
    for name, area, points, width, z in wear_band_specs:
        obj.add_polyline_strip(points, width, z, name, "FloorWear")
        start, end = points[0], points[-1]
        center = ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)
        length = math.hypot(end[0] - start[0], end[1] - start[1])
        add_public_floor_detail_record(records, name, "floor_wear_band", area, (center[0], center[1], z), (length, width))

    scuff_specs = [
        ("rotunda_north_threshold_floor_scuff", "Rotunda", (0.0, 11.6), (2.8, 0.55), 0.0, 4.742),
        ("rotunda_south_threshold_floor_scuff", "Rotunda", (0.0, -11.6), (2.8, 0.55), 0.0, 4.742),
        ("rotunda_east_threshold_floor_scuff", "Rotunda", (11.6, 0.0), (0.55, 2.8), 0.0, 4.742),
        ("rotunda_west_threshold_floor_scuff", "Rotunda", (-11.6, 0.0), (0.55, 2.8), 0.0, 4.742),
        ("statuary_center_floor_scuff", "National Statuary Hall", (28.0, -30.0), (3.6, 1.15), 8.0, 4.575),
        ("statuary_east_floor_scuff", "National Statuary Hall", (36.0, -30.8), (2.4, 0.72), -5.0, 4.575),
        ("statuary_west_floor_scuff", "National Statuary Hall", (20.0, -29.2), (2.4, 0.72), 6.0, 4.575),
        ("old_senate_center_floor_scuff", "Old Senate Chamber", (28.0, 30.0), (3.0, 0.98), -6.0, 4.575),
        ("old_senate_east_floor_scuff", "Old Senate Chamber", (35.2, 30.6), (2.0, 0.66), 4.0, 4.575),
        ("old_senate_west_floor_scuff", "Old Senate Chamber", (20.8, 29.4), (2.0, 0.66), -4.0, 4.575),
        ("house_rostrum_floor_scuff", "House Chamber public well", (0.0, -55.2), (4.8, 0.74), 0.0, 4.642),
        ("house_well_left_floor_scuff", "House Chamber public well", (-7.8, -53.8), (2.0, 0.58), -8.0, 4.642),
        ("house_well_right_floor_scuff", "House Chamber public well", (7.8, -53.8), (2.0, 0.58), 8.0, 4.642),
        ("senate_presiding_center_floor_scuff", "Senate presiding-officer public well", (0.0, 83.0), (3.6, 0.70), 0.0, 4.642),
        ("senate_presiding_left_floor_scuff", "Senate presiding-officer public well", (-5.4, 82.2), (1.7, 0.52), 5.0, 4.642),
        ("senate_presiding_right_floor_scuff", "Senate presiding-officer public well", (5.4, 82.2), (1.7, 0.52), -5.0, 4.642),
        ("east_public_circulation_north_floor_scuff", "East public approach / visitor circulation", (62.0, 22.0), (1.2, 3.0), 0.0, 4.548),
        ("east_public_circulation_south_floor_scuff", "East public approach / visitor circulation", (62.0, -22.0), (1.2, 3.0), 0.0, 4.548),
        ("west_public_circulation_north_floor_scuff", "West terrace public orientation marker", (-62.0, 22.0), (1.2, 3.0), 0.0, 4.548),
        ("west_public_circulation_south_floor_scuff", "West terrace public orientation marker", (-62.0, -22.0), (1.2, 3.0), 0.0, 4.548),
        ("house_gallery_left_floor_scuff", "House galleries", (-18.0, -100.0), (3.2, 0.46), 0.0, 4.992),
        ("house_gallery_right_floor_scuff", "House galleries", (18.0, -100.0), (3.2, 0.46), 0.0, 4.992),
        ("senate_gallery_left_floor_scuff", "Senate galleries", (-15.0, 97.5), (2.7, 0.42), 0.0, 4.992),
        ("senate_gallery_right_floor_scuff", "Senate galleries", (15.0, 97.5), (2.7, 0.42), 0.0, 4.992),
    ]
    for name, area, center, size, angle_degrees, z in scuff_specs:
        obj.add_oriented_box(center, size, 0.012, z, math.radians(angle_degrees), name, "FloorWear")
        add_public_floor_detail_record(records, name, "floor_wear_scuff_patch", area, (center[0], center[1], z + 0.006), size)

    add_public_room_shape_details(obj, labels, records)
    add_label(labels, "Public floor borders, thresholds, and marble tile joints - schematic", 18.0, 0.0, 5.2, "public_circulation_detail")


def add_surface_aging_detail_record(
    records: list[dict[str, Any]],
    name: str,
    kind: str,
    area: str,
    center: tuple[float, float, float],
    size: tuple[float, float],
    material: str,
) -> None:
    records.append(
        {
            "name": name,
            "kind": kind,
            "area": area,
            "center_m": [round(center[0], 3), round(center[1], 3), round(center[2], 3)],
            "size_m": [round(size[0], 3), round(size[1], 3)],
            "material": material,
            "public_accuracy": "schematic_public_interior_surface_aging_detail",
            "assignment": (
                "Public visual surface aging detail only; not a restricted room, "
                "security feature, staff location, or operational access map."
            ),
        }
    )


def add_public_interior_surface_aging_details(
    obj: ObjWriter,
    labels: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> None:
    def add_floor_patch(
        name: str,
        kind: str,
        area: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
        material: str = "FloorWear",
        angle_degrees: float = 0.0,
    ) -> None:
        obj.add_oriented_box(center, size, 0.010, z, math.radians(angle_degrees), name, material)
        add_surface_aging_detail_record(records, name, kind, area, (center[0], center[1], z + 0.005), size, material)

    def add_wall_patch(
        name: str,
        kind: str,
        area: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
        height: float,
        material: str = "StoneGrimeOverlay",
    ) -> None:
        obj.add_box(center, size, height, z, name, material)
        add_surface_aging_detail_record(records, name, kind, area, (center[0], center[1], z + height / 2.0), size, material)

    room_specs = [
        ("rotunda_surface_aging", "Rotunda", (0.0, 0.0), (29.5, 29.5), 4.50),
        ("house_chamber_surface_aging", "House Chamber", (0.0, -72.0), (62.0, 42.0), 4.58),
        ("senate_chamber_surface_aging", "Senate Chamber", (0.0, 68.0), (48.0, 38.0), 4.58),
        ("statuary_hall_surface_aging", "National Statuary Hall", (28.0, -30.0), (30.0, 20.0), 4.47),
        ("old_senate_surface_aging", "Old Senate Chamber", (28.0, 30.0), (26.0, 18.0), 4.47),
        ("house_gallery_surface_aging", "House galleries", (0.0, -96.0), (68.0, 10.0), 4.92),
        ("senate_gallery_surface_aging", "Senate galleries", (0.0, 94.0), (54.0, 10.0), 4.92),
        ("house_west_office_surface_aging", "House leadership/support offices - schematic zone", (-53.0, -55.0), (22.0, 46.0), 4.62),
        ("house_east_office_surface_aging", "House committee/support rooms - schematic zone", (53.0, -55.0), (22.0, 46.0), 4.62),
        ("senate_west_office_surface_aging", "Senate leadership/support offices - schematic zone", (-52.0, 55.0), (22.0, 46.0), 4.62),
        ("senate_east_office_surface_aging", "Senate committee/support rooms - schematic zone", (52.0, 55.0), (22.0, 46.0), 4.62),
    ]
    for prefix, area, center, size, floor_z in room_specs:
        cx, cy = center
        sx, sy = size
        north_y = cy + sy / 2.0 - 0.34
        south_y = cy - sy / 2.0 + 0.34
        east_x = cx + sx / 2.0 - 0.34
        west_x = cx - sx / 2.0 + 0.34
        add_floor_patch(f"{prefix}_north_baseboard_dust_shadow", "baseboard_dust_shadow", area, (cx, north_y - 0.16), (sx * 0.82, 0.18), floor_z + 0.026)
        add_floor_patch(f"{prefix}_south_baseboard_dust_shadow", "baseboard_dust_shadow", area, (cx, south_y + 0.16), (sx * 0.82, 0.18), floor_z + 0.026)
        add_floor_patch(f"{prefix}_east_baseboard_dust_shadow", "baseboard_dust_shadow", area, (east_x - 0.16, cy), (0.18, sy * 0.82), floor_z + 0.026)
        add_floor_patch(f"{prefix}_west_baseboard_dust_shadow", "baseboard_dust_shadow", area, (west_x + 0.16, cy), (0.18, sy * 0.82), floor_z + 0.026)
        for corner_index, (x_sign, y_sign) in enumerate([(-1.0, -1.0), (1.0, -1.0), (-1.0, 1.0), (1.0, 1.0)], start=1):
            x = cx + x_sign * (sx / 2.0 - 0.44)
            y = cy + y_sign * (sy / 2.0 - 0.44)
            if corner_index % 2:
                add_wall_patch(f"{prefix}_corner_grime_streak_{corner_index:02d}", "wall_corner_grime_streak", area, (x, y), (0.34, 0.052), 4.54, 0.82)
            else:
                add_wall_patch(f"{prefix}_corner_grime_streak_{corner_index:02d}", "wall_corner_grime_streak", area, (x, y), (0.052, 0.34), 4.54, 0.82)
        sill_width = min(max(sx * 0.14 + 0.42, 2.05), 3.82)
        add_wall_patch(f"{prefix}_north_window_sill_dust_shadow", "window_sill_dust_shadow", area, (cx - sx * 0.22, north_y - 0.038), (sill_width, 0.044), 5.42, 0.055)
        add_wall_patch(f"{prefix}_south_window_sill_dust_shadow", "window_sill_dust_shadow", area, (cx + sx * 0.22, south_y + 0.038), (sill_width, 0.044), 5.42, 0.055)
        add_wall_patch(f"{prefix}_north_radiator_heat_stain", "radiator_heat_stain", area, (cx - sx * 0.22, north_y - 0.036), (sill_width * 0.78, 0.040), 5.05, 0.30)
        add_wall_patch(f"{prefix}_south_radiator_heat_stain", "radiator_heat_stain", area, (cx + sx * 0.22, south_y + 0.036), (sill_width * 0.78, 0.040), 5.05, 0.30)
        add_wall_patch(f"{prefix}_north_contact_smudge", "wall_contact_smudge", area, (cx + sx * 0.12, north_y - 0.040), (sx * 0.16, 0.040), 5.52, 0.18)
        add_wall_patch(f"{prefix}_south_contact_smudge", "wall_contact_smudge", area, (cx - sx * 0.12, south_y + 0.040), (sx * 0.16, 0.040), 5.50, 0.18)
        add_wall_patch(f"{prefix}_east_contact_smudge", "wall_contact_smudge", area, (east_x - 0.040, cy - sy * 0.12), (0.040, sy * 0.16), 5.50, 0.18)
        add_wall_patch(f"{prefix}_west_contact_smudge", "wall_contact_smudge", area, (west_x + 0.040, cy + sy * 0.12), (0.040, sy * 0.16), 5.52, 0.18)
        add_floor_patch(f"{prefix}_north_floor_mop_streak", "floor_mop_streak", area, (cx - sx * 0.16, north_y - 0.55), (sx * 0.22, 0.16), floor_z + 0.036, "FloorWear", 2.5)
        add_floor_patch(f"{prefix}_south_floor_mop_streak", "floor_mop_streak", area, (cx + sx * 0.16, south_y + 0.55), (sx * 0.22, 0.16), floor_z + 0.036, "FloorWear", -2.5)

    threshold_tracks = [
        ("west_public_approach_surface_track", "West terrace public orientation marker", (-55.0, 0.0), (1.10, 7.0), 4.57, 0.0),
        ("east_public_approach_surface_track", "East public approach / visitor circulation", (55.0, 0.0), (1.10, 7.0), 4.57, 0.0),
        ("rotunda_south_surface_track", "Rotunda / House Chamber orientation", (0.0, -50.0), (6.6, 0.58), 4.61, 0.0),
        ("rotunda_north_surface_track", "Rotunda / Senate public spine", (0.0, 50.0), (6.4, 0.58), 4.61, 0.0),
        ("house_gallery_surface_track", "House Chamber / public gallery", (0.0, -91.0), (8.0, 0.52), 4.81, 0.0),
        ("senate_gallery_surface_track", "Senate Chamber / public gallery", (0.0, 89.0), (7.2, 0.52), 4.81, 0.0),
        ("statuary_surface_track", "Rotunda / National Statuary Hall", (16.2, -15.8), (4.7, 0.52), 4.57, 0.0),
        ("old_senate_surface_track", "Rotunda / Old Senate Chamber", (16.2, 15.8), (4.5, 0.52), 4.57, 0.0),
    ]
    for name, area, center, size, z, angle in threshold_tracks:
        add_floor_patch(name, "threshold_dirt_track", area, center, size, z, "FloorWear", angle)
        add_floor_patch(f"{name}_offset", "threshold_dirt_track", area, (center[0] + size[0] * 0.13, center[1] - size[1] * 0.08), (size[0] * 0.58, size[1] * 0.30), z + 0.014, "FloorWear", angle + 2.0)
        if size[0] < size[1]:
            smudge_center = (center[0] - 0.055, center[1] + size[1] * 0.22)
            smudge_size = (0.050, min(1.10, size[1] * 0.20))
        else:
            smudge_center = (center[0] + size[0] * 0.22, center[1] - 0.055)
            smudge_size = (min(1.10, size[0] * 0.20), 0.050)
        add_wall_patch(f"{name}_public_hand_smudge", "door_pull_smudge", area, smudge_center, smudge_size, 5.28, 0.24)

    for index, x in enumerate([value * 3.2 for value in range(-7, 8)], start=1):
        add_floor_patch(f"house_member_desk_edge_wear_patch_{index:02d}", "desk_edge_wear_patch", "House Chamber", (x, -70.0 + (index % 4 - 1.5) * 4.3), (0.72, 0.18), 5.015, "FloorWear", -4.0 + index % 5)
        add_floor_patch(f"house_member_chair_leather_scuff_patch_{index:02d}", "chair_leather_scuff_patch", "House Chamber", (x, -80.0 + (index % 3 - 1) * 3.0), (0.46, 0.22), 5.000, "FloorWear", 3.0 - index % 4)

    for index, x in enumerate([value * 2.8 for value in range(-6, 7)], start=1):
        add_floor_patch(f"senate_desk_edge_wear_patch_{index:02d}", "desk_edge_wear_patch", "Senate Chamber", (x, 70.0 + (index % 4 - 1.5) * 3.2), (0.68, 0.18), 5.090, "FloorWear", 5.0 - index % 5)
        add_floor_patch(f"senate_chair_leather_scuff_patch_{index:02d}", "chair_leather_scuff_patch", "Senate Chamber", (x, 79.0 + (index % 3 - 1) * 2.6), (0.42, 0.22), 5.065, "FloorWear", -3.0 + index % 4)

    for index, x in enumerate([value * 5.0 for value in range(-6, 7)], start=1):
        add_floor_patch(f"house_gallery_seat_rub_shadow_{index:02d}", "gallery_seat_rub_shadow", "House galleries", (x, -100.0), (1.2, 0.18), 5.005, "FloorWear")
    for index, x in enumerate([value * 4.4 for value in range(-5, 6)], start=1):
        add_floor_patch(f"senate_gallery_seat_rub_shadow_{index:02d}", "gallery_seat_rub_shadow", "Senate galleries", (x, 97.5), (1.1, 0.18), 5.005, "FloorWear")

    brass_specs = [
        ("rotunda_floor_trim_tarnish", "Rotunda", (0.0, 10.7), (3.8, 0.13), 4.72),
        ("rotunda_medallion_tarnish_north", "Rotunda", (0.0, 3.05), (1.2, 0.11), 4.75),
        ("rotunda_medallion_tarnish_south", "Rotunda", (0.0, -3.05), (1.2, 0.11), 4.75),
        ("house_rostrum_rail_tarnish", "House Chamber", (0.0, -50.1), (7.2, 0.12), 4.86),
        ("senate_presiding_rail_tarnish", "Senate Chamber", (0.0, 84.1), (6.4, 0.12), 4.86),
        ("house_gallery_rail_tarnish", "House galleries", (0.0, -91.5), (12.0, 0.12), 5.10),
        ("senate_gallery_rail_tarnish", "Senate galleries", (0.0, 88.7), (10.0, 0.12), 5.10),
    ]
    for name, area, center, size, z in brass_specs:
        add_floor_patch(name, "brass_tarnish_patch", area, center, size, z, "FloorWear")

    add_label(labels, "Layered public surface aging: dust, scuffs, smudges, mop streaks, heat stains, contact shadows, and tarnish", -18.0, -10.0, 5.6, "surface_aging_detail")


def add_chamber_detail_record(
    records: list[dict[str, Any]],
    name: str,
    kind: str,
    chamber: str,
    center: tuple[float, float, float],
    size: tuple[float, float] | None = None,
) -> None:
    record: dict[str, Any] = {
        "name": name,
        "kind": kind,
        "chamber": chamber,
        "center_m": [round(center[0], 3), round(center[1], 3), round(center[2], 3)],
        "public_accuracy": "schematic_public_chamber_visual_detail",
        "assignment": "Public visual detail only; not an operational seating, security, or staff-placement record.",
    }
    if size is not None:
        record["size_m"] = [round(size[0], 3), round(size[1], 3)]
    records.append(record)


def add_generic_chamber_desk_surface_details(
    obj: ObjWriter,
    records: list[dict[str, Any]],
    prefix: str,
    chamber: str,
    center: tuple[float, float],
    surface_size: tuple[float, float],
    z: float,
) -> None:
    x, y = center
    sx, sy = surface_size
    paper_size = (sx * 0.34, sy * 0.34)
    nameplate_size = (sx * 0.58, sy * 0.08)
    obj.add_box((x - sx * 0.14, y + sy * 0.04), paper_size, 0.014, z, f"{prefix}_generic_document_stack", "LaneMarkingWhite")
    obj.add_box((x + sx * 0.20, y + sy * 0.18), (sx * 0.14, sy * 0.10), 0.042, z, f"{prefix}_generic_microphone_marker", "DoorMetal")
    obj.add_box((x, y - sy * 0.38), nameplate_size, 0.020, z + 0.006, f"{prefix}_generic_nameplate_strip", "BrassRail")
    add_chamber_detail_record(
        records,
        f"{prefix}_generic_document_stack",
        "generic_document_stack",
        chamber,
        (x - sx * 0.14, y + sy * 0.04, z + 0.007),
        paper_size,
    )
    add_chamber_detail_record(
        records,
        f"{prefix}_generic_microphone_marker",
        "generic_desk_microphone_marker",
        chamber,
        (x + sx * 0.20, y + sy * 0.18, z + 0.021),
        (sx * 0.14, sy * 0.10),
    )
    add_chamber_detail_record(
        records,
        f"{prefix}_generic_nameplate_strip",
        "generic_nameplate_strip",
        chamber,
        (x, y - sy * 0.38, z + 0.016),
        nameplate_size,
    )


def add_generic_chamber_furniture_finish_details(
    obj: ObjWriter,
    records: list[dict[str, Any]],
    prefix: str,
    chamber: str,
    desk_center: tuple[float, float],
    desk_size: tuple[float, float],
    desk_top_z: float,
    chair_center: tuple[float, float],
    chair_size: tuple[float, float],
    chair_top_z: float,
    chair_back_center: tuple[float, float],
    chair_back_size: tuple[float, float],
    chair_back_z: float,
    chair_back_height: float,
) -> None:
    desk_x, desk_y = desk_center
    desk_sx, desk_sy = desk_size
    edge_size = (desk_sx * 0.82, desk_sy * 0.075)
    for side, offset in [("front", -desk_sy * 0.44), ("rear", desk_sy * 0.44)]:
        obj.add_box(
            (desk_x, desk_y + offset),
            edge_size,
            0.026,
            desk_top_z,
            f"{prefix}_generic_desk_{side}_edge_trim",
            "BrassRail",
        )
    add_chamber_detail_record(
        records,
        f"{prefix}_generic_desk_edge_trim",
        "generic_desk_edge_trim",
        chamber,
        (desk_x, desk_y, desk_top_z + 0.013),
        (desk_sx * 0.82, desk_sy),
    )
    grain_strip_size = (desk_sx * 0.72, max(0.010, desk_sy * 0.026))
    grain_offsets = [-desk_sy * 0.18, desk_sy * 0.16]
    for grain_index, offset in enumerate(grain_offsets, start=1):
        obj.add_box(
            (desk_x, desk_y + offset),
            grain_strip_size,
            0.010,
            desk_top_z + 0.030 + grain_index * 0.002,
            f"{prefix}_generic_desk_wood_grain_strip_{grain_index}",
            "FloorWear",
        )
    add_chamber_detail_record(
        records,
        f"{prefix}_generic_desk_wood_grain_strips",
        "generic_desk_wood_grain_strip",
        chamber,
        (desk_x, desk_y, desk_top_z + 0.036),
        (desk_sx * 0.72, desk_sy * 0.38),
    )
    highlight_size = (desk_sx * 0.34, max(0.010, desk_sy * 0.030))
    obj.add_box(
        (desk_x + desk_sx * 0.18, desk_y - desk_sy * 0.08),
        highlight_size,
        0.010,
        desk_top_z + 0.045,
        f"{prefix}_generic_desk_varnish_highlight",
        "InteriorTrim",
    )
    add_chamber_detail_record(
        records,
        f"{prefix}_generic_desk_varnish_highlight",
        "generic_desk_varnish_highlight",
        chamber,
        (desk_x + desk_sx * 0.18, desk_y - desk_sy * 0.08, desk_top_z + 0.050),
        highlight_size,
    )

    chair_x, chair_y = chair_center
    cushion_size = (chair_size[0] * 0.74, chair_size[1] * 0.64)
    obj.add_box(
        (chair_x, chair_y),
        cushion_size,
        0.040,
        chair_top_z,
        f"{prefix}_generic_chair_cushion_inset",
        "ChairLeather",
    )
    add_chamber_detail_record(
        records,
        f"{prefix}_generic_chair_cushion",
        "generic_chair_cushion",
        chamber,
        (chair_x, chair_y, chair_top_z + 0.020),
        cushion_size,
    )
    seam_long = (cushion_size[0] * 0.82, max(0.012, cushion_size[1] * 0.035))
    seam_short = (max(0.012, cushion_size[0] * 0.035), cushion_size[1] * 0.82)
    obj.add_box((chair_x, chair_y), seam_long, 0.018, chair_top_z + 0.042, f"{prefix}_generic_chair_cushion_cross_seam", "DoorMetal")
    obj.add_box((chair_x, chair_y), seam_short, 0.018, chair_top_z + 0.043, f"{prefix}_generic_chair_cushion_center_seam", "DoorMetal")
    add_chamber_detail_record(
        records,
        f"{prefix}_generic_chair_cushion_seam",
        "generic_chair_cushion_seam",
        chamber,
        (chair_x, chair_y, chair_top_z + 0.052),
        cushion_size,
    )
    piping_long_size = (cushion_size[0] * 0.88, max(0.010, cushion_size[1] * 0.032))
    piping_short_size = (max(0.010, cushion_size[0] * 0.032), cushion_size[1] * 0.88)
    obj.add_box((chair_x, chair_y - cushion_size[1] * 0.45), piping_long_size, 0.012, chair_top_z + 0.064, f"{prefix}_generic_chair_front_piping", "DoorMetal")
    obj.add_box((chair_x, chair_y + cushion_size[1] * 0.45), piping_long_size, 0.012, chair_top_z + 0.065, f"{prefix}_generic_chair_rear_piping", "DoorMetal")
    obj.add_box((chair_x - cushion_size[0] * 0.45, chair_y), piping_short_size, 0.012, chair_top_z + 0.066, f"{prefix}_generic_chair_left_piping", "DoorMetal")
    obj.add_box((chair_x + cushion_size[0] * 0.45, chair_y), piping_short_size, 0.012, chair_top_z + 0.067, f"{prefix}_generic_chair_right_piping", "DoorMetal")
    add_chamber_detail_record(
        records,
        f"{prefix}_generic_chair_cushion_piping",
        "generic_chair_cushion_piping",
        chamber,
        (chair_x, chair_y, chair_top_z + 0.068),
        cushion_size,
    )
    leather_wear_size = (cushion_size[0] * 0.34, cushion_size[1] * 0.24)
    obj.add_box(
        (chair_x - cushion_size[0] * 0.15, chair_y + cushion_size[1] * 0.10),
        leather_wear_size,
        0.010,
        chair_top_z + 0.074,
        f"{prefix}_generic_chair_leather_wear_patch",
        "FloorWear",
    )
    add_chamber_detail_record(
        records,
        f"{prefix}_generic_chair_leather_wear_patch",
        "generic_chair_leather_wear_patch",
        chamber,
        (chair_x - cushion_size[0] * 0.15, chair_y + cushion_size[1] * 0.10, chair_top_z + 0.079),
        leather_wear_size,
    )
    arm_wear_size = (max(0.018, chair_size[0] * 0.055), chair_size[1] * 0.34)
    for arm_index, dx in enumerate([-chair_size[0] * 0.62, chair_size[0] * 0.62], start=1):
        obj.add_box(
            (chair_x + dx, chair_y),
            arm_wear_size,
            0.012,
            chair_top_z + 0.145,
            f"{prefix}_generic_chair_arm_wear_{arm_index}",
            "FloorWear",
        )
    add_chamber_detail_record(
        records,
        f"{prefix}_generic_chair_arm_wear",
        "generic_chair_arm_wear",
        chamber,
        (chair_x, chair_y, chair_top_z + 0.151),
        (chair_size[0] * 1.24, chair_size[1] * 0.34),
    )

    back_x, back_y = chair_back_center
    back_panel_size = (chair_back_size[0] * 0.70, 0.040)
    back_panel_height = chair_back_height * 0.54
    obj.add_box(
        (back_x, back_y - chair_back_size[1] * 0.34),
        back_panel_size,
        back_panel_height,
        chair_back_z + chair_back_height * 0.22,
        f"{prefix}_generic_chair_back_inset",
        "InteriorTrim",
    )
    add_chamber_detail_record(
        records,
        f"{prefix}_generic_chair_back_inset",
        "generic_chair_back_inset",
        chamber,
        (back_x, back_y - chair_back_size[1] * 0.34, chair_back_z + chair_back_height * 0.49),
        back_panel_size,
    )
    button_y = back_y - chair_back_size[1] * 0.46
    button_z = chair_back_z + chair_back_height * 0.54
    for button_index, dx in enumerate([-back_panel_size[0] * 0.24, back_panel_size[0] * 0.24], start=1):
        obj.add_cylinder(
            (back_x + dx, button_y),
            0.032,
            button_z,
            0.020,
            f"{prefix}_generic_chair_back_button_{button_index}",
            "DoorMetal",
            segments=8,
        )
    add_chamber_detail_record(
        records,
        f"{prefix}_generic_chair_back_buttons",
        "generic_chair_back_button",
        chamber,
        (back_x, button_y, button_z + 0.010),
        (back_panel_size[0] * 0.58, 0.08),
    )
    back_scuff_size = (back_panel_size[0] * 0.36, 0.034)
    obj.add_box(
        (back_x - back_panel_size[0] * 0.12, back_y - chair_back_size[1] * 0.49),
        back_scuff_size,
        0.105,
        chair_back_z + chair_back_height * 0.48,
        f"{prefix}_generic_chair_back_leather_scuff",
        "FloorWear",
    )
    add_chamber_detail_record(
        records,
        f"{prefix}_generic_chair_back_leather_scuff",
        "generic_chair_back_leather_scuff",
        chamber,
        (back_x - back_panel_size[0] * 0.12, back_y - chair_back_size[1] * 0.49, chair_back_z + chair_back_height * 0.53),
        back_scuff_size,
    )

    pull_y = desk_y - desk_sy * 0.50
    pull_size = (desk_sx * 0.40, max(0.018, desk_sy * 0.055))
    obj.add_box((desk_x, pull_y), pull_size, 0.034, desk_top_z - 0.17, f"{prefix}_generic_desk_drawer_pull", "BrassRail")
    add_chamber_detail_record(
        records,
        f"{prefix}_generic_desk_drawer_pull",
        "generic_desk_drawer_pull",
        chamber,
        (desk_x, pull_y, desk_top_z - 0.153),
        pull_size,
    )


def add_chamber_arc_strip(
    obj: ObjWriter,
    records: list[dict[str, Any]],
    name: str,
    chamber: str,
    center: tuple[float, float],
    radius: float,
    start_deg: float,
    end_deg: float,
    width: float,
    z: float,
    material: str,
    segments: int = 28,
) -> None:
    start = math.radians(start_deg)
    end = math.radians(end_deg)
    points = [
        (
            center[0] + radius * math.cos(start + (end - start) * idx / segments),
            center[1] + radius * math.sin(start + (end - start) * idx / segments),
        )
        for idx in range(segments + 1)
    ]
    obj.add_polyline_strip(points, width, z, name, material)
    midpoint = points[len(points) // 2]
    add_chamber_detail_record(records, name, "desk_arc_marker", chamber, (midpoint[0], midpoint[1], z), (radius * 2.0, width))


def add_chamber_realism_details(
    obj: ObjWriter,
    labels: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> None:
    def rail(name: str, chamber: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        obj.add_box(center, size, 0.24, z, name, "BrassRail")
        add_chamber_detail_record(records, name, "rostrum_rail", chamber, (center[0], center[1], z + 0.12), size)

    def step(name: str, chamber: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        obj.add_box(center, size, 0.10, z, name, "StepStone")
        add_chamber_detail_record(records, name, "dais_step", chamber, (center[0], center[1], z + 0.05), size)

    def gallery_rail(name: str, chamber: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        obj.add_box(center, size, 0.72, z, name, "BrassRail")
        add_chamber_detail_record(records, name, "gallery_rail", chamber, (center[0], center[1], z + 0.36), size)

    def aisle(name: str, chamber: str, points: list[tuple[float, float]], z: float) -> None:
        obj.add_polyline_strip(points, 0.12, z, name, "BrassRail")
        mid = points[len(points) // 2]
        add_chamber_detail_record(records, name, "aisle_edge", chamber, (mid[0], mid[1], z), None)

    def backdrop_panel(name: str, chamber: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        obj.add_box(center, size, 2.1, z, name, "InteriorTrim")
        add_chamber_detail_record(records, name, "backdrop_panel", chamber, (center[0], center[1], z + 1.05), size)

    def rostrum_desk(name: str, chamber: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        obj.add_box(center, size, 0.42, z, f"{name}_desk_box", "DeskWood")
        obj.add_box((center[0], center[1] + size[1] * 0.34), (size[0] * 0.78, 0.14), 0.38, z + 0.36, f"{name}_raised_lip", "InteriorTrim")
        front_panel_center = (center[0], center[1] - size[1] * 0.38)
        front_panel_size = (size[0] * 0.58, 0.070)
        obj.add_box(front_panel_center, front_panel_size, 0.18, z + 0.12, f"{name}_front_panel_detail", "InteriorTrim")
        for pull_index, dx in enumerate([-size[0] * 0.18, size[0] * 0.18], start=1):
            obj.add_box((center[0] + dx, center[1] - size[1] * 0.43), (0.18, 0.040), 0.045, z + 0.32, f"{name}_brass_pull_{pull_index}", "BrassRail")
        add_chamber_detail_record(records, name, "rostrum_desk", chamber, (center[0], center[1], z + 0.21), size)
        add_chamber_detail_record(records, f"{name}_front_panel_detail", "rostrum_desk_front_panel_detail", chamber, (front_panel_center[0], front_panel_center[1], z + 0.21), front_panel_size)
        add_chamber_detail_record(records, f"{name}_brass_pull_detail", "rostrum_desk_brass_pull_detail", chamber, (center[0], center[1] - size[1] * 0.43, z + 0.342), (size[0] * 0.42, 0.050))

    def gallery_bench(
        name: str,
        chamber: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
        orientation: str,
    ) -> None:
        obj.add_box(center, size, 0.18, z, f"{name}_seat", "DeskWood")
        if orientation == "east_west":
            back_center = (center[0], center[1] + size[1] * 0.38)
            back_size = (size[0], 0.12)
            obj.add_box(back_center, back_size, 0.55, z + 0.14, f"{name}_back", "ChairLeather")
            for slat_index, y_offset in enumerate([-0.14, 0.0, 0.14], start=1):
                slat_center = (center[0], center[1] + y_offset)
                obj.add_box(slat_center, (size[0] * 0.92, 0.050), 0.030, z + 0.18, f"{name}_seat_slat_{slat_index:02d}", "InteriorTrim")
                add_chamber_detail_record(records, f"{name}_seat_slat_{slat_index:02d}", "gallery_bench_seat_slat", chamber, (slat_center[0], slat_center[1], z + 0.195), (size[0] * 0.92, 0.050))
            for bracket_index, x_offset in enumerate([-size[0] * 0.32, size[0] * 0.32], start=1):
                bracket_center = (center[0] + x_offset, center[1] + size[1] * 0.08)
                obj.add_box(bracket_center, (0.070, size[1] * 0.56), 0.22, z - 0.04, f"{name}_support_bracket_{bracket_index:02d}", "DoorMetal")
                add_chamber_detail_record(records, f"{name}_support_bracket_{bracket_index:02d}", "gallery_bench_support_bracket", chamber, (bracket_center[0], bracket_center[1], z + 0.07), (0.070, size[1] * 0.56))
        else:
            back_center = (center[0] + size[0] * 0.38, center[1])
            back_size = (0.12, size[1])
            obj.add_box(back_center, back_size, 0.55, z + 0.14, f"{name}_back", "ChairLeather")
            for slat_index, x_offset in enumerate([-0.14, 0.0, 0.14], start=1):
                slat_center = (center[0] + x_offset, center[1])
                obj.add_box(slat_center, (0.050, size[1] * 0.92), 0.030, z + 0.18, f"{name}_seat_slat_{slat_index:02d}", "InteriorTrim")
                add_chamber_detail_record(records, f"{name}_seat_slat_{slat_index:02d}", "gallery_bench_seat_slat", chamber, (slat_center[0], slat_center[1], z + 0.195), (0.050, size[1] * 0.92))
            for bracket_index, y_offset in enumerate([-size[1] * 0.32, size[1] * 0.32], start=1):
                bracket_center = (center[0] + size[0] * 0.08, center[1] + y_offset)
                obj.add_box(bracket_center, (size[0] * 0.56, 0.070), 0.22, z - 0.04, f"{name}_support_bracket_{bracket_index:02d}", "DoorMetal")
                add_chamber_detail_record(records, f"{name}_support_bracket_{bracket_index:02d}", "gallery_bench_support_bracket", chamber, (bracket_center[0], bracket_center[1], z + 0.07), (size[0] * 0.56, 0.070))
        add_chamber_detail_record(records, f"{name}_back", "gallery_bench_back_panel", chamber, (back_center[0], back_center[1], z + 0.415), back_size)
        add_chamber_detail_record(records, name, "gallery_bench", chamber, (center[0], center[1], z + 0.16), size)

    def flag_standard(name: str, chamber: str, x: float, y: float, z: float, flag_material: str) -> None:
        obj.add_cylinder((x, y), 0.055, z, 2.3, f"{name}_pole", "BrassRail", segments=10)
        obj.add_cylinder((x, y), 0.15, z + 2.3, 0.18, f"{name}_finial", "BrassRail", segments=12)
        obj.add_box((x + 0.28, y), (0.55, 0.08), 0.68, z + 1.35, f"{name}_cloth_panel", flag_material)
        for fold_index, dx in enumerate([0.12, 0.26, 0.40], start=1):
            obj.add_box((x + dx, y + 0.006), (0.030, 0.088), 0.62, z + 1.38, f"{name}_cloth_fold_{fold_index}", "FloorWear")
            add_chamber_detail_record(records, f"{name}_cloth_fold_{fold_index}", "chamber_flag_fold_strip", chamber, (x + dx, y + 0.006, z + 1.69), (0.030, 0.088))
        for stripe_index in range(4):
            stripe_z = z + 1.13 + stripe_index * 0.14
            stripe_material = "LaneMarkingWhite" if stripe_index % 2 == 0 else flag_material
            obj.add_box((x + 0.30, y - 0.002), (0.47, 0.090), 0.025, stripe_z, f"{name}_stripe_{stripe_index+1}", stripe_material)
            add_chamber_detail_record(records, f"{name}_stripe_{stripe_index+1}", "chamber_flag_stripe_detail", chamber, (x + 0.30, y - 0.002, stripe_z + 0.013), (0.47, 0.090))
        obj.add_box((x + 0.12, y - 0.004), (0.18, 0.095), 0.16, z + 1.55, f"{name}_canton_marker", "MarkerBlue")
        add_chamber_detail_record(records, name, "flag_standard", chamber, (x, y, z + 1.15), (0.7, 0.18))
        add_chamber_detail_record(records, f"{name}_cloth_panel", "chamber_flag_cloth_panel", chamber, (x + 0.28, y, z + 1.69), (0.55, 0.08))
        add_chamber_detail_record(records, f"{name}_canton_marker", "chamber_flag_canton_marker", chamber, (x + 0.12, y - 0.004, z + 1.63), (0.18, 0.095))

    def public_lectern(name: str, chamber: str, center: tuple[float, float], z: float) -> None:
        x, y = center
        obj.add_box((x, y), (0.78, 0.46), 0.82, z, f"{name}_base", "DeskWood")
        obj.add_box((x, y + 0.03), (0.92, 0.54), 0.12, z + 0.82, f"{name}_sloped_top", "InteriorTrim")
        obj.add_box((x, y - 0.32), (0.18, 0.12), 0.22, z + 0.92, f"{name}_microphone_marker", "DoorMetal")
        obj.add_box((x + 0.24, y + 0.13), (0.06, 0.28), 0.055, z + 1.00, f"{name}_reading_lamp_arm", "LightFixtureMetal")
        obj.add_box((x + 0.24, y + 0.30), (0.26, 0.08), 0.060, z + 1.03, f"{name}_reading_lamp_lens", "WarmLightGlass")
        add_chamber_detail_record(records, name, "public_lectern", chamber, (x, y, z + 0.58), (0.92, 0.54))
        add_chamber_detail_record(records, f"{name}_reading_lamp", "public_lectern_reading_lamp", chamber, (x + 0.24, y + 0.24, z + 1.03), (0.28, 0.18))

    def public_work_table(
        name: str,
        chamber: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
    ) -> None:
        x, y = center
        sx, sy = size
        obj.add_box(center, size, 0.26, z, f"{name}_tabletop", "DeskWood")
        for post_index, (dx, dy) in enumerate(
            [(-sx * 0.38, -sy * 0.32), (sx * 0.38, -sy * 0.32), (-sx * 0.38, sy * 0.32), (sx * 0.38, sy * 0.32)],
            start=1,
        ):
            obj.add_box((x + dx, y + dy), (0.10, 0.10), 0.62, z - 0.58, f"{name}_leg_{post_index}", "DeskWood")
        obj.add_box((x + sx * 0.24, y + sy * 0.20), (0.08, sy * 0.42), 0.050, z + 0.28, f"{name}_reading_lamp_arm", "LightFixtureMetal")
        obj.add_box((x + sx * 0.24, y + sy * 0.43), (0.34, 0.08), 0.060, z + 0.31, f"{name}_reading_lamp_lens", "WarmLightGlass")
        add_chamber_detail_record(records, name, "public_work_table", chamber, (x, y, z + 0.13), size)
        add_chamber_detail_record(records, f"{name}_reading_lamp", "public_work_table_lamp", chamber, (x + sx * 0.24, y + sy * 0.33, z + 0.31), (0.36, 0.20))

    def gallery_divider(name: str, chamber: str, center: tuple[float, float], orientation: str, z: float) -> None:
        x, y = center
        if orientation == "north_south":
            size = (0.14, 1.42)
        else:
            size = (1.42, 0.14)
        obj.add_box(center, size, 0.46, z, name, "BrassRail")
        add_chamber_detail_record(records, name, "gallery_divider", chamber, (x, y, z + 0.23), size)

    def balcony_fascia(name: str, chamber: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        obj.add_box(center, size, 0.44, z, name, "InteriorTrim")
        add_chamber_detail_record(records, name, "balcony_fascia", chamber, (center[0], center[1], z + 0.22), size)

    def desk_surface_marker(name: str, chamber: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        obj.add_box(center, size, 0.035, z, name, "BrassRail")
        add_chamber_detail_record(records, name, "desk_surface_marker", chamber, (center[0], center[1], z + 0.018), size)

    def aisle_step_light(name: str, chamber: str, center: tuple[float, float], z: float, orientation: str) -> None:
        if orientation == "east_west":
            size = (0.36, 0.10)
        else:
            size = (0.10, 0.36)
        obj.add_box(center, size, 0.045, z, f"{name}_warm_lens", "WarmLightGlass")
        obj.add_box(center, (size[0] * 1.18, size[1] * 1.18), 0.026, z - 0.012, f"{name}_metal_trim", "LightFixtureMetal")
        add_chamber_detail_record(records, name, "aisle_step_light", chamber, (center[0], center[1], z + 0.022), size)

    def row_marker_plaque(name: str, chamber: str, center: tuple[float, float], orientation: str, z: float) -> None:
        size = (0.64, 0.08) if orientation == "east_west" else (0.08, 0.64)
        obj.add_box(center, size, 0.20, z, f"{name}_brass_plate", "BrassRail")
        obj.add_box(center, (size[0] * 0.64, size[1] * 0.64), 0.035, z + 0.16, f"{name}_dark_letter_bar", "DoorMetal")
        add_chamber_detail_record(records, name, "row_marker_plaque", chamber, (center[0], center[1], z + 0.10), size)

    def rostrum_microphone_cluster(name: str, chamber: str, center: tuple[float, float], z: float, count: int) -> None:
        x, y = center
        for idx in range(count):
            offset = (idx - (count - 1) / 2.0) * 0.18
            obj.add_cylinder((x + offset, y), 0.028, z, 0.32, f"{name}_stem_{idx+1:02d}", "DoorMetal", segments=8)
            obj.add_cylinder((x + offset, y + 0.04), 0.050, z + 0.30, 0.08, f"{name}_head_{idx+1:02d}", "LightFixtureMetal", segments=8)
        add_chamber_detail_record(records, name, "rostrum_microphone_cluster", chamber, (x, y, z + 0.18), (0.18 * count, 0.20))

    def gallery_stanchion(name: str, chamber: str, center: tuple[float, float], z: float) -> None:
        x, y = center
        obj.add_cylinder((x, y), 0.12, z, 0.07, f"{name}_round_base", "DoorMetal", segments=12)
        obj.add_cylinder((x, y), 0.045, z + 0.05, 0.66, f"{name}_post", "BrassRail", segments=10)
        obj.add_cylinder((x, y), 0.085, z + 0.70, 0.08, f"{name}_cap", "BrassRail", segments=10)
        add_chamber_detail_record(records, name, "gallery_stanchion", chamber, (x, y, z + 0.38), (0.24, 0.24))

    def gallery_rail_baluster(name: str, chamber: str, center: tuple[float, float], z: float) -> None:
        x, y = center
        obj.add_cylinder((x, y), 0.035, z, 0.66, f"{name}_slender_post", "BrassRail", segments=8)
        obj.add_cylinder((x, y), 0.060, z + 0.64, 0.045, f"{name}_small_cap", "BrassRail", segments=8)
        add_chamber_detail_record(records, name, "gallery_rail_baluster", chamber, (x, y, z + 0.34), (0.12, 0.12))

    def gallery_support_column(name: str, chamber: str, center: tuple[float, float], z: float, height: float) -> None:
        x, y = center
        obj.add_cylinder((x, y), 0.18, z, height, f"{name}_shaft", "ColumnStone", segments=14)
        obj.add_cylinder((x, y), 0.30, z - 0.08, 0.12, f"{name}_base", "ColumnStone", segments=14)
        obj.add_cylinder((x, y), 0.28, z + height - 0.02, 0.14, f"{name}_capital", "ColumnStone", segments=14)
        add_chamber_detail_record(records, name, "gallery_support_column", chamber, (x, y, z + height / 2.0), (0.60, 0.60))

    def public_display_board(
        name: str,
        chamber: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
        orientation: str,
    ) -> None:
        x, y = center
        obj.add_box(center, size, 1.05, z, f"{name}_dark_panel", "DoorMetal")
        obj.add_box(center, (size[0] * 1.18, size[1] * 1.18), 0.08, z - 0.05, f"{name}_lower_frame", "BrassRail")
        obj.add_box(center, (size[0] * 1.18, size[1] * 1.18), 0.08, z + 1.05, f"{name}_upper_frame", "BrassRail")
        side_frame_size = (size[0] * 1.18, max(0.10, size[1] * 0.045)) if size[0] >= size[1] else (max(0.10, size[0] * 0.45), size[1] * 1.18)
        if size[0] >= size[1]:
            side_offsets = [(0.0, -size[1] * 0.56), (0.0, size[1] * 0.56)]
        else:
            side_offsets = [(-size[0] * 0.56, 0.0), (size[0] * 0.56, 0.0)]
        for frame_index, (dx, dy) in enumerate(side_offsets, start=1):
            obj.add_box((x + dx, y + dy), side_frame_size, 1.12, z - 0.03, f"{name}_side_frame_{frame_index}", "BrassRail")
        for idx in range(4):
            if orientation == "east_west":
                indicator_center = (x, y - size[1] * 0.30 + idx * size[1] * 0.20)
                indicator_size = (size[0] * 1.25, size[1] * 0.055)
            else:
                indicator_center = (x - size[0] * 0.30 + idx * size[0] * 0.20, y)
                indicator_size = (size[0] * 0.055, size[1] * 1.25)
            obj.add_box(indicator_center, indicator_size, 0.035, z + 0.52, f"{name}_indicator_strip_{idx+1}", "WarmLightGlass")
        add_chamber_detail_record(records, name, "public_display_board", chamber, (x, y, z + 0.52), size)
        add_chamber_detail_record(records, f"{name}_frame_detail", "public_display_board_frame_detail", chamber, (x, y, z + 0.56), (size[0] * 1.22, size[1] * 1.22))

    def chamber_wall_panel(
        name: str,
        chamber: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
        height: float,
    ) -> None:
        x, y = center
        obj.add_box(center, size, height, z, f"{name}_field", "PaintingCanvas")
        obj.add_box(center, (size[0] * 1.28, size[1] * 1.16), 0.085, z - 0.05, f"{name}_lower_trim", "InteriorTrim")
        obj.add_box(center, (size[0] * 1.28, size[1] * 1.16), 0.085, z + height - 0.03, f"{name}_upper_trim", "InteriorTrim")
        add_chamber_detail_record(records, name, "chamber_wall_acoustic_panel", chamber, (x, y, z + height / 2.0), size)

    def chamber_wall_sconce(
        name: str,
        chamber: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
    ) -> None:
        x, y = center
        obj.add_box(center, (size[0] * 1.35, size[1] * 1.35), 0.52, z, f"{name}_metal_backplate", "LightFixtureMetal")
        obj.add_box(center, size, 0.34, z + 0.10, f"{name}_warm_glass", "WarmLightGlass")
        add_chamber_detail_record(records, name, "chamber_wall_sconce_fixture", chamber, (x, y, z + 0.26), size)

    def chamber_wall_pilaster(
        name: str,
        chamber: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
        height: float,
    ) -> None:
        x, y = center
        obj.add_box(center, size, height, z, f"{name}_shaft", "InteriorTrim")
        obj.add_box(center, (size[0] * 1.45, size[1] * 1.45), 0.16, z - 0.06, f"{name}_base", "BrassRail")
        obj.add_box(center, (size[0] * 1.45, size[1] * 1.45), 0.16, z + height - 0.02, f"{name}_capital", "BrassRail")
        add_chamber_detail_record(records, name, "chamber_wall_pilaster_strip", chamber, (x, y, z + height / 2.0), size)

    def gallery_edge_trim(name: str, chamber: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        x, y = center
        obj.add_box(center, size, 0.12, z, f"{name}_brass_edge", "BrassRail")
        obj.add_box(center, (size[0] * 0.94, size[1] * 0.94), 0.055, z + 0.10, f"{name}_shadow_line", "DoorMetal")
        add_chamber_detail_record(records, name, "gallery_edge_trim", chamber, (x, y, z + 0.06), size)

    def chamber_upper_wall_frieze(name: str, chamber: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        x, y = center
        obj.add_box(center, size, 0.18, z, f"{name}_field", "InteriorTrim")
        obj.add_box(center, (size[0] * 0.72, size[1] * 0.72), 0.055, z + 0.16, f"{name}_inlay", "BrassRail")
        add_chamber_detail_record(records, name, "chamber_upper_wall_frieze_panel", chamber, (x, y, z + 0.09), size)

    def chamber_ceiling_cove(name: str, chamber: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        x, y = center
        obj.add_box(center, size, 0.16, z, f"{name}_cove_band", "InteriorTrim")
        obj.add_box(center, (size[0] * 0.88, size[1] * 0.88), 0.055, z + 0.14, f"{name}_brass_bead", "BrassRail")
        add_chamber_detail_record(records, name, "chamber_ceiling_cove_molding", chamber, (x, y, z + 0.08), size)

    def balcony_underside_coffer(name: str, chamber: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        x, y = center
        obj.add_box(center, size, 0.060, z, f"{name}_recessed_panel", "InteriorTrim")
        obj.add_box(center, (size[0] * 0.74, size[1] * 0.74), 0.035, z - 0.035, f"{name}_inner_shadow", "DoorMetal")
        add_chamber_detail_record(records, name, "balcony_underside_coffer", chamber, (x, y, z + 0.03), size)

    def chamber_public_light_globe(name: str, chamber: str, center: tuple[float, float], z: float) -> None:
        x, y = center
        obj.add_cylinder((x, y), 0.032, z, 0.44, f"{name}_stem", "LightFixtureMetal", segments=8)
        obj.add_cylinder((x, y), 0.15, z - 0.14, 0.20, f"{name}_warm_globe", "WarmLightGlass", segments=14)
        obj.add_cylinder((x, y), 0.18, z + 0.40, 0.05, f"{name}_ceiling_canopy", "BrassRail", segments=14)
        add_chamber_detail_record(records, name, "chamber_public_light_globe", chamber, (x, y, z + 0.10), (0.36, 0.36))

    def gallery_rail_ornament(
        name: str,
        chamber: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
        rosette_count: int,
    ) -> None:
        x, y = center
        horizontal = size[0] >= size[1]
        cap_size = (size[0] * 1.02, max(size[1] * 1.55, 0.20)) if horizontal else (max(size[0] * 1.55, 0.20), size[1] * 1.02)
        obj.add_box(center, cap_size, 0.08, z + 0.72, f"{name}_top_cap", "BrassRail")
        add_chamber_detail_record(records, f"{name}_top_cap", "gallery_rail_top_cap", chamber, (x, y, z + 0.76), cap_size)

        span = size[0] if horizontal else size[1]
        for idx in range(rosette_count):
            offset = -span * 0.42 + (span * 0.84) * idx / max(1, rosette_count - 1)
            rosette_center = (x + offset, y) if horizontal else (x, y + offset)
            obj.add_cylinder(rosette_center, 0.085, z + 0.795, 0.035, f"{name}_rosette_{idx+1:02d}", "ArtFrameGold", segments=12)
            add_chamber_detail_record(records, f"{name}_rosette_{idx+1:02d}", "gallery_rail_rosette", chamber, (rosette_center[0], rosette_center[1], z + 0.812), (0.17, 0.17))

    def chamber_carpet_runner(
        name: str,
        chamber: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
        material: str,
    ) -> None:
        x, y = center
        obj.add_box(center, size, 0.026, z, f"{name}_field", material)
        add_chamber_detail_record(records, name, "chamber_carpet_aisle_runner", chamber, (x, y, z + 0.013), size)
        horizontal = size[0] >= size[1]
        if horizontal:
            strip_size = (size[0], 0.045)
            strip_offsets = [(0.0, -size[1] / 2.0 + 0.055), (0.0, size[1] / 2.0 - 0.055)]
        else:
            strip_size = (0.045, size[1])
            strip_offsets = [(-size[0] / 2.0 + 0.055, 0.0), (size[0] / 2.0 - 0.055, 0.0)]
        for strip_index, (dx, dy) in enumerate(strip_offsets, start=1):
            strip_center = (x + dx, y + dy)
            strip_name = f"{name}_binding_strip_{strip_index}"
            obj.add_box(strip_center, strip_size, 0.018, z + 0.028, strip_name, "BrassRail")
            add_chamber_detail_record(
                records,
                strip_name,
                "chamber_carpet_binding_strip",
                chamber,
                (strip_center[0], strip_center[1], z + 0.037),
                strip_size,
            )
        weave_count = 3
        for weave_index in range(weave_count):
            ratio = (weave_index + 1) / (weave_count + 1)
            if horizontal:
                weave_center = (x - size[0] * 0.35 + size[0] * 0.70 * ratio, y)
                weave_size = (max(0.040, size[0] * 0.012), size[1] * 0.82)
            else:
                weave_center = (x, y - size[1] * 0.35 + size[1] * 0.70 * ratio)
                weave_size = (size[0] * 0.82, max(0.040, size[1] * 0.012))
            weave_name = f"{name}_subtle_weave_band_{weave_index+1}"
            obj.add_box(weave_center, weave_size, 0.010, z + 0.048 + weave_index * 0.002, weave_name, "FloorWear")
            add_chamber_detail_record(
                records,
                weave_name,
                "chamber_carpet_weave_band",
                chamber,
                (weave_center[0], weave_center[1], z + 0.054),
                weave_size,
            )
        for fringe_index, (dx, dy) in enumerate(strip_offsets, start=1):
            fringe_center = (x + dx * 1.02, y + dy * 1.02)
            fringe_name = f"{name}_edge_fringe_{fringe_index}"
            fringe_size = (strip_size[0] * 0.96, max(0.026, strip_size[1] * 0.45)) if horizontal else (max(0.026, strip_size[0] * 0.45), strip_size[1] * 0.96)
            obj.add_box(fringe_center, fringe_size, 0.009, z + 0.058 + fringe_index * 0.002, fringe_name, "InteriorTrim")
            add_chamber_detail_record(
                records,
                fringe_name,
                "chamber_carpet_edge_fringe",
                chamber,
                (fringe_center[0], fringe_center[1], z + 0.063),
                fringe_size,
            )

    def chamber_carpet_wear_path(
        name: str,
        chamber: str,
        center: tuple[float, float],
        size: tuple[float, float],
        z: float,
    ) -> None:
        obj.add_box(center, size, 0.014, z, name, "FloorWear")
        add_chamber_detail_record(records, name, "chamber_carpet_wear_path", chamber, (center[0], center[1], z + 0.007), size)

    def chamber_row_shadow_strip(name: str, chamber: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        obj.add_box(center, size, 0.016, z, name, "FloorWear")
        add_chamber_detail_record(records, name, "chamber_row_shadow_strip", chamber, (center[0], center[1], z + 0.008), size)

    def gallery_tread_nosing(name: str, chamber: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        obj.add_box(center, size, 0.026, z, f"{name}_brass_nosing", "BrassRail")
        shadow_size = (size[0] * 0.96, max(0.026, size[1] * 0.42)) if size[0] >= size[1] else (max(0.026, size[0] * 0.42), size[1] * 0.96)
        obj.add_box(center, shadow_size, 0.010, z - 0.012, f"{name}_dark_reveal", "DoorMetal")
        add_chamber_detail_record(records, name, "gallery_tread_nosing", chamber, (center[0], center[1], z + 0.013), size)

    def rostrum_backdrop_trim_inlay(name: str, chamber: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        obj.add_box(center, size, 0.040, z, name, "ArtFrameGold")
        add_chamber_detail_record(records, name, "rostrum_backdrop_trim_inlay", chamber, (center[0], center[1], z + 0.020), size)

    def chamber_carpet_medallion(
        name: str,
        chamber: str,
        center: tuple[float, float],
        radius: float,
        z: float,
        material: str,
    ) -> None:
        x, y = center
        obj.add_disk(center, radius, z, f"{name}_brass_outer_disk", "BrassRail", segments=36)
        obj.add_disk(center, radius * 0.72, z + 0.006, f"{name}_fabric_center_disk", material, segments=36)
        obj.add_box(center, (radius * 1.35, 0.035), 0.014, z + 0.010, f"{name}_horizontal_inlay", "ArtFrameGold")
        obj.add_box(center, (0.035, radius * 1.35), 0.014, z + 0.012, f"{name}_vertical_inlay", "ArtFrameGold")
        add_chamber_detail_record(records, name, "chamber_carpet_medallion", chamber, (x, y, z + 0.010), (radius * 2.0, radius * 2.0))

    def generic_rostrum_seal_medallion(
        name: str,
        chamber: str,
        center: tuple[float, float],
        radius: float,
        z: float,
    ) -> None:
        x, y = center
        obj.add_disk(center, radius, z, f"{name}_outer_disk", "ArtFrameGold", segments=36)
        obj.add_disk(center, radius * 0.74, z + 0.006, f"{name}_inner_disk", "PublicGallery", segments=36)
        obj.add_box(center, (radius * 1.18, 0.035), 0.014, z + 0.014, f"{name}_horizontal_mark", "BrassRail")
        obj.add_box(center, (0.035, radius * 1.18), 0.014, z + 0.018, f"{name}_vertical_mark", "BrassRail")
        add_chamber_detail_record(
            records,
            name,
            "generic_rostrum_seal_medallion",
            chamber,
            (x, y, z + 0.012),
            (radius * 2.0, radius * 2.0),
        )

    # House chamber public visual details.
    for runner_name, center, size in [
        ("house_center_aisle_carpet_runner", (0.0, -74.5), (1.48, 39.0)),
        ("house_well_cross_carpet_runner", (0.0, -55.8), (17.5, 0.72)),
        ("house_left_public_aisle_carpet_runner", (-24.5, -77.0), (0.86, 34.0)),
        ("house_right_public_aisle_carpet_runner", (24.5, -77.0), (0.86, 34.0)),
        ("house_gallery_front_carpet_runner", (0.0, -96.2), (61.0, 0.74)),
        ("house_gallery_rear_carpet_runner", (0.0, -101.4), (61.0, 0.72)),
    ]:
        chamber_carpet_runner(runner_name, "House Chamber", center, size, 4.635, "HouseCarpet")
    for wear_name, center, size in [
        ("house_center_aisle_carpet_wear_path", (0.0, -74.5), (0.72, 33.5)),
        ("house_well_cross_carpet_wear_path", (0.0, -55.5), (10.5, 0.38)),
        ("house_left_public_aisle_carpet_wear_path", (-24.5, -78.0), (0.42, 25.5)),
        ("house_right_public_aisle_carpet_wear_path", (24.5, -78.0), (0.42, 25.5)),
        ("house_front_rostrum_carpet_wear_path", (0.0, -59.0), (7.8, 0.36)),
        ("house_rear_gallery_carpet_wear_path", (0.0, -101.4), (46.0, 0.36)),
        ("house_front_gallery_carpet_wear_path", (0.0, -96.2), (46.0, 0.36)),
        ("house_member_floor_center_wear_path", (0.0, -87.0), (8.5, 0.34)),
    ]:
        chamber_carpet_wear_path(wear_name, "House Chamber", center, size, 4.668)
    for row in range(16):
        width = 20.0 + row * 2.2
        y = -70.0 - row * 1.42
        chamber_row_shadow_strip(
            f"house_member_row_shadow_strip_{row+1:02d}",
            "House Chamber",
            (0.0, y - 0.08),
            (width * 0.96, 0.052),
            4.665,
        )
    for row_index, y in enumerate([-96.0, -98.0, -100.0, -102.0], start=1):
        gallery_tread_nosing(f"house_gallery_tread_{row_index:02d}_front_nosing", "House Chamber", (0.0, y - 0.32), (62.0, 0.060), 4.83 + row_index * 0.14)
        gallery_tread_nosing(f"house_gallery_tread_{row_index:02d}_rear_nosing", "House Chamber", (0.0, y + 0.32), (62.0, 0.060), 4.83 + row_index * 0.14)
    for medallion_name, center, radius in [
        ("house_front_well_carpet_medallion", (0.0, -60.3), 0.54),
        ("house_rear_member_floor_carpet_medallion", (0.0, -90.2), 0.64),
    ]:
        chamber_carpet_medallion(medallion_name, "House Chamber", center, radius, 4.688, "HouseCarpet")
    rail("house_rostrum_front_brass_rail", "House Chamber", (0.0, -50.75), (14.6, 0.16), 5.42)
    rail("house_rostrum_left_brass_rail", "House Chamber", (-7.25, -48.7), (0.16, 4.1), 5.42)
    rail("house_rostrum_right_brass_rail", "House Chamber", (7.25, -48.7), (0.16, 4.1), 5.42)
    generic_rostrum_seal_medallion("house_rostrum_generic_public_seal_medallion", "House Chamber", (0.0, -48.15), 0.56, 5.93)
    for idx, y in enumerate([-51.55, -52.05, -52.55], start=1):
        step(f"house_rostrum_step_tread_{idx}", "House Chamber", (0.0, y), (15.6 - idx * 0.8, 0.32), 4.58 + idx * 0.08)
    for idx, x in enumerate([-5.0, -3.0, -1.0, 1.0, 3.0, 5.0], start=1):
        backdrop_panel(f"house_rostrum_backdrop_panel_{idx}", "House Chamber", (x, -46.45), (1.35, 0.12), 5.05)
        rostrum_backdrop_trim_inlay(f"house_rostrum_backdrop_panel_{idx}_left_inlay", "House Chamber", (x - 0.58, -46.39), (0.045, 0.10), 6.68)
        rostrum_backdrop_trim_inlay(f"house_rostrum_backdrop_panel_{idx}_right_inlay", "House Chamber", (x + 0.58, -46.39), (0.045, 0.10), 6.68)
    gallery_rail("house_gallery_front_brass_rail", "House Chamber", (0.0, -95.15), (66.0, 0.16), 5.24)
    gallery_rail("house_gallery_rear_brass_rail", "House Chamber", (0.0, -103.7), (66.0, 0.16), 5.54)
    gallery_rail_ornament("house_gallery_front_ornament", "House Chamber", (0.0, -95.15), (66.0, 0.16), 5.24, 9)
    gallery_rail_ornament("house_gallery_rear_ornament", "House Chamber", (0.0, -103.7), (66.0, 0.16), 5.54, 9)
    for idx, x in enumerate([value * 4.0 for value in range(-8, 9)], start=1):
        gallery_rail_baluster(f"house_gallery_front_baluster_{idx:02d}", "House Chamber", (x, -95.15), 5.27)
        gallery_rail_baluster(f"house_gallery_rear_baluster_{idx:02d}", "House Chamber", (x, -103.7), 5.57)
    aisle("house_center_aisle_left_edge", "House Chamber", [(-0.82, -54.0), (-0.82, -95.0)], 4.62)
    aisle("house_center_aisle_right_edge", "House Chamber", [(0.82, -54.0), (0.82, -95.0)], 4.62)
    aisle("house_left_aisle_outer_edge", "House Chamber", [(-15.4, -56.0), (-28.4, -95.0)], 4.62)
    aisle("house_right_aisle_outer_edge", "House Chamber", [(15.4, -56.0), (28.4, -95.0)], 4.62)
    flag_standard("house_rostrum_us_flag_left", "House Chamber", -6.35, -46.95, 5.05, "MarkerBlue")
    flag_standard("house_rostrum_us_flag_right", "House Chamber", 6.35, -46.95, 5.05, "ItemCloth")
    add_chamber_arc_strip(obj, records, "house_front_desk_arc_marker", "House Chamber", (0.0, -50.5), 21.5, 214.0, 326.0, 0.10, 4.64, "BrassRail")
    add_chamber_arc_strip(obj, records, "house_rear_desk_arc_marker", "House Chamber", (0.0, -50.5), 39.5, 218.0, 322.0, 0.10, 4.64, "BrassRail")
    public_lectern("house_well_public_lectern", "House Chamber", (0.0, -54.25), 4.62)
    public_work_table("house_clerk_public_work_table", "House Chamber", (0.0, -50.9), (4.8, 0.82), 5.16)
    public_work_table("house_press_public_work_table", "House Chamber", (0.0, -57.3), (5.8, 0.72), 4.82)
    balcony_fascia("house_gallery_front_balcony_fascia", "House Chamber", (0.0, -94.72), (66.5, 0.42), 5.76)
    balcony_fascia("house_gallery_rear_balcony_fascia", "House Chamber", (0.0, -104.05), (66.5, 0.38), 5.92)
    gallery_edge_trim("house_gallery_front_lower_edge_trim", "House Chamber", (0.0, -94.50), (66.5, 0.10), 5.62)
    gallery_edge_trim("house_gallery_front_upper_edge_trim", "House Chamber", (0.0, -94.92), (66.5, 0.10), 6.04)
    gallery_edge_trim("house_gallery_rear_lower_edge_trim", "House Chamber", (0.0, -103.86), (66.5, 0.10), 5.78)
    gallery_edge_trim("house_gallery_rear_upper_edge_trim", "House Chamber", (0.0, -104.24), (66.5, 0.10), 6.12)
    for idx, x in enumerate([-30.0, -22.0, -14.0, -6.0, 6.0, 14.0, 22.0, 30.0], start=1):
        gallery_divider(f"house_gallery_divider_{idx:02d}", "House Chamber", (x, -99.9), "north_south", 5.42)
    for row_index, (y, width) in enumerate(
        [(-69.0, 24.0), (-74.7, 32.8), (-80.4, 41.6), (-86.1, 50.4), (-91.8, 58.0)],
        start=1,
    ):
        desk_surface_marker(f"house_floor_row_surface_marker_{row_index:02d}", "House Chamber", (0.0, y), (width, 0.08), 4.98)
    for idx, y in enumerate([-58.0, -62.0, -66.0, -70.0, -74.0, -78.0, -82.0, -86.0, -90.0, -94.0], start=1):
        aisle_step_light(f"house_center_aisle_step_light_left_{idx:02d}", "House Chamber", (-1.02, y), 4.67, "east_west")
        aisle_step_light(f"house_center_aisle_step_light_right_{idx:02d}", "House Chamber", (1.02, y), 4.67, "east_west")
    for idx, y in enumerate([-61.0, -66.5, -72.0, -77.5, -83.0, -88.5, -94.0], start=1):
        row_marker_plaque(f"house_left_row_marker_plaque_{idx:02d}", "House Chamber", (-31.0, y), "north_south", 4.93)
        row_marker_plaque(f"house_right_row_marker_plaque_{idx:02d}", "House Chamber", (31.0, y), "north_south", 4.93)
    for idx, (x, y, sx, sy) in enumerate(
        [(0.0, -48.7, 3.8, 0.92), (-3.2, -49.8, 2.2, 0.72), (3.2, -49.8, 2.2, 0.72), (0.0, -52.1, 5.4, 0.72)],
        start=1,
    ):
        rostrum_desk(f"house_rostrum_generic_desk_{idx}", "House Chamber", (x, y), (sx, sy), 5.02)
        rostrum_microphone_cluster(f"house_rostrum_microphone_cluster_{idx}", "House Chamber", (x, y - sy * 0.22), 5.50, 3)
    for row_index, y in enumerate([-96.4, -98.4, -100.4, -102.4], start=1):
        for col_index, x in enumerate([-28.0, -20.0, -12.0, -4.0, 4.0, 12.0, 20.0, 28.0], start=1):
            gallery_bench(
                f"house_gallery_bench_r{row_index:02d}_c{col_index:02d}",
                "House Chamber",
                (x, y),
                (5.2, 0.42),
                4.98 + row_index * 0.14,
                "east_west",
            )
    for idx, x in enumerate([-32.0, -24.0, -16.0, -8.0, 8.0, 16.0, 24.0, 32.0], start=1):
        gallery_stanchion(f"house_gallery_front_stanchion_{idx:02d}", "House Chamber", (x, -94.55), 5.28)
        gallery_stanchion(f"house_gallery_rear_stanchion_{idx:02d}", "House Chamber", (x, -103.35), 5.60)
    for idx, x in enumerate([-30.0, -18.0, -6.0, 6.0, 18.0, 30.0], start=1):
        gallery_support_column(f"house_gallery_front_support_column_{idx:02d}", "House Chamber", (x, -94.35), 4.72, 2.10)
        gallery_support_column(f"house_gallery_rear_support_column_{idx:02d}", "House Chamber", (x, -103.15), 4.88, 2.00)
    public_display_board("house_west_public_display_board", "House Chamber", (-30.8, -68.0), (0.10, 5.4), 6.25, "east_west")
    public_display_board("house_east_public_display_board", "House Chamber", (30.8, -68.0), (0.10, 5.4), 6.25, "east_west")
    for side, x in [("west", -30.85), ("east", 30.85)]:
        for panel_index, y in enumerate([-56.0, -61.0, -66.0, -71.0, -76.0, -81.0, -86.0, -91.0], start=1):
            chamber_wall_panel(f"house_{side}_wall_acoustic_panel_{panel_index:02d}", "House Chamber", (x, y), (0.16, 2.15), 5.10, 1.38)
        for sconce_index, y in enumerate([-58.5, -66.5, -74.5, -82.5, -90.5], start=1):
            chamber_wall_sconce(f"house_{side}_wall_sconce_{sconce_index:02d}", "House Chamber", (x, y), (0.13, 0.52), 6.34)
        for pilaster_index, y in enumerate([-53.0, -59.0, -65.0, -71.0, -77.0, -83.0, -89.0, -94.0], start=1):
            chamber_wall_pilaster(f"house_{side}_wall_pilaster_{pilaster_index:02d}", "House Chamber", (x, y), (0.18, 0.28), 4.92, 2.28)
    for panel_index, x in enumerate([-28.0, -20.0, -12.0, -4.0, 4.0, 12.0, 20.0, 28.0], start=1):
        chamber_wall_panel(f"house_rear_gallery_wall_panel_{panel_index:02d}", "House Chamber", (x, -103.55), (3.05, 0.16), 5.28, 1.12)
    for sconce_index, x in enumerate([-24.0, -12.0, 0.0, 12.0, 24.0], start=1):
        chamber_wall_sconce(f"house_rear_gallery_wall_sconce_{sconce_index:02d}", "House Chamber", (x, -103.75), (0.44, 0.12), 6.48)
    for pilaster_index, x in enumerate([-32.0, -24.0, -16.0, -8.0, 0.0, 8.0, 16.0, 24.0, 32.0], start=1):
        chamber_wall_pilaster(f"house_rear_gallery_wall_pilaster_{pilaster_index:02d}", "House Chamber", (x, -103.9), (0.24, 0.18), 5.02, 2.05)
    for side, x in [("west", -30.95), ("east", 30.95)]:
        for panel_index, y in enumerate([-55.0, -60.0, -65.0, -70.0, -75.0, -80.0, -85.0, -90.0], start=1):
            chamber_upper_wall_frieze(f"house_{side}_upper_wall_frieze_{panel_index:02d}", "House Chamber", (x, y), (0.14, 1.92), 6.98)
            chamber_ceiling_cove(f"house_{side}_ceiling_cove_{panel_index:02d}", "House Chamber", (x, y), (0.18, 1.98), 7.30)
    for panel_index, x in enumerate([-28.0, -20.0, -12.0, -4.0, 4.0, 12.0, 20.0, 28.0], start=1):
        chamber_upper_wall_frieze(f"house_rear_upper_wall_frieze_{panel_index:02d}", "House Chamber", (x, -104.02), (2.80, 0.14), 7.02)
        chamber_ceiling_cove(f"house_rear_ceiling_cove_{panel_index:02d}", "House Chamber", (x, -104.08), (2.86, 0.18), 7.34)
    for rail_name, y in [("front", -94.72), ("rear", -103.96)]:
        for coffer_index, x in enumerate([-29.5, -23.0, -16.5, -10.0, -3.5, 3.5, 10.0, 16.5, 23.0, 29.5], start=1):
            balcony_underside_coffer(f"house_gallery_{rail_name}_underside_coffer_{coffer_index:02d}", "House Chamber", (x, y), (3.70, 0.30), 5.42)
    for side, x in [("west", -29.2), ("east", 29.2)]:
        for light_index, y in enumerate([-58.0, -66.0, -74.0, -82.0, -90.0], start=1):
            chamber_public_light_globe(f"house_{side}_upper_light_globe_{light_index:02d}", "House Chamber", (x, y), 7.05)
    for light_index, x in enumerate([-24.0, -12.0, 0.0, 12.0, 24.0], start=1):
        chamber_public_light_globe(f"house_rear_gallery_light_globe_{light_index:02d}", "House Chamber", (x, -101.8), 7.10)

    # Senate chamber public visual details.
    for runner_name, center, size in [
        ("senate_center_aisle_carpet_runner", (0.0, 73.0), (1.30, 22.0)),
        ("senate_well_cross_carpet_runner", (0.0, 80.1), (14.0, 0.68)),
        ("senate_left_public_aisle_carpet_runner", (-15.2, 73.5), (0.82, 18.0)),
        ("senate_right_public_aisle_carpet_runner", (15.2, 73.5), (0.82, 18.0)),
        ("senate_gallery_front_carpet_runner", (0.0, 94.85), (49.0, 0.70)),
        ("senate_gallery_rear_carpet_runner", (0.0, 99.8), (49.0, 0.68)),
    ]:
        chamber_carpet_runner(runner_name, "Senate Chamber", center, size, 4.635, "SenateCarpet")
    for wear_name, center, size in [
        ("senate_center_aisle_carpet_wear_path", (0.0, 73.0), (0.66, 18.5)),
        ("senate_well_cross_carpet_wear_path", (0.0, 80.1), (8.8, 0.34)),
        ("senate_left_public_aisle_carpet_wear_path", (-15.2, 73.7), (0.38, 14.0)),
        ("senate_right_public_aisle_carpet_wear_path", (15.2, 73.7), (0.38, 14.0)),
        ("senate_front_gallery_carpet_wear_path", (0.0, 94.85), (37.0, 0.34)),
        ("senate_rear_gallery_carpet_wear_path", (0.0, 99.8), (37.0, 0.34)),
    ]:
        chamber_carpet_wear_path(wear_name, "Senate Chamber", center, size, 4.668)
    for row in range(10):
        width = 13.0 + row * 2.2
        y = 65.0 + row * 1.35
        chamber_row_shadow_strip(
            f"senate_desk_row_shadow_strip_{row+1:02d}",
            "Senate Chamber",
            (0.0, y - 0.08),
            (width * 0.96, 0.052),
            4.665,
        )
    for row_index, y in enumerate([94.8, 96.6, 98.4, 100.2], start=1):
        gallery_tread_nosing(f"senate_gallery_tread_{row_index:02d}_front_nosing", "Senate Chamber", (0.0, y - 0.30), (49.0, 0.056), 4.81 + row_index * 0.14)
        gallery_tread_nosing(f"senate_gallery_tread_{row_index:02d}_rear_nosing", "Senate Chamber", (0.0, y + 0.30), (49.0, 0.056), 4.81 + row_index * 0.14)
    for medallion_name, center, radius in [
        ("senate_front_well_carpet_medallion", (0.0, 62.8), 0.50),
        ("senate_rear_floor_carpet_medallion", (0.0, 87.2), 0.56),
    ]:
        chamber_carpet_medallion(medallion_name, "Senate Chamber", center, radius, 4.688, "SenateCarpet")
    rail("senate_presiding_front_brass_rail", "Senate Chamber", (0.0, 81.85), (12.0, 0.16), 5.36)
    rail("senate_presiding_left_brass_rail", "Senate Chamber", (-6.0, 83.25), (0.16, 2.8), 5.36)
    rail("senate_presiding_right_brass_rail", "Senate Chamber", (6.0, 83.25), (0.16, 2.8), 5.36)
    generic_rostrum_seal_medallion("senate_presiding_generic_public_seal_medallion", "Senate Chamber", (0.0, 84.02), 0.50, 5.88)
    for idx, y in enumerate([81.0, 80.55], start=1):
        step(f"senate_presiding_step_tread_{idx}", "Senate Chamber", (0.0, y), (12.6 - idx * 0.6, 0.30), 4.58 + idx * 0.08)
    for idx, x in enumerate([-4.2, -2.1, 0.0, 2.1, 4.2], start=1):
        backdrop_panel(f"senate_presiding_backdrop_panel_{idx}", "Senate Chamber", (x, 85.15), (1.35, 0.12), 5.02)
        rostrum_backdrop_trim_inlay(f"senate_presiding_backdrop_panel_{idx}_left_inlay", "Senate Chamber", (x - 0.58, 85.09), (0.045, 0.10), 6.64)
        rostrum_backdrop_trim_inlay(f"senate_presiding_backdrop_panel_{idx}_right_inlay", "Senate Chamber", (x + 0.58, 85.09), (0.045, 0.10), 6.64)
    gallery_rail("senate_gallery_front_brass_rail", "Senate Chamber", (0.0, 94.05), (52.0, 0.16), 5.22)
    gallery_rail("senate_gallery_rear_brass_rail", "Senate Chamber", (0.0, 101.2), (52.0, 0.16), 5.52)
    gallery_rail_ornament("senate_gallery_front_ornament", "Senate Chamber", (0.0, 94.05), (52.0, 0.16), 5.22, 7)
    gallery_rail_ornament("senate_gallery_rear_ornament", "Senate Chamber", (0.0, 101.2), (52.0, 0.16), 5.52, 7)
    for idx, x in enumerate([value * 3.6 for value in range(-7, 8)], start=1):
        gallery_rail_baluster(f"senate_gallery_front_baluster_{idx:02d}", "Senate Chamber", (x, 94.05), 5.25)
        gallery_rail_baluster(f"senate_gallery_rear_baluster_{idx:02d}", "Senate Chamber", (x, 101.2), 5.55)
    aisle("senate_center_aisle_left_edge", "Senate Chamber", [(-0.72, 62.0), (-0.72, 83.0)], 4.62)
    aisle("senate_center_aisle_right_edge", "Senate Chamber", [(0.72, 62.0), (0.72, 83.0)], 4.62)
    aisle("senate_left_aisle_outer_edge", "Senate Chamber", [(-9.45, 63.0), (-18.45, 82.0)], 4.62)
    aisle("senate_right_aisle_outer_edge", "Senate Chamber", [(9.45, 63.0), (18.45, 82.0)], 4.62)
    flag_standard("senate_presiding_us_flag_left", "Senate Chamber", -5.2, 84.55, 5.0, "MarkerBlue")
    flag_standard("senate_presiding_us_flag_right", "Senate Chamber", 5.2, 84.55, 5.0, "ItemCloth")
    add_chamber_arc_strip(obj, records, "senate_front_desk_arc_marker", "Senate Chamber", (0.0, 84.0), 12.2, 205.0, 335.0, 0.10, 4.64, "BrassRail")
    add_chamber_arc_strip(obj, records, "senate_rear_desk_arc_marker", "Senate Chamber", (0.0, 84.0), 25.0, 209.0, 331.0, 0.10, 4.64, "BrassRail")
    public_lectern("senate_well_public_lectern", "Senate Chamber", (0.0, 79.55), 4.62)
    public_work_table("senate_clerk_public_work_table", "Senate Chamber", (0.0, 82.15), (4.2, 0.74), 5.08)
    public_work_table("senate_press_public_work_table", "Senate Chamber", (0.0, 77.2), (4.6, 0.66), 4.82)
    balcony_fascia("senate_gallery_front_balcony_fascia", "Senate Chamber", (0.0, 93.65), (52.5, 0.40), 5.74)
    balcony_fascia("senate_gallery_rear_balcony_fascia", "Senate Chamber", (0.0, 101.55), (52.5, 0.36), 5.90)
    gallery_edge_trim("senate_gallery_front_lower_edge_trim", "Senate Chamber", (0.0, 93.45), (52.5, 0.10), 5.60)
    gallery_edge_trim("senate_gallery_front_upper_edge_trim", "Senate Chamber", (0.0, 93.85), (52.5, 0.10), 6.02)
    gallery_edge_trim("senate_gallery_rear_lower_edge_trim", "Senate Chamber", (0.0, 101.38), (52.5, 0.10), 5.76)
    gallery_edge_trim("senate_gallery_rear_upper_edge_trim", "Senate Chamber", (0.0, 101.72), (52.5, 0.10), 6.08)
    for idx, x in enumerate([-23.5, -16.5, -9.5, -2.5, 2.5, 9.5, 16.5, 23.5], start=1):
        gallery_divider(f"senate_gallery_divider_{idx:02d}", "Senate Chamber", (x, 97.9), "north_south", 5.42)
    for row_index, (y, width) in enumerate(
        [(66.3, 15.0), (70.4, 21.6), (74.5, 28.2), (78.6, 34.8), (82.7, 39.5)],
        start=1,
    ):
        desk_surface_marker(f"senate_floor_row_surface_marker_{row_index:02d}", "Senate Chamber", (0.0, y), (width, 0.08), 4.98)
    for idx, y in enumerate([63.5, 66.8, 70.1, 73.4, 76.7, 80.0, 83.3, 86.6], start=1):
        aisle_step_light(f"senate_center_aisle_step_light_left_{idx:02d}", "Senate Chamber", (-0.92, y), 4.67, "east_west")
        aisle_step_light(f"senate_center_aisle_step_light_right_{idx:02d}", "Senate Chamber", (0.92, y), 4.67, "east_west")
    for idx, y in enumerate([65.0, 69.0, 73.0, 77.0, 81.0], start=1):
        row_marker_plaque(f"senate_left_row_marker_plaque_{idx:02d}", "Senate Chamber", (-22.4, y), "north_south", 4.93)
        row_marker_plaque(f"senate_right_row_marker_plaque_{idx:02d}", "Senate Chamber", (22.4, y), "north_south", 4.93)
    for idx, (x, y, sx, sy) in enumerate(
        [(0.0, 83.75, 3.2, 0.82), (-2.8, 82.7, 2.0, 0.66), (2.8, 82.7, 2.0, 0.66)],
        start=1,
    ):
        rostrum_desk(f"senate_presiding_generic_desk_{idx}", "Senate Chamber", (x, y), (sx, sy), 4.98)
        rostrum_microphone_cluster(f"senate_presiding_microphone_cluster_{idx}", "Senate Chamber", (x, y + sy * 0.22), 5.44, 3)
    for row_index, y in enumerate([94.8, 96.6, 98.4, 100.2], start=1):
        for col_index, x in enumerate([-21.0, -14.0, -7.0, 0.0, 7.0, 14.0, 21.0], start=1):
            gallery_bench(
                f"senate_gallery_bench_r{row_index:02d}_c{col_index:02d}",
                "Senate Chamber",
                (x, y),
                (4.8, 0.40),
                4.96 + row_index * 0.14,
                "east_west",
            )
    for idx, x in enumerate([-24.5, -17.5, -10.5, -3.5, 3.5, 10.5, 17.5, 24.5], start=1):
        gallery_stanchion(f"senate_gallery_front_stanchion_{idx:02d}", "Senate Chamber", (x, 93.55), 5.26)
        gallery_stanchion(f"senate_gallery_rear_stanchion_{idx:02d}", "Senate Chamber", (x, 101.00), 5.58)
    for idx, x in enumerate([-24.0, -14.4, -4.8, 4.8, 14.4, 24.0], start=1):
        gallery_support_column(f"senate_gallery_front_support_column_{idx:02d}", "Senate Chamber", (x, 93.35), 4.72, 2.02)
        gallery_support_column(f"senate_gallery_rear_support_column_{idx:02d}", "Senate Chamber", (x, 100.85), 4.88, 1.92)
    public_display_board("senate_west_public_display_board", "Senate Chamber", (-23.8, 70.0), (0.10, 4.6), 6.15, "east_west")
    public_display_board("senate_east_public_display_board", "Senate Chamber", (23.8, 70.0), (0.10, 4.6), 6.15, "east_west")
    for side, x in [("west", -23.85), ("east", 23.85)]:
        for panel_index, y in enumerate([62.0, 66.5, 71.0, 75.5, 80.0, 84.5], start=1):
            chamber_wall_panel(f"senate_{side}_wall_acoustic_panel_{panel_index:02d}", "Senate Chamber", (x, y), (0.16, 1.85), 5.06, 1.28)
        for sconce_index, y in enumerate([64.0, 72.0, 80.0, 86.0], start=1):
            chamber_wall_sconce(f"senate_{side}_wall_sconce_{sconce_index:02d}", "Senate Chamber", (x, y), (0.12, 0.48), 6.28)
        for pilaster_index, y in enumerate([60.2, 65.0, 69.8, 74.6, 79.4, 84.2, 88.2], start=1):
            chamber_wall_pilaster(f"senate_{side}_wall_pilaster_{pilaster_index:02d}", "Senate Chamber", (x, y), (0.17, 0.24), 4.90, 2.12)
    for panel_index, x in enumerate([-21.0, -14.0, -7.0, 0.0, 7.0, 14.0, 21.0], start=1):
        chamber_wall_panel(f"senate_rear_gallery_wall_panel_{panel_index:02d}", "Senate Chamber", (x, 101.35), (2.75, 0.15), 5.24, 1.05)
    for sconce_index, x in enumerate([-18.0, -9.0, 0.0, 9.0, 18.0], start=1):
        chamber_wall_sconce(f"senate_rear_gallery_wall_sconce_{sconce_index:02d}", "Senate Chamber", (x, 101.58), (0.40, 0.12), 6.42)
    for pilaster_index, x in enumerate([-24.0, -16.0, -8.0, 0.0, 8.0, 16.0, 24.0], start=1):
        chamber_wall_pilaster(f"senate_rear_gallery_wall_pilaster_{pilaster_index:02d}", "Senate Chamber", (x, 101.72), (0.22, 0.16), 4.98, 1.96)
    for side, x in [("west", -23.95), ("east", 23.95)]:
        for panel_index, y in enumerate([62.0, 66.5, 71.0, 75.5, 80.0, 84.5], start=1):
            chamber_upper_wall_frieze(f"senate_{side}_upper_wall_frieze_{panel_index:02d}", "Senate Chamber", (x, y), (0.13, 1.66), 6.86)
            chamber_ceiling_cove(f"senate_{side}_ceiling_cove_{panel_index:02d}", "Senate Chamber", (x, y), (0.17, 1.72), 7.18)
    for panel_index, x in enumerate([-21.0, -14.0, -7.0, 0.0, 7.0, 14.0, 21.0], start=1):
        chamber_upper_wall_frieze(f"senate_rear_upper_wall_frieze_{panel_index:02d}", "Senate Chamber", (x, 101.86), (2.45, 0.13), 6.94)
        chamber_ceiling_cove(f"senate_rear_ceiling_cove_{panel_index:02d}", "Senate Chamber", (x, 101.92), (2.51, 0.17), 7.24)
    for rail_name, y in [("front", 93.62), ("rear", 101.50)]:
        for coffer_index, x in enumerate([-22.5, -16.0, -9.5, -3.2, 3.2, 9.5, 16.0, 22.5], start=1):
            balcony_underside_coffer(f"senate_gallery_{rail_name}_underside_coffer_{coffer_index:02d}", "Senate Chamber", (x, y), (3.45, 0.28), 5.38)
    for side, x in [("west", -22.6), ("east", 22.6)]:
        for light_index, y in enumerate([64.0, 72.0, 80.0, 86.0], start=1):
            chamber_public_light_globe(f"senate_{side}_upper_light_globe_{light_index:02d}", "Senate Chamber", (x, y), 6.92)
    for light_index, x in enumerate([-18.0, -9.0, 0.0, 9.0, 18.0], start=1):
        chamber_public_light_globe(f"senate_rear_gallery_light_globe_{light_index:02d}", "Senate Chamber", (x, 99.8), 7.02)

    add_label(labels, "House and Senate chamber rails, dais steps, carpets, worn paths, wall panels, gallery trim, cove molding, and lights - schematic", 0.0, -43.0, 7.7, "chamber_detail")


def add_public_circulation_record(
    records: list[dict[str, Any]],
    name: str,
    kind: str,
    area: str,
    center: tuple[float, float, float],
    size: tuple[float, float] | None = None,
) -> None:
    record: dict[str, Any] = {
        "name": name,
        "kind": kind,
        "area": area,
        "center_m": [round(center[0], 3), round(center[1], 3), round(center[2], 3)],
        "public_accuracy": "schematic_public_circulation_visual_detail",
        "assignment": "Public orientation visual only; not a secure route, service route, evacuation route, or office assignment.",
    }
    if size is not None:
        record["size_m"] = [round(size[0], 3), round(size[1], 3)]
    records.append(record)


def add_public_circulation_details(
    obj: ObjWriter,
    labels: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> None:
    z = 4.49

    def corridor(name: str, area: str, points: list[tuple[float, float]], width: float) -> None:
        obj.add_polyline_strip(points, width, z, name, "RotundaFloor")
        center = polyline_midpoint(points)
        length = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:]))
        add_public_circulation_record(records, name, "public_corridor_band", area, (center[0], center[1], z), (length, width))

    def threshold(name: str, area: str, center: tuple[float, float], size: tuple[float, float]) -> None:
        obj.add_box(center, size, 0.055, z - 0.015, name, "StepStone")
        add_public_circulation_record(records, name, "door_threshold", area, (center[0], center[1], z), size)

    def portal(name: str, area: str, center: tuple[float, float], width: float, orientation: str) -> None:
        x, y = center
        if orientation == "east_west":
            post_size = (0.16, 0.24)
            lintel_size = (0.20, width + 0.50)
            transom_size = (0.075, width * 0.64)
            opening_size = (0.055, width * 0.74)
            jamb_size = (0.18, 0.34)
            post_offsets = [(0.0, -width / 2.0), (0.0, width / 2.0)]
        else:
            post_size = (0.24, 0.16)
            lintel_size = (width + 0.50, 0.20)
            transom_size = (width * 0.64, 0.075)
            opening_size = (width * 0.74, 0.055)
            jamb_size = (0.34, 0.18)
            post_offsets = [(-width / 2.0, 0.0), (width / 2.0, 0.0)]
        for idx, (dx, dy) in enumerate(post_offsets, start=1):
            obj.add_box((x + dx, y + dy), post_size, 2.35, 4.43, f"{name}_side_trim_{idx}", "InteriorTrim")
            obj.add_box((x + dx * 0.96, y + dy * 0.96), jamb_size, 2.05, 4.58, f"{name}_jamb_return_{idx}", "DoorMetal")
            add_public_circulation_record(records, f"{name}_jamb_return_{idx}", "public_portal_jamb_return", area, (x + dx * 0.96, y + dy * 0.96, 5.605), jamb_size)
        obj.add_box((x, y), opening_size, 1.98, 4.50, f"{name}_opening_shadow_panel", "DoorMetal")
        obj.add_box((x, y), lintel_size, 0.22, 6.78, f"{name}_header_trim", "InteriorTrim")
        obj.add_box((x, y), transom_size, 0.28, 6.34, f"{name}_public_transom_marker", "DoorGlass")
        add_public_circulation_record(records, f"{name}_opening_shadow_panel", "public_portal_opening_shadow", area, (x, y, 5.49), opening_size)
        add_public_circulation_record(records, name, "room_portal_trim", area, (x, y, 5.65), (width, 0.42))
        add_public_circulation_record(records, f"{name}_public_transom_marker", "public_portal_transom", area, (x, y, 6.48), transom_size)

    def sign(name: str, area: str, center: tuple[float, float], text: str) -> None:
        x, y = center
        obj.add_cylinder((x, y), 0.045, 4.48, 1.18, f"{name}_post", "BrassRail", segments=8)
        obj.add_box((x, y), (1.55, 0.10), 0.42, 5.55, f"{name}_blade", "MarkerBlue")
        add_public_circulation_record(records, name, "orientation_sign", area, (x, y, 5.75), (1.55, 0.42))
        add_label(labels, text, x, y, 6.55, "public_circulation_detail")

    def inlay(name: str, area: str, center: tuple[float, float], size: tuple[float, float]) -> None:
        obj.add_box(center, size, 0.035, z + 0.005, name, "BrassRail")
        add_public_circulation_record(records, name, "floor_inlay", area, (center[0], center[1], z + 0.02), size)

    def corridor_pilaster(name: str, area: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        shaft_size = (0.34, 0.16) if orientation == "east_west" else (0.16, 0.34)
        cap_size = (0.52, 0.22) if orientation == "east_west" else (0.22, 0.52)
        obj.add_box((x, y), shaft_size, 1.86, 4.45, f"{name}_shaft", "InteriorTrim")
        obj.add_box((x, y), cap_size, 0.16, 6.28, f"{name}_capital", "ArtFrameGold")
        obj.add_box((x, y), cap_size, 0.14, 4.36, f"{name}_base", "InteriorTrim")
        add_public_circulation_record(records, name, "public_corridor_pilaster", area, (x, y, 5.38), shaft_size)

    def corridor_sconce(name: str, area: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        plate_size = (0.12, 0.42) if orientation == "east_west" else (0.42, 0.12)
        arm_size = (0.42, 0.08) if orientation == "east_west" else (0.08, 0.42)
        obj.add_box((x, y), plate_size, 0.42, 5.68, f"{name}_backplate", "LightFixtureMetal")
        obj.add_box((x, y), arm_size, 0.07, 5.92, f"{name}_arm", "LightFixtureMetal")
        obj.add_cylinder((x, y), 0.13, 5.92, 0.22, f"{name}_warm_glass", "WarmLightGlass", segments=12)
        add_public_circulation_record(records, name, "public_corridor_sconce", area, (x, y, 5.98), plate_size)

    def floor_medallion(name: str, area: str, center: tuple[float, float], radius: float) -> None:
        x, y = center
        obj.add_cylinder((x, y), radius, z + 0.012, 0.035, f"{name}_brass_outer_ring", "BrassRail", segments=32)
        obj.add_cylinder((x, y), radius * 0.58, z + 0.052, 0.026, f"{name}_stone_center", "RotundaFloor", segments=32)
        add_public_circulation_record(records, name, "public_floor_medallion", area, (x, y, z + 0.045), (radius * 2.0, radius * 2.0))

    def direction_vector(direction: str) -> tuple[float, float]:
        vectors = {
            "east": (1.0, 0.0),
            "west": (-1.0, 0.0),
            "north": (0.0, 1.0),
            "south": (0.0, -1.0),
            "northeast": (1.0, 1.0),
            "northwest": (-1.0, 1.0),
            "southeast": (1.0, -1.0),
            "southwest": (-1.0, -1.0),
        }[direction]
        length = math.hypot(vectors[0], vectors[1])
        return (vectors[0] / length, vectors[1] / length)

    def route_arrow(name: str, area: str, center: tuple[float, float], direction: str) -> None:
        x, y = center
        vx, vy = direction_vector(direction)
        nx, ny = -vy, vx
        angle = math.atan2(vy, vx)
        stem_center = (x - vx * 0.28, y - vy * 0.28)
        tip = (x + vx * 0.58, y + vy * 0.58)
        base = (x + vx * 0.12, y + vy * 0.12)
        left = (base[0] + nx * 0.34, base[1] + ny * 0.34)
        right = (base[0] - nx * 0.34, base[1] - ny * 0.34)
        obj.add_oriented_box(stem_center, (0.74, 0.14), 0.026, z + 0.180, angle, f"{name}_stem", "MarkerBlue")
        obj.add_flat_polygon([tip, left, right], z + 0.218, f"{name}_head", "MarkerBlue")
        add_public_circulation_record(
            records,
            name,
            "public_route_floor_arrow",
            area,
            (x, y, z + 0.218),
            (1.28, 0.82),
        )

    def route_chevron(name: str, area: str, center: tuple[float, float], direction: str) -> None:
        x, y = center
        vx, vy = direction_vector(direction)
        angle = math.atan2(vy, vx)
        for side, offset in [("left", 0.30), ("right", -0.30)]:
            obj.add_oriented_box(
                (x - vx * 0.10, y - vy * 0.10),
                (0.62, 0.10),
                0.024,
                z + 0.225,
                angle + offset,
                f"{name}_{side}",
                "ArtFrameGold",
            )
        add_public_circulation_record(records, name, "public_route_chevron", area, (x, y, z + 0.237), (0.82, 0.58))

    def low_guide_rail(name: str, area: str, center: tuple[float, float], length: float, angle: float) -> None:
        x, y = center
        dx = math.cos(angle) * length / 2.0
        dy = math.sin(angle) * length / 2.0
        obj.add_oriented_box(center, (length, 0.10), 0.080, 5.18, angle, f"{name}_top_rail", "BrassRail")
        for post_index, (px, py) in enumerate([(x - dx, y - dy), (x + dx, y + dy)], start=1):
            obj.add_cylinder((px, py), 0.055, 4.58, 0.72, f"{name}_post_{post_index}", "BrassRail", segments=10)
        add_public_circulation_record(records, name, "public_low_guide_rail", area, (x, y, 5.22), (length, 0.72))

    def wall_size(width: float, depth: float, orientation: str) -> tuple[float, float]:
        if orientation == "east_west":
            return (width, depth)
        return (depth, width)

    def wall_along(center: tuple[float, float], offset: float, orientation: str) -> tuple[float, float]:
        x, y = center
        if orientation == "east_west":
            return (x + offset, y)
        return (x, y + offset)

    def wall_directory_board(name: str, area: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        board_size = wall_size(1.65, 0.12, orientation)
        obj.add_beveled_box(center, board_size, 0.76, 5.12, f"{name}_board", "MarkerBlue", 0.018)
        obj.add_box(center, wall_size(1.40, 0.045, orientation), 0.055, 5.78, f"{name}_header_strip", "ArtFrameGold")
        add_public_circulation_record(records, name, "public_directory_board", area, (x, y, 5.50), board_size)
        for line_index, (offset, width) in enumerate([(-0.44, 0.54), (-0.15, 0.96), (0.12, 0.78), (0.40, 0.62)], start=1):
            line_center = wall_along(center, offset, orientation)
            obj.add_box(line_center, wall_size(width, 0.030, orientation), 0.035, 5.26 + line_index * 0.105, f"{name}_line_glyph_{line_index}", "LaneMarkingWhite")
            add_public_circulation_record(
                records,
                f"{name}_line_glyph_{line_index}",
                "public_directory_line_glyph",
                area,
                (line_center[0], line_center[1], 5.278 + line_index * 0.105),
                wall_size(width, 0.030, orientation),
            )

    def wall_clock(name: str, area: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        obj.add_cylinder(center, 0.34, 5.78, 0.055, f"{name}_clock_face", "LaneMarkingWhite", segments=24)
        obj.add_cylinder(center, 0.37, 5.765, 0.035, f"{name}_clock_rim", "BrassRail", segments=24)
        hand_angle = 0.0 if orientation == "east_west" else math.pi / 2.0
        obj.add_oriented_box(center, (0.30, 0.026), 0.030, 5.86, hand_angle, f"{name}_long_hand", "DoorMetal")
        obj.add_oriented_box(center, (0.20, 0.026), 0.032, 5.895, hand_angle + math.pi / 2.0, f"{name}_short_hand", "DoorMetal")
        add_public_circulation_record(records, name, "public_wall_clock", area, (x, y, 5.82), (0.74, 0.74))
        add_public_circulation_record(records, f"{name}_hand_pair", "public_wall_clock_hand_pair", area, (x, y, 5.89), (0.36, 0.36))

    def public_safety_cabinet(name: str, area: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        cabinet_size = wall_size(0.72, 0.13, orientation)
        glass_size = wall_size(0.46, 0.035, orientation)
        obj.add_beveled_box(center, cabinet_size, 0.82, 4.92, f"{name}_red_frame", "TrafficSignalRed", 0.020)
        obj.add_box(center, glass_size, 0.52, 5.08, f"{name}_glass_panel", "DoorGlass")
        obj.add_box(wall_along(center, 0.31, orientation), wall_size(0.055, 0.040, orientation), 0.34, 5.16, f"{name}_small_pull", "BrassRail")
        add_public_circulation_record(records, name, "generic_public_safety_cabinet", area, (x, y, 5.33), cabinet_size)
        add_public_circulation_record(records, f"{name}_glass_panel", "generic_public_safety_cabinet_glass", area, (x, y, 5.34), glass_size)

    def emergency_light_block(name: str, area: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        block_size = wall_size(0.68, 0.12, orientation)
        lens_size = wall_size(0.18, 0.035, orientation)
        obj.add_beveled_box(center, block_size, 0.28, 6.24, f"{name}_body", "LightFixtureMetal", 0.014)
        for lens_index, offset in enumerate([-0.20, 0.20], start=1):
            lens_center = wall_along(center, offset, orientation)
            obj.add_box(lens_center, lens_size, 0.14, 6.34, f"{name}_warm_lens_{lens_index}", "WarmLightGlass")
        add_public_circulation_record(records, name, "generic_public_emergency_light_block", area, (x, y, 6.38), block_size)
        add_public_circulation_record(records, f"{name}_lens_pair", "generic_public_emergency_light_lens_pair", area, (x, y, 6.41), (0.58, 0.14))

    def wall_service_plates(name: str, area: str, center: tuple[float, float], orientation: str) -> None:
        switch_center = wall_along(center, -0.16, orientation)
        outlet_center = wall_along(center, 0.16, orientation)
        switch_size = wall_size(0.13, 0.026, orientation)
        outlet_size = wall_size(0.15, 0.026, orientation)
        obj.add_box(switch_center, switch_size, 0.20, 5.08, f"{name}_switch_plate", "LaneMarkingWhite")
        obj.add_box(switch_center, wall_size(0.045, 0.031, orientation), 0.055, 5.16, f"{name}_switch_toggle", "DoorMetal")
        obj.add_box(outlet_center, outlet_size, 0.18, 4.68, f"{name}_outlet_plate", "LaneMarkingWhite")
        for socket_index, z_offset in enumerate([0.04, 0.115], start=1):
            obj.add_box(outlet_center, wall_size(0.060, 0.031, orientation), 0.026, 4.70 + z_offset, f"{name}_outlet_slot_{socket_index}", "DoorMetal")
        add_public_circulation_record(records, f"{name}_switch_plate", "public_wall_switch_plate", area, (switch_center[0], switch_center[1], 5.18), switch_size)
        add_public_circulation_record(records, f"{name}_outlet_plate", "public_wall_outlet_plate", area, (outlet_center[0], outlet_center[1], 4.77), outlet_size)

    def transition_size(width: float, depth: float, orientation: str) -> tuple[float, float]:
        if orientation == "east_west":
            return (depth, width)
        return (width, depth)

    def transition_component_center(
        center: tuple[float, float],
        along_offset: float,
        normal_offset: float,
        orientation: str,
    ) -> tuple[float, float]:
        x, y = center
        if orientation == "east_west":
            return (x + normal_offset, y + along_offset)
        return (x + along_offset, y + normal_offset)

    def public_transition_surround(
        name: str,
        area: str,
        center: tuple[float, float],
        width: float,
        orientation: str,
    ) -> None:
        x, y = center
        surround_size = transition_size(width + 0.72, 0.20, orientation)
        mosaic_size = transition_size(width * 0.78, 0.34, orientation)
        header_size = transition_size(width + 0.96, 0.18, orientation)
        obj.add_box(center, surround_size, 0.18, 6.92, f"{name}_architrave_header_band", "ArtFrameGold")
        add_public_circulation_record(records, f"{name}_arch_surround", "public_transition_arch_surround", area, (x, y, 7.01), surround_size)

        for side, along_offset in [("left", -width / 2.0 - 0.28), ("right", width / 2.0 + 0.28)]:
            reveal_center = transition_component_center(center, along_offset, 0.0, orientation)
            reveal_size = transition_size(0.22, 0.18, orientation)
            obj.add_box(reveal_center, reveal_size, 2.05, 4.86, f"{name}_{side}_reveal_panel", "InteriorTrim")
            obj.add_box(reveal_center, transition_size(0.34, 0.24, orientation), 0.12, 6.84, f"{name}_{side}_reveal_cap", "BrassRail")
            add_public_circulation_record(records, f"{name}_{side}_reveal_panel", "public_transition_reveal_panel", area, (reveal_center[0], reveal_center[1], 5.89), reveal_size)

        keystone_center = transition_component_center(center, 0.0, 0.0, orientation)
        keystone_size = transition_size(0.54, 0.24, orientation)
        obj.add_box(keystone_center, keystone_size, 0.34, 7.18, f"{name}_keystone_block", "BrassRail")
        add_public_circulation_record(records, f"{name}_keystone_block", "public_transition_keystone", area, (x, y, 7.35), keystone_size)

        obj.add_box(center, mosaic_size, 0.038, z + 0.075, f"{name}_floor_mosaic_band", "ArtFrameGold")
        obj.add_box(center, transition_size(width * 0.42, 0.10, orientation), 0.044, z + 0.12, f"{name}_floor_mosaic_center_line", "BrassRail")
        add_public_circulation_record(records, f"{name}_floor_mosaic_band", "public_transition_floor_mosaic", area, (x, y, z + 0.095), mosaic_size)

        obj.add_box(center, header_size, 0.075, 7.32, f"{name}_upper_lintel_shadow", "DoorMetal")
        add_public_circulation_record(records, f"{name}_upper_lintel_shadow", "public_transition_lintel_shadow", area, (x, y, 7.36), header_size)

    def threshold_material_variation(
        name: str,
        area: str,
        center: tuple[float, float],
        width: float,
        orientation: str,
    ) -> None:
        x, y = center
        insert_size = transition_size(width * 0.58, 0.28, orientation)
        edge_size = transition_size(width * 0.72, 0.055, orientation)
        glow_size = transition_size(width * 0.82, 0.52, orientation)
        obj.add_box(center, insert_size, 0.030, z + 0.155, f"{name}_marble_threshold_insert", "RotundaFloor")
        add_public_circulation_record(records, f"{name}_marble_threshold_insert", "public_threshold_marble_insert", area, (x, y, z + 0.170), insert_size)

        for edge_index, normal_offset in enumerate([-0.20, 0.20], start=1):
            edge_center = transition_component_center(center, 0.0, normal_offset, orientation)
            obj.add_box(edge_center, edge_size, 0.026, z + 0.190, f"{name}_brass_threshold_edge_{edge_index}", "BrassRail")
            add_public_circulation_record(
                records,
                f"{name}_brass_threshold_edge_{edge_index}",
                "public_threshold_brass_edge",
                area,
                (edge_center[0], edge_center[1], z + 0.205),
                edge_size,
            )

        obj.add_box(center, glow_size, 0.018, z + 0.218, f"{name}_warm_transition_light_pool", "WarmLightGlass")
        add_public_circulation_record(records, f"{name}_warm_transition_light_pool", "public_transition_light_pool", area, (x, y, z + 0.227), glow_size)

    def public_level_transition_detail(
        name: str,
        area: str,
        center: tuple[float, float],
        width: float,
        orientation: str,
    ) -> None:
        x, y = center
        landing_size = transition_size(width * 0.92, 1.18, orientation)
        obj.add_box(center, landing_size, 0.040, z + 0.242, f"{name}_landing_slab", "StepStone")
        add_public_circulation_record(records, f"{name}_landing_slab", "public_level_transition_landing", area, (x, y, z + 0.262), landing_size)

        for tread_index, normal_offset in enumerate([-0.72, -0.42, 0.42, 0.72], start=1):
            tread_center = transition_component_center(center, 0.0, normal_offset, orientation)
            tread_size = transition_size(width * 0.86, 0.26, orientation)
            obj.add_box(tread_center, tread_size, 0.034, z + 0.265 + tread_index * 0.010, f"{name}_public_tread_{tread_index:02d}", "StepStone")
            add_public_circulation_record(
                records,
                f"{name}_public_tread_{tread_index:02d}",
                "public_level_transition_tread",
                area,
                (tread_center[0], tread_center[1], z + 0.292 + tread_index * 0.010),
                tread_size,
            )
            nosing_size = transition_size(width * 0.88, 0.045, orientation)
            nosing_center = transition_component_center(center, 0.0, normal_offset + (0.12 if normal_offset < 0.0 else -0.12), orientation)
            obj.add_box(nosing_center, nosing_size, 0.030, z + 0.318 + tread_index * 0.010, f"{name}_brass_nosing_{tread_index:02d}", "BrassRail")
            add_public_circulation_record(
                records,
                f"{name}_brass_nosing_{tread_index:02d}",
                "public_level_transition_nosing",
                area,
                (nosing_center[0], nosing_center[1], z + 0.333 + tread_index * 0.010),
                nosing_size,
            )

        for strip_index, normal_offset in enumerate([-0.96, 0.96], start=1):
            strip_center = transition_component_center(center, 0.0, normal_offset, orientation)
            strip_size = transition_size(width * 0.82, 0.075, orientation)
            obj.add_box(strip_center, strip_size, 0.026, z + 0.355, f"{name}_tactile_edge_strip_{strip_index:02d}", "LaneMarkingYellow")
            add_public_circulation_record(
                records,
                f"{name}_tactile_edge_strip_{strip_index:02d}",
                "public_level_transition_tactile_strip",
                area,
                (strip_center[0], strip_center[1], z + 0.368),
                strip_size,
            )

        ramp_center = transition_component_center(center, -width * 0.32, 0.0, orientation)
        ramp_size = transition_size(width * 0.18, 1.92, orientation)
        obj.add_box(ramp_center, ramp_size, 0.026, z + 0.335, f"{name}_schematic_ramp_panel", "InteriorFloor")
        add_public_circulation_record(records, f"{name}_schematic_ramp_panel", "public_accessibility_ramp_panel", area, (ramp_center[0], ramp_center[1], z + 0.348), ramp_size)

        for edge_index, along_delta in enumerate([-width * 0.11, width * 0.11], start=1):
            edge_center = transition_component_center(center, -width * 0.32 + along_delta, 0.0, orientation)
            edge_size = transition_size(0.045, 1.88, orientation)
            obj.add_box(edge_center, edge_size, 0.055, z + 0.350, f"{name}_schematic_ramp_edge_{edge_index:02d}", "BrassRail")
            add_public_circulation_record(
                records,
                f"{name}_schematic_ramp_edge_{edge_index:02d}",
                "public_accessibility_ramp_edge",
                area,
                (edge_center[0], edge_center[1], z + 0.378),
                edge_size,
            )

        rail_angle = 0.0 if orientation == "east_west" else math.pi / 2.0
        for rail_index, along_offset in enumerate([-width * 0.50, width * 0.50], start=1):
            rail_center = transition_component_center(center, along_offset, 0.0, orientation)
            obj.add_oriented_box(rail_center, (1.78, 0.075), 0.080, z + 0.930, rail_angle, f"{name}_public_handrail_{rail_index:02d}", "BrassRail")
            add_public_circulation_record(
                records,
                f"{name}_public_handrail_{rail_index:02d}",
                "public_level_transition_handrail",
                area,
                (rail_center[0], rail_center[1], z + 0.970),
                (1.78, 0.075),
            )
            for post_index, normal_offset in enumerate([-0.72, 0.72], start=1):
                post_center = transition_component_center(center, along_offset, normal_offset, orientation)
                obj.add_cylinder(post_center, 0.040, z + 0.330, 0.66, f"{name}_public_handrail_post_{rail_index:02d}_{post_index:02d}", "BrassRail", segments=8)
                add_public_circulation_record(
                    records,
                    f"{name}_public_handrail_post_{rail_index:02d}_{post_index:02d}",
                    "public_level_transition_handrail_post",
                    area,
                    (post_center[0], post_center[1], z + 0.660),
                    (0.08, 0.08),
                )

    corridor("east_west_public_axis_band", "Rotunda / east-west public approach", [(-68.0, 0.0), (-22.0, 0.0), (22.0, 0.0), (68.0, 0.0)], 5.2)
    corridor("rotunda_to_house_public_band", "Rotunda to House Chamber public orientation", [(0.0, -12.0), (0.0, -38.0), (0.0, -52.0)], 4.6)
    corridor("rotunda_to_senate_public_band", "Rotunda to Senate Chamber public orientation", [(0.0, 12.0), (0.0, 38.0), (0.0, 52.0)], 4.6)
    corridor("rotunda_to_statuary_hall_public_band", "Rotunda to National Statuary Hall", [(10.0, -8.0), (22.0, -18.0), (28.0, -26.0)], 3.6)
    corridor("rotunda_to_old_senate_public_band", "Rotunda to Old Senate Chamber", [(10.0, 8.0), (22.0, 18.0), (28.0, 26.0)], 3.4)
    corridor("house_gallery_public_band", "House gallery public orientation", [(0.0, -88.0), (0.0, -97.0)], 4.0)
    corridor("senate_gallery_public_band", "Senate gallery public orientation", [(0.0, 86.0), (0.0, 96.0)], 3.8)

    for name, area, center, size, orientation, width in [
        ("west_public_approach_threshold", "West terrace public orientation marker", (-55.0, 0.0), (0.72, 7.8), "east_west", 7.8),
        ("east_public_approach_threshold", "East public approach", (55.0, 0.0), (0.72, 7.8), "east_west", 7.8),
        ("rotunda_statuary_hall_threshold", "Rotunda / National Statuary Hall", (16.2, -15.8), (4.8, 0.62), "north_south", 4.8),
        ("rotunda_old_senate_threshold", "Rotunda / Old Senate Chamber", (16.2, 15.8), (4.6, 0.62), "north_south", 4.6),
        ("rotunda_house_threshold", "Rotunda / House Chamber orientation", (0.0, -51.0), (6.2, 0.70), "north_south", 6.2),
        ("rotunda_senate_threshold", "Rotunda / Senate Chamber orientation", (0.0, 51.0), (6.0, 0.70), "north_south", 6.0),
        ("house_gallery_threshold", "House Chamber / public gallery", (0.0, -91.0), (8.0, 0.62), "north_south", 8.0),
        ("senate_gallery_threshold", "Senate Chamber / public gallery", (0.0, 89.0), (7.0, 0.62), "north_south", 7.0),
    ]:
        threshold(name, area, center, size)
        portal(f"{name}_portal", area, center, width, orientation)
        public_transition_surround(f"{name}_public_transition", area, center, width, orientation)
        threshold_material_variation(f"{name}_material_variation", area, center, width, orientation)
        public_level_transition_detail(f"{name}_level_transition", area, center, width, orientation)

    for name, area, center, text in [
        ("rotunda_orientation_sign_west", "Rotunda", (-11.2, -3.8), "Rotunda / west public orientation"),
        ("rotunda_orientation_sign_east", "Rotunda", (11.2, 3.8), "Rotunda / east public orientation"),
        ("house_orientation_sign", "House Chamber approach", (-7.5, -53.5), "House Chamber public orientation"),
        ("senate_orientation_sign", "Senate Chamber approach", (7.5, 53.5), "Senate Chamber public orientation"),
        ("statuary_orientation_sign", "National Statuary Hall approach", (23.0, -22.0), "National Statuary Hall public marker"),
        ("old_senate_orientation_sign", "Old Senate Chamber approach", (23.0, 22.0), "Old Senate Chamber public marker"),
    ]:
        sign(name, area, center, text)

    for name, area, center, size in [
        ("rotunda_west_floor_inlay", "Rotunda", (-8.0, 0.0), (4.0, 0.16)),
        ("rotunda_east_floor_inlay", "Rotunda", (8.0, 0.0), (4.0, 0.16)),
        ("rotunda_north_floor_inlay", "Rotunda", (0.0, 8.0), (0.16, 4.0)),
        ("rotunda_south_floor_inlay", "Rotunda", (0.0, -8.0), (0.16, 4.0)),
        ("house_approach_floor_inlay", "House Chamber approach", (0.0, -42.0), (8.0, 0.14)),
        ("senate_approach_floor_inlay", "Senate Chamber approach", (0.0, 42.0), (8.0, 0.14)),
    ]:
        inlay(name, area, center, size)

    pilaster_specs: list[tuple[str, str, tuple[float, float], str]] = []
    for x in [-52.0, -36.0, -20.0, 20.0, 36.0, 52.0]:
        pilaster_specs.append(("east_west_axis_south", "Rotunda / east-west public approach", (x, -3.05), "east_west"))
        pilaster_specs.append(("east_west_axis_north", "Rotunda / east-west public approach", (x, 3.05), "east_west"))
    for y in [-44.0, -32.0, -20.0]:
        pilaster_specs.append(("house_axis_west", "Rotunda to House Chamber public orientation", (-2.75, y), "north_south"))
        pilaster_specs.append(("house_axis_east", "Rotunda to House Chamber public orientation", (2.75, y), "north_south"))
    for y in [20.0, 32.0, 44.0]:
        pilaster_specs.append(("senate_axis_west", "Rotunda to Senate Chamber public orientation", (-2.75, y), "north_south"))
        pilaster_specs.append(("senate_axis_east", "Rotunda to Senate Chamber public orientation", (2.75, y), "north_south"))
    for x in [-24.0, -12.0, 0.0, 12.0, 24.0]:
        pilaster_specs.append(("house_gallery_front", "House gallery public orientation", (x, -90.8), "east_west"))
        pilaster_specs.append(("senate_gallery_front", "Senate gallery public orientation", (x, 88.8), "east_west"))
    for index, (prefix, area, center, orientation) in enumerate(pilaster_specs, start=1):
        corridor_pilaster(f"{prefix}_public_corridor_pilaster_{index:02d}", area, center, orientation)

    sconce_specs: list[tuple[str, str, tuple[float, float], str]] = []
    for x in [-48.0, -28.0, -8.0, 8.0, 28.0, 48.0]:
        sconce_specs.append(("east_west_axis_south", "Rotunda / east-west public approach", (x, -2.72), "east_west"))
        sconce_specs.append(("east_west_axis_north", "Rotunda / east-west public approach", (x, 2.72), "east_west"))
    for y in [-42.0, -24.0]:
        sconce_specs.append(("house_axis_west", "Rotunda to House Chamber public orientation", (-2.42, y), "north_south"))
        sconce_specs.append(("house_axis_east", "Rotunda to House Chamber public orientation", (2.42, y), "north_south"))
    for y in [24.0, 42.0]:
        sconce_specs.append(("senate_axis_west", "Rotunda to Senate Chamber public orientation", (-2.42, y), "north_south"))
        sconce_specs.append(("senate_axis_east", "Rotunda to Senate Chamber public orientation", (2.42, y), "north_south"))
    for index, (prefix, area, center, orientation) in enumerate(sconce_specs, start=1):
        corridor_sconce(f"{prefix}_public_sconce_{index:02d}", area, center, orientation)

    for name, area, center, radius in [
        ("west_axis_public_floor_medallion", "Rotunda / east-west public approach", (-36.0, 0.0), 0.88),
        ("east_axis_public_floor_medallion", "Rotunda / east-west public approach", (36.0, 0.0), 0.88),
        ("house_axis_public_floor_medallion", "Rotunda to House Chamber public orientation", (0.0, -26.0), 0.78),
        ("senate_axis_public_floor_medallion", "Rotunda to Senate Chamber public orientation", (0.0, 26.0), 0.78),
        ("statuary_axis_public_floor_medallion", "Rotunda to National Statuary Hall", (18.0, -18.0), 0.68),
        ("old_senate_axis_public_floor_medallion", "Rotunda to Old Senate Chamber", (18.0, 18.0), 0.68),
        ("house_gallery_public_floor_medallion", "House gallery public orientation", (0.0, -91.0), 0.72),
        ("senate_gallery_public_floor_medallion", "Senate gallery public orientation", (0.0, 89.0), 0.72),
    ]:
        floor_medallion(name, area, center, radius)

    for name, area, center, direction in [
        ("west_axis_route_arrow_01", "Rotunda / east-west public approach", (-58.0, 0.0), "east"),
        ("west_axis_route_arrow_02", "Rotunda / east-west public approach", (-42.0, 0.0), "east"),
        ("west_axis_route_arrow_03", "Rotunda / east-west public approach", (-26.0, 0.0), "east"),
        ("east_axis_route_arrow_01", "Rotunda / east-west public approach", (58.0, 0.0), "west"),
        ("east_axis_route_arrow_02", "Rotunda / east-west public approach", (42.0, 0.0), "west"),
        ("east_axis_route_arrow_03", "Rotunda / east-west public approach", (26.0, 0.0), "west"),
        ("house_axis_route_arrow_01", "Rotunda to House Chamber public orientation", (0.0, -18.0), "south"),
        ("house_axis_route_arrow_02", "Rotunda to House Chamber public orientation", (0.0, -31.0), "south"),
        ("house_axis_route_arrow_03", "Rotunda to House Chamber public orientation", (0.0, -44.0), "south"),
        ("senate_axis_route_arrow_01", "Rotunda to Senate Chamber public orientation", (0.0, 18.0), "north"),
        ("senate_axis_route_arrow_02", "Rotunda to Senate Chamber public orientation", (0.0, 31.0), "north"),
        ("senate_axis_route_arrow_03", "Rotunda to Senate Chamber public orientation", (0.0, 44.0), "north"),
        ("statuary_route_arrow_01", "Rotunda to National Statuary Hall", (12.5, -10.5), "southeast"),
        ("statuary_route_arrow_02", "Rotunda to National Statuary Hall", (20.5, -18.0), "southeast"),
        ("old_senate_route_arrow_01", "Rotunda to Old Senate Chamber", (12.5, 10.5), "northeast"),
        ("old_senate_route_arrow_02", "Rotunda to Old Senate Chamber", (20.5, 18.0), "northeast"),
        ("house_gallery_route_arrow_01", "House gallery public orientation", (0.0, -90.0), "south"),
        ("house_gallery_route_arrow_02", "House gallery public orientation", (0.0, -96.0), "south"),
        ("senate_gallery_route_arrow_01", "Senate gallery public orientation", (0.0, 88.0), "north"),
        ("senate_gallery_route_arrow_02", "Senate gallery public orientation", (0.0, 95.0), "north"),
    ]:
        route_arrow(name, area, center, direction)

    for name, area, center, direction in [
        ("west_axis_route_chevron_01", "Rotunda / east-west public approach", (-50.0, 0.0), "east"),
        ("west_axis_route_chevron_02", "Rotunda / east-west public approach", (-34.0, 0.0), "east"),
        ("east_axis_route_chevron_01", "Rotunda / east-west public approach", (50.0, 0.0), "west"),
        ("east_axis_route_chevron_02", "Rotunda / east-west public approach", (34.0, 0.0), "west"),
        ("house_axis_route_chevron_01", "Rotunda to House Chamber public orientation", (0.0, -24.0), "south"),
        ("house_axis_route_chevron_02", "Rotunda to House Chamber public orientation", (0.0, -38.0), "south"),
        ("senate_axis_route_chevron_01", "Rotunda to Senate Chamber public orientation", (0.0, 24.0), "north"),
        ("senate_axis_route_chevron_02", "Rotunda to Senate Chamber public orientation", (0.0, 38.0), "north"),
        ("statuary_route_chevron_01", "Rotunda to National Statuary Hall", (16.2, -14.0), "southeast"),
        ("statuary_route_chevron_02", "Rotunda to National Statuary Hall", (23.5, -21.5), "southeast"),
        ("old_senate_route_chevron_01", "Rotunda to Old Senate Chamber", (16.2, 14.0), "northeast"),
        ("old_senate_route_chevron_02", "Rotunda to Old Senate Chamber", (23.5, 21.5), "northeast"),
        ("house_gallery_route_chevron_01", "House gallery public orientation", (0.0, -91.8), "south"),
        ("house_gallery_route_chevron_02", "House gallery public orientation", (0.0, -97.0), "south"),
        ("senate_gallery_route_chevron_01", "Senate gallery public orientation", (0.0, 89.8), "north"),
        ("senate_gallery_route_chevron_02", "Senate gallery public orientation", (0.0, 96.0), "north"),
    ]:
        route_chevron(name, area, center, direction)

    for name, area, center, length, angle in [
        ("west_axis_south_low_guide_rail", "Rotunda / east-west public approach", (-42.0, -2.55), 22.0, 0.0),
        ("west_axis_north_low_guide_rail", "Rotunda / east-west public approach", (-42.0, 2.55), 22.0, 0.0),
        ("east_axis_south_low_guide_rail", "Rotunda / east-west public approach", (42.0, -2.55), 22.0, 0.0),
        ("east_axis_north_low_guide_rail", "Rotunda / east-west public approach", (42.0, 2.55), 22.0, 0.0),
        ("house_axis_west_low_guide_rail", "Rotunda to House Chamber public orientation", (-2.25, -34.0), 24.0, math.pi / 2.0),
        ("house_axis_east_low_guide_rail", "Rotunda to House Chamber public orientation", (2.25, -34.0), 24.0, math.pi / 2.0),
        ("senate_axis_west_low_guide_rail", "Rotunda to Senate Chamber public orientation", (-2.25, 34.0), 24.0, math.pi / 2.0),
        ("senate_axis_east_low_guide_rail", "Rotunda to Senate Chamber public orientation", (2.25, 34.0), 24.0, math.pi / 2.0),
        ("statuary_outer_low_guide_rail", "Rotunda to National Statuary Hall", (18.0, -16.2), 15.0, -0.70),
        ("statuary_inner_low_guide_rail", "Rotunda to National Statuary Hall", (20.2, -18.8), 11.5, -0.70),
        ("old_senate_outer_low_guide_rail", "Rotunda to Old Senate Chamber", (18.0, 16.2), 15.0, 0.70),
        ("old_senate_inner_low_guide_rail", "Rotunda to Old Senate Chamber", (20.2, 18.8), 11.5, 0.70),
        ("house_gallery_low_guide_rail", "House gallery public orientation", (0.0, -93.6), 20.0, 0.0),
        ("senate_gallery_low_guide_rail", "Senate gallery public orientation", (0.0, 92.6), 18.0, 0.0),
    ]:
        low_guide_rail(name, area, center, length, angle)

    for name, area, center, orientation in [
        ("west_axis_directory", "Rotunda / east-west public approach", (-48.0, -3.18), "east_west"),
        ("east_axis_directory", "Rotunda / east-west public approach", (48.0, 3.18), "east_west"),
        ("house_axis_directory", "Rotunda to House Chamber public orientation", (-2.88, -42.0), "north_south"),
        ("senate_axis_directory", "Rotunda to Senate Chamber public orientation", (2.88, 42.0), "north_south"),
        ("house_gallery_directory", "House gallery public orientation", (-16.0, -90.95), "east_west"),
        ("senate_gallery_directory", "Senate gallery public orientation", (16.0, 88.95), "east_west"),
    ]:
        wall_directory_board(name, area, center, orientation)

    for name, area, center, orientation in [
        ("west_axis_public_clock", "Rotunda / east-west public approach", (-28.0, 3.16), "east_west"),
        ("east_axis_public_clock", "Rotunda / east-west public approach", (28.0, -3.16), "east_west"),
        ("rotunda_house_axis_public_clock", "Rotunda to House Chamber public orientation", (2.88, -28.0), "north_south"),
        ("rotunda_senate_axis_public_clock", "Rotunda to Senate Chamber public orientation", (-2.88, 28.0), "north_south"),
        ("statuary_public_clock", "Rotunda to National Statuary Hall", (22.4, -19.8), "north_south"),
        ("old_senate_public_clock", "Rotunda to Old Senate Chamber", (22.4, 19.8), "north_south"),
        ("house_gallery_public_clock", "House gallery public orientation", (22.0, -90.95), "east_west"),
        ("senate_gallery_public_clock", "Senate gallery public orientation", (-22.0, 88.95), "east_west"),
    ]:
        wall_clock(name, area, center, orientation)

    for index, (area, center, orientation) in enumerate([
        ("Rotunda / east-west public approach", (-54.0, -3.18), "east_west"),
        ("Rotunda / east-west public approach", (-18.0, 3.18), "east_west"),
        ("Rotunda / east-west public approach", (18.0, -3.18), "east_west"),
        ("Rotunda / east-west public approach", (54.0, 3.18), "east_west"),
        ("Rotunda to House Chamber public orientation", (-2.88, -36.0), "north_south"),
        ("Rotunda to House Chamber public orientation", (2.88, -20.0), "north_south"),
        ("Rotunda to Senate Chamber public orientation", (-2.88, 20.0), "north_south"),
        ("Rotunda to Senate Chamber public orientation", (2.88, 36.0), "north_south"),
        ("Rotunda to National Statuary Hall", (20.2, -17.1), "north_south"),
        ("Rotunda to Old Senate Chamber", (20.2, 17.1), "north_south"),
        ("House gallery public orientation", (-24.0, -90.95), "east_west"),
        ("Senate gallery public orientation", (24.0, 88.95), "east_west"),
    ], start=1):
        public_safety_cabinet(f"public_corridor_safety_cabinet_{index:02d}", area, center, orientation)

    for index, (area, center, orientation) in enumerate([
        ("Rotunda / east-west public approach", (-60.0, 3.16), "east_west"),
        ("Rotunda / east-west public approach", (-44.0, -3.16), "east_west"),
        ("Rotunda / east-west public approach", (-12.0, 3.16), "east_west"),
        ("Rotunda / east-west public approach", (12.0, -3.16), "east_west"),
        ("Rotunda / east-west public approach", (44.0, 3.16), "east_west"),
        ("Rotunda / east-west public approach", (60.0, -3.16), "east_west"),
        ("Rotunda to House Chamber public orientation", (-2.88, -46.0), "north_south"),
        ("Rotunda to House Chamber public orientation", (2.88, -32.0), "north_south"),
        ("Rotunda to House Chamber public orientation", (-2.88, -18.0), "north_south"),
        ("Rotunda to Senate Chamber public orientation", (2.88, 18.0), "north_south"),
        ("Rotunda to Senate Chamber public orientation", (-2.88, 32.0), "north_south"),
        ("Rotunda to Senate Chamber public orientation", (2.88, 46.0), "north_south"),
        ("Rotunda to National Statuary Hall", (24.4, -22.0), "north_south"),
        ("Rotunda to Old Senate Chamber", (24.4, 22.0), "north_south"),
        ("House gallery public orientation", (8.0, -90.95), "east_west"),
        ("Senate gallery public orientation", (-8.0, 88.95), "east_west"),
    ], start=1):
        emergency_light_block(f"public_corridor_emergency_light_{index:02d}", area, center, orientation)

    service_plate_specs: list[tuple[str, str, tuple[float, float], str]] = []
    for x in [-58.0, -38.0, -18.0, 18.0, 38.0, 58.0]:
        service_plate_specs.append(("east_west_axis_south", "Rotunda / east-west public approach", (x, -3.20), "east_west"))
        service_plate_specs.append(("east_west_axis_north", "Rotunda / east-west public approach", (x, 3.20), "east_west"))
    for y in [-48.0, -40.0, -30.0, -22.0]:
        service_plate_specs.append(("house_axis_west", "Rotunda to House Chamber public orientation", (-2.92, y), "north_south"))
        service_plate_specs.append(("house_axis_east", "Rotunda to House Chamber public orientation", (2.92, y), "north_south"))
    for y in [22.0, 30.0, 40.0, 48.0]:
        service_plate_specs.append(("senate_axis_west", "Rotunda to Senate Chamber public orientation", (-2.92, y), "north_south"))
        service_plate_specs.append(("senate_axis_east", "Rotunda to Senate Chamber public orientation", (2.92, y), "north_south"))
    for index, (prefix, area, center, orientation) in enumerate(service_plate_specs, start=1):
        wall_service_plates(f"{prefix}_service_plate_pair_{index:02d}", area, center, orientation)

    add_label(labels, "Public circulation thresholds, portals, orientation signs, and small wall fixtures - schematic", -17.0, 0.0, 7.3, "public_circulation_detail")
    add_label(labels, "Public corridor pilasters, sconces, floor medallions, route arrows, low guide rails, clocks, directories, and utility plates - schematic", 17.0, 0.0, 7.3, "public_circulation_detail")


def add_public_signage_detail_record(
    records: list[dict[str, Any]],
    name: str,
    kind: str,
    area: str,
    center: tuple[float, float, float],
    size: tuple[float, float] | None = None,
    message: str | None = None,
) -> None:
    record: dict[str, Any] = {
        "name": name,
        "kind": kind,
        "area": area,
        "center_m": [round(center[0], 3), round(center[1], 3), round(center[2], 3)],
        "public_accuracy": "schematic_public_wayfinding_signage_visual_detail",
        "assignment": (
            "Public visual wayfinding/signage detail only; not a restricted route, "
            "security feature, staff location, office assignment, or operational access map."
        ),
    }
    if size is not None:
        record["size_m"] = [round(size[0], 3), round(size[1], 3)]
    if message is not None:
        record["message"] = message
    records.append(record)


def add_public_interior_signage_details(
    obj: ObjWriter,
    labels: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> None:
    sign_z = 5.34
    label_z = 6.18

    def sign_size(width: float, thickness: float, orientation: str) -> tuple[float, float]:
        if orientation == "north_south":
            return (thickness, width)
        return (width, thickness)

    def sign_offset_center(
        center: tuple[float, float],
        longitudinal_offset: float,
        lateral_offset: float,
        orientation: str,
    ) -> tuple[float, float]:
        if orientation == "north_south":
            return (center[0] + lateral_offset, center[1] + longitudinal_offset)
        return (center[0] + longitudinal_offset, center[1] + lateral_offset)

    def add_sign_typography_strokes(
        name: str,
        area: str,
        center: tuple[float, float],
        width: float,
        orientation: str,
        z: float,
    ) -> None:
        stroke_specs = [
            (-0.30, -0.014, 0.18),
            (-0.11, 0.014, 0.13),
            (0.08, -0.014, 0.22),
            (0.29, 0.014, 0.12),
        ]
        for index, (offset_factor, lateral_offset, length_factor) in enumerate(stroke_specs, start=1):
            stroke_center = sign_offset_center(center, width * offset_factor, lateral_offset, orientation)
            stroke_size = sign_size(width * length_factor, 0.022, orientation)
            stroke_name = f"{name}_typography_stroke_{index:02d}"
            obj.add_box(stroke_center, stroke_size, 0.032, z, stroke_name, "LaneMarkingWhite")
            add_public_signage_detail_record(
                records,
                stroke_name,
                "sign_typography_stroke",
                area,
                (stroke_center[0], stroke_center[1], z + 0.016),
                stroke_size,
            )

    def wall_sign(
        name: str,
        kind: str,
        area: str,
        center: tuple[float, float],
        width: float,
        orientation: str,
        message: str,
        material: str = "MarkerBlue",
    ) -> None:
        size = sign_size(width, 0.10, orientation)
        obj.add_box(center, size, 0.42, sign_z, f"{name}_panel", material)
        obj.add_box(center, sign_size(width * 0.88, 0.035, orientation), 0.045, sign_z + 0.32, f"{name}_letter_bar_primary", "LaneMarkingWhite")
        obj.add_box(center, sign_size(width * 0.52, 0.030, orientation), 0.045, sign_z + 0.17, f"{name}_letter_bar_secondary", "LaneMarkingWhite")
        add_sign_typography_strokes(name, area, center, width, orientation, sign_z + 0.055)
        add_public_signage_detail_record(records, name, kind, area, (center[0], center[1], sign_z + 0.21), size, message)
        add_label(labels, message, center[0], center[1], label_z, "signage_detail")

    def standing_sign(
        name: str,
        kind: str,
        area: str,
        center: tuple[float, float],
        width: float,
        orientation: str,
        message: str,
        material: str = "StreetSignGreen",
    ) -> None:
        x, y = center
        size = sign_size(width, 0.12, orientation)
        obj.add_cylinder((x, y), 0.052, 4.50, 1.36, f"{name}_post", "BrassRail", segments=8)
        obj.add_cylinder((x, y), 0.20, 4.43, 0.08, f"{name}_base", "DoorMetal", segments=12)
        obj.add_box(center, size, 0.48, 5.58, f"{name}_blade", material)
        obj.add_box(center, sign_size(width * 0.82, 0.035, orientation), 0.050, 5.93, f"{name}_arrow_bar", "LaneMarkingWhite")
        obj.add_box(center, sign_size(width * 0.46, 0.030, orientation), 0.050, 5.75, f"{name}_caption_bar", "LaneMarkingWhite")
        add_sign_typography_strokes(name, area, center, width, orientation, 5.62)
        add_public_signage_detail_record(records, name, kind, area, (x, y, 5.82), size, message)
        add_label(labels, message, x, y, 6.55, "signage_detail")

    def map_kiosk(name: str, area: str, center: tuple[float, float], message: str) -> None:
        x, y = center
        obj.add_cylinder((x, y), 0.32, 4.45, 0.10, f"{name}_round_base", "DoorMetal", segments=18)
        obj.add_box((x, y), (0.72, 0.22), 1.34, 4.55, f"{name}_support", "BrassRail")
        obj.add_box((x, y), (1.55, 0.22), 1.12, 5.18, f"{name}_map_panel", "MarkerBlue")
        obj.add_box((x, y - 0.03), (1.26, 0.055), 0.62, 5.42, f"{name}_map_graphic_field", "LaneMarkingWhite")
        obj.add_box((x, y - 0.07), (0.92, 0.065), 0.08, 5.98, f"{name}_header_bar", "ArtFrameGold")
        for route_index, (offset_y, length) in enumerate([(-0.075, 0.96), (0.0, 0.70), (0.075, 1.10)], start=1):
            route_center = (x, y + offset_y)
            route_size = (length, 0.020)
            route_name = f"{name}_route_line_{route_index:02d}"
            obj.add_box(route_center, route_size, 0.030, 5.68 + route_index * 0.035, route_name, "StreetSignGreen")
            add_public_signage_detail_record(
                records,
                route_name,
                "map_kiosk_route_line",
                area,
                (route_center[0], route_center[1], 5.695 + route_index * 0.035),
                route_size,
                message,
            )
        add_public_signage_detail_record(records, name, "public_map_kiosk", area, (x, y, 5.74), (1.55, 0.22), message)
        add_label(labels, message, x, y, 6.65, "signage_detail")

    for name, area, center, width, orientation, message in [
        ("room_id_rotunda_west", "Rotunda", (-13.2, -0.7), 1.85, "east_west", "Rotunda room identification"),
        ("room_id_rotunda_east", "Rotunda", (13.2, 0.7), 1.85, "east_west", "Rotunda room identification"),
        ("room_id_statuary_hall", "National Statuary Hall", (16.8, -27.2), 2.05, "east_west", "National Statuary Hall identification"),
        ("room_id_old_senate", "Old Senate Chamber", (16.8, 27.2), 1.95, "east_west", "Old Senate Chamber identification"),
        ("room_id_crypt_marker", "Crypt below Rotunda marker", (-9.5, -23.6), 1.92, "east_west", "Crypt marker identification"),
        ("room_id_house_chamber", "House Chamber", (-9.8, -52.8), 2.18, "east_west", "House Chamber identification"),
        ("room_id_senate_chamber", "Senate Chamber", (9.8, 52.8), 2.12, "east_west", "Senate Chamber identification"),
        ("room_id_house_gallery", "House galleries", (-16.5, -91.8), 2.22, "east_west", "House public gallery identification"),
        ("room_id_senate_gallery", "Senate galleries", (16.5, 89.8), 2.16, "east_west", "Senate public gallery identification"),
    ]:
        wall_sign(name, "public_room_identification_sign", area, center, width, orientation, message)

    for name, area, center, width, orientation, message in [
        ("dir_west_rotunda_axis", "West terrace public orientation marker", (-45.0, -3.8), 2.20, "east_west", "Public wayfinding toward Rotunda"),
        ("dir_east_rotunda_axis", "East public approach / visitor circulation", (45.0, 3.8), 2.20, "east_west", "Public wayfinding toward Rotunda"),
        ("dir_rotunda_house", "Rotunda to House Chamber public orientation", (-4.8, -15.6), 2.02, "east_west", "Public wayfinding toward House Chamber"),
        ("dir_rotunda_senate", "Rotunda to Senate Chamber public orientation", (4.8, 15.6), 2.02, "east_west", "Public wayfinding toward Senate Chamber"),
        ("dir_rotunda_statuary", "Rotunda to National Statuary Hall", (10.8, -11.0), 1.88, "east_west", "Public wayfinding toward Statuary Hall"),
        ("dir_rotunda_old_senate", "Rotunda to Old Senate Chamber", (10.8, 11.0), 1.88, "east_west", "Public wayfinding toward Old Senate Chamber"),
        ("dir_house_gallery_left", "House gallery public orientation", (-20.0, -88.4), 1.92, "east_west", "Public wayfinding toward House Gallery"),
        ("dir_house_gallery_right", "House gallery public orientation", (20.0, -88.4), 1.92, "east_west", "Public wayfinding toward House Gallery"),
        ("dir_senate_gallery_left", "Senate gallery public orientation", (-17.0, 86.6), 1.88, "east_west", "Public wayfinding toward Senate Gallery"),
        ("dir_senate_gallery_right", "Senate gallery public orientation", (17.0, 86.6), 1.88, "east_west", "Public wayfinding toward Senate Gallery"),
        ("dir_house_support_west", "House leadership/support offices - schematic zone", (-42.0, -36.0), 1.78, "north_south", "Generic House support zone wayfinding"),
        ("dir_house_support_east", "House committee/support rooms - schematic zone", (42.0, -36.0), 1.78, "north_south", "Generic House support zone wayfinding"),
        ("dir_senate_support_west", "Senate leadership/support offices - schematic zone", (-42.0, 36.0), 1.78, "north_south", "Generic Senate support zone wayfinding"),
        ("dir_senate_support_east", "Senate committee/support rooms - schematic zone", (42.0, 36.0), 1.78, "north_south", "Generic Senate support zone wayfinding"),
        ("dir_public_return_west", "Public return orientation", (-32.0, 2.8), 1.86, "east_west", "Public wayfinding toward west orientation point"),
        ("dir_public_return_east", "Public return orientation", (32.0, -2.8), 1.86, "east_west", "Public wayfinding toward east orientation point"),
    ]:
        standing_sign(name, "public_directional_sign", area, center, width, orientation, message)

    for name, area, center, width, orientation, message in [
        ("gallery_sign_house_front", "House galleries", (0.0, -94.0), 2.20, "east_west", "House gallery public viewing area"),
        ("gallery_sign_house_rear", "House galleries", (0.0, -103.1), 2.00, "east_west", "House gallery rear public viewing area"),
        ("gallery_sign_house_west", "House galleries", (-29.5, -99.0), 1.72, "north_south", "House gallery side section"),
        ("gallery_sign_house_east", "House galleries", (29.5, -99.0), 1.72, "north_south", "House gallery side section"),
        ("gallery_sign_senate_front", "Senate galleries", (0.0, 93.0), 2.10, "east_west", "Senate gallery public viewing area"),
        ("gallery_sign_senate_rear", "Senate galleries", (0.0, 101.0), 1.92, "east_west", "Senate gallery rear public viewing area"),
        ("gallery_sign_senate_west", "Senate galleries", (-23.0, 97.4), 1.60, "north_south", "Senate gallery side section"),
        ("gallery_sign_senate_east", "Senate galleries", (23.0, 97.4), 1.60, "north_south", "Senate gallery side section"),
    ]:
        wall_sign(name, "visitor_gallery_sign", area, center, width, orientation, message, material="PublicGallery")

    for name, area, center, width, orientation, message in [
        ("role_house_speaker_rostrum", "House Chamber", (0.0, -47.35), 2.00, "east_west", "House rostrum role marker"),
        ("role_house_clerk_press", "House Chamber", (0.0, -52.2), 2.18, "east_west", "House clerks and press role marker"),
        ("role_house_members_left", "House Chamber", (-14.2, -73.0), 1.88, "east_west", "Generic House member seating block"),
        ("role_house_members_right", "House Chamber", (14.2, -73.0), 1.88, "east_west", "Generic House member seating block"),
        ("role_house_gallery", "House Chamber", (0.0, -96.0), 2.08, "east_west", "House public gallery role marker"),
        ("role_senate_presiding", "Senate Chamber", (0.0, 84.5), 1.92, "east_west", "Senate presiding officer role marker"),
        ("role_senate_clerk_press", "Senate Chamber", (0.0, 78.1), 2.00, "east_west", "Senate clerks and press role marker"),
        ("role_senate_desks_left", "Senate Chamber", (-10.0, 72.4), 1.82, "east_west", "Generic Senate desk block"),
        ("role_senate_desks_right", "Senate Chamber", (10.0, 72.4), 1.82, "east_west", "Generic Senate desk block"),
        ("role_senate_gallery", "Senate Chamber", (0.0, 96.0), 2.00, "east_west", "Senate public gallery role marker"),
    ]:
        wall_sign(name, "chamber_role_sign", area, center, width, orientation, message, material="InteriorTrim")

    for name, area, center, width, orientation, message in [
        ("office_zone_house_west_entry", "House leadership/support offices - schematic zone", (-62.8, -55.0), 1.98, "north_south", "Generic House support offices"),
        ("office_zone_house_east_entry", "House committee/support rooms - schematic zone", (62.8, -55.0), 1.98, "north_south", "Generic House committee/support rooms"),
        ("office_zone_senate_west_entry", "Senate leadership/support offices - schematic zone", (-61.8, 55.0), 1.98, "north_south", "Generic Senate support offices"),
        ("office_zone_senate_east_entry", "Senate committee/support rooms - schematic zone", (61.8, 55.0), 1.98, "north_south", "Generic Senate committee/support rooms"),
        ("office_zone_house_inner_pair", "House support circulation", (37.0, -64.5), 1.74, "north_south", "Generic House support circulation"),
        ("office_zone_senate_inner_pair", "Senate support circulation", (-36.5, 64.5), 1.74, "north_south", "Generic Senate support circulation"),
    ]:
        wall_sign(name, "generic_office_zone_sign", area, center, width, orientation, message, material="MarkerBlue")

    for name, area, center, message in [
        ("kiosk_west_public_orientation", "West terrace public orientation marker", (-57.0, -8.0), "Public orientation map kiosk - west"),
        ("kiosk_east_public_orientation", "East public approach / visitor circulation", (57.0, 8.0), "Public orientation map kiosk - east"),
        ("kiosk_rotunda_public_orientation", "Rotunda", (-6.5, 6.5), "Public orientation map kiosk - Rotunda"),
        ("kiosk_gallery_public_orientation", "House and Senate gallery orientation", (6.5, -6.5), "Public orientation map kiosk - galleries"),
    ]:
        map_kiosk(name, area, center, message)

    add_label(labels, "Public room signs, gallery signs, and map kiosks - schematic", -23.5, 7.0, 7.4, "signage_detail")


def add_public_door_detail_record(
    records: list[dict[str, Any]],
    name: str,
    kind: str,
    area: str,
    center: tuple[float, float, float],
    size: tuple[float, float] | None = None,
) -> None:
    record: dict[str, Any] = {
        "name": name,
        "kind": kind,
        "area": area,
        "center_m": [round(center[0], 3), round(center[1], 3), round(center[2], 3)],
        "public_accuracy": "schematic_public_interior_door_hardware_detail",
        "assignment": (
            "Public visual doorway/hardware detail only; not a restricted access point, "
            "security feature, staff location, or operational access map."
        ),
    }
    if size is not None:
        record["size_m"] = [round(size[0], 3), round(size[1], 3)]
    records.append(record)


def add_public_interior_door_details(
    obj: ObjWriter,
    labels: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> None:
    z = 4.48

    def plane_size(width: float, depth: float, orientation: str) -> tuple[float, float]:
        if orientation == "east_west":
            return (depth, width)
        return (width, depth)

    def component_center(
        center: tuple[float, float],
        along_offset: float,
        normal_offset: float,
        orientation: str,
    ) -> tuple[float, float]:
        x, y = center
        if orientation == "east_west":
            return (x + normal_offset, y + along_offset)
        return (x + along_offset, y + normal_offset)

    def add_component(
        name: str,
        kind: str,
        area: str,
        center: tuple[float, float],
        along_offset: float,
        normal_offset: float,
        width: float,
        depth: float,
        height: float,
        bottom_z: float,
        orientation: str,
        material: str,
    ) -> None:
        cx, cy = component_center(center, along_offset, normal_offset, orientation)
        size = plane_size(width, depth, orientation)
        obj.add_box((cx, cy), size, height, bottom_z, name, material)
        add_public_door_detail_record(records, name, kind, area, (cx, cy, bottom_z + height / 2.0), size)

    def add_floor_round_detail(
        name: str,
        kind: str,
        area: str,
        center: tuple[float, float],
        along_offset: float,
        normal_offset: float,
        radius: float,
        height: float,
        bottom_z: float,
        orientation: str,
        material: str,
    ) -> None:
        cx, cy = component_center(center, along_offset, normal_offset, orientation)
        obj.add_cylinder((cx, cy), radius, bottom_z, height, name, material, segments=12)
        add_public_door_detail_record(
            records,
            name,
            kind,
            area,
            (cx, cy, bottom_z + height / 2.0),
            (radius * 2.0, radius * 2.0),
        )

    def add_doorway(
        name: str,
        area: str,
        center: tuple[float, float],
        width: float,
        orientation: str,
        label: str,
    ) -> None:
        leaf_gap = 0.08
        leaf_width = max(0.72, (width - leaf_gap) / 2.0)
        left_offset = -(leaf_width / 2.0 + leaf_gap / 2.0)
        right_offset = leaf_width / 2.0 + leaf_gap / 2.0
        panel_height = 2.18
        side_lite_width = min(0.54, width * 0.10)

        for suffix, offset in [("left", left_offset), ("right", right_offset)]:
            add_component(f"{name}_{suffix}_door_leaf_panel", "public_double_door_panel", area, center, offset, 0.0, leaf_width, 0.12, panel_height, z, orientation, "DoorGlass")
            add_component(f"{name}_{suffix}_brass_pull_bar", "door_pull_bar", area, center, offset, -0.075, 0.10, 0.07, 1.02, z + 0.58, orientation, "BrassRail")
            add_component(f"{name}_{suffix}_kick_plate", "door_kick_plate", area, center, offset, -0.08, leaf_width * 0.82, 0.055, 0.30, z + 0.10, orientation, "DoorMetal")
            add_component(f"{name}_{suffix}_push_plate", "door_push_plate", area, center, offset, -0.086, 0.28, 0.040, 0.50, z + 0.82, orientation, "DoorMetal")
            add_component(f"{name}_{suffix}_closer_body", "door_closer_body", area, center, offset * 0.72, -0.078, min(0.56, leaf_width * 0.56), 0.060, 0.12, z + 2.02, orientation, "DoorMetal")
            add_component(f"{name}_{suffix}_closer_arm", "door_closer_arm", area, center, offset * 0.46, -0.092, min(0.48, leaf_width * 0.50), 0.038, 0.045, z + 1.94, orientation, "BrassRail")
            add_floor_round_detail(f"{name}_{suffix}_floor_door_stop", "floor_door_stop", area, center, offset, -0.44, 0.065, 0.075, z + 0.02, orientation, "DoorMetal")
            for hinge_index, hinge_z in enumerate([z + 0.30, z + 1.02, z + 1.78], start=1):
                hinge_offset = offset - leaf_width * 0.47 if suffix == "left" else offset + leaf_width * 0.47
                add_component(
                    f"{name}_{suffix}_hinge_plate_{hinge_index}",
                    "hinge_plate",
                    area,
                    center,
                    hinge_offset,
                    0.075,
                    0.14,
                    0.055,
                    0.22,
                    hinge_z,
                    orientation,
                    "DoorMetal",
                )

        add_component(f"{name}_transom_glass_panel", "transom_panel", area, center, 0.0, 0.0, width * 0.86, 0.12, 0.48, z + panel_height + 0.10, orientation, "DoorGlass")
        for mullion_index, mullion_offset in enumerate([-width * 0.24, width * 0.24], start=1):
            add_component(
                f"{name}_transom_mullion_{mullion_index}",
                "transom_mullion",
                area,
                center,
                mullion_offset,
                -0.004,
                0.052,
                0.135,
                0.52,
                z + panel_height + 0.08,
                orientation,
                "InteriorTrim",
            )
        add_component(f"{name}_header_trim", "door_header_trim", area, center, 0.0, 0.0, width + 0.50, 0.18, 0.18, z + panel_height + 0.62, orientation, "InteriorTrim")
        add_component(f"{name}_left_side_lite", "side_lite_panel", area, center, -width / 2.0 + side_lite_width / 2.0, 0.0, side_lite_width, 0.10, 1.62, z + 0.24, orientation, "DoorGlass")
        add_component(f"{name}_right_side_lite", "side_lite_panel", area, center, width / 2.0 - side_lite_width / 2.0, 0.0, side_lite_width, 0.10, 1.62, z + 0.24, orientation, "DoorGlass")
        for suffix, offset in [
            ("left", -width / 2.0 + side_lite_width / 2.0),
            ("right", width / 2.0 - side_lite_width / 2.0),
        ]:
            add_component(
                f"{name}_{suffix}_side_lite_mullion",
                "side_lite_mullion",
                area,
                center,
                offset,
                -0.004,
                0.042,
                0.122,
                1.72,
                z + 0.18,
                orientation,
                "InteriorTrim",
            )
        for screw_index, screw_offset in enumerate([-width * 0.34, -width * 0.12, width * 0.12, width * 0.34], start=1):
            add_floor_round_detail(
                f"{name}_threshold_screw_head_{screw_index}",
                "threshold_screw_head",
                area,
                center,
                screw_offset,
                -0.01,
                0.038,
                0.014,
                z + 0.002,
                orientation,
                "DoorMetal",
            )
        add_label(labels, label, center[0], center[1], z + 3.18, "door_detail")

    door_specs = [
        ("west_public_approach_door_detail", "West terrace public orientation marker", (-55.0, 0.0), 7.8, "east_west", "West public approach door hardware - schematic"),
        ("east_public_approach_door_detail", "East public approach", (55.0, 0.0), 7.8, "east_west", "East public approach door hardware - schematic"),
        ("rotunda_statuary_hall_door_detail", "Rotunda / National Statuary Hall", (16.2, -15.8), 4.8, "north_south", "Rotunda to Statuary Hall door hardware - schematic"),
        ("rotunda_old_senate_door_detail", "Rotunda / Old Senate Chamber", (16.2, 15.8), 4.6, "north_south", "Rotunda to Old Senate door hardware - schematic"),
        ("rotunda_house_door_detail", "Rotunda / House Chamber orientation", (0.0, -51.0), 6.2, "north_south", "House Chamber public doorway hardware - schematic"),
        ("rotunda_senate_door_detail", "Rotunda / Senate Chamber orientation", (0.0, 51.0), 6.0, "north_south", "Senate Chamber public doorway hardware - schematic"),
        ("house_gallery_door_detail", "House Chamber / public gallery", (0.0, -91.0), 8.0, "north_south", "House gallery doorway hardware - schematic"),
        ("senate_gallery_door_detail", "Senate Chamber / public gallery", (0.0, 89.0), 7.0, "north_south", "Senate gallery doorway hardware - schematic"),
        ("house_west_support_door_detail", "House leadership/support offices - schematic zone", (-62.8, -55.0), 3.5, "east_west", "Generic House support doorway hardware - schematic"),
        ("house_east_support_door_detail", "House committee/support rooms - schematic zone", (62.8, -55.0), 3.5, "east_west", "Generic House committee support doorway hardware - schematic"),
        ("senate_west_support_door_detail", "Senate leadership/support offices - schematic zone", (-61.8, 55.0), 3.5, "east_west", "Generic Senate support doorway hardware - schematic"),
        ("senate_east_support_door_detail", "Senate committee/support rooms - schematic zone", (61.8, 55.0), 3.5, "east_west", "Generic Senate committee support doorway hardware - schematic"),
    ]
    for args in door_specs:
        add_doorway(*args)

    add_label(labels, "Public doorway panels, pulls, hinges, closers, stops, mullions, kick plates, and transoms - schematic", 22.5, -7.5, 7.65, "door_detail")


def add_public_furnishing_detail_record(
    records: list[dict[str, Any]],
    name: str,
    kind: str,
    area: str,
    center: tuple[float, float, float],
    size: tuple[float, float] | None = None,
) -> None:
    record: dict[str, Any] = {
        "name": name,
        "kind": kind,
        "area": area,
        "center_m": [round(center[0], 3), round(center[1], 3), round(center[2], 3)],
        "public_accuracy": "schematic_public_interior_furnishing_fixture_detail",
        "assignment": (
            "Public visual furnishing/fixture detail only; not a restricted route, "
            "queue plan, security feature, staff location, or operational access map."
        ),
    }
    if size is not None:
        record["size_m"] = [round(size[0], 3), round(size[1], 3)]
    records.append(record)


def add_public_interior_furnishing_details(
    obj: ObjWriter,
    labels: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> None:
    floor_z = 4.50

    def oriented_size(length: float, depth: float, orientation: str) -> tuple[float, float]:
        if orientation == "north_south":
            return (depth, length)
        return (length, depth)

    def oriented_center(
        center: tuple[float, float],
        length_offset: float,
        depth_offset: float,
        orientation: str,
    ) -> tuple[float, float]:
        x, y = center
        if orientation == "north_south":
            return (x + depth_offset, y + length_offset)
        return (x + length_offset, y + depth_offset)

    def add_bench(name: str, area: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        seat_size = oriented_size(2.25, 0.52, orientation)
        back_size = oriented_size(2.25, 0.12, orientation)
        obj.add_box((x, y), seat_size, 0.16, floor_z + 0.32, f"{name}_seat_slab", "DeskWood")
        if orientation == "north_south":
            back_center = (x - 0.27, y)
        else:
            back_center = (x, y + 0.27)
        obj.add_box(back_center, back_size, 0.72, floor_z + 0.38, f"{name}_back_rail", "ChairLeather")
        for index, (dx, dy) in enumerate([(-0.82, -0.18), (0.82, -0.18), (-0.82, 0.18), (0.82, 0.18)], start=1):
            if orientation == "north_south":
                leg_center = (x + dy, y + dx)
            else:
                leg_center = (x + dx, y + dy)
            obj.add_box(leg_center, (0.10, 0.10), 0.34, floor_z, f"{name}_leg_{index}", "BrassRail")
        for slat_index, depth_offset in enumerate([-0.17, 0.0, 0.17], start=1):
            slat_center = oriented_center(center, 0.0, depth_offset, orientation)
            slat_size = oriented_size(2.06, 0.075, orientation)
            slat_name = f"{name}_seat_slat_{slat_index:02d}"
            obj.add_box(slat_center, slat_size, 0.040, floor_z + 0.50, slat_name, "BenchWood")
            add_public_furnishing_detail_record(records, slat_name, "bench_seat_slat", area, (slat_center[0], slat_center[1], floor_z + 0.52), slat_size)
        for arm_index, length_offset in enumerate([-1.02, 1.02], start=1):
            arm_center = oriented_center(center, length_offset, 0.0, orientation)
            arm_size = oriented_size(0.10, 0.64, orientation)
            arm_name = f"{name}_arm_rest_{arm_index:02d}"
            obj.add_box(arm_center, arm_size, 0.14, floor_z + 0.54, arm_name, "ChairLeather")
            add_public_furnishing_detail_record(records, arm_name, "bench_arm_rest", area, (arm_center[0], arm_center[1], floor_z + 0.61), arm_size)
        add_public_furnishing_detail_record(records, name, "public_bench", area, (x, y, floor_z + 0.42), seat_size)

    def add_display_case(name: str, area: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        base_size = oriented_size(1.55, 0.70, orientation)
        glass_size = oriented_size(1.35, 0.52, orientation)
        obj.add_box((x, y), base_size, 0.42, floor_z, f"{name}_stone_base", "InteriorTrim")
        obj.add_box((x, y), glass_size, 0.74, floor_z + 0.42, f"{name}_glass_case", "DoorGlass")
        obj.add_box((x, y), oriented_size(1.10, 0.34, orientation), 0.12, floor_z + 0.54, f"{name}_object_plinth", "StatueMarble")
        trim_specs = [
            ("front", 0.0, -0.285, 1.40, 0.045),
            ("back", 0.0, 0.285, 1.40, 0.045),
            ("left", -0.70, 0.0, 0.045, 0.58),
            ("right", 0.70, 0.0, 0.045, 0.58),
        ]
        for trim_index, (side, length_offset, depth_offset, length, depth) in enumerate(trim_specs, start=1):
            trim_center = oriented_center(center, length_offset, depth_offset, orientation)
            trim_size = oriented_size(length, depth, orientation)
            trim_name = f"{name}_glass_edge_trim_{side}"
            obj.add_box(trim_center, trim_size, 0.040, floor_z + 1.14, trim_name, "BrassRail")
            add_public_furnishing_detail_record(records, trim_name, "display_case_edge_trim", area, (trim_center[0], trim_center[1], floor_z + 1.16), trim_size)
        silhouette_name = f"{name}_object_silhouette"
        obj.add_cylinder((x, y), 0.13, floor_z + 0.66, 0.30, silhouette_name, "StatueBronze", segments=12)
        add_public_furnishing_detail_record(records, silhouette_name, "display_case_object_silhouette", area, (x, y, floor_z + 0.81), (0.26, 0.26))
        light_strip_size = oriented_size(1.22, 0.045, orientation)
        light_offsets = [-0.24, 0.24]
        for edge_index, edge_offset in enumerate(light_offsets, start=1):
            light_center = (x + edge_offset, y) if orientation == "north_south" else (x, y + edge_offset)
            obj.add_box(light_center, light_strip_size, 0.034, floor_z + 1.13, f"{name}_warm_light_strip_{edge_index}", "WarmLightGlass")
            add_public_furnishing_detail_record(
                records,
                f"{name}_warm_light_strip_{edge_index}",
                "display_case_light_strip",
                area,
                (light_center[0], light_center[1], floor_z + 1.147),
                light_strip_size,
            )
        plaque_size = oriented_size(0.62, 0.055, orientation)
        plaque_center = (x + 0.42, y) if orientation == "north_south" else (x, y - 0.42)
        obj.add_box(plaque_center, plaque_size, 0.070, floor_z + 0.48, f"{name}_small_label_plaque", "BrassRail")
        add_public_furnishing_detail_record(
            records,
            f"{name}_small_label_plaque",
            "display_case_label_plaque",
            area,
            (plaque_center[0], plaque_center[1], floor_z + 0.515),
            plaque_size,
        )
        add_public_furnishing_detail_record(records, name, "display_case", area, (x, y, floor_z + 0.78), base_size)

    def add_info_lectern(name: str, area: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        obj.add_box((x, y), (0.46, 0.38), 0.92, floor_z, f"{name}_pedestal", "DeskWood")
        panel_size = oriented_size(0.96, 0.08, orientation)
        obj.add_box((x, y), panel_size, 0.32, floor_z + 0.90, f"{name}_map_panel", "MarkerBlue")
        obj.add_box((x, y), oriented_size(0.78, 0.04, orientation), 0.05, floor_z + 1.20, f"{name}_header_strip", "LaneMarkingWhite")
        for line_index, (length_offset, length) in enumerate([(-0.24, 0.34), (0.0, 0.56), (0.24, 0.28)], start=1):
            line_center = oriented_center(center, length_offset, 0.0, orientation)
            line_size = oriented_size(length, 0.024, orientation)
            line_name = f"{name}_text_line_{line_index:02d}"
            obj.add_box(line_center, line_size, 0.030, floor_z + 1.08 + line_index * 0.025, line_name, "LaneMarkingWhite")
            add_public_furnishing_detail_record(records, line_name, "lectern_text_line", area, (line_center[0], line_center[1], floor_z + 1.095 + line_index * 0.025), line_size)
        add_public_furnishing_detail_record(records, name, "information_lectern", area, (x, y, floor_z + 0.70), panel_size)

    def add_receptacle(name: str, area: str, center: tuple[float, float], material: str) -> None:
        x, y = center
        obj.add_cylinder((x, y), 0.24, floor_z, 0.72, f"{name}_cylindrical_body", material, segments=14)
        obj.add_cylinder((x, y), 0.26, floor_z + 0.72, 0.08, f"{name}_rim_lid", "DoorMetal", segments=14)
        obj.add_box((x, y), (0.30, 0.045), 0.04, floor_z + 0.79, f"{name}_slot_marker", "LaneMarkingWhite")
        label_name = f"{name}_sorting_label"
        obj.add_box((x, y - 0.20), (0.22, 0.035), 0.16, floor_z + 0.38, label_name, "LaneMarkingWhite")
        add_public_furnishing_detail_record(records, label_name, "receptacle_sorting_label", area, (x, y - 0.20, floor_z + 0.46), (0.22, 0.035))
        add_public_furnishing_detail_record(records, name, "waste_receptacle", area, (x, y, floor_z + 0.40), (0.52, 0.52))

    def add_plant_urn(name: str, area: str, center: tuple[float, float]) -> None:
        x, y = center
        obj.add_cylinder((x, y), 0.36, floor_z, 0.45, f"{name}_stone_urn", "PlanterStone", segments=18)
        rim_name = f"{name}_raised_rim"
        obj.add_ring((x, y), 0.43, 0.28, floor_z + 0.43, 0.07, rim_name, "PlanterStone", segments=18)
        obj.add_cylinder((x, y), 0.30, floor_z + 0.43, 0.30, f"{name}_greenery_mass", "GroundGrass", segments=16)
        for leaf_index, (dx, dy, radius) in enumerate([(-0.12, 0.08, 0.16), (0.10, 0.12, 0.14), (0.06, -0.11, 0.15)], start=1):
            obj.add_cylinder((x + dx, y + dy), radius, floor_z + 0.62, 0.16, f"{name}_leaf_cluster_{leaf_index:02d}", "TreeCanopy", segments=10)
        add_public_furnishing_detail_record(records, rim_name, "plant_urn_rim", area, (x, y, floor_z + 0.465), (0.86, 0.86))
        add_public_furnishing_detail_record(records, f"{name}_leaf_clusters", "plant_leaf_cluster", area, (x, y, floor_z + 0.70), (0.72, 0.72))
        add_public_furnishing_detail_record(records, name, "plant_urn", area, (x, y, floor_z + 0.42), (0.72, 0.72))

    def add_queue_line(name: str, area: str, start: tuple[float, float], step: tuple[float, float], count: int) -> None:
        posts: list[tuple[float, float]] = []
        for index in range(count):
            x = start[0] + step[0] * index
            y = start[1] + step[1] * index
            posts.append((x, y))
            obj.add_cylinder((x, y), 0.055, floor_z, 0.86, f"{name}_post_{index+1:02d}", "BrassRail", segments=10)
            obj.add_cylinder((x, y), 0.14, floor_z, 0.06, f"{name}_post_{index+1:02d}_base", "DoorMetal", segments=12)
            add_public_furnishing_detail_record(records, f"{name}_post_{index+1:02d}", "public_queue_post", area, (x, y, floor_z + 0.43), (0.28, 0.28))
        for index, (a, b) in enumerate(zip(posts, posts[1:]), start=1):
            mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
            if abs(step[0]) >= abs(step[1]):
                size = (math.hypot(step[0], step[1]), 0.045)
            else:
                size = (0.045, math.hypot(step[0], step[1]))
            obj.add_box(mid, size, 0.05, floor_z + 0.66, f"{name}_rope_segment_{index:02d}", "BrassRail")
            add_public_furnishing_detail_record(records, f"{name}_rope_segment_{index:02d}", "queue_rope_segment", area, (mid[0], mid[1], floor_z + 0.685), size)

    for index, (center, orientation, area) in enumerate(
        [
            ((-8.6, 5.8), "east_west", "Rotunda"),
            ((8.6, 5.8), "east_west", "Rotunda"),
            ((-8.6, -5.8), "east_west", "Rotunda"),
            ((8.6, -5.8), "east_west", "Rotunda"),
            ((-11.8, 0.0), "north_south", "Rotunda"),
            ((11.8, 0.0), "north_south", "Rotunda"),
            ((20.0, -22.5), "east_west", "National Statuary Hall"),
            ((28.0, -22.5), "east_west", "National Statuary Hall"),
            ((36.0, -22.5), "east_west", "National Statuary Hall"),
            ((20.0, -37.5), "east_west", "National Statuary Hall"),
            ((28.0, -37.5), "east_west", "National Statuary Hall"),
            ((36.0, -37.5), "east_west", "National Statuary Hall"),
            ((20.5, 23.0), "east_west", "Old Senate Chamber"),
            ((35.5, 23.0), "east_west", "Old Senate Chamber"),
            ((20.5, 37.0), "east_west", "Old Senate Chamber"),
            ((35.5, 37.0), "east_west", "Old Senate Chamber"),
            ((-55.5, -20.0), "north_south", "Public circulation / schematic corridor"),
            ((55.5, 20.0), "north_south", "Public circulation / schematic corridor"),
            ((-24.0, -99.2), "east_west", "House galleries"),
            ((24.0, -99.2), "east_west", "House galleries"),
            ((-18.0, 97.5), "east_west", "Senate galleries"),
            ((18.0, 97.5), "east_west", "Senate galleries"),
            ((-52.8, -42.5), "north_south", "House leadership/support offices - schematic zone"),
            ((52.8, 42.5), "north_south", "Senate committee/support rooms - schematic zone"),
        ],
        start=1,
    ):
        add_bench(f"public_interior_bench_{index:02d}", area, center, orientation)

    for index, (center, orientation, area) in enumerate(
        [
            ((-6.0, 9.6), "east_west", "Rotunda"),
            ((6.0, 9.6), "east_west", "Rotunda"),
            ((-6.0, -9.6), "east_west", "Rotunda"),
            ((6.0, -9.6), "east_west", "Rotunda"),
            ((18.8, -28.0), "north_south", "National Statuary Hall"),
            ((24.5, -28.0), "north_south", "National Statuary Hall"),
            ((31.5, -32.0), "north_south", "National Statuary Hall"),
            ((37.2, -32.0), "north_south", "National Statuary Hall"),
            ((22.0, 28.0), "north_south", "Old Senate Chamber"),
            ((34.0, 32.0), "north_south", "Old Senate Chamber"),
            ((-47.5, -16.0), "north_south", "Public circulation / schematic corridor"),
            ((47.5, 16.0), "north_south", "Public circulation / schematic corridor"),
            ((-15.0, -94.2), "east_west", "House galleries"),
            ((15.0, -94.2), "east_west", "House galleries"),
            ((-13.0, 92.7), "east_west", "Senate galleries"),
            ((13.0, 92.7), "east_west", "Senate galleries"),
        ],
        start=1,
    ):
        add_display_case(f"public_interior_display_case_{index:02d}", area, center, orientation)

    for index, (center, orientation, area) in enumerate(
        [
            ((-50.5, 4.8), "north_south", "West terrace public orientation marker"),
            ((50.5, -4.8), "north_south", "East public approach / visitor circulation"),
            ((12.8, -12.0), "east_west", "Rotunda / National Statuary Hall"),
            ((12.8, 12.0), "east_west", "Rotunda / Old Senate Chamber"),
            ((-4.8, -48.2), "east_west", "Rotunda / House Chamber orientation"),
            ((4.8, 48.2), "east_west", "Rotunda / Senate Chamber orientation"),
            ((-10.5, -91.7), "east_west", "House Chamber / public gallery"),
            ((10.5, 89.7), "east_west", "Senate Chamber / public gallery"),
        ],
        start=1,
    ):
        add_display_case(f"public_transition_exhibit_case_{index:02d}", area, center, orientation)

    for index, (center, orientation, area) in enumerate(
        [
            ((-4.2, 4.2), "east_west", "Rotunda"),
            ((4.2, -4.2), "east_west", "Rotunda"),
            ((-52.5, 6.5), "north_south", "West terrace public orientation marker"),
            ((52.5, -6.5), "north_south", "East public approach / visitor circulation"),
            ((21.5, -20.8), "east_west", "National Statuary Hall"),
            ((21.5, 20.8), "east_west", "Old Senate Chamber"),
            ((-7.0, -87.0), "east_west", "House gallery public orientation"),
            ((7.0, 85.0), "east_west", "Senate gallery public orientation"),
            ((-45.0, -55.0), "north_south", "House leadership/support offices - schematic zone"),
            ((45.0, 55.0), "north_south", "Senate committee/support rooms - schematic zone"),
        ],
        start=1,
    ):
        add_info_lectern(f"public_information_lectern_{index:02d}", area, center, orientation)

    receptacle_specs = [
        ((-12.5, 7.0), "Rotunda", "DoorMetal"),
        ((12.5, -7.0), "Rotunda", "MarkerBlue"),
        ((-12.5, -7.0), "Rotunda", "DoorMetal"),
        ((12.5, 7.0), "Rotunda", "MarkerBlue"),
        ((17.0, -21.5), "National Statuary Hall", "DoorMetal"),
        ((39.0, -38.5), "National Statuary Hall", "MarkerBlue"),
        ((17.0, 21.5), "Old Senate Chamber", "DoorMetal"),
        ((39.0, 38.5), "Old Senate Chamber", "MarkerBlue"),
        ((-58.0, -4.5), "West terrace public orientation marker", "DoorMetal"),
        ((58.0, 4.5), "East public approach / visitor circulation", "MarkerBlue"),
        ((-31.0, -94.0), "House galleries", "DoorMetal"),
        ((31.0, -94.0), "House galleries", "MarkerBlue"),
        ((-24.0, 92.3), "Senate galleries", "DoorMetal"),
        ((24.0, 92.3), "Senate galleries", "MarkerBlue"),
        ((-45.0, -42.0), "House leadership/support offices - schematic zone", "DoorMetal"),
        ((45.0, 42.0), "Senate committee/support rooms - schematic zone", "MarkerBlue"),
    ]
    for index, (center, area, material) in enumerate(receptacle_specs, start=1):
        add_receptacle(f"public_receptacle_{index:02d}", area, center, material)

    plant_specs = [
        (-12.8, 0.0, "Rotunda"),
        (12.8, 0.0, "Rotunda"),
        (0.0, -12.8, "Rotunda"),
        (0.0, 12.8, "Rotunda"),
        (16.8, -39.0, "National Statuary Hall"),
        (39.2, -39.0, "National Statuary Hall"),
        (16.8, -21.0, "National Statuary Hall"),
        (39.2, -21.0, "National Statuary Hall"),
        (16.8, 21.0, "Old Senate Chamber"),
        (39.2, 21.0, "Old Senate Chamber"),
        (16.8, 39.0, "Old Senate Chamber"),
        (39.2, 39.0, "Old Senate Chamber"),
        (-56.0, -27.0, "West terrace public orientation marker"),
        (-56.0, 27.0, "West terrace public orientation marker"),
        (56.0, -27.0, "East public approach / visitor circulation"),
        (56.0, 27.0, "East public approach / visitor circulation"),
        (-30.0, -101.0, "House galleries"),
        (30.0, -101.0, "House galleries"),
        (-23.0, 99.8, "Senate galleries"),
        (23.0, 99.8, "Senate galleries"),
    ]
    for index, (x, y, area) in enumerate(plant_specs, start=1):
        add_plant_urn(f"public_plant_urn_{index:02d}", area, (x, y))

    for index, (area, start, step, count) in enumerate(
        [
            ("West terrace public orientation marker", (-58.0, -11.0), (1.4, 0.0), 6),
            ("East public approach / visitor circulation", (50.8, 11.0), (1.4, 0.0), 6),
            ("House gallery public orientation", (-5.0, -88.0), (2.0, 0.0), 6),
            ("Senate gallery public orientation", (-5.0, 86.0), (2.0, 0.0), 6),
        ],
        start=1,
    ):
        add_queue_line(f"public_fixture_queue_line_{index:02d}", area, start, step, count)

    add_label(labels, "Public benches, exhibit cases, lecterns, receptacles, plant urns, and queue posts - schematic", -27.5, 6.0, 7.8, "furnishing_detail")


def add_joint_session_layout(
    obj: ObjWriter,
    labels: list[dict[str, Any]],
    records: list[dict[str, Any]],
    chamber_records: list[dict[str, Any]],
) -> None:
    """Add generic public visual zones for a joint session in the House Chamber."""
    z = 5.05

    def joint_detail(name: str, kind: str, center: tuple[float, float, float], size: tuple[float, float] | None = None) -> None:
        add_chamber_detail_record(chamber_records, name, kind, "House Chamber", center, size)

    def zone(
        name: str,
        center: tuple[float, float],
        size: tuple[float, float],
        material: str,
        role: str,
        rows: int,
        cols: int,
    ) -> None:
        obj.add_box(center, size, 0.08, z, f"joint_session_zone_{name}", material)
        cx, cy = center
        sx, sy = size
        for row in range(rows):
            for col in range(cols):
                x = cx - sx / 2.0 + sx * (col + 0.5) / cols
                y = cy - sy / 2.0 + sy * (row + 0.5) / rows
                obj.add_box((x, y), (0.46, 0.42), 0.28, z + 0.08, f"{name}_chair_{row+1}_{col+1}", material)
        records.append(
            {
                "name": name,
                "role": role,
                "center_m": [round(cx, 3), round(cy, 3), round(z, 3)],
                "size_m": [round(sx, 3), round(sy, 3)],
                "visual_chairs": rows * cols,
                "assignment": "Generic public visual zone, not a current person-by-person seating chart.",
            }
        )
        add_label(labels, role, cx, cy, z + 1.1, "joint_session")

    # Rostrum arrangement visible during joint addresses: President at front,
    # Speaker and Vice President seated behind. This is a public visual
    # convention, not an operational seating map.
    obj.add_box((0.0, -49.1), (15.0, 5.0), 0.18, z, "joint_session_rostrum_platform", "PublicGallery")
    obj.add_box((0.0, -51.0), (2.1, 1.2), 1.05, z + 0.18, "president_address_podium", "PresidentPodium")
    obj.add_box((-2.0, -47.7), (1.0, 0.8), 0.44, z + 0.22, "speaker_chair_joint_session", "ChairLeather")
    obj.add_box((2.0, -47.7), (1.0, 0.8), 0.44, z + 0.22, "vice_president_chair_joint_session", "ChairLeather")
    obj.add_box((-2.0, -47.25), (1.0, 0.16), 1.05, z + 0.42, "speaker_chair_back_joint_session", "ChairLeather")
    obj.add_box((2.0, -47.25), (1.0, 0.16), 1.05, z + 0.42, "vice_president_chair_back_joint_session", "ChairLeather")
    add_label(labels, "President address podium", 0.0, -51.0, z + 1.8, "joint_session")
    add_label(labels, "Speaker of the House", -2.0, -47.7, z + 1.8, "joint_session")
    add_label(labels, "Vice President / President of the Senate", 2.0, -47.7, z + 1.8, "joint_session")

    for edge_name, center, size in [
        ("front", (0.0, -51.62), (15.4, 0.14)),
        ("left", (-7.58, -49.1), (0.14, 5.0)),
        ("right", (7.58, -49.1), (0.14, 5.0)),
    ]:
        obj.add_box(center, size, 0.055, z + 0.205, f"joint_session_rostrum_{edge_name}_step_edge", "BrassRail")
        joint_detail(f"joint_session_rostrum_{edge_name}_step_edge", "joint_session_rostrum_step_edge", (center[0], center[1], z + 0.232), size)

    obj.add_box((0.0, -51.34), (1.55, 0.46), 0.055, z + 1.25, "president_podium_reading_surface_joint_session", "DeskWood")
    obj.add_cylinder((0.0, -51.61), 0.30, z + 0.72, 0.045, "president_podium_public_front_medallion", "BrassRail", segments=24)
    obj.add_box((-0.18, -51.72), (0.08, 0.18), 0.16, z + 1.34, "president_podium_left_microphone", "DoorMetal")
    obj.add_box((0.18, -51.72), (0.08, 0.18), 0.16, z + 1.34, "president_podium_right_microphone", "DoorMetal")
    joint_detail("president_podium_reading_surface_joint_session", "joint_session_podium_reading_surface", (0.0, -51.34, z + 1.278), (1.55, 0.46))
    joint_detail("president_podium_public_front_medallion", "joint_session_podium_front_medallion", (0.0, -51.61, z + 0.742), (0.60, 0.60))
    joint_detail("president_podium_microphone_pair_joint_session", "joint_session_podium_microphone_pair", (0.0, -51.72, z + 1.42), (0.46, 0.18))

    for side, x in [("left", -1.55), ("right", 1.55)]:
        obj.add_box((x, -51.34), (0.08, 0.58), 0.52, z + 1.03, f"joint_session_{side}_generic_glass_side_panel", "DoorGlass")
        obj.add_cylinder((x, -51.05), 0.035, z + 0.62, 0.46, f"joint_session_{side}_glass_panel_stem", "DoorMetal", segments=8)
        joint_detail(f"joint_session_{side}_generic_glass_side_panel", "joint_session_glass_side_panel", (x, -51.34, z + 1.29), (0.08, 0.58))

    for chair_name, x in [("speaker", -2.0), ("vice_president", 2.0)]:
        obj.add_box((x - 0.54, -47.70), (0.10, 0.76), 0.18, z + 0.68, f"{chair_name}_chair_left_arm_joint_session", "ChairLeather")
        obj.add_box((x + 0.54, -47.70), (0.10, 0.76), 0.18, z + 0.68, f"{chair_name}_chair_right_arm_joint_session", "ChairLeather")
        obj.add_box((x, -47.17), (0.62, 0.040), 0.055, z + 1.10, f"{chair_name}_chair_back_button_row_joint_session", "BrassRail")
        obj.add_box((x, -47.70), (0.78, 0.040), 0.040, z + 0.69, f"{chair_name}_chair_cushion_front_seam_joint_session", "BrassRail")
        joint_detail(f"{chair_name}_chair_arm_pair_joint_session", "joint_session_presiding_chair_arm_pair", (x, -47.70, z + 0.77), (1.18, 0.76))
        joint_detail(f"{chair_name}_chair_back_detail_joint_session", "joint_session_presiding_chair_back_detail", (x, -47.17, z + 1.128), (0.62, 0.040))
        joint_detail(f"{chair_name}_chair_cushion_seam_joint_session", "joint_session_presiding_chair_cushion_seam", (x, -47.70, z + 0.71), (0.78, 0.040))

    records.extend(
        [
            {
                "name": "president_address_podium",
                "role": "President address podium",
                "center_m": [0.0, -51.0, round(z, 3)],
                "visual_chairs": 1,
                "assignment": "Public visual position during joint addresses.",
            },
            {
                "name": "speaker_chair_joint_session",
                "role": "Speaker of the House seated behind President",
                "center_m": [-2.0, -47.7, round(z, 3)],
                "visual_chairs": 1,
                "assignment": "Public visual position during joint addresses.",
            },
            {
                "name": "vice_president_chair_joint_session",
                "role": "Vice President / President of the Senate seated behind President",
                "center_m": [2.0, -47.7, round(z, 3)],
                "visual_chairs": 1,
                "assignment": "Public visual position during joint addresses.",
            },
        ]
    )

    zone("senate_floor_block", (-14.5, -60.5), (13.5, 8.0), "SenateDesk", "Senators / Senate guests generic block", 4, 7)
    zone("cabinet_floor_block", (14.5, -60.5), (13.5, 8.0), "CabinetZone", "Cabinet / executive branch generic block", 4, 7)
    zone("supreme_court_block", (-15.0, -70.5), (12.0, 5.5), "SupremeCourtZone", "Supreme Court generic block", 3, 5)
    zone("diplomatic_corps_block", (15.0, -70.5), (12.0, 5.5), "DiplomaticZone", "Diplomatic corps generic block", 3, 5)
    zone("press_pool_block", (0.0, -59.0), (9.0, 4.2), "PressZone", "Press / camera pool generic block", 2, 6)
    zone("members_and_guests_backfill", (0.0, -82.5), (48.0, 13.0), "JointSessionZone", "Members of Congress and guests overflow generic block", 5, 16)

    for name, center, width, material in [
        ("senate_floor_block", (-14.5, -56.25), 4.2, "SenateDesk"),
        ("cabinet_floor_block", (14.5, -56.25), 4.2, "CabinetZone"),
        ("supreme_court_block", (-15.0, -67.50), 3.8, "SupremeCourtZone"),
        ("diplomatic_corps_block", (15.0, -67.50), 3.8, "DiplomaticZone"),
        ("press_pool_block", (0.0, -56.70), 3.4, "PressZone"),
        ("members_and_guests_backfill", (0.0, -75.60), 5.8, "JointSessionZone"),
    ]:
        obj.add_box(center, (width, 0.12), 0.055, z + 0.19, f"joint_session_{name}_generic_role_nameplate", material)
        joint_detail(f"joint_session_{name}_generic_role_nameplate", "generic_joint_session_role_nameplate", (center[0], center[1], z + 0.218), (width, 0.12))

    for camera_index, (x, y, angle) in enumerate([(-3.2, -58.6, -0.30), (-1.05, -59.35, -0.10), (1.05, -59.35, 0.10), (3.2, -58.6, 0.30)], start=1):
        name = f"joint_session_press_camera_{camera_index:02d}"
        obj.add_cylinder((x, y), 0.055, z + 0.12, 0.70, f"{name}_tripod_center_post", "DoorMetal", segments=8)
        for leg_index, leg_angle in enumerate([angle, angle + 2.10, angle - 2.10], start=1):
            leg_center = (x + math.cos(leg_angle) * 0.34, y + math.sin(leg_angle) * 0.34)
            obj.add_oriented_box(leg_center, (0.72, 0.040), 0.045, z + 0.16, leg_angle, f"{name}_tripod_leg_{leg_index}", "DoorMetal")
        obj.add_oriented_box((x, y - 0.06), (0.48, 0.28), 0.30, z + 0.86, angle, f"{name}_camera_body", "DoorMetal")
        obj.add_oriented_box((x, y - 0.33), (0.26, 0.18), 0.18, z + 0.92, angle, f"{name}_camera_lens", "DoorGlass")
        joint_detail(f"{name}_tripod", "joint_session_press_camera_tripod", (x, y, z + 0.49), (0.88, 0.88))
        joint_detail(f"{name}_camera_body", "joint_session_press_camera_body", (x, y - 0.06, z + 1.01), (0.48, 0.28))
        joint_detail(f"{name}_camera_lens", "joint_session_press_camera_lens", (x, y - 0.33, z + 1.01), (0.26, 0.18))

    for cable_index, (x, y, width, angle) in enumerate([
        (-3.2, -60.15, 2.4, 0.00),
        (-1.05, -60.35, 2.0, 0.00),
        (1.05, -60.35, 2.0, 0.00),
        (3.2, -60.15, 2.4, 0.00),
        (-2.1, -57.30, 2.2, 0.18),
        (2.1, -57.30, 2.2, -0.18),
    ], start=1):
        obj.add_oriented_box((x, y), (width, 0.075), 0.030, z + 0.16, angle, f"joint_session_press_cable_cover_{cable_index:02d}", "DoorMetal")
        joint_detail(f"joint_session_press_cable_cover_{cable_index:02d}", "joint_session_press_cable_cover", (x, y, z + 0.175), (width, 0.075))

    for trim_index, (center, size) in enumerate([
        ((0.0, -61.18), (9.4, 0.10)),
        ((0.0, -56.82), (9.4, 0.10)),
        ((-4.72, -59.0), (0.10, 4.2)),
        ((4.72, -59.0), (0.10, 4.2)),
    ], start=1):
        obj.add_box(center, size, 0.040, z + 0.125, f"joint_session_press_pool_riser_edge_trim_{trim_index}", "BrassRail")
        joint_detail(f"joint_session_press_pool_riser_edge_trim_{trim_index}", "joint_session_press_pool_riser_edge_trim", (center[0], center[1], z + 0.145), size)


def build_seating_sections(
    labels: list[dict[str, Any]],
    seats: list[dict[str, Any]],
    joint_session: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Create public aggregate seating/role summaries for map inspection."""
    house = [seat for seat in seats if seat.get("chamber") == "House Chamber"]
    senate = [seat for seat in seats if seat.get("chamber") == "Senate Chamber"]
    senate_left = [seat for seat in senate if seat.get("location_m", [0.0])[0] < 0]
    senate_right = [seat for seat in senate if seat.get("location_m", [0.0])[0] >= 0]

    sections: list[dict[str, Any]] = [
        {
            "id": "house_representatives_floor_generic",
            "mode": "regular_session",
            "chamber": "House Chamber",
            "role": "Representatives generic floor seating",
            "count": len(house),
            "center_m": [0.0, -82.0, 5.2],
            "size_m": [55.0, 30.0],
            "assignment": "Generic public seating section. Current representative-by-seat assignments are not encoded.",
        },
        {
            "id": "house_rostrum_speaker_clerks_press",
            "mode": "regular_session",
            "chamber": "House Chamber",
            "role": "Speaker rostrum, clerks, and press area",
            "count": None,
            "center_m": [0.0, -48.5, 5.2],
            "size_m": [14.0, 4.2],
            "assignment": "Public role area, not an operational staff seating chart.",
        },
        {
            "id": "house_public_gallery",
            "mode": "regular_session",
            "chamber": "House Chamber",
            "role": "House public gallery / guests / press",
            "count": None,
            "center_m": [0.0, -100.0, 5.2],
            "size_m": [66.0, 8.0],
            "assignment": "Generic public gallery visual section.",
        },
        {
            "id": "senate_desks_left_generic_block",
            "mode": "regular_session",
            "chamber": "Senate Chamber",
            "role": "Senator desks generic left-side block",
            "count": len(senate_left),
            "center_m": [-9.5, 73.0, 5.2],
            "size_m": [20.0, 24.0],
            "assignment": "Generic desk block. Current senator-by-desk assignments are not encoded.",
        },
        {
            "id": "senate_desks_right_generic_block",
            "mode": "regular_session",
            "chamber": "Senate Chamber",
            "role": "Senator desks generic right-side block",
            "count": len(senate_right),
            "center_m": [9.5, 73.0, 5.2],
            "size_m": [20.0, 24.0],
            "assignment": "Generic desk block. Current senator-by-desk assignments are not encoded.",
        },
        {
            "id": "senate_presiding_officer_clerks",
            "mode": "regular_session",
            "chamber": "Senate Chamber",
            "role": "Presiding officer and clerks",
            "count": None,
            "center_m": [0.0, 83.5, 5.2],
            "size_m": [11.5, 3.2],
            "assignment": "Public role area, not an operational staff seating chart.",
        },
        {
            "id": "senate_public_gallery",
            "mode": "regular_session",
            "chamber": "Senate Chamber",
            "role": "Senate public gallery / guests / press",
            "count": None,
            "center_m": [0.0, 97.5, 5.2],
            "size_m": [52.0, 7.0],
            "assignment": "Generic public gallery visual section.",
        },
    ]

    joint_role_by_name = {record.get("name"): record for record in joint_session}
    for name in [
        "president_address_podium",
        "speaker_chair_joint_session",
        "vice_president_chair_joint_session",
        "senate_floor_block",
        "cabinet_floor_block",
        "supreme_court_block",
        "diplomatic_corps_block",
        "press_pool_block",
        "members_and_guests_backfill",
    ]:
        record = joint_role_by_name.get(name)
        if not record:
            continue
        sections.append(
            {
                "id": f"joint_session_{name}",
                "mode": "joint_session",
                "chamber": "House Chamber",
                "role": record["role"],
                "count": record.get("visual_chairs"),
                "center_m": record["center_m"],
                "size_m": record.get("size_m"),
                "assignment": record["assignment"],
            }
        )

    for section in sections[:7]:
        add_label(
            labels,
            section["role"],
            section["center_m"][0],
            section["center_m"][1],
            section["center_m"][2] + 1.25,
            "seating_section",
        )
    return sections


def add_chamber_public_role_zone_overlays(
    obj: ObjWriter,
    labels: list[dict[str, Any]],
    seating_sections: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> None:
    """Add visible public, non-person-specific role-zone overlays for top-down chamber inspection."""

    fallback_sizes: dict[str, tuple[float, float]] = {
        "joint_session_president_address_podium": (2.8, 1.8),
        "joint_session_speaker_chair_joint_session": (1.7, 1.4),
        "joint_session_vice_president_chair_joint_session": (1.7, 1.4),
    }
    material_by_id = {
        "house_representatives_floor_generic": "HouseCarpet",
        "house_rostrum_speaker_clerks_press": "PresidentPodium",
        "house_public_gallery": "PublicGallery",
        "senate_desks_left_generic_block": "SenateDesk",
        "senate_desks_right_generic_block": "SenateDesk",
        "senate_presiding_officer_clerks": "PresidentPodium",
        "senate_public_gallery": "PublicGallery",
        "joint_session_president_address_podium": "PresidentPodium",
        "joint_session_speaker_chair_joint_session": "ChairLeather",
        "joint_session_vice_president_chair_joint_session": "ChairLeather",
        "joint_session_senate_floor_block": "SenateDesk",
        "joint_session_cabinet_floor_block": "CabinetZone",
        "joint_session_supreme_court_block": "SupremeCourtZone",
        "joint_session_diplomatic_corps_block": "DiplomaticZone",
        "joint_session_press_pool_block": "PressZone",
        "joint_session_members_and_guests_backfill": "JointSessionZone",
    }

    def role_material(section_id: str, chamber: str) -> str:
        if section_id in material_by_id:
            return material_by_id[section_id]
        return "HouseCarpet" if chamber == "House Chamber" else "SenateCarpet"

    def detail_z(section: dict[str, Any]) -> float:
        # Keep joint-session overlays above the colored zone pads and regular
        # overlays just above the carpet, so they read in the browser top view.
        return 5.155 if section.get("mode") == "joint_session" else 4.565

    def plaque_anchor(x: float, y: float, sx: float, sy: float, chamber: str) -> tuple[float, float]:
        if chamber == "Senate Chamber":
            return (x, y + sy / 2.0 - min(0.70, sy * 0.22))
        return (x, y - sy / 2.0 + min(0.70, sy * 0.22))

    def add_count_ticks(
        section: dict[str, Any],
        base_name: str,
        chamber: str,
        center: tuple[float, float],
        size: tuple[float, float],
        zone_z: float,
    ) -> None:
        count = section.get("count")
        if not isinstance(count, int) or count <= 0:
            return
        x, y = center
        sx, sy = size
        seats_per_tick = 10 if count > 10 else 1
        tick_count = min(24, max(1, math.ceil(count / seats_per_tick)))
        if sx >= sy:
            tick_width = min(0.34, max(0.10, sx / (tick_count * 2.8)))
            tick_depth = min(0.32, max(0.12, sy * 0.10))
            usable_width = max(tick_width, sx - 1.0)
            start_x = x - usable_width / 2.0
            tick_y = y + sy / 2.0 - min(1.05, sy * 0.24)
        else:
            tick_width = min(0.32, max(0.12, sx * 0.10))
            tick_depth = min(0.34, max(0.10, sy / (tick_count * 2.8)))
            usable_depth = max(tick_depth, sy - 1.0)
            start_y = y - usable_depth / 2.0
            tick_x = x - sx / 2.0 + min(1.05, sx * 0.24)
        for tick_index in range(tick_count):
            if sx >= sy:
                t = 0.5 if tick_count == 1 else tick_index / (tick_count - 1)
                tick_center = (start_x + usable_width * t, tick_y)
                tick_size = (tick_width, tick_depth)
            else:
                t = 0.5 if tick_count == 1 else tick_index / (tick_count - 1)
                tick_center = (tick_x, start_y + usable_depth * t)
                tick_size = (tick_width, tick_depth)
            tick_name = f"{base_name}_count_tick_{tick_index+1:02d}"
            obj.add_box(tick_center, tick_size, 0.040, zone_z + 0.165, tick_name, "LaneMarkingWhite")
            add_chamber_detail_record(
                records,
                tick_name,
                "public_role_zone_count_tick",
                chamber,
                (tick_center[0], tick_center[1], zone_z + 0.185),
                tick_size,
            )
            records[-1].update(
                {
                    "section_id": section.get("id"),
                    "represented_count": count,
                    "seats_per_tick": seats_per_tick,
                    "tick_index": tick_index + 1,
                    "tick_count": tick_count,
                }
            )

    for section in seating_sections:
        section_id = str(section.get("id", "unknown_role_zone"))
        chamber = str(section.get("chamber", "House Chamber"))
        center = section.get("center_m", [0.0, 0.0, 5.2])
        size = section.get("size_m") or fallback_sizes.get(section_id, (2.0, 1.4))
        if not isinstance(center, list) or len(center) < 2:
            continue
        x = float(center[0])
        y = float(center[1])
        sx = max(0.7, float(size[0]))
        sy = max(0.7, float(size[1]))
        base_name = f"{section_id}_public_role_zone"
        zone_z = detail_z(section)
        material = role_material(section_id, chamber)

        obj.add_box((x, y), (sx, sy), 0.028, zone_z, f"{base_name}_floor_overlay", material)
        add_chamber_detail_record(
            records,
            f"{base_name}_floor_overlay",
            "public_role_zone_floor_overlay",
            chamber,
            (x, y, zone_z + 0.014),
            (sx, sy),
        )

        boundary_specs = [
            ("north", (x, y + sy / 2.0), (sx, 0.12)),
            ("south", (x, y - sy / 2.0), (sx, 0.12)),
            ("west", (x - sx / 2.0, y), (0.12, sy)),
            ("east", (x + sx / 2.0, y), (0.12, sy)),
        ]
        for side, boundary_center, boundary_size in boundary_specs:
            boundary_name = f"{base_name}_{side}_boundary_strip"
            obj.add_box(boundary_center, boundary_size, 0.070, zone_z + 0.030, boundary_name, "BrassRail")
            add_chamber_detail_record(
                records,
                boundary_name,
                "public_role_zone_boundary",
                chamber,
                (boundary_center[0], boundary_center[1], zone_z + 0.065),
                boundary_size,
            )

        plaque_x, plaque_y = plaque_anchor(x, y, sx, sy, chamber)
        plaque_width = min(max(sx * 0.34, 1.20), 4.80)
        plaque_depth = 0.18 if sx >= sy else 0.34
        plaque_size = (plaque_width, plaque_depth)
        plaque_z = zone_z + 0.130
        obj.add_box((plaque_x, plaque_y), (plaque_size[0] * 1.12, plaque_size[1] * 1.35), 0.055, plaque_z, f"{base_name}_plaque_backplate", "DoorMetal")
        obj.add_box((plaque_x, plaque_y), plaque_size, 0.045, plaque_z + 0.055, f"{base_name}_plaque_face", "BrassRail")
        add_chamber_detail_record(
            records,
            f"{base_name}_label_plaque",
            "public_role_zone_label_plaque",
            chamber,
            (plaque_x, plaque_y, plaque_z + 0.078),
            plaque_size,
        )
        add_label(
            labels,
            f"Public role zone - {section.get('role', section_id)}",
            plaque_x,
            plaque_y,
            plaque_z + 0.90,
            "chamber_role_overlay",
        )
        add_count_ticks(section, base_name, chamber, (x, y), (sx, sy), zone_z)


def build_house_seats(
    obj: ObjWriter,
    seats: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    chamber_details: list[dict[str, Any]],
) -> None:
    rows = 16
    seats_per_row = 28
    center_x, center_y = 0.0, -70.0
    rostrum_y = -48.5
    seat_id = 1
    obj.add_box((center_x, center_y - 10.0), (55.0, 30.0), 0.08, 4.46, "house_blue_chamber_carpet", "HouseCarpet")
    obj.add_polyline_strip([(0.0, -54.0), (0.0, -95.0)], 1.4, 4.53, "house_center_aisle", "InteriorFloor")
    obj.add_polyline_strip([(-16.0, -56.0), (-29.0, -95.0)], 1.1, 4.54, "house_left_aisle", "InteriorFloor")
    obj.add_polyline_strip([(16.0, -56.0), (29.0, -95.0)], 1.1, 4.54, "house_right_aisle", "InteriorFloor")
    for row in range(rows):
        width = 20.0 + row * 2.2
        y = center_y - row * 1.42
        for col in range(seats_per_row):
            t = (col + 0.5) / seats_per_row
            x = (t - 0.5) * width
            # Fan the rows around the rostrum with slight forward curvature.
            curved_y = y - abs(t - 0.5) * row * 0.24
            obj.add_beveled_box((x, curved_y + 0.20), (0.62, 0.28), 0.42, 4.55, f"house_member_desk_{seat_id:03d}", "HouseDesk", 0.045)
            obj.add_beveled_box((x, curved_y + 0.20), (0.46, 0.18), 0.028, 4.98, f"house_member_desk_top_inset_{seat_id:03d}", "InteriorTrim", 0.022)
            add_generic_chamber_desk_surface_details(
                obj,
                chamber_details,
                f"house_member_desk_{seat_id:03d}",
                "House Chamber",
                (x, curved_y + 0.20),
                (0.46, 0.18),
                5.012,
            )
            obj.add_beveled_box((x, curved_y - 0.24), (0.52, 0.45), 0.26, 4.55, f"house_member_chair_seat_{seat_id:03d}", "HouseSeat", 0.040)
            obj.add_beveled_box((x, curved_y - 0.50), (0.52, 0.14), 0.74, 4.72, f"house_member_chair_back_{seat_id:03d}", "HouseSeat", 0.025)
            obj.add_beveled_box((x - 0.32, curved_y - 0.24), (0.055, 0.36), 0.14, 4.78, f"house_member_chair_left_arm_{seat_id:03d}", "HouseSeat", 0.012)
            obj.add_beveled_box((x + 0.32, curved_y - 0.24), (0.055, 0.36), 0.14, 4.78, f"house_member_chair_right_arm_{seat_id:03d}", "HouseSeat", 0.012)
            add_generic_chamber_furniture_finish_details(
                obj,
                chamber_details,
                f"house_member_{seat_id:03d}",
                "House Chamber",
                (x, curved_y + 0.20),
                (0.62, 0.28),
                5.015,
                (x, curved_y - 0.24),
                (0.52, 0.45),
                4.82,
                (x, curved_y - 0.50),
                (0.52, 0.14),
                4.72,
                0.74,
            )
            add_chamber_detail_record(
                chamber_details,
                f"house_member_desk_top_inset_{seat_id:03d}",
                "generic_desk_surface_inset",
                "House Chamber",
                (x, curved_y + 0.20, 4.994),
                (0.46, 0.18),
            )
            add_chamber_detail_record(
                chamber_details,
                f"house_member_chair_arm_pair_{seat_id:03d}",
                "generic_chair_arm_pair",
                "House Chamber",
                (x, curved_y - 0.24, 4.85),
                (0.70, 0.36),
            )
            add_chamber_detail_record(
                chamber_details,
                f"house_member_beveled_furniture_{seat_id:03d}",
                "generic_beveled_chamber_furniture",
                "House Chamber",
                (x, curved_y - 0.02, 4.84),
                (0.74, 0.90),
            )
            seats.append(
                {
                    "id": f"house_member_seat_{seat_id:03d}",
                    "chamber": "House Chamber",
                    "role": "Representative floor seat",
                    "assignment": "Unassigned/generic. Representatives do not have permanent assigned floor seats in this dataset.",
                    "location_m": [round(x, 3), round(curved_y, 3), 4.78],
                    "row": row + 1,
                    "column": col + 1,
                }
            )
            seat_id += 1
        row_panel_name = f"house_member_row_modesty_panel_{row+1:02d}"
        obj.add_box((center_x, y + 0.44), (width * 0.92, 0.055), 0.18, 4.62, row_panel_name, "DeskWood")
        add_chamber_detail_record(
            chamber_details,
            row_panel_name,
            "generic_row_modesty_panel",
            "House Chamber",
            (center_x, y + 0.44, 4.71),
            (width * 0.92, 0.055),
        )
    add_label(labels, "House member seating: 448 generic floor seats", center_x, center_y - 13.0, 5.25, "seating")
    add_label(labels, "Speaker rostrum / clerks / press area", center_x, rostrum_y, 5.25, "seating")
    obj.add_box((center_x, rostrum_y), (14.0, 4.2), 0.38, 4.55, "house_rostrum_lower_platform", "PublicGallery")
    obj.add_box((center_x, rostrum_y + 0.9), (10.5, 2.2), 0.72, 4.9, "house_speaker_dais", "PublicGallery")
    obj.add_box((center_x, rostrum_y + 1.15), (6.0, 0.9), 0.72, 5.55, "house_speaker_desk", "DeskWood")
    obj.add_box((-6.5, rostrum_y - 0.65), (3.2, 1.2), 0.7, 4.75, "house_clerk_table_left", "DeskWood")
    obj.add_box((6.5, rostrum_y - 0.65), (3.2, 1.2), 0.7, 4.75, "house_clerk_table_right", "DeskWood")
    add_gallery_risers(obj, "house_north_public_gallery", (0.0, -100.0), 66.0, 8.0, 4, 4.55)


def build_senate_desks(
    obj: ObjWriter,
    seats: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    chamber_details: list[dict[str, Any]],
) -> None:
    desk_id = 1
    center_x, center_y = 0.0, 65.0
    presiding_y = 83.5
    obj.add_box((center_x, center_y + 8.0), (42.0, 26.0), 0.08, 4.46, "senate_red_chamber_carpet", "SenateCarpet")
    obj.add_polyline_strip([(0.0, 62.0), (0.0, 83.0)], 1.2, 4.53, "senate_center_aisle", "InteriorFloor")
    obj.add_polyline_strip([(-10.0, 63.0), (-19.0, 82.0)], 0.9, 4.54, "senate_left_aisle", "InteriorFloor")
    obj.add_polyline_strip([(10.0, 63.0), (19.0, 82.0)], 0.9, 4.54, "senate_right_aisle", "InteriorFloor")
    for row in range(10):
        width = 13.0 + row * 2.2
        y = center_y + row * 1.35
        for col in range(10):
            t = (col + 0.5) / 10.0
            x = (t - 0.5) * width
            curved_y = y + abs(t - 0.5) * row * 0.20
            obj.add_beveled_box((x, curved_y + 0.16), (0.82, 0.58), 0.54, 4.55, f"senate_desk_{desk_id:03d}", "SenateDesk", 0.055)
            obj.add_beveled_box((x, curved_y + 0.16), (0.60, 0.38), 0.028, 5.10, f"senate_desk_top_inset_{desk_id:03d}", "InteriorTrim", 0.030)
            add_generic_chamber_desk_surface_details(
                obj,
                chamber_details,
                f"senate_desk_{desk_id:03d}",
                "Senate Chamber",
                (x, curved_y + 0.16),
                (0.60, 0.38),
                5.132,
            )
            obj.add_beveled_box((x, curved_y - 0.40), (0.62, 0.50), 0.32, 4.55, f"senate_chair_seat_{desk_id:03d}", "SenateChair", 0.045)
            obj.add_beveled_box((x, curved_y - 0.70), (0.62, 0.16), 0.82, 4.72, f"senate_chair_back_{desk_id:03d}", "SenateChair", 0.030)
            obj.add_beveled_box((x - 0.38, curved_y - 0.40), (0.06, 0.40), 0.16, 4.82, f"senate_chair_left_arm_{desk_id:03d}", "SenateChair", 0.014)
            obj.add_beveled_box((x + 0.38, curved_y - 0.40), (0.06, 0.40), 0.16, 4.82, f"senate_chair_right_arm_{desk_id:03d}", "SenateChair", 0.014)
            add_generic_chamber_furniture_finish_details(
                obj,
                chamber_details,
                f"senate_desk_{desk_id:03d}",
                "Senate Chamber",
                (x, curved_y + 0.16),
                (0.82, 0.58),
                5.125,
                (x, curved_y - 0.40),
                (0.62, 0.50),
                4.88,
                (x, curved_y - 0.70),
                (0.62, 0.16),
                4.72,
                0.82,
            )
            add_chamber_detail_record(
                chamber_details,
                f"senate_desk_top_inset_{desk_id:03d}",
                "generic_desk_surface_inset",
                "Senate Chamber",
                (x, curved_y + 0.16, 5.114),
                (0.60, 0.38),
            )
            add_chamber_detail_record(
                chamber_details,
                f"senate_chair_arm_pair_{desk_id:03d}",
                "generic_chair_arm_pair",
                "Senate Chamber",
                (x, curved_y - 0.40, 4.90),
                (0.82, 0.40),
            )
            add_chamber_detail_record(
                chamber_details,
                f"senate_beveled_furniture_{desk_id:03d}",
                "generic_beveled_chamber_furniture",
                "Senate Chamber",
                (x, curved_y - 0.12, 4.90),
                (0.92, 1.10),
            )
            caucus_side = "generic left-side block" if x < 0 else "generic right-side block"
            seats.append(
                {
                    "id": f"senate_desk_{desk_id:03d}",
                    "chamber": "Senate Chamber",
                    "role": "Senator desk",
                    "assignment": "Generic desk. Current senator-by-desk assignments are not encoded.",
                    "caucus_side": caucus_side,
                    "location_m": [round(x, 3), round(curved_y, 3), 4.78],
                    "row": row + 1,
                    "column": col + 1,
                }
            )
            desk_id += 1
        row_panel_name = f"senate_desk_row_modesty_panel_{row+1:02d}"
        obj.add_box((center_x, y + 0.56), (width * 0.90, 0.060), 0.20, 4.64, row_panel_name, "DeskWood")
        add_chamber_detail_record(
            chamber_details,
            row_panel_name,
            "generic_row_modesty_panel",
            "Senate Chamber",
            (center_x, y + 0.56, 4.74),
            (width * 0.90, 0.060),
        )
    add_label(labels, "Senate desks: 100 generic desks", center_x, center_y + 8.0, 5.25, "seating")
    add_label(labels, "Presiding officer / clerks", center_x, presiding_y, 5.25, "seating")
    obj.add_box((center_x, presiding_y), (11.5, 3.2), 0.36, 4.55, "senate_presiding_officer_platform", "PublicGallery")
    obj.add_box((center_x, presiding_y + 0.65), (7.8, 1.5), 0.72, 4.9, "senate_presiding_officer_dais", "PublicGallery")
    obj.add_box((center_x, presiding_y + 0.85), (4.2, 0.8), 0.72, 5.5, "senate_presiding_officer_desk", "DeskWood")
    obj.add_box((-4.8, presiding_y - 0.75), (2.8, 1.1), 0.65, 4.75, "senate_clerk_table_left", "DeskWood")
    obj.add_box((4.8, presiding_y - 0.75), (2.8, 1.1), 0.65, 4.75, "senate_clerk_table_right", "DeskWood")
    add_gallery_risers(obj, "senate_public_gallery", (0.0, 97.5), 52.0, 7.0, 4, 4.55)


def build_interior() -> dict[str, Any]:
    obj = ObjWriter("capitol_public_interior_schematic")
    rooms: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    seats: list[dict[str, Any]] = []
    seating_sections: list[dict[str, Any]] = []
    office_cells: list[dict[str, Any]] = []
    office_details: list[dict[str, Any]] = []
    joint_session: list[dict[str, Any]] = []
    public_art: list[dict[str, Any]] = []
    light_fixtures: list[dict[str, Any]] = []
    light_fixture_details: list[dict[str, Any]] = []
    wall_treatments: list[dict[str, Any]] = []
    wall_finish_details: list[dict[str, Any]] = []
    chamber_details: list[dict[str, Any]] = []
    circulation_details: list[dict[str, Any]] = []
    signage_details: list[dict[str, Any]] = []
    door_details: list[dict[str, Any]] = []
    furnishing_details: list[dict[str, Any]] = []
    rotunda_details: list[dict[str, Any]] = []
    ceiling_details: list[dict[str, Any]] = []
    floor_details: list[dict[str, Any]] = []
    surface_aging_details: list[dict[str, Any]] = []

    # Broad second-floor public schematic. North = +Y. East = +X.
    add_room(obj, rooms, labels, "Capitol second-floor public schematic footprint", (0.0, 0.0), (150.0, 190.0), "InteriorFloor", "floorplate", z=3.95, height=0.08, with_walls=True)
    obj.add_disk((0.0, 0.0), 14.63, 4.08, "rotunda_96ft_diameter_public_schematic", "RotundaFloor", segments=80)
    rooms.append(
        {
            "name": "Rotunda",
            "category": "major_public_space",
            "center_m": [0.0, 0.0, 4.08],
            "diameter_m": 29.26,
            "diameter_source": "AOC states 96 feet diameter",
            "public_accuracy": "dimensioned_public_reference",
        }
    )
    add_label(labels, "Rotunda - 96 ft diameter", 0.0, 0.0, 5.0, "major_public_space")
    add_rotunda_visual_details(obj, labels, rotunda_details)

    add_room(obj, rooms, labels, "National Statuary Hall", (28.0, -30.0), (30.0, 20.0), "RotundaFloor", "major_public_space")
    add_room(obj, rooms, labels, "Old Senate Chamber", (28.0, 30.0), (26.0, 18.0), "RotundaFloor", "major_public_space")
    add_room(obj, rooms, labels, "Crypt below Rotunda marker", (0.0, -24.0), (24.0, 12.0), "MarkerBlue", "major_public_space")
    add_room(obj, rooms, labels, "House Chamber", (0.0, -72.0), (62.0, 42.0), "InteriorWall", "legislative_chamber")
    add_room(obj, rooms, labels, "Senate Chamber", (0.0, 68.0), (48.0, 38.0), "InteriorWall", "legislative_chamber")
    add_room(obj, rooms, labels, "House galleries", (0.0, -96.0), (68.0, 10.0), "PublicGallery", "visitor_gallery")
    add_room(obj, rooms, labels, "Senate galleries", (0.0, 94.0), (54.0, 10.0), "PublicGallery", "visitor_gallery")
    add_room(obj, rooms, labels, "House leadership/support offices - schematic zone", (-53.0, -55.0), (22.0, 46.0), "OfficeZone", "generic_office_zone")
    add_room(obj, rooms, labels, "House committee/support rooms - schematic zone", (53.0, -55.0), (22.0, 46.0), "OfficeZone", "generic_office_zone")
    add_room(obj, rooms, labels, "Senate leadership/support offices - schematic zone", (-52.0, 55.0), (22.0, 46.0), "OfficeZone", "generic_office_zone")
    add_room(obj, rooms, labels, "Senate committee/support rooms - schematic zone", (52.0, 55.0), (22.0, 46.0), "OfficeZone", "generic_office_zone")
    add_room(obj, rooms, labels, "East public approach / visitor circulation", (62.0, 0.0), (14.0, 70.0), "InteriorFloor", "public_circulation")
    add_room(obj, rooms, labels, "West terrace public orientation marker", (-62.0, 0.0), (14.0, 70.0), "InteriorFloor", "public_circulation")

    office_cells.extend(add_public_office_grid(obj, labels, "house_west_support", (-53.0, -55.0), (19.0, 42.0), 3, 5, office_details))
    office_cells.extend(add_public_office_grid(obj, labels, "house_east_support", (53.0, -55.0), (19.0, 42.0), 3, 5, office_details))
    office_cells.extend(add_public_office_grid(obj, labels, "senate_west_support", (-52.0, 55.0), (19.0, 42.0), 3, 5, office_details))
    office_cells.extend(add_public_office_grid(obj, labels, "senate_east_support", (52.0, 55.0), (19.0, 42.0), 3, 5, office_details))

    add_public_circulation_details(obj, labels, circulation_details)
    add_public_interior_signage_details(obj, labels, signage_details)
    add_public_interior_door_details(obj, labels, door_details)
    add_public_interior_furnishing_details(obj, labels, furnishing_details)
    build_house_seats(obj, seats, labels, chamber_details)
    build_senate_desks(obj, seats, labels, chamber_details)
    add_joint_session_layout(obj, labels, joint_session, chamber_details)
    seating_sections.extend(build_seating_sections(labels, seats, joint_session))
    add_chamber_public_role_zone_overlays(obj, labels, seating_sections, chamber_details)
    add_chamber_realism_details(obj, labels, chamber_details)
    public_art, light_fixtures, light_fixture_details = add_public_art_and_lighting(obj, labels)

    add_wall_treatment(obj, wall_treatments, "rotunda_wall_finish", "Rotunda", (0.0, 0.0), (29.5, 29.5), 10, 10, z=4.45)
    add_wall_treatment(obj, wall_treatments, "house_chamber_wall_finish", "House Chamber", (0.0, -72.0), (62.0, 42.0), 12, 8, z=4.45)
    add_wall_treatment(obj, wall_treatments, "senate_chamber_wall_finish", "Senate Chamber", (0.0, 68.0), (48.0, 38.0), 10, 8, z=4.45)
    add_wall_treatment(obj, wall_treatments, "national_statuary_hall_wall_finish", "National Statuary Hall", (28.0, -30.0), (30.0, 20.0), 8, 5, z=4.45)
    add_wall_treatment(obj, wall_treatments, "old_senate_chamber_wall_finish", "Old Senate Chamber", (28.0, 30.0), (26.0, 18.0), 7, 5, z=4.45)
    add_wall_treatment(obj, wall_treatments, "house_gallery_wall_finish", "House galleries", (0.0, -96.0), (68.0, 10.0), 12, 3, z=4.45)
    add_wall_treatment(obj, wall_treatments, "senate_gallery_wall_finish", "Senate galleries", (0.0, 94.0), (54.0, 10.0), 10, 3, z=4.45)
    add_wall_treatment(obj, wall_treatments, "house_west_office_wall_finish", "House leadership/support offices - schematic zone", (-53.0, -55.0), (22.0, 46.0), 5, 8, z=4.45)
    add_wall_treatment(obj, wall_treatments, "house_east_office_wall_finish", "House committee/support rooms - schematic zone", (53.0, -55.0), (22.0, 46.0), 5, 8, z=4.45)
    add_wall_treatment(obj, wall_treatments, "senate_west_office_wall_finish", "Senate leadership/support offices - schematic zone", (-52.0, 55.0), (22.0, 46.0), 5, 8, z=4.45)
    add_wall_treatment(obj, wall_treatments, "senate_east_office_wall_finish", "Senate committee/support rooms - schematic zone", (52.0, 55.0), (22.0, 46.0), 5, 8, z=4.45)
    add_public_interior_wall_finish_details(obj, labels, wall_finish_details)
    add_public_interior_ceiling_details(obj, labels, ceiling_details)
    add_public_interior_floor_details(obj, labels, floor_details)
    add_public_interior_surface_aging_details(obj, labels, surface_aging_details)
    add_label(labels, "Wainscot panels, chair rails, and picture rails - schematic", 0.0, -6.5, 7.6, "wall_treatment")

    obj.write(MESH_DIR / "capitol_public_interior_schematic.obj", "capitol_materials.mtl")
    return {
        "rooms": rooms,
        "labels": labels,
        "seating": seats,
        "seating_sections": seating_sections,
        "office_cells": office_cells,
        "office_details": office_details,
        "joint_session": joint_session,
        "public_art": public_art,
        "light_fixtures": light_fixtures,
        "light_fixture_details": light_fixture_details,
        "wall_treatments": wall_treatments,
        "wall_finish_details": wall_finish_details,
        "chamber_details": chamber_details,
        "circulation_details": circulation_details,
        "signage_details": signage_details,
        "door_details": door_details,
        "furnishing_details": furnishing_details,
        "rotunda_details": rotunda_details,
        "ceiling_details": ceiling_details,
        "floor_details": floor_details,
        "surface_aging_details": surface_aging_details,
        "interior_notice": (
            "Public schematic only. It maps major public spaces and generic chamber seating. "
            "It does not include restricted security details, private office assignments, "
            "secure routes, or current occupant-by-seat assignments."
        ),
    }


def build_gameplay_items() -> dict[str, Any]:
    obj = ObjWriter("capitol_gameplay_items")
    items: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    flagpole_banners: list[dict[str, Any]] = []

    base_x = -132.0
    base_y = -126.0
    spacing = 8.0
    z = 0.28
    definitions = [
        ("flagpole", "Flagpole", "flagpole_melee_prop", "abstract_melee_reach"),
        ("nunchucks", "Nunchucks", "nunchucks_melee_prop", "abstract_melee_stun"),
        ("bear_spray", "Bear spray", "bear_spray_prop", "abstract_cone_irritant_status"),
        ("mace_spray", "Mace spray", "mace_spray_prop", "abstract_short_cone_irritant_status"),
        ("feces_throwable", "Throwable feces", "feces_throwable_prop", "abstract_throwable_contamination"),
        ("knife", "Knife", "knife_melee_prop", "abstract_close_melee"),
        ("handgun", "Handgun", "handgun_prop", "abstract_ranged_placeholder"),
    ]

    def add_record(
        item_id: str,
        display_name: str,
        item_type: str,
        effect_class: str,
        center: tuple[float, float],
        aliases: list[str] | None = None,
    ) -> None:
        items.append(
            {
                "id": item_id,
                "display_name": display_name,
                "item_type": item_type,
                "category": "gameplay_item",
                "center_m": [round(center[0], 3), round(center[1], 3), round(z + 0.55, 3)],
                "sandbox_location": "Gameplay item preview lane west of the public map core",
                "effect_class": effect_class,
                "non_graphic": True,
                "public_accuracy": "fictional_gameplay_pickup_not_historical_or_map_feature",
                "implementation_note": "Abstract game pickup prop only; no real-world use, construction, or operational placement guidance.",
                "aliases": aliases or [],
            }
        )
        add_label(labels, display_name, center[0], center[1], z + 1.45, "gameplay_item")

    def add_pickup_pad(item_id: str, center: tuple[float, float], display_name: str) -> None:
        x, y = center
        obj.add_box((x, y), (5.4, 3.2), 0.12, 0.08, f"{item_id}_pickup_pad", "GameplayPickupPad")
        obj.add_box((x, y - 1.85), (4.4, 0.18), 0.18, 0.20, f"{item_id}_front_label_strip", "MarkerBlue")
        obj.add_box((x, y + 1.85), (4.4, 0.18), 0.18, 0.20, f"{item_id}_back_label_strip", "MarkerBlue")

    def add_flagpole(center: tuple[float, float]) -> None:
        x, y = center
        obj.add_box((x, y), (4.4, 0.13), 0.13, z + 0.22, "flagpole_staff", "ItemWood")
        obj.add_cylinder((x - 2.25, y), 0.15, z + 0.16, 0.24, "flagpole_end_cap", "ItemMetal", segments=12)

        # Flat prop panels, not exact merchandise replicas. The American flag
        # uses simple stripe/canton geometry; campaign banners use readable
        # metadata labels plus color-blocked cloth shapes for the viewer/Unreal.
        stripe_h = 0.055
        flag_origin_x = x + 0.72
        flag_origin_y = y + 0.50
        for stripe in range(13):
            material = "ItemCloth" if stripe % 2 == 0 else "LaneMarkingWhite"
            obj.add_box(
                (flag_origin_x + 0.48, flag_origin_y + stripe * stripe_h),
                (0.96, 0.045),
                0.035,
                z + 0.43,
                f"flagpole_american_flag_stripe_{stripe+1:02d}",
                material,
            )
        obj.add_box((flag_origin_x + 0.17, flag_origin_y + 0.47), (0.36, 0.30), 0.045, z + 0.46, "flagpole_american_flag_canton", "MarkerBlue")
        for star_index in range(12):
            sx = flag_origin_x + 0.04 + (star_index % 4) * 0.08
            sy = flag_origin_y + 0.37 + (star_index // 4) * 0.08
            obj.add_box((sx, sy), (0.025, 0.025), 0.055, z + 0.50, f"flagpole_american_flag_star_{star_index+1:02d}", "LaneMarkingWhite")
        flagpole_banners.append(
            {
                "id": "american_flag",
                "display_name": "American flag",
                "kind": "flag",
                "center_m": [round(flag_origin_x + 0.48, 3), round(flag_origin_y + 0.34, 3), round(z + 0.52, 3)],
                "style": "abstract red white stripe and blue canton game prop",
                "public_accuracy": "fictional_gameplay_banner_visual",
            }
        )

        banner_specs = [
            ("trump_2024_red", "Trump 2024 red banner", "ItemCloth", "LaneMarkingWhite"),
            ("trump_2024_blue", "Trump 2024 blue banner", "MarkerBlue", "LaneMarkingWhite"),
            ("save_america_red", "Save America campaign-style banner", "ItemCloth", "LaneMarkingWhite"),
            ("maga_blue", "Make America Great Again campaign-style banner", "MarkerBlue", "LaneMarkingWhite"),
        ]
        for banner_index, (banner_id, display_name, background, accent) in enumerate(banner_specs):
            bx = x - 1.30 + (banner_index % 2) * 2.65
            by = y - 1.22 - (banner_index // 2) * 0.62
            obj.add_box((bx, by), (2.35, 0.40), 0.045, z + 0.42, f"flagpole_{banner_id}_cloth", background)
            obj.add_box((bx, by - 0.16), (2.05, 0.035), 0.055, z + 0.47, f"flagpole_{banner_id}_top_text_bar", accent)
            obj.add_box((bx, by + 0.16), (1.45, 0.035), 0.055, z + 0.47, f"flagpole_{banner_id}_bottom_text_bar", accent)
            obj.add_box((bx - 1.25, by), (0.08, 0.48), 0.08, z + 0.36, f"flagpole_{banner_id}_left_grommet_strip", "ItemMetal")
            flagpole_banners.append(
                {
                    "id": banner_id,
                    "display_name": display_name,
                    "kind": "campaign_banner",
                    "center_m": [round(bx, 3), round(by, 3), round(z + 0.48, 3)],
                    "style": "abstract color-blocked campaign-style banner, not exact merch artwork",
                    "public_accuracy": "fictional_gameplay_banner_visual",
                    "text_reference": display_name,
                }
            )

    def add_nunchucks(center: tuple[float, float]) -> None:
        x, y = center
        obj.add_box((x - 0.75, y), (1.25, 0.26), 0.24, z + 0.24, "nunchucks_left_handle", "ItemWood")
        obj.add_box((x + 0.75, y), (1.25, 0.26), 0.24, z + 0.24, "nunchucks_right_handle", "ItemWood")
        obj.add_box((x, y), (0.70, 0.08), 0.08, z + 0.42, "nunchucks_chain", "ItemMetal")

    def add_spray_can(item_id: str, center: tuple[float, float], radius: float, height: float, material: str) -> None:
        x, y = center
        obj.add_cylinder((x, y), radius, z + 0.18, height, f"{item_id}_canister", material, segments=18)
        obj.add_cylinder((x, y), radius * 0.72, z + 0.18 + height, 0.18, f"{item_id}_cap", "ItemMetal", segments=18)
        obj.add_box((x + radius * 0.55, y), (radius * 1.3, radius * 0.28), 0.12, z + 0.18 + height + 0.14, f"{item_id}_nozzle", "ItemGrip")

    def add_feces_throwable(center: tuple[float, float]) -> None:
        x, y = center
        obj.add_cylinder((x, y), 0.55, z + 0.18, 0.22, "feces_throwable_base_blob", "ItemOrganicBrown", segments=18)
        obj.add_cylinder((x - 0.18, y + 0.05), 0.38, z + 0.36, 0.22, "feces_throwable_mid_blob", "ItemOrganicBrown", segments=18)
        obj.add_cylinder((x + 0.10, y - 0.03), 0.24, z + 0.54, 0.18, "feces_throwable_top_blob", "ItemOrganicBrown", segments=18)

    def add_knife(center: tuple[float, float]) -> None:
        x, y = center
        obj.add_box((x - 0.62, y), (1.05, 0.28), 0.18, z + 0.26, "knife_grip", "ItemGrip")
        obj.add_box((x + 0.56, y), (1.35, 0.20), 0.10, z + 0.30, "knife_blade", "ItemBlade")
        obj.add_box((x - 0.02, y), (0.12, 0.46), 0.20, z + 0.23, "knife_guard", "ItemMetal")

    def add_handgun(center: tuple[float, float]) -> None:
        x, y = center
        obj.add_box((x - 0.10, y), (1.35, 0.36), 0.34, z + 0.28, "handgun_slide_block", "ItemMetal")
        obj.add_box((x + 0.74, y), (0.70, 0.18), 0.18, z + 0.36, "handgun_barrel_block", "ItemMetal")
        obj.add_box((x - 0.45, y - 0.28), (0.34, 0.26), 0.82, z + 0.02, "handgun_grip_block", "ItemGrip")
        obj.add_box((x + 0.05, y - 0.27), (0.28, 0.10), 0.30, z + 0.18, "handgun_trigger_guard_silhouette", "ItemGrip")

    builders = {
        "flagpole": add_flagpole,
        "nunchucks": add_nunchucks,
        "bear_spray": lambda center: add_spray_can("bear_spray", center, 0.38, 1.18, "ItemWarningOrange"),
        "mace_spray": lambda center: add_spray_can("mace_spray", center, 0.28, 0.92, "ItemSprayCan"),
        "feces_throwable": add_feces_throwable,
        "knife": add_knife,
        "handgun": add_handgun,
    }

    for index, (item_id, display_name, item_type, effect_class) in enumerate(definitions):
        center = (base_x + (index % 4) * spacing, base_y + (index // 4) * spacing)
        add_pickup_pad(item_id, center, display_name)
        builders[item_id](center)
        aliases = ["numb-chucks"] if item_id == "nunchucks" else []
        add_record(item_id, display_name, item_type, effect_class, center, aliases)

    obj.write(MESH_DIR / "capitol_gameplay_items.obj", "capitol_materials.mtl")
    return {
        "items": items,
        "labels": labels,
        "flagpole_banners": flagpole_banners,
        "notice": (
            "Fictional non-graphic gameplay pickup props only. These are not historical placements, "
            "not public-safety guidance, and not real-world weapon use or construction instructions."
        ),
    }


def write_scene_metadata(
    exterior: dict[str, Any],
    landmark: dict[str, Any],
    interior: dict[str, Any],
    gameplay: dict[str, Any],
    osm_data: dict[str, Any],
) -> None:
    metadata = {
        "package": "capitol_unreal_map",
        "coordinate_system": {
            "origin": {
                "lat": LAT0,
                "lon": LON0,
                "description": "Approximate U.S. Capitol center; local X=east meters, local Y=north meters, Z=up meters.",
            },
            "obj_units": "centimeters",
            "unreal_scale_note": "OBJ vertices are written in centimeters so import scale can remain 1.0 in Unreal.",
        },
        "sources": {
            "target_map_era": {
                "label": TARGET_MAP_ERA,
                "target_osm_date_utc": TARGET_OSM_DATE_UTC,
                "selected_osm_source": relative_to_package(SOURCE),
                "fallback_note": (
                    "Historical OSM extracts are preferred. The 2026 extract is a visible fallback only "
                    "when the Jan 6-era or strict 2020 source file has not been fetched."
                ),
            },
            "exterior_osm": {
                "file": relative_to_package(SOURCE),
                "target_map_era": TARGET_MAP_ERA,
                "target_osm_date_utc": TARGET_OSM_DATE_UTC,
                "source_request": osm_data.get("source_request", {}),
                "generator": osm_data.get("generator"),
                "timestamp_osm_base": osm_data.get("osm3s", {}).get("timestamp_osm_base"),
                "license": "OpenStreetMap data is available under the Open Database License (ODbL).",
            },
            "interior_public_reference": [
                "Architect of the Capitol public pages for U.S. Capitol Building, Rotunda, House Wing, and Senate Wing.",
                "Interior spaces are schematic and based on publicly described major rooms and chamber functions.",
            ],
            "exterior_dcgis_planimetrics_1999": {
                "file": exterior.get("height_model", {}).get("dcgis_source_file"),
                "service_url": exterior.get("height_model", {}).get("dcgis_service_url"),
                "retrieved_utc": exterior.get("height_model", {}).get("dcgis_retrieved_utc"),
                "layers": [
                    "Rooftop Elevations - 1999",
                    "Elevation Point - 1999",
                ],
                "usage": "Conservative surrounding-building height correction for missing-height footprints only.",
            },
            "exterior_dcgis_planimetrics_1999_traffic_signs": {
                "file": exterior.get("traffic_sign_model", {}).get("source_file"),
                "service_url": exterior.get("traffic_sign_model", {}).get("service_url"),
                "retrieved_utc": exterior.get("traffic_sign_model", {}).get("retrieved_utc"),
                "layers": [
                    "Other Traffic Signs - 1999",
                    "Overhead Traffic Signs - 1999",
                ],
                "usage": "Generic public traffic-control sign and overhead-sign streetscape props.",
            },
            "exterior_dcgis_planimetrics_1999_public_fixtures": {
                "file": exterior.get("public_fixture_model", {}).get("source_file"),
                "service_url": exterior.get("public_fixture_model", {}).get("service_url"),
                "retrieved_utc": exterior.get("public_fixture_model", {}).get("retrieved_utc"),
                "layers": [
                    "Fire Hydrants - 1999",
                    "Miscellaneous Points (statues, planters, benches, bollard) - 1999",
                    "Street Trees - 1999",
                    "Utilities Poles - 1999",
                ],
                "usage": "Generic public hydrant, tree, utility-pole, and miscellaneous streetscape fixture props.",
            },
            "exterior_dcgis_planimetrics_1999_ground_surfaces": {
                "file": exterior.get("ground_surface_model", {}).get("source_file"),
                "service_url": exterior.get("ground_surface_model", {}).get("service_url"),
                "retrieved_utc": exterior.get("ground_surface_model", {}).get("retrieved_utc"),
                "layers": [
                    "Curbs - 1999",
                    "Roads - 1999",
                    "Sidewalks - 1999",
                ],
                "usage": "Public curb-line, sidewalk-edge, and road/sidewalk surface-patch streetscape details.",
            },
        },
        "meshes": [
            "generated/meshes/capitol_exterior_buildings.obj",
            "generated/meshes/capitol_exterior_roads_bike_lanes_markers.obj",
            "generated/meshes/capitol_landmark_visual_details.obj",
            "generated/meshes/capitol_public_interior_schematic.obj",
            "generated/meshes/capitol_gameplay_items.obj",
        ],
        "viewpoints": VIEWPOINTS,
        "exterior": exterior,
        "landmark": landmark,
        "interior": interior,
        "gameplay": gameplay,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "capitol_scene_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def main() -> None:
    MESH_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    write_mtl(MESH_DIR / "capitol_materials.mtl")
    nodes, ways, osm_data = load_osm()
    print(f"Using OSM source {relative_to_package(SOURCE)}")
    if SOURCE == PRESENT_DAY_OSM_SOURCE:
        print(
            "Warning: Jan 6-era OSM source is missing; using the 2026 fallback extract. "
            "Run scripts/fetch_osm_historical_capitol.py to fetch the historical source."
        )
    exterior = build_exterior(nodes, ways)
    landmark = build_capitol_landmark_details()
    interior = build_interior()
    gameplay = build_gameplay_items()
    write_scene_metadata(exterior, landmark, interior, gameplay, osm_data)
    print(f"Wrote meshes to {MESH_DIR}")
    print(f"Wrote metadata to {DATA_DIR / 'capitol_scene_metadata.json'}")
    print(
        "Counts:",
        f"{len(exterior['buildings'])} buildings,",
        f"{len(exterior['roads'])} roads/paths,",
        f"{len(exterior['bike_lanes'])} bike features,",
        f"{len(exterior['pedestrian_paths'])} pedestrian paths,",
        f"{len(exterior['curbs'])} curb edge records,",
        f"{len(exterior['street_markers'])} street markers,",
        f"{len(exterior['building_details'])} building visual details,",
        f"{len(exterior['streetscape_props'])} streetscape props,",
        f"{len(exterior['grounds_details'])} grounds details,",
        f"{len(landmark['elements'])} landmark detail elements,",
        f"{len(landmark['facade_details'])} facade/furniture details,",
        f"{len(interior['office_cells'])} generic office cells,",
        f"{len(interior['office_details'])} public office details,",
        f"{len(interior['seating_sections'])} seating sections,",
        f"{len(interior['public_art'])} public-art visuals,",
        f"{len(interior['light_fixtures'])} light fixtures,",
        f"{len(interior['light_fixture_details'])} light fixture detail records,",
        f"{len(interior['wall_treatments'])} wall-treatment records,",
        f"{len(interior['wall_finish_details'])} wall-finish detail records,",
        f"{len(interior['chamber_details'])} chamber detail records,",
        f"{len(interior['circulation_details'])} circulation detail records,",
        f"{len(interior['signage_details'])} signage detail records,",
        f"{len(interior['door_details'])} door detail records,",
        f"{len(interior['furnishing_details'])} furnishing detail records,",
        f"{len(interior['rotunda_details'])} rotunda detail records,",
        f"{len(interior['ceiling_details'])} ceiling detail records,",
        f"{len(interior['floor_details'])} floor detail records,",
        f"{len(interior['surface_aging_details'])} surface-aging detail records,",
        f"{len(interior['joint_session'])} joint-session visual records,",
        f"{len(interior['seating'])} generic chamber seats/desks,",
        f"{len(gameplay['items'])} gameplay item props",
    )


if __name__ == "__main__":
    main()
