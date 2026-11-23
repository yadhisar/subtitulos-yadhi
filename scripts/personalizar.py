"""Cambia tipografías, colores y tamaño de cualquier estilo desde la línea de comandos.

    --font "Bebas Neue"          tipografía del texto (cualquiera de fonts\\ o de Google Fonts; "Familia:800" elige peso)
    --emphasis-font "Pacifico"   tipografía de la palabra resaltada (en glide, la caligráfica)
    --big-font "Anton"           tipografía de la palabra gigante (estilo keyword)
    --color blanco | "#FFFFFF"   color del texto
    --accent rosa | "#FF4FA3" | auto   color del highlight (auto = sacado del video)
    --stroke negro | none        contorno
    --palette tiktok             paleta de colores.json (los flags sueltos mandan sobre la paleta)
    --size 1.2                   multiplica el tamaño del texto
    --case upper|lower|sentence  mayúsculas / minúsculas / como se dijo

Los colores aceptan hex (#RGB o #RRGGBB) o un nombre de colores.json (en español o inglés).
"""
from __future__ import annotations

import copy
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fuentes  # noqa: E402
import paths  # noqa: E402

KEYS = ("font", "emphasis_font", "big_font", "color", "accent", "stroke", "palette", "size", "case")


def colores() -> dict:
    return paths.read_json(paths.REPO / "colores.json")


def parse_color(value: str) -> str:
    v = value.strip()
    if re.fullmatch(r"#?[0-9a-fA-F]{6}", v):
        return "#" + v.lstrip("#").upper()
    if re.fullmatch(r"#?[0-9a-fA-F]{3}", v):
        s = v.lstrip("#")
        return "#" + "".join(c * 2 for c in s).upper()
    names = colores()["nombres"]
    k = v.lower()
    if k in names:
        return names[k]
    paths.die(f"no reconozco el color '{value}'. Usa un hex (#FF4FA3) o un nombre: {', '.join(sorted(set(names)))}")


def _accent_value(value: str, style: dict):
    if value.strip().lower() == "auto":
        cur = style.get("activeColor")
        fb = cur.get("fallback") if isinstance(cur, dict) else (cur or "#FFD60A")
        return {"auto": "accent", "fallback": fb}
    return parse_color(value)


def from_args(a) -> dict:
    """Los flags de personalización que vinieron en la línea de comandos (sin los vacíos)."""
    return {k: getattr(a, k) for k in KEYS if getattr(a, k, None) not in (None, "")}


def apply(style: dict, ov: dict) -> dict:
    if not ov:
        return style
    st = copy.deepcopy(style)
    if ov.get("palette"):
        pals = colores()["paletas"]
        name = str(ov["palette"]).lower()
        if name not in pals:
            paths.die(f"no existe la paleta '{ov['palette']}'. Paletas: {', '.join(pals)}")
        p = pals[name]
        st["color"] = p["color"]
        _set_accent(st, _accent_value(p["accent"], st))
        if p.get("stroke"):
            st["stroke"] = {"width": (st.get("stroke") or {}).get("width", 0.06), "color": p["stroke"]}
    if ov.get("color"):
        st["color"] = parse_color(ov["color"])
    if ov.get("accent"):
        _set_accent(st, _accent_value(ov["accent"], st))
    if ov.get("stroke"):
        if str(ov["stroke"]).lower() in ("none", "no", "ninguno", "off"):
            st["stroke"] = None
        else:
            st["stroke"] = {"width": (st.get("stroke") or {}).get("width", 0.08), "color": parse_color(ov["stroke"])}
    if ov.get("font"):
        st["font"] = fuentes.resolve(ov["font"], default_weight=st["font"].get("weight", 700))
    if ov.get("emphasis_font"):
        f = fuentes.resolve(ov["emphasis_font"], default_weight=(st.get("emphasisFont") or st["font"]).get("weight", 700))
        st["emphasisFont"] = f
        st["numberFont"] = f  # los números del highlight van en la misma letra elegida
    if ov.get("big_font"):
        st.setdefault("behind", {"enabled": False})
        st["behind"]["bigFont"] = fuentes.resolve(ov["big_font"], default_weight=700)
    if ov.get("size"):
        try:
            k = float(ov["size"])
        except ValueError:
            paths.die("--size es un multiplicador, p. ej. 1.2 (20 % más grande) o 0.9")
        if not 0.4 <= k <= 3:
            paths.die("--size debe estar entre 0.4 y 3")
        st["size"] = round(st["size"] * k, 3)
    if ov.get("case"):
        if ov["case"] not in ("upper", "lower", "sentence"):
            paths.die("--case debe ser upper, lower o sentence")
        st["case"] = ov["case"]
    return st


def _set_accent(st: dict, value) -> None:
    st["activeColor"] = value
    bh = st.get("behind") or {}
    if bh.get("enabled"):
        bh["bigColor"] = value


def palettes_text() -> str:
    pals = colores()["paletas"]
    out = ["Paletas (--palette):"]
    for k, p in pals.items():
        out.append(f"  {k:<9} {p['color']}  {p['accent']:<8} {p.get('descripcion', '')}")
    names = colores()["nombres"]
    es = [n for n in names if not re.fullmatch(r"white|black|red|yellow|orange|green|lime|mint|cyan|blue|teal|purple|violet|pink|magenta|gold|silver|gray|cream", n)]
    out.append("\nColores con nombre (--color, --accent, --stroke): " + ", ".join(es))
    out.append("O cualquier hex: --accent \"#FF4FA3\"")
    return "\n".join(out)
