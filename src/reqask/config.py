"""Настройки прогона из переменных окружения и файла .env."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace

from dotenv import load_dotenv

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
DEFAULT_CACHE_DIR = ".reqask_cache"

# Уровень рассуждения и лимит вывода по видам шагов. Лимит взят с запасом:
# у Gemini токены рассуждения входят в лимит вывода. Числа начальные, уточняются по живым прогонам.
STEP_PARAMS: dict[str, tuple[str, int]] = {
    "segment": ("low", 16_000),
    "review": ("medium", 24_000),
    "set": ("medium", 24_000),
    "verdict": ("medium", 16_000),
}
DEFAULT_STEP_PARAMS = ("medium", 16_000)
JSON_MODES = ("auto", "parse", "schema", "object", "none")


class ConfigError(Exception):
    """Ошибка конфигурации, которую пользователь может исправить сам."""


@dataclass(frozen=True)
class Settings:
    provider: str
    base_url: str | None
    api_key: str
    model: str
    temperature: float | None = None
    reasoning_effort: str | None = None
    json_mode: str = "auto"
    max_retries: int = 5
    max_repairs: int = 2
    timeout_sec: float = 240.0
    min_interval_sec: float = 0.0
    concurrency: int = 1
    batch_size: int = 6
    cache_dir: str | None = DEFAULT_CACHE_DIR

    def step_params(self, kind: str) -> tuple[str, int]:
        """Уровень рассуждения и лимит вывода для шага. LLM_REASONING_EFFORT перекрывает уровень для всех шагов."""
        effort, max_tokens = STEP_PARAMS.get(kind, DEFAULT_STEP_PARAMS)
        return self.reasoning_effort or effort, max_tokens

    def with_overrides(self, **kwargs) -> "Settings":
        return replace(self, **{k: v for k, v in kwargs.items() if v is not None})


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    if not value or value.startswith("your_"):
        return default
    return value


def _num(name: str, default, cast):
    raw = _env(name)
    if raw is None:
        return default
    try:
        return cast(raw)
    except ValueError as exc:
        raise ConfigError(f"Переменная {name} должна быть числом, получено: {raw!r}") from exc


def _provider() -> tuple[str, str | None, str, str]:
    """Возвращает (провайдер, base_url, ключ, модель) по первому заполненному варианту."""
    if _env("LLM_BASE_URL") or _env("LLM_API_KEY"):
        model = _env("LLM_MODEL")
        if not model:
            raise ConfigError("Задан LLM_BASE_URL или LLM_API_KEY, но не задан LLM_MODEL.")
        return "custom", _env("LLM_BASE_URL"), _env("LLM_API_KEY", "not-needed"), model

    if _env("GEMINI_API_KEY"):
        return "gemini", GEMINI_BASE_URL, _env("GEMINI_API_KEY"), _env("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

    if _env("OPENAI_API_KEY"):
        model = _env("OPENAI_MODEL")
        if not model:
            raise ConfigError("Задан OPENAI_API_KEY, но не задан OPENAI_MODEL.")
        return "openai", None, _env("OPENAI_API_KEY"), model

    if _env("OLLAMA_MODEL"):
        base = _env("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        if not base.endswith("/v1"):
            base += "/v1"
        return "ollama", base, "ollama", _env("OLLAMA_MODEL")

    raise ConfigError(
        "Не найден ключ модели. Скопируйте .env.example в .env и впишите GEMINI_API_KEY "
        "(бесплатный ключ: https://aistudio.google.com/). Другие варианты описаны в .env.example."
    )


def load_settings(env_file: str | None = None) -> Settings:
    load_dotenv(env_file or ".env", override=False)
    provider, base_url, api_key, model = _provider()

    json_mode = (_env("LLM_JSON_MODE", "auto") or "auto").lower()
    if json_mode not in JSON_MODES:
        raise ConfigError("LLM_JSON_MODE: допустимы " + ", ".join(JSON_MODES) + ".")

    cache_raw = os.getenv("REQASK_CACHE_DIR")
    cache_dir = DEFAULT_CACHE_DIR if cache_raw is None else (cache_raw.strip() or None)

    return Settings(
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=_num("LLM_TEMPERATURE", None, float),
        reasoning_effort=_env("LLM_REASONING_EFFORT"),
        json_mode=json_mode,
        max_retries=_num("LLM_MAX_RETRIES", 5, int),
        max_repairs=_num("LLM_MAX_REPAIRS", 2, int),
        timeout_sec=_num("LLM_TIMEOUT_SEC", 240.0, float),
        min_interval_sec=_num("LLM_MIN_INTERVAL_SEC", 0.0, float),
        concurrency=max(1, _num("LLM_CONCURRENCY", 1, int)),
        batch_size=max(1, _num("REQASK_BATCH_SIZE", 6, int)),
        cache_dir=cache_dir,
    )
