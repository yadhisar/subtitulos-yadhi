import pytest

import emphasis
import paths
from group import build_captions
from numeros import convert_words


@pytest.fixture
def caps(sample_words, video_1080):
    out = {}
    for name in ("glide", "bottom", "karaoke", "keyword"):
        style = paths.load_style(name)
        cap = build_captions(convert_words(sample_words), style, video_1080, [])
        emphasis.auto(cap, "auto", "Lima, TikTok, Instagram", None, style)
        out[name] = (cap, style)
    return out


def test_maximo_por_pagina_y_sin_stopwords(caps):
    for name, (cap, _) in caps.items():
        total = 0
        for p in cap["pages"]:
            on = [w for w in p["words"] if w["emphasis"]]
            total += len(on)
            assert len(on) <= (2 if len(p["words"]) >= 5 else 1), (name, p)
            for w in on:
                assert not emphasis.is_stop(w["text"]), (name, w)
                assert w["reason"], (name, w)
        assert total > 0, name


def test_prioridad_numeros_y_marcas(caps):
    cap, _ = caps["glide"]
    on = {w["text"].rstrip(".,"): w["reason"] for p in cap["pages"] for w in p["words"] if w["emphasis"]}
    assert on.get("S/ 1,800 millones") == "número"
    assert on.get("40%") == "número"
    assert any(r == "nombre/marca" for r in on.values())


def test_modo_numbers_y_off(sample_words, video_1080):
    style = paths.load_style("glide")
    cap = build_captions(convert_words(sample_words), style, video_1080, [])
    emphasis.auto(cap, "numbers", style=style)
    on = [w for p in cap["pages"] for w in p["words"] if w["emphasis"]]
    assert on and all(w["reason"] == "número" for w in on)
    emphasis.auto(cap, "off", style=style)
    assert not any(w["emphasis"] for p in cap["pages"] for w in p["words"])


def test_pick_drop_y_stopword(caps):
    cap, style = caps["glide"]
    k = next(i for i, p in enumerate(cap["pages"]) if any("rápido" in w["text"] for w in p["words"]))
    emphasis.pick(cap, f"{k + 1}:rápido=remate")
    w = next(w for w in cap["pages"][k]["words"] if "rápido" in w["text"])
    assert w["emphasis"] and w["reason"] == "remate"
    assert sum(x["emphasis"] for x in cap["pages"][k]["words"]) <= emphasis.limit_for(cap["pages"][k])
    emphasis.drop(cap, f"{k + 1}:rápido")
    assert not w["emphasis"]
    j = next(i for i, p in enumerate(cap["pages"]) if any(x["text"].lower() == "de" for x in p["words"]))
    with pytest.raises(SystemExit):
        emphasis.pick(cap, f"{j + 1}:de")


def test_palabras_pedidas_con_coma_de_miles(sample_words, video_1080):
    assert emphasis.split_words_arg("S/ 1,800 millones, gratis") == ["S/ 1,800 millones", "gratis"]
    style = paths.load_style("glide")
    cap = build_captions(convert_words(sample_words), style, video_1080, [])
    emphasis.auto(cap, "auto", forced="S/ 5,000", style=style)
    w = next(w for p in cap["pages"] for w in p["words"] if w["text"].startswith("S/ 5,000"))
    assert w["emphasis"] and w["reason"] == "pedido por ti"


def test_big_keyword_numeros_delante(caps):
    cap, _ = caps["keyword"]
    assert cap["big"], "keyword debe tener palabras grandes"
    for b in cap["big"]:
        if any(ch.isdigit() for ch in b["text"]):
            assert b["front"] is True
    for a, b in zip(cap["big"], cap["big"][1:]):
        assert a["endMs"] <= b["startMs"]
    cap_g, _ = caps["glide"]
    assert cap_g["big"] == []
