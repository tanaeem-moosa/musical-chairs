//! Real sampled SoundFont2 synthesizer tuned to exact 53-EDO via 14-bit per-channel pitch bend,
//! with smooth meend pitch glides, directional CC 11 phrasing swells, delayed CC 1 vibrato,
//! CC 64 damper pedal spans, and natural stereo register spread for ensemble sections.

use std::f64::consts::PI;
use std::fs::File;
use std::path::Path;
use std::sync::Arc;

use rustysynth::{SoundFont, Synthesizer, SynthesizerSettings};

use crate::reverb::{apply_hall_reverb_and_master, AudioStats};
use crate::synth::SAMPLE_RATE;
use crate::tuning::{edo53_to_12tet_midi, step_cents_to_freq, OCT};

pub const DEFAULT_SOUNDFONT_PATH: &str = "soundfonts/GeneralUser-GS.sf2";

/// 15 melodic MIDI channels (skipping General MIDI percussion channel 9).
const MELODIC_CHANNELS: [i32; 15] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15];

/// Directional MIDI CC 11 expression phrasing curve applied across a note's duration.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Default)]
pub enum SwellCurve {
    #[default]
    None,
    /// Symmetric human breath/bow arch (`82 -> 124 -> 82`).
    Arch,
    /// Smooth crescendo (`68 -> 126`).
    Cresc,
    /// Smooth diminuendo / taper (`125 -> 68`).
    Dim,
    /// Beethovenian sforzando-piano-bloom (`127 -> 80 -> 114`).
    Sfz,
}

impl SwellCurve {
    pub fn parse(swell_str: Option<&str>, breath_swell_flag: bool) -> Result<Self, String> {
        match swell_str {
            Some(raw) => match raw.trim().to_ascii_lowercase().as_str() {
                "none" | "" => Ok(Self::None),
                "arch" | "swell" | "breath" => Ok(Self::Arch),
                "cresc" | "crescendo" => Ok(Self::Cresc),
                "dim" | "diminuendo" | "decresc" => Ok(Self::Dim),
                "sfz" | "fp" | "sforzando" => Ok(Self::Sfz),
                other => Err(format!(
                    "Unknown note swell curve `{other}`. Supported: `none`, `arch`, `cresc`, `dim`, `sfz`"
                )),
            },
            None => Ok(if breath_swell_flag {
                Self::Arch
            } else {
                Self::None
            }),
        }
    }

    #[inline]
    fn initial_cc11(self) -> i32 {
        match self {
            Self::None => 115,
            Self::Arch => 82,
            Self::Cresc => 68,
            Self::Dim => 125,
            Self::Sfz => 127,
        }
    }

    #[inline]
    fn eval_cc11(self, u: f64) -> i32 {
        let u = u.clamp(0.0, 1.0);
        let val: f64 = match self {
            Self::None => 115.0,
            Self::Arch => 82.0 + 42.0 * (PI * u.powf(0.85)).sin(),
            Self::Cresc => 68.0 + 58.0 * u.powf(0.82),
            Self::Dim => 125.0 - 57.0 * u.powf(0.78),
            Self::Sfz => {
                if u < 0.16 {
                    let t = u / 0.16;
                    127.0 - 47.0 * t
                } else {
                    let t = (u - 0.16) / 0.84;
                    80.0 + 34.0 * t.powf(0.75)
                }
            }
        };
        val.round().clamp(60.0, 127.0) as i32
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Sf2Instrument {
    Piano,
    Celesta,
    ChurchOrgan,
    Harp,
    Flute,
    Clarinet,
    Oboe,
    EnglishHorn,
    Bassoon,
    Shakuhachi,
    FrenchHorn,
    Trombone,
    Violin,
    Viola,
    Cello,
    Contrabass,
    StringEnsemble,
    TremoloStrings,
    SlowStrings,
    Pizzicato,
    Timpani,
    Sitar,
}

impl Sf2Instrument {
    pub fn all() -> &'static [Sf2Instrument] {
        &[
            Sf2Instrument::Harp,
            Sf2Instrument::Sitar,
            Sf2Instrument::Clarinet,
            Sf2Instrument::EnglishHorn,
            Sf2Instrument::Bassoon,
            Sf2Instrument::Shakuhachi,
            Sf2Instrument::FrenchHorn,
            Sf2Instrument::Trombone,
            Sf2Instrument::Viola,
            Sf2Instrument::Cello,
            Sf2Instrument::StringEnsemble,
            Sf2Instrument::TremoloStrings,
            Sf2Instrument::Pizzicato,
            Sf2Instrument::Timpani,
            Sf2Instrument::Piano,
            Sf2Instrument::Celesta,
            Sf2Instrument::Flute,
            Sf2Instrument::Oboe,
            Sf2Instrument::Violin,
            Sf2Instrument::Contrabass,
            Sf2Instrument::SlowStrings,
            Sf2Instrument::ChurchOrgan,
        ]
    }

    pub fn id(self) -> &'static str {
        match self {
            Sf2Instrument::Piano => "piano",
            Sf2Instrument::Celesta => "celesta",
            Sf2Instrument::ChurchOrgan => "church_organ",
            Sf2Instrument::Harp => "harp",
            Sf2Instrument::Flute => "flute",
            Sf2Instrument::Clarinet => "clarinet",
            Sf2Instrument::Oboe => "oboe",
            Sf2Instrument::EnglishHorn => "english_horn",
            Sf2Instrument::Bassoon => "bassoon",
            Sf2Instrument::Shakuhachi => "shakuhachi",
            Sf2Instrument::FrenchHorn => "french_horn",
            Sf2Instrument::Trombone => "trombone",
            Sf2Instrument::Violin => "violin",
            Sf2Instrument::Viola => "viola",
            Sf2Instrument::Cello => "cello",
            Sf2Instrument::Contrabass => "contrabass",
            Sf2Instrument::StringEnsemble => "string_ensemble",
            Sf2Instrument::TremoloStrings => "tremolo_strings",
            Sf2Instrument::SlowStrings => "slow_strings",
            Sf2Instrument::Pizzicato => "pizzicato",
            Sf2Instrument::Timpani => "timpani",
            Sf2Instrument::Sitar => "sitar",
        }
    }

    pub fn from_id(id: &str) -> Option<Self> {
        match id {
            "piano" => Some(Sf2Instrument::Piano),
            "celesta" => Some(Sf2Instrument::Celesta),
            "church_organ" => Some(Sf2Instrument::ChurchOrgan),
            "harp" => Some(Sf2Instrument::Harp),
            "flute" => Some(Sf2Instrument::Flute),
            "clarinet" => Some(Sf2Instrument::Clarinet),
            "oboe" => Some(Sf2Instrument::Oboe),
            "english_horn" => Some(Sf2Instrument::EnglishHorn),
            "bassoon" => Some(Sf2Instrument::Bassoon),
            "shakuhachi" => Some(Sf2Instrument::Shakuhachi),
            "french_horn" => Some(Sf2Instrument::FrenchHorn),
            "trombone" => Some(Sf2Instrument::Trombone),
            "violin" => Some(Sf2Instrument::Violin),
            "viola" => Some(Sf2Instrument::Viola),
            "cello" => Some(Sf2Instrument::Cello),
            "contrabass" => Some(Sf2Instrument::Contrabass),
            "string_ensemble" => Some(Sf2Instrument::StringEnsemble),
            "tremolo_strings" => Some(Sf2Instrument::TremoloStrings),
            "slow_strings" => Some(Sf2Instrument::SlowStrings),
            "pizzicato" => Some(Sf2Instrument::Pizzicato),
            "timpani" => Some(Sf2Instrument::Timpani),
            "sitar" => Some(Sf2Instrument::Sitar),
            _ => None,
        }
    }

    pub fn name(self) -> &'static str {
        match self {
            Sf2Instrument::Piano => "Concert Grand Piano",
            Sf2Instrument::Celesta => "Celesta",
            Sf2Instrument::ChurchOrgan => "Church Pipe Organ",
            Sf2Instrument::Harp => "Orchestral Harp",
            Sf2Instrument::Flute => "Orchestral Flute",
            Sf2Instrument::Clarinet => "Clarinet",
            Sf2Instrument::Oboe => "Oboe",
            Sf2Instrument::EnglishHorn => "English Horn",
            Sf2Instrument::Bassoon => "Bassoon",
            Sf2Instrument::Shakuhachi => "Bamboo Flute (Shakuhachi)",
            Sf2Instrument::FrenchHorn => "French Horn",
            Sf2Instrument::Trombone => "Orchestral Trombone",
            Sf2Instrument::Violin => "Solo Violin",
            Sf2Instrument::Viola => "Solo Viola",
            Sf2Instrument::Cello => "Solo Cello",
            Sf2Instrument::Contrabass => "Contrabass",
            Sf2Instrument::StringEnsemble => "String Ensemble",
            Sf2Instrument::TremoloStrings => "Tremolo Strings",
            Sf2Instrument::SlowStrings => "Slow Lush Strings",
            Sf2Instrument::Pizzicato => "Pizzicato Strings",
            Sf2Instrument::Timpani => "Orchestral Timpani",
            Sf2Instrument::Sitar => "Sitar",
        }
    }

    pub fn family(self) -> &'static str {
        match self {
            Sf2Instrument::Piano | Sf2Instrument::Celesta | Sf2Instrument::Harp => "Keys & Plucked",
            Sf2Instrument::Sitar => "Indian Classical",
            Sf2Instrument::ChurchOrgan => "Organ",
            Sf2Instrument::Flute
            | Sf2Instrument::Clarinet
            | Sf2Instrument::Oboe
            | Sf2Instrument::EnglishHorn
            | Sf2Instrument::Bassoon => "Woodwinds",
            Sf2Instrument::Shakuhachi => "Woodwinds & World",
            Sf2Instrument::FrenchHorn | Sf2Instrument::Trombone => "Brass",
            Sf2Instrument::Timpani => "Percussion",
            Sf2Instrument::Violin
            | Sf2Instrument::Viola
            | Sf2Instrument::Cello
            | Sf2Instrument::Contrabass
            | Sf2Instrument::StringEnsemble
            | Sf2Instrument::TremoloStrings
            | Sf2Instrument::SlowStrings
            | Sf2Instrument::Pizzicato => "Strings",
        }
    }

    pub fn gm_program(self) -> i32 {
        match self {
            Sf2Instrument::Piano => 0,
            Sf2Instrument::Celesta => 8,
            Sf2Instrument::ChurchOrgan => 19,
            Sf2Instrument::Harp => 46,
            Sf2Instrument::Flute => 73,
            Sf2Instrument::Clarinet => 71,
            Sf2Instrument::Oboe => 68,
            Sf2Instrument::EnglishHorn => 69,
            Sf2Instrument::Bassoon => 70,
            Sf2Instrument::Shakuhachi => 77,
            Sf2Instrument::FrenchHorn => 60,
            Sf2Instrument::Trombone => 57,
            Sf2Instrument::Violin => 40,
            Sf2Instrument::Viola => 41,
            Sf2Instrument::Cello => 42,
            Sf2Instrument::Contrabass => 43,
            Sf2Instrument::StringEnsemble => 48,
            Sf2Instrument::TremoloStrings => 44,
            Sf2Instrument::SlowStrings => 49,
            Sf2Instrument::Pizzicato => 45,
            Sf2Instrument::Timpani => 47,
            Sf2Instrument::Sitar => 104,
        }
    }

    pub fn pan(self) -> i32 {
        match self {
            Sf2Instrument::Piano => 54,
            Sf2Instrument::Celesta => 82,
            Sf2Instrument::ChurchOrgan => 64,
            Sf2Instrument::Harp => 42,
            Sf2Instrument::Flute => 56,
            Sf2Instrument::Clarinet => 74,
            Sf2Instrument::Oboe => 60,
            Sf2Instrument::EnglishHorn => 70,
            Sf2Instrument::Bassoon => 76,
            Sf2Instrument::Shakuhachi => 52,
            Sf2Instrument::FrenchHorn => 48,
            Sf2Instrument::Trombone => 76,
            Sf2Instrument::Violin => 36,
            Sf2Instrument::Viola => 78,
            Sf2Instrument::Cello => 92,
            Sf2Instrument::Contrabass => 72,
            Sf2Instrument::StringEnsemble => 64,
            Sf2Instrument::TremoloStrings => 64,
            Sf2Instrument::SlowStrings => 70,
            Sf2Instrument::Pizzicato => 50,
            Sf2Instrument::Timpani => 52,
            Sf2Instrument::Sitar => 46,
        }
    }

    pub fn base_step_offset(self) -> i32 {
        match self {
            Sf2Instrument::Celesta
            | Sf2Instrument::Flute
            | Sf2Instrument::Shakuhachi
            | Sf2Instrument::Violin => OCT,
            Sf2Instrument::ChurchOrgan
            | Sf2Instrument::Bassoon
            | Sf2Instrument::FrenchHorn
            | Sf2Instrument::Trombone
            | Sf2Instrument::Cello => -OCT,
            Sf2Instrument::Contrabass | Sf2Instrument::Timpani => -2 * OCT,
            _ => 0,
        }
    }

    pub fn register_label(self) -> &'static str {
        match self {
            Sf2Instrument::Piano => "C4–G5",
            Sf2Instrument::Celesta => "C5–G6",
            Sf2Instrument::ChurchOrgan => "C3–G4",
            Sf2Instrument::Harp => "C4–G5",
            Sf2Instrument::Flute => "C5–G6",
            Sf2Instrument::Clarinet => "C4–G5",
            Sf2Instrument::Oboe => "C4–G5",
            Sf2Instrument::EnglishHorn => "C4–G5",
            Sf2Instrument::Bassoon => "C3–G4",
            Sf2Instrument::Shakuhachi => "C5–G6",
            Sf2Instrument::FrenchHorn => "C3–G4",
            Sf2Instrument::Trombone => "E2–C4",
            Sf2Instrument::Violin => "C5–G6",
            Sf2Instrument::Viola => "C4–G5",
            Sf2Instrument::Cello => "C3–G4",
            Sf2Instrument::Contrabass => "C2–G3",
            Sf2Instrument::StringEnsemble => "C4–G5",
            Sf2Instrument::TremoloStrings => "C3–G5",
            Sf2Instrument::SlowStrings => "C4–G5",
            Sf2Instrument::Pizzicato => "C4–G5",
            Sf2Instrument::Timpani => "C2–C4",
            Sf2Instrument::Sitar => "C4–G5",
        }
    }

    pub fn role_desc(self) -> &'static str {
        match self {
            Sf2Instrument::Piano => "Warm Mozartian clarity, damper pedal bloom, and full voicings",
            Sf2Instrument::Celesta => "Bell-like Debussy sparkle on upper 7-limit extensions",
            Sf2Instrument::ChurchOrgan => "Cathedral pipe anchor (warmed at 3500 Hz LP on stage)",
            Sf2Instrument::Harp => "Silky arpeggios and full 53-EDO harmonic sweeps",
            Sf2Instrument::Flute => "Upper lyric melody",
            Sf2Instrument::Clarinet => "Velvety woody alto/tenor voice and warm inner lines",
            Sf2Instrument::Oboe => "Bright double-reed classical solo voice",
            Sf2Instrument::EnglishHorn => "Warm, dark, velvety alto double-reed solo voice",
            Sf2Instrument::Bassoon => "Smooth, warm woody bass foundation (no growly bow buzz)",
            Sf2Instrument::Shakuhachi => "Breathy organic bamboo flute alternative to orchestral flute",
            Sf2Instrument::FrenchHorn => "Noble Beethovenian warmth and glowing mid-register pads",
            Sf2Instrument::Trombone => "Solemn symphonic low-mid brass chorales and noble pedals",
            Sf2Instrument::Violin => "Solo violin lead",
            Sf2Instrument::Viola => "Rich, warm inner counterpoint voice",
            Sf2Instrument::Cello => "Deep singing tenor/bass melodies and rhythmic pulse",
            Sf2Instrument::Contrabass => "Bowed orchestral contrabass",
            Sf2Instrument::StringEnsemble => "Wide lush orchestral string bed for pure 5/7-limit swells",
            Sf2Instrument::TremoloStrings => "Shimmering orchestral string tremolando for mist and drama",
            Sf2Instrument::SlowStrings => "Soft, slow-attack legato string pad",
            Sf2Instrument::Pizzicato => "Crisp plucked string articulation for Mozartian lightness",
            Sf2Instrument::Timpani => "Exact 53-EDO tuned orchestral timpani strokes and thunderous rolls",
            Sf2Instrument::Sitar => "Classical Indian sitar with 22-shruti 53-EDO meend pitch glides",
        }
    }

    pub fn default_vote(self) -> Option<&'static str> {
        match self {
            Sf2Instrument::Harp
            | Sf2Instrument::Clarinet
            | Sf2Instrument::EnglishHorn
            | Sf2Instrument::Bassoon
            | Sf2Instrument::FrenchHorn
            | Sf2Instrument::Trombone
            | Sf2Instrument::Viola
            | Sf2Instrument::Cello
            | Sf2Instrument::StringEnsemble
            | Sf2Instrument::TremoloStrings
            | Sf2Instrument::Pizzicato
            | Sf2Instrument::Timpani
            | Sf2Instrument::Piano => Some("keep"),
            Sf2Instrument::Sitar => Some("maybe"),
            Sf2Instrument::ChurchOrgan
            | Sf2Instrument::Oboe
            | Sf2Instrument::Violin
            | Sf2Instrument::SlowStrings
            | Sf2Instrument::Contrabass => Some("drop"),
            _ => None,
        }
    }

    pub fn is_polyphonic(self) -> bool {
        matches!(
            self,
            Sf2Instrument::Piano
                | Sf2Instrument::Celesta
                | Sf2Instrument::ChurchOrgan
                | Sf2Instrument::Harp
                | Sf2Instrument::StringEnsemble
                | Sf2Instrument::TremoloStrings
                | Sf2Instrument::SlowStrings
                | Sf2Instrument::Pizzicato
                | Sf2Instrument::Timpani
        )
    }

    pub fn uses_breath_swell(self) -> bool {
        matches!(
            self,
            Sf2Instrument::Flute
                | Sf2Instrument::Clarinet
                | Sf2Instrument::Oboe
                | Sf2Instrument::EnglishHorn
                | Sf2Instrument::Bassoon
                | Sf2Instrument::Shakuhachi
                | Sf2Instrument::FrenchHorn
                | Sf2Instrument::Trombone
        )
    }

    pub fn reverb_send(self) -> f32 {
        match self {
            Sf2Instrument::Contrabass | Sf2Instrument::Bassoon => 0.14,
            Sf2Instrument::Timpani => 0.23,
            Sf2Instrument::ChurchOrgan => 0.24,
            Sf2Instrument::Celesta | Sf2Instrument::Harp => 0.24,
            Sf2Instrument::SlowStrings
            | Sf2Instrument::StringEnsemble
            | Sf2Instrument::TremoloStrings => 0.22,
            _ => 0.20,
        }
    }
}

#[derive(Clone, Copy, Debug)]
pub struct Sf2Note {
    pub start_sample: usize,
    pub end_sample: usize,
    pub step: i32,
    pub micro_cents: f32,
    pub velocity: f32,
    pub slide_from_cents: f32,
    pub breath_swell: bool,
    pub swell: SwellCurve,
    pub vibrato: f32,
}

impl Sf2Note {
    pub fn simple(start_sample: usize, end_sample: usize, step: i32, velocity: f32) -> Self {
        Self {
            start_sample,
            end_sample,
            step,
            micro_cents: 0.0,
            velocity,
            slide_from_cents: 0.0,
            breath_swell: false,
            swell: SwellCurve::None,
            vibrato: 0.0,
        }
    }
}

/// Optional MIDI CC 64 damper sustain pedal span in sample coordinates.
#[derive(Clone, Copy, Debug)]
pub struct Sf2Pedal {
    pub start_sample: usize,
    pub end_sample: usize,
}

pub fn load_soundfont_result(path: impl AsRef<Path>) -> Result<Arc<SoundFont>, String> {
    let p = path.as_ref();
    let mut file = File::open(p)
        .map_err(|e| format!("Failed to open SoundFont at {}: {e}", p.display()))?;
    let sf = SoundFont::new(&mut file)
        .map_err(|e| format!("Failed to parse SoundFont2 at {}: {e}", p.display()))?;
    Ok(Arc::new(sf))
}

pub fn load_soundfont(path: impl AsRef<Path>) -> Arc<SoundFont> {
    load_soundfont_result(path).unwrap_or_else(|e| panic!("{e}"))
}

/// Converts a 53-EDO step + micro_cents into nearest MIDI key + 14-bit pitch bend (±2 semitones).
#[inline]
pub fn edo53_to_midi_bend(step: i32, micro_cents: f32) -> (i32, i32, i32) {
    let freq = step_cents_to_freq(step, micro_cents as f64);
    let midi_float = 69.0 + 12.0 * (freq / 440.0).log2();
    let midi_key = midi_float.round().clamp(0.0, 127.0) as i32;
    let semitone_offset = midi_float - midi_key as f64;
    let bend_14 = (8192.0 + (semitone_offset / 2.0) * 8192.0)
        .round()
        .clamp(0.0, 16383.0) as i32;
    let lsb = bend_14 & 0x7F;
    let msb = (bend_14 >> 7) & 0x7F;
    (midi_key, lsb, msb)
}

/// Computes 14-bit pitch bend relative to a fixed `midi_key` for smooth meend glides.
#[inline]
fn edo53_bend_for_key(step: i32, cents: f32, midi_key: i32) -> (i32, i32) {
    let freq = step_cents_to_freq(step, cents as f64);
    let midi_float = 69.0 + 12.0 * (freq / 440.0).log2();
    let semitone_offset = (midi_float - midi_key as f64).clamp(-1.95, 1.95);
    let bend_14 = (8192.0 + (semitone_offset / 2.0) * 8192.0)
        .round()
        .clamp(0.0, 16383.0) as i32;
    (bend_14 & 0x7F, (bend_14 >> 7) & 0x7F)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
enum MidiActionKind {
    PedalOff = 0,
    NoteOff = 1,
    PedalOn = 2,
    PitchBend = 3,
    ControlChange = 4,
    NoteOn = 5,
}

#[derive(Clone, Copy, Debug)]
struct ScheduledMidi {
    sample: usize,
    kind: MidiActionKind,
    note_idx: usize,
    d1: i32,
    d2: i32,
    bend_lsb: i32,
    bend_msb: i32,
    init_expr: i32,
}

/// Renders one `Sf2Instrument` track using 15 dedicated melodic channels for collision-free 53-EDO tuning.
pub fn render_sf2_track(
    sf: &Arc<SoundFont>,
    inst: Sf2Instrument,
    notes: &[Sf2Note],
    total_samples: usize,
) -> Vec<(f32, f32)> {
    render_sf2_track_with_sr(sf, inst, notes, total_samples, SAMPLE_RATE)
}

/// Renders one `Sf2Instrument` track at an explicit `sample_rate` in exact 53-EDO.
pub fn render_sf2_track_with_sr(
    sf: &Arc<SoundFont>,
    inst: Sf2Instrument,
    notes: &[Sf2Note],
    total_samples: usize,
    sample_rate: usize,
) -> Vec<(f32, f32)> {
    render_sf2_track_with_options(sf, inst, notes, total_samples, sample_rate, false)
}

/// Renders one `Sf2Instrument` track at an explicit `sample_rate`, optionally quantized to pure 12-TET.
pub fn render_sf2_track_with_options(
    sf: &Arc<SoundFont>,
    inst: Sf2Instrument,
    notes: &[Sf2Note],
    total_samples: usize,
    sample_rate: usize,
    quantize_12tet: bool,
) -> Vec<(f32, f32)> {
    render_sf2_track_full(
        sf,
        inst,
        notes,
        &[],
        total_samples,
        sample_rate,
        quantize_12tet,
        false,
    )
}

/// Full-featured SF2 track renderer supporting directional swells, delayed vibrato,
/// damper sustain pedal spans (`CC 64`), and stereo register spread for wide ensemble tracks.
#[allow(clippy::too_many_arguments)]
pub fn render_sf2_track_full(
    sf: &Arc<SoundFont>,
    inst: Sf2Instrument,
    notes: &[Sf2Note],
    pedals: &[Sf2Pedal],
    total_samples: usize,
    sample_rate: usize,
    quantize_12tet: bool,
    stereo_spread: bool,
) -> Vec<(f32, f32)> {
    let settings = SynthesizerSettings::new(sample_rate as i32);
    let mut synth =
        Synthesizer::new(sf, &settings).expect("Failed to create rustysynth Synthesizer");

    for &ch in &MELODIC_CHANNELS {
        synth.process_midi_message(ch, 0xC0, inst.gm_program(), 0);
        // RPN 0,0 -> Pitch Bend Sensitivity = ±2 semitones, 0 cents
        synth.process_midi_message(ch, 0xB0, 101, 0);
        synth.process_midi_message(ch, 0xB0, 100, 0);
        synth.process_midi_message(ch, 0xB0, 6, 2);
        synth.process_midi_message(ch, 0xB0, 38, 0);
        synth.process_midi_message(ch, 0xB0, 101, 127);
        synth.process_midi_message(ch, 0xB0, 100, 127);
        // Clean channel mix controls (zero internal SF2 chorus/reverb so 53-EDO intervals stay pure)
        synth.process_midi_message(ch, 0xB0, 7, 112);
        synth.process_midi_message(ch, 0xB0, 10, inst.pan());
        synth.process_midi_message(ch, 0xB0, 11, 115);
        synth.process_midi_message(ch, 0xB0, 1, 0);
        synth.process_midi_message(ch, 0xB0, 91, 0);
        synth.process_midi_message(ch, 0xB0, 93, 0);
    }

    let mut events = Vec::with_capacity(notes.len() * 5 + pedals.len() * 2);
    let min_swell_samples = (0.05 * sample_rate as f64) as usize;
    let min_vib_samples = (0.22 * sample_rate as f64) as usize;

    for (p_idx, ped) in pedals.iter().enumerate() {
        if ped.start_sample >= total_samples {
            continue;
        }
        let p_end = ped
            .end_sample
            .min(total_samples.saturating_sub(1))
            .max(ped.start_sample + 1);
        events.push(ScheduledMidi {
            sample: ped.start_sample,
            kind: MidiActionKind::PedalOn,
            note_idx: p_idx,
            d1: 64,
            d2: 127,
            bend_lsb: 0,
            bend_msb: 0,
            init_expr: 0,
        });
        events.push(ScheduledMidi {
            sample: p_end,
            kind: MidiActionKind::PedalOff,
            note_idx: p_idx,
            d1: 64,
            d2: 0,
            bend_lsb: 0,
            bend_msb: 0,
            init_expr: 0,
        });
    }

    for (idx, n) in notes.iter().enumerate() {
        if n.start_sample >= total_samples {
            continue;
        }
        let end_sample = n
            .end_sample
            .min(total_samples.saturating_sub(1))
            .max(n.start_sample + 1);
        let (midi_key, end_lsb, end_msb) = if quantize_12tet {
            // Exact 12-TET semitone, zero pitch bend (14-bit center = 8192 -> LSB 0, MSB 64)
            (edo53_to_12tet_midi(n.step, n.micro_cents as f64), 0, 64)
        } else {
            edo53_to_midi_bend(n.step, n.micro_cents)
        };
        let vel_7 = (n.velocity.clamp(0.05, 1.0) * 127.0).round() as i32;

        let (init_lsb, init_msb) = if !quantize_12tet && n.slide_from_cents.abs() > 0.5 {
            edo53_bend_for_key(n.step, n.micro_cents + n.slide_from_cents, midi_key)
        } else {
            (end_lsb, end_msb)
        };

        let swell = if n.swell != SwellCurve::None {
            n.swell
        } else if n.breath_swell {
            SwellCurve::Arch
        } else {
            SwellCurve::None
        };

        let init_expr = swell.initial_cc11();
        events.push(ScheduledMidi {
            sample: n.start_sample,
            kind: MidiActionKind::NoteOn,
            note_idx: idx,
            d1: midi_key,
            d2: vel_7.clamp(1, 127),
            bend_lsb: init_lsb,
            bend_msb: init_msb,
            init_expr,
        });

        // Smooth meend glide across the first 140 ms (disabled in pure 12-TET comparison mode)
        if !quantize_12tet && n.slide_from_cents.abs() > 0.5 {
            let glide_samples =
                ((0.14 * sample_rate as f64) as usize).min(end_sample - n.start_sample);
            let steps = 16usize;
            for k in 1..=steps {
                let u = k as f64 / steps as f64;
                let remain = (1.0 - u) * (1.0 - u);
                let c = n.micro_cents + n.slide_from_cents * remain as f32;
                let (lsb, msb) = edo53_bend_for_key(n.step, c, midi_key);
                let s = n.start_sample + (glide_samples * k) / steps;
                events.push(ScheduledMidi {
                    sample: s,
                    kind: MidiActionKind::PitchBend,
                    note_idx: idx,
                    d1: 0,
                    d2: 0,
                    bend_lsb: lsb,
                    bend_msb: msb,
                    init_expr: 0,
                });
            }
        }

        // Directional CC 11 phrasing curve (`arch`, `cresc`, `dim`, `sfz`)
        if swell != SwellCurve::None && end_sample > n.start_sample + min_swell_samples {
            let dur = end_sample - n.start_sample;
            let step_samp = ((0.025 * sample_rate as f64) as usize).max(1);
            let count = (dur / step_samp).clamp(4, 36);
            for k in 1..count {
                let u = k as f64 / count as f64;
                let expr = swell.eval_cc11(u);
                events.push(ScheduledMidi {
                    sample: n.start_sample + (dur * k) / count,
                    kind: MidiActionKind::ControlChange,
                    note_idx: idx,
                    d1: 11,
                    d2: expr,
                    bend_lsb: 0,
                    bend_msb: 0,
                    init_expr: 0,
                });
            }
        }

        // Delayed CC 1 vibrato bloom (locks pure 53-EDO pitch first, then warms into singing vibrato)
        let vib = n.vibrato.clamp(0.0, 1.0);
        if vib > 0.02 && end_sample > n.start_sample + min_vib_samples {
            let dur = end_sample - n.start_sample;
            let delay_samp = ((0.16 * sample_rate as f64) as usize).min(dur / 3);
            let active_dur = dur.saturating_sub(delay_samp).max(1);
            let steps = 10usize;
            for k in 1..=steps {
                let u = k as f64 / steps as f64;
                let env = (PI * u.powf(0.75)).sin();
                let cc1 = (vib as f64 * 76.0 * env).round().clamp(0.0, 110.0) as i32;
                events.push(ScheduledMidi {
                    sample: n.start_sample + delay_samp + (active_dur * k) / steps,
                    kind: MidiActionKind::ControlChange,
                    note_idx: idx,
                    d1: 1,
                    d2: cc1,
                    bend_lsb: 0,
                    bend_msb: 0,
                    init_expr: 0,
                });
            }
        }

        events.push(ScheduledMidi {
            sample: end_sample,
            kind: MidiActionKind::NoteOff,
            note_idx: idx,
            d1: midi_key,
            d2: 0,
            bend_lsb: 0,
            bend_msb: 0,
            init_expr: 0,
        });
    }

    // Sort chronologically; PedalOff & NoteOff run before PedalOn/PitchBend/CC/NoteOn at identical samples.
    events.sort_by_key(|e| (e.sample, e.kind, e.note_idx));

    let mut note_to_slot = vec![None::<usize>; notes.len()];
    let mut slot_owner = [None::<usize>; 15];
    let mut slot_started_at = [0usize; 15];
    let mut slot_released_at = [0usize; 15];
    let mut slot_key = [0i32; 15];

    let mut out = vec![(0.0_f32, 0.0_f32); total_samples];
    let mut l_blk = [0.0_f32; 512];
    let mut r_blk = [0.0_f32; 512];

    let mut cursor = 0usize;
    let mut ev_idx = 0usize;

    while cursor < total_samples {
        while ev_idx < events.len() && events[ev_idx].sample <= cursor {
            let ev = events[ev_idx];
            ev_idx += 1;

            match ev.kind {
                MidiActionKind::PedalOn | MidiActionKind::PedalOff => {
                    for &ch in &MELODIC_CHANNELS {
                        synth.process_midi_message(ch, 0xB0, 64, ev.d2);
                    }
                }
                MidiActionKind::NoteOn => {
                    let slot = (0..15)
                        .filter(|&s| slot_owner[s].is_none())
                        .min_by_key(|&s| slot_released_at[s])
                        .unwrap_or_else(|| {
                            let victim = (0..15).min_by_key(|&s| slot_started_at[s]).unwrap_or(0);
                            let ch = MELODIC_CHANNELS[victim];
                            synth.process_midi_message(ch, 0x80, slot_key[victim], 0);
                            if let Some(prev_note) = slot_owner[victim] {
                                note_to_slot[prev_note] = None;
                            }
                            victim
                        });

                    let ch = MELODIC_CHANNELS[slot];
                    if stereo_spread {
                        // Gentle orchestral/keyboard register pan across L..R
                        let spread_pan = (64 + ((ev.d1 - 62) * 3) / 2).clamp(20, 108);
                        synth.process_midi_message(ch, 0xB0, 10, spread_pan);
                    }
                    synth.process_midi_message(ch, 0xB0, 1, 0);
                    synth.process_midi_message(ch, 0xB0, 11, ev.init_expr);
                    synth.process_midi_message(ch, 0xE0, ev.bend_lsb, ev.bend_msb);
                    synth.process_midi_message(ch, 0x90, ev.d1, ev.d2);
                    slot_owner[slot] = Some(ev.note_idx);
                    slot_started_at[slot] = cursor;
                    slot_key[slot] = ev.d1;
                    note_to_slot[ev.note_idx] = Some(slot);
                }
                MidiActionKind::NoteOff => {
                    if let Some(slot) = note_to_slot[ev.note_idx].take() {
                        let ch = MELODIC_CHANNELS[slot];
                        synth.process_midi_message(ch, 0xB0, 1, 0);
                        synth.process_midi_message(ch, 0x80, ev.d1, 0);
                        slot_owner[slot] = None;
                        slot_released_at[slot] = cursor;
                    }
                }
                MidiActionKind::PitchBend => {
                    if let Some(slot) = note_to_slot[ev.note_idx] {
                        let ch = MELODIC_CHANNELS[slot];
                        synth.process_midi_message(ch, 0xE0, ev.bend_lsb, ev.bend_msb);
                    }
                }
                MidiActionKind::ControlChange => {
                    if let Some(slot) = note_to_slot[ev.note_idx] {
                        let ch = MELODIC_CHANNELS[slot];
                        synth.process_midi_message(ch, 0xB0, ev.d1, ev.d2);
                    }
                }
            }
        }

        let next_ev_sample = if ev_idx < events.len() {
            events[ev_idx].sample.min(total_samples)
        } else {
            total_samples
        };
        let chunk = (next_ev_sample - cursor).min(512);
        if chunk > 0 {
            synth.render(&mut l_blk[..chunk], &mut r_blk[..chunk]);
            for i in 0..chunk {
                out[cursor + i] = (l_blk[i], r_blk[i]);
            }
            cursor += chunk;
        }
    }

    out
}

/// Masters a dry SF2 stereo buffer with gentle hall reverb.
pub fn master_with_gentle_hall(
    dry: &[(f32, f32)],
    reverb_send_gain: f32,
) -> (Vec<(f32, f32)>, AudioStats) {
    let send: Vec<(f32, f32)> = dry
        .iter()
        .map(|&(l, r)| (l * reverb_send_gain, r * reverb_send_gain))
        .collect();
    apply_hall_reverb_and_master(dry, &send, SAMPLE_RATE)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::synth::tests::measure_pitch_hz;
    use crate::tuning::step_to_freq;

    #[test]
    fn test_sf2_53edo_pitch_accuracy() {
        let sf = load_soundfont(DEFAULT_SOUNDFONT_PATH);
        let total_samples = SAMPLE_RATE * 2;

        for &(inst, step, label) in &[
            (Sf2Instrument::Piano, 39, "Piano A4"),
            (Sf2Instrument::Clarinet, 0, "Clarinet C4(53edo)"),
            (Sf2Instrument::Oboe, 0, "Oboe C4(53edo)"),
            (Sf2Instrument::ChurchOrgan, 39 - OCT, "Organ A3"),
            (Sf2Instrument::ChurchOrgan, 0, "Organ C4(53edo)"),
            (Sf2Instrument::Bassoon, -OCT, "Bassoon C3(53edo)"),
            (Sf2Instrument::Trombone, -OCT, "Trombone C3(53edo)"),
        ] {
            let note = Sf2Note::simple(0, (SAMPLE_RATE as f64 * 1.3) as usize, step, 0.85);
            let stereo = render_sf2_track(&sf, inst, &[note], total_samples);
            let mono: Vec<f32> = stereo.iter().map(|&(l, r)| 0.5 * (l + r)).collect();

            let target = step_to_freq(step);
            let measured = measure_pitch_hz(&mono, 10000, 20000, target * 0.82, target * 1.22);
            let cents_err = (1200.0 * (measured / target).log2()).abs();
            assert!(
                cents_err < 5.0,
                "{label} pitch error {cents_err:.2} cents (target {target:.2} Hz, measured {measured:.2} Hz)"
            );
        }
    }

    #[test]
    fn test_swell_curves_and_damper_pedal_sustain() {
        assert_eq!(SwellCurve::parse(Some("cresc"), false).unwrap(), SwellCurve::Cresc);
        assert_eq!(SwellCurve::parse(Some("dim"), true).unwrap(), SwellCurve::Dim);
        assert_eq!(SwellCurve::parse(Some("sfz"), false).unwrap(), SwellCurve::Sfz);
        assert_eq!(SwellCurve::parse(None, true).unwrap(), SwellCurve::Arch);

        let sf = load_soundfont(DEFAULT_SOUNDFONT_PATH);
        let sr = SAMPLE_RATE;
        let total = sr * 2;
        // Short 0.15s staccato piano note at C4, compared with vs without CC64 damper pedal
        let note = Sf2Note::simple(0, (sr as f64 * 0.15) as usize, 0, 0.85);
        let dry_no_ped = render_sf2_track_full(&sf, Sf2Instrument::Piano, &[note], &[], total, sr, false, false);
        let ped = Sf2Pedal { start_sample: 0, end_sample: (sr as f64 * 1.6) as usize };
        let dry_ped = render_sf2_track_full(&sf, Sf2Instrument::Piano, &[note], &[ped], total, sr, false, false);

        let tail_energy = |buf: &[(f32, f32)]| -> f64 {
            buf[(sr / 2)..(sr + sr / 4)]
                .iter()
                .map(|&(l, r)| (l as f64).powi(2) + (r as f64).powi(2))
                .sum()
        };
        assert!(
            tail_energy(&dry_ped) > tail_energy(&dry_no_ped) * 4.0,
            "CC64 sustain pedal should ring well past note-off"
        );
    }
}
