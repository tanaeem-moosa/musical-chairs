//! 53-EDO tuning math, interval constants, and pure chord voicings.
#![allow(dead_code)]

/// Number of equal divisions of the octave.
pub const OCT: i32 = 53;

/// Purest 5-limit fifth (~701.89 cents, 0.07 cents from 3:2).
pub const P5: i32 = 31;
/// Purest 5-limit fourth (~498.11 cents, 0.07 cents from 4:3).
pub const P4: i32 = 22;
/// Purest 5-limit major third (~384.91 cents, 1.41 cents from 5:4).
pub const M3: i32 = 17;
/// Purest 5-limit minor third (~316.98 cents, 1.34 cents from 6:5).
#[allow(non_upper_case_globals)]
pub const m3: i32 = 14;
/// Purest 5-limit major sixth (~883.02 cents, 1.34 cents from 5:3).
pub const M6: i32 = 39;
/// Purest 5-limit minor sixth (~815.09 cents, 1.41 cents from 8:5).
#[allow(non_upper_case_globals)]
pub const m6: i32 = 36;
/// Major whole tone (9:8, ~203.77 cents).
pub const M2: i32 = 9;
/// Minor whole tone (10:9, ~181.13 cents).
#[allow(non_upper_case_globals)]
pub const m2_MINOR_TONE: i32 = 8;
/// Diatonic semitone (16:15, ~113.21 cents).
pub const DIATONIC_SEMI: i32 = 5;
/// Chromatic semitone (25:24 / 135:128 region, ~90.57 cents).
pub const CHROMATIC_SEMI: i32 = 4;
/// Harmonic seventh (7:4, ~973.58 cents, 4.76 cents from 7:4).
pub const HARM_7: i32 = 43;
/// Pythagorean minor seventh (16:9, ~996.23 cents).
#[allow(non_upper_case_globals)]
pub const PYTH_m7: i32 = 44;
/// Just minor seventh (9:5, ~1018.87 cents).
#[allow(non_upper_case_globals)]
pub const JUST_m7: i32 = 45;
/// Just major seventh (15:8, ~1086.79 cents).
pub const M7: i32 = 48;
/// Syntonic comma (~22.64 cents).
pub const COMMA: i32 = 1;
/// Enharmonic diesis (~45.28 cents, 53 - 3 * 17 = 2).
pub const DIESIS: i32 = 2;

/// Named 53-EDO pitch-class steps relative to C = 0.
pub const C: i32 = 0;
pub const D_MINUS: i32 = 8;
pub const D: i32 = 9;
pub const EB: i32 = 14;
pub const E: i32 = 17;
pub const F: i32 = 22;
pub const G: i32 = 31;
pub const AB: i32 = 36;
pub const A: i32 = 39;
pub const BB_HARM: i32 = 43;
pub const B: i32 = 48;

/// Returns the 53-EDO step for a pitch class in a given octave (C4 = step 0).
#[inline]
pub const fn pitch(pc: i32, octave: i32) -> i32 {
    pc + (octave - 4) * OCT
}

/// Step offset of A4 (440 Hz) above C4 (step 0).
pub const A4_STEP: i32 = 39;
/// Reference concert pitch for A4 in Hz.
pub const A4_HZ: f64 = 440.0;

/// Converts a 53-EDO step (C4 = 0, A4 = 39) to frequency in Hz.
#[inline]
pub fn step_to_freq(step: i32) -> f64 {
    A4_HZ * 2.0_f64.powf((step - A4_STEP) as f64 / OCT as f64)
}

/// Converts a 53-EDO step plus fine microtonal offset in cents to Hz.
#[inline]
pub fn step_cents_to_freq(step: i32, cents: f64) -> f64 {
    A4_HZ * 2.0_f64.powf(((step - A4_STEP) as f64 / OCT as f64) + cents / 1200.0)
}

/// Projects a 53-EDO step (+ microtonal cents) onto its nearest 12-TET MIDI key
/// anchored at C4 = step 0 (MIDI 60), so C4 (0), C4+comma (+1), and C4+diesis (+2)
/// quantize to MIDI 60 (C4 = 261.63 Hz) while A4 (39) quantizes to MIDI 69 (440 Hz).
#[inline]
pub fn edo53_to_12tet_midi(step: i32, cents: f64) -> i32 {
    let midi_float = 60.0 + (step as f64 / OCT as f64) * 12.0 + cents / 100.0;
    midi_float.round().clamp(0.0, 127.0) as i32
}

/// Converts a 12-TET MIDI note number to exact 12-EDO frequency in Hz (A4 = MIDI 69 = 440 Hz).
#[inline]
pub fn midi_to_12tet_freq(midi: i32) -> f64 {
    A4_HZ * 2.0_f64.powf((midi - 69) as f64 / 12.0)
}

/// Quantizes a 53-EDO step (+ microtonal cents) to its nearest 12-TET frequency in Hz.
#[inline]
pub fn step_cents_to_12tet_freq(step: i32, cents: f64) -> f64 {
    midi_to_12tet_freq(edo53_to_12tet_midi(step, cents))
}

/// 5-limit major triad [0, 17, 31] relative to `root`.
pub fn major_triad(root: i32) -> Vec<i32> {
    vec![root, root + M3, root + P5]
}

/// 5-limit minor triad [0, 14, 31] relative to `root`.
pub fn minor_triad(root: i32) -> Vec<i32> {
    vec![root, root + m3, root + P5]
}

/// Debussy 7-limit harmonic dominant seventh (4:5:6:7) [0, 17, 31, 43].
pub fn dom7_harmonic(root: i32) -> Vec<i32> {
    vec![root, root + M3, root + P5, root + HARM_7]
}

/// Debussy 7-limit harmonic dominant ninth (4:5:6:7:9) [0, 17, 31, 43, 62].
pub fn dom9_harmonic(root: i32) -> Vec<i32> {
    vec![root, root + M3, root + P5, root + HARM_7, root + OCT + M2]
}

/// Pure major seventh [0, 17, 31, 48].
pub fn maj7(root: i32) -> Vec<i32> {
    vec![root, root + M3, root + P5, root + M7]
}

/// Pure major ninth [0, 17, 31, 48, 62].
pub fn maj9(root: i32) -> Vec<i32> {
    vec![root, root + M3, root + P5, root + M7, root + OCT + M2]
}

/// Pure minor ninth [0, 14, 31, 45, 62].
pub fn min9(root: i32) -> Vec<i32> {
    vec![root, root + m3, root + P5, root + JUST_m7, root + OCT + M2]
}

/// Pure major add-9 [0, 17, 31, 62].
pub fn add9(root: i32) -> Vec<i32> {
    vec![root, root + M3, root + P5, root + OCT + M2]
}

/// Returns an approximate pitch name with comma offset and octave (C4 = step 0).
pub fn note_name_approx(step: i32) -> String {
    let octave = 4 + step.div_euclid(OCT);
    let pc = step.rem_euclid(OCT);

    // Closest 12-EDO anchor steps in 53-EDO (C=0, C#=4, D=9, Eb=14, E=17, F=22,
    // F#=26, G=31, Ab=36, A=39, Bb=44, B=48)
    const ANCHORS: [(i32, &str); 12] = [
        (0, "C"),
        (4, "C#"),
        (9, "D"),
        (14, "Eb"),
        (17, "E"),
        (22, "F"),
        (26, "F#"),
        (31, "G"),
        (36, "Ab"),
        (39, "A"),
        (44, "Bb"),
        (48, "B"),
    ];

    let mut best_name = "C";
    let mut best_diff: i32 = 100;
    for &(anchor, name) in &ANCHORS {
        let mut diff = pc - anchor;
        if diff > OCT / 2 {
            diff -= OCT;
        } else if diff < -(OCT / 2) {
            diff += OCT;
        }
        if diff.abs() < best_diff.abs() {
            best_diff = diff;
            best_name = name;
        }
    }

    if best_diff == 0 {
        format!("{}{}", best_name, octave)
    } else if best_diff > 0 {
        format!("{}{}+{}c", best_name, octave, best_diff)
    } else {
        format!("{}{}{}c", best_name, octave, best_diff)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cents_between(f1: f64, f2: f64) -> f64 {
        1200.0 * (f2 / f1).log2()
    }

    #[test]
    fn test_reference_and_just_intervals() {
        assert!((step_to_freq(39) - 440.0).abs() < 1e-9);

        let f_root = step_to_freq(0);
        let p5_err = (cents_between(f_root, step_to_freq(P5)) - 1200.0 * 1.5_f64.log2()).abs();
        let m3_err = (cents_between(f_root, step_to_freq(M3)) - 1200.0 * 1.25_f64.log2()).abs();
        let h7_err = (cents_between(f_root, step_to_freq(HARM_7)) - 1200.0 * 1.75_f64.log2()).abs();

        assert!(p5_err < 0.1, "P5 error too large: {p5_err}");
        assert!(m3_err < 1.5, "M3 error too large: {m3_err}");
        assert!(h7_err < 5.0, "HARM_7 error too large: {h7_err}");
    }

    #[test]
    fn test_diesis_and_comma_pump_geometry() {
        // Three downward pure major thirds: 0 -> -17 (36 mod 53) -> -34 (19 mod 53) -> -51 (+2 mod 53)
        let s0 = 0;
        let s1 = (s0 - M3).rem_euclid(OCT);
        let s2 = (s1 - M3).rem_euclid(OCT);
        let s3 = (s2 - M3).rem_euclid(OCT);
        assert_eq!(s1, 36);
        assert_eq!(s2, 19);
        assert_eq!(s3, DIESIS);

        // Two downward 5-limit comma pumps: I -> IV (+22) -> ii (-14) -> V (+22) -> I (-31)
        // Net shift per pump: +22 - 14 + 22 - 31 = -1 (one syntonic comma down)
        let pump_shift = P4 - m3 + P4 - P5;
        assert_eq!(pump_shift, -COMMA);
        assert_eq!(s3 + 2 * pump_shift, 0);

        assert_eq!(pitch(C, 4), 0);
        assert_eq!(pitch(A, 4), 39);
        assert_eq!(pitch(C, 3), -53);
        assert_eq!(pitch(F, 2), -84);
        assert_eq!(pitch(G, 2), -75);
        assert_eq!(pitch(A, 2), -67);
    }
}
