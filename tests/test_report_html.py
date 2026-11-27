"""HTML-вариант отчёта: экранирование, только внутренние ссылки, якоря, числа как в report.md, флаг --no-html."""

import json
import re
from pathlib import Path

from reqask import cli, report_html
from reqask.llm import LLMFatal
from reqask.pipeline import Pipeline
from reqask.report import render
from reqask.report_html import render_html
from reqask.schemas import BatchReviewOut, RunResult, SegmentationOut

from helpers import run, use
from helpers import SETTINGS, FakeLLM

EVIL = "<script>alert(1)</script> \"><img src=x onerror=1> & `код` 'кавычки'"


def _result(doc, llm=None) -> RunResult:
    return Pipeline(llm or FakeLLM(), SETTINGS).run(doc, "test")


def _hrefs(page: str) -> list[str]:
    return re.findall(r'href="([^"]*)"', page)


def _ids(page: str) -> list[str]:
    return re.findall(r'\sid="([^"]*)"', page)


def _assert_anchors(page: str) -> None:
    ids = _ids(page)
    assert len(ids) == len(set(ids)), "идентификаторы на странице повторяются"
    for href in _hrefs(page):
        assert href.startswith("#"), href
        assert href[1:] in ids, f"ссылка {href} без цели"


def test_document_and_model_text_is_escaped(doc):
    result = _result(doc)
    result.document_name = EVIL
    result.requirements[0].quote = EVIL
    finding = next(f for f in result.findings if f.evidence and f.status not in ("merged", "dropped"))
    finding.evidence[0].quote = EVIL
    finding.problem = EVIL
    result.questions[0].text = EVIL
    result.questions[0].quotes[0].quote = EVIL
    page = render_html(result)

    assert page.count("<script>") == 1  # только свой встроенный скрипт
    assert "alert(1)</script>" not in page and "<img" not in page and '"><img' not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert "&quot;&gt;&lt;img src=x onerror=1&gt;" in page
    assert "&amp; `код` &#x27;кавычки&#x27;" in page
    assert page.count("&lt;script&gt;alert(1)") >= 5  # имя документа, требование, цитата, проблема, вопрос
    _assert_anchors(page)


def test_no_external_resources_and_urls_stay_text(doc):
    result = _result(doc)
    url = "https://example.com/api?a=1&b=2"
    result.requirements[0].quote = f"Адрес сервиса {url} задаёт <архитектор>."
    page = render_html(result)
    for bad in ("<link", "<img", "<iframe", "src=", "@import", "url(", "http-equiv=\"refresh\""):
        assert bad not in page, bad
    assert all(href.startswith("#") for href in _hrefs(page))
    assert "https://example.com/api?a=1&amp;b=2" in page and 'href="https' not in page
    assert "&lt;архитектор&gt;" in page
    _assert_anchors(page)


def test_first_screen_numbers_match_markdown(doc):
    result = _result(doc)
    text, page = render(result), render_html(result)
    m = re.search(r"Требований: (\d+), с дефектами: (\d+)\. Замечаний: CRITICAL (\d+), MAJOR (\d+), MINOR (\d+)\. "
                  r"Вопросов автору: (\d+)\.", text)
    tiles = dict(re.findall(r'data-k="([\w-]+)"><b>(\d+)</b>', page))
    assert [tiles[k] for k in ("reqs", "with-defects", "critical", "major", "minor", "questions")] == list(m.groups())
    decision = re.search(r"\*\*Вердикт: (.+?)\.\*\*", text).group(1)
    assert f'<strong class="decision">{decision}</strong>' in page
    # Блокеры и главные вопросы первого экрана те же и в том же порядке.
    first_md = text.split("## 1. Паспорт")[0]
    first_html = page.split('id="passport"')[0]
    assert re.findall(r"\[([SDQ]-\d+)\]\(#", first_md) == re.findall(r'class="(?:bid[^"]*|qid)">([SDQ]-\d+)<', first_html)


def test_every_finding_and_question_from_markdown_is_in_html(doc):
    result = _result(doc)
    text, page = render(result), render_html(result)
    md_targets = set(re.findall(r'<a id="([^"]+)"></a>', text))
    assert md_targets <= set(_ids(page))
    for f in result.findings:
        if f.problem in text:
            assert report_html.esc(f.problem) in page


def test_incomplete_report_renders(doc):
    class FatalReview(FakeLLM):
        def complete_json(self, step, system, user, schema, kind=""):
            if schema is BatchReviewOut:
                raise LLMFatal("суточная квота исчерпана", kind="quota")
            return super().complete_json(step, system, user, schema, kind)

    result = _result(doc, FatalReview())
    page = render_html(result)
    assert "Отчёт неполный." in page and "суточная квота исчерпана" in page
    assert page.index("Отчёт неполный") < page.index('class="decision"')
    assert "Требование не проверено" in page
    _assert_anchors(page)


def test_document_without_requirements_renders(doc):
    class NoRequirements(FakeLLM):
        def complete_json(self, step, system, user, schema, kind=""):
            if schema is SegmentationOut:
                self.stats.calls += 1
                return SegmentationOut.model_validate({"requirements": [], "skipped": [
                    {"line_start": 1, "line_end": 14, "reason": "intro"}]})
            return super().complete_json(step, system, user, schema, kind)

    result = _result(doc, NoRequirements())
    assert not result.requirements
    page = render_html(result)
    assert '<strong class="decision">Не вынесен</strong>' in page
    assert 'data-k="reqs"><b>0</b>' in page
    _assert_anchors(page)


def test_old_json_without_new_fields_renders():
    """report.json старой версии агента: только обязательные поля, новых счётчиков и полей замечаний нет."""
    data = {
        "document_name": "old.md", "document_format": "md", "document_lines": 3, "document_sha256": "0" * 64,
        "started_at": "2026-11-20 10:00:00", "provider": "gemini", "model": "old-model", "agent_version": "0.0.1",
        "requirements": [{"id": "REQ-01", "source_id": None, "section": "Требования", "line_start": 2,
                          "line_end": 2, "kind": "functional", "summary": "Поиск", "quote": "Поиск работает быстро."}],
        "findings": [{"id": "D-01", "scope": "requirement", "criterion": "VERIFIABLE", "severity": "MAJOR",
                      "req_ids": ["REQ-01"], "problem": "Нет числа.", "recommendation": "Задать время.",
                      "question_id": "Q-09", "status": "confirmed"}],
        "verdict": {"decision": "Условно допускается", "ready_for_development": "Да, с оговорками",
                    "ready_for_testing": "Да, с оговорками", "rule": "правило", "rationale": "есть MAJOR"},
        "grounding": {}, "llm": {},
    }
    result = RunResult.model_validate_json(json.dumps(data))
    page = render_html(result)
    assert '<strong class="decision">Условно допускается</strong>' in page and "Нет числа." in page
    assert '<span class="dead">Q-09</span>' in page  # вопроса в старом json нет: ссылка стала текстом
    _assert_anchors(page)


def test_template_has_no_long_or_short_dashes(doc):
    source = Path(report_html.__file__).read_text(encoding="utf-8")
    assert "—" not in source and "–" not in source
    page = render_html(_result(doc))
    assert "—" not in page and "–" not in page


# ---------- командная строка ----------


def test_cli_writes_html_and_names_it_in_step_9(workdir, monkeypatch, capsys):  # noqa: F811
    use(monkeypatch, FakeLLM())
    assert run() == cli.EXIT_OK
    page = (workdir / "out" / "report.html").read_text(encoding="utf-8")
    assert page.startswith("<!doctype html>")
    report = (workdir / "out" / "report.md").read_text(encoding="utf-8")
    assert "| 9 | Отчёт | выполнен |" in report
    assert "записаны: report.md, report.questions.md, report.json, report.html" in report
    assert "записаны: report.md, report.questions.md, report.json, report.html" in page
    assert "out/report.html" in capsys.readouterr().out


def test_cli_no_html_skips_file(workdir, monkeypatch, capsys):  # noqa: F811
    use(monkeypatch, FakeLLM())
    assert run("--no-html", "--no-json") == cli.EXIT_OK
    out = workdir / "out"
    assert not (out / "report.html").exists() and not (out / "report.json").exists()
    assert "записаны: report.md, report.questions.md |" in (out / "report.md").read_text(encoding="utf-8")
    assert "report.html" not in capsys.readouterr().out


def test_cli_html_over_input_is_refused(workdir, monkeypatch, capsys):  # noqa: F811
    """Документ лежит там, куда лёг бы report.html: без --no-html прогон не начинается, документ цел."""
    llm = use(monkeypatch, FakeLLM())
    (workdir / "out").mkdir()
    source = workdir / "out" / "report.html"
    source.write_text((workdir / "spec.md").read_text(encoding="utf-8"), encoding="utf-8")
    assert cli.main(["-i", "out/report.html", "-o", "out/report.md", "-q"]) == cli.EXIT_INPUT
    assert "поверх проверяемого документа" in capsys.readouterr().err and llm.steps == []
    # С --no-html report.html не пишется, значит, и не затирает документ: прогон идёт.
    assert cli.main(["-i", "out/report.html", "-o", "out/report.md", "-q", "--no-html"]) == cli.EXIT_OK
    assert source.read_text(encoding="utf-8").startswith("# Библиотечный каталог")


def test_unreadable_document_removes_stale_html_but_not_the_input(workdir, monkeypatch):  # noqa: F811
    use(monkeypatch, FakeLLM())
    out = workdir / "out"
    out.mkdir()
    for name in ("report.html", "report.json", "report.questions.md"):
        (out / name).write_text("старый прогон", encoding="utf-8")
    (workdir / "broken.pdf").write_bytes(b"%PDF-1.4 broken")
    assert cli.main(["-i", "broken.pdf", "-o", "out/report.md", "-q", "--no-html", "--no-json"]) == cli.EXIT_INPUT
    assert "Не вынесен" in (out / "report.md").read_text(encoding="utf-8")
    assert not any((out / n).exists() for n in ("report.html", "report.json", "report.questions.md"))
    # Пустой документ с именем report.html и --no-html: отчёт с причиной пишется, сам документ не удаляется.
    (out / "report.html").write_text("  \n", encoding="utf-8")
    assert cli.main(["-i", "out/report.html", "-o", "out/report.md", "-q", "--no-html"]) == cli.EXIT_INPUT
    assert (out / "report.html").exists() and "Файл пуст" in (out / "report.md").read_text(encoding="utf-8")
