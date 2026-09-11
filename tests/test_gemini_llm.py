import httpx
import pytest

from app.providers.llm.gemini_llm import GEMINI_API_BASE, GeminiLLM

_OriginalAsyncClient = httpx.AsyncClient


class _Recorder:
    request = None


def _make_handler(recorder):
    def handler(request: httpx.Request) -> httpx.Response:
        recorder.request = request
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "  Recursion"},
                                {"text": " + Memoization \n"},
                            ]
                        }
                    }
                ]
            },
        )

    return handler


def _patch_client(monkeypatch, recorder):
    def fake_factory(**kwargs):
        return _OriginalAsyncClient(
            transport=httpx.MockTransport(_make_handler(recorder)), **kwargs
        )

    monkeypatch.setattr("httpx.AsyncClient", fake_factory)


@pytest.mark.asyncio
async def test_gemini_generate_summary_parses_response(monkeypatch):
    recorder = _Recorder()
    _patch_client(monkeypatch, recorder)

    llm = GeminiLLM(api_key="test-key", model="gemini-2.5-flash")
    result = await llm.generate_summary("Some problem", "N <= 100")

    assert result == "Recursion + Memoization"


@pytest.mark.asyncio
async def test_gemini_generate_summary_request_shape(monkeypatch):
    recorder = _Recorder()
    _patch_client(monkeypatch, recorder)

    llm = GeminiLLM(api_key="test-key", model="gemini-2.5-flash")
    await llm.generate_summary("Some problem", "N <= 100")

    req = recorder.request
    assert req.url == (
        f"{GEMINI_API_BASE}/v1beta/models/gemini-2.5-flash:generateContent"
    )
    assert req.headers["x-goog-api-key"] == "test-key"

    body = req.read()
    import json

    payload = json.loads(body)
    assert payload["contents"][0]["role"] == "user"
    assert "[PROBLEM STATEMENT]\nSome problem" in payload["contents"][0]["parts"][0]["text"]
    assert "[CONSTRAINTS]\nN <= 100" in payload["contents"][0]["parts"][0]["text"]
    assert "system_instruction" in payload
    assert payload["generationConfig"]["temperature"] == 0.1