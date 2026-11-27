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


# ---------- кэш ответов ----------

from test_llm import ONE, OneOut, client_with, completion  # noqa: E402,F401


def _cached_client(client_with, cache_dir, logs=None):
    client, sent, waits = client_with(lambda body, n: (200, completion(ONE)), cache_dir=str(cache_dir))
    if logs is not None:
        client.log = logs.append
    return client, sent


def test_cache_truncated_file_does_not_crash_and_calls_model(client_with, tmp_path):
    client, sent = _cached_client(client_with, tmp_path / "cache")
    key = client._cache_key("s", "u", OneOut, "")
    (tmp_path / "cache").mkdir()
    (tmp_path / "cache" / f"{key}.json").write_text('{"answer": "об', encoding="utf-8")
    out = client.complete_json("шаг", "s", "u", OneOut)
    assert out.answer == "ок" and len(sent) == 1
    # после новой записи файл целый и временных файлов нет
    assert sorted(p.suffix for p in (tmp_path / "cache").iterdir()) == [".json"]
    assert client._cache_get(key, OneOut).answer == "ок"


def test_cache_write_failure_is_logged_and_leaves_no_temp(client_with, tmp_path):
    cache = tmp_path / "cache"
    logs: list[str] = []
    client, _ = _cached_client(client_with, cache, logs)
    key = client._cache_key("s", "u", OneOut, "")
    cache.mkdir()
    (cache / f"{key}.json").mkdir()  # на месте файла каталог: replace не пройдёт
    out = client.complete_json("шаг", "s", "u", OneOut)
    assert out.answer == "ок"
    assert any("кэш не записан" in line for line in logs)
    assert [p.name for p in cache.iterdir()] == [f"{key}.json"]


# ---------- кодировка текстовых файлов ----------

RUS = ("Система должна принимать оплату картой через API банка. ФТ-1: СМС с кодом приходит в течение 30 секунд.\n"
       "Если оплата не прошла, пользователь видит сообщение об ошибке и может повторить попытку не более 3 раз.\n"
       "Администратор может отключить автопродление в личном кабинете; срок хранения данных не меньше 5 лет.\n")
FRENCH = ("Le résumé de la réunion à Paris est prêt. Les développeurs ont préparé l'été dernier un système "
          "qui gère les réservations et les paiements. Où est-ce que l'équipe a décidé d'enregistrer les données ?\n")
GERMAN = ("Das System muss alle Änderungen protokollieren. Die Größe der Datei darf nicht über zehn Megabyte "
          "liegen. Für Übersicht und Prüfung wird ein Bericht erzeugt, der äußerst genau über Fehler informiert.\n")


def _load(tmp_path, data: bytes, name="d.txt"):
    path = tmp_path / name
    path.write_bytes(data)
    return load_document(path)


@pytest.mark.parametrize("text", [
    RUS * 5,
    RUS,
    "Система должна хранить данные.\n",
    "СИСТЕМА ДОЛЖНА ХРАНИТЬ ДАННЫЕ\n",
    "Требования ФТ-1 и СМС через API: ФТ, НФТ, ТЗ, ИС, ЦБ, РФ.\n",
    "Пользователь вводит email и пароль. Сервер возвращает JSON со статусом 200.\n",
    "The system shall respond within 2 seconds.\n",
])
def test_cp1251_normal_text_is_read(tmp_path, text):
    doc = _load(tmp_path, text.encode("cp1251"))
    assert doc.lines[0].text == text.split("\n")[0]


def test_cp1251_real_requirements_file_is_read(tmp_path):
    text = (Path(__file__).resolve().parent.parent / "input" / "requirements.md").read_text(encoding="utf-8")
    doc = _load(tmp_path, text.encode("cp1251", errors="replace"), "r.md")
    assert doc.n > 50


@pytest.mark.parametrize("data", [
    (RUS * 5).encode("koi8-r"),
    "Система должна хранить данные.".encode("koi8-r"),
    (RUS * 5).encode("cp866"),
    FRENCH.encode("latin-1"),
    (GERMAN * 3).encode("latin-1"),
])
def test_wrong_encoding_is_rejected_with_advice(tmp_path, data):
    with pytest.raises(LoadError, match="UTF-8"):
        _load(tmp_path, data)
