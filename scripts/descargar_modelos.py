"""Descarga una sola vez los modelos de MediaPipe a %LOCALAPPDATA%\\subtitulos-yadhi\\models.

    uv run python scripts\\descargar_modelos.py [--force]

- selfie_multiclass_256x256.tflite  segmentación de persona (pelo, cuerpo, ropa) para el texto "detrás de ti"
- selfie_segmenter.tflite           segmentación rápida (respaldo)
- blaze_face_short_range.tflite     detector de caras (para no tapar la cara)
- hand_landmarker.task              manos (para no tapar las manos)
Son de Google (Apache 2.0). Nada se sube: solo se descargan.
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

BASE = "https://storage.googleapis.com/mediapipe-models"
MODELS = {
    "selfie_multiclass_256x256.tflite": f"{BASE}/image_segmenter/selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite",
    "selfie_segmenter.tflite": f"{BASE}/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite",
    "blaze_face_short_range.tflite": f"{BASE}/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite",
    "hand_landmarker.task": f"{BASE}/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
}


def model_path(name: str) -> Path:
    return paths.models_dir() / name


def missing() -> list[str]:
    return [n for n in MODELS if not model_path(n).exists() or model_path(n).stat().st_size == 0]


def download(force: bool = False) -> None:
    d = paths.models_dir()
    d.mkdir(parents=True, exist_ok=True)
    for name, url in MODELS.items():
        dst = d / name
        if dst.exists() and dst.stat().st_size > 0 and not force:
            print(f"[ya está] {name}")
            continue
        print(f"[bajando] {name} ...", flush=True)
        tmp = dst.with_name(dst.name + ".part")
        req = urllib.request.Request(url, headers={"User-Agent": "subtitulos-yadhi"})
        with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
            while True:
                b = r.read(1 << 16)
                if not b:
                    break
                f.write(b)
        tmp.replace(dst)
        print(f"          {dst.stat().st_size / 1e6:.1f} MB -> {dst}")
    print(f"Modelos listos en {d}")


def require() -> None:
    m = missing()
    if m:
        paths.die(f"faltan modelos de MediaPipe ({', '.join(m)}). Córrelo una vez:  uv run python scripts\\descargar_modelos.py")


def main(argv=None):
    paths.utf8_console()
    ap = argparse.ArgumentParser(description="Descarga los modelos de MediaPipe")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    download(a.force)


if __name__ == "__main__":
    main()
