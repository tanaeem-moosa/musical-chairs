//! ~65-second 53-EDO proof-of-concept miniature overture:
//! Mozartian clarity + Debussy 7-limit shimmer + Beethovenian structural drive.

use crate::score::{Articulation, Instrument, Score, TempoMap, TempoSegment};
use crate::tuning::{
    add9, dom7_harmonic, dom9_harmonic, maj7, maj9, major_triad, min9, pitch, COMMA, DIESIS, F, G,
    HARM_7, M2, M3, M6, OCT, P4, P5, m3,
};

/// Unifying Beethovenian 5-note seed motif relative to tonic: [0, +31, +22, +17, +9].
#[allow(dead_code)]
pub const SEED_MOTIF: [i32; 5] = [0, P5, P4, M3, M2];

/// Builds the 80-beat preview score (~66–70 seconds including concert hall decay).
pub fn build_preview_score() -> Score {
    let tempo = TempoMap::from_segments(vec![
        TempoSegment { beat: 0.0, bpm: 72.0 },
        TempoSegment { beat: 32.0, bpm: 72.0 },
        TempoSegment { beat: 42.0, bpm: 78.0 },
        TempoSegment { beat: 56.0, bpm: 74.0 },
        TempoSegment { beat: 60.0, bpm: 72.0 },
        TempoSegment { beat: 72.0, bpm: 68.0 },
        TempoSegment { beat: 80.0, bpm: 56.0 },
    ]);

    let mut s = Score::new(tempo);

    // =========================================================================
    // SECTION I (Beats 0..32): "Luminous Opening" — Tonic C (step 0)
    // Pure 5-limit Mozartian clarity meets Debussy harp/celesta 7-limit bloom.
    // =========================================================================
    build_section_one(&mut s);

    // =========================================================================
    // SECTION II (Beats 32..60): "Beethovenian Surge & Smooth 53-EDO Journey"
    // Chromatic-mediant cycle C(0) -> Ab(36) -> E(19) -> C++(+2 diesis)
    // followed by two silky 5-limit comma cadences (+2 -> +1 -> 0).
    // =========================================================================
    build_section_two(&mut s);

    // =========================================================================
    // SECTION III (Beats 60..80): "Radiant Resolution" — Home at Tonic C (0)
    // =========================================================================
    build_section_three(&mut s);

    s
}

fn add_warm_string_chord(
    s: &mut Score,
    start: f64,
    dur: f64,
    bass_step: i32,
    cello_step: i32,
    viola_step: i32,
    v2_step: i32,
    v1_step: Option<i32>,
    vel: f32,
    art: Articulation,
) {
    s.add_note(Instrument::Contrabass, start, dur, bass_step, vel * 0.72, Articulation::Sustained);
    s.add_note(Instrument::Cello, start, dur, cello_step, vel * 0.85, art);
    s.add_note(Instrument::Viola, start, dur, viola_step, vel * 0.82, art);
    s.add_note(Instrument::Violin2, start, dur, v2_step, vel * 0.80, art);
    if let Some(v1) = v1_step {
        s.add_note(Instrument::Violin1, start, dur, v1, vel * 0.88, art);
    }
}

fn add_harp_wave(
    s: &mut Score,
    start: f64,
    span_beats: f64,
    steps: &[i32],
    vel: f32,
) {
    let spacing = span_beats / (steps.len().max(1) as f64);
    s.add_arpeggio(
        Instrument::Harp,
        start,
        2.8,
        spacing,
        steps,
        vel,
        Articulation::Plucked,
    );
}

fn build_section_one(s: &mut Score) {
    // Beats 0..16: I(0) -> vi(-14 = A3) -> IV(22 = F4 / -31) -> V9_harm(31 = G4 / -22)
    // Bar 1-2 (Beats 0..4): C major (0)
    add_warm_string_chord(s, 0.0, 4.0, -OCT, -OCT + P5, -OCT + OCT, M3, None, 0.42, Articulation::Sustained);
    add_harp_wave(s, 0.0, 3.5, &[-OCT, -OCT + P5, 0, M3, P5, OCT, OCT + M3], 0.46);

    // Bar 3-4 (Beats 4..8): A minor 9 (-14)
    add_warm_string_chord(s, 4.0, 4.0, -OCT - m3, -m3, -m3 + P5, 0, None, 0.45, Articulation::Sustained);
    add_harp_wave(s, 4.0, 3.5, &[-OCT - m3, -P4, -m3, 0, M2, M3, P5], 0.46);

    // Flute introduces the Beethovenian seed motif over A minor -> F -> G9
    let flute_phrase1 = [
        (4.0, 1.5, OCT, 0.56),           // C5
        (5.5, 0.5, OCT + P5, 0.58),      // G5
        (6.0, 1.0, OCT + P4, 0.60),      // F5
        (7.0, 0.5, OCT + M3, 0.56),      // E5
        (7.5, 0.5, OCT + M2, 0.52),      // D5
    ];
    for &(t, d, st, v) in &flute_phrase1 {
        s.add_note(Instrument::Flute, t, d, st, v, Articulation::Legato);
    }

    // Beats 8..12: IV (F maj7, root = -31 = F3)
    add_warm_string_chord(s, 8.0, 4.0, pitch(F, 2), -OCT + P4, 0, M3, None, 0.50, Articulation::Sustained);
    add_harp_wave(s, 8.0, 3.5, &[-OCT - P4, -M2, 0, M3, P4, OCT, OCT + M3], 0.50);
    s.add_note(Instrument::Flute, 8.0, 2.5, OCT + M3, 0.58, Articulation::Expressive);
    s.add_note(Instrument::Flute, 10.5, 1.5, OCT + P4, 0.54, Articulation::Legato);

    // Celesta shimmer on pure F maj9
    let f_maj9 = maj9(-31 + OCT);
    s.add_arpeggio(Instrument::Celesta, 8.5, 2.0, 0.25, &f_maj9[1..], 0.40, Articulation::Bell);

    // Beats 12..16: V9_harmonic (G dom9 4:5:6:7:9, root = 31 - OCT = -22 = G3)
    add_warm_string_chord(s, 12.0, 4.0, pitch(G, 2), -P4, -P4 + M3, -P4 + HARM_7, None, 0.52, Articulation::Sustained);
    let g_dom9 = dom9_harmonic(-22);
    add_harp_wave(s, 12.0, 3.5, &[g_dom9[0], g_dom9[2], g_dom9[1] + OCT, g_dom9[3] + OCT, g_dom9[4]], 0.52);
    // Clarinet echoes the seed motif in canon at the fifth below
    s.add_note(Instrument::Clarinet, 12.0, 1.5, M2, 0.52, Articulation::Legato);
    s.add_note(Instrument::Clarinet, 13.5, 0.5, M6, 0.54, Articulation::Legato);
    s.add_note(Instrument::Clarinet, 14.0, 1.0, P5, 0.55, Articulation::Legato);
    s.add_note(Instrument::Clarinet, 15.0, 1.0, P4, 0.50, Articulation::Legato);

    // Beats 16..32: Answering phrase with Violin I taking over the melody
    // Beats 16..20: I(0) add9
    add_warm_string_chord(s, 16.0, 4.0, -OCT, -P4, 0, M3, Some(OCT), 0.54, Articulation::Expressive);
    add_harp_wave(s, 16.0, 3.5, &add9(0), 0.48);
    // Violin I sings seed motif with Mozartian turn
    s.add_note(Instrument::Violin1, 16.0, 1.5, OCT, 0.60, Articulation::Expressive);
    s.add_note(Instrument::Violin1, 17.5, 0.5, OCT + P5, 0.62, Articulation::Legato);
    s.add_note(Instrument::Violin1, 18.0, 1.0, OCT + P4, 0.64, Articulation::Legato);
    s.add_note(Instrument::Violin1, 19.0, 0.5, OCT + M3, 0.60, Articulation::Legato);
    s.add_note(Instrument::Violin1, 19.5, 0.5, OCT + M2, 0.56, Articulation::Legato);

    // Beats 20..24: iii7 (E min9, root = -OCT + M3) -> smooth Debussy color
    add_warm_string_chord(s, 20.0, 4.0, -OCT + M3, -P5 + M2, M3, M6, None, 0.52, Articulation::Sustained);
    let e_min9 = min9(-OCT + M3);
    add_harp_wave(s, 20.0, 3.5, &[e_min9[0], e_min9[2], e_min9[1] + OCT, e_min9[3] + OCT, e_min9[4]], 0.50);
    s.add_note(Instrument::Violin1, 20.0, 2.0, OCT + M6, 0.60, Articulation::Expressive);
    s.add_note(Instrument::Flute, 21.0, 2.5, OCT + P5, 0.54, Articulation::Legato);

    // Beats 24..28: IV (F maj7) -> ii9 (D min9)
    add_warm_string_chord(s, 24.0, 2.0, pitch(F, 2), -P4 + M2, 0, P4, Some(OCT + P4), 0.56, Articulation::Legato);
    add_warm_string_chord(s, 26.0, 2.0, -OCT + M2, -P4, M2, P4, Some(OCT + P5), 0.58, Articulation::Legato);
    s.add_arpeggio(Instrument::Celesta, 24.0, 2.0, 0.3, &maj7(P4), 0.44, Articulation::Bell);
    s.add_arpeggio(Instrument::Harp, 26.0, 2.5, 0.3, &min9(M2), 0.50, Articulation::Plucked);

    // Beats 28..32: V9_harmonic (G7(9) 7-limit) resolving into Section II
    add_warm_string_chord(s, 28.0, 4.0, pitch(G, 2), -P4, -P4 + M3, -P4 + HARM_7, None, 0.60, Articulation::Expressive);
    s.add_note(Instrument::Flute, 28.0, 2.0, OCT + M3 + M2, 0.58, Articulation::Expressive);
    s.add_note(Instrument::Clarinet, 28.0, 2.0, -P4 + HARM_7, 0.54, Articulation::Expressive);
    s.add_note(Instrument::Flute, 30.0, 2.0, OCT + P5, 0.62, Articulation::Legato);
    s.add_note(Instrument::Clarinet, 30.0, 2.0, P5, 0.58, Articulation::Legato);
    add_harp_wave(s, 28.0, 3.2, &dom9_harmonic(-22), 0.54);
}

fn build_section_two(s: &mut Score) {
    // Smooth 53-EDO chromatic-mediant cycle:
    //   Beats 32..37: C major (root = 0)
    //   Beats 37..42: Ab major (root = -M3 = -17, i.e. 36 mod 53; common tone = C!)
    //   Beats 42..47: E major (root = -2*M3 = -34, i.e. 19 mod 53; common tone = Ab/G#!)
    //   Beats 47..52: C++ major (root = -3*M3 + OCT = +2 DIESIS! common tone = E!)
    // Every transition shares an exact 53-EDO common tone while drifting +45.28 cents!

    let mediants: [(f64, f64, i32, f32); 4] = [
        (32.0, 5.0, 0, 0.62),          // C major (0)
        (37.0, 5.0, -M3, 0.68),        // Ab major (-17 -> 36 mod 53)
        (42.0, 5.0, -2 * M3, 0.76),    // E major (-34 -> 19 mod 53)
        (47.0, 5.0, DIESIS, 0.84),     // C++ major (+2 diesis, climactic glow!)
    ];

    for (idx, &(start, dur, root, vel)) in mediants.iter().enumerate() {
        // Subtle cathedral Organ Pedal & Contrabass anchor
        let pedal = root - OCT;
        s.add_note(Instrument::OrganPedal, start, dur, pedal, vel * 0.52, Articulation::Sustained);
        s.add_note(Instrument::Contrabass, start, dur, pedal, vel * 0.72, Articulation::Sustained);

        // Beethovenian 8th-note rhythmic surge in Cello & Viola
        let pulse_chord = major_triad(root);
        let num_pulses = (dur * 2.0) as usize;
        for p in 0..num_pulses {
            let pt = start + p as f64 * 0.5;
            let accent = if p % 2 == 0 { 1.0 } else { 0.82 };
            s.add_note(
                Instrument::Cello,
                pt,
                0.48,
                pulse_chord[0],
                vel * 0.74 * accent,
                Articulation::Expressive,
            );
            s.add_note(
                Instrument::Viola,
                pt,
                0.48,
                pulse_chord[1],
                vel * 0.70 * accent,
                Articulation::Expressive,
            );
        }

        // Soaring Violin I & Flute transformation of the seed motif transposed to `root`
        let mel_root = root + OCT;
        let motif_notes = [
            (0.0, 1.5, mel_root),
            (1.5, 0.5, mel_root + P5),
            (2.0, 1.0, mel_root + P4),
            (3.0, 1.0, mel_root + M3),
            (4.0, 1.0, mel_root + M2),
        ];
        for &(dt, md, mst) in &motif_notes {
            s.add_note(Instrument::Violin1, start + dt, md, mst, vel * 0.88, Articulation::Expressive);
            if idx >= 1 {
                s.add_note(Instrument::Flute, start + dt, md, mst, vel * 0.76, Articulation::Expressive);
            }
        }

        // Clarinet & Violin II warm counterline on harmonic 7th / add9 color
        s.add_note(Instrument::Violin2, start, dur, root + P5, vel * 0.68, Articulation::Sustained);
        s.add_note(Instrument::Clarinet, start + 0.5, dur - 0.5, root + M3, vel * 0.62, Articulation::Legato);

        // Debussy Harp & Celesta sweeps using 7-limit dom9 on the peak mediants
        let sweep = if idx >= 2 {
            dom9_harmonic(root)
        } else {
            add9(root)
        };
        add_harp_wave(s, start, 2.0, &sweep, vel * 0.72);
        s.add_arpeggio(
            Instrument::Celesta,
            start + 2.0,
            1.8,
            0.25,
            &sweep,
            vel * 0.58,
            Articulation::Bell,
        );
    }

    // -------------------------------------------------------------------------
    // Two Silky 5-Limit Comma Cadences returning cleanly from +2 -> +1 -> 0:
    // Pump formula per cadence: I(k) -> IV(k+22) -> ii(k+8) -> V(k+30) -> I(k-1)
    // Beats 52..56: Pump 1 (+2 -> +1)
    // Beats 56..60: Pump 2 (+1 -> 0)
    // -------------------------------------------------------------------------
    let pumps = [(52.0, DIESIS, 0.76_f32), (56.0, COMMA, 0.68_f32)];
    for &(t0, k, vel) in &pumps {
        // Beat t0+0..1: IV(k + P4 - OCT)
        let iv_root = k + P4 - OCT;
        add_warm_string_chord(s, t0, 1.0, iv_root, iv_root + P5, iv_root + OCT, iv_root + OCT + M3, Some(iv_root + OCT + P5), vel, Articulation::Legato);
        s.add_note(Instrument::Flute, t0, 1.0, k + OCT + P4, vel * 0.75, Articulation::Legato);

        // Beat t0+1..2: ii(k + M2 - m3 + P4... wait: k + P4 - m3 = k + 8 = D minor_tone!)
        let ii_root = k + P4 - m3; // k + 8
        add_warm_string_chord(s, t0 + 1.0, 1.0, ii_root - OCT, ii_root, ii_root + m3, ii_root + P5, Some(ii_root + OCT), vel * 0.96, Articulation::Legato);
        s.add_note(Instrument::Clarinet, t0 + 1.0, 1.0, ii_root + m3, vel * 0.72, Articulation::Legato);

        // Beat t0+2..3: V(k + P4 - m3 + P4 - OCT = k + 30) with Debussy harmonic 7th
        let v_root = ii_root + P4 - OCT; // k + 30 (- 53)
        add_warm_string_chord(s, t0 + 2.0, 1.0, v_root, v_root + P5, v_root + OCT, v_root + OCT + M3, Some(v_root + OCT + HARM_7), vel * 0.94, Articulation::Legato);
        s.add_arpeggio(Instrument::Harp, t0 + 2.0, 1.8, 0.2, &dom7_harmonic(v_root + OCT), vel * 0.62, Articulation::Plucked);

        // Beat t0+3..4: I(k - 1) arrived!
        let next_i = k - COMMA;
        add_warm_string_chord(s, t0 + 3.0, 1.0, next_i - OCT, next_i, next_i + M3, next_i + P5, Some(next_i + OCT), vel * 0.90, Articulation::Legato);
        s.add_arpeggio(Instrument::Celesta, t0 + 3.0, 1.5, 0.2, &major_triad(next_i + OCT), vel * 0.50, Articulation::Bell);
    }
}

fn build_section_three(s: &mut Score) {
    // Beats 60..80: Radiant Resolution on original Tonic C (0)
    // Beats 60..64: Warm I(0) bloom
    s.add_note(Instrument::OrganPedal, 60.0, 18.0, -OCT, 0.42, Articulation::Sustained);
    add_warm_string_chord(s, 60.0, 4.0, -OCT, -OCT + P5, 0, M3, Some(OCT + M3), 0.64, Articulation::Expressive);
    add_harp_wave(s, 60.0, 3.2, &[-OCT, -OCT + P5, 0, M3, P5, OCT, OCT + M2, OCT + M3], 0.58);

    // Flute & Violin I soar in pure major sixths (M6 = 39)
    let duet = [
        (60.0, 1.5, OCT + M3, OCT + M3 - M6),
        (61.5, 0.5, OCT + P5, OCT + P5 - M6),
        (62.0, 1.0, OCT + P4, OCT + P4 - M6),
        (63.0, 1.0, OCT + M3, OCT + M3 - M6),
    ];
    for &(t, d, hi, lo) in &duet {
        s.add_note(Instrument::Flute, t, d, hi, 0.66, Articulation::Expressive);
        s.add_note(Instrument::Violin1, t, d, hi, 0.68, Articulation::Expressive);
        s.add_note(Instrument::Clarinet, t, d, lo, 0.56, Articulation::Legato);
    }

    // Beats 64..68: IV (F maj9)
    add_warm_string_chord(s, 64.0, 4.0, pitch(F, 2), -P4, 0, M3, Some(OCT + P4), 0.60, Articulation::Expressive);
    add_harp_wave(s, 64.0, 3.2, &maj9(-31 + OCT), 0.54);
    s.add_note(Instrument::Flute, 64.0, 2.5, OCT + P4, 0.62, Articulation::Expressive);
    s.add_note(Instrument::Flute, 66.5, 1.5, OCT + M3, 0.56, Articulation::Legato);

    // Beats 68..72: V9_harmonic (G 4:5:6:7:9) plagal-dominant shimmer
    add_warm_string_chord(s, 68.0, 4.0, pitch(G, 2), -P4, -P4 + M3, -P4 + HARM_7, Some(OCT + M2), 0.56, Articulation::Expressive);
    add_harp_wave(s, 68.0, 3.2, &dom9_harmonic(-22), 0.52);
    s.add_arpeggio(Instrument::Celesta, 69.0, 2.2, 0.32, &dom9_harmonic(P5 - OCT + OCT), 0.46, Articulation::Bell);
    s.add_note(Instrument::Clarinet, 68.0, 3.5, M2 + M3, 0.52, Articulation::Legato);

    // Beats 72..80: Final serene C add9 -> pure C major chord fading into hall reverb
    add_warm_string_chord(s, 72.0, 6.5, -OCT, -OCT + P5, 0, M3, Some(OCT), 0.48, Articulation::Sustained);
    s.add_note(Instrument::Flute, 72.0, 5.5, OCT + P5, 0.46, Articulation::Sustained);
    s.add_note(Instrument::Clarinet, 72.0, 5.5, M3, 0.42, Articulation::Sustained);
    add_harp_wave(s, 72.0, 4.5, &[-OCT, -OCT + P5, 0, M3, P5, OCT, OCT + M2, OCT + P5, 2 * OCT], 0.46);
    s.add_arpeggio(Instrument::Celesta, 74.0, 3.0, 0.45, &[OCT, OCT + M3, OCT + P5, 2 * OCT], 0.36, Articulation::Bell);
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::synth::render_score;

    #[test]
    fn test_preview_score_renders_clean_audio() {
        let score = build_preview_score();
        let (audio, stats) = render_score(&score, 4.5);

        assert!(audio.len() > 48_000 * 60, "Preview should exceed 60 seconds");
        assert_eq!(stats.nan_count, 0, "Audio contains NaNs");
        assert_eq!(stats.clipped_samples, 0, "Audio contains clipped samples");
        assert!(stats.peak_db <= 0.0, "Peak above 0 dBFS: {}", stats.peak_db);
        assert!(stats.rms_l_db > -45.0 && stats.rms_l_db < -6.0, "Unexpected RMS L: {}", stats.rms_l_db);
        assert!(stats.rms_r_db > -45.0 && stats.rms_r_db < -6.0, "Unexpected RMS R: {}", stats.rms_r_db);
    }
}
