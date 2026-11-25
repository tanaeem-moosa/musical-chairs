//! Generates isolated 53-EDO instrument auditions (including full 53-note Harp sweep,
//! Sitar, physically modeled Ektara & Dotara, and warm breathing woodwinds),
//! plus a 3D-spatialized East-meets-West Chamber Fusion preview (`output/preview_fusion.wav`)
//! and synchronized stems (`output/stems_fusion/*.wav`).

use std::collections::HashMap;
use std::fs;
use std::sync::Arc;

use rustysynth::SoundFont;

use crate::indian::{render_dotara_track, render_ektara_track, IndianNote};
use crate::reverb::{
    apply_hall_reverb_and_master, apply_hall_reverb_linear, compute_audio_stats,
    compute_target_norm_gain, scale_linear_buffer,
};
use crate::score::{TempoMap, TempoSegment};
use crate::sf2_synth::{
    load_soundfont, master_with_gentle_hall, render_sf2_track, Sf2Instrument, Sf2Note,
    DEFAULT_SOUNDFONT_PATH,
};
use crate::spatial::{spatialize_track, StagePos};
use crate::synth::SAMPLE_RATE;
use crate::tuning::{
    add9, dom7_harmonic, dom9_harmonic, maj9, major_triad, pitch, A, C, COMMA, D, DIESIS, E, F,
    G, HARM_7, M2, M3, M6, OCT, P4, P5, m3,
};
use crate::wav::write_stereo_wav_16bit;

struct StemSpec {
    id: &'static str,
    name: &'static str,
    family: &'static str,
    inst: Sf2Instrument,
    gain: f32,
}

const CHAMBER_STEMS: [StemSpec; 11] = [
    StemSpec { id: "flute", name: "Orchestral Flute", family: "Woodwinds", inst: Sf2Instrument::Flute, gain: 0.92 },
    StemSpec { id: "clarinet", name: "Clarinet", family: "Woodwinds", inst: Sf2Instrument::Clarinet, gain: 0.85 },
    StemSpec { id: "oboe", name: "Oboe", family: "Woodwinds", inst: Sf2Instrument::Oboe, gain: 0.78 },
    StemSpec { id: "harp", name: "Orchestral Harp", family: "Keys & Plucked", inst: Sf2Instrument::Harp, gain: 0.95 },
    StemSpec { id: "celesta", name: "Celesta", family: "Keys & Plucked", inst: Sf2Instrument::Celesta, gain: 0.82 },
    StemSpec { id: "violin", name: "Solo Violin", family: "Strings", inst: Sf2Instrument::Violin, gain: 0.88 },
    StemSpec { id: "viola", name: "Solo Viola", family: "Strings", inst: Sf2Instrument::Viola, gain: 0.82 },
    StemSpec { id: "cello", name: "Solo Cello", family: "Strings", inst: Sf2Instrument::Cello, gain: 0.88 },
    StemSpec { id: "contrabass", name: "Contrabass", family: "Strings", inst: Sf2Instrument::Contrabass, gain: 0.82 },
    StemSpec { id: "strings_ens", name: "String Ensemble", family: "Strings", inst: Sf2Instrument::StringEnsemble, gain: 0.78 },
    StemSpec { id: "organ", name: "Church Pipe Organ", family: "Organ", inst: Sf2Instrument::ChurchOrgan, gain: 0.68 },
];

#[derive(Clone, Copy)]
enum FusionSource {
    Sf2(Sf2Instrument),
    Ektara,
    Dotara,
}

struct FusionStemSpec {
    id: &'static str,
    name: &'static str,
    family: &'static str,
    source: FusionSource,
    gain: f32,
    pos: StagePos,
}

const FUSION_STEMS: [FusionStemSpec; 11] = [
    FusionStemSpec { id: "harp", name: "Orchestral Harp", family: "Keys & Plucked", source: FusionSource::Sf2(Sf2Instrument::Harp), gain: 1.05, pos: StagePos::new(-3.2, 3.2) },
    FusionStemSpec { id: "sitar", name: "Sitar", family: "Indian Classical", source: FusionSource::Sf2(Sf2Instrument::Sitar), gain: 0.92, pos: StagePos::new(-1.6, 2.6) },
    FusionStemSpec { id: "dotara", name: "Dotara", family: "Indian Classical", source: FusionSource::Dotara, gain: 0.90, pos: StagePos::new(1.8, 2.8) },
    FusionStemSpec { id: "ektara", name: "Ektara", family: "Indian Classical", source: FusionSource::Ektara, gain: 0.85, pos: StagePos::new(-0.4, 3.4) },
    FusionStemSpec { id: "viola", name: "Solo Viola", family: "Strings", source: FusionSource::Sf2(Sf2Instrument::Viola), gain: 0.88, pos: StagePos::new(-2.2, 4.4) },
    FusionStemSpec { id: "cello", name: "Solo Cello", family: "Strings", source: FusionSource::Sf2(Sf2Instrument::Cello), gain: 0.92, pos: StagePos::new(2.6, 4.2) },
    FusionStemSpec { id: "pizzicato", name: "Pizzicato Strings", family: "Strings", source: FusionSource::Sf2(Sf2Instrument::Pizzicato), gain: 0.96, pos: StagePos::new(0.8, 4.8) },
    FusionStemSpec { id: "clarinet", name: "Clarinet", family: "Woodwinds", source: FusionSource::Sf2(Sf2Instrument::Clarinet), gain: 0.86, pos: StagePos::new(-1.2, 5.8) },
    FusionStemSpec { id: "french_horn", name: "French Horn", family: "Brass", source: FusionSource::Sf2(Sf2Instrument::FrenchHorn), gain: 0.78, pos: StagePos::new(2.2, 8.2) },
    FusionStemSpec { id: "bassoon", name: "Bassoon", family: "Woodwinds", source: FusionSource::Sf2(Sf2Instrument::Bassoon), gain: 0.84, pos: StagePos::new(0.5, 6.6) },
    FusionStemSpec { id: "strings_ens", name: "String Ensemble", family: "Strings", source: FusionSource::Sf2(Sf2Instrument::StringEnsemble), gain: 0.82, pos: StagePos::new(0.0, 7.4) },
];

pub fn render_all_auditions() {
    fs::create_dir_all("output/audition").expect("failed to create output/audition");
    fs::create_dir_all("output/stems").expect("failed to create output/stems");
    fs::create_dir_all("output/stems_fusion").expect("failed to create output/stems_fusion");

    let sf = load_soundfont(DEFAULT_SOUNDFONT_PATH);

    println!("Rendering isolated 53-EDO instrument auditions...");
    for &inst in Sf2Instrument::all() {
        if inst == Sf2Instrument::Sitar {
            render_sitar_audition(&sf);
        } else {
            render_solo_audition(&sf, inst);
        }
    }
    render_harp_53edo_showcase(&sf);
    render_ektara_audition();
    render_dotara_audition();

    println!("Rendering classic chamber stems & preview_sf2.wav...");
    render_chamber_showcase_and_stems(&sf);

    println!("Rendering 3D-spatialized East-West 53-EDO Fusion preview & stage stems...");
    render_fusion_showcase_and_stems(&sf);

    write_manifest();
    println!("Audition studio assets ready under output/audition/, output/stems/, and output/stems_fusion/.");
}

fn beat_to_sample(tempo: &TempoMap, beat: f64) -> usize {
    (tempo.beat_to_seconds(beat) * SAMPLE_RATE as f64).round().max(0.0) as usize
}

fn render_solo_audition(sf: &Arc<SoundFont>, inst: Sf2Instrument) {
    let tempo = TempoMap::constant(72.0);
    let base = inst.base_step_offset();
    let breath = inst.uses_breath_swell();
    let mut notes = Vec::new();

    let motif = [
        (0.0, 1.15, base, 0.76),
        (1.20, 0.52, base + P5, 0.82),
        (1.75, 0.72, base + P4, 0.85),
        (2.50, 0.58, base + M3, 0.78),
        (3.10, 0.82, base + M2, 0.72),
    ];
    for &(b, d, st, vel) in &motif {
        let mut n = Sf2Note::simple(beat_to_sample(&tempo, b), beat_to_sample(&tempo, b + d), st, vel);
        n.breath_swell = breath;
        notes.push(n);
    }

    if inst.is_polyphonic() {
        let triad = major_triad(base);
        for (i, &st) in triad.iter().enumerate() {
            let offset = if inst == Sf2Instrument::Harp { i as f64 * 0.08 } else { 0.0 };
            notes.push(Sf2Note::simple(
                beat_to_sample(&tempo, 4.0 + offset),
                beat_to_sample(&tempo, 5.85),
                st,
                0.72,
            ));
        }
        let d9 = dom9_harmonic(base);
        for (i, &st) in d9.iter().enumerate() {
            let offset = if inst == Sf2Instrument::Harp || inst == Sf2Instrument::Celesta {
                i as f64 * 0.10
            } else {
                0.0
            };
            notes.push(Sf2Note::simple(
                beat_to_sample(&tempo, 6.0 + offset),
                beat_to_sample(&tempo, 7.90),
                st,
                0.74,
            ));
        }
    } else {
        let line = [
            (4.0, 0.48, base, 0.72),
            (4.5, 0.48, base + M3, 0.76),
            (5.0, 0.48, base + P5, 0.80),
            (5.5, 0.48, base + HARM_7, 0.82),
            (6.0, 1.85, base + OCT, 0.84),
        ];
        for &(b, d, st, vel) in &line {
            let mut n = Sf2Note::simple(beat_to_sample(&tempo, b), beat_to_sample(&tempo, b + d), st, vel);
            n.breath_swell = breath;
            notes.push(n);
        }
    }

    if inst.is_polyphonic() {
        let chords: [(f64, f64, Vec<i32>, f32); 4] = [
            (8.0, 0.92, major_triad(base + P4 - OCT), 0.70),
            (9.0, 0.92, major_triad(base + P4 - m3), 0.68),
            (10.0, 0.92, dom7_harmonic(base + P5 - OCT), 0.75),
            (11.0, 1.45, add9(base - COMMA), 0.72),
        ];
        for (b, d, ref chord, vel) in chords {
            for (i, &st) in chord.iter().enumerate() {
                let offset = if inst == Sf2Instrument::Harp { i as f64 * 0.05 } else { 0.0 };
                notes.push(Sf2Note::simple(
                    beat_to_sample(&tempo, b + offset),
                    beat_to_sample(&tempo, b + d),
                    st,
                    vel,
                ));
            }
        }
    } else {
        let cadence_line = [
            (8.0, 0.92, base + P4, 0.78),
            (9.0, 0.92, base + M2, 0.76),
            (10.0, 0.92, base + HARM_7 - OCT + P5, 0.74),
            (11.0, 1.45, base - COMMA, 0.74),
        ];
        for &(b, d, st, vel) in &cadence_line {
            let mut n = Sf2Note::simple(beat_to_sample(&tempo, b), beat_to_sample(&tempo, b + d), st, vel);
            n.breath_swell = breath;
            notes.push(n);
        }
    }

    let total_samples = beat_to_sample(&tempo, 12.6) + (2.5 * SAMPLE_RATE as f64) as usize;
    let dry = render_sf2_track(sf, inst, &notes, total_samples);
    let (mastered, stats) = master_with_gentle_hall(&dry, inst.reverb_send());
    let path = format!("output/audition/{}.wav", inst.id());
    write_stereo_wav_16bit(&path, SAMPLE_RATE as u32, &mastered).expect("write solo wav");
    println!(
        "  - {:<25} -> {} (Peak {:.2} dB, RMS {:.2} dB)",
        inst.name(),
        path,
        stats.peak_db,
        stats.rms_l_db
    );
}

/// Dedicated Full 53-Note Octave Harp Showcase: ascending all 53 steps + Debussy/shruti bloom.
fn render_harp_53edo_showcase(sf: &Arc<SoundFont>) {
    let tempo = TempoMap::constant(72.0);
    let mut notes = Vec::new();

    // Beats 0..10.6: Silky ascending glissando through EVERY SINGLE ONE of the 53 steps (0..=53)
    for step in 0..=OCT {
        let b = step as f64 * 0.19;
        let accent = if matches!(step, 0 | 17 | 31 | 43 | 53) { 0.88 } else { 0.66 };
        notes.push(Sf2Note::simple(
            beat_to_sample(&tempo, b),
            beat_to_sample(&tempo, b + 1.8),
            step,
            accent,
        ));
    }

    // Beats 11.2..16.5: Pure 5-limit -> 7-limit -> diesis(+2) -> comma-resolved home bloom
    for (idx, &st) in [-OCT, -OCT + P5, 0, M3, P5, OCT, OCT + M3].iter().enumerate() {
        let b = 11.2 + idx as f64 * 0.10;
        notes.push(Sf2Note::simple(beat_to_sample(&tempo, b), beat_to_sample(&tempo, 13.4), st, 0.78));
    }
    for (idx, &st) in dom9_harmonic(0).iter().enumerate() {
        let b = 13.6 + idx as f64 * 0.12;
        notes.push(Sf2Note::simple(beat_to_sample(&tempo, b), beat_to_sample(&tempo, 16.5), st, 0.80));
    }

    let total_samples = beat_to_sample(&tempo, 17.0) + (2.8 * SAMPLE_RATE as f64) as usize;
    let dry = render_sf2_track(sf, Sf2Instrument::Harp, &notes, total_samples);
    let (mastered, stats) = master_with_gentle_hall(&dry, 0.25);
    let path = "output/audition/harp_53edo.wav";
    write_stereo_wav_16bit(path, SAMPLE_RATE as u32, &mastered).expect("write harp_53edo.wav");
    println!(
        "  - {:<25} -> {} (Peak {:.2} dB, RMS {:.2} dB)",
        "Harp Full 53-Note Sweep", path, stats.peak_db, stats.rms_l_db
    );
}

/// Solo Sitar playing Indian 22-shruti 53-EDO pitches with smooth meend glides.
fn render_sitar_audition(sf: &Arc<SoundFont>) {
    let tempo = TempoMap::constant(72.0);
    // Shruti steps in 53-EDO: Sa=0, Komal Re=5, Shuddha Ga=17, Tivra Ma=26, Pa=31, Komal Dha=36, Shuddha Dha=39, Komal Ni=43(7:4), Sa'=53
    let phrase: [(f64, f64, i32, f32, f32); 11] = [
        (0.0, 1.4, 0, 0.82, 0.0),
        (1.5, 0.9, 17, 0.80, -110.0),  // meend slide up into pure 5:4 Ga
        (2.5, 0.8, 26, 0.78, -90.0),   // meend up to Tivra Ma
        (3.4, 1.2, 31, 0.84, -85.0),   // land on pure Pa
        (4.8, 0.9, 43, 0.82, -120.0),  // meend into 7:4 Komal Ni
        (5.8, 1.4, OCT, 0.86, -150.0), // meend up to Sa'
        (7.5, 0.6, 39, 0.76, 90.0),    // slide down to Shuddha Dha
        (8.2, 0.6, 31, 0.78, 0.0),
        (8.9, 0.6, 17, 0.76, 0.0),
        (9.6, 0.7, 5, 0.74, 80.0),     // Komal Re (16:15 = 5 steps)
        (10.4, 2.0, 0, 0.84, 113.0),   // glide home to Sa
    ];

    let mut notes = Vec::new();
    // Soft sympathetic Sa/Pa drone plucks at phrase starts
    for &b in &[0.0, 4.8, 10.4] {
        notes.push(Sf2Note::simple(beat_to_sample(&tempo, b), beat_to_sample(&tempo, b + 2.5), -OCT, 0.45));
        notes.push(Sf2Note::simple(beat_to_sample(&tempo, b + 0.08), beat_to_sample(&tempo, b + 2.5), -OCT + P5, 0.40));
    }
    for &(b, d, st, vel, slide) in &phrase {
        notes.push(Sf2Note {
            start_sample: beat_to_sample(&tempo, b),
            end_sample: beat_to_sample(&tempo, b + d),
            step: st,
            micro_cents: 0.0,
            velocity: vel,
            slide_from_cents: slide,
            breath_swell: false,
        });
    }

    let total_samples = beat_to_sample(&tempo, 12.6) + (2.5 * SAMPLE_RATE as f64) as usize;
    let dry = render_sf2_track(sf, Sf2Instrument::Sitar, &notes, total_samples);
    let (mastered, stats) = master_with_gentle_hall(&dry, 0.22);
    let path = "output/audition/sitar.wav";
    write_stereo_wav_16bit(path, SAMPLE_RATE as u32, &mastered).expect("write sitar.wav");
    println!(
        "  - {:<25} -> {} (Peak {:.2} dB, RMS {:.2} dB)",
        "Sitar (Meend + 22-Shruti)", path, stats.peak_db, stats.rms_l_db
    );
}

fn render_ektara_audition() {
    let tempo = TempoMap::constant(72.0);
    let hits: [(f64, f64, i32, f32, f32); 14] = [
        (0.0, 0.9, -OCT, 0.82, 22.0),
        (1.0, 0.5, -OCT + P5, 0.72, 14.0),
        (1.5, 0.5, -OCT, 0.74, 18.0),
        (2.0, 0.9, -OCT + M3, 0.80, -30.0),
        (3.0, 0.9, -OCT + P5, 0.78, 20.0),
        (4.0, 0.5, 0, 0.86, 28.0),
        (4.5, 0.5, -OCT + P5, 0.74, 10.0),
        (5.0, 1.0, 0, 0.84, 24.0),
        (6.0, 0.9, HARM_7 - OCT, 0.78, -25.0),
        (7.0, 0.9, -OCT + P4, 0.76, 15.0),
        (8.0, 0.9, -OCT + M3, 0.78, 18.0),
        (9.0, 0.9, -OCT + M2, 0.74, 12.0),
        (10.0, 1.0, -OCT + P5, 0.80, 18.0),
        (11.0, 1.5, -OCT, 0.86, 25.0),
    ];
    let notes: Vec<IndianNote> = hits
        .iter()
        .map(|&(b, d, st, vel, meend)| IndianNote {
            start_sample: beat_to_sample(&tempo, b),
            end_sample: beat_to_sample(&tempo, b + d),
            step: st,
            velocity: vel,
            meend_cents: meend,
        })
        .collect();
    let total_samples = beat_to_sample(&tempo, 12.6) + (2.4 * SAMPLE_RATE as f64) as usize;
    let dry = render_ektara_track(&notes, total_samples);
    let (mastered, stats) = master_with_gentle_hall(&dry, 0.20);
    let path = "output/audition/ektara.wav";
    write_stereo_wav_16bit(path, SAMPLE_RATE as u32, &mastered).expect("write ektara.wav");
    println!(
        "  - {:<25} -> {} (Peak {:.2} dB, RMS {:.2} dB)",
        "Ektara (Physical Model)", path, stats.peak_db, stats.rms_l_db
    );
}

fn render_dotara_audition() {
    let tempo = TempoMap::constant(72.0);
    let hits: [(f64, f64, i32, f32); 19] = [
        (0.0, 0.55, -P4, 0.82),
        (0.5, 0.55, 0, 0.85),
        (1.0, 0.55, M3, 0.80),
        (1.5, 0.55, P5, 0.86),
        (2.0, 0.8, P4, 0.82),
        (2.85, 0.45, M3, 0.76),
        (3.35, 0.65, M2, 0.74),
        (4.0, 0.5, 0, 0.84),
        (4.5, 0.5, M3, 0.78),
        (5.0, 0.5, P5, 0.82),
        (5.5, 0.5, HARM_7, 0.84),
        (6.0, 1.2, OCT, 0.88),
        (7.5, 0.5, P5, 0.78),
        (8.0, 0.8, P4, 0.80),
        (9.0, 0.8, M2, 0.76),
        (10.0, 0.5, -P4, 0.78),
        (10.5, 0.5, M3, 0.80),
        (11.0, 0.5, P5, 0.82),
        (11.5, 1.2, -COMMA, 0.84),
    ];
    let notes: Vec<IndianNote> = hits
        .iter()
        .map(|&(b, d, st, vel)| IndianNote {
            start_sample: beat_to_sample(&tempo, b),
            end_sample: beat_to_sample(&tempo, b + d),
            step: st,
            velocity: vel,
            meend_cents: 0.0,
        })
        .collect();
    let total_samples = beat_to_sample(&tempo, 12.6) + (2.4 * SAMPLE_RATE as f64) as usize;
    let dry = render_dotara_track(&notes, total_samples);
    let (mastered, stats) = master_with_gentle_hall(&dry, 0.20);
    let path = "output/audition/dotara.wav";
    write_stereo_wav_16bit(path, SAMPLE_RATE as u32, &mastered).expect("write dotara.wav");
    println!(
        "  - {:<25} -> {} (Peak {:.2} dB, RMS {:.2} dB)",
        "Dotara (Physical Model)", path, stats.peak_db, stats.rms_l_db
    );
}

fn push_note(
    map: &mut HashMap<&'static str, Vec<Sf2Note>>,
    tempo: &TempoMap,
    stem_id: &'static str,
    start_b: f64,
    dur_b: f64,
    step: i32,
    vel: f32,
) {
    map.entry(stem_id).or_default().push(Sf2Note::simple(
        beat_to_sample(tempo, start_b),
        beat_to_sample(tempo, start_b + dur_b),
        step,
        vel.clamp(0.05, 1.0),
    ));
}

fn push_wind(
    map: &mut HashMap<&'static str, Vec<Sf2Note>>,
    tempo: &TempoMap,
    stem_id: &'static str,
    start_b: f64,
    dur_b: f64,
    step: i32,
    vel: f32,
) {
    let mut n = Sf2Note::simple(
        beat_to_sample(tempo, start_b),
        beat_to_sample(tempo, start_b + dur_b),
        step,
        vel.clamp(0.05, 1.0),
    );
    n.breath_swell = true;
    map.entry(stem_id).or_default().push(n);
}

fn push_sitar(
    map: &mut HashMap<&'static str, Vec<Sf2Note>>,
    tempo: &TempoMap,
    start_b: f64,
    dur_b: f64,
    step: i32,
    vel: f32,
    slide_from_cents: f32,
) {
    map.entry("sitar").or_default().push(Sf2Note {
        start_sample: beat_to_sample(tempo, start_b),
        end_sample: beat_to_sample(tempo, start_b + dur_b),
        step,
        micro_cents: 0.0,
        velocity: vel.clamp(0.05, 1.0),
        slide_from_cents,
        breath_swell: false,
    });
}

fn push_arp(
    map: &mut HashMap<&'static str, Vec<Sf2Note>>,
    tempo: &TempoMap,
    stem_id: &'static str,
    start_b: f64,
    dur_b: f64,
    spacing_b: f64,
    steps: &[i32],
    vel: f32,
) {
    for (i, &st) in steps.iter().enumerate() {
        push_note(map, tempo, stem_id, start_b + i as f64 * spacing_b, dur_b, st, vel);
    }
}

fn render_chamber_showcase_and_stems(sf: &Arc<SoundFont>) {
    let tempo = TempoMap::from_segments(vec![
        TempoSegment { beat: 0.0, bpm: 72.0 },
        TempoSegment { beat: 16.0, bpm: 74.0 },
        TempoSegment { beat: 28.0, bpm: 78.0 },
        TempoSegment { beat: 38.0, bpm: 72.0 },
        TempoSegment { beat: 44.0, bpm: 60.0 },
    ]);

    let mut tracks: HashMap<&'static str, Vec<Sf2Note>> = HashMap::new();

    push_arp(&mut tracks, &tempo, "harp", 0.0, 2.8, 0.42, &[-OCT, -OCT + P5, 0, M3, P5, OCT, OCT + M2, OCT + M3], 0.68);
    for &(b, d, st, v) in &[
        (1.0, 1.35, OCT, 0.72),
        (2.4, 0.55, OCT + P5, 0.76),
        (3.0, 0.90, OCT + P4, 0.78),
        (3.95, 0.50, OCT + M3, 0.72),
        (4.5, 1.40, OCT + M2, 0.68),
    ] {
        push_wind(&mut tracks, &tempo, "flute", b, d, st, v);
    }

    push_arp(&mut tracks, &tempo, "harp", 4.0, 2.6, 0.42, &[-OCT - m3, -P4, -m3, 0, M2, M3, P5, OCT], 0.66);
    push_note(&mut tracks, &tempo, "cello", 4.0, 3.6, -m3, 0.62);
    push_note(&mut tracks, &tempo, "viola", 4.2, 3.4, -m3 + P5, 0.58);
    for &(b, d, st, v) in &[(5.5, 0.95, 0, 0.66), (6.5, 0.50, P5, 0.70), (7.0, 0.90, P4, 0.68)] {
        push_wind(&mut tracks, &tempo, "clarinet", b, d, st, v);
    }

    for &st in &[-P4, 0, M3, P5] {
        push_note(&mut tracks, &tempo, "strings_ens", 8.0, 3.8, st, 0.62);
    }
    push_note(&mut tracks, &tempo, "contrabass", 8.0, 3.6, pitch(F, 2), 0.64);
    push_arp(&mut tracks, &tempo, "harp", 8.0, 2.4, 0.35, &maj9(-31 + OCT), 0.72);
    push_arp(&mut tracks, &tempo, "celesta", 9.0, 2.0, 0.28, &maj9(P4), 0.62);
    push_note(&mut tracks, &tempo, "violin", 8.0, 2.2, OCT + M3, 0.74);
    push_note(&mut tracks, &tempo, "violin", 10.25, 1.5, OCT + P4, 0.72);
    push_wind(&mut tracks, &tempo, "oboe", 8.5, 1.8, OCT + M2, 0.64);
    push_wind(&mut tracks, &tempo, "oboe", 10.35, 1.4, OCT + M3, 0.62);

    let g_d9 = dom9_harmonic(-22);
    for &st in &[-22, -22 + M3, -22 + HARM_7, M2] {
        push_note(&mut tracks, &tempo, "strings_ens", 12.0, 3.8, st, 0.66);
    }
    push_note(&mut tracks, &tempo, "contrabass", 12.0, 3.5, pitch(G, 2), 0.68);
    push_arp(&mut tracks, &tempo, "harp", 12.0, 2.4, 0.35, &[g_d9[0], g_d9[2], g_d9[1] + OCT, g_d9[3] + OCT, g_d9[4]], 0.74);
    push_arp(&mut tracks, &tempo, "celesta", 13.0, 2.0, 0.25, &dom9_harmonic(P5), 0.66);
    push_wind(&mut tracks, &tempo, "flute", 12.0, 1.8, OCT + M3 + M2, 0.74);
    push_wind(&mut tracks, &tempo, "flute", 14.0, 1.8, OCT + P5, 0.78);
    push_wind(&mut tracks, &tempo, "clarinet", 12.0, 3.5, -22 + HARM_7, 0.66);

    let mediants: [(f64, f64, i32, f32); 4] = [
        (16.0, 4.0, 0, 0.70),
        (20.0, 4.0, -M3, 0.75),
        (24.0, 4.0, -2 * M3, 0.82),
        (28.0, 4.0, DIESIS, 0.88),
    ];
    for (idx, &(start, dur, root, vel)) in mediants.iter().enumerate() {
        push_note(&mut tracks, &tempo, "contrabass", start, dur - 0.35, root - OCT, vel * 0.78);
        if idx >= 2 {
            push_note(&mut tracks, &tempo, "organ", start, dur - 0.15, root - OCT, vel * 0.68);
        }
        let tri = major_triad(root);
        for p in 0..6 {
            let pt = start + p as f64 * 0.5;
            let accent = if p % 2 == 0 { 0.85 } else { 0.68 };
            push_note(&mut tracks, &tempo, "cello", pt, 0.44, tri[0], vel * accent);
            push_note(&mut tracks, &tempo, "viola", pt, 0.44, tri[1], vel * accent * 0.92);
        }
        push_note(&mut tracks, &tempo, "cello", start + 3.0, 0.9, tri[2], vel * 0.76);
        push_note(&mut tracks, &tempo, "viola", start + 3.0, 0.9, tri[1], vel * 0.72);
        push_note(&mut tracks, &tempo, "strings_ens", start, dur - 0.2, root + P5, vel * 0.70);

        let mel_root = root + OCT;
        for &(dt, md, st) in &[
            (0.0, 1.3, mel_root),
            (1.35, 0.55, mel_root + P5),
            (1.95, 0.95, mel_root + P4),
            (2.95, 0.90, mel_root + M3),
        ] {
            push_note(&mut tracks, &tempo, "violin", start + dt, md, st, vel * 0.88);
            if idx >= 1 {
                push_wind(&mut tracks, &tempo, "flute", start + dt, md, st, vel * 0.80);
            }
            if idx >= 2 {
                push_wind(&mut tracks, &tempo, "oboe", start + dt, md, st - M6, vel * 0.68);
            }
        }
        push_wind(&mut tracks, &tempo, "clarinet", start + 0.3, dur - 0.5, root + M3, vel * 0.66);
        let sweep = if idx >= 2 { dom9_harmonic(root) } else { add9(root) };
        push_arp(&mut tracks, &tempo, "harp", start, 2.0, 0.32, &sweep, vel * 0.78);
        push_arp(&mut tracks, &tempo, "celesta", start + 1.8, 1.8, 0.24, &sweep, vel * 0.68);
    }

    for &(t0, k, vel) in &[(32.0, DIESIS, 0.78_f32), (36.0, COMMA, 0.72_f32)] {
        let iv_root = k + P4 - OCT;
        let ii_root = k + P4 - m3;
        let v_root = ii_root + P4 - OCT;
        let next_i = k - COMMA;

        push_note(&mut tracks, &tempo, "contrabass", t0, 0.92, iv_root, vel * 0.76);
        push_note(&mut tracks, &tempo, "cello", t0, 0.92, iv_root + P5, vel * 0.80);
        push_note(&mut tracks, &tempo, "viola", t0, 0.92, iv_root + OCT, vel * 0.76);
        push_note(&mut tracks, &tempo, "violin", t0, 0.92, iv_root + OCT + P5, vel * 0.84);
        push_wind(&mut tracks, &tempo, "flute", t0, 0.92, k + OCT + P4, vel * 0.78);

        push_note(&mut tracks, &tempo, "contrabass", t0 + 1.0, 0.92, ii_root - OCT, vel * 0.74);
        push_note(&mut tracks, &tempo, "cello", t0 + 1.0, 0.92, ii_root, vel * 0.78);
        push_note(&mut tracks, &tempo, "viola", t0 + 1.0, 0.92, ii_root + m3, vel * 0.76);
        push_note(&mut tracks, &tempo, "violin", t0 + 1.0, 0.92, ii_root + OCT, vel * 0.82);
        push_wind(&mut tracks, &tempo, "clarinet", t0 + 1.0, 0.92, ii_root + m3, vel * 0.72);

        push_note(&mut tracks, &tempo, "contrabass", t0 + 2.0, 0.92, v_root, vel * 0.76);
        push_note(&mut tracks, &tempo, "cello", t0 + 2.0, 0.92, v_root + P5, vel * 0.78);
        push_note(&mut tracks, &tempo, "viola", t0 + 2.0, 0.92, v_root + OCT + M3, vel * 0.76);
        push_note(&mut tracks, &tempo, "violin", t0 + 2.0, 0.92, v_root + OCT + HARM_7, vel * 0.82);
        push_arp(&mut tracks, &tempo, "harp", t0 + 2.0, 1.5, 0.16, &dom7_harmonic(v_root + OCT), vel * 0.72);

        push_note(&mut tracks, &tempo, "contrabass", t0 + 3.0, 0.95, next_i - OCT, vel * 0.74);
        push_note(&mut tracks, &tempo, "cello", t0 + 3.0, 0.95, next_i, vel * 0.76);
        push_note(&mut tracks, &tempo, "viola", t0 + 3.0, 0.95, next_i + M3, vel * 0.74);
        push_note(&mut tracks, &tempo, "violin", t0 + 3.0, 0.95, next_i + OCT, vel * 0.80);
        push_arp(&mut tracks, &tempo, "celesta", t0 + 3.0, 1.5, 0.18, &major_triad(next_i + OCT), vel * 0.62);
    }

    push_note(&mut tracks, &tempo, "contrabass", 40.0, 4.0, -OCT, 0.62);
    push_note(&mut tracks, &tempo, "organ", 40.0, 3.8, -OCT, 0.50);
    for &st in &[0, M3, P5, OCT + M2] {
        push_note(&mut tracks, &tempo, "strings_ens", 40.0, 4.0, st, 0.62);
    }
    push_note(&mut tracks, &tempo, "violin", 40.0, 3.8, OCT + M3, 0.70);
    push_wind(&mut tracks, &tempo, "flute", 40.0, 3.8, OCT + P5, 0.68);
    push_wind(&mut tracks, &tempo, "clarinet", 40.0, 3.8, M3, 0.58);
    push_wind(&mut tracks, &tempo, "oboe", 40.0, 3.5, OCT, 0.54);
    push_arp(&mut tracks, &tempo, "harp", 40.0, 3.2, 0.30, &[-OCT, -OCT + P5, 0, M3, P5, OCT, OCT + M2, OCT + P5, 2 * OCT], 0.70);
    push_arp(&mut tracks, &tempo, "celesta", 41.0, 2.8, 0.35, &[OCT, OCT + M3, OCT + P5, 2 * OCT], 0.58);

    let total_samples = beat_to_sample(&tempo, 44.0) + (3.8 * SAMPLE_RATE as f64) as usize;

    let mut stem_linears: Vec<(&StemSpec, Vec<(f64, f64)>)> = Vec::with_capacity(CHAMBER_STEMS.len());
    let mut sum_linear = vec![(0.0_f64, 0.0_f64); total_samples];

    for spec in &CHAMBER_STEMS {
        let notes = tracks.get(spec.id).map(|v| v.as_slice()).unwrap_or(&[]);
        let mut dry = render_sf2_track(sf, spec.inst, notes, total_samples);
        for s in &mut dry {
            s.0 *= spec.gain;
            s.1 *= spec.gain;
        }
        let rev_amt = spec.inst.reverb_send();
        let send: Vec<(f32, f32)> = dry.iter().map(|&(l, r)| (l * rev_amt, r * rev_amt)).collect();
        let linear = apply_hall_reverb_linear(&dry, &send, SAMPLE_RATE);

        for (i, &(l, r)) in linear.iter().enumerate() {
            sum_linear[i].0 += l;
            sum_linear[i].1 += r;
        }
        stem_linears.push((spec, linear));
    }

    let shared_gain = compute_target_norm_gain(&sum_linear);
    let full_mix = scale_linear_buffer(&sum_linear, shared_gain);
    let stats = compute_audio_stats(&full_mix);

    write_stereo_wav_16bit("output/preview_sf2.wav", SAMPLE_RATE as u32, &full_mix)
        .expect("write preview_sf2.wav");
    println!(
        "  - Chamber Full Mix     -> output/preview_sf2.wav ({:.2}s, Peak {:.2} dB, RMS {:.2} dB, Clipped {})",
        total_samples as f64 / SAMPLE_RATE as f64,
        stats.peak_db,
        stats.rms_l_db,
        stats.clipped_samples
    );

    for (spec, linear) in &stem_linears {
        let stem_audio = scale_linear_buffer(linear, shared_gain);
        let stem_path = format!("output/stems/{}.wav", spec.id);
        write_stereo_wav_16bit(&stem_path, SAMPLE_RATE as u32, &stem_audio).expect("write stem wav");
    }
}

/// Renders the new 3D-spatialized East-meets-West 53-EDO Chamber Fusion preview (`output/preview_fusion.wav`)
/// using ONLY the user's keeper instruments + Sitar, Ektara, Dotara, and Bassoon.
fn render_fusion_showcase_and_stems(sf: &Arc<SoundFont>) {
    let tempo = TempoMap::from_segments(vec![
        TempoSegment { beat: 0.0, bpm: 70.0 },
        TempoSegment { beat: 12.0, bpm: 72.0 },
        TempoSegment { beat: 24.0, bpm: 76.0 },
        TempoSegment { beat: 36.0, bpm: 72.0 },
        TempoSegment { beat: 48.0, bpm: 60.0 },
    ]);

    let mut sf2_tracks: HashMap<&'static str, Vec<Sf2Note>> = HashMap::new();
    let mut ektara_notes: Vec<IndianNote> = Vec::new();
    let mut dotara_notes: Vec<IndianNote> = Vec::new();

    let push_ekt = |list: &mut Vec<IndianNote>, b: f64, d: f64, step: i32, vel: f32, meend: f32| {
        list.push(IndianNote {
            start_sample: beat_to_sample(&tempo, b),
            end_sample: beat_to_sample(&tempo, b + d),
            step,
            velocity: vel,
            meend_cents: meend,
        });
    };
    let push_dot = |list: &mut Vec<IndianNote>, b: f64, d: f64, step: i32, vel: f32| {
        list.push(IndianNote {
            start_sample: beat_to_sample(&tempo, b),
            end_sample: beat_to_sample(&tempo, b + d),
            step,
            velocity: vel,
            meend_cents: 0.0,
        });
    };

    // =========================================================================
    // Phrase 1 (Beats 0..12): Intimate East-West Plucked Dialogue
    //   C add9 (0..4) -> A minor 9 (4..8) -> F major 9 (8..12)
    // =========================================================================
    push_arp(&mut sf2_tracks, &tempo, "harp", 0.0, 2.8, 0.32, &[
        pitch(C, 3), pitch(G, 3), pitch(C, 4), pitch(E, 4), pitch(G, 4), pitch(C, 5), pitch(D, 5), pitch(E, 5),
    ], 0.72);
    push_arp(&mut sf2_tracks, &tempo, "harp", 4.0, 2.8, 0.32, &[
        pitch(A, 2), pitch(E, 3), pitch(A, 3), pitch(C, 4), pitch(E, 4), pitch(G, 4), pitch(A, 4), pitch(C, 5),
    ], 0.70);
    push_arp(&mut sf2_tracks, &tempo, "harp", 8.0, 2.8, 0.34, &[
        pitch(F, 3), pitch(C, 4), pitch(F, 4), pitch(A, 4), pitch(C, 5), pitch(E, 5), pitch(G, 5),
    ], 0.74);

    // Pizzicato walking bass foundation (exact F2 and G2 roots!)
    for &(b, st) in &[
        (0.0, pitch(C, 3)), (2.0, pitch(G, 2)),
        (4.0, pitch(A, 2)), (6.0, pitch(E, 3)),
        (8.0, pitch(F, 2)), (10.0, pitch(C, 3)),
    ] {
        push_note(&mut sf2_tracks, &tempo, "pizzicato", b, 0.85, st, 0.72);
    }

    // Sitar sings strictly on chord tones with gentle meend slides
    for &(b, d, st, vel, slide) in &[
        (0.5, 1.4, pitch(C, 4), 0.76, 0.0),
        (2.0, 1.0, pitch(G, 4), 0.78, -45.0),
        (3.1, 0.85, pitch(E, 4), 0.74, 0.0),
        (4.2, 1.4, pitch(E, 4), 0.78, -40.0),
        (5.8, 1.1, pitch(C, 4), 0.74, 0.0),
        (7.0, 0.9, pitch(A, 3), 0.72, 0.0),
        (8.5, 1.4, pitch(F, 4), 0.78, -40.0),
        (10.0, 1.6, pitch(A, 4), 0.76, -45.0),
    ] {
        push_sitar(&mut sf2_tracks, &tempo, b, d, st, vel, slide);
    }

    // Dotara agile rhythmic interplay + Ektara earthy pulse (strictly chord tones)
    for &(b, st, vel) in &[
        (1.0, pitch(G, 3), 0.68), (1.5, pitch(C, 4), 0.70), (2.5, pitch(E, 4), 0.72), (3.5, pitch(D, 4), 0.66),
        (5.0, pitch(A, 3), 0.68), (5.5, pitch(C, 4), 0.72), (6.5, pitch(E, 4), 0.70), (7.5, pitch(G, 4), 0.66),
        (9.0, pitch(C, 4), 0.70), (9.5, pitch(F, 4), 0.74), (10.5, pitch(A, 4), 0.72), (11.5, pitch(C, 5), 0.68),
    ] {
        push_dot(&mut dotara_notes, b, 0.55, st, vel);
    }
    for &(b, st, meend) in &[
        (0.0, pitch(C, 3), 10.0), (4.0, pitch(A, 2), 10.0), (8.0, pitch(F, 2), 10.0),
    ] {
        push_ekt(&mut ektara_notes, b, 1.2, st, 0.72, meend);
    }

    // =========================================================================
    // Phrase 2 (Beats 12..24): Mozartian Canon + Debussy 7-Limit Bloom
    //   12..16: G dom9(7:4) | 16..20: C add9 | 20..22: F maj7 | 22..24: G dom9(7:4)
    // =========================================================================
    // Beats 12..16: G dom9 (7:4)
    push_wind(&mut sf2_tracks, &tempo, "bassoon", 12.0, 3.8, pitch(G, 2), 0.68);
    for &st in &[pitch(G, 3) + M3, pitch(G, 3) + P5, pitch(G, 3) + HARM_7] {
        push_note(&mut sf2_tracks, &tempo, "strings_ens", 12.0, 3.8, st, 0.60);
    }
    push_note(&mut sf2_tracks, &tempo, "cello", 12.0, 2.0, pitch(G, 3), 0.74);
    push_note(&mut sf2_tracks, &tempo, "cello", 14.0, 1.8, pitch(D, 4), 0.72);
    push_note(&mut sf2_tracks, &tempo, "viola", 13.0, 1.4, pitch(G, 3) + M3, 0.68);
    push_note(&mut sf2_tracks, &tempo, "viola", 14.5, 1.4, pitch(G, 3) + P5, 0.70);
    for &(b, d, st, v) in &[
        (12.0, 1.4, pitch(G, 3) + P5, 0.72),
        (13.5, 0.65, pitch(G, 3) + OCT + M2, 0.74),
        (14.2, 1.0, pitch(G, 4), 0.76),
        (15.3, 0.65, pitch(G, 3) + HARM_7, 0.72),
    ] {
        push_wind(&mut sf2_tracks, &tempo, "clarinet", b, d, st, v);
    }
    push_arp(&mut sf2_tracks, &tempo, "harp", 12.0, 2.4, 0.34, &dom9_harmonic(pitch(G, 3)), 0.72);

    // Beats 16..20: C add9
    push_wind(&mut sf2_tracks, &tempo, "bassoon", 16.0, 3.8, pitch(C, 3), 0.70);
    for &st in &[pitch(C, 4), pitch(E, 4), pitch(G, 4)] {
        push_note(&mut sf2_tracks, &tempo, "strings_ens", 16.0, 3.8, st, 0.64);
    }
    push_note(&mut sf2_tracks, &tempo, "cello", 16.0, 2.0, pitch(G, 3), 0.74);
    push_note(&mut sf2_tracks, &tempo, "cello", 18.0, 1.8, pitch(C, 4), 0.76);
    push_note(&mut sf2_tracks, &tempo, "viola", 17.0, 1.4, pitch(C, 5), 0.72);
    push_note(&mut sf2_tracks, &tempo, "viola", 18.5, 1.4, pitch(G, 4), 0.70);
    push_wind(&mut sf2_tracks, &tempo, "clarinet", 16.0, 1.8, pitch(E, 4), 0.76);
    push_wind(&mut sf2_tracks, &tempo, "clarinet", 18.0, 1.8, pitch(G, 4), 0.74);
    push_arp(&mut sf2_tracks, &tempo, "harp", 16.0, 2.4, 0.34, &add9(pitch(C, 4)), 0.72);
    push_sitar(&mut sf2_tracks, &tempo, 16.5, 1.6, pitch(G, 4), 0.68, -35.0);
    push_sitar(&mut sf2_tracks, &tempo, 18.2, 1.5, pitch(E, 4), 0.66, 0.0);

    // Beats 20..22: F maj7
    push_wind(&mut sf2_tracks, &tempo, "bassoon", 20.0, 1.9, pitch(F, 2), 0.72);
    for &st in &[pitch(F, 3), pitch(A, 3), pitch(C, 4), pitch(E, 4)] {
        push_note(&mut sf2_tracks, &tempo, "strings_ens", 20.0, 1.9, st, 0.66);
    }
    push_note(&mut sf2_tracks, &tempo, "cello", 20.0, 1.9, pitch(F, 3), 0.76);
    push_note(&mut sf2_tracks, &tempo, "viola", 20.2, 1.7, pitch(A, 4), 0.72);
    push_wind(&mut sf2_tracks, &tempo, "clarinet", 20.0, 1.9, pitch(C, 5), 0.78);
    push_arp(&mut sf2_tracks, &tempo, "harp", 20.0, 1.6, 0.25, &[
        pitch(F, 3), pitch(C, 4), pitch(F, 4), pitch(A, 4), pitch(C, 5),
    ], 0.74);

    // Beats 22..24: G dom9 (7:4)
    push_wind(&mut sf2_tracks, &tempo, "bassoon", 22.0, 1.9, pitch(G, 2), 0.72);
    for &st in &[pitch(G, 3), pitch(G, 3) + M3, pitch(G, 3) + P5, pitch(G, 3) + HARM_7] {
        push_note(&mut sf2_tracks, &tempo, "strings_ens", 22.0, 1.9, st, 0.68);
    }
    push_note(&mut sf2_tracks, &tempo, "cello", 22.0, 1.9, pitch(G, 3), 0.74);
    push_note(&mut sf2_tracks, &tempo, "viola", 22.2, 1.7, pitch(G, 4) + M3, 0.72);
    push_wind(&mut sf2_tracks, &tempo, "clarinet", 22.0, 1.9, pitch(G, 4) + P5, 0.76);
    push_arp(&mut sf2_tracks, &tempo, "harp", 22.0, 1.6, 0.25, &dom9_harmonic(pitch(G, 3)), 0.76);
    push_sitar(&mut sf2_tracks, &tempo, 22.1, 1.7, pitch(G, 3) + OCT + M2, 0.72, -35.0);

    // =========================================================================
    // Phrase 3 (Beats 24..36): Beethovenian French Horn Surge & Smooth 53-EDO Diesis Ascent
    //   C(0) -> Ab(-17 = 36) -> E(-34 = 19) -> C++(+2 diesis) — strictly pure triads + add9
    // =========================================================================
    let mediants: [(f64, f64, i32, f32); 4] = [
        (24.0, 3.0, 0, 0.74),
        (27.0, 3.0, -M3, 0.78),
        (30.0, 3.0, -2 * M3, 0.84),
        (33.0, 3.0, DIESIS, 0.90),
    ];
    for &(_, _) in &[(0, 0)] { let _ = (); }
    for &(start, dur, root, vel) in &mediants {
        push_wind(&mut sf2_tracks, &tempo, "bassoon", start, dur - 0.15, root - OCT, vel * 0.76);
        push_note(&mut sf2_tracks, &tempo, "strings_ens", start, dur - 0.1, root + M3, vel * 0.68);
        push_note(&mut sf2_tracks, &tempo, "strings_ens", start, dur - 0.1, root + P5, vel * 0.66);

        // French Horn heroic singing melody transposed cleanly across the diesis cycle!
        push_wind(&mut sf2_tracks, &tempo, "french_horn", start, 1.35, root, vel * 0.88);
        push_wind(&mut sf2_tracks, &tempo, "french_horn", start + 1.40, 1.50, root + P5, vel * 0.92);

        // Cello & Viola rhythmic surge + Pizzicato punctuation
        let tri = major_triad(root);
        for p in 0..6 {
            let pt = start + p as f64 * 0.5;
            let ac = if p % 2 == 0 { 0.84 } else { 0.68 };
            push_note(&mut sf2_tracks, &tempo, "cello", pt, 0.44, tri[0], vel * ac);
            push_note(&mut sf2_tracks, &tempo, "viola", pt, 0.44, tri[1], vel * ac * 0.90);
        }
        push_note(&mut sf2_tracks, &tempo, "pizzicato", start, 0.5, root - OCT, vel * 0.74);

        // Pure add9 Harp + gentle Sitar & Dotara consonance
        let sweep = add9(root);
        push_arp(&mut sf2_tracks, &tempo, "harp", start, 1.8, 0.28, &sweep, vel * 0.76);
        push_sitar(&mut sf2_tracks, &tempo, start + 0.2, 1.35, root + OCT, vel * 0.74, -40.0);
        push_sitar(&mut sf2_tracks, &tempo, start + 1.7, 1.15, root + OCT + M3, vel * 0.72, -35.0);
        push_dot(&mut dotara_notes, start + 0.5, 0.5, root + P5, vel * 0.74);
        push_dot(&mut dotara_notes, start + 1.5, 0.5, root + OCT, vel * 0.76);
        push_dot(&mut dotara_notes, start + 2.5, 0.5, root + OCT + M3, vel * 0.72);
        push_ekt(&mut ektara_notes, start, 1.0, root - OCT, vel * 0.68, 10.0);
    }

    // =========================================================================
    // Phrase 4 (Beats 36..48): Two Silky 5-Limit Comma Cadences (+2 -> +1 -> 0) & Home Bloom
    // =========================================================================
    for &(t0, k, vel) in &[(36.0, DIESIS, 0.78_f32), (40.0, COMMA, 0.72_f32)] {
        let iv_root = k + P4 - OCT;
        let ii_root = k + P4 - m3;
        let v_root = ii_root + P4 - OCT;
        let next_i = k - COMMA;

        push_wind(&mut sf2_tracks, &tempo, "bassoon", t0, 0.92, iv_root, vel * 0.74);
        push_note(&mut sf2_tracks, &tempo, "cello", t0, 0.92, iv_root + P5, vel * 0.78);
        push_note(&mut sf2_tracks, &tempo, "viola", t0, 0.92, iv_root + OCT, vel * 0.76);
        push_wind(&mut sf2_tracks, &tempo, "clarinet", t0, 0.92, k + OCT + P4, vel * 0.76);

        push_wind(&mut sf2_tracks, &tempo, "bassoon", t0 + 1.0, 0.92, ii_root - OCT, vel * 0.72);
        push_note(&mut sf2_tracks, &tempo, "cello", t0 + 1.0, 0.92, ii_root, vel * 0.76);
        push_note(&mut sf2_tracks, &tempo, "viola", t0 + 1.0, 0.92, ii_root + m3, vel * 0.74);
        push_wind(&mut sf2_tracks, &tempo, "french_horn", t0 + 1.0, 0.92, ii_root, vel * 0.68);

        push_wind(&mut sf2_tracks, &tempo, "bassoon", t0 + 2.0, 0.92, v_root, vel * 0.74);
        push_note(&mut sf2_tracks, &tempo, "cello", t0 + 2.0, 0.92, v_root + P5, vel * 0.76);
        push_note(&mut sf2_tracks, &tempo, "viola", t0 + 2.0, 0.92, v_root + OCT + M3, vel * 0.76);
        push_arp(&mut sf2_tracks, &tempo, "harp", t0 + 2.0, 0.92, 0.16, &dom7_harmonic(v_root + OCT), vel * 0.74);
        push_sitar(&mut sf2_tracks, &tempo, t0 + 2.0, 0.90, v_root + OCT + HARM_7, vel * 0.74, -35.0);

        push_wind(&mut sf2_tracks, &tempo, "bassoon", t0 + 3.0, 0.95, next_i - OCT, vel * 0.72);
        push_note(&mut sf2_tracks, &tempo, "cello", t0 + 3.0, 0.95, next_i, vel * 0.74);
        push_note(&mut sf2_tracks, &tempo, "viola", t0 + 3.0, 0.95, next_i + M3, vel * 0.74);
        push_wind(&mut sf2_tracks, &tempo, "clarinet", t0 + 3.0, 0.95, next_i + OCT, vel * 0.74);
        push_dot(&mut dotara_notes, t0 + 3.0, 0.75, next_i + P5, vel * 0.74);
    }

    // Beats 44..48: Serene East-West Final Resolution on Home C add9
    push_wind(&mut sf2_tracks, &tempo, "bassoon", 44.0, 3.8, pitch(C, 3), 0.66);
    push_wind(&mut sf2_tracks, &tempo, "french_horn", 44.0, 3.6, pitch(G, 3), 0.64);
    for &st in &[pitch(C, 4), pitch(E, 4), pitch(G, 4), pitch(D, 5)] {
        push_note(&mut sf2_tracks, &tempo, "strings_ens", 44.0, 3.8, st, 0.62);
    }
    push_note(&mut sf2_tracks, &tempo, "cello", 44.0, 3.8, pitch(G, 3), 0.66);
    push_note(&mut sf2_tracks, &tempo, "viola", 44.0, 3.8, pitch(E, 4), 0.64);
    push_wind(&mut sf2_tracks, &tempo, "clarinet", 44.0, 3.8, pitch(C, 5), 0.66);
    push_arp(&mut sf2_tracks, &tempo, "harp", 44.0, 3.2, 0.28, &[
        pitch(C, 3), pitch(G, 3), pitch(C, 4), pitch(E, 4), pitch(G, 4), pitch(C, 5), pitch(D, 5), pitch(G, 5), pitch(C, 6),
    ], 0.74);
    push_sitar(&mut sf2_tracks, &tempo, 44.2, 3.4, pitch(E, 5), 0.68, -35.0);
    push_dot(&mut dotara_notes, 45.0, 1.5, pitch(G, 4), 0.66);
    push_ekt(&mut ektara_notes, 44.0, 2.2, pitch(C, 3), 0.66, 8.0);
    push_note(&mut sf2_tracks, &tempo, "pizzicato", 44.0, 1.5, pitch(C, 3), 0.68);

    let total_samples = beat_to_sample(&tempo, 48.0) + (3.8 * SAMPLE_RATE as f64) as usize;

    let mut raw_stems: Vec<(&FusionStemSpec, Vec<(f32, f32)>)> = Vec::with_capacity(FUSION_STEMS.len());
    let mut sum_direct = vec![(0.0_f32, 0.0_f32); total_samples];
    let mut sum_send = vec![(0.0_f32, 0.0_f32); total_samples];
    let mut sum_dry_mono = vec![0.0_f64; total_samples];

    for spec in &FUSION_STEMS {
        let mut dry = match spec.source {
            FusionSource::Sf2(inst) => {
                let notes = sf2_tracks.get(spec.id).map(|v| v.as_slice()).unwrap_or(&[]);
                render_sf2_track(sf, inst, notes, total_samples)
            }
            FusionSource::Ektara => render_ektara_track(&ektara_notes, total_samples),
            FusionSource::Dotara => render_dotara_track(&dotara_notes, total_samples),
        };
        for (i, s) in dry.iter_mut().enumerate() {
            s.0 *= spec.gain;
            s.1 *= spec.gain;
            sum_dry_mono[i] += 0.5 * (s.0 as f64 + s.1 as f64);
        }

        // Spatialize for the static 3D preview_fusion.wav render
        let (direct, send) = spatialize_track(&dry, spec.pos, SAMPLE_RATE);
        for i in 0..total_samples {
            sum_direct[i].0 += direct[i].0;
            sum_direct[i].1 += direct[i].1;
            sum_send[i].0 += send[i].0;
            sum_send[i].1 += send[i].1;
        }
        raw_stems.push((spec, dry));
    }

    let (fusion_mix, stats) = apply_hall_reverb_and_master(&sum_direct, &sum_send, SAMPLE_RATE);
    write_stereo_wav_16bit("output/preview_fusion.wav", SAMPLE_RATE as u32, &fusion_mix)
        .expect("write preview_fusion.wav");
    println!(
        "  - East-West Fusion Mix -> output/preview_fusion.wav ({:.2}s, Peak {:.2} dB, RMS {:.2} dB, Clipped {})",
        total_samples as f64 / SAMPLE_RATE as f64,
        stats.peak_db,
        stats.rms_l_db,
        stats.clipped_samples
    );

    // Export centered, shared-gain dry stems for the live Web Audio 2D HRTF Stage Map!
    let dry_peak = sum_dry_mono.iter().map(|v| v.abs()).fold(0.0_f64, f64::max);
    let stem_scale = if dry_peak > 1e-9 {
        (0.75 / dry_peak).min(2.5)
    } else {
        1.0
    };
    for (spec, dry) in &raw_stems {
        let centered: Vec<(f32, f32)> = dry
            .iter()
            .map(|&(l, r)| {
                let m = (0.5 * (l as f64 + r as f64) * stem_scale) as f32;
                (m, m)
            })
            .collect();
        let path = format!("output/stems_fusion/{}.wav", spec.id);
        write_stereo_wav_16bit(&path, SAMPLE_RATE as u32, &centered).expect("write fusion stem");
    }
}

fn write_manifest() {
    let mut solos: Vec<(String, String, String, i32, String, String, String, &'static str)> = Vec::new();

    solos.push((
        "harp_53edo".into(),
        "Harp — Full 53-Note Octave Sweep".into(),
        "Keys & Plucked".into(),
        46,
        "C4–C5 (all 53 steps)".into(),
        "Plays every single one of the 53 steps in an octave, then blooms into 5-limit & 7-limit harmony".into(),
        "../output/audition/harp_53edo.wav".into(),
        "keep",
    ));
    solos.push((
        "ektara".into(),
        "Ektara (Physical Model)".into(),
        "Indian Classical".into(),
        0,
        "C3–C4".into(),
        "Single-string gourd resonator with elastic meend pitch bend & subtle jawari shimmer".into(),
        "../output/audition/ektara.wav".into(),
        "keep",
    ));
    solos.push((
        "dotara".into(),
        "Dotara (Physical Model)".into(),
        "Indian Classical".into(),
        0,
        "G3–C5".into(),
        "Crisp wooden-plectrum folk lute with taut goatskin body resonance & sympathetic ring".into(),
        "../output/audition/dotara.wav".into(),
        "keep",
    ));

    for &inst in Sf2Instrument::all() {
        let vote = inst.default_vote().unwrap_or("");
        solos.push((
            inst.id().into(),
            inst.name().into(),
            inst.family().into(),
            inst.gm_program(),
            inst.register_label().into(),
            inst.role_desc().into(),
            format!("../output/audition/{}.wav", inst.id()),
            vote,
        ));
    }

    let mut json = String::from("{\n  \"solo_instruments\": [\n");
    for (i, (id, name, family, gm, reg, role, wav, vote)) in solos.iter().enumerate() {
        let comma = if i + 1 < solos.len() { "," } else { "" };
        json.push_str(&format!(
            "    {{\"id\": \"{id}\", \"name\": \"{name}\", \"family\": \"{family}\", \"gm_program\": {gm}, \"register\": \"{reg}\", \"role\": \"{role}\", \"wav\": \"{wav}\", \"default_vote\": \"{vote}\"}}{comma}\n"
        ));
    }

    json.push_str("  ],\n  \"stems\": [\n");
    for (i, spec) in CHAMBER_STEMS.iter().enumerate() {
        let comma = if i + 1 < CHAMBER_STEMS.len() { "," } else { "" };
        json.push_str(&format!(
            "    {{\"id\": \"{}\", \"name\": \"{}\", \"family\": \"{}\", \"wav\": \"../output/stems/{}.wav\"}}{}\n",
            spec.id, spec.name, spec.family, spec.id, comma
        ));
    }

    json.push_str("  ],\n  \"fusion_stems\": [\n");
    for (i, spec) in FUSION_STEMS.iter().enumerate() {
        let comma = if i + 1 < FUSION_STEMS.len() { "," } else { "" };
        json.push_str(&format!(
            "    {{\"id\": \"{}\", \"name\": \"{}\", \"family\": \"{}\", \"x\": {:.2}, \"y\": {:.2}, \"wav\": \"../output/stems_fusion/{}.wav\"}}{}\n",
            spec.id, spec.name, spec.family, spec.pos.x, spec.pos.y, spec.id, comma
        ));
    }
    json.push_str("  ]\n}\n");

    fs::write("output/audition/manifest.json", json).expect("write manifest.json");
}
