//! Physical 3D concert stage spatialization (ITD, head-shadow ILD, air absorption,
//! ensemble stereo width spread, and depth reverb send).

use std::f64::consts::PI;

/// Physical stage coordinates in meters (listener at (0, 0) facing +y).
/// `x` spans left (-6m) to right (+6m); `y` spans front (2m) to rear (14m).
#[derive(Clone, Copy, Debug)]
pub struct StagePos {
    pub x: f64,
    pub y: f64,
}

impl StagePos {
    pub const fn new(x: f64, y: f64) -> Self {
        Self { x, y }
    }
}

fn spatialize_mono_source(
    mono_in: &[f64],
    pos: StagePos,
    sample_rate: usize,
) -> (Vec<(f32, f32)>, Vec<(f32, f32)>) {
    let sr = sample_rate as f64;
    let dist = (pos.x * pos.x + pos.y * pos.y).sqrt().max(1.5);
    let theta = pos.x.atan2(pos.y.max(0.5)); // radians, negative = left, positive = right
    let abs_sin = theta.sin().abs();

    // 1. Air absorption 1-pole low-pass proportional to distance
    let fc_air = (19500.0 - 900.0 * (dist - 2.0).max(0.0)).clamp(4800.0, 19000.0);
    let air_alpha = (-2.0 * PI * fc_air / sr).exp();
    let mut air_state = 0.0_f64;

    // 2. Woodworth spherical-head ITD (a = 8.75 cm, c = 343 m/s)
    let itd_s = (0.0875 / 343.0) * (theta.sin() + theta);
    let delay_samples = (itd_s.abs() * sr).min(48.0);
    let delay_left = theta > 0.0; // source on right -> left ear is far

    // 3. Head-shadow ILD & gentle low-pass on far ear
    let far_gain = 1.0 - 0.30 * abs_sin;
    let fc_head = (14500.0 - 8500.0 * abs_sin).clamp(4500.0, 14500.0);
    let head_alpha = (-2.0 * PI * fc_head / sr).exp();
    let mut head_state = 0.0_f64;

    // 4. Distance-based direct vs hall reverb balance
    let direct_gain = (3.8 / dist).powf(0.42).clamp(0.58, 1.12);
    let rev_send_gain = (0.13 + 0.024 * dist).clamp(0.15, 0.42);

    const BUF_LEN: usize = 64;
    let mut far_buf = [0.0_f64; BUF_LEN];
    let mut write_idx = 0usize;

    let mut direct = Vec::with_capacity(mono_in.len());
    let mut send = Vec::with_capacity(mono_in.len());

    for &mono in mono_in {
        let air = (1.0 - air_alpha) * mono + air_alpha * air_state;
        air_state = air;

        far_buf[write_idx] = air;
        let read_pos = write_idx as f64 - delay_samples;
        let i0_f = read_pos.floor();
        let frac = read_pos - i0_f;
        let i0 = (i0_f as isize).rem_euclid(BUF_LEN as isize) as usize;
        let i1 = (i0 + 1) & (BUF_LEN - 1);
        let delayed = (1.0 - frac) * far_buf[i0] + frac * far_buf[i1];
        write_idx = (write_idx + 1) & (BUF_LEN - 1);

        let far_lp = (1.0 - head_alpha) * delayed + head_alpha * head_state;
        head_state = far_lp;
        let shadowed = delayed + abs_sin * (far_lp - delayed);
        let far_sig = shadowed * far_gain;
        let near_sig = air;

        let (dl, dr) = if delay_left {
            (far_sig * direct_gain, near_sig * direct_gain)
        } else {
            (near_sig * direct_gain, far_sig * direct_gain)
        };

        direct.push((dl as f32, dr as f32));
        send.push(((dl * rev_send_gain) as f32, (dr * rev_send_gain) as f32));
    }

    (direct, send)
}

/// Applies point-source acoustic distance attenuation, air absorption, Woodworth ITD, and far-ear head shadow.
/// Returns `(direct_stereo, reverb_send_stereo)`.
pub fn spatialize_track(
    input: &[(f32, f32)],
    pos: StagePos,
    sample_rate: usize,
) -> (Vec<(f32, f32)>, Vec<(f32, f32)>) {
    spatialize_track_with_width(input, pos, 0.0, sample_rate)
}

/// Spatializes a track with optional physical stage width `width_m` (in meters).
/// - `width_m <= 0.05`: exact point-source model for soloists (`0.5 * (L + R)` at `pos`).
/// - `width_m > 0.05`: projects left & right ensemble wings from `(pos.x - width/2, pos.y)` and
///   `(pos.x + width/2, pos.y)` with subtle all-pass phase dispersion so string sections, pianos,
///   and pipe organs span a realistic 3D stereo arc across the concert stage.
pub fn spatialize_track_with_width(
    input: &[(f32, f32)],
    pos: StagePos,
    width_m: f64,
    sample_rate: usize,
) -> (Vec<(f32, f32)>, Vec<(f32, f32)>) {
    if !width_m.is_finite() || width_m <= 0.05 {
        let mono: Vec<f64> = input
            .iter()
            .map(|&(l, r)| 0.5 * (l as f64 + r as f64))
            .collect();
        return spatialize_mono_source(&mono, pos, sample_rate);
    }

    let half_w = 0.5 * width_m.clamp(0.0, 10.0);
    let pos_l = StagePos::new((pos.x - half_w).clamp(-6.5, 6.5), pos.y);
    let pos_r = StagePos::new((pos.x + half_w).clamp(-6.5, 6.5), pos.y);

    // Subtle 1st-order all-pass dispersion on the right wing (~320 Hz corner) so even centered
    // ensemble voices acquire natural spatial breadth with flat magnitude response.
    let sr = sample_rate as f64;
    let tan_w = (PI * 320.0 / sr).tan();
    let ap_coeff = (tan_w - 1.0) / (tan_w + 1.0);
    let mut ap_x1 = 0.0_f64;
    let mut ap_y1 = 0.0_f64;

    let mut left_wing = Vec::with_capacity(input.len());
    let mut right_wing = Vec::with_capacity(input.len());
    for &(l, r) in input {
        let lf = l as f64 * 0.52;
        let rf_raw = r as f64 * 0.52;
        let rf = ap_coeff * rf_raw + ap_x1 - ap_coeff * ap_y1;
        ap_x1 = rf_raw;
        ap_y1 = rf;
        left_wing.push(lf);
        right_wing.push(rf);
    }

    let (mut dir_l, mut snd_l) = spatialize_mono_source(&left_wing, pos_l, sample_rate);
    let (dir_r, snd_r) = spatialize_mono_source(&right_wing, pos_r, sample_rate);

    for i in 0..input.len() {
        dir_l[i].0 += dir_r[i].0;
        dir_l[i].1 += dir_r[i].1;
        snd_l[i].0 += snd_r[i].0;
        snd_l[i].1 += snd_r[i].1;
    }

    (dir_l, snd_l)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_wide_stage_section_creates_binaural_decorrelation() {
        let sr = 48_000usize;
        let input: Vec<(f32, f32)> = (0..4800)
            .map(|i| {
                let t = i as f64 / sr as f64;
                let l = (2.0 * PI * 264.0 * t).sin() as f32 * 0.5;
                let r = (2.0 * PI * 396.0 * t).sin() as f32 * 0.5;
                (l, r)
            })
            .collect();

        let center = StagePos::new(0.0, 6.0);
        let (pt_dir, _) = spatialize_track(&input, center, sr);
        // At x = 0, width = 0, L and R ears receive identical signal
        let pt_diff: f64 = pt_dir
            .iter()
            .map(|&(l, r)| (l as f64 - r as f64).abs())
            .sum();
        assert!(pt_diff < 1e-5, "Point source at x=0 should have identical L/R");

        // With width = 4.6m, L and R wings project from (-2.3, 6.0) and (+2.3, 6.0)
        let (wide_dir, _) = spatialize_track_with_width(&input, center, 4.6, sr);
        let wide_diff: f64 = wide_dir
            .iter()
            .map(|&(l, r)| (l as f64 - r as f64).abs())
            .sum::<f64>()
            / wide_dir.len() as f64;
        assert!(
            wide_diff > 0.02,
            "Wide ensemble section should produce clear L/R stereo spread (got {wide_diff})"
        );
    }
}
