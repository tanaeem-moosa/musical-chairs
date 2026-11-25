//! Acoustic instrument physical & additive synthesizer for 53-EDO chamber orchestra.

use std::f64::consts::PI;

use crate::reverb::{apply_hall_reverb_and_master, AudioStats};
use crate::score::{Articulation, Instrument, NoteEvent, Score};
use crate::tuning::step_cents_to_freq;

pub const SAMPLE_RATE: usize = 48_000;

pub(crate) struct XorShift64 {
    state: u64,
}

impl XorShift64 {
    pub(crate) fn new(seed: u64) -> Self {
        Self {
            state: seed ^ 0xA5A5_5A5A_1234_5678,
        }
    }

    #[inline]
    pub(crate) fn next_u64(&mut self) -> u64 {
        let mut x = self.state;
        if x == 0 {
            x = 0x9E37_79B9_7F4A_7C15;
        }
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        self.state = x;
        x
    }

    /// Uniform in [-1.0, 1.0].
    #[inline]
    pub(crate) fn next_bipolar(&mut self) -> f64 {
        let u = (self.next_u64() >> 11) as f64 * (1.0 / ((1u64 << 53) as f64));
        u * 2.0 - 1.0
    }
}

#[derive(Clone, Copy)]
pub(crate) struct BiquadLP {
    b0: f64,
    b1: f64,
    b2: f64,
    a1: f64,
    a2: f64,
    z1: f64,
    z2: f64,
}

impl BiquadLP {
    pub(crate) fn new(cutoff_hz: f64, q: f64) -> Self {
        let fc = cutoff_hz.clamp(40.0, 0.42 * SAMPLE_RATE as f64);
        let w0 = 2.0 * PI * fc / SAMPLE_RATE as f64;
        let cos_w0 = w0.cos();
        let alpha = w0.sin() / (2.0 * q);
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
    pub(crate) fn process(&mut self, x: f64) -> f64 {
        let y = self.b0 * x + self.z1;
        self.z1 = self.b1 * x - self.a1 * y + self.z2;
        self.z2 = self.b2 * x - self.a2 * y;
        y
    }
}

#[inline]
pub(crate) fn raised_cosine(u: f64) -> f64 {
    0.5 - 0.5 * (PI * u.clamp(0.0, 1.0)).cos()
}

fn pan_and_reverb(inst: Instrument) -> (f64, f64, f64) {
    let (pan, rev) = match inst {
        Instrument::Violin1 => (-0.48, 0.34),
        Instrument::Harp => (-0.36, 0.38),
        Instrument::Violin2 => (-0.22, 0.34),
        Instrument::Flute => (-0.16, 0.36),
        Instrument::OrganPedal => (0.00, 0.30),
        Instrument::Contrabass => (0.12, 0.15),
        Instrument::Clarinet => (0.18, 0.34),
        Instrument::Viola => (0.26, 0.34),
        Instrument::Celesta => (0.35, 0.42),
        Instrument::Cello => (0.46, 0.32),
    };
    let angle = (pan + 1.0) * (PI * 0.25);
    (angle.cos(), angle.sin(), rev)
}

/// Renders an entire `Score` into mastered stereo audio plus quality statistics.
pub fn render_score(score: &Score, tail_seconds: f64) -> (Vec<(f32, f32)>, AudioStats) {
    let total_secs = score.total_duration_seconds(tail_seconds);
    let total_samples = (total_secs * SAMPLE_RATE as f64).ceil() as usize + 1024;

    let mut dry = vec![(0.0_f32, 0.0_f32); total_samples];
    let mut send = vec![(0.0_f32, 0.0_f32); total_samples];

    for (idx, note) in score.notes.iter().enumerate() {
        let start_s = score.tempo.beat_to_seconds(note.start_beat);
        let end_s = score.tempo.beat_to_seconds(note.start_beat + note.duration_beat);
        let dur_s = (end_s - start_s).max(0.03);
        let start_sample = (start_s * SAMPLE_RATE as f64).round() as usize;
        if start_sample >= total_samples {
            continue;
        }

        let seed = ((idx as u64).wrapping_mul(0x9E37_79B9_7F4A_7C15))
            ^ ((note.step as i64 as u64).wrapping_mul(0xBF58_476D_1CE4_E5B9));
        let mono = synthesize_note(note, dur_s, seed);
        let (gl, gr, rev_amt) = pan_and_reverb(note.instrument);

        let limit = mono.len().min(total_samples - start_sample);
        for i in 0..limit {
            let s = mono[i];
            let l = s * gl as f32;
            let r = s * gr as f32;
            dry[start_sample + i].0 += l;
            dry[start_sample + i].1 += r;
            send[start_sample + i].0 += l * rev_amt as f32;
            send[start_sample + i].1 += r * rev_amt as f32;
        }
    }

    apply_hall_reverb_and_master(&dry, &send, SAMPLE_RATE)
}

pub fn synthesize_note(note: &NoteEvent, dur_s: f64, seed: u64) -> Vec<f32> {
    let freq = step_cents_to_freq(note.step, note.micro_cents as f64);
    let vel = note.velocity as f64;
    let rng = XorShift64::new(seed);

    match note.instrument {
        Instrument::Violin1
        | Instrument::Violin2
        | Instrument::Viola
        | Instrument::Cello
        | Instrument::Contrabass => render_string(note.instrument, freq, dur_s, vel, note.articulation, rng),
        Instrument::Harp => render_harp(freq, dur_s, vel, rng),
        Instrument::Celesta => render_celesta(freq, dur_s, vel, rng),
        Instrument::Flute => render_flute(freq, dur_s, vel, note.articulation, rng),
        Instrument::Clarinet => render_clarinet(freq, dur_s, vel, note.articulation, rng),
        Instrument::OrganPedal => render_organ_pedal(freq, dur_s, vel, rng),
    }
}

fn render_string(
    inst: Instrument,
    freq: f64,
    dur_s: f64,
    vel: f64,
    art: Articulation,
    mut rng: XorShift64,
) -> Vec<f32> {
    let attack_s = match inst {
        Instrument::Contrabass => 0.14,
        Instrument::Cello => 0.11,
        _ => match art {
            Articulation::Sustained => 0.14,
            _ => 0.085,
        },
    };
    let release_s = 0.45;
    let total_s = dur_s + release_s;
    let n = (total_s * SAMPLE_RATE as f64).ceil() as usize;
    let sr = SAMPLE_RATE as f64;
    let nyq_limit = 0.44 * sr;

    let (base_cut, section_gain) = match inst {
        Instrument::Violin1 => (2550.0, 0.21),
        Instrument::Violin2 => (2000.0, 0.19),
        Instrument::Viola => (1450.0, 0.20),
        Instrument::Cello => (960.0, 0.24),
        Instrument::Contrabass => (460.0, 0.29),
        _ => (1800.0, 0.20),
    };
    let mut body_lp = BiquadLP::new(base_cut * (0.78 + 0.45 * vel), 0.72);
    let mut bow_lp = BiquadLP::new((base_cut * 0.9).min(1800.0), 0.707);

    let vib_cents = match (inst, art) {
        (Instrument::Contrabass, _) => 1.2,
        (_, Articulation::Sustained) => 2.0,
        (_, Articulation::Legato | Articulation::Expressive) => 5.0,
        _ => 3.5,
    };
    let vib_rate = 5.0 + 0.35 * rng.next_bipolar();

    let max_h = ((nyq_limit / freq).floor() as usize).clamp(1, 22);
    let mut harm_amps = Vec::with_capacity(max_h);
    let mut norm = 0.0_f64;
    for k in 1..=max_h {
        let kf = k as f64;
        // Slight odd-harmonic warmth plus bow-bridge coloration
        let bridge_shape = if k % 2 == 1 { 1.0 } else { 0.86 };
        let a = bridge_shape / kf.powf(1.35);
        norm += a * a;
        harm_amps.push(a);
    }
    let harm_norm = 1.0 / norm.sqrt();

    let detune_cents = [-2.0_f64, 0.0, 2.0];
    let mut phases = [
        [0.0_f64; 22],
        [0.0_f64; 22],
        [0.0_f64; 22],
    ];
    for v in 0..3 {
        for k in 0..max_h {
            phases[v][k] = rng.next_bipolar() * PI;
        }
    }

    let mut out = vec![0.0_f32; n];
    let dur_samples = dur_s * sr;
    let atk_samples = attack_s * sr;
    let rel_samples = release_s * sr;

    for i in 0..n {
        let t = i as f64 / sr;
        let fi = i as f64;

        let env = if fi < dur_samples {
            let a = if fi < atk_samples {
                raised_cosine(fi / atk_samples)
            } else {
                1.0
            };
            // Gentle expressive arch across held phrases
            let mid = (fi / dur_samples).clamp(0.0, 1.0);
            let swell = 0.90 + 0.14 * (PI * mid).sin();
            a * swell
        } else {
            let r = (fi - dur_samples) / rel_samples;
            1.0 - raised_cosine(r)
        };

        let vib_ramp = ((t - 0.12) / 0.40).clamp(0.0, 1.0);
        let vib_mod = vib_cents * vib_ramp * (2.0 * PI * vib_rate * t).sin();

        let mut voice_sum = 0.0_f64;
        for v in 0..3 {
            let cents = detune_cents[v] + vib_mod;
            let f_v = freq * 2.0_f64.powf(cents / 1200.0);
            let dphi = 2.0 * PI * f_v / sr;
            let mut s = 0.0_f64;
            for k in 0..max_h {
                let mult = (k + 1) as f64;
                phases[v][k] += dphi * mult;
                if phases[v][k] > PI {
                    phases[v][k] -= 2.0 * PI;
                }
                s += harm_amps[k] * phases[v][k].sin();
            }
            voice_sum += s * harm_norm;
        }
        voice_sum /= 3.0_f64.sqrt();

        // Subtle bow-rosin onset breath
        let bow_env = (-t / 0.065).exp() * (t / 0.015).min(1.0);
        let bow_noise = bow_lp.process(rng.next_bipolar()) * 0.055 * bow_env;

        let filtered = body_lp.process(voice_sum + bow_noise);
        out[i] = (filtered * env * vel * section_gain) as f32;
    }

    out
}

/// Exact-pitch fractional-delay Karplus-Strong harp with 4-point cubic Lagrange interpolation.
fn render_harp(freq: f64, dur_s: f64, vel: f64, mut rng: XorShift64) -> Vec<f32> {
    let ring_s = (3.4 - 0.0014 * freq).clamp(1.6, 3.6);
    let total_s = dur_s.max(0.25).min(ring_s) + ring_s * 0.65;
    let n = (total_s * SAMPLE_RATE as f64).ceil() as usize;
    let sr = SAMPLE_RATE as f64;

    // Warm string damping factor (warmer in bass, brighter in treble)
    let a = (0.43 - 0.00014 * freq).clamp(0.26, 0.44);
    let w = 2.0 * PI * freq / sr;

    // Exact phase delay of y[n] = (1 - a)*x[n] + a*x[n-1]
    let h_re = (1.0 - a) + a * w.cos();
    let h_im = -a * w.sin();
    let filter_phase_delay = -h_im.atan2(h_re) / w;
    let filter_mag = (h_re * h_re + h_im * h_im).sqrt();

    let period_samples = sr / freq;
    let delay = (period_samples - filter_phase_delay).max(4.0);

    // Power-of-two ring buffer >= 4096 samples (covers down to ~12 Hz with room for cubic taps)
    let buf_len: usize = 4096;
    let mask = buf_len - 1;
    let mut buf = vec![0.0_f64; buf_len];

    // Soft plucked initial displacement: half-sine shape + low-passed gentle noise
    let init_len = (delay.round() as usize).clamp(4, buf_len - 8);
    let mut exc_lp = BiquadLP::new((freq * (3.8 + 2.5 * vel)).clamp(450.0, 5200.0), 0.707);
    let mut write_idx = init_len + 4;
    let mut dc_mean = 0.0_f64;
    let mut tmp_exc = vec![0.0_f64; init_len];
    for j in 0..init_len {
        let u = j as f64 / init_len as f64;
        let pluck_shape = (PI * u).sin() * 0.65 + (2.0 * PI * u).sin() * 0.15;
        let noise = exc_lp.process(rng.next_bipolar()) * 0.45;
        let val = pluck_shape + noise;
        tmp_exc[j] = val;
        dc_mean += val;
    }
    dc_mean /= init_len as f64;
    for j in 0..init_len {
        let pos = (write_idx + buf_len - init_len + j) & mask;
        buf[pos] = tmp_exc[j] - dc_mean;
    }

    // Calibrate loop decay for natural harp ring-out compensating for |H(w)|
    let decay_target = (ring_s * 0.95).max(1.2);
    let raw_damp = 10.0_f64.powf(-3.0 / (decay_target * freq));
    let damp = (raw_damp / filter_mag).clamp(0.985, 0.99985);

    let mut body_lp = BiquadLP::new((freq * 7.5 + 1400.0).min(8500.0), 0.65);
    let mut prev_delayed = buf[(write_idx + buf_len - init_len) & mask];
    let mut out = vec![0.0_f32; n];
    let fade_start = (n as f64 * 0.72) as usize;
    let fade_len = (n - fade_start).max(1);
    let atk_samples = (0.0025 * sr).max(1.0);

    for i in 0..n {
        let read_pos = write_idx as f64 - delay;
        let i0_f = read_pos.floor();
        let t = read_pos - i0_f;
        let i0 = (i0_f as isize).rem_euclid(buf_len as isize) as usize;

        let ym1 = buf[(i0 + buf_len - 1) & mask];
        let y0 = buf[i0];
        let y1 = buf[(i0 + 1) & mask];
        let y2 = buf[(i0 + 2) & mask];

        // 4-point cubic Lagrange interpolation over x in {-1, 0, 1, 2}
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

        let sample = body_lp.process(loop_val) * atk * tail_env * vel * 0.28;
        out[i] = sample as f32;
    }

    out
}

fn render_celesta(freq: f64, dur_s: f64, vel: f64, mut rng: XorShift64) -> Vec<f32> {
    let ring_s = (2.25 - 0.0005 * freq).clamp(1.3, 2.3);
    let total_s = dur_s.max(0.2) + ring_s;
    let n = (total_s * SAMPLE_RATE as f64).ceil() as usize;
    let sr = SAMPLE_RATE as f64;

    let mut out = vec![0.0_f32; n];
    let p1 = rng.next_bipolar() * PI;
    let p2 = rng.next_bipolar() * PI;
    let p3 = rng.next_bipolar() * PI;
    let p_bar = rng.next_bipolar() * PI;
    let mut mallet_lp = BiquadLP::new(1900.0, 0.707);

    let atk_s = 0.0035;
    for i in 0..n {
        let t = i as f64 / sr;
        let atk = if t < atk_s {
            raised_cosine(t / atk_s)
        } else {
            1.0
        };

        let e1 = (-t / (ring_s * 0.55)).exp();
        let e2 = (-t / (ring_s * 0.25)).exp();
        let e3 = (-t / (ring_s * 0.12)).exp();
        let e_bar = (-t / 0.14).exp();

        let s1 = (2.0 * PI * freq * t + p1).sin() * e1;
        let s2 = if freq * 2.0 < 0.44 * sr {
            0.22 * (2.0 * PI * freq * 2.0 * t + p2).sin() * e2
        } else {
            0.0
        };
        let s3 = if freq * 3.0 < 0.44 * sr {
            0.06 * (2.0 * PI * freq * 3.0 * t + p3).sin() * e3
        } else {
            0.0
        };
        let s_bar = if freq * 2.756 < 0.44 * sr {
            0.055 * (2.0 * PI * freq * 2.756 * t + p_bar).sin() * e_bar
        } else {
            0.0
        };

        let felt = mallet_lp.process(rng.next_bipolar()) * 0.04 * (-t / 0.012).exp();
        let tail_env = if t > total_s - 0.15 {
            1.0 - raised_cosine((t - (total_s - 0.15)) / 0.15)
        } else {
            1.0
        };

        out[i] = ((s1 + s2 + s3 + s_bar + felt) * atk * tail_env * vel * 0.23) as f32;
    }

    out
}

fn render_flute(
    freq: f64,
    dur_s: f64,
    vel: f64,
    art: Articulation,
    mut rng: XorShift64,
) -> Vec<f32> {
    let attack_s = 0.060;
    let release_s = 0.26;
    let total_s = dur_s + release_s;
    let n = (total_s * SAMPLE_RATE as f64).ceil() as usize;
    let sr = SAMPLE_RATE as f64;

    let vib_cents = match art {
        Articulation::Sustained => 2.5,
        _ => 5.5,
    };
    let vib_rate = 5.0 + 0.25 * rng.next_bipolar();
    let mut chiff_lp = BiquadLP::new((freq * 2.4).clamp(700.0, 3200.0), 1.4);
    let mut air_lp = BiquadLP::new(2400.0, 0.707);

    let mut phase = rng.next_bipolar() * PI;
    let mut out = vec![0.0_f32; n];
    let dur_samples = dur_s * sr;
    let atk_samples = attack_s * sr;
    let rel_samples = release_s * sr;

    for i in 0..n {
        let t = i as f64 / sr;
        let fi = i as f64;
        let env = if fi < dur_samples {
            let a = if fi < atk_samples {
                raised_cosine(fi / atk_samples)
            } else {
                1.0
            };
            let mid = (fi / dur_samples).clamp(0.0, 1.0);
            a * (0.92 + 0.10 * (PI * mid).sin())
        } else {
            1.0 - raised_cosine((fi - dur_samples) / rel_samples)
        };

        let vib_ramp = ((t - 0.14) / 0.35).clamp(0.0, 1.0);
        let vib = vib_cents * vib_ramp * (2.0 * PI * vib_rate * t).sin();
        let f_inst = freq * 2.0_f64.powf(vib / 1200.0);
        phase += 2.0 * PI * f_inst / sr;
        if phase > PI {
            phase -= 2.0 * PI;
        }

        let breath_bloom = (t / 0.20).min(1.0);
        let mut s = phase.sin();
        if f_inst * 2.0 < 0.44 * sr {
            s += (0.28 * vel * breath_bloom) * (2.0 * phase).sin();
        }
        if f_inst * 3.0 < 0.44 * sr {
            s += (0.08 * vel) * (3.0 * phase).sin();
        }
        if f_inst * 4.0 < 0.44 * sr {
            s += 0.025 * (4.0 * phase).sin();
        }

        let chiff = chiff_lp.process(rng.next_bipolar()) * 0.09 * (-t / 0.048).exp();
        let air = air_lp.process(rng.next_bipolar()) * 0.016;
        out[i] = ((s + chiff + air) * env * vel * 0.23) as f32;
    }

    out
}

fn render_clarinet(
    freq: f64,
    dur_s: f64,
    vel: f64,
    art: Articulation,
    mut rng: XorShift64,
) -> Vec<f32> {
    let attack_s = 0.048;
    let release_s = 0.25;
    let total_s = dur_s + release_s;
    let n = (total_s * SAMPLE_RATE as f64).ceil() as usize;
    let sr = SAMPLE_RATE as f64;

    let vib_cents = match art {
        Articulation::Sustained => 1.5,
        _ => 3.0,
    };
    let vib_rate = 4.8 + 0.2 * rng.next_bipolar();
    let mut woody_lp = BiquadLP::new(1500.0 + 450.0 * vel, 0.75);
    let mut reed_lp = BiquadLP::new(1800.0, 0.8);

    const HARMS: [(f64, f64); 8] = [
        (1.0, 1.0),
        (2.0, 0.07),
        (3.0, 0.52),
        (4.0, 0.05),
        (5.0, 0.22),
        (6.0, 0.025),
        (7.0, 0.09),
        (9.0, 0.035),
    ];

    let mut phase = rng.next_bipolar() * PI;
    let mut out = vec![0.0_f32; n];
    let dur_samples = dur_s * sr;
    let atk_samples = attack_s * sr;
    let rel_samples = release_s * sr;

    for i in 0..n {
        let t = i as f64 / sr;
        let fi = i as f64;
        let env = if fi < dur_samples {
            if fi < atk_samples {
                raised_cosine(fi / atk_samples)
            } else {
                1.0
            }
        } else {
            1.0 - raised_cosine((fi - dur_samples) / rel_samples)
        };

        let vib_ramp = ((t - 0.18) / 0.35).clamp(0.0, 1.0);
        let vib = vib_cents * vib_ramp * (2.0 * PI * vib_rate * t).sin();
        let f_inst = freq * 2.0_f64.powf(vib / 1200.0);
        phase += 2.0 * PI * f_inst / sr;
        if phase > PI {
            phase -= 2.0 * PI;
        }

        let mut s = 0.0;
        for &(mult, amp) in &HARMS {
            if f_inst * mult < 0.44 * sr {
                s += amp * (mult * phase).sin();
            }
        }

        let reed_noise = reed_lp.process(rng.next_bipolar()) * 0.035 * (-t / 0.035).exp();
        let filtered = woody_lp.process(s * 0.78 + reed_noise);
        out[i] = (filtered * env * vel * 0.22) as f32;
    }

    out
}

fn render_organ_pedal(freq: f64, dur_s: f64, vel: f64, mut rng: XorShift64) -> Vec<f32> {
    let attack_s = 0.12;
    let release_s = 0.55;
    let total_s = dur_s + release_s;
    let n = (total_s * SAMPLE_RATE as f64).ceil() as usize;
    let sr = SAMPLE_RATE as f64;

    let mut pipe_lp = BiquadLP::new(820.0, 0.707);
    let mut chiff_lp = BiquadLP::new(600.0, 0.9);
    let mut phase = rng.next_bipolar() * PI;
    let mut sub_phase = rng.next_bipolar() * PI;

    let has_sub16 = freq >= 62.0; // >= ~C2
    let mut out = vec![0.0_f32; n];
    let dur_samples = dur_s * sr;
    let atk_samples = attack_s * sr;
    let rel_samples = release_s * sr;

    for i in 0..n {
        let t = i as f64 / sr;
        let fi = i as f64;
        let env = if fi < dur_samples {
            if fi < atk_samples {
                raised_cosine(fi / atk_samples)
            } else {
                1.0
            }
        } else {
            1.0 - raised_cosine((fi - dur_samples) / rel_samples)
        };

        phase += 2.0 * PI * freq / sr;
        if phase > PI {
            phase -= 2.0 * PI;
        }
        sub_phase += 2.0 * PI * (freq * 0.5) / sr;
        if sub_phase > PI {
            sub_phase -= 2.0 * PI;
        }

        let mut s = phase.sin()
            + 0.34 * (2.0 * phase).sin()
            + 0.16 * (3.0 * phase).sin()
            + 0.07 * (4.0 * phase).sin()
            + 0.025 * (5.0 * phase).sin();
        if has_sub16 {
            s += 0.40 * sub_phase.sin();
        }

        let chiff = chiff_lp.process(rng.next_bipolar()) * 0.045 * (-t / 0.075).exp();
        let filtered = pipe_lp.process(s * 0.68 + chiff);
        out[i] = (filtered * env * vel * 0.24) as f32;
    }

    out
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;
    use crate::tuning::step_to_freq;

    #[cfg(test)]
    pub(crate) fn measure_pitch_hz(samples: &[f32], start: usize, len: usize, min_f: f64, max_f: f64) -> f64 {
        let end = (start + len).min(samples.len());
        let slice = &samples[start..end];
        let min_lag = (SAMPLE_RATE as f64 / max_f).floor() as usize;
        let max_lag = (SAMPLE_RATE as f64 / min_f).ceil() as usize;

        let mut best_lag = min_lag;
        let mut best_corr = f64::NEG_INFINITY;
        let mut corrs = vec![0.0_f64; max_lag + 2];

        for lag in (min_lag.saturating_sub(1))..=(max_lag + 1).min(slice.len() / 2) {
            let mut sum = 0.0_f64;
            let mut e1 = 0.0_f64;
            let mut e2 = 0.0_f64;
            for i in 0..(slice.len() - lag) {
                let a = slice[i] as f64;
                let b = slice[i + lag] as f64;
                sum += a * b;
                e1 += a * a;
                e2 += b * b;
            }
            let norm = sum / (e1 * e2).sqrt().max(1e-12);
            corrs[lag] = norm;
            if lag >= min_lag && lag <= max_lag && norm > best_corr {
                best_corr = norm;
                best_lag = lag;
            }
        }

        // Parabolic interpolation around best_lag
        let y_m1 = corrs[best_lag - 1];
        let y_0 = corrs[best_lag];
        let y_p1 = corrs[best_lag + 1];
        let denom = y_m1 - 2.0 * y_0 + y_p1;
        let delta = if denom.abs() > 1e-12 {
            0.5 * (y_m1 - y_p1) / denom
        } else {
            0.0
        };

        SAMPLE_RATE as f64 / (best_lag as f64 + delta.clamp(-0.5, 0.5))
    }

    #[test]
    fn test_harp_karplus_strong_pitch_accuracy() {
        for &(step, label) in &[(39, "A4"), (0, "C4"), (31, "G4")] {
            let note = NoteEvent {
                instrument: Instrument::Harp,
                start_beat: 0.0,
                duration_beat: 2.0,
                step,
                velocity: 0.8,
                articulation: Articulation::Plucked,
                micro_cents: 0.0,
            };
            let audio = synthesize_note(&note, 1.5, 42 + step as u64);
            let target = step_to_freq(step);
            let measured = measure_pitch_hz(&audio, 4800, 14400, target * 0.8, target * 1.25);
            let cents_err = (1200.0 * (measured / target).log2()).abs();
            assert!(
                cents_err < 5.0,
                "Harp {label} pitch error {cents_err:.2} cents (target {target:.2} Hz, measured {measured:.2} Hz)"
            );
        }
    }
}
