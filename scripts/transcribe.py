"""Transcripción local con faster-whisper, con tiempos por palabra.

    uv run python scripts\\transcribe.py "C:\\ruta con espacios\\video.mp4" --out words.json [--vocab "Ana, TikTok"]

- Caché por SHA-256 del archivo (+ modelo, idioma y vocabulario) en %LOCALAPPDATA%\\subtitulos-yadhi\\cache:
  la segunda corrida sobre el mismo video no vuelve a transcribir.
- --device cuda usa float16; si CUDA/cuDNN no está, avisa y sigue en CPU (int8).
- Salida words.json = {language, model, words:[{text,startMs,endMs,prob}]}: texto sin espacios al borde,
  puntuación pegada a la palabra. Luego se aplican --replace y los números hablados (numeros.py).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numeros  # noqa: E402
import paths  # noqa: E402

DEFAULT_MODEL = os.environ.get("SUBTITULOS_MODEL", "large-v3-turbo")
DEFAULT_DEVICE = os.environ.get("SUBTITULOS_DEVICE", "cpu")
PUNCT_ONLY = set(".,;:!?¿¡…\"'«»“”‘’()-–—")


def _cache_path(sha: str, model: str, lang: str, vocab: str) -> Path:
    key = hashlib.sha256(f"{model}|{lang}|{vocab}".encode("utf-8")).hexdigest()[:10]
    safe_model = model.replace("/", "_").replace("\\", "_")
    return paths.cache_dir() / f"{sha[:24]}-{safe_model}-{lang}-{key}.json"


def load_audio(video: Path, sr: int = 16000):
    """Audio mono 16 kHz float32 con ffmpeg (no depende de la versión de PyAV ni de la ruta)."""
    import numpy as np

    ffmpeg = paths.need("ffmpeg", "Gyan.FFmpeg")
    r = paths.run([ffmpeg, "-v", "error", "-nostdin", "-i", str(video), "-vn", "-ac", "1", "-ar", str(sr),
                   "-f", "f32le", "-"], capture=False, check=False, binary=True)
    if r.returncode != 0 or not r.stdout:
        paths.die(f"no pude leer el audio de {video}")
    return np.frombuffer(r.stdout, np.float32).copy()


def _run_whisper(audio, model: str, device: str, lang: str, vocab: str) -> tuple[list[dict], str]:
    from faster_whisper import WhisperModel

    compute = "float16" if device == "cuda" else "int8"
    root = paths.models_dir() / "whisper"
    root.mkdir(parents=True, exist_ok=True)
    print(f"Transcribiendo con {model} en {device} ({compute})... la primera vez descarga el modelo.", flush=True)
    wm = WhisperModel(model, device=device, compute_type=compute, download_root=str(root))
    prompt = f"Vocabulario: {vocab}." if vocab.strip() else None
    segments, info = wm.transcribe(
        audio,
        language=lang or None,
        word_timestamps=True,
        vad_filter=True,
        initial_prompt=prompt,
        beam_size=5,
        condition_on_previous_text=False,
    )
    words: list[dict] = []
    for seg in segments:  # el generador corre aquí: un fallo de CUDA aparece en este bucle
        for w in seg.words or []:
            t = (w.word or "").strip()
            if not t:
                continue
            if all(c in PUNCT_ONLY for c in t) and words:
                words[-1]["text"] += t
                continue
            s = int(round(w.start * 1000))
            e = int(round(w.end * 1000))
            if words and s < words[-1]["startMs"]:
                s = words[-1]["startMs"]
            words.append({"text": t, "startMs": s, "endMs": max(e, s + 1), "prob": round(float(w.probability), 3)})
    return words, info.language


def transcribe(video: Path, *, lang: str = "es", model: str = DEFAULT_MODEL, device: str = DEFAULT_DEVICE,
               vocab: str = "", use_cache: bool = True) -> dict:
    video = Path(video)
    info = paths.probe(video)
    sha = paths.sha256(video)
    cp = _cache_path(sha, model, lang or "auto", vocab)
    if use_cache and cp.exists():
        data = paths.read_json(cp)
        print(f"Transcripción desde caché ({cp.name}): no se vuelve a transcribir.", flush=True)
        return data
    t0 = time.time()
    audio = load_audio(video)
    try:
        words, language = _run_whisper(audio, model, device, lang, vocab)
        used = device
    except Exception as e:  # noqa: BLE001
        if device != "cuda":
            raise
        paths.warn(f"CUDA no funcionó ({type(e).__name__}: {str(e)[:160]}). Sigo en CPU (int8), será más lento. "
                   "Para usar la GPU hacen falta cuBLAS y cuDNN 9 para CUDA 12 (ver README, sección CUDA).")
        words, language = _run_whisper(audio, model, "cpu", lang, vocab)
        used = "cpu"
    data = {
        "version": 1,
        "source": {"sha256": sha, "durationMs": info["durationMs"], "fps": info["fps"],
                   "width": info["width"], "height": info["height"]},
        "language": language,
        "model": model,
        "device": used,
        "seconds": round(time.time() - t0, 1),
        "words": words,
    }
    paths.write_json(cp, data)
    return data


def parse_replace(items: list[str] | None) -> list[tuple[list[str], list[str]]]:
    """--replace "oido=Mostrado" (repetible). Lo de la izquierda puede tener varias palabras."""
    rules = []
    for it in items or []:
        if "=" not in it:
            paths.die(f"--replace necesita la forma oido=Mostrado (recibí '{it}')")
        heard, shown = it.split("=", 1)
        h = [numeros.norm(x) for x in heard.split() if numeros.norm(x)]
        s = shown.split()
        if h and s:
            rules.append((h, s))
    return rules


def apply_replace(words: list[dict], rules) -> list[dict]:
    if not rules:
        return words
    out: list[dict] = []
    i = 0
    norms = [numeros.norm(w["text"]) for w in words]
    while i < len(words):
        hit = None
        for heard, shown in rules:
            n = len(heard)
            if norms[i:i + n] == heard:
                hit = (n, shown)
                break
        if not hit:
            out.append(dict(words[i]))
            i += 1
            continue
        n, shown = hit
        span = words[i:i + n]
        lead = numeros._split_punct(span[0]["text"])[0]
        trail = numeros._split_punct(span[-1]["text"])[2]
        s, e = span[0]["startMs"], span[-1]["endMs"]
        step = (e - s) / len(shown)
        for k, t in enumerate(shown):
            txt = (lead if k == 0 else "") + t + (trail if k == len(shown) - 1 else "")
            out.append({"text": txt, "startMs": int(s + k * step), "endMs": int(s + (k + 1) * step),
                        "prob": min(w.get("prob", 1) for w in span)})
        i += n
    return out


def postprocess(data: dict, replace: list[str] | None = None, numbers: bool = True) -> dict:
    words = apply_replace(data["words"], parse_replace(replace))
    if numbers:
        words = numeros.convert_words(words)
    return {**data, "words": words}


def transcript_text(words: list[dict]) -> str:
    return " ".join(w["text"] for w in words)


def main(argv=None):
    paths.utf8_console()
    ap = argparse.ArgumentParser(description="Transcribe un video con tiempos por palabra (faster-whisper).")
    ap.add_argument("video", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--lang", default="es")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--device", default=DEFAULT_DEVICE, choices=["cpu", "cuda"])
    ap.add_argument("--vocab", default="")
    ap.add_argument("--replace", action="append")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--raw", action="store_true", help="sin --replace ni números (tal cual sale de whisper)")
    a = ap.parse_args(argv)
    if not a.video.exists():
        paths.die(f"no existe el video: {a.video}")
    data = transcribe(a.video, lang=a.lang, model=a.model, device=a.device, vocab=a.vocab, use_cache=not a.no_cache)
    if not a.raw:
        data = postprocess(data, a.replace)
    paths.write_json(a.out, data)
    print(transcript_text(data["words"]))
    print(f"\n{len(data['words'])} palabras -> {a.out}")


if __name__ == "__main__":
    main()
