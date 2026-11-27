"""Клиент модели: один OpenAI-совместимый интерфейс для Anthropic (Claude), Gemini, OpenAI, Ollama и других.

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
import os
import random
import re
import threading
import time
from pathlib import Path
from typing import Callable, TypeVar

from openai import (
    APIConnectionError,
    APIResponseValidationError,
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


class LLMSchemaError(LLMError):
    """Ответ не прошёл проверку схемы и после исправлений. Меньшая порция может помочь."""


class LLMNetworkError(LLMError):
    """Сеть или сервер провайдера: нет соединения, таймаут, 5xx после всех повторов.

    Меньшая порция тут не поможет, поэтому вызывающий код порцию не делит.
    """


class LLMContextTooLong(LLMError):
    """Запрос длиннее окна модели (400 про длину контекста). Повтор не поможет, меньшая порция может."""


class LLMFatal(LLMError):
    """Ошибка, которую повтор не исправит.

    kind: auth (ключ не принят), model (модель не найдена), quota (суточная квота или баланс),
    rate (лимит запросов не отпустил за все повторы). По kind командная строка решает,
    писать ли частичный отчёт.
    """

    def __init__(self, message: str, kind: str = "other"):
        super().__init__(message)
        self.kind = kind


# Паузы при минутном лимите (429), если провайдер не сказал, сколько ждать.
RATE_WAITS_SEC = (15.0, 30.0, 60.0, 65.0, 65.0)
MAX_RATE_WAIT_SEC = 120.0
# Слова в тексте ошибки 400, по которым понятно, что провайдер не принял формат ответа.
# Только тогда режим JSON понижается, и только для этой схемы.
JSON_ERROR_WORDS = ("response_format", "json_schema", "json_object", "schema", "structured", "output_format", "strict")
# Суточная квота и баланс: ждать бесполезно, каждый повтор тратит запрос.
# Gemini (26.11.2026): «Generate content requests per day limit exceeded on Free Tier»,
# quotaId «GenerateRequestsPerDayPerProjectPerModel-FreeTier». Минутный лимит Gemini тоже пишет
# «quota», поэтому одно слово quota признаком суточной не считаем.
DAILY_WORDS = ("per day", "perday", "daily", "insufficient_quota", "credit balance", "billing")
# Длина контекста. OpenAI: «This model's maximum context length is N tokens», код context_length_exceeded;
# Anthropic: «prompt is too long: N tokens > M maximum»; Gemini: «The input token count (N) exceeds the maximum
# number of tokens allowed (M)».
CONTEXT_WORDS = ("context_length_exceeded", "maximum context length", "context length", "context window",
                 "prompt is too long", "input token count", "too many tokens", "exceeds the maximum number of tokens")
# Тот же текст OpenAI бывает из-за слишком большого max_tokens: тогда это не длина документа.
OUTPUT_LIMIT_WORDS = ("max_tokens", "max_completion_tokens", "in the completion", "completion tokens")
AUTH_WORDS = ("api key", "api_key", "apikey", "invalid x-api-key", "authentication")
# Пока есть запасная модель, на сбои сервера и таймауты текущей тратим не больше стольких повторов:
# перегруженная модель держит 503 часами, а каждый повтор идёт в счёт суточной квоты.
FALLBACK_AFTER_RETRIES = 2
# Сколько раз повторять вызов после таймаута, если запасной модели нет.
TIMEOUT_RETRIES = 2
# Столько вызовов подряд, кончившихся сетевым сбоем после всех повторов, и прогон останавливается
# (LLMFatal rate): без сети иначе каждая порция ждёт свои повторы, и шаг идёт часами.
NET_FAILS_FATAL = 3


def _retry_after(error: Exception) -> float | None:
    """Сколько ждать по ответу провайдера: заголовок retry-after или retryDelay в теле Gemini."""
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None) or {}
    for name, scale in (("retry-after-ms", 0.001), ("retry-after", 1.0)):
        value = headers.get(name)
        if value:
            try:
                return float(value) * scale
            except ValueError:
                pass
    text = error_text(error) if isinstance(error, APIStatusError) else str(error)
    match = re.search(r"retry(?:Delay|[ _-]?after|\s+in)?\W{0,4}(\d+(?:\.\d+)?)\s*s", text, re.IGNORECASE)
    return float(match.group(1)) if match else None


# Короче ключ не прячем: тестовый «x» иначе съел бы все буквы x в тексте.
MIN_SECRET_CHARS = 8


def redact(text: str, secret: str | None) -> str:
    """Ключ в тексте ошибки или в логе заменяется на ***: провайдер может вернуть адрес запроса с ключом."""
    if secret and len(secret) >= MIN_SECRET_CHARS and secret in text:
        return text.replace(secret, "***")
    return text


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


class _Ping(BaseModel):
    """Схема из двух полей для проверки ключа."""

    ok: bool
    reply: str


class LLMClient:
    def __init__(self, settings: Settings, log: Callable[[str], None] | None = None):
        self.s = settings
        raw_log = log or (lambda _msg: None)
        self.log = lambda message: raw_log(redact(message, settings.api_key))
        self.stats = LLMStats()
        self._client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.timeout_sec,
            max_retries=0,
        )
        self._lock = threading.Lock()
        self._last_call = 0.0
        self._sleep = time.sleep
        # Порядок понижения режима JSON, если провайдер отклоняет формат ответа.
        # parse: схема pydantic через помощник SDK; schema: ручной json_schema;
        # object: просто JSON, схема только в тексте промпта; none: без формата.
        # Понижение идёт отдельно по каждой схеме: одна неудачная схема не снимает режим с остальных.
        self._ladder = ["parse", "schema", "object", "none"] if settings.json_mode == "auto" else [settings.json_mode]
        self._modes: dict[str, list[str]] = {}
        # Gemini 3.6+ игнорирует temperature и обещает ошибку 400, поэтому ему параметр не шлём.
        self._send_temperature = settings.temperature is not None and settings.provider != "gemini"
        if settings.temperature is not None and settings.provider == "gemini":
            self.log("  LLM_TEMPERATURE задан, но для Gemini не отправляется")
        # Уровень рассуждения: param (reasoning_effort), extra (thinking_level в extra_body, только Gemini), off.
        self._reasoning = "param"
        self._send_max_tokens = True
        self._cache_dir = Path(settings.cache_dir) if settings.cache_dir else None
        # Цепочка моделей: основная и запасные. Переход вперёд один на весь прогон, назад не возвращаемся.
        self._models = [settings.model, *[m for m in settings.fallback_models if m != settings.model]]
        self._model_i = 0
        # Сетевые сбои подряд (после всех повторов вызова) и был ли хоть один ответ: свой или из кэша.
        self._net_fails = 0
        self._answered = False

    @property
    def model(self) -> str:
        """Модель, которая отвечает сейчас: основная или запасная после перехода."""
        return self._models[self._model_i]

    def _has_fallback(self) -> bool:
        return self._model_i + 1 < len(self._models)

    def _switch_model(self, used: str, why: str) -> bool:
        """Переходит на следующую запасную модель после сбоя модели used. False, если запасных не осталось."""
        with self._lock:
            if self._models[self._model_i] != used:
                return True  # другой поток уже перешёл
            if self._model_i + 1 >= len(self._models):
                return False
            self._model_i += 1
            new = self._models[self._model_i]
            # Новая модель может принимать другое: режим JSON и параметры пробуем заново.
            self._modes = {}
            self._reasoning = "param"
            self._send_max_tokens = True
        self._note(f"модель {used}: {why}, перехожу на запасную {new}")
        return True

    def _modes_for(self, schema: type[BaseModel]) -> list[str]:
        with self._lock:
            return self._modes.setdefault(schema.__name__, list(self._ladder))

    @property
    def json_mode(self) -> str:
        """Режим ответа JSON после возможных понижений: один на все схемы или по каждой схеме."""
        used = {name: modes[0] for name, modes in self._modes.items()}
        if not used:
            return self._ladder[0]
        if len(set(used.values())) == 1:
            return next(iter(used.values()))
        return ", ".join(f"{name}: {mode}" for name, mode in sorted(used.items()))

    @property
    def reasoning_mode(self) -> str:
        return {"param": "reasoning_effort", "extra": "thinking_level в extra_body", "off": "не передаётся"}[self._reasoning]

    def _note(self, text: str) -> None:
        """Отказ провайдера или понижение режима: в лог и в паспорт отчёта."""
        self.log("  " + text)
        if text not in self.stats.notes:
            self.stats.notes.append(text)

    # ---------- кэш ----------

    def _cache_key(self, system: str, user: str, schema: type[BaseModel], kind: str, effort: str | None = None,
                   model: str | None = None) -> str:
        """Ключ по модели, которой идёт запрос: ответ запасной модели не ложится под именем основной."""
        payload = json.dumps(
            [self.s.base_url, model or self.model, effort or self.s.step_params(kind)[0],
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
        """Запись через временный файл рядом: прерванный прогон не оставит обрезанный JSON."""
        if not self._cache_dir:
            return
        tmp = self._cache_dir / f"{key}.{os.getpid()}.{threading.get_ident()}.tmp"
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            tmp.write_text(obj.model_dump_json(), encoding="utf-8")
            os.replace(tmp, self._cache_dir / f"{key}.json")
        except OSError as exc:
            self.log(f"  кэш не записан ({self._cache_dir}): {exc.strerror or exc}")
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass

    # ---------- вызов ----------

    def complete_json(
        self, step: str, system: str, user: str, schema: type[T], kind: str = "",
        effort: str | None = None, use_cache: bool = True,
    ) -> T:
        """Возвращает ответ модели, проверенный по схеме. Бросает LLMError, если не вышло.

        step: подпись для лога. kind: вид шага, по нему берутся уровень рассуждения и лимит вывода.
        effort: уровень рассуждения вместо уровня шага (повтор после обрезки).
        Все ошибки модели выходят наружу только отсюда: здесь из их текста убирается ключ.
        """
        try:
            return self._complete_json(step, system, user, schema, kind, effort, use_cache)
        except LLMError as exc:
            exc.args = tuple(redact(a, self.s.api_key) if isinstance(a, str) else a for a in exc.args)
            raise

    def _complete_json(self, step: str, system: str, user: str, schema: type[T], kind: str,
                       effort: str | None, use_cache: bool) -> T:
        key = self._cache_key(system, user, schema, kind, effort)
        cached = self._cache_get(key, schema) if use_cache else None
        if cached is not None:
            with self._lock:
                self.stats.cache_hits += 1
                self._answered = True
            return cached

        # Схема текстом добавляется в _kwargs и только в режимах object и none (П-04).
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        last_error = ""
        for attempt in range(self.s.max_repairs + 1):
            raw = self._chat(step, messages, schema, kind, effort)
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
            if use_cache:
                # Модель могла смениться внутри вызова (переход на запасную): ключ по той, что ответила.
                self._cache_put(self._cache_key(system, user, schema, kind, effort), obj)
            return obj
        raise LLMSchemaError(f"[{step}] модель не вернула валидный JSON: {last_error}")

    def check(self) -> dict:
        """Проверка ключа одним коротким вызовом без кэша. Бросает LLMError, как обычный вызов."""
        t0 = time.monotonic()
        out = self.complete_json(
            "проверка ключа", "Ты отвечаешь одним JSON-объектом.",
            'Верни JSON: ok = true, reply = "готово".', _Ping, kind="check", use_cache=False,
        )
        return {
            "ok": out.ok,
            "json_mode": self._modes_for(_Ping)[0],
            "reasoning": self.reasoning_mode,
            "max_tokens": self._send_max_tokens,
            "seconds": round(time.monotonic() - t0, 1),
            "notes": list(self.stats.notes),
            "tokens": self.stats.total_tokens,
        }

    def _throttle(self) -> None:
        if self.s.min_interval_sec <= 0:
            return
        with self._lock:
            wait = self._last_call + self.s.min_interval_sec - time.monotonic()
            self._last_call = max(time.monotonic(), self._last_call + self.s.min_interval_sec)
        if wait > 0:
            self._sleep(wait)

    def _kwargs(self, messages: list[dict], schema: type[BaseModel], kind: str, effort: str | None = None,
                model: str | None = None) -> dict:
        step_effort, max_tokens = self.s.step_params(kind)
        effort = effort or step_effort
        mode = self._modes_for(schema)[0]
        if mode in ("object", "none"):
            # Провайдер не держит схему сам: отдаём её текстом в системном сообщении.
            messages = [
                {**messages[0], "content": messages[0]["content"] + "\n\n" + schema_instruction(schema)},
                *messages[1:],
            ]
        kwargs: dict = {"model": model or self.model, "messages": messages}
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
        if self._reasoning == "param":
            kwargs["reasoning_effort"] = effort
        elif self._reasoning == "extra":
            # Запасной способ Gemini из страницы совместимости: thinking_level через extra_body.
            kwargs["extra_body"] = {"extra_body": {"google": {"thinking_config": {"thinking_level": effort}}}}
        if self._send_max_tokens:
            kwargs["max_tokens"] = max_tokens
        return kwargs

    def _not_api(self, detail: str) -> LLMFatal:
        """Адрес ответил, но не в формате OpenAI API: веб-страница, прокси, другой сервис (В-4)."""
        return LLMFatal(
            f"Адрес модели ответил не в формате OpenAI API (похоже на веб-страницу или другой сервис). "
            f"Проверьте адрес LLM_BASE_URL (обычно он кончается на /v1) и провайдера в .env. "
            f"Провайдер {self.s.provider}, адрес {self.s.base_url or 'по умолчанию'}. Ответ: {' '.join(detail.split())[:300]}",
            kind="model",
        )

    def _request(self, kwargs: dict) -> ChatCompletion:
        try:
            if not isinstance(kwargs.get("response_format"), type):
                response = self._client.chat.completions.create(**kwargs)
            else:
                raw = self._client.beta.chat.completions.with_raw_response.parse(**kwargs)
                try:
                    response = raw.parse()
                except ValidationError:
                    # SDK не разобрал ответ по схеме. Отдаём сырой текст дальше: там модель попросят исправить JSON.
                    response = ChatCompletion.model_validate_json(raw.text)
                except TypeError as exc:
                    # Тело без списка choices: SDK падает, перебирая None. Ошибка в теле ответа, не в запросе.
                    raise self._not_api(raw.text) from exc
        except APIResponseValidationError as exc:
            raise self._not_api(str(exc)) from exc
        except (AttributeError, ValueError) as exc:
            # Тело не JSON или не ответ чата: SDK отдаёт строку вместо объекта и падает на ней.
            # ValueError включает ошибку проверки pydantic и разбора JSON.
            raise self._not_api(f"{type(exc).__name__}: {exc}") from exc
        if not isinstance(response, ChatCompletion):
            raise self._not_api(str(response))
        if getattr(response, "choices", None) is None:
            # JSON пришёл, но без choices: SDK собрал объект без проверки полей.
            raise self._not_api(response.model_dump_json()[:300])
        return response

    def _downgrade(self, error: BadRequestError, schema: type[BaseModel]) -> bool:
        """Убирает одну возможность, которую провайдер назвал в ошибке. False, если ошибка про другое."""
        text = error_text(error).lower()
        if self._send_temperature and "temperature" in text:
            self._send_temperature = False
            self._note("провайдер не принимает temperature, отправляю без него")
            return True
        # Gemini на неподдерживаемый уровень отвечает 400 «Thinking level ... is not supported for this model».
        if self._reasoning != "off" and ("reasoning" in text or "thinking" in text):
            if self._reasoning == "param" and self.s.provider == "gemini":
                self._reasoning = "extra"
                self._note("провайдер не принял reasoning_effort, пробую thinking_level в extra_body")
            else:
                self._reasoning = "off"
                self._note("провайдер не принимает уровень рассуждения, отправляю без него")
            return True
        if self._send_max_tokens and "max_tokens" in text:
            self._send_max_tokens = False
            self._note("провайдер не принимает max_tokens, отправляю без лимита вывода")
            return True
        if any(word in text for word in JSON_ERROR_WORDS):
            modes = self._modes_for(schema)
            with self._lock:
                if len(modes) > 1:
                    dropped = modes.pop(0)
                    self._note(f"схема {schema.__name__}: режим JSON «{dropped}» отклонён, перехожу на «{modes[0]}»")
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

    def _auth_fatal(self, exc: APIStatusError) -> LLMFatal:
        text = error_text(exc)
        if "FREE_TIER_VERIFICATION_REQUIRED" in text:
            hint = "Проект в AI Studio не верифицирован: откройте https://aistudio.google.com/ и пройдите проверку."
        else:
            hint = "Ключ не принят, проверьте .env: ключ, провайдер и адрес LLM_BASE_URL."
        return LLMFatal(f"{hint} Провайдер {self.s.provider}, ответ: {text[:600]}", kind="auth")

    def _quota_fatal(self, text: str, model: str | None = None) -> LLMFatal:
        return LLMFatal(
            f"Суточная квота или баланс модели «{model or self.model}» исчерпаны. Смените модель (--model), ключ или уровень "
            f"оплаты и запустите снова: готовые шаги возьмутся из кэша. Ответ провайдера: {text[:600]}",
            kind="quota",
        )

    def _got_answer(self) -> None:
        """Провайдер ответил: счётчик сетевых сбоев подряд обнуляется."""
        with self._lock:
            self._net_fails = 0
            self._answered = True

    def _net_failure(self, step: str, model: str, limit: int, reason: str) -> LLMError:
        """Вызов кончился сетевым сбоем после всех повторов.

        Обычно это ошибка шага (LLMNetworkError). Фатальной она становится, если сбоев подряд
        NET_FAILS_FATAL или если провайдер не ответил ещё ни разу: тогда ждать дальше бессмысленно.
        """
        with self._lock:
            self._net_fails += 1
            fails, answered = self._net_fails, self._answered
        if fails >= NET_FAILS_FATAL or not answered:
            why = (f"{fails} вызова подряд кончились сбоем сети или сервера" if answered
                   else "провайдер не ответил ни разу")
            return LLMFatal(
                f"Модель {model} недоступна: {why} (повторов на вызов {limit}). Проверьте интернет, "
                f"адрес LLM_BASE_URL и состояние провайдера и запустите снова: готовые шаги возьмутся из кэша. "
                f"Последняя ошибка: {reason}",
                kind="rate",
            )
        return LLMNetworkError(f"[{step}] модель {model} не ответила за {limit} повторов: {reason}")

    def _chat(self, step: str, messages: list[dict], schema: type[BaseModel], kind: str = "",
              effort: str | None = None) -> str:
        """Один ответ модели с разбором ошибок по видам: auth, model, quota, rate."""
        delay = 2.0
        transient = 0
        rate_hits = 0
        empty_retried = False
        model = self.model
        while True:
            if model != self.model:
                # Модель сменилась (здесь или в соседнем потоке): счётчики повторов начинаются заново.
                model, delay, transient, rate_hits = self.model, 2.0, 0, 0
            self._throttle()
            wait: float | None = None
            try:
                response = self._request(self._kwargs(messages, schema, kind, effort, model))
            except LengthFinishReasonError as exc:
                self._count(exc.completion)
                self._got_answer()
                raise LLMTruncated(f"[{step}] ответ обрезан по лимиту длины") from exc
            except ContentFilterFinishReasonError as exc:
                self._got_answer()
                raise LLMError(f"[{step}] ответ закрыт фильтром содержания провайдера") from exc
            except BadRequestError as exc:
                text = error_text(exc)
                low = text.lower()
                if any(word in low for word in CONTEXT_WORDS) and not any(word in low for word in OUTPUT_LIMIT_WORDS):
                    raise LLMContextTooLong(
                        f"[{step}] документ длиннее окна модели, шаг пропущен. Ответ провайдера: {text[:300]}"
                    ) from exc
                # Gemini на неверный ключ отвечает 400 INVALID_ARGUMENT «Please pass a valid API key»
                # (проверено живым вызовом 25.11.2026), а не 401.
                if any(word in low for word in AUTH_WORDS):
                    raise self._auth_fatal(exc) from exc
                if any(word in low for word in DAILY_WORDS):
                    if self._switch_model(model, "суточная квота или баланс исчерпаны"):
                        continue
                    raise self._quota_fatal(text, model) from exc
                if self._downgrade(exc, schema):
                    continue
                # Остальные 400 режим не трогают: ошибка шага с текстом провайдера.
                raise LLMError(f"[{step}] провайдер отклонил запрос: {text[:1500]}") from exc
            except (AuthenticationError, PermissionDeniedError) as exc:
                raise self._auth_fatal(exc) from exc
            except NotFoundError as exc:
                # Запасной модели у этого ключа может не быть: идём дальше по цепочке. Основная обязана существовать.
                if model != self._models[0] and self._switch_model(model, "не найдена у провайдера"):
                    continue
                raise LLMFatal(
                    f"Модель «{model}» не найдена у провайдера {self.s.provider} или адрес API неверный. "
                    f"Проверьте имя модели в .env или --model. Ответ: {error_text(exc)[:600]}",
                    kind="model",
                ) from exc
            except RateLimitError as exc:
                text = error_text(exc)
                if any(word in text.lower() for word in DAILY_WORDS):
                    if self._switch_model(model, "суточная квота или баланс исчерпаны"):
                        continue
                    raise self._quota_fatal(text, model) from exc
                error: Exception = exc
                # Минутный лимит: пауза от провайдера, иначе 15, 30, 60, 65, 65 секунд.
                wait = _retry_after(exc) or RATE_WAITS_SEC[min(rate_hits, len(RATE_WAITS_SEC) - 1)]
                wait = min(wait, MAX_RATE_WAIT_SEC)
                rate_hits += 1
            except (APITimeoutError, APIConnectionError) as exc:
                error = exc
            except APIStatusError as exc:
                if exc.status_code < 500:
                    raise LLMError(f"[{step}] ошибка провайдера {exc.status_code}: {error_text(exc)[:1500]}") from exc
                error = exc
            else:
                self._count(response)
                self._got_answer()
                choice = response.choices[0] if response.choices else None
                content = (choice.message.content or "") if choice else ""
                finish = choice.finish_reason if choice is not None else None
                if finish == "length":
                    raise LLMTruncated(f"[{step}] ответ обрезан по лимиту длины")
                if finish == "content_filter":
                    raise LLMError(f"[{step}] ответ закрыт фильтром содержания провайдера")
                if content.strip():
                    return content
                # Пустой ответ: один повтор, дальше ошибка шага.
                if empty_retried:
                    raise LLMError(f"[{step}] модель дважды вернула пустой ответ")
                empty_retried = True
                with self._lock:
                    self.stats.retries += 1
                self.log(f"  [{step}] пустой ответ модели, повторяю один раз")
                continue

            transient += 1
            rate = isinstance(error, RateLimitError)
            hung = isinstance(error, APITimeoutError)
            # Минутный лимит ждём полностью: он общий для ключа. Сбои сервера при запасной модели ждём недолго.
            # Таймаут значит, что модель молчала весь timeout_sec: при запасной уходим сразу,
            # без запасной повторяем не больше TIMEOUT_RETRIES раз, иначе зависшая модель держит прогон десятки минут.
            if rate:
                limit = self.s.max_retries
            elif self._has_fallback():
                limit = 0 if hung else min(self.s.max_retries, FALLBACK_AFTER_RETRIES)
            else:
                limit = min(self.s.max_retries, TIMEOUT_RETRIES) if hung else self.s.max_retries
            if transient > limit:
                why = "держит лимит запросов (429)" if rate else f"не отвечает ({type(error).__name__})"
                if self._switch_model(model, why):
                    continue
                if isinstance(error, RateLimitError):
                    # Лимит не отпустил за все паузы: похоже на исчерпанную дневную квоту.
                    # Готовые ответы лежат в кэше, повторный запуск продолжит с этого места.
                    raise LLMFatal(
                        f"Провайдер держит лимит запросов (429) после {self.s.max_retries} повторов. "
                        "Подождите или смените модель/ключ и запустите снова: готовые шаги возьмутся из кэша.",
                        kind="rate",
                    )
                # У ошибки сервера причина лежит в теле ответа («high demand» у перегруженной модели Gemini).
                reason = error_text(error)[:400] if isinstance(error, APIStatusError) else str(error)
                raise self._net_failure(step, model, limit, reason)
            if wait is None:
                # Сбой сервера, таймаут, обрыв связи: 2-60 секунд с удвоением.
                wait = min(delay + random.uniform(0, 1), MAX_BACKOFF_SEC)
                retry_after = _retry_after(error)
                if retry_after:
                    wait = min(max(wait, retry_after), MAX_BACKOFF_SEC)
                delay = min(delay * 2, MAX_BACKOFF_SEC)
            with self._lock:
                self.stats.retries += 1
            self.log(f"  [{step}] {type(error).__name__}, повтор {transient}/{limit} через {wait:.0f} с")
            self._sleep(wait)
