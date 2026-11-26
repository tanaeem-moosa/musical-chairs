"""The Sympathetic 53-EDO Concert Viol (Cello) & Viola with Floating Bow — Blender 4.2 EEVEE Next."""

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

SCORE_PATH = REPO_ROOT / "scores" / "showcase_3d" / "04_viol_53edo.json"
WAV_PATH = REPO_ROOT / "output" / "showcase_3d" / "04_viol_53edo.wav"
OUT_DIR = REPO_ROOT / "output" / "showcase_3d"
BLEND_PATH = OUT_DIR / "04_viol_53edo.blend"
WEBM_PATH = OUT_DIR / "04_viol_53edo.webm"
TMP_FRAMES_DIR = Path("/tmp/frames_viol_53edo")

PEDESTAL_Z = 0.09
CELLO_STEP_MIN = -53
CELLO_STEP_MAX = 17
VIOLA_STEP_MIN = -26
VIOLA_STEP_MAX = 36


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


def _add_bevel(obj: bpy.types.Object, width: float = 0.0025, segments: int = 2) -> None:
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
    n_sides: int = 12,
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
    n_sides: int = 14,
    mat_idx: int = 0,
) -> None:
    _add_tube_along_points(bm, [p0, p1], [r0, r1], n_sides=n_sides, mat_idx=mat_idx)


# ---------------------------------------------------------------------------
# Analytic violin/viol figure-eight profile (right half x(u) >= 0, u in [-1, 1])
# ---------------------------------------------------------------------------

def _viol_half_width(u: float) -> float:
    """Return normalized half-width (in units of body_len) for u in [-1, 1] (-1=tail, +1=neck)."""
    # Classic Stradivarius figure-8: broad rounded lower bout (u~-0.58), pinched C-waist (u~0.06), rounded upper bout (u~0.58)
    u_c = max(-1.0, min(1.0, u))
    base = (max(0.0, 1.0 - abs(u_c) ** 2.6)) ** 0.46
    lower_lobe = 0.075 * math.exp(-((u_c + 0.56) / 0.36) ** 2)
    upper_lobe = 0.015 * math.exp(-((u_c - 0.58) / 0.32) ** 2)
    c_waist = -0.168 * math.exp(-((u_c - 0.06) / 0.20) ** 2)
    w = base * (0.315 + lower_lobe + upper_lobe + c_waist)
    return max(0.006, w)


def _viol_outline_xz(body_len: float, n_half: int = 44) -> list[tuple[float, float]]:
    """Return CCW 2D outline (x, z_rel) centered vertically at z_rel in [-body_len/2, +body_len/2]."""
    pts: list[tuple[float, float]] = []
    # Right side from bottom (-1) to top (+1)
    for i in range(n_half + 1):
        # Cosine spacing gives crisp roundings at top & bottom bouts
        theta = -0.5 * math.pi + math.pi * (i / float(n_half))
        u = math.sin(theta)
        w = _viol_half_width(u) * body_len
        z = u * (body_len * 0.5)
        pts.append((w, z))
    # Left side from top (+1) back to bottom (-1), skipping endpoints to avoid duplicates
    for i in range(n_half - 1, 0, -1):
        theta = -0.5 * math.pi + math.pi * (i / float(n_half))
        u = math.sin(theta)
        w = _viol_half_width(u) * body_len
        z = u * (body_len * 0.5)
        pts.append((-w, z))
    return pts


def _arch_height(x: float, z_rel: float, body_len: float, arch_max: float) -> float:
    """Compute smooth archtop dome elevation along -Y (front face) for (x, z_rel)."""
    u = max(-1.0, min(1.0, z_rel / (body_len * 0.5)))
    hw = max(0.005, _viol_half_width(u) * body_len)
    nx = min(1.0, abs(x) / hw)
    nz = abs(u)
    dome_x = max(0.0, 1.0 - nx * nx)
    dome_z = max(0.0, 1.0 - nz * nz)
    return arch_max * (dome_x ** 1.25) * (dome_z ** 0.85)


def _build_viol_body_mesh(
    col: bpy.types.Collection,
    name_prefix: str,
    body_len: float,
    rib_depth: float,
    arch_front: float,
    arch_back: float,
    mats: dict[str, bpy.types.Material],
    parent: bpy.types.Object,
) -> bpy.types.Object:
    """Build sculpted figure-eight body: WarmMahogany back/ribs + AntiqueSpruce archtop + dark f-holes."""
    outline = _viol_outline_xz(body_len, n_half=42)
    n_pts = len(outline)

    # 1) Back plate + Ribs (WarmMahogany = slot 0) + Spruce Rim Binding (slot 1)
    bm_ribs = bmesh.new()
    y_back = rib_depth * 0.5
    y_front = -rib_depth * 0.5

    # Build layered perimeter rings from back arch center -> back edge -> front edge
    ring_back_edge = [bm_ribs.verts.new((x, y_back, z)) for (x, z) in outline]
    ring_back_mid = [
        bm_ribs.verts.new((x * 0.62, y_back + _arch_height(x * 0.62, z * 0.62, body_len, arch_back) * 0.72, z * 0.76))
        for (x, z) in outline
    ]
    ring_back_inner = [
        bm_ribs.verts.new((x * 0.22, y_back + _arch_height(x * 0.22, z * 0.22, body_len, arch_back), z * 0.35))
        for (x, z) in outline
    ]
    ring_front_edge = [bm_ribs.verts.new((x, y_front, z)) for (x, z) in outline]
    # Overhang rim lip (+2.5mm outward) for authentic violin edge purfling
    lip_scale = 1.022
    ring_back_lip = [bm_ribs.verts.new((x * lip_scale, y_back - 0.002, z * 1.008)) for (x, z) in outline]
    ring_front_lip = [bm_ribs.verts.new((x * lip_scale, y_front + 0.002, z * 1.008)) for (x, z) in outline]

    # Ribs + overhanging edges
    _loft_rings(bm_ribs, [ring_front_lip, ring_front_edge, ring_back_edge, ring_back_lip], cap_start=False, cap_end=False, mat_idx=0)
    # Back arched dome
    _loft_rings(bm_ribs, [ring_back_lip, ring_back_mid, ring_back_inner], cap_start=False, cap_end=True, mat_idx=0)

    bmesh.ops.recalc_face_normals(bm_ribs, faces=bm_ribs.faces)
    body_obj = _make_mesh_obj(col, f"{name_prefix}_BackRibs", bm_ribs, [mats["WarmMahogany"]], smooth=True)
    body_obj.parent = parent

    # 2) Archtop Spruce Belly (AntiqueSpruce)
    bm_top = bmesh.new()
    top_rings: list[list[bmesh.types.BMVert]] = []
    scales = [(1.022, 1.008), (0.94, 0.96), (0.74, 0.80), (0.48, 0.56), (0.20, 0.28)]
    for sx, sz in scales:
        r = []
        for (x, z) in outline:
            px, pz = x * sx, z * sz
            arch_y = _arch_height(px, pz, body_len, arch_front)
            r.append(bm_top.verts.new((px, y_front - arch_y, pz)))
        top_rings.append(r)

    _loft_rings(bm_top, top_rings, cap_start=False, cap_end=True, mat_idx=0)
    # Close inner underside lip so belly looks solid from oblique angles
    inner_lip = [bm_top.verts.new((x * 0.98, y_front + 0.004, z * 0.99)) for (x, z) in outline]
    _loft_rings(bm_top, [inner_lip, top_rings[0]], cap_start=False, cap_end=False, mat_idx=0)
    bmesh.ops.recalc_face_normals(bm_top, faces=bm_top.faces)
    top_obj = _make_mesh_obj(col, f"{name_prefix}_SpruceBelly", bm_top, [mats["AntiqueSpruce"]], smooth=True)
    top_obj.parent = parent

    # 3) Purfling pinstripe inlaid near belly perimeter + sculpted dark F-holes
    bm_fh = bmesh.new()
    for side in (-1.0, 1.0):
        # S-shaped f-hole curve lying cleanly just above the spruce arch (-0.0015 offset)
        n_f = 18
        pts_fh: list[Vector] = []
        radii_fh: list[float] = []
        for k in range(n_f + 1):
            t = k / float(n_f)  # 0 (lower eye) -> 1 (upper eye)
            z = (-0.14 + 0.25 * t) * body_len
            x_base = (0.145 - 0.058 * t + 0.016 * math.sin(2.0 * math.pi * t)) * body_len
            x = side * x_base
            y_surf = y_front - _arch_height(x, z, body_len, arch_front) - 0.0012
            pts_fh.append(Vector((x, y_surf, z)))
            # Wider at eyes, narrowest at middle notches
            rad = body_len * (0.014 if (k in (0, n_f)) else (0.0085 + 0.003 * abs(t - 0.5)))
            radii_fh.append(rad)
        _add_tube_along_points(bm_fh, pts_fh, radii_fh, n_sides=8, mat_idx=0)
        # Upper and lower eye circles
        for end_pt, eye_r in ((pts_fh[0], body_len * 0.017), (pts_fh[-1], body_len * 0.014)):
            _add_cylinder_between(
                bm_fh,
                end_pt + Vector((0.0, 0.002, 0.0)),
                end_pt - Vector((0.0, 0.0015, 0.0)),
                eye_r,
                eye_r * 0.92,
                n_sides=12,
                mat_idx=0,
            )

    fh_obj = _make_mesh_obj(col, f"{name_prefix}_FHoles", bm_fh, [mats["GlossEbony"]], smooth=True)
    fh_obj.parent = parent
    return body_obj


def _build_viol_fittings(
    col: bpy.types.Collection,
    name_prefix: str,
    body_len: float,
    rib_depth: float,
    arch_front: float,
    step_min: int,
    step_max: int,
    open_steps: list[int],
    mats: dict[str, bpy.types.Material],
    parent: bpy.types.Object,
) -> dict[str, Any]:
    """Build bridge, tailpiece, neck, ebony fingerboard with 53-EDO micro-fret dots, scroll, pegs, strings & stop nodes."""
    y_front = -rib_depth * 0.5
    z_top_body = body_len * 0.5
    z_bot_body = -body_len * 0.5

    # Neck geometry constants proportional to body_len (cello ~0.755m, viola ~0.415m)
    neck_len = body_len * 0.42
    fb_bot_z = body_len * 0.145
    fb_top_z = z_top_body + neck_len
    fb_len = fb_top_z - fb_bot_z

    y_belly_bridge = y_front - _arch_height(0.0, 0.0, body_len, arch_front)
    y_nut = y_front - arch_front * 0.72
    bridge_h = body_len * 0.072
    bridge_z = -body_len * 0.025
    y_bridge_top = y_belly_bridge - bridge_h

    # Fingerboard slants slightly outward toward bridge so strings clear fingerboard evenly
    y_fb_bot = y_belly_bridge - bridge_h * 0.55
    y_fb_top = y_nut

    def fb_y_at_z(z: float) -> float:
        u = (z - fb_top_z) / (fb_bot_z - fb_top_z)
        return y_fb_top + u * (y_fb_bot - y_fb_top)

    # 1) Carved Bridge (AntiqueSpruce)
    bm_br = bmesh.new()
    br_w_bot = body_len * 0.095
    br_w_top = body_len * 0.078
    br_thick = body_len * 0.012
    n_arch = 12
    # Create clean arch bridge profile extruded in Z
    br_front: list[bmesh.types.BMVert] = []
    br_back: list[bmesh.types.BMVert] = []
    # Bottom feet + arched top crown
    pts_br = [
        (-br_w_bot * 0.5, y_belly_bridge + 0.002),
        (-br_w_bot * 0.46, y_belly_bridge - bridge_h * 0.35),
        (-br_w_top * 0.5, y_bridge_top + 0.004),
    ]
    for i in range(n_arch + 1):
        tx = -1.0 + 2.0 * (i / float(n_arch))
        bx = tx * br_w_top * 0.5
        by = y_bridge_top - body_len * 0.008 * (1.0 - tx * tx)
        pts_br.append((bx, by))
    pts_br.extend([
        (br_w_bot * 0.46, y_belly_bridge - bridge_h * 0.35),
        (br_w_bot * 0.5, y_belly_bridge + 0.002),
    ])
    for (bx, by) in pts_br:
        br_front.append(bm_br.verts.new((bx, by, bridge_z - br_thick * 0.5)))
        br_back.append(bm_br.verts.new((bx, by * 0.995, bridge_z + br_thick * 0.5)))
    _loft_rings(bm_br, [br_front, br_back], cap_start=True, cap_end=True)
    bmesh.ops.recalc_face_normals(bm_br, faces=bm_br.faces)
    br_obj = _make_mesh_obj(col, f"{name_prefix}_Bridge", bm_br, [mats["AntiqueSpruce"]], smooth=False)
    _add_bevel(br_obj, width=0.0008, segments=2)
    br_obj.parent = parent

    # 2) Tailpiece (GlossEbony) + Brass Fine Tuners + Tailgut
    bm_tp = bmesh.new()
    tp_z0 = z_bot_body + body_len * 0.065
    tp_z1 = bridge_z - body_len * 0.145
    tp_w0 = body_len * 0.026
    tp_w1 = body_len * 0.048
    tp_rings: list[list[bmesh.types.BMVert]] = []
    for k in range(6):
        u = k / 5.0
        z = tp_z0 + u * (tp_z1 - tp_z0)
        w = tp_w0 + u * (tp_w1 - tp_w0)
        y_surf = y_front - _arch_height(0.0, z, body_len, arch_front) - 0.012 - u * 0.018
        thick = body_len * 0.012
        tp_rings.append([
            bm_tp.verts.new((-w * 0.5, y_surf, z)),
            bm_tp.verts.new((w * 0.5, y_surf, z)),
            bm_tp.verts.new((w * 0.42, y_surf + thick, z)),
            bm_tp.verts.new((-w * 0.42, y_surf + thick, z)),
        ])
    _loft_rings(bm_tp, tp_rings, cap_start=True, cap_end=True, mat_idx=0)
    # Tailgut loop to bottom saddle
    saddle_pt = Vector((0.0, y_front - 0.004, z_bot_body - 0.003))
    for sx in (-1.0, 1.0):
        _add_cylinder_between(
            bm_tp,
            saddle_pt + Vector((sx * tp_w0 * 0.25, 0.0, 0.0)),
            Vector((sx * tp_w0 * 0.30, y_front - 0.012, tp_z0)),
            body_len * 0.0025,
            body_len * 0.0025,
            n_sides=8,
            mat_idx=1,
        )
    # 4 Brass fine-tuner screws on top of tailpiece
    for s_idx in range(4):
        tx = (-0.5 + s_idx / 3.0) * tp_w1 * 0.72
        tz = tp_z1 - body_len * 0.018
        ty = y_front - _arch_height(0.0, tz, body_len, arch_front) - 0.028
        _add_cylinder_between(
            bm_tp,
            Vector((tx, ty + 0.006, tz)),
            Vector((tx, ty - 0.008, tz)),
            body_len * 0.0045,
            body_len * 0.0055,
            n_sides=10,
            mat_idx=1,
        )
    bmesh.ops.recalc_face_normals(bm_tp, faces=bm_tp.faces)
    tp_obj = _make_mesh_obj(col, f"{name_prefix}_Tailpiece", bm_tp, [mats["GlossEbony"], mats["BrushedGold"]], smooth=False)
    _add_bevel(tp_obj, width=0.001, segments=2)
    tp_obj.parent = parent

    # 3) Neck, Heel, Pegbox & Multi-Turn Carved Scroll (WarmMahogany + GlossEbony pegs)
    bm_nk = bmesh.new()
    neck_w_top = body_len * 0.036
    neck_w_bot = body_len * 0.056
    neck_rings: list[list[bmesh.types.BMVert]] = []
    for k in range(8):
        u = k / 7.0
        z = z_top_body - body_len * 0.02 + u * (neck_len + body_len * 0.02)
        w = neck_w_bot + u * (neck_w_top - neck_w_bot)
        yf = fb_y_at_z(z) + 0.004
        yb = yf + body_len * (0.042 - 0.014 * u)
        # Rounded D-profile neck back
        neck_rings.append([
            bm_nk.verts.new((-w * 0.5, yf, z)),
            bm_nk.verts.new((-w * 0.36, (yf + yb) * 0.55, z)),
            bm_nk.verts.new((0.0, yb, z)),
            bm_nk.verts.new((w * 0.36, (yf + yb) * 0.55, z)),
            bm_nk.verts.new((w * 0.5, yf, z)),
        ])
    _loft_rings(bm_nk, neck_rings, cap_start=True, cap_end=True, mat_idx=0)

    # Carved neck heel joining upper bout
    _add_cylinder_between(
        bm_nk,
        Vector((0.0, y_front + rib_depth * 0.45, z_top_body - body_len * 0.01)),
        Vector((0.0, fb_y_at_z(z_top_body) + body_len * 0.026, z_top_body + body_len * 0.03)),
        body_len * 0.028,
        body_len * 0.022,
        n_sides=12,
        mat_idx=0,
    )

    # Pegbox walls (angled slightly back along +Y)
    pegbox_len = body_len * 0.165
    peg_z0 = fb_top_z
    peg_z1 = fb_top_z + pegbox_len
    peg_y0 = y_nut + 0.008
    peg_y1 = peg_y0 + body_len * 0.045
    pb_w0 = neck_w_top * 0.92
    pb_w1 = neck_w_top * 0.72
    pb_rings: list[list[bmesh.types.BMVert]] = []
    for k in range(5):
        u = k / 4.0
        z = peg_z0 + u * pegbox_len
        yc = peg_y0 + u * (peg_y1 - peg_y0)
        w = pb_w0 + u * (pb_w1 - pb_w0)
        d = body_len * 0.028
        pb_rings.append([
            bm_nk.verts.new((-w * 0.5, yc - d * 0.4, z)),
            bm_nk.verts.new((w * 0.5, yc - d * 0.4, z)),
            bm_nk.verts.new((w * 0.44, yc + d * 0.6, z)),
            bm_nk.verts.new((-w * 0.44, yc + d * 0.6, z)),
        ])
    _loft_rings(bm_nk, pb_rings, cap_start=True, cap_end=True, mat_idx=0)

    # Multi-turn Carved Spiral Scroll at top of pegbox
    scroll_center = Vector((0.0, peg_y1 + body_len * 0.014, peg_z1 + body_len * 0.038))
    scroll_pts: list[Vector] = []
    scroll_rads: list[float] = []
    n_scroll = 28
    for k in range(n_scroll):
        t = k / float(n_scroll - 1)
        ang = -0.3 * math.pi + t * 2.55 * math.pi
        rad_spiral = body_len * (0.046 * (1.0 - 0.72 * t))
        sy = scroll_center.y - rad_spiral * math.cos(ang)
        sz = scroll_center.z + rad_spiral * math.sin(ang)
        scroll_pts.append(Vector((0.0, sy, sz)))
        scroll_rads.append(body_len * (0.019 * (1.0 - 0.58 * t)))
    _add_tube_along_points(bm_nk, scroll_pts, scroll_rads, n_sides=12, mat_idx=0)
    # Central scroll boss eye protruding subtly on +/-X
    _add_cylinder_between(
        bm_nk,
        scroll_center + Vector((-neck_w_top * 0.52, 0.0, 0.0)),
        scroll_center + Vector((neck_w_top * 0.52, 0.0, 0.0)),
        body_len * 0.012,
        body_len * 0.012,
        n_sides=14,
        mat_idx=0,
    )

    # 4 Ebony Tuning Pegs with BrushedGold collar rings
    for p_idx in range(4):
        u = 0.18 + 0.64 * (p_idx / 3.0)
        pz = peg_z0 + u * pegbox_len
        py = peg_y0 + u * (peg_y1 - peg_y0) + body_len * 0.004
        side = -1.0 if p_idx % 2 == 0 else 1.0
        shank_end = Vector((side * body_len * 0.056, py, pz))
        _add_cylinder_between(
            bm_nk,
            Vector((-side * pb_w0 * 0.52, py, pz)),
            shank_end,
            body_len * 0.0055,
            body_len * 0.0045,
            n_sides=10,
            mat_idx=1,
        )
        # Gold collar ring
        _add_cylinder_between(
            bm_nk,
            Vector((side * pb_w0 * 0.45, py, pz)),
            Vector((side * pb_w0 * 0.58, py, pz)),
            body_len * 0.0075,
            body_len * 0.0075,
            n_sides=12,
            mat_idx=2,
        )
        # Paddle button head
        _add_cylinder_between(
            bm_nk,
            shank_end,
            shank_end + Vector((side * body_len * 0.016, 0.0, 0.0)),
            body_len * 0.014,
            body_len * 0.011,
            n_sides=12,
            mat_idx=1,
        )

    bmesh.ops.recalc_face_normals(bm_nk, faces=bm_nk.faces)
    nk_obj = _make_mesh_obj(
        col,
        f"{name_prefix}_NeckScroll",
        bm_nk,
        [mats["WarmMahogany"], mats["GlossEbony"], mats["BrushedGold"]],
        smooth=True,
    )
    nk_obj.parent = parent

    # 4) Ebony Fingerboard (GlossEbony) + 53-EDO Micro-Fret Golden Inlay Dots (BrushedGold)
    bm_fb = bmesh.new()
    fb_w_top = neck_w_top * 0.94
    fb_w_bot = body_len * 0.078
    fb_thick = body_len * 0.010
    fb_rings: list[list[bmesh.types.BMVert]] = []
    for k in range(10):
        u = k / 9.0
        z = fb_top_z - u * fb_len
        w = fb_w_top + u * (fb_w_bot - fb_w_top)
        yf = fb_y_at_z(z)
        # Gently cambered fingerboard top face (-Y)
        fb_rings.append([
            bm_fb.verts.new((-w * 0.5, yf + fb_thick * 0.15, z)),
            bm_fb.verts.new((-w * 0.25, yf - fb_thick * 0.12, z)),
            bm_fb.verts.new((0.0, yf - fb_thick * 0.22, z)),
            bm_fb.verts.new((w * 0.25, yf - fb_thick * 0.12, z)),
            bm_fb.verts.new((w * 0.5, yf + fb_thick * 0.15, z)),
            bm_fb.verts.new((w * 0.48, yf + fb_thick, z)),
            bm_fb.verts.new((-w * 0.48, yf + fb_thick, z)),
        ])
    _loft_rings(bm_fb, fb_rings, cap_start=True, cap_end=True, mat_idx=0)

    # Subtle 53-step golden micro-fret inlay dots inlaid flush along the ebony fingerboard
    # Map 53 micro-steps along the playable string scale length (from nut down to ~2 octaves)
    scale_len = fb_top_z - bridge_z
    for m_step in range(1, 54):
        # Equal-tempered 53-EDO acoustic string-length fraction: 1 - 2^(-m/53)
        stop_frac = 1.0 - (2.0 ** (-m_step / 53.0))
        z_dot = fb_top_z - stop_frac * scale_len
        if z_dot < fb_bot_z + 0.008:
            break
        u_fb = (fb_top_z - z_dot) / fb_len
        w_here = fb_w_top + u_fb * (fb_w_bot - fb_w_top)
        # Stagger micro-dots subtly across the 4 string lanes + highlight prime markers (5, 17, 22, 31, 43, 53)
        is_major = m_step in (17, 22, 31, 43, 53)
        lane_u = ((m_step % 4) - 1.5) / 3.2
        x_dot = lane_u * w_here * 0.72
        y_dot = fb_y_at_z(z_dot) - fb_thick * 0.16 * (1.0 - (x_dot / (w_here * 0.5)) ** 2)
        dot_r = body_len * (0.0038 if is_major else 0.0020)
        _add_cylinder_between(
            bm_fb,
            Vector((x_dot, y_dot + 0.0012, z_dot)),
            Vector((x_dot, y_dot - 0.0006, z_dot)),
            dot_r,
            dot_r * 0.9,
            n_sides=8,
            mat_idx=1,
        )

    bmesh.ops.recalc_face_normals(bm_fb, faces=bm_fb.faces)
    fb_obj = _make_mesh_obj(
        col,
        f"{name_prefix}_Fingerboard",
        bm_fb,
        [mats["GlossEbony"], mats["BrushedGold"]],
        smooth=True,
    )
    fb_obj.parent = parent

    # 5) 11 Sympathetic Copper/Silver Under-Strings beneath the fingerboard
    bm_symp = bmesh.new()
    for s_i in range(11):
        frac = (s_i - 5.0) / 5.0
        p_bot = Vector((frac * tp_w1 * 0.34, y_belly_bridge - bridge_h * 0.35, bridge_z - body_len * 0.14))
        p_top = Vector((frac * fb_w_top * 0.34, y_nut + 0.004, fb_top_z - body_len * 0.015))
        _add_cylinder_between(bm_symp, p_bot, p_top, body_len * 0.0008, body_len * 0.0008, n_sides=6, mat_idx=0)
    symp_obj = _make_mesh_obj(col, f"{name_prefix}_SympatheticStrings", bm_symp, [mats["CopperString"]], smooth=True)
    symp_obj.parent = parent

    # 6) 4 Main Glowing Strings (LuminousElement) with lateral X vibration shape keys
    strings_info: list[dict[str, Any]] = []
    for s_idx, open_step in enumerate(open_steps):
        lane = -0.5 + s_idx / 3.0  # -0.5 .. +0.5
        x_tp = lane * tp_w1 * 0.68
        x_br = lane * br_w_top * 0.72
        x_nut = lane * fb_w_top * 0.68
        crown_br = -body_len * 0.008 * (1.0 - (lane * 1.4) ** 2)

        p_tp = Vector((x_tp, y_front - _arch_height(0.0, tp_z1, body_len, arch_front) - 0.025, tp_z1))
        p_br = Vector((x_br, y_bridge_top + crown_br - 0.001, bridge_z))
        p_nut = Vector((x_nut, y_nut - 0.0025, fb_top_z))

        # Build multi-segment string mesh so shape key bows smoothly along sounding length (bridge -> nut)
        bm_s = bmesh.new()
        n_segs = 20
        n_sides = 8
        str_r = body_len * (0.0022 - 0.00022 * s_idx)
        pts_str: list[Vector] = [p_tp]
        for k in range(n_segs + 1):
            u = k / float(n_segs)
            pts_str.append(p_br.lerp(p_nut, u))
        rads_str = [str_r] * len(pts_str)
        _add_tube_along_points(bm_s, pts_str, rads_str, n_sides=n_sides, mat_idx=0)

        s_obj = _make_mesh_obj(
            col,
            f"{name_prefix}_String_{s_idx}",
            bm_s,
            [mats["LuminousElement"]],
            smooth=True,
        )
        s_obj.parent = parent
        idle_rgb = common.vivid_53edo_color(open_step)
        s_obj.color = (*idle_rgb, 0.04)

        # Lateral vibration shape key over the sounding span (ring indices 1 .. n_segs+1)
        sk_basis = s_obj.shape_key_add(name="Basis", from_mix=False)
        kb = s_obj.shape_key_add(name="Vibrate", from_mix=False)
        kb.slider_min = -1.5
        kb.slider_max = 1.5
        kb.value = 0.0
        amp = body_len * 0.0085
        for v_i, vert in enumerate(s_obj.data.vertices):
            ring_i = v_i // n_sides
            if ring_i >= 1:
                u = (ring_i - 1) / float(n_segs)
                kb.data[v_i].co.x = vert.co.x + amp * math.sin(math.pi * u)

        strings_info.append({
            "obj": s_obj,
            "kb": kb,
            "open_step": open_step,
            "idle_rgb": idle_rgb,
            "p_br": p_br,
            "p_nut": p_nut,
        })

    # 7) Reusable Luminous Finger-Stop Nodes (4 jewel collars sliding/illuminating on stopped positions)
    stop_nodes: list[bpy.types.Object] = []
    for i in range(4):
        bm_nd = bmesh.new()
        bmesh.ops.create_uvsphere(bm_nd, u_segments=14, v_segments=10, radius=body_len * 0.011)
        nd_obj = _make_mesh_obj(col, f"{name_prefix}_StopNode_{i}", bm_nd, [mats["LuminousElement"]], smooth=True)
        nd_obj.parent = parent
        nd_obj.color = (1.0, 0.85, 0.3, 0.0)
        nd_obj.scale = (0.0, 0.0, 0.0)
        nd_obj.location = (0.0, 0.0, 0.0)
        stop_nodes.append(nd_obj)

    return {
        "strings": strings_info,
        "stop_nodes": stop_nodes,
        "body_len": body_len,
        "bridge_z": bridge_z,
        "fb_top_z": fb_top_z,
        "step_min": step_min,
        "step_max": step_max,
    }


# ---------------------------------------------------------------------------
# Floating Pernambuco & Horsehair Bow
# ---------------------------------------------------------------------------

def _build_pernambuco_bow(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
    parent: bpy.types.Object,
    bow_len: float = 0.71,
) -> bpy.types.Object:
    """Build a cambered Pernambuco & Horsehair cello bow with frog at +X and tip at -X."""
    bow_pivot = _new_empty(col, "CelloFloatingBowPivot", location=(0.0, -0.155, 0.075), parent=parent)

    bm = bmesh.new()
    # Bow lies along X in [-bow_len*0.5, +bow_len*0.5]; horsehair is at y=0, stick arches toward -Y
    hx0 = -bow_len * 0.48  # tip
    hx1 = bow_len * 0.46   # frog
    n_pts = 18
    stick_pts: list[Vector] = []
    stick_rads: list[float] = []
    for k in range(n_pts + 1):
        u = k / float(n_pts)  # 0=tip -> 1=frog
        x = hx0 + u * (hx1 - hx0)
        # Classic inward camber toward horsehair (+Y is toward strings, stick is at -Y)
        camber = -0.022 + 0.011 * math.sin(math.pi * u)
        if u < 0.08:
            # Pointed swan-head tip curving down to meet hair
            camber = -0.022 * (u / 0.08)
        stick_pts.append(Vector((x, camber, 0.0)))
        stick_rads.append(0.0032 + 0.0020 * u)
    _add_tube_along_points(bm, stick_pts, stick_rads, n_sides=8, mat_idx=0)

    # Frog (GlossEbony) + SilverMetal ferrule & BrushedGold screw button
    frog_x0 = hx1 - 0.068
    frog_x1 = hx1 - 0.004
    frog_pts = [
        Vector((frog_x0, -0.021, -0.004)),
        Vector((frog_x1, -0.021, -0.004)),
        Vector((frog_x1, 0.002, -0.004)),
        Vector((frog_x0, 0.002, -0.004)),
    ]
    frog_f = [bm.verts.new(p) for p in frog_pts]
    frog_b = [bm.verts.new((p.x, p.y, 0.004)) for p in frog_pts]
    _loft_rings(bm, [frog_f, frog_b], cap_start=True, cap_end=True, mat_idx=1)
    # Screw button
    _add_cylinder_between(
        bm,
        Vector((hx1, -0.022, 0.0)),
        Vector((hx1 + 0.024, -0.022, 0.0)),
        0.0048,
        0.0042,
        n_sides=10,
        mat_idx=2,
    )
    # Silver winding grip near frog
    _add_cylinder_between(
        bm,
        Vector((frog_x0 - 0.065, -0.0195, 0.0)),
        Vector((frog_x0 - 0.005, -0.0195, 0.0)),
        0.0054,
        0.0054,
        n_sides=10,
        mat_idx=3,
    )

    # Horsehair flat ribbon at y=0 (closest to cello strings)
    hair_w = 0.0055
    hair_thick = 0.0016
    hair_rings: list[list[bmesh.types.BMVert]] = []
    for k in range(10):
        u = k / 9.0
        x = (hx0 + 0.006) + u * (frog_x0 + 0.008 - (hx0 + 0.006))
        hair_rings.append([
            bm.verts.new((x, -hair_thick * 0.5, -hair_w)),
            bm.verts.new((x, hair_thick * 0.5, -hair_w)),
            bm.verts.new((x, hair_thick * 0.5, hair_w)),
            bm.verts.new((x, -hair_thick * 0.5, hair_w)),
        ])
    _loft_rings(bm, hair_rings, cap_start=True, cap_end=True, mat_idx=4)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bow_mesh = _make_mesh_obj(
        col,
        "CelloFloatingBow",
        bm,
        [mats["WarmMahogany"], mats["GlossEbony"], mats["BrushedGold"], mats["SilverMetal"], mats["Horsehair"]],
        smooth=True,
    )
    bow_mesh.parent = bow_pivot
    return bow_pivot


# ---------------------------------------------------------------------------
# Grounded Pedestal Cradle & Endpin Supports (z = 0.09)
# ---------------------------------------------------------------------------

def _build_cello_mount(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Build grounded floor endpin cup + discreet rear cradle at z=0.09, returning cello body pivot."""
    cello_xy = (-0.20, 0.04)
    # 1) Endpin stopper puck flush on z = PEDESTAL_Z
    bm_cup = bmesh.new()
    _add_cylinder_between(
        bm_cup,
        Vector((cello_xy[0], cello_xy[1], PEDESTAL_Z)),
        Vector((cello_xy[0], cello_xy[1], PEDESTAL_Z + 0.020)),
        0.058,
        0.048,
        n_sides=32,
        mat_idx=0,
    )
    _add_cylinder_between(
        bm_cup,
        Vector((cello_xy[0], cello_xy[1], PEDESTAL_Z + 0.020)),
        Vector((cello_xy[0], cello_xy[1], PEDESTAL_Z + 0.026)),
        0.038,
        0.032,
        n_sides=24,
        mat_idx=1,
    )
    cup_obj = _make_mesh_obj(col, "CelloEndpinCup", bm_cup, [mats["GlossEbony"], mats["BrushedGold"]], smooth=True)
    _add_bevel(cup_obj, width=0.002, segments=2)

    # 2) Cello tilt pivot grounded cleanly inside the endpin cup (z = PEDESTAL_Z + 0.018)
    cello_pivot = _new_empty(
        col,
        "CelloAssemblyPivot",
        location=(cello_xy[0], cello_xy[1], PEDESTAL_Z + 0.018),
        rotation_euler=(math.radians(9.0), 0.0, math.radians(-14.0)),
    )

    # Adjustable Brass Endpin + Ebony Collar (in cello local frame, z=0 at cup -> z=0.25 at lower bout)
    endpin_len = 0.245
    bm_pin = bmesh.new()
    _add_cylinder_between(bm_pin, Vector((0.0, 0.0, 0.0)), Vector((0.0, 0.0, 0.018)), 0.011, 0.007, n_sides=14, mat_idx=0)
    _add_cylinder_between(bm_pin, Vector((0.0, 0.0, 0.018)), Vector((0.0, 0.0, endpin_len)), 0.006, 0.006, n_sides=14, mat_idx=1)
    # Ebony endpin socket + thumbscrew at bottom of cello body
    _add_cylinder_between(bm_pin, Vector((0.0, 0.0, endpin_len - 0.015)), Vector((0.0, 0.0, endpin_len + 0.016)), 0.018, 0.022, n_sides=16, mat_idx=2)
    _add_cylinder_between(bm_pin, Vector((0.018, 0.0, endpin_len)), Vector((0.036, 0.0, endpin_len)), 0.004, 0.008, n_sides=10, mat_idx=0)
    pin_obj = _make_mesh_obj(col, "CelloEndpin", bm_pin, [mats["BrushedGold"], mats["SilverMetal"], mats["GlossEbony"]], smooth=True)
    pin_obj.parent = cello_pivot

    # 3) Discreet Rear Ebony & Brass Museum Support Post seated at z=0.09 cradling the back ribs
    # Lower bout back sits around y ~ +0.16, z ~ 0.44 in world; add a slim pedestal post right behind it
    post_xy = (cello_xy[0] + 0.04, cello_xy[1] + 0.21)
    bm_sup = bmesh.new()
    _add_cylinder_between(
        bm_sup,
        Vector((post_xy[0], post_xy[1], PEDESTAL_Z)),
        Vector((post_xy[0], post_xy[1], PEDESTAL_Z + 0.018)),
        0.055,
        0.045,
        n_sides=24,
        mat_idx=0,
    )
    _add_cylinder_between(
        bm_sup,
        Vector((post_xy[0], post_xy[1], PEDESTAL_Z + 0.018)),
        Vector((post_xy[0], post_xy[1] - 0.025, 0.43)),
        0.010,
        0.008,
        n_sides=14,
        mat_idx=1,
    )
    # Curved cradle yoke touching back plate cleanly
    _add_tube_along_points(
        bm_sup,
        [
            Vector((post_xy[0] - 0.065, post_xy[1] - 0.068, 0.435)),
            Vector((post_xy[0], post_xy[1] - 0.028, 0.430)),
            Vector((post_xy[0] + 0.065, post_xy[1] - 0.052, 0.435)),
        ],
        [0.007, 0.009, 0.007],
        n_sides=10,
        mat_idx=0,
    )
    sup_obj = _make_mesh_obj(col, "CelloRearCradle", bm_sup, [mats["GlossEbony"], mats["BrushedGold"]], smooth=True)
    _add_bevel(sup_obj, width=0.0015, segments=2)

    # Child pivot for the cello body centered at z_local = endpin_len + body_len*0.5
    body_len = 0.755
    cello_body_center = _new_empty(
        col,
        "CelloBodyCenter",
        location=(0.0, 0.0, endpin_len + body_len * 0.5),
        parent=cello_pivot,
    )
    return cello_body_center


def _build_viola_mount(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Build sleek ebony & brass floor cradle seated flush at z=0.09, returning viola body pivot."""
    viola_xy = (0.42, -0.08)
    rot_z = math.radians(20.0)
    cradle_root = _new_empty(col, "ViolaCradleRoot", location=(viola_xy[0], viola_xy[1], PEDESTAL_Z), rotation_euler=(0.0, 0.0, rot_z))

    bm = bmesh.new()
    # Sleek beveled ebony base plate (grounded at local z=0 -> world z=0.09)
    _add_cylinder_between(bm, Vector((0.0, 0.0, 0.0)), Vector((0.0, 0.0, 0.020)), 0.135, 0.122, n_sides=32, mat_idx=0)
    _add_cylinder_between(bm, Vector((0.0, 0.0, 0.020)), Vector((0.0, 0.0, 0.026)), 0.124, 0.118, n_sides=32, mat_idx=1)

    # Rear brass stanchion + lower twin saddle arms
    _add_cylinder_between(bm, Vector((0.0, 0.055, 0.024)), Vector((0.0, 0.085, 0.29)), 0.011, 0.009, n_sides=14, mat_idx=1)
    # Lower cradle fork arms holding bottom bout cleanly at z_local ~ 0.145
    for sx in (-1.0, 1.0):
        _add_tube_along_points(
            bm,
            [
                Vector((0.0, 0.058, 0.145)),
                Vector((sx * 0.068, 0.010, 0.135)),
                Vector((sx * 0.072, -0.052, 0.148)),
            ],
            [0.007, 0.0065, 0.0075],
            n_sides=10,
            mat_idx=1,
        )
        # Dark velvet/ebony cradle pads
        _add_cylinder_between(
            bm,
            Vector((sx * 0.068, -0.025, 0.142)),
            Vector((sx * 0.072, -0.050, 0.149)),
            0.009,
            0.009,
            n_sides=10,
            mat_idx=0,
        )
    # Upper neck-rest yoke holding the viola upper shoulder / heel at z_local ~ 0.42
    _add_cylinder_between(bm, Vector((0.0, 0.085, 0.29)), Vector((0.0, 0.115, 0.44)), 0.009, 0.008, n_sides=14, mat_idx=1)
    _add_tube_along_points(
        bm,
        [
            Vector((-0.036, 0.068, 0.445)),
            Vector((0.0, 0.115, 0.440)),
            Vector((0.036, 0.068, 0.445)),
        ],
        [0.0065, 0.0075, 0.0065],
        n_sides=10,
        mat_idx=0,
    )

    cradle_obj = _make_mesh_obj(col, "ViolaCradle", bm, [mats["GlossEbony"], mats["BrushedGold"]], smooth=True)
    _add_bevel(cradle_obj, width=0.0018, segments=2)
    cradle_obj.parent = cradle_root

    # Viola body tilted cleanly back 20 deg inside the cradle
    viola_body_len = 0.425
    viola_pivot = _new_empty(
        col,
        "ViolaBodyCenter",
        location=(0.0, 0.015, 0.145 + viola_body_len * 0.5),
        rotation_euler=(math.radians(20.0), 0.0, 0.0),
        parent=cradle_root,
    )
    return viola_pivot


# ---------------------------------------------------------------------------
# Timeline Routing & Keyframe Animation
# ---------------------------------------------------------------------------

def _pick_string_index(step: int, open_steps: list[int]) -> int:
    """Assign a 53-EDO step to the natural string index (highest open_step <= step)."""
    chosen = 0
    for idx, ost in enumerate(open_steps):
        if step >= ost:
            chosen = idx
    return chosen


def _animate_viol_instrument(
    inst_data: dict[str, Any],
    notes: list[dict[str, Any]],
    fps: int,
    total_frames: int,
    bow_pivot: bpy.types.Object | None = None,
) -> None:
    """Animate string glow + lateral vibration, finger-stop jewel nodes, and optional floating bow."""
    strings = inst_data["strings"]
    stop_nodes = inst_data["stop_nodes"]
    open_steps = [s["open_step"] for s in strings]
    fb_top_z = inst_data["fb_top_z"]
    bridge_z = inst_data["bridge_z"]
    scale_len = fb_top_z - bridge_z

    # Group note events by assigned string index
    by_string: dict[int, list[dict[str, Any]]] = {i: [] for i in range(len(strings))}
    for n in notes:
        s_idx = _pick_string_index(n["step"], open_steps)
        by_string[s_idx].append(n)

    # 1) Animate each of the 4 main strings
    for s_idx, s_info in enumerate(strings):
        obj = s_info["obj"]
        kb = s_info["kb"]
        idle_rgb = s_info["idle_rgb"]
        evts = sorted(by_string[s_idx], key=lambda x: x["start_s"])

        obj.color = (*idle_rgb, 0.04)
        obj.keyframe_insert(data_path="color", frame=1)
        obj.scale = (1.0, 1.0, 1.0)
        obj.keyframe_insert(data_path="scale", index=0, frame=1)
        obj.keyframe_insert(data_path="scale", index=1, frame=1)
        kb.value = 0.0
        kb.keyframe_insert(data_path="value", frame=1)

        if not evts:
            continue

        const_frames: set[int] = {1}
        for i, ev in enumerate(evts):
            f0 = common.sec_to_frame(ev["start_s"], fps)
            f_end = min(total_frames, common.sec_to_frame(ev["end_s"], fps))
            next_f0 = common.sec_to_frame(evts[i + 1]["start_s"], fps) if i + 1 < len(evts) else total_frames + 10
            rgb = common.vivid_53edo_color(ev["step"])
            peak_alpha = min(0.84, 0.62 + 0.22 * ev["vel"])
            swell_scale = 1.0 + 0.38 * peak_alpha

            if f0 > 2:
                f_pre = f0 - 1
                obj.color = (*idle_rgb, 0.04)
                obj.keyframe_insert(data_path="color", frame=f_pre)
                obj.scale[0] = 1.0
                obj.scale[1] = 1.0
                obj.keyframe_insert(data_path="scale", index=0, frame=f_pre)
                obj.keyframe_insert(data_path="scale", index=1, frame=f_pre)
                kb.value = 0.0
                kb.keyframe_insert(data_path="value", frame=f_pre)
                const_frames.add(f_pre)

            # Sustain arc while bowed
            obj.color = (*rgb, peak_alpha)
            obj.keyframe_insert(data_path="color", frame=f0)
            obj.scale[0] = swell_scale
            obj.scale[1] = swell_scale
            obj.keyframe_insert(data_path="scale", index=0, frame=f0)
            obj.keyframe_insert(data_path="scale", index=1, frame=f0)

            hold_end = min(f_end, next_f0 - 2)
            if hold_end > f0:
                mid_f = (f0 + hold_end) // 2
                if mid_f > f0:
                    obj.color = (*rgb, min(1.0, peak_alpha * 1.05))
                    obj.keyframe_insert(data_path="color", frame=mid_f)
                obj.color = (*rgb, peak_alpha * 0.80)
                obj.keyframe_insert(data_path="color", frame=hold_end)
                obj.scale[0] = 1.0 + 0.28 * peak_alpha
                obj.scale[1] = 1.0 + 0.28 * peak_alpha
                obj.keyframe_insert(data_path="scale", index=0, frame=hold_end)
                obj.keyframe_insert(data_path="scale", index=1, frame=hold_end)

            if hold_end >= f_end and f_end < total_frames:
                f_rel = min(total_frames, f_end + 2)
                obj.color = (*idle_rgb, 0.04)
                obj.keyframe_insert(data_path="color", frame=f_rel)
                obj.scale[0] = 1.0
                obj.scale[1] = 1.0
                obj.keyframe_insert(data_path="scale", index=0, frame=f_rel)
                obj.keyframe_insert(data_path="scale", index=1, frame=f_rel)
                const_frames.add(f_rel)

            # Bowed lateral vibration (continuous high-frequency oscillation across sustained note)
            vib_end = min(f_end, next_f0 - 2, total_frames)
            vel_amp = 0.65 + 0.45 * ev["vel"]
            for k in range(0, vib_end - f0 + 1, 1):
                f_v = f0 + k
                env = math.sin(math.pi * min(1.0, (k + 1) / float(max(2, vib_end - f0 + 1)))) ** 0.4
                sign = 1.0 if (k % 2 == 0) else -1.0
                kb.value = vel_amp * env * sign
                kb.keyframe_insert(data_path="value", frame=f_v)
            if vib_end + 1 < next_f0:
                kb.value = 0.0
                kb.keyframe_insert(data_path="value", frame=min(total_frames, vib_end + 1))

        common.set_constant_segment(obj, "color", -1, const_frames)
        common.set_constant_segment(obj, "scale", 0, const_frames)
        common.set_constant_segment(obj, "scale", 1, const_frames)

    # 2) Animate 4 reusable finger-stop jewel nodes along the stopped fingerboard position
    node_free_frame = [1] * len(stop_nodes)
    node_const: list[set[int]] = [{1} for _ in stop_nodes]
    for nd in stop_nodes:
        nd.location = (0.0, 0.0, 0.0)
        nd.scale = (0.0, 0.0, 0.0)
        nd.color = (1.0, 0.85, 0.3, 0.0)
        nd.keyframe_insert(data_path="location", frame=1)
        nd.keyframe_insert(data_path="scale", frame=1)
        nd.keyframe_insert(data_path="color", frame=1)

    for ev in sorted(notes, key=lambda x: x["start_s"]):
        s_idx = _pick_string_index(ev["step"], open_steps)
        s_info = strings[s_idx]
        semisteps = max(0, ev["step"] - s_info["open_step"])
        stop_frac = min(0.56, 1.0 - (2.0 ** (-semisteps / 53.0)))
        # Interpolate along the string from nut (stop_frac=0) toward bridge (stop_frac=1)
        p_stop = s_info["p_nut"].lerp(s_info["p_br"], stop_frac)
        rgb = common.vivid_53edo_color(ev["step"])

        f0 = common.sec_to_frame(ev["start_s"], fps)
        f_end = min(total_frames, common.sec_to_frame(ev["end_s"], fps))
        best_i = min(range(len(stop_nodes)), key=lambda ni: node_free_frame[ni])
        nd = stop_nodes[best_i]

        if f0 - 1 >= node_free_frame[best_i]:
            nd.location = p_stop
            nd.scale = (0.0, 0.0, 0.0)
            nd.color = (*rgb, 0.0)
            nd.keyframe_insert(data_path="location", frame=f0 - 1)
            nd.keyframe_insert(data_path="scale", frame=f0 - 1)
            nd.keyframe_insert(data_path="color", frame=f0 - 1)
            node_const[best_i].add(f0 - 1)

        nd.location = p_stop
        nd.scale = (1.0, 1.0, 1.0)
        nd.color = (*rgb, 0.95)
        nd.keyframe_insert(data_path="location", frame=f0)
        nd.keyframe_insert(data_path="scale", frame=f0)
        nd.keyframe_insert(data_path="color", frame=f0)

        nd.location = p_stop
        nd.scale = (0.92, 0.92, 0.92)
        nd.color = (*rgb, 0.85)
        nd.keyframe_insert(data_path="location", frame=f_end)
        nd.keyframe_insert(data_path="scale", frame=f_end)
        nd.keyframe_insert(data_path="color", frame=f_end)

        f_hide = min(total_frames, f_end + 2)
        nd.scale = (0.0, 0.0, 0.0)
        nd.color = (*rgb, 0.0)
        nd.keyframe_insert(data_path="scale", frame=f_hide)
        nd.keyframe_insert(data_path="color", frame=f_hide)
        node_const[best_i].add(f_hide)
        node_free_frame[best_i] = f_hide + 1

    for ni, nd in enumerate(stop_nodes):
        common.set_constant_segment(nd, "scale", -1, node_const[ni])
        common.set_constant_segment(nd, "color", -1, node_const[ni])

    # 3) Animate Floating Pernambuco & Horsehair Bow sweeping right/left across notes
    if bow_pivot is not None:
        # Bow sits just above the cello strings in the bowing zone (between bridge & fingerboard end)
        bow_z = bridge_z + 0.058
        # Cello archtop + bridge string plane at bowing zone is ~ y_br = -0.132
        bow_y = strings[1]["p_br"].lerp(strings[1]["p_nut"], 0.09).y - 0.005

        bow_pivot.location = (0.04, bow_y - 0.025, bow_z)
        bow_pivot.rotation_euler = (math.radians(-4.0), math.radians(5.0), 0.0)
        bow_pivot.keyframe_insert(data_path="location", frame=1)
        bow_pivot.keyframe_insert(data_path="rotation_euler", frame=1)

        # Group simultaneous double-stops within 0.25s into single bow strokes
        strokes: list[dict[str, Any]] = []
        for n in sorted(notes, key=lambda x: x["start_s"]):
            s_idx = _pick_string_index(n["step"], open_steps)
            if strokes and abs(n["start_s"] - strokes[-1]["start_s"]) < 0.28:
                strokes[-1]["end_s"] = max(strokes[-1]["end_s"], n["end_s"])
                strokes[-1]["s_indices"].append(s_idx)
            else:
                strokes.append({
                    "start_s": n["start_s"],
                    "end_s": n["end_s"],
                    "s_indices": [s_idx],
                })

        for idx, st in enumerate(strokes):
            f0 = common.sec_to_frame(st["start_s"], fps)
            f1 = min(total_frames, common.sec_to_frame(st["end_s"], fps))
            # Down-bow (even idx): sweep left->right (+X); Up-bow (odd idx): sweep right->left (-X)
            x_start, x_end = (-0.16, 0.17) if (idx % 2 == 0) else (0.17, -0.16)
            avg_s = sum(st["s_indices"]) / float(len(st["s_indices"]))
            # Roll/angle around Y tilts bow onto the active string pair (C-G vs G-D vs D-A)
            tilt_y = math.radians((avg_s - 1.5) * -10.5)
            # Subtle yaw around Z for expressive bow draw
            yaw_z = math.radians(3.5 if (idx % 2 == 0) else -3.5)

            if idx == 0 and f0 > 2:
                bow_pivot.location = (x_start, bow_y - 0.022, bow_z)
                bow_pivot.rotation_euler = (0.0, tilt_y, yaw_z)
                bow_pivot.keyframe_insert(data_path="location", frame=max(2, f0 - 2))
                bow_pivot.keyframe_insert(data_path="rotation_euler", frame=max(2, f0 - 2))

            bow_pivot.location = (x_start, bow_y, bow_z)
            bow_pivot.rotation_euler = (math.radians(-2.0), tilt_y, yaw_z)
            bow_pivot.keyframe_insert(data_path="location", frame=f0)
            bow_pivot.keyframe_insert(data_path="rotation_euler", frame=f0)

            mid_f = (f0 + f1) // 2
            if mid_f > f0:
                bow_pivot.location = (0.5 * (x_start + x_end), bow_y + 0.002, bow_z - 0.004)
                bow_pivot.rotation_euler = (0.0, tilt_y, 0.0)
                bow_pivot.keyframe_insert(data_path="location", frame=mid_f)
                bow_pivot.keyframe_insert(data_path="rotation_euler", frame=mid_f)

            bow_pivot.location = (x_end, bow_y, bow_z)
            bow_pivot.rotation_euler = (math.radians(2.0), tilt_y, -yaw_z)
            bow_pivot.keyframe_insert(data_path="location", frame=f1)
            bow_pivot.keyframe_insert(data_path="rotation_euler", frame=f1)


# ---------------------------------------------------------------------------
# Stage Contract Entrypoint: build_instrument(...)
# ---------------------------------------------------------------------------

def build_instrument(
    mats: dict[str, bpy.types.Material],
    timeline: dict[str, Any],
    *,
    collection_name: str = "ConcertViolDuo",
    anchor_location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    anchor_rotation_z_deg: float = 0.0,
    anchor_scale: float = 1.0,
) -> bpy.types.Object:
    """Build & animate the 53-EDO Concert Viol (Cello) + Sympathetic Viola inside collection_name."""
    viol_col = bpy.data.collections.new(collection_name)
    bpy.context.scene.collection.children.link(viol_col)

    # 1) Cello (grounded via adjustable brass endpin & rear cradle at z=0.09)
    cello_pivot = _build_cello_mount(viol_col, mats)
    _build_viol_body_mesh(
        viol_col,
        "Cello",
        body_len=0.755,
        rib_depth=0.118,
        arch_front=0.028,
        arch_back=0.022,
        mats=mats,
        parent=cello_pivot,
    )
    cello_data = _build_viol_fittings(
        viol_col,
        "Cello",
        body_len=0.755,
        rib_depth=0.118,
        arch_front=0.028,
        step_min=CELLO_STEP_MIN,
        step_max=CELLO_STEP_MAX,
        open_steps=[-53, -36, -22, -5],
        mats=mats,
        parent=cello_pivot,
    )
    bow_pivot = _build_pernambuco_bow(viol_col, mats, parent=cello_pivot, bow_len=0.71)

    # 2) Sympathetic Viola (grounded on ebony & brass cradle at z=0.09)
    viola_pivot = _build_viola_mount(viol_col, mats)
    _build_viol_body_mesh(
        viol_col,
        "Viola",
        body_len=0.425,
        rib_depth=0.044,
        arch_front=0.015,
        arch_back=0.012,
        mats=mats,
        parent=viola_pivot,
    )
    viola_data = _build_viol_fittings(
        viol_col,
        "Viola",
        body_len=0.425,
        rib_depth=0.044,
        arch_front=0.015,
        step_min=VIOLA_STEP_MIN,
        step_max=VIOLA_STEP_MAX,
        open_steps=[-22, -5, 9, 26],
        mats=mats,
        parent=viola_pivot,
    )

    # Route timeline notes cleanly across cello / viola / string_ensemble
    cello_notes: list[dict[str, Any]] = []
    viola_notes: list[dict[str, Any]] = []
    for n in timeline.get("notes", []):
        tid = str(n.get("track_id", "")).lower()
        inst = str(n.get("instrument", "")).lower()
        raw_step = int(n["step"])
        if "viola" in tid or "viola" in inst:
            viola_notes.append({**n, "step": common.fold_step_to_range(raw_step, VIOLA_STEP_MIN, VIOLA_STEP_MAX)})
        elif "cello" in tid or "cello" in inst:
            cello_notes.append({**n, "step": common.fold_step_to_range(raw_step, CELLO_STEP_MIN, CELLO_STEP_MAX)})
        else:
            # string_ensemble / generic viol track: feed both cello & viola sympathetically
            cello_notes.append({**n, "step": common.fold_step_to_range(raw_step, CELLO_STEP_MIN, CELLO_STEP_MAX)})
            viola_notes.append({**n, "step": common.fold_step_to_range(raw_step, VIOLA_STEP_MIN, VIOLA_STEP_MAX)})

    fps = int(timeline.get("fps", 24))
    total_frames = int(timeline.get("total_frames", 1))
    _animate_viol_instrument(cello_data, cello_notes, fps, total_frames, bow_pivot=bow_pivot)
    _animate_viol_instrument(viola_data, viola_notes, fps, total_frames, bow_pivot=None)

    return common.parent_collection_to_anchor(
        viol_col,
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
    common.build_concert_stage(mats, pedestal_radius=1.65, pedestal_height=PEDESTAL_Z, light_target_z=0.78)
    _tune_studio_look(scene, mats)

    timeline = common.load_score_timeline(SCORE_PATH, WAV_PATH, fps=24)
    build_instrument(mats, timeline, collection_name="ConcertViolDuo")

    total_frames = int(timeline["total_frames"])
    cam_keyframes = [
        (1, (1.58, -3.55, 1.50)),
        (max(2, round(total_frames * 0.35)), (0.76, -3.68, 1.44)),
        (max(3, round(total_frames * 0.70)), (-0.48, -3.62, 1.38)),
        (total_frames, (1.05, -3.48, 1.46)),
    ]
    common.setup_orbit_camera(
        target_pos=(0.06, 0.0, 0.78),
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
    print(f"[viol_53edo] Saved blend: {BLEND_PATH}")

    if stills_only:
        frame_specs = [
            ("idle", 1),
            ("double_stop", common.sec_to_frame(4.2, 24)),
            ("resolution", common.sec_to_frame(9.6, 24)),
        ]
        rendered = common.render_diagnostic_stills(frame_specs, OUT_DIR, "diag_viol")
        for p in rendered:
            print(f"[viol_53edo] Diagnostic still: {p}")

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
