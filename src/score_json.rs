//! Agent-friendly JSON score loader, validator, and 3D-spatialized 53-EDO renderer.

use std::f64::consts::{FRAC_1_SQRT_2, PI};
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;

use rustysynth::SoundFont;
use serde::{Deserialize, Serialize};

use crate::indian::{render_dotara_track, render_ektara_track, IndianNote};
use crate::reverb::{apply_hall_reverb_and_master_with_rt60, AudioStats};
use crate::score::{TempoMap, TempoSegment};
use crate::sf2_synth::{
    load_soundfont_result, render_sf2_track_with_sr, Sf2Instrument, Sf2Note,
    DEFAULT_SOUNDFONT_PATH,
};
use crate::spatial::{spatialize_track, StagePos};
use crate::synth::SAMPLE_RATE;
use crate::wav::write_stereo_wav_16bit;

/// All 21 instrument identifiers supported by the JSON score schema.
pub const VALID_INSTRUMENTS: [&str; 21] = [
    "piano",
    "harp",
    "celesta",
    "church_organ",
    "clarinet",
    "english_horn",
    "bassoon",
    "french_horn",
    "flute",
    "oboe",
    "shakuhachi",
    "violin",
    "viola",
    "cello",
    "contrabass",
    "string_ensemble",
    "slow_strings",
    "pizzicato",
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
    #[serde(default = "default_tempo")]
    pub tempo: Vec<JsonTempoPoint>,
    pub tracks: Vec<JsonTrack>,
}

#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
pub struct JsonTempoPoint {
    pub beat: f64,
    pub bpm: f64,
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
    #[serde(default = "default_gain")]
    pub gain: f64,
    #[serde(default)]
    pub warm_lowpass_hz: Option<f64>,
    #[serde(default)]
    pub notes: Vec<JsonNote>,
}

impl JsonTrack {
    pub fn display_name(&self) -> &str {
        self.name.as_deref().unwrap_or(&self.id)
    }
}

#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
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
    pub meend_cents: f32,
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
}

impl Default for RenderOptions {
    fn default() -> Self {
        Self {
            soundfont_path: PathBuf::from(DEFAULT_SOUNDFONT_PATH),
            stems_dir: None,
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
    pub gain: f64,
    pub warm_lowpass_hz: Option<f64>,
}

#[derive(Clone, Debug)]
pub struct RenderResult {
    pub audio: Vec<(f32, f32)>,
    pub sample_rate: usize,
    pub duration_seconds: f64,
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
                    || !note.meend_cents.is_finite()
                {
                    return Err(format!(
                        "tracks[{ti}] (`{}`).notes[{ni}] contains non-finite float values",
                        track.id
                    ));
                }
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

fn render_single_track_dry(
    track: &JsonTrack,
    inst: ScoreInstrument,
    tempo: &TempoMap,
    sf: Option<&Arc<SoundFont>>,
    sample_rate: usize,
    total_samples: usize,
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
                    Sf2Note {
                        start_sample,
                        end_sample,
                        step: n.step,
                        micro_cents: n.cents,
                        velocity: n.vel,
                        slide_from_cents: slide,
                        breath_swell: n.breath_swell,
                    }
                })
                .collect();
            render_sf2_track_with_sr(sf_arc, sf2_inst, &notes, total_samples, sample_rate)
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
                ScoreInstrument::Ektara => render_ektara_track(&notes, native_total),
                ScoreInstrument::Dotara => render_dotara_track(&notes, native_total),
                ScoreInstrument::Sf2(_) => unreachable!(),
            };
            if sample_rate == SAMPLE_RATE {
                native
            } else {
                resample_stereo_linear(&native, SAMPLE_RATE, sample_rate, total_samples)
            }
        }
    };

    if let Some(cutoff_hz) = track.warm_lowpass_hz {
        apply_warm_lowpass(&mut dry, cutoff_hz, sample_rate);
    }

    let gain = track.gain as f32;
    if (gain - 1.0).abs() > 1e-6 {
        for s in &mut dry {
            s.0 *= gain;
            s.1 *= gain;
        }
    }

    dry
}

/// Renders a validated `JsonScore` through 3D concert-stage spatialization and FDN hall reverb.
/// When `opts.stems_dir` is `Some`, also writes synchronized centered dry stems `<dir>/<track.id>.wav`.
pub fn render_json_score(
    score: &JsonScore,
    opts: &RenderOptions,
) -> Result<RenderResult, String> {
    score.validate()?;

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
    let total_secs = tempo.beat_to_seconds(max_beat) + score.tail_seconds;
    let total_samples = ((total_secs * sr as f64).ceil().max(1.0)) as usize;

    let parsed_instruments: Vec<ScoreInstrument> = score
        .tracks
        .iter()
        .map(|t| ScoreInstrument::parse(&t.instrument))
        .collect::<Result<Vec<_>, _>>()?;

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
        sum_direct: vec![(0.0_f32, 0.0_f32); total_samples],
        sum_send: vec![(0.0_f32, 0.0_f32); total_samples],
        sum_dry_mono: if want_stems {
            vec![0.0_f64; total_samples]
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
            let tempo_ref = &tempo;
            let sf_ref = sf.as_ref();

            s.spawn(move || loop {
                let idx = next_ref.fetch_add(1, Ordering::Relaxed);
                if idx >= tracks.len() {
                    break;
                }
                let track = &tracks[idx];
                let inst = insts[idx];
                let dry = render_single_track_dry(
                    track,
                    inst,
                    tempo_ref,
                    sf_ref,
                    sr,
                    total_samples,
                );
                let pos = StagePos::new(track.x, track.y);
                let (direct, send) = spatialize_track(&dry, pos, sr);

                let (opt_mono, track_peak) = if want_stems {
                    let mut mono = Vec::with_capacity(total_samples);
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
                for i in 0..total_samples {
                    guard.sum_direct[i].0 += direct[i].0;
                    guard.sum_direct[i].1 += direct[i].1;
                    guard.sum_send[i].0 += send[i].0;
                    guard.sum_send[i].1 += send[i].1;
                }
                if let Some(mono) = opt_mono {
                    guard.max_track_mono_peak = guard.max_track_mono_peak.max(track_peak);
                    for i in 0..total_samples {
                        guard.sum_dry_mono[i] += mono[i] as f64;
                    }
                    guard.stems_mono[idx] = Some(mono);
                }
            });
        }
    });

    let mix = shared.into_inner().expect("mix mutex poisoned");
    let (audio, stats) =
        apply_hall_reverb_and_master_with_rt60(&mix.sum_direct, &mix.sum_send, sr, score.reverb_rt60);

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
            let centered: Vec<(f32, f32)> = mono
                .iter()
                .map(|&m| {
                    let s = (m as f64 * stem_scale) as f32;
                    (s, s)
                })
                .collect();
            let stem_path = stems_dir.join(format!("{}.wav", track.id));
            write_stereo_wav_16bit(&stem_path, sr as u32, &centered)
                .map_err(|e| format!("Failed to write stem {}: {e}", stem_path.display()))?;
            stems_written.push(stem_path);
        }
    }

    let track_summaries = score
        .tracks
        .iter()
        .map(|t| TrackSummary {
            id: t.id.clone(),
            name: t.display_name().to_string(),
            instrument: t.instrument.clone(),
            note_count: t.notes.len(),
            pos: StagePos::new(t.x, t.y),
            gain: t.gain,
            warm_lowpass_hz: t.warm_lowpass_hz,
        })
        .collect();

    Ok(RenderResult {
        audio,
        sample_rate: sr,
        duration_seconds: total_samples as f64 / sr as f64,
        stats,
        track_summaries,
        stems_written,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
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
        let n = tr.notes[0];
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
        assert_eq!(score.tempo.len(), 2);
        assert_eq!(score.tracks[0].display_name(), "Concert Grand Piano");
        assert!((score.tracks[0].x - (-2.4)).abs() < 1e-9);
        assert!((score.tracks[0].y - 3.4).abs() < 1e-9);
        assert!((score.tracks[0].gain - 0.95).abs() < 1e-9);
        assert_eq!(score.tracks[1].warm_lowpass_hz, Some(2900.0));
        let n = score.tracks[0].notes[0];
        assert!((n.vel - 0.82).abs() < 1e-6);
        assert!((n.cents - 1.5).abs() < 1e-6);
        assert!((n.slide_from_cents - (-12.0)).abs() < 1e-6);
        assert!(n.breath_swell);
        assert!((n.meend_cents - 5.0).abs() < 1e-6);

        // Every single one of the 21 documented instrument IDs must parse cleanly
        for name in VALID_INSTRUMENTS {
            assert!(
                ScoreInstrument::parse(name).is_ok(),
                "Expected `{name}` to be supported"
            );
        }
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
        assert!(rms(&high) < 0.15, "8 kHz should be strongly attenuated at 2.8 kHz LP");
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

        assert_eq!(result.track_summaries.len(), 5);
        assert_eq!(result.stems_written.len(), 5);
        for path in &result.stems_written {
            let meta = fs::metadata(path).expect("stem file should exist");
            assert!(meta.len() > 44, "stem WAV {} should contain audio frames", path.display());
        }

        let _ = fs::remove_dir_all(&stems_dir);
    }
}
