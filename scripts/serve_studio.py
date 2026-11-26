#!/usr/bin/env python3
"""
Zero-dependency HTTP static & library studio server with full RFC 9110 Byte-Range
support (Accept-Ranges: bytes, 206 Partial Content, 416 Range Not Satisfiable)
plus dynamic multi-score & multi-stem discovery at GET /api/library.

Usage:
  python3 scripts/serve_studio.py [port]
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")
CHUNK_SIZE = 64 * 1024

INSTRUMENT_FAMILIES: Dict[str, str] = {
    "piano": "Keys & Plucked",
    "harp": "Keys & Plucked",
    "nylon_guitar": "Keys & Plucked",
    "steel_guitar": "Keys & Plucked",
    "celesta": "Keys & Plucked",
    "church_organ": "Organ",
    "clarinet": "Woodwinds",
    "english_horn": "Woodwinds",
    "bassoon": "Woodwinds",
    "flute": "Woodwinds",
    "oboe": "Woodwinds",
    "shakuhachi": "Woodwinds",
    "french_horn": "Brass",
    "trombone": "Brass",
    "timpani": "Percussion",
    "violin": "Strings",
    "viola": "Strings",
    "cello": "Strings",
    "contrabass": "Strings",
    "string_ensemble": "Strings",
    "tremolo_strings": "Strings",
    "slow_strings": "Strings",
    "pizzicato": "Strings",
    "sitar": "Indian Classical",
    "ektara": "Indian Classical",
    "dotara": "Indian Classical",
}

SAMPLE_5MIN_FALLBACK_SECTIONS = [
    {"beat": 0.0, "seconds": 0.0, "mm_ss": "0:00", "title": "I. Dawn (0:00)"},
    {"beat": 92.0, "seconds": 73.5, "mm_ss": "1:14", "title": "II. Lotus & Mist"},
    {"beat": 180.0, "seconds": 151.0, "mm_ss": "2:31", "title": "III. Tempest"},
    {"beat": 212.0, "seconds": 174.8, "mm_ss": "2:55", "title": "Diesis Summit"},
    {"beat": 244.0, "seconds": 198.2, "mm_ss": "3:18", "title": "Comma Cascade"},
    {"beat": 280.0, "seconds": 227.0, "mm_ss": "3:47", "title": "IV. Transfiguration"},
    {"beat": 304.0, "seconds": 247.6, "mm_ss": "4:08", "title": "Pipe Organ"},
]

ORCHESTRAL_53EDO_FALLBACK_BEATS = [
    (0.0, "I. Adagio Sostenuto"),
    (72.0, "II. Scherzo & Fugato"),
    (148.0, "III. Diesis Tempest & Cascade"),
    (224.0, "IV. Passacaglia"),
    (248.0, "Cathedral Pipe Organ"),
]


def beat_to_seconds(tempo_pts: List[Dict[str, Any]], beat: float) -> float:
    if not tempo_pts:
        return beat * (60.0 / 70.0)
    segs = sorted(
        [(float(p.get("beat", 0.0)), max(1.0, float(p.get("bpm", 70.0)))) for p in tempo_pts],
        key=lambda x: x[0],
    )
    if len(segs) == 1:
        return beat * (60.0 / segs[0][1])
    secs = 0.0
    first_b, first_bpm = segs[0]
    if beat <= first_b:
        return beat * (60.0 / first_bpm)
    if first_b > 0.0:
        secs += first_b * (60.0 / first_bpm)
    for i in range(len(segs) - 1):
        a_b, a_bpm = segs[i]
        b_b, b_bpm = segs[i + 1]
        if beat <= a_b:
            break
        end_b = min(beat, b_b)
        span = b_b - a_b
        partial = end_b - a_b
        if partial <= 0.0:
            continue
        if span <= 1e-9 or abs(b_bpm - a_bpm) < 1e-6:
            secs += partial * (60.0 / a_bpm)
        else:
            slope = (b_bpm - a_bpm) / span
            bpm_end = a_bpm + slope * partial
            secs += (60.0 / slope) * math.log(bpm_end / a_bpm)
        if beat <= b_b:
            return secs
    last_b, last_bpm = segs[-1]
    if beat > last_b:
        secs += (beat - last_b) * (60.0 / last_bpm)
    return secs


def fmt_mm_ss(seconds: float) -> str:
    s = max(0, int(round(seconds)))
    return f"{s // 60}:{s % 60:02d}"


def build_library_payload(repo_root: Path) -> Dict[str, Any]:
    scores_dir = repo_root / "scores"
    output_dir = repo_root / "output"
    stage_players: Dict[str, Any] = {}
    concert_stage_file = repo_root / "stages" / "concert_hall.json"
    if concert_stage_file.is_file():
        try:
            stage_players = json.loads(concert_stage_file.read_text(encoding="utf-8")).get(
                "players", {}
            )
        except Exception:
            stage_players = {}

    compositions: List[Dict[str, Any]] = []
    score_files = sorted(scores_dir.glob("*.json")) if scores_dir.is_dir() else []

    for sf_path in score_files:
        stem = sf_path.stem
        try:
            data = json.loads(sf_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        mp3_53 = output_dir / f"{stem}.mp3"
        wav_53 = output_dir / f"{stem}.wav"
        mp3_12 = output_dir / f"{stem}_12tet.mp3"
        wav_12 = output_dir / f"{stem}_12tet.wav"
        svg_out = output_dir / f"{stem}.svg"
        svg_docs = repo_root / "docs" / f"{stem}.svg"
        webm_out = output_dir / f"{stem}.webm"

        audio_53 = (
            f"../output/{stem}.mp3"
            if mp3_53.is_file()
            else (f"../output/{stem}.wav" if wav_53.is_file() else None)
        )
        if audio_53 is None:
            # Only surface scores that have rendered audio ready to play
            continue

        audio_12 = (
            f"../output/{stem}_12tet.mp3"
            if mp3_12.is_file()
            else (f"../output/{stem}_12tet.wav" if wav_12.is_file() else None)
        )
        svg_url = (
            f"../output/{stem}.svg"
            if svg_out.is_file()
            else (f"../docs/{stem}.svg" if svg_docs.is_file() else None)
        )
        webm_url = f"../output/{stem}.webm" if webm_out.is_file() else None

        tempo_pts = data.get("tempo", [{"beat": 0.0, "bpm": 70.0}])
        raw_sections = data.get("sections", [])
        sections_out = []
        for sec in raw_sections:
            b = float(sec.get("beat", 0.0))
            t_s = beat_to_seconds(tempo_pts, b)
            sections_out.append(
                {
                    "beat": b,
                    "seconds": round(t_s, 2),
                    "mm_ss": fmt_mm_ss(t_s),
                    "title": str(sec.get("title", "")),
                }
            )
        sections_out.sort(key=lambda x: x["seconds"])
        if not sections_out and stem == "sample_5min":
            sections_out = SAMPLE_5MIN_FALLBACK_SECTIONS
        elif not sections_out and stem == "orchestral_53edo":
            sections_out = [
                {
                    "beat": b,
                    "seconds": round(beat_to_seconds(tempo_pts, b), 2),
                    "mm_ss": fmt_mm_ss(beat_to_seconds(tempo_pts, b)),
                    "title": title,
                }
                for b, title in ORCHESTRAL_53EDO_FALLBACK_BEATS
            ]

        tracks = data.get("tracks", [])
        note_count = sum(len(t.get("notes", [])) for t in tracks)

        # Check if synchronized dry stems exist for this score (`output/stems_<stem>/`)
        stems_subdir = output_dir / f"stems_{stem}"
        stem_items = []
        if stems_subdir.is_dir():
            for tr in tracks:
                tid = tr.get("id", "")
                inst = tr.get("instrument", "string_ensemble")
                st_wav = stems_subdir / f"{tid}.wav"
                if st_wav.is_file():
                    pl = stage_players.get(tid) or stage_players.get(inst) or {}
                    x = float(pl.get("x", tr.get("x", 0.0)))
                    y = float(pl.get("y", tr.get("y", 4.5)))
                    stem_items.append(
                        {
                            "id": tid,
                            "name": tr.get("name") or tid,
                            "family": INSTRUMENT_FAMILIES.get(inst, "Strings"),
                            "wav": f"../output/stems_{stem}/{tid}.wav",
                            "x": x,
                            "y": y,
                        }
                    )

        mtime = (wav_53 if wav_53.is_file() else mp3_53).stat().st_mtime
        compositions.append(
            {
                "id": stem,
                "title": data.get("title", stem),
                "description": data.get("description", ""),
                "score_path": f"scores/{stem}.json",
                "track_count": len(tracks),
                "note_count": note_count,
                "audio_53": audio_53,
                "wav_53": f"../output/{stem}.wav" if wav_53.is_file() else None,
                "audio_12": audio_12,
                "wav_12": f"../output/{stem}_12tet.wav" if wav_12.is_file() else None,
                "svg": svg_url,
                "webm": webm_url,
                "sections": sections_out,
                "stems": stem_items,
                "mtime": mtime,
            }
        )

    # Always feature The Shattered Semitone (`edo53_vs_12tet_10min`) first, then newest
    # rendered full compositions, keeping `example_minimal` at the end.
    compositions.sort(
        key=lambda c: (
            2
            if c["id"] == "edo53_vs_12tet_10min"
            else (0 if c["id"] == "example_minimal" else 1),
            c["mtime"],
        ),
        reverse=True,
    )
    return {"compositions": compositions}


def parse_byte_range(header: str, file_size: int) -> Optional[Tuple[int, int]]:
    """Parse a single HTTP byte-range spec into inclusive (start, end), or None if invalid."""
    spec = header.strip()
    if "," in spec:
        spec = spec.split(",", 1)[0].strip()
    m = RANGE_RE.match(spec)
    if not m or file_size <= 0:
        return None
    start_s, end_s = m.groups()
    if not start_s and not end_s:
        return None
    if start_s == "":
        suffix = int(end_s)
        if suffix <= 0:
            return None
        start = max(0, file_size - suffix)
        end = file_size - 1
    else:
        start = int(start_s)
        if start >= file_size:
            return None
        end = file_size - 1 if end_s == "" else min(int(end_s), file_size - 1)
        if end < start:
            return None
    return (start, end)


class RangeRequestHandler(SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler with full HTTP Range (206) + /api/library discovery."""

    protocol_version = "HTTP/1.1"

    def __init__(self, *args, directory: Optional[str] = None, **kwargs):
        self._repo_root = Path(__file__).resolve().parent.parent
        super().__init__(*args, directory=directory or str(self._repo_root), **kwargs)

    def _send_library_json(self, send_body: bool) -> None:
        payload = json.dumps(build_library_payload(self._repo_root)).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if send_body:
            self.wfile.write(payload)

    def _open_for_range(self, send_body: bool) -> None:
        clean_path = self.path.split("?", 1)[0]
        if clean_path == "/api/library":
            self._send_library_json(send_body=send_body)
            return

        path = self.translate_path(self.path)
        if os.path.isdir(path):
            f = self.send_head()
            if f:
                try:
                    if send_body:
                        self.copyfile(f, self.wfile)
                finally:
                    f.close()
            return

        if not os.path.isfile(path):
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        try:
            fs = os.fstat(f.fileno())
            file_size = fs.st_size
            ctype = self.guess_type(path)
            last_mod = self.date_time_string(fs.st_mtime)
            range_hdr = self.headers.get("Range")

            if range_hdr:
                parsed = parse_byte_range(range_hdr, file_size)
                if parsed is None:
                    self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                    self.send_header("Content-Range", f"bytes */{file_size}")
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return

                start, end = parsed
                length = end - start + 1
                self.send_response(HTTPStatus.PARTIAL_CONTENT)
                self.send_header("Content-Type", ctype)
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Last-Modified", last_mod)
                self.end_headers()

                if send_body:
                    f.seek(start)
                    remaining = length
                    while remaining > 0:
                        chunk = f.read(min(CHUNK_SIZE, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            else:
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", ctype)
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Length", str(file_size))
                self.send_header("Last-Modified", last_mod)
                self.end_headers()

                if send_body:
                    while True:
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            f.close()

    def do_GET(self) -> None:
        self._open_for_range(send_body=True)

    def do_HEAD(self) -> None:
        self._open_for_range(send_body=False)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    host = "127.0.0.1"
    repo_root = Path(__file__).resolve().parent.parent
    server = ReusableThreadingHTTPServer((host, port), RangeRequestHandler)
    print(
        f"Serving {repo_root} on http://{host}:{port}/ (HTTP Range/206 + /api/library enabled)",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
