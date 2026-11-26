"""The Herald & The Oracle — AI Geodesic Polyhedra — Blender 4.2 EEVEE Next showcase."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

import bmesh
import bpy
import mathutils
from mathutils import Matrix, Vector

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blender_gallery import common

SCORE_PATH = REPO_ROOT / "scores" / "showcase_3d" / "08_herald_oracle_ai.json"
WAV_PATH = REPO_ROOT / "output" / "showcase_3d" / "08_herald_oracle_ai.wav"
BLEND_PATH = REPO_ROOT / "output" / "showcase_3d" / "08_herald_oracle_ai.blend"
WEBM_PATH = REPO_ROOT / "output" / "showcase_3d" / "08_herald_oracle_ai.webm"
STILLS_DIR = REPO_ROOT / "output" / "showcase_3d"
TMP_FRAMES_DIR = Path("/tmp/frames_herald_oracle_ai")

PEDESTAL_Z = 0.09
STEP_MIN = 0
STEP_MAX = 106

HERALD_CENTER = Vector((-0.56, 0.04, 1.38))
ORACLE_CENTER = Vector((0.56, -0.04, 1.18))


def _make_mesh_obj(
    col: bpy.types.Collection,
    name: str,
    bm: bmesh.types.BMesh,
    mat: bpy.types.Material,
    *,
    smooth: bool = True,
    bevel_w: float = 0.0,
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    if smooth:
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    col.objects.link(obj)
    if bevel_w > 0.0:
        bev = obj.modifiers.new("Bevel", "BEVEL")
        bev.width = bevel_w
        bev.segments = 2
    return obj


def _add_cylinder(
    bm: bmesh.types.BMesh,
    p0: Vector,
    p1: Vector,
    r0: float,
    r1: float,
    segments: int = 10,
    cap_ends: bool = True,
) -> None:
    vec = p1 - p0
    length = vec.length
    if length < 1e-6:
        return
    mid = (p0 + p1) * 0.5
    rot = vec.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.create_cone(
        bm,
        cap_ends=cap_ends,
        cap_tris=False,
        segments=segments,
        radius1=r0,
        radius2=r1,
        depth=length,
        matrix=Matrix.Translation(mid) @ rot,
    )


def _add_torus(
    bm: bmesh.types.BMesh,
    major_r: float,
    minor_r: float,
    major_seg: int = 40,
    minor_seg: int = 8,
    transform: Matrix | None = None,
) -> None:
    rings: list[list[bmesh.types.BMVert]] = []
    for i in range(major_seg):
        ang = 2.0 * math.pi * i / major_seg
        ca, sa = math.cos(ang), math.sin(ang)
        rv: list[bmesh.types.BMVert] = []
        for j in range(minor_seg):
            phi = 2.0 * math.pi * j / minor_seg
            rr = major_r + minor_r * math.cos(phi)
            zz = minor_r * math.sin(phi)
            pt = Vector((rr * ca, rr * sa, zz))
            if transform is not None:
                pt = transform @ pt
            rv.append(bm.verts.new(pt))
        rings.append(rv)
    for i in range(major_seg):
        inext = (i + 1) % major_seg
        for j in range(minor_seg):
            jnext = (j + 1) % minor_seg
            bm.faces.new((rings[i][j], rings[inext][j], rings[inext][jnext], rings[i][jnext]))


def _add_octahedron(bm: bmesh.types.BMesh, radius: float, rot: Matrix | None = None) -> list[bmesh.types.BMVert]:
    pts = [
        Vector((radius, 0.0, 0.0)),
        Vector((-radius, 0.0, 0.0)),
        Vector((0.0, radius, 0.0)),
        Vector((0.0, -radius, 0.0)),
        Vector((0.0, 0.0, radius)),
        Vector((0.0, 0.0, -radius)),
    ]
    if rot is not None:
        pts = [rot @ p for p in pts]
    verts = [bm.verts.new(p) for p in pts]
    faces = [
        (0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4),
        (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5),
    ]
    for a, b, c in faces:
        bm.faces.new((verts[a], verts[b], verts[c]))
    return verts


def _add_wireframe_from_bm(bm_src: bmesh.types.BMesh, bm_dst: bmesh.types.BMesh, strut_r: float) -> None:
    """Emit crisp cylindrical brass struts along every unique edge of bm_src."""
    for edge in bm_src.edges:
        p0 = edge.verts[0].co.copy()
        p1 = edge.verts[1].co.copy()
        _add_cylinder(bm_dst, p0, p1, strut_r, strut_r, segments=6, cap_ends=True)


def _blend_rgb(a: tuple[float, float, float], b: tuple[float, float, float], t: float) -> tuple[float, float, float]:
    return (
        a[0] * (1.0 - t) + b[0] * t,
        a[1] * (1.0 - t) + b[1] * t,
        a[2] * (1.0 - t) + b[2] * t,
    )


def build_mathematical_plinth(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Build sleek GlossEbony & PolishedBrass octagonal mathematical plinth + critical-line pedestal."""
    bm_ebony = bmesh.new()
    bm_brass = bmesh.new()
    bm_gold = bmesh.new()

    def _add_oct_tier(center_xy: tuple[float, float], z0: float, z1: float, r0: float, r1: float, bm: bmesh.types.BMesh) -> None:
        cx, cy = center_xy
        bot_v, top_v = [], []
        for k in range(8):
            ang = (k + 0.5) * (2.0 * math.pi / 8.0)
            ca, sa = math.cos(ang), math.sin(ang)
            bot_v.append(bm.verts.new((cx + r0 * ca, cy + r0 * sa, z0)))
            top_v.append(bm.verts.new((cx + r1 * ca, cy + r1 * sa, z1)))
        for k in range(8):
            kn = (k + 1) % 8
            bm.faces.new((bot_v[k], bot_v[kn], top_v[kn], top_v[k]))
        bm.faces.new(list(reversed(bot_v)))
        bm.faces.new(top_v)

    # Main obsidian octagonal plinth seated flush at PEDESTAL_Z = 0.09
    _add_oct_tier((0.0, 0.0), PEDESTAL_Z, PEDESTAL_Z + 0.080, 1.12, 1.06, bm_ebony)
    _add_oct_tier((0.0, 0.0), PEDESTAL_Z + 0.080, PEDESTAL_Z + 0.094, 1.07, 1.03, bm_brass)
    _add_oct_tier((0.0, 0.0), PEDESTAL_Z + 0.094, PEDESTAL_Z + 0.150, 0.98, 0.94, bm_ebony)

    # Etched brass mathematical grid & Re(s)=1/2 critical-line meridian strip on top (z = 0.242)
    z_dial = PEDESTAL_Z + 0.152
    _add_torus(bm_brass, 0.86, 0.005, major_seg=48, minor_seg=6, transform=Matrix.Translation((0.0, 0.0, z_dial)))
    _add_torus(bm_brass, 0.56, 0.004, major_seg=40, minor_seg=6, transform=Matrix.Translation((0.0, 0.0, z_dial)))
    # Radial dial lines
    for k in range(8):
        ang = k * (math.pi / 4.0)
        p0 = Vector((0.18 * math.cos(ang), 0.18 * math.sin(ang), z_dial))
        p1 = Vector((0.86 * math.cos(ang), 0.86 * math.sin(ang), z_dial))
        _add_cylinder(bm_brass, p0, p1, 0.0035, 0.0035, segments=6)
    # Critical-line Re(s) = 1/2 brass meridian bar passing beneath Oracle
    _add_cylinder(
        bm_gold,
        Vector((ORACLE_CENTER.x, -0.78, z_dial + 0.002)),
        Vector((ORACLE_CENTER.x, 0.72, z_dial + 0.002)),
        0.007,
        0.007,
        segments=8,
    )

    # Left Orbital Projector Pad beneath The Herald
    hx, hy = HERALD_CENTER.x, HERALD_CENTER.y
    _add_oct_tier((hx, hy), z_dial - 0.004, z_dial + 0.056, 0.30, 0.26, bm_ebony)
    _add_torus(bm_brass, 0.265, 0.007, major_seg=32, minor_seg=8, transform=Matrix.Translation((hx, hy, z_dial + 0.054)))

    # Herald plinth emitter ring (LuminousElement)
    bm_emit = bmesh.new()
    _add_torus(bm_emit, 0.18, 0.010, major_seg=32, minor_seg=8, transform=Matrix.Translation((hx, hy, z_dial + 0.060)))
    herald_pad_glow = _make_mesh_obj(col, "HeraldProjectorGlow", bm_emit, mats["LuminousElement"], smooth=True)
    herald_pad_glow.color = (0.08, 0.72, 1.0, 0.18)

    # Right Critical-Line Column Pedestal beneath The Oracle
    ox, oy = ORACLE_CENTER.x, ORACLE_CENTER.y
    _add_oct_tier((ox, oy), z_dial - 0.004, z_dial + 0.12, 0.28, 0.23, bm_ebony)
    _add_oct_tier((ox, oy), z_dial + 0.12, z_dial + 0.14, 0.235, 0.215, bm_gold)
    _add_oct_tier((ox, oy), z_dial + 0.14, 0.62, 0.18, 0.14, bm_ebony)
    _add_oct_tier((ox, oy), 0.62, 0.65, 0.19, 0.21, bm_gold)

    # BrushedGold critical-line cradle arc rising seamlessly from Oracle pedestal toward Re(s)=1/2 gimbal
    cradle_r = 0.42
    n_arc = 28
    arc_rings: list[list[bmesh.types.BMVert]] = []
    n_tube = 10
    for i in range(n_arc + 1):
        a = math.radians(-145.0 + i * (110.0 / n_arc))
        c_pt = Vector((ox + cradle_r * math.cos(a), oy, ORACLE_CENTER.z + cradle_r * math.sin(a)))
        rad_dir = Vector((math.cos(a), 0.0, math.sin(a)))
        y_dir = Vector((0.0, 1.0, 0.0))
        ring = []
        for j in range(n_tube):
            phi = 2.0 * math.pi * j / n_tube
            pt = c_pt + rad_dir * (0.011 * math.cos(phi)) + y_dir * (0.011 * math.sin(phi))
            ring.append(bm_gold.verts.new(pt))
        arc_rings.append(ring)
    for i in range(n_arc):
        r0, r1 = arc_rings[i], arc_rings[i + 1]
        for j in range(n_tube):
            jn = (j + 1) % n_tube
            bm_gold.faces.new((r0[j], r0[jn], r1[jn], r1[j]))
    bm_gold.faces.new(list(reversed(arc_rings[0])))
    bm_gold.faces.new(arc_rings[-1])
    _add_cylinder(bm_gold, Vector((ox, oy, 0.65)), Vector((ox, oy, ORACLE_CENTER.z - cradle_r)), 0.014, 0.012, segments=10)

    _make_mesh_obj(col, "PlinthObsidian", bm_ebony, mats["GlossEbony"], smooth=False, bevel_w=0.004)
    _make_mesh_obj(col, "PlinthBrassInlay", bm_brass, mats["PolishedBrass"], smooth=True)
    _make_mesh_obj(col, "PlinthGoldCritical", bm_gold, mats["BrushedGold"], smooth=True)
    return herald_pad_glow


def build_herald(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build The Herald (ai_strip): crystalline icosahedron core + geodesic brass cage + 3 rotating rings."""
    anchor = bpy.data.objects.new("HeraldRoot", None)
    anchor.empty_display_type = "PLAIN_AXES"
    anchor.location = HERALD_CENTER
    col.objects.link(anchor)

    # 1) Faceted crystalline icosahedron core (LuminousElement, flat-shaded crisp crystal facets)
    bm_ico = bmesh.new()
    bmesh.ops.create_icosphere(bm_ico, subdivisions=1, radius=0.22)
    bm_cage = bmesh.new()
    _add_wireframe_from_bm(bm_ico, bm_cage, strut_r=0.0055)
    # Slightly inset core so brass geodesic lattice frames every facet cleanly
    bmesh.ops.scale(bm_ico, vec=(0.96, 0.96, 0.96), verts=bm_ico.verts)

    core_obj = _make_mesh_obj(col, "HeraldCrystalCore", bm_ico, mats["LuminousElement"], smooth=False)
    core_obj.parent = anchor
    core_obj.color = (0.08, 0.64, 0.98, 0.16)

    cage_obj = _make_mesh_obj(col, "HeraldGeodesicCage", bm_cage, mats["PolishedBrass"], smooth=True)
    cage_obj.parent = core_obj

    # 2) Three delicate rotating geodesic brass rings + luminous vertex nodes
    ring_specs = [
        ("HeraldRingOuter", 0.42, 0.0075, (0.42, -0.24, 0.10)),
        ("HeraldRingMid", 0.36, 0.0065, (-0.52, 0.38, 0.25)),
        ("HeraldRingInner", 0.30, 0.0055, (0.28, 0.62, -0.30)),
    ]
    ring_objs: list[bpy.types.Object] = []
    ring_nodes: list[bpy.types.Object] = []

    for rname, maj_r, min_r, init_rot in ring_specs:
        bm_r = bmesh.new()
        _add_torus(bm_r, maj_r, min_r, major_seg=44, minor_seg=8)
        r_obj = _make_mesh_obj(col, rname, bm_r, mats["PolishedBrass"], smooth=True)
        r_obj.parent = anchor
        r_obj.rotation_euler = init_rot
        ring_objs.append(r_obj)

        # 4 glowing cardinal jewel nodes per ring
        bm_nodes = bmesh.new()
        for k in range(4):
            ang = k * (math.pi * 0.5)
            pos = Vector((maj_r * math.cos(ang), maj_r * math.sin(ang), 0.0))
            _add_octahedron(bm_nodes, 0.015, rot=Matrix.Translation(pos))
        n_obj = _make_mesh_obj(col, f"{rname}_Nodes", bm_nodes, mats["LuminousElement"], smooth=False)
        n_obj.parent = r_obj
        n_obj.color = (0.14, 0.82, 1.0, 0.28)
        ring_nodes.append(n_obj)

    return {
        "anchor": anchor,
        "core_obj": core_obj,
        "ring_objs": ring_objs,
        "ring_nodes": ring_nodes,
    }


def build_oracle(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build The Oracle (ai_architect): nested dual-octahedron with BrushedGold meridian gimbal at Re(s)=1/2."""
    anchor = bpy.data.objects.new("OracleRoot", None)
    anchor.empty_display_type = "PLAIN_AXES"
    anchor.location = ORACLE_CENTER
    col.objects.link(anchor)

    # 1) Outer faceted crystal octahedron (LuminousElement) + BrushedGold edge struts
    bm_outer = bmesh.new()
    _add_octahedron(bm_outer, 0.24)
    bm_outer_cage = bmesh.new()
    _add_wireframe_from_bm(bm_outer, bm_outer_cage, strut_r=0.007)
    bmesh.ops.scale(bm_outer, vec=(0.94, 0.94, 0.94), verts=bm_outer.verts)

    outer_obj = _make_mesh_obj(col, "OracleOuterOctahedron", bm_outer, mats["LuminousElement"], smooth=False)
    outer_obj.parent = anchor
    outer_obj.color = (0.48, 0.14, 0.92, 0.14)

    outer_cage = _make_mesh_obj(col, "OracleOuterBrassFrame", bm_outer_cage, mats["BrushedGold"], smooth=True)
    outer_cage.parent = outer_obj

    # 2) Interpenetrating nested dual-octahedron (stately rotated gold/amethyst geometric compound)
    bm_inner = bmesh.new()
    dual_rot = Matrix.Rotation(math.radians(45.0), 4, "Z") @ Matrix.Rotation(math.radians(54.74), 4, "X")
    _add_octahedron(bm_inner, 0.235, rot=dual_rot)
    bm_inner_cage = bmesh.new()
    _add_wireframe_from_bm(bm_inner, bm_inner_cage, strut_r=0.006)
    bmesh.ops.scale(bm_inner, vec=(0.95, 0.95, 0.95), verts=bm_inner.verts)

    inner_obj = _make_mesh_obj(col, "OracleInnerDualCore", bm_inner, mats["LuminousElement"], smooth=False)
    inner_obj.parent = anchor
    inner_obj.color = (0.94, 0.68, 0.16, 0.22)

    inner_cage = _make_mesh_obj(col, "OracleInnerBrassFrame", bm_inner_cage, mats["PolishedBrass"], smooth=True)
    inner_cage.parent = inner_obj

    # 3) Stately BrushedGold Meridian Gimbal locked above Re(s)=1/2
    bm_gimbal = bmesh.new()
    # Vertical meridian ring in Y-Z plane (rotated 90 deg around Y)
    _add_torus(
        bm_gimbal,
        0.34,
        0.011,
        major_seg=48,
        minor_seg=10,
        transform=Matrix.Rotation(math.pi * 0.5, 4, "Y"),
    )
    # Polar axis finials (North & South spires along Z)
    _add_cylinder(bm_gimbal, Vector((0.0, 0.0, 0.34)), Vector((0.0, 0.0, 0.44)), 0.016, 0.003, segments=10)
    _add_cylinder(bm_gimbal, Vector((0.0, 0.0, -0.34)), Vector((0.0, 0.0, -0.42)), 0.016, 0.004, segments=10)
    gimbal_obj = _make_mesh_obj(col, "OracleMeridianGimbal", bm_gimbal, mats["BrushedGold"], smooth=True)
    gimbal_obj.parent = anchor
    # Slight architectural yaw so the critical-line meridian plane reads clearly to camera
    gimbal_obj.rotation_euler = (0.0, 0.0, math.radians(18.0))

    # Equatorial vernier brass ring rotating smoothly around Z
    bm_eq = bmesh.new()
    _add_torus(bm_eq, 0.38, 0.007, major_seg=48, minor_seg=8)
    eq_obj = _make_mesh_obj(col, "OracleEquatorialRing", bm_eq, mats["PolishedBrass"], smooth=True)
    eq_obj.parent = anchor

    return {
        "anchor": anchor,
        "outer_obj": outer_obj,
        "inner_obj": inner_obj,
        "gimbal_obj": gimbal_obj,
        "eq_obj": eq_obj,
    }


def build_harmonic_mirror_beam(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build slender luminous Harmonic Mirror Beam + resonance nodes connecting Herald & Oracle."""
    vec = ORACLE_CENTER - HERALD_CENTER
    dist = vec.length
    mid = (HERALD_CENTER + ORACLE_CENTER) * 0.5
    rot_q = vec.normalized().to_track_quat("Z", "Y")

    beam_root = bpy.data.objects.new("HarmonicMirrorBeamRoot", None)
    beam_root.empty_display_type = "PLAIN_AXES"
    beam_root.location = mid
    beam_root.rotation_euler = rot_q.to_euler()
    col.objects.link(beam_root)

    # Central slender luminous bridge cylinder
    bm_beam = bmesh.new()
    _add_cylinder(
        bm_beam,
        Vector((0.0, 0.0, -dist * 0.42)),
        Vector((0.0, 0.0, dist * 0.42)),
        0.011,
        0.011,
        segments=12,
    )
    # Tapered outer aura filaments / harmonic nodes at 1/4, 1/2, 3/4
    for z_frac, r_node in ((-0.22, 0.024), (0.0, 0.036), (0.22, 0.024)):
        _add_octahedron(bm_beam, r_node, rot=Matrix.Translation((0.0, 0.0, dist * z_frac)))

    beam_obj = _make_mesh_obj(col, "HarmonicMirrorBeam", bm_beam, mats["LuminousElement"], smooth=True)
    beam_obj.parent = beam_root
    beam_obj.color = (0.45, 0.72, 1.0, 0.0)
    beam_obj.scale = (0.0, 0.0, 0.0)

    # Delicate brass symmetry ring at the exact midpoint Re(s)=1/2 mirror pivot
    bm_ring = bmesh.new()
    _add_torus(bm_ring, 0.068, 0.0045, major_seg=28, minor_seg=6)
    mid_ring = _make_mesh_obj(col, "HarmonicMirrorPivotRing", bm_ring, mats["PolishedBrass"], smooth=True)
    mid_ring.parent = beam_root
    mid_ring.scale = (0.0, 0.0, 0.0)

    return {
        "root": beam_root,
        "beam_obj": beam_obj,
        "mid_ring": mid_ring,
    }


def _compute_mirror_overlaps(
    herald_notes: list[dict[str, Any]],
    oracle_notes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Find overlapping time intervals where both Herald and Oracle sound together."""
    overlaps: list[dict[str, Any]] = []
    for hn in herald_notes:
        for on in oracle_notes:
            s = max(float(hn["start_s"]), float(on["start_s"]))
            e = min(float(hn["end_s"]), float(on["end_s"]))
            if e - s > 0.03:
                overlaps.append(
                    {
                        "start_s": s,
                        "end_s": e,
                        "h_step": int(hn["step"]),
                        "o_step": int(on["step"]),
                        "vel": max(float(hn.get("vel", 0.7)), float(on.get("vel", 0.7))),
                    }
                )
    overlaps.sort(key=lambda x: x["start_s"])
    return overlaps


def animate_herald_oracle(
    timeline: dict[str, Any],
    herald_pad_glow: bpy.types.Object,
    herald: dict[str, Any],
    oracle: dict[str, Any],
    beam: dict[str, Any],
) -> None:
    """Keyframe clean crystalline rotation leaps, vivid 53-EDO glows, and Harmonic Mirror Beam."""
    fps = int(timeline["fps"])
    total_frames = int(timeline["total_frames"])

    herald_notes: list[dict[str, Any]] = []
    oracle_notes: list[dict[str, Any]] = []
    for ev in timeline.get("notes", []):
        tid = ev.get("track_id", "")
        if tid == "ai_strip":
            herald_notes.append(ev)
        elif tid == "ai_architect":
            oracle_notes.append(ev)

    # 1) Ambient gentle hover bob + steady geodesic ring rotation (smooth linear spin, zero jitter)
    for key_f in (1, total_frames):
        u = (key_f - 1) / float(max(1, total_frames - 1))
        herald["anchor"].location = (
            HERALD_CENTER.x,
            HERALD_CENTER.y,
            HERALD_CENTER.z + 0.025 * math.sin(2.0 * math.pi * u * 2.0),
        )
        herald["anchor"].keyframe_insert(data_path="location", frame=key_f)

        oracle["anchor"].location = (
            ORACLE_CENTER.x,
            ORACLE_CENTER.y,
            ORACLE_CENTER.z + 0.018 * math.cos(2.0 * math.pi * u * 2.0),
        )
        oracle["anchor"].keyframe_insert(data_path="location", frame=key_f)

    ring_speeds = ((1.2, 0.8, 1.8), (-1.4, 1.1, -1.5), (0.9, -1.3, 2.1))
    for r_obj, (sx, sy, sz) in zip(herald["ring_objs"], ring_speeds):
        base_rot = tuple(r_obj.rotation_euler)
        r_obj.rotation_euler = base_rot
        r_obj.keyframe_insert(data_path="rotation_euler", frame=1)
        r_obj.rotation_euler = (
            base_rot[0] + sx * math.pi,
            base_rot[1] + sy * math.pi,
            base_rot[2] + sz * math.pi,
        )
        r_obj.keyframe_insert(data_path="rotation_euler", frame=total_frames)

    oracle["eq_obj"].rotation_euler = (0.0, 0.0, 0.0)
    oracle["eq_obj"].keyframe_insert(data_path="rotation_euler", frame=1)
    oracle["eq_obj"].rotation_euler = (0.0, 0.0, 2.0 * math.pi)
    oracle["eq_obj"].keyframe_insert(data_path="rotation_euler", frame=total_frames)

    # 2) Animate The Herald (ai_strip): electric cyan/sapphire/vivid-step glow + clean crystalline rotation leaps
    h_core = herald["core_obj"]
    h_idle = (0.08, 0.64, 0.98, 0.14)
    h_core.color = h_idle
    h_core.rotation_euler = (0.0, 0.0, 0.0)
    h_core.keyframe_insert(data_path="color", frame=1)
    h_core.keyframe_insert(data_path="rotation_euler", frame=1)

    herald_pad_glow.color = (0.08, 0.72, 1.0, 0.14)
    herald_pad_glow.keyframe_insert(data_path="color", frame=1)

    for n_obj in herald["ring_nodes"]:
        n_obj.color = (0.14, 0.82, 1.0, 0.25)
        n_obj.keyframe_insert(data_path="color", frame=1)

    h_const: set[int] = {1}
    cur_rot = [0.0, 0.0, 0.0]
    herald_notes.sort(key=lambda x: x["start_s"])

    for i, ev in enumerate(herald_notes):
        f0 = common.sec_to_frame(ev["start_s"], fps)
        f_end = min(total_frames, max(f0 + 2, common.sec_to_frame(ev["end_s"], fps)))
        next_f0 = common.sec_to_frame(herald_notes[i + 1]["start_s"], fps) if i + 1 < len(herald_notes) else total_frames + 10
        step = int(ev["step"])
        rgb = _blend_rgb((0.06, 0.78, 1.0), common.vivid_53edo_color(step), 0.52)
        peak_a = min(1.0, 0.78 + 0.25 * float(ev.get("vel", 0.65)))

        if f0 > 2:
            prev_f = f0 - 1
            h_core.color = h_idle
            h_core.keyframe_insert(data_path="color", frame=prev_f)
            herald_pad_glow.color = (0.08, 0.72, 1.0, 0.14)
            herald_pad_glow.keyframe_insert(data_path="color", frame=prev_f)
            for n_obj in herald["ring_nodes"]:
                n_obj.color = (0.14, 0.82, 1.0, 0.25)
                n_obj.keyframe_insert(data_path="color", frame=prev_f)
            h_const.add(prev_f)

            # Hold previous rotation clean right up to onset - 1, then leap crisply in 4 frames
            h_core.rotation_euler = tuple(cur_rot)
            h_core.keyframe_insert(data_path="rotation_euler", frame=prev_f)

        # Crystalline icosahedral symmetry rotation leap (clean 60° / 36° steps, zero jitter)
        cur_rot[0] += math.radians(36.0)
        cur_rot[1] += math.radians(24.0 * (1 if (i % 2 == 0) else -1))
        cur_rot[2] += math.radians(60.0)
        f_leap = min(total_frames, f0 + 4, next_f0 - 1)
        h_core.rotation_euler = tuple(cur_rot)
        h_core.keyframe_insert(data_path="rotation_euler", frame=f_leap)

        h_core.color = (*rgb, peak_a)
        h_core.keyframe_insert(data_path="color", frame=f0)
        herald_pad_glow.color = (*rgb, peak_a * 0.75)
        herald_pad_glow.keyframe_insert(data_path="color", frame=f0)
        for n_obj in herald["ring_nodes"]:
            n_obj.color = (*rgb, 0.96)
            n_obj.keyframe_insert(data_path="color", frame=f0)

        hold_end = min(f_end, next_f0 - 2)
        if hold_end > f0:
            h_core.color = (*rgb, peak_a * 0.88)
            h_core.keyframe_insert(data_path="color", frame=hold_end)

        rel_f = min(total_frames, hold_end + 2)
        if rel_f < next_f0:
            h_core.color = h_idle
            h_core.keyframe_insert(data_path="color", frame=rel_f)
            herald_pad_glow.color = (0.08, 0.72, 1.0, 0.14)
            herald_pad_glow.keyframe_insert(data_path="color", frame=rel_f)
            for n_obj in herald["ring_nodes"]:
                n_obj.color = (0.14, 0.82, 1.0, 0.25)
                n_obj.keyframe_insert(data_path="color", frame=rel_f)
            h_const.add(rel_f)

    common.set_constant_segment(h_core, "color", -1, h_const)
    common.set_constant_segment(herald_pad_glow, "color", -1, h_const)
    for n_obj in herald["ring_nodes"]:
        common.set_constant_segment(n_obj, "color", -1, h_const)

    # 3) Animate The Oracle (ai_architect): blazing violet/amethyst/gold on mirror-pair notes
    o_outer = oracle["outer_obj"]
    o_inner = oracle["inner_obj"]
    o_idle_outer = (0.54, 0.18, 0.92, 0.12)
    o_idle_inner = (0.96, 0.72, 0.22, 0.20)

    o_outer.color = o_idle_outer
    o_outer.rotation_euler = (0.0, 0.0, 0.0)
    o_outer.keyframe_insert(data_path="color", frame=1)
    o_outer.keyframe_insert(data_path="rotation_euler", frame=1)

    o_inner.color = o_idle_inner
    o_inner.rotation_euler = (0.0, 0.0, 0.0)
    o_inner.keyframe_insert(data_path="color", frame=1)
    o_inner.keyframe_insert(data_path="rotation_euler", frame=1)

    o_const: set[int] = {1}
    o_rot_z = 0.0
    oracle_notes.sort(key=lambda x: x["start_s"])

    for i, ev in enumerate(oracle_notes):
        f0 = common.sec_to_frame(ev["start_s"], fps)
        f_end = min(total_frames, max(f0 + 2, common.sec_to_frame(ev["end_s"], fps)))
        next_f0 = common.sec_to_frame(oracle_notes[i + 1]["start_s"], fps) if i + 1 < len(oracle_notes) else total_frames + 10
        step = int(ev["step"])
        rgb_outer = _blend_rgb((0.70, 0.22, 0.98), common.vivid_53edo_color(step), 0.45)
        peak_a = min(1.0, 0.82 + 0.22 * float(ev.get("vel", 0.68)))

        if f0 > 2:
            prev_f = f0 - 1
            o_outer.color = o_idle_outer
            o_inner.color = o_idle_inner
            o_outer.keyframe_insert(data_path="color", frame=prev_f)
            o_inner.keyframe_insert(data_path="color", frame=prev_f)
            o_outer.rotation_euler = (0.0, 0.0, o_rot_z)
            o_inner.rotation_euler = (0.0, 0.0, -o_rot_z)
            o_outer.keyframe_insert(data_path="rotation_euler", frame=prev_f)
            o_inner.keyframe_insert(data_path="rotation_euler", frame=prev_f)
            o_const.add(prev_f)

        o_rot_z += math.radians(90.0)
        f_leap = min(total_frames, f0 + 5, next_f0 - 1)
        o_outer.rotation_euler = (0.0, 0.0, o_rot_z)
        o_inner.rotation_euler = (0.0, 0.0, -o_rot_z)
        o_outer.keyframe_insert(data_path="rotation_euler", frame=f_leap)
        o_inner.keyframe_insert(data_path="rotation_euler", frame=f_leap)

        o_outer.color = (*rgb_outer, peak_a)
        o_inner.color = (1.0, 0.78, 0.26, min(1.0, peak_a + 0.08))
        o_outer.keyframe_insert(data_path="color", frame=f0)
        o_inner.keyframe_insert(data_path="color", frame=f0)

        hold_end = min(f_end, next_f0 - 2)
        if hold_end > f0:
            o_outer.color = (*rgb_outer, peak_a * 0.92)
            o_inner.color = (1.0, 0.78, 0.26, peak_a)
            o_outer.keyframe_insert(data_path="color", frame=hold_end)
            o_inner.keyframe_insert(data_path="color", frame=hold_end)

        rel_f = min(total_frames, hold_end + 2)
        if rel_f < next_f0:
            o_outer.color = o_idle_outer
            o_inner.color = o_idle_inner
            o_outer.keyframe_insert(data_path="color", frame=rel_f)
            o_inner.keyframe_insert(data_path="color", frame=rel_f)
            o_const.add(rel_f)

    common.set_constant_segment(o_outer, "color", -1, o_const)
    common.set_constant_segment(o_inner, "color", -1, o_const)

    # 4) Harmonic Mirror Beam connecting Herald & Oracle during simultaneous mirror_pairs resonance
    beam_obj = beam["beam_obj"]
    mid_ring = beam["mid_ring"]
    beam_obj.color = (0.45, 0.72, 1.0, 0.0)
    beam_obj.scale = (0.0, 0.0, 0.0)
    mid_ring.scale = (0.0, 0.0, 0.0)
    beam_obj.keyframe_insert(data_path="color", frame=1)
    beam_obj.keyframe_insert(data_path="scale", frame=1)
    mid_ring.keyframe_insert(data_path="scale", frame=1)

    overlaps = _compute_mirror_overlaps(herald_notes, oracle_notes)
    b_const: set[int] = {1}
    for i, ov in enumerate(overlaps):
        f0 = common.sec_to_frame(ov["start_s"], fps)
        f_end = min(total_frames, max(f0 + 2, common.sec_to_frame(ov["end_s"], fps)))
        next_f0 = common.sec_to_frame(overlaps[i + 1]["start_s"], fps) if i + 1 < len(overlaps) else total_frames + 10

        col_h = common.vivid_53edo_color(ov["h_step"])
        col_o = common.vivid_53edo_color(ov["o_step"])
        col_bridge = _blend_rgb(_blend_rgb(col_h, col_o, 0.5), (0.62, 0.84, 1.0), 0.35)

        if f0 > 2:
            prev_f = f0 - 1
            beam_obj.color = (*col_bridge, 0.0)
            beam_obj.scale = (0.0, 0.0, 0.0)
            mid_ring.scale = (0.0, 0.0, 0.0)
            beam_obj.keyframe_insert(data_path="color", frame=prev_f)
            beam_obj.keyframe_insert(data_path="scale", frame=prev_f)
            mid_ring.keyframe_insert(data_path="scale", frame=prev_f)
            b_const.add(prev_f)

        beam_obj.color = (*col_bridge, 0.94)
        beam_obj.scale = (1.0, 1.0, 1.0)
        mid_ring.scale = (1.0, 1.0, 1.0)
        beam_obj.keyframe_insert(data_path="color", frame=f0)
        beam_obj.keyframe_insert(data_path="scale", frame=f0)
        mid_ring.keyframe_insert(data_path="scale", frame=f0)

        hold_end = min(f_end, next_f0 - 2)
        if hold_end > f0:
            beam_obj.color = (*col_bridge, 0.90)
            beam_obj.scale = (1.0, 1.0, 1.0)
            mid_ring.scale = (1.0, 1.0, 1.0)
            beam_obj.keyframe_insert(data_path="color", frame=hold_end)
            beam_obj.keyframe_insert(data_path="scale", frame=hold_end)
            mid_ring.keyframe_insert(data_path="scale", frame=hold_end)

        rel_f = min(total_frames, hold_end + 1)
        if rel_f < next_f0:
            beam_obj.color = (*col_bridge, 0.0)
            beam_obj.scale = (0.0, 0.0, 0.0)
            mid_ring.scale = (0.0, 0.0, 0.0)
            beam_obj.keyframe_insert(data_path="color", frame=rel_f)
            beam_obj.keyframe_insert(data_path="scale", frame=rel_f)
            mid_ring.keyframe_insert(data_path="scale", frame=rel_f)
            b_const.add(rel_f)

    common.set_constant_segment(beam_obj, "color", -1, b_const)
    common.set_constant_segment(beam_obj, "scale", -1, b_const)
    common.set_constant_segment(mid_ring, "scale", -1, b_const)


def build_instrument(
    mats: dict[str, bpy.types.Material],
    timeline: dict[str, Any],
    *,
    collection_name: str = "HeraldOracleAI",
    anchor_location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    anchor_rotation_z_deg: float = 0.0,
    anchor_scale: float = 1.0,
) -> bpy.types.Object:
    """Build and animate The Herald & The Oracle AI Geodesic Polyhedra inside collection_name."""
    col = bpy.data.collections.new(collection_name)
    bpy.context.scene.collection.children.link(col)

    herald_pad_glow = build_mathematical_plinth(col, mats)
    herald = build_herald(col, mats)
    oracle = build_oracle(col, mats)
    beam = build_harmonic_mirror_beam(col, mats)

    folded_timeline = {
        **timeline,
        "notes": [
            {**n, "step": common.fold_step_to_range(int(n["step"]), STEP_MIN, STEP_MAX)}
            for n in timeline.get("notes", [])
        ],
    }
    animate_herald_oracle(folded_timeline, herald_pad_glow, herald, oracle, beam)
    return common.parent_collection_to_anchor(
        col,
        f"{collection_name}_Anchor",
        location=anchor_location,
        rotation_z_deg=anchor_rotation_z_deg,
        scale=anchor_scale,
    )


def _setup_camera(total_frames: int) -> None:
    target = (0.0, 0.0, 0.94)
    keyframes = [
        (1, (-1.65, -4.15, 1.82)),
        (max(2, total_frames // 2), (0.0, -4.32, 1.74)),
        (total_frames, (1.55, -4.12, 1.82)),
    ]
    common.setup_orbit_camera(target, keyframes, lens_mm=38.0, dof_fstop=6.8)


def build_scene(taa_samples: int = 16) -> dict[str, Any]:
    """Assemble the standalone 08_herald_oracle_ai showcase scene."""
    scene = common.reset_scene(fps=24, res_x=1920, res_y=1080, taa_samples=taa_samples)
    scene.view_settings.exposure = -0.32

    mats = common.create_studio_materials()
    common.build_concert_stage(mats, pedestal_radius=1.65, pedestal_height=PEDESTAL_Z, light_target_z=1.08)

    # Keep LuminousElement richly saturated under AgX (electric cyan & royal amethyst)
    lum = mats.get("LuminousElement")
    if lum and lum.use_nodes:
        for node in lum.node_tree.nodes:
            if node.type == "MATH" and node.operation == "MULTIPLY":
                node.inputs[1].default_value = 3.6

    # Position TopAccent & RimLight so GlossEbony plinth stays sleek black without specular blowout
    for lname, scale in (("KeyLight", 0.55), ("RimLight", 0.62), ("TopAccent", 0.38)):
        lobj = bpy.data.objects.get(lname)
        if lobj and lobj.data:
            lobj.data.energy *= scale
            if lname == "TopAccent":
                loc = Vector((0.0, -0.4, 5.2))
                lobj.location = loc
                lobj.rotation_euler = (Vector((0.0, 0.0, 1.08)) - loc).to_track_quat("-Z", "Y").to_euler()
                lobj.data.size = 4.2
                lobj.visible_glossy = False
            elif lname == "RimLight":
                loc = Vector((3.2, 3.8, 2.6))
                lobj.location = loc
                lobj.rotation_euler = (Vector((0.0, 0.0, 1.08)) - loc).to_track_quat("-Z", "Y").to_euler()
    eb_bsdf = mats["GlossEbony"].node_tree.nodes.get("Principled BSDF")
    if eb_bsdf is not None:
        eb_bsdf.inputs["Roughness"].default_value = 0.14
        eb_bsdf.inputs["Coat Roughness"].default_value = 0.08
    ped_bsdf = mats["PedestalWood"].node_tree.nodes.get("Principled BSDF")
    if ped_bsdf is not None:
        ped_bsdf.inputs["Roughness"].default_value = 0.56
        ped_bsdf.inputs["Coat Weight"].default_value = 0.04

    timeline = common.load_score_timeline(SCORE_PATH, WAV_PATH, fps=24)
    build_instrument(mats, timeline)
    _setup_camera(int(timeline["total_frames"]))
    return timeline


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    stills_only = "--stills-only" in argv
    render_vid = "--render-video" in argv

    taa = 8 if render_vid and not stills_only else 16
    timeline = build_scene(taa_samples=taa)
    common.save_blend(BLEND_PATH)
    print(f"[herald_oracle_ai] Saved blend: {BLEND_PATH}")

    if stills_only:
        frame_specs = [
            ("idle", 1),
            ("herald_scan", common.sec_to_frame(3.5, 24)),
            ("mirror_lock", common.sec_to_frame(10.5, 24)),
        ]
        rendered = common.render_diagnostic_stills(frame_specs, STILLS_DIR, "diag_ai")
        for p in rendered:
            print(f"[herald_oracle_ai] Diagnostic still: {p}")

    if render_vid:
        common.render_video(WEBM_PATH, WAV_PATH, int(timeline["total_frames"]), TMP_FRAMES_DIR, fps=24)


if __name__ == "__main__":
    main()
