mod audition;
mod indian;
mod preview;
mod reverb;
mod score;
mod score_json;
mod sf2_synth;
mod spatial;
mod synth;
mod tuning;
mod video;
mod visualize;
mod wav;

use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::Instant;

use preview::build_preview_score;
use score_json::{
    load_json_score, load_stage_config, render_json_score, RenderOptions, TuningMode,
};
use sf2_synth::DEFAULT_SOUNDFONT_PATH;
use synth::{render_score, SAMPLE_RATE};
use tuning::{note_name_approx, COMMA, DIESIS, HARM_7, M3, P5};
use video::{render_video_webm, VideoOptions};
use visualize::render_score_svg;
use wav::write_stereo_wav_16bit;

fn print_usage() {
    eprintln!("Usage:");
    eprintln!("  edo53_music render <input.json> [output.wav] [OPTIONS]");
    eprintln!("    --stage <stage.json>       Decoupled stage placement, gain, LP & hall config");
    eprintln!("    --tuning <53edo|12tet>     Tuning system (default: 53edo)");
    eprintln!("    --end-silence <seconds>    Appended clean trailing silence after reverb tail");
    eprintln!("    --stems-dir <dir>          Also export synchronized centered dry stems");
    eprintln!("    --image <out.svg>          Also render 1600x960 dark-studio SVG score & stage map");
    eprintln!("    --soundfont <path>         Custom SoundFont2 path (default: soundfonts/GeneralUser-GS.sf2)");
    eprintln!("  edo53_music visualize <score.json> [out.svg] [--stage <stage.json>] [--tuning <53edo|12tet>] [--end-silence <seconds>]");
    eprintln!("  edo53_music render-video <score.json> <audio.wav> [output.webm] [OPTIONS]");
    eprintln!("    --stage <stage.json>       Decoupled stage placement & hall config");
    eprintln!("    --tuning <53edo|12tet>     Tuning system (default: 53edo)");
    eprintln!("    --fps <24>                 Video frame rate (default: 24)");
    eprintln!("    --width <1920>             Video width in pixels (default: 1920)");
    eprintln!("    --height <1080>            Video height in pixels (default: 1080)");
    eprintln!("  edo53_music audition");
    eprintln!("  edo53_music preview-synth");
}

fn default_output_with_ext(input_path: &Path, ext: &str) -> PathBuf {
    let stem = input_path
        .file_stem()
        .and_then(|s| s.to_str())
        .filter(|s| !s.is_empty())
        .unwrap_or("render");
    PathBuf::from("output").join(format!("{stem}.{ext}"))
}

fn ensure_parent_dir(path: &Path) {
    if let Some(parent) = path.parent() {
        if !parent.as_os_str().is_empty() {
            if let Err(e) = fs::create_dir_all(parent) {
                eprintln!("Error creating directory {}: {e}", parent.display());
                std::process::exit(1);
            }
        }
    }
}

fn parse_flag_value(flag: &str, args: &[String], i: &mut usize) -> String {
    if let Some(val) = args[*i].strip_prefix(&format!("{flag}=")) {
        if val.is_empty() {
            eprintln!("Error: {flag} requires a non-empty value.");
            std::process::exit(1);
        }
        val.to_string()
    } else {
        *i += 1;
        match args.get(*i) {
            Some(v) => v.clone(),
            None => {
                eprintln!("Error: {flag} requires a value.");
                std::process::exit(1);
            }
        }
    }
}

fn parse_nonneg_f64(flag: &str, raw: &str) -> f64 {
    match raw.parse::<f64>() {
        Ok(v) if v.is_finite() && v >= 0.0 => v,
        _ => {
            eprintln!("Error: {flag} expects a non-negative number, got `{raw}`.");
            std::process::exit(1);
        }
    }
}

fn run_render_cli(args: &[String]) {
    let mut positional: Vec<String> = Vec::new();
    let mut stems_dir: Option<PathBuf> = None;
    let mut stage_path: Option<PathBuf> = None;
    let mut image_path: Option<PathBuf> = None;
    let mut tuning = TuningMode::Edo53;
    let mut end_silence_override: Option<f64> = None;
    let mut soundfont_path = PathBuf::from(DEFAULT_SOUNDFONT_PATH);

    let mut i = 0;
    while i < args.len() {
        let arg = &args[i];
        if arg == "--help" || arg == "-h" {
            print_usage();
            return;
        } else if arg == "--stems-dir" || arg.starts_with("--stems-dir=") {
            stems_dir = Some(PathBuf::from(parse_flag_value("--stems-dir", args, &mut i)));
        } else if arg == "--stage" || arg.starts_with("--stage=") {
            stage_path = Some(PathBuf::from(parse_flag_value("--stage", args, &mut i)));
        } else if arg == "--image" || arg.starts_with("--image=") {
            image_path = Some(PathBuf::from(parse_flag_value("--image", args, &mut i)));
        } else if arg == "--tuning" || arg.starts_with("--tuning=") {
            let raw = parse_flag_value("--tuning", args, &mut i);
            tuning = match TuningMode::parse(&raw) {
                Ok(t) => t,
                Err(e) => {
                    eprintln!("Error: {e}");
                    std::process::exit(1);
                }
            };
        } else if arg == "--end-silence" || arg.starts_with("--end-silence=") {
            let raw = parse_flag_value("--end-silence", args, &mut i);
            end_silence_override = Some(parse_nonneg_f64("--end-silence", &raw));
        } else if arg == "--soundfont" || arg.starts_with("--soundfont=") {
            soundfont_path = PathBuf::from(parse_flag_value("--soundfont", args, &mut i));
        } else if arg.starts_with('-') {
            eprintln!("Error: unknown option `{arg}`.");
            print_usage();
            std::process::exit(1);
        } else {
            positional.push(arg.clone());
        }
        i += 1;
    }

    if positional.is_empty() || positional.len() > 2 {
        eprintln!("Error: `render` expects <input.json> and optional [output.wav].");
        print_usage();
        std::process::exit(1);
    }

    let input_path = PathBuf::from(&positional[0]);
    let output_path = positional
        .get(1)
        .map(PathBuf::from)
        .unwrap_or_else(|| default_output_with_ext(&input_path, "wav"));

    let t0 = Instant::now();
    let score = match load_json_score(&input_path) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("Error loading {}: {e}", input_path.display());
            std::process::exit(1);
        }
    };

    let stage = stage_path.as_ref().map(|p| match load_stage_config(p) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("Error loading stage {}: {e}", p.display());
            std::process::exit(1);
        }
    });

    let opts = RenderOptions {
        soundfont_path,
        stems_dir: stems_dir.clone(),
        stage: stage.clone(),
        tuning,
        end_silence_override,
    };

    let result = match render_json_score(&score, &opts) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("Error rendering {}: {e}", input_path.display());
            std::process::exit(1);
        }
    };

    ensure_parent_dir(&output_path);
    if let Err(e) = write_stereo_wav_16bit(&output_path, result.sample_rate as u32, &result.audio) {
        eprintln!("Error writing {}: {e}", output_path.display());
        std::process::exit(1);
    }

    if let Some(svg_path) = &image_path {
        let svg = match render_score_svg(&score, stage.as_ref(), tuning, end_silence_override) {
            Ok(s) => s,
            Err(e) => {
                eprintln!("Error generating SVG {}: {e}", svg_path.display());
                std::process::exit(1);
            }
        };
        ensure_parent_dir(svg_path);
        if let Err(e) = fs::write(svg_path, svg) {
            eprintln!("Error writing SVG {}: {e}", svg_path.display());
            std::process::exit(1);
        }
    }

    let elapsed = t0.elapsed().as_secs_f64();
    let total_notes: usize = result.track_summaries.iter().map(|t| t.note_count).sum();

    println!("53-EDO JSON Score Render: {}", score.title);
    if !score.description.is_empty() {
        println!("  Description: {}", score.description);
    }
    let stage_info = result
        .stage_name
        .as_deref()
        .map(|s| format!(" | Stage: {s}"))
        .unwrap_or_default();
    let silence_info = if result.end_silence_seconds > 0.0 {
        format!(" | End Silence: {:.2}s", result.end_silence_seconds)
    } else {
        String::new()
    };
    println!(
        "  Duration: {:.2}s @ {} Hz | Tuning: {} | Tracks: {} | Total Notes: {} | Tail: {:.2}s | Hall RT60: {:.2}s{}{}",
        result.duration_seconds,
        result.sample_rate,
        result.tuning.label(),
        result.track_summaries.len(),
        total_notes,
        result.tail_seconds,
        result.reverb_rt60,
        silence_info,
        stage_info
    );
    for tr in &result.track_summaries {
        let lp_str = match tr.warm_lowpass_hz {
            Some(hz) => format!(" | LP {hz:.0} Hz"),
            None => String::new(),
        };
        println!(
            "  - {:<18} ({:<24}) | {:<15} | {:>5} notes | pos ({:>5.1}, {:>4.1}) | gain {:.2}{}",
            tr.id,
            tr.name,
            tr.instrument,
            tr.note_count,
            tr.pos.x,
            tr.pos.y,
            tr.gain,
            lp_str
        );
    }
    if !result.stems_written.is_empty() {
        if let Some(dir) = &stems_dir {
            println!(
                "  Dry stems: {} files written to {}",
                result.stems_written.len(),
                dir.display()
            );
        }
    }
    if let Some(svg_path) = &image_path {
        println!("  Visual SVG: {}", svg_path.display());
    }
    println!(
        "Rendered {} in {:.2}s | Peak: {:.2} dBFS | RMS L/R: {:.2}/{:.2} dBFS | Clipped: {} | NaNs: {}",
        output_path.display(),
        elapsed,
        result.stats.peak_db,
        result.stats.rms_l_db,
        result.stats.rms_r_db,
        result.stats.clipped_samples,
        result.stats.nan_count
    );
}

fn run_visualize_cli(args: &[String]) {
    let mut positional: Vec<String> = Vec::new();
    let mut stage_path: Option<PathBuf> = None;
    let mut tuning = TuningMode::Edo53;
    let mut end_silence_override: Option<f64> = None;

    let mut i = 0;
    while i < args.len() {
        let arg = &args[i];
        if arg == "--help" || arg == "-h" {
            print_usage();
            return;
        } else if arg == "--stage" || arg.starts_with("--stage=") {
            stage_path = Some(PathBuf::from(parse_flag_value("--stage", args, &mut i)));
        } else if arg == "--tuning" || arg.starts_with("--tuning=") {
            let raw = parse_flag_value("--tuning", args, &mut i);
            tuning = match TuningMode::parse(&raw) {
                Ok(t) => t,
                Err(e) => {
                    eprintln!("Error: {e}");
                    std::process::exit(1);
                }
            };
        } else if arg == "--end-silence" || arg.starts_with("--end-silence=") {
            let raw = parse_flag_value("--end-silence", args, &mut i);
            end_silence_override = Some(parse_nonneg_f64("--end-silence", &raw));
        } else if arg.starts_with('-') {
            eprintln!("Error: unknown option `{arg}`.");
            print_usage();
            std::process::exit(1);
        } else {
            positional.push(arg.clone());
        }
        i += 1;
    }

    if positional.is_empty() || positional.len() > 2 {
        eprintln!("Error: `visualize` expects <score.json> and optional [out.svg].");
        print_usage();
        std::process::exit(1);
    }

    let input_path = PathBuf::from(&positional[0]);
    let out_svg = positional
        .get(1)
        .map(PathBuf::from)
        .unwrap_or_else(|| default_output_with_ext(&input_path, "svg"));

    let t0 = Instant::now();
    let score = match load_json_score(&input_path) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("Error loading {}: {e}", input_path.display());
            std::process::exit(1);
        }
    };
    let stage = stage_path.as_ref().map(|p| match load_stage_config(p) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("Error loading stage {}: {e}", p.display());
            std::process::exit(1);
        }
    });

    let svg = match render_score_svg(&score, stage.as_ref(), tuning, end_silence_override) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("Error visualizing {}: {e}", input_path.display());
            std::process::exit(1);
        }
    };

    ensure_parent_dir(&out_svg);
    if let Err(e) = fs::write(&out_svg, &svg) {
        eprintln!("Error writing {}: {e}", out_svg.display());
        std::process::exit(1);
    }

    println!(
        "Visualized `{}` -> {} ({} bytes, tuning: {}) in {:.3}s",
        score.title,
        out_svg.display(),
        svg.len(),
        tuning.label(),
        t0.elapsed().as_secs_f64()
    );
}

fn parse_pos_usize(flag: &str, raw: &str) -> usize {
    match raw.parse::<usize>() {
        Ok(v) if v > 0 => v,
        _ => {
            eprintln!("Error: {flag} expects a positive integer, got `{raw}`.");
            std::process::exit(1);
        }
    }
}

fn run_render_video_cli(args: &[String]) {
    let mut positional: Vec<String> = Vec::new();
    let mut stage_path: Option<PathBuf> = None;
    let mut tuning = TuningMode::Edo53;
    let mut fps: u32 = 24;
    let mut width: usize = 1920;
    let mut height: usize = 1080;

    let mut i = 0;
    while i < args.len() {
        let arg = &args[i];
        if arg == "--help" || arg == "-h" {
            print_usage();
            return;
        } else if arg == "--stage" || arg.starts_with("--stage=") {
            stage_path = Some(PathBuf::from(parse_flag_value("--stage", args, &mut i)));
        } else if arg == "--tuning" || arg.starts_with("--tuning=") {
            let raw = parse_flag_value("--tuning", args, &mut i);
            tuning = match TuningMode::parse(&raw) {
                Ok(t) => t,
                Err(e) => {
                    eprintln!("Error: {e}");
                    std::process::exit(1);
                }
            };
        } else if arg == "--fps" || arg.starts_with("--fps=") {
            let raw = parse_flag_value("--fps", args, &mut i);
            fps = parse_pos_usize("--fps", &raw) as u32;
        } else if arg == "--width" || arg.starts_with("--width=") {
            let raw = parse_flag_value("--width", args, &mut i);
            width = parse_pos_usize("--width", &raw);
        } else if arg == "--height" || arg.starts_with("--height=") {
            let raw = parse_flag_value("--height", args, &mut i);
            height = parse_pos_usize("--height", &raw);
        } else if arg.starts_with('-') {
            eprintln!("Error: unknown option `{arg}`.");
            print_usage();
            std::process::exit(1);
        } else {
            positional.push(arg.clone());
        }
        i += 1;
    }

    if positional.len() < 2 || positional.len() > 3 {
        eprintln!("Error: `render-video` expects <score.json> <audio.wav> [output.webm].");
        print_usage();
        std::process::exit(1);
    }

    let score_path = PathBuf::from(&positional[0]);
    let audio_path = PathBuf::from(&positional[1]);
    let output_path = positional
        .get(2)
        .map(PathBuf::from)
        .unwrap_or_else(|| default_output_with_ext(&score_path, "webm"));

    let score = match load_json_score(&score_path) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("Error loading {}: {e}", score_path.display());
            std::process::exit(1);
        }
    };
    let stage = stage_path.as_ref().map(|p| match load_stage_config(p) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("Error loading stage {}: {e}", p.display());
            std::process::exit(1);
        }
    });

    println!(
        "Rendering animated WebM video for `{}` ({}x{} @ {} fps, tuning: {})...",
        score.title,
        width,
        height,
        fps,
        tuning.label()
    );

    let opts = VideoOptions {
        width,
        height,
        fps,
        stage,
        tuning,
    };

    match render_video_webm(&score, &audio_path, &output_path, &opts) {
        Ok(stats) => {
            let size_mb = fs::metadata(&stats.output_path)
                .map(|m| m.len() as f64 / (1024.0 * 1024.0))
                .unwrap_or(0.0);
            println!(
                "Rendered {} ({:.2} MB, {}x{} @ {} fps, {} frames, {:.2}s) in {:.2}s ({:.1} fps)",
                stats.output_path.display(),
                size_mb,
                stats.width,
                stats.height,
                stats.fps,
                stats.total_frames,
                stats.duration_seconds,
                stats.elapsed_seconds,
                stats.total_frames as f64 / stats.elapsed_seconds.max(0.001)
            );
        }
        Err(e) => {
            eprintln!("Error rendering video: {e}");
            std::process::exit(1);
        }
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let mode = args.get(1).map(|s| s.as_str()).unwrap_or("audition");

    match mode {
        "render" => {
            run_render_cli(&args[2..]);
        }
        "visualize" => {
            run_visualize_cli(&args[2..]);
        }
        "render-video" => {
            run_render_video_cli(&args[2..]);
        }
        "audition" => {
            let t0 = Instant::now();
            audition::render_all_auditions();
            println!("Done in {:.2}s.", t0.elapsed().as_secs_f64());
        }
        "preview-synth" => {
            let t0 = Instant::now();
            fs::create_dir_all("output").expect("failed to create output directory");

            let score = build_preview_score();
            let tail_seconds = 4.5;
            let total_dur = score.total_duration_seconds(tail_seconds);

            println!("53-EDO Pure-Synth Classical Chamber Preview");
            println!(
                "  Key intervals: P5={} steps, M3={} steps, HARM_7(7:4)={} steps, COMMA={}, DIESIS={}",
                P5, M3, HARM_7, COMMA, DIESIS
            );
            println!(
                "  Sections: I Luminous Opening (C={}) | II Chromatic-Mediant Surge -> C++({}) -> 2x Comma Pump -> C | III Radiant Resolution",
                note_name_approx(0),
                note_name_approx(DIESIS)
            );
            println!(
                "  Score events: {}, target duration: {:.2}s @ {} Hz",
                score.notes.len(),
                total_dur,
                SAMPLE_RATE
            );

            let (audio, stats) = render_score(&score, tail_seconds);
            let out_path = "output/preview_60s.wav";
            write_stereo_wav_16bit(out_path, SAMPLE_RATE as u32, &audio)
                .expect("failed to write WAV");

            let elapsed = t0.elapsed().as_secs_f64();
            println!(
                "Rendered {} in {:.2}s | Peak: {:.2} dBFS | RMS L/R: {:.2}/{:.2} dBFS | Clipped: {} | NaNs: {}",
                out_path,
                elapsed,
                stats.peak_db,
                stats.rms_l_db,
                stats.rms_r_db,
                stats.clipped_samples,
                stats.nan_count
            );
        }
        "--help" | "-h" | "help" => {
            print_usage();
        }
        other => {
            eprintln!("Unknown mode `{other}`.");
            print_usage();
            std::process::exit(1);
        }
    }
}
