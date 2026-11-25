# 53-EDO JSON Score Format & Agent Authoring Guide

This guide is a self-contained specification for **AI agents and human composers** authoring microtonal classical music in **53-EDO (53 Equal Divisions of the Octave)** for the pure-Rust renderer in this repository.

Hand this file (plus [scores/example_minimal.json](../scores/example_minimal.json)) to any AI agent to let it compose a valid 53-EDO score, render it to 48 kHz stereo WAV + synced stems, and compare results side-by-side.

---

## 1. Quickstart CLI Commands

All commands run from the repository root (`/home/deck/projects/music`). The project requires `soundfonts/GeneralUser-GS.sf2` and compiles with pure Rust (`x86_64-unknown-linux-musl` via `.cargo/config.toml`).

```bash
# Render a JSON score (output defaults to output/<input_stem>.wav if omitted)
cargo run --release -- render scores/example_minimal.json
cargo run --release -- render scores/example_minimal.json output/example_minimal.wav

# Render a JSON score AND export synchronized centered dry stems (<dir>/<track.id>.wav)
cargo run --release -- render scores/sample_5min.json output/sample_5min.wav --stems-dir output/stems_5min

# Override the SoundFont2 file (default: soundfonts/GeneralUser-GS.sf2)
cargo run --release -- render scores/example_minimal.json output/example_minimal.wav --soundfont path/to/custom.sf2

# Render all isolated 53-EDO instrument auditions, 53-note harp sweep, & fusion showcase
cargo run --release -- audition

# Render the pure-Rust additive/physical-model synth preview (no SoundFont)
cargo run --release -- preview-synth

# Run the full test suite (tuning accuracy, JSON parsing, zero-NaN / zero-clip rendering)
cargo test --release
```

CLI flags accept both space-separated (`--stems-dir dir`) and `=` (`--stems-dir=dir`) forms. Every `render` invocation prints a verification summary to stdout:
- Score title, description, duration, sample rate, track count, total note count, tail, and Hall RT60
- Per-track note count, stage coordinates `(x, y)`, gain, and optional low-pass cutoff
- Stems summary (when `--stems-dir` is set)
- Mastering stats: `Peak dBFS`, `RMS L/R dBFS`, `Clipped` sample count (must be `0`), and `NaNs` (must be `0`)

---

## 2. Complete JSON Score Schema

### Full Annotated Example

```json
{
  "title": "Luminous 53-EDO Miniature",
  "description": "Short multi-track 53-EDO demonstration.",
  "sample_rate": 48000,
  "tail_seconds": 3.0,
  "reverb_rt60": 2.25,
  "tempo": [
    { "beat": 0.0, "bpm": 90.0 },
    { "beat": 8.0, "bpm": 84.0 }
  ],
  "tracks": [
    {
      "id": "english_horn",
      "name": "English Horn",
      "instrument": "english_horn",
      "x": 1.4,
      "y": 4.8,
      "gain": 0.88,
      "warm_lowpass_hz": null,
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

### Top-Level Fields

| Field | Type | Required | Default | Range / Notes |
|---|---|---|---|---|
| `title` | `string` | No | `"Untitled 53-EDO Piece"` | Human-readable composition title printed in CLI summary. |
| `description` | `string` | No | `""` | Free-form notes (movement outline, tuning notes, agent metadata). |
| `sample_rate` | `integer` | No | `48000` | Output sample rate in Hz (`8000`–`192000`). **Keep at `48000`** for native physical-model rendering without resampling. |
| `tail_seconds` | `number` | No | `4.5` | Extra reverb/release tail appended after the final note ends (`>= 0.0`; `2.5`–`6.0` recommended). |
| `reverb_rt60` | `number` | No | `2.25` | Concert hall 8-channel Walsh-Hadamard FDN RT60 decay time in seconds (`>= 0.0`; `1.2`–`3.5` typical, `2.25` = warm chamber hall). |
| `tempo` | `TempoPoint[]` | No | `[{"beat": 0.0, "bpm": 70.0}]` | Non-empty piecewise-linear BPM map (see below). |
| `tracks` | `Track[]` | **Yes** | — | Array of instrument tracks (rendered in parallel across CPU threads). |

### `TempoPoint` Object (`tempo[]`)

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `beat` | `number` | **Yes** | — | Musical beat position (`>= 0.0`). Segments are sorted ascending by `beat`. |
| `bpm` | `number` | **Yes** | — | Tempo in beats per minute (`> 0.0`, typically `48.0`–`120.0`). |

**How `TempoMap` interpolates:** Between consecutive points `(b1, bpm1)` and `(b2, bpm2)`, BPM changes **linearly** with exact analytical logarithmic time integration (`src/score.rs`).
- For a **constant tempo** across beats `0..64`, repeat the BPM: `{"beat": 0.0, "bpm": 72.0}, {"beat": 64.0, "bpm": 72.0}`.
- For a **smooth ritardando / accelerando** across beats `60..64`, set `{"beat": 60.0, "bpm": 72.0}, {"beat": 64.0, "bpm": 60.0}`.
- For an **abrupt tempo jump** at beat `64`, place a tiny step: `{"beat": 63.999, "bpm": 72.0}, {"beat": 64.0, "bpm": 80.0}`.

### `Track` Object (`tracks[]`)

| Field | Type | Required | Default | Range / Notes |
|---|---|---|---|---|
| `id` | `string` | **Yes** | — | Unique non-empty slug with no path separators (`/`, `\`, `..`). Used as stem filename `<stems-dir>/<id>.wav`. |
| `name` | `string \| null` | No | `id` | Display name for logs/UI. |
| `instrument` | `string` | **Yes** | — | Must be one of the 21 supported instrument IDs in Section 4. |
| `x` | `number` | No | `0.0` | Stage horizontal position in meters (`-6.0` far left to `+6.0` far right). |
| `y` | `number` | No | `4.5` | Stage depth in meters (`2.0` front to `14.0` rear). Listener is at `(0, 0)` facing `+y`. |
| `gain` | `number` | No | `1.0` | Linear track mix gain (`>= 0.0`, `0.4`–`1.2` typical) applied after optional low-pass and before spatialization. |
| `warm_lowpass_hz` | `number \| null` | No | `null` | Optional 2-pole Butterworth low-pass cutoff in Hz (`> 0.0`, clamped internally to `[40, 0.45*sr]`) applied to L/R before spatialization. Ideal for warming bright GM presets (e.g. `2800.0`–`3200.0` for `sitar`). |
| `notes` | `Note[]` | No | `[]` | Array of note events on this track. |

### `Note` Object (`tracks[].notes[]`)

| Field | Type | Required | Default | Range / Notes |
|---|---|---|---|---|
| `beat` | `number` | **Yes** | — | Note onset time in musical beats (`>= 0.0`). |
| `dur` | `number` | **Yes** | — | Note duration in musical beats (`> 0.0`). |
| `step` | `integer` | **Yes** | — | **53-EDO pitch step**, where **`C4 = 0`**, **`A4 = 39` (440 Hz)**, **`OCT = 53`**. |
| `vel` | `number` | No | `0.75` | Normalized velocity (`0.05`–`1.0`). Shape dynamically (`0.40`–`0.92`) for musical phrasing. |
| `cents` | `number` | No | `0.0` | Extra fine microtonal pitch offset in cents added on top of `step`. |
| `slide_from_cents` | `number` | No | `0.0` | **SF2 instruments** (also accepted as fallback by `ektara`). Smooth 140 ms quadratic pitch-bend glide *from* `step + cents + slide_from_cents` *into* `step + cents`. Negative slides up; positive slides down. Keep within `[-150, +150]` (clamped at `±195` cents). |
| `breath_swell` | `boolean` | No | `false` | **SF2 instruments only.** Applies a smooth MIDI CC 11 expression arch (`82 → 124 → 82`) on notes longer than ~50 ms. Set `true` on winds & brass (`clarinet`, `english_horn`, `bassoon`, `french_horn`). |
| `meend_cents` | `number` | No | `0.0` | **`ektara` physical model** (also accepted as fallback by SF2 slides). Initial elastic pitch-relaxation offset in cents (exponential decay, τ = 110 ms) into `step`. Positive (`+12` to `+28`) gives authentic gourd-string pluck relaxation. |

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

All **21 supported `instrument` IDs** are rendered with exact 53-EDO tuning:
- **19 SoundFont2 instruments** (`GeneralUser-GS.sf2` via `rustysynth`): each track gets **15 dedicated melodic MIDI channels** (channels 0–8, 10–15) with ±2-semitone 14-bit pitch bend so chords never collide in pitch bend, and SF2 chorus/reverb are disabled so 53-EDO intervals stay acoustically pure.
- **2 Pure-Rust Physical Models** (`src/indian.rs`): Karplus-Strong waveguide models with cubic fractional delay, body formants, and exact 53-EDO pitch (`ektara`, `dotara`).

### Full 21-Instrument Catalog

| `instrument` ID | Engine | Tier | Sweet-Spot Steps (Pitch) | Rec. Stage `(x, y)` | Features & Acoustic Notes |
|---|---|---|---|---|---|
| `piano` | SF2 GM 0 | **Warm Core** | `-106..+92` (C2–A5) | `(-2.4, 3.4)` | Crisp Mozartian clarity & rich chords; user favorite. |
| `harp` | SF2 GM 46 | **Warm Core** | `-84..+106` (F2–C6) | `(-3.2, 3.2)` | Silky full 53-EDO arpeggios & harmonic sweeps; avoid letting chords bleed across changes. |
| `pizzicato` | SF2 GM 45 | **Warm Core** | `-53..+70` (C3–E5) | `(0.8, 4.8)` | Crisp plucked pulse for Mozartian lightness. |
| `string_ensemble` | SF2 GM 48 | **Warm Core** | `-53..+84` (C3–G5) | `(0.0, 7.4)` | Lush full-orchestra sustained bed; gorgeous for pure 5-limit/7-limit swells. |
| `viola` | SF2 GM 41 | **Warm Core** | `-53..+53` (C3–C5) | `(-2.2, 4.4)` | Rich, warm alto inner counterpoint; far smoother than GM solo violin. |
| `cello` | SF2 GM 42 | **Warm Core** | `-106..+17` (C2–E4) | `(2.6, 4.2)` | Singing tenor/bass melodies and warm harmonic anchor. |
| `clarinet` | SF2 GM 71 | **Warm Core** | `-36..+70` (E3–E5) | `(-1.2, 5.8)` | Velvety woody voice; use `breath_swell: true`. |
| `english_horn` | SF2 GM 69 | **Warm Core** | `-31..+53` (F3–C5) | `(1.4, 4.8)` | Dark, expressive alto double-reed; user favorite — use `breath_swell: true`. |
| `bassoon` | SF2 GM 70 | **Warm Core** | `-106..0` (C2–C4) | `(0.5, 6.6)` | Warm woody bass foundation without contrabass bow buzz; use `breath_swell: true`. |
| `french_horn` | SF2 GM 60 | **Warm Core** | `-75..+31` (G2–G4) | `(2.2, 8.2)` | Noble Beethovenian warmth & glowing mid-register pads; use `breath_swell: true`. |
| `dotara` | Phys. Model | **Indian Color** | `-53..+53` (C3–C5) | `(1.8, 2.8)` | Crisp wooden-plectrum folk lute with goatskin body & sympathetic 12th. |
| `ektara` | Phys. Model | **Indian Color** | `-84..+17` (F2–E4) | `(-0.4, 3.4)` | Warm single-string gourd drone/pulse; supports `meend_cents` (`+12`..`+28`). |
| `sitar` | SF2 GM 104 | **Indian Color** | `-53..+31` (C3–G4) | `(-1.6, 2.6)` | Supports `slide_from_cents` meend glides. **Tip:** set `warm_lowpass_hz: 2800.0`, stay in C3–G4, and keep slides `<= 40¢` in dense textures so it stays silky, not sharp. |
| `church_organ` | SF2 GM 19 | **Finisher Only** | `-106..+53` (C2–C5) | `(0.0, 10.5)` | Cathedral pipe power with slight GM reed edge; save for dramatic finale swells rather than continuous accompaniment. |
| `celesta` | SF2 GM 8 | *Caution* | `0..+106` (C4–C6) | `(1.8, 3.8)` | Bright bell sparkle; can sound toy-like/synthy if overused. |
| `flute` | SF2 GM 73 | *Caution* | `0..+106` (C4–C6) | `(-0.8, 5.4)` | GM preset can sound thin/mechanical; prefer `clarinet` or `english_horn`. |
| `oboe` | SF2 GM 68 | *Caution* | `0..+70` (C4–E5) | `(0.8, 5.4)` | Bright/piercing GM reed; prefer `english_horn` for warmth. |
| `shakuhachi` | SF2 GM 77 | *Caution* | `0..+84` (C4–G5) | `(-1.4, 4.6)` | Heavy breath noise in GM preset; use sparingly if at all. |
| `violin` | SF2 GM 40 | *Caution* | `0..+106` (C4–C6) | `(-2.8, 3.6)` | GM solo violin sounds thin/synthy; prefer `viola` + `string_ensemble`. |
| `contrabass` | SF2 GM 43 | *Caution* | `-128..-31` (G1–F3) | `(3.2, 6.4)` | Growly bow buzz in GM preset; prefer `bassoon` + `cello` for lush bass. |
| `slow_strings` | SF2 GM 49 | *Caution* | `-53..+70` (C3–E5) | `(0.0, 8.0)` | Synthy pad character in GM preset; prefer `string_ensemble`. |

### 3D Concert Stage Geometry (`src/spatial.rs`)

```
                       REAR OF STAGE (y = 11m)
                      [ church_organ (0, 10.5) ]
                  [ french_horn (2.2, 8.2) ]
                   [ string_ensemble (0.0, 7.4) ]
                        [ bassoon (0.5, 6.6) ]
            [ clarinet (-1.2, 5.8) ]   [ english_horn (1.4, 4.8) ]
   [ viola (-2.2, 4.4) ]   [ pizzicato (0.8, 4.8) ]   [ cello (2.6, 4.2) ]
[ harp (-3.2, 3.2) ] [ piano (-2.4, 3.4) ] [ ektara (-0.4, 3.4) ] [ dotara (1.8, 2.8) ]
                        [ sitar (-1.6, 2.6) ]

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

1. **One coherent harmonic grid per bar:** Never swap incompatible bass roots (e.g. `F2` against a `G` chord), never mix `Bb_harm` (`43`) with `B` (`48`) in the same beat, and never layer a dominant 7th over a pure major triad. When writing a Python generator, add an automated **consonance validator** checking every active note against the bar's chord tones!
2. **No close thirds below `C3` (`step = -53`):** Close intervals (3rds/2nds) in the bass create severe low-frequency acoustic roughness even in pure JI. Below `C3`, use roots, octaves (`+53`), and pure fifths (`+31`); voice thirds (`+17`/`+14`), 7ths (`+43`), and 9ths (`+62`) at `C3` and above.
3. **Stop harp/piano arpeggios cleanly before chord changes:** Release arpeggio notes ~0.1–0.2 beats before the next harmony so previous chord tones don't clash across barlines.
4. **Always use `breath_swell: true` and breathing rests on winds & horns:** Sustained notes on `clarinet`, `english_horn`, `bassoon`, and `french_horn` sound dramatically more human with `breath_swell: true` and 0.5–2 beat phrase rests between melodic sentences.
5. **Shape velocities dynamically (`vel`):** Vary `vel` smoothly across phrases (`0.42` pp → `0.68` mp → `0.86` f → `0.48` pp) rather than writing flat `0.75` everywhere.
6. **Respect the 15-voice per-track SF2 channel pool:** Each SF2 track allocates 15 independent pitch-bent channels; keep simultaneous overlapping notes per SF2 track `<= 15` so the oldest voice isn't stolen mid-decay.
7. **Warm up `sitar` if used:** Set `"warm_lowpass_hz": 2800.0` on the sitar track, stay in C3–G4 (`-53..+31`), and keep `slide_from_cents` gentle (`<= 40` cents) inside orchestral textures.
8. **Balance track `gain` (`0.60`–`1.05`):** The master bus applies a soft-knee limiter above `0.85` and peak-normalizes the final stereo mix to `-1.0 dBFS`. Keep soloist tracks slightly higher (`0.85`–`1.00`) and pads/drones slightly lower (`0.60`–`0.82`).

---

## 5. Multi-Agent Composition & Side-by-Side Comparison Workflow

This engine was specifically built so you can hand `docs/SCORE_FORMAT.md` to **any other AI agent** (Claude, GPT, Gemini, Codex, etc.), let it compose its own 53-EDO score, render both pieces through the exact same acoustic engine, and compare them objectively and by ear!

### Step 1 — Prompt Another Agent

Give the competing agent a prompt like:

> Read `docs/SCORE_FORMAT.md` and `scores/example_minimal.json` in `/home/deck/projects/music`. Compose an original 53-EDO classical piece (~2–5 minutes) using the Warm Core orchestra + subtle Indian color. Write a Python generator or JSON directly to `scores/agent_b.json` conforming strictly to the schema, then render it with:
> `cargo run --release -- render scores/agent_b.json output/agent_b.wav --stems-dir output/stems_agent_b`

### Step 2 — Render Both Scores Through the Same Engine

```bash
# Reference 5-minute showcase
cargo run --release -- render scores/sample_5min.json output/sample_5min.wav --stems-dir output/stems_5min

# Competing agent's composition
cargo run --release -- render scores/agent_b.json output/agent_b.wav --stems-dir output/stems_agent_b
```

### Step 3 — Compare Loudness, Duration & Dynamics Side-by-Side

```bash
for wav in output/sample_5min.wav output/agent_b.wav; do
  echo "=== $wav ==="
  ffprobe -v error -show_entries format=duration:stream=sample_rate,channels -of default=nw=1 "$wav"
  ffmpeg -hide_banner -nostats -i "$wav" -af "volumedetect" -f null - 2>&1 | grep -E "mean_volume|max_volume"
  ffmpeg -hide_banner -nostats -i "$wav" -af "ebur128=framelog=quiet" -f null - 2>&1 | grep -E "I:|LRA:|True peak:" | tail -n 3
done
```

What to look for when comparing two 53-EDO renders:
- **Sample rate / format:** `48000 Hz`, 2 channels (stereo), `0` clipped samples, `0` NaNs.
- **Max peak:** `-1.0 dBFS` (confirming clean peak normalization with zero clipping).
- **Mean volume / Integrated loudness (`I`):** `-22` to `-14 LUFS` is healthy for dynamic classical music.
- **Loudness Range (`LRA`):** `6–14 LU` indicates real musical contrast (pp passages vs climaxes) rather than flat compression.
- **Audition by ear:** Serve the repo root locally (`python3 -m http.server 8765`) and listen side-by-side at `http://127.0.0.1:8765/audition/` or directly via `http://127.0.0.1:8765/output/sample_5min.wav` vs `http://127.0.0.1:8765/output/agent_b.wav`.
