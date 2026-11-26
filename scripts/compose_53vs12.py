#!/usr/bin/env python3
"""
Compose a concert-grade ~10-minute (585–615s) pure stage-independent 53-EDO symphonic work:
  "The Shattered Semitone (Symphonia 53 contra 12) — Seven Studies in the Syntonic Abyss"

Engineered so that EVERY movement shines with crystalline acoustic purity, lyrical microtonal
melody, and seamless common-tone modulation in 53-EDO (`--tuning 53edo`), while catastrophically
collapsing into monotone repeated notes, sheared major->minor chords, vanished septimal shrutis,
stripped portamenti, and +14c/+31c beating when quantized to 12-TET (`--tuning 12tet`).

Exact `edo53_to_12tet_midi` Collapse Buckets Exploited Throughout:
  - MIDI 60 (C4):  steps {-2, -1, 0, +1, +2}   (5 steps = 90.6 cents -> 1 dead semitone!)
  - MIDI 62 (D4):  steps {7, 8, 9, 10, 11}     (5 steps: 10:9, 9:8, 8:7 -> 1 dead semitone!)
  - MIDI 63 (Eb4): steps {12, 13, 14, 15}      (4 steps: 7:6 subminor vs 6:5 minor -> 1 note!)
  - MIDI 64 (E4):  steps {16, 17, 18, 19}      (4 steps: grave, 5:4, 81:64, 9:7 -> 1 note!)
  - MIDI 65 (F4):  steps {20, 21, 22, 23, 24}  (5 steps = 90.6 cents -> 1 dead semitone!)
  - MIDI 66 (F#4): steps {25, 26, 27, 28}      (4 steps: 7:5, 45:32, 729:512, 10:7 -> 1 note!)
  - MIDI 67 (G4):  steps {29, 30, 31, 32, 33}  (5 steps = 90.6 cents -> 1 dead semitone!)
  - MIDI 69 (A4):  steps {38, 39, 40, 41}      (4 steps around 440.00 Hz -> 1 dead semitone!)
  - MIDI 70 (Bb4): steps {42, 43, 44, 45, 46}  (5 steps: 7:4, 16:9, 9:5 -> 1 dead semitone!)
  - Diesis Shear:  [38, 2, 16] is a pure 4:5:6 Ab++ Major triad in 53-EDO, but quantizes in
                   12-TET to [69(A), 60(C), 64(E)] = A MINOR!

Outputs: scores/edo53_vs_12tet_10min.json
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

# =============================================================================
# 53-EDO Pitch & Interval Constants (C4 = 0, A4 = 39 = 440.00 Hz, OCT = 53)
# =============================================================================
OCT = 53
COMMA = 1        # 81:80 (~22.64c syntonic comma)
DIESIS = 2       # 128:125 (~45.28c enharmonic diesis)
SEMI_CHROM = 4   # ~90.57c chromatic semitone
SEMI = 5         # 16:15 (~113.21c diatonic semitone)
m2_MINOR = 8     # 10:9  (~181.13c minor whole tone)
M2 = 9           # 9:8   (~203.77c major whole tone)
SUP_M2 = 10      # 8:7   (~226.42c septimal supermajor second)
SUB_m3 = 12      # 7:6   (~271.70c septimal subminor third)
PYTH_m3 = 13     # 32:27 (~294.34c Pythagorean minor third)
m3 = 14          # 6:5   (~316.98c pure minor third)
SUP_m3 = 15      # 27:22 (~339.62c superminor third)
GRAVE_M3 = 16    # 100:81 (~362.26c grave major third)
M3 = 17          # 5:4   (~384.91c pure major third)
PYTH_M3 = 18     # 81:64 (~407.55c Pythagorean ditone)
SUP_M3 = 19      # 9:7   (~430.19c septimal supermajor third)
P4 = 22          # 4:3   (~498.11c pure fourth)
SEPT_TT = 25     # 7:5   (~566.04c septimal tritone)
JUST_TT = 26     # 45:32 (~588.68c just tritone / Tivra Ma)
PYTH_TT = 27     # 729:512 (~611.32c Pythagorean tritone)
P5 = 31          # 3:2   (~701.89c pure fifth)
m6 = 36          # 8:5   (~815.09c pure minor sixth)
M6 = 39          # 5:3   (~883.02c pure major sixth)
HARM_7 = 43      # 7:4   (~973.58c septimal harmonic seventh)
PYTH_m7 = 44     # 16:9  (~996.23c Pythagorean minor seventh)
JUST_m7 = 45     # 9:5   (~1018.87c just minor seventh)
SUP_m7 = 46      # ~1041.51c superminor seventh (pairs in P5 with SUP_m3=15)
GRAVE_M7 = 47    # ~1064.15c grave major seventh (pairs in P5 with GRAVE_M3=16)
M7 = 48          # 15:8  (~1086.79c pure major seventh)
PYTH_M7 = 49     # 243:128 (~1109.43c Pythagorean major seventh)

# Reference pitch classes at comma plane k = 0
C = 0
DB = 5
D_MINUS = 8
D = 9
EB_HARM = 12
EB = 14
E = 17
F = 22
FS = 26
G_MINUS = 30
G = 31
AB = 36
A = 39           # Exact 440.00 Hz in Octave 4!
BB_HARM = 43
BB = 44
BB_JUST = 45
B = 48

WIND_BRASS = {"clarinet", "english_horn", "bassoon", "french_horn", "trombone"}
BASS_CAPABLE = {"bassoon", "cello", "trombone", "piano", "church_organ", "ektara", "timpani"}
# Exact sweet-spot register guardrails from docs/SCORE_FORMAT.md §4
SWEET_SPOTS: Dict[str, Tuple[int, int]] = {
    "piano": (-106, 92),
    "harp": (-84, 106),
    "pizzicato": (-53, 70),
    "string_ensemble": (-53, 84),
    "tremolo_strings": (-53, 84),
    "viola": (-53, 53),
    "cello": (-106, 17),
    "clarinet": (-36, 70),
    "english_horn": (-31, 53),
    "bassoon": (-106, 0),
    "french_horn": (-75, 31),
    "trombone": (-89, 0),
    "timpani": (-106, 0),
    "dotara": (-53, 53),
    "ektara": (-84, 17),
    "sitar": (-53, 31),
    "church_organ": (-106, 53),
}
STRICT_CHORD_TRACKS = {
    "harp",
    "pizzicato",
    "string_ensemble",
    "tremolo_strings",
    "bassoon",
    "trombone",
    "dotara",
    "ektara",
    "church_organ",
}


def pitch(pc: int, octave: int, k: int = 0) -> int:
    """Exact 53-EDO step for pitch class `pc` in `octave` (C4 = 0) + comma shift `k`."""
    return pc + (octave - 4) * OCT + k


def mod53_dist(a: int, b: int) -> int:
    d = (a - b) % OCT
    return min(d, OCT - d)


def edo53_to_12tet_midi(step: int, cents: float = 0.0) -> int:
    """Exact replica of Rust `tuning::edo53_to_12tet_midi`."""
    val = 60.0 + (step / OCT) * 12.0 + cents / 100.0
    # Rust f64::round rounds half away from zero
    if val >= 0.0:
        r = int(math.floor(val + 0.5))
    else:
        r = int(math.ceil(val - 0.5))
    return max(0, min(127, r))


# =============================================================================
# Clash-Free Pure 5-Limit, 7-Limit, Pythagorean & Shruti Chord Templates
# Every template + melody_extra guarantees pairwise mod53_dist >= 4!
# =============================================================================
CHORD_TEMPLATES: Dict[str, Tuple[int, ...]] = {
    "open5": (0, P5),
    "maj": (0, M3, P5),
    "min": (0, m3, P5),
    "add9": (0, M2, M3, P5),
    "maj7": (0, M3, P5, M7),
    "maj9": (0, M2, M3, P5, M7),
    "min7": (0, m3, P5, JUST_m7),
    "min9": (0, M2, m3, P5, JUST_m7),
    "min_dm": (0, m3, P5),                  # ii(8) minor with minor-tone melody compatibility
    "dom7": (0, M3, P5, HARM_7),            # 4:5:6:7 septimal dominant 7th
    "dom9": (0, M2, M3, P5, HARM_7),        # 4:5:6:7:9 Debussy/shruti dominant 9th
    # 12-TET Collapse Modal Variants (all share root 0 & fifth 31!):
    "submin7": (0, SUB_m3, P5, HARM_7),     # [0, 12, 31, 43] = 6:7:9:10.5 -> Cm7 in 12-TET!
    "pyth_min7": (0, PYTH_m3, P5, PYTH_m7), # [0, 13, 31, 44] -> Cm7 in 12-TET!
    "supmin7": (0, SUP_m3, P5, SUP_m7),     # [0, 15, 31, 46] -> Cm7 in 12-TET!
    "grave_maj": (0, GRAVE_M3, P5),         # [0, 16, 31] -> C maj in 12-TET!
    "grave_maj7": (0, GRAVE_M3, P5, GRAVE_M7),
    "pyth_maj": (0, PYTH_M3, P5),           # [0, 18, 31] (81:64) -> C maj in 12-TET!
    "pyth_maj7": (0, PYTH_M3, P5, PYTH_M7), # [0, 18, 31, 49] -> Cmaj7 in 12-TET!
    "supmaj": (0, SUP_M3, P5),              # [0, 19, 31] (9:7 supermajor) -> C maj in 12-TET!
    "sus4": (0, P4, P5),
    "sus2": (0, M2, P5),
}

MELODY_EXTRA: Dict[str, Tuple[int, ...]] = {
    "open5": (M2, P4, M6),
    "maj": (M2, P4, M6, M7),
    "min": (M2, P4, m6, JUST_m7),
    "add9": (P4, M6, M7),
    "maj7": (M2, P4, M6),
    "maj9": (P4, M6),
    "min7": (M2, P4, m6),
    "min9": (P4, m6),
    "min_dm": (m2_MINOR, P4, m6, PYTH_m7),
    "dom7": (M2, P4),
    "dom9": (P4,),
    "submin7": (P4, m6),
    "pyth_min7": (P4, m6),
    "supmin7": (M2, P4, M6),
    "grave_maj": (m2_MINOR, P4, GRAVE_M7),
    "grave_maj7": (m2_MINOR, P4),
    "pyth_maj": (M2, 40, PYTH_M7),
    "pyth_maj7": (M2, 40),
    "supmaj": (SUP_M2, 24, JUST_m7),
    "sus4": (M2, M6),
    "sus2": (P4, M6),
}


@dataclass
class ChordSpan:
    start: float
    end: float
    root_pc: int
    quality: str
    label: str = ""
    pedal_pc: Optional[int] = None

    @property
    def chord_pcs(self) -> Set[int]:
        s = {(self.root_pc + iv) % OCT for iv in CHORD_TEMPLATES[self.quality]}
        if self.pedal_pc is not None:
            s.add(self.pedal_pc % OCT)
        return s

    @property
    def melody_pcs(self) -> Set[int]:
        s = set(self.chord_pcs)
        for iv in MELODY_EXTRA[self.quality]:
            cand = (self.root_pc + iv) % OCT
            if all(mod53_dist(cand, existing) >= 4 for existing in s):
                s.add(cand)
        return s

    def verify_clash_free(self) -> None:
        pcs = sorted(self.melody_pcs)
        for i in range(len(pcs)):
            for j in range(i + 1, len(pcs)):
                d = mod53_dist(pcs[i], pcs[j])
                if d < 4:
                    raise ValueError(
                        f"Span {self.label} ({self.start}..{self.end}) has internal comma clash: "
                        f"pc {pcs[i]} vs {pcs[j]} (dist={d})"
                    )

    def nearest_step(self, target_step: int, allow_melody: bool = False) -> int:
        pcs = self.melody_pcs if allow_melody else self.chord_pcs
        best = target_step
        best_dist = 999
        for d in range(-26, 27):
            cand = target_step + d
            if (cand % OCT) in pcs and abs(d) < best_dist:
                best_dist = abs(d)
                best = cand
        return best

    def bass_root(self, low: int = -106, high: int = -54) -> int:
        """Places bass root (or pedal_pc) cleanly inside [C2..B2] (-106..-54)."""
        pc = self.pedal_pc if self.pedal_pc is not None else self.root_pc
        st = (pc % OCT) - 2 * OCT
        while st < low:
            st += OCT
        while st > high:
            st -= OCT
        return st

    def tenor_root(self) -> int:
        """Places root cleanly inside [C3..B3] (-53..-1) so all upper voices sit >= C3."""
        r = (self.root_pc % OCT) - OCT
        while r < -53:
            r += OCT
        while r > -1:
            r -= OCT
        return r

    def third_offset(self) -> int:
        q = self.quality
        if q in ("maj", "add9", "maj7", "maj9", "dom7", "dom9"):
            return M3
        if q in ("min", "min7", "min9", "min_dm"):
            return m3
        if q == "submin7":
            return SUB_m3
        if q == "pyth_min7":
            return PYTH_m3
        if q == "supmin7":
            return SUP_m3
        if q in ("grave_maj", "grave_maj7"):
            return GRAVE_M3
        if q in ("pyth_maj", "pyth_maj7"):
            return PYTH_M3
        if q == "supmaj":
            return SUP_M3
        if q == "sus4":
            return P4
        if q == "sus2":
            return M2
        return P5

    def seventh_offset(self) -> Optional[int]:
        q = self.quality
        if q in ("dom7", "dom9", "submin7"):
            return HARM_7
        if q in ("maj7", "maj9"):
            return M7
        if q in ("min7", "min9"):
            return JUST_m7
        if q == "pyth_min7":
            return PYTH_m7
        if q == "supmin7":
            return SUP_m7
        if q == "grave_maj7":
            return GRAVE_M7
        if q == "pyth_maj7":
            return PYTH_M7
        return None

    def open_voicing(self, include_9: bool = True, include_7: bool = True) -> List[int]:
        """Warm orchestral voicing (>= C3) with zero low-register mud and zero 5-step minor-2nd rubs."""
        r = self.tenor_root()
        q = self.quality
        if q == "open5":
            return [r, r + P5, r + OCT]
        th = self.third_offset()
        sev = self.seventh_offset() if include_7 else None
        if q == "min9" and include_9:
            # Exact SCORE_FORMAT.md §3 min9 voicing [0, 14, 31, 45, 62] (avoids M2 vs m3 5-step rub!)
            return sorted({r, r + m3, r + P5, r + OCT + M2} | ({r + sev} if sev is not None else set()))
        if include_9 and q in ("add9", "dom9", "maj9"):
            # Exact SCORE_FORMAT.md §3 [0, 17, 31, (43/48), 62] open voicing
            return sorted({r, r + M3, r + P5, r + OCT + M2} | ({r + sev} if sev is not None else set()))
        voicing = [r, r + P5]
        if sev is not None:
            voicing.append(r + sev)
        voicing.append(r + OCT + th)
        return sorted(set(voicing))

    def arp_scale(self, low_step: int, high_step: int) -> List[int]:
        pcs = set(self.chord_pcs)
        if self.quality in ("maj7", "maj9", "grave_maj7", "pyth_maj7"):
            sev = self.seventh_offset()
            if sev is not None:
                pcs.discard((self.root_pc + sev) % OCT)
        return [s for s in range(low_step, high_step + 1) if (s % OCT) in pcs]


# =============================================================================
# Analytical Piecewise-Linear TempoMap (exact match to Rust `src/score.rs`)
# =============================================================================
class TempoMap:
    def __init__(self, segments: List[Tuple[float, float]]):
        self.segments = sorted(segments, key=lambda x: x[0])

    def bpm_at(self, beat: float) -> float:
        if beat <= self.segments[0][0]:
            return self.segments[0][1]
        for i in range(len(self.segments) - 1):
            b0, bpm0 = self.segments[i]
            b1, bpm1 = self.segments[i + 1]
            if b0 <= beat <= b1:
                if b1 - b0 <= 1e-9:
                    return bpm1
                u = (beat - b0) / (b1 - b0)
                return bpm0 + u * (bpm1 - bpm0)
        return self.segments[-1][1]

    def beat_to_seconds(self, beat: float) -> float:
        if len(self.segments) == 1:
            return beat * (60.0 / self.segments[0][1])
        secs = 0.0
        first_b, first_bpm = self.segments[0]
        if beat <= first_b:
            return beat * (60.0 / first_bpm)
        if first_b > 0.0:
            secs += first_b * (60.0 / first_bpm)

        for i in range(len(self.segments) - 1):
            a_b, a_bpm = self.segments[i]
            b_b, b_bpm = self.segments[i + 1]
            if beat <= a_b:
                break
            end_b = min(beat, b_b)
            span = b_b - a_b
            partial = end_b - a_b
            if partial <= 0.0:
                continue
            if span <= 1e-9 or abs(b_bpm - a_bpm) < 1e-6:
                secs += partial * (60.0 / a_bpm)
            else:
                slope = (b_bpm - a_bpm) / span
                bpm_end = a_bpm + slope * partial
                secs += (60.0 / slope) * math.log(bpm_end / a_bpm)
            if beat <= b_b:
                return secs

        last_b, last_bpm = self.segments[-1]
        if beat > last_b:
            secs += (beat - last_b) * (60.0 / last_bpm)
        return secs

    def to_json(self) -> List[Dict[str, float]]:
        return [{"beat": round(b, 4), "bpm": round(bpm, 3)} for b, bpm in self.segments]


# =============================================================================
# Stage-Independent Score Builder with Exact Comma & Mud Boundary Safety
# =============================================================================
@dataclass
class TrackSpec:
    id: str
    name: str
    instrument: str
    notes: List[Dict] = field(default_factory=list)
    pedals: List[Dict] = field(default_factory=list)


class ScoreBuilder:
    def __init__(self, tempo_segments: List[Tuple[float, float]]):
        self.tempo = TempoMap(tempo_segments)
        self.grid: List[ChordSpan] = []
        self.sections: List[Tuple[float, str]] = []
        self.tracks: Dict[str, TrackSpec] = {}
        self._init_tracks()

    def _init_tracks(self) -> None:
        # 17 Warm-Core + Indian Shruti + Finale Organ tracks (100% stage-independent!)
        specs = [
            TrackSpec("piano", "Concert Grand Piano", "piano"),
            TrackSpec("harp", "Orchestral Harp", "harp"),
            TrackSpec("pizzicato", "Pizzicato Strings", "pizzicato"),
            TrackSpec("string_ensemble", "String Orchestra", "string_ensemble"),
            TrackSpec("tremolo_strings", "Tremolo Strings", "tremolo_strings"),
            TrackSpec("viola", "Solo Viola", "viola"),
            TrackSpec("cello", "Solo Cello", "cello"),
            TrackSpec("clarinet", "Solo Clarinet", "clarinet"),
            TrackSpec("english_horn", "English Horn", "english_horn"),
            TrackSpec("bassoon", "Solo Bassoon", "bassoon"),
            TrackSpec("french_horn", "French Horn", "french_horn"),
            TrackSpec("trombone", "Symphonic Trombone", "trombone"),
            TrackSpec("timpani", "53-EDO Timpani", "timpani"),
            TrackSpec("sitar", "Sitar (Shruti Veil)", "sitar"),
            TrackSpec("dotara", "Dotara", "dotara"),
            TrackSpec("ektara", "Ektara", "ektara"),
            TrackSpec("church_organ", "Cathedral Pipe Organ", "church_organ"),
        ]
        for s in specs:
            self.tracks[s.id] = s

    def add_section(self, beat: float, title: str) -> None:
        self.sections.append((beat, title))

    def add_span(
        self,
        start: float,
        end: float,
        root_pc: int,
        quality: str,
        label: str = "",
        pedal_pc: Optional[int] = None,
    ) -> ChordSpan:
        span = ChordSpan(
            start=float(start),
            end=float(end),
            root_pc=root_pc % OCT,
            quality=quality,
            label=label,
            pedal_pc=(pedal_pc % OCT) if pedal_pc is not None else None,
        )
        span.verify_clash_free()
        self.grid.append(span)
        return span

    def span_at(self, beat: float) -> ChordSpan:
        for sp in self.grid:
            if sp.start - 1e-6 <= beat < sp.end - 1e-6:
                return sp
        return self.grid[-1]

    def add_pedal(self, track_id: str, beat: float, dur: float) -> None:
        if dur > 0.15:
            self.tracks[track_id].pedals.append({
                "beat": round(beat, 4),
                "dur": round(dur, 4),
            })

    def _safe_dur(self, track_id: str, beat: float, dur: float, step: int) -> float:
        """Trims `dur` before any subsequent ChordSpan where `step` would create a comma clash or low mud."""
        if track_id == "timpani":
            return max(0.08, dur)
        end = beat + dur
        pc = step % OCT
        strict = track_id in STRICT_CHORD_TRACKS
        # Gap in beats corresponding to ~0.07s so zero boundary tail crosses into incompatible spans
        bpm = self.tempo.bpm_at(beat)
        gap_beats = max(0.06, 0.075 * (bpm / 60.0))

        for sp in self.grid:
            if sp.end <= beat + 1e-6:
                continue
            if sp.start >= end - 1e-6:
                break
            if sp.start > beat + 1e-6:
                allowed = sp.chord_pcs if strict else sp.melody_pcs
                # Also check < C3 low-register mud against next span's bass_root
                low_conflict = False
                if step < -OCT:
                    br = sp.bass_root()
                    diff = abs(step - br)
                    if 0 < diff < P4:
                        low_conflict = True
                if (pc not in allowed) or low_conflict:
                    end = min(end, sp.start - gap_beats)
                    break
        return max(0.06, end - beat)

    def note(
        self,
        track_id: str,
        beat: float,
        dur: float,
        step: int,
        vel: float,
        *,
        cents: float = 0.0,
        slide_from_cents: float = 0.0,
        swell: Optional[str] = None,
        breath_swell: Optional[bool] = None,
        vibrato: float = 0.0,
        meend_cents: float = 0.0,
        trim_to_chord: bool = True,
        snap_to_harmony: bool = False,
    ) -> None:
        tr = self.tracks[track_id]
        strict = track_id in STRICT_CHORD_TRACKS
        sp0 = self.span_at(beat)

        # Prevent accidental < C3 mud on non-bass instruments
        if track_id not in BASS_CAPABLE and step < -OCT:
            step += OCT

        # Fold into SCORE_FORMAT.md §4 sweet spot before & after harmonic snapping
        lo_sw, hi_sw = SWEET_SPOTS[track_id]
        while step > hi_sw:
            step -= OCT
        while step < lo_sw:
            step += OCT

        if snap_to_harmony and track_id != "timpani":
            step = sp0.nearest_step(step, allow_melody=not strict)
        elif track_id != "timpani":
            allowed = sp0.chord_pcs if strict else sp0.melody_pcs
            if (step % OCT) not in allowed:
                step = sp0.nearest_step(step, allow_melody=not strict)

        while step > hi_sw:
            step -= OCT
        while step < lo_sw:
            step += OCT
        if step < -OCT and track_id != "timpani":
            br = sp0.bass_root()
            if step != br and abs(step - br) < P4:
                step = br if br >= lo_sw else br + OCT

        if trim_to_chord:
            dur = self._safe_dur(track_id, beat, dur, step)

        if swell is None and breath_swell is None and tr.instrument in WIND_BRASS and dur >= 0.65:
            swell = "arch"

        # Calibrate concert dynamic range (pp ~0.38 to ff ~0.87) for healthy EBU R128 LRA (9–13 LU) & I (-18 LUFS)
        vel_cap = 0.78 if track_id == "timpani" else 0.87
        scaled_v = 0.36 + 0.51 * ((max(0.15, min(0.96, float(vel))) - 0.15) / 0.81)
        v = max(0.34, min(vel_cap, scaled_v))
        entry: Dict = {
            "beat": round(beat, 4),
            "dur": round(dur, 4),
            "step": int(step),
            "vel": round(v, 3),
        }
        if abs(cents) > 1e-4:
            entry["cents"] = round(cents, 2)
        if abs(slide_from_cents) > 1e-4:
            entry["slide_from_cents"] = round(max(-150.0, min(150.0, slide_from_cents)), 2)
        if swell is not None:
            entry["swell"] = swell
        elif breath_swell:
            entry["breath_swell"] = True
        if vibrato > 1e-3:
            entry["vibrato"] = round(max(0.0, min(1.0, vibrato)), 3)
        if abs(meend_cents) > 1e-4:
            entry["meend_cents"] = round(meend_cents, 2)
        tr.notes.append(entry)

    def chord(
        self,
        track_id: str,
        beat: float,
        dur: float,
        steps: Sequence[int],
        vel: float,
        *,
        roll: float = 0.0,
        swell: Optional[str] = None,
        vibrato: float = 0.0,
    ) -> None:
        n = len(steps)
        for i, st in enumerate(steps):
            w = 1.0 if i in (0, n - 1) else 0.90
            self.note(
                track_id,
                beat + i * roll,
                max(0.10, dur - i * roll),
                st,
                vel * w,
                swell=swell,
                vibrato=vibrato,
            )

    def string_pad(
        self,
        span: ChordSpan,
        vel: float,
        *,
        track_id: str = "string_ensemble",
        include_9: bool = True,
        include_7: bool = True,
        swell: str = "arch",
        trim_tail: float = 0.12,
    ) -> None:
        if track_id == "tremolo_strings":
            include_7 = False
            include_9 = False
        voicing = span.open_voicing(include_9=include_9, include_7=include_7)
        dur = max(0.25, (span.end - span.start) - trim_tail)
        self.chord(track_id, span.start, dur, voicing, vel, swell=swell)

    def harp_sweep(
        self,
        span: ChordSpan,
        beat: float,
        low_step: int,
        high_step: int,
        vel: float,
        *,
        spacing: float = 0.16,
        note_dur: float = 1.8,
        ascending: bool = True,
        max_notes: int = 8,
        with_pedal: bool = False,
    ) -> None:
        pts = span.arp_scale(low_step, high_step)
        if not pts:
            return
        if len(pts) > max_notes:
            pts = [pts[int(round(i * (len(pts) - 1) / (max_notes - 1)))] for i in range(max_notes)]
        if not ascending:
            pts = list(reversed(pts))
        n = max(1, len(pts))
        if with_pedal and (span.end - beat) > 0.5:
            self.add_pedal("harp", beat, (span.end - beat) - 0.14)
        for i, st in enumerate(pts):
            t = beat + i * spacing
            if t >= span.end - 0.10:
                break
            u = i / max(1, n - 1)
            arch = 0.94 + 0.14 * math.sin(math.pi * u)
            self.note("harp", t, min(note_dur, span.end - t - 0.08), st, vel * arch)

    def piano_figuration(
        self,
        span: ChordSpan,
        vel: float,
        *,
        style: str = "nocturne",
        step_beats: float = 0.5,
        use_pedal: bool = True,
    ) -> None:
        r = span.tenor_root()
        th = span.third_offset()
        sev = span.seventh_offset()
        upper_color = (
            r + OCT + M2
            if span.quality in ("add9", "maj9", "min9", "dom9")
            else (r + sev if sev is not None else r + OCT + th)
        )
        if style == "nocturne":
            seq = [r, r + P5, r + OCT + th, upper_color, r + OCT + P5, upper_color, r + OCT + th, r + P5]
        elif style == "canon":
            seq = [r + P5, r + OCT, r + OCT + th, r + P5, upper_color, r + OCT + th, r + OCT, r + P5]
        elif style == "triplet":
            seq = [r, r + P5, r + OCT + th, r + OCT + P5, upper_color, r + OCT + th]
        elif style == "scherzo":
            seq = [r, r + th, r + P5, r + OCT, r + OCT + th, r + P5, r + th, r + OCT]
        else:  # "grand"
            seq = [r, r + P5, r + OCT, r + OCT + th, upper_color, r + OCT + P5, r + 2 * OCT, upper_color]

        dur_span = span.end - span.start
        if use_pedal and dur_span >= 1.2 and style in ("nocturne", "triplet", "grand"):
            self.add_pedal("piano", span.start + 0.02, dur_span - 0.16)

        t = span.start
        idx = 0
        while t < span.end - 0.08:
            st = seq[idx % len(seq)]
            b_rel = (t - span.start) % 4.0
            if style == "scherzo":
                acc = 1.10 if b_rel < 0.04 else (0.96 if abs(b_rel - 2.0) < 0.05 else 0.80)
                ndur = min(step_beats * 0.78, span.end - t - 0.06)
            elif style == "canon":
                acc = 1.05 if b_rel < 0.04 else 0.86
                ndur = min(step_beats * 0.88, span.end - t - 0.06)
            else:
                acc = 1.08 if b_rel < 0.04 else (0.98 if abs(b_rel - 2.0) < 0.05 else 0.86)
                ndur = min(step_beats * 1.25, span.end - t - 0.07)
            self.note("piano", t, ndur, st, vel * acc)
            t += step_beats
            idx += 1

    def timpani_roll(
        self,
        beat: float,
        dur: float,
        step: int,
        vel_start: float,
        vel_end: float,
        spacing: float = 0.25,
    ) -> None:
        t = beat
        end = beat + dur
        while t < end - 0.05:
            u = (t - beat) / max(0.01, dur)
            v = vel_start + (vel_end - vel_start) * (u ** 0.85)
            self.note("timpani", t, min(spacing * 1.6, end - t + 0.1), step, v, trim_to_chord=False)
            t += spacing

    def lyrical_line(
        self,
        track_id: str,
        events: Sequence[Tuple[float, float, int, float]],
        *,
        vibrato: float = 0.24,
        comma_glide: bool = True,
        leap_slide: float = 16.0,
        default_swell: Optional[str] = None,
    ) -> None:
        """
        Renders an expressive solo phrase. When `comma_glide=True`, small microtonal steps
        (1..4 syntonic commas = 22.6..90.6 cents!) receive authentic `slide_from_cents`
        glides so 53-EDO sings vocally while `--tuning 12tet` strips both glide AND pitch motion!
        """
        n = len(events)
        is_wind = self.tracks[track_id].instrument in WIND_BRASS
        for i, (b, d, st, v) in enumerate(events):
            u = i / max(1, n - 1) if n > 1 else 0.5
            phrase_arch = 0.93 + 0.12 * math.sin(math.pi * (u ** 0.85))
            slide = 0.0
            if i > 0:
                pb, pd, pst, _ = events[i - 1]
                diff = st - pst
                gap = b - (pb + pd)
                if comma_glide and 1 <= abs(diff) <= 4 and gap < 0.35 and d >= 0.45:
                    # Exact microtonal portamento from previous comma plane!
                    raw_cents = -diff * (1200.0 / OCT) * 0.85
                    slide = max(-42.0 if track_id == "sitar" else -85.0, min(42.0 if track_id == "sitar" else 85.0, raw_cents))
                elif leap_slide > 0.0 and 8 <= abs(diff) <= 22 and gap < 0.22 and d >= 0.85:
                    slide = -leap_slide if diff > 0 else leap_slide * 0.85
            sw = default_swell
            if sw is None and (is_wind or track_id in ("viola", "cello")) and d >= 1.1:
                sw = "arch" if i < n - 1 else "dim"
            vib = vibrato if d >= 0.65 and track_id in ("viola", "cello", "english_horn", "clarinet", "french_horn") else 0.0
            self.note(
                track_id,
                b,
                d,
                st,
                v * phrase_arch,
                slide_from_cents=slide,
                swell=sw,
                vibrato=vib,
            )

    def build_dict(self) -> Dict:
        self.grid.sort(key=lambda s: s.start)
        tracks_json = []
        for tr in self.tracks.values():
            for n in tr.notes:
                n["dur"] = round(self._safe_dur(tr.id, n["beat"], n["dur"], n["step"]), 4)
            sorted_notes = sorted(tr.notes, key=lambda x: (x["beat"], x["step"]))
            # Ensure natural human breathing rests (>= 0.85b) at least every ~13.5 beats on all winds/brass
            if tr.instrument in WIND_BRASS and len(sorted_notes) > 1:
                run_start = sorted_notes[0]["beat"]
                for i in range(1, len(sorted_notes)):
                    prev = sorted_notes[i - 1]
                    cur = sorted_notes[i]
                    prev_end = prev["beat"] + prev["dur"]
                    gap = cur["beat"] - prev_end
                    if gap >= 0.80:
                        run_start = cur["beat"]
                    elif (cur["beat"] + cur["dur"]) - run_start > 13.5 and prev["dur"] >= 1.20:
                        new_dur = (cur["beat"] - 0.88) - prev["beat"]
                        if new_dur >= 0.30:
                            prev["dur"] = round(new_dur, 4)
                            run_start = cur["beat"]
            t_obj: Dict = {
                "id": tr.id,
                "name": tr.name,
                "instrument": tr.instrument,
                "notes": sorted_notes,
            }
            if tr.pedals:
                t_obj["pedals"] = sorted(tr.pedals, key=lambda p: p["beat"])
            tracks_json.append(t_obj)

        sections_json = [
            {"beat": round(b, 3), "title": title}
            for b, title in sorted(self.sections, key=lambda s: s[0])
        ]

        return {
            "title": "The Shattered Semitone (Symphonia 53 contra 12) — Seven Studies in the Syntonic Abyss",
            "description": (
                "A concert-grade ~10-minute stage-independent 53-EDO symphonic classical work "
                "specifically composed to maximize the structural and acoustic divergence between "
                "53-EDO and 12-TET. Features 5-comma melodic arches and 4-voice canons inside single "
                "12-TET semitone buckets ({-2..+2}, {12..15}, {16..19}, {20..24}, {29..33}, {38..41}, "
                "{42..46}), septimal 7:6 vs 6:5 and 7:4 vs 9:5 shruti mirrors, a 6-stage continuous "
                "syntonic comma passacaglia spiral (k = -2 to +3), chromatic-mediant diesis ladders "
                "where pure [38, 2, 16] Ab++ Major shears into A minor in 12-TET, a hushed Adagio "
                "lament of beat-free glass chords, and a final Cathedral Pipe Organ apotheosis."
            ),
            "sample_rate": 48000,
            "sections": sections_json,
            "tempo": self.tempo.to_json(),
            "tracks": tracks_json,
        }


# =============================================================================
# Compose the 7-Section ~10-Minute Symphonic Work
# =============================================================================
def compose_53vs12() -> Tuple[ScoreBuilder, Dict]:
    tempo_segments = [
        # Section I (0..88): Prologus — The Fivefold Unison & Septimal Dawn (~84s)
        (0.0, 60.5),
        (16.0, 63.8),
        (48.0, 65.8),
        (72.0, 59.5),
        (87.99, 59.5),
        # Section II (88..192): Canon Per Tonos Syntonicos — Four-Voice Collapse Fugato (~75s)
        (88.0, 81.8),
        (136.0, 86.0),
        (176.0, 82.8),
        (191.99, 79.6),
        # Section III (192..296): Nocturne of the Vanishing Shrutis — Septimal & Shruti Mirror (~92s)
        (192.0, 65.8),
        (228.0, 69.0),
        (264.0, 66.8),
        (288.0, 61.5),
        (295.99, 61.5),
        # Section IV (296..416): Passacaglia of the Endless Comma Spiral (k = -2 to +3) (~83s)
        (296.0, 82.8),
        (344.0, 89.2),
        (368.0, 91.2),
        (396.0, 84.9),
        (415.99, 80.6),
        # Section V (416..536): Scherzo — The Diesis Labyrinth (Major-to-Minor Shear) (~75s)
        (416.0, 95.5),
        (464.0, 98.8),
        (504.0, 96.5),
        (528.0, 87.0),
        (535.99, 82.8),
        # Section VI (536..632): Adagio Mesto — Lament on the Broken Third & Glass Harmonics (~92s)
        (536.0, 59.5),
        (576.0, 62.6),
        (608.0, 66.8),
        (631.99, 69.0),
        # Section VII (632..736): Finale & Cathedral Organ Apotheosis (~94s + 5s tail -> ~600s!)
        (632.0, 73.2),
        (664.0, 75.4),
        (708.0, 64.8),
        (726.0, 54.2),
        (736.0, 51.0),
    ]
    sb = ScoreBuilder(tempo_segments)

    # Register the 7 structural sections
    sb.add_section(0.0, "I. Prologus — The Fivefold Unison & Septimal Dawn")
    sb.add_section(88.0, "II. Canon Per Tonos Syntonicos — Four-Voice Collapse Fugato")
    sb.add_section(192.0, "III. Nocturne of the Vanishing Shrutis — Septimal & Shruti Mirror")
    sb.add_section(296.0, "IV. Passacaglia of the Endless Comma Spiral (k = -2 to +3)")
    sb.add_section(416.0, "V. Scherzo — The Diesis Labyrinth & Major-to-Minor Shear")
    sb.add_section(536.0, "VI. Adagio Mesto — Lament on the Broken Third & Glass Harmonics")
    sb.add_section(632.0, "VII. Finale & Cathedral Organ Apotheosis — The 53-Tone Continuum")

    # =========================================================================
    # SECTION I (Beats 0..88): PROLOGUS — THE FIVEFOLD UNISON & SEPTIMAL DAWN
    # =========================================================================
    # I.A (0..16): Hushed pp Awakening around exact Concert A4 = 39 = 440.00 Hz
    s1_intro = [
        sb.add_span(0.0, 4.0, F, "maj", "I.A1 Pure 4:5:6 F maj (A4=440Hz)", F),
        sb.add_span(4.0, 8.0, C, "dom9", "I.A2 Septimal 4:5:6:7:9 C9/F", F),
        sb.add_span(8.0, 12.0, D_MINUS, "min_dm", "I.A3 Pure 10:12:15 Dm-", None),
        sb.add_span(12.0, 16.0, C, "dom7", "I.A4 Pure 4:5:6:7 C7", None),
    ]
    for i, sp in enumerate(s1_intro):
        v = [0.28, 0.34, 0.38, 0.34][i]
        sb.string_pad(sp, vel=v, swell="cresc" if i < 2 else "arch", trim_tail=0.14)
        sb.note("bassoon", sp.start + 0.1, 3.5, sp.bass_root(), v + 0.05, swell="arch")
        if i in (0, 1, 3):
            sb.harp_sweep(sp, sp.start + 0.25, pitch(F, 3) - 6, pitch(A, 5), vel=v + 0.10, spacing=0.26, note_dur=2.4, with_pedal=True)

    # Solo Viola & English Horn emerge from 440.00 Hz stillness
    sb.lyrical_line("viola", [
        (0.5, 3.2, pitch(A, 4), 0.36),
        (4.2, 1.8, pitch(BB_HARM, 4), 0.42),
        (6.1, 1.6, pitch(G, 4), 0.38),
        (8.2, 3.4, pitch(A, 4), 0.44),
        (12.2, 3.3, pitch(G, 4), 0.38),
    ], vibrato=0.28)
    sb.lyrical_line("english_horn", [
        (4.5, 3.1, pitch(D, 4), 0.38),
        (8.5, 1.6, pitch(F, 4), 0.44),
        (10.2, 1.5, pitch(D_MINUS, 4), 0.40),
        (12.4, 3.1, pitch(BB_HARM, 4), 0.46),
    ], vibrato=0.30)

    # I.B (16..48): THE FIVEFOLD UNISON MOTTO!
    # Wave 1 (16..32): 16 one-beat comma planes undulating k = -2..+2 on C!
    # ALL 5 steps of C ({-2,-1,0,1,2}) = MIDI 60, G ({29..33}) = MIDI 67, E ({16..19}) = MIDI 64!
    k_wave1 = [-2, -1, 0, +1, +2, +1, 0, -1, -2, -1, 0, +1, +2, +1, 0, -1]
    clar_motto1 = []
    viola_motto1 = []
    cello_motto1 = []
    piano_motto1 = []
    for idx, k in enumerate(k_wave1):
        b0 = 16.0 + idx * 1.0
        sp = sb.add_span(b0, b0 + 1.0, C + k, "maj", f"I.B1 Fivefold C(k={k:+d})")
        dyn = 0.44 + 0.04 * (idx if idx <= 4 else (8 - idx if idx <= 8 else idx - 8))
        sb.string_pad(sp, vel=dyn * 0.82, include_9=False, swell="arch", trim_tail=0.08)
        cello_motto1.append((b0, 0.88, pitch(C, 3, k), dyn + 0.04))       # {-55..-51} -> ALL MIDI 48!
        piano_motto1.append((b0 + 0.15, 0.72, pitch(C, 5, k), dyn * 0.90))  # {51..55} -> ALL MIDI 72!
        # Clarinet sings DIRECT 5-comma scale on C4 (beats 16..23 -> ALL MIDI 60!) then G4 (24..31 -> ALL MIDI 67!)
        if idx < 7:
            clar_motto1.append((b0, 0.88, pitch(C, 4, k), dyn + 0.12))
        elif 8 <= idx < 15:  # Breath at beat 23 & 31!
            clar_motto1.append((b0, 0.88, pitch(G, 4, k), dyn + 0.14))
        # Viola sings direct comma-arch on G3 ({-24..-20} -> ALL MIDI 55) then E4 ({16..19} -> ALL MIDI 64)
        if idx < 8:
            viola_motto1.append((b0, 0.88, pitch(G, 3, k), dyn + 0.08))
        elif k >= -1:
            viola_motto1.append((b0, 0.88, pitch(E, 4, k), dyn + 0.10))
    sb.lyrical_line("clarinet", clar_motto1, vibrato=0.22, comma_glide=True)
    sb.lyrical_line("viola", viola_motto1, vibrato=0.28, comma_glide=True)
    sb.lyrical_line("cello", cello_motto1, vibrato=0.24, comma_glide=True)
    sb.lyrical_line("piano", piano_motto1, vibrato=0.0, comma_glide=False)

    # Wave 2 (32..48): 16 one-beat Septimal 4:5:6:7:9 planes across k in {-1, 0, +1, +2}!
    # EVERY voice stays inside a single 12-TET MIDI note: C->60, E->64, G->67, Bb_harm->70, D->74!
    k_wave2 = [-1, 0, +1, +2, +1, 0, -1, 0, +1, +2, +1, 0, -1, 0, +1, 0]
    eh_motto2 = []
    horn_motto2 = []
    clar_motto2 = []
    for idx, k in enumerate(k_wave2):
        b0 = 32.0 + idx * 1.0
        sp = sb.add_span(b0, b0 + 1.0, C + k, "dom9", f"I.B2 Septimal9 Collapse C9(k={k:+d})")
        dyn = 0.48 + 0.03 * (idx % 6)
        sb.string_pad(sp, vel=dyn * 0.85, include_9=True, swell="arch", trim_tail=0.08)
        if idx % 2 == 0:
            sb.note("bassoon", b0, 0.86, sp.bass_root(), dyn, swell="arch")
        if idx not in (7, 15):  # Double-reed breathing rests!
            eh_motto2.append((b0, 0.88, pitch(BB_HARM, 4, k), dyn + 0.14))  # {42..45} -> ALL MIDI 70!
        if idx not in (5, 11):
            horn_motto2.append((b0, 0.86, pitch(E, 4, k), dyn + 0.06))      # {16..19} -> ALL MIDI 64!
        if idx not in (3, 10, 15):
            clar_motto2.append((b0 + 0.1, 0.78, pitch(D, 5, k), dyn + 0.08))  # {61..64} -> ALL MIDI 74!
    sb.lyrical_line("english_horn", eh_motto2, vibrato=0.32, comma_glide=True)
    sb.lyrical_line("french_horn", horn_motto2, vibrato=0.18, comma_glide=True)
    sb.lyrical_line("clarinet", clar_motto2, vibrato=0.22, comma_glide=True)

    # I.C (48..88): Pastoral Septimal Bloom & Expressive F-Bucket (20..24) Chamber Dissolve
    s1_bloom_specs = [
        (48.0, 52.0, F, "add9", "I.C1 F add9"),
        (52.0, 56.0, F, "dom9", "I.C2 Septimal F9 (Eb_harm=12!)"),
        (56.0, 60.0, BB, "maj9", "I.C3 Bb maj9"),
        (60.0, 64.0, G_MINUS, "min_dm", "I.C4 Gm-"),
        (64.0, 68.0, C, "dom9", "I.C5 C dom9(43)"),
        # 68..84: 5-step F4 Collapse Cadenza (F+k for k = -2, -1, 0, +1, +2 -> {20,21,22,23,24} = ALL MIDI 65!)
        (68.0, 71.0, F - 2, "maj", "I.C6 F--(20)"),
        (71.0, 74.0, F - 1, "maj", "I.C7 F-(21)"),
        (74.0, 77.0, F, "add9", "I.C8 F(22)"),
        (77.0, 80.0, F + 1, "maj", "I.C9 F+(23)"),
        (80.0, 83.0, F + 2, "maj", "I.C10 F++(24)"),
        (83.0, 88.0, F, "add9", "I.C11 Home F add9 pp repose"),
    ]
    s1_bloom = [sb.add_span(*c) for c in s1_bloom_specs]
    for i, sp in enumerate(s1_bloom[:5]):
        dyn = [0.54, 0.62, 0.68, 0.60, 0.56][i]
        sb.string_pad(sp, vel=dyn, swell="arch")
        sb.piano_figuration(sp, vel=dyn * 0.90, style="nocturne", step_beats=0.5)
        if i != 3:
            sb.note("bassoon", sp.start, 3.6, sp.bass_root(), dyn + 0.04, swell="arch")
        sb.note("cello", sp.start, 1.8, sp.bass_root() + OCT, dyn + 0.08, vibrato=0.28, swell="arch")
        sb.note("cello", sp.start + 2.0, 1.7, sp.bass_root() + OCT + P5, dyn + 0.05, vibrato=0.25)

    sb.lyrical_line("clarinet", [
        (48.0, 1.4, pitch(A, 4), 0.64),
        (49.5, 0.45, pitch(C, 5), 0.66),
        (50.0, 1.8, pitch(G, 4), 0.62),
        (52.0, 2.2, pitch(EB_HARM, 5), 0.72),   # Radiant 7:4 above F!
        (54.4, 1.3, pitch(C, 5), 0.66),
        # Breath 55.7..56.3
        (56.3, 1.6, pitch(D_MINUS, 5), 0.72),
        (58.0, 1.8, pitch(A, 4), 0.68),
        (60.2, 1.7, pitch(BB, 4), 0.64),
        (62.0, 1.7, pitch(G_MINUS, 4), 0.60),
        # Breath 63.7..64.4
        (64.4, 1.8, pitch(BB_HARM, 4), 0.64),
        (66.4, 1.3, pitch(E, 4), 0.56),
    ], vibrato=0.24)

    # 68..88: Hushed Solo Cello + Solo Viola + Piano 5-Comma F-Bucket Sigh ({20..24} -> ALL F4 in 12-TET!)
    cello_f_sigh = []
    viola_c_sigh = []
    for j, k in enumerate([-2, -1, 0, +1, +2]):
        sp = s1_bloom[5 + j]
        v = 0.48 - 0.03 * abs(j - 2)
        sb.string_pad(sp, vel=v * 0.72, include_9=False, swell="arch", trim_tail=0.14)
        sb.add_pedal("piano", sp.start + 0.03, 2.75)
        sb.note("piano", sp.start + 0.4, 2.2, pitch(C, 5, k), v * 0.85)  # {51..55} -> ALL MIDI 72!
        cello_f_sigh.append((sp.start, 2.75, pitch(F, 3, k), v + 0.08))  # {-33..-29} -> ALL MIDI 53!
        viola_c_sigh.append((sp.start + 0.2, 2.55, pitch(F, 4, k), v + 0.06))  # {20..24} -> ALL MIDI 65!
    sb.lyrical_line("cello", cello_f_sigh, vibrato=0.34, comma_glide=True)
    sb.lyrical_line("viola", viola_c_sigh, vibrato=0.32, comma_glide=True)

    # Final bar of Sec I (83..88): pp repose
    sp_end1 = s1_bloom[-1]
    sb.string_pad(sp_end1, vel=0.30, swell="dim", trim_tail=0.25)
    sb.harp_sweep(sp_end1, 83.2, pitch(F, 3), pitch(E, 5), vel=0.36, spacing=0.32, note_dur=3.2, with_pedal=True)
    sb.note("english_horn", 83.5, 3.8, pitch(A, 4), 0.34, swell="dim", vibrato=0.25)

    # =========================================================================
    # SECTION II (Beats 88..192): CANON PER TONOS SYNTONICOS — COLLAPSE FUGATO
    # =========================================================================
    # II.A (88..136): Antiphonal 5-Voice Staircase Canon!
    # Three distinct 16-beat canonical sentences:
    #   Wave A (88..104):  Ascending C-bucket staircase k = -2 -> -1 -> 0 -> +1 -> +2 -> 0
    #   Wave B (104..120): Descending G-bucket mirror staircase k = +2 -> +1 -> 0 -> -1 -> -2 -> 0
    #   Wave C (120..136): Stretto 2-beat interlocking hocket across F(20..24) & C(-2..+2)!
    wave_a_planes = [
        (88.0, 91.0, C - 2, "maj"),
        (91.0, 94.0, C - 1, "maj"),
        (94.0, 97.0, C, "add9"),
        (97.0, 100.0, C + 1, "maj"),
        (100.0, 103.0, C + 2, "maj"),
        (103.0, 104.0, G, "dom7"),
    ]
    solo_order_a = ["clarinet", "viola", "english_horn", "cello", "french_horn"]
    for idx, (b0, b1, rpc, qual) in enumerate(wave_a_planes):
        sp = sb.add_span(b0, b1, rpc, qual, f"II.A1 Staircase {idx}")
        if idx < 5:
            k = idx - 2
            dyn = 0.42 + 0.06 * idx
            solo = solo_order_a[idx]
            oct_s = 3 if solo in ("cello", "french_horn") else 4
            # Crisp classical 4-note rhythmic subject on C & G (BOTH buckets collapse in 12-TET!)
            sb.lyrical_line(solo, [
                (b0, 0.70, pitch(C, oct_s, k), dyn + 0.14),
                (b0 + 0.75, 0.22, pitch(G, oct_s, k), dyn + 0.08),
                (b0 + 1.00, 0.90, pitch(C, oct_s, k), dyn + 0.16),
                (b0 + 2.00, 0.82, pitch(G, oct_s, k), dyn + 0.10),
            ], vibrato=0.22, comma_glide=False)
            # Pizzicato & Bassoon light classical pulse
            sb.note("pizzicato", b0, 0.45, pitch(C, 3, k), dyn)
            sb.note("pizzicato", b0 + 1.5, 0.45, pitch(G, 3, k), dyn * 0.9)
            if idx % 2 == 0:
                sb.note("bassoon", b0, 2.4, sp.bass_root(), dyn * 0.92, swell="dim")
            sb.piano_figuration(sp, vel=dyn * 0.82, style="canon", step_beats=0.5, use_pedal=False)
        else:
            sb.chord("string_ensemble", b0, 0.88, sp.open_voicing(False), 0.56, swell="cresc")

    wave_b_planes = [
        (104.0, 107.0, G + 2, "dom7"),
        (107.0, 110.0, G + 1, "dom7"),
        (110.0, 113.0, G, "dom9"),
        (113.0, 116.0, G - 1, "dom7"),
        (116.0, 119.0, G - 2, "maj"),
        (119.0, 120.0, C, "maj"),
    ]
    solo_order_b = ["english_horn", "clarinet", "viola", "french_horn", "cello"]
    for idx, (b0, b1, rpc, qual) in enumerate(wave_b_planes):
        sp = sb.add_span(b0, b1, rpc, qual, f"II.A2 Mirror {idx}")
        if idx < 5:
            k = 2 - idx
            dyn = 0.64 - 0.04 * idx
            solo = solo_order_b[idx]
            oct_s = 3 if solo in ("cello", "french_horn") else 4
            # Inverted motif on G ({29..33} -> ALL MIDI 67) & F_harm ({20..24} -> ALL MIDI 65!)
            # Note: G(31) + HARM_7(43) = 74 ≡ 21 (F-1)! For k in {-1..+2}, 21+k in {20..23} -> ALL MIDI 65!
            top_pc = (G + HARM_7) % OCT if qual.startswith("dom") else (G + M3) % OCT
            sb.lyrical_line(solo, [
                (b0, 0.45, pitch(G, oct_s, k), dyn + 0.12),
                (b0 + 0.50, 0.45, pitch(top_pc, oct_s, k), dyn + 0.14),
                (b0 + 1.00, 1.10, pitch(G, oct_s, k), dyn + 0.16),
                (b0 + 2.20, 0.62, pitch(D, oct_s, k), dyn + 0.08),
            ], vibrato=0.24)
            sb.harp_sweep(sp, b0, pitch(G, 2, k) + OCT, pitch(G, 5, k), vel=dyn * 0.90, spacing=0.20, note_dur=1.3, ascending=(idx % 2 == 0), max_notes=6)
            sb.note("pizzicato", b0 + 1.0, 0.40, pitch(D, 3, k), dyn * 0.88)
        else:
            sb.chord("string_ensemble", b0, 0.88, sp.open_voicing(False), 0.52)

    # Stretto Hocket (120..136): 8 rapid 2-beat steps zig-zagging across k = -2, 0, -1, +1, 0, +2, +1, 0 on F!
    stretto_ks = [-2, 0, -1, +1, 0, +2, +1, 0]
    for idx, k in enumerate(stretto_ks):
        b0 = 120.0 + idx * 2.0
        sp = sb.add_span(b0, b0 + 2.0, F + k, "maj", f"II.A3 Stretto F(k={k:+d})")
        dyn = 0.48 + 0.035 * idx
        # Interlocking 8th-note hocket: Clarinet (F4: 20..24) <-> Viola (C4: -2..+2) <-> Pizzicato!
        sb.note("clarinet", b0, 0.42, pitch(F, 4, k), dyn + 0.10)
        sb.note("viola", b0 + 0.5, 0.42, pitch(C, 4, k), dyn + 0.08)
        sb.note("english_horn", b0 + 1.0, 0.42, pitch(F, 4, k), dyn + 0.12)
        sb.note("cello", b0 + 1.5, 0.40, pitch(C, 3, k), dyn + 0.10)
        sb.note("pizzicato", b0, 0.35, pitch(F, 3, k), dyn * 0.90)
        sb.note("pizzicato", b0 + 1.0, 0.35, pitch(C, 4, k), dyn * 0.88)
        if k >= -1:
            # A4+k for k in {-1,0,1,2} = {38,39,40,41} -> ALL MIDI 69 (A4)!
            sb.note("piano", b0 + 0.25, 0.65, pitch(A, 4, k), dyn * 0.92)
            sb.note("piano", b0 + 1.25, 0.60, pitch(F, 5, k), dyn * 0.95)

    # II.B (136..192): FOUR-VOICE LOCKSTEP COMMA FUGATO!
    # 12 one-beat microtonal planes per exposition so EVERY contrapuntal voice steps
    # directly across 4 syntonic commas inside a single 12-TET MIDI key bucket!
    fugato_k_12 = [-1, 0, +1, +2, +1, 0, -1, 0, +1, +2, +1, 0]

    # Exposition 1 (136..148): Solo Viola Subject (E4: 16..19 -> G4: 30..33) + Pizzicato
    viola_exp1 = []
    pizz_exp1 = []
    for i, k in enumerate(fugato_k_12):
        b0 = 136.0 + i * 1.0
        sb.add_span(b0, b0 + 1.0, C + k, "maj", f"II.B Exp1 k={k:+d}")
        pizz_exp1.append((b0, 0.42, pitch(C, 3, k), 0.48))
        target_pc = E if i < 6 else G
        viola_exp1.append((b0, 0.88, pitch(target_pc, 4, k), 0.56 + 0.015 * i))
    sb.lyrical_line("viola", viola_exp1, vibrato=0.28, comma_glide=True)
    sb.lyrical_line("pizzicato", pizz_exp1, vibrato=0.0, comma_glide=False)

    # Exposition 2 (148..160): Clarinet Subject (G4: 30..33 -> D5: 61..64) + Viola CS (E4: 16..19 -> C4: -1..+2) + Piano
    clar_exp2 = []
    viola_exp2 = []
    piano_exp2 = []
    for i, k in enumerate(fugato_k_12):
        b0 = 148.0 + i * 1.0
        sb.add_span(b0, b0 + 1.0, C + k, "add9", f"II.B Exp2 k={k:+d}")
        dyn = 0.58 + 0.015 * i
        piano_exp2.append((b0 + 0.5, 0.42, pitch(C, 5, k), dyn * 0.86))
        if i not in (5, 11):  # Breathing rests!
            c_pc, c_oct = (G, 4) if i < 6 else (D, 5)
            clar_exp2.append((b0, 0.88, pitch(c_pc, c_oct, k), dyn + 0.10))
        v_pc = E if i >= 6 else C
        viola_exp2.append((b0, 0.88, pitch(v_pc, 4, k), dyn + 0.05))
    sb.lyrical_line("clarinet", clar_exp2, vibrato=0.20, comma_glide=True)
    sb.lyrical_line("viola", viola_exp2, vibrato=0.26, comma_glide=True)
    sb.lyrical_line("piano", piano_exp2, vibrato=0.0, comma_glide=False)

    # Exposition 3 (160..172): Cello Subject (C3 -> G3) + Clarinet Septimal CS (Bb4: 42..45) + Viola (E4: 16..19) + Harp
    cello_exp3 = []
    clar_exp3 = []
    viola_exp3 = []
    for i, k in enumerate(fugato_k_12):
        b0 = 160.0 + i * 1.0
        sp = sb.add_span(b0, b0 + 1.0, C + k, "dom9", f"II.B Exp3 Septimal k={k:+d}")
        dyn = 0.62 + 0.018 * i
        if i % 2 == 0:
            sb.harp_sweep(sp, b0, pitch(C, 3, k), pitch(D, 5, k), vel=dyn * 0.88, spacing=0.18, note_dur=0.78, max_notes=4)
        cello_exp3.append((b0, 0.88, pitch(C if i < 6 else G, 3, k), dyn + 0.10))
        if i not in (5, 11):
            clar_exp3.append((b0, 0.88, pitch(BB_HARM, 4, k), dyn + 0.10))
        viola_exp3.append((b0, 0.88, pitch(E, 4, k), dyn + 0.06))
    sb.lyrical_line("cello", cello_exp3, vibrato=0.30, comma_glide=True)
    sb.lyrical_line("clarinet", clar_exp3, vibrato=0.22, comma_glide=True)
    sb.lyrical_line("viola", viola_exp3, vibrato=0.26, comma_glide=True)

    # Exposition 4 (172..184): Full 4-Voice + French Horn + String Orchestra Climax on F9(k)!
    eh_exp4 = []
    horn_exp4 = []
    cello_exp4 = []
    for i, k in enumerate(fugato_k_12):
        b0 = 172.0 + i * 1.0
        sp = sb.add_span(b0, b0 + 1.0, F + k, "dom9", f"II.B Exp4 F9(k={k:+d})")
        dyn = 0.70 + 0.012 * i
        sb.string_pad(sp, vel=dyn * 0.86, swell="cresc" if i < 8 else "arch", trim_tail=0.08)
        if i % 4 == 0:
            sb.note("bassoon", b0, 0.88, sp.bass_root(), dyn * 0.90, swell="arch")
            sb.note("timpani", b0, 0.75, sp.bass_root(), dyn * 0.74, trim_to_chord=False)
        if i not in (5, 11):
            eh_exp4.append((b0, 0.88, pitch(A, 4, k), dyn + 0.10))       # {38..41} -> ALL MIDI 69 (A4)!
        if i not in (3, 9):
            horn_exp4.append((b0, 0.86, pitch(C, 4, k), dyn + 0.06))     # {-1..+2} -> ALL MIDI 60!
        cello_exp4.append((b0, 0.88, pitch(F, 3, k), dyn + 0.08))        # {-32..-29} -> ALL MIDI 53!
    sb.lyrical_line("english_horn", eh_exp4, vibrato=0.30, comma_glide=True)
    sb.lyrical_line("french_horn", horn_exp4, vibrato=0.18, comma_glide=True)
    sb.lyrical_line("cello", cello_exp4, vibrato=0.28, comma_glide=True)

    # Fugato Taper (184..192): Graceful classical cadence into C open fifth (p)
    s2_coda = [
        sb.add_span(184.0, 188.0, C + 1, "maj", "II.C1 C+"),
        sb.add_span(188.0, 192.0, C, "open5", "II.C2 C open5 bridge to Nocturne"),
    ]
    sb.string_pad(s2_coda[0], vel=0.58, swell="dim")
    sb.string_pad(s2_coda[1], vel=0.36, swell="dim")
    sb.lyrical_line("clarinet", [
        (184.0, 1.8, pitch(G, 4, 1), 0.62),
        (186.0, 1.8, pitch(E, 4, 1), 0.52),
        (188.2, 3.2, pitch(G, 4, 0), 0.38),
    ], vibrato=0.22, default_swell="dim")
    sb.note("cello", 188.0, 3.6, pitch(C, 3), 0.38, swell="dim")

    # =========================================================================
    # SECTION III (Beats 192..296): NOCTURNE OF THE VANISHING SHRUTIS
    # =========================================================================
    # III.A (192..228): THE MINOR-THIRD & SEVENTH PRISM over constant C(0) + G(31)!
    # 12 three-beat undulating shruti waves across [0, 12..15, 31, 43..46]!
    # In 12-TET: ALL 12 BARS = IDENTICAL STATIC Cm7 [60, 63, 67, 70] while Viola, English Horn & Sitar freeze!
    minor_wave_cycle = [
        ("submin7", SUB_m3, HARM_7),
        ("pyth_min7", PYTH_m3, PYTH_m7),
        ("min7", m3, JUST_m7),
        ("supmin7", SUP_m3, SUP_m7),
        ("min7", m3, JUST_m7),
        ("pyth_min7", PYTH_m3, PYTH_m7),
        ("submin7", SUB_m3, HARM_7),
        ("pyth_min7", PYTH_m3, PYTH_m7),
        ("min7", m3, JUST_m7),
        ("supmin7", SUP_m3, SUP_m7),
        ("min7", m3, JUST_m7),
        ("submin7", SUB_m3, HARM_7),
    ]
    eh_prism_m = []
    viola_prism_m = []
    sitar_prism_m = []
    for idx, (qual, th_iv, sev_iv) in enumerate(minor_wave_cycle):
        b0 = 192.0 + idx * 3.0
        sp = sb.add_span(b0, b0 + 3.0, C, qual, f"III.A Shruti {qual}")
        dyn = 0.42 + 0.04 * (idx % 4)
        sb.note("ektara", b0, 2.7, pitch(C, 3), dyn + 0.06, meend_cents=22.0)
        sb.note("dotara", b0 + 1.5, 1.2, pitch(G, 3), dyn * 0.94)
        if idx % 3 == 0:
            sb.note("bassoon", b0, 2.6, pitch(C, 2), dyn, swell="arch")
        sb.string_pad(sp, vel=dyn * 0.80, swell="arch", trim_tail=0.14)

        viola_prism_m.append((b0 + 0.1, 2.7, pitch(th_iv, 4), dyn + 0.10))       # {12..15} -> ALL Eb4!
        if idx not in (5, 11):
            eh_prism_m.append((b0 + 0.15, 2.65, pitch(sev_iv, 4), dyn + 0.14))   # {43..46} -> ALL Bb4!
        sitar_prism_m.append((b0 + 0.4, 2.3, pitch(th_iv, 4) if idx < 6 else pitch(sev_iv, 3), dyn + 0.12))
    sb.lyrical_line("viola", viola_prism_m, vibrato=0.34, comma_glide=True)
    sb.lyrical_line("english_horn", eh_prism_m, vibrato=0.36, comma_glide=True)
    sb.lyrical_line("sitar", sitar_prism_m, vibrato=0.0, comma_glide=True, leap_slide=24.0)

    # III.B (228..264): THE MAJOR-THIRD & LYDIAN-TRITONE SHRUTI PRISM!
    # Part 1 (228..246): 9 two-beat waves across {16,17,18,19} (ALL = E4!) & {47,48,49} (ALL = B4!)
    maj_wave_cycle = [
        ("grave_maj7", GRAVE_M3, GRAVE_M7),
        ("maj7", M3, M7),
        ("pyth_maj7", PYTH_M3, PYTH_M7),
        ("supmaj", SUP_M3, M7),
        ("pyth_maj7", PYTH_M3, PYTH_M7),
        ("maj7", M3, M7),
        ("grave_maj7", GRAVE_M3, GRAVE_M7),
        ("maj7", M3, M7),
        ("supmaj", SUP_M3, SUP_M2 + OCT),
    ]
    clar_maj_p = []
    cello_maj_p = []
    for idx, (qual, th_iv, _) in enumerate(maj_wave_cycle):
        b0 = 228.0 + idx * 2.0
        sp = sb.add_span(b0, b0 + 2.0, C, qual, f"III.B1 {qual}")
        dyn = 0.48 + 0.03 * (idx if idx <= 4 else 8 - idx)
        sb.string_pad(sp, vel=dyn * 0.82, swell="arch", trim_tail=0.10)
        if idx % 2 == 0:
            sb.harp_sweep(sp, b0 + 0.08, pitch(C, 3), pitch(G, 5), vel=dyn + 0.06, spacing=0.20, note_dur=1.4, max_notes=5)
        cello_maj_p.append((b0, 1.84, pitch(th_iv, 3), dyn + 0.10))          # {-37..-34} -> ALL MIDI 52!
        if idx not in (4, 8):
            clar_maj_p.append((b0 + 0.08, 1.76, pitch(th_iv, 4), dyn + 0.12))  # {16..19} -> ALL MIDI 64!
        else:
            sb.note("french_horn", b0 + 0.08, 1.76, pitch(th_iv, 4), dyn + 0.10, swell="arch", vibrato=0.20)
    sb.lyrical_line("clarinet", clar_maj_p, vibrato=0.26, comma_glide=True)
    sb.lyrical_line("cello", cello_maj_p, vibrato=0.34, comma_glide=True)

    # D-Root F#-Bucket Prism (246..264): 9 two-beat waves across {25, 26, 27, 28} -> ALL MIDI 66 (F#4)!
    d_wave_cycle = [
        ("grave_maj", 25),
        ("maj", 26),
        ("pyth_maj", 27),
        ("supmaj", 28),
        ("pyth_maj", 27),
        ("maj", 26),
        ("grave_maj", 25),
        ("maj", 26),
        ("pyth_maj", 27),
    ]
    sitar_d_p = []
    eh_d_p = []
    for idx, (qual, fs_step) in enumerate(d_wave_cycle):
        b0 = 246.0 + idx * 2.0
        sp = sb.add_span(b0, b0 + 2.0, D, qual, f"III.B2 F#-Bucket step={fs_step}")
        dyn = 0.54 + 0.025 * (idx % 4)
        if idx % 2 == 0:
            sb.note("ektara", b0, 1.82, pitch(D, 3), dyn, meend_cents=24.0)
        sb.note("dotara", b0 + 1.0, 0.82, pitch(A, 3) + 1, dyn * 0.90)
        sb.string_pad(sp, vel=dyn * 0.78, swell="arch", trim_tail=0.10)
        sitar_d_p.append((b0 + 0.1, 1.74, fs_step, dyn + 0.14))
        if idx not in (4, 8):
            eh_d_p.append((b0 + 0.15, 1.70, fs_step, dyn + 0.12))
    sb.lyrical_line("sitar", sitar_d_p, comma_glide=True, leap_slide=28.0)
    sb.lyrical_line("english_horn", eh_d_p, vibrato=0.34, comma_glide=True)

    # III.C (264..296): Intimate Shruti-Debussy Dialogue & Whispered ppp Dissolve
    s3_coda_specs = [
        (264.0, 270.0, G, "dom9", "III.C1 G9 (7:4 F=21)"),
        (270.0, 276.0, C, "dom9", "III.C2 C9 (7:4 Bb=43)"),
        (276.0, 282.0, F, "dom9", "III.C3 F9 (7:4 Eb=12, A4=440Hz!)"),
        (282.0, 288.0, F, "maj9", "III.C4 F maj9 (15:8 E=17)"),
        (288.0, 296.0, C, "open5", "III.C5 Hushed ppp C5 abyss before Passacaglia"),
    ]
    for idx, (b0, b1, rpc, qual, lbl) in enumerate(s3_coda_specs):
        sp = sb.add_span(b0, b1, rpc, qual, lbl)
        dur = b1 - b0
        dyn = [0.50, 0.46, 0.42, 0.34, 0.24][idx]
        sb.string_pad(sp, vel=dyn * 0.80, swell="dim" if idx >= 3 else "arch", trim_tail=0.20)
        if idx < 4:
            sb.piano_figuration(sp, vel=dyn * 0.82, style="nocturne", step_beats=0.75)
            sb.note("cello", b0, dur - 0.4, sp.bass_root() + OCT, dyn + 0.08, vibrato=0.30, swell="arch")
        else:
            sb.note("ektara", b0 + 0.5, 3.2, pitch(C, 3), 0.26, meend_cents=26.0)
            sb.note("viola", b0 + 0.2, 6.8, pitch(G, 3), 0.24, swell="dim", vibrato=0.22)
    sb.lyrical_line("clarinet", [
        (264.4, 2.6, pitch(B, 4), 0.52),       # 31+17=48 (pure 5:4 over G!)
        (267.2, 2.4, 21, 0.50),                # 31+43=74≡21 (7:4 over G!)
        # Breath
        (270.5, 2.6, pitch(BB_HARM, 4), 0.48),
        (273.3, 2.3, pitch(E, 4), 0.44),
        # Breath
        (276.6, 2.8, pitch(EB_HARM, 4), 0.44),
        (282.6, 4.6, pitch(E, 4), 0.34),       # 12 (Eb_harm) -> 17 (E) pure modal sigh!
    ], vibrato=0.26, default_swell="dim")

    # =========================================================================
    # SECTION IV (Beats 296..416): PASSACAGLIA OF THE ENDLESS COMMA SPIRAL
    #   5 Upward 5-Limit Comma Pumps climbing k = -2 -> -1 -> 0 -> +1 -> +2 -> +3!
    #   Each pump: I(k) [4b] -> V(k+31) [4b] -> ii(k+9) [4b] -> IV(k+23) [4b] -> I(k+1)!
    #   Every transition holds an EXACT common tone in 53-EDO:
    #     I(k)->V(k+31) shares G(k+31); V->ii(k+9) shares D(k+9);
    #     ii->IV(k+23) shares F+(k+23) & A+(k+40); IV->I(k+1) shares C+(k+1)!
    #   In 12-TET: k = -2, -1, 0, +1, +2 ALL quantize to flat C-G-Dm-F (ZERO modulation
    #   for 80 beats!), then at k = +3 it suddenly lurches mid-phrase into C#/F#!
    # =========================================================================
    for pump_idx, k in enumerate([-2, -1, 0, +1, +2]):
        base_b = 296.0 + pump_idx * 16.0
        sp_I = sb.add_span(base_b, base_b + 4.0, C + k, "maj", f"IV.Var{pump_idx+1} I(k={k:+d})")
        sp_V = sb.add_span(base_b + 4.0, base_b + 8.0, G + k, "dom7" if pump_idx >= 2 else "maj", f"IV.Var{pump_idx+1} V(k={k:+d})")
        sp_ii = sb.add_span(base_b + 8.0, base_b + 12.0, D + k, "min7" if pump_idx >= 1 else "min", f"IV.Var{pump_idx+1} ii(k={k:+d})")
        sp_IV = sb.add_span(base_b + 12.0, base_b + 16.0, F + k + 1, "add9" if pump_idx >= 2 else "maj", f"IV.Var{pump_idx+1} IV+(k={k+1:+d})")
        var_spans = [sp_I, sp_V, sp_ii, sp_IV]

        if pump_idx == 0:
            # Variation 1 (k = -2 -> -1, p): Stalking Cello & Bassoon Ground Bass + Pizzicato & Viola Filigree
            for si, sp in enumerate(var_spans):
                br = sp.bass_root()
                sb.note("bassoon", sp.start, 3.4, br, 0.42 + 0.02 * si, swell="arch")
                sb.note("cello", sp.start, 1.8, br + OCT, 0.46 + 0.02 * si, vibrato=0.28, swell="arch")
                sb.note("cello", sp.start + 2.0, 1.7, br + OCT + P5, 0.44 + 0.02 * si, vibrato=0.24)
                r = sp.tenor_root()
                th = sp.third_offset()
                for sub in range(4):
                    sb.note("pizzicato", sp.start + sub + 0.5, 0.38, r + (P5 if sub % 2 == 0 else OCT + th), 0.40)
            sb.lyrical_line("viola", [
                (base_b + 0.5, 1.4, pitch(E, 4, k), 0.48),
                (base_b + 2.0, 1.8, pitch(G, 4, k), 0.50),
                (base_b + 4.0, 2.4, pitch(G, 4, k), 0.52),          # Exact common tone G!
                (base_b + 6.6, 1.2, pitch(D, 4, k), 0.48),
                (base_b + 8.0, 2.4, pitch(D, 4, k), 0.52),          # Exact common tone D!
                (base_b + 10.6, 1.2, pitch(A, 4, k + 1), 0.54),
                (base_b + 12.0, 3.6, pitch(A, 4, k + 1), 0.56),     # Exact common tone A+!
            ], vibrato=0.30)

        elif pump_idx == 1:
            # Variation 2 (k = -1 -> 0, mp): Flowing Piano Triplets + Clarinet & English Horn Canon
            for si, sp in enumerate(var_spans):
                dyn = 0.50 + 0.02 * si
                sb.piano_figuration(sp, vel=dyn, style="triplet", step_beats=2.0 / 3.0)
                sb.note("cello", sp.start, 3.6, sp.bass_root() + OCT, dyn + 0.04, vibrato=0.26, swell="arch")
            sb.lyrical_line("clarinet", [
                (base_b, 1.8, pitch(G, 4, k), 0.56),
                (base_b + 2.0, 1.8, pitch(E, 4, k), 0.54),
                (base_b + 4.0, 1.8, pitch(D, 5, k), 0.60),
                (base_b + 6.0, 1.6, pitch(B, 4, k), 0.58),
                # Breath 7.6..8.5
                (base_b + 8.5, 1.8, pitch(A, 4, k + 1), 0.60),
                (base_b + 10.5, 1.3, pitch(F, 4, k + 1), 0.58),
                (base_b + 12.0, 3.6, pitch(C, 5, k + 1), 0.64),
            ], vibrato=0.22)
            sb.lyrical_line("english_horn", [
                (base_b + 2.0, 1.8, pitch(C, 4, k), 0.52),
                (base_b + 4.0, 3.5, pitch(G, 4, k), 0.56),
                # Breath
                (base_b + 8.0, 3.6, pitch(D, 4, k), 0.58),
                (base_b + 12.2, 3.4, pitch(A, 4, k + 1), 0.60),
            ], vibrato=0.28)

        elif pump_idx == 2:
            # Variation 3 (k = 0 -> +1, mf): Harp Sweeps + Lush Strings + Soaring Cello/Viola Octaves
            for si, sp in enumerate(var_spans):
                dyn = 0.58 + 0.025 * si
                sb.string_pad(sp, vel=dyn, swell="arch")
                sb.harp_sweep(sp, sp.start, pitch(C, 3, k), pitch(G, 5, k + 1), vel=dyn + 0.08, spacing=0.18, note_dur=2.0, ascending=(si % 2 == 0), max_notes=8, with_pedal=True)
                if si != 2:
                    sb.note("bassoon", sp.start, 3.5, sp.bass_root(), dyn + 0.04, swell="arch")
            tenor_mel = [
                (base_b, 1.4, pitch(C, 4, k), 0.66),
                (base_b + 1.5, 0.45, pitch(D, 4, k), 0.64),
                (base_b + 2.0, 1.8, pitch(E, 4, k), 0.68),
                (base_b + 4.0, 2.8, pitch(G, 4, k), 0.72),
                (base_b + 7.0, 0.85, pitch(F, 4, k) - 1, 0.68),     # 7:4 of G!
                (base_b + 8.0, 2.8, pitch(F, 4, k + 1), 0.72),
                (base_b + 11.0, 0.85, pitch(A, 4, k + 1), 0.74),
                (base_b + 12.0, 3.7, pitch(C, 5, k + 1), 0.76),
            ]
            sb.lyrical_line("viola", tenor_mel, vibrato=0.32)
            sb.lyrical_line("cello", [(b, d, st - OCT, v * 0.96) for b, d, st, v in tenor_mel], vibrato=0.34)

        elif pump_idx == 3:
            # Variation 4 (k = +1 -> +2, f): Kinetic Dotara/Pizzicato Drive + Heroic French Horn & Woodwinds
            for si, sp in enumerate(var_spans):
                dyn = 0.68 + 0.025 * si
                sb.string_pad(sp, vel=dyn * 0.90, swell="cresc")
                sb.piano_figuration(sp, vel=dyn * 0.88, style="scherzo", step_beats=0.5, use_pedal=False)
                r = sp.tenor_root()
                for sub in range(4):
                    sb.note("dotara", sp.start + sub, 0.45, r + (0 if sub % 2 == 0 else P5), dyn * 0.92)
                    sb.note("pizzicato", sp.start + sub + 0.5, 0.35, r + OCT, dyn * 0.88)
                sb.note("bassoon", sp.start, 1.8, sp.bass_root(), dyn, swell="dim")
            sb.lyrical_line("french_horn", [
                (base_b, 3.6, pitch(G, 3, k), 0.74),
                (base_b + 4.0, 3.5, pitch(G, 3, k), 0.78),
                # Breath 7.5..8.2
                (base_b + 8.2, 3.5, pitch(A, 3, k + 1), 0.80),
                (base_b + 12.0, 3.6, pitch(C, 4, k + 1), 0.84),
            ], vibrato=0.20)
            sb.lyrical_line("clarinet", [
                (base_b + 0.5, 1.3, pitch(E, 5, k), 0.74),
                (base_b + 2.0, 1.8, pitch(C, 5, k), 0.76),
                (base_b + 4.5, 1.3, pitch(D, 5, k), 0.78),
                (base_b + 6.0, 1.6, pitch(B, 4, k), 0.76),
                (base_b + 8.5, 1.3, pitch(C, 5, k + 1), 0.80),
                (base_b + 10.0, 1.8, pitch(A, 4, k + 1), 0.82),
                (base_b + 12.5, 3.1, pitch(E, 5, k + 1), 0.84),
            ], vibrato=0.22)

        else:
            # Variation 5 (k = +2 -> +3, ff!): Full Symphonic Brass + Tremolo + Timpani Summit!
            for si, sp in enumerate(var_spans):
                dyn = 0.78 + 0.035 * si
                sb.string_pad(sp, vel=dyn, track_id="string_ensemble", swell="cresc")
                sb.string_pad(sp, vel=dyn * 0.86, track_id="tremolo_strings", include_9=False, swell="cresc")
                sb.piano_figuration(sp, vel=dyn * 0.90, style="grand", step_beats=0.5)
                br = sp.bass_root()
                if si != 2:
                    sb.note("trombone", sp.start, 3.5, br + OCT, dyn * 0.90, swell="cresc")
                    sb.note("bassoon", sp.start, 3.5, br, dyn * 0.92, swell="cresc")
                sb.note("timpani", sp.start, 1.2, br, dyn * 0.88, trim_to_chord=False)
                sb.note("timpani", sp.start + 2.0, 1.2, br, dyn * 0.82, trim_to_chord=False)
            sb.timpani_roll(base_b + 13.0, 2.8, var_spans[-1].bass_root(), 0.68, 0.92, spacing=0.25)
            sb.lyrical_line("french_horn", [
                (base_b, 3.6, pitch(C, 4, k), 0.84),
                (base_b + 4.0, 3.5, pitch(D, 4, k), 0.86),
                (base_b + 8.2, 3.5, pitch(F, 4, k + 1), 0.88),
                (base_b + 12.0, 3.7, pitch(A, 4, k + 1), 0.92),
            ], vibrato=0.22, default_swell="cresc")

    # Summit Arrival at k = +3 (376..384) + Triple Downward Comma Cascade (+3 -> +2 -> +1 -> 0, 384..416)!
    # At k = +3: C+++ = +3 (MIDI 61 C#4 in 12-TET!!), E+++ = 20 (MIDI 65 F4!!), G+++ = 34 (MIDI 68 Ab4!!)
    sp_summit = sb.add_span(376.0, 384.0, C + 3, "add9", "IV.Summit Blinding C+++(k=+3 -> C# in 12-TET!)")
    sb.string_pad(sp_summit, vel=0.92, track_id="string_ensemble", swell="sfz")
    sb.string_pad(sp_summit, vel=0.84, track_id="tremolo_strings", swell="dim")
    sb.note("trombone", 376.0, 5.5, pitch(C, 3, 3), 0.90, swell="sfz")
    sb.note("french_horn", 376.0, 5.5, pitch(G, 3, 3), 0.92, swell="sfz")
    sb.note("bassoon", 376.0, 5.5, sp_summit.bass_root(), 0.90, swell="dim")
    sb.note("timpani", 376.0, 2.0, sp_summit.bass_root(), 0.94, trim_to_chord=False)
    sb.harp_sweep(sp_summit, 376.2, pitch(C, 3, 3), pitch(G, 5, 3), vel=0.92, spacing=0.14, note_dur=3.2, max_notes=10, with_pedal=True)
    sb.lyrical_line("clarinet", [
        (376.0, 3.8, pitch(E, 5, 3), 0.92),
        (380.2, 3.4, pitch(D, 5, 3), 0.80),
    ], vibrato=0.26, default_swell="dim")
    sb.lyrical_line("english_horn", [
        (376.0, 3.8, pitch(G, 4, 3), 0.90),
        (380.2, 3.4, pitch(E, 4, 3), 0.78),
    ], vibrato=0.30, default_swell="dim")

    # Triple Downward Comma Cascade (384..416): 3 rapid 10-beat downward comma pumps (+3 -> +2 -> +1 -> 0) + 2-beat breath
    # Downward pump: I(k)[2.5b] -> IV(k+22)[2.5b] -> ii-(k+8)[2.5b] -> V-(k+30)[2.5b] -> I(k-1)!
    for c_idx, k in enumerate([+3, +2, +1]):
        b0 = 384.0 + c_idx * 10.0
        dyn_base = 0.78 - 0.16 * c_idx
        c_spans = [
            sb.add_span(b0, b0 + 2.5, C + k, "maj", f"IV.Down I(k={k:+d})"),
            sb.add_span(b0 + 2.5, b0 + 5.0, F + k, "maj", f"IV.Down IV(k={k:+d})"),
            sb.add_span(b0 + 5.0, b0 + 7.5, D_MINUS + k, "min_dm", f"IV.Down ii-(k={k:+d})"),
            sb.add_span(b0 + 7.5, b0 + 10.0, G_MINUS + k, "dom7", f"IV.Down V-(k={k-1:+d})"),
        ]
        for si, sp in enumerate(c_spans):
            v = dyn_base - 0.03 * si
            sb.string_pad(sp, vel=v, swell="sfz" if si == 0 else "dim", trim_tail=0.10)
            sb.note("cello", sp.start, 2.25, sp.bass_root() + OCT, v + 0.06, vibrato=0.28, swell="dim")
            if si in (0, 2):
                sb.note("bassoon", sp.start, 2.2, sp.bass_root(), v + 0.04, swell="dim")
            sb.piano_figuration(sp, vel=v * 0.85, style="canon", step_beats=0.5, use_pedal=False)
        sb.lyrical_line("viola", [
            (b0, 2.3, pitch(C, 4, k), dyn_base + 0.06),
            (b0 + 2.5, 2.3, pitch(C, 4, k), dyn_base + 0.04),      # Shared C!
            (b0 + 5.0, 2.3, pitch(A, 4, k), dyn_base + 0.02),      # Shared A!
            (b0 + 7.5, 2.2, pitch(F, 4, k - 1), dyn_base),         # Septimal 7:4 -> resolves to E(k-1)!
        ], vibrato=0.28)

    sp_pre_sch = sb.add_span(414.0, 416.0, C, "open5", "IV.End Hushed k=0 arrival")
    sb.note("pizzicato", 414.0, 0.4, pitch(C, 3), 0.36)
    sb.note("pizzicato", 415.0, 0.4, pitch(G, 3), 0.32)

    # =========================================================================
    # SECTION V (Beats 416..536): SCHERZO — THE DIESIS LABYRINTH
    #   V.A (416..464): Two Full Major-Third Diesis Ladders!
    #     Ladder 1 (416..440): C(0) -> Ab(36) -> E(19) -> C++(2)  (+2 diesis!)
    #     Ladder 2 (440..464): C++(2) -> Ab++(38) -> E++(21) -> C++++(4)!
    #       CRITICAL 12-TET BREAKAGE: [38, 2, 16] is a blazing pure 4:5:6 Major
    #       Triad in 53-EDO, yet 12-TET quantizes it to [69(A), 60(C), 64(E)] = A MINOR!!
    # =========================================================================
    diesis_ladder = [
        (416.0, 422.0, 0, "maj", 0, "V.A1 C(0) [0,17,31]"),
        (422.0, 428.0, 36, "maj", 0, "V.A2 Ab(36) [36,0,14] (holds C=0!)"),
        (428.0, 434.0, 19, "maj", 36, "V.A3 E+(19) [19,36,50] (holds Ab=36!)"),
        (434.0, 440.0, 2, "add9", 19, "V.A4 C++(2) [2,19,33] (+45.3c Diesis!)"),
        (440.0, 446.0, 2, "maj", 2, "V.A5 C++(2) launch"),
        (446.0, 452.0, 38, "maj", 2, "V.A6 Ab++(38) [38,2,16] -> SHEARS TO A MINOR IN 12-TET!"),
        (452.0, 458.0, 21, "maj", 38, "V.A7 E++(21) [21,38,52] -> SHEARS TO F MAJOR IN 12-TET!"),
        (458.0, 464.0, 4, "maj", 21, "V.A8 C++++(4) [4,21,35] (+90.6c Double Diesis!)"),
    ]
    for idx, (b0, b1, rpc, qual, common_pc, lbl) in enumerate(diesis_ladder):
        sp = sb.add_span(b0, b1, rpc, qual, lbl)
        dyn = 0.54 + 0.05 * idx
        # Shimmering Tremolo Strings + French Horn hold the EXACT motionless common tone across barlines!
        common_step = pitch(common_pc, 4)
        if common_step > 34:
            common_step -= OCT
        sb.note("tremolo_strings", b0, 5.7, common_step + OCT, dyn * 0.80, swell="cresc")
        if idx % 2 == 1:
            sb.note("french_horn", b0, 5.4, common_step, dyn + 0.08, swell="sfz", vibrato=0.18)
        # Agile Scherzo rhythm in Pizzicato, Piano & Strings
        sb.piano_figuration(sp, vel=dyn * 0.88, style="scherzo", step_beats=0.5, use_pedal=False)
        r = sp.tenor_root()
        th = sp.third_offset()
        for beat_off in (0.0, 2.0, 4.0):
            sb.chord("string_ensemble", b0 + beat_off, 1.4, [r, r + P5, r + OCT + th], dyn * 0.90, swell="sfz" if beat_off == 0.0 else "dim")
            sb.note("pizzicato", b0 + beat_off + 1.5, 0.38, r + OCT, dyn * 0.92)
        if idx >= 4:
            sb.note("trombone", b0, 4.8, sp.bass_root() + OCT, dyn * 0.86, swell="sfz")
            sb.note("timpani", b0, 1.2, sp.bass_root(), dyn * 0.85, trim_to_chord=False)
        else:
            sb.note("bassoon", b0, 4.8, sp.bass_root(), dyn * 0.88, swell="arch")

        # Nimble Clarinet & Viola Scherzo Subject dancing around each pure triad
        if idx % 2 == 0:
            sb.lyrical_line("clarinet", [
                (b0, 0.42, r + OCT, dyn + 0.10),
                (b0 + 0.5, 0.42, r + OCT + th, dyn + 0.12),
                (b0 + 1.0, 0.85, r + OCT + P5, dyn + 0.14),
                (b0 + 2.5, 0.42, r + OCT + th, dyn + 0.10),
                (b0 + 3.0, 1.8, r + 2 * OCT, dyn + 0.16),
            ], vibrato=0.18, comma_glide=False)
        else:
            sb.lyrical_line("english_horn", [
                (b0, 0.85, r + OCT + th, dyn + 0.12),
                (b0 + 1.0, 0.42, r + OCT, dyn + 0.10),
                (b0 + 1.5, 0.42, r + P5, dyn + 0.08),
                (b0 + 2.0, 2.4, r + OCT + th, dyn + 0.14),
            ], vibrato=0.24, comma_glide=False)
        # Agile Solo Viola & Solo Cello Scherzo counterpoint spotlighting the common-tone & triad shift!
        sb.lyrical_line("viola", [
            (b0 + 0.5, 0.85, common_step, dyn + 0.06),
            (b0 + 1.5, 0.42, r + P5, dyn + 0.08),
            (b0 + 2.0, 0.85, r + OCT + th, dyn + 0.10),
            (b0 + 3.5, 1.9, common_step, dyn + 0.08),
        ], vibrato=0.24, comma_glide=True)
        sb.lyrical_line("cello", [
            (b0, 1.4, r, dyn + 0.08),
            (b0 + 2.0, 1.4, r + P5, dyn + 0.06),
            (b0 + 4.0, 1.6, r, dyn + 0.10),
        ], vibrato=0.26, comma_glide=True)

    # V.B (464..504): Trio — Direct +/-2 Diesis Mirror Confrontation (C++=+2 vs C--=-2, 90.6c apart, BOTH = C in 12-TET!)
    # Alternating every 4 beats with crisp 0.25-beat dramatic silences & septimal pivots!
    trio_specs = [
        (464.0, 468.0, C + 2, "maj", "V.B1 C++(+2 -> MIDI 60)"),
        (468.0, 472.0, C - 2, "maj", "V.B2 C--(-2 -> MIDI 60! -90.6c plunge!)"),
        (472.0, 476.0, C + 2, "dom7", "V.B3 C++7(+2 -> MIDI 60)"),
        (476.0, 480.0, C - 1, "dom7", "V.B4 C-7(-1 -> MIDI 60! -67.9c drop!)"),
        (480.0, 485.0, F + 2, "maj", "V.B5 F++(24 -> MIDI 65)"),
        (485.0, 490.0, F - 2, "maj", "V.B6 F--(20 -> MIDI 65! -90.6c plunge!)"),
        (490.0, 497.0, G + 2, "dom9", "V.B7 G++9(33 -> MIDI 67)"),
        (497.0, 504.0, G - 2, "dom7", "V.B8 G--7(29 -> MIDI 67! -90.6c plunge!)"),
    ]
    for idx, (b0, b1, rpc, qual, lbl) in enumerate(trio_specs):
        sp = sb.add_span(b0, b1, rpc, qual, lbl)
        dur = b1 - b0
        is_high = (idx % 2 == 0)
        dyn = 0.66 if is_high else 0.44   # Bright forte vs shadowed subito piano echo!
        r = sp.tenor_root()
        th = sp.third_offset()
        # Clean release 0.35 beats early so +/-2 juxtapositions have crystalline air between them!
        if is_high:
            sb.chord("piano", b0, 0.9, [r, r + P5, r + OCT + th], dyn + 0.08)
            sb.chord("piano", b0 + 1.5, 1.2, [r + P5, r + OCT, r + OCT + th], dyn + 0.06)
            sb.harp_sweep(sp, b0 + 0.2, r, r + 2 * OCT, vel=dyn + 0.06, spacing=0.16, note_dur=1.4, max_notes=7)
            sb.lyrical_line("clarinet", [
                (b0, 1.1, r + OCT + th, dyn + 0.12),
                (b0 + 1.3, 1.8, r + OCT + P5, dyn + 0.10),
            ], vibrato=0.20)
        else:
            # Shadowed chamber answer in Viola, Cello, Sitar & Dotara (-90.6c lower, yet IDENTICAL in 12-TET!)
            sb.chord("string_ensemble", b0 + 0.1, dur - 0.5, sp.open_voicing(False), dyn * 0.85, swell="arch")
            sb.note("dotara", b0 + 0.1, 0.9, r + P5, dyn + 0.08)
            sb.note("sitar", b0 + 0.6, 1.6, r + OCT, dyn + 0.10, slide_from_cents=28.0)
            sb.lyrical_line("viola", [
                (b0 + 0.1, 1.1, r + OCT + th, dyn + 0.12),
                (b0 + 1.3, dur - 1.8, r + P5, dyn + 0.08),
            ], vibrato=0.30)

    # V.C (504..536): Scherzo Climactic Return & Dissolve into Home Plane k = 0
    s5_return = [
        (504.0, 510.0, C, "maj", "V.C1 C(0)"),
        (510.0, 516.0, AB, "maj", "V.C2 Ab(36)"),
        (516.0, 522.0, 19, "maj", "V.C3 E+(19)"),
        (522.0, 526.0, 2, "maj", "V.C4 C++(2)"),
        # Double downward comma resolution (+2 -> +1 -> 0) via F+2 -> Dm+1 -> G+1 -> C0!
        (526.0, 529.0, F + 2, "maj", "V.C5 IV++"),
        (529.0, 532.0, G, "dom7", "V.C6 V7(0)"),
        (532.0, 536.0, C, "min7", "V.C7 Tragic C minor turn into Adagio Mesto"),
    ]
    for idx, (b0, b1, rpc, qual, lbl) in enumerate(s5_return):
        sp = sb.add_span(b0, b1, rpc, qual, lbl)
        dur = b1 - b0
        dyn = [0.74, 0.80, 0.86, 0.88, 0.72, 0.56, 0.38][idx]
        sb.string_pad(sp, vel=dyn * 0.90, swell="sfz" if idx < 4 else "dim", trim_tail=0.14)
        if idx < 5:
            sb.piano_figuration(sp, vel=dyn * 0.86, style="scherzo", step_beats=0.5, use_pedal=False)
            sb.note("timpani", b0, 1.1, sp.bass_root(), dyn * 0.84, trim_to_chord=False)
        if idx in (1, 2, 3):
            sb.note("trombone", b0, dur - 0.5, sp.bass_root() + OCT, dyn * 0.86, swell="cresc")
            sb.note("french_horn", b0, dur - 0.5, sp.tenor_root() + P5, dyn * 0.88, swell="sfz")
    sb.lyrical_line("cello", [
        (526.2, 2.5, pitch(F, 3, 2), 0.68),
        (529.2, 2.5, pitch(G, 3, 0), 0.54),
        (532.2, 3.4, pitch(EB, 3, 0), 0.40),
    ], vibrato=0.34, default_swell="dim")

    # =========================================================================
    # SECTION VI (Beats 536..632): ADAGIO MESTO — LAMENT ON THE BROKEN THIRD
    #   Hushed pp chamber transparency (vel 0.22..0.48) for wide orchestral LRA!
    #   Exposed long beat-free chords + weeping 4-comma melodic descents on E4
    #   (19 -> 18 -> 17 -> 16 = ALL E4 in 12-TET!) & A4 (41 -> 40 -> 39 -> 38 = ALL A4!).
    # =========================================================================
    # VI.A (536..576): Weeping 4-Comma Descents in Exposed Strings, Brass Chorale & Double Reeds
    lament_planes = [
        # Wave 1 (536..556): E4 weeping descent 19 -> 18 -> 17 -> 16 (5 beats each, pp!)
        (536.0, 541.0, C + 2, "maj", pitch(E, 4, 2), pitch(G, 3, 2)),
        (541.0, 546.0, C + 1, "maj", pitch(E, 4, 1), pitch(G, 3, 1)),
        (546.0, 551.0, C, "maj7", pitch(E, 4, 0), pitch(G, 3, 0)),
        (551.0, 556.0, C - 1, "maj", pitch(E, 4, -1), pitch(G, 3, -1)),
        # Wave 2 (556..576): A4 (440 Hz!) weeping descent 41 -> 40 -> 39 -> 38 over F(k = +2 -> +1 -> 0 -> -1)!
        (556.0, 561.0, F + 2, "maj", pitch(A, 4, 2), pitch(C, 4, 2)),
        (561.0, 566.0, F + 1, "maj", pitch(A, 4, 1), pitch(C, 4, 1)),
        (566.0, 571.0, F, "maj9", pitch(A, 4, 0), pitch(C, 4, 0)),
        (571.0, 576.0, F - 1, "maj", pitch(A, 4, -1), pitch(C, 4, -1)),
    ]
    eh_lament = []
    clar_lament = []
    viola_lament = []
    cello_lament = []
    piano_lament = []
    for idx, (b0, b1, rpc, qual, mel_step, inner_step) in enumerate(lament_planes):
        sp = sb.add_span(b0, b1, rpc, qual, f"VI.A Lament {idx+1}")
        v = [0.40, 0.38, 0.36, 0.35, 0.44, 0.42, 0.38, 0.36][idx]
        # Exposed, glass-still string + soft trombone/horn chorale (beats horribly at +14c in 12-TET!)
        sb.string_pad(sp, vel=v, swell="arch" if idx % 4 < 3 else "dim", trim_tail=0.18)
        if idx in (0, 2, 4, 6):
            sb.note("trombone", b0 + 0.2, 4.3, sp.bass_root() + OCT, v + 0.02, swell="arch")
            sb.note("french_horn", b0 + 0.2, 4.3, inner_step, v + 0.04, swell="arch", vibrato=0.16)
        # Sparse crystalline Piano teardrops stepping directly across E5 ({70..73}->MIDI 76) & A5 ({91..94}->MIDI 81)
        sb.add_pedal("piano", b0 + 0.05, 4.65)
        piano_lament.append((b0 + 0.6, 3.8, mel_step + OCT, v + 0.06))

        if idx not in (3, 7):  # Human breathing rests at the end of each 4-bar sigh!
            eh_lament.append((b0 + 0.15, 4.45, mel_step, v + 0.12))
        if idx in (1, 2, 3, 5, 6, 7):
            clar_lament.append((b0 + 1.2, 3.3, inner_step + OCT, v + 0.08))
        viola_lament.append((b0 + 0.10, 4.55, inner_step, v + 0.08))
        cello_lament.append((b0, 4.65, sp.bass_root() + OCT, v + 0.08))

    sb.lyrical_line("english_horn", eh_lament, vibrato=0.38, comma_glide=True)
    sb.lyrical_line("clarinet", clar_lament, vibrato=0.28, comma_glide=True)
    sb.lyrical_line("viola", viola_lament, vibrato=0.36, comma_glide=True)
    sb.lyrical_line("cello", cello_lament, vibrato=0.34, comma_glide=True)
    sb.lyrical_line("piano", piano_lament, vibrato=0.0, comma_glide=False)

    # VI.B (576..608): Glass Cathedral of 4:5:6:7:9 Septimal Resonance (p -> mf)
    s6_glass = [
        (576.0, 584.0, F, "maj9", "VI.B1 Pure F maj9 (A4=440Hz)"),
        (584.0, 592.0, F, "dom9", "VI.B2 Pure Septimal F9 (Eb_harm=12)"),
        (592.0, 600.0, BB, "maj9", "VI.B3 Pure Bb maj9"),
        (600.0, 608.0, C, "dom9", "VI.B4 Pure Septimal C9 (Bb_harm=43)"),
    ]
    for idx, (b0, b1, rpc, qual, lbl) in enumerate(s6_glass):
        sp = sb.add_span(b0, b1, rpc, qual, lbl)
        v = [0.34, 0.42, 0.48, 0.44][idx]
        sb.string_pad(sp, vel=v, swell="arch", trim_tail=0.20)
        sb.harp_sweep(sp, b0 + 0.3, pitch(C, 3), pitch(F, 6) - 6, vel=v + 0.10, spacing=0.28, note_dur=3.8, max_notes=9, with_pedal=True)
        if idx % 2 == 0:
            sb.note("bassoon", b0 + 0.2, 6.8, sp.bass_root(), v + 0.04, swell="arch")
        sb.note("ektara", b0 + 0.4, 3.6, sp.bass_root() + OCT, v + 0.04, meend_cents=20.0)

    sb.lyrical_line("clarinet", [
        (576.6, 3.4, pitch(A, 4), 0.42),
        (580.4, 3.2, pitch(G, 4), 0.46),
        # Breath
        (584.6, 3.8, pitch(EB_HARM, 5), 0.52),
        (588.8, 2.8, pitch(G, 4), 0.46),
        # Breath
        (592.6, 3.6, pitch(D_MINUS, 5), 0.56),
        (596.5, 3.1, pitch(A, 4), 0.52),
        # Breath
        (600.6, 4.0, pitch(BB_HARM, 4), 0.54),
        (605.0, 2.6, pitch(D, 5), 0.48),
    ], vibrato=0.28)
    sb.lyrical_line("sitar", [
        (585.2, 2.2, pitch(EB_HARM, 4), 0.44),
        (587.8, 2.4, pitch(C, 4), 0.42),
        (601.2, 2.4, pitch(BB_HARM, 3), 0.44),
        (604.0, 2.6, pitch(G, 3), 0.40),
    ], comma_glide=True, leap_slide=24.0)

    # VI.C (608..632): Awakening Contrapuntal Bridge toward the Finale (p -> mf, 63->65 BPM)
    s6_bridge = [
        (608.0, 612.0, D_MINUS, "min_dm", "VI.C1 Dm-"),
        (612.0, 616.0, BB, "maj", "VI.C2 Bb"),
        (616.0, 620.0, G_MINUS, "min_dm", "VI.C3 Gm-"),
        (620.0, 624.0, C, "maj", "VI.C4 C"),
        (624.0, 628.0, C + 1, "dom7", "VI.C5 C+7 comma lift"),
        (628.0, 632.0, C, "dom9", "VI.C6 Dominant expectancy"),
    ]
    for idx, (b0, b1, rpc, qual, lbl) in enumerate(s6_bridge):
        sp = sb.add_span(b0, b1, rpc, qual, lbl)
        v = 0.40 + 0.05 * idx
        sb.string_pad(sp, vel=v, track_id="tremolo_strings" if idx >= 3 else "string_ensemble", swell="cresc")
        sb.piano_figuration(sp, vel=v * 0.86, style="nocturne", step_beats=0.5)
        sb.note("cello", b0, 3.7, sp.bass_root() + OCT, v + 0.08, vibrato=0.30, swell="cresc")
    sb.timpani_roll(628.0, 3.8, pitch(C, 2), 0.36, 0.72, spacing=0.25)

    # =========================================================================
    # SECTION VII (Beats 632..736): FINALE & CATHEDRAL ORGAN APOTHEOSIS
    #   VII.A (632..664): Symphonic Synthesis & Celebratory Comma Wave (mf -> f)
    #   VII.B (664..708): CATHEDRAL PIPE ORGAN ENTRANCE (first & only appearance!)
    #                     + Full 17-Track Symphonic Apotheosis (f -> ff)
    #   VII.C (708..736): Transcendent Plagal Coda & Pure 4:5:6 F Major Stillness (ppp)
    # =========================================================================
    # VII.A (632..664): Symphonic Synthesis (Fivefold Motto + Shruti Ninths + Brass Fanfares)
    s7_gather = [
        (632.0, 636.0, F - 1, "maj", "VII.A1 F-(21)"),
        (636.0, 640.0, F, "add9", "VII.A2 F(22, A4=440Hz!)"),
        (640.0, 644.0, F + 1, "maj", "VII.A3 F+(23)"),
        (644.0, 648.0, F + 2, "dom9", "VII.A4 F++9(24)"),
        (648.0, 652.0, BB + 2, "maj9", "VII.A5 Bb++9"),
        (652.0, 656.0, G, "min9", "VII.A6 Gm9"),
        (656.0, 660.0, C, "dom7", "VII.A7 C7(43)"),
        (660.0, 664.0, C, "dom9", "VII.A8 C9(4:5:6:7:9) Herald to Organ!"),
    ]
    for idx, (b0, b1, rpc, qual, lbl) in enumerate(s7_gather):
        sp = sb.add_span(b0, b1, rpc, qual, lbl)
        dyn = 0.66 + 0.03 * idx
        sb.string_pad(sp, vel=dyn * 0.90, swell="cresc")
        sb.piano_figuration(sp, vel=dyn * 0.88, style="grand", step_beats=0.5)
        sb.note("cello", b0, 1.85, sp.bass_root() + OCT, dyn + 0.06, vibrato=0.30)
        sb.note("cello", b0 + 2.0, 1.80, sp.bass_root() + OCT + P5, dyn + 0.04, vibrato=0.28)
        if idx % 2 == 0:
            sb.note("bassoon", b0, 3.6, sp.bass_root(), dyn * 0.92, swell="cresc")
            sb.harp_sweep(sp, b0, pitch(C, 3), pitch(F, 6) - 5, vel=dyn * 0.92, spacing=0.16, note_dur=2.2, max_notes=9)
        if idx >= 4:
            sb.note("french_horn", b0, 3.5, sp.tenor_root() + P5, dyn * 0.92, swell="cresc", vibrato=0.20)
    # Clarinet & English Horn soar across the 4-comma A4 bucket ({38,39,40,41} -> ALL MIDI 69!) with clean breaths
    sb.lyrical_line("clarinet", [
        (632.0, 3.6, pitch(A, 4, -1), 0.74),
        (636.0, 3.6, pitch(A, 4, 0), 0.78),
        (640.0, 3.1, pitch(A, 4, +1), 0.82),
        # Clean 0.90b breath 643.1..644.0
        (644.0, 3.1, pitch(A, 4, +2), 0.86),
        (648.0, 3.6, pitch(D_MINUS, 5, 2), 0.86),
        (652.0, 3.1, pitch(D, 5, 0), 0.86),
        # Clean 0.90b breath 655.1..656.0
        (656.0, 3.5, pitch(BB_HARM, 4, 0), 0.88),
        (660.0, 3.0, pitch(D, 5, 0), 0.92),
        # Clean 1.00b breath 663.0..664.0 before Organ Apotheosis!
    ], vibrato=0.26, comma_glide=True)
    sb.timpani_roll(660.0, 3.85, pitch(C, 2), 0.65, 0.94, spacing=0.20)

    # VII.B (664..708): CATHEDRAL PIPE ORGAN APOTHEOSIS!
    apoth_specs = [
        (664.0, 669.5, F, "add9", "VII.B1 ORGAN ENTRANCE: Pure F add9 (A4=440Hz!)"),
        (669.5, 675.0, C, "dom9", "VII.B2 Septimal C9 (4:5:6:7:9)"),
        (675.0, 680.5, D_MINUS, "min_dm", "VII.B3 Noble Dm-"),
        (680.5, 686.0, A, "min7", "VII.B4 Radiant Am7 (39,0,17,31)"),
        (686.0, 691.5, BB, "add9", "VII.B5 Soaring Bb add9 (pure 4:5:6:9 without M7/root rub!)"),
        (691.5, 697.0, F, "dom9", "VII.B6 Septimal F9 (Eb_harm=12)"),
        (697.0, 702.5, C, "dom9", "VII.B7 Climactic Septimal C9"),
        (702.5, 708.0, F, "add9", "VII.B8 Cathedral Crown on F add9 (A4=440Hz!)"),
    ]
    organ_vels = [0.68, 0.74, 0.78, 0.82, 0.86, 0.88, 0.92, 0.94]
    apoth_mel = []
    eh_apoth = []
    viola_apoth = []
    for idx, (b0, b1, rpc, qual, lbl) in enumerate(apoth_specs):
        sp = sb.add_span(b0, b1, rpc, qual, lbl)
        dur = b1 - b0
        ov = organ_vels[idx]
        br = sp.bass_root()
        r_ten = sp.tenor_root()
        th = sp.third_offset()

        # Wide, mud-free Cathedral Pipe Organ voicings strictly <= C5 (step 53)!
        org_top1 = r_ten + OCT + th
        if org_top1 > 53:
            org_top1 -= OCT
        org_top2 = r_ten + OCT + P5
        if org_top2 > 53:
            org_top2 -= OCT
        org_v = sorted({br, br + OCT, r_ten + P5, org_top1, org_top2})
        sb.chord("church_organ", b0, dur - 0.16, org_v, ov, swell="cresc" if idx < 6 else "sfz")

        sb.string_pad(sp, vel=ov * 0.92, track_id="string_ensemble", swell="arch")
        sb.string_pad(sp, vel=ov * 0.80, track_id="tremolo_strings", include_9=False, include_7=False, swell="cresc")
        sb.piano_figuration(sp, vel=ov * 0.86, style="grand", step_beats=0.5)
        sb.harp_sweep(sp, b0 + 0.1, pitch(C, 3), pitch(C, 6), vel=ov * 0.94, spacing=0.15, note_dur=2.6, ascending=(idx % 2 == 0), max_notes=10, with_pedal=True)

        # Brass & Bassoon phrase in 2-bar (11-beat) arches with >= 1.0-beat breathing rests!
        breath_bar = (idx % 2 == 1)
        w_dur = (dur - 1.05) if breath_bar else (dur - 0.25)
        if idx != 3:
            sb.note("trombone", b0, w_dur, br + OCT, ov * 0.88, swell="sfz" if idx in (0, 7) else "arch")
            sb.note("bassoon", b0, w_dur, br, ov * 0.90, swell="arch")
        if idx not in (2, 5):
            sb.note("french_horn", b0 + 0.1, w_dur - 0.1, r_ten + P5, ov * 0.92, swell="arch", vibrato=0.20)

        sb.note("cello", b0, dur * 0.5 - 0.1, br + OCT, ov * 0.94, vibrato=0.32)
        sb.note("cello", b0 + dur * 0.5, dur * 0.5 - 0.2, br + P5, ov * 0.90, vibrato=0.28)
        sb.note("dotara", b0, 0.9, r_ten + OCT, ov * 0.84)
        sb.note("ektara", b0, 2.4, br + OCT, ov * 0.82, meend_cents=20.0)
        if idx in (0, 4, 6, 7):
            sb.note("timpani", b0, 1.5, br, ov * 0.90, trim_to_chord=False)
            if idx == 6:
                sb.timpani_roll(b0 + 2.5, dur - 2.65, br, 0.72, 0.95, spacing=0.22)

    # Grand Anthemic Apotheosis Melody in Clarinet, English Horn & Viola (with >= 1.0b breaths every ~11b!)
    apoth_mel = [
        (664.0, 2.6, pitch(A, 4), 0.88),
        (666.8, 1.2, pitch(C, 5), 0.90),
        (668.1, 1.2, pitch(G, 4), 0.86),
        (669.5, 2.6, pitch(BB_HARM, 4), 0.92),
        (672.2, 1.8, pitch(D, 5), 0.90),
        # Breath 674.0..675.2 (1.20b!)
        (675.2, 2.8, pitch(A, 4), 0.90),
        (678.2, 2.0, pitch(D_MINUS, 5), 0.94),
        (680.5, 2.6, pitch(E, 5), 0.92),
        (683.2, 1.8, pitch(C, 5), 0.88),
        # Breath 685.0..686.2 (1.20b!)
        (686.2, 2.8, pitch(D_MINUS, 5), 0.94),
        (689.2, 2.0, pitch(C, 5), 0.95),
        (691.5, 2.6, pitch(EB_HARM, 5), 0.94),
        (694.2, 1.8, pitch(C, 5), 0.92),
        # Breath 696.0..697.1 (1.10b!)
        (697.1, 2.5, pitch(E, 5), 0.95),
        (699.8, 1.2, pitch(D, 5), 0.94),
        (701.1, 1.2, pitch(BB_HARM, 4), 0.92),
        (702.5, 4.6, pitch(A, 4), 0.96),         # Crowns on exact 440.00 Hz!
    ]
    sb.lyrical_line("clarinet", apoth_mel, vibrato=0.26)
    eh_apoth = [(b, d, st - OCT if st > 53 else st, v * 0.93) for b, d, st, v in apoth_mel]
    sb.lyrical_line("english_horn", eh_apoth, vibrato=0.30)
    for b, d, st, v in apoth_mel:
        sp_at = sb.span_at(b)
        vst = sp_at.nearest_step(st - M3 - (OCT if st >= pitch(D, 5) else 0), allow_melody=False)
        viola_apoth.append((b, d, vst, v * 0.88))
    sb.lyrical_line("viola", viola_apoth, vibrato=0.32)

    # VII.C (708..736): Serene Plagal Coda & Beat-Free 4:5:6 F Major Stillness (mf -> ppp)
    coda_specs = [
        (708.0, 714.0, BB, "add9", "VII.C1 Plagal Bb add9 / F pedal", F),
        (714.0, 720.0, F, "dom9", "VII.C2 Septimal F9 farewell", F),
        (720.0, 727.0, F, "add9", "VII.C3 Luminous F add9", F),
        (727.0, 736.0, F, "maj", "VII.C4 Final Beat-Free 4:5:6 F Major Stillness (A4=440Hz)", F),
    ]
    coda_org_v = [0.62, 0.46, 0.34, 0.22]
    for idx, (b0, b1, rpc, qual, lbl, ped) in enumerate(coda_specs):
        sp = sb.add_span(b0, b1, rpc, qual, lbl, ped)
        dur = b1 - b0
        ov = coda_org_v[idx]
        br = sp.bass_root()   # Deep F2 (-84) across entire Coda!
        if idx < 3:
            sb.chord("church_organ", b0, dur - 0.20, [br, br + OCT, pitch(C, 4), pitch(A, 4)], ov, swell="dim")
        else:
            # Final glass-pure 4:5:6 F Major chord [F2, F3, C4, F4, A4=440Hz] strictly <= C5 (53)!
            sb.chord("church_organ", b0, dur - 0.60, [br, br + OCT, pitch(C, 4), pitch(F, 4), pitch(A, 4)], ov, swell="dim")

        sb.string_pad(sp, vel=ov * 0.95, include_9=(idx < 3), swell="dim", trim_tail=0.30)
        # Bassoon breathes >= 1.0b between coda phrases!
        sb.note("bassoon", b0, dur - 1.05, br, ov * 0.90, swell="dim")
        sb.note("cello", b0, dur - 0.50, br + OCT, ov * 0.92, vibrato=0.22, swell="dim")
        sb.harp_sweep(sp, b0 + 0.3, pitch(F, 3), pitch(C, 6), vel=ov + 0.10, spacing=0.30, note_dur=3.8, max_notes=8, with_pedal=True)

    # Last tender French Horn, English Horn & Piano bell echoes into silence
    sb.lyrical_line("french_horn", [
        (708.4, 5.0, pitch(D_MINUS, 4), 0.52),
        (714.4, 5.0, pitch(EB_HARM, 4), 0.42),
        (727.4, 7.6, pitch(C, 4), 0.24),
    ], vibrato=0.16, default_swell="dim")
    sb.lyrical_line("english_horn", [
        (720.5, 5.8, pitch(G, 4), 0.34),
        (727.6, 7.4, pitch(A, 4), 0.22),
    ], vibrato=0.24, default_swell="dim")

    sb.add_pedal("piano", 720.2, 6.4)
    sb.add_pedal("piano", 727.2, 8.2)
    sb.lyrical_line("piano", [
        (720.6, 2.8, pitch(C, 5), 0.36),
        (723.6, 2.8, pitch(G, 4), 0.32),
        (727.8, 3.2, pitch(C, 5), 0.28),
        (731.4, 4.0, pitch(A, 4), 0.21),         # Final bell droplet on exact A4 = 440.00 Hz!
    ], vibrato=0.0, comma_glide=False)

    score = sb.build_dict()
    return sb, score


# =============================================================================
# Exact Replica of Rust `analyze` + 53-EDO vs 12-TET Collapse Quantitative Audit
# =============================================================================
def audit_score(sb: ScoreBuilder, score: Dict) -> None:
    errors: List[str] = []

    # 1. Pure stage-independence check
    for forbidden in ("reverb_rt60", "tail_seconds", "end_silence_seconds"):
        if forbidden in score:
            errors.append(f"Top-level score must omit '{forbidden}'")
    for tr in score["tracks"]:
        for forbidden in ("x", "y", "width", "gain", "warm_lowpass_hz"):
            if forbidden in tr:
                errors.append(f"Track '{tr['id']}' must omit inline '{forbidden}'")

    # 2. Exact SF2 15-channel polyphony, < C3 mud, comma clashes, organ timing & 12-TET collapse stats
    all_spans = []
    max_end_s = 0.0
    max_beat = 0.0
    total_notes = 0
    collapse_transitions = 0
    pitched_transitions = 0
    solo_collapse = 0
    solo_transitions = 0
    SOLO_IDS = {"clarinet", "english_horn", "viola", "cello", "french_horn", "sitar"}
    swell_count = 0
    vib_count = 0
    slide_count = 0
    organ_first_beat: Optional[float] = None

    for tr in score["tracks"]:
        tid = tr["id"]
        inst = tr["instrument"]
        is_perc = inst == "timpani"
        is_sf2 = inst not in ("ektara", "dotara")
        notes = tr["notes"]
        total_notes += len(notes)

        evs = []
        for idx, n in enumerate(notes):
            b0 = n["beat"]
            b1 = b0 + n["dur"]
            s0 = sb.tempo.beat_to_seconds(b0)
            s1 = max(s0 + 0.01, sb.tempo.beat_to_seconds(b1))
            max_beat = max(max_beat, b1)
            max_end_s = max(max_end_s, s1)
            evs.append((s0, 1, b0))
            evs.append((s1, -1, b0))
            all_spans.append((s0, s1, b0, n["step"], tid, is_perc))

            if inst == "church_organ":
                if organ_first_beat is None or b0 < organ_first_beat:
                    organ_first_beat = b0
            if n.get("swell") or n.get("breath_swell"):
                swell_count += 1
            if n.get("vibrato", 0.0) > 0.0:
                vib_count += 1
            if abs(n.get("slide_from_cents", 0.0)) > 0.0 or abs(n.get("meend_cents", 0.0)) > 0.0:
                slide_count += 1

            if idx > 0 and not is_perc:
                prev_st = notes[idx - 1]["step"]
                cur_st = n["step"]
                if prev_st != cur_st:
                    pitched_transitions += 1
                    is_col = edo53_to_12tet_midi(prev_st) == edo53_to_12tet_midi(cur_st)
                    if is_col:
                        collapse_transitions += 1
                    if tid in SOLO_IDS:
                        solo_transitions += 1
                        if is_col:
                            solo_collapse += 1

        evs.sort(key=lambda x: (x[0], x[1]))
        active = 0
        steals = 0
        for _, d, _ in evs:
            if d > 0:
                if is_sf2 and active >= 15:
                    steals += 1
                else:
                    active += 1
            else:
                active = max(0, active - 1)
        if steals > 0:
            errors.append(f"Track '{tid}' has {steals} SF2 voice steals!")

        # Sweet-spot register audit (SCORE_FORMAT.md §4)
        lo_sw, hi_sw = SWEET_SPOTS[tid]
        for n in notes:
            if not (lo_sw <= n["step"] <= hi_sw):
                errors.append(
                    f"Register out of sweet spot on '{tid}' at beat {n['beat']:.2f}: "
                    f"step={n['step']} not in [{lo_sw}, {hi_sw}]"
                )
                break

        # Wind/brass breathing audit (merging < 0.50b gaps -> max run <= 15.5b)
        if inst in WIND_BRASS and notes:
            max_run = 0.0
            max_run_start = notes[0]["beat"]
            cur_s = notes[0]["beat"]
            cur_e = cur_s + notes[0]["dur"]
            for n in notes[1:]:
                if n["beat"] - cur_e < 0.50:
                    cur_e = max(cur_e, n["beat"] + n["dur"])
                else:
                    if cur_e - cur_s > max_run:
                        max_run = cur_e - cur_s
                        max_run_start = cur_s
                    cur_s = n["beat"]
                    cur_e = cur_s + n["dur"]
            if cur_e - cur_s > max_run:
                max_run = cur_e - cur_s
                max_run_start = cur_s
            if max_run > 15.5:
                errors.append(
                    f"Unbreathed wind/brass run on '{tid}': {max_run:.2f}b starting at beat {max_run_start:.2f}"
                )

    if organ_first_beat is None or organ_first_beat < 650.0:
        errors.append(f"church_organ must be reserved strictly for Finale (got first beat={organ_first_beat})")

    # Sustained same-octave minor-second / semitone rub check (4..=6 steps absolute diff >= 1.0b)
    beat_spans = []
    for tr in score["tracks"]:
        if tr["instrument"] == "timpani":
            continue
        for n in tr["notes"]:
            if n["dur"] >= 1.0:
                beat_spans.append((n["beat"], n["beat"] + n["dur"], n["step"], tr["id"]))
    beat_spans.sort()
    for i in range(len(beat_spans)):
        b0_a, b1_a, st_a, tid_a = beat_spans[i]
        for j in range(i + 1, len(beat_spans)):
            b0_b, b1_b, st_b, tid_b = beat_spans[j]
            if b0_b >= b1_a - 1.0:
                break
            ov_b = min(b1_a, b1_b) - max(b0_a, b0_b)
            if ov_b >= 1.0 and 4 <= abs(st_a - st_b) <= 6:
                errors.append(
                    f"Sustained semitone rub ({abs(st_a - st_b)} steps, {ov_b:.2f}b) at beat {max(b0_a, b0_b):.2f}: "
                    f"{tid_a}({st_a}) vs {tid_b}({st_b})"
                )
                if len(errors) > 25:
                    break

    # Exact low-register mud check (< -53, overlap >= 0.08s, 0 < diff < 22)
    low_spans = sorted([s for s in all_spans if s[3] < -OCT and not s[5]], key=lambda x: x[0])
    for i in range(len(low_spans)):
        s0_a, s1_a, _, st_a, tid_a, _ = low_spans[i]
        for j in range(i + 1, len(low_spans)):
            s0_b, s1_b, b_b, st_b, tid_b, _ = low_spans[j]
            if s0_b >= s1_a - 0.08:
                break
            ov = min(s1_a, s1_b) - s0_b
            if ov >= 0.08 and 0 < abs(st_b - st_a) < P4:
                errors.append(f"Low mud at beat {b_b:.2f}: {tid_a}({st_a}) vs {tid_b}({st_b})")
                break

    # Exact comma-clash check (overlap >= 0.20s, 1 <= mod53_dist <= 3)
    pitched_spans = sorted([s for s in all_spans if not s[5]], key=lambda x: x[0])
    for i in range(len(pitched_spans)):
        s0_a, s1_a, b_a, st_a, tid_a, _ = pitched_spans[i]
        for j in range(i + 1, len(pitched_spans)):
            s0_b, s1_b, b_b, st_b, tid_b, _ = pitched_spans[j]
            if s0_b >= s1_a - 0.20:
                break
            ov = min(s1_a, s1_b) - max(s0_a, s0_b)
            if ov >= 0.20:
                d = mod53_dist(st_a, st_b)
                if 1 <= d <= 3:
                    errors.append(
                        f"Comma clash at beat {max(b_a, b_b):.2f} ({ov:.2f}s): "
                        f"{tid_a}({st_a}) vs {tid_b}({st_b}) dist={d}"
                    )
                    if len(errors) > 25:
                        break
        if len(errors) > 25:
            break

    musical_dur = max_end_s + 5.0  # stages/concert_hall.json tail_seconds = 5.0
    if not (585.0 <= musical_dur <= 615.0):
        errors.append(f"Duration {musical_dur:.2f}s outside target [585, 615]s!")

    if errors:
        print(f"AUDIT FAILED ({len(errors)} issues):")
        for e in errors[:25]:
            print("  !", e)
        raise SystemExit(1)

    pct = (100.0 * collapse_transitions / max(1, pitched_transitions))
    solo_pct = (100.0 * solo_collapse / max(1, solo_transitions))
    print("AUDIT PASSED (0 voice steals, 0 low mud, 0 comma clashes, 100% stage-independent)!")
    print(
        f"Duration: {musical_dur:.2f}s ({int(musical_dur // 60)}:{musical_dur % 60:05.2f}) | "
        f"Total Beats: {max_beat:.1f} | Total Notes: {total_notes}"
    )
    print(
        f"53-vs-12 Acoustic Signature: {collapse_transitions}/{pitched_transitions} ({pct:.1f}%) overall "
        f"({solo_collapse}/{solo_transitions} = {solo_pct:.1f}% on soloists!) flatten to 0 semitones in 12-TET!"
    )
    print(
        f"Expressive Micro-Articulations: {swell_count} swells, {vib_count} vibrato notes, "
        f"{slide_count} portamento/meend glides, {sum(len(t.get('pedals', [])) for t in score['tracks'])} pedal spans"
    )


def main() -> None:
    sb, score = compose_53vs12()
    audit_score(sb, score)

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = os.path.join(repo_root, "scores", "edo53_vs_12tet_10min.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(score, f, indent=2)
    print(f"Wrote {out_path} ({os.path.getsize(out_path) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
