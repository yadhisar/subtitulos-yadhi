import paths
from group import build_captions, set_page_ends, to_srt
from numeros import convert_words


def _caps(words, style_name, video, cuts=None):
    style = paths.load_style(style_name)
    return build_captions(convert_words(words), style, video, cuts or []), style


def test_paginas_no_se_solapan(sample_words, video_1080):
    for name in ("glide", "bottom", "karaoke", "keyword"):
        cap, _ = _caps(sample_words, name, video_1080)
        pages = cap["pages"]
        assert pages
        for a, b in zip(pages, pages[1:]):
            assert a["endMs"] <= b["startMs"], (name, a, b)
        for p in pages:
            assert p["startMs"] < p["endMs"]


def test_ninguna_pagina_cruza_un_corte(sample_words, video_1080):
    cuts = [2500, 7300, 12000, 20450]
    cap, _ = _caps(sample_words, "glide", video_1080, cuts)
    for p in cap["pages"]:
        for c in cuts:
            assert not (p["startMs"] < c < p["endMs"]), (c, p["startMs"], p["endMs"])


def test_respeta_max_words_y_max_lines(sample_words, video_1080):
    for name in ("glide", "bottom", "karaoke", "keyword"):
        cap, style = _caps(sample_words, name, video_1080)
        pg = style["page"]
        for p in cap["pages"]:
            assert len(p["words"]) <= pg["maxWords"], (name, p)
            assert len({w["line"] for w in p["words"]}) <= pg["maxLines"], (name, p)


def test_un_monto_nunca_se_parte(sample_words, video_1080):
    cap, _ = _caps(sample_words, "bottom", video_1080)
    textos = [w["text"] for p in cap["pages"] for w in p["words"]]
    assert any("S/ 1,800 millones" in t for t in textos)
    assert any("S/ 5,000" in t for t in textos)
    assert any(t.startswith("40%") for t in textos)
    # ninguna página termina en "S/" o empieza con "millones"
    for p in cap["pages"]:
        assert p["words"][-1]["text"] not in ("S/", "S/.")
        assert not p["words"][0]["text"].startswith("millones")


def test_hold_400_y_700(video_1080):
    words = [{"text": "Hola", "startMs": 0, "endMs": 300, "prob": 1}, {"text": "Lima.", "startMs": 320, "endMs": 700, "prob": 1},
             {"text": "Chau", "startMs": 5000, "endMs": 5300, "prob": 1}]
    cap, _ = _caps(words, "glide", video_1080)
    assert cap["pages"][0]["endMs"] == 1100  # 700 + 400
    cap["pages"][0]["words"][1]["emphasis"] = True
    set_page_ends(cap)
    assert cap["pages"][0]["endMs"] == 1400  # 700 + 700 con highlight


def test_srt(sample_words, video_1080):
    cap, _ = _caps(sample_words, "karaoke", video_1080)
    srt = to_srt(cap)
    assert srt.startswith("1\n00:00:00,")
    assert "-->" in srt and "TikTok" in srt
