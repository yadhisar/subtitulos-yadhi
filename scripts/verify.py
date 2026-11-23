"""Revisa el resultado y arma la hoja de contacto (preview.jpg).

    uv run python scripts\\verify.py --video original.mp4 --out video.subtitulado.mp4 --captions video.captions.json --preview video.preview.jpg

JSON de salida:
  ok        true si el video final tiene el mismo tamaño, fps, duración (±1 cuadro) y audio que el original
  warnings  zona segura, contraste bajo, línea desbordada, palabra grande casi oculta...
  notes     páginas movidas, cortes, tomas aptas para "detrás"...
  preview   ruta de la hoja de contacto: 6-9 cuadros del video final con la zona segura de TikTok dibujada
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import group  # noqa: E402
import paths  # noqa: E402
import textbox  # noqa: E402


def check_output(src: dict, out: dict) -> tuple[bool, list[str]]:
    errs = []
    if (src["width"], src["height"]) != (out["width"], out["height"]):
        errs.append(f"tamaño distinto: {src['width']}x{src['height']} -> {out['width']}x{out['height']}")
    if abs(src["fps"] - out["fps"]) > 0.02:
        errs.append(f"fps distinto: {src['fps']} -> {out['fps']}")
    frame_ms = 1000 / src["fps"]
    if abs(src["durationMs"] - out["durationMs"]) > frame_ms + 1:
        errs.append(f"duración distinta: {src['durationMs']} ms -> {out['durationMs']} ms")
    if src["hasAudio"] and not out["hasAudio"]:
        errs.append("se perdió el audio")
    return not errs, errs


def caption_warnings(cap: dict, style: dict) -> list[str]:
    W, H = cap["video"]["width"], cap["video"]["height"]
    warns = []
    for k, p in enumerate(cap["pages"], 1):
        b = textbox.page_box(p, style, W, H)
        if H > W and not textbox.in_safe_zone(b, W, H):
            warns.append(f"página {k} fuera de la zona segura de TikTok ({group.page_text(p, ' ')})")
        if b["shrink"] < 0.7:
            warns.append(f"página {k}: línea desbordada, se achicó al {b['shrink']:.0%} ({group.page_text(p, ' ')})")
        c = p.get("contrast")
        lg = p.get("legibility")
        if c is not None and c < 2.0 and (not lg or lg.get("strength", 0) < 0.6):
            warns.append(f"página {k}: contraste bajo ({c}:1) sin tratamiento suficiente")
    return warns


def _times_for_sheet(cap: dict, n: int = 9) -> list[tuple[int, str]]:
    pages = cap["pages"]
    if not pages:
        d = cap["video"]["durationMs"]
        return [(int(d * (k + 0.5) / 6), "") for k in range(6)]
    n = max(6, min(n, len(pages)))
    pref = [i for i, p in enumerate(pages) if any(w.get("emphasis") for w in p["words"])]
    chosen = set()
    step = len(pages) / n
    for k in range(n):
        lo, hi = int(k * step), max(int(k * step) + 1, int((k + 1) * step))
        cand = [i for i in pref if lo <= i < hi] or list(range(lo, min(hi, len(pages))))
        if cand:
            chosen.add(cand[0])
    out = []
    for i in sorted(chosen)[:n]:
        p = pages[i]
        # con todas las palabras ya en pantalla y antes de que la página empiece a desvanecerse
        t = min(p["endMs"] - 200, max(w["endMs"] for w in p["words"]) + 40)
        out.append((max(p["startMs"] + 40, int(t)), f"{i + 1}"))
    return out


def contact_sheet(video: Path, cap: dict, dst: Path, work: Path) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    label_font = ImageFont.truetype(str(paths.FONTS / "Inter-Medium.ttf"), 14)
    ffmpeg = paths.need("ffmpeg", "Gyan.FFmpeg")
    W, H = cap["video"]["width"], cap["video"]["height"]
    tw = 360 if H >= W else 480
    th = int(round(H * tw / W))
    shots = []
    work.mkdir(parents=True, exist_ok=True)
    for k, (ms, label) in enumerate(_times_for_sheet(cap)):
        png = work / f"sheet_{k}.png"
        paths.run([ffmpeg, "-v", "error", "-y", "-ss", f"{ms / 1000:.3f}", "-i", video, "-frames:v", "1",
                   "-vf", f"scale={tw}:{th}", png], capture=True, check=False)
        if png.exists():
            shots.append((png, ms, label))
    cols = 3
    rows = max(1, (len(shots) + cols - 1) // cols)
    pad, head = 10, 26
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * pad, rows * (th + head) + (rows + 1) * pad), (24, 24, 24))
    for k, (png, ms, label) in enumerate(shots):
        im = Image.open(png).convert("RGBA")
        ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        if H > W:  # zona segura de TikTok
            red = (255, 40, 40, 70)
            d.rectangle([0, 0, tw, int(th * textbox.SAFE_TOP)], fill=red)
            d.rectangle([0, int(th * textbox.SAFE_BOTTOM), tw, th], fill=red)
            d.rectangle([int(tw * (1 - textbox.SAFE_RIGHT)), int(th * textbox.SAFE_TOP), tw, int(th * textbox.SAFE_BOTTOM)], fill=red)
            d.rectangle([0, int(th * textbox.SAFE_TOP), int(tw * (1 - textbox.SAFE_RIGHT)), int(th * textbox.SAFE_BOTTOM)],
                        outline=(255, 80, 80, 200), width=1)
        im = Image.alpha_composite(im, ov).convert("RGB")
        r, c = divmod(k, cols)
        x = pad + c * (tw + pad)
        y = pad + r * (th + head + pad)
        sheet.paste(im, (x, y + head))
        t = ms / 1000
        ImageDraw.Draw(sheet).text((x + 2, y + 6), f"{int(t // 60):02d}:{t % 60:05.2f}  pág {label}", fill=(230, 230, 230),
                                    font=label_font)
        png.unlink(missing_ok=True)
    dst.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dst, quality=90)
    return dst


def verify(src_video: Path, out_video: Path, cap: dict, style: dict, preview: Path, work: Path,
           notes: list[str] | None = None, warnings: list[str] | None = None) -> dict:
    src = paths.probe(src_video)
    out = paths.probe(out_video)
    ok, errs = check_output(src, out)
    warns = list(warnings or []) + caption_warnings(cap, style)
    nts = list(notes or [])
    cuts = cap.get("cuts") or []
    nts.append(f"{len(cap['pages'])} páginas, {len(cuts)} corte(s) de toma")
    contact_sheet(out_video, cap, preview, work)
    return {"ok": ok, "errors": errs, "warnings": warns, "notes": nts, "preview": str(preview), "video": str(out_video),
            "source": {k: src[k] for k in ("width", "height", "fps", "durationMs", "hasAudio")},
            "output": {k: out[k] for k in ("width", "height", "fps", "durationMs", "hasAudio")}}


def main(argv=None):
    paths.utf8_console()
    ap = argparse.ArgumentParser(description="Verifica el video subtitulado y arma la hoja de contacto")
    ap.add_argument("--video", type=Path, required=True, help="video de entrada (o el recortado a 9:16)")
    ap.add_argument("--out", type=Path, required=True, help="video subtitulado")
    ap.add_argument("--captions", type=Path, required=True)
    ap.add_argument("--preview", type=Path, required=True)
    a = ap.parse_args(argv)
    cap = paths.read_json(a.captions)
    style = paths.load_style(cap["style"])
    import json

    res = verify(a.video, a.out, cap, style, a.preview, a.preview.parent / ".subtitulos" / "sheet")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res["ok"] else 1)


if __name__ == "__main__":
    main()
