"""The Bosanquet 5-Tier Terraced 53-EDO Concert Grand Piano for Blender 4.2 EEVEE Next."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

import bmesh
import bpy
import mathutils

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from blender_gallery import common  # noqa: E402

SCORE_JSON_PATH = PROJECT_ROOT / "scores" / "showcase_3d" / "03_piano_bosanquet.json"
WAV_PATH = PROJECT_ROOT / "output" / "showcase_3d" / "03_piano_bosanquet.wav"
OUT_DIR = PROJECT_ROOT / "output" / "showcase_3d"
BLEND_PATH = OUT_DIR / "03_piano_bosanquet.blend"
WEBM_PATH = OUT_DIR / "03_piano_bosanquet.webm"
TMP_FRAMES_DIR = OUT_DIR / "_tmp_piano_frames"

PEDESTAL_HEIGHT = 0.09
CABINET_BASE_Z = 0.68
RIM_TOP_Z = 0.96
SOUNDBOARD_Z = 0.80
PLATE_Z = 0.842
LID_OPEN_DEG = 34.0

KEY_STEP_MIN = -55
KEY_STEP_MAX = 106
KEY_DEPRESS_Z = -0.015
NUM_TIERS = 5

# 12 chromatic pitch classes per 53-EDO octave:
# (pc_idx, anchor_step_in_53, k_min, k_max, is_natural)
PITCH_CLASSES: list[tuple[int, int, int, int, bool]] = [
    (0, 0, -2, 2, True),     # C
    (1, 5, -2, 1, False),    # C# / Db
    (2, 9, -2, 2, True),     # D
    (3, 13, -1, 1, False),   # Eb
    (4, 17, -2, 2, True),    # E
    (5, 22, -2, 1, True),    # F
    (6, 26, -2, 2, False),   # F#
    (7, 31, -2, 2, True),    # G
    (8, 36, -2, 1, False),   # Ab
    (9, 39, -1, 1, True),    # A
    (10, 43, -2, 2, False),  # Bb
    (11, 48, -2, 2, True),   # B
]

# Subtle comma-tier tint for idle luminous key inlays (alpha=0.04 stays well below glare threshold
# while giving high contrast against both ivory/ebony frames and alpha=1.0 note bursts).
TIER_IDLE_TINT_NATURAL: list[tuple[float, float, float]] = [
    (0.055, 0.045, 0.035),
    (0.065, 0.055, 0.042),
    (0.080, 0.068, 0.050),
    (0.065, 0.058, 0.048),
    (0.055, 0.050, 0.045),
]
TIER_IDLE_TINT_ACCIDENTAL: list[tuple[float, float, float]] = [
    (0.015, 0.015, 0.022),
    (0.018, 0.018, 0.026),
    (0.022, 0.022, 0.032),
    (0.018, 0.018, 0.028),
    (0.015, 0.016, 0.024),
]


def _link_to_collection(obj: bpy.types.Object, col: bpy.types.Collection) -> None:
    for existing in list(obj.users_collection):
        existing.objects.unlink(obj)
    col.objects.link(obj)


def _new_mesh_object(
    name: str,
    bm: bmesh.types.BMesh,
    col: bpy.types.Collection,
    materials: list[bpy.types.Material],
    smooth: bool = True,
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    if smooth:
        for poly in mesh.polygons:
            poly.use_smooth = True
    for mat in materials:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    return obj


def _add_bevel(obj: bpy.types.Object, width: float = 0.004, segments: int = 2) -> None:
    bev = obj.modifiers.new("Bevel", "BEVEL")
    bev.width = width
    bev.segments = segments
    bev.limit_method = "ANGLE"
    bev.angle_limit = math.radians(30.0)


def _bezier_pt(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    u = 1.0 - t
    x = (u**3) * p0[0] + 3 * (u**2) * t * p1[0] + 3 * u * (t**2) * p2[0] + (t**3) * p3[0]
    y = (u**3) * p0[1] + 3 * (u**2) * t * p1[1] + 3 * u * (t**2) * p2[1] + (t**3) * p3[1]
    return (x, y)


def grand_rim_contour(inset: float = 0.0, n_bentside: int = 36, n_tail: int = 28) -> list[tuple[float, float]]:
    """Return closed CCW 2D contour (x, y) of the grand body at analytic inward `inset`."""
    x_left = -0.725 + inset
    x_right_front = 0.725 - inset
    y_front = -0.360 + inset
    cx, cy = -0.360, 0.700
    r_tail = max(0.05, 0.365 - inset)
    x_tail_right = cx + r_tail  # joins bentside smoothly at y = cy

    pts: list[tuple[float, float]] = [
        (x_left, y_front),
        (x_right_front, y_front),
    ]
    # Analytic bentside Bezier shifted along exact inward normal (-dy, dx)
    p0, p1, p2, p3 = (0.725, -0.360), (0.680, -0.020), (0.005, 0.340), (0.005, 0.700)
    raw_bentside = [_bezier_pt(p0, p1, p2, p3, i / n_bentside) for i in range(n_bentside + 1)]
    for i in range(1, n_bentside + 1):
        bx, by = raw_bentside[i]
        px, py = raw_bentside[i - 1]
        nx_prev, ny_prev = raw_bentside[min(n_bentside, i + 1)]
        tx = nx_prev - px
        ty = ny_prev - py
        tlen = math.hypot(tx, ty) or 1.0
        # CCW inward normal is (-ty, tx)
        ix = bx + (-ty / tlen) * inset
        iy = by + (tx / tlen) * inset
        # Clamp near front-right corner so sharp corner never folds over itself
        ix = min(ix, x_right_front)
        iy = max(iy, y_front)
        if i == n_bentside:
            ix, iy = x_tail_right, cy
        pts.append((ix, iy))

    # Semicircular tail centered at (-0.360, +0.700)
    for i in range(1, n_tail + 1):
        ang = math.pi * (i / n_tail)
        pts.append((cx + r_tail * math.cos(ang), cy + r_tail * math.sin(ang)))

    # Straight left bass spine back down toward (x_left, y_front)
    for frac in (0.75, 0.50, 0.25):
        pts.append((x_left, y_front + frac * (cy - y_front)))
    return pts


def _build_extruded_ring(
    name: str,
    outer_pts: list[tuple[float, float]],
    inner_pts: list[tuple[float, float]],
    z_bot: float,
    z_top: float,
    col: bpy.types.Collection,
    outer_mat: bpy.types.Material,
    inner_mat: bpy.types.Material,
) -> bpy.types.Object:
    """Build a watertight hollow wall between outer_pts and inner_pts."""
    bm = bmesh.new()
    n = len(outer_pts)
    ob = [bm.verts.new((x, y, z_bot)) for x, y in outer_pts]
    ot = [bm.verts.new((x, y, z_top)) for x, y in outer_pts]
    ib = [bm.verts.new((x, y, z_bot)) for x, y in inner_pts]
    it = [bm.verts.new((x, y, z_top)) for x, y in inner_pts]

    for i in range(n):
        j = (i + 1) % n
        f_out = bm.faces.new((ob[i], ob[j], ot[j], ot[i]))
        f_out.material_index = 0
        f_in = bm.faces.new((ib[j], ib[i], it[i], it[j]))
        f_in.material_index = 1
        f_top = bm.faces.new((ot[i], ot[j], it[j], it[i]))
        f_top.material_index = 0
        f_bot = bm.faces.new((ib[i], ib[j], ob[j], ob[i]))
        f_bot.material_index = 0

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = _new_mesh_object(name, bm, col, [outer_mat, inner_mat], smooth=True)
    _add_bevel(obj, width=0.004, segments=2)
    return obj


def _build_filled_slab(
    name: str,
    pts: list[tuple[float, float]],
    z_bot: float,
    z_top: float,
    col: bpy.types.Collection,
    mat: bpy.types.Material,
    bevel_w: float = 0.004,
) -> bpy.types.Object:
    bm = bmesh.new()
    vb = [bm.verts.new((x, y, z_bot)) for x, y in pts]
    vt = [bm.verts.new((x, y, z_top)) for x, y in pts]
    n = len(pts)
    bm.faces.new(list(reversed(vb)))
    bm.faces.new(vt)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((vb[i], vb[j], vt[j], vt[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = _new_mesh_object(name, bm, col, [mat], smooth=False)
    if bevel_w > 0:
        _add_bevel(obj, width=bevel_w, segments=2)
    return obj


def _build_box(
    name: str,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    col: bpy.types.Collection,
    mat: bpy.types.Material,
    bevel_w: float = 0.003,
) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    obj = _new_mesh_object(name, bm, col, [mat], smooth=False)
    if bevel_w > 0:
        _add_bevel(obj, width=bevel_w, segments=2)
    return obj


def _build_cylinder(
    name: str,
    p0: tuple[float, float, float],
    p1: tuple[float, float, float],
    r0: float,
    r1: float,
    segments: int,
    col: bpy.types.Collection,
    mat: bpy.types.Material,
) -> bpy.types.Object:
    v0 = mathutils.Vector(p0)
    v1 = mathutils.Vector(p1)
    vec = v1 - v0
    length = vec.length
    mid = (v0 + v1) * 0.5
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=segments,
        radius1=r0,
        radius2=r1,
        depth=length,
    )
    obj = _new_mesh_object(name, bm, col, [mat], smooth=True)
    obj.location = mid
    obj.rotation_euler = vec.to_track_quat("Z", "Y").to_euler()
    return obj


def _build_cabinet_and_legs(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> None:
    """Construct S-rim grand cabinet, keybed, cheek blocks, 3 brass-shod legs, and propped lid."""
    outer_pts = grand_rim_contour(inset=0.0)
    inner_pts = grand_rim_contour(inset=0.042)

    # Main curved S-rim wall (GlossEbony exterior, DarkRosewood interior)
    _build_extruded_ring(
        "GrandRimWall",
        outer_pts,
        inner_pts,
        CABINET_BASE_Z,
        RIM_TOP_Z,
        col,
        mats["GlossEbony"],
        mats["DarkRosewood"],
    )

    # Bottom belly floor enclosing the case underneath
    _build_filled_slab(
        "GrandBellyFloor",
        grand_rim_contour(inset=0.008),
        CABINET_BASE_Z,
        CABINET_BASE_Z + 0.025,
        col,
        mats["GlossEbony"],
        bevel_w=0.003,
    )

    # Brass molding strip circling the lower rim edge
    _build_extruded_ring(
        "RimBrassTrim",
        grand_rim_contour(inset=-0.002),
        grand_rim_contour(inset=0.004),
        CABINET_BASE_Z + 0.014,
        CABINET_BASE_Z + 0.024,
        col,
        mats["PolishedBrass"],
        mats["PolishedBrass"],
    )

    # Keybed base & front apron extending from y=-0.85 to y=-0.34
    _build_box(
        "KeybedBase",
        (0.0, -0.595, 0.706),
        (1.450, 0.510, 0.052),
        col,
        mats["GlossEbony"],
        bevel_w=0.004,
    )
    # Left & right terraced cheek blocks framing the 5-tier keyboard
    for side_tag, cx in (("Left", -0.695), ("Right", 0.695)):
        _build_box(
            f"CheekBlock_{side_tag}",
            (cx, -0.595, 0.790),
            (0.060, 0.510, 0.116),
            col,
            mats["GlossEbony"],
            bevel_w=0.004,
        )
        # Subtle brass inlay bar along the inner cheek crest
        _build_box(
            f"CheekBrassInlay_{side_tag}",
            (cx + (-0.005 if cx > 0 else 0.005), -0.595, 0.850),
            (0.008, 0.480, 0.006),
            col,
            mats["PolishedBrass"],
            bevel_w=0.001,
        )

    # Fallboard / Nameboard behind the k=+2 terrace
    _build_box(
        "Fallboard",
        (0.0, -0.360, 0.875),
        (1.330, 0.036, 0.140),
        col,
        mats["GlossEbony"],
        bevel_w=0.004,
    )
    _build_box(
        "FallboardBrassRule",
        (0.0, -0.379, 0.865),
        (0.420, 0.004, 0.010),
        col,
        mats["PolishedBrass"],
        bevel_w=0.001,
    )

    # Open fretwork brass & rosewood music rack (keeps interior harp plate clearly visible)
    _build_box("MusicDeskLedge", (0.0, -0.355, 0.955), (0.760, 0.044, 0.012), col, mats["DarkRosewood"], bevel_w=0.002)
    for bx in (-0.34, -0.17, 0.0, 0.17, 0.34):
        _build_cylinder(
            f"MusicRackPost_{bx:+.2f}",
            (bx, -0.345, 0.955),
            (bx, -0.315, 1.075),
            0.0035,
            0.003,
            12,
            col,
            mats["PolishedBrass"],
        )
    _build_cylinder("MusicRackTopBar", (-0.36, -0.315, 1.075), (0.36, -0.315, 1.075), 0.004, 0.004, 12, col, mats["PolishedBrass"])

    # 3 tapered brass-shod legs resting flush on z = PEDESTAL_HEIGHT (0.09)
    leg_coords = [
        ("FrontLeft", -0.610, -0.610),
        ("FrontRight", 0.610, -0.610),
        ("RearTail", -0.260, 0.880),
    ]
    for tag, lx, ly in leg_coords:
        # Brass caster cup & wheel foot flush at z = 0.09
        _build_cylinder(
            f"LegCaster_{tag}",
            (lx, ly, PEDESTAL_HEIGHT),
            (lx, ly, PEDESTAL_HEIGHT + 0.032),
            0.022,
            0.018,
            24,
            col,
            mats["PolishedBrass"],
        )
        # Tapered brass ferrule sleeve
        _build_cylinder(
            f"LegFerrule_{tag}",
            (lx, ly, PEDESTAL_HEIGHT + 0.032),
            (lx, ly, PEDESTAL_HEIGHT + 0.095),
            0.018,
            0.024,
            24,
            col,
            mats["PolishedBrass"],
        )
        # Main tapered GlossEbony leg shaft (octagonal-faceted classical concert grand profile)
        _build_cylinder(
            f"LegShaft_{tag}",
            (lx, ly, PEDESTAL_HEIGHT + 0.095),
            (lx, ly, CABINET_BASE_Z - 0.055),
            0.024,
            0.044,
            8,
            col,
            mats["GlossEbony"],
        )
        # Upper capital block & brass collar meeting cabinet underside
        _build_box(
            f"LegCapital_{tag}",
            (lx, ly, CABINET_BASE_Z - 0.025),
            (0.105, 0.105, 0.060),
            col,
            mats["GlossEbony"],
            bevel_w=0.004,
        )
        _build_cylinder(
            f"LegTopCollar_{tag}",
            (lx, ly, CABINET_BASE_Z - 0.058),
            (lx, ly, CABINET_BASE_Z - 0.046),
            0.046,
            0.052,
            16,
            col,
            mats["PolishedBrass"],
        )

    # Propped-open glossy ebony lid (~34 degrees around bass spine hinge x=-0.725, z=0.965)
    lid_contour = [(-0.725, -0.375), (0.725, -0.375)] + outer_pts[2:]
    lid_obj = _build_filled_slab(
        "GrandLid",
        lid_contour,
        0.0,
        0.022,
        col,
        mats["GlossEbony"],
        bevel_w=0.004,
    )
    hinge_x = -0.725
    hinge_z = RIM_TOP_Z + 0.004
    # Shift vertices into hinge-local space so rotation is strictly around the left spine
    for v in lid_obj.data.vertices:
        v.co.x -= hinge_x
    lid_obj.location = (hinge_x, 0.0, hinge_z)
    # Negative Y rotation lifts +X edge UPWARD into +Z
    lid_theta = math.radians(LID_OPEN_DEG)
    lid_obj.rotation_euler = (0.0, -lid_theta, 0.0)

    # Brass lid hinges along left spine
    for hy in (-0.15, 0.25, 0.62):
        _build_cylinder(
            f"LidHinge_{hy:+.2f}",
            (-0.726, hy - 0.025, hinge_z),
            (-0.726, hy + 0.025, hinge_z),
            0.006,
            0.006,
            12,
            col,
            mats["PolishedBrass"],
        )

    # Exact geometric placement of the golden prop stick from inner right rim to lid underside
    prop_base = mathutils.Vector((0.560, -0.020, 0.910))
    # Lid underside point at local dx = 1.15m from hinge (x ≈ +0.425 flat)
    dx_prop = 1.16
    prop_top_world = mathutils.Vector((
        hinge_x + dx_prop * math.cos(lid_theta),
        -0.020,
        hinge_z + dx_prop * math.sin(lid_theta),
    ))
    _build_cylinder(
        "LidPropStick",
        tuple(prop_base),
        tuple(prop_top_world),
        0.009,
        0.007,
        16,
        col,
        mats["PolishedBrass"],
    )
    _build_cylinder(
        "LidPropSocket",
        (prop_base.x, prop_base.y, prop_base.z - 0.015),
        (prop_base.x, prop_base.y, prop_base.z + 0.012),
        0.016,
        0.014,
        16,
        col,
        mats["BrushedGold"],
    )


def _build_pedal_lyre(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Build brass & ebony pedal lyre at bottom front and return the animated damper pedal."""
    lyre_y = -0.54
    # Two vertical ebony columns + center brass rod
    for sx in (-0.068, 0.068):
        _build_cylinder(
            f"LyreColumn_{sx:+.3f}",
            (sx, lyre_y, 0.165),
            (sx, lyre_y, CABINET_BASE_Z + 0.005),
            0.013,
            0.015,
            16,
            col,
            mats["GlossEbony"],
        )
    # 3 interior brass lyre rods
    for rx in (-0.028, 0.0, 0.028):
        _build_cylinder(
            f"LyreRod_{rx:+.3f}",
            (rx, lyre_y, 0.175),
            (rx, lyre_y, CABINET_BASE_Z),
            0.004,
            0.004,
            12,
            col,
            mats["PolishedBrass"],
        )
    # Diagonal brass stay braces stabilizing the lyre back to the belly rail
    for sx in (-0.062, 0.062):
        _build_cylinder(
            f"LyreBrace_{sx:+.3f}",
            (sx, lyre_y + 0.02, 0.215),
            (sx * 1.6, -0.22, CABINET_BASE_Z + 0.005),
            0.005,
            0.005,
            12,
            col,
            mats["PolishedBrass"],
        )

    # Pedal box housing resting slightly above pedestal top with central brass foot pad
    _build_box("PedalBox", (0.0, lyre_y, 0.155), (0.210, 0.095, 0.066), col, mats["GlossEbony"], bevel_w=0.004)
    _build_cylinder(
        "PedalBoxFoot",
        (0.0, lyre_y, PEDESTAL_HEIGHT),
        (0.0, lyre_y, 0.125),
        0.032,
        0.024,
        24,
        col,
        mats["PolishedBrass"],
    )

    # 3 Brass pedals protruding forward (-Y); pivot at box front (y = lyre_y - 0.038)
    damper_pedal: bpy.types.Object | None = None
    pivot_y = lyre_y - 0.038
    pivot_z = 0.146
    for tag, px in (("UnaCorda", -0.062), ("Sostenuto", 0.0), ("Damper", 0.062)):
        bm = bmesh.new()
        # Pedal arm extending forward in -Y from pivot (0, 0, 0) to y = -0.095
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(0.022, 0.095, 0.010), verts=bm.verts)
        bmesh.ops.translate(bm, vec=(0.0, -0.0475, 0.0), verts=bm.verts)
        # Wider curved toe pad at tip
        bm_pad = bmesh.new()
        bmesh.ops.create_cube(bm_pad, size=1.0)
        bmesh.ops.scale(bm_pad, vec=(0.030, 0.040, 0.012), verts=bm_pad.verts)
        bmesh.ops.translate(bm_pad, vec=(0.0, -0.092, 0.001), verts=bm_pad.verts)
        me_tmp = bpy.data.meshes.new("_tmp_pad")
        bm_pad.to_mesh(me_tmp)
        bm_pad.free()
        bm.from_mesh(me_tmp)
        bpy.data.meshes.remove(me_tmp)

        pobj = _new_mesh_object(f"Pedal_{tag}", bm, col, [mats["PolishedBrass"]], smooth=False)
        pobj.location = (px, pivot_y, pivot_z)
        _add_bevel(pobj, width=0.002, segments=2)
        if tag == "Damper":
            damper_pedal = pobj

    assert damper_pedal is not None
    return damper_pedal


def _build_interior_harp_and_strings(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> None:
    """Build spruce soundboard, cast-iron gold harp plate, tuning pins, and 95 fan-strung strings."""
    # AntiqueSpruce soundboard filling interior cavity
    sb_pts = grand_rim_contour(inset=0.047)
    _build_filled_slab("Soundboard", sb_pts, SOUNDBOARD_Z - 0.014, SOUNDBOARD_Z, col, mats["AntiqueSpruce"], bevel_w=0.002)

    # DarkRosewood pinblock / wrestplank at front interior
    _build_box("PinBlock", (0.0, -0.255, 0.822), (1.330, 0.165, 0.036), col, mats["DarkRosewood"], bevel_w=0.003)

    # CastIronGold Harp Plate: perimeter flange + sweeping structural struts + bridge bars
    plate_outer = grand_rim_contour(inset=0.054)
    plate_inner = grand_rim_contour(inset=0.118)
    _build_extruded_ring(
        "CastIronHarpFrame",
        plate_outer,
        plate_inner,
        PLATE_Z - 0.016,
        PLATE_Z + 0.008,
        col,
        mats["CastIronGold"],
        mats["CastIronGold"],
    )
    # Front agraffe / pressure bar across pinblock
    _build_box("PlateFrontApron", (0.0, -0.240, PLATE_Z - 0.004), (1.300, 0.120, 0.020), col, mats["CastIronGold"], bevel_w=0.003)
    # Sculptural radial ribs spanning the plate across the soundboard
    rib_specs = [
        ((-0.62, -0.18), (-0.64, 0.68)),
        ((-0.34, -0.18), (-0.42, 0.98)),
        ((-0.02, -0.18), (-0.22, 0.96)),
        ((0.28, -0.18), (-0.04, 0.68)),
        ((0.56, -0.18), (0.34, 0.16)),
    ]
    for idx, ((x0, y0), (x1, y1)) in enumerate(rib_specs):
        _build_cylinder(
            f"PlateStrut_{idx}",
            (x0, y0, PLATE_Z + 0.002),
            (x1, y1, PLATE_Z + 0.002),
            0.015,
            0.012,
            12,
            col,
            mats["CastIronGold"],
        )
    # Curved soundboard bridges
    _build_cylinder("TrebleBridge", (-0.18, 0.42, SOUNDBOARD_Z + 0.016), (0.52, -0.04, SOUNDBOARD_Z + 0.016), 0.011, 0.009, 12, col, mats["DarkRosewood"])
    _build_cylinder("BassBridge", (-0.42, 0.78, SOUNDBOARD_Z + 0.020), (-0.08, 0.66, SOUNDBOARD_Z + 0.020), 0.012, 0.011, 12, col, mats["DarkRosewood"])

    # ~95 Fan-strung strings: 71 treble/tenor brass/copper strings + 24 overstrung copper bass strings = 95!
    bm_treble = bmesh.new()
    bm_bass = bmesh.new()
    bm_pins = bmesh.new()

    def _add_cyl_to_bm(bm: bmesh.types.BMesh, p0: tuple[float, float, float], p1: tuple[float, float, float], r: float, segs: int = 6) -> None:
        v0 = mathutils.Vector(p0)
        v1 = mathutils.Vector(p1)
        vec = v1 - v0
        mat = mathutils.Matrix.Translation((v0 + v1) * 0.5) @ vec.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(
            bm,
            cap_ends=False,
            cap_tris=False,
            segments=segs,
            radius1=r,
            radius2=r,
            depth=vec.length,
            matrix=mat,
        )

    # 71 Treble & Tenor strings fanning from front (-0.28..+0.62) to curved bentside/treble hitch pins
    n_treble = 71
    for i in range(n_treble):
        t = i / (n_treble - 1)
        x0 = -0.24 + t * 0.86
        y0 = -0.22
        if t < 0.45:
            u = t / 0.45
            x1 = -0.34 + u * 0.31
            y1 = 0.82 - u * 0.24
        else:
            u = (t - 0.45) / 0.55
            bx, by = _bezier_pt((0.005, 0.58), (0.04, 0.30), (0.52, 0.05), (0.62, -0.08), u)
            x1, y1 = bx - 0.06, by
        z_str = PLATE_Z + 0.016
        r_str = 0.0012 - 0.0005 * t
        _add_cyl_to_bm(bm_treble, (x0, y0, z_str), (x1, y1, z_str), r_str, segs=6)
        _add_cyl_to_bm(bm_pins, (x0, y0 - 0.03, PLATE_Z + 0.002), (x0, y0 - 0.03, PLATE_Z + 0.022), 0.0026, segs=8)

    # 24 Overstrung wound CopperString bass strings crossing diagonally above tenor strings
    n_bass = 24
    for i in range(n_bass):
        t = i / (n_bass - 1)
        x0 = -0.62 + t * 0.36
        y0 = -0.22
        x1 = -0.36 + t * 0.30
        y1 = 0.94 - t * 0.22
        z_str = PLATE_Z + 0.034
        r_str = 0.0019 - 0.0004 * t
        _add_cyl_to_bm(bm_bass, (x0, y0, z_str), (x1, y1, z_str), r_str, segs=6)
        _add_cyl_to_bm(bm_pins, (x0, y0 - 0.03, PLATE_Z + 0.002), (x0, y0 - 0.03, PLATE_Z + 0.024), 0.0030, segs=8)

    _new_mesh_object("TrebleStrings", bm_treble, col, [mats["BrushedGold"]], smooth=True)
    _new_mesh_object("OverstrungBassStrings", bm_bass, col, [mats["CopperString"]], smooth=True)
    _new_mesh_object("TuningPins", bm_pins, col, [mats["PolishedBrass"]], smooth=True)


def bosanquet_key_layout(step: int) -> dict[str, Any]:
    """Map 53-EDO step (-55..+106) to Bosanquet column, comma terrace k (-2..+2), and 3D coordinates."""
    r = (step + 2) % 53 - 2
    oct_idx = (step - r) // 53

    pc_idx = 0
    k = 0
    is_natural = True
    for pc, anchor, k_min, k_max, nat in PITCH_CLASSES:
        diff = r - anchor
        if k_min <= diff <= k_max:
            pc_idx = pc
            k = diff
            is_natural = nat
            break

    col_idx = (oct_idx + 1) * 12 + pc_idx  # 0..36 across 3 octaves + top C
    col_pitch_x = 0.0355
    x_center = (col_idx - 18.0) * col_pitch_x + k * 0.0026

    tier = k + 2  # 0..4
    y_center = -0.760 + tier * 0.082
    z_top = 0.748 + tier * 0.017
    return {
        "step": step,
        "oct": oct_idx,
        "pc": pc_idx,
        "anchor": PITCH_CLASSES[pc_idx][1],
        "k": k,
        "tier": tier,
        "is_natural": is_natural,
        "x": x_center,
        "y": y_center,
        "z_top": z_top,
    }


def _active_key_color(step: int, anchor: int, k: int) -> tuple[float, float, float]:
    """Return a saturated 53-EDO jewel color preserving canonical hues and comma warmth/coolness."""
    base = common.color_for_53edo_step(step)
    if step % 53 not in common.STEP_COLOR_MAP:
        anchor_rgb = common.color_for_53edo_step(anchor)
        if anchor % 53 not in common.STEP_COLOR_MAP:
            anchor_rgb = (0.98, 0.46, 0.05)
        if k < 0:
            shift = (1.0, 0.30, 0.02)
            mix = 0.22 * abs(k)
        elif k > 0:
            shift = (0.06, 0.84, 1.0)
            mix = 0.22 * k
        else:
            shift = (0.98, 0.46, 0.05)
            mix = 0.0
        base = tuple((1.0 - mix) * anchor_rgb[i] + mix * shift[i] for i in range(3))
    return base


def _create_key_mesh_object(
    name: str,
    width: float,
    length: float,
    height: float,
    body_mat: bpy.types.Material,
    lum_mat: bpy.types.Material,
    col: bpy.types.Collection,
) -> bpy.types.Object:
    """Create a beveled ivory/ebony key body (slot 0) with a raised top/front luminous inlay (slot 1)."""
    bm = bmesh.new()
    hw = width * 0.5
    hl = length * 0.5
    bevel = 0.0018

    # Main beveled key body (slot 0: IvoryKey or GlossEbony)
    b_bot = [
        bm.verts.new((-hw, -hl, -height)),
        bm.verts.new((hw, -hl, -height)),
        bm.verts.new((hw, hl, -height)),
        bm.verts.new((-hw, hl, -height)),
    ]
    b_shoulder = [
        bm.verts.new((-hw, -hl, -bevel)),
        bm.verts.new((hw, -hl, -bevel)),
        bm.verts.new((hw, hl, -bevel)),
        bm.verts.new((-hw, hl, -bevel)),
    ]
    b_top = [
        bm.verts.new((-hw + bevel, -hl + bevel, 0.0)),
        bm.verts.new((hw - bevel, -hl + bevel, 0.0)),
        bm.verts.new((hw - bevel, hl - bevel, 0.0)),
        bm.verts.new((-hw + bevel, hl - bevel, 0.0)),
    ]
    f_bot = bm.faces.new(list(reversed(b_bot)))
    f_bot.material_index = 0
    for i in range(4):
        j = (i + 1) % 4
        f_side = bm.faces.new((b_bot[i], b_bot[j], b_shoulder[j], b_shoulder[i]))
        f_side.material_index = 0
        f_chamfer = bm.faces.new((b_shoulder[i], b_shoulder[j], b_top[j], b_top[i]))
        f_chamfer.material_index = 0
    f_top = bm.faces.new(b_top)
    f_top.material_index = 0

    # Wide central + front-lip luminous cap (slot 1: LuminousElement) so active keys read clearly
    ihw = hw * 0.84
    ihl = hl * 0.88
    inlay_h = 0.0028
    inlay_bev = 0.0012
    in_base = [
        bm.verts.new((-ihw, -hl + bevel * 0.5, 0.0)),
        bm.verts.new((ihw, -hl + bevel * 0.5, 0.0)),
        bm.verts.new((ihw, ihl, 0.0)),
        bm.verts.new((-ihw, ihl, 0.0)),
    ]
    in_top = [
        bm.verts.new((-ihw + inlay_bev, -hl + bevel * 0.5 + inlay_bev, inlay_h)),
        bm.verts.new((ihw - inlay_bev, -hl + bevel * 0.5 + inlay_bev, inlay_h)),
        bm.verts.new((ihw - inlay_bev, ihl - inlay_bev, inlay_h)),
        bm.verts.new((-ihw + inlay_bev, ihl - inlay_bev, inlay_h)),
    ]
    for i in range(4):
        j = (i + 1) % 4
        f_in_side = bm.faces.new((in_base[i], in_base[j], in_top[j], in_top[i]))
        f_in_side.material_index = 1
    f_in_top = bm.faces.new(in_top)
    f_in_top.material_index = 1

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _new_mesh_object(name, bm, col, [body_mat, lum_mat], smooth=False)


def _build_bosanquet_keyboard_and_hammers(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> tuple[dict[int, dict[str, Any]], dict[int, bpy.types.Object]]:
    """Build 5 stepped terrace risers, 162 beveled 53-EDO keys, and 162 interior hammers."""
    # 5 DarkRosewood & PolishedBrass stepped terrace shelves beneath the 5 comma keybeds
    for tier in range(NUM_TIERS):
        z_top_keys = 0.748 + tier * 0.017
        shelf_top = z_top_keys - 0.030
        shelf_bot = 0.722
        y_front = -0.818 + tier * 0.082
        y_back = -0.355
        yc = 0.5 * (y_front + y_back)
        yd = y_back - y_front
        _build_box(
            f"TerraceRiser_{tier}",
            (0.0, yc, 0.5 * (shelf_top + shelf_bot)),
            (1.330, yd, shelf_top - shelf_bot),
            col,
            mats["DarkRosewood"],
            bevel_w=0.002,
        )
        _build_box(
            f"TerraceBrassTrim_{tier}",
            (0.0, y_front + 0.002, shelf_top - 0.002),
            (1.330, 0.005, 0.004),
            col,
            mats["PolishedBrass"],
            bevel_w=0.001,
        )

    keys: dict[int, dict[str, Any]] = {}
    hammers: dict[int, bpy.types.Object] = {}

    for step in range(KEY_STEP_MIN, KEY_STEP_MAX + 1):
        info = bosanquet_key_layout(step)
        tier = info["tier"]
        body_mat = mats["IvoryKey"] if info["is_natural"] else mats["GlossEbony"]
        idle_rgb = TIER_IDLE_TINT_NATURAL[tier] if info["is_natural"] else TIER_IDLE_TINT_ACCIDENTAL[tier]
        idle_rgba = (*idle_rgb, 0.04)

        key_w = 0.0275 if info["is_natural"] else 0.0235
        key_len = 0.094
        key_h = 0.017

        kobj = _create_key_mesh_object(
            f"Key_{step:+04d}_k{info['k']:+d}",
            key_w,
            key_len,
            key_h,
            body_mat,
            mats["LuminousElement"],
            col,
        )
        kobj.location = (info["x"], info["y"], info["z_top"])
        kobj.color = idle_rgba
        keys[step] = {
            "obj": kobj,
            "rest_z": info["z_top"],
            "idle_rgba": idle_rgba,
            "glow_rgb": _active_key_color(step, info["anchor"], info["k"]),
        }

        # Matching interior hammer sitting just behind the pinblock edge, poised below the strings
        hm_x = max(-0.62, min(0.62, info["x"] * 0.97))
        hm_y = -0.295 + tier * 0.005
        hm_z = 0.808
        bm_h = bmesh.new()
        # Shank extending +Y toward strings (pivot at 0,0,0 -> head at y=+0.075)
        bmesh.ops.create_cube(bm_h, size=1.0)
        bmesh.ops.scale(bm_h, vec=(0.005, 0.075, 0.005), verts=bm_h.verts)
        bmesh.ops.translate(bm_h, vec=(0.0, 0.0375, 0.0), verts=bm_h.verts)
        for f in bm_h.faces:
            f.material_index = 0
        bm_head = bmesh.new()
        bmesh.ops.create_cube(bm_head, size=1.0)
        bmesh.ops.scale(bm_head, vec=(0.0085, 0.014, 0.022), verts=bm_head.verts)
        bmesh.ops.translate(bm_head, vec=(0.0, 0.075, 0.011), verts=bm_head.verts)
        me_head = bpy.data.meshes.new("_tmp_hm_head")
        bm_head.to_mesh(me_head)
        bm_head.free()
        for p in me_head.polygons:
            p.material_index = 1
        bm_h.from_mesh(me_head)
        bpy.data.meshes.remove(me_head)

        hobj = _new_mesh_object(
            f"Hammer_{step:+04d}",
            bm_h,
            col,
            [mats["WarmMahogany"], mats["IvoryKey"]],
            smooth=False,
        )
        hobj.location = (hm_x, hm_y, hm_z)
        hammers[step] = hobj

    return keys, hammers


def _animate_timeline(
    timeline: dict[str, Any],
    keys: dict[int, dict[str, Any]],
    hammers: dict[int, bpy.types.Object],
    damper_pedal: bpy.types.Object,
) -> None:
    """Keyframe crisp key depressions, luminous bursts, hammer kicks, and damper pedal."""
    fps = int(timeline["fps"])
    total_frames = int(timeline["total_frames"])

    # Set initial rest state at frame 1 for every key & hammer
    for step, kdata in keys.items():
        kobj = kdata["obj"]
        kobj.location.z = kdata["rest_z"]
        kobj.color = kdata["idle_rgba"]
        kobj.keyframe_insert(data_path="location", index=2, frame=1)
        kobj.keyframe_insert(data_path="color", frame=1)

        hobj = hammers[step]
        hobj.rotation_euler.x = 0.0
        hobj.keyframe_insert(data_path="rotation_euler", index=0, frame=1)

    for ev in timeline["notes"]:
        step = int(ev["step"])
        if step not in keys:
            continue
        kdata = keys[step]
        kobj = kdata["obj"]
        hobj = hammers[step]

        f_start = common.sec_to_frame(ev["start_s"], fps)
        f_end = max(f_start + 2, common.sec_to_frame(ev["end_s"], fps))
        f_pre = max(1, f_start - 1)
        f_post = min(total_frames, f_end + 1)

        rest_z = kdata["rest_z"]
        idle_rgba = kdata["idle_rgba"]
        glow_rgba = (*kdata["glow_rgb"], 1.0)

        # Crisp rest before onset
        kobj.location.z = rest_z
        kobj.color = idle_rgba
        kobj.keyframe_insert(data_path="location", index=2, frame=f_pre)
        kobj.keyframe_insert(data_path="color", frame=f_pre)

        # Depressed & blazing at onset
        kobj.location.z = rest_z + KEY_DEPRESS_Z
        kobj.color = glow_rgba
        kobj.keyframe_insert(data_path="location", index=2, frame=f_start)
        kobj.keyframe_insert(data_path="color", frame=f_start)

        # Held through note end
        kobj.location.z = rest_z + KEY_DEPRESS_Z
        kobj.color = glow_rgba
        kobj.keyframe_insert(data_path="location", index=2, frame=f_end)
        kobj.keyframe_insert(data_path="color", frame=f_end)

        # Crisp release 1 frame after end
        kobj.location.z = rest_z
        kobj.color = idle_rgba
        kobj.keyframe_insert(data_path="location", index=2, frame=f_post)
        kobj.keyframe_insert(data_path="color", frame=f_post)

        # Hammer strike kick upward toward strings (+X rotation lifts +Y hammer head into +Z)
        f_strike = min(total_frames, f_start + 1)
        f_rebound = min(f_end, f_start + 4)
        hobj.rotation_euler.x = 0.0
        hobj.keyframe_insert(data_path="rotation_euler", index=0, frame=f_pre)
        hobj.rotation_euler.x = 0.36
        hobj.keyframe_insert(data_path="rotation_euler", index=0, frame=f_strike)
        if f_rebound > f_strike:
            hobj.rotation_euler.x = 0.10
            hobj.keyframe_insert(data_path="rotation_euler", index=0, frame=f_rebound)
        hobj.rotation_euler.x = 0.0
        hobj.keyframe_insert(data_path="rotation_euler", index=0, frame=f_post)

    # Animate right damper pedal downward from timeline["pedals"]
    damper_pedal.rotation_euler.x = 0.0
    damper_pedal.keyframe_insert(data_path="rotation_euler", index=0, frame=1)
    for pev in timeline["pedals"]:
        f_on = common.sec_to_frame(pev["start_s"], fps)
        f_off = max(f_on + 2, common.sec_to_frame(pev["end_s"], fps))
        f_pre = max(1, f_on - 2)
        f_post = min(total_frames, f_off + 2)

        damper_pedal.rotation_euler.x = 0.0
        damper_pedal.keyframe_insert(data_path="rotation_euler", index=0, frame=f_pre)
        # Positive X rotation lowers the -Y pedal tip downward toward the pedestal
        damper_pedal.rotation_euler.x = 0.26
        damper_pedal.keyframe_insert(data_path="rotation_euler", index=0, frame=min(total_frames, f_on + 1))
        damper_pedal.rotation_euler.x = 0.26
        damper_pedal.keyframe_insert(data_path="rotation_euler", index=0, frame=max(f_on + 1, f_off - 1))
        damper_pedal.rotation_euler.x = 0.0
        damper_pedal.keyframe_insert(data_path="rotation_euler", index=0, frame=f_post)


def _tune_studio_look(
    scene: bpy.types.Scene,
    mats: dict[str, bpy.types.Material],
) -> None:
    """Tune exposure, stage lights, material roughness, and emission strength locally."""
    scene.view_settings.exposure = -0.35

    # Raise FOG_GLOW threshold slightly so only active emissive keys bloom, not rim/floor specular
    if scene.use_nodes and scene.node_tree:
        for node in scene.node_tree.nodes:
            if node.type == "GLARE":
                node.threshold = 1.15

    # Soften stage lighting to eliminate blown-out pedestal/rim glare while keeping rich ebony luster
    light_tweaks = {
        "KeyLight": (580.0, 3.2),
        "TopAccent": (340.0, 3.6),
        "RimLight": (620.0, 2.8),
        "FillLight": (360.0, 3.6),
    }
    for lname, (energy, size) in light_tweaks.items():
        lobj = bpy.data.objects.get(lname)
        if lobj and lobj.data:
            lobj.data.energy = energy
            lobj.data.size = size

    def _set_bsdf(mat_name: str, **inputs: Any) -> None:
        mat = mats.get(mat_name)
        if not mat or not mat.use_nodes:
            return
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf is None:
            return
        for key, val in inputs.items():
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = val

    _set_bsdf("PedestalWood", Roughness=0.42, **{"Coat Weight": 0.08, "Specular IOR Level": 0.35})
    _set_bsdf("StageFloor", Roughness=0.26, **{"Coat Weight": 0.12})
    _set_bsdf("CastIronGold", Roughness=0.42)
    _set_bsdf("IvoryKey", **{"Base Color": (0.58, 0.54, 0.46, 1.0), "Roughness": 0.28, "Coat Weight": 0.15})

    # Lower LuminousElement emission multiplier from 16.0 -> 6.2 so AgX retains rich jewel saturation
    lum = mats.get("LuminousElement")
    if lum and lum.use_nodes:
        for node in lum.node_tree.nodes:
            if node.type == "MATH" and node.operation == "MULTIPLY":
                node.inputs[1].default_value = 6.2


def build_scene() -> dict[str, Any]:
    """Assemble the full Bosanquet 53-EDO Concert Grand Piano scene & timeline."""
    scene = common.reset_scene(fps=24, res_x=1920, res_y=1080, taa_samples=16)
    mats = common.create_studio_materials()
    common.build_concert_stage(mats, pedestal_radius=1.65, pedestal_height=PEDESTAL_HEIGHT, light_target_z=0.90)
    _tune_studio_look(scene, mats)

    piano_col = bpy.data.collections.new("BosanquetPiano")
    scene.collection.children.link(piano_col)

    _build_cabinet_and_legs(piano_col, mats)
    damper_pedal = _build_pedal_lyre(piano_col, mats)
    _build_interior_harp_and_strings(piano_col, mats)
    keys, hammers = _build_bosanquet_keyboard_and_hammers(piano_col, mats)

    timeline = common.load_score_timeline(SCORE_JSON_PATH, WAV_PATH, fps=24)
    _animate_timeline(timeline, keys, hammers, damper_pedal)

    total_frames = int(timeline["total_frames"])
    # Hero 3/4 orbit sweeping from front-right into higher terrace angle and back
    cam_keyframes = [
        (1, (2.68, -3.22, 1.92)),
        (round(total_frames * 0.30), (2.06, -3.38, 2.08)),
        (round(total_frames * 0.60), (1.58, -3.44, 2.12)),
        (round(total_frames * 0.85), (2.32, -3.22, 1.98)),
        (total_frames, (2.74, -3.02, 1.88)),
    ]
    common.setup_orbit_camera(
        target_pos=(-0.02, 0.02, 0.77),
        keyframes_cam_loc=cam_keyframes,
        lens_mm=32.0,
        dof_fstop=8.0,
    )
    return timeline


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    stills_only = "--stills-only" in argv
    render_video_flag = "--render-video" in argv

    timeline = build_scene()

    if stills_only:
        common.save_blend(BLEND_PATH)
        frame_specs = [
            ("terrace_low", common.sec_to_frame(1.2, 24)),
            ("terrace_high", common.sec_to_frame(8.2, 24)),
            ("finale", common.sec_to_frame(11.2, 24)),
        ]
        rendered = common.render_diagnostic_stills(frame_specs, OUT_DIR, "diag_piano")
        print(f"[piano_bosanquet] Saved blend: {BLEND_PATH}")
        for path in rendered:
            print(f"[piano_bosanquet] Rendered still: {path}")

    if render_video_flag:
        common.render_video(
            WEBM_PATH,
            WAV_PATH,
            int(timeline["total_frames"]),
            TMP_FRAMES_DIR,
            fps=24,
        )


if __name__ == "__main__":
    main()
