"""Клиент модели против локального HTTP-сервера: ошибки, повторы, понижение режима, обрезка."""

import json

import pytest

from reqask.llm import LLMError, LLMFatal, LLMTruncated

from helpers import ONE, OneOut, TWO, TwoOut, ask, completion, error


def test_temperature_goes_only_to_non_gemini(client_with):
    client, sent, _ = client_with(lambda b, n: (200, completion(ONE)), temperature=0.2)
    ask(client)
    assert "temperature" not in sent[0]
    client, sent, _ = client_with(lambda b, n: (200, completion(ONE)), provider="custom", temperature=0.2)
    ask(client)
    assert sent[0]["temperature"] == 0.2


def test_json_downgrade_is_per_schema(client_with):
    """400 про формат понижает режим только у этой схемы, остальные остаются на parse."""
    def handler(body, n):
        fmt = body.get("response_format") or {}
        if fmt.get("json_schema", {}).get("name") == "OneOut":
            return 400, error(400, "response_format.json_schema: For 'integer' type, property 'minimum' is not supported")
        return 200, completion(ONE if "answer" in json.dumps(body, ensure_ascii=False) else TWO)

    client, sent, _ = client_with(handler)
    ask(client, OneOut)
    ask(client, TwoOut)
    formats = [(b.get("response_format") or {}).get("type") for b in sent]
    assert formats == ["json_schema", "json_schema", "json_object", "json_schema"]
    assert client._modes == {"OneOut": ["object", "none"], "TwoOut": ["parse", "schema", "object", "none"]}
    assert client.json_mode == "OneOut: object, TwoOut: parse"
    assert any("OneOut" in note for note in client.stats.notes)


def test_other_400_keeps_mode_and_fails_step(client_with):
    client, sent, _ = client_with(lambda b, n: (400, error(400, "messages: too many images")))
    with pytest.raises(LLMError) as info:
        ask(client)
    assert not isinstance(info.value, LLMFatal) and "too many images" in str(info.value)
    assert len(sent) == 1 and client.json_mode == "parse"


def test_rate_limit_waits_from_body_then_default_schedule(client_with):
    def handler(body, n):
        if n == 1:
            return 429, [error(429, "Quota exceeded for metric per minute", status="RESOURCE_EXHAUSTED",
                               details=[{"retryDelay": "7s"}])]
        if n == 2:
            return 429, error(429, "rate limited")
        return 200, completion(ONE)

    client, sent, waits = client_with(handler)
    assert ask(client).answer == "ок"
    assert waits == [7.0, 30.0] and client.stats.retries == 2  # 7 из тела, затем вторая пауза по расписанию


def test_rate_limit_header_retry_after(client_with):
    answers = iter([(429, error(429, "slow down"), {"retry-after": "3"}), (200, completion(ONE))])
    client, _, waits = client_with(lambda b, n: next(answers))
    ask(client)
    assert waits == [3.0]


def test_rate_limit_that_never_ends_is_fatal(client_with):
    client, sent, waits = client_with(lambda b, n: (429, error(429, "rate limited")), max_retries=2)
    with pytest.raises(LLMFatal) as info:
        ask(client)
    assert info.value.kind == "rate" and len(sent) == 3 and waits == [15.0, 30.0]


def test_daily_quota_is_fatal_without_waiting(client_with):
    body = [error(429, "Generate content requests per day limit exceeded on Free Tier", status="RESOURCE_EXHAUSTED")]
    client, sent, waits = client_with(lambda b, n: (429, body))
    with pytest.raises(LLMFatal) as info:
        ask(client)
    assert info.value.kind == "quota" and len(sent) == 1 and waits == []


def test_daily_quota_switches_to_fallback_model(client_with):
    """Квота считается по моделям, поэтому при суточной квоте клиент идёт на запасную без ожидания."""
    body = [error(429, "Generate content requests per day limit exceeded on Free Tier", status="RESOURCE_EXHAUSTED")]
    client, sent, waits = client_with(
        lambda b, n: (429, body) if b["model"] == "m" else (200, completion(ONE)), fallback_models=("m", "b"))
    assert ask(client).answer == "ок" and ask(client).answer == "ок"
    # Переход один на весь клиент: второй вызов к исчерпанной модели уже не идёт.
    assert [b["model"] for b in sent] == ["m", "b", "b"] and waits == []
    assert client.model == "b" and any("перехожу на запасную b" in note for note in client.stats.notes)


def test_overloaded_model_switches_after_two_retries(client_with):
    """При запасной модели на 503 тратится два повтора, а не все пять."""
    client, sent, waits = client_with(
        lambda b, n: (503, error(503, "high demand")) if b["model"] == "m" else (200, completion(ONE)),
        fallback_models=("b",))
    assert ask(client).answer == "ок"
    assert [b["model"] for b in sent] == ["m", "m", "m", "b"] and len(waits) == 2


def test_missing_fallback_is_skipped_and_last_model_gets_all_retries(client_with):
    def handler(b, n):
        if b["model"] == "m":
            return 429, [error(429, "requests per day limit exceeded")]
        if b["model"] == "gone":
            return 404, error(404, "model not found")
        return 503, error(503, "high demand")

    client, sent, waits = client_with(handler, fallback_models=("gone", "last"), max_retries=3)
    with pytest.raises(LLMError):
        ask(client)
    # У последней модели запасных нет: она получает все повторы, как клиент без цепочки.
    assert [b["model"] for b in sent] == ["m", "gone", "last", "last", "last", "last"] and len(waits) == 3


@pytest.mark.parametrize("status,message,kind", [
    (401, "invalid x-api-key", "auth"),
    (403, "FREE_TIER_VERIFICATION_REQUIRED", "auth"),
    (400, "API key not valid. Please pass a valid API key.", "auth"),
    (404, "model not found", "model"),
])
def test_auth_and_missing_model_are_fatal_at_once(client_with, status, message, kind):
    client, sent, waits = client_with(lambda b, n: (status, error(status, message)))
    with pytest.raises(LLMFatal) as info:
        ask(client)
    assert info.value.kind == kind and len(sent) == 1 and waits == []
    if "VERIFICATION" in message:
        assert "AI Studio" in str(info.value)


def test_server_errors_retry_with_doubling(client_with):
    answers = iter([(503, error(503, "overloaded")), (500, error(500, "boom")), (200, completion(ONE))])
    client, sent, waits = client_with(lambda b, n: next(answers))
    ask(client)
    assert len(sent) == 3 and 2 <= waits[0] < 3 and 4 <= waits[1] < 5


def test_truncated_answer(client_with):
    client, _, _ = client_with(lambda b, n: (200, completion('{"answer": "о', finish="length")))
    with pytest.raises(LLMTruncated):
        ask(client)


def test_empty_answer_is_repeated_once(client_with):
    answers = iter([(200, completion("")), (200, completion(ONE))])
    client, sent, _ = client_with(lambda b, n: next(answers))
    assert ask(client).answer == "ок" and len(sent) == 2

    client, sent, _ = client_with(lambda b, n: (200, completion("  ")))
    with pytest.raises(LLMError):
        ask(client)
    assert len(sent) == 2


def test_content_filter_is_not_repeated(client_with):
    client, sent, _ = client_with(lambda b, n: (200, completion("", finish="content_filter")))
    with pytest.raises(LLMError, match="фильтром"):
        ask(client)
    assert len(sent) == 1


def test_reasoning_refusal_gemini_tries_thinking_level_then_drops(client_with):
    def handler(body, n):
        if "reasoning_effort" in body or "extra_body" in body:
            return 400, [error(400, "Thinking level is not supported for this model")]
        return 200, completion(ONE)

    client, sent, _ = client_with(handler)
    ask(client)
    assert "reasoning_effort" in sent[0]
    # Gemini ждёт ключ extra_body прямо в теле запроса (страница совместимости OpenAI).
    assert sent[1]["extra_body"]["google"]["thinking_config"]["thinking_level"] == "medium"
    assert "reasoning_effort" not in sent[1]
    assert "extra_body" not in sent[2] and "reasoning_effort" not in sent[2]
    assert len(client.stats.notes) == 2 and client.json_mode == "parse"  # режим JSON не тронут


def test_reasoning_refusal_other_provider_drops_at_once(client_with):
    def handler(body, n):
        if "reasoning_effort" in body:
            return 400, error(400, "Unrecognized request argument: reasoning_effort")
        return 200, completion(ONE)

    client, sent, _ = client_with(handler, provider="custom")
    ask(client)
    assert len(sent) == 2 and "extra_body" not in sent[1]


def test_effort_override_and_check(client_with):
    client, sent, _ = client_with(lambda b, n: (200, completion('{"ok": true, "reply": "готово"}')))
    info = client.check()
    assert info["ok"] and info["json_mode"] == "parse" and info["reasoning"] == "reasoning_effort"
    assert sent[0]["reasoning_effort"] == "low" and sent[0]["max_tokens"] == 4_000

    client, sent, _ = client_with(lambda b, n: (200, completion(ONE)))
    ask(client, effort="low")
    assert sent[0]["reasoning_effort"] == "low"  # повтор прохода по набору после обрезки
