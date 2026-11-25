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
mod wav;

use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::Instant;

use preview::build_preview_score;
use score_json::{load_json_score, render_json_score, RenderOptions};
use sf2_synth::DEFAULT_SOUNDFONT_PATH;
use synth::{render_score, SAMPLE_RATE};
use tuning::{note_name_approx, COMMA, DIESIS, HARM_7, M3, P5};
use wav::write_stereo_wav_16bit;

fn print_usage() {
    eprintln!("Usage:");
    eprintln!("  edo53_music render <input.json> [output.wav] [--stems-dir <dir>] [--soundfont <path>]");
    eprintln!("  edo53_music audition");
    eprintln!("  edo53_music preview-synth");
}

fn default_output_wav(input_path: &Path) -> PathBuf {
    let stem = input_path
        .file_stem()
        .and_then(|s| s.to_str())
        .filter(|s| !s.is_empty())
        .unwrap_or("render");
    PathBuf::from("output").join(format!("{stem}.wav"))
}

fn run_render_cli(args: &[String]) {
    let mut positional: Vec<String> = Vec::new();
    let mut stems_dir: Option<PathBuf> = None;
    let mut soundfont_path = PathBuf::from(DEFAULT_SOUNDFONT_PATH);

    let mut i = 0;
    while i < args.len() {
        let arg = &args[i];
        if arg == "--help" || arg == "-h" {
            print_usage();
            return;
        } else if arg == "--stems-dir" {
            i += 1;
            let Some(val) = args.get(i) else {
                eprintln!("Error: --stems-dir requires a directory argument.");
                std::process::exit(1);
            };
            stems_dir = Some(PathBuf::from(val));
        } else if let Some(val) = arg.strip_prefix("--stems-dir=") {
            if val.is_empty() {
                eprintln!("Error: --stems-dir requires a non-empty directory.");
                std::process::exit(1);
            }
            stems_dir = Some(PathBuf::from(val));
        } else if arg == "--soundfont" {
            i += 1;
            let Some(val) = args.get(i) else {
                eprintln!("Error: --soundfont requires a file path argument.");
                std::process::exit(1);
            };
            soundfont_path = PathBuf::from(val);
        } else if let Some(val) = arg.strip_prefix("--soundfont=") {
            if val.is_empty() {
                eprintln!("Error: --soundfont requires a non-empty file path.");
                std::process::exit(1);
            }
            soundfont_path = PathBuf::from(val);
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
        .unwrap_or_else(|| default_output_wav(&input_path));

    let t0 = Instant::now();
    let score = match load_json_score(&input_path) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("Error loading {}: {e}", input_path.display());
            std::process::exit(1);
        }
    };

    let opts = RenderOptions {
        soundfont_path,
        stems_dir: stems_dir.clone(),
    };

    let result = match render_json_score(&score, &opts) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("Error rendering {}: {e}", input_path.display());
            std::process::exit(1);
        }
    };

    if let Some(parent) = output_path.parent() {
        if !parent.as_os_str().is_empty() {
            if let Err(e) = fs::create_dir_all(parent) {
                eprintln!(
                    "Error creating output directory {}: {e}",
                    parent.display()
                );
                std::process::exit(1);
            }
        }
    }

    if let Err(e) = write_stereo_wav_16bit(&output_path, result.sample_rate as u32, &result.audio) {
        eprintln!("Error writing {}: {e}", output_path.display());
        std::process::exit(1);
    }

    let elapsed = t0.elapsed().as_secs_f64();
    let total_notes: usize = result.track_summaries.iter().map(|t| t.note_count).sum();

    println!("53-EDO JSON Score Render: {}", score.title);
    if !score.description.is_empty() {
        println!("  Description: {}", score.description);
    }
    println!(
        "  Duration: {:.2}s @ {} Hz | Tracks: {} | Total Notes: {} | Tail: {:.2}s | Hall RT60: {:.2}s",
        result.duration_seconds,
        result.sample_rate,
        result.track_summaries.len(),
        total_notes,
        score.tail_seconds,
        score.reverb_rt60
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

fn main() {
    let args: Vec<String> = env::args().collect();
    let mode = args.get(1).map(|s| s.as_str()).unwrap_or("audition");

    match mode {
        "render" => {
            run_render_cli(&args[2..]);
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
