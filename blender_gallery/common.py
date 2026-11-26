"""Shared Blender 4.2 EEVEE Next studio rig, materials, timeline & render helpers."""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any

import bpy
import mathutils


STEP_COLOR_MAP: dict[int, tuple[float, float, float]] = {
    0: (0.95, 0.14, 0.20),   # Tonic / Octave: Ruby
    5: (0.98, 0.56, 0.08),   # Whole-step / 5-step: Amber
    17: (0.10, 0.86, 0.40),  # Just Major 3rd (5/4): Emerald
    31: (0.16, 0.54, 0.98),  # Just Fifth (3/2): Sapphire
    43: (0.68, 0.24, 0.96),  # Septimal Seventh: Amethyst
}
DEFAULT_GOLD_COLOR: tuple[float, float, float] = (0.96, 0.52, 0.08)


def color_for_53edo_step(step: int) -> tuple[float, float, float]:
    """Return an RGB tuple identifying canonical 53-EDO pitch classes."""
    return STEP_COLOR_MAP.get(step % 53, DEFAULT_GOLD_COLOR)


def vivid_53edo_color(step: int) -> tuple[float, float, float]:
    """Return a deeply saturated AgX-safe RGB jewel hue for every 53-EDO step."""
    pc = step % 53
    if pc in STEP_COLOR_MAP:
        return STEP_COLOR_MAP[pc]
    # Smooth HSV wheel across remaining 53 steps, high saturation (0.88) & vivid value (0.95)
    hue = (pc / 53.0) % 1.0
    col = mathutils.Color()
    col.hsv = (hue, 0.88, 0.95)
    return (col.r, col.g, col.b)


def fold_step_to_range(step: int, step_min: int, step_max: int) -> int:
    """Octave-fold a 53-EDO pitch step by multiples of 53 into [step_min, step_max]."""
    s = int(step)
    while s < step_min:
        s += 53
    while s > step_max:
        s -= 53
    return max(step_min, min(step_max, s))


def reset_scene(
    fps: int = 24,
    res_x: int = 1920,
    res_y: int = 1080,
    taa_samples: int = 8,
) -> bpy.types.Scene:
    """Reset Blender to a clean factory state configured for fast EEVEE Next GPU renders."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.eevee.taa_render_samples = taa_samples
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100
    scene.render.fps = fps
    scene.render.fps_base = 1.0
    scene.frame_start = 1

    # World: dark midnight concert hall atmosphere
    world = bpy.data.worlds.new("ConcertNightWorld")
    scene.world = world
    world.use_nodes = True
    wnodes = world.node_tree.nodes
    wlinks = world.node_tree.links
    bg = wnodes.get("Background")
    if bg is not None:
        bg.inputs["Color"].default_value = (0.008, 0.011, 0.020, 1.0)
        bg.inputs["Strength"].default_value = 1.0

    # Color management: AgX handles bright emissive pluck blooms cleanly
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = -0.28

    # GPU Compositor with FOG_GLOW glare (Blender 4.2 replacement for eevee.use_bloom)
    scene.render.compositor_device = "GPU"
    scene.use_nodes = True
    tree = scene.node_tree
    rl = tree.nodes.get("Render Layers")
    comp = tree.nodes.get("Composite")
    if rl is not None and comp is not None:
        glare = tree.nodes.new("CompositorNodeGlare")
        glare.glare_type = "FOG_GLOW"
        glare.quality = "MEDIUM"
        glare.threshold = 1.10
        glare.size = 6
        w_out = rl.outputs["Image"]
        tree.links.new(w_out, glare.inputs["Image"])
        tree.links.new(glare.outputs["Image"], comp.inputs["Image"])

    return scene


def _make_principled(
    name: str,
    base_color: tuple[float, float, float, float],
    metallic: float = 0.0,
    roughness: float = 0.4,
    specular: float = 0.5,
    coat_weight: float = 0.0,
    coat_roughness: float = 0.08,
) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = base_color
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Specular IOR Level"].default_value = specular
        bsdf.inputs["Coat Weight"].default_value = coat_weight
        bsdf.inputs["Coat Roughness"].default_value = coat_roughness
    return mat


def _make_luminous_element_material(
    name: str = "LuminousElement",
    max_emission_strength: float = 7.5,
    roughness: float = 0.22,
    metallic: float = 0.40,
) -> bpy.types.Material:
    """Create ONE shared shader reading per-object Object Info Color (RGB) + Alpha (glow)."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    obj_info = nodes.new("ShaderNodeObjectInfo")
    mult = nodes.new("ShaderNodeMath")
    mult.operation = "MULTIPLY"
    mult.inputs[1].default_value = max_emission_strength

    if bsdf is not None:
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Specular IOR Level"].default_value = 0.6
        links.new(obj_info.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(obj_info.outputs["Color"], bsdf.inputs["Emission Color"])
        links.new(obj_info.outputs["Alpha"], mult.inputs[0])
        links.new(mult.outputs["Value"], bsdf.inputs["Emission Strength"])
    return mat


def create_studio_materials() -> dict[str, bpy.types.Material]:
    """Create and return the shared PBR material palette."""
    return {
        "BrushedGold": _make_principled(
            "BrushedGold", (0.86, 0.66, 0.24, 1.0), metallic=0.95, roughness=0.22
        ),
        "PolishedBrass": _make_principled(
            "PolishedBrass", (0.92, 0.74, 0.30, 1.0), metallic=0.98, roughness=0.14
        ),
        "CastIronGold": _make_principled(
            "CastIronGold", (0.62, 0.48, 0.20, 1.0), metallic=0.86, roughness=0.34
        ),
        "DarkRosewood": _make_principled(
            "DarkRosewood",
            (0.11, 0.032, 0.016, 1.0),
            roughness=0.20,
            coat_weight=0.45,
            coat_roughness=0.06,
        ),
        "WarmMahogany": _make_principled(
            "WarmMahogany",
            (0.20, 0.062, 0.024, 1.0),
            roughness=0.24,
            coat_weight=0.35,
        ),
        "GlossEbony": _make_principled(
            "GlossEbony",
            (0.014, 0.014, 0.018, 1.0),
            roughness=0.06,
            specular=0.68,
            coat_weight=0.88,
            coat_roughness=0.03,
        ),
        "AntiqueSpruce": _make_principled(
            "AntiqueSpruce",
            (0.62, 0.42, 0.20, 1.0),
            roughness=0.30,
            coat_weight=0.28,
        ),
        "IvoryKey": _make_principled(
            "IvoryKey",
            (0.62, 0.58, 0.50, 1.0),
            roughness=0.26,
            coat_weight=0.20,
        ),
        "CopperString": _make_principled(
            "CopperString", (0.82, 0.44, 0.22, 1.0), metallic=0.92, roughness=0.18
        ),
        "HammeredCopper": _make_principled(
            "HammeredCopper", (0.84, 0.40, 0.18, 1.0), metallic=0.94, roughness=0.24
        ),
        "SilverMetal": _make_principled(
            "SilverMetal", (0.82, 0.84, 0.88, 1.0), metallic=0.96, roughness=0.18
        ),
        "PewterMetal": _make_principled(
            "PewterMetal", (0.58, 0.60, 0.64, 1.0), metallic=0.92, roughness=0.28
        ),
        "Grenadilla": _make_principled(
            "Grenadilla",
            (0.032, 0.024, 0.020, 1.0),
            roughness=0.18,
            coat_weight=0.35,
        ),
        "CalfskinHead": _make_principled(
            "CalfskinHead",
            (0.74, 0.66, 0.50, 1.0),
            roughness=0.48,
            specular=0.35,
        ),
        "Horsehair": _make_principled(
            "Horsehair",
            (0.84, 0.80, 0.70, 1.0),
            roughness=0.44,
        ),
        "StageFloor": _make_principled(
            "StageFloor",
            (0.015, 0.018, 0.028, 1.0),
            roughness=0.24,
            specular=0.48,
            coat_weight=0.14,
        ),
        "PedestalWood": _make_principled(
            "PedestalWood",
            (0.040, 0.030, 0.036, 1.0),
            roughness=0.42,
            specular=0.35,
            coat_weight=0.08,
        ),
        "LuminousElement": _make_luminous_element_material(),
    }


def _add_area_light(
    collection: bpy.types.Collection,
    name: str,
    location: tuple[float, float, float],
    target: tuple[float, float, float],
    energy: float,
    color: tuple[float, float, float],
    size: float,
) -> bpy.types.Object:
    ldata = bpy.data.lights.new(name=name, type="AREA")
    ldata.energy = energy
    ldata.color = color
    ldata.size = size
    lobj = bpy.data.objects.new(name=name, object_data=ldata)
    lobj.location = location
    direction = mathutils.Vector(target) - mathutils.Vector(location)
    lobj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    collection.objects.link(lobj)
    return lobj


def build_concert_stage(
    mats: dict[str, bpy.types.Material],
    pedestal_radius: float = 1.65,
    pedestal_height: float = 0.09,
    light_target_z: float = 0.95,
) -> bpy.types.Collection:
    """Create concert floor, stepped midnight plinth with gold trim, and 4-light studio rig."""
    scene = bpy.context.scene
    col = bpy.data.collections.new("ConcertStage")
    scene.collection.children.link(col)

    # Reflective floor disk
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=16.0, depth=0.04, location=(0.0, 0.0, -0.02))
    floor = bpy.context.active_object
    floor.name = "StageFloor"
    floor.data.materials.append(mats["StageFloor"])
    for c in list(floor.users_collection):
        c.objects.unlink(floor)
    col.objects.link(floor)

    # Main cylindrical plinth
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=64,
        radius=pedestal_radius,
        depth=pedestal_height,
        location=(0.0, 0.0, pedestal_height * 0.5),
    )
    plinth = bpy.context.active_object
    plinth.name = "ConcertPedestal"
    plinth.data.materials.append(mats["PedestalWood"])
    bev = plinth.modifiers.new("Bevel", "BEVEL")
    bev.width = 0.012
    bev.segments = 2
    for c in list(plinth.users_collection):
        c.objects.unlink(plinth)
    col.objects.link(plinth)

    # Brushed gold trim ring near top of plinth
    bpy.ops.mesh.primitive_torus_add(
        major_radius=pedestal_radius - 0.008,
        minor_radius=0.009,
        major_segments=64,
        minor_segments=12,
        location=(0.0, 0.0, pedestal_height - 0.012),
    )
    ring = bpy.context.active_object
    ring.name = "PedestalGoldTrim"
    ring.data.materials.append(mats["BrushedGold"])
    for c in list(ring.users_collection):
        c.objects.unlink(ring)
    col.objects.link(ring)

    target = (0.0, 0.0, light_target_z)
    _add_area_light(col, "KeyLight", (3.6, -3.8, 3.4), target, energy=780.0, color=(1.0, 0.93, 0.85), size=3.0)
    _add_area_light(col, "FillLight", (-4.2, -2.5, 2.5), target, energy=380.0, color=(0.58, 0.76, 1.0), size=3.6)
    _add_area_light(col, "RimLight", (-1.8, 4.2, 3.0), target, energy=760.0, color=(1.0, 0.84, 0.64), size=2.8)
    _add_area_light(col, "TopAccent", (0.2, 0.4, 4.4), target, energy=440.0, color=(0.92, 0.95, 1.0), size=3.4)
    return col


def load_score_timeline(
    score_json_path: str | Path,
    wav_path: str | Path,
    fps: int = 24,
) -> dict[str, Any]:
    """Parse score JSON events and WAV duration into exact second & frame timelines."""
    score_path = Path(score_json_path)
    audio_path = Path(wav_path)
    with score_path.open("r", encoding="utf-8") as f:
        score = json.load(f)

    with wave.open(str(audio_path), "rb") as wf:
        wav_dur_s = wf.getnframes() / float(wf.getframerate())

    tempo_pts = sorted(score.get("tempo", [{"beat": 0.0, "bpm": 120.0}]), key=lambda x: x["beat"])

    def beat_to_sec(beat: float) -> float:
        if beat <= 0.0:
            return 0.0
        elapsed = 0.0
        cur_beat = 0.0
        cur_bpm = float(tempo_pts[0]["bpm"])
        for pt in tempo_pts:
            pt_b = float(pt["beat"])
            if pt_b <= cur_beat:
                cur_bpm = float(pt["bpm"])
                continue
            if beat <= pt_b:
                elapsed += (beat - cur_beat) * (60.0 / cur_bpm)
                return elapsed
            elapsed += (pt_b - cur_beat) * (60.0 / cur_bpm)
            cur_beat = pt_b
            cur_bpm = float(pt["bpm"])
        elapsed += (beat - cur_beat) * (60.0 / cur_bpm)
        return elapsed

    notes: list[dict[str, Any]] = []
    pedals: list[dict[str, Any]] = []
    for tr in score.get("tracks", []):
        tid = tr.get("id", "")
        inst = tr.get("instrument", "")
        for p in tr.get("pedals", []):
            sb = float(p["beat"])
            db = float(p["dur"])
            s_t = beat_to_sec(sb)
            e_t = beat_to_sec(sb + db)
            pedals.append({"track_id": tid, "start_s": s_t, "end_s": e_t})
        for n in tr.get("notes", []):
            sb = float(n["beat"])
            db = float(n["dur"])
            s_t = beat_to_sec(sb)
            e_t = beat_to_sec(sb + db)
            notes.append(
                {
                    "track_id": tid,
                    "instrument": inst,
                    "step": int(n["step"]),
                    "vel": float(n.get("vel", 0.8)),
                    "start_s": s_t,
                    "end_s": e_t,
                    "dur_s": max(0.04, e_t - s_t),
                    "slide_from_cents": float(n.get("slide_from_cents", 0.0)),
                    "swell": n.get("swell"),
                    "vibrato": float(n.get("vibrato", 0.0)),
                }
            )

    notes.sort(key=lambda x: (x["start_s"], x["step"]))
    pedals.sort(key=lambda x: x["start_s"])
    total_frames = max(1, math.ceil(wav_dur_s * fps))
    bpy.context.scene.frame_end = total_frames
    return {
        "title": score.get("title", score_path.stem),
        "duration_s": wav_dur_s,
        "fps": fps,
        "total_frames": total_frames,
        "notes": notes,
        "pedals": pedals,
    }


def sec_to_frame(sec: float, fps: int = 24) -> int:
    """Convert timeline seconds to 1-based Blender frame index."""
    return max(1, round(sec * fps) + 1)


def slice_timeline(
    timeline: dict[str, Any],
    start_s: float,
    dur_s: float,
    *,
    track_ids: set[str] | None = None,
    instrument_names: set[str] | None = None,
) -> dict[str, Any]:
    """Filter timeline events to [start_s, start_s + dur_s] and specific tracks/instruments."""
    win_end = start_s + dur_s
    fps = int(timeline.get("fps", 24))
    out_notes: list[dict[str, Any]] = []
    out_pedals: list[dict[str, Any]] = []

    def _matches(ev: dict[str, Any]) -> bool:
        if track_ids is not None and ev.get("track_id") not in track_ids:
            return False
        if instrument_names is not None and ev.get("instrument") not in instrument_names:
            return False
        return True

    for n in timeline.get("notes", []):
        if not _matches(n):
            continue
        if n["end_s"] <= start_s or n["start_s"] >= win_end:
            continue
        ns = max(0.0, n["start_s"] - start_s)
        ne = min(dur_s, n["end_s"] - start_s)
        if ne <= ns:
            continue
        out_notes.append(
            {
                **n,
                "start_s": ns,
                "end_s": ne,
                "dur_s": max(0.04, ne - ns),
            }
        )

    for p in timeline.get("pedals", []):
        if track_ids is not None and p.get("track_id") not in track_ids:
            continue
        if p["end_s"] <= start_s or p["start_s"] >= win_end:
            continue
        ps = max(0.0, p["start_s"] - start_s)
        pe = min(dur_s, p["end_s"] - start_s)
        if pe <= ps:
            continue
        out_pedals.append({**p, "start_s": ps, "end_s": pe})

    return {
        "title": timeline.get("title", ""),
        "duration_s": dur_s,
        "fps": fps,
        "total_frames": max(1, math.ceil(dur_s * fps)),
        "notes": out_notes,
        "pedals": out_pedals,
    }


def parent_collection_to_anchor(
    col: bpy.types.Collection,
    anchor_name: str,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation_z_deg: float = 0.0,
    scale: float = 1.0,
) -> bpy.types.Object:
    """Attach all top-level objects in col to an anchor Empty so stage placement preserves keyframes."""
    anchor = bpy.data.objects.new(anchor_name, None)
    anchor.empty_display_type = "PLAIN_AXES"
    anchor.location = location
    anchor.rotation_euler = (0.0, 0.0, math.radians(rotation_z_deg))
    anchor.scale = (scale, scale, scale)
    col.objects.link(anchor)

    ident = mathutils.Matrix.Identity(4)
    for obj in list(col.objects):
        if obj is anchor or obj.parent is not None:
            continue
        obj.parent = anchor
        obj.matrix_parent_inverse = ident.copy()
    return anchor


def set_constant_segment(obj_or_id: Any, data_path: str, index: int, frames: set[int]) -> None:
    """Force CONSTANT interpolation on specified keyframe X-coordinates so glow never ramps early."""
    ad = obj_or_id.animation_data
    if not ad or not ad.action:
        return
    for fc in ad.action.fcurves:
        if fc.data_path == data_path and (index < 0 or fc.array_index == index):
            for kp in fc.keyframe_points:
                if int(round(kp.co.x)) in frames:
                    kp.interpolation = "CONSTANT"


def setup_orbit_camera(
    target_pos: tuple[float, float, float],
    keyframes_cam_loc: list[tuple[int, tuple[float, float, float]]],
    lens_mm: float = 42.0,
    dof_fstop: float = 5.6,
) -> bpy.types.Object:
    """Create a tracked studio camera with smooth BEZIER orbit/push-in keyframes."""
    scene = bpy.context.scene
    target_empty = bpy.data.objects.new("CameraTarget", None)
    target_empty.empty_display_type = "PLAIN_AXES"
    target_empty.location = target_pos
    scene.collection.objects.link(target_empty)

    cam_data = bpy.data.cameras.new("ShowcaseCamera")
    cam_data.lens = lens_mm
    cam_data.clip_start = 0.05
    cam_data.clip_end = 100.0
    cam_data.dof.use_dof = True
    cam_data.dof.focus_object = target_empty
    cam_data.dof.aperture_fstop = dof_fstop

    cam_obj = bpy.data.objects.new("ShowcaseCamera", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    track = cam_obj.constraints.new(type="TRACK_TO")
    track.target = target_empty
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    for frame_num, loc in keyframes_cam_loc:
        cam_obj.location = loc
        cam_obj.keyframe_insert(data_path="location", frame=frame_num)

    if cam_obj.animation_data and cam_obj.animation_data.action:
        for fc in cam_obj.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"
    return cam_obj


def save_blend(blend_path: str | Path) -> Path:
    """Pack minimal data and save .blend scene."""
    out = Path(blend_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    return out


def render_diagnostic_stills(
    frame_specs: list[tuple[str, int]],
    out_dir: str | Path,
    prefix: str,
) -> list[Path]:
    """Render specific diagnostic frames as lossless PNG stills for visual inspection."""
    scene = bpy.context.scene
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    prev_fmt = scene.render.image_settings.file_format
    prev_filepath = scene.render.filepath
    scene.render.image_settings.file_format = "PNG"

    rendered: list[Path] = []
    for tag, frame_num in frame_specs:
        clamped = max(scene.frame_start, min(scene.frame_end, int(frame_num)))
        dst = out_path / f"{prefix}_{tag}.png"
        scene.frame_set(clamped)
        scene.render.filepath = str(dst)
        bpy.ops.render.render(write_still=True)
        rendered.append(dst)

    scene.render.image_settings.file_format = prev_fmt
    scene.render.filepath = prev_filepath
    return rendered


def render_video(
    out_webm: str | Path,
    wav_path: str | Path,
    total_frames: int,
    tmp_frames_dir: str | Path,
    fps: int = 24,
    keep_frames: bool = False,
) -> Path:
    """Render JPEG Q96 sequence in EEVEE Next GPU, encode VP9+Opus .webm, and verify."""
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = total_frames

    frames_dir = Path(tmp_frames_dir)
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)

    webm_path = Path(out_webm)
    webm_path.parent.mkdir(parents=True, exist_ok=True)

    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 96
    scene.render.filepath = str(frames_dir / "frame_")
    bpy.ops.render.render(animation=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
        "-i",
        str(frames_dir / "frame_%04d.jpg"),
        "-i",
        str(wav_path),
        "-c:v",
        "libvpx-vp9",
        "-crf",
        "24",
        "-b:v",
        "0",
        "-row-mt",
        "1",
        "-tile-columns",
        "2",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "libopus",
        "-b:a",
        "192k",
        "-shortest",
        str(webm_path),
    ]
    subprocess.run(cmd, check=True)
    if not keep_frames and frames_dir.exists():
        shutil.rmtree(frames_dir)

    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=codec_name,width,height,r_frame_rate",
            "-of",
            "default=noprint_wrappers=1",
            str(webm_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    print(f"[render_video] Verified {webm_path}:\n{probe.stdout.strip()}")
    return webm_path
