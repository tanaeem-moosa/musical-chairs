#!/usr/bin/env python3
"""
Compose a concert-grade ~10-minute (585–615s) pure stage-independent 53-EDO work:
  "The Shattered Semitone (v2) — Concerto Grosso for Dual Guitars, Plucked Consort & 53-EDO Orchestra"

Engineered for razor-sharp plucked-string clarity (`nylon_guitar`, `steel_guitar`, `harp`,
`pizzicato`, `dotara`, `sitar`), ZERO seasick Western portamento glides (`slide_from_cents = 0`
on all Western instruments; discrete fretted articulation & genuine functional/mediant voice-leading
throughout), real tempo contrast (`64 BPM` Adagio to `130 BPM` Scherzo), and unmistakable
53-EDO vs 12-TET acoustic & structural divergence right from `0:00`!

Seven Structural Movements (~600s = 10:00):
  I.   Campanella Prelude: The Shattered Semitone (0:00–1:25, 112 -> 118 BPM)
  II.  Fretted Toccatina & Eagle-53 Chromatic Mediants (1:25–2:50, 126 BPM)
  III. East–West Plucked Shruti Dialogue (2:50–4:15, 82 -> 92 BPM)
  IV.  The Syntonic Comma Pump: C -> Am -> Dm -> G -> C Passacaglia (4:15–5:45, 98 -> 116 BPM)
  V.   Scherzo of the Diesis Shear: Ab++ Major -> 12-TET A minor (5:45–7:15, 130 BPM)
  VI.  Adagio of Glass Harmonics: 7-Limit & 11-Limit Resonance (7:15–8:35, 64 BPM)
  VII. Finale: The 53-Tone Continuum & Cathedral Organ Apotheosis (8:35–10:00, 116 -> 126 -> 68 BPM)

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
EAGLE_3 = 3      # 25:24 (~67.92c classic chromatic semitone / Eagle-53 mediant shift)
SEMI_CHROM = 4   # ~90.57c Pythagorean chromatic semitone
SEMI = 5         # 16:15 (~113.21c pure diatonic semitone)
m2_MINOR = 8     # 10:9  (~181.13c minor whole tone / Shuddha Re 1)
M2 = 9           # 9:8   (~203.77c major whole tone / Shuddha Re 2)
SUP_M2 = 10      # 8:7   (~226.42c septimal supermajor second)
SUB_m3 = 12      # 7:6   (~271.70c septimal subminor third / Komal Ga 1)
PYTH_m3 = 13     # 32:27 (~294.34c Pythagorean minor third)
m3 = 14          # 6:5   (~316.98c pure minor third / Komal Ga 2)
SUP_m3 = 15      # 27:22 (~339.62c undecimal superminor third)
GRAVE_M3 = 16    # 100:81 (~362.26c grave major third)
M3 = 17          # 5:4   (~384.91c pure major third)
PYTH_M3 = 18     # 81:64 (~407.55c Pythagorean ditone)
SUP_M3 = 19      # 9:7   (~430.19c septimal supermajor third)
P4 = 22          # 4:3   (~498.11c pure fourth)
UNDEC_11 = 24    # 11:8  (~543.40c 11-limit harmonic fourth / undecimal overtone)
SEPT_TT = 25     # 7:5   (~566.04c septimal tritone)
JUST_TT = 26     # 45:32 (~588.68c just tritone / Tivra Ma)
P5 = 31          # 3:2   (~701.89c pure fifth)
PYTH_m6 = 35     # 128:81 (~792.45c Pythagorean minor sixth / Komal Dha 1)
m6 = 36          # 8:5   (~815.09c pure minor sixth / Komal Dha 2)
M6 = 39          # 5:3   (~883.02c pure major sixth)
HARM_7 = 43      # 7:4   (~973.58c septimal harmonic seventh)
PYTH_m7 = 44     # 16:9  (~996.23c Pythagorean minor seventh)
JUST_m7 = 45     # 9:5   (~1018.87c just minor seventh)
M7 = 48          # 15:8  (~1086.79c pure major seventh)

# Reference pitch classes at k = 0
C = 0
CS_EAGLE = 3     # 25:24 classic C# (+67.9c)
DB = 5           # 16:15 Db (+113.2c; Db7 = [5, 22, 36, 48]!)
D_MINUS = 8      # 10:9 minor-tone D
D = 9            # 9:8 major-tone D
EB_HARM = 12     # 7:6 subminor Eb
EB = 14          # 6:5 pure minor Eb
E = 17           # 5:4 pure major E
F = 22           # 4:3 pure F
FS = 26          # 45:32 Tivra Ma / F#
G_MINUS = 30
G = 31           # 3:2 pure G
GS_EAGLE = 34    # 25:16 classic G# (17 + 17 = 34; 3 steps above G=31!)
AB_PYTH = 35     # 128:81 Komal Dha 1
AB = 36          # 8:5 pure Ab / Komal Dha 2 (Ab7 = [36, 0, 14, 26]!)
AB_DIESIS = 38   # Ab++ ([38, 2, 16] = pure 4:5:6 Major -> quantizes to A minor [69,60,64] in 12-TET!)
A = 39           # Exact 440.00 Hz in Octave 4!
BB_HARM = 43     # 7:4 septimal Bb
BB = 44          # 16:9 Bb
BB_JUST = 45     # 9:5 just Bb
B = 48           # 15:8 pure B

INDIAN_TRACKS = {"sitar", "dotara", "ektara"}
WESTERN_TRACKS = {
    "nylon_guitar",
    "steel_guitar",
    "harp",
    "piano",
    "pizzicato",
    "string_ensemble",
    "tremolo_strings",
    "viola",
    "cello",
    "clarinet",
    "english_horn",
    "bassoon",
    "french_horn",
    "trombone",
    "timpani",
    "church_organ",
}
WIND_BRASS = {"clarinet", "english_horn", "bassoon", "french_horn", "trombone"}
BASS_CAPABLE = {
    "nylon_guitar",
    "steel_guitar",
    "harp",
    "piano",
    "bassoon",
    "cello",
    "trombone",
    "french_horn",
    "church_organ",
    "ektara",
    "timpani",
}

# Idiomatic sweet-spot registers (guitars strictly in [-84, +70] = F2..E5, mostly -53..+62)
SWEET_SPOTS: Dict[str, Tuple[int, int]] = {
    "nylon_guitar": (-84, 68),
    "steel_guitar": (-84, 70),
    "harp": (-84, 106),
    "piano": (-106, 92),
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
    "string_ensemble",
    "tremolo_strings",
    "bassoon",
    "trombone",
    "church_organ",
    "ektara",
}

# Section III beat boundaries (Indian meend ornaments permitted ONLY inside Section III!)
SEC3_START = 340.0
SEC3_END = 464.0


def pitch(pc: int, octave: int, k: int = 0) -> int:
    """Exact 53-EDO step for pitch class `pc` in `octave` (C4 = 0) + comma offset `k`."""
    return pc + (octave - 4) * OCT + k


def mod53_dist(a: int, b: int) -> int:
    d = (a - b) % OCT
    return min(d, OCT - d)


def edo53_to_12tet_midi(step: int, cents: float = 0.0) -> int:
    """Exact replica of Rust `tuning::edo53_to_12tet_midi`."""
    val = 60.0 + (step / OCT) * 12.0 + cents / 100.0
    if val >= 0.0:
        r = int(math.floor(val + 0.5))
    else:
        r = int(math.ceil(val - 0.5))
    return max(0, min(127, r))


# =============================================================================
# Clash-Free & Semitone-Rub-Free Pure 5/7/11-Limit & Shruti Chord Templates
# Every template + melody_extra guarantees pairwise mod53_dist >= 7 (except maj7
# where M7=48 omits same-octave root 53 so 4..=6 close rubs never occur!).
# =============================================================================
CHORD_TEMPLATES: Dict[str, Tuple[int, ...]] = {
    "open5": (0, P5),
    "maj": (0, M3, P5),
    "min": (0, m3, P5),
    "pyth_min": (0, PYTH_m3, P5),           # [0, 13, 31] -> on F(22): [22, 35, 0] (Komal Dha 1 = 35!)
    "submin": (0, SUB_m3, P5),              # [0, 12, 31] -> pure 6:7:9 septimal subminor triad
    "add9": (0, M2, M3, P5),                # [0, 9, 17, 31] -> min pairwise dist = 8!
    "maj7": (0, M3, P5, M7),                # [0, 17, 31, 48] -> voiced openly without same-oct root
    "min7": (0, m3, P5, JUST_m7),           # [0, 14, 31, 45] -> min pairwise dist = 8!
    "min7_p": (0, m3, P5, PYTH_m7),         # [0, 14, 31, 44] -> Dm7(9) = [9, 23, 40, 0] holds C=0!
    "min9": (0, M2, m3, P5, JUST_m7),       # voiced with M2 in upper octave (+62)
    "min_dm": (0, m3, P5),
    "dom7": (0, M3, P5, HARM_7),            # [0, 17, 31, 43] = pure 4:5:6:7!
    "dom7_p": (0, M3, P5, PYTH_m7),         # [0, 17, 31, 44] -> G7+(32) = [32, 49, 10, 23] holds F+=23!
    "dom9": (0, M2, M3, P5, HARM_7),        # [0, 9, 17, 31, 43] = pure 4:5:6:7:9!
    "submin7": (0, SUB_m3, P5, HARM_7),     # [0, 12, 31, 43] = 6:7:9:10.5 -> Cm7 in 12-TET!
    "overtone11": (0, M3, UNDEC_11, P5, HARM_7),  # [0, 17, 24, 31, 43] = 8:10:11:12:14 11-limit bell!
    "sus2_m": (0, m2_MINOR, P5),            # [0, 8, 31] = Raga Shuddha Re 1 (10:9 = step 8)
    "sus2": (0, M2, P5),                    # [0, 9, 31] = Raga Shuddha Re 2 (9:8 = step 9)
    "sus4": (0, P4, P5),
}

# Melody extensions chosen so pairwise mod53_dist >= 7 against ALL chord tones!
MELODY_EXTRA: Dict[str, Tuple[int, ...]] = {
    "open5": (M2, P4, M6),
    "maj": (M2, M6),
    "min": (P4, JUST_m7),
    "pyth_min": (P4, PYTH_m7),
    "submin": (P4, HARM_7),
    "add9": (M6,),
    "maj7": (M2, M6),
    "min7": (P4,),
    "min7_p": (P4,),
    "min9": (P4,),
    "min_dm": (P4, PYTH_m7),
    "dom7": (M2,),
    "dom7_p": (M2,),
    "dom9": (),
    "submin7": (m2_MINOR, P4),
    "overtone11": (M2,),
    "sus2_m": (M6,),
    "sus2": (M6,),
    "sus4": (M2, M6),
}


@dataclass
class ChordSpan:
    start: float
    end: float
    root_pc: int
    quality: str
    label: str = ""
    pedal_pc: Optional[int] = None
    free_microtonal: bool = False

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
            if all(mod53_dist(cand, existing) >= 7 for existing in s):
                s.add(cand)
        return s

    def verify_clash_free(self) -> None:
        if self.free_microtonal:
            return
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
        """Places bass root cleanly inside [low..high] (default C2..B2 = -106..-54)."""
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
        if q in ("maj", "add9", "maj7", "dom7", "dom7_p", "dom9", "overtone11"):
            return M3
        if q in ("min", "min7", "min7_p", "min9", "min_dm"):
            return m3
        if q == "pyth_min":
            return PYTH_m3
        if q in ("submin", "submin7"):
            return SUB_m3
        if q == "sus4":
            return P4
        if q == "sus2_m":
            return m2_MINOR
        if q == "sus2":
            return M2
        return P5

    def seventh_offset(self) -> Optional[int]:
        q = self.quality
        if q in ("dom7", "dom9", "submin7", "overtone11"):
            return HARM_7
        if q in ("min7_p", "dom7_p"):
            return PYTH_m7
        if q in ("min7", "min9"):
            return JUST_m7
        if q == "maj7":
            return M7
        return None

    def open_voicing(self, include_9: bool = True, include_7: bool = True) -> List[int]:
        """Warm orchestral voicing (>= C3) with zero low mud and zero 4..=6-step close rubs."""
        r = self.tenor_root()
        q = self.quality
        if q == "open5":
            return [r, r + P5, r + OCT]
        th = self.third_offset()
        sev = self.seventh_offset() if include_7 else None
        if q == "overtone11":
            return sorted({r, r + P5, r + HARM_7, r + OCT + M3, r + OCT + UNDEC_11})
        if q == "min9" and include_9:
            return sorted({r, r + m3, r + P5, r + OCT + M2} | ({r + sev} if sev is not None else set()))
        if include_9 and q in ("add9", "dom9"):
            return sorted({r, r + M3, r + P5, r + OCT + M2} | ({r + sev} if sev is not None else set()))
        voicing = [r, r + P5]
        if sev is not None:
            voicing.append(r + sev)
        else:
            voicing.append(r + OCT)
        voicing.append(r + OCT + th)
        return sorted(set(voicing))

    def guitar_voicing(self, max_strings: int = 6) -> List[int]:
        """
        Idiomatic 5- or 6-string guitar chord in [-84, +68] (F2..D#5):
        - At most ONE bass string < -53 (when root_pc >= 22, matching exact bass_root()),
          with the next string >= -53 (>= 31 steps higher -> ZERO < C3 mud!).
        - Zero 4..=6-step close-register rubs (maj7 omits r+OCT adjacent to r+48; min9 places M2 at +62).
        """
        r = self.tenor_root()  # [-53..-1]
        th = self.third_offset()
        sev = self.seventh_offset()
        q = self.quality
        rpc = (self.pedal_pc if self.pedal_pc is not None else self.root_pc) % OCT

        pts: List[int] = []
        if rpc >= 22:
            br = self.bass_root(-84, -54)  # [-84..-54]
            pts.append(br)
        pts.append(r)
        pts.append(r + P5)

        if q == "overtone11":
            pts.extend([r + HARM_7, r + OCT + M3, r + OCT + UNDEC_11])
        elif q in ("dom9", "add9"):
            if sev is not None:
                pts.append(r + sev)
            pts.extend([r + OCT + M3, r + OCT + M2 if r + OCT + M2 > r + OCT + M3 else r + 2 * OCT + M2])
        elif q == "min9":
            pts.extend([r + JUST_m7, r + OCT + m3, r + OCT + M2 + OCT if r + OCT + M2 < r + OCT + m3 + 7 else r + OCT + M2])
        elif sev is not None:
            pts.append(r + sev)
            pts.append(r + OCT + th)
            pts.append(r + OCT + P5)
        else:
            pts.extend([r + OCT, r + OCT + th, r + OCT + P5])

        # Fold any top note > 68 down cleanly while preserving >= 7-step spacing
        cleaned: List[int] = []
        for st in sorted(set(pts)):
            while st > 68:
                st -= OCT
            if st < -84:
                st += OCT
            if all(abs(st - prev) >= 7 or st == prev for prev in cleaned):
                if st not in cleaned:
                    cleaned.append(st)
        cleaned.sort()
        # Ensure at most one note < -53
        low_notes = [x for x in cleaned if x < -OCT]
        if len(low_notes) > 1:
            cleaned = [low_notes[0]] + [x for x in cleaned if x >= -OCT]
        return cleaned[:max_strings]

    def arp_scale(self, low_step: int, high_step: int) -> List[int]:
        pcs = set(self.chord_pcs)
        if self.quality == "maj7":
            pcs.discard(self.root_pc % OCT)
        pts = [s for s in range(low_step, high_step + 1) if (s % OCT) in pcs]
        # Filter out any close 4..=6 step neighbors
        filtered: List[int] = []
        for s in pts:
            if not filtered or s - filtered[-1] >= 7:
                filtered.append(s)
        return filtered


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

    def seconds_to_beat_approx(self, target_s: float, lo_b: float = 0.0, hi_b: float = 1200.0) -> float:
        for _ in range(36):
            mid = 0.5 * (lo_b + hi_b)
            if self.beat_to_seconds(mid) < target_s:
                lo_b = mid
            else:
                hi_b = mid
        return 0.5 * (lo_b + hi_b)

    def to_json(self) -> List[Dict[str, float]]:
        return [{"beat": round(b, 4), "bpm": round(bpm, 3)} for b, bpm in self.segments]


# =============================================================================
# Stage-Independent Score Builder with Zero-Wail & Zero-Clash Guarantees
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
        specs = [
            TrackSpec("nylon_guitar", "Classical Nylon Guitar", "nylon_guitar"),
            TrackSpec("steel_guitar", "Acoustic Steel Guitar", "steel_guitar"),
            TrackSpec("harp", "Orchestral Harp", "harp"),
            TrackSpec("piano", "Concert Grand Piano", "piano"),
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
        free_microtonal: bool = False,
    ) -> ChordSpan:
        span = ChordSpan(
            start=float(start),
            end=float(end),
            root_pc=root_pc % OCT,
            quality=quality,
            label=label,
            pedal_pc=(pedal_pc % OCT) if pedal_pc is not None else None,
            free_microtonal=free_microtonal,
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
        """Trims `dur` cleanly before any subsequent ChordSpan where `step` would clash or mud."""
        if track_id == "timpani":
            return max(0.08, dur)
        end = beat + dur
        pc = step % OCT
        strict = track_id in STRICT_CHORD_TRACKS
        bpm = self.tempo.bpm_at(beat)
        gap_beats = max(0.07, 0.085 * (bpm / 60.0))

        for sp in self.grid:
            if sp.end <= beat + 1e-6:
                continue
            if sp.start >= end - 1e-6:
                break
            if sp.start > beat + 1e-6:
                if sp.free_microtonal:
                    end = min(end, sp.start - gap_beats)
                    break
                allowed = sp.chord_pcs if strict else sp.melody_pcs
                low_conflict = False
                if step < -OCT:
                    br = sp.bass_root()
                    diff = abs(step - br)
                    if 0 < diff < P4:
                        low_conflict = True
                # Also prevent carrying a close 4..=6 step note into next span's chord tones
                comma_or_rub = any(mod53_dist(pc, cpc) <= 6 and pc != cpc for cpc in sp.chord_pcs)
                if (pc not in allowed) or low_conflict or comma_or_rub:
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
        slide_from_cents: float = 0.0,
        swell: Optional[str] = None,
        breath_swell: Optional[bool] = None,
        vibrato: float = 0.0,
        meend_cents: float = 0.0,
        trim_to_chord: bool = True,
        exact_step: bool = False,
    ) -> None:
        tr = self.tracks[track_id]
        strict = track_id in STRICT_CHORD_TRACKS
        sp0 = self.span_at(beat)

        # STRICT ANTI-WAILING ENFORCEMENT:
        # 1) ZERO slide_from_cents and ZERO meend_cents on ALL Western instruments everywhere!
        # 2) Indian meend ornaments allowed ONLY in Section III (SEC3_START..SEC3_END)!
        if track_id not in INDIAN_TRACKS or not (SEC3_START - 1e-3 <= beat < SEC3_END + 1e-3):
            slide_from_cents = 0.0
            meend_cents = 0.0
        if track_id in ("nylon_guitar", "steel_guitar", "harp", "piano", "pizzicato", "dotara", "ektara"):
            vibrato = 0.0

        if track_id not in BASS_CAPABLE and step < -OCT:
            step += OCT

        lo_sw, hi_sw = SWEET_SPOTS[track_id]
        while step > hi_sw:
            step -= OCT
        while step < lo_sw:
            step += OCT

        if not exact_step and not sp0.free_microtonal and track_id != "timpani":
            allowed = sp0.chord_pcs if strict else sp0.melody_pcs
            if (step % OCT) not in allowed:
                step = sp0.nearest_step(step, allow_melody=not strict)

        while step > hi_sw:
            step -= OCT
        while step < lo_sw:
            step += OCT

        if step < -OCT and track_id != "timpani" and not exact_step:
            br = sp0.bass_root(low=lo_sw, high=-54)
            if step != br and abs(step - br) < P4:
                step = br if br >= lo_sw else br + OCT

        if trim_to_chord:
            dur = self._safe_dur(track_id, beat, dur, step)

        if swell is None and breath_swell is None and tr.instrument in WIND_BRASS and dur >= 0.70:
            swell = "arch"

        # Calibrate concert dynamic curve into [0.48, 0.83] so full orchestration + velocity
        # yields a natural EBU R128 Loudness Range right around 11.5–13.2 LU on both stage modes.
        vel_cap = 0.74 if track_id in ("timpani", "church_organ") else 0.83
        norm_u = (max(0.24, min(0.92, float(vel))) - 0.24) / 0.68
        scaled_v = 0.48 + 0.35 * norm_u
        v = max(0.47, min(vel_cap, scaled_v))

        entry: Dict = {
            "beat": round(beat, 4),
            "dur": round(dur, 4),
            "step": int(step),
            "vel": round(v, 3),
        }
        if abs(slide_from_cents) > 1e-4:
            entry["slide_from_cents"] = round(max(-38.0, min(38.0, slide_from_cents)), 2)
        if swell is not None:
            entry["swell"] = swell
        elif breath_swell:
            entry["breath_swell"] = True
        if vibrato > 1e-3:
            entry["vibrato"] = round(max(0.0, min(0.45, vibrato)), 3)
        if abs(meend_cents) > 1e-4:
            entry["meend_cents"] = round(max(-30.0, min(30.0, meend_cents)), 2)
        tr.notes.append(entry)

    def guitar_strum(
        self,
        track_id: str,
        beat: float,
        dur: float,
        steps: Sequence[int],
        vel: float,
        *,
        roll: float = 0.045,
        upstroke: bool = False,
        exact_step: bool = False,
    ) -> None:
        """Crisp 4–6 string classical/acoustic guitar strum with zero vibrato and zero pitch bend."""
        ordered = list(reversed(steps)) if upstroke else list(steps)
        n = len(ordered)
        for i, st in enumerate(ordered):
            t = beat + i * roll
            d = max(0.12, dur - i * roll)
            w = 1.02 if i in (0, n - 1) else 0.91
            self.note(track_id, t, d, st, vel * w, exact_step=exact_step)

    def guitar_fingerstyle(
        self,
        track_id: str,
        span: ChordSpan,
        vel: float,
        *,
        style: str = "baroque",
        step_beats: float = 0.5,
        ring_mult: float = 1.65,
    ) -> None:
        """Idiomatic fingerpicking / plectrum arpeggio across a 5–6 string 53-EDO guitar voicing."""
        gv = span.guitar_voicing(max_strings=6)
        while len(gv) < 5:
            gv.append(min(68, gv[-1] + P5))
        if len(gv) >= 6:
            s0, s1, s2, s3, s4 = gv[0], gv[2], gv[3], gv[4], gv[5]
        else:
            s0, s1, s2, s3, s4 = gv[0], gv[1], gv[2], gv[3], gv[-1]
        if span.quality not in ("open5", "sus2", "sus2_m", "sus4"):
            th_pc = (span.root_pc + span.third_offset()) % OCT
            if all((st % OCT) != th_pc for st in (s0, s1, s2, s3, s4)):
                th_cands = [st for st in gv if (st % OCT) == th_pc]
                s3 = th_cands[0] if th_cands else min(68, span.tenor_root() + OCT + span.third_offset())
        if style == "baroque":
            seq = [s0, s2, s3, s4, s3, s2, s1, s3]
        elif style == "travis":
            seq = [s0, s3, s1, s4, s0, s2, s1, s3]
        elif style == "toccatina":
            seq = [s0, s2, s4, s3, s1, s3, s4, s2]
        elif style == "scherzo":
            seq = [s0, s1, s3, s4, s3, s2]
        else:  # "glass"
            seq = [s0, s2, s4, s3]

        t = span.start
        idx = 0
        while t < span.end - 0.08:
            st = seq[idx % len(seq)]
            b_rel = (t - span.start) % 4.0
            acc = 1.06 if b_rel < 0.04 else (0.96 if abs(b_rel - 2.0) < 0.05 else 0.85)
            ndur = min(step_beats * ring_mult, span.end - t - 0.07)
            self.note(track_id, t, max(0.10, ndur), st, vel * acc)
            t += step_beats
            idx += 1

    def campanella_cascade(
        self,
        start_beat: float,
        end_beat: float,
        groups: Sequence[Sequence[int]],
        vel: float,
        *,
        step_beats: float = 0.25,
        include_harp: bool = True,
        lead_steel: bool = False,
    ) -> None:
        """
        True classical/Spanish cross-string *campanella* cascade:
        - Each plucked player (`nylon_guitar` Stage Left, `steel_guitar` Stage Right, `harp`)
          plucks an entire 3–4 note intra-semitone comma group (e.g. {-1,0,+1}, {16,17,18,19},
          {30,31,32}, {42,43,44,45}) across adjacent strings (`slide_from_cents = 0`, `vibrato = 0`),
          answered antiphonally by the partner guitar & harp!
        - In 53-EDO: shimmering rising/falling microtonal bell scales on BOTH guitars.
        - In 12-TET: each 3–4 note cell collapses onto a single repeated MIDI pitch (clunky stutter!).
        - Within-bucket comma neighbors release crisply (`overlap <= 0.03b << 0.20s` -> 0 comma clashes!).
        """
        players = (
            ["steel_guitar", "nylon_guitar", "harp"]
            if (lead_steel and include_harp)
            else (["nylon_guitar", "steel_guitar", "harp"] if include_harp else ["nylon_guitar", "steel_guitar"])
        )
        if not groups:
            return
        t = start_beat
        g_idx = 0
        total_dur = max(0.5, end_beat - start_beat)
        while t < end_beat - 0.06:
            grp = groups[g_idx % len(groups)]
            tid = players[g_idx % len(players)]
            for j, st in enumerate(grp):
                if t >= end_beat - 0.06:
                    break
                u = (t - start_beat) / total_dur
                arch = 0.92 + 0.16 * math.sin(math.pi * min(1.0, u))
                is_last_in_cell = (j == len(grp) - 1)
                # Intra-cell comma steps release crisply right at next pluck; final note of cell rings out
                # across the next group (provided next group is in a consonant non-adjacent bucket!)
                next_grp = groups[(g_idx + 1) % len(groups)]
                next_first = next_grp[0] if next_grp else st
                if not is_last_in_cell:
                    ndur = step_beats + 0.02
                elif 1 <= mod53_dist(st, next_first) <= 6 and st != next_first:
                    ndur = step_beats + 0.02
                else:
                    ndur = min(step_beats * 2.6, end_beat - t - 0.06)
                self.note(tid, t, max(0.08, min(ndur, end_beat - t - 0.05)), st, vel * arch, exact_step=True, trim_to_chord=False)
                t += step_beats
            g_idx += 1

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
        exact_step: bool = False,
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
                exact_step=exact_step,
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
        trim_tail: float = 0.14,
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
        note_dur: float = 1.6,
        ascending: bool = True,
        max_notes: int = 7,
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
            self.add_pedal("harp", beat, (span.end - beat) - 0.16)
        for i, st in enumerate(pts):
            t = beat + i * spacing
            if t >= span.end - 0.10:
                break
            u = i / max(1, n - 1)
            arch = 0.94 + 0.14 * math.sin(math.pi * u)
            self.note("harp", t, min(note_dur, span.end - t - 0.09), st, vel * arch)

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
            if span.quality in ("add9", "min9", "dom9")
            else (r + sev if sev is not None else r + OCT + th)
        )
        top_root = r + P5 if span.quality == "maj7" else r + OCT
        if style == "nocturne":
            seq = [r, r + P5, r + OCT + th, upper_color, r + OCT + P5, upper_color, r + OCT + th, r + P5]
        elif style == "staccato":
            seq = [r + P5, top_root, r + OCT + th, r + OCT + P5, r + OCT + th, top_root]
        elif style == "triplet":
            seq = [r, r + P5, r + OCT + th, r + OCT + P5, upper_color, r + OCT + th]
        elif style == "scherzo":
            seq = [r, r + P5, top_root, r + OCT + th, r + OCT + P5, r + OCT + th, top_root, r + P5]
        else:  # "grand"
            seq = [r, r + P5, top_root, r + OCT + th, upper_color, r + OCT + P5, r + 2 * OCT + th - th, upper_color]

        dur_span = span.end - span.start
        if use_pedal and dur_span >= 1.4 and style in ("nocturne", "triplet", "grand"):
            self.add_pedal("piano", span.start + 0.02, dur_span - 0.18)

        t = span.start
        idx = 0
        while t < span.end - 0.08:
            st = seq[idx % len(seq)]
            b_rel = (t - span.start) % 4.0
            if style in ("scherzo", "staccato"):
                acc = 1.08 if b_rel < 0.04 else 0.84
                ndur = min(step_beats * 0.62, span.end - t - 0.06)
            else:
                acc = 1.06 if b_rel < 0.04 else 0.88
                ndur = min(step_beats * 1.15, span.end - t - 0.08)
            self.note("piano", t, max(0.08, ndur), st, vel * acc)
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
            self.note("timpani", t, min(spacing * 1.5, end - t + 0.08), step, v, trim_to_chord=False)
            t += spacing

    def phrase(
        self,
        track_id: str,
        events: Sequence[Tuple[float, float, int, float]],
        *,
        vibrato: float = 0.18,
        indian_meend: bool = False,
        default_swell: Optional[str] = None,
        exact_step: bool = False,
    ) -> None:
        """
        Clean classical/raga melodic phrase.
        - Western instruments ALWAYS get `slide_from_cents = 0.0` (zero wailing!).
        - `sitar` in Section III may use subtle `<= 32c` meend when `indian_meend=True`.
        """
        n = len(events)
        is_wind = self.tracks[track_id].instrument in WIND_BRASS
        for i, (b, d, st, v) in enumerate(events):
            u = i / max(1, n - 1) if n > 1 else 0.5
            arch = 0.93 + 0.13 * math.sin(math.pi * (u ** 0.85))
            slide = 0.0
            meend = 0.0
            if indian_meend and track_id in INDIAN_TRACKS and (SEC3_START <= b < SEC3_END):
                if track_id == "sitar" and i > 0:
                    pb, pd, pst, _ = events[i - 1]
                    diff = st - pst
                    if 1 <= abs(diff) <= 5 and (b - (pb + pd)) < 0.35 and d >= 0.5:
                        slide = max(-32.0, min(32.0, -diff * (1200.0 / OCT) * 0.72))
                elif track_id in ("ektara", "dotara") and d >= 0.7:
                    meend = 18.0
            sw = default_swell
            if sw is None and (is_wind or track_id in ("viola", "cello")) and d >= 1.1:
                sw = "arch" if i < n - 1 else "dim"
            vib = (
                vibrato
                if d >= 0.80 and track_id in ("viola", "cello", "english_horn", "clarinet", "french_horn")
                else 0.0
            )
            self.note(
                track_id,
                b,
                d,
                st,
                v * arch,
                slide_from_cents=slide,
                meend_cents=meend,
                swell=sw,
                vibrato=vib,
                exact_step=exact_step,
            )

    def _finalize_safety_passes(self) -> None:
        """
        Deterministic acoustic safety post-passes:
        1. Trim notes across incompatible ChordSpan boundaries.
        2. Enforce 0 `< C3` low-register mud overlaps (>= 0.08s, 0 < diff < 22).
        3. Enforce 0 `1..=3` mod-53 comma clashes (>= 0.17s).
        4. Enforce 0 sustained `4..=6`-step close-register rubs (> 0.30b).
        5. Enforce <= 13 simultaneous active voices per SF2 track (0 voice steals) & wind breaths.
        """
        self.grid.sort(key=lambda s: s.start)

        # Build flat list of mutable note references for cross-track timing checks
        flat = []
        for tr in self.tracks.values():
            is_perc = tr.instrument == "timpani"
            for n in tr.notes:
                if not is_perc:
                    flat.append((tr.id, n))

        # Sort by onset beat
        flat.sort(key=lambda item: (item[1]["beat"], item[0]))

        # Pass A: Prevent sustained 4..=6 step rubs (> 0.30b) & < C3 low mud & >= 0.17s comma clashes
        for idx_a in range(len(flat)):
            tid_a, na = flat[idx_a]
            b0_a = na["beat"]
            b1_a = b0_a + na["dur"]
            s0_a = self.tempo.beat_to_seconds(b0_a)
            s1_a = max(s0_a + 0.01, self.tempo.beat_to_seconds(b1_a))
            st_a = na["step"]

            for idx_b in range(idx_a + 1, len(flat)):
                tid_b, nb = flat[idx_b]
                b0_b = nb["beat"]
                if b0_b >= b1_a - 0.01:
                    break
                b1_b = b0_b + nb["dur"]
                st_b = nb["step"]

                # 1) Low mud (< -53, 0 < diff < 22, overlap >= 0.06s)
                if st_a < -OCT and st_b < -OCT and 0 < abs(st_a - st_b) < P4:
                    s0_b = self.tempo.beat_to_seconds(b0_b)
                    s1_b = max(s0_b + 0.01, self.tempo.beat_to_seconds(b1_b))
                    if min(s1_a, s1_b) - max(s0_a, s0_b) >= 0.06:
                        if b0_b > b0_a + 0.06:
                            na["dur"] = round(max(0.06, b0_b - b0_a - 0.03), 4)
                            b1_a = b0_a + na["dur"]
                            s1_a = self.tempo.beat_to_seconds(b1_a)
                        else:
                            # Simultaneous low notes: lift the upper-capable track up an octave
                            nb["step"] = st_b + OCT
                            st_b = nb["step"]

                # 2) Comma clash (1 <= mod53_dist <= 3, overlap >= 0.16s)
                d_mod = mod53_dist(st_a, st_b)
                if 1 <= d_mod <= 3:
                    s0_b = self.tempo.beat_to_seconds(b0_b)
                    s1_b = max(s0_b + 0.01, self.tempo.beat_to_seconds(b1_b))
                    ov_s = min(s1_a, s1_b) - max(s0_a, s0_b)
                    if ov_s >= 0.16:
                        target_end_s = s0_b + 0.10 if s0_b > s0_a + 0.04 else s0_a + 0.12
                        new_end_b = self.tempo.seconds_to_beat_approx(target_end_s, b0_a, b1_a)
                        na["dur"] = round(max(0.06, new_end_b - b0_a), 4)
                        b1_a = b0_a + na["dur"]
                        s1_a = self.tempo.beat_to_seconds(b1_a)

                # 3) Close semitone rub (4 <= abs(st_a - st_b) <= 6, overlap > 0.28b or > 0.28s)
                if 4 <= abs(st_a - st_b) <= 6:
                    s0_b = self.tempo.beat_to_seconds(b0_b)
                    s1_b = max(s0_b + 0.01, self.tempo.beat_to_seconds(b1_b))
                    ov_b = min(b1_a, b1_b) - max(b0_a, b0_b)
                    ov_s = min(s1_a, s1_b) - max(s0_a, s0_b)
                    if ov_b > 0.28 or ov_s > 0.28:
                        if nb["dur"] <= na["dur"] and b0_b >= b0_a:
                            nb["dur"] = round(min(nb["dur"], 0.24), 4)
                        elif b0_b > b0_a + 0.08:
                            na["dur"] = round(max(0.06, (b0_b + 0.22) - b0_a), 4)
                            b1_a = b0_a + na["dur"]
                            s1_a = self.tempo.beat_to_seconds(b1_a)
                        else:
                            lo_b, hi_b = SWEET_SPOTS[tid_b]
                            if st_b + OCT <= hi_b:
                                nb["step"] = st_b + OCT
                            elif st_b - OCT >= max(-OCT, lo_b):
                                nb["step"] = st_b - OCT
                            else:
                                nb["dur"] = round(min(nb["dur"], 0.24), 4)

        # Pass B: Per-track SF2 15-channel polyphony cap (cap cleanly at <= 13 active voices!)
        # and natural wind/brass breathing rests
        for tr in self.tracks.values():
            tr.notes.sort(key=lambda x: (x["beat"], x["step"]))
            is_sf2 = tr.instrument not in ("ektara", "dotara")
            if is_sf2 and len(tr.notes) > 13:
                active_notes: List[Dict] = []
                for n in tr.notes:
                    s0 = self.tempo.beat_to_seconds(n["beat"])
                    active_notes = [
                        an for an in active_notes
                        if self.tempo.beat_to_seconds(an["beat"] + an["dur"]) > s0 + 0.005
                    ]
                    while len(active_notes) >= 13:
                        # Trim the earliest-started note so it releases cleanly before `s0`
                        oldest = min(active_notes, key=lambda an: an["beat"])
                        active_notes.remove(oldest)
                        target_b = self.tempo.seconds_to_beat_approx(
                            max(self.tempo.beat_to_seconds(oldest["beat"]) + 0.04, s0 - 0.015),
                            oldest["beat"],
                            oldest["beat"] + oldest["dur"],
                        )
                        oldest["dur"] = round(max(0.06, target_b - oldest["beat"]), 4)
                    active_notes.append(n)

            if tr.instrument in WIND_BRASS and len(tr.notes) > 1:
                run_start = tr.notes[0]["beat"]
                for i in range(1, len(tr.notes)):
                    prev = tr.notes[i - 1]
                    cur = tr.notes[i]
                    prev_end = prev["beat"] + prev["dur"]
                    gap = cur["beat"] - prev_end
                    if gap >= 0.80:
                        run_start = cur["beat"]
                    elif (cur["beat"] + cur["dur"]) - run_start > 12.5:
                        new_dur = (cur["beat"] - 0.88) - prev["beat"]
                        if new_dur >= 0.18:
                            prev["dur"] = round(new_dur, 4)
                            run_start = cur["beat"]

    def build_dict(self) -> Dict:
        self._finalize_safety_passes()
        tracks_json = []
        for tr in self.tracks.values():
            sorted_notes = sorted(tr.notes, key=lambda x: (x["beat"], x["step"]))
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
            "title": "The Shattered Semitone (v2) — Concerto Grosso for Dual Guitars & 53-EDO Orchestra",
            "description": (
                "Stage-independent ~10-minute 53-EDO concerto grosso starring Classical Nylon Guitar "
                "and Acoustic Steel Guitar alongside Orchestral Harp, Indian Shruti Lutes (Sitar, Dotara, "
                "Ektara), Chamber Orchestra, and Cathedral Pipe Organ. Engineered with zero Western "
                "pitch-bend glides and crisp plucked transients to prove 53-EDO vs 12-TET immediately: "
                "sparkling cross-string campanella cascades inside single 12-TET semitones, Eagle-53 "
                "3-step (25:24) chromatic mediants, East-West 1-2 shruti raga dialogues, a 5-variation "
                "C -> Am -> Dm -> G -> C syntonic comma passacaglia pump (k = -2 -> +3), exposed guitar "
                "[38, 2, 16] Ab++ Major chords that shear into root-position A minor in 12-TET, "
                "7-limit & 11-limit glass harmonics, and a triumphant 19-track finale."
            ),
            "sample_rate": 48000,
            "sections": sections_json,
            "tempo": self.tempo.to_json(),
            "tracks": tracks_json,
        }


# =============================================================================
# Compose All 7 Movements (~600.0s = 10:00)
# =============================================================================
def compose_53vs12() -> Tuple[ScoreBuilder, Dict]:
    tempo_segments = [
        # I. Campanella Prelude: The Shattered Semitone (0:00–1:25, beats 0..164, 112 -> 118 BPM)
        (0.0, 112.0),
        (64.0, 118.0),
        (140.0, 116.0),
        (163.99, 112.0),
        # II. Fretted Toccatina & Eagle-53 Chromatic Mediants (1:25–2:49, beats 164..340, 126 BPM)
        (164.0, 126.0),
        (324.0, 126.0),
        (339.99, 118.0),
        # III. East–West Plucked Shruti Dialogue (2:49–4:13, beats 340..464, 82 -> 92 BPM)
        (340.0, 82.0),
        (400.0, 92.0),
        (448.0, 90.0),
        (463.99, 84.0),
        # IV. The Syntonic Comma Pump: C -> Am -> Dm -> G -> C Passacaglia (4:13–5:42, beats 464..624, 98 -> 116 BPM)
        (464.0, 98.0),
        (544.0, 110.0),
        (592.0, 116.0),
        (623.99, 108.0),
        # V. Scherzo of the Diesis Shear: Ab++ Major -> 12-TET A minor (5:42–7:13, beats 624..816, 130 BPM)
        (624.0, 130.0),
        (768.0, 130.0),
        (800.0, 122.0),
        (815.99, 96.0),
        # VI. Adagio of Glass Harmonics: 7-Limit & 11-Limit Resonance (7:13–8:35, beats 816..904, 64 BPM)
        (816.0, 64.0),
        (880.0, 64.0),
        (903.99, 68.0),
        # VII. Finale: The 53-Tone Continuum (8:35–10:00, beats 904..1052, 116 -> 126 -> 68 BPM)
        (904.0, 116.0),
        (960.0, 126.0),
        (1016.0, 120.0),
        (1036.0, 82.0),
        (1052.0, 68.0),
    ]
    sb = ScoreBuilder(tempo_segments)

    sb.add_section(0.0, "I. Campanella Prelude: The Shattered Semitone")
    sb.add_section(164.0, "II. Fretted Toccatina & Eagle-53 Chromatic Mediants")
    sb.add_section(340.0, "III. East–West Plucked Shruti Dialogue")
    sb.add_section(464.0, "IV. The Syntonic Comma Pump (C -> Am -> Dm -> G -> C Passacaglia)")
    sb.add_section(624.0, "V. Scherzo of the Diesis Shear (Ab++ Major -> 12-TET A minor)")
    sb.add_section(816.0, "VI. Adagio of Glass Harmonics (7-Limit & 11-Limit Resonance)")
    sb.add_section(904.0, "VII. Finale: The 53-Tone Continuum")

    # =========================================================================
    # SECTION I (Beats 0..164, 0:00–1:25, 112 -> 118 BPM):
    #   CAMPANELLA PRELUDE — THE SHATTERED SEMITONE
    #   Immediate 0:00–0:30 A/B showcase: antiphonal Nylon Guitar <-> Steel Guitar
    #   + Harp cross-string campanella cascades inside single 12-TET semitone
    #   buckets ({-1,0,+1}, {16,17,18}, {30,31,32}, {42,43,44}) alternating with
    #   ringing beatless 6-string 4:5:6 & 4:5:6:7:9 guitar chords!
    # =========================================================================
    # I.A (0..64, ~0:00–0:34): Exposed Dual-Guitar & Harp Campanella + Ringing 6-String Chords
    # Statement 1 (0..16): C Tonic & Septimal C9
    sb.add_span(0.0, 4.0, C, "maj", "I.A1 Campanella Cascade on C/E/G/Bb Buckets", free_microtonal=True)
    sp_c_ring = sb.add_span(4.0, 8.0, C, "maj", "I.A2 Ringing 6-String Pure 4:5:6 C Major")
    sb.add_span(8.0, 12.0, C, "dom9", "I.A3 Campanella Cascade Ascending to D5", free_microtonal=True)
    sp_c9_ring = sb.add_span(12.0, 16.0, C, "dom9", "I.A4 Ringing 6-String Pure 4:5:6:7:9 C9")

    # Bar 1 (0..4): Immediate 0:00 sparkling 16th-note campanella across {-1,0,+1}, {16,17,18}, {30,31,32}, {42,43,44}!
    sb.campanella_cascade(
        0.0, 3.85,
        [[-1, 0, +1], [16, 17, 18], [30, 31, 32], [42, 43, 44], [52, 53, 54]],
        vel=0.68,
        step_beats=0.25,
        include_harp=True,
        lead_steel=False,
    )
    # Bar 2 (4..8): Beatless 6-string 4:5:6 C Major Guitar Lock!
    c_maj_6 = [-53, -22, 0, 17, 31, 53]
    sb.guitar_strum("nylon_guitar", 4.0, 3.7, c_maj_6, vel=0.76, roll=0.05)
    sb.guitar_strum("steel_guitar", 4.25, 3.45, c_maj_6, vel=0.74, roll=0.045, upstroke=True)
    sb.harp_sweep(sp_c_ring, 4.5, -53, 70, vel=0.66, spacing=0.22, note_dur=2.8, max_notes=7, with_pedal=True)

    # Bar 3 (8..12): Steel-led campanella cascade across {16..19} (E4), {30..32} (G4), {42..45} (Bb4), {61..63} (D5)!
    sb.campanella_cascade(
        8.0, 11.85,
        [[16, 17, 18, 19], [30, 31, 32], [42, 43, 44, 45], [61, 62, 63]],
        vel=0.72,
        step_beats=0.25,
        include_harp=True,
        lead_steel=True,
    )
    # Bar 4 (12..16): Beatless 6-string 4:5:6:7:9 Septimal C9 Guitar Lock!
    c_dom9_6 = [-53, -22, 17, 31, 43, 62]
    sb.guitar_strum("steel_guitar", 12.0, 3.7, c_dom9_6, vel=0.78, roll=0.05)
    sb.guitar_strum("nylon_guitar", 12.25, 3.45, c_dom9_6, vel=0.76, roll=0.045, upstroke=True)
    sb.harp_sweep(sp_c9_ring, 12.5, -53, 70, vel=0.70, spacing=0.20, note_dur=2.8, ascending=False, max_notes=7, with_pedal=True)

    # Statement 2 (16..32): Answer in F Major (A4 = 39 = 440.00 Hz!) & Septimal F9
    sb.add_span(16.0, 20.0, F, "maj", "I.A5 Campanella Cascade on F/A(440Hz)/C/Eb Buckets", free_microtonal=True)
    sp_f_ring = sb.add_span(20.0, 24.0, F, "add9", "I.A6 Ringing 6-String Pure F add9 (A4=440Hz)")
    sb.add_span(24.0, 28.0, F, "dom9", "I.A7 Campanella Cascade on Eb(12..15) & A(38..41)", free_microtonal=True)
    sp_f9_ring = sb.add_span(28.0, 32.0, F, "dom9", "I.A8 Ringing 6-String Pure 4:5:6:7:9 F9")

    sb.campanella_cascade(
        16.0, 19.85,
        [[-32, -31, -30], [-1, 0, +1], [21, 22, 23], [38, 39, 40, 41], [52, 53, 54]],
        vel=0.70,
        step_beats=0.25,
        include_harp=True,
    )
    f_add9_6 = [-84, -31, 0, 22, 39, 62 - 31]  # [-84(F2), -31(F3), 0(C4), 22(F4), 31(G4=9th!), 39(A4=440Hz)]
    sb.guitar_strum("nylon_guitar", 20.0, 3.7, f_add9_6, vel=0.78, roll=0.05)
    sb.guitar_strum("steel_guitar", 20.3, 3.4, [-84, -31, 0, 22, 39, 53], vel=0.76, roll=0.045, upstroke=True)
    sb.harp_sweep(sp_f_ring, 20.5, -31, 75, vel=0.68, spacing=0.22, note_dur=2.8, max_notes=7, with_pedal=True)

    sb.campanella_cascade(
        24.0, 27.85,
        [[12, 13, 14, 15], [21, 22, 23], [30, 31, 32], [38, 39, 40, 41], [65, 66, 67]],
        vel=0.74,
        step_beats=0.25,
        include_harp=True,
        lead_steel=True,
    )
    f_dom9_6 = [-84, -31, 0, 12, 31, 39]  # Pure 4:5:6:7:9 on F (Eb_harm=12, G=31, A=39=440Hz)!
    sb.guitar_strum("steel_guitar", 28.0, 3.7, f_dom9_6, vel=0.80, roll=0.05)
    sb.guitar_strum("nylon_guitar", 28.3, 3.4, f_dom9_6, vel=0.78, roll=0.045, upstroke=True)
    sb.note("pizzicato", 28.0, 0.5, -31, 0.58)
    sb.note("cello", 28.0, 3.5, -84, 0.54, swell="dim", vibrato=0.16)

    # Statement 3 (32..64): Baroque Spanish Dual-Guitar Progression + Chamber Awakening (p -> mf)
    s1_baroque_specs = [
        (32.0, 36.0, BB, "add9", "I.A9 Bb add9"),
        (36.0, 40.0, G_MINUS, "min_dm", "I.A10 Gm-"),
        (40.0, 44.0, D_MINUS, "min_dm", "I.A11 Dm-"),
        (44.0, 48.0, A, "dom7", "I.A12 A7 (4:5:6:7 on 440Hz!)"),
        (48.0, 52.0, D, "min7", "I.A13 Dm7"),
        (52.0, 56.0, G, "dom9", "I.A14 G9 (7:4 = step 21)"),
        (56.0, 60.0, C, "add9", "I.A15 C add9"),
        (60.0, 64.0, C, "maj", "I.A16 Campanella Echo Bridge", True),
    ]
    for idx, spec in enumerate(s1_baroque_specs):
        b0, b1, rpc, qual, lbl = spec[:5]
        is_free = spec[5] if len(spec) > 5 else False
        sp = sb.add_span(b0, b1, rpc, qual, lbl, free_microtonal=is_free)
        dyn = 0.44 + 0.035 * idx
        if not is_free:
            sb.guitar_fingerstyle("nylon_guitar", sp, vel=dyn + 0.08, style="baroque", step_beats=0.25, ring_mult=1.7)
            sb.guitar_strum("steel_guitar", b0, 1.75, sp.guitar_voicing(5), vel=dyn + 0.06, roll=0.04)
            sb.guitar_strum("steel_guitar", b0 + 2.0, 1.75, sp.guitar_voicing(5), vel=dyn + 0.04, roll=0.04, upstroke=True)
            sb.note("pizzicato", b0, 0.45, sp.tenor_root(), dyn * 0.90)
            sb.note("pizzicato", b0 + 2.0, 0.45, sp.tenor_root() + P5, dyn * 0.86)
            if idx % 2 == 0:
                sb.note("cello", b0, 3.6, sp.bass_root(-106, -54), dyn * 0.92, swell="arch", vibrato=0.18)
        else:
            sb.campanella_cascade(
                b0, b1 - 0.15,
                [[-1, 0, +1], [16, 17, 18, 19], [30, 31, 32], [52, 53, 54]],
                vel=0.52,
                step_beats=0.25,
                include_harp=True,
            )

    # Crisp Mozartian Clarinet & Viola counterpoint (ZERO slide_from_cents!)
    sb.phrase("clarinet", [
        (32.5, 1.3, pitch(D_MINUS, 5), 0.50),
        (34.0, 1.7, pitch(F, 4), 0.48),
        (36.5, 1.3, pitch(BB, 4), 0.52),
        (38.0, 1.7, pitch(D_MINUS, 5), 0.54),
        # Breath 39.7..40.5
        (40.5, 1.4, pitch(A, 4), 0.56),
        (42.0, 1.7, pitch(F, 4), 0.54),
        (44.5, 2.8, pitch(CS_EAGLE, 5), 0.60),   # Pure 5:4 of A4 (39+17=56)!
        # Breath 47.3..48.5
        (48.5, 1.4, pitch(C, 5), 0.62),
        (50.0, 1.7, pitch(A, 4) + 1, 0.60),
        (52.5, 1.4, 21 + OCT, 0.66),             # Septimal 7:4 of G in oct 5!
        (54.0, 1.7, pitch(B, 4), 0.64),
        (56.0, 3.4, pitch(E, 5), 0.68),
    ], vibrato=0.18)

    # I.B (64..128, ~0:34–1:07): Concerto Grosso Dialogue — Tutti Orchestra <-> Solo Campanella Guitars!
    s1_concerto = [
        (64.0, 70.0, C, "add9", "I.B1 Tutti C add9", False),
        (70.0, 76.0, A, "min7", "I.B2 Tutti Am7 (A4=440Hz)", False),
        (76.0, 80.0, C, "maj", "I.B3 Solo Guitar Campanella on E4 & Bb4", True),
        (80.0, 86.0, F, "add9", "I.B4 Tutti F add9", False),
        (86.0, 92.0, G, "dom9", "I.B5 Tutti Septimal G9", False),
        (92.0, 96.0, G, "maj", "I.B6 Solo Guitar Campanella on G4 & D5", True),
        (96.0, 102.0, E, "dom7", "I.B7 Radiant E7 [17,34,48,7]", False),
        (102.0, 108.0, A, "min7", "I.B8 Lush Am7", False),
        (108.0, 114.0, D_MINUS, "min_dm", "I.B9 Dm- Subdominant", False),
        (114.0, 120.0, G, "dom7", "I.B10 G7 Dominant", False),
        (120.0, 128.0, C, "add9", "I.B11 Radiant C add9 Arrival", False),
    ]
    for idx, (b0, b1, rpc, qual, lbl, is_free) in enumerate(s1_concerto):
        sp = sb.add_span(b0, b1, rpc, qual, lbl, free_microtonal=is_free)
        dur = b1 - b0
        if is_free:
            # Intimate p-mp solo guitar + harp campanella spotlight (contrasts dynamically with tutti f!)
            buckets = (
                [[16, 17, 18, 19], [30, 31, 32], [42, 43, 44, 45], [52, 53, 54]]
                if rpc == C
                else [[8, 9, 10], [30, 31, 32, 33], [47, 48, 49], [61, 62, 63]]
            )
            sb.campanella_cascade(b0, b1 - 0.14, buckets, vel=0.52, step_beats=0.25, include_harp=True, lead_steel=(rpc == G))
        else:
            dyn = 0.66 + 0.015 * idx
            sb.string_pad(sp, vel=dyn * 0.85, swell="arch")
            sb.guitar_fingerstyle("steel_guitar", sp, vel=dyn + 0.06, style="travis", step_beats=0.5, ring_mult=1.6)
            sb.guitar_fingerstyle("nylon_guitar", sp, vel=dyn + 0.04, style="baroque", step_beats=0.5, ring_mult=1.5)
            sb.piano_figuration(sp, vel=dyn * 0.80, style="nocturne", step_beats=0.5)
            if idx % 2 == 0:
                sb.harp_sweep(sp, b0 + 0.2, -53, 84, vel=dyn * 0.90, spacing=0.20, note_dur=2.2, max_notes=7, with_pedal=True)
                sb.note("bassoon", b0, dur - 0.95, sp.bass_root(), dyn * 0.88, swell="arch")
            sb.note("cello", b0, dur * 0.5 - 0.15, sp.bass_root(), dyn * 0.92, vibrato=0.20)
            sb.note("cello", b0 + dur * 0.5, dur * 0.5 - 0.25, sp.tenor_root() + P5, dyn * 0.86, vibrato=0.18)
            if idx in (4, 6, 9, 10):
                sb.note("french_horn", b0 + 0.2, dur - 1.1, sp.tenor_root() + P5, dyn * 0.88, swell="arch", vibrato=0.14)

    sb.phrase("english_horn", [
        (64.5, 2.4, pitch(E, 4), 0.64),
        (67.2, 2.4, pitch(D, 4), 0.62),
        (70.4, 2.6, pitch(C, 4), 0.66),
        (73.2, 2.4, pitch(E, 4), 0.64),
        # Solo guitar interlude 76..80 acts as natural breath!
        (80.4, 2.6, pitch(A, 4), 0.68),
        (83.2, 2.4, pitch(G, 4), 0.66),
        (86.4, 2.6, 21, 0.72),                  # Pure 7:4 of G!
        (89.2, 2.4, pitch(D, 4), 0.68),
        # Solo guitar interlude 92..96!
        (96.4, 2.6, pitch(GS_EAGLE, 4), 0.74),  # Pure 5:4 of E!
        (99.2, 2.4, pitch(B, 4), 0.72),
        (102.4, 4.8, pitch(C, 5), 0.74),
        # Breath 107.2..114.4
        (114.4, 2.6, 21, 0.72),
        (117.2, 2.4, pitch(B, 3), 0.70),
        (120.2, 5.8, pitch(E, 4), 0.76),
    ], vibrato=0.20)

    # I.C (128..164, ~1:07–1:25): Hushed Subito-Piano Campanella Coda & Crisp E-Major Pivot
    sb.add_span(128.0, 136.0, C, "maj", "I.C1 Subito pp Campanella Whisper", free_microtonal=True)
    sp_ic2 = sb.add_span(136.0, 144.0, F, "maj7", "I.C2 Luminous Glass F maj7")
    sp_ic3 = sb.add_span(144.0, 152.0, D_MINUS, "min_dm", "I.C3 Dm- Chamber Bridge")
    sp_ic4 = sb.add_span(152.0, 158.0, B - P5, "maj", "I.C4 E Major Pivot [17,34,48]")  # B - P5 = 17 = E!
    sp_ic5 = sb.add_span(158.0, 164.0, E, "dom7", "I.C5 Crisp Plucked E7 Launch into Toccatina")

    sb.campanella_cascade(
        128.0, 135.8,
        [[-1, 0, +1], [16, 17, 18], [30, 31, 32], [42, 43, 44]],
        vel=0.38,
        step_beats=0.3333,
        include_harp=True,
    )
    for sp_c, v_c in ((sp_ic2, 0.38), (sp_ic3, 0.42), (sp_ic4, 0.50), (sp_ic5, 0.58)):
        sb.guitar_fingerstyle("nylon_guitar", sp_c, vel=v_c + 0.06, style="baroque", step_beats=0.5, ring_mult=1.8)
        sb.guitar_strum("steel_guitar", sp_c.start, (sp_c.end - sp_c.start) * 0.48, sp_c.guitar_voicing(5), vel=v_c + 0.05, roll=0.05)
        sb.string_pad(sp_c, vel=v_c * 0.78, swell="arch")
    sb.harp_sweep(sp_ic5, 158.2, -36, 70, vel=0.62, spacing=0.18, note_dur=1.8, max_notes=7)

    # =========================================================================
    # SECTION II (Beats 164..340, 1:25–2:50, 126 BPM):
    #   FRETTED TOCCATINA & EAGLE-53 CHROMATIC MEDIANTS
    #   Driving plucked counterpoint (`steel_guitar`, `nylon_guitar`, `pizzicato`,
    #   `harp`, staccato `piano` & `clarinet`) exploring John O'Sullivan's Eagle-53
    #   `3`-step (`67.9c`, `25:24`) chromatic-mediant shifts (`E <-> G <-> G#`,
    #   `C <-> C#`, `Db7 [5,22,36,48]` & `Ab7 [36,0,14,26]`, `F7` & `C7`) +
    #   4-voice plucked fugato!
    # =========================================================================
    # II.A (164..252): Driving Eagle-53 Chromatic-Mediant Toccatina (126 BPM)
    toccatina_plan = [
        # Cycle 1 (164..196): E(17) <-> G(31) <-> G#(34) <-> E(17) Eagle-53 3-Step Mediant Orbit!
        (164.0, 172.0, E, "maj", "II.A1 E Major [17,34,48]"),
        (172.0, 180.0, G, "maj", "II.A2 G Major [31,48,9] (holds B=48; G=31 is -3 steps below G#=34!)"),
        (180.0, 188.0, GS_EAGLE, "maj", "II.A3 G# Major [34,51,12] (+3 steps 25:24 Eagle-53 lift from G!)"),
        (188.0, 196.0, E, "dom7", "II.A4 E7 [17,34,48,7] (holds G#=34!)"),
        # Cycle 2 (196..228): A(39) -> C(0) <-> C#(3) -> F7 [22,39,0,12] -> Db7 [5,22,36,48] -> C7 [0,17,31,43]!
        (196.0, 202.0, A, "maj", "II.A5 A Major [39,3,17] (introduces C#=3!)"),
        (202.0, 208.0, C, "maj", "II.A6 C Major [0,17,31] (-3 steps 25:24 Eagle shift C#->C, holds E=17!)"),
        (208.0, 214.0, CS_EAGLE, "maj", "II.A7 C# Major [3,20,34] (+3 steps 25:24 Eagle shift C->C#!)"),
        (214.0, 220.0, F, "dom7", "II.A8 Pure F7 [22,39,0,12]"),
        (220.0, 224.0, DB, "dom7", "II.A9 Eagle Augmented-6th Db7 [5,22,36,48] (holds F=22!)"),
        (224.0, 228.0, C, "dom7", "II.A10 Pure C7 [0,17,31,43]"),
        # Cycle 3 (228..252): Ab7 [36,0,14,26] -> G(31) <-> G#(34) -> Ab7 [36,0,14,26] -> G7 -> C!
        (228.0, 234.0, AB, "dom7", "II.A11 Eagle Augmented-6th Ab7 [36,0,14,26] (holds C=0!)"),
        (234.0, 240.0, G, "maj", "II.A12 G Major [31,48,9] (26->31 & 36->31 symmetrical +/-5 resolution!)"),
        (240.0, 244.0, GS_EAGLE, "maj", "II.A13 G# Major [34,51,12] (+3 steps 25:24!)"),
        (244.0, 248.0, G, "dom7", "II.A14 G7 [31,48,9,21] (-3 steps back to G7!)"),
        (248.0, 252.0, C, "add9", "II.A15 Crisp Toccatina Cadence on C add9"),
    ]
    for idx, (b0, b1, rpc, qual, lbl) in enumerate(toccatina_plan):
        sp = sb.add_span(b0, b1, rpc, qual, lbl)
        dur = b1 - b0
        dyn = 0.56 + 0.015 * (idx % 8)
        # Rapid alternating 8th/16th motoric Toccatina between Steel Guitar & Nylon Guitar!
        sb.guitar_fingerstyle("steel_guitar", sp, vel=dyn + 0.10, style="toccatina", step_beats=0.25 if idx % 2 == 0 else 0.5, ring_mult=1.25)
        sb.guitar_fingerstyle("nylon_guitar", sp, vel=dyn + 0.08, style="baroque", step_beats=0.5 if idx % 2 == 0 else 0.25, ring_mult=1.35)
        # Crisp offbeat Pizzicato + Harp + Staccato Piano
        r = sp.tenor_root()
        th = sp.third_offset()
        t_p = b0
        while t_p < b1 - 0.4:
            sb.note("pizzicato", t_p, 0.32, r, dyn * 0.92)
            sb.note("pizzicato", t_p + 1.0, 0.30, r + P5, dyn * 0.86)
            if t_p + 1.5 < b1 - 0.3:
                sb.note("harp", t_p + 0.5, 0.85, r + OCT + th, dyn * 0.90)
                sb.note("harp", t_p + 1.5, 0.85, r + OCT + P5, dyn * 0.88)
            t_p += 2.0
        sb.piano_figuration(sp, vel=dyn * 0.82, style="staccato", step_beats=0.5, use_pedal=False)
        if idx % 2 == 0:
            sb.note("bassoon", b0, min(2.6, dur - 0.9), sp.bass_root(), dyn * 0.88, swell="dim")
        # Staccato/articulate Clarinet & Viola highlighting the exact 3-step (67.9c) Eagle shifts!
        if b1 - b0 >= 4.0 and idx % 3 != 2:
            sb.phrase("clarinet", [
                (b0 + 0.0, 0.42, r + OCT + th, dyn + 0.10),
                (b0 + 0.5, 0.42, r + OCT + P5, dyn + 0.08),
                (b0 + 1.0, 0.85, r + OCT + th, dyn + 0.12),
                (b0 + 2.5, 1.10, r + 2 * OCT if qual != "maj7" else r + OCT + P5, dyn + 0.10),
            ], vibrato=0.10)

    # II.B (252..340): 4-Voice Plucked Fugato (`steel_guitar` -> `nylon_guitar` -> `harp` -> `pizzicato` + chamber ripieno)
    # Crisp Baroque/Neoclassical fugato subject with discrete microtonal ornament episodes!
    fugato_harmony = [
        # Exposition 1 (252..268): Voice 1 (`steel_guitar` solo subject) + `pizzicato` walking bass
        (252.0, 256.0, C, "maj", "II.B1 Fugato v1 C", False),
        (256.0, 260.0, G, "dom7", "II.B2 Fugato v1 G7", False),
        (260.0, 264.0, A, "min7", "II.B3 Fugato v1 Am7", False),
        (264.0, 268.0, E, "maj", "II.B4 Fugato v1 E (Eagle pivot)", False),
        # Exposition 2 (268..284): Voice 2 (`nylon_guitar` answer in G/D) + `steel_guitar` countersubject
        (268.0, 272.0, G, "maj", "II.B5 Fugato v2 G (+3 from E's G#=34!)", False),
        (272.0, 276.0, D, "dom7", "II.B6 Fugato v2 D7", False),
        (276.0, 280.0, E, "min7", "II.B7 Fugato v2 Em7", False),
        (280.0, 284.0, C, "dom7", "II.B8 Fugato v2 C7", False),
        # Episode 1 (284..292): Plucked Campanella Sequence (interlocking 3-voice microtonal hocket!)
        (284.0, 288.0, F, "maj", "II.B9 Fugato Campanella Episode F", True),
        (288.0, 292.0, C, "maj", "II.B10 Fugato Campanella Episode C", True),
        # Exposition 3 (292..308): Voice 3 (`harp`) + Voice 4 (`pizzicato`/`clarinet`) + Dual Guitars!
        (292.0, 296.0, F, "add9", "II.B11 Fugato v3 F add9", False),
        (296.0, 300.0, DB, "dom7", "II.B12 Fugato v3 Db7 [5,22,36,48]", False),
        (300.0, 304.0, C, "maj", "II.B13 Fugato v3 C", False),
        (304.0, 308.0, AB, "dom7", "II.B14 Fugato v3 Ab7 [36,0,14,26]", False),
        # Stretto & Toccatina Climax (308..340): Eagle-53 Stretto -> Hushed Open-5th Bridge to Section III
        (308.0, 314.0, G, "dom9", "II.B15 Stretto G9", False),
        (314.0, 320.0, GS_EAGLE, "maj", "II.B16 Stretto Eagle G# Major [34,51,12]", False),
        (320.0, 326.0, E, "dom7", "II.B17 Stretto E7", False),
        (326.0, 332.0, A, "min7", "II.B18 Stretto Am7 -> F9", False),
        (332.0, 336.0, G, "dom7", "II.B19 Cadential G7", False),
        (336.0, 340.0, C, "open5", "II.B20 Crisp Plucked C5 Bridge to Shruti Dialogue", False),
    ]

    def write_fugato_subject(track_id: str, sp: ChordSpan, oct_shift: int, vel: float) -> None:
        r = sp.tenor_root() + oct_shift * OCT
        th = sp.third_offset()
        b0 = sp.start
        # Crisp 8-note baroque subject: [root, P5, OCT, P5, th+OCT, P5, th, root]
        subj = [
            (b0 + 0.0, 0.42, r, vel + 0.08),
            (b0 + 0.5, 0.42, r + P5, vel + 0.04),
            (b0 + 1.0, 0.68, r + OCT, vel + 0.10),
            (b0 + 1.75, 0.22, r + P5, vel + 0.02),
            (b0 + 2.0, 0.42, r + OCT + th, vel + 0.12),
            (b0 + 2.5, 0.42, r + P5, vel + 0.05),
            (b0 + 3.0, 0.42, r + th, vel + 0.06),
            (b0 + 3.5, 0.38, r, vel + 0.04),
        ]
        sb.phrase(track_id, subj, vibrato=0.0)

    for idx, (b0, b1, rpc, qual, lbl, is_free) in enumerate(fugato_harmony):
        sp = sb.add_span(b0, b1, rpc, qual, lbl, free_microtonal=is_free)
        dur = b1 - b0
        if is_free:
            buckets = (
                [[21, 22, 23], [38, 39, 40, 41], [52, 53, 54]]
                if rpc == F
                else [[-1, 0, +1], [16, 17, 18, 19], [30, 31, 32], [42, 43, 44]]
            )
            sb.campanella_cascade(b0, b1 - 0.12, buckets, vel=0.64, step_beats=0.25, include_harp=True, lead_steel=(rpc == C))
            continue

        if idx < 4:
            # Exp 1: Steel Guitar solo subject + light Pizzicato bass
            write_fugato_subject("steel_guitar", sp, 1, 0.56)
            sb.note("pizzicato", b0, 0.45, sp.tenor_root(), 0.46)
            sb.note("pizzicato", b0 + 2.0, 0.45, sp.tenor_root() + P5, 0.44)
        elif idx < 8:
            # Exp 2: Nylon Guitar subject + Steel Guitar 16th countersubject + Cello staccato bass
            write_fugato_subject("nylon_guitar", sp, 1, 0.60)
            sb.guitar_fingerstyle("steel_guitar", sp, vel=0.54, style="baroque", step_beats=0.5, ring_mult=1.3)
            sb.note("cello", b0, 0.85, sp.bass_root(), 0.52, vibrato=0.14)
            sb.note("cello", b0 + 2.0, 0.85, sp.bass_root() + P5 if sp.bass_root() + P5 <= 17 else sp.bass_root(), 0.50)
        elif idx < 14:
            # Exp 3: Harp subject + Dual Guitars + Pizzicato + Clarinet!
            write_fugato_subject("harp", sp, 1, 0.66)
            sb.guitar_fingerstyle("steel_guitar", sp, vel=0.62, style="toccatina", step_beats=0.25, ring_mult=1.2)
            sb.guitar_fingerstyle("nylon_guitar", sp, vel=0.60, style="travis", step_beats=0.5, ring_mult=1.4)
            sb.note("pizzicato", b0, 0.4, sp.tenor_root(), 0.58)
            sb.note("pizzicato", b0 + 1.0, 0.4, sp.tenor_root() + P5, 0.54)
            sb.note("pizzicato", b0 + 2.0, 0.4, sp.tenor_root() + OCT, 0.58)
            if idx % 2 == 0:
                write_fugato_subject("clarinet", sp, 1, 0.62)
        elif idx < 19:
            # Stretto Climax (f): Full plucked consort + Strings + Piano + Brass accents!
            dyn = 0.74 if idx < 18 else 0.58
            sb.string_pad(sp, vel=dyn * 0.84, swell="sfz" if idx < 17 else "dim")
            sb.guitar_fingerstyle("steel_guitar", sp, vel=dyn + 0.08, style="toccatina", step_beats=0.25, ring_mult=1.25)
            sb.guitar_strum("nylon_guitar", b0, 1.8, sp.guitar_voicing(6), vel=dyn + 0.08, roll=0.04)
            if dur >= 5.5:
                sb.guitar_strum("nylon_guitar", b0 + 3.0, 2.2, sp.guitar_voicing(6), vel=dyn + 0.06, roll=0.04, upstroke=True)
            sb.piano_figuration(sp, vel=dyn * 0.82, style="scherzo", step_beats=0.5, use_pedal=False)
            if idx in (14, 15, 16):
                sb.note("french_horn", b0, dur - 1.2, sp.tenor_root() + P5, dyn * 0.88, swell="sfz", vibrato=0.14)
                sb.note("bassoon", b0, dur - 1.2, sp.bass_root(), dyn * 0.88, swell="arch")
                sb.note("timpani", b0, 0.9, sp.bass_root(), dyn * 0.76, trim_to_chord=False)
        else:
            # Clean decrescendo plucked open-5th landing (336..340)
            sb.guitar_strum("nylon_guitar", b0, 3.6, [-53, -22, 0, 31, 53], vel=0.46, roll=0.06)
            sb.guitar_strum("steel_guitar", b0 + 0.4, 3.2, [-53, -22, 0, 31, 53], vel=0.42, roll=0.06, upstroke=True)

    # =========================================================================
    # SECTION III (Beats 340..464, 2:50–4:15, 82 -> 92 BPM):
    #   EAST–WEST PLUCKED SHRUTI DIALOGUE
    #   Intimate chamber conversation between Western plucked strings (`nylon_guitar`,
    #   `steel_guitar`, `harp`) and Indian strings (`sitar`, `dotara`, `ektara`),
    #   contrasting two ragas separated by 1–2 shrutis (`12` vs `14`, `8` vs `9`,
    #   `35` vs `36`) that 12-TET collapses into identical notes!
    #   (ONLY `sitar`/`dotara`/`ektara` use gentle meend here; Western = 0 slide!)
    # =========================================================================
    # III.A (340..388, 82 -> 88 BPM): Shruti Pair 1 & 2 — `12` (7:6) vs `14` (6:5) AND `8` (10:9) vs `9` (9:8)!
    # Alternating 6-beat East call (Raga Septimal Kafi: Komal Ga=12, Komal Ni=43, Re=8)
    # and 6-beat West answer (5-Limit Kafi: Komal Ga=14, Komal Ni=45, Re=9) over Sa=C(0), Pa=G(31)!
    shruti_part_a = [
        (340.0, 346.0, C, "submin7", "III.A1 East Call: Septimal Ga=12 & Ni=43", "east_12"),
        (346.0, 352.0, C, "min7", "III.A2 West Answer: Pure 5-Limit Ga=14 & Ni=45 (SAME 12-TET NOTES!)", "west_14"),
        (352.0, 358.0, C, "sus2_m", "III.A3 East Call: Shuddha Re_1 = 8 (10:9)", "east_8"),
        (358.0, 364.0, C, "sus2", "III.A4 West Answer: Shuddha Re_2 = 9 (9:8) (SAME 12-TET D4!)", "west_9"),
        (364.0, 370.0, C, "submin7", "III.A5 Jugalbandi Intertwine on Septimal 12 & 43", "both_12"),
        (370.0, 376.0, C, "min7", "III.A6 Jugalbandi Intertwine on 5-Limit 14 & 45", "both_14"),
        (376.0, 382.0, C, "sus2_m", "III.A7 Jugalbandi Re_1 = 8", "both_8"),
        (382.0, 388.0, C, "sus2", "III.A8 Jugalbandi Re_2 = 9", "both_9"),
    ]
    for idx, (b0, b1, rpc, qual, lbl, mode_tag) in enumerate(shruti_part_a):
        sp = sb.add_span(b0, b1, rpc, qual, lbl)
        dyn = 0.34 + 0.02 * idx  # Intimate p-mp chamber dynamic for wide LRA!
        # Grounded Sa-Pa drone on Ektara & Cello (rock-solid C=0, zero bass wailing!)
        sb.note("ektara", b0, 2.8, pitch(C, 3), dyn + 0.04, meend_cents=20.0)
        sb.note("ektara", b0 + 3.0, 2.7, pitch(C, 3), dyn + 0.02, meend_cents=16.0)
        if idx % 2 == 0:
            sb.note("cello", b0, 5.5, pitch(C, 2), dyn * 0.90, swell="arch", vibrato=0.16)

        if mode_tag.startswith("east"):
            ga_or_re = EB_HARM if "12" in mode_tag else D_MINUS
            ni_or_dha = BB_HARM if "12" in mode_tag else A
            sb.phrase("sitar", [
                (b0 + 0.0, 1.3, pitch(C, 4), dyn + 0.12),
                (b0 + 1.5, 1.8, pitch(ga_or_re, 4), dyn + 0.16),
                (b0 + 3.5, 1.2, pitch(G, 3), dyn + 0.10),
                (b0 + 4.8, 1.0, pitch(ni_or_dha, 3), dyn + 0.14),
            ], indian_meend=True)
            sb.phrase("dotara", [
                (b0 + 0.5, 0.8, pitch(G, 3), dyn + 0.08),
                (b0 + 2.0, 1.2, pitch(ga_or_re, 4), dyn + 0.10),
                (b0 + 4.0, 1.4, pitch(C, 4), dyn + 0.08),
            ], indian_meend=True)
            # Soft Western plucked halo on Sa & Pa
            sb.note("nylon_guitar", b0 + 0.25, 2.4, pitch(G, 3), dyn * 0.85)
            sb.note("steel_guitar", b0 + 3.25, 2.3, pitch(C, 4), dyn * 0.85)

        elif mode_tag.startswith("west"):
            ga_or_re = EB if "14" in mode_tag else D
            ni_or_dha = BB_JUST if "14" in mode_tag else A
            # Western guitars + harp answer with razor-sharp discrete frets (`slide_from_cents = 0`)!
            sb.guitar_strum("nylon_guitar", b0, 2.7, sp.guitar_voicing(5), vel=dyn + 0.10, roll=0.05)
            sb.phrase("steel_guitar", [
                (b0 + 0.25, 1.1, pitch(C, 4), dyn + 0.12),
                (b0 + 1.5, 1.8, pitch(ga_or_re, 4), dyn + 0.16),
                (b0 + 3.5, 1.1, pitch(G, 4), dyn + 0.12),
                (b0 + 4.75, 1.0, pitch(ni_or_dha, 4), dyn + 0.14),
            ])
            sb.harp_sweep(sp, b0 + 0.5, -53, 67, vel=dyn + 0.06, spacing=0.24, note_dur=2.2, max_notes=6, with_pedal=True)

        else:
            # Simultaneous East-West Jugalbandi trading 1.5-beat phrases!
            ga_st = EB_HARM if "12" in mode_tag else (EB if "14" in mode_tag else (D_MINUS if "8" in mode_tag else D))
            sb.guitar_fingerstyle("nylon_guitar", sp, vel=dyn + 0.08, style="baroque", step_beats=0.5, ring_mult=1.6)
            sb.phrase("sitar", [
                (b0 + 0.0, 1.4, pitch(ga_st, 4), dyn + 0.14),
                (b0 + 1.5, 1.3, pitch(C, 4), dyn + 0.10),
            ], indian_meend=True)
            sb.phrase("steel_guitar", [
                (b0 + 3.0, 1.4, pitch(ga_st, 4), dyn + 0.14),
                (b0 + 4.5, 1.2, pitch(G, 4), dyn + 0.12),
            ])
            sb.note("dotara", b0 + 2.0, 0.9, pitch(G, 3), dyn + 0.08)

    # III.B (388..436, 88 -> 92 BPM): Shruti Pair 3 — Komal Dha `35` (128:81) vs `36` (8:5)
    # Harmonized cleanly as `F pyth_min [22, 35, 0]` vs `F min [22, 36, 0]` (BOTH = Fm in 12-TET!)
    shruti_part_b = [
        (388.0, 394.0, F, "pyth_min", "III.B1 East Bhairavi Call: Komal Dha_1 = 35 (128:81)", 35),
        (394.0, 400.0, F, "min", "III.B2 West Answer: Komal Dha_2 = 36 (8:5) (BOTH = Ab4 in 12-TET!)", 36),
        (400.0, 406.0, F, "pyth_min", "III.B3 East-West Echo on Shruti 35", 35),
        (406.0, 412.0, F, "min", "III.B4 East-West Echo on Shruti 36", 36),
        (412.0, 418.0, C, "dom9", "III.B5 Radiant Yaman/Khamaj Septimal C9 Bloom", 43),
        (418.0, 424.0, F, "dom9", "III.B6 Septimal F9 (Eb_harm=12, A4=440Hz)", 12),
        (424.0, 430.0, C, "sus2_m", "III.B7 Shruti Re_1 (8) Recall", 8),
        (430.0, 436.0, C, "add9", "III.B8 Pure 9:8 Re_2 (9) & 5:4 Ga (17) Resolution", 17),
    ]
    for idx, (b0, b1, rpc, qual, lbl, feat_pc) in enumerate(shruti_part_b):
        sp = sb.add_span(b0, b1, rpc, qual, lbl)
        dyn = 0.44 + 0.02 * (idx if idx < 5 else 8 - idx)
        sb.guitar_fingerstyle("nylon_guitar", sp, vel=dyn + 0.08, style="baroque", step_beats=0.5, ring_mult=1.6)
        sb.guitar_fingerstyle("steel_guitar", sp, vel=dyn + 0.06, style="travis", step_beats=0.5, ring_mult=1.5)
        sb.note("ektara", b0, 2.7, sp.tenor_root(), dyn, meend_cents=20.0)
        sb.note("dotara", b0 + 1.5, 1.1, sp.tenor_root() + P5, dyn + 0.04)
        sb.note("dotara", b0 + 4.5, 1.1, sp.tenor_root(), dyn + 0.02)
        if idx < 4:
            # Highlight 35 vs 36 directly in Sitar (Oct 3/4) answered by English Horn & Harp (zero Western slide!)
            sitar_st = feat_pc - OCT if feat_pc > 31 else feat_pc
            sb.phrase("sitar", [
                (b0 + 0.2, 1.6, sitar_st, dyn + 0.14),
                (b0 + 2.0, 1.2, pitch(C, 4), dyn + 0.10),
            ], indian_meend=True)
            sb.phrase("english_horn", [
                (b0 + 3.2, 2.4, feat_pc, dyn + 0.12),
            ], vibrato=0.22)
        else:
            sb.string_pad(sp, vel=dyn * 0.76, swell="arch")
            sb.harp_sweep(sp, b0 + 0.3, -53, 75, vel=dyn + 0.08, spacing=0.22, note_dur=2.4, max_notes=7, with_pedal=True)

    # III.C (436..464, 90 -> 84 BPM): Sparkling Plucked Sawal-Jawab Coda & Hushed pp Cadence
    sb.add_span(436.0, 444.0, C, "maj", "III.C1 East-West Plucked Shruti Cascade", free_microtonal=True)
    sp_3c2 = sb.add_span(444.0, 452.0, F, "add9", "III.C2 Serene F add9")
    sp_3c3 = sb.add_span(452.0, 458.0, G, "sus4", "III.C3 Suspended G sus4")
    sp_3c4 = sb.add_span(458.0, 464.0, C, "open5", "III.C4 Hushed pp Sa-Pa Stillness before Passacaglia")

    # Interlocking shruti cascade across {8,9,10}, {12,13,14}, {35,36}, {43,44,45}!
    sb.campanella_cascade(
        436.0, 443.8,
        [[8, 9, 10], [16, 17, 18], [30, 31, 32], [43, 44, 45]],
        vel=0.48,
        step_beats=0.25,
        include_harp=True,
    )
    for sp_c, v_c in ((sp_3c2, 0.42), (sp_3c3, 0.36), (sp_3c4, 0.30)):
        sb.guitar_fingerstyle("nylon_guitar", sp_c, vel=v_c + 0.05, style="glass", step_beats=0.75, ring_mult=1.9)
        sb.guitar_strum("steel_guitar", sp_c.start, (sp_c.end - sp_c.start) - 0.3, sp_c.guitar_voicing(5), vel=v_c + 0.04, roll=0.06)
        sb.note("ektara", sp_c.start + 0.2, 2.8, sp_c.tenor_root(), v_c, meend_cents=18.0)

    # =========================================================================
    # SECTION IV (Beats 464..624, 4:15–5:45, 98 -> 116 BPM):
    #   THE SYNTONIC COMMA PUMP (`C -> Am -> Dm -> G -> C` PASSACAGLIA)
    #   5 Variations climbing k = -2 -> -1 -> 0 -> +1 -> +2 -> +3 (+113.2c total!):
    #     1. C(k)    [k, 17+k, 31+k]
    #     2. Am(k)   [39+k, k, 17+k]          (holds exact C=k AND E=17+k!)
    #     3. Dm7(k)  [9+k, 23+k, 40+k, k]     (holds exact C=k as 16:9 7th!)
    #     4. G7+(k)  [32+k, 49+k, 10+k, 23+k] (holds exact F+=23+k, and resolves
    #                                          by pure P5 & +/-5 semitones to C(k+1)!)
    #   Driven by rhythmic fingerstyle `steel_guitar` + `nylon_guitar` patterns and
    #   building chamber orchestra from `p` (Var 1) to `ff` (Var 5 & Summit k=+3)!
    # =========================================================================
    for var_idx, k in enumerate([-2, -1, 0, +1, +2]):
        base_b = 464.0 + var_idx * 24.0  # 24 beats per variation (6 beats per chord!)
        sp_C = sb.add_span(base_b + 0.0, base_b + 6.0, C + k, "maj", f"IV.Var{var_idx+1} C(k={k:+d})")
        sp_Am = sb.add_span(base_b + 6.0, base_b + 12.0, A + k, "min", f"IV.Var{var_idx+1} Am(k={k:+d})")
        sp_Dm = sb.add_span(base_b + 12.0, base_b + 18.0, D + k, "min7_p", f"IV.Var{var_idx+1} Dm7(k={k:+d}, holds C)")
        sp_G = sb.add_span(base_b + 18.0, base_b + 24.0, G + k + 1, "dom7_p", f"IV.Var{var_idx+1} G7(k={k+1:+d}, lifts to C{k+1:+d})")
        var_spans = [sp_C, sp_Am, sp_Dm, sp_G]

        # Progressive dynamic build across the 5 variations (0.38 -> 0.84) for rich orchestral LRA!
        dyn_base = [0.36, 0.48, 0.60, 0.72, 0.82][var_idx]

        for si, sp in enumerate(var_spans):
            dyn = dyn_base + 0.02 * si
            # Continuous rhythmic fingerstyle Dual Guitars are the engine of every variation!
            sb.guitar_fingerstyle(
                "steel_guitar",
                sp,
                vel=dyn + 0.07,
                style="travis" if var_idx < 3 else "toccatina",
                step_beats=0.5 if var_idx < 2 else 0.25,
                ring_mult=1.55,
            )
            sb.guitar_fingerstyle(
                "nylon_guitar",
                sp,
                vel=dyn + 0.06,
                style="baroque",
                step_beats=0.5,
                ring_mult=1.65,
            )
            # Accentuated beat-1 6-string strum on Nylon Guitar from Var 2 onward
            if var_idx >= 1:
                sb.guitar_strum("nylon_guitar", sp.start, 1.8, sp.guitar_voicing(5), vel=dyn + 0.08, roll=0.04)

            br = sp.bass_root(-106, -54)
            if var_idx == 0:
                # Var 1 (k=-2 -> -1, p): Intimate Dual Guitars + Pizzicato walking bass
                sb.note("pizzicato", sp.start, 0.45, sp.tenor_root(), dyn + 0.04)
                sb.note("pizzicato", sp.start + 3.0, 0.45, sp.tenor_root() + P5, dyn + 0.02)
            elif var_idx == 1:
                # Var 2 (k=-1 -> 0, mp): Add Singing Cello & Solo Viola holding exact common tones!
                sb.note("cello", sp.start, 5.4, br + OCT, dyn + 0.06, swell="arch", vibrato=0.22)
                sb.harp_sweep(sp, sp.start + 0.5, -53, 70, vel=dyn + 0.04, spacing=0.25, note_dur=2.2, max_notes=6)
            elif var_idx == 2:
                # Var 3 (k=0 -> +1, mf): Add Woodwinds, Harp & Warm Strings
                sb.string_pad(sp, vel=dyn * 0.82, swell="arch")
                sb.piano_figuration(sp, vel=dyn * 0.80, style="triplet", step_beats=0.5)
                if si != 2:
                    sb.note("bassoon", sp.start, 4.8, br, dyn * 0.90, swell="arch")
            elif var_idx == 3:
                # Var 4 (k=+1 -> +2, f): Add Noble French Horn, Dotara & Driving Strings
                sb.string_pad(sp, vel=dyn * 0.88, swell="cresc")
                sb.piano_figuration(sp, vel=dyn * 0.84, style="scherzo", step_beats=0.5, use_pedal=False)
                sb.note("dotara", sp.start, 0.6, sp.tenor_root() + OCT, dyn * 0.90)
                sb.note("dotara", sp.start + 3.0, 0.6, sp.tenor_root() + P5, dyn * 0.88)
                if si != 1:
                    sb.note("french_horn", sp.start + 0.2, 4.8, sp.tenor_root() + P5, dyn * 0.90, swell="arch", vibrato=0.16)
                    sb.note("bassoon", sp.start, 4.8, br, dyn * 0.90, swell="arch")
            else:
                # Var 5 (k=+2 -> +3, ff): Full Orchestra + Trombone + Tremolo + Timpani Build!
                sb.string_pad(sp, vel=dyn * 0.92, track_id="string_ensemble", swell="cresc")
                sb.string_pad(sp, vel=dyn * 0.82, track_id="tremolo_strings", swell="cresc")
                sb.piano_figuration(sp, vel=dyn * 0.88, style="grand", step_beats=0.5)
                if si != 2:
                    sb.note("trombone", sp.start, 4.8, br + OCT, dyn * 0.88, swell="cresc")
                    sb.note("bassoon", sp.start, 4.8, br, dyn * 0.90, swell="cresc")
                sb.note("timpani", sp.start, 1.1, br, dyn * 0.82, trim_to_chord=False)
                sb.note("timpani", sp.start + 3.0, 1.1, br, dyn * 0.78, trim_to_chord=False)

        # Spotlight the EXACT common-tone chain across C -> Am -> Dm7 -> G7 -> C+ in solo winds/strings!
        if var_idx >= 1:
            lead_inst = ["viola", "clarinet", "english_horn", "clarinet"][var_idx - 1]
            oct_l = 4 if lead_inst != "clarinet" or var_idx == 2 else 5
            sb.phrase(lead_inst, [
                (base_b + 0.2, 5.2, pitch(C, oct_l, k), dyn_base + 0.10),       # C(k) root
                (base_b + 6.0, 5.0, pitch(C, oct_l, k), dyn_base + 0.12),       # Exact common tone in Am(k)!
                # Clean 1.0b breath 11.0..12.0!
                (base_b + 12.0, 5.2, pitch(C, oct_l, k), dyn_base + 0.14),      # Exact common tone 7th in Dm7(k)!
                (base_b + 18.0, 2.8, pitch(F, oct_l - (1 if oct_l == 5 else 0), k + 1), dyn_base + 0.14),  # Common tone F+!
                (base_b + 21.0, 2.5, pitch(B, oct_l - 1, k + 1), dyn_base + 0.16),  # Leading tone B+ -> C(k+1)!
            ], vibrato=0.20)

    # Summit Arrival at k = +3 (584..596): Blazing C+++ Major ([3, 20, 34] -> C# Major in 12-TET!!)
    sp_summit = sb.add_span(584.0, 596.0, C + 3, "add9", "IV.Summit Blinding C+++(k=+3 -> C# in 12-TET!)")
    sb.timpani_roll(581.0, 2.85, pitch(G, 2, 3), 0.62, 0.86, spacing=0.25)
    sb.string_pad(sp_summit, vel=0.88, track_id="string_ensemble", swell="sfz")
    sb.string_pad(sp_summit, vel=0.78, track_id="tremolo_strings", swell="dim")
    sb.guitar_strum("steel_guitar", 584.0, 5.5, sp_summit.guitar_voicing(6), vel=0.90, roll=0.04)
    sb.guitar_strum("nylon_guitar", 584.2, 5.3, sp_summit.guitar_voicing(6), vel=0.88, roll=0.045, upstroke=True)
    sb.guitar_fingerstyle("steel_guitar", ChordSpan(590.0, 596.0, C + 3, "add9"), vel=0.82, style="toccatina", step_beats=0.25)
    sb.harp_sweep(sp_summit, 584.3, -50, 87, vel=0.88, spacing=0.15, note_dur=3.5, max_notes=9, with_pedal=True)
    sb.note("trombone", 584.0, 6.5, pitch(C, 3, 3), 0.86, swell="sfz")
    sb.note("french_horn", 584.0, 6.5, pitch(G, 3, 3), 0.88, swell="sfz", vibrato=0.16)
    sb.note("bassoon", 584.0, 6.5, sp_summit.bass_root(), 0.86, swell="dim")
    sb.note("timpani", 584.0, 1.8, sp_summit.bass_root(), 0.86, trim_to_chord=False)
    sb.phrase("clarinet", [
        (584.0, 5.2, pitch(E, 5, 3), 0.88),
        (590.2, 5.0, pitch(D, 5, 3), 0.78),
    ], vibrato=0.22, default_swell="dim")

    # Downward Comma Return (596..624): 3 crisp downward comma steps (+3 -> +2 -> +1 -> 0) into Scherzo!
    down_return = [
        (596.0, 602.0, F + 3, "maj", "IV.Ret1 F+++(25)"),
        (602.0, 608.0, G + 2, "dom7", "IV.Ret2 G++7 -> C++"),
        (608.0, 614.0, F + 2, "maj", "IV.Ret3 F++(24)"),
        (614.0, 620.0, G, "dom7", "IV.Ret4 G7(0)"),
        (620.0, 624.0, C, "open5", "IV.Ret5 Crisp Plucked C5 Launchpad"),
    ]
    for idx, (b0, b1, rpc, qual, lbl) in enumerate(down_return):
        sp = sb.add_span(b0, b1, rpc, qual, lbl)
        v = 0.70 - 0.08 * idx
        sb.guitar_fingerstyle("nylon_guitar", sp, vel=v + 0.06, style="baroque", step_beats=0.5, ring_mult=1.5)
        sb.guitar_strum("steel_guitar", b0, (b1 - b0) * 0.65, sp.guitar_voicing(5), vel=v + 0.06, roll=0.045)
        if idx < 4:
            sb.string_pad(sp, vel=v * 0.82, swell="dim")
            sb.note("cello", b0, (b1 - b0) - 0.5, sp.bass_root() + OCT, v + 0.04, swell="dim", vibrato=0.18)

    # =========================================================================
    # SECTION V (Beats 624..816, 5:45–7:15, 130 BPM):
    #   SCHERZO OF THE DIESIS SHEAR (`Ab++ Major [38, 2, 16]` -> 12-TET `A minor`!)
    #   FIRST spotlights the pure `17`-step major-third diesis chains AND the
    #   blazing `[38, 2, 16]` `Ab++ Major` chord on **EXPOSED RINGING `steel_guitar`
    #   + `nylon_guitar` + `harp`** (`[-68, -37, -15, 2, 16, 38]` = pure 4:5:6 Major
    #   in 53-EDO, yet `[A2, E3, A3, C4, E4, A4]` = OPEN A MINOR in 12-TET!!)
    #   BEFORE brass and strings answer!
    # =========================================================================
    # V.A (624..688): EXPOSED GUITAR + HARP DIESIS SHEAR SPOTLIGHT -> ORCHESTRAL ANSWER!
    # Phrase 1 (624..656): Purely Plucked Exposed Diesis Chain!
    #   C(0) [0,17,31] -> Ab(36) [36,0,14] -> E+(19) [19,36,50] -> C++(2) [2,19,33] -> Ab++(38) [38,2,16]!!
    exposed_diesis = [
        (624.0, 630.0, C, "maj", "V.A1 Exposed Guitar C Major [0,17,31]"),
        (630.0, 636.0, AB, "maj", "V.A2 Exposed Guitar Ab Major [36,0,14] (holds C=0!)"),
        (636.0, 642.0, 19, "maj", "V.A3 Exposed Guitar E+ Major [19,36,50] (holds Ab=36!)"),
        (642.0, 648.0, DIESIS, "maj", "V.A4 Exposed Guitar C++ Major [2,19,33] (+45.3c Diesis!)"),
        # 8 FULL BEATS (~3.7s) OF COMPLETELY EXPOSED RINGING [38, 2, 16] Ab++ MAJOR GUITAR CHORD!
        (648.0, 656.0, AB_DIESIS, "maj", "V.A5 EXPOSED GUITAR [38,2,16] Ab++ MAJOR -> 12-TET A MINOR!!"),
    ]
    ab_diesis_guitar_6 = [-68, -37, -15, 2, 16, 38]  # Exact [A2, E3, A3, C4, E4, A4] in 12-TET!

    for idx, (b0, b1, rpc, qual, lbl) in enumerate(exposed_diesis):
        sp = sb.add_span(b0, b1, rpc, qual, lbl)
        dur = b1 - b0
        gv = ab_diesis_guitar_6 if rpc == AB_DIESIS else sp.guitar_voicing(6)
        v_g = 0.74 + 0.03 * idx
        # Exposed razor-sharp ringing chords on Steel Guitar, Nylon Guitar & Harp (NO winds/strings!)
        sb.guitar_strum("steel_guitar", b0, min(3.8, dur - 0.25), gv, vel=v_g, roll=0.045, exact_step=(rpc == AB_DIESIS))
        sb.guitar_strum("nylon_guitar", b0 + 0.25, min(3.6, dur - 0.50), gv, vel=v_g - 0.02, roll=0.045, upstroke=True, exact_step=(rpc == AB_DIESIS))
        if dur >= 7.5:
            # Second ringing strum on [38, 2, 16] so A/B listeners hear it strike twice in pure isolation!
            sb.guitar_strum("nylon_guitar", b0 + 4.0, 3.7, gv, vel=v_g + 0.02, roll=0.04, exact_step=True)
            sb.guitar_strum("steel_guitar", b0 + 4.25, 3.45, gv, vel=v_g + 0.02, roll=0.04, upstroke=True, exact_step=True)
            sb.chord("harp", b0, 3.6, [-15, 2, 16, 38, 55], vel=0.72, roll=0.06, exact_step=True)
            sb.chord("harp", b0 + 4.0, 3.6, [-15, 2, 16, 38, 55], vel=0.74, roll=0.06, exact_step=True)
        else:
            sb.harp_sweep(sp, b0 + 0.4, -53, 75, vel=0.68, spacing=0.18, note_dur=2.4, max_notes=6, with_pedal=True)

    # Phrase 2 (656..696): Ascending `+17` Major-Third Diesis Chain (`C -> E -> G#` & `C++++ -> E++ -> [38,2,16] Ab++`)
    # Answered by Heroic Brass, Strings & Timpani!
    scherzo_tutti = [
        (656.0, 662.0, C, "maj", "V.A6 Tutti C(0) [0,17,31]"),
        (662.0, 668.0, E, "maj", "V.A7 Tutti E(17) [17,34,48] (+17 pure M3, holds E=17!)"),
        (668.0, 674.0, GS_EAGLE, "maj", "V.A8 Tutti G#(34) [34,51,12] (+17 pure M3, holds G#=34!)"),
        (674.0, 680.0, 4, "maj", "V.A9 Tutti C++++(4) [4,21,35]"),
        (680.0, 686.0, 21, "maj", "V.A10 Tutti E++(21) [21,38,52] (+17 pure M3, shears to F Major in 12-TET!)"),
        (686.0, 696.0, AB_DIESIS, "maj", "V.A11 Tutti Answer on [38,2,16] Ab++ Major -> 12-TET A minor!"),
    ]
    for idx, (b0, b1, rpc, qual, lbl) in enumerate(scherzo_tutti):
        sp = sb.add_span(b0, b1, rpc, qual, lbl)
        dur = b1 - b0
        dyn = 0.74 + 0.025 * idx
        gv = ab_diesis_guitar_6 if rpc == AB_DIESIS else sp.guitar_voicing(6)
        sb.guitar_fingerstyle("steel_guitar", sp, vel=dyn + 0.06, style="scherzo", step_beats=0.5, ring_mult=1.35)
        sb.guitar_strum("nylon_guitar", b0, 2.6, gv, vel=dyn + 0.06, roll=0.04, exact_step=(rpc == AB_DIESIS))
        if dur >= 8.0:
            sb.guitar_strum("nylon_guitar", b0 + 4.0, 3.6, gv, vel=dyn + 0.06, roll=0.04, upstroke=True, exact_step=True)
        sb.string_pad(sp, vel=dyn * 0.88, swell="sfz")
        sb.piano_figuration(sp, vel=dyn * 0.84, style="scherzo", step_beats=0.5, use_pedal=False)
        if idx % 2 == 1:
            sb.note("french_horn", b0, min(4.8, dur - 1.1), sp.tenor_root() + P5, dyn * 0.90, swell="sfz", vibrato=0.14)
            sb.note("trombone", b0, min(4.8, dur - 1.1), sp.bass_root() + OCT, dyn * 0.86, swell="sfz")
        else:
            sb.note("bassoon", b0, min(4.8, dur - 1.1), sp.bass_root(), dyn * 0.88, swell="arch")
        sb.note("timpani", b0, 1.0, sp.bass_root(), dyn * 0.80, trim_to_chord=False)

    # V.B (696..760): Antiphonal Diesis-Echo Trio — Exposed Guitars (`Ab++ [38,2,16]` vs `A min [39,0,17]`)!
    # Direct back-to-back comparison: Bar A = `Ab++ Major [38, 2, 16]` vs Bar B = `A minor [39, 0, 17]`!
    # In 53-EDO: radiant Major triad vs poignant Minor triad!
    # In 12-TET: BOTH BARS QUANTIZE TO THE EXACT SAME A MINOR TRIAD [A, C, E]!!
    trio_pairs = [
        (696.0, 704.0, AB_DIESIS, "maj", "V.B1 Exposed Guitar Ab++ Major [38,2,16] (-> Am in 12-TET!)", True),
        (704.0, 712.0, A, "min", "V.B2 Exposed Guitar True A minor [39,0,17] (IDENTICAL in 12-TET!)", False),
        (712.0, 720.0, 21, "maj", "V.B3 Exposed Guitar E++ Major [21,38,52] (-> F Major in 12-TET!)", True),
        (720.0, 728.0, F, "maj", "V.B4 Exposed Guitar True F Major [22,39,0] (IDENTICAL in 12-TET!)", False),
        (728.0, 736.0, AB_DIESIS, "maj", "V.B5 Guitar + Winds Ab++ Major [38,2,16]", True),
        (736.0, 744.0, A, "min7", "V.B6 Guitar + Winds True Am7 [39,0,17,31]", False),
        (744.0, 752.0, C + 2, "maj", "V.B7 C++(2) Diesis Bridge", True),
        (752.0, 760.0, C, "maj", "V.B8 C(0) Home Plane Echo (Identical in 12-TET!)", False),
    ]
    for idx, (b0, b1, rpc, qual, lbl, is_diesis_side) in enumerate(trio_pairs):
        sp = sb.add_span(b0, b1, rpc, qual, lbl)
        v_t = 0.56 if is_diesis_side else 0.44  # Clear dynamic terrace!
        gv = ab_diesis_guitar_6 if rpc == AB_DIESIS else ([-67, -36, -14, 0, 17, 39] if rpc == A and qual == "min" else sp.guitar_voicing(6))
        sb.guitar_strum("steel_guitar", b0, 3.6, gv, vel=v_t + 0.12, roll=0.045, exact_step=(rpc in (AB_DIESIS, A) and qual in ("maj", "min")))
        sb.guitar_fingerstyle("nylon_guitar", sp, vel=v_t + 0.08, style="baroque", step_beats=0.5, ring_mult=1.6)
        sb.harp_sweep(sp, b0 + 2.0, -53, 75, vel=v_t + 0.06, spacing=0.20, note_dur=2.2, max_notes=6)
        if idx >= 4:
            r = sp.tenor_root()
            th = sp.third_offset()
            sb.phrase("clarinet" if is_diesis_side else "viola", [
                (b0 + 0.5, 2.8, r + OCT + th, v_t + 0.12),
                (b0 + 3.8, 3.4, r + OCT + P5, v_t + 0.10),
            ], vibrato=0.18)

    # V.C (760..816): Brisk Scherzo Reprise & Graceful Decrescendo into the Adagio (130 -> 96 BPM)
    s5_reprise = [
        (760.0, 768.0, C, "maj", "V.C1 Scherzo Reprise C(0)"),
        (768.0, 776.0, AB, "maj", "V.C2 Ab(36)"),
        (776.0, 784.0, 19, "maj", "V.C3 E+(19)"),
        (784.0, 792.0, DIESIS, "add9", "V.C4 C++(2) add9 Climax"),
        (792.0, 800.0, F + 2, "maj", "V.C5 IV++(24)"),
        (800.0, 808.0, G, "dom9", "V.C6 Septimal G9 Transition"),
        (808.0, 816.0, C, "submin7", "V.C7 Hushed Subminor Portal into Glass Adagio"),
    ]
    for idx, (b0, b1, rpc, qual, lbl) in enumerate(s5_reprise):
        sp = sb.add_span(b0, b1, rpc, qual, lbl)
        dyn = [0.74, 0.78, 0.82, 0.84, 0.66, 0.48, 0.34][idx]
        sb.guitar_fingerstyle("steel_guitar", sp, vel=dyn + 0.06, style="scherzo" if idx < 5 else "glass", step_beats=0.5, ring_mult=1.5)
        sb.guitar_fingerstyle("nylon_guitar", sp, vel=dyn + 0.04, style="baroque", step_beats=0.5, ring_mult=1.6)
        sb.string_pad(sp, vel=dyn * 0.86, swell="sfz" if idx < 4 else "dim")
        if idx < 4:
            sb.piano_figuration(sp, vel=dyn * 0.82, style="scherzo", step_beats=0.5, use_pedal=False)
            sb.note("timpani", b0, 1.0, sp.bass_root(), dyn * 0.78, trim_to_chord=False)
        if idx in (1, 2, 3):
            sb.note("french_horn", b0 + 0.2, 6.4, sp.tenor_root() + P5, dyn * 0.88, swell="sfz", vibrato=0.14)

    # =========================================================================
    # SECTION VI (Beats 816..904, 7:15–8:35, 64 BPM):
    #   ADAGIO OF GLASS HARMONICS (7-LIMIT & 11-LIMIT RESONANCE)
    #   Hushed pp-mp (`vel 0.25..0.46`) oasis of crystal-pure `4:5:6:7` (`dom7`),
    #   `7:6` (`submin7`), and `8:10:11:12:14` (`overtone11`, step 24 = 11:8!)
    #   chords ringing on bell-like `nylon_guitar`, `steel_guitar`, `harp`,
    #   `cello`, and `english_horn` — ZERO portamento bends (`slide_from_cents=0`)!
    # =========================================================================
    adagio_plan = [
        (816.0, 824.0, F, "maj7", "VI.1 Glass F maj7 (A4=440Hz, pp)"),
        (824.0, 832.0, F, "dom9", "VI.2 Pure 4:5:6:7:9 Septimal F9 (Eb_harm=12)"),
        (832.0, 840.0, F, "overtone11", "VI.3 Pure 11-Limit Overtone F11 (8:10:11:12:14, 11:8 = step 46)"),
        (840.0, 848.0, C, "submin7", "VI.4 Pure 7:6 & 7:4 Subminor C submin7 [0,12,31,43]"),
        (848.0, 856.0, C, "dom9", "VI.5 Pure 4:5:6:7:9 Septimal C9 [0,9,17,31,43]"),
        (856.0, 864.0, C, "overtone11", "VI.6 Pure 11-Limit Overtone C11 [0,17,24,31,43] (11:8 = step 24!)"),
        (864.0, 872.0, BB_HARM, "add9", "VI.7 Luminous Septimal-Root Bb_harm(43) add9"),
        (872.0, 880.0, G, "submin7", "VI.8 Poignant 7:6 G submin7 [31,43,9,21]"),
        (880.0, 888.0, D_MINUS, "min_dm", "VI.9 Gentle Awakening Dm-"),
        (888.0, 896.0, C, "dom7", "VI.10 Expectant Pure 4:5:6:7 C7"),
        (896.0, 904.0, C, "dom9", "VI.11 Shimmering C9 Herald into Finale"),
    ]
    for idx, (b0, b1, rpc, qual, lbl) in enumerate(adagio_plan):
        sp = sb.add_span(b0, b1, rpc, qual, lbl)
        dur = b1 - b0
        # Hushed ppp-mp across beats 816..888 (0.26..0.38), gently blooming 888..904 (0.44..0.54)
        v = [0.27, 0.30, 0.33, 0.28, 0.32, 0.35, 0.34, 0.30, 0.38, 0.46, 0.54][idx]

        # Exposed bell-pure Nylon Guitar + Steel Guitar chords & upper-register bell harmonics!
        gv = sp.guitar_voicing(6)
        sb.guitar_strum("nylon_guitar", b0, dur * 0.48, gv, vel=v + 0.08, roll=0.08)
        sb.guitar_fingerstyle("steel_guitar", sp, vel=v + 0.06, style="glass", step_beats=1.0, ring_mult=1.85)
        if idx < 8:
            # High crystalline artificial-harmonic bell notes on Nylon Guitar in second half of bar
            r = sp.tenor_root()
            th = sp.third_offset()
            harm_top = min(68, r + 2 * OCT + (UNDEC_11 - OCT if qual == "overtone11" else 0))
            sb.note("nylon_guitar", b0 + 4.0, 3.6, min(68, r + OCT + th), v + 0.09)
            sb.note("steel_guitar", b0 + 5.0, 2.7, harm_top, v + 0.08)

        sb.harp_sweep(sp, b0 + 0.5, -53, 92, vel=v + 0.08, spacing=0.35, note_dur=3.8, ascending=(idx % 2 == 0), max_notes=7, with_pedal=True)
        sb.string_pad(sp, vel=v * 0.85, swell="arch" if idx < 9 else "cresc", trim_tail=0.20)
        sb.note("cello", b0 + 0.1, dur - 0.8, sp.bass_root(-106, -54) + OCT, v + 0.06, swell="arch", vibrato=0.18)
        if idx in (0, 2, 4, 6):
            sb.note("bassoon", b0 + 0.2, 6.2, sp.bass_root(-106, -54), v + 0.04, swell="arch")

    # Intimate singing English Horn & Clarinet (zero portamento bends; pure interval lock!)
    sb.phrase("english_horn", [
        (817.0, 5.8, pitch(A, 4), 0.34),         # Pure 5:4 (440Hz)
        # Breath
        (825.0, 5.8, pitch(EB_HARM, 4), 0.36),   # Pure 7:4 of F!
        # Breath
        (833.0, 5.8, F + UNDEC_11, 0.38),        # Pure 11:8 of F (step 46)!
        # Breath
        (841.0, 5.8, pitch(EB_HARM, 4), 0.34),   # Pure 7:6 of C (step 12)!
        # Breath
        (857.0, 5.8, UNDEC_11, 0.40),            # Pure 11:8 of C (step 24)!
        # Breath
        (873.0, 5.8, 21, 0.36),                  # Pure 7:4 of G!
    ], vibrato=0.20)

    sb.phrase("clarinet", [
        (849.0, 5.8, pitch(BB_HARM, 4), 0.38),   # Pure 7:4 of C!
        # Breath
        (865.0, 5.8, 43 + M3, 0.40),             # Pure 5:4 above Bb_harm (step 60 = D-5)!
        # Breath
        (881.0, 5.8, pitch(A, 4), 0.44),
        (889.0, 5.8, pitch(BB_HARM, 4), 0.50),
        (897.0, 5.8, pitch(D, 5), 0.58),
    ], vibrato=0.18)

    # =========================================================================
    # SECTION VII (Beats 904..1052, 8:35–10:00, 116 -> 126 -> 68 BPM):
    #   FINALE — THE 53-TONE CONTINUUM & CATHEDRAL ORGAN APOTHEOSIS
    #   VII.A (904..960, 116->126 BPM): Virtuosic Dual-Guitar + Harp Perpetuum Mobile
    #   VII.B (960..1016, 126->120 BPM): Cathedral Pipe Organ Entrance (0 notes prior!)
    #                                    + Full 19-Track Symphonic Apotheosis (ff!)
    #   VII.C (1016..1052, 120->68 BPM): Serene Plagal Coda & Exposed Dual-Guitar
    #                                    4:5:6 F Major Bell Stillness (ppp, ~600s!)
    # =========================================================================
    # VII.A (904..960): Virtuosic Dual-Guitar & Plucked Consort Synthesis
    s7_virtuoso = [
        (904.0, 910.0, F, "add9", "VII.A1 Dual-Guitar Perpetuum Launch F add9", False),
        (910.0, 916.0, C, "dom9", "VII.A2 Septimal C9", False),
        (916.0, 920.0, F, "maj", "VII.A3 Finale Campanella Recall on F/A(440Hz)", True),
        (920.0, 926.0, D, "min7", "VII.A4 Dm7", False),
        (926.0, 932.0, BB, "add9", "VII.A5 Bb add9", False),
        (932.0, 938.0, G, "dom9", "VII.A6 G9", False),
        (938.0, 944.0, AB_DIESIS, "maj", "VII.A7 Diesis Recall Ab++ Major [38,2,16]", False),
        (944.0, 950.0, C, "add9", "VII.A8 Eagle/Diesis Return to C add9", False),
        (950.0, 955.0, C, "dom7", "VII.A9 Building C7", False),
        (955.0, 960.0, C, "dom9", "VII.A10 Blazing Septimal C9 Herald to Cathedral Organ!", False),
    ]
    for idx, (b0, b1, rpc, qual, lbl, is_free) in enumerate(s7_virtuoso):
        sp = sb.add_span(b0, b1, rpc, qual, lbl, free_microtonal=is_free)
        dur = b1 - b0
        if is_free:
            sb.campanella_cascade(
                b0, b1 - 0.12,
                [[21, 22, 23], [38, 39, 40, 41], [52, 53, 54], [65, 66, 67]],
                vel=0.74,
                step_beats=0.25,
                include_harp=True,
                lead_steel=True,
            )
            continue
        dyn = 0.66 + 0.022 * idx
        gv = ab_diesis_guitar_6 if rpc == AB_DIESIS else sp.guitar_voicing(6)
        sb.guitar_fingerstyle("steel_guitar", sp, vel=dyn + 0.08, style="toccatina", step_beats=0.25, ring_mult=1.35)
        sb.guitar_fingerstyle("nylon_guitar", sp, vel=dyn + 0.07, style="baroque", step_beats=0.25 if idx >= 7 else 0.5, ring_mult=1.45)
        sb.guitar_strum("nylon_guitar", b0, 1.6, gv, vel=dyn + 0.08, roll=0.04, exact_step=(rpc == AB_DIESIS))
        sb.string_pad(sp, vel=dyn * 0.86, swell="cresc")
        sb.piano_figuration(sp, vel=dyn * 0.84, style="grand", step_beats=0.5)
        if idx % 2 == 0:
            sb.harp_sweep(sp, b0 + 0.1, -53, 92, vel=dyn * 0.90, spacing=0.16, note_dur=2.2, max_notes=8, with_pedal=True)
            sb.note("bassoon", b0, dur - 1.0, sp.bass_root(), dyn * 0.88, swell="cresc")
        sb.note("cello", b0, dur * 0.5 - 0.15, sp.bass_root(), dyn * 0.90, vibrato=0.22)
        sb.note("cello", b0 + dur * 0.5, dur * 0.5 - 0.2, sp.tenor_root() + P5, dyn * 0.86, vibrato=0.20)
        if idx >= 5:
            sb.note("french_horn", b0 + 0.1, dur - 1.1, sp.tenor_root() + P5, dyn * 0.90, swell="cresc", vibrato=0.16)
    sb.timpani_roll(955.0, 4.85, pitch(C, 2), 0.62, 0.90, spacing=0.25)

    # VII.B (960..1016): CATHEDRAL PIPE ORGAN APOTHEOSIS & 19-TRACK TUTTI!
    apoth_specs = [
        (960.0, 967.0, F, "add9", "VII.B1 ORGAN ENTRANCE: Pure F add9 (A4=440Hz!)"),
        (967.0, 974.0, C, "dom9", "VII.B2 Septimal C9 (4:5:6:7:9)"),
        (974.0, 981.0, D_MINUS, "min_dm", "VII.B3 Noble Dm-"),
        (981.0, 988.0, A, "min7", "VII.B4 Radiant Am7 (A4=440Hz)"),
        (988.0, 995.0, BB, "add9", "VII.B5 Soaring Bb add9"),
        (995.0, 1002.0, F, "dom9", "VII.B6 Septimal F9 (Eb_harm=12)"),
        (1002.0, 1009.0, C, "dom9", "VII.B7 Climactic Septimal C9"),
        (1009.0, 1016.0, F, "add9", "VII.B8 Cathedral Crown on F add9 (A4=440Hz!)"),
    ]
    organ_vels = [0.74, 0.78, 0.80, 0.83, 0.86, 0.88, 0.90, 0.92]
    for idx, (b0, b1, rpc, qual, lbl) in enumerate(apoth_specs):
        sp = sb.add_span(b0, b1, rpc, qual, lbl)
        dur = b1 - b0
        ov = organ_vels[idx]
        br = sp.bass_root(-106, -54)
        r_ten = sp.tenor_root()
        th = sp.third_offset()

        # Cathedral Pipe Organ strictly <= C5 (step 53), zero mud!
        org_top1 = r_ten + OCT + th
        if org_top1 > 53:
            org_top1 -= OCT
        org_top2 = r_ten + OCT + P5
        if org_top2 > 53:
            org_top2 -= OCT
        org_v = sorted({br, br + OCT, r_ten + P5, org_top1, org_top2})
        sb.chord("church_organ", b0, dur - 0.18, org_v, ov, swell="cresc" if idx < 6 else "sfz")

        # Virtuosic Dual Guitars + Harp tapestry right through the grand Tutti!
        sb.guitar_strum("nylon_guitar", b0, 2.2, sp.guitar_voicing(6), vel=min(0.92, ov + 0.04), roll=0.04)
        sb.guitar_fingerstyle("steel_guitar", sp, vel=min(0.92, ov + 0.04), style="toccatina", step_beats=0.25, ring_mult=1.3)
        sb.guitar_fingerstyle("nylon_guitar", ChordSpan(b0 + 2.5, b1, rpc, qual), vel=ov, style="baroque", step_beats=0.5, ring_mult=1.4)
        sb.harp_sweep(sp, b0 + 0.15, -53, 101, vel=ov * 0.94, spacing=0.16, note_dur=2.6, ascending=(idx % 2 == 0), max_notes=9, with_pedal=True)

        sb.string_pad(sp, vel=ov * 0.90, track_id="string_ensemble", swell="arch")
        sb.string_pad(sp, vel=ov * 0.78, track_id="tremolo_strings", swell="cresc")
        sb.piano_figuration(sp, vel=ov * 0.84, style="grand", step_beats=0.5)

        # Clean wind/brass phrasing with >= 1.1b breaths every 2 bars!
        w_dur = (dur - 1.20) if (idx % 2 == 1) else (dur - 0.25)
        if idx != 3:
            sb.note("trombone", b0, w_dur, br + OCT, ov * 0.86, swell="sfz" if idx in (0, 7) else "arch")
            sb.note("bassoon", b0, w_dur, br, ov * 0.88, swell="arch")
        if idx not in (2, 5):
            sb.note("french_horn", b0 + 0.1, w_dur - 0.1, r_ten + P5, ov * 0.90, swell="arch", vibrato=0.16)

        sb.note("cello", b0, dur * 0.5 - 0.15, br + OCT, ov * 0.92, vibrato=0.24)
        sb.note("cello", b0 + dur * 0.5, dur * 0.5 - 0.2, r_ten + P5, ov * 0.88, vibrato=0.22)
        sb.note("dotara", b0, 0.9, r_ten + OCT, ov * 0.84)
        sb.note("ektara", b0, 2.4, r_ten, ov * 0.80)
        if idx in (0, 4, 6, 7):
            sb.note("timpani", b0, 1.4, br, ov * 0.86, trim_to_chord=False)
            if idx == 6:
                sb.timpani_roll(b0 + 3.0, dur - 3.15, br, 0.68, 0.90, spacing=0.25)

    # Soaring Anthemic Apotheosis Melody in Clarinet, English Horn & Viola (zero pitch glides!)
    apoth_mel = [
        (960.0, 3.2, pitch(A, 4), 0.86),
        (963.5, 3.1, pitch(C, 5), 0.88),
        (967.0, 3.2, pitch(BB_HARM, 4), 0.90),
        (970.5, 2.3, pitch(D, 5), 0.88),
        # Breath 972.8..974.2
        (974.2, 3.2, pitch(A, 4), 0.88),
        (977.6, 3.0, pitch(D_MINUS, 5), 0.90),
        (981.0, 3.2, pitch(E, 5), 0.90),
        (984.5, 2.3, pitch(C, 5), 0.86),
        # Breath 986.8..988.2
        (988.2, 3.2, pitch(D_MINUS, 5), 0.90),
        (991.6, 3.0, pitch(C, 5), 0.91),
        (995.0, 3.2, pitch(EB_HARM, 5), 0.91),
        (998.5, 2.3, pitch(C, 5), 0.88),
        # Breath 1000.8..1002.2
        (1002.2, 3.2, pitch(E, 5), 0.92),
        (1005.6, 3.0, pitch(BB_HARM, 4), 0.90),
        (1009.0, 5.8, pitch(A, 4), 0.92),         # Crowns on exact A4 = 440.00 Hz!
    ]
    sb.phrase("clarinet", apoth_mel, vibrato=0.22)
    sb.phrase("english_horn", [(b, d, st - OCT if st > 53 else st, v * 0.92) for b, d, st, v in apoth_mel], vibrato=0.24)
    sb.phrase("viola", [(b, d, st - OCT, v * 0.88) for b, d, st, v in apoth_mel], vibrato=0.24)

    # VII.C (1016..1052, 120 -> 68 BPM): Serene Plagal Coda & Exposed Dual-Guitar 4:5:6 Bell Stillness (mf -> ppp)
    coda_specs = [
        (1016.0, 1025.0, BB, "add9", "VII.C1 Plagal Bb add9 / F pedal", F),
        (1025.0, 1034.0, F, "dom9", "VII.C2 Septimal F9 Farewell", F),
        (1034.0, 1043.0, F, "add9", "VII.C3 Intimate Dual-Guitar & Harp F add9", F),
        (1043.0, 1052.0, F, "maj", "VII.C4 Final Beatless 4:5:6 F Major Guitar Bell (A4=440Hz, ppp)", F),
    ]
    coda_vels = [0.54, 0.40, 0.30, 0.25]
    for idx, (b0, b1, rpc, qual, lbl, ped) in enumerate(coda_specs):
        sp = sb.add_span(b0, b1, rpc, qual, lbl, ped)
        dur = b1 - b0
        cv = coda_vels[idx]
        br = sp.bass_root(-106, -54)  # Deep F2 (-84)

        if idx < 2:
            sb.chord("church_organ", b0, dur - 0.4, [br, br + OCT, pitch(C, 4), pitch(A, 4)], cv, swell="dim")
            sb.string_pad(sp, vel=cv * 0.88, swell="dim", trim_tail=0.30)
            sb.note("bassoon", b0, dur - 1.2, br, cv * 0.86, swell="dim")

        # Dual guitars + harp carry the final 27 seconds into beatless glass stillness!
        if idx < 3:
            sb.guitar_fingerstyle("nylon_guitar", sp, vel=cv + 0.06, style="glass", step_beats=1.0, ring_mult=1.9)
            sb.guitar_strum("steel_guitar", b0 + 0.2, dur * 0.65, sp.guitar_voicing(6), vel=cv + 0.05, roll=0.07)
            sb.harp_sweep(sp, b0 + 0.6, -31, 89, vel=cv + 0.06, spacing=0.32, note_dur=3.8, max_notes=7, with_pedal=True)
        else:
            # Final pure 4:5:6 F Major 6-string chord [-84(F2), -31(F3), 0(C4), 22(F4), 39(A4=440Hz), 53(C5)]!
            final_f_6 = [-84, -31, 0, 22, 39, 53]
            sb.guitar_strum("nylon_guitar", b0, dur - 0.35, final_f_6, vel=0.32, roll=0.09)
            sb.guitar_strum("steel_guitar", b0 + 0.6, dur - 0.95, final_f_6, vel=0.30, roll=0.09, upstroke=True)
            sb.add_pedal("harp", b0 + 0.2, dur - 0.5)
            sb.chord("harp", b0 + 1.2, dur - 1.5, [-31, 0, 22, 39, 53], vel=0.28, roll=0.14)
            sb.note("cello", b0, dur - 0.6, -84, 0.26, swell="dim", vibrato=0.12)

    score = sb.build_dict()
    return sb, score


# =============================================================================
# Strict Musicological & Acoustic Audit (Exact Match to `analyze` + v2 Brief)
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

    # 2. Strict Anti-Wailing Check: ZERO slide_from_cents on ALL Western instruments!
    western_slides = 0
    indian_slides = 0
    for tr in score["tracks"]:
        tid = tr["id"]
        for n in tr["notes"]:
            sc = abs(n.get("slide_from_cents", 0.0))
            mc = abs(n.get("meend_cents", 0.0))
            if tid in WESTERN_TRACKS and (sc > 0.0 or mc > 0.0):
                western_slides += 1
                errors.append(f"Western glide forbidden on '{tid}' at beat {n['beat']}: slide={sc}, meend={mc}")
                break
            if tid in INDIAN_TRACKS and (sc > 0.0 or mc > 0.0):
                indian_slides += 1

    # Confirm no 1-beat unchanging-root comma-oscillation spans
    short_spans = [sp for sp in sb.grid if (sp.end - sp.start) < 2.5]
    if short_spans:
        errors.append(f"Found {len(short_spans)} short <2.5b ChordSpans (risk of 1-beat comma oscillation!)")

    # 3. Guitar prominence & per-section coverage check
    sec_bounds = [s["beat"] for s in score["sections"]] + [99999.0]
    guitar_counts = {"nylon_guitar": 0, "steel_guitar": 0}
    guitar_opening_30s = {"nylon_guitar": 0, "steel_guitar": 0}
    guitar_per_sec: Dict[str, List[int]] = {
        "nylon_guitar": [0] * len(score["sections"]),
        "steel_guitar": [0] * len(score["sections"]),
    }

    all_spans = []
    max_end_s = 0.0
    max_beat = 0.0
    total_notes = 0
    organ_first_beat: Optional[float] = None
    collapse_transitions = 0
    pitched_transitions = 0

    for tr in score["tracks"]:
        tid = tr["id"]
        inst = tr["instrument"]
        is_perc = inst == "timpani"
        is_sf2 = inst not in ("ektara", "dotara")
        notes = tr["notes"]
        total_notes += len(notes)

        if tid in guitar_counts:
            guitar_counts[tid] = len(notes)
            for n in notes:
                t_sec = sb.tempo.beat_to_seconds(n["beat"])
                if t_sec <= 30.0:
                    guitar_opening_30s[tid] += 1
                for si in range(len(score["sections"])):
                    if sec_bounds[si] - 1e-4 <= n["beat"] < sec_bounds[si + 1] - 1e-4:
                        guitar_per_sec[tid][si] += 1
                        break

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
            all_spans.append((s0, s1, b0, b1, n["step"], tid, is_perc))

            if inst == "church_organ":
                if organ_first_beat is None or b0 < organ_first_beat:
                    organ_first_beat = b0

            if idx > 0 and not is_perc:
                prev_st = notes[idx - 1]["step"]
                cur_st = n["step"]
                if prev_st != cur_st:
                    pitched_transitions += 1
                    if edo53_to_12tet_midi(prev_st) == edo53_to_12tet_midi(cur_st):
                        collapse_transitions += 1

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

        lo_sw, hi_sw = SWEET_SPOTS[tid]
        for n in notes:
            if not (lo_sw <= n["step"] <= hi_sw):
                errors.append(
                    f"Register out of sweet spot on '{tid}' at beat {n['beat']:.2f}: "
                    f"step={n['step']} not in [{lo_sw}, {hi_sw}]"
                )
                break

        if inst in WIND_BRASS and notes:
            max_run = 0.0
            cur_s = notes[0]["beat"]
            cur_e = cur_s + notes[0]["dur"]
            for n in notes[1:]:
                if n["beat"] - cur_e < 0.50:
                    cur_e = max(cur_e, n["beat"] + n["dur"])
                else:
                    max_run = max(max_run, cur_e - cur_s)
                    cur_s = n["beat"]
                    cur_e = cur_s + n["dur"]
            max_run = max(max_run, cur_e - cur_s)
            if max_run > 15.0:
                errors.append(f"Unbreathed wind/brass run on '{tid}': {max_run:.2f}b")

    combined_guitar_notes = guitar_counts["nylon_guitar"] + guitar_counts["steel_guitar"]
    if combined_guitar_notes < 900:
        errors.append(f"Combined guitar notes {combined_guitar_notes} < 900 minimum!")
    for g_id in ("nylon_guitar", "steel_guitar"):
        if guitar_opening_30s[g_id] < 20:
            errors.append(f"'{g_id}' not prominent enough in 0:00-0:30 ({guitar_opening_30s[g_id]} notes)")
        for si, cnt in enumerate(guitar_per_sec[g_id]):
            if cnt < 15:
                errors.append(f"'{g_id}' has too few notes ({cnt}) in Section {si + 1}")

    if organ_first_beat is None or organ_first_beat < 950.0:
        errors.append(f"church_organ must be reserved strictly for Finale VII.B (got {organ_first_beat})")

    # 3b. Every non-open5/sus harmonic ChordSpan must sound its pure 53-EDO chord 3rd!
    for sp in sb.grid:
        if sp.free_microtonal or sp.quality in ("open5", "sus2", "sus2_m", "sus4"):
            continue
        th_pc = (sp.root_pc + sp.third_offset()) % OCT
        has_third = any(
            (not is_perc)
            and b0 < sp.end - 0.05
            and b1 > sp.start + 0.05
            and (st % OCT) == th_pc
            for _, _, b0, b1, st, _, is_perc in all_spans
        )
        if not has_third:
            errors.append(
                f"ChordSpan '{sp.label}' ({sp.start:.1f}..{sp.end:.1f}, q={sp.quality}) omits its chord 3rd (pc={th_pc})!"
            )

    # 4. Sustained 4..=6-step close-register rub check (> 0.35b)
    pitched_spans = sorted([s for s in all_spans if not s[6]], key=lambda x: x[2])
    for i in range(len(pitched_spans)):
        _, _, b0_a, b1_a, st_a, tid_a, _ = pitched_spans[i]
        for j in range(i + 1, len(pitched_spans)):
            _, _, b0_b, b1_b, st_b, tid_b, _ = pitched_spans[j]
            if b0_b >= b1_a - 0.35:
                break
            ov_b = min(b1_a, b1_b) - max(b0_a, b0_b)
            if ov_b > 0.35 and 4 <= abs(st_a - st_b) <= 6:
                errors.append(
                    f"Sustained 4..=6-step rub ({abs(st_a - st_b)} steps, {ov_b:.2f}b) at beat {max(b0_a, b0_b):.2f}: "
                    f"{tid_a}({st_a}) vs {tid_b}({st_b})"
                )
                if len(errors) > 20:
                    break

    # 5. Low-register mud check (< -53, overlap >= 0.08s, 0 < diff < 22)
    low_spans = sorted([s for s in all_spans if s[4] < -OCT and not s[6]], key=lambda x: x[0])
    for i in range(len(low_spans)):
        s0_a, s1_a, _, _, st_a, tid_a, _ = low_spans[i]
        for j in range(i + 1, len(low_spans)):
            s0_b, s1_b, b_b, _, st_b, tid_b, _ = low_spans[j]
            if s0_b >= s1_a - 0.08:
                break
            if min(s1_a, s1_b) - max(s0_a, s0_b) >= 0.08 and 0 < abs(st_b - st_a) < P4:
                errors.append(f"Low mud at beat {b_b:.2f}: {tid_a}({st_a}) vs {tid_b}({st_b})")
                break

    # 6. Exact comma-clash check (overlap >= 0.20s, 1 <= mod53_dist <= 3)
    time_spans = sorted([s for s in all_spans if not s[6]], key=lambda x: x[0])
    for i in range(len(time_spans)):
        s0_a, s1_a, b_a, _, st_a, tid_a, _ = time_spans[i]
        for j in range(i + 1, len(time_spans)):
            s0_b, s1_b, b_b, _, st_b, tid_b, _ = time_spans[j]
            if s0_b >= s1_a - 0.20:
                break
            ov_s = min(s1_a, s1_b) - max(s0_a, s0_b)
            if ov_s >= 0.20:
                d = mod53_dist(st_a, st_b)
                if 1 <= d <= 3:
                    errors.append(
                        f"Comma clash at beat {max(b_a, b_b):.2f} ({ov_s:.2f}s): "
                        f"{tid_a}({st_a}) vs {tid_b}({st_b}) dist={d}"
                    )
                    if len(errors) > 20:
                        break

    dur_default_tail = max_end_s + 4.5
    dur_stage_tail = max_end_s + 5.0
    if not (585.0 <= dur_default_tail <= 615.0 and 585.0 <= dur_stage_tail <= 615.0):
        errors.append(f"Duration {dur_default_tail:.2f}s / {dur_stage_tail:.2f}s outside [585, 615]s!")

    bpms = [pt["bpm"] for pt in score["tempo"]]
    if min(bpms) > 68.0 or max(bpms) < 124.0:
        errors.append(f"Tempo range {min(bpms)}..{max(bpms)} BPM does not span <=68 to >=124 BPM!")

    if errors:
        print(f"AUDIT FAILED ({len(errors)} issues):")
        for e in errors[:25]:
            print("  !", e)
        raise SystemExit(1)

    print("AUDIT PASSED (0 Western glides, 0 voice steals, 0 low mud, 0 comma clashes, 0 >0.35b rubs)!")
    print(
        f"Duration: {dur_default_tail:.2f}s (default tail) / {dur_stage_tail:.2f}s (stage tail) | "
        f"Beats: {max_beat:.1f} | Tempo: {min(bpms):.1f}–{max(bpms):.1f} BPM | Total Notes: {total_notes}"
    )
    print(
        f"Dual Guitars: nylon_guitar={guitar_counts['nylon_guitar']} (0:00-0:30: {guitar_opening_30s['nylon_guitar']}, per-sec={guitar_per_sec['nylon_guitar']}), "
        f"steel_guitar={guitar_counts['steel_guitar']} (0:00-0:30: {guitar_opening_30s['steel_guitar']}, per-sec={guitar_per_sec['steel_guitar']}), "
        f"combined={combined_guitar_notes}"
    )
    print(
        f"Western pitch glides: {western_slides} | Section III Indian meend notes: {indian_slides} | "
        f"Intra-semitone melodic collapses: {collapse_transitions}/{pitched_transitions} "
        f"({100.0 * collapse_transitions / max(1, pitched_transitions):.1f}%)"
    )
    for s in score["sections"]:
        ts = sb.tempo.beat_to_seconds(s["beat"])
        print(f"  [{int(ts // 60)}:{int(round(ts)) % 60:02d}] beat {s['beat']:6.1f} : {s['title']}")


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
