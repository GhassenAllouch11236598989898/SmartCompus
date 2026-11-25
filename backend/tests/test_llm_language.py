"""SA-34 — Détecteur de langue (français, dialecte tunisien, Arabizi, mélange). Sans base de données."""

import pytest

from app.llm.language import detect_language, language_label
from app.models.applications import MessageLanguage as L


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Bonjour, quelles sont les conditions d'admission en licence ?", L.fr),
        ("Je viens d'une autre école après une L2, comment intégrer le cycle ingénieur ?", L.fr),
        ("ma moyenne est de 12", L.fr),
        ("9adech flous el licence gestion ?", L.arabizi),
        ("aslema, ya3tik sa7a", L.arabizi),
        ("w ken ma najjamtech fel bac ?", L.arabizi),
        ("chnia les conditions bech nod5ol lel prepa ?", L.arabizi),
        ("شنوة الفورماسيونات اللي فمّا ؟", L.tn_darija),
        ("ماعنديش برشا فلوس", L.tn_darija),
        ("ما هي شروط القبول في الماجستير ؟", L.ar),
        ("nheb na3ref les frais d'inscription mta3 cycle ingénieur", L.mixed),
        ("نحب نعرف la différence entre prépa et licence", L.mixed),
        ("What are the fees for the engineering program?", L.en),
    ],
)
def test_detect_language(text, expected):
    assert detect_language(text).language == expected


@pytest.mark.parametrize("text", ["", "   ", "😀", "123"])
def test_detect_language_unknown(text):
    guess = detect_language(text)
    assert guess.language == L.unknown
    assert guess.confidence == 0.0


def test_confidence_fits_numeric_3_2():
    for text in ["9adech", "Bonjour", "شنوة", "ok"]:
        c = detect_language(text).confidence
        assert 0 <= c <= 1 and round(c, 2) == c


def test_language_label_covers_all_values():
    assert all(language_label(lang) for lang in L)
