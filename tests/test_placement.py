import paths
import textbox
from emphasis import auto
from group import build_captions
from numeros import convert_words
from placement import place


def _subject(face, hands=None, dur=32000):
    return {"fps": 4, "samples": [{"ms": ms, "faces": [face], "hands": hands or []} for ms in range(0, dur, 250)]}


def _caps(words, name, video):
    style = paths.load_style(name)
    cap = build_captions(convert_words(words), style, video, [])
    auto(cap, "auto", "Lima, TikTok", None, style)
    return cap, style


def test_ninguna_pagina_encima_de_la_cara_ni_fuera_de_zona_segura(sample_words, video_1080):
    W, H = video_1080["width"], video_1080["height"]
    # cara grande a media pantalla, justo donde los estilos ponen el texto por defecto
    face = [0.30, 0.38, 0.40, 0.26]
    for name in ("glide", "bottom", "karaoke", "keyword"):
        cap, style = _caps(sample_words, name, video_1080)
        place(cap, style, _subject(face))
        for p in cap["pages"]:
            b = textbox.page_box(p, style, W, H)
            assert textbox.in_safe_zone(b, W, H), (name, p["y"], b)
            assert not textbox.overlaps(b, [face], W, H), (name, p["y"], b)


def test_sin_cara_no_mueve_nada(sample_words, video_1080):
    cap, style = _caps(sample_words, "glide", video_1080)
    notes = place(cap, style, {"fps": 4, "samples": []})
    assert all(p["y"] in (None, style["position"]["y"]) for p in cap["pages"])
    assert not any("movida" in n for n in notes)


def test_altura_fija_para_todo_el_video(sample_words, video_1080):
    cap, style = _caps(sample_words, "karaoke", video_1080)
    place(cap, style, _subject([0.32, 0.45, 0.36, 0.22]))
    ys = {p["y"] for p in cap["pages"]}
    assert len(ys) == 1  # misma cara todo el rato -> una sola altura


def test_manos_solo_mueven_esas_paginas(sample_words, video_1080):
    cap, style = _caps(sample_words, "glide", video_1080)
    sub = _subject([0.35, 0.15, 0.30, 0.18])
    # manos delante del texto solo entre 9 y 12 s
    for s in sub["samples"]:
        if 9000 <= s["ms"] <= 12000:
            s["hands"] = [[0.2, 0.5, 0.6, 0.12]]
    notes = place(cap, style, sub)
    W, H = video_1080["width"], video_1080["height"]
    for p in cap["pages"]:
        b = textbox.page_box(p, style, W, H)
        assert textbox.in_safe_zone(b, W, H)
    assert any("movida" in n for n in notes)
