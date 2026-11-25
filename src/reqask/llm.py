"""Клиент модели: один OpenAI-совместимый интерфейс для Gemini, OpenAI, Ollama и других.

Что делает сверх простого вызова:
- требует ответ в JSON и проверяет его по схеме pydantic;
- при невалидном JSON возвращает модели текст ошибки и просит исправить ответ;
- повторяет запрос при лимитах (429), ошибках сервера и обрывах связи с растущей паузой;
- сам понижает режим JSON и убирает параметры, которые провайдер не поддерживает;
- кэширует проверенные ответы на диске, чтобы повторный прогон не тратил квоту.
"""

from __future__ import annotations

import hashlib
import json
import random
import threading
import time
from pathlib import Path
from typing import Callable, TypeVar

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ContentFilterFinishReasonError,
    LengthFinishReasonError,
    NotFoundError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)
from openai.types.chat import ChatCompletion
from pydantic import BaseModel, ValidationError

from .config import Settings
from .schemas import LLMStats

T = TypeVar("T", bound=BaseModel)

MAX_BACKOFF_SEC = 60.0


class LLMError(Exception):
    """Модель не дала пригодный ответ после всех попыток."""


class LLMTruncated(LLMError):
    """Ответ обрезан по лимиту длины. Вызывающий код может уменьшить порцию."""


class LLMFatal(LLMError):
    """Ошибка, которую повтор не исправит: неверный ключ, нет доступа, нет такой модели."""


def extract_json(raw: str) -> str:
    """Достаёт JSON-объект из ответа: снимает ограждение ``` и текст вокруг."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("в ответе нет JSON-объекта")
    return text[start : end + 1]


def error_text(error: APIStatusError) -> str:
    """Текст ошибки вместе с телом ответа.

    Gemini отдаёт тело списком `[{"error": {...}}]`, SDK такое не разворачивает,
    и в str(error) остаётся только «Error code: 400». Причину берём из тела.
    """
    try:
        body = error.response.text
    except Exception:  # noqa: BLE001  тело могло быть уже закрыто или не прочитано
        body = ""
    return f"{error} {body[:2000]}".strip()


def schema_instruction(schema: type[BaseModel]) -> str:
    return (
        "Формат ответа: один JSON-объект по этой JSON Schema. "
        "Без пояснений, без markdown, без текста до и после.\n"
        + json.dumps(schema.model_json_schema(), ensure_ascii=False)
    )


class LLMClient:
    def __init__(self, settings: Settings, log: Callable[[str], None] | None = None):
        self.s = settings
        self.log = log or (lambda _msg: None)
        self.stats = LLMStats()
        self._client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.timeout_sec,
            max_retries=0,
        )
        self._lock = threading.Lock()
        self._last_call = 0.0
        # Порядок понижения режима JSON, если провайдер отклоняет запрос.
        # parse: схема pydantic через помощник SDK; schema: ручной json_schema;
        # object: просто JSON, схема только в тексте промпта; none: без формата.
        ladder = {"auto": ["parse", "schema", "object", "none"]}
        self._json_modes = list(ladder.get(settings.json_mode, [settings.json_mode]))
        # Gemini 3.6+ игнорирует temperature и обещает ошибку 400, поэтому ему параметр не шлём.
        self._send_temperature = settings.temperature is not None and settings.provider != "gemini"
        if settings.temperature is not None and settings.provider == "gemini":
            self.log("  LLM_TEMPERATURE задан, но для Gemini не отправляется")
        self._send_reasoning = True
        self._send_max_tokens = True
        self._cache_dir = Path(settings.cache_dir) if settings.cache_dir else None

    @property
    def json_mode(self) -> str:
        """Текущий режим ответа JSON после возможных понижений."""
        return self._json_modes[0] if self._json_modes else ""

    # ---------- кэш ----------

    def _cache_key(self, system: str, user: str, schema: type[BaseModel], kind: str) -> str:
        payload = json.dumps(
            [self.s.base_url, self.s.model, self.s.temperature, self.s.step_params(kind)[0],
             system, user, schema.model_json_schema()],
            ensure_ascii=False, sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _cache_get(self, key: str, schema: type[T]) -> T | None:
        if not self._cache_dir:
            return None
        path = self._cache_dir / f"{key}.json"
        if not path.is_file():
            return None
        try:
            return schema.model_validate_json(path.read_text(encoding="utf-8"))
        except (ValidationError, OSError, ValueError):
            return None

    def _cache_put(self, key: str, obj: BaseModel) -> None:
        if not self._cache_dir:
            return
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            (self._cache_dir / f"{key}.json").write_text(obj.model_dump_json(), encoding="utf-8")
        except OSError:
            pass

    # ---------- вызов ----------

    def complete_json(self, step: str, system: str, user: str, schema: type[T], kind: str = "") -> T:
        """Возвращает ответ модели, проверенный по схеме. Бросает LLMError, если не вышло.

        step: подпись для лога. kind: вид шага, по нему берутся уровень рассуждения и лимит вывода.
        """
        key = self._cache_key(system, user, schema, kind)
        cached = self._cache_get(key, schema)
        if cached is not None:
            with self._lock:
                self.stats.cache_hits += 1
            return cached

        # Схема текстом добавляется в _kwargs и только в режимах object и none (П-04).
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        last_error = ""
        for attempt in range(self.s.max_repairs + 1):
            raw = self._chat(step, messages, schema, kind)
            try:
                obj = schema.model_validate_json(extract_json(raw))
            except (ValidationError, ValueError) as exc:
                last_error = str(exc)[:1500]
                if attempt == self.s.max_repairs:
                    break
                with self._lock:
                    self.stats.repairs += 1
                self.log(f"  [{step}] ответ не прошёл проверку схемы, прошу исправить")
                messages = messages[:2] + [
                    {"role": "assistant", "content": raw[:8000]},
                    {
                        "role": "user",
                        "content": "Ответ не прошёл проверку. Ошибка:\n" + last_error
                        + "\nВерни исправленный JSON-объект целиком, строго по схеме, без текста вокруг.",
                    },
                ]
                continue
            self._cache_put(key, obj)
            return obj
        raise LLMError(f"[{step}] модель не вернула валидный JSON: {last_error}")

    def _throttle(self) -> None:
        if self.s.min_interval_sec <= 0:
            return
        with self._lock:
            wait = self._last_call + self.s.min_interval_sec - time.monotonic()
            self._last_call = max(time.monotonic(), self._last_call + self.s.min_interval_sec)
        if wait > 0:
            time.sleep(wait)

    def _kwargs(self, messages: list[dict], schema: type[BaseModel], kind: str) -> dict:
        effort, max_tokens = self.s.step_params(kind)
        mode = self._json_modes[0]
        if mode in ("object", "none"):
            # Провайдер не держит схему сам: отдаём её текстом в системном сообщении.
            messages = [
                {**messages[0], "content": messages[0]["content"] + "\n\n" + schema_instruction(schema)},
                *messages[1:],
            ]
        kwargs: dict = {"model": self.s.model, "messages": messages}
        if mode == "parse":
            kwargs["response_format"] = schema
        elif mode == "schema":
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
            }
        elif mode == "object":
            kwargs["response_format"] = {"type": "json_object"}
        if self._send_temperature:
            kwargs["temperature"] = self.s.temperature
        if self._send_reasoning:
            kwargs["reasoning_effort"] = effort
        if self._send_max_tokens:
            kwargs["max_tokens"] = max_tokens
        return kwargs

    def _request(self, kwargs: dict) -> ChatCompletion:
        if not isinstance(kwargs.get("response_format"), type):
            return self._client.chat.completions.create(**kwargs)
        raw = self._client.beta.chat.completions.with_raw_response.parse(**kwargs)
        try:
            return raw.parse()
        except ValidationError:
            # SDK не разобрал ответ по схеме. Отдаём сырой текст дальше: там модель попросят исправить JSON.
            return ChatCompletion.model_validate_json(raw.text)

    def _downgrade(self, error: BadRequestError) -> bool:
        """Убирает одну неподдерживаемую возможность. False, если убирать больше нечего."""
        text = error_text(error).lower()
        with self._lock:
            if self._send_temperature and "temperature" in text:
                self._send_temperature = False
                self.log("  провайдер не принимает temperature, отправляю без него")
                return True
            # Gemini на неподдерживаемый уровень отвечает 400 «Thinking level ... is not supported for this model».
            if self._send_reasoning and ("reasoning" in text or "thinking" in text):
                self._send_reasoning = False
                self.log("  провайдер не принимает reasoning_effort, отправляю без него")
                return True
            if self._send_max_tokens and "max_tokens" in text:
                self._send_max_tokens = False
                self.log("  провайдер не принимает max_tokens, отправляю без лимита вывода")
                return True
            if len(self._json_modes) > 1:
                dropped = self._json_modes.pop(0)
                self.log(f"  режим JSON «{dropped}» отклонён, перехожу на «{self._json_modes[0]}»")
                return True
            if self._send_temperature:
                self._send_temperature = False
                return True
            if self._send_reasoning:
                self._send_reasoning = False
                return True
        return False

    def _count(self, response: ChatCompletion) -> None:
        """Учёт вызова и токенов.

        Gemini не отдаёт completion_tokens_details: токены рассуждения видны только как разница
        total - prompt - completion (проверено живым вызовом 25.11.2026: 17 + 16 при total 331).
        """
        usage = getattr(response, "usage", None)
        details = getattr(usage, "completion_tokens_details", None)
        prompt = getattr(usage, "prompt_tokens", 0) or 0
        completion = getattr(usage, "completion_tokens", 0) or 0
        total = getattr(usage, "total_tokens", 0) or 0
        reasoning = getattr(details, "reasoning_tokens", None)
        if reasoning is None:
            reasoning = max(0, total - prompt - completion)
        with self._lock:
            self.stats.calls += 1
            self.stats.prompt_tokens += prompt
            self.stats.completion_tokens += completion
            self.stats.total_tokens += total
            self.stats.reasoning_tokens += reasoning

    def _chat(self, step: str, messages: list[dict], schema: type[BaseModel], kind: str = "") -> str:
        delay = 2.0
        transient = 0
        while True:
            self._throttle()
            try:
                response = self._request(self._kwargs(messages, schema, kind))
            except LengthFinishReasonError as exc:
                self._count(exc.completion)
                raise LLMTruncated(f"[{step}] ответ обрезан по лимиту длины") from exc
            except ContentFilterFinishReasonError as exc:
                raise LLMError(f"[{step}] ответ закрыт фильтром содержания провайдера") from exc
            except BadRequestError as exc:
                # Gemini на неверный ключ отвечает 400 INVALID_ARGUMENT «Please pass a valid API key»
                # (проверено живым вызовом 25.11.2026), а не 401.
                if "api key" in error_text(exc).lower():
                    raise LLMFatal(
                        f"Ключ модели не принят провайдером ({self.s.provider}), проверьте .env: {error_text(exc)}"
                    ) from exc
                if self._downgrade(exc):
                    continue
                raise LLMError(f"[{step}] провайдер отклонил запрос: {error_text(exc)}") from exc
            except (AuthenticationError, PermissionDeniedError) as exc:
                raise LLMFatal(f"Ключ модели не принят провайдером ({self.s.provider}): {error_text(exc)}") from exc
            except NotFoundError as exc:
                raise LLMFatal(f"Модель «{self.s.model}» не найдена у провайдера: {error_text(exc)}") from exc
            except RateLimitError as exc:
                # Суточная квота Gemini (проверено 26.11.2026): 429 RESOURCE_EXHAUSTED, в тексте
                # «Generate content requests per day limit exceeded on Free Tier» и quotaId
                # «GenerateRequestsPerDayPerProjectPerModel-FreeTier». Ждать бесполезно, а каждый повтор тратит запрос.
                text = error_text(exc)
                if "per day" in text.lower() or "perday" in text.lower():
                    raise LLMFatal(
                        f"Суточная квота модели «{self.s.model}» исчерпана. Смените модель (--model), ключ или уровень "
                        f"оплаты и запустите снова: готовые шаги возьмутся из кэша. Ответ провайдера: {text[:600]}"
                    ) from exc
                error: Exception = exc
            except (APITimeoutError, APIConnectionError) as exc:
                error = exc
            except APIStatusError as exc:
                if exc.status_code < 500:
                    raise LLMError(f"[{step}] ошибка провайдера {exc.status_code}: {error_text(exc)}") from exc
                error = exc
            else:
                self._count(response)
                choice = response.choices[0] if response.choices else None
                content = (choice.message.content or "") if choice else ""
                if choice is not None and choice.finish_reason == "length":
                    raise LLMTruncated(f"[{step}] ответ обрезан по лимиту длины")
                if content.strip():
                    return content
                error = LLMError("пустой ответ модели")

            transient += 1
            if transient > self.s.max_retries:
                if isinstance(error, RateLimitError):
                    # Лимит не отпустил за все паузы: похоже на исчерпанную дневную квоту.
                    # Готовые ответы лежат в кэше, повторный запуск продолжит с этого места.
                    raise LLMFatal(
                        f"Провайдер держит лимит запросов (429) после {self.s.max_retries} повторов. "
                        "Подождите или смените модель/ключ и запустите снова: готовые шаги возьмутся из кэша."
                    )
                raise LLMError(f"[{step}] не удалось получить ответ за {self.s.max_retries} повторов: {error}")
            wait = delay + random.uniform(0, 1)
            retry_after = getattr(getattr(error, "response", None), "headers", {}).get("retry-after")
            if retry_after:
                try:
                    wait = max(wait, float(retry_after))
                except ValueError:
                    pass
            wait = min(wait, MAX_BACKOFF_SEC)
            with self._lock:
                self.stats.retries += 1
            self.log(f"  [{step}] {type(error).__name__}, повтор {transient}/{self.s.max_retries} через {wait:.0f} с")
            time.sleep(wait)
            delay = min(delay * 2, MAX_BACKOFF_SEC)
