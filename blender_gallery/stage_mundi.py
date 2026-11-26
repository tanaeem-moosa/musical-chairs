"""Harmonia Mundi 53-EDO Concert Hall Stage — 7-Instrument Acoustic Ensemble Showcase."""

from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path
from typing import Any

import bmesh
import bpy
import mathutils
from mathutils import Matrix

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blender_gallery import common
from blender_gallery.instruments import (
    guitar_53edo,
    harp_53edo,
    organ_timpani_53edo,
    piano_bosanquet,
    sitar_shruti_53edo,
    viol_53edo,
    winds_brass_53edo,
)

SCORE_PATH = REPO_ROOT / "scores" / "sample_5min.json"
EXCERPT_WAV_PATH = REPO_ROOT / "output" / "showcase_3d" / "harmonia_mundi_excerpt.wav"
FULL_WAV_PATH = REPO_ROOT / "output" / "sample_5min.wav"
BLEND_PATH = REPO_ROOT / "output" / "showcase_3d" / "harmonia_mundi_stage.blend"
WEBM_PATH = REPO_ROOT / "output" / "showcase_3d" / "harmonia_mundi_stage.webm"
STILLS_DIR = REPO_ROOT / "output" / "showcase_3d"
TMP_FRAMES_DIR = Path("/tmp/frames_harmonia_mundi")

STAGE_RADIUS = 5.40
STAGE_TOP_Z = 0.09
ORGAN_RISER_CENTER = (0.0, 3.30)
ORGAN_RISER_RADIUS = 2.20
ORGAN_RISER_TOP_Z = 0.45
CAMERA_TARGET = (0.0, 0.45, 0.95)


def _link_exclusively(obj: bpy.types.Object, col: bpy.types.Collection) -> None:
    """Link obj only to col."""
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)


def _tune_stage_materials(mats: dict[str, bpy.types.Material]) -> None:
    """Calibrate stage wood & luminous shaders locally for rich AgX luxury with zero blowout."""
    ped_bsdf = mats["PedestalWood"].node_tree.nodes.get("Principled BSDF")
    if ped_bsdf is not None:
        ped_bsdf.inputs["Base Color"].default_value = (0.028, 0.020, 0.024, 1.0)
        ped_bsdf.inputs["Roughness"].default_value = 0.78
        ped_bsdf.inputs["Specular IOR Level"].default_value = 0.08
        ped_bsdf.inputs["Coat Weight"].default_value = 0.0

    floor_bsdf = mats["StageFloor"].node_tree.nodes.get("Principled BSDF")
    if floor_bsdf is not None:
        floor_bsdf.inputs["Roughness"].default_value = 0.34
        floor_bsdf.inputs["Specular IOR Level"].default_value = 0.32
        floor_bsdf.inputs["Coat Weight"].default_value = 0.08

    lum = mats.get("LuminousElement")
    if lum and lum.use_nodes:
        for node in lum.node_tree.nodes:
            if node.type == "MATH" and node.operation == "MULTIPLY":
                node.inputs[1].default_value = 6.2


def _build_organ_riser_mesh(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> None:
    """Build the rear semi-circular Cathedral Organ riser (top z=0.45m) with stepped brass molding."""
    cx, cy = ORGAN_RISER_CENTER
    n_seg = 96

    def _clamped_riser_ring(radius: float) -> list[tuple[float, float]]:
        pts: list[tuple[float, float]] = []
        max_stage_r = STAGE_RADIUS - 0.04
        for i in range(n_seg):
            ang = (2.0 * math.pi * i) / n_seg
            px = cx + radius * math.cos(ang)
            py = cy + radius * math.sin(ang)
            r_stage = math.hypot(px, py)
            if r_stage > max_stage_r:
                scale = max_stage_r / r_stage
                px *= scale
                py *= scale
            pts.append((px, py))
        return pts

    def _add_extruded_disk(name: str, radius: float, z0: float, z1: float, mat: bpy.types.Material) -> None:
        bm = bmesh.new()
        pts = _clamped_riser_ring(radius)
        bot = [bm.verts.new((x, y, z0)) for x, y in pts]
        top = [bm.verts.new((x, y, z1)) for x, y in pts]
        for i in range(n_seg):
            jn = (i + 1) % n_seg
            bm.faces.new((bot[i], bot[jn], top[jn], top[i]))
        bm.faces.new(list(reversed(bot)))
        bm.faces.new(top)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
        obj = bpy.data.objects.new(name, mesh)
        obj.data.materials.append(mat)
        col.objects.link(obj)
        bev = obj.modifiers.new("Bevel", "BEVEL")
        bev.width = 0.008
        bev.segments = 2

    def _add_molding_band(name: str, radius: float, z_mid: float, thick_r: float, thick_z: float) -> None:
        bm = bmesh.new()
        pts_in = _clamped_riser_ring(radius - thick_r)
        pts_out = _clamped_riser_ring(radius + thick_r * 0.4)
        z_lo = z_mid - thick_z * 0.5
        z_hi = z_mid + thick_z * 0.5
        ring_lo_out = [bm.verts.new((x, y, z_lo)) for x, y in pts_out]
        ring_hi_out = [bm.verts.new((x, y, z_hi)) for x, y in pts_out]
        ring_hi_in = [bm.verts.new((x, y, z_hi)) for x, y in pts_in]
        ring_lo_in = [bm.verts.new((x, y, z_lo)) for x, y in pts_in]
        for i in range(n_seg):
            jn = (i + 1) % n_seg
            bm.faces.new((ring_lo_out[i], ring_lo_out[jn], ring_hi_out[jn], ring_hi_out[i]))
            bm.faces.new((ring_hi_out[i], ring_hi_out[jn], ring_hi_in[jn], ring_hi_in[i]))
            bm.faces.new((ring_hi_in[i], ring_hi_in[jn], ring_lo_in[jn], ring_lo_in[i]))
            bm.faces.new((ring_lo_in[i], ring_lo_in[jn], ring_lo_out[jn], ring_lo_out[i]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
        obj = bpy.data.objects.new(name, mesh)
        obj.data.materials.append(mats["PolishedBrass"])
        col.objects.link(obj)

    # Lower riser tier (z = 0.09 .. 0.27) & upper riser tier (z = 0.27 .. 0.45)
    _add_extruded_disk("OrganRiserLower", ORGAN_RISER_RADIUS, STAGE_TOP_Z - 0.005, 0.27, mats["DarkRosewood"])
    _add_molding_band("OrganRiserBrassLower", ORGAN_RISER_RADIUS, 0.262, 0.020, 0.016)
    _add_extruded_disk("OrganRiserUpper", ORGAN_RISER_RADIUS - 0.14, 0.265, ORGAN_RISER_TOP_Z, mats["PedestalWood"])
    _add_molding_band("OrganRiserBrassUpper", ORGAN_RISER_RADIUS - 0.14, ORGAN_RISER_TOP_Z - 0.010, 0.018, 0.016)


def _build_harmonic_compass_ring(
    col: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> None:
    """Embed 53 radial brushed-gold & canonical jewel compass inlays flush at z=0.09m."""
    bm_gold = bmesh.new()
    z_inlay = STAGE_TOP_Z + 0.0008

    # Subtle concentric framing rings at r=4.58m and r=5.22m
    for r_ring, width in ((4.58, 0.014), (5.22, 0.016)):
        n_arc = 128
        r_in = r_ring - width * 0.5
        r_out = r_ring + width * 0.5
        v_in_b = [bm_gold.verts.new((r_in * math.cos(2 * math.pi * i / n_arc), r_in * math.sin(2 * math.pi * i / n_arc), STAGE_TOP_Z - 0.001)) for i in range(n_arc)]
        v_in_t = [bm_gold.verts.new((r_in * math.cos(2 * math.pi * i / n_arc), r_in * math.sin(2 * math.pi * i / n_arc), z_inlay)) for i in range(n_arc)]
        v_out_t = [bm_gold.verts.new((r_out * math.cos(2 * math.pi * i / n_arc), r_out * math.sin(2 * math.pi * i / n_arc), z_inlay)) for i in range(n_arc)]
        v_out_b = [bm_gold.verts.new((r_out * math.cos(2 * math.pi * i / n_arc), r_out * math.sin(2 * math.pi * i / n_arc), STAGE_TOP_Z - 0.001)) for i in range(n_arc)]
        for i in range(n_arc):
            jn = (i + 1) % n_arc
            bm_gold.faces.new((v_in_t[i], v_out_t[i], v_out_t[jn], v_in_t[jn]))
            bm_gold.faces.new((v_out_b[i], v_out_t[i], v_out_t[jn], v_out_b[jn]))
            bm_gold.faces.new((v_in_t[i], v_in_b[i], v_in_b[jn], v_in_t[jn]))

    canonical_steps = set(common.STEP_COLOR_MAP.keys())
    for step in range(53):
        # Place step 0 at front-center (-Y) and wrap counter-clockwise around the 53-EDO circle
        ang = -math.pi * 0.5 + (2.0 * math.pi * step) / 53.0
        is_canon = step in canonical_steps
        strip_w = 0.034 if is_canon else 0.020
        r0 = 4.58
        r1 = 5.10 if is_canon else 5.12
        r_mid = 0.5 * (r0 + r1)
        mat_rot = Matrix.Rotation(ang, 4, "Z")
        mat_pos = Matrix.Translation((r_mid * math.cos(ang), r_mid * math.sin(ang), z_inlay))
        mat_scale = Matrix.Diagonal((r1 - r0, strip_w, 0.0028, 1.0))
        bmesh.ops.create_cube(bm_gold, size=1.0, matrix=mat_pos @ mat_rot @ mat_scale)

        # Canonical & chromatic outer jewel pip embedded flush between r=5.12..5.21m
        jewel_r0 = 5.125
        jewel_r1 = 5.205
        jewel_mid = 0.5 * (jewel_r0 + jewel_r1)
        bm_j = bmesh.new()
        j_scale = Matrix.Diagonal((jewel_r1 - jewel_r0, strip_w * 1.25, 0.0032, 1.0))
        bmesh.ops.create_cube(bm_j, size=1.0, matrix=Matrix.Translation((jewel_mid * math.cos(ang), jewel_mid * math.sin(ang), z_inlay + 0.0005)) @ mat_rot @ j_scale)
        bmesh.ops.recalc_face_normals(bm_j, faces=bm_j.faces)
        j_mesh = bpy.data.meshes.new(f"CompassJewel_{step:02d}")
        bm_j.to_mesh(j_mesh)
        bm_j.free()
        j_obj = bpy.data.objects.new(f"CompassJewel_{step:02d}", j_mesh)
        j_obj.data.materials.append(mats["LuminousElement"])
        rgb = common.vivid_53edo_color(step)
        alpha = 0.36 if is_canon else 0.095
        j_obj.color = (*rgb, alpha)
        col.objects.link(j_obj)

    bmesh.ops.recalc_face_normals(bm_gold, faces=bm_gold.faces)
    gold_mesh = bpy.data.meshes.new("HarmonicCompassGoldInlay")
    bm_gold.to_mesh(gold_mesh)
    bm_gold.free()
    gold_obj = bpy.data.objects.new("HarmonicCompassGoldInlay", gold_mesh)
    gold_obj.data.materials.append(mats["BrushedGold"])
    col.objects.link(gold_obj)


def _add_spot_light(
    col: bpy.types.Collection,
    name: str,
    location: tuple[float, float, float],
    target: tuple[float, float, float],
    energy: float,
    color: tuple[float, float, float],
    spot_size_deg: float,
    spot_blend: float = 0.45,
    radius: float = 0.8,
) -> bpy.types.Object:
    ldata = bpy.data.lights.new(name=name, type="SPOT")
    ldata.energy = energy
    ldata.color = color
    ldata.spot_size = math.radians(spot_size_deg)
    ldata.spot_blend = spot_blend
    ldata.shadow_soft_size = radius
    lobj = bpy.data.objects.new(name=name, object_data=ldata)
    lobj.location = location
    direction = mathutils.Vector(target) - mathutils.Vector(location)
    lobj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    col.objects.link(lobj)
    return lobj


def build_harmonia_mundi_stage(mats: dict[str, bpy.types.Material]) -> bpy.types.Collection:
    """Build the 53-EDO Concert Hall amphitheater stage, organ riser, compass ring & lighting rig."""
    scene = bpy.context.scene
    col = bpy.data.collections.new("HarmoniaMundiStage")
    scene.collection.children.link(col)

    # 1) Broad reflective dark concert hall floor (radius=22m)
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=22.0, depth=0.04, location=(0.0, 0.0, -0.02))
    floor = bpy.context.active_object
    floor.name = "HallFloor"
    floor.data.materials.append(mats["StageFloor"])
    _link_exclusively(floor, col)

    # 2) Terraced circular mahogany-and-gold amphitheater stage (lower terrace r=5.64m, upper deck r=5.40m at z=0.09m)
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=STAGE_RADIUS + 0.24, depth=0.045, location=(0.0, 0.0, 0.0225))
    lower_terrace = bpy.context.active_object
    lower_terrace.name = "StageLowerTerrace"
    lower_terrace.data.materials.append(mats["DarkRosewood"])
    bev_l = lower_terrace.modifiers.new("Bevel", "BEVEL")
    bev_l.width = 0.010
    bev_l.segments = 2
    _link_exclusively(lower_terrace, col)

    bpy.ops.mesh.primitive_torus_add(
        major_radius=STAGE_RADIUS + 0.232,
        minor_radius=0.011,
        major_segments=96,
        minor_segments=12,
        location=(0.0, 0.0, 0.041),
    )
    lower_trim = bpy.context.active_object
    lower_trim.name = "StageLowerGoldTrim"
    lower_trim.data.materials.append(mats["BrushedGold"])
    _link_exclusively(lower_trim, col)

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=96,
        radius=STAGE_RADIUS,
        depth=STAGE_TOP_Z,
        location=(0.0, 0.0, STAGE_TOP_Z * 0.5),
    )
    stage_deck = bpy.context.active_object
    stage_deck.name = "StageMainDeck"
    stage_deck.data.materials.append(mats["PedestalWood"])
    bev = stage_deck.modifiers.new("Bevel", "BEVEL")
    bev.width = 0.012
    bev.segments = 2
    _link_exclusively(stage_deck, col)

    bpy.ops.mesh.primitive_torus_add(
        major_radius=STAGE_RADIUS - 0.008,
        minor_radius=0.013,
        major_segments=96,
        minor_segments=12,
        location=(0.0, 0.0, STAGE_TOP_Z - 0.012),
    )
    upper_trim = bpy.context.active_object
    upper_trim.name = "StageMainGoldTrim"
    upper_trim.data.materials.append(mats["BrushedGold"])
    _link_exclusively(upper_trim, col)

    # 3) Rear semi-circular Cathedral Organ riser (center=(0.0, 3.30), top at z=0.45m)
    _build_organ_riser_mesh(col, mats)

    # 4) Inlaid 53-Division Harmonic Compass Ring (radius 4.6..5.2m)
    _build_harmonic_compass_ring(col, mats)

    # 5) Concert Hall 3-Point + Architectural Uplight Rig (calibrated for AgX exposure=-0.28)
    _add_spot_light(
        col,
        "HallFrontKeySpot",
        location=(5.6, -8.2, 6.0),
        target=(0.0, 0.2, 0.9),
        energy=1650.0,
        color=(1.0, 0.91, 0.80),
        spot_size_deg=74.0,
        spot_blend=0.72,
        radius=1.6,
    )
    common._add_area_light(
        col,
        "HallIndigoFill",
        location=(-7.8, -4.8, 4.4),
        target=(0.0, 0.4, 1.0),
        energy=880.0,
        color=(0.44, 0.62, 1.0),
        size=6.0,
    )
    common._add_area_light(
        col,
        "HallOverheadWash",
        location=(0.0, -0.5, 8.6),
        target=(0.0, 0.4, 0.6),
        energy=360.0,
        color=(0.90, 0.93, 1.0),
        size=8.0,
    )
    # Warm golden architectural rim & uplights behind the Cathedral Pipe Organ
    common._add_area_light(
        col,
        "OrganBackRim",
        location=(-0.4, 7.2, 5.0),
        target=(0.0, 2.8, 1.9),
        energy=1150.0,
        color=(1.0, 0.80, 0.54),
        size=4.2,
    )
    _add_spot_light(
        col,
        "OrganUplightLeft",
        location=(-1.4, 4.35, 0.55),
        target=(-0.2, 3.65, 2.8),
        energy=260.0,
        color=(1.0, 0.78, 0.48),
        spot_size_deg=62.0,
        spot_blend=0.65,
        radius=0.35,
    )
    _add_spot_light(
        col,
        "OrganUplightRight",
        location=(1.4, 4.35, 0.55),
        target=(0.2, 3.65, 2.8),
        energy=260.0,
        color=(1.0, 0.78, 0.48),
        spot_size_deg=62.0,
        spot_blend=0.65,
        radius=0.35,
    )
    # Gentle low-angle front-side accent grazing Piano & Winds without hotspots
    _add_spot_light(
        col,
        "FrontStageAccent",
        location=(-5.2, -6.2, 3.2),
        target=(0.4, -0.2, 0.85),
        energy=540.0,
        color=(1.0, 0.90, 0.78),
        spot_size_deg=68.0,
        spot_blend=0.68,
        radius=1.2,
    )
    return col


def _synthesize_timpani_notes(organ_tl: dict[str, Any]) -> list[dict[str, Any]]:
    """Synthesize timpani strikes on deep church_organ notes (step <= -70) and downbeat roots."""
    notes = sorted(organ_tl.get("notes", []), key=lambda x: (x["start_s"], x["step"]))
    if not notes:
        return []

    # Group simultaneous organ notes into chord onsets (within 30 ms)
    groups: list[list[dict[str, Any]]] = []
    for n in notes:
        if not groups or abs(n["start_s"] - groups[-1][0]["start_s"]) > 0.03:
            groups.append([n])
        else:
            groups[-1].append(n)

    timpani_hits: list[dict[str, Any]] = []
    for grp in groups:
        deep_notes = [n for n in grp if int(n["step"]) <= -70]
        chosen = deep_notes if deep_notes else [min(grp, key=lambda n: int(n["step"]))]
        for n in chosen:
            timpani_hits.append(
                {
                    **n,
                    "track_id": "timpani",
                    "instrument": "timpani",
                    "dur_s": 0.55,
                    "end_s": n["start_s"] + 0.55,
                    "vel": max(0.78, min(1.0, float(n.get("vel", 0.7)) + 0.35)),
                }
            )
    return timpani_hits


def _verify_anchors_and_clearances(anchors: list[tuple[str, bpy.types.Object, str]]) -> None:
    """Confirm every child mesh is parented to its anchor and check pairwise horizontal clearances."""
    bpy.context.view_layer.update()
    bounds: dict[str, tuple[float, float, float, float, float, float]] = {}

    for label, anchor, col_name in anchors:
        col = bpy.data.collections.get(col_name)
        assert col is not None, f"Missing collection {col_name}"
        xs: list[float] = []
        ys: list[float] = []
        zs: list[float] = []
        unparented: list[str] = []
        for obj in col.objects:
            if obj is anchor:
                continue
            root = obj
            while root.parent is not None:
                root = root.parent
            if root is not anchor:
                unparented.append(obj.name)
            if obj.type == "MESH":
                # Ignore parked pluck beads below stage z=0 in idle frame
                world_pts = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
                if max(p.z for p in world_pts) < 0.05:
                    continue
                for p in world_pts:
                    xs.append(p.x)
                    ys.append(p.y)
                    zs.append(p.z)
        if unparented:
            raise RuntimeError(f"Objects not parented to {anchor.name}: {unparented}")
        ab = (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))
        bounds[label] = ab
        print(
            f"[stage_mundi] {label:8s} anchor={tuple(round(v, 2) for v in anchor.location)} "
            f"X=[{ab[0]:.2f},{ab[1]:.2f}] Y=[{ab[2]:.2f},{ab[3]:.2f}] Z=[{ab[4]:.2f},{ab[5]:.2f}]"
        )

    labels = [a[0] for a in anchors]
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            a, b = bounds[labels[i]], bounds[labels[j]]
            dx = max(a[0] - b[1], b[0] - a[1])
            dy = max(a[2] - b[3], b[2] - a[3])
            gap = max(dx, dy)
            if gap < 0.0:
                print(f"[stage_mundi] WARNING: AABB overlap {labels[i]} <-> {labels[j]} (dx={dx:.2f}, dy={dy:.2f})")


def _setup_stage_camera(total_frames: int, fps: int = 24) -> bpy.types.Object:
    """Configure 35s 3-phase cinematic camera choreography tracking (0.0, 0.45, 0.95)."""
    tx, ty, _ = CAMERA_TARGET

    def polar(az_deg: float, dist: float, z: float) -> tuple[float, float, float]:
        rad = math.radians(az_deg)
        return (tx + dist * math.sin(rad), ty - dist * math.cos(rad), z)

    def tf(sec_frac: float) -> int:
        return max(1, min(total_frames, round(sec_frac * (total_frames - 1)) + 1))

    # Scale smoothly with total_frames (default 35s = 840 frames)
    keyframes = [
        (1, polar(-13.0, 7.65, 2.38)),               # 0.0s establishing front-left sweep (all 7 visible)
        (tf(7.0 / 35.0), polar(-4.0, 7.90, 2.34)),   # 7.0s front-center sweep past Piano/Viol/Guitar/Sitar
        (tf(14.0 / 35.0), polar(14.0, 7.80, 2.58)),  # 14.0s front-right sweep across Harp/Sitar/Winds
        (tf(20.0 / 35.0), polar(6.0, 8.60, 3.10)),   # 20.0s crane pull-back as Organ & Horn enter
        (tf(24.0 / 35.0), polar(2.0, 9.25, 3.52)),   # 24.0s rising overview
        (tf(31.0 / 35.0), polar(1.5, 9.85, 3.78)),   # 31.0s grand finale overview (all 7 & full 53-ring framed)
        (total_frames, polar(-6.0, 9.95, 3.84)),     # 35.0s final orchestral vista
    ]

    # Deduplicate frame indices if someone passes a very short --duration-sec
    seen: set[int] = set()
    unique_kf: list[tuple[int, tuple[float, float, float]]] = []
    for fnum, loc in keyframes:
        if fnum not in seen:
            seen.add(fnum)
            unique_kf.append((fnum, loc))

    return common.setup_orbit_camera(
        CAMERA_TARGET,
        unique_kf,
        lens_mm=34.0,
        dof_fstop=8.0,
    )


def build_scene(
    *,
    start_s: float = 222.0,
    dur_s: float = 35.0,
    full: bool = False,
) -> tuple[dict[str, Any], Path]:
    """Assemble the complete 7-instrument Harmonia Mundi Concert Hall Stage & timeline."""
    fps = 24
    scene = common.reset_scene(fps=fps, res_x=1920, res_y=1080, taa_samples=8)
    scene.view_settings.exposure = -0.28

    mats = common.create_studio_materials()
    _tune_stage_materials(mats)
    build_harmonia_mundi_stage(mats)

    wav_path = FULL_WAV_PATH if (full or not EXCERPT_WAV_PATH.exists()) else EXCERPT_WAV_PATH
    ref_wav_for_load = FULL_WAV_PATH if FULL_WAV_PATH.exists() else wav_path
    full_tl = common.load_score_timeline(SCORE_PATH, ref_wav_for_load, fps=fps)

    if full:
        start_s = 0.0
        dur_s = float(full_tl["duration_s"])
        win_tl = full_tl
    else:
        win_tl = common.slice_timeline(full_tl, start_s, dur_s)

    total_frames = int(win_tl["total_frames"])
    scene.frame_start = 1
    scene.frame_end = total_frames

    # 1) Rear Center Riser: Organ & Timpani (organ + synthesized timpani hits)
    organ_tl = common.slice_timeline(full_tl, start_s, dur_s, track_ids={"church_organ"})
    organ_tl["notes"] = sorted(
        list(organ_tl["notes"]) + _synthesize_timpani_notes(organ_tl),
        key=lambda x: (x["start_s"], x["step"]),
    )
    anchor_organ = organ_timpani_53edo.build_instrument(
        mats,
        organ_tl,
        collection_name="OrganTimpani53EDO",
        anchor_location=(0.0, 3.30, 0.36),
        anchor_rotation_z_deg=0.0,
    )

    # 2) Front-Left: Bosanquet 53-EDO Concert Grand Piano
    anchor_piano = piano_bosanquet.build_instrument(
        mats,
        common.slice_timeline(full_tl, start_s, dur_s, track_ids={"piano"}),
        collection_name="BosanquetPiano",
        anchor_location=(-2.80, -1.25, 0.0),
        anchor_rotation_z_deg=32.0,
    )

    # 3) Front-Right: Alexandrian 53-EDO Arch-Harp
    anchor_harp = harp_53edo.build_instrument(
        mats,
        common.slice_timeline(full_tl, start_s, dur_s, track_ids={"harp"}),
        collection_name="AlexandrianArchHarp",
        anchor_location=(2.75, -1.00, 0.0),
        anchor_rotation_z_deg=-32.0,
    )

    # 4) Front-Center-Left: Concert Viol Duo (Cello + Viola)
    anchor_viol = viol_53edo.build_instrument(
        mats,
        common.slice_timeline(full_tl, start_s, dur_s, track_ids={"cello", "viola", "string_ensemble"}),
        collection_name="ConcertViolDuo",
        anchor_location=(-1.05, -1.85, 0.0),
        anchor_rotation_z_deg=16.0,
    )

    # 5) Front-Center-Right: 53-Fret Concert Guitar (Dotara + Pizzicato)
    anchor_guitar = guitar_53edo.build_instrument(
        mats,
        common.slice_timeline(full_tl, start_s, dur_s, track_ids={"dotara", "pizzicato"}),
        collection_name="Guitar53EDO",
        anchor_location=(1.00, -1.75, 0.0),
        anchor_rotation_z_deg=-18.0,
    )

    # 6) Mid-Right: 22-Shruti Sitar & Gourd Ektara
    anchor_sitar = sitar_shruti_53edo.build_instrument(
        mats,
        common.slice_timeline(full_tl, start_s, dur_s, track_ids={"sitar", "ektara"}),
        collection_name="SitarShruti53EDO",
        anchor_location=(2.35, 0.95, 0.0),
        anchor_rotation_z_deg=-38.0,
    )

    # 7) Mid-Left: Woodwind & Brass Consort (Clarinet, English Horn, French Horn, Bassoon)
    anchor_winds = winds_brass_53edo.build_instrument(
        mats,
        common.slice_timeline(full_tl, start_s, dur_s, track_ids={"clarinet", "english_horn", "french_horn", "bassoon"}),
        collection_name="WindsBrassConsort",
        anchor_location=(-2.40, 0.95, 0.0),
        anchor_rotation_z_deg=24.0,
    )

    _verify_anchors_and_clearances(
        [
            ("organ", anchor_organ, "OrganTimpani53EDO"),
            ("piano", anchor_piano, "BosanquetPiano"),
            ("harp", anchor_harp, "AlexandrianArchHarp"),
            ("viol", anchor_viol, "ConcertViolDuo"),
            ("guitar", anchor_guitar, "Guitar53EDO"),
            ("sitar", anchor_sitar, "SitarShruti53EDO"),
            ("winds", anchor_winds, "WindsBrassConsort"),
        ]
    )

    _setup_stage_camera(total_frames, fps=fps)
    return win_tl, wav_path


def _parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description="Build & render Harmonia Mundi 53-EDO Concert Stage.")
    parser.add_argument("--start-sec", type=float, default=222.0, help="Excerpt start second in sample_5min.json")
    parser.add_argument("--duration-sec", type=float, default=35.0, help="Excerpt duration in seconds")
    parser.add_argument("--full", action="store_true", help="Render full sample_5min.json timeline")
    parser.add_argument("--stills-only", action="store_true", help="Save .blend and render 4 diagnostic PNGs")
    parser.add_argument("--render-video", action="store_true", help="Render full VP9+Opus .webm video")
    return parser.parse_args(argv)


def main() -> None:
    args = _parse_args()
    timeline, wav_path = build_scene(
        start_s=args.start_sec,
        dur_s=args.duration_sec,
        full=args.full,
    )
    total_frames = int(timeline["total_frames"])
    fps = int(timeline["fps"])

    common.save_blend(BLEND_PATH)
    print(f"[stage_mundi] Saved {BLEND_PATH} (total_frames={total_frames}, fps={fps}, wav={wav_path})")

    if args.stills_only:
        frame_specs = [
            ("establishing", 1),
            ("bridge", common.sec_to_frame(7.5, fps)),
            ("organ", common.sec_to_frame(21.0, fps)),
            ("finale", common.sec_to_frame(31.5, fps)),
        ]
        t0 = time.perf_counter()
        rendered = common.render_diagnostic_stills(frame_specs, STILLS_DIR, "diag_mundi")
        elapsed = time.perf_counter() - t0
        per_frame = elapsed / max(1, len(rendered))
        print(
            f"[stage_mundi] Rendered {len(rendered)} diagnostic stills in {elapsed:.2f}s "
            f"({per_frame:.2f}s/frame): {[str(p) for p in rendered]}"
        )
    elif args.render_video:
        common.render_video(WEBM_PATH, wav_path, total_frames, TMP_FRAMES_DIR, fps=fps)


if __name__ == "__main__":
    main()
