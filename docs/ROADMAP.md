# Musical Chairs — Roadmap & Musical Vision

**Musical Chairs** aims to make **53-EDO microtonal classical composition** both acoustically effortless and unmistakably rewarding to hear — uniting pure just-intonation harmony, physical 3D concert-stage acoustics, and expressive multi-agent composition.

---

## Phase 1 — Engine Polish *(Current)*

Lock down the pure-Rust core renderer and studio tooling so composers and AI agents have a rock-solid, repeatable instrument:

- **Decoupled 2-Input Pipeline:** Pure-music `score.json` paired with reusable 3D concert stages (`stages/concert_hall.json`, `stages/intimate_circle.json`, `stages/east_west_split.json`).
- **Exact 53-EDO + 12-TET A/B Comparison:** 15-channel per-track 14-bit pitch-bent SoundFont2 rendering, pure-Rust physical models (`ektara`, `dotara`), Woodworth ITD/ILD 3D spatialization, 8-channel Walsh-Hadamard FDN hall reverb, intentional `--end-silence`, and instant `--tuning 12tet` comparison with `A/B Switch (−10s)` in the Byte-Range studio UI (`scripts/serve_studio.py`).
- **Visualizers:** Pure-Rust 1600×960 dark-studio SVG score/stage maps (`visualize` / `--image`) and 1080p VP9 + Opus animated WebM concert videos (`render-video`), featuring an upgraded **53-EDO Harmonic Wheel** with `~`-prefixed approximate 12-tone landmarks (`~C`..`~B`), live highlighted active 53-EDO step numbers (`0..52`), and real-time **Pythagorean & Just interval ratio readouts** (`1:1`, `3:2`, `9:8`, `81:64`, `5:4`, `6:5`, `7:4`, `81:80`, etc.).

---

## Phase 2 — Pure Third & Harmonic Seventh 53-EDO Showcase Studies

Create dedicated compositions engineered from bar 1 to highlight **what 53-EDO does dramatically better than 12-TET** — audible immediately on an A/B toggle:

- **Beat-Free Pure Thirds (`5:4 = 17/53`, `6:5 = 14/53`):** Slow, sustained harmonic cradles on lush **String Ensemble**, **Viola**, **Cello**, **French Horn**, **English Horn**, **Clarinet**, **Harp**, and **Cathedral Pipe Organ**, where 12-TET's `+14¢` sharp major thirds and `−16¢` flat minor thirds visibly beat against 53-EDO's glassy stillness.
- **Debussy Harmonic Sevenths & Ninths (`7:4 = 43/53`, `4:5:6:7:9`):** Lingering septimal chords that glow as pure consonances rather than restless dissonances.
- **Immediate Comma Spirals & Diesis Journeys:** Transparent, slow-moving **chromatic-mediant diesis climbs (`+2` steps / `+45.3¢`)** and **5-limit syntonic comma pumps (`±1` step / `±22.6¢`)** placed right in the opening phrases so listeners feel the pitch center lift and resolve across the 53-tone lattice in real time.

---

## Phase 3 — Goal- & Mood-Driven Multi-Agent Compositions

Build a curated library of 53-EDO scores crafted for distinct emotional moods and listening contexts, comparing different compositional approaches and AI agents on identical virtual stages using [docs/SCORE_FORMAT.md](SCORE_FORMAT.md):

- **Melancholic Twilight & Contemplation** — Slow breathing reeds, harp harmonics, and tender minor-6th/septimal shading.
- **Serene Meditative Flow** — Pure 22-shruti East–West drones, Ektara/Dotara pulses, and unhurried harmonic blooms.
- **Pastoral Luminosity** — Mozartian clarity, buoyant pizzicato/woodwind counterpoint, and sunlit 5-limit triads.
- **Beethovenian Dramatic Arcs** — Motivic development, surging brass/strings across comma modulations, and cathartic resolutions.

---

## Phase 4 — Full 15-Minute Multi-Movement East–West Symphony

Scale the refined 5-minute *Harmonia Mundi* blueprint into a **full 15-minute multi-movement concert symphony** in 53-EDO — expanding thematic architecture, contrapuntal development, antiphonal East–West dialogue, and large-scale comma/diesis tonal architecture with synchronized stems, poster artwork, and 1080p animated concert video.

---

## Phase 5 — Sheet Music & DAW Export *(Future)*

Bridge the engine outward to external production tools and live human performers:

- **DAW / VST Interoperability:** Export **MPE `.mid`** (MIDI Polyphonic Expression with per-note 14-bit pitch bend) alongside **Scala `.scl` / `.kbm`** tuning files so any `score.json` can drive high-end orchestral VST libraries and hardware synths.
- **Human-Readable Microtonal Notation:** Export **microtonal `.musicxml`** and **LilyPond (`.ly`)** scores with Helmholtz-Ellis / Sagittal comma accidentals so live chamber musicians can read and perform the scores.
