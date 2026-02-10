"""Tests for OpenAI client with smart fallback."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.openai_client.client import OpenAIClient
from src.services.openai_client.models import AIResponse


def _make_completion(content: str) -> MagicMock:
    """Create a mock ChatCompletion response."""
    choice = MagicMock()
    choice.message.content = content
    completion = MagicMock()
    completion.choices = [choice]
    return completion


def _good_response(intent="sell", confidence=0.9) -> str:
    return json.dumps({
        "intent": intent,
        "confidence": confidence,
        "entities": {"brand": "Toyota", "model": "Camry", "year": "2022", "budget": None, "mileage": None},
        "reply": "Понял, вы хотите продать Toyota Camry 2022 года.",
    })


def _low_confidence_response() -> str:
    return json.dumps({
        "intent": "buy",
        "confidence": 0.4,
        "entities": {},
        "reply": "Не совсем уверен.",
    })


def _invalid_json_response() -> str:
    return "This is not valid JSON at all"


def _empty_intent_response() -> str:
    return json.dumps({
        "intent": "",
        "confidence": 0.8,
        "entities": {},
        "reply": "Hmm",
    })


# ---------------------------------------------------------------
# Parsing tests
# ---------------------------------------------------------------

class TestParseResponse:
    def test_valid_json(self):
        client = OpenAIClient(client=MagicMock())
        result = client._parse_response(_good_response(), "gpt-4o-mini")
        assert result.intent == "sell"
        assert result.confidence == 0.9
        assert result.entities["brand"] == "Toyota"
        assert result.model_used == "gpt-4o-mini"

    def test_invalid_json(self):
        client = OpenAIClient(client=MagicMock())
        result = client._parse_response("not json", "gpt-4o-mini")
        assert result.intent == ""
        assert result.confidence == 0.0

    def test_json_with_markdown_fences(self):
        client = OpenAIClient(client=MagicMock())
        content = "```json\n" + _good_response() + "\n```"
        result = client._parse_response(content, "gpt-4o-mini")
        assert result.intent == "sell"
        assert result.confidence == 0.9

    def test_empty_content(self):
        client = OpenAIClient(client=MagicMock())
        result = client._parse_response("", "gpt-4o-mini")
        assert result.intent == ""


# ---------------------------------------------------------------
# Smart fallback logic
# ---------------------------------------------------------------

class TestNeedsFallback:
    def test_good_response_no_fallback(self):
        client = OpenAIClient(client=MagicMock())
        resp = AIResponse(intent="sell", confidence=0.9)
        assert client._needs_fallback(resp) is False

    def test_low_confidence_needs_fallback(self):
        client = OpenAIClient(client=MagicMock())
        resp = AIResponse(intent="buy", confidence=0.4)
        assert client._needs_fallback(resp) is True

    def test_empty_intent_needs_fallback(self):
        client = OpenAIClient(client=MagicMock())
        resp = AIResponse(intent="", confidence=0.9)
        assert client._needs_fallback(resp) is True

    def test_threshold_boundary(self):
        client = OpenAIClient(client=MagicMock())
        # Exactly at threshold = no fallback
        resp = AIResponse(intent="sell", confidence=0.65)
        assert client._needs_fallback(resp) is False

        # Below threshold = fallback
        resp = AIResponse(intent="sell", confidence=0.64)
        assert client._needs_fallback(resp) is True


# ---------------------------------------------------------------
# classify() integration
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_classify_high_confidence_no_fallback():
    """High confidence response -> no fallback triggered."""
    mock_openai = AsyncMock()
    mock_openai.chat.completions.create = AsyncMock(
        return_value=_make_completion(_good_response())
    )

    client = OpenAIClient(client=mock_openai)
    result = await client.classify("Хочу продать Toyota Camry 2022")

    assert result.intent == "sell"
    assert result.confidence == 0.9
    assert result.entities["brand"] == "Toyota"
    assert result.used_fallback is False
    # Should only call the API once
    mock_openai.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_classify_low_confidence_triggers_fallback():
    """Low confidence from mini -> fallback to full model."""
    mock_openai = AsyncMock()

    call_count = 0

    async def fake_create(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call (mini) - low confidence
            return _make_completion(_low_confidence_response())
        else:
            # Second call (fallback) - good response
            return _make_completion(_good_response("buy", 0.85))

    mock_openai.chat.completions.create = AsyncMock(side_effect=fake_create)

    client = OpenAIClient(client=mock_openai)
    result = await client.classify("Хочу купить машину")

    assert result.intent == "buy"
    assert result.confidence == 0.85
    assert result.used_fallback is True
    assert call_count == 2


@pytest.mark.asyncio
async def test_classify_invalid_json_triggers_fallback():
    """Invalid JSON from mini -> fallback."""
    mock_openai = AsyncMock()

    call_count = 0

    async def fake_create(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _make_completion(_invalid_json_response())
        else:
            return _make_completion(_good_response("check", 0.8))

    mock_openai.chat.completions.create = AsyncMock(side_effect=fake_create)

    client = OpenAIClient(client=mock_openai)
    result = await client.classify("Проверить авто по VIN")

    assert result.intent == "check"
    assert result.used_fallback is True
    assert call_count == 2


@pytest.mark.asyncio
async def test_classify_empty_intent_triggers_fallback():
    """Empty intent from mini -> fallback."""
    mock_openai = AsyncMock()

    call_count = 0

    async def fake_create(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _make_completion(_empty_intent_response())
        else:
            return _make_completion(_good_response("legal", 0.75))

    mock_openai.chat.completions.create = AsyncMock(side_effect=fake_create)

    client = OpenAIClient(client=mock_openai)
    result = await client.classify("Юридический вопрос по авто")

    assert result.intent == "legal"
    assert result.used_fallback is True


@pytest.mark.asyncio
async def test_classify_api_error_returns_unknown():
    """API exception -> returns unknown intent, no crash."""
    mock_openai = AsyncMock()
    mock_openai.chat.completions.create = AsyncMock(
        side_effect=Exception("API timeout")
    )

    client = OpenAIClient(client=mock_openai)
    result = await client.classify("Тест")

    assert result.intent == "unknown"
    assert result.confidence == 0.0
    # API error on primary -> fallback is triggered (empty intent)
    # fallback also fails -> returns unknown
    assert mock_openai.chat.completions.create.call_count == 2


@pytest.mark.asyncio
async def test_classify_truncates_long_message():
    """Messages longer than 500 chars are truncated."""
    mock_openai = AsyncMock()
    mock_openai.chat.completions.create = AsyncMock(
        return_value=_make_completion(_good_response())
    )

    client = OpenAIClient(client=mock_openai)
    long_message = "A" * 1000
    await client.classify(long_message)

    call_args = mock_openai.chat.completions.create.call_args
    user_msg = call_args.kwargs["messages"][1]["content"]
    assert len(user_msg) == 500


# ---------------------------------------------------------------
# AIResponse model
# ---------------------------------------------------------------

class TestAIResponse:
    def test_has_intent(self):
        assert AIResponse(intent="sell").has_intent is True
        assert AIResponse(intent="unknown").has_intent is False
        assert AIResponse(intent="faq").has_intent is False
        assert AIResponse(intent="").has_intent is False

    def test_is_high_confidence(self):
        assert AIResponse(confidence=0.7).is_high_confidence is True
        assert AIResponse(confidence=0.8).is_high_confidence is True
        assert AIResponse(confidence=0.69).is_high_confidence is False
