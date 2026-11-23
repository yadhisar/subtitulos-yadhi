"""Recorte de la persona cuadro a cuadro (MediaPipe ImageSegmenter) para poner texto "detrás de ti".

    uv run python scripts\\matte.py "C:\\...\\video.mp4" --out matte.mkv [--cuts 4042,7542]

Salida:
- matte.mkv: video en escala de grises (blanco = persona), mismo tamaño, fps y número de cuadros que el video,
  sin pérdida (FFV1). composite.py lo usa como alfa de la persona.
- matte.json: por cuadro, cuánto del cuadro ocupa la persona, qué tan estable es el recorte y una grilla 9x16
  de ocupación (shots.py la usa para saber si la palabra grande quedaría casi oculta).

El recorte se suaviza en el tiempo (sin parpadeo) y el suavizado se reinicia en cada corte de toma.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import descargar_modelos  # noqa: E402
import paths  # noqa: E402
import subject as subj  # noqa: E402

GRID = (9, 16)  # columnas x filas


def segmenter(model: str = "selfie_multiclass_256x256.tflite"):
    from mediapipe.tasks.python import vision

    return vision.ImageSegmenter.create_from_options(
        vision.ImageSegmenterOptions(base_options=subj._base(model), output_confidence_masks=True,
                                     output_category_mask=False))


def person_prob(seg, frame, multiclass: bool):
    import numpy as np

    res = seg.segment(subj.to_mp(frame))
    masks = res.confidence_masks
    if multiclass:
        return 1.0 - np.asarray(masks[0].numpy_view(), dtype=np.float32)  # clase 0 = fondo
    return np.asarray(masks[0].numpy_view(), dtype=np.float32)


def make_matte(video: Path, info: dict, out: Path, cuts_ms: list[int] | None = None, width: int = 384,
               smooth: float = 0.55) -> dict:
    import cv2
    import numpy as np

    descargar_modelos.require()
    multiclass = True
    try:
        seg = segmenter()
    except Exception:  # noqa: BLE001
        multiclass = False
        seg = segmenter("selfie_segmenter.tflite")
    ffmpeg = paths.need("ffmpeg", "Gyan.FFmpeg")
    w, h = paths.scaled_size(info, width)
    W, H = info["width"], info["height"]
    out.parent.mkdir(parents=True, exist_ok=True)
    sigma = max(0.8, H / 1080 * 1.6)
    writer = subprocess.Popen(
        [ffmpeg, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}", "-r", str(info["fps"]),
         "-i", "-", "-vf", f"scale={W}:{H}:flags=bicubic,gblur=sigma={sigma:.2f}", "-c:v", "ffv1", "-pix_fmt", "gray",
         str(out)],
        stdin=subprocess.PIPE)
    cut_frames = {int(round(c * info["fps"] / 1000)) for c in (cuts_ms or [])}
    prev_raw = None
    ema = None
    coverage, instability, grid = [], [], []
    n = 0
    for i, _, fr in paths.iter_frames(video, info, width):
        raw = person_prob(seg, fr, multiclass)
        if raw.shape != (h, w):
            raw = cv2.resize(raw, (w, h), interpolation=cv2.INTER_LINEAR)
        if i in cut_frames or ema is None:
            ema = raw.copy()
            instability.append(0.0)
        else:
            instability.append(round(float(np.abs(raw - prev_raw).mean()), 4))
            ema = smooth * raw + (1 - smooth) * ema
        prev_raw = raw
        t = np.clip((ema - 0.3) / 0.4, 0, 1)
        m = t * t * (3 - 2 * t)  # bordes más definidos sin escalón duro
        coverage.append(round(float((m > 0.5).mean()), 4))
        g = cv2.resize(m, GRID, interpolation=cv2.INTER_AREA)
        grid.append([int(round(v * 100)) for v in g.flatten()])
        writer.stdin.write((m * 255).astype(np.uint8).tobytes())
        n += 1
    writer.stdin.close()
    writer.wait()
    seg.close()
    if writer.returncode != 0:
        paths.die("ffmpeg no pudo escribir el matte")
    return {"fps": info["fps"], "frames": n, "grid": list(GRID), "coverage": coverage, "instability": instability,
            "cells": grid, "model": "multiclass" if multiclass else "selfie"}


def main(argv=None):
    paths.utf8_console()
    ap = argparse.ArgumentParser(description="Genera el matte (recorte) de la persona")
    ap.add_argument("video", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cuts", default="", help="cortes en ms separados por coma")
    a = ap.parse_args(argv)
    info = paths.probe(a.video)
    cuts = [int(x) for x in a.cuts.split(",") if x.strip()]
    stats = make_matte(a.video, info, a.out, cuts)
    paths.write_json(a.out.with_suffix(".json"), stats, indent=None)
    print(f"{stats['frames']} cuadros -> {a.out}")


if __name__ == "__main__":
    main()
