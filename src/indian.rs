//! Physically modeled classical Indian plucked instruments (Ektara & Dotara) in exact 53-EDO.

use std::f64::consts::PI;

use crate::synth::{raised_cosine, BiquadLP, XorShift64, SAMPLE_RATE};
use crate::tuning::{step_cents_to_12tet_freq, step_to_freq};

#[derive(Clone, Copy)]
struct BiquadBP {
    b0: f64,
    b2: f64,
    a1: f64,
    a2: f64,
    z1: f64,
    z2: f64,
}

impl BiquadBP {
    fn new(center_hz: f64, q: f64) -> Self {
        let fc = center_hz.clamp(40.0, 0.42 * SAMPLE_RATE as f64);
        let w0 = 2.0 * PI * fc / SAMPLE_RATE as f64;
        let cos_w0 = w0.cos();
        let alpha = w0.sin() / (2.0 * q);
        let a0 = 1.0 + alpha;
        Self {
            b0: alpha / a0,
            b2: -alpha / a0,
            a1: (-2.0 * cos_w0) / a0,
            a2: (1.0 - alpha) / a0,
            z1: 0.0,
            z2: 0.0,
        }
    }

    #[inline]
    fn process(&mut self, x: f64) -> f64 {
        let y = self.b0 * x + self.z1;
        self.z1 = -self.a1 * y + self.z2;
        self.z2 = self.b2 * x - self.a2 * y;
        y
    }
}

#[derive(Clone, Copy, Debug)]
pub struct IndianNote {
    pub start_sample: usize,
    pub end_sample: usize,
    pub step: i32,
    pub velocity: f32,
    pub meend_cents: f32,
}

/// Renders an Ektara (single-string gourd/skin resonator with elastic pitch-relaxation & subtle jawari).
pub fn render_ektara(step: i32, dur_s: f64, vel: f64, meend_cents: f64, seed: u64) -> Vec<f32> {
    render_ektara_hz(step_to_freq(step), dur_s, vel, meend_cents, seed)
}

/// Renders an Ektara at an explicit fundamental frequency `base_freq` in Hz.
pub fn render_ektara_hz(
    base_freq: f64,
    dur_s: f64,
    vel: f64,
    meend_cents: f64,
    seed: u64,
) -> Vec<f32> {
    let sr = SAMPLE_RATE as f64;
    let ring_s = (1.85 - 0.0005 * base_freq).clamp(1.2, 2.0);
    let total_s = dur_s.max(0.25).min(ring_s) + ring_s * 0.55;
    let n = (total_s * sr).ceil() as usize;

    // Warm string damping
    let a = (0.38 - 0.00012 * base_freq).clamp(0.24, 0.40);
    let buf_len: usize = 4096;
    let mask = buf_len - 1;
    let mut buf = vec![0.0_f64; buf_len];

    let init_freq = base_freq * 2.0_f64.powf(meend_cents / 1200.0);
    let init_period = (sr / init_freq).clamp(6.0, (buf_len - 12) as f64);
    let init_len = init_period.round() as usize;

    let mut rng = XorShift64::new(seed);
    let mut exc_lp = BiquadLP::new((base_freq * (4.5 + 2.5 * vel)).clamp(600.0, 5600.0), 0.707);
    let mut write_idx = init_len + 4;
    let mut tmp = vec![0.0_f64; init_len];
    let mut mean = 0.0;
    for j in 0..init_len {
        let u = j as f64 / init_len as f64;
        let shape = (PI * u).sin() * 0.55 + (3.0 * PI * u).sin() * 0.14;
        let noise = exc_lp.process(rng.next_bipolar()) * 0.50;
        let v = shape + noise;
        tmp[j] = v;
        mean += v;
    }
    mean /= init_len as f64;
    for j in 0..init_len {
        let pos = (write_idx + buf_len - init_len + j) & mask;
        buf[pos] = tmp[j] - mean;
    }

    // Gourd & skin membrane formants
    let mut body1 = BiquadBP::new(240.0, 2.2);
    let mut body2 = BiquadBP::new(620.0, 2.5);
    let mut prev_delayed = buf[(write_idx + buf_len - init_len) & mask];

    // Gentle DC blocker for subtle jawari harmonic bloom
    let dc_alpha = (-2.0 * PI * 28.0 / sr).exp();
    let mut dc_in = 0.0;
    let mut dc_out = 0.0;

    let mut out = vec![0.0_f32; n];
    let fade_start = (n as f64 * 0.70) as usize;
    let fade_len = (n - fade_start).max(1);
    let atk_samples = (0.003 * sr).max(1.0);

    for i in 0..n {
        let t_sec = i as f64 / sr;
        let cents_inst = meend_cents * (-t_sec / 0.11).exp();
        let f_inst = base_freq * 2.0_f64.powf(cents_inst / 1200.0);
        let w = 2.0 * PI * f_inst / sr;
        let h_re = (1.0 - a) + a * w.cos();
        let h_im = -a * w.sin();
        let filter_phase_delay = -h_im.atan2(h_re) / w;
        let filter_mag = (h_re * h_re + h_im * h_im).sqrt();
        let delay = (sr / f_inst - filter_phase_delay).max(4.0);

        let raw_damp = 10.0_f64.powf(-3.0 / (ring_s * f_inst));
        let damp = (raw_damp / filter_mag).clamp(0.985, 0.9997);

        let read_pos = write_idx as f64 - delay;
        let i0_f = read_pos.floor();
        let t = read_pos - i0_f;
        let i0 = (i0_f as isize).rem_euclid(buf_len as isize) as usize;

        let ym1 = buf[(i0 + buf_len - 1) & mask];
        let y0 = buf[i0];
        let y1 = buf[(i0 + 1) & mask];
        let y2 = buf[(i0 + 2) & mask];

        let c_m1 = -t * (t - 1.0) * (t - 2.0) / 6.0;
        let c_0 = (t + 1.0) * (t - 1.0) * (t - 2.0) / 2.0;
        let c_1 = -(t + 1.0) * t * (t - 2.0) / 2.0;
        let c_2 = (t + 1.0) * t * (t - 1.0) / 6.0;
        let delayed = c_m1 * ym1 + c_0 * y0 + c_1 * y1 + c_2 * y2;

        let lp = (1.0 - a) * delayed + a * prev_delayed;
        prev_delayed = delayed;
        let loop_val = lp * damp;

        buf[write_idx] = loop_val;
        write_idx = (write_idx + 1) & mask;

        // Subtle jawari curved-bridge bloom + gourd/skin resonance
        let jawari_raw = loop_val + 0.065 * loop_val * loop_val;
        let jawari = dc_alpha * (dc_out + jawari_raw - dc_in);
        dc_in = jawari_raw;
        dc_out = jawari;

        let res = 0.58 * jawari + 0.28 * body1.process(jawari) + 0.18 * body2.process(jawari);

        let atk = if (i as f64) < atk_samples {
            raised_cosine(i as f64 / atk_samples)
        } else {
            1.0
        };
        let tail_env = if i >= fade_start {
            1.0 - raised_cosine((i - fade_start) as f64 / fade_len as f64)
        } else {
            1.0
        };

        out[i] = (res * atk * tail_env * vel * 0.34) as f32;
    }

    out
}

/// Renders a Dotara (wooden-plectrum plucked folk lute with crisp attack and taut goatskin resonance).
pub fn render_dotara(step: i32, dur_s: f64, vel: f64, seed: u64) -> Vec<f32> {
    render_dotara_hz(step_to_freq(step), dur_s, vel, seed)
}

/// Renders a Dotara at an explicit fundamental frequency `freq` in Hz.
pub fn render_dotara_hz(freq: f64, dur_s: f64, vel: f64, seed: u64) -> Vec<f32> {
    let sr = SAMPLE_RATE as f64;
    let ring_s = (1.55 - 0.0005 * freq).clamp(1.05, 1.65);
    let total_s = dur_s.max(0.20).min(ring_s) + ring_s * 0.55;
    let n = (total_s * sr).ceil() as usize;

    let a = (0.31 - 0.00010 * freq).clamp(0.18, 0.33);
    let w = 2.0 * PI * freq / sr;
    let h_re = (1.0 - a) + a * w.cos();
    let h_im = -a * w.sin();
    let filter_phase_delay = -h_im.atan2(h_re) / w;
    let filter_mag = (h_re * h_re + h_im * h_im).sqrt();
    let delay = (sr / freq - filter_phase_delay).max(4.0);

    let buf_len: usize = 4096;
    let mask = buf_len - 1;
    let mut buf = vec![0.0_f64; buf_len];

    let init_len = (delay.round() as usize).clamp(4, buf_len - 8);
    let mut rng = XorShift64::new(seed);
    let mut exc_lp = BiquadLP::new((freq * (6.2 + 3.0 * vel)).clamp(900.0, 7200.0), 0.707);
    let mut write_idx = init_len + 4;
    let mut tmp = vec![0.0_f64; init_len];
    let mut mean = 0.0;
    for j in 0..init_len {
        let u = j as f64 / init_len as f64;
        // Sharper wooden-plectrum (kathi) triangular-like displacement + bright noise
        let tri = if u < 0.28 { u / 0.28 } else { (1.0 - u) / 0.72 };
        let noise = exc_lp.process(rng.next_bipolar()) * 0.58;
        let v = (tri - 0.35) * 0.75 + noise;
        tmp[j] = v;
        mean += v;
    }
    mean /= init_len as f64;
    for j in 0..init_len {
        let pos = (write_idx + buf_len - init_len + j) & mask;
        buf[pos] = tmp[j] - mean;
    }

    let raw_damp = 10.0_f64.powf(-3.0 / (ring_s * freq));
    let damp = (raw_damp / filter_mag).clamp(0.982, 0.9996);

    let mut skin1 = BiquadBP::new(290.0, 1.9);
    let mut skin2 = BiquadBP::new(960.0, 2.0);
    let mut prev_delayed = buf[(write_idx + buf_len - init_len) & mask];

    let mut out = vec![0.0_f32; n];
    let fade_start = (n as f64 * 0.68) as usize;
    let fade_len = (n - fade_start).max(1);
    let atk_samples = (0.0015 * sr).max(1.0);
    let symp_freq = freq * 3.0; // sympathetic 12th (octave + 5th)

    for i in 0..n {
        let t_sec = i as f64 / sr;
        let read_pos = write_idx as f64 - delay;
        let i0_f = read_pos.floor();
        let t = read_pos - i0_f;
        let i0 = (i0_f as isize).rem_euclid(buf_len as isize) as usize;

        let ym1 = buf[(i0 + buf_len - 1) & mask];
        let y0 = buf[i0];
        let y1 = buf[(i0 + 1) & mask];
        let y2 = buf[(i0 + 2) & mask];

        let c_m1 = -t * (t - 1.0) * (t - 2.0) / 6.0;
        let c_0 = (t + 1.0) * (t - 1.0) * (t - 2.0) / 2.0;
        let c_1 = -(t + 1.0) * t * (t - 2.0) / 2.0;
        let c_2 = (t + 1.0) * t * (t - 1.0) / 6.0;
        let delayed = c_m1 * ym1 + c_0 * y0 + c_1 * y1 + c_2 * y2;

        let lp = (1.0 - a) * delayed + a * prev_delayed;
        prev_delayed = delayed;
        let loop_val = lp * damp;

        buf[write_idx] = loop_val;
        write_idx = (write_idx + 1) & mask;

        let symp = if symp_freq < 0.42 * sr {
            0.06 * (2.0 * PI * symp_freq * t_sec).sin() * (-t_sec / 0.42).exp()
        } else {
            0.0
        };

        let body = 0.62 * loop_val + 0.25 * skin1.process(loop_val) + 0.20 * skin2.process(loop_val) + symp;

        let atk = if (i as f64) < atk_samples {
            raised_cosine(i as f64 / atk_samples)
        } else {
            1.0
        };
        let tail_env = if i >= fade_start {
            1.0 - raised_cosine((i - fade_start) as f64 / fade_len as f64)
        } else {
            1.0
        };

        out[i] = (body * atk * tail_env * vel * 0.34) as f32;
    }

    out
}

pub fn render_ektara_track(notes: &[IndianNote], total_samples: usize) -> Vec<(f32, f32)> {
    render_ektara_track_with_tuning(notes, total_samples, false)
}

pub fn render_ektara_track_with_tuning(
    notes: &[IndianNote],
    total_samples: usize,
    quantize_12tet: bool,
) -> Vec<(f32, f32)> {
    let mut out = vec![(0.0_f32, 0.0_f32); total_samples];
    for (idx, n) in notes.iter().enumerate() {
        if n.start_sample >= total_samples {
            continue;
        }
        let dur_s = (n.end_sample.saturating_sub(n.start_sample) as f64 / SAMPLE_RATE as f64).max(0.15);
        let seed = 0xE17A_0000_u64 ^ ((idx as u64).wrapping_mul(0x9E37_79B9_7F4A_7C15));
        let mono = if quantize_12tet {
            render_ektara_hz(
                step_cents_to_12tet_freq(n.step, 0.0),
                dur_s,
                n.velocity as f64,
                0.0,
                seed,
            )
        } else {
            render_ektara(n.step, dur_s, n.velocity as f64, n.meend_cents as f64, seed)
        };
        let limit = mono.len().min(total_samples - n.start_sample);
        for i in 0..limit {
            let s = mono[i];
            out[n.start_sample + i].0 += s;
            out[n.start_sample + i].1 += s;
        }
    }
    out
}

pub fn render_dotara_track(notes: &[IndianNote], total_samples: usize) -> Vec<(f32, f32)> {
    render_dotara_track_with_tuning(notes, total_samples, false)
}

pub fn render_dotara_track_with_tuning(
    notes: &[IndianNote],
    total_samples: usize,
    quantize_12tet: bool,
) -> Vec<(f32, f32)> {
    let mut out = vec![(0.0_f32, 0.0_f32); total_samples];
    for (idx, n) in notes.iter().enumerate() {
        if n.start_sample >= total_samples {
            continue;
        }
        let dur_s = (n.end_sample.saturating_sub(n.start_sample) as f64 / SAMPLE_RATE as f64).max(0.15);
        let seed = 0xD07A_0000_u64 ^ ((idx as u64).wrapping_mul(0xBF58_476D_1CE4_E5B9));
        let mono = if quantize_12tet {
            render_dotara_hz(
                step_cents_to_12tet_freq(n.step, 0.0),
                dur_s,
                n.velocity as f64,
                seed,
            )
        } else {
            render_dotara(n.step, dur_s, n.velocity as f64, seed)
        };
        let limit = mono.len().min(total_samples - n.start_sample);
        for i in 0..limit {
            let s = mono[i];
            out[n.start_sample + i].0 += s;
            out[n.start_sample + i].1 += s;
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::synth::tests::measure_pitch_hz;
    use crate::tuning::{step_to_freq, P4};

    #[test]
    fn test_indian_instruments_53edo_pitch_accuracy() {
        for &(step, label) in &[(0, "C4(53edo)"), (-P4, "G3(53edo)")] {
            let target = step_to_freq(step);

            let ekt = render_ektara(step, 1.2, 0.85, 0.0, 101_u64.wrapping_add(step as u64));
            let ekt_hz = measure_pitch_hz(&ekt, 4800, 14400, target * 0.8, target * 1.25);
            let ekt_err = (1200.0 * (ekt_hz / target).log2()).abs();
            assert!(
                ekt_err < 5.0,
                "Ektara {label} pitch error {ekt_err:.2} cents (target {target:.2} Hz, measured {ekt_hz:.2} Hz)"
            );

            let dot = render_dotara(step, 1.2, 0.85, 202_u64.wrapping_add(step as u64));
            let dot_hz = measure_pitch_hz(&dot, 4800, 14400, target * 0.8, target * 1.25);
            let dot_err = (1200.0 * (dot_hz / target).log2()).abs();
            assert!(
                dot_err < 5.0,
                "Dotara {label} pitch error {dot_err:.2} cents (target {target:.2} Hz, measured {dot_hz:.2} Hz)"
            );
        }
    }
}
