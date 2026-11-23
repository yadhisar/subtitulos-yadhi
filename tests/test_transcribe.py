from transcribe import apply_replace, parse_replace, postprocess


def _w(text):
    return [{"text": t, "startMs": i * 100, "endMs": i * 100 + 90, "prob": 0.9} for i, t in enumerate(text.split())]


def test_replace_una_y_varias_palabras():
    words = _w("Hola, soy de tik tok. en lima")
    out = apply_replace(words, parse_replace(["tik tok=TikTok", "lima=Lima"]))
    assert [w["text"] for w in out] == ["Hola,", "soy", "de", "TikTok.", "en", "Lima"]
    assert out[3]["startMs"] == 300 and out[3]["endMs"] == 490


def test_postprocess_aplica_numeros_despues_del_replace():
    data = {"words": _w("cobra cinco mil lucas")}
    out = postprocess(data, ["cobra=Cobra"])
    assert [w["text"] for w in out["words"]] == ["Cobra", "S/ 5,000"]
