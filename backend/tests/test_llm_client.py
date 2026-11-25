"""SA-36 — Client LLM OpenAI-compatible (transport HTTP simulé, aucun réseau)."""

import json

import httpx
import pytest

from app.llm.client import ChatMessage, FakeLLMClient, LLMError, OpenAICompatibleClient, clean_completion

MSGS = [ChatMessage("system", "Tu es SmartCampus AI."), ChatMessage("user", "9adech el licence ?")]


def _client(handler, **kw) -> OpenAICompatibleClient:
    return OpenAICompatibleClient("http://llm.test/v1/", "qwen2.5:7b-instruct", transport=httpx.MockTransport(handler), **kw)


def _ok(content: str, **extra):
    return httpx.Response(200, json={"model": "qwen2.5:7b-instruct", "choices": [
        {"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 20, "completion_tokens": 8}, **extra})


def test_chat_sends_openai_payload_and_parses_response():
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        seen["body"] = json.loads(request.content)
        return _ok("El licence: 5 900 TND scolarité.")

    r = _client(handler, api_key="secret").chat(MSGS, temperature=0.1, max_tokens=64, json_mode=True)
    assert seen["url"] == "http://llm.test/v1/chat/completions"
    assert seen["auth"] == "Bearer secret"
    assert seen["body"]["model"] == "qwen2.5:7b-instruct"
    assert seen["body"]["messages"][1] == {"role": "user", "content": "9adech el licence ?"}
    assert seen["body"]["temperature"] == 0.1 and seen["body"]["max_tokens"] == 64
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert r.content == "El licence: 5 900 TND scolarité."
    assert (r.prompt_tokens, r.completion_tokens, r.finish_reason) == (20, 8, "stop")


def test_no_auth_header_without_key():
    def handler(request):
        assert "Authorization" not in request.headers
        return _ok("ok")

    _client(handler).chat(MSGS)


def test_think_blocks_are_removed():
    assert clean_completion("<think>raisonnement</think>\nAhla !") == "Ahla !"
    assert _client(lambda r: _ok("<think>x</think>Réponse")).chat(MSGS).content == "Réponse"


def test_retries_once_on_server_error_then_succeeds():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503) if len(calls) == 1 else _ok("ok")

    assert _client(handler).chat(MSGS).content == "ok"
    assert len(calls) == 2


def test_raises_llm_error_when_unavailable():
    def handler(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(LLMError, match="indisponible"):
        _client(handler).chat(MSGS)


def test_client_error_is_not_retried():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(404, json={"error": "model not found"})

    with pytest.raises(LLMError, match="404"):
        _client(handler).chat(MSGS)
    assert len(calls) == 1


def test_invalid_payload_raises():
    with pytest.raises(LLMError, match="illisible"):
        _client(lambda r: httpx.Response(200, json={"foo": 1})).chat(MSGS)


def test_fake_client():
    fake = FakeLLMClient(responses=["un", "deux"])
    assert fake.chat(MSGS).content == "un"
    assert fake.chat(MSGS).content == "deux"
    assert fake.chat(MSGS).content == "Réponse de test."
    assert len(fake.calls) == 3
    with pytest.raises(LLMError):
        FakeLLMClient(fail=True).chat(MSGS)
