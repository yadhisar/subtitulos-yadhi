"""Cortes duros de toma con ffmpeg (select='gt(scene,0.4)',showinfo).

    uv run python scripts\\cuts.py "C:\\...\\video.mp4" [--threshold 0.4] [--out cuts.json]

Devuelve los ms del primer cuadro de cada toma nueva. Ninguna página de subtítulos cruza un corte (group.py).
Se analiza una copia chica (ancho 320) para que sea rápido; dos "cortes" a menos de 0.5 s se cuentan como uno
(un flash o una transición corta no parte una frase en dos).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

PTS = re.compile(r"pts_time:\s*([0-9.]+)")


def detect(video: Path, threshold: float = 0.4, min_gap_ms: int = 500) -> list[int]:
    ffmpeg = paths.need("ffmpeg", "Gyan.FFmpeg")
    vf = f"scale=320:-2,select='gt(scene,{threshold})',showinfo"
    r = paths.run([ffmpeg, "-hide_banner", "-nostats", "-i", video, "-an", "-vf", vf, "-f", "null", "-"],
                  capture=True, check=False)
    if r.returncode != 0:
        paths.warn("no pude detectar cortes (sigo sin cortes)")
        return []
    cuts: list[int] = []
    for line in (r.stderr or "").splitlines():
        if "showinfo" not in line or "pts_time" not in line:
            continue
        m = PTS.search(line)
        if not m:
            continue
        ms = int(round(float(m.group(1)) * 1000))
        if ms <= 0:
            continue
        if cuts and ms - cuts[-1] < min_gap_ms:
            continue
        cuts.append(ms)
    return cuts


def main(argv=None):
    paths.utf8_console()
    ap = argparse.ArgumentParser(description="Detecta cortes duros de toma.")
    ap.add_argument("video", type=Path)
    ap.add_argument("--threshold", type=float, default=0.4)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    cuts = detect(a.video, a.threshold)
    if a.out:
        paths.write_json(a.out, {"cuts": cuts})
    print({"cuts": cuts})


if __name__ == "__main__":
    main()
