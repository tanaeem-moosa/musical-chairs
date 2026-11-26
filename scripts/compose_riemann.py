#!/usr/bin/env python3
"""
Compose a monumental ~15-minute (900s) 4-movement 53-EDO orchestral symphony:
  "Ode to the Riemann Hypothesis — Symphony in 53-EDO"

Four Programmatic Movements:
  I.   The Primes (~3:45, 0:00–3:45, beats 0..264):
       Prime-limit harmonic awakening (2:1, 3:2, 5:4, 7:4, 11:8, 13:8, 17:16, 19:16),
       Sieve of Eratosthenes polyrhythmic/additive prime cells (2, 3, 5, 7 beat cycles
       & prime-indexed subdivisions), and the Euler Product orchestral convergence.
  II.  Analytic Continuation (~3:45, 3:45–7:30, beats 264..516):
       Crossing the divergence pole Re(s) = 1 via common-tone chromatic-mediant diesis
       rotations (0 -> 36 -> 19 -> 2) into the Critical Strip 0 < Re(s) < 1, centered on
       Riemann's symmetric functional equation xi(s) = xi(1 - s) realized as exact 53-EDO
       simultaneous mirror-inversion counterpoint & palindromic arch form, dissolving at
       the first nontrivial zero (t_1 ≈ 14.1347).
  III. A Century of Small Progress (~4:00, 7:30–11:30, beats 516..836):
       A 10-variation Brahmsian/Brucknerian Symphonic Passacaglia & 4-Voice Developing
       Fugato honoring Hadamard/de la Vallée Poussin, Hardy, Selberg, and Montgomery–
       Odlyzko pair correlation — climbing step-by-step across syntonic comma planes
       (k = 0 -> +1 -> +2 -> +3) with Beethovenian drive, sfz brass/timpani struggles,
       and subito piano setbacks, halting unresolved at k = +3 one step shy of truth.
  IV.  The Proof: AI & The Critical Line (~3:30, 11:30–15:00, beats 836..1100 + 5s tail):
       Rapid hyper-parallel algorithmic arpeggio & contrapuntal lattices scanning across
       comma planes until the hidden symmetry locks onto k = 0: the Prime Motif (Mvt I),
       Mirror Theme (Mvt II), and Passacaglia Pillar (Mvt III) unite simultaneously in a
       Cathedral Pipe Organ (church_organ) + full-orchestra Proof Apotheosis, dissolving
       into luminous beat-free 53-EDO stillness on the Critical Line Re(s) = 1/2.

Outputs: scores/riemann_hypothesis_15min.json (pure stage-independent score)
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

# =============================================================================
# 53-EDO Tuning & Prime-Harmonic Constants (C4 = 0, A4 = 39 = 440 Hz, OCT = 53)
# =============================================================================
OCT = 53
COMMA = 1        # 81:80 syntonic comma (~22.64c)
DIESIS = 2       # 128:125 enharmonic diesis (~45.28c)
SEMI = 5         # 16:15 diatonic semitone & 17:16 prime harmonic (113.21c)
m2_MINOR = 8     # 10:9 minor whole tone (181.13c)
M2 = 9           # 9:8 major whole tone (203.77c)
PRIME_19 = 13    # 19:16 19th-harmonic step (294.34c vs 297.51c, -3.17c)
m3 = 14          # 6:5 pure minor third (316.98c)
M3 = 17          # 5:4 pure major third — Prime 5! (384.91c)
P4 = 22          # 4:3 pure fourth (498.11c)
PRIME_11 = 24    # 11:8 11th-harmonic — Prime 11! (543.40c)
P5 = 31          # 3:2 pure fifth — Prime 3! (701.89c)
m6 = 36          # 8:5 pure minor sixth (815.09c)
PRIME_13 = 37    # 13:8 13th-harmonic — Prime 13! (837.74c vs 840.53c, -2.79c)
M6 = 39          # 5:3 pure major sixth (883.02c; A4 = 440.00 Hz)
HARM_7 = 43      # 7:4 septimal seventh — Prime 7! (973.58c)
JUST_m7 = 45     # 9:5 pure minor seventh (1018.87c)
M7 = 48          # 15:8 pure major seventh (1086.79c)

# Reference pitch classes on Home Comma Plane k = 0
C = 0
D_MINUS = 8
D = 9
EB = 14
E = 17
F = 22
G = 31
AB = 36
A = 39
BB_HARM = 43
BB = 44
B = 48

PRIMES_UP_TO_60 = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59]
PRIME_SET = set(PRIMES_UP_TO_60)

WIND_BRASS = {"clarinet", "english_horn", "bassoon", "french_horn", "trombone"}
STRICT_CHORD_TRACKS = {
    "harp",
    "pizzicato",
    "string_ensemble",
    "tremolo_strings",
    "bassoon",
    "trombone",
    "church_organ",
}


def pitch(pc: int, octave: int, k: int = 0) -> int:
    """Exact 53-EDO step for pitch class `pc` in `octave` (C4 = 0) + syntonic comma shift `k`."""
    return pc + (octave - 4) * OCT + k


def mod53_dist(a: int, b: int) -> int:
    d = (a - b) % OCT
    return min(d, OCT - d)


# =============================================================================
# Pure 5/7/11/13-Limit & Mirror-Symmetric Chord Templates (min mod53 dist >= 4!)
# =============================================================================
CHORD_TEMPLATES: Dict[str, Tuple[int, ...]] = {
    "open5": (0, P5),
    "maj": (0, M3, P5),
    "add9": (0, M2, M3, P5),
    "maj7": (0, M3, P5, M7),
    "maj9": (0, M2, M3, P5, M7),
    "mirror_maj": (0, M2, M3, P5, M6, M7),       # Self-dual under x -> 2R + 48 - x!
    "min": (0, m3, P5),
    "min7": (0, m3, P5, JUST_m7),
    "min9": (0, M2, m3, P5, JUST_m7),
    "mirror_min": (0, M2, m3, P5, m6, JUST_m7),  # Self-dual under x -> 2R + 45 - x!
    "dom7": (0, M3, P5, HARM_7),
    "dom9": (0, M2, M3, P5, HARM_7),
    "sus2": (0, M2, P5),
    "sus4": (0, P4, P5),
    "prime7": (0, M3, P5, HARM_7),
    "prime11": (0, M3, PRIME_11, P5, HARM_7),
    "prime13": (0, M3, PRIME_11, P5, PRIME_13, HARM_7),
    "prime17_19": (0, SEMI, PRIME_19, M3, PRIME_11, P5, PRIME_13, HARM_7),
}

MELODY_EXTRA: Dict[str, Tuple[int, ...]] = {
    "open5": (M2, M3, M6),
    "maj": (M2, P4, M6, M7),
    "add9": (P4, M6, M7),
    "maj7": (M2, P4, M6),
    "maj9": (P4, M6),
    "mirror_maj": (),
    "min": (M2, P4, m6, JUST_m7),
    "min7": (M2, P4, m6),
    "min9": (P4, m6),
    "mirror_min": (),
    "dom7": (M2, M6),
    "dom9": (M6,),
    "sus2": (M3, P4, M6),
    "sus4": (M2, M6, M7),
    "prime7": (M2, M6),
    "prime11": (M2, M6),
    "prime13": (M2,),
    "prime17_19": (M2,),
}


@dataclass
class ChordSpan:
    start: float
    end: float
    root_pc: int
    quality: str
    label: str = ""
    pedal_pc: Optional[int] = None

    def __post_init__(self) -> None:
        self.root_pc = self.root_pc % OCT
        if self.pedal_pc is not None:
            self.pedal_pc = self.pedal_pc % OCT
        pcs = sorted(self.melody_pcs)
        for i, a in enumerate(pcs):
            for b in pcs[i + 1 :]:
                d = mod53_dist(a, b)
                if 0 < d <= 3:
                    raise ValueError(
                        f"ChordSpan {self.label} ({self.root_pc} {self.quality}) has internal "
                        f"comma clash {a} vs {b} (dist={d})"
                    )

    @property
    def chord_pcs(self) -> Set[int]:
        s = {(self.root_pc + iv) % OCT for iv in CHORD_TEMPLATES[self.quality]}
        if self.pedal_pc is not None:
            s.add(self.pedal_pc)
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
        for d in range(-27, 28):
            cand = target_step + d
            if (cand % OCT) in pcs and abs(d) < best_dist:
                best_dist = abs(d)
                best = cand
        return best

    def bass_root(self, low: int = -106, high: int = -55) -> int:
        """Warm C2..B2 bass root (< -53)."""
        pc = self.pedal_pc if self.pedal_pc is not None else self.root_pc
        st = pc - 2 * OCT
        while st < low:
            st += OCT
        while st > high:
            st -= OCT
        return st

    def tenor_root(self) -> int:
        """Clean C3..B3 root (-53..-1) so all chord intervals above sit >= C3."""
        r = self.root_pc - OCT
        while r < -53:
            r += OCT
        while r > -1:
            r -= OCT
        return r

    def open_voicing(self, include_ext: bool = True) -> List[int]:
        """Wide beat-free string/brass voicing strictly >= C3 (-53) with zero narrow cluster intervals."""
        r = self.tenor_root()
        q = self.quality
        if q == "open5":
            return [r, r + P5, r + OCT]
        if q in ("min", "min7", "min9", "mirror_min"):
            if include_ext and q == "min9":
                # Exact SCORE_FORMAT.md §3 pure minor 9th [0, 14, 31, 45, 62] (zero narrow seconds!)
                return [r, r + m3, r + P5, r + JUST_m7, r + OCT + M2]
            v = [r, r + P5, r + OCT + m3]
            if include_ext and q in ("min7", "mirror_min"):
                v.insert(2, r + JUST_m7)
            return sorted(v)
        if q == "sus4":
            return [r, r + P5, r + OCT + P4]
        if q == "sus2":
            return [r, r + P5, r + OCT + M2]
        if q in ("dom7", "dom9", "prime7", "prime11", "prime13", "prime17_19"):
            v = [r, r + P5, r + HARM_7, r + OCT + M3]
            if include_ext and q == "dom9":
                v.append(r + OCT + M2)
            elif include_ext and q in ("prime11", "prime13", "prime17_19"):
                v.append(r + OCT + PRIME_11)
            return sorted(v)
        # Major / add9 / maj7 / maj9 / mirror_maj: omit M7 in dense orchestral pads when include_ext=False,
        # and voice maj9/add9 as open [r, r+P5, r+OCT+M2, r+OCT+M3] (16 steps = minor 3rd? wait: M3-M2 = 8 steps = 181c,
        # or even cleaner: [r, r+M3, r+P5, r+OCT+M2] where every adjacent interval >= 14 steps!)
        if include_ext and q in ("add9", "maj9"):
            return [r, r + M3, r + P5, r + OCT + M2]
        if include_ext and q in ("maj7", "mirror_maj"):
            return [r, r + M3, r + P5, r + M7]
        return [r, r + P5, r + OCT + M3]

    def scale_steps(self, low_step: int, high_step: int, allow_melody: bool = False) -> List[int]:
        pcs = self.melody_pcs if allow_melody else self.chord_pcs
        return [s for s in range(low_step, high_step + 1) if (s % OCT) in pcs]

    def mirror_sum(self, center_oct: int = 4) -> int:
        """Exact pitch-reflection sum S around Middle C such that u in [C4..B4] <-> S-u in [G2..C4]!"""
        r = self.root_pc + (center_oct - 4) * OCT
        while r > 26:
            r -= OCT
        while r < -26:
            r += OCT
        s = (2 * r + JUST_m7 - OCT) if self.quality in ("min", "min7", "min9", "mirror_min") else (2 * r + M7 - OCT)
        while s > 24:
            s -= OCT
        while s < -28:
            s += OCT
        return s


# =============================================================================
# Analytical TempoMap (exact match to Rust src/score.rs)
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


@dataclass
class TrackSpec:
    id: str
    name: str
    instrument: str
    notes: List[Dict] = field(default_factory=list)
    pedals: List[Dict[str, float]] = field(default_factory=list)


# =============================================================================
# Stage-Independent Orchestral Symphony Builder
# =============================================================================
class RiemannSymphonyBuilder:
    def __init__(self, tempo_segments: List[Tuple[float, float]]):
        self.tempo = TempoMap(tempo_segments)
        self.grid: List[ChordSpan] = []
        self.sections: List[Dict] = []
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
            TrackSpec("tremolo_strings", "Tremolo Strings", "tremolo_strings"),
            TrackSpec("clarinet", "Solo Clarinet", "clarinet"),
            TrackSpec("english_horn", "English Horn", "english_horn"),
            TrackSpec("bassoon", "Solo Bassoon", "bassoon"),
            TrackSpec("french_horn", "French Horns", "french_horn"),
            TrackSpec("trombone", "Symphonic Trombones", "trombone"),
            TrackSpec("timpani", "53-EDO Timpani", "timpani"),
            TrackSpec("church_organ", "Cathedral Pipe Organ", "church_organ"),
        ]
        for s in specs:
            self.tracks[s.id] = s

    def add_section(self, beat: float, title: str) -> None:
        self.sections.append({"beat": round(beat, 3), "title": title})

    def add_span(
        self,
        start: float,
        end: float,
        root_pc: int,
        quality: str,
        label: str = "",
        pedal_pc: Optional[int] = None,
    ) -> ChordSpan:
        sp = ChordSpan(
            start=start,
            end=end,
            root_pc=root_pc,
            quality=quality,
            label=label,
            pedal_pc=pedal_pc,
        )
        self.grid.append(sp)
        return sp

    def span_at(self, beat: float) -> ChordSpan:
        # Binary search over sorted grid
        lo, hi = 0, len(self.grid) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            sp = self.grid[mid]
            if beat < sp.start - 1e-6:
                hi = mid - 1
            elif beat >= sp.end - 1e-6:
                lo = mid + 1
            else:
                return sp
        return self.grid[max(0, min(len(self.grid) - 1, lo))]

    def add_pedal(self, start: float, dur: float, track_id: str = "piano") -> None:
        if dur > 0.15:
            self.tracks[track_id].pedals.append(
                {"beat": round(start, 4), "dur": round(dur, 4)}
            )

    def _safe_dur(self, track_id: str, beat: float, dur: float, step: int) -> float:
        """Guarantees zero cross-span comma clashes and zero <C3 low-register mud."""
        if track_id == "timpani":
            return max(0.08, dur)
        end = beat + dur
        pc = step % OCT
        strict = track_id in STRICT_CHORD_TRACKS
        is_low = step < -OCT
        cur_sp = self.span_at(beat)
        cur_bass = cur_sp.bass_root()

        for sp in self.grid:
            if sp.end <= beat + 1e-6:
                continue
            if sp.start >= end - 1e-6:
                break
            if sp.start > beat + 1e-6:
                allowed = sp.chord_pcs if strict else sp.melody_pcs
                clash_any = any(0 < mod53_dist(pc, apc) <= 3 for apc in sp.melody_pcs)
                if (pc not in allowed) or clash_any:
                    end = min(end, sp.start - 0.08)
                    break
                if is_low and sp.bass_root() != cur_bass:
                    diff = abs(sp.bass_root() - step)
                    if 0 < diff < P4:
                        end = min(end, sp.start - 0.14)
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
        swell: Optional[str] = None,
        vibrato: float = 0.0,
        snap_to_harmony: bool = False,
        allow_melody: Optional[bool] = None,
        trim: bool = True,
    ) -> None:
        tr = self.tracks[track_id]
        strict = track_id in STRICT_CHORD_TRACKS
        if allow_melody is None:
            allow_melody = not strict

        sp = self.span_at(beat)
        if snap_to_harmony and track_id != "timpani":
            step = sp.nearest_step(step, allow_melody=allow_melody)

        # Sweet-spot register guardrails per instrument (preserving exact pitch class mod 53!)
        sweet_high = {
            "english_horn": 53,
            "clarinet": 70,
            "viola": 53,
            "cello": 24,
            "french_horn": 31,
            "trombone": 0,
            "bassoon": 0,
            "church_organ": 53,
            "harp": 106,
            "piano": 92,
            "pizzicato": 70,
        }
        sweet_low = {
            "trombone": -89,
            "french_horn": -67,
            "english_horn": -31,
            "clarinet": -36,
            "viola": -53,
            "pizzicato": -53,
            "harp": -53,
            "cello": -106,
            "bassoon": -106,
            "church_organ": -106,
            "piano": -106,
        }
        if track_id in sweet_high:
            hi_lim = sweet_high[track_id]
            while step > hi_lim:
                step -= OCT
        if track_id in sweet_low:
            lo_lim = sweet_low[track_id]
            while step < lo_lim:
                step += OCT

        # Protect <C3 register against mud on non-percussive tracks
        if track_id != "timpani" and step < -OCT:
            br = sp.bass_root()
            diff = abs(step - br)
            if 0 < diff < P4:
                # Snap cleanly to exact bass_root (if >= sweet_low) or +OCT (>= -53)
                lo_ok = sweet_low.get(track_id, -106)
                if track_id in ("bassoon", "trombone", "church_organ") and br >= lo_ok:
                    step = br
                else:
                    step += OCT

        if trim:
            dur = self._safe_dur(track_id, beat, dur, step)

        if swell is None and tr.instrument in WIND_BRASS and dur >= 0.45:
            swell = "arch"

        # Musical dynamic floor calibration: keeps pp chamber passages warm & audible
        # while landing LRA comfortably around ~11.5-12.4 LU (strictly inside 7..14 LU)!
        v_raw = max(0.20, min(0.96, float(vel)))
        v = 0.52 + 0.38 * (((v_raw - 0.20) / 0.76) ** 0.84)
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
        if swell is not None and swell != "none":
            entry["swell"] = swell
        if vibrato > 1e-3:
            entry["vibrato"] = round(min(0.65, vibrato), 3)
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
    ) -> None:
        n = len(steps)
        for i, st in enumerate(steps):
            w = 1.0 if i in (0, n - 1) else 0.90
            self.note(
                track_id,
                beat + i * roll,
                max(0.12, dur - i * roll),
                st,
                vel * w,
                swell=swell,
            )

    def phrase(
        self,
        track_id: str,
        events: Sequence[Tuple[float, float, int, float]],
        *,
        swell: Optional[str] = None,
        vibrato: float = 0.0,
        slide_cents: float = 0.0,
        snap: bool = True,
        allow_melody: bool = True,
    ) -> None:
        n = len(events)
        for i, (b, d, st, v) in enumerate(events):
            u = i / max(1, n - 1) if n > 1 else 0.5
            arch = 0.93 + 0.12 * math.sin(math.pi * (u ** 0.85))
            sl = 0.0
            if slide_cents > 0.0 and i > 0 and d >= 0.75:
                pb, pd, pst, _ = events[i - 1]
                diff = st - pst
                if 5 <= abs(diff) <= 24 and (b - (pb + pd)) <= 0.30:
                    sl = -slide_cents if diff > 0 else slide_cents * 0.85
            vib = vibrato if d >= 0.85 else (vibrato * 0.45 if d >= 0.55 else 0.0)
            sw = swell
            if sw is None:
                if i == n - 1 and d >= 1.5:
                    sw = "dim"
                elif track_id in WIND_BRASS or d >= 1.1:
                    sw = "arch"
            self.note(
                track_id,
                b,
                d,
                st,
                v * arch,
                slide_from_cents=sl,
                swell=sw,
                vibrato=vib,
                snap_to_harmony=snap,
                allow_melody=allow_melody,
            )

    def string_pad(
        self,
        span: ChordSpan,
        vel: float,
        *,
        track_id: str = "string_ensemble",
        swell: str = "arch",
        include_ext: bool = True,
        trim_tail: float = 0.14,
    ) -> None:
        voicing = span.open_voicing(include_ext=include_ext)
        dur = max(0.30, (span.end - span.start) - trim_tail)
        self.chord(track_id, span.start, dur, voicing, vel, swell=swell)

    def harp_arp(
        self,
        span: ChordSpan,
        beat: float,
        low_step: int,
        high_step: int,
        vel: float,
        *,
        spacing: float = 0.18,
        note_dur: float = 1.6,
        ascending: bool = True,
        max_notes: int = 8,
        zig_zag: bool = False,
    ) -> None:
        pts_raw = span.scale_steps(max(-53, low_step), min(106, high_step), allow_melody=False)
        # On sustained harp sweeps (note_dur >= 1.0b), avoid M7 (5 steps below root) and M2/m6 on minor
        # (5 steps from m3/P5) so long ringing harp strings never form minor-second grinds against pads/organ!
        if note_dur >= 1.0:
            r_pc = span.root_pc
            avoid_pcs: Set[int] = set()
            if span.quality in ("maj7", "maj9", "mirror_maj"):
                avoid_pcs.add((r_pc + M7) % OCT)
            if span.quality in ("min9", "mirror_min"):
                avoid_pcs.add((r_pc + M2) % OCT)
                avoid_pcs.add((r_pc + m6) % OCT)
            pts_raw = [s for s in pts_raw if (s % OCT) not in avoid_pcs]
        pts: List[int] = []
        for s in pts_raw:
            if not pts or abs(s - pts[-1]) >= 8:
                pts.append(s)
        if not pts:
            return
        if len(pts) > max_notes:
            pts = [
                pts[int(round(i * (len(pts) - 1) / max(1, max_notes - 1)))]
                for i in range(max_notes)
            ]
        if not ascending:
            pts = list(reversed(pts))
        if zig_zag and len(pts) >= 4:
            zig = []
            for i in range(len(pts) - 1):
                zig.append(pts[i])
                if i % 2 == 1 and i + 1 < len(pts):
                    zig.append(pts[i - 1])
            zig.append(pts[-1])
            pts = zig[:max_notes]
        n = len(pts)
        for i, st in enumerate(pts):
            t = beat + i * spacing
            if t >= span.end - 0.12:
                break
            u = i / max(1, n - 1)
            shape = 0.92 + 0.16 * math.sin(math.pi * u)
            nd = min(note_dur, span.end - t - 0.08)
            self.note("harp", t, nd, st, vel * shape, snap_to_harmony=False)

    def timpani_roll(
        self,
        beat: float,
        dur: float,
        step: int,
        vel_start: float,
        vel_end: float,
        subdiv: float = 0.25,
    ) -> None:
        steps_n = max(1, int(round(dur / subdiv)))
        for i in range(steps_n):
            u = i / max(1, steps_n - 1)
            v = vel_start + (vel_end - vel_start) * (u ** 0.9)
            accent = 1.06 if i in (0, steps_n - 1) else (0.94 + 0.05 * (i % 2))
            self.note("timpani", beat + i * subdiv, subdiv * 0.92, step, v * accent, trim=False)

    def build_dict(self) -> Dict:
        tracks_json = []
        for tr in self.tracks.values():
            # Final safety pass on durations and sorting
            cleaned_notes = []
            for n in tr.notes:
                n["dur"] = round(
                    self._safe_dur(tr.id, n["beat"], n["dur"], n["step"]), 4
                )
                cleaned_notes.append(n)
            cleaned_notes.sort(key=lambda x: (x["beat"], x["step"]))

            # Ensure natural human section-wide breathing rests (>= 0.80 beats at least every <= 14.5 beats)
            # across ALL wind & brass tracks, even when multi-voice brass chords are staggered!
            if tr.instrument in WIND_BRASS and cleaned_notes:
                for _pass in range(64):
                    ivs = sorted((n["beat"], n["beat"] + n["dur"]) for n in cleaned_notes)
                    merged: List[Tuple[float, float]] = []
                    for b0, e0 in ivs:
                        if merged and b0 - merged[-1][1] < 0.75:
                            merged[-1] = (merged[-1][0], max(merged[-1][1], e0))
                        else:
                            merged.append((b0, e0))
                    over = [(b0, e0) for b0, e0 in merged if (e0 - b0) > 15.0]
                    if not over:
                        break
                    mb0, me0 = over[0]
                    target_cut = mb0 + 12.0
                    # Find cleanest note-onset boundary in [mb0 + 7.5 .. mb0 + 15.0]
                    onsets = sorted({
                        n["beat"] for n in cleaned_notes
                        if mb0 + 7.5 <= n["beat"] <= mb0 + 15.0
                    })
                    cut_b = min(onsets, key=lambda x: abs(x - target_cut)) if onsets else round(target_cut)
                    breath_end = cut_b - 0.85
                    changed = False
                    for n in cleaned_notes:
                        nb = n["beat"]
                        ne = nb + n["dur"]
                        if nb < cut_b - 0.05 and ne > breath_end:
                            new_d = max(0.35, breath_end - nb)
                            if new_d < n["dur"] - 1e-4:
                                n["dur"] = round(new_d, 4)
                                if n.get("swell") in (None, "arch"):
                                    n["swell"] = "dim"
                                changed = True
                    if not changed:
                        # Long single held note > 15 beats: split/trim cleanly at mb0 + 13.5
                        for n in cleaned_notes:
                            if n["beat"] <= mb0 + 13.5 < n["beat"] + n["dur"]:
                                n["dur"] = round(max(0.5, (mb0 + 13.5) - n["beat"]), 4)
                                n["swell"] = "dim"
                                changed = True
                        if not changed:
                            break

            t_obj: Dict = {
                "id": tr.id,
                "name": tr.name,
                "instrument": tr.instrument,
                "notes": cleaned_notes,
            }
            if tr.pedals:
                t_obj["pedals"] = sorted(tr.pedals, key=lambda p: p["beat"])
            tracks_json.append(t_obj)

        # Orchestral Transparency Pass: if a background pad voice in string_ensemble/tremolo_strings
        # sustains within 1..6 steps (minor/major 2nd in the same octave) for >= 0.95 beats against any
        # solo wind/string/brass/organ note, drop that redundant inner pad voice so soloists shine cleanly!
        fg_notes: List[Tuple[float, float, int]] = []
        for t_obj in tracks_json:
            if t_obj["id"] in ("clarinet", "english_horn", "viola", "cello", "french_horn", "trombone", "church_organ", "piano"):
                for n in t_obj["notes"]:
                    fg_notes.append((n["beat"], n["beat"] + n["dur"], n["step"]))
        fg_notes.sort()

        for t_obj in tracks_json:
            if t_obj["id"] in ("string_ensemble", "tremolo_strings"):
                kept = []
                for n in t_obj["notes"]:
                    b0, e0, st0 = n["beat"], n["beat"] + n["dur"], n["step"]
                    clash = False
                    for fb, fe, fst in fg_notes:
                        if fb >= e0 - 0.95:
                            break
                        if min(e0, fe) - max(b0, fb) >= 0.95 and 0 < abs(st0 - fst) <= 6:
                            clash = True
                            break
                    if not clash:
                        kept.append(n)
                t_obj["notes"] = kept

        return {
            "title": "Ode to the Riemann Hypothesis — Symphony in 53-EDO",
            "description": (
                "A monumental ~15-minute (900s) stage-independent 4-movement 53-EDO orchestral symphony "
                "tracing the mathematical epic of the Riemann Hypothesis: I. The Primes (prime-limit "
                "harmonics 2,3,5,7,11,13,17,19, Sieve of Eratosthenes polyrhythms & Euler Product); "
                "II. Analytic Continuation (Re(s)=1 divergence wall, chromatic-mediant diesis rotations, "
                "exact xi(s)=xi(1-s) simultaneous mirror-inversion counterpoint & palindromic arch, first "
                "nontrivial zero); III. A Century of Small Progress (10-variation Brahmsian/Brucknerian "
                "Passacaglia & 4-voice Fugato climbing k=0->+1->+2->+3 to an unresolved summit); IV. The "
                "Proof: AI & The Critical Line (hyper-parallel algorithmic lattice locking onto k=0 in a "
                "Cathedral Pipe Organ + full-orchestra triple-theme Proof Apotheosis & Critical Line stillness)."
            ),
            "sample_rate": 48000,
            "sections": sorted(self.sections, key=lambda s: s["beat"]),
            "tempo": self.tempo.to_json(),
            "tracks": tracks_json,
        }


# =============================================================================
# MOVEMENT I — THE PRIMES (Beats 0..264, 0:00 – 3:45)
# =============================================================================
def compose_movement_1(sb: RiemannSymphonyBuilder) -> None:
    sb.add_section(0.0, "I. The Primes — 1. Genesis of Irreducible Harmonics (2, 3, 5, 7)")
    sb.add_section(60.0, "I.2 Sieve of Eratosthenes & Higher Prime Harmonics (11, 13, 17, 19)")
    sb.add_section(132.0, "I.3 The Euler Product — Orchestral Prime Convergence")
    sb.add_section(204.0, "I.4 Asymptotic Mystery (x / ln x) & Approach to Re(s) = 1")

    m1_specs = [
        # I.1 (0..60): Awakening of Primes 2 (2:1), 3 (3:2), 5 (5:4), 7 (7:4)
        (0.0, 8.0, C, "open5", "I.1a Prime 2 & 3 Awakening (C open5)"),
        (8.0, 16.0, C, "maj", "I.1b Prime 5Pure Third (C 4:5:6)"),
        (16.0, 24.0, G, "maj", "I.1c Fifth Expansion (G maj)"),
        (24.0, 32.0, C, "add9", "I.1d 9:8 & 5:4 Bloom (C add9)"),
        (32.0, 40.0, F, "maj9", "I.1e Subdominant Glow (F maj9)"),
        (40.0, 48.0, C, "prime7", "I.1f Prime 7 Septimal Awakening (C 4:5:6:7)"),
        (48.0, 54.0, G, "dom9", "I.1g Septimal Dominant (G dom9)"),
        (54.0, 60.0, C, "add9", "I.1h Prime Cadence (C add9)"),
        # I.2 (60..132): Sieve of Eratosthenes Polyrhythms & Primes 11, 13, 17, 19
        (60.0, 68.0, C, "prime11", "I.2a Prime 11 Harmonic (11:8 = +24)"),
        (68.0, 76.0, G, "prime11", "I.2b G Prime-11 Spectrum"),
        (76.0, 84.0, C, "prime13", "I.2c Prime 13 Harmonic (13:8 = +37)"),
        (84.0, 92.0, F, "prime13", "I.2d F Prime-13 Spectrum"),
        (92.0, 100.0, C, "prime17_19", "I.2e Primes 17 & 19 Full Overtone Sieve"),
        (100.0, 108.0, A, "min9", "I.2f Sieve Counterpoint Am9"),
        (108.0, 116.0, D, "dom9", "I.2g Sieve Counterpoint D dom9"),
        (116.0, 124.0, G, "dom9", "I.2h Sieve Dominant G dom9"),
        (124.0, 132.0, C, "maj9", "I.2i Shimmering Prime Lattice C maj9"),
        # I.3 (132..204): The Euler Product — Full Orchestral Convergence + Comma Lift & Return
        (132.0, 140.0, C, "add9", "I.3a Euler Product Surge I (C add9)"),
        (140.0, 148.0, E, "min7", "I.3b Mediant Stream iii (Em7)"),
        (148.0, 156.0, A, "min9", "I.3c Relative Stream vi (Am9)"),
        (156.0, 164.0, F, "maj9", "I.3d Subdominant Stream IV (F maj9)"),
        (164.0, 168.0, C, "maj", "I.3e Comma Lift I(0)"),
        (168.0, 172.0, G, "maj", "I.3f Comma Lift V(31)"),
        (172.0, 176.0, D, "min7", "I.3g Comma Lift ii(9)"),
        (176.0, 180.0, F + 1, "maj9", "I.3h Comma Lift IV+(23)"),
        (180.0, 184.0, G + 1, "dom9", "I.3i Comma Lift V9+(32)"),
        (184.0, 192.0, C + 1, "add9", "I.3j Euler Crest on k=+1 (C+ add9)"),
        (192.0, 196.0, F + 1, "maj", "I.3k Comma Return IV+(23)"),
        (196.0, 200.0, D, "min7", "I.3l Comma Return ii(9)"),
        (200.0, 204.0, G, "dom9", "I.3m Comma Return V9(31 -> k=0)"),
        # I.4 (204..264): Asymptotic Thinning (pi(x) ~ x / ln x) & Approach to Re(s) = 1
        (204.0, 212.0, C, "maj9", "I.4a Post-Climax Glow (C maj9)"),
        (212.0, 220.0, A, "min9", "I.4b Thinning Primes (Am9)"),
        (220.0, 228.0, F, "maj7", "I.4c Logarithmic Drift (F maj7)"),
        (228.0, 236.0, D_MINUS, "min7", "I.4d Solitary Prime Echoes (Dm-7)"),
        (236.0, 244.0, G, "sus4", "I.4e Horizon Mist (G sus4)"),
        (244.0, 254.0, G, "dom7", "I.4f Septimal Shadow (G dom7)"),
        (254.0, 264.0, E, "dom7", "I.4g Portal to the Pole Re(s)=1 (E dom7)"),
    ]
    spans = [sb.add_span(*c) for c in m1_specs]

    # --- I.1 (0..60): Hushed Genesis of Primes 2, 3, 5, 7 (ppp -> mp) ---
    # Prime 2 (2-beat cycle on piano/harp octaves) + Prime 3 (3-beat pizzicato fifths) + Prime 5 (5-beat clarinet/cello)
    sb.add_pedal(0.0, 7.8)
    sb.add_pedal(8.0, 7.8)
    sb.add_pedal(24.0, 7.8)
    sb.add_pedal(32.0, 7.8)
    sb.add_pedal(40.0, 7.8)

    # Bar 0..8: Solitary C4=0 unity & 2:1 octaves + 3:2 fifths emerging from silence (ppp -> pp)
    genesis_piano = [
        (0.0, 1.8, pitch(C, 4), 0.25),
        (2.0, 1.8, pitch(C, 5), 0.28),
        (4.0, 1.8, pitch(C, 3), 0.30),
        (6.0, 1.8, pitch(G, 4), 0.33),  # Prime 3 (3:2 = 31) enters!
        (8.0, 1.8, pitch(C, 4), 0.35),
        (10.0, 1.8, pitch(E, 4), 0.38),  # Prime 5 (5:4 = 17) enters!
        (12.0, 1.8, pitch(G, 4), 0.40),
        (14.0, 1.8, pitch(E, 5), 0.42),
    ]
    for b, d, st, v in genesis_piano:
        sb.note("piano", b, d, st, v, snap_to_harmony=False)

    # Warm hushed Viola + String Ensemble harmonic cradle in I.1 so opening primes glow in the hall
    for sp_g in spans[:4]:
        sb.string_pad(sp_g, vel=0.32, swell="arch", include_ext=False)

    # Prime-3 (every 3 beats) pizzicato pulse vs Prime-2 harp harmonics across 3..32
    t3 = 3.0
    idx3 = 0
    while t3 < 31.5:
        sp = sb.span_at(t3)
        r3 = sp.tenor_root()
        st3 = r3 + (P5 if idx3 % 2 == 0 else OCT)
        sb.note("pizzicato", t3, 0.55, st3, 0.30 + 0.015 * idx3, snap_to_harmony=False)
        t3 += 3.0
        idx3 += 1

    for sp_i, sp in enumerate(spans[:8]):
        if sp_i >= 1:
            sb.harp_arp(
                sp,
                sp.start + 0.5,
                pitch(C, 3),
                pitch(G, 5),
                vel=0.32 + 0.03 * sp_i,
                spacing=0.35 - 0.02 * min(4, sp_i),
                note_dur=2.2,
                ascending=(sp_i % 2 == 0),
                max_notes=5 + (sp_i % 4),
            )
        if sp_i >= 4:
            sb.note("bassoon", sp.start, (sp.end - sp.start) - 0.5, sp.bass_root(), 0.36 + 0.03 * (sp_i - 4), swell="arch")

    # Clarinet & Cello introduce the PRIME MOTIF: rising [1:1, 5:4, 3:2, 7:4, 2:1] in 5-beat & 7-beat cells!
    sb.phrase("cello", [
        (9.0, 2.6, pitch(C, 3), 0.34),
        (12.0, 3.4, pitch(G, 3), 0.38),
        (16.5, 2.2, pitch(G, 3), 0.40),
        (19.0, 2.2, pitch(B, 3), 0.42),
        (21.5, 2.1, pitch(D, 4), 0.44),
        # Breath 23.6..25.0
        (25.0, 2.8, pitch(C, 3), 0.42),
        (28.0, 3.6, pitch(E, 3), 0.45),
        (32.5, 3.2, pitch(F, 3), 0.48),
        (36.0, 3.5, pitch(A, 3), 0.50),
        # Prime 7 (40..48): deep C3 root grounding the septimal 7:4 chord
        (40.0, 3.6, pitch(C, 3), 0.50),
        (44.0, 3.6, pitch(G, 3), 0.48),
        (48.5, 4.8, pitch(G, 2), 0.46),
        (54.0, 5.2, pitch(C, 3), 0.42),
    ], vibrato=0.24, slide_cents=16.0)

    sb.phrase("clarinet", [
        # Prime 5 entry (10..15.5) -> 5-beat groupings (2+3)
        (10.0, 1.8, pitch(E, 4), 0.38),
        (12.0, 2.8, pitch(G, 4), 0.42),
        # Breath 14.8..17.0
        (17.0, 1.8, pitch(D, 4), 0.42),
        (19.0, 1.8, pitch(G, 4), 0.46),
        (21.0, 2.6, pitch(B, 4), 0.48),
        # Bar 24..32: Prime Motif foreshadowing (C4 -> E4 -> G4 -> D5 -> C5)
        (24.5, 1.4, pitch(C, 4), 0.46),
        (26.0, 1.8, pitch(E, 4), 0.50),
        (28.0, 1.8, pitch(G, 4), 0.52),
        (30.0, 1.7, pitch(D, 5), 0.54),
        # Bar 33..39 (F maj9)
        (33.0, 1.8, pitch(A, 4), 0.52),
        (35.0, 1.8, pitch(C, 5), 0.55),
        (37.0, 2.5, pitch(E, 5), 0.54),
        # Bar 40..48: FULL PRIME MOTIF with Septimal 7:4 (C4 -> E4 -> G4 -> Bb_harm4 -> C5)!
        (40.5, 1.3, pitch(C, 4), 0.52),
        (42.0, 1.3, pitch(E, 4), 0.55),
        (43.5, 1.8, pitch(G, 4), 0.58),
        (45.5, 2.2, pitch(BB_HARM, 4), 0.62),
        # Cadence 49..59
        (49.0, 2.2, pitch(A, 4, 1), 0.56),   # 9th over G(31) is 40 = A4+1!
        (51.5, 2.1, pitch(G, 4), 0.52),
        (54.5, 4.5, pitch(E, 4), 0.46),
    ], vibrato=0.18)

    # French Horn spotlights the awakening of Prime 7 (BB_HARM = 43) at beat 40!
    sb.phrase("french_horn", [
        (40.2, 3.5, pitch(BB_HARM, 3), 0.48),
        (44.0, 3.6, pitch(E, 4), 0.50),
        (48.2, 5.2, pitch(D, 4), 0.48),
        (54.2, 5.0, pitch(G, 3), 0.42),
    ], vibrato=0.14)

    # --- I.2 (60..132): Sieve of Eratosthenes Polyrhythm (2, 3, 5, 7) & Primes 11, 13, 17, 19 ---
    # Every 0.5-beat grid slot k in 0..143:
    #   - Multiples of 14 slots (7.0 beats): Timpani fundamental stroke (Prime 7 sieve)
    #   - Multiples of 10 slots (5.0 beats): Bassoon / Cello warm ground (Prime 5 sieve)
    #   - Multiples of 6 slots  (3.0 beats): Pizzicato fifth/octave pluck (Prime 3 sieve)
    #   - Prime-numbered slots (k % 60 in PRIME_SET): Piano & Harp sparkling "Un-sieved Prime Stars"!
    for slot in range(144):
        b = 60.0 + slot * 0.5
        sp = sb.span_at(b)
        prog_u = slot / 144.0
        base_v = 0.42 + 0.18 * math.sin(math.pi * prog_u)

        if slot % 14 == 0:
            sb.note("timpani", b, 1.4, sp.bass_root(), base_v * 0.92, trim=False)
        if slot % 10 == 0 and b < 130.5:
            sb.note("bassoon", b, 3.8, sp.bass_root(), base_v * 0.96, swell="arch")
        if slot % 6 == 0:
            pizz_pts = sp.scale_steps(pitch(C, 3), pitch(C, 5), allow_melody=False)
            if pizz_pts:
                st_p = pizz_pts[(slot // 6 * 3) % len(pizz_pts)]
                sb.note("pizzicato", b, 0.42, st_p, base_v * 0.88, snap_to_harmony=False)

        k60 = (slot % 60) + 2
        if k60 in PRIME_SET:
            pts = sp.scale_steps(pitch(E, 3), pitch(A, 5), allow_melody=False)
            if pts:
                # Deterministic non-repeating prime permutation across the chord's overtones
                idx_p = (k60 * 7 + slot // 12) % len(pts)
                st_star = pts[idx_p]
                sb.note("piano", b, 0.65, st_star, base_v * (0.95 if k60 <= 19 else 0.82), snap_to_harmony=False)
                if k60 in (3, 7, 13, 23, 37, 47, 59):
                    sb.harp_arp(
                        sp,
                        b,
                        pitch(C, 3),
                        pitch(A, 5),
                        vel=base_v * 0.90,
                        spacing=0.16,
                        note_dur=1.4,
                        ascending=(k60 % 4 == 1),
                        max_notes=6,
                    )

    # English Horn, Viola & Clarinet spotlight Primes 11 (+24), 13 (+37), 17 (+5), 19 (+13)!
    sb.phrase("english_horn", [
        # Bar 60..68 (C prime11): Prime 11 = step 24 (F#4-2c, 11:8 harmonic!)
        (60.5, 2.2, pitch(E, 4), 0.56),
        (63.0, 2.8, PRIME_11, 0.64),
        (66.0, 1.7, pitch(G, 4), 0.58),
        # Bar 68..76 (G prime11: 31 + 24 = 55 = D4-7? 55 - 53 = 2, oct 4 = 55 -> C5+2!)
        (69.0, 2.4, 31 + M3, 0.60),
        (71.5, 2.6, 31 + PRIME_11 - OCT, 0.65),
        (74.2, 1.5, pitch(G, 4), 0.58),
        # Breath 75.7..77.0
        # Bar 76..84 (C prime13): Prime 13 = step 37 (Ab4+1c, 13:8 within 2.8c!)
        (77.0, 2.2, PRIME_11, 0.62),
        (79.5, 2.8, PRIME_13, 0.68),
        (82.5, 1.3, BB_HARM, 0.64),
        # Bar 84..92 (F prime13: 22 + 37 = 59 -> C#5+2c, oct 4 = 6!)
        (84.5, 2.4, 22 + PRIME_11, 0.64),
        (87.0, 2.8, 22 + PRIME_13 - OCT, 0.66),
        (90.0, 1.7, pitch(C, 4), 0.58),
        # Breath 91.7..93.0
        # Bar 92..100 (C prime17_19): Prime 17 (+5) & Prime 19 (+13) exotic overtone arch!
        (93.0, 1.8, SEMI, 0.60),
        (95.0, 2.2, PRIME_19, 0.66),
        (97.5, 2.2, M3, 0.64),
    ], vibrato=0.28, slide_cents=18.0, snap=False)

    # Lyrical continuation 102..130 (snapped cleanly to each span's pure 53-EDO harmony!)
    sb.phrase("english_horn", [
        (102.0, 2.6, pitch(E, 4), 0.60),
        (105.0, 2.6, pitch(G, 4), 0.64),
        (109.0, 2.6, pitch(A, 4, 1), 0.64),        # Exact 3:2 fifth (40) over D(9)!
        (112.0, 3.4, 9 + HARM_7 - OCT, 0.62),
        (117.0, 2.6, pitch(D, 4), 0.60),
        (120.0, 3.4, 31 + HARM_7 - OCT, 0.64),
        (124.5, 3.2, pitch(E, 4), 0.58),
        (128.0, 3.4, pitch(G, 4), 0.54),
    ], vibrato=0.28, slide_cents=18.0, snap=True)

    sb.phrase("viola", [
        (61.5, 2.2, pitch(G, 3), 0.50),
        (64.0, 3.4, BB_HARM - OCT, 0.54),
        (68.5, 3.2, pitch(D, 3), 0.54),
        (72.0, 3.5, 31 + HARM_7 - 2 * OCT, 0.56),
        (76.5, 3.2, pitch(C, 3), 0.58),
        (80.0, 3.6, pitch(G, 3), 0.60),
        (84.5, 3.2, pitch(A, 3), 0.60),
        (88.0, 3.5, pitch(F, 3), 0.58),
        (92.5, 3.2, pitch(G, 3), 0.62),
        (96.0, 3.6, BB_HARM - OCT, 0.60),
        (100.5, 3.5, pitch(C, 4), 0.58),
        (104.5, 3.2, pitch(E, 4), 0.60),
        (108.5, 3.5, 9 + M3, 0.60),
        (112.5, 3.2, pitch(D, 4), 0.58),
        (116.5, 3.5, pitch(B, 3), 0.60),
        (120.5, 3.2, pitch(G, 4), 0.62),
        (124.5, 6.8, pitch(G, 4), 0.56),
    ], vibrato=0.22, snap=True)

    # Subtle string veil enters in the second half of I.2 (100..132)
    for sp in spans[13:17]:
        sb.string_pad(sp, vel=0.44, swell="arch", include_ext=True)

    # --- I.3 (132..204): The Euler Product — Full Orchestral Convergence (mf -> ff) ---
    euler_spans = spans[17:30]
    for i, sp in enumerate(euler_spans):
        u = i / max(1, len(euler_spans) - 1)
        # Peaks brilliantly at i=9 (C+ add9 Euler Crest at 184..192, vel ~0.88)
        crest = 1.0 - abs(i - 9) / 10.0
        dyn = 0.56 + 0.30 * (crest ** 1.3)
        dur = sp.end - sp.start
        br = sp.bass_root()

        sb.string_pad(sp, vel=dyn * 0.90, swell="cresc" if i < 9 else "arch", include_ext=True)
        if 7 <= i <= 10:
            sb.string_pad(sp, vel=dyn * 0.68, track_id="tremolo_strings", swell="cresc" if i < 9 else "dim", include_ext=False)
        sb.note("bassoon", sp.start, dur - 0.25, br, dyn * 0.92, swell="arch")
        sb.add_pedal(sp.start, dur - 0.16)

        # Evolving Piano Euler-lattice arpeggios (distinct pattern per bar)
        pts = sp.scale_steps(pitch(C, 3), pitch(G, 5), allow_melody=False)
        step_b = 0.5 if dur >= 6.0 else 0.5
        t = sp.start
        p_idx = 0
        while t < sp.end - 0.10 and pts:
            # Prime-stride index walk (stride 2 or 3 depending on bar parity)
            stride = 2 if (i + p_idx) % 3 != 0 else 1
            st_p = pts[(p_idx * stride + i) % len(pts)]
            acc = 1.08 if (p_idx % 4 == 0) else 0.86
            sb.note("piano", t, 0.62, st_p, dyn * 0.82 * acc, snap_to_harmony=False)
            t += step_b
            p_idx += 1

        if i in (0, 2, 3, 7, 8, 9, 12):
            sb.harp_arp(
                sp,
                sp.start,
                pitch(C, 3),
                pitch(C, 6),
                vel=dyn * 0.94,
                spacing=0.14,
                note_dur=2.1,
                ascending=(i != 12),
                max_notes=10,
            )

        if i in (3, 8, 9, 12):
            sb.note("timpani", sp.start, 1.5, br, dyn * 0.88, trim=False)
            if i == 8:
                sb.timpani_roll(sp.start + 2.0, 1.9, br, 0.58, 0.86, subdiv=0.25)

        if 6 <= i <= 10:
            # Noble Trombone + French Horn harmonic pillars across the Comma Lift!
            tr_st = sp.tenor_root()
            sb.note("trombone", sp.start, dur - 0.30, br, dyn * 0.82, swell="cresc" if i < 9 else "arch")
            sb.note("french_horn", sp.start, dur - 0.30, tr_st + P5, dyn * 0.88, swell="arch", vibrato=0.16)

    # Soaring Clarinet, English Horn, Cello & Viola Euler Counterpoint in I.3 (132..204)
    sb.phrase("clarinet", [
        # Prime Motif expanded heroically across C add9 -> Em7 -> Am9 -> F maj9
        (132.0, 1.4, pitch(C, 5), 0.68),
        (133.5, 0.5, pitch(D, 5), 0.66),
        (134.0, 1.8, pitch(E, 5), 0.72),
        (136.0, 1.8, pitch(G, 5), 0.76),
        (138.0, 1.7, pitch(D, 5), 0.70),
        (140.5, 1.8, pitch(B, 4), 0.70),
        (142.5, 1.8, pitch(E, 5), 0.74),
        (144.5, 3.0, pitch(D, 5, 0), 0.72),
        # Breath 147.5..149.0
        (149.0, 1.8, pitch(C, 5), 0.74),
        (151.0, 1.8, pitch(E, 5), 0.78),
        (153.0, 2.6, pitch(B, 4), 0.74),
        (156.0, 1.8, pitch(A, 4), 0.76),
        (158.0, 1.8, pitch(C, 5), 0.80),
        (160.0, 3.5, pitch(E, 5), 0.82),
        # Comma Lift ascent (164..192, k=0 -> +1): holds exact common tones!
        (164.5, 3.2, pitch(G, 4, 0), 0.78),
        (168.0, 3.6, pitch(G, 4, 0), 0.80),    # Common tone G(31)
        (172.0, 3.6, pitch(A, 4, 1), 0.82),    # 9 + 31 = 40 = A4+1!
        (176.0, 3.6, pitch(C, 5, 1), 0.86),
        (180.0, 1.8, pitch(D, 5, 1), 0.88),
        (182.0, 1.8, 32 + HARM_7, 0.90),       # Septimal 7th over G+(32)!
        # Euler Crest at 184..192 on C+(1)!
        (184.0, 1.8, pitch(E, 5, 1), 0.92),
        (186.0, 1.8, pitch(G, 5, 1), 0.94),
        (188.0, 3.6, pitch(D, 5, 1), 0.88),
        # Downward comma return 192..204 (+1 -> 0)
        (192.5, 3.2, pitch(C, 5, 1), 0.82),
        (196.0, 3.6, pitch(A, 4, 1), 0.78),
        (200.0, 3.6, pitch(B, 4, 0), 0.74),
    ], vibrato=0.22)

    sb.phrase("cello", [
        (132.0, 3.6, pitch(C, 3), 0.64),
        (136.0, 3.6, pitch(G, 3), 0.68),
        (140.0, 3.6, pitch(E, 3), 0.68),
        (144.0, 3.6, pitch(B, 3), 0.70),
        (148.0, 3.6, pitch(A, 3), 0.72),
        (152.0, 3.6, pitch(E, 3), 0.70),
        (156.0, 3.6, pitch(F, 3), 0.74),
        (160.0, 3.6, pitch(C, 4), 0.78),
        (164.0, 3.6, pitch(E, 3, 0), 0.76),
        (168.0, 3.6, pitch(D, 3, 0), 0.78),
        (172.0, 3.6, pitch(D, 3, 0), 0.80),    # Exact common tone D(9) into Dm7!
        (176.0, 3.6, pitch(F, 3, 1), 0.84),
        (180.0, 3.6, pitch(G, 3, 1), 0.88),
        (184.0, 3.8, pitch(C, 3, 1), 0.90),
        (188.0, 3.8, pitch(G, 3, 1), 0.86),
        (192.0, 3.6, pitch(A, 3, 1), 0.80),
        (196.0, 3.6, pitch(F, 3, 1), 0.76),    # 9 + 14 = 23 = F3+1!
        (200.0, 3.6, pitch(G, 3, 0), 0.74),
    ], vibrato=0.28, slide_cents=16.0)

    sb.phrase("english_horn", [
        (136.0, 3.5, pitch(E, 4), 0.66),
        (140.0, 3.5, pitch(G, 4), 0.68),
        (148.5, 3.2, pitch(E, 4), 0.70),
        (152.0, 3.5, pitch(E, 4), 0.74),
        (156.5, 3.2, pitch(C, 5), 0.76),
        (160.0, 3.5, pitch(A, 4), 0.76),
        # Joins climax 176..192
        (176.5, 3.2, pitch(A, 4, 1), 0.82),
        (180.0, 3.6, pitch(B, 4, 1), 0.86),
        (184.0, 3.8, pitch(C, 5, 1), 0.90),
        (188.0, 3.6, pitch(G, 4, 1), 0.84),
    ], vibrato=0.26)

    # --- I.4 (204..264): Asymptotic Thinning (x / ln x) & Approach to Re(s) = 1 (mf -> pp) ---
    asym_spans = spans[30:]
    for i, sp in enumerate(asym_spans):
        dur = sp.end - sp.start
        dyn = 0.56 - 0.05 * i  # Tapers 0.56 -> 0.26
        br = sp.bass_root()
        sb.add_pedal(sp.start, dur - 0.20)
        if i <= 3:
            sb.string_pad(sp, vel=dyn * 0.85, swell="dim", include_ext=(i < 2))
        else:
            # Mysterious shimmering tremolo mist approaching the Pole Re(s)=1!
            sb.string_pad(sp, vel=dyn + 0.06, track_id="tremolo_strings", swell="arch", include_ext=False)
        sb.note("bassoon", sp.start, dur * 0.75, br, dyn + 0.05, swell="dim")
        # Thinning prime intervals: gaps widen logarithmically!
        sb.harp_arp(
            sp,
            sp.start + 0.8,
            pitch(E, 3),
            pitch(E, 5),
            vel=dyn + 0.08,
            spacing=0.28 + 0.06 * i,
            note_dur=2.6,
            ascending=(i < 4),
            max_notes=max(3, 7 - i),
        )

    # Sparse English Horn & Viola echoes + ominous low Timpani pulse at 254..264
    sb.phrase("english_horn", [
        (205.0, 2.8, pitch(G, 4), 0.56),
        (208.5, 3.0, pitch(E, 4), 0.52),
        (214.0, 3.2, pitch(C, 5), 0.48),
        (222.0, 3.8, pitch(A, 4), 0.44),
        (231.0, 4.2, pitch(F, 4), 0.38),
        (246.0, 4.8, 31 + HARM_7 - OCT, 0.36),
        (256.0, 6.2, 17 + HARM_7 - OCT, 0.34),  # Septimal 7th over E(17) = 60 -> C4+7!
    ], swell="dim", vibrato=0.24, snap=False)

    sb.timpani_roll(256.0, 7.5, spans[-1].bass_root(), 0.24, 0.46, subdiv=0.35)


# =============================================================================
# MOVEMENT II — ANALYTIC CONTINUATION (Beats 264..516, 3:45 – 7:30)
# =============================================================================
def compose_movement_2(sb: RiemannSymphonyBuilder) -> None:
    sb.add_section(264.0, "II. Analytic Continuation — 1. The Divergence Wall at Re(s) = 1")
    sb.add_section(320.0, "II.2 Into the Critical Strip (0 < Re(s) < 1) — Nocturne")
    sb.add_section(384.0, "II.3 Functional Equation xi(s) = xi(1 - s) — Exact Mirror & Palindrome")
    sb.add_section(456.0, "II.4 First Nontrivial Zero (t_1 = 14.1347) — Spectral Stillness")

    m2_specs = [
        # II.1 (264..320): Divergence Pole Re(s)=1 & Chromatic-Mediant Diesis Rotation (0 -> 36 -> 19 -> 2)
        (264.0, 272.0, A, "min", "II.1a Pole Horizon Am"),
        (272.0, 280.0, C, "maj", "II.1b Pole Surge C(0)"),
        (280.0, 288.0, AB, "maj", "II.1c Analytic Rotation -M3: Ab(36, holds C=0)"),
        (288.0, 296.0, 19, "maj", "II.1d Analytic Rotation -M3: E-(19, holds Ab=36)"),
        (296.0, 304.0, 2, "maj", "II.1e Breach of Re(s)=1: C++(2, holds E-=19, +2 Diesis!)"),
        (304.0, 308.0, 24, "maj7", "II.1f Subito pp Strip Entry F++(24)"),
        (308.0, 312.0, 10, "min7", "II.1g Comma Glide ii+(10)"),
        (312.0, 320.0, 32, "dom7", "II.1h Comma Glide V7+(32 -> k=+1)"),
        # II.2 (320..384): Critical Strip Nocturne (k=+1 -> 0)
        (320.0, 328.0, C + 1, "maj9", "II.2a Critical Strip Nocturne C+(1)"),
        (328.0, 336.0, A + 1, "min9", "II.2b Strip Nocturne Am9+(40)"),
        (336.0, 344.0, F + 1, "maj9", "II.2c Strip Nocturne F+ maj9(23)"),
        (344.0, 352.0, D_MINUS + 1, "min9", "II.2d Strip Nocturne Dm9+(9)"),
        (352.0, 360.0, BB + 1, "maj7", "II.2e Downward Glide Bb+(45)"),
        (360.0, 368.0, G, "min7", "II.2f Downward Glide Gm7(31)"),
        (368.0, 376.0, C, "dom9", "II.2g Septimal Bridge C dom9(0)"),
        (376.0, 384.0, F, "maj9", "II.2h Arrival at Critical Line Axis F maj9(22)"),
        # II.3 (384..456): Palindromic 18-Bar Functional Equation Arch around Beat 420.0!
        # Forward Half (384..420, 9 bars x 4 beats):
        (384.0, 388.0, C, "mirror_maj", "II.3.1 Mirror Forward 1: C"),
        (388.0, 392.0, A, "mirror_min", "II.3.2 Mirror Forward 2: Am"),
        (392.0, 396.0, F, "mirror_maj", "II.3.3 Mirror Forward 3: F"),
        (396.0, 400.0, D_MINUS, "mirror_min", "II.3.4 Mirror Forward 4: Dm-"),
        (400.0, 404.0, G, "mirror_maj", "II.3.5 Mirror Forward 5: G"),
        (404.0, 408.0, E, "mirror_min", "II.3.6 Mirror Forward 6: Em"),
        (408.0, 412.0, A, "mirror_min", "II.3.7 Mirror Forward 7: Am"),
        (412.0, 416.0, F, "mirror_maj", "II.3.8 Mirror Forward 8: F"),
        (416.0, 420.0, C, "mirror_maj", "II.3.9 Critical Line Axis Re(s)=1/2 (Left)"),
        # Retrograde Half (420..456, exact harmonic palindrome!):
        (420.0, 424.0, C, "mirror_maj", "II.3.10 Critical Line Axis Re(s)=1/2 (Right)"),
        (424.0, 428.0, F, "mirror_maj", "II.3.11 Mirror Retrograde 8: F"),
        (428.0, 432.0, A, "mirror_min", "II.3.12 Mirror Retrograde 7: Am"),
        (432.0, 436.0, E, "mirror_min", "II.3.13 Mirror Retrograde 6: Em"),
        (436.0, 440.0, G, "mirror_maj", "II.3.14 Mirror Retrograde 5: G"),
        (440.0, 444.0, D_MINUS, "mirror_min", "II.3.15 Mirror Retrograde 4: Dm-"),
        (444.0, 448.0, F, "mirror_maj", "II.3.16 Mirror Retrograde 3: F"),
        (448.0, 452.0, A, "mirror_min", "II.3.17 Mirror Retrograde 2: Am"),
        (452.0, 456.0, C, "mirror_maj", "II.3.18 Mirror Retrograde 1: C"),
        # II.4 (456..516): First Nontrivial Zero (1/2 + i*14.1347) — Spectral Cancellation (mf -> ppp)
        (456.0, 464.0, A, "min9", "II.4a Zero Approach Am9"),
        (464.0, 472.0, F, "maj9", "II.4b Zero Approach F maj9"),
        (472.0, 480.0, D_MINUS, "min9", "II.4c Zero Approach Dm-9"),
        (480.0, 488.0, G, "dom9", "II.4d Septimal Convergence G dom9"),
        (488.0, 496.0, C, "add9", "II.4e Zero Node Settling C add9"),
        (496.0, 506.0, C, "sus2", "II.4f Spectral Cancellation C sus2"),
        (506.0, 516.0, C, "open5", "II.4g First Nontrivial Zero (ppp Unison/Fifth)"),
    ]
    spans = [sb.add_span(*c) for c in m2_specs]

    # --- II.1 (264..320): Crossing the Pole Re(s)=1 via Common-Tone Diesis Rotations ---
    for i, sp in enumerate(spans[:5]):
        dur = sp.end - sp.start
        dyn = 0.56 + 0.09 * i  # 0.56 -> 0.92 ff Breach!
        br = sp.bass_root()
        sb.string_pad(sp, vel=dyn * 0.88, track_id="tremolo_strings", swell="cresc", include_ext=False)
        sb.string_pad(sp, vel=dyn * 0.82, swell="cresc", include_ext=False)
        sb.note("bassoon", sp.start, dur - 0.25, br, dyn * 0.90, swell="cresc")
        sb.note("trombone", sp.start, dur - 0.25, br, dyn * 0.88, swell="sfz" if i == 4 else "cresc")
        sb.note("trombone", sp.start + 0.2, dur - 0.45, sp.tenor_root() + P5, dyn * 0.82, swell="cresc")
        sb.harp_arp(sp, sp.start, pitch(C, 3), pitch(C, 6), vel=dyn * 0.92, spacing=0.14, note_dur=2.2, ascending=(i % 2 == 0), max_notes=10)
        if i < 4:
            sb.note("timpani", sp.start, 1.6, br, dyn * 0.85, trim=False)
            sb.note("timpani", sp.start + 4.0, 1.6, br, dyn * 0.88, trim=False)
        else:
            sb.timpani_roll(sp.start, 7.6, br, 0.78, 0.94, subdiv=0.25)

    # Exact Common-Tone Golden Thread held across the barlines in French Horn & English Horn!
    # 264..280: C4(0) / E4(17); 272..288: C4(0) held seamlessly across C(0)->Ab(36)!
    # 284..296: Ab4(36) held seamlessly across Ab(36)->E-(19)!
    # 292..304: E-4(19) held seamlessly across E-(19)->C++(2)!
    sb.note("french_horn", 264.5, 7.2, pitch(E, 4), 0.62, swell="cresc", trim=False)
    sb.note("french_horn", 272.5, 15.2, pitch(C, 4), 0.78, swell="cresc", vibrato=0.18, trim=False)
    sb.note("english_horn", 284.0, 11.6, pitch(AB, 4), 0.84, swell="cresc", vibrato=0.25, trim=False)
    sb.note("clarinet", 292.0, 11.7, 19 + OCT, 0.90, swell="sfz", vibrato=0.22, trim=False)

    # Subito pp crossing into the Critical Strip (304..320)
    for j, sp in enumerate(spans[5:8]):
        dur = sp.end - sp.start
        dyn = [0.34, 0.36, 0.40][j]
        sb.add_pedal(sp.start, dur - 0.16)
        sb.string_pad(sp, vel=dyn * 0.82, swell="dim" if j == 0 else "arch", include_ext=True)
        sb.harp_arp(sp, sp.start + 0.3, pitch(E, 3), pitch(G, 5), vel=dyn + 0.06, spacing=0.24, note_dur=2.4, ascending=False, max_notes=6)

    # --- II.2 (320..384): Critical Strip Nocturne (Pedaled Piano + English Horn + Cello, pp -> mf) ---
    nocturne_spans = spans[8:16]
    for i, sp in enumerate(nocturne_spans):
        dur = sp.end - sp.start
        dyn = 0.36 + 0.035 * min(i, 8 - i + 2)
        br = sp.bass_root()
        sb.add_pedal(sp.start, 3.84)
        sb.add_pedal(sp.start + 4.0, 3.84)
        sb.note("bassoon", sp.start, 3.6, br, dyn * 0.90, swell="arch")
        sb.note("bassoon", sp.start + 4.0, 3.6, br, dyn * 0.86, swell="dim")
        if i >= 2:
            sb.string_pad(sp, vel=dyn * 0.76, swell="arch", include_ext=True)
        if i % 2 == 0:
            sb.harp_arp(sp, sp.start + 1.0, pitch(C, 3), pitch(A, 5), vel=dyn + 0.08, spacing=0.20, note_dur=2.6, ascending=True, max_notes=8)

        # Flowing Pedaled Piano Nocturne Waves (wide open 10ths/5ths >= C3)
        pts = sp.scale_steps(pitch(C, 3), pitch(E, 5), allow_melody=False)
        if len(pts) >= 5:
            wave_idx = [0, 2, 4, 3, 1, 3, 4, 2, 0, 2, 3, 4, 2, 1, 2, 3]
            for s_k, wi in enumerate(wave_idx):
                t = sp.start + s_k * 0.5
                st_w = pts[(wi + (i % 2)) % len(pts)]
                acc = 1.06 if s_k % 8 == 0 else 0.86
                sb.note("piano", t, 0.72, st_w, dyn * 0.84 * acc, snap_to_harmony=False)

    # Lyrical English Horn & Cello Critical Strip Cantabile (320..384)
    sb.phrase("english_horn", [
        (321.0, 2.6, pitch(E, 4, 1), 0.48),
        (324.0, 3.4, pitch(B, 4, 1), 0.54),
        (328.5, 2.8, pitch(C, 5, 1), 0.56),
        (332.0, 3.4, pitch(E, 4, 1), 0.52),
        # Breath 335.4..337.0
        (337.0, 2.6, pitch(A, 4, 1), 0.58),
        (340.0, 3.5, pitch(C, 5, 1), 0.62),
        (344.5, 2.8, pitch(A, 4, 1), 0.60),
        (348.0, 3.4, pitch(F, 4, 1), 0.56),
        # Breath 351.4..353.0
        (353.0, 2.6, pitch(D_MINUS, 5, 1), 0.62),  # 8+1 = 9 in Oct 5!
        (356.0, 3.5, pitch(A, 4, 1), 0.60),
        (360.5, 2.8, pitch(BB, 4, 1), 0.62),       # 44+1 = 45 = pure m3 of Gm(31)!
        (364.0, 3.5, pitch(D, 4, 0), 0.58),
        (369.0, 2.8, BB_HARM, 0.64),               # Septimal 7:4 glow on k=0!
        (372.0, 3.5, pitch(G, 4, 0), 0.60),
        (376.5, 6.5, pitch(A, 4, 0), 0.56),
    ], vibrato=0.34, slide_cents=22.0, snap=True)

    sb.phrase("cello", [
        (324.5, 3.0, pitch(G, 3, 1), 0.46),
        (328.5, 3.2, pitch(A, 3, 1), 0.50),
        (332.5, 3.0, pitch(C, 4, 1), 0.52),
        (336.5, 3.2, pitch(F, 3, 1), 0.54),
        (340.5, 3.0, pitch(A, 3, 1), 0.56),
        (344.5, 3.2, pitch(D_MINUS, 3, 1), 0.56),
        (348.5, 3.0, pitch(A, 3, 1), 0.54),
        (352.5, 3.2, pitch(F, 3, 1), 0.58),
        (356.5, 3.0, pitch(D_MINUS, 4, 1), 0.60),
        (360.5, 3.2, pitch(G, 3, 0), 0.58),
        (364.5, 3.0, pitch(BB, 3, 1), 0.56),
        (368.5, 3.2, pitch(E, 3, 0), 0.58),
        (372.5, 3.0, pitch(C, 4, 0), 0.60),
        (376.5, 6.5, pitch(F, 3, 0), 0.54),
    ], vibrato=0.32, slide_cents=20.0, snap=True)

    # --- II.3 (384..456): Functional Equation xi(s) = xi(1 - s) ---
    # Exact Simultaneous Mirror-Inversion Counterpoint & 18-Bar Palindromic Arch around Beat 420.0!
    mirror_fwd_spans = spans[16:25]
    mirror_ret_spans = spans[25:34]

    # 9-bar melodic offsets (bar_idx, beat_in_bar, dur, scale_deg_from_upper)
    # Every note u has exact mirror partner l = S - u in the same self-dual chord!
    fwd_upper_bars = [
        [(0.0, 1.8, pitch(E, 4), 0.52), (2.0, 1.8, pitch(G, 4), 0.56)],                 # C: E4(17)<->G4(31)
        [(0.0, 1.3, pitch(A, 4), 0.56), (1.5, 0.5, pitch(B, 4), 0.54), (2.0, 1.8, pitch(C, 5), 0.60)],
        [(0.0, 1.8, pitch(A, 4), 0.60), (2.0, 1.8, pitch(C, 5), 0.64)],
        [(0.0, 1.3, pitch(D_MINUS, 5), 0.64), (1.5, 0.5, pitch(C, 5), 0.62), (2.0, 1.8, pitch(A, 4), 0.66)],
        [(0.0, 1.8, pitch(B, 4), 0.68), (2.0, 1.8, pitch(D, 5), 0.72)],
        [(0.0, 1.3, pitch(E, 5), 0.72), (1.5, 0.5, pitch(B, 4), 0.70), (2.0, 1.8, pitch(G, 4), 0.74)],
        [(0.0, 1.8, pitch(C, 5), 0.76), (2.0, 1.8, pitch(E, 5), 0.80)],
        [(0.0, 1.8, pitch(C, 5), 0.82), (2.0, 1.8, pitch(A, 4), 0.84)],
        [(0.0, 1.8, pitch(B, 4), 0.86), (2.0, 1.9, pitch(G, 4), 0.88)],                 # Crest approaching 420.0!
    ]

    # Forward Half (384..420): English Horn + Clarinet sing u(t); Cello + Viola mirror S - u(t)!
    for bi, sp in enumerate(mirror_fwd_spans):
        S = sp.mirror_sum(center_oct=4)
        dyn = 0.46 + 0.045 * bi
        sb.add_pedal(sp.start, 3.84)
        if bi >= 2:
            sb.string_pad(sp, vel=dyn * 0.78, swell="cresc" if bi >= 6 else "arch", include_ext=True)
        if bi >= 4:
            sb.note("bassoon", sp.start, 3.7, sp.bass_root(), dyn * 0.86, swell="arch")
        if bi in (0, 3, 6, 8):
            sb.harp_arp(sp, sp.start, pitch(C, 3), pitch(B, 5), vel=dyn * 0.90, spacing=0.16, note_dur=2.0, ascending=True, max_notes=8)

        # Mirror Piano dyads on off-beats: RH plays u_p in Oct 4..5, LH plays exact S - u_p >= C3!
        pts_hi = sp.scale_steps(pitch(D, 4), pitch(C, 5), allow_melody=False)
        for q in range(4):
            if pts_hi:
                u_p = pts_hi[(q + bi) % len(pts_hi)]
                l_p = S - u_p
                while l_p < -53:
                    l_p += OCT
                sb.note("piano", sp.start + q + 0.5, 0.75, u_p, dyn * 0.74, snap_to_harmony=False)
                sb.note("piano", sp.start + q + 0.5, 0.75, l_p, dyn * 0.72, snap_to_harmony=False)

        for off, dur, raw_u, v in fwd_upper_bars[bi]:
            u_st = sp.nearest_step(raw_u, allow_melody=False)
            while u_st > 48:
                u_st -= OCT
            while u_st < 9:
                u_st += OCT
            l_st = S - u_st   # Exact un-wrapped integer reflection in [-76..+15]!
            if l_st < -OCT and abs(l_st - sp.bass_root()) < P4 and l_st != sp.bass_root():
                # Shift S up one octave on this pair so both u_st and l_st sit >= C3 with exact sum S+OCT!
                l_st += OCT
            lead_tr = "clarinet" if bi < 3 else "english_horn"
            mirr_tr = "viola" if (bi < 3 and l_st >= -53) else "cello"
            sb.note(lead_tr, sp.start + off, dur, u_st, v, swell="arch", vibrato=0.28, snap_to_harmony=False)
            sb.note(mirr_tr, sp.start + off, dur, l_st, v * 0.96, swell="arch", vibrato=0.28, snap_to_harmony=False)
            if bi >= 6:
                # Double at the critical-line crest in Clarinet + Viola!
                v_st = l_st + OCT if l_st < -48 else l_st
                sb.note("clarinet", sp.start + off, dur, u_st + OCT if u_st < 22 else u_st, v * 0.88, swell="arch", vibrato=0.20, snap_to_harmony=False)
                sb.note("viola", sp.start + off, dur, v_st, v * 0.84, swell="arch", vibrato=0.20, snap_to_harmony=False)

    # Golden French Horn bloom right across the Critical Line Axis (beat 416..424)!
    sb.note("french_horn", 416.0, 3.8, pitch(G, 3), 0.80, swell="cresc", vibrato=0.18)
    sb.note("french_horn", 420.0, 3.8, pitch(E, 4), 0.82, swell="dim", vibrato=0.18)

    # Retrograde Half (420..456): True Retrograde-Inversion Palindrome!
    # Reverses harmonic order AND reverses time within each bar while swapping roles:
    # Cello/Viola now sing the primary mirror-inverted line while Clarinet/English Horn answer!
    for r_i, sp in enumerate(mirror_ret_spans):
        src_bi = 8 - r_i
        S = sp.mirror_sum(center_oct=4)
        dyn = 0.82 - 0.045 * r_i
        sb.add_pedal(sp.start, 3.84)
        if r_i <= 6:
            sb.string_pad(sp, vel=dyn * 0.76, swell="dim" if r_i >= 5 else "arch", include_ext=True)
        if r_i <= 4:
            sb.note("bassoon", sp.start, 3.7, sp.bass_root(), dyn * 0.84, swell="dim")
        if r_i in (0, 2, 5, 8):
            sb.harp_arp(sp, sp.start, pitch(C, 3), pitch(B, 5), vel=dyn * 0.88, spacing=0.18, note_dur=2.1, ascending=False, max_notes=8)

        # Retrograde time reversal of each bar's events: new_off = 4.0 - (off + dur)
        src_events = fwd_upper_bars[src_bi]
        for off, dur, raw_u, v in reversed(src_events):
            rev_off = max(0.0, round(4.0 - (off + dur), 3))
            u_st = sp.nearest_step(raw_u, allow_melody=False)
            while u_st > 48:
                u_st -= OCT
            while u_st < 9:
                u_st += OCT
            l_st = S - u_st
            if l_st < -OCT and abs(l_st - sp.bass_root()) < P4 and l_st != sp.bass_root():
                l_st += OCT
            v_scaled = v * (0.96 - 0.03 * r_i)
            # Orchestral role inversion across the mirror!
            sb.note("cello", sp.start + rev_off, dur, l_st, v_scaled, swell="arch", vibrato=0.30, snap_to_harmony=False)
            sb.note("clarinet" if r_i >= 5 else "english_horn", sp.start + rev_off, dur, u_st, v_scaled * 0.94, swell="arch", vibrato=0.26, snap_to_harmony=False)

        # Flowing triplet-feel Piano mirror filigree (distinct texture from forward half!)
        pts_hi = sp.scale_steps(pitch(D, 4), pitch(C, 5), allow_melody=False)
        for q, sub_t in enumerate([0.0, 1.0, 2.0, 3.0]):
            if pts_hi:
                u_p = pts_hi[(len(pts_hi) - 1 - q - r_i) % len(pts_hi)]
                l_p = S - u_p
                while l_p < -53:
                    l_p += OCT
                sb.note("piano", sp.start + sub_t, 0.82, u_p, dyn * 0.70, snap_to_harmony=False)
                sb.note("piano", sp.start + sub_t + 0.35, 0.65, l_p, dyn * 0.66, snap_to_harmony=False)

    # --- II.4 (456..516): First Nontrivial Zero (t_1 = 14.1347) — Spectral Cancellation (mp -> pp) ---
    zero_spans = spans[34:]
    for i, sp in enumerate(zero_spans):
        dur = sp.end - sp.start
        dyn = max(0.38, 0.52 - 0.024 * i)
        sb.add_pedal(sp.start, dur - 0.20)
        if i <= 4:
            sb.string_pad(sp, vel=dyn * 0.86, swell="dim", include_ext=False)
        else:
            # Pure C3, G3, C4, G4 glass harmonic stillness (audible warm pp!)
            sb.chord("string_ensemble", sp.start, dur - 0.30, [pitch(C, 3), pitch(G, 3), pitch(C, 4), pitch(G, 4)], dyn * 0.86, swell="dim")
            sb.note("french_horn", sp.start + 0.5, dur - 1.2, pitch(G, 3), dyn * 0.82, swell="dim")
        sb.note("bassoon", sp.start, dur * 0.72, sp.bass_root(), dyn * 0.90, swell="dim")
        sb.harp_arp(sp, sp.start + 0.6, pitch(C, 3), pitch(G, 5), vel=dyn + 0.08, spacing=0.30 + 0.04 * i, note_dur=3.0, ascending=True, max_notes=max(4, 7 - i))

    # Voices converge inward step-by-step onto exact C4 = 0 at the Nontrivial Zero!
    sb.phrase("viola", [
        (457.0, 5.5, pitch(E, 4), 0.48),
        (465.0, 5.5, pitch(C, 4), 0.46),
        (473.0, 5.5, pitch(D_MINUS, 4), 0.44),
        (481.0, 5.5, pitch(D, 4), 0.42),
        (489.0, 6.0, pitch(C, 4), 0.40),
        (506.5, 8.2, pitch(C, 4), 0.38),
    ], swell="dim", vibrato=0.18)

    sb.phrase("cello", [
        (458.0, 5.0, pitch(A, 3), 0.48),
        (466.0, 5.0, pitch(A, 3), 0.46),
        (474.0, 5.0, pitch(A, 3), 0.44),
        (482.0, 5.0, pitch(B, 3), 0.42),
        (497.0, 7.5, pitch(C, 3), 0.40),
        (506.5, 8.2, pitch(G, 3), 0.38),
    ], swell="dim", vibrato=0.20)

    sb.note("piano", 508.0, 6.5, pitch(C, 4), 0.40, snap_to_harmony=False)
    sb.note("piano", 510.5, 4.5, pitch(C, 5), 0.38, snap_to_harmony=False)


# =============================================================================
# MOVEMENT III — A CENTURY OF SMALL PROGRESS (Beats 516..836, 7:30 – 11:30)
# 10 Evolving Brahmsian/Brucknerian Passacaglia Variations & 4-Voice Fugato
# Climbing Across Syntonic Comma Planes: k = 0 -> +1 -> +2 -> +3 (Unresolved!)
# =============================================================================
def add_passacaglia_cycle(
    sb: RiemannSymphonyBuilder,
    start_beat: float,
    k: int,
    var_num: int,
    climb_comma: bool = False,
    unresolved_end: bool = False,
) -> List[ChordSpan]:
    """Adds one 8-bar (32-beat) Passacaglia harmonic cycle on comma plane `k`."""
    b = start_beat
    if not climb_comma and not unresolved_end:
        specs = [
            (b + 0.0, b + 4.0, C + k, "min", f"III.V{var_num}.1 Cm(k={k})"),
            (b + 4.0, b + 8.0, G + k, "min7", f"III.V{var_num}.2 Gm7(k={k})"),
            (b + 8.0, b + 12.0, AB + k, "maj7", f"III.V{var_num}.3 Ab maj7(k={k})"),
            (b + 12.0, b + 16.0, EB + k, "add9", f"III.V{var_num}.4 Eb add9(k={k})"),
            (b + 16.0, b + 20.0, F + k, "min7", f"III.V{var_num}.5 Fm7(k={k})"),
            (b + 20.0, b + 24.0, C + k, "min", f"III.V{var_num}.6 Cm(k={k})"),
            (b + 24.0, b + 28.0, AB + k, "maj9", f"III.V{var_num}.7 Ab maj9(k={k})"),
            (b + 28.0, b + 32.0, G + k, "dom7", f"III.V{var_num}.8 G dom7(k={k})"),
        ]
    elif climb_comma:
        # Smooth upward syntonic comma modulation k -> k+1 across bars 5..8!
        specs = [
            (b + 0.0, b + 4.0, C + k, "min", f"III.V{var_num}.1 Cm(k={k})"),
            (b + 4.0, b + 8.0, G + k, "min7", f"III.V{var_num}.2 Gm7(k={k})"),
            (b + 8.0, b + 12.0, AB + k, "maj7", f"III.V{var_num}.3 Ab maj7(k={k})"),
            (b + 12.0, b + 16.0, EB + k, "maj", f"III.V{var_num}.4 Eb(k={k})"),
            (b + 16.0, b + 20.0, G + k, "maj", f"III.V{var_num}.5 Pivot V(31+{k})"),
            (b + 20.0, b + 24.0, D + k, "min7", f"III.V{var_num}.6 Pivot ii(9+{k})"),
            (b + 24.0, b + 28.0, F + k + 1, "maj7", f"III.V{var_num}.7 Lifted IV+(23+{k})"),
            (b + 28.0, b + 32.0, G + k + 1, "dom7", f"III.V{var_num}.8 Lifted V7+(k={k + 1})"),
        ]
    else:
        # Variation 10 (k=+3): freezes unresolved on tense G+++ dom7 cliffhanger!
        specs = [
            (b + 0.0, b + 4.0, C + k, "min", f"III.V{var_num}.1 Cm(k={k})"),
            (b + 4.0, b + 8.0, AB + k, "maj7", f"III.V{var_num}.2 Ab maj7(k={k})"),
            (b + 8.0, b + 12.0, F + k, "min7", f"III.V{var_num}.3 Fm7(k={k})"),
            (b + 12.0, b + 16.0, G + k, "sus4", f"III.V{var_num}.4 G sus4(k={k})"),
            (b + 16.0, b + 24.0, AB + k, "maj9", f"III.V{var_num}.5 Tragic VI9(k={k})"),
            (b + 24.0, b + 32.0, G + k, "dom7", f"III.V{var_num}.6 Unresolved Summit V7(k={k}!)"),
        ]
    return [sb.add_span(*s) for s in specs]


def compose_movement_3(sb: RiemannSymphonyBuilder) -> None:
    sb.add_section(516.0, "III. A Century of Small Progress — 1. Granite Passacaglia (Hadamard & Hardy, k=0->+1)")
    sb.add_section(612.0, "III.2 Four-Voice Fugato & Selberg Parity Setback (k=+1->+2)")
    sb.add_section(708.0, "III.3 Montgomery–Odlyzko Pair Correlation & Comma Ascent (k=+2->+3)")
    sb.add_section(772.0, "III.4 The Unresolved Summit at k=+3 — One Step Shy of Truth")

    # Build all 10 Passacaglia variations (320 beats: 516..836)
    v1 = add_passacaglia_cycle(sb, 516.0, k=0, var_num=1)
    v2 = add_passacaglia_cycle(sb, 548.0, k=0, var_num=2)
    v3 = add_passacaglia_cycle(sb, 580.0, k=0, var_num=3, climb_comma=True)       # 0 -> +1
    v4 = add_passacaglia_cycle(sb, 612.0, k=1, var_num=4)                         # Fugato on k=+1
    v5 = add_passacaglia_cycle(sb, 644.0, k=1, var_num=5)                         # Drive & Subito pp setback!
    v6 = add_passacaglia_cycle(sb, 676.0, k=1, var_num=6, climb_comma=True)       # +1 -> +2
    v7 = add_passacaglia_cycle(sb, 708.0, k=2, var_num=7)                         # Pair correlation on k=+2
    v8 = add_passacaglia_cycle(sb, 740.0, k=2, var_num=8, climb_comma=True)       # +2 -> +3
    v9 = add_passacaglia_cycle(sb, 772.0, k=3, var_num=9)                         # Summit struggle on k=+3
    v10 = add_passacaglia_cycle(sb, 804.0, k=3, var_num=10, unresolved_end=True)  # Unresolved cliffhanger

    # --- Variation 1 (516..548, k=0, pp -> mp): Solitary Cello & Bassoon Granite Ground ---
    for i, sp in enumerate(v1):
        br = sp.bass_root()
        v = 0.36 + 0.018 * i
        sb.note("bassoon", sp.start, 3.3, br, v, swell="arch")
        sb.note("cello", sp.start, 2.5, br + OCT, v + 0.05, swell="arch", vibrato=0.22)
        sb.note("cello", sp.start + 3.0, 0.85, br + OCT + P5, v + 0.02, swell="none")
        sb.note("pizzicato", sp.start, 0.45, br + OCT, v + 0.05)
        sb.string_pad(sp, vel=v * 0.78, swell="arch", include_ext=False)
        if i >= 3:
            sb.note("viola", sp.start + 1.0, 2.6, sp.tenor_root() + OCT + (m3 if "min" in sp.quality else M3), v + 0.03, swell="arch", vibrato=0.18)

    # --- Variation 2 (548..580, k=0, mp): English Horn & Clarinet Two-Voice Canon ---
    eh_v2 = []
    cl_v2 = []
    for i, sp in enumerate(v2):
        br = sp.bass_root()
        v = 0.46 + 0.012 * i
        sb.note("bassoon", sp.start, 1.8, br, v, swell="arch")
        sb.note("bassoon", sp.start + 2.0, 1.7, br + OCT + P5, v * 0.94, swell="arch")
        sb.note("cello", sp.start, 1.8, br + OCT, v + 0.04, vibrato=0.20)
        sb.note("cello", sp.start + 2.0, 1.8, br + OCT + P5, v + 0.02, vibrato=0.18)
        # Brahmsian off-beat syncopated Piano chords
        voic = sp.open_voicing(include_ext=False)
        sb.chord("piano", sp.start + 0.5, 1.2, voic, v * 0.80)
        sb.chord("piano", sp.start + 2.5, 1.2, voic, v * 0.78)
        if i % 2 == 0:
            eh_v2.extend([
                (sp.start, 1.4, sp.nearest_step(pitch(G, 4) - i, allow_melody=False), v + 0.08),
                (sp.start + 1.5, 0.45, sp.nearest_step(pitch(EB, 4), allow_melody=True), v + 0.05),
                (sp.start + 2.0, 1.7, sp.nearest_step(pitch(C, 5) - i * 2, allow_melody=False), v + 0.10),
            ])
        else:
            # Imitative answer in Clarinet 1 bar later while English Horn breathes!
            cl_v2.extend([
                (sp.start, 1.4, sp.nearest_step(pitch(C, 5) - i, allow_melody=False), v + 0.08),
                (sp.start + 1.5, 0.45, sp.nearest_step(pitch(G, 4), allow_melody=True), v + 0.05),
                (sp.start + 2.0, 1.7, sp.nearest_step(pitch(EB, 5) - i * 2, allow_melody=False), v + 0.10),
            ])
    sb.phrase("english_horn", eh_v2, vibrato=0.28, slide_cents=16.0)
    sb.phrase("clarinet", cl_v2, vibrato=0.22)

    # --- Variation 3 (580..612, k=0 -> +1, mp -> mf): Hardy (1914) — First Upward Comma Lift! ---
    for i, sp in enumerate(v3):
        br = sp.bass_root()
        v = 0.52 + 0.025 * i
        sb.string_pad(sp, vel=v * 0.82, swell="cresc" if i >= 4 else "arch", include_ext=True)
        sb.note("bassoon", sp.start, 3.7, br, v * 0.94, swell="arch")
        sb.add_pedal(sp.start, 3.84)
        # Flowing Viola & Cello eighth-note contrapuntal weave
        pts = sp.scale_steps(pitch(C, 3), pitch(C, 5), allow_melody=True)
        if len(pts) >= 5:
            for s_i in range(8):
                t = sp.start + s_i * 0.5
                st_v = pts[(s_i + i * 2) % len(pts)]
                sb.note("viola", t, 0.44, st_v, v * (0.94 if s_i % 4 == 0 else 0.80), snap_to_harmony=False)
        if i in (0, 3, 6, 7):
            sb.harp_arp(sp, sp.start, pitch(C, 3), pitch(G, 5), vel=v * 0.92, spacing=0.16, note_dur=1.9, ascending=True, max_notes=8)
        if i >= 4:
            # French Horn highlights the upward comma step k=0 -> +1!
            hr_st = sp.tenor_root() + P5
            sb.note("french_horn", sp.start, 3.6, hr_st, v * 0.92, swell="cresc" if i == 7 else "arch", vibrato=0.18)

    # Soaring Cello & Clarinet Hardy-1914 Counter-Melody in Variation 3 (580..612)
    sb.phrase("cello", [
        (580.0, 3.6, pitch(G, 3, 0), 0.56),
        (584.0, 3.6, pitch(D, 3, 0), 0.58),
        (588.0, 3.6, pitch(EB, 3, 0), 0.60),
        (592.0, 3.6, pitch(G, 3, 0), 0.62),
        (596.0, 3.6, pitch(G, 3, 0), 0.66),
        (600.0, 3.6, pitch(A, 3, 1), 0.70),
        (604.0, 3.6, pitch(F, 3, 1), 0.72),
        (608.0, 3.6, pitch(G, 3, 1), 0.76),
    ], vibrato=0.28, slide_cents=18.0, snap=True)
    sb.phrase("clarinet", [
        (582.0, 1.8, pitch(EB, 5, 0), 0.56),
        (584.0, 3.4, pitch(D, 5, 0), 0.60),
        (590.0, 1.8, pitch(C, 5, 0), 0.62),
        (592.0, 3.4, pitch(BB, 4, 1), 0.64),
        (598.0, 1.8, pitch(D, 5, 0), 0.68),
        (600.0, 3.5, pitch(C, 5, 1), 0.72),
        (606.0, 1.8, pitch(C, 5, 1), 0.74),
        (608.0, 3.5, pitch(B, 4, 1), 0.78),
    ], vibrato=0.22, snap=True)

    # --- Variation 4 (612..644, k=+1, mf): Genuine 4-Voice Developing Fugato! ---
    # Voices enter successively every 2 bars (8 beats): Clarinet -> Viola -> English Horn -> Cello+Bassoon
    k1 = 1
    # Voice 1: Clarinet Subject at 612..620 + Countersubject 620..644
    sb.phrase("clarinet", [
        (612.0, 0.85, pitch(C, 4, k1), 0.64),
        (613.0, 0.85, pitch(G, 4, k1), 0.68),
        (614.0, 0.42, pitch(AB, 4, k1), 0.66),
        (614.5, 0.42, pitch(G, 4, k1), 0.64),
        (615.0, 0.85, pitch(EB, 4, k1), 0.68),
        (616.0, 1.35, pitch(BB, 4, k1 + 0), 0.70),
        (617.5, 0.42, pitch(G, 4, k1), 0.66),
        (618.0, 1.60, pitch(D, 4, k1), 0.64),
        # Breath 619.6..621.0, then lively countersubject!
        (621.0, 0.85, pitch(EB, 5, k1), 0.68),
        (622.0, 0.85, pitch(C, 5, k1), 0.66),
        (624.0, 1.80, pitch(BB, 4, k1), 0.70),
        (626.0, 1.60, pitch(G, 4, k1), 0.66),
        # Stretto 632..644
        (632.0, 0.85, pitch(G, 4, k1), 0.72),
        (633.0, 0.85, pitch(C, 5, k1), 0.74),
        (634.0, 1.70, pitch(EB, 5, k1), 0.76),
        (636.0, 1.80, pitch(C, 5, k1), 0.74),
        (638.0, 1.70, pitch(AB, 4, k1), 0.72),
        (640.0, 1.80, pitch(B, 4, k1), 0.76),
        (642.0, 1.70, pitch(D, 5, k1), 0.78),
    ], vibrato=0.18, snap=True)

    # Voice 2: Viola Answer at 620..628 + Counterpoint 628..644
    sb.phrase("viola", [
        (620.0, 0.85, pitch(EB, 4, k1), 0.66),
        (621.0, 0.85, pitch(AB, 4, k1), 0.70),
        (622.0, 0.42, pitch(G, 4, k1), 0.68),
        (622.5, 0.42, pitch(EB, 4, k1), 0.66),
        (623.0, 0.85, pitch(C, 4, k1), 0.68),
        (624.0, 1.35, pitch(G, 4, k1), 0.70),
        (625.5, 0.42, pitch(EB, 4, k1), 0.68),
        (626.0, 1.60, pitch(BB, 3, k1), 0.66),
        (628.0, 1.80, pitch(C, 4, k1), 0.68),
        (630.0, 1.80, pitch(F, 4, k1), 0.70),
        (632.5, 1.40, pitch(EB, 4, k1), 0.70),
        (634.0, 1.80, pitch(G, 4, k1), 0.72),
        (636.5, 1.40, pitch(AB, 4, k1), 0.72),
        (638.0, 1.80, pitch(EB, 4, k1), 0.70),
        (640.0, 3.60, pitch(G, 4, k1), 0.74),
    ], vibrato=0.22, snap=True)

    # Voice 3: English Horn Subject at 628..636 + Stretto 636..644
    sb.phrase("english_horn", [
        (628.0, 0.85, pitch(F, 4, k1), 0.70),
        (629.0, 0.85, pitch(AB, 4, k1), 0.74),
        (630.0, 0.42, pitch(G, 4, k1), 0.72),
        (630.5, 0.42, pitch(F, 4, k1), 0.70),
        (631.0, 0.85, pitch(C, 4, k1), 0.72),
        (632.0, 1.80, pitch(G, 4, k1), 0.74),
        (634.0, 1.70, pitch(C, 4, k1), 0.70),
        (636.0, 0.85, pitch(EB, 4, k1), 0.74),
        (637.0, 0.85, pitch(AB, 4, k1), 0.76),
        (638.0, 1.70, pitch(C, 5, k1), 0.78),
        (640.0, 1.80, pitch(G, 4, k1), 0.76),
        (642.0, 1.70, 32 + HARM_7 - OCT, 0.78),
    ], vibrato=0.24, snap=True)

    # Voice 4: Cello + Bassoon Bass Subject at 636..644 (with light pizzicato in 612..636)
    for i, sp in enumerate(v4):
        br = sp.bass_root()
        if i < 6:
            sb.note("pizzicato", sp.start, 0.42, br + OCT, 0.56)
            sb.note("pizzicato", sp.start + 2.0, 0.42, br + OCT + P5, 0.50)
        else:
            sb.note("bassoon", sp.start, 1.8, br, 0.74, swell="arch")
            sb.note("bassoon", sp.start + 2.0, 1.8, br, 0.76, swell="arch")
            sb.note("cello", sp.start, 0.85, br + OCT, 0.76)
            sb.note("cello", sp.start + 1.0, 0.85, br + OCT + P5, 0.78)
            sb.note("cello", sp.start + 2.0, 1.70, br + 2 * OCT, 0.80, vibrato=0.24)

    # --- Variation 5 (644..676, k=+1): Beethovenian Drive & Selberg Parity Barrier (f -> subito pp!) ---
    for i, sp in enumerate(v5):
        br = sp.bass_root()
        # Bars 0..5 (644..668): urgent Beethovenian motor + sfz brass!
        # Bars 6..7 (668..676): SUBITO PIANO setback (vel drops from 0.84 to 0.28!)
        if i < 6:
            dyn = 0.74 + 0.02 * i
            sb.string_pad(sp, vel=dyn * 0.84, swell="sfz" if i in (0, 4) else "arch", include_ext=False)
            sb.note("bassoon", sp.start, 1.7, br, dyn * 0.92, swell="sfz")
            sb.note("bassoon", sp.start + 2.0, 1.7, br, dyn * 0.88, swell="arch")
            if i in (0, 2, 4, 5):
                sb.note("trombone", sp.start, 2.2, br, dyn * 0.86, swell="sfz")
                sb.note("french_horn", sp.start, 2.4, sp.tenor_root() + OCT, dyn * 0.88, swell="sfz")
                sb.note("timpani", sp.start, 0.9, br, dyn * 0.88, trim=False)
                sb.note("timpani", sp.start + 1.5, 0.6, br, dyn * 0.80, trim=False)
            # Urgent eighth-note Piano + Cello motor
            pts = sp.scale_steps(pitch(C, 3), pitch(C, 5), allow_melody=False)
            for s_k in range(8):
                t = sp.start + s_k * 0.5
                acc = 1.12 if s_k in (0, 3, 4) else 0.82
                sb.note("cello", t, 0.36, br + OCT + (P5 if s_k % 2 == 1 else 0), dyn * 0.88 * acc)
                if pts:
                    sb.note("piano", t, 0.38, pts[(s_k * 2 + i) % len(pts)], dyn * 0.82 * acc, snap_to_harmony=False)
        else:
            # SUBITO PIANO Setback at 668..676! Lone tremolo whisper & desolate Clarinet sigh
            sb.string_pad(sp, vel=0.28, track_id="tremolo_strings", swell="dim", include_ext=False)
            sb.note("pizzicato", sp.start, 0.45, br + OCT, 0.30)

    sb.phrase("english_horn", [
        # Urgent Beethovenian syncopated drive in Variation 5 (644..668) before the Subito pp Barrier!
        (644.5, 1.3, pitch(G, 4, k1), 0.78),
        (646.0, 1.7, pitch(C, 5, k1), 0.82),
        (648.5, 1.3, pitch(BB, 4, k1), 0.80),
        (650.0, 1.7, pitch(G, 4, k1), 0.78),
        (652.5, 1.3, pitch(AB, 4, k1), 0.82),
        (654.0, 1.7, pitch(C, 5, k1), 0.85),
        (656.5, 1.3, pitch(BB, 4, k1), 0.84),
        (658.0, 1.7, pitch(EB, 4, k1), 0.80),
        (660.5, 1.3, pitch(AB, 4, k1), 0.86),
        (662.0, 1.7, pitch(F, 4, k1), 0.84),
        (664.5, 1.3, pitch(G, 4, k1), 0.88),
        (666.0, 1.6, pitch(EB, 4, k1), 0.86),
    ], swell="sfz", vibrato=0.24, snap=True)

    sb.phrase("clarinet", [
        (668.5, 2.8, pitch(EB, 4, k1), 0.32),
        (672.0, 3.4, pitch(D, 4, k1), 0.28),
    ], swell="dim", vibrato=0.16, snap=True)

    # --- Variation 6 (676..708, k=+1 -> +2, pp -> f): Persistent Rebuilding & Second Comma Lift! ---
    for i, sp in enumerate(v6):
        br = sp.bass_root()
        dyn = 0.36 + 0.06 * i  # Climbs steadily from 0.36 pp back up to 0.78 f!
        sb.add_pedal(sp.start, 3.84)
        sb.string_pad(sp, vel=dyn * 0.84, swell="cresc", include_ext=True)
        sb.note("bassoon", sp.start, 3.6, br, dyn * 0.90, swell="cresc")
        sb.harp_arp(sp, sp.start, pitch(C, 3), pitch(A, 5), vel=dyn * 0.94, spacing=0.16, note_dur=2.1, ascending=True, max_notes=9)
        if i >= 4:
            sb.note("french_horn", sp.start, 3.6, sp.tenor_root() + P5, dyn * 0.90, swell="cresc", vibrato=0.18)
        if i == 7:
            sb.timpani_roll(sp.start + 1.0, 2.8, br, 0.50, 0.80, subdiv=0.25)

    sb.phrase("english_horn", [
        (676.5, 3.2, pitch(G, 4, 1), 0.42),
        (680.5, 3.2, pitch(BB, 4, 1), 0.48),
        (684.5, 3.2, pitch(C, 5, 1), 0.54),
        (688.5, 3.2, pitch(BB, 4, 1), 0.60),
        (692.5, 3.2, pitch(B, 4, 1), 0.66),
        (696.5, 3.2, pitch(A, 4, 2), 0.72),     # Pivot onto k=+2!
        (700.5, 3.2, pitch(C, 5, 2), 0.78),
        (704.5, 3.2, pitch(D, 5, 2), 0.82),
    ], swell="cresc", vibrato=0.28, slide_cents=16.0, snap=True)

    # --- Variation 7 (708..740, k=+2, f): Montgomery–Odlyzko Pair Correlation (GUE Repulsion!) ---
    # Irregular non-colliding syncopated offsets [0.0, 0.75, 1.75, 2.5, 3.25] (level spacing repulsion!)
    gue_offsets = [0.0, 0.75, 1.75, 2.50, 3.25]
    for i, sp in enumerate(v7):
        br = sp.bass_root()
        dyn = 0.74 + 0.015 * (i % 4)
        # Trombone + French Horn intone the Passacaglia Pillar in solemn sustained augmentation!
        sb.note("trombone", sp.start, 3.7, br, dyn * 0.86, swell="arch")
        sb.note("french_horn", sp.start, 3.7, sp.tenor_root() + OCT, dyn * 0.88, swell="arch", vibrato=0.16)
        sb.note("bassoon", sp.start, 3.7, br, dyn * 0.88, swell="arch")
        pts = sp.scale_steps(pitch(D, 3), pitch(F, 5), allow_melody=False)
        for g_idx, off in enumerate(gue_offsets):
            if pts:
                st_a = pts[(g_idx * 3 + i) % len(pts)]
                st_b = pts[(g_idx * 3 + i + 2) % len(pts)]
                sb.note("piano", sp.start + off, 0.52, st_a, dyn * 0.86, snap_to_harmony=False)
                sb.note("pizzicato", sp.start + off, 0.38, st_b, dyn * 0.80, snap_to_harmony=False)
                if g_idx in (1, 3):
                    sb.note("clarinet", sp.start + off, 0.58, st_a + OCT if st_a < 25 else st_a, dyn * 0.88, snap_to_harmony=False)
                else:
                    sb.note("viola", sp.start + off, 0.58, st_b, dyn * 0.84, snap_to_harmony=False)

    # --- Variation 8 (740..772, k=+2 -> +3, f -> ff): Third Upward Comma Ascent to Summit k=+3! ---
    for i, sp in enumerate(v8):
        br = sp.bass_root()
        dyn = 0.78 + 0.02 * i
        sb.string_pad(sp, vel=dyn * 0.90, swell="cresc", include_ext=True)
        sb.string_pad(sp, vel=dyn * 0.76, track_id="tremolo_strings", swell="cresc", include_ext=False)
        sb.note("bassoon", sp.start, 3.7, br, dyn * 0.92, swell="cresc")
        sb.note("trombone", sp.start, 3.7, br, dyn * 0.90, swell="cresc")
        sb.note("french_horn", sp.start, 3.7, sp.tenor_root() + P5, dyn * 0.92, swell="cresc")
        sb.harp_arp(sp, sp.start, pitch(C, 3), pitch(C, 6), vel=dyn * 0.94, spacing=0.13, note_dur=2.2, ascending=(i % 2 == 0), max_notes=10)
        for q in range(4):
            sb.note("cello", sp.start + q, 0.82, br + OCT + (P5 if q % 2 == 1 else 0), dyn * 0.92, vibrato=0.22)
        if i in (0, 4, 6, 7):
            sb.note("timpani", sp.start, 1.5, br, dyn * 0.90, trim=False)
        if i == 7:
            sb.timpani_roll(sp.start + 1.5, 2.4, br, 0.76, 0.94, subdiv=0.25)

    # Soaring Clarinet + English Horn octave-apart ascent to k=+3!
    v8_mel = [(sp.start, 1.8, sp.nearest_step(pitch(G, 4, 2) + i * 3, allow_melody=False), 0.84 + 0.015 * i) for i, sp in enumerate(v8)]
    v8_mel2 = [(sp.start + 2.0, 1.8, sp.nearest_step(pitch(C, 5, 2) + i * 2, allow_melody=False), 0.86 + 0.015 * i) for i, sp in enumerate(v8)]
    full_v8_mel = sorted(v8_mel + v8_mel2, key=lambda x: x[0])
    sb.phrase("clarinet", full_v8_mel, swell="cresc", vibrato=0.22, snap=False)
    sb.phrase("english_horn", [(b, d, st - OCT if st > 48 else st, v * 0.94) for b, d, st, v in full_v8_mel if int(b) % 8 != 4], vibrato=0.24, snap=False)

    # --- Variation 9 (772..804, k=+3, ff): Heroic Brucknerian Struggle on the k=+3 Summit ---
    for i, sp in enumerate(v9):
        br = sp.bass_root()
        dyn = 0.88 + 0.01 * min(i, 6)
        sb.string_pad(sp, vel=dyn * 0.90, swell="sfz" if i % 2 == 0 else "arch", include_ext=True)
        sb.string_pad(sp, vel=dyn * 0.80, track_id="tremolo_strings", swell="arch", include_ext=False)
        sb.note("bassoon", sp.start, 3.7, br, dyn * 0.94, swell="sfz")
        sb.note("trombone", sp.start, 3.7, br, dyn * 0.92, swell="sfz")
        sb.note("trombone", sp.start + 0.1, 3.5, sp.tenor_root() + P5, dyn * 0.86, swell="arch")
        sb.note("french_horn", sp.start, 1.8, sp.tenor_root() + OCT, dyn * 0.94, swell="sfz")
        sb.note("french_horn", sp.start + 2.0, 1.8, sp.tenor_root() + OCT + (m3 if "min" in sp.quality else M3), dyn * 0.92, swell="arch")
        sb.note("timpani", sp.start, 1.2, br, dyn * 0.92, trim=False)
        sb.note("timpani", sp.start + 2.5, 0.8, br, dyn * 0.86, trim=False)
        # Thunderous Piano octave/fifth summit chords
        tr_r = sp.tenor_root()
        sb.chord("piano", sp.start, 1.6, [tr_r, tr_r + P5, tr_r + OCT], dyn * 0.88)
        sb.chord("piano", sp.start + 2.0, 1.6, [tr_r + P5, tr_r + OCT, tr_r + OCT + P5], dyn * 0.86)

    # Passionate Clarinet + Viola Summit Counterpoint straining at k=+3 in Variation 9 (772..804)
    k3 = 3
    sb.phrase("clarinet", [
        (772.0, 1.8, pitch(C, 5, k3), 0.88),
        (774.0, 1.8, pitch(EB, 5, k3), 0.92),
        (776.0, 3.6, pitch(D, 5, k3), 0.90),
        (780.5, 1.4, pitch(C, 5, k3), 0.90),
        (782.0, 1.8, pitch(EB, 5, k3), 0.94),
        (784.0, 3.6, pitch(BB, 4, k3), 0.90),
        # Breath 787.6..788.5
        (788.5, 1.4, pitch(AB, 4, k3), 0.90),
        (790.0, 1.8, pitch(C, 5, k3), 0.94),
        (792.0, 3.6, pitch(G, 5, k3), 0.95),
        (796.5, 3.2, pitch(EB, 5, k3), 0.94),
        (800.0, 3.6, pitch(D, 5, k3), 0.95),
    ], swell="sfz", vibrato=0.24, snap=True)
    sb.phrase("viola", [
        (772.0, 3.6, pitch(G, 4, k3), 0.86),
        (776.0, 3.6, pitch(BB, 4, k3), 0.88),
        (780.0, 3.6, pitch(AB, 4, k3), 0.88),
        (784.0, 3.6, pitch(G, 4, k3), 0.88),
        (788.0, 3.6, pitch(F, 4, k3), 0.90),
        (792.0, 3.6, pitch(EB, 4, k3), 0.90),
        (796.0, 3.6, pitch(C, 5, k3), 0.92),
        (800.0, 3.6, pitch(B, 4, k3), 0.92),
    ], vibrato=0.26, snap=True)

    # --- Variation 10 (804..836, k=+3, mf -> pp cliffhanger): One Step Shy of Truth! ---
    for i, sp in enumerate(v10):
        dur = sp.end - sp.start
        br = sp.bass_root()
        dyn = [0.64, 0.58, 0.52, 0.48, 0.44, 0.36][i]
        sb.string_pad(sp, vel=dyn * 0.84, track_id="tremolo_strings", swell="dim" if i == 5 else "arch", include_ext=False)
        if i <= 4:
            sb.note("bassoon", sp.start, dur - 0.3, br, dyn * 0.90, swell="dim")
            sb.note("cello", sp.start, dur - 0.3, br + OCT, dyn * 0.92, swell="dim", vibrato=0.28)
        else:
            # Final unresolved G+++ dom7 (root = 34: [34, 51, 12, 24]) hanging in suspense!
            sb.timpani_roll(sp.start, dur - 0.4, br, 0.38, 0.24, subdiv=0.32)
            sb.note("bassoon", sp.start, dur - 0.5, br, 0.36, swell="dim")
            # English Horn & Viola freeze on the unresolved septimal seventh step 24!
            sb.note("english_horn", sp.start + 0.5, dur - 0.9, 24, 0.44, swell="dim", vibrato=0.30, snap_to_harmony=False)
            sb.note("viola", sp.start + 1.0, dur - 1.4, 51 - OCT, 0.38, swell="dim", vibrato=0.22, snap_to_harmony=False)


# =============================================================================
# MOVEMENT IV — THE PROOF: AI & THE CRITICAL LINE (Beats 836..1100, 11:30 – 15:00)
# =============================================================================
def compose_movement_4(sb: RiemannSymphonyBuilder) -> None:
    sb.add_section(836.0, "IV. The Proof: AI & The Critical Line — 1. Hyper-Parallel Algorithmic Lattice")
    sb.add_section(908.0, "IV.2 Symmetry Lock & Convergence onto Home Comma Plane k = 0")
    sb.add_section(964.0, "IV.3 PROOF APOTHEOSIS — Cathedral Pipe Organ & Triple Thematic Unification")
    sb.add_section(1044.0, "IV.4 Q.E.D. — Beat-Free Stillness on the Critical Line Re(s) = 1/2")

    m4_specs = [
        # IV.1 (836..908, 18 bars x 4 beats): Rapid Algorithmic Search Scanning Across Comma Planes!
        # Bridges directly from Mvt III's unresolved pitch 24 into F++ maj(24)!
        (836.0, 840.0, 24, "maj", "IV.1.1 Lattice Scan F++(k=+2)"),
        (840.0, 844.0, 10, "min7", "IV.1.2 Lattice Scan Dm+(k=+2)"),
        (844.0, 848.0, 45, "maj9", "IV.1.3 Lattice Scan Bb+(k=+1)"),
        (848.0, 852.0, 31, "min7", "IV.1.4 Lattice Scan Gm(k=+1)"),
        (852.0, 856.0, 14, "maj9", "IV.1.5 Lattice Scan Eb(k=0)"),
        (856.0, 860.0, 0, "min9", "IV.1.6 Lattice Scan Cm9(k=0)"),
        (860.0, 864.0, 36, "maj7", "IV.1.7 Lattice Scan Ab(k=0)"),
        (864.0, 868.0, 19, "maj", "IV.1.8 Diesis Probe E-(19)"),
        (868.0, 872.0, 2, "add9", "IV.1.9 Diesis Probe C++(k=+2)"),
        (872.0, 876.0, 33, "min7", "IV.1.10 Lattice Scan Gm++(k=+2)"),
        (876.0, 880.0, 24, "maj7", "IV.1.11 Lattice Scan F++(k=+2)"),
        (880.0, 884.0, 32, "dom7", "IV.1.12 Comma Lock Step V7+(k=+1)"),
        (884.0, 888.0, 1, "add9", "IV.1.13 Lattice Scan C+(k=+1)"),
        (888.0, 892.0, 40, "min7", "IV.1.14 Lattice Scan Am7+(k=+1)"),
        (892.0, 896.0, 23, "maj9", "IV.1.15 Lattice Scan F+(k=+1)"),
        (896.0, 900.0, 9, "min7", "IV.1.16 Comma Lock Step ii(9)"),
        (900.0, 904.0, 31, "dom9", "IV.1.17 Target Acquired: G dom9(k=0!)"),
        (904.0, 908.0, 0, "prime13", "IV.1.18 Prime Spectrum Verified on k=0!"),
        # IV.2 (908..964, 14 bars x 4 beats): Symmetry Lock & Pre-Apotheosis Surge onto k=0!
        (908.0, 912.0, C, "mirror_maj", "IV.2.1 Mirror Invariant C(k=0)"),
        (912.0, 916.0, A, "mirror_min", "IV.2.2 Mirror Invariant Am(k=0)"),
        (916.0, 920.0, F, "mirror_maj", "IV.2.3 Mirror Invariant F(k=0)"),
        (920.0, 924.0, G, "dom9", "IV.2.4 Septimal Lock G dom9"),
        (924.0, 928.0, E, "min7", "IV.2.5 Rising Tide Em7"),
        (928.0, 932.0, A, "min9", "IV.2.6 Rising Tide Am9"),
        (932.0, 936.0, D_MINUS, "min7", "IV.2.7 Rising Tide Dm-7"),
        (936.0, 940.0, G, "dom7", "IV.2.8 Rising Tide G dom7"),
        (940.0, 948.0, F, "maj9", "IV.2.9 Pre-Apotheosis Subdominant Pillar F maj9"),
        (948.0, 956.0, G, "sus4", "IV.2.10 Dominant Tension G sus4"),
        (956.0, 964.0, G, "dom9", "IV.2.11 Blazing Dominant Herald G dom9(4:5:6:7:9)"),
        # IV.3 (964..1044, 20 bars = 80 beats, Home k=0): CATHEDRAL PIPE ORGAN PROOF APOTHEOSIS!
        (964.0, 968.0, C, "add9", "IV.3.1 ORGAN ENTRY: Transfigured Major Passacaglia I (C add9)"),
        (968.0, 972.0, G, "maj", "IV.3.2 Apotheosis V (G maj)"),
        (972.0, 976.0, A, "min9", "IV.3.3 Apotheosis vi (Am9)"),
        (976.0, 980.0, E, "min7", "IV.3.4 Apotheosis iii (Em7)"),
        (980.0, 984.0, F, "maj9", "IV.3.5 Apotheosis IV (F maj9)"),
        (984.0, 988.0, C, "mirror_maj", "IV.3.6 Apotheosis Mirror I (C maj7)"),
        (988.0, 992.0, D_MINUS, "min9", "IV.3.7 Apotheosis ii (Dm-9)"),
        (992.0, 996.0, G, "dom9", "IV.3.8 Apotheosis V9 (4:5:6:7:9)"),
        (996.0, 1000.0, AB, "maj7", "IV.3.9 Heroic Brucknerian Blaze bVI (Ab maj7)"),
        (1000.0, 1004.0, G, "dom9", "IV.3.10 Roaring Cadential V9"),
        # Second Grand Wave of IV.3 (1004..1044):
        (1004.0, 1012.0, C, "mirror_maj", "IV.3.11 Triple-Theme Crown I (C maj9)"),
        (1012.0, 1020.0, F, "maj9", "IV.3.12 Cathedral Subdominant Expanse IV (F maj9)"),
        (1020.0, 1028.0, A, "min9", "IV.3.13 Luminous Mediant vi (Am9)"),
        (1028.0, 1036.0, G, "dom9", "IV.3.14 Ultimate Symphonic Climax V9 (4:5:6:7:9)"),
        (1036.0, 1044.0, C, "add9", "IV.3.15 Proof Resolution: Exact Home k=0 (C add9)"),
        # IV.4 (1044..1100, 56 beats, Home k=0): Q.E.D. — Beat-Free Stillness on Re(s) = 1/2
        (1044.0, 1052.0, F, "maj9", "IV.4.1 Plagal Halo I (F maj9 / C pedal)", C),
        (1052.0, 1060.0, C, "mirror_maj", "IV.4.2 Final Mirror Farewell (C maj7)"),
        (1060.0, 1068.0, F, "add9", "IV.4.3 Plagal Halo II (F add9 / C pedal)", C),
        (1068.0, 1080.0, C, "add9", "IV.4.4 Organ Fade into Pure Resonance (C add9)"),
        (1080.0, 1100.0, C, "maj", "IV.4.5 Q.E.D. — Beatless 4:5:6 Critical Line Stillness"),
    ]
    spans = [sb.add_span(*c) for c in m4_specs]

    # --- IV.1 (836..908): Crystalline 16th-Note Hyper-Parallel Algorithmic Lattice (pp -> mf) ---
    # Dry, razor-sharp Piano 16th-notes (0.25 beat) + interlocking Harp + Pizzicato + Clarinet + Viola!
    lattice_perms = [
        (0, 2, 4, 1, 3, 5, 2, 4, 6, 3, 5, 1, 4, 2, 5, 3),
        (0, 3, 1, 4, 2, 5, 3, 6, 4, 1, 5, 2, 6, 3, 4, 1),
        (5, 3, 1, 0, 2, 4, 6, 4, 2, 1, 3, 5, 4, 2, 0, 3),
        (1, 4, 2, 5, 0, 3, 6, 2, 4, 1, 5, 3, 0, 4, 2, 6),
    ]
    for i, sp in enumerate(spans[:18]):
        u = i / 17.0
        dyn = 0.34 + 0.24 * (u ** 1.1)  # Grows cleanly from 0.34 pp crystal to 0.58 mf!
        pts = sp.scale_steps(pitch(C, 3), pitch(A, 5), allow_melody=False)
        perm = lattice_perms[i % len(lattice_perms)]
        if pts:
            for s16 in range(16):
                t = sp.start + s16 * 0.25
                st_p = pts[(perm[s16] + i) % len(pts)]
                acc = 1.08 if s16 % 4 == 0 else (0.96 if s16 % 2 == 0 else 0.84)
                # Short crisp dur=0.42 keeps piano polyphony <= 3!
                sb.note("piano", t, 0.42, st_p, dyn * acc, snap_to_harmony=False)

            # Interlocking Harp counter-lattice on 8th-note offbeats (max 8 notes per bar -> poly <= 7)
            for s8 in range(8):
                t_h = sp.start + s8 * 0.5 + 0.125
                st_h = pts[(len(pts) - 1 - ((s8 * 2 + i) % len(pts)))]
                sb.note("harp", t_h, 0.85, st_h, dyn * 0.92, snap_to_harmony=False)

        # Prime-grid Pizzicato & Pointillistic Clarinet/Viola algorithmic probes
        br = sp.bass_root()
        sb.note("pizzicato", sp.start, 0.35, br + OCT, dyn * 0.95)
        sb.note("pizzicato", sp.start + 1.75, 0.35, br + OCT + P5, dyn * 0.85)
        sb.note("pizzicato", sp.start + 3.0, 0.35, br + OCT, dyn * 0.88)
        if i % 2 == 0 and len(pts) >= 4:
            sb.phrase("clarinet", [
                (sp.start + 0.5, 0.65, pts[-2], dyn + 0.06),
                (sp.start + 1.25, 0.45, pts[-3], dyn + 0.04),
                (sp.start + 2.0, 1.30, pts[-1], dyn + 0.10),
            ], swell="arch", snap=False)
        elif len(pts) >= 4:
            sb.phrase("viola", [
                (sp.start + 0.25, 0.65, pts[1], dyn + 0.06),
                (sp.start + 1.0, 0.65, pts[2], dyn + 0.08),
                (sp.start + 2.25, 1.30, pts[3], dyn + 0.10),
            ], swell="arch", snap=False)
        if i >= 12:
            sb.note("cello", sp.start, 3.6, br + OCT, dyn * 0.92, swell="cresc")

    # --- IV.2 (908..964): Symmetry Lock & Pre-Apotheosis Surge onto Home k=0 (mf -> ff) ---
    lock_spans = spans[18:29]
    for i, sp in enumerate(lock_spans):
        dur = sp.end - sp.start
        dyn = 0.60 + 0.032 * i  # Surges 0.60 -> 0.92 ff!
        br = sp.bass_root()
        sb.add_pedal(sp.start, dur - 0.16)
        sb.string_pad(sp, vel=dyn * 0.88, swell="cresc", include_ext=True)
        if i >= 6:
            sb.string_pad(sp, vel=dyn * 0.80, track_id="tremolo_strings", swell="cresc", include_ext=False)
            sb.note("trombone", sp.start, dur - 0.25, br, dyn * 0.88, swell="cresc")
            sb.note("french_horn", sp.start, dur - 0.25, sp.tenor_root() + P5, dyn * 0.90, swell="cresc")
        sb.note("bassoon", sp.start, dur - 0.25, br, dyn * 0.92, swell="cresc")
        sb.harp_arp(sp, sp.start, pitch(C, 3), pitch(C, 6), vel=dyn * 0.94, spacing=0.14, note_dur=2.0, ascending=(i % 2 == 0), max_notes=10)

        # Mirror lock verification in bars 0..2 (908..920): English Horn + Cello lock S - u!
        if i < 3:
            S = sp.mirror_sum(center_oct=4)
            u_targets = [(pitch(E, 4), pitch(G, 4)), (pitch(C, 5), pitch(E, 4)), (pitch(F, 4), pitch(A, 4))][i]
            u1 = sp.nearest_step(u_targets[0], allow_melody=False)
            u2 = sp.nearest_step(u_targets[1], allow_melody=False)
            sb.note("english_horn", sp.start, 1.8, u1, dyn + 0.06, swell="arch", vibrato=0.26, snap_to_harmony=False)
            sb.note("cello", sp.start, 1.8, S - u1, dyn + 0.06, swell="arch", vibrato=0.26, snap_to_harmony=False)
            sb.note("english_horn", sp.start + 2.0, 1.8, u2, dyn + 0.08, swell="arch", vibrato=0.26, snap_to_harmony=False)
            sb.note("cello", sp.start + 2.0, 1.8, S - u2, dyn + 0.08, swell="arch", vibrato=0.26, snap_to_harmony=False)

    # Roaring Dominant Herald Timpani Roll & Fanfare (948..964 -> Organ Entry!)
    sb.timpani_roll(948.0, 7.6, pitch(G, 2), 0.62, 0.82, subdiv=0.25)
    sb.timpani_roll(956.0, 7.8, pitch(G, 2), 0.82, 0.96, subdiv=0.25)
    sb.phrase("clarinet", [
        (940.5, 3.2, pitch(A, 4), 0.78),
        (944.0, 3.6, pitch(C, 5), 0.82),
        (948.5, 3.2, pitch(C, 5), 0.86),
        (952.0, 3.6, pitch(D, 5), 0.90),
        (956.0, 1.8, pitch(B, 4), 0.92),
        (958.0, 1.8, 31 + HARM_7, 0.94),
        (960.0, 3.7, pitch(D, 5), 0.96),
    ], swell="cresc", vibrato=0.22)

    # --- IV.3 (964..1044): CATHEDRAL PIPE ORGAN & TRIPLE-THEME PROOF APOTHEOSIS (Home k=0!) ---
    # church_organ enters FOR THE VERY FIRST TIME at beat 964.0!
    apoth_spans = spans[29:44]
    for i, sp in enumerate(apoth_spans):
        dur = sp.end - sp.start
        br = sp.bass_root()
        tr_r = sp.tenor_root()
        q_third = m3 if "min" in sp.quality else M3
        # Smooth grand dynamic contour peaking at i=13 (G dom9 Ultimate Climax at 1028..1036, vel=0.95)
        ov = 0.74 + 0.20 * math.sin(math.pi * min(1.0, (i + 1) / 14.5))
        if i == 14:
            ov = 0.86

        # 1. Cathedral Pipe Organ (wide beat-free 5-voice cathedral registration: C2..E5)
        org_voic = [br, br + OCT, tr_r + P5, tr_r + OCT, tr_r + OCT + q_third]
        sb.chord("church_organ", sp.start, dur - 0.14, org_voic, ov, swell="cresc" if i == 13 else "arch")

        # 2. Orchestral Strings + Brass + Bassoon + Pedaled Piano + Sweeping Harp
        # Omit M7 in string_pad when church_organ & french_horn sustain tr_r + OCT so zero M7-vs-OCT semitone grinds occur!
        use_ext = sp.quality not in ("maj7", "mirror_maj")
        sb.string_pad(sp, vel=ov * 0.92, swell="arch", include_ext=use_ext)
        if i in (0, 7, 8, 9, 10, 13, 14):
            sb.string_pad(sp, vel=ov * 0.78, track_id="tremolo_strings", swell="arch", include_ext=False)
        sb.note("bassoon", sp.start, dur - 0.20, br, ov * 0.92, swell="arch")
        sb.note("trombone", sp.start, dur - 0.22, br, ov * 0.90, swell="sfz" if i in (0, 10, 13) else "arch")
        sb.note("french_horn", sp.start, dur * 0.5 - 0.15, tr_r + P5, ov * 0.92, swell="arch")
        sb.note("french_horn", sp.start + dur * 0.5, dur * 0.5 - 0.20, tr_r + OCT, ov * 0.94, swell="arch", vibrato=0.18)

        sb.add_pedal(sp.start, dur - 0.16)
        pts_p = sp.scale_steps(pitch(C, 3), pitch(G, 5), allow_melody=False)
        step_p = 0.5
        tp = sp.start
        pi_k = 0
        while tp < sp.end - 0.10 and pts_p:
            sb.note("piano", tp, 0.65, pts_p[(pi_k * 2 + i) % len(pts_p)], ov * 0.82, snap_to_harmony=False)
            tp += step_p
            pi_k += 1

        sb.harp_arp(sp, sp.start, pitch(C, 3), pitch(C, 6), vel=ov * 0.94, spacing=0.14, note_dur=2.4, ascending=(i % 2 == 0), max_notes=11)
        if dur >= 7.5:
            sb.harp_arp(sp, sp.start + 4.0, pitch(C, 3), pitch(C, 6), vel=ov * 0.90, spacing=0.15, note_dur=2.4, ascending=False, max_notes=10)

        # 53-EDO Timpani punctuating the transfigured Major Passacaglia pillars!
        if i in (0, 1, 7, 8, 9, 10, 13, 14):
            sb.note("timpani", sp.start, 1.4, br, ov * 0.92, trim=False)
            if i == 13:
                sb.timpani_roll(sp.start + 4.0, 3.8, br, 0.84, 0.96, subdiv=0.25)

    # SIMULTANEOUS TRIPLE-THEME CONTRAPUNTAL UNIFICATION IN IV.3 (964..1044):
    #   (A) Clarinet soars at the top with the PRIME MOTIF (Mvt I: 1:1 -> 5:4 -> 3:2 -> 7:4 -> 2:1 -> 9:4)!
    #   (B) English Horn & Cello sing the MIRROR COUNTERPOINT (Mvt II: S - u symmetry on C mirror_maj)!
    #   (C) Organ/Trombone/Bassoon/Viola carry the Transfigured PASSACAGLIA PILLAR (Mvt III)!
    sb.phrase("clarinet", [
        # Cycle A (964..1004): Prime Motif blazing in C Major!
        (964.0, 1.35, pitch(C, 5), 0.88),
        (965.5, 0.45, pitch(D, 5), 0.86),
        (966.0, 1.85, pitch(E, 5), 0.92),
        (968.0, 1.80, pitch(G, 5), 0.94),
        (970.0, 1.80, pitch(D, 5), 0.90),
        (972.0, 1.80, pitch(E, 5), 0.90),
        (974.0, 1.80, pitch(C, 5), 0.88),
        # Breath 975.8..976.5
        (976.5, 1.40, pitch(B, 4), 0.88),
        (978.0, 1.80, pitch(E, 5), 0.90),
        (980.0, 1.80, pitch(C, 5), 0.92),
        (982.0, 1.80, pitch(A, 4), 0.88),
        (984.0, 1.80, pitch(E, 5), 0.92),
        (986.0, 1.80, pitch(G, 5), 0.94),
        # Breath 987.8..988.5
        (988.5, 1.40, pitch(F, 5), 0.90),
        (990.0, 1.80, pitch(D_MINUS, 5), 0.88),
        (992.0, 1.80, pitch(D, 5), 0.92),
        (994.0, 1.80, 31 + HARM_7, 0.94),         # Septimal 7:4 Prime-7 crown!
        (996.0, 1.80, pitch(EB, 5), 0.94),
        (998.0, 1.80, pitch(C, 5), 0.92),
        (1000.0, 1.80, pitch(D, 5), 0.94),
        (1002.0, 1.80, pitch(B, 4), 0.92),
        # Cycle B (1004..1044): Grand Broadened Crown!
        (1004.0, 2.6, pitch(C, 5), 0.92),
        (1007.0, 1.0, pitch(E, 5), 0.94),
        (1008.0, 3.6, pitch(G, 5), 0.95),
        # Breath 1011.6..1012.5
        (1012.5, 3.2, pitch(E, 5), 0.92),
        (1016.0, 3.6, pitch(C, 5), 0.90),
        (1020.5, 3.2, pitch(E, 5), 0.92),
        (1024.0, 3.6, pitch(C, 5), 0.90),
        # Ultimate Septimal Climax 1028..1036 -> Home C5 1036..1044!
        (1028.0, 1.8, pitch(G, 5), 0.96),
        (1030.0, 1.8, 31 + HARM_7, 0.95),
        (1032.0, 1.8, pitch(D, 5), 0.94),
        (1034.0, 1.8, pitch(B, 4), 0.92),
        (1036.0, 7.4, pitch(E, 5), 0.94),         # Pure 5:4 Major Third Crown!
    ], vibrato=0.24, snap=True)

    # English Horn & Cello Mirror Duet inside IV.3 (exact S=48 reflection on 984..988 & 1004..1012!)
    sb.note("english_horn", 984.0, 1.8, pitch(E, 4), 0.88, swell="arch", vibrato=0.28, snap_to_harmony=False)
    sb.note("cello", 984.0, 1.8, pitch(G, 4) - OCT, 0.88, swell="arch", vibrato=0.28, snap_to_harmony=False)
    sb.note("english_horn", 986.0, 1.8, pitch(A, 4), 0.90, swell="arch", vibrato=0.28, snap_to_harmony=False)
    sb.note("cello", 986.0, 1.8, pitch(D, 4), 0.90, swell="arch", vibrato=0.28, snap_to_harmony=False)

    # Broad 8-beat Mirror Theme at 1004..1012 (sum = -5 exact: E4(17)+G3(-22)=-5, A4(39)+D3(-44)=-5, G4(31)+E3(-36)=-5, B4(48)+C3(-53)=-5!)
    for m_off, u_st in [(0.0, 17), (2.0, 39), (4.0, 31), (6.0, 48)]:
        l_st = -5 - u_st
        sb.note("english_horn", 1004.0 + m_off, 1.85, u_st, 0.92, swell="arch", vibrato=0.28, snap_to_harmony=False)
        sb.note("cello", 1004.0 + m_off, 1.85, l_st, 0.92, swell="arch", vibrato=0.28, snap_to_harmony=False)

    # Singing Cello & Viola arches across the rest of IV.3
    sb.phrase("viola", [
        (964.0, 3.6, pitch(G, 4), 0.84),
        (968.0, 3.6, pitch(D, 4), 0.84),
        (972.0, 3.6, pitch(C, 4), 0.84),
        (976.0, 3.6, pitch(G, 4), 0.84),
        (980.0, 3.6, pitch(A, 4), 0.86),
        (988.0, 3.6, pitch(A, 4), 0.86),
        (992.0, 3.6, pitch(G, 4), 0.88),
        (996.0, 3.6, pitch(EB, 4), 0.88),
        (1000.0, 3.6, pitch(G, 4), 0.90),
        (1012.0, 7.5, pitch(A, 4), 0.88),
        (1020.0, 7.5, pitch(E, 4), 0.88),
        (1028.0, 7.5, pitch(G, 4), 0.92),
        (1036.0, 7.5, pitch(G, 4), 0.88),
    ], vibrato=0.24, snap=True)

    # --- IV.4 (1044..1100): Q.E.D. — Beat-Free Stillness on Re(s) = 1/2 (mf -> pp) ---
    coda_spans = spans[44:]
    coda_dyn = [0.62, 0.54, 0.48, 0.44, 0.40]
    for i, sp in enumerate(coda_spans):
        dur = sp.end - sp.start
        v = coda_dyn[i]
        br = sp.bass_root()   # Pure C2 (-106) tonic pedal throughout the entire coda!
        sb.add_pedal(sp.start, dur - 0.25)
        sb.string_pad(sp, vel=v * 0.88, swell="dim", include_ext=False, trim_tail=0.35)
        if i <= 3:
            # Pipe Organ gently recedes into cathedral silence before the final unaccompanied string/harp halo
            org_coda = [br, br + OCT, pitch(G, 3), pitch(E, 4) if i in (1, 3) else pitch(A, 4)]
            sb.chord("church_organ", sp.start, dur - 0.85, org_coda, v * 0.85, swell="dim")
            sb.note("bassoon", sp.start, dur - 0.90, br, v * 0.88, swell="dim")
        else:
            sb.note("french_horn", sp.start + 0.5, 9.0, pitch(G, 3), v * 0.84, swell="dim")
            sb.note("french_horn", sp.start + 10.5, 8.8, pitch(G, 3), v * 0.78, swell="dim")
        sb.harp_arp(
            sp,
            sp.start + 0.4,
            pitch(C, 3),
            pitch(G, 5),
            vel=v + 0.08,
            spacing=0.30 + 0.05 * i,
            note_dur=3.8,
            ascending=True,
            max_notes=9 - i,
        )

    # Final Mirror Farewell at 1052..1060 (E4=17 <-> G4=31, D4=9 <-> A4=39 -> C4=0 / C5=53!)
    sb.note("english_horn", 1052.5, 3.4, pitch(G, 4), 0.50, swell="dim", vibrato=0.24, snap_to_harmony=False)
    sb.note("cello", 1052.5, 3.4, pitch(E, 4), 0.50, swell="dim", vibrato=0.24, snap_to_harmony=False)
    sb.note("english_horn", 1056.2, 3.4, pitch(E, 4), 0.46, swell="dim", vibrato=0.20, snap_to_harmony=False)
    sb.note("cello", 1056.2, 3.4, pitch(G, 4) - OCT, 0.46, swell="dim", vibrato=0.20, snap_to_harmony=False)

    # Final Prime Overtones (1:1, 2:1, 3:2, 5:4) ringing into eternity at 1080..1100!
    final_bells = [
        (1081.0, 6.0, pitch(C, 4), 0.44),
        (1084.0, 6.0, pitch(G, 4), 0.42),
        (1087.0, 6.0, pitch(C, 5), 0.40),
        (1090.5, 6.5, pitch(E, 5), 0.39),
        (1094.0, 6.0, pitch(G, 5), 0.38),   # Ends at exact beat 1100.0 -> + 5.0s hall tail = 900.0s!
    ]
    for b, d, st, v in final_bells:
        sb.note("piano", b, d, st, v, snap_to_harmony=False, trim=False)
    sb.note("cello", 1080.0, 19.5, pitch(C, 3), 0.42, swell="dim", snap_to_harmony=False, trim=False)


# =============================================================================
# Build & Self-Validate the Complete 15-Minute Symphony
# =============================================================================
def compose_riemann_symphony() -> Tuple[RiemannSymphonyBuilder, Dict]:
    # Exact analytical piecewise-linear tempo map calibrated so:
    #   Mvt I   (0..264)    = 0:00 – 3:45 (~225s)
    #   Mvt II  (264..516)  = 3:45 – 7:30 (~225s)
    #   Mvt III (516..836)  = 7:30 – 11:30 (~240s)
    #   Mvt IV  (836..1100) = 11:30 – 14:55 active + 5.0s hall tail = 15:00 (900.0s)!
    tempo_segments = [
        # Movement I: The Primes (264 beats -> ~225.0s, avg ~70.4 BPM)
        (0.0, 64.5),
        (60.0, 69.5),
        (132.0, 76.5),
        (204.0, 73.5),
        (263.99, 62.5),
        # Movement II: Analytic Continuation (252 beats -> ~225.0s, avg ~67.2 BPM)
        (264.0, 66.0),
        (320.0, 67.5),
        (384.0, 69.0),
        (420.0, 72.5),
        (456.0, 67.5),
        (515.99, 59.0),
        # Movement III: A Century of Small Progress (320 beats -> ~240.0s, avg ~80.0 BPM)
        (516.0, 72.5),
        (612.0, 79.5),
        (708.0, 86.5),
        (772.0, 89.5),
        (804.0, 78.0),
        (835.99, 64.0),
        # Movement IV: The Proof: AI & The Critical Line (264 beats -> ~206.0s + 5.0s tail = 211.0s)
        (836.0, 95.0),
        (908.0, 97.0),
        (963.99, 82.0),
        (964.0, 73.0),
        (1044.0, 66.5),
        (1100.0, 54.0),
    ]

    sb = RiemannSymphonyBuilder(tempo_segments)
    compose_movement_1(sb)
    compose_movement_2(sb)
    compose_movement_3(sb)
    compose_movement_4(sb)

    score = sb.build_dict()
    return sb, score


def validate_riemann_score(sb: RiemannSymphonyBuilder, score: Dict) -> None:
    errors: List[str] = []

    # 1. Pure stage-independence check
    for forbidden in ("reverb_rt60", "tail_seconds", "end_silence_seconds"):
        if forbidden in score:
            errors.append(f"Top-level score must omit '{forbidden}'")
    for tr in score["tracks"]:
        for forbidden in ("x", "y", "width", "gain", "warm_lowpass_hz"):
            if forbidden in tr:
                errors.append(f"Track '{tr['id']}' must omit inline '{forbidden}'")
        if tr["id"] == "church_organ":
            if not tr["notes"]:
                errors.append("church_organ has 0 notes!")
            elif tr["notes"][0]["beat"] < 960.0:
                errors.append(f"church_organ entered prematurely at beat {tr['notes'][0]['beat']}")

    # 2. Duration & movement boundary verification
    m_beats = [0.0, 264.0, 516.0, 836.0, 1100.0]
    m_secs = [sb.tempo.beat_to_seconds(b) for b in m_beats]
    total_dur = m_secs[-1] + 5.0
    print("Movement Timestamps:")
    names = [
        "I.   The Primes",
        "II.  Analytic Continuation",
        "III. A Century of Small Progress",
        "IV.  The Proof: AI & The Critical Line",
    ]
    for i, nm in enumerate(names):
        s0, s1 = m_secs[i], m_secs[i + 1] + (5.0 if i == 3 else 0.0)
        print(
            f"  {nm:<40} beat {m_beats[i]:6.1f}..{m_beats[i + 1]:6.1f} | "
            f"{int(s0 // 60)}:{s0 % 60:05.2f} – {int(s1 // 60)}:{s1 % 60:05.2f} ({s1 - s0:.1f}s)"
        )
    print(f"Total Concert Hall Duration (with 5.0s tail): {total_dur:.2f}s ({int(total_dur // 60)}:{total_dur % 60:05.2f})")
    if not (885.0 <= total_dur <= 915.0):
        errors.append(f"Total duration {total_dur:.2f}s outside required 885..915s window!")

    if errors:
        for e in errors:
            print("ERROR:", e)
        raise SystemExit(1)


def main() -> None:
    sb, score = compose_riemann_symphony()
    validate_riemann_score(sb, score)

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = os.path.join(repo_root, "scores", "riemann_hypothesis_15min.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(score, f, indent=2)
    total_notes = sum(len(t["notes"]) for t in score["tracks"])
    print(f"Wrote {out_path} ({os.path.getsize(out_path) / 1024:.1f} KB, {total_notes} notes)")


if __name__ == "__main__":
    main()
