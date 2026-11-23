"""subtitulos: subtítulos animados estilo TikTok/Reels, 100% local.

    subtitulos "C:\\ruta con espacios\\video.mp4" [--style glide]
    subtitulos "C:\\...\\video.mp4" --stop-after transcribe          # solo transcribe (para revisar nombres)
    subtitulos "C:\\...\\video.mp4" --stop-after group               # páginas + highlights automáticos
    subtitulos "C:\\...\\video.mp4" --captions "C:\\...\\video.captions.json"   # re-render tras editar
    subtitulos --list-styles

Salidas junto al video (o en --out-dir):
    video.subtitulado.mp4  video.srt  video.captions.json  video.preview.jpg
Intermedios (transcripción, recortes, overlays) en la subcarpeta .subtitulos\\<nombre>\\
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import composite  # noqa: E402
import cuts as cuts_mod  # noqa: E402
import emphasis  # noqa: E402
import fuentes  # noqa: E402
import group  # noqa: E402
import legibility  # noqa: E402
import paths  # noqa: E402
import personalizar  # noqa: E402
import placement  # noqa: E402
import transcribe  # noqa: E402
import verify  # noqa: E402

ASPECTS = {"9:16": 9 / 16, "1:1": 1.0, "4:5": 4 / 5, "16:9": 16 / 9, "source": None}


def list_styles() -> str:
    rows = []
    for p in sorted(paths.STYLES.glob("*.json")):
        st = paths.read_json(p)
        behind = " (detrás)" if (st.get("behind") or {}).get("enabled") else ""
        rows.append(f"  {p.stem:<10} {st.get('description', '')}{behind}")
    return "Estilos (--style):\n" + "\n".join(rows)


def _key(p: Path) -> str:
    s = p.stat()
    return f"{s.st_size}-{s.st_mtime_ns}"


def prepare_source(video: Path, info: dict, aspect: str, work: Path) -> Path:
    """Recorta al centro a la proporción pedida (9:16 por defecto) y pasa a fps constante si hacía falta."""
    ratio = ASPECTS[aspect]
    w, h = info["width"], info["height"]
    crop = ratio is not None and abs(w / h - ratio) / ratio > 0.01
    if not crop and not info.get("vfr"):
        return video
    dst = work / "source.mp4"
    meta = work / "source.json"
    key = {"src": _key(video), "aspect": aspect}
    if dst.exists() and meta.exists() and paths.read_json(meta) == key:
        return dst
    vf = []
    if crop:
        if w / h > ratio:
            cw, ch = paths.even(h * ratio), h // 2 * 2
        else:
            cw, ch = w // 2 * 2, paths.even(w / ratio)
        vf.append(f"crop={cw}:{ch}:(iw-{cw})/2:(ih-{ch})/2")
        print(f"El video es {w}x{h}; se recorta al centro a {aspect} ({cw}x{ch}).", flush=True)
    else:
        print("El video tiene fps variable: se pasa a fps constante para que todo calce cuadro a cuadro.", flush=True)
    ffmpeg = paths.need("ffmpeg", "Gyan.FFmpeg")
    cmd = [ffmpeg, "-v", "error", "-y", "-i", video]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    cmd += ["-r", str(info["fps"]), "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p"]
    if info["hasAudio"]:
        cmd += ["-c:a", "copy"] if (info["audioCodec"] or "") in composite.MP4_AUDIO_OK else ["-c:a", "aac", "-b:a", "192k"]
    cmd += [dst]
    work.mkdir(parents=True, exist_ok=True)
    paths.run(cmd, capture=True)
    paths.write_json(meta, key)
    return dst


def cached(path: Path, key: str, build):
    """Reusa un JSON intermedio si se generó con la misma fuente."""
    if path.exists():
        d = paths.read_json(path)
        if d.get("_key") == key:
            return d
    d = build()
    d["_key"] = key
    paths.write_json(path, d, indent=None)
    return d


def render(cap_path: Path, style_path: Path, jobs: list[dict], work: Path) -> None:
    node = paths.need("node", "OpenJS.NodeJS.LTS")
    jp = paths.write_json(work / "render-jobs.json", jobs)
    t0 = time.time()
    print(f"Renderizando la capa de subtítulos con Remotion ({', '.join(j['layer'] for j in jobs)})...", flush=True)
    r = paths.run([node, paths.TEMPLATE / "render.mjs", "--batch", jp], cwd=paths.TEMPLATE, check=False)
    if r.returncode != 0:
        paths.die("el render de Remotion falló (mira el error de arriba)")
    print(f"  listo en {time.time() - t0:.0f} s", flush=True)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="subtitulos", description="Subtítulos animados estilo TikTok/Reels, 100% local.")
    ap.add_argument("video", nargs="?", type=Path, help="ruta del video (entre comillas si tiene espacios)")
    ap.add_argument("--style", help="glide (por defecto), bottom, karaoke, keyword o la ruta de un .json")
    g = ap.add_argument_group("personalizar (sirven con cualquier estilo)")
    g.add_argument("--font", help='tipografía del texto: "Bebas Neue", "Poppins:800" (se baja de Google Fonts si no está)')
    g.add_argument("--emphasis-font", help="tipografía de la palabra resaltada")
    g.add_argument("--big-font", help="tipografía de la palabra gigante (estilo keyword)")
    g.add_argument("--color", help='color del texto: blanco, "#FFFFFF"...')
    g.add_argument("--accent", help='color del highlight: rosa, "#FF4FA3" o auto (sacado del video)')
    g.add_argument("--stroke", help="color del contorno, o none")
    g.add_argument("--palette", help="paleta de colores.json: tiktok, neon, rosa, dorado... (--list-palettes)")
    g.add_argument("--size", help="multiplica el tamaño del texto: 1.2 = 20 %% más grande")
    g.add_argument("--case", choices=["upper", "lower", "sentence"], help="mayúsculas, minúsculas o como se dijo")
    ap.add_argument("--lang", default="es")
    ap.add_argument("--vocab", default="", help='nombres que whisper debe conocer: "Ana, TikTok, Canva"')
    ap.add_argument("--replace", action="append", help="oido=Mostrado (repetible)")
    ap.add_argument("--aspect", default="9:16", choices=list(ASPECTS))
    ap.add_argument("--emphasis", default="auto", choices=["auto", "numbers", "off"])
    ap.add_argument("--emphasis-words", help="'S/ 1,800 millones, gratis'")
    ap.add_argument("--behind", default="auto", choices=["auto", "on", "off"])
    ap.add_argument("--placement", default="auto", choices=["auto", "off"])
    ap.add_argument("--cuts", default="auto", choices=["auto", "off"])
    ap.add_argument("--legibility", default="auto", choices=["auto", "off"])
    ap.add_argument("--model", default=transcribe.DEFAULT_MODEL, help="large-v3-turbo (por defecto), small, medium...")
    ap.add_argument("--device", default=transcribe.DEFAULT_DEVICE, choices=["cpu", "cuda"])
    ap.add_argument("--stop-after", choices=["transcribe", "group"])
    ap.add_argument("--captions", type=Path, help="captions.json editado: re-render sin volver a transcribir")
    ap.add_argument("--words", type=Path, help="usar este words.json en vez de transcribir (pruebas)")
    ap.add_argument("--list-styles", action="store_true")
    ap.add_argument("--list-fonts", action="store_true")
    ap.add_argument("--list-palettes", action="store_true")
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--no-cache", action="store_true", help="volver a transcribir aunque esté en caché")
    return ap


def main(argv=None):
    paths.utf8_console()
    a = build_parser().parse_args(argv)
    if a.list_styles:
        print(list_styles())
        return 0
    if a.list_fonts:
        print(fuentes.list_text())
        return 0
    if a.list_palettes:
        print(personalizar.palettes_text())
        return 0
    if not a.video:
        paths.die('falta el video:  subtitulos "C:\\ruta\\video.mp4"')
    video = a.video.expanduser().resolve()
    if not video.exists():
        paths.die(f"no existe el video: {video}")
    o = paths.outputs(video, a.out_dir)
    work = o["work"]
    work.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    info0 = paths.probe(video)
    src = prepare_source(video, info0, a.aspect, work)
    info = paths.probe(src) if src != video else info0
    style_name = a.style
    prev = paths.read_json(a.captions) if a.captions and a.captions.exists() else None
    if not style_name and prev:
        style_name = prev.get("style")
    if not a.style and not a.captions:
        print("Estilo: glide (por defecto). Otros: bottom, karaoke, keyword  (--list-styles). "
              "Colores y letras: --palette, --accent, --font  (--list-palettes, --list-fonts)")
    # personalización: los flags de ahora, o los que se usaron la vez anterior si se re-renderiza sin flags
    overrides = personalizar.from_args(a)
    if not overrides and prev:
        overrides = prev.get("overrides") or {}
    style = personalizar.apply(paths.load_style(style_name or "glide"), overrides)

    if a.captions:
        if not a.captions.exists():
            paths.die(f"no existe {a.captions}")
        cap = paths.read_json(a.captions)
        v = cap["video"]
        if (v["width"], v["height"]) != (info["width"], info["height"]):
            paths.die(f"captions.json es de un video {v['width']}x{v['height']} y este es {info['width']}x{info['height']} "
                      f"(¿otro --aspect?)")
        cap["style"] = style["name"]
        cap["overrides"] = overrides
        cap["video"].update({"fps": info["fps"], "durationMs": info["durationMs"]})
        cap.setdefault("_page", group.page_params(style))
        group.regroup_lines(cap, style)
        group.set_page_ends(cap)
        emphasis.compute_big(cap, style)
        print(f"Re-render desde {a.captions} ({len(cap['pages'])} páginas): no se vuelve a transcribir.")
    else:
        if a.words:
            data = paths.read_json(a.words)
            data = transcribe.postprocess(data, a.replace)
            print(f"Palabras desde {a.words} (sin transcribir).")
        else:
            raw = transcribe.transcribe(src, lang=a.lang, model=a.model, device=a.device, vocab=a.vocab,
                                        use_cache=not a.no_cache)
            data = transcribe.postprocess(raw, a.replace)
        paths.write_json(o["words"], data)
        print("\n--- Transcripción ---")
        print(transcribe.transcript_text(data["words"]))
        print(f"--- {len(data['words'])} palabras  ({o['words']}) ---\n")
        if a.stop_after == "transcribe":
            print("Revisa nombres y marcas. Corrige con --vocab \"...\" (vuelve a transcribir) o --replace oido=Mostrado,\n"
                  "y sigue con --stop-after group.")
            return 0
        cuts = cuts_mod.detect(src) if a.cuts == "auto" else []
        if cuts:
            print(f"Cortes de toma: {', '.join(f'{c / 1000:.2f}s' for c in cuts)}")
        cap = group.build_captions(data["words"], style, info, cuts)
        cap["overrides"] = overrides
        emphasis.auto(cap, a.emphasis, a.vocab, a.emphasis_words, style)
        paths.write_json(o["captions"], cap)
        group.write_srt(cap, o["srt"])
        if a.stop_after == "group":
            print(emphasis.show(cap))
            print(f"\ncaptions: {o['captions']}\nsrt:      {o['srt']}")
            print("Ajusta highlights con scripts\\emphasis.py --pick/--drop y renderiza con --captions.")
            return 0

    notes: list[str] = []
    warns: list[str] = []
    key = _key(src)
    behind_on = bool((style.get("behind") or {}).get("enabled")) and a.behind != "off"
    subject = None
    if a.placement == "auto" or behind_on:
        import subject as subj

        print("Buscando cara y manos (MediaPipe)...", flush=True)
        subject = cached(work / "subject.json", key, lambda: subj.analyze(src, info))
    notes += placement.place(cap, style, subject, a.placement)

    matte_path = work / "matte.mkv"
    if behind_on:
        import matte as matte_mod
        import shots as shots_mod

        mkey = key + f"-{','.join(map(str, cap.get('cuts') or []))}"
        meta = work / "matte.json"
        mstats = paths.read_json(meta) if meta.exists() else {}
        if mstats.get("_key") != mkey or not matte_path.exists():
            print("Recortando a la persona cuadro a cuadro (MediaPipe)...", flush=True)
            mstats = matte_mod.make_matte(src, info, matte_path, cap.get("cuts"))
            mstats["_key"] = mkey
            paths.write_json(meta, mstats, indent=None)
        shots, n2, w2 = shots_mod.decide(cap, style, mstats, subject, a.behind)
        cap["shots"] = [{k: v for k, v in s.items()} for s in shots]
        notes += n2
        warns += w2
    elif (style.get("behind") or {}).get("enabled"):
        for b in cap.get("big") or []:
            b["front"] = True
        notes.append("--behind off: la palabra grande va delante")

    print("Midiendo legibilidad y color de acento...", flush=True)
    notes += legibility.analyze(cap, style, src, info, a.legibility)
    cap["notes"] = notes
    paths.write_json(o["captions"], cap)
    group.write_srt(cap, o["srt"])

    style_json = paths.write_json(work / "style.json", style)
    use_behind = behind_on and any(not b.get("front") for b in cap.get("big") or [])
    if use_behind:
        jobs = [{"captions": str(o["captions"]), "style": str(style_json), "layer": "behind", "out": str(work / "overlay-behind.mov")},
                {"captions": str(o["captions"]), "style": str(style_json), "layer": "front", "out": str(work / "overlay-front.mov")}]
    else:
        jobs = [{"captions": str(o["captions"]), "style": str(style_json), "layer": "all", "out": str(work / "overlay.mov")}]
    render(o["captions"], style_json, jobs, work)

    print("Componiendo el video final (ffmpeg)...", flush=True)
    if use_behind:
        composite.composite(src, o["mp4"], behind=work / "overlay-behind.mov", matte=matte_path, front=work / "overlay-front.mov")
    else:
        composite.composite(src, o["mp4"], overlay=work / "overlay.mov")
    for j in jobs:  # los .mov pesan mucho: se borran apenas se usan
        Path(j["out"]).unlink(missing_ok=True)

    res = verify.verify(src, o["mp4"], cap, style, o["preview"], work / "sheet", notes, warns)
    res["srt"] = str(o["srt"])
    res["captions"] = str(o["captions"])
    res["seconds"] = round(time.time() - t_start, 1)
    paths.write_json(work / "verify.json", res)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    print(f"\nListo: {o['mp4']}")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
