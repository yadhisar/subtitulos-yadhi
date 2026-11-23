"""Compone el video final con ffmpeg (argumentos en lista, sin shell).

    uv run python scripts\\composite.py --video in.mp4 --overlay overlay.mov --out out.mp4
    uv run python scripts\\composite.py --video in.mp4 --behind behind.mov --matte matte.mkv --front front.mov --out out.mp4

Modo detrás apila: video -> palabras grandes -> persona (video x matte) -> línea pequeña.
Salida H.264 crf 18, yuv420p, +faststart, mismo tamaño y fps; el audio se copia (o se pasa a AAC si el
contenedor MP4 no lo acepta).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

MP4_AUDIO_OK = {"aac", "mp3", "alac", "ac3", "eac3", "opus", "flac"}


def composite(video: Path, out: Path, *, overlay: Path | None = None, behind: Path | None = None,
              matte: Path | None = None, front: Path | None = None, crf: int = 18, preset: str = "medium") -> Path:
    ffmpeg = paths.need("ffmpeg", "Gyan.FFmpeg")
    info = paths.probe(video)
    ov = "overlay=format=auto:eof_action=pass"
    if behind:
        if not matte:
            paths.die("el modo detrás necesita --matte")
        inputs = [video, behind, matte] + ([front] if front else [])
        fc = (f"[0:v]split=2[bg][src];[2:v]format=gray,scale={info['width']}:{info['height']}[m];"
              f"[src][m]alphamerge[fg];[bg][1:v]{ov}[b1];[b1][fg]{ov}[b2]")
        fc += f";[b2][3:v]{ov},format=yuv420p[v]" if front else ";[b2]format=yuv420p[v]"
    else:
        if not overlay:
            paths.die("falta --overlay (o --behind con --matte)")
        inputs = [video, overlay]
        fc = f"[0:v][1:v]{ov},format=yuv420p[v]"
    cmd = [ffmpeg, "-v", "error", "-y"]
    for i in inputs:
        cmd += ["-i", i]
    cmd += ["-filter_complex", fc, "-map", "[v]"]
    if info["hasAudio"]:
        cmd += ["-map", "0:a:0"]
        cmd += ["-c:a", "copy"] if (info["audioCodec"] or "") in MP4_AUDIO_OK else ["-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-crf", str(crf), "-preset", preset, "-pix_fmt", "yuv420p", "-r", str(info["fps"]),
            "-movflags", "+faststart", out]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    paths.run(cmd, capture=True)
    return Path(out)


def main(argv=None):
    paths.utf8_console()
    ap = argparse.ArgumentParser(description="Pone la capa de subtítulos sobre el video")
    ap.add_argument("--video", type=Path, required=True)
    ap.add_argument("--overlay", type=Path)
    ap.add_argument("--behind", type=Path)
    ap.add_argument("--matte", type=Path)
    ap.add_argument("--front", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--preset", default="medium")
    a = ap.parse_args(argv)
    out = composite(a.video, a.out, overlay=a.overlay, behind=a.behind, matte=a.matte, front=a.front, crf=a.crf,
                    preset=a.preset)
    print({"out": str(out)})


if __name__ == "__main__":
    main()
