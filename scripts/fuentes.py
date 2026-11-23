"""Tipografías: catálogo de las que trae el repo y descarga de cualquier otra de Google Fonts.

    uv run python scripts\\fuentes.py --list                       # las que ya están en fonts\\
    uv run python scripts\\fuentes.py --add "Bebas Neue"            # baja una familia (pesos 400, 700 y 900 si existen)
    uv run python scripts\\fuentes.py --add "Poppins" --weights 600,800 --italic
    uv run python scripts\\fuentes.py --pack                        # baja el pack completo del repo (PACK, abajo)

En subtitulos.py basta con --font "Bebas Neue" o --font "Poppins:800": si no está en fonts\\, se baja sola la
primera vez (un TTF estático por peso, con su licencia). Al renderizar no se usa internet.

Archivos: fonts\\<Familia sin espacios>-<Peso><Italic>.ttf  (p. ej. BebasNeue-Regular.ttf, Poppins-ExtraBoldItalic.ttf)
y la licencia como fonts\\OFL-<Familia>.txt (o LICENSE-<Familia>.txt si es Apache).
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

WEIGHTS = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular", 500: "Medium", 600: "SemiBold",
           700: "Bold", 800: "ExtraBold", 900: "Black"}
BY_NAME = {v.lower(): k for k, v in WEIGHTS.items()}
UA = {"User-Agent": "subtitulos-yadhi"}  # con un navegador "desconocido", Google Fonts entrega TTF estático

# Pack que trae el repo: (familia, pesos, categoría, ¿itálica?)
PACK: list[tuple[str, list[int], str, bool]] = [
    # sans
    ("Inter", [500, 600, 700, 900], "sans", False),
    ("Montserrat", [600, 700, 800, 900], "sans", False),
    ("Poppins", [600, 700, 800, 900], "sans", False),
    ("Roboto", [500, 700, 900], "sans", False),
    ("Open Sans", [600, 700, 800], "sans", False),
    ("Lato", [700, 900], "sans", False),
    ("Nunito", [700, 900], "sans", False),
    ("Raleway", [700, 900], "sans", False),
    ("Work Sans", [600, 800], "sans", False),
    ("DM Sans", [700, 900], "sans", False),
    ("Manrope", [700, 800], "sans", False),
    ("Plus Jakarta Sans", [700, 800], "sans", False),
    ("Outfit", [600, 800], "sans", False),
    ("Rubik", [700, 900], "sans", False),
    ("Figtree", [700, 900], "sans", False),
    ("Lexend", [600, 800], "sans", False),
    # display / condensadas
    ("Anton", [400], "display", False),
    ("Bebas Neue", [400], "display", False),
    ("Oswald", [600, 700], "display", False),
    ("Archivo Black", [400], "display", False),
    ("Barlow Condensed", [700, 900], "display", False),
    ("League Spartan", [700, 900], "display", False),
    ("Bricolage Grotesque", [700, 800], "display", False),
    ("Teko", [600], "display", False),
    ("Alfa Slab One", [400], "display", False),
    # serif
    ("Playfair Display", [700, 900], "serif", True),
    ("DM Serif Display", [400], "serif", True),
    ("Lora", [700], "serif", True),
    ("Merriweather", [700, 900], "serif", False),
    ("Instrument Serif", [400], "serif", True),
    ("Abril Fatface", [400], "serif", False),
    ("Libre Baskerville", [700], "serif", False),
    # script / a mano
    ("Pinyon Script", [400], "script", False),
    ("Great Vibes", [400], "script", False),
    ("Dancing Script", [700], "script", False),
    ("Pacifico", [400], "script", False),
    ("Satisfy", [400], "script", False),
    ("Caveat", [700], "script", False),
    ("Kalam", [700], "script", False),
    ("Permanent Marker", [400], "script", False),
    ("Shadows Into Light", [400], "script", False),
    # divertidas
    ("Luckiest Guy", [400], "divertida", False),
    ("Bangers", [400], "divertida", False),
    ("Fredoka", [600, 700], "divertida", False),
    ("Lilita One", [400], "divertida", False),
    ("Titan One", [400], "divertida", False),
    ("Bowlby One", [400], "divertida", False),
    ("Chewy", [400], "divertida", False),
    # mono
    ("Space Mono", [700], "mono", False),
    ("JetBrains Mono", [700, 800], "mono", False),
]
CATEGORY = {f: c for f, _, c, _ in PACK}


def slug(family: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", family.title() if family.islower() else family)


def file_name(family: str, weight: int, italic: bool = False) -> str:
    w = WEIGHTS.get(weight, str(weight))
    if italic:
        w = "Italic" if weight == 400 else f"{w}Italic"
    return f"{slug(family)}-{w}.ttf"


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def download_weight(family: str, weight: int, italic: bool = False, dest: Path | None = None) -> Path | None:
    """Baja un peso. None si Google Fonts no lo tiene."""
    dest = dest or paths.FONTS
    out = dest / file_name(family, weight, italic)
    if out.exists() and out.stat().st_size > 0:
        return out
    fam = urllib.parse.quote_plus(family)
    q = f"ital,wght@1,{weight}" if italic else f"wght@{weight}"
    try:
        css = _get(f"https://fonts.googleapis.com/css2?family={fam}:{q}").decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 400:
            return None
        raise
    m = re.search(r"url\((https://[^)]+\.ttf)\)", css)
    if not m:
        return None
    dest.mkdir(parents=True, exist_ok=True)
    out.write_bytes(_get(m.group(1)))
    return out


def download_license(family: str, dest: Path | None = None) -> Path | None:
    dest = dest or paths.FONTS
    s = slug(family)
    for p in dest.glob(f"*-{s}.txt"):
        return p
    d = re.sub(r"[^a-z0-9]", "", family.lower())
    for folder, name, prefix in (("ofl", "OFL.txt", "OFL"), ("apache", "LICENSE.txt", "LICENSE"), ("ufl", "UFL.txt", "UFL")):
        try:
            data = _get(f"https://raw.githubusercontent.com/google/fonts/main/{folder}/{d}/{name}")
        except urllib.error.HTTPError:
            continue
        out = dest / f"{prefix}-{s}.txt"
        out.write_bytes(data)
        return out
    return None


def add_family(family: str, weights: list[int] | None = None, italic: bool = False, quiet: bool = False) -> list[Path]:
    weights = weights or [400, 700, 900]
    got = []
    for w in weights:
        for it in ([False, True] if italic else [False]):
            p = download_weight(family, w, it)
            if p:
                got.append(p)
    if not got:
        paths.die(f"Google Fonts no tiene '{family}' (revisa el nombre exacto en fonts.google.com)")
    lic = download_license(family)
    if not quiet:
        for p in got:
            print(f"  {p.name}")
        print(f"  licencia: {lic.name if lic else 'no encontrada (revísala en fonts.google.com)'}")
    return got


def installed() -> dict[str, list[tuple[int, bool, str]]]:
    """{slug de familia: [(peso, itálica, archivo)]} de lo que hay en fonts\\."""
    out: dict[str, list[tuple[int, bool, str]]] = {}
    for p in sorted(paths.FONTS.glob("*.ttf")):
        m = re.match(r"^(.+)-([A-Za-z]+?)(Italic)?\.ttf$", p.name)
        if not m:
            continue
        fam, wname, it = m.group(1), m.group(2), bool(m.group(3))
        if wname == "Italic":
            wname, it = "Regular", True
        w = BY_NAME.get(wname.lower())
        if w is None:
            continue
        out.setdefault(fam, []).append((w, it, p.name))
    return out


def _pretty(sl: str) -> str:
    for f, *_ in PACK:
        if slug(f) == sl:
            return f
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", sl)


def parse_spec(spec: str) -> tuple[str, int | None, bool]:
    """'Bebas Neue' · 'Poppins:800' · 'Poppins ExtraBold' · 'Playfair Display:700i' -> (familia, peso, itálica)."""
    s = spec.strip()
    weight = None
    italic = False
    if ":" in s:
        s, w = s.rsplit(":", 1)
        w = w.strip().lower()
        if w.endswith("i"):
            italic, w = True, w[:-1]
        weight = int(w) if w.isdigit() else BY_NAME.get(w)
    else:
        parts = s.split()
        if parts and parts[-1].lower() == "italic":
            italic = True
            parts = parts[:-1]
        if len(parts) > 1 and parts[-1].lower() in BY_NAME:
            weight = BY_NAME[parts[-1].lower()]
            parts = parts[:-1]
        s = " ".join(parts)
    return s.strip(), weight, italic


def resolve(spec: str, default_weight: int = 700, download: bool = True) -> dict:
    """--font "..." -> {family, file, weight} para el JSON del estilo. Baja la familia si no está."""
    family, weight, italic = parse_spec(spec)
    sl = slug(family)
    have = installed().get(sl, [])
    want = weight or default_weight
    cands = [h for h in have if h[1] == italic]
    if weight and not any(h[0] == weight for h in cands):
        cands = []
    if not cands and download:
        print(f"Bajando la tipografía '{family}' de Google Fonts (solo la primera vez)...", flush=True)
        ws = [weight] if weight else [400, 700, 900]
        add_family(family, ws, italic, quiet=True)
        have = installed().get(sl, [])
        cands = [h for h in have if h[1] == italic]
    if not cands:
        paths.die(f"no tengo la tipografía '{spec}'. Mira las disponibles con --list-fonts")
    w, it, fname = min(cands, key=lambda h: (abs(h[0] - want), -h[0]))
    label = WEIGHTS.get(w, str(w)) + (" Italic" if it else "")
    return {"family": f"{_pretty(sl)} {label}", "file": fname, "weight": w}


def list_text() -> str:
    inst = installed()
    groups: dict[str, list[str]] = {}
    for sl, items in sorted(inst.items()):
        fam = _pretty(sl)
        ws = ", ".join(f"{w}{'i' if it else ''}" for w, it, _ in sorted(items))
        groups.setdefault(CATEGORY.get(fam, "otras"), []).append(f"    {fam:<22} {ws}")
    out = [f"Tipografías en fonts\\ ({len(inst)} familias). Úsalas con --font \"Familia\" o --font \"Familia:800\":"]
    for cat in ("sans", "display", "serif", "script", "divertida", "mono", "otras"):
        if cat in groups:
            out.append(f"  {cat}")
            out += groups[cat]
    out.append("Cualquier otra de fonts.google.com se baja sola al usarla con --font.")
    return "\n".join(out)


def main(argv=None):
    paths.utf8_console()
    ap = argparse.ArgumentParser(description="Tipografías: lista, descarga y pack")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--add", help='familia de Google Fonts, p. ej. "Bebas Neue"')
    ap.add_argument("--weights", help="pesos separados por coma (400,700,900 por defecto)")
    ap.add_argument("--italic", action="store_true")
    ap.add_argument("--pack", action="store_true", help="baja todo el pack del repo")
    a = ap.parse_args(argv)
    if a.add:
        ws = [int(x) for x in a.weights.split(",")] if a.weights else None
        print(f"{a.add}:")
        add_family(a.add, ws, a.italic)
    elif a.pack:
        for fam, ws, _, it in PACK:
            print(f"{fam}...", flush=True)
            add_family(fam, ws, False, quiet=True)
            if it:
                for w in ws:
                    download_weight(fam, w, True)
    print(list_text())


if __name__ == "__main__":
    main()
