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
        add_window_surround(name, center, z, orientation, 1.34, 1.28)

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

    def add_roof_cap(name: str, center: tuple[float, float], size: tuple[float, float], z: float) -> None:
        obj.add_box(center, size, 0.48, z, f"{name}_parapet_cap", "ColumnStone")
        obj.add_box(center, (size[0] * 0.92, size[1] * 0.92), 0.22, z + 0.48, f"{name}_slightly_recessed_roof", "CapitolDome")
        add_facade_detail(name, "roof_parapet_and_recessed_roof", (center[0], center[1], z + 0.48))

    def add_column_row(prefix: str, orientation: str, fixed: float, values: list[float], z_base: float, height: float) -> None:
        for idx, value in enumerate(values, start=1):
            center = (fixed, value) if orientation == "east_west" else (value, fixed)
            obj.add_cylinder(center, 0.46, z_base, height, f"{prefix}_column_{idx:02d}", "ColumnStone", segments=18)
            add_facade_detail(f"{prefix}_column_{idx:02d}", "exterior_column", (center[0], center[1], z_base + height / 2.0))

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
                add_window_surround(
                    f"{prefix}_window_{level_index:02d}_{value_index:02d}",
                    (x, y),
                    z_level,
                    orientation,
                    width,
                    height,
                )

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
        add_element(f"{name.replace('_', ' ').title()} revolving door visual", "public_entrance_visual", (x, y, 1.5))

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
            obj.add_box((sx, 0.0), (depth, width), 0.22 + step_index * 0.05, 0.08 + step_index * 0.22, f"{side}_front_stair_step_{step_index+1}", "StepStone")
        for idx, y in enumerate([-24.0, -16.0, -8.0, 0.0, 8.0, 16.0, 24.0], start=1):
            obj.add_cylinder((x * 0.92, y), 0.62, 0.2, 13.5, f"{side}_portico_column_{idx}", "ColumnStone", segments=20)
        add_element(f"{side.title()} front steps and colonnade", "landmark", (x, 0.0, 3.0))
        for door_index, y in enumerate([-9.0, 0.0, 9.0], start=1):
            add_revolving_door(f"{side}_front_{door_index}", (x * 0.86, y), side)
        for lamp_index, y in enumerate([-18.0, -6.0, 6.0, 18.0], start=1):
            add_public_entry_lamp(f"{side}_front_lamp_{lamp_index}", (x * 0.92, y))

    for side, y in (("north", 99.0), ("south", -99.0)):
        add_column_row(f"{side}_wing_portico", "north_south", y * 0.98, [-19.0, -12.5, -6.0, 0.0, 6.0, 12.5, 19.0], 1.3, 10.9)
        for door_index, x in enumerate([-8.0, 0.0, 8.0], start=1):
            add_revolving_door(f"{side}_wing_{door_index}", (x, y), side)
        for lamp_index, x in enumerate([-18.0, -6.0, 6.0, 18.0], start=1):
            add_public_entry_lamp(f"{side}_wing_lamp_{lamp_index}", (x, y * 0.95))

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
        if idx % 2 == 0:
            wx = 17.85 * math.cos(angle)
            wy = 17.85 * math.sin(angle)
            obj.add_cylinder((wx, wy), 0.30, 22.8, 1.25, f"dome_drum_dark_window_{idx//2+1:02d}", "FacadeWindow", segments=10)
    for idx in range(24):
        angle = math.tau * idx / 24.0
        px = 12.2 * math.cos(angle)
        py = 12.2 * math.sin(angle)
        obj.add_cylinder((px, py), 0.10, 34.5, 16.5, f"dome_vertical_rib_{idx+1:02d}", "ColumnStone", segments=8)
    obj.add_dome((0.0, 0.0), 18.0, 34.0, 22.0, "capitol_dome_approximate_shell", "CapitolDome", segments=72, rings=10)
    obj.add_cylinder((0.0, 0.0), 4.2, 55.5, 5.2, "dome_lantern_cylinder", "ColumnStone", segments=32)
    for idx in range(8):
        angle = math.tau * idx / 8.0
        obj.add_cylinder((4.28 * math.cos(angle), 4.28 * math.sin(angle)), 0.16, 56.25, 1.7, f"dome_lantern_dark_window_{idx+1:02d}", "FacadeWindow", segments=8)
    add_facade_detail("dome_lantern_dark_window_ring", "lantern_window", (0.0, 0.0, 57.1), {"count": 8})
    obj.add_dome((0.0, 0.0), 4.2, 60.2, 4.0, "dome_lantern_cap", "CapitolDome", segments=32, rings=5)
    obj.add_cylinder((0.0, 0.0), 0.18, 64.0, 2.1, "dome_lantern_finial", "ColumnStone", segments=12)
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
    z: float = 4.45,
) -> list[dict[str, Any]]:
    cx, cy = center
    sx, sy = size
    cell_w = sx / columns
    cell_h = sy / rows
    records: list[dict[str, Any]] = []
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
            obj.add_box((ox, oy - cell_h * 0.28), (0.70, 0.55), 0.55, z + 0.18, room_id + "_chair", "ChairLeather")
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


def add_rotunda_visual_details(obj: ObjWriter, labels: list[dict[str, Any]]) -> None:
    obj.add_ring((0.0, 0.0), 15.05, 14.45, 4.35, 4.9, "rotunda_public_wall_ring", "RotundaWall", segments=96)
    obj.add_ring((0.0, 0.0), 10.8, 10.55, 4.42, 0.18, "rotunda_inner_floor_trim_ring", "BrassRail", segments=96)
    obj.add_cylinder((0.0, 0.0), 3.2, 4.46, 0.18, "rotunda_center_floor_medallion", "BrassRail", segments=64)
    for idx in range(16):
        angle = math.tau * idx / 16.0
        x = 13.55 * math.cos(angle)
        y = 13.55 * math.sin(angle)
        obj.add_cylinder((x, y), 0.28, 4.42, 4.25, f"rotunda_perimeter_column_{idx+1:02d}", "ColumnStone", segments=16)
    add_label(labels, "Rotunda wall ring, columns, floor trim", 0.0, 11.0, 7.2, "major_public_space")


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

    def flag_standard(name: str, chamber: str, x: float, y: float, z: float, flag_material: str) -> None:
        obj.add_cylinder((x, y), 0.055, z, 2.3, f"{name}_pole", "BrassRail", segments=10)
        obj.add_cylinder((x, y), 0.15, z + 2.3, 0.18, f"{name}_finial", "BrassRail", segments=12)
        obj.add_box((x + 0.28, y), (0.55, 0.08), 0.68, z + 1.35, f"{name}_cloth_panel", flag_material)
        add_chamber_detail_record(records, name, "flag_standard", chamber, (x, y, z + 1.15), (0.7, 0.18))

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

    add_label(labels, "House and Senate chamber rails, dais steps, flags, and aisle trim - schematic", 0.0, -43.0, 7.7, "chamber_detail")


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


def build_house_seats(obj: ObjWriter, seats: list[dict[str, Any]], labels: list[dict[str, Any]]) -> None:
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
            obj.add_box((x, curved_y - 0.24), (0.52, 0.45), 0.26, 4.55, f"house_member_chair_seat_{seat_id:03d}", "HouseSeat")
            obj.add_box((x, curved_y - 0.50), (0.52, 0.14), 0.74, 4.72, f"house_member_chair_back_{seat_id:03d}", "HouseSeat")
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
    add_label(labels, "House member seating: 448 generic floor seats", center_x, center_y - 13.0, 5.25, "seating")
    add_label(labels, "Speaker rostrum / clerks / press area", center_x, rostrum_y, 5.25, "seating")
    obj.add_box((center_x, rostrum_y), (14.0, 4.2), 0.38, 4.55, "house_rostrum_lower_platform", "PublicGallery")
    obj.add_box((center_x, rostrum_y + 0.9), (10.5, 2.2), 0.72, 4.9, "house_speaker_dais", "PublicGallery")
    obj.add_box((center_x, rostrum_y + 1.15), (6.0, 0.9), 0.72, 5.55, "house_speaker_desk", "DeskWood")
    obj.add_box((-6.5, rostrum_y - 0.65), (3.2, 1.2), 0.7, 4.75, "house_clerk_table_left", "DeskWood")
    obj.add_box((6.5, rostrum_y - 0.65), (3.2, 1.2), 0.7, 4.75, "house_clerk_table_right", "DeskWood")
    add_gallery_risers(obj, "house_north_public_gallery", (0.0, -100.0), 66.0, 8.0, 4, 4.55)


def build_senate_desks(obj: ObjWriter, seats: list[dict[str, Any]], labels: list[dict[str, Any]]) -> None:
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
            obj.add_box((x, curved_y - 0.40), (0.62, 0.50), 0.32, 4.55, f"senate_chair_seat_{desk_id:03d}", "SenateChair")
            obj.add_box((x, curved_y - 0.70), (0.62, 0.16), 0.82, 4.72, f"senate_chair_back_{desk_id:03d}", "SenateChair")
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
    joint_session: list[dict[str, Any]] = []
    public_art: list[dict[str, Any]] = []
    light_fixtures: list[dict[str, Any]] = []
    wall_treatments: list[dict[str, Any]] = []
    chamber_details: list[dict[str, Any]] = []

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
    add_rotunda_visual_details(obj, labels)

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

    office_cells.extend(add_public_office_grid(obj, labels, "house_west_support", (-53.0, -55.0), (19.0, 42.0), 3, 5))
    office_cells.extend(add_public_office_grid(obj, labels, "house_east_support", (53.0, -55.0), (19.0, 42.0), 3, 5))
    office_cells.extend(add_public_office_grid(obj, labels, "senate_west_support", (-52.0, 55.0), (19.0, 42.0), 3, 5))
    office_cells.extend(add_public_office_grid(obj, labels, "senate_east_support", (52.0, 55.0), (19.0, 42.0), 3, 5))

    build_house_seats(obj, seats, labels)
    build_senate_desks(obj, seats, labels)
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
    add_label(labels, "Wainscot panels, chair rails, and picture rails - schematic", 0.0, -6.5, 7.6, "wall_treatment")

    obj.write(MESH_DIR / "capitol_public_interior_schematic.obj", "capitol_materials.mtl")
    return {
        "rooms": rooms,
        "labels": labels,
        "seating": seats,
        "seating_sections": seating_sections,
        "office_cells": office_cells,
        "joint_session": joint_session,
        "public_art": public_art,
        "light_fixtures": light_fixtures,
        "wall_treatments": wall_treatments,
        "chamber_details": chamber_details,
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
        f"{len(exterior['streetscape_props'])} streetscape props,",
        f"{len(landmark['elements'])} landmark detail elements,",
        f"{len(landmark['facade_details'])} facade/furniture details,",
        f"{len(interior['office_cells'])} generic office cells,",
        f"{len(interior['seating_sections'])} seating sections,",
        f"{len(interior['public_art'])} public-art visuals,",
        f"{len(interior['light_fixtures'])} light fixtures,",
        f"{len(interior['wall_treatments'])} wall-treatment records,",
        f"{len(interior['chamber_details'])} chamber detail records,",
        f"{len(interior['joint_session'])} joint-session visual records,",
        f"{len(interior['seating'])} generic chamber seats/desks,",
        f"{len(gameplay['items'])} gameplay item props",
    )


if __name__ == "__main__":
    main()
