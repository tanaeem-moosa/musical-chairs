#!/usr/bin/env python3
"""
Compose a ~15-minute (900s) 4-movement 53-EDO orchestral & bamboo-synth symphony:
  "Ode to the Riemann Hypothesis — Symphony in 53-EDO" (v2)

Four Programmatic Movements & Signature Musical Structures:
  I.   The Primes (Curiosity) (~0:00–3:28, brisk playful 118 -> 136 -> 114 BPM):
       Bright, mercurial, chamber-led prime-harmonic awakening (4:5:6:7:9:11, steps
       0, 17, 31, 43, 9, 24), asymmetric 5-beat & 7-beat hockets, Sieve of Eratosthenes,
       and Euler Product convergence (trombone & church_organ tacet, zero dark drones).
       Forges STRUCTURE 1 (The Prime Curiosity Hook): recurring 6-note rising/skipping
       prime-harmonic motif [+0, +9, +17, +31, +43, +53] in a snappy 2+3+2 prime rhythm.

  II.  Analytic Continuation (Through the Mirror) (~3:28–6:58, 88 -> 114 -> 66 BPM):
       Wonder-struck, weightless crossing of the Re(s) = 1 pole via both 53-EDO common-tone
       diesis rotations (0 -> 17 -> 34 -> 51 and 0 -> 36 -> 19 -> 2), surging in fluid
       rubato waves to 114 BPM at the Critical Line before hushing to 66 BPM for the
       First Nontrivial Zero (t_1 = 14.1347).
       Forges STRUCTURE 2 (The Functional Mirror Wedge, xi(s) = xi(1 - s)): upper winds
       (flute/clarinet) and lower strings (cello/viola) diverge and reconverge in exact
       53-EDO pitch inversion (u + l = S) inside a 28-bar time-retrograde palindrome.

  III. A Century of Small Progress (~6:58–11:25, 72 -> 104 -> 136 -> 60 BPM):
       Preserves the ~8:00 C-minor Passacaglia core (STRUCTURE 3A) and the monumental
       Unresolved Summit freeze on G+++7 (step 24), sharpened with dramatic speed surges
       across the century (72 -> 104 -> 122 -> [74 subito pp Selberg barrier] -> 136 ->
       60 BPM), bold STRUCTURE 3B (Montgomery–Odlyzko Pair-Correlation Riff [0.0, 0.75,
       1.75, 2.50, 3.25]), and fracturing human attempts to overlay Structures 1 & 2.

  IV.  AI, Unified Triumph & Melancholy for Humanity (~11:25–15:00, 152 -> 168 -> 122 -> 52 BPM):
       Introduces two synthetic-timbre Bamboo Flute (shakuhachi) AI voices (ai_strip &
       ai_architect, strictly tacet in Mvts I–III, steps 31..124 = G4–E6, vibrato 0.0,
       swell "none"):
         - IV.1 (152 BPM): Solo ai_strip zero-free-strip sprint cracking the step-24 wall.
         - IV.2 (168 BPM): ai_architect + ai_strip full synthesis snap-fitting Structure 1
           inside Structure 2 and locking onto Structures 3B + 3A down k = +3 -> +2 -> +1 -> 0.
         - IV.3 (122 BPM Maestoso): church_organ enters for the first time with full orchestra
           + AI synth-flutes in radiant 53-EDO C Major (4:5:6:7:9), uniting Structures 1, 2, 3.
         - IV.4 (52 BPM Adagio malinconico): Brass, timpani, and organ fall silent. High above,
           ai_architect hums an untroubled, beatless 53-EDO fifth/seventh halo while lone human
           cello & english_horn (vibrato 0.78, ppp–mp vel 0.26..0.38) sing an aching 16:15 &
           -1 comma farewell to Structures 1 & 3A with sparse CC 64 piano teardrops.

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
PRIME_19 = 13    # 19:16 19th-harmonic / -1 comma minor third (294.34c)
m3 = 14          # 6:5 pure minor third (316.98c)
M3_MINUS = 16    # 5:4 shifted by -1 comma (362.26c)
M3 = 17          # 5:4 pure major third — Prime 5! (384.91c)
P4 = 22          # 4:3 pure fourth (498.11c)
PRIME_11 = 24    # 11:8 11th-harmonic — Prime 11! (543.40c)
P5 = 31          # 3:2 pure fifth — Prime 3! (701.89c)
m6_MINUS = 35    # 8:5 shifted by -1 comma / 128:81 (792.45c)
m6 = 36          # 8:5 pure minor sixth (815.09c)
PRIME_13 = 37    # 13:8 13th-harmonic — Prime 13! (837.74c)
M6 = 39          # 5:3 pure major sixth (883.02c; A4 = 440.00 Hz)
HARM_7 = 43      # 7:4 septimal seventh — Prime 7! (973.58c)
JUST_m7 = 45     # 9:5 pure minor seventh (1018.87c)
M7 = 48          # 15:8 pure major seventh (1086.79c)

# Reference pitch classes on Home Comma Plane k = 0
C = 0
DB = 5
D_MINUS = 8
D = 9
EB_MINUS = 13
EB = 14
E_MINUS = 16
E = 17
F = 22
G = 31
AB_MINUS = 35
AB = 36
A = 39
BB_HARM = 43
BB = 44
B = 48

# Signature Structure Constants
PRIME_HOOK_OFFSETS: Tuple[int, ...] = (0, M2, M3, P5, HARM_7, OCT)          # [+0, +9, +17, +31, +43, +53]
PRIME_HOOK_MAJ_OFFSETS: Tuple[int, ...] = (0, M2, M3, P5, M6, OCT)          # [+0, +9, +17, +31, +39, +53]
PAIR_CORR_OFFSETS: Tuple[float, ...] = (0.0, 0.75, 1.75, 2.50, 3.25)        # Structure 3B GUE level repulsion

PRIMES_UP_TO_60 = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59]
PRIME_SET = set(PRIMES_UP_TO_60)

HUMAN_WINDS_BRASS = {"flute", "clarinet", "english_horn", "bassoon", "french_horn", "trombone"}
AI_SYNTH_TRACKS = {"ai_strip", "ai_architect"}
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
# Pure 5/7/11/13-Limit, Mirror-Symmetric & Comma-Sigh Templates (min mod53 >= 4!)
# =============================================================================
CHORD_TEMPLATES: Dict[str, Tuple[int, ...]] = {
    "open5": (0, P5),
    "maj": (0, M3, P5),
    "add9": (0, M2, M3, P5),
    "maj69": (0, M2, M3, P5, M6),
    "maj7": (0, M3, P5, M7),
    "maj9": (0, M2, M3, P5, M7),
    "mirror_maj": (0, M2, M3, P5, M6, M7),       # Self-dual under x -> 2R + 48 - x!
    "min": (0, m3, P5),
    "min7": (0, m3, P5, JUST_m7),
    "min9": (0, M2, m3, P5, JUST_m7),
    "mirror_min": (0, M2, m3, P5, m6, JUST_m7),  # Self-dual under x -> 2R + 45 - x!
    "dom7": (0, M3, P5, HARM_7),
    "dom9": (0, M2, M3, P5, HARM_7),             # 4:5:6:7:9 — exact host for Structure 1!
    "sus2": (0, M2, P5),
    "sus4": (0, P4, P5),
    "prime7": (0, M3, P5, HARM_7),
    "prime11": (0, M2, M3, PRIME_11, P5, HARM_7),  # 4:5:6:7:9:11 (steps 0,9,17,24,31,43)!
    "prime13": (0, M2, M3, PRIME_11, P5, PRIME_13, HARM_7),
    "prime17_19": (0, SEMI, PRIME_19, M3, PRIME_11, P5, PRIME_13, HARM_7),
    # IV.4 Melancholy for Humanity: high AI {0, 31, 43} halo + human 16:15 & -1 comma sighs!
    "halo_maj_sigh": (0, M3_MINUS, P5, HARM_7),              # {0, 16, 31, 43} (-1 comma M3 sigh)
    "halo_phryg": (0, SEMI, m3, P4, P5, m6, HARM_7),         # {0, 5, 14, 22, 31, 36, 43} (16:15 + minor + P4)
    "halo_comma_sigh": (0, PRIME_19, P5, m6_MINUS, HARM_7),  # {0, 13, 31, 35, 43} (-1 comma m3/m6 sigh)
}

MELODY_EXTRA: Dict[str, Tuple[int, ...]] = {
    "open5": (M2, M3, M6),
    "maj": (M2, P4, M6, M7),
    "add9": (P4, M6, M7),
    "maj69": (P4, M7),
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
    "prime11": (M6,),
    "prime13": (),
    "prime17_19": (),
    "halo_maj_sigh": (M2,),
    "halo_phryg": (),
    "halo_comma_sigh": (M2,),
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
        if q in ("min", "min7", "min9", "mirror_min", "halo_phryg", "halo_comma_sigh"):
            th = PRIME_19 if q == "halo_comma_sigh" else m3
            if include_ext and q == "min9":
                return [r, r + m3, r + P5, r + JUST_m7, r + OCT + M2]
            v = [r, r + P5, r + OCT + th]
            if include_ext and q in ("min7", "mirror_min"):
                v.insert(2, r + JUST_m7)
            return sorted(v)
        if q == "halo_maj_sigh":
            return [r, r + P5, r + OCT + M3_MINUS]
        if q == "sus4":
            return [r, r + P5, r + OCT + P4]
        if q == "sus2":
            return [r, r + P5, r + OCT + M2]
        if q in ("dom7", "dom9", "prime7", "prime11", "prime13", "prime17_19"):
            v = [r, r + P5, r + HARM_7, r + OCT + M3]
            if include_ext and q in ("prime11", "prime13", "prime17_19"):
                v.append(r + OCT + PRIME_11)
            return sorted(v)
        if include_ext and q in ("add9", "maj69", "maj9"):
            return [r, r + M3, r + P5, r + OCT + M2]
        if include_ext and q in ("maj7", "mirror_maj"):
            return [r, r + M3, r + P5, r + M7]
        return [r, r + P5, r + OCT + M3]

    def scale_steps(self, low_step: int, high_step: int, allow_melody: bool = False) -> List[int]:
        pcs = self.melody_pcs if allow_melody else self.chord_pcs
        return [s for s in range(low_step, high_step + 1) if (s % OCT) in pcs]

    def mirror_sum_wedge(self) -> int:
        """
        Exact 53-EDO reflection sum S for Structure 2 (Functional Mirror Wedge)
        such that upper winds u in [G4..E5] <-> lower strings S - u in [G3..E4] (>= C3)!
        On C mirror_maj: S = 48 (G4=31 <-> E4=17 [dist 14], E5=70 <-> G3=-22 [dist 92]).
        On A mirror_min: r = -14 -> 2*(-14) + 45 + 53 = 70? Let's anchor S near 42..54!
        """
        r = self.root_pc
        if r > 26:
            r -= OCT
        base = (2 * r + JUST_m7) if self.quality in ("min", "min7", "min9", "mirror_min") else (2 * r + M7)
        while base < 32:
            base += OCT
        while base > 64:
            base -= OCT
        return base


# =============================================================================
# Analytical TempoMap (exact match to Rust src/score.rs)
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


@dataclass
class TrackSpec:
    id: str
    name: str
    instrument: str
    notes: List[Dict] = field(default_factory=list)
    pedals: List[Dict[str, float]] = field(default_factory=list)


# =============================================================================
# Stage-Independent Orchestral & Bamboo-Synth Symphony Builder
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
            TrackSpec("flute", "Concert Flute", "flute"),
            TrackSpec("clarinet", "Solo Clarinet", "clarinet"),
            TrackSpec("english_horn", "English Horn", "english_horn"),
            TrackSpec("bassoon", "Solo Bassoon", "bassoon"),
            TrackSpec("french_horn", "French Horns", "french_horn"),
            TrackSpec("trombone", "Symphonic Trombones", "trombone"),
            TrackSpec("viola", "Solo Viola", "viola"),
            TrackSpec("cello", "Solo Cello", "cello"),
            TrackSpec("string_ensemble", "String Orchestra", "string_ensemble"),
            TrackSpec("tremolo_strings", "Tremolo Strings", "tremolo_strings"),
            TrackSpec("timpani", "53-EDO Timpani", "timpani"),
            TrackSpec("church_organ", "Cathedral Pipe Organ", "church_organ"),
            TrackSpec("ai_strip", "The Herald (Zero-Free Strip)", "shakuhachi"),
            TrackSpec("ai_architect", "The Oracle (Critical Line)", "shakuhachi"),
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
                    end = min(end, sp.start - 0.10)
                    break
                if is_low and sp.bass_root() != cur_bass:
                    diff = abs(sp.bass_root() - step)
                    if 0 < diff < P4:
                        end = min(end, sp.start - 0.16)
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
        max_step_override: Optional[int] = None,
    ) -> None:
        tr = self.tracks[track_id]
        strict = track_id in STRICT_CHORD_TRACKS
        if allow_melody is None:
            allow_melody = not strict

        sp = self.span_at(beat)
        if snap_to_harmony and track_id != "timpani":
            step = sp.nearest_step(step, allow_melody=allow_melody)

        # Idiomatic sweet-spot register guardrails per track (preserving exact pitch class mod 53!)
        sweet_high = {
            "ai_strip": 124,       # G4..E6 (31..124)
            "ai_architect": 124,   # G4..E6 (31..124)
            "flute": 106,          # C4..C6 (0..106, inside C4..D6)
            "clarinet": 70,        # E3..E5 (-36..70)
            "english_horn": 53,    # F3..C5 (-31..53)
            "viola": 53,           # C3..C5 (-53..53)
            "cello": 31,           # C2..G4 (-106..31)
            "french_horn": 31,     # G2..G4 (-75..31)
            "trombone": 0,         # E2..C4 (-89..0)
            "bassoon": 0,          # C2..C4 (-106..0)
            "timpani": 0,          # C2..C4 (-106..0)
            "church_organ": 53,    # C2..C5 (-106..53)
            "harp": 106,           # C3..C6 (-53..106)
            "piano": 92,           # C2..A5 (-106..92)
            "pizzicato": 70,       # C3..E5 (-53..70)
            "string_ensemble": 84,
            "tremolo_strings": 84,
        }
        sweet_low = {
            "ai_strip": 31,        # Strictly >= G4 (31)!
            "ai_architect": 31,    # Strictly >= G4 (31)!
            "flute": 0,            # Strictly >= C4 (0)!
            "clarinet": -36,
            "english_horn": -31,
            "viola": -53,
            "pizzicato": -53,
            "harp": -53,
            "string_ensemble": -53,
            "tremolo_strings": -53,
            "french_horn": -67,
            "trombone": -89,
            "cello": -106,
            "bassoon": -106,
            "timpani": -106,
            "church_organ": -106,
            "piano": -106,
        }
        if max_step_override is not None:
            while step > max_step_override:
                step -= OCT
        elif track_id in sweet_high:
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
                lo_ok = sweet_low.get(track_id, -106)
                if track_id in ("bassoon", "trombone", "church_organ", "cello") and br >= lo_ok:
                    step = br
                else:
                    step += OCT

        if trim:
            dur = self._safe_dur(track_id, beat, dur, step)

        # AI synth-flutes MUST stay synthetic/cool: vibrato = 0.0, swell = "none"
        if track_id in AI_SYNTH_TRACKS:
            vibrato = 0.0
            swell = "none"
        elif swell is None and tr.instrument in HUMAN_WINDS_BRASS and dur >= 0.45:
            swell = "arch"

        # True wide musical velocity mapping (0.15 .. 0.94): preserves whispered ppp halo/veil
        # in IV.4 (0.16..0.23) beneath human soloists (0.28..0.40) and ff blaze in IV.3 (0.88..0.94)!
        v = max(0.15, min(0.94, float(vel)))
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
        if track_id in AI_SYNTH_TRACKS:
            entry["swell"] = "none"
        elif swell is not None and swell != "none":
            entry["swell"] = swell
        if vibrato > 1e-3 and track_id not in AI_SYNTH_TRACKS:
            entry["vibrato"] = round(min(0.90, vibrato), 3)
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
            w = 1.0 if i in (0, n - 1) else 0.92
            self.note(
                track_id,
                beat + i * roll,
                max(0.10, dur - i * roll),
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
            arch = 0.95 + 0.09 * math.sin(math.pi * (u ** 0.85))
            sl = 0.0
            if slide_cents > 0.0 and i > 0 and d >= 0.70:
                pb, pd, pst, _ = events[i - 1]
                diff = st - pst
                if 1 <= abs(diff) <= 24 and (b - (pb + pd)) <= 0.35:
                    sl = -slide_cents if diff > 0 else slide_cents * 0.88
            vib = vibrato if d >= 0.75 else (vibrato * 0.50 if d >= 0.45 else 0.0)
            sw = swell
            if sw is None and track_id not in AI_SYNTH_TRACKS:
                if i == n - 1 and d >= 1.5:
                    sw = "dim"
                elif self.tracks[track_id].instrument in HUMAN_WINDS_BRASS or d >= 1.0:
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

    def emit_prime_hook(
        self,
        track_id: str,
        beat: float,
        base_step: int,
        vel: float,
        *,
        unit: float = 0.5,
        use_septimal: bool = True,
        staccato: bool = True,
        vibrato: float = 0.14,
        swell: Optional[str] = None,
        snap: bool = False,
    ) -> None:
        """
        STRUCTURE 1 — The Prime Curiosity Hook:
        6-note rising/skipping prime-harmonic motif [+0, +9, +17, +31, +43, +53]
        in an unmistakable 2+3+2 = 7-unit prime rhythm:
          Group 1 (2u): +0 (1u), +9 (1u)
          Group 2 (3u): +17 (1u), +31 (1u), +43 (1u)
          Group 3 (2u): +53 (2u summit crown!)
        """
        offs = PRIME_HOOK_OFFSETS if use_septimal else PRIME_HOOK_MAJ_OFFSETS
        rel_onsets = (0.0, 1.0, 2.0, 3.0, 4.0, 5.0)
        rel_durs = (
            (0.68, 0.68, 0.68, 0.68, 0.72, 1.72)
            if staccato
            else (0.88, 0.88, 0.88, 0.88, 0.90, 1.82)
        )
        accents = (1.02, 0.90, 1.04, 0.93, 0.96, 1.08)
        for off_iv, ro, rd, acc in zip(offs, rel_onsets, rel_durs, accents):
            t = beat + ro * unit
            d = rd * unit
            sw = swell
            if track_id in AI_SYNTH_TRACKS:
                sw = "none"
            elif sw is None and ro < 5.0 and d < 0.55:
                sw = "none"
            self.note(
                track_id,
                t,
                d,
                base_step + off_iv,
                vel * acc,
                swell=sw,
                vibrato=(vibrato if ro == 5.0 and track_id not in AI_SYNTH_TRACKS else 0.0),
                snap_to_harmony=snap,
            )

    def emit_mirror_wedge_bar(
        self,
        span: ChordSpan,
        upper_track: str,
        lower_track: str,
        vel: float,
        *,
        diverging: bool = True,
        retrograde: bool = False,
        S_override: Optional[int] = None,
        vibrato: float = 0.24,
    ) -> None:
        """
        STRUCTURE 2 — The Functional Mirror Wedge (xi(s) = xi(1 - s)):
        Upper voice plays u(t) while lower voice plays exact S - u(t) so u + l == S!
        Diverging bar opens from pure 3rd (14..17 steps) out to wide 10th/12th;
        reconverging bar closes symmetrically back to pure 3rd!
        """
        S = S_override if S_override is not None else span.mirror_sum_wedge()
        # Pick clean chord tones in [S//2 + 6 .. S//2 + 46] so u > l with gap >= 12 steps!
        half = S // 2
        u_cands = span.scale_steps(half + 6, half + 48, allow_melody=False)
        valid_u = []
        for u in u_cands:
            l = S - u
            if ((l % OCT) in span.chord_pcs) and (u - l >= 12) and (l >= -48):
                valid_u.append(u)
        if len(valid_u) < 3:
            # Fallback using nearest chord steps preserving >= 12-step separation
            for raw_d in (8, 16, 24, 34):
                u = span.nearest_step(half + raw_d, allow_melody=False)
                l = span.nearest_step(S - u, allow_melody=False)
                if u - l >= 12 and l >= -48:
                    valid_u.append(u)
        if not valid_u:
            return
        pts = valid_u[:4]
        while len(pts) < 4:
            pts.append(pts[-1])
        seq_u = pts if diverging else list(reversed(pts))
        raw_rhythm = [(0.0, 0.90), (1.0, 0.90), (2.0, 0.90), (3.0, 0.90)]
        if retrograde:
            seq_u = list(reversed(seq_u))

        for (off, dur), u_st in zip(raw_rhythm, seq_u):
            l_st = S - u_st
            if (l_st % OCT) not in span.chord_pcs:
                l_st = span.nearest_step(l_st, allow_melody=False)
            t = span.start + off
            if t >= span.end - 0.12:
                break
            self.note(
                upper_track,
                t,
                dur,
                u_st,
                vel,
                swell="none" if upper_track in AI_SYNTH_TRACKS else "arch",
                vibrato=0.0 if upper_track in AI_SYNTH_TRACKS else vibrato,
                snap_to_harmony=False,
            )
            self.note(
                lower_track,
                t,
                dur,
                l_st,
                vel * 0.95,
                swell="none" if lower_track in AI_SYNTH_TRACKS else "arch",
                vibrato=0.0 if lower_track in AI_SYNTH_TRACKS else vibrato,
                snap_to_harmony=False,
            )

    def emit_pair_correlation_riff(
        self,
        span: ChordSpan,
        track_id: str,
        steps_cycle: Sequence[int],
        vel: float,
        *,
        dur: float = 0.42,
        swell: Optional[str] = None,
    ) -> None:
        """
        STRUCTURE 3B — Montgomery–Odlyzko Pair-Correlation Riff:
        Bold GUE level-repulsion syncopated cell [0.0, 0.75, 1.75, 2.50, 3.25].
        """
        if not steps_cycle:
            return
        accents = (1.06, 0.94, 1.04, 0.92, 1.02)
        for idx, (off, acc) in enumerate(zip(PAIR_CORR_OFFSETS, accents)):
            t = span.start + off
            if t >= span.end - 0.10:
                break
            st = steps_cycle[idx % len(steps_cycle)]
            self.note(
                track_id,
                t,
                dur,
                st,
                vel * acc,
                swell=swell,
                snap_to_harmony=False,
                trim=(track_id != "timpani"),
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
        dur = max(0.28, (span.end - span.start) - trim_tail)
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
        note_dur: float = 1.4,
        ascending: bool = True,
        max_notes: int = 8,
    ) -> None:
        pts_raw = span.scale_steps(max(-53, low_step), min(106, high_step), allow_melody=False)
        if note_dur >= 0.8:
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
        n = len(pts)
        for i, st in enumerate(pts):
            t = beat + i * spacing
            if t >= span.end - 0.12:
                break
            u = i / max(1, n - 1)
            shape = 0.93 + 0.14 * math.sin(math.pi * u)
            nd = min(note_dur, span.end - t - 0.10)
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
            accent = 1.05 if i in (0, steps_n - 1) else (0.94 + 0.04 * (i % 2))
            self.note("timpani", beat + i * subdiv, subdiv * 0.90, step, v * accent, trim=False)

    def build_dict(self) -> Dict:
        tracks_json = []
        for tr in self.tracks.values():
            cleaned_notes = []
            for n in tr.notes:
                if tr.id != "timpani":
                    n["dur"] = round(
                        self._safe_dur(tr.id, n["beat"], n["dur"], n["step"]), 4
                    )
                cleaned_notes.append(n)
            cleaned_notes.sort(key=lambda x: (x["beat"], x["step"]))

            # Enforce human wind & brass breathing gaps (>= 0.85 beats at least every <= 14.5 beats)
            if tr.instrument in HUMAN_WINDS_BRASS and cleaned_notes:
                for _pass in range(96):
                    ivs = sorted((n["beat"], n["beat"] + n["dur"]) for n in cleaned_notes)
                    merged: List[Tuple[float, float]] = []
                    for b0, e0 in ivs:
                        if merged and b0 - merged[-1][1] < 0.80:
                            merged[-1] = (merged[-1][0], max(merged[-1][1], e0))
                        else:
                            merged.append((b0, e0))
                    over = [(b0, e0) for b0, e0 in merged if (e0 - b0) > 14.5]
                    if not over:
                        break
                    mb0, _me0 = over[0]
                    target_cut = mb0 + 12.0
                    onsets = sorted({
                        n["beat"] for n in cleaned_notes
                        if mb0 + 7.5 <= n["beat"] <= mb0 + 14.4
                    })
                    cut_b = min(onsets, key=lambda x: abs(x - target_cut)) if onsets else round(target_cut, 2)
                    breath_end = cut_b - 0.88
                    kept_breath = []
                    changed = False
                    for n in cleaned_notes:
                        nb = n["beat"]
                        ne = nb + n["dur"]
                        if breath_end - 0.18 <= nb < cut_b - 0.02:
                            # Clear short pickup/riff note inside the 0.88-beat breath window
                            changed = True
                            continue
                        if nb < breath_end - 0.18 and ne > breath_end:
                            new_d = max(0.22, breath_end - nb)
                            if new_d < n["dur"] - 1e-4:
                                n["dur"] = round(new_d, 4)
                                if n.get("swell") in (None, "arch"):
                                    n["swell"] = "dim"
                                changed = True
                        kept_breath.append(n)
                    cleaned_notes = kept_breath
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

        # Precision Semitone-Rub & Transparency Resolver:
        # Guarantees ZERO sustained 4..=6-step narrow-second rubs (> 0.35b) across ALL
        # non-percussive tracks while protecting primary thematic voices!
        priority = {
            "ai_strip": 100,
            "ai_architect": 99,
            "english_horn": 95,
            "clarinet": 94,
            "flute": 93,
            "cello": 92,
            "church_organ": 90,
            "viola": 82,
            "french_horn": 80,
            "trombone": 78,
            "bassoon": 76,
            "piano": 65,
            "pizzicato": 60,
            "harp": 50,
            "string_ensemble": 30,
            "tremolo_strings": 25,
        }
        for _rub_pass in range(8):
            all_refs: List[Tuple[float, float, int, int, str, int, Dict]] = []
            for ti, t_obj in enumerate(tracks_json):
                if t_obj["instrument"] == "timpani":
                    continue
                tid = t_obj["id"]
                pr = priority.get(tid, 50)
                for ni, n in enumerate(t_obj["notes"]):
                    all_refs.append((n["beat"], n["beat"] + n["dur"], n["step"], pr, tid, ti, n))
            all_refs.sort(key=lambda x: x[0])

            to_drop: Set[Tuple[int, int]] = set()
            any_fix = False
            for idx_a in range(len(all_refs)):
                b_a, e_a, st_a, pr_a, tid_a, ti_a, n_a = all_refs[idx_a]
                if (ti_a, id(n_a)) in to_drop:
                    continue
                for idx_b in range(idx_a + 1, len(all_refs)):
                    b_b, e_b, st_b, pr_b, tid_b, ti_b, n_b = all_refs[idx_b]
                    if b_b >= e_a - 0.32:
                        break
                    if (ti_b, id(n_b)) in to_drop:
                        continue
                    step_diff = abs(st_a - st_b)
                    if 1 <= step_diff <= 6:
                        ov_s = max(b_a, b_b)
                        ov_e = min(e_a, e_b)
                        if ov_e - ov_s > 0.32:
                            # Modify lower-priority note (or earlier tail if equal priority)
                            if (pr_a, b_a) <= (pr_b, b_b):
                                victim_n, victim_ti, cut_at = n_a, ti_a, ov_s + 0.24
                            else:
                                victim_n, victim_ti, cut_at = n_b, ti_b, ov_s + 0.24
                            new_dur = cut_at - victim_n["beat"]
                            if new_dur >= 0.14 and victim_n["beat"] < ov_s - 0.05:
                                victim_n["dur"] = round(new_dur, 4)
                                if victim_n is n_a:
                                    e_a = victim_n["beat"] + victim_n["dur"]
                                any_fix = True
                            else:
                                to_drop.add((victim_ti, id(victim_n)))
                                any_fix = True
                                if victim_n is n_a:
                                    break
            if to_drop:
                for ti, t_obj in enumerate(tracks_json):
                    t_obj["notes"] = [
                        n for n in t_obj["notes"] if (ti, id(n)) not in to_drop
                    ]
            if not any_fix:
                break

        return {
            "title": "Ode to the Riemann Hypothesis — Symphony in 53-EDO",
            "description": (
                "A ~15-minute (900s) stage-independent 4-movement 53-EDO symphony (52–168 BPM): "
                "I. The Primes (Curiosity: playful 118–136 BPM chamber colors, 4:5:6:7:9:11 bright "
                "harmonies, 5 & 7-beat hockets, Sieve of Eratosthenes & Structure 1 Prime Curiosity Hook); "
                "II. Analytic Continuation (Through the Mirror: 88–114–66 BPM rubato waves, both 53-EDO "
                "diesis rotations, Structure 2 Functional Mirror Wedge xi(s)=xi(1-s) & palindrome, First "
                "Nontrivial Zero); III. A Century of Small Progress (72–136–60 BPM: C-minor Passacaglia "
                "Structure 3A, Fugato, Selberg subito pp barrier, Structure 3B Montgomery–Odlyzko Pair-"
                "Correlation Riff, fracturing human motifs & G+++7 step-24 Unresolved Summit); IV. The Herald, "
                "The Oracle, Triumph & Melancholy for Humanity (Bamboo-Synth shakuhachi The Herald & The Oracle "
                "at 152 & 168 BPM snap-fitting all structures, 122 BPM Cathedral Pipe Organ + tutti Proof "
                "Triumph, and 52 BPM ppp–mp human cello/english_horn 16:15 & -1 comma farewell beneath "
                "an eternal beatless 53-EDO harmonic halo)."
            ),
            "sample_rate": 48000,
            "sections": sorted(self.sections, key=lambda s: s["beat"]),
            "tempo": self.tempo.to_json(),
            "tracks": tracks_json,
        }


# =============================================================================
# MOVEMENT I — THE PRIMES (CURIOSITY) (Beats 0..440, ~0:00 – 3:28, 118->136->114 BPM)
# Playful, bright, mercurial chamber sparkle; trombone & church_organ TACET!
# =============================================================================
def compose_movement_1(sb: RiemannSymphonyBuilder) -> None:
    sb.add_section(0.0, "I.1 The Primes (Curiosity) — Prime Curiosity Hook & Asymmetric 5+7 Groove")
    sb.add_section(108.0, "I.2 Sieve of Eratosthenes — 5 & 7-Beat Hockets & Higher Primes (11, 13, 17, 19)")
    sb.add_section(228.0, "I.3 The Euler Product — Sparkling Chamber-Orchestral Convergence (k = 0 -> +1 -> 0)")
    sb.add_section(348.0, "I.4 Asymptotic Mystery (x / ln x) & Shimmering Portal to Re(s) = 1")

    m1_specs = [
        # I.1 (0..108): 9 playful prime cycles of (7 beats + 5 beats = 12 beats)!
        # Cycle 1 (0..12)
        (0.0, 7.0, C, "dom9", "I.1.1a Prime Curiosity Hook I (C 4:5:6:7:9)"),
        (7.0, 12.0, G, "dom9", "I.1.1b 5-Beat Answer (G 4:5:6:7:9)"),
        # Cycle 2 (12..24)
        (12.0, 19.0, G, "dom9", "I.1.2a Prime Hook on G (G dom9)"),
        (19.0, 24.0, C, "add9", "I.1.2b 5-Beat Bounce (C add9)"),
        # Cycle 3 (24..36)
        (24.0, 31.0, C, "prime11", "I.1.3a Overtone 11 Awakening (C 4:5:6:7:9:11)"),
        (31.0, 36.0, F, "maj69", "I.1.3b Subdominant Dance (F maj69)"),
        # Cycle 4 (36..48)
        (36.0, 43.0, C, "dom9", "I.1.4a Broad 7-Beat Prime Hook (C dom9)"),
        (43.0, 48.0, D, "dom9", "I.1.4b Bright V/V Sparkle (D dom9)"),
        # Cycle 5 (48..60)
        (48.0, 55.0, G, "prime11", "I.1.5a Dominant Prime-11 (G 4:5:6:7:9:11)"),
        (55.0, 60.0, C, "maj69", "I.1.5b Luminous Tonic (C maj69)"),
        # Cycle 6 (60..72)
        (60.0, 67.0, C, "prime11", "I.1.6a Prime-11 Hook (C prime11)"),
        (67.0, 72.0, A, "min7", "I.1.6b Playful Relative Dance (Am7)"),
        # Cycle 7 (72..84)
        (72.0, 79.0, F, "dom9", "I.1.7a Septimal Subdominant Hook (F dom9)"),
        (79.0, 84.0, G, "dom9", "I.1.7b Dominant Skip (G dom9)"),
        # Cycle 8 (84..96)
        (84.0, 91.0, C, "dom9", "I.1.8a Canon Hook I (C dom9)"),
        (91.0, 96.0, E, "min7", "I.1.8b Mediant Skip (Em7)"),
        # Cycle 9 (96..108)
        (96.0, 103.0, G, "dom9", "I.1.9a Canon Hook II (G dom9)"),
        (103.0, 108.0, C, "prime11", "I.1.9b Cadential Prime-11 Spark (C prime11)"),

        # I.2 (108..228): Sieve of Eratosthenes — 10 cycles of (7 + 5 = 12 beats)!
        (108.0, 115.0, C, "prime11", "I.2.1a Sieve Launch (C prime11)"),
        (115.0, 120.0, G, "prime11", "I.2.1b Sieve G prime11"),
        (120.0, 127.0, C, "prime13", "I.2.2a Prime 13 Harmonic (+37)"),
        (127.0, 132.0, F, "prime11", "I.2.2b F prime11"),
        (132.0, 139.0, C, "dom9", "I.2.3a Flute Prime Hook in the Sieve"),
        (139.0, 144.0, D, "dom9", "I.2.3b D dom9"),
        (144.0, 151.0, G, "prime13", "I.2.4a G Prime-13 Constellation"),
        (151.0, 156.0, C, "maj69", "I.2.4b C maj69"),
        (156.0, 163.0, C, "prime17_19", "I.2.5a Primes 17 (+5) & 19 (+13) Exotic Sparkle"),
        (163.0, 168.0, G, "dom9", "I.2.5b G dom9"),
        (168.0, 175.0, F, "dom9", "I.2.6a Clarinet Prime Hook on F"),
        (175.0, 180.0, C, "add9", "I.2.6b C add9"),
        (180.0, 187.0, A, "min9", "I.2.7a Nimble Minor Hocket (Am9)"),
        (187.0, 192.0, D, "dom9", "I.2.7b D dom9"),
        (192.0, 199.0, G, "dom9", "I.2.8a Dominant Hocket (G dom9)"),
        (199.0, 204.0, C, "prime11", "I.2.8b C prime11"),
        (204.0, 211.0, C, "dom9", "I.2.9a Double-Woodwind Prime Hook"),
        (211.0, 216.0, F, "maj69", "I.2.9b F maj69"),
        (216.0, 223.0, G, "dom9", "I.2.10a Pre-Euler Bounce (G dom9)"),
        (223.0, 228.0, C, "add9", "I.2.10b Bright Launchpad (C add9)"),

        # I.3 (228..348): Euler Product — 15 brisk 8-beat bars with Upward Comma Lift k=0->+1->0!
        (228.0, 236.0, C, "dom9", "I.3.1 Euler Product Launch (C dom9)"),
        (236.0, 244.0, G, "dom9", "I.3.2 Euler Stream V (G dom9)"),
        (244.0, 252.0, A, "min7", "I.3.3 Euler Stream vi (Am7)"),
        (252.0, 260.0, E, "min7", "I.3.4 Euler Stream iii (Em7)"),
        (260.0, 268.0, F, "maj69", "I.3.5 Euler Stream IV (F maj69)"),
        (268.0, 276.0, C, "prime11", "I.3.6 Prime-11 Convergence (C prime11)"),
        (276.0, 284.0, G, "maj", "I.3.7 Comma Lift V(31)"),
        (284.0, 292.0, D, "min7", "I.3.8 Comma Lift ii(9)"),
        (292.0, 300.0, F + 1, "maj69", "I.3.9 Comma Lift IV+(23)"),
        (300.0, 308.0, G + 1, "dom9", "I.3.10 Comma Lift V9+(32)"),
        (308.0, 316.0, C + 1, "dom9", "I.3.11 EULER CREST ON k=+1 (C+ dom9)!"),
        (316.0, 324.0, C + 1, "prime11", "I.3.12 Radiant Overtone Crown on k=+1"),
        (324.0, 332.0, F + 1, "maj", "I.3.13 Downward Return IV+(23)"),
        (332.0, 340.0, D, "min7", "I.3.14 Downward Return ii(9)"),
        (340.0, 348.0, G, "dom9", "I.3.15 Joyful Return V9(31 -> k=0)"),

        # I.4 (348..440): Asymptotic Thinning (x / ln x) & Expectant Approach to Re(s) = 1
        (348.0, 360.0, C, "maj69", "I.4.1 Sunlit Prime Horizon (C maj69)"),
        (360.0, 372.0, G, "dom9", "I.4.2 Curious Echo Hook (G dom9)"),
        (372.0, 384.0, F, "maj9", "I.4.3 Logarithmic Drift I (F maj9)"),
        (384.0, 396.0, C, "add9", "I.4.4 Logarithmic Drift II (C add9)"),
        (396.0, 408.0, A, "min9", "I.4.5 Questioning Glance (Am9)"),
        (408.0, 420.0, D, "dom9", "I.4.6 Brightening Threshold (D dom9)"),
        (420.0, 430.0, G, "sus2", "I.4.7 Shimmering Horizon (G sus2)"),
        (430.0, 440.0, E, "dom9", "I.4.8 Luminous Portal to Re(s) = 1 (E dom9)"),
    ]
    spans = [sb.add_span(*c) for c in m1_specs]

    # --- I.1 (0..108): Mercurial, Playful 7+5 Prime Hockets & Structure 1 Statements ---
    for cyc in range(9):
        sp7 = spans[2 * cyc]        # 7-beat span
        sp5 = spans[2 * cyc + 1]    # 5-beat span
        dyn = 0.62 + 0.020 * min(cyc, 6)

        # Light sunny Haydn/Prokofiev high string chamber cushion (strictly >= C3, zero heavy drones!)
        sb.string_pad(sp7, vel=dyn * 0.72, swell="arch", include_ext=False)
        sb.string_pad(sp5, vel=dyn * 0.62, swell="arch", include_ext=False)

        # Nimble 7-beat pizzicato + light cello/viola bounce (2+3+2 grouping: 0.0, 2.0, 5.0!)
        r7 = sp7.tenor_root()
        sb.note("pizzicato", sp7.start + 0.0, 0.38, r7, dyn * 0.96)
        sb.note("pizzicato", sp7.start + 2.0, 0.38, r7 + P5, dyn * 0.90)
        sb.note("pizzicato", sp7.start + 5.0, 0.38, r7 + OCT, dyn * 0.94)
        sb.note("cello", sp7.start + 0.0, 0.55, sp7.bass_root() + OCT, dyn * 0.88, swell="none")
        sb.note("cello", sp7.start + 5.0, 0.55, sp7.bass_root() + OCT + P5, dyn * 0.84, swell="none")

        # 5-beat hocket answer (2+3 grouping: 0.0, 1.0, 2.0, 3.5!)
        r5 = sp5.tenor_root()
        sb.note("pizzicato", sp5.start + 0.0, 0.38, r5 + OCT, dyn * 0.94)
        sb.note("pizzicato", sp5.start + 2.0, 0.38, r5 + P5, dyn * 0.90)
        sb.note("pizzicato", sp5.start + 3.5, 0.38, r5, dyn * 0.88)
        if cyc % 2 == 1:
            sb.note("bassoon", sp5.start + 0.0, 0.52, sp5.bass_root(), dyn * 0.84, swell="none")
            sb.note("bassoon", sp5.start + 2.0, 0.52, sp5.bass_root() + P5, dyn * 0.80, swell="none")

        # Sparkling Harp prime-overtone splashes on the 5-beat answer bars
        sb.harp_arp(
            sp5,
            sp5.start + 0.25,
            pitch(C, 4),
            pitch(C, 6),
            vel=dyn * 0.92,
            spacing=0.22,
            note_dur=1.2,
            ascending=(cyc % 2 == 0),
            max_notes=6,
        )

        # Crisp staccato Piano off-beat prime sparkles
        pts7 = sp7.scale_steps(pitch(E, 4), pitch(A, 5), allow_melody=False)
        if pts7 and cyc not in (2, 3):
            for k_hit, off in enumerate((1.0, 2.5, 4.0, 6.0)):
                st_p = pts7[(k_hit * 2 + cyc) % len(pts7)]
                sb.note("piano", sp7.start + off, 0.36, st_p, dyn * 0.84, snap_to_harmony=False)

        # Light buoyant Viola rhythmic inner dance
        v_th = r7 + OCT + M3
        sb.note("viola", sp7.start + 2.0, 0.48, v_th, dyn * 0.82, swell="none")
        sb.note("viola", sp7.start + 3.5, 0.48, r7 + P5, dyn * 0.80, swell="none")

    # FOREGROUND STRUCTURE 1 (Prime Curiosity Hook [+0,+9,+17,+31,+43,+53] in 2+3+2 rhythm) across I.1:
    # 1. Cycle 1 (beat 0.0): Flute introduces the Prime Curiosity Hook in C5..C6!
    sb.emit_prime_hook("flute", 0.0, pitch(C, 5), vel=0.66, unit=0.5)
    sb.emit_prime_hook("clarinet", 3.5, pitch(C, 4), vel=0.64, unit=0.5)  # Immediate cheeky octave echo!
    # Playful 5-beat woodwind hocket at 7.0..12.0
    sb.phrase("flute", [(7.0, 0.65, pitch(D, 5), 0.62), (8.0, 0.65, pitch(B, 4), 0.60), (9.5, 1.4, pitch(G, 5), 0.66)], vibrato=0.14)

    # 2. Cycle 2 (beat 12.0): Clarinet states Prime Hook on G4, answered by Pizzicato + Piano!
    sb.emit_prime_hook("clarinet", 12.0, pitch(G, 4) - OCT, vel=0.66, unit=0.5)
    sb.emit_prime_hook("piano", 15.5, pitch(G, 4), vel=0.64, unit=0.5)
    sb.phrase("english_horn", [(19.0, 0.8, pitch(E, 4), 0.62), (20.0, 0.8, pitch(G, 4), 0.64), (21.0, 1.8, pitch(D, 4), 0.62)], vibrato=0.18)

    # 3. Cycle 3 (beat 24.0): Staccato Piano + Pizzicato unison Prime Hook -> Flute crowns with Prime 11 (+24)!
    sb.emit_prime_hook("piano", 24.0, pitch(C, 4), vel=0.68, unit=0.5)
    sb.emit_prime_hook("pizzicato", 24.0, pitch(C, 4), vel=0.64, unit=0.5)
    sb.phrase("flute", [(27.5, 0.8, pitch(E, 5), 0.66), (28.5, 1.8, pitch(C, 5) + PRIME_11, 0.70)], vibrato=0.15, snap=False)

    # 4. Cycle 4 (beat 36.0): Full 7.0-beat (unit=1.0) playful Flute + Viola statement!
    sb.emit_prime_hook("flute", 36.0, pitch(C, 5), vel=0.70, unit=1.0, staccato=True)
    sb.phrase("clarinet", [(43.0, 0.8, 9 + M3, 0.66), (44.0, 0.8, 9 + P5, 0.68), (45.0, 1.8, 9 + HARM_7, 0.70)], vibrato=0.16, snap=False)

    # 5. Cycle 5 & 6 (48..72): English Horn & Viola spotlight Prime 11 (+24) + Hook on C4!
    sb.phrase("english_horn", [
        (48.0, 0.85, pitch(B, 3), 0.64),
        (49.0, 0.85, pitch(D, 4), 0.66),
        (50.0, 1.80, 31 + PRIME_11 - OCT, 0.70),  # 11th harmonic over G!
        (52.5, 1.80, pitch(G, 4), 0.66),
    ], vibrato=0.20, snap=False)
    sb.emit_prime_hook("english_horn", 60.0, pitch(C, 4), vel=0.70, unit=0.5)
    sb.phrase("flute", [(63.5, 1.2, pitch(C, 5) + PRIME_11, 0.70), (65.0, 1.6, pitch(G, 5), 0.72)], vibrato=0.16, snap=False)

    # 6. Cycle 7, 8, 9 (72..108): Canon of Prime Curiosity Hooks across Viola, Flute, Clarinet & Piano!
    sb.emit_prime_hook("viola", 72.0, pitch(F, 3), vel=0.68, unit=0.5)
    sb.emit_prime_hook("flute", 84.0, pitch(C, 5), vel=0.72, unit=0.5)
    sb.emit_prime_hook("clarinet", 87.5, pitch(C, 4), vel=0.70, unit=0.5)
    sb.emit_prime_hook("clarinet", 96.0, pitch(G, 3), vel=0.72, unit=0.5)
    sb.emit_prime_hook("flute", 99.5, pitch(G, 4), vel=0.74, unit=0.5)
    sb.chord("piano", 103.0, 0.55, [pitch(C, 4), pitch(E, 4), pitch(G, 4), pitch(C, 5) + PRIME_11], 0.72)

    # --- I.2 (108..228): Sieve of Eratosthenes Polyrhythm & Higher Primes (11, 13, 17, 19) ---
    for idx_sv, sp_sieve in enumerate(spans[18:38]):
        sb.string_pad(sp_sieve, vel=0.56 if idx_sv % 2 == 0 else 0.48, swell="arch", include_ext=False)
    # Crisp 0.5-beat sieve across 240 eighth-note slots (108..228):
    for slot in range(240):
        b = 108.0 + slot * 0.5
        sp = sb.span_at(b)
        u = slot / 240.0
        base_v = 0.62 + 0.12 * math.sin(math.pi * u)

        # Prime-7 pulse (every 14 slots = 7.0 beats): playful light timpani + harp chime (every other 7-cycle)
        if slot % 28 == 0:
            sb.note("timpani", b, 0.55, sp.bass_root(), base_v * 0.78, trim=False)
        # Prime-5 pulse (every 10 slots = 5.0 beats): nimble staccato bassoon/cello bounce
        if slot % 10 == 0:
            sb.note("cello", b, 0.42, sp.bass_root() + OCT, base_v * 0.88, swell="none")
            if (slot // 10) % 2 == 0:
                sb.note("bassoon", b, 0.45, sp.bass_root(), base_v * 0.84, swell="none")
        # Prime-3 pulse (every 6 slots = 3.0 beats): crisp pizzicato pluck
        if slot % 6 == 0:
            pizz_pts = sp.scale_steps(pitch(C, 3), pitch(E, 5), allow_melody=False)
            if pizz_pts:
                st_p = pizz_pts[(slot // 6 * 3) % len(pizz_pts)]
                sb.note("pizzicato", b, 0.34, st_p, base_v * 0.88, snap_to_harmony=False)

        # Unsieved Prime Stars on Piano & Harp!
        k60 = (slot % 60) + 2
        if k60 in PRIME_SET:
            pts = sp.scale_steps(pitch(E, 4), pitch(A, 5), allow_melody=False)
            if pts:
                st_star = pts[(k60 * 5 + slot // 10) % len(pts)]
                sb.note("piano", b, 0.34, st_star, base_v * 0.86, snap_to_harmony=False)
                if k60 in (5, 13, 29, 43, 59):
                    sb.harp_arp(
                        sp,
                        b,
                        pitch(C, 4),
                        pitch(C, 6),
                        vel=base_v * 0.88,
                        spacing=0.15,
                        note_dur=0.95,
                        ascending=(k60 % 4 == 1),
                        max_notes=5,
                    )

    # Spotlight Primes 11 (+24), 13 (+37), 17 (+5), 19 (+13) + recurring Prime Hooks in I.2:
    sb.emit_prime_hook("pizzicato", 108.0, pitch(C, 4), vel=0.70, unit=0.5)
    sb.phrase("english_horn", [
        (120.0, 0.9, PRIME_11, 0.68),
        (121.0, 1.4, PRIME_13, 0.72),      # Prime 13 (13:8 = +37)!
        (123.0, 1.2, BB_HARM, 0.70),
        (125.0, 1.5, pitch(C, 5), 0.72),
    ], vibrato=0.20, snap=False)
    sb.emit_prime_hook("flute", 132.0, pitch(C, 5), vel=0.74, unit=0.5)
    sb.phrase("clarinet", [
        (144.0, 0.9, 31 + PRIME_11 - OCT, 0.68),
        (145.0, 1.4, 31 + PRIME_13 - OCT, 0.72),
        (147.0, 1.6, pitch(G, 4), 0.70),
        # Bar 156..163: Primes 17 (+5) & 19 (+13) playful curiosity!
        (156.0, 0.85, SEMI + OCT, 0.70),
        (157.0, 0.85, PRIME_19 + OCT, 0.74),
        (158.0, 0.85, M3 + OCT, 0.72),
        (159.0, 1.60, PRIME_11 + OCT, 0.75),
    ], vibrato=0.18, snap=False)
    sb.emit_prime_hook("clarinet", 168.0, pitch(F, 4), vel=0.74, unit=0.5)
    sb.phrase("viola", [
        (180.0, 1.4, pitch(E, 4), 0.66),
        (182.0, 1.4, pitch(G, 4), 0.68),
        (184.0, 2.2, pitch(B, 3), 0.66),
        (187.5, 1.8, 9 + M3, 0.68),
        (192.5, 2.0, pitch(D, 4), 0.70),
        (195.0, 2.5, pitch(B, 3), 0.72),
    ], vibrato=0.20, snap=True)
    # Double-woodwind hocket Prime Hook at 204.0!
    sb.emit_prime_hook("flute", 204.0, pitch(C, 5), vel=0.76, unit=0.5)
    sb.emit_prime_hook("english_horn", 207.5, pitch(C, 4), vel=0.72, unit=0.5)
    sb.phrase("clarinet", [(216.0, 1.2, pitch(D, 5), 0.72), (218.0, 1.2, 31 + HARM_7, 0.74), (220.0, 2.2, pitch(G, 5), 0.76)], vibrato=0.18, snap=False)

    # --- I.3 (228..348): Euler Product — Sparkling Chamber-Orchestral Convergence (136 BPM!) ---
    euler_spans = spans[38:53]
    for i, sp in enumerate(euler_spans):
        dur = sp.end - sp.start
        crest = 1.0 - abs(i - 10) / 11.0
        dyn = 0.64 + 0.20 * (crest ** 1.2)   # Bright, buoyant mf -> f (0.64..0.84)
        br = sp.bass_root()

        # Airy major String Ensemble + dancing Pizzicato + light Bassoon (trombone & organ TACET!)
        sb.string_pad(sp, vel=dyn * 0.82, swell="cresc" if i == 9 else "arch", include_ext=True)
        sb.note("bassoon", sp.start, 1.6, br, dyn * 0.84, swell="arch")
        sb.note("bassoon", sp.start + 4.0, 1.6, br, dyn * 0.82, swell="arch")
        sb.note("pizzicato", sp.start + 2.0, 0.35, sp.tenor_root() + P5, dyn * 0.86)
        sb.note("pizzicato", sp.start + 6.0, 0.35, sp.tenor_root() + OCT, dyn * 0.86)

        # Warm French Horn joins ONLY for the radiant Comma Lift crest (bars 6..11, 276..324)
        if 6 <= i <= 11:
            sb.note("french_horn", sp.start, 3.4, sp.tenor_root() + P5, dyn * 0.82, swell="arch", vibrato=0.14)

        if i in (0, 5, 9, 10, 11, 14):
            sb.harp_arp(sp, sp.start, pitch(C, 4), pitch(C, 6), vel=dyn * 0.92, spacing=0.14, note_dur=1.4, ascending=(i != 14), max_notes=8)
        if i in (9, 10):
            sb.note("timpani", sp.start, 0.75, br, dyn * 0.78, trim=False)

        # Crisp Haydn/Prokofiev 8th-note Piano Alberti/overtone sparkle
        pts = sp.scale_steps(pitch(C, 4), pitch(A, 5), allow_melody=False)
        if pts:
            for s_k in range(8):
                t = sp.start + s_k * 1.0 + 0.5
                st_p = pts[(s_k * 2 + i) % len(pts)]
                sb.note("piano", t, 0.36, st_p, dyn * 0.80, snap_to_harmony=False)

    # Radiant Prime Hooks & Counterpoint across I.3 (including k=+1 Euler Crest at 308.0!):
    sb.emit_prime_hook("flute", 228.0, pitch(C, 5), vel=0.78, unit=0.5)
    sb.emit_prime_hook("clarinet", 236.0, pitch(G, 4) - OCT, vel=0.76, unit=0.5)
    sb.phrase("flute", [
        (244.0, 1.6, pitch(E, 5), 0.74),
        (246.0, 1.6, pitch(G, 5), 0.76),
        (248.0, 3.2, pitch(C, 6), 0.78),
        (260.0, 1.8, pitch(A, 5), 0.76),
        (262.0, 1.8, pitch(G, 5), 0.74),
        (264.0, 3.2, pitch(D, 5), 0.74),
    ], vibrato=0.18, snap=True)
    sb.emit_prime_hook("english_horn", 268.0, pitch(C, 4), vel=0.76, unit=0.5)
    # Comma Lift common-tone climb (276..308: k=0 -> k=+1):
    sb.phrase("clarinet", [
        (276.0, 3.4, pitch(G, 4, 0), 0.76),
        (284.0, 3.4, pitch(A, 4, 1), 0.78),    # 9 + 31 = 40 = A4+1!
        (292.0, 3.4, pitch(C, 5, 1), 0.80),
        (300.0, 1.8, pitch(D, 5, 1), 0.82),
        (302.0, 1.8, 32 + HARM_7, 0.84),
        (304.0, 3.4, pitch(B, 4, 1), 0.84),
    ], vibrato=0.18, snap=True)
    # EULER CREST at beat 308.0 on C+(k=+1): Flute + Piano fire Structure 1 shifted +1 comma!
    sb.emit_prime_hook("flute", 308.0, pitch(C, 5, 1), vel=0.84, unit=0.5)
    sb.emit_prime_hook("piano", 312.0, pitch(C, 4, 1), vel=0.82, unit=0.5)
    sb.phrase("cello", [
        (276.0, 3.4, pitch(B, 3, 0), 0.74),
        (284.0, 3.4, pitch(D, 4, 0), 0.76),
        (292.0, 3.4, pitch(A, 3, 1), 0.78),
        (308.0, 3.6, pitch(G, 3, 1), 0.82),
        (316.0, 3.6, pitch(E, 4, 1), 0.80),
        (324.0, 3.6, pitch(C, 4, 1), 0.76),
        (332.0, 3.6, pitch(A, 3, 1), 0.74),
        (340.0, 3.6, pitch(G, 3, 0), 0.74),
    ], vibrato=0.22, snap=True)
    sb.emit_prime_hook("clarinet", 340.0, pitch(G, 3), vel=0.76, unit=0.5)

    # --- I.4 (348..440): Asymptotic Thinning (x / ln x) & Luminous Portal to Re(s) = 1 ---
    asym_spans = spans[53:]
    prime_gaps = [2.0, 3.0, 5.0, 7.0, 11.0, 13.0, 17.0, 19.0]
    t_star = 349.0
    g_i = 0
    while t_star < 438.0:
        sp = sb.span_at(t_star)
        pts = sp.scale_steps(pitch(E, 4), pitch(C, 6), allow_melody=False)
        if pts:
            v_s = max(0.46, 0.68 - 0.025 * g_i)
            sb.note("piano", t_star, 0.85, pts[(g_i * 3) % len(pts)], v_s, snap_to_harmony=False)
            sb.note("pizzicato", t_star, 0.38, sp.tenor_root() + OCT, v_s * 0.90)
        t_star += prime_gaps[min(g_i, len(prime_gaps) - 1)] * 0.55
        g_i += 1

    for i, sp in enumerate(asym_spans):
        dur = sp.end - sp.start
        dyn = 0.66 - 0.010 * i
        sb.add_pedal(sp.start, dur - 0.25)
        if i < 6:
            sb.string_pad(sp, vel=dyn * 0.86, swell="arch", include_ext=(i < 4))
        else:
            sb.string_pad(sp, vel=dyn * 0.88, track_id="tremolo_strings", swell="cresc", include_ext=False)
        sb.note("cello", sp.start, dur * 0.78, sp.tenor_root(), dyn * 0.88, swell="arch", vibrato=0.22)
        sb.harp_arp(sp, sp.start + 0.6, pitch(C, 4), pitch(C, 6), vel=dyn * 0.90, spacing=0.22 + 0.03 * i, note_dur=2.0, ascending=True, max_notes=max(5, 7 - i // 2))

    # One final curious Flute Prime Hook at 360.0 & shimmering English Horn horizon call
    sb.emit_prime_hook("flute", 360.0, pitch(G, 4), vel=0.64, unit=0.5)
    sb.phrase("english_horn", [
        (385.0, 3.2, pitch(E, 4), 0.56),
        (397.0, 3.6, pitch(C, 5), 0.54),
        (409.0, 3.6, 9 + HARM_7 - OCT, 0.54),
        (431.0, 6.5, 17 + HARM_7 - OCT, 0.56),   # Septimal portal over E dom9!
    ], vibrato=0.24, snap=False)


# =============================================================================
# MOVEMENT II — ANALYTIC CONTINUATION (THROUGH THE MIRROR)
# (Beats 440..764, ~3:28 – 6:58, fluid rubato waves 88 -> 114 -> 66 BPM)
# =============================================================================
def compose_movement_2(sb: RiemannSymphonyBuilder) -> None:
    sb.add_section(440.0, "II.1 Stepping Through the Pole Re(s) = 1 — Luminous 53-EDO Diesis Rotations")
    sb.add_section(512.0, "II.2 Weightless Critical Strip (0 < Re(s) < 1) — Comma Glide & Mirror Awakening")
    sb.add_section(584.0, "II.3 Functional Equation xi(s) = xi(1 - s) — Exact Mirror Wedge & Palindrome")
    sb.add_section(696.0, "II.4 First Nontrivial Zero (t_1 = 14.1347) — Hushed Convergence at 66 BPM")

    m2_specs = [
        # II.1 (440..512): BOTH 53-EDO Major-Third Diesis Rotations!
        # Ascending cycle: 0 -> 17 -> 34 -> 51 (-2 diesis!), returning cleanly,
        # then Descending cycle: 0 -> 36 -> 19 -> 2 (+2 diesis!) into the Strip!
        (440.0, 448.0, C, "maj", "II.1.1 Pole Horizon C(0)"),
        (448.0, 456.0, 17, "maj", "II.1.2 Ascending Rotation +M3: E(17, holds E=17)"),
        (456.0, 464.0, 34, "maj", "II.1.3 Ascending Rotation +M3: G#(34, holds G#=34)"),
        (464.0, 472.0, 51, "maj", "II.1.4 First Diesis Portal C--(51, holds 51, -2 Diesis!)"),
        (472.0, 476.0, 34, "maj", "II.1.5 Luminous Pivot G#(34)"),
        (476.0, 480.0, 17, "maj", "II.1.6 Luminous Pivot E(17)"),
        (480.0, 488.0, C, "maj", "II.1.7 Central Axis C(0)"),
        (488.0, 496.0, 36, "maj", "II.1.8 Descending Rotation -M3: Ab(36, holds C=0)"),
        (496.0, 504.0, 19, "maj", "II.1.9 Descending Rotation -M3: E-(19, holds Ab=36)"),
        (504.0, 512.0, 2, "maj", "II.1.10 Breach into Strip C++(2, holds E-=19, +2 Diesis!)"),

        # II.2 (512..584): Weightless Critical Strip Luminosity (k=+2 -> +1 -> 0)
        (512.0, 520.0, 24, "maj7", "II.2.1 Weightless Float F++ maj7(24)"),
        (520.0, 528.0, 10, "min7", "II.2.2 Comma Float ii+(10)"),
        (528.0, 536.0, 32, "dom9", "II.2.3 Comma Float V9+(32)"),
        (536.0, 544.0, C + 1, "maj9", "II.2.4 Strip Glow C+ maj9(1)"),
        (544.0, 552.0, A + 1, "min9", "II.2.5 Strip Glow Am+9(40)"),
        (552.0, 560.0, F + 1, "maj69", "II.2.6 Strip Glow F+ maj69(23)"),
        (560.0, 568.0, D, "min7", "II.2.7 Comma Return ii(9)"),
        (568.0, 576.0, G, "dom9", "II.2.8 Septimal Bridge V9(31 -> k=0)"),
        (576.0, 584.0, C, "mirror_maj", "II.2.9 Mirror Axis Awakening C(0)"),

        # II.3 (584..696): 28-Bar Palindromic Functional Equation Arch around Beat 640.0!
        # Forward Half (584..640, 14 bars x 4 beats = 7 diverging/reconverging 2-bar wedges):
        (584.0, 588.0, C, "mirror_maj", "II.3.F1 Wedge 1 Open: C"),
        (588.0, 592.0, C, "mirror_maj", "II.3.F2 Wedge 1 Close: C"),
        (592.0, 596.0, A, "mirror_min", "II.3.F3 Wedge 2 Open: Am"),
        (596.0, 600.0, A, "mirror_min", "II.3.F4 Wedge 2 Close: Am"),
        (600.0, 604.0, F, "mirror_maj", "II.3.F5 Wedge 3 Open: F"),
        (604.0, 608.0, F, "mirror_maj", "II.3.F6 Wedge 3 Close: F"),
        (608.0, 612.0, D_MINUS, "mirror_min", "II.3.F7 Wedge 4 Open: Dm-"),
        (612.0, 616.0, G, "mirror_maj", "II.3.F8 Wedge 4 Close: G"),
        (616.0, 620.0, E, "mirror_min", "II.3.F9 Wedge 5 Open: Em"),
        (620.0, 624.0, A, "mirror_min", "II.3.F10 Wedge 5 Close: Am"),
        (624.0, 628.0, F, "mirror_maj", "II.3.F11 Wedge 6 Open: F"),
        (628.0, 632.0, G, "mirror_maj", "II.3.F12 Wedge 6 Close: G"),
        (632.0, 636.0, C, "mirror_maj", "II.3.F13 Critical Line Crest Open: C"),
        (636.0, 640.0, C, "mirror_maj", "II.3.F14 Critical Line Axis Left (beat 640.0)"),
        # Retrograde Half (640..696, exact 14-bar harmonic & melodic retrograde palindrome!):
        (640.0, 644.0, C, "mirror_maj", "II.3.R14 Critical Line Axis Right (beat 640.0)"),
        (644.0, 648.0, C, "mirror_maj", "II.3.R13 Critical Line Crest Retrograde: C"),
        (648.0, 652.0, G, "mirror_maj", "II.3.R12 Wedge 6 Retrograde: G"),
        (652.0, 656.0, F, "mirror_maj", "II.3.R11 Wedge 6 Retrograde: F"),
        (656.0, 660.0, A, "mirror_min", "II.3.R10 Wedge 5 Retrograde: Am"),
        (660.0, 664.0, E, "mirror_min", "II.3.R9 Wedge 5 Retrograde: Em"),
        (664.0, 668.0, G, "mirror_maj", "II.3.R8 Wedge 4 Retrograde: G"),
        (668.0, 672.0, D_MINUS, "mirror_min", "II.3.R7 Wedge 4 Retrograde: Dm-"),
        (672.0, 676.0, F, "mirror_maj", "II.3.R6 Wedge 3 Retrograde: F"),
        (676.0, 680.0, F, "mirror_maj", "II.3.R5 Wedge 3 Retrograde: F"),
        (680.0, 684.0, A, "mirror_min", "II.3.R4 Wedge 2 Retrograde: Am"),
        (684.0, 688.0, A, "mirror_min", "II.3.R3 Wedge 2 Retrograde: Am"),
        (688.0, 692.0, C, "mirror_maj", "II.3.R2 Wedge 1 Retrograde: C"),
        (692.0, 696.0, C, "mirror_maj", "II.3.R1 Wedge 1 Retrograde: C"),

        # II.4 (696..764): First Nontrivial Zero (t_1 = 14.1347) — Hushed Convergence at 66 BPM
        (696.0, 706.0, A, "min9", "II.4.1 Zero Approach Am9"),
        (706.0, 716.0, F, "maj9", "II.4.2 Zero Approach F maj9"),
        (716.0, 726.0, D_MINUS, "min9", "II.4.3 Zero Approach Dm-9"),
        (726.0, 736.0, G, "dom9", "II.4.4 Septimal Convergence G dom9"),
        (736.0, 746.0, C, "add9", "II.4.5 Zero Node Settling C add9"),
        (746.0, 755.0, C, "sus2", "II.4.6 Spectral Cancellation C sus2"),
        (755.0, 764.0, C, "open5", "II.4.7 First Nontrivial Zero (C4=0 Stillness)"),
    ]
    spans = [sb.add_span(*c) for c in m2_specs]

    # --- II.1 (440..512): Luminous, Wonder-Struck Diesis Rotations (NO heavy trombone!) ---
    for i, sp in enumerate(spans[:10]):
        dur = sp.end - sp.start
        wave = math.sin(math.pi * (i + 1) / 10.5)
        dyn = 0.58 + 0.22 * wave   # Surges 0.58 -> 0.80 with airy shimmer!
        sb.add_pedal(sp.start, dur - 0.18)
        sb.string_pad(sp, vel=dyn * 0.82, track_id="tremolo_strings", swell="arch", include_ext=False)
        sb.string_pad(sp, vel=dyn * 0.80, swell="arch", include_ext=False)
        sb.harp_arp(sp, sp.start, pitch(C, 3), pitch(C, 6), vel=dyn * 0.92, spacing=0.15, note_dur=1.9, ascending=(i % 2 == 0), max_notes=9)
        sb.note("cello", sp.start, dur - 0.35, sp.tenor_root(), dyn * 0.86, swell="arch", vibrato=0.24)
        if i in (3, 8, 9):
            sb.note("french_horn", sp.start, dur - 0.35, sp.tenor_root() + P5, dyn * 0.82, swell="arch", vibrato=0.16)

    # Golden Common-Tone Threads across BOTH Diesis Rotations (0->17->34->51 and 0->36->19->2):
    sb.note("flute", 441.0, 13.5, pitch(E, 5), 0.68, swell="arch", vibrato=0.22, trim=False)          # E5=70 across C(0)->E(17)!
    sb.note("clarinet", 450.0, 12.8, 34 + OCT, 0.72, swell="arch", vibrato=0.20, trim=False)           # G#5=87? Clapped to G#4=34!
    sb.note("english_horn", 458.0, 13.2, 51, 0.74, swell="arch", vibrato=0.24, trim=False)             # C--5=51 across G#(34)->C--(51)!
    sb.note("flute", 481.0, 13.8, pitch(C, 5), 0.74, swell="cresc", vibrato=0.22, trim=False)          # C5=53 across C(0)->Ab(36)!
    sb.note("clarinet", 490.0, 13.2, pitch(AB, 4), 0.78, swell="cresc", vibrato=0.22, trim=False)      # Ab4=36 across Ab(36)->E-(19)!
    sb.note("flute", 498.0, 13.2, 19 + OCT, 0.82, swell="arch", vibrato=0.22, trim=False)              # E-5=72 across E-(19)->C++(2)!

    # --- II.2 (512..584): Weightless Critical Strip Nocturne & First Mirror Glimmers ---
    for i, sp in enumerate(spans[10:19]):
        dur = sp.end - sp.start
        dyn = 0.58 + 0.022 * min(i, 6)
        sb.add_pedal(sp.start, 3.82)
        sb.add_pedal(sp.start + 4.0, 3.82)
        sb.string_pad(sp, vel=dyn * 0.82, swell="arch", include_ext=True)
        if i % 2 == 0:
            sb.harp_arp(sp, sp.start + 0.5, pitch(C, 3), pitch(C, 6), vel=dyn * 0.90, spacing=0.18, note_dur=2.1, ascending=True, max_notes=8)
        pts = sp.scale_steps(pitch(E, 3), pitch(G, 5), allow_melody=False)
        if len(pts) >= 5:
            wave_idx = [0, 2, 4, 3, 1, 3, 4, 2]
            for s_k, wi in enumerate(wave_idx):
                sb.note("piano", sp.start + s_k * 1.0, 0.78, pts[(wi + i) % len(pts)], dyn * 0.82, snap_to_harmony=False)

    # Singing Flute, English Horn & Cello Critical Strip Cantabile (512..584):
    sb.phrase("english_horn", [
        (513.0, 3.2, 24 + M3, 0.54),
        (517.0, 2.6, 24, 0.52),
        (521.0, 3.2, 10 + m3, 0.56),
        (529.0, 3.2, 32 + M3 - OCT, 0.58),
        (537.0, 3.4, pitch(E, 4, 1), 0.60),
        (541.0, 2.6, pitch(G, 4, 1), 0.62),
        (545.0, 3.4, pitch(C, 5, 1), 0.64),
        (553.0, 3.4, pitch(A, 4, 1), 0.62),
        (561.0, 3.4, pitch(F, 4, 1), 0.60),
        (569.0, 3.4, BB_HARM, 0.64),
    ], vibrato=0.30, slide_cents=20.0, snap=True)

    # First Mirror Wedge Preview on 576..584 (C mirror_maj)!
    sb.emit_mirror_wedge_bar(spans[18], "flute", "cello", vel=0.62, diverging=True, S_override=48)

    # --- II.3 (584..696): STRUCTURE 2 — Functional Mirror Wedge & 28-Bar Palindrome! ---
    # Forward 14 bars (584..640, surging to 114 BPM at beat 640.0)
    fwd_spans = spans[19:33]
    ret_spans = spans[33:47]

    for bi, sp in enumerate(fwd_spans):
        u_prog = bi / 13.0
        dyn = 0.54 + 0.30 * (u_prog ** 0.95)   # Surges luminously 0.54 -> 0.84 at Critical Line!
        is_open = (bi % 2 == 0)
        up_tr = "flute" if (bi // 2) % 2 == 0 else "clarinet"
        lo_tr = "cello" if (bi // 2) % 2 == 0 else "viola"

        sb.emit_mirror_wedge_bar(sp, up_tr, lo_tr, vel=dyn, diverging=is_open, retrograde=False, vibrato=0.24)
        # Double at the surging Critical-Line crest (bars 10..13, 624..640)!
        if bi >= 10:
            up2 = "clarinet" if up_tr == "flute" else "flute"
            lo2 = "viola" if lo_tr == "cello" else "cello"
            sb.emit_mirror_wedge_bar(sp, up2, lo2, vel=dyn * 0.88, diverging=is_open, retrograde=False, vibrato=0.20)

        sb.add_pedal(sp.start, 3.82)
        if bi >= 2:
            sb.string_pad(sp, vel=dyn * 0.72, swell="cresc" if bi >= 10 else "arch", include_ext=False)
        if bi >= 6 and bi % 2 == 0:
            sb.note("bassoon", sp.start, 3.6, sp.bass_root(), dyn * 0.80, swell="arch")
        if bi % 2 == 0:
            sb.harp_arp(sp, sp.start + 0.25, pitch(C, 3), pitch(C, 6), vel=dyn * 0.88, spacing=0.16, note_dur=1.5, ascending=is_open, max_notes=7)
        else:
            # Off-beat Mirror Piano dyads summing to exact S!
            S = sp.mirror_sum_wedge()
            u_p = sp.nearest_step((S // 2) + 19, allow_melody=False)
            l_p = sp.nearest_step(S - u_p, allow_melody=False)
            if u_p - l_p >= 12:
                sb.note("piano", sp.start + 0.5, 0.65, u_p, dyn * 0.76, snap_to_harmony=False)
                sb.note("piano", sp.start + 0.5, 0.65, l_p, dyn * 0.74, snap_to_harmony=False)
                sb.note("piano", sp.start + 2.5, 0.65, u_p, dyn * 0.76, snap_to_harmony=False)
                sb.note("piano", sp.start + 2.5, 0.65, l_p, dyn * 0.74, snap_to_harmony=False)

    # Radiant French Horn halo right across the Critical Line Axis Re(s) = 1/2 (636..644)!
    sb.note("french_horn", 636.0, 3.7, pitch(G, 3), 0.80, swell="cresc", vibrato=0.18)
    sb.note("french_horn", 640.0, 3.7, pitch(E, 4), 0.80, swell="dim", vibrato=0.18)

    # Retrograde Half (640..696, exact time-retrograde symmetry receding 114 -> 86 BPM!):
    for ri, sp in enumerate(ret_spans):
        src_bi = 13 - ri
        u_prog = src_bi / 13.0
        dyn = 0.50 + 0.30 * (u_prog ** 0.95)
        is_open = (src_bi % 2 == 0)
        # Swap woodwind/string pairings across the mirror!
        up_tr = "clarinet" if (src_bi // 2) % 2 == 0 else "flute"
        lo_tr = "viola" if (src_bi // 2) % 2 == 0 else "cello"

        sb.emit_mirror_wedge_bar(sp, up_tr, lo_tr, vel=dyn, diverging=is_open, retrograde=True, vibrato=0.24)
        sb.add_pedal(sp.start, 3.82)
        if ri <= 10:
            sb.string_pad(sp, vel=dyn * 0.70, swell="dim" if ri >= 8 else "arch", include_ext=False)
        if ri % 2 == 1:
            sb.harp_arp(sp, sp.start + 0.25, pitch(C, 3), pitch(C, 6), vel=dyn * 0.86, spacing=0.18, note_dur=1.5, ascending=False, max_notes=7)

    # --- II.4 (696..764): First Nontrivial Zero (t_1 = 14.1347) — Hushed 66 BPM Stillness ---
    zero_spans = spans[47:]
    for i, sp in enumerate(zero_spans):
        dur = sp.end - sp.start
        dyn = max(0.56, 0.68 - 0.018 * i) if i < 6 else 0.50
        sb.add_pedal(sp.start, dur - 0.25)
        if i <= 4:
            sb.string_pad(sp, vel=dyn * 0.90, swell="dim", include_ext=False)
            sb.note("bassoon", sp.start, dur * 0.72, sp.bass_root(), dyn * 0.88, swell="dim")
        else:
            sb.chord("string_ensemble", sp.start, dur - 0.35, [pitch(C, 3), pitch(G, 3), pitch(C, 4), pitch(G, 4)], dyn * 0.90, swell="dim")
            sb.note("french_horn", sp.start + 0.4, dur - 1.0, pitch(G, 3), dyn * 0.86, swell="dim")
        sb.harp_arp(sp, sp.start + 0.6, pitch(C, 3), pitch(G, 5), vel=dyn + 0.08, spacing=0.28 + 0.03 * i, note_dur=2.8, ascending=True, max_notes=max(5, 8 - i))
        pts_z = sp.scale_steps(pitch(C, 4), pitch(E, 5), allow_melody=False)
        if pts_z and i < 6:
            sb.note("piano", sp.start + 2.0, 2.4, pts_z[0], dyn * 0.82, snap_to_harmony=False)
            sb.note("piano", sp.start + 5.5, 2.4, pts_z[-1], dyn * 0.78, snap_to_harmony=False)

    # Mirror aperture narrows step-by-step onto exact C4 = 0!
    sb.phrase("flute", [
        (697.0, 5.5, pitch(E, 5), 0.64),
        (707.0, 5.5, pitch(C, 5), 0.62),
        (717.0, 5.5, pitch(A, 4), 0.60),
        (727.0, 5.5, pitch(G, 4), 0.58),
        (737.0, 6.0, pitch(E, 4), 0.56),
        (755.5, 7.2, pitch(C, 4), 0.50),
    ], swell="dim", vibrato=0.20)
    sb.phrase("cello", [
        (698.0, 5.5, pitch(E, 3), 0.64),
        (708.0, 5.5, pitch(F, 3), 0.62),
        (718.0, 5.5, pitch(A, 3), 0.60),
        (728.0, 5.5, pitch(B, 3), 0.58),
        (746.5, 6.5, pitch(G, 3), 0.54),
        (755.5, 7.2, pitch(C, 3), 0.50),
    ], swell="dim", vibrato=0.22)
    sb.note("piano", 757.0, 6.0, pitch(C, 4), 0.50, snap_to_harmony=False)


# =============================================================================
# MOVEMENT III — A CENTURY OF SMALL PROGRESS
# (Beats 764..1154, ~6:58 – 11:25, 72 -> 104 -> 136 -> 60 BPM)
# Preserves ~8:00 C-minor Passacaglia (3A) & Unresolved Summit (G+++7 step 24)
# + Bold Pair-Correlation Riff (3B) & Fracturing Overlays of Structures 1 & 2!
# =============================================================================
def add_passacaglia_cycle(
    sb: RiemannSymphonyBuilder,
    start_beat: float,
    k: int,
    var_num: int,
    climb_comma: bool = False,
    unresolved_end: bool = False,
    summit_stretch: float = 0.0,
) -> List[ChordSpan]:
    """Adds one 8-bar (32-beat, or +summit_stretch on Var 12) Passacaglia cycle on comma plane `k`."""
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
        specs = [
            (b + 0.0, b + 4.0, C + k, "min", f"III.V{var_num}.1 Cm(k={k})"),
            (b + 4.0, b + 8.0, AB + k, "maj7", f"III.V{var_num}.2 Ab maj7(k={k})"),
            (b + 8.0, b + 12.0, F + k, "min7", f"III.V{var_num}.3 Fm7(k={k})"),
            (b + 12.0, b + 16.0, G + k, "sus4", f"III.V{var_num}.4 G sus4(k={k})"),
            (b + 16.0, b + 24.0, AB + k, "maj9", f"III.V{var_num}.5 Tragic VI9(k={k})"),
            (b + 24.0, b + 32.0 + summit_stretch, G + k, "dom7", f"III.V{var_num}.6 Unresolved Summit G+++7(step 24!)"),
        ]
    return [sb.add_span(*s) for s in specs]


def compose_movement_3(sb: RiemannSymphonyBuilder) -> None:
    sb.add_section(764.0, "III.1 C-Minor Passacaglia — Hadamard, de la Vallée Poussin & Hardy (k = 0 -> +1)")
    sb.add_section(860.0, "III.2 Four-Voice Fugato, Breakthrough Drive & Selberg Parity Setback (k = +1 -> +2)")
    sb.add_section(956.0, "III.3 Montgomery–Odlyzko Pair-Correlation Riff & 136 BPM Surge (k = +2 -> +3)")
    sb.add_section(1052.0, "III.4 Colossal Climb & Unresolved Summit at k = +3 (G+++7 Step 24 Freeze)")

    # 12 Evolving Passacaglia Variations (764.0 .. 1154.0 = 390 beats)
    v1 = add_passacaglia_cycle(sb, 764.0, k=0, var_num=1)                          # 6:58–7:24
    v2 = add_passacaglia_cycle(sb, 796.0, k=0, var_num=2)                          # 7:24–7:50
    v3 = add_passacaglia_cycle(sb, 828.0, k=0, var_num=3, climb_comma=True)        # 7:50–8:14 (~8:00 Core!)
    v4 = add_passacaglia_cycle(sb, 860.0, k=1, var_num=4)                          # 8:14–8:35 Fugato
    v5 = add_passacaglia_cycle(sb, 892.0, k=1, var_num=5)                          # 8:35–8:54 Drive & Selberg subito pp!
    v6 = add_passacaglia_cycle(sb, 924.0, k=1, var_num=6, climb_comma=True)        # 8:54–9:14 Rebuilding +1->+2
    v7 = add_passacaglia_cycle(sb, 956.0, k=2, var_num=7)                          # 9:14–9:31 Pair-Correlation Riff!
    v8 = add_passacaglia_cycle(sb, 988.0, k=2, var_num=8, climb_comma=True)        # 9:31–9:45 136 BPM Surge +2->+3!
    v9 = add_passacaglia_cycle(sb, 1020.0, k=3, var_num=9)                         # 9:45–10:00 Fracturing Motifs at k=+3!
    v10 = add_passacaglia_cycle(sb, 1052.0, k=3, var_num=10)                       # 10:00–10:20 Broadening Struggle
    v11 = add_passacaglia_cycle(sb, 1084.0, k=3, var_num=11)                       # 10:20–10:48 Colossal Brucknerian Summit
    v12 = add_passacaglia_cycle(sb, 1116.0, k=3, var_num=12, unresolved_end=True, summit_stretch=6.0)  # 10:48–11:25 Freeze!

    # --- Variation 1 (764..796, k=0, 72 BPM): Solitary Cello & Bassoon Granite C-Minor Ground ---
    for i, sp in enumerate(v1):
        br = sp.bass_root()
        v = 0.58 + 0.012 * i
        sb.note("bassoon", sp.start, 3.3, br, v, swell="arch")
        sb.note("cello", sp.start, 2.5, br + OCT, v + 0.05, swell="arch", vibrato=0.26)
        sb.note("cello", sp.start + 3.0, 0.85, br + OCT + P5, v + 0.02, swell="none")
        sb.note("pizzicato", sp.start, 0.42, br + OCT, v + 0.04)
        sb.string_pad(sp, vel=v * 0.86, swell="arch", include_ext=False)
        if i >= 3:
            th = m3 if "min" in sp.quality else M3
            sb.note("viola", sp.start + 1.0, 2.6, sp.tenor_root() + OCT + th, v, swell="arch", vibrato=0.22)

    # --- Variation 2 (796..828, k=0, ~7:30–7:50): Brahmsian Off-Beat Piano & Woodwind Lament ---
    eh_v2, cl_v2 = [], []
    for i, sp in enumerate(v2):
        br = sp.bass_root()
        v = 0.50 + 0.012 * i
        sb.note("bassoon", sp.start, 1.8, br, v, swell="arch")
        sb.note("bassoon", sp.start + 2.0, 1.7, br, v * 0.94, swell="arch")
        sb.note("cello", sp.start, 1.8, br + OCT, v + 0.04, vibrato=0.24)
        sb.note("cello", sp.start + 2.0, 1.8, br + OCT + P5, v + 0.02, vibrato=0.20)
        voic = sp.open_voicing(include_ext=False)
        sb.chord("piano", sp.start + 0.5, 1.15, voic, v * 0.80)
        sb.chord("piano", sp.start + 2.5, 1.15, voic, v * 0.78)
        if i % 2 == 0:
            eh_v2.extend([
                (sp.start, 1.4, sp.nearest_step(pitch(G, 4) - i, allow_melody=False), v + 0.08),
                (sp.start + 1.5, 0.45, sp.nearest_step(pitch(EB, 4), allow_melody=True), v + 0.05),
                (sp.start + 2.0, 1.7, sp.nearest_step(pitch(C, 5) - i * 2, allow_melody=False), v + 0.10),
            ])
        else:
            cl_v2.extend([
                (sp.start, 1.4, sp.nearest_step(pitch(C, 5) - i, allow_melody=False), v + 0.08),
                (sp.start + 1.5, 0.45, sp.nearest_step(pitch(G, 4), allow_melody=True), v + 0.05),
                (sp.start + 2.0, 1.7, sp.nearest_step(pitch(EB, 5) - i * 2, allow_melody=False), v + 0.10),
            ])
    sb.phrase("english_horn", eh_v2, vibrato=0.30, slide_cents=16.0)
    sb.phrase("clarinet", cl_v2, vibrato=0.22)

    # --- Variation 3 (828..860, k=0->+1, right across ~8:00!): Hardy (1914) First Comma Lift ---
    for i, sp in enumerate(v3):
        br = sp.bass_root()
        v = 0.56 + 0.022 * i
        sb.string_pad(sp, vel=v * 0.82, swell="cresc" if i >= 4 else "arch", include_ext=True)
        sb.note("bassoon", sp.start, 3.6, br, v * 0.92, swell="arch")
        sb.add_pedal(sp.start, 3.82)
        pts = sp.scale_steps(pitch(C, 3), pitch(C, 5), allow_melody=True)
        if len(pts) >= 5:
            for s_i in range(8):
                sb.note("viola", sp.start + s_i * 0.5, 0.42, pts[(s_i + i * 2) % len(pts)], v * (0.92 if s_i % 4 == 0 else 0.78), snap_to_harmony=False)
        if i in (0, 3, 6, 7):
            sb.harp_arp(sp, sp.start, pitch(C, 3), pitch(G, 5), vel=v * 0.90, spacing=0.16, note_dur=1.8, ascending=True, max_notes=8)
        if i >= 4:
            sb.note("french_horn", sp.start, 3.5, sp.tenor_root() + P5, v * 0.88, swell="cresc" if i == 7 else "arch", vibrato=0.18)

    sb.phrase("cello", [
        (828.0, 3.6, pitch(G, 3, 0), 0.60),
        (832.0, 3.6, pitch(D, 3, 0), 0.62),
        (836.0, 3.6, pitch(EB, 3, 0), 0.64),
        (840.0, 3.6, pitch(G, 3, 0), 0.66),
        (844.0, 3.6, pitch(G, 3, 0), 0.68),
        (848.0, 3.6, pitch(A, 3, 1), 0.72),
        (852.0, 3.6, pitch(F, 3, 1), 0.74),
        (856.0, 3.6, pitch(G, 3, 1), 0.76),
    ], vibrato=0.28, slide_cents=18.0, snap=True)

    # --- Variation 4 (860..892, k=+1, accelerating 86 -> 104 BPM): 4-Voice Orchestral Fugato ---
    k1 = 1
    sb.phrase("clarinet", [
        (860.0, 0.85, pitch(C, 4, k1), 0.66), (861.0, 0.85, pitch(G, 4, k1), 0.70),
        (862.0, 0.42, pitch(AB, 4, k1), 0.68), (862.5, 0.42, pitch(G, 4, k1), 0.66),
        (863.0, 0.85, pitch(EB, 4, k1), 0.70), (864.0, 1.35, pitch(BB, 4, k1), 0.72),
        (865.5, 0.42, pitch(G, 4, k1), 0.68), (866.0, 1.60, pitch(D, 4, k1), 0.66),
        (869.0, 0.85, pitch(EB, 5, k1), 0.70), (870.0, 0.85, pitch(C, 5, k1), 0.68),
        (872.0, 1.80, pitch(BB, 4, k1), 0.72), (880.0, 0.85, pitch(G, 4, k1), 0.74),
        (881.0, 0.85, pitch(C, 5, k1), 0.76), (882.0, 1.70, pitch(EB, 5, k1), 0.78),
        (884.0, 1.80, pitch(C, 5, k1), 0.76), (888.0, 1.80, pitch(B, 4, k1), 0.78),
        (890.0, 1.70, pitch(D, 5, k1), 0.80),
    ], vibrato=0.18, snap=True)
    sb.phrase("viola", [
        (868.0, 0.85, pitch(EB, 4, k1), 0.68), (869.0, 0.85, pitch(AB, 4, k1), 0.72),
        (870.0, 0.42, pitch(G, 4, k1), 0.70), (870.5, 0.42, pitch(EB, 4, k1), 0.68),
        (871.0, 0.85, pitch(C, 4, k1), 0.70), (872.0, 1.35, pitch(G, 4, k1), 0.72),
        (876.0, 1.80, pitch(C, 4, k1), 0.70), (878.0, 1.80, pitch(F, 4, k1), 0.72),
        (884.0, 1.80, pitch(AB, 4, k1), 0.74), (888.0, 3.50, pitch(G, 4, k1), 0.76),
    ], vibrato=0.22, snap=True)
    sb.phrase("english_horn", [
        (876.0, 0.85, pitch(F, 4, k1), 0.72), (877.0, 0.85, pitch(AB, 4, k1), 0.75),
        (878.0, 0.85, pitch(G, 4, k1), 0.74), (880.0, 1.80, pitch(G, 4, k1), 0.76),
        (884.0, 0.85, pitch(EB, 4, k1), 0.76), (886.0, 1.70, pitch(C, 5, k1), 0.80),
        (888.0, 1.80, pitch(G, 4, k1), 0.78), (890.0, 1.70, 32 + HARM_7 - OCT, 0.80),
    ], vibrato=0.24, snap=True)
    for i, sp in enumerate(v4):
        br = sp.bass_root()
        if i < 6:
            sb.note("pizzicato", sp.start, 0.40, br + OCT, 0.58)
            sb.note("pizzicato", sp.start + 2.0, 0.40, br + OCT + P5, 0.54)
        else:
            sb.note("bassoon", sp.start, 1.8, br, 0.76, swell="arch")
            sb.note("bassoon", sp.start + 2.0, 1.8, br, 0.78, swell="arch")
            sb.note("cello", sp.start, 0.85, br + OCT, 0.78)
            sb.note("cello", sp.start + 1.0, 0.85, br + OCT + P5, 0.80)
            sb.note("cello", sp.start + 2.0, 1.70, br + 2 * OCT, 0.80, vibrato=0.24)

    # --- Variation 5 (892..924, k=+1, 104->122 BPM -> 74 BPM Subito pp Selberg Setback!) ---
    for i, sp in enumerate(v5):
        br = sp.bass_root()
        if i < 6:
            dyn = 0.76 + 0.02 * i
            sb.string_pad(sp, vel=dyn * 0.82, swell="sfz" if i in (0, 4) else "arch", include_ext=False)
            sb.note("bassoon", sp.start, 1.7, br, dyn * 0.90, swell="sfz")
            sb.note("bassoon", sp.start + 2.0, 1.7, br, dyn * 0.86, swell="arch")
            # Foreshadow Structure 3B Pair-Correlation Riff in Pizzicato + Piano!
            pts = sp.scale_steps(pitch(C, 3), pitch(C, 5), allow_melody=False)
            sb.emit_pair_correlation_riff(sp, "pizzicato", [br + OCT, br + OCT + P5], dyn * 0.86, dur=0.35)
            if pts:
                sb.emit_pair_correlation_riff(sp, "piano", pts[1:6], dyn * 0.82, dur=0.36)
            if i in (0, 2, 4, 5):
                sb.note("trombone", sp.start, 2.0, br, dyn * 0.86, swell="sfz")
                sb.note("french_horn", sp.start, 2.2, sp.tenor_root() + OCT, dyn * 0.88, swell="sfz")
                sb.note("timpani", sp.start, 0.8, br, dyn * 0.86, trim=False)
        else:
            # SUBITO PIANO SELBERG PARITY BARRIER at 916..924 (74 BPM, vel 0.30)!
            sb.string_pad(sp, vel=0.30, track_id="tremolo_strings", swell="dim", include_ext=False)
            sb.note("pizzicato", sp.start, 0.42, br + OCT, 0.32)

    # Human attempt #1: Flute tries to overlay Structure 1 (Prime Hook) in minor at 900.0 & 908.0 before hitting the wall!
    sb.emit_prime_hook("flute", 900.0, pitch(AB, 4, k1), vel=0.80, unit=0.5, use_septimal=False, snap=True)
    sb.emit_prime_hook("flute", 908.0, pitch(F, 4, k1), vel=0.82, unit=0.5, use_septimal=False, snap=True)
    sb.phrase("clarinet", [(916.5, 2.8, pitch(EB, 4, k1), 0.34), (920.0, 3.4, pitch(D, 4, k1), 0.30)], swell="dim", vibrato=0.20, snap=True)

    # --- Variation 6 (924..956, k=+1->+2, accelerating 80 -> 108 BPM): Persistent Rebuilding ---
    for i, sp in enumerate(v6):
        br = sp.bass_root()
        dyn = 0.56 + 0.032 * i
        sb.add_pedal(sp.start, 3.82)
        sb.string_pad(sp, vel=dyn * 0.84, swell="cresc", include_ext=True)
        sb.note("bassoon", sp.start, 3.5, br, dyn * 0.88, swell="cresc")
        sb.note("cello", sp.start, 3.5, br + OCT, dyn * 0.88, swell="cresc", vibrato=0.24)
        sb.harp_arp(sp, sp.start, pitch(C, 3), pitch(A, 5), vel=dyn * 0.90, spacing=0.16, note_dur=1.8, ascending=True, max_notes=8)
        if i >= 4:
            sb.note("french_horn", sp.start, 3.5, sp.tenor_root() + P5, dyn * 0.86, swell="cresc", vibrato=0.18)
        if i == 7:
            sb.timpani_roll(sp.start + 1.0, 2.8, br, 0.56, 0.78, subdiv=0.25)

    sb.phrase("english_horn", [
        (924.5, 3.2, pitch(G, 4, 1), 0.58), (928.5, 3.2, pitch(BB, 4, 1), 0.62),
        (932.5, 3.2, pitch(C, 5, 1), 0.66), (936.5, 3.2, pitch(BB, 4, 1), 0.70),
        (940.5, 3.2, pitch(B, 4, 1), 0.74), (944.5, 3.2, pitch(A, 4, 2), 0.76),
        (948.5, 3.2, pitch(C, 5, 2), 0.78), (952.5, 3.2, pitch(D, 5, 2), 0.80),
    ], swell="cresc", vibrato=0.28, slide_cents=16.0, snap=True)

    # --- Variation 7 (956..988, k=+2, 108 -> 128 BPM): STRUCTURE 3B — Montgomery–Odlyzko Pair-Correlation Riff! ---
    for i, sp in enumerate(v7):
        br = sp.bass_root()
        tr_r = sp.tenor_root()
        dyn = 0.68 + 0.010 * i
        # Bold Brass + String + Piano Pair-Correlation Riff [0.0, 0.75, 1.75, 2.50, 3.25]!
        sb.emit_pair_correlation_riff(sp, "french_horn", [tr_r + P5, tr_r + OCT], dyn * 0.88, dur=0.45, swell="sfz")
        if i % 2 == 0:
            sb.emit_pair_correlation_riff(sp, "trombone", [br], dyn * 0.84, dur=0.45, swell="sfz")
        sb.emit_pair_correlation_riff(sp, "pizzicato", [tr_r, tr_r + P5, tr_r + OCT], dyn * 0.86, dur=0.35)
        pts = sp.scale_steps(pitch(D, 3), pitch(F, 5), allow_melody=False)
        if pts:
            sb.emit_pair_correlation_riff(sp, "piano", pts[1:6], dyn * 0.82, dur=0.40)
            sb.emit_pair_correlation_riff(sp, "viola", pts[:4], dyn * 0.82, dur=0.44)
        sb.note("bassoon", sp.start, 3.6, br, dyn * 0.86, swell="arch")

    # --- Variation 8 (988..1020, k=+2->+3, 128 -> 136 BPM SURGE!): Human Overlays of Structures 1 & 2! ---
    for i, sp in enumerate(v8):
        br = sp.bass_root()
        tr_r = sp.tenor_root()
        dyn = 0.72 + 0.010 * i
        sb.string_pad(sp, vel=dyn * 0.78, swell="cresc", include_ext=True)
        sb.note("bassoon", sp.start, 3.6, br, dyn * 0.86, swell="cresc")
        sb.emit_pair_correlation_riff(sp, "pizzicato", [tr_r + P5, tr_r + OCT], dyn * 0.84, dur=0.32)
        if i in (0, 2, 4, 6, 7):
            sb.emit_pair_correlation_riff(sp, "french_horn", [tr_r + P5], dyn * 0.86, dur=0.42, swell="sfz")
            sb.note("timpani", sp.start, 0.9, br, dyn * 0.82, trim=False)
        # Human instruments attempt to lock Structure 1 (Prime Hook) & Structure 2 (Mirror Wedge) at 136 BPM!
        if i in (0, 2, 6):
            sb.emit_prime_hook("flute", sp.start, pitch(C, 5, 2 + (1 if i >= 6 else 0)), vel=dyn * 0.96, unit=0.5, use_septimal=False, snap=True)
        elif i in (1, 3, 5):
            sb.emit_mirror_wedge_bar(sp, "clarinet", "cello", vel=dyn * 0.92, diverging=(i != 3), vibrato=0.22)
        if i == 7:
            sb.timpani_roll(sp.start + 1.5, 2.4, br, 0.72, 0.84, subdiv=0.25)

    # --- Variation 9 (1020..1052, k=+3, 136 -> 132 BPM): Collision & Fracturing at the k=+3 Wall! ---
    k3 = 3
    for i, sp in enumerate(v9):
        br = sp.bass_root()
        tr_r = sp.tenor_root()
        dyn = 0.76 + 0.008 * min(i, 5)
        sb.string_pad(sp, vel=dyn * 0.86, track_id="tremolo_strings", swell="sfz", include_ext=False)
        sb.emit_pair_correlation_riff(sp, "trombone", [br], dyn * 0.88, dur=0.44, swell="sfz")
        sb.emit_pair_correlation_riff(sp, "piano", [tr_r, tr_r + P5, tr_r + OCT], dyn * 0.86, dur=0.38)
        # Fractured 4-note shards of Structure 1 (+0, +9, +14, +31 — snapping off short before +53!)
        if i % 2 == 0:
            r_sh = pitch(C, 5, k3)
            for j_s, iv_s in enumerate((0, M2, m3, P5)):
                sb.note("flute", sp.start + j_s * 0.5, 0.36, r_sh + iv_s, dyn * 0.94, snap_to_harmony=True)
                sb.note("clarinet", sp.start + 2.0 + j_s * 0.5, 0.36, r_sh - OCT + iv_s, dyn * 0.92, snap_to_harmony=True)

    # --- Variation 10 & 11 (1052..1116, k=+3, broadening 112 -> 78 -> 62 BPM): Colossal Brucknerian Climb! ---
    for v_idx, var_spans in enumerate((v10, v11)):
        for i, sp in enumerate(var_spans):
            br = sp.bass_root()
            tr_r = sp.tenor_root()
            dyn = (0.76 + 0.008 * i) if v_idx == 0 else (0.80 + 0.006 * min(i, 5))
            sb.string_pad(sp, vel=dyn * 0.80, swell="sfz" if i % 2 == 0 else "arch", include_ext=True)
            if v_idx == 1:
                sb.string_pad(sp, vel=dyn * 0.70, track_id="tremolo_strings", swell="arch", include_ext=False)
            sb.note("bassoon", sp.start, 3.6, br, dyn * 0.86, swell="sfz")
            if i % 2 == 0 or v_idx == 1:
                sb.note("trombone", sp.start, 3.5, br, dyn * 0.84, swell="sfz")
            sb.note("french_horn", sp.start, 1.8, tr_r + OCT, dyn * 0.86, swell="sfz")
            sb.note("french_horn", sp.start + 2.0, 1.7, tr_r + P5, dyn * 0.84, swell="arch")
            sb.note("timpani", sp.start + 0.02, 1.1, br, dyn * 0.84, trim=False)
            if v_idx == 1 and i in (3, 7):
                sb.timpani_roll(sp.start + 2.0, 1.9, br, 0.74, 0.86, subdiv=0.25)
            sb.chord("piano", sp.start, 1.5, [tr_r, tr_r + P5, tr_r + OCT], dyn * 0.80)
            sb.chord("piano", sp.start + 2.0, 1.5, [tr_r + P5, tr_r + OCT], dyn * 0.78)

    sb.phrase("clarinet", [
        (1084.0, 1.8, pitch(C, 5, k3), 0.86), (1086.0, 1.8, pitch(EB, 5, k3), 0.89),
        (1088.0, 3.6, pitch(D, 5, k3), 0.88), (1092.5, 1.4, pitch(C, 5, k3), 0.88),
        (1094.0, 1.8, pitch(EB, 5, k3), 0.90), (1096.0, 3.6, pitch(BB, 4, k3), 0.88),
        (1100.5, 3.2, pitch(C, 5, k3), 0.90), (1104.0, 3.6, pitch(G, 5, k3), 0.91),
        (1108.5, 3.2, pitch(EB, 5, k3), 0.90), (1112.0, 3.6, pitch(D, 5, k3), 0.91),
    ], swell="sfz", vibrato=0.24, snap=True)

    # --- Variation 12 (1116..1154, k=+3, 62 -> 60 BPM): MONUMENTAL UNRESOLVED SUMMIT (G+++7 Step 24)! ---
    for i, sp in enumerate(v12):
        dur = sp.end - sp.start
        br = sp.bass_root()
        dyn = [0.74, 0.68, 0.62, 0.58, 0.54, 0.50][i]
        sb.string_pad(sp, vel=dyn * 0.86, track_id="tremolo_strings", swell="dim" if i == 5 else "arch", include_ext=False)
        if i <= 4:
            sb.note("bassoon", sp.start, dur - 0.35, br, dyn * 0.88, swell="dim")
            sb.note("cello", sp.start, dur - 0.35, br + OCT, dyn * 0.90, swell="dim", vibrato=0.28)
        else:
            # Final 14-beat Unresolved G+++ dom7 (root=34: [34, 51, 12, 24]) hanging in frozen suspense!
            sb.timpani_roll(sp.start, dur - 0.5, br, 0.54, 0.38, subdiv=0.35)
            sb.note("bassoon", sp.start, 11.5, br, 0.50, swell="dim")
            # English Horn, Viola & French Horn freeze on the unresolved septimal 7th step = 24!
            sb.note("english_horn", sp.start + 0.5, 12.0, 24, 0.54, swell="dim", vibrato=0.32, snap_to_harmony=False)
            sb.note("viola", sp.start + 1.0, 12.0, 51 - OCT, 0.48, swell="dim", vibrato=0.24, snap_to_harmony=False)
            sb.note("french_horn", sp.start + 1.5, 10.5, 12, 0.48, swell="dim", vibrato=0.18, snap_to_harmony=False)


# =============================================================================
# MOVEMENT IV — AI (BAMBOO FLUTE SYNTH), UNIFIED TRIUMPH & MELANCHOLY FOR HUMANITY
# (Beats 1154..1563 + 5.0s tail, ~11:25 – 15:00, 152 -> 168 -> 122 -> 52 BPM)
# =============================================================================
def compose_movement_4(sb: RiemannSymphonyBuilder) -> None:
    sb.add_section(1154.0, "IV.1 The Herald: Zero-Free Strips — Cold Breakthrough in the Strip (152 BPM)")
    sb.add_section(1254.0, "IV.2 The Oracle: Inspired Synthesis — All Structures Snap-Fit (168 BPM)")
    sb.add_section(1394.0, "IV.3 Triumph of the Proof — Pipe Organ & Full Orchestra Unite All Structures (122 BPM)")
    sb.add_section(1506.0, "IV.4 Epilogue: Melancholy for Humanity — Eternal Halo & Lone Human Farewell (52 BPM)")

    m4_specs = [
        # --- IV.1 (1154..1254, 25 bars x 4 beats @ 152 BPM): The Herald — Zero-Free Strip Narrowing! ---
        # Steps directly out of unresolved step 24 (F++4/F++5 = 24/77) across 11-limit (24) & 13-limit (37) bounds!
        (1154.0, 1158.0, 0, "prime13", "IV.1.1 SOLO THE HERALD: Stepping Out of Step 24 Across 11 & 13-Limit Bounds"),
        (1158.0, 1162.0, 24, "prime13", "IV.1.2 SOLO THE HERALD: Angular 11/13-Limit Strip Probe (F++ prime13)"),
        (1162.0, 1166.0, 10, "min7", "IV.1.3 The Herald + Lattice: Strip Scan Dm+(10)"),
        (1166.0, 1170.0, 33, "dom9", "IV.1.4 The Herald + Lattice: Strip Scan G++ dom9(33)"),
        (1170.0, 1174.0, 2, "dom9", "IV.1.5 Zero-Free Strip Narrowing C++(k=+2)"),
        (1174.0, 1178.0, 41, "min7", "IV.1.6 Strip Bound Am++(41)"),
        (1178.0, 1182.0, 24, "maj69", "IV.1.7 Strip Bound F++(24)"),
        (1182.0, 1186.0, 32, "dom9", "IV.1.8 First Bound Shift V9+(k=+1)"),
        (1186.0, 1190.0, 1, "dom9", "IV.1.9 Strip Scan C+(k=+1)"),
        (1190.0, 1194.0, 40, "min7", "IV.1.10 Strip Scan Am+(40)"),
        (1194.0, 1198.0, 23, "maj69", "IV.1.11 Strip Scan F+(23)"),
        (1198.0, 1202.0, 9, "min7", "IV.1.12 Strip Scan Dm(9)"),
        (1202.0, 1206.0, 31, "dom9", "IV.1.13 Critical Strip Glimpse G dom9(k=0)"),
        (1206.0, 1210.0, 0, "prime11", "IV.1.14 Overtone Probe C prime11"),
        (1210.0, 1214.0, 36, "maj7", "IV.1.15 Analytic Probe Ab(36)"),
        (1214.0, 1218.0, 19, "maj", "IV.1.16 Analytic Probe E-(19)"),
        (1218.0, 1222.0, 2, "add9", "IV.1.17 Analytic Probe C++(2)"),
        (1222.0, 1226.0, 24, "maj", "IV.1.18 Re-centering F++(24)"),
        (1226.0, 1230.0, 33, "dom9", "IV.1.19 Strip Bound G++(33)"),
        (1230.0, 1234.0, 3, "min", "IV.1.20 Re-engaging k=+3 Wall Cm+++(3)!"),
        (1234.0, 1238.0, 39, "maj7", "IV.1.21 Strip Bound Ab+++(39)"),
        (1238.0, 1242.0, 25, "min7", "IV.1.22 Strip Bound Fm+++(25)"),
        (1242.0, 1246.0, 34, "dom9", "IV.1.23 Summit Lock G+++ dom9(34)"),
        (1246.0, 1250.0, 3, "dom9", "IV.1.24 Herald Handoff C+++ dom9(3)"),
        (1250.0, 1254.0, 34, "dom9", "IV.1.25 Summoning The Oracle (G+++ dom9)!"),

        # --- IV.2 (1254..1394, 35 bars x 4 beats @ 168 BPM): Inspired Full Synthesis! ---
        # Phase A (1254..1302, 12 bars): Snap-fitting Structure 1 (Prime Hook) INSIDE Structure 2 (Mirror Wedge)!
        (1254.0, 1258.0, C + 3, "mirror_maj", "IV.2.1 AI Synthesis: Prime Hook in Mirror Wedge C+++"),
        (1258.0, 1262.0, C + 3, "dom9", "IV.2.2 AI Synthesis: Septimal Lock C+++"),
        (1262.0, 1266.0, A + 3, "mirror_min", "IV.2.3 AI Synthesis: Mirror Wedge Am+++"),
        (1266.0, 1270.0, F + 3, "mirror_maj", "IV.2.4 AI Synthesis: Mirror Wedge F+++"),
        (1270.0, 1274.0, G + 3, "dom9", "IV.2.5 AI Synthesis: Prime Hook V9+++"),
        (1274.0, 1278.0, C + 2, "mirror_maj", "IV.2.6 Comma Step Down k=+2: C++"),
        (1278.0, 1282.0, A + 2, "mirror_min", "IV.2.7 Mirror Wedge Am++"),
        (1282.0, 1286.0, F + 2, "mirror_maj", "IV.2.8 Mirror Wedge F++"),
        (1286.0, 1290.0, G + 2, "dom9", "IV.2.9 Prime Hook V9++"),
        (1290.0, 1294.0, C + 1, "mirror_maj", "IV.2.10 Comma Step Down k=+1: C+"),
        (1294.0, 1298.0, F + 1, "mirror_maj", "IV.2.11 Mirror Wedge F+"),
        (1298.0, 1302.0, G + 3, "dom9", "IV.2.12 Full Ladder Reset V9+++ for Passacaglia Lock!"),
        # Phase B (1302..1394, 23 bars): Locking Structures 1+2 onto Structure 3B+3A down k=+3 -> +2 -> +1 -> 0!
        # Step k = +3 (1302..1318, 4 bars):
        (1302.0, 1306.0, C + 3, "min", "IV.2.13 Full Lock k=+3: Cm+++"),
        (1306.0, 1310.0, AB + 3, "maj7", "IV.2.14 Full Lock k=+3: Ab+++"),
        (1310.0, 1314.0, F + 3, "maj69", "IV.2.15 Pivot Down: F+++"),
        (1314.0, 1318.0, G + 2, "dom9", "IV.2.16 Comma Unlock -> k=+2 (G++ dom9)"),
        # Step k = +2 (1318..1334, 4 bars):
        (1318.0, 1322.0, C + 2, "dom9", "IV.2.17 Full Lock k=+2: C++ dom9"),
        (1322.0, 1326.0, A + 2, "min7", "IV.2.18 Full Lock k=+2: Am++"),
        (1326.0, 1330.0, F + 2, "maj69", "IV.2.19 Pivot Down: F++"),
        (1330.0, 1334.0, G + 1, "dom9", "IV.2.20 Comma Unlock -> k=+1 (G+ dom9)"),
        # Step k = +1 (1334..1350, 4 bars):
        (1334.0, 1338.0, C + 1, "dom9", "IV.2.21 Full Lock k=+1: C+ dom9"),
        (1338.0, 1342.0, A + 1, "min7", "IV.2.22 Full Lock k=+1: Am+"),
        (1342.0, 1346.0, F + 1, "maj69", "IV.2.23 Pivot Down: F+"),
        (1346.0, 1350.0, G + 0, "dom9", "IV.2.24 CRITICAL LINE UNLOCKED -> k=0 (G dom9)!"),
        # Home Plane k = 0 Convergence & Blazing Dominant Herald (1350..1394, 11 bars):
        (1350.0, 1354.0, C, "prime11", "IV.2.25 Critical Line Locked: C prime11 (k=0)!"),
        (1354.0, 1358.0, G, "dom9", "IV.2.26 Critical Line V9"),
        (1358.0, 1362.0, A, "mirror_min", "IV.2.27 Critical Line Am"),
        (1362.0, 1366.0, F, "mirror_maj", "IV.2.28 Critical Line F"),
        (1366.0, 1370.0, C, "mirror_maj", "IV.2.29 Critical Line C"),
        (1370.0, 1374.0, D_MINUS, "min7", "IV.2.30 Pre-Triumph Surge ii"),
        (1374.0, 1378.0, F, "maj9", "IV.2.31 Pre-Triumph Pillar IV"),
        (1378.0, 1386.0, G, "sus4", "IV.2.32 Dominant Herald G sus4"),
        (1386.0, 1394.0, G, "dom9", "IV.2.33 Blazing Dominant Herald G dom9 (4:5:6:7:9)!"),

        # --- IV.3 (1394..1506, 28 bars x 4 beats @ 122 BPM Maestoso): TRIUMPH OF THE PROOF! ---
        # church_organ enters FOR THE VERY FIRST TIME at beat 1394.0!
        # Grand Wave 1 (1394..1442, 12 bars): Major-Transfigured Passacaglia + Structures 1, 2, 3!
        (1394.0, 1398.0, C, "dom9", "IV.3.1 ORGAN ENTRY: Triumph of the Proof I (C 4:5:6:7:9)"),
        (1398.0, 1402.0, G, "dom9", "IV.3.2 Triumph V (G dom9)"),
        (1402.0, 1406.0, A, "min7", "IV.3.3 Triumph vi (Am7)"),
        (1406.0, 1410.0, E, "min7", "IV.3.4 Triumph iii (Em7)"),
        (1410.0, 1414.0, F, "maj69", "IV.3.5 Triumph IV (F maj69)"),
        (1414.0, 1418.0, C, "mirror_maj", "IV.3.6 Triumph Mirror I (C mirror_maj)"),
        (1418.0, 1422.0, D_MINUS, "min9", "IV.3.7 Triumph ii (Dm-9)"),
        (1422.0, 1426.0, G, "dom9", "IV.3.8 Triumph V9"),
        (1426.0, 1430.0, AB, "maj7", "IV.3.9 Heroic Brucknerian Blaze bVI (Ab maj7)"),
        (1430.0, 1434.0, F, "maj9", "IV.3.10 Radiant Subdominant IV"),
        (1434.0, 1442.0, G, "dom9", "IV.3.11 Roaring Cadential V9"),
        # Grand Wave 2 (1442..1506, 16 bars): Ultimate Unified Crown on Home k = 0!
        (1442.0, 1450.0, C, "prime11", "IV.3.12 Prime-11 & Organ Crown I (C 4:5:6:7:9:11)"),
        (1450.0, 1458.0, C, "mirror_maj", "IV.3.13 Mirror & Organ Crown I (C mirror_maj)"),
        (1458.0, 1466.0, F, "maj69", "IV.3.14 Cathedral Expanse IV (F maj69)"),
        (1466.0, 1474.0, A, "mirror_min", "IV.3.15 Luminous Mediant vi (Am)"),
        (1474.0, 1482.0, F, "dom9", "IV.3.16 Septimal Subdominant Glow (F dom9)"),
        (1482.0, 1490.0, G, "dom9", "IV.3.17 Ultimate Symphonic Climax V9 (4:5:6:7:9)!"),
        (1490.0, 1498.0, C, "add9", "IV.3.18 Proof Resolution I (C add9)"),
        (1498.0, 1506.0, C, "maj", "IV.3.19 Radiant C-Major Q.E.D. Chord (4:5:6)"),

        # --- IV.4 (1506..1563, 57 beats @ 52 BPM Adagio malinconico): MELANCHOLY FOR HUMANITY! ---
        # Brass, timpani, and church_organ 100% SILENT!
        # High AI Halo ({0, 31, 43} in G5..C6) + Lone Human Cello & English Horn 16:15 & -1 Comma Farewell!
        (1506.0, 1514.0, C, "dom9", "IV.4.1 Silence Falls — Complete 6-Note Prime Curiosity Remembrance"),
        (1514.0, 1522.0, C, "halo_maj_sigh", "IV.4.2 First -1 Comma Human Sigh (E -> E-)"),
        (1522.0, 1530.0, C, "halo_phryg", "IV.4.3 Human Passacaglia Ground I (C3 -> G2 -> Ab2 -> Eb3)"),
        (1530.0, 1534.0, C, "halo_phryg", "IV.4.4a Human Passacaglia Ground II (F3 -> C3)"),
        (1534.0, 1538.0, C, "halo_comma_sigh", "IV.4.4b Aching -1 Comma Passacaglia Sigh (Ab-2 -> G2, Eb-4)"),
        (1538.0, 1546.0, C, "halo_phryg", "IV.4.5 Last Fragile 16:15 Sigh (Db4 -> C4)"),
        (1546.0, 1554.0, C, "prime7", "IV.4.6 Strings Vanish — Lone Human Breath Under Machine Perfection"),
        (1554.0, 1563.0, C, "prime7", "IV.4.7 Eternal 53-EDO Fifth/Seventh Halo into Silence"),
    ]
    spans = [sb.add_span(*c) for c in m4_specs]

    # =========================================================================
    # IV.1 (1154..1254, 152 BPM): The Herald (Zero-Free Strip) + Crystalline Lattice!
    # Zero scoops (slide_from_cents=0.0), zero <0.45b chatter (all dur in 0.48..1.82b),
    # tamed poised velocity (0.48..0.60), and shimmering C5–D6 piano/harp/pizzicato lattice!
    # =========================================================================
    iv1_spans = [sp for sp in spans if 1154.0 <= sp.start < 1254.0]

    # Bars 0..1 (1154.0..1162.0, ~3.2s): 100% SOLO ai_strip ("The Herald") stepping out of
    # the unresolved step 24 (F++ -> 77) in chilling, angular 0.5–1.5b leaps across
    # 11-limit (24/77, 48/101) and 13-limit (37/90, 61/114) bounds at vel 0.48–0.57!
    solo_herald_opening = [
        # Bar 0 (1154..1158, C prime13: {0, 9, 17, 24, 31, 37, 43})
        (1154.0, 1.42, PRIME_11 + OCT, 0.48),          # 77 (F++5 = step 24 + OCT: cold emergence!)
        (1155.5, 0.92, PRIME_13, 0.52),                # 37 (13:8 lower strip bound)
        (1156.5, 0.48, PRIME_13 + OCT, 0.55),          # 90 (13:8 upper octave bound)
        (1157.0, 0.88, PRIME_11 + OCT, 0.51),          # 77 (11:8 bound return)
        # Bar 1 (1158..1162, F++ prime13: {24, 33, 41, 48, 2, 8, 14})
        (1158.0, 0.92, 24 + PRIME_11, 0.52),           # 48 (11:8 above step 24)
        (1159.0, 0.48, 24 + PRIME_13 + OCT, 0.56),     # 114 (13:8 high strip ceiling)
        (1159.5, 0.92, 24 + PRIME_13, 0.53),           # 61 (13:8 middle probe)
        (1160.5, 1.38, 24 + PRIME_11 + OCT, 0.57),     # 101 (poised 1.38b 11-limit hold)
    ]
    for b_h, d_h, st_h, v_h in solo_herald_opening:
        sb.note("ai_strip", b_h, d_h, st_h, v_h, slide_from_cents=0.0, swell="none", vibrato=0.0, snap_to_harmony=False, trim=False)

    hook_bars_iv1 = {
        4: 2 + OCT,      # 1170..1174: C++5 (55) on C++ dom9 (k=+2)
        8: 1 + OCT,      # 1186..1190: C+5 (54) on C+ dom9 (k=+1)
        13: 0 + OCT,     # 1206..1210: C5 (53) on C prime11 (k=0)
        18: 33,          # 1226..1230: G++4 (33) on G++ dom9
        23: 3 + OCT,     # 1246..1250: C+++5 (56) on C+++ dom9 (k=+3)
    }

    for i, sp in enumerate(iv1_spans):
        if i < 2:
            continue
        u_lat = (i - 2) / 22.0
        herald_v = 0.50 + 0.08 * u_lat   # Tamed, poised 0.50 -> 0.58 (strictly <= 0.60!)

        # 1. THE HERALD (ai_strip): sleek 0.48–1.82b prime-interval probes & Structure 1 statements!
        if i in hook_bars_iv1:
            # Clean, glassy Structure 1 (Prime Curiosity Hook [+0,+9,+17,+31,+43,+53]) in 2+3+2 rhythm
            # with every note >= 0.48b (0.48, 0.48, 0.48, 0.48, 0.48, 1.38) and zero pitch scoops!
            base_h = hook_bars_iv1[i]
            hook_onsets = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5)
            hook_durs = (0.48, 0.48, 0.48, 0.48, 0.48, 1.38)
            hook_accs = (1.00, 0.94, 1.02, 0.95, 0.97, 1.03)
            for off_iv, ro, rd, acc in zip(PRIME_HOOK_OFFSETS, hook_onsets, hook_durs, hook_accs):
                sb.note(
                    "ai_strip",
                    sp.start + ro,
                    rd,
                    base_h + off_iv,
                    min(0.60, herald_v * acc),
                    slide_from_cents=0.0,
                    swell="none",
                    vibrato=0.0,
                    snap_to_harmony=False,
                    trim=False,
                )
        elif i == 24:
            # Final bar (1250..1254, G+++ dom9): conquering step 24 (77) and summoning The Oracle!
            for ro, rd, st_f, v_f in (
                (0.0, 0.92, 51, 0.55),
                (1.0, 0.92, PRIME_11 + OCT, 0.57),
                (2.0, 1.82, 51 + OCT, 0.60),
            ):
                sb.note("ai_strip", sp.start + ro, rd, st_f, v_f, slide_from_cents=0.0, swell="none", vibrato=0.0, snap_to_harmony=False, trim=False)
        else:
            # Inward-narrowing zero-free-strip bounds across G4..Eb6 (36..116 -> 58..96)!
            narrow_u = min(1.0, (i - 2) / 20.0)
            lo_lim = int(round(36 + 22 * narrow_u))
            hi_lim = int(round(116 - 20 * narrow_u))
            sub_pts = sp.scale_steps(lo_lim, hi_lim, allow_melody=False)
            if len(sub_pts) < 3:
                sub_pts = sp.scale_steps(36, 116, allow_melody=False)
            if sub_pts:
                n_s = len(sub_pts)
                p_lo = sub_pts[0]
                p_hi = sub_pts[-1]
                p_mid_lo = sub_pts[min(n_s - 1, max(1, n_s // 3))]
                p_mid_hi = sub_pts[max(0, min(n_s - 2, (2 * n_s) // 3))]
                cell_type = i % 4
                if cell_type == 2:
                    probe_notes = [
                        (0.0, 0.92, p_lo, 0.98),
                        (1.0, 0.48, p_hi, 1.02),
                        (1.5, 0.92, p_mid_lo, 0.96),
                        (2.5, 1.38, p_mid_hi, 1.01),
                    ]
                elif cell_type == 3:
                    probe_notes = [
                        (0.0, 1.40, p_hi, 1.01),
                        (1.5, 0.48, p_lo, 0.95),
                        (2.0, 0.92, p_mid_hi, 0.99),
                        (3.0, 0.88, p_mid_lo, 0.96),
                    ]
                elif cell_type == 1:
                    probe_notes = [
                        (0.0, 0.48, p_mid_lo, 0.95),
                        (0.5, 0.92, p_hi, 1.02),
                        (1.5, 1.40, p_lo, 0.99),
                        (3.0, 0.88, p_mid_hi, 0.97),
                    ]
                else:
                    probe_notes = [
                        (0.5, 0.92, p_hi, 1.00),
                        (1.5, 0.48, p_mid_lo, 0.95),
                        (2.0, 0.48, p_lo, 0.96),
                        (2.5, 1.38, p_mid_hi, 1.02),
                    ]
                for ro, rd, st_p, acc in probe_notes:
                    sb.note(
                        "ai_strip",
                        sp.start + ro,
                        rd,
                        st_p,
                        min(0.60, max(0.49, herald_v * acc)),
                        slide_from_cents=0.0,
                        swell="none",
                        vibrato=0.0,
                        snap_to_harmony=False,
                        trim=False,
                    )

        # 2. SHIMMERING ZERO-FREE-STRIP LATTICE (beat 1162.0 onward, i >= 2):
        # Crisp, quiet high Piano (C5–D6 = 53..115, vel 0.38–0.50) + Harp + Pizzicato!
        pts_p = sp.scale_steps(pitch(C, 5), pitch(D, 6), allow_melody=False)
        if pts_p:
            p_base = 0.39 + 0.07 * u_lat   # 0.39 -> 0.46
            n_p = len(pts_p)
            if i < 8:
                lat_slots = (0.0, 0.5, 1.0, 1.5, 1.75, 2.0, 2.5, 3.0, 3.5, 3.75)
                p_dur = 0.21
            else:
                lat_slots = (0.0, 0.25, 0.5, 1.0, 1.25, 1.5, 2.0, 2.25, 2.5, 3.0, 3.25, 3.5)
                p_dur = 0.20
            for idx_l, off_l in enumerate(lat_slots):
                if idx_l % 2 == 0:
                    st_lat = pts_p[(idx_l // 2 + i) % n_p]
                else:
                    st_lat = pts_p[-1 - ((idx_l // 2 + i * 2) % n_p)]
                v_lat = min(0.50, max(0.38, p_base * (1.05 if off_l in (0.0, 2.0) else 0.95)))
                sb.note(
                    "piano",
                    sp.start + off_l,
                    p_dur,
                    st_lat,
                    v_lat,
                    snap_to_harmony=False,
                    max_step_override=pitch(D, 6),
                )

        # Crisp chamber Pizzicato strip-markers
        r_ten = sp.tenor_root()
        pizz_v = 0.40 + 0.08 * u_lat
        sb.note("pizzicato", sp.start + 0.0, 0.28, r_ten + OCT, pizz_v)
        sb.note("pizzicato", sp.start + 1.5, 0.26, r_ten + P5, pizz_v * 0.94)
        sb.note("pizzicato", sp.start + 2.75, 0.26, r_ten, pizz_v * 0.92)

        # Shimmering Harp arpeggios spinning through the lattice
        if i % 2 == 0 or i in (3, 13, 19, 23):
            sb.harp_arp(
                sp,
                sp.start + 0.12,
                pitch(C, 4),
                pitch(C, 6),
                vel=0.41 + 0.07 * u_lat,
                spacing=0.16,
                note_dur=0.68,
                ascending=(i % 4 < 2),
                max_notes=6,
            )

        # Subtle warm Cello chamber pulse on alternate bars from i=4 onward
        if i >= 4 and i % 2 == 0:
            sb.note("cello", sp.start + 1.0, 0.46, sp.bass_root() + OCT, 0.40 + 0.06 * u_lat, swell="none")

    # =========================================================================
    # IV.2 (1254..1394, 168 BPM): ai_architect + ai_strip Full Synthesis!
    # =========================================================================
    iv2_spans = [sp for sp in spans if 1254.0 <= sp.start < 1394.0]
    for i, sp in enumerate(iv2_spans):
        dur = sp.end - sp.start
        dyn = 0.62 + 0.14 * (i / max(1, len(iv2_spans) - 1))   # Surges 0.62 -> 0.76 cleanly!
        br = sp.bass_root()
        tr_r = sp.tenor_root()

        if i < 12:
            # PHASE A (1254..1302): Structure 1 (Prime Hook) SNAP-FIT INSIDE Structure 2 (Mirror Wedge)!
            # ai_strip fires Structure 1 ascending in 2+3+2 rhythm while ai_architect simultaneously
            # fires the EXACT 53-EDO pitch-inverted Mirror Prime Hook (u + l = S_ai) in G4..E6!
            hook_base = max(48, min(62, sp.nearest_step(53, allow_melody=False)))
            use_7 = "dom" in sp.quality
            offs_h = PRIME_HOOK_OFFSETS if use_7 else PRIME_HOOK_MAJ_OFFSETS
            S_ai = 2 * hook_base + (HARM_7 if use_7 else M7)
            for iv_h, ro, rd, acc in zip(offs_h, (0.0, 1.0, 2.0, 3.0, 4.0, 5.0), (0.68, 0.68, 0.68, 0.68, 0.72, 1.72), (1.02, 0.92, 1.04, 0.94, 0.96, 1.06)):
                t_h = sp.start + ro * 0.5
                d_h = rd * 0.5
                u_ai = sp.nearest_step(hook_base + iv_h, allow_melody=False)
                l_ai = sp.nearest_step(S_ai - (hook_base + iv_h), allow_melody=False)
                while l_ai < 34:
                    l_ai += OCT
                while l_ai > 120:
                    l_ai -= OCT
                sb.note("ai_strip", t_h, d_h, u_ai, dyn * acc, swell="none", vibrato=0.0, snap_to_harmony=False)
                if abs(u_ai - l_ai) == 0 or abs(u_ai - l_ai) >= 8:
                    sb.note("ai_architect", t_h, d_h, l_ai, dyn * 0.96 * acc, swell="none", vibrato=0.0, snap_to_harmony=False)

            # Human strings & winds catch the exact lower Mirror Wedge reflection!
            sb.emit_mirror_wedge_bar(sp, "flute" if i % 2 == 0 else "clarinet", "cello" if i % 2 == 0 else "viola", vel=dyn * 0.86, diverging=(i % 2 == 0), vibrato=0.20)
            sb.harp_arp(sp, sp.start, pitch(C, 4), pitch(C, 6), vel=dyn * 0.86, spacing=0.14, note_dur=0.95, ascending=(i % 2 == 0), max_notes=7)

        else:
            # PHASE B (1302..1394): Locking Structures 1 + 2 onto Structure 3B (Pair-Correlation) + 3A (Passacaglia)
            # while stepping cleanly down k = +3 -> +2 -> +1 -> 0!
            pts_arch = sp.scale_steps(36, 122, allow_melody=False)
            if len(pts_arch) >= 4 and dur <= 4.5:
                # ai_architect punches multi-voice synth-flute chords on the EXACT Structure 3B Pair-Correlation Riff!
                for g_i, off in enumerate(PAIR_CORR_OFFSETS):
                    v1_s = pts_arch[-1 - (g_i % 3)]
                    v2_s = pts_arch[max(0, len(pts_arch) - 4 - (g_i % 2))]
                    sb.note("ai_architect", sp.start + off, 0.38, v1_s, dyn * 0.95, swell="none", vibrato=0.0, snap_to_harmony=False)
                    if abs(v1_s - v2_s) >= 12:
                        sb.note("ai_architect", sp.start + off, 0.38, v2_s, dyn * 0.88, swell="none", vibrato=0.0, snap_to_harmony=False)

                # ai_strip weaves 16th-note cascades & Prime Curiosity Hooks on every comma-unlock bar!
                if (i - 12) % 4 in (0, 3):
                    hb = max(36, min(68, sp.nearest_step(53, allow_melody=False)))
                    sb.emit_prime_hook("ai_strip", sp.start, hb, vel=dyn * 0.98, unit=0.5, staccato=True, snap=True)
                else:
                    for s8 in range(8):
                        sb.note("ai_strip", sp.start + s8 * 0.5 + 0.25, 0.22, pts_arch[(s8 * 2 + i) % len(pts_arch)], dyn * 0.92, swell="none", vibrato=0.0, snap_to_harmony=False)
            elif len(pts_arch) >= 4:
                # Dominant Herald bars 1378..1394 (8-beat spans): blazing interlocking AI synth-flutes + timpani roll!
                sb.emit_prime_hook("ai_strip", sp.start, pitch(G, 4), vel=dyn, unit=0.5, staccato=True, snap=True)
                sb.emit_prime_hook("ai_architect", sp.start + 4.0, pitch(G, 4), vel=dyn * 1.02, unit=0.5, staccato=True, snap=True)
                sb.harp_arp(sp, sp.start, pitch(C, 3), pitch(C, 6), vel=dyn * 0.94, spacing=0.14, note_dur=1.6, ascending=True, max_notes=10)
                sb.timpani_roll(sp.start, dur - 0.3, br, dyn * 0.82, dyn * 0.98, subdiv=0.25)

            # Structure 3A Passacaglia Ground in Bassoon/Cello + Structure 3B in Pizzicato/Piano/Horns!
            sb.note("bassoon", sp.start, min(3.6, dur - 0.3), br, dyn * 0.90, swell="cresc")
            sb.string_pad(sp, vel=dyn * 0.82, swell="cresc", include_ext=(i >= 24))
            sb.emit_pair_correlation_riff(sp, "pizzicato", [tr_r + P5, tr_r + OCT], dyn * 0.88, dur=0.32)
            pts_p = sp.scale_steps(pitch(C, 3), pitch(G, 5), allow_melody=False)
            if pts_p:
                sb.emit_pair_correlation_riff(sp, "piano", pts_p[1:6], dyn * 0.84, dur=0.35)
            if i >= 24:
                sb.note("french_horn", sp.start, min(3.6, dur - 0.3), tr_r + P5, dyn * 0.88, swell="cresc")
                sb.note("trombone", sp.start, min(3.6, dur - 0.3), br, dyn * 0.86, swell="cresc")

    # =========================================================================
    # IV.3 (1394..1506, 122 BPM Maestoso): TRIUMPH OF THE PROOF!
    # church_organ enters FOR THE VERY FIRST TIME + Full Orchestra + AI Flutes
    # Simultaneously uniting Structure 1, Structure 2, and Structure 3A+3B!
    # =========================================================================
    apoth_spans = [sp for sp in spans if 1394.0 <= sp.start < 1506.0]
    for i, sp in enumerate(apoth_spans):
        dur = sp.end - sp.start
        br = sp.bass_root()
        tr_r = sp.tenor_root()
        q_th = m3 if "min" in sp.quality else M3
        # Grand symphonic dynamic arch: brass & AI flutes soar (0.82..0.90) while church_organ
        # sits at a warm cathedral foundation (0.54..0.62) and accompaniment pads stay transparent!
        arch_u = math.sin(math.pi * min(1.0, (i + 1) / 17.5))
        org_v = 0.54 + 0.06 * arch_u
        brass_v = 0.80 + 0.06 * arch_u
        lead_v = 0.83 + 0.06 * arch_u
        if i == 16:
            org_v = 0.62
            brass_v = 0.88
            lead_v = 0.91

        # 1. STRUCTURE 3A: Cathedral Pipe Organ (5-voice pure registration C2..E5) + Bassoon!
        org_voic = [br, br + OCT, tr_r + P5, tr_r + OCT, tr_r + OCT + q_th]
        sb.chord("church_organ", sp.start, dur - 0.16, org_voic, org_v, swell="cresc" if i == 16 else "arch")
        sb.note("bassoon", sp.start, min(3.8, dur - 0.25), br, 0.72 + 0.05 * arch_u, swell="arch")

        # 2. STRUCTURE 3B: Bold Brass + Timpani + Pizzicato Pair-Correlation Fanfare [0, 0.75, 1.75, 2.50, 3.25]!
        if i % 2 == 0 or i in (10, 16):
            sb.emit_pair_correlation_riff(sp, "trombone", [br], brass_v, dur=0.52, swell="sfz")
            sb.emit_pair_correlation_riff(sp, "french_horn", [tr_r + P5, tr_r + OCT], brass_v * 1.01, dur=0.52, swell="sfz")
            sb.note("timpani", sp.start + 0.03, 1.1, br, brass_v * 0.90, trim=False)
            if i == 16:
                sb.timpani_roll(sp.start + 4.0, 3.7, br, 0.72, 0.84, subdiv=0.25)
        else:
            sb.note("french_horn", sp.start, min(3.6, dur - 0.25), tr_r + P5, brass_v * 0.96, swell="arch", vibrato=0.16)
            sb.note("trombone", sp.start, min(3.4, dur - 0.35), br, brass_v * 0.92, swell="arch")
        sb.emit_pair_correlation_riff(sp, "pizzicato", [tr_r + P5, tr_r + OCT], 0.70 + 0.06 * arch_u, dur=0.35)

        # Lush String Ensemble + Radiant Pedaled Piano Chords/Octaves + Sweeping Harp (all 17 tracks active!)
        use_ext = sp.quality not in ("maj7", "mirror_maj")
        sb.string_pad(sp, vel=0.50 + 0.06 * arch_u, swell="arch", include_ext=use_ext)
        if i in (0, 8, 10, 11, 16, 17):
            sb.string_pad(sp, vel=0.46 + 0.05 * arch_u, track_id="tremolo_strings", swell="arch", include_ext=False)
        sb.add_pedal(sp.start, min(3.82, dur - 0.18))
        if dur >= 7.5:
            sb.add_pedal(sp.start + 4.0, min(3.82, dur - 4.18))
        # Radiant Concert Grand Piano celebratory chords & octaves matching the CC 64 pedals!
        p_voic = [tr_r, tr_r + P5, tr_r + OCT + q_th]
        sb.chord("piano", sp.start, 1.4, p_voic, 0.64 + 0.06 * arch_u, roll=0.03)
        sb.chord("piano", sp.start + 2.0, 1.4, [tr_r + P5, tr_r + OCT, tr_r + OCT + P5], 0.62 + 0.06 * arch_u, roll=0.03)
        if dur >= 7.5:
            sb.chord("piano", sp.start + 4.0, 1.6, p_voic, 0.66 + 0.06 * arch_u, roll=0.03)
            sb.chord("piano", sp.start + 6.0, 1.5, [tr_r + P5, tr_r + OCT], 0.64 + 0.05 * arch_u, roll=0.03)

        sb.harp_arp(sp, sp.start + 0.04, pitch(C, 3), pitch(C, 6), vel=0.64 + 0.06 * arch_u, spacing=0.15, note_dur=1.8, ascending=(i % 2 == 0), max_notes=8)

        # 3. STRUCTURE 1 (Prime Curiosity Hook): Soaring in Flute + Clarinet + ai_strip (reaching vel 0.90..0.94)!
        if i in (0, 1, 4, 7, 10, 11, 15, 16, 17):
            use_7 = sp.quality in ("dom9", "prime11")
            sb.emit_prime_hook("flute", sp.start, pitch(C, 5), vel=lead_v, unit=0.5, use_septimal=use_7, staccato=False, snap=True)
            sb.emit_prime_hook("clarinet", sp.start, pitch(C, 4), vel=lead_v * 0.97, unit=0.5, use_septimal=use_7, staccato=False, snap=True)
            if dur >= 7.5:
                sb.emit_prime_hook("ai_strip", sp.start + 4.0, pitch(C, 5), vel=lead_v, unit=0.5, use_septimal=use_7, staccato=True, snap=True)
        else:
            pts_hi = sp.scale_steps(53, 120, allow_melody=False)
            if pts_hi:
                for q in range(4):
                    sb.note("ai_strip", sp.start + q, 0.45, pts_hi[-1 - (q % min(4, len(pts_hi)))], lead_v * 0.98, swell="none", vibrato=0.0, snap_to_harmony=False)

        # 4. STRUCTURE 2 (Functional Mirror Wedge): ai_architect (upper mirror) <-> Cello + Viola + English Horn (lower mirror)!
        pts_arch = sp.scale_steps(48, 118, allow_melody=False)
        pts_low = sp.scale_steps(-36, 28, allow_melody=False)
        if len(pts_arch) >= 4 and len(pts_low) >= 4:
            div = (i % 2 == 0)
            u_seq = pts_arch[:4] if div else list(reversed(pts_arch[:4]))
            l_seq = list(reversed(pts_low[-4:])) if div else pts_low[-4:]
            for m_k, (u_m, l_m) in enumerate(zip(u_seq, l_seq)):
                t_m = sp.start + m_k * 1.0
                if t_m < sp.end - 0.2:
                    sb.note("ai_architect", t_m, 0.82, u_m, lead_v * 0.98, swell="none", vibrato=0.0, snap_to_harmony=False)
                    sb.note("cello", t_m, 0.85, l_m, 0.80 + 0.08 * arch_u, swell="arch", vibrato=0.26, snap_to_harmony=False)
                    # Viola partners Cello in the lower Mirror Wedge across IV.3!
                    v_m = max(-45, min(48, l_m + OCT))
                    if abs(v_m - l_m) == 0 or abs(v_m - l_m) >= 12:
                        sb.note("viola", t_m, 0.82, v_m, 0.76 + 0.08 * arch_u, swell="arch", vibrato=0.24, snap_to_harmony=True)
                    if i % 3 == 1:
                        sb.note("english_horn", t_m, 0.85, max(-24, min(48, l_m + OCT)), 0.78 + 0.08 * arch_u, swell="arch", vibrato=0.26, snap_to_harmony=True)
        if dur >= 7.5 and i == 18:
            # Radiant C-Major crown chord on 1498..1506 before sudden silence of IV.4!
            sb.note("ai_architect", sp.start, dur - 0.4, pitch(G, 5), 0.88, swell="none", vibrato=0.0, snap_to_harmony=False)
            sb.note("ai_strip", sp.start, dur - 0.4, pitch(C, 6), 0.88, swell="none", vibrato=0.0, snap_to_harmony=False)

    # =========================================================================
    # IV.4 (1506..1563 + 5.0s tail, 52 BPM Adagio malinconico):
    # EPILOGUE — MELANCHOLY FOR HUMANITY!
    # Brass, timpani, and church_organ 100% TACET!
    # All IV.4 velocities strictly <= 0.40, with AI halo & string veil hushed
    # (0.16..0.22) well below lone human Cello & English Horn (0.28..0.40)!
    # =========================================================================
    coda_spans = [sp for sp in spans if sp.start >= 1506.0]

    # 1. High above (G5=84, Bb_harm5=96, C6=106): ai_architect (shakuhachi, vibrato: 0.0, swell: "none")
    # hums a hushed (vel 0.18..0.22), beatless 53-EDO fifth/seventh halo ~6 dB below the human soloists!
    for i, sp in enumerate(coda_spans):
        dur = sp.end - sp.start
        halo_v = max(0.21, 0.25 - 0.006 * i)
        halo_step_a = pitch(G, 5)
        halo_step_b = pitch(C, 6) if i % 2 == 0 else (BB_HARM + OCT)
        sb.note("ai_architect", sp.start + 0.15, dur * 0.52, halo_step_a, halo_v, swell="none", vibrato=0.0, snap_to_harmony=False, trim=False)
        sb.note("ai_architect", sp.start + dur * 0.48, dur * 0.46, halo_step_b, halo_v * 0.94, swell="none", vibrato=0.0, snap_to_harmony=False, trim=False)

        # Whisper-soft ppp string breath (vel 0.16..0.20) in early spans ONLY — drops out completely
        # in the final 2 spans (beats 1546..1563) so lone human Cello & English Horn close the work!
        if sp.start < 1545.5:
            veil_v = max(0.16, 0.20 - 0.008 * i)
            sb.chord("string_ensemble", sp.start + 0.20, dur - 0.50, [pitch(C, 3), pitch(G, 3)], veil_v, swell="dim" if sp.start >= 1534.0 else "arch")
            if sp.start < 1538.0:
                sb.note("viola", sp.start + 0.30, dur - 0.70, pitch(G, 3), veil_v, swell="arch", vibrato=0.66)
        sb.add_pedal(sp.start, dur - 0.30)

    # 2. Beneath the eternal AI halo: LONE HUMAN CELLO & ENGLISH HORN
    # (vibrato = 0.76..0.80, fragile arch/dim swells, vel = 0.28..0.40 <= 0.40, human slides <= 22.64c)!
    #
    # Span 0 (1506..1514, C dom9): Complete, fragile 6-note remembrance of STRUCTURE 1
    # (Prime Curiosity Hook: C4[0] -> D4[9] -> E4[17] -> G4[31] -> Bb_harm4[43] -> C5[53] in 2+3+2 breath)!
    sb.note("english_horn", 1506.3, 1.05, pitch(C, 4), 0.36, swell="arch", vibrato=0.76, snap_to_harmony=False, trim=False)
    sb.note("english_horn", 1507.5, 1.05, pitch(D, 4), 0.37, swell="arch", vibrato=0.76, snap_to_harmony=False, trim=False)
    sb.note("english_horn", 1508.8, 1.05, pitch(E, 4), 0.38, swell="arch", vibrato=0.78, snap_to_harmony=False, trim=False)
    sb.note("english_horn", 1510.0, 1.05, pitch(G, 4), 0.39, swell="arch", vibrato=0.78, snap_to_harmony=False, trim=False)
    sb.note("english_horn", 1511.2, 1.05, BB_HARM, 0.40, swell="arch", vibrato=0.78, snap_to_harmony=False, trim=False)
    sb.note("english_horn", 1512.4, 1.40, pitch(C, 5), 0.40, swell="dim", vibrato=0.80, snap_to_harmony=False, trim=False)
    sb.note("cello", 1506.5, 6.8, pitch(C, 3), 0.37, swell="arch", vibrato=0.76, snap_to_harmony=False, trim=False)

    # Span 1 (1514..1522, halo_maj_sigh {0, 16, 31, 43}): -1 SYNTONIC COMMA SIGH (E4=17 -> E-4=16)!
    sb.note("english_horn", 1514.6, 3.4, E_MINUS, 0.39, swell="dim", vibrato=0.78, slide_from_cents=22.64, snap_to_harmony=False, trim=False)
    sb.note("english_horn", 1518.4, 3.0, pitch(D, 4), 0.36, swell="dim", vibrato=0.76, snap_to_harmony=False, trim=False)
    sb.note("cello", 1515.0, 3.2, pitch(G, 3), 0.38, swell="arch", vibrato=0.78, snap_to_harmony=False, trim=False)
    sb.note("cello", 1518.5, 3.1, pitch(C, 3), 0.36, swell="dim", vibrato=0.76, snap_to_harmony=False, trim=False)

    # Span 2 & 3 (1522..1538): Complete 8-note Cello remembrance of STRUCTURE 3A (Human Passacaglia Ground):
    # C3 -> G2 -> Ab2 -> Eb3 -> F3 -> C3 -> Ab-2 (-1 comma sigh!) -> G2!
    c_passacaglia_farewell = [
        (1522.1, 1.80, pitch(C, 3), 0.38, "arch", 0.0),
        (1524.0, 1.80, pitch(G, 2), 0.38, "arch", 0.0),
        (1526.0, 1.80, pitch(AB, 2), 0.39, "arch", 0.0),
        (1528.0, 1.80, pitch(EB, 3), 0.39, "arch", 0.0),
        (1530.1, 1.80, pitch(F, 3), 0.40, "arch", 0.0),
        (1532.0, 1.80, pitch(C, 3), 0.38, "dim", 0.0),
        (1534.1, 1.80, AB_MINUS - 2 * OCT, 0.39, "dim", 22.64),   # -1 comma sigh Ab2 -> Ab-2!
        (1536.0, 1.80, pitch(G, 2), 0.36, "dim", 0.0),
    ]
    for b_c, d_c, st_c, v_c, sw_c, sl_c in c_passacaglia_farewell:
        sb.note("cello", b_c, d_c, st_c, v_c, swell=sw_c, vibrato=0.78, slide_from_cents=sl_c, snap_to_harmony=False, trim=False)

    # English Horn counter-lament across Span 2 & 3 (Eb4 -> Db4 [16:15], then Eb-4 [-1 comma sigh]):
    sb.note("english_horn", 1523.5, 2.8, pitch(EB, 4), 0.39, swell="arch", vibrato=0.78, snap_to_harmony=False, trim=False)
    sb.note("english_horn", 1526.6, 2.9, DB, 0.38, swell="dim", vibrato=0.78, snap_to_harmony=False, trim=False)
    sb.note("english_horn", 1534.2, 3.4, EB_MINUS, 0.38, swell="dim", vibrato=0.78, slide_from_cents=22.64, snap_to_harmony=False, trim=False)

    # Span 4 (1538..1546, halo_phryg): Minor-inflected Structure 1 farewell & clean 16:15 (Db4 -> C4) sigh!
    sb.note("english_horn", 1538.4, 1.3, pitch(C, 4), 0.36, swell="arch", vibrato=0.76, snap_to_harmony=False, trim=False)
    sb.note("english_horn", 1539.8, 1.3, pitch(EB, 4), 0.37, swell="arch", vibrato=0.78, snap_to_harmony=False, trim=False)
    sb.note("english_horn", 1541.2, 1.3, pitch(G, 4), 0.36, swell="arch", vibrato=0.78, snap_to_harmony=False, trim=False)
    sb.note("english_horn", 1542.6, 1.4, DB, 0.35, swell="arch", vibrato=0.78, snap_to_harmony=False, trim=False)
    sb.note("english_horn", 1544.1, 1.7, pitch(C, 4), 0.33, swell="dim", vibrato=0.78, slide_from_cents=0.0, snap_to_harmony=False, trim=False)
    sb.note("cello", 1539.0, 6.4, pitch(C, 3), 0.35, swell="dim", vibrato=0.76, snap_to_harmony=False, trim=False)

    # Span 5 & 6 (1546..1563, C prime7, strings 100% silent!): Lone Cello & English Horn fade out
    sb.note("cello", 1546.4, 6.8, pitch(G, 2), 0.34, swell="dim", vibrato=0.78, snap_to_harmony=False, trim=False)
    sb.note("english_horn", 1547.8, 4.8, pitch(G, 4), 0.34, swell="dim", vibrato=0.78, snap_to_harmony=False, trim=False)
    sb.note("english_horn", 1554.2, 4.4, pitch(C, 4), 0.30, swell="dim", vibrato=0.76, snap_to_harmony=False, trim=False)
    sb.note("cello", 1554.0, 8.0, pitch(C, 2), 0.30, swell="dim", vibrato=0.76, snap_to_harmony=False, trim=False)

    # 3. Sparse CC 64 Pedaled Piano Teardrops fading into silence (ppp vel 0.24..0.34)!
    teardrops = [
        (1508.5, 3.0, pitch(G, 4), 0.34),
        (1516.0, 3.2, pitch(C, 5), 0.32),
        (1524.5, 3.2, pitch(G, 4), 0.31),
        (1533.0, 3.2, pitch(C, 5), 0.30),
        (1542.0, 3.4, pitch(G, 4), 0.28),
        (1550.0, 4.0, pitch(C, 5), 0.26),
        (1557.5, 5.5, pitch(G, 4), 0.24),   # Final teardrop ends at beat 1563.0 -> +5.0s tail = 900s!
    ]
    for b_t, d_t, st_t, v_t in teardrops:
        sb.note("piano", b_t, d_t, st_t, v_t, snap_to_harmony=False, trim=False)


# =============================================================================
# Build & Self-Validate the Complete 15-Minute v2 Symphony
# =============================================================================
def compose_riemann_symphony() -> Tuple[RiemannSymphonyBuilder, Dict]:
    # Piecewise-linear tempo map spanning 52.0 BPM to 168.0 BPM:
    #   Mvt I   (0..440)     = 0:00 – 3:28 (~208.5s, brisk playful 118 -> 136 -> 114 BPM)
    #   Mvt II  (440..764)   = 3:28 – 6:58 (~209.2s, rubato waves 88 -> 114 -> 66 BPM)
    #   Mvt III (764..1154)  = 6:58 – 11:25 (~267.2s, 72 -> 104 -> 122 -> [74] -> 136 -> 60 BPM)
    #   Mvt IV  (1154..1563) = 11:25 – 15:00 (~210.0s active + 5.0s tail = 900.0s, 152->168->122->52 BPM)
    tempo_segments = [
        # Movement I: The Primes (Curiosity) (118 -> 136 -> 114 BPM)
        (0.0, 118.0),
        (108.0, 126.0),
        (228.0, 136.0),
        (300.0, 136.0),
        (348.0, 124.0),
        (439.99, 114.0),
        # Movement II: Analytic Continuation (Through the Mirror) (88 -> 114 -> 66 BPM)
        (440.0, 88.0),
        (496.0, 108.0),
        (512.0, 92.0),
        (584.0, 104.0),
        (640.0, 114.0),
        (696.0, 86.0),
        (736.0, 68.0),
        (763.99, 66.0),
        # Movement III: A Century of Small Progress (72 -> 104 -> 136 -> 60 BPM)
        (764.0, 72.0),
        (828.0, 74.0),
        (860.0, 86.0),
        (892.0, 104.0),
        (915.99, 122.0),
        (916.0, 74.0),      # Selberg subito pp Parity Barrier!
        (923.99, 74.0),
        (924.0, 80.0),
        (956.0, 108.0),
        (988.0, 128.0),
        (1020.0, 136.0),
        (1051.99, 132.0),
        (1052.0, 112.0),
        (1084.0, 78.0),
        (1116.0, 62.0),
        (1153.99, 60.0),
        # Movement IV: AI, Unified Triumph & Melancholy for Humanity (152 -> 168 -> 122 -> 52 BPM)
        (1154.0, 152.0),
        (1253.99, 152.0),
        (1254.0, 168.0),
        (1393.99, 168.0),
        (1394.0, 122.0),
        (1505.99, 122.0),
        (1506.0, 58.0),
        (1514.0, 52.0),
        (1563.0, 52.0),
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
    tracks_by_id = {tr["id"]: tr for tr in score["tracks"]}
    for tr in score["tracks"]:
        for forbidden in ("x", "y", "width", "gain", "warm_lowpass_hz"):
            if forbidden in tr:
                errors.append(f"Track '{tr['id']}' must omit inline '{forbidden}'")

    # 2. Strict architectural & timbral checks
    for ai_id, min_beat in (("ai_strip", 1154.0), ("ai_architect", 1254.0)):
        tr = tracks_by_id[ai_id]
        if not tr["notes"]:
            errors.append(f"{ai_id} has 0 notes!")
        for n in tr["notes"]:
            if n["beat"] < min_beat - 1e-4:
                errors.append(f"{ai_id} entered prematurely at beat {n['beat']} (< {min_beat})")
                break
            if not (31 <= n["step"] <= 124):
                errors.append(f"{ai_id} step {n['step']} outside G4..E6 (31..124)")
                break
            if n.get("vibrato", 0.0) > 1e-4 or n.get("swell", "none") != "none":
                errors.append(f"{ai_id} must keep vibrato=0.0 and swell='none'")
                break

    org_notes = tracks_by_id["church_organ"]["notes"]
    if not org_notes:
        errors.append("church_organ has 0 notes!")
    else:
        if org_notes[0]["beat"] < 1394.0 - 1e-4:
            errors.append(f"church_organ entered prematurely at beat {org_notes[0]['beat']}")
        if any(n["beat"] >= 1506.0 - 1e-4 for n in org_notes):
            errors.append("church_organ must be silent in IV.4 (>= 1506.0)!")

    if any(n["beat"] < 440.0 for n in tracks_by_id["trombone"]["notes"]):
        errors.append("trombone must be TACET in Movement I (< 440.0)!")
    for silent_iv4 in ("trombone", "french_horn", "timpani", "church_organ"):
        if any(n["beat"] >= 1506.0 - 1e-4 for n in tracks_by_id[silent_iv4]["notes"]):
            errors.append(f"{silent_iv4} must be silent in IV.4 (>= 1506.0)!")

    # Verify IV.1 polish constraints on The Herald (ai_strip): zero <0.46b chatter, zero scoops, tamed vel <=0.62
    iv1_herald = [n for n in tracks_by_id["ai_strip"]["notes"] if 1154.0 <= n["beat"] < 1254.0]
    if not iv1_herald:
        errors.append("ai_strip has 0 notes in IV.1 (1154..1254)!")
    for n in iv1_herald:
        if n["dur"] < 0.46 - 1e-4 or n["dur"] > 1.85 + 1e-4:
            errors.append(f"IV.1 ai_strip note at {n['beat']} has dur={n['dur']} outside 0.46..1.85b!")
            break
        if abs(n.get("slide_from_cents", 0.0)) > 1e-4:
            errors.append(f"IV.1 ai_strip note at {n['beat']} has non-zero slide_from_cents={n.get('slide_from_cents')}!")
            break
        if n["vel"] > 0.62 + 1e-4:
            errors.append(f"IV.1 ai_strip note at {n['beat']} exceeds vel 0.62: {n['vel']}!")
            break

    # Verify IV.4 velocity intimacy (<= 0.40) and overall dynamic contrast
    iv4_vels = [
        n["vel"]
        for tr in score["tracks"]
        for n in tr["notes"]
        if n["beat"] >= 1506.0
    ]
    iv3_vels = [
        n["vel"]
        for tr in score["tracks"]
        for n in tr["notes"]
        if 1394.0 <= n["beat"] < 1506.0
    ]
    if not iv4_vels or max(iv4_vels) > 0.401 or min(iv4_vels) > 0.35:
        errors.append(f"IV.4 velocities {min(iv4_vels):.3f}..{max(iv4_vels):.3f} violate ppp-mp intimacy!")
    if not iv3_vels or max(iv3_vels) < 0.88:
        errors.append(f"IV.3 peak velocity {max(iv3_vels):.3f} < 0.88!")

    # Verify human wind & brass breathing rests (<= 15.0 beats max continuous phrase)
    for wb_id in HUMAN_WINDS_BRASS:
        ivs = sorted((n["beat"], n["beat"] + n["dur"]) for n in tracks_by_id[wb_id]["notes"])
        merged_wb: List[Tuple[float, float]] = []
        for a0, b0 in ivs:
            if merged_wb and a0 - merged_wb[-1][1] < 0.75:
                merged_wb[-1] = (merged_wb[-1][0], max(merged_wb[-1][1], b0))
            else:
                merged_wb.append((a0, b0))
        mx_wb = max((b0 - a0 for a0, b0 in merged_wb), default=0.0)
        if mx_wb > 15.0:
            errors.append(f"{wb_id} exceeds human breathing span: {mx_wb:.2f} beats (> 15.0b)")

    # 3. Verify ZERO sustained 4..=6-step narrow-second rubs > 0.35 beats across all non-timpani tracks
    pitched = []
    for tr in score["tracks"]:
        if tr["instrument"] == "timpani":
            continue
        for n in tr["notes"]:
            pitched.append((n["beat"], n["beat"] + n["dur"], n["step"], tr["id"]))
    pitched.sort()
    rub_count = 0
    for i, (b0, e0, s0, t0) in enumerate(pitched):
        for b1, e1, s1, t1 in pitched[i + 1 :]:
            if b1 >= e0 - 0.35:
                break
            if 4 <= abs(s0 - s1) <= 6 and (min(e0, e1) - max(b0, b1)) > 0.35:
                rub_count += 1
                if rub_count <= 5:
                    errors.append(
                        f"Sustained 4..6-step rub >0.35b at beat {max(b0, b1):.2f}: {t0}({s0}) vs {t1}({s1})"
                    )
    print(f"Sustained 4..6-step rubs > 0.35b: {rub_count}")

    # 4. Duration & movement boundary summary
    m_beats = [0.0, 440.0, 764.0, 1154.0, 1254.0, 1394.0, 1506.0, 1563.0]
    m_secs = [sb.tempo.beat_to_seconds(b) for b in m_beats]
    total_dur = m_secs[-1] + 5.0
    print("Movement & Sub-Movement Timestamps:")
    labels = [
        ("I.   The Primes (Curiosity)", 0, 1, False),
        ("II.  Analytic Continuation (Mirror)", 1, 2, False),
        ("III. A Century of Small Progress", 2, 3, False),
        ("IV.1 The Herald: Zero-Free Strips", 3, 4, False),
        ("IV.2 The Oracle: Inspired Synthesis", 4, 5, False),
        ("IV.3 Triumph of the Proof", 5, 6, False),
        ("IV.4 Epilogue: Melancholy for Humanity", 6, 7, True),
    ]
    for nm, i0, i1, add_tail in labels:
        s0 = m_secs[i0]
        s1 = m_secs[i1] + (5.0 if add_tail else 0.0)
        print(
            f"  {nm:<40} beat {m_beats[i0]:6.1f}..{m_beats[i1]:6.1f} | "
            f"{int(s0 // 60):2d}:{s0 % 60:05.2f} – {int(s1 // 60):2d}:{s1 % 60:05.2f} ({s1 - s0:5.1f}s)"
        )
    print(
        f"Total Concert Hall Duration (with 5.0s tail): {total_dur:.2f}s "
        f"({int(total_dur // 60)}:{total_dur % 60:05.2f}) | Default tail (4.5s): {total_dur - 0.5:.2f}s"
    )
    if not (885.0 <= total_dur <= 915.0) or not (885.0 <= total_dur - 0.5 <= 915.0):
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
