"""Правила промптов второй волны: нарезка размытых требований, общие фразы вместо случаев
одного документа, сверка пересказа строк. Классы граничных случаев: отдельный третий проход шага 5."""

from dataclasses import replace

from reqask import prompts
from reqask.llm import LLMError, LLMTruncated
from reqask.pipeline import EDGE_STEP, Pipeline
from reqask.schemas import EdgeReviewOut, SetReviewOut

from test_core import SETTINGS, FakeLLM, _set_finding, doc  # noqa: F401  (doc это фикстура)

EDGE_CLASSES = ("величины:", "границы диапазонов:", "время:", "состояние:", "операции:", "классификация:",
                "смежные системы:", "одновременность:", "количество:", "права:")


def _final() -> str:
    return prompts.final_prompt("spec.md", 3, [], "решение", 5, "L0001 текст")


def test_segmentation_keeps_vague_requirements():
    text = prompts.segmentation_prompt("L0001 текст", "", None)
    assert "нельзя написать тест" not in text
    assert "даже если оно размытое или его нельзя проверить" in text
    for word in ("should", "may", "желательно", "рекомендуется"):
        assert word in text
    # правило про констатацию отсутствия осталось
    assert "констатация, которая ничего не требует" in text


def test_no_case_list_of_given_document_in_final_prompt():
    text = _final()
    assert "хранение и показ" not in text
    assert "краткая схема и подробное правило" not in text
    assert "обзор и деталь, внутреннее и внешнее представление" in text
    assert "в каталоге полное название книги" in text


def test_identifier_example_and_numbers_rule():
    seg = prompts.segmentation_prompt("L0001 текст", "", None)
    assert "ФТ-3" not in seg and "«ТР-7»" in seg
    assert "сроков, лимитов, объёмов, процентов и количеств" in prompts.NUMBERS_RULE
    assert "порогов" not in prompts.NUMBERS_RULE


def test_final_prompt_checks_line_paraphrase():
    assert "Не приписывай строке документа того, чего в ней нет" in _final()


def test_edge_prompt_has_all_classes_and_rules():
    text = prompts.edge_prompt([], "L0001 текст")
    block = text[text.index("Классы граничных случаев:"):text.index("Как искать:")]
    for cls in EDGE_CLASSES:
        assert f"- {cls}" in block
    for rule in ("пропусти молча", "kind gap", "criterion SET_COMPLETE", "не придумывай",
                 "описано в любой строке документа", "Один случай, одно замечание",
                 f"Не больше {prompts.EDGE_MAX_FINDINGS} замечаний", "Эти проходы замечаний не нашли."):
        assert rule in text, rule
    assert prompts.QUESTION_RULES in text and prompts.SET_FINDING_RULES in text and prompts.SEVERITY_RULES in text
    assert "—" not in text and "–" not in text


def test_edge_classes_left_completeness_prompt():
    text = prompts.completeness_prompt([], "L0001 текст")
    assert "Граничные случаи." not in text and "одновременность:" not in text
    assert "3. граничные значения: минимум, максимум, ноль, пусто" in text
    assert "Первый проход замечаний не нашёл." in text


def test_edge_prompt_lists_found_findings(doc):  # noqa: F811
    llm = FakeLLM()
    Pipeline(llm, SETTINGS).run(doc, "test")
    user = dict(zip(llm.steps, llm.users))[EDGE_STEP]
    assert "Уже найдено проходами по согласованности и полноте" in user
    assert "- SET_CONSISTENT | REQ-02, REQ-03 | Разное число книг" in user
    assert "Пустой раздел" in user and "Эти проходы замечаний не нашли." not in user


class EdgeLLM(FakeLLM):
    def complete_json(self, step, system, user, schema, kind="", **opts):
        if schema is EdgeReviewOut:
            self.steps.append(step)
            return EdgeReviewOut.model_validate({"findings": [
                _set_finding("gap", "SET_COMPLETE", "MAJOR", "Возврат книги в последний день",
                             ["Читатель может взять на руки не больше 5 книг"], req_ids=["REQ-002"],
                             question="Можно ли взять шестую книгу, если одна сдаётся сейчас?"),
            ]})
        return super().complete_json(step, system, user, schema, kind)


def test_edge_pass_runs_third_and_findings_go_through_pipeline(doc):  # noqa: F811
    logs = []
    llm = EdgeLLM()
    result = Pipeline(llm, SETTINGS, logs.append).run(doc, "test")
    set_steps = [s for s in llm.steps if s.startswith("набор")]
    assert set_steps == ["набор: согласованность", "набор: полнота и остальные критерии", EDGE_STEP]
    edge = [f for f in result.findings if f.origin == "edge"]
    assert len(edge) == 1 and edge[0].id.startswith("S-") and edge[0].evidence[0].status == "exact"
    assert edge[0].status != "unreviewed"  # критик его видел
    assert any(f.origin == "consistency" for f in result.findings)
    step5 = next(s for s in result.steps if s.number == "5")
    assert step5.name == "Набор требований целиком (три прохода)" and "граничных случаев 1" in step5.summary
    assert f"  {EDGE_STEP}" in logs and f"  {EDGE_STEP}: замечаний 1" in logs


def test_edge_switch_off(doc):  # noqa: F811
    llm = EdgeLLM()
    result = Pipeline(llm, replace(SETTINGS, edge=False)).run(doc, "test")
    assert EDGE_STEP not in llm.steps and not any(f.origin == "edge" for f in result.findings)
    step5 = next(s for s in result.steps if s.number == "5")
    assert "два прохода" in step5.name and "граничных" not in step5.summary and step5.status == "ok"


def test_edge_switch_from_env_and_cli(monkeypatch, tmp_path):
    from reqask import cli
    from reqask.config import load_settings

    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:9/v1/")
    monkeypatch.setenv("LLM_API_KEY", "x")
    monkeypatch.setenv("LLM_MODEL", "fake")
    monkeypatch.chdir(tmp_path)  # без .env: настройки только из переменных
    monkeypatch.setenv("REQASK_EDGE", "0")
    assert load_settings().edge is False
    monkeypatch.setenv("REQASK_EDGE", "1")
    assert load_settings().edge is True
    assert cli.build_parser().parse_args(["--no-edge"]).no_edge is True


def test_edge_pass_failure_does_not_break_run(doc):  # noqa: F811
    class Broken(FakeLLM):
        def complete_json(self, step, system, user, schema, kind="", **opts):
            if schema is EdgeReviewOut:
                self.steps.append(step)
                raise LLMError("сеть недоступна")
            return super().complete_json(step, system, user, schema, kind)

    result = Pipeline(Broken(), SETTINGS).run(doc, "test")
    step5 = next(s for s in result.steps if s.number == "5")
    assert step5.status == "degraded" and EDGE_STEP in step5.reason
    assert any(f.origin == "completeness" for f in result.findings)
    assert result.critic.done and result.questions


def test_truncated_edge_pass_retries_once_with_low_effort(doc):  # noqa: F811
    class Cut(EdgeLLM):
        efforts: list = []

        def complete_json(self, step, system, user, schema, kind="", **opts):
            if schema is EdgeReviewOut:
                self.efforts.append(opts.get("effort"))
                if opts.get("effort") != "low":
                    raise LLMTruncated("обрезан")
            return super().complete_json(step, system, user, schema, kind)

    llm = Cut()
    result = Pipeline(llm, SETTINGS).run(doc, "test")
    assert llm.efforts == [None, "low"] and not result.failed_steps
    assert [f.origin for f in result.findings].count("edge") == 1


def test_completeness_schema_unchanged():
    """Ответ полноты берётся из кэша: схема прохода и ключ не поменялись."""
    assert set(SetReviewOut.model_fields) == {"analyses", "findings"}
    assert set(EdgeReviewOut.model_fields) == {"findings"}
