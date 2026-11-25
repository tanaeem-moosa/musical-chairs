//! Chamber concert hall reverb (early reflections + 8-channel Walsh-Hadamard FDN)
//! and mastering stage (DC blocker, soft-knee limiter, peak normalization).

use std::f64::consts::PI;

#[derive(Clone, Debug)]
pub struct AudioStats {
    pub peak_db: f64,
    pub rms_l_db: f64,
    pub rms_r_db: f64,
    pub clipped_samples: usize,
    pub nan_count: usize,
}

/// Applies stereo concert hall reverb + 18 Hz DC blocker linearly (no limiting/normalization).
pub fn apply_hall_reverb_linear(
    dry: &[(f32, f32)],
    send: &[(f32, f32)],
    sample_rate: usize,
) -> Vec<(f64, f64)> {
    apply_hall_reverb_linear_with_rt60(dry, send, sample_rate, 2.25)
}

/// Applies stereo concert hall reverb with configurable RT60 + 18 Hz DC blocker linearly.
pub fn apply_hall_reverb_linear_with_rt60(
    dry: &[(f32, f32)],
    send: &[(f32, f32)],
    sample_rate: usize,
    rt60_seconds: f64,
) -> Vec<(f64, f64)> {
    assert_eq!(dry.len(), send.len());
    let n = dry.len();
    let sr = sample_rate as f64;

    let mut mix = Vec::with_capacity(n);

    if rt60_seconds <= 0.01 {
        for &(l, r) in dry {
            mix.push((l as f64, r as f64));
        }
    } else {
        // 1. High-pass filter the reverb send at ~115 Hz to keep the low end clean.
        let hp_alpha = (-2.0 * PI * 115.0 / sr).exp();
        let mut hp_prev_in_l = 0.0_f64;
        let mut hp_prev_out_l = 0.0_f64;
        let mut hp_prev_in_r = 0.0_f64;
        let mut hp_prev_out_r = 0.0_f64;

        // 2. Stereo early reflection taps (prime ms spacings 11..37 ms).
        let er_buf_len = (0.050 * sr) as usize + 16;
        let mut er_buf_l = vec![0.0_f64; er_buf_len];
        let mut er_buf_r = vec![0.0_f64; er_buf_len];
        let mut er_idx = 0usize;

        let er_taps_l: [(usize, f64); 6] = [
            ((0.0113 * sr) as usize, 0.24),
            ((0.0171 * sr) as usize, -0.19),
            ((0.0219 * sr) as usize, 0.16),
            ((0.0277 * sr) as usize, -0.13),
            ((0.0331 * sr) as usize, 0.11),
            ((0.0373 * sr) as usize, -0.08),
        ];
        let er_taps_r: [(usize, f64); 6] = [
            ((0.0127 * sr) as usize, 0.23),
            ((0.0183 * sr) as usize, -0.18),
            ((0.0233 * sr) as usize, 0.16),
            ((0.0289 * sr) as usize, -0.13),
            ((0.0347 * sr) as usize, 0.10),
            ((0.0389 * sr) as usize, -0.08),
        ];

        // 3. 8-channel Walsh-Hadamard FDN with prime delay lengths (~29..73 ms at 48 kHz).
        const CH: usize = 8;
        let base_delays: [usize; CH] = [1399, 1637, 1973, 2267, 2549, 2927, 3217, 3511];
        let fdn_delays: [usize; CH] = if sample_rate == 48_000 {
            base_delays
        } else {
            let ratio = sr / 48_000.0;
            std::array::from_fn(|i| ((base_delays[i] as f64 * ratio).round() as usize).max(64))
        };
        let rt60 = rt60_seconds.clamp(0.15, 15.0);
        let mut fdn_bufs: Vec<Vec<f64>> = fdn_delays.iter().map(|&d| vec![0.0; d]).collect();
        let mut fdn_idx = [0usize; CH];
        let mut fdn_lp = [0.0_f64; CH];
        let fdn_gains: [f64; CH] = std::array::from_fn(|i| {
            10.0_f64.powf(-3.0 * fdn_delays[i] as f64 / (rt60 * sr))
        });
        let lp_damp = 0.34_f64; // high-frequency air absorption inside hall
        let norm_h = 1.0_f64 / (CH as f64).sqrt();

        let mut er_lp_l = 0.0_f64;
        let mut er_lp_r = 0.0_f64;

        for i in 0..n {
            let in_l = send[i].0 as f64;
            let in_r = send[i].1 as f64;

            let hp_l = hp_alpha * (hp_prev_out_l + in_l - hp_prev_in_l);
            hp_prev_in_l = in_l;
            hp_prev_out_l = hp_l;

            let hp_r = hp_alpha * (hp_prev_out_r + in_r - hp_prev_in_r);
            hp_prev_in_r = in_r;
            hp_prev_out_r = hp_r;

            er_buf_l[er_idx] = hp_l;
            er_buf_r[er_idx] = hp_r;

            let mut er_l = 0.0;
            let mut er_r = 0.0;
            for &(tap, gain) in &er_taps_l {
                let pos = (er_idx + er_buf_len - tap) % er_buf_len;
                er_l += er_buf_l[pos] * gain;
            }
            for &(tap, gain) in &er_taps_r {
                let pos = (er_idx + er_buf_len - tap) % er_buf_len;
                er_r += er_buf_r[pos] * gain;
            }
            er_idx = (er_idx + 1) % er_buf_len;

            er_lp_l = 0.72 * er_l + 0.28 * er_lp_l;
            er_lp_r = 0.72 * er_r + 0.28 * er_lp_r;

            // Read FDN delay outputs
            let mut x = [0.0_f64; CH];
            for c in 0..CH {
                let delayed = fdn_bufs[c][fdn_idx[c]];
                fdn_lp[c] = (1.0 - lp_damp) * delayed + lp_damp * fdn_lp[c];
                x[c] = fdn_lp[c] * fdn_gains[c];
            }

            // Fast 8-point Walsh-Hadamard transform
            let mut h = x;
            for step in [1usize, 2, 4] {
                let mut j = 0;
                while j < CH {
                    for k in 0..step {
                        let a = h[j + k];
                        let b = h[j + k + step];
                        h[j + k] = a + b;
                        h[j + k + step] = a - b;
                    }
                    j += step * 2;
                }
            }
            for c in 0..CH {
                h[c] *= norm_h;
            }

            // Feed stereo input into FDN channels and advance pointers
            let mono_cross = 0.25 * (hp_l + hp_r);
            for c in 0..CH {
                let feed = if c % 2 == 0 {
                    0.75 * hp_l + 0.25 * mono_cross
                } else {
                    0.75 * hp_r + 0.25 * mono_cross
                };
                fdn_bufs[c][fdn_idx[c]] = h[c] + feed * 0.48;
                fdn_idx[c] = (fdn_idx[c] + 1) % fdn_delays[c];
            }

            // Decorrelated stereo wet sum
            let late_l = 0.26 * (x[0] - x[2] + x[4] - x[6] + 0.30 * (x[1] - x[5]));
            let late_r = 0.26 * (x[1] - x[3] + x[5] - x[7] + 0.30 * (x[2] - x[6]));

            let wet_l = 0.30 * er_lp_l + late_l;
            let wet_r = 0.30 * er_lp_r + late_r;

            mix.push((dry[i].0 as f64 + wet_l, dry[i].1 as f64 + wet_r));
        }
    }

    // Gentle 18 Hz DC blocker
    let dc_alpha = (-2.0 * PI * 18.0 / sr).exp();
    let mut dc_in_l = 0.0_f64;
    let mut dc_out_l = 0.0_f64;
    let mut dc_in_r = 0.0_f64;
    let mut dc_out_r = 0.0_f64;

    for pair in &mut mix {
        if !pair.0.is_finite() || !pair.1.is_finite() {
            *pair = (0.0, 0.0);
            continue;
        }
        let dl = dc_alpha * (dc_out_l + pair.0 - dc_in_l);
        dc_in_l = pair.0;
        dc_out_l = dl;

        let dr = dc_alpha * (dc_out_r + pair.1 - dc_in_r);
        dc_in_r = pair.1;
        dc_out_r = dr;

        pair.0 = dl;
        pair.1 = dr;
    }

    mix
}

/// Scales a linear stereo buffer by a constant gain (used for synced stems).
pub fn scale_linear_buffer(mix: &[(f64, f64)], gain: f64) -> Vec<(f32, f32)> {
    mix.iter()
        .map(|&(l, r)| ((l * gain) as f32, (r * gain) as f32))
        .collect()
}

/// Computes exact peak-normalizing gain to -1.0 dBFS without nonlinear distortion.
pub fn compute_target_norm_gain(mix: &[(f64, f64)]) -> f64 {
    let max_abs = mix
        .iter()
        .map(|&(l, r)| l.abs().max(r.abs()))
        .fold(0.0_f64, f64::max);
    let target_peak = 10.0_f64.powf(-1.0 / 20.0);
    if max_abs > 1e-9 {
        target_peak / max_abs
    } else {
        1.0
    }
}

/// Computes stats from an already-scaled stereo f32 buffer.
pub fn compute_audio_stats(samples: &[(f32, f32)]) -> AudioStats {
    let n = samples.len().max(1);
    let mut sum_sq_l = 0.0_f64;
    let mut sum_sq_r = 0.0_f64;
    let mut final_peak = 0.0_f64;
    let mut clipped_samples = 0usize;
    let mut nan_count = 0usize;

    for &(l, r) in samples {
        let fl = l as f64;
        let fr = r as f64;
        if !fl.is_finite() || !fr.is_finite() {
            nan_count += 1;
            continue;
        }
        if fl.abs() >= 1.0 || fr.abs() >= 1.0 {
            clipped_samples += 1;
        }
        final_peak = final_peak.max(fl.abs()).max(fr.abs());
        sum_sq_l += fl * fl;
        sum_sq_r += fr * fr;
    }

    let rms_l = (sum_sq_l / n as f64).sqrt();
    let rms_r = (sum_sq_r / n as f64).sqrt();
    let to_db = |v: f64| if v > 1e-12 { 20.0 * v.log10() } else { -120.0 };

    AudioStats {
        peak_db: to_db(final_peak),
        rms_l_db: to_db(rms_l),
        rms_r_db: to_db(rms_r),
        clipped_samples,
        nan_count,
    }
}

/// Applies stereo concert hall reverb to `send` and mixes it with `dry`, then masters.
pub fn apply_hall_reverb_and_master(
    dry: &[(f32, f32)],
    send: &[(f32, f32)],
    sample_rate: usize,
) -> (Vec<(f32, f32)>, AudioStats) {
    apply_hall_reverb_and_master_with_rt60(dry, send, sample_rate, 2.25)
}

/// Applies stereo concert hall reverb with configurable RT60 to `send`, mixes with `dry`, and masters.
pub fn apply_hall_reverb_and_master_with_rt60(
    dry: &[(f32, f32)],
    send: &[(f32, f32)],
    sample_rate: usize,
    rt60_seconds: f64,
) -> (Vec<(f32, f32)>, AudioStats) {
    let n = dry.len();
    let mut mix = apply_hall_reverb_linear_with_rt60(dry, send, sample_rate, rt60_seconds);

    let max_abs = mix
        .iter()
        .map(|&(l, r)| l.abs().max(r.abs()))
        .fold(0.0_f64, f64::max);

    // Pre-scale so typical peaks sit cleanly below 1.0 before soft limiting, then target -1.0 dBFS.
    let pre_scale = if max_abs > 0.95 { 0.95 / max_abs } else { 1.0 };
    let soft_limit = |v: f64| -> f64 {
        let a = v.abs();
        if a <= 0.85 {
            v
        } else {
            let excess = (a - 0.85) / 0.15;
            v.signum() * (0.85 + 0.14 * excess.tanh())
        }
    };

    let mut post_max = 0.0_f64;
    for pair in &mut mix {
        pair.0 = soft_limit(pair.0 * pre_scale);
        pair.1 = soft_limit(pair.1 * pre_scale);
        post_max = post_max.max(pair.0.abs()).max(pair.1.abs());
    }

    let target_peak = 10.0_f64.powf(-1.0 / 20.0); // ~0.89125 (-1.0 dBFS)
    let norm_gain = if post_max > 1e-9 {
        target_peak / post_max
    } else {
        1.0
    };

    let mut sum_sq_l = 0.0_f64;
    let mut sum_sq_r = 0.0_f64;
    let mut final_peak = 0.0_f64;
    let mut clipped_samples = 0usize;
    let mut out = Vec::with_capacity(n);

    for (l, r) in mix {
        let fl = l * norm_gain;
        let fr = r * norm_gain;
        if fl.abs() >= 1.0 || fr.abs() >= 1.0 {
            clipped_samples += 1;
        }
        final_peak = final_peak.max(fl.abs()).max(fr.abs());
        sum_sq_l += fl * fl;
        sum_sq_r += fr * fr;
        out.push((fl as f32, fr as f32));
    }

    let rms_l = (sum_sq_l / n.max(1) as f64).sqrt();
    let rms_r = (sum_sq_r / n.max(1) as f64).sqrt();
    let to_db = |v: f64| if v > 1e-12 { 20.0 * v.log10() } else { -120.0 };

    let stats = AudioStats {
        peak_db: to_db(final_peak),
        rms_l_db: to_db(rms_l),
        rms_r_db: to_db(rms_r),
        clipped_samples,
        nan_count: 0,
    };

    (out, stats)
}
