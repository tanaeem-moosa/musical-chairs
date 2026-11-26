//! Pure-Rust dark-studio SVG visualizer (1600x960) for 53-EDO scores and concert stage maps.

use std::fmt::Write as FmtWrite;

use crate::score::{TempoMap, TempoSegment};
use crate::score_json::{
    resolve_stage_params, resolve_track_placement, JsonScore, ScoreInstrument, StageConfig,
    TuningMode,
};
use crate::tuning::{edo53_to_12tet_midi, OCT};

const SVG_W: f64 = 1600.0;
const SVG_H: f64 = 960.0;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum InstrumentFamily {
    KeysPlucked,
    Strings,
    Woodwinds,
    Brass,
    Percussion,
    Indian,
    Organ,
}

impl InstrumentFamily {
    fn from_instrument(inst: &str) -> Self {
        match ScoreInstrument::parse(inst) {
            Ok(ScoreInstrument::Ektara | ScoreInstrument::Dotara) => Self::Indian,
            Ok(ScoreInstrument::Sf2(sf2)) => match sf2.family() {
                "Keys & Plucked" => Self::KeysPlucked,
                "Strings" => Self::Strings,
                "Woodwinds" | "Woodwinds & World" => Self::Woodwinds,
                "Brass" => Self::Brass,
                "Percussion" => Self::Percussion,
                "Indian Classical" => Self::Indian,
                "Organ" => Self::Organ,
                _ => Self::Strings,
            },
            Err(_) => Self::Strings,
        }
    }

    fn color(self) -> &'static str {
        match self {
            Self::KeysPlucked => "#f5c542",
            Self::Strings => "#58a6ff",
            Self::Woodwinds => "#3dd68c",
            Self::Brass => "#f0883e",
            Self::Percussion => "#ff7b72",
            Self::Indian => "#e86ca8",
            Self::Organ => "#a371f7",
        }
    }

    fn label(self) -> &'static str {
        match self {
            Self::KeysPlucked => "Keys & Plucked",
            Self::Strings => "Strings",
            Self::Woodwinds => "Woodwinds",
            Self::Brass => "Brass",
            Self::Percussion => "Timpani & Perc.",
            Self::Indian => "Indian Classical",
            Self::Organ => "Pipe Organ",
        }
    }

    fn all() -> [Self; 7] {
        [
            Self::KeysPlucked,
            Self::Strings,
            Self::Woodwinds,
            Self::Brass,
            Self::Percussion,
            Self::Indian,
            Self::Organ,
        ]
    }
}

fn xml_escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for ch in s.chars() {
        match ch {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            '\'' => out.push_str("&apos;"),
            _ => out.push(ch),
        }
    }
    out
}

fn format_mm_ss(seconds: f64) -> String {
    let total = seconds.round().max(0.0) as u64;
    let m = total / 60;
    let s = total % 60;
    format!("{m}:{s:02}")
}

/// Computes signed comma offset (-2..=+2) of a 53-EDO step relative to the 12 standard diatonic/chromatic anchors.
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

fn pick_time_tick_step(duration_s: f64) -> f64 {
    for &step in &[1.0, 2.0, 5.0, 10.0, 15.0, 30.0, 60.0, 120.0] {
        if duration_s / step <= 12.0 {
            return step;
        }
    }
    120.0
}

/// Generates a crisp 1600x960 dark-studio SVG visualizing both the 2D concert stage map
/// and the full-piece 53-EDO pitch-roll timeline with comma/tuning indicator.
pub fn render_score_svg(
    score: &JsonScore,
    stage: Option<&StageConfig>,
    tuning: TuningMode,
    end_silence_override: Option<f64>,
) -> Result<String, String> {
    score.validate()?;
    if let Some(st) = stage {
        st.validate()?;
    }

    let stage_params = resolve_stage_params(score, stage, end_silence_override)?;
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

    let mut max_note_end_s = 0.0_f64;
    let mut total_notes = 0usize;
    let mut min_step = -2 * OCT; // C2
    let mut max_step = 2 * OCT; // C6

    struct NoteViz {
        start_s: f64,
        end_s: f64,
        pitch_step: f64,
        raw_step: i32,
        vel: f32,
        color: &'static str,
    }

    let mut viz_notes: Vec<NoteViz> = Vec::new();

    for track in &score.tracks {
        let fam = InstrumentFamily::from_instrument(&track.instrument);
        let color = fam.color();
        total_notes += track.notes.len();
        for n in &track.notes {
            let s0 = tempo.beat_to_seconds(n.beat);
            let s1 = tempo.beat_to_seconds(n.beat + n.dur).max(s0 + 0.04);
            max_note_end_s = max_note_end_s.max(s1);

            let pitch_step = match tuning {
                TuningMode::Edo53 => n.step as f64 + (n.cents as f64 / (1200.0 / OCT as f64)),
                TuningMode::Tet12 => {
                    let midi = edo53_to_12tet_midi(n.step, n.cents as f64);
                    (midi - 60) as f64 * (OCT as f64 / 12.0)
                }
            };

            let step_floor = pitch_step.floor() as i32;
            let step_ceil = pitch_step.ceil() as i32;
            min_step = min_step.min(step_floor);
            max_step = max_step.max(step_ceil);

            viz_notes.push(NoteViz {
                start_s: s0,
                end_s: s1,
                pitch_step,
                raw_step: n.step,
                vel: n.vel,
                color,
            });
        }
    }

    let musical_dur_s = (max_note_end_s + stage_params.tail_seconds).max(1.0);
    let full_dur_s = musical_dur_s + stage_params.end_silence_seconds;
    let timeline_dur_s = max_note_end_s.max(1.0);

    // Snap pitch axis cleanly to octave multiples of 53 (at least C2..C6)
    let min_oct = (min_step as f64 / OCT as f64).floor() as i32;
    let max_oct = (max_step as f64 / OCT as f64).ceil() as i32;
    let axis_min_step = (min_oct.min(-2) * OCT) as f64;
    let axis_max_step = (max_oct.max(2) * OCT) as f64;

    let mut svg = String::with_capacity(64 * 1024);

    // Header & Defs
    let _ = writeln!(
        svg,
        r##"<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_W:.0}" height="{SVG_H:.0}" viewBox="0 0 {SVG_W:.0} {SVG_H:.0}">"##
    );
    svg.push_str(
        r##"  <defs>
    <linearGradient id="bgGrad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#090d14"/>
      <stop offset="100%" stop-color="#111827"/>
    </linearGradient>
    <linearGradient id="stageGlow" x1="0.5" y1="1" x2="0.5" y2="0">
      <stop offset="0%" stop-color="#1d3557" stop-opacity="0.38"/>
      <stop offset="100%" stop-color="#0f172a" stop-opacity="0.04"/>
    </linearGradient>
    <clipPath id="stageClip">
      <rect x="40" y="148" width="484" height="618" rx="10"/>
    </clipPath>
    <clipPath id="rollClip">
      <rect x="626" y="148" width="928" height="656" rx="6"/>
    </clipPath>
    <style>
      .sans { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
      .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
    </style>
  </defs>
"##,
    );

    // Background
    let _ = writeln!(
        svg,
        r##"  <rect x="0" y="0" width="{SVG_W:.0}" height="{SVG_H:.0}" fill="url(#bgGrad)"/>"##
    );

    // Top Header Bar
    let tuning_label = match tuning {
        TuningMode::Edo53 => "53-EDO (Pure 5/7-Limit)",
        TuningMode::Tet12 => "12-TET (Equal Temperament)",
    };
    let (badge_bg, badge_fg, badge_stroke) = match tuning {
        TuningMode::Edo53 => ("#0f2d26", "#3dd68c", "#26825c"),
        TuningMode::Tet12 => ("#33230f", "#f5c542", "#9e7724"),
    };
    let stage_badge = stage_params
        .stage_name
        .as_deref()
        .unwrap_or("Inline Stage");
    let silence_note = if stage_params.end_silence_seconds > 0.0 {
        format!(" + {:.0}s silence", stage_params.end_silence_seconds)
    } else {
        String::new()
    };

    let _ = writeln!(
        svg,
        r##"  <rect x="24" y="16" width="1552" height="62" rx="12" fill="#121a29" stroke="#24314a" stroke-width="1.2"/>
  <text x="44" y="45" class="sans" font-size="22" font-weight="700" fill="#f1f5f9">{title}</text>
  <text x="44" y="66" class="mono" font-size="12" fill="#94a3b8">Duration {dur} ({full_s:.1}s{silence})  ·  {tracks} tracks  ·  {notes} notes  ·  Hall RT60 {rt60:.2}s  ·  Stage: {stage}</text>
  <rect x="1312" y="29" width="244" height="36" rx="18" fill="{badge_bg}" stroke="{badge_stroke}" stroke-width="1.4"/>
  <text x="1434" y="52" text-anchor="middle" class="mono" font-size="13" font-weight="700" fill="{badge_fg}">{tuning_label}</text>"##,
        title = xml_escape(&score.title),
        dur = format_mm_ss(full_dur_s),
        full_s = full_dur_s,
        silence = silence_note,
        tracks = score.tracks.len(),
        notes = total_notes,
        rt60 = stage_params.reverb_rt60,
        stage = xml_escape(stage_badge),
        badge_bg = badge_bg,
        badge_fg = badge_fg,
        badge_stroke = badge_stroke,
        tuning_label = tuning_label,
    );

    // =========================================================================
    // LEFT PANEL: 2D Concert Stage Diagram (x = 24..540, y = 92..936)
    // =========================================================================
    svg.push_str(
        r##"  <rect x="24" y="92" width="516" height="844" rx="14" fill="#121a29" stroke="#24314a" stroke-width="1.2"/>
  <text x="44" y="122" class="sans" font-size="16" font-weight="700" fill="#e2e8f0">2D Concert Stage Map</text>
  <text x="520" y="122" text-anchor="end" class="mono" font-size="11" fill="#64748b">meters · listener at (0, 0)</text>
  <rect x="40" y="148" width="484" height="618" rx="10" fill="#0c1220" stroke="#1e293b" stroke-width="1"/>
"##,
    );

    let stage_cx = 282.0_f64;
    let stage_cy = 736.0_f64;
    let px_per_m = 45.0_f64;

    svg.push_str(r##"  <g clip-path="url(#stageClip)">"##);
    svg.push('\n');
    // Subtle radial acoustic glow from listener
    let _ = writeln!(
        svg,
        r##"    <rect x="40" y="148" width="484" height="618" fill="url(#stageGlow)"/>"##
    );
    // Acoustic azimuth lines (-45, 0, +45 deg)
    let _ = writeln!(
        svg,
        r##"    <line x1="{cx:.1}" y1="{cy:.1}" x2="{cx:.1}" y2="148" stroke="#1e293b" stroke-width="1" stroke-dasharray="4 4"/>
    <line x1="{cx:.1}" y1="{cy:.1}" x2="{lx:.1}" y2="{ly:.1}" stroke="#1b263b" stroke-width="1" stroke-dasharray="3 5"/>
    <line x1="{cx:.1}" y1="{cy:.1}" x2="{rx:.1}" y2="{ly:.1}" stroke="#1b263b" stroke-width="1" stroke-dasharray="3 5"/>"##,
        cx = stage_cx,
        cy = stage_cy,
        lx = stage_cx - 600.0,
        rx = stage_cx + 600.0,
        ly = stage_cy - 600.0,
    );

    // Depth arcs at 3m, 6m, 9m, 12m
    for &dist_m in &[3.0_f64, 6.0, 9.0, 12.0] {
        let r = dist_m * px_per_m;
        let label_y = stage_cy - r + 14.0;
        let _ = writeln!(
            svg,
            r##"    <circle cx="{cx:.1}" cy="{cy:.1}" r="{r:.1}" fill="none" stroke="#25354f" stroke-width="1.1" stroke-dasharray="5 5"/>
    <text x="{lx:.1}" y="{ly:.1}" text-anchor="middle" class="mono" font-size="10.5" fill="#64748b">{d:.0}m</text>"##,
            cx = stage_cx,
            cy = stage_cy,
            r = r,
            lx = stage_cx + 22.0,
            ly = label_y,
            d = dist_m,
        );
    }

    // Stage Left / Stage Right subtle edge cues
    let _ = writeln!(
        svg,
        r##"    <text x="54" y="756" class="mono" font-size="10" fill="#475569">LEFT (-5m)</text>
    <text x="510" y="756" text-anchor="end" class="mono" font-size="10" fill="#475569">RIGHT (+5m)</text>"##
    );

    // Listener marker at (0, 0)
    let _ = writeln!(
        svg,
        r##"    <circle cx="{cx:.1}" cy="{cy:.1}" r="11" fill="#1e293b" stroke="#94a3b8" stroke-width="1.6"/>
    <polygon points="{cx:.1},{t:.1} {l:.1},{b:.1} {r:.1},{b:.1}" fill="#e2e8f0"/>
    <text x="{cx:.1}" y="{lbl:.1}" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="#cbd5e1">LISTENER</text>"##,
        cx = stage_cx,
        cy = stage_cy,
        t = stage_cy - 6.0,
        l = stage_cx - 4.5,
        r = stage_cx + 4.5,
        b = stage_cy + 4.0,
        lbl = stage_cy + 23.0,
    );

    // Collect musicians and nudge overlapping labels gently
    struct StageNode {
        sx: f64,
        sy: f64,
        width_px: f64,
        label_y: f64,
        radius: f64,
        color: &'static str,
        label: String,
        coords: String,
        has_lp: bool,
    }

    let mut nodes: Vec<StageNode> = score
        .tracks
        .iter()
        .map(|track| {
            let p = resolve_track_placement(track, stage);
            let fam = InstrumentFamily::from_instrument(&track.instrument);
            let sx = (stage_cx + p.x * px_per_m).clamp(62.0, 502.0);
            let sy = (stage_cy - p.y * px_per_m).clamp(172.0, 706.0);
            let width_px = if p.width > 0.35 {
                (p.width * px_per_m).clamp(0.0, 380.0)
            } else {
                0.0
            };
            let radius = (7.5 + 3.5 * p.gain.clamp(0.4, 1.3)).clamp(8.0, 12.5);
            StageNode {
                sx,
                sy,
                width_px,
                label_y: sy - radius - 5.0,
                radius,
                color: fam.color(),
                label: track.display_name().to_string(),
                coords: format!("({:.1}, {:.1})", p.x, p.y),
                has_lp: p.warm_lowpass_hz.is_some(),
            }
        })
        .collect();

    // Sort top-to-bottom for simple label de-overlapping
    nodes.sort_by(|a, b| a.sy.total_cmp(&b.sy));
    for i in 0..nodes.len() {
        for j in 0..i {
            let dx = (nodes[i].sx - nodes[j].sx).abs();
            let dy = (nodes[i].label_y - nodes[j].label_y).abs();
            if dx < 86.0 && dy < 15.0 {
                nodes[i].label_y = nodes[i].sy + nodes[i].radius + 13.0;
            }
        }
    }

    for node in &nodes {
        if node.width_px > 12.0 {
            let wx0 = (node.sx - 0.5 * node.width_px).clamp(48.0, 516.0);
            let wx1 = (node.sx + 0.5 * node.width_px).clamp(48.0, 516.0);
            let _ = writeln!(
                svg,
                r##"    <line x1="{wx0:.1}" y1="{y:.1}" x2="{wx1:.1}" y2="{y:.1}" stroke="{c}" stroke-opacity="0.38" stroke-width="2.0" stroke-dasharray="4 3"/>
    <circle cx="{wx0:.1}" cy="{y:.1}" r="2.3" fill="{c}" fill-opacity="0.55"/>
    <circle cx="{wx1:.1}" cy="{y:.1}" r="2.3" fill="{c}" fill-opacity="0.55"/>"##,
                wx0 = wx0,
                wx1 = wx1,
                y = node.sy,
                c = node.color,
            );
        }
        let _ = writeln!(
            svg,
            r##"    <circle cx="{x:.1}" cy="{y:.1}" r="{glow:.1}" fill="{c}" fill-opacity="0.18"/>"##,
            x = node.sx,
            y = node.sy,
            glow = node.radius + 5.5,
            c = node.color,
        );
        if node.has_lp {
            let _ = writeln!(
                svg,
                r##"    <circle cx="{x:.1}" cy="{y:.1}" r="{r:.1}" fill="none" stroke="{c}" stroke-opacity="0.65" stroke-width="1.2" stroke-dasharray="3 2"/>"##,
                x = node.sx,
                y = node.sy,
                r = node.radius + 3.2,
                c = node.color,
            );
        }
        let _ = writeln!(
            svg,
            r##"    <circle cx="{x:.1}" cy="{y:.1}" r="{r:.1}" fill="{c}" stroke="#0b101b" stroke-width="1.8"/>
    <circle cx="{x:.1}" cy="{y:.1}" r="2.2" fill="#0b101b"/>
    <text x="{x:.1}" y="{ly:.1}" text-anchor="middle" class="sans" font-size="11" font-weight="600" fill="#f1f5f9">{lbl}</text>
    <text x="{x:.1}" y="{cy2:.1}" text-anchor="middle" class="mono" font-size="9" fill="#94a3b8">{coords}</text>"##,
            x = node.sx,
            y = node.sy,
            r = node.radius,
            c = node.color,
            ly = node.label_y,
            cy2 = node.label_y + 10.5,
            lbl = xml_escape(&node.label),
            coords = node.coords,
        );
    }
    svg.push_str("  </g>\n");

    // Family Color Legend at bottom of Left Panel
    svg.push_str(
        r##"  <text x="44" y="792" class="sans" font-size="12" font-weight="700" fill="#cbd5e1">Instrument Families</text>
  <text x="520" y="792" text-anchor="end" class="mono" font-size="10" fill="#64748b">dashed ring = warm LP</text>
"##,
    );
    for (idx, fam) in InstrumentFamily::all().iter().enumerate() {
        let col = idx % 2;
        let row = idx / 2;
        let lx = 50.0 + col as f64 * 238.0;
        let ly = 812.0 + row as f64 * 28.0;
        let _ = writeln!(
            svg,
            r##"  <rect x="{x:.1}" y="{ry:.1}" width="222" height="23" rx="6" fill="#0e1625" stroke="#1e293b" stroke-width="1"/>
  <circle cx="{cx:.1}" cy="{cy:.1}" r="5.0" fill="{c}"/>
  <text x="{tx:.1}" y="{ty:.1}" class="sans" font-size="11.5" fill="#e2e8f0">{lbl}</text>"##,
            x = lx,
            ry = ly - 13.0,
            cx = lx + 16.0,
            cy = ly - 1.5,
            c = fam.color(),
            tx = lx + 30.0,
            ty = ly + 2.5,
            lbl = xml_escape(fam.label()),
        );
    }

    // =========================================================================
    // RIGHT PANEL: Full-Piece 53-EDO Pitch-Roll Timeline (x = 564..1576, y = 92..936)
    // =========================================================================
    svg.push_str(
        r##"  <rect x="564" y="92" width="1012" height="844" rx="14" fill="#121a29" stroke="#24314a" stroke-width="1.2"/>
  <text x="586" y="122" class="sans" font-size="16" font-weight="700" fill="#e2e8f0">53-EDO Pitch-Roll Timeline</text>
"##,
    );
    let _ = writeln!(
        svg,
        r##"  <text x="1554" y="122" text-anchor="end" class="mono" font-size="11" fill="#64748b">53 steps / octave  ·  A4 = 440 Hz (step 39)  ·  C4 = step 0</text>"##
    );

    let roll_x = 626.0_f64;
    let roll_y = 148.0_f64;
    let roll_w = 928.0_f64;
    let roll_h = 656.0_f64;

    let _ = writeln!(
        svg,
        r##"  <rect x="{roll_x:.0}" y="{roll_y:.0}" width="{roll_w:.0}" height="{roll_h:.0}" rx="6" fill="#0c1220" stroke="#1e293b" stroke-width="1"/>"##
    );

    let pitch_to_y = |step_f: f64| -> f64 {
        let u = (step_f - axis_min_step) / (axis_max_step - axis_min_step).max(1.0);
        roll_y + roll_h - 14.0 - u * (roll_h - 28.0)
    };
    let time_to_x = |t_s: f64| -> f64 { roll_x + (t_s / timeline_dur_s).clamp(0.0, 1.0) * roll_w };

    // Horizontal octave & fifth gridlines
    let start_oct = (axis_min_step as i32) / OCT;
    let end_oct = (axis_max_step as i32) / OCT;
    for oct_rel in start_oct..=end_oct {
        let step_c = (oct_rel * OCT) as f64;
        let yc = pitch_to_y(step_c);
        let oct_num = 4 + oct_rel;
        let stroke = if oct_rel == 0 { "#3b5278" } else { "#223049" };
        let _ = writeln!(
            svg,
            r##"  <line x1="{x0:.1}" y1="{y:.1}" x2="{x1:.1}" y2="{y:.1}" stroke="{stroke}" stroke-width="1.1"/>
  <text x="{lx:.1}" y="{ly:.1}" text-anchor="end" class="mono" font-size="11.5" font-weight="600" fill="#cbd5e1">C{oct_num}</text>"##,
            x0 = roll_x,
            x1 = roll_x + roll_w,
            y = yc,
            stroke = stroke,
            lx = roll_x - 10.0,
            ly = yc + 4.0,
            oct_num = oct_num,
        );
        if oct_rel < end_oct {
            let yg = pitch_to_y(step_c + 31.0);
            let _ = writeln!(
                svg,
                r##"  <line x1="{x0:.1}" y1="{y:.1}" x2="{x1:.1}" y2="{y:.1}" stroke="#172235" stroke-width="0.8" stroke-dasharray="3 4"/>
  <text x="{lx:.1}" y="{ly:.1}" text-anchor="end" class="mono" font-size="9.5" fill="#64748b">G{oct_num}</text>"##,
                x0 = roll_x,
                x1 = roll_x + roll_w,
                y = yg,
                lx = roll_x - 10.0,
                ly = yg + 3.0,
                oct_num = oct_num,
            );
        }
    }

    // Vertical time gridlines (m:ss)
    let tick_s = pick_time_tick_step(timeline_dur_s);
    let mut t = 0.0;
    while t <= timeline_dur_s + 1e-6 {
        let xt = time_to_x(t);
        let _ = writeln!(
            svg,
            r##"  <line x1="{x:.1}" y1="{y0:.1}" x2="{x:.1}" y2="{y1:.1}" stroke="#1b263b" stroke-width="1"/>
  <text x="{x:.1}" y="{ty:.1}" text-anchor="middle" class="mono" font-size="10.5" fill="#94a3b8">{lbl}</text>"##,
            x = xt,
            y0 = roll_y,
            y1 = roll_y + roll_h,
            ty = roll_y + roll_h + 16.0,
            lbl = format_mm_ss(t),
        );
        t += tick_s;
    }

    // Render pitch-roll notes inside clip path
    let step_px = (roll_h - 28.0) / (axis_max_step - axis_min_step).max(1.0);
    let note_h = (step_px * 2.2).clamp(2.4, 6.5);

    svg.push_str(r##"  <g clip-path="url(#rollClip)">"##);
    svg.push('\n');
    for n in &viz_notes {
        let x0 = time_to_x(n.start_s);
        let x1 = time_to_x(n.end_s);
        let w = (x1 - x0).max(2.0);
        let yc = pitch_to_y(n.pitch_step);
        let op = (0.35 + 0.60 * n.vel.clamp(0.1, 1.0)).clamp(0.35, 0.95);
        let _ = writeln!(
            svg,
            r##"    <rect x="{x0:.1}" y="{y:.1}" width="{w:.1}" height="{h:.1}" rx="1.4" fill="{c}" fill-opacity="{op:.2}"/>"##,
            x0 = x0,
            y = yc - note_h * 0.5,
            w = w,
            h = note_h,
            c = n.color,
            op = op,
        );
    }

    // Optional Movement / Section vertical markers & header pills inside pitch-roll
    if !score.sections.is_empty() {
        let mut sorted_secs: Vec<(f64, &str)> = score
            .sections
            .iter()
            .map(|s| (tempo.beat_to_seconds(s.beat), s.title.as_str()))
            .collect();
        sorted_secs.sort_by(|a, b| a.0.total_cmp(&b.0));

        let mut last_lbl_end_x = -999.0_f64;
        let mut row_toggle = 0usize;
        for (sec_s, sec_title) in &sorted_secs {
            if *sec_s > timeline_dur_s + 0.5 {
                continue;
            }
            let xs = time_to_x(*sec_s);
            let _ = writeln!(
                svg,
                r##"    <line x1="{xs:.1}" y1="{y0:.1}" x2="{xs:.1}" y2="{y1:.1}" stroke="#f5c542" stroke-opacity="0.46" stroke-width="1.2" stroke-dasharray="4 4"/>"##,
                xs = xs,
                y0 = roll_y,
                y1 = roll_y + roll_h,
            );
            let short_t: String = sec_title.chars().take(24).collect();
            let est_w = (short_t.chars().count() as f64 * 6.2 + 12.0).max(36.0);
            let ly = if xs < last_lbl_end_x + 6.0 {
                row_toggle = 1 - row_toggle;
                roll_y + 8.0 + row_toggle as f64 * 20.0
            } else {
                row_toggle = 0;
                roll_y + 8.0
            };
            last_lbl_end_x = xs + est_w;
            let _ = writeln!(
                svg,
                r##"    <rect x="{rx:.1}" y="{ry:.1}" width="{rw:.1}" height="17" rx="4" fill="#131c2e" fill-opacity="0.90" stroke="#f5c542" stroke-opacity="0.55" stroke-width="0.9"/>
    <text x="{tx:.1}" y="{ty:.1}" class="sans" font-size="10" font-weight="600" fill="#fde68a">{lbl}</text>"##,
                rx = xs + 3.0,
                ry = ly,
                rw = est_w,
                tx = xs + 8.0,
                ty = ly + 12.0,
                lbl = xml_escape(&short_t),
            );
        }
    }
    svg.push_str("  </g>\n");

    // =========================================================================
    // COMMA / TUNING INDICATOR STRIP (x = 626..1554, y = 838..918)
    // =========================================================================
    let strip_y = 840.0_f64;
    let strip_h = 76.0_f64;
    let _ = writeln!(
        svg,
        r##"  <rect x="{roll_x:.0}" y="{strip_y:.0}" width="{roll_w:.0}" height="{strip_h:.0}" rx="6" fill="#0c1220" stroke="#1e293b" stroke-width="1"/>
  <text x="{lx:.1}" y="{ty:.1}" text-anchor="end" class="mono" font-size="10" font-weight="700" fill="#94a3b8">COMMA</text>
  <text x="{lx:.1}" y="{ty2:.1}" text-anchor="end" class="mono" font-size="9" fill="#64748b">DRIFT</text>"##,
        lx = roll_x - 10.0,
        ty = strip_y + 34.0,
        ty2 = strip_y + 48.0,
    );

    let comma_min = -2.0_f64;
    let comma_max = 3.2_f64;
    let comma_to_y = |c: f64| -> f64 {
        let u = (c - comma_min) / (comma_max - comma_min);
        strip_y + strip_h - 10.0 - u.clamp(0.0, 1.0) * (strip_h - 20.0)
    };

    // Zero comma baseline & +1c/+2c/+3c markers
    for &(c_val, c_lbl, col) in &[
        (0.0, "0c", "#3b5278"),
        (1.0, "+1c", "#1e2e47"),
        (2.0, "+2c", "#1e2e47"),
        (-1.0, "-1c", "#1e2e47"),
    ] {
        let yc = comma_to_y(c_val);
        let _ = writeln!(
            svg,
            r##"  <line x1="{x0:.1}" y1="{y:.1}" x2="{x1:.1}" y2="{y:.1}" stroke="{col}" stroke-width="1"/>
  <text x="{lx:.1}" y="{ly:.1}" class="mono" font-size="9" fill="#64748b">{c_lbl}</text>"##,
            x0 = roll_x,
            x1 = roll_x + roll_w,
            y = yc,
            col = col,
            lx = roll_x + 6.0,
            ly = yc - 2.0,
            c_lbl = c_lbl,
        );
    }

    match tuning {
        TuningMode::Edo53 => {
            let bins = 120usize;
            let bin_dur = timeline_dur_s / bins as f64;
            let mut pts = String::new();
            let mut last_c = 0.0_f64;
            for b in 0..bins {
                let t0 = b as f64 * bin_dur;
                let t1 = t0 + bin_dur;
                let mut sum_c = 0.0_f64;
                let mut count = 0usize;
                for n in &viz_notes {
                    if n.start_s < t1 && n.end_s > t0 {
                        sum_c += comma_offset_from_anchor(n.raw_step);
                        count += 1;
                    }
                }
                let avg_c = if count > 0 {
                    last_c = sum_c / count as f64;
                    last_c
                } else {
                    last_c
                };
                let xb = roll_x + ((b as f64 + 0.5) / bins as f64) * roll_w;
                let yb = comma_to_y(avg_c);
                let _ = write!(pts, "{xb:.1},{yb:.1} ");
            }
            let _ = writeln!(
                svg,
                r##"  <polyline fill="none" stroke="#3dd68c" stroke-width="2.0" points="{pts}"/>
  <text x="{rx:.1}" y="{ry:.1}" text-anchor="end" class="mono" font-size="10" fill="#3dd68c">53-EDO active comma drift (1c ≈ 22.6¢ · diesis +2c ≈ 45.3¢)</text>"##,
                pts = pts.trim(),
                rx = roll_x + roll_w - 8.0,
                ry = strip_y + 14.0,
            );
        }
        TuningMode::Tet12 => {
            let y0 = comma_to_y(0.0);
            let _ = writeln!(
                svg,
                r##"  <line x1="{x0:.1}" y1="{y0:.1}" x2="{x1:.1}" y2="{y0:.1}" stroke="#f5c542" stroke-width="2.2"/>
  <text x="{rx:.1}" y="{ry:.1}" text-anchor="end" class="mono" font-size="10" fill="#f5c542">12-TET quantized (0c — all syntonic commas &amp; dieses collapsed)</text>"##,
                x0 = roll_x,
                x1 = roll_x + roll_w,
                y0 = y0,
                rx = roll_x + roll_w - 8.0,
                ry = strip_y + 14.0,
            );
        }
    }

    svg.push_str("</svg>\n");
    Ok(svg)
}
