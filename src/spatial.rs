//! Physical 3D concert stage spatialization (ITD, head-shadow ILD, air absorption, and depth reverb send).

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

/// Applies acoustic distance attenuation, air absorption, Woodworth ITD, and far-ear head shadow.
/// Returns `(direct_stereo, reverb_send_stereo)`.
pub fn spatialize_track(
    input: &[(f32, f32)],
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

    let mut direct = Vec::with_capacity(input.len());
    let mut send = Vec::with_capacity(input.len());

    for &(l_in, r_in) in input {
        // Point-source mono core with very subtle stereo preservation
        let mono = 0.5 * (l_in as f64 + r_in as f64);
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
        let far_sig = far_lp * far_gain;
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
