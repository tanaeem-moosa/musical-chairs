//! Agent-friendly JSON score loader, decoupled stage config, tuning modes (53-EDO / 12-TET),
//! intentional trailing silence, and 3D-spatialized renderer.

use std::collections::HashMap;
use std::f64::consts::{FRAC_1_SQRT_2, PI};
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;

use rustysynth::SoundFont;
use serde::{Deserialize, Deserializer, Serialize};

use crate::indian::{render_dotara_track_with_tuning, render_ektara_track_with_tuning, IndianNote};
use crate::reverb::{apply_hall_reverb_and_master_with_rt60, AudioStats};
use crate::score::{TempoMap, TempoSegment};
use crate::sf2_synth::{
    load_soundfont_result, render_sf2_track_full, Sf2Instrument, Sf2Note, Sf2Pedal, SwellCurve,
    DEFAULT_SOUNDFONT_PATH,
};
use crate::spatial::{spatialize_track_with_width, StagePos};
use crate::synth::SAMPLE_RATE;
use crate::wav::write_stereo_wav_16bit;

/// All 26 instrument identifiers supported by the JSON score schema.
pub const VALID_INSTRUMENTS: [&str; 26] = [
    "piano",
    "harp",
    "nylon_guitar",
    "steel_guitar",
    "celesta",
    "church_organ",
    "clarinet",
    "english_horn",
    "bassoon",
    "french_horn",
    "trombone",
    "flute",
    "oboe",
    "shakuhachi",
    "violin",
    "viola",
    "cello",
    "contrabass",
    "string_ensemble",
    "tremolo_strings",
    "slow_strings",
    "pizzicato",
    "timpani",
    "sitar",
    "ektara",
    "dotara",
];

fn default_title() -> String {
    "Untitled 53-EDO Piece".to_string()
}

fn default_sample_rate() -> usize {
    SAMPLE_RATE
}

fn default_tail_seconds() -> f64 {
    4.5
}

fn default_reverb_rt60() -> f64 {
    2.25
}

fn default_tempo() -> Vec<JsonTempoPoint> {
    vec![JsonTempoPoint {
        beat: 0.0,
        bpm: 70.0,
    }]
}

fn default_y() -> f64 {
    4.5
}

fn default_gain() -> f64 {
    1.0
}

fn default_vel() -> f32 {
    0.75
}

fn deserialize_optional_nullable_f64<'de, D>(
    deserializer: D,
) -> Result<Option<Option<f64>>, D::Error>
where
    D: Deserializer<'de>,
{
    Ok(Some(Option::<f64>::deserialize(deserializer)?))
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Default)]
pub enum TuningMode {
    #[default]
    Edo53,
    Tet12,
}

impl TuningMode {
    pub fn parse(s: &str) -> Result<Self, String> {
        match s.to_ascii_lowercase().as_str() {
            "53edo" => Ok(TuningMode::Edo53),
            "12tet" => Ok(TuningMode::Tet12),
            other => Err(format!(
                "Unknown tuning `{other}`. Supported tunings: `53edo` (default), `12tet`"
            )),
        }
    }

    pub fn label(self) -> &'static str {
        match self {
            TuningMode::Edo53 => "53edo",
            TuningMode::Tet12 => "12tet",
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct JsonScore {
    #[serde(default = "default_title")]
    pub title: String,
    #[serde(default)]
    pub description: String,
    #[serde(default = "default_sample_rate")]
    pub sample_rate: usize,
    #[serde(default = "default_tail_seconds")]
    pub tail_seconds: f64,
    #[serde(default = "default_reverb_rt60")]
    pub reverb_rt60: f64,
    #[serde(default)]
    pub end_silence_seconds: f64,
    #[serde(default = "default_tempo")]
    pub tempo: Vec<JsonTempoPoint>,
    #[serde(default)]
    pub sections: Vec<JsonSection>,
    pub tracks: Vec<JsonTrack>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct JsonSection {
    pub beat: f64,
    pub title: String,
}

#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
pub struct JsonTempoPoint {
    pub beat: f64,
    pub bpm: f64,
}

#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
pub struct JsonPedalSpan {
    pub beat: f64,
    pub dur: f64,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct JsonTrack {
    pub id: String,
    #[serde(default)]
    pub name: Option<String>,
    pub instrument: String,
    #[serde(default)]
    pub x: f64,
    #[serde(default = "default_y")]
    pub y: f64,
    #[serde(default)]
    pub width: f64,
    #[serde(default = "default_gain")]
    pub gain: f64,
    #[serde(default)]
    pub warm_lowpass_hz: Option<f64>,
    #[serde(default)]
    pub pedals: Vec<JsonPedalSpan>,
    #[serde(default)]
    pub notes: Vec<JsonNote>,
}

impl JsonTrack {
    pub fn display_name(&self) -> &str {
        self.name.as_deref().unwrap_or(&self.id)
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct JsonNote {
    pub beat: f64,
    pub dur: f64,
    pub step: i32,
    #[serde(default = "default_vel")]
    pub vel: f32,
    #[serde(default)]
    pub cents: f32,
    #[serde(default)]
    pub slide_from_cents: f32,
    #[serde(default)]
    pub breath_swell: bool,
    #[serde(default)]
    pub swell: Option<String>,
    #[serde(default)]
    pub vibrato: f32,
    #[serde(default)]
    pub meend_cents: f32,
}

/// Optional per-player spatial/mix override inside a decoupled `stage.json`.
#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct StagePlayerPlacement {
    #[serde(default)]
    pub x: Option<f64>,
    #[serde(default)]
    pub y: Option<f64>,
    #[serde(default)]
    pub width: Option<f64>,
    #[serde(default)]
    pub gain: Option<f64>,
    /// `None` = omitted (inherit inline), `Some(None)` = explicit `null` (disable LP), `Some(Some(hz))` = override LP.
    #[serde(default, deserialize_with = "deserialize_optional_nullable_f64")]
    pub warm_lowpass_hz: Option<Option<f64>>,
}

/// Decoupled concert-stage configuration loaded via `--stage <stage.json>`.
#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct StageConfig {
    #[serde(default)]
    pub name: Option<String>,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub reverb_rt60: Option<f64>,
    #[serde(default)]
    pub tail_seconds: Option<f64>,
    #[serde(default)]
    pub end_silence_seconds: Option<f64>,
    #[serde(default)]
    pub players: HashMap<String, StagePlayerPlacement>,
}

impl StageConfig {
    pub fn validate(&self) -> Result<(), String> {
        if let Some(rt60) = self.reverb_rt60 {
            if !rt60.is_finite() || rt60 < 0.0 {
                return Err(format!(
                    "Invalid stage reverb_rt60 {rt60} (must be finite and >= 0.0)"
                ));
            }
        }
        if let Some(tail) = self.tail_seconds {
            if !tail.is_finite() || tail < 0.0 {
                return Err(format!(
                    "Invalid stage tail_seconds {tail} (must be finite and >= 0.0)"
                ));
            }
        }
        if let Some(sil) = self.end_silence_seconds {
            if !sil.is_finite() || sil < 0.0 {
                return Err(format!(
                    "Invalid stage end_silence_seconds {sil} (must be finite and >= 0.0)"
                ));
            }
        }
        for (key, p) in &self.players {
            if let Some(x) = p.x {
                if !x.is_finite() {
                    return Err(format!("stage.players[{key}].x={x} must be finite"));
                }
            }
            if let Some(y) = p.y {
                if !y.is_finite() {
                    return Err(format!("stage.players[{key}].y={y} must be finite"));
                }
            }
            if let Some(w) = p.width {
                if !w.is_finite() || w < 0.0 {
                    return Err(format!(
                        "stage.players[{key}].width={w} must be finite and >= 0.0"
                    ));
                }
            }
            if let Some(g) = p.gain {
                if !g.is_finite() || g < 0.0 {
                    return Err(format!(
                        "stage.players[{key}].gain={g} must be finite and >= 0.0"
                    ));
                }
            }
            if let Some(Some(hz)) = p.warm_lowpass_hz {
                if !hz.is_finite() || hz <= 0.0 {
                    return Err(format!(
                        "stage.players[{key}].warm_lowpass_hz={hz} must be finite and > 0.0"
                    ));
                }
            }
        }
        Ok(())
    }
}

/// Parses and validates a `StageConfig` from JSON text.
pub fn parse_stage_config(json: &str) -> Result<StageConfig, String> {
    let stage: StageConfig =
        serde_json::from_str(json).map_err(|e| format!("Failed to parse stage JSON: {e}"))?;
    stage.validate()?;
    Ok(stage)
}

/// Reads and validates a `StageConfig` from disk.
pub fn load_stage_config(path: impl AsRef<Path>) -> Result<StageConfig, String> {
    let p = path.as_ref();
    let content = fs::read_to_string(p)
        .map_err(|e| format!("Failed to read stage file {}: {e}", p.display()))?;
    parse_stage_config(&content)
}

#[derive(Clone, Debug)]
pub struct ResolvedStageParams {
    pub stage_name: Option<String>,
    pub reverb_rt60: f64,
    pub tail_seconds: f64,
    pub end_silence_seconds: f64,
}

#[derive(Clone, Copy, Debug)]
pub struct ResolvedTrackPlacement {
    pub x: f64,
    pub y: f64,
    pub width: f64,
    pub gain: f64,
    pub warm_lowpass_hz: Option<f64>,
}

/// Resolves hall RT60, tail seconds, and trailing silence using precedence:
/// CLI override > `stage.json` > `score.json` > defaults.
pub fn resolve_stage_params(
    score: &JsonScore,
    stage: Option<&StageConfig>,
    end_silence_override: Option<f64>,
) -> Result<ResolvedStageParams, String> {
    let end_silence_seconds = end_silence_override
        .or_else(|| stage.and_then(|s| s.end_silence_seconds))
        .unwrap_or(score.end_silence_seconds);
    if !end_silence_seconds.is_finite() || end_silence_seconds < 0.0 {
        return Err(format!(
            "Invalid end_silence_seconds {end_silence_seconds} (must be finite and >= 0.0)"
        ));
    }

    Ok(ResolvedStageParams {
        stage_name: stage.and_then(|s| s.name.clone()),
        reverb_rt60: stage.and_then(|s| s.reverb_rt60).unwrap_or(score.reverb_rt60),
        tail_seconds: stage
            .and_then(|s| s.tail_seconds)
            .unwrap_or(score.tail_seconds),
        end_silence_seconds,
    })
}

/// Resolves a track's stage coordinates, gain, and optional warm lowpass using precedence:
/// `stage.players[track.id]` -> `stage.players[track.instrument]` -> inline track fields -> defaults.
pub fn resolve_track_placement(
    track: &JsonTrack,
    stage: Option<&StageConfig>,
) -> ResolvedTrackPlacement {
    let by_id = stage.and_then(|s| s.players.get(&track.id));
    let by_inst = stage.and_then(|s| s.players.get(&track.instrument));

    let x = by_id
        .and_then(|p| p.x)
        .or_else(|| by_inst.and_then(|p| p.x))
        .unwrap_or(track.x);
    let y = by_id
        .and_then(|p| p.y)
        .or_else(|| by_inst.and_then(|p| p.y))
        .unwrap_or(track.y);
    let width = by_id
        .and_then(|p| p.width)
        .or_else(|| by_inst.and_then(|p| p.width))
        .unwrap_or(track.width);
    let gain = by_id
        .and_then(|p| p.gain)
        .or_else(|| by_inst.and_then(|p| p.gain))
        .unwrap_or(track.gain);
    let warm_lowpass_hz = by_id
        .and_then(|p| p.warm_lowpass_hz)
        .or_else(|| by_inst.and_then(|p| p.warm_lowpass_hz))
        .unwrap_or(track.warm_lowpass_hz);

    ResolvedTrackPlacement {
        x,
        y,
        width,
        gain,
        warm_lowpass_hz,
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ScoreInstrument {
    Sf2(Sf2Instrument),
    Ektara,
    Dotara,
}

impl ScoreInstrument {
    pub fn parse(name: &str) -> Result<Self, String> {
        if let Some(sf2) = Sf2Instrument::from_id(name) {
            return Ok(ScoreInstrument::Sf2(sf2));
        }
        match name {
            "ektara" => Ok(ScoreInstrument::Ektara),
            "dotara" => Ok(ScoreInstrument::Dotara),
            other => Err(format!(
                "Unknown instrument `{other}`. Supported instruments: {}",
                VALID_INSTRUMENTS.join(", ")
            )),
        }
    }
}

#[derive(Clone, Debug)]
pub struct RenderOptions {
    pub soundfont_path: PathBuf,
    pub stems_dir: Option<PathBuf>,
    pub stage: Option<StageConfig>,
    pub tuning: TuningMode,
    pub end_silence_override: Option<f64>,
}

impl Default for RenderOptions {
    fn default() -> Self {
        Self {
            soundfont_path: PathBuf::from(DEFAULT_SOUNDFONT_PATH),
            stems_dir: None,
            stage: None,
            tuning: TuningMode::Edo53,
            end_silence_override: None,
        }
    }
}

#[derive(Clone, Debug)]
pub struct TrackSummary {
    pub id: String,
    pub name: String,
    pub instrument: String,
    pub note_count: usize,
    pub pos: StagePos,
    pub width: f64,
    pub gain: f64,
    pub warm_lowpass_hz: Option<f64>,
}

#[derive(Clone, Debug)]
pub struct RenderResult {
    pub audio: Vec<(f32, f32)>,
    pub sample_rate: usize,
    pub duration_seconds: f64,
    pub tail_seconds: f64,
    pub reverb_rt60: f64,
    pub end_silence_seconds: f64,
    pub stage_name: Option<String>,
    pub tuning: TuningMode,
    pub stats: AudioStats,
    pub track_summaries: Vec<TrackSummary>,
    pub stems_written: Vec<PathBuf>,
}

impl JsonScore {
    /// Validates score parameters, instruments, tempo map, track metadata, and note events.
    pub fn validate(&self) -> Result<(), String> {
        if !(8_000..=192_000).contains(&self.sample_rate) {
            return Err(format!(
                "Invalid sample_rate {} (must be between 8000 and 192000)",
                self.sample_rate
            ));
        }
        if !self.tail_seconds.is_finite() || self.tail_seconds < 0.0 {
            return Err(format!(
                "Invalid tail_seconds {} (must be finite and >= 0.0)",
                self.tail_seconds
            ));
        }
        if !self.reverb_rt60.is_finite() || self.reverb_rt60 < 0.0 {
            return Err(format!(
                "Invalid reverb_rt60 {} (must be finite and >= 0.0)",
                self.reverb_rt60
            ));
        }
        if !self.end_silence_seconds.is_finite() || self.end_silence_seconds < 0.0 {
            return Err(format!(
                "Invalid end_silence_seconds {} (must be finite and >= 0.0)",
                self.end_silence_seconds
            ));
        }
        if self.tempo.is_empty() {
            return Err("Tempo map must contain at least one {beat, bpm} point".to_string());
        }
        for (i, tp) in self.tempo.iter().enumerate() {
            if !tp.beat.is_finite() || tp.beat < 0.0 {
                return Err(format!(
                    "tempo[{i}].beat={} must be finite and >= 0.0",
                    tp.beat
                ));
            }
            if !tp.bpm.is_finite() || tp.bpm <= 0.0 {
                return Err(format!(
                    "tempo[{i}].bpm={} must be finite and > 0.0",
                    tp.bpm
                ));
            }
        }
        for (si, sec) in self.sections.iter().enumerate() {
            if !sec.beat.is_finite() || sec.beat < 0.0 {
                return Err(format!(
                    "sections[{si}].beat={} must be finite and >= 0.0",
                    sec.beat
                ));
            }
            if sec.title.trim().is_empty() {
                return Err(format!("sections[{si}].title must be non-empty"));
            }
        }
        for (ti, track) in self.tracks.iter().enumerate() {
            if track.id.trim().is_empty()
                || track.id.contains('/')
                || track.id.contains('\\')
                || track.id.contains("..")
            {
                return Err(format!(
                    "tracks[{ti}].id=`{}` must be non-empty and contain no path separators",
                    track.id
                ));
            }
            ScoreInstrument::parse(&track.instrument)
                .map_err(|e| format!("tracks[{ti}] (`{}`): {e}", track.id))?;
            if !track.x.is_finite() || !track.y.is_finite() {
                return Err(format!(
                    "tracks[{ti}] (`{}`): stage position ({}, {}) must be finite",
                    track.id, track.x, track.y
                ));
            }
            if !track.width.is_finite() || track.width < 0.0 {
                return Err(format!(
                    "tracks[{ti}] (`{}`): width {} must be finite and >= 0.0",
                    track.id, track.width
                ));
            }
            if !track.gain.is_finite() || track.gain < 0.0 {
                return Err(format!(
                    "tracks[{ti}] (`{}`): gain {} must be finite and >= 0.0",
                    track.id, track.gain
                ));
            }
            if let Some(hz) = track.warm_lowpass_hz {
                if !hz.is_finite() || hz <= 0.0 {
                    return Err(format!(
                        "tracks[{ti}] (`{}`): warm_lowpass_hz {} must be finite and > 0.0",
                        track.id, hz
                    ));
                }
            }
            for (pi, ped) in track.pedals.iter().enumerate() {
                if !ped.beat.is_finite() || ped.beat < 0.0 || !ped.dur.is_finite() || ped.dur <= 0.0
                {
                    return Err(format!(
                        "tracks[{ti}] (`{}`).pedals[{pi}] must have finite beat >= 0.0 and dur > 0.0",
                        track.id
                    ));
                }
            }
            for (ni, note) in track.notes.iter().enumerate() {
                if !note.beat.is_finite() || note.beat < 0.0 {
                    return Err(format!(
                        "tracks[{ti}] (`{}`).notes[{ni}].beat={} must be finite and >= 0.0",
                        track.id, note.beat
                    ));
                }
                if !note.dur.is_finite() || note.dur <= 0.0 {
                    return Err(format!(
                        "tracks[{ti}] (`{}`).notes[{ni}].dur={} must be finite and > 0.0",
                        track.id, note.dur
                    ));
                }
                if !note.vel.is_finite()
                    || !note.cents.is_finite()
                    || !note.slide_from_cents.is_finite()
                    || !note.vibrato.is_finite()
                    || note.vibrato < 0.0
                    || !note.meend_cents.is_finite()
                {
                    return Err(format!(
                        "tracks[{ti}] (`{}`).notes[{ni}] contains invalid or non-finite float values",
                        track.id
                    ));
                }
                SwellCurve::parse(note.swell.as_deref(), note.breath_swell).map_err(|e| {
                    format!("tracks[{ti}] (`{}`).notes[{ni}]: {e}", track.id)
                })?;
            }
        }
        Ok(())
    }
}

/// Parses a `JsonScore` from a JSON string and validates all fields.
pub fn parse_json_score(json: &str) -> Result<JsonScore, String> {
    let score: JsonScore =
        serde_json::from_str(json).map_err(|e| format!("Failed to parse JSON score: {e}"))?;
    score.validate()?;
    Ok(score)
}

/// Reads and validates a `JsonScore` from disk.
pub fn load_json_score(path: impl AsRef<Path>) -> Result<JsonScore, String> {
    let p = path.as_ref();
    let content = fs::read_to_string(p)
        .map_err(|e| format!("Failed to read score file {}: {e}", p.display()))?;
    parse_json_score(&content)
}

/// 2-pole Butterworth low-pass biquad filter (Q = 1/sqrt(2)) for warm track shelving.
#[derive(Clone, Copy)]
struct WarmBiquadLP {
    b0: f64,
    b1: f64,
    b2: f64,
    a1: f64,
    a2: f64,
    z1: f64,
    z2: f64,
}

impl WarmBiquadLP {
    fn new(cutoff_hz: f64, sample_rate: usize) -> Self {
        let sr = sample_rate as f64;
        let fc = cutoff_hz.clamp(40.0, 0.45 * sr);
        let w0 = 2.0 * PI * fc / sr;
        let cos_w0 = w0.cos();
        let alpha = w0.sin() / (2.0 * FRAC_1_SQRT_2);
        let a0 = 1.0 + alpha;
        Self {
            b0: ((1.0 - cos_w0) * 0.5) / a0,
            b1: (1.0 - cos_w0) / a0,
            b2: ((1.0 - cos_w0) * 0.5) / a0,
            a1: (-2.0 * cos_w0) / a0,
            a2: (1.0 - alpha) / a0,
            z1: 0.0,
            z2: 0.0,
        }
    }

    #[inline]
    fn process(&mut self, x: f64) -> f64 {
        let y = self.b0 * x + self.z1;
        self.z1 = self.b1 * x - self.a1 * y + self.z2;
        self.z2 = self.b2 * x - self.a2 * y;
        y
    }
}

/// Applies a 2-pole warm Butterworth low-pass filter independently to both L and R channels.
pub fn apply_warm_lowpass(buf: &mut [(f32, f32)], cutoff_hz: f64, sample_rate: usize) {
    let mut lp_l = WarmBiquadLP::new(cutoff_hz, sample_rate);
    let mut lp_r = WarmBiquadLP::new(cutoff_hz, sample_rate);
    for pair in buf.iter_mut() {
        pair.0 = lp_l.process(pair.0 as f64) as f32;
        pair.1 = lp_r.process(pair.1 as f64) as f32;
    }
}

fn beat_to_sample(tempo: &TempoMap, beat: f64, sample_rate: usize) -> usize {
    (tempo.beat_to_seconds(beat) * sample_rate as f64)
        .round()
        .max(0.0) as usize
}

/// Linearly resamples a stereo buffer from `src_sr` to `dst_sr` (used if physical models
/// are requested at a non-48kHz sample rate).
fn resample_stereo_linear(
    src: &[(f32, f32)],
    src_sr: usize,
    dst_sr: usize,
    dst_len: usize,
) -> Vec<(f32, f32)> {
    if src.is_empty() || dst_len == 0 {
        return vec![(0.0, 0.0); dst_len];
    }
    let ratio = src_sr as f64 / dst_sr as f64;
    let last = src.len() - 1;
    let mut out = Vec::with_capacity(dst_len);
    for i in 0..dst_len {
        let pos = i as f64 * ratio;
        let idx = (pos.floor() as usize).min(last);
        let next = (idx + 1).min(last);
        let frac = (pos - idx as f64) as f32;
        let l = src[idx].0 * (1.0 - frac) + src[next].0 * frac;
        let r = src[idx].1 * (1.0 - frac) + src[next].1 * frac;
        out.push((l, r));
    }
    out
}

#[allow(clippy::too_many_arguments)]
fn render_single_track_dry(
    track: &JsonTrack,
    placement: ResolvedTrackPlacement,
    inst: ScoreInstrument,
    tempo: &TempoMap,
    sf: Option<&Arc<SoundFont>>,
    sample_rate: usize,
    total_samples: usize,
    quantize_12tet: bool,
) -> Vec<(f32, f32)> {
    let mut dry = match inst {
        ScoreInstrument::Sf2(sf2_inst) => {
            let sf_arc = sf.expect("SoundFont must be loaded when SF2 tracks exist");
            let notes: Vec<Sf2Note> = track
                .notes
                .iter()
                .map(|n| {
                    let start_sample = beat_to_sample(tempo, n.beat, sample_rate);
                    let end_sample = beat_to_sample(tempo, n.beat + n.dur, sample_rate)
                        .max(start_sample + 1);
                     let slide = if n.slide_from_cents.abs() > 0.0 {
                        n.slide_from_cents
                    } else {
                        n.meend_cents
                    };
                    let swell = SwellCurve::parse(n.swell.as_deref(), n.breath_swell)
                        .unwrap_or(SwellCurve::None);
                    Sf2Note {
                        start_sample,
                        end_sample,
                        step: n.step,
                        micro_cents: n.cents,
                        velocity: n.vel,
                        slide_from_cents: slide,
                        breath_swell: n.breath_swell,
                        swell,
                        vibrato: n.vibrato,
                    }
                })
                .collect();
            let pedals: Vec<Sf2Pedal> = track
                .pedals
                .iter()
                .map(|p| {
                    let start_sample = beat_to_sample(tempo, p.beat, sample_rate);
                    let end_sample =
                        beat_to_sample(tempo, p.beat + p.dur, sample_rate).max(start_sample + 1);
                    Sf2Pedal {
                        start_sample,
                        end_sample,
                    }
                })
                .collect();
            render_sf2_track_full(
                sf_arc,
                sf2_inst,
                &notes,
                &pedals,
                total_samples,
                sample_rate,
                quantize_12tet,
                placement.width > 0.25,
            )
        }
        ScoreInstrument::Ektara | ScoreInstrument::Dotara => {
            let native_total = if sample_rate == SAMPLE_RATE {
                total_samples
            } else {
                ((total_samples as f64 * SAMPLE_RATE as f64) / sample_rate as f64).ceil() as usize
            };
            let notes: Vec<IndianNote> = track
                .notes
                .iter()
                .map(|n| {
                    let start_sample = beat_to_sample(tempo, n.beat, SAMPLE_RATE);
                    let end_sample = beat_to_sample(tempo, n.beat + n.dur, SAMPLE_RATE)
                        .max(start_sample + 1);
                    let meend = if n.meend_cents.abs() > 0.0 {
                        n.meend_cents
                    } else {
                        n.slide_from_cents
                    };
                    IndianNote {
                        start_sample,
                        end_sample,
                        step: n.step,
                        velocity: n.vel,
                        meend_cents: meend,
                    }
                })
                .collect();
            let native = match inst {
                ScoreInstrument::Ektara => {
                    render_ektara_track_with_tuning(&notes, native_total, quantize_12tet)
                }
                ScoreInstrument::Dotara => {
                    render_dotara_track_with_tuning(&notes, native_total, quantize_12tet)
                }
                ScoreInstrument::Sf2(_) => unreachable!(),
            };
            if sample_rate == SAMPLE_RATE {
                native
            } else {
                resample_stereo_linear(&native, SAMPLE_RATE, sample_rate, total_samples)
            }
        }
    };

    if let Some(cutoff_hz) = placement.warm_lowpass_hz {
        apply_warm_lowpass(&mut dry, cutoff_hz, sample_rate);
    }

    let gain = placement.gain as f32;
    if (gain - 1.0).abs() > 1e-6 {
        for s in &mut dry {
            s.0 *= gain;
            s.1 *= gain;
        }
    }

    dry
}

/// Renders a validated `JsonScore` through 3D concert-stage spatialization and FDN hall reverb.
/// Supports optional decoupled `StageConfig`, `53edo` / `12tet` tuning mode, intentional trailing
/// silence appended after mastering, and synchronized centered dry stems via `opts.stems_dir`.
pub fn render_json_score(
    score: &JsonScore,
    opts: &RenderOptions,
) -> Result<RenderResult, String> {
    score.validate()?;
    if let Some(stage) = &opts.stage {
        stage.validate()?;
    }

    let stage_params = resolve_stage_params(score, opts.stage.as_ref(), opts.end_silence_override)?;
    let quantize_12tet = opts.tuning == TuningMode::Tet12;

    let sr = score.sample_rate;
    let tempo = TempoMap::from_segments(
        score
            .tempo
            .iter()
            .map(|t| TempoSegment {
                beat: t.beat,
                bpm: t.bpm,
            })
            .collect(),
    );

    let max_beat = score
        .tracks
        .iter()
        .flat_map(|t| t.notes.iter())
        .map(|n| n.beat + n.dur)
        .fold(0.0_f64, f64::max);
    let musical_secs = tempo.beat_to_seconds(max_beat) + stage_params.tail_seconds;
    let musical_samples = ((musical_secs * sr as f64).ceil().max(1.0)) as usize;
    let silence_samples = (stage_params.end_silence_seconds * sr as f64).round().max(0.0) as usize;

    let parsed_instruments: Vec<ScoreInstrument> = score
        .tracks
        .iter()
        .map(|t| ScoreInstrument::parse(&t.instrument))
        .collect::<Result<Vec<_>, _>>()?;

    let placements: Vec<ResolvedTrackPlacement> = score
        .tracks
        .iter()
        .map(|t| resolve_track_placement(t, opts.stage.as_ref()))
        .collect();

    let needs_sf2 = parsed_instruments
        .iter()
        .any(|inst| matches!(inst, ScoreInstrument::Sf2(_)));
    let sf = if needs_sf2 {
        Some(load_soundfont_result(&opts.soundfont_path)?)
    } else {
        None
    };

    let want_stems = opts.stems_dir.is_some();
    let track_count = score.tracks.len();

    struct SharedMix {
        sum_direct: Vec<(f32, f32)>,
        sum_send: Vec<(f32, f32)>,
        sum_dry_mono: Vec<f64>,
        max_track_mono_peak: f64,
        stems_mono: Vec<Option<Vec<f32>>>,
    }

    let shared = Mutex::new(SharedMix {
        sum_direct: vec![(0.0_f32, 0.0_f32); musical_samples],
        sum_send: vec![(0.0_f32, 0.0_f32); musical_samples],
        sum_dry_mono: if want_stems {
            vec![0.0_f64; musical_samples]
        } else {
            Vec::new()
        },
        max_track_mono_peak: 0.0,
        stems_mono: if want_stems {
            vec![None; track_count]
        } else {
            Vec::new()
        },
    });

    let next_idx = AtomicUsize::new(0);
    let max_threads = thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(1)
        .min(track_count.max(1));

    thread::scope(|s| {
        for _ in 0..max_threads {
            let shared_ref = &shared;
            let next_ref = &next_idx;
            let tracks = &score.tracks;
            let insts = &parsed_instruments;
            let place_ref = &placements;
            let tempo_ref = &tempo;
            let sf_ref = sf.as_ref();

            s.spawn(move || loop {
                let idx = next_ref.fetch_add(1, Ordering::Relaxed);
                if idx >= tracks.len() {
                    break;
                }
                let track = &tracks[idx];
                let inst = insts[idx];
                let placement = place_ref[idx];
                let dry = render_single_track_dry(
                    track,
                    placement,
                    inst,
                    tempo_ref,
                    sf_ref,
                    sr,
                    musical_samples,
                    quantize_12tet,
                );
                let pos = StagePos::new(placement.x, placement.y);
                let (direct, send) =
                    spatialize_track_with_width(&dry, pos, placement.width, sr);

                let (opt_mono, track_peak) = if want_stems {
                    let mut mono = Vec::with_capacity(musical_samples);
                    let mut peak = 0.0_f64;
                    for &(l, r) in &dry {
                        let m = 0.5 * (l as f64 + r as f64);
                        peak = peak.max(m.abs());
                        mono.push(m as f32);
                    }
                    (Some(mono), peak)
                } else {
                    (None, 0.0)
                };
                drop(dry);

                let mut guard = shared_ref.lock().expect("mix mutex poisoned");
                for i in 0..musical_samples {
                    guard.sum_direct[i].0 += direct[i].0;
                    guard.sum_direct[i].1 += direct[i].1;
                    guard.sum_send[i].0 += send[i].0;
                    guard.sum_send[i].1 += send[i].1;
                }
                if let Some(mono) = opt_mono {
                    guard.max_track_mono_peak = guard.max_track_mono_peak.max(track_peak);
                    for i in 0..musical_samples {
                        guard.sum_dry_mono[i] += mono[i] as f64;
                    }
                    guard.stems_mono[idx] = Some(mono);
                }
            });
        }
    });

    let mix = shared.into_inner().expect("mix mutex poisoned");
    let (mut audio, stats) = apply_hall_reverb_and_master_with_rt60(
        &mix.sum_direct,
        &mix.sum_send,
        sr,
        stage_params.reverb_rt60,
    );

    // Append exact clean trailing silence AFTER mastering so RMS & normalization stay unaffected.
    if silence_samples > 0 {
        audio.resize(musical_samples + silence_samples, (0.0_f32, 0.0_f32));
    }

    let mut stems_written = Vec::new();
    if let Some(stems_dir) = &opts.stems_dir {
        fs::create_dir_all(stems_dir).map_err(|e| {
            format!(
                "Failed to create stems directory {}: {e}",
                stems_dir.display()
            )
        })?;
        let sum_peak = mix
            .sum_dry_mono
            .iter()
            .map(|v| v.abs())
            .fold(0.0_f64, f64::max);
        let dry_peak = sum_peak.max(mix.max_track_mono_peak);
        let stem_scale = if dry_peak > 1e-9 {
            (0.75 / dry_peak).min(2.5)
        } else {
            1.0
        };

        for (track, opt_mono) in score.tracks.iter().zip(mix.stems_mono.iter()) {
            let mono = opt_mono
                .as_ref()
                .expect("stem mono buffer missing when stems_dir is set");
            let mut centered: Vec<(f32, f32)> = Vec::with_capacity(musical_samples + silence_samples);
            for &m in mono {
                let s = (m as f64 * stem_scale) as f32;
                centered.push((s, s));
            }
            if silence_samples > 0 {
                centered.resize(musical_samples + silence_samples, (0.0_f32, 0.0_f32));
            }
            let stem_path = stems_dir.join(format!("{}.wav", track.id));
            write_stereo_wav_16bit(&stem_path, sr as u32, &centered)
                .map_err(|e| format!("Failed to write stem {}: {e}", stem_path.display()))?;
            stems_written.push(stem_path);
        }
    }

    let track_summaries = score
        .tracks
        .iter()
        .zip(placements.iter())
        .map(|(t, p)| TrackSummary {
            id: t.id.clone(),
            name: t.display_name().to_string(),
            instrument: t.instrument.clone(),
            note_count: t.notes.len(),
            pos: StagePos::new(p.x, p.y),
            width: p.width,
            gain: p.gain,
            warm_lowpass_hz: p.warm_lowpass_hz,
        })
        .collect();

    Ok(RenderResult {
        duration_seconds: audio.len() as f64 / sr as f64,
        audio,
        sample_rate: sr,
        tail_seconds: stage_params.tail_seconds,
        reverb_rt60: stage_params.reverb_rt60,
        end_silence_seconds: stage_params.end_silence_seconds,
        stage_name: stage_params.stage_name,
        tuning: opts.tuning,
        stats,
        track_summaries,
        stems_written,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::tuning::{edo53_to_12tet_midi, midi_to_12tet_freq, step_cents_to_12tet_freq, A4_STEP, DIESIS};
    use crate::visualize::render_score_svg;
    use std::time::{SystemTime, UNIX_EPOCH};

    #[test]
    fn test_parse_minimal_json_and_defaults() {
        let minimal = r#"{
            "tracks": [
                {
                    "id": "lead_piano",
                    "instrument": "piano",
                    "notes": [
                        { "beat": 0.0, "dur": 1.5, "step": 0 }
                    ]
                }
            ]
        }"#;

        let score = parse_json_score(minimal).expect("minimal score should parse");
        assert_eq!(score.title, "Untitled 53-EDO Piece");
        assert_eq!(score.description, "");
        assert_eq!(score.sample_rate, 48_000);
        assert!((score.tail_seconds - 4.5).abs() < 1e-9);
        assert!((score.reverb_rt60 - 2.25).abs() < 1e-9);
        assert!((score.end_silence_seconds - 0.0).abs() < 1e-9);
        assert_eq!(score.tempo.len(), 1);
        assert!((score.tempo[0].beat - 0.0).abs() < 1e-9);
        assert!((score.tempo[0].bpm - 70.0).abs() < 1e-9);

        assert_eq!(score.tracks.len(), 1);
        let tr = &score.tracks[0];
        assert_eq!(tr.id, "lead_piano");
        assert_eq!(tr.name, None);
        assert_eq!(tr.display_name(), "lead_piano");
        assert_eq!(tr.instrument, "piano");
        assert!((tr.x - 0.0).abs() < 1e-9);
        assert!((tr.y - 4.5).abs() < 1e-9);
        assert!((tr.gain - 1.0).abs() < 1e-9);
        assert_eq!(tr.warm_lowpass_hz, None);

        assert_eq!(tr.notes.len(), 1);
        let n = &tr.notes[0];
        assert!((n.beat - 0.0).abs() < 1e-9);
        assert!((n.dur - 1.5).abs() < 1e-9);
        assert_eq!(n.step, 0);
        assert!((n.vel - 0.75).abs() < 1e-6);
        assert!((n.cents - 0.0).abs() < 1e-6);
        assert!((n.slide_from_cents - 0.0).abs() < 1e-6);
        assert!(!n.breath_swell);
        assert!((n.meend_cents - 0.0).abs() < 1e-6);
    }

    #[test]
    fn test_parse_full_json_and_all_instruments() {
        let full = r#"{
            "title": "My 53-EDO Piece",
            "description": "Full schema test",
            "sample_rate": 48000,
            "tail_seconds": 3.0,
            "reverb_rt60": 1.9,
            "end_silence_seconds": 2.5,
            "tempo": [
                { "beat": 0.0, "bpm": 72.0 },
                { "beat": 8.0, "bpm": 84.0 }
            ],
            "tracks": [
                {
                    "id": "piano",
                    "name": "Concert Grand Piano",
                    "instrument": "piano",
                    "x": -2.4,
                    "y": 3.4,
                    "gain": 0.95,
                    "warm_lowpass_hz": null,
                    "notes": [
                        {
                            "beat": 0.0,
                            "dur": 2.0,
                            "step": 0,
                            "vel": 0.82,
                            "cents": 1.5,
                            "slide_from_cents": -12.0,
                            "breath_swell": true,
                            "meend_cents": 5.0
                        }
                    ]
                },
                {
                    "id": "sitar_warm",
                    "name": "Warm Sitar",
                    "instrument": "sitar",
                    "x": 1.5,
                    "y": 2.8,
                    "gain": 0.88,
                    "warm_lowpass_hz": 2900.0,
                    "notes": []
                }
            ]
        }"#;

        let score = parse_json_score(full).expect("full score should parse");
        assert_eq!(score.title, "My 53-EDO Piece");
        assert_eq!(score.description, "Full schema test");
        assert_eq!(score.sample_rate, 48_000);
        assert!((score.tail_seconds - 3.0).abs() < 1e-9);
        assert!((score.reverb_rt60 - 1.9).abs() < 1e-9);
        assert!((score.end_silence_seconds - 2.5).abs() < 1e-9);
        assert_eq!(score.tempo.len(), 2);
        assert_eq!(score.tracks[0].display_name(), "Concert Grand Piano");
        assert!((score.tracks[0].x - (-2.4)).abs() < 1e-9);
        assert!((score.tracks[0].y - 3.4).abs() < 1e-9);
        assert!((score.tracks[0].gain - 0.95).abs() < 1e-9);
        assert_eq!(score.tracks[1].warm_lowpass_hz, Some(2900.0));
        let n = &score.tracks[0].notes[0];
        assert!((n.vel - 0.82).abs() < 1e-6);
        assert!((n.cents - 1.5).abs() < 1e-6);
        assert!((n.slide_from_cents - (-12.0)).abs() < 1e-6);
        assert!(n.breath_swell);
        assert!((n.meend_cents - 5.0).abs() < 1e-6);

        assert_eq!(VALID_INSTRUMENTS.len(), 26);
        for name in VALID_INSTRUMENTS {
            assert!(
                ScoreInstrument::parse(name).is_ok(),
                "Expected `{name}` to be supported"
            );
        }
        assert_eq!(
            ScoreInstrument::parse("nylon_guitar").unwrap(),
            ScoreInstrument::Sf2(Sf2Instrument::NylonGuitar)
        );
        assert_eq!(
            ScoreInstrument::parse("steel_guitar").unwrap(),
            ScoreInstrument::Sf2(Sf2Instrument::SteelGuitar)
        );
    }

    #[test]
    fn test_unknown_instrument_and_validation_errors() {
        let bad_inst = r#"{
            "tracks": [
                { "id": "t1", "instrument": "kazoo_9000", "notes": [] }
            ]
        }"#;
        let err = parse_json_score(bad_inst).unwrap_err();
        assert!(
            err.contains("Unknown instrument") && err.contains("kazoo_9000"),
            "Unexpected error message: {err}"
        );

        let empty_tempo = r#"{
            "tempo": [],
            "tracks": [{ "id": "t1", "instrument": "piano", "notes": [] }]
        }"#;
        assert!(parse_json_score(empty_tempo).is_err());

        let bad_lp = r#"{
            "tracks": [{ "id": "s", "instrument": "sitar", "warm_lowpass_hz": -100.0, "notes": [] }]
        }"#;
        assert!(parse_json_score(bad_lp).is_err());

        let bad_id = r#"{
            "tracks": [{ "id": "../escape", "instrument": "piano", "notes": [] }]
        }"#;
        assert!(parse_json_score(bad_id).is_err());
    }

    #[test]
    fn test_stage_config_loading_and_precedence() {
        let score = parse_json_score(
            r#"{
                "title": "Precedence Test",
                "reverb_rt60": 2.0,
                "tail_seconds": 4.0,
                "end_silence_seconds": 1.0,
                "tracks": [
                    { "id": "piano_lead", "instrument": "piano", "x": -1.0, "y": 2.0, "gain": 0.8, "warm_lowpass_hz": 4000.0, "notes": [] },
                    { "id": "piano_two",  "instrument": "piano", "x": -1.5, "y": 2.5, "gain": 0.7, "warm_lowpass_hz": 3800.0, "notes": [] },
                    { "id": "harp_solo",  "instrument": "harp",  "x":  3.1, "y": 5.2, "gain": 0.9, "notes": [] }
                ]
            }"#,
        )
        .unwrap();

        let stage = parse_stage_config(
            r#"{
                "name": "Custom Stage",
                "reverb_rt60": 1.65,
                "tail_seconds": 5.5,
                "end_silence_seconds": 3.0,
                "players": {
                    "piano_lead": { "x": -3.2, "warm_lowpass_hz": null },
                    "piano":      { "x": -2.4, "y": 3.4, "gain": 0.95, "warm_lowpass_hz": 3100.0 }
                }
            }"#,
        )
        .unwrap();

        // Hall params precedence: CLI override > stage.json > score.json
        let params_stage = resolve_stage_params(&score, Some(&stage), None).unwrap();
        assert_eq!(params_stage.stage_name.as_deref(), Some("Custom Stage"));
        assert!((params_stage.reverb_rt60 - 1.65).abs() < 1e-9);
        assert!((params_stage.tail_seconds - 5.5).abs() < 1e-9);
        assert!((params_stage.end_silence_seconds - 3.0).abs() < 1e-9);

        let params_cli = resolve_stage_params(&score, Some(&stage), Some(30.0)).unwrap();
        assert!((params_cli.end_silence_seconds - 30.0).abs() < 1e-9);

        // Track 0 ("piano_lead"): id overrides x & explicit null LP; falls back to instrument ("piano") for y & gain
        let p0 = resolve_track_placement(&score.tracks[0], Some(&stage));
        assert!((p0.x - (-3.2)).abs() < 1e-9);
        assert!((p0.y - 3.4).abs() < 1e-9);
        assert!((p0.gain - 0.95).abs() < 1e-9);
        assert_eq!(p0.warm_lowpass_hz, None);

        // Track 1 ("piano_two"): matches instrument ("piano") in stage
        let p1 = resolve_track_placement(&score.tracks[1], Some(&stage));
        assert!((p1.x - (-2.4)).abs() < 1e-9);
        assert!((p1.y - 3.4).abs() < 1e-9);
        assert!((p1.gain - 0.95).abs() < 1e-9);
        assert_eq!(p1.warm_lowpass_hz, Some(3100.0));

        // Track 2 ("harp_solo"): not in stage -> preserves inline track fields
        let p2 = resolve_track_placement(&score.tracks[2], Some(&stage));
        assert!((p2.x - 3.1).abs() < 1e-9);
        assert!((p2.y - 5.2).abs() < 1e-9);
        assert!((p2.gain - 0.9).abs() < 1e-9);
        assert_eq!(p2.warm_lowpass_hz, None);

        // Also confirm all 3 bundled stage presets parse and validate cleanly!
        for preset in [
            "stages/concert_hall.json",
            "stages/intimate_circle.json",
            "stages/east_west_split.json",
        ] {
            let loaded = load_stage_config(preset)
                .unwrap_or_else(|e| panic!("Preset {preset} failed to load: {e}"));
            assert!(
                loaded.players.len() >= 14,
                "Preset {preset} should configure at least 14 players"
            );
        }
    }

    #[test]
    fn test_12tet_pitch_quantization() {
        // C4 (step 0) -> MIDI 60 -> 261.6256 Hz (~261.63 Hz)
        assert_eq!(edo53_to_12tet_midi(0, 0.0), 60);
        let c4_hz = step_cents_to_12tet_freq(0, 0.0);
        assert!(
            (c4_hz - 261.625565).abs() < 0.01,
            "Expected C4 ≈ 261.63 Hz, got {c4_hz}"
        );

        // DIESIS (+2) -> collapses to C4 (MIDI 60) in 12-TET!
        assert_eq!(edo53_to_12tet_midi(DIESIS, 0.0), 60);
        assert!((step_cents_to_12tet_freq(DIESIS, 0.0) - c4_hz).abs() < 1e-9);

        // A4 (step 39) -> MIDI 69 -> exact 440.00 Hz
        assert_eq!(edo53_to_12tet_midi(A4_STEP, 0.0), 69);
        assert!((midi_to_12tet_freq(69) - 440.0).abs() < 1e-9);

        // Pure 53-EDO major triad on C++ (+2 diesis: [2, 19, 33]) stays C-E-G [60, 64, 67] in 12-TET
        assert_eq!(edo53_to_12tet_midi(2, 0.0), 60);
        assert_eq!(edo53_to_12tet_midi(19, 0.0), 64);
        assert_eq!(edo53_to_12tet_midi(33, 0.0), 67);
    }

    #[test]
    fn test_warm_lowpass_attenuates_high_freq() {
        let sr = 48_000usize;
        let n = 4800usize;
        let make_sine = |hz: f64| -> Vec<(f32, f32)> {
            (0..n)
                .map(|i| {
                    let s = (2.0 * PI * hz * i as f64 / sr as f64).sin() as f32;
                    (s, s)
                })
                .collect()
        };
        let rms = |buf: &[(f32, f32)]| -> f64 {
            let slice = &buf[480..];
            let sum: f64 = slice.iter().map(|&(l, _)| (l as f64) * (l as f64)).sum();
            (sum / slice.len() as f64).sqrt()
        };

        let mut low = make_sine(300.0);
        let mut high = make_sine(8000.0);
        apply_warm_lowpass(&mut low, 2800.0, sr);
        apply_warm_lowpass(&mut high, 2800.0, sr);

        assert!(rms(&low) > 0.65, "300 Hz should pass mostly unattenuated");
        assert!(
            rms(&high) < 0.15,
            "8 kHz should be strongly attenuated at 2.8 kHz LP"
        );
    }

    #[test]
    fn test_end_silence_appends_exact_silence_without_altering_rms() {
        let json = r#"{
            "title": "Silence Test",
            "tail_seconds": 0.4,
            "tempo": [{"beat": 0.0, "bpm": 120.0}],
            "tracks": [
                {
                    "id": "ektara",
                    "instrument": "ektara",
                    "notes": [{ "beat": 0.0, "dur": 0.5, "step": 0, "vel": 0.8 }]
                }
            ]
        }"#;
        let score = parse_json_score(json).unwrap();
        let base = render_json_score(&score, &RenderOptions::default()).unwrap();

        let opts_sil = RenderOptions {
            end_silence_override: Some(1.5),
            ..RenderOptions::default()
        };
        let with_sil = render_json_score(&score, &opts_sil).unwrap();

        let expected_extra = (1.5 * 48_000.0) as usize;
        assert_eq!(with_sil.audio.len(), base.audio.len() + expected_extra);
        assert!((with_sil.stats.rms_l_db - base.stats.rms_l_db).abs() < 1e-6);
        assert!((with_sil.stats.peak_db - base.stats.peak_db).abs() < 1e-6);
        for &(l, r) in &with_sil.audio[base.audio.len()..] {
            assert_eq!(l, 0.0);
            assert_eq!(r, 0.0);
        }
    }

    #[test]
    fn test_svg_visualization_generation() {
        let json = r#"{
            "title": "Dawn & Lotus <53-EDO>",
            "tail_seconds": 1.0,
            "tempo": [{"beat": 0.0, "bpm": 80.0}],
            "tracks": [
                { "id": "piano", "name": "Concert Grand", "instrument": "piano", "notes": [
                    { "beat": 0.0, "dur": 1.0, "step": 0, "vel": 0.8 },
                    { "beat": 1.0, "dur": 1.0, "step": 2, "vel": 0.85 }
                ]},
                { "id": "sitar", "instrument": "sitar", "notes": [
                    { "beat": 0.5, "dur": 1.5, "step": 31, "vel": 0.75 }
                ]}
            ]
        }"#;
        let score = parse_json_score(json).unwrap();
        let stage = load_stage_config("stages/concert_hall.json").unwrap();

        let svg_53 = render_score_svg(&score, Some(&stage), TuningMode::Edo53, Some(5.0)).unwrap();
        assert!(svg_53.starts_with("<svg "));
        assert!(svg_53.trim_end().ends_with("</svg>"));
        assert!(svg_53.contains("width=\"1600\" height=\"960\""));
        assert!(svg_53.contains("Dawn &amp; Lotus &lt;53-EDO&gt;"));
        assert!(svg_53.contains("Keys &amp; Plucked"));
        assert!(svg_53.contains("53-EDO (Pure 5/7-Limit)"));
        assert!(svg_53.contains("Concert Grand"));
        assert!(svg_53.contains("Concert Hall"));
        assert!(svg_53.contains("3m") && svg_53.contains("12m"));

        // Verify zero unescaped '&' anywhere in generated XML
        for svg in [&svg_53] {
            let mut rest = svg.as_str();
            while let Some(idx) = rest.find('&') {
                let tail = &rest[idx..];
                assert!(
                    tail.starts_with("&amp;")
                        || tail.starts_with("&lt;")
                        || tail.starts_with("&gt;")
                        || tail.starts_with("&quot;")
                        || tail.starts_with("&apos;"),
                    "Unescaped '&' in SVG near: {}",
                    &tail[..tail.len().min(32)]
                );
                rest = &rest[idx + 1..];
            }
        }

        let svg_12 = render_score_svg(&score, Some(&stage), TuningMode::Tet12, None).unwrap();
        assert!(svg_12.contains("12-TET (Equal Temperament)"));
        assert!(svg_12.contains("12-TET quantized"));
    }

    #[test]
    fn test_render_short_multitrack_json_score_and_stems() {
        let json = r#"{
            "title": "Short 53-EDO Smoke Test",
            "description": "Multi-track SF2 + warm LP sitar + physical ektara/dotara",
            "sample_rate": 48000,
            "tail_seconds": 0.8,
            "reverb_rt60": 1.8,
            "tempo": [{"beat": 0.0, "bpm": 120.0}],
            "tracks": [
                {
                    "id": "piano",
                    "name": "Concert Grand Piano",
                    "instrument": "piano",
                    "x": -2.2,
                    "y": 3.5,
                    "gain": 0.95,
                    "notes": [
                        { "beat": 0.0, "dur": 1.5, "step": 0, "vel": 0.78 },
                        { "beat": 0.0, "dur": 1.5, "step": 17, "vel": 0.72 },
                        { "beat": 0.0, "dur": 1.5, "step": 31, "vel": 0.74 }
                    ]
                },
                {
                    "id": "clarinet",
                    "instrument": "clarinet",
                    "x": 1.4,
                    "y": 5.2,
                    "gain": 0.85,
                    "notes": [
                        { "beat": 0.25, "dur": 1.2, "step": 43, "vel": 0.76, "breath_swell": true }
                    ]
                },
                {
                    "id": "sitar",
                    "instrument": "sitar",
                    "x": -1.2,
                    "y": 2.9,
                    "gain": 0.80,
                    "warm_lowpass_hz": 3000.0,
                    "notes": [
                        { "beat": 0.5, "dur": 1.0, "step": 53, "vel": 0.74, "slide_from_cents": -35.0 }
                    ]
                },
                {
                    "id": "ektara",
                    "instrument": "ektara",
                    "x": -0.4,
                    "y": 3.2,
                    "gain": 0.75,
                    "notes": [
                        { "beat": 0.0, "dur": 1.0, "step": -53, "vel": 0.70, "meend_cents": 15.0 }
                    ]
                },
                {
                    "id": "dotara",
                    "instrument": "dotara",
                    "x": 1.6,
                    "y": 3.0,
                    "gain": 0.75,
                    "notes": [
                        { "beat": 0.5, "dur": 0.8, "step": -22, "vel": 0.72 }
                    ]
                }
            ]
        }"#;

        let score = parse_json_score(json).expect("valid test score");
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let stems_dir = std::env::temp_dir().join(format!("edo53_test_stems_{unique}"));

        let opts = RenderOptions {
            soundfont_path: PathBuf::from(DEFAULT_SOUNDFONT_PATH),
            stems_dir: Some(stems_dir.clone()),
            stage: None,
            tuning: TuningMode::Edo53,
            end_silence_override: None,
        };

        let result = render_json_score(&score, &opts).expect("render should succeed");
        assert!(!result.audio.is_empty());
        assert_eq!(result.sample_rate, 48_000);
        assert_eq!(result.stats.nan_count, 0, "must produce 0 NaNs");
        assert_eq!(result.stats.clipped_samples, 0, "must produce 0 clipping");
        assert!(
            result.stats.peak_db > -12.0 && result.stats.peak_db <= -0.5,
            "unexpected peak_db: {}",
            result.stats.peak_db
        );
        for &(l, r) in &result.audio {
            assert!(l.is_finite() && r.is_finite());
            assert!(l.abs() < 1.0 && r.abs() < 1.0);
        }

        // Also verify 12tet render succeeds cleanly with 0 NaNs / 0 clipping
        let opts_12 = RenderOptions {
            tuning: TuningMode::Tet12,
            ..RenderOptions::default()
        };
        let res_12 = render_json_score(&score, &opts_12).expect("12tet render should succeed");
        assert_eq!(res_12.tuning, TuningMode::Tet12);
        assert_eq!(res_12.stats.nan_count, 0);
        assert_eq!(res_12.stats.clipped_samples, 0);

        assert_eq!(result.track_summaries.len(), 5);
        assert_eq!(result.stems_written.len(), 5);
        for path in &result.stems_written {
            let meta = fs::metadata(path).expect("stem file should exist");
            assert!(
                meta.len() > 44,
                "stem WAV {} should contain audio frames",
                path.display()
            );
        }

        let _ = fs::remove_dir_all(&stems_dir);
    }
}
