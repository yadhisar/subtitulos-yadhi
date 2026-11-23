import pytest

import fuentes
import paths
import personalizar
import textbox


def test_colores_hex_y_nombres():
    assert personalizar.parse_color("#ff4fa3") == "#FF4FA3"
    assert personalizar.parse_color("f00") == "#FF0000"
    assert personalizar.parse_color("Rosa") == "#FF4FA3"
    assert personalizar.parse_color("yellow") == "#FFD60A"
    with pytest.raises(SystemExit):
        personalizar.parse_color("colorinventado")


def test_paleta_y_flags_sueltos_mandan():
    st = personalizar.apply(paths.load_style("glide"), {"palette": "tiktok", "color": "crema"})
    assert st["activeColor"] == "#FE2C55"
    assert st["color"] == "#FFF4E0"


def test_paleta_cambia_tambien_la_palabra_grande():
    st = personalizar.apply(paths.load_style("keyword"), {"palette": "neon"})
    assert st["behind"]["bigColor"] == "#39FF14"


def test_accent_auto_y_stroke_none():
    st = personalizar.apply(paths.load_style("bottom"), {"accent": "auto", "stroke": "none"})
    assert st["activeColor"]["auto"] == "accent"
    assert st["stroke"] is None


def test_todas_las_paletas_son_validas():
    for name in personalizar.colores()["paletas"]:
        st = personalizar.apply(paths.load_style("karaoke"), {"palette": name})
        assert st["color"].startswith("#")


@pytest.mark.parametrize(
    "spec, esperado",
    [
        ("Bebas Neue", ("Bebas Neue", None, False)),
        ("Poppins:800", ("Poppins", 800, False)),
        ("Poppins ExtraBold", ("Poppins", 800, False)),
        ("Playfair Display:700i", ("Playfair Display", 700, True)),
        ("Lora Bold Italic", ("Lora", 700, True)),
    ],
)
def test_parse_font(spec, esperado):
    assert fuentes.parse_spec(spec) == esperado


def test_font_del_pack_sin_descargar():
    f = fuentes.resolve("Poppins:800", download=False)
    assert f["file"] == "Poppins-ExtraBold.ttf" and f["weight"] == 800
    f = fuentes.resolve("Bebas Neue", download=False)
    assert f["file"] == "BebasNeue-Regular.ttf"
    assert (paths.FONTS / f["file"]).exists()


def test_font_override_cambia_la_medida():
    base = paths.load_style("glide")
    page = {"words": [{"text": "Hola", "line": 0}, {"text": "mundo", "line": 0}], "y": None}
    w0 = textbox.page_box(page, base, 1080, 1920)
    st = personalizar.apply(base, {"font": "Bebas Neue", "size": "1.3"})
    w1 = textbox.page_box(page, st, 1080, 1920)
    assert st["font"]["file"] == "BebasNeue-Regular.ttf"
    assert abs(st["size"] - base["size"] * 1.3) < 1e-6
    assert (w1["y1"] - w1["y0"]) > (w0["y1"] - w0["y0"])


def test_cada_familia_del_pack_tiene_licencia():
    lic = {p.stem.split("-", 1)[1] for p in paths.FONTS.glob("*.txt")}
    for sl in fuentes.installed():
        assert sl in lic, sl
