#!/usr/bin/env python3
"""
Compose an original ~4-minute pure Western Orchestral Classical work in 53-EDO:
  "Symphonia Prisma in 53-EDO — Adagio, Scherzo, Diesis Tempest & Passacaglia"

Anchored in F Major (F4 = step 22, A4 = step 39 = 440.00 Hz exact!) so that on a
53-EDO vs 12-TET A/B switch at 0:00, concert A4 (440 Hz) stays motionless while
the entire orchestra snaps from 12-TET beating thirds into glass-still 4:5:6 and
4:5:6:7:9 pure resonance.

Features:
  - 11 pure Western Warm-Core orchestral tracks (stage-independent JSON for stages/*.json)
  - Mvt I   (Beats   0..72): Adagio Sostenuto — Cradle of Pure Thirds & Septimal Ninths
                             + Upward 5-Limit Syntonic Comma Lift (k = 0 -> +1)
  - Mvt II  (Beats  72..148): Allegretto Grazioso — Classical Scherzo & 4-Voice Fugato (k = +1)
  - Mvt III (Beats 148..224): Allegro Appassionato — Chromatic-Mediant Diesis Ascent (k = +1 -> +3)
                             & Triple Downward Comma Cascade (+3 -> +2 -> +1 -> 0)
  - Mvt IV  (Beats 224..296): Maestoso Passacaglia & Cathedral Pipe Organ Apotheosis (Home k = 0)

Outputs: scores/orchestral_53edo.json
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

# =============================================================================
# 53-EDO Pitch & Interval Constants (C4 = 0, A4 = 39 = 440.0 Hz, OCT = 53)
# =============================================================================
OCT = 53
P5 = 31          # 3:2   (701.89c, -0.07c error)
P4 = 22          # 4:3   (498.11c, +0.07c error)
M3 = 17          # 5:4   (384.91c, -1.41c error)
m3 = 14          # 6:5   (316.98c, +1.34c error)
M6 = 39          # 5:3   (883.02c, -1.34c error)
m6 = 36          # 8:5   (815.09c, +1.41c error)
M2 = 9           # 9:8   (203.77c, -0.14c error)
m2_MINOR = 8     # 10:9  (181.13c, -1.27c error)
SEMI = 5         # 16:15 (113.21c)
HARM_7 = 43      # 7:4   (973.58c, septimal harmonic 7th)
PYTH_m7 = 44     # 16:9  (996.23c)
JUST_m7 = 45     # 9:5   (1018.87c)
M7 = 48          # 15:8  (1086.79c)
COMMA = 1        # 81:80 (~22.64c syntonic comma)
DIESIS = 2       # 128:125 (~45.28c enharmonic diesis)

# Reference pitch classes at comma plane k = 0
C = 0
DB = 5           # Pure M3 below F(22): 22 - 17 = 5
D_MINUS = 8      # Pure M3 above Bb(44): (44 + 17) % 53 = 8
D = 9            # Major whole tone above C(0); pure m3 below F(22) is D_MINUS(8)? Wait: 9 + 13=22, 8 + 14 = 22!
EB_HARM = 12     # Septimal 7:4 above F(22): (22 + 43) % 53 = 12
EB = 14          # Pure 6:5 above C(0)
E = 17           # Pure 5:4 above C(0); pure M7 above F(22): (22 + 48) % 53 = 17
F = 22           # Home Tonic F (pure 4:3 above C, pure 5:4 below A4=39!)
G_MINUS = 30     # Minor whole tone above F(22): 22 + 8 = 30 (ii in downward comma pump!)
G = 31           # Major whole tone above F(22): 22 + 9 = 31 (pure 3:2 above C!)
AB = 36          # Pure m3 above F(22): 22 + 14 = 36
A = 39           # Concert A4 = 440.00 Hz! Pure 5:4 major third above F(22): 22 + 17 = 39!
BB_HARM = 43     # Septimal 7:4 above C(0): 0 + 43 = 43!
BB = 44          # Pure P4 above F(22): 22 + 22 = 44!
B = 48           # Pure M7 above C(0)

WIND_INSTRUMENTS = {"clarinet", "english_horn", "bassoon", "french_horn"}
STRICT_CHORD_TRACKS = {
    "harp",
    "pizzicato",
    "string_ensemble",
    "bassoon",
    "church_organ",
}


def pitch(pc: int, octave: int, k: int = 0) -> int:
    """Exact 53-EDO step for pitch class `pc` (0..52) in `octave` (C4 = 0) + comma offset `k`."""
    return pc + (octave - 4) * OCT + k


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
    "sus4": (0, P4, P5),
    "sus2": (0, M2, P5),
}

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
    "sus4": (M2, M3, M6),
    "sus2": (M3, P4, M6),
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

    def bass_root(self, low: int = -106, high: int = -56) -> int:
        """Places bass root (or pedal_pc) cleanly inside the warm low bass register [C2..B2]."""
        pc = self.pedal_pc if self.pedal_pc is not None else self.root_pc
        st = pc - 2 * OCT
        while st < low:
            st += OCT
        while st > high:
            st -= OCT
        return st

    def tenor_root(self) -> int:
        """Places root cleanly in [C3..B3] (-53..-1) so thirds/7ths above it sit >= C3."""
        r = (self.root_pc % OCT) - OCT
        while r < -53:
            r += OCT
        while r > -1:
            r -= OCT
        return r

    def open_voicing(self, include_9: bool = True) -> List[int]:
        """Warm, wide orchestral string/brass chord voicing with zero close low intervals."""
        r = self.tenor_root()
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
        if q == "sus4":
            return [r, r + P5, r + OCT + P4]
        if q == "sus2":
            return [r, r + P5, r + OCT + M2]
        return [r, r + P5, r + OCT + M3]

    def arp_scale(self, low_step: int, high_step: int) -> List[int]:
        pcs = self.chord_pcs
        return [s for s in range(low_step, high_step + 1) if s % OCT in pcs]


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


@dataclass
class TrackSpec:
    id: str
    name: str
    instrument: str
    notes: List[Dict] = field(default_factory=list)


class OrchestraBuilder:
    def __init__(self, tempo_segments: List[Tuple[float, float]]):
        self.tempo = TempoMap(tempo_segments)
        self.grid: List[ChordSpan] = []
        self.tracks: Dict[str, TrackSpec] = {}
        self._init_tracks()

    def _init_tracks(self) -> None:
        specs = [
            TrackSpec("piano", "Concert Grand Piano", "piano"),
            TrackSpec("harp", "Orchestral Harp", "harp"),
            TrackSpec("pizzicato", "Pizzicato Strings", "pizzicato"),
            TrackSpec("viola", "Solo Viola", "viola"),
            TrackSpec("cello", "Solo Cello", "cello"),
            TrackSpec("string_ensemble", "String Orchestra", "string_ensemble"),
            TrackSpec("clarinet", "Solo Clarinet", "clarinet"),
            TrackSpec("english_horn", "English Horn", "english_horn"),
            TrackSpec("bassoon", "Solo Bassoon", "bassoon"),
            TrackSpec("french_horn", "French Horn", "french_horn"),
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

    def span_at(self, beat: float) -> ChordSpan:
        for sp in self.grid:
            if sp.start - 1e-6 <= beat < sp.end - 1e-6:
                return sp
        return self.grid[-1]

    def _safe_dur(self, beat: float, dur: float, step: int, strict: bool) -> float:
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
                    end = min(end, sp.start - 0.06)
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
        trim_to_chord: bool = True,
        snap_to_harmony: bool = False,
    ) -> None:
        tr = self.tracks[track_id]
        strict = track_id in STRICT_CHORD_TRACKS
        if snap_to_harmony:
            sp = self.span_at(beat)
            step = sp.nearest_step(step, allow_melody=not strict)
        if trim_to_chord:
            dur = self._safe_dur(beat, dur, step, strict=strict)
        if breath_swell is None:
            breath_swell = tr.instrument in WIND_INSTRUMENTS
        v = max(0.08, min(0.95, float(vel)))
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

    def string_swell(
        self,
        span: ChordSpan,
        vel: float,
        include_9: bool = True,
        trim_tail: float = 0.14,
    ) -> None:
        voicing = span.open_voicing(include_9=include_9)
        dur = max(0.35, (span.end - span.start) - trim_tail)
        self.chord("string_ensemble", span.start, dur, voicing, vel)

    def harp_gliss(
        self,
        span: ChordSpan,
        beat: float,
        low_step: int,
        high_step: int,
        vel: float,
        spacing: float = 0.16,
        note_dur: float = 1.9,
        ascending: bool = True,
        max_notes: int = 9,
    ) -> None:
        pts = span.arp_scale(low_step, high_step)
        if not pts:
            return
        if len(pts) > max_notes:
            pts = [pts[int(round(i * (len(pts) - 1) / (max_notes - 1)))] for i in range(max_notes)]
        if not ascending:
            pts = list(reversed(pts))
        n = max(1, len(pts))
        for i, st in enumerate(pts):
            u = i / max(1, n - 1)
            shape = 1.0 + 0.13 * math.sin(math.pi * u)
            if beat + i * spacing < span.end - 0.10:
                self.note("harp", beat + i * spacing, note_dur, st, vel * shape)

    def piano_accompaniment(
        self,
        span: ChordSpan,
        vel: float,
        style: str = "nocturne",
        step_beats: float = 0.5,
    ) -> None:
        r = span.tenor_root()
        q = span.quality
        third = M3 if q in ("maj", "add9", "maj7", "maj9", "dom7", "dom9") else m3
        if q == "sus4":
            third = P4
        elif q == "sus2":
            third = M2
        ext = r + OCT + third
        if q in ("add9", "maj9", "dom9", "min9"):
            ext = r + OCT + M2
        elif q == "dom7":
            ext = r + HARM_7
        elif q == "maj7":
            ext = r + M7
        elif q == "min7":
            ext = r + JUST_m7

        if style == "nocturne":
            seq = [r, r + P5, r + OCT + third, ext, r + OCT + P5, ext, r + OCT + third, r + P5]
        elif style == "scherzo":
            seq = [r, r + P5, r + third, r + P5, r + OCT, r + P5, r + third, r + P5]
        elif style == "storm":
            seq = [r, r + P5, r + OCT, r + P5, r + OCT + third, r + OCT, r + P5, r + OCT]
        else:  # passacaglia
            seq = [r, r + P5, r + OCT, r + OCT + third, ext, r + OCT + P5, ext, r + OCT]

        t = span.start
        idx = 0
        while t < span.end - 0.06:
            st = seq[idx % len(seq)]
            b_in = (t - span.start) % 4.0
            if style == "storm":
                acc = 1.12 if b_in < 0.05 else (1.04 if abs(b_in - 2.0) < 0.05 else 0.85)
                ndur = min(step_beats * 0.90, span.end - t - 0.05)
            elif style == "scherzo":
                acc = 1.08 if b_in < 0.05 else (0.96 if abs(b_in - 2.0) < 0.05 else 0.80)
                ndur = min(step_beats * 0.82, span.end - t - 0.05)
            else:
                acc = 1.06 if b_in < 0.05 else (0.96 if abs(b_in - 2.0) < 0.05 else 0.86)
                ndur = min(step_beats * 1.38, span.end - t - 0.06)
            self.note("piano", t, ndur, st, vel * acc)
            t += step_beats
            idx += 1

    def phrase(
        self,
        track_id: str,
        events: Sequence[Tuple[float, float, int, float]],
        *,
        expressive_slide: float = 0.0,
        snap_to_harmony: bool = False,
    ) -> None:
        n = len(events)
        for i, (b, d, st, v) in enumerate(events):
            u = i / max(1, n - 1) if n > 1 else 0.5
            arch = 0.94 + 0.10 * math.sin(math.pi * (u ** 0.85))
            slide = 0.0
            if expressive_slide > 0.0 and i > 0:
                prev_b, prev_d, prev_st, _ = events[i - 1]
                diff = st - prev_st
                # Gentle classical portamento only on connected lyrical leaps
                if 8 <= abs(diff) <= 22 and (b - (prev_b + prev_d)) < 0.25 and d >= 0.85:
                    slide = -expressive_slide if diff > 0 else expressive_slide * 0.8
            self.note(
                track_id,
                b,
                d,
                st,
                v * arch,
                slide_from_cents=slide,
                snap_to_harmony=snap_to_harmony,
            )

    def build_dict(self) -> Dict:
        tracks_json = []
        for tr in self.tracks.values():
            strict = tr.id in STRICT_CHORD_TRACKS
            for n in tr.notes:
                n["dur"] = round(
                    self._safe_dur(n["beat"], n["dur"], n["step"], strict=strict), 4
                )
            sorted_notes = sorted(tr.notes, key=lambda n: (n["beat"], n["step"]))
            tracks_json.append({
                "id": tr.id,
                "name": tr.name,
                "instrument": tr.instrument,
                "notes": sorted_notes,
            })

        return {
            "title": "Symphonia Prisma in 53-EDO — Adagio, Scherzo, Diesis & Passacaglia",
            "description": (
                "An original ~4-minute stage-independent Western orchestral classical work in F Major "
                "(anchored around exact concert A4 = step 39 = 440.00 Hz). Showcases glass-pure 5-limit "
                "triads (4:5:6) and septimal harmonic ninths (4:5:6:7:9) from Bar 1, an upward syntonic "
                "comma lift (+1), a 4-voice woodwind/string fugato scherzo, a Beethovenian chromatic-mediant "
                "diesis summit (+1 -> +3) with triple downward comma cascade (+3 -> 0), and a Brahmsian "
                "passacaglia culminating in a Cathedral Pipe Organ apotheosis."
            ),
            "sample_rate": 48000,
            "tempo": self.tempo.to_json(),
            "tracks": tracks_json,
        }


# =============================================================================
# Compose the 4-Movement Orchestral Classical Work (~4:00)
# =============================================================================
def compose_orchestral_work() -> Tuple[OrchestraBuilder, Dict]:
    tempo_segments = [
        # Movement I: Adagio Sostenuto — Cradle of Pure Thirds & Comma Lift (Beats 0..72)
        (0.0, 58.0),
        (24.0, 61.0),
        (48.0, 63.0),
        (66.0, 59.0),
        (71.99, 59.0),
        # Movement II: Allegretto Grazioso — Classical Scherzo & Fugato (Beats 72..148)
        (72.0, 88.0),
        (104.0, 91.0),
        (136.0, 86.0),
        (144.0, 78.0),
        (147.99, 78.0),
        # Movement III: Allegro Appassionato — Diesis Tempest & Comma Cascade (Beats 148..224)
        (148.0, 86.0),
        (164.0, 84.0),
        (172.0, 90.0),
        (204.0, 85.0),
        (216.0, 73.0),
        (223.99, 73.0),
        # Movement IV: Maestoso & Adagio — Passacaglia & Cathedral Apotheosis (Beats 224..296)
        (224.0, 68.0),
        (256.0, 65.0),
        (276.0, 60.0),
        (288.0, 52.0),
    ]
    ob = OrchestraBuilder(tempo_segments)

    # =========================================================================
    # MOVEMENT I: ADAGIO SOSTENUTO — "CRADLE OF PURE THIRDS" (Beats 0..72)
    #   I.A (0..24, k=0): Beat-free 4:5:6 F Major & 4:5:6:7:9 Septimal Cradle
    #                     around A4 = 440.00 Hz (instant 53-EDO vs 12-TET A/B!)
    #   I.B (24..48, k=0): Lyrical Brahmsian Woodwind & String Dialogue
    #   I.C (48..72, k=0 -> +1): Transparent Upward Syntonic Comma Lift (+22.6c)
    # =========================================================================
    m1_chords = [
        # I.A (0..24): Pure 5-limit & 7-limit sustained harmonic showcase
        (0.0, 6.0, F, "maj", "I.A1 Pure 4:5:6 F maj (A4=440Hz)", F),
        (6.0, 12.0, C, "dom9", "I.A2 Septimal C dom9(4:5:6:7:9) / F pedal", F),
        (12.0, 16.0, D_MINUS, "min", "I.A3 Pure 10:12:15 Dm-(8,22,39)", None),
        (16.0, 20.0, BB, "maj9", "I.A4 Pure Bb maj9(44,8,22,39,0)", None),
        (20.0, 24.0, C, "dom7", "I.A5 Pure Septimal C dom7(7:4)", None),
        # I.B (24..48): Flowing Pastoral & Septimal Bloom
        (24.0, 28.0, F, "add9", "I.B1 F add9", None),
        (28.0, 32.0, F, "dom9", "I.B2 Septimal F dom9(Eb_harm=12!)", None),
        (32.0, 36.0, BB, "maj9", "I.B3 Bb maj9 resolution", None),
        (36.0, 40.0, G_MINUS, "min7", "I.B4 Gm-7(30,44,8,22)", None),
        (40.0, 44.0, C, "dom9", "I.B5 C dom9(7:4)", None),
        (44.0, 48.0, F, "maj9", "I.B6 F maj9 glow", None),
        # I.C (48..72): UPWARD 5-LIMIT SYNTONIC COMMA PUMP (k = 0 -> k = +1, F22 -> F+23!)
        # Common tones: C(0) -> G(31),D(9) -> Bb+(45),D(9) -> F+(23) -> C+(1) -> F+(23)
        (48.0, 52.0, F, "maj", "I.C1 CommaUp I(22 = F)", None),
        (52.0, 56.0, C, "maj", "I.C2 CommaUp V(0 = C, shares C0)", None),
        (56.0, 60.0, G, "min7", "I.C3 CommaUp ii(31 = Gm, shares G31 & D9)", None),
        (60.0, 64.0, BB + 1, "maj9", "I.C4 CommaUp IV+(45 = Bb+, shares 45 & D9!)", None),
        (64.0, 68.0, C + 1, "dom9", "I.C5 CommaUp V9+(1 = C+, septimal Bb+harm=44)", None),
        (68.0, 72.0, F + 1, "add9", "I.C6 CommaUp Arrival I+(23 = F+, +1 comma!)", None),
    ]
    m1_spans = [ob.add_span(*c) for c in m1_chords]

    # --- I.A (0..24): Glass-Still Pure Thirds & Septimal Ninths ---
    for i, sp in enumerate(m1_spans[:5]):
        dur = sp.end - sp.start
        br = sp.bass_root()
        dyn = [0.48, 0.54, 0.58, 0.62, 0.56][i]
        ob.string_swell(sp, vel=dyn, include_9=(i in (1, 3)), trim_tail=0.16)
        ob.note("bassoon", sp.start, dur - 0.25, br, dyn + 0.08)
        ob.note("cello", sp.start, dur - 0.25, br + OCT, dyn + 0.10)
        # Golden French Horn holds the pure 5:4 third A3/A4 or 7:4 seventh!
        horn_steps = [
            pitch(A, 3),            # Bar 0: exact A3 (220.00 Hz) pure 5:4 over F!
            pitch(BB_HARM, 3),      # Bar 1: exact 7:4 septimal 7th over C!
            pitch(A, 3),            # Bar 2: common-tone A3 (pure 3:2 fifth of D-8!)
            pitch(A, 3),            # Bar 3: pure 15:8 maj7 over Bb(44)!
            pitch(G, 3),            # Bar 4: pure 3:2 fifth of C(0)
        ]
        ob.note("french_horn", sp.start + 0.15, dur - 0.40, horn_steps[i], dyn + 0.12)
        ob.harp_gliss(
            sp,
            sp.start + 0.25,
            pitch(F, 3) - 10,
            pitch(A, 5),
            vel=dyn + 0.12,
            spacing=0.24,
            note_dur=2.8,
            ascending=(i != 4),
            max_notes=8,
        )

    # Singing English Horn Principal Theme ("Prisma Motif": F4 -> A4 -> C5 -> G4 -> A4)
    ob.phrase("english_horn", [
        # Bar 0 (0..6, F maj): emerges warmly out of the pure A=440Hz string chord
        (1.0, 2.2, pitch(A, 4), 0.72),
        (3.4, 1.1, pitch(C, 5), 0.76),
        (4.6, 1.2, pitch(A, 4), 0.72),
        # Bar 1 (6..12, C dom9/F): lingers on the luminous 7:4 Bb_harm(43) & 9:8 D5!
        (6.2, 2.2, pitch(BB_HARM, 4), 0.80),
        (8.6, 1.1, pitch(G, 4), 0.74),
        (9.8, 1.9, pitch(E, 4), 0.70),
        # Breath 11.7..12.5
        # Bar 2..4 (12..24): tender arch across Dm- -> Bb maj9 -> C dom7(7:4)
        (12.5, 1.6, pitch(F, 4), 0.74),
        (14.2, 1.6, pitch(A, 4), 0.78),
        (16.0, 1.8, pitch(D_MINUS, 5), 0.82),    # Pure 5:4 major third above Bb(44)!
        (18.0, 0.9, pitch(C, 5), 0.78),
        (19.0, 0.9, pitch(A, 4), 0.74),
        (20.0, 1.8, pitch(G, 4), 0.76),
        (22.0, 1.7, pitch(E, 4), 0.68),
    ], expressive_slide=18.0)

    # Solo Viola warm inner counterpoint in I.A (bars 2..4)
    ob.phrase("viola", [
        (12.0, 1.8, pitch(D_MINUS, 4), 0.64),
        (14.0, 1.8, pitch(F, 4), 0.68),
        (16.0, 1.8, pitch(F, 4), 0.70),
        (18.0, 1.8, pitch(D_MINUS, 4), 0.68),
        (20.0, 1.8, pitch(C, 4), 0.68),
        (22.0, 1.7, pitch(BB_HARM, 3), 0.66),
    ])

    # --- I.B (24..48): Brahmsian/Debussyan Orchestral Bloom (Septimal F dom9 -> Bb maj9) ---
    for i, sp in enumerate(m1_spans[5:11]):
        br = sp.bass_root()
        dyn = 0.56 + 0.03 * (i if i < 4 else 6 - i)
        ob.string_swell(sp, vel=dyn, include_9=True)
        ob.piano_accompaniment(sp, vel=dyn * 0.90, style="nocturne", step_beats=0.5)
        ob.note("bassoon", sp.start, 3.7, br, dyn + 0.06)
        if i in (0, 2, 4, 5):
            ob.harp_gliss(sp, sp.start, pitch(C, 3), pitch(C, 6), vel=dyn + 0.12, spacing=0.16, note_dur=2.2, ascending=(i != 4), max_notes=9)

    # Clarinet & Solo Cello soaring duet in I.B (spotlighting F dom9's septimal Eb_harm = 12!)
    ob.phrase("clarinet", [
        (24.0, 1.35, pitch(F, 4), 0.74),
        (25.5, 0.45, pitch(G, 4), 0.76),
        (26.0, 1.80, pitch(A, 4), 0.80),
        # Bar 28 (F dom9): pure septimal 7:4 above F(22) is EB_HARM(12) in Oct 5!
        (28.0, 1.80, pitch(EB_HARM, 5), 0.84),
        (30.0, 0.90, pitch(C, 5), 0.80),
        (31.0, 0.90, pitch(A, 4), 0.78),
        # Bar 32 (Bb maj9): resolves purely by step into D_MINUS(8)5!
        (32.0, 1.80, pitch(D_MINUS, 5), 0.86),
        (34.0, 0.90, pitch(C, 5), 0.82),
        (35.0, 0.90, pitch(A, 4), 0.78),
        # Bar 36 (Gm-7 -> C dom9 -> F maj9)
        (36.0, 1.35, pitch(BB, 4), 0.80),
        (37.5, 0.45, pitch(A, 4), 0.76),
        (38.0, 1.80, pitch(G_MINUS, 4), 0.76),
        (40.0, 1.35, pitch(G, 4), 0.78),
        (41.5, 0.45, pitch(BB_HARM, 4), 0.80),
        (42.0, 1.80, pitch(D, 5), 0.82),
        (44.0, 1.80, pitch(C, 5), 0.76),
        (46.0, 1.80, pitch(A, 4), 0.70),
    ])
    ob.phrase("cello", [
        (24.0, 1.8, pitch(F, 3), 0.68),
        (26.0, 1.8, pitch(C, 4), 0.72),
        (28.0, 1.8, pitch(A, 3), 0.74),
        (30.0, 1.8, pitch(F, 3), 0.70),
        (32.0, 1.8, pitch(BB, 3), 0.76),
        (34.0, 1.8, pitch(F, 3), 0.72),
        (36.0, 1.8, pitch(G_MINUS, 3), 0.74),
        (38.0, 1.8, pitch(D_MINUS, 4), 0.76),
        (40.0, 1.8, pitch(E, 3), 0.72),
        (42.0, 1.8, pitch(G, 3), 0.74),
        (44.0, 3.6, pitch(F, 3), 0.68),
    ], expressive_slide=15.0)

    # --- I.C (48..72): Transparent Upward 5-Limit Syntonic Comma Lift (k = 0 -> +1) ---
    for i, sp in enumerate(m1_spans[11:]):
        br = sp.bass_root()
        dyn = 0.52 + 0.04 * i
        ob.string_swell(sp, vel=dyn * 0.86, include_9=(i >= 3))
        ob.piano_accompaniment(sp, vel=dyn * 0.86, style="nocturne", step_beats=0.5)
        ob.note("bassoon", sp.start, 3.7, br, dyn + 0.06)
        ob.harp_gliss(sp, sp.start, pitch(C, 3), pitch(C, 6), vel=dyn + 0.14, spacing=0.15, note_dur=2.3, ascending=True, max_notes=10)

    # English Horn & French Horn highlight the exact held common-tone pivots across k = 0 -> +1!
    ob.phrase("english_horn", [
        (48.0, 1.8, pitch(A, 4, 0), 0.74),
        (50.0, 1.8, pitch(C, 5, 0), 0.78),            # Pivot 1: C(0) held into V(C)!
        (52.0, 1.8, pitch(C, 5, 0), 0.78),
        (54.0, 1.8, pitch(G, 4, 0), 0.76),            # Pivot 2: G(31) held into ii(Gm)!
        (56.0, 1.8, pitch(G, 4, 0), 0.78),
        (58.0, 1.8, pitch(D, 4, 0), 0.80),            # Pivot 3: D(9) = pure M3 of Bb+(45)!
        (60.0, 1.8, pitch(D_MINUS, 4, 1), 0.82),      # pitch(D_MINUS,4,1) == 8+1 == 9 (exact D4!)
        (62.0, 1.8, pitch(F, 4, 1), 0.86),            # Lifted tonic F+(23) emerges!
        (64.0, 1.35, pitch(G, 4, 1), 0.88),
        (65.5, 0.45, pitch(BB_HARM, 4, 1), 0.86),     # Septimal 7:4 over C+(1)
        (66.0, 1.8, pitch(E, 4, 1), 0.84),
        (68.0, 3.6, pitch(A, 4, 1), 0.80),            # Radiant arrival on F+(23), A+(40)!
    ])
    ob.phrase("french_horn", [
        (52.0, 3.6, pitch(G, 3, 0), 0.66),
        (56.0, 3.6, pitch(BB, 3, 1), 0.70),           # 44+1 = 45 (pure m3 of Gm31!)
        (60.0, 3.6, pitch(F, 3, 1), 0.74),
        (64.0, 3.6, pitch(C, 4, 1), 0.78),
        (68.0, 3.6, pitch(C, 4, 1), 0.74),
    ])

    # =========================================================================
    # MOVEMENT II: ALLEGRETTO GRAZIOSO — "SCHERZO & FUGATO" (Beats 72..148, k = +1)
    #   II.A (72..104): Buoyant Classical Scherzo (Pizzicato, Clarinet, Piano, Viola — NO pad!)
    #   II.B (104..136): 4-Voice Orchestral Fugato (Clarinet -> Viola -> Eng Horn -> Cello/Bassoon)
    #   II.C (136..148): Sunlit Horn Cadence & Bridge to the Minor Tempest
    # =========================================================================
    k1 = 1
    m2_chords = [
        # II.A (72..104, k=+1): Agile Classical 8-bar Scherzo Theme
        (72.0, 76.0, F + k1, "maj", "II.A1 F+ scherzo"),
        (76.0, 80.0, C + k1, "maj", "II.A2 C+"),
        (80.0, 84.0, D_MINUS + k1, "min7", "II.A3 Dm7+"),
        (84.0, 88.0, C + k1, "maj", "II.A4 C+ half-cadence"),
        (88.0, 92.0, BB + k1, "maj9", "II.A5 Bb+ maj9"),
        (92.0, 96.0, F + k1, "maj", "II.A6 F+"),
        (96.0, 100.0, G_MINUS + k1, "min7", "II.A7 Gm7+"),
        (100.0, 104.0, C + k1, "dom9", "II.A8 C+ dom9(7:4)"),
        # II.B (104..136, k=+1): 4-Voice Imitative Fugato across the Orchestra
        (104.0, 108.0, F + k1, "maj", "II.B1 Fugato Voice 1 (Clarinet): F+"),
        (108.0, 112.0, C + k1, "maj", "II.B2 Fugato Voice 2 (Viola): C+"),
        (112.0, 116.0, D_MINUS + k1, "min", "II.B3 Fugato Voice 3 (Eng Horn): Dm+"),
        (116.0, 120.0, A + k1, "min", "II.B4 Fugato Voice 4 (Cello): Am+"),
        (120.0, 124.0, BB + k1, "maj7", "II.B5 Fugato Episode Bb+ maj7"),
        (124.0, 128.0, F + k1, "add9", "II.B6 Fugato Episode F+ add9"),
        (128.0, 132.0, G_MINUS + k1, "min7", "II.B7 Stretto Gm7+"),
        (132.0, 136.0, C + k1, "dom9", "II.B8 Stretto V9+"),
        # II.C (136..148, k=+1): Sunlit Resolution -> Dramatic Shadow Pivot to Dm+
        (136.0, 140.0, F + k1, "add9", "II.C1 Sunlit F+ add9"),
        (140.0, 144.0, F + k1, "maj", "II.C2 F+"),
        (144.0, 148.0, A + k1, "dom7", "II.C3 Shadow Pivot V7/vi (A+ dom7 -> Dm+!)"),
    ]
    m2_spans = [ob.add_span(*c) for c in m2_chords]

    # --- II.A (72..104): Translucent Classical Scherzando ---
    for i, sp in enumerate(m2_spans[:8]):
        br = sp.bass_root()
        ob.piano_accompaniment(sp, vel=0.52, style="scherzo", step_beats=0.5)
        # Buoyant Classical Pizzicato pulse (beats 0, 1, 2, 3)
        ob.note("pizzicato", sp.start + 0.0, 0.45, br + OCT, 0.66)
        ob.note("pizzicato", sp.start + 1.0, 0.40, br + OCT + P5, 0.50)
        ob.note("pizzicato", sp.start + 2.0, 0.45, br + OCT, 0.58)
        ob.note("pizzicato", sp.start + 3.0, 0.40, br + OCT + P5, 0.52)
        if i >= 4:
            ob.note("bassoon", sp.start, 1.6, br, 0.60)
            ob.note("bassoon", sp.start + 2.0, 1.6, br + P5, 0.54)
        if i in (0, 4, 7):
            ob.harp_gliss(sp, sp.start, pitch(F, 3, k1), pitch(C, 6, k1), vel=0.62, spacing=0.13, note_dur=1.4, ascending=True, max_notes=7)

    # Sparkling Clarinet & Piano Scherzo Melody (72..104)
    ob.phrase("clarinet", [
        # Antecedent (72..88)
        (72.0, 0.85, pitch(F, 4, k1), 0.74),
        (73.0, 0.42, pitch(G, 4, k1), 0.72),
        (73.5, 0.42, pitch(A, 4, k1), 0.76),
        (74.0, 0.85, pitch(C, 5, k1), 0.80),
        (75.0, 0.85, pitch(A, 4, k1), 0.76),
        (76.0, 1.35, pitch(G, 4, k1), 0.78),
        (77.5, 0.42, pitch(E, 4, k1), 0.72),
        (78.0, 1.50, pitch(C, 4, k1), 0.70),
        (80.0, 0.85, pitch(F, 4, k1), 0.76),
        (81.0, 0.42, pitch(G, 4, k1), 0.78),
        (81.5, 0.42, pitch(A, 4, k1), 0.80),
        (82.0, 0.85, pitch(D_MINUS, 5, k1), 0.82),
        (83.0, 0.85, pitch(A, 4, k1), 0.76),
        (84.0, 0.85, pitch(G, 4, k1), 0.76),
        (85.0, 0.42, pitch(A, 4, k1), 0.74),
        (85.5, 0.42, pitch(G, 4, k1), 0.72),
        (86.0, 1.50, pitch(E, 4, k1), 0.70),
        # Consequent (88..104)
        (88.0, 0.85, pitch(D_MINUS, 5, k1), 0.82),
        (89.0, 0.42, pitch(C, 5, k1), 0.78),
        (89.5, 0.42, pitch(BB, 4, k1), 0.76),
        (90.0, 0.85, pitch(A, 4, k1), 0.80),
        (91.0, 0.85, pitch(F, 4, k1), 0.74),
        (92.0, 0.85, pitch(A, 4, k1), 0.78),
        (93.0, 0.42, pitch(C, 5, k1), 0.80),
        (93.5, 0.42, pitch(F, 5, k1), 0.84),
        (94.0, 1.50, pitch(C, 5, k1), 0.78),
        (96.0, 0.85, pitch(BB, 4, k1), 0.78),
        (97.0, 0.85, pitch(G_MINUS, 4, k1), 0.74),
        (98.0, 0.85, pitch(D_MINUS, 5, k1), 0.80),
        (99.0, 0.85, pitch(BB, 4, k1), 0.76),
        (100.0, 0.85, pitch(C, 5, k1), 0.80),
        (101.0, 0.42, pitch(BB_HARM, 4, k1), 0.78),
        (101.5, 0.42, pitch(A, 4, k1 + 1), 0.76),
        (102.0, 1.60, pitch(G, 4, k1), 0.74),
    ], snap_to_harmony=True)

    # Viola nimble staccato-legato counter-subject in II.A
    ob.phrase("viola", [
        (74.0, 0.85, pitch(A, 4, k1), 0.68),
        (75.0, 0.85, pitch(F, 4, k1), 0.66),
        (78.0, 0.85, pitch(E, 4, k1), 0.68),
        (79.0, 0.85, pitch(G, 4, k1), 0.70),
        (82.0, 0.85, pitch(F, 4, k1), 0.70),
        (83.0, 0.85, pitch(D_MINUS, 4, k1), 0.68),
        (86.0, 1.50, pitch(C, 4, k1), 0.68),
        (90.0, 0.85, pitch(F, 4, k1), 0.70),
        (91.0, 0.85, pitch(D_MINUS, 4, k1), 0.68),
        (94.0, 0.85, pitch(A, 4, k1), 0.72),
        (95.0, 0.85, pitch(F, 4, k1), 0.70),
        (98.0, 0.85, pitch(G_MINUS, 4, k1), 0.72),
        (99.0, 0.85, pitch(F, 4, k1), 0.70),
        (102.0, 1.50, pitch(E, 4, k1), 0.72),
    ], snap_to_harmony=True)

    # --- II.B (104..136): Genuine 4-Voice Classical Fugato Exposition & Stretto! ---
    # Voice 1 (104..108): Clarinet states rising-fourth/stepwise Fugato Subject on F+
    ob.phrase("clarinet", [
        (104.0, 0.85, pitch(C, 4, k1), 0.76),
        (105.0, 0.85, pitch(F, 4, k1), 0.80),
        (106.0, 0.42, pitch(G, 4, k1), 0.78),
        (106.5, 0.42, pitch(A, 4, k1), 0.82),
        (107.0, 0.85, pitch(C, 5, k1), 0.84),
        # Continues with brisk countersubject over Voice 2!
        (108.0, 0.85, pitch(E, 5, k1), 0.80),
        (109.0, 0.42, pitch(D, 5, k1), 0.78),
        (109.5, 0.42, pitch(C, 5, k1), 0.76),
        (110.0, 1.60, pitch(G, 4, k1), 0.74),
        # Stretto return at 120..136!
        (120.0, 0.85, pitch(D_MINUS, 5, k1), 0.80),
        (121.0, 0.85, pitch(C, 5, k1), 0.78),
        (122.0, 1.60, pitch(A, 4, k1), 0.76),
        (124.0, 0.85, pitch(C, 5, k1), 0.82),
        (125.0, 0.42, pitch(D, 5, k1), 0.80),
        (125.5, 0.42, pitch(F, 5, k1), 0.86),
        (126.0, 1.60, pitch(C, 5, k1), 0.82),
        (128.0, 0.85, pitch(BB, 4, k1), 0.82),
        (129.0, 0.85, pitch(D_MINUS, 5, k1), 0.84),
        (130.0, 1.60, pitch(G_MINUS, 4, k1), 0.78),
        (132.0, 0.85, pitch(G, 4, k1), 0.82),
        (133.0, 0.85, pitch(BB_HARM, 4, k1), 0.84),
        (134.0, 1.70, pitch(E, 5, k1), 0.86),
    ], snap_to_harmony=True)

    # Voice 2 (108..116): Solo Viola tonal answer on C+
    ob.phrase("viola", [
        (108.0, 0.85, pitch(G, 3, k1), 0.78),
        (109.0, 0.85, pitch(C, 4, k1), 0.82),
        (110.0, 0.42, pitch(D, 4, k1), 0.80),
        (110.5, 0.42, pitch(E, 4, k1), 0.82),
        (111.0, 0.85, pitch(G, 4, k1), 0.84),
        (112.0, 0.85, pitch(A, 4, k1), 0.80),
        (113.0, 0.85, pitch(F, 4, k1), 0.78),
        (114.0, 1.60, pitch(D_MINUS, 4, k1), 0.74),
        # Episode & Stretto counterpoint 116..136
        (116.0, 1.80, pitch(E, 4, k1), 0.74),
        (118.0, 1.80, pitch(C, 4, k1), 0.72),
        (120.0, 1.80, pitch(F, 4, k1), 0.76),
        (122.0, 1.80, pitch(D_MINUS, 4, k1), 0.74),
        (124.0, 1.80, pitch(A, 4, k1), 0.78),
        (126.0, 1.80, pitch(F, 4, k1), 0.76),
        (128.5, 0.85, pitch(F, 4, k1), 0.78),
        (129.5, 0.85, pitch(BB, 4, k1), 0.80),
        (130.5, 1.30, pitch(D_MINUS, 4, k1), 0.76),
        (132.0, 1.80, pitch(C, 4, k1), 0.78),
        (134.0, 1.70, pitch(G, 4, k1), 0.80),
    ], snap_to_harmony=True)

    # Voice 3 (112..124): English Horn enters warmly on Dm+
    ob.phrase("english_horn", [
        (112.0, 0.85, pitch(A, 3, k1), 0.80),
        (113.0, 0.85, pitch(D_MINUS, 4, k1), 0.84),
        (114.0, 0.42, pitch(E, 4, k1), 0.82),
        (114.5, 0.42, pitch(F, 4, k1), 0.84),
        (115.0, 0.85, pitch(A, 4, k1), 0.86),
        (116.0, 0.85, pitch(C, 5, k1), 0.84),
        (117.0, 0.85, pitch(A, 4, k1), 0.80),
        (118.0, 1.70, pitch(E, 4, k1), 0.76),
        # Rejoins in Stretto 128..136
        (128.0, 1.80, pitch(D_MINUS, 4, k1), 0.78),
        (130.0, 1.80, pitch(BB, 4, k1), 0.82),
        (132.0, 1.80, pitch(E, 4, k1), 0.80),
        (134.0, 1.70, pitch(BB_HARM, 4, k1), 0.84),
    ], snap_to_harmony=True)

    # Voice 4 (116..136): Cello + Bassoon enter in the bass/baritone with the Subject!
    ob.phrase("cello", [
        (116.0, 0.85, pitch(E, 3, k1), 0.80),
        (117.0, 0.85, pitch(A, 3, k1), 0.84),
        (118.0, 0.42, pitch(B, 3, k1), 0.82),
        (118.5, 0.42, pitch(C, 4, k1), 0.84),
        (119.0, 0.85, pitch(E, 4, k1), 0.86),
        (120.0, 1.80, pitch(BB, 3, k1), 0.80),
        (122.0, 1.80, pitch(F, 3, k1), 0.78),
        (124.0, 1.80, pitch(F, 3, k1), 0.80),
        (126.0, 1.80, pitch(A, 3, k1), 0.82),
        (128.0, 1.80, pitch(G_MINUS, 3, k1), 0.82),
        (130.0, 1.80, pitch(BB, 3, k1), 0.80),
        (132.0, 1.80, pitch(C, 3, k1), 0.84),
        (134.0, 1.80, pitch(G, 3, k1), 0.82),
    ], snap_to_harmony=True)

    for i, sp in enumerate(m2_spans[8:16]):
        br = sp.bass_root()
        if i >= 4:
            ob.piano_accompaniment(sp, vel=0.54, style="scherzo", step_beats=0.5)
            ob.note("bassoon", sp.start, 3.6, br, 0.68)
            ob.string_swell(sp, vel=0.48 + 0.04 * (i - 4), include_9=True)
        else:
            ob.note("pizzicato", sp.start, 0.45, br + OCT, 0.56)
            ob.note("pizzicato", sp.start + 2.0, 0.45, br + OCT + P5, 0.50)

    # --- II.C (136..148): Sunlit Horn Cadence -> Sudden Dramatic Shadow Pivot (A+ dom7 -> Dm+) ---
    for i, sp in enumerate(m2_spans[16:]):
        br = sp.bass_root()
        dyn = [0.68, 0.62, 0.72][i]
        ob.string_swell(sp, vel=dyn * 0.86, include_9=(i == 0))
        ob.note("bassoon", sp.start, 3.7, br, dyn * 0.92)
        ob.note("cello", sp.start, 3.7, br + OCT, dyn * 0.90)
        if i < 2:
            ob.harp_gliss(sp, sp.start, pitch(F, 3, k1), pitch(C, 6, k1), vel=0.70, spacing=0.14, note_dur=2.0, ascending=(i == 0), max_notes=9)
        else:
            # Bar 144..148: A+ dom7(7:4) foreboding tremolo-like piano octaves into Tempest!
            ob.piano_accompaniment(sp, vel=0.66, style="storm", step_beats=0.5)

    ob.phrase("french_horn", [
        (136.0, 1.35, pitch(C, 4, k1), 0.80),
        (137.5, 0.45, pitch(F, 4, k1), 0.84),
        (138.0, 1.80, pitch(A, 4, k1), 0.86),
        (140.0, 3.60, pitch(C, 4, k1), 0.76),
        # Foreboding septimal dominant ninth call on A+(40): G_harm = 40+43 = 83 ≡ 30!
        (144.0, 1.80, pitch(A, 3, k1), 0.82),
        (146.0, 1.80, pitch(E, 4, k1), 0.86),
    ], snap_to_harmony=True)

    # =========================================================================
    # MOVEMENT III: ALLEGRO APPASSIONATO — "DIESIS TEMPEST & COMMA CASCADE" (148..224)
    #   III.A (148..172, k=+1): Beethovenian D-minor Drive + Subito Piano Breath
    #   III.B (172..204, k=+1 -> +3): Chromatic-Mediant Diesis Summit!
    #                                 F+(23) -> Db+(6) -> A--(42) -> F+++(25)
    #   III.C (204..224, k=+3 -> 0):  Triple Downward Comma Cascade (+3 -> +2 -> +1 -> 0)
    # =========================================================================
    m3_chords = [
        # III.A (148..172, k=+1): Stormy D minor (D_MINUS+1 = 9? Wait: let's use D=9+1=10 min: [10, 24, 41] or D_MINUS+1=9 min: [9, 23(F+!), 40(A+!)])
        # YES! Look at (D_MINUS + k1 = 9) min = [9, 23(F+), 40(A+)] — exact relative minor of F+(23)!
        (148.0, 152.0, 9, "min", "III.A1 Storm Dm+(9,23,40)"),
        (152.0, 156.0, 45, "maj7", "III.A2 Bb+ maj7(45,9,23,40)"),
        (156.0, 160.0, 31, "min7", "III.A3 Gm7+(31,45,9,23)"),
        (160.0, 164.0, 40, "dom7", "III.A4 V7/vi A+ dom7(40,4,18,30)"),
        (164.0, 168.0, 9, "min", "III.A5 Subito Piano Dm+ whisper!"),
        (168.0, 172.0, 1, "dom9", "III.A6 Explosive Crescendo C+ dom9 -> F+!"),
        # III.B (172..204): Chromatic-Mediant Diesis Ascent (+1 -> +3, exact common tones!)
        #   23 (F+: 23, 40, 1) -> 6 (Db+: 6, 23, 37 — shares 23!)
        #   -> 42 (A--+: 42, 6, 20 — shares 6!) -> 25 (F+++: 25, 42, 3 — shares 42!)
        (172.0, 180.0, 23, "maj", "III.B1 Diesis Pillar 1: F+(23,40,1)"),
        (180.0, 188.0, 6, "maj", "III.B2 Diesis Pillar 2: Db+(6,23,37 — holds F+23!)"),
        (188.0, 196.0, 42, "maj", "III.B3 Diesis Pillar 3: A(42,6,20 — holds Db+6!)"),
        (196.0, 204.0, 25, "add9", "III.B4 Diesis Summit: F+++(25,42,3,34 — holds A42!)"),
        # III.C (204..224): Triple Downward Syntonic Comma Cascade (k=+3 -> +2 -> +1 -> 0)
        #   Each pump: I(22+k) -> IV(44+k) -> ii(30+k min) -> V7(-1+k dom7) -> I(21+k)
        # Pump 1 (+3 -> +2): Full-Orchestra Heroic Surge (6 beats)
        (204.0, 205.5, 25, "maj", "III.C1 I(+3 = 25)"),
        (205.5, 207.0, 47, "maj", "III.C1 IV(+3 = 47)"),
        (207.0, 208.5, 33, "min", "III.C1 ii(+3 = 33)"),
        (208.5, 210.0, 2, "dom7", "III.C1 V7(+2 = 2)"),
        # Pump 2 (+2 -> +1): Agile Woodwind & String Canon (6 beats)
        (210.0, 211.5, 24, "maj", "III.C2 I(+2 = 24)"),
        (211.5, 213.0, 46, "maj", "III.C2 IV(+2 = 46)"),
        (213.0, 214.5, 32, "min", "III.C2 ii(+2 = 32)"),
        (214.5, 216.0, 1, "dom7", "III.C2 V7(+1 = 1)"),
        # Pump 3 (+1 -> 0): Expressive Broadening Homecoming into Passacaglia! (8 beats)
        (216.0, 218.0, 23, "maj", "III.C3 I(+1 = 23)"),
        (218.0, 220.0, 44, "maj", "III.C3 IV(0 = 44? Wait: 23+22=45!)"),
        (220.0, 222.0, 31, "min", "III.C3 ii(+1 = 31)"),
        (222.0, 224.0, 0, "dom9", "III.C3 V9(0 = C dom9 -> HOME F=22!)"),
    ]
    # Fix III.C3 exact comma pump math (+1 -> 0):
    # From I(23): IV is 23 + 22 = 45 ([45, 9, 23]), ii is 23 + 8 = 31 ([31, 45, 9]), V9(0) is [0, 17, 31, 43, 9] (shares 31 & 9!), resolving to I(22 = F)!
    m3_chords[-3] = (218.0, 220.0, 45, "maj", "III.C3 IV(+1 = 45, shares 23)")
    m3_spans = [ob.add_span(*c) for c in m3_chords]

    # --- III.A (148..172): Beethovenian Kinetic Motor + Subito Piano ---
    for i, sp in enumerate(m3_spans[:6]):
        br = sp.bass_root()
        is_subito_p = (i == 4)
        dyn = 0.42 if is_subito_p else (0.72 + 0.04 * i)
        ob.piano_accompaniment(sp, vel=dyn * 0.88, style="storm", step_beats=0.5)
        q_third = M3 if sp.quality in ("maj", "maj7", "dom7", "dom9") else m3
        for k_s, off in enumerate([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]):
            acc = 1.10 if k_s in (0, 3, 4) else 0.80
            ob.note("cello", sp.start + off, 0.36, br + OCT + (P5 if k_s % 2 == 1 else 0), dyn * 0.90 * acc)
            ob.note("viola", sp.start + off, 0.34, sp.tenor_root() + OCT + (q_third if k_s % 2 == 1 else 0), dyn * 0.74 * acc)
        ob.note("bassoon", sp.start, 1.6, br, dyn * 0.92)
        if not is_subito_p:
            ob.note("bassoon", sp.start + 2.0, 1.6, br + P5, dyn * 0.86)
            ob.note("pizzicato", sp.start, 0.42, br + OCT, dyn * 0.84)
            ob.note("pizzicato", sp.start + 1.5, 0.42, br + OCT, dyn * 0.78)
            ob.string_swell(sp, vel=dyn * 0.78, include_9=False)

    # Heroic Dotted French Horn & Fierce Clarinet Sweeps in III.A
    ob.phrase("french_horn", [
        (148.0, 0.40, pitch(A, 3, k1), 0.82),
        (148.5, 0.40, pitch(A, 3, k1), 0.84),
        (149.0, 0.40, pitch(A, 3, k1), 0.88),
        (149.5, 2.10, pitch(F, 4, k1), 0.92),
        (152.0, 1.35, pitch(D_MINUS, 4, k1), 0.86),
        (153.5, 0.45, pitch(F, 4, k1), 0.88),
        (154.0, 1.70, pitch(A, 4, k1), 0.90),
        (156.0, 1.35, pitch(G_MINUS, 4, k1), 0.86),
        (157.5, 0.45, pitch(F, 4, k1), 0.84),
        (158.0, 1.70, pitch(D_MINUS, 4, k1), 0.82),
        (160.0, 3.60, pitch(E, 4, k1), 0.88),
        # Roaring crescendo out of subito piano (168..172)
        (168.0, 1.35, pitch(C, 4, k1), 0.82),
        (169.5, 0.45, pitch(E, 4, k1), 0.88),
        (170.0, 1.80, pitch(G, 4, k1), 0.94),
    ], snap_to_harmony=True)

    ob.phrase("clarinet", [
        (150.0, 0.45, pitch(A, 4, k1), 0.80),
        (150.5, 0.45, pitch(D_MINUS, 5, k1), 0.84),
        (151.0, 0.85, pitch(F, 5, k1), 0.88),
        (154.0, 0.45, pitch(A, 4, k1), 0.82),
        (154.5, 0.45, pitch(C, 5, k1), 0.86),
        (155.0, 0.85, pitch(F, 5, k1), 0.88),
        (158.0, 0.45, pitch(BB, 4, k1), 0.82),
        (158.5, 0.45, pitch(D_MINUS, 5, k1), 0.86),
        (159.0, 0.85, pitch(G_MINUS, 4, k1), 0.82),
        # Eerie subito piano sigh on English Horn/Clarinet at 164..168
        (164.5, 1.20, pitch(F, 4, k1), 0.50),
        (166.0, 1.60, pitch(D_MINUS, 4, k1), 0.48),
        # Blazing scale up to Diesis Pillar 1!
        (168.5, 0.45, pitch(G, 4, k1), 0.80),
        (169.0, 0.45, pitch(BB_HARM, 4, k1), 0.84),
        (169.5, 0.45, pitch(C, 5, k1), 0.88),
        (170.0, 1.80, pitch(E, 5, k1), 0.92),
    ], snap_to_harmony=True)

    # --- III.B (172..204): 4 Monumental Chromatic-Mediant Diesis Pillars (23 -> 6 -> 42 -> 25) ---
    diesis_spans = m3_spans[6:10]
    # Common-tone golden thread: F+(23) -> Db+(6) -> A(42) -> F+++(25)
    diesis_fanfares = [
        # Pillar 0 (172..180, F+ = 23): [23, 40, 1]
        [(172.0, 1.35, 23, 0.88), (173.5, 0.45, 40, 0.90), (174.0, 1.80, 54, 0.92),
         (176.0, 1.80, 40, 0.88), (178.0, 1.85, 23 + OCT, 0.92)],
        # Pillar 1 (180..188, Db+ = 6): [6, 23, 37] — pivots directly on held 23+OCT (76)!
        [(180.0, 1.80, 23 + OCT, 0.92), (182.0, 1.80, 37, 0.90), (184.0, 1.35, 6 + OCT, 0.92),
         (185.5, 0.45, 37, 0.88), (186.0, 1.85, 6 + OCT, 0.92)],
        # Pillar 2 (188..196, A = 42): [42, 6, 20] — pivots directly on held 6+OCT (59)!
        [(188.0, 1.80, 6 + OCT, 0.92), (190.0, 1.80, 20 + OCT, 0.94), (192.0, 1.35, 42, 0.90),
         (193.5, 0.45, 6 + OCT, 0.92), (194.0, 1.85, 42 + OCT, 0.94)],
        # Pillar 3 (196..204, F+++ = 25): [25, 42, 3, 34] — pivots on held 42+OCT (95)!
        [(196.0, 1.80, 42 + OCT, 0.95), (198.0, 1.80, 3 + OCT, 0.94), (200.0, 1.35, 25 + OCT, 0.95),
         (201.5, 0.45, 34 + OCT, 0.92), (202.0, 1.85, 42 + OCT, 0.95)],
    ]
    for idx, sp in enumerate(diesis_spans):
        br = sp.bass_root()
        dyn = 0.80 + 0.04 * idx
        ob.string_swell(sp, vel=dyn * 0.85, include_9=(idx == 3))
        ob.piano_accompaniment(sp, vel=dyn * 0.86, style="storm", step_beats=0.5)
        ob.harp_gliss(sp, sp.start, pitch(C, 3), pitch(C, 6), vel=dyn * 0.92, spacing=0.12, note_dur=2.4, ascending=True, max_notes=11)
        ob.harp_gliss(sp, sp.start + 4.0, pitch(C, 3), pitch(C, 6), vel=dyn * 0.88, spacing=0.13, note_dur=2.4, ascending=False, max_notes=10)
        for q in range(8):
            ob.note("cello", sp.start + q, 0.78, br + OCT + (P5 if q % 2 == 1 else 0), dyn * (0.94 if q % 2 == 0 else 0.82))
        ob.note("bassoon", sp.start, 3.8, br, dyn * 0.94)
        ob.note("bassoon", sp.start + 4.0, 3.8, br, dyn * 0.95)
        hr = sp.tenor_root() + OCT
        ob.phrase("french_horn", [
            (sp.start, 1.35, hr, dyn * 0.92),
            (sp.start + 1.5, 0.45, hr + P5 if hr + P5 <= 42 else hr - P4, dyn * 0.94),
            (sp.start + 2.0, 1.80, hr, dyn * 0.92),
            (sp.start + 4.0, 3.80, hr, dyn * 0.95),
        ], snap_to_harmony=True)
        ob.phrase("clarinet", diesis_fanfares[idx])
        ob.phrase("english_horn", [(b, d, st - OCT if st > 50 else st, v * 0.90) for b, d, st, v in diesis_fanfares[idx]])
        ob.phrase("viola", [(b, d, st - OCT, v * 0.82) for b, d, st, v in diesis_fanfares[idx]])

    # --- III.C (204..224): Triple Downward Comma Cascade (+3 -> +2 -> +1 -> 0) ---
    for idx, sp in enumerate(m3_spans[10:]):
        c_group = idx // 4   # 0: +3->+2 surge, 1: +2->+1 woodwind canon, 2: +1->0 lyrical homecoming
        br = sp.bass_root()
        dur = sp.end - sp.start
        if c_group == 0:
            ob.string_swell(sp, vel=0.72, include_9=False, trim_tail=0.08)
            ob.piano_accompaniment(sp, vel=0.72, style="storm", step_beats=0.5)
            ob.note("bassoon", sp.start, dur - 0.08, br, 0.82)
            ob.note("cello", sp.start, dur - 0.08, br + OCT, 0.82)
            top_st = sp.nearest_step(pitch(A, 4, 3) - (idx % 4) * 4, allow_melody=False)
            ob.note("clarinet", sp.start, dur - 0.10, top_st + OCT if top_st < 35 else top_st, 0.86)
            ob.note("french_horn", sp.start, dur - 0.10, sp.nearest_step(pitch(C, 4, 3), allow_melody=False), 0.82)
        elif c_group == 1:
            # Transparent chamber canon (+2 -> +1)
            ob.piano_accompaniment(sp, vel=0.56, style="scherzo", step_beats=0.5)
            ob.note("pizzicato", sp.start, 0.45, br + OCT, 0.66)
            ob.note("bassoon", sp.start, dur - 0.10, br, 0.66)
            mel_st = sp.nearest_step(pitch(F, 4, 2) + ((idx % 4) % 2) * M3, allow_melody=False)
            ob.note("english_horn", sp.start, dur - 0.12, mel_st, 0.78)
            ob.note("viola", sp.start + 0.5, max(0.3, dur - 0.62), sp.nearest_step(mel_st - m3, allow_melody=False), 0.72)
        else:
            # Broadening glowing homecoming (+1 -> 0)
            ob.string_swell(sp, vel=0.56 + 0.04 * (idx % 4), include_9=(idx % 4 == 3), trim_tail=0.10)
            ob.piano_accompaniment(sp, vel=0.56, style="nocturne", step_beats=0.5)
            ob.note("bassoon", sp.start, dur - 0.12, br, 0.70)
            ob.note("cello", sp.start, dur - 0.12, br + OCT, 0.74)
            ob.harp_gliss(sp, sp.start, pitch(C, 3), pitch(A, 5), vel=0.68, spacing=0.16, note_dur=1.6, ascending=True, max_notes=7)
            lead_st = sp.nearest_step(pitch(G, 4, 1), allow_melody=False)
            ob.note("english_horn", sp.start, dur - 0.14, lead_st, 0.80)

    # =========================================================================
    # MOVEMENT IV: MAESTOSO & ADAGIO — "PASSACAGLIA & CATHEDRAL APOTHEOSIS" (224..296)
    #   Exact Home Comma Plane k = 0 (A4 = 39 = 440.00 Hz!)
    #   IV.A (224..248): Noble Brahmsian Passacaglia Cycle 1 (Cello Ground Bass + Winds/Strings; Organ SILENT!)
    #   IV.B (248..280): CATHEDRAL PIPE ORGAN ENTRANCE (~3:05) + Full Orchestral Recapitulation of Prisma Theme!
    #   IV.C (280..296): Serene Septimal Plagal Coda & Pure 4:5:6 F Major Whisper Fade
    # =========================================================================
    m4_chords = [
        # IV.A (224..248, k=0): Passacaglia Cycle 1 (6 bars x 4 beats = 24 beats, Organ SILENT)
        (224.0, 228.0, F, "add9", "IV.A1 Passacaglia I (F add9)"),
        (228.0, 232.0, C, "maj", "IV.A2 Passacaglia V (C maj)"),
        (232.0, 236.0, D_MINUS, "min7", "IV.A3 Passacaglia vi (Dm-7)"),
        (236.0, 240.0, BB, "maj9", "IV.A4 Passacaglia IV (Bb maj9)"),
        (240.0, 244.0, G_MINUS, "min7", "IV.A5 Passacaglia ii (Gm-7)"),
        (244.0, 248.0, C, "dom9", "IV.A6 Passacaglia V9(7:4)"),
        # IV.B (248..280, k=0): CATHEDRAL PIPE ORGAN ENTERS + Grand Symphonic Apotheosis!
        (248.0, 252.0, F, "add9", "IV.B1 Organ Entry pp: F add9 (Prisma Theme!)"),
        (252.0, 256.0, C, "dom9", "IV.B2 Organ mp: Septimal C dom9(7:4)"),
        (256.0, 260.0, D_MINUS, "min7", "IV.B3 Organ mf: Dm-7"),
        (260.0, 264.0, A, "min", "IV.B4 Organ mf+: Am(39,0,17)"),
        (264.0, 268.0, BB, "maj9", "IV.B5 Organ f: Bb maj9"),
        (268.0, 272.0, F, "maj", "IV.B6 Organ f: F maj"),
        (272.0, 276.0, C, "dom9", "IV.B7 Climax: C dom9(4:5:6:7:9)"),
        (276.0, 280.0, F, "add9", "IV.B8 Cathedral Apotheosis: F add9"),
        # IV.C (280..296, k=0): Transfigured Septimal Plagal Coda -> Pure 4:5:6 F Major Stillness
        (280.0, 285.0, BB, "maj9", "IV.C1 Plagal IV (Bb maj9 / F pedal)", F),
        (285.0, 290.0, F, "dom9", "IV.C2 Septimal Halo (F dom9 7:4 -> Bb? Wait: let's do Gm-7 -> F!)", F),
        (290.0, 296.0, F, "maj", "IV.C3 Final Pure 4:5:6 F Major Stillness (A4=440Hz)", F),
    ]
    # Make IV.C2 a tender pure minor-plagal / add9 halo over F pedal: Bb maj7/F -> F add9 -> Pure F maj!
    m4_chords[-2] = (285.0, 290.0, F, "add9", "IV.C2 Luminous F add9 Halo", F)
    m4_spans = [ob.add_span(*c) for c in m4_chords]

    # --- IV.A (224..248): Noble Brahmsian Passacaglia Cycle 1 (Organ SILENT!) ---
    for i, sp in enumerate(m4_spans[:6]):
        br = sp.bass_root()
        dyn = 0.54 + 0.03 * i
        # Singing Cello + Bassoon Passacaglia Ground Bass
        ob.note("bassoon", sp.start, 3.7, br, dyn + 0.08)
        ob.note("cello", sp.start, 1.85, br + OCT, dyn + 0.14)
        ob.note("cello", sp.start + 2.0, 1.80, br + OCT + P5, dyn + 0.10)
        ob.piano_accompaniment(sp, vel=dyn * 0.88, style="passacaglia", step_beats=0.5)
        if i >= 1:
            ob.string_swell(sp, vel=dyn * 0.80, include_9=True)
        if i in (0, 2, 4, 5):
            ob.harp_gliss(sp, sp.start, pitch(C, 3), pitch(C, 6), vel=dyn + 0.10, spacing=0.16, note_dur=2.2, ascending=(i % 2 == 0), max_notes=9)

    # Intertwining English Horn + Clarinet + Viola Passacaglia Variations in IV.A
    ob.phrase("english_horn", [
        (224.0, 1.8, pitch(A, 4), 0.74),
        (226.0, 1.8, pitch(G, 4), 0.72),
        (228.0, 1.8, pitch(E, 4), 0.74),
        (230.0, 1.8, pitch(G, 4), 0.78),
        (232.0, 1.8, pitch(F, 4), 0.78),
        (234.0, 1.8, pitch(A, 4), 0.82),
        (236.0, 1.8, pitch(D_MINUS, 5), 0.84),
        (238.0, 1.8, pitch(C, 5), 0.80),
        (240.0, 1.8, pitch(BB, 4), 0.80),
        (242.0, 1.8, pitch(G_MINUS, 4), 0.76),
        (244.0, 1.8, pitch(G, 4), 0.80),
        (246.0, 1.8, pitch(E, 4), 0.76),
    ], expressive_slide=16.0)
    ob.phrase("clarinet", [
        (228.5, 1.4, pitch(C, 5), 0.72),
        (230.2, 1.6, pitch(E, 5), 0.76),
        (232.5, 1.4, pitch(D_MINUS, 5), 0.76),
        (234.2, 1.6, pitch(C, 5), 0.74),
        (236.5, 1.4, pitch(F, 5), 0.80),
        (238.2, 1.6, pitch(D_MINUS, 5), 0.78),
        (240.5, 1.4, pitch(D_MINUS, 5), 0.78),
        (242.2, 1.6, pitch(BB, 4), 0.76),
        (244.5, 1.4, pitch(D, 5), 0.82),
        (246.2, 1.6, pitch(BB_HARM, 4), 0.80),
    ])

    # --- IV.B (248..280): CATHEDRAL PIPE ORGAN ENTRANCE + GRAND PRISMA APOTHEOSIS! ---
    organ_curve = [0.38, 0.48, 0.58, 0.68, 0.76, 0.82, 0.86, 0.90]
    for i, sp in enumerate(m4_spans[6:14]):
        br = sp.bass_root()
        ov = organ_curve[i]
        orch_v = 0.62 + 0.04 * i
        # Wide, beat-free 5-limit Cathedral Pipe Organ voicings (roots & octaves below C3, thirds above C4!)
        q_third = M3 if sp.quality in ("maj", "add9", "maj7", "maj9", "dom7", "dom9") else m3
        org_voicing = [br, br + OCT]
        if i >= 1:
            org_voicing.append(br + OCT + P5)
        if i >= 2:
            org_voicing.append(br + 2 * OCT + q_third)
        if i >= 4:
            org_voicing.append(br + 2 * OCT)
        ob.chord("church_organ", sp.start, 3.86, org_voicing, ov)

        ob.string_swell(sp, vel=orch_v * 0.86, include_9=True)
        ob.piano_accompaniment(sp, vel=orch_v * 0.80, style="passacaglia", step_beats=0.5)
        ob.harp_gliss(sp, sp.start, pitch(C, 3), pitch(C, 6), vel=orch_v * 0.90, spacing=0.14, note_dur=2.5, ascending=(i % 2 == 0), max_notes=11)
        ob.note("bassoon", sp.start, 3.7, br, orch_v * 0.88)
        ob.note("cello", sp.start, 1.85, br + OCT, orch_v * 0.92)
        ob.note("cello", sp.start + 2.0, 1.80, br + OCT + P5, orch_v * 0.88)

    # Full-Orchestra Thematic Apotheosis (Clarinet + English Horn + Viola + French Horn Counter-Anthem!)
    apotheosis_melody = [
        # Bar 248 (F add9): Prisma Theme rises in golden majesty!
        (248.0, 1.35, pitch(A, 4), 0.82),
        (249.5, 0.45, pitch(G, 4), 0.80),
        (250.0, 1.85, pitch(C, 5), 0.86),
        # Bar 252 (C dom9 7:4)
        (252.0, 1.35, pitch(BB_HARM, 4), 0.86),
        (253.5, 0.45, pitch(D, 5), 0.88),
        (254.0, 1.85, pitch(G, 4), 0.84),
        # Bar 256 (Dm-7)
        (256.0, 1.35, pitch(A, 4), 0.86),
        (257.5, 0.45, pitch(C, 5), 0.88),
        (258.0, 1.85, pitch(F, 5), 0.92),
        # Bar 260 (Am: 39, 0, 17)
        (260.0, 1.35, pitch(E, 5), 0.90),
        (261.5, 0.45, pitch(C, 5), 0.88),
        (262.0, 1.85, pitch(A, 4), 0.86),
        # Bar 264 (Bb maj9)
        (264.0, 1.35, pitch(D_MINUS, 5), 0.92),
        (265.5, 0.45, pitch(F, 5), 0.94),
        (266.0, 1.85, pitch(C, 5), 0.90),
        # Bar 268 (F maj)
        (268.0, 1.35, pitch(A, 4), 0.90),
        (269.5, 0.45, pitch(C, 5), 0.92),
        (270.0, 1.85, pitch(F, 5), 0.95),
        # Bar 272 (C dom9 4:5:6:7:9 Climax!)
        (272.0, 1.35, pitch(E, 5), 0.94),
        (273.5, 0.45, pitch(D, 5), 0.92),
        (274.0, 0.90, pitch(BB_HARM, 4), 0.92),
        (275.0, 0.90, pitch(G, 4), 0.90),
        # Bar 276 (F add9 Cathedral Crown!)
        (276.0, 3.80, pitch(A, 4), 0.95),          # Crowns on exact 440.00 Hz pure 5:4 major third!
    ]
    ob.phrase("clarinet", apotheosis_melody)
    ob.phrase("english_horn", [(b, d, st - OCT if st >= pitch(D_MINUS, 5) else st, v * 0.92) for b, d, st, v in apotheosis_melody])
    viola_apoth = []
    for b, d, st, v in apotheosis_melody:
        sp_at = ob.span_at(b)
        viola_apoth.append((b, d, sp_at.nearest_step(st - M3 - (OCT if st >= pitch(E, 5) else 0), allow_melody=False), v * 0.80))
    ob.phrase("viola", viola_apoth)

    ob.phrase("french_horn", [
        (248.0, 3.7, pitch(C, 4), 0.76),
        (252.0, 3.7, pitch(E, 4), 0.80),
        (256.0, 3.7, pitch(F, 4), 0.84),
        (260.0, 3.7, pitch(E, 4), 0.86),
        (264.0, 3.7, pitch(F, 4), 0.90),
        (268.0, 3.7, pitch(C, 4), 0.92),
        (272.0, 3.7, pitch(C, 4), 0.94),
        (276.0, 3.8, pitch(C, 4), 0.95),
    ])

    # --- IV.C (280..296): Serene Plagal Coda & Pure 4:5:6 F Major Stillness ---
    coda_spans = m4_spans[14:]
    coda_org = [0.64, 0.48, 0.34]
    coda_str = [0.60, 0.46, 0.34]
    for i, sp in enumerate(coda_spans):
        br = sp.bass_root()   # F2 pedal (-84) across all three coda bars!
        dur = sp.end - sp.start
        ov = coda_org[i]
        sv = coda_str[i]
        if i == 0:
            ob.chord("church_organ", sp.start, dur - 0.16, [br, br + OCT, pitch(D_MINUS, 4), pitch(A, 4)], ov)
        elif i == 1:
            ob.chord("church_organ", sp.start, dur - 0.16, [br, br + OCT, pitch(C, 4), pitch(G, 4), pitch(A, 4)], ov)
        else:
            # Final pure 4:5:6 F major cathedral chord centered on exact A4 = 440.00 Hz!
            ob.chord("church_organ", sp.start, dur - 0.50, [br, br + OCT, pitch(C, 4), pitch(A, 4), pitch(F, 5)], ov)

        ob.string_swell(sp, vel=sv, include_9=(i < 2), trim_tail=0.30)
        ob.note("bassoon", sp.start, dur - 0.35, br, sv * 0.90)
        ob.note("cello", sp.start, dur - 0.35, br + OCT, sv * 0.90)
        ob.harp_gliss(sp, sp.start + 0.3, pitch(F, 3), pitch(F, 6), vel=sv + 0.12, spacing=0.28, note_dur=3.6, ascending=True, max_notes=9)

    # Final tender English Horn & French Horn sigh + crystalline Piano bell echo
    ob.phrase("french_horn", [
        (280.0, 4.6, pitch(D_MINUS, 4), 0.62),
        (285.0, 4.6, pitch(C, 4), 0.50),
        (290.0, 5.4, pitch(A, 3), 0.38),
    ])
    ob.phrase("english_horn", [
        (280.5, 4.0, pitch(A, 4), 0.64),
        (285.5, 4.0, pitch(G, 4), 0.52),
        (290.2, 5.0, pitch(F, 4), 0.40),
    ])
    ob.phrase("piano", [
        (281.0, 1.8, pitch(F, 5), 0.56),
        (283.0, 1.8, pitch(D_MINUS, 5), 0.52),
        (286.0, 1.8, pitch(C, 5), 0.48),
        (288.0, 1.8, pitch(A, 4), 0.44),
        (290.5, 2.0, pitch(C, 5), 0.42),
        (292.8, 2.8, pitch(A, 4), 0.36),          # Last bell drop on exact 440.00 Hz pure third!
    ])

    score = ob.build_dict()
    return ob, score


# =============================================================================
# Strict Automated Harmonic, Register, Polyphony & Stage-Independence Validator
# =============================================================================
def validate_score(ob: OrchestraBuilder, score: Dict) -> None:
    errors: List[str] = []
    max_beat = 0.0
    organ_first_beat: Optional[float] = None

    # 1. Ensure pure stage-independence (no inline x/y/gain/warm_lowpass_hz)
    for forbidden in ("reverb_rt60", "tail_seconds"):
        if forbidden in score:
            errors.append(f"Top-level score should omit '{forbidden}' for pure stage-independence")

    for tr in score["tracks"]:
        tid = tr["id"]
        inst = tr["instrument"]
        for forbidden in ("x", "y", "gain", "warm_lowpass_hz"):
            if forbidden in tr:
                errors.append(f"Track '{tid}' should omit inline '{forbidden}'")

        events: List[Tuple[float, int]] = []
        for n in tr["notes"]:
            b0 = n["beat"]
            b1 = b0 + n["dur"]
            max_beat = max(max_beat, b1)
            events.append((b0, +1))
            events.append((b1, -1))

            if inst == "church_organ":
                if organ_first_beat is None or b0 < organ_first_beat:
                    organ_first_beat = b0
                if b0 < 245.0:
                    errors.append(f"church_organ entered too early at beat {b0:.2f}")

            if inst in WIND_INSTRUMENTS and not n.get("breath_swell", False):
                errors.append(f"Wind/brass track '{tid}' at beat {b0:.2f} missing breath_swell=True")

            strict = tid in STRICT_CHORD_TRACKS
            pc = n["step"] % OCT
            for sp in ob.grid:
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
            errors.append(f"Track '{tid}' exceeds 15-channel SF2 polyphony pool: peak={peak_poly}")

    # 2. Check zero close intervals (< P4 = 22 steps) below C3 (-53) across ALL tracks
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

    tail_s = 5.0  # stages/concert_hall.json tail_seconds
    total_sec = ob.tempo.beat_to_seconds(max_beat) + tail_s
    organ_sec = ob.tempo.beat_to_seconds(organ_first_beat) if organ_first_beat is not None else None
    if organ_sec is None:
        errors.append("church_organ has no notes!")

    if errors:
        print(f"VALIDATION FAILED with {len(errors)} error(s):")
        for e in errors[:30]:
            print("  -", e)
        raise SystemExit(1)

    print("VALIDATION PASSED (0 harmony clashes, 0 low-register mud, 0 polyphony overflows)!")
    print(f"Total Beats: {max_beat:.1f} | Concert Hall Duration: {total_sec:.2f}s ({int(total_sec // 60)}:{total_sec % 60:05.2f})")
    print("Section Timestamps:")
    for label, b in [
        ("I.   Adagio Sostenuto — Cradle of Pure Thirds (F maj, A4=440Hz)", 0.0),
        ("     -> Brahmsian Septimal Bloom (F dom9 7:4 -> Bb maj9)", 24.0),
        ("     -> Upward 5-Limit Syntonic Comma Lift (k=0 -> +1)", 48.0),
        ("II.  Allegretto Grazioso — Classical Scherzo (k=+1)", 72.0),
        ("     -> 4-Voice Orchestral Fugato (Clarinet/Viola/EngHorn/Cello)", 104.0),
        ("III. Allegro Appassionato — Tempest in D minor (k=+1)", 148.0),
        ("     -> Chromatic-Mediant Diesis Summit (+1 -> +3)", 172.0),
        ("     -> Triple Downward Comma Cascade (+3 -> 0)", 204.0),
        ("IV.  Maestoso Passacaglia (Home k=0)", 224.0),
        ("     -> Cathedral Pipe Organ Apotheosis", organ_first_beat or 248.0),
        ("     -> Serene Plagal Coda & Pure 4:5:6 F Major Stillness", 280.0),
    ]:
        t = ob.tempo.beat_to_seconds(b)
        print(f"  {label:<62} beat {b:5.1f}  @ {int(t // 60)}:{t % 60:05.2f}")
    print("Track Note Counts:")
    for tr in score["tracks"]:
        print(f"  {tr['id']:<18} ({tr['instrument']:<15}): {len(tr['notes']):4d} notes")


def main() -> None:
    ob, score = compose_orchestral_work()
    validate_score(ob, score)

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = os.path.join(repo_root, "scores", "orchestral_53edo.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(score, f, indent=2)
    print(f"Wrote {out_path} ({os.path.getsize(out_path) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
