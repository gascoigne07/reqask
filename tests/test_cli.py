"""Т-06. Командная строка: коды возврата, частичный отчёт, вывод не в Markdown, ошибка записи."""

from pathlib import Path

import pytest

from reqask import cli
from reqask.llm import LLMFatal
from reqask.schemas import BatchReviewOut, FinalOut, SegmentationOut

from test_core import DOC, FakeLLM


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch):
    """Чистая папка без .env: настройки только из переменных, кэш выключен, сети нет."""
    monkeypatch.chdir(tmp_path)
    for name in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_MODEL", "LLM_BASE_URL", "LLM_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:9/v1/")
    monkeypatch.setenv("LLM_API_KEY", "x")
    monkeypatch.setenv("LLM_MODEL", "fake")
    monkeypatch.setenv("REQASK_CACHE_DIR", "")
    (tmp_path / "spec.md").write_text(DOC, encoding="utf-8")
    return tmp_path


def use(monkeypatch, llm):
    monkeypatch.setattr(cli, "LLMClient", lambda settings, log=None: llm)
    return llm


def run(*extra):
    return cli.main(["-i", "spec.md", "-o", "out/report.md", "-q", *extra])


def test_full_report_is_code_0(workdir, monkeypatch):
    use(monkeypatch, FakeLLM())
    assert run() == cli.EXIT_OK
    for name in ("report.md", "report.questions.md", "report.json"):
        assert (workdir / "out" / name).is_file()
    assert "Отчёт неполный" not in (workdir / "out" / "report.md").read_text(encoding="utf-8")


def test_fail_on_critical_is_code_10(workdir, monkeypatch):
    use(monkeypatch, FakeLLM())
    assert run("--fail-on-critical") == cli.EXIT_CRITICAL  # в заглушке есть CRITICAL


class FatalAt(FakeLLM):
    def __init__(self, schema, kind):
        super().__init__()
        self.fatal_schema, self.kind = schema, kind

    def complete_json(self, step, system, user, schema, kind="", **opts):
        if schema is self.fatal_schema:
            raise LLMFatal("суточная квота исчерпана", kind=self.kind)
        return super().complete_json(step, system, user, schema, kind)


def test_fatal_on_last_step_gives_partial_report_code_3(workdir, monkeypatch):
    llm = use(monkeypatch, FatalAt(FinalOut, "quota"))
    assert run() == cli.EXIT_PARTIAL
    report = (workdir / "out" / "report.md").read_text(encoding="utf-8")
    assert "> **Отчёт неполный.**" in report and "причина: суточная квота исчерпана" in report
    assert "по неполным данным" in report
    assert "Сводные вопросы не сформированы" in report  # запасной путь вопросов
    assert "итог" not in llm.steps  # шаг с моделью после фатальной ошибки не вызывался


def test_fatal_in_review_skips_remaining_model_steps(workdir, monkeypatch):
    llm = use(monkeypatch, FatalAt(BatchReviewOut, "quota"))
    assert run() == cli.EXIT_PARTIAL
    assert not any(step.startswith("набор") for step in llm.steps)
    report = (workdir / "out" / "report.md").read_text(encoding="utf-8")
    assert "требования без проверки: REQ-01, REQ-02, REQ-03" in report


def test_fatal_segmentation_before_any_answer_is_code_1_without_report(workdir, monkeypatch, capsys):
    """Лимит на первом же вызове: модель не ответила ни разу, отчёт не пишется (ревью кода, пункт 1)."""
    use(monkeypatch, FatalAt(SegmentationOut, "rate"))
    assert run() == cli.EXIT_NO_MODEL
    assert not (workdir / "out" / "report.md").exists()
    assert "суточная квота исчерпана" in capsys.readouterr().err


def test_bad_key_on_first_call_is_code_1_without_report(workdir, monkeypatch, capsys):
    use(monkeypatch, FatalAt(SegmentationOut, "auth"))
    assert run() == cli.EXIT_NO_MODEL
    assert not (workdir / "out" / "report.md").exists()
    assert "отчёт не записан" in capsys.readouterr().err


def test_input_errors_are_code_2(workdir, monkeypatch, capsys):
    use(monkeypatch, FakeLLM())
    assert cli.main(["-i", "nope.md", "-o", "report.md", "-q"]) == cli.EXIT_INPUT
    assert cli.main(["-q"]) == cli.EXIT_INPUT
    monkeypatch.delenv("LLM_MODEL")
    assert run() == cli.EXIT_INPUT  # настройки неполные
    assert "LLM_MODEL" in capsys.readouterr().err


def test_pdf_output_is_refused_before_model_calls(workdir, monkeypatch, capsys):
    llm = use(monkeypatch, FakeLLM())
    assert cli.main(["-i", "spec.md", "-o", "report.pdf", "-q"]) == cli.EXIT_INPUT
    assert ".md" in capsys.readouterr().err and llm.steps == []
    assert not (workdir / "report.pdf").exists()


def test_write_error_is_code_2(workdir, monkeypatch, capsys):
    use(monkeypatch, FakeLLM())

    def broken(_result):
        raise OSError("нет места на диске")

    monkeypatch.setattr(cli, "render_questions", broken)
    assert run() == cli.EXIT_INPUT
    assert "не удалось записать отчёт" in capsys.readouterr().err


def test_interrupt_is_code_130(workdir, monkeypatch):
    class Stop(FakeLLM):
        def complete_json(self, *args, **kwargs):
            raise KeyboardInterrupt

    use(monkeypatch, Stop())
    assert run() == cli.EXIT_INTERRUPTED


def test_unreadable_document_gets_diagnostic_report(tmp_path, monkeypatch):
    """Повреждённый или пустой документ: код 2, причина в stderr и в файле отчёта; модель не вызывается."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "broken.pdf").write_bytes(b"%PDF-1.4 broken")
    (tmp_path / "empty.md").write_text("  \n", encoding="utf-8")
    assert cli.main(["-i", "broken.pdf", "-o", "out/report.md", "-q"]) == cli.EXIT_INPUT
    report = (tmp_path / "out" / "report.md").read_text(encoding="utf-8")
    assert "broken.pdf" in report and "**Вердикт: Не вынесен.**" in report and "- Причина: " in report
    assert cli.main(["-i", "empty.md", "-o", "empty-report.md", "-q"]) == cli.EXIT_INPUT
    assert "Файл пуст" in (tmp_path / "empty-report.md").read_text(encoding="utf-8")
    # Файла нет вовсе: это ошибка в команде, отчёт не пишется.
    assert cli.main(["-i", "nope.md", "-o", "nope-report.md", "-q"]) == cli.EXIT_INPUT
    assert not (tmp_path / "nope-report.md").exists()
