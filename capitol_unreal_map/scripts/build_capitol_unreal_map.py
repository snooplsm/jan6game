#!/usr/bin/env python3
"""Build a public-data U.S. Capitol map package for Unreal Engine.

The exterior is derived from OpenStreetMap geometry. The interior is a
public-only schematic based on public descriptions of major Capitol spaces; it
does not model restricted office assignments, service routes, or security
features.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source_data" / "capitol_osm_overpass_2026-07-04.json"
GENERATED = ROOT / "generated"
MESH_DIR = GENERATED / "meshes"
DATA_DIR = GENERATED / "data"

LAT0 = 38.889939
LON0 = -77.009051
EARTH_M_PER_DEG_LAT = 111_320.0
EARTH_M_PER_DEG_LON = 111_320.0 * math.cos(math.radians(LAT0))
OBJ_UNIT_SCALE = 100.0  # meters to Unreal centimeters
UV_TILE_METERS = 3.0


MATERIALS = {
    "BuildingGeneric": (0.72, 0.72, 0.70, 1.0),
    "BuildingCapitol": (0.90, 0.88, 0.82, 1.0),
    "CapitolStone": (0.86, 0.84, 0.78, 1.0),
    "CapitolDome": (0.82, 0.82, 0.78, 1.0),
    "ColumnStone": (0.90, 0.88, 0.82, 1.0),
    "StepStone": (0.62, 0.60, 0.56, 1.0),
    "GroundGrass": (0.16, 0.32, 0.12, 1.0),
    "PlazaStone": (0.58, 0.56, 0.50, 1.0),
    "RoadAsphalt": (0.045, 0.048, 0.052, 1.0),
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
        "label": "CapitolMap_Camera_Interior_Cutaway",
        "location_m": [0.0, -8.0, 120.0],
        "target_m": [0.0, 0.0, 5.2],
        "fov": 64.0,
        "category": "public_interior_cutaway",
        "viewer_note": "Hide exterior/landmark/roads/gameplay meshes for unobstructed public interior inspection.",
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


def parse_height(tags: dict[str, str], is_capitol: bool) -> float:
    if is_capitol:
        return 28.0
    height = tags.get("height") or tags.get("building:height")
    if height:
        match = re.search(r"([0-9]+(?:\.[0-9]+)?)", height)
        if match:
            value = float(match.group(1))
            if "ft" in height.lower() or "'" in height:
                value *= 0.3048
            return min(max(value, 3.0), 70.0)
    levels = tags.get("building:levels")
    if levels and levels.replace(".", "", 1).isdigit():
        return min(max(float(levels) * 3.4, 3.0), 70.0)
    return 11.0


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

        rows = max(1, min(3, int(height // 4.0)))
        cols_x = max(2, min(5, int(width // 7.0)))
        cols_y = max(2, min(5, int(depth // 7.0)))
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
            for col in range(cols_y):
                y = min_y + depth * (col + 0.5) / cols_y
                for face_name, x_face in (("east", max_x + 0.05), ("west", min_x - 0.05)):
                    window_name = f"{safe_prefix}_{face_name}_window_r{row+1:02d}_c{col+1:02d}"
                    buildings.add_box((x_face, y), (0.08, 1.12), 0.92, z, window_name, "FacadeWindow")
                    add_building_detail_record(window_name, "surrounding_building_facade_window", way_id, name, (x_face, y, z + 0.46), {"face": face_name})

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

        for unit_index, (ox, oy) in enumerate([(-0.18, -0.12), (0.20, 0.16)], start=1):
            unit_center = (cx + width * ox, cy + depth * oy)
            unit_size = (max(0.8, min(3.8, width * 0.22)), max(0.65, min(2.4, depth * 0.18)))
            unit_name = f"{safe_prefix}_rooftop_detail_{unit_index}"
            buildings.add_box(unit_center, unit_size, 0.55, height + 0.18, unit_name, "BuildingGeneric")
            add_building_detail_record(unit_name, "surrounding_building_rooftop_detail", way_id, name, (unit_center[0], unit_center[1], height + 0.46))

        for unit_index, (ox, oy) in enumerate([(0.10, -0.28), (-0.28, 0.22)], start=1):
            unit_center = (cx + width * ox, cy + depth * oy)
            unit_size = (max(0.72, min(2.7, width * 0.16)), max(0.58, min(1.85, depth * 0.14)))
            unit_name = f"{safe_prefix}_rooftop_mechanical_{unit_index}"
            buildings.add_box(unit_center, unit_size, 0.42, height + 0.76, unit_name, "DoorMetal")
            buildings.add_cylinder(unit_center, max(0.18, min(unit_size) * 0.24), height + 1.20, 0.055, f"{unit_name}_fan_cap", "FacadeWindow", segments=12)
            add_building_detail_record(
                unit_name,
                "surrounding_building_rooftop_mechanical",
                way_id,
                name,
                (unit_center[0], unit_center[1], height + 0.97),
            )

    def add_streetlight(name: str, point: tuple[float, float], side_sign: float) -> None:
        x, y = point
        lamp_x = x + side_sign * 0.62
        roads.add_cylinder((x, y), 0.075, 0.10, 5.1, f"{name}_pole", "StreetLightPole", segments=10)
        roads.add_box((x + side_sign * 0.30, y), (0.62, 0.10), 0.08, 5.05, f"{name}_arm", "StreetLightPole")
        roads.add_cylinder((lamp_x, y), 0.18, 4.62, 0.34, f"{name}_warm_glass", "StreetLightGlass", segments=12)
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
        add_streetscape_record(name, "street_name_sign", (x, y, 1.45), extra={"label": text[:80]})

    def add_traffic_signal(name: str, point: tuple[float, float]) -> None:
        x, y = point
        roads.add_cylinder((x, y), 0.07, 0.08, 4.05, f"{name}_pole", "StreetLightPole", segments=10)
        roads.add_box((x, y), (0.44, 0.28), 1.24, 3.05, f"{name}_signal_head", "TrafficSignalHousing")
        roads.add_box((x, y - 0.15), (0.20, 0.055), 0.18, 3.95, f"{name}_red_lens", "TrafficSignalRed")
        roads.add_box((x, y - 0.15), (0.20, 0.055), 0.18, 3.58, f"{name}_yellow_lens", "TrafficSignalYellow")
        roads.add_box((x, y - 0.15), (0.20, 0.055), 0.18, 3.21, f"{name}_green_lens", "TrafficSignalGreen")
        add_streetscape_record(name, "traffic_signal_prop", (x, y, 2.5))

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
        else:
            panel_size = (0.10, 3.2)
            roof_size = (1.2, 3.6)
            post_offsets = [(-0.42, -1.45), (-0.42, 1.45), (0.42, -1.45), (0.42, 1.45)]
        for idx, (dx, dy) in enumerate(post_offsets, start=1):
            roads.add_cylinder((x + dx, y + dy), 0.055, 0.10, 2.15, f"{name}_post_{idx:02d}", "StreetLightPole", segments=8)
        roads.add_box((x, y), panel_size, 1.28, 0.42, f"{name}_glass_back_panel", "DoorGlass")
        roads.add_box((x, y), roof_size, 0.10, 2.24, f"{name}_flat_roof", "DoorMetal")
        add_streetscape_record(name, "public_bus_stop_shelter", (x, y, 1.35), extra={"orientation": orientation})

    def add_public_hydrant(name: str, center: tuple[float, float]) -> None:
        x, y = center
        roads.add_cylinder((x, y), 0.18, 0.10, 0.62, f"{name}_barrel", "TrafficSignalRed", segments=12)
        roads.add_cylinder((x, y), 0.20, 0.72, 0.12, f"{name}_cap", "TrafficSignalYellow", segments=12)
        roads.add_box((x, y), (0.64, 0.12), 0.12, 0.46, f"{name}_side_nozzles", "TrafficSignalYellow")
        add_streetscape_record(name, "public_hydrant_marker", (x, y, 0.48))

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
            height = parse_height(tags, is_capitol)
            cx = sum(p[0] for p in points) / len(points)
            cy = sum(p[1] for p in points) / len(points)
            if is_us_capitol:
                metadata["replaced_buildings"].append(
                    {
                        "id": way["id"],
                        "name": name,
                        "center_m": [round(cx, 3), round(cy, 3), round(height / 2.0, 3)],
                        "reason": "Skipped concave OSM extrusion; replaced by authored Capitol landmark visual mesh.",
                        "tags": tags,
                    }
                )
            else:
                material = "BuildingCapitol" if is_capitol else "BuildingGeneric"
                buildings.add_extruded_polygon(points, 0.0, height, f"building_{name}_{way['id']}", material)
                add_surrounding_building_visuals(way["id"], name, points, height, (cx, cy))
                metadata["buildings"].append(
                    {
                        "id": way["id"],
                        "name": name,
                        "height_m": round(height, 2),
                        "center_m": [round(cx, 3), round(cy, 3), round(height / 2.0, 3)],
                        "tags": tags,
                    }
                )

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

    add_public_roadway_visual_details()
    add_capitol_grounds_details()

    buildings.write(MESH_DIR / "capitol_exterior_buildings.obj", "capitol_materials.mtl")
    roads.write(MESH_DIR / "capitol_exterior_roads_bike_lanes_markers.obj", "capitol_materials.mtl")
    return metadata


def build_capitol_landmark_details() -> dict[str, Any]:
    obj = ObjWriter("capitol_landmark_visual_details")
    labels: list[dict[str, Any]] = []
    elements: list[dict[str, Any]] = []
    facade_details: list[dict[str, Any]] = []

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

    def add_roof_cap(name: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        obj.add_box(center, size, 0.48, z, f"{name}_parapet_cap", "ColumnStone")
        obj.add_box(center, (size[0] * 0.92, size[1] * 0.92), 0.22, z + 0.48, f"{name}_slightly_recessed_roof", "CapitolDome")
        add_facade_detail(name, "roof_parapet_and_recessed_roof", (center[0], center[1], z + 0.48))

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

    def add_plaza_wear_patch(name: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        obj.add_box(center, size, 0.026, z, name, "StepStone")
        add_facade_detail(
            name,
            "plaza_wear_patch",
            (center[0], center[1], z + 0.013),
            {"size_m": [round(size[0], 3), round(size[1], 3)]},
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
        obj.add_ring(center, radius * 1.18, radius * 0.90, z_base + height - 0.32, 0.22, f"{prefix}_capital_torus", "ColumnStone", segments=24)
        obj.add_box(center, (radius * 2.65, radius * 2.65), 0.18, z_base + height - 0.02, f"{prefix}_square_abacus", "ColumnStone")

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
        obj.add_extruded_polygon(points, z, height, name, "ColumnStone")

    def add_dome_window_trim(index: int, angle: float, radius: float) -> None:
        add_radial_trim_bar(f"dome_drum_window_trim_{index:02d}_left_jamb", angle, radius, -0.45, 22.55, 1.62, 0.12, 0.28)
        add_radial_trim_bar(f"dome_drum_window_trim_{index:02d}_right_jamb", angle, radius, 0.45, 22.55, 1.62, 0.12, 0.28)
        add_radial_trim_bar(f"dome_drum_window_trim_{index:02d}_lintel", angle, radius, 0.0, 24.08, 0.14, 1.04, 0.30)
        add_radial_trim_bar(f"dome_drum_window_trim_{index:02d}_sill", angle, radius, 0.0, 22.40, 0.14, 0.98, 0.30)
        add_facade_detail(
            f"dome_drum_window_trim_{index:02d}",
            "dome_drum_window_trim",
            (radius * math.cos(angle), radius * math.sin(angle), 23.35),
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
            (radius * math.cos(angle), radius * math.sin(angle), z + panel_height / 2.0),
            {"angle_degrees": round(math.degrees(angle), 2), "size_m": [round(panel_width, 3), round(panel_height, 3)]},
        )

    def add_dome_drum_spandrel_panel(name: str, angle: float, z: float) -> None:
        radius = 18.18
        add_radial_trim_bar(f"{name}_stone_panel", angle, radius, 0.0, z, 0.34, 1.18, 0.24)
        add_facade_detail(
            name,
            "dome_drum_spandrel_panel",
            (radius * math.cos(angle), radius * math.sin(angle), z + 0.17),
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
            (radius * math.cos(angle), radius * math.sin(angle), 23.25),
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
            (mid_radius * math.cos(angle), mid_radius * math.sin(angle), 43.8),
            {"radial_index": index, "segments": len(segments_spec)},
        )

    def add_lantern_window_trim(index: int, angle: float) -> None:
        radius = 4.78
        add_radial_trim_bar(f"dome_lantern_window_trim_{index:02d}_left_jamb", angle, radius, -0.36, 56.02, 2.05, 0.075, 0.20)
        add_radial_trim_bar(f"dome_lantern_window_trim_{index:02d}_right_jamb", angle, radius, 0.36, 56.02, 2.05, 0.075, 0.20)
        add_radial_trim_bar(f"dome_lantern_window_trim_{index:02d}_lintel", angle, radius, 0.0, 58.10, 0.11, 0.82, 0.22)
        add_radial_trim_bar(f"dome_lantern_window_trim_{index:02d}_sill", angle, radius, 0.0, 55.86, 0.11, 0.78, 0.22)
        add_facade_detail(
            f"dome_lantern_window_trim_{index:02d}",
            "lantern_window_trim",
            (radius * math.cos(angle), radius * math.sin(angle), 57.08),
            {"radial_index": index},
        )

    def add_statue_of_freedom_silhouette() -> None:
        obj.add_cylinder((0.0, 0.0), 0.42, 66.12, 0.34, "statue_of_freedom_round_base", "StatueBronze", segments=16)
        obj.add_cylinder((0.0, 0.0), 0.24, 66.44, 1.20, "statue_of_freedom_body_silhouette", "StatueBronze", segments=12)
        obj.add_cylinder((0.0, 0.0), 0.16, 67.62, 0.22, "statue_of_freedom_head_silhouette", "StatueBronze", segments=12)
        obj.add_box((0.0, 0.0), (1.08, 0.11), 0.12, 67.22, "statue_of_freedom_arm_silhouette", "StatueBronze")
        obj.add_box((-0.38, 0.0), (0.12, 0.10), 0.88, 67.12, "statue_of_freedom_left_drape_silhouette", "StatueBronze")
        obj.add_box((0.38, 0.0), (0.12, 0.10), 0.88, 67.12, "statue_of_freedom_right_drape_silhouette", "StatueBronze")
        obj.add_cylinder((0.0, 0.0), 0.09, 67.83, 0.42, "statue_of_freedom_plume_silhouette", "StatueBronze", segments=10)
        add_facade_detail("statue_of_freedom_silhouette", "statue_of_freedom_silhouette", (0.0, 0.0, 67.20))

    def add_revolving_door(name: str, center: tuple[float, float], facade: str) -> None:
        x, y = center
        obj.add_cylinder((x, y), 1.18, 0.14, 2.65, f"{name}_glass_drum", "DoorGlass", segments=28)
        obj.add_cylinder((x, y), 0.10, 0.12, 2.85, f"{name}_center_post", "DoorMetal", segments=12)
        obj.add_box((x, y), (2.15, 0.08), 2.45, 0.22, f"{name}_revolving_panel_a", "DoorGlass")
        obj.add_box((x, y), (0.08, 2.15), 2.45, 0.22, f"{name}_revolving_panel_b", "DoorGlass")
        obj.add_box((x, y), (2.8, 2.8), 0.10, 0.08, f"{name}_threshold_plate", "DoorMetal")
        if facade in {"east", "west"}:
            obj.add_box((x, y), (0.42, 3.45), 3.05, 0.10, f"{name}_dark_recess", "DoorMetal")
        else:
            obj.add_box((x, y), (3.45, 0.42), 3.05, 0.10, f"{name}_dark_recess", "DoorMetal")
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

    obj.add_box((0.0, 0.0), (430.0, 360.0), 0.08, -0.06, "capitol_campus_ground_plane", "GroundGrass")
    obj.add_box((0.0, 0.0), (185.0, 165.0), 0.10, 0.0, "capitol_plaza_walkable_stone_plane", "PlazaStone")

    # Public visual massing: layered wings, pavilions, porticos, roof caps,
    # columns, dome, and lantern. Dimensions are approximate for visual
    # orientation rather than survey-grade modeling.
    obj.add_box((0.0, 0.0), (154.0, 188.0), 1.05, 0.08, "capitol_continuous_raised_plinth", "StepStone")
    obj.add_box((0.0, 0.0), (78.0, 58.0), 12.4, 1.13, "capitol_central_body_lower", "CapitolStone")
    obj.add_box((0.0, 0.0), (62.0, 44.0), 4.2, 13.53, "capitol_central_body_upper_setback", "CapitolStone")
    add_roof_cap("central_body_roof", (0.0, 0.0), (82.0, 62.0), 17.73)

    for wing_name, y, width, depth in (("senate_north_wing", 68.0, 82.0, 58.0), ("house_south_wing", -68.0, 90.0, 62.0)):
        obj.add_box((0.0, y), (width, depth), 10.9, 1.13, f"{wing_name}_main_block", "CapitolStone")
        obj.add_box((-34.0, y), (16.0, depth + 4.0), 13.2, 1.13, f"{wing_name}_west_end_pavilion", "CapitolStone")
        obj.add_box((34.0, y), (16.0, depth + 4.0), 13.2, 1.13, f"{wing_name}_east_end_pavilion", "CapitolStone")
        obj.add_box((0.0, y), (26.0, depth + 8.0), 12.4, 1.13, f"{wing_name}_center_pavilion", "CapitolStone")
        add_roof_cap(f"{wing_name}_main_roof", (0.0, y), (width + 2.0, depth + 2.0), 12.05)
        add_roof_cap(f"{wing_name}_center_pavilion_roof", (0.0, y), (28.0, depth + 10.0), 13.55)
        add_facade_detail(f"{wing_name}_articulated_pavilions", "wing_pavilion_massing", (0.0, y, 7.2))

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

    add_element("Articulated public roof silhouette and courtyard recesses", "landmark", (0.0, 0.0, 18.5))

    for side, x in (("east", 58.5), ("west", -58.5)):
        obj.add_box((x, 0.0), (17.0, 68.0), 13.7, 1.13, f"{side}_front_projecting_portico_block", "CapitolStone")
        obj.add_box((x, 0.0), (20.0, 72.0), 0.55, 14.83, f"{side}_front_entablature", "ColumnStone")
        obj.add_pediment((x + (2.2 if x > 0 else -2.2), 0.0), 56.0, 4.4, 15.38, 4.2, f"{side}_front_triangular_pediment", "ColumnStone", "east_west")
        obj.add_box((x + (2.7 if x > 0 else -2.7), 0.0), (0.18, 12.0), 0.42, 16.25, f"{side}_front_pediment_public_relief_panel", "ColumnStone")
        add_roof_cap(f"{side}_front_portico_roof", (x, 0.0), (20.5, 70.0), 13.95)
        add_facade_detail(f"{side}_front_triangular_pediment", "classical_pediment", (x, 0.0, 17.1))
        add_facade_detail(f"{side}_front_pediment_public_relief_panel", "pediment_relief_panel", (x, 0.0, 16.46))

    for side, y in (("north", 99.0), ("south", -99.0)):
        obj.add_box((0.0, y), (50.0, 13.0), 11.8, 1.13, f"{side}_wing_public_portico_block", "CapitolStone")
        obj.add_box((0.0, y), (54.0, 15.5), 0.48, 13.15, f"{side}_wing_entablature", "ColumnStone")
        obj.add_pediment((0.0, y + (2.0 if y > 0 else -2.0)), 44.0, 4.0, 13.63, 3.3, f"{side}_wing_triangular_pediment", "ColumnStone", "north_south")
        obj.add_box((0.0, y + (2.4 if y > 0 else -2.4)), (10.0, 0.18), 0.38, 14.52, f"{side}_wing_pediment_public_relief_panel", "ColumnStone")
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

    # Facade rhythm: public visual windows, belt courses, and cornice bands.
    y_window_positions = [value * 5.0 for value in range(-6, 7)]
    wing_x_window_positions = [value * 5.6 for value in range(-7, 8)]
    add_facade_window_grid("east_front", "east_west", 63.2, y_window_positions, [3.8, 7.2, 10.6, 14.0])
    add_facade_window_grid("west_front", "east_west", -63.2, y_window_positions, [3.8, 7.2, 10.6, 14.0])
    add_facade_window_grid("senate_north_wing", "north_south", 97.2, wing_x_window_positions, [3.7, 7.1, 10.5])
    add_facade_window_grid("house_south_wing", "north_south", -97.2, wing_x_window_positions, [3.7, 7.1, 10.5])
    add_window_grid_on_face("east_front_deep_shadow", "east_west", 67.3, [-27, -18, -9, 9, 18, 27], [5.1, 8.5, 11.9], width=1.05)
    add_window_grid_on_face("west_front_deep_shadow", "east_west", -67.3, [-27, -18, -9, 9, 18, 27], [5.1, 8.5, 11.9], width=1.05)
    add_window_grid_on_face("north_portico_shadow", "north_south", 101.8, [-20, -12, -4, 4, 12, 20], [4.9, 8.3, 11.2], width=0.9)
    add_window_grid_on_face("south_portico_shadow", "north_south", -101.8, [-20, -12, -4, 4, 12, 20], [4.9, 8.3, 11.2], width=0.9)

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
        for idx, y in enumerate([-24.0, -16.0, -8.0, 0.0, 8.0, 16.0, 24.0], start=1):
            column_center = (x * 0.92, y)
            column_name = f"{side}_portico_column_{idx}"
            obj.add_cylinder(column_center, 0.62, 0.2, 13.5, column_name, "ColumnStone", segments=20)
            add_exterior_column_ornament(column_name, column_center, 0.62, 0.2, 13.5, "east_west")
            add_facade_detail(column_name, "exterior_column", (column_center[0], column_center[1], 6.95))
        add_element(f"{side.title()} front steps and colonnade", "landmark", (x, 0.0, 3.0))
        for door_index, y in enumerate([-9.0, 0.0, 9.0], start=1):
            add_revolving_door(f"{side}_front_{door_index}", (x * 0.86, y), side)
        for lamp_index, y in enumerate([-18.0, -6.0, 6.0, 18.0], start=1):
            add_public_entry_lamp(f"{side}_front_lamp_{lamp_index}", (x * 0.92, y))
        add_approach_handrails(f"{side}_front_approach_handrail", "east_west", (x * 0.98, 0.0), 12.5, (-35.5, 35.5))

    for side, y in (("north", 99.0), ("south", -99.0)):
        add_column_row(f"{side}_wing_portico", "north_south", y * 0.98, [-19.0, -12.5, -6.0, 0.0, 6.0, 12.5, 19.0], 1.3, 10.9)
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
        for door_index, x in enumerate([-8.0, 0.0, 8.0], start=1):
            add_revolving_door(f"{side}_wing_{door_index}", (x, y), side)
        for lamp_index, x in enumerate([-18.0, -6.0, 6.0, 18.0], start=1):
            add_public_entry_lamp(f"{side}_wing_lamp_{lamp_index}", (x, y * 0.95))
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

    obj.add_cylinder((0.0, 0.0), 20.5, 17.9, 1.2, "dome_base_octagonal_plinth", "ColumnStone", segments=32)
    obj.add_cylinder((0.0, 0.0), 18.0, 18.0, 16.0, "dome_drum_cylinder", "CapitolDome", segments=96)
    obj.add_ring((0.0, 0.0), 18.4, 17.8, 20.6, 0.55, "dome_lower_balustrade_ring", "ColumnStone", segments=96)
    obj.add_ring((0.0, 0.0), 16.2, 15.7, 30.8, 0.45, "dome_upper_balustrade_ring", "ColumnStone", segments=96)
    for idx in range(48):
        angle = math.tau * idx / 48.0
        obj.add_cylinder((18.1 * math.cos(angle), 18.1 * math.sin(angle)), 0.11, 20.72, 0.78, f"dome_lower_balustrade_post_{idx+1:02d}", "ColumnStone", segments=8)
        obj.add_cylinder((15.95 * math.cos(angle), 15.95 * math.sin(angle)), 0.09, 30.92, 0.64, f"dome_upper_balustrade_post_{idx+1:02d}", "ColumnStone", segments=8)
    add_facade_detail("dome_lower_balustrade_posts", "dome_balustrade_posts", (0.0, 0.0, 21.1), {"count": 48})
    add_facade_detail("dome_upper_balustrade_posts", "dome_balustrade_posts", (0.0, 0.0, 31.24), {"count": 48})
    for idx in range(32):
        angle = math.tau * idx / 32.0
        px = 18.1 * math.cos(angle)
        py = 18.1 * math.sin(angle)
        obj.add_cylinder((px, py), 0.18, 19.0, 10.4, f"dome_drum_pilaster_{idx+1:02d}", "ColumnStone", segments=10)
        add_dome_drum_arcade_bay(idx + 1, angle)
        if idx % 2 == 0:
            wx = 17.85 * math.cos(angle)
            wy = 17.85 * math.sin(angle)
            add_dome_window_trim(idx // 2 + 1, angle, 18.02)
            obj.add_cylinder((wx, wy), 0.30, 22.8, 1.25, f"dome_drum_dark_window_{idx//2+1:02d}", "FacadeWindow", segments=10)
            add_dome_drum_spandrel_panel(f"dome_drum_spandrel_panel_{idx//2+1:02d}", angle, 25.25)
    for idx in range(24):
        angle = math.tau * idx / 24.0
        px = 12.2 * math.cos(angle)
        py = 12.2 * math.sin(angle)
        obj.add_cylinder((px, py), 0.10, 34.5, 16.5, f"dome_vertical_rib_{idx+1:02d}", "ColumnStone", segments=8)
        add_dome_curved_rib(idx + 1, angle)
        add_facade_detail(
            f"dome_vertical_rib_{idx+1:02d}",
            "dome_vertical_rib",
            (px, py, 42.75),
            {"radial_index": idx + 1},
        )
    for band_index, (outer_radius, inner_radius, z) in enumerate(
        [(18.0, 17.70, 37.8), (16.9, 16.55, 42.6), (14.55, 14.20, 47.4), (11.50, 11.18, 51.2)],
        start=1,
    ):
        obj.add_ring((0.0, 0.0), outer_radius, inner_radius, z, 0.16, f"dome_lateral_stone_band_{band_index}", "ColumnStone", segments=96)
        add_facade_detail(
            f"dome_lateral_stone_band_{band_index}",
            "dome_lateral_band",
            (0.0, 0.0, z + 0.08),
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
    obj.add_dome((0.0, 0.0), 18.0, 34.0, 22.0, "capitol_dome_approximate_shell", "CapitolDome", segments=72, rings=10)
    obj.add_cylinder((0.0, 0.0), 4.2, 55.5, 5.2, "dome_lantern_cylinder", "ColumnStone", segments=32)
    for idx in range(16):
        angle = math.tau * idx / 16.0
        obj.add_cylinder((4.45 * math.cos(angle), 4.45 * math.sin(angle)), 0.10, 55.55, 4.48, f"dome_lantern_column_{idx+1:02d}", "ColumnStone", segments=10)
        obj.add_cylinder((4.58 * math.cos(angle), 4.58 * math.sin(angle)), 0.055, 59.88, 0.70, f"dome_lantern_balustrade_post_{idx+1:02d}", "ColumnStone", segments=8)
        add_facade_detail(
            f"dome_lantern_column_{idx+1:02d}",
            "lantern_column",
            (4.45 * math.cos(angle), 4.45 * math.sin(angle), 57.79),
            {"radial_index": idx + 1},
        )
    obj.add_ring((0.0, 0.0), 4.72, 4.44, 60.45, 0.16, "dome_lantern_balustrade_ring", "ColumnStone", segments=64)
    add_facade_detail("dome_lantern_balustrade", "lantern_balustrade", (0.0, 0.0, 60.28), {"count": 16})
    for idx in range(8):
        angle = math.tau * idx / 8.0
        obj.add_cylinder((4.28 * math.cos(angle), 4.28 * math.sin(angle)), 0.16, 56.25, 1.7, f"dome_lantern_dark_window_{idx+1:02d}", "FacadeWindow", segments=8)
        add_lantern_window_trim(idx + 1, angle)
    add_facade_detail("dome_lantern_dark_window_ring", "lantern_window", (0.0, 0.0, 57.1), {"count": 8})
    obj.add_dome((0.0, 0.0), 4.2, 60.2, 4.0, "dome_lantern_cap", "CapitolDome", segments=32, rings=5)
    obj.add_cylinder((0.0, 0.0), 0.18, 64.0, 2.1, "dome_lantern_finial", "ColumnStone", segments=12)
    add_statue_of_freedom_silhouette()
    add_facade_detail("dome_lantern_finial", "dome_finial", (0.0, 0.0, 65.05))
    add_element("Capitol Dome / lantern visual massing", "landmark", (0.0, 0.0, 49.0))

    obj.write(MESH_DIR / "capitol_landmark_visual_details.obj", "capitol_materials.mtl")
    return {"elements": elements, "labels": labels, "facade_details": facade_details}


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
        add_office_detail(table_name, "shared_support_table", (table_center[0], table_center[1], z + 0.36), (cell_w * 0.62, 0.92))

    for row in range(rows):
        for col in range(columns):
            ox = cx - sx / 2.0 + cell_w * (col + 0.5)
            oy = cy - sy / 2.0 + cell_h * (row + 0.5)
            room_id = f"{prefix}_generic_office_{row+1}_{col+1}"
            obj.add_box((ox, oy), (cell_w * 0.82, cell_h * 0.72), 0.16, z, room_id + "_floor", "OfficeZone")
            obj.add_box((ox, oy + cell_h * 0.36), (cell_w * 0.80, 0.18), 2.2, z + 0.16, room_id + "_back_partition", "InteriorTrim")
            obj.add_box((ox - cell_w * 0.40, oy), (0.18, cell_h * 0.68), 2.2, z + 0.16, room_id + "_left_partition", "InteriorTrim")
            obj.add_box((ox + cell_w * 0.40, oy), (0.18, cell_h * 0.68), 2.2, z + 0.16, room_id + "_right_partition", "InteriorTrim")
            obj.add_box((ox, oy - cell_h * 0.10), (cell_w * 0.40, 0.70), 0.78, z + 0.18, room_id + "_desk", "DeskWood")
            obj.add_box((ox, oy - cell_h * 0.10), (cell_w * 0.28, 0.46), 0.030, z + 0.97, room_id + "_desk_surface_inset", "InteriorTrim")
            obj.add_box((ox, oy - cell_h * 0.28), (0.70, 0.55), 0.55, z + 0.18, room_id + "_chair", "ChairLeather")
            obj.add_box((ox, oy - cell_h * 0.36), (0.74, 0.10), 0.72, z + 0.52, room_id + "_chair_back", "ChairLeather")
            obj.add_box((ox - 0.44, oy - cell_h * 0.28), (0.055, 0.42), 0.18, z + 0.54, room_id + "_chair_left_arm", "ChairLeather")
            obj.add_box((ox + 0.44, oy - cell_h * 0.28), (0.055, 0.42), 0.18, z + 0.54, room_id + "_chair_right_arm", "ChairLeather")
            bookcase_x = ox - cell_w * 0.27
            obj.add_box((bookcase_x, oy + cell_h * 0.22), (0.58, 1.55), 1.35, z + 0.20, room_id + "_bookcase_body", "DeskWood")
            for shelf_index, shelf_y in enumerate([-0.46, 0.0, 0.46], start=1):
                obj.add_box((bookcase_x, oy + cell_h * 0.22 + shelf_y), (0.62, 0.045), 0.055, z + 0.76 + shelf_index * 0.25, f"{room_id}_bookcase_shelf_{shelf_index}", "InteriorTrim")
            cabinet_x = ox + cell_w * 0.27
            obj.add_box((cabinet_x, oy + cell_h * 0.18), (0.72, 1.10), 0.78, z + 0.18, room_id + "_storage_cabinet", "InteriorTrim")
            obj.add_box((cabinet_x, oy + cell_h * 0.18), (0.78, 0.055), 0.08, z + 0.98, room_id + "_storage_cabinet_top", "DeskWood")
            door_y = oy - cell_h * 0.36
            obj.add_box((ox, door_y), (cell_w * 0.36, 0.08), 0.06, z + 0.03, room_id + "_public_door_threshold", "StepStone")
            obj.add_box((ox, door_y + 0.05), (cell_w * 0.26, 0.10), 1.62, z + 0.22, room_id + "_generic_door_panel", "DoorGlass")
            plaque_x = ox - cell_w * 0.24
            obj.add_box((plaque_x, door_y + 0.10), (0.34, 0.055), 0.22, z + 1.38, room_id + "_generic_public_plaque", "MarkerBlue")
            add_office_detail(room_id + "_desk_surface_inset", "generic_office_desk_surface_inset", (ox, oy - cell_h * 0.10, z + 0.985), (cell_w * 0.28, 0.46))
            add_office_detail(room_id + "_chair_back", "generic_office_chair_back", (ox, oy - cell_h * 0.36, z + 0.88), (0.74, 0.10))
            add_office_detail(room_id + "_chair_arm_pair", "generic_office_chair_arm_pair", (ox, oy - cell_h * 0.28, z + 0.63), (0.94, 0.42))
            add_office_detail(room_id + "_bookcase", "generic_office_bookcase", (bookcase_x, oy + cell_h * 0.22, z + 0.875), (0.62, 1.55))
            add_office_detail(room_id + "_storage_cabinet", "generic_office_storage_cabinet", (cabinet_x, oy + cell_h * 0.18, z + 0.57), (0.78, 1.10))
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

    for idx in range(32):
        angle = math.tau * idx / 32.0 + math.pi / 32.0
        x = 14.72 * math.cos(angle)
        y = 14.72 * math.sin(angle)
        name = f"rotunda_upper_coffer_panel_{idx+1:02d}"
        obj.add_cylinder((x, y), 0.24, 7.55, 0.10, name, "ArtFrameGold", segments=12)
        add_rotunda_detail(name, "upper_coffer_panel", (x, y, 7.6), (0.48, 0.48))

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
            size = (6.75, 0.72)
        else:
            obj.add_box((cx, cy - 3.15), (0.72, 0.46), 3.35, 4.48, f"{name}_left_post", "InteriorTrim")
            obj.add_box((cx, cy + 3.15), (0.72, 0.46), 3.35, 4.48, f"{name}_right_post", "InteriorTrim")
            obj.add_box((cx, cy), (0.72, 6.75), 0.55, 7.62, f"{name}_lintel", "InteriorTrim")
            obj.add_box((cx - sign * 0.18, cy), (0.16, 5.65), 0.42, 7.12, f"{name}_inner_shadow_line", "BrassRail")
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
    obj.add_cylinder((x, y), 0.62, z, 0.34, f"{name}_plinth", "StepStone", segments=18)
    obj.add_cylinder((x, y), 0.34, z + 0.34, 1.28, f"{name}_body", material, segments=18)
    obj.add_cylinder((x, y), 0.20, z + 1.62, 0.28, f"{name}_head", material, segments=18)
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
) -> None:
    x, y = center
    width, height = size
    if facing_axis == "x":
        obj.add_box((x, y), (0.16, width + 0.34), height + 0.34, z - height / 2.0, f"{name}_frame", "ArtFrameGold")
        obj.add_box((x, y), (0.18, width), height, z - height / 2.0 + 0.08, f"{name}_canvas", material)
    else:
        obj.add_box((x, y), (width + 0.34, 0.16), height + 0.34, z - height / 2.0, f"{name}_frame", "ArtFrameGold")
        obj.add_box((x, y), (width, 0.18), height, z - height / 2.0 + 0.08, f"{name}_canvas", material)
    records.append(
        {
            "name": name,
            "type": art_type,
            "location": location,
            "center_m": [round(x, 3), round(y, 3), round(z, 3)],
            "size_m": [round(width, 3), round(height, 3)],
            "public_accuracy": public_accuracy,
            "assignment": "Schematic public-art panel, not an exact artwork inventory record.",
        }
    )


def add_light_fixture(
    obj: ObjWriter,
    fixtures: list[dict[str, Any]],
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
        obj.add_cylinder((x, y), 0.48, z - 0.16, 0.18, f"{name}_metal_ring", "LightFixtureMetal", segments=24)
        for idx in range(6):
            angle = math.tau * idx / 6.0
            px = x + 0.42 * math.cos(angle)
            py = y + 0.42 * math.sin(angle)
            obj.add_cylinder((px, py), 0.10, z - 0.55, 0.32, f"{name}_glass_bulb_{idx+1}", "WarmLightGlass", segments=12)
    elif fixture_type == "sconce":
        obj.add_box((x, y), (0.35, 0.12), 0.55, z - 0.28, f"{name}_sconce_backplate", "LightFixtureMetal")
        obj.add_cylinder((x, y), 0.13, z - 0.12, 0.32, f"{name}_sconce_glass", "WarmLightGlass", segments=12)
    else:
        obj.add_cylinder((x, y), 0.26, z - 0.22, 0.32, f"{name}_pendant_glass", "WarmLightGlass", segments=16)
        obj.add_cylinder((x, y), 0.07, z + 0.10, 0.42, f"{name}_pendant_stem", "LightFixtureMetal", segments=10)
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
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    art: list[dict[str, Any]] = []
    lights: list[dict[str, Any]] = []

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

    # Rotunda wall paintings are represented as public historical painting
    # panels without exact painting-by-painting placement.
    for idx in range(8):
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
    add_light_fixture(obj, lights, "rotunda_center_chandelier", "chandelier", "Rotunda", (0.0, 0.0), 9.1, 2600.0, 16.0)
    for idx in range(8):
        angle = math.tau * idx / 8.0
        add_light_fixture(
            obj,
            lights,
            f"rotunda_perimeter_sconce_{idx+1:02d}",
            "sconce",
            "Rotunda",
            (13.2 * math.cos(angle), 13.2 * math.sin(angle)),
            7.4,
            650.0,
            7.0,
        )

    for idx, x in enumerate([-20.0, -10.0, 0.0, 10.0, 20.0], start=1):
        add_light_fixture(obj, lights, f"house_chamber_pendant_{idx:02d}", "pendant", "House Chamber", (x, -72.0), 8.2, 900.0, 9.0)
        add_light_fixture(obj, lights, f"senate_chamber_pendant_{idx:02d}", "pendant", "Senate Chamber", (x * 0.75, 68.0), 8.2, 850.0, 8.0)

    for idx, y in enumerate([-87.0, -80.5, -74.0, -67.5, -61.0], start=1):
        add_light_fixture(obj, lights, f"house_west_wall_sconce_{idx:02d}", "sconce", "House Chamber", (-30.2, y), 7.0, 560.0, 6.8)
        add_light_fixture(obj, lights, f"house_east_wall_sconce_{idx:02d}", "sconce", "House Chamber", (30.2, y), 7.0, 560.0, 6.8)

    for idx, y in enumerate([58.0, 64.5, 71.0, 77.5], start=1):
        add_light_fixture(obj, lights, f"senate_west_wall_sconce_{idx:02d}", "sconce", "Senate Chamber", (-23.2, y), 7.0, 540.0, 6.4)
        add_light_fixture(obj, lights, f"senate_east_wall_sconce_{idx:02d}", "sconce", "Senate Chamber", (23.2, y), 7.0, 540.0, 6.4)

    for idx, x in enumerate([-24.0, -8.0, 8.0, 24.0], start=1):
        add_light_fixture(obj, lights, f"house_gallery_sconce_{idx:02d}", "sconce", "House galleries", (x, -100.9), 6.85, 440.0, 5.4)
        add_light_fixture(obj, lights, f"senate_gallery_sconce_{idx:02d}", "sconce", "Senate galleries", (x * 0.78, 98.8), 6.85, 420.0, 5.2)

    for idx, x in enumerate([20.0, 28.0, 36.0], start=1):
        add_light_fixture(obj, lights, f"statuary_hall_pendant_{idx:02d}", "pendant", "National Statuary Hall", (x, -30.0), 7.8, 720.0, 7.0)
        add_light_fixture(obj, lights, f"old_senate_chamber_pendant_{idx:02d}", "pendant", "Old Senate Chamber", (x, 30.0), 7.8, 680.0, 6.5)

    for idx, (x, y) in enumerate([(-53.0, -55.0), (53.0, -55.0), (-52.0, 55.0), (52.0, 55.0)], start=1):
        add_light_fixture(obj, lights, f"generic_office_zone_light_{idx:02d}", "pendant", "Generic office/support zone", (x, y), 7.2, 550.0, 6.0)

    add_label(labels, "Warm public lighting fixtures - schematic", 0.0, 6.5, 9.7, "lighting")
    return art, lights


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

    def add_baseboard(name: str, room: str, center: tuple[float, float], size: tuple[float, float]) -> None:
        obj.add_box(center, size, 0.18, baseboard_z, f"{name}_baseboard", "InteriorTrim")
        add_wall_finish_detail_record(records, name, "baseboard", room, (center[0], center[1], baseboard_z + 0.09), size)

    def add_pilaster(name: str, room: str, center: tuple[float, float], size: tuple[float, float]) -> None:
        obj.add_box(center, size, 2.35, pilaster_z, f"{name}_shaft", "InteriorTrim")
        obj.add_box(center, (size[0] * 1.45, size[1] * 1.45), 0.18, pilaster_z + 2.32, f"{name}_cap", "ArtFrameGold")
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
            obj.add_box((x, y), top_size, 0.065, bottom_z, f"{name}_bottom_rail", material)
            obj.add_box((x, y), top_size, 0.065, bottom_z + height, f"{name}_top_rail", material)
            obj.add_box((x - width / 2.0, y), side_size, height, bottom_z, f"{name}_left_stile", material)
            obj.add_box((x + width / 2.0, y), side_size, height, bottom_z, f"{name}_right_stile", material)
            size = (width, wall_depth)
        else:
            top_size = (wall_depth, width)
            side_size = (wall_depth, thickness)
            obj.add_box((x, y), top_size, 0.065, bottom_z, f"{name}_bottom_rail", material)
            obj.add_box((x, y), top_size, 0.065, bottom_z + height, f"{name}_top_rail", material)
            obj.add_box((x, y - width / 2.0), side_size, height, bottom_z, f"{name}_left_stile", material)
            obj.add_box((x, y + width / 2.0), side_size, height, bottom_z, f"{name}_right_stile", material)
            size = (wall_depth, width)
        add_wall_finish_detail_record(records, name, kind, room, (x, y, bottom_z + height / 2.0), size)

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

        for index in range(panel_count_long):
            x = cx - sx / 2.0 + sx * (index + 0.5) / panel_count_long
            width = sx / panel_count_long * 0.64
            add_frame(f"{name}_north_wainscot_frame_{index+1:02d}", room, (x, north_y), width, "east_west", "raised_wainscot_frame", panel_bottom_z, panel_height, "InteriorTrim")
            add_frame(f"{name}_south_wainscot_frame_{index+1:02d}", room, (x, south_y), width, "east_west", "raised_wainscot_frame", panel_bottom_z, panel_height, "InteriorTrim")
            if index % 2 == 0:
                upper_width = sx / panel_count_long * 0.72
                add_frame(f"{name}_north_upper_wall_frame_{index+1:02d}", room, (x, north_y), upper_width, "east_west", "upper_wall_panel_frame", upper_z, 0.72, "ArtFrameGold")
                add_frame(f"{name}_south_upper_wall_frame_{index+1:02d}", room, (x, south_y), upper_width, "east_west", "upper_wall_panel_frame", upper_z, 0.72, "ArtFrameGold")
        for index in range(panel_count_short):
            y = cy - sy / 2.0 + sy * (index + 0.5) / panel_count_short
            width = sy / panel_count_short * 0.64
            add_frame(f"{name}_east_wainscot_frame_{index+1:02d}", room, (east_x, y), width, "north_south", "raised_wainscot_frame", panel_bottom_z, panel_height, "InteriorTrim")
            add_frame(f"{name}_west_wainscot_frame_{index+1:02d}", room, (west_x, y), width, "north_south", "raised_wainscot_frame", panel_bottom_z, panel_height, "InteriorTrim")
            if index % 2 == 0:
                upper_width = sy / panel_count_short * 0.70
                add_frame(f"{name}_east_upper_wall_frame_{index+1:02d}", room, (east_x, y), upper_width, "north_south", "upper_wall_panel_frame", upper_z, 0.68, "ArtFrameGold")
                add_frame(f"{name}_west_upper_wall_frame_{index+1:02d}", room, (west_x, y), upper_width, "north_south", "upper_wall_panel_frame", upper_z, 0.68, "ArtFrameGold")

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

    add_label(labels, "Raised wall panels, pilasters, and baseboards - schematic", -23.0, -7.5, 7.7, "wall_finish_detail")


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
        obj.add_box(detail_center, detail_size, crown_height, z, detail_name, "ArtFrameGold")
        add_interior_ceiling_detail_record(
            records,
            detail_name,
            "crown_molding",
            room,
            (detail_center[0], detail_center[1], z + crown_height / 2.0),
            detail_size,
        )

    for col in range(1, columns):
        x = cx - sx / 2.0 + sx * col / columns
        detail_name = f"{name}_vertical_ceiling_beam_{col:02d}"
        obj.add_box((x, cy), (beam_width, sy * 0.94), beam_height, z + 0.02, detail_name, "InteriorTrim")
        add_interior_ceiling_detail_record(records, detail_name, "ceiling_grid_beam", room, (x, cy, z + 0.08), (beam_width, sy * 0.94))
    for row in range(1, rows):
        y = cy - sy / 2.0 + sy * row / rows
        detail_name = f"{name}_horizontal_ceiling_beam_{row:02d}"
        obj.add_box((cx, y), (sx * 0.94, beam_width), beam_height, z + 0.02, detail_name, "InteriorTrim")
        add_interior_ceiling_detail_record(records, detail_name, "ceiling_grid_beam", room, (cx, y, z + 0.08), (sx * 0.94, beam_width))

    cell_w = sx / columns
    cell_h = sy / rows
    for row in range(rows):
        for col in range(columns):
            px = cx - sx / 2.0 + cell_w * (col + 0.5)
            py = cy - sy / 2.0 + cell_h * (row + 0.5)
            detail_name = f"{name}_coffer_panel_r{row+1:02d}_c{col+1:02d}"
            panel_size = (cell_w * 0.70, cell_h * 0.66)
            obj.add_box((px, py), panel_size, 0.035, z + 0.10, detail_name, "RotundaWall")
            add_interior_ceiling_detail_record(records, detail_name, "coffer_panel", room, (px, py, z + 0.118), panel_size)

    for index, (ox, oy) in enumerate(medallion_offsets, start=1):
        x = cx + sx * ox
        y = cy + sy * oy
        medallion_name = f"{name}_ceiling_medallion_{index:02d}"
        canopy_name = f"{name}_light_canopy_{index:02d}"
        obj.add_cylinder((x, y), 0.52, z + 0.16, 0.06, medallion_name, "ArtFrameGold", segments=24)
        obj.add_cylinder((x, y), 0.22, z + 0.22, 0.08, canopy_name, "LightFixtureMetal", segments=18)
        add_interior_ceiling_detail_record(records, medallion_name, "ceiling_medallion", room, (x, y, z + 0.19), (1.04, 1.04))
        add_interior_ceiling_detail_record(records, canopy_name, "light_canopy", room, (x, y, z + 0.26), (0.44, 0.44))


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


def add_public_interior_floor_details(
    obj: ObjWriter,
    labels: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> None:
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

    carpet_specs = [
        ("house_chamber_carpet_border", "House Chamber", (0.0, -80.0), (55.5, 30.5), 4.57, "HouseCarpet"),
        ("senate_chamber_carpet_border", "Senate Chamber", (0.0, 73.0), (42.5, 26.5), 4.57, "SenateCarpet"),
        ("house_gallery_carpet_border", "House galleries", (0.0, -100.0), (66.5, 7.6), 4.92, "HouseCarpet"),
        ("senate_gallery_carpet_border", "Senate galleries", (0.0, 97.5), (52.5, 6.8), 4.92, "SenateCarpet"),
    ]
    for name, area, center, size, z, material in carpet_specs:
        add_floor_border(obj, records, name, area, center, size, z, "carpet_border_strip", material, thickness=0.22)

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

    add_label(labels, "Public floor borders, thresholds, and marble tile joints - schematic", 18.0, 0.0, 5.2, "public_circulation_detail")


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
        add_chamber_detail_record(records, name, "rostrum_desk", chamber, (center[0], center[1], z + 0.21), size)

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
            obj.add_box((center[0], center[1] + size[1] * 0.38), (size[0], 0.12), 0.55, z + 0.14, f"{name}_back", "ChairLeather")
        else:
            obj.add_box((center[0] + size[0] * 0.38, center[1]), (0.12, size[1]), 0.55, z + 0.14, f"{name}_back", "ChairLeather")
        add_chamber_detail_record(records, name, "gallery_bench", chamber, (center[0], center[1], z + 0.16), size)

    def flag_standard(name: str, chamber: str, x: float, y: float, z: float, flag_material: str) -> None:
        obj.add_cylinder((x, y), 0.055, z, 2.3, f"{name}_pole", "BrassRail", segments=10)
        obj.add_cylinder((x, y), 0.15, z + 2.3, 0.18, f"{name}_finial", "BrassRail", segments=12)
        obj.add_box((x + 0.28, y), (0.55, 0.08), 0.68, z + 1.35, f"{name}_cloth_panel", flag_material)
        add_chamber_detail_record(records, name, "flag_standard", chamber, (x, y, z + 1.15), (0.7, 0.18))

    def public_lectern(name: str, chamber: str, center: tuple[float, float], z: float) -> None:
        x, y = center
        obj.add_box((x, y), (0.78, 0.46), 0.82, z, f"{name}_base", "DeskWood")
        obj.add_box((x, y + 0.03), (0.92, 0.54), 0.12, z + 0.82, f"{name}_sloped_top", "InteriorTrim")
        obj.add_box((x, y - 0.32), (0.18, 0.12), 0.22, z + 0.92, f"{name}_microphone_marker", "DoorMetal")
        add_chamber_detail_record(records, name, "public_lectern", chamber, (x, y, z + 0.58), (0.92, 0.54))

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
        add_chamber_detail_record(records, name, "public_work_table", chamber, (x, y, z + 0.13), size)

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

    # House chamber public visual details.
    rail("house_rostrum_front_brass_rail", "House Chamber", (0.0, -50.75), (14.6, 0.16), 5.42)
    rail("house_rostrum_left_brass_rail", "House Chamber", (-7.25, -48.7), (0.16, 4.1), 5.42)
    rail("house_rostrum_right_brass_rail", "House Chamber", (7.25, -48.7), (0.16, 4.1), 5.42)
    for idx, y in enumerate([-51.55, -52.05, -52.55], start=1):
        step(f"house_rostrum_step_tread_{idx}", "House Chamber", (0.0, y), (15.6 - idx * 0.8, 0.32), 4.58 + idx * 0.08)
    for idx, x in enumerate([-5.0, -3.0, -1.0, 1.0, 3.0, 5.0], start=1):
        backdrop_panel(f"house_rostrum_backdrop_panel_{idx}", "House Chamber", (x, -46.45), (1.35, 0.12), 5.05)
    gallery_rail("house_gallery_front_brass_rail", "House Chamber", (0.0, -95.15), (66.0, 0.16), 5.24)
    gallery_rail("house_gallery_rear_brass_rail", "House Chamber", (0.0, -103.7), (66.0, 0.16), 5.54)
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

    # Senate chamber public visual details.
    rail("senate_presiding_front_brass_rail", "Senate Chamber", (0.0, 81.85), (12.0, 0.16), 5.36)
    rail("senate_presiding_left_brass_rail", "Senate Chamber", (-6.0, 83.25), (0.16, 2.8), 5.36)
    rail("senate_presiding_right_brass_rail", "Senate Chamber", (6.0, 83.25), (0.16, 2.8), 5.36)
    for idx, y in enumerate([81.0, 80.55], start=1):
        step(f"senate_presiding_step_tread_{idx}", "Senate Chamber", (0.0, y), (12.6 - idx * 0.6, 0.30), 4.58 + idx * 0.08)
    for idx, x in enumerate([-4.2, -2.1, 0.0, 2.1, 4.2], start=1):
        backdrop_panel(f"senate_presiding_backdrop_panel_{idx}", "Senate Chamber", (x, 85.15), (1.35, 0.12), 5.02)
    gallery_rail("senate_gallery_front_brass_rail", "Senate Chamber", (0.0, 94.05), (52.0, 0.16), 5.22)
    gallery_rail("senate_gallery_rear_brass_rail", "Senate Chamber", (0.0, 101.2), (52.0, 0.16), 5.52)
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

    add_label(labels, "House and Senate chamber rails, dais steps, flags, and aisle trim - schematic", 0.0, -43.0, 7.7, "chamber_detail")


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
            post_offsets = [(0.0, -width / 2.0), (0.0, width / 2.0)]
        else:
            post_size = (0.24, 0.16)
            lintel_size = (width + 0.50, 0.20)
            transom_size = (width * 0.64, 0.075)
            post_offsets = [(-width / 2.0, 0.0), (width / 2.0, 0.0)]
        for idx, (dx, dy) in enumerate(post_offsets, start=1):
            obj.add_box((x + dx, y + dy), post_size, 2.35, 4.43, f"{name}_side_trim_{idx}", "InteriorTrim")
        obj.add_box((x, y), lintel_size, 0.22, 6.78, f"{name}_header_trim", "InteriorTrim")
        obj.add_box((x, y), transom_size, 0.28, 6.34, f"{name}_public_transom_marker", "DoorGlass")
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

    add_label(labels, "Public circulation thresholds, portals, and orientation signs - schematic", -17.0, 0.0, 7.3, "public_circulation_detail")
    add_label(labels, "Public corridor pilasters, sconces, and floor medallions - schematic", 17.0, 0.0, 7.3, "public_circulation_detail")


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
        add_public_signage_detail_record(records, name, kind, area, (x, y, 5.82), size, message)
        add_label(labels, message, x, y, 6.55, "signage_detail")

    def map_kiosk(name: str, area: str, center: tuple[float, float], message: str) -> None:
        x, y = center
        obj.add_cylinder((x, y), 0.32, 4.45, 0.10, f"{name}_round_base", "DoorMetal", segments=18)
        obj.add_box((x, y), (0.72, 0.22), 1.34, 4.55, f"{name}_support", "BrassRail")
        obj.add_box((x, y), (1.55, 0.22), 1.12, 5.18, f"{name}_map_panel", "MarkerBlue")
        obj.add_box((x, y - 0.03), (1.26, 0.055), 0.62, 5.42, f"{name}_map_graphic_field", "LaneMarkingWhite")
        obj.add_box((x, y - 0.07), (0.92, 0.065), 0.08, 5.98, f"{name}_header_bar", "ArtFrameGold")
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
        add_component(f"{name}_header_trim", "door_header_trim", area, center, 0.0, 0.0, width + 0.50, 0.18, 0.18, z + panel_height + 0.62, orientation, "InteriorTrim")
        add_component(f"{name}_left_side_lite", "side_lite_panel", area, center, -width / 2.0 + side_lite_width / 2.0, 0.0, side_lite_width, 0.10, 1.62, z + 0.24, orientation, "DoorGlass")
        add_component(f"{name}_right_side_lite", "side_lite_panel", area, center, width / 2.0 - side_lite_width / 2.0, 0.0, side_lite_width, 0.10, 1.62, z + 0.24, orientation, "DoorGlass")
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

    add_label(labels, "Public doorway panels, pulls, hinges, kick plates, and transoms - schematic", 22.5, -7.5, 7.65, "door_detail")


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
        add_public_furnishing_detail_record(records, name, "public_bench", area, (x, y, floor_z + 0.42), seat_size)

    def add_display_case(name: str, area: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        base_size = oriented_size(1.55, 0.70, orientation)
        glass_size = oriented_size(1.35, 0.52, orientation)
        obj.add_box((x, y), base_size, 0.42, floor_z, f"{name}_stone_base", "InteriorTrim")
        obj.add_box((x, y), glass_size, 0.74, floor_z + 0.42, f"{name}_glass_case", "DoorGlass")
        obj.add_box((x, y), oriented_size(1.10, 0.34, orientation), 0.12, floor_z + 0.54, f"{name}_object_plinth", "StatueMarble")
        add_public_furnishing_detail_record(records, name, "display_case", area, (x, y, floor_z + 0.78), base_size)

    def add_info_lectern(name: str, area: str, center: tuple[float, float], orientation: str) -> None:
        x, y = center
        obj.add_box((x, y), (0.46, 0.38), 0.92, floor_z, f"{name}_pedestal", "DeskWood")
        panel_size = oriented_size(0.96, 0.08, orientation)
        obj.add_box((x, y), panel_size, 0.32, floor_z + 0.90, f"{name}_map_panel", "MarkerBlue")
        obj.add_box((x, y), oriented_size(0.78, 0.04, orientation), 0.05, floor_z + 1.20, f"{name}_header_strip", "LaneMarkingWhite")
        add_public_furnishing_detail_record(records, name, "information_lectern", area, (x, y, floor_z + 0.70), panel_size)

    def add_receptacle(name: str, area: str, center: tuple[float, float], material: str) -> None:
        x, y = center
        obj.add_cylinder((x, y), 0.24, floor_z, 0.72, f"{name}_cylindrical_body", material, segments=14)
        obj.add_cylinder((x, y), 0.26, floor_z + 0.72, 0.08, f"{name}_rim_lid", "DoorMetal", segments=14)
        obj.add_box((x, y), (0.30, 0.045), 0.04, floor_z + 0.79, f"{name}_slot_marker", "LaneMarkingWhite")
        add_public_furnishing_detail_record(records, name, "waste_receptacle", area, (x, y, floor_z + 0.40), (0.52, 0.52))

    def add_plant_urn(name: str, area: str, center: tuple[float, float]) -> None:
        x, y = center
        obj.add_cylinder((x, y), 0.36, floor_z, 0.45, f"{name}_stone_urn", "PlanterStone", segments=18)
        obj.add_cylinder((x, y), 0.30, floor_z + 0.43, 0.30, f"{name}_greenery_mass", "GroundGrass", segments=16)
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
) -> None:
    """Add generic public visual zones for a joint session in the House Chamber."""
    z = 5.05

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
            obj.add_box((x, curved_y + 0.20), (0.62, 0.28), 0.42, 4.55, f"house_member_desk_{seat_id:03d}", "HouseDesk")
            obj.add_box((x, curved_y + 0.20), (0.46, 0.18), 0.028, 4.98, f"house_member_desk_top_inset_{seat_id:03d}", "InteriorTrim")
            add_generic_chamber_desk_surface_details(
                obj,
                chamber_details,
                f"house_member_desk_{seat_id:03d}",
                "House Chamber",
                (x, curved_y + 0.20),
                (0.46, 0.18),
                5.012,
            )
            obj.add_box((x, curved_y - 0.24), (0.52, 0.45), 0.26, 4.55, f"house_member_chair_seat_{seat_id:03d}", "HouseSeat")
            obj.add_box((x, curved_y - 0.50), (0.52, 0.14), 0.74, 4.72, f"house_member_chair_back_{seat_id:03d}", "HouseSeat")
            obj.add_box((x - 0.32, curved_y - 0.24), (0.055, 0.36), 0.14, 4.78, f"house_member_chair_left_arm_{seat_id:03d}", "HouseSeat")
            obj.add_box((x + 0.32, curved_y - 0.24), (0.055, 0.36), 0.14, 4.78, f"house_member_chair_right_arm_{seat_id:03d}", "HouseSeat")
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
            obj.add_box((x, curved_y + 0.16), (0.82, 0.58), 0.54, 4.55, f"senate_desk_{desk_id:03d}", "SenateDesk")
            obj.add_box((x, curved_y + 0.16), (0.60, 0.38), 0.028, 5.10, f"senate_desk_top_inset_{desk_id:03d}", "InteriorTrim")
            add_generic_chamber_desk_surface_details(
                obj,
                chamber_details,
                f"senate_desk_{desk_id:03d}",
                "Senate Chamber",
                (x, curved_y + 0.16),
                (0.60, 0.38),
                5.132,
            )
            obj.add_box((x, curved_y - 0.40), (0.62, 0.50), 0.32, 4.55, f"senate_chair_seat_{desk_id:03d}", "SenateChair")
            obj.add_box((x, curved_y - 0.70), (0.62, 0.16), 0.82, 4.72, f"senate_chair_back_{desk_id:03d}", "SenateChair")
            obj.add_box((x - 0.38, curved_y - 0.40), (0.06, 0.40), 0.16, 4.82, f"senate_chair_left_arm_{desk_id:03d}", "SenateChair")
            obj.add_box((x + 0.38, curved_y - 0.40), (0.06, 0.40), 0.16, 4.82, f"senate_chair_right_arm_{desk_id:03d}", "SenateChair")
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
    add_joint_session_layout(obj, labels, joint_session)
    seating_sections.extend(build_seating_sections(labels, seats, joint_session))
    add_chamber_realism_details(obj, labels, chamber_details)
    public_art, light_fixtures = add_public_art_and_lighting(obj, labels)

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
            "exterior_osm": {
                "file": "source_data/capitol_osm_overpass_2026-07-04.json",
                "generator": osm_data.get("generator"),
                "timestamp_osm_base": osm_data.get("osm3s", {}).get("timestamp_osm_base"),
                "license": "OpenStreetMap data is available under the Open Database License (ODbL).",
            },
            "interior_public_reference": [
                "Architect of the Capitol public pages for U.S. Capitol Building, Rotunda, House Wing, and Senate Wing.",
                "Interior spaces are schematic and based on publicly described major rooms and chamber functions.",
            ],
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
        f"{len(interior['joint_session'])} joint-session visual records,",
        f"{len(interior['seating'])} generic chamber seats/desks,",
        f"{len(gameplay['items'])} gameplay item props",
    )


if __name__ == "__main__":
    main()
