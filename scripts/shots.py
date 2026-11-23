"""Decide POR TOMA si la palabra grande puede ir detrás de la persona.

    uv run python scripts\\shots.py video.captions.json --matte matte.json [--subject subject.json]

Una toma no sirve para "detrás" si:
- la persona ocupa demasiado del cuadro (primer plano),
- la cara es muy grande, o
- el recorte es inestable (pelo fino, manos rápidas, movimiento de cámara).
En esas tomas la palabra grande pasa delante (front=true). También pasa delante si quedaría casi oculta detrás
de la persona. Los números siempre van delante (dígitos tapados cambian el sentido).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

MAX_COVER = 0.55
MAX_FACE_H = 0.40
MAX_INSTABILITY = 0.035


def _shot_ranges(cuts: list[int], dur: int) -> list[tuple[int, int]]:
    edges = [0] + [c for c in sorted(cuts) if 0 < c < dur] + [dur]
    return [(a, b) for a, b in zip(edges, edges[1:]) if b > a]


def big_box_cells(b: dict, style: dict, W: int, H: int, grid=(9, 16)) -> list[int]:
    """Celdas de la grilla de ocupación que tapa la palabra grande (aprox. por su caja)."""
    bh = style.get("behind") or {}
    cy = (bh.get("frontY", 70) if b.get("front") else bh.get("bigY", 30)) / 100
    size = (bh.get("frontMaxSize", 11) if b.get("front") else bh.get("bigMaxSize", 24)) / 100
    half_h = size * 0.75 / 2
    width = (bh.get("frontWidth", 74) if b.get("front") else bh.get("bigWidth", 92)) / 100 * 0.82
    x0, x1 = 0.5 - width / 2, 0.5 + width / 2
    y0, y1 = cy - half_h, cy + half_h
    cols, rows = grid
    cells = []
    for r in range(rows):
        for c in range(cols):
            cx, cyy = (c + 0.5) / cols, (r + 0.5) / rows
            if x0 <= cx <= x1 and y0 <= cyy <= y1:
                cells.append(r * cols + c)
    return cells


def decide(cap: dict, style: dict, matte: dict | None, subject: dict | None, behind_mode: str = "auto") -> tuple[list[dict], list[str], list[str]]:
    """Devuelve (shots, notas, avisos) y marca cap['big'][i]['front'] donde haga falta."""
    W, H = cap["video"]["width"], cap["video"]["height"]
    dur = cap["video"]["durationMs"]
    fps = cap["video"]["fps"]
    notes: list[str] = []
    warns: list[str] = []
    shots = []
    for a, b in _shot_ranges(cap.get("cuts") or [], dur):
        f0, f1 = int(a * fps / 1000), max(int(a * fps / 1000) + 1, int(b * fps / 1000))
        cov = inst = 0.0
        if matte and matte.get("coverage"):
            cv = matte["coverage"][f0:f1] or [0]
            iv = matte["instability"][f0 + 1:f1] or [0]
            cov = sorted(cv)[len(cv) // 2]
            inst = sum(iv) / len(iv)
        face_h = 0.0
        if subject:
            for s in subject.get("samples", []):
                if a <= s["ms"] < b:
                    for fb in s.get("faces", []):
                        face_h = max(face_h, fb[3])
        reasons = []
        if cov > MAX_COVER:
            reasons.append(f"primer plano (persona {cov:.0%} del cuadro)")
        if face_h > MAX_FACE_H:
            reasons.append(f"cara muy grande ({face_h:.0%} del alto)")
        if inst > MAX_INSTABILITY:
            reasons.append("recorte inestable")
        if not matte:
            reasons.append("sin recorte")
        ok = behind_mode == "on" or (behind_mode == "auto" and not reasons)
        if behind_mode == "off":
            ok = False
        shots.append({"startMs": a, "endMs": b, "cover": round(cov, 3), "face": round(face_h, 3),
                      "instability": round(inst, 4), "behind": ok, "why": reasons})
    n_ok = sum(1 for s in shots if s["behind"])
    if shots and behind_mode != "off":
        notes.append(f"tomas aptas para 'detrás': {n_ok} de {len(shots)}")
    for i, s in enumerate(shots):
        if not s["behind"] and s["why"] and behind_mode == "auto":
            notes.append(f"toma {i + 1} ({s['startMs'] / 1000:.1f}-{s['endMs'] / 1000:.1f}s): palabra grande delante — {', '.join(s['why'])}")
    bh = style.get("behind") or {}
    min_visible = float(bh.get("minVisible", 0.55))
    for b in cap.get("big") or []:
        if any(ch.isdigit() for ch in b["text"]):
            b["front"] = True
            continue
        shot = next((s for s in shots if s["startMs"] <= b["startMs"] < s["endMs"]), None)
        if shot is None or not shot["behind"]:
            b["front"] = True
            continue
        b["front"] = False
        if matte and matte.get("cells"):
            cells = big_box_cells(b, style, W, H, tuple(matte.get("grid", (9, 16))))
            fa = int(b["startMs"] * fps / 1000)
            fb = max(fa + 1, int(b["endMs"] * fps / 1000))
            frames = list(range(fa, min(fb, len(matte["cells"]))))[::3] or [min(fa, len(matte["cells"]) - 1)]
            hid = []
            for fi in frames:
                row = matte["cells"][fi]
                hid.append(sum(row[c] for c in cells) / (100 * max(1, len(cells))))
            hidden = sum(hid) / len(hid)
            if hidden > 1 - min_visible:
                if behind_mode == "on":  # la forzaste: se respeta, pero se avisa
                    warns.append(f"palabra grande '{b['text']}' ({b['startMs'] / 1000:.1f}s) queda {hidden:.0%} oculta detrás de la persona (--behind on)")
                else:
                    b["front"] = True
                    warns.append(f"palabra grande '{b['text']}' ({b['startMs'] / 1000:.1f}s) quedaba {hidden:.0%} oculta: va delante")
    return shots, notes, warns


def main(argv=None):
    paths.utf8_console()
    ap = argparse.ArgumentParser(description="Decide por toma si la palabra grande va detrás")
    ap.add_argument("captions", type=Path)
    ap.add_argument("--matte", type=Path)
    ap.add_argument("--subject", type=Path)
    ap.add_argument("--behind", default="auto", choices=["auto", "on", "off"])
    a = ap.parse_args(argv)
    cap = paths.read_json(a.captions)
    style = paths.load_style(cap["style"])
    shots, notes, warns = decide(cap, style, paths.read_json(a.matte) if a.matte else None,
                                 paths.read_json(a.subject) if a.subject else None, a.behind)
    cap["shots"] = shots
    paths.write_json(a.captions, cap)
    print("\n".join(notes + warns))


if __name__ == "__main__":
    main()
