"""Находки аудита кода: границы настроек, ключ в repr, загрузчик, кэш, длина контекста, внедрение инструкций."""

import os

import pytest

from reqask.config import ConfigError, Settings, load_settings


@pytest.fixture
def env(monkeypatch, tmp_path):
    """Чистое окружение: только ключ и модель, .env из рабочей папки не читается."""
    monkeypatch.chdir(tmp_path)
    for name in list(os.environ):
        if name.startswith(("LLM_", "GEMINI_", "ANTHROPIC_", "OPENAI_", "OLLAMA_", "REQASK_")):
            monkeypatch.delenv(name)
    monkeypatch.setenv("LLM_API_KEY", "secret-key-123456")
    monkeypatch.setenv("LLM_MODEL", "m")
    return monkeypatch


@pytest.mark.parametrize("name,value", [
    ("LLM_MAX_REPAIRS", "-1"), ("LLM_MAX_RETRIES", "-1"), ("LLM_TIMEOUT_SEC", "0"),
    ("LLM_TIMEOUT_SEC", "-5"), ("LLM_MIN_INTERVAL_SEC", "-1"), ("LLM_TIMEOUT_SEC", "nan"),
])
def test_numeric_settings_out_of_range(env, name, value):
    env.setenv(name, value)
    with pytest.raises(ConfigError, match=name):
        load_settings()


def test_numeric_settings_boundaries_ok(env):
    env.setenv("LLM_MAX_REPAIRS", "0")
    env.setenv("LLM_MAX_RETRIES", "0")
    env.setenv("LLM_MIN_INTERVAL_SEC", "0")
    env.setenv("LLM_TIMEOUT_SEC", "0.5")
    s = load_settings()
    assert (s.max_repairs, s.max_retries, s.min_interval_sec, s.timeout_sec) == (0, 0, 0.0, 0.5)


def test_api_key_not_in_repr():
    s = Settings(provider="p", base_url=None, api_key="secret-key-123456", model="m")
    assert "secret-key-123456" not in repr(s)
    assert s.api_key == "secret-key-123456"
