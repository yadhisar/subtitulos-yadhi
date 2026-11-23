"""Prepara el smoke test: agrupa sample-words.json con cada estilo y arma la lista de renders (un PNG por estilo y capa).

    python tests\\smoke_prep.py <carpeta_salida>      -> escribe jobs.json y un captions.json por estilo
    python tests\\smoke_prep.py <carpeta_salida> --check   -> verifica que cada PNG tenga algo dibujado
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import emphasis  # noqa: E402
import paths  # noqa: E402
import personalizar  # noqa: E402
from group import build_captions  # noqa: E402
from numeros import convert_words  # noqa: E402

LAYERS = ("all", "mask")
# combinaciones de tipografía y color (solo capa all): prueban --font, --emphasis-font, --palette, --accent...
VARIANTS = [
    ("bottom", {"font": "Bebas Neue", "palette": "tiktok", "size": "1.15"}),
    ("glide", {"font": "Poppins:800", "emphasis_font": "Pacifico", "accent": "rosa"}),
    ("karaoke", {"font": "Luckiest Guy", "palette": "neon", "case": "upper"}),
    ("keyword", {"font": "Outfit:600", "big_font": "Bebas Neue", "palette": "dorado"}),
    ("bottom", {"font": "Playfair Display:900", "palette": "oscuro", "case": "sentence"}),
    ("glide", {"font": "Fredoka:700", "emphasis_font": "Great Vibes", "palette": "oceano"}),
]


def pick_frame(cap: dict) -> int:
    fps = cap["video"]["fps"]
    for b in cap.get("big") or []:
        if not b.get("front"):
            p = cap["pages"][b["page"]]
            t = min(b["endMs"], p["endMs"]) - 120
            return int(t * fps / 1000)
    for p in cap["pages"]:
        if any(w.get("emphasis") for w in p["words"]) and len(p["words"]) >= 3:
            t = min(p["endMs"] - 120, p["words"][-1]["endMs"] + 60)
            return int(t * fps / 1000)
    p = cap["pages"][0]
    return int((p["endMs"] - 120) * fps / 1000)


def prep(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    words = convert_words(paths.read_json(ROOT / "tests" / "sample-words.json")["words"])
    video = {"width": 1080, "height": 1920, "fps": 30.0, "durationMs": 32000}
    jobs = []
    for sp in sorted(paths.STYLES.glob("*.json")):
        style = paths.load_style(str(sp))
        cap = build_captions(words, style, video, [])
        emphasis.auto(cap, "auto", "Lima, TikTok, Instagram", None, style)
        cp = paths.write_json(out / f"{sp.stem}.captions.json", cap)
        frame = pick_frame(cap)
        for layer in LAYERS:
            jobs.append({"captions": str(cp), "style": str(sp), "layer": layer, "still": frame,
                         "png": str(out / f"{sp.stem}-{layer}.png")})
    for k, (name, ov) in enumerate(VARIANTS):
        style = personalizar.apply(paths.load_style(name), ov)
        sp = paths.write_json(out / f"var{k}-{name}.style.json", style)
        cap = build_captions(words, style, video, [])
        emphasis.auto(cap, "auto", "Lima, TikTok, Instagram", None, style)
        cp = paths.write_json(out / f"var{k}-{name}.captions.json", cap)
        jobs.append({"captions": str(cp), "style": str(sp), "layer": "all", "still": pick_frame(cap),
                     "png": str(out / f"var{k}-{name}-all.png")})
    paths.write_json(out / "jobs.json", jobs)
    print(f"{len(jobs)} renders -> {out / 'jobs.json'}")


def check(out: Path) -> int:
    from PIL import Image

    jobs = paths.read_json(out / "jobs.json")
    bad = 0
    for j in jobs:
        p = Path(j["png"])
        if not p.exists():
            print(f"[FALLA] no existe {p.name}")
            bad += 1
            continue
        im = Image.open(p).convert("RGBA")
        if j["layer"] == "mask":
            box = im.convert("L").point(lambda v: 255 if v > 127 else 0).getbbox()
        else:
            box = im.getchannel("A").getbbox()
        if not box:
            print(f"[FALLA] {p.name} está vacío")
            bad += 1
        else:
            print(f"[OK]    {p.name}  texto en {box}")
    return bad


if __name__ == "__main__":
    paths.utf8_console()
    o = Path(sys.argv[1])
    if "--check" in sys.argv:
        sys.exit(1 if check(o) else 0)
    prep(o)
