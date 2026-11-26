//! Pure-Rust 53-EDO acoustic & harmonic score analyzer (`edo53_music analyze`).
//!
//! Audits any `JsonScore` in milliseconds for:
//! - 15-channel SF2 polyphony limits and exact voice-stealing events
//! - Low-register mud (`step < -53` / below C3 intervals narrower than P4 = 22 steps)
//! - Cross-track microtonal / syntonic-comma collisions (`1..=3` steps mod 53 = 22.6¢–67.9¢)
//! - Comma-plane drift trajectory and dynamic velocity contour across the piece

use std::fmt::Write as FmtWrite;

use serde::Serialize;

use crate::score::{TempoMap, TempoSegment};
use crate::score_json::{resolve_stage_params, JsonScore, ScoreInstrument, StageConfig};
use crate::tuning::{note_name_approx, OCT, P4};

#[derive(Clone, Debug, Serialize)]
pub struct SectionReport {
    pub beat: f64,
    pub time_seconds: f64,
    pub time_mm_ss: String,
    pub title: String,
}

#[derive(Clone, Debug, Serialize)]
pub struct TrackAudit {
    pub id: String,
    pub name: String,
    pub instrument: String,
    pub note_count: usize,
    pub min_step: i32,
    pub max_step: i32,
    pub min_note: String,
    pub max_note: String,
    pub vel_min: f32,
    pub vel_max: f32,
    pub pedal_count: usize,
    pub peak_polyphony: usize,
    pub voice_steal_count: usize,
    pub first_steal_beat: Option<f64>,
}

#[derive(Clone, Debug, Serialize)]
pub struct LowMudIssue {
    pub beat: f64,
    pub time_seconds: f64,
    pub track_a: String,
    pub step_a: i32,
    pub note_a: String,
    pub track_b: String,
    pub step_b: i32,
    pub note_b: String,
    pub interval_steps: i32,
    pub interval_cents: f64,
}

#[derive(Clone, Debug, Serialize)]
pub struct CommaClashIssue {
    pub time_seconds: f64,
    pub duration_seconds: f64,
    pub beat_approx: f64,
    pub track_a: String,
    pub step_a: i32,
    pub note_a: String,
    pub track_b: String,
    pub step_b: i32,
    pub note_b: String,
    pub pc_distance: i32,
    pub clash_cents: f64,
}

#[derive(Clone, Debug, Serialize)]
pub struct CommaWindowSummary {
    pub start_seconds: f64,
    pub end_seconds: f64,
    pub active_notes: usize,
    pub mean_velocity: f32,
    pub avg_comma_offset: f64,
}

#[derive(Clone, Debug, Serialize)]
pub struct ScoreAnalysis {
    pub title: String,
    pub total_beats: f64,
    pub musical_seconds: f64,
    pub duration_seconds: f64,
    pub bpm_min: f64,
    pub bpm_max: f64,
    pub track_count: usize,
    pub total_notes: usize,
    pub total_voice_steals: usize,
    pub sections: Vec<SectionReport>,
    pub tracks: Vec<TrackAudit>,
    pub low_register_mud: Vec<LowMudIssue>,
    pub comma_clashes: Vec<CommaClashIssue>,
    pub comma_windows: Vec<CommaWindowSummary>,
    pub verdict: String,
}

fn format_mm_ss(seconds: f64) -> String {
    let total = seconds.round().max(0.0) as u64;
    format!("{}:{:02}", total / 60, total % 60)
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

#[inline]
fn mod53_distance(step_a: i32, step_b: i32) -> i32 {
    let d = (step_a - step_b).rem_euclid(OCT);
    d.min(OCT - d)
}

/// Runs a full acoustic, polyphony, register, and 53-EDO comma-clash analysis on `score`.
pub fn analyze_score(
    score: &JsonScore,
    stage: Option<&StageConfig>,
) -> Result<ScoreAnalysis, String> {
    score.validate()?;
    if let Some(st) = stage {
        st.validate()?;
    }

    let stage_params = resolve_stage_params(score, stage, None)?;
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

    let bpm_min = score
        .tempo
        .iter()
        .map(|t| t.bpm)
        .fold(f64::INFINITY, f64::min);
    let bpm_max = score.tempo.iter().map(|t| t.bpm).fold(0.0_f64, f64::max);

    let mut sections: Vec<SectionReport> = score
        .sections
        .iter()
        .map(|s| {
            let t_sec = tempo.beat_to_seconds(s.beat);
            SectionReport {
                beat: s.beat,
                time_seconds: t_sec,
                time_mm_ss: format_mm_ss(t_sec),
                title: s.title.clone(),
            }
        })
        .collect();
    sections.sort_by(|a, b| a.beat.total_cmp(&b.beat));

    let mut total_beats = 0.0_f64;
    let mut max_note_end_s = 0.0_f64;
    let mut total_notes = 0usize;
    let mut total_voice_steals = 0usize;
    let mut tracks_out = Vec::with_capacity(score.tracks.len());

    #[derive(Clone)]
    struct ActiveSpan {
        start_b: f64,
        start_s: f64,
        end_s: f64,
        step: i32,
        vel: f32,
        track_idx: usize,
        is_percussive: bool,
    }
    let mut all_spans: Vec<ActiveSpan> = Vec::new();

    for (ti, tr) in score.tracks.iter().enumerate() {
        let inst = ScoreInstrument::parse(&tr.instrument)?;
        let is_sf2 = matches!(inst, ScoreInstrument::Sf2(_));
        let is_percussive = tr.instrument == "timpani";
        total_notes += tr.notes.len();

        let mut min_step = i32::MAX;
        let mut max_step = i32::MIN;
        let mut vel_min = f32::INFINITY;
        let mut vel_max = 0.0_f32;

        // Simulate exact 15-slot SF2 channel allocation to count real voice steals
        let mut evs: Vec<(f64, i32, usize)> = Vec::with_capacity(tr.notes.len() * 2);
        for (ni, n) in tr.notes.iter().enumerate() {
            let b0 = n.beat;
            let b1 = n.beat + n.dur;
            let s0 = tempo.beat_to_seconds(b0);
            let s1 = tempo.beat_to_seconds(b1).max(s0 + 0.01);
            total_beats = total_beats.max(b1);
            max_note_end_s = max_note_end_s.max(s1);
            min_step = min_step.min(n.step);
            max_step = max_step.max(n.step);
            vel_min = vel_min.min(n.vel);
            vel_max = vel_max.max(n.vel);

            evs.push((s0, 1, ni));
            evs.push((s1, -1, ni));

            all_spans.push(ActiveSpan {
                start_b: b0,
                start_s: s0,
                end_s: s1,
                step: n.step,
                vel: n.vel,
                track_idx: ti,
                is_percussive,
            });
        }

        // Release (-1) ordered before NoteOn (+1) at identical timestamps
        evs.sort_by(|a, b| a.0.total_cmp(&b.0).then_with(|| a.1.cmp(&b.1)));
        let mut active = 0usize;
        let mut peak_poly = 0usize;
        let mut voice_steals = 0usize;
        let mut first_steal_beat = None;

        for &(_, delta, ni) in &evs {
            if delta > 0 {
                if is_sf2 && active >= 15 {
                    voice_steals += 1;
                    if first_steal_beat.is_none() {
                        first_steal_beat = Some(tr.notes[ni].beat);
                    }
                } else {
                    active += 1;
                }
                peak_poly = peak_poly.max(active);
            } else {
                active = active.saturating_sub(1);
            }
        }
        total_voice_steals += voice_steals;

        let (min_s_clean, max_s_clean, min_lbl, max_lbl, vmin_c, vmax_c) = if tr.notes.is_empty() {
            (0, 0, "-".to_string(), "-".to_string(), 0.0, 0.0)
        } else {
            (
                min_step,
                max_step,
                note_name_approx(min_step),
                note_name_approx(max_step),
                vel_min,
                vel_max,
            )
        };

        tracks_out.push(TrackAudit {
            id: tr.id.clone(),
            name: tr.display_name().to_string(),
            instrument: tr.instrument.clone(),
            note_count: tr.notes.len(),
            min_step: min_s_clean,
            max_step: max_s_clean,
            min_note: min_lbl,
            max_note: max_lbl,
            vel_min: vmin_c,
            vel_max: vmax_c,
            pedal_count: tr.pedals.len(),
            peak_polyphony: peak_poly,
            voice_steal_count: voice_steals,
            first_steal_beat,
        });
    }

    // 1. Low-register mud audit: simultaneous notes < -53 (C3) closer than P4 (22 steps)
    let mut low_spans: Vec<&ActiveSpan> = all_spans
        .iter()
        .filter(|s| s.step < -OCT && !s.is_percussive)
        .collect();
    low_spans.sort_by(|a, b| a.start_s.total_cmp(&b.start_s));

    let mut low_register_mud = Vec::new();
    for i in 0..low_spans.len() {
        let a = low_spans[i];
        for b in &low_spans[(i + 1)..] {
            if b.start_s >= a.end_s - 0.08 {
                break;
            }
            let overlap = a.end_s.min(b.end_s) - b.start_s;
            if overlap < 0.08 {
                continue;
            }
            let diff = (b.step - a.step).abs();
            if diff > 0 && diff < P4 {
                low_register_mud.push(LowMudIssue {
                    beat: b.start_b,
                    time_seconds: b.start_s,
                    track_a: score.tracks[a.track_idx].id.clone(),
                    step_a: a.step,
                    note_a: note_name_approx(a.step),
                    track_b: score.tracks[b.track_idx].id.clone(),
                    step_b: b.step,
                    note_b: note_name_approx(b.step),
                    interval_steps: diff,
                    interval_cents: diff as f64 * (1200.0 / OCT as f64),
                });
                if low_register_mud.len() >= 32 {
                    break;
                }
            }
        }
        if low_register_mud.len() >= 32 {
            break;
        }
    }

    // 2. Cross-track microtonal / comma-clash audit (`1..=3` steps mod 53 sustained >= 0.20s)
    let mut pitched_spans: Vec<&ActiveSpan> =
        all_spans.iter().filter(|s| !s.is_percussive).collect();
    pitched_spans.sort_by(|a, b| a.start_s.total_cmp(&b.start_s));

    let mut comma_clashes = Vec::new();
    for i in 0..pitched_spans.len() {
        let a = pitched_spans[i];
        for b in &pitched_spans[(i + 1)..] {
            if b.start_s >= a.end_s - 0.20 {
                break;
            }
            let overlap_start = a.start_s.max(b.start_s);
            let overlap_end = a.end_s.min(b.end_s);
            let overlap_dur = overlap_end - overlap_start;
            if overlap_dur < 0.20 {
                continue;
            }
            let pc_dist = mod53_distance(a.step, b.step);
            if (1..=3).contains(&pc_dist) {
                let clash_beat = if b.start_s >= a.start_s {
                    b.start_b
                } else {
                    a.start_b
                };
                // Deduplicate adjacent repeated arpeggio hits within 1.0s on the same track pair & steps
                let dup = comma_clashes.iter().any(|prev: &CommaClashIssue| {
                    (prev.time_seconds - overlap_start).abs() < 1.0
                        && prev.step_a == a.step
                        && prev.step_b == b.step
                        && prev.track_a == score.tracks[a.track_idx].id
                        && prev.track_b == score.tracks[b.track_idx].id
                });
                if !dup {
                    comma_clashes.push(CommaClashIssue {
                        time_seconds: overlap_start,
                        duration_seconds: overlap_dur,
                        beat_approx: clash_beat,
                        track_a: score.tracks[a.track_idx].id.clone(),
                        step_a: a.step,
                        note_a: note_name_approx(a.step),
                        track_b: score.tracks[b.track_idx].id.clone(),
                        step_b: b.step,
                        note_b: note_name_approx(b.step),
                        pc_distance: pc_dist,
                        clash_cents: pc_dist as f64 * (1200.0 / OCT as f64),
                    });
                }
                if comma_clashes.len() >= 32 {
                    break;
                }
            }
        }
        if comma_clashes.len() >= 32 {
            break;
        }
    }

    // 3. Comma-drift & dynamic contour windows (10 even slices across active music)
    let active_dur = max_note_end_s.max(1.0);
    let win_count = 10usize;
    let win_dur = active_dur / win_count as f64;
    let mut comma_windows = Vec::with_capacity(win_count);
    let mut last_comma = 0.0_f64;

    for w in 0..win_count {
        let t0 = w as f64 * win_dur;
        let t1 = t0 + win_dur;
        let mut cnt = 0usize;
        let mut vel_sum = 0.0_f32;
        let mut comma_sum = 0.0_f64;
        for sp in &all_spans {
            if sp.start_s < t1 && sp.end_s > t0 && !sp.is_percussive {
                cnt += 1;
                vel_sum += sp.vel;
                comma_sum += comma_offset_from_anchor(sp.step);
            }
        }
        let avg_c = if cnt > 0 {
            last_comma = comma_sum / cnt as f64;
            last_comma
        } else {
            last_comma
        };
        comma_windows.push(CommaWindowSummary {
            start_seconds: t0,
            end_seconds: t1,
            active_notes: cnt,
            mean_velocity: if cnt > 0 { vel_sum / cnt as f32 } else { 0.0 },
            avg_comma_offset: avg_c,
        });
    }

    let musical_seconds = max_note_end_s + stage_params.tail_seconds;
    let duration_seconds = musical_seconds + stage_params.end_silence_seconds;
    let verdict = if total_voice_steals == 0
        && low_register_mud.is_empty()
        && comma_clashes.is_empty()
    {
        "PASS".to_string()
    } else {
        format!(
            "WARN ({} voice steals, {} low-mud overlaps, {} comma clashes)",
            total_voice_steals,
            low_register_mud.len(),
            comma_clashes.len()
        )
    };

    Ok(ScoreAnalysis {
        title: score.title.clone(),
        total_beats,
        musical_seconds,
        duration_seconds,
        bpm_min,
        bpm_max,
        track_count: score.tracks.len(),
        total_notes,
        total_voice_steals,
        sections,
        tracks: tracks_out,
        low_register_mud,
        comma_clashes,
        comma_windows,
        verdict,
    })
}

/// Formats `ScoreAnalysis` into a human-readable CLI report.
pub fn format_analysis_report(rep: &ScoreAnalysis) -> String {
    let mut out = String::with_capacity(4096);
    let _ = writeln!(out, "53-EDO Acoustic & Harmonic Analysis: {}", rep.title);
    let _ = writeln!(
        out,
        "  Duration: {} ({:.2}s) | Beats: {:.1} | Tempo: {:.1}–{:.1} BPM | Tracks: {} | Notes: {}",
        format_mm_ss(rep.duration_seconds),
        rep.duration_seconds,
        rep.total_beats,
        rep.bpm_min,
        rep.bpm_max,
        rep.track_count,
        rep.total_notes
    );
    let _ = writeln!(out, "  Verdict:  {}", rep.verdict);

    if !rep.sections.is_empty() {
        let _ = writeln!(out, "\n  Sections ({}):", rep.sections.len());
        for s in &rep.sections {
            let _ = writeln!(
                out,
                "    - [{:>5}] beat {:>6.1} : {}",
                s.time_mm_ss, s.beat, s.title
            );
        }
    }

    let _ = writeln!(
        out,
        "\n  Track Polyphony, Range & Dynamics (15-channel SF2 limit):"
    );
    for tr in &rep.tracks {
        let ped_str = if tr.pedal_count > 0 {
            format!(" | {} pedals", tr.pedal_count)
        } else {
            String::new()
        };
        let steal_str = if tr.voice_steal_count > 0 {
            format!(" [STEALS: {}]", tr.voice_steal_count)
        } else {
            String::new()
        };
        let _ = writeln!(
            out,
            "    - {:<18} ({:<16}) | {:>4} notes | range {:<8}..{:<8} | vel {:.2}–{:.2} | peak poly {:>2}/15{}{}",
            tr.id,
            tr.instrument,
            tr.note_count,
            tr.min_note,
            tr.max_note,
            tr.vel_min,
            tr.vel_max,
            tr.peak_polyphony,
            ped_str,
            steal_str
        );
    }

    let _ = writeln!(out, "\n  Comma-Drift & Dynamic Contour:");
    for w in &rep.comma_windows {
        let _ = writeln!(
            out,
            "    {:>5}–{:<5} | {:>4} notes | mean vel {:.2} | avg comma {:+.2}c",
            format_mm_ss(w.start_seconds),
            format_mm_ss(w.end_seconds),
            w.active_notes,
            w.mean_velocity,
            w.avg_comma_offset
        );
    }

    if !rep.low_register_mud.is_empty() {
        let _ = writeln!(
            out,
            "\n  Low-Register Mud Warnings (< C3 intervals narrower than P4):"
        );
        for m in rep.low_register_mud.iter().take(10) {
            let _ = writeln!(
                out,
                "    ! beat {:>6.2} ({}) : {} ({}) vs {} ({}) -> {} steps ({:.1}c)",
                m.beat,
                format_mm_ss(m.time_seconds),
                m.track_a,
                m.note_a,
                m.track_b,
                m.note_b,
                m.interval_steps,
                m.interval_cents
            );
        }
    }

    if !rep.comma_clashes.is_empty() {
        let _ = writeln!(
            out,
            "\n  Microtonal / Syntonic-Comma Clashes (1..=3 steps mod 53 >= 0.20s):"
        );
        for c in rep.comma_clashes.iter().take(10) {
            let _ = writeln!(
                out,
                "    ! {} (beat {:>6.2}, {:.2}s) : {} ({}) vs {} ({}) -> {}c ({:.1} cents)",
                format_mm_ss(c.time_seconds),
                c.beat_approx,
                c.duration_seconds,
                c.track_a,
                c.note_a,
                c.track_b,
                c.note_b,
                c.pc_distance,
                c.clash_cents
            );
        }
    }

    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::score_json::parse_json_score;

    #[test]
    fn test_analyzer_detects_clean_vs_clashing_scores() {
        let clean = parse_json_score(
            r#"{
                "title": "Clean Pure Triad",
                "sections": [{ "beat": 0.0, "title": "I. Opening" }],
                "tempo": [{ "beat": 0.0, "bpm": 60.0 }],
                "tracks": [
                    { "id": "cello", "instrument": "cello", "notes": [{ "beat": 0.0, "dur": 2.0, "step": -53 }] },
                    { "id": "viola", "instrument": "viola", "notes": [{ "beat": 0.0, "dur": 2.0, "step": 17 }] },
                    { "id": "clarinet", "instrument": "clarinet", "notes": [{ "beat": 0.0, "dur": 2.0, "step": 31, "swell": "arch" }] }
                ]
            }"#,
        )
        .unwrap();

        let rep_clean = analyze_score(&clean, None).unwrap();
        assert_eq!(rep_clean.verdict, "PASS");
        assert_eq!(rep_clean.sections.len(), 1);
        assert!(rep_clean.low_register_mud.is_empty());
        assert!(rep_clean.comma_clashes.is_empty());

        // Score with 1) low mud below C3 (-84 vs -70 = 14 steps < P4), and 2) 1-comma clash (17 vs 18)
        let flawed = parse_json_score(
            r#"{
                "title": "Flawed Score",
                "tempo": [{ "beat": 0.0, "bpm": 60.0 }],
                "tracks": [
                    { "id": "bassoon", "instrument": "bassoon", "notes": [{ "beat": 0.0, "dur": 2.0, "step": -84 }] },
                    { "id": "cello", "instrument": "cello", "notes": [{ "beat": 0.0, "dur": 2.0, "step": -70 }] },
                    { "id": "viola", "instrument": "viola", "notes": [{ "beat": 0.0, "dur": 2.0, "step": 17 }] },
                    { "id": "clarinet", "instrument": "clarinet", "notes": [{ "beat": 0.0, "dur": 2.0, "step": 18 }] }
                ]
            }"#,
        )
        .unwrap();

        let rep_flawed = analyze_score(&flawed, None).unwrap();
        assert!(rep_flawed.verdict.starts_with("WARN"));
        assert_eq!(rep_flawed.low_register_mud.len(), 1);
        assert_eq!(rep_flawed.comma_clashes.len(), 1);
        assert_eq!(rep_flawed.comma_clashes[0].pc_distance, 1);
    }
}
