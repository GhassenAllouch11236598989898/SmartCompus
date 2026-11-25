"""Normalisation de texte multilingue (français, arabe, Arabizi) pour la comparaison et l'extraction."""

import json
import re
import unicodedata
from typing import Any

_AR_DIACRITICS = re.compile(r"[ً-ْـ]")  # harakat + tatweel
_AR_UNIFY = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه", "ى": "ي", "ڤ": "ق", "پ": "ب"})
_SPACES = re.compile(r"\s+")
_NUM_SEP = re.compile(r"(?<=\d)[\s.  ](?=\d{3}\b)")  # 5 200 / 5.200 -> 5200


def normalize(text: str) -> str:
    """Minuscules, sans accents latins ni diacritiques arabes, lettres arabes unifiées, milliers collés."""
    text = unicodedata.normalize("NFKC", text or "").lower().translate(_AR_UNIFY)
    text = _AR_DIACRITICS.sub("", text)
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    text = _NUM_SEP.sub("", text)
    return _SPACES.sub(" ", text).strip()


def parse_json_object(text: str) -> dict[str, Any] | None:
    """Premier objet JSON de la réponse (tolère ```json ... ``` et du texte autour)."""
    if not text:
        return None
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        value = json.loads(text[start:i + 1])
                    except ValueError:
                        break
                    return value if isinstance(value, dict) else None
        start = text.find("{", start + 1)
    return None
