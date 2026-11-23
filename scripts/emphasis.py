"""Highlights (palabras resaltadas) en español, con su motivo.

    uv run python scripts\\emphasis.py video.captions.json --show
    uv run python scripts\\emphasis.py video.captions.json --pick '3:Lima=lugar' --pick '5:S/ 1,800 millones=precio'
    uv run python scripts\\emphasis.py video.captions.json --drop '4:gratis'
    uv run python scripts\\emphasis.py video.captions.json --clear
    uv run python scripts\\emphasis.py video.captions.json --auto [--mode auto|numbers|off] [--words 'S/ 1,800 millones, gratis']

PAG es el número de página que muestra --show (empieza en 1). En PowerShell usa comillas SIMPLES para montos
con S/ y $ (con comillas dobles, PowerShell intenta leer $100 como variable).

Prioridad automática:
  1) números, precios, %, fechas      2) nombres, marcas y lugares (TikTok, Lima, --vocab)
  3) palabra de contraste o remate ("nunca", "gratis", "nadie", "pierdes")      4) el tema, la primera vez
Máximo 1 highlight por página (2 si la página tiene 5 palabras o más). Nunca una stopword. Cada highlight
guarda "reason". También decide la lista "big" (palabra gigante) para los estilos con texto detrás de la persona.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import group  # noqa: E402
import numeros  # noqa: E402
import paths  # noqa: E402

STOPWORDS = set("""
a al algo algun alguna algunas alguno algunos ante antes aqui asi aun aunque bien cada como con contra cual cuales
cuando de del desde donde dos e el ella ellas ello ellos en entre era eran eres es esa esas ese eso esos esta estaba
estaban estamos estan estar estas este esto estos estoy fue fueron fui ha habia han has hasta hay he la las le les lo
los mas me mi mis mucho muy ni no nos nosotros o os otra otras otro otros para pero poco por porque que quien quienes
se sea ser si sido sin sobre son su sus tambien tan tanto te ti tiene tienen tengo tienes toda todas todo todos tu tus
un una uno unos unas usted ustedes va van vas voy y ya yo eh ah oye pues entonces osea o sea bueno ok okay tipo este
esta asi nada mas solo hacer hace hago haces hacen ir vez veces cosa cosas mismo misma algo aca alla ahi les nuestro
nuestra nuestros nuestras vamos vaya estoy estas estamos dice dijo decir digo puedes puede pueden puedo quiero quieres
poder tener tiene tienes tenemos saber sabes hacer haz estar sido solamente sino dia dias tipo forma manera parte
""".split())

BRANDS = {"tiktok", "instagram", "whatsapp", "facebook", "youtube", "google", "chatgpt", "claude", "netflix",
          "amazon", "apple", "iphone", "android", "spotify", "canva", "excel", "linkedin", "shopify", "mercadolibre",
          "uber", "rappi", "capcut", "meta"}
PUNCH = {"nunca", "gratis", "nadie", "pierdes", "pierde", "pierden", "perder", "jamas", "siempre", "cero", "unica",
         "unico", "ultimo", "ultima", "error", "errores", "prohibido", "secreto", "clave", "ojo", "cuidado", "facil",
         "rapido", "doble", "triple", "verdad", "mentira", "estafa", "estafas", "falso", "falsa", "urgente", "peor",
         "mejor", "gana", "ganas", "ganar", "ganancia", "dinero", "plata", "venta", "ventas", "vendes", "vender",
         "multa", "multas", "riesgo", "problema", "solucion", "nuevo", "nueva", "hoy", "ahora", "todos", "todo"}
PUNCH -= {"todos", "todo"}  # son stopwords: nunca se resaltan

REASONS = {1: "número", 2: "nombre/marca", 3: "remate", 4: "tema"}


def limit_for(page: dict) -> int:
    return 2 if len(page["words"]) >= 5 else 1


def is_stop(text: str) -> bool:
    return numeros.norm(text) in STOPWORDS and not numeros.is_number_token(text)


def _bare(text: str) -> str:
    return re.sub(r"[^\w]", "", numeros.norm(text))


def topic_word(cap: dict) -> str | None:
    c = Counter()
    for p in cap["pages"]:
        for w in p["words"]:
            n = _bare(w["text"])
            if len(n) >= 5 and n not in STOPWORDS and not numeros.is_number_token(w["text"]):
                c[n] += 1
    if not c:
        return None
    word, n = c.most_common(1)[0]
    return word if n >= 2 else None


def classify(w: dict, sentence_start: bool, vocab: set[str], topic: str | None) -> tuple[int, str] | None:
    text = w["text"]
    if w.get("num") or numeros.is_number_token(text):
        return 1, REASONS[1]
    if is_stop(text):
        return None
    n = _bare(text)
    if len(n) < 3:
        return None
    core = numeros._split_punct(text)[1]
    capital = core[:1].isupper()
    # una marca que también es palabra común ("meta de ventas") solo cuenta si viene con mayúscula
    if n in vocab or (n in BRANDS and capital) or (capital and not sentence_start):
        return 2, REASONS[2]
    if n in PUNCH:
        return 3, REASONS[3]
    if topic and n == topic:
        return 4, REASONS[4]
    return None


def split_words_arg(s: str | None) -> list[str]:
    """'S/ 1,800 millones, gratis' -> ['S/ 1,800 millones', 'gratis']  (la coma de 1,800 no separa)."""
    if not s:
        return []
    return [x.strip() for x in re.split(r",\s+|;\s*", s) if x.strip()]


def auto(cap: dict, mode: str = "auto", vocab: str = "", forced: str | None = None, style: dict | None = None) -> dict:
    for p in cap["pages"]:
        for w in p["words"]:
            w["emphasis"] = False
            w["reason"] = None
            w.pop("picked", None)
    if mode == "off":
        group.set_page_ends(cap)
        compute_big(cap, style)
        return cap
    vset = {_bare(t) for item in split_words_arg(vocab) for t in item.split()} if vocab else set()
    forced_list = [numeros.norm(x) for x in split_words_arg(forced)]
    topic = topic_word(cap) if mode == "auto" else None
    topic_used = False
    prev_end_sentence = True
    for p in cap["pages"]:
        lim = limit_for(p)
        cands = []
        for i, w in enumerate(p["words"]):
            n = numeros.norm(w["text"])
            if forced_list and any(n == f or (len(f.split()) == 1 and _bare(w["text"]) == re.sub(r"[^\w]", "", f))
                                   for f in forced_list):
                if not is_stop(w["text"]):
                    cands.append((0, i, "pedido por ti"))
            c = classify(w, prev_end_sentence, vset, None if topic_used else topic)
            prev_end_sentence = w["text"].endswith(group.SENTENCE_END)
            if not c:
                continue
            pr, reason = c
            if mode == "numbers" and pr != 1:
                continue
            cands.append((pr, i, reason))
        seen = set()
        picked = 0
        for pr, i, reason in sorted(cands, key=lambda c: (c[0], -len(p["words"][c[1]]["text"]), c[1])):
            if picked >= lim or i in seen:
                continue
            p["words"][i]["emphasis"] = True
            p["words"][i]["reason"] = reason
            seen.add(i)
            picked += 1
            if pr == 4:
                topic_used = True
    group.set_page_ends(cap)
    compute_big(cap, style)
    return cap


def compute_big(cap: dict, style: dict | None) -> dict:
    """Palabra gigante para estilos "detrás" (behind.enabled). Los números van delante (front=true) siempre."""
    bh = (style or {}).get("behind") or {}
    if not bh.get("enabled"):
        cap["big"] = []
        return cap
    max_chars = int(bh.get("maxChars", 9))
    min_hold = int(bh.get("minHoldMs", 900))
    every = int(bh.get("everyMs", 1700))
    min_gap = int(bh.get("minGapMs", 150))
    dur = cap["video"]["durationMs"]
    cuts = cap.get("cuts") or []
    big = []
    last_start = -10 ** 9
    for pi, p in enumerate(cap["pages"]):
        em = [w for w in p["words"] if w.get("emphasis")]
        em.sort(key=lambda w: (0 if (w.get("num") or numeros.is_number_token(w["text"])) else 1))
        for w in em:
            txt = numeros._split_punct(w["text"])[1]
            is_num = bool(w.get("num") or numeros.is_number_token(txt))
            if not is_num and len(_bare(txt)) > max_chars:
                continue
            if is_num and len(txt) > max_chars + 10:
                continue
            if w["startMs"] - last_start < every:
                break
            start = int(w["startMs"])
            end = max(int(p["endMs"]), start + min_hold)
            nxt_cut = next((c for c in cuts if c > start), None)
            end = min(end, dur, nxt_cut if nxt_cut is not None else dur)
            big.append({"text": txt, "startMs": start, "endMs": end, "front": is_num, "page": pi})
            last_start = start
            break
    for k in range(len(big) - 1):
        big[k]["endMs"] = max(big[k]["startMs"] + 1, min(big[k]["endMs"], big[k + 1]["startMs"] - min_gap))
    cap["big"] = big
    return cap


def _find(cap: dict, spec: str) -> tuple[int, int, str | None]:
    """'3:Lima=lugar' -> (índice de página, índice de palabra, razón)."""
    if ":" not in spec:
        paths.die(f"usa PAG:PALABRA (recibí '{spec}')")
    pg, rest = spec.split(":", 1)
    reason = None
    if "=" in rest:
        rest, reason = rest.split("=", 1)
        reason = reason.strip() or None
    try:
        pi = int(pg.strip()) - 1
    except ValueError:
        paths.die(f"la página debe ser un número (recibí '{pg}')")
    if not (0 <= pi < len(cap["pages"])):
        paths.die(f"no existe la página {pi + 1} (hay {len(cap['pages'])})")
    target = numeros.norm(rest)
    ws = cap["pages"][pi]["words"]
    for i, w in enumerate(ws):
        if numeros.norm(w["text"]) == target:
            return pi, i, reason
    for i, w in enumerate(ws):
        if _bare(w["text"]) == re.sub(r"[^\w]", "", target):
            return pi, i, reason
    paths.die(f"no encuentro '{rest}' en la página {pi + 1}: {' '.join(w['text'] for w in ws)}")


def pick(cap: dict, spec: str) -> str:
    pi, i, reason = _find(cap, spec)
    p = cap["pages"][pi]
    w = p["words"][i]
    if is_stop(w["text"]):
        paths.die(f"'{w['text']}' es una stopword: no se resalta")
    on = [k for k, x in enumerate(p["words"]) if x.get("emphasis") and k != i]
    if len(on) + 1 > limit_for(p):
        # se libera el highlight automático de menor prioridad; si todos son elegidos a mano, se avisa
        auto_on = [k for k in on if not p["words"][k].get("picked")]
        if not auto_on:
            paths.die(f"la página {pi + 1} ya tiene {len(on)} highlight(s) elegidos (máximo {limit_for(p)}). "
                      f"Quita uno con --drop primero.")
        k = auto_on[-1]
        p["words"][k]["emphasis"] = False
        p["words"][k]["reason"] = None
    w["emphasis"] = True
    w["reason"] = reason or "elegido"
    w["picked"] = True
    return f"página {pi + 1}: [{w['text']}] ({w['reason']})"


def drop(cap: dict, spec: str) -> str:
    pi, i, _ = _find(cap, spec)
    w = cap["pages"][pi]["words"][i]
    w["emphasis"] = False
    w["reason"] = None
    w.pop("picked", None)
    return f"página {pi + 1}: {w['text']} sin highlight"


def show(cap: dict) -> str:
    out = []
    for k, p in enumerate(cap["pages"], 1):
        t = p["startMs"] / 1000
        txt = " ".join(f"[{w['text']}]" if w.get("emphasis") else w["text"] for w in p["words"])
        why = "; ".join(f"{w['text']}: {w['reason']}" for w in p["words"] if w.get("emphasis"))
        out.append(f"{k:>3}  {int(t // 60):02d}:{t % 60:04.1f}  {txt}" + (f"   <- {why}" if why else ""))
    if cap.get("big"):
        out.append("\nPalabra grande (estilos detrás):")
        for b in cap["big"]:
            out.append(f"  {b['startMs'] / 1000:6.1f}s  {b['text']}  {'(delante)' if b.get('front') else '(detrás)'}")
    return "\n".join(out)


def main(argv=None):
    paths.utf8_console()
    ap = argparse.ArgumentParser(description="Ver y elegir highlights de captions.json")
    ap.add_argument("captions", type=Path)
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--pick", action="append", default=[])
    ap.add_argument("--drop", action="append", default=[])
    ap.add_argument("--clear", action="store_true")
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--mode", default="auto", choices=["auto", "numbers", "off"])
    ap.add_argument("--words", help="palabras a resaltar sí o sí: 'S/ 1,800 millones, gratis'")
    ap.add_argument("--vocab", default="")
    ap.add_argument("--style", help="estilo (para recalcular la palabra grande); por defecto el de captions.json")
    a = ap.parse_args(argv)
    cap = paths.read_json(a.captions)
    style = paths.load_style(a.style or cap.get("style", "glide"))
    changed = False
    if a.clear:
        auto(cap, "off", style=style)
        changed = True
    if a.auto:
        auto(cap, a.mode, a.vocab, a.words, style)
        changed = True
    for s in a.pick:
        print(pick(cap, s))
        changed = True
    for s in a.drop:
        print(drop(cap, s))
        changed = True
    if changed:
        group.set_page_ends(cap)
        compute_big(cap, style)
        paths.write_json(a.captions, cap)
    if a.show or not changed:
        print(show(cap))


if __name__ == "__main__":
    main()
