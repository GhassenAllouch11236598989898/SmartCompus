"""SA-38 — Dialogue interactif (ou scénario rejoué) avec le chatbot, via l'API.

    python -m scripts.chat_demo                         # mode interactif (quitter : /q)
    python -m scripts.chat_demo --scenario orientation  # rejoue le scénario du cahier des charges
    python -m scripts.chat_demo --url http://localhost:8000 --memoire

Prérequis : API lancée (docker compose up) et serveur LLM joignable (ollama serve).
"""

import argparse
import json
import sys
import time

import httpx

SCENARIOS = {
    "orientation": [
        "aslema, 9rit bac maths w jebt 15 de moyenne",
        "nheb el maths w l'informatique barcha ama mouch mitakked bin prepa w licence info",
        "nheb nwalli ingénieur logiciel, ama nheb 7aja pratique w progressive",
        "chnowa tnasa7ni ?",
        "w 9adech el flous mta3 el prepa ?",
    ],
    "tunisien": [
        "عسلامة، قريت باك سيانس وجبت 13",
        "نحب الإنفورماتيك والذكاء الاصطناعي، شنوة تنصحني ؟",
        "قداش الفلوس متاع الليسانس ؟",
        "ونجم نخلص على أقساط ؟",
    ],
    "francais": [
        "Bonjour, j'ai un bac technique avec 12 de moyenne.",
        "Est-ce que je peux faire la licence informatique ?",
        "Et après, je peux passer en cycle ingénieur ?",
        "Vous avez une formation en médecine ?",
    ],
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--scenario", choices=sorted(SCENARIOS))
    ap.add_argument("--memoire", action="store_true", help="afficher la mémoire après chaque tour")
    args = ap.parse_args(argv)

    with httpx.Client(base_url=f"{args.url.rstrip('/')}/api/v1", timeout=180) as http:
        token = http.post("/sessions").raise_for_status().json()["session_token"]  # session visiteur SA-25
        headers = {"X-Session-Token": token}
        messages = iter(SCENARIOS[args.scenario]) if args.scenario else None
        while True:
            if messages is not None:
                text = next(messages, None)
                if text is None:
                    break
                print(f"\nVous > {text}")
            else:
                try:
                    text = input("\nVous > ").strip()
                except EOFError:
                    break
                if text in ("/q", "/quit", "exit"):
                    break
                if not text:
                    continue
            start = time.perf_counter()
            r = http.post("/chat/messages", json={"content": text}, headers=headers)
            if r.status_code != 200:
                print(f"[{r.status_code}] {r.json()['error']['message']}", file=sys.stderr)
                continue
            body = r.json()
            lang = body["user_message"]["detected_language"]
            print(f"SmartCampus ({lang}, {time.perf_counter() - start:.1f} s) > {body['reply']['content']}")
            if args.memoire:
                print("  mémoire :", json.dumps(body["memory"]["profile"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
