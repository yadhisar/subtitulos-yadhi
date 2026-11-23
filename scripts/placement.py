"""Mueve los subtítulos fuera de la cara y las manos, solo si hace falta, dentro de la zona segura de TikTok.

    uv run python scripts\\placement.py video.captions.json --subject subject.json [--style glide]

Cómo decide:
1. Busca UNA altura para todo el video (dentro de position.flex del estilo) que no tape la cara en la mayoría de
   páginas, lo más cerca posible de la altura del estilo. Una altura fija se lee mejor que texto que salta.
2. Solo las páginas que aún chocan con la cara o las manos se mueven a la altura libre más cercana; se anotan.
3. Nunca deja texto por encima del 17 % ni en el 20 % inferior ni en el 12 % derecho (zona segura de TikTok).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import subject as subj  # noqa: E402
import textbox  # noqa: E402


def _range(style: dict) -> tuple[float, float]:
    y0 = style["position"]["y"]
    flex = style["position"].get("flex")
    if flex == 0:
        return y0, y0
    if isinstance(flex, (list, tuple)) and len(flex) == 2:
        return float(flex[0]), float(flex[1])
    return max(0.0, y0 - 15), min(100.0, y0 + 15)


def _candidates(lo: float, hi: float, y0: float) -> list[float]:
    ys = [round(lo + k * 0.5, 2) for k in range(int((hi - lo) / 0.5) + 1)]
    return sorted(ys, key=lambda y: (abs(y - y0), y))


def _fits(page, style, W, H, y, boxes) -> bool:
    b = textbox.page_box(page, style, W, H, y)
    return textbox.in_safe_zone(b, W, H) and not textbox.overlaps(b, boxes, W, H)


def place(cap: dict, style: dict, subject: dict | None, mode: str = "auto") -> list[str]:
    W, H = cap["video"]["width"], cap["video"]["height"]
    notes: list[str] = []
    y0 = style["position"]["y"]
    lo, hi = _range(style)
    for p in cap["pages"]:
        p["y"] = None
    cands = _candidates(lo, hi, y0)
    # la altura del estilo, corregida si por sí sola ya cae fuera de la zona segura
    safe_cands = [y for y in cands if all(textbox.in_safe_zone(textbox.page_box(p, style, W, H, y), W, H) for p in cap["pages"])]
    if not safe_cands:
        safe_cands = cands
    if mode == "off" or not subject:
        y = safe_cands[0]
        if y != y0:
            for p in cap["pages"]:
                p["y"] = y
            notes.append(f"altura ajustada a {y}% para quedar dentro de la zona segura")
        return notes
    page_boxes = [subj.boxes_between(subject, p["startMs"], p["endMs"]) for p in cap["pages"]]
    face_boxes = [subj.boxes_between(subject, p["startMs"], p["endMs"], hands=False) for p in cap["pages"]]

    def cost(y):
        hits = sum(1 for p, fb in zip(cap["pages"], face_boxes) if not _fits(p, style, W, H, y, fb))
        return hits * 1000 + abs(y - y0)

    gy = min(safe_cands, key=cost)
    if gy != y0:
        notes.append(f"altura general {gy}% (el estilo pide {y0}%) para no tapar la cara")
    moved = 0
    for k, (p, boxes) in enumerate(zip(cap["pages"], page_boxes)):
        p["y"] = gy
        if _fits(p, style, W, H, gy, boxes):
            continue
        alt = next((y for y in _candidates(lo, hi, gy) if _fits(p, style, W, H, y, boxes)), None)
        if alt is None:
            # sin altura libre de cara y manos: al menos libre de la cara
            alt = next((y for y in _candidates(lo, hi, gy) if _fits(p, style, W, H, y, face_boxes[k])), None)
        if alt is not None and alt != gy:
            p["y"] = alt
            moved += 1
            notes.append(f"página {k + 1} movida a {alt}% (cara/manos)")
        elif alt is None:
            notes.append(f"página {k + 1}: no hay altura libre de la cara dentro del rango del estilo")
    if moved:
        notes.append(f"{moved} página(s) movida(s) por cara/manos")
    return notes


def main(argv=None):
    paths.utf8_console()
    ap = argparse.ArgumentParser(description="Saca los subtítulos de encima de la cara y las manos")
    ap.add_argument("captions", type=Path)
    ap.add_argument("--subject", type=Path)
    ap.add_argument("--style")
    ap.add_argument("--mode", default="auto", choices=["auto", "off"])
    a = ap.parse_args(argv)
    cap = paths.read_json(a.captions)
    style = paths.load_style(a.style or cap["style"])
    sub = paths.read_json(a.subject) if a.subject else None
    notes = place(cap, style, sub, a.mode)
    paths.write_json(a.captions, cap)
    print("\n".join(notes) or "sin cambios")


if __name__ == "__main__":
    main()
