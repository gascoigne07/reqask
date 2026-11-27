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


# ---------- загрузчик: заголовки и проверка идентификаторов ----------

from pathlib import Path  # noqa: E402

from reqask.loader import Document, Line, LoadError, load_document  # noqa: E402


def test_is_heading_matches_headings_list(tmp_path):
    path = tmp_path / "d.md"
    path.write_text("# A\nтекст\n## B\n```\n# не заголовок\n```\n### C\n", encoding="utf-8")
    doc = load_document(path)
    expected = {no for no, _level, _title in doc._headings}
    assert expected == {1, 3, 7}
    assert [no for no in range(1, doc.n + 1) if doc.is_heading(no)] == sorted(expected)
    assert not doc.is_content(1) and doc.is_content(2)


def test_check_ids_keeps_order_without_duplicates(tmp_path):
    from reqask.pipeline import Pipeline
    from test_core import SETTINGS, FakeLLM

    path = tmp_path / "d.md"
    path.write_text("FR-1. Система должна А.\nFR-2. Система должна Б.\nFR-1. Система должна В.\n", encoding="utf-8")
    doc = load_document(path)
    pipe = Pipeline(FakeLLM(), SETTINGS, lambda _m: None)
    pipe._check_ids(doc, [])
    assert pipe.quality.ids_in_document == 2
    assert pipe.quality.ids_missing == ["FR-1", "FR-2"]


# ---------- DOCX: таблицы ----------

def test_docx_table_merged_cells_pipe_and_separator(tmp_path):
    import docx

    d = docx.Document()
    d.add_paragraph("Перед таблицей")
    table = d.add_table(rows=3, cols=3)
    top = table.cell(0, 0).merge(table.cell(0, 2))
    top.text = "Общий заголовок"
    for i, text in enumerate(["Поле", "Значение", "Примечание"]):
        table.cell(1, i).text = text
    table.cell(2, 0).text = "mode"
    table.cell(2, 1).text = "a|b"
    table.cell(2, 2).text = "два   слова"
    path = tmp_path / "t.docx"
    d.save(str(path))
    texts = [line.text for line in load_document(path).lines]
    assert texts[1:6] == [
        "| Общий заголовок |",
        "| --- |",
        "| Поле | Значение | Примечание |",
        "| mode | a\\|b | два слова |",
        "",
    ]


def test_docx_separator_is_table_separator_for_loader(tmp_path):
    import docx

    d = docx.Document()
    table = d.add_table(rows=2, cols=2)
    for r in range(2):
        for c in range(2):
            table.cell(r, c).text = f"x{r}{c}"
    path = tmp_path / "t.docx"
    d.save(str(path))
    doc = load_document(path)
    assert [doc.is_content(i) for i in (1, 2, 3)] == [True, False, True]
