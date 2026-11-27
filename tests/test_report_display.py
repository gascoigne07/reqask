"""Показ в report.py: конец предложения у числа в кавычках, оценка при снятом критиком замечании."""

from reqask.pipeline import Pipeline
from reqask.report import _Report, _first_sentence, render

from helpers import SETTINGS, FakeLLM


def test_first_sentence_keeps_number_inside_quotes_and_heading_number():
    text = "Текст стоит в разделе «403. Unsuccessful, Forbidden», но задаёт ответ 404. Второе предложение."
    assert _first_sentence(text, 200) == "Текст стоит в разделе «403. Unsuccessful, Forbidden», но задаёт ответ 404."
    assert _first_sentence("403. Ответ при запрете доступа. Дальше текст.", 200) == "403. Ответ при запрете доступа."
    # Число в конце обычного предложения по-прежнему его кончает.
    assert _first_sentence("Лимит до 404. Дальше текст.", 200) == "Лимит до 404."


def test_criterion_with_only_dropped_findings_is_shown_as_pass(doc):
    result = Pipeline(FakeLLM(), SETTINGS).run(doc, "test")
    d2 = next(f for f in result.findings if f.id == "D-02")
    assert d2.req_ids == ["REQ-02"] and d2.criterion == "UNAMBIGUOUS"
    req = next(x for x in result.requirements if x.id == "REQ-02")
    assert {c.criterion: c.status for c in result.checks["REQ-02"]}["UNAMBIGUOUS"] == "fail"

    d2.status, d2.critic_reason = "dropped", "документ отвечает строкой 5"
    assert _Report(result)._statuses(req)[1]["statuses"]["UNAMBIGUOUS"] == "pass"
    assert "❌ Однозначность" not in render(result)
    # report.json не меняется: правка только в показе.
    assert {c.criterion: c.status for c in result.checks["REQ-02"]}["UNAMBIGUOUS"] == "fail"

    d2.status, d2.merged_into = "merged", "S-01"
    assert _Report(result)._statuses(req)[1]["statuses"]["UNAMBIGUOUS"] == "fail"
