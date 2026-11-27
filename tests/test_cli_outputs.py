"""Файлы командной строки: пробная запись, каталог на входе, один и тот же файл, --render, --dry-run."""

import os

import pytest

from reqask import cli, report_html
from reqask.report import _first_sentence
from reqask.schemas import RunResult

from helpers import run, use
from helpers import FakeLLM


def _full_run(workdir, monkeypatch, *extra):
    use(monkeypatch, FakeLLM())
    assert run(*extra) == cli.EXIT_OK
    return workdir / "out"


def test_probe_fails_before_model_when_a_report_file_is_a_directory(workdir, monkeypatch, capsys):
    llm = use(monkeypatch, FakeLLM())
    (workdir / "out" / "report.questions.md").mkdir(parents=True)
    assert run() == cli.EXIT_INPUT
    assert "report.questions.md" in capsys.readouterr().err
    assert llm.steps == []


def test_probe_leaves_no_empty_files_and_keeps_existing(workdir, monkeypatch):
    out = workdir / "out"
    out.mkdir()
    (out / "report.json").write_text("старое", encoding="utf-8")
    cli._probe_writable(cli._report_files(out / "report.md"))
    assert (out / "report.json").read_text(encoding="utf-8") == "старое"
    assert sorted(p.name for p in out.iterdir()) == ["report.json"]


def test_json_is_written_first_and_survives_render_failure(workdir, monkeypatch, capsys):
    use(monkeypatch, FakeLLM())

    def broken(_result):
        raise OSError("нет места на диске")

    monkeypatch.setattr(cli, "render", broken)
    assert run() == cli.EXIT_INPUT
    err = capsys.readouterr().err
    assert "не удалось записать отчёт" in err and "report.json" in err
    RunResult.model_validate_json((workdir / "out" / "report.json").read_text(encoding="utf-8"))


def test_render_html_failure_keeps_md_and_json(workdir, monkeypatch, capsys):
    use(monkeypatch, FakeLLM())

    def broken(_result):
        raise RuntimeError("сломался рендер")

    monkeypatch.setattr(cli, "render_html", broken)
    assert run() == cli.EXIT_OK
    out = workdir / "out"
    assert (out / "report.md").is_file() and (out / "report.json").is_file() and not (out / "report.html").exists()
    assert "report.html не собран" in capsys.readouterr().err


def test_directory_input_keeps_previous_report(workdir, capsys):
    out = workdir / "out"
    out.mkdir()
    (out / "report.md").write_text("прежний отчёт", encoding="utf-8")
    (out / "report.json").write_text("{}", encoding="utf-8")
    (workdir / "folder").mkdir()
    assert cli.main(["-i", "folder", "-o", "out/report.md", "-q"]) == cli.EXIT_INPUT
    assert (out / "report.md").read_text(encoding="utf-8") == "прежний отчёт"
    assert (out / "report.json").exists()
    assert "папка" in capsys.readouterr().err


def test_broken_pdf_still_gets_diagnostic_report(workdir):
    (workdir / "broken.pdf").write_bytes(b"%PDF-1.4 broken")
    assert cli.main(["-i", "broken.pdf", "-o", "out/report.md", "-q"]) == cli.EXIT_INPUT
    assert "Не вынесен" in (workdir / "out" / "report.md").read_text(encoding="utf-8")


def test_hard_link_and_case_variant_are_same_file(workdir, monkeypatch):
    llm = use(monkeypatch, FakeLLM())
    os.link(workdir / "spec.md", workdir / "alias.md")
    assert cli.main(["-i", "spec.md", "-o", "alias.md", "-q"]) == cli.EXIT_INPUT
    assert llm.steps == []
    if (workdir / "SPEC.MD").exists():  # файловая система без учёта регистра
        assert cli.main(["-i", "spec.md", "-o", "SPEC.MD", "-q"]) == cli.EXIT_INPUT
        assert llm.steps == []
    else:
        pytest.skip("файловая система с учётом регистра: вариант с заглавными буквами это другой файл")


def test_compare_refuses_output_that_is_hard_link_to_input(workdir, capsys):
    run_json = workdir / "a.json"
    run_json.write_text("{}", encoding="utf-8")
    os.link(run_json, workdir / "b.md")
    assert cli.main(["--compare", "a.json", "a.json", "-o", "b.md"]) == cli.EXIT_INPUT


def test_no_html_and_no_json_report_stale_files(workdir, monkeypatch, capsys):
    out = _full_run(workdir, monkeypatch)
    capsys.readouterr()
    use(monkeypatch, FakeLLM())
    assert run("--no-html", "--no-json") == cli.EXIT_OK
    text = capsys.readouterr().out
    assert "Старый report.html не обновлён" in text and "Старый report.json не обновлён" in text
    assert (out / "report.html").exists() and (out / "report.json").exists()


def test_debug_traceback_does_not_print_key(workdir, monkeypatch, capsys):
    monkeypatch.setenv("REQASK_DEBUG", "1")
    monkeypatch.setenv("LLM_API_KEY", "sk-secret-key-123456")

    def boom(*a, **k):
        raise RuntimeError("запрос к https://x/?key=sk-secret-key-123456 упал")

    monkeypatch.setattr(cli, "load_document", boom)
    assert cli.main(["-i", "spec.md", "-o", "out/report.md", "-q"]) == cli.EXIT_NO_MODEL
    err = capsys.readouterr().err
    assert "sk-secret-key-123456" not in err and "***" in err


def test_render_rebuilds_same_files_without_model_or_key(workdir, monkeypatch, tmp_path_factory):
    out = _full_run(workdir, monkeypatch)
    for name in ("LLM_API_KEY", "LLM_MODEL", "LLM_BASE_URL"):
        monkeypatch.delenv(name)
    other = workdir / "again"
    assert cli.main(["--render", str(out / "report.json"), "-o", str(other / "report.md")]) == cli.EXIT_OK
    for name in ("report.md", "report.html", "report.questions.md"):
        assert (other / name).read_bytes() == (out / name).read_bytes(), name
    assert (other / "report.json").is_file()


def test_render_respects_no_html_no_json_and_rejects_bad_input(workdir, monkeypatch, capsys):
    out = _full_run(workdir, monkeypatch)
    other = workdir / "again"
    assert cli.main(["--render", str(out / "report.json"), "-o", str(other / "report.md"), "--no-html", "--no-json"]) == 0
    assert sorted(p.name for p in other.iterdir()) == ["report.md", "report.questions.md"]
    bad = workdir / "bad.json"
    bad.write_text("{не json", encoding="utf-8")
    assert cli.main(["--render", "bad.json", "-o", "x.md"]) == cli.EXIT_INPUT
    bad.write_text('{"a": 1}', encoding="utf-8")
    assert cli.main(["--render", "bad.json", "-o", "x.md"]) == cli.EXIT_INPUT
    assert cli.main(["--render", "nope.json", "-o", "x.md"]) == cli.EXIT_INPUT
    assert cli.main(["--render", "bad.json"]) == cli.EXIT_INPUT
    for extra in (["-i", "spec.md"], ["--check"], ["--compare", "a", "b"], ["--dry-run"]):
        assert cli.main(["--render", str(out / "report.json"), "-o", "x.md", *extra]) == cli.EXIT_INPUT
    assert not (workdir / "x.md").exists()


def test_old_json_without_schema_version_is_readable(workdir, monkeypatch):
    out = _full_run(workdir, monkeypatch)
    text = (out / "report.json").read_text(encoding="utf-8")
    assert '"schema_version": 1' in text
    result = RunResult.model_validate_json(text.replace('  "schema_version": 1,\n', ""))
    assert result.schema_version == 1


def test_dry_run_needs_no_key_and_no_model(workdir, monkeypatch, capsys):
    llm = use(monkeypatch, FakeLLM())
    for name in ("LLM_API_KEY", "LLM_MODEL", "LLM_BASE_URL"):
        monkeypatch.delenv(name)
    assert cli.main(["--dry-run", "-i", "spec.md"]) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "строк:" in out and "Шаг 3, нарезка: 1 кусок" in out and "по одному обращению на 6 требований" in out
    assert "Без шага 4: 6-7 обращений" in out and llm.steps == []
    assert cli.main(["--dry-run", "-i", "spec.md", "--no-critic", "--no-edge", "--batch-size", "2"]) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "на 2 требований" in out and "Без шага 4: 4 обращений" in out
    assert cli.main(["--dry-run"]) == cli.EXIT_INPUT
    assert not (workdir / "out").exists()


def test_call_estimate_line_is_only_in_log(workdir, monkeypatch, capsys):
    use(monkeypatch, FakeLLM())
    assert cli.main(["-i", "spec.md", "-o", "out/report.md"]) == cli.EXIT_OK
    assert "дальше примерно" in capsys.readouterr().err
    for name in ("report.md", "report.json", "report.html"):
        assert "дальше примерно" not in (workdir / "out" / name).read_text(encoding="utf-8")


def test_first_sentence_unclosed_quote_does_not_swallow_text():
    assert _first_sentence("Он сказал «да. Нет. Да", 100) == "Он сказал «да."
    assert _first_sentence("В разделе «12. Общие сведения» нет цифр. Дальше.", 100) == "В разделе «12. Общие сведения» нет цифр."


def test_html_where_falls_back_to_whole_set(workdir, monkeypatch):
    out = _full_run(workdir, monkeypatch)
    result = RunResult.model_validate_json((out / "report.json").read_text(encoding="utf-8"))
    finding = result.findings[0]
    finding.req_ids, finding.section = ["REQ-999"], ""
    page = report_html._Html(result)
    assert page.where(finding) == "набор в целом"
