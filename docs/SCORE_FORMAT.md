# Musical Chairs — 53-EDO Score & Stage Format Guide

This guide is a self-contained specification for **AI agents and human composers** authoring microtonal classical music in **53-EDO (53 Equal Divisions of the Octave)** for **Musical Chairs**.

Musical Chairs uses a **decoupled 2-input architecture**:
1. **`score.json`** — Pure stage-independent music (tempo map, instrument tracks, 53-EDO notes & articulation).
2. **`--stage <stage.json>`** — Reusable concert-stage seating `(x, y)`, per-player mix `gain`, `warm_lowpass_hz`, hall `reverb_rt60`, `tail_seconds`, and `end_silence_seconds`.

Hand this file (plus [scores/example_minimal.json](../scores/example_minimal.json)) to any AI agent so it can compose a valid 53-EDO score, render it on any virtual stage in **53-EDO or 12-TET**, export synchronized dry stems + a **1600×960 dark-studio SVG score/stage map**, and compare compositions side-by-side.

---

## 1. Quickstart CLI Commands

All commands run from the repository root (`/home/deck/projects/music`). No SoundFont files are committed or bundled in this repository — see **[Setup: Obtaining a General MIDI SoundFont](../README.md#setup-obtaining-a-general-midi-soundfont-sf2)** in `README.md` to obtain GeneralUser GS (`https://schristiancollins.com/generaluser.php`) or an alternative GM `.sf2` (such as FluidR3_GM or MuseScore General, each under its own license) and place it at `soundfonts/GeneralUser-GS.sf2` or pass `--soundfont /path/to/your.sf2`. The engine compiles with pure Rust (`x86_64-unknown-linux-musl` via `.cargo/config.toml`).

```bash
# Render a pure-music score on a reusable stage preset (defaults to output/<stem>.wav)
cargo run --release -- render scores/example_minimal.json --stage stages/concert_hall.json

# Full render: 53-EDO + stage preset + 30s intentional trailing silence + 1600x960 SVG visual
cargo run --release -- render scores/sample_5min.json output/sample_5min.wav \
  --stage stages/concert_hall.json \
  --end-silence 30 \
  --image output/sample_5min.svg

# Render the EXACT same score quantized to 12-TET for direct 53-EDO vs 12-TET A/B comparison
cargo run --release -- render scores/sample_5min.json output/sample_5min_12tet.wav \
  --stage stages/concert_hall.json \
  --tuning 12tet \
  --end-silence 30

# Render AND export synchronized centered dry stems (<dir>/<track.id>.wav)
cargo run --release -- render scores/sample_5min.json output/sample_5min.wav \
  --stage stages/concert_hall.json \
  --stems-dir output/stems_5min

# Audit a score in ~2 ms (15-ch voice stealing, <C3 mud, comma clashes, comma-drift contour)
cargo run --release -- analyze scores/sample_5min.json --stage stages/concert_hall.json

# Fast standalone SVG visualization (~6 ms, no audio rendering required; defaults to output/<stem>.svg)
cargo run --release -- visualize scores/sample_5min.json output/sample_5min.svg \
  --stage stages/concert_hall.json \
  --tuning 53edo

# Render YouTube-ready 1080p VP9 + 192k Opus animated WebM concert video (requires ffmpeg; defaults to output/<stem>.webm)
cargo run --release -- render-video scores/sample_5min.json output/sample_5min.wav output/sample_5min.webm \
  --stage stages/concert_hall.json \
  --fps 24

# Override SoundFont2 path (default: soundfonts/GeneralUser-GS.sf2)
cargo run --release -- render scores/example_minimal.json output/example_minimal.wav \
  --stage stages/intimate_circle.json \
  --soundfont path/to/custom.sf2

# Render all isolated 53-EDO instrument auditions, 53-note harp sweep, & fusion showcase
cargo run --release -- audition

# Render the pure-Rust additive/physical-model synth preview (no SoundFont)
cargo run --release -- preview-synth

# Run the full test suite (tuning accuracy, StageConfig precedence, 12-TET quantization, end-silence, SVG)
cargo test --release
```

### Complete CLI Flag Reference

| Subcommand | Flags | Notes |
|---|---|---|
| `render <input.json> [output.wav]` | `--stage <stage.json>` | Optional decoupled stage placement, gain, warm LP & hall settings. |
| | `--tuning <53edo\|12tet>` | Tuning system (default: `53edo`). See §2.3 for 12-TET projection details. |
| | `--end-silence <seconds>` | Appends exact clean `(0.0, 0.0)` silence after the mastered reverb tail (overrides JSON). |
| | `--stems-dir <dir>` | Exports synchronized centered dry stems `<dir>/<track.id>.wav` (including trailing silence). |
| | `--image <out.svg>` | Also writes a 1600×960 dark-studio SVG (2D stage map + pitch-roll timeline). |
| | `--soundfont <path>` | Custom SoundFont2 file (default: `soundfonts/GeneralUser-GS.sf2`). |
| `analyze <score.json>` | `--stage <stage.json>`, `--json` | Audits 15-channel SF2 polyphony/voice-stealing, `< C3` low-register mud, cross-track comma clashes (`1..=3` steps mod 53), section timestamps, and comma-drift contour. |
| `visualize <score.json> [out.svg]` | `--stage <stage.json>`, `--tuning <53edo\|12tet>`, `--end-silence <seconds>` | Pure-Rust SVG generator (`out.svg` defaults to `output/<stem>.svg`). |
| `render-video <score.json> <audio.wav> [output.webm]` | `--stage <stage.json>`, `--tuning <53edo\|12tet>`, `--fps <24>`, `--width <1920>`, `--height <1080>` | Pure-Rust animated 1080p VP9 (`yuv420p`) + 192k Opus WebM video piped to `ffmpeg` (`output.webm` defaults to `output/<score_stem>.webm`). Reads exact WAV duration including trailing silence. |
| `audition` | *(none)* | Generates isolated instrument auditions + fusion showcase under `output/`. |
| `preview-synth` | *(none)* | Generates pure-Rust physical/additive synth preview (`output/preview_60s.wav`). |

All flags accept both space-separated (`--stage stages/concert_hall.json`) and `=` (`--stage=stages/concert_hall.json`) forms. Every `render` run prints title, duration, tuning, stage name, tail/RT60/end-silence, per-track note counts/coords/gain/LP, stems/SVG paths, and mastering stats (`Peak dBFS`, `RMS L/R dBFS`, `Clipped`, `NaNs`).

---

## 2. Decoupled 2-Input Schema (`score.json` + `stage.json`)

### 2.1 Pure-Music `score.json` Schema

Recommended practice is to keep `score.json` **purely musical** (omitting `x`, `y`, `gain`, `warm_lowpass_hz`, `reverb_rt60`, `tail_seconds`) and pass `--stage stages/concert_hall.json` at render time. Inline track stage fields remain fully supported for backward compatibility.

#### Minimal Pure-Music Example

```json
{
  "title": "Luminous 53-EDO Miniature",
  "description": "Stage-independent pure-music 53-EDO score.",
  "sample_rate": 48000,
  "tempo": [
    { "beat": 0.0, "bpm": 90.0 },
    { "beat": 8.0, "bpm": 84.0 }
  ],
  "tracks": [
    {
      "id": "english_horn",
      "name": "English Horn",
      "instrument": "english_horn",
      "notes": [
        {
          "beat": 0.5,
          "dur": 1.4,
          "step": 31,
          "vel": 0.76,
          "cents": 0.0,
          "slide_from_cents": 0.0,
          "breath_swell": true,
          "meend_cents": 0.0
        }
      ]
    }
  ]
}
```

#### Top-Level `score.json` Fields

| Field | Type | Required | Default | Range / Notes |
|---|---|---|---|---|
| `title` | `string` | No | `"Untitled 53-EDO Piece"` | Human-readable composition title printed in CLI & SVG header. |
| `description` | `string` | No | `""` | Free-form notes (movement outline, tuning notes, agent metadata). |
| `sample_rate` | `integer` | No | `48000` | Output sample rate in Hz (`8000`–`192000`). **Keep at `48000`** for native physical-model rendering without resampling. |
| `tail_seconds` | `number` | No | `4.5` | Extra reverb/release tail appended after the final note ends (`>= 0.0`). Overridden by `stage.json` if set there. |
| `reverb_rt60` | `number` | No | `2.25` | 8-channel Walsh-Hadamard FDN hall decay time in seconds (`>= 0.0`). Overridden by `stage.json` if set there. |
| `end_silence_seconds` | `number` | No | `0.0` | Clean trailing silence `(0.0, 0.0)` appended *after* the mastered reverb tail without altering RMS or peak normalization. Precedence: CLI `--end-silence` > `stage.json` > `score.json` > `0.0`. |
| `tempo` | `TempoPoint[]` | No | `[{"beat": 0.0, "bpm": 70.0}]` | Non-empty piecewise-linear BPM map (see below). |
| `sections` | `Section[]` | No | `[]` | Optional movement/section markers `[{"beat": 0.0, "title": "I. Adagio"}]` rendered on SVG timelines, 1080p WebM video headers, `analyze`, and Studio UI jump buttons. |
| `tracks` | `Track[]` | **Yes** | — | Array of instrument tracks (rendered in parallel across CPU threads). |

#### `TempoPoint` Object (`tempo[]`)

| Field | Type | Required | Notes |
|---|---|---|---|
| `beat` | `number` | **Yes** | Musical beat position (`>= 0.0`). Segments are sorted ascending by `beat`. |
| `bpm` | `number` | **Yes** | Tempo in beats per minute (`> 0.0`, typically `48.0`–`120.0`). |

**How `TempoMap` interpolates (`src/score.rs`):** Between consecutive points `(b1, bpm1)` and `(b2, bpm2)`, BPM ramps linearly with exact analytical logarithmic time integration:
- **Constant tempo** across beats `0..64`: `{"beat": 0.0, "bpm": 72.0}, {"beat": 64.0, "bpm": 72.0}`.
- **Smooth ritardando / accelerando** across beats `60..64`: `{"beat": 60.0, "bpm": 72.0}, {"beat": 64.0, "bpm": 60.0}`.
- **Abrupt tempo jump** at beat `64`: `{"beat": 63.999, "bpm": 72.0}, {"beat": 64.0, "bpm": 80.0}`.

#### `Track` Object (`tracks[]`)

| Field | Type | Required | Default | Range / Notes |
|---|---|---|---|---|
| `id` | `string` | **Yes** | — | Unique non-empty slug with no path separators (`/`, `\`, `..`). Used as stem filename `<stems-dir>/<id>.wav` and primary lookup key in `stage.json`. |
| `name` | `string \| null` | No | `id` | Display name for CLI logs & SVG stage labels. |
| `instrument` | `string` | **Yes** | — | Must be one of the 26 supported instrument IDs in Section 4. Also used as fallback lookup key in `stage.json`. |
| `notes` | `Note[]` | No | `[]` | Array of note events on this track. |
| `pedals` | `PedalSpan[]` | No | `[]` | Optional MIDI `CC 64` damper sustain pedal spans `[{"beat": 0.0, "dur": 3.85}]` for `piano` / `harp` sympathetic resonance. |
| `x` *(optional inline)* | `number` | No | `0.0` | Stage horizontal position in meters (`-6.0` left to `+6.0` right). Prefer setting in `stage.json`. |
| `y` *(optional inline)* | `number` | No | `4.5` | Stage depth in meters (`2.0` front to `14.0` rear). Prefer setting in `stage.json`. |
| `width` *(optional inline)* | `number` | No | `0.0` | Physical ensemble stereo spread in meters (`0.0` = pinpoint soloist; `1.4`–`4.8` = wide piano / string orchestra / pipe organ). Prefer setting in `stage.json`. |
| `gain` *(optional inline)* | `number` | No | `1.0` | Linear track mix gain (`>= 0.0`, `0.4`–`1.2` typical). Prefer setting in `stage.json`. |
| `warm_lowpass_hz` *(optional inline)* | `number \| null` | No | `null` | Optional 2-pole Butterworth low-pass cutoff in Hz (`> 0.0`, clamped internally to `[40, 0.45*sr]`) applied to L/R before spatialization. Prefer setting in `stage.json`. |

#### `Note` Object (`tracks[].notes[]`)

| Field | Type | Required | Default | Range / Notes |
|---|---|---|---|---|
| `beat` | `number` | **Yes** | — | Note onset time in musical beats (`>= 0.0`). |
| `dur` | `number` | **Yes** | — | Note duration in musical beats (`> 0.0`). |
| `step` | `integer` | **Yes** | — | **53-EDO pitch step**, where **`C4 = 0`**, **`A4 = 39` (440 Hz)**, **`OCT = 53`**. |
| `vel` | `number` | No | `0.75` | Normalized velocity (`0.05`–`1.0`). Shape dynamically (`0.40`–`0.92`) for musical phrasing. |
| `cents` | `number` | No | `0.0` | Extra fine microtonal pitch offset in cents added on top of `step`. |
| `slide_from_cents` | `number` | No | `0.0` | **SF2 instruments** (fallback for `ektara`). Smooth 140 ms quadratic pitch-bend glide *from* `step + cents + slide_from_cents` *into* `step + cents`. Negative slides up; positive slides down. Keep within `[-150, +150]` (clamped at `±195¢`). Ignored in `--tuning 12tet`. |
| `breath_swell` | `boolean` | No | `false` | **SF2 instruments only.** Shorthand for `swell: "arch"` (`82 → 124 → 82`). |
| `swell` | `string \| null` | No | `null` | **SF2 instruments only.** Directional CC 11 expression curve: `"none"`, `"arch"`, `"cresc"` (`68 → 126`), `"dim"` (`125 → 68`), or `"sfz"` (`127 → 80 → 114`). Works on winds, brass, and strings! |
| `vibrato` | `number` | No | `0.0` | **SF2 instruments only.** Delayed `CC 1` vibrato depth (`0.0`–`1.0`) blooming smoothly ~160 ms after attack so pure 53-EDO intervals lock cleanly first. |
| `meend_cents` | `number` | No | `0.0` | **`ektara` physical model** (fallback for SF2 slides). Initial elastic pitch-relaxation offset in cents (exponential decay, τ = 110 ms) into `step`. Positive (`+12` to `+28`) gives authentic gourd-string pluck relaxation. Ignored in `--tuning 12tet`. |

---

### 2.2 Reusable `stage.json` Schema & Precedence

A `stage.json` file separates **room acoustics and concert seating** from the musical score so you can audition the exact same `score.json` in multiple acoustic spaces!

```json
{
  "name": "Concert Hall",
  "description": "Balanced symphonic concert hall seating",
  "reverb_rt60": 2.25,
  "tail_seconds": 5.0,
  "end_silence_seconds": 0.0,
  "players": {
    "piano":        { "x": -2.3, "y": 3.3,  "gain": 0.96, "warm_lowpass_hz": null },
    "sitar":        { "x": -1.5, "y": 2.7,  "gain": 0.84, "warm_lowpass_hz": 2700.0 },
    "church_organ": { "x":  0.0, "y": 10.4, "gain": 0.74, "warm_lowpass_hz": 3500.0 }
  }
}
```

#### Exact Resolution Precedence (`src/score_json.rs`)
- **Per-track fields (`x`, `y`, `gain`, `warm_lowpass_hz`):**
  1. `stage.players[track.id]` (if `--stage` is provided and key exists)
  2. `stage.players[track.instrument]` (fallback if `track.id` differs from `track.instrument`, e.g. `"piano_lh"` falls back to `"piano"`)
  3. Inline field on the track in `score.json`
  4. Engine default (`x = 0.0`, `y = 4.5`, `gain = 1.0`, `warm_lowpass_hz = null`)
  - *Note on `warm_lowpass_hz`:* An explicit `"warm_lowpass_hz": null` in `stage.json` **explicitly disables** an inline low-pass filter; omitting the key falls back down the precedence chain.
- **Hall & tail fields (`reverb_rt60`, `tail_seconds`):** `stage.json` (if present) > `score.json` > default (`2.25` / `4.5`).
- **Trailing silence (`end_silence_seconds`):** CLI `--end-silence` > `stage.json` > `score.json` > `0.0`.

#### Bundled Stage Presets (`stages/`)

| Preset File | Name | `reverb_rt60` | `tail_seconds` | Acoustic Layout |
|---|---|---:|---:|---|
| [stages/concert_hall.json](../stages/concert_hall.json) | **Concert Hall** | `2.25 s` | `5.0 s` | Balanced symphonic seating matching the 14-track 5-min ensemble (includes defaults for all 26 instruments, warmed `sitar` LP `2700 Hz`, `church_organ` LP `3500 Hz`). |
| [stages/intimate_circle.json](../stages/intimate_circle.json) | **Intimate Chamber Circle** | `1.45 s` | `3.8 s` | Close, warm chamber-salon semicircle (`y = 2.2–6.8 m`) with tighter hall bloom and immediate presence. |
| [stages/east_west_split.json](../stages/east_west_split.json) | **East-West Antiphonal Split** | `2.35 s` | `5.0 s` | Western chamber orchestra arrayed Stage Left (`x < 0`) answering Indian classical shruti instruments (`sitar`, `dotara`, `ektara`) arrayed Stage Right (`x > 0`). |

---

### 2.3 Tuning Modes (`--tuning 53edo|12tet`) & SVG Visualization (`--image` / `visualize`)

- **`--tuning 53edo` (default):** Full exact 53-EDO frequency synthesis (`440 * 2^((step - 39)/53 + cents/1200)`), 14-bit pitch-bent SF2 channels, smooth meend glides, and exact waveguide pitch on `ektara`/`dotara`.
- **`--tuning 12tet`:** Projects every note's 53-EDO pitch to its nearest 12-TET semitone anchored at `C4 = step 0`:
  $$\text{midi} = \operatorname{round}\!\left(60 + \frac{12 \cdot \text{step}}{53} + \frac{\text{cents}}{100}\right)$$
  For example: `C4 (step 0) → MIDI 60 (261.63 Hz)`, `DIESIS (+2) → MIDI 60 (261.63 Hz)` (collapsing the diesis!), and `A4 (step 39) → MIDI 69 (440.00 Hz)`. SF2 tracks use zero pitch bend / glide and `ektara`/`dotara` tune to exact `440 * 2^((midi - 69)/12)` Hz. This makes it trivial to hear how much cleaner 53-EDO triads, 7-limit ninths, and comma modulations sound compared to 12-TET!
- **SVG Visualizer (`--image <out.svg>` or `visualize <score.json> [out.svg]`):** Generates a crisp **1600×960 dark-studio SVG** in pure Rust (~6 ms for a 5-minute symphony) featuring:
  - **Left Panel — 2D Concert Stage Map:** Concentric depth arcs (`3m, 6m, 9m, 12m`), listener position at `(0, 0)`, family-colored labeled musician markers from the resolved `stage.json`, and dashed rings indicating active `warm_lowpass_hz` filters.
  - **Right Panel — Pitch-Roll Timeline:** Every note across the full score color-coded by instrument family, `m:ss` time axis, `C2..C6` octave lines, title/tuning header, and a bottom **comma-drift indicator strip** visualizing 53-EDO comma/diesis motion.
- **Animated YouTube WebM Video (`render-video <score.json> <audio.wav> [output.webm]`):** Pure-Rust multi-threaded frame rasterizer (`src/video.rs`) piping raw `rgb24` frames directly to `ffmpeg` (`libvpx-vp9 -b:v 0 -crf 30 -deadline realtime -cpu-used 6 -row-mt 1 -pix_fmt yuv420p` + `libopus 192k`, ~115 fps at 1080p!). Matches the exact RIFF duration of `<audio.wav>` (including trailing silence) and renders:
  - **Left Panel:** Live 2D Concert Stage Map with golden `3m/6m/9m/12m` depth arcs, collision-free anti-aliased vector labels, multi-layer additive musician glows (80 ms attack / 320 ms decay), expanding concentric onset ripples, and a warm Pipe Organ crown bloom.
  - **Right Panel:** Top **53-EDO/12-TET Harmonic Mandala Wheel** (53 golden tick marks with `~`-prefixed approximate 12-tone landmarks, glowing active pitch orbs with exact 53-EDO step numbers `0..52`, translucent harmonic chord lines, and live Pythagorean & Just interval ratio readouts such as `1:1`, `3:2`, `9:8`, `81:64`, `5:4`, `7:4`) + bottom **Now Playing** live instrument level bars and `m:ss / total` timestamp.
  - **Bottom Progress Bar:** Smooth playhead with subtle `"CONTEMPLATIVE SILENCE"` dimming during trailing silence.

---

## 3. 53-EDO Music Theory Cheat Sheet for Agents

### Exact Pitch & Frequency Formulas (`src/tuning.rs`)

- **Step size:** $1200 / 53 \approx 22.6415\text{ cents}$ (one **syntonic comma**!)
- **Reference pitch:** `A4 = 440.0 Hz` at `step = 39`; `C4` (middle C) is `step = 0` ($\approx 264.17\text{ Hz}$, pure 5:3 below A4).
- **Frequency from `(step, cents)`:**
  $$f(\text{step}, \text{cents}) = 440 \times 2^{\left(\frac{\text{step} - 39}{53} + \frac{\text{cents}}{1200}\right)}$$
- **Octave formula:**
  ```python
  OCT = 53
  def pitch(pc: int, octave: int) -> int:
      return pc + (octave - 4) * 53
  ```

### Pitch-Class Table (`C = 0`)

| Name | `pc` | Cents | Pure JI Ratio | Oct 2 | Oct 3 | Oct 4 | Oct 5 |
|---|---:|---:|---|---:|---:|---:|---:|
| `C` | `0` | `0.00` | `1:1` | `-106` | `-53` | `0` | `53` |
| `D_MINUS` | `8` | `181.13` | `10:9` (minor whole tone) | `-98` | `-45` | `8` | `61` |
| `D` | `9` | `203.77` | `9:8` (major whole tone) | `-97` | `-44` | `9` | `62` |
| `EB` | `14` | `316.98` | `6:5` (pure minor 3rd) | `-92` | `-39` | `14` | `67` |
| `E` | `17` | `384.91` | `5:4` (pure major 3rd) | `-89` | `-36` | `17` | `70` |
| `F` | `22` | `498.11` | `4:3` (pure 4th) | `-84` | `-31` | `22` | `75` |
| `G` | `31` | `701.89` | `3:2` (pure 5th) | `-75` | `-22` | `31` | `84` |
| `AB` | `36` | `815.09` | `8:5` (pure minor 6th) | `-70` | `-17` | `36` | `89` |
| `A` | `39` | `883.02` | `5:3` (pure major 6th) | `-67` | `-14` | `39` | `92` |
| `BB_HARM` | `43` | `973.58` | `7:4` (harmonic 7th) | `-63` | `-10` | `43` | `96` |
| `B` | `48` | `1086.79` | `15:8` (pure major 7th) | `-58` | `-5` | `48` | `101` |

### Exact Interval Constants (`src/tuning.rs`)

| Constant | Steps | Cents | Target JI Ratio | Error vs JI |
|---|---:|---:|---|---:|
| `COMMA` | `1` | `22.64` | `81:80` (syntonic comma) | `+1.13¢` |
| `DIESIS` | `2` | `45.28` | `128:125` (enharmonic diesis) | `+4.22¢` |
| `CHROMATIC_SEMI` | `4` | `90.57` | `256:243` / `135:128` | — |
| `DIATONIC_SEMI` | `5` | `113.21` | `16:15` | `+1.48¢` |
| `m2_MINOR_TONE` | `8` | `181.13` | `10:9` | `-1.27¢` |
| `M2` | `9` | `203.77` | `9:8` | `-0.14¢` |
| `m3` | `14` | `316.98` | `6:5` | `+1.34¢` |
| `M3` | `17` | `384.91` | `5:4` | `-1.41¢` |
| `P4` | `22` | `498.11` | `4:3` | `+0.07¢` |
| `P5` | `31` | `701.89` | `3:2` | `-0.07¢` |
| `m6` | `36` | `815.09` | `8:5` | `+1.41¢` |
| `M6` | `39` | `883.02` | `5:3` | `-1.34¢` |
| `HARM_7` | `43` | `973.58` | `7:4` (septimal / harmonic 7th) | `+4.76¢` |
| `PYTH_m7` | `44` | `996.23` | `16:9` | `+0.14¢` |
| `JUST_m7` | `45` | `1018.87` | `9:5` | `+1.27¢` |
| `M7` | `48` | `1086.79` | `15:8` | `-1.48¢` |
| `OCT` | `53` | `1200.00` | `2:1` | `0.00¢` |

### Pure Chord Voicings (Offsets Relative to `root`)

| Chord Type | Step Offsets from `root` | Acoustic Character |
|---|---|---|
| **5-Limit Major Triad** | `[0, 17, 31]` | Beat-free `4:5:6` resonance (14¢ purer M3 than 12-EDO). |
| **5-Limit Minor Triad** | `[0, 14, 31]` | Warm, velvety `10:12:15` minor triad. |
| **Debussy 7-Limit Dom7 (`4:5:6:7`)** | `[0, 17, 31, 43]` | Luminous, non-beating blue/impressionist dominant 7th. |
| **Debussy 7-Limit Dom9 (`4:5:6:7:9`)** | `[0, 17, 31, 43, 62]` | Iconic shimmering Debussy chord (`62 = 53 + 9 = OCT + M2`). |
| **Pure Major 7th** | `[0, 17, 31, 48]` | Glassy `8:10:12:15` major seventh. |
| **Pure Major 9th** | `[0, 17, 31, 48, 62]` | Radiant open impressionist tonic sonority. |
| **Pure Minor 9th** | `[0, 14, 31, 45, 62]` | Deep, warm minor ninth using `JUST_m7 = 45` (`9:5`). |
| **Pure Add-9** | `[0, 17, 31, 62]` | Clean lyrical Mozart/Beethoven tonic bloom. |

### Indian 22-Shruti Step Map in 53-EDO (`Sa = 0`)

53-EDO maps all 22 classical Indian shrutis with sub-2-cent accuracy:

| Swara | 53-EDO Step(s) | JI Ratio | Musical Color |
|---|---:|---|---|
| **Sa** (Shadja) | `0` | `1:1` | Home tonic drone |
| **Komal Re** | `4` / **`5`** | `256:243` / `16:15` | `5` = standard expressive Komal Re (Bhairav / Bhairavi) |
| **Shuddha Re** | `8` / **`9`** | `10:9` / `9:8` | `9` = bright Yaman/Bilawal Re; `8` = soft lower Re |
| **Komal Ga** | `13` / **`14`** | `32:27` / `6:5` | `14` = warm consonant minor 3rd |
| **Shuddha Ga** | **`17`** / `18` | `5:4` / `81:64` | `17` = pure sweet 5:4 Ga |
| **Shuddha Ma** | **`22`** / `23` | `4:3` / `27:20` | `22` = pure 4:3 Ma |
| **Tivra Ma** | **`26`** / `27` | `45:32` / `729:512` | `26` = radiant Yaman sharp 4th (`M3 + M2 = 17 + 9`) |
| **Pa** (Panchama) | **`31`** | `3:2` | Pure beat-free fifth drone |
| **Komal Dha** | `35` / **`36`** | `128:81` / `8:5` | `36` = tender pure minor 6th |
| **Shuddha Dha** | **`39`** / `40` | `5:3` / `27:16` | `39` = pure 5:3 major 6th |
| **Komal Ni** | **`43`** / `44` / `45` | `7:4` / `16:9` / `9:5` | `43` = lush septimal Komal Ni (bridges Debussy & raga!) |
| **Shuddha Ni** | **`48`** / `49` | `15:8` / `243:128` | `48` = pure leading tone (`15:8`) |
| **Sa'** | `53` | `2:1` | Upper octave tonic |

*(Bold steps `0, 5, 17, 26, 31, 36, 39, 43, 53` match the verified `src/audition.rs` sitar shruti palette.)*

### Signature 53-EDO Modulations (Impossible in 12-EDO!)

Because every 5-limit chord is pure, harmonic cycles do **not** close on the same pitch — they glide smoothly across the 53-tone comma lattice while keeping exact common tones at every chord change!

1. **Chromatic-Mediant Diesis Shift (`+2` steps / `+45.28¢`):**
   - Progression of major triads descending by pure major thirds (`-17` steps each):
     $$\text{C}(k) \xrightarrow{-17} \text{A}\flat(k - 17) \xrightarrow{-17} \text{E}(k - 34) \xrightarrow{-17} \text{C}^{++}(k + 2)$$
   - Modulo 53: `0 → 36 → 19 → 2` (since $3 \times 17 = 51 = 53 - 2$).
   - Every transition holds an **exact common tone** (e.g., `C = 0` is the pure 5:4 third of `Ab = 36`, since `36 + 17 = 53 ≡ 0`!).

2. **Downward 5-Limit Comma Pump (`-1` step / `-22.64¢`):**
   - Progression: `I(k) → IV(k+22) → ii(k+8) → V(k+30) → I(k-1)`
     - `I(k)` = `[k, k+17, k+31]`
     - `IV(k+22)` = `[k+22, k+39, k+53]` (shares `k`)
     - `ii(k+8)` = `[k+8, k+22, k+39]` (minor triad on `D_MINUS`; shares both `k+22` and `k+39`!)
     - `V(k+30)` = `[k+30, k+47, k+61]` (shares `k+8 ≡ k+61` with `ii`, and sits a pure `P5 = 31` above `k-1`!)
     - `I(k-1)` = `[k-1, k+16, k+30]` (shares `k+30`!)
   - **Exact cancellation:** Two downward comma pumps (`-1 - 1 = -2`) return a `+2` diesis modulation seamlessly back to exact home tonic `k = 0`!

3. **Upward 5-Limit Comma Pump (`+1` step / `+22.64¢`):**
   - Progression: `I(k) → V(k+31) → ii(k+9) → IV(k+23) → I(k+1)`
     - `I(k)` = `[k, k+17, k+31]`
     - `V(k+31)` = `[k+31, k+48, k+62]` (shares `k+31`)
     - `ii(k+9)` = `[k+9, k+23, k+40]` (minor triad on `D`; shares `k+9 ≡ k+62`!)
     - `IV(k+23)` = `[k+23, k+40, k+54]` (shares both `k+23` and `k+40`!)
     - `I(k+1)` = `[k+1, k+18, k+32]` (shares `k+1 ≡ k+54`!)

---

## 4. Instrument Catalog, Stage Seating & Acoustic Tips

All **26 supported `instrument` IDs** render in exact 53-EDO (or 12-TET with `--tuning 12tet`):
- **24 SoundFont2 instruments** (`GeneralUser-GS.sf2` via `rustysynth`): each track gets **15 dedicated melodic MIDI channels** (channels 0–8, 10–15) with ±2-semitone 14-bit pitch bend so chords never collide in pitch bend, and SF2 chorus/reverb are disabled so 53-EDO intervals stay acoustically pure.
- **2 Pure-Rust Physical Models** (`src/indian.rs`): Karplus-Strong waveguide models with cubic fractional delay, body formants, and exact 53-EDO pitch (`ektara`, `dotara`).

### Full 26-Instrument Catalog

| `instrument` ID | Engine | Tier | Sweet-Spot Steps (Pitch) | Concert Hall `(x, y)` | Features & Acoustic Notes |
|---|---|---|---|---|---|
| `piano` | SF2 GM 0 | **Warm Core** | `-106..+92` (C2–A5) | `(-2.3, 3.3)` | Crisp Mozartian clarity, `width: 1.4`, supports `pedals` (`CC 64`). |
| `harp` | SF2 GM 46 | **Warm Core** | `-84..+106` (F2–C6) | `(-3.4, 3.7)` | Silky full 53-EDO arpeggios & harmonic sweeps (`width: 1.0`). |
| `nylon_guitar` | SF2 GM 24 | **Warm Core** | `-89..+70` (E2–E5) | `(-1.2, 3.6)` | Warm Spanish/classical plucked nylon strings; crystal-clear 53-EDO chord lock & *campanella* cascades. |
| `steel_guitar` | SF2 GM 25 | **Warm Core** | `-89..+70` (E2–E5) | `(1.3, 3.3)` | Bright fingerstyle steel strings exposing beatless 5/7-limit overtones vs 12-TET. |
| `pizzicato` | SF2 GM 45 | **Warm Core** | `-53..+70` (C3–E5) | `(1.1, 4.3)` | Crisp plucked pulse for Mozartian lightness (`width: 2.2`). |
| `string_ensemble` | SF2 GM 48 | **Warm Core** | `-53..+84` (C3–G5) | `(0.0, 7.6)` | Wide (`width: 4.8`) lush orchestral bed; supports `swell` (`cresc`/`dim`/`arch`). |
| `tremolo_strings` | SF2 GM 44 | **Warm Core** | `-53..+84` (C3–G5) | `(0.6, 7.9)` | Wide (`width: 4.4`) shimmering Brucknerian/Debussyan string tremolando. |
| `viola` | SF2 GM 41 | **Warm Core** | `-53..+53` (C3–C5) | `(-1.8, 4.5)` | Rich, warm alto inner counterpoint; supports `vibrato` & `swell`. |
| `cello` | SF2 GM 42 | **Warm Core** | `-106..+17` (C2–E4) | `(2.4, 4.1)` | Singing tenor/bass melodies; supports `vibrato` & `slide_from_cents`. |
| `clarinet` | SF2 GM 71 | **Warm Core** | `-36..+70` (E3–E5) | `(-1.2, 5.6)` | Velvety woody voice; use `swell` / `breath_swell: true`. |
| `english_horn` | SF2 GM 69 | **Warm Core** | `-31..+53` (F3–C5) | `(1.4, 5.4)` | Dark, expressive alto double-reed; use `swell` + subtle `vibrato`. |
| `bassoon` | SF2 GM 70 | **Warm Core** | `-106..0` (C2–C4) | `(0.4, 6.4)` | Warm woody bass foundation without contrabass bow buzz; use `breath_swell: true`. |
| `french_horn` | SF2 GM 60 | **Warm Core** | `-75..+31` (G2–G4) | `(2.3, 7.8)` | Noble Beethovenian warmth & glowing mid-register pads; use `swell`. |
| `trombone` | SF2 GM 57 | **Warm Core** | `-89..0` (E2–C4) | `(3.1, 8.5)` | Solemn symphonic brass chorales (`LP 3600 Hz` in `concert_hall.json`); use `swell`. |
| `timpani` | SF2 GM 47 | **Warm Core** | `-106..0` (C2–C4) | `(-2.2, 8.8)` | Exact 53-EDO tuned orchestral timpani strokes & dramatic rolls (`width: 1.2`). |
| `dotara` | Phys. Model | **Indian Color** | `-53..+53` (C3–C5) | `(2.0, 2.8)` | Crisp wooden-plectrum folk lute with goatskin body & sympathetic 12th. |
| `ektara` | Phys. Model | **Indian Color** | `-84..+17` (F2–E4) | `(-0.5, 3.1)` | Warm single-string gourd drone/pulse; supports `meend_cents` (`+12`..`+28`). |
| `sitar` | SF2 GM 104 | **Indian Color** | `-53..+31` (C3–G4) | `(-1.5, 2.7)` | Supports `slide_from_cents` meend glides. **Tip:** `stages/concert_hall.json` applies `warm_lowpass_hz: 2700.0`; stay in C3–G4 and keep slides `<= 40¢` in dense textures. |
| `church_organ` | SF2 GM 19 | **Finisher Only** | `-106..+53` (C2–C5) | `(0.0, 10.4)` | Cathedral pipe power (`stages/concert_hall.json` applies `warm_lowpass_hz: 3500.0`); save for dramatic finale swells rather than continuous accompaniment. |
| `celesta` | SF2 GM 8 | *Caution* | `0..+106` (C4–C6) | `(-3.8, 4.8)` | Bright bell sparkle; can sound toy-like/synthy if overused. |
| `flute` | SF2 GM 73 | *Caution* | `0..+106` (C4–C6) | `(-1.6, 5.4)` | GM preset can sound thin/mechanical; prefer `clarinet` or `english_horn`. |
| `oboe` | SF2 GM 68 | *Caution* | `0..+70` (C4–E5) | `(0.8, 5.4)` | Bright/piercing GM reed; prefer `english_horn` for warmth. |
| `shakuhachi` | SF2 GM 77 | *Caution* | `0..+84` (C4–G5) | `(-0.6, 5.0)` | Heavy breath noise in GM preset; use sparingly if at all. |
| `violin` | SF2 GM 40 | *Caution* | `0..+106` (C4–C6) | `(-2.6, 3.8)` | GM solo violin sounds thin/synthy; prefer `viola` + `string_ensemble`. |
| `contrabass` | SF2 GM 43 | *Caution* | `-128..-31` (G1–F3) | `(3.4, 5.4)` | Growly bow buzz in GM preset; prefer `bassoon` + `cello` for lush bass. |
| `slow_strings` | SF2 GM 49 | *Caution* | `-53..+70` (C3–E5) | `(0.0, 8.2)` | Synthy pad character in GM preset; prefer `string_ensemble`. |

### 3D Concert Stage Geometry (`src/spatial.rs`)

```
                       REAR OF STAGE (y = 11m)
                      [ church_organ (0, 10.4) ]
                  [ french_horn (2.3, 7.8) ]
                   [ string_ensemble (0.0, 7.6) ]
                        [ bassoon (0.4, 6.4) ]
            [ clarinet (-1.2, 5.6) ]   [ english_horn (1.4, 5.4) ]
   [ viola (-1.8, 4.5) ]   [ pizzicato (1.1, 4.3) ]   [ cello (2.4, 4.1) ]
[ harp (-3.4, 3.7) ] [ piano (-2.3, 3.3) ] [ ektara (-0.5, 3.1) ] [ dotara (2.0, 2.8) ]
                        [ sitar (-1.5, 2.7) ]

                           LISTENER (0, 0)
                              facing +y
```

What `spatial::spatialize_track` physically models from `(x, y)`:
- **Distance attenuation:** `(3.8 / dist)^0.42` (clamped `0.58`–`1.12`)
- **Air absorption:** 1-pole low-pass scaling from `19.0 kHz` (close) down to `4.8 kHz` (far)
- **Woodworth ITD:** spherical-head interaural time delay (`a = 8.75 cm`, `c = 343 m/s`)
- **Head-shadow ILD & LP:** far ear attenuated up to `-30%` and low-passed down to `4.5 kHz`
- **Depth-coupled reverb send:** `0.13 + 0.024 * dist` (instruments further back naturally bloom deeper into the hall!)

### Essential Acoustic & Compositional Pitfalls (Agent Checklist)

1. **One coherent harmonic grid per bar:** Never swap incompatible bass roots (e.g. `F2` against a `G` chord), never mix `Bb_harm` (`43`) with `B` (`48`) in the same beat, and never layer a dominant 7th over a pure major triad. Add an automated **consonance validator** in your generator script checking every active note against the bar's chord tones!
2. **No close thirds below `C3` (`step = -53`):** Close intervals (3rds/2nds) in the bass create severe low-frequency roughness even in pure JI. Below `C3`, use roots, octaves (`+53`), and pure fifths (`+31`); voice thirds (`+17`/`+14`), 7ths (`+43`), and 9ths (`+62`) at `C3` and above.
3. **Stop harp/piano arpeggios cleanly before chord changes:** Release arpeggio notes ~0.1–0.2 beats before the next harmony so previous chord tones don't clash across barlines.
4. **Always use `breath_swell: true` and breathing rests on winds & horns:** Sustained notes on `clarinet`, `english_horn`, `bassoon`, and `french_horn` sound dramatically more human with `breath_swell: true` and 0.5–2 beat phrase rests between melodic sentences.
5. **Shape velocities dynamically (`vel`):** Vary `vel` smoothly across phrases (`0.42` pp → `0.68` mp → `0.86` f → `0.48` pp) rather than writing flat `0.75` everywhere.
6. **Respect the 15-voice per-track SF2 channel pool:** Each SF2 track allocates 15 independent pitch-bent channels; keep simultaneous overlapping notes per SF2 track `<= 15` so the oldest voice isn't stolen mid-decay.
7. **Warm up `sitar` and `church_organ` via `stage.json`:** `stages/concert_hall.json` applies `warm_lowpass_hz: 2700.0` on `sitar` and `3500.0` on `church_organ` to smooth GM upper reed/string harshness.
8. **Keep scores stage-independent:** Omit `x`, `y`, `gain`, `warm_lowpass_hz` in `score.json` so anyone can re-stage your composition with `--stage stages/concert_hall.json`, `stages/intimate_circle.json`, or `stages/east_west_split.json`.

---

## 5. Multi-Agent, Stage-Swap & 12-TET Comparison Workflows

Because the musical score is decoupled from both the **stage** and the **tuning system**, you can run clean controlled experiments across agents, rooms, and tunings!

### A. Compare Two AI Agents on the Exact Same Stage

Give a competing AI agent a prompt like:

> Read `docs/SCORE_FORMAT.md` and `scores/example_minimal.json`. Compose an original pure-music 53-EDO classical piece (~2–5 minutes) using the Warm Core orchestra + subtle Indian color (omit inline stage fields so it pairs with `stages/concert_hall.json`). Save the JSON to `scores/agent_b.json`, then render both audio and SVG:
> `cargo run --release -- render scores/agent_b.json output/agent_b.wav --stage stages/concert_hall.json --image output/agent_b.svg`

Render both scores on the identical stage preset:

```bash
# Reference 5-minute showcase
cargo run --release -- render scores/sample_5min.json output/sample_5min.wav \
  --stage stages/concert_hall.json --image output/sample_5min.svg

# Competing agent's composition on the exact same virtual stage
cargo run --release -- render scores/agent_b.json output/agent_b.wav \
  --stage stages/concert_hall.json --image output/agent_b.svg
```

### B. Compare 53-EDO vs 12-TET (or Swap Stages) on the Same Score

```bash
# 53-EDO vs 12-TET A/B comparison (with 30s trailing contemplation silence)
cargo run --release -- render scores/sample_5min.json output/sample_5min.wav \
  --stage stages/concert_hall.json --tuning 53edo --end-silence 30
cargo run --release -- render scores/sample_5min.json output/sample_5min_12tet.wav \
  --stage stages/concert_hall.json --tuning 12tet --end-silence 30

# Re-seat the exact same score in an East-West antiphonal hall or intimate chamber salon
cargo run --release -- render scores/sample_5min.json output/sample_5min_split.wav \
  --stage stages/east_west_split.json --image output/sample_5min_split.svg
cargo run --release -- render scores/sample_5min.json output/sample_5min_circle.wav \
  --stage stages/intimate_circle.json --image output/sample_5min_circle.svg
```

### C. Objective Loudness, Duration & Dynamics Check

```bash
for audio in output/sample_5min.wav output/agent_b.wav; do
  echo "=== $audio ==="
  ffprobe -v error -show_entries format=duration:stream=sample_rate,channels -of default=nw=1 "$audio"
  ffmpeg -hide_banner -nostats -i "$audio" -af "volumedetect" -f null - 2>&1 | grep -E "mean_volume|max_volume"
  ffmpeg -hide_banner -nostats -i "$audio" -af "ebur128=framelog=quiet" -f null - 2>&1 | grep -E "I:|LRA:|True peak:" | tail -n 3
done
```

What to check:
- **Sample rate / format:** `48000 Hz`, 2 channels (stereo), `0` clipped samples, `0` NaNs.
- **Max peak:** `-1.0 dBFS` (clean peak normalization; `--end-silence` does not distort mastering gain).
- **Mean volume / Integrated loudness (`I`):** `-22` to `-14 LUFS` is healthy for dynamic classical music.
- **Loudness Range (`LRA`):** `6–14 LU` confirms genuine dynamic phrasing (`pp` passages vs climaxes).
- **Audition by ear & eye:** Serve the repo root with the built-in Byte-Range server (`python3 scripts/serve_studio.py 8765`, supporting HTTP `206 Partial Content` for smooth audio seeking and `A/B Switch (−10s)`) and open `http://127.0.0.1:8765/audition/` to A/B listen and inspect the generated SVGs & WebM videos!
