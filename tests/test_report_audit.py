"""Правки отчёта по аудиту сдачи: счётчик дефектов, дубль блокеров, сокращения, слияния, паспорт, вердикт."""

import pytest

from reqask.report import _first_sentence, _gist, render, render_questions
from reqask.schemas import (
    CriterionCheck, Evidence, Finding, GroundingStats, LLMStats, Question, Requirement, RunResult, StepStat, Verdict,
)


def _req(n: int, line: int, quote: str = "Система сохраняет порог.") -> Requirement:
    return Requirement(id=f"REQ-0{n}", source_id=None, section="Раздел", line_start=line, line_end=line,
                       kind="functional", summary="суть", quote=quote)


def _f(fid: str, scope: str, lines: list[int], req_ids: list[str], severity: str = "MAJOR", **kw) -> Finding:
    return Finding(id=fid, scope=scope, criterion="COMPLETE" if scope == "requirement" else "SET_COMPLETE",
                   severity=severity, req_ids=req_ids, problem=kw.pop("problem", f"Проблема {fid}."),
                   recommendation="Исправить.", evidence=[Evidence(quote=f"цитата {n}", line=n) for n in lines], **kw)


def _result(findings: list[Finding], requirements: list[Requirement] | None = None, **kw) -> RunResult:
    reqs = requirements or [_req(1, 10), _req(2, 20), _req(3, 30), _req(4, 40)]
    blockers = [f.id for f in sorted((f for f in findings if f.severity == "CRITICAL" and f.status in ("confirmed", "unreviewed")),
                                     key=lambda f: f.scope != "set")]
    verdict = kw.pop("verdict", None) or Verdict(
        decision="Не рекомендуется начинать" if blockers else "Условно допускается", ready_for_development="Нет",
        ready_for_testing="Нет", rule="правило", rationale="обоснование", blockers=blockers, critic_done=True)
    return RunResult(
        document_name="doc.md", document_format="md", document_lines=50, document_sha256="0" * 64,
        started_at="2026-11-27 10:00:00 +0500", provider="custom", model="fake", agent_version="test",
        requirements=reqs, findings=findings, verdict=verdict, grounding=GroundingStats(),
        llm=kw.pop("llm", None) or LLMStats(), **kw,
    )


def _row(report: str, name: str) -> str:
    return next(line for line in report.splitlines() if line.startswith(f"| {name} |"))


def test_merged_defect_counts_as_defect_in_summary_and_first_screen():
    """Требование, чей дефект критик слил в замечание по набору, считается с дефектом (сводка сходится с разделом 3)."""
    findings = [
        _f("D-01", "requirement", [10], ["REQ-01"], status="confirmed"),
        _f("D-02", "requirement", [20], ["REQ-02"], status="merged", merged_into="S-01", critic_reason="то же"),
        _f("D-03", "requirement", [30], ["REQ-03"], status="dropped", critic_reason="ложное"),
        _f("S-01", "set", [20, 40], ["REQ-02", "REQ-04"], status="confirmed"),
    ]
    report = render(_result(findings))
    assert "- Требований: 4, с дефектами: 2." in report
    assert _row(report, "с дефектами") == "| с дефектами | 2 |" and _row(report, "без своих замечаний") == "| без своих замечаний | 2 |"
    # Слитое в общее замечание стоит в своей группе, снятое критиком только пометка.
    moved = report[report.index("**Дефект описан в общем замечании"):]
    assert moved.startswith("**Дефект описан в общем замечании, на которое ссылается строка (1):**")
    assert "**REQ-02 · строка 20 · Раздел**: слито критиком: [D-02](#d-02) в [S-01](#s-01)." in report
    assert "**Замечаний не найдено, есть пометки к оценкам (1):**" in report and "снято критиком: [D-03](#d-03)" in report
    # Сводка раскладывает «без своих замечаний» на те же группы, что раздел 3: 2 = 1 затронуто набором + 1 с пометками.
    assert _row(report, "из них затронуты замечаниями по набору") == "| из них затронуты замечаниями по набору | 1 |"
    assert _row(report, "из них с пометками к оценкам") == "| из них с пометками к оценкам | 1 |"


def test_requirement_blocker_inside_set_blocker_is_one_row():
    """D и S закрывает один вопрос, строки D внутри строк S: на первом экране и в сводке одна строка."""
    findings = [
        _f("S-01", "set", [10, 20], ["REQ-01", "REQ-02"], "CRITICAL", title="Метод чтения не описан",
           question_id="Q-01", status="confirmed"),
        _f("D-01", "requirement", [20], ["REQ-02"], "CRITICAL", question_id="Q-01", status="confirmed"),
        # Другой вопрос: остаётся отдельной строкой.
        _f("D-02", "requirement", [30], ["REQ-03"], "CRITICAL", question_id="Q-02", status="confirmed"),
        # Тот же вопрос, но строка вне цитат S: отдельной строкой.
        _f("D-03", "requirement", [40], ["REQ-04"], "CRITICAL", question_id="Q-01", status="confirmed"),
    ]
    result = _result(findings)
    assert result.verdict.blockers == ["S-01", "D-01", "D-02", "D-03"]
    report = render(result)
    first = report[: report.index("## 1. Паспорт")]
    assert "- [S-01](#s-01) · [REQ-01](#req-01), [REQ-02](#req-02) · Метод чтения не описан (вместе с [D-01](#d-01))" in first
    assert "- [D-01](#d-01)" not in first and "- [D-02](#d-02)" in first and "- [D-03](#d-03)" in first
    summary = report[report.index("### Блокеры"): report.index("## 6. Вердикт")]
    assert "[D-01](#d-01) ·" not in summary and "(вместе с [D-01](#d-01))" in summary
    assert sum(1 for line in summary.splitlines() if line[:1].isdigit()) == 3
    # Счётчик CRITICAL прежний: четыре замечания.
    assert _row(report, "CRITICAL (критичный)") == "| CRITICAL (критичный) | 4 |"


@pytest.mark.parametrize("text, expected", [
    ("Статус 400 описан иначе, но логика п. 5 (строка 121) тоже про сумму. Второе.",
     "Статус 400 описан иначе, но логика п. 5 (строка 121) тоже про сумму."),
    ("Код не задан, т. е. тест не написать. Дальше.", "Код не задан, т. е. тест не написать."),
    ("Шаги и т. д. Не описаны.", "Шаги и т. д. Не описаны."),
    ("Пример есть, напр. Код 404 в разделе. Дальше.", "Пример есть, напр. Код 404 в разделе."),
    ("Автор И. И. Иванов не указан. Дальше.", "Автор И. И. Иванов не указан."),
    ("См. стр. 3 документа. Дальше.", "См. стр. 3 документа."),
    ("Значение вне 0 и 1. Шаг 5 молчит.", "Значение вне 0 и 1."),
    ("Одно предложение без точки в конце", "Одно предложение без точки в конце"),
])
def test_first_sentence_does_not_stop_at_abbreviations(text, expected):
    assert _first_sentence(text, 200) == expected


def test_gist_in_appendix_keeps_abbreviation():
    f = _f("D-01", "requirement", [10], ["REQ-01"], problem="Статус описан иначе, но логика п. 5.2 про сумму. Второе.")
    assert _gist(f, 200) == "Статус описан иначе, но логика п. 5.2 про сумму."


def test_merge_shown_once_in_requirement_block():
    """Слитое в замечание этого же блока видно только как «Критик слил сюда», без второй строки «Слито критиком»."""
    findings = [
        _f("D-01", "requirement", [10], ["REQ-01"], status="confirmed"),
        _f("D-02", "requirement", [10], ["REQ-01"], status="merged", merged_into="D-01", critic_reason="то же"),
        _f("D-03", "requirement", [10], ["REQ-01"], status="merged", merged_into="S-01", critic_reason="общее"),
        _f("S-01", "set", [10, 20], ["REQ-01", "REQ-02"], status="confirmed"),
    ]
    report = render(_result(findings))
    block = report[report.index('### <a id="req-01"></a>'): report.index("## 4.")]
    assert "- Критик слил сюда: [D-02](#d-02)" in block
    assert "[D-02](#d-02) в [D-01](#d-01)" not in block
    # Слитое в замечание другого блока ссылку сохраняет.
    assert "Слито критиком: [D-03](#d-03) в [S-01](#s-01)." in block


def test_passport_explains_coverage_and_hides_skipped_steps():
    steps = [StepStat(number="0", name="Чтение", status="ok"),
             StepStat(number="7", name="Критик", status="skipped", reason="выключен (--no-critic или REQASK_CRITIC=0)")]
    result = _result([], steps=steps)
    result.quality.content_lines, result.quality.in_requirements, result.quality.skipped_by_model = 10, 4, 6
    report = render(result)
    assert _row(report, "Шаги") == "| Шаги | выполнено 1, частично 0, не выполнено 0 |"
    assert "не включено" not in _row(report, "Шаги")
    assert "отмечены как не требования 6 (заголовки, вводный текст, шаблоны, см. раздел 2)" in _row(report, "Покрытие нарезкой")
    assert "отброшено без опоры на текст 0 (ни найденной цитаты, ни ссылки на требование или раздел" in _row(report, "Цитаты")
    # В журнале шагов выключенный флагом шаг остаётся с причиной.
    assert "| 7 | Критик | пропущен | 0 | 0.0 | выключен (--no-critic или REQASK_CRITIC=0) |" in report


@pytest.mark.parametrize("calls, hits, mode", [
    (0, 5, "только из кэша"),
    (3, 5, "живой прогон, часть ответов из кэша"),
    (3, 0, "живой прогон"),
])
def test_passport_mode(calls, hits, mode):
    """llm.calls считает только живые вызовы, cache_hits идёт отдельно."""
    report = render(_result([], llm=LLMStats(calls=calls, cache_hits=hits)))
    assert _row(report, "Режим") == f"| Режим | {mode}; формат ответа JSON: не известен |"


def _partial(reason: str, decision: str = "Не вынесен") -> Verdict:
    return Verdict(decision=decision, ready_for_development="Не определена", ready_for_testing="Не определена",
                   rule="правило", rationale=f"{reason} обоснование", partial=True, partial_reason=reason)


def test_incomplete_verdict_does_not_repeat_itself():
    """«Отчёт неполный» один раз на первом экране (в блоке), шаги не дублируются под вердиктом."""
    reason = ("Отчёт неполный: проверено требований 3 из 4. Шаги: 4 «Проверка каждого требования (порции)» (частично). "
              "Причина в начале отчёта.")
    result = _result([], verdict=_partial(reason), unreviewed=["REQ-04"], fatal="ошибка провайдера",
                     steps=[StepStat(number="4", name="Проверка каждого требования (порции)", status="degraded")])
    report = render(result)
    first = report[: report.index("## 1. Паспорт")]
    assert first.count("Отчёт неполный") == 1 and first.lower().count("отчёт неполный") == 1
    assert "**Вердикт: Не вынесен.**\nРешение не вынесено: положительное решение по неполным данным не принимается. " \
           "Проверено требований 3 из 4.\n" in first
    assert first.count("«Проверка каждого требования (порции)»") == 1
    section = report[report.index("## 6. Вердикт"): report.index("## 7.")]
    assert "отчёт неполный, а" not in section


def test_incomplete_verdict_without_requirements_reads_well():
    """Своя причина (документ без требований) стоит сама, без общей фразы про неполные данные."""
    reason = "В документе не найдено требований, проверять нечего."
    steps = [StepStat(number="3", name="Нарезка", status="ok"), StepStat(number="4", name="Проверка", status="skipped")]
    result = _result([], requirements=[_req(1, 1)], verdict=_partial(reason), steps=steps,
                     failed_steps=["нарезка: требований нет"])
    result.requirements = []
    report = render(result)
    assert "**Вердикт: Не вынесен.**\nРешение не вынесено. В документе не найдено требований, проверять нечего.\n" in report
    assert "неполным данным" not in report[: report.index("## 1. Паспорт")]
    # Старый текст причины (до правки в pipeline) тоже читается без повтора.
    old = _partial("Отчёт неполный. Шаги: 3 «Нарезка требований (5 строк)» (не выполнен); 4 «Проверка» (не выполнен).")
    result.verdict = old
    first = render(result)[:render(result).index("## 1. Паспорт")]
    assert "**Вердикт: Не вынесен.**\nРешение не вынесено: положительное решение по неполным данным не принимается.\n" in first
    assert first.lower().count("отчёт неполный") == 1


def test_question_numbers_note_and_na_noise():
    findings = [_f("D-01", "requirement", [10], ["REQ-01"], status="confirmed", question_id="Q-01"),
                _f("D-02", "requirement", [20], ["REQ-02"], status="confirmed", question_id="Q-02")]
    questions = [Question(id="Q-01", text="Первый?", addressee="architect", finding_ids=["D-01"], priority=2),
                 Question(id="Q-02", text="Второй?", addressee="business", finding_ids=["D-02"], priority=1)]
    checks = {"REQ-03": [CriterionCheck(criterion="FEASIBLE", status="na", note="Пример, к нему не применима")]}
    result = _result(findings, questions=questions, checks=checks)
    assert "номера идут по важности, поэтому внутри раздела номера не подряд" in render_questions(result)
    report = render(result)
    assert "номера идут по важности" in report[report.index("## 7."):]
    # Требование только с «не применим» стоит в общей строке без шумного пояснения.
    assert "ни по одному применимому критерию (2):**" in report and "к нему не применима" not in report


def test_quote_with_code_fence_uses_tildes():
    req = _req(1, 10, quote='**404**\n```json\n{"message":"нет"}')
    report = render(_result([_f("D-01", "requirement", [10], ["REQ-01"], status="confirmed")],
                            requirements=[req]))
    assert '~~~text\n**404**\n```json\n{"message":"нет"}\n~~~' in report and "````" not in report
