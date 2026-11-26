"""The 22-Shruti Sympathetic Sitar & Gourd Ektara Monochord — Blender 4.2 EEVEE Next showcase."""

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

SCORE_PATH = REPO_ROOT / "scores" / "showcase_3d" / "05_shruti_sitar_53edo.json"
WAV_PATH = REPO_ROOT / "output" / "showcase_3d" / "05_shruti_sitar_53edo.wav"
BLEND_PATH = REPO_ROOT / "output" / "showcase_3d" / "05_shruti_sitar_53edo.blend"
WEBM_PATH = REPO_ROOT / "output" / "showcase_3d" / "05_shruti_sitar_53edo.webm"
OUT_DIR = REPO_ROOT / "output" / "showcase_3d"
TMP_FRAMES_DIR = Path("/tmp/frames_sitar_shruti_53edo")

PEDESTAL_Z = 0.09

# Sitar positioned left-center so upper pegbox & finial stay cleanly separated from Ektara
SITAR_TUMBA_CENTER = Vector((-0.62, 0.04, 0.285))
SITAR_NECK_START = Vector((-0.44, 0.02, 0.355))
SITAR_NECK_END = Vector((0.50, -0.08, 0.895))
SITAR_NUM_FRETS = 22
SITAR_NUM_MAIN_STRINGS = 5
SITAR_NUM_TARAF = 13

SHRUTI_22_STEPS = [0, 2, 5, 7, 9, 12, 14, 17, 20, 22, 24, 26, 31, 33, 36, 39, 41, 43, 46, 48, 51, 53]
TARAF_STEPS = [0, 5, 9, 12, 17, 22, 26, 31, 35, 39, 43, 48, 53]

# Ektara standing upright to the right with clean silhouette separation
EKTARA_BASE_XY = Vector((0.86, -0.30, 0.0))


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


def _sitar_frame() -> tuple[Vector, Vector, Vector]:
    """Return orthonormal (u_neck, v_side, n_face) for the sitar dandi."""
    u_ax = (SITAR_NECK_END - SITAR_NECK_START).normalized()
    ref = Vector((0.0, -0.52, 0.85)).normalized()
    n_ax = (ref - ref.dot(u_ax) * u_ax).normalized()
    v_ax = n_ax.cross(u_ax).normalized()
    return u_ax, v_ax, n_ax


def _fret_u(f_idx: int) -> float:
    """Logarithmic-shruti normalized position along neck [0.20..0.82] for fret 0..21."""
    step = SHRUTI_22_STEPS[f_idx]
    d = 1.0 - (2.0 ** (-step / 53.0))
    return 0.82 - 1.24 * d


def _build_sitar_cradle(col: bpy.types.Collection, mats: dict[str, bpy.types.Material]) -> None:
    """Build sculpted DarkRosewood & BrushedGold floor cradle seated flush at z=PEDESTAL_Z."""
    tc = SITAR_TUMBA_CENTER
    bm_base = bmesh.new()
    bmesh.ops.create_cone(
        bm_base,
        cap_ends=True,
        cap_tris=False,
        segments=24,
        radius1=0.195,
        radius2=0.175,
        depth=0.026,
        matrix=Matrix.Translation((tc.x, tc.y, PEDESTAL_Z + 0.013)),
    )
    n_c = 24
    rings: list[list[bmesh.types.BMVert]] = []
    for r_out, z_off in (
        (0.165, PEDESTAL_Z + 0.024),
        (0.175, PEDESTAL_Z + 0.068),
        (0.182, PEDESTAL_Z + 0.095),
    ):
        ring = [
            bm_base.verts.new(
                (tc.x + r_out * math.cos(2.0 * math.pi * k / n_c), tc.y + r_out * math.sin(2.0 * math.pi * k / n_c), z_off)
            )
            for k in range(n_c)
        ]
        rings.append(ring)
    _loft_rings(bm_base, rings, cap_start=True, cap_end=False)

    _, _, n_ax = _sitar_frame()
    sup_pt = SITAR_NECK_START.lerp(SITAR_NECK_END, 0.54) - n_ax * 0.044
    bmesh.ops.create_cone(
        bm_base,
        cap_ends=True,
        cap_tris=False,
        segments=16,
        radius1=0.066,
        radius2=0.046,
        depth=0.024,
        matrix=Matrix.Translation((sup_pt.x, sup_pt.y, PEDESTAL_Z + 0.012)),
    )
    sup_h = sup_pt.z - (PEDESTAL_Z + 0.022)
    bmesh.ops.create_cone(
        bm_base,
        cap_ends=True,
        cap_tris=False,
        segments=14,
        radius1=0.019,
        radius2=0.014,
        depth=sup_h,
        matrix=Matrix.Translation((sup_pt.x, sup_pt.y, PEDESTAL_Z + 0.022 + sup_h * 0.5)),
    )
    _new_mesh_obj(col, "Sitar53_RosewoodCradle", bm_base, [mats["DarkRosewood"]], smooth=True)

    bm_gold = bmesh.new()
    bmesh.ops.create_cone(
        bm_gold,
        cap_ends=True,
        cap_tris=False,
        segments=24,
        radius1=0.178,
        radius2=0.176,
        depth=0.008,
        matrix=Matrix.Translation((tc.x, tc.y, PEDESTAL_Z + 0.028)),
    )
    bmesh.ops.create_cube(
        bm_gold,
        size=1.0,
        matrix=Matrix.Translation((sup_pt.x, sup_pt.y, sup_pt.z - 0.004)) @ Matrix.Diagonal((0.036, 0.088, 0.010, 1.0)),
    )
    for sy in (-0.040, 0.040):
        bmesh.ops.create_cube(
            bm_gold,
            size=1.0,
            matrix=Matrix.Translation((sup_pt.x, sup_pt.y + sy, sup_pt.z + 0.015)) @ Matrix.Diagonal((0.030, 0.010, 0.036, 1.0)),
        )
    _new_mesh_obj(col, "Sitar53_CradleGoldTrim", bm_gold, [mats["BrushedGold"]], smooth=True)


def _build_sitar_body_and_neck(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> tuple[Vector, dict[int, bpy.types.Object]]:
    """Build sitar gourds, surface-conforming floral ribs, dandi neck, 22 arched brass frets & carved pegs."""
    u_ax, v_ax, n_ax = _sitar_frame()
    rot_sitar = Matrix((
        (u_ax.x, v_ax.x, n_ax.x, 0.0),
        (u_ax.y, v_ax.y, n_ax.y, 0.0),
        (u_ax.z, v_ax.z, n_ax.z, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    ))
    tc = SITAR_TUMBA_CENTER

    # 1) Main carved gourd (WarmMahogany) + upper chota tumba
    bm_gourd = bmesh.new()
    bmesh.ops.create_uvsphere(
        bm_gourd,
        u_segments=28,
        v_segments=18,
        radius=0.195,
        matrix=Matrix.Translation(tc) @ rot_sitar @ Matrix.Diagonal((1.06, 0.98, 0.88, 1.0)),
    )
    u_tumba2 = SITAR_NECK_START.lerp(SITAR_NECK_END, 0.72) - n_ax * 0.120
    bmesh.ops.create_uvsphere(
        bm_gourd,
        u_segments=20,
        v_segments=14,
        radius=0.090,
        matrix=Matrix.Translation(u_tumba2) @ rot_sitar @ Matrix.Diagonal((1.02, 0.96, 0.90, 1.0)),
    )

    # Hollow dandi neck lofted from gourd shoulder to pegbox
    n_rings = 16
    n_arc = 14
    neck_rings: list[list[bmesh.types.BMVert]] = []
    for r_i in range(n_rings):
        t = r_i / float(n_rings - 1)
        c_pt = SITAR_NECK_START.lerp(SITAR_NECK_END, t)
        hw = 0.044 - 0.010 * t
        depth = 0.046 - 0.014 * t
        ring = []
        for k in range(n_arc):
            ang = 2.0 * math.pi * (k / float(n_arc))
            vy = hw * math.cos(ang)
            nz = min(0.008, depth * math.sin(ang))
            ring.append(bm_gourd.verts.new(c_pt + v_ax * vy + n_ax * nz))
        neck_rings.append(ring)
    _loft_rings(bm_gourd, neck_rings, cap_start=True, cap_end=True)

    peg_end = SITAR_NECK_END + u_ax * 0.185
    bmesh.ops.create_cube(
        bm_gourd,
        size=1.0,
        matrix=Matrix.Translation(SITAR_NECK_END.lerp(peg_end, 0.5)) @ rot_sitar @ Matrix.Diagonal((0.19, 0.056, 0.042, 1.0)),
    )
    bmesh.ops.recalc_face_normals(bm_gourd, faces=bm_gourd.faces)
    _new_mesh_obj(col, "Sitar53_MahoganyBodyNeck", bm_gourd, [mats["WarmMahogany"]], smooth=True)

    # 2) DarkRosewood surface-conforming fluted floral ribs on main gourd (zero spikes!) + tabli + pegs
    bm_rose = bmesh.new()
    rx, ry, rz = 0.195 * 1.06, 0.195 * 0.98, 0.195 * 0.88
    for rib_i in range(12):
        phi = 2.0 * math.pi * (rib_i / 12.0)
        # Skip ribs directly hidden under the flat top tabli face
        if math.sin(phi) > 0.65:
            continue
        rib_rings: list[list[bmesh.types.BMVert]] = []
        for s_i in range(9):
            theta = -0.98 + (s_i / 8.0) * 1.96  # meridian arc from back to front of gourd
            ct, st = math.cos(theta), math.sin(theta)
            # Ellipsoid surface point & local outward normal
            p_loc = Vector((rx * st, ry * ct * math.cos(phi), rz * ct * math.sin(phi)))
            n_loc = Vector((p_loc.x / (rx * rx), p_loc.y / (ry * ry), p_loc.z / (rz * rz))).normalized()
            tangent_m = Vector((rx * ct, -ry * st * math.cos(phi), -rz * st * math.sin(phi))).normalized()
            side_m = tangent_m.cross(n_loc).normalized()
            taper = math.sin(math.pi * (s_i / 8.0)) ** 0.65
            w_r = 0.008 * taper + 0.0015
            h_r = 0.005 * taper + 0.001
            ring = []
            for k in range(6):
                a_r = 2.0 * math.pi * (k / 6.0)
                pt_loc = p_loc + side_m * (w_r * math.cos(a_r)) + n_loc * (h_r * (0.3 + math.sin(a_r)))
                ring.append(bm_rose.verts.new(tc + (rot_sitar.to_3x3() @ pt_loc)))
            rib_rings.append(ring)
        _loft_rings(bm_rose, rib_rings, cap_start=True, cap_end=True)

    # Flattened carved soundboard face (tabli) seated flush into upper gourd shoulder
    bmesh.ops.create_cone(
        bm_rose,
        cap_ends=True,
        cap_tris=False,
        segments=28,
        radius1=0.156,
        radius2=0.144,
        depth=0.016,
        matrix=Matrix.Translation(tc + n_ax * 0.144) @ rot_sitar,
    )
    bmesh.ops.create_cube(
        bm_rose,
        size=1.0,
        matrix=Matrix.Translation(SITAR_NECK_START.lerp(SITAR_NECK_END, 0.5) + n_ax * 0.008)
        @ rot_sitar
        @ Matrix.Diagonal(((SITAR_NECK_END - SITAR_NECK_START).length, 0.072, 0.005, 1.0)),
    )

    rot_peg_main = rot_sitar @ Matrix.Rotation(math.pi * 0.5, 4, "X")
    for p_i in range(SITAR_NUM_MAIN_STRINGS):
        side = 1.0 if p_i % 2 == 0 else -1.0
        px = SITAR_NECK_END + u_ax * (0.03 + p_i * 0.033) + v_ax * (side * 0.068)
        bmesh.ops.create_cone(
            bm_rose,
            cap_ends=True,
            cap_tris=False,
            segments=10,
            radius1=0.0045,
            radius2=0.0065,
            depth=0.085,
            matrix=Matrix.Translation(px) @ rot_peg_main,
        )
        bmesh.ops.create_uvsphere(
            bm_rose,
            u_segments=10,
            v_segments=8,
            radius=0.013,
            matrix=Matrix.Translation(px + v_ax * (side * 0.045)) @ rot_sitar @ Matrix.Diagonal((0.7, 0.55, 1.25, 1.0)),
        )

    for t_i in range(SITAR_NUM_TARAF):
        u_p = 0.34 + (t_i / float(SITAR_NUM_TARAF - 1)) * 0.54
        p_base = SITAR_NECK_START.lerp(SITAR_NECK_END, u_p) - v_ax * 0.048 - n_ax * 0.004
        bmesh.ops.create_cone(
            bm_rose,
            cap_ends=True,
            cap_tris=False,
            segments=8,
            radius1=0.0028,
            radius2=0.0042,
            depth=0.048,
            matrix=Matrix.Translation(p_base) @ rot_peg_main,
        )
    bmesh.ops.recalc_face_normals(bm_rose, faces=bm_rose.faces)
    _new_mesh_obj(col, "Sitar53_RosewoodRibsAndPegs", bm_rose, [mats["DarkRosewood"]], smooth=True)

    # 3) IvoryKey jawari bridge aligned onto the acoustic fret plane + tailpiece + pegbox finial
    bridge_pos = tc + n_ax * 0.165 - u_ax * 0.025
    # Compute exact acoustic height at bridge so main strings skim cleanly across all 22 frets
    p_fret_ref = SITAR_NECK_START.lerp(SITAR_NECK_END, 0.5) + n_ax * 0.038
    bridge_top = p_fret_ref - u_ax * (p_fret_ref - bridge_pos).dot(u_ax)
    bridge_h = max(0.024, (bridge_top - bridge_pos).dot(n_ax))

    bm_ivory = bmesh.new()
    bmesh.ops.create_cube(
        bm_ivory,
        size=1.0,
        matrix=Matrix.Translation(bridge_pos + n_ax * (bridge_h * 0.5))
        @ rot_sitar
        @ Matrix.Diagonal((0.022, 0.068, bridge_h, 1.0)),
    )
    bmesh.ops.create_uvsphere(
        bm_ivory,
        u_segments=12,
        v_segments=10,
        radius=0.022,
        matrix=Matrix.Translation(tc - u_ax * 0.205) @ rot_sitar @ Matrix.Diagonal((1.4, 0.85, 0.85, 1.0)),
    )
    bmesh.ops.create_uvsphere(
        bm_ivory,
        u_segments=12,
        v_segments=10,
        radius=0.020,
        matrix=Matrix.Translation(peg_end + u_ax * 0.015) @ rot_sitar @ Matrix.Diagonal((1.6, 0.9, 0.9, 1.0)),
    )
    _new_mesh_obj(col, "Sitar53_IvoryBridgeAndFinials", bm_ivory, [mats["IvoryKey"]], smooth=True)

    # 4) 22 arched scalloped PolishedBrass frets + 22 luminous fret-crown jewels (dark slate idle -> vivid jewel)
    bm_frets = bmesh.new()
    fret_glows: dict[int, bpy.types.Object] = {}
    lum_mat = mats["LuminousElement"]

    for f_i in range(SITAR_NUM_FRETS):
        u_f = _fret_u(f_i)
        c_pt = SITAR_NECK_START.lerp(SITAR_NECK_END, u_f) + n_ax * 0.012
        hw = (0.044 - 0.010 * u_f) * 1.04
        arch_segs = 9
        arch_rings: list[list[bmesh.types.BMVert]] = []
        for a_i in range(arch_segs):
            s = -1.0 + 2.0 * (a_i / float(arch_segs - 1))
            pt_mid = c_pt + v_ax * (s * hw) + n_ax * (0.018 * (1.0 - s * s) + 0.008)
            r_pts = [
                pt_mid - u_ax * 0.0024 - n_ax * 0.0020,
                pt_mid + u_ax * 0.0024 - n_ax * 0.0020,
                pt_mid + u_ax * 0.0018 + n_ax * 0.0025,
                pt_mid - u_ax * 0.0018 + n_ax * 0.0025,
            ]
            arch_rings.append([bm_frets.verts.new(p) for p in r_pts])
        _loft_rings(bm_frets, arch_rings, cap_start=True, cap_end=True)

        bm_jewel = bmesh.new()
        bmesh.ops.create_cube(
            bm_jewel,
            size=1.0,
            matrix=Matrix.Translation(c_pt + n_ax * 0.027) @ rot_sitar @ Matrix.Diagonal((0.0052, 0.028, 0.0038, 1.0)),
        )
        j_obj = _new_mesh_obj(col, f"Sitar53_FretGlow_{f_i:02d}", bm_jewel, [lum_mat], smooth=False)
        j_obj.color = (0.08, 0.06, 0.04, 0.03)
        fret_glows[f_i] = j_obj

    bmesh.ops.recalc_face_normals(bm_frets, faces=bm_frets.faces)
    _new_mesh_obj(col, "Sitar53_ArchedBrassFrets", bm_frets, [mats["PolishedBrass"]], smooth=True)
    return bridge_top, fret_glows


def _build_sitar_strings(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
    bridge_top: Vector,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build 5 main upper strings (with bold Meend + Pluck shape keys) and 13 taraf sympathetic strings."""
    u_ax, v_ax, n_ax = _sitar_frame()
    lum_mat = mats["LuminousElement"]
    main_strings: list[dict[str, Any]] = []
    n_rings = 28
    n_sides = 8

    for s_i in range(SITAR_NUM_MAIN_STRINGS):
        frac = s_i / float(SITAR_NUM_MAIN_STRINGS - 1)
        vy = 0.022 - frac * 0.044
        p_br = bridge_top + v_ax * vy
        p_peg = SITAR_NECK_END + u_ax * (0.03 + s_i * 0.030) + n_ax * 0.036 + v_ax * (vy * 0.72)

        bm = bmesh.new()
        rings: list[list[bmesh.types.BMVert]] = []
        ts_arr: list[float] = []
        radius = 0.00175 if s_i == 0 else 0.00105
        for r_i in range(n_rings):
            t = r_i / float(n_rings - 1)
            c_pt = p_br.lerp(p_peg, t)
            tan = (p_peg - p_br).normalized()
            side_b = tan.cross(n_ax).normalized()
            up_b = side_b.cross(tan).normalized()
            ring = []
            for k in range(n_sides):
                ang = 2.0 * math.pi * (k / float(n_sides))
                ring.append(bm.verts.new(c_pt + side_b * (radius * math.cos(ang)) + up_b * (radius * math.sin(ang))))
            rings.append(ring)
            ts_arr.append(t)
        _loft_rings(bm, rings, cap_start=True, cap_end=True)

        obj = _new_mesh_obj(col, f"Sitar53_MainString_{s_i}", bm, [lum_mat], smooth=True)
        idle_rgb = (0.78, 0.74, 0.64) if s_i < 3 else (0.74, 0.48, 0.24)
        obj.color = (idle_rgb[0], idle_rgb[1], idle_rgb[2], 0.04)

        obj.shape_key_add(name="Basis", from_mix=False)
        kb_meend = obj.shape_key_add(name="Meend", from_mix=False)
        kb_meend.slider_min = -1.6
        kb_meend.slider_max = 1.6
        kb_meend.value = 0.0

        kb_pluck = obj.shape_key_add(name="Pluck", from_mix=False)
        kb_pluck.slider_min = -1.5
        kb_pluck.slider_max = 1.5
        kb_pluck.value = 0.0

        for v_i, vert in enumerate(obj.data.vertices):
            t = ts_arr[v_i // n_sides]
            # Bold dramatic lateral meend sweep across the curved brass frets (visible from front 3/4 camera)
            env_m = math.sin(math.pi * max(0.0, min(1.0, (t - 0.14) / 0.76))) ** 1.1 if 0.14 <= t <= 0.90 else 0.0
            kb_meend.data[v_i].co = vert.co - v_ax * (0.066 * env_m) + n_ax * (0.018 * env_m)
            kb_pluck.data[v_i].co = vert.co + (v_ax * 0.008 + n_ax * 0.006) * math.sin(math.pi * t)

        main_strings.append({"obj": obj, "kb_meend": kb_meend, "kb_pluck": kb_pluck, "idle_rgb": idle_rgb})

    # 13 sympathetic taraf strings under the arched frets (warm brass idle -> vivid color on resonance)
    taraf_strings: list[dict[str, Any]] = []
    taraf_idle_rgb = (0.52, 0.42, 0.22)
    for t_i, t_step in enumerate(TARAF_STEPS):
        frac = t_i / float(SITAR_NUM_TARAF - 1)
        vy = 0.028 - frac * 0.056
        u_peg = 0.34 + frac * 0.54
        p_br = bridge_top - n_ax * 0.014 + v_ax * (vy * 0.65)
        p_peg = SITAR_NECK_START.lerp(SITAR_NECK_END, u_peg) - v_ax * 0.036 + n_ax * 0.013

        bm = bmesh.new()
        rings = []
        ts_t = []
        radius = 0.00078
        for r_i in range(12):
            t = r_i / 11.0
            c_pt = p_br.lerp(p_peg, t)
            tan = (p_peg - p_br).normalized()
            side_b = tan.cross(n_ax).normalized()
            up_b = side_b.cross(tan).normalized()
            ring = []
            for k in range(6):
                ang = 2.0 * math.pi * (k / 6.0)
                ring.append(bm.verts.new(c_pt + side_b * (radius * math.cos(ang)) + up_b * (radius * math.sin(ang))))
            rings.append(ring)
            ts_t.append(t)
        _loft_rings(bm, rings, cap_start=True, cap_end=True)

        obj = _new_mesh_obj(col, f"Sitar53_TarafString_{t_i:02d}", bm, [lum_mat], smooth=True)
        rgb = common.vivid_53edo_color(t_step)
        obj.color = (*taraf_idle_rgb, 0.03)

        obj.shape_key_add(name="Basis", from_mix=False)
        kb = obj.shape_key_add(name="Sympathy", from_mix=False)
        kb.slider_min = -1.5
        kb.slider_max = 1.5
        kb.value = 0.0
        for v_i, vert in enumerate(obj.data.vertices):
            t = ts_t[v_i // 6]
            kb.data[v_i].co = vert.co + n_ax * (0.004 * math.sin(math.pi * t))

        taraf_strings.append({"obj": obj, "kb": kb, "step": t_step, "rgb": rgb, "idle_rgb": taraf_idle_rgb})

    return main_strings, taraf_strings


def _build_ektara(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    """Build upright Gourd Ektara Monochord seated flush at z=PEDESTAL_Z (0.09)."""
    bx, by, _ = EKTARA_BASE_XY
    bm_stand = bmesh.new()
    bmesh.ops.create_cone(
        bm_stand,
        cap_ends=True,
        cap_tris=False,
        segments=24,
        radius1=0.112,
        radius2=0.096,
        depth=0.022,
        matrix=Matrix.Translation((bx, by, PEDESTAL_Z + 0.011)),
    )
    _new_mesh_obj(col, "Ektara_StandRing", bm_stand, [mats["DarkRosewood"]], smooth=True)

    gourd_center = Vector((bx, by, PEDESTAL_Z + 0.110))
    bm_gourd = bmesh.new()
    n_u, n_seg = 14, 24
    g_rings: list[list[bmesh.types.BMVert]] = []
    for i in range(n_u):
        t = i / float(n_u - 1)
        z_g = gourd_center.z - 0.092 + t * 0.184
        rad = 0.038 + 0.084 * math.sin(math.pi * (0.12 + 0.76 * t))
        if i == n_u - 1:
            rad = 0.088
        ring = [
            bm_gourd.verts.new((bx + rad * math.cos(2.0 * math.pi * k / n_seg), by + rad * math.sin(2.0 * math.pi * k / n_seg), z_g))
            for k in range(n_seg)
        ]
        g_rings.append(ring)
    _loft_rings(bm_gourd, g_rings, cap_start=True, cap_end=False)
    _new_mesh_obj(col, "Ektara_GourdBody", bm_gourd, [mats["WarmMahogany"]], smooth=True)

    skin_z = gourd_center.z + 0.092
    bm_skin = bmesh.new()
    bmesh.ops.create_cone(
        bm_skin,
        cap_ends=True,
        cap_tris=False,
        segments=24,
        radius1=0.090,
        radius2=0.088,
        depth=0.008,
        matrix=Matrix.Translation((bx, by, skin_z)),
    )
    _new_mesh_obj(col, "Ektara_CalfskinHead", bm_skin, [mats["CalfskinHead"]], smooth=True)

    bm_fork = bmesh.new()
    top_z = PEDESTAL_Z + 0.74
    for side in (-1.0, 1.0):
        f_rings: list[list[bmesh.types.BMVert]] = []
        for i in range(10):
            t = i / 9.0
            z_f = gourd_center.z + t * (top_z - gourd_center.z)
            x_off = side * (0.110 * ((1.0 - t) ** 1.15) + 0.014 * t)
            ring = [
                bm_fork.verts.new((bx + x_off + 0.0085 * math.cos(2.0 * math.pi * k / 8.0), by + 0.012 * math.sin(2.0 * math.pi * k / 8.0), z_f))
                for k in range(8)
            ]
            f_rings.append(ring)
        _loft_rings(bm_fork, f_rings, cap_start=True, cap_end=True)
    _new_mesh_obj(col, "Ektara_SplitBambooFork", bm_fork, [mats["AntiqueSpruce"]], smooth=True)

    bm_brass = bmesh.new()
    bmesh.ops.create_cone(
        bm_brass,
        cap_ends=True,
        cap_tris=False,
        segments=24,
        radius1=0.093,
        radius2=0.092,
        depth=0.012,
        matrix=Matrix.Translation((bx, by, skin_z - 0.004)),
    )
    for z_band in (top_z - 0.048, top_z - 0.005):
        bmesh.ops.create_cone(
            bm_brass,
            cap_ends=True,
            cap_tris=False,
            segments=16,
            radius1=0.026,
            radius2=0.024,
            depth=0.013,
            matrix=Matrix.Translation((bx, by, z_band)),
        )
    bmesh.ops.create_cone(
        bm_brass,
        cap_ends=True,
        cap_tris=False,
        segments=10,
        radius1=0.0045,
        radius2=0.0045,
        depth=0.088,
        matrix=Matrix.Translation((bx + 0.022, by, top_z + 0.020)) @ Matrix.Rotation(math.pi * 0.5, 4, "Y"),
    )
    _new_mesh_obj(col, "Ektara_BrassHardware", bm_brass, [mats["PolishedBrass"]], smooth=True)

    bm_cap = bmesh.new()
    bmesh.ops.create_cube(
        bm_cap,
        size=1.0,
        matrix=Matrix.Translation((bx, by, top_z + 0.020)) @ Matrix.Diagonal((0.046, 0.034, 0.062, 1.0)),
    )
    _new_mesh_obj(col, "Ektara_TopPeghead", bm_cap, [mats["DarkRosewood"]], smooth=False)

    bm_str = bmesh.new()
    p_bot = Vector((bx, by, skin_z + 0.005))
    p_top = Vector((bx, by, top_z + 0.018))
    n_rings_s = 16
    s_rings: list[list[bmesh.types.BMVert]] = []
    ts_e: list[float] = []
    for r_i in range(n_rings_s):
        t = r_i / float(n_rings_s - 1)
        pt = p_bot.lerp(p_top, t)
        ring = [
            bm_str.verts.new((pt.x + 0.0016 * math.cos(2.0 * math.pi * k / 8.0), pt.y + 0.0016 * math.sin(2.0 * math.pi * k / 8.0), pt.z))
            for k in range(8)
        ]
        s_rings.append(ring)
        ts_e.append(t)
    _loft_rings(bm_str, s_rings, cap_start=True, cap_end=True)

    str_obj = _new_mesh_obj(col, "Ektara_MonochordString", bm_str, [mats["LuminousElement"]], smooth=True)
    str_obj.color = (0.78, 0.52, 0.20, 0.05)

    str_obj.shape_key_add(name="Basis", from_mix=False)
    kb_e = str_obj.shape_key_add(name="Pluck", from_mix=False)
    kb_e.slider_min = -1.5
    kb_e.slider_max = 1.5
    kb_e.value = 0.0
    for v_i, vert in enumerate(str_obj.data.vertices):
        t = ts_e[v_i // 8]
        kb_e.data[v_i].co = vert.co + Vector((0.011, 0.007, 0.0)) * math.sin(math.pi * t)

    return {"obj": str_obj, "kb": kb_e, "idle_rgb": (0.78, 0.52, 0.20)}


def _closest_fret_index(step: int) -> int:
    folded = common.fold_step_to_range(step, 0, 53)
    return min(range(SITAR_NUM_FRETS), key=lambda i: abs(SHRUTI_22_STEPS[i] - folded))


def _animate_sitar_and_ektara(
    timeline: dict[str, Any],
    fret_glows: dict[int, bpy.types.Object],
    main_strings: list[dict[str, Any]],
    taraf_strings: list[dict[str, Any]],
    ektara: dict[str, Any],
) -> None:
    """Keyframe meend string bends, taraf sympathetic shimmer, fret glows, and ektara drone."""
    fps = int(timeline["fps"])
    total_frames = int(timeline["total_frames"])

    sitar_notes = [n for n in timeline.get("notes", []) if n.get("instrument") == "sitar" or n.get("track_id") == "sitar"]
    ektara_notes = [n for n in timeline.get("notes", []) if n.get("instrument") == "ektara" or n.get("track_id") == "ektara"]
    if not sitar_notes and not ektara_notes:
        sitar_notes = list(timeline.get("notes", []))

    # 1) Main sitar melody string (baaj) with bold meend deflection
    baaj = main_strings[0]
    b_obj = baaj["obj"]
    kb_m = baaj["kb_meend"]
    kb_p = baaj["kb_pluck"]
    b_idle = baaj["idle_rgb"]

    b_obj.color = (*b_idle, 0.04)
    b_obj.keyframe_insert(data_path="color", frame=1)
    kb_m.value = 0.0
    kb_m.keyframe_insert(data_path="value", frame=1)
    kb_p.value = 0.0
    kb_p.keyframe_insert(data_path="value", frame=1)

    const_b: set[int] = {1}
    for i, ev in enumerate(sitar_notes):
        f0 = common.sec_to_frame(ev["start_s"], fps)
        dur_s = float(ev["dur_s"])
        f1 = min(total_frames, max(f0 + 4, common.sec_to_frame(ev["end_s"], fps)))
        next_f0 = common.sec_to_frame(sitar_notes[i + 1]["start_s"], fps) if i + 1 < len(sitar_notes) else total_frames + 10
        rgb = common.vivid_53edo_color(int(ev["step"]))

        if f0 > 2:
            b_obj.color = (*b_idle, 0.04)
            b_obj.keyframe_insert(data_path="color", frame=f0 - 1)
            const_b.add(f0 - 1)
            kb_m.value = 0.0
            kb_m.keyframe_insert(data_path="value", frame=f0 - 1)
            kb_p.value = 0.0
            kb_p.keyframe_insert(data_path="value", frame=f0 - 1)

        peak_a = min(1.0, 0.92 + 0.10 * float(ev.get("vel", 0.8)))
        b_obj.color = (*rgb, peak_a)
        b_obj.keyframe_insert(data_path="color", frame=f0)

        clip_end = min(f1, next_f0 - 2)
        for f in range(f0 + 2, clip_end + 1, 2):
            u = min(1.0, ((f - 1) / float(fps) - ev["start_s"]) / max(0.08, dur_s))
            a_val = 0.04 + (peak_a - 0.04) * max(0.0, 1.0 - (u ** 2.4))
            b_obj.color = (*rgb, a_val)
            b_obj.keyframe_insert(data_path="color", frame=f)

        slide = float(ev.get("slide_from_cents", 0.0))
        if abs(slide) > 0.1:
            sign = 1.0 if slide < 0 else -0.85
            amp_m = sign * min(1.55, max(1.05, abs(slide) / 36.0))
            for f in range(f0, clip_end + 1):
                u = min(1.0, ((f - 1) / float(fps) - ev["start_s"]) / max(0.08, dur_s))
                arch = math.sin(math.pi * (0.18 + 0.62 * min(u, 0.92))) ** 0.55
                vib = 1.0 + 0.07 * math.sin(2.0 * math.pi * 4.0 * u)
                kb_m.value = amp_m * arch * vib
                kb_m.keyframe_insert(data_path="value", frame=f)
        else:
            kb_m.value = 0.0
            kb_m.keyframe_insert(data_path="value", frame=f0)

        vib_end = min(f0 + min(26, max(8, int(round(dur_s * fps)))), clip_end)
        for k in range(vib_end - f0 + 1):
            kb_p.value = (1.0 if k % 2 == 0 else -1.0) * 0.95 * math.exp(-0.11 * k)
            kb_p.keyframe_insert(data_path="value", frame=f0 + k)

        if clip_end + 1 < next_f0 and clip_end + 1 <= total_frames:
            b_obj.color = (*b_idle, 0.04)
            b_obj.keyframe_insert(data_path="color", frame=clip_end + 1)
            const_b.add(clip_end + 1)
            kb_m.value = 0.0
            kb_m.keyframe_insert(data_path="value", frame=clip_end + 1)
            kb_p.value = 0.0
            kb_p.keyframe_insert(data_path="value", frame=clip_end + 1)

    for idx_ch in range(4):
        common.set_constant_segment(b_obj, "color", idx_ch, const_b)

    for s_i, sinfo in enumerate(main_strings[1:], start=1):
        sobj = sinfo["obj"]
        sidle = sinfo["idle_rgb"]
        sobj.color = (*sidle, 0.04)
        sobj.keyframe_insert(data_path="color", frame=1)
        const_s: set[int] = {1}
        for ev in sitar_notes:
            if s_i == 4 or (int(ev["step"]) % 53 in (0, 31, 53)):
                f0 = common.sec_to_frame(ev["start_s"], fps)
                f1 = min(total_frames, common.sec_to_frame(ev["end_s"], fps))
                if f0 > 2:
                    sobj.color = (*sidle, 0.04)
                    sobj.keyframe_insert(data_path="color", frame=f0 - 1)
                    const_s.add(f0 - 1)
                sobj.color = (1.0, 0.82, 0.34, 0.45)
                sobj.keyframe_insert(data_path="color", frame=f0)
                if f1 + 1 <= total_frames:
                    sobj.color = (*sidle, 0.04)
                    sobj.keyframe_insert(data_path="color", frame=f1 + 1)
                    const_s.add(f1 + 1)
        for idx_ch in range(4):
            common.set_constant_segment(sobj, "color", idx_ch, const_s)

    # 2) 22 Arched Fret Jewel Markers
    notes_by_fret: dict[int, list[dict[str, Any]]] = {fi: [] for fi in range(SITAR_NUM_FRETS)}
    for ev in sitar_notes:
        notes_by_fret[_closest_fret_index(int(ev["step"]))].append(ev)

    for f_i, f_obj in fret_glows.items():
        evts = notes_by_fret[f_i]
        idle_f_rgb = (0.08, 0.06, 0.04)
        f_obj.color = (*idle_f_rgb, 0.03)
        f_obj.keyframe_insert(data_path="color", frame=1)
        if not evts:
            continue
        rgb_f = common.vivid_53edo_color(SHRUTI_22_STEPS[f_i])
        const_f: set[int] = {1}
        for i, ev in enumerate(evts):
            f0 = common.sec_to_frame(ev["start_s"], fps)
            f1 = min(total_frames, common.sec_to_frame(ev["end_s"], fps))
            next_f0 = common.sec_to_frame(evts[i + 1]["start_s"], fps) if i + 1 < len(evts) else total_frames + 10
            if f0 > 2:
                f_obj.color = (*idle_f_rgb, 0.03)
                f_obj.keyframe_insert(data_path="color", frame=f0 - 1)
                const_f.add(f0 - 1)
            f_obj.color = (*rgb_f, 1.0)
            f_obj.keyframe_insert(data_path="color", frame=f0)
            clip_end = min(f1, next_f0 - 2)
            if clip_end > f0:
                f_obj.color = (*rgb_f, 0.85)
                f_obj.keyframe_insert(data_path="color", frame=clip_end)
            if clip_end + 1 < next_f0 and clip_end + 1 <= total_frames:
                f_obj.color = (*idle_f_rgb, 0.03)
                f_obj.keyframe_insert(data_path="color", frame=clip_end + 1)
                const_f.add(clip_end + 1)
        for ch in range(4):
            common.set_constant_segment(f_obj, "color", ch, const_f)

    # 3) 13 Taraf sympathetic strings (dark bronze idle -> vivid jewel shimmer when sympathetic!)
    for tinfo in taraf_strings:
        tobj = tinfo["obj"]
        tkb = tinfo["kb"]
        t_step = tinfo["step"]
        t_rgb = tinfo["rgb"]
        t_idle = tinfo["idle_rgb"]
        tobj.color = (*t_idle, 0.03)
        tobj.keyframe_insert(data_path="color", frame=1)
        tkb.value = 0.0
        tkb.keyframe_insert(data_path="value", frame=1)
        const_t: set[int] = {1}

        for ev in sitar_notes:
            pc = int(ev["step"]) % 53
            diff = min(abs(t_step - pc), 53 - abs(t_step - pc))
            if diff <= 1:
                peak_sym = 0.98
            elif abs((t_step - pc) % 53 - 31) <= 1 or abs((t_step - pc) % 53 - 22) <= 1:
                peak_sym = 0.55
            else:
                continue
            f0 = common.sec_to_frame(ev["start_s"], fps) + 1
            f1 = min(total_frames, common.sec_to_frame(ev["end_s"], fps) + 2)
            if f0 > 2:
                tobj.color = (*t_idle, 0.03)
                tobj.keyframe_insert(data_path="color", frame=f0 - 1)
                const_t.add(f0 - 1)
            tobj.color = (*t_rgb, peak_sym)
            tobj.keyframe_insert(data_path="color", frame=f0 + 1)
            if f1 > f0 + 1:
                tobj.color = (*t_rgb, peak_sym * 0.85)
                tobj.keyframe_insert(data_path="color", frame=f1)
            for k in range(min(22, max(4, f1 - f0))):
                tkb.value = (0.9 if k % 2 == 0 else -0.9) * peak_sym * math.exp(-0.08 * k)
                tkb.keyframe_insert(data_path="value", frame=f0 + k)
            if f1 + 1 <= total_frames:
                tobj.color = (*t_idle, 0.03)
                tobj.keyframe_insert(data_path="color", frame=f1 + 1)
                const_t.add(f1 + 1)
                tkb.value = 0.0
                tkb.keyframe_insert(data_path="value", frame=f1 + 1)

        for ch in range(4):
            common.set_constant_segment(tobj, "color", ch, const_t)

    # 4) Ektara vertical monochord string pulsing on ektara track notes
    e_obj = ektara["obj"]
    e_kb = ektara["kb"]
    e_idle = ektara["idle_rgb"]
    e_obj.color = (*e_idle, 0.05)
    e_obj.keyframe_insert(data_path="color", frame=1)
    e_kb.value = 0.0
    e_kb.keyframe_insert(data_path="value", frame=1)
    const_e: set[int] = {1}

    for i, ev in enumerate(ektara_notes):
        f0 = common.sec_to_frame(ev["start_s"], fps)
        f1 = min(total_frames, max(f0 + 3, common.sec_to_frame(ev["end_s"], fps)))
        next_f0 = common.sec_to_frame(ektara_notes[i + 1]["start_s"], fps) if i + 1 < len(ektara_notes) else total_frames + 10
        rgb = common.vivid_53edo_color(int(ev["step"]))

        if f0 > 2:
            e_obj.color = (*e_idle, 0.05)
            e_obj.keyframe_insert(data_path="color", frame=f0 - 1)
            const_e.add(f0 - 1)
            e_kb.value = 0.0
            e_kb.keyframe_insert(data_path="value", frame=f0 - 1)

        peak_a = min(1.0, 0.88 + 0.14 * float(ev.get("vel", 0.7)))
        e_obj.color = (*rgb, peak_a)
        e_obj.keyframe_insert(data_path="color", frame=f0)

        clip_end = min(f1, next_f0 - 2)
        for f in range(f0 + 2, clip_end + 1, 2):
            u = min(1.0, ((f - 1) / float(fps) - ev["start_s"]) / max(0.08, float(ev["dur_s"])))
            e_obj.color = (*rgb, 0.05 + (peak_a - 0.05) * max(0.0, 1.0 - (u ** 2.1)))
            e_obj.keyframe_insert(data_path="color", frame=f)

        for k in range(min(14, max(4, clip_end - f0 + 1))):
            e_kb.value = (1.0 if k % 2 == 0 else -1.0) * 0.9 * math.exp(-0.14 * k)
            e_kb.keyframe_insert(data_path="value", frame=f0 + k)

        if clip_end + 1 < next_f0 and clip_end + 1 <= total_frames:
            e_obj.color = (*e_idle, 0.05)
            e_obj.keyframe_insert(data_path="color", frame=clip_end + 1)
            const_e.add(clip_end + 1)
            e_kb.value = 0.0
            e_kb.keyframe_insert(data_path="value", frame=clip_end + 1)

    for idx_ch in range(4):
        common.set_constant_segment(e_obj, "color", idx_ch, const_e)


def build_instrument(
    mats: dict[str, bpy.types.Material],
    timeline: dict[str, Any],
    *,
    collection_name: str = "SitarShruti53EDO",
    anchor_location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    anchor_rotation_z_deg: float = 0.0,
    anchor_scale: float = 1.0,
) -> bpy.types.Object:
    """Build and animate the 22-Shruti Sitar & Gourd Ektara inside collection_name."""
    col = bpy.data.collections.new(collection_name)
    bpy.context.scene.collection.children.link(col)

    _build_sitar_cradle(col, mats)
    bridge_top, fret_glows = _build_sitar_body_and_neck(col, mats)
    main_strings, taraf_strings = _build_sitar_strings(col, mats, bridge_top)
    ektara = _build_ektara(col, mats)

    folded_notes = []
    for n in timeline.get("notes", []):
        st = int(n["step"])
        is_ek = n.get("instrument") == "ektara" or n.get("track_id") == "ektara"
        st_f = common.fold_step_to_range(st, -53, -1) if is_ek else common.fold_step_to_range(st, 0, 53)
        folded_notes.append({**n, "step": st_f})

    _animate_sitar_and_ektara(
        {**timeline, "notes": folded_notes},
        fret_glows,
        main_strings,
        taraf_strings,
        ektara,
    )
    return common.parent_collection_to_anchor(
        col,
        f"{collection_name}_Anchor",
        location=anchor_location,
        rotation_z_deg=anchor_rotation_z_deg,
        scale=anchor_scale,
    )


def build_scene() -> dict[str, Any]:
    """Assemble the standalone 05_shruti_sitar_53edo showcase scene."""
    scene = common.reset_scene(fps=24, res_x=1920, res_y=1080, taa_samples=8)
    scene.view_settings.exposure = -0.34
    mats = common.create_studio_materials()

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
    build_instrument(mats, timeline, collection_name="SitarShruti53EDO")

    total_frames = int(timeline["total_frames"])
    cam_keyframes = [
        (1, (0.50, -2.26, 0.96)),
        (max(2, round(total_frames * 0.48)), (0.22, -2.14, 1.02)),
        (total_frames, (0.64, -2.20, 0.92)),
    ]
    common.setup_orbit_camera(
        target_pos=(0.08, -0.06, 0.48),
        keyframes_cam_loc=cam_keyframes,
        lens_mm=36.0,
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
            ("meend", common.sec_to_frame(4.0, 24)),
            ("ragaclimax", common.sec_to_frame(9.2, 24)),
        ]
        rendered = common.render_diagnostic_stills(frame_specs, OUT_DIR, "diag_sitar")
        for p in rendered:
            print(f"[sitar_shruti_53edo] Diagnostic still: {p}")

    if render_vid:
        common.render_video(WEBM_PATH, WAV_PATH, int(timeline["total_frames"]), TMP_FRAMES_DIR, fps=24)


if __name__ == "__main__":
    main()
