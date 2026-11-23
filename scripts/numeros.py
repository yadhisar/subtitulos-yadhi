"""Números hablados en español -> un solo token con cifras (formato Perú).

    "cinco mil soles"                  -> "S/ 5,000"
    "mil ochocientos millones de soles" -> "S/ 1,800 millones"
    "cuarenta por ciento"              -> "40%"
    "dos mil veinticuatro"             -> "2024"
    "cien dólares"                     -> "$100"
    "tres veces"                       -> "3x"
    "cinco soles con cincuenta"        -> "S/ 5.50"

Reglas:
- Coma de miles y punto decimal (1,800 / 5,000.50), como se escribe en Perú.
- Si el transcript ya trae cifras ("5000", "1.800"), se respetan tal cual; solo se les pega la moneda o el %.
- Un monto queda en UN token (con "num": true), así group.py nunca lo parte entre líneas ni páginas.
- Un número suelto y chico ("dos", "un", "mil gracias") se deja en letras: solo se convierte si es >= 10,
  tiene varias palabras, o lleva moneda, %, "veces" o millones.

Uso suelto:  uv run python scripts\\numeros.py "cinco mil soles"
"""
from __future__ import annotations

import re
import sys
import unicodedata

UNITS = {"cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
         "seis": 6, "siete": 7, "ocho": 8, "nueve": 9}
TEENS = {"diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16,
         "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiun": 21, "veintiuno": 21,
         "veintiuna": 21, "veintidos": 22, "veintitres": 23, "veinticuatro": 24, "veinticinco": 25,
         "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29}
TENS = {"treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90}
HUNDREDS = {"cien": 100, "ciento": 100, "doscientos": 200, "doscientas": 200, "trescientos": 300, "trescientas": 300,
            "cuatrocientos": 400, "cuatrocientas": 400, "quinientos": 500, "quinientas": 500, "seiscientos": 600,
            "seiscientas": 600, "setecientos": 700, "setecientas": 700, "ochocientos": 800, "ochocientas": 800,
            "novecientos": 900, "novecientas": 900}
MILLON = {"millon", "millones"}
CURRENCY = {"soles": "S/ ", "sol": "S/ ", "lucas": "S/ ", "luca": "S/ ", "dolares": "$", "dolar": "$",
            "euros": "€", "euro": "€"}
CENTS = {"centimos", "centimo", "centavos", "centavo"}
# palabras sueltas que NO se convierten aunque valgan >= 10 ("mil gracias", "al cien")
LONE_KEEP = {"mil", "cien", "un", "una", "uno", "cero"}

LEAD_PUNCT = "¿¡\"'«“‘(["
TRAIL_PUNCT = ".,;:!?…\"'»”’)]"
DIGITS_RE = re.compile(r"^(S/\s?|\$|€)?\d[\d.,]*%?$")


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def norm(text: str) -> str:
    """minúsculas, sin tildes, sin puntuación de borde (deja dígitos, %, $, / y separadores)."""
    t = strip_accents(text.strip().lower())
    return t.strip(LEAD_PUNCT + TRAIL_PUNCT + " ")


def is_number_token(text: str) -> bool:
    return bool(re.search(r"\d", text))


def _split_punct(text: str) -> tuple[str, str, str]:
    t = text.strip()
    i = 0
    while i < len(t) and t[i] in LEAD_PUNCT:
        i += 1
    j = len(t)
    while j > i and t[j - 1] in TRAIL_PUNCT:
        j -= 1
    return t[:i], t[i:j], t[j:]


def parse_spoken(ws: list[str], i: int):
    """Lee un número en palabras desde ws[i]. Devuelve (valor, j, millones_count | None, n_palabras) o None."""
    total_m = 0
    th = 0
    cur = 0
    last = None
    j = i
    count_m = None
    while j < len(ws):
        w = ws[j]
        if w in UNITS:
            if last not in (None, "hund", "mil", "millon", "y"):
                break
            cur += UNITS[w]
            last = "unit"
        elif w in TEENS:
            if last not in (None, "hund", "mil", "millon"):
                break
            cur += TEENS[w]
            last = "teen"
        elif w in TENS:
            if last not in (None, "hund", "mil", "millon"):
                break
            cur += TENS[w]
            last = "tens"
        elif w == "y":
            nxt = ws[j + 1] if j + 1 < len(ws) else ""
            if last == "tens" and UNITS.get(nxt, 0) > 0:
                last = "y"
            else:
                break
        elif w in HUNDREDS:
            if last not in (None, "mil", "millon"):
                break
            cur += HUNDREDS[w]
            last = "hund"
        elif w == "mil":
            if last in ("mil",) or th:
                break
            th = (cur or 1) * 1000
            cur = 0
            last = "mil"
        elif w in MILLON:
            if last == "millon" or total_m:
                break
            count_m = (th + cur) or 1
            total_m = count_m * 1_000_000
            th = cur = 0
            last = "millon"
        else:
            break
        j += 1
    if j == i:
        return None
    value = total_m + th + cur
    return value, j, (count_m if last == "millon" else None), j - i


def _digits_value(s: str) -> float | None:
    s = s.replace("S/", "").replace("$", "").replace("€", "").replace("%", "").strip()
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", s):
        return float(re.sub(r"[.,]", "", s))
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def _fmt(n: float) -> str:
    if abs(n - round(n)) < 1e-9:
        return f"{int(round(n)):,}"
    return f"{n:,.2f}".rstrip("0").rstrip(".") if n < 1000 else f"{n:,.2f}"


def convert_words(words: list[dict]) -> list[dict]:
    """Recorre la lista de palabras de words.json y junta cada número hablado en un token."""
    raw = [w["text"] for w in words]
    ws = [norm(t) for t in raw]
    out: list[dict] = []
    i = 0
    n = len(words)
    while i < n:
        res = _try_number(raw, ws, i)
        if res is None:
            out.append(dict(words[i]))
            i += 1
            continue
        text, j = res
        first, last = words[i], words[j - 1]
        lead = _split_punct(raw[i])[0]
        trail = _split_punct(raw[j - 1])[2]
        probs = [w.get("prob", 1.0) for w in words[i:j]]
        tok = {"text": f"{lead}{text}{trail}", "startMs": first["startMs"], "endMs": last["endMs"],
               "prob": round(min(probs), 3), "num": True}
        out.append(tok)
        i = j
    return out


def _try_number(raw: list[str], ws: list[str], i: int):
    w0 = ws[i]
    core0 = _split_punct(raw[i])[1]
    digits = bool(DIGITS_RE.match(core0)) and is_number_token(core0)
    count_m = None
    year_ok = False
    if digits:
        if any(p in core0 for p in ("S/", "$", "€")) or core0.endswith("%"):
            # ya viene con moneda o %: se respeta tal cual, solo se pega un "millones" que lo siga
            if i + 1 < len(ws) and ws[i + 1] in MILLON and not _split_punct(raw[i])[2]:
                return f"{core0} {'millón' if ws[i + 1] == 'millon' else 'millones'}", i + 2
            return None
        num_text = core0
        value = _digits_value(core0) or 0
        j = i + 1
        nwords = 1
        if j < len(ws) and ws[j] == "mil" and not _split_punct(raw[i])[2]:
            value *= 1000
            num_text = _fmt(value)
            j += 1
            nwords += 1
        elif j < len(ws) and ws[j] in MILLON and not _split_punct(raw[i])[2]:
            count_m = num_text
            j += 1
            nwords += 1
    else:
        p = parse_spoken(ws, i)
        if p is None:
            return None
        value, j, cm, nwords = p
        # el número no puede cruzar una pausa marcada con puntuación ("cinco. Mil..."): se corta ahí
        for k in range(i, j - 1):
            if _split_punct(raw[k])[2]:
                j = k + 1
                p2 = parse_spoken(ws[: j], i)
                if p2 is None:
                    return None
                value, j, cm, nwords = p2
                break
        count_m = _fmt(cm) if cm else None
        num_text = _fmt(value)
        year_ok = 1900 <= value <= 2100 and "mil" in ws[i:j] and cm is None

    def trail_at(k):  # ¿la palabra k termina en puntuación? entonces no se sigue leyendo después de ella
        return bool(_split_punct(raw[k])[2])

    dec = None
    # decimales: "dos punto cinco", "uno coma cinco millones"
    if j < len(ws) - 1 and ws[j] in ("punto", "coma") and not trail_at(j - 1):
        p = parse_spoken([w if w not in MILLON else "\0" for w in ws], j + 1)
        if p and p[2] is None:
            dec = str(p[0])
            nwords += p[3] + 1
            j = p[1]
            if j < len(ws) and ws[j] in MILLON and not trail_at(j - 1):
                count_m = f"{num_text}.{dec}"
                dec = None
                j += 1
                nwords += 1
    cur = None
    pct = False
    veces = False

    def take_cents(k):
        if k < len(ws) - 1 and ws[k] == "con" and not trail_at(k - 1):
            p = parse_spoken(ws, k + 1)
            if p and p[0] < 100 and p[2] is None:
                k2 = p[1]
                if k2 < len(ws) and ws[k2] in CENTS and not trail_at(k2 - 1):
                    k2 += 1
                return f"{p[0]:02d}", k2
        return None, k

    if j < len(ws) and not trail_at(j - 1):
        nxt = ws[j]
        if nxt == "por" and j + 1 < len(ws) and ws[j + 1] == "ciento":
            pct, j = True, j + 2
        elif nxt in ("porciento", "%"):  # whisper a veces escribe "50 %" con el signo aparte
            pct, j = True, j + 1
        elif nxt in CURRENCY:
            cur, j = CURRENCY[nxt], j + 1
        elif nxt == "de" and j + 1 < len(ws) and ws[j + 1] in CURRENCY and count_m:
            cur, j = CURRENCY[ws[j + 1]], j + 2
        elif nxt == "veces":
            veces, j = True, j + 1
        elif nxt == "con":
            # "cinco con cincuenta soles"
            cents, k = take_cents(j)
            if cents and k < len(ws) and ws[k] in CURRENCY and not trail_at(k - 1):
                dec, cur, j = cents, CURRENCY[ws[k]], k + 1
    if cur and dec is None and count_m is None:
        cents, j = take_cents(j)
        if cents:
            dec = cents

    single_small = nwords == 1 and not digits and (w0 in LONE_KEEP or value < 10)
    if not (cur or pct or veces):
        if digits:
            if nwords == 1:
                return None  # cifras sueltas: se respetan como vienen
        elif single_small:
            return None
    if count_m is not None:
        word = "millón" if count_m in ("1",) else "millones"
        num = f"{count_m} {word}"
    elif digits and nwords == 1:
        num = num_text  # se respeta lo que escribió el transcript
    elif year_ok and not (cur or pct):
        num = str(int(value))
    else:
        num = num_text
        if dec is not None:
            num = f"{num}.{dec}"
    if pct:
        return f"{num}%", j
    if cur:
        return f"{cur}{num}", j
    if veces:
        return f"{num}x", j
    return num, j


def convert_text(text: str) -> str:
    """Atajo para pruebas: convierte una frase suelta."""
    words = [{"text": t, "startMs": k * 100, "endMs": k * 100 + 90, "prob": 1.0} for k, t in enumerate(text.split())]
    return " ".join(w["text"] for w in convert_words(words))


if __name__ == "__main__":
    import paths

    paths.utf8_console()
    for arg in sys.argv[1:] or ["cinco mil soles", "mil ochocientos millones de soles", "cuarenta por ciento",
                                "dos mil veinticuatro", "cien dólares", "tres veces"]:
        print(f"{arg!r} -> {convert_text(arg)!r}")
