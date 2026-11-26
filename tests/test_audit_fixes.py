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


# ---------- шаги конвейера (С-3, С-4, Н-3) ----------

import inspect  # noqa: E402

from reqask.llm import LLMError  # noqa: E402
from reqask.pipeline import NO_REQUIREMENTS, STEP_NAMES, Pipeline, _with_trailing_dash, tidy  # noqa: E402
from reqask.schemas import CriticOut, FinalOut, Finding, Question, SegmentationOut  # noqa: E402


class _Seg(FakeLLM):
    """Нарезка с заданным ответом, остальное как у FakeLLM."""

    def __init__(self, seg: dict | Exception, critic: Exception | None = None):
        super().__init__()
        self.seg, self.critic_error = seg, critic

    def complete_json(self, step, system, user, schema, kind=""):
        if schema is SegmentationOut:
            self.steps.append(step)
            self.stats.calls += 1
            if isinstance(self.seg, Exception):
                raise self.seg
            return SegmentationOut.model_validate(self.seg)
        if schema is CriticOut and self.critic_error:
            self.steps.append(step)
            raise self.critic_error
        return super().complete_json(step, system, user, schema, kind)


def _settings():
    from test_core import SETTINGS
    return SETTINGS


def test_steps_numbered_as_in_log_and_decide_has_no_dead_parameter(doc):
    assert list(inspect.signature(Pipeline.decide).parameters) == ["findings"]
    result = Pipeline(FakeLLM(), _settings()).run(doc, "test")
    names = {s.number: s.name for s in result.steps}
    assert names["6"] == STEP_NAMES["6"] and "свёртка" in names["6"]
    assert [s.number for s in result.steps] == ["0", "3", "4", "5", "6", "7", "8"]
    doc_text = inspect.getmodule(Pipeline).__doc__
    for number in ("0.", "3.", "4.", "5.", "6.", "7.", "8.", "9."):
        assert f"\n{number} " in doc_text


_ONLY_SKIPPED = {"requirements": [], "skipped": [{"line_start": 1, "line_end": 14, "reason": "intro"}]}
_OFFICE = "# Наш офис\n\nОфис открыт с девяти утра.\nНа кухне есть кофе.\nПо пятницам пицца.\n"


@pytest.fixture
def office(tmp_path):
    path = tmp_path / "office.md"
    path.write_text(_OFFICE, encoding="utf-8")
    return load_document(path)


def test_document_without_requirements_is_not_a_failure(office):
    pipe = Pipeline(_Seg(_ONLY_SKIPPED), _settings())
    result = pipe.run(office, "test")
    assert result.failed_steps == [] and not result.requirements
    status = {s.number: s.status for s in result.steps}
    assert status["3"] == "ok"
    assert all(status[n] == "skipped" for n in ("4", "5", "6", "7", "8"))
    v = result.verdict
    assert v.partial_reason == NO_REQUIREMENTS and v.rationale.startswith(NO_REQUIREMENTS)
    assert v.decision == "Не вынесен" and v.ready_for_testing == "Не определена" and v.partial
    assert cli.is_incomplete(result)  # код 3 остаётся


def test_segmentation_failure_without_requirements_stays_failed(doc):
    result = Pipeline(_Seg(LLMError("битый ответ")), _settings()).run(doc, "test")
    status = {s.number: s.status for s in result.steps}
    assert status["3"] == "failed" and all(status[n] == "failed" for n in ("4", "5", "6", "7", "8"))
    assert result.verdict.partial_reason != NO_REQUIREMENTS


def test_no_requirements_cli_code_3_with_own_message(workdir, monkeypatch, capsys):
    (workdir / "spec.md").write_text(_OFFICE, encoding="utf-8")
    use(monkeypatch, _Seg(_ONLY_SKIPPED))
    assert run() == cli.EXIT_PARTIAL
    assert "Требования не найдены" in capsys.readouterr().err


def test_conclude_without_active_findings_does_not_call_model(doc):
    llm = FakeLLM()
    pipe = Pipeline(llm, _settings())
    gone = [Finding(id="D-01", scope="requirement", criterion="COMPLETE", severity="CRITICAL", problem="п",
                    recommendation="р", req_ids=["REQ-01"], status="dropped", question="Что?")]
    verdict, questions = pipe.conclude(doc, [], gone)
    assert "итог" not in llm.steps and questions == []
    assert verdict.decision == "Допускается" and "сняты критиком" in verdict.rationale
    assert not any(s.startswith("итог") for s in pipe.failed_steps)


def test_critic_failure_says_verdict_without_critic(doc):
    result = Pipeline(_Seg(FakeLLM().complete_json("нарезка", "", "", SegmentationOut).model_dump(),
                           critic=LLMError("сбой")), _settings()).run(doc, "test")
    assert any("без перепроверки критиком" in s for s in result.failed_steps)
    assert {s.number: s.status for s in result.steps}["7"] == "failed"


# ---------- требования с идентификатором вне нарезки ----------


def test_given_document_ids_change_nothing(doc):
    result = Pipeline(FakeLLM(), _settings()).run(doc, "test")
    assert result.quality.ids_added == [] and result.quality.ids_missing == []
    assert [(r.id, r.line_start, r.line_end) for r in result.requirements] == [
        ("REQ-01", 4, 4), ("REQ-02", 5, 5), ("REQ-03", 9, 11)]


def test_requirement_with_id_lost_by_segmentation_is_added_by_code(doc):
    seg = {"requirements": [
        {"line_start": 4, "line_end": 4, "source_id": "FR-1", "section": "Требования", "kind": "functional",
         "summary": "Быстрый поиск"},
        {"line_start": 9, "line_end": 11, "source_id": None, "section": "Данные", "kind": "data", "summary": "Поле"},
    ], "skipped": [{"line_start": 5, "line_end": 5, "reason": "other"}, {"line_start": 13, "line_end": 14,
                                                                       "reason": "template"}]}
    pipe = Pipeline(_Seg(seg), _settings())
    result = pipe.run(doc, "test")
    assert result.quality.ids_added == ["FR-2"] and result.quality.ids_missing == []
    added = next(r for r in result.requirements if r.source_id == "FR-2")
    assert (added.id, added.line_start, added.line_end, added.section) == ("REQ-02", 5, 5, "Требования")
    assert [r.id for r in result.requirements] == ["REQ-01", "REQ-02", "REQ-03"]
    assert all(not (s.line_start <= 5 <= s.line_end) for s in result.skipped_lines)
    step3 = next(s for s in result.steps if s.number == "3")
    assert "добавлено кодом по идентификаторам: FR-2" in step3.summary


def test_lost_id_stops_at_next_id_heading_or_empty_line(tmp_path):
    from reqask.loader import load_document

    path = tmp_path / "spec.md"
    path.write_text("# Спецификация\n\nФТ-1. Система хранит заказы.\nФТ-2. Система шлёт письмо.\n"
                    "Письмо уходит в течение TBD минут.\n\nФТ-3. Система пишет журнал.\n## Прочее\n", encoding="utf-8")
    spec = load_document(path)
    seg = {"requirements": [{"line_start": 3, "line_end": 3, "source_id": "ФТ-1", "section": "", "kind": "functional",
                             "summary": "Заказы"}], "skipped": []}
    pipe = Pipeline(_Seg(seg), _settings())
    reqs = pipe.segment(spec)
    assert [(r.source_id, r.line_start, r.line_end) for r in reqs] == [("ФТ-1", 3, 3), ("ФТ-2", 4, 5), ("ФТ-3", 7, 7)]
    assert pipe.quality.ids_missing == []


def test_failed_segmentation_is_not_masked_by_id_recovery(doc):
    result = Pipeline(_Seg(LLMError("битый ответ")), _settings()).run(doc, "test")
    assert result.requirements == [] and result.quality.ids_added == []


# ---------- порядок сводных вопросов ----------


def test_questions_order_contradiction_then_critical_then_weight():
    def f(fid, scope, severity, kind="defect"):
        return Finding(id=fid, scope=scope, kind=kind, criterion="COMPLETE", severity=severity, problem="п",
                       recommendation="р", req_ids=["REQ-01"])

    findings = [f("D-01", "requirement", "MAJOR"), f("D-02", "requirement", "MAJOR"), f("D-03", "requirement", "MAJOR"),
                f("D-04", "requirement", "CRITICAL"), f("S-01", "set", "CRITICAL", "gap"),
                f("S-02", "set", "CRITICAL", "contradiction"), f("S-03", "set", "MAJOR")]

    def q(*ids, priority):
        return Question(id="", text="?", addressee="analyst", blocks="б", finding_ids=list(ids), priority=priority)

    qs = [q("D-01", "D-02", "D-03", priority=6.25), q("D-04", priority=5.25), q("S-01", priority=5.25),
          q("S-02", priority=5.25), q("S-03", priority=2.25)]
    out = Pipeline._number_questions(qs, findings)
    assert [x.finding_ids[0] for x in out] == ["S-02", "S-01", "D-04", "D-01", "S-03"]
    assert [x.id for x in out] == ["Q-01", "Q-02", "Q-03", "Q-04", "Q-05"]


# ---------- tidy не меняет текст документа ----------


def test_tidy_keeps_document_dashes():
    assert tidy("Через документ «Уведомление по карте — REST API» — это главный") == \
        "Через документ «Уведомление по карте — REST API», это главный"
    assert tidy("| **Swagger** | — |") == "| **Swagger** | — |"
    assert tidy("Поле:\n—\nдальше") == "Поле:\n—\nдальше"
    assert tidy("Вызов `a — b` — пример") == "Вызов `a — b`, пример"
    assert tidy("```\nx — y\n```\nтекст — тут") == "```\nx — y\n```\nтекст, тут"
    assert tidy("строки 1–64 — диапазон") == "строки 1-64, диапазон"


def test_quote_keeps_trailing_dash_of_empty_value():
    line = "| **Request URL** | Dev: `/alerts/saveLimit` . Prod: — |"
    assert _with_trailing_dash("Dev: `/alerts/saveLimit` . Prod:", line) == "Dev: `/alerts/saveLimit` . Prod: —"
    assert _with_trailing_dash("Dev: `/alerts/saveLimit`", line) == "Dev: `/alerts/saveLimit`"
    assert _with_trailing_dash("Prod: —", line) == "Prod: —"
