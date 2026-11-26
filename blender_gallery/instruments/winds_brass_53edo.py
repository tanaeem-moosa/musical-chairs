"""The Micro-Valve Brass & Woodwind Consort (Clarinet, French Horn, Slide Trombone) — Blender 4.2 EEVEE Next."""

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

from blender_gallery import common  # noqa: E402

SCORE_PATH = REPO_ROOT / "scores" / "showcase_3d" / "06_winds_brass_53edo.json"
WAV_PATH = REPO_ROOT / "output" / "showcase_3d" / "06_winds_brass_53edo.wav"
OUT_DIR = REPO_ROOT / "output" / "showcase_3d"
BLEND_PATH = OUT_DIR / "06_winds_brass_53edo.blend"
WEBM_PATH = OUT_DIR / "06_winds_brass_53edo.webm"
TMP_FRAMES_DIR = Path("/tmp/frames_winds_brass_53edo")

PEDESTAL_Z = 0.09
CLARINET_STEP_MIN = -26
CLARINET_STEP_MAX = 60
HORN_STEP_MIN = -44
HORN_STEP_MAX = 22
TROMBONE_STEP_MIN = -53
TROMBONE_STEP_MAX = 0


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _make_mesh_obj(
    col: bpy.types.Collection,
    name: str,
    bm: bmesh.types.BMesh,
    mats: list[bpy.types.Material],
    smooth: bool = True,
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    if smooth:
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    for mat in mats:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    return obj


def _new_empty(
    col: bpy.types.Collection,
    name: str,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation_euler: tuple[float, float, float] = (0.0, 0.0, 0.0),
    parent: bpy.types.Object | None = None,
) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.05
    obj.location = location
    obj.rotation_euler = rotation_euler
    col.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def _add_bevel(obj: bpy.types.Object, width: float = 0.002, segments: int = 2) -> None:
    bev = obj.modifiers.new("Bevel", "BEVEL")
    bev.width = width
    bev.segments = segments
    bev.limit_method = "ANGLE"
    bev.angle_limit = math.radians(32.0)


def _loft_rings(
    bm: bmesh.types.BMesh,
    rings: list[list[bmesh.types.BMVert]],
    cap_start: bool = True,
    cap_end: bool = True,
    mat_idx: int = 0,
) -> None:
    n_seg = len(rings[0])
    for i in range(len(rings) - 1):
        r0 = rings[i]
        r1 = rings[i + 1]
        for j in range(n_seg):
            jn = (j + 1) % n_seg
            f = bm.faces.new((r0[j], r0[jn], r1[jn], r1[j]))
            f.material_index = mat_idx
    if cap_start:
        f0 = bm.faces.new(list(reversed(rings[0])))
        f0.material_index = mat_idx
    if cap_end:
        f1 = bm.faces.new(rings[-1])
        f1.material_index = mat_idx


def _add_tube_along_points(
    bm: bmesh.types.BMesh,
    pts: list[Vector],
    radii: list[float],
    n_sides: int = 16,
    cap_start: bool = True,
    cap_end: bool = True,
    mat_idx: int = 0,
) -> None:
    rings: list[list[bmesh.types.BMVert]] = []
    prev_n = Vector((1.0, 0.0, 0.0))
    for i, p in enumerate(pts):
        if i == 0:
            tangent = (pts[1] - pts[0]).normalized()
        elif i == len(pts) - 1:
            tangent = (pts[-1] - pts[-2]).normalized()
        else:
            tangent = (pts[i + 1] - pts[i - 1]).normalized()
        if abs(tangent.dot(prev_n)) > 0.96:
            alt = Vector((0.0, 1.0, 0.0)) if abs(tangent.y) < 0.9 else Vector((0.0, 0.0, 1.0))
            n_vec = tangent.cross(alt).normalized()
        else:
            n_vec = (prev_n - tangent * prev_n.dot(tangent)).normalized()
        b_vec = tangent.cross(n_vec).normalized()
        prev_n = n_vec

        r = radii[i]
        ring = []
        for k in range(n_sides):
            ang = 2.0 * math.pi * k / n_sides
            offset = (n_vec * math.cos(ang) + b_vec * math.sin(ang)) * r
            ring.append(bm.verts.new(p + offset))
        rings.append(ring)

    _loft_rings(bm, rings, cap_start=cap_start, cap_end=cap_end, mat_idx=mat_idx)


def _add_cylinder_between(
    bm: bmesh.types.BMesh,
    p0: Vector,
    p1: Vector,
    r0: float,
    r1: float,
    n_sides: int = 16,
    mat_idx: int = 0,
) -> None:
    _add_tube_along_points(bm, [p0, p1], [r0, r1], n_sides=n_sides, mat_idx=mat_idx)


def _add_flared_bell(
    bm: bmesh.types.BMesh,
    center_base: Vector,
    axis_dir: Vector,
    length: float,
    r_throat: float,
    r_rim: float,
    n_len: int = 16,
    n_sides: int = 28,
    mat_idx: int = 0,
    wall_thick: float = 0.0022,
) -> None:
    """Build a hollow flared brass/woodwind bell with rolled outer rim."""
    axis = axis_dir.normalized()
    ref = Vector((1.0, 0.0, 0.0)) if abs(axis.x) < 0.9 else Vector((0.0, 1.0, 0.0))
    u_vec = axis.cross(ref).normalized()
    v_vec = axis.cross(u_vec).normalized()

    outer_rings: list[list[bmesh.types.BMVert]] = []
    inner_rings: list[list[bmesh.types.BMVert]] = []
    for i in range(n_len + 1):
        t = i / float(n_len)
        # Exponential acoustic flare profile
        flare = (math.exp(3.4 * t) - 1.0) / (math.exp(3.4) - 1.0)
        r_out = r_throat + (r_rim - r_throat) * flare
        r_in = max(0.002, r_out - wall_thick * (1.0 + 0.6 * t))
        c = center_base + axis * (t * length)
        ro = []
        ri = []
        for k in range(n_sides):
            ang = 2.0 * math.pi * k / n_sides
            dir_r = u_vec * math.cos(ang) + v_vec * math.sin(ang)
            ro.append(bm.verts.new(c + dir_r * r_out))
            ri.append(bm.verts.new(c + dir_r * r_in))
        outer_rings.append(ro)
        inner_rings.append(ri)

    # Outer wall, rim bridge, and inner bell throat
    _loft_rings(bm, outer_rings, cap_start=False, cap_end=False, mat_idx=mat_idx)
    _loft_rings(bm, [outer_rings[-1], inner_rings[-1]], cap_start=False, cap_end=False, mat_idx=mat_idx)
    _loft_rings(bm, list(reversed(inner_rings)), cap_start=False, cap_end=False, mat_idx=mat_idx)


def _build_floor_stand_base(
    bm: bmesh.types.BMesh,
    radius: float = 0.145,
) -> None:
    """Add a sleek GlossEbony + BrushedGold floor disk grounded flush at local z=0 (world z=0.09)."""
    _add_cylinder_between(bm, Vector((0.0, 0.0, 0.0)), Vector((0.0, 0.0, 0.018)), radius, radius * 0.90, n_sides=36, mat_idx=0)
    _add_cylinder_between(bm, Vector((0.0, 0.0, 0.018)), Vector((0.0, 0.0, 0.025)), radius * 0.91, radius * 0.85, n_sides=36, mat_idx=1)
    _add_cylinder_between(bm, Vector((0.0, 0.0, 0.025)), Vector((0.0, 0.0, 0.036)), radius * 0.34, radius * 0.24, n_sides=24, mat_idx=0)


# ---------------------------------------------------------------------------
# 1) Left Instrument: 53-Key Clarinet
# ---------------------------------------------------------------------------

def _build_clarinet_assembly(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build 53-Key Clarinet on a grounded stand + 16 articulated SilverMetal key cups + bell aura."""
    root = _new_empty(
        col,
        "ClarinetStandRoot",
        location=(-0.58, -0.05, PEDESTAL_Z),
        rotation_euler=(0.0, 0.0, math.radians(16.0)),
    )

    # Sleek ebony & brass floor stand (grounded at z_local=0 -> world z=0.09)
    bm_st = bmesh.new()
    _build_floor_stand_base(bm_st, radius=0.145)
    # Angled central post + twin U-yokes supporting clarinet tilted 26 deg forward-left so bell opens into clean air
    _add_cylinder_between(bm_st, Vector((0.0, 0.0, 0.034)), Vector((0.0, 0.04, 0.56)), 0.011, 0.0085, n_sides=14, mat_idx=1)
    # Lower cradle arm (around z=0.28)
    _add_tube_along_points(
        bm_st,
        [Vector((-0.038, -0.04, 0.27)), Vector((0.0, 0.02, 0.26)), Vector((0.038, -0.04, 0.27))],
        [0.0065, 0.0075, 0.0065],
        n_sides=10,
        mat_idx=1,
    )
    # Upper cradle arm (around z=0.56)
    _add_tube_along_points(
        bm_st,
        [Vector((-0.028, -0.01, 0.57)), Vector((0.0, 0.04, 0.56)), Vector((0.028, -0.01, 0.57))],
        [0.006, 0.007, 0.006],
        n_sides=10,
        mat_idx=1,
    )
    st_obj = _make_mesh_obj(col, "ClarinetFloorStand", bm_st, [mats["GlossEbony"], mats["BrushedGold"]], smooth=True)
    _add_bevel(st_obj, width=0.0015, segments=2)
    st_obj.parent = root

    # Clarinet body frame tilted cleanly forward (-Y) by 20 deg so keys & bell face camera
    body_pivot = _new_empty(
        col,
        "ClarinetBodyPivot",
        location=(0.0, -0.01, 0.22),
        rotation_euler=(math.radians(-20.0), 0.0, 0.0),
        parent=root,
    )

    # Bore runs along local Z from z=0.04 (bell mouth) to z=0.72 (mouthpiece tip)
    bm_cl = bmesh.new()
    # Flared Grenadilla Bell (z=0.04 .. 0.16) opening downward-forward into clean air above pedestal
    _add_flared_bell(
        bm_cl,
        center_base=Vector((0.0, 0.0, 0.16)),
        axis_dir=Vector((0.0, 0.0, -1.0)),
        length=0.12,
        r_throat=0.0185,
        r_rim=0.046,
        n_len=14,
        n_sides=28,
        mat_idx=0,
        wall_thick=0.003,
    )
    # PolishedBrass bell trim ring
    _add_cylinder_between(bm_cl, Vector((0.0, 0.0, 0.040)), Vector((0.0, 0.0, 0.050)), 0.0472, 0.0445, n_sides=28, mat_idx=1)

    # Lower joint, upper joint, barrel (Grenadilla = slot 0) + Silver tenon rings (slot 2)
    bore_sections = [
        (0.16, 0.36, 0.0185, 0.0172, 0),
        (0.36, 0.368, 0.0188, 0.0188, 2),  # middle silver tenon ring
        (0.368, 0.555, 0.0172, 0.0162, 0),
        (0.555, 0.563, 0.0180, 0.0180, 2),  # barrel ring bottom
        (0.563, 0.625, 0.0188, 0.0178, 0),  # barrel
        (0.625, 0.632, 0.0182, 0.0182, 2),  # barrel ring top
    ]
    for z0, z1, r0, r1, midx in bore_sections:
        _add_cylinder_between(bm_cl, Vector((0.0, 0.0, z0)), Vector((0.0, 0.0, z1)), r0, r1, n_sides=24, mat_idx=midx)

    # Mouthpiece beak tapering toward tip (z=0.632 .. 0.715)
    mp_rings: list[list[bmesh.types.BMVert]] = []
    for k in range(7):
        u = k / 6.0
        z = 0.632 + u * 0.083
        rx = 0.0155 * (1.0 - 0.15 * u)
        ry = 0.0155 * (1.0 - 0.74 * (u ** 1.35))
        ring = []
        for s in range(18):
            ang = 2.0 * math.pi * s / 18
            ring.append(bm_cl.verts.new((rx * math.cos(ang), ry * math.sin(ang), z)))
        mp_rings.append(ring)
    _loft_rings(bm_cl, mp_rings, cap_start=True, cap_end=True, mat_idx=3)

    # IvoryKey Reed + PolishedBrass Ligature
    _add_cylinder_between(bm_cl, Vector((0.0, -0.014, 0.655)), Vector((0.0, -0.006, 0.712)), 0.0085, 0.007, n_sides=8, mat_idx=4)
    _add_cylinder_between(bm_cl, Vector((0.0, 0.0, 0.640)), Vector((0.0, 0.0, 0.665)), 0.0168, 0.0158, n_sides=20, mat_idx=1)

    # Long SilverMetal vertical keywork side-rods framing the bore
    for side_x, z_lo, z_hi in ((-0.022, 0.19, 0.54), (0.022, 0.21, 0.53), (-0.015, 0.37, 0.55)):
        _add_cylinder_between(
            bm_cl,
            Vector((side_x, -0.014, z_lo)),
            Vector((side_x, -0.014, z_hi)),
            0.0022,
            0.0022,
            n_sides=8,
            mat_idx=2,
        )

    bmesh.ops.recalc_face_normals(bm_cl, faces=bm_cl.faces)
    cl_obj = _make_mesh_obj(
        col,
        "ClarinetBody",
        bm_cl,
        [mats["Grenadilla"], mats["PolishedBrass"], mats["SilverMetal"], mats["GlossEbony"], mats["IvoryKey"]],
        smooth=True,
    )
    cl_obj.parent = body_pivot

    # 16 Articulated SilverMetal Key Cups + Luminous tone-hole jewel rings along the front (-Y) face
    key_cups: list[dict[str, Any]] = []
    n_keys = 16
    for k_i in range(n_keys):
        u = k_i / float(n_keys - 1)
        zk = 0.535 - u * 0.345
        # Alternate slightly left/right for rich 53-key microtonal cluster silhouette
        ang_offset = 0.24 * math.sin(k_i * 1.45)
        r_bore = 0.0170 + 0.0014 * u
        hinge_side = -1.0 if (k_i % 2 == 0) else 1.0
        hinge_x = hinge_side * 0.021
        cup_x = math.sin(ang_offset) * (r_bore + 0.003)
        cup_y = -math.cos(ang_offset) * (r_bore + 0.003)

        # Tone-hole luminous glow ring flush on the Grenadilla bore
        bm_th = bmesh.new()
        _add_cylinder_between(
            bm_th,
            Vector((cup_x, cup_y + 0.003, zk)),
            Vector((cup_x, cup_y - 0.001, zk)),
            0.0072,
            0.0068,
            n_sides=14,
            mat_idx=0,
        )
        th_obj = _make_mesh_obj(col, f"ClarinetToneHole_{k_i:02d}", bm_th, [mats["LuminousElement"]], smooth=True)
        th_obj.parent = body_pivot
        th_obj.color = (*common.vivid_53edo_color(k_i * 3), 0.02)

        # Articulated key cup pivoted at its hinge post (hinge_x, cup_y - 0.003, zk)
        cup_pivot = _new_empty(
            col,
            f"ClarinetKeyPivot_{k_i:02d}",
            location=(hinge_x, cup_y - 0.003, zk),
            parent=body_pivot,
        )
        bm_kc = bmesh.new()
        rel_cx = cup_x - hinge_x
        # Lever arm from hinge to cup
        _add_cylinder_between(
            bm_kc,
            Vector((0.0, 0.0, 0.0)),
            Vector((rel_cx, 0.0, 0.0)),
            0.0018,
            0.0018,
            n_sides=8,
            mat_idx=0,
        )
        # Beveled SilverMetal key cup over the tone hole
        _add_cylinder_between(
            bm_kc,
            Vector((rel_cx, 0.002, 0.0)),
            Vector((rel_cx, -0.0035, 0.0)),
            0.0082,
            0.0068,
            n_sides=16,
            mat_idx=0,
        )
        kc_obj = _make_mesh_obj(col, f"ClarinetKeyCup_{k_i:02d}", bm_kc, [mats["SilverMetal"]], smooth=True)
        kc_obj.parent = cup_pivot

        key_cups.append({
            "pivot": cup_pivot,
            "hinge_side": hinge_side,
            "tone_hole": th_obj,
        })

    # Luminous Breath / Acoustic Aura Rings emerging softly from Clarinet Bell (hidden at scale 0 when idle)
    aura_objs: list[bpy.types.Object] = []
    # 1) Soft Inner Bell-Throat Glow Ring
    bm_br = bmesh.new()
    _add_flared_bell(
        bm_br,
        center_base=Vector((0.0, 0.0, 0.072)),
        axis_dir=Vector((0.0, 0.0, -1.0)),
        length=0.026,
        r_throat=0.026,
        r_rim=0.041,
        n_len=6,
        n_sides=28,
        mat_idx=0,
        wall_thick=0.0018,
    )
    bell_ring = _make_mesh_obj(col, "ClarinetBellAuraRing", bm_br, [mats["LuminousElement"]], smooth=True)
    bell_ring.parent = body_pivot
    bell_ring.color = (0.2, 0.8, 0.5, 0.0)
    bell_ring.scale = (0.0, 0.0, 0.0)
    aura_objs.append(bell_ring)

    # 2) Twin Delicate Acoustic Breath Wave Halos floating cleanly below the bell mouth
    for ring_idx, (z_ring, r_ring, tube_r) in enumerate(((0.015, 0.056, 0.0032), (-0.022, 0.076, 0.0026))):
        bm_halo = bmesh.new()
        n_seg_h = 32
        pts_h = [
            Vector((r_ring * math.cos(2.0 * math.pi * k / n_seg_h), r_ring * math.sin(2.0 * math.pi * k / n_seg_h), z_ring))
            for k in range(n_seg_h + 1)
        ]
        _add_tube_along_points(bm_halo, pts_h, [tube_r] * len(pts_h), n_sides=8, cap_start=False, cap_end=False, mat_idx=0)
        halo_obj = _make_mesh_obj(col, f"ClarinetBreathHalo_{ring_idx}", bm_halo, [mats["LuminousElement"]], smooth=True)
        halo_obj.parent = body_pivot
        halo_obj.color = (0.2, 0.8, 0.5, 0.0)
        halo_obj.scale = (0.0, 0.0, 0.0)
        aura_objs.append(halo_obj)

    return {
        "key_cups": key_cups,
        "aura_objs": aura_objs,
    }


# ---------------------------------------------------------------------------
# 2) Center Instrument: 53-Valve French Horn
# ---------------------------------------------------------------------------

def _build_french_horn_assembly(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build 53-Valve French Horn on grounded ebony/brass cradle with 4 rotary paddles & bell flare."""
    root = _new_empty(col, "FrenchHornStandRoot", location=(0.0, 0.14, PEDESTAL_Z))

    # Grounded ebony & brass floor cradle stand (z_local=0 -> world z=0.09)
    bm_st = bmesh.new()
    _build_floor_stand_base(bm_st, radius=0.165)
    _add_cylinder_between(bm_st, Vector((0.0, 0.0, 0.034)), Vector((0.0, 0.02, 0.42)), 0.013, 0.010, n_sides=16, mat_idx=1)
    # Cradle yoke hugging bottom of main brass coil around z=0.44
    _add_tube_along_points(
        bm_st,
        [
            Vector((-0.11, -0.02, 0.48)),
            Vector((-0.055, 0.01, 0.435)),
            Vector((0.0, 0.02, 0.42)),
            Vector((0.055, 0.01, 0.435)),
            Vector((0.11, -0.02, 0.48)),
        ],
        [0.008, 0.008, 0.010, 0.008, 0.008],
        n_sides=12,
        mat_idx=1,
    )
    st_obj = _make_mesh_obj(col, "FrenchHornStand", bm_st, [mats["GlossEbony"], mats["BrushedGold"]], smooth=True)
    _add_bevel(st_obj, width=0.0015, segments=2)
    st_obj.parent = root

    # Horn body pivot centered at z_local=0.67, rotated slightly so flared bell faces forward-right cleanly
    horn_pivot = _new_empty(
        col,
        "FrenchHornBodyPivot",
        location=(0.0, 0.0, 0.67),
        rotation_euler=(math.radians(-8.0), 0.0, math.radians(-18.0)),
        parent=root,
    )

    bm_hr = bmesh.new()
    # Main coiled horn loop in X-Z plane (wrapping ~1.35 turns from leadpipe into sweeping flared bell)
    loop_r = 0.205
    n_coil = 56
    coil_pts: list[Vector] = []
    coil_rads: list[float] = []
    for i in range(n_coil):
        u = i / float(n_coil - 1)
        ang = math.radians(110.0) + u * math.radians(410.0)
        # Spiral slightly outward into the bell section
        rad_here = loop_r * (0.94 + 0.14 * (u ** 2))
        y_off = -0.022 + 0.055 * u
        x = rad_here * math.cos(ang)
        z = rad_here * math.sin(ang)
        coil_pts.append(Vector((x, y_off, z)))
        # Conical expansion from 6.5mm leadpipe to 36mm bell throat
        coil_rads.append(0.0068 + 0.029 * (u ** 2.2))
    _add_tube_along_points(bm_hr, coil_pts, coil_rads, n_sides=18, mat_idx=0)

    # Flared Bell sweeping off the final tangent of the coil
    bell_base = coil_pts[-1]
    bell_dir = (coil_pts[-1] - coil_pts[-2]).normalized() + Vector((0.28, -0.45, -0.15))
    bell_dir.normalize()
    _add_flared_bell(
        bm_hr,
        center_base=bell_base - bell_dir * 0.01,
        axis_dir=bell_dir,
        length=0.22,
        r_throat=0.036,
        r_rim=0.162,
        n_len=16,
        n_sides=34,
        mat_idx=0,
        wall_thick=0.0024,
    )

    # Inner tuning slide crooks & bracing struts soldered cleanly to outer coil and valve cluster
    for k in range(3):
        ang0 = math.radians(-25.0 + k * 75.0)
        ang1 = ang0 + math.radians(52.0)
        crook_pts = []
        crook_rads = []
        for s in range(14):
            t = s / 13.0
            a = ang0 + t * (ang1 - ang0)
            rc = 0.140 + 0.015 * math.sin(math.pi * t)
            crook_pts.append(Vector((rc * math.cos(a), 0.012 * (k - 1), rc * math.sin(a))))
            crook_rads.append(0.0070)
        _add_tube_along_points(bm_hr, crook_pts, crook_rads, n_sides=12, mat_idx=0)
        _add_cylinder_between(bm_hr, crook_pts[2], crook_pts[3], 0.0086, 0.0086, n_sides=12, mat_idx=1)
        # Connect both ends of each crook cleanly outward to the main horn ring + brace inward
        for end_pt in (crook_pts[0], crook_pts[-1]):
            ang_e = math.atan2(end_pt.z, end_pt.x)
            outer_pt = Vector((loop_r * 0.98 * math.cos(ang_e), end_pt.y * 0.4, loop_r * 0.98 * math.sin(ang_e)))
            _add_cylinder_between(bm_hr, end_pt, outer_pt, 0.0068, 0.0068, n_sides=10, mat_idx=0)

    # Curved Leadpipe + SilverMetal Mouthpiece on upper-left side
    lp_pts = [
        Vector((-0.14, -0.02, 0.15)),
        Vector((-0.24, -0.05, 0.12)),
        Vector((-0.30, -0.09, 0.06)),
    ]
    _add_tube_along_points(bm_hr, lp_pts, [0.0068, 0.0058, 0.0050], n_sides=12, mat_idx=0)
    _add_cylinder_between(bm_hr, lp_pts[-1], lp_pts[-1] + Vector((-0.025, -0.022, -0.015)), 0.0052, 0.0105, n_sides=14, mat_idx=1)

    # 4 Rotary Valve Casings arranged cleanly across the center-left cluster + manifold tubes
    valve_centers = [
        Vector((-0.075, -0.020, 0.035)),
        Vector((-0.042, -0.020, 0.012)),
        Vector((-0.008, -0.020, -0.011)),
        Vector((0.026, -0.020, -0.034)),
    ]
    # Connect valve cluster manifold between casings and out to leadpipe & main loop
    _add_cylinder_between(bm_hr, lp_pts[0], valve_centers[0], 0.0066, 0.0066, n_sides=10, mat_idx=0)
    _add_cylinder_between(bm_hr, valve_centers[0], valve_centers[-1], 0.0075, 0.0075, n_sides=12, mat_idx=0)
    _add_cylinder_between(bm_hr, valve_centers[-1], Vector((0.145, 0.0, -0.125)), 0.0068, 0.0068, n_sides=10, mat_idx=0)
    for vc in valve_centers:
        # Radial brass valve tubing loop extending behind each casing
        _add_tube_along_points(
            bm_hr,
            [
                vc + Vector((0.0, 0.012, 0.0)),
                vc + Vector((0.028, 0.028, 0.038)),
                vc + Vector((0.048, 0.022, 0.020)),
                vc + Vector((0.012, 0.010, -0.004)),
            ],
            [0.0062, 0.0062, 0.0062, 0.0062],
            n_sides=10,
            mat_idx=0,
        )
        _add_cylinder_between(
            bm_hr,
            vc + Vector((0.0, 0.018, 0.0)),
            vc + Vector((0.0, -0.018, 0.0)),
            0.0155,
            0.0155,
            n_sides=18,
            mat_idx=2,
        )
        _add_cylinder_between(
            bm_hr,
            vc + Vector((0.0, -0.018, 0.0)),
            vc + Vector((0.0, -0.024, 0.0)),
            0.012,
            0.009,
            n_sides=16,
            mat_idx=1,
        )

    bmesh.ops.recalc_face_normals(bm_hr, faces=bm_hr.faces)
    hr_obj = _make_mesh_obj(
        col,
        "FrenchHornBody",
        bm_hr,
        [mats["PolishedBrass"], mats["SilverMetal"], mats["BrushedGold"]],
        smooth=True,
    )
    hr_obj.parent = horn_pivot

    # 4 Articulated Rotary Valve Paddles (depress on french_horn notes)
    paddles: list[bpy.types.Object] = []
    for v_i, vc in enumerate(valve_centers):
        piv = _new_empty(
            col,
            f"HornValvePaddlePivot_{v_i}",
            location=(vc.x - 0.012, vc.y - 0.026, vc.z + 0.028),
            parent=horn_pivot,
        )
        bm_pd = bmesh.new()
        # Lever arm + ergonomic curved finger spatula
        _add_cylinder_between(bm_pd, Vector((0.0, 0.0, 0.0)), Vector((0.010, -0.018, -0.024)), 0.0022, 0.0022, n_sides=8, mat_idx=0)
        _add_cylinder_between(
            bm_pd,
            Vector((0.006, -0.020, -0.026)),
            Vector((0.018, -0.022, -0.028)),
            0.0075,
            0.0068,
            n_sides=14,
            mat_idx=0,
        )
        pd_obj = _make_mesh_obj(col, f"HornValvePaddle_{v_i}", bm_pd, [mats["SilverMetal"]], smooth=True)
        pd_obj.parent = piv
        paddles.append(piv)

    # Warm Luminous Bell Flare centered at bell mouth origin so scaling is purely radial
    rim_c_h = bell_base + bell_dir * 0.195
    horn_flare = _new_empty(col, "FrenchHornBellFlarePivot", location=tuple(rim_c_h), parent=horn_pivot)
    bm_bf = bmesh.new()
    ref_h = Vector((1.0, 0.0, 0.0)) if abs(bell_dir.x) < 0.9 else Vector((0.0, 1.0, 0.0))
    u_h = bell_dir.cross(ref_h).normalized()
    v_h = bell_dir.cross(u_h).normalized()
    for d_off, r_ring, t_rad in ((-0.005, 0.128, 0.0055), (0.028, 0.148, 0.0036)):
        c_ring = bell_dir * d_off
        pts_ring = [
            c_ring + (u_h * math.cos(2.0 * math.pi * k / 32) + v_h * math.sin(2.0 * math.pi * k / 32)) * r_ring
            for k in range(33)
        ]
        _add_tube_along_points(bm_bf, pts_ring, [t_rad] * len(pts_ring), n_sides=10, cap_start=False, cap_end=False, mat_idx=0)
    horn_flare_mesh = _make_mesh_obj(col, "FrenchHornBellFlare", bm_bf, [mats["LuminousElement"]], smooth=True)
    horn_flare_mesh.parent = horn_flare
    horn_flare_mesh.color = (0.96, 0.62, 0.14, 0.0)
    horn_flare_mesh.scale = (0.0, 0.0, 0.0)

    return {
        "paddles": paddles,
        "bell_flare": horn_flare_mesh,
    }


# ---------------------------------------------------------------------------
# 3) Right Instrument: 53-Position Slide Trombone
# ---------------------------------------------------------------------------

def _build_trombone_assembly(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build 53-Position Slide Trombone on floor stand with telescoping outer U-slide & bell glow."""
    root = _new_empty(
        col,
        "TromboneStandRoot",
        location=(0.58, -0.04, PEDESTAL_Z),
        rotation_euler=(0.0, 0.0, math.radians(-20.0)),
    )

    # Grounded ebony & brass floor stand (z_local=0 -> world z=0.09)
    bm_st = bmesh.new()
    _build_floor_stand_base(bm_st, radius=0.155)
    _add_cylinder_between(bm_st, Vector((0.0, 0.0, 0.034)), Vector((0.0, 0.0, 0.63)), 0.0115, 0.0085, n_sides=16, mat_idx=1)
    # Conical padded bell-support cone at top of stand (z=0.62..0.70) + lower brace cradle (z=0.45)
    _add_cylinder_between(bm_st, Vector((0.0, 0.0, 0.62)), Vector((0.0, -0.02, 0.70)), 0.018, 0.034, n_sides=18, mat_idx=0)
    _add_tube_along_points(
        bm_st,
        [Vector((-0.04, -0.05, 0.47)), Vector((0.0, 0.0, 0.45)), Vector((0.04, -0.05, 0.47))],
        [0.006, 0.007, 0.006],
        n_sides=10,
        mat_idx=1,
    )
    st_obj = _make_mesh_obj(col, "TromboneFloorStand", bm_st, [mats["GlossEbony"], mats["BrushedGold"]], smooth=True)
    _add_bevel(st_obj, width=0.0015, segments=2)
    st_obj.parent = root

    # SlideAxis frame: tilted 24 deg forward (-Y) so slide extends cleanly downward-forward above pedestal
    slide_axis = _new_empty(
        col,
        "TromboneSlideAxis",
        location=(0.0, -0.02, 0.69),
        rotation_euler=(math.radians(-24.0), 0.0, 0.0),
        parent=root,
    )

    # In TromboneSlideAxis local coordinates:
    # +Z goes upward toward bell mouth & tuning counterweight; -Z goes downward along slide tubes!
    # Parallel inner slide tube X positions: x_left = -0.036, x_right = +0.036
    x_in = 0.036
    bm_tb = bmesh.new()

    # 1) Inner chrome slide tubes (SilverMetal = slot 1), extending from z=+0.08 down to z=-0.46
    for sx in (-x_in, x_in):
        _add_cylinder_between(bm_tb, Vector((sx, 0.0, 0.08)), Vector((sx, 0.0, -0.46)), 0.0056, 0.0056, n_sides=14, mat_idx=1)

    # Mouthpiece branch & leadpipe on upper-left tube (+Z end)
    _add_cylinder_between(bm_tb, Vector((-x_in, 0.0, 0.08)), Vector((-x_in - 0.012, -0.02, 0.16)), 0.0062, 0.0095, n_sides=14, mat_idx=1)

    # 2) Coiled Bell Section & Rear Tuning Slide Bow (PolishedBrass = slot 0, BrushedGold = slot 2)
    # Rear tuning slide U-loop arching upward behind (+Y) from z=0.04 to z=0.38
    rear_pts: list[Vector] = []
    rear_rads: list[float] = []
    # Rise along x=+x_in up into rear U-turn at z=0.38, y=+0.055, then descend to bell bow
    for i in range(18):
        t = i / 17.0
        ang = math.pi * t
        px = x_in * math.cos(ang) * 0.95
        pz = 0.18 + 0.19 * math.sin(ang)
        py = 0.045 + 0.015 * math.sin(ang)
        rear_pts.append(Vector((px, py, pz)))
        rear_rads.append(0.0072 + 0.0028 * t)
    _add_tube_along_points(bm_tb, rear_pts, rear_rads, n_sides=14, mat_idx=0)
    # Connect right inner slide joint to rear tuning loop
    _add_cylinder_between(bm_tb, Vector((x_in, 0.0, 0.06)), rear_pts[0], 0.0074, 0.0072, n_sides=14, mat_idx=0)

    # BrushedGold counterweight medallion on rear bow
    _add_cylinder_between(
        bm_tb,
        Vector((0.0, 0.052, 0.375)),
        Vector((0.0, 0.070, 0.375)),
        0.028,
        0.026,
        n_sides=24,
        mat_idx=2,
    )

    # Bell throat ascending smoothly from rear loop forward-upward to flared bell opening toward camera (-Y/+Z)
    bell_pts = [
        rear_pts[-1],
        Vector((-x_in * 0.95, 0.032, 0.04)),
        Vector((-x_in * 0.85, -0.008, 0.12)),
        Vector((-x_in * 0.72, -0.042, 0.25)),
        Vector((-x_in * 0.58, -0.072, 0.36)),
    ]
    _add_tube_along_points(bm_tb, bell_pts, [0.010, 0.012, 0.015, 0.019, 0.024], n_sides=18, mat_idx=0)

    bell_base = bell_pts[-1]
    bell_dir = Vector((-0.18, -0.78, 0.60)).normalized()
    _add_flared_bell(
        bm_tb,
        center_base=bell_base - bell_dir * 0.01,
        axis_dir=bell_dir,
        length=0.19,
        r_throat=0.024,
        r_rim=0.112,
        n_len=16,
        n_sides=32,
        mat_idx=0,
        wall_thick=0.0022,
    )
    # BrushedGold bell rim trim ring
    rim_c = bell_base + bell_dir * 0.178
    _add_cylinder_between(bm_tb, rim_c - bell_dir * 0.005, rim_c + bell_dir * 0.003, 0.1125, 0.1135, n_sides=32, mat_idx=2)

    # Structural cross-braces
    _add_cylinder_between(bm_tb, Vector((-x_in, 0.0, 0.05)), Vector((x_in, 0.0, 0.05)), 0.0045, 0.0045, n_sides=10, mat_idx=2)
    _add_cylinder_between(bm_tb, Vector((-x_in * 0.82, -0.02, 0.16)), Vector((0.0, 0.045, 0.22)), 0.004, 0.004, n_sides=10, mat_idx=2)

    bmesh.ops.recalc_face_normals(bm_tb, faces=bm_tb.faces)
    tb_obj = _make_mesh_obj(
        col,
        "TromboneBellSection",
        bm_tb,
        [mats["PolishedBrass"], mats["SilverMetal"], mats["BrushedGold"]],
        smooth=True,
    )
    tb_obj.parent = slide_axis

    # 3) Telescoping Outer U-Slide (translates smoothly along local Z of TromboneSlideAxis!)
    # When outer_slide.location.z = 0 (pos=0), top of outer slide sits at z=+0.02 and bow bottom at z=-0.34.
    # When pos=1.0, outer_slide.location.z = -0.26 -> bow bottom at z=-0.60, still overlapping inner tubes (-0.46)!
    # Wait: at pos=1.0, outer slide top is at z=+0.02 - 0.26 = -0.24, while inner tubes go down to -0.46 -> 0.22m clean overlap!
    bm_os = bmesh.new()
    for sx in (-x_in, x_in):
        _add_cylinder_between(bm_os, Vector((sx, 0.0, 0.02)), Vector((sx, 0.0, -0.32)), 0.0076, 0.0074, n_sides=16, mat_idx=0)
        # BrushedGold slide collar sleeves at top
        _add_cylinder_between(bm_os, Vector((sx, 0.0, 0.025)), Vector((sx, 0.0, -0.005)), 0.0088, 0.0088, n_sides=16, mat_idx=1)
    # Cross-brace at top of outer slide
    _add_cylinder_between(bm_os, Vector((-x_in, 0.0, -0.01)), Vector((x_in, 0.0, -0.01)), 0.0048, 0.0048, n_sides=10, mat_idx=1)
    # Bottom U-bow connecting the two outer tubes
    u_pts: list[Vector] = []
    u_rads: list[float] = []
    for k in range(15):
        t = k / 14.0
        ang = math.pi + math.pi * t
        ux = x_in * math.cos(ang)
        uz = -0.32 + 0.042 * math.sin(ang)
        u_pts.append(Vector((ux, 0.0, uz)))
        u_rads.append(0.0076)
    _add_tube_along_points(bm_os, u_pts, u_rads, n_sides=14, mat_idx=0)
    # Tiny brass water-key spit valve on bow
    _add_cylinder_between(bm_os, Vector((0.0, -0.006, -0.362)), Vector((0.018, -0.012, -0.358)), 0.0024, 0.0032, n_sides=8, mat_idx=1)

    bmesh.ops.recalc_face_normals(bm_os, faces=bm_os.faces)
    outer_slide = _make_mesh_obj(
        col,
        "TromboneOuterSlide",
        bm_os,
        [mats["PolishedBrass"], mats["BrushedGold"]],
        smooth=True,
    )
    outer_slide.parent = slide_axis

    # 4) Luminous Bell Flare centered at trombone bell mouth origin so scaling is purely radial
    tb_flare_piv = _new_empty(col, "TromboneBellFlarePivot", location=tuple(rim_c), parent=slide_axis)
    bm_tf = bmesh.new()
    ref_t = Vector((1.0, 0.0, 0.0)) if abs(bell_dir.x) < 0.9 else Vector((0.0, 1.0, 0.0))
    u_t = bell_dir.cross(ref_t).normalized()
    v_t = bell_dir.cross(u_t).normalized()
    for d_off, r_ring, t_rad in ((-0.008, 0.088, 0.0045), (0.022, 0.105, 0.0032)):
        c_ring = bell_dir * d_off
        pts_ring = [
            c_ring + (u_t * math.cos(2.0 * math.pi * k / 32) + v_t * math.sin(2.0 * math.pi * k / 32)) * r_ring
            for k in range(33)
        ]
        _add_tube_along_points(bm_tf, pts_ring, [t_rad] * len(pts_ring), n_sides=10, cap_start=False, cap_end=False, mat_idx=0)
    tb_flare = _make_mesh_obj(col, "TromboneBellFlare", bm_tf, [mats["LuminousElement"]], smooth=True)
    tb_flare.parent = tb_flare_piv
    tb_flare.color = (0.95, 0.16, 0.22, 0.0)
    tb_flare.scale = (0.0, 0.0, 0.0)

    return {
        "outer_slide": outer_slide,
        "bell_flare": tb_flare,
    }


# ---------------------------------------------------------------------------
# Keyframe Animation
# ---------------------------------------------------------------------------

def _animate_clarinet(
    cl_data: dict[str, Any],
    notes: list[dict[str, Any]],
    fps: int,
    total_frames: int,
) -> None:
    """Animate Clarinet SilverMetal key cups lifting, tone-hole rings glowing, and bell breath aura."""
    key_cups = cl_data["key_cups"]
    aura_objs = cl_data["aura_objs"]
    n_keys = len(key_cups)

    for k_i, kc in enumerate(key_cups):
        kc["pivot"].rotation_euler = (0.0, 0.0, 0.0)
        kc["pivot"].keyframe_insert(data_path="rotation_euler", index=1, frame=1)
        kc["tone_hole"].color[3] = 0.02
        kc["tone_hole"].keyframe_insert(data_path="color", frame=1)

    for ao in aura_objs:
        ao.color = (0.2, 0.8, 0.5, 0.0)
        ao.scale = (0.0, 0.0, 0.0)
        ao.keyframe_insert(data_path="color", frame=1)
        ao.keyframe_insert(data_path="scale", frame=1)

    if not notes:
        return

    # Map notes to key cups (each note lifts a cluster of 2 adjacent key cups cleanly)
    cup_events: dict[int, list[dict[str, Any]]] = {i: [] for i in range(n_keys)}
    for ev in sorted(notes, key=lambda x: x["start_s"]):
        idx = int(round((ev["step"] - CLARINET_STEP_MIN) / float(CLARINET_STEP_MAX - CLARINET_STEP_MIN) * (n_keys - 1)))
        idx = max(0, min(n_keys - 1, idx))
        cup_events[idx].append(ev)
        cup_events[(idx + 1) % n_keys].append(ev)

    for k_i, kc in enumerate(key_cups):
        piv = kc["pivot"]
        th = kc["tone_hole"]
        side = kc["hinge_side"]
        # Rotate around Y so cup lifts outward (-Y) off the bore
        lift_rad = side * math.radians(26.0)
        evts = cup_events[k_i]
        const_th: set[int] = {1}

        for i, ev in enumerate(evts):
            f0 = common.sec_to_frame(ev["start_s"], fps)
            f1 = min(total_frames, common.sec_to_frame(ev["end_s"], fps))
            next_f0 = common.sec_to_frame(evts[i + 1]["start_s"], fps) if i + 1 < len(evts) else total_frames + 10
            rgb = common.vivid_53edo_color(ev["step"])
            hold_end = min(f1, next_f0 - 2)

            if f0 > 2:
                f_pre = f0 - 1
                piv.rotation_euler[1] = 0.0
                piv.keyframe_insert(data_path="rotation_euler", index=1, frame=f_pre)
                th.color[3] = 0.02
                th.keyframe_insert(data_path="color", frame=f_pre)
                const_th.add(f_pre)

            piv.rotation_euler[1] = lift_rad
            piv.keyframe_insert(data_path="rotation_euler", index=1, frame=f0)
            piv.keyframe_insert(data_path="rotation_euler", index=1, frame=max(f0, hold_end))

            th.color = (*rgb, 0.95)
            th.keyframe_insert(data_path="color", frame=f0)
            th.color = (*rgb, 0.85)
            th.keyframe_insert(data_path="color", frame=max(f0, hold_end))

            if hold_end >= f1 and f1 < total_frames:
                f_rel = min(total_frames, f1 + 2)
                piv.rotation_euler[1] = 0.0
                piv.keyframe_insert(data_path="rotation_euler", index=1, frame=f_rel)
                th.color = (*rgb, 0.02)
                th.keyframe_insert(data_path="color", frame=f_rel)
                const_th.add(f_rel)

        common.set_constant_segment(th, "color", -1, const_th)

    # Bell breath aura ring & cone pulse on every clarinet note
    aura_const: set[int] = {1}
    sorted_notes = sorted(notes, key=lambda x: x["start_s"])
    for i, ev in enumerate(sorted_notes):
        f0 = common.sec_to_frame(ev["start_s"], fps)
        f1 = min(total_frames, common.sec_to_frame(ev["end_s"], fps))
        next_f0 = common.sec_to_frame(sorted_notes[i + 1]["start_s"], fps) if i + 1 < len(sorted_notes) else total_frames + 10
        rgb = common.vivid_53edo_color(ev["step"])
        peak = min(0.88, 0.60 + 0.30 * ev["vel"])
        hold_end = min(f1, next_f0 - 2)

        for idx_a, ao in enumerate(aura_objs):
            al = peak * (0.88 if idx_a == 0 else 0.72)
            sc_peak = 1.02 if idx_a == 0 else (1.06 + 0.05 * idx_a)
            if f0 > 2:
                ao.color = (*rgb, 0.0)
                ao.scale = (0.0, 0.0, 0.0)
                ao.keyframe_insert(data_path="color", frame=f0 - 1)
                ao.keyframe_insert(data_path="scale", frame=f0 - 1)
                if idx_a == 0:
                    aura_const.add(f0 - 1)

            ao.color = (*rgb, al)
            ao.scale = (sc_peak, sc_peak, sc_peak)
            ao.keyframe_insert(data_path="color", frame=f0)
            ao.keyframe_insert(data_path="scale", frame=f0)

            ao.color = (*rgb, al * 0.82)
            ao.scale = (sc_peak * 1.05, sc_peak * 1.05, sc_peak * 1.05)
            ao.keyframe_insert(data_path="color", frame=max(f0, hold_end))
            ao.keyframe_insert(data_path="scale", frame=max(f0, hold_end))

            if hold_end >= f1 and f1 < total_frames:
                f_rel = min(total_frames, f1 + 2)
                ao.color = (*rgb, 0.0)
                ao.scale = (0.0, 0.0, 0.0)
                ao.keyframe_insert(data_path="color", frame=f_rel)
                ao.keyframe_insert(data_path="scale", frame=f_rel)
                if idx_a == 0:
                    aura_const.add(f_rel)

    for ao in aura_objs:
        common.set_constant_segment(ao, "color", -1, aura_const)
        common.set_constant_segment(ao, "scale", -1, aura_const)


def _animate_french_horn(
    hr_data: dict[str, Any],
    notes: list[dict[str, Any]],
    fps: int,
    total_frames: int,
) -> None:
    """Animate 4 rotary valve paddles depressing and warm luminous bell flare on french_horn notes."""
    paddles = hr_data["paddles"]
    bell_flare = hr_data["bell_flare"]

    for piv in paddles:
        piv.rotation_euler = (0.0, 0.0, 0.0)
        piv.keyframe_insert(data_path="rotation_euler", index=0, frame=1)

    bell_flare.color = (0.96, 0.62, 0.14, 0.0)
    bell_flare.scale = (0.0, 0.0, 0.0)
    bell_flare.keyframe_insert(data_path="color", frame=1)
    bell_flare.keyframe_insert(data_path="scale", frame=1)

    if not notes:
        return

    flare_const: set[int] = {1}
    sorted_notes = sorted(notes, key=lambda x: x["start_s"])
    for i, ev in enumerate(sorted_notes):
        f0 = common.sec_to_frame(ev["start_s"], fps)
        f1 = min(total_frames, common.sec_to_frame(ev["end_s"], fps))
        next_f0 = common.sec_to_frame(sorted_notes[i + 1]["start_s"], fps) if i + 1 < len(sorted_notes) else total_frames + 10
        hold_end = min(f1, next_f0 - 2)
        rgb = common.vivid_53edo_color(ev["step"])
        al = min(0.76, 0.54 + 0.24 * ev["vel"])

        # Deterministic 4-valve fingering mask (at least 2 paddles depress for rich visual silhouette)
        pc = abs(int(ev["step"])) % 15 + 1
        active_mask = [bool((pc >> b) & 1) for b in range(4)]
        if sum(active_mask) < 2:
            active_mask[0] = True
            active_mask[(pc % 3) + 1] = True

        for v_i, piv in enumerate(paddles):
            depress = math.radians(22.0) if active_mask[v_i] else 0.0
            if f0 > 2:
                piv.rotation_euler[0] = 0.0
                piv.keyframe_insert(data_path="rotation_euler", index=0, frame=f0 - 1)
            piv.rotation_euler[0] = depress
            piv.keyframe_insert(data_path="rotation_euler", index=0, frame=f0)
            piv.keyframe_insert(data_path="rotation_euler", index=0, frame=max(f0, hold_end))
            if hold_end >= f1 and f1 < total_frames:
                piv.rotation_euler[0] = 0.0
                piv.keyframe_insert(data_path="rotation_euler", index=0, frame=min(total_frames, f1 + 2))

        if f0 > 2:
            bell_flare.color = (*rgb, 0.0)
            bell_flare.scale = (0.0, 0.0, 0.0)
            bell_flare.keyframe_insert(data_path="color", frame=f0 - 1)
            bell_flare.keyframe_insert(data_path="scale", frame=f0 - 1)
            flare_const.add(f0 - 1)
        bell_flare.color = (*rgb, al)
        bell_flare.scale = (1.0, 1.0, 1.0)
        bell_flare.keyframe_insert(data_path="color", frame=f0)
        bell_flare.keyframe_insert(data_path="scale", frame=f0)
        bell_flare.color = (*rgb, al * 0.85)
        bell_flare.scale = (1.0, 1.0, 1.0)
        bell_flare.keyframe_insert(data_path="color", frame=max(f0, hold_end))
        bell_flare.keyframe_insert(data_path="scale", frame=max(f0, hold_end))
        if hold_end >= f1 and f1 < total_frames:
            f_rel = min(total_frames, f1 + 2)
            bell_flare.color = (*rgb, 0.0)
            bell_flare.scale = (0.0, 0.0, 0.0)
            bell_flare.keyframe_insert(data_path="color", frame=f_rel)
            bell_flare.keyframe_insert(data_path="scale", frame=f_rel)
            flare_const.add(f_rel)

    common.set_constant_segment(bell_flare, "color", -1, flare_const)
    common.set_constant_segment(bell_flare, "scale", -1, flare_const)


def _animate_trombone(
    tb_data: dict[str, Any],
    notes: list[dict[str, Any]],
    fps: int,
    total_frames: int,
) -> None:
    """Animate telescoping outer U-slide along slide axis (position=0..1) and bell glow."""
    outer_slide = tb_data["outer_slide"]
    bell_flare = tb_data["bell_flare"]
    max_travel_m = 0.24  # local -Z displacement at position=1.0

    outer_slide.location = (0.0, 0.0, 0.0)
    outer_slide.keyframe_insert(data_path="location", index=2, frame=1)
    bell_flare.color = (0.95, 0.16, 0.22, 0.0)
    bell_flare.scale = (0.0, 0.0, 0.0)
    bell_flare.keyframe_insert(data_path="color", frame=1)
    bell_flare.keyframe_insert(data_path="scale", frame=1)

    if not notes:
        return

    flare_const: set[int] = {1}
    sorted_notes = sorted(notes, key=lambda x: x["start_s"])
    for i, ev in enumerate(sorted_notes):
        f0 = common.sec_to_frame(ev["start_s"], fps)
        f1 = min(total_frames, common.sec_to_frame(ev["end_s"], fps))
        next_f0 = common.sec_to_frame(sorted_notes[i + 1]["start_s"], fps) if i + 1 < len(sorted_notes) else total_frames + 10
        hold_end = min(f1, next_f0 - 2)
        rgb = common.vivid_53edo_color(ev["step"])
        al = min(0.76, 0.56 + 0.22 * ev["vel"])

        # Position = 0..1 mapped from pitch step (lower step = further slide extension)
        pos = max(0.0, min(1.0, (TROMBONE_STEP_MAX - ev["step"]) / float(TROMBONE_STEP_MAX - TROMBONE_STEP_MIN)))
        target_z = -pos * max_travel_m

        # Pre-position slide smoothly 4 frames before attack like a real trombonist
        if i == 0 and f0 > 6:
            outer_slide.location[2] = 0.0
            outer_slide.keyframe_insert(data_path="location", index=2, frame=max(2, f0 - 6))
        outer_slide.location[2] = target_z
        outer_slide.keyframe_insert(data_path="location", index=2, frame=f0)
        outer_slide.keyframe_insert(data_path="location", index=2, frame=max(f0, hold_end))

        if f0 > 2:
            bell_flare.color = (*rgb, 0.0)
            bell_flare.scale = (0.0, 0.0, 0.0)
            bell_flare.keyframe_insert(data_path="color", frame=f0 - 1)
            bell_flare.keyframe_insert(data_path="scale", frame=f0 - 1)
            flare_const.add(f0 - 1)
        bell_flare.color = (*rgb, al)
        bell_flare.scale = (1.0, 1.0, 1.0)
        bell_flare.keyframe_insert(data_path="color", frame=f0)
        bell_flare.keyframe_insert(data_path="scale", frame=f0)
        bell_flare.color = (*rgb, al * 0.85)
        bell_flare.scale = (1.0, 1.0, 1.0)
        bell_flare.keyframe_insert(data_path="color", frame=max(f0, hold_end))
        bell_flare.keyframe_insert(data_path="scale", frame=max(f0, hold_end))
        if hold_end >= f1 and f1 < total_frames:
            f_rel = min(total_frames, f1 + 2)
            bell_flare.color = (*rgb, 0.0)
            bell_flare.scale = (0.0, 0.0, 0.0)
            bell_flare.keyframe_insert(data_path="color", frame=f_rel)
            bell_flare.keyframe_insert(data_path="scale", frame=f_rel)
            flare_const.add(f_rel)

    common.set_constant_segment(bell_flare, "color", -1, flare_const)
    common.set_constant_segment(bell_flare, "scale", -1, flare_const)


# ---------------------------------------------------------------------------
# Stage Contract Entrypoint: build_instrument(...)
# ---------------------------------------------------------------------------

def build_instrument(
    mats: dict[str, bpy.types.Material],
    timeline: dict[str, Any],
    *,
    collection_name: str = "WindsBrassConsort",
    anchor_location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    anchor_rotation_z_deg: float = 0.0,
    anchor_scale: float = 1.0,
) -> bpy.types.Object:
    """Build & animate the 53-EDO Woodwind & Brass Consort inside collection_name."""
    consort_col = bpy.data.collections.new(collection_name)
    bpy.context.scene.collection.children.link(consort_col)

    cl_data = _build_clarinet_assembly(consort_col, mats)
    hr_data = _build_french_horn_assembly(consort_col, mats)
    tb_data = _build_trombone_assembly(consort_col, mats)

    cl_notes: list[dict[str, Any]] = []
    hr_notes: list[dict[str, Any]] = []
    tb_notes: list[dict[str, Any]] = []

    for n in timeline.get("notes", []):
        tid = str(n.get("track_id", "")).lower()
        inst = str(n.get("instrument", "")).lower()
        raw_step = int(n["step"])
        if "clarinet" in tid or "clarinet" in inst or "english_horn" in tid or "english_horn" in inst:
            cl_notes.append({**n, "step": common.fold_step_to_range(raw_step, CLARINET_STEP_MIN, CLARINET_STEP_MAX)})
        elif "french_horn" in tid or "french_horn" in inst or "horn" in tid or "horn" in inst:
            hr_notes.append({**n, "step": common.fold_step_to_range(raw_step, HORN_STEP_MIN, HORN_STEP_MAX)})
        elif "trombone" in tid or "trombone" in inst or "bassoon" in tid or "bassoon" in inst:
            tb_notes.append({**n, "step": common.fold_step_to_range(raw_step, TROMBONE_STEP_MIN, TROMBONE_STEP_MAX)})
        else:
            # Generic brass/woodwind fallback
            hr_notes.append({**n, "step": common.fold_step_to_range(raw_step, HORN_STEP_MIN, HORN_STEP_MAX)})

    fps = int(timeline.get("fps", 24))
    total_frames = int(timeline.get("total_frames", 1))
    _animate_clarinet(cl_data, cl_notes, fps, total_frames)
    _animate_french_horn(hr_data, hr_notes, fps, total_frames)
    _animate_trombone(tb_data, tb_notes, fps, total_frames)

    return common.parent_collection_to_anchor(
        consort_col,
        f"{collection_name}_Anchor",
        location=anchor_location,
        rotation_z_deg=anchor_rotation_z_deg,
        scale=anchor_scale,
    )


# ---------------------------------------------------------------------------
# Standalone Showcase Scene
# ---------------------------------------------------------------------------

def _tune_studio_look(scene: bpy.types.Scene, mats: dict[str, bpy.types.Material]) -> None:
    scene.view_settings.exposure = -0.44
    if scene.use_nodes and scene.node_tree:
        for node in scene.node_tree.nodes:
            if node.type == "GLARE":
                node.threshold = 1.15

    light_tweaks = {
        "KeyLight": (540.0, 3.2),
        "FillLight": (340.0, 3.6),
        "RimLight": (600.0, 2.8),
        "TopAccent": (280.0, 3.6),
    }
    for lname, (energy, size) in light_tweaks.items():
        lobj = bpy.data.objects.get(lname)
        if lobj and lobj.data:
            lobj.data.energy = energy
            lobj.data.size = size

    ped_bsdf = mats["PedestalWood"].node_tree.nodes.get("Principled BSDF")
    if ped_bsdf is not None:
        ped_bsdf.inputs["Roughness"].default_value = 0.56
        ped_bsdf.inputs["Specular IOR Level"].default_value = 0.16
        ped_bsdf.inputs["Coat Weight"].default_value = 0.03


def build_scene(taa_samples: int = 16) -> dict[str, Any]:
    scene = common.reset_scene(fps=24, res_x=1920, res_y=1080, taa_samples=taa_samples)
    mats = common.create_studio_materials()
    common.build_concert_stage(mats, pedestal_radius=1.65, pedestal_height=PEDESTAL_Z, light_target_z=0.68)
    _tune_studio_look(scene, mats)

    timeline = common.load_score_timeline(SCORE_PATH, WAV_PATH, fps=24)
    build_instrument(mats, timeline, collection_name="WindsBrassConsort")

    total_frames = int(timeline["total_frames"])
    # Start slightly left-front for clarinet hook, orbit smoothly across center/right for brass fanfare
    cam_keyframes = [
        (1, (-0.82, -3.45, 1.32)),
        (max(2, round(total_frames * 0.25)), (-0.86, -3.38, 1.30)),
        (max(3, round(total_frames * 0.65)), (0.76, -3.52, 1.36)),
        (total_frames, (0.38, -3.58, 1.34)),
    ]
    common.setup_orbit_camera(
        target_pos=(0.0, 0.0, 0.66),
        keyframes_cam_loc=cam_keyframes,
        lens_mm=34.0,
        dof_fstop=6.4,
    )
    return timeline


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    stills_only = "--stills-only" in argv
    render_vid = "--render-video" in argv

    taa = 8 if render_vid else 16
    timeline = build_scene(taa_samples=taa)
    common.save_blend(BLEND_PATH)
    print(f"[winds_brass_53edo] Saved blend: {BLEND_PATH}")

    if stills_only:
        frame_specs = [
            ("idle", 1),
            ("clarinet_hook", common.sec_to_frame(2.2, 24)),
            ("brass_fanfare", common.sec_to_frame(10.5, 24)),
        ]
        rendered = common.render_diagnostic_stills(frame_specs, OUT_DIR, "diag_winds")
        for p in rendered:
            print(f"[winds_brass_53edo] Diagnostic still: {p}")

    if render_vid:
        common.render_video(
            WEBM_PATH,
            WAV_PATH,
            int(timeline["total_frames"]),
            TMP_FRAMES_DIR,
            fps=24,
        )


if __name__ == "__main__":
    main()
