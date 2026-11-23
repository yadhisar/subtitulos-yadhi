"""Utilidades de rutas y procesos para Windows.

Reglas que sigue todo el repo:
- Rutas siempre con pathlib (soportan espacios y tildes: "C:\\...\\Campaña 2026\\video.mp4").
- subprocess siempre con una LISTA de argumentos, nunca shell=True ni strings concatenados.
- Todo lo que se descarga o se cachea vive en SUBTITULOS_HOME (por defecto %LOCALAPPDATA%\\subtitulos-yadhi).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
STYLES = REPO / "styles"
FONTS = REPO / "fonts"
TEMPLATE = REPO / "template"


def utf8_console() -> None:
    """La consola de Windows no siempre está en UTF-8: sin esto, 'subtítulos' sale como 'subtÃ­tulos'."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def home() -> Path:
    env = os.environ.get("SUBTITULOS_HOME")
    if env:
        return Path(env)
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "subtitulos-yadhi"


def models_dir() -> Path:
    return home() / "models"


def cache_dir() -> Path:
    return home() / "cache"


def outputs(video: Path, out_dir: Path | None = None) -> dict[str, Path]:
    """Nombres de salida junto al video (o en --out-dir). Los intermedios van a una subcarpeta oculta."""
    video = Path(video)
    out = Path(out_dir) if out_dir else video.parent
    stem = video.stem
    work = out / ".subtitulos" / stem
    return {
        "dir": out,
        "work": work,
        "mp4": out / f"{stem}.subtitulado.mp4",
        "srt": out / f"{stem}.srt",
        "captions": out / f"{stem}.captions.json",
        "preview": out / f"{stem}.preview.jpg",
        "words": work / "words.json",
    }


def which(tool: str) -> str | None:
    return shutil.which(tool)


def need(tool: str, winget_id: str) -> str:
    p = which(tool)
    if not p:
        die(f"No encuentro '{tool}'. Instálalo con:  winget install -e --id {winget_id}")
    return p


def die(msg: str, code: int = 1):
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def warn(msg: str) -> None:
    print(f"AVISO: {msg}", file=sys.stderr)


def run(cmd: list, *, capture: bool = False, cwd: Path | None = None, check: bool = True,
        binary: bool = False) -> subprocess.CompletedProcess:
    """Corre un comando como lista de argumentos (sin shell). binary=True devuelve stdout en bytes."""
    cmd = [str(c) for c in cmd]
    if binary:
        r = subprocess.run(cmd, cwd=str(cwd) if cwd else None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if check and r.returncode != 0:
            die(f"falló: {Path(cmd[0]).name} (código {r.returncode})")
        return r
    r = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=capture,
        text=capture,
        encoding="utf-8" if capture else None,
        errors="replace" if capture else None,
    )
    if check and r.returncode != 0:
        tail = ""
        if capture:
            tail = "\n" + "\n".join(((r.stderr or "") + (r.stdout or "")).strip().splitlines()[-15:])
        die(f"falló: {Path(cmd[0]).name} (código {r.returncode}){tail}")
    return r


def sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _fps(rate: str | None) -> float | None:
    if not rate or rate in ("0/0", "0"):
        return None
    try:
        v = float(Fraction(rate))
    except (ValueError, ZeroDivisionError):
        return None
    return v if v > 0 else None


def probe(video: Path) -> dict:
    """Ancho, alto, fps, duración y audio de un video (ffprobe)."""
    ffprobe = need("ffprobe", "Gyan.FFmpeg")
    r = run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", video], capture=True)
    data = json.loads(r.stdout)
    vs = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if not vs:
        die(f"'{video}' no tiene pista de video")
    aus = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
    w, h = int(vs["width"]), int(vs["height"])
    rot = 0
    for sd in vs.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(round(float(sd["rotation"])))
    if (vs.get("tags") or {}).get("rotate"):
        rot = int(vs["tags"]["rotate"])
    if abs(rot) % 180 == 90:  # video de celular grabado "de lado": ffmpeg lo endereza al decodificar
        w, h = h, w
    avg = _fps(vs.get("avg_frame_rate"))
    rr = _fps(vs.get("r_frame_rate"))
    fps = avg or rr or 30.0
    vfr = bool(avg and rr and abs(avg - rr) / rr > 0.01)
    fps = round(fps, 3)
    dur = vs.get("duration") or data.get("format", {}).get("duration") or "0"
    dur_ms = int(round(float(dur) * 1000))
    nb = vs.get("nb_frames")
    return {
        "width": w,
        "height": h,
        "fps": fps,
        "durationMs": dur_ms,
        "frames": int(nb) if nb and str(nb).isdigit() else int(round(dur_ms * fps / 1000)),
        "hasAudio": bool(aus),
        "audioCodec": aus[0].get("codec_name") if aus else None,
        "videoCodec": vs.get("codec_name"),
        "vfr": vfr,
    }


def scaled_size(info: dict, width: int) -> tuple[int, int]:
    w = min(width, info["width"]) // 2 * 2
    h = max(2, int(round(info["height"] * w / info["width"] / 2)) * 2)
    return w, h


def iter_frames(video: Path, info: dict, width: int, fps: float | None = None):
    """Cuadros RGB (numpy HxWx3) leídos con ffmpeg por una tubería.

    OpenCV no abre rutas con tildes en Windows; ffmpeg sí. Con fps=None salen todos los cuadros del video.
    Devuelve (índice, ms, cuadro).
    """
    import numpy as np

    ffmpeg = need("ffmpeg", "Gyan.FFmpeg")
    w, h = scaled_size(info, width)
    vf = f"scale={w}:{h}:flags=area"
    if fps:
        vf = f"fps={fps}," + vf
    cmd = [ffmpeg, "-v", "error", "-i", str(video), "-an", "-vf", vf]
    if not fps:
        cmd += ["-fps_mode", "passthrough"]
    cmd += ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    size = w * h * 3
    step = 1000.0 / (fps or info["fps"])
    i = 0
    try:
        while True:
            buf = p.stdout.read(size)
            if len(buf) < size:
                break
            yield i, int(round(i * step)), np.frombuffer(buf, np.uint8).reshape(h, w, 3)
            i += 1
    finally:
        p.stdout.close()
        p.wait()


def even(x: float) -> int:
    return max(2, int(round(x / 2)) * 2)


def read_json(p: Path):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(p: Path, data, indent: int | None = 2) -> Path:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
        f.write("\n")
    os.replace(tmp, p)
    return p


def load_style(name_or_path: str) -> dict:
    """--style glide  o  --style C:\\ruta\\mi-estilo.json"""
    p = Path(name_or_path)
    if p.suffix.lower() != ".json":
        p = STYLES / f"{name_or_path}.json"
    if not p.exists():
        names = ", ".join(sorted(x.stem for x in STYLES.glob("*.json")))
        die(f"no existe el estilo '{name_or_path}'. Estilos: {names}")
    st = read_json(p)
    st.setdefault("name", p.stem)
    return st


def ms_to_srt(ms: int) -> str:
    ms = max(0, int(ms))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
