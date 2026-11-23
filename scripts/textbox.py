"""Estimación, en Python, de la caja que ocupará cada página en pantalla.

Replica la medida de template/src/engine/layout.ts con Pillow y las mismas fuentes de fonts\\, para que
placement.py, legibility.py y verify.py sepan dónde va a caer el texto sin abrir Chrome.
"""
from __future__ import annotations

from functools import lru_cache

import paths

SAFE_TOP = 0.17      # nada de texto por encima de y=330 en 1920 (perfil y búsqueda de TikTok)
SAFE_BOTTOM = 0.80   # el 20 % inferior lo tapan descripción y botones
SAFE_RIGHT = 0.12    # el 12 % derecho lo tapan los botones (me gusta, comentar...)


@lru_cache(maxsize=32)
def _font(file: str):
    from PIL import ImageFont

    return ImageFont.truetype(str(paths.FONTS / file), 200)


@lru_cache(maxsize=32)
def cap_height(file: str) -> float:
    b = _font(file).getbbox("H")
    v = (b[3] - b[1]) / 200
    return v if v > 0.3 else 0.7


def text_width(text: str, file: str, size: float) -> float:
    return _font(file).getlength(text) * size / 200


def apply_case(text: str, case: str, num: bool) -> str:
    if num:
        return text
    return text.upper() if case == "upper" else text.lower() if case == "lower" else text


def is_num(w: dict) -> bool:
    return bool(w.get("num")) or any(c.isdigit() for c in w["text"])


def word_spec(style: dict, w: dict) -> tuple[str, float]:
    """(archivo de fuente, multiplicador de tamaño) de una palabra, igual que el `spec` de cada estilo TSX."""
    t = (style.get("anim") or {}).get("type", style.get("name"))
    a = style.get("anim") or {}
    base = style["font"]["file"]
    if w.get("emphasis"):
        if t == "glide":
            if is_num(w) and style.get("numberFont"):
                return style["numberFont"]["file"], float(a.get("numberScale", 1.6))
            return (style.get("emphasisFont") or style["font"])["file"], float(a.get("scriptScale", 2.6))
        if t == "karaoke":
            return base, float(a.get("emphasisScale", 1.08))
    return base, 1.0


def safe_x(style: dict, W: int, H: int) -> tuple[float, float]:
    m = style["position"]["marginX"]
    right = m if W > H else max(m, SAFE_RIGHT * 100)
    return W * m / 100, W * (1 - right / 100)


def page_box(page: dict, style: dict, W: int, H: int, y_pct: float | None = None, skip: set[int] | None = None) -> dict:
    """Caja en px {x0, y0, x1, y1, shrink} de una página centrada en y_pct (o page.y o position.y)."""
    words = [w for i, w in enumerate(page["words"]) if not skip or i not in skip]
    if not words:
        return {"x0": 0, "y0": 0, "x1": 0, "y1": 0, "shrink": 1.0}
    wide = W > H
    fs = style["size"] / 100 * H * (1.35 if wide else 1)
    case = style.get("case", "sentence")
    base_file = style["font"]["file"]
    lines: dict[int, list[tuple[float, float, str]]] = {}
    for w in words:
        f, mul = word_spec(style, w)
        txt = apply_case(w["text"], case, is_num(w))
        lines.setdefault(int(w.get("line", 0)), []).append((text_width(txt, f, fs * mul), mul, f))
    space = text_width("n n", base_file, fs) - text_width("nn", base_file, fs)
    widths = {k: sum(x[0] for x in v) + space * (len(v) - 1) for k, v in lines.items()}
    xl, xr = safe_x(style, W, H)
    avail = xr - xl
    natural = max(widths.values())
    shrink = min(1.0, avail / natural * 0.99) if natural > 0 else 1.0
    fs *= shrink
    desc = fs * 0.3
    gap = fs * (style.get("lineHeight", 1.2) - 1)
    asc = [max(cap_height(f) * fs * mul for _, mul, f in v) for _, v in sorted(lines.items())]
    block_h = sum(a + desc for a in asc) + gap * (len(asc) - 1)
    block_w = natural * shrink
    y = y_pct if y_pct is not None else (page.get("y") if page.get("y") is not None else style["position"]["y"])
    cy = H * y / 100
    cx = (xl + xr) / 2
    return {"x0": cx - block_w / 2, "y0": cy - block_h / 2, "x1": cx + block_w / 2, "y1": cy + block_h / 2,
            "shrink": round(shrink, 3), "fs": fs}


def in_safe_zone(box: dict, W: int, H: int) -> bool:
    right = W * (1 - SAFE_RIGHT) if H > W else W
    return box["y0"] >= H * SAFE_TOP - 1 and box["y1"] <= H * SAFE_BOTTOM + 1 and box["x1"] <= right + 1


def overlaps(box: dict, norm_boxes: list[list[float]], W: int, H: int, margin: float = 0.015) -> bool:
    for x, y, w, h in norm_boxes:
        bx0, by0 = (x - margin) * W, (y - margin) * H
        bx1, by1 = (x + w + margin) * W, (y + h + margin) * H
        if box["x0"] < bx1 and box["x1"] > bx0 and box["y0"] < by1 and box["y1"] > by0:
            return True
    return False
