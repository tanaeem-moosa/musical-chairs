"""The Alexandrian 53-String-Per-Octave Arch-Harp — Blender 4.2 EEVEE Next showcase."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bmesh
import bpy
import mathutils
from mathutils import Matrix, Vector

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blender_gallery.common import (
    build_concert_stage,
    color_for_53edo_step,
    create_studio_materials,
    load_score_timeline,
    render_diagnostic_stills,
    render_video,
    reset_scene,
    save_blend,
    sec_to_frame,
    setup_orbit_camera,
)

SCORE_PATH = REPO_ROOT / "scores" / "showcase_3d" / "01_harp_53edo.json"
WAV_PATH = REPO_ROOT / "output" / "showcase_3d" / "01_harp_53edo.wav"
BLEND_PATH = REPO_ROOT / "output" / "showcase_3d" / "01_harp_53edo.blend"
WEBM_PATH = REPO_ROOT / "output" / "showcase_3d" / "01_harp_53edo.webm"
STILLS_DIR = REPO_ROOT / "output" / "showcase_3d"
TMP_FRAMES_DIR = Path("/tmp/frames_harp_53edo")

PEDESTAL_Z = 0.09
STEP_MIN = -53
STEP_MAX = 84
NUM_STRINGS = STEP_MAX - STEP_MIN + 1  # 138 strings

# Neck cubic Bezier control points in (0, Y, Z)
NECK_P0 = Vector((0.0, -0.45, 1.90))
NECK_P1 = Vector((0.0, -0.18, 1.05))
NECK_P2 = Vector((0.0, 0.36, 1.88))
NECK_P3 = Vector((0.0, 0.62, 1.12))

# Soundboard centerline endpoints in (0, Y, Z) (~42 deg backward tilt from vertical)
SB_BASE = Vector((0.0, -0.15, 0.21))
SB_SHOULDER = Vector((0.0, 0.62, 1.065))


def _link_obj(col: bpy.types.Collection, obj: bpy.types.Object) -> bpy.types.Object:
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def _make_mesh_obj(
    col: bpy.types.Collection,
    name: str,
    bm: bmesh.types.BMesh,
    mat: bpy.types.Material,
    smooth: bool = True,
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
    return obj


def eval_neck_curve(u: float) -> Vector:
    """Evaluate cubic Bezier harmonic neck centerline at parameter u in [0, 1]."""
    t = max(0.0, min(1.0, u))
    mt = 1.0 - t
    return (
        (mt ** 3) * NECK_P0
        + 3.0 * (mt ** 2) * t * NECK_P1
        + 3.0 * mt * (t ** 2) * NECK_P2
        + (t ** 3) * NECK_P3
    )


def eval_neck_tangent(u: float) -> Vector:
    """Evaluate unit tangent of the harmonic neck curve."""
    t = max(0.0, min(1.0, u))
    mt = 1.0 - t
    deriv = (
        3.0 * (mt ** 2) * (NECK_P1 - NECK_P0)
        + 6.0 * mt * t * (NECK_P2 - NECK_P1)
        + 3.0 * (t ** 2) * (NECK_P3 - NECK_P2)
    )
    return deriv.normalized()


def string_endpoints(idx: int) -> tuple[Vector, Vector]:
    """Return (bottom_eyelet, top_neck_pin) world positions for string index 0..137."""
    frac = idx / float(NUM_STRINGS - 1)
    u_neck = 0.065 + frac * 0.875
    neck_center = eval_neck_curve(u_neck)
    # String exits from the lower rim of the harmonic neck
    half_h = 0.056 - 0.016 * frac
    top_pt = neck_center - Vector((0.0, 0.0, half_h * 0.65))

    t_sb = 0.05 + frac * 0.88
    bot_pt = SB_BASE.lerp(SB_SHOULDER, t_sb)
    return bot_pt, top_pt


def _loft_rings(
    bm: bmesh.types.BMesh,
    rings: list[list[bmesh.types.BMVert]],
    cap_start: bool = True,
    cap_end: bool = True,
) -> None:
    """Bridge consecutive vertex rings into a closed manifold shell."""
    n_seg = len(rings[0])
    for r_i in range(len(rings) - 1):
        r0 = rings[r_i]
        r1 = rings[r_i + 1]
        for j in range(n_seg):
            jn = (j + 1) % n_seg
            bm.faces.new((r0[j], r0[jn], r1[jn], r1[j]))
    if cap_start:
        bm.faces.new(list(reversed(rings[0])))
    if cap_end:
        bm.faces.new(rings[-1])


def build_pedestal_and_pedals(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> list[bpy.types.Object]:
    """Build stepped octagonal rosewood+gold harp pedestal on z=0.09 and 7 brass pedal stubs."""
    center_xy = Vector((0.0, -0.26, 0.0))

    # Stepped octagonal plinth tiers (seated flush at z=PEDESTAL_Z)
    tiers = [
        # (name, z0, z1, rx0, ry0, rx1, ry1, mat, bevel_w)
        ("HarpBaseTier1", PEDESTAL_Z, PEDESTAL_Z + 0.036, 0.255, 0.305, 0.242, 0.292, mats["DarkRosewood"], 0.004),
        ("HarpBaseGoldTrim1", PEDESTAL_Z + 0.036, PEDESTAL_Z + 0.050, 0.246, 0.296, 0.236, 0.286, mats["BrushedGold"], 0.002),
        ("HarpBaseTier2", PEDESTAL_Z + 0.050, PEDESTAL_Z + 0.108, 0.228, 0.278, 0.205, 0.254, mats["DarkRosewood"], 0.004),
        ("HarpBaseCrownMould", PEDESTAL_Z + 0.108, PEDESTAL_Z + 0.128, 0.212, 0.262, 0.188, 0.236, mats["BrushedGold"], 0.003),
        ("HarpBaseUpperBox", PEDESTAL_Z + 0.128, PEDESTAL_Z + 0.155, 0.184, 0.232, 0.172, 0.216, mats["WarmMahogany"], 0.003),
    ]

    for name, z0, z1, rx0, ry0, rx1, ry1, mat, bev_w in tiers:
        bm = bmesh.new()
        n_sides = 8
        rings: list[list[bmesh.types.BMVert]] = []
        for z_val, rx, ry in ((z0, rx0, ry0), (z1, rx1, ry1)):
            ring = []
            for k in range(n_sides):
                ang = (k + 0.5) * (2.0 * math.pi / n_sides)
                # Slightly flattened octagon proportions
                x = center_xy.x + rx * math.cos(ang)
                y = center_xy.y + ry * math.sin(ang)
                ring.append(bm.verts.new((x, y, z_val)))
            rings.append(ring)
        _loft_rings(bm, rings, cap_start=True, cap_end=True)
        obj = _make_mesh_obj(col, name, bm, mat, smooth=False)
        bev = obj.modifiers.new("Bevel", "BEVEL")
        bev.width = bev_w
        bev.segments = 2

    # Four sculpted golden claw/scroll feet tucked cleanly under the 4 diagonal corners on z=0.09
    bm_feet = bmesh.new()
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            fx = center_xy.x + sx * 0.175
            fy = center_xy.y + sy * 0.215
            yaw = math.atan2(sy * 0.215, sx * 0.175)
            mat_f = Matrix.Translation((fx, fy, PEDESTAL_Z + 0.017)) @ Matrix.Rotation(yaw, 4, "Z")
            bmesh.ops.create_uvsphere(
                bm_feet,
                u_segments=12,
                v_segments=8,
                radius=0.025,
                matrix=mat_f @ Matrix.Diagonal((1.45, 0.85, 0.72, 1.0)),
            )
    _make_mesh_obj(col, "HarpBaseFeet", bm_feet, mats["BrushedGold"], smooth=True)

    # 7 brass pedal stubs fanned around the rear/pedalist side (+Y) of the octagonal foot
    pedal_angles_deg = [-102.0, -68.0, -34.0, 0.0, 34.0, 68.0, 102.0]
    pedal_objs: list[bpy.types.Object] = []
    bm_collars = bmesh.new()

    for idx, deg in enumerate(pedal_angles_deg):
        rad = math.radians(deg)
        dir_vec = Vector((math.sin(rad), math.cos(rad), 0.0)).normalized()
        anchor = Vector((
            center_xy.x + dir_vec.x * 0.226,
            center_xy.y + dir_vec.y * 0.272,
            PEDESTAL_Z + 0.036,
        ))
        # Collar escutcheon on the plinth
        rot_q = dir_vec.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(
            bm_collars,
            cap_ends=True,
            cap_tris=False,
            segments=12,
            radius1=0.016,
            radius2=0.013,
            depth=0.016,
            matrix=Matrix.Translation(anchor) @ rot_q,
        )

        # Individual animated brass pedal lever + ribbed pad
        bm_p = bmesh.new()
        # Stem along +Y local (we'll orient object along dir_vec so pivot is at anchor)
        bmesh.ops.create_cube(
            bm_p,
            size=1.0,
            matrix=Matrix.Translation((0.0, 0.042, 0.0)) @ Matrix.Diagonal((0.016, 0.088, 0.010, 1.0)),
        )
        # Toe pad at end
        bmesh.ops.create_cube(
            bm_p,
            size=1.0,
            matrix=Matrix.Translation((0.0, 0.088, 0.002)) @ Matrix.Diagonal((0.028, 0.036, 0.012, 1.0)),
        )
        p_obj = _make_mesh_obj(col, f"HarpPedal_{idx}", bm_p, mats["PolishedBrass"], smooth=False)
        p_obj.location = anchor
        yaw = math.atan2(-dir_vec.x, dir_vec.y)
        p_obj.rotation_euler = (-0.16, 0.0, yaw)
        bev_p = p_obj.modifiers.new("Bevel", "BEVEL")
        bev_p.width = 0.0018
        bev_p.segments = 2
        pedal_objs.append(p_obj)

    _make_mesh_obj(col, "HarpPedalCollars", bm_collars, mats["BrushedGold"], smooth=True)
    return pedal_objs


def build_soundbox_and_soundboard(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> None:
    """Build tapered hollow-look rosewood soundbox (~42 deg tilt) and spruce soundboard."""
    axis_vec = (SB_SHOULDER - SB_BASE).normalized()
    length = (SB_SHOULDER - SB_BASE).length
    # Perpendicular normal pointing toward strings (-Y, +Z) and back (+Y, -Z)
    normal_front = Vector((0.0, -axis_vec.z, axis_vec.y)).normalized()
    right_x = Vector((1.0, 0.0, 0.0))

    n_slices = 18
    n_arc = 18  # semi-elliptical back profile

    # Outer DarkRosewood rounded stave soundbox shell (U-shaped hollow trough open to soundboard)
    bm_shell = bmesh.new()
    bm_trim = bmesh.new()
    outer_rings: list[list[bmesh.types.BMVert]] = []
    inner_rings: list[list[bmesh.types.BMVert]] = []
    left_trim_rings: list[list[bmesh.types.BMVert]] = []
    right_trim_rings: list[list[bmesh.types.BMVert]] = []

    wall = 0.014
    for i in range(n_slices + 1):
        t = i / float(n_slices)
        c = SB_BASE.lerp(SB_SHOULDER, t)
        # Taper from wide rounded bass bottom to slender treble shoulder
        half_w = 0.175 * (1.0 - 0.64 * (t ** 0.92))
        depth_back = 0.215 * (1.0 - 0.56 * (t ** 0.92))

        o_ring: list[bmesh.types.BMVert] = []
        in_ring: list[bmesh.types.BMVert] = []
        # Cross-section: semi-ellipse arcing from +X edge around back (-normal_front) to -X edge
        for j in range(n_arc + 1):
            ang = math.pi * (j / float(n_arc))  # 0 (+X) -> pi (-X)
            lx = half_w * math.cos(ang)
            lz_back = depth_back * math.sin(ang)
            pt_o = c + right_x * lx - normal_front * lz_back
            o_ring.append(bm_shell.verts.new(pt_o))

            lx_i = max(0.012, half_w - wall) * math.cos(ang)
            lz_i = max(0.015, depth_back - wall) * math.sin(ang)
            pt_i = c + right_x * lx_i - normal_front * lz_i
            in_ring.append(bm_shell.verts.new(pt_i))

        outer_rings.append(o_ring)
        inner_rings.append(in_ring)

        # Gold edge binding beads along both soundboard rims
        for sign_x, trim_list in ((-1.0, left_trim_rings), (1.0, right_trim_rings)):
            edge_c = c + right_x * (sign_x * half_w)
            t_ring = []
            for k in range(8):
                a = 2.0 * math.pi * (k / 8.0)
                pt_t = edge_c + right_x * (0.0055 * math.cos(a)) + normal_front * (0.0055 * math.sin(a))
                t_ring.append(bm_trim.verts.new(pt_t))
            trim_list.append(t_ring)

    # Connect outer & inner shells and rim edges
    for i in range(n_slices):
        o0, o1 = outer_rings[i], outer_rings[i + 1]
        i0, i1 = inner_rings[i], inner_rings[i + 1]
        for j in range(n_arc):
            bm_shell.faces.new((o0[j], o1[j], o1[j + 1], o0[j + 1]))
            bm_shell.faces.new((i0[j], i0[j + 1], i1[j + 1], i1[j]))
        # Front rims connecting outer and inner walls
        bm_shell.faces.new((o0[0], i0[0], i1[0], o1[0]))
        bm_shell.faces.new((o0[-1], o0[-1], i0[-1])) if False else bm_shell.faces.new((i0[-1], o0[-1], o1[-1], i1[-1]))

    # Cap bottom & top ends of soundbox cavity
    for j in range(n_arc):
        bm_shell.faces.new((outer_rings[0][j], outer_rings[0][j + 1], inner_rings[0][j + 1], inner_rings[0][j]))
        bm_shell.faces.new((outer_rings[-1][j], inner_rings[-1][j], inner_rings[-1][j + 1], outer_rings[-1][j + 1]))

    _make_mesh_obj(col, "HarpSoundboxShell", bm_shell, mats["DarkRosewood"], smooth=True)

    _loft_rings(bm_trim, left_trim_rings, cap_start=True, cap_end=True)
    _loft_rings(bm_trim, right_trim_rings, cap_start=True, cap_end=True)
    _make_mesh_obj(col, "HarpSoundboxGoldBinding", bm_trim, mats["BrushedGold"], smooth=True)

    # Soundhole gold rings recessed flush along the back spine of the soundbox
    bm_holes = bmesh.new()
    bm_hole_dark = bmesh.new()
    for t_h, rad_h in ((0.20, 0.042), (0.39, 0.036), (0.58, 0.030), (0.76, 0.024)):
        c = SB_BASE.lerp(SB_SHOULDER, t_h)
        depth_back = 0.215 * (1.0 - 0.56 * (t_h ** 0.92))
        hole_pos = c - normal_front * (depth_back - 0.002)
        rot_q = (-normal_front).to_track_quat("Z", "Y").to_matrix().to_4x4()
        # Flush gold bezel ring
        n_seg = 24
        ring_verts_o = []
        ring_verts_i = []
        for k in range(n_seg):
            a = 2.0 * math.pi * (k / n_seg)
            p_o = Matrix.Translation(hole_pos) @ rot_q @ Vector((rad_h * math.cos(a), rad_h * math.sin(a), 0.001))
            p_i = Matrix.Translation(hole_pos) @ rot_q @ Vector(((rad_h - 0.006) * math.cos(a), (rad_h - 0.006) * math.sin(a), -0.004))
            ring_verts_o.append(bm_holes.verts.new(p_o))
            ring_verts_i.append(bm_holes.verts.new(p_i))
        for k in range(n_seg):
            kn = (k + 1) % n_seg
            bm_holes.faces.new((ring_verts_o[k], ring_verts_o[kn], ring_verts_i[kn], ring_verts_i[k]))
        bmesh.ops.create_cone(
            bm_hole_dark,
            cap_ends=True,
            cap_tris=False,
            segments=20,
            radius1=rad_h - 0.005,
            radius2=rad_h - 0.005,
            depth=0.004,
            matrix=Matrix.Translation(hole_pos) @ rot_q @ Matrix.Translation((0.0, 0.0, -0.003)),
        )
    _make_mesh_obj(col, "HarpSoundholeRings", bm_holes, mats["BrushedGold"], smooth=True)
    _make_mesh_obj(col, "HarpSoundholeCavities", bm_hole_dark, mats["GlossEbony"], smooth=True)

    # AntiqueSpruce beveled soundboard plate sitting across the front face of the soundbox
    bm_sb = bmesh.new()
    sb_rings: list[list[bmesh.types.BMVert]] = []
    for i in range(n_slices + 1):
        t = i / float(n_slices)
        c = SB_BASE.lerp(SB_SHOULDER, t)
        half_w = 0.168 * (1.0 - 0.64 * (t ** 0.92))
        pts = [
            c + right_x * half_w - normal_front * 0.004,
            c + right_x * (half_w * 0.94) + normal_front * 0.006,
            c + right_x * 0.024 + normal_front * 0.008,
            c - right_x * 0.024 + normal_front * 0.008,
            c - right_x * (half_w * 0.94) + normal_front * 0.006,
            c - right_x * half_w - normal_front * 0.004,
        ]
        sb_rings.append([bm_sb.verts.new(p) for p in pts])
    _loft_rings(bm_sb, sb_rings, cap_start=True, cap_end=True)
    _make_mesh_obj(col, "HarpSpruceSoundboard", bm_sb, mats["AntiqueSpruce"], smooth=False)

    # Central tapered WarmMahogany string-rib strip + 138 PolishedBrass eyelets
    bm_rib = bmesh.new()
    rib_rings: list[list[bmesh.types.BMVert]] = []
    for i in range(n_slices + 1):
        t = i / float(n_slices)
        c = SB_BASE.lerp(SB_SHOULDER, t)
        rw = 0.028 * (1.0 - 0.35 * t)
        pts = [
            c + right_x * rw + normal_front * 0.006,
            c + right_x * (rw * 0.72) + normal_front * 0.015,
            c - right_x * (rw * 0.72) + normal_front * 0.015,
            c - right_x * rw + normal_front * 0.006,
        ]
        rib_rings.append([bm_rib.verts.new(p) for p in pts])
    _loft_rings(bm_rib, rib_rings, cap_start=True, cap_end=True)
    _make_mesh_obj(col, "HarpCenterStringRib", bm_rib, mats["DarkRosewood"], smooth=False)

    # 138 brass eyelets along the center string rib
    bm_eyelets = bmesh.new()
    rot_sb = normal_front.to_track_quat("Z", "Y").to_matrix().to_4x4()
    for idx in range(NUM_STRINGS):
        bot_pt, _ = string_endpoints(idx)
        mat_e = Matrix.Translation(bot_pt + normal_front * 0.013) @ rot_sb
        bmesh.ops.create_cone(
            bm_eyelets,
            cap_ends=True,
            cap_tris=False,
            segments=8,
            radius1=0.0036,
            radius2=0.0026,
            depth=0.006,
            matrix=mat_e,
        )
    _make_mesh_obj(col, "HarpSoundboardEyelets", bm_eyelets, mats["PolishedBrass"], smooth=True)


def build_forepillar_and_crown(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> None:
    """Build fluted mahogany/gold forepillar (~1.95m tall) and carved golden crown volute."""
    # Forepillar shaft from base housing (z=0.23) up to capital collar (z=1.84)
    z_bot = PEDESTAL_Z + 0.145
    z_top = 1.84
    n_z = 28
    n_flutes = 14
    pts_per_flute = 3  # ridge, valley, ridge -> crisp concave flutes
    n_ring = n_flutes * pts_per_flute

    bm_col = bmesh.new()
    rings: list[list[bmesh.types.BMVert]] = []
    for i in range(n_z + 1):
        t = i / float(n_z)
        z = z_bot + t * (z_top - z_bot)
        # Subtle entasis curve: gentle forward bow in Y and classical column taper
        y_center = -0.45 - 0.022 * math.sin(math.pi * t)
        base_r = 0.044 + 0.008 * math.sin(math.pi * (t ** 0.75)) - 0.007 * t
        # Fade flute depth smoothly near base and capital collars
        flute_env = math.sin(math.pi * max(0.0, min(1.0, (t - 0.05) / 0.90))) ** 0.6 if 0.05 < t < 0.95 else 0.0
        flute_depth = 0.0048 * flute_env

        ring: list[bmesh.types.BMVert] = []
        for k in range(n_ring):
            ang = 2.0 * math.pi * (k / float(n_ring))
            sub = k % pts_per_flute
            r = base_r - (flute_depth if sub == 1 else 0.0)
            ring.append(bm_col.verts.new((r * math.cos(ang), y_center + r * math.sin(ang), z)))
        rings.append(ring)

    _loft_rings(bm_col, rings, cap_start=True, cap_end=True)
    _make_mesh_obj(col, "HarpForepillarShaft", bm_col, mats["WarmMahogany"], smooth=True)

    # Gold base & capital turned collars + decorative mid-band
    bm_collars = bmesh.new()
    collar_specs = [
        # (z, y, r_max, height)
        (z_bot + 0.015, -0.45, 0.058, 0.045),
        (z_bot + 0.058, -0.452, 0.050, 0.026),
        (z_bot + 0.42, -0.465, 0.052, 0.018),
        (z_top - 0.02, -0.452, 0.050, 0.028),
        (z_top + 0.025, -0.45, 0.062, 0.052),
        (z_top + 0.065, -0.45, 0.072, 0.032),
    ]
    for cz, cy, cr, ch in collar_specs:
        # Stacked torus + cylinder moulding
        bmesh.ops.create_cone(
            bm_collars,
            cap_ends=True,
            cap_tris=False,
            segments=32,
            radius1=cr,
            radius2=cr * 0.94,
            depth=ch,
            matrix=Matrix.Translation((0.0, cy, cz)),
        )
        # Beaded torus ring
        n_maj, n_min = 32, 10
        r_min = ch * 0.28
        t_rings: list[list[bmesh.types.BMVert]] = []
        for a_i in range(n_maj):
            ang_m = 2.0 * math.pi * (a_i / n_maj)
            dir_r = Vector((math.cos(ang_m), math.sin(ang_m), 0.0))
            tr: list[bmesh.types.BMVert] = []
            for b_i in range(n_min):
                ang_n = 2.0 * math.pi * (b_i / n_min)
                pt = Vector((0.0, cy, cz)) + dir_r * (cr + r_min * math.cos(ang_n)) + Vector((0.0, 0.0, r_min * math.sin(ang_n)))
                tr.append(bm_collars.verts.new(pt))
            t_rings.append(tr)
        for a_i in range(n_maj):
            an = (a_i + 1) % n_maj
            for b_i in range(n_min):
                bn = (b_i + 1) % n_min
                bm_collars.faces.new((t_rings[a_i][b_i], t_rings[an][b_i], t_rings[an][bn], t_rings[a_i][bn]))

    _make_mesh_obj(col, "HarpForepillarGoldCollars", bm_collars, mats["BrushedGold"], smooth=True)

    # Carved golden crown volute at top of forepillar (reaching z ≈ 2.09m -> 2.0m above pedestal)
    bm_crown = bmesh.new()
    # 1) Sweeping crest arch from capital (y=-0.45, z=1.90) rising to z=2.09 and curling forward (-Y)
    n_scroll = 34
    scroll_rings: list[list[bmesh.types.BMVert]] = []
    scroll_pts: list[tuple[Vector, float, float]] = []
    for i in range(n_scroll):
        s = i / float(n_scroll - 1)
        if s < 0.45:
            # Rising neck of crown up and slightly back before cresting forward
            u = s / 0.45
            y = -0.45 - 0.03 * math.sin(u * math.pi) - 0.08 * (u ** 2)
            z = 1.88 + 0.21 * math.sin(u * math.pi * 0.65)
            rx = 0.044 * (1.0 - 0.25 * u)
            rz = 0.052 * (1.0 - 0.20 * u)
        else:
            # Tight inward spiral volute facing forward (-Y)
            u = (s - 0.45) / 0.55
            theta = u * 1.65 * math.pi
            rad_s = 0.078 * (1.0 - 0.72 * u)
            center_y = -0.53
            center_z = 2.01
            y = center_y - rad_s * math.sin(theta)
            z = center_z + rad_s * math.cos(theta)
            rx = 0.033 * (1.0 - 0.52 * u)
            rz = 0.038 * (1.0 - 0.55 * u)
        scroll_pts.append((Vector((0.0, y, z)), rx, rz))

    n_sec = 14
    for idx, (pt, rx, rz) in enumerate(scroll_pts):
        if idx == 0:
            tan = (scroll_pts[1][0] - pt).normalized()
        elif idx == len(scroll_pts) - 1:
            tan = (pt - scroll_pts[-2][0]).normalized()
        else:
            tan = (scroll_pts[idx + 1][0] - scroll_pts[idx - 1][0]).normalized()
        side_x = Vector((1.0, 0.0, 0.0))
        up_n = tan.cross(side_x).normalized()
        ring = []
        for k in range(n_sec):
            a = 2.0 * math.pi * (k / n_sec)
            # Fluted/sculpted oval cross section
            fl = 1.0 + 0.08 * math.cos(4.0 * a)
            p = pt + side_x * (rx * fl * math.cos(a)) + up_n * (rz * fl * math.sin(a))
            ring.append(bm_crown.verts.new(p))
        scroll_rings.append(ring)
    _loft_rings(bm_crown, scroll_rings, cap_start=True, cap_end=True)

    # Volute eye bosses on +/-X of the scroll center + carved finial crest
    for sx in (-1.0, 1.0):
        bmesh.ops.create_uvsphere(
            bm_crown,
            u_segments=14,
            v_segments=10,
            radius=0.028,
            matrix=Matrix.Translation((sx * 0.022, -0.53, 2.01)) @ Matrix.Diagonal((0.55, 1.0, 1.0, 1.0)),
        )
    # Rear crown bridge sweeping gracefully from crown back into NECK_P0
    bmesh.ops.create_uvsphere(
        bm_crown,
        u_segments=16,
        v_segments=12,
        radius=0.056,
        matrix=Matrix.Translation((0.0, -0.43, 1.92)) @ Matrix.Diagonal((0.88, 1.35, 1.05, 1.0)),
    )
    _make_mesh_obj(col, "HarpCrownVolute", bm_crown, mats["BrushedGold"], smooth=True)


def build_harmonic_neck_and_pins(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> None:
    """Build sweeping S-curve mahogany harmonic neck, gold action plate, and 138 tuning pins."""
    n_segs = 44
    n_sec = 16

    bm_neck = bmesh.new()
    bm_plate = bmesh.new()
    neck_rings: list[list[bmesh.types.BMVert]] = []
    plate_rings: list[list[bmesh.types.BMVert]] = []

    side_x = Vector((1.0, 0.0, 0.0))
    for i in range(n_segs + 1):
        u = i / float(n_segs)
        c = eval_neck_curve(u)
        tan = eval_neck_tangent(u)
        up_n = tan.cross(side_x).normalized()

        # Sculpted tapered beam cross-section (deeper in bass, slender in treble)
        half_w = 0.028 - 0.008 * u
        half_h = 0.058 - 0.018 * u

        n_ring: list[bmesh.types.BMVert] = []
        for k in range(n_sec):
            a = 2.0 * math.pi * (k / n_sec)
            # Rounded-rectangular sculpted luthiery profile
            cx = math.cos(a)
            cz = math.sin(a)
            sx = math.copysign(abs(cx) ** 0.72, cx) * half_w
            sz = math.copysign(abs(cz) ** 0.78, cz) * half_h
            n_ring.append(bm_neck.verts.new(c + side_x * sx + up_n * sz))
        neck_rings.append(n_ring)

        # BrushedGold brass action-plate cheek along the +X face of the neck
        px = half_w + 0.004
        ph = half_h * 0.78
        p_pts = [
            c + side_x * (half_w * 0.75) + up_n * ph,
            c + side_x * px + up_n * (ph * 0.88),
            c + side_x * px - up_n * (ph * 0.88),
            c + side_x * (half_w * 0.75) - up_n * ph,
        ]
        plate_rings.append([bm_plate.verts.new(p) for p in p_pts])

    _loft_rings(bm_neck, neck_rings, cap_start=True, cap_end=True)
    _make_mesh_obj(col, "HarpHarmonicNeck", bm_neck, mats["WarmMahogany"], smooth=True)

    _loft_rings(bm_plate, plate_rings, cap_start=True, cap_end=True)
    _make_mesh_obj(col, "HarpNeckBrassActionPlate", bm_plate, mats["BrushedGold"], smooth=False)

    # Carved sculpted knee arch joining the neck seamlessly into the soundbox shoulder
    bm_knee = bmesh.new()
    knee_rings: list[list[bmesh.types.BMVert]] = []
    knee_pts = [
        (SB_SHOULDER - Vector((0.0, 0.055, 0.060)), 0.060, 0.058),
        (SB_SHOULDER - Vector((0.0, 0.015, 0.015)), 0.052, 0.056),
        (Vector((0.0, 0.622, 1.075)), 0.042, 0.054),
        (NECK_P3 + Vector((0.0, -0.010, 0.005)), 0.024, 0.044),
    ]
    for pt, rx, ry in knee_pts:
        r_v = []
        for k in range(14):
            a = 2.0 * math.pi * (k / 14.0)
            r_v.append(bm_knee.verts.new((pt.x + rx * math.cos(a), pt.y + ry * math.sin(a), pt.z + 0.012 * math.sin(a))))
        knee_rings.append(r_v)
    _loft_rings(bm_knee, knee_rings, cap_start=True, cap_end=True)
    _make_mesh_obj(col, "HarpKneeArch", bm_knee, mats["DarkRosewood"], smooth=True)

    # Gold shoulder collar accent wrapping the knee-to-soundbox joint seamlessly
    bm_knee_gold = bmesh.new()
    sb_dir = (SB_SHOULDER - SB_BASE).normalized()
    rot_sb = sb_dir.to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.create_cone(
        bm_knee_gold,
        cap_ends=True,
        cap_tris=False,
        segments=24,
        radius1=0.064,
        radius2=0.052,
        depth=0.036,
        matrix=Matrix.Translation(SB_SHOULDER - sb_dir * 0.004) @ rot_sb,
    )
    _make_mesh_obj(col, "HarpKneeGoldCollar", bm_knee_gold, mats["BrushedGold"], smooth=True)

    # 138 brass tuning pins + 138 bridge pins protruding cleanly on the +X face
    bm_pins = bmesh.new()
    rot_x = Vector((1.0, 0.0, 0.0)).to_track_quat("Z", "Y").to_matrix().to_4x4()
    for idx in range(NUM_STRINGS):
        frac = idx / float(NUM_STRINGS - 1)
        u_neck = 0.065 + frac * 0.875
        c = eval_neck_curve(u_neck)
        _, top_pt = string_endpoints(idx)

        # Tuning pin higher on the +X side of the neck
        pin_z_off = 0.016 - 0.004 * frac
        pin_pos = Vector((0.022, c.y, c.z + pin_z_off))
        bmesh.ops.create_cone(
            bm_pins,
            cap_ends=True,
            cap_tris=False,
            segments=8,
            radius1=0.0030,
            radius2=0.0024,
            depth=0.036,
            matrix=Matrix.Translation(pin_pos) @ rot_x,
        )
        # Flattened square-ish tuning pin head at tip (+X)
        bmesh.ops.create_cube(
            bm_pins,
            size=1.0,
            matrix=Matrix.Translation(pin_pos + Vector((0.017, 0.0, 0.0)))
            @ Matrix.Diagonal((0.006, 0.0045, 0.0045, 1.0)),
        )

        # Small bridge pin at string exit point
        bridge_pos = Vector((0.014, top_pt.y, top_pt.z + 0.008))
        bmesh.ops.create_cone(
            bm_pins,
            cap_ends=True,
            cap_tris=False,
            segments=6,
            radius1=0.0022,
            radius2=0.0018,
            depth=0.022,
            matrix=Matrix.Translation(bridge_pos) @ rot_x,
        )

    _make_mesh_obj(col, "HarpTuningAndBridgePins", bm_pins, mats["PolishedBrass"], smooth=True)


def build_strings(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[int, dict]:
    """Create 138 individual 3D strings (steps -53..+84) with PluckX shape keys."""
    luminous_mat = mats["LuminousElement"]
    strings_by_step: dict[int, dict] = {}

    n_rings = 9  # 8 segments along string length for smooth lateral standing-wave bow
    n_sides = 8

    for idx in range(NUM_STRINGS):
        step = STEP_MIN + idx
        frac = idx / float(NUM_STRINGS - 1)
        bot_pt, top_pt = string_endpoints(idx)
        vec = top_pt - bot_pt
        length = vec.length
        mid_pt = (bot_pt + top_pt) * 0.5
        radius = 0.00078 - 0.00024 * frac  # authentic 1.56mm bass -> 1.08mm treble harp strings

        bm = bmesh.new()
        rings: list[list[bmesh.types.BMVert]] = []
        ring_ts: list[float] = []
        for r_i in range(n_rings):
            t = r_i / float(n_rings - 1)
            z_loc = (t - 0.5) * length
            ring = []
            for k in range(n_sides):
                ang = 2.0 * math.pi * (k / float(n_sides))
                ring.append(bm.verts.new((radius * math.cos(ang), radius * math.sin(ang), z_loc)))
            rings.append(ring)
            ring_ts.append(t)
        _loft_rings(bm, rings, cap_start=True, cap_end=True)

        mesh = bpy.data.meshes.new(f"HarpString_{step:+03d}")
        bm.normal_update()
        bm.to_mesh(mesh)
        bm.free()
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))

        obj = bpy.data.objects.new(f"HarpString_{step:+03d}", mesh)
        obj.data.materials.append(luminous_mat)
        obj.location = mid_pt
        # Align local +Z with string direction (vec lies in Y-Z so local +X stays global +X)
        obj.rotation_euler = vec.normalized().to_track_quat("Z", "Y").to_euler()
        col.objects.link(obj)

        # Harmonic lattice RGB tint + idle rest glow alpha=0.03
        rgb = color_for_53edo_step(step)
        obj.color = (rgb[0], rgb[1], rgb[2], 0.03)

        # Shape key for lateral X standing-wave pluck vibration (pinned cleanly at both ends)
        obj.shape_key_add(name="Basis", from_mix=False)
        kb = obj.shape_key_add(name="PluckX", from_mix=False)
        kb.slider_min = -1.5
        kb.slider_max = 1.5
        kb.value = 0.0
        amp_x = 0.011 + 0.007 * (1.0 - frac)  # bass strings bow wider than short treble strings
        for v_i, vert in enumerate(mesh.vertices):
            ring_i = v_i // n_sides
            t = ring_ts[ring_i]
            kb.data[v_i].co.x = vert.co.x + amp_x * math.sin(math.pi * t)

        strings_by_step[step] = {
            "obj": obj,
            "kb": kb,
            "bot_pt": bot_pt,
            "top_pt": top_pt,
            "rgb": rgb,
        }

    return strings_by_step


def build_pluck_beads(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
    count: int = 8,
) -> list[bpy.types.Object]:
    """Create reusable golden luminous pluck bead spheres sharing LuminousElement."""
    beads: list[bpy.types.Object] = []
    luminous_mat = mats["LuminousElement"]

    for i in range(count):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=10, radius=0.014)
        obj = _make_mesh_obj(col, f"HarpPluckBead_{i}", bm, luminous_mat, smooth=True)
        obj.color = (1.0, 0.84, 0.30, 0.0)
        obj.scale = (0.0, 0.0, 0.0)
        obj.location = (0.0, 0.0, -1.0)
        beads.append(obj)

    return beads


def _set_constant_segment(obj_or_id, data_path: str, index: int, frames: set[int]) -> None:
    """Force CONSTANT interpolation on specified keyframe X-coordinates so glow never ramps early."""
    ad = obj_or_id.animation_data
    if not ad or not ad.action:
        return
    for fc in ad.action.fcurves:
        if fc.data_path == data_path and (index < 0 or fc.array_index == index):
            for kp in fc.keyframe_points:
                if int(round(kp.co.x)) in frames:
                    kp.interpolation = "CONSTANT"


def animate_harp(
    timeline: dict,
    strings_by_step: dict[int, dict],
    beads: list[bpy.types.Object],
    pedal_objs: list[bpy.types.Object],
) -> None:
    """Keyframe string glow spikes, damped X vibrations, pluck beads, and pedals."""
    fps = timeline["fps"]
    total_frames = timeline["total_frames"]
    notes = timeline["notes"]

    # Group notes by step
    by_step: dict[int, list[dict]] = {}
    for n in notes:
        by_step.setdefault(n["step"], []).append(n)

    # 1) Animate every string (rest idle keyframes for unplayed strings too, clean baseline)
    for step, info in strings_by_step.items():
        obj = info["obj"]
        kb = info["kb"]
        evts = by_step.get(step, [])

        obj.color[3] = 0.03
        obj.keyframe_insert(data_path="color", index=3, frame=1)
        obj.scale = (1.0, 1.0, 1.0)
        obj.keyframe_insert(data_path="scale", index=0, frame=1)
        obj.keyframe_insert(data_path="scale", index=1, frame=1)
        kb.value = 0.0
        kb.keyframe_insert(data_path="value", frame=1)

        if not evts:
            continue

        const_frames: set[int] = {1}
        for i, ev in enumerate(evts):
            f0 = sec_to_frame(ev["start_s"], fps)
            decay_s = min(ev["dur_s"], 1.8)
            f_end = min(total_frames, sec_to_frame(ev["start_s"] + decay_s, fps))
            next_f0 = sec_to_frame(evts[i + 1]["start_s"], fps) if i + 1 < len(evts) else total_frames + 10

            # Pre-onset rest / hold keyframe 1 frame before pluck so glow & pluck snap cleanly
            if f0 > 2:
                prev_f = f0 - 1
                # Determine pre-onset alpha: 0.03 if previous note already finished, else smoothly clipped
                pre_alpha = 0.03
                if i > 0:
                    prev_ev = evts[i - 1]
                    prev_decay = min(prev_ev["dur_s"], 1.8)
                    elapsed_prev = (prev_f - 1) / float(fps) - prev_ev["start_s"]
                    if 0.0 < elapsed_prev < prev_decay:
                        u_prev = elapsed_prev / prev_decay
                        pre_alpha = 0.03 + 0.97 * max(0.0, 1.0 - (u_prev ** 2.5))
                obj.color[3] = pre_alpha
                obj.keyframe_insert(data_path="color", index=3, frame=prev_f)
                const_frames.add(prev_f)

                pre_sw = 1.0 + 0.85 * max(0.0, (pre_alpha - 0.03) / 0.97)
                obj.scale[0] = pre_sw
                obj.scale[1] = pre_sw
                obj.keyframe_insert(data_path="scale", index=0, frame=prev_f)
                obj.keyframe_insert(data_path="scale", index=1, frame=prev_f)

                kb.value = 0.0
                kb.keyframe_insert(data_path="value", frame=prev_f)

            # Onset spike
            peak_alpha = min(1.0, 0.85 + 0.20 * ev["vel"])
            obj.color[3] = peak_alpha
            obj.keyframe_insert(data_path="color", index=3, frame=f0)
            peak_sw = 1.0 + 0.85 * ((peak_alpha - 0.03) / 0.97)
            obj.scale[0] = peak_sw
            obj.scale[1] = peak_sw
            obj.keyframe_insert(data_path="scale", index=0, frame=f0)
            obj.keyframe_insert(data_path="scale", index=1, frame=f0)

            # Sample lush sustain-then-decay glow curve up to min(f_end, next_f0 - 2)
            clip_end = min(f_end, next_f0 - 2)
            for f in range(f0 + 2, clip_end + 1, 2):
                u = min(1.0, ((f - 1) / float(fps) - ev["start_s"]) / max(0.05, decay_s))
                val = 0.03 + (peak_alpha - 0.03) * max(0.0, 1.0 - (u ** 2.5))
                obj.color[3] = val
                obj.keyframe_insert(data_path="color", index=3, frame=f)
                sw = 1.0 + 0.85 * ((val - 0.03) / 0.97)
                obj.scale[0] = sw
                obj.scale[1] = sw
                obj.keyframe_insert(data_path="scale", index=0, frame=f)
                obj.keyframe_insert(data_path="scale", index=1, frame=f)

            if clip_end >= f_end:
                obj.color[3] = 0.03
                obj.keyframe_insert(data_path="color", index=3, frame=f_end)
                obj.scale[0] = 1.0
                obj.scale[1] = 1.0
                obj.keyframe_insert(data_path="scale", index=0, frame=f_end)
                obj.keyframe_insert(data_path="scale", index=1, frame=f_end)
                const_frames.add(f_end)

            # Exponentially damped lateral X oscillation (lasts up to 1.5s on sustained chords)
            vib_frames = min(36, max(8, int(round(min(ev["dur_s"], 1.5) * fps))))
            vib_end = min(f0 + vib_frames, next_f0 - 2, total_frames)
            vel_amp = 0.78 + 0.45 * ev["vel"]
            for k in range(vib_end - f0 + 1):
                f_v = f0 + k
                damp = math.exp(-0.095 * k)
                sign = 1.0 if (k % 2 == 0) else -1.0
                kb.value = vel_amp * damp * sign
                kb.keyframe_insert(data_path="value", frame=f_v)
            if vib_end + 1 < next_f0:
                kb.value = 0.0
                kb.keyframe_insert(data_path="value", frame=min(total_frames, vib_end + 1))

        _set_constant_segment(obj, "color", 3, const_frames)
        _set_constant_segment(obj, "scale", 0, const_frames)
        _set_constant_segment(obj, "scale", 1, const_frames)

    # 2) Animate 8 reusable golden pluck beads gliding rapidly up played strings
    bead_free_frame = [1] * len(beads)
    bead_const_frames: list[set[int]] = [{1} for _ in beads]

    for b in beads:
        b.location = (0.0, 0.0, -1.0)
        b.scale = (0.0, 0.0, 0.0)
        b.color = (1.0, 0.84, 0.30, 0.0)
        b.keyframe_insert(data_path="location", frame=1)
        b.keyframe_insert(data_path="scale", frame=1)
        b.keyframe_insert(data_path="color", index=3, frame=1)

    for ev in notes:
        step = ev["step"]
        if step not in strings_by_step:
            continue
        f0 = sec_to_frame(ev["start_s"], fps)
        # Rapid 0.34s (~8 frames) glide up the played string
        glide_dur_s = min(0.36, max(0.22, ev["dur_s"] * 0.48))
        f_end = min(total_frames, f0 + max(5, int(round(glide_dur_s * fps))))

        # Pick earliest available bead
        best_i = min(range(len(beads)), key=lambda bi: bead_free_frame[bi])
        bead = beads[best_i]
        info = strings_by_step[step]
        bot_pt: Vector = info["bot_pt"]
        top_pt: Vector = info["top_pt"]

        # Start slightly above the soundboard eyelet and race up to 92% of the string
        p_start = bot_pt.lerp(top_pt, 0.08)
        p_end = bot_pt.lerp(top_pt, 0.92)

        pre_f = max(1, f0 - 1)
        if pre_f >= bead_free_frame[best_i]:
            bead.location = p_start
            bead.scale = (0.0, 0.0, 0.0)
            bead.color[3] = 0.0
            bead.keyframe_insert(data_path="location", frame=pre_f)
            bead.keyframe_insert(data_path="scale", frame=pre_f)
            bead.keyframe_insert(data_path="color", index=3, frame=pre_f)
            bead_const_frames[best_i].add(pre_f)

        n_glide = max(1, f_end - f0)
        for k in range(n_glide + 1):
            u = k / float(n_glide)
            # Smooth ease-out rapid upward glide
            eased = 1.0 - (1.0 - u) ** 1.7
            pos = p_start.lerp(p_end, eased)
            # Envelope: pop in immediately at onset, taper gently at neck arrival
            sc = 1.15 * (1.0 - 0.55 * (u ** 2.2))
            al = 1.0 - 0.65 * (u ** 2.4)
            f_k = f0 + k
            bead.location = pos
            bead.scale = (sc, sc, sc)
            bead.color[3] = al
            bead.keyframe_insert(data_path="location", frame=f_k)
            bead.keyframe_insert(data_path="scale", frame=f_k)
            bead.keyframe_insert(data_path="color", index=3, frame=f_k)

        hide_f = min(total_frames, f_end + 1)
        bead.scale = (0.0, 0.0, 0.0)
        bead.color[3] = 0.0
        bead.keyframe_insert(data_path="scale", frame=hide_f)
        bead.keyframe_insert(data_path="color", index=3, frame=hide_f)
        bead_const_frames[best_i].add(hide_f)
        bead_free_frame[best_i] = hide_f + 1

    for bi, bead in enumerate(beads):
        _set_constant_segment(bead, "color", 3, bead_const_frames[bi])
        _set_constant_segment(bead, "scale", -1, bead_const_frames[bi])

    # 3) Subtle realistic pedal depression on pedal events in the score
    active_pedal_indices = [1, 3, 5]
    for p_idx in active_pedal_indices:
        if p_idx < len(pedal_objs):
            p_obj = pedal_objs[p_idx]
            base_rot_x = -0.16
            p_obj.rotation_euler[0] = base_rot_x
            p_obj.keyframe_insert(data_path="rotation_euler", index=0, frame=1)
            for pev in timeline.get("pedals", []):
                fs = sec_to_frame(pev["start_s"], fps)
                fe = min(total_frames, sec_to_frame(pev["end_s"], fps))
                if fs > 2:
                    p_obj.rotation_euler[0] = base_rot_x
                    p_obj.keyframe_insert(data_path="rotation_euler", index=0, frame=fs - 2)
                p_obj.rotation_euler[0] = base_rot_x - 0.14
                p_obj.keyframe_insert(data_path="rotation_euler", index=0, frame=fs + 2)
                p_obj.keyframe_insert(data_path="rotation_euler", index=0, frame=max(fs + 2, fe - 2))
                if fe < total_frames:
                    p_obj.rotation_euler[0] = base_rot_x
                    p_obj.keyframe_insert(data_path="rotation_euler", index=0, frame=min(total_frames, fe + 2))


def setup_harp_camera(total_frames: int) -> None:
    """Orbit 30 deg around the harp from 3/4 front-right to clean side profile with push-in."""
    target = (0.0, 0.0, 1.05)

    def polar(az_deg: float, dist: float, z: float) -> tuple[float, float, float]:
        rad = math.radians(az_deg)
        return (dist * math.sin(rad), -dist * math.cos(rad), z)

    keyframes = [
        (1, polar(62.0, 5.55, 1.44)),
        (max(2, total_frames // 2), polar(77.0, 5.25, 1.35)),
        (total_frames, polar(92.0, 4.95, 1.26)),
    ]
    setup_orbit_camera(target, keyframes, lens_mm=42.0, dof_fstop=5.6)


def build_scene() -> dict:
    """Build the complete Alexandrian 53-EDO Arch-Harp scene and return score timeline."""
    scene = reset_scene(fps=24, res_x=1920, res_y=1080, taa_samples=16)
    # Tame AgX exposure slightly so glossy wood & gold retain rich contrast without blowing out
    scene.view_settings.exposure = -0.22

    mats = create_studio_materials()
    # Keep LuminousElement saturated under AgX instead of clipping to white at 16.0
    if mats["LuminousElement"].use_nodes:
        for node in mats["LuminousElement"].node_tree.nodes:
            if node.type == "MATH" and node.operation == "MULTIPLY":
                node.inputs[1].default_value = 9.5

    # Soften pedestal specular hotspot locally so the dark plinth frames the harp cleanly
    ped_bsdf = mats["PedestalWood"].node_tree.nodes.get("Principled BSDF")
    if ped_bsdf is not None:
        ped_bsdf.inputs["Roughness"].default_value = 0.42
        ped_bsdf.inputs["Coat Weight"].default_value = 0.10

    build_concert_stage(mats, pedestal_radius=1.65, pedestal_height=PEDESTAL_Z, light_target_z=1.05)

    # Dial studio light energies down slightly locally so spruce/gold/pedestal don't trigger false glare
    for lname, scale in (("KeyLight", 0.65), ("RimLight", 0.68), ("TopAccent", 0.65)):
        lobj = bpy.data.objects.get(lname)
        if lobj and lobj.data:
            lobj.data.energy *= scale

    timeline = load_score_timeline(SCORE_PATH, WAV_PATH, fps=24)

    harp_col = bpy.data.collections.new("AlexandrianArchHarp")
    bpy.context.scene.collection.children.link(harp_col)

    pedal_objs = build_pedestal_and_pedals(harp_col, mats)
    build_soundbox_and_soundboard(harp_col, mats)
    build_forepillar_and_crown(harp_col, mats)
    build_harmonic_neck_and_pins(harp_col, mats)
    strings_by_step = build_strings(harp_col, mats)
    beads = build_pluck_beads(harp_col, mats, count=8)

    animate_harp(timeline, strings_by_step, beads, pedal_objs)
    setup_harp_camera(timeline["total_frames"])
    return timeline


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    stills_only = "--stills-only" in argv
    render_vid = "--render-video" in argv

    timeline = build_scene()
    save_blend(BLEND_PATH)

    if stills_only:
        frame_specs = [
            ("idle", 1),
            ("glissando", sec_to_frame(4.5, 24)),
            ("chord", sec_to_frame(11.4, 24)),
        ]
        rendered = render_diagnostic_stills(frame_specs, STILLS_DIR, "diag_harp")
        for p in rendered:
            print(f"[harp_53edo] Diagnostic still: {p}")

    if render_vid:
        render_video(WEBM_PATH, WAV_PATH, timeline["total_frames"], TMP_FRAMES_DIR, fps=24)


if __name__ == "__main__":
    main()
