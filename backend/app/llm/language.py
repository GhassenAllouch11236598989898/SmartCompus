"""SA-34 — Détection de la langue d'un message : français, dialecte tunisien (graphie arabe),
Arabizi (dialecte tunisien en caractères latins + chiffres), arabe standard, anglais, mélange.

Heuristique volontairement légère (aucune dépendance, < 1 ms) : elle sert à remplir
``messages.detected_language`` et à demander au LLM de répondre dans la langue du candidat.
Ses performances sont mesurées par ``python -m evaluation.run_eval --suite detecteur``.

Règles :
- graphie arabe : marqueurs du dialecte tunisien (شنوة, كيفاش, برشا...) -> ``tn_darija``, sinon ``ar`` ;
- graphie latine : chiffres-lettres dans un mot (3, 5, 7, 9...) ou lexique Arabizi -> ``arabizi`` ;
  mots-outils français -> ``fr`` ; anglais -> ``en`` ;
- les deux graphies, ou Arabizi et français équilibrés (code-switching) -> ``mixed``.
"""

import re
import unicodedata
from dataclasses import dataclass

from app.models.applications import MessageLanguage

_ARABIC_CHAR = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")
_LATIN_CHAR = re.compile(r"[A-Za-zÀ-ÿ]")
_TOKEN = re.compile(r"[\w']+", re.UNICODE)
# Un chiffre collé à des lettres (ex. "9adech", "ya3tik", "sa7a", "m3a") : signature de l'Arabizi.
# Au moins deux lettres : "l2", "m1" ou "bac+2" (niveaux d'études) ne sont pas de l'Arabizi.
_ARABIZI_DIGIT_WORD = re.compile(r"^(?=(?:.*[a-z]){2})(?=.*[235789])[a-z235789']+$")
_FRENCH_ELISION = re.compile(r"^(?:d|l|j|qu|c|n|s|m|t)'[a-zà-ÿ]{2,}$")

TN_DARIJA_MARKERS = frozenset({
    "شنوة", "شنوا", "شنية", "شني", "كيفاش", "قداش", "علاش", "وقتاش", "وين", "شكون", "برشا", "برشة",
    "ياسر", "باش", "بش", "متاع", "متع", "فمّا", "فما", "توّا", "توا", "نحب", "نحبّ", "نجم", "نعرف",
    "موش", "مش", "مانيش", "ماعنديش", "معنديش", "عندي", "نقرا", "قريت", "نخدم", "زادة", "زاده",
    "بالڤدا", "باهي", "يعيشك", "عسلامة", "عالسلامة", "ڤداش", "كان", "حاجة", "برك", "هكا", "هاذا",
    "هاذي", "إنتي", "انتي", "إنتوما", "آنا", "انا", "يزي", "خاطر", "نشوف", "تنجم", "بعد", "توة",
})
MSA_MARKERS = frozenset({
    "ما", "ماذا", "كيف", "هل", "أريد", "اريد", "لماذا", "التي", "الذي", "هذه", "هذا", "يمكنني", "أود",
    "الرسوم", "شروط", "القبول",
})
ARABIZI_MARKERS = frozenset({
    "chnowa", "chnowa", "chnoua", "chniya", "chneya", "chnia", "chnou", "kifech", "kifach", "kifeh",
    "9adech", "qadech", "adech", "3lech", "alech", "wa9tech", "waqtech", "win", "chkoun", "chkon",
    "barcha", "barsha", "yesser", "bech", "bch", "mte3", "mta3", "mtaa", "famma", "fama", "taw", "tawa",
    "nheb", "n7eb", "nhib", "n7ib", "nejem", "nnajem", "najem", "na3ref", "n3ref", "mouch", "mech",
    "mich", "manich", "ma3andich", "3andi", "andi", "n9ra", "nakra", "9rit", "krit", "nekhdem", "zeda",
    "zada", "behi", "bahi", "ya3tik", "sa7a", "saha", "3aslema", "aslema", "salem", "brabi", "chbik",
    "ena", "inti", "enti", "intouma", "houa", "hiya", "kima", "kan", "ken", "barka", "hakka", "hedha",
    "hedhi", "yezzi", "5ater", "khater", "nchouf", "tnajem", "ba3d", "9bal", "kbal", "lazem", "lezem",
    "wela", "walla", "ama", "chnaya", "fel", "fil", "mel", "mil", "3al", "lel", "nemchi", "ne5dem",
    "na9ra", "inchallah", "n7ebb", "nheb", "9raya", "9ari", "fi", "w", "m3a", "ma3", "jem3a", "nwalli",
    "chnouma", "9a3ed", "nsajel", "nsajjel", "flous", "soum", "bel", "bil", "elli", "illi", "el", "ya",
    "chnia", "nod5ol", "nodkhol", "lel", "far9", "tnasa7ni", "tnasba7li", "nwalli", "mitakked", "bin",
})
FRENCH_MARKERS = frozenset({
    "le", "la", "les", "un", "une", "des", "du", "de", "et", "est", "je", "vous", "pour", "quels",
    "quelle", "quelles", "quel", "comment", "pourquoi", "combien", "est-ce", "que", "qui", "avec",
    "dans", "sur", "pas", "mon", "ma", "mes", "votre", "vos", "il", "elle", "nous", "sont", "suis",
    "ai", "au", "aux", "ce", "cette", "c'est", "j'ai", "voudrais", "veux", "peux", "bonjour", "merci",
    "après", "aussi", "ou", "entre", "faire", "faut", "proposez", "avez", "puis", "peut", "êtes", "être",
})
# Les noms du domaine (licence, frais, formation...) sont des emprunts courants en Arabizi :
# seuls les mots-outils et les élisions (d', l', j'...) comptent comme français.
ENGLISH_MARKERS = frozenset({
    "the", "is", "are", "what", "how", "which", "i", "you", "want", "fees", "can", "and", "of", "to",
    "my", "do", "does", "hello", "hi", "please", "thanks", "for", "with",
})
# Mots ambigus français/Arabizi : ne comptent pas comme preuve d'Arabizi seuls.
_AMBIGUOUS = frozenset({"fi", "w", "kan", "ken", "win", "ama", "salem", "bel", "mil", "fel", "fil", "mel"})


@dataclass(frozen=True)
class LanguageGuess:
    language: MessageLanguage
    confidence: float  # 0..1, arrondi à 2 décimales (colonne NUMERIC(3,2))


def _strip_accents(word: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", word) if unicodedata.category(c) != "Mn")


def _guess(lang: MessageLanguage, conf: float) -> LanguageGuess:
    return LanguageGuess(lang, round(max(0.0, min(conf, 1.0)), 2))


def detect_language(text: str) -> LanguageGuess:
    """Détecte la langue dominante d'un message candidat."""
    text = (text or "").strip()
    if not text:
        return _guess(MessageLanguage.unknown, 0.0)

    n_ar = len(_ARABIC_CHAR.findall(text))
    n_lat = len(_LATIN_CHAR.findall(text))
    if n_ar == 0 and n_lat == 0:
        return _guess(MessageLanguage.unknown, 0.0)

    tokens = _TOKEN.findall(text.lower())
    ar_tokens = [t for t in tokens if _ARABIC_CHAR.search(t)]
    lat_tokens = [t for t in tokens if not _ARABIC_CHAR.search(t) and _LATIN_CHAR.search(t)]

    # --- Deux graphies significatives : code-switching (ex. "نحب نعرف les frais").
    if n_ar and n_lat and min(len(ar_tokens), len(lat_tokens)) >= 2:
        return _guess(MessageLanguage.mixed, 0.7)

    if n_ar >= n_lat:
        tn = sum(t in TN_DARIJA_MARKERS for t in ar_tokens)
        msa = sum(t in MSA_MARKERS for t in ar_tokens)
        # Préfixe tunisien "ب" + verbe (باش) ou négation "ما...ش" (ماعنديش, مانيش, منجمش).
        tn += sum(1 for t in ar_tokens if len(t) > 3 and t.startswith("م") and t.endswith("ش"))
        if tn > msa:
            return _guess(MessageLanguage.tn_darija, 0.6 + 0.1 * min(tn, 4))
        if msa > 0:
            return _guess(MessageLanguage.ar, 0.6 + 0.1 * min(msa, 3))
        return _guess(MessageLanguage.tn_darija if len(ar_tokens) <= 4 else MessageLanguage.ar, 0.5)

    words = [_strip_accents(t) for t in lat_tokens]
    digit_words = sum(1 for t in lat_tokens if _ARABIZI_DIGIT_WORD.match(t))
    arabizi_words = sum(
        1 for t, w in zip(lat_tokens, words, strict=True)
        if _ARABIZI_DIGIT_WORD.match(t) or (w in ARABIZI_MARKERS and w not in _AMBIGUOUS)
    )
    french = sum(1 for t in lat_tokens if t in FRENCH_MARKERS or _FRENCH_ELISION.match(t))
    # Négation tunisienne "ma ... ch" (ma najjamtech, ma 3andich) : "ma" n'est alors pas français.
    negations = sum(
        1 for a, b in zip(lat_tokens, lat_tokens[1:], strict=False) if a == "ma" and len(b) > 3 and b.endswith("ch")
    )
    arabizi_words += negations
    french -= negations
    english = sum(1 for t in lat_tokens if t in ENGLISH_MARKERS)
    total = max(len(lat_tokens), 1)

    if arabizi_words == 0:
        if english > french:
            return _guess(MessageLanguage.en, 0.5 + 0.5 * english / total)
        if french:
            return _guess(MessageLanguage.fr, 0.6 + 0.4 * french / total)
        return _guess(MessageLanguage.unknown, 0.3)

    # Code-switching : part des mots-outils français parmi les mots identifiés.
    if french >= 2:
        share = french / (french + arabizi_words)
        if share > 0.85:
            return _guess(MessageLanguage.fr, 0.6)
        if share >= 0.4:
            return _guess(MessageLanguage.mixed, 0.6)
    return _guess(MessageLanguage.arabizi, 0.6 + 0.4 * min(arabizi_words + digit_words, 5) / 5)


DIALECT_FAMILY = frozenset({MessageLanguage.tn_darija, MessageLanguage.arabizi, MessageLanguage.mixed})


def language_label(lang: MessageLanguage) -> str:
    """Libellé lisible pour le prompt système (consigne « réponds dans la langue du candidat »)."""
    return {
        MessageLanguage.fr: "français",
        MessageLanguage.ar: "arabe standard",
        MessageLanguage.tn_darija: "dialecte tunisien en graphie arabe",
        MessageLanguage.arabizi: "dialecte tunisien en Arabizi (lettres latines et chiffres 3, 7, 9...)",
        MessageLanguage.en: "anglais",
        MessageLanguage.mixed: "mélange dialecte tunisien / français (code-switching), comme le candidat",
        MessageLanguage.unknown: "français",
    }[lang]
