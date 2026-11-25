# 53-EDO Classical Music Engine

A pure-Rust **53-EDO (53 Equal Divisions of the Octave)** microtonal classical music renderer combining:

- **Exact 53-EDO Tuning (`A4 = 440 Hz` at step `39`, `C4 = 0`, `OCT = 53`):** Pure 5-limit triads (`[0, 17, 31]` within 1.4¢ of 4:5:6), Debussy 7-limit harmonic ninths (`[0, 17, 31, 43, 62]`), Indian 22-shruti pitches, chromatic-mediant diesis modulations (`+2`), and seamless 5-limit comma pumps (`±1`).
- **19 SoundFont2 Instruments + 2 Physical Models:** 15 dedicated melodic MIDI channels per SF2 track (`rustysynth` + `soundfonts/GeneralUser-GS.sf2`) for collision-free 14-bit pitch bend, CC 11 wind breath swells, and meend glides — paired with physically modeled **Ektara** and **Dotara** in pure Rust (`src/indian.rs`).
- **3D Concert Stage & Hall Reverb:** Physical ITD, head-shadow ILD, air absorption, and depth-coupled reverb sends (`src/spatial.rs`) feeding an 8-channel Walsh-Hadamard FDN chamber hall (`src/reverb.rs`).
- **Agent-Friendly JSON Score Format:** Any human or AI agent can author a JSON score and render mastered 48 kHz WAVs + optional synchronized stems.

---

## Quickstart

```bash
# 1. Render the 8-second minimal example score (defaults to output/example_minimal.wav)
cargo run --release -- render scores/example_minimal.json

# 2. Render the 5-minute 4-movement 53-EDO showcase (+ optional dry stems)
cargo run --release -- render scores/sample_5min.json output/sample_5min.wav --stems-dir output/stems_5min

# 3. Render isolated 53-EDO instrument auditions & 3D stage fusion assets
cargo run --release -- audition

# 4. Run unit & tuning-accuracy tests
cargo test --release
```

### Listen in the Audition & 3D Stage Studio

Start a local static file server from the project root (if not already running):

```bash
python3 -m http.server 8765
```

Then open:
- **Audition & 3D Stage Studio:** [http://127.0.0.1:8765/audition/](http://127.0.0.1:8765/audition/) — audition all 21 instruments in 53-EDO, drag instruments across an interactive 2D concert stage mixer, and play the 5-minute showcase.
- **Direct 5-Minute Showcase WAV:** [http://127.0.0.1:8765/output/sample_5min.wav](http://127.0.0.1:8765/output/sample_5min.wav)

---

## Composing Scores & Multi-Agent Comparison

Want another AI agent (or yourself) to compose a new 53-EDO piece and compare it side-by-side against `output/sample_5min.wav`?

1. Read **[docs/SCORE_FORMAT.md](docs/SCORE_FORMAT.md)** — complete CLI flags, JSON schema, 53-EDO theory cheat sheet, 21-instrument catalog, stage coordinates, and acoustic pitfalls.
2. Copy **[scores/example_minimal.json](scores/example_minimal.json)** as a minimal 8-second starting template.
3. Generate `scores/agent_b.json`, render `output/agent_b.wav`, and compare loudness/dynamics/audio side-by-side using the commands in [docs/SCORE_FORMAT.md §5](docs/SCORE_FORMAT.md#5-multi-agent-composition--side-by-side-comparison-workflow).

---

## Project Layout

| Path | Purpose |
|---|---|
| [docs/SCORE_FORMAT.md](docs/SCORE_FORMAT.md) | Agent-ready JSON score reference, 53-EDO cheat sheet, instrument catalog & multi-agent comparison guide |
| [scores/example_minimal.json](scores/example_minimal.json) | Minimal 8-second 4-track 53-EDO template score |
| [scores/sample_5min.json](scores/sample_5min.json) | 5-minute 4-movement 53-EDO symphony sketch (`output/sample_5min.wav`) |
| [audition/index.html](audition/index.html) | Interactive Audition & 3D Concert Stage web studio |
| [src/score_json.rs](src/score_json.rs) | JSON score parser, optional warm low-pass filter, multi-track renderer & stem exporter |
| [src/tuning.rs](src/tuning.rs) | 53-EDO pitch math, pure 5-limit/7-limit intervals & chord helpers |
| [src/sf2_synth.rs](src/sf2_synth.rs) | 15-channel per-track 14-bit pitch-bent SoundFont2 renderer |
| [src/indian.rs](src/indian.rs) | Physically modeled 53-EDO Ektara & Dotara waveguide synthesizers |
| [src/spatial.rs](src/spatial.rs) | Physical 3D concert-stage spatializer (ITD, head-shadow ILD, air absorption) |
| [src/reverb.rs](src/reverb.rs) | Early reflections + 8-channel Walsh-Hadamard FDN hall reverb & `-1.0 dBFS` master |
