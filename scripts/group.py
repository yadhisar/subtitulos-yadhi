"""Agrupa las palabras en "páginas" de 1-2 líneas y escribe captions.json + .srt.

    uv run python scripts\\group.py words.json --style glide --video "C:\\...\\video.mp4" --out captions.json [--srt video.srt]
    uv run python scripts\\group.py words.json --style glide --size 1080x1920 --fps 30 --out captions.json   (sin video)

Reglas (vienen de page{} en el JSON del estilo):
- maxWords, maxCharsPerLine (maxCharsPerLineWide en horizontal), maxLines, minFrames, maxFrames, gapBreakMs.
- Una pausa > gapBreakMs, un punto final o un corte de toma empiezan página nueva. Ninguna página cruza un corte.
- Una página termina cuando empieza la siguiente o 400 ms después de su última palabra (700 ms si tiene highlight).
  Nunca se solapan.
- Un monto es un solo token (numeros.py), así que nunca se parte entre líneas ni páginas.
- No se deja una palabrita colgando al final ("de", "la", "y"...) si se puede pasar a la página siguiente.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numeros  # noqa: E402
import paths  # noqa: E402

DANGLING = {"de", "del", "la", "el", "los", "las", "un", "una", "y", "o", "que", "en", "a", "al", "por", "con",
            "para", "mi", "tu", "su", "sus", "mis", "lo", "le", "se", "me", "te", "es", "no", "ni", "pero"}
SENTENCE_END = (".", "?", "!", "…")
CLAUSE_END = (",", ";", ":")

DEFAULT_PAGE = {"maxWords": 5, "maxCharsPerLine": 24, "maxLines": 1, "minFrames": 14, "maxFrames": 75,
                "gapBreakMs": 350}


def page_params(style: dict, wide: bool = False) -> dict:
    p = {**DEFAULT_PAGE, **(style.get("page") or {})}
    if wide and p.get("maxCharsPerLineWide"):
        p["maxCharsPerLine"] = p["maxCharsPerLineWide"]
    return p


def _chars(ws: list[dict]) -> int:
    return sum(len(w["text"]) for w in ws) + max(0, len(ws) - 1)


def _cut_between(cuts: list[int], a: int, b: int) -> bool:
    return any(a < c <= b for c in cuts)


def split_pages(words: list[dict], pp: dict, cuts: list[int], fps: float) -> list[list[dict]]:
    max_words = int(pp["maxWords"])
    max_chars = int(pp["maxCharsPerLine"]) * int(pp["maxLines"])
    max_ms = int(pp["maxFrames"]) * 1000 / fps
    gap_ms = int(pp["gapBreakMs"])
    pages: list[list[dict]] = []
    cur: list[dict] = []
    for w in words:
        if cur:
            prev = cur[-1]
            size = len(cur) >= max_words or _chars(cur + [w]) > max_chars or (w["endMs"] - cur[0]["startMs"]) > max_ms
            hard = (w["startMs"] - prev["endMs"] > gap_ms or _cut_between(cuts, prev["startMs"], w["startMs"])
                    or prev["text"].endswith(SENTENCE_END))
            soft = prev["text"].endswith(CLAUSE_END) and len(cur) >= 2
            if hard or size or soft:
                carry = None
                if (size and not hard and not soft and len(cur) >= 2
                        and numeros.norm(prev["text"]) in DANGLING and not prev.get("num")
                        and not _cut_between(cuts, prev["startMs"], w["startMs"])
                        and _chars([prev, w]) <= max_chars):
                    carry = cur.pop()
                pages.append(cur)
                cur = [carry] if carry else []
        cur.append(w)
    if cur:
        pages.append(cur)
    return pages


def assign_lines(ws: list[dict], max_chars_line: int, max_lines: int) -> list[int]:
    if max_lines <= 1 or len(ws) < 2 or _chars(ws) <= max_chars_line:
        return [0] * len(ws)
    best_k, best = 1, None
    for k in range(1, len(ws)):
        a, b = _chars(ws[:k]), _chars(ws[k:])
        # equilibrio, con un leve premio a que la línea de arriba sea la más corta (pirámide)
        score = max(a, b) + (0.5 if a > b else 0)
        if best is None or score < best:
            best, best_k = score, k
    return [0 if i < best_k else 1 for i in range(len(ws))]


def set_page_ends(cap: dict) -> dict:
    """Recalcula startMs/endMs de cada página (se vuelve a llamar después de elegir highlights)."""
    fps = cap["video"]["fps"]
    dur = cap["video"]["durationMs"]
    cuts = cap.get("cuts") or []
    st = cap.get("_page") or {}
    min_ms = int(st.get("minFrames", DEFAULT_PAGE["minFrames"])) * 1000 / fps
    pages = cap["pages"]
    for i, p in enumerate(pages):
        ws = p["words"]
        start = ws[0]["startMs"]
        last_end = max(w["endMs"] for w in ws)
        hold = 700 if any(w.get("emphasis") for w in ws) else 400
        end = max(last_end + hold, start + min_ms)
        limit = dur
        if i + 1 < len(pages):
            limit = min(limit, pages[i + 1]["words"][0]["startMs"])
        nxt_cut = next((c for c in cuts if c > start), None)
        if nxt_cut is not None:
            limit = min(limit, nxt_cut)
        end = min(end, limit)
        if end <= start:
            end = start + 1
        p["startMs"] = int(start)
        p["endMs"] = int(round(end))
        for w in ws:  # una palabra que cruza el corte se recorta al corte
            if w["endMs"] > p["endMs"]:
                w["endMs"] = p["endMs"]
    return cap


def build_captions(words: list[dict], style: dict, video: dict, cuts: list[int] | None = None) -> dict:
    cuts = sorted(int(c) for c in (cuts or []))
    wide = video["width"] > video["height"]
    pp = page_params(style, wide)
    pages_w = split_pages(words, pp, cuts, video["fps"])
    pages = []
    for ws in pages_w:
        lines = assign_lines(ws, int(pp["maxCharsPerLine"]), int(pp["maxLines"]))
        out_ws = []
        for w, ln in zip(ws, lines):
            d = {"text": w["text"], "startMs": int(w["startMs"]), "endMs": int(w["endMs"]), "line": ln,
                 "emphasis": False, "reason": None}
            if w.get("num") or numeros.is_number_token(w["text"]):
                d["num"] = True
            out_ws.append(d)
        pages.append({"startMs": out_ws[0]["startMs"], "endMs": out_ws[-1]["endMs"], "y": None, "words": out_ws})
    cap = {
        "version": 1,
        "video": {"width": video["width"], "height": video["height"], "fps": video["fps"],
                  "durationMs": video["durationMs"]},
        "style": style.get("name", "glide"),
        "cuts": cuts,
        "pages": pages,
        "big": [],
        "notes": [],
        "_page": {k: pp[k] for k in ("minFrames", "maxFrames", "maxWords", "maxLines", "maxCharsPerLine")},
    }
    return set_page_ends(cap)


def regroup_lines(cap: dict, style: dict) -> dict:
    """Si alguien editó captions.json a mano (palabras nuevas, sin 'line'), rehace las líneas."""
    wide = cap["video"]["width"] > cap["video"]["height"]
    pp = page_params(style, wide)
    for p in cap["pages"]:
        if any("line" not in w for w in p["words"]):
            for w, ln in zip(p["words"], assign_lines(p["words"], int(pp["maxCharsPerLine"]), int(pp["maxLines"]))):
                w["line"] = ln
    return cap


def page_text(p: dict, sep: str = "\n") -> str:
    lines: dict[int, list[str]] = {}
    for w in p["words"]:
        lines.setdefault(int(w.get("line", 0)), []).append(w["text"])
    return sep.join(" ".join(v) for _, v in sorted(lines.items()))


def to_srt(cap: dict) -> str:
    out = []
    for i, p in enumerate(cap["pages"], 1):
        out.append(f"{i}\n{paths.ms_to_srt(p['startMs'])} --> {paths.ms_to_srt(p['endMs'])}\n{page_text(p)}\n")
    return "\n".join(out)


def write_srt(cap: dict, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_srt(cap), encoding="utf-8")
    return path


def main(argv=None):
    paths.utf8_console()
    ap = argparse.ArgumentParser(description="Agrupa palabras en páginas y escribe captions.json y .srt")
    ap.add_argument("words", type=Path)
    ap.add_argument("--style", default="glide")
    ap.add_argument("--video", type=Path)
    ap.add_argument("--size", default="1080x1920", help="ancho x alto si no hay --video")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--duration-ms", type=int)
    ap.add_argument("--cuts", type=Path, help="cuts.json de cuts.py")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--srt", type=Path)
    a = ap.parse_args(argv)
    data = paths.read_json(a.words)
    words = data["words"] if isinstance(data, dict) else data
    style = paths.load_style(a.style)
    if a.video:
        info = paths.probe(a.video)
    else:
        w, h = (int(x) for x in a.size.lower().split("x"))
        dur = a.duration_ms or (max(x["endMs"] for x in words) + 1000)
        info = {"width": w, "height": h, "fps": a.fps, "durationMs": dur}
    cuts = paths.read_json(a.cuts)["cuts"] if a.cuts else []
    cap = build_captions(words, style, info, cuts)
    paths.write_json(a.out, cap)
    if a.srt:
        write_srt(cap, a.srt)
    print(f"{len(cap['pages'])} páginas -> {a.out}")


if __name__ == "__main__":
    main()
