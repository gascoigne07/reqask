"""Честные формулировки отчёта: блок «Что агент не проверяет», «замечаний не найдено» вместо «выполнен»,
пояснение чисел о номерах из документа (раздел 2 и паспорт)."""

from reqask.report import LIMITS, LIMITS_TITLE, PASS_LABEL, render, segmentation_ids
from reqask.report_html import render_html
from reqask.schemas import QualityStats

from test_report_audit import _f, _req, _result


def _with_ids():
    reqs = [_req(1, 10), _req(2, 20), _req(3, 30), _req(4, 40)]
    reqs[0].source_id, reqs[1].source_id, reqs[2].source_id = "ФТ-1", "ФТ-2", "1"
    return reqs


def test_limits_block_in_verdict_and_link_on_first_screen():
    report = render(_result([_f("D-01", "requirement", [10], ["REQ-01"])]))
    first = report[: report.index("## 1.")]
    assert "не доказывает, что требование верное" in first and "[раздел 6](#limits)" in first
    verdict = report[report.index("## 6."): report.index("## 7.")]
    assert '<a id="limits"></a>' in verdict and f"### {LIMITS_TITLE}" in verdict
    for item in LIMITS:
        assert f"- {item}" in verdict
    assert 4 <= len(LIMITS) <= 6
    assert "—" not in "".join(LIMITS) and "–" not in "".join(LIMITS)


def test_pass_is_called_no_findings_not_fulfilled():
    report = render(_result([_f("D-01", "requirement", [10], ["REQ-01"])]))
    assert f"✅ {PASS_LABEL}" in report and "✅ выполнен" not in report
    assert "все применимые критерии выполнены" not in report
    assert "**Замечаний не найдено ни по одному применимому критерию (3):**" in report
    html = render_html(_result([_f("D-01", "requirement", [10], ["REQ-01"])]))
    assert "все применимые критерии выполнены" not in html and PASS_LABEL in html
    assert 'id="limits"' in html and 'href="#limits"' in html and LIMITS_TITLE in html


def test_document_numbers_explained_in_segmentation_and_passport():
    result = _result([], requirements=_with_ids(), quality=QualityStats(ids_in_document=2))
    text = segmentation_ids(result)
    assert text.startswith("Номер из документа стоит у 3 требований: у 2 это идентификатор с буквами")
    assert "у 1 номер пункта списка" in text and "код нашёл в документе 2, это число стоит в паспорте" in text
    report = render(result)
    assert text in report
    assert "| Идентификаторы с буквами (вида «ФТ-3») | разных в документе 2, в нарезке 2, потерянных нет |" in report
    assert "Своего номера в документе нет ни у одного требования." == segmentation_ids(_result([]))
