"""Правки по ревью кода 27.11 (audit3.md, раздел «Ревью кода», пункты 1-14)."""

from pathlib import Path

import pytest

from reqask import cli
from reqask.schemas import BatchReviewOut, SegmentationOut

from test_cli import FatalAt, run, use, workdir  # noqa: F401  фикстура workdir нужна тестам ниже
from test_core import FakeLLM, doc  # noqa: F401


# ---------- 1. фатальная ошибка до первого ответа не трогает прежний отчёт ----------


OLD_FILES = {
    "report.md": "# Вчерашний отчёт\n",
    "report.questions.md": "# Вчерашние вопросы\n",
    "report.json": '{"old": true}\n',
}


@pytest.mark.parametrize("kind", ["quota", "rate", "auth", "model"])
def test_fatal_before_first_answer_keeps_old_report(workdir, monkeypatch, capsys, kind):
    out = workdir / "out"
    out.mkdir()
    for name, text in OLD_FILES.items():
        (out / name).write_bytes(text.encode("utf-8"))
    use(monkeypatch, FatalAt(SegmentationOut, kind))
    assert run() == cli.EXIT_NO_MODEL
    for name, text in OLD_FILES.items():
        assert (out / name).read_bytes() == text.encode("utf-8")
    err = capsys.readouterr().err
    assert "отчёт не записан" in err and "суточная квота исчерпана" in err


def test_fatal_after_segmentation_still_gives_partial_report(workdir, monkeypatch):
    """Нарезка прошла, дальше квота: отчёт неполный, код 3, как раньше."""
    use(monkeypatch, FatalAt(BatchReviewOut, "quota"))
    assert run() == cli.EXIT_PARTIAL
    assert "Отчёт неполный" in (workdir / "out" / "report.md").read_text(encoding="utf-8")


# ---------- 2. сетевые сбои: порция не делится, три подряд останавливают прогон ----------


import httpx2  # noqa: E402  транспорт SDK openai 3.x
from openai import APIConnectionError  # noqa: E402
from openai.types.chat import ChatCompletion  # noqa: E402

from reqask.llm import LLMClient, LLMError, LLMFatal, LLMNetworkError, LLMTruncated  # noqa: E402
from reqask.pipeline import Pipeline  # noqa: E402

from test_core import SETTINGS  # noqa: E402
from test_llm import ONE, OneOut, client_with, completion, error  # noqa: E402,F401


class _Batches(FakeLLM):
    """Первая порция проверки падает заданной ошибкой, остальные вызовы отвечают как обычно."""

    def __init__(self, exc):
        super().__init__()
        self.exc, self.review_calls = exc, 0

    def complete_json(self, step, system, user, schema, kind="", **opts):
        if schema is BatchReviewOut:
            self.review_calls += 1
            if self.review_calls == 1:
                self.steps.append(step)
                raise self.exc
        return super().complete_json(step, system, user, schema, kind)


def test_truncated_batch_is_split(doc):
    llm = _Batches(LLMTruncated("[проверка] ответ обрезан по лимиту длины"))
    result = Pipeline(llm, SETTINGS).run(doc, "test")
    assert llm.review_calls == 3  # порция из трёх требований, затем две половины
    assert result.unreviewed == []


def test_network_failure_does_not_split_batch(doc):
    llm = _Batches(LLMNetworkError("[проверка] модель не ответила за 5 повторов: Connection error"))
    result = Pipeline(llm, SETTINGS).run(doc, "test")
    assert llm.review_calls == 1  # порция не делилась
    assert result.unreviewed == ["REQ-01", "REQ-02", "REQ-03"]
    assert result.fatal is None and any(s.startswith("набор") for s in llm.steps)  # прогон идёт дальше


def _content_for(schema, fake=FakeLLM()):
    return fake.complete_json("нарезка", "", "", schema).model_dump_json()


def test_three_network_failures_in_a_row_stop_model_steps(doc):
    """Настоящий клиент: нарезка отвечает, каждая порция проверки кончается обрывом связи."""
    settings = SETTINGS.with_overrides(batch_size=1)
    client = LLMClient(settings)
    client._sleep = lambda _wait: None
    sent: list[str] = []

    def request(kwargs):
        if not sent:  # первый вызов прогона это нарезка
            sent.append("нарезка")
            return ChatCompletion.model_validate(completion(_content_for(SegmentationOut)))
        sent.append("проверка")
        raise APIConnectionError(request=httpx2.Request("POST", "http://127.0.0.1:9/v1/chat/completions"))

    client._request = request
    result = Pipeline(client, settings).run(doc, "test")
    assert sent == ["нарезка", "проверка", "проверка", "проверка"]  # max_retries=0: один запрос на порцию
    assert result.fatal and "3 вызова подряд" in result.fatal
    assert result.unreviewed == ["REQ-01", "REQ-02", "REQ-03"]
    assert any("пропущено после фатальной ошибки" in s for s in result.failed_steps)


def test_network_counter_resets_on_answer_and_is_fatal_before_first_answer(client_with):
    # Провайдер не ответил ни разу: первый же сетевой сбой фатальный.
    client, sent, _ = client_with(lambda b, n: (503, error(503, "overloaded")), max_retries=1)
    with pytest.raises(LLMFatal) as info:
        client.complete_json("шаг", "s", "u", OneOut, kind="review")
    assert info.value.kind == "rate" and "ни разу" in str(info.value) and len(sent) == 2

    # Ответ был: два сбоя подряд это ошибки шага, удачный ответ обнуляет счётчик, третий подряд фатальный.
    plan = iter(["ok", "down", "down", "ok", "down", "down", "down"])
    client, sent, _ = client_with(
        lambda b, n: (200, completion(ONE)) if next(plan) == "ok" else (503, error(503, "overloaded")), max_retries=0)
    got = []
    for _ in range(6):
        try:
            client.complete_json("шаг", "s", "u", OneOut, kind="review", use_cache=False)
            got.append("ok")
        except LLMFatal:
            got.append("fatal")
        except LLMNetworkError:
            got.append("net")
    assert got == ["ok", "net", "net", "ok", "net", "net"]
    with pytest.raises(LLMFatal):
        client.complete_json("шаг", "s", "u", OneOut, kind="review", use_cache=False)
    assert issubclass(LLMNetworkError, LLMError)


# ---------- 5. отчёт поверх документа ----------


@pytest.mark.parametrize("output", ["spec.md", "./spec.md", "sub/../spec.md"])
def test_output_equal_to_input_is_refused(workdir, monkeypatch, capsys, output):
    llm = use(monkeypatch, FakeLLM())
    before = (workdir / "spec.md").read_bytes()
    assert cli.main(["-i", "spec.md", "-o", output, "-q"]) == cli.EXIT_INPUT
    assert (workdir / "spec.md").read_bytes() == before and llm.steps == []
    assert "поверх проверяемого документа" in capsys.readouterr().err


def test_questions_file_equal_to_input_is_refused(workdir, monkeypatch):
    (workdir / "report.questions.md").write_text("FR-1. Система должна работать.\n", encoding="utf-8")
    use(monkeypatch, FakeLLM())
    assert cli.main(["-i", "report.questions.md", "-o", "report.md", "-q"]) == cli.EXIT_INPUT
    assert (workdir / "report.questions.md").read_text(encoding="utf-8").startswith("FR-1.")


def test_unreadable_input_does_not_overwrite_itself(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "broken.md").write_bytes(b"\x00\x01")
    assert cli.main(["-i", "broken.md", "-o", "broken.md", "-q"]) == cli.EXIT_INPUT
    assert (tmp_path / "broken.md").read_bytes() == b"\x00\x01"


# ---------- 6. нечитаемый документ: старые соседние файлы удаляются ----------


def test_unreadable_document_removes_stale_questions_and_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    for name, text in OLD_FILES.items():
        (out / name).write_text(text, encoding="utf-8")
    (tmp_path / "broken.pdf").write_bytes(b"%PDF-1.4 broken")
    assert cli.main(["-i", "broken.pdf", "-o", "out/report.md", "-q"]) == cli.EXIT_INPUT
    assert "**Вердикт: Не вынесен.**" in (out / "report.md").read_text(encoding="utf-8")
    assert not (out / "report.questions.md").exists() and not (out / "report.json").exists()


# ---------- 10. журнал шагов без несуществующих шагов 1, 2, 5в ----------


from dataclasses import replace  # noqa: E402

from reqask.report import render  # noqa: E402
from reqask.schemas import StepStat  # noqa: E402


def test_journal_has_no_retired_steps_and_flags_are_named(doc):
    logs: list[str] = []
    result = Pipeline(FakeLLM(), replace(SETTINGS, critic=False, edge=False), logs.append).run(doc, "test")
    assert [s.number for s in result.steps] == ["0", "3", "4", "5", "6", "7", "8"]
    assert not any("не включён" in m or "желательная" in m for m in logs)
    assert "Шаг 7. Критик: выключен (--no-critic или REQASK_CRITIC=0)" in logs
    steps = {s.number: s for s in result.steps}
    assert "--no-edge" in steps["5"].name
    report = render(result)
    journal = report[report.index("Журнал шагов"):]
    assert "| 7 | Критик | пропущен |" in journal and "выключен (--no-critic" in journal
    assert "| Критик | выключен (--no-critic или REQASK_CRITIC=0) |" in report


def test_old_json_with_retired_steps_renders_without_them(doc):
    result = Pipeline(FakeLLM(), SETTINGS).run(doc, "test")
    result.steps[1:1] = [StepStat(number="1", name="Структурные проверки кодом", status="skipped", reason="желательная часть"),
                         StepStat(number="2", name="Контекст документа", status="skipped", reason="желательная часть")]
    result.steps.append(StepStat(number="5в", name="Чек-лист ревью из документа", status="skipped", reason="желательная часть"))
    report = render(result)
    assert "желательная часть" not in report and "Чек-лист ревью" not in report and "не включён" not in report
