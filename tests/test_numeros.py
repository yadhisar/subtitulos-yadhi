import pytest

from numeros import convert_text, convert_words


@pytest.mark.parametrize(
    "oido, esperado",
    [
        ("cinco mil soles", "S/ 5,000"),
        ("mil ochocientos millones de soles", "S/ 1,800 millones"),
        ("cuarenta por ciento", "40%"),
        ("dos mil veinticuatro", "2024"),
        ("cien dólares", "$100"),
        ("tres veces", "3x"),
        ("treinta y cinco por ciento", "35%"),
        ("doscientos cincuenta mil soles", "S/ 250,000"),
        ("cinco soles con cincuenta", "S/ 5.50"),
        ("un millón de soles", "S/ 1 millón"),
        ("mil novecientos noventa y nueve", "1999"),
        ("veinte años", "20 años"),
        ("dos punto cinco millones", "2.5 millones"),
    ],
)
def test_numeros_hablados(oido, esperado):
    assert convert_text(oido) == esperado


@pytest.mark.parametrize(
    "frase",
    ["tengo dos hijos y una tienda", "mil gracias", "una vez al mes", "al cien"],
)
def test_no_toca_numeros_chicos_ni_frases_hechas(frase):
    assert convert_text(frase) == frase


def test_respeta_cifras_ya_escritas():
    assert convert_text("el 40% es S/5,000.") == "el 40% es S/5,000."
    assert convert_text("cobré 1.800 soles") == "cobré S/ 1.800"


def test_porcentaje_con_signo_aparte():
    assert convert_text("cerca del 50 % de la venta") == "cerca del 50% de la venta"
    assert convert_text("cuarenta %") == "40%"


def test_puntuacion_se_queda_pegada():
    assert convert_text("¿cuarenta y cinco soles?") == "¿S/ 45?"
    assert convert_text("son cinco mil soles.") == "son S/ 5,000."


def test_monto_es_un_solo_token_con_tiempos():
    words = [{"text": t, "startMs": i * 100, "endMs": i * 100 + 80, "prob": 0.9}
             for i, t in enumerate("gané mil ochocientos millones de soles hoy".split())]
    out = convert_words(words)
    assert [w["text"] for w in out] == ["gané", "S/ 1,800 millones", "hoy"]
    tok = out[1]
    assert tok["num"] is True
    assert tok["startMs"] == 100 and tok["endMs"] == 580


def test_no_cruza_punto_final():
    assert convert_text("eran cinco. Mil personas") == "eran cinco. Mil personas"
