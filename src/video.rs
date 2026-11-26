//! Pure-Rust animated YouTube WebM video renderer (1920x1080 VP9 + Opus via ffmpeg pipe).
//!
//! Renders a luminous midnight-indigo concert-hall visualization featuring:
//! - Live 2D Concert Stage Map with additive radial glows, expanding onset ripples, and Pipe Organ crown
//! - Live 53-EDO / 12-TET Harmonic Mandala Wheel with glowing pitch-class orbs and chord geometry
//! - Anti-aliased vector-stroke typography (capsule-segment SDF rasterization) & live level meters
//! - Smooth timeline progress bar with trailing contemplative silence dimming

use std::f64::consts::PI;
use std::fs::{self, File};
use std::io::{BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::thread;
use std::time::Instant;

use crate::score::{TempoMap, TempoSegment};
use crate::score_json::{
    resolve_stage_params, resolve_track_placement, JsonScore, ScoreInstrument, StageConfig,
    TuningMode,
};
use crate::tuning::{edo53_to_12tet_midi, OCT};

#[derive(Clone, Debug)]
pub struct VideoOptions {
    pub width: usize,
    pub height: usize,
    pub fps: u32,
    pub stage: Option<StageConfig>,
    pub tuning: TuningMode,
}

impl Default for VideoOptions {
    fn default() -> Self {
        Self {
            width: 1920,
            height: 1080,
            fps: 24,
            stage: None,
            tuning: TuningMode::Edo53,
        }
    }
}

#[derive(Clone, Debug)]
pub struct VideoRenderStats {
    pub output_path: PathBuf,
    pub width: usize,
    pub height: usize,
    pub fps: u32,
    pub total_frames: usize,
    pub duration_seconds: f64,
    pub elapsed_seconds: f64,
}

#[derive(Clone, Copy, Debug)]
struct Rgb(f32, f32, f32);

impl Rgb {
    const fn from_u8(r: u8, g: u8, b: u8) -> Self {
        Self(r as f32, g as f32, b as f32)
    }

    #[inline]
    fn lerp(self, other: Self, t: f32) -> Self {
        let u = t.clamp(0.0, 1.0);
        Self(
            self.0 + (other.0 - self.0) * u,
            self.1 + (other.1 - self.1) * u,
            self.2 + (other.2 - self.2) * u,
        )
    }
}

fn family_color(inst: &str) -> Rgb {
    match ScoreInstrument::parse(inst) {
        Ok(ScoreInstrument::Ektara | ScoreInstrument::Dotara) => Rgb::from_u8(240, 118, 178),
        Ok(ScoreInstrument::Sf2(sf2)) => match sf2.family() {
            "Keys & Plucked" => Rgb::from_u8(248, 202, 78),
            "Strings" => Rgb::from_u8(106, 178, 255),
            "Woodwinds" | "Woodwinds & World" => Rgb::from_u8(72, 224, 158),
            "Brass" => Rgb::from_u8(245, 148, 72),
            "Indian Classical" => Rgb::from_u8(240, 118, 178),
            "Organ" => Rgb::from_u8(178, 132, 255),
            _ => Rgb::from_u8(160, 180, 220),
        },
        Err(_) => Rgb::from_u8(160, 180, 220),
    }
}

/// Fast RGB24 software rasterizer with alpha-blending, additive lighting, and capsule SDF strokes.
struct Canvas<'a> {
    w: usize,
    h: usize,
    buf: &'a mut [u8],
}

impl<'a> Canvas<'a> {
    fn new(w: usize, h: usize, buf: &'a mut [u8]) -> Self {
        debug_assert_eq!(buf.len(), w * h * 3);
        Self { w, h, buf }
    }

    #[inline]
    fn blend_px(&mut self, x: usize, y: usize, col: Rgb, alpha: f32) {
        if alpha <= 0.001 || x >= self.w || y >= self.h {
            return;
        }
        let a = alpha.min(1.0);
        let inv = 1.0 - a;
        let idx = (y * self.w + x) * 3;
        self.buf[idx] = (self.buf[idx] as f32 * inv + col.0 * a).min(255.0) as u8;
        self.buf[idx + 1] = (self.buf[idx + 1] as f32 * inv + col.1 * a).min(255.0) as u8;
        self.buf[idx + 2] = (self.buf[idx + 2] as f32 * inv + col.2 * a).min(255.0) as u8;
    }

    #[inline]
    fn add_px(&mut self, x: usize, y: usize, col: Rgb, intensity: f32) {
        if intensity <= 0.001 || x >= self.w || y >= self.h {
            return;
        }
        let idx = (y * self.w + x) * 3;
        let r = self.buf[idx] as f32 + col.0 * intensity;
        let g = self.buf[idx + 1] as f32 + col.1 * intensity;
        let b = self.buf[idx + 2] as f32 + col.2 * intensity;
        self.buf[idx] = r.min(255.0) as u8;
        self.buf[idx + 1] = g.min(255.0) as u8;
        self.buf[idx + 2] = b.min(255.0) as u8;
    }

    fn fill_rounded_rect(
        &mut self,
        x0: f32,
        y0: f32,
        x1: f32,
        y1: f32,
        radius: f32,
        fill: Rgb,
        alpha: f32,
        border: Option<(Rgb, f32, f32)>,
    ) {
        let min_x = (x0 - 2.0).floor().max(0.0) as usize;
        let max_x = (x1 + 2.0).ceil().min((self.w - 1) as f32) as usize;
        let min_y = (y0 - 2.0).floor().max(0.0) as usize;
        let max_y = (y1 + 2.0).ceil().min((self.h - 1) as f32) as usize;

        let cx = 0.5 * (x0 + x1);
        let cy = 0.5 * (y0 + y1);
        let hx = (0.5 * (x1 - x0) - radius).max(0.0);
        let hy = (0.5 * (y1 - y0) - radius).max(0.0);

        for y in min_y..=max_y {
            let py = y as f32 + 0.5;
            let qy = (py - cy).abs() - hy;
            let qy_pos = qy.max(0.0);
            for x in min_x..=max_x {
                let px = x as f32 + 0.5;
                let qx = (px - cx).abs() - hx;
                let qx_pos = qx.max(0.0);
                let dist = (qx_pos * qx_pos + qy_pos * qy_pos).sqrt()
                    + qx.max(qy).min(0.0)
                    - radius;

                if dist < 1.2 {
                    let cov = (0.5 - dist).clamp(0.0, 1.0);
                    if cov > 0.0 {
                        self.blend_px(x, y, fill, alpha * cov);
                    }
                    if let Some((bcol, b_alpha, b_thick)) = border {
                        let bd = (dist.abs() - 0.5 * b_thick).max(0.0);
                        let bcov = (1.0 - bd).clamp(0.0, 1.0);
                        if bcov > 0.0 {
                            self.blend_px(x, y, bcol, b_alpha * bcov);
                        }
                    }
                }
            }
        }
    }

    fn fill_circle_aa(&mut self, cx: f32, cy: f32, r: f32, col: Rgb, alpha: f32) {
        let min_x = (cx - r - 1.5).floor().max(0.0) as usize;
        let max_x = (cx + r + 1.5).ceil().min((self.w - 1) as f32) as usize;
        let min_y = (cy - r - 1.5).floor().max(0.0) as usize;
        let max_y = (cy + r + 1.5).ceil().min((self.h - 1) as f32) as usize;
        let r_max2 = (r + 1.5) * (r + 1.5);
        for y in min_y..=max_y {
            let dy = y as f32 + 0.5 - cy;
            let dy2 = dy * dy;
            for x in min_x..=max_x {
                let dx = x as f32 + 0.5 - cx;
                let d2 = dx * dx + dy2;
                if d2 <= r_max2 {
                    let d = d2.sqrt();
                    let cov = (r + 0.6 - d).clamp(0.0, 1.0);
                    self.blend_px(x, y, col, alpha * cov);
                }
            }
        }
    }

    fn add_radial_glow(
        &mut self,
        cx: f32,
        cy: f32,
        r: f32,
        col: Rgb,
        intensity: f32,
        clip: Option<(usize, usize, usize, usize)>,
    ) {
        if r <= 1.0 || intensity <= 0.002 {
            return;
        }
        let (cx0, cy0, cx1, cy1) = clip.unwrap_or((0, 0, self.w - 1, self.h - 1));
        let min_x = (cx - r).floor().max(cx0 as f32) as usize;
        let max_x = (cx + r).ceil().min(cx1 as f32) as usize;
        let min_y = (cy - r).floor().max(cy0 as f32) as usize;
        let max_y = (cy + r).ceil().min(cy1 as f32) as usize;
        if min_x > max_x || min_y > max_y {
            return;
        }
        let inv_r2 = 1.0 / (r * r);
        for y in min_y..=max_y {
            let dy = y as f32 + 0.5 - cy;
            let dy2 = dy * dy;
            let row_base = y * self.w;
            for x in min_x..=max_x {
                let dx = x as f32 + 0.5 - cx;
                let u2 = (dx * dx + dy2) * inv_r2;
                if u2 < 1.0 {
                    let fall = 1.0 - u2;
                    let w = fall * fall * fall * intensity;
                    if w > 0.002 {
                        let idx = (row_base + x) * 3;
                        self.buf[idx] = (self.buf[idx] as f32 + col.0 * w).min(255.0) as u8;
                        self.buf[idx + 1] = (self.buf[idx + 1] as f32 + col.1 * w).min(255.0) as u8;
                        self.buf[idx + 2] = (self.buf[idx + 2] as f32 + col.2 * w).min(255.0) as u8;
                    }
                }
            }
        }
    }

    fn stroke_circle_aa(
        &mut self,
        cx: f32,
        cy: f32,
        r: f32,
        thickness: f32,
        col: Rgb,
        alpha: f32,
        additive: bool,
        clip: Option<(usize, usize, usize, usize)>,
    ) {
        if r <= 0.5 || alpha <= 0.002 {
            return;
        }
        let half_t = 0.5 * thickness;
        let outer = r + half_t + 1.2;
        let inner = (r - half_t - 1.2).max(0.0);
        let outer2 = outer * outer;
        let inner2 = inner * inner;
        let (cx0, cy0, cx1, cy1) = clip.unwrap_or((0, 0, self.w - 1, self.h - 1));
        let min_x = (cx - outer).floor().max(cx0 as f32) as usize;
        let max_x = (cx + outer).ceil().min(cx1 as f32) as usize;
        let min_y = (cy - outer).floor().max(cy0 as f32) as usize;
        let max_y = (cy + outer).ceil().min(cy1 as f32) as usize;
        if min_x > max_x || min_y > max_y {
            return;
        }

        for y in min_y..=max_y {
            let dy = y as f32 + 0.5 - cy;
            let dy2 = dy * dy;
            for x in min_x..=max_x {
                let dx = x as f32 + 0.5 - cx;
                let d2 = dx * dx + dy2;
                if d2 <= outer2 && d2 >= inner2 {
                    let d = (d2.sqrt() - r).abs();
                    let cov = (half_t + 0.85 - d).clamp(0.0, 1.0);
                    if cov > 0.0 {
                        if additive {
                            self.add_px(x, y, col, alpha * cov);
                        } else {
                            self.blend_px(x, y, col, alpha * cov);
                        }
                    }
                }
            }
        }
    }

    /// Anti-aliased capsule-segment stroke (signed distance to segment).
    fn draw_capsule_aa(
        &mut self,
        x0: f32,
        y0: f32,
        x1: f32,
        y1: f32,
        radius: f32,
        col: Rgb,
        alpha: f32,
        additive: bool,
        clip: Option<(usize, usize, usize, usize)>,
    ) {
        if alpha <= 0.002 {
            return;
        }
        let pad = radius + 1.2;
        let (cx0, cy0, cx1, cy1) = clip.unwrap_or((0, 0, self.w - 1, self.h - 1));
        let min_x = x0.min(x1).sub_pad(pad).max(cx0 as f32) as usize;
        let max_x = (x0.max(x1) + pad).ceil().min(cx1 as f32) as usize;
        let min_y = y0.min(y1).sub_pad(pad).max(cy0 as f32) as usize;
        let max_y = (y0.max(y1) + pad).ceil().min(cy1 as f32) as usize;
        if min_x > max_x || min_y > max_y {
            return;
        }

        let vx = x1 - x0;
        let vy = y1 - y0;
        let len2 = vx * vx + vy * vy;
        let inv_len2 = if len2 > 1e-6 { 1.0 / len2 } else { 0.0 };
        let r_outer = radius + 0.85;
        let r_outer2 = r_outer * r_outer;

        for y in min_y..=max_y {
            let py = y as f32 + 0.5 - y0;
            for x in min_x..=max_x {
                let px = x as f32 + 0.5 - x0;
                let t = if len2 > 1e-6 {
                    ((px * vx + py * vy) * inv_len2).clamp(0.0, 1.0)
                } else {
                    0.0
                };
                let dx = px - vx * t;
                let dy = py - vy * t;
                let d2 = dx * dx + dy * dy;
                if d2 < r_outer2 {
                    let d = d2.sqrt();
                    let cov = ((r_outer - d) / 1.15).clamp(0.0, 1.0);
                    if cov > 0.0 {
                        if additive {
                            self.add_px(x, y, col, alpha * cov);
                        } else {
                            self.blend_px(x, y, col, alpha * cov);
                        }
                    }
                }
            }
        }
    }

    fn draw_text_vector(
        &mut self,
        text: &str,
        x: f32,
        y: f32,
        height: f32,
        stroke_radius: f32,
        col: Rgb,
        alpha: f32,
        align: TextAlign,
    ) {
        let total_w = measure_vector_text(text, height);
        let mut cursor_x = match align {
            TextAlign::Left => x,
            TextAlign::Center => x - 0.5 * total_w,
            TextAlign::Right => x - total_w,
        };
        let tracking = height * 0.16;

        for ch in text.chars() {
            let upper = ch.to_ascii_uppercase();
            let (gw, strokes) = glyph_strokes(upper);
            for poly in strokes {
                if poly.len() == 1 {
                    let px = cursor_x + poly[0].0 * height;
                    let py = y + poly[0].1 * height;
                    self.fill_circle_aa(px, py, stroke_radius * 1.15, col, alpha);
                } else {
                    for seg in poly.windows(2) {
                        let x0 = cursor_x + seg[0].0 * height;
                        let y0 = y + seg[0].1 * height;
                        let x1 = cursor_x + seg[1].0 * height;
                        let y1 = y + seg[1].1 * height;
                        self.draw_capsule_aa(
                            x0,
                            y0,
                            x1,
                            y1,
                            stroke_radius,
                            col,
                            alpha,
                            false,
                            None,
                        );
                    }
                }
            }
            cursor_x += gw * height + tracking;
        }
    }
}

trait SubPad {
    fn sub_pad(self, pad: f32) -> f32;
}
impl SubPad for f32 {
    #[inline]
    fn sub_pad(self, pad: f32) -> f32 {
        (self - pad).floor().max(0.0)
    }
}

#[derive(Clone, Copy)]
enum TextAlign {
    Left,
    Center,
    Right,
}

fn measure_vector_text(text: &str, height: f32) -> f32 {
    let tracking = height * 0.16;
    let mut w = 0.0_f32;
    let mut count = 0usize;
    for ch in text.chars() {
        let (gw, _) = glyph_strokes(ch.to_ascii_uppercase());
        w += gw * height;
        count += 1;
    }
    if count > 1 {
        w += tracking * (count - 1) as f32;
    }
    w
}

/// Clean geometric proportional vector stroke font (smooth multi-segment curves, zero jagged pixels).
fn glyph_strokes(ch: char) -> (f32, &'static [&'static [(f32, f32)]]) {
    match ch {
        'A' => (0.64, &[&[(0.02, 1.0), (0.32, 0.0), (0.62, 1.0)], &[(0.13, 0.66), (0.51, 0.66)]]),
        'B' => (0.60, &[
            &[(0.06, 1.0), (0.06, 0.0), (0.38, 0.0), (0.50, 0.06), (0.54, 0.20), (0.50, 0.36), (0.38, 0.46), (0.06, 0.46)],
            &[(0.38, 0.46), (0.53, 0.54), (0.57, 0.72), (0.53, 0.90), (0.38, 1.0), (0.06, 1.0)],
        ]),
        'C' => (0.60, &[&[(0.55, 0.18), (0.44, 0.04), (0.28, 0.0), (0.14, 0.08), (0.05, 0.28), (0.05, 0.72), (0.14, 0.92), (0.28, 1.0), (0.44, 0.96), (0.55, 0.82)]]),
        'D' => (0.62, &[&[(0.06, 1.0), (0.06, 0.0), (0.32, 0.0), (0.48, 0.08), (0.57, 0.28), (0.57, 0.72), (0.48, 0.92), (0.32, 1.0), (0.06, 1.0)]]),
        'E' => (0.54, &[&[(0.50, 0.0), (0.06, 0.0), (0.06, 1.0), (0.50, 1.0)], &[(0.06, 0.48), (0.43, 0.48)]]),
        'F' => (0.52, &[&[(0.48, 0.0), (0.06, 0.0), (0.06, 1.0)], &[(0.06, 0.48), (0.42, 0.48)]]),
        'G' => (0.64, &[&[(0.57, 0.18), (0.46, 0.04), (0.30, 0.0), (0.14, 0.08), (0.05, 0.28), (0.05, 0.72), (0.14, 0.92), (0.30, 1.0), (0.48, 0.94), (0.57, 0.78), (0.57, 0.54), (0.34, 0.54)]]),
        'H' => (0.60, &[&[(0.06, 0.0), (0.06, 1.0)], &[(0.54, 0.0), (0.54, 1.0)], &[(0.06, 0.48), (0.54, 0.48)]]),
        'I' => (0.24, &[&[(0.12, 0.0), (0.12, 1.0)]]),
        'J' => (0.50, &[&[(0.42, 0.0), (0.42, 0.72), (0.36, 0.92), (0.22, 1.0), (0.10, 0.94), (0.04, 0.80)]]),
        'K' => (0.58, &[&[(0.06, 0.0), (0.06, 1.0)], &[(0.54, 0.0), (0.08, 0.54)], &[(0.22, 0.38), (0.55, 1.0)]]),
        'L' => (0.50, &[&[(0.06, 0.0), (0.06, 1.0), (0.48, 1.0)]]),
        'M' => (0.74, &[&[(0.06, 1.0), (0.06, 0.0), (0.37, 0.64), (0.68, 0.0), (0.68, 1.0)]]),
        'N' => (0.62, &[&[(0.06, 1.0), (0.06, 0.0), (0.56, 1.0), (0.56, 0.0)]]),
        'O' => (0.66, &[&[(0.33, 0.0), (0.16, 0.07), (0.06, 0.26), (0.06, 0.74), (0.16, 0.93), (0.33, 1.0), (0.50, 0.93), (0.60, 0.74), (0.60, 0.26), (0.50, 0.07), (0.33, 0.0)]]),
        'P' => (0.58, &[&[(0.06, 1.0), (0.06, 0.0), (0.36, 0.0), (0.50, 0.08), (0.54, 0.26), (0.50, 0.44), (0.36, 0.52), (0.06, 0.52)]]),
        'Q' => (0.66, &[
            &[(0.33, 0.0), (0.16, 0.07), (0.06, 0.26), (0.06, 0.74), (0.16, 0.93), (0.33, 1.0), (0.50, 0.93), (0.60, 0.74), (0.60, 0.26), (0.50, 0.07), (0.33, 0.0)],
            &[(0.38, 0.72), (0.62, 1.02)],
        ]),
        'R' => (0.60, &[
            &[(0.06, 1.0), (0.06, 0.0), (0.36, 0.0), (0.50, 0.08), (0.54, 0.25), (0.50, 0.43), (0.36, 0.51), (0.06, 0.51)],
            &[(0.34, 0.51), (0.56, 1.0)],
        ]),
        'S' => (0.58, &[&[(0.52, 0.16), (0.42, 0.03), (0.26, 0.0), (0.12, 0.06), (0.06, 0.20), (0.12, 0.36), (0.28, 0.46), (0.44, 0.54), (0.53, 0.68), (0.51, 0.86), (0.38, 0.98), (0.22, 1.0), (0.09, 0.92), (0.04, 0.80)]]),
        'T' => (0.58, &[&[(0.02, 0.0), (0.56, 0.0)], &[(0.29, 0.0), (0.29, 1.0)]]),
        'U' => (0.60, &[&[(0.06, 0.0), (0.06, 0.70), (0.13, 0.90), (0.30, 1.0), (0.47, 0.90), (0.54, 0.70), (0.54, 0.0)]]),
        'V' => (0.62, &[&[(0.03, 0.0), (0.31, 1.0), (0.59, 0.0)]]),
        'W' => (0.82, &[&[(0.03, 0.0), (0.21, 1.0), (0.41, 0.32), (0.61, 1.0), (0.79, 0.0)]]),
        'X' => (0.58, &[&[(0.05, 0.0), (0.53, 1.0)], &[(0.53, 0.0), (0.05, 1.0)]]),
        'Y' => (0.58, &[&[(0.04, 0.0), (0.29, 0.48), (0.54, 0.0)], &[(0.29, 0.48), (0.29, 1.0)]]),
        'Z' => (0.56, &[&[(0.05, 0.0), (0.51, 0.0), (0.05, 1.0), (0.51, 1.0)]]),
        '0' => (0.56, &[
            &[(0.28, 0.0), (0.13, 0.08), (0.06, 0.28), (0.06, 0.72), (0.13, 0.92), (0.28, 1.0), (0.43, 0.92), (0.50, 0.72), (0.50, 0.28), (0.43, 0.08), (0.28, 0.0)],
            &[(0.14, 0.78), (0.42, 0.22)],
        ]),
        '1' => (0.42, &[&[(0.10, 0.20), (0.26, 0.0), (0.26, 1.0)], &[(0.08, 1.0), (0.40, 1.0)]]),
        '2' => (0.54, &[&[(0.07, 0.22), (0.16, 0.05), (0.30, 0.0), (0.44, 0.08), (0.49, 0.24), (0.44, 0.42), (0.06, 1.0), (0.50, 1.0)]]),
        '3' => (0.54, &[&[(0.08, 0.16), (0.18, 0.03), (0.32, 0.0), (0.45, 0.08), (0.49, 0.24), (0.43, 0.40), (0.26, 0.47), (0.44, 0.56), (0.50, 0.74), (0.44, 0.92), (0.30, 1.0), (0.14, 0.96), (0.06, 0.84)]]),
        '4' => (0.56, &[&[(0.42, 1.0), (0.42, 0.0), (0.05, 0.66), (0.53, 0.66)]]),
        '5' => (0.54, &[&[(0.47, 0.0), (0.10, 0.0), (0.08, 0.44), (0.24, 0.38), (0.40, 0.42), (0.50, 0.58), (0.50, 0.78), (0.41, 0.94), (0.26, 1.0), (0.12, 0.95), (0.05, 0.84)]]),
        '6' => (0.54, &[&[(0.46, 0.12), (0.34, 0.0), (0.18, 0.06), (0.08, 0.26), (0.06, 0.64), (0.12, 0.90), (0.28, 1.0), (0.44, 0.92), (0.50, 0.72), (0.44, 0.52), (0.28, 0.45), (0.12, 0.54), (0.07, 0.68)]]),
        '7' => (0.54, &[&[(0.06, 0.0), (0.50, 0.0), (0.20, 1.0)]]),
        '8' => (0.56, &[
            &[(0.28, 0.46), (0.14, 0.38), (0.09, 0.22), (0.16, 0.06), (0.28, 0.0), (0.40, 0.06), (0.47, 0.22), (0.42, 0.38), (0.28, 0.46), (0.12, 0.56), (0.06, 0.74), (0.13, 0.92), (0.28, 1.0), (0.43, 0.92), (0.50, 0.74), (0.44, 0.56), (0.28, 0.46)],
        ]),
        '9' => (0.54, &[&[(0.08, 0.88), (0.20, 1.0), (0.36, 0.94), (0.46, 0.74), (0.48, 0.36), (0.42, 0.10), (0.26, 0.0), (0.10, 0.08), (0.05, 0.28), (0.11, 0.48), (0.26, 0.55), (0.42, 0.46), (0.47, 0.32)]]),
        ':' => (0.20, &[&[(0.10, 0.32)], &[(0.10, 0.76)]]),
        '.' => (0.18, &[&[(0.09, 0.94)]]),
        ',' => (0.20, &[&[(0.11, 0.88), (0.07, 1.08)]]),
        '/' => (0.42, &[&[(0.06, 1.0), (0.36, 0.0)]]),
        '-' | '–' | '—' => (0.42, &[&[(0.06, 0.52), (0.36, 0.52)]]),
        '+' => (0.46, &[&[(0.06, 0.52), (0.40, 0.52)], &[(0.23, 0.30), (0.23, 0.74)]]),
        '(' => (0.28, &[&[(0.22, 0.0), (0.10, 0.24), (0.08, 0.50), (0.10, 0.76), (0.22, 1.0)]]),
        ')' => (0.28, &[&[(0.06, 0.0), (0.18, 0.24), (0.20, 0.50), (0.18, 0.76), (0.06, 1.0)]]),
        '|' | '·' => (0.22, &[&[(0.11, 0.16), (0.11, 0.84)]]),
        '&' => (0.64, &[&[(0.58, 0.96), (0.14, 0.42), (0.14, 0.16), (0.26, 0.02), (0.40, 0.06), (0.44, 0.22), (0.32, 0.42), (0.08, 0.66), (0.10, 0.88), (0.26, 1.0), (0.44, 0.92), (0.58, 0.62)]]),
        ' ' => (0.34, &[]),
        _ => (0.36, &[&[(0.08, 0.52), (0.28, 0.52)]]),
    }
}

fn format_mm_ss(seconds: f64) -> String {
    let total = seconds.floor().max(0.0) as u64;
    let m = total / 60;
    let s = total % 60;
    format!("{m}:{s:02}")
}

fn comma_offset_from_anchor(step: i32) -> f64 {
    const ANCHORS: [i32; 12] = [0, 4, 9, 14, 17, 22, 26, 31, 36, 39, 44, 48];
    let pc = step.rem_euclid(OCT);
    let mut best_diff = 100i32;
    for &a in &ANCHORS {
        let mut diff = pc - a;
        if diff > OCT / 2 {
            diff -= OCT;
        } else if diff < -(OCT / 2) {
            diff += OCT;
        }
        if diff.abs() < best_diff.abs() {
            best_diff = diff;
        }
    }
    best_diff as f64
}

/// Parses exact duration in seconds from a RIFF/WAVE file header.
pub fn read_wav_duration_seconds(path: impl AsRef<Path>) -> Option<f64> {
    let mut f = File::open(path.as_ref()).ok()?;
    let mut header = [0u8; 12];
    f.read_exact(&mut header).ok()?;
    if &header[0..4] != b"RIFF" || &header[8..12] != b"WAVE" {
        return None;
    }

    let mut byte_rate: Option<u32> = None;
    let mut data_bytes: Option<u32> = None;

    loop {
        let mut chunk_hdr = [0u8; 8];
        if f.read_exact(&mut chunk_hdr).is_err() {
            break;
        }
        let id = &chunk_hdr[0..4];
        let size = u32::from_le_bytes([chunk_hdr[4], chunk_hdr[5], chunk_hdr[6], chunk_hdr[7]]);

        if id == b"fmt " && size >= 16 {
            let mut fmt_buf = vec![0u8; size as usize];
            f.read_exact(&mut fmt_buf).ok()?;
            byte_rate = Some(u32::from_le_bytes([
                fmt_buf[8],
                fmt_buf[9],
                fmt_buf[10],
                fmt_buf[11],
            ]));
        } else if id == b"data" {
            data_bytes = Some(size);
            break;
        } else {
            let mut skip = vec![0u8; size as usize];
            if f.read_exact(&mut skip).is_err() {
                break;
            }
        }
        // Pad byte for odd chunk sizes
        if size % 2 == 1 {
            let mut pad = [0u8; 1];
            let _ = f.read_exact(&mut pad);
        }
    }

    let br = byte_rate?;
    let db = data_bytes?;
    if br == 0 {
        return None;
    }
    Some(db as f64 / br as f64)
}

#[derive(Clone, Debug)]
struct TimedNote {
    start_s: f64,
    end_s: f64,
    vel: f32,
    step: i32,
    wheel_pos: f32, // continuous position in [0, 53)
}

#[derive(Clone, Debug)]
struct TrackAnim {
    label: String,
    short_label: String,
    is_organ: bool,
    color: Rgb,
    stage_x: f32,
    stage_y: f32,
    label_y: f32,
    base_radius: f32,
    notes: Vec<TimedNote>,
    max_note_dur: f64,
}

/// Precomputed layout and static background for blazing-fast per-frame animation.
pub struct VideoScene {
    pub width: usize,
    pub height: usize,
    pub total_dur_s: f64,
    pub musical_end_s: f64,
    tuning: TuningMode,
    sc: f32,
    stage_clip: (usize, usize, usize, usize),
    wheel_cx: f32,
    wheel_cy: f32,
    wheel_r: f32,
    now_x0: f32,
    now_y0: f32,
    now_x1: f32,
    now_y1: f32,
    bar_x0: f32,
    bar_x1: f32,
    bar_y: f32,
    bg: Vec<u8>,
    tracks: Vec<TrackAnim>,
}

impl VideoScene {
    pub fn build(
        score: &JsonScore,
        opts: &VideoOptions,
        audio_duration_s: Option<f64>,
    ) -> Result<Self, String> {
        score.validate()?;
        if let Some(st) = &opts.stage {
            st.validate()?;
        }
        let stage_params = resolve_stage_params(score, opts.stage.as_ref(), None)?;
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

        let w = opts.width.max(320);
        let h = opts.height.max(180);
        let sx = w as f32 / 1920.0;
        let sy = h as f32 / 1080.0;
        let sc = sx.min(sy);

        // Stage viewport bounds (Left ~62% panel)
        let st_x0 = (52.0 * sx).round() as usize;
        let st_y0 = (158.0 * sy).round() as usize;
        let st_x1 = (1188.0 * sx).round().min((w - 1) as f32) as usize;
        let st_y1 = (952.0 * sy).round().min((h - 1) as f32) as usize;
        let stage_clip = (st_x0, st_y0, st_x1, st_y1);

        let stage_cx = 620.0 * sx;
        let stage_cy = 918.0 * sy;
        let px_per_m = 61.5 * sc;

        // Harmonic Wheel geometry (Top Right card)
        let wheel_cx = 1560.0 * sx;
        let wheel_cy = 348.0 * sy;
        let wheel_r = 166.0 * sc;

        // Now Playing telemetry bounds (Bottom Right card)
        let now_x0 = 1256.0 * sx;
        let now_y0 = 644.0 * sy;
        let now_x1 = 1864.0 * sx;
        let now_y1 = 954.0 * sy;

        // Bottom Progress Bar geometry
        let bar_x0 = 148.0 * sx;
        let bar_x1 = 1772.0 * sx;
        let bar_y = 1024.0 * sy;

        // Build per-track sorted timed notes
        let mut max_note_end_s = 0.0_f64;
        let mut tracks: Vec<TrackAnim> = Vec::with_capacity(score.tracks.len());

        for track in &score.tracks {
            let placement = resolve_track_placement(track, opts.stage.as_ref());
            let mut notes: Vec<TimedNote> = track
                .notes
                .iter()
                .map(|n| {
                    let s0 = tempo.beat_to_seconds(n.beat);
                    let s1 = tempo.beat_to_seconds(n.beat + n.dur).max(s0 + 0.05);
                    max_note_end_s = max_note_end_s.max(s1);
                    let wheel_pos = match opts.tuning {
                        TuningMode::Edo53 => n.step.rem_euclid(OCT) as f32,
                        TuningMode::Tet12 => {
                            let midi = edo53_to_12tet_midi(n.step, n.cents as f64);
                            ((midi - 60).rem_euclid(12) as f32) * (OCT as f32 / 12.0)
                        }
                    };
                    TimedNote {
                        start_s: s0,
                        end_s: s1,
                        vel: n.vel.clamp(0.05, 1.0),
                        step: n.step,
                        wheel_pos,
                    }
                })
                .collect();
            notes.sort_by(|a, b| a.start_s.total_cmp(&b.start_s));
            let max_note_dur = notes
                .iter()
                .map(|n| n.end_s - n.start_s)
                .fold(0.5_f64, f64::max);

            let stage_x = (stage_cx + placement.x as f32 * px_per_m)
                .clamp(st_x0 as f32 + 56.0 * sc, st_x1 as f32 - 56.0 * sc);
            let stage_y = (stage_cy - placement.y as f32 * px_per_m)
                .clamp(st_y0 as f32 + 46.0 * sc, st_y1 as f32 - 54.0 * sc);
            let base_radius = (10.5 * sc * (0.85 + 0.25 * placement.gain as f32).clamp(0.85, 1.25))
                .max(6.0);

            let raw_name = track.display_name().to_string();
            let panel_label = clean_panel_label(&raw_name, 26);
            let short_label = concise_stage_label(&raw_name, &track.instrument);

            tracks.push(TrackAnim {
                label: panel_label,
                short_label,
                is_organ: track.instrument == "church_organ",
                color: family_color(&track.instrument),
                stage_x,
                stage_y,
                label_y: stage_y + base_radius + 11.0 * sc,
                base_radius,
                notes,
                max_note_dur,
            });
        }

        // Compute non-colliding positions for depth-arc labels (3M, 6M, 9M, 12M)
        let mut arc_labels: Vec<(f32, f32, String, TextAlign)> = Vec::new();
        let mut placed_boxes: Vec<(f32, f32, f32, f32)> = Vec::with_capacity(tracks.len() + 4);
        let arc_lbl_h = 10.0 * sc;
        for &dist_m in &[3.0_f32, 6.0, 9.0, 12.0] {
            let r = dist_m * px_per_m;
            let lbl_y = stage_cy - r + 10.0 * sc;
            if lbl_y <= st_y0 as f32 + 12.0 * sc {
                continue;
            }
            let text = format!("{}M", dist_m as i32);
            let tw = measure_vector_text(&text, arc_lbl_h) + 6.0 * sc;
            // Pick whichever side of the center azimuth ray is farther from any player orb
            let cand_left = (stage_cx - 10.0 * sc, TextAlign::Right, stage_cx - 10.0 * sc - tw, stage_cx - 10.0 * sc);
            let cand_right = (stage_cx + 10.0 * sc, TextAlign::Left, stage_cx + 10.0 * sc, stage_cx + 10.0 * sc + tw);
            let min_dist_to_orb = |bx0: f32, bx1: f32| -> f32 {
                let bcx = 0.5 * (bx0 + bx1);
                let bcy = lbl_y + 0.5 * arc_lbl_h;
                tracks
                    .iter()
                    .map(|t| ((t.stage_x - bcx).hypot(t.stage_y - bcy)) - t.base_radius)
                    .fold(f32::INFINITY, f32::min)
            };
            let chosen = if min_dist_to_orb(cand_left.2, cand_left.3)
                >= min_dist_to_orb(cand_right.2, cand_right.3)
            {
                cand_left
            } else {
                cand_right
            };
            arc_labels.push((chosen.0, lbl_y, text, chosen.1));
            placed_boxes.push((
                chosen.2 - 4.0 * sc,
                lbl_y - 4.0 * sc,
                chosen.3 + 4.0 * sc,
                lbl_y + arc_lbl_h + 4.0 * sc,
            ));
        }

        // Smart label de-overlap on stage map: avoid overlapping other orbs, arc labels, or player labels
        let lbl_h = 10.5 * sc;
        for i in 0..tracks.len() {
            let half_w = 0.5 * measure_vector_text(&tracks[i].short_label, lbl_h) + 7.0 * sc;
            let sx_i = tracks[i].stage_x;
            let sy_i = tracks[i].stage_y;
            let r_i = tracks[i].base_radius;
            let candidates = [
                sy_i + r_i + 12.0 * sc,
                sy_i - r_i - 22.0 * sc,
                sy_i + r_i + 25.0 * sc,
                sy_i - r_i - 35.0 * sc,
            ];
            let mut best_y = candidates[0];
            let mut best_score = i32::MAX;
            for &cy_cand in &candidates {
                if cy_cand < st_y0 as f32 + 10.0 * sc || cy_cand + lbl_h > st_y1 as f32 - 14.0 * sc {
                    continue;
                }
                let bx0 = sx_i - half_w;
                let bx1 = sx_i + half_w;
                let by0 = cy_cand - 4.0 * sc;
                let by1 = cy_cand + lbl_h + 4.0 * sc;
                let mut penalty = 0i32;
                for (j, other) in tracks.iter().enumerate() {
                    if j == i {
                        continue;
                    }
                    let pad = other.base_radius + 9.0 * sc;
                    if other.stage_x + pad > bx0
                        && other.stage_x - pad < bx1
                        && other.stage_y + pad > by0
                        && other.stage_y - pad < by1
                    {
                        penalty += 10;
                    }
                }
                for &(px0, py0, px1, py1) in &placed_boxes {
                    if px1 > bx0 && px0 < bx1 && py1 > by0 && py0 < by1 {
                        penalty += 10;
                    }
                }
                if penalty < best_score {
                    best_score = penalty;
                    best_y = cy_cand;
                    if penalty == 0 {
                        break;
                    }
                }
            }
            tracks[i].label_y = best_y;
            placed_boxes.push((
                sx_i - half_w,
                best_y - 4.0 * sc,
                sx_i + half_w,
                best_y + lbl_h + 4.0 * sc,
            ));
        }

        let musical_end_s = (max_note_end_s + stage_params.tail_seconds).max(1.0);
        let fallback_dur = musical_end_s + stage_params.end_silence_seconds;
        let total_dur_s = audio_duration_s.unwrap_or(fallback_dur).max(1.0);

        // Pre-render static background ONCE
        let mut bg = vec![0u8; w * h * 3];
        render_static_background(
            &mut bg,
            w,
            h,
            sx,
            sy,
            sc,
            score,
            stage_params.stage_name.as_deref(),
            opts.tuning,
            stage_cx,
            stage_cy,
            px_per_m,
            stage_clip,
            &arc_labels,
            wheel_cx,
            wheel_cy,
            wheel_r,
            bar_x0,
            bar_x1,
            bar_y,
            musical_end_s,
            total_dur_s,
        );

        Ok(Self {
            width: w,
            height: h,
            total_dur_s,
            musical_end_s,
            tuning: opts.tuning,
            sc,
            stage_clip,
            wheel_cx,
            wheel_cy,
            wheel_r,
            now_x0,
            now_y0,
            now_x1,
            now_y1,
            bar_x0,
            bar_x1,
            bar_y,
            bg,
            tracks,
        })
    }

    /// Renders frame at time `t_sec` into `out_rgb` (length `width * height * 3`).
    pub fn render_frame(&self, t_sec: f64, out_rgb: &mut [u8]) {
        out_rgb.copy_from_slice(&self.bg);
        let mut c = Canvas::new(self.width, self.height, out_rgb);
        let sc = self.sc;

        // Smooth contemplative silence dimming once music + reverb tail finish
        let in_silence = self.total_dur_s > self.musical_end_s + 1.0 && t_sec > self.musical_end_s;
        let silence_fade = if in_silence {
            ((t_sec - self.musical_end_s) / 1.8).clamp(0.0, 1.0) as f32
        } else {
            0.0
        };
        let glow_mult = 1.0 - 0.55 * silence_fade;

        // 1. Evaluate per-track live envelopes, recent note ripples, and active pitch classes
        let mut track_energies = vec![0.0_f32; self.tracks.len()];
        struct ActivePitch {
            wheel_pos: f32,
            energy: f32,
            color: Rgb,
            step: i32,
        }
        let mut active_pitches: Vec<ActivePitch> = Vec::with_capacity(32);

        for (ti, tr) in self.tracks.iter().enumerate() {
            let mut energy = 0.0_f32;
            let mut ripple_ages: [f32; 3] = [-1.0; 3];
            let mut ripple_vels: [f32; 3] = [0.0; 3];
            let mut ripple_count = 0usize;
            let mut last_onset = f64::INFINITY;

            let upper = tr.notes.partition_point(|n| n.start_s <= t_sec);
            let lookback = tr.max_note_dur + 1.45;
            for n in tr.notes[..upper].iter().rev() {
                let dt_start = t_sec - n.start_s;
                if dt_start > lookback {
                    break;
                }
                let env = note_envelope(t_sec, n.start_s, n.end_s, n.vel);
                if env > 0.012 {
                    energy = energy.max(env).min(1.20);
                    active_pitches.push(ActivePitch {
                        wheel_pos: n.wheel_pos,
                        energy: env,
                        color: tr.color,
                        step: n.step,
                    });
                }
                if dt_start >= 0.0
                    && dt_start < 1.15
                    && ripple_count < 3
                    && (last_onset - n.start_s) >= 0.14
                {
                    ripple_ages[ripple_count] = (dt_start / 1.15) as f32;
                    ripple_vels[ripple_count] = n.vel;
                    ripple_count += 1;
                    last_onset = n.start_s;
                }
            }

            track_energies[ti] = energy * glow_mult;

            // Draw live stage ripples & multi-layer glow for this musician
            let e = track_energies[ti];
            if tr.is_organ && e > 0.04 {
                // Majestic rear-center Cathedral Pipe Organ crown bloom
                let crown_r = (95.0 + 135.0 * e) * sc;
                c.add_radial_glow(
                    tr.stage_x,
                    tr.stage_y - 12.0 * sc,
                    crown_r,
                    Rgb::from_u8(186, 146, 255),
                    0.34 * e,
                    Some(self.stage_clip),
                );
                c.add_radial_glow(
                    tr.stage_x,
                    tr.stage_y,
                    (58.0 + 68.0 * e) * sc,
                    Rgb::from_u8(250, 212, 130),
                    0.28 * e,
                    Some(self.stage_clip),
                );
                // Delicate golden crown rays above organ
                for ray in -2..=2 {
                    let ang = -PI * 0.5 + ray as f64 * 0.24;
                    let r0 = (tr.base_radius + 10.0 * sc) as f64;
                    let r1 = (tr.base_radius + (30.0 + 48.0 * e) * sc) as f64;
                    c.draw_capsule_aa(
                        tr.stage_x + (ang.cos() * r0) as f32,
                        tr.stage_y + (ang.sin() * r0) as f32,
                        tr.stage_x + (ang.cos() * r1) as f32,
                        tr.stage_y + (ang.sin() * r1) as f32,
                        1.4 * sc,
                        Rgb::from_u8(248, 215, 138),
                        0.45 * e,
                        true,
                        Some(self.stage_clip),
                    );
                }
            }

            // Expanding concentric acoustic ripple rings on note onsets
            for k in 0..ripple_count {
                let age = ripple_ages[k];
                let fade = (1.0 - age).powf(1.65) * ripple_vels[k] * glow_mult;
                if fade > 0.02 {
                    let ring_r = tr.base_radius + (6.0 + 96.0 * age) * sc;
                    c.stroke_circle_aa(
                        tr.stage_x,
                        tr.stage_y,
                        ring_r,
                        (2.2 - 1.0 * age) * sc,
                        tr.color.lerp(Rgb::from_u8(255, 240, 200), 0.3),
                        0.62 * fade,
                        true,
                        Some(self.stage_clip),
                    );
                }
            }

            // Multi-layer additive radial glow bloom
            if e > 0.015 {
                let outer_r = (36.0 + 68.0 * e) * sc;
                c.add_radial_glow(
                    tr.stage_x,
                    tr.stage_y,
                    outer_r,
                    tr.color,
                    0.46 * e,
                    Some(self.stage_clip),
                );
                let inner_r = (16.0 + 24.0 * e) * sc;
                c.add_radial_glow(
                    tr.stage_x,
                    tr.stage_y,
                    inner_r,
                    tr.color.lerp(Rgb::from_u8(255, 248, 224), 0.55),
                    0.55 * e,
                    Some(self.stage_clip),
                );
            }

            // Musician orb core
            let orb_r = tr.base_radius + (4.8 * e) * sc;
            let orb_col = if e > 0.02 {
                tr.color.lerp(Rgb::from_u8(255, 250, 236), (0.52 * e).min(0.65))
            } else {
                tr.color.lerp(Rgb::from_u8(26, 36, 62), 0.62)
            };
            c.fill_circle_aa(tr.stage_x, tr.stage_y, orb_r, orb_col, 0.96);
            c.stroke_circle_aa(
                tr.stage_x,
                tr.stage_y,
                orb_r,
                1.4 * sc,
                if e > 0.05 {
                    Rgb::from_u8(255, 248, 226)
                } else {
                    tr.color
                },
                if e > 0.05 { 0.85 } else { 0.42 },
                false,
                Some(self.stage_clip),
            );
            if e > 0.08 {
                c.fill_circle_aa(
                    tr.stage_x,
                    tr.stage_y,
                    (orb_r * 0.42).max(2.2),
                    Rgb::from_u8(255, 252, 242),
                    (0.92 * e).min(0.95),
                );
            }

            // Crisp illuminated label
            let lbl_col = Rgb::from_u8(138, 152, 184)
                .lerp(Rgb::from_u8(252, 248, 236), (e * 1.4).min(1.0));
            let lbl_alpha = (0.68 + 0.32 * e.min(1.0)) * (1.0 - 0.30 * silence_fade);
            c.draw_text_vector(
                &tr.short_label,
                tr.stage_x,
                tr.label_y,
                10.5 * sc,
                0.85 * sc,
                lbl_col,
                lbl_alpha,
                TextAlign::Center,
            );
        }

        // 2. Live 53-EDO / 12-TET Harmonic Mandala Wheel
        // Collapse simultaneous pitches by discrete wheel bucket (0..52)
        let mut bucket_energy = [0.0_f32; 53];
        let mut bucket_pos = [0.0_f32; 53];
        let mut bucket_col = [Rgb::from_u8(248, 202, 78); 53];
        let mut comma_sum = 0.0_f64;
        let mut comma_weight = 0.0_f64;

        for ap in &active_pitches {
            let idx = (ap.wheel_pos.round() as i32).rem_euclid(53) as usize;
            let e = ap.energy * glow_mult;
            if e > bucket_energy[idx] {
                bucket_energy[idx] = e;
                bucket_pos[idx] = ap.wheel_pos;
                bucket_col[idx] = ap.color;
            }
            comma_sum += comma_offset_from_anchor(ap.step) * e as f64;
            comma_weight += e as f64;
        }

        let mut wheel_nodes: Vec<(f32, f32, f32, Rgb)> = Vec::with_capacity(16);
        for i in 0..53 {
            let e = bucket_energy[i];
            if e > 0.04 {
                let ang = -PI * 0.5 + 2.0 * PI * (bucket_pos[i] as f64 / 53.0);
                let nx = self.wheel_cx + (ang.cos() * self.wheel_r as f64) as f32;
                let ny = self.wheel_cy + (ang.sin() * self.wheel_r as f64) as f32;
                wheel_nodes.push((nx, ny, e, bucket_col[i]));
            }
        }

        // Translucent harmonic chord geometry lines connecting active pitch classes
        for i in 0..wheel_nodes.len() {
            for j in (i + 1)..wheel_nodes.len() {
                let (x0, y0, e0, c0) = wheel_nodes[i];
                let (x1, y1, e1, c1) = wheel_nodes[j];
                let line_e = (e0 * e1).sqrt();
                if line_e > 0.08 {
                    let mid_col = c0.lerp(c1, 0.5).lerp(Rgb::from_u8(248, 224, 156), 0.35);
                    c.draw_capsule_aa(
                        x0,
                        y0,
                        x1,
                        y1,
                        (0.95 + 0.7 * line_e) * sc,
                        mid_col,
                        (0.38 * line_e).min(0.45),
                        true,
                        None,
                    );
                }
            }
        }

        // Glowing pitch-class orbs on the harmonic wheel
        for &(nx, ny, e, col) in &wheel_nodes {
            c.add_radial_glow(nx, ny, (18.0 + 18.0 * e) * sc, col, 0.52 * e, None);
            c.fill_circle_aa(
                nx,
                ny,
                (5.2 + 3.2 * e) * sc,
                col.lerp(Rgb::from_u8(255, 250, 236), 0.45),
                0.95,
            );
        }

        // Subtle center readout inside harmonic wheel
        if comma_weight > 0.05 && silence_fade < 0.7 {
            let center_lbl = match self.tuning {
                TuningMode::Edo53 => {
                    let avg_c = comma_sum / comma_weight;
                    let rounded = avg_c.round() as i32;
                    if rounded == 0 {
                        "HOME 0C".to_string()
                    } else if rounded == 2 {
                        "+2C DIESIS".to_string()
                    } else if rounded > 0 {
                        format!("+{rounded}C COMMA")
                    } else {
                        format!("{rounded}C COMMA")
                    }
                }
                TuningMode::Tet12 => "12-TET 0C".to_string(),
            };
            let voices_lbl = format!("{} ACTIVE PITCHES", wheel_nodes.len());
            c.draw_text_vector(
                &center_lbl,
                self.wheel_cx,
                self.wheel_cy - 12.0 * sc,
                14.5 * sc,
                1.05 * sc,
                Rgb::from_u8(246, 220, 148),
                0.86 * (1.0 - silence_fade),
                TextAlign::Center,
            );
            c.draw_text_vector(
                &voices_lbl,
                self.wheel_cx,
                self.wheel_cy + 12.0 * sc,
                9.5 * sc,
                0.78 * sc,
                Rgb::from_u8(152, 168, 200),
                0.75 * (1.0 - silence_fade),
                TextAlign::Center,
            );
        } else if in_silence {
            c.draw_text_vector(
                "STILLNESS",
                self.wheel_cx,
                self.wheel_cy - 6.0 * sc,
                13.5 * sc,
                0.95 * sc,
                Rgb::from_u8(212, 194, 152),
                0.65 * silence_fade,
                TextAlign::Center,
            );
        }

        // 3. Bottom-Right Now Playing Telemetry Panel (live timestamp + instrument level meters)
        let time_str = format!(
            "{} / {}",
            format_mm_ss(t_sec.min(self.total_dur_s)),
            format_mm_ss(self.total_dur_s)
        );
        c.draw_text_vector(
            &time_str,
            self.now_x1,
            self.now_y0 - 34.0 * sc,
            13.5 * sc,
            1.05 * sc,
            Rgb::from_u8(248, 212, 120),
            0.94,
            TextAlign::Right,
        );

        let max_rows = self.tracks.len().min(14);
        let row_pitch = ((self.now_y1 - self.now_y0) / max_rows.max(1) as f32).min(24.0 * sc);
        let bar_start_x = self.now_x0 + 258.0 * sc;
        let bar_w = (self.now_x1 - bar_start_x).max(60.0 * sc);
        let bar_h = (8.5 * sc).max(4.0);

        for (idx, tr) in self.tracks.iter().take(max_rows).enumerate() {
            let e = track_energies[idx];
            let ry = self.now_y0 + idx as f32 * row_pitch;
            let dot_y = ry + 5.5 * sc;

            // Activity indicator dot
            let dot_col = if e > 0.04 {
                tr.color.lerp(Rgb::from_u8(255, 250, 236), 0.35 * e)
            } else {
                tr.color.lerp(Rgb::from_u8(28, 38, 60), 0.72)
            };
            if e > 0.05 {
                c.add_radial_glow(self.now_x0 + 6.0 * sc, dot_y, 12.0 * sc, tr.color, 0.45 * e, None);
            }
            c.fill_circle_aa(self.now_x0 + 6.0 * sc, dot_y, (4.0 + 1.2 * e) * sc, dot_col, 0.95);

            // Instrument label
            let name_col = Rgb::from_u8(126, 140, 170)
                .lerp(Rgb::from_u8(248, 246, 238), (e * 1.35).min(1.0));
            c.draw_text_vector(
                &tr.label,
                self.now_x0 + 20.0 * sc,
                ry,
                10.5 * sc,
                0.82 * sc,
                name_col,
                0.70 + 0.30 * e.min(1.0),
                TextAlign::Left,
            );

            // Meter trough
            c.fill_rounded_rect(
                bar_start_x,
                dot_y - 0.5 * bar_h,
                bar_start_x + bar_w,
                dot_y + 0.5 * bar_h,
                0.5 * bar_h,
                Rgb::from_u8(18, 26, 46),
                0.92,
                None,
            );

            // Animated level fill
            let fill_frac = e.clamp(0.0, 1.0);
            if fill_frac > 0.015 {
                let fw = (bar_w * fill_frac).max(bar_h);
                let fill_col = tr.color.lerp(Rgb::from_u8(255, 238, 190), 0.25 * fill_frac);
                c.fill_rounded_rect(
                    bar_start_x,
                    dot_y - 0.5 * bar_h,
                    bar_start_x + fw,
                    dot_y + 0.5 * bar_h,
                    0.5 * bar_h,
                    fill_col,
                    0.92,
                    None,
                );
            }
        }

        // 4. Bottom Progress Bar + Playhead + Contemplative Silence Caption
        let prog = (t_sec / self.total_dur_s).clamp(0.0, 1.0) as f32;
        let play_x = self.bar_x0 + prog * (self.bar_x1 - self.bar_x0);

        if play_x > self.bar_x0 + 2.0 {
            let bar_col = if in_silence {
                Rgb::from_u8(178, 152, 118)
            } else {
                Rgb::from_u8(244, 196, 86)
            };
            c.fill_rounded_rect(
                self.bar_x0,
                self.bar_y - 3.5 * sc,
                play_x,
                self.bar_y + 3.5 * sc,
                3.5 * sc,
                bar_col,
                0.92,
                None,
            );
        }

        // Playhead glow orb
        c.add_radial_glow(
            play_x,
            self.bar_y,
            22.0 * sc,
            Rgb::from_u8(248, 212, 120),
            0.55 * glow_mult,
            None,
        );
        c.fill_circle_aa(play_x, self.bar_y, 6.5 * sc, Rgb::from_u8(255, 248, 224), 0.98);

        // Live left timestamp on progress bar
        c.draw_text_vector(
            &format_mm_ss(t_sec.min(self.total_dur_s)),
            self.bar_x0 - 18.0 * sc,
            self.bar_y - 6.0 * sc,
            13.0 * sc,
            1.0 * sc,
            Rgb::from_u8(244, 218, 146),
            0.95,
            TextAlign::Right,
        );

        // Trailing silence serene caption
        if silence_fade > 0.02 {
            c.draw_text_vector(
                "CONTEMPLATIVE SILENCE",
                0.5 * (self.bar_x0 + self.bar_x1),
                self.bar_y - 25.0 * sc,
                11.5 * sc,
                0.9 * sc,
                Rgb::from_u8(226, 206, 162),
                0.88 * silence_fade,
                TextAlign::Center,
            );
        }
    }
}

/// Smooth 80 ms attack / 320 ms exponential decay note activation envelope.
#[inline]
fn note_envelope(t_sec: f64, start_s: f64, end_s: f64, vel: f32) -> f32 {
    if t_sec < start_s {
        return 0.0;
    }
    let dt_start = t_sec - start_s;
    let attack = if dt_start < 0.08 {
        let u = (dt_start / 0.08) as f32;
        u * u * (3.0 - 2.0 * u) // smoothstep
    } else {
        1.0
    };

    if t_sec <= end_s {
        let hold = 0.78 + 0.22 * (-(dt_start / 1.4)).exp() as f32;
        vel * attack * hold
    } else {
        let dt_rel = t_sec - end_s;
        if dt_rel > 1.35 {
            return 0.0;
        }
        let hold_end = 0.78 + 0.22 * (-((end_s - start_s) / 1.4)).exp() as f32;
        let decay = (-(dt_rel / 0.32)).exp() as f32;
        vel * attack * hold_end * decay
    }
}

fn shorten_label(s: &str, max_chars: usize) -> String {
    let trimmed = s.trim();
    if trimmed.chars().count() <= max_chars {
        return trimmed.to_string();
    }
    // Trim cleanly at word boundary rather than cutting mid-word with an ugly dot
    let mut out = String::new();
    for word in trimmed.split_whitespace() {
        let next_len = if out.is_empty() {
            word.chars().count()
        } else {
            out.chars().count() + 1 + word.chars().count()
        };
        if next_len > max_chars {
            break;
        }
        if !out.is_empty() {
            out.push(' ');
        }
        out.push_str(word);
    }
    if out.is_empty() {
        trimmed.chars().take(max_chars).collect()
    } else {
        out
    }
}

/// Clean full-word display name for the Now Playing panel (no abrupt mid-word truncation).
fn clean_panel_label(raw_name: &str, max_chars: usize) -> String {
    let trimmed = raw_name.trim();
    if trimmed.chars().count() <= max_chars {
        return trimmed.to_string();
    }
    // Strip verbose parenthetical notes first if needed
    if let Some((base, _)) = trimmed.split_once('(') {
        let b = base.trim();
        if !b.is_empty() && b.chars().count() <= max_chars {
            return b.to_string();
        }
    }
    shorten_label(trimmed, max_chars)
}

/// Crisp, concise orchestral label for the 2D stage map so neighboring players never collide.
fn concise_stage_label(raw_name: &str, instrument: &str) -> String {
    let lower = raw_name.trim().to_ascii_lowercase();
    let canonical = match instrument {
        "piano" if lower.contains("piano") => Some("PIANO"),
        "harp" if lower.contains("harp") => Some("HARP"),
        "celesta" if lower.contains("celesta") => Some("CELESTA"),
        "church_organ" if lower.contains("organ") => Some("PIPE ORGAN"),
        "string_ensemble" if lower.contains("string") => Some("STRINGS"),
        "slow_strings" if lower.contains("string") => Some("SLOW STRINGS"),
        "pizzicato" if lower.contains("pizzicato") => Some("PIZZICATO"),
        "violin" if lower.contains("violin") => Some("VIOLIN"),
        "viola" if lower.contains("viola") => Some("VIOLA"),
        "cello" if lower.contains("cello") => Some("CELLO"),
        "contrabass" if lower.contains("contrabass") || lower.contains("bass") => Some("CONTRABASS"),
        "flute" if lower.contains("flute") => Some("FLUTE"),
        "clarinet" if lower.contains("clarinet") => Some("CLARINET"),
        "oboe" if lower.contains("oboe") => Some("OBOE"),
        "english_horn" if lower.contains("english horn") => Some("ENGLISH HORN"),
        "bassoon" if lower.contains("bassoon") => Some("BASSOON"),
        "shakuhachi" if lower.contains("shakuhachi") => Some("SHAKUHACHI"),
        "french_horn" if lower.contains("french horn") || lower.contains("horn") => Some("FRENCH HORN"),
        "sitar" if lower.contains("sitar") => Some("SITAR"),
        "ektara" if lower.contains("ektara") => Some("EKTARA"),
        "dotara" if lower.contains("dotara") => Some("DOTARA"),
        _ => None,
    };
    if let Some(lbl) = canonical {
        return lbl.to_string();
    }
    clean_panel_label(raw_name, 14)
}

#[allow(clippy::too_many_arguments)]
fn render_static_background(
    buf: &mut [u8],
    w: usize,
    h: usize,
    sx: f32,
    sy: f32,
    sc: f32,
    score: &JsonScore,
    stage_name: Option<&str>,
    tuning: TuningMode,
    stage_cx: f32,
    stage_cy: f32,
    px_per_m: f32,
    stage_clip: (usize, usize, usize, usize),
    arc_labels: &[(f32, f32, String, TextAlign)],
    wheel_cx: f32,
    wheel_cy: f32,
    wheel_r: f32,
    bar_x0: f32,
    bar_x1: f32,
    bar_y: f32,
    musical_end_s: f64,
    total_dur_s: f64,
) {
    // 1. Deep midnight-indigo radial gradient with warm subtle amber-lavender concert hall atmosphere
    let inv_w = 1.0 / w as f32;
    let inv_h = 1.0 / h as f32;
    for y in 0..h {
        let ny = y as f32 * inv_h;
        let row = y * w * 3;
        for x in 0..w {
            let nx = x as f32 * inv_w;
            // Indigo luminous center near stage
            let dx1 = (nx - 0.35) * 1.45;
            let dy1 = (ny - 0.56) * 1.25;
            let g1 = (1.0 - (dx1 * dx1 + dy1 * dy1).sqrt()).clamp(0.0, 1.0);
            let g1s = g1 * g1;

            // Warm golden-lavender twilight bloom near rear stage & harmonic wheel
            let dx2 = (nx - 0.78) * 1.7;
            let dy2 = (ny - 0.34) * 1.5;
            let g2 = (1.0 - (dx2 * dx2 + dy2 * dy2).sqrt()).clamp(0.0, 1.0);
            let g2s = g2 * g2;

            let r = 7.0 + 17.0 * g1s + 14.0 * g2s;
            let g = 10.0 + 21.0 * g1s + 12.0 * g2s;
            let b = 22.0 + 38.0 * g1s + 26.0 * g2s;

            let idx = row + x * 3;
            buf[idx] = r.min(255.0) as u8;
            buf[idx + 1] = g.min(255.0) as u8;
            buf[idx + 2] = b.min(255.0) as u8;
        }
    }

    let mut c = Canvas::new(w, h, buf);
    let card_bg = Rgb::from_u8(13, 19, 36);
    let card_border = Rgb::from_u8(48, 64, 98);
    let inner_bg = Rgb::from_u8(9, 14, 28);
    let gold_soft = Rgb::from_u8(218, 184, 114);
    let slate_muted = Rgb::from_u8(134, 150, 182);

    // 2. Top Header Card
    c.fill_rounded_rect(
        32.0 * sx,
        18.0 * sy,
        1888.0 * sx,
        92.0 * sy,
        14.0 * sc,
        card_bg,
        0.88,
        Some((card_border, 0.75, 1.4 * sc)),
    );

    // Split title nicely if it has an em-dash or hyphen separator
    let (main_title, sub_part) = if let Some((a, b)) = score.title.split_once('—') {
        (a.trim(), Some(b.trim()))
    } else if let Some((a, b)) = score.title.split_once(" - ") {
        (a.trim(), Some(b.trim()))
    } else {
        (score.title.as_str(), None)
    };
    let main_title_clean = shorten_label(main_title, 44);
    let stage_lbl = stage_name.unwrap_or("INLINE STAGE");
    let subtitle = match sub_part {
        Some(sub) => format!("{}  |  STAGE: {}", shorten_label(sub, 48), stage_lbl),
        None => format!("MUSICAL CHAIRS  |  STAGE: {}", stage_lbl),
    };

    c.draw_text_vector(
        &main_title_clean,
        58.0 * sx,
        32.0 * sy,
        24.0 * sc,
        1.55 * sc,
        Rgb::from_u8(248, 242, 224),
        0.96,
        TextAlign::Left,
    );
    c.draw_text_vector(
        &subtitle,
        58.0 * sx,
        66.0 * sy,
        11.5 * sc,
        0.85 * sc,
        slate_muted,
        0.85,
        TextAlign::Left,
    );

    // Tuning Pill Badge
    let (badge_fill, badge_border, badge_txt, badge_label) = match tuning {
        TuningMode::Edo53 => (
            Rgb::from_u8(16, 48, 42),
            Rgb::from_u8(64, 186, 138),
            Rgb::from_u8(104, 236, 178),
            "53-EDO JUST INTONATION",
        ),
        TuningMode::Tet12 => (
            Rgb::from_u8(54, 38, 16),
            Rgb::from_u8(212, 164, 62),
            Rgb::from_u8(248, 212, 112),
            "12-TET EQUAL TEMP",
        ),
    };
    c.fill_rounded_rect(
        1546.0 * sx,
        34.0 * sy,
        1866.0 * sx,
        76.0 * sy,
        21.0 * sc,
        badge_fill,
        0.95,
        Some((badge_border, 0.85, 1.5 * sc)),
    );
    c.draw_text_vector(
        badge_label,
        1706.0 * sx,
        48.5 * sy,
        12.5 * sc,
        0.95 * sc,
        badge_txt,
        0.96,
        TextAlign::Center,
    );

    // 3. Left / Main Panel: 2D Concert Stage Map
    c.fill_rounded_rect(
        32.0 * sx,
        108.0 * sy,
        1208.0 * sx,
        972.0 * sy,
        16.0 * sc,
        card_bg,
        0.86,
        Some((card_border, 0.75, 1.4 * sc)),
    );
    c.draw_text_vector(
        "CONCERT STAGE  2D SPATIAL SOUNDFIELD",
        56.0 * sx,
        126.0 * sy,
        14.0 * sc,
        1.05 * sc,
        Rgb::from_u8(236, 228, 208),
        0.92,
        TextAlign::Left,
    );
    c.draw_text_vector(
        "METERS  |  LISTENER (0, 0)",
        1184.0 * sx,
        128.0 * sy,
        10.5 * sc,
        0.82 * sc,
        slate_muted,
        0.78,
        TextAlign::Right,
    );
    c.fill_rounded_rect(
        stage_clip.0 as f32,
        stage_clip.1 as f32,
        stage_clip.2 as f32,
        stage_clip.3 as f32,
        12.0 * sc,
        inner_bg,
        0.94,
        Some((Rgb::from_u8(34, 48, 76), 0.7, 1.1 * sc)),
    );

    // Subtle warm spotlight from rear center of concert hall
    c.add_radial_glow(
        stage_cx,
        stage_clip.1 as f32 + 95.0 * sy,
        420.0 * sc,
        Rgb::from_u8(88, 66, 118),
        0.14,
        Some(stage_clip),
    );
    c.add_radial_glow(
        stage_cx,
        stage_cy - 180.0 * sy,
        360.0 * sc,
        Rgb::from_u8(46, 72, 120),
        0.13,
        Some(stage_clip),
    );

    // Azimuth guide lines (-45, 0, +45 deg)
    c.draw_capsule_aa(
        stage_cx,
        stage_cy,
        stage_cx,
        stage_clip.1 as f32,
        0.7 * sc,
        gold_soft,
        0.14,
        false,
        Some(stage_clip),
    );
    c.draw_capsule_aa(
        stage_cx,
        stage_cy,
        stage_cx - 760.0 * sc,
        stage_cy - 760.0 * sc,
        0.65 * sc,
        gold_soft,
        0.10,
        false,
        Some(stage_clip),
    );
    c.draw_capsule_aa(
        stage_cx,
        stage_cy,
        stage_cx + 760.0 * sc,
        stage_cy - 760.0 * sc,
        0.65 * sc,
        gold_soft,
        0.10,
        false,
        Some(stage_clip),
    );

    // Golden 3m, 6m, 9m, 12m concert-hall depth arcs
    for &dist_m in &[3.0_f32, 6.0, 9.0, 12.0] {
        let r = dist_m * px_per_m;
        c.stroke_circle_aa(
            stage_cx,
            stage_cy,
            r,
            1.25 * sc,
            gold_soft,
            0.22,
            false,
            Some(stage_clip),
        );
    }
    for (lx, ly, text, align) in arc_labels {
        c.draw_text_vector(
            text,
            *lx,
            *ly,
            10.0 * sc,
            0.78 * sc,
            gold_soft,
            0.56,
            *align,
        );
    }

    // Listener emblem at bottom center of stage
    c.add_radial_glow(
        stage_cx,
        stage_cy,
        34.0 * sc,
        Rgb::from_u8(224, 198, 134),
        0.16,
        Some(stage_clip),
    );
    c.fill_circle_aa(stage_cx, stage_cy, 12.0 * sc, Rgb::from_u8(24, 34, 58), 0.96);
    c.stroke_circle_aa(
        stage_cx,
        stage_cy,
        12.0 * sc,
        1.6 * sc,
        gold_soft,
        0.82,
        false,
        Some(stage_clip),
    );
    // Upward facing listener chevron
    c.draw_capsule_aa(
        stage_cx - 5.0 * sc,
        stage_cy + 3.0 * sc,
        stage_cx,
        stage_cy - 5.5 * sc,
        1.4 * sc,
        Rgb::from_u8(248, 240, 218),
        0.95,
        false,
        Some(stage_clip),
    );
    c.draw_capsule_aa(
        stage_cx + 5.0 * sc,
        stage_cy + 3.0 * sc,
        stage_cx,
        stage_cy - 5.5 * sc,
        1.4 * sc,
        Rgb::from_u8(248, 240, 218),
        0.95,
        false,
        Some(stage_clip),
    );
    c.draw_text_vector(
        "LISTENER",
        stage_cx,
        stage_cy + 18.0 * sc,
        9.5 * sc,
        0.78 * sc,
        gold_soft,
        0.82,
        TextAlign::Center,
    );

    // Subtle Stage Left / Right cues
    c.draw_text_vector(
        "STAGE LEFT",
        stage_clip.0 as f32 + 18.0 * sc,
        stage_clip.3 as f32 - 22.0 * sc,
        9.5 * sc,
        0.75 * sc,
        slate_muted,
        0.48,
        TextAlign::Left,
    );
    c.draw_text_vector(
        "STAGE RIGHT",
        stage_clip.2 as f32 - 18.0 * sc,
        stage_clip.3 as f32 - 22.0 * sc,
        9.5 * sc,
        0.75 * sc,
        slate_muted,
        0.48,
        TextAlign::Right,
    );

    // 4. Right Top Card: 53-EDO Harmonic Mandala Wheel
    c.fill_rounded_rect(
        1232.0 * sx,
        108.0 * sy,
        1888.0 * sx,
        572.0 * sy,
        16.0 * sc,
        card_bg,
        0.86,
        Some((card_border, 0.75, 1.4 * sc)),
    );
    let wheel_title = match tuning {
        TuningMode::Edo53 => "53-EDO HARMONIC WHEEL",
        TuningMode::Tet12 => "12-TET HARMONIC WHEEL",
    };
    c.draw_text_vector(
        wheel_title,
        1256.0 * sx,
        126.0 * sy,
        14.0 * sc,
        1.05 * sc,
        Rgb::from_u8(236, 228, 208),
        0.92,
        TextAlign::Left,
    );
    c.draw_text_vector(
        "STEPS 0..52",
        1864.0 * sx,
        128.0 * sy,
        10.5 * sc,
        0.82 * sc,
        slate_muted,
        0.75,
        TextAlign::Right,
    );

    // Wheel rings & subtle indigo core disk
    c.fill_circle_aa(wheel_cx, wheel_cy, wheel_r, inner_bg, 0.88);
    c.stroke_circle_aa(
        wheel_cx,
        wheel_cy,
        wheel_r,
        1.6 * sc,
        gold_soft,
        0.38,
        false,
        None,
    );
    c.stroke_circle_aa(
        wheel_cx,
        wheel_cy,
        wheel_r * 0.62,
        1.0 * sc,
        Rgb::from_u8(78, 98, 138),
        0.22,
        false,
        None,
    );

    // 53 golden tick marks around the harmonic circle
    const ANCHOR_LABELS: [(i32, &str); 12] = [
        (0, "C"),
        (4, "C+"),
        (9, "D"),
        (14, "EB"),
        (17, "E"),
        (22, "F"),
        (26, "F+"),
        (31, "G"),
        (36, "AB"),
        (39, "A"),
        (43, "H7"),
        (48, "B"),
    ];
    for step in 0..53 {
        let ang = -PI * 0.5 + 2.0 * PI * (step as f64 / 53.0);
        let cos_a = ang.cos() as f32;
        let sin_a = ang.sin() as f32;
        let anchor = ANCHOR_LABELS.iter().find(|&&(s, _)| s == step);
        let (r_in, r_out, thick, alpha) = if anchor.is_some() {
            (wheel_r - 9.0 * sc, wheel_r + 6.0 * sc, 1.3 * sc, 0.72)
        } else {
            (wheel_r - 4.5 * sc, wheel_r + 2.5 * sc, 0.85 * sc, 0.34)
        };
        c.draw_capsule_aa(
            wheel_cx + cos_a * r_in,
            wheel_cy + sin_a * r_in,
            wheel_cx + cos_a * r_out,
            wheel_cy + sin_a * r_out,
            thick * 0.5,
            gold_soft,
            alpha,
            false,
            None,
        );
        if let Some(&(_, lbl)) = anchor {
            let lr = wheel_r + 21.0 * sc;
            let lx = wheel_cx + cos_a * lr;
            let ly = wheel_cy + sin_a * lr - 4.8 * sc;
            let is_primary = matches!(step, 0 | 17 | 31 | 39 | 43);
            c.draw_text_vector(
                lbl,
                lx,
                ly,
                if is_primary { 10.5 * sc } else { 9.0 * sc },
                0.82 * sc,
                if is_primary {
                    Rgb::from_u8(246, 218, 138)
                } else {
                    slate_muted
                },
                if is_primary { 0.92 } else { 0.68 },
                TextAlign::Center,
            );
        }
    }

    // 5. Right Bottom Card: Now Playing Telemetry
    c.fill_rounded_rect(
        1232.0 * sx,
        590.0 * sy,
        1888.0 * sx,
        972.0 * sy,
        16.0 * sc,
        card_bg,
        0.86,
        Some((card_border, 0.75, 1.4 * sc)),
    );
    c.draw_text_vector(
        "NOW PLAYING",
        1256.0 * sx,
        610.0 * sy,
        14.0 * sc,
        1.05 * sc,
        Rgb::from_u8(236, 228, 208),
        0.92,
        TextAlign::Left,
    );

    // 6. Bottom Progress Bar Card
    c.fill_rounded_rect(
        32.0 * sx,
        988.0 * sy,
        1888.0 * sx,
        1060.0 * sy,
        14.0 * sc,
        card_bg,
        0.88,
        Some((card_border, 0.75, 1.4 * sc)),
    );
    // Progress track trough
    c.fill_rounded_rect(
        bar_x0,
        bar_y - 3.5 * sc,
        bar_x1,
        bar_y + 3.5 * sc,
        3.5 * sc,
        Rgb::from_u8(24, 34, 58),
        0.95,
        None,
    );

    // Marker where music + tail transitions into contemplative trailing silence
    if total_dur_s > musical_end_s + 1.0 {
        let sx_sil = bar_x0 + ((musical_end_s / total_dur_s).clamp(0.0, 1.0) as f32) * (bar_x1 - bar_x0);
        c.draw_capsule_aa(
            sx_sil,
            bar_y - 10.0 * sc,
            sx_sil,
            bar_y + 10.0 * sc,
            1.0 * sc,
            gold_soft,
            0.55,
            false,
            None,
        );
    }

    // Clean minute/second time markers below progress bar
    let tick_s = if total_dur_s <= 30.0 {
        5.0
    } else if total_dur_s <= 120.0 {
        15.0
    } else {
        60.0
    };
    let mut tm = 0.0;
    while tm <= total_dur_s - 0.25 * tick_s {
        let tx = bar_x0 + ((tm / total_dur_s) as f32) * (bar_x1 - bar_x0);
        c.draw_capsule_aa(
            tx,
            bar_y + 7.0 * sc,
            tx,
            bar_y + 12.0 * sc,
            0.7 * sc,
            slate_muted,
            0.45,
            false,
            None,
        );
        c.draw_text_vector(
            &format_mm_ss(tm),
            tx,
            bar_y + 16.0 * sc,
            9.0 * sc,
            0.72 * sc,
            slate_muted,
            0.65,
            TextAlign::Center,
        );
        tm += tick_s;
    }

    // Total duration on far right of progress bar
    c.draw_text_vector(
        &format_mm_ss(total_dur_s),
        bar_x1 + 18.0 * sc,
        bar_y - 6.0 * sc,
        13.0 * sc,
        1.0 * sc,
        slate_muted,
        0.88,
        TextAlign::Left,
    );
}

/// Renders an animated VP9 + Opus YouTube WebM video by streaming raw RGB24 frames to `ffmpeg`.
pub fn render_video_webm(
    score: &JsonScore,
    audio_path: impl AsRef<Path>,
    output_path: impl AsRef<Path>,
    opts: &VideoOptions,
) -> Result<VideoRenderStats, String> {
    let audio_p = audio_path.as_ref();
    let out_p = output_path.as_ref();

    if !audio_p.exists() {
        return Err(format!("Audio input file not found: {}", audio_p.display()));
    }
    if opts.fps == 0 || opts.fps > 120 {
        return Err(format!("Invalid fps {} (must be 1..=120)", opts.fps));
    }
    if opts.width < 320 || opts.height < 180 || opts.width % 2 != 0 || opts.height % 2 != 0 {
        return Err(format!(
            "Invalid dimensions {}x{} (must be even numbers >= 320x180)",
            opts.width, opts.height
        ));
    }

    if let Some(parent) = out_p.parent() {
        if !parent.as_os_str().is_empty() {
            fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create directory {}: {e}", parent.display()))?;
        }
    }

    let wav_dur = read_wav_duration_seconds(audio_p);
    let scene = VideoScene::build(score, opts, wav_dur)?;
    let total_frames = (scene.total_dur_s * opts.fps as f64).ceil().max(1.0) as usize;

    let size_arg = format!("{}x{}", scene.width, scene.height);
    let fps_arg = opts.fps.to_string();

    let mut child = Command::new("ffmpeg")
        .args([
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            &size_arg,
            "-r",
            &fps_arg,
            "-i",
            "pipe:0",
            "-i",
        ])
        .arg(audio_p)
        .args([
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libvpx-vp9",
            "-b:v",
            "0",
            "-crf",
            "30",
            "-deadline",
            "realtime",
            "-cpu-used",
            "6",
            "-row-mt",
            "1",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "libopus",
            "-b:a",
            "192k",
            "-shortest",
            "-y",
        ])
        .arg(out_p)
        .stdin(Stdio::piped())
        .stdout(Stdio::null())
        .stderr(Stdio::inherit())
        .spawn()
        .map_err(|e| format!("Failed to launch ffmpeg: {e}"))?;

    let stdin = child
        .stdin
        .take()
        .ok_or_else(|| "Failed to open ffmpeg stdin pipe".to_string())?;
    let mut writer = BufWriter::with_capacity(4 * 1024 * 1024, stdin);

    let frame_bytes = scene.width * scene.height * 3;
    let batch_size = thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(4)
        .clamp(1, 8);
    let mut batch_bufs: Vec<Vec<u8>> = (0..batch_size).map(|_| vec![0u8; frame_bytes]).collect();

    let t0 = Instant::now();
    let mut last_log = Instant::now();
    let mut frame_idx = 0usize;

    while frame_idx < total_frames {
        let count = (total_frames - frame_idx).min(batch_size);
        let scene_ref = &scene;
        let fps_f = opts.fps as f64;
        let base_idx = frame_idx;

        thread::scope(|s| {
            for (slot, buf) in batch_bufs[..count].iter_mut().enumerate() {
                let t_sec = (base_idx + slot) as f64 / fps_f;
                s.spawn(move || {
                    scene_ref.render_frame(t_sec, buf);
                });
            }
        });

        for buf in &batch_bufs[..count] {
            if let Err(e) = writer.write_all(buf) {
                let _ = child.wait();
                return Err(format!(
                    "Failed writing frame {frame_idx}/{total_frames} to ffmpeg pipe: {e}"
                ));
            }
        }

        frame_idx += count;
        if last_log.elapsed().as_secs_f64() >= 3.0 || frame_idx == total_frames {
            let elapsed = t0.elapsed().as_secs_f64().max(0.001);
            let cur_fps = frame_idx as f64 / elapsed;
            let pct = 100.0 * frame_idx as f64 / total_frames as f64;
            let rem = (total_frames - frame_idx) as f64 / cur_fps.max(0.1);
            println!(
                "  [render-video] {:>5}/{} frames ({:>5.1}%) | {:>5.1} fps | ETA {:>4.0}s",
                frame_idx, total_frames, pct, cur_fps, rem
            );
            last_log = Instant::now();
        }
    }

    writer
        .flush()
        .map_err(|e| format!("Failed flushing ffmpeg stdin: {e}"))?;
    drop(writer);

    let status = child
        .wait()
        .map_err(|e| format!("Failed waiting on ffmpeg: {e}"))?;
    if !status.success() {
        return Err(format!("ffmpeg exited with non-zero status: {status}"));
    }

    Ok(VideoRenderStats {
        output_path: out_p.to_path_buf(),
        width: scene.width,
        height: scene.height,
        fps: opts.fps,
        total_frames,
        duration_seconds: scene.total_dur_s,
        elapsed_seconds: t0.elapsed().as_secs_f64(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::score_json::{load_stage_config, parse_json_score};

    #[test]
    fn test_video_frame_render_and_active_glow_brightness() {
        let json = r#"{
            "title": "Harmonia Mundi — Video Frame Test",
            "tail_seconds": 1.0,
            "end_silence_seconds": 2.0,
            "tempo": [{"beat": 0.0, "bpm": 60.0}],
            "tracks": [
                {
                    "id": "piano",
                    "name": "Concert Grand Piano",
                    "instrument": "piano",
                    "notes": [
                        { "beat": 1.0, "dur": 1.5, "step": 0, "vel": 0.90 },
                        { "beat": 1.0, "dur": 1.5, "step": 17, "vel": 0.85 },
                        { "beat": 1.0, "dur": 1.5, "step": 31, "vel": 0.85 }
                    ]
                },
                {
                    "id": "church_organ",
                    "name": "Cathedral Pipe Organ",
                    "instrument": "church_organ",
                    "notes": [
                        { "beat": 1.2, "dur": 1.3, "step": -53, "vel": 0.85 }
                    ]
                }
            ]
        }"#;

        let score = parse_json_score(json).expect("valid score");
        let stage = load_stage_config("stages/concert_hall.json").expect("concert_hall stage");
        let opts = VideoOptions {
            width: 640,
            height: 360,
            fps: 24,
            stage: Some(stage),
            tuning: TuningMode::Edo53,
        };

        let scene = VideoScene::build(&score, &opts, Some(5.5)).expect("build scene");
        assert_eq!(scene.width, 640);
        assert_eq!(scene.height, 360);
        assert!((scene.total_dur_s - 5.5).abs() < 1e-6);

        let mut silent_frame = vec![0u8; scene.width * scene.height * 3];
        let mut active_frame = vec![0u8; scene.width * scene.height * 3];
        let mut silence_tail_frame = vec![0u8; scene.width * scene.height * 3];

        // t = 0.2s: before any note starts (silent)
        scene.render_frame(0.2, &mut silent_frame);
        // t = 1.4s: piano + organ actively sounding
        scene.render_frame(1.4, &mut active_frame);
        // t = 4.8s: during trailing contemplative silence
        scene.render_frame(4.8, &mut silence_tail_frame);

        let sample_patch_luma = |buf: &[u8], cx: f32, cy: f32, r: i32| -> f64 {
            let mut sum = 0.0_f64;
            let mut cnt = 0usize;
            let icx = cx.round() as i32;
            let icy = cy.round() as i32;
            for dy in -r..=r {
                for dx in -r..=r {
                    let x = (icx + dx).clamp(0, scene.width as i32 - 1) as usize;
                    let y = (icy + dy).clamp(0, scene.height as i32 - 1) as usize;
                    let idx = (y * scene.width + x) * 3;
                    sum += buf[idx] as f64 + buf[idx + 1] as f64 + buf[idx + 2] as f64;
                    cnt += 1;
                }
            }
            sum / cnt.max(1) as f64
        };

        let piano_tr = &scene.tracks[0];
        let luma_silent = sample_patch_luma(&silent_frame, piano_tr.stage_x, piano_tr.stage_y, 10);
        let luma_active = sample_patch_luma(&active_frame, piano_tr.stage_x, piano_tr.stage_y, 10);
        assert!(
            luma_active > luma_silent + 30.0,
            "Active piano glow should be substantially brighter than silent frame (active={luma_active:.1}, silent={luma_silent:.1})"
        );

        let organ_tr = &scene.tracks[1];
        let organ_silent = sample_patch_luma(&silent_frame, organ_tr.stage_x, organ_tr.stage_y, 12);
        let organ_active = sample_patch_luma(&active_frame, organ_tr.stage_x, organ_tr.stage_y, 12);
        assert!(
            organ_active > organ_silent + 25.0,
            "Active pipe organ crown should brighten clearly (active={organ_active:.1}, silent={organ_silent:.1})"
        );
    }
}
