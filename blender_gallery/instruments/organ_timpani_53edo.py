"""The 53-Rank Pipe Organ & 4 Copper 53-EDO Concert Timpani — Blender 4.2 EEVEE Next showcase."""

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

SCORE_PATH = REPO_ROOT / "scores" / "showcase_3d" / "07_organ_timpani_53edo.json"
WAV_PATH = REPO_ROOT / "output" / "showcase_3d" / "07_organ_timpani_53edo.wav"
BLEND_PATH = REPO_ROOT / "output" / "showcase_3d" / "07_organ_timpani_53edo.blend"
WEBM_PATH = REPO_ROOT / "output" / "showcase_3d" / "07_organ_timpani_53edo.webm"
STILLS_DIR = REPO_ROOT / "output" / "showcase_3d"
TMP_FRAMES_DIR = Path("/tmp/frames_organ_timpani_53edo")

PEDESTAL_Z = 0.09
NUM_PIPES = 53
PIPE_STEP_MIN = 0
PIPE_STEP_MAX = 52
TIMPANI_CENTERS = (-106, -92, -84, -75)  # 4 concert kettles (32", 29", 26", 23")


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


def _add_box(
    bm: bmesh.types.BMesh,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    rot_euler: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> None:
    mat_rot = mathutils.Euler(rot_euler, "XYZ").to_matrix().to_4x4()
    mat = Matrix.Translation(center) @ mat_rot @ Matrix.Diagonal((*size, 1.0))
    bmesh.ops.create_cube(bm, size=1.0, matrix=mat)


def _add_cylinder(
    bm: bmesh.types.BMesh,
    p0: Vector,
    p1: Vector,
    r0: float,
    r1: float,
    segments: int = 12,
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


def _loft_rings(
    bm: bmesh.types.BMesh,
    rings: list[list[bmesh.types.BMVert]],
    cap_start: bool = False,
    cap_end: bool = False,
) -> None:
    n_seg = len(rings[0])
    for i in range(len(rings) - 1):
        r0 = rings[i]
        r1 = rings[i + 1]
        for j in range(n_seg):
            jn = (j + 1) % n_seg
            bm.faces.new((r0[j], r0[jn], r1[jn], r1[j]))
    if cap_start:
        bm.faces.new(list(reversed(rings[0])))
    if cap_end:
        bm.faces.new(rings[-1])


def _slot_for_pitch_class(pc: int) -> int:
    """Bijective acoustic A-frame placement: pc=0 at center spire (slot 26), 1..52 balanced L/R."""
    if pc == 0:
        return 26
    dist = (pc + 1) // 2  # 1..26 outward from center
    # Alternates pairs cleanly so major 3rd (17), fifth (31), septimal 7th (43) balance L/R
    side = -1 if ((pc + ((pc - 1) // 4)) % 2 == 1) else 1
    return 26 + side * dist


def _pipe_geometry_params(slot: int) -> tuple[float, float, float, float]:
    """Return (x, pipe_len, radius, foot_height) for facade slot 0..52."""
    x = (slot - 26) * 0.0435  # spans [-1.131, +1.131]
    d_norm = abs(slot - 26) / 26.0
    # Cathedral A-frame wingspan: tallest at center (z~2.60m), tapering gracefully to wings
    pipe_len = 1.32 - 0.80 * (d_norm ** 0.88)
    radius = 0.0255 - 0.0120 * (d_norm ** 0.85)
    foot_h = 0.14 + 0.12 * (1.0 - d_norm)
    return x, pipe_len, radius, foot_h


def build_organ_case_and_console(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> None:
    """Build stepped DarkRosewood & WarmMahogany cathedral case, gilded corbels, twin-manual console, and pedalboard."""
    bm_rose = bmesh.new()
    bm_mahog = bmesh.new()
    bm_gold = bmesh.new()
    bm_ivory = bmesh.new()
    bm_ebony = bmesh.new()

    # 1) Stepped base plinth seated flush at PEDESTAL_Z (z = 0.09)
    _add_box(bm_rose, (0.0, 0.44, PEDESTAL_Z + 0.030), (1.36, 0.56, 0.060))
    _add_box(bm_gold, (0.0, 0.44, PEDESTAL_Z + 0.065), (1.32, 0.54, 0.012))
    _add_box(bm_rose, (0.0, 0.45, PEDESTAL_Z + 0.58), (1.24, 0.48, 1.02))

    # Recessed WarmMahogany wainscot panels on front & flanks
    for sx in (-1.0, 0.0, 1.0):
        px = sx * 0.41
        pw = 0.34 if sx != 0.0 else 0.38
        _add_box(bm_mahog, (px, 0.205, PEDESTAL_Z + 0.42), (pw, 0.024, 0.58))
        _add_box(bm_gold, (px, 0.194, PEDESTAL_Z + 0.72), (pw + 0.02, 0.010, 0.014))
        _add_box(bm_gold, (px, 0.194, PEDESTAL_Z + 0.12), (pw + 0.02, 0.010, 0.014))
    for sx in (-1.0, 1.0):
        _add_box(bm_mahog, (sx * 0.625, 0.45, PEDESTAL_Z + 0.55), (0.022, 0.36, 0.74))

    # 2) Overhanging upper windchest cornice (z = 1.17 .. 1.28) supporting all 53 pipes
    _add_box(bm_rose, (0.0, 0.41, 1.21), (2.34, 0.46, 0.065))
    _add_box(bm_gold, (0.0, 0.41, 1.175), (2.38, 0.48, 0.016))
    _add_box(bm_rose, (0.0, 0.40, 1.255), (2.40, 0.49, 0.042))
    _add_box(bm_gold, (0.0, 0.40, 1.278), (2.42, 0.50, 0.012))

    # 3) Sculpted gilded S-scroll corbels supporting the overhanging wing chests
    for sx in (-1.0, 1.0):
        for cx in (0.72, 0.92, 1.10):
            x_pos = sx * cx
            pts = [
                Vector((x_pos, 0.26, 0.80)),
                Vector((x_pos, 0.24, 0.94)),
                Vector((x_pos, 0.21, 1.07)),
                Vector((x_pos, 0.18, 1.17)),
            ]
            # Offset outward diagonally for dramatic corbel flare
            inner_x = sx * 0.61
            corbel_pts = [
                Vector((inner_x, 0.29, 0.78 + (cx - 0.72) * 0.15)),
                Vector((inner_x + sx * 0.28 * (cx - 0.60), 0.25, 0.96)),
                Vector((x_pos, 0.22, 1.10)),
                Vector((x_pos, 0.22, 1.17)),
            ]
            for i in range(len(corbel_pts) - 1):
                r_a = 0.022 - i * 0.003
                r_b = 0.019 - i * 0.003
                _add_cylinder(bm_gold, corbel_pts[i], corbel_pts[i + 1], r_a, r_b, segments=10)
            # Scroll volute medallion at tip
            bmesh.ops.create_uvsphere(
                bm_gold,
                u_segments=10,
                v_segments=8,
                radius=0.022,
                matrix=Matrix.Translation((x_pos, 0.19, 1.155)) @ Matrix.Diagonal((0.8, 1.2, 1.2, 1.0)),
            )

    # 4) Twin-manual console drawer at z ~ 0.95m (y = -0.07 .. +0.21)
    # Console deck & side cheeks
    _add_box(bm_rose, (0.0, 0.07, 0.86), (1.02, 0.28, 0.040))
    _add_box(bm_gold, (0.0, -0.072, 0.86), (1.03, 0.012, 0.026))
    for sx in (-1.0, 1.0):
        _add_box(bm_rose, (sx * 0.49, 0.07, 0.95), (0.042, 0.28, 0.16))
        _add_box(bm_mahog, (sx * 0.43, 0.11, 0.96), (0.075, 0.16, 0.14))
        # Console support bracket corbels under drawer
        _add_cylinder(
            bm_gold,
            Vector((sx * 0.42, 0.21, 0.68)),
            Vector((sx * 0.42, -0.03, 0.85)),
            0.018,
            0.014,
            segments=10,
        )
        # Drawstop knobs (4 per side)
        for row_i in range(2):
            for col_i in range(2):
                kx = sx * (0.405 + col_i * 0.032)
                kz = 0.92 + row_i * 0.048
                _add_cylinder(
                    bm_gold,
                    Vector((kx, 0.035, kz)),
                    Vector((kx, 0.005, kz)),
                    0.005,
                    0.005,
                    segments=8,
                )
                bmesh.ops.create_uvsphere(
                    bm_ivory,
                    u_segments=10,
                    v_segments=6,
                    radius=0.010,
                    matrix=Matrix.Translation((kx, 0.002, kz)) @ Matrix.Diagonal((1.0, 0.55, 1.0, 1.0)),
                )

    # Lower (Great) & Upper (Swell) Manuals at z=0.895 and z=0.948
    n_nat = 29
    key_span = 0.72
    kw = key_span / n_nat
    for manual_idx, (mz, my) in enumerate(((0.895, -0.01), (0.948, 0.075))):
        _add_box(bm_mahog, (0.0, my + 0.01, mz - 0.014), (0.76, 0.11, 0.014))
        for k in range(n_nat):
            kx = -key_span * 0.5 + (k + 0.5) * kw
            _add_box(bm_ivory, (kx, my - 0.01, mz), (kw * 0.86, 0.085, 0.012))
            if k % 7 not in (2, 6) and k < n_nat - 1:
                _add_box(bm_ebony, (kx + kw * 0.5, my + 0.012, mz + 0.008), (kw * 0.54, 0.052, 0.011))

    # Carved music desk above manuals (z = 1.01 .. 1.16)
    _add_box(bm_mahog, (0.0, 0.145, 1.08), (0.62, 0.016, 0.14), rot_euler=(math.radians(-18.0), 0.0, 0.0))
    _add_box(bm_gold, (0.0, 0.115, 1.02), (0.64, 0.032, 0.012))

    # 5) Pedalboard tucked cleanly on pedestal floor (z = 0.09..0.145)
    _add_box(bm_rose, (0.0, 0.01, PEDESTAL_Z + 0.012), (0.88, 0.28, 0.024))
    n_pedals = 17
    for p in range(n_pedals):
        px = -0.38 + p * (0.76 / (n_pedals - 1))
        is_sharp = (p % 7) in (1, 3, 5)
        bm_target = bm_ebony if is_sharp else bm_mahog
        _add_box(bm_target, (px, 0.0, PEDESTAL_Z + 0.034), (0.022, 0.24, 0.018))

    # 6) Cathedral A-frame back wall & raking gable cornice behind the 53 pipes
    # Build tapered stepped gable box matching the A-frame pipe tops
    n_gable_steps = 11
    for g in range(n_gable_steps):
        frac = g / float(n_gable_steps - 1)
        gx_half = 1.16 * (1.0 - 0.88 * frac)
        gz = 1.28 + 0.44 + frac * 0.84
        _add_box(bm_rose, (0.0, 0.46, gz), (gx_half * 2.0, 0.34, 0.10))
        if g % 2 == 0:
            _add_box(bm_mahog, (0.0, 0.30, gz), (gx_half * 1.90, 0.02, 0.075))

    # Twin raking BrushedGold A-frame gable rafters & center spire finial
    apex = Vector((0.0, 0.28, 2.63))
    for sx in (-1.0, 1.0):
        wing_tip = Vector((sx * 1.18, 0.28, 1.77))
        _add_cylinder(bm_gold, wing_tip, apex, 0.020, 0.024, segments=10)
        # Wing tip finial urn
        _add_cylinder(bm_gold, wing_tip, wing_tip + Vector((0.0, 0.0, 0.10)), 0.026, 0.005, segments=10)
    # Central spire finial
    _add_cylinder(bm_gold, apex, apex + Vector((0.0, 0.0, 0.14)), 0.034, 0.004, segments=12)
    bmesh.ops.create_uvsphere(
        bm_gold, u_segments=12, v_segments=8, radius=0.026, matrix=Matrix.Translation(apex + Vector((0.0, 0.0, 0.04)))
    )

    # Horizontal gilded pipe-rack stay bars across the facade
    _add_cylinder(bm_gold, Vector((-1.15, 0.215, 1.62)), Vector((1.15, 0.215, 1.62)), 0.007, 0.007, segments=8)
    _add_cylinder(bm_gold, Vector((-0.65, 0.215, 2.04)), Vector((0.65, 0.215, 2.04)), 0.007, 0.007, segments=8)

    _make_mesh_obj(col, "OrganCaseRosewood", bm_rose, mats["DarkRosewood"], smooth=False, bevel_w=0.004)
    _make_mesh_obj(col, "OrganCaseMahogany", bm_mahog, mats["WarmMahogany"], smooth=False, bevel_w=0.003)
    _make_mesh_obj(col, "OrganCaseGoldTrim", bm_gold, mats["BrushedGold"], smooth=True)
    _make_mesh_obj(col, "OrganConsoleIvory", bm_ivory, mats["IvoryKey"], smooth=False, bevel_w=0.001)
    _make_mesh_obj(col, "OrganConsoleEbony", bm_ebony, mats["GlossEbony"], smooth=False, bevel_w=0.001)


def build_53_organ_pipes(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[int, dict[str, Any]]:
    """Build 53 graduated facade pipes (BrushedGold & PewterMetal) + 53 LuminousElement mouth/crown rings."""
    bm_gold_pipes = bmesh.new()
    bm_pewter_pipes = bmesh.new()
    pipes_by_pc: dict[int, dict[str, Any]] = {}

    z_base = 1.28
    y_pipe = 0.245

    for pc in range(NUM_PIPES):
        slot = _slot_for_pitch_class(pc)
        x, pipe_len, radius, foot_h = _pipe_geometry_params(slot)
        use_gold = (slot % 2 == 0)
        bm_body = bm_gold_pipes if use_gold else bm_pewter_pipes

        p_bot = Vector((x, y_pipe, z_base))
        p_mouth = Vector((x, y_pipe, z_base + foot_h))
        p_top = Vector((x, y_pipe, z_base + pipe_len))
        p_cap = Vector((x, y_pipe, z_base + pipe_len + radius * 1.4))

        # Conical foot + cylindrical pipe body + mitered crown cone (12 radial segs keeps polys compact)
        _add_cylinder(bm_body, p_bot, p_mouth, radius * 0.40, radius, segments=12)
        _add_cylinder(bm_body, p_mouth, p_top, radius, radius, segments=12)
        _add_cylinder(bm_body, p_top, p_cap, radius * 1.04, radius * 0.12, segments=12)

        # LuminousElement object per pitch class: glowing labium pipe-mouth + glowing crown ring
        bm_lum = bmesh.new()
        # Pipe-mouth (labium slot facing -Y audience)
        mouth_h = max(0.024, radius * 1.45)
        _add_box(
            bm_lum,
            (x, y_pipe - radius * 0.88, z_base + foot_h + mouth_h * 0.55),
            (radius * 1.15, radius * 0.34, mouth_h),
        )
        # Crown ring near top of pipe
        ring_z = z_base + pipe_len - 0.032
        ring_r = radius * 1.08
        minor_r = max(0.0045, radius * 0.20)
        n_maj, n_min = 14, 6
        rings: list[list[bmesh.types.BMVert]] = []
        for i in range(n_maj):
            ang = 2.0 * math.pi * i / n_maj
            ca, sa = math.cos(ang), math.sin(ang)
            r_verts = []
            for j in range(n_min):
                phi = 2.0 * math.pi * j / n_min
                rr = ring_r + minor_r * math.cos(phi)
                zz = ring_z + minor_r * math.sin(phi)
                r_verts.append(bm_lum.verts.new((x + rr * ca, y_pipe + rr * sa, zz)))
            rings.append(r_verts)
        # Connect torus loop
        for i in range(n_maj):
            inext = (i + 1) % n_maj
            for j in range(n_min):
                jnext = (j + 1) % n_min
                bm_lum.faces.new((rings[i][j], rings[inext][j], rings[inext][jnext], rings[i][jnext]))

        lum_obj = _make_mesh_obj(col, f"OrganPipeGlow_{pc:02d}", bm_lum, mats["LuminousElement"], smooth=True)
        rgb = common.vivid_53edo_color(pc)
        idle_dark = (rgb[0] * 0.18, rgb[1] * 0.18, rgb[2] * 0.18, 0.02)
        lum_obj.color = idle_dark

        pipes_by_pc[pc] = {
            "obj": lum_obj,
            "rgb": rgb,
            "idle_rgba": idle_dark,
        }

    _make_mesh_obj(col, "OrganPipesGold", bm_gold_pipes, mats["BrushedGold"], smooth=True)
    _make_mesh_obj(col, "OrganPipesPewter", bm_pewter_pipes, mats["PewterMetal"], smooth=True)
    return pipes_by_pc


def build_4_copper_timpani(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> list[dict[str, Any]]:
    """Build 4 HammeredCopper concert timpani on BrushedGold struts with CalfskinHeads, mallets & ripple rings."""
    drum_specs = [
        # (name, x, y, r_head, z_rim, center_step)
        ("Timpani32_Bass", -0.94, -0.46, 0.290, 0.83, -106),
        ("Timpani29_Tenor", -0.54, -0.74, 0.255, 0.81, -92),
        ("Timpani26_Baritone", 0.54, -0.74, 0.230, 0.79, -84),
        ("Timpani23_High", 0.94, -0.46, 0.205, 0.77, -75),
    ]

    bm_copper = bmesh.new()
    bm_gold = bmesh.new()
    bm_brass = bmesh.new()
    bm_rose = bmesh.new()

    timpani_list: list[dict[str, Any]] = []

    for idx, (dname, dx, dy, r_head, z_rim, center_step) in enumerate(drum_specs):
        # 1) Parabolic HammeredCopper kettle bowl
        bowl_bot_z = PEDESTAL_Z + 0.16
        bowl_top_z = z_rim - 0.02
        n_radial = 24
        n_profile = 9
        rings: list[list[bmesh.types.BMVert]] = []
        for pi in range(n_profile):
            u = pi / float(n_profile - 1)  # 0 at bottom vent, 1 at rim
            r_cur = r_head * (0.20 + 0.80 * (u ** 0.48))
            z_cur = bowl_bot_z + (bowl_top_z - bowl_bot_z) * (u ** 1.15)
            ring = []
            for ri in range(n_radial):
                ang = 2.0 * math.pi * ri / n_radial
                ring.append(bm_copper.verts.new((dx + r_cur * math.cos(ang), dy + r_cur * math.sin(ang), z_cur)))
            rings.append(ring)
        _loft_rings(bm_copper, rings, cap_start=True, cap_end=False)

        # Copper bottom vent cap
        bmesh.ops.create_uvsphere(
            bm_copper,
            u_segments=12,
            v_segments=6,
            radius=r_head * 0.22,
            matrix=Matrix.Translation((dx, dy, bowl_bot_z)) @ Matrix.Diagonal((1.0, 1.0, 0.55, 1.0)),
        )

        # 2) BrushedGold base spider + pedal + 6 inclined struts + counterhoop + T-handle tuning lugs
        r_base = r_head * 0.76
        # Base ring seated on PEDESTAL_Z
        _add_cylinder(
            bm_gold,
            Vector((dx, dy, PEDESTAL_Z)),
            Vector((dx, dy, PEDESTAL_Z + 0.022)),
            r_base,
            r_base * 0.96,
            segments=24,
        )
        # Pedal foot housing facing front-center
        yaw_to_front = math.atan2(-dx, -dy) if abs(dx) > 0.01 else 0.0
        _add_box(
            bm_rose,
            (dx, dy - r_base * 0.85, PEDESTAL_Z + 0.032),
            (0.08, 0.15, 0.056),
            rot_euler=(0.0, 0.0, yaw_to_front * 0.25),
        )
        _add_box(
            bm_brass,
            (dx, dy - r_base * 0.96, PEDESTAL_Z + 0.052),
            (0.055, 0.12, 0.012),
            rot_euler=(0.22, 0.0, yaw_to_front * 0.25),
        )

        # Counterhoop ring & 6 tension struts
        n_struts = 6
        hoop_r = r_head + 0.020
        for s_i in range(n_struts):
            ang = 2.0 * math.pi * (s_i + 0.5) / n_struts
            ca, sa = math.cos(ang), math.sin(ang)
            p_foot = Vector((dx + r_base * 0.92 * ca, dy + r_base * 0.92 * sa, PEDESTAL_Z + 0.015))
            p_top = Vector((dx + hoop_r * ca, dy + hoop_r * sa, z_rim))
            _add_cylinder(bm_gold, p_foot, p_top, 0.011, 0.009, segments=8)
            # Tuning lug T-handle at rim
            _add_cylinder(bm_brass, p_top, p_top + Vector((0.0, 0.0, 0.036)), 0.006, 0.006, segments=8)
            _add_cylinder(
                bm_brass,
                p_top + Vector((-0.018 * sa, 0.018 * ca, 0.036)),
                p_top + Vector((0.018 * sa, -0.018 * ca, 0.036)),
                0.004,
                0.004,
                segments=6,
            )

        # Counterhoop torus
        n_maj, n_min = 28, 8
        h_rings: list[list[bmesh.types.BMVert]] = []
        for i in range(n_maj):
            ang = 2.0 * math.pi * i / n_maj
            ca, sa = math.cos(ang), math.sin(ang)
            rv = []
            for j in range(n_min):
                phi = 2.0 * math.pi * j / n_min
                rr = hoop_r + 0.013 * math.cos(phi)
                zz = z_rim - 0.006 + 0.013 * math.sin(phi)
                rv.append(bm_gold.verts.new((dx + rr * ca, dy + rr * sa, zz)))
            h_rings.append(rv)
        for i in range(n_maj):
            inext = (i + 1) % n_maj
            for j in range(n_min):
                jnext = (j + 1) % n_min
                bm_gold.faces.new((h_rings[i][j], h_rings[inext][j], h_rings[inext][jnext], h_rings[i][jnext]))

        # 3) Individual CalfskinHead membrane object (animated vertical bounce on impact)
        bm_head = bmesh.new()
        bmesh.ops.create_cone(
            bm_head,
            cap_ends=True,
            cap_tris=False,
            segments=28,
            radius1=r_head,
            radius2=r_head,
            depth=0.010,
        )
        head_obj = _make_mesh_obj(col, f"{dname}_Head", bm_head, mats["CalfskinHead"], smooth=True)
        head_obj.location = (dx, dy, z_rim - 0.002)

        # 4) Luminous Ripple Ring hovering just above drumhead (LuminousElement)
        bm_ring = bmesh.new()
        n_rmaj, n_rmin = 28, 8
        r_ring = r_head * 0.82
        ring_verts: list[list[bmesh.types.BMVert]] = []
        for i in range(n_rmaj):
            ang = 2.0 * math.pi * i / n_rmaj
            ca, sa = math.cos(ang), math.sin(ang)
            rv = []
            for j in range(n_rmin):
                phi = 2.0 * math.pi * j / n_rmin
                rr = r_ring + 0.008 * math.cos(phi)
                zz = 0.006 * math.sin(phi)
                rv.append(bm_ring.verts.new((rr * ca, rr * sa, zz)))
            ring_verts.append(rv)
        for i in range(n_rmaj):
            inext = (i + 1) % n_rmaj
            for j in range(n_rmin):
                jnext = (j + 1) % n_rmin
                bm_ring.faces.new((ring_verts[i][j], ring_verts[inext][j], ring_verts[inext][jnext], ring_verts[i][jnext]))
        # Add inner secondary pulse ring
        r_inner = r_head * 0.48
        ring_verts2: list[list[bmesh.types.BMVert]] = []
        for i in range(n_rmaj):
            ang = 2.0 * math.pi * i / n_rmaj
            ca, sa = math.cos(ang), math.sin(ang)
            rv = []
            for j in range(n_rmin):
                phi = 2.0 * math.pi * j / n_rmin
                rr = r_inner + 0.006 * math.cos(phi)
                zz = 0.005 * math.sin(phi)
                rv.append(bm_ring.verts.new((rr * ca, rr * sa, zz)))
            ring_verts2.append(rv)
        for i in range(n_rmaj):
            inext = (i + 1) % n_rmaj
            for j in range(n_rmin):
                jnext = (j + 1) % n_rmin
                bm_ring.faces.new((ring_verts2[i][j], ring_verts2[inext][j], ring_verts2[inext][jnext], ring_verts2[i][jnext]))

        ripple_obj = _make_mesh_obj(col, f"{dname}_Ripple", bm_ring, mats["LuminousElement"], smooth=True)
        ripple_obj.location = (dx, dy, z_rim + 0.007)
        rgb = common.vivid_53edo_color(center_step)
        ripple_obj.color = (*rgb, 0.0)
        ripple_obj.scale = (0.0, 0.0, 0.0)

        # 5) Floating Animated Felt Mallet poised above outer-front rim
        # Pivot at outer handle butt so rotating around local X strikes felt ball cleanly onto drumhead!
        bm_mallet = bmesh.new()
        mallet_len = r_head * 1.15
        # Bamboo/Mahogany shaft along -Y in local space -> handle at (0,0,0), felt head at (0, -mallet_len, 0)
        _add_cylinder(
            bm_mallet,
            Vector((0.0, 0.0, 0.0)),
            Vector((0.0, -mallet_len, 0.0)),
            0.005,
            0.0038,
            segments=8,
        )
        # Butt pommel
        bmesh.ops.create_uvsphere(
            bm_mallet, u_segments=8, v_segments=6, radius=0.008, matrix=Matrix.Translation((0.0, 0.0, 0.0))
        )
        # Felt head (assign material index 1 for Horsehair white felt)
        bm_felt = bmesh.new()
        bmesh.ops.create_uvsphere(
            bm_felt,
            u_segments=12,
            v_segments=8,
            radius=0.022,
            matrix=Matrix.Translation((0.0, -mallet_len, 0.0)) @ Matrix.Diagonal((1.0, 0.85, 0.90, 1.0)),
        )
        me_felt = bpy.data.meshes.new("_tmp_felt")
        bm_felt.to_mesh(me_felt)
        bm_felt.free()
        for p in me_felt.polygons:
            p.material_index = 1
        bm_mallet.from_mesh(me_felt)
        bpy.data.meshes.remove(me_felt)

        mallet_obj = _make_mesh_obj(col, f"{dname}_Mallet", bm_mallet, mats["WarmMahogany"], smooth=True)
        mallet_obj.data.materials.append(mats["Horsehair"])
        # Place pivot just outside drum rim toward front-outer diagonal, facing inward toward drumhead strike zone
        strike_ang = math.radians(-115.0 if dx < 0 else -65.0)
        pivot_dist = r_head * 1.48
        px = dx + pivot_dist * math.cos(strike_ang)
        py = dy + pivot_dist * math.sin(strike_ang)
        mallet_obj.location = (px, py, z_rim + 0.032)
        # Orient local -Y toward drum center
        dir_to_center = Vector((dx - px, dy - py, 0.0)).normalized()
        yaw = math.atan2(dir_to_center.x, -dir_to_center.y)
        mallet_obj.rotation_euler = (-0.36, 0.0, yaw)  # negative X tilts -Y tip UPWARD (+Z)

        timpani_list.append(
            {
                "name": dname,
                "center_step": center_step,
                "head_obj": head_obj,
                "head_rest_z": z_rim - 0.002,
                "ripple_obj": ripple_obj,
                "mallet_obj": mallet_obj,
                "mallet_rest_rx": -0.36,
                "mallet_hit_rx": 0.03,
            }
        )

    _make_mesh_obj(col, "TimpaniBowls", bm_copper, mats["HammeredCopper"], smooth=True)
    _make_mesh_obj(col, "TimpaniGoldStruts", bm_gold, mats["BrushedGold"], smooth=True)
    _make_mesh_obj(col, "TimpaniBrassHardware", bm_brass, mats["PolishedBrass"], smooth=True)
    _make_mesh_obj(col, "TimpaniPedalHousings", bm_rose, mats["DarkRosewood"], smooth=False, bevel_w=0.003)
    return timpani_list


def _drum_index_for_step(step: int) -> int:
    folded = common.fold_step_to_range(step, -106, -53)
    if folded >= -64:
        return 3  # -53 octave pedal up on highest 23" kettle
    return min(range(len(TIMPANI_CENTERS)), key=lambda idx: abs(folded - TIMPANI_CENTERS[idx]))


def animate_organ_and_timpani(
    timeline: dict[str, Any],
    pipes_by_pc: dict[int, dict[str, Any]],
    timpani_list: list[dict[str, Any]],
) -> None:
    """Keyframe 53 pipe-organ glows, 4 timpani mallet strikes, drumhead bounces & luminous ripples."""
    fps = int(timeline["fps"])
    total_frames = int(timeline["total_frames"])

    organ_notes: list[dict[str, Any]] = []
    timpani_notes: list[dict[str, Any]] = []
    for ev in timeline.get("notes", []):
        tid = ev.get("track_id", "")
        inst = ev.get("instrument", "")
        if tid == "timpani" or inst == "timpani":
            timpani_notes.append(ev)
        elif tid == "church_organ" or inst == "church_organ":
            organ_notes.append(ev)

    # 1) Animate 53 Organ Pipes (folded to 0..52)
    pipes_events: dict[int, list[dict[str, Any]]] = {pc: [] for pc in range(NUM_PIPES)}
    for ev in organ_notes:
        pc = common.fold_step_to_range(int(ev["step"]), PIPE_STEP_MIN, PIPE_STEP_MAX)
        pipes_events[pc].append(ev)

    for pc, pinfo in pipes_by_pc.items():
        obj = pinfo["obj"]
        idle_rgba = pinfo["idle_rgba"]
        obj.color = idle_rgba
        obj.keyframe_insert(data_path="color", frame=1)

        evts = sorted(pipes_events[pc], key=lambda x: x["start_s"])
        if not evts:
            continue
        const_frames: set[int] = {1}

        for i, ev in enumerate(evts):
            f0 = common.sec_to_frame(ev["start_s"], fps)
            f_end = min(total_frames, max(f0 + 2, common.sec_to_frame(ev["end_s"], fps)))
            next_f0 = common.sec_to_frame(evts[i + 1]["start_s"], fps) if i + 1 < len(evts) else total_frames + 10
            rgb = common.vivid_53edo_color(int(ev["step"]))
            peak_a = min(1.0, 0.78 + 0.25 * float(ev.get("vel", 0.7)))

            if f0 > 2:
                prev_f = f0 - 1
                obj.color = idle_rgba
                obj.keyframe_insert(data_path="color", frame=prev_f)
                const_frames.add(prev_f)

            # Swell / onset glow
            swell_mode = ev.get("swell")
            if swell_mode == "cresc":
                obj.color = (*rgb, peak_a * 0.68)
                obj.keyframe_insert(data_path="color", frame=f0)
                f_mid = min(next_f0 - 2, max(f0 + 2, (f0 + f_end) // 2))
                obj.color = (*rgb, peak_a)
                obj.keyframe_insert(data_path="color", frame=f_mid)
            else:
                obj.color = (*rgb, peak_a)
                obj.keyframe_insert(data_path="color", frame=f0)

            hold_end = min(f_end, next_f0 - 2)
            if hold_end > f0:
                obj.color = (*rgb, peak_a * 0.92)
                obj.keyframe_insert(data_path="color", frame=hold_end)

            rel_f = min(total_frames, hold_end + 2)
            if rel_f < next_f0:
                obj.color = idle_rgba
                obj.keyframe_insert(data_path="color", frame=rel_f)
                const_frames.add(rel_f)

        common.set_constant_segment(obj, "color", 3, const_frames)

    # 2) Animate 4 Concert Timpani (mallet strikes, drumhead dip, luminous ripple rings)
    drum_events: list[list[dict[str, Any]]] = [[] for _ in timpani_list]
    for ev in timpani_notes:
        d_idx = _drum_index_for_step(int(ev["step"]))
        drum_events[d_idx].append(ev)

    for d_idx, drum in enumerate(timpani_list):
        head_obj = drum["head_obj"]
        head_z0 = drum["head_rest_z"]
        ripple_obj = drum["ripple_obj"]
        mallet_obj = drum["mallet_obj"]
        rx_rest = drum["mallet_rest_rx"]
        rx_hit = drum["mallet_hit_rx"]

        head_obj.location.z = head_z0
        head_obj.keyframe_insert(data_path="location", index=2, frame=1)

        ripple_obj.color[3] = 0.0
        ripple_obj.scale = (0.0, 0.0, 0.0)
        ripple_obj.keyframe_insert(data_path="color", frame=1)
        ripple_obj.keyframe_insert(data_path="scale", frame=1)

        mallet_obj.rotation_euler.x = rx_rest
        mallet_obj.keyframe_insert(data_path="rotation_euler", index=0, frame=1)

        evts = sorted(drum_events[d_idx], key=lambda x: x["start_s"])
        const_ripple: set[int] = {1}

        for i, ev in enumerate(evts):
            f0 = common.sec_to_frame(ev["start_s"], fps)
            next_f0 = common.sec_to_frame(evts[i + 1]["start_s"], fps) if i + 1 < len(evts) else total_frames + 10
            vel = float(ev.get("vel", 0.8))
            rgb = common.vivid_53edo_color(int(ev["step"]))

            # Mallet downward strike -> crisp rebound
            f_up = max(1, f0 - 2)
            if i == 0 or (f_up > common.sec_to_frame(evts[i - 1]["start_s"], fps) + 1):
                mallet_obj.rotation_euler.x = rx_rest
                mallet_obj.keyframe_insert(data_path="rotation_euler", index=0, frame=f_up)

            mallet_obj.rotation_euler.x = rx_hit
            mallet_obj.keyframe_insert(data_path="rotation_euler", index=0, frame=f0)

            f_reb = min(total_frames, f0 + 3, next_f0 - 1)
            if f_reb > f0:
                mallet_obj.rotation_euler.x = rx_rest * 0.85
                mallet_obj.keyframe_insert(data_path="rotation_euler", index=0, frame=f_reb)
            if f0 + 5 < next_f0:
                mallet_obj.rotation_euler.x = rx_rest
                mallet_obj.keyframe_insert(data_path="rotation_euler", index=0, frame=min(total_frames, f0 + 5))

            # Drumhead impact depression
            if f0 > 2:
                head_obj.location.z = head_z0
                head_obj.keyframe_insert(data_path="location", index=2, frame=f0 - 1)
            head_obj.location.z = head_z0 - 0.008 * vel
            head_obj.keyframe_insert(data_path="location", index=2, frame=f0)
            head_obj.location.z = head_z0
            head_obj.keyframe_insert(data_path="location", index=2, frame=min(total_frames, f0 + 2, next_f0 - 1))

            # Luminous ripple ring burst & expansion
            if f0 > 2 and (i == 0 or f0 - 1 > common.sec_to_frame(evts[i - 1]["start_s"], fps)):
                ripple_obj.color = (*rgb, 0.0)
                ripple_obj.scale = (0.35, 0.35, 1.0)
                ripple_obj.keyframe_insert(data_path="color", frame=f0 - 1)
                ripple_obj.keyframe_insert(data_path="scale", frame=f0 - 1)
                const_ripple.add(f0 - 1)

            peak_a = min(1.0, 0.78 + 0.25 * vel)
            ripple_obj.color = (*rgb, peak_a)
            ripple_obj.scale = (0.55, 0.55, 1.0)
            ripple_obj.keyframe_insert(data_path="color", frame=f0)
            ripple_obj.keyframe_insert(data_path="scale", frame=f0)

            decay_f = min(total_frames, f0 + max(4, min(14, round(ev["dur_s"] * fps))), next_f0 - 1)
            if decay_f > f0:
                ripple_obj.color = (*rgb, 0.04)
                ripple_obj.scale = (1.06, 1.06, 1.0)
                ripple_obj.keyframe_insert(data_path="color", frame=decay_f)
                ripple_obj.keyframe_insert(data_path="scale", frame=decay_f)
            if decay_f + 1 < next_f0 and decay_f + 1 <= total_frames:
                ripple_obj.color = (*rgb, 0.0)
                ripple_obj.scale = (0.0, 0.0, 0.0)
                ripple_obj.keyframe_insert(data_path="color", frame=decay_f + 1)
                ripple_obj.keyframe_insert(data_path="scale", frame=decay_f + 1)
                const_ripple.add(decay_f + 1)

        common.set_constant_segment(ripple_obj, "color", -1, const_ripple)
        common.set_constant_segment(ripple_obj, "scale", -1, const_ripple)


def build_instrument(
    mats: dict[str, bpy.types.Material],
    timeline: dict[str, Any],
    *,
    collection_name: str = "OrganTimpani53EDO",
    anchor_location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    anchor_rotation_z_deg: float = 0.0,
    anchor_scale: float = 1.0,
) -> bpy.types.Object:
    """Build and animate the 53-Rank Pipe Organ & 4 Copper Timpani inside collection_name mounted to anchor."""
    col = bpy.data.collections.new(collection_name)
    bpy.context.scene.collection.children.link(col)

    build_organ_case_and_console(col, mats)
    pipes_by_pc = build_53_organ_pipes(col, mats)
    timpani_list = build_4_copper_timpani(col, mats)

    animate_organ_and_timpani(timeline, pipes_by_pc, timpani_list)
    return common.parent_collection_to_anchor(
        col,
        f"{collection_name}_Anchor",
        location=anchor_location,
        rotation_z_deg=anchor_rotation_z_deg,
        scale=anchor_scale,
    )


def _setup_camera(total_frames: int) -> None:
    target = (0.0, 0.02, 1.32)
    keyframes = [
        (1, (1.65, -5.25, 2.24)),
        (max(2, total_frames // 2), (0.65, -5.42, 2.18)),
        (total_frames, (-0.95, -5.30, 2.26)),
    ]
    common.setup_orbit_camera(target, keyframes, lens_mm=36.0, dof_fstop=6.8)


def build_scene(taa_samples: int = 16) -> dict[str, Any]:
    """Assemble the standalone 07_organ_timpani_53edo showcase scene."""
    scene = common.reset_scene(fps=24, res_x=1920, res_y=1080, taa_samples=taa_samples)
    scene.view_settings.exposure = -0.28

    mats = common.create_studio_materials()
    common.build_concert_stage(mats, pedestal_radius=1.65, pedestal_height=PEDESTAL_Z, light_target_z=1.25)

    for lname, scale in (("KeyLight", 0.68), ("RimLight", 0.62), ("TopAccent", 0.60)):
        lobj = bpy.data.objects.get(lname)
        if lobj and lobj.data:
            lobj.data.energy *= scale
            if lname == "RimLight":
                loc = Vector((-1.8, 4.5, 3.6))
                lobj.location = loc
                lobj.rotation_euler = (Vector((0.0, 0.0, 1.25)) - loc).to_track_quat("-Z", "Y").to_euler()
    ped_bsdf = mats["PedestalWood"].node_tree.nodes.get("Principled BSDF")
    if ped_bsdf is not None:
        ped_bsdf.inputs["Roughness"].default_value = 0.55
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
    print(f"[organ_timpani_53edo] Saved blend: {BLEND_PATH}")

    if stills_only:
        frame_specs = [
            ("idle", 1),
            ("timpani_roll", common.sec_to_frame(3.6, 24)),
            ("organ_chorale", common.sec_to_frame(10.5, 24)),
        ]
        rendered = common.render_diagnostic_stills(frame_specs, STILLS_DIR, "diag_organ")
        for p in rendered:
            print(f"[organ_timpani_53edo] Diagnostic still: {p}")

    if render_vid:
        common.render_video(WEBM_PATH, WAV_PATH, int(timeline["total_frames"]), TMP_FRAMES_DIR, fps=24)


if __name__ == "__main__":
    main()
