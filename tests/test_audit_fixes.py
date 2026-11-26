"""Правки по аудиту кода 27.11: крайние входы, аргументы, ответы не в формате API, шаги конвейера."""

import os
from pathlib import Path

import pytest

from reqask import cli
from reqask.config import ConfigError, load_settings
from reqask.loader import LoadError, load_document

from test_cli import run, use, workdir  # noqa: F401  фикстура workdir нужна тестам ниже
from test_core import FakeLLM, doc  # noqa: F401


# ---------- вход (В-2, С-2, Н-2) ----------


def test_broken_docx_and_rtf_are_load_errors(tmp_path):
    fake = tmp_path / "spec.docx"
    fake.write_bytes(b"not a zip")
    with pytest.raises(LoadError, match="DOCX"):
        load_document(fake)
    rtf = tmp_path / "spec.rtf"
    rtf.write_text("{\\rtf1 text}", encoding="ascii")
    with pytest.raises(LoadError, match=r"\.rtf не поддерживается"):
        load_document(rtf)


@pytest.mark.skipif(os.name != "posix" or os.geteuid() == 0, reason="нужны права обычного пользователя POSIX")
def test_unreadable_file_is_load_error(tmp_path):
    path = tmp_path / "spec.md"
    path.write_text("Система должна работать.", encoding="utf-8")
    path.chmod(0)
    try:
        with pytest.raises(LoadError, match="Не удалось прочитать"):
            load_document(path)
    finally:
        path.chmod(0o644)


def test_directory_input_says_it_is_a_folder(tmp_path):
    with pytest.raises(LoadError, match="папка"):
        load_document(tmp_path)


def test_utf16_with_bom_is_read_as_text(tmp_path):
    path = tmp_path / "spec.txt"
    path.write_bytes("# Требования\n\n1. Система должна отвечать.\n".encode("utf-16"))
    doc = load_document(path)
    assert [line.text for line in doc.lines] == ["# Требования", "", "1. Система должна отвечать."]


def test_binary_file_with_text_extension_is_refused(tmp_path):
    path = tmp_path / "spec.md"
    path.write_bytes(bytes(range(256)) * 16)
    with pytest.raises(LoadError, match="двоичный"):
        load_document(path)
    nul = tmp_path / "nul.txt"
    nul.write_bytes("Система должна\x00 работать.\n".encode("utf-8"))
    with pytest.raises(LoadError, match="двоичный"):
        load_document(nul)


def test_ordinary_text_with_tabs_is_not_binary(tmp_path):
    path = tmp_path / "spec.md"
    path.write_text("| a\t| b |\r\n\fСистема должна работать.\n", encoding="utf-8")
    assert load_document(path).n == 3  # \f тоже делит строки (str.splitlines)


# ---------- аргументы и настройки (В-3, С-5, Н-1) ----------


@pytest.mark.parametrize("size", ["0", "-1"])
def test_batch_size_below_one_is_code_2_before_model(workdir, monkeypatch, size):
    llm = use(monkeypatch, FakeLLM())
    assert run("--batch-size", size) == cli.EXIT_INPUT
    assert llm.stats.calls == 0


def test_missing_env_file_is_config_error(workdir, monkeypatch):
    with pytest.raises(ConfigError, match="не найден"):
        load_settings(str(workdir / "nope.env"))
    use(monkeypatch, FakeLLM())
    assert run("--env-file", "nope.env") == cli.EXIT_INPUT


def test_output_folder_is_not_created_when_input_is_missing(workdir):
    code = cli.main(["-i", "missing.md", "-o", "new/report.md", "-q"])
    assert code == cli.EXIT_INPUT
    assert not (workdir / "new").exists()


# ---------- последний рубеж в командной строке (В-4) ----------


def test_unexpected_error_is_message_and_code_1(workdir, monkeypatch, capsys):
    use(monkeypatch, FakeLLM())

    def boom(self, doc, version):
        raise RuntimeError("что-то сломалось")

    monkeypatch.setattr(cli.Pipeline, "run", boom)
    monkeypatch.delenv("REQASK_DEBUG", raising=False)
    assert run() == cli.EXIT_NO_MODEL
    err = capsys.readouterr().err
    assert "Внутренняя ошибка агента: RuntimeError: что-то сломалось" in err
    assert "Traceback" not in err
    monkeypatch.setenv("REQASK_DEBUG", "1")
    assert run() == cli.EXIT_NO_MODEL
    assert "Traceback" in capsys.readouterr().err


# ---------- клиент модели (В-4, В-5) ----------

from reqask.llm import LLMFatal  # noqa: E402
from test_llm import ONE, OneOut, ask, client_with, completion  # noqa: E402,F401


@pytest.mark.parametrize("mode", ["parse", "none"])
def test_answer_not_in_openai_format_is_fatal_with_address_hint(client_with, mode):
    client, sent, _ = client_with(lambda b, n: (200, {"hello": "world"}), json_mode=mode)
    with pytest.raises(LLMFatal, match="LLM_BASE_URL") as err:
        ask(client)
    assert err.value.kind == "model" and len(sent) == 1


def test_cache_key_follows_model_that_answered(client_with, tmp_path):
    body = [{"error": {"code": 429, "message": "requests per day limit exceeded"}}]
    client, sent, _ = client_with(
        lambda b, n: (429, body) if b["model"] == "m" else (200, completion(ONE)),
        fallback_models=("b",), cache_dir=str(tmp_path))
    assert ask(client).answer == "ок"
    files = [p.stem for p in tmp_path.glob("*.json")]
    assert files == [client._cache_key("system", "user", OneOut, "review", model="b")]
    assert files != [client._cache_key("system", "user", OneOut, "review", model="m")]


def test_result_names_the_model_that_answered(doc):
    from test_core import SETTINGS
    from reqask.pipeline import Pipeline

    llm = FakeLLM()
    llm.model = "fallback-model"
    result = Pipeline(llm, SETTINGS).run(doc, "test")
    assert result.model == "fallback-model (запасная: основная fake-model не ответила)"
    same = FakeLLM()
    same.model = SETTINGS.model
    assert Pipeline(same, SETTINGS).run(doc, "test").model == SETTINGS.model
