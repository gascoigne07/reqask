"""Тесты без сети: модель подменена заглушкой."""

import json
import re
from dataclasses import replace
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from pydantic import BaseModel

from reqask.config import Settings
from reqask.grounding import TextIndex, normalize
from reqask.lint import lint
from reqask.llm import LLMClient, LLMError, LLMFatal, LLMTruncated, extract_json
from reqask.loader import LoadError, load_document
from reqask.pipeline import Pipeline, make_id
from reqask import prompts
from reqask.report import render
from reqask.schemas import (
    BatchReviewOut,
    Evidence,
    Question,
    CriticOut,
    LLMStats,
    SegmentationOut,
    EdgeReviewOut,
    SetReviewOut,
    FinalOut,
    TopFix,
)

DOC = """# Библиотечный каталог

## Требования
* **FR-1.** Система должна быстро показывать результаты поиска книги.
* **FR-2.** Читатель может взять на руки не больше 5 книг.

## Данные

| Поле | Тип |
| :--- | :--- |
| `max_books` | Не больше 3 книг на читателя, integer |

## Тестирование
заполняется позже
"""

class SimpleOut(BaseModel):
    """Простая схема для тестов клиента модели."""

    rationale: str
    top_fixes: list[TopFix]


SETTINGS = Settings(provider="fake", base_url=None, api_key="x", model="fake-model", cache_dir=None, max_retries=0)


@pytest.fixture
def doc(tmp_path: Path):
    path = tmp_path / "spec.md"
    path.write_text(DOC, encoding="utf-8")
    return load_document(path)


def _defect(criterion, severity, evidence, question=None, addressee=None, line=None):
    return {"criterion": criterion, "severity": severity, "evidence": evidence, "line": line,
            "problem": "п", "impact": "и", "recommendation": "р", "question": question, "addressee": addressee}


def _set_finding(kind, criterion, severity, title, evidence, req_ids=(), question=None, section=None, addressee=None,
                 divergence="none"):
    return {"kind": kind, "criterion": criterion, "severity": severity, "title": title, "req_ids": list(req_ids),
            "section": section, "evidence": [{"quote": q, "line": None} for q in evidence], "problem": "п",
            "impact": "и", "recommendation": "р", "question": question, "addressee": addressee,
            "divergence": divergence}


def _question(ids, n_options, recommended=None, addressee=None):
    return {"text": f"Вопрос про {ids[0]}?", "addressee": addressee,
            "options": [{"answer": f"вариант {i}", "consequence": "правка"} for i in range(1, n_options + 1)],
            "recommended": recommended, "why_recommended": "так проще" if recommended else None,
            "blocks": "нельзя реализовать", "doc_says": None, "finding_ids": list(ids)}


class FakeLLM:
    """Отдаёт заранее заданные ответы по типу схемы, как это делала бы модель."""

    def __init__(self):
        self.stats = LLMStats()
        self.steps: list[str] = []
        self.users: list[str] = []

    def complete_json(self, step, system, user, schema, kind=""):
        self.steps.append(step)
        self.users.append(user)
        self.stats.calls += 1
        if schema is SegmentationOut:
            return SegmentationOut.model_validate({"requirements": [
                {"line_start": 4, "line_end": 4, "source_id": "FR-1.", "section": "Требования",
                 "kind": "nonfunctional", "summary": "Быстрый поиск"},
                {"line_start": 5, "line_end": 5, "source_id": "FR-2", "section": "Требования",
                 "kind": "data", "summary": "Число книг на руках"},
                {"line_start": 9, "line_end": 11, "source_id": None, "section": "Данные",
                 "kind": "странный", "summary": "Поле max_books"},
            ], "skipped": [{"line_start": 13, "line_end": 14, "reason": "Template"}]})
        if schema is BatchReviewOut:
            return BatchReviewOut.model_validate({"reviews": [
                {"req_id": "REQ-001", "checks": [
                    {"criterion": "verifiable", "status": "fail", "note": "нет числа"},
                    {"criterion": "COMPLETE", "status": "fail", "note": "дефект не описан"},
                    {"criterion": "NECESSARY", "status": "NA", "note": "не применим"},
                    {"criterion": "STYLE", "status": "fail", "note": "нет такого критерия"},
                    {"criterion": "SINGULAR", "status": "Pass", "note": ""},
                ], "defects": [
                    _defect("verifiable", "critical", "«быстро показывать»", "Какое время ответа, в секундах?", "Business"),
                    _defect("STYLE", "MAJOR", "быстро показывать результаты", "лишний вопрос", "qa"),
                ], "rewritten": "Система отвечает за <N секунд>."},
                {"req_id": "REQ-2", "checks": [
                    {"criterion": "UNAMBIGUOUS", "status": "pass", "note": "лишнее пояснение"},
                ], "defects": [
                    _defect("UNAMBIGUOUS", "MINOR", "такого текста в документе нет совсем"),
                ], "rewritten": None},
                {"req_id": "REQ-03", "checks": [], "defects": [], "rewritten": None},
            ]})
        if schema is SetReviewOut:
            if "согласованность" in step:
                return SetReviewOut.model_validate({
                    "analyses": [{"criterion": "SET_CONSISTENT", "status": "fail", "analysis": "Сравнил число книг."},
                                 {"criterion": "SET_COMPLETE", "status": "ok", "analysis": "чужой критерий"}],
                    "findings": [_set_finding(
                        "contradiction", "SET_CONSISTENT", "CRITICAL", "Разное число книг",
                        ["Читатель может взять на руки не больше 5 книг", "Не больше 3 книг на читателя, integer",
                         "выдуманная цитата абсолютно"],
                        req_ids=["REQ-002", "REQ-3", "REQ-999"], question="Сколько книг можно взять: 3 или 5?",
                        addressee="business",
                    )]})
            return SetReviewOut.model_validate({
                "analyses": [{"criterion": "SET_COMPLETE", "status": "partial", "analysis": "Раздел тестов пуст."}],
                "findings": [
                    _set_finding("gap", "SET_COMPLETE", "MAJOR", "Пустой раздел", ["заполняется позже"],
                                 question="Кто и когда заполнит раздел тестирования?"),
                    _set_finding("other", "SET_RANKED", "MINOR", "Без опоры", ["нет такой цитаты нигде вообще"]),
                    _set_finding("gap", "SET_COMPLETE", "MAJOR", "Нет требований к доступу", [],
                                 question="Кто может менять лимит книг?", section="Требования", addressee="security"),
                    _set_finding("gap", "SET_COMPLETE", "MAJOR", "Пробел без места", [], question="Вопрос?"),
                ]})
        if schema is EdgeReviewOut:
            # По умолчанию граничных случаев нет: остальные тесты считают замечания первых двух проходов.
            return EdgeReviewOut.model_validate({"findings": []})
        if schema is CriticOut:
            # По умолчанию критик оставляет все замечания из списка как есть.
            ids = re.findall(r"^([DS]-\d+) \|", user, re.MULTILINE)
            return CriticOut.model_validate({"decisions": [
                {"finding_id": i, "action": "keep", "severity": None, "into": None, "reason": "верно"} for i in ids]})
        if schema is FinalOut:
            return FinalOut.model_validate({"rationale": "Есть блокеры.", "top_fixes": [
                {"finding_ids": ["S-01", "X-404"], "action": "Оставить одно число."},
                {"finding_ids": ["нет"], "action": "Мимо."},
            ], "questions": [
                _question(["S-01", "D-99"], 2, recommended=1, addressee="business"),
                _question(["s-01"], 3),  # тот же набор замечаний: сливается с первым
                _question(["S-02", "S-03"], 1),  # один вариант: отброшен
                _question(["X-1"], 2),  # нет существующих замечаний: отброшен
                _question(["S-02"], 5, recommended=7),  # вариантов больше четырёх, номер рекомендации мимо
            ]})
        raise AssertionError(schema)


def test_loader_sections_and_content(doc):
    assert doc.n == 14
    assert doc.section_path(4) == "Требования"
    assert doc.is_heading(3) and not doc.is_content(3)
    assert not doc.is_content(10)  # разделитель таблицы
    assert doc.numbered(4, 4).startswith("L0004| ")


def test_loader_errors(tmp_path):
    with pytest.raises(LoadError):
        load_document(tmp_path / "missing.md")
    empty = tmp_path / "empty.md"
    empty.write_text("   \n")
    with pytest.raises(LoadError):
        load_document(empty)


def test_grounding(doc):
    index = TextIndex(doc)
    assert normalize("**FR-1.**  «Ёж»") == 'fr-1. "еж"'
    assert index.find("Читатель может взять на руки не больше 5 книг") == 5
    assert index.find("max_books | Не больше 3 книг") == 11  # разметка таблицы не мешает
    assert index.find("Система должна ... результаты поиска книги") == 4  # многоточие внутри
    assert index.find("Читатель может взять на руки не больше 5 книг", 9, 11) is None  # вне диапазона
    assert index.find("этого нет") is None
    assert index.fuzzy("Система должна быстро показывать результаты поиска книжки", 4, 4) == 4
    # Порог 0,8: общий кусок меньше 80% цитаты не засчитывается (К-06).
    assert index.fuzzy("Система обязана быстро показывать результаты поиска книги", 4, 4) is None
    # Короткая цитата сверяется по номеру строки с допуском в две строки.
    assert index.is_short("5") and index.find_short("5", 6) == 5 and index.find_short("5", 9) is None
    assert index.fuzzy("совершенно посторонний текст про погоду", 4, 4) is None


def test_lint():
    hints = lint("Система должна быстро и удобно работать и т.д.")
    assert len(hints) == 3
    assert lint("Порог от 1 000 до 1 000 000 включительно.") == []
    assert lint("Лимит: TBD") == ["«tbd»: незаполненное место"]


def test_placeholder_dictionary():
    """Словарь заглушек общий: служебные пометки ловятся, обычные слова нет."""
    from reqask.lint import placeholder_marks

    hits = {
        "version TODO: of the server": ["TODO"], "Срок: TBD, решение ???": ["TBD", "???"],
        "FIXME проверить": ["FIXME"], "To be determined later.": ["To be determined"],
        "Тариф уточняется": ["уточняется"], "Порог будет определён позже": ["будет определён"],
        "Требует уточнения у заказчика": ["Требует уточнения"], "Раздел [заполнить]": ["заполнить"],
        "Текст дописать позже": ["дописать позже"], "Цена: XXX руб.": ["XXX"],
        "Сценарии будут добавлены позже": ["будут добавлены позже"],
        "Раздел будет описан в следующей версии": ["будет описан в следующей версии"],
        "Details to be added in a future version.": ["to be added in a future version"],
    }
    for text, marks in hits.items():
        assert placeholder_marks(text) == marks, text
    for text in ("Пользователь должен заполнить форму заказа.", "Поля заполняются кассиром.",
                 "a todo list for users", "Значение уточнить нельзя без договора",
                 "Records are to be added to the log."):
        assert placeholder_marks(text) == [], text


@pytest.mark.parametrize("text", [
    "Телефон в формате +7 (XXX) XXX-XX-XX.",  # XXX в маске это формат
    'Ответ: {"items": [...], "total": 0}',  # многоточие в примере JSON
    "Вызов send(...) повторяется трижды.",  # многоточие в примере кода
    "После оплаты будет добавлена запись в журнал.",  # обычное будущее время
    "Поле будет заполнено автоматически.",  # обычное будущее время
])
def test_placeholder_dictionary_skips_ordinary_text(text):
    from reqask.lint import placeholder_marks

    assert placeholder_marks(text) == []


def test_extract_json():
    assert extract_json('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert extract_json('Вот ответ: {"a": {"b": 2}} конец') == '{"a": {"b": 2}}'
    with pytest.raises(ValueError):
        extract_json("нет json")


def test_pipeline_end_to_end(doc):
    llm = FakeLLM()
    result = Pipeline(llm, SETTINGS).run(doc, "test")

    reqs = result.requirements
    assert [r.id for r in reqs] == ["REQ-01", "REQ-02", "REQ-03"]  # две цифры при числе до 99
    assert reqs[0].source_id == "FR-1" and reqs[2].source_id is None
    assert reqs[0].quote == doc.line(4).text  # цитата вырезана из документа дословно
    assert (reqs[2].line_start, reqs[2].line_end) == (9, 11)  # таблица целиком, вместе с шапкой
    assert reqs[2].kind == "other"
    assert reqs[0].lint_hints and reqs[0].lint_confirmed == reqs[0].lint_hints  # «быстро» есть в цитате дефекта

    by_id = {f.id: f for f in result.findings}
    d1 = by_id["D-01"]
    assert d1.severity == "CRITICAL" and d1.criterion == "VERIFIABLE"
    assert d1.evidence[0].status == "exact" and d1.evidence[0].line == 4
    assert d1.question == "Какое время ответа, в секундах?" and d1.addressee == "business" and d1.impact == "и"
    assert by_id["D-02"].req_ids == ["REQ-02"]  # дефект с неверным критерием отброшен, порция цела
    d2 = by_id["D-02"]  # выдуманная цитата: не найдена, замечание в карантине (К-06)
    assert d2.evidence[0].status == "missing" and d2.status == "quarantine" and result.grounding.quarantine == 1
    assert by_id["D-02"].question is None and by_id["D-02"].addressee is None
    assert result.quality.dropped_defects == 1 and result.quality.dropped_checks == 1

    checks = {c.criterion: c for c in result.checks["REQ-01"]}
    assert len(checks) == 9 and checks["VERIFIABLE"].status == "fail"
    assert checks["COMPLETE"].status == "unknown"  # fail без дефекта
    assert checks["NECESSARY"].status == "na" and checks["SINGULAR"].status == "pass"
    assert {c.status for c in result.checks["REQ-03"]} == {"pass"}
    # Дефект важнее оценки pass; пропущенные оценки считаются pass и видны в паспорте.
    amb = {c.criterion: c for c in result.checks["REQ-02"]}["UNAMBIGUOUS"]
    assert amb.status == "fail" and amb.note == ""
    assert result.quality.checks_pass_overridden == 1
    assert result.quality.checks_missing == 5 + 8 + 9

    s1 = by_id["S-01"]
    assert s1.kind == "contradiction" and s1.req_ids == ["REQ-02", "REQ-03"]
    assert [e.line for e in s1.evidence if e.status != "missing"] == [5, 11] and s1.evidence[2].status == "missing"
    assert s1.question and s1.addressee == "business"
    gap = next(f for f in result.findings if f.title == "Нет требований к доступу")
    assert gap.kind == "gap" and not gap.evidence and gap.section == "Требования" and gap.addressee == "security"
    titles = {f.title for f in result.findings}
    assert "Без опоры" not in titles and "Пробел без места" not in titles  # без опоры на текст отброшены
    assert result.grounding.dropped_findings == 2 and result.grounding.missing == 3
    assert [a.criterion for a in result.set_analyses] == ["SET_CONSISTENT", "SET_COMPLETE"]
    assert result.set_analyses[1].status == "partial"  # чужой критерий из первого прохода не принят

    # Второй проход по набору видит замечания первого и просит их не повторять.
    assert "Разное число книг" in llm.users[3]

    v = result.verdict
    assert v.decision == "Не рекомендуется начинать" and v.blockers == ["S-01", "D-01"] and v.critic_done
    assert v.ready_for_development == "Нет" and v.ready_for_testing == "Нет"
    assert [fix.finding_ids for fix in v.top_fixes] == [["S-01"]]

    # Сводные вопросы: проверки кодом, приоритет, запасной вопрос для непокрытого CRITICAL (К-08).
    qs = result.questions
    assert [(q.id, q.finding_ids, q.source) for q in qs] == [
        ("Q-01", ["S-01"], "model"), ("Q-02", ["D-01"], "fallback"), ("Q-03", ["S-02"], "model"),
    ]
    assert [q.priority for q in qs] == [5.5, 5.25, 2.0]  # CRITICAL 5 + 0,25 за требование
    assert qs[0].recommended == 1 and qs[0].addressee == "business" and qs[0].req_ids == ["REQ-02", "REQ-03"]
    assert [e.line for e in qs[0].quotes] == [5, 11]  # цитаты подставлены из замечания
    assert len(qs[2].options) == 4 and qs[2].recommended is None and qs[2].why_recommended is None
    assert qs[2].addressee == "analyst" and qs[1].text == "Какое время ответа, в секундах?"
    q = result.quality
    assert (q.questions_dropped, q.questions_merged, q.questions_added) == (2, 1, 1)
    assert by_id["D-01"].question_id == "Q-02" and by_id["S-01"].question_id == "Q-01"
    assert v.questions_by_model
    assert [(s.line_start, s.line_end, s.reason) for s in result.skipped_lines] == [(13, 14, "template")]
    assert result.uncovered_lines == []
    assert result.quality.ids_in_document == 2 and result.quality.ids_missing == []
    assert result.rewritten == {"REQ-01": "Система отвечает за <N секунд>."}

    _check_report(result)


SECTIONS = (
    "**Вердикт:", "## 1. Паспорт прогона", "## 2. Нарезка на требования", "## 3. Проверка каждого требования",
    "## 4. Проверка набора требований целиком", "## 5. Сводка", "## 6. Вердикт", "## 7. Вопросы к автору ТЗ",
    "## Приложение А.", "## Приложение Б.",
)


def _check_report(result):
    """Т-05: порядок разделов, вердикт до паспорта, вопросы, формат идентификаторов, нет тире."""
    report = render(result)
    positions = [report.index(h) for h in SECTIONS]
    assert positions == sorted(positions)
    for heading in ("### 4.1. Системная полнота", "### 4.2. Взаимная непротиворечивость", "### 4.3. Осуществимость и стандарты"):
        assert heading in report
    assert "**Вердикт: Не рекомендуется начинать.**" in report
    assert "Критичные замечания не перепроверены" not in report and "| Критик | проверено CRITICAL и MAJOR" in report
    # Первый экран: блокеры и главные вопросы до паспорта, со ссылками на якоря.
    first = report[: report.index("## 1. Паспорт прогона")]
    assert len(first.splitlines()) <= 40
    assert "[S-01](#s-01)" in first and "[Q-01](#q-01)" in first
    assert '<a id="q-01"></a>' in report and '<a id="req-01"></a>' in report and '<a id="d-01"></a>' in report
    # Блок требования (9.2): заголовок, оценки одной строкой, дефект с вопросом и ссылкой на сводный вопрос.
    assert '### <a id="req-01"></a>REQ-01 · FR-1 · строка' in report
    marks = next(line for line in report.splitlines() if line.startswith("Оценки: "))
    assert "❌ Пров." in marks and "➖ Необх." in marks
    # Пояснение печатается у «не применим», а у нарушения с дефектом его даёт сам дефект.
    assert "- ➖ Необходимость: " in report and "- ❌ Проверяемость: " not in report
    assert "| Критерий | Оценка |" not in report
    assert "**D-01 [CRITICAL] Проверяемость.**" in report
    assert "- Вопрос заказчику (бизнес): Какое время ответа, в секундах? См. [Q-02](#q-02)." in report
    assert "**Готовая формулировка:** Система отвечает за <N секунд>." in report
    # Требования без замечаний собраны в одну строку со ссылками, а не в отдельные блоки.
    assert '**Без замечаний, все применимые критерии выполнены (1):** <a id="req-03"></a>REQ-03 (строки 9-11).' in report
    # Вопросы (9.3): группа по адресату, варианты, рекомендация, что закрывает.
    assert '#### <a id="q-01"></a>Q-01 · заказчику (бизнес) · блокирует разработку' in report
    assert "  1. вариант 1. Последствие: правка" in report and "- Рекомендуем: вариант 1, потому что так проще" in report
    assert "- Закрывает замечания: [S-01](#s-01)." in report
    assert "fake-model" in report and "Журнал шагов" in report
    assert "—" not in report and "–" not in report


def test_questions_file_has_no_service_links(doc):
    from reqask.report import render_questions

    text = render_questions(Pipeline(FakeLLM(), SETTINGS).run(doc, "test"))
    assert text.startswith("# Вопросы по документу «spec.md»")
    assert "## Вопросы заказчику (бизнес)" in text and "### Q-01. Вопрос про S-01?" in text
    assert "Варианты:" in text and "Сейчас в документе: `Читатель может взять" in text
    assert "Закрывает замечания" not in text and "](#" not in text and "D-01" not in text
    assert "—" not in text and "–" not in text


def test_steps_are_logged_in_table_order(doc):
    logs = []
    result = Pipeline(FakeLLM(), SETTINGS, logs.append).run(doc, "test")
    assert [s.number for s in result.steps] == ["0", "1", "2", "3", "4", "5", "5в", "6", "7", "8"]
    assert {s.number: s.status for s in result.steps}["7"] == "ok"
    assert result.critic.keep == result.critic.reviewed > 0 and result.verdict.critic_done
    off = Pipeline(FakeLLM(), replace(SETTINGS, critic=False)).run(doc, "test")
    assert {s.number: s.status for s in off.steps}["7"] == "skipped"
    assert all(s.status in ("ok", "skipped") for s in result.steps)
    assert sum(s.calls for s in result.steps) == result.llm.calls
    assert "Шаг 3. Нарезка требований (14 строк)" in logs and any("итог шага: требований 3" in x for x in logs)


def test_ids_lost_in_segmentation_are_reported(doc):
    class Lossy(FakeLLM):
        def complete_json(self, step, system, user, schema, kind=""):
            out = super().complete_json(step, system, user, schema, kind)
            if schema is SegmentationOut:
                out.requirements[1].source_id = None
            return out

    result = Pipeline(Lossy(), SETTINGS).run(doc, "test")
    assert result.quality.ids_missing == ["FR-2"]
    assert "которых нет в нарезке: FR-2" in render(result)


def test_ids_use_three_digits_over_99():
    assert make_id("REQ", 7, 99) == "REQ-07" and make_id("REQ", 7, 100) == "REQ-007"


def test_pipeline_survives_failed_steps(doc):
    class Flaky(FakeLLM):
        def complete_json(self, step, system, user, schema, kind=""):
            if schema in (BatchReviewOut, FinalOut) or "полнота" in step:
                self.steps.append(step)
                raise LLMError("сбой")
            return super().complete_json(step, system, user, schema, kind)

    result = Pipeline(Flaky(), SETTINGS).run(doc, "test")
    assert result.unreviewed == ["REQ-01", "REQ-02", "REQ-03"]
    assert len(result.failed_steps) == 5  # три требования, проход по набору, итог
    assert [f.id for f in result.findings] == ["S-01"]
    assert result.verdict.generated_by_model is False and result.verdict.top_fixes
    # Запасной путь вопросов: из поля question замечания, без вариантов (К-08).
    assert not result.verdict.questions_by_model
    assert [(q.id, q.finding_ids, q.source, q.options) for q in result.questions] == [("Q-01", ["S-01"], "fallback", [])]
    report = render(result)
    assert "> **Отчёт неполный.**" in report and report.index("Отчёт неполный") < report.index("**Вердикт:")
    assert "шаг 4 «Проверка каждого требования»: не выполнен" in report
    assert "Сводные вопросы не сформированы" in report


def test_llm_repairs_invalid_json(monkeypatch):
    client = LLMClient(SETTINGS)
    answers = iter(["это не json", '{"rationale": "ок", "top_fixes": [{"finding_ids": ["D-001"]}]}',
                    '{"rationale": "ок", "top_fixes": []}'])
    seen = []

    def fake_chat(step, messages, schema, kind="", effort=None):
        seen.append(len(messages))
        return next(answers)

    monkeypatch.setattr(client, "_chat", fake_chat)
    out = client.complete_json("итог", "system", "user", SimpleOut)
    assert out.rationale == "ок" and client.stats.repairs == 2
    assert seen == [2, 4, 4]  # в повторе модель видит свой ответ и текст ошибки


def test_llm_gives_up_after_repairs(monkeypatch):
    client = LLMClient(SETTINGS)
    monkeypatch.setattr(client, "_chat", lambda *a: "мусор")
    with pytest.raises(LLMError):
        client.complete_json("итог", "system", "user", SimpleOut)


# ---------- клиент против локального сервера: что уходит провайдеру и как разбирается ответ ----------


@pytest.fixture
def client_with():
    """Настоящий LLMClient против локального HTTP-сервера. handler(тело запроса, номер) -> (код, тело ответа)."""
    servers = []

    def make(handler, **overrides):
        sent: list[dict] = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["content-length"])))
                sent.append(body)
                status, payload = handler(body, len(sent))
                data = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        params = {"cache_dir": None, "max_retries": 0, **overrides}
        settings = Settings(provider="gemini", base_url=f"http://127.0.0.1:{server.server_port}/v1/", api_key="x",
                            model="m", **params)
        logs: list[str] = []
        return LLMClient(settings, logs.append), sent, logs

    yield make
    for server in servers:
        server.shutdown()
        server.server_close()


def _completion(content: str, finish: str = "stop") -> dict:
    return {
        "id": "1", "object": "chat.completion", "created": 0, "model": "m",
        "choices": [{"index": 0, "finish_reason": finish, "message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 40,
                  "completion_tokens_details": {"reasoning_tokens": 25}},
    }


VERDICT_JSON = '{"rationale": "ок", "top_fixes": []}'


def test_llm_request_params(client_with):
    client, sent, logs = client_with(lambda body, n: (200, _completion(VERDICT_JSON)), temperature=0.3)
    out = client.complete_json("итог", "system", "user", SimpleOut, kind="verdict")
    client.complete_json("нарезка 1/1", "system", "user", SimpleOut, kind="segment")

    assert out.rationale == "ок"
    first, second = sent
    assert "temperature" not in first and "top_p" not in first and "seed" not in first
    assert any("LLM_TEMPERATURE" in line for line in logs)  # одно предупреждение, параметр не ушёл
    assert (first["reasoning_effort"], first["max_tokens"]) == ("medium", 24_000)
    assert (second["reasoning_effort"], second["max_tokens"]) == ("low", 16_000)
    assert first["response_format"]["type"] == "json_schema"  # режим parse: схему строит SDK
    assert first["response_format"]["json_schema"]["name"] == "SimpleOut"
    assert "JSON Schema" not in first["messages"][0]["content"]  # схема ушла один раз, в response_format (П-04)
    stats = client.stats
    assert (stats.calls, stats.prompt_tokens, stats.completion_tokens) == (2, 20, 10)
    assert (stats.total_tokens, stats.reasoning_tokens) == (80, 50)


def test_llm_json_mode_ladder(client_with):
    def handler(body, n):
        if "response_format" in body:
            return 400, {"error": {"message": "response_format is not supported", "code": 400}}
        return 200, _completion("Ответ:\n```json\n" + VERDICT_JSON + "\n```")

    client, sent, _ = client_with(handler)
    client.complete_json("итог", "system", "user", SimpleOut, kind="verdict")
    formats = [(body.get("response_format") or {}).get("type") for body in sent]
    assert formats == ["json_schema", "json_schema", "json_object", None]  # parse, schema, object, none
    assert "strict" in sent[0]["response_format"]["json_schema"] and "strict" not in sent[1]["response_format"]["json_schema"]
    has_schema_text = ["JSON Schema" in body["messages"][0]["content"] for body in sent]
    assert has_schema_text == [False, False, True, True]  # текстом схема идёт только в object и none


def test_llm_drops_rejected_params_and_stops_on_bad_key(client_with):
    def handler(body, n):
        if "reasoning_effort" in body:
            return 400, [{"error": {"code": 400, "message": "Unknown parameter: reasoning_effort"}}]
        if "max_tokens" in body:
            return 400, {"error": {"message": "max_tokens is not supported, use max_completion_tokens"}}
        return 200, _completion(VERDICT_JSON)

    client, sent, _ = client_with(handler)
    client.complete_json("итог", "system", "user", SimpleOut, kind="verdict")
    assert len(sent) == 3 and "reasoning_effort" not in sent[2] and "max_tokens" not in sent[2]
    assert sent[2]["response_format"]["type"] == "json_schema"  # режим JSON при этом не понижен

    # Gemini отдаёт тело ошибки списком, причина есть только в нём.
    client, sent, _ = client_with(lambda body, n: (400, [{"error": {"code": 400, "message": "Please pass a valid API key"}}]))
    with pytest.raises(LLMFatal):
        client.complete_json("итог", "system", "user", SimpleOut, kind="verdict")
    assert len(sent) == 1  # без повторов и без понижения режимов


def test_llm_truncated_and_unparsed_answers(client_with):
    client, _, _ = client_with(lambda body, n: (200, _completion('{"rationale": "об', finish="length")))
    with pytest.raises(LLMTruncated):
        client.complete_json("итог", "system", "user", SimpleOut, kind="verdict")
    assert client.stats.calls == 1

    # Ответ не по схеме: SDK его не разбирает, клиент отдаёт текст модели на исправление.
    answers = iter(['{"rationale": 5, "top_fixes": "нет"}', VERDICT_JSON])
    client, sent, _ = client_with(lambda body, n: (200, _completion(next(answers))))
    out = client.complete_json("итог", "system", "user", SimpleOut, kind="verdict")
    assert out.rationale == "ок" and client.stats.repairs == 1 and len(sent[1]["messages"]) == 4


def test_llm_daily_quota_is_fatal_without_retries(client_with):
    body = [{"error": {"code": 429, "status": "RESOURCE_EXHAUSTED",
                       "message": "Quota exceeded: Generate content requests per day limit exceeded on Free Tier."}}]
    client, sent, _ = client_with(lambda request, n: (429, body), max_retries=3)
    with pytest.raises(LLMFatal):
        client.complete_json("итог", "system", "user", SimpleOut, kind="verdict")
    assert len(sent) == 1  # повторы суточную квоту не вернут, а запросы тратят


def test_decision_rule_ignores_inactive_findings():
    from reqask.schemas import Finding

    def f(severity, criterion="COMPLETE", status="unreviewed", fid="D-01"):
        return Finding(id=fid, scope="requirement", criterion=criterion, severity=severity,
                       problem="п", recommendation="р", status=status)

    decide = Pipeline.decide
    assert decide([f("CRITICAL", "VERIFIABLE")]) == ("Не рекомендуется начинать", "Нет", "Нет", ["D-01"])
    assert decide([f("CRITICAL", "NECESSARY")])[2] == "Да, с оговорками"  # не блокер тестирования
    assert decide([f("MAJOR")])[:3] == ("Условно допускается", "Да, с оговорками", "Да, с оговорками")
    assert decide([f("MINOR")])[0] == "Допускается" and decide([])[0] == "Допускается"
    # Снятое критиком и ушедшее в карантин CRITICAL на решение не влияет (К-09).
    gone = [f("CRITICAL", status="quarantine"), f("CRITICAL", status="dropped", fid="D-02"), f("MAJOR", fid="D-03")]
    assert decide(gone) == ("Условно допускается", "Да, с оговорками", "Да, с оговорками", [])


def test_final_step_retries_with_fewer_questions_when_truncated(doc):
    class Long(FakeLLM):
        def complete_json(self, step, system, user, schema, kind=""):
            if schema is FinalOut and "не больше 4." in user:
                self.steps.append(step)
                self.users.append(user)
                raise LLMTruncated("[итог] ответ обрезан по лимиту длины")
            return super().complete_json(step, system, user, schema, kind)

    llm = Long()
    result = Pipeline(llm, SETTINGS).run(doc, "test")
    finals = [u for s, u in zip(llm.steps, llm.users) if s == "итог"]
    # Четыре CRITICAL и MAJOR с вопросом дают потолок 4; после обрезки повтор с потолком 3.
    assert len(finals) == 2 and "не больше 3." in finals[1]
    assert result.verdict.questions_by_model and not result.failed_steps


def test_model_text_has_no_dashes_but_quotes_stay():
    from reqask.pipeline import tidy

    assert tidy("длина 1–64 символа") == "длина 1-64 символа"
    assert tidy("ФТ-1 — ФТ-4 покрыты") == "ФТ-1 - ФТ-4 покрыты"
    assert tidy("порог — главное") == "порог, главное"
    assert tidy(None) is None


def test_single_quote_contradiction_becomes_question(doc):
    class OneQuote(FakeLLM):
        def complete_json(self, step, system, user, schema, kind=""):
            out = super().complete_json(step, system, user, schema, kind)
            if schema is SetReviewOut and "согласованность" in step:
                out.findings[0].evidence = out.findings[0].evidence[:1]
            return out

    result = Pipeline(OneQuote(), SETTINGS).run(doc, "test")
    s1 = next(f for f in result.findings if f.title == "Разное число книг")
    assert s1.status == "question_only" and result.grounding.question_only == 1
    q = next(q for q in result.questions if s1.id in q.finding_ids)
    assert q.source == "fallback" and s1.id not in result.verdict.blockers
    report = render(result)
    assert "### Требует проверки" in report and "критичных замечаний не подтверждены цитатой" in report


def test_same_problem_in_three_requirements_is_folded():
    from reqask.schemas import Evidence, Finding, Requirement

    reqs = [Requirement(id=f"REQ-0{i}", source_id=None, section="", line_start=i, line_end=i, kind="other",
                        summary="", quote="q") for i in range(1, 5)]
    def f(i, problem="Нет единицы измерения."):
        return Finding(id=f"D-0{i}", scope="requirement", criterion="COMPLETE", severity="MAJOR", req_ids=[f"REQ-0{i}"],
                       evidence=[Evidence(quote="q", line=i)], problem=problem, recommendation="р")
    findings = [f(1), f(2, "нет единицы  измерения"), f(3), f(4, "Другое.")]
    folded = Pipeline(FakeLLM(), SETTINGS).fold(findings, reqs)
    assert len(folded) == 1
    system, members = folded[0]
    assert system.scope == "set" and system.req_ids == ["REQ-01", "REQ-02", "REQ-03"] and len(system.places) == 3
    assert [m.status for m in members] == ["merged"] * 3 and findings[3].status == "unreviewed"


def test_truncated_set_pass_retries_once_with_low_effort(doc):
    """М-07: проход по набору после обрезки повторяется один раз с reasoning_effort=low."""
    class Cut(FakeLLM):
        efforts: list = []

        def complete_json(self, step, system, user, schema, kind="", **opts):
            if schema is SetReviewOut and "согласованность" in step:
                self.efforts.append(opts.get("effort"))
                if opts.get("effort") != "low":
                    raise LLMTruncated("обрезан")
            return super().complete_json(step, system, user, schema, kind)

    llm = Cut()
    result = Pipeline(llm, SETTINGS).run(doc, "test")
    assert llm.efforts == [None, "low"] and not result.failed_steps


def test_truncated_critic_retries_once_with_low_effort(doc):
    """Обрезанный ответ критика повторяется один раз с reasoning_effort=low, шаг не падает."""
    class Cut(FakeLLM):
        efforts: list = []

        def complete_json(self, step, system, user, schema, kind="", **opts):
            if schema is CriticOut:
                self.efforts.append(opts.get("effort"))
                if opts.get("effort") != "low":
                    raise LLMTruncated("обрезан")
            return super().complete_json(step, system, user, schema, kind)

    llm = Cut()
    result = Pipeline(llm, SETTINGS).run(doc, "test")
    assert llm.efforts == [None, "low"]
    assert result.critic.done and not result.failed_steps


def test_failed_batch_logs_reason_kind_and_text(doc):
    """Сбой порции пишет в журнал вид ошибки и короткий текст, а не только «сбой»."""
    from reqask.pipeline import error_reason

    class Broken(FakeLLM):
        calls = 0

        def complete_json(self, step, system, user, schema, kind="", **opts):
            if schema is BatchReviewOut:
                Broken.calls += 1
                if Broken.calls == 1:
                    raise LLMError(f"[{step}] модель не вернула валидный JSON: reviews.0.checks: field required")
                if Broken.calls == 2:
                    raise LLMTruncated(f"[{step}] ответ обрезан по лимиту длины")
            return super().complete_json(step, system, user, schema, kind)

    logs: list[str] = []
    Pipeline(Broken(), SETTINGS, log=logs.append).run(doc, "test")
    split = [m for m in logs if "делю порцию пополам" in m]
    assert split and "(схема: модель не вернула валидный JSON: reviews.0.checks: field required)" in split[0]
    assert "[" not in split[0].split("(", 1)[1]  # служебная метка шага срезана
    assert any("не проверено (обрезка: ответ обрезан по лимиту длины)" in m for m in logs)
    assert error_reason(LLMError("[итог] ошибка провайдера 500: " + "x" * 400)).startswith("другое: ошибка провайдера 500")
    assert len(error_reason(LLMError("y" * 400))) <= len("другое: ") + 200


def test_truncated_segmentation_chunk_is_split(tmp_path):
    """М-07: обрезанный ответ нарезки делит кусок пополам."""
    path = tmp_path / "long.md"
    path.write_text("\n".join(f"* Правило {i}: система хранит запись {i}." for i in range(1, 61)), encoding="utf-8")
    long_doc = load_document(path)

    class Cut(FakeLLM):
        ranges: list = []

        def complete_json(self, step, system, user, schema, kind="", **opts):
            if schema is SegmentationOut:
                self.ranges.append(step)
                if step == "нарезка 1/1":
                    raise LLMTruncated("обрезан")
                return SegmentationOut.model_validate({"requirements": [], "skipped": []})
            return super().complete_json(step, system, user, schema, kind)

    llm = Cut()
    Pipeline(llm, SETTINGS).run(long_doc, "test")
    assert llm.ranges == ["нарезка 1/1", "нарезка 1/1a", "нарезка 1/1b"]


def test_critic_decisions_and_limits(doc):
    """К-07: решения критика применяются, ограничения держит код."""
    from reqask.schemas import Evidence, Finding

    def f(fid, severity, req="REQ-01", scope="requirement", line=4):
        return Finding(id=fid, scope=scope, criterion="COMPLETE", severity=severity, req_ids=[req],
                       evidence=[Evidence(quote=f"цитата {fid}", line=line)], problem=f"проблема {fid}",
                       recommendation="р", question=None if fid == "S-01" else f"вопрос {fid}?")

    findings = [f("D-01", "CRITICAL"), f("D-02", "MAJOR"), f("D-03", "MAJOR"), f("D-04", "MAJOR"),
                f("D-05", "CRITICAL", req="REQ-02", line=5), f("D-06", "MAJOR"), f("D-07", "MAJOR"),
                f("D-08", "MAJOR"), f("D-09", "MINOR"), f("D-10", "MAJOR"), f("S-01", "MAJOR", scope="set")]

    def d(fid, action, severity=None, into=None, reason="причина"):
        return {"finding_id": fid, "action": action, "severity": severity, "into": into, "reason": reason}

    class CriticLLM:
        stats = LLMStats()
        users: list[str] = []

        def complete_json(self, step, system, user, schema, kind=""):
            assert schema is CriticOut and kind == "critic"
            self.users.append(user)
            if len(self.users) > 1:
                return CriticOut.model_validate({"decisions": []})  # повтор по D-10 тоже без решения
            return CriticOut.model_validate({"decisions": [
                d("d-01", "downgrade", "major", reason="число есть в разделе данных"),
                d("D-02", "downgrade", "CRITICAL"),          # повысить нельзя
                d("D-03", "drop", reason="  "),              # снять без причины нельзя
                d("D-04", "drop", reason="сведения есть в строке 9"),
                d("D-05", "merge", into="S-01"),             # цель берёт старший уровень, цитаты и требования
                d("D-06", "merge", into="D-07"), d("D-07", "merge", into="D-06"),  # цикл
                d("D-08", "merge", into="X-404"),            # неизвестная цель
                d("D-09", "drop"),                           # MINOR критику не передаётся
                d("S-01", "keep"), d("S-01", "drop"),        # второе решение по тому же замечанию
            ]})

    llm = CriticLLM()
    pipe = Pipeline(llm, SETTINGS)
    pipe.critique(doc, findings)
    by = {x.id: x for x in findings}
    c = pipe.critic

    assert "D-09 |" not in llm.users[0] and "D-10 |" in llm.users[0]
    assert by["D-01"].status == "downgraded" and by["D-01"].severity == "MAJOR" and by["D-01"].severity_before == "CRITICAL"
    assert by["D-02"].severity == "MAJOR" and by["D-02"].status == "unreviewed"
    assert by["D-03"].status == "unreviewed"
    assert by["D-04"].status == "dropped" and by["D-04"].critic_reason == "сведения есть в строке 9"
    assert by["D-05"].status == "merged" and by["D-05"].merged_into == "S-01"
    s1 = by["S-01"]
    assert s1.status == "confirmed" and s1.severity == "CRITICAL" and s1.severity_before == "MAJOR"
    assert s1.req_ids == ["REQ-01", "REQ-02"] and [e.line for e in s1.evidence] == [4, 5]
    assert s1.question == "вопрос D-05?"  # у цели вопроса не было, взят у слитого
    assert by["D-06"].status == by["D-07"].status == by["D-08"].status == "unreviewed"
    assert by["D-09"].status == "unreviewed" and by["D-10"].status == "unreviewed"
    assert (c.reviewed, c.keep, c.downgraded, c.dropped, c.merged, c.no_decision, c.rejected) == (10, 1, 1, 1, 1, 1, 7)
    assert (c.retry_calls, c.retry_resolved) == (1, 0) and len(llm.users) == 2
    assert "D-10 |" in llm.users[1] and "Это повторный запрос" in llm.users[1]
    assert c.done and pipe._verdict(findings, rationale="").critic_done
    # Слитое и снятое не входят в вердикт: блокер теперь S-01, а не D-05.
    assert Pipeline.decide(findings)[3] == ["S-01"]


def test_report_shows_critic_merges(doc):
    """Цель слияния перечисляет слитые замечания, в приложении Б нет двух точек подряд."""
    result = Pipeline(FakeLLM(), SETTINGS).run(doc, "test")
    src = next(f for f in result.findings if f.id.startswith("D-"))
    src.status, src.merged_into, src.critic_reason = "merged", "S-01", "то же исправление."
    src.problem = src.problem.rstrip(".") + "."
    report = render(result)
    assert f"- Критик слил сюда: [{src.id}](#{src.id.lower()})" in report
    assert "Причина: слито с другим замечанием [S-01](#s-01): то же исправление." in report
    appendix = report[report.index("## Приложение Б."):]
    assert not re.search(r"[^.]\.\.(?!\.)", appendix)


def test_question_text_helpers():
    """Цитаты без повторов, суть без пересказа цитаты, аббревиатура в начале фразы не портится."""
    from reqask.grounding import distinct_quotes
    from reqask.report import _question_body, _sentence_case
    from reqask.schemas import Option

    long = Evidence(quote="Ответ, если доступ к ресурсу запрещен.", line=7, status="exact")
    part = Evidence(quote="доступ к ресурсу запрещен", line=7, status="exact")
    other = Evidence(quote="доступ к ресурсу запрещен", line=9, status="exact")
    lost = Evidence(quote="нет такого", line=3, status="missing")
    assert distinct_quotes([part, long, other, lost]) == [long, other]
    assert _sentence_case("GET меняет данные") == "GET меняет данные" and _sentence_case("Так проще") == "так проще"
    q = Question(id="Q-01", text="Какой код?", addressee="architect", blocks="нельзя", finding_ids=["S-01"],
                 quotes=[long], doc_says="Ответ, если доступ к ресурсу запрещен", recommended=None)
    assert not any(row.startswith("- Суть:") for row in _question_body(q))
    q.doc_says = "Для одного случая заданы два разных кода"
    assert "- Суть: Для одного случая заданы два разных кода" in _question_body(q)
    q.blocks = "Нельзя написать тест на ответ."
    q.options = [Option(answer="Код 404", consequence="Клиент не узнает, что ресурс есть."),
                 Option(answer="Код 403", consequence="GET отдаёт отказ")]
    body = _question_body(q)
    assert "- Без ответа: нельзя написать тест на ответ." in body
    assert "  1. Код 404. Последствие: клиент не узнает, что ресурс есть." in body
    assert "  2. Код 403. Последствие: GET отдаёт отказ." in body


def test_priority_caps_requirement_bonus():
    """Вопрос по таблице, порезанной на много требований, не обгоняет вопрос того же уровня (К-08)."""
    from reqask.schemas import Finding

    def finding(fid: str, reqs: list[str]) -> Finding:
        return Finding(id=fid, scope="set", criterion="CONSISTENT", severity="CRITICAL",
                       problem="п", recommendation="р", req_ids=reqs)

    assert Pipeline._priority([finding("S-01", ["REQ-01", "REQ-02", "REQ-03", "REQ-04"])])[0] == 5.5
    assert Pipeline._priority([finding("S-02", ["REQ-05", "REQ-06"])])[0] == 5.5
    assert Pipeline._priority([finding("S-03", ["REQ-07"])])[0] == 5.25


def test_equal_priority_puts_set_findings_first():
    """При равном весе вопрос по замечанию набора идёт раньше вопроса по одному требованию (К-08)."""
    from reqask.schemas import Finding

    d = Finding(id="D-01", scope="requirement", criterion="COMPLETE", severity="CRITICAL", problem="п",
                recommendation="р", req_ids=["REQ-01", "REQ-02"])
    s = Finding(id="S-01", scope="set", criterion="CONSISTENT", severity="CRITICAL", problem="п",
                recommendation="р", req_ids=["REQ-03", "REQ-04"])
    qs = [Question(id="", text="Про D?", addressee="architect", blocks="б", finding_ids=["D-01"], priority=5.5),
          Question(id="", text="Про S?", addressee="business", blocks="б", finding_ids=["S-01"], priority=5.5)]
    out = Pipeline._number_questions(qs, [d, s])
    assert [(q.id, q.finding_ids) for q in out] == [("Q-01", ["S-01"]), ("Q-02", ["D-01"])]


def test_line_marks_become_words():
    """Служебная разметка строк из промпта не попадает в отчёт (причины критика, тексты модели)."""
    from reqask.pipeline import _plain_lines, tidy

    assert _plain_lines("Чек-лист в L68 и L72 не отмечен") == "Чек-лист в строках 68 и 72 не отмечен"
    assert _plain_lines("L20 указывает") == "строка 20 указывает"
    assert _plain_lines("кэш L2-уровня") == "кэш L2-уровня"
    # В общем тексте модели правится только разметка с нулями: короткое L5 может быть обозначением документа.
    assert tidy("см. L0012, уровень L5") == "см. строка 12, уровень L5"


def test_final_prompt_marks_findings_without_question(doc):
    """Итог видит, у каких CRITICAL и MAJOR нет вопроса, и получает документ для сверки."""
    result = Pipeline(FakeLLM(), SETTINGS).run(doc, "test")
    f = next(x for x in result.findings if x.severity != "MINOR")
    f.question = None
    text = prompts.final_prompt("spec.md", 3, [f], "решение", 5, doc.numbered())
    assert f"{f.id} | {f.severity}" in text and "| вопроса нет" in text
    assert "Документ (слева номера строк)" in text and doc.numbered() in text


def test_placeholders_outside_requirements_go_to_set_pass(doc):
    """Заглушка вне требований попадает подсказкой во второй проход по набору и в паспорт."""
    llm = FakeLLM()
    result = Pipeline(llm, SETTINGS).run(doc, "test")
    no = next(line.no for line in doc.lines if line.text == "заполняется позже")
    assert not any(r.line_start <= no <= r.line_end for r in result.requirements)
    assert result.quality.placeholder_lines == [no]
    assert result.quality.placeholder_lines_cited == [no]  # замечание «Пустой раздел» цитирует эту строку
    users = dict(zip(llm.steps, llm.users))
    assert f"- строка {no}: заполняется позже" in users["набор: полнота и остальные критерии"]
    assert "незаполненных мест" not in users["набор: согласованность"]
    assert "его цитата содержит саму пометку" in " ".join(users["набор: полнота и остальные критерии"].split())
    assert f"строк с незаполненными местами (TODO, TBD и подобные) 1: {no}; есть в замечаниях 1" in render(result)


def test_placeholder_counts_as_cited_only_when_quote_has_marker(tmp_path):
    """Замечание про другое место той же строки заглушку не закрывает."""
    path = tmp_path / "spec.md"
    path.write_text(DOC.replace("заполняется позже", "Раздел готовит отдел качества, срок TBD"), encoding="utf-8")
    doc = load_document(path)

    class OtherQuote(FakeLLM):
        def complete_json(self, step, system, user, schema, kind="", **opts):
            if schema is SetReviewOut and "полнота" in step:
                return SetReviewOut.model_validate({"analyses": [], "findings": [_set_finding(
                    "gap", "SET_COMPLETE", "MAJOR", "Кто готовит раздел", ["Раздел готовит отдел качества"],
                    question="Кто утверждает сценарии?")]})
            return super().complete_json(step, system, user, schema, kind)

    result = Pipeline(OtherQuote(), SETTINGS).run(doc, "test")
    no = next(line.no for line in doc.lines if "срок TBD" in line.text)
    assert result.quality.placeholder_lines == [no]
    assert any(e.line == no for f in result.findings for e in f.evidence)
    assert result.quality.placeholder_lines_cited == []


def test_final_prompt_forbids_invented_numbers_in_options(doc):
    """Числа, которого нет в документе, вариант ответа не выдаёт за готовый ответ."""
    text = prompts.final_prompt("spec.md", 3, [], "решение", 5, doc.numbered())
    rule = text[text.index("- Числа в вариантах."):]
    rule = rule[:rule.index("\n- ")]
    assert "только из документа" in rule
    assert "«задать значение» с единицей измерения" in rule and "«например»" in rule


def test_numbers_rule_is_shared_by_finding_and_summary_questions(doc):
    """Правило про числа одно на оба промпта, пример формата его не нарушает."""
    result = Pipeline(FakeLLM(), SETTINGS).run(doc, "test")
    review = prompts.review_prompt(result.requirements[:1], doc.numbered(), True)
    final = prompts.final_prompt("spec.md", 3, [], "решение", 5, doc.numbered())
    for text in (prompts.QUESTION_RULES, review, prompts.completeness_prompt([], doc.numbered()), final):
        assert f"- {prompts.NUMBERS_RULE}" in text
    example = prompts.QUESTION_RULES[prompts.QUESTION_RULES.index("- Пример формата"):]
    for number in re.findall(r"\d+", example):
        assert re.search(rf"например,? {number}\b", example), number


def test_review_prompt_rewrites_in_language_of_requirement(doc):
    """Готовая формулировка заменяет текст требования: язык требования, остальное по-русски."""
    result = Pipeline(FakeLLM(), SETTINGS).run(doc, "test")
    text = prompts.review_prompt(result.requirements[:1], doc.numbered(), True)
    rule = text[text.index("Язык rewritten"):]
    assert "язык текста этого требования" in rule and "<N seconds>" in rule
    assert "каждую метку в угловых скобках пиши на том же языке, и короткую, и описательную" in " ".join(rule.split())
    assert "остальные поля ответа пиши по-русски" in rule
    assert "если задача прямо не велит для поля другой язык" in prompts.SYSTEM


def test_merge_keeps_distinct_quotes_only():
    """Слияние не копирует ту же цитату и её часть; ненайденная цитата цели остаётся."""
    from reqask.schemas import Finding

    target = Finding(id="S-01", scope="set", criterion="SET_CONSISTENT", severity="MAJOR", problem="п",
                     recommendation="р", evidence=[Evidence(quote="Ответ 403, доступ запрещен.", line=7),
                                                   Evidence(quote="нет такой строки", line=None, status="missing")])
    src = Finding(id="D-01", scope="requirement", criterion="COMPLETE", severity="MAJOR", problem="п",
                  recommendation="р", evidence=[Evidence(quote="доступ запрещен", line=7),
                                                Evidence(quote="Ответ 403, доступ запрещен.", line=7),
                                                Evidence(quote="Другая строка документа", line=9)])
    Pipeline._merge_into(src, target)
    assert [(e.line, e.status) for e in target.evidence] == [(7, "exact"), (9, "exact"), (None, "missing")]


def test_question_with_two_choices_is_dropped():
    """Сводный вопрос с двумя знаками вопроса или с «и/или» склеивает два решения и отбрасывается."""
    from reqask.schemas import Finding

    ranked = [Finding(id="D-01", scope="requirement", criterion="COMPLETE", severity="MAJOR", problem="п",
                      recommendation="р", req_ids=["REQ-01"], question="в?")]
    opts = [{"answer": "да", "consequence": "c"}, {"answer": "нет", "consequence": "c"}]

    def q(text):
        return {"text": text, "addressee": "business", "options": opts, "recommended": None,
                "why_recommended": None, "blocks": "б", "doc_says": None, "finding_ids": ["D-01"]}

    out = FinalOut.model_validate({"rationale": "r", "top_fixes": [], "questions": [
        q("Сколько дней хранится заказ? Кто его отменяет?"), q("Нужен ли отчёт и/или выгрузка?"),
        q("Сколько дней хранится заказ: 1 или 3?")]})
    pipe = Pipeline(FakeLLM(), SETTINGS)
    questions = pipe._questions(out, ranked)
    assert [x.text for x in questions] == ["Сколько дней хранится заказ: 1 или 3?"]
    assert pipe.quality.questions_dropped == 2


def test_divergence_raises_to_critical_only_with_two_places(doc):
    """Расхождение поведения, расчёта или единиц в двух местах поднимается до CRITICAL; формат и имена нет."""
    two = ["Читатель может взять на руки не больше 5 книг", "Не больше 3 книг на читателя, integer"]

    class DivergenceLLM(FakeLLM):
        def complete_json(self, step, system, user, schema, kind=""):
            if schema is SetReviewOut and "согласованность" in step:
                self.stats.calls += 1
                return SetReviewOut.model_validate({"analyses": [], "findings": [
                    _set_finding("contradiction", "SET_CONSISTENT", "MAJOR", "Разный лимит", two,
                                 question="Сколько книг: 3 или 5?", divergence="Result"),
                    _set_finding("other", "SET_CONSISTENT", "MAJOR", "Разный тип", two,
                                 question="Какой тип поля?", divergence="format"),
                    _set_finding("other", "SET_CONSISTENT", "MAJOR", "Разные имена", two,
                                 question="Какое имя верное?", divergence="naming"),
                    _set_finding("other", "SET_COMPLETE", "MAJOR", "Единицы в одном месте", two[:1],
                                 question="В чём лимит?", divergence="units"),
                    _set_finding("other", "SET_CONSISTENT", "MAJOR", "Неизвестный вид", two,
                                 question="Что верно?", divergence="странный"),
                ]})
            return super().complete_json(step, system, user, schema, kind)

    result = Pipeline(DivergenceLLM(), SETTINGS).run(doc, "test")
    by_title = {f.title: f for f in result.findings if f.scope == "set"}
    raised = by_title["Разный лимит"]
    assert raised.severity == "CRITICAL" and raised.severity_raised_from == "MAJOR" and raised.divergence == "result"
    for title in ("Разный тип", "Разные имена", "Единицы в одном месте", "Неизвестный вид"):
        assert by_title[title].severity == "MAJOR" and by_title[title].severity_raised_from is None
    assert by_title["Неизвестный вид"].divergence == "none"
    assert result.quality.severity_raised == 1
    assert raised.id in result.verdict.blockers
    report = render(result)
    assert "Уровень поднят кодом с MAJOR до CRITICAL: два места документа задают разный результат расчёта." in report
    assert "уровень поднят кодом по виду расхождения 1" in report


def test_critical_keeps_question_when_model_question_is_dropped(doc):
    """Сводный вопрос с двумя «?» отброшен: CRITICAL всё равно получает вопрос из своего поля."""

    class DoubleLLM(FakeLLM):
        def complete_json(self, step, system, user, schema, kind=""):
            if schema is FinalOut:
                self.stats.calls += 1
                bad = _question(["S-01"], 2)
                bad["text"] = "Сколько книг можно взять? И на какой срок?"
                return FinalOut.model_validate({"rationale": "r", "top_fixes": [
                    {"finding_ids": ["S-01"], "action": "Оставить одно число."}],
                    "questions": [bad, _question(["S-02"], 2)]})
            return super().complete_json(step, system, user, schema, kind)

    result = Pipeline(DoubleLLM(), SETTINGS).run(doc, "test")
    critical = [f for f in result.findings if f.severity == "CRITICAL" and f.status not in ("merged", "dropped")]
    assert critical and all(f.question_id for f in critical)
    assert result.quality.questions_dropped == 1 and result.quality.questions_added >= 1
    assert all("?" not in q.text[:-1] for q in result.questions)


def test_critic_gets_merge_candidates_by_shared_line(doc):
    """Замечания с цитатами на одной строке идут критику группой кандидатов на слияние."""
    from reqask.schemas import Finding

    def f(fid, lines, severity="MAJOR"):
        return Finding(id=fid, scope="set" if fid.startswith("S") else "requirement", criterion="COMPLETE",
                       severity=severity, problem=f"п {fid}", recommendation="р", question="в?",
                       evidence=[Evidence(quote=f"цитата {fid} {n}", line=n) for n in lines]
                       + [Evidence(quote="не найдена", line=4, status="missing")])

    pool = [f("D-01", [5], "CRITICAL"), f("S-01", [5, 9], "CRITICAL"), f("D-02", [9]), f("D-03", [11])]
    groups = Pipeline._merge_candidates(pool)
    assert groups == [(5, ["D-01", "S-01"]), (9, ["S-01", "D-02"])]  # ненайденная цитата строки 4 не в счёт

    class CriticLLM(FakeLLM):
        def complete_json(self, step, system, user, schema, kind=""):
            self.users.append(user)
            return CriticOut.model_validate({"decisions": []})

    llm = CriticLLM()
    pipe = Pipeline(llm, SETTINGS)
    pipe.critique(doc, pool)
    assert "- строка 5: D-01, S-01" in llm.users[0] and "- строка 9: S-01, D-02" in llm.users[0]
    assert pipe.critic.candidate_groups == 2
    assert "Кандидаты на слияние" not in prompts.critic_prompt(pool, "", True, [])


def test_critic_retries_once_for_findings_without_decision(doc):
    """Повтор только по замечаниям без решения; цели слияния из первого списка доступны."""
    from reqask.schemas import Finding

    def f(fid, line, severity="MAJOR"):
        return Finding(id=fid, scope="set" if fid.startswith("S") else "requirement", criterion="COMPLETE",
                       severity=severity, problem=f"п {fid}", recommendation="р", question="в?",
                       evidence=[Evidence(quote=f"цитата {fid}", line=line)])

    pool = [f("S-01", 5, "CRITICAL"), f("D-01", 5, "CRITICAL"), f("D-02", 9), f("D-03", 11)]

    def d(fid, action, into=None):
        return {"finding_id": fid, "action": action, "severity": None, "into": into, "reason": "причина"}

    class RetryLLM(FakeLLM):
        def complete_json(self, step, system, user, schema, kind=""):
            self.users.append(user)
            if len(self.users) == 1:
                return CriticOut.model_validate({"decisions": [d("S-01", "keep"), d("D-02", "keep")]})
            # Повтор: решение по D-01 и D-03 принимается, по уже решённому S-01 отклоняется.
            return CriticOut.model_validate({"decisions": [
                d("D-01", "merge", into="S-01"), d("D-03", "keep"), d("S-01", "drop")]})

    llm = RetryLLM()
    pipe = Pipeline(llm, SETTINGS)
    pipe.critique(doc, pool)
    by = {x.id: x for x in pool}
    c = pipe.critic
    retry_rows = llm.users[1].split("Уже проверенные замечания")[0]
    assert "D-01 |" in retry_rows and "D-03 |" in retry_rows and "S-01 |" not in retry_rows
    assert "- строка 5: S-01, D-01" in llm.users[1]
    assert by["D-01"].status == "merged" and by["D-01"].merged_into == "S-01"
    assert by["S-01"].status == "confirmed" and by["D-03"].status == "confirmed"
    assert (c.retry_calls, c.retry_resolved, c.no_decision, c.rejected, c.merged) == (1, 2, 0, 1, 1)
    report_row = "повтор по замечаниям без решения: решено 2"
    pipe2 = Pipeline(FakeLLM(), SETTINGS)
    result = pipe2.run(doc, "test")
    result.critic = c
    assert report_row in render(result)


def test_blockers_set_first_and_all_on_first_screen_up_to_ten(doc):
    """Блокеры: S раньше D; на первом экране все, если их не больше десяти, иначе восемь и ссылка."""
    from reqask.schemas import Finding

    def crit(fid):
        return Finding(id=fid, scope="set" if fid.startswith("S") else "requirement", criterion="COMPLETE",
                       severity="CRITICAL", title=f"суть {fid}", problem=f"п {fid}", recommendation="р",
                       status="confirmed")

    ids = ["D-01", "D-02", "S-01", "S-02", "S-03", "S-04", "S-05", "S-06"]
    assert Pipeline.decide([crit(i) for i in ids])[3] == ids[2:] + ids[:2]

    def first_screen(n_set):
        result = Pipeline(FakeLLM(), SETTINGS).run(doc, "test")
        result.findings = [crit("D-01"), crit("D-02")] + [crit(f"S-{i:02d}") for i in range(1, n_set + 1)]
        result.verdict.blockers = Pipeline.decide(result.findings)[3]
        report = render(result)
        return report[report.index("**Блокеры:**"):report.index("**Блокеры:**") + 3000].split("\n\n")[1]

    nine = first_screen(7)
    assert nine.count("\n- ") + 1 == 9 and "и ещё" not in nine
    assert nine.index("[S-01]") < nine.index("[D-01]")
    ten = first_screen(8)
    assert ten.count("\n- ") + 1 == 10 and "и ещё" not in ten
    eleven = first_screen(9)
    assert eleven.count("\n- ") + 1 == 9 and "- и ещё 3, полный список" in eleven


def test_check_walks_fallback_chain(client_with, capsys):
    """--check идёт по цепочке моделей: ответила запасная, значит код 0 и строка о том, на чём пойдёт прогон."""
    from reqask import cli

    quota = [{"error": {"code": 429, "status": "RESOURCE_EXHAUSTED",
                        "message": "Generate content requests per day limit exceeded on Free Tier"}}]
    ok = _completion(json.dumps({"ok": True, "reply": "готово"}))
    client, sent, _ = client_with(lambda b, n: (429, quota) if b["model"] == "m" else (200, ok), fallback_models=("b",))
    assert cli.run_check(client.s, lambda m: None) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert [b["model"] for b in sent] == ["m", "b"]
    assert "Запасные модели: b." in out and "отвечает модель b" in out
    assert "Основная модель не отвечает, прогон пойдёт на b." in out and "Переход: модель m" in out

    client, sent, _ = client_with(lambda b, n: (429, quota), fallback_models=("b",))
    assert cli.run_check(client.s, lambda m: None) == cli.EXIT_NO_MODEL
    assert "Не ответила ни одна модель цепочки: m, b." in capsys.readouterr().err

    client, sent, _ = client_with(lambda b, n: (200, ok))
    assert cli.run_check(client.s, lambda m: None) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "отвечает модель m" in out and "Основная модель не отвечает" not in out


def test_incomplete_report_has_no_positive_verdict(doc):
    """К-10: неполный отчёт без CRITICAL даёт «Не вынесен» с причиной; найденный CRITICAL решение оставляет."""

    class FatalReview(FakeLLM):
        def __init__(self, set_answer=True):
            super().__init__()
            self.set_answer = set_answer

        def complete_json(self, step, system, user, schema, kind=""):
            if schema is BatchReviewOut:
                raise LLMFatal("квота исчерпана", kind="quota")
            return super().complete_json(step, system, user, schema, kind)

    result = Pipeline(FatalReview(), SETTINGS).run(doc, "test")
    v = result.verdict
    assert v.partial and not any(f.severity == "CRITICAL" for f in result.findings)
    assert (v.decision, v.ready_for_development, v.ready_for_testing) == ("Не вынесен", "Не определена", "Не определена")
    assert v.partial_reason.startswith("Отчёт неполный: проверено требований 0 из 3.")
    assert "«Проверка каждого требования» (не выполнен)" in v.partial_reason
    report = render(result)
    head = report.split("## 1.")[0]
    assert "**Вердикт: Не вынесен.**" in head and "Проверено требований 0 из 3" in head and "Допускается" not in head
    assert v.rationale.startswith(v.partial_reason)

    # Неполный отчёт, но CRITICAL найден: решение «Не рекомендуется начинать» остаётся.
    class FatalCritic(FakeLLM):
        def complete_json(self, step, system, user, schema, kind=""):
            if schema is CriticOut:
                raise LLMFatal("квота исчерпана", kind="quota")
            return super().complete_json(step, system, user, schema, kind)

    result = Pipeline(FatalCritic(), SETTINGS).run(doc, "test")
    v = result.verdict
    assert v.partial and v.decision == "Не рекомендуется начинать" and v.ready_for_development == "Нет"
    assert "CRITICAL найден в проверенной части" in render(result).split("## 1.")[0]
