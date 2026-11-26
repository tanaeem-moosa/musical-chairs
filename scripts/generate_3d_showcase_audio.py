#!/usr/bin/env python3
"""
Generate 8 synchronized 12-15s 53-EDO showcase scores (`scores/showcase_3d/*.json`)
and render their stereo WAVs (`output/showcase_3d/*.wav`) for the Blender 3D Instrument Gallery.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "target/x86_64-unknown-linux-musl/release/edo53_music"
SCORES_DIR = ROOT / "scores" / "showcase_3d"
OUT_DIR = ROOT / "output" / "showcase_3d"

OCT = 53
P4 = 22
P5 = 31
M2 = 9
M3 = 17
m3 = 14
M6 = 39
M7 = 48
HARM_7 = 43
U11 = 24
T13 = 37
SEMI = 5  # 16:15


def make_score(
    stem: str,
    title: str,
    description: str,
    bpm: float,
    tracks: List[Dict],
    tail_seconds: float = 1.5,
) -> Path:
    SCORES_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "title": title,
        "description": description,
        "sample_rate": 48000,
        "tail_seconds": tail_seconds,
        "reverb_rt60": 2.1,
        "end_silence_seconds": 0.4,
        "tempo": [{"beat": 0.0, "bpm": bpm}],
        "tracks": tracks,
    }
    path = SCORES_DIR / f"{stem}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def note(
    beat: float,
    dur: float,
    step: int,
    vel: float = 0.78,
    *,
    slide_from_cents: float = 0.0,
    swell: Optional[str] = None,
    vibrato: float = 0.0,
) -> Dict:
    d: Dict = {
        "beat": round(beat, 4),
        "dur": round(dur, 4),
        "step": int(step),
        "vel": round(max(0.08, min(0.95, vel)), 3),
    }
    if abs(slide_from_cents) > 0.01:
        d["slide_from_cents"] = round(slide_from_cents, 2)
    if swell:
        d["swell"] = swell
    if vibrato > 0.0:
        d["vibrato"] = round(vibrato, 2)
    return d


def build_01_harp() -> Path:
    # ~13.0s at 104 BPM: Full 53-step ascending octave glissando (0..53) + luminous 4:5:6:7:9 arpeggiated chords
    bpm = 104.0
    notes: List[Dict] = []
    # 0.0..10.6b (~6.1s): All 54 steps (0..53) in flowing 53-EDO cascade
    for s in range(54):
        b = 0.25 + s * 0.18
        is_prime_accent = s in (0, 5, 17, 31, 37, 43, 53)
        vel = 0.84 if is_prime_accent else (0.64 + 0.12 * ((s % 5) / 4.0))
        notes.append(note(b, 1.45 if is_prime_accent else 0.75, s - OCT, vel))

    # 10.6..21.5b (~6.3s): 4:5:6:7:9 & 11-limit rolled chords
    chords = [
        (10.8, 3.0, [0 - OCT, 31 - OCT, 0, 17, 31, 43, 62], 0.80),  # C dom9 (4:5:6:7:9)
        (14.0, 3.0, [22 - OCT, 0, 22, 39, 53, 70, 77], 0.82),      # F maj6/11
        (17.2, 4.2, [0 - OCT, 31 - OCT, 0, 17, 31, 53, 70, 84], 0.86),  # Radiant C 4:5:6 crown
    ]
    pedals = []
    for c_start, c_dur, steps, vel in chords:
        pedals.append({"beat": round(c_start, 3), "dur": round(c_dur - 0.12, 3)})
        for j, st in enumerate(steps):
            notes.append(note(c_start + j * 0.11, c_dur - j * 0.11, st, vel - 0.02 * (j % 3)))

    return make_score(
        "01_harp_53edo",
        "The Alexandrian 53-String-Per-Octave Arch-Harp",
        "Full 53-step microtonal octave sweep (0..53) followed by beatless 4:5:6:7:9 arpeggios.",
        bpm,
        [{"id": "harp", "name": "53-EDO Arch-Harp", "instrument": "harp", "pedals": pedals, "notes": notes}],
    )


def build_02_guitar() -> Path:
    # ~13.0s at 116 BPM: Rapid campanella intra-semitone cascade + ringing 6-string Eagle-53 chords
    bpm = 116.0
    steel_notes: List[Dict] = []
    nylon_notes: List[Dict] = []

    # 0.0..12.0b: Campanella cascade hopping 1-2 commas inside single 12-TET semitone buckets!
    # {-1,0,+1}, {16,17,18}, {30,31,32}, {42,43,44}
    pat = [-1, 17, 31, 0, 18, 32, +1, 43, 17, 30, 53, 44]
    for cyc in range(4):
        base_b = cyc * 3.0
        for j, st in enumerate(pat):
            b = base_b + j * 0.24
            target = steel_notes if j % 2 == 0 else nylon_notes
            target.append(note(b, 1.35, st - (OCT if st > 35 else 0), 0.72 + 0.03 * cyc))

    # 12.4..24.0b: Ringing 6-string Eagle-53 chords (C 4:5:6:7, Ab++ Maj [38,2,16], E 4:5:6)
    g_chords = [
        (12.5, 3.6, [-53, -22, 0, 17, 31, 43], steel_notes, 0.80),   # C7 (4:5:6:7)
        (16.3, 3.6, [-68, -37, -15, 2, 16, 38], nylon_notes, 0.82),  # Ab++ Major ([38,2,16] diesis!)
        (20.1, 4.2, [-49, -18, 4, 21, 35, 57], steel_notes, 0.84),   # E+ 4:5:6 bright crown
    ]
    for c_start, c_dur, steps, target, vel in g_chords:
        for j, st in enumerate(steps):
            target.append(note(c_start + j * 0.08, c_dur - j * 0.08, st, vel))

    return make_score(
        "02_guitar_53edo",
        "The 53-Fret Logarithmic Concert Guitar",
        "Discrete micro-fretted campanella cascades inside single 12-TET semitones & ringing 53-EDO chords.",
        bpm,
        [
            {"id": "steel_guitar", "name": "53-Fret Steel Guitar", "instrument": "steel_guitar", "notes": steel_notes},
            {"id": "nylon_guitar", "name": "53-Fret Nylon Guitar", "instrument": "nylon_guitar", "notes": nylon_notes},
        ],
    )


def build_03_piano_bosanquet() -> Path:
    # ~13.2s at 104 BPM: Walking visibly up Bosanquet's 5 comma terraces (k = -2 -> -1 -> 0 -> +1 -> +2)
    bpm = 104.0
    notes: List[Dict] = []
    pedals = []
    # Steps 0..16s (~0..20.5b): 5 comma planes k = -2, -1, 0, +1, +2
    for idx, k in enumerate([-2, -1, 0, +1, +2]):
        b0 = idx * 3.0
        pedals.append({"beat": round(b0, 3), "dur": 2.85})
        voic = [-53 + k, -22 + k, 0 + k, 17 + k, 31 + k, 43 + k]
        for j, st in enumerate(voic):
            notes.append(note(b0 + j * 0.22, 2.75 - j * 0.22, st, 0.68 + 0.03 * idx))
        # High shimmer terrace step
        notes.append(note(b0 + 1.8, 1.1, 53 + k, 0.78))
        notes.append(note(b0 + 2.3, 0.7, 70 + k, 0.74))

    # Finale septimal arpeggio (15.5..21.5b)
    pedals.append({"beat": 15.4, "dur": 5.8})
    arp = [-53, -22, 0, 17, 31, 43, 53, 62, 70, 84, 96, 106]
    for j, st in enumerate(arp):
        notes.append(note(15.5 + j * 0.20, 4.5 - j * 0.14, st, 0.70 + 0.015 * j))

    return make_score(
        "03_piano_bosanquet",
        "The Bosanquet 5-Tier Terraced 53-EDO Grand Piano",
        "Five syntonic comma terraces climbing k = -2 to +2 with damper-pedal septimal resonance.",
        bpm,
        [{"id": "piano", "name": "Bosanquet 53-EDO Piano", "instrument": "piano", "pedals": pedals, "notes": notes}],
    )


def build_04_viol() -> Path:
    # ~13.0s at 88 BPM: Expressive bowed 5:4, 6:5, and 7:4 double-stops & lyrical bow reversals
    bpm = 88.0
    cello_notes: List[Dict] = []
    viola_notes: List[Dict] = []

    phrases = [
        (0.2, 2.4, -53, -22, 0.74, "arch"),    # C2-G2 open 3:2
        (2.8, 2.2, -36, 0, 0.78, "cresc"),     # E-C 5:4 double-stop resonance
        (5.2, 2.4, -22, 17, 0.80, "arch"),     # G-E+ 5:3 / 5:4
        (7.8, 2.4, -39, -10, 0.76, "arch"),    # Dm minor 6:5
        (10.4, 2.8, -53, -10, 0.82, "cresc"),  # C-Bb_harm (7:4!)
        (13.4, 4.2, -53, 0, 0.84, "dim"),      # Deep tonic resolution
    ]
    for b, d, low_s, hi_s, vel, sw in phrases:
        cello_notes.append(note(b, d, low_s, vel, swell=sw, vibrato=0.35))
        cello_notes.append(note(b + 0.08, d - 0.12, low_s + P5, vel * 0.88, swell=sw, vibrato=0.30))
        viola_notes.append(note(b + 0.15, d - 0.18, hi_s, vel * 0.90, swell=sw, vibrato=0.45))

    return make_score(
        "04_viol_53edo",
        "The Sympathetic 53-EDO Concert Viol & Floating Bow",
        "Bowed 5:4, 6:5, and 7:4 double-stops illuminating beatless string vibration and bow direction.",
        bpm,
        [
            {"id": "cello", "name": "53-EDO Concert Viol", "instrument": "cello", "notes": cello_notes},
            {"id": "viola", "name": "Sympathetic Viola", "instrument": "viola", "notes": viola_notes},
        ],
    )


def build_05_sitar_shruti() -> Path:
    # ~13.0s at 90 BPM: 22-shruti Sitar meend glides over Ektara drone
    bpm = 90.0
    sitar_notes: List[Dict] = []
    ektara_notes: List[Dict] = []

    for i in range(18):
        ektara_notes.append(note(i * 1.0, 0.88, -53 if i % 4 != 2 else -22, 0.72 if i % 2 == 0 else 0.58))

    mel = [
        (0.2, 1.5, 0, 0.0, 0.78),
        (1.9, 1.4, 12, -45.28, 0.80),   # 7:6 Komal Ga with slow meend
        (3.5, 1.4, 17, -67.92, 0.82),   # 5:4 Shuddha Ga
        (5.1, 1.6, 26, -45.28, 0.84),   # 7:5 Tivra Ma
        (6.9, 1.8, 31, 0.0, 0.86),      # Pa (3:2)
        (8.9, 1.4, 35, +45.28, 0.80),   # Ati-Komal Dha sliding down
        (10.5, 1.6, 43, -45.28, 0.82),  # 7:4 Komal Ni
        (12.3, 1.6, 53, -67.92, 0.86),  # High Sa glide
        (14.1, 3.2, 31, +22.64, 0.76),  # Gentle comma settle to Pa
    ]
    for b, d, st, sl, vel in mel:
        sitar_notes.append(note(b, d, st, vel, slide_from_cents=sl))

    return make_score(
        "05_shruti_sitar_53edo",
        "The 22-Shruti Sympathetic Sitar & Gourd Monochord",
        "Intimate 53-EDO meend string deflections and sympathetic taraf shimmer over Ektara drone.",
        bpm,
        [
            {"id": "sitar", "name": "22-Shruti Sitar", "instrument": "sitar", "notes": sitar_notes},
            {"id": "ektara", "name": "Ektara Monochord", "instrument": "ektara", "notes": ektara_notes},
        ],
    )


def build_06_winds_brass() -> Path:
    # ~13.0s at 112 BPM: Micro-keyed Clarinet hook answered by Trombone slide & French Horn 4:5:6:7 fanfare
    bpm = 112.0
    clar_notes: List[Dict] = []
    horn_notes: List[Dict] = []
    tromb_notes: List[Dict] = []

    # 0.0..10.0b: Clarinet agile prime-step hook (5, 17, 31, 43, 53)
    hook = [(0.2, 0.55, 0), (0.85, 0.55, 9), (1.5, 0.55, 17), (2.15, 0.55, 31), (2.8, 0.75, 43), (3.7, 1.5, 53)]
    for rep, root in enumerate([0, 31 - 53]):
        for b, d, iv in hook:
            clar_notes.append(note(rep * 5.2 + b, d, root + iv, 0.78, swell="arch", vibrato=0.25))

    # 10.6..22.5b: Brass Trombone physical slide & Horn pure 4:5:6:7 chorale
    brass_chords = [
        (10.6, 2.4, -53, 17 - 53, 31, 0.80, "sfz"),       # C 5:4
        (13.2, 2.4, -36, 43 - 53, 17, 0.78, "arch"),      # Eb/C7 septimal step shift
        (15.8, 2.4, -44, 0, 22, 0.82, "cresc"),           # D/G-F transition
        (18.4, 3.8, -53, 43 - 53, 17, 0.86, "cresc"),     # Glorious C 4:5:6:7 fanfare
    ]
    for b, d, t_st, h_st, c_st, vel, sw in brass_chords:
        tromb_notes.append(note(b, d, t_st, vel, swell=sw))
        horn_notes.append(note(b + 0.08, d - 0.10, h_st, vel * 0.94, swell=sw, vibrato=0.18))
        clar_notes.append(note(b + 0.16, d - 0.18, c_st, vel * 0.90, swell=sw, vibrato=0.22))

    return make_score(
        "06_winds_brass_53edo",
        "The Micro-Valve Brass & Woodwind Consort",
        "Micro-keyed Clarinet prime hooks answered by sliding 53-EDO Trombone & French Horn pure 4:5:6:7 brass.",
        bpm,
        [
            {"id": "clarinet", "name": "53-Key Clarinet", "instrument": "clarinet", "notes": clar_notes},
            {"id": "french_horn", "name": "53-Valve French Horn", "instrument": "french_horn", "notes": horn_notes},
            {"id": "trombone", "name": "53-Position Trombone", "instrument": "trombone", "notes": tromb_notes},
        ],
    )


def build_07_organ_timpani() -> Path:
    # ~13.0s at 96 BPM: Tuned Timpani strokes & roll igniting a majestic 53-EDO Pipe Organ chord
    bpm = 96.0
    timp_notes: List[Dict] = []
    organ_notes: List[Dict] = []

    # 0.0..6.5b: Dramatic 53-EDO Timpani solo strokes (C2, G2, Eb2, C3) + accelerando roll
    for b, st, v in [(0.2, -106, 0.82), (1.5, -75, 0.78), (2.6, -92, 0.76), (3.6, -53, 0.84)]:
        timp_notes.append(note(b, 1.0, st, v))
    for k in range(16):
        b = 4.8 + k * 0.18
        timp_notes.append(note(b, 0.35, -106 if k % 2 == 0 else -75, 0.45 + 0.025 * k))

    # 7.8..19.5b: Towering 53-EDO Cathedral Pipe Organ chorale + Timpani punctuation
    org_chords = [
        (7.8, 3.6, [-106, -53, -22, 0, 17, 31], 0.74),
        (11.6, 3.4, [-84, -31, 0, 22, 39, 53], 0.78),
        (15.2, 4.4, [-106, -53, -22, 0, 17, 31, 43, 53, 70], 0.84),
    ]
    for b, d, steps, vel in org_chords:
        timp_notes.append(note(b, 1.2, steps[0], vel + 0.04))
        for st in steps:
            organ_notes.append(note(b, d, st, vel * 0.90, swell="cresc" if b > 14 else "arch"))

    return make_score(
        "07_organ_timpani_53edo",
        "The 53-Rank Pipe Organ & Copper Timpani",
        "Tuned 53-EDO copper Timpani strokes igniting illuminated Cathedral Pipe Organ ranks.",
        bpm,
        [
            {"id": "timpani", "name": "Copper 53-EDO Timpani", "instrument": "timpani", "notes": timp_notes},
            {"id": "church_organ", "name": "Cathedral Pipe Organ", "instrument": "church_organ", "notes": organ_notes},
        ],
    )


def build_08_herald_oracle() -> Path:
    # ~13.0s at 136 BPM: The Herald & The Oracle — crystalline AI polyhedra in 11/13-limit strip scan & mirror lock
    bpm = 136.0
    herald_notes: List[Dict] = []
    oracle_notes: List[Dict] = []

    # 0.0..12.0b: The Herald alone — sleek 11/13-limit strip leaps (zero vibrato, no short-note chatter)
    strip = [
        (0.2, 0.9, 77, 0.62), (1.3, 0.8, 37, 0.60), (2.3, 1.1, 65, 0.64),
        (3.6, 0.8, 43, 0.60), (4.6, 1.2, 90, 0.66), (6.0, 0.9, 48, 0.62),
        (7.2, 1.4, 77, 0.68), (8.8, 1.4, 53, 0.66), (10.4, 1.6, 62, 0.68),
    ]
    for b, d, st, vel in strip:
        herald_notes.append(note(b, d, st, vel, swell="none", vibrato=0.0))

    # 12.2..27.5b: The Oracle joins along Critical Line axis (S = 148, exact u + l = 148 mirror!)
    # Pairs centered on 74 (~G#5): (90,58), (84,64), (77,71), (96,52), (106,42), (84,64)
    mirror_pairs = [
        (12.4, 1.8, 90, 58, 0.68),
        (14.4, 1.8, 84, 64, 0.70),
        (16.4, 2.0, 77, 71, 0.72),
        (18.6, 2.2, 96, 52, 0.74),
        (21.0, 2.4, 106, 42, 0.76),
        (23.6, 4.2, 84, 53, 0.72),  # Pure C-E critical lock
    ]
    for b, d, u_st, l_st, vel in mirror_pairs:
        herald_notes.append(note(b, d, u_st, vel, swell="none", vibrato=0.0))
        oracle_notes.append(note(b, d, l_st, vel * 0.96, swell="none", vibrato=0.0))

    return make_score(
        "08_herald_oracle_ai",
        "The Herald & The Oracle — AI Geodesic Polyhedra",
        "Crystalline zero-vibrato Bamboo-Synth voices slicing 11/13-limit strip bounds into mirror synthesis.",
        bpm,
        [
            {"id": "ai_strip", "name": "The Herald (Zero-Free Strip)", "instrument": "shakuhachi", "notes": herald_notes},
            {"id": "ai_architect", "name": "The Oracle (Critical Line)", "instrument": "shakuhachi", "notes": oracle_notes},
        ],
    )


def main() -> None:
    import sys

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if "--all" in sys.argv[1:]:
        builders = [
            build_01_harp,
            build_02_guitar,
            build_03_piano_bosanquet,
            build_04_viol,
            build_05_sitar_shruti,
            build_06_winds_brass,
            build_07_organ_timpani,
            build_08_herald_oracle,
        ]
    else:
        builders = [
            build_01_harp,
            build_03_piano_bosanquet,
        ]
    for fn in builders:
        score_path = fn()
        wav_path = OUT_DIR / f"{score_path.stem}.wav"
        cmd = [str(BIN), "render", str(score_path), str(wav_path)]
        print(f"Rendering {wav_path.name}...")
        subprocess.run(cmd, cwd=ROOT, check=True)
    print("All 8 3D showcase scores & WAVs ready under scores/showcase_3d/ and output/showcase_3d/.")


if __name__ == "__main__":
    main()
