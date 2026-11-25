"""SA-37 — Mémoire conversationnelle du candidat.

Deux niveaux, comme demandé par le cahier des charges (« niveau, centres d'intérêt, préférences,
questions déjà posées et choix envisagés ») :

1. **Mémoire courte** : les derniers messages de la conversation (table ``messages``), envoyés au LLM
   dans une fenêtre bornée en nombre de messages et en caractères (``LLM_MEMORY_MAX_*``).
2. **Mémoire longue** : un profil candidat structuré, mis à jour à chaque message et stocké dans
   ``conversations.memory`` (JSONB). Il reste dans le prompt même quand les anciens messages sortent
   de la fenêtre : le bot n'oublie pas la moyenne donnée au premier message.

L'extraction du profil se fait par règles (français, tunisien en graphie arabe, Arabizi : aucune
latence ajoutée) ou, en option (``LLM_MEMORY_EXTRACTION=llm``), par le LLM avec repli sur les règles.

Point d'intégration avec les sessions visiteurs (SA-23 à SA-25) : ``ConversationMemory.from_json`` /
``to_json`` suffisent à brancher un autre stockage.
"""

import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from app.llm.client import ChatMessage
from app.llm.text import normalize

LIST_FIELDS = ("interets", "preferences", "contraintes", "formations_evoquees")
SCALAR_FIELDS = ("niveau", "section_bac", "moyenne", "objectif")
MAX_LIST_ITEMS = 10
MAX_QUESTIONS = 8

PROFILE_LABELS = {
    "niveau": "Niveau d'études",
    "section_bac": "Section du bac",
    "moyenne": "Moyenne",
    "interets": "Centres d'intérêt",
    "preferences": "Préférences",
    "contraintes": "Contraintes",
    "objectif": "Projet professionnel",
    "formations_evoquees": "Formations évoquées",
}


# ======================================================================== extraction par règles
def _any(text: str, patterns: Iterable[str]) -> bool:
    return any(re.search(p, text) for p in patterns)


_W = r"(?<![\w])"  # début de mot (fonctionne aussi pour l'arabe)
_E = r"(?![\w])"   # fin de mot
_P = _W + r"(?:[وبلف]?ال|[وبلف])?"  # + préfixes arabes collés : و، ب، ل، ف، ال (والذكاء, بالانفو...)

SECTIONS = {  # valeur canonique -> motifs (texte normalisé : minuscules, sans accents, arabe unifié)
    "mathématiques": [r"maths?", r"mathematiques?", r"رياضيات", r"ماث"],
    "sciences expérimentales": [r"sciences?(?: exp\w*)?", r"sc\.? ?exp", r"سيانس", r"علوم"],
    "informatique": [r"info(?:rmatique)?", r"انفو", r"اعلاميه"],
    "technique": [r"techniques?", r"tech", r"تقني(?:ه)?"],
    "économie et gestion": [r"eco(?:nomie)?(?: (?:et |w )?gestion)?", r"gestion", r"اقتصاد"],
    "lettres": [r"lettres?", r"اداب"],
    "sport": [r"sports?", r"رياضه"],
}
_BAC = r"(?:bac(?:calaureat)?|باك|section|شعبه|terminale)"

INTERESTS = {
    "informatique": [r"informatique", r"info", r"انفورماتيك", r"الانفورماتيك", r"اعلاميه", r"programmation",
                     r"prog", r"cod(?:e|age|ing)"],
    "intelligence artificielle": [r"ia", r"ai", r"intelligence artificielle", r"ذكاء(?: ال)?(?:اصطناعي)?"],
    "robotique": [r"robotique", r"robots?", r"روبوتيك"],
    "data": [r"data(?: science)?", r"donnees", r"داتا"],
    "développement web": [r"web", r"sites?(?: web)?"],
    "réseaux et sécurité": [r"reseaux?", r"securite", r"cyber\w*"],
    "mathématiques": [r"maths?", r"mathematiques?", r"رياضيات", r"الماث", r"ماث"],
    "physique": [r"physique", r"فيزياء"],
    "gestion": [r"gestion", r"management", r"جستيون"],
    "marketing": [r"marketing", r"ماركتينغ"],
    "finance et comptabilité": [r"finance", r"compta(?:bilite)?", r"محاسبه"],
}
_LIKE = [r"nheb+", r"n7eb+", r"nhib", r"n7ib", r"j'aime", r"aime", r"j'adore", r"adore", r"passionne",
         r"interess\w*", r"نحب", r"يعجبني", r"نموت على", r"تستهويني", r"7aja nheb", r"ye3jebni", r"yi3jebni"]

PREFERENCES = {
    "formation pratique": [r"pratiques?", r"concret", r"terrain", r"3amali", r"عمليه", r"تطبيقي"],
    # "pratique akthar mel théorie" (plus pratique QUE théorique) ne compte pas comme préférence théorique.
    "formation théorique": [r"(?<!mel )(?<!men )(?<!que )(?<!من )theori(?:que|e)", r"(?<!من )نظري"],
    "parcours progressif": [r"progressi(?:f|ve)", r"chwaya b chwaya", r"شويه بشويه"],
    "enseignement hybride ou en ligne": [r"en ligne", r"online", r"hybride", r"a distance", r"عن بعد"],
}
CONSTRAINTS = {
    # Demander un prix ("9adech el flous ?") n'est pas une contrainte : il faut un manque ou un "trop cher".
    "budget limité": [r"ma ?3andi(?:ch|sh) (?:barcha )?flous", r"flous (?:9lal|9lil)", r"budget", r"ghal(?:i|ya)",
                      r"(?:trop |tres |barcha )cher", r"ar5es", r"arkhes", r"moins cher", r"م(?:ا ?)?عنديش (?:برشا )?فلوس",
                      r"غالي", r"ارخص", r"ميزانيه"],
}
CITIES = {"tunis": "Tunis", "sfax": "Sfax", "sousse": "Sousse", "monastir": "Monastir", "nabeul": "Nabeul",
          "bizerte": "Bizerte", "gabes": "Gabès", "kairouan": "Kairouan", "ariana": "Ariana",
          "صفاقس": "Sfax", "تونس": "Tunis", "سوسه": "Sousse", "المنستير": "Monastir", "نابل": "Nabeul",
          "بنزرت": "Bizerte", "قابس": "Gabès", "القيروان": "Kairouan"}

FORMATIONS = {
    "Cycle préparatoire intégré": [r"prepa", r"preparatoire", r"بريبا", r"تحضيري"],
    "Licence en Informatique": [r"licence (?:en )?info(?:rmatique)?", r"ليسانس (?:في )?(?:ال)?انفو\w*"],
    "Licence en Gestion": [r"licence (?:en )?gestion", r"ليسانس (?:في )?(?:ال)?جستيون"],
    "Cycle ingénieur": [r"ingenieurs?", r"cycle ing", r"انجينيور", r"الانجينيور", r"مهندس"],
    "Master Marketing digital": [r"master", r"ماستر", r"ماجستير"],
}

_NUM = r"(\d{1,2}(?:[.,]\d{1,2})?)"
_AVERAGE_PATTERNS = [
    rf"(?:moyenne|moyen|moy|معدل|معدلي)\D{{0,20}}?{_NUM}",
    rf"(?:jebt|jibt|khdhit|5dhit|j'ai eu|ai eu|جبت|خذيت)\s+{_NUM}",
    rf"{_NUM}\s*(?:/\s*20|sur 20|de moyenne|de moy|moyenne|معدل)",
]
_GOAL = re.compile(r"(?i)(?:devenir|nwalli|nweli|نولي|نخدم|travailler comme|metier de|travailler en)\s+([^?.!,;\n]{3,60})")


def _put(profile: dict[str, Any], key: str, value: Any) -> None:
    if key in LIST_FIELDS:
        current = profile.setdefault(key, [])
        for v in value if isinstance(value, list) else [value]:
            if v and v not in current:
                current.append(v)
        del current[:-MAX_LIST_ITEMS]
    elif value not in (None, ""):
        profile[key] = value


def extract_profile(message: str) -> dict[str, Any]:
    """Informations de profil trouvées dans un message candidat (règles, sans LLM)."""
    text = normalize(message)
    found: dict[str, Any] = {}

    for pattern in _AVERAGE_PATTERNS:
        if m := re.search(pattern, text):
            value = float(m.group(1).replace(",", "."))
            if 0 < value <= 20:
                found["moyenne"] = f"{value:g}"
                break

    for m in re.finditer(rf"{_W}{_BAC}\s+(?:de |en |fi |في |متاع )?(\S+(?: \S+)?)", text):
        tail = m.group(1)
        section = next((c for c, pats in SECTIONS.items() if _any(tail, [rf"^{p}{_E}" for p in pats])), None)
        if section:
            found["section_bac"] = section
            break

    if re.search(r"terminale|terminal|بكالوريا هذا العام|fel bac (?:hedha|el 3am)", text):
        found["niveau"] = "terminale"
    elif m := re.search(r"bac\s*\+\s*([1-8])", text):
        found["niveau"] = f"bac+{m.group(1)}"
    elif m := re.search(rf"{_W}l([123]){_E}", text):
        found["niveau"] = f"licence {m.group(1)}e année (bac+{m.group(1)})"
    elif re.search(r"(?:3andi|andi|j'ai (?:une|ma)|عندي) (?:licence|ليسانس)", text):
        found["niveau"] = "licence (bac+3)"
    elif re.search(r"(?:j'ai (?:eu )?(?:mon )?bac|bachelier|9rit bac|krit bac|5dhit (?:el )?bac|3andi (?:el )?bac|"
                   r"نجحت في الباك|قريت باك|عندي (?:ال)?باك|خذيت (?:ال)?باك)", text):
        found["niveau"] = "bachelier"

    if _any(text, _LIKE):
        _put(found, "interets", [k for k, pats in INTERESTS.items() if _any(text, [rf"{_P}{p}{_E}" for p in pats])])
    _put(found, "preferences", [k for k, pats in PREFERENCES.items() if _any(text, [rf"{_P}{p}" for p in pats])])
    _put(found, "contraintes", [k for k, pats in CONSTRAINTS.items() if _any(text, [rf"{_P}{p}" for p in pats])])
    _put(found, "contraintes", [f"ville : {label}" for c, label in CITIES.items() if re.search(rf"{_P}{c}{_E}", text)])
    _put(found, "formations_evoquees",
         [k for k, pats in FORMATIONS.items() if _any(text, [rf"{_P}{p}{_E}" for p in pats])])
    if "niveau" not in found and "moyenne" in found and re.search(_BAC, text):
        found["niveau"] = "bachelier"
    if m := _GOAL.search(unicodedata.normalize("NFKC", message)):
        found["objectif"] = m.group(1).strip()
    return {k: v for k, v in found.items() if v not in (None, "", [])}


def profile_from_llm(data: dict[str, Any] | None) -> dict[str, Any]:
    """Convertit la sortie JSON du prompt PROFILE_EXTRACT_SYSTEM vers le format de la mémoire."""
    found: dict[str, Any] = {}
    for key, value in (data or {}).items():
        if value in (None, "", [], {}):
            continue
        if key in ("formation", "institution"):
            key = "formations_evoquees"
        elif key == "lieu":
            key, value = "contraintes", f"ville : {value}"
        if key in LIST_FIELDS:
            values = value if isinstance(value, list) else [value]
            _put(found, key, [str(v)[:80] for v in values])
        elif key in SCALAR_FIELDS:
            found[key] = str(value)[:80]
    return found


# ======================================================================== état de la mémoire
@dataclass
class ConversationMemory:
    profile: dict[str, Any] = field(default_factory=dict)
    questions: list[str] = field(default_factory=list)  # dernières questions du candidat
    language: str | None = None                          # dernière langue détectée
    turns: int = 0

    @classmethod
    def from_json(cls, data: dict[str, Any] | None) -> "ConversationMemory":
        data = data or {}
        return cls(profile=dict(data.get("profil") or {}), questions=list(data.get("questions_posees") or []),
                   language=data.get("langue"), turns=int(data.get("tours") or 0))

    def to_json(self) -> dict[str, Any]:
        return {"profil": self.profile, "questions_posees": self.questions, "langue": self.language,
                "tours": self.turns}

    def merge(self, found: dict[str, Any]) -> None:
        for key, value in found.items():
            _put(self.profile, key, value)

    def observe_user_message(self, message: str, language: str, extracted: dict[str, Any] | None = None) -> None:
        """Met à jour la mémoire avec un nouveau message candidat (avant l'appel au LLM)."""
        self.merge(extract_profile(message))
        if extracted:
            self.merge(extracted)
        self.questions.append(message.strip()[:200])
        del self.questions[:-MAX_QUESTIONS]
        self.language = language
        self.turns += 1

    def to_prompt(self) -> str:
        if not self.profile and len(self.questions) <= 1:
            return "MÉMOIRE : premier échange, profil du candidat encore inconnu."
        lines = ["MÉMOIRE (ce que tu sais déjà du candidat) :"]
        for key, label in PROFILE_LABELS.items():
            if value := self.profile.get(key):
                lines.append(f"- {label} : {', '.join(value) if isinstance(value, list) else value}")
        missing = [PROFILE_LABELS[k] for k in ("niveau", "section_bac", "moyenne", "interets") if k not in self.profile]
        if missing:
            lines.append(f"- Encore inconnu : {', '.join(missing)}")
        previous = self.questions[:-1]
        if previous:
            lines.append("- Questions déjà posées : " + " | ".join(previous[-5:]))
        return "\n".join(lines)


# ======================================================================== fenêtre d'historique
@dataclass(frozen=True)
class HistoryItem:
    role: str  # "user" | "assistant"
    content: str


def build_history(items: Sequence[HistoryItem], *, max_messages: int, max_chars: int) -> list[ChatMessage]:
    """Derniers messages (ordre chronologique) tenant dans la fenêtre. Les plus anciens sortent en premier ;
    la fenêtre commence toujours par un message du candidat."""
    kept: list[HistoryItem] = []
    total = 0
    for item in reversed([i for i in items if i.role in ("user", "assistant")]):
        if len(kept) >= max_messages or total + len(item.content) > max_chars:
            break
        kept.append(item)
        total += len(item.content)
    kept.reverse()
    while kept and kept[0].role != "user":
        kept.pop(0)
    return [ChatMessage(i.role, i.content) for i in kept]  # type: ignore[arg-type]
