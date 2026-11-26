#!/usr/bin/env python3
"""
Compose a ~5-minute lush classical 53-EDO symphonic showcase (v2):
  "Harmonia Mundi in 53-EDO — Four Movements Across the Syntonic Comma"

Fuses Mozartian poise & agile counterpoint, Debussy 7-limit (4:5:6:7:9) shimmer
with prominent Indian classical 53-EDO shruti dialogue (Dotara, Ektara, gently
warmed Sitar), Beethovenian kinetic drive & chromatic-mediant drama, and a
thematically unified Cathedral Pipe Organ finale (~final 50 seconds).

Outputs: scores/sample_5min.json
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

# =============================================================================
# 53-EDO Pitch & Tuning Math (C4 = 0, OCT = 53, A4 = 39 = 440 Hz)
# =============================================================================
OCT = 53
P5 = 31          # 3:2  (701.89c)
P4 = 22          # 4:3  (498.11c)
M3 = 17          # 5:4  (384.91c)
m3 = 14          # 6:5  (316.98c)
M6 = 39          # 5:3  (883.02c)
m6 = 36          # 8:5  (815.09c)
M2 = 9           # 9:8  (203.77c)
m2_MINOR = 8     # 10:9 (181.13c)
SEMI = 5         # 16:15 (113.21c)
HARM_7 = 43      # 7:4  (973.58c)
PYTH_m7 = 44     # 16:9
JUST_m7 = 45     # 9:5  (1018.87c)
M7 = 48          # 15:8 (1086.79c)
COMMA = 1        # syntonic comma (~22.64c)
DIESIS = 2       # enharmonic diesis (~45.28c)

# Pitch classes relative to C = 0 (at comma plane k = 0)
C = 0
D_MINUS = 8
D = 9
EB = 14
E = 17
F = 22
FS = 26          # Pure M3 above D(9): 9+17=26 (Tivra Ma!)
G = 31
AB = 36
A = 39
BB_HARM = 43
BB_JUST = 45
B = 48

ALLOWED_INSTRUMENTS = {
    "piano",
    "harp",
    "pizzicato",
    "string_ensemble",
    "viola",
    "cello",
    "clarinet",
    "english_horn",
    "bassoon",
    "french_horn",
    "dotara",
    "ektara",
    "sitar",
    "church_organ",
}

WIND_INSTRUMENTS = {"clarinet", "english_horn", "bassoon", "french_horn"}
STRICT_CHORD_TRACKS = {
    "harp",
    "pizzicato",
    "string_ensemble",
    "bassoon",
    "dotara",
    "ektara",
    "church_organ",
}


def pitch(pc: int, octave: int, k: int = 0) -> int:
    """Exact 53-EDO step for pitch class `pc` in `octave` shifted by comma offset `k`."""
    return pc + (octave - 4) * OCT + k


# Chord interval templates (all pure 5-limit or 7-limit)
CHORD_TEMPLATES: Dict[str, Tuple[int, ...]] = {
    "maj": (0, M3, P5),
    "min": (0, m3, P5),
    "add9": (0, M3, P5, M2),
    "maj7": (0, M3, P5, M7),
    "maj9": (0, M3, P5, M7, M2),
    "min7": (0, m3, P5, JUST_m7),
    "min9": (0, m3, P5, JUST_m7, M2),
    "dom7": (0, M3, P5, HARM_7),
    "dom9": (0, M3, P5, HARM_7, M2),
    "sus2": (0, M2, P5),
}

# Pure diatonic/modal passing & neighbor tones allowed for lyrical melody voices
MELODY_EXTRA: Dict[str, Tuple[int, ...]] = {
    "maj": (M2, P4, M6, M7),
    "min": (M2, P4, m6, JUST_m7),
    "add9": (P4, M6, M7),
    "maj7": (M2, P4, M6),
    "maj9": (P4, M6),
    "min7": (M2, P4, m6),
    "min9": (P4, m6),
    "dom7": (M2, M6),
    "dom9": (M6,),
    "sus2": (M3, P4, M6),
}


@dataclass
class ChordSpan:
    start: float
    end: float
    root_pc: int     # 0..52 (already includes comma shift k)
    quality: str
    label: str = ""
    pedal_pc: Optional[int] = None   # Optional bass pedal pitch-class (e.g. C pedal under F/C)

    @property
    def chord_pcs(self) -> Set[int]:
        s = {(self.root_pc + iv) % OCT for iv in CHORD_TEMPLATES[self.quality]}
        if self.pedal_pc is not None:
            s.add(self.pedal_pc % OCT)
        return s

    @property
    def melody_pcs(self) -> Set[int]:
        return self.chord_pcs | {
            (self.root_pc + iv) % OCT for iv in MELODY_EXTRA[self.quality]
        }

    def nearest_step(self, target_step: int, allow_melody: bool = False) -> int:
        pcs = self.melody_pcs if allow_melody else self.chord_pcs
        best = target_step
        best_dist = 999
        for d in range(-26, 27):
            cand = target_step + d
            if cand % OCT in pcs and abs(d) < best_dist:
                best_dist = abs(d)
                best = cand
        return best

    def bass_root(self, octave: int = 2) -> int:
        """Places bass root (or pedal_pc) cleanly inside warm low bass zone [-108..-54]."""
        pc = self.pedal_pc if self.pedal_pc is not None else self.root_pc
        base = pc + (octave - 4) * OCT
        while base < -108:
            base += OCT
        while base > -54:
            base -= OCT
        return base

    def voicing(self, base_oct: int = 3, include_9: bool = True) -> List[int]:
        """Build an open, lush voicing from root_pc starting near `base_oct`."""
        r = self.root_pc + (base_oct - 4) * OCT
        while r < (base_oct - 4) * OCT - 10:
            r += OCT
        while r > (base_oct - 3) * OCT - 10:
            r -= OCT
        q = self.quality
        if q == "maj":
            return [r, r + P5, r + OCT + M3]
        if q == "min":
            return [r, r + P5, r + OCT + m3]
        if q == "add9":
            return [r, r + P5, r + OCT + M2, r + OCT + M3] if include_9 else [r, r + P5, r + OCT + M3]
        if q == "maj7":
            return [r, r + P5, r + M7, r + OCT + M3]
        if q == "maj9":
            return [r, r + P5, r + M7, r + OCT + M2, r + OCT + M3] if include_9 else [r, r + P5, r + M7, r + OCT + M3]
        if q == "min7":
            return [r, r + P5, r + JUST_m7, r + OCT + m3]
        if q == "min9":
            return [r, r + P5, r + JUST_m7, r + OCT + M2, r + OCT + m3] if include_9 else [r, r + P5, r + JUST_m7, r + OCT + m3]
        if q == "dom7":
            return [r, r + P5, r + HARM_7, r + OCT + M3]
        if q == "dom9":
            return [r, r + P5, r + HARM_7, r + OCT + M2, r + OCT + M3] if include_9 else [r, r + P5, r + HARM_7, r + OCT + M3]
        if q == "sus2":
            return [r, r + P5, r + OCT + M2]
        return [r, r + M3, r + P5]

    def arp_scale(self, low_step: int, high_step: int) -> List[int]:
        pcs = self.chord_pcs
        return [s for s in range(low_step, high_step + 1) if s % OCT in pcs]


# =============================================================================
# TempoMap (exact analytical match to Rust src/score.rs)
# =============================================================================
class TempoMap:
    def __init__(self, segments: List[Tuple[float, float]]):
        self.segments = sorted(segments, key=lambda x: x[0])

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
# Score Builder with Automatic Boundary Trimming & Expressive Shaping
# =============================================================================
@dataclass
class TrackSpec:
    id: str
    name: str
    instrument: str
    notes: List[Dict] = field(default_factory=list)


class SymphonyBuilder:
    def __init__(self, tempo_segments: List[Tuple[float, float]]):
        self.tempo = TempoMap(tempo_segments)
        self.grid: List[ChordSpan] = []
        self.tracks: Dict[str, TrackSpec] = {}
        self._init_tracks()

    def _init_tracks(self) -> None:
        # Pure stage-independent musical tracks (stage seating, gains, LP & hall acoustics live in stages/*.json!)
        specs = [
            TrackSpec("piano", "Concert Grand Piano", "piano"),
            TrackSpec("harp", "Orchestral Harp (53-EDO)", "harp"),
            TrackSpec("pizzicato", "Pizzicato Strings", "pizzicato"),
            TrackSpec("viola", "Solo Viola", "viola"),
            TrackSpec("cello", "Solo Cello", "cello"),
            TrackSpec("string_ensemble", "String Ensemble", "string_ensemble"),
            TrackSpec("clarinet", "Clarinet", "clarinet"),
            TrackSpec("english_horn", "English Horn", "english_horn"),
            TrackSpec("bassoon", "Bassoon", "bassoon"),
            TrackSpec("french_horn", "French Horn", "french_horn"),
            TrackSpec("dotara", "Dotara", "dotara"),
            TrackSpec("ektara", "Ektara", "ektara"),
            TrackSpec("sitar", "Sitar (Warm Veil)", "sitar"),
            TrackSpec("church_organ", "Cathedral Pipe Organ", "church_organ"),
        ]
        for s in specs:
            self.tracks[s.id] = s

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
            start=start,
            end=end,
            root_pc=root_pc % OCT,
            quality=quality,
            label=label,
            pedal_pc=(pedal_pc % OCT) if pedal_pc is not None else None,
        )
        self.grid.append(span)
        return span

    def _safe_dur(self, beat: float, dur: float, step: int, strict: bool) -> float:
        """Trim note cleanly before any chord boundary where `step` would clash."""
        end = beat + dur
        pc = step % OCT
        for sp in self.grid:
            if sp.end <= beat + 1e-6:
                continue
            if sp.start >= end - 1e-6:
                break
            if sp.start > beat + 1e-6:
                allowed = sp.chord_pcs if strict else sp.melody_pcs
                if pc not in allowed:
                    end = min(end, sp.start - 0.05)
                    break
        return max(0.08, end - beat)

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
        breath_swell: Optional[bool] = None,
        meend_cents: float = 0.0,
        trim_to_chord: bool = True,
    ) -> None:
        tr = self.tracks[track_id]
        strict = track_id in STRICT_CHORD_TRACKS
        if trim_to_chord:
            dur = self._safe_dur(beat, dur, step, strict=strict)
        if breath_swell is None:
            breath_swell = tr.instrument in WIND_INSTRUMENTS
        v = max(0.08, min(0.96, float(vel)))
        entry: Dict = {
            "beat": round(beat, 4),
            "dur": round(dur, 4),
            "step": int(step),
            "vel": round(v, 3),
        }
        if abs(cents) > 1e-4:
            entry["cents"] = round(cents, 2)
        if abs(slide_from_cents) > 1e-4:
            entry["slide_from_cents"] = round(slide_from_cents, 2)
        if breath_swell:
            entry["breath_swell"] = True
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
        roll: float = 0.0,
    ) -> None:
        for i, st in enumerate(steps):
            weight = 1.0 if i in (0, len(steps) - 1) else 0.90
            self.note(track_id, beat + i * roll, max(0.12, dur - i * roll), st, vel * weight)

    def arp(
        self,
        track_id: str,
        beat: float,
        note_dur: float,
        spacing: float,
        steps: Sequence[int],
        vel: float,
        arch: float = 0.12,
    ) -> None:
        n = max(1, len(steps))
        for i, st in enumerate(steps):
            u = i / max(1, n - 1)
            shape = 1.0 + arch * math.sin(math.pi * u)
            self.note(track_id, beat + i * spacing, note_dur, st, vel * shape)

    def piano_figure(
        self,
        span: ChordSpan,
        vel: float,
        pattern: str = "alberti",
        oct_low: int = 3,
        step_beats: float = 0.5,
    ) -> None:
        """Expressive Mozartian / Debussy / Beethovenian piano accompaniment figures."""
        r = span.root_pc + (oct_low - 4) * OCT
        while r < -53:   # Keep broken-chord roots >= C3 so zero muddy thirds below C3
            r += OCT
        while r > -1:
            r -= OCT
        third = M3 if span.quality in ("maj", "add9", "maj7", "maj9", "dom7", "dom9") else m3
        if span.quality == "sus2":
            third = M2
        fifth = P5
        ext = None
        if span.quality in ("add9", "maj9", "dom9", "min9"):
            ext = OCT + M2
        elif span.quality == "dom7":
            ext = HARM_7
        elif span.quality == "maj7":
            ext = M7
        elif span.quality == "min7":
            ext = JUST_m7

        if pattern == "alberti":
            seq = [r, r + fifth, r + third, r + fifth]
        elif pattern == "mozart_wave":
            top = r + OCT + third
            seq = [r, r + fifth, r + OCT, r + fifth, r + third, r + fifth, top, r + fifth]
        elif pattern == "debussy_shimmer":
            top = r + ext if ext is not None else r + OCT + third
            seq = [r, r + fifth, r + OCT + third, top, r + OCT + fifth, top, r + OCT + third, r + fifth]
        elif pattern == "beethoven_drive":
            # Urgent pulsating 8th-note Beethovenian accompaniment!
            seq = [r, r + fifth, r + OCT, r + fifth, r + third, r + OCT, r + fifth, r + OCT]
        else:  # wave
            top = r + ext if ext is not None else r + OCT + third
            seq = [r, r + fifth, r + OCT, top, r + OCT, r + fifth, r + third, r + fifth]

        t = span.start
        idx = 0
        while t < span.end - 0.04:
            st = seq[idx % len(seq)]
            b_bar = (t - span.start) % 4.0
            if pattern == "beethoven_drive":
                accent = 1.12 if b_bar < 0.05 else (1.05 if abs(b_bar - 1.5) < 0.05 or abs(b_bar - 2.0) < 0.05 else 0.86)
                ndur = min(step_beats * 0.92, span.end - t - 0.04)
            else:
                accent = 1.07 if b_bar < 0.05 else (0.98 if abs(b_bar - 2.0) < 0.05 else 0.86)
                ndur = min(step_beats * 1.35, span.end - t - 0.05)
            self.note("piano", t, ndur, st, vel * accent)
            t += step_beats
            idx += 1

    def harp_sweep(
        self,
        span: ChordSpan,
        beat: float,
        low_step: int,
        high_step: int,
        vel: float,
        spacing: float = 0.16,
        note_dur: float = 1.8,
        ascending: bool = True,
        max_notes: int = 10,
    ) -> None:
        pts = span.arp_scale(low_step, high_step)
        if not pts:
            return
        if len(pts) > max_notes:
            pts = [pts[int(round(i * (len(pts) - 1) / (max_notes - 1)))] for i in range(max_notes)]
        if not ascending:
            pts = list(reversed(pts))
        self.arp("harp", beat, note_dur, spacing, pts, vel, arch=0.14)

    def string_pad(
        self,
        span: ChordSpan,
        vel: float,
        base_oct: int = 3,
        include_9: bool = True,
        trim_tail: float = 0.16,
    ) -> None:
        voicing = span.voicing(base_oct=base_oct, include_9=include_9)
        dur = max(0.4, (span.end - span.start) - trim_tail)
        self.chord("string_ensemble", span.start, dur, voicing, vel)

    def melody_phrase(
        self,
        track_id: str,
        events: Sequence[Tuple[float, float, int, float]],
        *,
        slide_threshold: float = 0.0,
    ) -> None:
        """Adds an expressive melodic phrase: list of (beat, dur, step, vel)."""
        n = len(events)
        for i, (b, d, st, v) in enumerate(events):
            u = i / max(1, n - 1) if n > 1 else 0.5
            contour = 0.94 + 0.10 * math.sin(math.pi * (u ** 0.85))
            slide = 0.0
            if slide_threshold > 0.0 and i > 0:
                prev_st = events[i - 1][2]
                diff = st - prev_st
                if abs(diff) >= 5:
                    slide = -min(slide_threshold, abs(diff) * 2.4) if diff > 0 else min(slide_threshold * 0.75, abs(diff) * 2.0)
            self.note(track_id, b, d, st, v * contour, slide_from_cents=slide)

    def dotara_tala_bar(
        self,
        span: ChordSpan,
        vel: float,
        low_step: int = pitch(G, 3),
        high_step: int = pitch(E, 5),
        pattern: str = "teental",
    ) -> None:
        """Lively 3+3+2 / 3+2+3 Indian folk-classical plucked counterpoint strictly on chord tones."""
        pts = span.arp_scale(low_step, high_step)
        if len(pts) < 4:
            return
        if pattern == "teental":
            # 3+3+2 rhythmic lilt across 4 beats (8th-note grid: 0.0, 0.5, 1.5, 2.0, 3.0, 3.5)
            offs = [(0.0, 0, 1.05), (0.5, 2, 0.88), (1.5, 3, 1.02), (2.0, 1, 0.90), (2.5, 4, 0.96), (3.0, 2, 1.00), (3.5, 3, 0.90)]
        else:
            # Gentle flowing wave (0.5, 1.0, 2.0, 2.5, 3.5)
            offs = [(0.5, 0, 0.95), (1.0, 2, 1.04), (1.5, 3, 0.90), (2.5, 4, 1.02), (3.0, 2, 0.92), (3.5, 1, 0.86)]
        for off, idx, mult in offs:
            if span.start + off < span.end - 0.15:
                st = pts[min(idx, len(pts) - 1)]
                self.note("dotara", span.start + off, 0.46, st, vel * mult)

    def build_dict(self) -> Dict:
        tracks_json = []
        for tr in self.tracks.values():
            sorted_notes = sorted(tr.notes, key=lambda n: (n["beat"], n["step"]))
            tracks_json.append({
                "id": tr.id,
                "name": tr.name,
                "instrument": tr.instrument,
                "notes": sorted_notes,
            })

        return {
            "title": "Harmonia Mundi in 53-EDO — Four Movements Across the Syntonic Comma",
            "description": (
                "A ~5-minute stage-independent classical 53-EDO symphonic poem fusing Mozartian lyrical "
                "counterpoint, Debussy 7-limit (4:5:6:7:9) impressionism, prominent Indian classical 53-EDO "
                "shruti dialogue (Dotara, Ektara, Sitar), Beethovenian rhythmic drama across a chromatic-mediant "
                "diesis summit and triple downward comma cascade, and a unified Cathedral Pipe Organ finale. "
                "Pair with --stage stages/concert_hall.json (or intimate_circle.json / east_west_split.json)."
            ),
            "sample_rate": 48000,
            "tempo": self.tempo.to_json(),
            "tracks": tracks_json,
        }


# =============================================================================
# Composition of the 4 Connected Movements (~5:05 total)
# =============================================================================
def compose_symphony() -> Tuple[SymphonyBuilder, Dict]:
    tempo_segments = [
        # Movement I: Dawn & Clarity (Beats 0..92, Mozartian poise & grace)
        (0.0, 75.0),
        (32.0, 77.0),
        (64.0, 76.0),
        (86.0, 71.0),
        # Movement II: Lotus & Mist (Beats 92..180, Debussy + Indian shrutis)
        (92.0, 67.0),
        (124.0, 66.0),
        (156.0, 69.0),
        (176.0, 72.0),
        # Movement III: Tempest Across the Comma (Beats 180..280, Beethovenian drive)
        (180.0, 80.0),
        (196.0, 78.0),   # Subito piano breath before explosion
        (204.0, 84.0),   # Surge into Diesis summit!
        (236.0, 82.0),
        (244.0, 80.0),
        (268.0, 73.0),
        # Movement IV: Transfiguration (Beats 280..362, Organ Finisher)
        (280.0, 71.0),
        (304.0, 69.0),
        (328.0, 67.0),
        (344.0, 61.0),
        (356.0, 55.0),
    ]
    sb = SymphonyBuilder(tempo_segments)

    # =========================================================================
    # MOVEMENT I: DAWN & CLARITY (Beats 0..92, 0:00 - 1:13, Tonic k = 0)
    # Genuine Mozartian Antecedent-Consequent melody, flowing 8th-note Alberti,
    # agile Clarinet/Viola/Piano imitative dialogue, translucent chamber clarity!
    # =========================================================================
    k0 = 0
    m1_chords = [
        # I.A (0..32): 8-Bar Mozartian Antecedent (0..16) -> Consequent (16..32)
        (0.0, 4.0, C, "add9", "I.A1 C add9"),
        (4.0, 8.0, G, "maj", "I.A2 G"),
        (8.0, 12.0, A, "min7", "I.A3 Am7"),
        (12.0, 16.0, G, "maj", "I.A4 G half-cadence"),
        (16.0, 20.0, F, "maj9", "I.A5 F maj9"),
        (20.0, 24.0, C, "maj", "I.A6 C"),
        (24.0, 28.0, F, "maj7", "I.A7 F maj7"),
        (28.0, 32.0, G, "dom9", "I.A8 G dom9(7:4)"),
        # I.B (32..64): Agile Chamber Counterpoint (Clarinet, Viola, Piano, Cello, Bassoon — NO string pad!)
        (32.0, 36.0, C, "maj", "I.B1 C"),
        (36.0, 40.0, E, "min7", "I.B2 Em7"),
        (40.0, 44.0, A, "min9", "I.B3 Am9"),
        (44.0, 48.0, F, "maj9", "I.B4 F maj9"),
        (48.0, 52.0, G, "dom7", "I.B5 G dom7(7:4)"),
        (52.0, 56.0, A, "min", "I.B6 Am"),
        (56.0, 60.0, F, "maj9", "I.B7 F maj9"),
        (60.0, 64.0, G, "dom9", "I.B8 G dom9(7:4)"),
        # I.C (64..92): Warm First Orchestral Bloom -> Dissolve to Mist
        (64.0, 68.0, C, "add9", "I.C1 C add9"),
        (68.0, 72.0, G, "maj", "I.C2 G"),
        (72.0, 76.0, A, "min7", "I.C3 Am7"),
        (76.0, 80.0, F, "maj9", "I.C4 F maj9"),
        (80.0, 84.0, G, "dom9", "I.C5 G dom9(7:4)"),
        (84.0, 88.0, C, "add9", "I.C6 C add9 home"),
        (88.0, 92.0, C, "sus2", "I.C7 Mist bridge"),
    ]
    m1_spans = [sb.add_span(*c) for c in m1_chords]

    # --- I.A (0..32): Mozartian Antecedent-Consequent Exposition ---
    for i, sp in enumerate(m1_spans[:8]):
        # Flowing 8th-note Piano Alberti / Mozart wave in LH
        sb.piano_figure(sp, vel=0.52 + 0.02 * (i % 4), pattern="alberti" if i < 4 else "mozart_wave", oct_low=3, step_beats=0.5)
        # Light, buoyant Mozartian Pizzicato walking bass (beats 0, 1.5, 2, 3)
        br = sp.bass_root(2)
        sb.note("pizzicato", sp.start, 0.55, br + OCT, 0.64)
        sb.note("pizzicato", sp.start + 1.5, 0.45, br + P5, 0.48)
        sb.note("pizzicato", sp.start + 2.0, 0.55, br + OCT, 0.56)
        sb.note("pizzicato", sp.start + 3.0, 0.55, br + P5, 0.50)
        # Harp filigree sparkles on key phrase breaths
        if i in (0, 3, 4, 7):
            sb.harp_sweep(sp, sp.start + (2.0 if i == 3 else 0.0), pitch(C, 4), pitch(G, 5), vel=0.62, spacing=0.14, note_dur=1.6, ascending=(i != 3), max_notes=7)

    # Piano RH: Memorable, Rhythmically Agile 8-Bar Mozartian Dawn Theme!
    # (Reprised heroically in Movement IV!)
    sb.melody_phrase("piano", [
        # Antecedent Bar 0 (C add9): Rising 5th Dawn Arc + nimble 8th-note grace turn!
        (0.0, 1.35, pitch(C, 5), 0.74),
        (1.5, 0.45, pitch(D, 5), 0.70),
        (2.0, 0.90, pitch(E, 5), 0.78),
        (3.0, 0.45, pitch(G, 5), 0.80),
        (3.5, 0.45, pitch(E, 5), 0.74),
        # Bar 1 (G): graceful scalar sigh
        (4.0, 1.35, pitch(D, 5), 0.74),
        (5.5, 0.45, pitch(B, 4), 0.70),
        (6.0, 0.90, pitch(G, 4), 0.72),
        (7.0, 0.85, pitch(B, 4), 0.74),
        # Bar 2 (Am7): lyrical arch (pure P4 above A39 is D_MINUS=8!)
        (8.0, 0.90, pitch(C, 5), 0.78),
        (9.0, 0.45, pitch(D_MINUS, 5), 0.76),
        (9.5, 0.45, pitch(E, 5), 0.80),
        (10.0, 0.90, pitch(C, 5), 0.74),
        (11.0, 0.85, pitch(A, 4), 0.70),
        # Bar 3 (G): poised Mozartian half-cadence + breath!
        (12.0, 0.90, pitch(B, 4), 0.72),
        (13.0, 0.45, pitch(C, 5), 0.74),
        (13.5, 0.45, pitch(D, 5), 0.76),
        (14.0, 1.60, pitch(B, 4), 0.70),
        # Consequent Bar 4 (F maj9): climbs warmly higher!
        (16.0, 1.35, pitch(A, 4), 0.74),
        (17.5, 0.45, pitch(C, 5), 0.78),
        (18.0, 0.90, pitch(E, 5), 0.82),
        (19.0, 0.45, pitch(G, 5), 0.84),
        (19.5, 0.45, pitch(E, 5), 0.78),
        # Bar 5 (C): sunlit descent
        (20.0, 0.90, pitch(C, 5), 0.78),
        (21.0, 0.45, pitch(D, 5), 0.76),
        (21.5, 0.45, pitch(E, 5), 0.80),
        (22.0, 0.90, pitch(G, 5), 0.82),
        (23.0, 0.85, pitch(E, 5), 0.76),
        # Bar 6 (F maj7): expressive suspension
        (24.0, 1.35, pitch(F, 5), 0.80),
        (25.5, 0.45, pitch(E, 5), 0.78),
        (26.0, 0.90, pitch(C, 5), 0.76),
        (27.0, 0.85, pitch(A, 4), 0.72),
        # Bar 7 (G dom9 7:4): sparkling 7-limit turn into I.B!
        (28.0, 0.90, pitch(B, 4), 0.76),
        (29.0, 0.45, pitch(A, 4, 1), 0.74),     # Pure 9th A+(40) over G(31)
        (29.5, 0.45, pitch(G, 4), 0.72),
        (30.0, 0.90, pitch(G, 3) + HARM_7, 0.70),
        (31.0, 0.85, pitch(D, 4), 0.68),
    ])

    # Cello warm singing duet replies in the Consequent (16..32)
    sb.melody_phrase("cello", [
        (16.5, 1.3, pitch(F, 3), 0.64),
        (18.0, 1.6, pitch(A, 3), 0.68),
        (20.5, 1.3, pitch(G, 3), 0.66),
        (22.0, 1.6, pitch(E, 3), 0.64),
        (24.5, 1.3, pitch(A, 3), 0.68),
        (26.0, 1.6, pitch(C, 4), 0.72),
        (28.5, 1.4, pitch(D, 4), 0.70),
        (30.2, 1.5, pitch(B, 3), 0.66),
    ])

    # --- I.B (32..64): Agile Mozartian Counterpoint (Clarinet, Viola, Piano, Cello, Bassoon) ---
    for i, sp in enumerate(m1_spans[8:16]):
        br = sp.bass_root(2)
        sb.piano_figure(sp, vel=0.50, pattern="alberti" if i % 2 == 0 else "mozart_wave", oct_low=3, step_beats=0.5)
        # Warm singing Bassoon walking bass (2 notes per bar — musical motion, not static!)
        sb.note("bassoon", sp.start, 1.85, br, 0.64)
        sb.note("bassoon", sp.start + 2.0, 1.80, br + P5, 0.58)
        # Crisp Pizzicato off-beat lift
        sb.note("pizzicato", sp.start + 1.0, 0.45, br + OCT, 0.52)
        sb.note("pizzicato", sp.start + 3.0, 0.45, br + P5, 0.48)
        if i in (1, 3, 5, 7):
            sb.harp_sweep(sp, sp.start + 1.5, pitch(C, 4), pitch(G, 5), vel=0.60, spacing=0.14, note_dur=1.5, ascending=(i in (3, 7)), max_notes=6)

    # Clarinet agile Mozartian melody with dotted rhythms & graceful 8th-note runs!
    sb.melody_phrase("clarinet", [
        # Call 1 (32..40): C -> Em7
        (32.0, 0.90, pitch(E, 4), 0.74),
        (33.0, 0.45, pitch(G, 4), 0.76),
        (33.5, 0.45, pitch(C, 5), 0.80),
        (34.0, 1.35, pitch(G, 4), 0.76),
        (35.5, 0.45, pitch(E, 4), 0.72),
        (36.0, 0.90, pitch(B, 4), 0.78),
        (37.0, 0.45, pitch(A, 4), 0.74),
        (37.5, 0.45, pitch(G, 4), 0.72),
        (38.0, 1.40, pitch(E, 4), 0.70),
        # Breath 39.4..42.0 while Viola answers!
        # Call 2 (42..52): Am9 -> F maj9 -> G dom7(7:4)
        (42.0, 0.90, pitch(E, 5), 0.78),
        (43.0, 0.45, pitch(C, 5), 0.76),
        (43.5, 0.45, pitch(B, 4), 0.74),
        (44.0, 1.35, pitch(A, 4), 0.78),
        (45.5, 0.45, pitch(G, 4), 0.76),
        (46.0, 0.90, pitch(C, 5), 0.80),
        (47.0, 0.85, pitch(E, 5), 0.82),
        (48.0, 1.35, pitch(D, 5), 0.80),
        (49.5, 0.45, pitch(B, 4), 0.76),
        (50.0, 1.60, pitch(G, 4), 0.74),
        # Call 3 (54..64): Am -> F maj9 -> G dom9(7:4)
        (54.0, 0.90, pitch(C, 5), 0.76),
        (55.0, 0.45, pitch(D_MINUS, 5), 0.78),
        (55.5, 0.45, pitch(E, 5), 0.80),
        (56.0, 1.35, pitch(C, 5), 0.82),
        (57.5, 0.45, pitch(A, 4), 0.78),
        (58.0, 0.90, pitch(G, 4), 0.76),
        (59.0, 0.85, pitch(E, 4), 0.74),
        (60.0, 0.90, pitch(B, 4), 0.78),
        (61.0, 0.45, pitch(A, 4, 1), 0.76),
        (61.5, 0.45, pitch(G, 4), 0.74),
        (62.0, 1.70, pitch(D, 5), 0.80),
    ])

    # Viola lively imitative answer in canon with Clarinet!
    sb.melody_phrase("viola", [
        (34.5, 0.45, pitch(C, 4), 0.68),
        (35.0, 0.85, pitch(E, 4), 0.72),
        (36.5, 0.90, pitch(G, 4), 0.72),
        (37.5, 0.45, pitch(E, 4), 0.68),
        # Takes lead at 39.5..43.5 while Clarinet breathes!
        (40.0, 0.90, pitch(A, 4), 0.76),
        (41.0, 0.45, pitch(B, 4), 0.78),
        (41.5, 0.45, pitch(C, 5), 0.80),
        (42.0, 1.40, pitch(A, 4), 0.74),
        # Imitative interplay 45..64
        (45.0, 0.90, pitch(F, 4), 0.70),
        (46.0, 0.90, pitch(A, 4), 0.74),
        (47.0, 0.85, pitch(G, 4), 0.70),
        (49.0, 0.90, pitch(G, 3) + HARM_7, 0.72),
        (50.0, 1.50, pitch(D, 4), 0.70),
        # Leads bars 52..54!
        (52.0, 0.90, pitch(A, 4), 0.76),
        (53.0, 0.45, pitch(G, 4), 0.74),
        (53.5, 0.45, pitch(E, 4), 0.72),
        (54.0, 1.40, pitch(A, 4), 0.74),
        (57.0, 0.90, pitch(A, 4), 0.72),
        (58.0, 1.40, pitch(C, 5), 0.74),
        (60.5, 1.30, pitch(G, 4), 0.72),
        (62.0, 1.60, pitch(B, 4), 0.76),
    ])

    # Cello agile lyrical bass-tenor counterpoint in I.B
    sb.melody_phrase("cello", [
        (32.0, 1.8, pitch(C, 3), 0.66),
        (34.0, 0.9, pitch(E, 3), 0.68),
        (35.0, 0.9, pitch(G, 3), 0.70),
        (36.0, 1.8, pitch(G, 3), 0.68),
        (38.0, 1.8, pitch(B, 3), 0.70),
        (40.0, 1.8, pitch(A, 3), 0.72),
        (42.0, 1.8, pitch(E, 3), 0.68),
        (44.0, 1.8, pitch(F, 3), 0.72),
        (46.0, 1.8, pitch(A, 3), 0.74),
        (48.0, 1.8, pitch(B, 3), 0.72),
        (50.0, 1.8, pitch(G, 3), 0.70),
        (52.0, 1.8, pitch(A, 3), 0.72),
        (54.0, 1.8, pitch(C, 4), 0.74),
        (56.0, 1.8, pitch(A, 3), 0.74),
        (58.0, 1.8, pitch(F, 3), 0.70),
        (60.0, 1.8, pitch(G, 3), 0.74),
        (62.0, 1.8, pitch(D, 4), 0.72),
    ])

    # --- I.C (64..92): Warm First Orchestral Bloom -> Dissolve to Mist ---
    for i, sp in enumerate(m1_spans[16:]):
        is_bridge = i == 6
        br = sp.bass_root(2)
        if not is_bridge:
            dyn = 0.56 if i < 4 else (0.52 if i == 4 else 0.44)
            sb.string_pad(sp, vel=dyn, base_oct=3, include_9=True)
            sb.note("bassoon", sp.start, 3.6, br, dyn + 0.08)
            sb.piano_figure(sp, vel=dyn - 0.02, pattern="mozart_wave", oct_low=3, step_beats=0.5)
            sb.harp_sweep(sp, sp.start, pitch(C, 3), pitch(G, 5), vel=dyn + 0.12, spacing=0.16, note_dur=2.2, ascending=(i % 2 == 0), max_notes=9)
        else:
            # 88..92: Hushed transition into Lotus & Mist
            sb.harp_sweep(sp, sp.start, pitch(C, 3), pitch(G, 5), vel=0.58, spacing=0.22, note_dur=3.2, ascending=True, max_notes=9)
            sb.chord("piano", 88.0, 3.6, [pitch(C, 3), pitch(G, 3), pitch(D, 4), pitch(G, 4)], 0.46, roll=0.14)
            sb.note("viola", 88.5, 3.2, pitch(G, 4), 0.44)

    # Clarinet + Piano soar on the Dawn Theme reprise in I.C (64..88)
    sb.melody_phrase("clarinet", [
        (64.0, 1.35, pitch(C, 5), 0.80),
        (65.5, 0.45, pitch(D, 5), 0.78),
        (66.0, 0.90, pitch(E, 5), 0.82),
        (67.0, 0.85, pitch(G, 5), 0.84),
        (68.0, 1.35, pitch(D, 5), 0.78),
        (69.5, 0.45, pitch(B, 4), 0.74),
        (70.0, 1.60, pitch(G, 4), 0.76),
        (72.0, 0.90, pitch(A, 4), 0.80),
        (73.0, 0.45, pitch(C, 5), 0.82),
        (73.5, 0.45, pitch(E, 5), 0.84),
        (74.0, 1.60, pitch(C, 5), 0.80),
        (76.0, 1.35, pitch(A, 4), 0.80),
        (77.5, 0.45, pitch(C, 5), 0.82),
        (78.0, 1.70, pitch(E, 5), 0.82),
        (80.0, 0.90, pitch(D, 5), 0.78),
        (81.0, 0.45, pitch(B, 4), 0.74),
        (81.5, 0.45, pitch(A, 4, 1), 0.72),
        (82.0, 1.60, pitch(G, 4), 0.70),
        (84.0, 3.40, pitch(E, 4), 0.60),
    ])
    # French Horn warm lyrical counter-melody in I.C
    sb.melody_phrase("french_horn", [
        (64.5, 1.5, pitch(G, 3), 0.66),
        (66.2, 1.6, pitch(C, 4), 0.70),
        (68.0, 1.8, pitch(B, 3), 0.68),
        (70.0, 1.7, pitch(D, 4), 0.72),
        (72.0, 1.8, pitch(C, 4), 0.72),
        (74.0, 1.7, pitch(G, 3), 0.68),
        (76.0, 1.8, pitch(A, 3), 0.74),
        (78.0, 1.7, pitch(C, 4), 0.74),
        (80.0, 1.8, pitch(G, 3), 0.70),
        (82.0, 1.7, pitch(D, 4), 0.66),
        (84.0, 3.5, pitch(G, 3), 0.56),
    ])
    sb.melody_phrase("cello", [
        (64.0, 3.6, pitch(C, 3), 0.68),
        (68.0, 3.6, pitch(G, 3), 0.70),
        (72.0, 3.6, pitch(E, 3), 0.70),
        (76.0, 3.6, pitch(F, 3), 0.72),
        (80.0, 3.6, pitch(D, 3), 0.68),
        (84.0, 3.6, pitch(C, 3), 0.58),
    ])

    # =========================================================================
    # MOVEMENT II: LOTUS & MIST (Beats 92..180, 1:13 - 2:31)
    # Floating Debussy 7-limit pedal points + PROMINENT Indian Shruti Chamber
    # Dialogue (Ektara, Dotara, Warmed Sitar) + Velvety English Horn Lead!
    # Glides smoothly UP +1 comma (k=0 -> k=+1) at Beats 156..180!
    # =========================================================================
    k1 = 1
    m2_chords = [
        # II.A (92..124, k=0): Floating Debussy Pedal Points (C pedal 92..108, G/A shimmer 108..124)
        # NO heavy string pads — pure luminous transparency for English Horn, Harp, Ektara, Dotara, Piano droplets!
        (92.0, 96.0, C, "add9", "II.A1 C add9 pedal", C),
        (96.0, 100.0, C, "dom9", "II.A2 C dom9(7:4) pedal", C),
        (100.0, 104.0, F, "maj9", "II.A3 F maj9 / C pedal!", C),
        (104.0, 108.0, C, "add9", "II.A4 C add9 pedal", C),
        (108.0, 112.0, G, "sus2", "II.A5 G sus2 float", G),
        (112.0, 116.0, G, "dom9", "II.A6 G dom9(7:4) float", G),
        (116.0, 120.0, F, "maj9", "II.A7 F maj9 shimmer", None),
        (120.0, 124.0, C, "add9", "II.A8 C add9 mist", C),
        # II.B (124..156, k=0): Prominent Sitar <-> English Horn Shruti Call-and-Response!
        # Floating Impressionist parallel 9ths & Raga Yaman Tivra Ma (F#26) color!
        (124.0, 128.0, C, "add9", "II.B1 C add9 (Sitar solo)", C),
        (128.0, 132.0, F, "maj9", "II.B2 F maj9 / C pedal (Sitar)", C),
        (132.0, 136.0, G, "dom9", "II.B3 G dom9(7:4) (Eng Horn reply)", None),
        (136.0, 140.0, A, "min9", "II.B4 Am9 shimmer", None),
        (140.0, 144.0, D, "maj", "II.B5 D maj (Tivra Ma F#26, A+40 — Sitar!)", None),
        (144.0, 148.0, G, "dom9", "II.B6 G dom9(7:4) (Sitar -> Eng Horn)", None),
        (148.0, 152.0, F, "maj9", "II.B7 F maj9 (Duet)", None),
        (152.0, 156.0, C, "add9", "II.B8 C add9 shimmer", C),
        # II.C (156..180): UPWARD 5-LIMIT COMMA GLIDE (k = 0 -> k = +1) with liquid Debussy Harp & Dotara!
        (156.0, 160.0, C + k0, "add9", "II.C1 CommaUp I(0)", None),
        (160.0, 164.0, G + k0, "maj", "II.C2 CommaUp V(31)", None),
        (164.0, 168.0, D + k0, "min7", "II.C3 CommaUp ii(9) pivot!", None),
        (168.0, 172.0, F + k1, "maj9", "II.C4 CommaUp IV(23 = F+)", None),
        (172.0, 176.0, G + k1, "dom9", "II.C5 CommaUp V9(32 = G+)", None),
        (176.0, 180.0, C + k1, "add9", "II.C6 CommaUp I(+1 = C+!)", None),
    ]
    m2_spans = [sb.add_span(*c) for c in m2_chords]

    # --- II.A (92..124): Floating Pedal Shimmer + Prominent Ektara/Dotara + Velvety English Horn ---
    for i, sp in enumerate(m2_spans[:8]):
        br = sp.bass_root(2)
        # Prominent, earthy Ektara gourd drone pulse (14c elastic meend bounce!)
        sb.note("ektara", sp.start, 1.6, br + OCT, 0.80, meend_cents=14.0)
        sb.note("ektara", sp.start + 2.0, 1.4, br + OCT + P5, 0.64, meend_cents=10.0)
        if i % 2 == 1:
            sb.note("ektara", sp.start + 3.0, 0.9, br + OCT, 0.62, meend_cents=12.0)

        # Lively Dotara Indian folk-classical tala counterpoint (crystal clear!)
        sb.dotara_tala_bar(sp, vel=0.74 if i % 2 == 0 else 0.68, pattern="teental" if i >= 2 else "wave")

        # Liquid 2-octave Debussy Harp sweeps!
        sb.harp_sweep(sp, sp.start, pitch(C, 3), pitch(C, 6), vel=0.68, spacing=0.14, note_dur=2.4, ascending=(i % 2 == 0), max_notes=11)
        if i in (1, 3, 5, 7):
            sb.harp_sweep(sp, sp.start + 2.0, pitch(G, 3), pitch(G, 5), vel=0.58, spacing=0.16, note_dur=1.8, ascending=False, max_notes=7)

        # Crystalline Debussy Piano water droplets in upper register (C5..C6)
        drop_pts = sp.arp_scale(pitch(C, 5), pitch(C, 6))
        if len(drop_pts) >= 4:
            sb.note("piano", sp.start + 0.5, 1.3, drop_pts[-1], 0.54)
            sb.note("piano", sp.start + 1.5, 1.1, drop_pts[2], 0.48)
            sb.note("piano", sp.start + 2.5, 1.2, drop_pts[3], 0.52)
            sb.note("piano", sp.start + 3.25, 0.9, drop_pts[0], 0.44)

        # Ultra-hushed String Ensemble whisper ONLY on bars 4..7 (keeps bars 0..3 totally transparent!)
        if i >= 4:
            sb.string_pad(sp, vel=0.38, base_oct=3, include_9=True)
            sb.note("bassoon", sp.start, 3.6, br, 0.52)

    # Velvety English Horn Lead (93..123) — expressive, singing, unhurried yet melodically alive!
    sb.melody_phrase("english_horn", [
        # Phrase 1 (93..107): C add9 -> C dom9(7:4) -> F/C -> C add9
        (93.0, 1.40, pitch(G, 4), 0.78),
        (94.5, 0.45, pitch(E, 4), 0.74),
        (95.0, 0.90, pitch(D, 4), 0.72),
        (96.0, 1.35, pitch(G, 4), 0.80),
        (97.5, 0.90, pitch(BB_HARM, 4), 0.84),  # Pure 7:4 Debussy harmonic 7th!
        (98.5, 0.45, pitch(A, 4), 0.80),
        (99.0, 0.90, pitch(G, 4), 0.76),
        (100.0, 1.40, pitch(A, 4), 0.82),
        (101.5, 0.45, pitch(G, 4), 0.78),
        (102.0, 0.90, pitch(E, 4), 0.74),
        (103.0, 0.90, pitch(C, 5), 0.80),
        (104.0, 1.40, pitch(G, 4), 0.76),
        (105.5, 1.80, pitch(E, 4), 0.70),
        # Breath 107.3..108.5
        # Phrase 2 (108.5..123.5): G sus2 -> G dom9(7:4) -> F maj9 -> C add9
        (108.5, 1.35, pitch(D, 4), 0.74),
        (110.0, 0.90, pitch(A, 4, 1), 0.80),    # Pure 9:8 M2 above G(31) = A+(40)!
        (111.0, 0.90, pitch(G, 4), 0.78),
        (112.0, 1.35, pitch(B, 4), 0.82),
        (113.5, 0.45, pitch(A, 4, 1), 0.80),
        (114.0, 0.90, pitch(G, 4), 0.76),
        (115.0, 0.90, pitch(G, 3) + HARM_7, 0.78),
        (116.0, 1.40, pitch(A, 4), 0.82),
        (117.5, 0.45, pitch(G, 4), 0.78),
        (118.0, 1.60, pitch(E, 4), 0.76),
        (120.0, 1.40, pitch(D, 4), 0.72),
        (121.6, 2.00, pitch(C, 4), 0.66),
    ])

    # --- II.B (124..156): PROMINENT Sitar <-> English Horn Indian Shruti Dialogue! ---
    for i, sp in enumerate(m2_spans[8:16]):
        br = sp.bass_root(2)
        # Ektara warm rhythmic drone anchor
        sb.note("ektara", sp.start, 1.7, br + OCT, 0.80, meend_cents=15.0)
        sb.note("ektara", sp.start + 2.5, 1.2, br + OCT, 0.64, meend_cents=10.0)
        # Dotara sparkles on bars 1, 3, 5, 7 (breathing space around Sitar!)
        if i in (0, 2, 4, 6, 7):
            sb.dotara_tala_bar(sp, vel=0.72 if i in (2, 6) else 0.64, pattern="wave" if i in (0, 4) else "teental")
        # Liquid 2-octave Harp ripples
        sb.harp_sweep(sp, sp.start, pitch(C, 3), pitch(C, 6), vel=0.64, spacing=0.15, note_dur=2.2, ascending=(i % 2 == 0), max_notes=10)
        # Debussy Impressionist piano shimmer (sparse, translucent, NEVER blocky!)
        if i in (1, 3, 5, 7):
            sb.piano_figure(sp, vel=0.46, pattern="debussy_shimmer", oct_low=3, step_beats=0.5)
        # Soft Strings ONLY on English Horn response bars (keeps Sitar crystal clear!)
        if i in (2, 3, 6, 7):
            sb.string_pad(sp, vel=0.40, base_oct=3, include_9=True)

    # Warmed Lower-Mid Register Sitar Soloist (LP 2700 Hz, lyrical raga meend glides <= 38c!)
    sb.melody_phrase("sitar", [
        # Sitar Solo Call 1 (124..132): C add9 -> F maj9/C (singing raga Yaman-style ascent!)
        (124.2, 1.20, pitch(C, 4), 0.80),
        (125.5, 0.60, pitch(D, 4), 0.82),
        (126.2, 0.85, pitch(E, 4), 0.86),
        (127.2, 0.70, pitch(G, 4), 0.84),
        (128.0, 1.25, pitch(A, 4), 0.88),
        (129.4, 0.60, pitch(G, 4), 0.84),
        (130.1, 0.85, pitch(E, 4), 0.82),
        (131.0, 0.90, pitch(C, 4), 0.78),
        # Sitar Solo Call 2 (140..148): D maj (Tivra Ma F#26 & A+40!) -> G dom9(7:4)
        (140.2, 1.20, pitch(D, 4), 0.82),
        (141.5, 0.65, pitch(FS, 4), 0.88),       # Pure Tivra Ma (45:32 / F#26)!
        (142.3, 0.85, pitch(A, 4, 1), 0.90),     # Pure 5th above D(9) = A+(40)!
        (143.2, 0.70, pitch(FS, 4), 0.84),
        (144.0, 1.20, pitch(G, 4), 0.86),
        (145.3, 0.65, pitch(G, 3) + HARM_7, 0.84),
        (146.1, 0.85, pitch(D, 4), 0.82),
        (147.0, 0.90, pitch(B, 3), 0.76),
        # Brief warm Sitar closing flourish (152..156)
        (152.5, 1.10, pitch(E, 4), 0.80),
        (153.8, 0.80, pitch(G, 4), 0.82),
        (154.7, 1.10, pitch(C, 4), 0.76),
    ], slide_threshold=36.0)

    # English Horn answers Sitar tenderly (132..140 & 148..154)
    sb.melody_phrase("english_horn", [
        (132.0, 1.20, pitch(G, 4), 0.80),
        (133.3, 0.60, pitch(A, 4, 1), 0.84),
        (134.0, 0.90, pitch(B, 4), 0.86),
        (135.0, 0.90, pitch(G, 4), 0.80),
        (136.0, 1.35, pitch(C, 5), 0.84),
        (137.5, 0.45, pitch(B, 4), 0.80),
        (138.0, 1.70, pitch(A, 4), 0.76),
        # Response 2 (148..153.5)
        (148.0, 1.35, pitch(A, 4), 0.84),
        (149.5, 0.45, pitch(G, 4), 0.80),
        (150.0, 0.90, pitch(E, 4), 0.78),
        (151.0, 0.90, pitch(C, 5), 0.82),
        (152.0, 1.40, pitch(G, 4), 0.74),
    ])

    # Cello warm melodic pedal thread beneath II.B
    sb.melody_phrase("cello", [
        (124.0, 3.6, pitch(C, 3), 0.62),
        (128.0, 3.6, pitch(C, 3), 0.64),
        (132.0, 3.6, pitch(G, 3), 0.66),
        (136.0, 3.6, pitch(A, 3), 0.68),
        (140.0, 3.6, pitch(D, 3), 0.70),
        (144.0, 3.6, pitch(G, 3), 0.70),
        (148.0, 3.6, pitch(F, 3), 0.68),
        (152.0, 3.6, pitch(C, 3), 0.64),
    ])

    # --- II.C (156..180): UPWARD 5-LIMIT COMMA GLIDE (k = 0 -> k = +1) ---
    for i, sp in enumerate(m2_spans[16:]):
        br = sp.bass_root(2)
        dyn = 0.54 + 0.035 * i
        sb.string_pad(sp, vel=dyn * 0.82, base_oct=3, include_9=True)
        sb.note("bassoon", sp.start, 3.6, br, dyn + 0.06)
        sb.piano_figure(sp, vel=dyn * 0.88, pattern="debussy_shimmer", oct_low=3, step_beats=0.5)
        # Lush 2-octave liquid Harp sweeps guiding the upward comma lift!
        sb.harp_sweep(sp, sp.start, pitch(C, 3), pitch(C, 6), vel=dyn + 0.14, spacing=0.14, note_dur=2.4, ascending=True, max_notes=11)
        # Dotara & Ektara shimmer carrying the Indian color right across the comma boundary!
        sb.dotara_tala_bar(sp, vel=0.66 + 0.02 * i, pattern="wave")
        if i in (0, 3, 5):
            sb.note("ektara", sp.start, 1.5, br + OCT, 0.72, meend_cents=12.0)

    # English Horn + Viola sing a flowing ascending line across the +1 comma glide!
    sb.melody_phrase("english_horn", [
        (156.0, 1.8, pitch(E, 4, k0), 0.76),
        (158.0, 1.8, pitch(G, 4, k0), 0.80),
        (160.0, 1.8, pitch(B, 4, k0), 0.82),
        (162.0, 1.8, pitch(D, 4, k0), 0.78),          # Common tone D(9)!
        (164.0, 1.35, pitch(D, 4, k0), 0.80),         # Pivot Dm7(9: D, F+23, A+40)
        (165.5, 0.45, pitch(E, 4, k1), 0.80),
        (166.0, 1.8, pitch(F, 4, k1), 0.84),          # Common tone F+(23)!
        (168.0, 1.35, pitch(A, 4, k1), 0.86),
        (169.5, 0.45, pitch(G, 4, k1), 0.84),
        (170.0, 1.8, pitch(C, 5, k1), 0.88),
        (172.0, 1.35, pitch(B, 4, k1), 0.88),
        (173.5, 0.45, pitch(A, 4, k1 + 1), 0.84),     # Pure 9th A++(41) over G+(32)
        (174.0, 1.8, pitch(G, 4, k1), 0.82),
        (176.0, 3.5, pitch(E, 4, k1), 0.80),          # Luminous arrival on C+(+1)!
    ])
    sb.melody_phrase("french_horn", [
        (164.0, 3.6, pitch(A, 3, k1), 0.66),
        (168.0, 3.6, pitch(C, 4, k1), 0.72),
        (172.0, 3.6, pitch(D, 4, k1), 0.76),
        (176.0, 3.6, pitch(G, 3, k1), 0.78),
    ])

    # =========================================================================
    # MOVEMENT III: TEMPEST ACROSS THE COMMA (Beats 180..280, 2:31 - 3:44)
    # REAL BEETHOVENIAN KINETIC DRIVE:
    #   III.A (180..212): Urgent 8th-note ostinato, dotted heroic French Horn,
    #                     subito piano breath (196..200) -> roaring crescendo!
    #   III.B (212..244): Chromatic-Mediant Diesis Summit (C+1 -> Ab+37 -> E+20 -> C+++3)
    #                     with surging rhythmic waves & blazing fanfare!
    #   III.C (244..280): Triple Downward Comma Cascade (+3 -> +2 -> +1 -> 0) —
    #                     THREE COMPLETELY DISTINCT ORCHESTRATIONS & TEXTURES!
    # =========================================================================
    m3_chords = [
        # III.A (180..212, k=+1)
        (180.0, 184.0, C + k1, "min", "III.A1 Cm+ drive"),
        (184.0, 188.0, AB + k1, "maj", "III.A2 Ab+"),
        (188.0, 192.0, F + k1, "min7", "III.A3 Fm7+"),
        (192.0, 196.0, G + k1, "dom7", "III.A4 G7+"),
        (196.0, 200.0, C + k1, "min", "III.A5 Subito piano Cm+"),
        (200.0, 204.0, EB + k1, "maj9", "III.A6 Crescendo Eb maj9+"),
        (204.0, 208.0, F + k1, "maj", "III.A7 Surge F maj+"),
        (208.0, 212.0, G + k1, "dom9", "III.A8 Climax Prep G dom9+"),
        # III.B (212..244): Chromatic-Mediant Diesis Summit (+1 -> +3, common tone every step!)
        (212.0, 220.0, 1, "maj", "III.B1 Diesis C+(k=+1)"),
        (220.0, 228.0, 37, "maj", "III.B2 Diesis Ab+(shares C+1)"),
        (228.0, 236.0, 20, "maj", "III.B3 Diesis E+(shares Ab+37)"),
        (236.0, 244.0, 3, "add9", "III.B4 Diesis Summit C+++(k=+3, shares E+20)!"),
        # III.C (244..280): Triple Downward Comma Cascade (+3 -> +2 -> +1 -> 0)
        # Cascade 1 (+3 -> +2): Heroic Full-Orchestra Surge
        (244.0, 246.0, 3, "maj", "III.C1 I(+3)"),
        (246.0, 248.0, 25, "maj", "III.C1 IV(+25)"),
        (248.0, 250.0, 11, "min", "III.C1 ii(+11)"),
        (250.0, 252.0, 33, "dom7", "III.C1 V7(+33)"),
        (252.0, 256.0, 2, "add9", "III.C1 I(+2)"),
        # Cascade 2 (+2 -> +1): Agile Woodwind & Viola Imitative Counterpoint
        (256.0, 258.0, 2, "maj", "III.C2 I(+2)"),
        (258.0, 260.0, 24, "maj", "III.C2 IV(+24)"),
        (260.0, 262.0, 10, "min", "III.C2 ii(+10)"),
        (262.0, 264.0, 32, "dom7", "III.C2 V7(+32)"),
        (264.0, 268.0, 1, "add9", "III.C2 I(+1)"),
        # Cascade 3 (+1 -> 0): Melting Chamber Homecoming (English Horn, Piano, Harp, Dotara!)
        (268.0, 270.0, 1, "maj", "III.C3 I(+1)"),
        (270.0, 272.0, 23, "maj", "III.C3 IV(+23)"),
        (272.0, 274.0, 9, "min", "III.C3 ii(+9)"),
        (274.0, 276.0, 31, "dom9", "III.C3 V9(+31)"),
        (276.0, 280.0, 0, "add9", "III.C3 HOME I(0)!"),
    ]
    m3_spans = [sb.add_span(*c) for c in m3_chords]

    # --- III.A (180..212): Beethovenian Kinetic Motor + Subito Piano Contrast ---
    for i, sp in enumerate(m3_spans[:8]):
        br = sp.bass_root(2)
        is_subito_p = (i == 4)  # Beats 196..200 dramatic hushed tension drop!
        dyn = 0.44 if is_subito_p else (0.68 + 0.03 * i)

        # Urgent Beethovenian 8th-note Piano drive + dramatic bass punches
        sb.piano_figure(sp, vel=dyn * 0.88, pattern="beethoven_drive", oct_low=3, step_beats=0.5)
        if not is_subito_p:
            sb.note("piano", sp.start, 0.85, br, dyn * 0.94)
            sb.note("piano", sp.start + 1.5, 0.45, br, dyn * 0.84)   # Syncopated sfz!
            sb.note("piano", sp.start + 2.0, 0.85, br, dyn * 0.90)

        # Urgent 8th-note Cello + Viola kinetic ostinato (short-short-short-LONG!)
        third = M3 if sp.quality in ("maj", "add9", "maj9", "dom7", "dom9") else m3
        for k_step, off in enumerate([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]):
            st_c = br + OCT if k_step % 2 == 0 else br + OCT + P5
            acc = 1.08 if k_step in (0, 3, 4) else 0.80
            sb.note("cello", sp.start + off, 0.36, st_c, dyn * 0.90 * acc)
            # Viola driving inner 8th-note pulse an octave higher
            st_v = br + 2 * OCT + (third if k_step % 2 == 1 else 0)
            sb.note("viola", sp.start + off, 0.34, st_v, dyn * 0.72 * acc)

        # Bassoon & Pizzicato rhythmic punctuation
        sb.note("bassoon", sp.start, 1.4, br, dyn * 0.94)
        if not is_subito_p:
            sb.note("bassoon", sp.start + 2.0, 1.6, br + P5, dyn * 0.88)
            sb.note("pizzicato", sp.start, 0.45, br + OCT, dyn * 0.84)
            sb.note("pizzicato", sp.start + 1.5, 0.45, br + OCT, dyn * 0.78)
            sb.note("pizzicato", sp.start + 2.0, 0.45, br + P5, dyn * 0.80)
            sb.string_pad(sp, vel=dyn * 0.78, base_oct=3, include_9=False)

    # Bold Heroic Beethovenian French Horn Fanfare (dotted rhythms & soaring intervals!)
    sb.melody_phrase("french_horn", [
        # Statement 1 (180..196): short-short-short-LONG heroic call!
        (180.0, 0.40, pitch(G, 3, k1), 0.80),
        (180.5, 0.40, pitch(G, 3, k1), 0.82),
        (181.0, 0.40, pitch(G, 3, k1), 0.86),
        (181.5, 2.10, pitch(EB, 4, k1), 0.90),
        (184.0, 1.35, pitch(C, 4, k1), 0.86),
        (185.5, 0.45, pitch(EB, 4, k1), 0.88),
        (186.0, 1.70, pitch(AB, 4, k1), 0.92),
        (188.0, 1.35, pitch(F, 4, k1), 0.86),
        (189.5, 0.45, pitch(EB, 4, k1), 0.82),
        (190.0, 1.70, pitch(C, 4, k1), 0.80),
        (192.0, 1.35, pitch(D, 4, k1), 0.88),
        (193.5, 0.45, pitch(B, 3, k1), 0.84),
        (194.0, 1.70, pitch(G, 3, k1), 0.82),
        # Subito piano whisper at 196..200, then roaring crescendo 200..212!
        (200.0, 0.90, pitch(EB, 4, k1), 0.76),
        (201.0, 0.45, pitch(F, 4, k1 + 1), 0.80),   # Pure 9th F++(24) over Eb+(15)
        (201.5, 0.45, pitch(G, 4, k1), 0.84),
        (202.0, 1.70, pitch(BB_JUST, 4, k1), 0.88),
        (204.0, 1.35, pitch(A, 4, k1), 0.90),
        (205.5, 0.45, pitch(F, 4, k1), 0.86),
        (206.0, 1.70, pitch(C, 5, k1), 0.92),
        (208.0, 1.35, pitch(B, 4, k1), 0.92),
        (209.5, 0.45, pitch(A, 4, k1 + 1), 0.90),   # Pure 9th A++(41) over G+(32)
        (210.0, 1.80, pitch(G, 4, k1), 0.94),
    ])

    # Fierce Clarinet agile 8th-note Beethovenian sweeps answering the Horn!
    sb.melody_phrase("clarinet", [
        (182.0, 0.45, pitch(C, 5, k1), 0.78),
        (182.5, 0.45, pitch(D, 5, k1), 0.80),
        (183.0, 0.90, pitch(EB, 5, k1), 0.84),
        (185.0, 0.45, pitch(C, 5, k1), 0.80),
        (185.5, 0.45, pitch(EB, 5, k1), 0.84),
        (186.0, 1.60, pitch(AB, 4, k1), 0.82),
        (189.0, 0.45, pitch(AB, 4, k1), 0.82),
        (189.5, 0.45, pitch(C, 5, k1), 0.86),
        (190.0, 1.60, pitch(F, 5, k1), 0.88),
        (193.0, 0.45, pitch(D, 5, k1), 0.84),
        (193.5, 0.45, pitch(B, 4, k1), 0.82),
        (194.0, 1.60, pitch(G, 4, k1), 0.80),
        # Hushed eerie whisper on subito piano bar (196..200)!
        (196.5, 0.90, pitch(EB, 4, k1), 0.52),
        (197.5, 0.45, pitch(F, 4, k1), 0.54),
        (198.0, 1.60, pitch(G, 4, k1), 0.58),
        # Roaring surge 201..212
        (201.5, 0.45, pitch(G, 4, k1), 0.80),
        (202.0, 0.45, pitch(BB_JUST, 4, k1), 0.84),
        (202.5, 1.20, pitch(EB, 5, k1), 0.88),
        (205.0, 0.45, pitch(A, 4, k1), 0.86),
        (205.5, 0.45, pitch(C, 5, k1), 0.90),
        (206.0, 1.60, pitch(F, 5, k1), 0.92),
        (209.0, 0.45, pitch(D, 5, k1), 0.90),
        (209.5, 0.45, pitch(B, 4, k1), 0.88),
        (210.0, 1.80, pitch(D, 5, k1), 0.92),
    ])

    # --- III.B (212..244): Chromatic-Mediant Diesis Summit (+1 -> +3) — Surging Rhythmic Waves! ---
    diesis_pillars = m3_spans[8:12]
    diesis_melodies = [
        # Pillar 0: C+(1) — heroic dotted fanfare climbing to C+5!
        [(212.0, 1.35, pitch(C, 5, 1), 0.86), (213.5, 0.45, pitch(E, 5, 1), 0.88), (214.0, 1.70, pitch(G, 5, 1), 0.92),
         (216.0, 0.90, pitch(E, 5, 1), 0.86), (217.0, 0.90, pitch(D, 5, 1), 0.84), (218.0, 1.80, pitch(C, 5, 1), 0.90)],
        # Pillar 1: Ab+(37) — pivots on exact C+(1), blazes to Eb+(15) and Ab+(37)!
        [(220.0, 1.35, pitch(C, 5, 1), 0.90), (221.5, 0.45, pitch(EB, 5, 1), 0.92), (222.0, 1.70, pitch(AB, 4, 1), 0.88),
         (224.0, 0.90, pitch(C, 5, 1), 0.90), (225.0, 0.90, pitch(EB, 5, 1), 0.92), (226.0, 1.80, pitch(AB, 4, 1), 0.90)],
        # Pillar 2: E+(20) — pivots on exact Ab+/G#+(37), surges to B+(51) and E+(20)!
        [(228.0, 1.35, pitch(AB, 4, 1), 0.90), (229.5, 0.45, pitch(B, 4, 3), 0.92), (230.0, 1.70, pitch(E, 5, 3), 0.94),
         (232.0, 0.90, pitch(B, 4, 3), 0.90), (233.0, 0.90, pitch(AB, 4, 1), 0.88), (234.0, 1.80, pitch(E, 5, 3), 0.94)],
        # Pillar 3: C+++(3) Summit — pivots on exact E+++(20), crowns G+++(34) & C+++(3)!
        [(236.0, 1.35, pitch(E, 5, 3), 0.94), (237.5, 0.45, pitch(G, 5, 3), 0.95), (238.0, 1.70, pitch(C, 5, 3), 0.92),
         (240.0, 0.90, pitch(D, 5, 3), 0.92), (241.0, 0.90, pitch(E, 5, 3), 0.94), (242.0, 1.80, pitch(G, 5, 3), 0.95)],
    ]
    for idx, sp in enumerate(diesis_pillars):
        br = sp.bass_root(2)
        dyn = 0.78 + 0.04 * idx
        sb.string_pad(sp, vel=dyn * 0.84, base_oct=3, include_9=(idx == 3))
        # Driving Beethovenian Piano 8th-note waves across all 8 beats!
        sb.piano_figure(sp, vel=dyn * 0.86, pattern="beethoven_drive", oct_low=3, step_beats=0.5)
        # Dramatic 2-octave Harp glissandi every 4 beats!
        sb.harp_sweep(sp, sp.start, pitch(C, 3), pitch(C, 6), vel=dyn * 0.92, spacing=0.12, note_dur=2.4, ascending=True, max_notes=11)
        sb.harp_sweep(sp, sp.start + 4.0, pitch(C, 3), pitch(C, 6), vel=dyn * 0.88, spacing=0.13, note_dur=2.4, ascending=False, max_notes=10)
        # Driving Cello rhythmic quarters + Bassoon heroic pedal
        for q in range(8):
            sb.note("cello", sp.start + q, 0.78, br + OCT + (P5 if q % 2 == 1 else 0), dyn * (0.94 if q % 2 == 0 else 0.82))
        sb.note("bassoon", sp.start, 3.8, br, dyn * 0.94)
        sb.note("bassoon", sp.start + 4.0, 3.8, br, dyn * 0.96)
        # Heroic French Horn dotted fanfare on root & fifth!
        hr = sp.root_pc
        if hr > 35:
            hr -= OCT
        sb.melody_phrase("french_horn", [
            (sp.start, 1.35, hr, dyn * 0.94),
            (sp.start + 1.5, 0.45, hr + P5, dyn * 0.96),
            (sp.start + 2.0, 1.80, hr + P5, dyn * 0.94),
            (sp.start + 4.0, 1.35, hr + OCT, dyn * 0.96),
            (sp.start + 5.5, 0.45, hr + P5, dyn * 0.94),
            (sp.start + 6.0, 1.80, hr + P5, dyn * 0.96),
        ])
        sb.melody_phrase("clarinet", diesis_melodies[idx])
        sb.melody_phrase("viola", [(b, d, st - OCT, v * 0.82) for b, d, st, v in diesis_melodies[idx]])

    # --- III.C (244..280): Triple Silky Downward Comma Cascade (+3 -> +2 -> +1 -> 0) ---
    # THREE COMPLETELY DISTINCT ORCHESTRATIONS & RHYTHMIC WAVES (no repetitive slabs!)
    cascade_spans = m3_spans[12:]  # 15 spans = 3 cascades of 5 spans
    for idx, sp in enumerate(cascade_spans):
        c_num = idx // 5     # 0=Heroic Wave (+3->+2), 1=Agile Woodwind Canon (+2->+1), 2=Tender Chamber Homecoming (+1->0)
        step_i = idx % 5     # 0=I, 1=IV, 2=ii, 3=V7, 4=I_next (4 beats)
        br = sp.bass_root(2)
        dur = sp.end - sp.start
        k_cur = 3 - c_num
        k_next = k_cur - 1

        if c_num == 0:
            # CASCADE 1 (+3 -> +2): Heroic Full-Orchestra Wave with driving 8ths & bold Horn!
            dyn = 0.80
            sb.string_pad(sp, vel=0.68, base_oct=3, include_9=(step_i == 4))
            sb.piano_figure(sp, vel=0.72, pattern="beethoven_drive", oct_low=3, step_beats=0.5)
            sb.note("bassoon", sp.start, dur - 0.10, br, 0.78)
            for off in [o * 0.5 for o in range(int(dur * 2))]:
                sb.note("cello", sp.start + off, 0.38, br + OCT + (P5 if int(off * 2) % 2 == 1 else 0), 0.74)
            if step_i in (0, 2, 4):
                sb.harp_sweep(sp, sp.start, pitch(C, 3), pitch(C, 6), vel=0.80, spacing=0.13, note_dur=min(dur, 2.0), ascending=(step_i != 2), max_notes=9)
            # Heroic French Horn + Clarinet descending fanfare
            targets_c1 = [
                [(sp.start, 0.90, pitch(G, 4, 3), 0.88), (sp.start + 1.0, 0.90, pitch(E, 4, 3), 0.84)],
                [(sp.start, 0.90, pitch(A, 4, 3), 0.88), (sp.start + 1.0, 0.90, pitch(F, 4, 3), 0.84)],
                [(sp.start, 0.90, pitch(F, 4, 3), 0.86), (sp.start + 1.0, 0.90, pitch(D, 4, 2), 0.82)],
                [(sp.start, 0.90, pitch(B, 4, 2), 0.88), (sp.start + 1.0, 0.90, pitch(G, 4, 2), 0.84)],
                [(sp.start, 1.35, pitch(E, 5, 2), 0.88), (sp.start + 1.5, 0.45, pitch(D, 5, 2), 0.84), (sp.start + 2.0, 1.80, pitch(C, 5, 2), 0.86)],
            ]
            sb.melody_phrase("clarinet", targets_c1[step_i])
            if step_i == 0:
                sb.note("french_horn", sp.start, dur - 0.14, pitch(C, 4, 3), 0.82)
            elif step_i == 3:
                sb.note("french_horn", sp.start, dur - 0.14, pitch(G, 3, 2), 0.82)
            elif step_i == 4:
                sb.note("french_horn", sp.start, dur - 0.14, pitch(C, 4, 2), 0.84)

        elif c_num == 1:
            # CASCADE 2 (+2 -> +1): Agile Transparent Woodwind & Viola Counterpoint (NO string pad on steps 0..3!)
            sb.piano_figure(sp, vel=0.56, pattern="mozart_wave", oct_low=3, step_beats=0.5)
            sb.note("pizzicato", sp.start, 0.55, br + OCT, 0.66)
            if dur >= 3.5:
                sb.note("pizzicato", sp.start + 2.0, 0.55, br + P5, 0.60)
            sb.note("bassoon", sp.start, dur - 0.12, br, 0.64)
            sb.harp_sweep(sp, sp.start, pitch(C, 4), pitch(G, 5), vel=0.66, spacing=0.14, note_dur=1.5, ascending=(step_i % 2 == 0), max_notes=7)
            if step_i == 4:
                sb.string_pad(sp, vel=0.52, base_oct=3, include_9=True)
            # Flowing 8th-note Clarinet + Viola imitative duet!
            cl_c2 = [
                [(sp.start, 0.90, pitch(E, 4, 2), 0.76), (sp.start + 1.0, 0.45, pitch(G, 4, 2), 0.78), (sp.start + 1.5, 0.45, pitch(C, 5, 2), 0.80)],
                [(sp.start, 0.90, pitch(A, 4, 2), 0.80), (sp.start + 1.0, 0.90, pitch(C, 5, 2), 0.82)],
                [(sp.start, 0.90, pitch(F, 4, 2), 0.78), (sp.start + 1.0, 0.90, pitch(A, 4, 2), 0.80)],
                [(sp.start, 0.90, pitch(B, 4, 1), 0.80), (sp.start + 1.0, 0.90, pitch(G, 4, 1), 0.76)],
                [(sp.start, 1.35, pitch(G, 4, 1), 0.78), (sp.start + 1.5, 0.45, pitch(E, 4, 1), 0.74), (sp.start + 2.0, 1.80, pitch(C, 5, 1), 0.76)],
            ]
            sb.melody_phrase("clarinet", cl_c2[step_i])
            # Viola answers 0.5 beat later in pure chord harmony!
            v_st = sp.nearest_step(cl_c2[step_i][0][2] - M3, allow_melody=False)
            sb.note("viola", sp.start + 0.5, dur - 0.6, v_st, 0.68)

        else:
            # CASCADE 3 (+1 -> 0): Tender Melting Homecoming — English Horn, Harp, Piano & Dotara glow!
            sb.string_pad(sp, vel=0.46 if step_i < 4 else 0.50, base_oct=3, include_9=(step_i >= 3))
            sb.note("cello", sp.start, dur - 0.14, br + OCT, 0.64)
            sb.piano_figure(sp, vel=0.50, pattern="debussy_shimmer", oct_low=3, step_beats=0.5)
            sb.harp_sweep(sp, sp.start, pitch(C, 3), pitch(C, 6), vel=0.66, spacing=0.16, note_dur=2.2, ascending=(step_i != 2), max_notes=9)
            if step_i == 4:
                # Warm Dotara & Ektara welcome home at exact k = 0!
                sb.note("ektara", sp.start, 1.6, pitch(C, 3), 0.66, meend_cents=10.0)
                sb.dotara_tala_bar(sp, vel=0.62, pattern="wave")
                sb.note("french_horn", sp.start, 3.6, pitch(G, 3), 0.68)
            eh_c3 = [
                [(sp.start, 1.80, pitch(E, 4, 1), 0.76)],
                [(sp.start, 1.80, pitch(A, 4, 1), 0.78)],
                [(sp.start, 1.80, pitch(F, 4, 1), 0.76)],
                [(sp.start, 0.90, pitch(B, 4, 0), 0.78), (sp.start + 1.0, 0.90, pitch(A, 4, 1), 0.74)],
                [(sp.start, 1.40, pitch(G, 4, 0), 0.76), (sp.start + 1.6, 2.20, pitch(E, 4, 0), 0.70)],
            ]
            sb.melody_phrase("english_horn", eh_c3[step_i])

    # =========================================================================
    # MOVEMENT IV: TRANSFIGURATION (Beats 280..362, 3:44 - 5:04)
    #   IV.A (280..304): Luminous East-West Synthesis (Organ SILENT!)
    #   IV.B (304..336): CATHEDRAL PIPE ORGAN ENTRANCE (~4:05) + FULL THEMATIC
    #                    RECAPITULATION of Movement I's Dawn Theme soaring above!
    #   IV.C (336..362): Transfigured Amen Coda + Piano/Harp/Ektara Whisper Fade
    # =========================================================================
    m4_chords = [
        # IV.A (280..304, k=0): Luminous East-West Synthesis (Organ SILENT!)
        (280.0, 284.0, C, "add9", "IV.A1 C add9 synthesis"),
        (284.0, 288.0, F, "maj9", "IV.A2 F maj9"),
        (288.0, 292.0, A, "min9", "IV.A3 Am9"),
        (292.0, 296.0, G, "dom9", "IV.A4 G dom9(7:4)"),
        (296.0, 300.0, F, "maj9", "IV.A5 F maj9 anticipation"),
        (300.0, 304.0, G, "sus2", "IV.A6 G sus2 hush before Organ"),
        # IV.B (304..336, k=0): CATHEDRAL PIPE ORGAN ENTERS AT BEAT 304 (~4:05) + MVT I THEME REPRISE!
        (304.0, 308.0, C, "add9", "IV.B1 Organ Entry pp: C add9 (Dawn Theme!)"),
        (308.0, 312.0, G, "maj", "IV.B2 Organ mp: G"),
        (312.0, 316.0, A, "min7", "IV.B3 Organ mf: Am7"),
        (316.0, 320.0, E, "min", "IV.B4 Organ mf+: Em"),
        (320.0, 324.0, F, "maj9", "IV.B5 Organ f: F maj9"),
        (324.0, 328.0, C, "maj", "IV.B6 Organ f: C"),
        (328.0, 332.0, G, "dom9", "IV.B7 Climax: G dom9(7:4)"),
        (332.0, 336.0, C, "add9", "IV.B8 Cathedral Apotheosis: C add9"),
        # IV.C (336..362, k=0): Transfigured Amen Coda & East-West Whisper Fade
        (336.0, 342.0, F, "maj9", "IV.C1 Amen IV (F maj9)"),
        (342.0, 348.0, C, "add9", "IV.C2 Amen I (C add9)"),
        (348.0, 354.0, F, "maj", "IV.C3 Final Plagal F"),
        (354.0, 362.0, C, "maj", "IV.C4 Final Pure 5-Limit C Home"),
    ]
    m4_spans = [sb.add_span(*c) for c in m4_chords]

    # --- IV.A (280..304): Flowing East-West Synthesis (Organ SILENT!) ---
    for i, sp in enumerate(m4_spans[:6]):
        br = sp.bass_root(2)
        sb.piano_figure(sp, vel=0.52, pattern="mozart_wave" if i < 3 else "debussy_shimmer", oct_low=3, step_beats=0.5)
        sb.harp_sweep(sp, sp.start, pitch(C, 3), pitch(C, 6), vel=0.64, spacing=0.16, note_dur=2.4, ascending=(i % 2 == 0), max_notes=10)
        if i >= 2:
            sb.string_pad(sp, vel=0.44 + 0.03 * (i - 2), base_oct=3, include_9=True)
        sb.note("bassoon", sp.start, 3.6, br, 0.58)
        # Warm nostalgic Indian chamber reprise on bars 0..2!
        if i in (0, 1, 2):
            sb.note("ektara", sp.start, 1.5, br + OCT, 0.70, meend_cents=12.0)
            sb.dotara_tala_bar(sp, vel=0.66, pattern="wave")

    # Nostalgic Sitar whisper (280..288) answering English Horn + Clarinet duet!
    sb.melody_phrase("sitar", [
        (281.0, 1.2, pitch(G, 4), 0.74),
        (282.4, 1.4, pitch(E, 4), 0.72),
        (284.5, 1.3, pitch(A, 4), 0.76),
        (286.0, 1.6, pitch(C, 4), 0.70),
    ], slide_threshold=32.0)

    sb.melody_phrase("english_horn", [
        (280.0, 1.35, pitch(E, 4), 0.74),
        (281.5, 0.45, pitch(G, 4), 0.76),
        (282.0, 1.60, pitch(C, 5), 0.78),
        (284.0, 1.35, pitch(A, 4), 0.78),
        (285.5, 0.45, pitch(G, 4), 0.76),
        (286.0, 1.60, pitch(E, 4), 0.74),
        (288.0, 1.35, pitch(E, 4), 0.74),
        (289.5, 0.45, pitch(G, 4), 0.78),
        (290.0, 1.60, pitch(C, 5), 0.80),
        (292.0, 1.35, pitch(B, 4), 0.80),
        (293.5, 0.45, pitch(A, 4, 1), 0.78),
        (294.0, 1.70, pitch(G, 4), 0.76),
        (296.0, 1.80, pitch(A, 4), 0.78),
        (298.0, 1.70, pitch(C, 5), 0.80),
        (300.0, 3.60, pitch(D, 5), 0.74),
    ])
    sb.melody_phrase("clarinet", [
        (288.5, 1.4, pitch(A, 4), 0.70),
        (290.2, 1.6, pitch(E, 5), 0.74),
        (292.5, 1.5, pitch(D, 5), 0.74),
        (294.2, 1.6, pitch(G, 3) + HARM_7, 0.70),
        (296.5, 1.5, pitch(E, 5), 0.76),
        (298.2, 1.6, pitch(G, 5), 0.78),
        (300.5, 3.0, pitch(G, 4), 0.68),
    ])
    sb.melody_phrase("cello", [
        (280.0, 3.6, pitch(C, 3), 0.64),
        (284.0, 3.6, pitch(F, 3), 0.66),
        (288.0, 3.6, pitch(A, 3), 0.68),
        (292.0, 3.6, pitch(G, 3), 0.68),
        (296.0, 3.6, pitch(F, 3), 0.70),
        (300.0, 3.6, pitch(G, 3), 0.70),
    ])

    # --- IV.B (304..336): CATHEDRAL PIPE ORGAN ENTRANCE (~4:05) + SOARING MVT I DAWN RECAPITULATION! ---
    organ_curve = [0.36, 0.46, 0.56, 0.66, 0.74, 0.80, 0.85, 0.88]
    for i, sp in enumerate(m4_spans[6:14]):
        br = sp.bass_root(2)
        org_v = organ_curve[i]
        orch_v = 0.60 + 0.04 * i

        # Cathedral Pipe Organ: wide, beat-free 5-limit open voicings (zero low-register thirds!)
        org_notes = [br, br + OCT]
        if i >= 1:
            org_notes.append(br + OCT + P5)
        if i >= 2:
            third_iv = M3 if sp.quality in ("maj", "add9", "maj7", "maj9", "dom7", "dom9") else m3
            org_notes.append(br + 2 * OCT + third_iv)
        if i >= 4:
            org_notes.append(br + 2 * OCT)
        sb.chord("church_organ", sp.start, 3.88, org_notes, org_v)

        # Shimmering Piano 8th-note waves & 2-octave Harp glissandi beneath the soaring melody!
        sb.piano_figure(sp, vel=orch_v * 0.78, pattern="mozart_wave" if i < 4 else "debussy_shimmer", oct_low=3, step_beats=0.5)
        sb.harp_sweep(sp, sp.start, pitch(C, 3), pitch(C, 6), vel=orch_v * 0.88, spacing=0.14, note_dur=2.6, ascending=(i % 2 == 0), max_notes=11)
        sb.string_pad(sp, vel=orch_v * 0.84, base_oct=3, include_9=True)
        sb.note("bassoon", sp.start, 3.7, br, orch_v * 0.86)
        sb.note("cello", sp.start, 1.85, br + OCT, orch_v * 0.90)
        sb.note("cello", sp.start + 2.0, 1.80, br + OCT + P5, orch_v * 0.88)

    # THEMATIC APOTHEOSIS: Movement I's singing Dawn Theme returns gloriously on Clarinet + English Horn + Viola!
    dawn_recap = [
        # Bar 0 (304..308, C add9): Rising Dawn Arc + Mozart turn!
        (304.0, 1.35, pitch(C, 5), 0.80),
        (305.5, 0.45, pitch(D, 5), 0.78),
        (306.0, 0.90, pitch(E, 5), 0.84),
        (307.0, 0.45, pitch(G, 5), 0.86),
        (307.5, 0.45, pitch(E, 5), 0.82),
        # Bar 1 (308..312, G)
        (308.0, 1.35, pitch(D, 5), 0.82),
        (309.5, 0.45, pitch(B, 4), 0.78),
        (310.0, 0.90, pitch(G, 4), 0.80),
        (311.0, 0.85, pitch(B, 4), 0.82),
        # Bar 2 (312..316, Am7: pure P4 above A39 is D_MINUS=8!)
        (312.0, 0.90, pitch(C, 5), 0.84),
        (313.0, 0.45, pitch(D_MINUS, 5), 0.84),
        (313.5, 0.45, pitch(E, 5), 0.88),
        (314.0, 0.90, pitch(C, 5), 0.84),
        (315.0, 0.85, pitch(A, 4), 0.80),
        # Bar 3 (316..320, Em)
        (316.0, 1.35, pitch(B, 4), 0.84),
        (317.5, 0.45, pitch(G, 4), 0.82),
        (318.0, 1.80, pitch(E, 5), 0.88),
        # Bar 4 (320..324, F maj9): Soaring climax ascent!
        (320.0, 1.35, pitch(A, 4), 0.86),
        (321.5, 0.45, pitch(C, 5), 0.88),
        (322.0, 0.90, pitch(E, 5), 0.90),
        (323.0, 0.45, pitch(G, 5), 0.92),
        (323.5, 0.45, pitch(E, 5), 0.88),
        # Bar 5 (324..328, C)
        (324.0, 0.90, pitch(C, 5), 0.88),
        (325.0, 0.45, pitch(D, 5), 0.88),
        (325.5, 0.45, pitch(E, 5), 0.90),
        (326.0, 0.90, pitch(G, 5), 0.92),
        (327.0, 0.85, pitch(E, 5), 0.88),
        # Bar 6 (328..332, G dom9 7:4)
        (328.0, 1.35, pitch(D, 5), 0.92),
        (329.5, 0.45, pitch(B, 4), 0.88),
        (330.0, 0.90, pitch(A, 4, 1), 0.90),    # Pure 9th A+(40) over G(31)
        (331.0, 0.85, pitch(B, 4), 0.90),
        # Bar 7 (332..336, C add9 Apotheosis!)
        (332.0, 3.80, pitch(C, 5), 0.94),
    ]
    sb.melody_phrase("clarinet", dawn_recap)
    # English Horn doubles the radiant melody warmly in the middle octave from 312..336!
    sb.melody_phrase("english_horn", [(b, d, st - OCT if st >= pitch(E, 5) else st, v * 0.92) for b, d, st, v in dawn_recap if b >= 312.0])
    # Viola weaves rich lyrical harmony a 3rd/6th below!
    viola_recap = []
    for b, d, st, v in dawn_recap:
        sp_at = next(sp for sp in m4_spans[6:14] if sp.start - 1e-6 <= b < sp.end - 1e-6)
        viola_recap.append((b, d, sp_at.nearest_step(st - M3 - (OCT if st >= pitch(E, 5) else 0), allow_melody=False), v * 0.78))
    sb.melody_phrase("viola", viola_recap)

    # French Horn sings a noble Beethovenian counter-anthem beneath the Dawn Recapitulation!
    sb.melody_phrase("french_horn", [
        (304.0, 1.8, pitch(G, 3), 0.72),
        (306.0, 1.8, pitch(C, 4), 0.76),
        (308.0, 1.8, pitch(B, 3), 0.76),
        (310.0, 1.8, pitch(D, 4), 0.80),
        (312.0, 1.8, pitch(E, 4), 0.82),
        (314.0, 1.8, pitch(C, 4), 0.80),
        (316.0, 1.8, pitch(G, 4), 0.84),
        (318.0, 1.8, pitch(B, 3), 0.82),
        (320.0, 1.8, pitch(A, 4), 0.88),
        (322.0, 1.8, pitch(G, 4), 0.86),
        (324.0, 1.8, pitch(E, 4), 0.88),
        (326.0, 1.8, pitch(G, 4), 0.90),
        (328.0, 1.8, pitch(B, 4), 0.92),
        (330.0, 1.8, pitch(G, 4), 0.90),
        (332.0, 3.8, pitch(G, 4), 0.94),
    ])

    # --- IV.C (336..362): Transfigured Amen Coda + Piano/Harp/Ektara East-West Whisper Fade ---
    coda_spans = m4_spans[14:]  # F maj9 (6b), C add9 (6b), F maj (6b), C maj (8b)
    coda_org_vels = [0.72, 0.58, 0.44, 0.34]
    coda_orch_vels = [0.68, 0.56, 0.44, 0.36]

    for i, sp in enumerate(coda_spans):
        br = sp.bass_root(2)
        dur = sp.end - sp.start
        ov = coda_org_vels[i]
        sv = coda_orch_vels[i]
        org_chord = [br, br + OCT, br + OCT + P5, br + 2 * OCT + M3]
        if i == 3:
            sb.chord("church_organ", sp.start, dur - 0.6, [pitch(C, 2), pitch(C, 3), pitch(G, 3), pitch(E, 4), pitch(C, 5)], ov)
        else:
            sb.chord("church_organ", sp.start, dur - 0.14, org_chord, ov)

        sb.string_pad(sp, vel=sv, base_oct=3, include_9=(i < 2), trim_tail=0.25)
        sb.note("bassoon", sp.start, dur - 0.3, br, sv * 0.88)
        sb.note("cello", sp.start, dur - 0.3, br + OCT, sv * 0.86)
        sb.harp_sweep(
            sp,
            sp.start + 0.25,
            pitch(C, 3),
            pitch(C, 6),
            vel=sv + 0.12,
            spacing=0.26 if i < 3 else 0.36,
            note_dur=3.8,
            ascending=True,
            max_notes=9,
        )

    # Final French Horn Amen sigh
    sb.melody_phrase("french_horn", [
        (336.0, 5.4, pitch(A, 3), 0.66),
        (342.0, 5.4, pitch(G, 3), 0.58),
        (348.0, 5.4, pitch(A, 3), 0.48),
        (354.0, 6.6, pitch(G, 3), 0.38),
    ])

    # Warm, subtle Ektara + Dotara East-West farewell echo in the dissolving Coda!
    sb.note("ektara", 342.0, 2.2, pitch(C, 3), 0.56, meend_cents=10.0)
    sb.note("ektara", 354.0, 2.8, pitch(C, 3), 0.48, meend_cents=8.0)
    sb.note("dotara", 344.0, 1.0, pitch(G, 4), 0.50)
    sb.note("dotara", 345.0, 1.0, pitch(E, 4), 0.46)
    sb.note("dotara", 355.5, 1.2, pitch(G, 4), 0.42)

    # Piano tender high reminiscence of the Dawn Theme dissolving into cathedral silence!
    sb.melody_phrase("piano", [
        (337.5, 1.4, pitch(C, 5), 0.60),
        (339.0, 0.9, pitch(E, 5), 0.62),
        (340.0, 1.8, pitch(A, 4), 0.56),
        (342.5, 1.5, pitch(G, 4), 0.56),
        (344.2, 1.4, pitch(D, 5), 0.54),
        (345.8, 1.8, pitch(E, 5), 0.52),
        (348.5, 2.2, pitch(F, 5), 0.48),
        (351.0, 2.4, pitch(C, 5), 0.44),
        # Final crystalline Dawn Arc whisper over pure 5-limit C major cathedral chord
        (354.2, 1.3, pitch(C, 5), 0.50),
        (355.6, 0.7, pitch(D, 5), 0.46),
        (356.4, 1.3, pitch(E, 5), 0.46),
        (357.8, 1.4, pitch(G, 5), 0.44),
        (359.4, 2.4, pitch(C, 5), 0.36),
    ])
    sb.chord("piano", 336.0, 5.4, [pitch(F, 3), pitch(C, 4), pitch(E, 4), pitch(A, 4)], 0.50, roll=0.14)
    sb.chord("piano", 342.0, 5.4, [pitch(C, 3), pitch(G, 3), pitch(D, 4), pitch(E, 4)], 0.46, roll=0.14)
    sb.chord("piano", 348.0, 5.4, [pitch(F, 3), pitch(C, 4), pitch(F, 4), pitch(A, 4)], 0.42, roll=0.16)
    sb.chord("piano", 354.0, 7.2, [pitch(C, 3), pitch(G, 3), pitch(C, 4), pitch(E, 4)], 0.38, roll=0.18)

    score = sb.build_dict()
    return sb, score


# =============================================================================
# Built-in Harmonic Consonance, Register, Polyphony & Timing Validator
# =============================================================================
def validate_score(sb: SymphonyBuilder, score: Dict) -> None:
    errors: List[str] = []
    organ_first_beat: Optional[float] = None
    max_beat = 0.0

    for tr in score["tracks"]:
        inst = tr["instrument"]
        tid = tr["id"]
        if inst not in ALLOWED_INSTRUMENTS:
            errors.append(f"Forbidden instrument '{inst}' in track '{tid}'")

        notes = tr["notes"]
        events = []
        for n in notes:
            b0 = n["beat"]
            b1 = b0 + n["dur"]
            max_beat = max(max_beat, b1)
            events.append((b0, 1))
            events.append((b1, -1))
            if inst == "church_organ":
                if organ_first_beat is None or b0 < organ_first_beat:
                    organ_first_beat = b0
                if b0 < 296.0:
                    errors.append(f"church_organ entered too early at beat {b0:.2f}")
            if inst in WIND_INSTRUMENTS and not n.get("breath_swell", False):
                errors.append(f"Wind track '{tid}' note at beat {b0:.2f} missing breath_swell=True")

            strict = tid in STRICT_CHORD_TRACKS
            pc = n["step"] % OCT
            for sp in sb.grid:
                if sp.end <= b0 + 0.02 or sp.start >= b1 - 0.02:
                    continue
                allowed = sp.chord_pcs if strict else sp.melody_pcs
                if pc not in allowed:
                    errors.append(
                        f"Harmony clash: track={tid} beat={b0:.2f}..{b1:.2f} step={n['step']} (pc={pc}) "
                        f"not in {sp.label} (root={sp.root_pc}, {sp.quality}, allowed={sorted(allowed)})"
                    )

        events.sort(key=lambda x: (x[0], x[1]))
        cur = 0
        peak_poly = 0
        for _, delta in events:
            cur += delta
            peak_poly = max(peak_poly, cur)
        if peak_poly > 14:
            errors.append(f"Track '{tid}' exceeds safe 15-channel polyphony: peak={peak_poly}")

    # Check no close thirds/seconds below C3 (-53) simultaneously across ALL tracks
    low_notes: List[Tuple[float, float, int, str]] = []
    for tr in score["tracks"]:
        for n in tr["notes"]:
            if n["step"] < -53:
                low_notes.append((n["beat"], n["beat"] + n["dur"], n["step"], tr["id"]))
    low_notes.sort()
    for i in range(len(low_notes)):
        b0, e0, s0, t0 = low_notes[i]
        for j in range(i + 1, len(low_notes)):
            b1, e1, s1, t1 = low_notes[j]
            if b1 >= e0 - 0.05:
                break
            diff = abs(s1 - s0)
            if 0 < diff < P4:
                errors.append(
                    f"Low-register mud (<C3): {t0}({s0}) & {t1}({s1}) overlap at beat {b1:.2f} (diff={diff} steps)"
                )

    tail_s = score.get("tail_seconds", 5.0)
    total_sec = sb.tempo.beat_to_seconds(max_beat) + tail_s
    if not (295.0 <= total_sec <= 315.0):
        errors.append(f"Total duration {total_sec:.2f}s outside target [295.0, 315.0]s")

    organ_sec = sb.tempo.beat_to_seconds(organ_first_beat) if organ_first_beat is not None else None
    if organ_sec is None:
        errors.append("church_organ has no notes!")
    else:
        remaining = total_sec - organ_sec
        if not (40.0 <= remaining <= 65.0):
            errors.append(f"church_organ enters at {organ_sec:.1f}s ({remaining:.1f}s remaining; want ~50s)")

    if errors:
        print(f"VALIDATION FAILED with {len(errors)} error(s):")
        for e in errors[:30]:
            print("  -", e)
        raise SystemExit(1)

    print("VALIDATION PASSED (0 harmony clashes, 0 low-register mud, 0 polyphony overflows)!")
    print(f"Total Beats: {max_beat:.1f} | Total Duration: {total_sec:.2f}s ({int(total_sec // 60)}:{total_sec % 60:05.2f})")
    print("Movement Timestamps:")
    for name, b in [
        ("I.   Dawn & Clarity (k=0)", 0.0),
        ("II.  Lotus & Mist (k=0 -> +1)", 92.0),
        ("     -> Sitar & English Horn Shruti Dialogue", 124.0),
        ("     -> Upward Comma Glide (0 -> +1)", 156.0),
        ("III. Tempest Across the Comma (k=+1 -> +3 -> 0)", 180.0),
        ("     -> Chromatic-Mediant Diesis (+1 -> +3)", 212.0),
        ("     -> Triple Downward Comma Cascade (+3 -> 0)", 244.0),
        ("IV.  Transfiguration (Home k=0)", 280.0),
        ("     -> Cathedral Pipe Organ + Dawn Reprise", organ_first_beat or 304.0),
        ("     -> Transfigured Amen Coda", 336.0),
    ]:
        t = sb.tempo.beat_to_seconds(b)
        print(f"  {name:<50} beat {b:5.1f}  @ {int(t // 60)}:{t % 60:05.2f}")
    print("Track Note Counts:")
    for tr in score["tracks"]:
        print(f"  {tr['id']:<16} ({tr['instrument']:<15}): {len(tr['notes']):4d} notes")


def main() -> None:
    sb, score = compose_symphony()
    validate_score(sb, score)

    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scores", "sample_5min.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(score, f, indent=2)
    print(f"Wrote {out_path} ({os.path.getsize(out_path) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
