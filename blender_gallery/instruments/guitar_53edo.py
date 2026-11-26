"""The 53-Fret Logarithmic Concert Guitar — Blender 4.2 EEVEE Next showcase."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

import bmesh
import bpy
from mathutils import Matrix, Vector

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blender_gallery import common

SCORE_PATH = REPO_ROOT / "scores" / "showcase_3d" / "02_guitar_53edo.json"
WAV_PATH = REPO_ROOT / "output" / "showcase_3d" / "02_guitar_53edo.wav"
BLEND_PATH = REPO_ROOT / "output" / "showcase_3d" / "02_guitar_53edo.blend"
WEBM_PATH = REPO_ROOT / "output" / "showcase_3d" / "02_guitar_53edo.webm"
OUT_DIR = REPO_ROOT / "output" / "showcase_3d"
TMP_FRAMES_DIR = Path("/tmp/frames_guitar_53edo")

PEDESTAL_Z = 0.09
NUM_FRETS = 53
NUM_STRINGS = 6

SCALE_LENGTH = 0.98
BODY_MIN_X = -0.185
BODY_MAX_X = 0.505
BODY_DEPTH = 0.108
SOUNDBOARD_THICK = 0.004
FRETBOARD_MIN_X = 0.435
FRETBOARD_MAX_X = SCALE_LENGTH
FRETBOARD_THICK = 0.0085
NUT_X = SCALE_LENGTH
SADDLE_X = 0.0
SOUNDHOLE_X = 0.305
SOUNDHOLE_R = 0.062

NECK_TILT_DEG = 28.0
SOUNDBOARD_LEAN_DEG = 20.0

OPEN_STRING_STEPS = [-68, -46, -24, -2, 15, 37]
STRING_IDLE_COLORS = [
    (0.72, 0.42, 0.20),
    (0.74, 0.48, 0.24),
    (0.76, 0.55, 0.30),
    (0.72, 0.72, 0.76),
    (0.74, 0.74, 0.78),
    (0.76, 0.76, 0.80),
]
FRET_IDLE_RGB = (0.04, 0.04, 0.05)


def _guitar_frame_basis() -> tuple[Vector, Vector, Vector]:
    """Return orthonormal right-handed (u_neck, v_bass_up, n_soundboard) world axes."""
    tilt = math.radians(NECK_TILT_DEG)
    lean = math.radians(SOUNDBOARD_LEAN_DEG)
    u_ax = Vector((math.cos(tilt), 0.0, math.sin(tilt))).normalized()
    desired_n = Vector((0.0, -math.cos(lean), math.sin(lean))).normalized()
    n_ax = (desired_n - desired_n.dot(u_ax) * u_ax).normalized()
    v_ax = n_ax.cross(u_ax).normalized()
    return u_ax, v_ax, n_ax


def _guitar_outline_point(t_param: float) -> tuple[float, float]:
    """Smooth C-infinity classical hourglass outline parameterized by t in [0, 2*pi)."""
    u = 0.5 * (1.0 - math.cos(t_param))
    gx = BODY_MIN_X + u * (BODY_MAX_X - BODY_MIN_X)
    # Asymmetric bout envelope + deep waist pinch
    t_abs = t_param if t_param <= math.pi else (2.0 * math.pi - t_param)
    waist_pinch = 0.095 * math.exp(-((t_abs - 1.56) / 0.40) ** 2)
    bout_amp = 0.242 - 0.036 * math.cos(t_abs) - waist_pinch
    gy = math.sin(t_param) * bout_amp
    return gx, gy


def _raycast_body_perimeter(n_rays: int = 72) -> list[tuple[float, float]]:
    """Sample body outline at uniform angles around (SOUNDHOLE_X, 0) for watertight radial meshing."""
    poly = [_guitar_outline_point(2.0 * math.pi * (i / 512.0)) for i in range(512)]
    out: list[tuple[float, float]] = []
    cx, cy = SOUNDHOLE_X, 0.0
    for k in range(n_rays):
        ang = 2.0 * math.pi * (k / float(n_rays))
        dx, dy = math.cos(ang), math.sin(ang)
        best_r = 0.15
        for i in range(len(poly)):
            x1, y1 = poly[i][0] - cx, poly[i][1] - cy
            x2, y2 = poly[(i + 1) % len(poly)][0] - cx, poly[(i + 1) % len(poly)][1] - cy
            sx, sy = x2 - x1, y2 - y1
            denom = dx * sy - dy * sx
            if abs(denom) < 1e-10:
                continue
            r = (x1 * sy - y1 * sx) / denom
            u = (x1 * dy - y1 * dx) / denom
            if r > 0.0 and -1e-4 <= u <= 1.0 + 1e-4:
                best_r = r
                break
        out.append((cx + best_r * dx, cy + best_r * dy))
    return out


def _fret_x(k: int) -> float:
    """Logarithmic 53-EDO fret position along local +X_g for k in 0..53."""
    return NUT_X - SCALE_LENGTH * (1.0 - (2.0 ** (-k / 53.0)))


def _fretboard_half_width(gx: float) -> float:
    """Linear taper from nut (0.0285m) to body tongue (0.0365m)."""
    t = max(0.0, min(1.0, (NUT_X - gx) / (NUT_X - FRETBOARD_MIN_X)))
    return 0.0285 + 0.0082 * t


def _string_y(s_idx: int, gx: float) -> float:
    """String lateral Y coordinate from bass (+Y_g, idx 0) to treble (-Y_g, idx 5)."""
    t_len = max(0.0, min(1.0, (gx - SADDLE_X) / (NUT_X - SADDLE_X)))
    span = 0.058 + (0.044 - 0.058) * t_len
    frac = s_idx / float(NUM_STRINGS - 1)
    return (0.5 - frac) * span


def _string_z(gx: float) -> float:
    """String height above local soundboard surface (z=0) at gx."""
    if gx <= NUT_X:
        t = max(0.0, min(1.0, (gx - SADDLE_X) / (NUT_X - SADDLE_X)))
        return 0.0135 * (1.0 - t) + (FRETBOARD_THICK + 0.0038) * t
    return FRETBOARD_THICK + 0.0038


def _guitar_pivot_and_matrix() -> tuple[Vector, Matrix]:
    """Compute guitar world pivot and 4x4 transform so lower bout rests cleanly above z=0.09."""
    u_ax, v_ax, n_ax = _guitar_frame_basis()
    rot_m = Matrix((
        (u_ax.x, v_ax.x, n_ax.x, 0.0),
        (u_ax.y, v_ax.y, n_ax.y, 0.0),
        (u_ax.z, v_ax.z, n_ax.z, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    ))
    min_z = 1e9
    for i in range(96):
        gx, gy = _guitar_outline_point(2.0 * math.pi * (i / 96.0))
        for gz in (-BODY_DEPTH, 0.0):
            wz = (rot_m @ Vector((gx, gy, gz))).z
            if wz < min_z:
                min_z = wz
    target_min_z = PEDESTAL_Z + 0.062
    pivot = Vector((-0.24, 0.02, target_min_z - min_z))
    return pivot, Matrix.Translation(pivot) @ rot_m


def _new_mesh_obj(
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
    if smooth and len(mesh.polygons) > 0:
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    obj = bpy.data.objects.new(name, mesh)
    for m in mats:
        obj.data.materials.append(m)
    col.objects.link(obj)
    return obj


def _loft_rings(
    bm: bmesh.types.BMesh,
    rings: list[list[bmesh.types.BMVert]],
    cap_start: bool = True,
    cap_end: bool = True,
) -> None:
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


def _build_body_and_soundboard(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
    guitar_mat: Matrix,
) -> None:
    """Build smooth hourglass DarkRosewood ribs/back, watertight AntiqueSpruce top, brass rosette, and bridge."""
    n_prof = 144
    perimeter = _raycast_body_perimeter(n_prof)

    # 1) DarkRosewood back, sides & subtle bevel binding
    bm_body = bmesh.new()
    z_layers = [
        (-BODY_DEPTH, 0.95),
        (-BODY_DEPTH + 0.009, 0.996),
        (-SOUNDBOARD_THICK, 1.002),
        (0.0005, 0.998),
    ]
    rings: list[list[bmesh.types.BMVert]] = []
    for z_val, scale_xy in z_layers:
        ring = []
        for gx, gy in perimeter:
            cx = 0.16
            sx = cx + (gx - cx) * scale_xy
            sy = gy * scale_xy
            dome = -0.007 * max(0.0, 1.0 - ((gx - 0.12) / 0.36) ** 2) if z_val < -BODY_DEPTH + 0.01 else 0.0
            ring.append(bm_body.verts.new(guitar_mat @ Vector((sx, sy, z_val + dome))))
        rings.append(ring)
    _loft_rings(bm_body, rings, cap_start=True, cap_end=False)

    inner_ring = [
        bm_body.verts.new(guitar_mat @ Vector((0.16 + (gx - 0.16) * 0.92, gy * 0.92, -BODY_DEPTH + 0.014)))
        for gx, gy in perimeter
    ]
    bm_body.faces.new(inner_ring)
    bmesh.ops.recalc_face_normals(bm_body, faces=bm_body.faces)
    _new_mesh_obj(col, "Guitar53_RosewoodBody", bm_body, [mats["DarkRosewood"]], smooth=True)

    # 2) Watertight radial-quad AntiqueSpruce soundboard with clean circular soundhole
    bm_top = bmesh.new()
    outer_top = [bm_top.verts.new(guitar_mat @ Vector((gx, gy, 0.0))) for gx, gy in perimeter]
    outer_bot = [bm_top.verts.new(guitar_mat @ Vector((gx, gy, -SOUNDBOARD_THICK))) for gx, gy in perimeter]
    hole_top = []
    hole_bot = []
    for k in range(n_prof):
        ang = 2.0 * math.pi * (k / float(n_prof))
        hx = SOUNDHOLE_X + SOUNDHOLE_R * math.cos(ang)
        hy = SOUNDHOLE_R * math.sin(ang)
        hole_top.append(bm_top.verts.new(guitar_mat @ Vector((hx, hy, 0.0))))
        hole_bot.append(bm_top.verts.new(guitar_mat @ Vector((hx, hy, -SOUNDBOARD_THICK))))

    for k in range(n_prof):
        kn = (k + 1) % n_prof
        # Top quad from soundhole lip to outer rim
        bm_top.faces.new((hole_top[k], outer_top[k], outer_top[kn], hole_top[kn]))
        # Outer rim thickness strip
        bm_top.faces.new((outer_bot[k], outer_bot[kn], outer_top[kn], outer_top[k]))
        # Inner soundhole wall
        bm_top.faces.new((hole_top[k], hole_top[kn], hole_bot[kn], hole_bot[k]))

    bmesh.ops.recalc_face_normals(bm_top, faces=bm_top.faces)
    _new_mesh_obj(col, "Guitar53_SpruceSoundboard", bm_top, [mats["AntiqueSpruce"]], smooth=True)

    # 3) Dark hollow cavity disc inside body beneath soundhole
    bm_cav = bmesh.new()
    cav_ring = [
        bm_cav.verts.new(
            guitar_mat
            @ Vector(
                (
                    SOUNDHOLE_X + 0.14 * math.cos(2.0 * math.pi * k / 32.0),
                    0.14 * math.sin(2.0 * math.pi * k / 32.0),
                    -BODY_DEPTH + 0.017,
                )
            )
        )
        for k in range(32)
    ]
    bm_cav.faces.new(cav_ring)
    _new_mesh_obj(col, "Guitar53_SoundholeCavity", bm_cav, [mats["GlossEbony"]], smooth=False)

    # 4) Inlaid concentric brass soundhole rosette rings
    bm_ros = bmesh.new()
    for r_in, r_out, z_off in (
        (SOUNDHOLE_R + 0.004, SOUNDHOLE_R + 0.0085, 0.0008),
        (SOUNDHOLE_R + 0.013, SOUNDHOLE_R + 0.0195, 0.0009),
        (SOUNDHOLE_R + 0.023, SOUNDHOLE_R + 0.0265, 0.0008),
    ):
        n_s = 48
        v_in_b, v_out_b, v_in_t, v_out_t = [], [], [], []
        for k in range(n_s):
            ang = 2.0 * math.pi * (k / float(n_s))
            ca, sa = math.cos(ang), math.sin(ang)
            v_in_b.append(bm_ros.verts.new(guitar_mat @ Vector((SOUNDHOLE_X + r_in * ca, r_in * sa, -0.0005))))
            v_out_b.append(bm_ros.verts.new(guitar_mat @ Vector((SOUNDHOLE_X + r_out * ca, r_out * sa, -0.0005))))
            v_in_t.append(bm_ros.verts.new(guitar_mat @ Vector((SOUNDHOLE_X + r_in * ca, r_in * sa, z_off))))
            v_out_t.append(bm_ros.verts.new(guitar_mat @ Vector((SOUNDHOLE_X + r_out * ca, r_out * sa, z_off))))
        for k in range(n_s):
            kn = (k + 1) % n_s
            bm_ros.faces.new((v_in_t[k], v_out_t[k], v_out_t[kn], v_in_t[kn]))
            bm_ros.faces.new((v_in_b[k], v_in_t[k], v_in_t[kn], v_in_b[kn]))
            bm_ros.faces.new((v_out_t[k], v_out_b[k], v_out_b[kn], v_out_t[kn]))
    bmesh.ops.recalc_face_normals(bm_ros, faces=bm_ros.faces)
    _new_mesh_obj(col, "Guitar53_BrassRosette", bm_ros, [mats["PolishedBrass"]], smooth=True)

    # 5) Rosewood bridge + ivory saddle + 6 brass bridge pins
    bm_br = bmesh.new()
    bmesh.ops.create_cube(
        bm_br,
        size=1.0,
        matrix=guitar_mat @ Matrix.Translation((SADDLE_X - 0.012, 0.0, 0.0055)) @ Matrix.Diagonal((0.036, 0.082, 0.011, 1.0)),
    )
    for sy in (-0.068, 0.068):
        bmesh.ops.create_cube(
            bm_br,
            size=1.0,
            matrix=guitar_mat @ Matrix.Translation((SADDLE_X - 0.012, sy, 0.0032)) @ Matrix.Diagonal((0.032, 0.056, 0.0064, 1.0)),
        )
    _new_mesh_obj(col, "Guitar53_Bridge", bm_br, [mats["DarkRosewood"]], smooth=False)

    bm_sad = bmesh.new()
    bmesh.ops.create_cube(
        bm_sad,
        size=1.0,
        matrix=guitar_mat @ Matrix.Translation((SADDLE_X, 0.0, 0.0115)) @ Matrix.Diagonal((0.0042, 0.068, 0.0055, 1.0)),
    )
    _new_mesh_obj(col, "Guitar53_IvorySaddle", bm_sad, [mats["IvoryKey"]], smooth=False)

    bm_bpins = bmesh.new()
    for s_idx in range(NUM_STRINGS):
        sy = _string_y(s_idx, SADDLE_X)
        bmesh.ops.create_cone(
            bm_bpins,
            cap_ends=True,
            cap_tris=False,
            segments=10,
            radius1=0.0026,
            radius2=0.0034,
            depth=0.007,
            matrix=guitar_mat @ Matrix.Translation((SADDLE_X - 0.020, sy, 0.012)),
        )
    _new_mesh_obj(col, "Guitar53_BridgePins", bm_bpins, [mats["PolishedBrass"]], smooth=True)


def _build_neck_headstock_and_frets(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
    guitar_mat: Matrix,
) -> dict[int, bpy.types.Object]:
    """Build WarmMahogany neck, slotted headstock + 6 pegs, GlossEbony fretboard, 53 brass frets & 53 luminous bars."""
    bm_neck = bmesh.new()
    n_u = 16
    n_arc = 11
    neck_rings: list[list[bmesh.types.BMVert]] = []
    for i in range(n_u):
        t = i / float(n_u - 1)
        gx = 0.490 + t * (NUT_X - 0.490)
        hw = _fretboard_half_width(gx)
        depth = 0.072 if i == 0 else (0.024 - 0.005 * t)
        ring = []
        for k in range(n_arc):
            ang = math.pi * (k / float(n_arc - 1))
            ring.append(bm_neck.verts.new(guitar_mat @ Vector((gx, hw * math.cos(ang), -depth * math.sin(ang)))))
        neck_rings.append(ring)
    _loft_rings(bm_neck, neck_rings, cap_start=True, cap_end=True)

    hs_tilt = math.radians(14.0)
    hs_mat = guitar_mat @ Matrix.Translation((NUT_X, 0.0, 0.002)) @ Matrix.Rotation(hs_tilt, 4, "Y")
    for cy in (-0.030, 0.0, 0.030):
        w_cheek = 0.015 if cy != 0.0 else 0.013
        bmesh.ops.create_cube(
            bm_neck,
            size=1.0,
            matrix=hs_mat @ Matrix.Translation((0.105, cy, -0.006)) @ Matrix.Diagonal((0.190, w_cheek, 0.018, 1.0)),
        )
    bmesh.ops.create_cube(
        bm_neck,
        size=1.0,
        matrix=hs_mat @ Matrix.Translation((0.018, 0.0, -0.006)) @ Matrix.Diagonal((0.036, 0.074, 0.018, 1.0)),
    )
    bmesh.ops.create_cube(
        bm_neck,
        size=1.0,
        matrix=hs_mat @ Matrix.Translation((0.195, 0.0, -0.006)) @ Matrix.Diagonal((0.030, 0.076, 0.019, 1.0)),
    )
    bmesh.ops.recalc_face_normals(bm_neck, faces=bm_neck.faces)
    _new_mesh_obj(col, "Guitar53_MahoganyNeck", bm_neck, [mats["WarmMahogany"]], smooth=True)

    # GlossEbony fretboard
    bm_fb = bmesh.new()
    fb_rings: list[list[bmesh.types.BMVert]] = []
    for gx in (FRETBOARD_MIN_X, 0.56, 0.78, NUT_X):
        hw = _fretboard_half_width(gx)
        pts = [
            Vector((gx, -hw, 0.0)),
            Vector((gx, hw, 0.0)),
            Vector((gx, hw * 0.96, FRETBOARD_THICK)),
            Vector((gx, -hw * 0.96, FRETBOARD_THICK)),
        ]
        fb_rings.append([bm_fb.verts.new(guitar_mat @ p) for p in pts])
    _loft_rings(bm_fb, fb_rings, cap_start=True, cap_end=True)
    bmesh.ops.recalc_face_normals(bm_fb, faces=bm_fb.faces)
    _new_mesh_obj(col, "Guitar53_EbonyFretboard", bm_fb, [mats["GlossEbony"]], smooth=False)

    # Ivory nut
    bm_nut = bmesh.new()
    nut_hw = _fretboard_half_width(NUT_X)
    bmesh.ops.create_cube(
        bm_nut,
        size=1.0,
        matrix=guitar_mat @ Matrix.Translation((NUT_X + 0.0025, 0.0, FRETBOARD_THICK + 0.002))
        @ Matrix.Diagonal((0.005, nut_hw * 1.96, 0.005, 1.0)),
    )
    _new_mesh_obj(col, "Guitar53_IvoryNut", bm_nut, [mats["IvoryKey"]], smooth=False)

    # 6 PolishedBrass tuning pegs
    bm_pegs = bmesh.new()
    rot_y = Matrix.Rotation(math.pi * 0.5, 4, "X")
    for side in (-1.0, 1.0):
        for p_i in range(3):
            px = 0.056 + p_i * 0.048
            bmesh.ops.create_cone(
                bm_pegs,
                cap_ends=True,
                cap_tris=False,
                segments=12,
                radius1=0.0042,
                radius2=0.0042,
                depth=0.032,
                matrix=hs_mat @ Matrix.Translation((px, side * 0.015, -0.006)) @ rot_y,
            )
            bmesh.ops.create_cone(
                bm_pegs,
                cap_ends=True,
                cap_tris=False,
                segments=10,
                radius1=0.0032,
                radius2=0.0032,
                depth=0.036,
                matrix=hs_mat @ Matrix.Translation((px, side * 0.048, -0.006)) @ rot_y,
            )
            bmesh.ops.create_cube(
                bm_pegs,
                size=1.0,
                matrix=hs_mat @ Matrix.Translation((px, side * 0.068, -0.006)) @ Matrix.Diagonal((0.020, 0.007, 0.014, 1.0)),
            )
    _new_mesh_obj(col, "Guitar53_BrassTuningPegs", bm_pegs, [mats["PolishedBrass"]], smooth=True)

    # 53 micro-spaced logarithmic PolishedBrass frets
    bm_frets = bmesh.new()
    for k in range(1, NUM_FRETS + 1):
        fx = _fret_x(k)
        f_hw = _fretboard_half_width(fx) * 0.97
        r_wire = 0.0011 if (k % 53 != 0 and k != 17 and k != 31) else 0.00145
        bmesh.ops.create_cone(
            bm_frets,
            cap_ends=True,
            cap_tris=False,
            segments=8,
            radius1=r_wire,
            radius2=r_wire,
            depth=f_hw * 1.98,
            matrix=guitar_mat @ Matrix.Translation((fx, 0.0, FRETBOARD_THICK + r_wire * 0.65)) @ rot_y,
        )
    _new_mesh_obj(col, "Guitar53_LogarithmicFrets", bm_frets, [mats["PolishedBrass"]], smooth=True)

    # 53 glowing luminous fret-marker bars perched along the fretboard (idle dark ebony-slate -> vivid jewel on trigger)
    fret_bars: dict[int, bpy.types.Object] = {}
    lum_mat = mats["LuminousElement"]
    for pc in range(NUM_FRETS):
        bx = 0.5 * (NUT_X + _fret_x(1)) if pc == 0 else 0.5 * (_fret_x(pc) + _fret_x(pc + 1))
        b_hw = _fretboard_half_width(bx) * 0.90
        bm_bar = bmesh.new()
        bmesh.ops.create_cube(
            bm_bar,
            size=1.0,
            matrix=guitar_mat @ Matrix.Translation((bx, 0.0, FRETBOARD_THICK + 0.0016))
            @ Matrix.Diagonal((0.0044, b_hw * 1.92, 0.0032, 1.0)),
        )
        bar_obj = _new_mesh_obj(col, f"Guitar53_FretBar_{pc:02d}", bm_bar, [lum_mat], smooth=False)
        bar_obj.color = (FRET_IDLE_RGB[0], FRET_IDLE_RGB[1], FRET_IDLE_RGB[2], 0.03)
        fret_bars[pc] = bar_obj

    return fret_bars


def _build_strings(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
    guitar_mat: Matrix,
) -> list[dict[str, Any]]:
    """Build 6 individual vibrating strings with Pluck shape keys sharing LuminousElement."""
    lum_mat = mats["LuminousElement"]
    strings: list[dict[str, Any]] = []
    n_rings = 24
    n_sides = 8
    hs_tilt = math.radians(14.0)
    hs_mat = guitar_mat @ Matrix.Translation((NUT_X, 0.0, 0.002)) @ Matrix.Rotation(hs_tilt, 4, "Y")

    for s_idx in range(NUM_STRINGS):
        radius = 0.0013 - 0.00012 * s_idx
        p_sad = guitar_mat @ Vector((SADDLE_X, _string_y(s_idx, SADDLE_X), _string_z(SADDLE_X)))
        p_nut = guitar_mat @ Vector((NUT_X, _string_y(s_idx, NUT_X), _string_z(NUT_X)))
        side = 1.0 if s_idx < 3 else -1.0
        peg_i = s_idx if s_idx < 3 else (5 - s_idx)
        cap_x = 0.056 + peg_i * 0.048
        p_peg = hs_mat @ Vector((cap_x, side * 0.015, -0.002))

        pts_local: list[Vector] = []
        ts_vib: list[float] = []
        for r_i in range(n_rings - 2):
            t = r_i / float(n_rings - 3)
            pts_local.append(p_sad.lerp(p_nut, t))
            ts_vib.append(t)
        pts_local.append(p_nut.lerp(p_peg, 0.5))
        ts_vib.append(0.0)
        pts_local.append(p_peg)
        ts_vib.append(0.0)

        bm = bmesh.new()
        rings: list[list[bmesh.types.BMVert]] = []
        normal_world = (guitar_mat.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
        for r_i, c_pt in enumerate(pts_local):
            tan = (pts_local[r_i + 1] - c_pt).normalized() if r_i < len(pts_local) - 1 else (c_pt - pts_local[r_i - 1]).normalized()
            side_b = tan.cross(normal_world).normalized()
            up_b = side_b.cross(tan).normalized()
            ring = []
            for k in range(n_sides):
                ang = 2.0 * math.pi * (k / float(n_sides))
                ring.append(bm.verts.new(c_pt + side_b * (radius * math.cos(ang)) + up_b * (radius * math.sin(ang))))
            rings.append(ring)
        _loft_rings(bm, rings, cap_start=True, cap_end=True)

        obj = _new_mesh_obj(col, f"Guitar53_String_{s_idx}", bm, [lum_mat], smooth=True)
        idle_rgb = STRING_IDLE_COLORS[s_idx]
        obj.color = (idle_rgb[0], idle_rgb[1], idle_rgb[2], 0.04)

        obj.shape_key_add(name="Basis", from_mix=False)
        kb = obj.shape_key_add(name="Pluck", from_mix=False)
        kb.slider_min = -1.6
        kb.slider_max = 1.6
        kb.value = 0.0
        amp = 0.009 + 0.0035 * (1.0 - s_idx / 5.0)
        lat_world = (guitar_mat.to_3x3() @ Vector((0.0, 0.85, 0.45))).normalized()
        for v_i, vert in enumerate(obj.data.vertices):
            t = ts_vib[v_i // n_sides]
            kb.data[v_i].co = vert.co + lat_world * (amp * math.sin(math.pi * t))

        strings.append({
            "obj": obj,
            "kb": kb,
            "idle_rgb": idle_rgb,
            "open_step": OPEN_STRING_STEPS[s_idx],
        })
    return strings


def _build_cradle(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
    guitar_mat: Matrix,
) -> None:
    """Build open-rail GlossEbony & PolishedBrass cradle seated flush at z=PEDESTAL_Z (0.09)."""
    contact_pts: list[Vector] = []
    for gx_sample in (-0.06, 0.14):
        best_pt = None
        best_z = 1e9
        for t_i in range(128):
            gx, gy = _guitar_outline_point(2.0 * math.pi * (t_i / 128.0))
            if gy >= 0.0 or abs(gx - gx_sample) > 0.025:
                continue
            for gz in (-BODY_DEPTH * 0.55, -BODY_DEPTH * 0.25, 0.0):
                wp = guitar_mat @ Vector((gx, gy, gz))
                if wp.z < best_z:
                    best_z = wp.z
                    best_pt = wp
        if best_pt is not None:
            contact_pts.append(best_pt)

    neck_support_pt = guitar_mat @ Vector((0.52, -0.020, -0.020))
    all_pts = contact_pts + [neck_support_pt]
    xs = [p.x for p in all_pts]
    ys = [p.y for p in all_pts]
    cx = 0.5 * (min(xs) + max(xs))
    cy = 0.5 * (min(ys) + max(ys))
    span_x = (max(xs) - min(xs)) + 0.22

    # Sculpted open H-frame GlossEbony rails (no big mirror slab!) flush at z=0.09
    bm_base = bmesh.new()
    # Main longitudinal spine rail
    bmesh.ops.create_cube(
        bm_base,
        size=1.0,
        matrix=Matrix.Translation((cx, cy, PEDESTAL_Z + 0.015)) @ Matrix.Diagonal((span_x, 0.064, 0.030, 1.0)),
    )
    # Cross-feet at ends
    for fx in (cx - span_x * 0.43, cx + span_x * 0.43):
        bmesh.ops.create_cube(
            bm_base,
            size=1.0,
            matrix=Matrix.Translation((fx, cy, PEDESTAL_Z + 0.014)) @ Matrix.Diagonal((0.056, 0.28, 0.028, 1.0)),
        )
    base_obj = _new_mesh_obj(col, "Guitar53_CradleFrame", bm_base, [mats["GlossEbony"]], smooth=False)
    bev = base_obj.modifiers.new("Bevel", "BEVEL")
    bev.width = 0.004
    bev.segments = 2

    # Brass foot pads & rail inlay
    bm_btrim = bmesh.new()
    bmesh.ops.create_cube(
        bm_btrim,
        size=1.0,
        matrix=Matrix.Translation((cx, cy, PEDESTAL_Z + 0.031)) @ Matrix.Diagonal((span_x - 0.03, 0.024, 0.004, 1.0)),
    )
    for fx in (cx - span_x * 0.43, cx + span_x * 0.43):
        for fy in (cy - 0.125, cy + 0.125):
            bmesh.ops.create_cone(
                bm_btrim,
                cap_ends=True,
                cap_tris=False,
                segments=14,
                radius1=0.022,
                radius2=0.018,
                depth=0.008,
                matrix=Matrix.Translation((fx, fy, PEDESTAL_Z + 0.004)),
            )
    _new_mesh_obj(col, "Guitar53_CradleBrassTrim", bm_btrim, [mats["PolishedBrass"]], smooth=True)

    # Vertical ebony columns + brass U-yokes
    bm_cols = bmesh.new()
    bm_saddles = bmesh.new()
    base_top_z = PEDESTAL_Z + 0.030
    for idx, pt in enumerate(all_pts):
        col_h = max(0.02, pt.z - base_top_z - 0.004)
        rad = 0.015 if idx < 2 else 0.012
        bmesh.ops.create_cone(
            bm_cols,
            cap_ends=True,
            cap_tris=False,
            segments=16,
            radius1=rad * 1.3,
            radius2=rad,
            depth=col_h,
            matrix=Matrix.Translation((pt.x, pt.y, base_top_z + col_h * 0.5)),
        )
        bmesh.ops.create_cone(
            bm_saddles,
            cap_ends=True,
            cap_tris=False,
            segments=16,
            radius1=rad * 1.5,
            radius2=rad * 1.4,
            depth=0.010,
            matrix=Matrix.Translation((pt.x, pt.y, base_top_z + 0.005)),
        )
        yoke_w = 0.088 if idx < 2 else 0.056
        bmesh.ops.create_cube(
            bm_saddles,
            size=1.0,
            matrix=Matrix.Translation((pt.x, pt.y, pt.z - 0.005)) @ Matrix.Diagonal((0.030, yoke_w, 0.010, 1.0)),
        )
        for sy in (-yoke_w * 0.46, yoke_w * 0.46):
            bmesh.ops.create_cube(
                bm_saddles,
                size=1.0,
                matrix=Matrix.Translation((pt.x, pt.y + sy, pt.z + 0.012)) @ Matrix.Diagonal((0.026, 0.010, 0.034, 1.0)),
            )

    _new_mesh_obj(col, "Guitar53_CradleColumns", bm_cols, [mats["GlossEbony"]], smooth=True)
    _new_mesh_obj(col, "Guitar53_CradleBrassYokes", bm_saddles, [mats["PolishedBrass"]], smooth=True)


def _assign_note_to_string(step: int, start_s: float, string_busy_until: list[float]) -> int:
    candidates = []
    for s_idx, open_s in enumerate(OPEN_STRING_STEPS):
        busy_pen = 100.0 if string_busy_until[s_idx] > start_s + 0.02 else 0.0
        dist = abs(step - (open_s + 14))
        candidates.append((busy_pen + dist, s_idx))
    candidates.sort()
    return candidates[0][1]


def _animate_guitar(
    timeline: dict[str, Any],
    fret_bars: dict[int, bpy.types.Object],
    strings: list[dict[str, Any]],
) -> None:
    """Animate 53 luminous fret-marker bars and 6 vibrating luminous strings."""
    fps = int(timeline["fps"])
    total_frames = int(timeline["total_frames"])
    notes = sorted(timeline.get("notes", []), key=lambda n: (n["start_s"], n["step"]))

    notes_by_pc: dict[int, list[dict[str, Any]]] = {pc: [] for pc in range(NUM_FRETS)}
    notes_by_str: list[list[dict[str, Any]]] = [[] for _ in range(NUM_STRINGS)]
    string_busy_until = [-1.0] * NUM_STRINGS

    for ev in notes:
        step = int(ev["step"])
        pc = step % NUM_FRETS
        notes_by_pc[pc].append(ev)
        s_idx = _assign_note_to_string(step, float(ev["start_s"]), string_busy_until)
        string_busy_until[s_idx] = float(ev["end_s"])
        notes_by_str[s_idx].append(ev)

    # 53 fret-marker bars: idle dark slate (alpha=0.03) -> vivid jewel hue (alpha=1.0) on trigger
    for pc, bar_obj in fret_bars.items():
        evts = notes_by_pc[pc]
        bar_obj.color = (*FRET_IDLE_RGB, 0.03)
        bar_obj.keyframe_insert(data_path="color", frame=1)
        if not evts:
            continue

        rgb = common.vivid_53edo_color(pc)
        intervals: list[tuple[int, int, float]] = []
        for ev in evts:
            f0 = common.sec_to_frame(ev["start_s"], fps)
            f1 = min(total_frames, max(f0 + 2, common.sec_to_frame(ev["end_s"], fps)))
            peak = min(1.0, 0.92 + 0.10 * float(ev.get("vel", 0.8)))
            if intervals and f0 <= intervals[-1][1] + 1:
                prev_f0, prev_f1, prev_pk = intervals[-1]
                intervals[-1] = (prev_f0, max(prev_f1, f1), max(prev_pk, peak))
            else:
                intervals.append((f0, f1, peak))

        const_frames: set[int] = {1}
        for i, (f0, f1, peak) in enumerate(intervals):
            next_f0 = intervals[i + 1][0] if i + 1 < len(intervals) else total_frames + 10
            if f0 > 2:
                bar_obj.color = (*FRET_IDLE_RGB, 0.03)
                bar_obj.keyframe_insert(data_path="color", frame=f0 - 1)
                const_frames.add(f0 - 1)
            bar_obj.color = (*rgb, peak)
            bar_obj.keyframe_insert(data_path="color", frame=f0)
            hold_f = min(f1, next_f0 - 2)
            if hold_f > f0:
                bar_obj.color = (*rgb, max(0.75, peak * 0.84))
                bar_obj.keyframe_insert(data_path="color", frame=hold_f)
            if hold_f + 1 < next_f0 and hold_f + 1 <= total_frames:
                bar_obj.color = (*FRET_IDLE_RGB, 0.03)
                bar_obj.keyframe_insert(data_path="color", frame=hold_f + 1)
                const_frames.add(hold_f + 1)
        for ch in range(4):
            common.set_constant_segment(bar_obj, "color", ch, const_frames)

    # 6 strings: vivid jewel color + damped standing-wave oscillation
    for s_idx, sinfo in enumerate(strings):
        obj = sinfo["obj"]
        kb = sinfo["kb"]
        idle_rgb = sinfo["idle_rgb"]
        evts = notes_by_str[s_idx]

        obj.color = (*idle_rgb, 0.04)
        obj.keyframe_insert(data_path="color", frame=1)
        kb.value = 0.0
        kb.keyframe_insert(data_path="value", frame=1)
        if not evts:
            continue

        const_frames_c: set[int] = {1}
        for i, ev in enumerate(evts):
            f0 = common.sec_to_frame(ev["start_s"], fps)
            dur_s = float(ev["dur_s"])
            f1 = min(total_frames, max(f0 + 3, common.sec_to_frame(ev["start_s"] + min(dur_s, 1.8), fps)))
            next_f0 = common.sec_to_frame(evts[i + 1]["start_s"], fps) if i + 1 < len(evts) else total_frames + 10
            rgb = common.vivid_53edo_color(int(ev["step"]))

            if f0 > 2:
                obj.color = (*idle_rgb, 0.04)
                obj.keyframe_insert(data_path="color", frame=f0 - 1)
                const_frames_c.add(f0 - 1)
                kb.value = 0.0
                kb.keyframe_insert(data_path="value", frame=f0 - 1)

            peak_a = min(1.0, 0.90 + 0.12 * float(ev.get("vel", 0.8)))
            obj.color = (*rgb, peak_a)
            obj.keyframe_insert(data_path="color", frame=f0)

            clip_end = min(f1, next_f0 - 2)
            for f in range(f0 + 2, clip_end + 1, 2):
                u = min(1.0, ((f - 1) / float(fps) - ev["start_s"]) / max(0.08, min(dur_s, 1.8)))
                a_val = 0.04 + (peak_a - 0.04) * max(0.0, 1.0 - (u ** 2.2))
                obj.color = (*rgb, a_val)
                obj.keyframe_insert(data_path="color", frame=f)

            if clip_end + 1 < next_f0 and clip_end + 1 <= total_frames:
                obj.color = (*idle_rgb, 0.04)
                obj.keyframe_insert(data_path="color", frame=clip_end + 1)
                const_frames_c.add(clip_end + 1)

            vib_frames = min(30, max(8, int(round(min(dur_s, 1.25) * fps))))
            vib_end = min(f0 + vib_frames, next_f0 - 2, total_frames)
            vel_amp = 0.90 + 0.45 * float(ev.get("vel", 0.8))
            for k in range(vib_end - f0 + 1):
                damp = math.exp(-0.10 * k)
                kb.value = vel_amp * damp * (1.0 if k % 2 == 0 else -1.0)
                kb.keyframe_insert(data_path="value", frame=f0 + k)
            if vib_end + 1 < next_f0 and vib_end + 1 <= total_frames:
                kb.value = 0.0
                kb.keyframe_insert(data_path="value", frame=vib_end + 1)

        for idx_ch in range(4):
            common.set_constant_segment(obj, "color", idx_ch, const_frames_c)


def build_instrument(
    mats: dict[str, bpy.types.Material],
    timeline: dict[str, Any],
    *,
    collection_name: str = "Guitar53EDO",
    anchor_location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    anchor_rotation_z_deg: float = 0.0,
    anchor_scale: float = 1.0,
) -> bpy.types.Object:
    """Build and animate the 53-Fret Concert Guitar inside collection_name and attach to an anchor Empty."""
    col = bpy.data.collections.new(collection_name)
    bpy.context.scene.collection.children.link(col)

    _, guitar_mat = _guitar_pivot_and_matrix()
    _build_body_and_soundboard(col, mats, guitar_mat)
    fret_bars = _build_neck_headstock_and_frets(col, mats, guitar_mat)
    strings = _build_strings(col, mats, guitar_mat)
    _build_cradle(col, mats, guitar_mat)

    folded_timeline = {
        **timeline,
        "notes": [
            {**n, "step": common.fold_step_to_range(int(n["step"]), -68, 57)}
            for n in timeline.get("notes", [])
        ],
    }
    _animate_guitar(folded_timeline, fret_bars, strings)
    return common.parent_collection_to_anchor(
        col,
        f"{collection_name}_Anchor",
        location=anchor_location,
        rotation_z_deg=anchor_rotation_z_deg,
        scale=anchor_scale,
    )


def build_scene() -> dict[str, Any]:
    """Assemble the standalone 02_guitar_53edo showcase scene."""
    scene = common.reset_scene(fps=24, res_x=1920, res_y=1080, taa_samples=8)
    scene.view_settings.exposure = -0.34
    mats = common.create_studio_materials()

    # Soften pedestal specular hotspot locally in standalone showcase
    ped_bsdf = mats["PedestalWood"].node_tree.nodes.get("Principled BSDF")
    if ped_bsdf is not None:
        ped_bsdf.inputs["Roughness"].default_value = 0.62
        ped_bsdf.inputs["Specular IOR Level"].default_value = 0.18
        ped_bsdf.inputs["Coat Weight"].default_value = 0.0

    common.build_concert_stage(mats, pedestal_radius=1.65, pedestal_height=PEDESTAL_Z, light_target_z=0.52)
    for lname, scale in (("KeyLight", 0.56), ("FillLight", 0.72), ("RimLight", 0.62), ("TopAccent", 0.45)):
        lobj = bpy.data.objects.get(lname)
        if lobj and lobj.data:
            lobj.data.energy *= scale

    timeline = common.load_score_timeline(SCORE_PATH, WAV_PATH, fps=24)
    build_instrument(mats, timeline, collection_name="Guitar53EDO")

    total_frames = int(timeline["total_frames"])
    cam_keyframes = [
        (1, (0.42, -2.08, 0.88)),
        (max(2, round(total_frames * 0.45)), (0.20, -1.98, 0.94)),
        (total_frames, (0.58, -2.04, 0.86)),
    ]
    common.setup_orbit_camera(
        target_pos=(0.14, -0.02, 0.50),
        keyframes_cam_loc=cam_keyframes,
        lens_mm=38.0,
        dof_fstop=6.4,
    )
    return timeline


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    stills_only = "--stills-only" in argv
    render_vid = "--render-video" in argv

    timeline = build_scene()
    common.save_blend(BLEND_PATH)

    if stills_only:
        frame_specs = [
            ("idle", 1),
            ("campanella", common.sec_to_frame(3.5, 24)),
            ("chord", common.sec_to_frame(11.0, 24)),
        ]
        rendered = common.render_diagnostic_stills(frame_specs, OUT_DIR, "diag_guitar")
        for p in rendered:
            print(f"[guitar_53edo] Diagnostic still: {p}")

    if render_vid:
        common.render_video(WEBM_PATH, WAV_PATH, int(timeline["total_frames"]), TMP_FRAMES_DIR, fps=24)


if __name__ == "__main__":
    main()
