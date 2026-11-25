"""Client LLM unique pour tout le backend (SA-33 évaluation, SA-36 dialogue).

Le backend parle à n'importe quel serveur exposant l'API « OpenAI-compatible »
``POST {base_url}/chat/completions`` : Ollama (``http://localhost:11434/v1``), vLLM, TGI,
LM Studio, llama.cpp server... Le modèle open-source (et plus tard son adaptateur LoRA/QLoRA)
est donc servi à part et se change par configuration, sans toucher au code.

``FakeLLMClient`` sert aux tests et au mode ``--dry-run`` de l'évaluation : aucun réseau.

Sécurité : le contenu des prompts et des réponses n'est jamais journalisé (données candidat).
"""

import logging
import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol

import httpx

logger = logging.getLogger("smartcampus.llm")

Role = Literal["system", "user", "assistant"]

# Modèles « raisonnants » (Qwen3, DeepSeek-R1...) : le raisonnement n'est jamais montré au candidat.
_THINK_BLOCK = re.compile(r"<think>.*?</think>\s*", re.DOTALL | re.IGNORECASE)


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str

    def as_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str
    latency_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    finish_reason: str | None = None


class LLMError(Exception):
    """Erreur d'appel au LLM (serveur injoignable, délai dépassé, réponse invalide)."""


class LLMClient(Protocol):
    model: str

    def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse: ...


def clean_completion(text: str) -> str:
    return _THINK_BLOCK.sub("", text or "").strip()


class OpenAICompatibleClient:
    """Client HTTP synchrone (les routes FastAPI du projet sont synchrones)."""

    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        api_key: str | None = None,
        timeout_s: float = 60.0,
        temperature: float = 0.3,
        max_tokens: int = 512,
        max_retries: int = 1,
        transport: httpx.BaseTransport | None = None,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"), headers=headers, timeout=timeout_s, transport=transport
        )

    def close(self) -> None:
        self._http.close()

    def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        payload: dict = {
            "model": self.model,
            "messages": [m.as_dict() for m in messages],
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            start = time.perf_counter()
            try:
                resp = self._http.post("/chat/completions", json=payload)
            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning("LLM %s : délai dépassé (tentative %d)", self.model, attempt + 1)
                continue
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning("LLM %s : serveur injoignable (%s)", self.model, type(exc).__name__)
                continue
            latency_ms = (time.perf_counter() - start) * 1000
            if resp.status_code >= 500:
                last_error = LLMError(f"HTTP {resp.status_code}")
                logger.warning("LLM %s : HTTP %d (tentative %d)", self.model, resp.status_code, attempt + 1)
                continue
            if resp.status_code >= 400:
                raise LLMError(f"Requête LLM refusée (HTTP {resp.status_code}).")
            return self._parse(resp, latency_ms)
        raise LLMError("Le service LLM est indisponible.") from last_error

    def _parse(self, resp: httpx.Response, latency_ms: float) -> LLMResponse:
        try:
            data = resp.json()
            choice = data["choices"][0]
            content = choice["message"]["content"] or ""
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError("Réponse LLM illisible.") from exc
        usage = data.get("usage") or {}
        return LLMResponse(
            content=clean_completion(content),
            model=data.get("model") or self.model,
            latency_ms=round(latency_ms, 1),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            finish_reason=choice.get("finish_reason"),
        )


@dataclass
class FakeLLMClient:
    """LLM factice et déterministe : renvoie ``responder(messages)`` ou des réponses scriptées."""

    responses: list[str] = field(default_factory=list)
    responder: Callable[[Sequence[ChatMessage]], str] | None = None
    model: str = "fake-llm"
    fail: bool = False
    calls: list[list[ChatMessage]] = field(default_factory=list)

    def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        self.calls.append(list(messages))
        if self.fail:
            raise LLMError("Le service LLM est indisponible.")
        if self.responses:
            content = self.responses.pop(0)
        elif self.responder is not None:
            content = self.responder(messages)
        else:
            content = "Réponse de test."
        return LLMResponse(content=clean_completion(content), model=self.model, latency_ms=1.0,
                           prompt_tokens=sum(len(m.content) // 4 for m in messages),
                           completion_tokens=len(content) // 4, finish_reason="stop")
