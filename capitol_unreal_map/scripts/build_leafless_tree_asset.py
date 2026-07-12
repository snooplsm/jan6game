"""Generate a reusable leafless deciduous tree for the Jan. 6 winter scene.

The mesh is intentionally species-neutral and represents the public silhouette
of a mature maintained campus tree.  Dimensions are Unreal centimeters.  The
branch hierarchy is deterministic so regenerations are stable in source control.
"""

from __future__ import annotations

import math
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "generated" / "meshes"
OBJ_PATH = OUT_DIR / "capitol_leafless_winter_tree.obj"
MTL_PATH = OUT_DIR / "capitol_leafless_winter_tree.mtl"


class Mesh:
    def __init__(self) -> None:
        self.vertices: list[tuple[float, float, float]] = []
        self.faces: list[tuple[int, int, int, int]] = []

    def vertex(self, p: tuple[float, float, float]) -> int:
        self.vertices.append(p)
        return len(self.vertices)

    def tapered_segment(
        self,
        start: tuple[float, float, float],
        end: tuple[float, float, float],
        radius_start: float,
        radius_end: float,
        sides: int = 8,
    ) -> None:
        dx, dy, dz = (end[i] - start[i] for i in range(3))
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length < 0.01:
            return
        axis = (dx / length, dy / length, dz / length)
        helper = (0.0, 0.0, 1.0) if abs(axis[2]) < 0.92 else (1.0, 0.0, 0.0)
        ux = axis[1] * helper[2] - axis[2] * helper[1]
        uy = axis[2] * helper[0] - axis[0] * helper[2]
        uz = axis[0] * helper[1] - axis[1] * helper[0]
        ul = math.sqrt(ux * ux + uy * uy + uz * uz)
        u = (ux / ul, uy / ul, uz / ul)
        v = (
            axis[1] * u[2] - axis[2] * u[1],
            axis[2] * u[0] - axis[0] * u[2],
            axis[0] * u[1] - axis[1] * u[0],
        )
        rings: list[list[int]] = []
        for center, radius in ((start, radius_start), (end, radius_end)):
            ring: list[int] = []
            for i in range(sides):
                a = math.tau * i / sides
                offset = tuple(radius * (math.cos(a) * u[j] + math.sin(a) * v[j]) for j in range(3))
                ring.append(self.vertex(tuple(center[j] + offset[j] for j in range(3))))
            rings.append(ring)
        for i in range(sides):
            j = (i + 1) % sides
            self.faces.append((rings[0][i], rings[0][j], rings[1][j], rings[1][i]))


def endpoint(
    start: tuple[float, float, float],
    azimuth: float,
    elevation: float,
    length: float,
) -> tuple[float, float, float]:
    horizontal = length * math.cos(elevation)
    return (
        start[0] + math.cos(azimuth) * horizontal,
        start[1] + math.sin(azimuth) * horizontal,
        start[2] + math.sin(elevation) * length,
    )


def build() -> None:
    rng = random.Random(20210106)
    mesh = Mesh()
    mesh.tapered_segment((0.0, 0.0, 0.0), (0.0, 0.0, 780.0), 48.0, 20.0, 12)
    mesh.tapered_segment((0.0, 0.0, 770.0), (18.0, -8.0, 1040.0), 21.0, 5.5, 10)

    primary_specs = [
        (250.0, 0.10, 0.52, 340.0), (300.0, 2.95, 0.48, 325.0),
        (390.0, 1.35, 0.58, 330.0), (430.0, 4.35, 0.55, 310.0),
        (520.0, 0.65, 0.66, 300.0), (560.0, 3.65, 0.64, 285.0),
        (650.0, 2.05, 0.72, 260.0), (690.0, 5.15, 0.74, 245.0),
        (760.0, 0.95, 0.82, 220.0), (790.0, 4.05, 0.84, 205.0),
    ]
    for index, (z, azimuth, elevation, length) in enumerate(primary_specs):
        base = (0.0, 0.0, z)
        tip = endpoint(base, azimuth, elevation, length)
        r0 = max(10.0, 23.0 - index * 1.15)
        mesh.tapered_segment(base, tip, r0, r0 * 0.34, 9)
        for child in range(3):
            fraction = 0.42 + child * 0.19
            joint = tuple(base[i] + (tip[i] - base[i]) * fraction for i in range(3))
            child_az = azimuth + (-0.92 + child * 0.86) + rng.uniform(-0.16, 0.16)
            child_el = elevation + rng.uniform(-0.08, 0.18)
            child_len = length * (0.48 - child * 0.055)
            child_tip = endpoint(joint, child_az, child_el, child_len)
            mesh.tapered_segment(joint, child_tip, r0 * 0.36, 2.8, 7)
            for twig in (-1, 1):
                twig_joint = tuple(joint[i] + (child_tip[i] - joint[i]) * 0.62 for i in range(3))
                twig_tip = endpoint(
                    twig_joint,
                    child_az + twig * (0.48 + rng.uniform(-0.10, 0.10)),
                    child_el + 0.12 + rng.uniform(-0.06, 0.12),
                    child_len * 0.44,
                )
                mesh.tapered_segment(twig_joint, twig_tip, 2.8, 0.75, 6)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["mtllib capitol_leafless_winter_tree.mtl", "o CapitolLeaflessWinterTree", "usemtl WinterTreeBark"]
    lines.extend(f"v {x:.4f} {y:.4f} {z:.4f}" for x, y, z in mesh.vertices)
    lines.extend("f " + " ".join(map(str, face)) for face in mesh.faces)
    OBJ_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    MTL_PATH.write_text(
        "newmtl WinterTreeBark\nKd 0.105 0.072 0.050\nKs 0.025 0.025 0.025\nNs 12\n",
        encoding="utf-8",
    )
    print(f"wrote {OBJ_PATH} ({len(mesh.vertices)} vertices, {len(mesh.faces)} faces)")


if __name__ == "__main__":
    build()
