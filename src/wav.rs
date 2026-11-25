//! 16-bit PCM stereo WAV writer with TPDF dither.

use std::fs::File;
use std::io::{BufWriter, Result, Write};
use std::path::Path;

pub fn write_stereo_wav_16bit(
    path: impl AsRef<Path>,
    sample_rate: u32,
    samples: &[(f32, f32)],
) -> Result<()> {
    let file = File::create(path)?;
    let mut w = BufWriter::with_capacity(64 * 1024, file);

    let num_channels: u16 = 2;
    let bits_per_sample: u16 = 16;
    let block_align: u16 = num_channels * (bits_per_sample / 8);
    let byte_rate: u32 = sample_rate * block_align as u32;
    let data_bytes: u32 = (samples.len() * block_align as usize) as u32;
    let riff_size: u32 = 36 + data_bytes;

    w.write_all(b"RIFF")?;
    w.write_all(&riff_size.to_le_bytes())?;
    w.write_all(b"WAVE")?;
    w.write_all(b"fmt ")?;
    w.write_all(&16u32.to_le_bytes())?; // PCM chunk size
    w.write_all(&1u16.to_le_bytes())?; // PCM format
    w.write_all(&num_channels.to_le_bytes())?;
    w.write_all(&sample_rate.to_le_bytes())?;
    w.write_all(&byte_rate.to_le_bytes())?;
    w.write_all(&block_align.to_le_bytes())?;
    w.write_all(&bits_per_sample.to_le_bytes())?;
    w.write_all(b"data")?;
    w.write_all(&data_bytes.to_le_bytes())?;

    // TPDF dither PRNG state
    let mut rng: u64 = 0x9E37_79B9_7F4A_7C15;
    let mut next_u = || -> f32 {
        rng ^= rng << 13;
        rng ^= rng >> 7;
        rng ^= rng << 17;
        ((rng >> 40) as f32) * (1.0 / 16_777_216.0)
    };

    for &(l, r) in samples {
        let dl = (next_u() - next_u()) * (1.0 / 32767.0);
        let dr = (next_u() - next_u()) * (1.0 / 32767.0);
        let ql = ((l + dl).clamp(-1.0, 1.0) * 32767.0).round() as i16;
        let qr = ((r + dr).clamp(-1.0, 1.0) * 32767.0).round() as i16;
        w.write_all(&ql.to_le_bytes())?;
        w.write_all(&qr.to_le_bytes())?;
    }

    w.flush()
}
