"""Métriques de l'évaluation (sans dépendance externe, testées dans tests/test_llm_evaluation.py)."""

import math
import re
from collections import Counter
from collections.abc import Iterable
from typing import Any

from app.llm.language import DIALECT_FAMILY
from app.llm.text import normalize, parse_json_object  # noqa: F401 - réexporté pour les suites
from app.models.applications import MessageLanguage


def keyword_recall(answer: str, groups: Iterable[str]) -> float | None:
    """Part des groupes de mots-clés présents. Un groupe "a|b|c" est satisfait par une des variantes."""
    groups = list(groups)
    if not groups:
        return None
    text = normalize(answer)
    hits = sum(1 for g in groups if any(normalize(alt) in text for alt in g.split("|") if alt.strip()))
    return hits / len(groups)


def language_score(expected: str, detected: str) -> float:
    """1 = même langue ; 0,5 = même famille dialectale (ex. question Arabizi, réponse en tunisien arabe)
    ou réponse en français à un message mixte ; 0 sinon."""
    if expected == detected:
        return 1.0
    family = {lang.value for lang in DIALECT_FAMILY}
    if expected == MessageLanguage.mixed.value and detected in family | {"fr"}:
        return 1.0 if detected in family else 0.5
    if expected in family and detected in family:
        return 0.5
    return 0.0


_UNKNOWN_PATTERNS = [
    r"\bpas (d'|de )?(information|info|donnee|formation)", r"\bne (dispose|propose|trouve|connais|sais)",
    r"\baucun(e)?\b", r"\bn'existe pas", r"\bpas disponible", r"\bnon disponible", r"\bpas (dans|mentionne)",
    r"\bcontacte[rz]? l'administration", r"\bje ne peux pas", r"\bmalheureusement",
    r"ma3andich", r"ma 3andich", r"ma3andnach", r"ma 3andnach", r"mafamech", r"ma famech", r"mouch mawjoud",
    r"ma n3rafch", r"ma na3refch", r"famech", r"ma3andi hata",
    r"ماعنديش", r"معنديش", r"ما عنديش", r"ماعندناش", r"ما عندناش", r"مافماش", r"ما فماش", r"موش موجود",
    r"لا توجد", r"ليس لدي", r"غير متوفر", r"ما نعرفش", r"مانعرفش",
]
_UNKNOWN_RE = re.compile("|".join(_UNKNOWN_PATTERNS))
_MONEY_RE = re.compile(r"\d[\d\s.,]*\s*(tnd|dt|dinars?|دينار|د\.ت)", re.IGNORECASE)
_DOMAIN_RE = re.compile(
    r"formation|orientation|admission|inscription|iit|isb|licence|prepa|ingenieur|candidat|etude|"
    r"فورماسيون|تكوين|توجيه|تسجيل|قراية|دراسة|ليسانس|9raya|na9ra|t9ra"
)


def says_unknown(answer: str) -> bool:
    return bool(_UNKNOWN_RE.search(normalize(answer)))


def behaviour_ok(expected: str, answer: str) -> bool:
    """Comportement attendu : repondre / dire_inconnu (sans inventer de montant) / recentrer."""
    norm = normalize(answer)
    if expected == "dire_inconnu":
        return says_unknown(answer) and not _MONEY_RE.search(norm)
    if expected == "recentrer":
        return bool(_DOMAIN_RE.search(norm))
    return bool(norm) and not says_unknown(answer)


def chrf(hypothesis: str, reference: str, *, n: int = 6, beta: float = 2.0) -> float:
    """chrF (Popović 2015) : F-score de n-grammes de caractères (1..n), espaces ignorés, 0..100."""
    hyp, ref = normalize(hypothesis).replace(" ", ""), normalize(reference).replace(" ", "")
    if not hyp or not ref:
        return 0.0
    precisions, recalls = [], []
    for k in range(1, n + 1):
        h = Counter(hyp[i:i + k] for i in range(len(hyp) - k + 1))
        r = Counter(ref[i:i + k] for i in range(len(ref) - k + 1))
        if not h or not r:
            continue
        overlap = sum((h & r).values())
        precisions.append(overlap / sum(h.values()))
        recalls.append(overlap / sum(r.values()))
    if not precisions:
        return 0.0
    p, r = sum(precisions) / len(precisions), sum(recalls) / len(recalls)
    if p == 0 and r == 0:
        return 0.0
    b2 = beta * beta
    return 100 * (1 + b2) * p * r / (b2 * p + r)


def _flatten(value: Any) -> str:
    if isinstance(value, list | tuple):
        return " ".join(_flatten(v) for v in value)
    return "" if value is None else str(value)


def slot_scores(predicted: dict[str, Any] | None, gold: dict[str, Any]) -> tuple[float, float, float]:
    """(précision, rappel, F1) sur les champs du profil. Une valeur attendue "a|b" accepte a ou b ;
    une liste attendue est satisfaite si chacun de ses éléments est retrouvé."""
    predicted = {k: v for k, v in (predicted or {}).items() if v not in (None, "", [], {})}
    if not gold:
        return (1.0, 1.0, 1.0) if not predicted else (0.0, 1.0, 0.0)

    def match(expected: Any, got: Any) -> bool:
        text = normalize(_flatten(got))
        items = expected if isinstance(expected, list) else [expected]
        return all(any(normalize(alt) in text for alt in str(it).split("|")) for it in items)

    correct = sum(1 for k, v in gold.items() if k in predicted and match(v, predicted[k]))
    precision = correct / len(predicted) if predicted else 0.0
    recall = correct / len(gold)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def mean(values: Iterable[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def percentile(values: Iterable[float], q: float) -> float | None:
    vals = sorted(values)
    if not vals:
        return None
    k = (len(vals) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return vals[lo] + (vals[hi] - vals[lo]) * (k - lo)
