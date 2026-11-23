"""Contraste solo donde hace falta + color de acento sacado del video.

    uv run python scripts\\legibility.py video.captions.json --video "C:\\...\\video.mp4"

- Para cada página mide la luminancia y el contraste del fondo justo detrás del texto (en el cuadro del medio
  de la página). Si el texto no se lee (fondo claro o muy cargado), le pone a ESA página el tratamiento del
  estilo (legibility.mode: halo, scrim u outline) con una fuerza 0..1 (tope legibility.max). Las demás no
  llevan nada.
- Paleta: busca el tono dominante del video y elige un acento que contraste con él (tono opuesto, claro y
  saturado). Los colores del estilo escritos como {"auto": "accent", "fallback": "#..."} lo usan.
"""
from __future__ import annotations

import argparse
import colorsys
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import textbox  # noqa: E402

TARGET = 4.5  # contraste mínimo tipo WCAG entre el texto y lo más claro del fondo


def _lum(rgb):
    import numpy as np

    c = rgb.astype(np.float32) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def _hex_lum(color: str) -> float:
    s = (color or "#ffffff").strip().lstrip("#")
    if len(s) != 6:
        return 1.0
    import numpy as np

    return float(_lum(np.array([[[int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)]]], dtype=np.uint8))[0, 0])


def accent_from(frames) -> str | None:
    import numpy as np

    hist = np.zeros(36)
    for fr in frames:
        small = fr[::4, ::4].reshape(-1, 3).astype(np.float32) / 255.0
        mx, mn = small.max(1), small.min(1)
        s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
        keep = (s > 0.3) & (mx > 0.3)
        if not keep.any():
            continue
        px_ = small[keep]
        r, g, b = px_[:, 0], px_[:, 1], px_[:, 2]
        mxk, mnk = mx[keep], mn[keep]
        d = np.maximum(mxk - mnk, 1e-6)
        h = np.where(mxk == r, ((g - b) / d) % 6, np.where(mxk == g, (b - r) / d + 2, (r - g) / d + 4)) / 6
        np.add.at(hist, (h * 36).astype(int) % 36, s[keep] * mxk)
    if hist.sum() <= 0:
        return None
    h0 = (hist.argmax() + 0.5) / 36
    h = (h0 + 0.5) % 1.0
    r, g, b = colorsys.hsv_to_rgb(h, 0.5, 1.0)
    return "#{:02X}{:02X}{:02X}".format(int(r * 255), int(g * 255), int(b * 255))


def analyze(cap: dict, style: dict, video: Path, info: dict, mode: str = "auto") -> list[str]:
    import numpy as np

    W, H = cap["video"]["width"], cap["video"]["height"]
    notes: list[str] = []
    lg = style.get("legibility") or {"mode": "halo", "max": 1}
    sample_fps = 2.0
    frames = {}
    for _, ms, fr in paths.iter_frames(video, info, 360, fps=sample_fps):
        frames[ms] = fr
    if not frames:
        return notes
    keys = sorted(frames)
    pal = accent_from([frames[k] for k in keys[:: max(1, len(keys) // 24)]])
    if pal:
        cap["palette"] = {"accent": pal}
        notes.append(f"color de acento del video: {pal}")
    text_l = _hex_lum(style.get("color", "#FFFFFF") if isinstance(style.get("color"), str) else "#FFFFFF")
    fixed = 0
    for k, p in enumerate(cap["pages"]):
        p["legibility"] = None
        mid = (p["startMs"] + p["endMs"]) / 2
        near = min(keys, key=lambda t: abs(t - mid))
        fr = frames[near]
        sh, sw = fr.shape[:2]
        b = textbox.page_box(p, style, W, H)
        x0, x1 = int(max(0, b["x0"] / W * sw)), int(min(sw, b["x1"] / W * sw))
        y0, y1 = int(max(0, b["y0"] / H * sh)), int(min(sh, b["y1"] / H * sh))
        if x1 - x0 < 2 or y1 - y0 < 2:
            continue
        L = _lum(fr[y0:y1, x0:x1])
        bright = float(np.percentile(L, 90))
        busy = float(L.std())
        if text_l > 0.5:
            contrast = (text_l + 0.05) / (bright + 0.05)
        else:
            contrast = (float(np.percentile(L, 10)) + 0.05) / (text_l + 0.05)
        p["contrast"] = round(contrast, 2)
        if mode == "off":
            continue
        need = max(0.0, (TARGET - contrast) / (TARGET - 1.2)) + max(0.0, busy - 0.18) * 2
        if need > 0.05:
            p["legibility"] = {"mode": lg.get("mode", "halo"), "strength": round(min(float(lg.get("max", 1)), max(0.25, need)), 2)}
            fixed += 1
    if fixed:
        notes.append(f"contraste añadido en {fixed} de {len(cap['pages'])} páginas ({lg.get('mode', 'halo')})")
    return notes


def main(argv=None):
    paths.utf8_console()
    ap = argparse.ArgumentParser(description="Mide la legibilidad y elige el color de acento")
    ap.add_argument("captions", type=Path)
    ap.add_argument("--video", type=Path, required=True)
    ap.add_argument("--mode", default="auto", choices=["auto", "off"])
    a = ap.parse_args(argv)
    cap = paths.read_json(a.captions)
    style = paths.load_style(cap["style"])
    notes = analyze(cap, style, a.video, paths.probe(a.video), a.mode)
    paths.write_json(a.captions, cap)
    print("\n".join(notes) or "todo se lee sin ayuda")


if __name__ == "__main__":
    main()
