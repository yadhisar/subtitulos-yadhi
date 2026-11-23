"""Cara y manos por tiempo (MediaPipe Tasks: FaceDetector + HandLandmarker).

    uv run python scripts\\subject.py "C:\\...\\video.mp4" --out subject.json [--fps 4]

Muestrea el video (4 cuadros por segundo por defecto) y guarda cajas normalizadas 0..1:
    {"fps": 4, "samples": [{"ms": 0, "faces": [[x, y, w, h]], "hands": [[x, y, w, h]]}]}
placement.py las usa para que el texto no tape la cara ni las manos; shots.py para decidir "detrás".
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# MediaPipe escribe mucho log técnico en la consola: se silencia
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import descargar_modelos  # noqa: E402
import paths  # noqa: E402


def _base(name: str):
    from mediapipe.tasks import python as mpt

    # se pasa el modelo como bytes: así no importa si la ruta tiene espacios o tildes
    return mpt.BaseOptions(model_asset_buffer=descargar_modelos.model_path(name).read_bytes())


def face_detector():
    from mediapipe.tasks.python import vision

    return vision.FaceDetector.create_from_options(
        vision.FaceDetectorOptions(base_options=_base("blaze_face_short_range.tflite"), min_detection_confidence=0.5))


def hand_landmarker():
    from mediapipe.tasks.python import vision

    return vision.HandLandmarker.create_from_options(
        vision.HandLandmarkerOptions(base_options=_base("hand_landmarker.task"), num_hands=2,
                                     min_hand_detection_confidence=0.5))


def to_mp(frame):
    import mediapipe as mp
    import numpy as np

    return mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(frame))


def analyze(video: Path, info: dict, fps: float = 4.0, width: int = 640) -> dict:
    descargar_modelos.require()
    fd = face_detector()
    hl = hand_landmarker()
    samples = []
    for _, ms, fr in paths.iter_frames(video, info, width, fps=fps):
        h, w = fr.shape[:2]
        img = to_mp(fr)
        faces = []
        for d in fd.detect(img).detections:
            b = d.bounding_box
            # la caja de BlazeFace corta la frente y el mentón: se agranda un poco hacia arriba y abajo
            x, y, bw, bh = b.origin_x / w, b.origin_y / h, b.width / w, b.height / h
            y0 = max(0.0, y - bh * 0.25)
            faces.append([round(x, 4), round(y0, 4), round(bw, 4), round(min(1 - y0, bh * 1.45), 4)])
        hands = []
        for lm in hl.detect(img).hand_landmarks:
            xs = [p.x for p in lm]
            ys = [p.y for p in lm]
            x0, x1 = max(0.0, min(xs)), min(1.0, max(xs))
            y0, y1 = max(0.0, min(ys)), min(1.0, max(ys))
            if x1 > x0 and y1 > y0:
                hands.append([round(x0, 4), round(y0, 4), round(x1 - x0, 4), round(y1 - y0, 4)])
        samples.append({"ms": ms, "faces": faces, "hands": hands})
    fd.close()
    hl.close()
    return {"fps": fps, "samples": samples}


def boxes_between(subject: dict | None, a_ms: int, b_ms: int, pad_ms: int = 250, hands: bool = True) -> list[list[float]]:
    """Todas las cajas (cara y, si se pide, manos) vistas entre a_ms y b_ms."""
    if not subject:
        return []
    out = []
    for s in subject.get("samples", []):
        if a_ms - pad_ms <= s["ms"] <= b_ms + pad_ms:
            out += s.get("faces", [])
            if hands:
                out += s.get("hands", [])
    return out


def main(argv=None):
    paths.utf8_console()
    ap = argparse.ArgumentParser(description="Detecta cara y manos a lo largo del video")
    ap.add_argument("video", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--fps", type=float, default=4.0)
    a = ap.parse_args(argv)
    info = paths.probe(a.video)
    data = analyze(a.video, info, a.fps)
    paths.write_json(a.out, data, indent=None)
    n = sum(1 for s in data["samples"] if s["faces"])
    print(f"{len(data['samples'])} muestras, cara en {n} -> {a.out}")


if __name__ == "__main__":
    main()
