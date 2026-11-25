//! Musical score data structures, tempo map, and event helpers.

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Instrument {
    Flute,
    Clarinet,
    Harp,
    Celesta,
    Violin1,
    Violin2,
    Viola,
    Cello,
    Contrabass,
    OrganPedal,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Articulation {
    Legato,
    Sustained,
    Plucked,
    Bell,
    Expressive,
}

#[derive(Clone, Debug)]
pub struct NoteEvent {
    pub instrument: Instrument,
    pub start_beat: f64,
    pub duration_beat: f64,
    pub step: i32,
    pub velocity: f32,
    pub articulation: Articulation,
    pub micro_cents: f32,
}

#[derive(Clone, Copy, Debug)]
pub struct TempoSegment {
    pub beat: f64,
    pub bpm: f64,
}

/// Piecewise-linear BPM tempo map with exact analytical beat-to-second integration.
#[derive(Clone, Debug)]
pub struct TempoMap {
    segments: Vec<TempoSegment>,
}

impl TempoMap {
    #[allow(dead_code)]
    pub fn constant(bpm: f64) -> Self {
        Self {
            segments: vec![TempoSegment { beat: 0.0, bpm }],
        }
    }

    pub fn from_segments(mut segments: Vec<TempoSegment>) -> Self {
        assert!(!segments.is_empty(), "TempoMap requires at least one segment");
        segments.sort_by(|a, b| a.beat.total_cmp(&b.beat));
        Self { segments }
    }

    /// Converts musical beat position into elapsed seconds.
    pub fn beat_to_seconds(&self, beat: f64) -> f64 {
        if self.segments.len() == 1 {
            return beat * (60.0 / self.segments[0].bpm);
        }

        let mut secs = 0.0;
        let first = self.segments[0];
        if beat <= first.beat {
            return beat * (60.0 / first.bpm);
        }
        if first.beat > 0.0 {
            secs += first.beat * (60.0 / first.bpm);
        }

        for i in 0..self.segments.len() - 1 {
            let a = self.segments[i];
            let b = self.segments[i + 1];
            if beat <= a.beat {
                break;
            }
            let end_b = beat.min(b.beat);
            let span = b.beat - a.beat;
            let partial = end_b - a.beat;
            if partial <= 0.0 {
                continue;
            }
            if span <= 1e-9 || (b.bpm - a.bpm).abs() < 1e-6 {
                secs += partial * (60.0 / a.bpm);
            } else {
                let slope = (b.bpm - a.bpm) / span;
                let bpm_end = a.bpm + slope * partial;
                secs += (60.0 / slope) * (bpm_end / a.bpm).ln();
            }
            if beat <= b.beat {
                return secs;
            }
        }

        let last = *self.segments.last().unwrap();
        if beat > last.beat {
            secs += (beat - last.beat) * (60.0 / last.bpm);
        }
        secs
    }
}

#[derive(Clone, Debug)]
pub struct Score {
    pub tempo: TempoMap,
    pub notes: Vec<NoteEvent>,
}

impl Score {
    pub fn new(tempo: TempoMap) -> Self {
        Self {
            tempo,
            notes: Vec::new(),
        }
    }

    pub fn add_note(
        &mut self,
        instrument: Instrument,
        start_beat: f64,
        duration_beat: f64,
        step: i32,
        velocity: f32,
        articulation: Articulation,
    ) {
        self.notes.push(NoteEvent {
            instrument,
            start_beat,
            duration_beat,
            step,
            velocity: velocity.clamp(0.02, 1.0),
            articulation,
            micro_cents: 0.0,
        });
    }

    #[allow(dead_code)]
    pub fn add_chord(
        &mut self,
        instrument: Instrument,
        start_beat: f64,
        duration_beat: f64,
        steps: &[i32],
        velocity: f32,
        articulation: Articulation,
    ) {
        for &step in steps {
            self.add_note(instrument, start_beat, duration_beat, step, velocity, articulation);
        }
    }

    /// Adds a rolled or flowing arpeggio across `steps`.
    pub fn add_arpeggio(
        &mut self,
        instrument: Instrument,
        start_beat: f64,
        note_duration_beat: f64,
        step_spacing_beat: f64,
        steps: &[i32],
        velocity: f32,
        articulation: Articulation,
    ) {
        for (idx, &step) in steps.iter().enumerate() {
            let t = start_beat + idx as f64 * step_spacing_beat;
            // Gentle dynamic arch across the arpeggio
            let arch = 1.0 - 0.06 * ((idx as f32 / steps.len().max(1) as f32) - 0.5).abs();
            self.add_note(
                instrument,
                t,
                note_duration_beat,
                step,
                velocity * arch,
                articulation,
            );
        }
    }

    pub fn total_duration_seconds(&self, tail_seconds: f64) -> f64 {
        let max_beat = self
            .notes
            .iter()
            .map(|n| n.start_beat + n.duration_beat)
            .fold(0.0_f64, f64::max);
        self.tempo.beat_to_seconds(max_beat) + tail_seconds
    }
}
